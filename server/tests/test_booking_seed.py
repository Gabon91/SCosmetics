from sqlalchemy import func, select

from app.db.seed import seed_booking_demo, seed_treatments
from app.db.session import SessionLocal
from app.models.beautician import Beautician, BeauticianWorkingHours


def test_booking_demo_seed_is_idempotent() -> None:
    with SessionLocal() as session:
        seed_treatments(session)
        seed_booking_demo(session)
        first_beautician_count = session.scalar(
            select(func.count()).select_from(Beautician)
        )
        first_working_hours_count = session.scalar(
            select(func.count()).select_from(BeauticianWorkingHours)
        )

        seed_booking_demo(session)
        second_beautician_count = session.scalar(
            select(func.count()).select_from(Beautician)
        )
        second_working_hours_count = session.scalar(
            select(func.count()).select_from(BeauticianWorkingHours)
        )

    assert first_beautician_count == second_beautician_count
    assert first_working_hours_count == second_working_hours_count
    assert first_beautician_count >= 2
