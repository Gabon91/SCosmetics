from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician, beautician_treatments
from app.models.treatment import Treatment
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.waitlist import WaitlistCreate
from app.services.availability import as_utc

OFFER_MINUTES = 15


class WaitlistConflictError(Exception):
    pass


class WaitlistTargetError(Exception):
    pass


class WaitlistNotFoundError(Exception):
    pass


def join_waitlist(session: Session, user_id: int, data: WaitlistCreate) -> WaitlistEntry:
    today = datetime.now(ZoneInfo(settings.business_timezone)).date()
    if data.preferred_date < today:
        raise WaitlistConflictError("Choose today or a future date")
    treatment = session.scalar(
        select(Treatment).where(Treatment.id == data.treatment_id, Treatment.active.is_(True))
    )
    if treatment is None:
        raise WaitlistTargetError
    if data.beautician_id is not None:
        qualified = session.scalar(
            select(Beautician.id)
            .join(beautician_treatments)
            .where(
                Beautician.id == data.beautician_id,
                Beautician.active.is_(True),
                beautician_treatments.c.treatment_id == data.treatment_id,
            )
        )
        if qualified is None:
            raise WaitlistTargetError

    existing = session.scalar(
        select(WaitlistEntry).where(
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.treatment_id == data.treatment_id,
            WaitlistEntry.preferred_date == data.preferred_date,
            WaitlistEntry.beautician_id == data.beautician_id,
            WaitlistEntry.status.in_([WaitlistStatus.WAITING, WaitlistStatus.OFFERED]),
        )
    )
    if existing is not None and (
        existing.status == WaitlistStatus.WAITING
        or existing.offer_expires_at is not None
        and as_utc(existing.offer_expires_at) > datetime.now(UTC)
    ):
        raise WaitlistConflictError("Already on the waitlist for this date")

    entry = WaitlistEntry(
        user_id=user_id,
        treatment_id=data.treatment_id,
        preferred_date=data.preferred_date,
        beautician_id=data.beautician_id,
    )
    session.add(entry)
    session.commit()
    return entry


def cancel_waitlist_entry(session: Session, user_id: int, entry_id: int) -> WaitlistEntry:
    entry = session.scalar(
        select(WaitlistEntry)
        .where(WaitlistEntry.id == entry_id, WaitlistEntry.user_id == user_id)
        .with_for_update()
    )
    if entry is None:
        raise WaitlistNotFoundError
    if entry.status not in (WaitlistStatus.WAITING, WaitlistStatus.OFFERED):
        raise WaitlistConflictError("Waitlist entry cannot be cancelled")
    entry.status = WaitlistStatus.CANCELLED
    session.commit()
    return entry


def cancel_customer_appointment(
    session: Session, customer_id: int, appointment_id: int
) -> Appointment:
    """Cancel and offer the released slot to the oldest matching waitlist entry."""
    try:
        existing = session.get(Appointment, appointment_id)
        if existing is None or existing.customer_id != customer_id:
            raise WaitlistNotFoundError
        # Serialize cancellation with bookings that lock the treatment row.
        session.scalar(
            select(Treatment.id)
            .where(Treatment.id == existing.treatment_id)
            .with_for_update()
        )
        appointment = session.scalar(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        now = datetime.now(UTC)
        if (
            appointment is None
            or appointment.status != AppointmentStatus.BOOKED
            or as_utc(appointment.start_time) <= now
        ):
            raise WaitlistConflictError("Only future booked appointments can be cancelled")

        local_date = as_utc(appointment.start_time).astimezone(
            ZoneInfo(settings.business_timezone)
        ).date()
        waiting = session.scalar(
            select(WaitlistEntry)
            .where(
                WaitlistEntry.status == WaitlistStatus.WAITING,
                WaitlistEntry.treatment_id == appointment.treatment_id,
                WaitlistEntry.preferred_date == local_date,
                WaitlistEntry.user_id != customer_id,
                or_(
                    WaitlistEntry.beautician_id.is_(None),
                    WaitlistEntry.beautician_id == appointment.beautician_id,
                ),
            )
            .order_by(WaitlistEntry.created_at, WaitlistEntry.id)
            .with_for_update()
        )
        appointment.status = AppointmentStatus.CANCELLED
        if waiting is not None:
            waiting.status = WaitlistStatus.OFFERED
            waiting.beautician_id = appointment.beautician_id
            waiting.offered_start_time = appointment.start_time
            waiting.offered_end_time = appointment.end_time
            waiting.offer_expires_at = min(
                now + timedelta(minutes=OFFER_MINUTES),
                as_utc(appointment.start_time),
            )
        session.commit()
        return appointment
    except Exception:
        session.rollback()
        raise
