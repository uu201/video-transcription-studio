"""FastAPI 应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.exports import router as exports_router
from app.api.analyses import router as analyses_router
from app.api.scan_sources import router as sources_router
from app.api.tasks import router as tasks_router
from app.api.transfers import router as transfers_router
from app.config import load_settings
from app.db.database import Database
from app.services.scanner import Scanner
from app.web.views import router as web_router
from app.workers.worker import TaskWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 实例。"""
    settings = load_settings()
    database = Database(settings.database_path)
    database.migrate()
    scanner = Scanner(database)
    worker = TaskWorker(settings, database)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用启动数据库和后台 Worker，退出时停止 Worker。"""
        worker.start()
        yield
        worker.stop()

    application = FastAPI(title="视频转文案工作台", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.database = database
    application.state.scanner = scanner
    application.state.worker = worker
    static_dir = Path(__file__).parent / "static"
    application.mount("/static", StaticFiles(directory=static_dir), name="static")
    application.include_router(web_router)
    application.include_router(sources_router)
    application.include_router(tasks_router)
    application.include_router(exports_router)
    application.include_router(analyses_router)
    application.include_router(transfers_router)

    @application.get("/api/health", tags=["系统"])
    def health() -> dict:
        """仅检查 Web 与 SQLite。"""
        database.fetch_one("SELECT 1")
        return {"status": "ok", "database": "ok"}

    @application.get("/api/system/info", tags=["系统"])
    def system_info() -> dict:
        """返回非敏感运行信息。"""
        return {"python": __import__("sys").version.split()[0], "root": str(settings.root_dir), "asrModel": settings.asr_model, "asrDevice": settings.asr_device}

    @application.post("/api/system/check-media-tools", tags=["系统"])
    def check_media_tools() -> dict:
        """检查应用内 FFmpeg。"""
        from app.services.media_toolchain import MediaToolchain
        try:
            toolchain = MediaToolchain.from_app_root(settings)
            toolchain.check()
            return {"available": True, "ffmpeg": toolchain.ffmpeg_path(), "ffprobe": toolchain.ffprobe_path()}
        except Exception as exc:
            return {"available": False, "message": str(exc)}

    return application


app = create_app()
