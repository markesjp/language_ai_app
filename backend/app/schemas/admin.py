from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class AdminSessionResponse(BaseModel):
    authenticated: bool
    expires_at: int | None = None


class AdminSettingItem(BaseModel):
    key: str
    label: str
    category: str
    value: object | None = None
    masked_value: str | None = None
    editable: bool = False
    secret: bool = False
    requires_restart: bool = False
    description: str
    options: list[str] = []


class AdminSettingsResponse(BaseModel):
    settings: list[AdminSettingItem]
    warnings: list[str] = []


class AdminSettingsUpdate(BaseModel):
    values: dict[str, object]
