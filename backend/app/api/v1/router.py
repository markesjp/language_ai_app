from fastapi import APIRouter

from app.api.v1.routes import (
    admin_auth,
    admin_practice,
    admin_rbac,
    admin_rag,
    admin_settings,
    analytics,
    auth,
    conversation,
    health,
    practice,
    profiles,
    speech,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(conversation.router, prefix="/conversation", tags=["conversation"])
api_router.include_router(practice.router, prefix="/practice", tags=["practice"])
api_router.include_router(speech.router, prefix="/speech", tags=["speech"])
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])
api_router.include_router(admin_practice.router, prefix="/admin", tags=["admin-practice"])
api_router.include_router(admin_rbac.router, prefix="/admin/rbac", tags=["admin-rbac"])
api_router.include_router(admin_rag.router, prefix="/admin/rag", tags=["admin-rag"])
api_router.include_router(analytics.router, prefix="/admin/analytics", tags=["analytics"])
api_router.include_router(admin_settings.router, prefix="/admin/settings", tags=["admin-settings"])
