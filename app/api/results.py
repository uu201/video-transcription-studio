"""转录结果资产 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.dependencies import database
from app.db.database import Database

router = APIRouter(prefix="/api/results", tags=["转录结果"])


class ResultDeleteInput(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


@router.get("")
def list_results(limit: int = Query(default=200, ge=1, le=500), db: Database = Depends(database)) -> list[dict]:
    """返回已完成且已有转写正文的结果资产，供结果书架使用。"""
    rows = db.fetch_all(
        """
        SELECT t.id, t.media_file_id AS mediaFileId, m.file_name AS fileName,
               m.path, m.extension, m.size_bytes AS fileSize, t.status,
               t.language, t.progress, t.finished_at AS finishedAt,
               t.created_at AS createdAt, t.updated_at AS updatedAt,
               tr.clean_text AS cleanText, tr.raw_text AS rawText,
               tr.version AS transcriptVersion,
               (SELECT COUNT(*) FROM transcript_segment s WHERE s.transcript_id = tr.id) AS segmentCount,
               (SELECT COUNT(*) FROM ai_analysis a WHERE a.task_id = t.id AND a.status = 'SUCCEEDED') AS analysisCount
        FROM processing_task t
        JOIN media_file m ON m.id = t.media_file_id
        JOIN transcript tr ON tr.task_id = t.id
        WHERE t.status = 'SUCCEEDED'
        ORDER BY COALESCE(t.finished_at, t.updated_at) DESC, t.id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in rows]


@router.delete("", status_code=status.HTTP_200_OK)
def delete_results(payload: ResultDeleteInput, request: Request, db: Database = Depends(database)) -> dict:
    """批量删除转录任务及结果，保留源媒体文件以便后续重新扫描。"""
    ids = list(dict.fromkeys(payload.ids))
    placeholders = ",".join("?" for _ in ids)
    rows = db.fetch_all(
        f"SELECT id FROM processing_task WHERE status='SUCCEEDED' AND id IN ({placeholders})",
        tuple(ids),
    )
    deleted_ids = [int(row["id"]) for row in rows]
    if not deleted_ids:
        raise HTTPException(404, "没有找到可删除的转录结果")
    deleted_placeholders = ",".join("?" for _ in deleted_ids)
    deleted = db.execute(f"DELETE FROM processing_task WHERE id IN ({deleted_placeholders})", tuple(deleted_ids))
    event_hub = getattr(request.app.state, "event_hub", None)
    if event_hub:
        for task_id in deleted_ids:
            event_hub.publish({"type": "task.deleted", "taskId": task_id})
    return {"deleted": deleted, "taskIds": deleted_ids, "rescanAvailable": True}
