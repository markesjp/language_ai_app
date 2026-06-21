import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.models import AdminCredential

HASH_ITERATIONS = 210_000


@dataclass
class AdminSession:
    subject: str
    expires_at: int


def _development_password() -> str | None:
    if settings.admin_master_password:
        return settings.admin_master_password
    if settings.environment == "development":
        return "admin123"
    return None


def _hash_password(password: str, salt: str, iterations: int = HASH_ITERATIONS) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return digest.hex()


def create_password_record(password: str) -> tuple[str, str, int]:
    salt = secrets.token_hex(32)
    return _hash_password(password, salt), salt, HASH_ITERATIONS


def verify_password(password: str, credential: AdminCredential) -> bool:
    digest = _hash_password(password, credential.salt, credential.iterations)
    return secrets.compare_digest(digest, credential.password_hash)


async def bootstrap_admin_credential(session: AsyncSession) -> None:
    existing = await session.scalar(select(AdminCredential).limit(1))
    if existing:
        return

    password = _development_password()
    if not password:
        return

    password_hash, salt, iterations = create_password_record(password)
    session.add(AdminCredential(password_hash=password_hash, salt=salt, iterations=iterations))
    await session.commit()


async def validate_admin_password(session: AsyncSession, password: str) -> bool:
    credential = await session.scalar(select(AdminCredential).limit(1))
    if not credential:
        await bootstrap_admin_credential(session)
        credential = await session.scalar(select(AdminCredential).limit(1))
    if not credential:
        return False
    return verify_password(password, credential)


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def create_session_token() -> str:
    now = int(time.time())
    payload = {
        "sub": "admin",
        "iat": now,
        "exp": now + settings.admin_session_ttl_seconds,
        "nonce": secrets.token_urlsafe(16),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.admin_session_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def verify_session_token(token: str | None) -> AdminSession | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.admin_session_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("sub") != "admin":
        return None
    expires_at = int(payload.get("exp", 0))
    if expires_at < int(time.time()):
        return None
    return AdminSession(subject="admin", expires_at=expires_at)


def set_admin_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.admin_session_cookie,
        token,
        max_age=settings.admin_session_ttl_seconds,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(settings.admin_session_cookie, path="/")


async def require_admin(request: Request) -> AdminSession:
    session = verify_session_token(request.cookies.get(settings.admin_session_cookie))
    if session:
        return session
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin session required",
    )


async def get_optional_admin_session(request: Request) -> AdminSession | None:
    return verify_session_token(request.cookies.get(settings.admin_session_cookie))
