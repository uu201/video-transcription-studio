"""应用内 FFmpeg/FFprobe 路径解析。"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from app.config import Settings
from app.domain.schemas import AppError


class MediaToolchain:
    """只从应用运行时目录或显式配置获取媒体工具。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    @classmethod
    def from_app_root(cls, settings: Settings | None = None) -> "MediaToolchain":
        """创建使用当前项目根目录的工具链。"""
        if settings is None:
            from app.config import load_settings
            settings = load_settings()
        return cls(settings)

    def _platform_dir(self) -> Path:
        """根据当前平台选择发布包目录。"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        if system == "windows":
            name = "windows-x64"
        elif system == "darwin":
            name = "macos-arm64" if "arm" in machine else "macos-x64"
        else:
            name = "linux-x64"
        return self.settings.root_dir / "runtime" / "ffmpeg" / name

    def _path(self, name: str) -> Path:
        """解析具体工具路径。"""
        directory = self.settings.ffmpeg_dir or self._platform_dir()
        suffix = ".exe" if platform.system().lower() == "windows" else ""
        return directory / f"{name}{suffix}"

    def ffmpeg_path(self) -> str:
        """返回 ffmpeg 路径。"""
        return str(self._path("ffmpeg"))

    def ffprobe_path(self) -> str:
        """返回 ffprobe 路径。"""
        return str(self._path("ffprobe"))

    def check(self) -> None:
        """检查应用内工具；开发环境允许通过环境变量覆盖。"""
        missing = [str(path) for path in (self._path("ffmpeg"), self._path("ffprobe")) if not path.is_file()]
        if missing:
            raise AppError(
                code="MEDIA_TOOLS_MISSING",
                user_message="应用内 FFmpeg 工具不可用",
                detail="、".join(missing),
                retryable=False,
                user_action="将 ffmpeg 和 ffprobe 放入 runtime/ffmpeg 对应平台目录，或配置 VIDEO_TEXT_FFMPEG_DIR",
            )
        for executable in (self.ffmpeg_path(), self.ffprobe_path()):
            try:
                subprocess.run([executable, "-version"], capture_output=True, timeout=5, check=True)
            except (OSError, subprocess.SubprocessError) as exc:
                raise AppError("MEDIA_TOOLS_INVALID", "媒体工具无法执行", str(exc), False, "检查文件权限和平台版本") from exc
