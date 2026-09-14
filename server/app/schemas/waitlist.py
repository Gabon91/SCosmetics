from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.core.config import settings


class WaitlistCreate(BaseModel):
    treatment_id: int = Field(gt=0)
    preferred_date: date
    beautician_id: int | None = Field(default=None, gt=0)


class WaitlistRead(BaseModel):
    id: int
    treatment_id: int
    preferred_date: date
    beautician_id: int | None
    status: WaitlistStatus
    offered_start_time: datetime | None
    offered_end_time: datetime | None
    offer_expires_at: datetime | None
    offer_expired: bool


def waitlist_read(entry: WaitlistEntry) -> WaitlistRead:
    expires = entry.offer_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    business_timezone = ZoneInfo(settings.business_timezone)

    def local_time(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(business_timezone)

    return WaitlistRead(
        id=entry.id,
        treatment_id=entry.treatment_id,
        preferred_date=entry.preferred_date,
        beautician_id=entry.beautician_id,
        status=entry.status,
        offered_start_time=local_time(entry.offered_start_time),
        offered_end_time=local_time(entry.offered_end_time),
        offer_expires_at=expires,
        offer_expired=expires is not None and expires <= datetime.now(UTC),
    )
