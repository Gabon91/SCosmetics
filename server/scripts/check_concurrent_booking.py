r"""Check a real booking race against the local API, MySQL, and Redis.

Run from the server directory:
    .\.venv\Scripts\python.exe -m scripts.check_concurrent_booking
"""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from secrets import token_urlsafe
from threading import Barrier
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from redis import Redis
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.appointment import Appointment
from app.models.user import User, UserRole


def check_local_services(api_url: str) -> None:
    api = urlsplit(api_url)
    database = make_url(settings.database_url)
    redis = urlsplit(settings.redis_url)
    local_hosts = {"127.0.0.1", "localhost"}

    if api.scheme != "http" or api.hostname not in local_hosts:
        raise RuntimeError("The test API must use local HTTP, not a remote URL")
    if (
        settings.environment != "development"
        or database.drivername != "mysql+pymysql"
        or database.host not in local_hosts
        or database.database != "scosmetics"
    ):
        raise RuntimeError("Use the local development MySQL database named scosmetics")
    if redis.scheme != "redis" or redis.hostname not in local_hosts:
        raise RuntimeError("Use a local Redis instance for this test")

    Redis.from_url(settings.redis_url, socket_connect_timeout=2).ping()
    with httpx.Client(base_url=api_url, timeout=10, trust_env=False) as client:
        health = client.get("/health")
        health.raise_for_status()
        if health.json().get("environment") != "development":
            raise RuntimeError("The API is not running in development mode")


def create_test_customer(email: str, password: str) -> int:
    with SessionLocal() as session:
        customer = User(
            first_name="Concurrency",
            last_name="Check",
            email=email,
            phone="050-000-0099",
            password_hash=hash_password(password),
            role=UserRole.CUSTOMER,
        )
        session.add(customer)
        session.flush()
        customer_id = customer.id
        session.commit()
        return customer_id


def find_shared_slot(
    client: httpx.Client, headers: dict[str, str]
) -> tuple[int, list[dict]]:
    treatments_response = client.get("/api/v1/treatments")
    treatments_response.raise_for_status()
    treatment = next(
        (
            item
            for item in treatments_response.json()
            if item["name"] == "הסרת שיער בלייזר"
        ),
        None,
    )
    if treatment is None:
        raise RuntimeError("The demo laser treatment was not found")

    today = datetime.now(ZoneInfo(settings.business_timezone)).date()
    for days_ahead in range(1, 15):
        appointment_date = today + timedelta(days=days_ahead)
        response = client.get(
            "/api/v1/appointments/availability",
            params={
                "treatment_id": treatment["id"],
                "date": appointment_date.isoformat(),
            },
            headers=headers,
        )
        response.raise_for_status()
        by_start: dict[str, dict[int, dict]] = defaultdict(dict)
        for slot in response.json()["slots"]:
            by_start[slot["start_time"]][slot["beautician_id"]] = slot
        for slots_by_beautician in by_start.values():
            if len(slots_by_beautician) >= 2:
                return treatment["id"], list(slots_by_beautician.values())[:2]

    raise RuntimeError("No shared slot for two beauticians in the next 14 days")


def book_at_the_same_moment(
    api_url: str,
    headers: dict[str, str],
    treatment_id: int,
    slots: list[dict],
) -> list[tuple[int, dict]]:
    # Both worker threads wait here until the main thread releases them.
    barrier = Barrier(3)

    def send(slot: dict) -> tuple[int, dict]:
        with httpx.Client(base_url=api_url, timeout=15, trust_env=False) as client:
            barrier.wait(timeout=10)
            response = client.post(
                "/api/v1/appointments",
                headers=headers,
                json={
                    "treatment_id": treatment_id,
                    "beautician_id": slot["beautician_id"],
                    "start_time": slot["start_time"],
                },
            )
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(send, slots[0])
        second = executor.submit(send, slots[1])
        barrier.wait(timeout=10)
        return [first.result(), second.result()]


def cleanup(customer_id: int, email: str) -> None:
    with SessionLocal() as session:
        customer = session.get(User, customer_id)
        if customer is None:
            return
        if customer.email != email:
            raise RuntimeError("Customer ID changed; refusing to delete another user")

        appointments = session.scalars(
            select(Appointment).where(Appointment.customer_id == customer_id)
        ).all()
        for appointment in appointments:
            session.delete(appointment)
        session.delete(customer)
        session.commit()
        print(f"Cleanup: removed {len(appointments)} test appointment(s) and the test customer")


def main(api_url: str) -> None:
    check_local_services(api_url)
    email = f"concurrent-check-{uuid4().hex}@example.com"
    password = token_urlsafe(24)
    customer_id = create_test_customer(email, password)
    print(f"Temporary customer ID: {customer_id}")

    try:
        with httpx.Client(base_url=api_url, timeout=10, trust_env=False) as client:
            login = client.post(
                "/api/v1/auth/login", json={"email": email, "password": password}
            )
            if login.status_code != 200:
                raise RuntimeError(
                    f"API login returned {login.status_code}; check its MySQL connection"
                )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            treatment_id, slots = find_shared_slot(client, headers)

        print(f"Shared slot: {slots[0]['start_time']}")
        print(f"Beauticians: {slots[0]['beautician_id']}, {slots[1]['beautician_id']}")
        results = book_at_the_same_moment(api_url, headers, treatment_id, slots)
        statuses = sorted(status for status, _ in results)
        print(f"Concurrent HTTP statuses: {statuses}")

        with SessionLocal() as session:
            appointments = session.scalars(
                select(Appointment).where(Appointment.customer_id == customer_id)
            ).all()
            stored_ids = {appointment.id for appointment in appointments}
        successful_ids = {
            body.get("id") for status, body in results if status == 201
        }
        print(f"Appointments stored in MySQL: {len(stored_ids)}")
        if statuses != [201, 409] or len(stored_ids) != 1 or stored_ids != successful_ids:
            raise RuntimeError(f"Booking race failed: {results}")
        print("PASS: exactly one booking was stored")
    finally:
        cleanup(customer_id, email)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8004",
        help="Local development API URL (default: http://127.0.0.1:8004)",
    )
    arguments = parser.parse_args()
    main(arguments.api_url.rstrip("/"))
