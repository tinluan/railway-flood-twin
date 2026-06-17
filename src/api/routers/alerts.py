"""
src/api/routers/alerts.py — API Alerts Router
=================================================
Provides GET endpoints to retrieve RAMS-compliant risk verdicts and hotspot rankings
for the railway network at a specific timestep.

Architecture Position (API Layer):
    - EXPOSES: /api/v1/alerts/current and /api/v1/alerts/hotspots
    - READS:   data/processed/z_config.json (thresholds)
               data/processed/hecras_wse_results.json (water surface elevations)
    - USES:    src/engine/fragility_curves.py (computes P_failure on the fly)
               src/engine/alert_dispatcher.py (generates RAMS verdicts)
    - USED BY: Streamlit dashboard (to display traffic lights and top-N hotspots)

Endpoints:
    - GET /api/v1/alerts/current?timestep=T
        → Returns a SystemAlertSummary containing the overall network status (GREEN/YELLOW/ORANGE/RED)
          and a list of individual AlertVerdicts for every asset.
    - GET /api/v1/alerts/hotspots?top_n=5&timestep=T
        → Returns the top N most critical assets ranked by overtopping margin.

Relationship with other files:
    UPSTREAM:
      - hecras_bridge.py → provides the WSE data
    SCHEMAS:
      - src/api/schemas.py (AlertVerdict, SystemAlertSummary, HotspotResponse)

Example Usage (Client-side):
    import requests

    # 1. Get system status at hour 24:
    resp = requests.get("http://localhost:8000/api/v1/alerts/current?timestep=24")
    data = resp.json()
    print(f"Overall status: {data['overall_status']}")
    print(f"Red alerts: {data['red_count']}")

    # 2. Get top 3 hotspots:
    resp = requests.get("http://localhost:8000/api/v1/alerts/hotspots?top_n=3&timestep=24")
    hotspots = resp.json()["hotspots"]
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import (
    AlertColor,
    AlertVerdict,
    HotspotEntry,
    HotspotResponse,
    SystemAlertSummary,
)
from src.utils.paths import ProjectPaths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Alerts"])

paths = ProjectPaths


# ---------------------------------------------------------------------------
# Cached data
# ---------------------------------------------------------------------------
_z_config_cache: Optional[dict] = None
_wse_cache: Optional[dict] = None


def _load_z_config() -> dict:
    global _z_config_cache
    if _z_config_cache is None:
        z_path = paths.PROCESSED / "z_config.json"
        if not z_path.exists():
            raise HTTPException(status_code=503, detail=f"z_config.json not found at {z_path}")
        with open(z_path, "r", encoding="utf-8") as f:
            _z_config_cache = json.load(f)
    return _z_config_cache


def _load_wse() -> dict:
    global _wse_cache
    if _wse_cache is None:
        wse_path = paths.PROCESSED / "hecras_wse_results.json"
        if not wse_path.exists():
            raise HTTPException(status_code=503, detail=f"hecras_wse_results.json not found at {wse_path}")
        with open(wse_path, "r", encoding="utf-8") as f:
            _wse_cache = json.load(f)
        logger.info("Loaded hecras_wse_results.json (%d assets)", len(_wse_cache))
    return _wse_cache


def _evaluate_alert(asset_id: str, z_entry: dict, wse_entry: dict, timestep: int) -> AlertVerdict:
    """Evaluate the risk verdict for a single asset at a given timestep."""
    from src.engine.fragility_curves import FragilityEvaluator
    from src.engine.alert_dispatcher import AlertDispatcher

    evaluator = FragilityEvaluator()
    dispatcher = AlertDispatcher()

    wse_series = wse_entry.get("wse_m", [])
    base_z = wse_entry.get("base_z_m", 0)

    # Clamp timestep to available range
    t = min(timestep, len(wse_series) - 1) if wse_series else 0
    current_wse = wse_series[t] if wse_series else base_z

    # Determine z_ballast (red threshold = rail level)
    z_ballast = z_entry.get("red_z_m", z_entry.get("z_min_m", base_z))

    # Water depth above terrain
    water_depth = max(0, current_wse - base_z)
    p_failure = evaluator.calculate_p_failure(water_depth)
    category = evaluator.get_risk_category(p_failure)

    verdict = dispatcher.generate_verdict(asset_id, current_wse, z_ballast, p_failure, category)

    # Map to our enhanced colour system (add ORANGE between YELLOW and RED)
    yellow_z = z_entry.get("yellow_z_m")
    orange_z = z_entry.get("orange_z_m")
    red_z = z_entry.get("red_z_m")

    if red_z is not None and current_wse > red_z:
        color = AlertColor.RED
    elif orange_z is not None and current_wse > orange_z:
        color = AlertColor.ORANGE
    elif yellow_z is not None and current_wse > yellow_z:
        color = AlertColor.YELLOW
    else:
        color = AlertColor.GREEN

    return AlertVerdict(
        segment_id=asset_id,
        wse_m=round(current_wse, 3),
        z_ballast_m=z_ballast,
        p_failure_pct=round(p_failure * 100, 1),
        status=color,
        directive=verdict["directive"],
        timestamp=verdict["timestamp"],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/alerts/current",
    response_model=SystemAlertSummary,
    summary="System-wide risk verdict",
    description="Evaluates every asset against its thresholds at the specified "
                "timestep and returns a full risk snapshot with per-asset alerts.",
)
async def get_current_alerts(
    timestep: int = Query(47, ge=0, description="Timestep to evaluate (0-47 for 48h scenario)"),
):
    z_config = _load_z_config()
    wse_data = _load_wse()

    alerts = []
    counts = {"GREEN": 0, "YELLOW": 0, "ORANGE": 0, "RED": 0}

    for asset_id, z_entry in z_config.items():
        wse_entry = wse_data.get(asset_id, {})
        verdict = _evaluate_alert(asset_id, z_entry, wse_entry, timestep)
        alerts.append(verdict)
        counts[verdict.status.value] += 1

    # Overall status = worst among all assets
    if counts["RED"] > 0:
        overall = AlertColor.RED
    elif counts["ORANGE"] > 0:
        overall = AlertColor.ORANGE
    elif counts["YELLOW"] > 0:
        overall = AlertColor.YELLOW
    else:
        overall = AlertColor.GREEN

    return SystemAlertSummary(
        overall_status=overall,
        total_assets=len(alerts),
        green_count=counts["GREEN"],
        yellow_count=counts["YELLOW"],
        orange_count=counts["ORANGE"],
        red_count=counts["RED"],
        alerts=alerts,
    )


@router.get(
    "/alerts/hotspots",
    response_model=HotspotResponse,
    summary="Top-N critical assets",
    description="Returns the N assets with the highest risk margin (WSE minus "
                "the most critical threshold exceeded).",
)
async def get_hotspots(
    top_n: int = Query(5, ge=1, le=50, description="Number of hotspots to return"),
    timestep: int = Query(47, ge=0, description="Timestep to evaluate"),
):
    z_config = _load_z_config()
    wse_data = _load_wse()

    scored: list[tuple[str, float, AlertColor]] = []

    for asset_id, z_entry in z_config.items():
        wse_entry = wse_data.get(asset_id, {})
        wse_series = wse_entry.get("wse_m", [])
        base_z = wse_entry.get("base_z_m", 0)

        t = min(timestep, len(wse_series) - 1) if wse_series else 0
        current_wse = wse_series[t] if wse_series else base_z

        # Find the most critical threshold exceeded
        red_z = z_entry.get("red_z_m")
        orange_z = z_entry.get("orange_z_m")
        yellow_z = z_entry.get("yellow_z_m")

        if red_z is not None and current_wse > red_z:
            margin = current_wse - red_z
            color = AlertColor.RED
        elif orange_z is not None and current_wse > orange_z:
            margin = current_wse - orange_z
            color = AlertColor.ORANGE
        elif yellow_z is not None and current_wse > yellow_z:
            margin = current_wse - yellow_z
            color = AlertColor.YELLOW
        else:
            # Use distance to nearest threshold as negative margin
            thresholds = [t for t in [yellow_z, orange_z, red_z] if t is not None]
            margin = (current_wse - min(thresholds)) if thresholds else 0
            color = AlertColor.GREEN

        scored.append((asset_id, margin, color, current_wse))

    # Sort by margin descending (highest overtopping first)
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_n]

    hotspots = [
        HotspotEntry(
            rank=i + 1,
            asset_id=item[0],
            wse_m=round(item[3], 3),
            threshold_exceeded=item[2],
            margin_m=round(item[1], 3),
        )
        for i, item in enumerate(top)
    ]

    return HotspotResponse(count=len(hotspots), hotspots=hotspots)
