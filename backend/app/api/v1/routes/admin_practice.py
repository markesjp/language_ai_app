from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models import PracticeScenario, PracticeSkill, VoicePersonality, VoicePreset
from app.schemas.practice import (
    PracticeScenarioCreate,
    PracticeScenarioRead,
    PracticeScenarioUpdate,
    PracticeSkillCreate,
    PracticeSkillRead,
    PracticeSkillUpdate,
    VoicePresetCreate,
    VoicePresetRead,
    VoicePresetUpdate,
    VoicePersonalityCreate,
    VoicePersonalityRead,
    VoicePersonalityUpdate,
)
from app.services.rbac import require_permission

router = APIRouter(dependencies=[Depends(require_permission("admin.catalog:read"))])


async def _get_skill(session: AsyncSession, skill_id: str) -> PracticeSkill:
    skill = await session.get(PracticeSkill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


async def _get_scenario(session: AsyncSession, scenario_id: str) -> PracticeScenario:
    scenario = await session.scalar(
        select(PracticeScenario)
        .where(PracticeScenario.id == scenario_id)
        .options(selectinload(PracticeScenario.skills))
    )
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return scenario


async def _get_voice_preset(session: AsyncSession, preset_id: str) -> VoicePreset:
    preset = await session.get(VoicePreset, preset_id)
    if not preset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice preset not found")
    return preset


async def _get_voice_personality(session: AsyncSession, personality_id: str) -> VoicePersonality:
    personality = await session.get(VoicePersonality, personality_id)
    if not personality:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice personality not found")
    return personality


async def _load_skills(session: AsyncSession, skill_ids: list[str]) -> list[PracticeSkill]:
    if not skill_ids:
        return []
    result = await session.execute(select(PracticeSkill).where(PracticeSkill.id.in_(skill_ids)))
    skills = list(result.scalars().all())
    if len(skills) != len(set(skill_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skills do not exist")
    return skills


async def _ensure_single_default(session: AsyncSession, selected: VoicePreset) -> None:
    if not selected.is_default:
        return
    result = await session.execute(select(VoicePreset).where(VoicePreset.id != selected.id))
    for preset in result.scalars().all():
        preset.is_default = False


@router.get("/skills", response_model=list[PracticeSkillRead])
async def list_skills(session: AsyncSession = Depends(get_session)) -> list[PracticeSkill]:
    result = await session.execute(select(PracticeSkill).order_by(PracticeSkill.name))
    return list(result.scalars().all())


@router.post("/skills", response_model=PracticeSkillRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def create_skill(payload: PracticeSkillCreate, session: AsyncSession = Depends(get_session)) -> PracticeSkill:
    skill = PracticeSkill(**payload.model_dump())
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return skill


@router.put("/skills/{skill_id}", response_model=PracticeSkillRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def update_skill(
    skill_id: str,
    payload: PracticeSkillUpdate,
    session: AsyncSession = Depends(get_session),
) -> PracticeSkill:
    skill = await _get_skill(session, skill_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(skill, key, value)
    await session.commit()
    await session.refresh(skill)
    return skill


@router.delete("/skills/{skill_id}", response_model=PracticeSkillRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def delete_skill(skill_id: str, session: AsyncSession = Depends(get_session)) -> PracticeSkill:
    skill = await _get_skill(session, skill_id)
    skill.is_active = False
    await session.commit()
    await session.refresh(skill)
    return skill


@router.get("/scenarios", response_model=list[PracticeScenarioRead])
async def list_scenarios(session: AsyncSession = Depends(get_session)) -> list[PracticeScenario]:
    result = await session.execute(
        select(PracticeScenario).options(selectinload(PracticeScenario.skills)).order_by(PracticeScenario.title)
    )
    return list(result.scalars().all())


@router.post("/scenarios", response_model=PracticeScenarioRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def create_scenario(
    payload: PracticeScenarioCreate,
    session: AsyncSession = Depends(get_session),
) -> PracticeScenario:
    data = payload.model_dump()
    skill_ids = data.pop("skill_ids")
    scenario = PracticeScenario(**data)
    scenario.skills = await _load_skills(session, skill_ids)
    session.add(scenario)
    await session.commit()
    return await _get_scenario(session, scenario.id)


@router.put("/scenarios/{scenario_id}", response_model=PracticeScenarioRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def update_scenario(
    scenario_id: str,
    payload: PracticeScenarioUpdate,
    session: AsyncSession = Depends(get_session),
) -> PracticeScenario:
    scenario = await _get_scenario(session, scenario_id)
    data = payload.model_dump(exclude_unset=True)
    skill_ids = data.pop("skill_ids", None)
    for key, value in data.items():
        setattr(scenario, key, value)
    if skill_ids is not None:
        scenario.skills = await _load_skills(session, skill_ids)
    await session.commit()
    return await _get_scenario(session, scenario.id)


@router.delete("/scenarios/{scenario_id}", response_model=PracticeScenarioRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def delete_scenario(scenario_id: str, session: AsyncSession = Depends(get_session)) -> PracticeScenario:
    scenario = await _get_scenario(session, scenario_id)
    scenario.is_active = False
    await session.commit()
    return await _get_scenario(session, scenario.id)


@router.get("/voice-presets", response_model=list[VoicePresetRead])
async def list_voice_presets(session: AsyncSession = Depends(get_session)) -> list[VoicePreset]:
    result = await session.execute(select(VoicePreset).order_by(VoicePreset.is_default.desc(), VoicePreset.name))
    return list(result.scalars().all())


@router.post("/voice-presets", response_model=VoicePresetRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def create_voice_preset(
    payload: VoicePresetCreate,
    session: AsyncSession = Depends(get_session),
) -> VoicePreset:
    preset = VoicePreset(**payload.model_dump())
    session.add(preset)
    await session.flush()
    await _ensure_single_default(session, preset)
    await session.commit()
    await session.refresh(preset)
    return preset


@router.put("/voice-presets/{preset_id}", response_model=VoicePresetRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def update_voice_preset(
    preset_id: str,
    payload: VoicePresetUpdate,
    session: AsyncSession = Depends(get_session),
) -> VoicePreset:
    preset = await _get_voice_preset(session, preset_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(preset, key, value)
    await _ensure_single_default(session, preset)
    await session.commit()
    await session.refresh(preset)
    return preset


@router.delete("/voice-presets/{preset_id}", response_model=VoicePresetRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def delete_voice_preset(preset_id: str, session: AsyncSession = Depends(get_session)) -> VoicePreset:
    preset = await _get_voice_preset(session, preset_id)
    preset.is_active = False
    await session.commit()
    await session.refresh(preset)
    return preset


@router.get("/voice-personalities", response_model=list[VoicePersonalityRead])
async def list_voice_personalities(session: AsyncSession = Depends(get_session)) -> list[VoicePersonality]:
    result = await session.execute(select(VoicePersonality).order_by(VoicePersonality.gender, VoicePersonality.name))
    return list(result.scalars().all())


@router.post("/voice-personalities", response_model=VoicePersonalityRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def create_voice_personality(
    payload: VoicePersonalityCreate,
    session: AsyncSession = Depends(get_session),
) -> VoicePersonality:
    personality = VoicePersonality(**payload.model_dump())
    session.add(personality)
    await session.commit()
    await session.refresh(personality)
    return personality


@router.put("/voice-personalities/{personality_id}", response_model=VoicePersonalityRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def update_voice_personality(
    personality_id: str,
    payload: VoicePersonalityUpdate,
    session: AsyncSession = Depends(get_session),
) -> VoicePersonality:
    personality = await _get_voice_personality(session, personality_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(personality, key, value)
    await session.commit()
    await session.refresh(personality)
    return personality


@router.delete("/voice-personalities/{personality_id}", response_model=VoicePersonalityRead, dependencies=[Depends(require_permission("admin.catalog:write"))])
async def delete_voice_personality(personality_id: str, session: AsyncSession = Depends(get_session)) -> VoicePersonality:
    personality = await _get_voice_personality(session, personality_id)
    personality.is_active = False
    await session.commit()
    await session.refresh(personality)
    return personality
