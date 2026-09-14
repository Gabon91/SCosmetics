from datetime import time

from pydantic import BaseModel, Field, model_validator


class WorkingHoursInput(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError("Working hours must end after they start")
        return self


class BeauticianInput(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    phone: str = Field(min_length=5, max_length=30)
    password: str = Field(min_length=8)
    bio: str = Field(default="", max_length=4000)
    treatment_ids: list[int] = Field(default_factory=list)
    working_hours: list[WorkingHoursInput] = Field(default_factory=list)
    active: bool = True


class BeauticianPatch(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, min_length=5, max_length=30)
    bio: str | None = Field(default=None, max_length=4000)
    treatment_ids: list[int] | None = None
    working_hours: list[WorkingHoursInput] | None = None
    active: bool | None = None


class BeauticianAdminRead(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    bio: str
    treatment_ids: list[int]
    working_hours: list[WorkingHoursInput]
    active: bool
