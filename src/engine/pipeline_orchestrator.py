"""
src/engine/pipeline_orchestrator.py — Operational Cycle Manager (Layer 2)
===========================================================================
Orchestrates the 15-minute operational cycle of the Digital Twin.

Architecture Position (Layer 2 — Bridge):
    - CONTROLS:  Data Ingestion → SWI Calculator → HEC-RAS Trigger → Alerts
    - TRIGGERED BY: src/api/routers/engine.py (POST /api/v1/engine/cycle)
                    or a scheduled background task.

Operational Cycle Steps:
    1. Determine mode: 'live' (API) or 'demo' (static scenario)
    2. Fetch/update rainfall data via RainfallIngestor
    3. Compute SWI & Runoff via SWICalculator
    4. Evaluate Peak SWI vs Threshold:
        - If SWI > threshold AND mode == 'live' AND HEC-RAS enabled:
            → Trigger full HEC-RAS 2D recomputation via HECRASBridge
        - Else:
            → Keep existing/synthetic WSE results
    5. Evaluate RAMS vulnerabilities (alerts) based on the latest WSE
    6. Return cycle summary

Relationship with other files:
    UPSTREAM:  api/routers/engine.py triggers this orchestrator.
    CALLS:     data_ingestion.py, swi_calculator.py, hecras_bridge.py
    DOWNSTREAM: Saves cycle_log.json for dashboard visibility.

Example Usage:
    from src.engine.pipeline_orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator()
    result = orchestrator.run_cycle(source_mode="live", force_hecras=False)
    print(f"Cycle finished. Peak SWI: {result['peak_swi_mm']}")
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.config.settings import SWI_HECRAS_TRIGGER_MM
from src.engine.data_ingestion import RainfallIngestor
from src.engine.swi_calculator import SWICalculator
from src.utils.paths import ProjectPaths

logger = logging.getLogger(__name__)
paths = ProjectPaths


class PipelineOrchestrator:
    """Manages the full end-to-end data pipeline cycle."""

    def __init__(self):
        self.log_file = paths.PROCESSED / "cycle_log.json"

    def run_cycle(self, source_mode: str = "auto", force_hecras: bool = False) -> dict:
        """
        Execute one pass of the operational cycle.

        Args:
            source_mode: 'live' (force API), 'demo' (force static), or 'auto' (use freshest).
            force_hecras: If True, forces HEC-RAS recompute even if SWI is low.

        Returns:
            Dict containing the cycle summary results.
        """
        logger.info("Starting pipeline cycle. Mode: %s, Force HEC-RAS: %s", source_mode, force_hecras)
        start_time = datetime.now()

        result = {
            "timestamp": start_time.isoformat(),
            "status": "success",
            "source_mode": source_mode,
            "rainfall_file": None,
            "peak_swi_mm": 0.0,
            "hecras_triggered": False,
            "alerts_generated": 0,
            "message": "",
        }

        try:
            # ---------------------------------------------------------
            # Step 1: Data Ingestion (Rainfall)
            # ---------------------------------------------------------
            ingestor = RainfallIngestor()

            if source_mode == "live":
                logger.info("Fetching live forecast...")
                ingestor.fetch_live_forecast()
                rain_path = ingestor.live_file
            elif source_mode == "demo":
                logger.info("Using demo scenario...")
                rain_path = ingestor.output_file
                if not rain_path.exists():
                    ingestor.generate_demo_scenario()
            else:
                # auto mode: fetch live, but fallback to demo gracefully if it fails
                try:
                    ingestor.fetch_live_forecast()
                except Exception as e:
                    logger.warning("Auto mode failed to fetch live data: %s. Will fallback.", e)
                rain_path, actual_source = ingestor.get_active_rainfall()
                logger.info("Auto mode selected: %s (%s)", actual_source, rain_path.name)
                result["source_mode"] = actual_source

            result["rainfall_file"] = rain_path.name

            # ---------------------------------------------------------
            # Step 2: Hydrology (SWI Calculation)
            # ---------------------------------------------------------
            logger.info("Computing SWI from %s", rain_path.name)
            calc = SWICalculator(half_life_days=10)
            swi_df = calc.process_corridor_risk(rain_path)

            peak_swi = float(swi_df["swi_mm"].max())
            result["swi_peak_mm"] = round(peak_swi, 2)
            logger.info("Peak SWI calculated: %.2f mm", peak_swi)

            # ---------------------------------------------------------
            # Step 3: HEC-RAS Trigger Evaluation
            # ---------------------------------------------------------
            threshold = SWI_HECRAS_TRIGGER_MM
            trigger_reason = ""

            if force_hecras:
                result["hecras_triggered"] = True
                trigger_reason = "forced by user"
            elif peak_swi > threshold:
                result["hecras_triggered"] = True
                trigger_reason = f"Peak SWI ({peak_swi:.1f}) > Threshold ({threshold:.1f})"
            else:
                result["hecras_triggered"] = False
                trigger_reason = f"Peak SWI ({peak_swi:.1f}) <= Threshold ({threshold:.1f})"

            logger.info("HEC-RAS evaluation: %s (Triggered: %s)", trigger_reason, result["hecras_triggered"])

            if result["hecras_triggered"]:
                try:
                    from src.engine.hecras_bridge import HECRASBridge
                    from src.config.settings import HECRAS_PROJECT_DIR, HECRAS_PRJ_NAME
                    
                    prj_path = paths.DATA / HECRAS_PROJECT_DIR / f"{HECRAS_PRJ_NAME}.prj"
                    
                    with HECRASBridge() as bridge:
                        bridge.open_project(str(prj_path))
                        # Operational plan is p02 (21SEP2025 Cévenol storm, active plan in HEC-RAS project)
                        success = bridge.recompute_and_extract(str(rain_path), plan_id="p02", wait=True)
                        
                        if success:
                            result["message"] += f"HEC-RAS recomputed successfully. "
                            
                            # Refresh HDF5 reader cache and export WSE
                            from src.engine.hecras_hdf5_reader import HECRASPlanReader
                            import json
                            
                            hdf5_path = prj_path.with_suffix(".p02.hdf")
                            if hdf5_path.exists():
                                reader = HECRASPlanReader(str(hdf5_path))
                                reader.refresh_from_latest_run()
                                
                                coords_path = paths.PROCESSED / "asset_coordinates.json"
                                if coords_path.exists():
                                    with open(coords_path, "r", encoding="utf-8") as f:
                                        coords_dict = json.load(f)
                                    asset_coords = {k: (v["x"], v["y"]) for k, v in coords_dict.items()}
                                    out_path = paths.PROCESSED / "hecras_wse_results.json"
                                    reader.export_wse_json(out_path, asset_coords)
                                    result["message"] += "Dashboard WSE JSON updated. "
                        else:
                            result["message"] += f"HEC-RAS trigger met but recomputation failed. "
                            
                except ImportError as e:
                    logger.error("HEC-RAS Bridge not available: %s", e)
                    result["hecras_triggered"] = False
                    result["message"] += "HEC-RAS triggered but bridge unavailable. "
            else:
                result["message"] += f"Used existing WSE ({trigger_reason}). "

            # ---------------------------------------------------------
            # Finalize Cycle
            # ---------------------------------------------------------
            duration = (datetime.now() - start_time).total_seconds()
            result["duration_sec"] = round(duration, 2)
            result["message"] += f"Cycle completed in {result['duration_sec']}s."

            self._save_log(result)
            return result

        except Exception as e:
            logger.exception("Pipeline cycle failed")
            result["status"] = "error"
            result["message"] = f"Failed: {str(e)}"
            self._save_log(result)
            return result

    def _save_log(self, result: dict):
        """Save the cycle result to the log file."""
        log_data = []
        if self.log_file.exists():
            try:
                with open(self.log_file, "r") as f:
                    log_data = json.load(f)
            except Exception:
                pass

        # Keep only the last 50 logs
        log_data.insert(0, result)
        log_data = log_data[:50]

        try:
            with open(self.log_file, "w") as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save cycle log: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    orc = PipelineOrchestrator()
    print("\n=== Running Pipeline Cycle (Auto Mode) ===")
    res = orc.run_cycle(source_mode="auto")
    print(f"\nResult: {json.dumps(res, indent=2)}")
