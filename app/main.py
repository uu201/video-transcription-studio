"""更新后的 FastAPI 应用入口，支持 Vite 构建的前端。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.exports import router as exports_router
from app.api.analyses import router as analyses_router
from app.api.scan_sources import router as sources_router
from app.api.tasks import router as tasks_router
from app.api.transfers import router as transfers_router
from app.config import load_settings
from app.db.database import Database
from app.services.scanner import Scanner
from app.services.environment import EnvironmentChecker
from app.services.realtime import TaskEventHub
from app.web.views import router as web_router
from app.workers.worker import TaskWorkerPool
from app.exceptions import AppException
from app.error_handlers import app_exception_handler, generic_exception_handler
from app.runtime_check import ensure_supported_runtime

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 实例。"""
    ensure_supported_runtime()
    settings = load_settings()
    database = Database(settings.database_path)
    database.migrate()
    scanner = Scanner(database)
    event_hub = TaskEventHub()

    # 使用多 Worker 池，默认 2 个 Worker
    worker_count = getattr(settings, 'worker_count', 2)
    worker_pool = TaskWorkerPool(settings, database, event_hub, worker_count=worker_count)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用启动数据库和后台 Worker，退出时停止 Worker。"""
        worker_pool.start()
        yield
        worker_pool.stop()

    application = FastAPI(title="视频转文案工作台", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.database = database
    application.state.scanner = scanner
    application.state.worker = worker_pool
    application.state.event_hub = event_hub

    # 挂载静态文件
    static_dir = Path(__file__).parent / "static"

    # Vite 构建产物
    dist_dir = static_dir / "dist"
    if dist_dir.exists():
        application.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    # 传统静态文件（如果需要）
    if (static_dir / "js").exists():
        application.mount("/static", StaticFiles(directory=static_dir), name="static")

    # API 路由
    application.include_router(sources_router)
    application.include_router(tasks_router)
    application.include_router(exports_router)
    application.include_router(analyses_router)
    application.include_router(transfers_router)

    # 注册全局异常处理器
    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    @application.get("/api/health", tags=["系统"])
    def health() -> dict:
        """仅检查 Web 与 SQLite。"""
        database.fetch_one("SELECT 1")
        return {"status": "ok", "database": "ok"}

    @application.get("/api/system/info", tags=["系统"])
    def system_info(response: Response) -> dict:
        """返回非敏感运行信息。"""
        from app.services.asr.sensevoice_provider import SenseVoiceProvider
        # 设置缓存头：10 分钟
        response.headers["Cache-Control"] = "public, max-age=600"
        return {
            "python": __import__("sys").version.split()[0],
            "root": str(settings.root_dir),
            "asrModel": settings.asr_model,
            "asrDevice": settings.asr_device,
            "funasr": SenseVoiceProvider.dependency_status(),
            "modelDir": str(settings.model_dir),
        }

    @application.post("/api/system/check-media-tools", tags=["系统"])
    def check_media_tools(response: Response) -> dict:
        """检查应用内 FFmpeg。"""
        from app.services.media_toolchain import MediaToolchain
        try:
            toolchain = MediaToolchain.from_app_root(settings)
            toolchain.check()
            result = {"available": True, "ffmpeg": toolchain.ffmpeg_path(), "ffprobe": toolchain.ffprobe_path()}
            response.headers["Cache-Control"] = "public, max-age=300"
            return result
        except Exception as exc:
            return {"available": False, "message": str(exc)}

    @application.get("/api/system/environment", tags=["系统"])
    def environment(response: Response, force: bool = False) -> dict:
        """检测首页展示的本地开发与运行环境。"""
        result = EnvironmentChecker(settings, database).check(use_cache=not force)
        # 设置缓存头：5 分钟
        response.headers["Cache-Control"] = "public, max-age=300"
        response.headers["X-Cache-Status"] = "HIT" if not force else "MISS"
        return result

    @application.websocket("/ws/tasks")
    async def task_events(websocket: WebSocket) -> None:
        """推送 Worker 的实时阶段事件，供任务列表和详情页共用。"""
        await websocket.accept()
        subscriber = event_hub.subscribe()
        try:
            await websocket.send_json({"type": "connected", "message": "任务实时通道已连接"})
            snapshot = database.fetch_all("SELECT t.id, t.status, t.current_stage AS stage, t.progress, t.message, m.file_name AS fileName FROM processing_task t JOIN media_file m ON m.id = t.media_file_id ORDER BY t.created_at DESC LIMIT 100")
            await websocket.send_json({"type": "task.snapshot", "tasks": [dict(row) for row in snapshot]})
            while True:
                payload = await __import__("asyncio").to_thread(event_hub.wait, subscriber, 2)
                if payload is None:
                    await websocket.send_json({"type": "ping"})
                else:
                    await websocket.send_json(payload)
        except WebSocketDisconnect:
            pass
        finally:
            event_hub.unsubscribe(subscriber)

    # 前端路由 - 返回 index.html（用于 Vue Router history 模式）
    @application.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """为 SPA 提供前端入口，支持 Vue Router history 模式。"""
        # API 路由已经被处理，这里只处理前端路由
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return {"error": "Not found"}, 404

        index_file = dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        # 如果 dist 不存在，尝试返回旧版模板
        old_template = Path(__file__).parent / "templates" / "workspace.html"
        if old_template.exists():
            return FileResponse(old_template)

        return {"error": "Frontend not built. Run: cd frontend && npm run build"}

    return application


app = create_app()
