import math

import httpx

from app.core.config import settings
from app.services.ai_providers.base import EmbeddingProvider, LlmProvider, LlmResult, LlmUsage
from app.services.runtime_settings import get_runtime_str


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


class OllamaLlmProvider(LlmProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.model = get_runtime_str("ollama_llm_model", settings.ollama_llm_model) or settings.ollama_llm_model

    async def complete(self, system_prompt: str, user_prompt: str, max_output_tokens: int | None = None) -> LlmResult:
        payload = {
            "model": self.model,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "num_ctx": 1024,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if max_output_tokens:
            payload["options"]["num_predict"] = max_output_tokens
        base_url = get_runtime_str("ollama_base_url", settings.ollama_base_url)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{base_url}/api/chat", json=payload)
            response.raise_for_status()
        text = response.json().get("message", {}).get("content", "").strip()
        return LlmResult(
            text=text or "O modelo local não retornou texto.",
            usage=LlmUsage(
                provider=self.name,
                model=self.model,
                input_tokens=_estimate_tokens(system_prompt + user_prompt),
                output_tokens=_estimate_tokens(text),
                estimated_cost_usd=0,
            ),
        )


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.model = get_runtime_str("ollama_embedding_model", settings.ollama_embedding_model) or settings.ollama_embedding_model

    async def embed(self, text: str) -> list[float]:
        payload = {"model": self.model, "input": text}
        base_url = get_runtime_str("ollama_base_url", settings.ollama_base_url)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{base_url}/api/embed", json=payload)
            response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings") or []
        if embeddings:
            return [float(value) for value in embeddings[0]]
        return [float(value) for value in data.get("embedding", [])]
