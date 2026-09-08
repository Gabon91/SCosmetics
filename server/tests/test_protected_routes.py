import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.dependencies.auth import require_roles
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User, UserRole

PASSWORD = "StrongPassword123!"


def register_and_login(client: TestClient, email: str) -> tuple[dict, dict]:
    registration_response = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "לקוחה",
            "last_name": "בדיקה",
            "email": email,
            "phone": "050-1112233",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
    )
    assert registration_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login_response.status_code == 200
    return registration_response.json(), login_response.json()


def bearer_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_me_returns_the_authenticated_user() -> None:
    with TestClient(app) as client:
        registered_user, tokens = register_and_login(client, "me@example.com")
        response = client.get(
            "/api/v1/auth/me",
            headers=bearer_header(tokens["access_token"]),
        )

    assert response.status_code == 200
    assert response.json() == registered_user


def test_me_rejects_a_missing_access_token() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_an_invalid_access_token() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers=bearer_header("not-a-valid-jwt"),
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_me_rejects_a_refresh_token() -> None:
    with TestClient(app) as client:
        _, tokens = register_and_login(client, "refresh-at-me@example.com")
        response = client.get(
            "/api/v1/auth/me",
            headers=bearer_header(tokens["refresh_token"]),
        )

    assert response.status_code == 401


def test_me_rejects_a_user_deactivated_after_login() -> None:
    email = "deactivated-after-login@example.com"
    with TestClient(app) as client:
        _, tokens = register_and_login(client, email)

        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.email == email))
            assert user is not None
            user.active = False
            session.commit()

        response = client.get(
            "/api/v1/auth/me",
            headers=bearer_header(tokens["access_token"]),
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "User account is inactive"}


@pytest.mark.parametrize(
    ("role", "is_allowed"),
    [
        (UserRole.CUSTOMER, False),
        (UserRole.BEAUTICIAN, True),
        (UserRole.ADMIN, True),
    ],
)
def test_staff_permission_checks_every_role(
    role: UserRole,
    is_allowed: bool,
) -> None:
    staff_only = require_roles(UserRole.BEAUTICIAN, UserRole.ADMIN)
    user = User(
        first_name="Test",
        last_name="User",
        email=f"{role.value}@example.com",
        phone="050-0000000",
        password_hash="unused-in-this-test",
        role=role,
    )

    if is_allowed:
        assert staff_only(user) is user
    else:
        with pytest.raises(HTTPException) as error:
            staff_only(user)
        assert error.value.status_code == 403
        assert error.value.detail == "Insufficient permissions"
