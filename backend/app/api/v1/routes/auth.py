from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.models import LearnerProfile, User
from app.schemas.auth import (
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserSessionResponse,
)
from app.services.user_auth import (
    clear_user_cookie,
    create_password_reset_token,
    create_user_session_token,
    create_oauth_state,
    exchange_google_code_for_userinfo,
    get_optional_user_session,
    google_authorization_url,
    register_user,
    reset_password,
    set_user_cookie,
    upsert_google_user,
    validate_user_password,
    verify_oauth_state,
    verify_user_session_token,
)
from app.services.rbac import effective_permissions, effective_profiles, ensure_default_profile, get_user_with_profiles

router = APIRouter()


async def _user_response(session: AsyncSession, user: User, *, expires_at: int | None = None) -> UserSessionResponse:
    await ensure_default_profile(session, user)
    user = await get_user_with_profiles(session, user.id) or user
    profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    return UserSessionResponse(
        authenticated=True,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        expires_at=expires_at,
        onboarding_completed=bool(profile.onboarding_completed) if profile else False,
        recommended_scenario_id=profile.recommended_scenario_id if profile else None,
        target_language=profile.target_language if profile else None,
        proficiency_level=profile.proficiency_level if profile else None,
        learning_goal=profile.learning_goal if profile else None,
        practice_preference=profile.practice_preference if profile else None,
        voice_preference=profile.voice_preference if profile else None,
        profiles=effective_profiles(user),
        permissions=effective_permissions(user),
    )


async def _redirect_after_login(session: AsyncSession, user: User) -> str:
    profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
    if not profile or not profile.onboarding_completed:
        return settings.frontend_onboarding_url
    return settings.frontend_post_login_url


@router.post("/register", response_model=UserSessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserSessionResponse:
    user = await register_user(
        session,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        native_language=payload.native_language,
        target_language=payload.target_language,
        proficiency_level=payload.proficiency_level,
    )
    token = create_user_session_token(user)
    set_user_cookie(response, token)
    user_session = verify_user_session_token(token)
    return await _user_response(session, user, expires_at=user_session.expires_at if user_session else None)


@router.post("/login", response_model=UserSessionResponse)
async def login(
    payload: UserLoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserSessionResponse:
    user = await validate_user_password(session, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_user_session_token(user)
    set_user_cookie(response, token)
    user_session = verify_user_session_token(token)
    return await _user_response(session, user, expires_at=user_session.expires_at if user_session else None)


@router.post("/logout", response_model=UserSessionResponse)
async def logout(response: Response) -> UserSessionResponse:
    clear_user_cookie(response)
    return UserSessionResponse(authenticated=False)


@router.get("/me", response_model=UserSessionResponse)
async def me(
    user_session=Depends(get_optional_user_session),
    session: AsyncSession = Depends(get_session),
) -> UserSessionResponse:
    if not user_session:
        return UserSessionResponse(authenticated=False)
    user = await session.get(User, user_session.user_id)
    if not user:
        return UserSessionResponse(authenticated=False)
    return await _user_response(session, user, expires_at=user_session.expires_at)


@router.get("/google/start")
async def google_start() -> RedirectResponse:
    state = create_oauth_state()
    return RedirectResponse(google_authorization_url(state), status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    if not code or not verify_oauth_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Google OAuth callback")
    userinfo = await exchange_google_code_for_userinfo(code)
    user = await upsert_google_user(
        session,
        email=str(userinfo["email"]),
        display_name=str(userinfo.get("name") or userinfo["email"]).strip(),
    )
    redirect = RedirectResponse(await _redirect_after_login(session, user), status_code=status.HTTP_302_FOUND)
    set_user_cookie(redirect, create_user_session_token(user))
    return redirect


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
) -> PasswordResetRequestResponse:
    token = await create_password_reset_token(session, payload.email)
    return PasswordResetRequestResponse(
        accepted=True,
        reset_token=token if settings.environment == "development" else None,
        message="Se o email existir, um token de redefinição foi gerado.",
    )


@router.post("/password-reset/confirm", response_model=UserSessionResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_session),
) -> UserSessionResponse:
    await reset_password(session, payload.token, payload.new_password)
    return UserSessionResponse(authenticated=False)
