from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, or_

from app.core.tokens import issue_token_pair
from app.db.session import SessionLocal
from app.main import app
from app.models.appointment import Appointment
from app.models.beautician import (
    Beautician,
    BeauticianWorkingHours,
    beautician_treatments,
)
from app.models.treatment import Treatment
from app.models.user import User, UserRole

BUSINESS_TIMEZONE = ZoneInfo("Asia/Jerusalem")


@dataclass(frozen=True)
class AvailabilityTestData:
    appointment_date: date
    access_token: str
    customer_id: int
    treatment_id: int
    other_treatment_id: int
    beautician_ids: tuple[int, int]
    user_ids: tuple[int, int, int]


def next_monday() -> date:
    today = datetime.now(BUSINESS_TIMEZONE).date()
    days_until_monday = (7 - today.weekday()) % 7
    return today + timedelta(days=days_until_monday or 7)


def user(email: str, role: UserRole) -> User:
    return User(
        first_name="Test",
        last_name="User",
        email=email,
        phone="050-0000000",
        password_hash="unused-in-availability-tests",
        role=role,
    )


def treatment(name: str, duration_minutes: int) -> Treatment:
    return Treatment(
        name=name,
        category="בדיקות זמינות",
        description="טיפול לבדיקת חישוב זמינות.",
        duration_minutes=duration_minutes,
        price=Decimal("100.00"),
        accent="rose",
    )


@pytest.fixture
def availability_data() -> AvailabilityTestData:
    suffix = uuid4().hex
    appointment_date = next_monday()

    with SessionLocal() as session:
        customer = user(f"customer-{suffix}@example.com", UserRole.CUSTOMER)
        first_user = user(
            f"beautician-1-{suffix}@example.com",
            UserRole.BEAUTICIAN,
        )
        second_user = user(
            f"beautician-2-{suffix}@example.com",
            UserRole.BEAUTICIAN,
        )
        target_treatment = treatment(f"Target {suffix}", 45)
        other_treatment = treatment(f"Other {suffix}", 30)
        session.add_all(
            [
                customer,
                first_user,
                second_user,
                target_treatment,
                other_treatment,
            ]
        )
        session.flush()

        first_beautician = Beautician(
            user=first_user,
            treatments=[target_treatment, other_treatment],
            working_hours=[
                BeauticianWorkingHours(
                    weekday=appointment_date.weekday(),
                    start_time=time(9, 0),
                    end_time=time(12, 0),
                )
            ],
        )
        second_beautician = Beautician(
            user=second_user,
            treatments=[target_treatment],
            working_hours=[
                BeauticianWorkingHours(
                    weekday=appointment_date.weekday(),
                    start_time=time(9, 0),
                    end_time=time(12, 0),
                )
            ],
        )
        session.add_all([first_beautician, second_beautician])
        session.commit()

        data = AvailabilityTestData(
            appointment_date=appointment_date,
            access_token=issue_token_pair(customer.id, customer.role).access_token,
            customer_id=customer.id,
            treatment_id=target_treatment.id,
            other_treatment_id=other_treatment.id,
            beautician_ids=(first_beautician.id, second_beautician.id),
            user_ids=(customer.id, first_user.id, second_user.id),
        )

    try:
        yield data
    finally:
        with SessionLocal() as session:
            session.execute(
                delete(Appointment).where(
                    or_(
                        Appointment.customer_id == data.customer_id,
                        Appointment.beautician_id.in_(data.beautician_ids),
                        Appointment.treatment_id.in_(
                            [data.treatment_id, data.other_treatment_id]
                        ),
                    )
                )
            )
            session.execute(
                beautician_treatments.delete().where(
                    beautician_treatments.c.beautician_id.in_(
                        data.beautician_ids
                    )
                )
            )
            session.execute(
                delete(BeauticianWorkingHours).where(
                    BeauticianWorkingHours.beautician_id.in_(
                        data.beautician_ids
                    )
                )
            )
            session.execute(
                delete(Beautician).where(
                    Beautician.id.in_(data.beautician_ids)
                )
            )
            session.execute(
                delete(Treatment).where(
                    Treatment.id.in_(
                        [data.treatment_id, data.other_treatment_id]
                    )
                )
            )
            session.execute(delete(User).where(User.id.in_(data.user_ids)))
            session.commit()


