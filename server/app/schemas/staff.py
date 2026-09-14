from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.appointment import AppointmentStatus


class StaffAppointmentRead(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    customer_phone: str
    beautician_id: int
    beautician_name: str
    treatment_id: int
    treatment_name: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    uses_package: bool


class StaffDashboardRead(BaseModel):
    date: str
    appointments_today: int
    completed_today: int
    upcoming_today: int
    active_customers: int | None
    demo_orders_month: int | None
    demo_sales_month: Decimal | None
    appointments: list[StaffAppointmentRead]


class StaffBeauticianRead(BaseModel):
    id: int
    name: str
