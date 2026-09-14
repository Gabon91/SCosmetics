"""The new staff and CMS routes must enforce roles and keep public data in sync."""

from datetime import UTC, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.tokens import issue_token_pair
from app.db.session import SessionLocal
from app.main import app
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician
from app.models.site import TeamMember
from app.models.treatment import Treatment
from app.models.user import User, UserRole

ZONE = ZoneInfo("Asia/Jerusalem")


def token_for(user: User) -> dict[str, str]:
    token = issue_token_pair(user.id, user.role).access_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_context():
    suffix = uuid4().hex
    with TestClient(app) as client:
        with SessionLocal() as session:
            admin = User(
                first_name="Stage", last_name="Five",
                email=f"stage5-admin-{suffix}@example.com", phone="050-0000000",
                password_hash="unused", role=UserRole.ADMIN,
            )
            customer = User(
                first_name="Stage", last_name="Customer",
                email=f"stage5-customer-{suffix}@example.com", phone="050-0000000",
                password_hash="unused", role=UserRole.CUSTOMER,
            )
            session.add_all([admin, customer])
            session.flush()
            beauticians = session.scalars(select(Beautician).order_by(Beautician.id).limit(2)).all()
            assert len(beauticians) == 2
            staff_users = [session.get(User, person.user_id) for person in beauticians]
            treatment = session.scalar(select(Treatment).where(Treatment.active.is_(True)))
            assert treatment is not None
            day = datetime.now(ZONE).date()
            appointments = []
            for index, person in enumerate(beauticians):
                start = datetime.combine(day, time(10 + index), tzinfo=ZONE).astimezone(UTC)
                item = Appointment(
                    customer_id=customer.id, beautician_id=person.id,
                    treatment_id=treatment.id, start_time=start,
                    end_time=start + timedelta(minutes=treatment.duration_minutes),
                )
                session.add(item)
                appointments.append(item)
            session.commit()
            context = {
                "admin": token_for(admin),
                "customer": token_for(customer),
                "staff": [token_for(user) for user in staff_users],
                "appointments": [item.id for item in appointments],
                "day": day.isoformat(),
                "customer_id": customer.id,
                "admin_id": admin.id,
            }
        try:
            yield client, context
        finally:
            with SessionLocal() as session:
                session.execute(delete(Appointment).where(Appointment.customer_id == context["customer_id"]))
                session.execute(delete(User).where(User.id.in_([context["customer_id"], context["admin_id"]])))
                session.commit()


def test_staff_routes_require_authentication_and_role(staff_context) -> None:
    client, context = staff_context
    for path in ("/api/v1/staff/dashboard", "/api/v1/staff/appointments", "/api/v1/cms/treatments"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=context["customer"]).status_code == 403
    assert client.get("/api/v1/cms/treatments", headers=context["staff"][0]).status_code == 403
    assert client.get("/api/v1/staff/dashboard", headers=context["staff"][0]).status_code == 200
    assert client.get("/api/v1/cms/treatments", headers=context["admin"]).status_code == 200


def test_admin_customer_list_and_edit_are_private(staff_context) -> None:
    client, context = staff_context
    path = "/api/v1/staff/customers"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=context["customer"]).status_code == 403
    assert client.get(path, headers=context["staff"][0]).status_code == 403
    customers = client.get(path, params={"search": "stage5-customer"}, headers=context["admin"])
    assert customers.status_code == 200
    assert any(item["id"] == context["customer_id"] for item in customers.json())
    edit = f"{path}/{context['customer_id']}"
    assert client.patch(edit, json={"phone": "050-8888888"}, headers=context["staff"][0]).status_code == 403
    result = client.patch(edit, json={"phone": "050-8888888"}, headers=context["admin"])
    assert result.status_code == 200
    assert result.json()["phone"] == "050-8888888"
    assert "password_hash" not in result.json()


