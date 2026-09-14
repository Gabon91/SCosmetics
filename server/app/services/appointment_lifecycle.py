from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician
from app.models.package import UserPackage, UserPackageStatus
from app.models.user import User, UserRole


class AppointmentNotFoundError(Exception):
    pass


class AppointmentPermissionError(Exception):
    pass


class AppointmentStateError(Exception):
    pass


def complete_appointment(
    session: Session, appointment_id: int, staff: User
) -> Appointment:
    """Complete once; package balance changes in the same transaction."""
    try:
        appointment = session.scalar(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .with_for_update()
        )
        if appointment is None:
            raise AppointmentNotFoundError
        if staff.role == UserRole.BEAUTICIAN:
            own_beautician_id = session.scalar(
                select(Beautician.id).where(Beautician.user_id == staff.id)
            )
            if own_beautician_id != appointment.beautician_id:
                raise AppointmentPermissionError
        elif staff.role != UserRole.ADMIN:
            raise AppointmentPermissionError

        if appointment.status == AppointmentStatus.COMPLETED:
            return appointment
        if appointment.status != AppointmentStatus.BOOKED:
            raise AppointmentStateError

        if appointment.user_package_id is not None:
            user_package = session.scalar(
                select(UserPackage)
                .where(UserPackage.id == appointment.user_package_id)
                .with_for_update()
            )
            if user_package is None or user_package.remaining_sessions < 1:
                raise AppointmentStateError
            user_package.used_sessions += 1
            user_package.remaining_sessions -= 1
            if user_package.remaining_sessions == 0:
                user_package.status = UserPackageStatus.EXHAUSTED

        appointment.status = AppointmentStatus.COMPLETED
        appointment.completed_at = datetime.now(UTC)
        session.commit()
        return appointment
    except Exception:
        session.rollback()
        raise
