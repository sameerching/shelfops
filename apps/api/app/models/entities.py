from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="brand")
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(back_populates="brand")
    skus: Mapped[list["SKU"]] = relationship(back_populates="brand_rel")
    import_batches: Mapped[list["ImportBatch"]] = relationship(back_populates="brand")
    availability_snapshots: Mapped[list["AvailabilitySnapshot"]] = relationship(back_populates="brand")
    sales_velocity_rows: Mapped[list["SalesVelocity"]] = relationship(back_populates="brand")
    inventory_positions: Mapped[list["InventoryPosition"]] = relationship(back_populates="brand")
    po_records: Mapped[list["PORecord"]] = relationship(back_populates="brand")
    dispatch_records: Mapped[list["DispatchRecord"]] = relationship(back_populates="brand")
    grn_records: Mapped[list["GRNRecord"]] = relationship(back_populates="brand")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False)

    brand: Mapped[Brand] = relationship(back_populates="users")


class UploadedFile(TimestampMixin, Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    brand: Mapped[Brand] = relationship(back_populates="uploaded_files")


class SKU(TimestampMixin, Base):
    __tablename__ = "skus"
    __table_args__ = (UniqueConstraint("brand_id", "sku_code", name="uq_skus_brand_id_sku_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_code: Mapped[str] = mapped_column(String(100), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    contribution_margin: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    case_pack: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mrp: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_hero_sku: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    brand_rel: Mapped[Brand] = relationship(back_populates="skus")
    availability_snapshots: Mapped[list["AvailabilitySnapshot"]] = relationship(back_populates="sku")
    sales_velocity_rows: Mapped[list["SalesVelocity"]] = relationship(back_populates="sku")
    inventory_positions: Mapped[list["InventoryPosition"]] = relationship(back_populates="sku")
    po_records: Mapped[list["PORecord"]] = relationship(back_populates="sku")
    dispatch_records: Mapped[list["DispatchRecord"]] = relationship(back_populates="sku")
    grn_records: Mapped[list["GRNRecord"]] = relationship(back_populates="sku")


class ImportBatch(TimestampMixin, Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_rows: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    accepted_rows: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rejected_rows: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    duplicate_rows: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    brand: Mapped[Brand] = relationship(back_populates="import_batches")
    row_errors: Mapped[list["ImportRowError"]] = relationship(back_populates="import_batch", cascade="all, delete-orphan")
    availability_snapshots: Mapped[list["AvailabilitySnapshot"]] = relationship(back_populates="import_batch")
    sales_velocity_rows: Mapped[list["SalesVelocity"]] = relationship(back_populates="import_batch")
    inventory_positions: Mapped[list["InventoryPosition"]] = relationship(back_populates="import_batch")
    po_records: Mapped[list["PORecord"]] = relationship(back_populates="import_batch")
    dispatch_records: Mapped[list["DispatchRecord"]] = relationship(back_populates="import_batch")
    grn_records: Mapped[list["GRNRecord"]] = relationship(back_populates="import_batch")


class ImportRowError(Base):
    __tablename__ = "import_row_errors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(nullable=False)
    column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    import_batch: Mapped[ImportBatch] = relationship(back_populates="row_errors")


class Location(TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("platform", "city", "location", name="uq_locations_platform_city_location"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)

    availability_snapshots: Mapped[list["AvailabilitySnapshot"]] = relationship(back_populates="location_rel")


class AvailabilitySnapshot(TimestampMixin, Base):
    __tablename__ = "availability_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "sku_id",
            "location_id",
            "timestamp",
            name="uq_availability_snapshot_dedupe",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand] = relationship(back_populates="availability_snapshots")
    sku: Mapped[SKU] = relationship(back_populates="availability_snapshots")
    location_rel: Mapped[Location] = relationship(back_populates="availability_snapshots")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="availability_snapshots")


class SalesVelocity(TimestampMixin, Base):
    __tablename__ = "sales_velocity"
    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "sku_id",
            "platform",
            "city",
            name="uq_sales_velocity_brand_sku_platform_city",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_units_per_day: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand] = relationship(back_populates="sales_velocity_rows")
    sku: Mapped[SKU] = relationship(back_populates="sales_velocity_rows")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="sales_velocity_rows")


class InventoryPosition(TimestampMixin, Base):
    __tablename__ = "inventory_positions"
    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "sku_id",
            "warehouse",
            "city",
            "timestamp",
            name="uq_inventory_position_dedupe",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    available_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand] = relationship(back_populates="inventory_positions")
    sku: Mapped[SKU] = relationship(back_populates="inventory_positions")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="inventory_positions")


class PORecord(TimestampMixin, Base):
    __tablename__ = "po_records"
    __table_args__ = (
        UniqueConstraint("brand_id", "sku_id", "platform", "city", "po_number", name="uq_po_record_dedupe"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    po_number: Mapped[str] = mapped_column(String(100), nullable=False)
    po_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    po_status: Mapped[str] = mapped_column(String(100), nullable=False)
    po_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand] = relationship(back_populates="po_records")
    sku: Mapped[SKU] = relationship(back_populates="po_records")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="po_records")


class DispatchRecord(TimestampMixin, Base):
    __tablename__ = "dispatch_records"
    __table_args__ = (
        UniqueConstraint("brand_id", "sku_id", "platform", "city", "dispatch_date", name="uq_dispatch_record_dedupe"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    dispatch_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    dispatch_status: Mapped[str] = mapped_column(String(100), nullable=False)
    dispatch_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand] = relationship(back_populates="dispatch_records")
    sku: Mapped[SKU] = relationship(back_populates="dispatch_records")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="dispatch_records")


class GRNRecord(TimestampMixin, Base):
    __tablename__ = "grn_records"
    __table_args__ = (
        UniqueConstraint("brand_id", "sku_id", "platform", "city", "grn_date", name="uq_grn_record_dedupe"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    grn_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    grn_status: Mapped[str] = mapped_column(String(100), nullable=False)
    grn_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )

    brand: Mapped[Brand] = relationship(back_populates="grn_records")
    sku: Mapped[SKU] = relationship(back_populates="grn_records")
    import_batch: Mapped[ImportBatch] = relationship(back_populates="grn_records")
