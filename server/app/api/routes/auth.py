from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.core.tokens import IssuedTokenPair
from app.db.session import get_db
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenPairResponse,
    UserLoginRequest,
    UserRead,
    UserRegistrationRequest,
)
from app.services.auth import (
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.services.users import EmailAlreadyRegisteredError, UserService

router = APIRouter()


def token_response(token_pair: IssuedTokenPair) -> TokenPairResponse:
    return TokenPairResponse.model_validate(token_pair)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


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


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Log in with email and password",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid email or password",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User account is inactive",
        },
    },
)
def login(
    data: UserLoginRequest,
    session: Session = Depends(get_db),
) -> TokenPairResponse:
    try:
        return token_response(AuthService(session).login(data))
    except InvalidCredentialsError:
        raise unauthorized("Invalid email or password") from None
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        ) from None


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Refresh an access token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid or expired refresh token",
        }
    },
)
def refresh_tokens(
    data: RefreshTokenRequest,
    session: Session = Depends(get_db),
) -> TokenPairResponse:
    try:
        return token_response(AuthService(session).refresh(data.refresh_token))
    except InvalidRefreshTokenError:
        raise unauthorized("Invalid or expired refresh token") from None


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the authenticated user",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing or invalid access token",
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User account is inactive",
        },
    },
)
def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
