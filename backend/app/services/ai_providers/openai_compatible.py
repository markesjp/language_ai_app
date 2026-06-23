import math

import httpx

from app.services.ai_providers.base import EmbeddingProvider, LlmProvider, LlmResult, LlmUsage, RerankProvider


def _estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _clean_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


class OpenAiCompatibleLlmProvider(LlmProvider):
    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str | None,
        base_url: str,
        missing_key_message: str,
    ) -> None:
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = _clean_base_url(base_url)
        self.missing_key_message = missing_key_message

    async def complete(self, system_prompt: str, user_prompt: str, max_output_tokens: int | None = None) -> LlmResult:
        if not self.api_key:
            raise ValueError(self.missing_key_message)

        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        if max_output_tokens:
            payload["max_tokens"] = max_output_tokens

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        text = ""
        if choices:
            message = choices[0].get("message") or {}
            text = str(message.get("content") or choices[0].get("text") or "").strip()
        usage = data.get("usage", {})
        return LlmResult(
            text=text or "Nao consegui gerar uma resposta agora. Tente novamente em instantes.",
            usage=LlmUsage(
                provider=self.name,
                model=self.model,
                input_tokens=int(usage.get("prompt_tokens") or _estimate_tokens(system_prompt + user_prompt)),
                output_tokens=int(usage.get("completion_tokens") or _estimate_tokens(text)),
                cached_tokens=int(usage.get("prompt_tokens_details", {}).get("cached_tokens") or 0),
                estimated_cost_usd=0,
            ),
        )


class OpenAiCompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str | None,
        base_url: str,
        missing_key_message: str,
    ) -> None:
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = _clean_base_url(base_url)
        self.missing_key_message = missing_key_message

    async def embed(self, text: str) -> list[float]:
        if not self.api_key:
            raise ValueError(self.missing_key_message)

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return []
        return [float(value) for value in data[0].get("embedding", [])]


class OpenAiCompatibleRerankProvider(RerankProvider):
    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str | None,
        base_url: str,
        missing_key_message: str,
    ) -> None:
        self.name = name
        self.model = model
        self.api_key = api_key
        self.base_url = _clean_base_url(base_url)
        self.missing_key_message = missing_key_message

    async def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[tuple[int, float]]:
        if not documents:
            return []
        if not self.api_key:
            raise ValueError(self.missing_key_message)

        payload = {
            "model": self.model,
            "query": {"text": query},
            "passages": [{"text": document} for document in documents],
        }
        if top_n:
            payload["top_n"] = top_n
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/ranking",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        rows = data.get("rankings") or data.get("results") or []
        ranked: list[tuple[int, float]] = []
        for row in rows:
            index = row.get("index", row.get("passage_index"))
            score = row.get("relevance_score", row.get("logit", row.get("score", 0)))
            if index is not None:
                ranked.append((int(index), float(score)))
        return ranked
