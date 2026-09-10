"""独立 SenseVoice/FunASR 适配器，不依赖 video_to_text.py。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import Settings
from app.domain.schemas import ASRResult, ASRSegment, AppError

LOGGER = logging.getLogger(__name__)


class SenseVoiceProvider:
    """延迟加载 SenseVoiceSmall，屏蔽 FunASR 返回格式差异。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """首次识别时加载模型，避免首页启动依赖模型包。"""
        if self._model is not None:
            return self._model
        try:
            from funasr import AutoModel
        except ImportError as exc:
            raise AppError("ASR_DEPENDENCY_MISSING", "语音识别依赖未安装", str(exc), False, "执行 pip install -r requirements.txt") from exc
        try:
            self._model = AutoModel(
                model=self.settings.asr_model,
                trust_remote_code=True,
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": self.settings.asr_max_segment_ms},
                device=self.settings.asr_device,
                disable_pbar=True,
                disable_log=True,
                disable_update=True,
            )
        except Exception as exc:
            raise AppError("ASR_MODEL_LOAD_FAILED", "语音识别模型加载失败", repr(exc), True, "检查模型目录、网络或切换到 CPU 后重试") from exc
        return self._model

    @staticmethod
    def _milliseconds(value: Any) -> float:
        """将 FunASR 常见的毫秒/秒时间戳转成秒。"""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return number / 1000 if number > 1000 else number

    def transcribe(self, audio_path: Path, language: str, options: dict[str, Any]) -> ASRResult:
        """调用模型并解析文本、时间戳和完整原始结果。"""
        model = self._load_model()
        try:
            generated = model.generate(
                input=str(audio_path), cache={}, language=language,
                use_itn=options.get("use_itn", self.settings.asr_use_itn),
                batch_size_s=options.get("batch_size_s", self.settings.asr_batch_size_s),
                merge_vad=True, merge_length_s=options.get("merge_length_s", self.settings.asr_merge_length_s),
            )
        except Exception as exc:
            raise AppError("ASR_INFERENCE_FAILED", "语音识别失败", repr(exc), True, "检查音频格式或切换到 CPU 后重试") from exc
        raw = [] if generated is None else [generated] if isinstance(generated, dict) else list(generated)
        segments: list[ASRSegment] = []
        texts: list[str] = []
        try:
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
        except ImportError:
            rich_transcription_postprocess = lambda value: value
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "") or "")
            text = str(rich_transcription_postprocess(text)).strip()
            if text:
                texts.append(text)
            timestamp = item.get("timestamp") or item.get("timestamps") or []
            start = end = 0.0
            if isinstance(timestamp, list) and timestamp:
                first = timestamp[0]
                last = timestamp[-1]
                if isinstance(first, (list, tuple)):
                    start = self._milliseconds(first[0])
                if isinstance(last, (list, tuple)) and len(last) > 1:
                    end = self._milliseconds(last[1])
            start = self._milliseconds(item.get("start", start))
            end = self._milliseconds(item.get("end", end)) or start
            segments.append(ASRSegment(index, start, end, text, item.get("spk"), item.get("confidence")))
        return ASRResult(language, "\n".join(texts), segments, raw)
