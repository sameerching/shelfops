from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.entities import AvailabilitySnapshot, CaseUpdate, Location, SKU, SalesVelocity, StockoutCase
from app.schemas.cases import StockoutCaseResponse


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
    existing_cases = db.execute(select(StockoutCase).where(StockoutCase.brand_id == brand_id)).scalars().all()
    existing_by_combo: dict[tuple[int, int, int], list[StockoutCase]] = {}
    for existing_case in existing_cases:
        combo_key = (existing_case.brand_id, existing_case.sku_id, existing_case.location_id)
        existing_by_combo.setdefault(combo_key, []).append(existing_case)
    for combo_cases in existing_by_combo.values():
        combo_cases.sort(key=lambda row: (row.detected_at, row.id))

    snapshot_rows = db.execute(
        select(
            AvailabilitySnapshot.brand_id,
            AvailabilitySnapshot.sku_id,
            AvailabilitySnapshot.location_id,
            AvailabilitySnapshot.status,
            AvailabilitySnapshot.timestamp,
        )
        .where(AvailabilitySnapshot.brand_id == brand_id)
        .order_by(
            AvailabilitySnapshot.brand_id,
            AvailabilitySnapshot.sku_id,
            AvailabilitySnapshot.location_id,
            AvailabilitySnapshot.timestamp,
            AvailabilitySnapshot.id,
        )
    ).all()

    snapshots_by_combo: dict[tuple[int, int, int], list[tuple[str, datetime]]] = {}
    for row_brand_id, row_sku_id, row_location_id, status, timestamp in snapshot_rows:
        combo = (row_brand_id, row_sku_id, row_location_id)
        snapshots_by_combo.setdefault(combo, []).append((status, timestamp))

    incident_by_combo: dict[tuple[int, int, int], list[tuple[datetime, datetime, datetime | None]]] = {}
    for combo, timeline in snapshots_by_combo.items():
        incidents: list[tuple[datetime, datetime, datetime | None]] = []
        open_start: datetime | None = None
        last_oos: datetime | None = None

        for status, timestamp in timeline:
            if status == "out_of_stock":
                if open_start is None:
                    open_start = timestamp
                last_oos = timestamp
                continue
            if status == "in_stock" and open_start is not None and last_oos is not None:
                incidents.append((open_start, last_oos, timestamp))
                open_start = None
                last_oos = None

        if open_start is not None and last_oos is not None:
            incidents.append((open_start, last_oos, None))

        if incidents:
            incident_by_combo[combo] = incidents

    generated_cases = 0
    updated_cases = 0
    recovered_cases = 0

    for combo, incidents in incident_by_combo.items():
        group_brand_id, sku_id, location_id = combo
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

        cases_for_combo = existing_by_combo.get(combo, [])
        case_by_detected = {existing_case.detected_at: existing_case for existing_case in cases_for_combo}
        unmatched_case_ids: set[int] = {existing_case.id for existing_case in cases_for_combo}
        active_unmatched_cases: list[StockoutCase] = [
            existing_case
            for existing_case in cases_for_combo
            if existing_case.id in unmatched_case_ids and existing_case.recovered_at is None
        ]

        for first_oos, last_oos, recovered_at in incidents:
            case = case_by_detected.get(first_oos)
            if case is None and recovered_at is None and len(active_unmatched_cases) == 1:
                # Backfilled out_of_stock snapshots can shift incident start earlier than the currently open case.
                # In that situation, update the existing open case instead of creating a duplicate.
                case = active_unmatched_cases[0]

            duration_end = recovered_at if recovered_at is not None else last_oos
            duration_hours = _hours_between(first_oos, duration_end)
            lost_sales, lost_margin, priority = _calculate_estimates(duration_hours=duration_hours, velocity=velocity, sku=sku)
            if recovered_at is not None:
                incident_status = "recovered"
            elif case is None:
                incident_status = "detected"
            else:
                incident_status = "active"

            if case is None:
                case = StockoutCase(
                    brand_id=group_brand_id,
                    sku_id=sku_id,
                    location_id=location_id,
                    detected_at=first_oos,
                    last_seen_oos_at=last_oos,
                    recovered_at=recovered_at,
                    stockout_duration_hours=duration_hours,
                    estimated_lost_sales=lost_sales,
                    estimated_lost_margin=lost_margin,
                    priority=priority,
                    status=incident_status,
                )
                db.add(case)
                db.flush()
                db.add(
                    CaseUpdate(
                        case_id=case.id,
                        update_text="Case detected from out_of_stock availability snapshots",
                        old_status=None,
                        new_status=incident_status,
                    )
                )
                generated_cases += 1
                continue

            unmatched_case_ids.discard(case.id)
            active_unmatched_cases = [existing_case for existing_case in active_unmatched_cases if existing_case.id != case.id]
            old_status = case.status
            has_changed = False
            if case.detected_at != first_oos:
                case.detected_at = first_oos
                has_changed = True
            if case.last_seen_oos_at != last_oos:
                case.last_seen_oos_at = last_oos
                has_changed = True
            if case.stockout_duration_hours != duration_hours:
                case.stockout_duration_hours = duration_hours
                has_changed = True
            if case.estimated_lost_sales != lost_sales:
                case.estimated_lost_sales = lost_sales
                has_changed = True
            if case.estimated_lost_margin != lost_margin:
                case.estimated_lost_margin = lost_margin
                has_changed = True
            if case.priority != priority:
                case.priority = priority
                has_changed = True
            if case.recovered_at != recovered_at:
                case.recovered_at = recovered_at
                has_changed = True
            if case.status != incident_status:
                case.status = incident_status
                has_changed = True

            if has_changed:
                db.add(
                    CaseUpdate(
                        case_id=case.id,
                        update_text="Case updated from availability status transitions",
                        old_status=old_status,
                        new_status=case.status,
                    )
                )
                if old_status != "recovered" and case.status == "recovered":
                    recovered_cases += 1
                else:
                    updated_cases += 1

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
