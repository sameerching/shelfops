# ShelfOps Data Formats (CSV/XLSX)

ShelfOps MVP starts from file uploads only. Each file can be CSV or XLSX.

## General rules
- Header row required.
- Column names are case-insensitive but mapped to canonical names below.
- Dates should be ISO (`YYYY-MM-DD`) where possible.
- Currency and quantity fields should be numeric.
- All timestamps are interpreted as UTC unless a timezone column is provided.
- Primary dedupe key for ingested rows = `report_type + source_file + natural_key fields`.

---

## 1) SKU master
**Purpose:** Master dimension for SKU metadata used by the case and impact engines.

### Required columns
- `sku_code` (string) — unique SKU identifier
- `sku_name` (string)
- `category` (string)
- `selling_price` (number)
- `contribution_margin` (number)
- `case_pack` (number)

### Optional columns
- `brand` (string)
- `mrp` (number)
- `is_hero_sku` (boolean)
- `active_flag` (boolean)

---

## 2) Availability report
**Purpose:** Detect stockouts by SKU/platform/city/location over time.

### Required columns
- `sku_code` (string)
- `platform` (string)
- `city` (string)
- `location` (string)
- `status` (string: `in_stock` / `out_of_stock`)
- `timestamp` (datetime)

### Optional columns
- none in Phase 1

---

## 3) Sales velocity
**Purpose:** Provide expected demand baseline for lost revenue estimation.

### Required columns
- `sku_code` (string)
- `platform` (string)
- `city` (string)
- `avg_units_per_day` (number)

### Optional columns
- none in Phase 1

---

## 4) Inventory report
**Purpose:** Assess inventory availability by warehouse and city.

### Required columns
- `sku_code` (string)
- `warehouse` (string)
- `city` (string)
- `available_qty` (number)
- `timestamp` (datetime)

### Optional columns
- none in Phase 1

---

## 5) PO tracker
**Purpose:** Diagnose supply-side gaps from purchase order status.

### Required columns
- `sku_code` (string)
- `platform` (string)
- `city` (string)
- `po_number` (string)
- `po_qty` (number)
- `po_status` (string)
- `po_date` (date)

### Optional columns
- none in Phase 1

---

## 6) Dispatch tracker
**Purpose:** Track dispatch execution against planned replenishment.

### Required columns
- `sku_code` (string)
- `platform` (string)
- `city` (string)
- `dispatch_qty` (number)
- `dispatch_status` (string)
- `dispatch_date` (date)

### Optional columns
- none in Phase 1

---

## 7) GRN tracker
**Purpose:** Confirm goods receipt completion and inward timing.

### Required columns
- `sku_code` (string)
- `platform` (string)
- `city` (string)
- `grn_qty` (number)
- `grn_status` (string)
- `grn_date` (date)

### Optional columns
- none in Phase 1

---

## 8) Owner mapping
**Purpose:** Map platform and city to operational owners.

### Required columns
- `platform` (string)
- `city` (string)
- `owner_name` (string)
- `owner_email` (string)
- `role` (string)

### Optional columns
- none in Phase 1

---

## Validation behavior (MVP)
- Hard fail batch if required columns are missing.
- Soft fail row if datatype coercion fails; keep rest of batch.
- Store row-level errors with `row_number`, `column_name`, `error_code`, `error_message`.
- Provide import summary metrics:
  - `total_rows`
  - `accepted_rows`
  - `rejected_rows`
  - `duplicate_rows`
