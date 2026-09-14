from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import DatabaseSession, require_roles
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.commerce import DemoPurchaseRead, DemoPurchaseRequest
from app.services.commerce import PackageNotAvailableError, create_demo_purchase

router = APIRouter()
Customer = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]


@router.post("", response_model=DemoPurchaseRead, status_code=status.HTTP_201_CREATED)
def demo_purchase(
    data: DemoPurchaseRequest, customer: Customer, session: DatabaseSession
) -> DemoPurchaseRead:
    if settings.environment != "development":
        raise HTTPException(503, "Demo checkout is disabled outside development")
    try:
        order, user_packages = create_demo_purchase(
            session, customer.id, data.package_id, data.quantity
        )
    except PackageNotAvailableError:
        raise HTTPException(404, "Package not found or inactive") from None
    return DemoPurchaseRead(
        order_id=order.id,
        total=order.total,
        status=order.status,
        user_package_ids=[package.id for package in user_packages],
    )
