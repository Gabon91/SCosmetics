from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies.auth import CurrentUser, DatabaseSession
from app.schemas.appointment import (
    AvailabilityResponse,
    AvailabilitySlotRead,
)
from app.services.availability import (
    AvailabilityService,
    BeauticianNotQualifiedError,
    TreatmentNotFoundError,
)

router = APIRouter()


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
    _current_user: CurrentUser,
    beautician_id: Annotated[int | None, Query(gt=0)] = None,
) -> AvailabilityResponse:
    try:
        result = AvailabilityService(session).list_available_slots(
            treatment_id,
            appointment_date,
            beautician_id,
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
