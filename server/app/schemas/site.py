from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentUpdate(BaseModel):
    values: dict[str, str] = Field(min_length=1)


class EquipmentInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    manufacturer: str = Field(default="", max_length=120)
    description: str = Field(min_length=2)
    image_url: str = Field(default="", max_length=500)
    treatment_ids: list[int] = Field(default_factory=list)
    active: bool = True

    @field_validator("image_url")
    @classmethod
    def local_image_only(cls, value: str) -> str:
        if value and not value.startswith("/images/"):
            raise ValueError("Image must be a local /images/ path")
        return value


class EquipmentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    manufacturer: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, min_length=2)
    image_url: str | None = Field(default=None, max_length=500)
    treatment_ids: list[int] | None = None
    active: bool | None = None

    @field_validator("image_url")
    @classmethod
    def local_image_only(cls, value: str | None) -> str | None:
        if value and not value.startswith("/images/"):
            raise ValueError("Image must be a local /images/ path")
        return value


class EquipmentRead(EquipmentInput):
    id: int


class TeamMemberInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=2, max_length=4000)
    image_url: str = Field(default="", max_length=500)
    featured: bool = False
    display_order: int = Field(default=0, ge=0)
    active: bool = True

    @field_validator("image_url")
    @classmethod
    def local_image_only(cls, value: str) -> str:
        if value and not value.startswith("/images/"):
            raise ValueError("Image must be a local /images/ path")
        return value


class TeamMemberPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=2, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)
    featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    active: bool | None = None

    @field_validator("image_url")
    @classmethod
    def local_image_only(cls, value: str | None) -> str | None:
        if value and not value.startswith("/images/"):
            raise ValueError("Image must be a local /images/ path")
        return value


class TeamMemberRead(TeamMemberInput):
    id: int
    model_config = ConfigDict(from_attributes=True)
