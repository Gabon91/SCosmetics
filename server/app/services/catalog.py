import json

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.treatment import Treatment
from app.schemas.treatment import TreatmentRead

CACHE_KEY = "catalog:treatments:active"


class CatalogService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.cache = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        )

    def list_active_treatments(self) -> tuple[list[TreatmentRead], str]:
        cached = self._read_cache()
        if cached is not None:
            return cached, "HIT"

        records = self.session.scalars(
            select(Treatment)
            .where(Treatment.active.is_(True))
            .order_by(Treatment.id)
        ).all()
        treatments = [TreatmentRead.model_validate(record) for record in records]
        self._write_cache(treatments)
        return treatments, "MISS"

    def _read_cache(self) -> list[TreatmentRead] | None:
        try:
            payload = self.cache.get(CACHE_KEY)
        except RedisError:
            return None

        if payload is None:
            return None

        return [TreatmentRead.model_validate(item) for item in json.loads(payload)]

    def _write_cache(self, treatments: list[TreatmentRead]) -> None:
        try:
            self.cache.set(
                CACHE_KEY,
                json.dumps(
                    [treatment.model_dump() for treatment in treatments],
                    ensure_ascii=False,
                ),
                ex=settings.cache_ttl_seconds,
            )
        except RedisError:
            return

    def invalidate(self) -> None:
        """Remove stale public catalog data after an administrator changes a treatment."""
        try:
            self.cache.delete(CACHE_KEY)
        except RedisError:
            return
