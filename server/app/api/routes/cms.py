from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import DatabaseSession, require_roles
from app.models.package import Package
from app.models.beautician import Beautician, BeauticianWorkingHours
from app.models.site import Equipment, SiteContent, TeamMember
from app.models.treatment import Treatment
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.schemas.beautician_admin import BeauticianAdminRead, BeauticianInput, BeauticianPatch, WorkingHoursInput
from app.schemas.cms import (
    PackageAdminRead, PackageInput, PackagePatch,
    TreatmentAdminRead, TreatmentInput, TreatmentPatch,
)
from app.services.catalog import CatalogService
from app.schemas.site import (
    ContentUpdate, EquipmentInput, EquipmentPatch, EquipmentRead,
    TeamMemberInput, TeamMemberPatch, TeamMemberRead,
)
from app.api.routes.site import equipment_read
from app.db.seed import DEFAULT_SITE_CONTENT

router = APIRouter()
Admin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def treatment_read(item: Treatment) -> TreatmentAdminRead:
    return TreatmentAdminRead(
        id=item.id, name=item.name, category=item.category,
        description=item.description, duration_minutes=item.duration_minutes,
        price=item.price, accent=item.accent, active=item.active,
    )


def package_read(item: Package) -> PackageAdminRead:
    return PackageAdminRead(
        id=item.id, name=item.name, price=item.price, sessions=item.sessions,
        validity_days=item.validity_days,
        treatment_ids=[treatment.id for treatment in item.treatments], active=item.active,
    )


def apply_fields(item: Treatment | Package | Equipment | TeamMember, data: BaseModel, skip: set[str] = frozenset()) -> None:
    for key, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        if key not in skip:
            setattr(item, key, value)


@router.get("/treatments", response_model=list[TreatmentAdminRead])
def all_treatments(_: Admin, session: DatabaseSession) -> list[TreatmentAdminRead]:
    return [treatment_read(item) for item in session.scalars(select(Treatment).order_by(Treatment.id))]


@router.post("/treatments", response_model=TreatmentAdminRead, status_code=status.HTTP_201_CREATED)
def create_treatment(data: TreatmentInput, _: Admin, session: DatabaseSession) -> TreatmentAdminRead:
    item = Treatment(**data.model_dump())
    session.add(item)
    session.commit()
    CatalogService(session).invalidate()
    return treatment_read(item)


@router.patch("/treatments/{treatment_id}", response_model=TreatmentAdminRead)
def update_treatment(treatment_id: int, data: TreatmentPatch, _: Admin, session: DatabaseSession) -> TreatmentAdminRead:
    item = session.get(Treatment, treatment_id)
    if item is None:
        raise HTTPException(404, "Treatment not found")
    apply_fields(item, data)
    session.commit()
    CatalogService(session).invalidate()
    return treatment_read(item)


@router.delete("/treatments/{treatment_id}", response_model=TreatmentAdminRead)
def archive_treatment(treatment_id: int, _: Admin, session: DatabaseSession) -> TreatmentAdminRead:
    item = session.get(Treatment, treatment_id)
    if item is None:
        raise HTTPException(404, "Treatment not found")
    item.active = False
    session.commit()
    CatalogService(session).invalidate()
    return treatment_read(item)


def resolve_treatments(session: DatabaseSession, ids: list[int]) -> list[Treatment]:
    unique_ids = set(ids)
    treatments = list(session.scalars(
        select(Treatment).where(Treatment.id.in_(unique_ids), Treatment.active.is_(True))
    ))
    if len(treatments) != len(unique_ids):
        raise HTTPException(422, "Every package treatment must be active and exist")
    return treatments


@router.get("/packages", response_model=list[PackageAdminRead])
def all_packages(_: Admin, session: DatabaseSession) -> list[PackageAdminRead]:
    items = session.scalars(
        select(Package).options(selectinload(Package.treatments)).order_by(Package.id)
    ).all()
    return [package_read(item) for item in items]


@router.post("/packages", response_model=PackageAdminRead, status_code=status.HTTP_201_CREATED)
def create_package(data: PackageInput, _: Admin, session: DatabaseSession) -> PackageAdminRead:
    treatments = resolve_treatments(session, data.treatment_ids)
    item = Package(**data.model_dump(exclude={"treatment_ids"}), treatments=treatments)
    session.add(item)
    session.commit()
    return package_read(item)


