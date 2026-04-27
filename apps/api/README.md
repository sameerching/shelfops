# ShelfOps API

## Run locally

```bash
uv sync --group dev
uv run uvicorn app.main:app --reload
```

## Local infrastructure

From the repository root:

```bash
docker compose up -d postgres redis
```

## Run migrations

```bash
uv run alembic upgrade head
```

## Run tests

```bash
uv run pytest -q
```
