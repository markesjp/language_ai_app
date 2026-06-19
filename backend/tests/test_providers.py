import pytest

from app.services.ai_providers.mock import MockEmbeddingProvider, MockLlmProvider


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
