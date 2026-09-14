from datetime import datetime, time, timedelta
from threading import Lock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.routes.appointments import get_booking_lock_manager
from app.core.tokens import issue_token_pair
from app.db.session import SessionLocal
from app.main import app
from app.models.appointment import Appointment
from app.models.beautician import Beautician
from app.models.order import Order, OrderItem
from app.models.package import Package, UserPackage
from app.models.treatment import Treatment
from app.models.user import User, UserRole
from app.models.waitlist import WaitlistEntry
from app.services.booking_lock import BookingLockManager

ZONE = ZoneInfo("Asia/Jerusalem")


class FakeLock:
    def __init__(self, mutex: Lock, wait: int) -> None:
        self.mutex = mutex
        self.wait = wait

    def acquire(self) -> bool:
        return self.mutex.acquire(timeout=self.wait)

    def release(self) -> None:
        self.mutex.release()


class FakeRedis:
    def __init__(self) -> None:
        self.guard = Lock()
        self.locks: dict[str, Lock] = {}

    def lock(self, name: str, *, timeout: int, blocking_timeout: int) -> FakeLock:
        with self.guard:
            mutex = self.locks.setdefault(name, Lock())
        return FakeLock(mutex, blocking_timeout)


@pytest.fixture
def customers():
    suffix = uuid4().hex
    with SessionLocal() as session:
        first = User(
            first_name="Stage", last_name="Four",
            email=f"stage4-first-{suffix}@example.com", phone="050-0000101",
            password_hash="unused", role=UserRole.CUSTOMER,
        )
        second = User(
            first_name="Stage", last_name="Four",
            email=f"stage4-second-{suffix}@example.com", phone="050-0000102",
            password_hash="unused", role=UserRole.CUSTOMER,
        )
        session.add_all([first, second])
        session.commit()
        ids = (first.id, second.id)

    app.dependency_overrides[get_booking_lock_manager] = lambda: BookingLockManager(FakeRedis())
    try:
        yield ids
    finally:
        app.dependency_overrides.pop(get_booking_lock_manager, None)
        with SessionLocal() as session:
            order_ids = list(session.scalars(select(Order.id).where(Order.user_id.in_(ids))))
            session.execute(delete(WaitlistEntry).where(WaitlistEntry.user_id.in_(ids)))
            session.execute(delete(Appointment).where(Appointment.customer_id.in_(ids)))
            session.execute(delete(UserPackage).where(UserPackage.user_id.in_(ids)))
            session.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
            session.execute(delete(Order).where(Order.user_id.in_(ids)))
            session.execute(delete(User).where(User.id.in_(ids)))
            session.commit()


def auth(user_id: int, role: UserRole = UserRole.CUSTOMER) -> dict[str, str]:
    token = issue_token_pair(user_id, role).access_token
    return {"Authorization": f"Bearer {token}"}


def next_monday():
    today = datetime.now(ZONE).date()
    days = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


def demo_entities() -> tuple[int, int, int, int]:
    with SessionLocal() as session:
        treatment = session.scalar(select(Treatment).where(Treatment.name == "הסרת שיער בלייזר"))
        package = session.scalar(select(Package).where(Package.name.like("סדרת לייזר%")))
        staff = session.scalar(select(User).where(User.email == "sigal@scosmetics.local"))
        beautician = session.scalar(select(Beautician).where(Beautician.user_id == staff.id))
        return treatment.id, package.id, staff.id, beautician.id


def booking_payload(treatment_id: int, beautician_id: int, hour: int, user_package_id=None):
    return {
        "treatment_id": treatment_id,
        "beautician_id": beautician_id,
        "start_time": datetime.combine(next_monday(), time(hour), tzinfo=ZONE).isoformat(),
        "user_package_id": user_package_id,
    }


