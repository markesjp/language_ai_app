from fastapi import APIRouter

from app.api.v1.routes import admin_rag, analytics, conversation, health, profiles, speech

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(conversation.router, prefix="/conversation", tags=["conversation"])
api_router.include_router(speech.router, prefix="/speech", tags=["speech"])
api_router.include_router(admin_rag.router, prefix="/admin/rag", tags=["admin-rag"])
api_router.include_router(analytics.router, prefix="/admin/analytics", tags=["analytics"])
