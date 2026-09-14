from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.user import UserRole

Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=80),
]
Phone = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=7,
        max_length=30,
        pattern=r"^[0-9+()\-\s]+$",
    ),
]


class UserRegistrationRequest(BaseModel):
    first_name: Name
    last_name: Name
    email: EmailStr
    phone: Phone
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_matching_passwords(self) -> "UserRegistrationRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match")
        return self


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_token_expires_in: int
    refresh_token_expires_in: int

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    role: UserRole
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerProfilePatch(BaseModel):
    first_name: Name | None = None
    last_name: Name | None = None
    email: EmailStr | None = None
    phone: Phone | None = None


class CustomerAdminPatch(CustomerProfilePatch):
    active: bool | None = None
