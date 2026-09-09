#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Turn a video or audio file into transcript text with SenseVoice."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("video_to_text")
AUDIO_EXTS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".weba",
    ".wma",
}
LANGUAGES = ("auto", "zh", "en", "yue", "ja", "ko", "nospeech")


def configure_logging() -> None:
    """Configure concise, UTF-8 console logs for both terminals and pipes."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes)} 分 {remaining_seconds:.1f} 秒"


def positive_int(value: str) -> int:
    """Parse a positive integer for argparse."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"必须是整数：{value}") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError(f"必须大于 0：{value}")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use FunAudioLLM/SenseVoice to transcribe a video or audio file."
    )
    parser.add_argument("input", type=Path, help="视频或音频文件路径")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="输出 txt 文件路径；默认写到输入文件同目录同名 .txt",
    )
    parser.add_argument(
        "--model",
        default="iic/SenseVoiceSmall",
        help="SenseVoice 模型名或本地模型目录，默认：iic/SenseVoiceSmall",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help='推理设备：auto、cpu、cuda:0 等，默认 auto',
    )
    parser.add_argument(
        "--language",
        default="auto",
        choices=LANGUAGES,
        help='语言：auto、zh、en、yue、ja、ko、nospeech，默认 auto',
    )
    parser.add_argument(
        "--batch-size-s",
        type=positive_int,
        default=60,
        help="动态批处理音频秒数，默认 60",
    )
    parser.add_argument(
        "--merge-length-s",
        type=positive_int,
        default=15,
        help="VAD 短片段合并后的目标长度，默认 15 秒",
    )
    parser.add_argument(
        "--max-segment-ms",
        type=positive_int,
        default=30000,
        help="VAD 单段最长时长，默认 30000 毫秒",
    )
    parser.add_argument(
        "--no-itn",
        action="store_true",
        help="关闭逆文本规范化；默认会把数字、日期等转成更自然的写法",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="即使输入是音频，也先用 ffmpeg 转成 16k 单声道 wav",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="额外保存 SenseVoice 原始结果 JSON，便于排查或二次处理",
    )
    return parser.parse_args()


def pick_device(device: str) -> str:
    if device != "auto":
        return device

    try:
        import torch
    except Exception:
        return "cpu"

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def ensure_input(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"找不到输入文件：{path}")
    if not path.is_file():
        raise ValueError(f"输入路径不是文件：{path}")
    return path


def resolve_output(path: Path) -> Path:
    """Expand a user path without requiring the output file to exist."""
    return path.expanduser().resolve()


def validate_output_paths(
    input_path: Path,
    output_path: Path,
    json_path: Path | None,
) -> None:
    paths = {"文本输出": output_path}
    if json_path:
        paths["JSON 输出"] = json_path

    for label, path in paths.items():
        if path == input_path:
            raise ValueError(f"{label}不能覆盖输入文件：{path}")

    if json_path and json_path == output_path:
        raise ValueError("文本输出和 JSON 输出不能使用同一个文件")


def should_extract(input_path: Path, force_extract: bool) -> bool:
    return force_extract or input_path.suffix.lower() not in AUDIO_EXTS


def extract_audio(input_path: Path, workdir: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "需要先安装 ffmpeg 并确保它在 PATH 中，才能从视频里提取音轨。"
        )

    wav_path = workdir / f"{input_path.stem}.sensevoice.wav"
    LOGGER.info("提取音频：ffmpeg -> 16 kHz 单声道 WAV")
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(wav_path),
    ]
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        details = " ".join(completed.stderr.split())
        message = f"ffmpeg 提取音频失败，退出码：{completed.returncode}"
        if details:
            message = f"{message}：{details}"
        raise RuntimeError(message)
    return wav_path


def build_model(model_name: str, device: str, max_segment_ms: int) -> Any:
    try:
        from funasr import AutoModel
    except ImportError as exc:
        raise RuntimeError(
            "缺少 funasr。请先执行：pip install -r requirements.txt"
        ) from exc

    return AutoModel(
        model=model_name,
        trust_remote_code=True,
        vad_model="fsmn-vad",
        vad_kwargs={"max_single_segment_time": max_segment_ms},
        device=device,
        disable_update=True,
        disable_pbar=True,
        disable_log=True,
    )


def transcribe(
    model: Any,
    audio_path: Path,
    language: str,
    use_itn: bool,
    batch_size_s: int,
    merge_length_s: int,
) -> tuple[str, list[dict[str, Any]]]:
    from funasr.utils.postprocess_utils import rich_transcription_postprocess

    generated = model.generate(
        input=str(audio_path),
        cache={},
        language=language,
        use_itn=use_itn,
        batch_size_s=batch_size_s,
        merge_vad=True,
        merge_length_s=merge_length_s,
    )

    if generated is None:
        result: list[dict[str, Any]] = []
    elif isinstance(generated, dict):
        result = [generated]
    else:
        result = list(generated)

    lines: list[str] = []
    for item in result:
        if not isinstance(item, dict):
            raise TypeError("SenseVoice 返回了无法处理的结果格式")

        raw_text = item.get("text", "")
        text = rich_transcription_postprocess(str(raw_text or "")).strip()
        if text:
            lines.append(text)

    return "\n".join(lines), result


def save_text(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def save_json(result: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    configure_logging()
    args = parse_args()

    try:
        input_path = ensure_input(args.input)
        output_path = resolve_output(args.output or input_path.with_suffix(".txt"))
        json_path = resolve_output(args.json) if args.json else None
        validate_output_paths(input_path, output_path, json_path)
        device = pick_device(args.device)

        LOGGER.info("输入文件：%s", input_path)
        LOGGER.info("文本输出：%s", output_path)
        if json_path:
            LOGGER.info("JSON 输出：%s", json_path)
        LOGGER.info("推理设备：%s | 语言：%s", device, args.language)

        started_at = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="sensevoice_") as tmp:
            tmpdir = Path(tmp)
            if should_extract(input_path, args.force_extract):
                audio_path = extract_audio(input_path, tmpdir)
            else:
                audio_path = input_path
                LOGGER.info("使用原始音频：无需转换")

            LOGGER.info("加载模型：%s", args.model)
            model = build_model(args.model, device, args.max_segment_ms)

            LOGGER.info("开始识别，预计需要一些时间，请稍候")
            text, raw_result = transcribe(
                model=model,
                audio_path=audio_path,
                language=args.language,
                use_itn=not args.no_itn,
                batch_size_s=args.batch_size_s,
                merge_length_s=args.merge_length_s,
            )

        elapsed = format_duration(time.perf_counter() - started_at)
        save_text(text, output_path)
        LOGGER.info(
            "识别完成：耗时 %s | %d 段 | %d 字符",
            elapsed,
            len(raw_result),
            len(text),
        )
        LOGGER.info("已保存文本：%s", output_path)
        if json_path:
            save_json(raw_result, json_path)
            LOGGER.info("已保存 JSON：%s", json_path)

        if text:
            preview_length = 1000
            preview = text[:preview_length]
            LOGGER.info("文案预览：前 %d 字符", min(len(text), preview_length))
            print(preview)
            if len(text) > preview_length:
                print("...")
        else:
            LOGGER.warning("识别完成，但没有识别到文本")
        return 0
    except Exception as exc:
        LOGGER.error("%s：%s", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
