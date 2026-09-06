from fastapi import APIRouter

from app.api.routes import health, treatments
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(
    treatments.router,
    prefix=f"{settings.api_v1_prefix}/treatments",
    tags=["treatments"],
)

