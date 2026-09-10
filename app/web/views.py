"""Jinja2 页面视图。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.dependencies import database
from app.db.database import Database

templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["页面"])


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染首页概览。"""
    counts = {row["status"]: row["count"] for row in db.fetch_all("SELECT status, COUNT(*) AS count FROM processing_task GROUP BY status")}
    recent = db.fetch_all("SELECT t.*, m.file_name FROM processing_task t JOIN media_file m ON m.id=t.media_file_id ORDER BY t.created_at DESC LIMIT 8")
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"counts": counts, "recent": recent, "active": "dashboard"},
    )


@router.get("/scan-sources", response_class=HTMLResponse)
def scan_sources_page(request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染扫描源管理页。"""
    return templates.TemplateResponse(
        request=request,
        name="scan_sources.html",
        context={"sources": db.fetch_all("SELECT * FROM scan_source ORDER BY id DESC"), "active": "sources"},
    )


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染任务列表页。"""
    rows = db.fetch_all("SELECT t.*, m.file_name FROM processing_task t JOIN media_file m ON m.id=t.media_file_id ORDER BY t.created_at DESC")
    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={"tasks": rows, "active": "tasks"},
    )


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail_page(task_id: int, request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染任务详情页。"""
    task = db.fetch_one("SELECT t.*, m.file_name, m.path, m.media_info_json FROM processing_task t JOIN media_file m ON m.id=t.media_file_id WHERE t.id=?", (task_id,))
    if not task:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "任务不存在"},
            status_code=404,
        )
    transcript = db.fetch_one("SELECT * FROM transcript WHERE task_id=?", (task_id,))
    segments = db.fetch_all("SELECT s.* FROM transcript_segment s JOIN transcript t ON t.id=s.transcript_id WHERE t.task_id=? ORDER BY s.sequence", (task_id,))
    events = db.fetch_all("SELECT * FROM task_event WHERE task_id=? ORDER BY created_at", (task_id,))
    return templates.TemplateResponse(
        request=request,
        name="task_detail.html",
        context={"task": task, "transcript": transcript, "segments": segments, "events": events, "active": "tasks"},
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    """渲染设置页。"""
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"active": "settings"},
    )
