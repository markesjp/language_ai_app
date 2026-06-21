from pydantic import BaseModel, Field


class PermissionRead(BaseModel):
    key: str
    description: str

    model_config = {"from_attributes": True}


class RbacProfileBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=255)
    is_active: bool = True
    permission_keys: list[str] = []


class RbacProfileCreate(RbacProfileBase):
    pass


class RbacProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    permission_keys: list[str] | None = None


class RbacProfileRead(BaseModel):
    id: str
    name: str
    description: str
    is_system: bool
    is_active: bool
    permissions: list[PermissionRead] = []

    model_config = {"from_attributes": True}


class RbacUserRead(BaseModel):
    id: str
    email: str
    display_name: str
    profile_ids: list[str] = []
    profile_names: list[str] = []
    permissions: list[str] = []


class UserProfileAssignment(BaseModel):
    profile_ids: list[str]


class RbacOverviewResponse(BaseModel):
    profiles: list[RbacProfileRead]
    permissions: list[PermissionRead]
    users: list[RbacUserRead]
