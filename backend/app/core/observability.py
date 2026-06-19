import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from uuid import uuid4


LATENCY_FIELDS = (
    "time_to_first_transcript",
    "stt_duration",
    "rag_duration",
    "time_to_first_token",
    "llm_duration",
    "time_to_first_audio",
    "tts_duration",
    "total_turn_duration",
)


@dataclass
class TraceContext:
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    conversation_turn_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class LatencyTracker:
    started_at: float = field(default_factory=time.perf_counter)
    measurements_ms: dict[str, float] = field(default_factory=dict)

    def mark_duration(self, name: str, started_at: float) -> None:
        self.measurements_ms[name] = round((time.perf_counter() - started_at) * 1000, 3)

    def finish(self) -> dict[str, float]:
        self.measurements_ms["total_turn_duration"] = round((time.perf_counter() - self.started_at) * 1000, 3)
        return self.measurements_ms


@asynccontextmanager
async def timed_step(tracker: LatencyTracker, name: str) -> AsyncIterator[None]:
    started_at = time.perf_counter()
    try:
        yield
    finally:
        tracker.mark_duration(name, started_at)
