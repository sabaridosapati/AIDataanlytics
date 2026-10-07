import json

from openai import AsyncOpenAI

from app.llm.provider import LLMError


class OpenAIProvider:
    def __init__(self, settings):
        # Short per-call timeout: steps have a 30 s budget and the whole query 150 s.
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=1, timeout=settings.openai_timeout_s)
        self.chat_model = settings.openai_chat_model
        self.embed_model = settings.openai_embed_model
        self.temperature = settings.openai_temperature

    def _params(self, model: str | None) -> dict:
        params: dict = {"model": model or self.chat_model}
        if self.temperature is not None:
            params["temperature"] = self.temperature
        return params

    async def chat_json(self, *, purpose: str, system: str, user: str, schema: dict, model: str | None = None) -> dict:
        try:
            resp = await self.client.chat.completions.create(
                **self._params(model),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": purpose, "schema": schema, "strict": True},
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        message = resp.choices[0].message
        if getattr(message, "refusal", None):
            raise LLMError(f"The model refused: {message.refusal}")
        if not message.content:
            raise LLMError("The model returned an empty response")
        try:
            return json.loads(message.content)
        except json.JSONDecodeError as exc:
            raise LLMError("The model returned invalid JSON") from exc

    async def chat_text(self, *, purpose: str, system: str, user: str, model: str | None = None) -> str:
        try:
            resp = await self.client.chat.completions.create(
                **self._params(model),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        return (resp.choices[0].message.content or "").strip()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        try:
            for i in range(0, len(texts), 100):
                resp = await self.client.embeddings.create(model=self.embed_model, input=texts[i : i + 100])
                out.extend(d.embedding for d in resp.data)
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"OpenAI embedding request failed: {exc}") from exc
        return out
