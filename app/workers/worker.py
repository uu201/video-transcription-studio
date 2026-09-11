"""独立线程轮询任务，避免 Web 请求执行长耗时模型推理。"""

from __future__ import annotations

import logging
import threading
import uuid
from queue import Queue, Empty

from app.config import Settings
from app.db.database import Database, utc_now
from app.services.pipeline import PipelineService

LOGGER = logging.getLogger(__name__)


class TaskWorkerPool:
    """多 Worker 并发任务处理池。"""

    def __init__(self, settings: Settings, database: Database, event_hub=None, worker_count: int = None):
        self.settings = settings
        self.database = database
        self.event_hub = event_hub
        self.worker_count = worker_count or getattr(settings, 'worker_count', 2)
        self.workers = []
        self._stop = threading.Event()
        self._task_queue = Queue(maxsize=100)
        self._condition = threading.Condition()
        self._dispatcher_thread = None

    def start(self) -> None:
        """启动所有 Worker 和任务分发线程。"""
        if self.workers:
            return

        # 启动 Worker 线程
        for i in range(self.worker_count):
            worker = TaskWorker(
                settings=self.settings,
                database=self.database,
                event_hub=self.event_hub,
                worker_id=f"worker-{i+1}-{uuid.uuid4().hex[:6]}",
                task_queue=self._task_queue,
                stop_event=self._stop
            )
            worker.start()
            self.workers.append(worker)

        # 启动任务分发线程
        self._dispatcher_thread = threading.Thread(
            target=self._dispatch_tasks,
            name="task-dispatcher",
            daemon=True
        )
        self._dispatcher_thread.start()

        LOGGER.info(f"TaskWorkerPool 已启动，Worker 数量: {self.worker_count}")

    def stop(self) -> None:
        """停止所有 Worker。"""
        LOGGER.info("正在停止 TaskWorkerPool...")
        self._stop.set()

        # 通知所有等待的 Worker
        with self._condition:
            self._condition.notify_all()

        # 等待所有 Worker 完成
        for worker in self.workers:
            worker.stop()

        if self._dispatcher_thread:
            self._dispatcher_thread.join(timeout=3)

        self.workers = []
        LOGGER.info("TaskWorkerPool 已停止")

    def notify_new_task(self) -> None:
        """通知有新任务到达，立即唤醒分发线程。"""
        with self._condition:
            self._condition.notify()

    def _dispatch_tasks(self) -> None:
        """任务分发线程：轮询数据库并将任务放入队列。"""
        while not self._stop.is_set():
            try:
                # 如果队列已满，等待
                if self._task_queue.full():
                    self._stop.wait(1)
                    continue

                # 查询待处理任务
                task_id = self._claim_next()
                if task_id:
                    self._task_queue.put(task_id, timeout=1)
                    LOGGER.debug(f"任务 {task_id} 已加入队列")
                else:
                    # 没有任务时等待通知或超时
                    with self._condition:
                        self._condition.wait(timeout=self.settings.poll_interval_seconds)

            except Exception as e:
                LOGGER.error(f"任务分发异常: {e}", exc_info=True)
                self._stop.wait(1)

    def _claim_next(self) -> int | None:
        """从数据库中领取下一个待处理任务。"""
        now = utc_now()
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT id FROM processing_task WHERE status = 'QUEUED' AND cancel_requested = 0 AND pause_requested = 0 ORDER BY created_at LIMIT 1"
            ).fetchone()

            if not row:
                return None

            # 标记任务为已领取但未分配 Worker
            changed = connection.execute(
                "UPDATE processing_task SET status = 'RUNNING', current_stage = 'PROBING', progress = 1, message = '等待 Worker 处理', heartbeat_at = ?, started_at = COALESCE(started_at, ?), updated_at = ? WHERE id = ? AND status = 'QUEUED' AND pause_requested = 0",
                (now, now, now, row["id"])
            ).rowcount

            if changed != 1:
                return None

            connection.execute(
                "INSERT INTO task_event (task_id, stage, level, message, created_at) VALUES (?, 'PROBING', 'INFO', '任务已领取', ?)",
                (row["id"], now)
            )

            if self.event_hub:
                self.event_hub.publish({"type": "task.updated", "taskId": int(row["id"]), "status": "RUNNING", "stage": "PROBING", "progress": 1, "message": "等待 Worker 处理", "at": now})

            return int(row["id"])


class TaskWorker:
    """单个任务处理 Worker。"""

    def __init__(self, settings: Settings, database: Database, event_hub=None, worker_id: str = None, task_queue: Queue = None, stop_event: threading.Event = None):
        self.settings = settings
        self.database = database
        self.event_hub = event_hub
        self.pipeline = PipelineService(settings, database, event_hub)
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.task_queue = task_queue
        self.stop_event = stop_event or threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动后台线程。"""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name=f"video-text-{self.worker_id}",
            daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """请求线程在当前任务完成后退出。"""
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        """从队列获取任务并处理。"""
        LOGGER.info(f"Worker {self.worker_id} 已启动")

        while not self.stop_event.is_set():
            try:
                # 从队列获取任务（超时 1 秒）
                task_id = self.task_queue.get(timeout=1)

                # 更新 Worker ID
                now = utc_now()
                with self.database.connection() as connection:
                    connection.execute(
                        "UPDATE processing_task SET worker_id = ?, message = '开始处理', heartbeat_at = ?, updated_at = ? WHERE id = ?",
                        (self.worker_id, now, now, task_id)
                    )

                LOGGER.info(f"Worker {self.worker_id} 开始处理任务 {task_id}")
                self.pipeline.process(task_id)
                LOGGER.info(f"Worker {self.worker_id} 完成任务 {task_id}")

                self.task_queue.task_done()

            except Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                LOGGER.error(f"Worker {self.worker_id} 处理任务异常: {e}", exc_info=True)

        LOGGER.info(f"Worker {self.worker_id} 已停止")
