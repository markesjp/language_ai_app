from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.analytics import DashboardResponse
from app.services.analytics.service import AnalyticsService

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(session: AsyncSession = Depends(get_session)) -> DashboardResponse:
    return await AnalyticsService(session).dashboard()
