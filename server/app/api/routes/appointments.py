from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import (
    CurrentUser,
    DatabaseSession,
    require_roles,
)
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AvailabilityResponse,
    AvailabilitySlotRead,
)
from app.services.availability import (
    AvailabilityService,
    BeauticianNotQualifiedError,
    TreatmentNotFoundError,
)
from app.services.appointment_lifecycle import (
    AppointmentNotFoundError,
    AppointmentPermissionError,
    AppointmentStateError,
    complete_appointment as complete_booking,
)
from app.services.booking import (
    BookingService,
    PackageNotUsableError,
    SlotUnavailableError,
)
from app.services.booking_lock import (
    BookingLockBusyError,
    BookingLockManager,
    BookingLockUnavailableError,
)
from app.services.waitlist import (
    WaitlistConflictError,
    WaitlistNotFoundError,
    cancel_customer_appointment,
)

router = APIRouter()

BookingSession = Annotated[Session, Depends(get_db, use_cache=False)]
CurrentCustomer = Annotated[
    User,
    Depends(require_roles(UserRole.CUSTOMER)),
]


def get_booking_lock_manager() -> BookingLockManager:
    return BookingLockManager()


BookingLocks = Annotated[
    BookingLockManager,
    Depends(get_booking_lock_manager),
]
CurrentStaff = Annotated[
    User,
    Depends(require_roles(UserRole.BEAUTICIAN, UserRole.ADMIN)),
]


@router.get(
    "/availability",
    response_model=AvailabilityResponse,
    summary="List available appointment slots",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication is required",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Treatment or qualified beautician was not found",
        },
    },
)
def list_availability(
    treatment_id: Annotated[int, Query(gt=0)],
    appointment_date: Annotated[date, Query(alias="date")],
    session: DatabaseSession,
    current_user: CurrentUser,
    beautician_id: Annotated[int | None, Query(gt=0)] = None,
) -> AvailabilityResponse:
    try:
        result = AvailabilityService(session).list_available_slots(
            treatment_id,
            appointment_date,
            beautician_id,
            current_user.id,
        )
    except TreatmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found",
        ) from None
    except BeauticianNotQualifiedError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beautician not found or not qualified for treatment",
        ) from None

    return AvailabilityResponse(
        date=result.appointment_date,
        treatment_id=result.treatment.id,
        treatment_name=result.treatment.name,
        duration_minutes=result.treatment.duration_minutes,
        slots=[
            AvailabilitySlotRead.model_validate(slot) for slot in result.slots
        ],
    )


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication is required",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Only customers may book appointments",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Treatment or qualified beautician was not found",
        },
        status.HTTP_409_CONFLICT: {
            "description": "Slot is unavailable or booking is in progress",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Booking lock service is unavailable",
        },
    },
)
def create_appointment(
    data: AppointmentCreate,
    current_customer: CurrentCustomer,
    session: BookingSession,
    lock_manager: BookingLocks,
) -> AppointmentRead:
    try:
        appointment = BookingService(
            session,
            lock_manager,
        ).create_appointment(current_customer.id, data)
    except TreatmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found",
        ) from None
    except BeauticianNotQualifiedError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beautician not found or not qualified for treatment",
        ) from None
    except SlotUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment slot is not available",
        ) from None
    except PackageNotUsableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Package is not available for this booking",
        ) from None
    except BookingLockBusyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking is in progress; please try again",
        ) from None
    except BookingLockUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Booking is temporarily unavailable",
        ) from None

    return AppointmentRead.model_validate(appointment)


@router.delete("/{appointment_id}", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: int, customer: CurrentCustomer, session: BookingSession
) -> AppointmentRead:
    try:
        appointment = cancel_customer_appointment(session, customer.id, appointment_id)
    except WaitlistNotFoundError:
        raise HTTPException(404, "Appointment not found") from None
    except WaitlistConflictError as error:
        raise HTTPException(409, str(error)) from None
    return AppointmentRead.model_validate(appointment)


@router.patch("/{appointment_id}/complete", response_model=AppointmentRead)
def complete_appointment(
    appointment_id: int, staff: CurrentStaff, session: BookingSession
) -> AppointmentRead:
    try:
        appointment = complete_booking(session, appointment_id, staff)
    except AppointmentNotFoundError:
        raise HTTPException(404, "Appointment not found") from None
    except AppointmentPermissionError:
        raise HTTPException(403, "This appointment is not assigned to you") from None
    except AppointmentStateError:
        raise HTTPException(409, "Appointment cannot be completed") from None
    return AppointmentRead.model_validate(appointment)
