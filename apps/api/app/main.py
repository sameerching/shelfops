from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.skus import router as skus_router

app = FastAPI(title="ShelfOps API")
app.include_router(health_router)
app.include_router(imports_router)
app.include_router(skus_router)
