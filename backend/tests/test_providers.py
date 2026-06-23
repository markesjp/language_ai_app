import pytest
import httpx

from app.services.ai_providers.mock import MockEmbeddingProvider, MockLlmProvider
from app.services.ai_providers.router import ProviderRouter
from app.services import runtime_settings
from app.services.ai_providers.groq import GroqLlmProvider
from app.services.ai_providers.cohere import CohereRerankProvider
from app.services.speech.providers import DeepgramSttProvider, DeepgramTtsProvider, ElevenLabsTtsProvider, SpeechProviderRouter


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
    assert router.get_llm("groq").name == "groq"
    assert router.get_llm("nvidia_nim").name == "nvidia_nim"
    assert router.get_embeddings("cohere").name == "cohere"
    assert router.get_embeddings("nvidia_nim").name == "nvidia_nim"
    assert router.get_rerank("none").name == "none"
    assert router.get_rerank("cohere").name == "cohere"
    assert router.get_rerank("nvidia_nim").name == "nvidia_nim"


def test_speech_router_exposes_real_adapters():
    router = SpeechProviderRouter()

    assert router.get_stt("mock").name == "mock"
    assert router.get_stt("groq").name == "groq"
    assert router.get_stt("deepgram").name == "deepgram"
    assert router.get_tts("mock").name == "mock"
    assert router.get_tts("deepgram").name == "deepgram"
    assert router.get_tts("elevenlabs").name == "elevenlabs"


def test_provider_router_rejects_unknown_provider():
    router = ProviderRouter()

    with pytest.raises(ValueError):
        router.get_llm("unknown")
    with pytest.raises(ValueError):
        router.get_embeddings("unknown")
    with pytest.raises(ValueError):
        router.get_rerank("unknown")


def test_provider_router_uses_runtime_overrides():
    runtime_settings._runtime_settings["default_llm_provider"] = "ollama"
    runtime_settings._runtime_settings["default_embedding_provider"] = "ollama"
    try:
        router = ProviderRouter()

        assert router.get_llm().name == "ollama"
        assert router.get_embeddings().name == "ollama"
    finally:
        runtime_settings._runtime_settings.clear()


@pytest.mark.asyncio
async def test_openai_compatible_llm_posts_chat_completion(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.services.ai_providers.openai_compatible.httpx.AsyncClient",
        lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    runtime_settings._runtime_settings.update({"groq_api_key": "key", "groq_llm_model": "llama-test"})
    try:
        result = await GroqLlmProvider().complete("system", "user", max_output_tokens=12)
    finally:
        runtime_settings._runtime_settings.clear()

    assert result.text == "hello"
    assert result.usage.provider == "groq"
    assert requests[0].url.path.endswith("/chat/completions")
    assert requests[0].headers["authorization"] == "Bearer key"
    assert '"max_tokens":12' in requests[0].content.decode().replace(" ", "")


@pytest.mark.asyncio
async def test_cohere_rerank_reorders_documents(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"index": 1, "relevance_score": 0.91}, {"index": 0, "relevance_score": 0.4}]})

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.services.ai_providers.cohere.httpx.AsyncClient",
        lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    runtime_settings._runtime_settings["cohere_api_key"] = "key"
    try:
        result = await CohereRerankProvider().rerank("query", ["low", "high"], top_n=2)
    finally:
        runtime_settings._runtime_settings.clear()

    assert result == [(1, 0.91), (0, 0.4)]


@pytest.mark.asyncio
async def test_deepgram_stt_uses_token_header(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"metadata": {"duration": 1.25}, "results": {"channels": [{"alternatives": [{"transcript": "ola"}]}]}},
        )

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.services.speech.providers.httpx.AsyncClient",
        lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    runtime_settings._runtime_settings["deepgram_api_key"] = "dg"
    try:
        text, usage = await DeepgramSttProvider().transcribe(b"audio", content_type="audio/webm")
    finally:
        runtime_settings._runtime_settings.clear()

    assert text == "ola"
    assert usage.audio_seconds == 1.25
    assert requests[0].headers["authorization"] == "Token dg"


@pytest.mark.asyncio
async def test_deepgram_tts_returns_audio(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"mp3")

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.services.speech.providers.httpx.AsyncClient",
        lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    runtime_settings._runtime_settings["deepgram_api_key"] = "dg"
    try:
        audio, usage = await DeepgramTtsProvider().synthesize("hello")
    finally:
        runtime_settings._runtime_settings.clear()

    assert audio == b"mp3"
    assert usage.tts_characters == 5


@pytest.mark.asyncio
async def test_elevenlabs_tts_returns_audio(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"voice")

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.services.speech.providers.httpx.AsyncClient",
        lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    runtime_settings._runtime_settings["elevenlabs_api_key"] = "el"
    try:
        audio, usage = await ElevenLabsTtsProvider().synthesize("hello", voice="voice-id")
    finally:
        runtime_settings._runtime_settings.clear()

    assert audio == b"voice"
    assert usage.provider == "elevenlabs"
    assert requests[0].url.path.endswith("/v1/text-to-speech/voice-id")
    assert requests[0].headers["xi-api-key"] == "el"
