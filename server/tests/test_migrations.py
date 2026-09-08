import tempfile
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

SERVER_ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_creates_expected_schema() -> None:
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
            "treatments",
            "users",
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
    finally:
        if engine is not None:
            engine.dispose()
        database_path.unlink(missing_ok=True)
