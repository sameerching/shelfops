"""add locations and availability snapshots

Revision ID: 20260427_0003
Revises: 20260427_0002
Create Date: 2026-04-27 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_0003"
down_revision: str | None = "20260427_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "city", "location", name="uq_locations_platform_city_location"),
    )
    op.create_index(op.f("ix_locations_id"), "locations", ["id"], unique=False)

    op.create_table(
        "availability_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "sku_id", "location_id", "timestamp", name="uq_availability_snapshot_dedupe"),
    )
    op.create_index(op.f("ix_availability_snapshots_id"), "availability_snapshots", ["id"], unique=False)
    op.create_index(op.f("ix_availability_snapshots_brand_id"), "availability_snapshots", ["brand_id"], unique=False)
    op.create_index(op.f("ix_availability_snapshots_sku_id"), "availability_snapshots", ["sku_id"], unique=False)
    op.create_index(op.f("ix_availability_snapshots_location_id"), "availability_snapshots", ["location_id"], unique=False)
    op.create_index(op.f("ix_availability_snapshots_import_batch_id"), "availability_snapshots", ["import_batch_id"], unique=False)
    op.create_index(op.f("ix_availability_snapshots_timestamp"), "availability_snapshots", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_availability_snapshots_timestamp"), table_name="availability_snapshots")
    op.drop_index(op.f("ix_availability_snapshots_import_batch_id"), table_name="availability_snapshots")
    op.drop_index(op.f("ix_availability_snapshots_location_id"), table_name="availability_snapshots")
    op.drop_index(op.f("ix_availability_snapshots_sku_id"), table_name="availability_snapshots")
    op.drop_index(op.f("ix_availability_snapshots_brand_id"), table_name="availability_snapshots")
    op.drop_index(op.f("ix_availability_snapshots_id"), table_name="availability_snapshots")
    op.drop_table("availability_snapshots")

    op.drop_index(op.f("ix_locations_id"), table_name="locations")
    op.drop_table("locations")
