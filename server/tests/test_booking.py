from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from threading import Barrier, Lock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    LockNotOwnedError,
)
from sqlalchemy import delete, func, or_, select

from app.api.routes.appointments import get_booking_lock_manager
from app.core.tokens import issue_token_pair
from app.db.session import SessionLocal
from app.main import app
from app.models.appointment import Appointment, AppointmentStatus
from app.models.package import Package, UserPackage
from app.models.beautician import (
    Beautician,
    BeauticianWorkingHours,
    beautician_treatments,
)
from app.models.treatment import Treatment
from app.models.user import User, UserRole
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.services.booking_lock import BookingLockManager
from app.services.availability import as_utc

BUSINESS_TIMEZONE = ZoneInfo("Asia/Jerusalem")
BOOKING_URL = "/api/v1/appointments"


class FakeLock:
    def __init__(self, name: str, mutex: Lock, wait: float) -> None:
        self.name = name
        self.mutex = mutex
        self.wait = wait

    def acquire(self) -> bool:
        return self.mutex.acquire(timeout=self.wait)

    def release(self) -> None:
        self.mutex.release()


class FakeRedis:
    def __init__(self) -> None:
        self.guard = Lock()
        self.mutexes: dict[str, Lock] = {}

    def lock(self, name: str, *, timeout: int, blocking_timeout: int) -> FakeLock:
        with self.guard:
            mutex = self.mutexes.setdefault(name, Lock())
        return FakeLock(name, mutex, blocking_timeout)


class UnavailableRedis:
    def lock(self, name: str, *, timeout: int, blocking_timeout: int) -> FakeLock:
        raise RedisConnectionError("Redis is unavailable")


class BusyLock:
    def __init__(self, name: str) -> None:
        self.name = name

    def acquire(self) -> bool:
        return False


class BusyRedis:
    def lock(self, name: str, *, timeout: int, blocking_timeout: int) -> BusyLock:
        return BusyLock(name)


class ExpiredLock:
    def __init__(self, name: str) -> None:
        self.name = name

    def acquire(self) -> bool:
        return True

    def release(self) -> None:
        raise LockNotOwnedError("Lock already expired")


class ExpiredRedis:
    def lock(self, name: str, *, timeout: int, blocking_timeout: int) -> ExpiredLock:
        return ExpiredLock(name)


@dataclass(frozen=True)
class BookingTestData:
    appointment_date: date
    customer_id: int
    customer_token: str
    staff_token: str
    treatment_id: int
    other_treatment_id: int
    beautician_ids: tuple[int, int]
    user_ids: tuple[int, int, int]


def next_monday() -> date:
    today = datetime.now(BUSINESS_TIMEZONE).date()
    days_until_monday = (7 - today.weekday()) % 7
    return today + timedelta(days=days_until_monday or 7)


def make_user(email: str, role: UserRole) -> User:
    return User(
        first_name="Booking",
        last_name="Tester",
        email=email,
        phone="050-0000000",
        password_hash="unused-in-booking-tests",
        role=role,
    )


def make_treatment(name: str, minutes: int) -> Treatment:
    return Treatment(
        name=name,
        category="בדיקות תורים",
        description="טיפול לבדיקת יצירת תור.",
        duration_minutes=minutes,
        price=Decimal("100.00"),
        accent="rose",
    )


