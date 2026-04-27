"""add sku master import tables

Revision ID: 20260427_0002
Revises: 20260427_0001
Create Date: 2026-04-27 00:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_0002"
down_revision: str | None = "20260427_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("sku_code", sa.String(length=100), nullable=False),
        sa.Column("sku_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("selling_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("contribution_margin", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("case_pack", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("mrp", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_hero_sku", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active_flag", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "sku_code", name="uq_skus_brand_id_sku_code"),
    )
    op.create_index(op.f("ix_skus_id"), "skus", ["id"], unique=False)
    op.create_index(op.f("ix_skus_brand_id"), "skus", ["brand_id"], unique=False)

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_batches_id"), "import_batches", ["id"], unique=False)
    op.create_index(op.f("ix_import_batches_brand_id"), "import_batches", ["brand_id"], unique=False)

    op.create_table(
        "import_row_errors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_name", sa.String(length=100), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_row_errors_id"), "import_row_errors", ["id"], unique=False)
    op.create_index(op.f("ix_import_row_errors_import_batch_id"), "import_row_errors", ["import_batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_import_row_errors_import_batch_id"), table_name="import_row_errors")
    op.drop_index(op.f("ix_import_row_errors_id"), table_name="import_row_errors")
    op.drop_table("import_row_errors")

    op.drop_index(op.f("ix_import_batches_brand_id"), table_name="import_batches")
    op.drop_index(op.f("ix_import_batches_id"), table_name="import_batches")
    op.drop_table("import_batches")

    op.drop_index(op.f("ix_skus_brand_id"), table_name="skus")
    op.drop_index(op.f("ix_skus_id"), table_name="skus")
    op.drop_table("skus")
