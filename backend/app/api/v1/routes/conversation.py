from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.conversation import ChatRequest, ChatResponse
from app.services.conversation import ConversationService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, session: AsyncSession = Depends(get_session)) -> ChatResponse:
    return await ConversationService(session).chat(payload)
