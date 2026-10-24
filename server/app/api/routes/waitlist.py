from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import DatabaseSession, require_roles
from app.models.user import User, UserRole
from app.schemas.waitlist import WaitlistCreate, WaitlistRead, waitlist_read
from app.services.waitlist import (
    WaitlistConflictError,
    WaitlistNotFoundError,
    WaitlistTargetError,
    cancel_waitlist_entry,
    join_waitlist,
)

router = APIRouter()
Customer = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]


@router.post("", response_model=WaitlistRead, status_code=status.HTTP_201_CREATED)
def join(data: WaitlistCreate, customer: Customer, session: DatabaseSession) -> WaitlistRead:
    try:
        entry = join_waitlist(session, customer.id, data)
    except WaitlistTargetError:
        raise HTTPException(404, "Treatment or qualified beautician not found") from None
    except WaitlistConflictError as error:
        raise HTTPException(409, str(error)) from None
    return waitlist_read(entry)


@router.delete("/{entry_id}", response_model=WaitlistRead)
def leave(entry_id: int, customer: Customer, session: DatabaseSession) -> WaitlistRead:
    try:
        entry = cancel_waitlist_entry(session, customer.id, entry_id)
    except WaitlistNotFoundError:
        raise HTTPException(404, "Waitlist entry not found") from None
    except WaitlistConflictError as error:
        raise HTTPException(409, str(error)) from None
    return waitlist_read(entry)
