from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
