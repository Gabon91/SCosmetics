"""Add demo orders, treatment packages, and waitlist offers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_packages_waitlist"
down_revision: str | Sequence[str] | None = "0002_booking_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("sessions", sa.Integer(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint("sessions > 0", name="ck_packages_sessions_positive"),
        sa.CheckConstraint("validity_days > 0", name="ck_packages_validity_positive"),
    )
    op.create_table(
        "package_treatments",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("treatment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["treatment_id"], ["treatments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("package_id", "treatment_id"),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("demo_confirmed", native_enum=False),
            server_default="demo_confirmed",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("package_id", sa.Integer(), sa.ForeignKey("packages.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_table(
        "user_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("package_id", sa.Integer(), sa.ForeignKey("packages.id"), nullable=False),
        sa.Column("total_sessions", sa.Integer(), nullable=False),
        sa.Column("used_sessions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("remaining_sessions", sa.Integer(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "exhausted", native_enum=False),
            server_default="active",
            nullable=False,
        ),
        sa.CheckConstraint(
            "total_sessions > 0 AND used_sessions >= 0 AND remaining_sessions >= 0",
            name="ck_user_packages_nonnegative_balance",
        ),
        sa.CheckConstraint(
            "used_sessions + remaining_sessions = total_sessions",
            name="ck_user_packages_balance_matches_total",
        ),
    )
    op.create_index("ix_user_packages_user_id", "user_packages", ["user_id"])
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.add_column(sa.Column("user_package_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_appointments_user_package", "user_packages", ["user_package_id"], ["id"]
        )
        batch_op.create_index("ix_appointments_user_package_id", ["user_package_id"])
    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("treatment_id", sa.Integer(), sa.ForeignKey("treatments.id"), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("beautician_id", sa.Integer(), sa.ForeignKey("beauticians.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("waiting", "offered", "fulfilled", "cancelled", native_enum=False),
            server_default="waiting",
            nullable=False,
        ),
        sa.Column("offered_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offered_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offer_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_waitlist_user_id", "waitlist", ["user_id"])
    op.create_index("ix_waitlist_treatment_id", "waitlist", ["treatment_id"])
    op.create_index("ix_waitlist_preferred_date", "waitlist", ["preferred_date"])


def downgrade() -> None:
    op.drop_index("ix_waitlist_preferred_date", table_name="waitlist")
    op.drop_index("ix_waitlist_treatment_id", table_name="waitlist")
    op.drop_index("ix_waitlist_user_id", table_name="waitlist")
    op.drop_table("waitlist")
    with op.batch_alter_table("appointments") as batch_op:
        batch_op.drop_index("ix_appointments_user_package_id")
        batch_op.drop_constraint("fk_appointments_user_package", type_="foreignkey")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("user_package_id")
    op.drop_index("ix_user_packages_user_id", table_name="user_packages")
    op.drop_table("user_packages")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("package_treatments")
    op.drop_table("packages")
