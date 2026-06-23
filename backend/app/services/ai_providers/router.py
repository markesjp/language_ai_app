from app.core.config import settings
from app.services.ai_providers.base import EmbeddingProvider, LlmProvider, RerankProvider
from app.services.ai_providers.cohere import CohereEmbeddingProvider, CohereRerankProvider
from app.services.ai_providers.gemini import GeminiEmbeddingProvider, GeminiLlmProvider
from app.services.ai_providers.groq import GroqLlmProvider
from app.services.ai_providers.mock import MockEmbeddingProvider, MockLlmProvider, NoopRerankProvider
from app.services.ai_providers.nvidia_nim import NvidiaNimEmbeddingProvider, NvidiaNimLlmProvider, NvidiaNimRerankProvider
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
        if provider == "groq":
            return GroqLlmProvider()
        if provider == "nvidia_nim":
            return NvidiaNimLlmProvider()
        raise ValueError(f"Unsupported LLM provider: {provider}")

    def get_embeddings(self, provider_name: str | None = None) -> EmbeddingProvider:
        provider = provider_name or get_runtime_str("default_embedding_provider", settings.default_embedding_provider)
        if provider == "mock":
            return MockEmbeddingProvider()
        if provider == "gemini":
            return GeminiEmbeddingProvider()
        if provider == "ollama":
            return OllamaEmbeddingProvider()
        if provider == "cohere":
            return CohereEmbeddingProvider()
        if provider == "nvidia_nim":
            return NvidiaNimEmbeddingProvider()
        raise ValueError(f"Unsupported embedding provider: {provider}")

    def get_rerank(self, provider_name: str | None = None) -> RerankProvider:
        provider = provider_name or get_runtime_str("default_rerank_provider", settings.default_rerank_provider)
        if provider in {"none", "mock"}:
            return NoopRerankProvider()
        if provider == "cohere":
            return CohereRerankProvider()
        if provider == "nvidia_nim":
            return NvidiaNimRerankProvider()
        raise ValueError(f"Unsupported rerank provider: {provider}")


provider_router = ProviderRouter()
