from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician
from app.models.package import UserPackage, UserPackageStatus, package_treatments
from app.models.treatment import Treatment
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.appointment import AppointmentCreate
from app.services.availability import AvailabilityService, as_utc
from app.services.booking_lock import BookingLockManager


class SlotUnavailableError(Exception):
    pass


class PackageNotUsableError(Exception):
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

                if data.user_package_id is not None:
                    user_package = self.session.scalar(
                        select(UserPackage)
                        .where(
                            UserPackage.id == data.user_package_id,
                            UserPackage.user_id == customer_id,
                        )
                        .with_for_update()
                    )
                    eligible_treatment = self.session.scalar(
                        select(package_treatments.c.treatment_id).where(
                            package_treatments.c.package_id == (
                                user_package.package_id if user_package else -1
                            ),
                            package_treatments.c.treatment_id == data.treatment_id,
                        )
                    )
                    reserved = self.session.scalar(
                        select(func.count(Appointment.id)).where(
                            Appointment.user_package_id == data.user_package_id,
                            Appointment.status == AppointmentStatus.BOOKED,
                        )
                    ) or 0
                    if (
                        user_package is None
                        or user_package.status != UserPackageStatus.ACTIVE
                        or user_package.expiration_date < appointment_date
                        or eligible_treatment is None
                        or user_package.remaining_sessions <= reserved
                    ):
                        raise PackageNotUsableError

                availability = AvailabilityService(
                    self.session
                ).list_available_slots(
                    data.treatment_id,
                    appointment_date,
                    data.beautician_id,
                    customer_id,
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
                    user_package_id=data.user_package_id,
                    start_time=start_utc,
                    end_time=slot.end_time.astimezone(UTC),
                )
                self.session.add(appointment)
                offers = self.session.scalars(
                    select(WaitlistEntry)
                    .where(
                        WaitlistEntry.user_id == customer_id,
                        WaitlistEntry.treatment_id == data.treatment_id,
                        WaitlistEntry.beautician_id == data.beautician_id,
                        WaitlistEntry.status == WaitlistStatus.OFFERED,
                    )
                    .with_for_update()
                ).all()
                for offer in offers:
                    if (
                        offer.offered_start_time is not None
                        and offer.offer_expires_at is not None
                        and as_utc(offer.offered_start_time) == start_utc
                        and as_utc(offer.offer_expires_at) > datetime.now(UTC)
                    ):
                        offer.status = WaitlistStatus.FULFILLED
                self.session.commit()
                return appointment
            except Exception:
                self.session.rollback()
                raise
