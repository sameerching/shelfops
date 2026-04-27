"""add sales velocity table

Revision ID: 20260427_0004
Revises: 20260427_0003
Create Date: 2026-04-27 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_0004"
down_revision: str | None = "20260427_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_velocity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("avg_units_per_day", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "brand_id",
            "sku_id",
            "platform",
            "city",
            name="uq_sales_velocity_brand_sku_platform_city",
        ),
    )
    op.create_index(op.f("ix_sales_velocity_id"), "sales_velocity", ["id"], unique=False)
    op.create_index(op.f("ix_sales_velocity_brand_id"), "sales_velocity", ["brand_id"], unique=False)
    op.create_index(op.f("ix_sales_velocity_sku_id"), "sales_velocity", ["sku_id"], unique=False)
    op.create_index(op.f("ix_sales_velocity_import_batch_id"), "sales_velocity", ["import_batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_velocity_import_batch_id"), table_name="sales_velocity")
    op.drop_index(op.f("ix_sales_velocity_sku_id"), table_name="sales_velocity")
    op.drop_index(op.f("ix_sales_velocity_brand_id"), table_name="sales_velocity")
    op.drop_index(op.f("ix_sales_velocity_id"), table_name="sales_velocity")
    op.drop_table("sales_velocity")
