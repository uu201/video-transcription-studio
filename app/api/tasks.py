"""任务、状态和转写结果 API。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


def _task(row) -> dict:
    """转换任务数据库行。"""
    return {"id": row["id"], "mediaFileId": row["media_file_id"], "fileName": row["file_name"], "path": row["path"], "status": row["status"], "stage": row["current_stage"], "progress": row["progress"], "message": row["message"], "requestedAi": bool(row["requested_ai"]), "language": row["language"], "error": {"code": row["error_code"], "message": row["error_message"], "detail": row["error_detail"], "retryable": bool(row["retryable"])} if row["error_code"] else None, "startedAt": row["started_at"], "finishedAt": row["finished_at"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


TASK_QUERY = "SELECT t.*, m.file_name, m.path FROM processing_task t JOIN media_file m ON m.id = t.media_file_id"


@router.get("")
def list_tasks(status_filter: str | None = Query(default=None, alias="status"), limit: int = Query(default=100, ge=1, le=500), db: Database = Depends(database)) -> list[dict]:
    """分页返回任务。"""
    if status_filter:
        rows = db.fetch_all(TASK_QUERY + " WHERE t.status = ? ORDER BY t.created_at DESC LIMIT ?", (status_filter, limit))
    else:
        rows = db.fetch_all(TASK_QUERY + " ORDER BY t.created_at DESC LIMIT ?", (limit,))
    return [_task(row) for row in rows]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_task(payload: TaskInput, db: Database = Depends(database)) -> dict:
    """基于已发现媒体文件创建排队任务。"""
    media = db.fetch_one("SELECT id, file_name, path FROM media_file WHERE id = ?", (payload.mediaFileId,))
    if not media:
        raise HTTPException(404, "媒体文件不存在")
    now = utc_now()
    task_id = db.execute("INSERT INTO processing_task (media_file_id, requested_ai, language, asr_options_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (payload.mediaFileId, int(payload.requestedAi), payload.language, json.dumps(payload.asrOptions), now, now))
    return {"id": task_id, "status": TaskStatus.QUEUED.value}


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
def start_task(task_id: int, db: Database = Depends(database)) -> dict:
    """手动将任务置为排队状态。"""
    changed = db.execute("UPDATE processing_task SET status='QUEUED', cancel_requested=0, error_code=NULL, error_message=NULL, error_detail=NULL, updated_at=? WHERE id=? AND status IN ('FAILED','CANCELED')", (utc_now(), task_id))
    if changed == 0:
        raise HTTPException(409, "任务当前状态不允许启动")
    return get_task(task_id, db)


@router.post("/{task_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_task(task_id: int, db: Database = Depends(database)) -> dict:
    """复制失败任务为新的处理记录，保留历史记录。"""
    row = db.fetch_one("SELECT media_file_id, language, requested_ai, asr_options_json FROM processing_task WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(404, "任务不存在")
    now = utc_now()
    new_id = db.execute("INSERT INTO processing_task (media_file_id, language, requested_ai, asr_options_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (row["media_file_id"], row["language"], row["requested_ai"], row["asr_options_json"], now, now))
    return {"id": new_id, "status": TaskStatus.QUEUED.value}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, db: Database = Depends(database)) -> dict:
    """设置取消标记，由 Worker 在阶段边界处理。"""
    changed = db.execute("UPDATE processing_task SET cancel_requested=1, updated_at=? WHERE id=? AND status IN ('QUEUED','RUNNING')", (utc_now(), task_id))
    if changed == 0:
        raise HTTPException(409, "任务当前状态不允许取消")
    return {"id": task_id, "cancelRequested": True}


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_task(task_id: int, db: Database = Depends(database)) -> None:
    """删除任务及其结果。"""
    if db.execute("DELETE FROM processing_task WHERE id = ?", (task_id,)) == 0:
        raise HTTPException(404, "任务不存在")


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
