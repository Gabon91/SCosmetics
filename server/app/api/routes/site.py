from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import DatabaseSession
from app.models.site import Equipment, SiteContent, TeamMember
from app.schemas.site import EquipmentRead, TeamMemberRead

router = APIRouter()


def equipment_read(item: Equipment) -> EquipmentRead:
    return EquipmentRead(
        id=item.id, name=item.name, manufacturer=item.manufacturer,
        description=item.description, image_url=item.image_url,
        treatment_ids=[treatment.id for treatment in item.treatments], active=item.active,
    )


@router.get("/content", response_model=dict[str, str])
def public_content(session: DatabaseSession) -> dict[str, str]:
    return {item.key: item.value for item in session.scalars(select(SiteContent))}


@router.get("/equipment", response_model=list[EquipmentRead])
def public_equipment(session: DatabaseSession) -> list[EquipmentRead]:
    items = session.scalars(
        select(Equipment).where(Equipment.active.is_(True))
        .options(selectinload(Equipment.treatments)).order_by(Equipment.id)
    ).all()
    return [equipment_read(item) for item in items]


@router.get("/team", response_model=list[TeamMemberRead])
def public_team(session: DatabaseSession) -> list[TeamMemberRead]:
    people = session.scalars(
        select(TeamMember).where(TeamMember.active.is_(True))
        .order_by(TeamMember.display_order, TeamMember.id)
    ).all()
    return [TeamMemberRead.model_validate(person) for person in people]
