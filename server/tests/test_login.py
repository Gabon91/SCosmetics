from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.tokens import TokenType, decode_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User

PASSWORD = "StrongPassword123!"


def register_customer(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "לקוחה",
            "last_name": "בדיקה",
            "email": email,
            "phone": "050-7654321",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def test_login_returns_access_and_refresh_tokens() -> None:
    with TestClient(app) as client:
        registered_user = register_customer(client, "login@example.com")
        response = login(client, "LOGIN@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token_expires_in"] == 15 * 60
    assert body["refresh_token_expires_in"] == 7 * 24 * 60 * 60

    access_claims = decode_token(body["access_token"], TokenType.ACCESS)
    refresh_claims = decode_token(body["refresh_token"], TokenType.REFRESH)
    assert access_claims.user_id == registered_user["id"]
    assert refresh_claims.user_id == registered_user["id"]


def test_login_rejects_a_wrong_password() -> None:
    with TestClient(app) as client:
        register_customer(client, "wrong-password@example.com")
        response = login(
            client,
            "wrong-password@example.com",
            "WrongPassword123!",
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_does_not_reveal_an_unknown_email() -> None:
    with TestClient(app) as client:
        response = login(client, "unknown@example.com")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_inactive_user_cannot_log_in() -> None:
    email = "inactive@example.com"
    with TestClient(app) as client:
        register_customer(client, email)

        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.email == email))
            assert user is not None
            user.active = False
            session.commit()

        response = login(client, email)

    assert response.status_code == 403
    assert response.json() == {"detail": "User account is inactive"}


def test_refresh_issues_a_new_token_pair() -> None:
    with TestClient(app) as client:
        registered_user = register_customer(client, "refresh@example.com")
        login_response = login(client, "refresh@example.com")
        original_tokens = login_response.json()

        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_tokens["refresh_token"]},
        )

    assert refresh_response.status_code == 200
    refreshed_tokens = refresh_response.json()
    assert refreshed_tokens["access_token"] != original_tokens["access_token"]
    assert refreshed_tokens["refresh_token"] != original_tokens["refresh_token"]

    claims = decode_token(refreshed_tokens["access_token"], TokenType.ACCESS)
    assert claims.user_id == registered_user["id"]


def test_access_token_cannot_be_used_as_a_refresh_token() -> None:
    with TestClient(app) as client:
        register_customer(client, "wrong-token-type@example.com")
        login_response = login(client, "wrong-token-type@example.com")

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login_response.json()["access_token"]},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired refresh token"}
