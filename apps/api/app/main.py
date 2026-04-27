from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.availability import router as availability_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.sales_velocity import router as sales_velocity_router
from app.api.skus import router as skus_router

app = FastAPI(title="ShelfOps API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(imports_router)
app.include_router(skus_router)
app.include_router(availability_router)
app.include_router(sales_velocity_router)
