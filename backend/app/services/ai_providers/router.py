from app.core.config import settings
from app.services.ai_providers.base import EmbeddingProvider, LlmProvider
from app.services.ai_providers.mock import MockEmbeddingProvider, MockLlmProvider


class ProviderRouter:
    def get_llm(self, provider_name: str | None = None) -> LlmProvider:
        provider = provider_name or settings.default_llm_provider
        if provider == "mock":
            return MockLlmProvider()
        raise ValueError(f"Unsupported LLM provider: {provider}")

    def get_embeddings(self, provider_name: str | None = None) -> EmbeddingProvider:
        provider = provider_name or settings.default_embedding_provider
        if provider == "mock":
            return MockEmbeddingProvider()
        raise ValueError(f"Unsupported embedding provider: {provider}")


provider_router = ProviderRouter()