@router.patch("/packages/{package_id}", response_model=PackageAdminRead)
def update_package(package_id: int, data: PackagePatch, _: Admin, session: DatabaseSession) -> PackageAdminRead:
    item = session.scalar(select(Package).where(Package.id == package_id).options(selectinload(Package.treatments)))
    if item is None:
        raise HTTPException(404, "Package not found")
    if data.treatment_ids is not None:
        item.treatments = resolve_treatments(session, data.treatment_ids)
    apply_fields(item, data, {"treatment_ids"})
    session.commit()
    return package_read(item)


@router.delete("/packages/{package_id}", response_model=PackageAdminRead)
def archive_package(package_id: int, _: Admin, session: DatabaseSession) -> PackageAdminRead:
    item = session.scalar(select(Package).where(Package.id == package_id).options(selectinload(Package.treatments)))
    if item is None:
        raise HTTPException(404, "Package not found")
    item.active = False
    session.commit()
    return package_read(item)


@router.get("/content", response_model=dict[str, str])
def all_content(_: Admin, session: DatabaseSession) -> dict[str, str]:
    return {item.key: item.value for item in session.scalars(select(SiteContent))}


@router.patch("/content", response_model=dict[str, str])
def update_content(data: ContentUpdate, _: Admin, session: DatabaseSession) -> dict[str, str]:
    if not data.values.keys() <= DEFAULT_SITE_CONTENT.keys():
        raise HTTPException(422, "Unknown site content key")
    if any(len(value) > 4000 for value in data.values.values()):
        raise HTTPException(422, "Site content value is too long")
    for key, value in data.values.items():
        item = session.get(SiteContent, key)
        if item is None:
            session.add(SiteContent(key=key, value=value))
        else:
            item.value = value
    session.commit()
    return all_content(_, session)


@router.get("/equipment", response_model=list[EquipmentRead])
def all_equipment(_: Admin, session: DatabaseSession) -> list[EquipmentRead]:
    items = session.scalars(
        select(Equipment).options(selectinload(Equipment.treatments)).order_by(Equipment.id)
    ).all()
    return [equipment_read(item) for item in items]


