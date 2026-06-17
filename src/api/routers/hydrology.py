"""
src/api/routers/hydrology.py — API Hydrology Router
=======================================================
Provides GET endpoints to retrieve SWI (Soil Water Index) time-series results
and synthetic flood polygon geometries (GeoJSON).

Architecture Position (API Layer):
    - EXPOSES: /api/v1/hydrology/swi, /api/v1/flood-polygons, /api/v1/flood-polygons/{timestep}
    - READS:   data/processed/swi_results.csv
               data/processed/synthetic_flood_timesteps.json
    - USED BY: Streamlit dashboard (SWI charts and animated maps)

Endpoints:
    - GET /api/v1/hydrology/swi
        → Returns the hourly rainfall, SWI, and runoff coefficient time-series.
          Supports ?start_hour and ?end_hour query parameters for slicing.
    - GET /api/v1/flood-polygons
        → Returns metadata about available timesteps (e.g., total count, range).
    - GET /api/v1/flood-polygons/{timestep}
        → Returns a GeoJSON FeatureCollection of flood extents for that hour.

Relationship with other files:
    UPSTREAM:
      - swi_calculator.py → generates swi_results.csv
      - synthetic_inundation.py → generates synthetic_flood_timesteps.json
    SCHEMAS:
      - src/api/schemas.py (SWIResponse, FloodPolygonResponse)

Example Usage (Client-side):
    import requests

    # 1. Fetch SWI results for hours 10 to 20:
    resp = requests.get("http://localhost:8000/api/v1/hydrology/swi?start_hour=10&end_hour=20")
    swi_data = resp.json()["records"]

    # 2. Fetch the flood polygon for hour 24:
    resp = requests.get("http://localhost:8000/api/v1/flood-polygons/24")
    geojson = resp.json()["geojson"]
"""

import json
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import FloodPolygonResponse, SWIRecord, SWIResponse
from src.utils.paths import ProjectPaths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Hydrology"])

paths = ProjectPaths


# ---------------------------------------------------------------------------
# Cached data
# ---------------------------------------------------------------------------
_swi_cache: Optional[pd.DataFrame] = None
_flood_cache: Optional[dict] = None


def _load_swi() -> pd.DataFrame:
    global _swi_cache
    if _swi_cache is None:
        swi_path = paths.PROCESSED / "swi_results.csv"
        if not swi_path.exists():
            raise HTTPException(status_code=503, detail=f"swi_results.csv not found at {swi_path}")
        _swi_cache = pd.read_csv(swi_path)
        logger.info("Loaded swi_results.csv (%d rows)", len(_swi_cache))
    return _swi_cache


def _load_flood_polygons() -> dict:
    global _flood_cache
    if _flood_cache is None:
        fp_path = paths.PROCESSED / "synthetic_flood_timesteps.json"
        if not fp_path.exists():
            raise HTTPException(status_code=503, detail=f"synthetic_flood_timesteps.json not found at {fp_path}")
        with open(fp_path, "r", encoding="utf-8") as f:
            _flood_cache = json.load(f)
        logger.info("Loaded synthetic_flood_timesteps.json (%d timesteps)", len(_flood_cache))
    return _flood_cache


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/hydrology/swi",
    response_model=SWIResponse,
    summary="Get SWI time-series",
    description="Returns the full Soil Water Index + runoff coefficient "
                "time-series from the latest hydrological computation.",
)
async def get_swi(
    start_hour: Optional[int] = Query(None, ge=0, description="Filter: start hour index"),
    end_hour: Optional[int] = Query(None, ge=0, description="Filter: end hour index"),
):
    df = _load_swi()

    # Slice if requested
    if start_hour is not None:
        df = df.iloc[start_hour:]
    if end_hour is not None:
        df = df.iloc[: (end_hour + 1) if start_hour is None else (end_hour - (start_hour or 0) + 1)]

    records = []
    for idx, row in df.iterrows():
        records.append(
            SWIRecord(
                timestamp=row.get("timestamp"),
                hour=int(idx) if start_hour is None else int(idx),
                intensity_mm_h=float(row.get("intensity_mm_h", 0)),
                swi_mm=float(row.get("swi_mm", 0)),
                runoff_coeff=float(row.get("runoff_coeff", 0)),
                active_runoff_mm=float(row.get("active_runoff_mm", 0)),
            )
        )
    return SWIResponse(count=len(records), records=records)


@router.get(
    "/flood-polygons/{timestep}",
    response_model=FloodPolygonResponse,
    summary="Get flood polygon for a timestep",
    description="Returns the synthetic inundation GeoJSON FeatureCollection "
                "for a given timestep (0-47 for the 48h Cevenol scenario).",
)
async def get_flood_polygon(timestep: int):
    flood_data = _load_flood_polygons()
    key = str(timestep)
    if key not in flood_data:
        available = sorted(flood_data.keys(), key=int)
        raise HTTPException(
            status_code=404,
            detail=f"Timestep {timestep} not found. "
                   f"Available: {available[0]}–{available[-1]} ({len(available)} total).",
        )
    return FloodPolygonResponse(timestep=timestep, geojson=flood_data[key])


@router.get(
    "/flood-polygons",
    summary="List available flood timesteps",
    description="Returns metadata about available flood polygon timesteps.",
)
async def list_flood_timesteps():
    flood_data = _load_flood_polygons()
    keys = sorted(flood_data.keys(), key=int)
    return {
        "total_timesteps": len(keys),
        "range": {"start": int(keys[0]), "end": int(keys[-1])} if keys else None,
        "timesteps_with_features": [
            int(k) for k in keys if flood_data[k].get("features")
        ],
    }
