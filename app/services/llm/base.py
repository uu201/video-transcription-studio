"""LLM Provider 抽象接口。"""

from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    """业务层依赖的最小生成接口。"""

    name: str

    def generate(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """生成一段分析结果。"""
        ...

    def health_check(self) -> bool:
        """检查 Provider 是否可用。"""
        ...