@pytest.fixture
def booking_data() -> BookingTestData:
    suffix = uuid4().hex
    appointment_date = next_monday()

    with SessionLocal() as session:
        customer = make_user(f"booking-{suffix}@example.com", UserRole.CUSTOMER)
        first_user = make_user(
            f"booking-staff-1-{suffix}@example.com", UserRole.BEAUTICIAN
        )
        second_user = make_user(
            f"booking-staff-2-{suffix}@example.com", UserRole.BEAUTICIAN
        )
        target = make_treatment(f"Target {suffix}", 45)
        other = make_treatment(f"Other {suffix}", 30)
        session.add_all([customer, first_user, second_user, target, other])
        session.flush()

        first_beautician = Beautician(
            user=first_user,
            treatments=[target, other],
            working_hours=[
                BeauticianWorkingHours(
                    weekday=appointment_date.weekday(),
                    start_time=time(9),
                    end_time=time(12),
                )
            ],
        )
        second_beautician = Beautician(
            user=second_user,
            treatments=[target],
            working_hours=[
                BeauticianWorkingHours(
                    weekday=appointment_date.weekday(),
                    start_time=time(9),
                    end_time=time(12),
                )
            ],
        )
        session.add_all([first_beautician, second_beautician])
        session.commit()

        data = BookingTestData(
            appointment_date=appointment_date,
            customer_id=customer.id,
            customer_token=issue_token_pair(
                customer.id, customer.role
            ).access_token,
            staff_token=issue_token_pair(
                first_user.id, first_user.role
            ).access_token,
            treatment_id=target.id,
            other_treatment_id=other.id,
            beautician_ids=(first_beautician.id, second_beautician.id),
            user_ids=(customer.id, first_user.id, second_user.id),
        )

    lock_manager = BookingLockManager(FakeRedis())
    app.dependency_overrides[get_booking_lock_manager] = lambda: lock_manager
    try:
        yield data
    finally:
        app.dependency_overrides.pop(get_booking_lock_manager, None)
        with SessionLocal() as session:
            session.execute(
                delete(Appointment).where(
                    or_(
                        Appointment.customer_id == data.customer_id,
                        Appointment.beautician_id.in_(data.beautician_ids),
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
                    Treatment.id.in_([data.treatment_id, data.other_treatment_id])
                )
            )
            session.execute(delete(User).where(User.id.in_(data.user_ids)))
            session.commit()


def headers(data: BookingTestData, *, staff: bool = False) -> dict[str, str]:
    token = data.staff_token if staff else data.customer_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(booking_data: BookingTestData):
    with SessionLocal() as session:
        admin = make_user(f"booking-admin-{uuid4().hex}@example.com", UserRole.ADMIN)
        session.add(admin)
        session.commit()
        admin_id = admin.id
        auth = {"Authorization": f"Bearer {issue_token_pair(admin.id, admin.role).access_token}"}
    try:
        yield auth
    finally:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id == admin_id))
            session.commit()


def test_admin_books_for_existing_customer_and_staff_cannot(booking_data: BookingTestData, admin_headers) -> None:
    path = "/api/v1/staff/appointments"
    request = {**payload(booking_data), "customer_id": booking_data.customer_id}
    with TestClient(app) as client:
        assert client.post(path, json=request).status_code == 401
        assert client.post(path, json=request, headers=headers(booking_data, staff=True)).status_code == 403
        assert client.post(path, json=request, headers=headers(booking_data)).status_code == 403
        assert client.post(path, json={**request, "customer_id": 99999999}, headers=admin_headers).status_code == 404
        created = client.post(path, json=request, headers=admin_headers)
        assert created.status_code == 201, created.text
        assert created.json()["customer_id"] == booking_data.customer_id
        collision = client.post(path, json={**request, "beautician_id": booking_data.beautician_ids[1]}, headers=admin_headers)
        assert collision.status_code == 409


