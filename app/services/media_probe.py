"""使用 FFprobe 读取媒体摘要。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.domain.schemas import AppError, MediaInfo
from app.services.media_toolchain import MediaToolchain


class MediaProbe:
    """媒体探测器，不向页面暴露 FFprobe 原始输出。"""

    def __init__(self, toolchain: MediaToolchain):
        self.toolchain = toolchain

    def inspect(self, media_path: Path) -> MediaInfo:
        """读取视频流、音频流和时长。"""
        command = [
            self.toolchain.ffprobe_path(), "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(media_path),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AppError("MEDIA_PROBE_FAILED", "读取媒体信息失败", str(exc), True, "检查文件是否可访问后重试") from exc
        if result.returncode != 0:
            raise AppError("MEDIA_PROBE_FAILED", "读取媒体信息失败", result.stderr[-2000:], True, "确认文件没有损坏后重试")
        try:
            payload = json.loads(result.stdout)
            streams = payload.get("streams", [])
            format_info = payload.get("format", {})
            video = next((item for item in streams if item.get("codec_type") == "video"), {})
            return MediaInfo(
                duration=float(format_info["duration"]) if format_info.get("duration") else None,
                width=int(video["width"]) if video.get("width") else None,
                height=int(video["height"]) if video.get("height") else None,
                audio_streams=sum(1 for item in streams if item.get("codec_type") == "audio"),
                video_streams=sum(1 for item in streams if item.get("codec_type") == "video"),
                format_name=format_info.get("format_name"),
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise AppError("MEDIA_PROBE_FAILED", "媒体信息格式无法解析", str(exc), True, "确认文件由支持的媒体格式编码") from exc
