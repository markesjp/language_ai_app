from pydantic import BaseModel, Field


class PracticeSkillBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    target_language: str | None = Field(default=None, max_length=16)
    level: str | None = Field(default=None, max_length=32)
    is_active: bool = True


class PracticeSkillCreate(PracticeSkillBase):
    pass


class PracticeSkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    target_language: str | None = Field(default=None, max_length=16)
    level: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None


class PracticeSkillRead(PracticeSkillBase):
    id: str

    model_config = {"from_attributes": True}


class PracticeScenarioBase(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = ""
    prompt_template: str = Field(
        default="Practice this real-life situation with a friendly tutor style.",
        min_length=8,
    )
    target_language: str | None = Field(default=None, max_length=16)
    level: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    skill_ids: list[str] = []


class PracticeScenarioCreate(PracticeScenarioBase):
    pass


class PracticeScenarioUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    prompt_template: str | None = Field(default=None, min_length=8)
    target_language: str | None = Field(default=None, max_length=16)
    level: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    skill_ids: list[str] | None = None


class PracticeScenarioRead(BaseModel):
    id: str
    title: str
    description: str
    prompt_template: str
    target_language: str | None
    level: str | None
    is_active: bool
    skills: list[PracticeSkillRead] = []

    model_config = {"from_attributes": True}


class VoicePresetBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: str = Field(default="browser", max_length=64)
    model: str = Field(default="browser-speech-synthesis", max_length=120)
    voice: str = Field(default="", max_length=160)
    language: str = Field(default="en-US", max_length=16)
    speed: float = Field(default=0.96, ge=0.5, le=1.6)
    pitch: float = Field(default=1.0, ge=0.5, le=1.5)
    is_default: bool = False
    is_active: bool = True


class VoicePresetCreate(VoicePresetBase):
    pass


class VoicePresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=120)
    voice: str | None = Field(default=None, max_length=160)
    language: str | None = Field(default=None, max_length=16)
    speed: float | None = Field(default=None, ge=0.5, le=1.6)
    pitch: float | None = Field(default=None, ge=0.5, le=1.5)
    is_default: bool | None = None
    is_active: bool | None = None


class VoicePresetRead(VoicePresetBase):
    id: str

    model_config = {"from_attributes": True}


class PracticeCatalogResponse(BaseModel):
    skills: list[PracticeSkillRead]
    scenarios: list[PracticeScenarioRead]
    voice_presets: list[VoicePresetRead]
