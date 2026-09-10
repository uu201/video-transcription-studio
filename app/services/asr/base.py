"""ASR Provider 抽象接口。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from app.domain.schemas import ASRResult


class ASRProvider(Protocol):
    """将一个音频文件转换成统一识别结果。"""

    def transcribe(self, audio_path: Path, language: str, options: dict[str, Any]) -> ASRResult:
        """执行识别。"""
        ...
