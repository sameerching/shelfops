from fastapi import FastAPI

app = FastAPI(title="ShelfOps API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
