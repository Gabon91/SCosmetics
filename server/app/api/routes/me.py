from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.api.dependencies.auth import DatabaseSession, require_roles
from app.core.config import settings
from app.models.appointment import Appointment
from app.models.order import Order, OrderItem
from app.models.package import UserPackage
from app.models.user import User, UserRole
from app.schemas.auth import CustomerProfilePatch, UserRead
from app.models.waitlist import WaitlistEntry
from app.schemas.appointment import AppointmentRead
from app.schemas.commerce import OrderItemRead, OrderRead, UserPackageRead
from app.schemas.waitlist import WaitlistRead, waitlist_read

router = APIRouter()
Customer = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]


@router.patch("/profile", response_model=UserRead)
def update_my_profile(data: CustomerProfilePatch, customer: Customer, session: DatabaseSession) -> User:
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(customer, field, value.strip().lower() if field == "email" else value.strip())
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Email already registered") from None
    return customer


@router.get("/appointments", response_model=list[AppointmentRead])
def my_appointments(customer: Customer, session: DatabaseSession) -> list[Appointment]:
    return list(
        session.scalars(
            select(Appointment)
            .where(Appointment.customer_id == customer.id)
            .order_by(Appointment.start_time.desc())
        ).all()
    )


@router.get("/packages", response_model=list[UserPackageRead])
def my_packages(customer: Customer, session: DatabaseSession) -> list[UserPackageRead]:
    packages = session.scalars(
        select(UserPackage)
        .where(UserPackage.user_id == customer.id)
        .options(joinedload(UserPackage.package))
        .order_by(UserPackage.id.desc())
    ).all()
    today = datetime.now(ZoneInfo(settings.business_timezone)).date()
    return [
        UserPackageRead(
            id=item.id,
            package_id=item.package_id,
            package_name=item.package.name,
            total_sessions=item.total_sessions,
            used_sessions=item.used_sessions,
            remaining_sessions=item.remaining_sessions,
            expiration_date=item.expiration_date,
            status=item.status,
            expired=item.expiration_date < today,
        )
        for item in packages
    ]


@router.get("/orders", response_model=list[OrderRead])
def my_orders(customer: Customer, session: DatabaseSession) -> list[OrderRead]:
    orders = session.scalars(
        select(Order)
        .where(Order.user_id == customer.id)
        .options(selectinload(Order.items).joinedload(OrderItem.package))
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()
    return [
        OrderRead(
            id=order.id,
            total=order.total,
            status=order.status,
            created_at=order.created_at,
            items=[
                OrderItemRead(
                    package_id=item.package_id,
                    package_name=item.package.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                for item in order.items
            ],
        )
        for order in orders
    ]


@router.get("/waitlist", response_model=list[WaitlistRead])
def my_waitlist(customer: Customer, session: DatabaseSession) -> list[WaitlistRead]:
    entries = session.scalars(
        select(WaitlistEntry)
        .where(WaitlistEntry.user_id == customer.id)
        .order_by(WaitlistEntry.created_at.desc(), WaitlistEntry.id.desc())
    ).all()
    return [waitlist_read(entry) for entry in entries]
