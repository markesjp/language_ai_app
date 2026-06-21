from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LlmUsage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0


@dataclass
class LlmResult:
    text: str
    usage: LlmUsage


class LlmProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str, max_output_tokens: int | None = None) -> LlmResult:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError
