"""使用 FFmpeg 抽取 16kHz 单声道 WAV。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.domain.schemas import AppError
from app.services.media_toolchain import MediaToolchain


class AudioExtractor:
    """媒体音频准备服务。"""

    AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".weba", ".wma"}

    def __init__(self, toolchain: MediaToolchain, cache_dir: Path):
        self.toolchain = toolchain
        self.cache_dir = cache_dir

    def prepare(self, media_path: Path, task_id: int) -> Path:
        """为任务创建隔离临时目录并返回 WAV 路径。"""
        task_dir = self.cache_dir / "audio" / str(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        output = task_dir / "audio.wav"
        if media_path.suffix.lower() in self.AUDIO_EXTENSIONS:
            return media_path
        command = [self.toolchain.ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(media_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(output)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AppError("FFMPEG_FAILED", "提取音频失败", str(exc), True, "确认媒体文件可读取后重试") from exc
        if result.returncode != 0 or not output.exists():
            raise AppError("FFMPEG_FAILED", "提取音频失败", result.stderr[-3000:], True, "检查文件是否包含可用音轨")
        return output

    def cleanup(self, task_id: int) -> None:
        """清理任务专属临时音频。"""
        directory = self.cache_dir / "audio" / str(task_id)
        if directory.exists():
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink(missing_ok=True)
            directory.rmdir()
