import math

import httpx

from app.core.config import settings
from app.services.ai_providers.base import EmbeddingProvider, LlmProvider, LlmResult, LlmUsage
from app.services.runtime_settings import get_runtime_int, get_runtime_str


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


class GeminiLlmProvider(LlmProvider):
    name = "gemini"

    def __init__(self) -> None:
        self.model = get_runtime_str("gemini_llm_model", settings.gemini_llm_model) or settings.gemini_llm_model

    async def complete(self, system_prompt: str, user_prompt: str, max_output_tokens: int | None = None) -> LlmResult:
        api_key = get_runtime_str("gemini_api_key", settings.gemini_api_key)
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required when DEFAULT_LLM_PROVIDER=gemini")

        base_url = get_runtime_str("gemini_api_base_url", settings.gemini_api_base_url)
        url = f"{base_url}/models/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        }
        if max_output_tokens:
            payload["generationConfig"] = {"maxOutputTokens": max_output_tokens}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)
            response.raise_for_status()
        data = response.json()
        text = "".join(
            part.get("text", "")
            for candidate in data.get("candidates", [])
            for part in candidate.get("content", {}).get("parts", [])
        ).strip()
        usage_metadata = data.get("usageMetadata", {})
        input_tokens = usage_metadata.get("promptTokenCount") or _estimate_tokens(system_prompt + user_prompt)
        output_tokens = usage_metadata.get("candidatesTokenCount") or _estimate_tokens(text)
        return LlmResult(
            text=text or "Não consegui gerar uma resposta agora. Tente novamente em instantes.",
            usage=LlmUsage(
                provider=self.name,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=0,
            ),
        )


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    def __init__(self) -> None:
        self.model = get_runtime_str("gemini_embedding_model", settings.gemini_embedding_model) or settings.gemini_embedding_model

    async def embed(self, text: str) -> list[float]:
        api_key = get_runtime_str("gemini_api_key", settings.gemini_api_key)
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required when DEFAULT_EMBEDDING_PROVIDER=gemini")

        base_url = get_runtime_str("gemini_api_base_url", settings.gemini_api_base_url)
        url = f"{base_url}/models/{self.model}:embedContent"
        payload = {
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": get_runtime_int("embedding_dimension", settings.embedding_dimension),
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)
            response.raise_for_status()
        values = response.json().get("embedding", {}).get("values", [])
        return [float(value) for value in values]
