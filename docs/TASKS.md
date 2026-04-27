# ShelfOps Implementation Plan (Phased Tasks)

## Phase 0: Repo foundation
- [ ] Create monorepo scaffolding and standard tooling.
- [ ] Add base documentation (PRD, architecture, data formats, tasks).
- [ ] Define Python dependency management and lint/test setup.
- [ ] Define frontend package and TypeScript/Tailwind standards.
- [ ] Add Docker Compose for PostgreSQL + Redis.
- [ ] Set up Alembic baseline.
- [ ] Add CI skeleton for docs + backend tests.

## Phase 1: Data import
- [ ] Build upload endpoints for CSV/XLSX files.
- [ ] Implement parser adapters per report type.
- [ ] Implement schema validation using Pydantic models.
- [ ] Store import batches, row outcomes, and error details.
- [ ] Add import history API + UI.
- [ ] Add deterministic tests for happy path and validation failures.

## Phase 2: Stockout case engine
- [ ] Define stockout detection logic from availability report.
- [ ] Create case generation pipeline (dedupe + idempotency rules).
- [ ] Implement lost revenue estimation formula and configurable parameters.
- [ ] Persist cases with severity/priority scoring.
- [ ] Add APIs for case listing/filtering/detail.
- [ ] Build initial dashboard list view for created cases.

## Phase 3: Diagnosis and replenishment action
- [ ] Implement rules engine combining inventory + PO + dispatch + GRN signals.
- [ ] Map diagnosis categories (e.g., no inward, delayed dispatch, PO gap).
- [ ] Attach confidence/reason fields to each diagnosis.
- [ ] Build recommendation engine for next replenishment action.
- [ ] Add SLA/due-date defaults by priority.
- [ ] Test diagnosis and recommendation logic thoroughly.

## Phase 4: Dashboard and workflow
- [ ] Build operational dashboard (filters, impact ranking, status lanes).
- [ ] Add owner assignment and status transition workflow.
- [ ] Add recovery timeline logs and comments/notes.
- [ ] Track KPIs: open cases, overdue cases, estimated recovery value.
- [ ] Add export capability for case views.

## Phase 5: AI assistant layer (later)
- [ ] Introduce AI-assisted summaries of diagnosis rationale.
- [ ] Add AI action drafting with human approval gates.
- [ ] Add conversational analytics over case history.
- [ ] Add guardrails, prompt tracing, and decision audit logs.
- [ ] Keep AI optional and non-blocking for core workflow.

---

## Cross-phase quality gates
- [ ] Every phase includes API contract updates and migration review.
- [ ] Every business rule must include tests.
- [ ] Update architecture/data docs when model or format changes.
- [ ] No scraping in MVP phases.
- [ ] No auth in prototype unless scope changes explicitly.
