# ShelfOps

ShelfOps is a quick-commerce availability recovery platform for D2C/FMCG brands.

It converts uploaded operational data into recovery actions:
`CSV/XLSX upload -> stockout case -> lost revenue estimate -> diagnosis -> recommended replenishment action -> owner assignment -> recovery tracking`.

## Important boundary
ShelfOps does **not** begin with digital shelf scraping.
MVP starts strictly from uploaded CSV/XLSX reports.

## Tech stack (planned)
- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI + Python
- Database: PostgreSQL
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Validation: Pydantic v2
- File parsing: pandas + openpyxl
- Local infra: Docker Compose (PostgreSQL + Redis)

## Project status
This repository currently contains **planning and documentation only**.
No frontend or backend application code has been scaffolded yet.

Available docs:
- `AGENTS.md` — engineering and delivery rules for future tasks
- `docs/PRD.md` — product requirements
- `docs/TASKS.md` — phased implementation plan
- `docs/DATA_FORMATS.md` — CSV/XLSX data contracts
- `docs/ARCHITECTURE.md` — planned system architecture

## Local run instructions (when implementation starts)
Planned commands for future setup:

```bash
# Start local services
docker compose up -d postgres redis

# Backend (planned)
uvicorn app.main:app --reload
pytest -q
alembic upgrade head

# Frontend (planned)
npm run dev
```

## MVP scope guardrails
- No scraping in MVP
- No AI integration in v1
- No authentication in the first prototype unless explicitly requested
