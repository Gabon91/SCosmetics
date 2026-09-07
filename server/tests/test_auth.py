from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import verify_password
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


def registration_data(email: str = "sigal@example.com") -> dict[str, str]:
    return {
        "first_name": "סיגל",
        "last_name": "לוי",
        "email": email,
        "phone": "050-1234567",
        "password": "StrongPassword123!",
        "password_confirmation": "StrongPassword123!",
    }


def test_customer_registration_hashes_the_password() -> None:
    data = registration_data()

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=data)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "sigal@example.com"
    assert body["role"] == "customer"
    assert "password" not in body
    assert "password_hash" not in body

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == data["email"]))

    assert user is not None
    assert user.password_hash != data["password"]
    assert verify_password(data["password"], user.password_hash)


def test_registration_rejects_a_duplicate_email() -> None:
    first_registration = registration_data("duplicate@example.com")
    second_registration = registration_data("DUPLICATE@example.com")

    with TestClient(app) as client:
        first_response = client.post(
            "/api/v1/auth/register",
            json=first_registration,
        )
        second_response = client.post(
            "/api/v1/auth/register",
            json=second_registration,
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "Email is already registered"}


def test_registration_rejects_passwords_that_do_not_match() -> None:
    data = registration_data("mismatch@example.com")
    data["password_confirmation"] = "DifferentPassword123!"

    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json=data)

    assert response.status_code == 422
