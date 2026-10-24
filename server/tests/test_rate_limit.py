from collections import defaultdict

from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.main import app


class CountingLimiter:
    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)

    async def hit(self, key: str) -> tuple[int, int]:
        self.counts[key] += 1
        return self.counts[key], 42


def test_login_returns_429_after_ten_attempts() -> None:
    with TestClient(app) as client:
        app.state.rate_limiter = CountingLimiter()
        for _ in range(10):
            response = client.post(
                "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong-password"}
            )
            assert response.status_code == 401
        limited = client.post(
            "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong-password"}
        )
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "42"


def test_public_reads_have_a_separate_bucket() -> None:
    with TestClient(app) as client:
        limiter = CountingLimiter()
        app.state.rate_limiter = limiter
        for _ in range(100):
            assert client.get("/api/v1/site/content").status_code == 200
        assert client.get("/api/v1/treatments").status_code == 429
        assert client.get("/health").status_code == 200
    assert len(limiter.counts) == 1


def test_redis_failure_does_not_break_login_in_development() -> None:
    class FailedLimiter:
        async def hit(self, _: str) -> tuple[int, int]:
            raise RedisError("Redis unavailable")

    with TestClient(app) as client:
        app.state.rate_limiter = FailedLimiter()
        response = client.post(
            "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong-password"}
        )
    assert response.status_code == 401
