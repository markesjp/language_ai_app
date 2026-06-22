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
    gender: str = Field(default="neutral", pattern="^(female|male|neutral)$")
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
    gender: str | None = Field(default=None, pattern="^(female|male|neutral)$")
    speed: float | None = Field(default=None, ge=0.5, le=1.6)
    pitch: float | None = Field(default=None, ge=0.5, le=1.5)
    is_default: bool | None = None
    is_active: bool | None = None


class VoicePresetRead(VoicePresetBase):
    id: str

    model_config = {"from_attributes": True}


class VoicePersonalityBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    gender: str = Field(default="neutral", pattern="^(female|male|neutral)$")
    age: int | None = Field(default=None, ge=13, le=100)
    profession: str = Field(default="", max_length=120)
    hobbies: str = ""
    description: str = ""
    tone: str = Field(default="friendly", max_length=120)
    prompt_instructions: str = ""
    target_language: str | None = Field(default=None, max_length=16)
    is_active: bool = True


class VoicePersonalityCreate(VoicePersonalityBase):
    pass


class VoicePersonalityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    gender: str | None = Field(default=None, pattern="^(female|male|neutral)$")
    age: int | None = Field(default=None, ge=13, le=100)
    profession: str | None = Field(default=None, max_length=120)
    hobbies: str | None = None
    description: str | None = None
    tone: str | None = Field(default=None, max_length=120)
    prompt_instructions: str | None = None
    target_language: str | None = Field(default=None, max_length=16)
    is_active: bool | None = None


class VoicePersonalityRead(VoicePersonalityBase):
    id: str

    model_config = {"from_attributes": True}


class VoicePersonalityPublic(BaseModel):
    id: str
    name: str
    gender: str
    age: int | None
    profession: str
    hobbies: str
    description: str
    tone: str
    target_language: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class PracticeCatalogResponse(BaseModel):
    skills: list[PracticeSkillRead]
    scenarios: list[PracticeScenarioRead]
    voice_presets: list[VoicePresetRead]
    voice_personalities: list[VoicePersonalityPublic] = []
