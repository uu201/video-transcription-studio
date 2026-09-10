"""跨层传输的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ASRSegment:
    """单个带时间戳的识别分段。"""

    sequence: int
    start: float
    end: float
    text: str
    speaker: str | None = None
    confidence: float | None = None


@dataclass
class ASRResult:
    """ASR Provider 的统一结果。"""

    language: str | None
    text: str
    segments: list[ASRSegment]
    raw_result: list[dict[str, Any]]


@dataclass
class MediaInfo:
    """FFprobe 返回的媒体摘要。"""

    duration: float | None = None
    width: int | None = None
    height: int | None = None
    audio_streams: int = 0
    video_streams: int = 0
    format_name: str | None = None


@dataclass
class AppError(Exception):
    """面向用户的统一错误，保留可重试和建议动作。"""

    code: str
    user_message: str
    detail: str | None = None
    retryable: bool = False
    user_action: str | None = None

    def __str__(self) -> str:
        """返回不包含堆栈的简短错误。"""
        return self.user_message


@dataclass
class ScanResult:
    """目录扫描统计。"""

    discovered: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
