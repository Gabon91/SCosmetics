"""Add beauticians, working hours, certifications, and appointments."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_booking_foundation"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    treatment_constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(
            "treatments"
        )
    }
    if "ck_treatments_duration_15_minute_increment" not in treatment_constraints:
        with op.batch_alter_table("treatments") as batch_op:
            batch_op.create_check_constraint(
                "ck_treatments_duration_15_minute_increment",
                "duration_minutes > 0 AND duration_minutes % 15 = 0",
            )

    op.create_table(
        "beauticians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "bio",
            sa.Text(),
            server_default=sa.text("('')"),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_beauticians_active", "beauticians", ["active"])
    op.create_index(
        "ix_beauticians_user_id",
        "beauticians",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "beautician_treatments",
        sa.Column("beautician_id", sa.Integer(), nullable=False),
        sa.Column("treatment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["beautician_id"],
            ["beauticians.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["treatment_id"],
            ["treatments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("beautician_id", "treatment_id"),
    )

    op.create_table(
        "beautician_working_hours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("beautician_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "start_time < end_time",
            name="ck_beautician_working_hours_time_range",
        ),
        sa.CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_beautician_working_hours_weekday",
        ),
        sa.ForeignKeyConstraint(
            ["beautician_id"],
            ["beauticians.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "beautician_id",
            "weekday",
            "start_time",
            "end_time",
            name="uq_beautician_working_hours_shift",
        ),
    )
    op.create_index(
        "ix_beautician_working_hours_beautician_id",
        "beautician_working_hours",
        ["beautician_id"],
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("beautician_id", sa.Integer(), nullable=False),
        sa.Column("treatment_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "booked",
                "completed",
                "cancelled",
                "no_show",
                name="appointment_status",
                native_enum=False,
            ),
            server_default="booked",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_time > start_time",
            name="ck_appointments_time_range",
        ),
        sa.ForeignKeyConstraint(["beautician_id"], ["beauticians.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["treatment_id"], ["treatments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointments_beautician_start",
        "appointments",
        ["beautician_id", "start_time"],
    )
    op.create_index(
        "ix_appointments_customer_id",
        "appointments",
        ["customer_id"],
    )
    op.create_index(
        "ix_appointments_start_status",
        "appointments",
        ["start_time", "status"],
    )
    op.create_index(
        "ix_appointments_treatment_start",
        "appointments",
        ["treatment_id", "start_time"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_appointments_treatment_start",
        table_name="appointments",
    )
    op.drop_index(
        "ix_appointments_start_status",
        table_name="appointments",
    )
    op.drop_index("ix_appointments_customer_id", table_name="appointments")
    op.drop_index(
        "ix_appointments_beautician_start",
        table_name="appointments",
    )
    op.drop_table("appointments")

    op.drop_index(
        "ix_beautician_working_hours_beautician_id",
        table_name="beautician_working_hours",
    )
    op.drop_table("beautician_working_hours")
    op.drop_table("beautician_treatments")

    op.drop_index("ix_beauticians_user_id", table_name="beauticians")
    op.drop_index("ix_beauticians_active", table_name="beauticians")
    op.drop_table("beauticians")

    treatment_constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(
            "treatments"
        )
    }
    if "ck_treatments_duration_15_minute_increment" in treatment_constraints:
        with op.batch_alter_table("treatments") as batch_op:
            batch_op.drop_constraint(
                "ck_treatments_duration_15_minute_increment",
                type_="check",
            )
