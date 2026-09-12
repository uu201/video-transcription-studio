"""AI 分析队列 API。"""
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
    return {"id": row["id"], "fileName": row["file_name"], "transcriptId": row["transcript_id"], "analysisType": row["analysis_type"], "status": row["status"], "progress": row["progress"], "message": row["message"], "pauseRequested": bool(row["pause_requested"]), "cancelRequested": bool(row["cancel_requested"]), "providerName": row["provider_name"], "model": row["model"], "resultId": row["result_id"], "error": {"code": row["error_code"], "message": row["error_message"], "detail": row["error_detail"], "retryable": bool(row["retryable"])} if row["error_code"] else None, "createdAt": row["created_at"], "updatedAt": row["updated_at"], "finishedAt": row["finished_at"]}
@router.get("/tasks")
def list_ai_tasks(status_filter: str | None = Query(None, alias="status"), limit: int = Query(100, ge=1, le=500), db: Database = Depends(database)): return [_item(r) for r in AIAnalysisTaskRepository(db).list(status_filter, limit)]
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
    repo.update(task_id,status='QUEUED',progress=0,message='等待分析',error_code=None,error_message=None,error_detail=None,retryable=0,cancel_requested=0,worker_id=None,started_at=None,finished_at=None)
    return get_ai_task(task_id,db)
@router.post("/tasks/{task_id}/cancel")
def cancel_ai_task(task_id: int, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status']=='QUEUED': repo.update(task_id,status='CANCELED',message='已取消',finished_at=utc_now())
    elif row['status']=='RUNNING': repo.update(task_id,cancel_requested=1,message='正在取消')
    else: raise HTTPException(409, "当前状态不允许取消")
    return get_ai_task(task_id,db)
@router.post("/tasks/{task_id}/start")
def start_ai_task(task_id: int, request: Request, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status'] not in ('PAUSED','FAILED','CANCELED'): raise HTTPException(409, "当前状态不允许开始")
    repo.update(task_id,status='QUEUED',progress=0,message='等待分析',error_code=None,error_message=None,error_detail=None,retryable=0,cancel_requested=0,pause_requested=0,worker_id=None,started_at=None,finished_at=None)
    return get_ai_task(task_id,db)
@router.post("/tasks/{task_id}/pause")
def pause_ai_task(task_id: int, db: Database = Depends(database)):
    repo=AIAnalysisTaskRepository(db); row=repo.get(task_id)
    if not row: raise HTTPException(404, "AI 分析任务不存在")
    if row['status']=='QUEUED': repo.update(task_id,status='PAUSED',pause_requested=1,message='已暂停')
    elif row['status']=='RUNNING': repo.update(task_id,pause_requested=1,message='正在等待暂停')
    else: raise HTTPException(409, "当前状态不允许暂停")
    return get_ai_task(task_id,db)
@router.delete("/tasks/{task_id}", status_code=204)
def delete_ai_task(task_id: int, db: Database = Depends(database)):
    if db.execute("DELETE FROM ai_analysis_task WHERE id=?",(task_id,))==0: raise HTTPException(404,"AI 分析任务不存在")
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