@router.post("/equipment", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def create_equipment(data: EquipmentInput, _: Admin, session: DatabaseSession) -> EquipmentRead:
    treatments = resolve_treatments(session, data.treatment_ids)
    item = Equipment(**data.model_dump(exclude={"treatment_ids"}), treatments=treatments)
    session.add(item)
    session.commit()
    return equipment_read(item)


@router.patch("/equipment/{equipment_id}", response_model=EquipmentRead)
def update_equipment(equipment_id: int, data: EquipmentPatch, _: Admin, session: DatabaseSession) -> EquipmentRead:
    item = session.scalar(select(Equipment).where(Equipment.id == equipment_id).options(selectinload(Equipment.treatments)))
    if item is None:
        raise HTTPException(404, "Equipment not found")
    if data.treatment_ids is not None:
        item.treatments = resolve_treatments(session, data.treatment_ids)
    apply_fields(item, data, {"treatment_ids"})
    session.commit()
    return equipment_read(item)


@router.delete("/equipment/{equipment_id}", response_model=EquipmentRead)
def archive_equipment(equipment_id: int, _: Admin, session: DatabaseSession) -> EquipmentRead:
    item = session.scalar(select(Equipment).where(Equipment.id == equipment_id).options(selectinload(Equipment.treatments)))
    if item is None:
        raise HTTPException(404, "Equipment not found")
    item.active = False
    session.commit()
    return equipment_read(item)


@router.get("/team", response_model=list[TeamMemberRead])
def all_team(_: Admin, session: DatabaseSession) -> list[TeamMemberRead]:
    people = session.scalars(select(TeamMember).order_by(TeamMember.display_order, TeamMember.id)).all()
    return [TeamMemberRead.model_validate(person) for person in people]


@router.post("/team", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
def create_team_member(data: TeamMemberInput, _: Admin, session: DatabaseSession) -> TeamMemberRead:
    if data.featured:
        session.execute(update(TeamMember).values(featured=False))
    item = TeamMember(**data.model_dump())
    session.add(item)
    session.commit()
    return TeamMemberRead.model_validate(item)


@router.patch("/team/{member_id}", response_model=TeamMemberRead)
def update_team_member(member_id: int, data: TeamMemberPatch, _: Admin, session: DatabaseSession) -> TeamMemberRead:
    item = session.get(TeamMember, member_id)
    if item is None:
        raise HTTPException(404, "Team member not found")
    if data.featured:
        session.execute(update(TeamMember).values(featured=False))
    apply_fields(item, data)
    session.commit()
    return TeamMemberRead.model_validate(item)


@router.delete("/team/{member_id}", response_model=TeamMemberRead)
def archive_team_member(member_id: int, _: Admin, session: DatabaseSession) -> TeamMemberRead:
    item = session.get(TeamMember, member_id)
    if item is None:
        raise HTTPException(404, "Team member not found")
    item.active = False
    session.commit()
    return TeamMemberRead.model_validate(item)


def validate_shifts(shifts: list[WorkingHoursInput]) -> None:
    by_day: dict[int, list[WorkingHoursInput]] = {}
    for shift in shifts:
        by_day.setdefault(shift.weekday, []).append(shift)
    for daily in by_day.values():
        ordered = sorted(daily, key=lambda shift: shift.start_time)
        if any(first.end_time > second.start_time for first, second in zip(ordered, ordered[1:])):
            raise HTTPException(422, "Working-hour shifts must not overlap")


def read_beautician(item: Beautician) -> BeauticianAdminRead:
    return BeauticianAdminRead(
        id=item.id, user_id=item.user_id,
        first_name=item.user.first_name, last_name=item.user.last_name,
        email=item.user.email, phone=item.user.phone, bio=item.bio,
        treatment_ids=[treatment.id for treatment in item.treatments],
        working_hours=[WorkingHoursInput(
            weekday=shift.weekday, start_time=shift.start_time, end_time=shift.end_time,
        ) for shift in sorted(item.working_hours, key=lambda shift: (shift.weekday, shift.start_time)) if shift.active],
        active=item.active and item.user.active,
    )


def beautician_query():
    return select(Beautician).options(
        selectinload(Beautician.user),
        selectinload(Beautician.treatments),
        selectinload(Beautician.working_hours),
    )


@router.get("/beauticians", response_model=list[BeauticianAdminRead])
def all_beauticians(_: Admin, session: DatabaseSession) -> list[BeauticianAdminRead]:
    return [read_beautician(item) for item in session.scalars(beautician_query().order_by(Beautician.id))]


@router.post("/beauticians", response_model=BeauticianAdminRead, status_code=status.HTTP_201_CREATED)
def create_beautician(data: BeauticianInput, _: Admin, session: DatabaseSession) -> BeauticianAdminRead:
    validate_shifts(data.working_hours)
    email = data.email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "Invalid email")
    if session.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(409, "Email already registered")
    user = User(
        first_name=data.first_name.strip(), last_name=data.last_name.strip(),
        email=email, phone=data.phone.strip(),
        password_hash=hash_password(data.password), role=UserRole.BEAUTICIAN,
        active=data.active,
    )
    item = Beautician(
        user=user, bio=data.bio, active=data.active,
        treatments=resolve_treatments(session, data.treatment_ids),
        working_hours=[BeauticianWorkingHours(**shift.model_dump()) for shift in data.working_hours],
    )
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Email or working hours already exist") from None
    return read_beautician(item)


@router.patch("/beauticians/{beautician_id}", response_model=BeauticianAdminRead)
def update_beautician(beautician_id: int, data: BeauticianPatch, _: Admin, session: DatabaseSession) -> BeauticianAdminRead:
    item = session.scalar(beautician_query().where(Beautician.id == beautician_id))
    if item is None:
        raise HTTPException(404, "Beautician not found")
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    for field in ("first_name", "last_name", "phone"):
        if field in values:
            setattr(item.user, field, values[field].strip())
    if "email" in values:
        email = values["email"].strip().lower()
        if "@" not in email:
            raise HTTPException(422, "Invalid email")
        if session.scalar(select(User.id).where(User.email == email, User.id != item.user_id)) is not None:
            raise HTTPException(409, "Email already registered")
        item.user.email = email
    if "bio" in values:
        item.bio = data.bio or ""
    if data.treatment_ids is not None:
        item.treatments = resolve_treatments(session, data.treatment_ids)
    if data.working_hours is not None:
        validate_shifts(data.working_hours)
        item.working_hours.clear()
        session.flush()
        item.working_hours = [BeauticianWorkingHours(**shift.model_dump()) for shift in data.working_hours]
    if data.active is not None:
        item.active = item.user.active = data.active
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Email or working hours already exist") from None
    return read_beautician(item)


@router.delete("/beauticians/{beautician_id}", response_model=BeauticianAdminRead)
def archive_beautician(beautician_id: int, _: Admin, session: DatabaseSession) -> BeauticianAdminRead:
    item = session.scalar(beautician_query().where(Beautician.id == beautician_id))
    if item is None:
        raise HTTPException(404, "Beautician not found")
    item.active = item.user.active = False
    session.commit()
    return read_beautician(item)
