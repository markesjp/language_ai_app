from pydantic import BaseModel


class DashboardMetric(BaseModel):
    name: str
    value: float
    dimensions: dict = {}


class DashboardResponse(BaseModel):
    metrics: list[DashboardMetric]
    privacy_note: str
