from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SpeechUsage:
    provider: str
    model: str
    audio_seconds: float = 0
    tts_characters: int = 0
    estimated_cost_usd: float = 0


class SttProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, *, filename: str | None = None, content_type: str | None = None) -> tuple[str, SpeechUsage]:
        raise NotImplementedError


class TtsProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        model: str | None = None,
        speed: float | None = None,
    ) -> tuple[bytes, SpeechUsage]:
        raise NotImplementedError


class MockSttProvider(SttProvider):
    name = "mock"
    model = "mock-stt-001"

    async def transcribe(self, audio_bytes: bytes, *, filename: str | None = None, content_type: str | None = None) -> tuple[str, SpeechUsage]:
        seconds = max(0.1, len(audio_bytes) / 32000)
        return "mock transcription", SpeechUsage(provider=self.name, model=self.model, audio_seconds=seconds)


class MockTtsProvider(TtsProvider):
    name = "mock"
    model = "mock-tts-001"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        model: str | None = None,
        speed: float | None = None,
    ) -> tuple[bytes, SpeechUsage]:
        return b"", SpeechUsage(provider=self.name, model=model or self.model, tts_characters=len(text))
