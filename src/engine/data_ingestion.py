"""
src/engine/data_ingestion.py — Rainfall Ingestor (Layer 2: Bridge)
===================================================================
Handles the first step of the 15-minute operational cycle:
fetching or simulating rainfall intensity data for the railway corridor.

Architecture Position (Layer 2 — Bridge):
    - Produces: data/raw/rainfall_Ligne_400.csv       (demo scenario)
                data/raw/rainfall_Ligne_400_live.csv   (live API data)
    - Consumed by: ``src/engine/swi_calculator.py`` (SWI calculation)
    - Orchestrated by: ``src/engine/pipeline_orchestrator.py``

Class: RainfallIngestor
    Tri-mode class:
      1. Live mode   — ``fetch_live_forecast()``     → calls Open-Meteo via RainfallProvider
      2. Demo mode   — ``generate_demo_scenario()``  → synthetic 48-hour flash-flood event
      3. Auto mode   — ``get_active_rainfall()``     → returns whichever source is freshest

Output File (data/raw/rainfall_Ligne_400.csv):
    | Column          | Type   | Description                  |
    |-----------------|--------|------------------------------|
    | timestamp       | str    | ISO datetime of observation  |
    | intensity_mm_h  | float  | Rainfall rate (mm per hour)  |
    | source          | str    | "DEMO_SCENARIO" or "OPEN_METEO_*" |

Database / File Relationship:
    READS:   nothing (source of truth for raw rainfall)
    WRITES:  data/raw/rainfall_<corridor_id>.csv
             data/raw/rainfall_<corridor_id>_live.csv
    NEXT:    src/engine/swi_calculator.py reads that CSV to compute SWI

Example Usage:
    # 1. Generate a synthetic high-intensity flash-flood for demonstration:
    from src.engine.data_ingestion import RainfallIngestor
    ingestor = RainfallIngestor(corridor_id="Ligne_400")
    df = ingestor.generate_demo_scenario(intensity="high")
    # df has 48 rows with random 25-45 mm/h peak between hours 18-30.

    # 2. Fetch live forecast from Open-Meteo API:
    df_live = ingestor.fetch_live_forecast()
    # Saves to data/raw/rainfall_Ligne_400_live.csv

    # 3. Get whichever rainfall source is most recent:
    path, source = ingestor.get_active_rainfall()
    # Returns (Path, "live" or "demo")

    # 4. Fetch live data (legacy stub — now wraps fetch_live_forecast):
    live = ingestor.fetch_live_data()
    # Returns: {"timestamp": datetime.now(), "intensity": 1.5, "source": "API_LIVE"}

    # 5. Run from terminal to seed raw data:
    #    python src/engine/data_ingestion.py
    #    → Saves: data/raw/rainfall_Ligne_400.csv
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional
import random
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import our central path manager
from src.utils.paths import paths

logger = logging.getLogger(__name__)


class RainfallIngestor:
    """Handles both live API fetching and historical demo simulations."""

    def __init__(self, corridor_id="Ligne_400"):
        self.corridor_id = corridor_id
        self.output_file = paths.RAW / f"rainfall_{corridor_id}.csv"
        self.live_file = paths.RAW / f"rainfall_{corridor_id}_live.csv"

    # ------------------------------------------------------------------
    # Live API Mode (Open-Meteo)
    # ------------------------------------------------------------------
    def fetch_live_forecast(self, include_history: bool = True) -> pd.DataFrame:
        """
        Fetch real-time rainfall forecast from Open-Meteo API.

        Uses the RainfallProvider to fetch hourly rain + showers data,
        then saves it in the format expected by the SWI calculator.

        Args:
            include_history: If True, includes 7 days of historical data
                             for SWI warm-up.

        Returns:
            DataFrame with columns: timestamp, intensity_mm_h, source
        """
        from src.engine.rainfall_provider import RainfallProvider

        try:
            # Load config if available
            try:
                from src.config.settings import CORRIDOR_LAT, CORRIDOR_LON
                provider = RainfallProvider(lat=CORRIDOR_LAT, lon=CORRIDOR_LON)
            except ImportError:
                provider = RainfallProvider()

            df = provider.fetch_forecast(include_history=include_history)

            # Save to the live file
            df.to_csv(self.live_file, index=False)
            logger.info("Live rainfall saved to %s (%d records)", self.live_file, len(df))
            print(f"Live forecast saved to {self.live_file} ({len(df)} records)")

            return df

        except Exception as e:
            logger.error("Failed to fetch live forecast: %s", e)
            print(f"ERROR: Failed to fetch live forecast: {e}")
            print("Falling back to existing demo data.")
            # Return the demo file if it exists
            if self.output_file.exists():
                return pd.read_csv(self.output_file)
            raise

    def fetch_live_data(self):
        """
        Placeholder for OpenWeatherMap / Météo-France API integration.

        Legacy method — preserved for backward compatibility.
        For full forecast, use fetch_live_forecast() instead.
        """
        # In a real scenario, this would use 'requests' to fetch JSON
        print(f"Fetching live data for {self.corridor_id}...")

        try:
            from src.engine.rainfall_provider import RainfallProvider
            provider = RainfallProvider()
            current = provider.fetch_current()
            return {
                "timestamp": current["timestamp"],
                "intensity": current["intensity_mm_h"],
                "source": "API_LIVE",
            }
        except Exception as e:
            # Fallback to original mock
            logger.warning(f"Legacy live fetch failed, returning mock data. Error: {e}")
            now = datetime.now()
            return {"timestamp": now, "intensity": 1.5, "source": "FALLBACK_MOCK"}

    # ------------------------------------------------------------------
    # Demo Mode (Synthetic)
    # ------------------------------------------------------------------
    def generate_demo_scenario(self, intensity="high"):
        """Creates a synthetic rainfall event for contest demonstration."""
        print(f"Generating '{intensity}' intensity scenario...")
        data = []
        base_time = datetime.now() - timedelta(hours=24)

        for i in range(48):  # 48 hours of data
            time = base_time + timedelta(hours=i)
            # Sigmoid-like peak in the middle
            if 18 < i < 30 and intensity == "high":
                rain = random.uniform(25.0, 45.0)  # Flash flood peak
            else:
                rain = random.uniform(0.0, 5.0)

            data.append({
                "timestamp": time,
                "intensity_mm_h": round(rain, 2),
                "source": "DEMO_SCENARIO"
            })

        df = pd.DataFrame(data)
        df.to_csv(self.output_file, index=False)
        print(f"Demo data saved to {self.output_file}")
        return df

    # ------------------------------------------------------------------
    # Source Selection
    # ------------------------------------------------------------------
    def get_active_rainfall(self) -> Tuple[Path, str]:
        """
        Return the path to the most recent rainfall data file.

        Returns:
            Tuple of (file_path, source_label).
            source_label is "live" if the live file is newer, else "demo".
        """
        demo_exists = self.output_file.exists()
        live_exists = self.live_file.exists()

        if live_exists and demo_exists:
            # Compare modification times
            live_mtime = self.live_file.stat().st_mtime
            demo_mtime = self.output_file.stat().st_mtime
            if live_mtime > demo_mtime:
                return self.live_file, "live"
            return self.output_file, "demo"
        elif live_exists:
            return self.live_file, "live"
        elif demo_exists:
            return self.output_file, "demo"
        else:
            raise FileNotFoundError(
                f"No rainfall data found. Expected at:\n"
                f"  Demo: {self.output_file}\n"
                f"  Live: {self.live_file}"
            )

    def get_rainfall_summary(self) -> dict:
        """Return a summary of available rainfall data sources."""
        result = {
            "demo_file": str(self.output_file),
            "demo_exists": self.output_file.exists(),
            "live_file": str(self.live_file),
            "live_exists": self.live_file.exists(),
            "active_source": None,
        }

        if self.live_file.exists():
            mtime = datetime.fromtimestamp(self.live_file.stat().st_mtime)
            result["live_last_updated"] = mtime.isoformat()
            result["live_age_minutes"] = round(
                (datetime.now() - mtime).total_seconds() / 60, 1
            )

        try:
            _, source = self.get_active_rainfall()
            result["active_source"] = source
        except FileNotFoundError:
            pass

        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingestor = RainfallIngestor()

    # For the contest, we run the high intensity demo
    ingestor.generate_demo_scenario(intensity="high")

    # Also test live fetch
    print("\n--- Testing Live Forecast Fetch ---")
    try:
        df = ingestor.fetch_live_forecast()
        print(f"Live data: {len(df)} records")
        print(f"Peak: {df['intensity_mm_h'].max():.1f} mm/h")
    except Exception as e:
        print(f"Live fetch failed (expected if no internet): {e}")

    # Summary
    print(f"\nRainfall summary: {ingestor.get_rainfall_summary()}")
