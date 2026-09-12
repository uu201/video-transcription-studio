"""任务、状态和转写结果 API。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.api.dependencies import database
from app.db.database import Database, utc_now
from app.domain.enums import TaskStatus

router = APIRouter(prefix="/api/tasks", tags=["任务"])


class TaskInput(BaseModel):
    """手工创建任务的参数。"""

    mediaFileId: int
    language: str = "auto"
    requestedAi: bool = False
    asrOptions: dict = Field(default_factory=dict)


class BatchTaskInput(BaseModel):
    """批量创建任务的参数。"""

    mediaFileIds: list[int] = Field(min_length=1, max_length=500)
    language: str = "auto"


def _task(row) -> dict:
    """转换任务数据库行。"""
    return {"id": row["id"], "mediaFileId": row["media_file_id"], "fileName": row["file_name"], "path": row["path"], "extension": row["extension"], "fileSize": row["size_bytes"], "status": row["status"], "stage": row["current_stage"], "progress": row["progress"], "message": row["message"], "pauseRequested": bool(row["pause_requested"]), "cancelRequested": bool(row["cancel_requested"]), "requestedAi": bool(row["requested_ai"]), "language": row["language"], "error": {"code": row["error_code"], "message": row["error_message"], "detail": row["error_detail"], "retryable": bool(row["retryable"])} if row["error_code"] else None, "startedAt": row["started_at"], "finishedAt": row["finished_at"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


TASK_QUERY = "SELECT t.*, m.file_name, m.path, m.extension, m.size_bytes FROM processing_task t JOIN media_file m ON m.id = t.media_file_id"


def _publish_task_event(request: Request, task_id: int, *, status_value: str, message: str, pause_requested: bool | None = None, cancel_requested: bool | None = None) -> None:
    """广播用户操作，确保其他打开的队列页面立即同步。"""
    event_hub = getattr(request.app.state, "event_hub", None)
    if event_hub:
        payload = {"type": "task.updated", "taskId": task_id, "status": status_value, "message": message, "at": utc_now()}
        if pause_requested is not None:
            payload["pauseRequested"] = pause_requested
        if cancel_requested is not None:
            payload["cancelRequested"] = cancel_requested
        event_hub.publish(payload)


def _publish_task_deleted(request: Request, task_id: int) -> None:
    """通知其他队列页面移除已删除记录。"""
    event_hub = getattr(request.app.state, "event_hub", None)
    if event_hub:
        event_hub.publish({"type": "task.deleted", "taskId": task_id, "at": utc_now()})


@router.get("")
def list_tasks(response: Response, status_filter: str | None = Query(default=None, alias="status"), limit: int = Query(default=100, ge=1, le=500), db: Database = Depends(database)) -> list[dict]:
    """分页返回任务。"""
    # 任务列表缓存 3 秒，因为状态会频繁变化
    response.headers["Cache-Control"] = "public, max-age=3"
    if status_filter:
        rows = db.fetch_all(TASK_QUERY + " WHERE t.status = ? ORDER BY t.created_at DESC LIMIT ?", (status_filter, limit))
    else:
        rows = db.fetch_all(TASK_QUERY + " ORDER BY t.created_at DESC LIMIT ?", (limit,))
    return [_task(row) for row in rows]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_task(payload: TaskInput, request: Request, db: Database = Depends(database)) -> dict:
    """基于已发现媒体文件创建排队任务。"""
    media = db.fetch_one("SELECT id, file_name, path FROM media_file WHERE id = ?", (payload.mediaFileId,))
    if not media:
        raise HTTPException(404, "媒体文件不存在")
    now = utc_now()
    task_id = db.execute("INSERT INTO processing_task (media_file_id, requested_ai, language, asr_options_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (payload.mediaFileId, int(payload.requestedAi), payload.language, json.dumps(payload.asrOptions), now, now))
    _publish_task_event(request, task_id, status_value=TaskStatus.QUEUED.value, message="等待处理")
    worker = getattr(request.app.state, "worker", None)
    if worker:
        worker.notify_new_task()
    return {"id": task_id, "status": TaskStatus.QUEUED.value}


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
def create_tasks(payload: BatchTaskInput, request: Request, db: Database = Depends(database)) -> dict:
    """将用户勾选且未处理的媒体文件批量加入转写队列。"""
    media_ids = list(dict.fromkeys(payload.mediaFileIds))
    placeholders = ",".join("?" for _ in media_ids)
    rows = db.fetch_all(
        f"SELECT id FROM media_file WHERE id IN ({placeholders}) ORDER BY id",
        tuple(media_ids),
    )
    existing_ids = {row["id"] for row in rows}
    missing_ids = [media_id for media_id in media_ids if media_id not in existing_ids]
    if missing_ids:
        raise HTTPException(404, f"媒体文件不存在：{missing_ids}")

    now = utc_now()
    created_ids: list[int] = []
    skipped_ids: list[int] = []
    with db.connection() as connection:
        for media_id in media_ids:
            task = connection.execute(
                "SELECT id FROM processing_task WHERE media_file_id = ? LIMIT 1",
                (media_id,),
            ).fetchone()
            if task:
                skipped_ids.append(media_id)
                continue
            cursor = connection.execute(
                "INSERT INTO processing_task (media_file_id, language, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (media_id, payload.language, now, now),
            )
            created_ids.append(cursor.lastrowid)
    for task_id in created_ids:
        _publish_task_event(request, task_id, status_value=TaskStatus.QUEUED.value, message="等待处理")
    worker = getattr(request.app.state, "worker", None)
    if worker and created_ids:
        worker.notify_new_task()
    return {"created": len(created_ids), "taskIds": created_ids, "skippedMediaIds": skipped_ids}


@router.get("/{task_id}")
def get_task(task_id: int, db: Database = Depends(database)) -> dict:
    """返回任务详情、事件和媒体信息。"""
    row = db.fetch_one(TASK_QUERY + " WHERE t.id = ?", (task_id,))
    if not row:
        raise HTTPException(404, "任务不存在")
    data = _task(row)
    media_row = db.fetch_one("SELECT media_info_json FROM media_file WHERE id = ?", (row["media_file_id"],))
    data["mediaInfo"] = json.loads(media_row["media_info_json"]) if media_row and media_row["media_info_json"] else None
    data["events"] = [dict(event) for event in db.fetch_all("SELECT stage, level, message, detail, created_at AS createdAt FROM task_event WHERE task_id = ? ORDER BY created_at", (task_id,))]
    return data


@router.post("/{task_id}/start")
def start_task(task_id: int, request: Request, db: Database = Depends(database)) -> dict:
    """手动将任务置为排队状态。"""
    changed = db.execute("UPDATE processing_task SET status='QUEUED', cancel_requested=0, error_code=NULL, error_message=NULL, error_detail=NULL, updated_at=? WHERE id=? AND status IN ('FAILED','CANCELED')", (utc_now(), task_id))
    if changed == 0:
        raise HTTPException(409, "任务当前状态不允许启动")
    _publish_task_event(request, task_id, status_value=TaskStatus.QUEUED.value, message="等待处理")
    return get_task(task_id, db)


@router.post("/{task_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_task(task_id: int, request: Request, db: Database = Depends(database)) -> dict:
    """在原任务记录上重新排队，避免重复创建任务。"""
    row = db.fetch_one("SELECT status FROM processing_task WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(404, "任务不存在")
    now = utc_now()
    with db.connection() as connection:
        changed = connection.execute(
            "UPDATE processing_task SET status='QUEUED', current_stage='QUEUED', progress=0, message='等待处理', cancel_requested=0, pause_requested=0, error_code=NULL, error_message=NULL, error_detail=NULL, retryable=0, worker_id=NULL, heartbeat_at=NULL, started_at=NULL, finished_at=NULL, updated_at=? WHERE id=? AND status IN ('FAILED','CANCELED')",
            (now, task_id),
        ).rowcount
        if changed == 0:
            raise HTTPException(409, "任务当前状态不允许重试")
        connection.execute("DELETE FROM transcript WHERE task_id = ?", (task_id,))
        connection.execute("DELETE FROM export_record WHERE task_id = ?", (task_id,))
        connection.execute("DELETE FROM ai_analysis WHERE task_id = ?", (task_id,))
        connection.execute("DELETE FROM file_transfer WHERE task_id = ?", (task_id,))
        connection.execute("INSERT INTO task_event (task_id, stage, level, message, created_at) VALUES (?, 'QUEUED', 'INFO', '任务已重新排队', ?)", (task_id, now))
    _publish_task_event(request, task_id, status_value=TaskStatus.QUEUED.value, message="等待处理", pause_requested=False, cancel_requested=False)
    return {"id": task_id, "status": TaskStatus.QUEUED.value}


@router.post("/{task_id}/pause")
def pause_task(task_id: int, request: Request, db: Database = Depends(database)) -> dict:
    """请求暂停任务；运行中的任务在当前阶段结束后暂停。"""
    row = db.fetch_one("SELECT status FROM processing_task WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(404, "任务不存在")
    if row["status"] == TaskStatus.QUEUED.value:
        changed = db.execute("UPDATE processing_task SET status='PAUSED', pause_requested=1, message='已暂停', updated_at=? WHERE id=? AND status='QUEUED'", (utc_now(), task_id))
    elif row["status"] == TaskStatus.RUNNING.value:
        changed = db.execute("UPDATE processing_task SET pause_requested=1, message='正在等待暂停', updated_at=? WHERE id=? AND status='RUNNING'", (utc_now(), task_id))
    else:
        raise HTTPException(409, "任务当前状态不允许暂停")
    if changed == 0:
        raise HTTPException(409, "任务状态已发生变化")
    _publish_task_event(request, task_id, status_value="PAUSED" if row["status"] == TaskStatus.QUEUED.value else "RUNNING", message="已暂停" if row["status"] == TaskStatus.QUEUED.value else "正在等待暂停", pause_requested=True)
    return get_task(task_id, db)


@router.post("/{task_id}/resume")
def resume_task(task_id: int, request: Request, db: Database = Depends(database)) -> dict:
    """恢复暂停任务，将其重新加入处理队列。"""
    now = utc_now()
    changed = db.execute("UPDATE processing_task SET status='QUEUED', pause_requested=0, cancel_requested=0, message='等待处理', updated_at=? WHERE id=? AND status='PAUSED'", (now, task_id))
    if changed == 0:
        raise HTTPException(409, "任务当前状态不允许恢复")
    db.execute("INSERT INTO task_event (task_id, stage, level, message, created_at) VALUES (?, 'QUEUED', 'INFO', '任务已恢复，等待处理', ?)", (task_id, now))
    _publish_task_event(request, task_id, status_value="QUEUED", message="等待处理", pause_requested=False, cancel_requested=False)
    return get_task(task_id, db)


@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, request: Request, db: Database = Depends(database)) -> dict:
    """设置取消标记，由 Worker 在阶段边界处理。"""
    row = db.fetch_one("SELECT status FROM processing_task WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(404, "任务不存在")
    was_queued = row["status"] == TaskStatus.QUEUED.value
    now = utc_now()
    changed = db.execute("UPDATE processing_task SET status='CANCELED', cancel_requested=1, message='已取消', finished_at=?, updated_at=? WHERE id=? AND status='QUEUED'", (now, now, task_id))
    if changed == 0:
        changed = db.execute("UPDATE processing_task SET cancel_requested=1, message='正在取消', updated_at=? WHERE id=? AND status='RUNNING'", (now, task_id))
    if changed == 0:
        raise HTTPException(409, "任务当前状态不允许取消")
    _publish_task_event(request, task_id, status_value="CANCELED" if was_queued else "RUNNING", message="已取消" if was_queued else "正在取消", cancel_requested=True)
    return {"id": task_id, "cancelRequested": True}


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_task(task_id: int, request: Request, db: Database = Depends(database)) -> None:
    """删除任务及其结果。"""
    if db.execute("DELETE FROM processing_task WHERE id = ?", (task_id,)) == 0:
        raise HTTPException(404, "任务不存在")
    _publish_task_deleted(request, task_id)


@router.get("/{task_id}/transcript")
def get_transcript(task_id: int, db: Database = Depends(database)) -> dict:
    """返回原始文本、清洗文本和原始 JSON。"""
    row = db.fetch_one("SELECT * FROM transcript WHERE task_id = ?", (task_id,))
    if not row:
        raise HTTPException(404, "转写结果不存在")
    return {"id": row["id"], "taskId": task_id, "language": row["language"], "rawText": row["raw_text"], "cleanText": row["clean_text"], "rawJson": json.loads(row["raw_json"]), "version": row["version"]}


@router.get("/{task_id}/segments")
def get_segments(task_id: int, db: Database = Depends(database)) -> list[dict]:
    """返回时间戳分段。"""
    rows = db.fetch_all("SELECT s.sequence, s.start_seconds, s.end_seconds, s.text, s.speaker, s.confidence FROM transcript_segment s JOIN transcript t ON t.id=s.transcript_id WHERE t.task_id=? ORDER BY s.sequence", (task_id,))
    return [{"sequence": row["sequence"], "start": row["start_seconds"], "end": row["end_seconds"], "text": row["text"], "speaker": row["speaker"], "confidence": row["confidence"]} for row in rows]
