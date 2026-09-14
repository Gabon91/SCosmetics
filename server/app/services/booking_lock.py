import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

from redis import Redis
from redis.exceptions import LockError, RedisError
from redis.lock import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)

LOCK_TTL_SECONDS = 30
LOCK_WAIT_SECONDS = 2


class BookingLockBusyError(Exception):
    pass


class BookingLockUnavailableError(Exception):
    pass


class BookingLockManager:
    def __init__(self, client: Redis | None = None) -> None:
        self.client = client if client is not None else Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )

    @contextmanager
    def hold(
        self,
        treatment_id: int,
        beautician_id: int,
        appointment_date: date,
    ) -> Generator[None, None, None]:
        with self.hold_many([(treatment_id, beautician_id, appointment_date)]):
            yield

    @contextmanager
    def hold_many(
        self, resources: list[tuple[int, int, date]],
    ) -> Generator[None, None, None]:
        """Acquire both old and new slot locks in one stable order."""
        keys = sorted({
            key
            for treatment_id, beautician_id, appointment_date in resources
            for key in (
                f"booking:beautician:{beautician_id}:{appointment_date.isoformat()}",
                f"booking:treatment:{treatment_id}:{appointment_date.isoformat()}",
            )
        })
        acquired: list[Lock] = []

        try:
            for key in keys:
                try:
                    lock = self.client.lock(
                        key,
                        timeout=LOCK_TTL_SECONDS,
                        blocking_timeout=LOCK_WAIT_SECONDS,
                    )
                    locked = lock.acquire()
                except RedisError as error:
                    raise BookingLockUnavailableError from error
                if not locked:
                    raise BookingLockBusyError
                acquired.append(lock)

            yield
        finally:
            for lock in reversed(acquired):
                try:
                    lock.release()
                except (LockError, RedisError):
                    # A timed-out lock may no longer belong to this request.
                    logger.warning("Could not release booking lock %s", lock.name)
