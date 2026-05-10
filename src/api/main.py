"""
Railway Flood-Risk Digital Twin — REST API
==========================================
FastAPI application entry-point.

Start with:
    .conda\\python.exe -m uvicorn src.api.main:app --reload --port 8000

Swagger docs will be available at:  http://localhost:8000/docs
ReDoc at:                           http://localhost:8000/redoc
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import assets, alerts, hydrology, engine

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("railway_api")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Railway Flood-Twin API starting ===")
    logger.info("Docs:  http://localhost:8000/docs")
    logger.info("ReDoc: http://localhost:8000/redoc")
    yield
    logger.info("=== Railway Flood-Twin API shutting down ===")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Railway Flood-Risk Digital Twin API",
    description=(
        "RESTful API for the SNCF Ligne 400 Flood-Risk Digital Twin demonstrator. "
        "Exposes infrastructure asset data, real-time RAMS risk verdicts, "
        "hydrological SWI computations, and synthetic flood inundation maps.\n\n"
        "**Architecture**: 4-Layer Model (Data Sources → Bridge → Simulation → Vulnerability & Alert)\n\n"
        "**Alert Hierarchy**: GREEN → YELLOW → ORANGE → RED (CAP-standard)"
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# CORS — allow Streamlit dashboard and future frontends
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",   # Streamlit default
        "http://localhost:3000",   # React / Next.js dev
        "http://localhost:5173",   # Vite dev
        "http://127.0.0.1:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
app.include_router(assets.router)
app.include_router(alerts.router)
app.include_router(hydrology.router)
app.include_router(engine.router)


# ---------------------------------------------------------------------------
# Root health-check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Railway Flood-Risk Digital Twin API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Lightweight health probe for monitoring."""
    return {"status": "ok"}
