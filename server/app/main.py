from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.seed import seed_treatments
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as session:
        seed_treatments(session)
    yield


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="REST API for the SCosmetics beauty clinic platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
