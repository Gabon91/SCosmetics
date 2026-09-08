from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError as PyJWTInvalidTokenError

from app.core.config import settings
from app.models.user import UserRole


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenValidationError(Exception):
    pass


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    role: UserRole
    token_type: TokenType
    token_id: str


@dataclass(frozen=True)
class IssuedTokenPair:
    access_token: str
    refresh_token: str
    access_token_expires_in: int
    refresh_token_expires_in: int


def create_token(
    user_id: int,
    role: UserRole,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    issued_at = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": token_type.value,
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": issued_at + expires_delta,
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def issue_token_pair(user_id: int, role: UserRole) -> IssuedTokenPair:
    access_lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_lifetime = timedelta(days=settings.refresh_token_expire_days)

    return IssuedTokenPair(
        access_token=create_token(
            user_id,
            role,
            TokenType.ACCESS,
            access_lifetime,
        ),
        refresh_token=create_token(
            user_id,
            role,
            TokenType.REFRESH,
            refresh_lifetime,
        ),
        access_token_expires_in=int(access_lifetime.total_seconds()),
        refresh_token_expires_in=int(refresh_lifetime.total_seconds()),
    )


def decode_token(token: str, expected_type: TokenType) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "role", "type", "jti", "iat", "exp", "iss"]
            },
        )
        token_type = TokenType(payload["type"])
        role = UserRole(payload["role"])
        user_id = int(payload["sub"])
        token_id = str(payload["jti"])
    except (PyJWTInvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise TokenValidationError from error

    if token_type is not expected_type or user_id < 1 or not token_id:
        raise TokenValidationError

    return TokenClaims(
        user_id=user_id,
        role=role,
        token_type=token_type,
        token_id=token_id,
    )
