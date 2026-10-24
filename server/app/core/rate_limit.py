"""Small Redis-backed per-IP rate limiter for the API's exposed routes."""

from collections.abc import Awaitable, Callable
from hashlib import sha256
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

WINDOW_SECONDS = 60
HIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return { count, redis.call('TTL', KEYS[1]) }
"""


class RateLimiter:
    def __init__(self) -> None:
        self.redis = Redis.from_url(
            settings.redis_url, decode_responses=True,
            socket_connect_timeout=0.25, socket_timeout=0.25,
        )

    async def hit(self, key: str) -> tuple[int, int]:
        result: Any = await self.redis.eval(HIT_SCRIPT, 1, key, WINDOW_SECONDS)
        return int(result[0]), max(1, int(result[1]))

    async def close(self) -> None:
        await self.redis.aclose()


def policy(request: Request) -> tuple[str, int] | None:
    if request.method == "OPTIONS":
        return None
    path = request.url.path
    if path == f"{settings.api_v1_prefix}/auth/login" and request.method == "POST":
        return "login", 10
    if path == f"{settings.api_v1_prefix}/auth/register" and request.method == "POST":
        return "register", 10
    if path == f"{settings.api_v1_prefix}/appointments" and request.method == "POST":
        return "booking", 20
    if request.method == "GET" and (
        path.startswith(f"{settings.api_v1_prefix}/site/")
        or path in {f"{settings.api_v1_prefix}/treatments", f"{settings.api_v1_prefix}/packages"}
    ):
        return "public", 100
    return None


async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    selected = policy(request)
    if selected is None:
        return await call_next(request)

    category, maximum = selected
    # Do not trust user-supplied X-Forwarded-For without an explicitly trusted proxy.
    address = request.client.host if request.client else "unknown"
    digest = sha256(address.encode("utf-8")).hexdigest()[:24]
    try:
        count, retry_after = await request.app.state.rate_limiter.hit(f"rate:{category}:{digest}")
    except RedisError:
        # Local development/tests keep working without Redis; booking itself fails closed.
        return await call_next(request)
    if count > maximum:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again shortly."},
            headers={"Retry-After": str(retry_after)},
        )
    return await call_next(request)
