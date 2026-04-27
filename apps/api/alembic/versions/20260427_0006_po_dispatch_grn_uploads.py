"""add po, dispatch, and grn records tables

Revision ID: 20260427_0006
Revises: 20260427_0005
Create Date: 2026-04-27 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_0006"
down_revision: str | None = "20260427_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "po_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("po_number", sa.String(length=100), nullable=False),
        sa.Column("po_qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("po_status", sa.String(length=100), nullable=False),
        sa.Column("po_date", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "sku_id", "platform", "city", "po_number", "source_file", name="uq_po_record_dedupe"),
    )
    op.create_index(op.f("ix_po_records_id"), "po_records", ["id"], unique=False)
    op.create_index(op.f("ix_po_records_brand_id"), "po_records", ["brand_id"], unique=False)
    op.create_index(op.f("ix_po_records_sku_id"), "po_records", ["sku_id"], unique=False)
    op.create_index(op.f("ix_po_records_po_date"), "po_records", ["po_date"], unique=False)
    op.create_index(op.f("ix_po_records_source_file"), "po_records", ["source_file"], unique=False)
    op.create_index(op.f("ix_po_records_import_batch_id"), "po_records", ["import_batch_id"], unique=False)

    op.create_table(
        "dispatch_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("dispatch_qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("dispatch_status", sa.String(length=100), nullable=False),
        sa.Column("dispatch_date", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "brand_id", "sku_id", "platform", "city", "dispatch_date", "source_file", name="uq_dispatch_record_dedupe"
        ),
    )
    op.create_index(op.f("ix_dispatch_records_id"), "dispatch_records", ["id"], unique=False)
    op.create_index(op.f("ix_dispatch_records_brand_id"), "dispatch_records", ["brand_id"], unique=False)
    op.create_index(op.f("ix_dispatch_records_sku_id"), "dispatch_records", ["sku_id"], unique=False)
    op.create_index(op.f("ix_dispatch_records_dispatch_date"), "dispatch_records", ["dispatch_date"], unique=False)
    op.create_index(op.f("ix_dispatch_records_source_file"), "dispatch_records", ["source_file"], unique=False)
    op.create_index(
        op.f("ix_dispatch_records_import_batch_id"),
        "dispatch_records",
        ["import_batch_id"],
        unique=False,
    )

    op.create_table(
        "grn_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("grn_qty", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("grn_status", sa.String(length=100), nullable=False),
        sa.Column("grn_date", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "sku_id", "platform", "city", "grn_date", "source_file", name="uq_grn_record_dedupe"),
    )
    op.create_index(op.f("ix_grn_records_id"), "grn_records", ["id"], unique=False)
    op.create_index(op.f("ix_grn_records_brand_id"), "grn_records", ["brand_id"], unique=False)
    op.create_index(op.f("ix_grn_records_sku_id"), "grn_records", ["sku_id"], unique=False)
    op.create_index(op.f("ix_grn_records_grn_date"), "grn_records", ["grn_date"], unique=False)
    op.create_index(op.f("ix_grn_records_source_file"), "grn_records", ["source_file"], unique=False)
    op.create_index(op.f("ix_grn_records_import_batch_id"), "grn_records", ["import_batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_grn_records_source_file"), table_name="grn_records")
    op.drop_index(op.f("ix_grn_records_import_batch_id"), table_name="grn_records")
    op.drop_index(op.f("ix_grn_records_grn_date"), table_name="grn_records")
    op.drop_index(op.f("ix_grn_records_sku_id"), table_name="grn_records")
    op.drop_index(op.f("ix_grn_records_brand_id"), table_name="grn_records")
    op.drop_index(op.f("ix_grn_records_id"), table_name="grn_records")
    op.drop_table("grn_records")

    op.drop_index(op.f("ix_dispatch_records_source_file"), table_name="dispatch_records")
    op.drop_index(op.f("ix_dispatch_records_import_batch_id"), table_name="dispatch_records")
    op.drop_index(op.f("ix_dispatch_records_dispatch_date"), table_name="dispatch_records")
    op.drop_index(op.f("ix_dispatch_records_sku_id"), table_name="dispatch_records")
    op.drop_index(op.f("ix_dispatch_records_brand_id"), table_name="dispatch_records")
    op.drop_index(op.f("ix_dispatch_records_id"), table_name="dispatch_records")
    op.drop_table("dispatch_records")

    op.drop_index(op.f("ix_po_records_source_file"), table_name="po_records")
    op.drop_index(op.f("ix_po_records_import_batch_id"), table_name="po_records")
    op.drop_index(op.f("ix_po_records_po_date"), table_name="po_records")
    op.drop_index(op.f("ix_po_records_sku_id"), table_name="po_records")
    op.drop_index(op.f("ix_po_records_brand_id"), table_name="po_records")
    op.drop_index(op.f("ix_po_records_id"), table_name="po_records")
    op.drop_table("po_records")
