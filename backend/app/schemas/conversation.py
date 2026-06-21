from pydantic import BaseModel, Field

from app.schemas.common import UsageSummary


class ChatRequest(BaseModel):
    user_id: str
    session_id: str | None = None
    topic: str = Field(default="daily conversation", max_length=160)
    native_language: str = "pt"
    target_language: str = "en"
    message: str = Field(min_length=1, max_length=8000)
    mode: str = "text"
    voice_enabled: bool = False
    scenario_id: str | None = None
    skill_ids: list[str] = []
    custom_scenario: str | None = Field(default=None, max_length=240)
    custom_skills: str | None = Field(default=None, max_length=400)
    voice_preset_id: str | None = None
    voice_speed: float | None = Field(default=None, ge=0.5, le=1.6)


class PedagogicalFeedback(BaseModel):
    corrected_text: str | None = None
    explanation: str
    focus_points: list[str] = []
    encouragement: str


class ChatResponse(BaseModel):
    trace_id: str
    conversation_turn_id: str
    session_id: str
    answer: str
    feedback: PedagogicalFeedback
    latency_ms: dict[str, float]
    usage: UsageSummary
