r"""Exercise manager booking and rescheduling against local MySQL and Redis.

Run from server: .\.venv\Scripts\python.exe -m scripts.check_admin_booking
Creates temporary users and one appointment, then removes only those records.
"""

from datetime import datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.core.tokens import issue_token_pair
from app.db.session import SessionLocal
from app.models.appointment import Appointment
from app.models.treatment import Treatment
from app.models.user import User, UserRole
from scripts.check_concurrent_booking import check_local_services

API_URL = "http://127.0.0.1:8004"


def main() -> None:
    check_local_services(API_URL)
    suffix = uuid4().hex
    emails = (f"admin-booking-admin-{suffix}@example.com",
              f"admin-booking-customer-{suffix}@example.com")
    with SessionLocal() as session:
        treatment = session.scalar(select(Treatment).where(Treatment.name == "הסרת שיער בלייזר"))
        if treatment is None:
            raise RuntimeError("Demo laser treatment not found")
        treatment_id = treatment.id
        password_hash = hash_password(token_urlsafe(24))
        admin = User(first_name="Temporary", last_name="Manager", email=emails[0],
                     phone="050-000-0098", password_hash=password_hash, role=UserRole.ADMIN)
        customer = User(first_name="Temporary", last_name="Customer", email=emails[1],
                        phone="050-000-0097", password_hash=password_hash, role=UserRole.CUSTOMER)
        session.add_all([admin, customer])
        session.commit()
        admin_id, customer_id = admin.id, customer.id
        token = issue_token_pair(admin_id, UserRole.ADMIN).access_token

    try:
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(base_url=API_URL, timeout=15, trust_env=False) as client:
            today = datetime.now(ZoneInfo(settings.business_timezone)).date()
            choice = None
            for days_ahead in range(1, 15):
                day = today + timedelta(days=days_ahead)
                available = client.get("/api/v1/staff/booking-availability", headers=headers,
                    params={"customer_id": customer_id, "treatment_id": treatment_id, "date": day.isoformat()})
                available.raise_for_status()
                slots = available.json()["slots"]
                for first in slots:
                    second = next((slot for slot in slots if
                        datetime.fromisoformat(slot["start_time"]) >= datetime.fromisoformat(first["end_time"])), None)
                    if second is not None:
                        choice = (day, first, second)
                        break
                if choice:
                    break
            if choice is None:
                raise RuntimeError("No pair of non-overlapping slots in the next 14 days")
            day, first, second = choice
            created = client.post("/api/v1/staff/appointments", headers=headers, json={
                "customer_id": customer_id, "treatment_id": treatment_id,
                "beautician_id": first["beautician_id"], "start_time": first["start_time"],
            })
            if created.status_code != 201:
                raise RuntimeError(f"Manager booking failed: HTTP {created.status_code} {created.text}")
            appointment_id = created.json()["id"]
            changed = client.patch(f"/api/v1/staff/appointments/{appointment_id}/reschedule",
                headers=headers, json={"beautician_id": second["beautician_id"],
                                       "start_time": second["start_time"]})
            if changed.status_code != 200:
                raise RuntimeError(f"Manager reschedule failed: HTTP {changed.status_code} {changed.text}")
            if changed.json()["id"] != appointment_id:
                raise RuntimeError("Reschedule created a second appointment")
            with SessionLocal() as session:
                stored = session.scalars(select(Appointment).where(Appointment.customer_id == customer_id)).all()
                if len(stored) != 1 or stored[0].id != appointment_id:
                    raise RuntimeError("MySQL does not contain exactly the moved appointment")
            print(f"PASS: admin created and moved appointment #{appointment_id} on {day}; MySQL stores one record")
    finally:
        with SessionLocal() as session:
            for user_id, email in ((customer_id, emails[1]), (admin_id, emails[0])):
                user = session.get(User, user_id)
                if user is None or user.email != email:
                    raise RuntimeError("Temporary user changed; refusing cleanup")
            appointments = session.scalars(select(Appointment).where(Appointment.customer_id == customer_id)).all()
            for appointment in appointments:
                session.delete(appointment)
            session.flush()
            session.delete(session.get(User, customer_id))
            session.delete(session.get(User, admin_id))
            session.commit()
            print("Cleanup: removed temporary appointment and users")


if __name__ == "__main__":
    main()
