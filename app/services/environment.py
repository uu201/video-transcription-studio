"""本地运行环境检测服务。"""

from __future__ import annotations

import platform
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import Settings
from app.db.database import Database
from app.services.asr.sensevoice_provider import SenseVoiceProvider
from app.services.media_toolchain import MediaToolchain


class EnvironmentCache:
    """环境检测结果缓存，避免频繁检测。"""

    _cache: dict[str, Any] | None = None
    _cached_at: datetime | None = None
    _ttl_seconds: int = 300  # 默认 5 分钟缓存

    @classmethod
    def get(cls, ttl_seconds: int = 300) -> dict[str, Any] | None:
        """获取缓存的环境检测结果。"""
        cls._ttl_seconds = ttl_seconds
        if cls._cache is None or cls._cached_at is None:
            return None

        elapsed = (datetime.now() - cls._cached_at).total_seconds()
        if elapsed > cls._ttl_seconds:
            return None

        return cls._cache

    @classmethod
    def set(cls, result: dict[str, Any]) -> None:
        """缓存环境检测结果。"""
        cls._cache = result
        cls._cached_at = datetime.now()

    @classmethod
    def clear(cls) -> None:
        """清除缓存，强制重新检测。"""
        cls._cache = None
        cls._cached_at = None


class EnvironmentChecker:
    """检测启动、媒体处理和 ASR 所需的本地能力。"""

    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.toolchain = MediaToolchain.from_app_root(settings)

    @staticmethod
    def _writable_directory(path: Path) -> tuple[bool, str]:
        """检查目录是否可创建并写入临时探针文件。"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".environment-check"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True, str(path)
        except OSError as exc:
            return False, f"{path}: {exc}"

    @staticmethod
    def _executable(path: str) -> tuple[bool, str]:
        """检查媒体工具是否存在且可以执行。"""
        executable = Path(path)
        if not executable.is_file():
            return False, f"文件不存在：{executable}"
        try:
            result = subprocess.run([str(executable), "-version"], capture_output=True, timeout=5, check=False)
            if result.returncode != 0:
                return False, f"无法执行：{executable}"
            first_line = result.stdout.decode(errors="replace").splitlines()[0] if isinstance(result.stdout, bytes) and result.stdout else "可执行"
            return True, first_line[:120]
        except (OSError, subprocess.SubprocessError) as exc:
            return False, str(exc)

    def check(self, use_cache: bool = True) -> dict[str, Any]:
        """返回适合首页展示的环境检测结果。"""
        # 尝试从缓存获取
        if use_cache:
            cached = EnvironmentCache.get(ttl_seconds=300)
            if cached is not None:
                return cached

        items: list[dict[str, Any]] = []

        items.append({"key": "python", "label": "Python 运行时", "status": "ok", "value": platform.python_version(), "detail": sys.executable})

        funasr = SenseVoiceProvider.dependency_status()
        items.append({
            "key": "funasr",
            "label": "FunASR 依赖",
            "status": "ok" if funasr["installed"] else "error",
            "value": f"v{funasr['version']}" if funasr["installed"] else "未安装",
            "detail": "可加载 SenseVoice" if funasr["installed"] else "执行 python -m pip install -r requirements.txt",
        })

        for key, label, path in (("ffmpeg", "FFmpeg", self.toolchain.ffmpeg_path()), ("ffprobe", "FFprobe", self.toolchain.ffprobe_path())):
            available, detail = self._executable(path)
            items.append({"key": key, "label": label, "status": "ok" if available else "error", "value": "可用" if available else "缺失", "detail": detail})

        database_ok = False
        database_detail = ""
        try:
            self.database.fetch_one("SELECT 1")
            database_ok = True
            database_detail = str(self.settings.database_path)
        except Exception as exc:  # pragma: no cover - 由运行环境决定
            database_detail = str(exc)
        items.append({"key": "database", "label": "SQLite 数据库", "status": "ok" if database_ok else "error", "value": "已连接" if database_ok else "不可用", "detail": database_detail})

        writable, writable_detail = self._writable_directory(self.settings.model_dir)
        items.append({"key": "modelDir", "label": "模型目录", "status": "ok" if writable else "error", "value": "可写" if writable else "不可写", "detail": writable_detail})

        # ModelScope 在不同版本中可能把模型放到 model_dir 或 model_dir/models，
        # 同时兼容用户目录缓存，避免下载过程中页面显示错误状态。
        model_cache_roots = [self.settings.model_dir, self.settings.model_dir / "models"]
        user_cache_value = os.getenv("MODELSCOPE_CACHE")
        if user_cache_value:
            model_cache_roots.append(Path(user_cache_value))
        model_cache_roots.append(Path.home() / ".cache" / "modelscope" / "hub" / "models")

        def model_state(model_name: str, label: str) -> dict[str, Any]:
            """检查模型权重和 ModelScope 临时下载目录。"""
            parts = model_name.split("/")
            candidates = [root.joinpath(*parts) for root in model_cache_roots]
            existing = next((path for path in candidates if path.is_dir()), None)
            complete = next((path for path in candidates if (path / "model.pt").is_file()), None)
            if complete:
                size_bytes = (complete / "model.pt").stat().st_size
                size_text = f"{size_bytes / (1024 ** 3):.2f} GB" if size_bytes >= 100 * 1024 ** 2 else f"{size_bytes / (1024 ** 2):.1f} MB"
                return {"key": model_name, "label": label, "status": "ok", "value": "已下载", "detail": f"{size_text} · {complete}"}
            downloading = any((root.joinpath("._____temp", *parts)).exists() for root in model_cache_roots)
            if downloading or existing:
                return {"key": model_name, "label": label, "status": "warn", "value": "下载中" if downloading else "未完成", "detail": str(existing or candidates[0])}
            return {"key": model_name, "label": label, "status": "warn", "value": "未下载", "detail": f"首次识别时下载到 {candidates[0]}"}

        items.append(model_state(self.settings.asr_model, "SenseVoiceSmall 模型"))
        items.append(model_state("iic/speech_fsmn_vad_zh-cn-16k-common-pytorch", "FSMN-VAD 模型"))

        try:
            import torch
            cuda = bool(torch.cuda.is_available())
            items.append({"key": "cuda", "label": "GPU 加速", "status": "ok" if cuda else "warn", "value": torch.cuda.get_device_name(0) if cuda else "使用 CPU", "detail": "CUDA 可用" if cuda else "未检测到 CUDA，CPU 模式可继续使用"})
        except Exception as exc:
            items.append({"key": "cuda", "label": "GPU 加速", "status": "warn", "value": "使用 CPU", "detail": str(exc)})

        required = {item["status"] for item in items if item["key"] != "cuda"}
        overall = "ok" if required == {"ok"} else "attention"
        result = {"overall": overall, "checkedAt": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"), "items": items}

        # 缓存检测结果
        EnvironmentCache.set(result)
        return result
