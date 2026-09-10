"""转写结果导出 TXT、JSON、SRT。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.domain.schemas import ASRResult


class Exporter:
    """将结果写入任务专属目录并记录导出文件。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _srt_time(seconds: float) -> str:
        """将秒数格式化成 SRT 时间。"""
        milliseconds = max(0, int(seconds * 1000))
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds_part, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d},{millis:03d}"

    def export(self, task_id: int, result: ASRResult, clean_text: str) -> dict[str, Path]:
        """导出三种文件并返回文件路径。"""
        directory = self.settings.result_dir / str(task_id)
        directory.mkdir(parents=True, exist_ok=True)
        txt = directory / "transcript.txt"
        json_path = directory / "transcript.json"
        srt = directory / "transcript.srt"
        txt.write_text(clean_text + ("\n" if clean_text else ""), encoding="utf-8")
        payload: dict[str, Any] = {"language": result.language, "text": result.text, "segments": [segment.__dict__ for segment in result.segments], "rawResult": result.raw_result}
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        blocks = []
        for segment in result.segments:
            blocks.append(f"{segment.sequence}\n{self._srt_time(segment.start)} --> {self._srt_time(segment.end)}\n{segment.text}\n")
        srt.write_text("\n".join(blocks), encoding="utf-8")
        return {"txt": txt, "json": json_path, "srt": srt}
