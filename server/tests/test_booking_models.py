from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician, BeauticianWorkingHours
from app.models.treatment import Treatment
from app.models.user import User, UserRole


def make_user(email: str, role: UserRole) -> User:
    return User(
        first_name="Test",
        last_name="User",
        email=email,
        phone="050-0000000",
        password_hash="unused-in-model-tests",
        role=role,
    )


def make_treatment(name: str, duration_minutes: int) -> Treatment:
    return Treatment(
        name=name,
        category="בדיקות",
        description="טיפול לצורך בדיקת מודל הנתונים.",
        duration_minutes=duration_minutes,
        price=Decimal("100.00"),
        accent="rose",
        active=False,
    )


def test_treatments_support_different_durations() -> None:
    durations = [30, 45, 60, 75]

    with SessionLocal() as session:
        treatments = [
            make_treatment(f"Duration {duration}", duration)
            for duration in durations
        ]
        session.add_all(treatments)
        session.commit()

        assert [treatment.duration_minutes for treatment in treatments] == (
            durations
        )


def test_treatment_duration_must_use_15_minute_increments() -> None:
    with SessionLocal() as session:
        session.add(make_treatment("Invalid duration", 20))

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


def test_beautician_has_certifications_and_weekly_working_hours() -> None:
    with SessionLocal() as session:
        beautician_user = make_user(
            "booking-beautician@example.com",
            UserRole.BEAUTICIAN,
        )
        laser = make_treatment("Laser certification", 45)
        beautician = Beautician(
            user=beautician_user,
            bio="קוסמטיקאית מוסמכת לטיפולי לייזר.",
            treatments=[laser],
            working_hours=[
                BeauticianWorkingHours(
                    weekday=0,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            ],
        )
        session.add(beautician)
        session.commit()

        assert beautician.user.role is UserRole.BEAUTICIAN
        assert beautician.treatments == [laser]
        assert beautician.working_hours[0].weekday == 0
        assert beautician.working_hours[0].start_time == time(9, 0)


def test_appointment_links_customer_beautician_and_treatment() -> None:
    with SessionLocal() as session:
        customer = make_user("booking-customer@example.com", UserRole.CUSTOMER)
        beautician = Beautician(
            user=make_user(
                "appointment-beautician@example.com",
                UserRole.BEAUTICIAN,
            )
        )
        treatment = make_treatment("Appointment treatment", 75)
        beautician.treatments.append(treatment)
        session.add_all([customer, beautician])
        session.flush()

        start_time = datetime(2026, 9, 14, 9, 0, tzinfo=UTC)
        appointment = Appointment(
            customer=customer,
            beautician=beautician,
            treatment=treatment,
            start_time=start_time,
            end_time=start_time + timedelta(
                minutes=treatment.duration_minutes
            ),
        )
        session.add(appointment)
        session.commit()

        assert appointment.status is AppointmentStatus.BOOKED
        assert appointment.customer.email == "booking-customer@example.com"
        assert appointment.beautician.id == beautician.id
        assert appointment.treatment.duration_minutes == 75
        assert appointment.end_time - appointment.start_time == timedelta(
            minutes=75
        )


def test_working_hours_reject_an_invalid_time_range() -> None:
    with SessionLocal() as session:
        beautician = Beautician(
            user=make_user(
                "invalid-hours@example.com",
                UserRole.BEAUTICIAN,
            ),
            working_hours=[
                BeauticianWorkingHours(
                    weekday=1,
                    start_time=time(17, 0),
                    end_time=time(9, 0),
                )
            ],
        )
        session.add(beautician)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


def test_locked_is_not_a_persisted_appointment_status() -> None:
    assert {status.value for status in AppointmentStatus} == {
        "booked",
        "completed",
        "cancelled",
        "no_show",
    }
