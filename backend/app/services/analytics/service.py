from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationTurn, LearnerProfile, UsageLedger
from app.schemas.analytics import DashboardMetric, DashboardResponse


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def dashboard(self) -> DashboardResponse:
        profiles_count = await self.session.scalar(select(func.count()).select_from(LearnerProfile))
        turns_count = await self.session.scalar(select(func.count()).select_from(ConversationTurn))
        cost_sum = await self.session.scalar(select(func.coalesce(func.sum(UsageLedger.estimated_cost_usd), 0)))

        language_rows = await self.session.execute(
            select(LearnerProfile.target_language, func.count())
            .group_by(LearnerProfile.target_language)
            .order_by(func.count().desc())
        )
        metrics = [
            DashboardMetric(name="learners_total", value=float(profiles_count or 0)),
            DashboardMetric(name="conversation_turns_total", value=float(turns_count or 0)),
            DashboardMetric(name="estimated_cost_usd_total", value=float(cost_sum or 0)),
        ]
        metrics.extend(
            DashboardMetric(
                name="target_language_distribution",
                value=float(count),
                dimensions={"target_language": language},
            )
            for language, count in language_rows.all()
        )
        return DashboardResponse(
            metrics=metrics,
            privacy_note="Dashboard usa dados agregados e não expõe PII, conversas privadas ou áudio bruto.",
        )
