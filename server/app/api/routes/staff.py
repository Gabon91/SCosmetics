import csv
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from app.api.dependencies.auth import DatabaseSession, require_roles
from app.api.routes.appointments import get_booking_lock_manager
from app.core.config import settings
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.beautician import Beautician
from app.models.order import Order
from app.models.package import UserPackage
from app.models.user import User, UserRole
from app.schemas.auth import CustomerAdminPatch, UserRead
from app.schemas.commerce import UserPackageRead
from app.schemas.appointment import (
    AppointmentCreate, AppointmentRead, AppointmentReschedule,
    AvailabilityResponse, AvailabilitySlotRead, StaffAppointmentCreate,
)
from app.schemas.staff import StaffAppointmentRead, StaffBeauticianRead, StaffDashboardRead
from app.services.appointment_lifecycle import (
    AppointmentNotFoundError,
    AppointmentPermissionError,
    AppointmentStateError,
    mark_no_show,
)
from app.services.availability import (
    AvailabilityService, BeauticianNotQualifiedError, TreatmentNotFoundError, as_utc,
)
from app.services.booking import (
    BookingNotFoundError, BookingService, PackageNotUsableError,
    RescheduleNotAllowedError, SlotUnavailableError,
)
from app.services.booking_lock import BookingLockBusyError, BookingLockManager, BookingLockUnavailableError
from app.services.waitlist import WaitlistConflictError, WaitlistNotFoundError, cancel_customer_appointment

router = APIRouter()
Staff = Annotated[User, Depends(require_roles(UserRole.BEAUTICIAN, UserRole.ADMIN))]
Admin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
BUSINESS_ZONE = ZoneInfo(settings.business_timezone)
BookingSession = Annotated[Session, Depends(get_db, use_cache=False)]
BookingLocks = Annotated[BookingLockManager, Depends(get_booking_lock_manager)]


def active_customer(session: DatabaseSession, customer_id: int) -> User:
    customer = session.scalar(select(User).where(User.id == customer_id, User.role == UserRole.CUSTOMER))
    if customer is None:
        raise HTTPException(404, "Customer not found")
    if not customer.active:
        raise HTTPException(409, "Customer account is inactive")
    return customer


def booking_error(error: Exception) -> HTTPException:
    if isinstance(error, (TreatmentNotFoundError, BeauticianNotQualifiedError, BookingNotFoundError)):
        return HTTPException(404, "Treatment, beautician or appointment not found")
    if isinstance(error, (SlotUnavailableError, PackageNotUsableError, RescheduleNotAllowedError, BookingLockBusyError)):
        return HTTPException(409, "Slot or appointment is unavailable")
    if isinstance(error, BookingLockUnavailableError):
        return HTTPException(503, "Booking is temporarily unavailable")
    raise error


@router.get("/booking-availability", response_model=AvailabilityResponse)
def staff_booking_availability(
    _: Admin, session: DatabaseSession,
    customer_id: Annotated[int, Query(gt=0)],
    treatment_id: Annotated[int, Query(gt=0)],
    appointment_date: Annotated[date, Query(alias="date")],
    appointment_id: Annotated[int | None, Query(gt=0)] = None,
) -> AvailabilityResponse:
    active_customer(session, customer_id)
    if appointment_id is not None:
        existing = session.get(Appointment, appointment_id)
        if existing is None or existing.customer_id != customer_id or existing.treatment_id != treatment_id:
            raise HTTPException(404, "Appointment not found for customer and treatment")
        if existing.status != AppointmentStatus.BOOKED or as_utc(existing.start_time) <= datetime.now(UTC):
            raise HTTPException(409, "Only future booked appointments may be moved")
    try:
        result = AvailabilityService(session).list_available_slots(
            treatment_id, appointment_date, customer_id=customer_id,
            exclude_appointment_id=appointment_id,
        )
    except (TreatmentNotFoundError, BeauticianNotQualifiedError) as error:
        raise booking_error(error) from None
    return AvailabilityResponse(
        date=result.appointment_date, treatment_id=result.treatment.id,
        treatment_name=result.treatment.name,
        duration_minutes=result.treatment.duration_minutes,
        slots=[AvailabilitySlotRead.model_validate(slot) for slot in result.slots],
    )


@router.post("/appointments", response_model=AppointmentRead, status_code=201)
def create_staff_appointment(
    data: StaffAppointmentCreate, _: Admin, session: BookingSession,
    lock_manager: BookingLocks,
) -> AppointmentRead:
    active_customer(session, data.customer_id)
    booking = AppointmentCreate.model_validate(data.model_dump(exclude={"customer_id"}))
    try:
        result = BookingService(session, lock_manager).create_appointment(data.customer_id, booking)
    except (TreatmentNotFoundError, BeauticianNotQualifiedError, SlotUnavailableError,
            PackageNotUsableError, BookingLockBusyError, BookingLockUnavailableError) as error:
        raise booking_error(error) from None
    return AppointmentRead.model_validate(result)


