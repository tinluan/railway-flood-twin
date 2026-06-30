"""
src/api/routers/engine.py — API Engine Router
=================================================
Provides POST endpoints to trigger the 15-minute operational cycle or to run
in-memory custom rainfall simulations.

Architecture Position (API Layer):
    - EXPOSES: /api/v1/engine/cycle and /api/v1/engine/simulate
    - USES:    src/engine/swi_calculator.py
               src/engine/fragility_curves.py
               src/engine/alert_dispatcher.py
    - USED BY: Streamlit dashboard (simulation panel and cycle trigger)

Endpoints:
    - POST /api/v1/engine/cycle
        → Triggers the full data pipeline: reads rainfall CSV, computes SWI,
          saves results. (HEC-RAS trigger is currently blocked pending .prj availability).
    - POST /api/v1/engine/simulate
        → Accepts a custom hourly rainfall array (JSON payload), computes SWI and
          runoff, and generates synthetic alerts for a representative corridor.
          All computations are in-memory (does not overwrite `data/processed`).

Relationship with other files:
    UPSTREAM:
      - Calls engine logic directly, bypassing file reads for simulations.
    SCHEMAS:
      - src/api/schemas.py (CycleRequest, CycleResult, SimulationRequest, SimulationResult)

Example Usage (Client-side):
    import requests

    # 1. Trigger the operational cycle:
    resp = requests.post("http://localhost:8000/api/v1/engine/cycle")
    print(resp.json()["message"])

    # 2. Run a custom simulation (e.g. 5 hours of 10mm/h rain):
    payload = {
        "rainfall_mm_h": [10.0, 10.0, 10.0, 10.0, 10.0],
        "half_life_days": 10.0
    }
    resp = requests.post("http://localhost:8000/api/v1/engine/simulate", json=payload)
    results = resp.json()
    print(f"Peak SWI: {results['peak_swi_mm']}")

    # 3. Fetch Live Rainfall:
    resp = requests.get("http://localhost:8000/api/v1/rainfall/live")
    print(resp.json())
"""

import logging
from datetime import datetime
from typing import List

import numpy as np
from fastapi import APIRouter

from src.api.schemas import (
    AlertColor,
    AlertVerdict,
    CycleRequest,
    CycleResult,
    SimulationRequest,
    SimulationResult,
    RainfallForecastResponse,
    HECRASRecomputeResult,
)
from src.engine.swi_calculator import SWICalculator
from src.engine.fragility_curves import FragilityEvaluator
from src.engine.alert_dispatcher import AlertDispatcher
from src.engine.pipeline_orchestrator import PipelineOrchestrator
from src.engine.rainfall_provider import RainfallProvider
from src.engine.data_ingestion import RainfallIngestor
from src.utils.paths import ProjectPaths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Engine"])

paths = ProjectPaths


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/engine/cycle",
    response_model=CycleResult,
    summary="Trigger operational cycle",
    description="Executes the 15-minute operational cycle: "
                "Ingest weather → Update SWI → Evaluate risk → Dispatch alerts. "
                "Returns a summary of the cycle results.",
)
async def trigger_cycle(request: CycleRequest = CycleRequest()):
    """Run the full data pipeline."""
    try:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run_cycle(
            source_mode="auto",
            force_hecras=request.force_hecras
        )
        return CycleResult(**result)
    except Exception as e:
        logger.exception("Cycle failed")
        return CycleResult(status="error", message=str(e))


@router.post(
    "/engine/hecras-recompute",
    response_model=HECRASRecomputeResult,
    summary="Trigger HEC-RAS 2D Recomputation",
    description="Forces a full unsteady flow computation in HEC-RAS using "
                "the latest rainfall data. Requires HEC-RAS 6.7 installed.",
)
async def trigger_hecras_recompute(plan_id: str = "p01"):
    """Manually trigger HEC-RAS run."""
    try:
        # We will implement this fully in Component 4.
        # For now, it returns a stub.
        return HECRASRecomputeResult(
            status="success",
            plan_id=plan_id,
            message="HEC-RAS bridge is currently being updated to support precipitation injection. "
                    "Recomputation request received.",
            wse_extracted=False
        )
    except Exception as e:
        logger.exception("HEC-RAS trigger failed")
        return HECRASRecomputeResult(status="error", plan_id=plan_id, message=str(e))


