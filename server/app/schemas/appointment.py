from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    treatment_id: int = Field(gt=0)
    beautician_id: int = Field(gt=0)
    start_time: datetime
    user_package_id: int | None = Field(default=None, gt=0)

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("start_time must include a timezone offset")

        start_utc = value.astimezone(UTC)
        if (
            start_utc.minute % 15 != 0
            or start_utc.second != 0
            or start_utc.microsecond != 0
        ):
            raise ValueError("start_time must be on a 15-minute boundary")
        return value


class StaffAppointmentCreate(AppointmentCreate):
    customer_id: int = Field(gt=0)


class AppointmentReschedule(BaseModel):
    beautician_id: int = Field(gt=0)
    start_time: datetime

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: datetime) -> datetime:
        return AppointmentCreate.validate_start_time(value)


class AppointmentRead(BaseModel):
    id: int
    customer_id: int
    beautician_id: int
    treatment_id: int
    user_package_id: int | None
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("start_time", "end_time", "completed_at")
    @classmethod
    def expose_utc_offset(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class AvailabilitySlotRead(BaseModel):
    beautician_id: int
    beautician_name: str
    start_time: datetime
    end_time: datetime

    model_config = ConfigDict(from_attributes=True)


class AvailabilityResponse(BaseModel):
    date: date
    treatment_id: int
    treatment_name: str
    duration_minutes: int
    slots: list[AvailabilitySlotRead]
