from typing import Protocol


class LLMError(Exception):
    """The language model could not produce a usable response."""


class LLMProvider(Protocol):
    async def chat_json(self, *, purpose: str, system: str, user: str, schema: dict, model: str | None = None) -> dict: ...

    async def chat_text(self, *, purpose: str, system: str, user: str, model: str | None = None) -> str: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


def build_provider(settings) -> LLMProvider:
    if settings.llm_provider == "fake":
        from app.llm.demo_script import DEMO_RULES
        from app.llm.fake_provider import FakeLLMProvider

        return FakeLLMProvider(rules=DEMO_RULES, dim=settings.embed_dim)
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai (or set LLM_PROVIDER=fake for demo mode)")
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)
    raise RuntimeError(f"Unknown LLM_PROVIDER '{settings.llm_provider}' (expected 'openai' or 'fake')")
