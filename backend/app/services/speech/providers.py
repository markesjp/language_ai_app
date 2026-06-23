import httpx

from app.core.config import settings
from app.services.runtime_settings import get_runtime_str
from app.services.speech.interfaces import MockSttProvider, MockTtsProvider, SpeechUsage, SttProvider, TtsProvider


def _audio_seconds(audio_bytes: bytes) -> float:
    return max(0.1, len(audio_bytes) / 32000)


class GroqSttProvider(SttProvider):
    name = "groq"

    def __init__(self) -> None:
        self.model = get_runtime_str("groq_stt_model", settings.groq_stt_model) or settings.groq_stt_model

    async def transcribe(self, audio_bytes: bytes, *, filename: str | None = None, content_type: str | None = None) -> tuple[str, SpeechUsage]:
        api_key = get_runtime_str("groq_api_key", settings.groq_api_key)
        if not api_key:
            raise ValueError("GROQ_API_KEY is required when DEFAULT_STT_PROVIDER=groq")
        base_url = get_runtime_str("groq_api_base_url", settings.groq_api_base_url) or settings.groq_api_base_url
        files = {"file": (filename or "audio.webm", audio_bytes, content_type or "application/octet-stream")}
        data = {"model": self.model, "response_format": "json"}
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=files,
            )
            response.raise_for_status()
        text = str(response.json().get("text", "")).strip()
        return text, SpeechUsage(provider=self.name, model=self.model, audio_seconds=_audio_seconds(audio_bytes))


class DeepgramSttProvider(SttProvider):
    name = "deepgram"

    def __init__(self) -> None:
        self.model = get_runtime_str("deepgram_stt_model", settings.deepgram_stt_model) or settings.deepgram_stt_model

    async def transcribe(self, audio_bytes: bytes, *, filename: str | None = None, content_type: str | None = None) -> tuple[str, SpeechUsage]:
        api_key = get_runtime_str("deepgram_api_key", settings.deepgram_api_key)
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY is required when DEFAULT_STT_PROVIDER=deepgram")
        base_url = get_runtime_str("deepgram_api_base_url", settings.deepgram_api_base_url) or settings.deepgram_api_base_url
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1/listen",
                params={"model": self.model, "smart_format": "true"},
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": content_type or "application/octet-stream",
                },
                content=audio_bytes,
            )
            response.raise_for_status()
        data = response.json()
        alternatives = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])
        text = str(alternatives[0].get("transcript", "")).strip()
        duration = float(data.get("metadata", {}).get("duration") or _audio_seconds(audio_bytes))
        return text, SpeechUsage(provider=self.name, model=self.model, audio_seconds=duration)


class DeepgramTtsProvider(TtsProvider):
    name = "deepgram"

    def __init__(self) -> None:
        self.model = get_runtime_str("deepgram_tts_model", settings.deepgram_tts_model) or settings.deepgram_tts_model

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        model: str | None = None,
        speed: float | None = None,
    ) -> tuple[bytes, SpeechUsage]:
        api_key = get_runtime_str("deepgram_api_key", settings.deepgram_api_key)
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY is required when DEFAULT_TTS_PROVIDER=deepgram")
        selected_model = model or voice or self.model
        base_url = get_runtime_str("deepgram_api_base_url", settings.deepgram_api_base_url) or settings.deepgram_api_base_url
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1/speak",
                params={"model": selected_model},
                headers={"Authorization": f"Token {api_key}", "Accept": "audio/mpeg"},
                json={"text": text},
            )
            response.raise_for_status()
        return response.content, SpeechUsage(provider=self.name, model=selected_model, tts_characters=len(text))


class ElevenLabsTtsProvider(TtsProvider):
    name = "elevenlabs"

    def __init__(self) -> None:
        self.model = get_runtime_str("elevenlabs_tts_model", settings.elevenlabs_tts_model) or settings.elevenlabs_tts_model

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        model: str | None = None,
        speed: float | None = None,
    ) -> tuple[bytes, SpeechUsage]:
        api_key = get_runtime_str("elevenlabs_api_key", settings.elevenlabs_api_key)
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is required when DEFAULT_TTS_PROVIDER=elevenlabs")
        selected_model = model or self.model
        voice_id = voice or get_runtime_str("elevenlabs_default_voice_id", settings.elevenlabs_default_voice_id) or settings.elevenlabs_default_voice_id
        base_url = get_runtime_str("elevenlabs_api_base_url", settings.elevenlabs_api_base_url) or settings.elevenlabs_api_base_url
        payload: dict = {"text": text, "model_id": selected_model}
        if speed:
            payload["voice_settings"] = {"stability": 0.5, "similarity_boost": 0.75, "style": max(0, min(1, speed - 0.5))}
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Accept": "audio/mpeg"},
                json=payload,
            )
            response.raise_for_status()
        return response.content, SpeechUsage(provider=self.name, model=selected_model, tts_characters=len(text))


class SpeechProviderRouter:
    def get_stt(self, provider_name: str | None = None) -> SttProvider:
        provider = provider_name or get_runtime_str("default_stt_provider", settings.default_stt_provider)
        if provider == "mock":
            return MockSttProvider()
        if provider == "groq":
            return GroqSttProvider()
        if provider == "deepgram":
            return DeepgramSttProvider()
        raise ValueError(f"Unsupported STT provider: {provider}")

    def get_tts(self, provider_name: str | None = None) -> TtsProvider:
        provider = provider_name or get_runtime_str("default_tts_provider", settings.default_tts_provider)
        if provider == "mock":
            return MockTtsProvider()
        if provider == "deepgram":
            return DeepgramTtsProvider()
        if provider == "elevenlabs":
            return ElevenLabsTtsProvider()
        raise ValueError(f"Unsupported TTS provider: {provider}")


speech_provider_router = SpeechProviderRouter()
