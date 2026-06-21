import hashlib
import math

from app.services.ai_providers.base import EmbeddingProvider, LlmProvider, LlmResult, LlmUsage


class MockLlmProvider(LlmProvider):
    name = "mock"
    model = "mock-teacher-001"

    async def complete(self, system_prompt: str, user_prompt: str, max_output_tokens: int | None = None) -> LlmResult:
        input_tokens = max(1, (len(system_prompt) + len(user_prompt)) // 4)
        answer = (
            "Claro! Vamos praticar juntos. "
            "Vou responder de forma natural e, quando houver erro, corrigir com gentileza. "
            f"Sobre o que você disse: {user_prompt[:240]}"
        )
        output_tokens = max(1, len(answer) // 4)
        return LlmResult(
            text=answer,
            usage=LlmUsage(
                provider=self.name,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=0,
            ),
        )


class MockEmbeddingProvider(EmbeddingProvider):
    name = "mock"
    model = "hash-embedding-64"

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [(byte / 255.0) for byte in digest + digest]
        magnitude = math.sqrt(sum(value * value for value in values)) or 1
        return [round(value / magnitude, 6) for value in values]
