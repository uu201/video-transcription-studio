"""AI 分析队列 API。"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from app.api.dependencies import database
from app.db.database import Database, utc_now
from app.repositories.ai_analysis_task import AIAnalysisTaskRepository
from app.services.ai_analysis_queue import AIAnalysisQueueService

router = APIRouter(prefix="/api/ai", tags=["AI 分析"])
compat_router = APIRouter(prefix="/api", tags=["AI 分析"])
class AnalysisInput(BaseModel):
    analysisTypes: list[str] = Field(min_length=1, max_length=20)
def _item(row):
    return {"id": row["id"], "fileName": row["file_name"], "transcriptId": row["transcript_id"], "transcriptionTaskId": row["transcription_task_id"], "analysisType": row["analysis_type"], "analysisTypes": json.loads(row["analysis_types_json"] or '[]'), "status": row["status"], "progress": row["progress"], "message": row["message"], "pauseRequested": bool(row["pause_requested"]), "cancelRequested": bool(row["cancel_requested"]), "providerName": row["provider_name"], "model": row["model"], "resultId": row["result_id"], "error": {"code": row["error_code"], "message": row["error_message"], "detail": row["error_detail"], "retryable": bool(row["retryable"])} if row["error_code"] else None, "createdAt": row["created_at"], "updatedAt": row["updated_at"], "finishedAt": row["finished_at"]}


def _publish_ai_event(request: Request, event_type: str, task_id: int, *, status_value: str, message: str, **extra) -> None:
    event_hub = getattr(request.app.state, "event_hub", None)
    if event_hub:
        event_hub.publish({"type": event_type, "taskId": task_id, "status": status_value, "message": message, "updatedAt": utc_now(), **extra})
@router.get("/tasks")
def list_ai_tasks(status_filter: str | None = Query(None, alias="status"), transcript_id: int | None = Query(None, alias="transcriptId"), db: Database = Depends(database)):
    items = [_item(r) for r in AIAnalysisTaskRepository(db).list(status_filter)]
    return [item for item in items if transcript_id is None or item["transcriptId"] == transcript_id]


@router.post("/tasks/pause-all", status_code=202)
def pause_all_ai_tasks(request: Request, db: Database = Depends(database)):
    """Pause every queued or running AI task immediately."""
    now = utc_now()
    with db.connection() as connection:
        rows = connection.execute(
            "SELECT id, progress FROM ai_analysis_task WHERE status IN ('QUEUED', 'RUNNING') ORDER BY id"
        ).fetchall()
        for row in rows:
            connection.execute(
                "UPDATE ai_analysis_task SET status='PAUSED', pause_requested=1, message='已暂停', updated_at=? WHERE id=? AND status IN ('QUEUED', 'RUNNING')",
                (now, row["id"]),
            )
    for row in rows:
        _publish_ai_event(
            request,
            "ai.task.updated",
            int(row["id"]),
            status_value="PAUSED",
            message="已暂停",
            progress=int(row["progress"] or 0),
            pauseRequested=True,
        )
    return {"updated": len(rows)}


@router.post("/tasks/start-all", status_code=202)
def start_all_ai_tasks(request: Request, db: Database = Depends(database)):
    """Resume every paused AI task."""
    now = utc_now()
    with db.connection() as connection:
        rows = connection.execute(
            "SELECT id FROM ai_analysis_task WHERE status='PAUSED' ORDER BY id"
        ).fetchall()
        connection.execute(
            "UPDATE ai_analysis_task SET status='QUEUED', pause_requested=0, cancel_requested=0, message='等待分析', worker_id=NULL, heartbeat_at=NULL, updated_at=? WHERE status='PAUSED'",
            (now,),
        )
    for row in rows:
        _publish_ai_event(
            request,
            "ai.task.updated",
            int(row["id"]),
            status_value="QUEUED",
            message="等待分析",
            progress=0,
            pauseRequested=False,
            cancelRequested=False,
        )
    return {"updated": len(rows)}
@router.get("/tasks/{task_id}")
def get_ai_task(task_id: int, db: Database = Depends(database)):
    row=AIAnalysisTaskRepository(db).get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    return _item(row)
@router.post("/tasks/{task_id}/retry", status_code=202)
def retry_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status'] not in ('FAILED','CANCELED'): raise HTTPException(409, "当前状态不允许重试")
    repo.update(task_id,status='QUEUED',progress=0,message='等待分析',error_code=None,error_message=None,error_detail=None,retryable=0,cancel_requested=0,pause_requested=0,worker_id=None,started_at=None,finished_at=None)
    _publish_ai_event(request, "ai.task.updated", task_id, status_value="QUEUED", message="等待分析", progress=0, pauseRequested=False, cancelRequested=False)
    return get_ai_task(task_id,db)
@router.post("/tasks/{task_id}/reanalyze", status_code=202)
def reanalyze_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    row = AIAnalysisTaskRepository(db).get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status'] not in ('SUCCEEDED', 'FAILED', 'CANCELED'): raise HTTPException(409, "当前状态不允许重新分析")
    created, _ = AIAnalysisQueueService(db, getattr(request.app.state, 'event_hub', None)).create(row['transcript_id'], json.loads(row['analysis_types_json'] or '[]'))
    return {"taskIds": created, "analysisType": row['analysis_type']}
@router.post("/tasks/{task_id}/cancel")
def cancel_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status'] not in ('QUEUED', 'RUNNING', 'PAUSED'):
        raise HTTPException(409, "当前状态不允许取消")
    repo.update(task_id,status='CANCELED',cancel_requested=1,message='已取消',finished_at=utc_now())
    _publish_ai_event(request, "ai.task.updated", task_id, status_value="CANCELED", message="已取消", progress=row['progress'], cancelRequested=True)
    return get_ai_task(task_id,db)
@router.post("/tasks/{task_id}/start")
def start_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status'] not in ('PAUSED','FAILED','CANCELED'): raise HTTPException(409, "当前状态不允许开始")
    repo.update(task_id,status='QUEUED',progress=0,message='等待分析',error_code=None,error_message=None,error_detail=None,retryable=0,cancel_requested=0,pause_requested=0,worker_id=None,started_at=None,finished_at=None)
    _publish_ai_event(request, "ai.task.updated", task_id, status_value="QUEUED", message="等待分析", progress=0, pauseRequested=False, cancelRequested=False)
    return get_ai_task(task_id,db)
@router.post("/tasks/{task_id}/pause")
def pause_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status'] not in ('QUEUED', 'RUNNING'):
        raise HTTPException(409, "当前状态不允许暂停")
    repo.update(task_id,status='PAUSED',pause_requested=1,message='已暂停')
    _publish_ai_event(request, "ai.task.updated", task_id, status_value="PAUSED", message="已暂停", progress=row['progress'], pauseRequested=True)
    return get_ai_task(task_id,db)
@router.delete("/tasks/{task_id}", status_code=204)
def delete_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    if db.execute("DELETE FROM ai_analysis_task WHERE id=?",(task_id,))==0: raise HTTPException(404,"AI 分析任务不存在")
    _publish_ai_event(request, "ai.task.deleted", task_id, status_value="CANCELED", message="已删除")
@router.post("/transcripts/{transcript_id}", status_code=202)
def create_ai_tasks(transcript_id:int,payload:AnalysisInput,request:Request,db:Database=Depends(database)):
    try: created,skipped=AIAnalysisQueueService(db,getattr(request.app.state,'event_hub',None)).create(transcript_id,payload.analysisTypes)
    except ValueError as exc: raise HTTPException(404,str(exc))
    return {"created":len(created),"taskIds":created,"skippedTypes":skipped}

@compat_router.get("/tasks/{task_id}/analyses")
def list_task_analyses(task_id: int, db: Database = Depends(database)):
    """兼容任务详情页，返回该转录任务已生成的分析结果。"""
    rows = db.fetch_all(
        "SELECT id, analysis_type, content, provider_name, model, status, created_at FROM ai_analysis WHERE task_id=? ORDER BY created_at DESC",
        (task_id,),
    )
    return [{"id": r["id"], "taskId": task_id, "analysisType": r["analysis_type"], "content": r["content"], "providerName": r["provider_name"], "model": r["model"], "status": r["status"], "createdAt": r["created_at"]} for r in rows]
