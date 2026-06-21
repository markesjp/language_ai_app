from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    email: str
    display_name: str = Field(min_length=1, max_length=120)
    native_language: str = "pt"
    target_language: str = "en"
    proficiency_level: str = "beginner"
    age_range: str | None = None
    gender: str | None = None
    correction_preference: str = "friendly"
    voice_preference: str | None = None


class ProfileRead(ProfileCreate):
    user_id: str
    is_admin: bool = False
    learning_goal: str | None = None
    practice_preference: str | None = None
    onboarding_completed: bool = False
    recommended_scenario_id: str | None = None


class OnboardingUpdate(BaseModel):
    target_language: str = "en"
    proficiency_level: str = "beginner"
    learning_goal: str = Field(default="conversation", max_length=64)
    practice_preference: str = Field(default="guided", max_length=64)
    voice_preference: str | None = Field(default=None, max_length=64)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    native_language: str | None = Field(default=None, max_length=16)
    target_language: str | None = Field(default=None, max_length=16)
    proficiency_level: str | None = Field(default=None, max_length=32)
    correction_preference: str | None = Field(default=None, max_length=32)
    voice_preference: str | None = Field(default=None, max_length=64)
    learning_goal: str | None = Field(default=None, max_length=64)
    practice_preference: str | None = Field(default=None, max_length=64)


class OnboardingResponse(BaseModel):
    onboarding_completed: bool
    recommended_scenario_id: str | None = None
    recommended_scenario_title: str | None = None


class LearnerDashboardResponse(BaseModel):
    streak_days: int
    practice_minutes: int
    conversation_turns: int
    skills_trained: list[str]
    last_session_topic: str | None = None
    recommendation: str
