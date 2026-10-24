from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import DatabaseSession
from app.models.package import Package
from app.schemas.commerce import PackageRead

router = APIRouter()


@router.get("", response_model=list[PackageRead])
def list_packages(session: DatabaseSession) -> list[PackageRead]:
    packages = session.scalars(
        select(Package)
        .where(Package.active.is_(True))
        .options(selectinload(Package.treatments))
        .order_by(Package.id)
    ).all()
    return [
        PackageRead(
            id=package.id,
            name=package.name,
            price=package.price,
            sessions=package.sessions,
            validity_days=package.validity_days,
            treatment_ids=[treatment.id for treatment in package.treatments],
        )
        for package in packages
    ]
