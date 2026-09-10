"""应用配置加载与路径管理。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Settings:
    """集中保存运行时配置，避免业务模块直接读取环境变量。"""

    root_dir: Path
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: Path = Path("data/video_content.db")
    result_dir: Path = Path("data/results")
    cache_dir: Path = Path("data/cache")
    model_dir: Path = Path("data/models")
    log_dir: Path = Path("data/logs")
    poll_interval_seconds: float = 2.0
    stale_task_timeout_seconds: int = 1800
    max_concurrency: int = 1
    worker_count: int = 2  # 并发 Worker 数量
    ffmpeg_dir: Path | None = None
    asr_model: str = "iic/SenseVoiceSmall"
    asr_device: str = "cpu"
    asr_language: str = "auto"
    asr_use_itn: bool = True
    asr_batch_size_s: int = 30
    asr_merge_length_s: int = 15
    asr_max_segment_ms: int = 30000
    ai_enabled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def resolve(self, value: str | Path) -> Path:
        """将相对路径解析到项目根目录。"""
        path = Path(value).expanduser()
        return path if path.is_absolute() else self.root_dir / path

    def prepare_directories(self) -> None:
        """创建应用运行所需目录。"""
        for path in (self.database_path.parent, self.result_dir, self.cache_dir, self.model_dir, self.log_dir):
            path.mkdir(parents=True, exist_ok=True)


def _as_bool(value: Any, default: bool) -> bool:
    """兼容 YAML、环境变量中的布尔值。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_settings(root_dir: Path | None = None) -> Settings:
    """按默认值、YAML、环境变量顺序加载配置。"""
    root = (root_dir or Path(__file__).resolve().parents[1]).resolve()
    config_path = Path(os.getenv("VIDEO_TEXT_CONFIG", str(root / "config" / "app.yaml")))
    raw: dict[str, Any] = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    server = raw.get("server", {})
    database = raw.get("database", {})
    paths = raw.get("paths", {})
    worker = raw.get("worker", {})
    media = raw.get("media", {}).get("ffmpeg", {})
    asr = raw.get("asr", {})
    ai = raw.get("ai", {})
    settings = Settings(
        root_dir=root,
        host=os.getenv("VIDEO_TEXT_SERVER_HOST", server.get("host", "127.0.0.1")),
        port=int(os.getenv("VIDEO_TEXT_SERVER_PORT", server.get("port", 8000))),
        database_path=Path(os.getenv("VIDEO_TEXT_DATABASE_URL", database.get("path", "data/video_content.db")).replace("sqlite:///", "")),
        result_dir=Path(paths.get("result_dir", "data/results")),
        cache_dir=Path(paths.get("cache_dir", "data/cache")),
        model_dir=Path(os.getenv("VIDEO_TEXT_MODEL_DIR", paths.get("model_dir", "data/models"))),
        log_dir=Path(paths.get("log_dir", "data/logs")),
        poll_interval_seconds=float(worker.get("poll_interval_seconds", 2)),
        stale_task_timeout_seconds=int(worker.get("stale_task_timeout_seconds", 1800)),
        max_concurrency=int(worker.get("max_concurrency", 1)),
        worker_count=int(os.getenv("VIDEO_TEXT_WORKER_COUNT", worker.get("worker_count", 2))),
        ffmpeg_dir=Path(os.getenv("VIDEO_TEXT_FFMPEG_DIR")) if os.getenv("VIDEO_TEXT_FFMPEG_DIR") else (Path(media["external_dir"]) if media.get("external_dir") else None),
        asr_model=asr.get("model", "iic/SenseVoiceSmall"),
        asr_device=asr.get("device", "cpu"),
        asr_language=asr.get("language", "auto"),
        asr_use_itn=_as_bool(asr.get("use_itn"), True),
        asr_batch_size_s=int(asr.get("batch_size_s", 30)),
        asr_merge_length_s=int(asr.get("merge_length_s", 15)),
        asr_max_segment_ms=int(asr.get("max_single_segment_time_ms", 30000)),
        ai_enabled=_as_bool(ai.get("enabled"), False),
        extra=raw,
    )
    settings.database_path = settings.resolve(settings.database_path)
    settings.result_dir = settings.resolve(settings.result_dir)
    settings.cache_dir = settings.resolve(settings.cache_dir)
    settings.model_dir = settings.resolve(settings.model_dir)
    settings.log_dir = settings.resolve(settings.log_dir)
    if settings.ffmpeg_dir and not settings.ffmpeg_dir.is_absolute():
        settings.ffmpeg_dir = settings.resolve(settings.ffmpeg_dir)
    settings.prepare_directories()
    return settings
