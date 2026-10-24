from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician
from app.models.package import UserPackage, UserPackageStatus, package_treatments
from app.models.treatment import Treatment
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.appointment import AppointmentCreate, AppointmentReschedule
from app.services.availability import AvailabilityService, as_utc
from app.services.booking_lock import BookingLockManager


class SlotUnavailableError(Exception):
    pass


class PackageNotUsableError(Exception):
    pass


class BookingNotFoundError(Exception):
    pass


class RescheduleNotAllowedError(Exception):
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

    def reschedule_appointment(self, appointment_id: int, data: AppointmentReschedule) -> Appointment:
        """Move a future booking atomically; keep its ID, treatment and package."""
        current = self.session.get(Appointment, appointment_id)
        if current is None:
            raise BookingNotFoundError
        original_start = as_utc(current.start_time)
        original_end = as_utc(current.end_time)
        original_staff = current.beautician_id
        treatment_id = current.treatment_id
        old_date = original_start.astimezone(self.business_timezone).date()
        target_start = data.start_time.astimezone(UTC)
        target_date = target_start.astimezone(self.business_timezone).date()
        resources = [
            (treatment_id, original_staff, old_date),
            (treatment_id, data.beautician_id, target_date),
        ]
        with self.lock_manager.hold_many(resources):
            try:
                # The treatment row serializes writes even if a Redis lock expires.
                self.session.scalar(select(Treatment.id).where(Treatment.id == treatment_id).with_for_update())
                appointment = self.session.scalar(
                    select(Appointment).where(Appointment.id == appointment_id)
                    .with_for_update().execution_options(populate_existing=True)
                )
                if appointment is None:
                    raise BookingNotFoundError
                if (
                    appointment.status != AppointmentStatus.BOOKED
                    or as_utc(appointment.start_time) <= datetime.now(UTC)
                    or as_utc(appointment.start_time) != original_start
                    or appointment.beautician_id != original_staff
                    or (target_start == original_start and data.beautician_id == original_staff)
                ):
                    raise RescheduleNotAllowedError

                if appointment.user_package_id is not None:
                    owned = self.session.scalar(
                        select(UserPackage).where(UserPackage.id == appointment.user_package_id).with_for_update()
                    )
                    if (
                        owned is None or owned.status != UserPackageStatus.ACTIVE
                        or owned.expiration_date < target_date
                    ):
                        raise PackageNotUsableError

                available = AvailabilityService(self.session).list_available_slots(
                    treatment_id, target_date, data.beautician_id,
                    appointment.customer_id, exclude_appointment_id=appointment.id,
                )
                slot = next((candidate for candidate in available.slots
                             if candidate.start_time.astimezone(UTC) == target_start), None)
                if slot is None:
                    raise SlotUnavailableError

                appointment.beautician_id = data.beautician_id
                appointment.start_time = target_start
                appointment.end_time = slot.end_time.astimezone(UTC)
                self.session.flush()

                # A reservation offered to this customer becomes fulfilled on use.
                for offer in self.session.scalars(
                    select(WaitlistEntry).where(
                        WaitlistEntry.user_id == appointment.customer_id,
                        WaitlistEntry.treatment_id == treatment_id,
                        WaitlistEntry.beautician_id == data.beautician_id,
                        WaitlistEntry.status == WaitlistStatus.OFFERED,
                    ).with_for_update()
                ):
                    if (
                        offer.offered_start_time is not None
                        and offer.offer_expires_at is not None
                        and as_utc(offer.offered_start_time) == target_start
                        and as_utc(offer.offer_expires_at) > datetime.now(UTC)
                    ):
                        offer.status = WaitlistStatus.FULFILLED
                self.session.flush()

                # Offer the former slot only if it is now fully free.
                old_slots = AvailabilityService(self.session).list_available_slots(
                    treatment_id, old_date, original_staff,
                ).slots
                if any(candidate.start_time.astimezone(UTC) == original_start
                       and candidate.end_time.astimezone(UTC) == original_end
                       for candidate in old_slots):
                    waiting = self.session.scalar(
                        select(WaitlistEntry).where(
                            WaitlistEntry.status == WaitlistStatus.WAITING,
                            WaitlistEntry.treatment_id == treatment_id,
                            WaitlistEntry.preferred_date == old_date,
                            WaitlistEntry.user_id != appointment.customer_id,
                            or_(WaitlistEntry.beautician_id.is_(None),
                                WaitlistEntry.beautician_id == original_staff),
                        ).order_by(WaitlistEntry.created_at, WaitlistEntry.id).with_for_update()
                    )
                    if waiting is not None:
                        waiting.status = WaitlistStatus.OFFERED
                        waiting.beautician_id = original_staff
                        waiting.offered_start_time = original_start
                        waiting.offered_end_time = original_end
                        waiting.offer_expires_at = min(
                            datetime.now(UTC) + timedelta(minutes=15), original_start,
                        )
                self.session.commit()
                return appointment
            except Exception:
                self.session.rollback()
                raise
