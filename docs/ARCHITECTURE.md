# ShelfOps Architecture (Planned)

## 1) Repository structure

```text
shelfops/
  AGENTS.md
  README.md
  docs/
    PRD.md
    TASKS.md
    DATA_FORMATS.md
    ARCHITECTURE.md
  backend/                 # FastAPI service (to be created)
    app/
      api/
      core/
      models/
      schemas/
      services/
      repositories/
      jobs/
    alembic/
    tests/
  frontend/                # Next.js app (to be created)
    src/
      app/
      components/
      lib/
      hooks/
  infra/
    docker/
    compose/
```

## 2) Backend structure
- `app/api/` → FastAPI routers grouped by domain:
  - `imports`
  - `cases`
  - `diagnosis`
  - `actions`
  - `tracking`
  - `metrics`
- `app/schemas/` → Pydantic v2 request/response + ingestion schemas.
- `app/models/` → SQLAlchemy models.
- `app/services/` → business logic (import parser, case engine, diagnosis engine).
- `app/repositories/` → DB access boundaries.
- `app/jobs/` → asynchronous/background processing.
- `tests/` → pytest unit + integration tests.

## 3) Frontend structure
- `src/app/` → Next.js routes/pages.
- `src/components/` → reusable UI components (tables, filters, status chips).
- `src/lib/` → API client + helpers.
- `src/hooks/` → state and data-fetch hooks.

Planned key screens:
1. Import center (upload + validation feedback)
2. Stockout case list/board
3. Case detail (diagnosis + actions + timeline)
4. Recovery KPI dashboard

## 4) Database tables (initial plan)
- `import_batches`
  - metadata for each file upload and processing state.
- `import_rows`
  - optional normalized/staged raw records and row-level outcomes.
- `products`
  - SKU master.
- `availability_snapshots`
  - normalized availability events.
- `sales_velocity_daily`
  - historical sales metrics for impact estimation.
- `inventory_positions`
  - stock by node/date.
- `purchase_orders`
- `dispatch_events`
- `grn_events`
- `stockout_cases`
  - core workflow entity.
- `case_diagnoses`
  - reason category + evidence.
- `case_actions`
  - recommended and/or assigned actions.
- `case_assignments`
  - owner + SLA fields.
- `case_status_history`
  - state transitions and audit trail.

## 5) API modules (planned)
- `POST /imports/{report_type}`: upload file.
- `GET /imports`: list batches and outcomes.
- `GET /imports/{batch_id}`: validation details.
- `POST /cases/generate`: generate/update cases from imported data.
- `GET /cases`: list/filter cases.
- `GET /cases/{case_id}`: case detail.
- `POST /cases/{case_id}/diagnose`: run or refresh diagnosis.
- `POST /cases/{case_id}/recommend-action`: generate action suggestion.
- `POST /cases/{case_id}/assign`: assign owner.
- `POST /cases/{case_id}/status`: update status.
- `GET /metrics/recovery`: aggregate KPI view.

## 6) Background job plan
Use Redis-backed worker (implementation choice deferred; e.g., RQ/Celery/Arq).

Initial async jobs:
1. Parse and validate uploaded files.
2. Case generation for large date windows.
3. Diagnosis refresh jobs.
4. Periodic KPI materialization.

Job requirements:
- idempotent execution
- retry policy with dead-letter behavior
- observable progress + failures via import/job status endpoints

## 7) Future AI agent plan (post-MVP)
AI is deferred to later phases and should remain optional.

Potential future additions:
1. Case summary generation for operators.
2. Action recommendation refinement with confidence notes.
3. Natural-language querying over recovery metrics.

Guardrails for future AI:
- human-in-the-loop approval for any generated action text
- explainability fields persisted with outputs
- no autonomous execution of operational actions
