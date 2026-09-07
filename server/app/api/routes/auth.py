from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import UserRead, UserRegistrationRequest
from app.services.users import EmailAlreadyRegisteredError, UserService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Email is already registered",
        }
    },
)
def register_customer(
    data: UserRegistrationRequest,
    session: Session = Depends(get_db),
) -> UserRead:
    try:
        return UserService(session).register_customer(data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None
