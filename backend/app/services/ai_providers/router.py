from app.core.config import settings
from app.services.ai_providers.base import EmbeddingProvider, LlmProvider
from app.services.ai_providers.gemini import GeminiEmbeddingProvider, GeminiLlmProvider
from app.services.ai_providers.mock import MockEmbeddingProvider, MockLlmProvider
from app.services.ai_providers.ollama import OllamaEmbeddingProvider, OllamaLlmProvider
from app.services.runtime_settings import get_runtime_str


class ProviderRouter:
    def get_llm(self, provider_name: str | None = None) -> LlmProvider:
        provider = provider_name or get_runtime_str("default_llm_provider", settings.default_llm_provider)
        if provider == "mock":
            return MockLlmProvider()
        if provider == "gemini":
            return GeminiLlmProvider()
        if provider == "ollama":
            return OllamaLlmProvider()
        raise ValueError(f"Unsupported LLM provider: {provider}")

    def get_embeddings(self, provider_name: str | None = None) -> EmbeddingProvider:
        provider = provider_name or get_runtime_str("default_embedding_provider", settings.default_embedding_provider)
        if provider == "mock":
            return MockEmbeddingProvider()
        if provider == "gemini":
            return GeminiEmbeddingProvider()
        if provider == "ollama":
            return OllamaEmbeddingProvider()
        raise ValueError(f"Unsupported embedding provider: {provider}")


provider_router = ProviderRouter()
