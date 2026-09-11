"""独立 SenseVoice/FunASR 适配器，不依赖 video_to_text.py。"""

from __future__ import annotations

import json
import logging
import os
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

        # 将模型缓存固定到项目目录，避免模型散落在用户目录且难以备份。
        # 关键：设置环境变量必须在导入 funasr 之前
        # 对于 Windows 中文路径，需要确保使用正确的编码
        cache_dir = str(self.settings.model_dir.resolve())
        os.environ["MODELSCOPE_CACHE"] = cache_dir
        os.environ["HF_HOME"] = str(self.settings.model_dir.resolve() / "huggingface")
        os.environ["MODELSCOPE_MODULES_CACHE"] = cache_dir

        # 对于 Windows 系统，设置环境变量确保路径编码正确
        if os.name == 'nt':
            import sys
            # 确保 Python 使用 UTF-8 处理文件系统路径
            if sys.getfilesystemencoding().lower() != 'utf-8':
                LOGGER.warning(f"文件系统编码为 {sys.getfilesystemencoding()}，可能导致中文路径问题")

        try:
            from funasr import AutoModel
        except ImportError as exc:
            raise AppError(
                "ASR_DEPENDENCY_MISSING",
                "当前 Python 环境没有安装 FunASR",
                str(exc),
                True,
                "请在启动服务的同一个虚拟环境中执行 python -m pip install -r requirements.txt，然后重试任务",
            ) from exc

        try:
            # 检查正确位置和嵌套位置的模型
            local_model_path = self.settings.model_dir / "iic" / "SenseVoiceSmall"
            nested_model_path = self.settings.model_dir / "models" / "iic" / "SenseVoiceSmall"
            snapshot_root = self.settings.model_dir / "models" / self.settings.asr_model.replace("/", "--") / "snapshots"

            # 优先使用正确位置的模型
            if local_model_path.exists() and (local_model_path / "model.pt").exists():
                # 将路径转换为绝对路径并使用 resolve() 规范化
                # 对于 Windows 上的中文路径，使用短路径格式可以避免某些编码问题
                model_path = str(local_model_path.resolve())
                LOGGER.info(f"使用本地模型: {model_path}")
            # 如果嵌套位置有完整模型，先移动到正确位置再使用
            elif nested_model_path.exists() and (nested_model_path / "model.pt").exists():
                LOGGER.info(f"检测到嵌套位置的模型，正在移动到正确位置...")
                try:
                    import shutil
                    # 确保目标父目录存在
                    local_model_path.parent.mkdir(parents=True, exist_ok=True)
                    # 移动整个模型目录
                    shutil.move(str(nested_model_path), str(local_model_path))
                    LOGGER.info(f"模型已移动到: {local_model_path}")
                    model_path = str(local_model_path.resolve())
                except Exception as e:
                    LOGGER.warning(f"移动模型失败，将使用嵌套位置: {e}")
                    model_path = str(nested_model_path.resolve())
            elif snapshot_root.is_dir() and any((snapshot / "model.pt").is_file() for snapshot in snapshot_root.iterdir() if snapshot.is_dir()):
                snapshot_model = next(snapshot for snapshot in snapshot_root.iterdir() if snapshot.is_dir() and (snapshot / "model.pt").is_file())
                model_path = str(snapshot_model.parent.resolve())
                LOGGER.info(f"使用 ModelScope 本地快照模型: {model_path}")
            else:
                # 否则使用模型 ID，会自动下载
                model_path = self.settings.asr_model
                LOGGER.info(f"模型不存在，将从 ModelScope 下载: {model_path}")

            # 第三方模型库的详细下载日志不直接刷屏，阶段进度由平台统一显示。
            for logger_name in ("funasr", "modelscope", "modelscope.hub", "huggingface_hub"):
                logging.getLogger(logger_name).setLevel(logging.WARNING)

            # SenseVoiceSmall 不需要 trust_remote_code，模型实现已内置在 FunASR 中
            # 设置为 False 可以避免 "No module named 'model'" 警告
            self._model = AutoModel(
                model=model_path,  # 使用本地路径或模型 ID
                trust_remote_code=False,
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": self.settings.asr_max_segment_ms},
                device=self.settings.asr_device,
                disable_pbar=True,
                disable_log=True,
                disable_update=True,
            )

            # 模型加载成功后，检查并修复可能的嵌套 models 目录问题
            self._fix_nested_models_directory()
        except Exception as exc:
            raise AppError("ASR_MODEL_LOAD_FAILED", "语音识别模型加载失败", repr(exc), True, "检查模型目录、网络或切换到 CPU 后重试") from exc
        return self._model

    def _fix_nested_models_directory(self) -> None:
        """修复 ModelScope 可能创建的嵌套 models 目录。

        某些版本的 ModelScope 会在 MODELSCOPE_CACHE 下创建 models/ 子目录，
        导致路径变成 data/models/models/iic/...，这里自动修复这个问题。
        """
        nested_models_dir = self.settings.model_dir / "models"
        if not nested_models_dir.exists():
            return

        # 检查是否有 iic 目录在嵌套的 models 下
        nested_iic_dir = nested_models_dir / "iic"
        target_iic_dir = self.settings.model_dir / "iic"

        if not nested_iic_dir.exists():
            # 检查临时目录
            temp_dir = nested_models_dir / "._____temp" / "iic"
            if temp_dir.exists():
                LOGGER.info(f"检测到临时下载目录: {temp_dir}")
            return

        # 如果目标已存在，需要合并而不是替换
        if target_iic_dir.exists():
            LOGGER.info("目标模型目录已存在，正在合并...")
            try:
                import shutil
                # 遍历嵌套目录中的所有内容
                for item in nested_iic_dir.rglob("*"):
                    if item.is_file():
                        # 计算相对路径
                        relative_path = item.relative_to(nested_iic_dir)
                        target_path = target_iic_dir / relative_path

                        # 如果目标文件不存在或大小不同，则复制
                        if not target_path.exists() or target_path.stat().st_size != item.stat().st_size:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(item), str(target_path))
                            LOGGER.info(f"已复制: {relative_path}")

                # 删除嵌套目录
                shutil.rmtree(str(nested_iic_dir))
                LOGGER.info(f"已删除嵌套的 iic 目录: {nested_iic_dir}")

            except Exception as e:
                LOGGER.warning(f"合并模型目录失败: {e}")
        else:
            # 目标不存在，直接移动
            try:
                import shutil
                LOGGER.info(f"检测到嵌套模型目录，正在修复: {nested_iic_dir} -> {target_iic_dir}")
                shutil.move(str(nested_iic_dir), str(target_iic_dir))
                LOGGER.info("模型目录已移动到正确位置")
            except Exception as e:
                LOGGER.warning(f"移动模型目录失败: {e}")
                return

        # 检查并清理嵌套 models 目录
        try:
            # 删除临时目录
            temp_dir = nested_models_dir / "._____temp"
            if temp_dir.exists():
                import shutil
                shutil.rmtree(str(temp_dir))
                LOGGER.info(f"已删除临时目录: {temp_dir}")

            # 如果 models 目录为空或只剩临时文件，删除它
            if nested_models_dir.exists():
                remaining_items = list(nested_models_dir.iterdir())
                if not remaining_items:
                    nested_models_dir.rmdir()
                    LOGGER.info(f"已删除空的嵌套目录: {nested_models_dir}")
                else:
                    LOGGER.info(f"嵌套目录还有其他内容，保留: {[item.name for item in remaining_items]}")
        except Exception as e:
            LOGGER.warning(f"清理嵌套目录失败，但不影响使用: {e}")

    @staticmethod
    def dependency_status() -> dict[str, Any]:
        """返回不加载模型的 FunASR 依赖状态。"""
        try:
            import funasr
            return {"installed": True, "version": getattr(funasr, "__version__", "unknown")}
        except ImportError as exc:
            return {"installed": False, "version": None, "error": str(exc)}

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
