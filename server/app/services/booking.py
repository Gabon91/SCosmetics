from datetime import UTC
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.beautician import Beautician
from app.models.treatment import Treatment
from app.schemas.appointment import AppointmentCreate
from app.services.availability import AvailabilityService
from app.services.booking_lock import BookingLockManager


class SlotUnavailableError(Exception):
    pass


class BookingService:
    def __init__(
        self,
        session: Session,
        lock_manager: BookingLockManager,
    ) -> None:
        self.session = session
        self.lock_manager = lock_manager
        self.business_timezone = ZoneInfo(settings.business_timezone)

    def create_appointment(
        self,
        customer_id: int,
        data: AppointmentCreate,
    ) -> Appointment:
        start_utc = data.start_time.astimezone(UTC)
        appointment_date = start_utc.astimezone(
            self.business_timezone
        ).date()

        with self.lock_manager.hold(
            data.treatment_id,
            data.beautician_id,
            appointment_date,
        ):
            try:
                # Existing rows serialize writes even if a Redis TTL expires.
                self.session.scalar(
                    select(Treatment.id)
                    .where(Treatment.id == data.treatment_id)
                    .with_for_update()
                )
                self.session.scalar(
                    select(Beautician.id)
                    .where(Beautician.id == data.beautician_id)
                    .with_for_update()
                )

                availability = AvailabilityService(
                    self.session
                ).list_available_slots(
                    data.treatment_id,
                    appointment_date,
                    data.beautician_id,
                )
                slot = next(
                    (
                        candidate
                        for candidate in availability.slots
                        if candidate.start_time.astimezone(UTC) == start_utc
                    ),
                    None,
                )
                if slot is None:
                    raise SlotUnavailableError

                appointment = Appointment(
                    customer_id=customer_id,
                    beautician_id=data.beautician_id,
                    treatment_id=data.treatment_id,
                    start_time=start_utc,
                    end_time=slot.end_time.astimezone(UTC),
                )
                self.session.add(appointment)
                self.session.commit()
                return appointment
            except Exception:
                self.session.rollback()
                raise
