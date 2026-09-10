"""AI 分析 API 兼容入口。"""

from fastapi import APIRouter, Depends

from app.api.dependencies import database
from app.db.database import Database

router = APIRouter(prefix="/api", tags=["AI 分析"])


@router.post("/tasks/{task_id}/analyses")
def create_analysis(task_id: int, db: Database = Depends(database)) -> dict:
    """预留 AI 分析任务接口，当前明确返回未启用状态。"""
    exists = db.fetch_one("SELECT id FROM processing_task WHERE id=?", (task_id,))
    return {"taskId": task_id, "status": "DISABLED", "message": "AI Provider 尚未启用"} if exists else {"taskId": task_id, "status": "NOT_FOUND"}


@router.post("/analyses/{analysis_id}/retry")
def retry_analysis(analysis_id: int) -> dict:
    """预留 AI 分析重试接口。"""
    return {"id": analysis_id, "status": "DISABLED", "message": "AI Provider 尚未启用"}