def test_admin_reschedule_keeps_appointment_and_rechecks_availability(booking_data: BookingTestData, admin_headers) -> None:
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/staff/appointments",
            json={**payload(booking_data), "customer_id": booking_data.customer_id},
            headers=admin_headers,
        )
        assert first.status_code == 201, first.text
        booking_id = first.json()["id"]
        available = client.get("/api/v1/staff/booking-availability", params={
            "customer_id": booking_data.customer_id,
            "treatment_id": booking_data.treatment_id,
            "date": booking_data.appointment_date.isoformat(),
            "appointment_id": booking_id,
        }, headers=admin_headers)
        assert available.status_code == 200, available.text
        assert any(datetime.fromisoformat(slot["start_time"]).astimezone(BUSINESS_TIMEZONE).strftime("%H:%M") == "09:15"
                   for slot in available.json()["slots"])
        path = f"/api/v1/staff/appointments/{booking_id}/reschedule"
        assert client.patch(path, json={"beautician_id": booking_data.beautician_ids[1],
                                        "start_time": local_start(booking_data, 9, 15).isoformat()},
                            headers=headers(booking_data, staff=True)).status_code == 403
        changed = client.patch(path, json={"beautician_id": booking_data.beautician_ids[1],
                                           "start_time": local_start(booking_data, 9, 45).isoformat()},
                               headers=admin_headers)
        assert changed.status_code == 200, changed.text
        assert changed.json()["id"] == booking_id
        assert changed.json()["beautician_id"] == booking_data.beautician_ids[1]
        assert datetime.fromisoformat(changed.json()["start_time"]).astimezone(BUSINESS_TIMEZONE).strftime("%H:%M") == "09:45"
        assert client.patch(path, json={"beautician_id": booking_data.beautician_ids[1],
                                        "start_time": local_start(booking_data, 9, 45).isoformat()},
                            headers=admin_headers).status_code == 409
        assert client.patch(path, json={"beautician_id": booking_data.beautician_ids[0],
                                        "start_time": local_start(booking_data, 9, 10).isoformat()},
                            headers=admin_headers).status_code == 422
    with SessionLocal() as session:
        assert session.scalar(select(func.count(Appointment.id)).where(Appointment.customer_id == booking_data.customer_id)) == 1


def test_admin_reschedule_offers_freed_slot_to_waitlist(booking_data: BookingTestData, admin_headers) -> None:
    with SessionLocal() as session:
        waiting_customer = make_user(f"booking-wait-{uuid4().hex}@example.com", UserRole.CUSTOMER)
        session.add(waiting_customer)
        session.flush()
        entry = WaitlistEntry(
            user_id=waiting_customer.id, treatment_id=booking_data.treatment_id,
            preferred_date=booking_data.appointment_date,
        )
        session.add(entry)
        session.commit()
        waiting_id, entry_id = waiting_customer.id, entry.id
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/staff/appointments",
                                  json={**payload(booking_data), "customer_id": booking_data.customer_id},
                                  headers=admin_headers)
            assert created.status_code == 201, created.text
            moved = client.patch(f"/api/v1/staff/appointments/{created.json()['id']}/reschedule",
                                 json={"beautician_id": booking_data.beautician_ids[1],
                                       "start_time": local_start(booking_data, 9, 45).isoformat()},
                                 headers=admin_headers)
            assert moved.status_code == 200, moved.text
        with SessionLocal() as session:
            offer = session.get(WaitlistEntry, entry_id)
            assert offer.status == WaitlistStatus.OFFERED
            assert offer.beautician_id == booking_data.beautician_ids[0]
            assert as_utc(offer.offered_start_time) == local_start(booking_data, 9).astimezone(UTC)
    finally:
        with SessionLocal() as session:
            session.execute(delete(WaitlistEntry).where(WaitlistEntry.id == entry_id))
            session.execute(delete(User).where(User.id == waiting_id))
            session.commit()


