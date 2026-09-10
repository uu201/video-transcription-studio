"""导出文件下载 API。"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import database
from app.db.database import Database, utc_now

router = APIRouter(prefix="/api", tags=["导出"])


@router.post("/tasks/{task_id}/export")
def export_task(task_id: int, export_type: str = "txt", db: Database = Depends(database)) -> dict:
    """返回已生成的导出文件记录。"""
    row = db.fetch_one("SELECT id, file_path FROM export_record WHERE task_id = ? AND export_type = ? ORDER BY id DESC LIMIT 1", (task_id, export_type))
    if not row:
        raise HTTPException(404, "该任务尚未生成此格式的导出文件")
    return {"id": row["id"], "taskId": task_id, "type": export_type, "downloadUrl": f"/api/exports/{row['id']}/download"}


@router.get("/exports/{export_id}/download")
def download_export(export_id: int, type: str | None = None, db: Database = Depends(database)) -> FileResponse:
    """下载导出结果，拒绝不存在或目录外路径。"""
    if type:
        row = db.fetch_one("SELECT file_path, export_type FROM export_record WHERE task_id = ? AND export_type = ? ORDER BY id DESC LIMIT 1", (export_id, type))
    else:
        row = db.fetch_one("SELECT file_path, export_type FROM export_record WHERE id = ?", (export_id,))
    if not row or not Path(row["file_path"]).is_file():
        raise HTTPException(404, "导出文件不存在")
    return FileResponse(row["file_path"], filename=Path(row["file_path"]).name, media_type="text/plain; charset=utf-8")


@router.get("/tasks/{task_id}/download")
def download_task_export(task_id: int, type: str = "txt", db: Database = Depends(database)) -> FileResponse:
    """按任务和格式下载最近一次导出文件，方便详情页直接使用。"""
    row = db.fetch_one("SELECT file_path FROM export_record WHERE task_id = ? AND export_type = ? ORDER BY id DESC LIMIT 1", (task_id, type))
    if not row or not Path(row["file_path"]).is_file():
        raise HTTPException(404, "导出文件不存在")
    return FileResponse(row["file_path"], filename=Path(row["file_path"]).name, media_type="text/plain; charset=utf-8")


@router.get("/tasks/{task_id}/analyses")
def list_analyses(task_id: int, db: Database = Depends(database)) -> list[dict]:
    """预留 AI 分析结果接口。"""
    return [dict(row) for row in db.fetch_all("SELECT id, analysis_type AS analysisType, content, provider_name AS providerName, model, prompt_version AS promptVersion, status, created_at AS createdAt FROM ai_analysis WHERE task_id=? ORDER BY id", (task_id,))]
