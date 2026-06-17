"""
src/api/routers/assets.py — API Assets Router
=================================================
Provides GET endpoints to retrieve railway infrastructure asset metadata,
RAMS Z-thresholds, and 60m East-West DTM terrain profiles.

Architecture Position (API Layer):
    - EXPOSES: /api/v1/assets and /api/v1/cross-sections
    - READS:   data/processed/z_config.json         (asset thresholds)
               data/processed/voie_segments.json    (Voie segment metadata)
               data/processed/cross_sections.json   (DTM terrain profiles)
    - USED BY: Streamlit dashboard (to draw maps and asset lists)

Endpoints:
    - GET /api/v1/assets               → List all assets and their thresholds
    - GET /api/v1/assets/{id}          → Get full details for one asset
    - GET /api/v1/cross-sections/{id}  → Get the 60m elevation profile

Relationship with other files:
    UPSTREAM:
      - segment_voie.py → populates z_config.json with granular track segments
      - extract_cross_sections.py → creates the cross_sections.json
    SCHEMAS:
      - src/api/schemas.py (AssetSummary, AssetDetail, CrossSectionResponse)

Example Usage (Client-side):
    import requests

    # 1. Fetch all bridges:
    resp = requests.get("http://localhost:8000/api/v1/assets?asset_type=Pont Rail")
    bridges = resp.json()

    # 2. Fetch the terrain profile for a specific bridge:
    resp = requests.get("http://localhost:8000/api/v1/cross-sections/Pont_0")
    profile = resp.json()["profile"]
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import (
    AssetDetail,
    AssetSummary,
    AssetThresholds,
    CrossSectionPoint,
    CrossSectionResponse,
)
from src.utils.paths import ProjectPaths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Assets"])

paths = ProjectPaths


# ---------------------------------------------------------------------------
# Helpers — lazy-load data files (cached after first call)
# ---------------------------------------------------------------------------
_z_config_cache: Optional[dict] = None
_cross_sections_cache: Optional[dict] = None
_voie_segments_cache: Optional[dict] = None


def _load_z_config() -> dict:
    global _z_config_cache
    if _z_config_cache is None:
        z_path = paths.PROCESSED / "z_config.json"
        if not z_path.exists():
            raise HTTPException(status_code=503, detail=f"z_config.json not found at {z_path}")
        with open(z_path, "r", encoding="utf-8") as f:
            _z_config_cache = json.load(f)
        logger.info("Loaded z_config.json (%d assets)", len(_z_config_cache))
    return _z_config_cache


def _load_cross_sections() -> dict:
    global _cross_sections_cache
    if _cross_sections_cache is None:
        cs_path = paths.PROCESSED / "cross_sections.json"
        if not cs_path.exists():
            raise HTTPException(status_code=503, detail=f"cross_sections.json not found at {cs_path}")
        with open(cs_path, "r", encoding="utf-8") as f:
            _cross_sections_cache = json.load(f)
        logger.info("Loaded cross_sections.json (%d profiles)", len(_cross_sections_cache))
    return _cross_sections_cache


def _load_voie_segments() -> dict:
    global _voie_segments_cache
    if _voie_segments_cache is None:
        vs_path = paths.PROCESSED / "voie_segments.json"
        if vs_path.exists():
            with open(vs_path, "r", encoding="utf-8") as f:
                _voie_segments_cache = json.load(f)
            logger.info("Loaded voie_segments.json (%d segments)", len(_voie_segments_cache))
        else:
            _voie_segments_cache = {}
    return _voie_segments_cache


# ---------------------------------------------------------------------------
# Helpers — convert raw z_config entry to schema
# ---------------------------------------------------------------------------
def _entry_to_summary(asset_id: str, entry: dict) -> AssetSummary:
    thresholds = AssetThresholds(
        yellow_z_m=entry.get("yellow_z_m"),
        orange_z_m=entry.get("orange_z_m"),
        red_z_m=entry.get("red_z_m"),
    )
    return AssetSummary(
        asset_id=asset_id,
        asset_type=entry.get("asset_type"),
        thresholds=thresholds,
    )


def _entry_to_detail(asset_id: str, entry: dict) -> AssetDetail:
    known_keys = {
        "asset_type", "yellow_z_m", "orange_z_m", "red_z_m",
        "z_min_m", "z_max_m", "z_mean_m", "nearest_voie", "nearest_talus",
    }
    extra = {k: v for k, v in entry.items() if k not in known_keys}
    thresholds = AssetThresholds(
        yellow_z_m=entry.get("yellow_z_m"),
        orange_z_m=entry.get("orange_z_m"),
        red_z_m=entry.get("red_z_m"),
    )
    return AssetDetail(
        asset_id=asset_id,
        asset_type=entry.get("asset_type"),
        thresholds=thresholds,
        z_min_m=entry.get("z_min_m"),
        z_max_m=entry.get("z_max_m"),
        z_mean_m=entry.get("z_mean_m"),
        nearest_voie=entry.get("nearest_voie"),
        nearest_talus=entry.get("nearest_talus"),
        extra=extra if extra else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/assets",
    response_model=List[AssetSummary],
    summary="List all monitored assets",
    description="Returns the list of 120+ infrastructure assets with their "
                "Yellow / Orange / Red Z-thresholds from z_config.json.",
)
async def list_assets(
    asset_type: Optional[str] = Query(None, description="Filter by asset type (e.g. 'Voie', 'Buse')"),
):
    z_config = _load_z_config()
    results = []
    for asset_id, entry in z_config.items():
        if asset_type and entry.get("asset_type") != asset_type:
            continue
        results.append(_entry_to_summary(asset_id, entry))
    return results


@router.get(
    "/assets/{asset_id}",
    response_model=AssetDetail,
    summary="Get asset details",
    description="Returns full details and risk thresholds for a specific asset.",
)
async def get_asset(asset_id: str):
    z_config = _load_z_config()
    if asset_id not in z_config:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found")
    return _entry_to_detail(asset_id, z_config[asset_id])


@router.get(
    "/cross-sections/{asset_id}",
    response_model=CrossSectionResponse,
    summary="Get DTM cross-section profile",
    description="Returns the 60 m East-West terrain profile sampled at 1 m "
                "intervals from the asset centroid.",
)
async def get_cross_section(asset_id: str):
    cross_sections = _load_cross_sections()
    if asset_id not in cross_sections:
        raise HTTPException(
            status_code=404,
            detail=f"No cross-section profile for '{asset_id}'. "
                   f"Available: {len(cross_sections)} assets with DTM coverage.",
        )

    raw = cross_sections[asset_id]

    # Support two possible storage formats
    if isinstance(raw, list):
        # List of [distance, elevation] pairs
        profile = [
            CrossSectionPoint(distance_m=pt[0], elevation_m=pt[1])
            for pt in raw
        ]
    elif isinstance(raw, dict) and "distances" in raw and "elevations" in raw:
        profile = [
            CrossSectionPoint(distance_m=d, elevation_m=e)
            for d, e in zip(raw["distances"], raw["elevations"])
        ]
    else:
        profile = []

    return CrossSectionResponse(
        asset_id=asset_id,
        source="dtm",
        profile=profile,
    )
