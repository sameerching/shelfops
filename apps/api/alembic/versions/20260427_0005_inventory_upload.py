"""add inventory positions table

Revision ID: 20260427_0005
Revises: 20260427_0004
Create Date: 2026-04-27 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_0005"
down_revision: str | None = "20260427_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("warehouse", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("available_qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
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
            "warehouse",
            "city",
            "timestamp",
            name="uq_inventory_position_dedupe",
        ),
    )
    op.create_index(op.f("ix_inventory_positions_id"), "inventory_positions", ["id"], unique=False)
    op.create_index(op.f("ix_inventory_positions_brand_id"), "inventory_positions", ["brand_id"], unique=False)
    op.create_index(op.f("ix_inventory_positions_sku_id"), "inventory_positions", ["sku_id"], unique=False)
    op.create_index(op.f("ix_inventory_positions_timestamp"), "inventory_positions", ["timestamp"], unique=False)
    op.create_index(
        op.f("ix_inventory_positions_import_batch_id"),
        "inventory_positions",
        ["import_batch_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_positions_import_batch_id"), table_name="inventory_positions")
    op.drop_index(op.f("ix_inventory_positions_timestamp"), table_name="inventory_positions")
    op.drop_index(op.f("ix_inventory_positions_sku_id"), table_name="inventory_positions")
    op.drop_index(op.f("ix_inventory_positions_brand_id"), table_name="inventory_positions")
    op.drop_index(op.f("ix_inventory_positions_id"), table_name="inventory_positions")
    op.drop_table("inventory_positions")
