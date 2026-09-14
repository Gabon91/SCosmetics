import tempfile
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

SERVER_ROOT = Path(__file__).resolve().parents[1]


def test_migrations_create_expected_schema_and_can_downgrade() -> None:
    database_path = Path(tempfile.gettempdir()) / f"migration-{uuid4().hex}.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    alembic_config = Config(str(SERVER_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(SERVER_ROOT / "migrations"),
    )
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    engine = None
    try:
        command.upgrade(alembic_config, "head")

        engine = create_engine(database_url)
        inspector = inspect(engine)

        assert set(inspector.get_table_names()) == {
            "alembic_version",
            "appointments",
            "beautician_treatments",
            "beautician_working_hours",
            "beauticians",
            "order_items",
            "orders",
            "package_treatments",
            "packages",
            "treatments",
            "user_packages",
            "users",
            "waitlist",
        }
        assert {column["name"] for column in inspector.get_columns("users")} == {
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "password_hash",
            "role",
            "active",
            "created_at",
        }
        assert any(
            index["name"] == "ix_users_email" and index["unique"]
            for index in inspector.get_indexes("users")
        )
        treatment_constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("treatments")
        }
        assert (
            "ck_treatments_duration_15_minute_increment"
            in treatment_constraints
        )
        assert {
            column["name"]
            for column in inspector.get_columns("appointments")
        } == {
            "id",
            "customer_id",
            "beautician_id",
            "treatment_id",
            "user_package_id",
            "start_time",
            "end_time",
            "status",
            "created_at",
            "completed_at",
        }
        appointment_indexes = {
            index["name"] for index in inspector.get_indexes("appointments")
        }
        assert "ix_appointments_beautician_start" in appointment_indexes
        assert "ix_appointments_treatment_start" in appointment_indexes

        engine.dispose()
        engine = None
        command.downgrade(alembic_config, "0001_initial_schema")

        engine = create_engine(database_url)
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {
            "alembic_version",
            "treatments",
            "users",
        }
        assert not {
            constraint["name"]
            for constraint in inspector.get_check_constraints("treatments")
        }
    finally:
        if engine is not None:
            engine.dispose()
        database_path.unlink(missing_ok=True)
