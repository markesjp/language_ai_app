from dataclasses import dataclass


@dataclass
class SpeechUsage:
    provider: str
    model: str
    audio_seconds: float = 0
    tts_characters: int = 0
    estimated_cost_usd: float = 0


class MockSttProvider:
    name = "mock"
    model = "mock-stt-001"

    async def transcribe(self, audio_bytes: bytes) -> tuple[str, SpeechUsage]:
        seconds = max(0.1, len(audio_bytes) / 32000)
        return "mock transcription", SpeechUsage(provider=self.name, model=self.model, audio_seconds=seconds)


class MockTtsProvider:
    name = "mock"
    model = "mock-tts-001"

    async def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, SpeechUsage]:
        return b"", SpeechUsage(provider=self.name, model=self.model, tts_characters=len(text))
