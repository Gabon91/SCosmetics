import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest

TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"scosmetics-{uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from app import models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
