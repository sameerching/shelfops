# ShelfOps

ShelfOps is a quick-commerce availability recovery platform for D2C/FMCG brands.

It converts uploaded operational data into recovery actions:
`CSV/XLSX upload -> stockout case -> lost revenue estimate -> diagnosis -> recommended replenishment action -> owner assignment -> recovery tracking`.

## Important boundary
ShelfOps does **not** begin with digital shelf scraping.
MVP starts strictly from uploaded CSV/XLSX reports.

## Repository structure

```text
apps/
  web/    # Next.js + TypeScript + Tailwind
  api/    # FastAPI + uv + pytest
docs/
AGENTS.md
docker-compose.yml
README.md
```

## Local setup

### 1) Start infrastructure

```bash
docker compose up -d postgres redis
```

### 2) Run backend API

```bash
cd apps/api
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Health endpoints:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
curl http://127.0.0.1:8000/health/db
# {"status":"ok"}
```

### 3) Run backend tests

```bash
cd apps/api
uv run pytest -q
```

### 4) Run frontend web app

```bash
cd apps/web
npm install
npm run dev
```

### 5) Build/type-check frontend

```bash
cd apps/web
npm run build
npm run typecheck
```

## MVP scope guardrails
- No scraping in MVP
- No AI integration in v1
- No authentication in the first prototype unless explicitly requested
- No product feature implementation in Phase 0 beyond repository foundation
