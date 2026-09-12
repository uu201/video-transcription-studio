"""LLM Provider 工厂。"""

from app.services.llm.openai_compatible import OpenAICompatibleProvider


def create_provider(provider_type: str, **options):
    """根据设置创建 Provider，不让业务层绑定厂商。"""
    if provider_type == "openai-compatible":
        return OpenAICompatibleProvider(
            options["base_url"],
            options["api_key"],
            options["model"],
            options.get("timeout", OpenAICompatibleProvider.DEFAULT_TIMEOUT_SECONDS),
        )
    raise ValueError(f"不支持的 AI Provider：{provider_type}")
