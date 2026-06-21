from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    native_language: str = "pt"
    target_language: str = "en"
    proficiency_level: str = "beginner"


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=128)


class UserSessionResponse(BaseModel):
    authenticated: bool
    user_id: str | None = None
    email: str | None = None
    display_name: str | None = None
    expires_at: int | None = None
    onboarding_completed: bool = False
    recommended_scenario_id: str | None = None
    target_language: str | None = None
    proficiency_level: str | None = None
    learning_goal: str | None = None
    practice_preference: str | None = None
    voice_preference: str | None = None
    profiles: list[str] = []
    permissions: list[str] = []


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PasswordResetRequestResponse(BaseModel):
    accepted: bool = True
    reset_token: str | None = None
    message: str


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)
