"""
Engine Router — Trigger the 15-minute operational cycle or run simulations.
===========================================================================
Uses:
  - src/engine/swi_calculator.py
  - src/engine/fragility_curves.py
  - src/engine/alert_dispatcher.py
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
)
from src.engine.swi_calculator import SWICalculator
from src.engine.fragility_curves import FragilityEvaluator
from src.engine.alert_dispatcher import AlertDispatcher
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
    """Run the full data pipeline on existing rainfall data."""
    rain_file = paths.RAW / "rainfall_Ligne_400.csv"

    if not rain_file.exists():
        return CycleResult(
            status="error",
            message=f"Rainfall data not found at {rain_file}. Run data ingestion first.",
        )

    try:
        # Step 1: Compute SWI
        calc = SWICalculator(half_life_days=10)
        df = calc.process_corridor_risk(rain_file)

        peak_swi = float(df["swi_mm"].max())
        logger.info("Cycle complete. Peak SWI = %.2f mm", peak_swi)

        return CycleResult(
            status="success",
            swi_peak_mm=round(peak_swi, 2),
            alerts_generated=0,  # Alerts depend on HEC-RAS .prj (currently blocked)
            message=f"SWI updated from {rain_file.name}. Peak SWI = {peak_swi:.2f} mm. "
                    f"HEC-RAS dispatch is blocked (awaiting .prj file).",
        )
    except Exception as e:
        logger.exception("Cycle failed")
        return CycleResult(status="error", message=str(e))


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
