
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db
from app.model_service import ModelNotLoaded, get_model_service
from app.routers import insights, predict, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.errors = 0
    yield


app = FastAPI(
    title="FraudShield AI",
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Explainable credit card fraud scoring and "
        "investigation API (portfolio project)."
    ),
)

app.state.errors = 0

# CORS: allow the deployed frontend and local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *get_settings().cors_origins,
        "https://fraud-shield-a3fka0i6w-charan-2d53.vercel.app",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def count_errors(request: Request, call_next):
    response = await call_next(request)

    if response.status_code >= 500:
        request.app.state.errors = (
            getattr(request.app.state, "errors", 0) + 1
        )

    return response


@app.exception_handler(ModelNotLoaded)
async def model_missing(request: Request, exc: ModelNotLoaded):
    request.app.state.errors = (
        getattr(request.app.state, "errors", 0) + 1
    )

    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


@app.get("/health", tags=["health"])
def health():
    try:
        svc = get_model_service()
        return {
            "status": "ok",
            "model_loaded": True,
            "model_version": svc.version,
        }
    except ModelNotLoaded as e:
        return {
            "status": "degraded",
            "model_loaded": False,
            "detail": str(e),
        }


app.include_router(predict.router)
app.include_router(transactions.router)
app.include_router(insights.router)