def test_customer_updates_only_own_profile(staff_context) -> None:
    client, context = staff_context
    path = "/api/v1/me/profile"
    assert client.patch(path, json={"first_name": "Nope"}).status_code == 401
    assert client.patch(path, json={"first_name": "Nope"}, headers=context["staff"][0]).status_code == 403
    response = client.patch(path, json={"first_name": "Updated", "phone": "050-7777777"}, headers=context["customer"])
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert client.get("/api/v1/auth/me", headers=context["customer"]).json()["phone"] == "050-7777777"
    assert client.patch(path, json={"role": "admin"}, headers=context["customer"]).json()["role"] == "customer"


def test_admin_can_cancel_future_booking_but_staff_cannot(staff_context) -> None:
    client, context = staff_context
    with SessionLocal() as session:
        treatment = session.scalar(select(Treatment).where(Treatment.active.is_(True)))
        beautician = session.scalar(select(Beautician).order_by(Beautician.id))
        assert treatment is not None and beautician is not None
        start = datetime.combine(datetime.now(ZONE).date() + timedelta(days=5), time(11), tzinfo=ZONE).astimezone(UTC)
        appointment = Appointment(
            customer_id=context["customer_id"], beautician_id=beautician.id,
            treatment_id=treatment.id, start_time=start,
            end_time=start + timedelta(minutes=treatment.duration_minutes),
        )
        session.add(appointment)
        session.commit()
        appointment_id = appointment.id
    path = f"/api/v1/staff/appointments/{appointment_id}"
    assert client.delete(path, headers=context["staff"][0]).status_code == 403
    assert client.delete(path, headers=context["admin"]).status_code == 200
    assert client.delete(path, headers=context["admin"]).status_code == 409
    with SessionLocal() as session:
        assert session.get(Appointment, appointment_id).status == AppointmentStatus.CANCELLED


def test_beautician_sees_only_own_appointments(staff_context) -> None:
    client, context = staff_context
    first_id, second_id = context["appointments"]
    path = f"/api/v1/staff/appointments?date={context['day']}"
    first = client.get(path, headers=context["staff"][0])
    second = client.get(path, headers=context["staff"][1])
    admin = client.get(path, headers=context["admin"])
    assert first.status_code == second.status_code == admin.status_code == 200
    assert first_id in {item["id"] for item in first.json()}
    assert second_id not in {item["id"] for item in first.json()}
    assert second_id in {item["id"] for item in second.json()}
    assert first_id not in {item["id"] for item in second.json()}
    assert {first_id, second_id} <= {item["id"] for item in admin.json()}
    assert client.get("/api/v1/staff/dashboard", headers=context["staff"][0]).json()["active_customers"] is None
    assert client.get("/api/v1/staff/dashboard", headers=context["admin"]).json()["active_customers"] >= 1


def test_no_show_is_scoped_and_idempotent(staff_context) -> None:
    client, context = staff_context
    appointment_id = context["appointments"][0]
    path = f"/api/v1/staff/appointments/{appointment_id}/no-show"
    assert client.patch(path, headers=context["customer"]).status_code == 403
    assert client.patch(path, headers=context["staff"][1]).status_code == 403
    first = client.patch(path, headers=context["staff"][0])
    again = client.patch(path, headers=context["staff"][0])
    assert first.status_code == again.status_code == 200
    assert first.json()["status"] == again.json()["status"] == AppointmentStatus.NO_SHOW.value


def test_csv_reports_are_admin_only(staff_context) -> None:
    client, context = staff_context
    path = "/api/v1/staff/reports/appointments.csv"
    assert client.get(path, headers=context["staff"][0]).status_code == 403
    response = client.get(path, headers=context["admin"])
    assert response.status_code == 200
    assert response.text.startswith("\ufeffID,Customer,Beautician")
    assert str(context["appointments"][0]) in response.text


