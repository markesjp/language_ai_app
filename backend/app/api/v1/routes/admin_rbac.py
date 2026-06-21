from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models import RbacPermission, RbacProfile, User
from app.schemas.rbac import (
    PermissionRead,
    RbacOverviewResponse,
    RbacProfileCreate,
    RbacProfileRead,
    RbacProfileUpdate,
    RbacUserRead,
    UserProfileAssignment,
)
from app.services.rbac import assign_profiles, effective_permissions, require_permission

router = APIRouter(dependencies=[Depends(require_permission("admin.rbac:read"))])


async def _get_profile(session: AsyncSession, profile_id: str) -> RbacProfile:
    profile = await session.scalar(
        select(RbacProfile).where(RbacProfile.id == profile_id).options(selectinload(RbacProfile.permissions))
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


async def _load_permissions(session: AsyncSession, keys: list[str]) -> list[RbacPermission]:
    if not keys:
        return []
    result = await session.execute(select(RbacPermission).where(RbacPermission.key.in_(keys)))
    permissions = list(result.scalars().all())
    if len(permissions) != len(set(keys)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more permissions do not exist")
    return permissions


def _user_read(user: User) -> RbacUserRead:
    profiles = [profile for profile in user.rbac_profiles if profile.is_active]
    return RbacUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        profile_ids=[profile.id for profile in profiles],
        profile_names=[profile.name for profile in profiles],
        permissions=effective_permissions(user),
    )


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(session: AsyncSession = Depends(get_session)) -> list[RbacPermission]:
    result = await session.execute(select(RbacPermission).order_by(RbacPermission.key))
    return list(result.scalars().all())


@router.get("/profiles", response_model=list[RbacProfileRead])
async def list_profiles(session: AsyncSession = Depends(get_session)) -> list[RbacProfile]:
    result = await session.execute(select(RbacProfile).options(selectinload(RbacProfile.permissions)).order_by(RbacProfile.name))
    return list(result.scalars().all())


@router.post("/profiles", response_model=RbacProfileRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("admin.rbac:write"))])
async def create_profile(payload: RbacProfileCreate, session: AsyncSession = Depends(get_session)) -> RbacProfile:
    profile = RbacProfile(
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
        is_system=False,
    )
    profile.permissions = await _load_permissions(session, payload.permission_keys)
    session.add(profile)
    await session.commit()
    return await _get_profile(session, profile.id)


@router.put("/profiles/{profile_id}", response_model=RbacProfileRead, dependencies=[Depends(require_permission("admin.rbac:write"))])
async def update_profile(
    profile_id: str,
    payload: RbacProfileUpdate,
    session: AsyncSession = Depends(get_session),
) -> RbacProfile:
    profile = await _get_profile(session, profile_id)
    data = payload.model_dump(exclude_unset=True)
    permission_keys = data.pop("permission_keys", None)
    for key, value in data.items():
        setattr(profile, key, value)
    if permission_keys is not None:
        profile.permissions = await _load_permissions(session, permission_keys)
    await session.commit()
    return await _get_profile(session, profile.id)


@router.get("/users", response_model=list[RbacUserRead], dependencies=[Depends(require_permission("admin.users:read"))])
async def list_users(session: AsyncSession = Depends(get_session)) -> list[RbacUserRead]:
    result = await session.execute(select(User).options(selectinload(User.rbac_profiles).selectinload(RbacProfile.permissions)).order_by(User.email))
    return [_user_read(user) for user in result.scalars().all()]


@router.put("/users/{user_id}/profiles", response_model=RbacUserRead, dependencies=[Depends(require_permission("admin.users:write"))])
async def set_user_profiles(
    user_id: str,
    payload: UserProfileAssignment,
    session: AsyncSession = Depends(get_session),
) -> RbacUserRead:
    user = await session.scalar(select(User).where(User.id == user_id).options(selectinload(User.rbac_profiles)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = await assign_profiles(session, user, payload.profile_ids)
    return _user_read(updated)


@router.get("/overview", response_model=RbacOverviewResponse, dependencies=[Depends(require_permission("admin.users:read"))])
async def overview(session: AsyncSession = Depends(get_session)) -> RbacOverviewResponse:
    permissions = await list_permissions(session)
    profiles = await list_profiles(session)
    users = await list_users(session)
    return RbacOverviewResponse(profiles=profiles, permissions=permissions, users=users)
