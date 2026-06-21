from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import ConversationSession, ConversationTurn, LearnerProfile, PracticeScenario, User
from app.schemas.profile import (
    LearnerDashboardResponse,
    OnboardingResponse,
    OnboardingUpdate,
    ProfileCreate,
    ProfileRead,
    ProfileUpdate,
)
from app.services.rbac import require_permission
from app.services.user_auth import require_user

router = APIRouter()


def _profile_response(user: User, profile: LearnerProfile, email: str | None = None) -> ProfileRead:
    return ProfileRead(
        user_id=user.id,
        email=email or user.email,
        display_name=user.display_name,
        native_language=profile.native_language,
        target_language=profile.target_language,
        proficiency_level=profile.proficiency_level,
        age_range=profile.age_range,
        gender=profile.gender,
        correction_preference=profile.correction_preference,
        voice_preference=profile.voice_preference,
        is_admin=user.is_admin,
        learning_goal=profile.learning_goal,
        practice_preference=profile.practice_preference,
        onboarding_completed=profile.onboarding_completed,
        recommended_scenario_id=profile.recommended_scenario_id,
    )


def _pick_scenario(goal: str, scenarios: list[PracticeScenario], target_language: str | None = None) -> PracticeScenario | None:
    normalized_goal = goal.lower()
    if target_language:
        language_matches = [scenario for scenario in scenarios if scenario.target_language in {None, target_language}]
        if language_matches:
            scenarios = language_matches
    preferred_terms = ["entrevista"] if any(term in normalized_goal for term in ["work", "job", "trabalho", "entrevista"]) else []
    preferred_terms += ["viagem", "hotel"] if any(term in normalized_goal for term in ["travel", "viagem", "turismo"]) else []
    preferred_terms += ["café", "cafeteria", "apresent"] if not preferred_terms else []
    for term in preferred_terms:
        for scenario in scenarios:
            if term in scenario.title.lower():
                return scenario
    return scenarios[0] if scenarios else None


@router.post("", response_model=ProfileRead)
async def create_profile(payload: ProfileCreate, session: AsyncSession = Depends(get_session)) -> ProfileRead:
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=payload.email, display_name=payload.display_name)
    session.add(user)
    await session.flush()
    profile = LearnerProfile(
        user_id=user.id,
        native_language=payload.native_language,
        target_language=payload.target_language,
        proficiency_level=payload.proficiency_level,
        age_range=payload.age_range,
        gender=payload.gender,
        correction_preference=payload.correction_preference,
        voice_preference=payload.voice_preference,
    )
    session.add(profile)
    await session.commit()
    return _profile_response(user, profile, payload.email)


@router.patch("/me/onboarding", response_model=OnboardingResponse)
async def save_onboarding(
    payload: OnboardingUpdate,
    _user=Depends(require_permission("profile:write")),
    user_session=Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingResponse:
    user = await session.get(User, user_session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile:
        profile = LearnerProfile(user_id=user.id)
        session.add(profile)
        await session.flush()

    scenarios_result = await session.execute(
        select(PracticeScenario).where(PracticeScenario.is_active.is_(True)).order_by(PracticeScenario.title)
    )
    recommended = _pick_scenario(payload.learning_goal, list(scenarios_result.scalars().all()), payload.target_language)
    profile.target_language = payload.target_language
    profile.proficiency_level = payload.proficiency_level
    profile.learning_goal = payload.learning_goal
    profile.practice_preference = payload.practice_preference
    profile.voice_preference = payload.voice_preference
    profile.onboarding_completed = True
    profile.recommended_scenario_id = recommended.id if recommended else None
    await session.commit()
    return OnboardingResponse(
        onboarding_completed=True,
        recommended_scenario_id=recommended.id if recommended else None,
        recommended_scenario_title=recommended.title if recommended else None,
    )


@router.get("/me", response_model=ProfileRead)
async def get_my_profile(
    _user=Depends(require_permission("profile:read")),
    user_session=Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileRead:
    user = await session.get(User, user_session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile:
        profile = LearnerProfile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return _profile_response(user, profile)


@router.patch("/me", response_model=ProfileRead)
async def update_my_profile(
    payload: ProfileUpdate,
    _user=Depends(require_permission("profile:write")),
    user_session=Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileRead:
    user = await session.get(User, user_session.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile:
        profile = LearnerProfile(user_id=user.id)
        session.add(profile)
        await session.flush()
    data = payload.model_dump(exclude_unset=True)
    display_name = data.pop("display_name", None)
    if display_name is not None:
        user.display_name = display_name
    for key, value in data.items():
        setattr(profile, key, value)
    if any(key in data for key in {"target_language", "learning_goal", "proficiency_level"}):
        scenarios_result = await session.execute(
            select(PracticeScenario).where(PracticeScenario.is_active.is_(True)).order_by(PracticeScenario.title)
        )
        recommended = _pick_scenario(profile.learning_goal or "conversation", list(scenarios_result.scalars().all()), profile.target_language)
        profile.recommended_scenario_id = recommended.id if recommended else None
    await session.commit()
    await session.refresh(user)
    await session.refresh(profile)
    return _profile_response(user, profile)


@router.get("/me/dashboard", response_model=LearnerDashboardResponse)
async def learner_dashboard(
    _user=Depends(require_permission("dashboard:read")),
    user_session=Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> LearnerDashboardResponse:
    profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_session.user_id))
    sessions_result = await session.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == user_session.user_id)
        .order_by(ConversationSession.created_at.desc())
    )
    sessions = list(sessions_result.scalars().all())
    turns_result = await session.execute(select(ConversationTurn).where(ConversationTurn.user_id == user_session.user_id))
    turns = list(turns_result.scalars().all())
    focus = [profile.learning_goal] if profile and profile.learning_goal else []
    if profile and profile.practice_preference:
        focus.append(profile.practice_preference)
    return LearnerDashboardResponse(
        streak_days=1 if turns else 0,
        practice_minutes=max(0, len(turns) * 2),
        conversation_turns=len(turns),
        skills_trained=focus or ["conversação"],
        last_session_topic=sessions[0].topic if sessions else None,
        recommendation="Faça uma conversa curta hoje para manter o ritmo.",
    )


@router.get("/{user_id}", response_model=ProfileRead)
async def get_profile(user_id: str, session: AsyncSession = Depends(get_session)) -> ProfileRead:
    result = await session.execute(
        select(User, LearnerProfile).join(LearnerProfile, LearnerProfile.user_id == User.id).where(User.id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    user, profile = row
    return _profile_response(user, profile)
