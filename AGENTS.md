# ShelfOps Agent & Engineering Guide

## Product description
ShelfOps is a quick-commerce availability recovery platform for D2C/FMCG brands.

It converts uploaded stock and operations reports into concrete recovery work:

1. CSV/XLSX import
2. Stockout case creation
3. Lost revenue estimation
4. Root-cause diagnosis
5. Recommended replenishment action
6. Owner assignment
7. Recovery tracking

**Boundary:** ShelfOps does **not** do digital shelf scraping in MVP. It starts from user-uploaded files.

## Tech stack
- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python 3.12+
- Database: PostgreSQL
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Validation: Pydantic v2
- File parsing: pandas + openpyxl
- Cache/queue support: Redis (via Docker Compose)
- Backend tests: pytest
- Frontend tests: deferred until post-MVP

## Engineering rules
1. Build iteratively against docs/PRD.md and docs/TASKS.md.
2. Keep architecture modular and traceable from import → case → action → recovery.
3. Prefer explicit data contracts over implicit assumptions.
4. Every feature must preserve auditability (who/what/when).
5. No AI features in MVP unless explicitly requested.
6. No scraping in MVP.
7. No authentication in first prototype unless explicitly requested.
8. Keep pull requests small, focused, and reversible.

## Backend rules
1. Use FastAPI routers by bounded context (imports, cases, diagnosis, actions, tracking).
2. Use Pydantic v2 schemas for all request/response and ingestion validation.
3. SQLAlchemy models must map clearly to business entities from docs/ARCHITECTURE.md.
4. Use Alembic for any schema change; never modify DB schema without migration.
5. Parsing pipeline must capture row-level validation errors and expose import diagnostics.
6. Lost revenue and diagnosis logic must be deterministic and testable.
7. Time fields should be timezone-aware UTC.

## Frontend rules
1. Next.js App Router + TypeScript strict mode.
2. Tailwind for styling; avoid ad-hoc CSS unless justified.
3. UI should prioritize operational workflow speed:
   - identify stockouts,
   - inspect diagnosis,
   - assign action,
   - track closure.
4. Keep pages lightweight and API-driven.
5. Favor reusable table/filter/status components for operational dashboards.

## Testing rules
1. Backend features require pytest coverage for:
   - validation,
   - import normalization,
   - case generation,
   - diagnosis,
   - action recommendation logic.
2. Add regression tests for bugs before shipping fixes.
3. Migrations must be tested on a clean DB.
4. For MVP, frontend testing can be minimal/manual unless scope requests automation.

## Commands
> These are target commands for future implementation.

- Start local infra:
  - `docker compose up -d postgres redis`
- Run backend dev server:
  - `uvicorn app.main:app --reload`
- Run backend tests:
  - `pytest -q`
- Run Alembic migrations:
  - `alembic upgrade head`
- Run frontend dev server:
  - `npm run dev`

## Definition of done
A task is done when:
1. It maps to PRD scope and an item in docs/TASKS.md.
2. Code is documented and follows this guide.
3. Tests pass for affected backend logic.
4. Data contracts and migration impacts are updated in docs when needed.
5. PR review comments are resolved.
6. No boundary violations (no scraper, no unauthorized AI/auth additions).

## Review guidelines
1. Verify feature aligns to explicit MVP requirements.
2. Verify data inputs/outputs match docs/DATA_FORMATS.md.
3. Verify business logic has deterministic tests.
4. Verify migrations are safe and reversible.
5. Verify API contracts are explicit and typed.
6. Verify no forbidden scope creep (scraping, auth, AI in MVP).
7. Prefer actionable comments with expected outcomes.
