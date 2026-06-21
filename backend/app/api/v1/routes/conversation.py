from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.conversation import ChatRequest, ChatResponse
from app.services.conversation import ConversationService
from app.services.rbac import require_permission

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_permission("chat:write"))])
async def chat(payload: ChatRequest, session: AsyncSession = Depends(get_session)) -> ChatResponse:
    return await ConversationService(session).chat(payload)
