from collections.abc import Sequence

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models import RbacPermission, RbacProfile, User
from app.core.config import settings
from app.services.admin_auth import verify_session_token
from app.services.user_auth import get_optional_user_session

PERMISSIONS: dict[str, str] = {
    "chat:read": "Acessar chat",
    "chat:write": "Enviar mensagens no chat",
    "dashboard:read": "Acessar dashboard do aluno",
    "profile:read": "Ler perfil próprio",
    "profile:write": "Editar perfil próprio",
    "catalog:read": "Ler catálogo público",
    "admin.rag:read": "Ler Admin RAG",
    "admin.rag:write": "Indexar e consultar Admin RAG",
    "admin.analytics:read": "Ler analytics administrativo",
    "admin.settings:read": "Ler configurações administrativas",
    "admin.settings:write": "Editar configurações administrativas",
    "admin.catalog:read": "Ler catálogo administrativo",
    "admin.catalog:write": "Editar catálogo administrativo",
    "admin.users:read": "Ler usuários",
    "admin.users:write": "Editar vínculos de usuários",
    "admin.rbac:read": "Ler RBAC",
    "admin.rbac:write": "Editar RBAC",
}

PROFILE_PERMISSIONS: dict[str, list[str]] = {
    "Owner": list(PERMISSIONS),
    "Admin": [
        "chat:read",
        "chat:write",
        "dashboard:read",
        "profile:read",
        "profile:write",
        "catalog:read",
        "admin.rag:read",
        "admin.rag:write",
        "admin.analytics:read",
        "admin.settings:read",
        "admin.settings:write",
        "admin.catalog:read",
        "admin.catalog:write",
        "admin.users:read",
    ],
    "Editor": ["chat:read", "chat:write", "dashboard:read", "profile:read", "profile:write", "catalog:read", "admin.catalog:read", "admin.catalog:write"],
    "Learner": ["chat:read", "chat:write", "dashboard:read", "profile:read", "profile:write", "catalog:read"],
    "Viewer": ["chat:read", "dashboard:read", "profile:read", "catalog:read"],
}

PROFILE_DESCRIPTIONS = {
    "Owner": "Acesso total ao sistema.",
    "Admin": "Administra conteúdo, RAG, analytics e configurações.",
    "Editor": "Edita catálogo e usa recursos comuns.",
    "Learner": "Usuário comum com chat, dashboard e perfil.",
    "Viewer": "Leitura limitada.",
}


async def bootstrap_rbac(session: AsyncSession) -> None:
    result = await session.execute(select(RbacPermission))
    permissions_by_key = {permission.key: permission for permission in result.scalars().all()}
    for key, description in PERMISSIONS.items():
        permission = permissions_by_key.get(key)
        if not permission:
            permission = RbacPermission(key=key, description=description)
            session.add(permission)
            permissions_by_key[key] = permission
        else:
            permission.description = description
    await session.flush()

    profile_result = await session.execute(select(RbacProfile).options(selectinload(RbacProfile.permissions)))
    profiles_by_name = {profile.name: profile for profile in profile_result.scalars().all()}
    for name, permission_keys in PROFILE_PERMISSIONS.items():
        profile = profiles_by_name.get(name)
        if not profile:
            profile = RbacProfile(name=name, is_system=True)
            session.add(profile)
        profile.description = PROFILE_DESCRIPTIONS[name]
        profile.is_system = True
        profile.is_active = True
        profile.permissions = [permissions_by_key[key] for key in permission_keys if key in permissions_by_key]
    await session.commit()


async def get_user_with_profiles(session: AsyncSession, user_id: str) -> User | None:
    return await session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.rbac_profiles).selectinload(RbacProfile.permissions))
    )


def effective_permissions(user: User) -> list[str]:
    keys = {
        permission.key
        for profile in user.rbac_profiles
        if profile.is_active
        for permission in profile.permissions
    }
    return sorted(keys)


def effective_profiles(user: User) -> list[str]:
    return sorted(profile.name for profile in user.rbac_profiles if profile.is_active)


async def ensure_default_profile(session: AsyncSession, user: User, profile_name: str = "Learner") -> None:
    if user.rbac_profiles:
        return
    profile = await session.scalar(select(RbacProfile).where(RbacProfile.name == profile_name))
    if not profile:
        await bootstrap_rbac(session)
        profile = await session.scalar(select(RbacProfile).where(RbacProfile.name == profile_name))
    if profile:
        user.rbac_profiles = [profile]
        await session.commit()


async def assign_profiles(session: AsyncSession, user: User, profile_ids: Sequence[str]) -> User:
    result = await session.execute(select(RbacProfile).where(RbacProfile.id.in_(list(profile_ids))))
    profiles = list(result.scalars().all())
    if len(profiles) != len(set(profile_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more profiles do not exist")
    user.rbac_profiles = profiles
    await session.commit()
    return await get_user_with_profiles(session, user.id) or user


def has_permission(user: User, permission: str) -> bool:
    return permission in effective_permissions(user)


def require_permission(permission: str):
    async def dependency(
        request: Request,
        user_session=Depends(get_optional_user_session),
        session: AsyncSession = Depends(get_session),
    ) -> User | None:
        legacy_admin = verify_session_token(request.cookies.get(settings.admin_session_cookie))
        if legacy_admin and permission.startswith("admin."):
            request.state.rbac_legacy_admin = True
            return None
        if not user_session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User session required")
        user = await get_user_with_profiles(session, user_session.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User session required")
        await ensure_default_profile(session, user)
        user = await get_user_with_profiles(session, user.id) or user
        if has_permission(user, permission):
            request.state.rbac_user = user
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")

    return dependency
