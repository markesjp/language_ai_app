import pytest

from app.services.ai_providers.mock import MockEmbeddingProvider, MockLlmProvider
from app.services.ai_providers.router import ProviderRouter
from app.services import runtime_settings


@pytest.mark.asyncio
async def test_mock_llm_reports_usage():
    result = await MockLlmProvider().complete("system", "hello")

    assert result.text
    assert result.usage.provider == "mock"
    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0


@pytest.mark.asyncio
async def test_mock_embeddings_are_deterministic():
    provider = MockEmbeddingProvider()

    assert await provider.embed("same") == await provider.embed("same")
    assert len(await provider.embed("same")) == 64


def test_provider_router_exposes_real_adapters():
    router = ProviderRouter()

    assert router.get_llm("gemini").name == "gemini"
    assert router.get_embeddings("gemini").name == "gemini"
    assert router.get_llm("ollama").name == "ollama"
    assert router.get_embeddings("ollama").name == "ollama"


def test_provider_router_uses_runtime_overrides():
    runtime_settings._runtime_settings["default_llm_provider"] = "ollama"
    runtime_settings._runtime_settings["default_embedding_provider"] = "ollama"
    try:
        router = ProviderRouter()

        assert router.get_llm().name == "ollama"
        assert router.get_embeddings().name == "ollama"
    finally:
        runtime_settings._runtime_settings.clear()
