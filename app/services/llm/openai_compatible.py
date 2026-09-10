"""OpenAI Compatible HTTP Provider。"""

from __future__ import annotations

from typing import Any

import httpx

from app.domain.schemas import AppError


class OpenAICompatibleProvider:
    """使用 Chat Completions 协议，业务层不绑定具体厂商。"""

    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """请求兼容接口并抽取统一结果。"""
        payload = {"model": options.get("model", self.model), "messages": [{"role": "user", "content": prompt}], "temperature": options.get("temperature", 0.3)}
        try:
            response = httpx.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}"}, json=payload, timeout=self.timeout)
            response.raise_for_status()
            raw = response.json()
            return {"content": raw["choices"][0]["message"]["content"], "raw_response": raw, "model": raw.get("model", payload["model"]), "usage": raw.get("usage", {})}
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise AppError("AI_REQUEST_FAILED", "AI 分析请求失败", str(exc), True, "检查 Provider 地址和网络后重试") from exc

    def health_check(self) -> bool:
        """通过 models 端点做轻量检查。"""
        try:
            response = httpx.get(f"{self.base_url}/models", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10)
            return response.is_success
        except httpx.HTTPError:
            return False
