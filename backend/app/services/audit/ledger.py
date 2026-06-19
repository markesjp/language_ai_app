from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UsageLedger
from app.services.ai_providers.base import LlmUsage
from app.services.speech.interfaces import SpeechUsage


async def record_llm_usage(
    session: AsyncSession,
    *,
    trace_id: str,
    user_id: str | None,
    feature: str,
    usage: LlmUsage,
) -> None:
    session.add(
        UsageLedger(
            trace_id=trace_id,
            user_id=user_id,
            feature=feature,
            provider=usage.provider,
            model=usage.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
            estimated_cost_usd=usage.estimated_cost_usd,
        )
    )


async def record_speech_usage(
    session: AsyncSession,
    *,
    trace_id: str,
    user_id: str | None,
    feature: str,
    usage: SpeechUsage,
) -> None:
    session.add(
        UsageLedger(
            trace_id=trace_id,
            user_id=user_id,
            feature=feature,
            provider=usage.provider,
            model=usage.model,
            audio_seconds=usage.audio_seconds,
            tts_characters=usage.tts_characters,
            estimated_cost_usd=usage.estimated_cost_usd,
        )
    )
