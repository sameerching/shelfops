# ShelfOps Data Formats (CSV/XLSX)

ShelfOps MVP starts from file uploads only. Each file can be CSV or XLSX.

## General rules
- Header row required.
- Column names are case-insensitive but mapped to canonical names below.
- Dates should be ISO (`YYYY-MM-DD`) where possible.
- Currency fields should be numeric.
- All timestamps are interpreted as UTC unless a timezone column is provided.
- Primary dedupe key for ingested rows = report_type + source_file + natural_key fields.

---

## 1) SKU master
**Purpose:** Master dimension for SKU metadata.

### Required columns
- `sku_code` (string) — unique SKU identifier
- `sku_name` (string)
- `brand` (string)
- `category` (string)
- `mrp` (number)
- `list_price` (number)
- `uom` (string)
- `active_flag` (boolean)

### Optional columns
- `subcategory` (string)
- `launch_date` (date)
- `discontinue_date` (date)

---

## 2) Availability report
**Purpose:** Detect stockouts by SKU/location/platform/time.

### Required columns
- `report_date` (date)
- `platform` (string)
- `city` (string)
- `store_id` (string)
- `sku_code` (string)
- `availability_status` (string: `in_stock` / `out_of_stock`)
- `snapshot_time` (datetime)

### Optional columns
- `listing_status` (string)
- `buy_box_status` (string)

---

## 3) Sales velocity
**Purpose:** Estimate lost revenue during stockout periods.

### Required columns
- `date` (date)
- `platform` (string)
- `city` (string)
- `sku_code` (string)
- `units_sold` (number)
- `net_revenue` (number)

### Optional columns
- `promo_flag` (boolean)
- `discount_amount` (number)

---

## 4) Inventory report
**Purpose:** Understand on-hand and available inventory by node.

### Required columns
- `report_date` (date)
- `node_type` (string: `warehouse` / `dark_store`)
- `node_id` (string)
- `sku_code` (string)
- `on_hand_qty` (number)
- `available_qty` (number)
- `reserved_qty` (number)

### Optional columns
- `in_transit_qty` (number)
- `safety_stock_qty` (number)

---

## 5) PO tracker
**Purpose:** Diagnose supply gaps due to purchase order delays or shortages.

### Required columns
- `po_number` (string)
- `po_date` (date)
- `supplier_name` (string)
- `sku_code` (string)
- `ordered_qty` (number)
- `expected_dispatch_date` (date)
- `expected_grn_date` (date)
- `po_status` (string)

### Optional columns
- `received_qty` (number)
- `po_line_value` (number)

---

## 6) Dispatch tracker
**Purpose:** Track fulfillment dispatch execution against POs/transfers.

### Required columns
- `dispatch_id` (string)
- `dispatch_date` (date)
- `source_node_id` (string)
- `destination_node_id` (string)
- `sku_code` (string)
- `dispatch_qty` (number)
- `dispatch_status` (string)

### Optional columns
- `eta_date` (date)
- `transporter_name` (string)

---

## 7) GRN tracker
**Purpose:** Confirm goods receipt and inward completion.

### Required columns
- `grn_number` (string)
- `grn_date` (date)
- `node_id` (string)
- `sku_code` (string)
- `received_qty` (number)
- `grn_status` (string)

### Optional columns
- `po_number` (string)
- `short_qty` (number)
- `damage_qty` (number)

---

## 8) Owner mapping
**Purpose:** Map platform/city/category combinations to case owners.

### Required columns
- `owner_id` (string)
- `owner_name` (string)
- `owner_email` (string)
- `platform` (string)
- `city` (string)
- `category` (string)

### Optional columns
- `backup_owner_email` (string)
- `sla_hours` (number)

---

## Validation behavior (MVP)
- Hard fail batch if required columns are missing.
- Soft fail row if datatype coercion fails; keep rest of batch.
- Store row-level errors with `row_number`, `column_name`, `error_code`, `error_message`.
- Provide import summary metrics:
  - total_rows
  - accepted_rows
  - rejected_rows
  - duplicate_rows