def test_admin_reschedule_keeps_package_and_rejects_expired_target(booking_data: BookingTestData, admin_headers) -> None:
    with SessionLocal() as session:
        treatment = session.get(Treatment, booking_data.treatment_id)
        bundle = Package(
            name=f"Booking package {uuid4().hex}", price=Decimal("200.00"),
            sessions=2, validity_days=14, treatments=[treatment],
        )
        session.add(bundle)
        session.flush()
        owned = UserPackage(
            user_id=booking_data.customer_id, package_id=bundle.id,
            total_sessions=2, used_sessions=0, remaining_sessions=2,
            expiration_date=booking_data.appointment_date + timedelta(days=2),
        )
        session.add(owned)
        session.commit()
        owned_id, bundle_id = owned.id, bundle.id
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/staff/appointments",
                json={**payload(booking_data), "customer_id": booking_data.customer_id,
                      "user_package_id": owned_id}, headers=admin_headers,
            )
            assert created.status_code == 201, created.text
            path = f"/api/v1/staff/appointments/{created.json()['id']}/reschedule"
            moved = client.patch(path, json={
                "beautician_id": booking_data.beautician_ids[1],
                "start_time": local_start(booking_data, 9, 45).isoformat(),
            }, headers=admin_headers)
            assert moved.status_code == 200, moved.text
            assert moved.json()["user_package_id"] == owned_id
            too_late = client.patch(path, json={
                "beautician_id": booking_data.beautician_ids[1],
                "start_time": (local_start(booking_data, 9) + timedelta(days=7)).isoformat(),
            }, headers=admin_headers)
            assert too_late.status_code == 409
            with SessionLocal() as session:
                appointment = session.get(Appointment, created.json()["id"])
                assert appointment.user_package_id == owned_id
                assert as_utc(appointment.start_time) == local_start(booking_data, 9, 45).astimezone(UTC)
    finally:
        with SessionLocal() as session:
            session.execute(delete(Appointment).where(Appointment.user_package_id == owned_id))
            session.delete(session.get(UserPackage, owned_id))
            session.flush()
            session.delete(session.get(Package, bundle_id))
            session.commit()


def local_start(data: BookingTestData, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(
        data.appointment_date,
        time(hour, minute),
        tzinfo=BUSINESS_TIMEZONE,
    )


def payload(
    data: BookingTestData,
    hour: int = 9,
    minute: int = 0,
    *,
    treatment_id: int | None = None,
    beautician_id: int | None = None,
) -> dict[str, int | str]:
    return {
        "treatment_id": treatment_id or data.treatment_id,
        "beautician_id": beautician_id or data.beautician_ids[0],
        "start_time": local_start(data, hour, minute).isoformat(),
    }


def test_customer_can_book_available_slot(booking_data: BookingTestData) -> None:
    with TestClient(app) as client:
        response = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] == booking_data.customer_id
    assert body["status"] == AppointmentStatus.BOOKED.value
    assert datetime.fromisoformat(body["end_time"]) - datetime.fromisoformat(
        body["start_time"]
    ) == timedelta(minutes=45)
    with SessionLocal() as session:
        assert session.get(Appointment, body["id"]) is not None


def test_same_treatment_cannot_overlap_across_beauticians(
    booking_data: BookingTestData,
) -> None:
    with TestClient(app) as client:
        first = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )
        second = client.post(
            BOOKING_URL,
            json=payload(
                booking_data,
                minute=15,
                beautician_id=booking_data.beautician_ids[1],
            ),
            headers=headers(booking_data),
        )

    assert first.status_code == 201
    assert second.status_code == 409


def test_same_beautician_cannot_overlap_other_treatment(
    booking_data: BookingTestData,
) -> None:
    with TestClient(app) as client:
        first = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )
        second = client.post(
            BOOKING_URL,
            json=payload(
                booking_data,
                minute=15,
                treatment_id=booking_data.other_treatment_id,
            ),
            headers=headers(booking_data),
        )

    assert first.status_code == 201
    assert second.status_code == 409


def test_next_slot_can_start_when_previous_ends(
    booking_data: BookingTestData,
) -> None:
    with TestClient(app) as client:
        first = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )
        second = client.post(
            BOOKING_URL,
            json=payload(
                booking_data,
                minute=45,
                beautician_id=booking_data.beautician_ids[1],
            ),
            headers=headers(booking_data),
        )

    assert first.status_code == 201
    assert second.status_code == 201


def test_slot_must_fit_inside_working_hours(
    booking_data: BookingTestData,
) -> None:
    with TestClient(app) as client:
        response = client.post(
            BOOKING_URL,
            json=payload(booking_data, hour=11, minute=30),
            headers=headers(booking_data),
        )

    assert response.status_code == 409


