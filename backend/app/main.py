"""
NL2I Backend — FastAPI Application Entry Point.

AI-powered AWS Infrastructure Designer & Deployer.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.utils.logging import setup_logging

# Import all models so they are registered with SQLAlchemy
from app.models import user, project, architecture, deployment, chat  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create database tables on startup."""
    setup_logging(debug=settings.DEBUG)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered AWS Infrastructure Designer & Deployer — Convert natural language to AWS architecture, Terraform IaC, and deploy.",
    lifespan=lifespan,
)

# ── CORS Middleware ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API Routers ────────────────────────────────────────
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.architecture import router as architecture_router
from app.api.deployment import router as deployment_router
from app.api.websocket import router as websocket_router
from app.api.config import router as config_router
from app.api.monitoring import router as monitoring_router

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(architecture_router)
app.include_router(deployment_router)
app.include_router(websocket_router)
app.include_router(config_router)
app.include_router(monitoring_router)


@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "version": settings.APP_VERSION,
    }
