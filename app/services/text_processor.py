"""文本清洗和版本化处理。"""

from __future__ import annotations

import re

from app.domain.schemas import ASRResult


class TextProcessor:
    """保留原始识别结果，同时生成适合阅读的清洗文本。"""

    def process(self, result: ASRResult) -> str:
        """规范空白、去除重复标点和空行。"""
        text = result.text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"([，。！？、])\1+", r"\1", text)
        return "\n".join(line.strip() for line in text.splitlines()).strip()