def test_admin_treatment_changes_are_public_and_archive_hides_them(staff_context) -> None:
    client, context = staff_context
    name = f"Stage5 {uuid4().hex}"
    created = client.post(
        "/api/v1/cms/treatments", headers=context["admin"],
        json={
            "name": name, "category": "בדיקות", "description": "טיפול בדיקה",
            "duration_minutes": 45, "price": "125.00", "accent": "rose",
        },
    )
    assert created.status_code == 201
    treatment_id = created.json()["id"]
    try:
        changed = client.patch(
            f"/api/v1/cms/treatments/{treatment_id}",
            headers=context["admin"], json={"duration_minutes": 60},
        )
        assert changed.status_code == 200
        assert changed.json()["duration_minutes"] == 60
        assert any(item["id"] == treatment_id for item in client.get("/api/v1/treatments").json())
        archived = client.delete(f"/api/v1/cms/treatments/{treatment_id}", headers=context["admin"])
        assert archived.status_code == 200
        assert archived.json()["active"] is False
        assert not any(item["id"] == treatment_id for item in client.get("/api/v1/treatments").json())
    finally:
        with SessionLocal() as session:
            session.execute(delete(Treatment).where(Treatment.id == treatment_id))
            session.commit()


def test_admin_can_edit_site_copy_but_unknown_keys_are_rejected(staff_context) -> None:
    client, context = staff_context
    path = "/api/v1/cms/content"
    original = client.get(path, headers=context["admin"]).json()["about_title"]
    try:
        changed = client.patch(path, headers=context["admin"], json={"values": {"about_title": "כותרת חדשה"}})
        assert changed.status_code == 200
        assert client.get("/api/v1/site/content").json()["about_title"] == "כותרת חדשה"
        invalid = client.patch(path, headers=context["admin"], json={"values": {"unknown_key": "value"}})
        assert invalid.status_code == 422
        assert client.get("/api/v1/site/content").json()["about_title"] == "כותרת חדשה"
    finally:
        client.patch(path, headers=context["admin"], json={"values": {"about_title": original}})


def test_equipment_is_public_only_while_active(staff_context) -> None:
    client, context = staff_context
    treatment_id = client.get("/api/v1/treatments").json()[0]["id"]
    created = client.post(
        "/api/v1/cms/equipment", headers=context["admin"],
        json={"name": f"Stage5 {uuid4().hex}", "description": "מכשיר בדיקה", "treatment_ids": [treatment_id]},
    )
    assert created.status_code == 201
    equipment_id = created.json()["id"]
    assert any(item["id"] == equipment_id for item in client.get("/api/v1/site/equipment").json())
    edited = client.patch(
        f"/api/v1/cms/equipment/{equipment_id}", headers=context["admin"],
        json={"description": "תיאור מעודכן"},
    )
    assert edited.status_code == 200
    assert edited.json()["description"] == "תיאור מעודכן"
    archived = client.delete(f"/api/v1/cms/equipment/{equipment_id}", headers=context["admin"])
    assert archived.status_code == 200
    assert not any(item["id"] == equipment_id for item in client.get("/api/v1/site/equipment").json())


def test_package_crud_and_duration_validation(staff_context) -> None:
    client, context = staff_context
    treatment_id = client.get("/api/v1/treatments").json()[0]["id"]
    invalid_treatment = client.post(
        "/api/v1/cms/treatments", headers=context["admin"],
        json={"name": "Invalid duration", "category": "בדיקות", "description": "טיפול בדיקה", "duration_minutes": 35, "price": "100"},
    )
    assert invalid_treatment.status_code == 422
    created = client.post(
        "/api/v1/cms/packages", headers=context["admin"],
        json={"name": f"Stage5 {uuid4().hex}", "price": "300.00", "sessions": 3,
              "validity_days": 90, "treatment_ids": [treatment_id]},
    )
    assert created.status_code == 201
    package_id = created.json()["id"]
    changed = client.patch(
        f"/api/v1/cms/packages/{package_id}", headers=context["admin"], json={"sessions": 4},
    )
    assert changed.status_code == 200
    assert changed.json()["sessions"] == 4
    assert any(item["id"] == package_id for item in client.get("/api/v1/packages").json())
    archived = client.delete(f"/api/v1/cms/packages/{package_id}", headers=context["admin"])
    assert archived.status_code == 200
    assert not any(item["id"] == package_id for item in client.get("/api/v1/packages").json())


