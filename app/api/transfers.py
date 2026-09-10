"""文件转移 API 兼容入口。"""

from fastapi import APIRouter, Depends

from app.api.dependencies import database
from app.db.database import Database

router = APIRouter(prefix="/api", tags=["文件转移"])


@router.get("/tasks/{task_id}/transfers")
def list_transfers(task_id: int, db: Database = Depends(database)) -> list[dict]:
    """返回任务的归档记录。"""
    return [dict(row) for row in db.fetch_all("SELECT * FROM file_transfer WHERE task_id=? ORDER BY id", (task_id,))]


@router.post("/transfers/{transfer_id}/retry")
def retry_transfer(transfer_id: int) -> dict:
    """预留文件转移重试接口。"""
    return {"id": transfer_id, "status": "PENDING"}
