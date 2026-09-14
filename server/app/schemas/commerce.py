from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.models.package import UserPackageStatus


class PackageRead(BaseModel):
    id: int
    name: str
    price: Decimal
    sessions: int
    validity_days: int
    treatment_ids: list[int]


class DemoPurchaseRequest(BaseModel):
    package_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=5)


class DemoPurchaseRead(BaseModel):
    order_id: int
    total: Decimal
    status: OrderStatus
    user_package_ids: list[int]
    note: str = "Demo only — no payment was charged"


class UserPackageRead(BaseModel):
    id: int
    package_id: int
    package_name: str
    total_sessions: int
    used_sessions: int
    remaining_sessions: int
    expiration_date: date
    status: UserPackageStatus
    expired: bool


class OrderItemRead(BaseModel):
    package_id: int
    package_name: str
    quantity: int
    unit_price: Decimal


class OrderRead(BaseModel):
    id: int
    total: Decimal
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemRead]