@router.patch("/appointments/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_staff_appointment(
    appointment_id: int, data: AppointmentReschedule, _: Admin,
    session: BookingSession, lock_manager: BookingLocks,
) -> AppointmentRead:
    try:
        result = BookingService(session, lock_manager).reschedule_appointment(appointment_id, data)
    except (TreatmentNotFoundError, BeauticianNotQualifiedError, BookingNotFoundError,
            SlotUnavailableError, PackageNotUsableError, RescheduleNotAllowedError,
            BookingLockBusyError, BookingLockUnavailableError) as error:
        raise booking_error(error) from None
    return AppointmentRead.model_validate(result)


@router.get("/customers", response_model=list[UserRead])
def list_customers(
    _: Admin, session: DatabaseSession,
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> list[User]:
    query = select(User).where(User.role == UserRole.CUSTOMER)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(User.first_name.like(term), User.last_name.like(term), User.email.like(term), User.phone.like(term)))
    return list(session.scalars(query.order_by(User.id.desc()).limit(100)).all())


@router.patch("/customers/{customer_id}", response_model=UserRead)
def update_customer(customer_id: int, data: CustomerAdminPatch, _: Admin, session: DatabaseSession) -> User:
    customer = session.scalar(select(User).where(User.id == customer_id, User.role == UserRole.CUSTOMER))
    if customer is None:
        raise HTTPException(404, "Customer not found")
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(customer, field, value.strip().lower() if field == "email" else value.strip() if isinstance(value, str) else value)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Email already registered") from None
    return customer


@router.get("/customers/{customer_id}/packages", response_model=list[UserPackageRead])
def list_customer_packages(customer_id: int, _: Admin, session: DatabaseSession) -> list[UserPackageRead]:
    active_customer(session, customer_id)
    owned = session.scalars(
        select(UserPackage).where(UserPackage.user_id == customer_id)
        .options(joinedload(UserPackage.package)).order_by(UserPackage.id.desc())
    ).all()
    today = datetime.now(BUSINESS_ZONE).date()
    return [UserPackageRead(
        id=item.id, package_id=item.package_id, package_name=item.package.name,
        total_sessions=item.total_sessions, used_sessions=item.used_sessions,
        remaining_sessions=item.remaining_sessions, expiration_date=item.expiration_date,
        status=item.status, expired=item.expiration_date < today,
    ) for item in owned]


@router.delete("/appointments/{appointment_id}", response_model=AppointmentRead)
def cancel_staff_appointment(appointment_id: int, _: Admin, session: DatabaseSession) -> AppointmentRead:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(404, "Appointment not found")
    try:
        cancelled = cancel_customer_appointment(session, appointment.customer_id, appointment_id)
    except WaitlistNotFoundError:
        raise HTTPException(404, "Appointment not found") from None
    except WaitlistConflictError as error:
        raise HTTPException(409, str(error)) from None
    return AppointmentRead.model_validate(cancelled)


def own_beautician_id(session: DatabaseSession, user: User) -> int | None:
    if user.role == UserRole.ADMIN:
        return None
    beautician_id = session.scalar(select(Beautician.id).where(Beautician.user_id == user.id))
    if beautician_id is None:
        raise HTTPException(403, "No beautician profile")
    return beautician_id


def staff_appointment(item: Appointment) -> StaffAppointmentRead:
    return StaffAppointmentRead(
        id=item.id,
        customer_id=item.customer_id,
        customer_name=f"{item.customer.first_name} {item.customer.last_name}",
        customer_phone=item.customer.phone,
        beautician_id=item.beautician_id,
        beautician_name=f"{item.beautician.user.first_name} {item.beautician.user.last_name}",
        treatment_id=item.treatment_id,
        treatment_name=item.treatment.name,
        start_time=as_utc(item.start_time),
        end_time=as_utc(item.end_time),
        status=item.status,
        uses_package=item.user_package_id is not None,
    )


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=BUSINESS_ZONE).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=BUSINESS_ZONE).astimezone(UTC)
    return start, end


def appointment_query(start: datetime, end: datetime):
    return (
        select(Appointment)
        .where(Appointment.start_time >= start, Appointment.start_time < end)
        .options(
            joinedload(Appointment.customer),
            joinedload(Appointment.treatment),
            joinedload(Appointment.beautician).joinedload(Beautician.user),
        )
        .order_by(Appointment.start_time, Appointment.id)
    )


