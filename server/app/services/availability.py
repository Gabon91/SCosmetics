from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import (
    Beautician,
    BeauticianWorkingHours,
    beautician_treatments,
)
from app.models.treatment import Treatment
from app.models.user import User, UserRole

SLOT_INTERVAL_MINUTES = 15


class TreatmentNotFoundError(Exception):
    pass


class BeauticianNotQualifiedError(Exception):
    pass


@dataclass(frozen=True)
class AvailableSlot:
    beautician_id: int
    beautician_name: str
    start_time: datetime
    end_time: datetime


@dataclass(frozen=True)
class AvailabilityResult:
    appointment_date: date
    treatment: Treatment
    slots: list[AvailableSlot]


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ranges_overlap(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    return first_start < second_end and first_end > second_start


def ceil_to_slot_interval(value: datetime) -> datetime:
    remainder = value.minute % SLOT_INTERVAL_MINUTES
    minutes_to_add = (SLOT_INTERVAL_MINUTES - remainder) % SLOT_INTERVAL_MINUTES
    if value.second or value.microsecond:
        minutes_to_add = (
            minutes_to_add
            if minutes_to_add
            else SLOT_INTERVAL_MINUTES
        )
    return (value + timedelta(minutes=minutes_to_add)).replace(
        second=0,
        microsecond=0,
    )


class AvailabilityService:
    def __init__(self, session: Session):
        self.session = session
        self.business_timezone = ZoneInfo(settings.business_timezone)

    def list_available_slots(
        self,
        treatment_id: int,
        appointment_date: date,
        beautician_id: int | None = None,
    ) -> AvailabilityResult:
        treatment = self.session.scalar(
            select(Treatment).where(
                Treatment.id == treatment_id,
                Treatment.active.is_(True),
            )
        )
        if treatment is None:
            raise TreatmentNotFoundError

        beauticians = self._qualified_beauticians(
            treatment_id,
            beautician_id,
        )
        if beautician_id is not None and not beauticians:
            raise BeauticianNotQualifiedError

        appointments = self._blocking_appointments(
            treatment_id,
            [beautician.id for beautician in beauticians],
            appointment_date,
        )
        now = datetime.now(self.business_timezone)
        slots: list[AvailableSlot] = []
        seen_slots: set[tuple[int, datetime]] = set()

        for beautician in beauticians:
            for working_hours in beautician.working_hours:
                if (
                    not working_hours.active
                    or working_hours.weekday != appointment_date.weekday()
                ):
                    continue

                for slot in self._slots_for_shift(
                    beautician,
                    working_hours,
                    treatment,
                    appointment_date,
                    appointments,
                    now,
                ):
                    slot_key = (slot.beautician_id, slot.start_time)
                    if slot_key not in seen_slots:
                        seen_slots.add(slot_key)
                        slots.append(slot)

        slots.sort(key=lambda slot: (slot.start_time, slot.beautician_id))
        return AvailabilityResult(
            appointment_date=appointment_date,
            treatment=treatment,
            slots=slots,
        )

    def _qualified_beauticians(
        self,
        treatment_id: int,
        beautician_id: int | None,
    ) -> list[Beautician]:
        statement = (
            select(Beautician)
            .join(
                beautician_treatments,
                Beautician.id == beautician_treatments.c.beautician_id,
            )
            .join(User, User.id == Beautician.user_id)
            .where(
                beautician_treatments.c.treatment_id == treatment_id,
                Beautician.active.is_(True),
                User.active.is_(True),
                User.role == UserRole.BEAUTICIAN,
            )
            .options(
                selectinload(Beautician.user),
                selectinload(Beautician.working_hours),
            )
            .order_by(Beautician.id)
        )
        if beautician_id is not None:
            statement = statement.where(Beautician.id == beautician_id)
        return list(self.session.scalars(statement).unique().all())

    def _blocking_appointments(
        self,
        treatment_id: int,
        beautician_ids: list[int],
        appointment_date: date,
    ) -> list[Appointment]:
        if not beautician_ids:
            return []

        day_start_local = datetime.combine(
            appointment_date,
            time.min,
            tzinfo=self.business_timezone,
        )
        day_end_local = datetime.combine(
            appointment_date + timedelta(days=1),
            time.min,
            tzinfo=self.business_timezone,
        )
        day_start = day_start_local.astimezone(UTC)
        day_end = day_end_local.astimezone(UTC)

        statement = select(Appointment).where(
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.start_time < day_end,
            Appointment.end_time > day_start,
            or_(
                Appointment.beautician_id.in_(beautician_ids),
                Appointment.treatment_id == treatment_id,
            ),
        )
        return list(self.session.scalars(statement).all())

    def _slots_for_shift(
        self,
        beautician: Beautician,
        working_hours: BeauticianWorkingHours,
        treatment: Treatment,
        appointment_date: date,
        appointments: list[Appointment],
        now: datetime,
    ) -> list[AvailableSlot]:
        shift_start = datetime.combine(
            appointment_date,
            working_hours.start_time,
            tzinfo=self.business_timezone,
        )
        shift_end = datetime.combine(
            appointment_date,
            working_hours.end_time,
            tzinfo=self.business_timezone,
        )
        slot_start = ceil_to_slot_interval(shift_start)
        duration = timedelta(minutes=treatment.duration_minutes)
        slots: list[AvailableSlot] = []

        while slot_start + duration <= shift_end:
            slot_end = slot_start + duration
            if slot_start > now and not self._has_conflict(
                beautician.id,
                treatment.id,
                slot_start,
                slot_end,
                appointments,
            ):
                slots.append(
                    AvailableSlot(
                        beautician_id=beautician.id,
                        beautician_name=(
                            f"{beautician.user.first_name} "
                            f"{beautician.user.last_name}"
                        ),
                        start_time=slot_start,
                        end_time=slot_end,
                    )
                )
            slot_start += timedelta(minutes=SLOT_INTERVAL_MINUTES)

        return slots

    @staticmethod
    def _has_conflict(
        beautician_id: int,
        treatment_id: int,
        slot_start: datetime,
        slot_end: datetime,
        appointments: list[Appointment],
    ) -> bool:
        slot_start_utc = slot_start.astimezone(UTC)
        slot_end_utc = slot_end.astimezone(UTC)

        return any(
            (
                appointment.beautician_id == beautician_id
                or appointment.treatment_id == treatment_id
            )
            and ranges_overlap(
                slot_start_utc,
                slot_end_utc,
                as_utc(appointment.start_time),
                as_utc(appointment.end_time),
            )
            for appointment in appointments
        )
