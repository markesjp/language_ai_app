from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.admin import AdminLoginRequest, AdminSessionResponse
from app.services.admin_auth import (
    clear_admin_cookie,
    create_session_token,
    get_optional_admin_session,
    set_admin_cookie,
    validate_admin_password,
    verify_session_token,
)

router = APIRouter()


@router.post("/login", response_model=AdminSessionResponse)
async def login(
    payload: AdminLoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AdminSessionResponse:
    if not await validate_admin_password(session, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")
    token = create_session_token()
    set_admin_cookie(response, token)
    admin_session = verify_session_token(token)
    return AdminSessionResponse(authenticated=True, expires_at=admin_session.expires_at if admin_session else None)


@router.post("/logout", response_model=AdminSessionResponse)
async def logout(response: Response) -> AdminSessionResponse:
    clear_admin_cookie(response)
    return AdminSessionResponse(authenticated=False)


@router.get("/me", response_model=AdminSessionResponse)
async def me(admin_session=Depends(get_optional_admin_session)) -> AdminSessionResponse:
    if not admin_session:
        return AdminSessionResponse(authenticated=False)
    return AdminSessionResponse(authenticated=True, expires_at=admin_session.expires_at)
