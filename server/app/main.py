from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.rate_limit import RateLimiter, rate_limit_middleware
from app.db.seed import seed_booking_demo, seed_equipment, seed_packages, seed_site_content, seed_team, seed_treatments
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    limiter = RateLimiter()
    app.state.rate_limiter = limiter
    with SessionLocal() as session:
        seed_treatments(session)
        if settings.environment == "development":
            seed_booking_demo(session)
            seed_packages(session)
            seed_site_content(session)
            seed_equipment(session)
            seed_team(session)
    try:
        yield
    finally:
        await limiter.close()


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="REST API for the SCosmetics beauty clinic platform.",
    lifespan=lifespan,
)

app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
