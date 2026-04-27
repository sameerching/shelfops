from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Select, and_, func, select, tuple_
from sqlalchemy.orm import Session

from app.models.entities import AvailabilitySnapshot, CaseUpdate, Location, SKU, SalesVelocity, StockoutCase
from app.schemas.cases import StockoutCaseResponse

ACTIVE_CASE_STATUSES = {"detected", "active"}


def _hours_between(start: datetime, end: datetime) -> Decimal:
    seconds = Decimal(str((end - start).total_seconds()))
    hours = (seconds / Decimal("3600")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return max(hours, Decimal("0"))


def _priority_for_sales(estimated_lost_sales: Decimal) -> str:
    if estimated_lost_sales >= Decimal("50000"):
        return "P0"
    if estimated_lost_sales >= Decimal("10000"):
        return "P1"
    if estimated_lost_sales >= Decimal("2000"):
        return "P2"
    return "P3"


def _calculate_estimates(
    *,
    duration_hours: Decimal,
    velocity: SalesVelocity | None,
    sku: SKU,
) -> tuple[Decimal, Decimal, str]:
    if velocity is None:
        return Decimal("0.00"), Decimal("0.00"), "P3"

    duration_days = duration_hours / Decimal("24")
    lost_sales = (velocity.avg_units_per_day * sku.selling_price * duration_days).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    lost_margin = (velocity.avg_units_per_day * sku.contribution_margin * duration_days).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return lost_sales, lost_margin, _priority_for_sales(lost_sales)


def _to_response(case: StockoutCase, sku: SKU, location: Location) -> StockoutCaseResponse:
    return StockoutCaseResponse(
        id=case.id,
        sku_code=sku.sku_code,
        sku_name=sku.sku_name,
        platform=location.platform,
        city=location.city,
        location=location.location,
        status=case.status,
        priority=case.priority,
        detected_at=case.detected_at,
        last_seen_oos_at=case.last_seen_oos_at,
        recovered_at=case.recovered_at,
        stockout_duration_hours=case.stockout_duration_hours,
        estimated_lost_sales=case.estimated_lost_sales,
        estimated_lost_margin=case.estimated_lost_margin,
    )


def generate_stockout_cases(db: Session, brand_id: int) -> tuple[int, int, int, list[StockoutCase]]:
    active_cases = db.execute(
        select(StockoutCase).where(StockoutCase.brand_id == brand_id, StockoutCase.status.in_(ACTIVE_CASE_STATUSES))
    ).scalars().all()
    active_map = {(c.brand_id, c.sku_id, c.location_id): c for c in active_cases}

    latest_subquery = (
        select(
            AvailabilitySnapshot.brand_id.label("brand_id"),
            AvailabilitySnapshot.sku_id.label("sku_id"),
            AvailabilitySnapshot.location_id.label("location_id"),
            func.max(AvailabilitySnapshot.timestamp).label("latest_timestamp"),
        )
        .where(AvailabilitySnapshot.brand_id == brand_id)
        .group_by(AvailabilitySnapshot.brand_id, AvailabilitySnapshot.sku_id, AvailabilitySnapshot.location_id)
        .subquery()
    )

    latest_rows = db.execute(
        select(AvailabilitySnapshot)
        .join(
            latest_subquery,
            and_(
                AvailabilitySnapshot.brand_id == latest_subquery.c.brand_id,
                AvailabilitySnapshot.sku_id == latest_subquery.c.sku_id,
                AvailabilitySnapshot.location_id == latest_subquery.c.location_id,
                AvailabilitySnapshot.timestamp == latest_subquery.c.latest_timestamp,
            ),
        )
        .where(AvailabilitySnapshot.brand_id == brand_id)
    ).scalars()
    latest_by_combo = {(r.brand_id, r.sku_id, r.location_id): r for r in latest_rows}
    current_oos_combos = [combo for combo, row in latest_by_combo.items() if row.status == "out_of_stock"]

    oos_groups: list[tuple[int, int, int, datetime, datetime]] = []
    if current_oos_combos:
        scoped_rows = db.execute(
            select(
                AvailabilitySnapshot.brand_id,
                AvailabilitySnapshot.sku_id,
                AvailabilitySnapshot.location_id,
                AvailabilitySnapshot.status,
                AvailabilitySnapshot.timestamp,
            ).where(
                AvailabilitySnapshot.brand_id == brand_id,
                tuple_(
                    AvailabilitySnapshot.brand_id,
                    AvailabilitySnapshot.sku_id,
                    AvailabilitySnapshot.location_id,
                ).in_(current_oos_combos),
            )
        ).all()

        last_in_stock_by_combo: dict[tuple[int, int, int], datetime] = {}
        oos_timestamps_by_combo: dict[tuple[int, int, int], list[datetime]] = {}
        for row_brand_id, row_sku_id, row_location_id, status, timestamp in scoped_rows:
            combo = (row_brand_id, row_sku_id, row_location_id)
            if status == "in_stock":
                prior = last_in_stock_by_combo.get(combo)
                if prior is None or timestamp > prior:
                    last_in_stock_by_combo[combo] = timestamp
                continue
            if status != "out_of_stock":
                continue
            oos_timestamps_by_combo.setdefault(combo, []).append(timestamp)

        for combo in current_oos_combos:
            oos_timestamps = oos_timestamps_by_combo.get(combo, [])
            if not oos_timestamps:
                continue
            last_in_stock = last_in_stock_by_combo.get(combo)
            if last_in_stock is not None:
                oos_timestamps = [ts for ts in oos_timestamps if ts > last_in_stock]
            if not oos_timestamps:
                continue
            oos_groups.append((combo[0], combo[1], combo[2], min(oos_timestamps), max(oos_timestamps)))

    generated_cases = 0
    updated_cases = 0
    recovered_cases = 0

    for group_brand_id, sku_id, location_id, first_oos, last_oos in oos_groups:
        combo = (group_brand_id, sku_id, location_id)
        case = active_map.get(combo)
        sku = db.get(SKU, sku_id)
        location = db.get(Location, location_id)
        if sku is None or location is None:
            continue

        velocity = db.execute(
            select(SalesVelocity).where(
                SalesVelocity.brand_id == group_brand_id,
                SalesVelocity.sku_id == sku_id,
                SalesVelocity.platform == location.platform,
                SalesVelocity.city == location.city,
            )
        ).scalar_one_or_none()

        if case is None:
            duration_hours = _hours_between(first_oos, last_oos)
            lost_sales, lost_margin, priority = _calculate_estimates(duration_hours=duration_hours, velocity=velocity, sku=sku)
            case = StockoutCase(
                brand_id=group_brand_id,
                sku_id=sku_id,
                location_id=location_id,
                detected_at=first_oos,
                last_seen_oos_at=last_oos,
                recovered_at=None,
                stockout_duration_hours=duration_hours,
                estimated_lost_sales=lost_sales,
                estimated_lost_margin=lost_margin,
                priority=priority,
                status="detected",
            )
            db.add(case)
            db.flush()
            db.add(
                CaseUpdate(
                    case_id=case.id,
                    update_text="Case detected from out_of_stock availability snapshots",
                    old_status=None,
                    new_status="detected",
                )
            )
            active_map[combo] = case
            generated_cases += 1
            continue

        prior_last_seen = case.last_seen_oos_at
        case.last_seen_oos_at = max(case.last_seen_oos_at, last_oos)
        duration_hours = _hours_between(case.detected_at, case.last_seen_oos_at)
        lost_sales, lost_margin, priority = _calculate_estimates(duration_hours=duration_hours, velocity=velocity, sku=sku)
        case.stockout_duration_hours = duration_hours
        case.estimated_lost_sales = lost_sales
        case.estimated_lost_margin = lost_margin
        case.priority = priority
        old_status = case.status
        case.status = "active"
        case.recovered_at = None
        if prior_last_seen != case.last_seen_oos_at or old_status != case.status:
            db.add(
                CaseUpdate(
                    case_id=case.id,
                    update_text="Case updated with latest out_of_stock signal",
                    old_status=old_status,
                    new_status=case.status,
                )
            )
            updated_cases += 1

    for combo, case in active_map.items():
        latest_snapshot = latest_by_combo.get(combo)
        if latest_snapshot is None:
            continue
        if latest_snapshot.status != "in_stock":
            continue
        old_status = case.status
        case.status = "recovered"
        case.recovered_at = latest_snapshot.timestamp
        db.add(
            CaseUpdate(
                case_id=case.id,
                update_text="Case marked recovered from latest in_stock signal",
                old_status=old_status,
                new_status="recovered",
            )
        )
        recovered_cases += 1

    db.commit()

    result_cases = db.execute(
        select(StockoutCase)
        .where(StockoutCase.brand_id == brand_id)
        .order_by(StockoutCase.updated_at.desc(), StockoutCase.id.desc())
    ).scalars().all()
    return generated_cases, updated_cases, recovered_cases, result_cases


def list_cases(
    db: Session,
    *,
    brand_id: int,
    sku_code: str | None = None,
    platform: str | None = None,
    city: str | None = None,
    status: str | None = None,
    priority: str | None = None,
) -> list[StockoutCaseResponse]:
    stmt: Select[tuple[StockoutCase, SKU, Location]] = (
        select(StockoutCase, SKU, Location)
        .join(SKU, StockoutCase.sku_id == SKU.id)
        .join(Location, StockoutCase.location_id == Location.id)
        .where(StockoutCase.brand_id == brand_id)
        .order_by(StockoutCase.updated_at.desc(), StockoutCase.id.desc())
    )

    if sku_code:
        stmt = stmt.where(SKU.sku_code == sku_code)
    if platform:
        stmt = stmt.where(Location.platform == platform)
    if city:
        stmt = stmt.where(Location.city == city)
    if status:
        stmt = stmt.where(StockoutCase.status == status)
    if priority:
        stmt = stmt.where(StockoutCase.priority == priority)

    rows = db.execute(stmt).all()
    return [_to_response(case, sku, location) for case, sku, location in rows]


def get_case_detail(db: Session, case_id: int) -> StockoutCaseResponse | None:
    row = db.execute(
        select(StockoutCase, SKU, Location)
        .join(SKU, StockoutCase.sku_id == SKU.id)
        .join(Location, StockoutCase.location_id == Location.id)
        .where(StockoutCase.id == case_id)
    ).one_or_none()

    if row is None:
        return None

    case, sku, location = row
    return _to_response(case, sku, location)
