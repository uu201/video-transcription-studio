"""独立线程轮询任务，避免 Web 请求执行长耗时模型推理。"""

from __future__ import annotations

import logging
import threading
import uuid

from app.config import Settings
from app.db.database import Database, utc_now
from app.services.pipeline import PipelineService

LOGGER = logging.getLogger(__name__)


class TaskWorker:
    """单并发任务 Worker。"""

    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.pipeline = PipelineService(settings, database)
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动后台线程。"""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="video-text-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """请求线程在当前任务完成后退出。"""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        """轮询、条件领取并处理任务。"""
        while not self._stop.is_set():
            task_id = self._claim_next()
            if task_id:
                self.pipeline.process(task_id)
            else:
                self._stop.wait(self.settings.poll_interval_seconds)

    def _claim_next(self) -> int | None:
        """使用条件更新保证同一任务只被一个 Worker 领取。"""
        now = utc_now()
        with self.database.connection() as connection:
            row = connection.execute("SELECT id FROM processing_task WHERE status = 'QUEUED' AND cancel_requested = 0 ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                return None
            changed = connection.execute("UPDATE processing_task SET status = 'RUNNING', current_stage = 'PROBING', progress = 1, message = '开始处理', worker_id = ?, heartbeat_at = ?, started_at = COALESCE(started_at, ?), updated_at = ? WHERE id = ? AND status = 'QUEUED'", (self.worker_id, now, now, now, row["id"])).rowcount
            if changed != 1:
                return None
            connection.execute("INSERT INTO task_event (task_id, stage, level, message, created_at) VALUES (?, 'PROBING', 'INFO', '开始处理', ?)", (row["id"], now))
            return int(row["id"])