def test_team_editor_updates_public_cards_and_single_featured_profile(staff_context) -> None:
    client, context = staff_context
    before = client.get("/api/v1/cms/team", headers=context["admin"]).json()
    original_featured = next(item["id"] for item in before if item["featured"])
    created = client.post(
        "/api/v1/cms/team", headers=context["admin"],
        json={"name": f"Stage5 {uuid4().hex}", "title": "מטפלת לדוגמה", "description": "תיאור לבדיקה",
              "image_url": "/images/logo-scosmetics.png", "display_order": 20},
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    try:
        assert any(item["id"] == member_id for item in client.get("/api/v1/site/team").json())
        featured = client.patch(
            f"/api/v1/cms/team/{member_id}", headers=context["admin"], json={"featured": True},
        )
        assert featured.status_code == 200
        assert [item["id"] for item in client.get("/api/v1/site/team").json() if item["featured"]] == [member_id]
        archived = client.delete(f"/api/v1/cms/team/{member_id}", headers=context["admin"])
        assert archived.status_code == 200
        assert not any(item["id"] == member_id for item in client.get("/api/v1/site/team").json())
    finally:
        client.patch(f"/api/v1/cms/team/{original_featured}", headers=context["admin"], json={"featured": True})
        with SessionLocal() as session:
            session.execute(delete(TeamMember).where(TeamMember.id == member_id))
            session.commit()


def test_admin_manages_bookable_beautician_skills_hours_and_access(staff_context) -> None:
    client, context = staff_context
    treatment_id = client.get("/api/v1/treatments").json()[0]["id"]
    email = f"stage5-staff-{uuid4().hex}@example.com"
    password = "StrongPassword123!"
    created = client.post(
        "/api/v1/cms/beauticians", headers=context["admin"],
        json={
            "first_name": "מטפלת", "last_name": "בדיקה", "email": email,
            "phone": "050-1234567", "password": password,
            "bio": "מטפלת מוסמכת", "treatment_ids": [treatment_id],
            "working_hours": [{"weekday": 0, "start_time": "09:00", "end_time": "17:00"}],
        },
    )
    assert created.status_code == 201, created.text
    person_id = created.json()["id"]
    user_id = created.json()["user_id"]
    try:
        assert created.json()["treatment_ids"] == [treatment_id]
        assert client.post("/api/v1/auth/login", json={"email": email, "password": password}).status_code == 200
        assert client.get("/api/v1/cms/beauticians", headers=context["staff"][0]).status_code == 403
        overlapping = client.patch(
            f"/api/v1/cms/beauticians/{person_id}", headers=context["admin"],
            json={"working_hours": [
                {"weekday": 0, "start_time": "09:00", "end_time": "12:00"},
                {"weekday": 0, "start_time": "11:00", "end_time": "14:00"},
            ]},
        )
        assert overlapping.status_code == 422
        updated = client.patch(
            f"/api/v1/cms/beauticians/{person_id}", headers=context["admin"],
            json={"working_hours": [{"weekday": 2, "start_time": "10:00", "end_time": "16:00"}]},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["working_hours"][0]["weekday"] == 2
        archived = client.delete(f"/api/v1/cms/beauticians/{person_id}", headers=context["admin"])
        assert archived.status_code == 200
        assert archived.json()["active"] is False
        assert client.post("/api/v1/auth/login", json={"email": email, "password": password}).status_code == 403
        assert person_id not in {item["id"] for item in client.get("/api/v1/staff/beauticians", headers=context["admin"]).json()}
    finally:
        with SessionLocal() as session:
            person = session.get(Beautician, person_id)
            if person is not None:
                session.delete(person)
                session.flush()
            user = session.get(User, user_id)
            if user is not None:
                session.delete(user)
            session.commit()
