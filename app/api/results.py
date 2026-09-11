"""转录结果资产 API。"""

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import database
from app.db.database import Database

router = APIRouter(prefix="/api/results", tags=["转录结果"])


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
