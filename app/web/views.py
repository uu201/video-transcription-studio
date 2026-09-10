"""Jinja2 页面视图。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.dependencies import database
from app.db.database import Database

templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).resolve().parents[1] / "templates"))
router = APIRouter(tags=["页面"])


def _prototype_page(initial_tab: str = "overview", task_id: int | None = None) -> HTMLResponse:
    """返回 Vue 单页应用，并注入真实页面路由状态。"""
    prototype_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "templates" / "workspace.html"
    html = prototype_path.read_text(encoding="utf-8")
    # 原型自带的是演示数据脚本，替换为连接真实 API/WebSocket 的工作区脚本。
    script_marker = "\n  <script>\n    const { createApp, ref, computed, onMounted } = Vue;"
    script_start = html.find(script_marker)
    body_end = html.rfind("</body>")
    if script_start >= 0 and body_end > script_start:
        # 设置页的模型卡片也绑定实时检测结果，避免继续显示原型中的固定演示状态。
        html = html.replace('type="success">就绪 100%</el-tag>', ':type="envData.senseVoice.ok ? \'success\' : \'warning\'">{{ envData.senseVoice.status || \'未检测\' }}</el-tag>', 1)
        html = html.replace('type="success">就绪 100%</el-tag>', ':type="envData.vad.ok ? \'success\' : \'warning\'">{{ envData.vad.status || \'未检测\' }}</el-tag>', 1)
        # 前面的模板替换会改变字符串长度，因此重新计算脚本结束位置。
        script_start = html.find(script_marker)
        body_end = html.rfind("</body>")
        html = html[:script_start] + "\n  <script>\n    window.__INITIAL_STATE__ = " + __import__("json").dumps({"tab": initial_tab, "taskId": task_id}, ensure_ascii=False) + ";\n  </script>\n  <script src=\"/static/js/workspace.js\"></script>\n" + html[body_end:]
    return HTMLResponse(html)


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染首页概览。"""
    return _prototype_page("overview")


@router.get("/scan-sources", response_class=HTMLResponse)
def scan_sources_page(request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染扫描源管理页。"""
    return _prototype_page("sources")


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染任务列表页。"""
    return _prototype_page("tasks")


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail_page(task_id: int, request: Request, db: Database = Depends(database)) -> HTMLResponse:
    """渲染任务详情页。"""
    return _prototype_page("task-detail", task_id)


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    """渲染设置页。"""
    return _prototype_page("settings")