def test_demo_purchase_booking_and_completion_use_balance_once(customers) -> None:
    customer_id = customers[0]
    with TestClient(app) as client:
        treatment_id, package_id, staff_id, beautician_id = demo_entities()
        purchase = client.post(
            "/api/v1/orders", json={"package_id": package_id}, headers=auth(customer_id)
        )
        assert purchase.status_code == 201
        assert purchase.json()["status"] == "demo_confirmed"
        user_package_id = purchase.json()["user_package_ids"][0]

        # Arrange one remaining session so reservation and exhaustion are easy to see.
        with SessionLocal() as session:
            user_package = session.get(UserPackage, user_package_id)
            user_package.used_sessions = user_package.total_sessions - 1
            user_package.remaining_sessions = 1
            session.commit()

        first = client.post(
            "/api/v1/appointments",
            json=booking_payload(treatment_id, beautician_id, 10, user_package_id),
            headers=auth(customer_id),
        )
        assert first.status_code == 201
        assert client.get("/api/v1/me/packages", headers=auth(customer_id)).json()[0]["remaining_sessions"] == 1
        second = client.post(
            "/api/v1/appointments",
            json=booking_payload(treatment_id, beautician_id, 11, user_package_id),
            headers=auth(customer_id),
        )
        assert second.status_code == 409

        complete_url = f"/api/v1/appointments/{first.json()['id']}/complete"
        assert client.patch(complete_url, headers=auth(staff_id, UserRole.BEAUTICIAN)).status_code == 200
        assert client.patch(complete_url, headers=auth(staff_id, UserRole.BEAUTICIAN)).status_code == 200
        balance = client.get("/api/v1/me/packages", headers=auth(customer_id)).json()[0]
        assert balance["remaining_sessions"] == 0
        assert balance["used_sessions"] == balance["total_sessions"]
        assert len(client.get("/api/v1/me/orders", headers=auth(customer_id)).json()) == 1
        own_appointments = client.get("/api/v1/me/appointments", headers=auth(customer_id)).json()
        assert len(own_appointments) == 1
        assert own_appointments[0]["start_time"].endswith("Z")


def test_cancellation_offers_waitlist_slot_only_to_next_customer(customers) -> None:
    first_customer, waiting_customer = customers
    with TestClient(app) as client:
        treatment_id, _, _, beautician_id = demo_entities()
        original = client.post(
            "/api/v1/appointments",
            json=booking_payload(treatment_id, beautician_id, 10),
            headers=auth(first_customer),
        )
        assert original.status_code == 201

        joined = client.post(
            "/api/v1/waitlist",
            json={
                "treatment_id": treatment_id,
                "preferred_date": next_monday().isoformat(),
                "beautician_id": beautician_id,
            },
            headers=auth(waiting_customer),
        )
        assert joined.status_code == 201
        assert joined.json()["status"] == "waiting"

        cancelled = client.delete(
            f"/api/v1/appointments/{original.json()['id']}",
            headers=auth(first_customer),
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        offer = client.get("/api/v1/me/waitlist", headers=auth(waiting_customer)).json()[0]
        assert offer["status"] == "offered"
        assert offer["offer_expired"] is False
        params = {
            "treatment_id": treatment_id,
            "date": next_monday().isoformat(),
            "beautician_id": beautician_id,
        }
        first_slots = client.get(
            "/api/v1/appointments/availability", params=params, headers=auth(first_customer)
        ).json()["slots"]
        waiting_slots = client.get(
            "/api/v1/appointments/availability", params=params, headers=auth(waiting_customer)
        ).json()["slots"]
        offered_start = offer["offered_start_time"]
        assert all(slot["start_time"] != offered_start for slot in first_slots)
        assert any(slot["start_time"] == offered_start for slot in waiting_slots)

        accepted = client.post(
            "/api/v1/appointments",
            json={
                "treatment_id": treatment_id,
                "beautician_id": beautician_id,
                "start_time": offered_start,
            },
            headers=auth(waiting_customer),
        )
        assert accepted.status_code == 201
        assert client.get("/api/v1/me/waitlist", headers=auth(waiting_customer)).json()[0]["status"] == "fulfilled"