def authorization_header(data: AvailabilityTestData) -> dict[str, str]:
    return {"Authorization": f"Bearer {data.access_token}"}


def availability_url(data: AvailabilityTestData) -> str:
    return (
        "/api/v1/appointments/availability"
        f"?treatment_id={data.treatment_id}"
        f"&date={data.appointment_date.isoformat()}"
    )


def local_datetime(data: AvailabilityTestData, hour: int, minute: int) -> datetime:
    return datetime.combine(
        data.appointment_date,
        time(hour, minute),
        tzinfo=BUSINESS_TIMEZONE,
    )


def add_appointment(
    data: AvailabilityTestData,
    beautician_id: int,
    treatment_id: int,
    start_time: datetime,
    duration_minutes: int,
) -> None:
    with SessionLocal() as session:
        session.add(
            Appointment(
                customer_id=data.customer_id,
                beautician_id=beautician_id,
                treatment_id=treatment_id,
                start_time=start_time.astimezone(UTC),
                end_time=(
                    start_time + timedelta(minutes=duration_minutes)
                ).astimezone(UTC),
            )
        )
        session.commit()


def slot_starts(response_body: dict, beautician_id: int) -> set[str]:
    return {
        datetime.fromisoformat(slot["start_time"]).strftime("%H:%M")
        for slot in response_body["slots"]
        if slot["beautician_id"] == beautician_id
    }


def test_availability_returns_15_minute_slots_with_treatment_duration(
    availability_data: AvailabilityTestData,
) -> None:
    with TestClient(app) as client:
        response = client.get(
            availability_url(availability_data),
            headers=authorization_header(availability_data),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["duration_minutes"] == 45
    assert len(body["slots"]) == 20
    assert all(
        datetime.fromisoformat(slot["end_time"])
        - datetime.fromisoformat(slot["start_time"])
        == timedelta(minutes=45)
        for slot in body["slots"]
    )
    assert slot_starts(body, availability_data.beautician_ids[0]) == {
        "09:00",
        "09:15",
        "09:30",
        "09:45",
        "10:00",
        "10:15",
        "10:30",
        "10:45",
        "11:00",
        "11:15",
    }


def test_availability_can_filter_by_beautician(
    availability_data: AvailabilityTestData,
) -> None:
    selected_beautician_id = availability_data.beautician_ids[1]
    url = availability_url(availability_data) + (
        f"&beautician_id={selected_beautician_id}"
    )

    with TestClient(app) as client:
        response = client.get(
            url,
            headers=authorization_header(availability_data),
        )

    assert response.status_code == 200
    assert {
        slot["beautician_id"] for slot in response.json()["slots"]
    } == {selected_beautician_id}


def test_busy_beautician_is_blocked_even_for_another_treatment(
    availability_data: AvailabilityTestData,
) -> None:
    first_beautician_id, second_beautician_id = (
        availability_data.beautician_ids
    )
    add_appointment(
        availability_data,
        first_beautician_id,
        availability_data.other_treatment_id,
        local_datetime(availability_data, 9, 30),
        60,
    )

    with TestClient(app) as client:
        response = client.get(
            availability_url(availability_data),
            headers=authorization_header(availability_data),
        )

    body = response.json()
    assert "09:00" not in slot_starts(body, first_beautician_id)
    assert "10:15" not in slot_starts(body, first_beautician_id)
    assert "10:30" in slot_starts(body, first_beautician_id)
    assert "09:00" in slot_starts(body, second_beautician_id)


def test_same_treatment_blocks_every_beautician(
    availability_data: AvailabilityTestData,
) -> None:
    first_beautician_id, second_beautician_id = (
        availability_data.beautician_ids
    )
    add_appointment(
        availability_data,
        first_beautician_id,
        availability_data.treatment_id,
        local_datetime(availability_data, 9, 30),
        45,
    )

    with TestClient(app) as client:
        response = client.get(
            availability_url(availability_data),
            headers=authorization_header(availability_data),
        )

    body = response.json()
    for beautician_id in (first_beautician_id, second_beautician_id):
        assert "09:00" not in slot_starts(body, beautician_id)
        assert "10:00" not in slot_starts(body, beautician_id)
        assert "10:15" in slot_starts(body, beautician_id)


def test_availability_requires_authentication(
    availability_data: AvailabilityTestData,
) -> None:
    with TestClient(app) as client:
        response = client.get(availability_url(availability_data))

    assert response.status_code == 401
