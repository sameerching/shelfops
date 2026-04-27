"""add stockout_cases and case_updates tables

Revision ID: 20260427_0007
Revises: 20260427_0006
Create Date: 2026-04-27 09:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_0007"
down_revision: str | None = "20260427_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stockout_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_oos_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stockout_duration_hours", sa.Numeric(precision=12, scale=4), server_default="0", nullable=False),
        sa.Column("estimated_lost_sales", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("estimated_lost_margin", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stockout_cases_id"), "stockout_cases", ["id"], unique=False)
    op.create_index(op.f("ix_stockout_cases_brand_id"), "stockout_cases", ["brand_id"], unique=False)
    op.create_index(op.f("ix_stockout_cases_sku_id"), "stockout_cases", ["sku_id"], unique=False)
    op.create_index(op.f("ix_stockout_cases_location_id"), "stockout_cases", ["location_id"], unique=False)
    op.create_index(op.f("ix_stockout_cases_detected_at"), "stockout_cases", ["detected_at"], unique=False)
    op.create_index(op.f("ix_stockout_cases_last_seen_oos_at"), "stockout_cases", ["last_seen_oos_at"], unique=False)
    op.create_index(op.f("ix_stockout_cases_recovered_at"), "stockout_cases", ["recovered_at"], unique=False)
    op.create_index(op.f("ix_stockout_cases_priority"), "stockout_cases", ["priority"], unique=False)
    op.create_index(op.f("ix_stockout_cases_status"), "stockout_cases", ["status"], unique=False)

    op.create_table(
        "case_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("update_text", sa.Text(), nullable=False),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["stockout_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_case_updates_id"), "case_updates", ["id"], unique=False)
    op.create_index(op.f("ix_case_updates_case_id"), "case_updates", ["case_id"], unique=False)
    op.create_index(op.f("ix_case_updates_created_at"), "case_updates", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_case_updates_created_at"), table_name="case_updates")
    op.drop_index(op.f("ix_case_updates_case_id"), table_name="case_updates")
    op.drop_index(op.f("ix_case_updates_id"), table_name="case_updates")
    op.drop_table("case_updates")

    op.drop_index(op.f("ix_stockout_cases_status"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_priority"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_recovered_at"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_last_seen_oos_at"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_detected_at"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_location_id"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_sku_id"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_brand_id"), table_name="stockout_cases")
    op.drop_index(op.f("ix_stockout_cases_id"), table_name="stockout_cases")
    op.drop_table("stockout_cases")
