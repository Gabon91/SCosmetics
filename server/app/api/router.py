from fastapi import APIRouter

from app.api.routes import appointments, auth, health, me, orders, packages, treatments, waitlist
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(
    auth.router,
    prefix=f"{settings.api_v1_prefix}/auth",
    tags=["auth"],
)
api_router.include_router(
    treatments.router,
    prefix=f"{settings.api_v1_prefix}/treatments",
    tags=["treatments"],
)
api_router.include_router(
    appointments.router,
    prefix=f"{settings.api_v1_prefix}/appointments",
    tags=["appointments"],
)
api_router.include_router(
    packages.router,
    prefix=f"{settings.api_v1_prefix}/packages",
    tags=["packages"],
)
api_router.include_router(
    orders.router,
    prefix=f"{settings.api_v1_prefix}/orders",
    tags=["orders"],
)
api_router.include_router(
    me.router,
    prefix=f"{settings.api_v1_prefix}/me",
    tags=["me"],
)
api_router.include_router(
    waitlist.router,
    prefix=f"{settings.api_v1_prefix}/waitlist",
    tags=["waitlist"],
)
