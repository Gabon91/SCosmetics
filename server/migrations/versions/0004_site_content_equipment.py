"""Add editable site content and equipment catalog."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_site_content_equipment"
down_revision: str | Sequence[str] | None = "0003_packages_waitlist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_content",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("manufacturer", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "equipment_treatments",
        sa.Column("equipment_id", sa.Integer(), sa.ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("treatment_id", sa.Integer(), sa.ForeignKey("treatments.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("equipment_treatments")
    op.drop_table("equipment")
    op.drop_table("site_content")
