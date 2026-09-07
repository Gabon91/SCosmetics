from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.tokens import (
    IssuedTokenPair,
    TokenType,
    TokenValidationError,
    decode_token,
    issue_token_pair,
)
from app.models.user import User
from app.schemas.auth import UserLoginRequest

DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password")


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def login(self, data: UserLoginRequest) -> IssuedTokenPair:
        normalized_email = str(data.email).strip().lower()
        user = self.session.scalar(
            select(User).where(User.email == normalized_email)
        )

        if user is None:
            verify_password(data.password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError

        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError

        if not user.active:
            raise InactiveUserError

        return issue_token_pair(user.id, user.role)

    def refresh(self, refresh_token: str) -> IssuedTokenPair:
        try:
            claims = decode_token(refresh_token, TokenType.REFRESH)
        except TokenValidationError as error:
            raise InvalidRefreshTokenError from error

        user = self.session.get(User, claims.user_id)
        if user is None or not user.active:
            raise InvalidRefreshTokenError

        return issue_token_pair(user.id, user.role)
