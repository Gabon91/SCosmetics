from decimal import Decimal

from pydantic import BaseModel, Field


class TreatmentInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2)
    duration_minutes: int = Field(gt=0, multiple_of=15)
    price: Decimal = Field(ge=0)
    accent: str = Field(default="light-pink", max_length=20)
    active: bool = True


class TreatmentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, min_length=2)
    duration_minutes: int | None = Field(default=None, gt=0, multiple_of=15)
    price: Decimal | None = Field(default=None, ge=0)
    accent: str | None = Field(default=None, max_length=20)
    active: bool | None = None


class TreatmentAdminRead(TreatmentInput):
    id: int


class PackageInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    price: Decimal = Field(ge=0)
    sessions: int = Field(gt=0)
    validity_days: int = Field(gt=0)
    treatment_ids: list[int] = Field(min_length=1)
    active: bool = True


class PackagePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    price: Decimal | None = Field(default=None, ge=0)
    sessions: int | None = Field(default=None, gt=0)
    validity_days: int | None = Field(default=None, gt=0)
    treatment_ids: list[int] | None = Field(default=None, min_length=1)
    active: bool | None = None


class PackageAdminRead(PackageInput):
    id: int
