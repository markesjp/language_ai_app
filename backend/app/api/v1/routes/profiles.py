from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import LearnerProfile, User
from app.schemas.profile import ProfileCreate, ProfileRead

router = APIRouter()


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
    return ProfileRead(user_id=user.id, is_admin=user.is_admin, **payload.model_dump())


@router.get("/{user_id}", response_model=ProfileRead)
async def get_profile(user_id: str, session: AsyncSession = Depends(get_session)) -> ProfileRead:
    result = await session.execute(
        select(User, LearnerProfile).join(LearnerProfile, LearnerProfile.user_id == User.id).where(User.id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    user, profile = row
    return ProfileRead(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        native_language=profile.native_language,
        target_language=profile.target_language,
        proficiency_level=profile.proficiency_level,
        age_range=profile.age_range,
        gender=profile.gender,
        correction_preference=profile.correction_preference,
        voice_preference=profile.voice_preference,
        is_admin=user.is_admin,
    )
