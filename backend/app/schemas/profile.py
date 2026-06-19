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
