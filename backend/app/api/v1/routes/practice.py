from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models import PracticeScenario, PracticeSkill, VoicePreset
from app.schemas.practice import PracticeCatalogResponse
from app.services.rbac import require_permission

router = APIRouter()


def _voice_language_prefix(target_language: str) -> str:
    return {"en": "en", "es": "es", "fr": "fr", "pt": "pt"}.get(target_language, target_language)


@router.get("/catalog", response_model=PracticeCatalogResponse)
async def catalog(
    target_language: str | None = None,
    _user=Depends(require_permission("catalog:read")),
    session: AsyncSession = Depends(get_session),
) -> PracticeCatalogResponse:
    skill_query = select(PracticeSkill).where(PracticeSkill.is_active.is_(True))
    scenario_query = select(PracticeScenario).where(PracticeScenario.is_active.is_(True))
    voice_query = select(VoicePreset).where(VoicePreset.is_active.is_(True))
    if target_language:
        skill_query = skill_query.where((PracticeSkill.target_language.is_(None)) | (PracticeSkill.target_language == target_language))
        scenario_query = scenario_query.where(
            (PracticeScenario.target_language.is_(None)) | (PracticeScenario.target_language == target_language)
        )
        prefix = _voice_language_prefix(target_language)
        voice_query = voice_query.where(VoicePreset.language.ilike(f"{prefix}%"))

    skills_result = await session.execute(
        skill_query.order_by(PracticeSkill.name)
    )
    scenarios_result = await session.execute(
        scenario_query
        .options(selectinload(PracticeScenario.skills))
        .order_by(PracticeScenario.title)
    )
    voices_result = await session.execute(
        voice_query.order_by(VoicePreset.is_default.desc(), VoicePreset.name)
    )
    return PracticeCatalogResponse(
        skills=list(skills_result.scalars().all()),
        scenarios=list(scenarios_result.scalars().all()),
        voice_presets=list(voices_result.scalars().all()),
    )
