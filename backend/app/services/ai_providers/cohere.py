import httpx

from app.core.config import settings
from app.services.ai_providers.base import EmbeddingProvider, RerankProvider
from app.services.runtime_settings import get_runtime_str


class CohereEmbeddingProvider(EmbeddingProvider):
    name = "cohere"

    def __init__(self) -> None:
        self.model = get_runtime_str("cohere_embedding_model", settings.cohere_embedding_model) or settings.cohere_embedding_model

    async def embed(self, text: str) -> list[float]:
        api_key = get_runtime_str("cohere_api_key", settings.cohere_api_key)
        if not api_key:
            raise ValueError("COHERE_API_KEY is required when DEFAULT_EMBEDDING_PROVIDER=cohere")

        base_url = get_runtime_str("cohere_api_base_url", settings.cohere_api_base_url) or settings.cohere_api_base_url
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v2/embed",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "texts": [text],
                    "input_type": "search_document",
                    "embedding_types": ["float"],
                },
            )
            response.raise_for_status()
        embeddings = response.json().get("embeddings", {})
        values = embeddings.get("float", [[]])[0] if isinstance(embeddings, dict) else embeddings[0]
        return [float(value) for value in values]


class CohereRerankProvider(RerankProvider):
    name = "cohere"

    def __init__(self) -> None:
        self.model = get_runtime_str("cohere_rerank_model", settings.cohere_rerank_model) or settings.cohere_rerank_model

    async def rerank(self, query: str, documents: list[str], top_n: int | None = None) -> list[tuple[int, float]]:
        if not documents:
            return []
        api_key = get_runtime_str("cohere_api_key", settings.cohere_api_key)
        if not api_key:
            raise ValueError("COHERE_API_KEY is required when DEFAULT_RERANK_PROVIDER=cohere")

        base_url = get_runtime_str("cohere_api_base_url", settings.cohere_api_base_url) or settings.cohere_api_base_url
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v2/rerank",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n or len(documents),
                },
            )
            response.raise_for_status()
        return [
            (int(row["index"]), float(row.get("relevance_score", 0)))
            for row in response.json().get("results", [])
        ]
