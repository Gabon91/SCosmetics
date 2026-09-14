from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order, OrderItem
from app.models.package import Package, UserPackage


class PackageNotAvailableError(Exception):
    pass


def create_demo_purchase(
    session: Session, customer_id: int, package_id: int, quantity: int
) -> tuple[Order, list[UserPackage]]:
    """Record a demo order and grant packages without processing a payment."""
    try:
        package = session.scalar(
            select(Package)
            .where(Package.id == package_id, Package.active.is_(True))
            .with_for_update()
        )
        if package is None:
            raise PackageNotAvailableError

        today = datetime.now(ZoneInfo(settings.business_timezone)).date()
        order = Order(
            user_id=customer_id,
            total=package.price * quantity,
            items=[
                OrderItem(
                    package_id=package.id,
                    quantity=quantity,
                    unit_price=package.price,
                )
            ],
        )
        user_packages = [
            UserPackage(
                user_id=customer_id,
                package_id=package.id,
                total_sessions=package.sessions,
                used_sessions=0,
                remaining_sessions=package.sessions,
                expiration_date=today + timedelta(days=package.validity_days),
            )
            for _ in range(quantity)
        ]
        session.add(order)
        session.add_all(user_packages)
        session.commit()
        return order, user_packages
    except Exception:
        session.rollback()
        raise
