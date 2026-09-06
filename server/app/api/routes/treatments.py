from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.treatment import TreatmentRead
from app.services.catalog import CatalogService

router = APIRouter()


@router.get("", response_model=list[TreatmentRead], summary="List active treatments")
def list_treatments(
    response: Response,
    session: Session = Depends(get_db),
) -> list[TreatmentRead]:
    treatments, cache_status = CatalogService(session).list_active_treatments()
    response.headers["X-Cache"] = cache_status
    return treatments

