"""OpenAI Compatible HTTP Provider。"""

from __future__ import annotations

import threading
from typing import Any

import httpx

from app.domain.schemas import AppError


class OpenAICompatibleProvider:
    """使用 Chat Completions 协议，业务层不绑定具体厂商。"""

    name = "openai-compatible"
    DEFAULT_TIMEOUT_SECONDS = 300

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        try:
            timeout_value = float(timeout)
        except (TypeError, ValueError):
            timeout_value = self.DEFAULT_TIMEOUT_SECONDS
        self.timeout = max(1.0, timeout_value)
        self._client_lock = threading.Lock()
        self._active_client: httpx.Client | None = None

    def generate(self, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        """请求兼容接口并抽取统一结果。"""
        messages = []
        if options.get("system_prompt"):
            messages.append({"role": "system", "content": options["system_prompt"]})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": options.get("model", self.model), "messages": messages, "temperature": options.get("temperature", 0.3)}
        if options.get("max_tokens") is not None:
            payload["max_tokens"] = int(options["max_tokens"])
        try:
            client = httpx.Client(timeout=self.timeout, trust_env=False)
            with self._client_lock:
                self._active_client = client
            try:
                response = client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}"}, json=payload)
                response.raise_for_status()
                raw = response.json()
                return {"content": raw["choices"][0]["message"]["content"], "raw_response": raw, "model": raw.get("model", payload["model"]), "usage": raw.get("usage", {})}
            finally:
                with self._client_lock:
                    if self._active_client is client:
                        self._active_client = None
                client.close()
        except (httpx.HTTPError, KeyError, ValueError, RuntimeError) as exc:
            raise AppError("AI_REQUEST_FAILED", "AI 分析请求失败", str(exc), True, "检查 Provider 地址和网络后重试") from exc

    def cancel(self) -> None:
        """Close the active request so a paused or canceled task releases promptly."""
        with self._client_lock:
            client = self._active_client
        if client is not None:
            client.close()

    def health_check(self) -> bool:
        """通过 models 端点做轻量检查。"""
        try:
            response = httpx.get(f"{self.base_url}/models", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=10, trust_env=False)
            return response.is_success
        except httpx.HTTPError:
            return False
