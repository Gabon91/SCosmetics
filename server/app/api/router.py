from fastapi import APIRouter

from app.api.routes import auth, health, treatments
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
