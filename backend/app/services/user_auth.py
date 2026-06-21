import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import LearnerProfile, PasswordResetToken, User
from app.services.admin_auth import create_password_record


@dataclass
class UserSession:
    user_id: str
    email: str
    display_name: str
    expires_at: int


def _hash_password(password: str, salt: str, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return digest.hex()


def _verify_user_password(password: str, user: User) -> bool:
    if not user.password_hash or not user.salt:
        return False
    digest = _hash_password(password, user.salt, user.iterations)
    return secrets.compare_digest(digest, user.password_hash)


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session_token(user: User) -> str:
    now = int(time.time())
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.display_name,
        "iat": now,
        "exp": now + settings.user_session_ttl_seconds,
        "nonce": secrets.token_urlsafe(16),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.user_session_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def create_oauth_state() -> str:
    now = int(time.time())
    payload = {"iat": now, "exp": now + 600, "nonce": secrets.token_urlsafe(16)}
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.user_session_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_oauth_state(state: str | None) -> bool:
    if not state or "." not in state:
        return False
    body, signature = state.rsplit(".", 1)
    expected = hmac.new(settings.user_session_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, json.JSONDecodeError):
        return False
    return int(payload.get("exp", 0)) >= int(time.time())


def google_authorization_url(state: str) -> str:
    if not settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured")
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


def verify_user_session_token(token: str | None) -> UserSession | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.user_session_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, json.JSONDecodeError):
        return None
    expires_at = int(payload.get("exp", 0))
    if expires_at < int(time.time()):
        return None
    return UserSession(
        user_id=str(payload.get("sub")),
        email=str(payload.get("email")),
        display_name=str(payload.get("name")),
        expires_at=expires_at,
    )


def set_user_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.user_session_cookie,
        token,
        max_age=settings.user_session_ttl_seconds,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_user_cookie(response: Response) -> None:
    response.delete_cookie(settings.user_session_cookie, path="/")


async def require_user(request: Request) -> UserSession:
    session = verify_user_session_token(request.cookies.get(settings.user_session_cookie))
    if session:
        return session
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User session required")


async def get_optional_user_session(request: Request) -> UserSession | None:
    return verify_user_session_token(request.cookies.get(settings.user_session_cookie))


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    native_language: str,
    target_language: str,
    proficiency_level: str,
) -> User:
    normalized_email = email.lower().strip()
    existing = await session.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    password_hash, salt, iterations = create_password_record(password)
    user = User(
        email=normalized_email,
        display_name=display_name,
        password_hash=password_hash,
        salt=salt,
        iterations=iterations,
    )
    session.add(user)
    await session.flush()
    session.add(
        LearnerProfile(
            user_id=user.id,
            native_language=native_language,
            target_language=target_language,
            proficiency_level=proficiency_level,
        )
    )
    await session.commit()
    await session.refresh(user)
    return user


async def upsert_google_user(session: AsyncSession, *, email: str, display_name: str) -> User:
    normalized_email = email.lower().strip()
    user = await session.scalar(select(User).where(User.email == normalized_email))
    if user:
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        profile = await session.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        if not profile:
            session.add(LearnerProfile(user_id=user.id))
        await session.commit()
        await session.refresh(user)
        return user

    user = User(email=normalized_email, display_name=display_name or normalized_email.split("@")[0])
    session.add(user)
    await session.flush()
    session.add(LearnerProfile(user_id=user.id))
    await session.commit()
    await session.refresh(user)
    return user


async def exchange_google_code_for_userinfo(code: str) -> dict:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured")
    async with httpx.AsyncClient(timeout=12) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google token exchange failed")
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google access token missing")
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google userinfo failed")
        userinfo = userinfo_response.json()
        if not userinfo.get("email"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google email missing")
        return userinfo


async def validate_user_password(session: AsyncSession, email: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not _verify_user_password(password, user):
        return None
    return user


async def create_password_reset_token(session: AsyncSession, email: str) -> str | None:
    user = await session.scalar(select(User).where(User.email == email.lower().strip()))
    if not user:
        return None
    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_token_hash(token),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.password_reset_ttl_seconds),
    )
    session.add(reset)
    await session.commit()
    return token


async def reset_password(session: AsyncSession, token: str, new_password: str) -> None:
    reset = await session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == _token_hash(token)))
    now = datetime.now(UTC)
    if not reset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if reset.used_at or expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user = await session.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    password_hash, salt, iterations = create_password_record(new_password)
    user.password_hash = password_hash
    user.salt = salt
    user.iterations = iterations
    reset.used_at = now
    await session.commit()