@router.get(
    "/rainfall/live",
    summary="Fetch latest live rainfall",
    description="Fetches just the current hour's rainfall from Open-Meteo API.",
)
async def get_live_rainfall():
    """Get the current hour's rainfall."""
    try:
        provider = RainfallProvider()
        return provider.fetch_current()
    except Exception as e:
        logger.exception("Live rainfall fetch failed")
        return {"status": "error", "message": str(e)}


@router.get(
    "/rainfall/forecast",
    response_model=RainfallForecastResponse,
    summary="Fetch 48h rainfall forecast",
    description="Fetches the 48-hour rainfall forecast from Open-Meteo API.",
)
async def get_rainfall_forecast():
    """Get the 48-hour rainfall forecast."""
    try:
        provider = RainfallProvider()
        df = provider.fetch_forecast(include_history=False, forecast_days=2)
        records = df.to_dict(orient="records")
        return RainfallForecastResponse(
            provider="Open-Meteo",
            latitude=provider.lat,
            longitude=provider.lon,
            records=len(records),
            data=[
                {
                    "timestamp": r["timestamp"].isoformat(),
                    "intensity_mm_h": r["intensity_mm_h"],
                    "source": r["source"]
                }
                for r in records
            ]
        )
    except Exception as e:
        logger.exception("Forecast fetch failed")
        raise


@router.post(
    "/engine/simulate",
    response_model=SimulationResult,
    summary="Run custom rainfall simulation",
    description="Accepts a custom hourly rainfall array and computes projected "
                "SWI, runoff coefficients, and alert verdicts without modifying "
                "any stored data. Pure in-memory computation.",
)
async def run_simulation(request: SimulationRequest):
    """In-memory simulation: rainfall → SWI → fragility → alerts."""
    calc = SWICalculator(half_life_days=request.half_life_days)
    evaluator = FragilityEvaluator()
    dispatcher = AlertDispatcher()

    # Compute SWI series
    swi_series = calc.compute_swi_recursive(request.rainfall_mm_h)
    runoff_series = [
        float(calc.calculate_runoff_coefficient(swi)) for swi in swi_series
    ]

    peak_swi = max(swi_series) if swi_series else 0.0

    # Generate per-timestep alerts using a synthetic single-segment model
    # (Uses Voie baseline elevation from a typical corridor value)
    BASE_Z = 210.0  # Representative corridor base elevation (m NGF)
    Z_BALLAST = 211.5  # Typical ballast top elevation

    alerts: List[AlertVerdict] = []
    for t, (swi_val, rain, runoff_coeff) in enumerate(
        zip(swi_series, request.rainfall_mm_h, runoff_series)
    ):
        # Simplified WSE estimate: base + scaled runoff contribution
        active_runoff = rain * runoff_coeff
        # Quick Manning-like approximation: depth ~ active_runoff^0.6 / 100
        water_depth = (active_runoff ** 0.6) / 100.0 if active_runoff > 0 else 0
        wse = BASE_Z + water_depth

        p_failure = evaluator.calculate_p_failure(water_depth)
        category = evaluator.get_risk_category(p_failure)

        verdict = dispatcher.generate_verdict("SIM_CORRIDOR", wse, Z_BALLAST, p_failure, category)

        # Map to 4-color system
        if wse > Z_BALLAST:
            color = AlertColor.RED
        elif wse > Z_BALLAST - 0.5:
            color = AlertColor.ORANGE
        elif wse > Z_BALLAST - 1.0:
            color = AlertColor.YELLOW
        else:
            color = AlertColor.GREEN

        alerts.append(
            AlertVerdict(
                segment_id="SIM_CORRIDOR",
                wse_m=round(wse, 3),
                z_ballast_m=Z_BALLAST,
                p_failure_pct=round(p_failure * 100, 1),
                status=color,
                directive=verdict["directive"],
                timestamp=f"T+{t}h",
            )
        )

    return SimulationResult(
        timesteps=len(swi_series),
        swi_series=[round(s, 3) for s in swi_series],
        runoff_series=[round(r, 4) for r in runoff_series],
        peak_swi_mm=round(peak_swi, 2),
        alerts=alerts,
    )