def test_missing_treatment_or_unqualified_beautician_returns_404(
    booking_data: BookingTestData,
) -> None:
    with TestClient(app) as client:
        missing_treatment = client.post(
            BOOKING_URL,
            json=payload(booking_data, treatment_id=99999999),
            headers=headers(booking_data),
        )
        unqualified_beautician = client.post(
            BOOKING_URL,
            json=payload(
                booking_data,
                treatment_id=booking_data.other_treatment_id,
                beautician_id=booking_data.beautician_ids[1],
            ),
            headers=headers(booking_data),
        )

    assert missing_treatment.status_code == 404
    assert unqualified_beautician.status_code == 404


@pytest.mark.parametrize(
    "start_time",
    ["2026-09-14T09:00:00", "2026-09-14T09:10:00+03:00"],
)
def test_start_time_requires_offset_and_quarter_hour(
    booking_data: BookingTestData,
    start_time: str,
) -> None:
    request = payload(booking_data)
    request["start_time"] = start_time
    with TestClient(app) as client:
        response = client.post(
            BOOKING_URL,
            json=request,
            headers=headers(booking_data),
        )

    assert response.status_code == 422


def test_only_authenticated_customers_can_book(
    booking_data: BookingTestData,
) -> None:
    with TestClient(app) as client:
        unauthenticated = client.post(BOOKING_URL, json=payload(booking_data))
        staff = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data, staff=True),
        )

    assert unauthenticated.status_code == 401
    assert staff.status_code == 403


def test_booking_fails_closed_when_redis_is_unavailable(
    booking_data: BookingTestData,
) -> None:
    app.dependency_overrides[get_booking_lock_manager] = lambda: (
        BookingLockManager(UnavailableRedis())
    )
    with TestClient(app) as client:
        response = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )

    assert response.status_code == 503
    with SessionLocal() as session:
        appointments = session.scalars(
            select(Appointment).where(
                Appointment.customer_id == booking_data.customer_id
            )
        ).all()
    assert appointments == []


def test_busy_lock_returns_conflict_without_creating_appointment(
    booking_data: BookingTestData,
) -> None:
    app.dependency_overrides[get_booking_lock_manager] = lambda: (
        BookingLockManager(BusyRedis())
    )
    with TestClient(app) as client:
        response = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )

    assert response.status_code == 409
    with SessionLocal() as session:
        assert session.scalars(
            select(Appointment).where(
                Appointment.customer_id == booking_data.customer_id
            )
        ).all() == []


def test_expired_lock_does_not_hide_successful_commit(
    booking_data: BookingTestData,
) -> None:
    app.dependency_overrides[get_booking_lock_manager] = lambda: (
        BookingLockManager(ExpiredRedis())
    )
    with TestClient(app) as client:
        response = client.post(
            BOOKING_URL,
            json=payload(booking_data),
            headers=headers(booking_data),
        )

    assert response.status_code == 201
    with SessionLocal() as session:
        assert session.get(Appointment, response.json()["id"]) is not None


def test_concurrent_requests_create_only_one_appointment(
    booking_data: BookingTestData,
) -> None:
    barrier = Barrier(3)

    def book(beautician_id: int) -> int:
        barrier.wait()
        with TestClient(app) as client:
            response = client.post(
                BOOKING_URL,
                json=payload(booking_data, beautician_id=beautician_id),
                headers=headers(booking_data),
            )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(book, booking_data.beautician_ids[0])
        second = executor.submit(book, booking_data.beautician_ids[1])
        barrier.wait()
        statuses = sorted([first.result(), second.result()])

    assert statuses == [201, 409]
    with SessionLocal() as session:
        appointments = session.scalars(
            select(Appointment).where(
                Appointment.customer_id == booking_data.customer_id
            )
        ).all()
    assert len(appointments) == 1