@router.get("/appointments", response_model=list[StaffAppointmentRead])
def list_staff_appointments(
    staff: Staff,
    session: DatabaseSession,
    appointment_date: Annotated[date | None, Query(alias="date")] = None,
    beautician_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
) -> list[StaffAppointmentRead]:
    day = appointment_date or datetime.now(BUSINESS_ZONE).date()
    start, end = day_bounds(day)
    query = appointment_query(start, end)
    own_id = own_beautician_id(session, staff)
    if own_id is not None:
        query = query.where(Appointment.beautician_id == own_id)
    elif beautician_id is not None:
        query = query.where(Appointment.beautician_id == beautician_id)
    if status_filter is not None:
        query = query.where(Appointment.status == status_filter)
    return [staff_appointment(item) for item in session.scalars(query.limit(300)).all()]


@router.get("/dashboard", response_model=StaffDashboardRead)
def dashboard(staff: Staff, session: DatabaseSession) -> StaffDashboardRead:
    today = datetime.now(BUSINESS_ZONE).date()
    start, end = day_bounds(today)
    query = appointment_query(start, end)
    own_id = own_beautician_id(session, staff)
    if own_id is not None:
        query = query.where(Appointment.beautician_id == own_id)
    appointments = [staff_appointment(item) for item in session.scalars(query).all()]
    active_customers = demo_orders_month = None
    demo_sales_month = None
    if staff.role == UserRole.ADMIN:
        active_customers = session.scalar(
            select(func.count(User.id)).where(User.role == UserRole.CUSTOMER, User.active.is_(True))
        ) or 0
        month_start = datetime(today.year, today.month, 1, tzinfo=BUSINESS_ZONE).astimezone(UTC)
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = datetime(next_month.year, next_month.month, 1, tzinfo=BUSINESS_ZONE).astimezone(UTC)
        demo_orders_month, demo_sales_month = session.execute(
            select(func.count(Order.id), func.sum(Order.total)).where(
                Order.created_at >= month_start, Order.created_at < month_end
            )
        ).one()
        demo_sales_month = demo_sales_month or Decimal("0.00")
    return StaffDashboardRead(
        date=today.isoformat(),
        appointments_today=len(appointments),
        completed_today=sum(item.status == AppointmentStatus.COMPLETED for item in appointments),
        upcoming_today=sum(item.status == AppointmentStatus.BOOKED for item in appointments),
        active_customers=active_customers,
        demo_orders_month=demo_orders_month,
        demo_sales_month=demo_sales_month,
        appointments=appointments[:12],
    )


@router.get("/beauticians", response_model=list[StaffBeauticianRead])
def list_staff_beauticians(_: Staff, session: DatabaseSession) -> list[StaffBeauticianRead]:
    people = session.scalars(
        select(Beautician).join(Beautician.user).where(Beautician.active.is_(True))
        .options(joinedload(Beautician.user)).order_by(Beautician.id)
    ).all()
    return [StaffBeauticianRead(id=person.id, name=f"{person.user.first_name} {person.user.last_name}") for person in people]


@router.patch("/appointments/{appointment_id}/no-show", response_model=AppointmentRead)
def set_no_show(appointment_id: int, staff: Staff, session: DatabaseSession) -> AppointmentRead:
    try:
        return AppointmentRead.model_validate(mark_no_show(session, appointment_id, staff))
    except AppointmentNotFoundError:
        raise HTTPException(404, "Appointment not found") from None
    except AppointmentPermissionError:
        raise HTTPException(403, "This appointment is not assigned to you") from None
    except AppointmentStateError:
        raise HTTPException(409, "Appointment cannot be marked no-show") from None


@router.get("/reports/{kind}.csv")
def export_report(kind: Literal["appointments", "orders"], _: Admin, session: DatabaseSession) -> Response:
    output = StringIO()
    writer = csv.writer(output)
    if kind == "appointments":
        writer.writerow(["ID", "Customer", "Beautician", "Treatment", "Start UTC", "Status"])
        records = session.scalars(
            select(Appointment).options(
                joinedload(Appointment.customer),
                joinedload(Appointment.beautician).joinedload(Beautician.user),
                joinedload(Appointment.treatment),
            ).order_by(Appointment.id.desc()).limit(5000)
        ).all()
        for item in records:
            writer.writerow([item.id, f"{item.customer.first_name} {item.customer.last_name}",
                             f"{item.beautician.user.first_name} {item.beautician.user.last_name}",
                             item.treatment.name, as_utc(item.start_time).isoformat(), item.status.value])
    else:
        writer.writerow(["ID", "Customer ID", "Total ILS", "Status", "Created At"])
        for item in session.scalars(select(Order).order_by(Order.id.desc()).limit(5000)):
            writer.writerow([item.id, item.user_id, item.total, item.status.value, item.created_at.isoformat()])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="scosmetics-{kind}.csv"'},
    )
