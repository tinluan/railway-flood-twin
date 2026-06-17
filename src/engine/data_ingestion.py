"""
src/engine/data_ingestion.py — Rainfall Ingestor (Layer 2: Bridge)
===================================================================
Handles the first step of the 15-minute operational cycle:
fetching or simulating rainfall intensity data for the railway corridor.

Architecture Position (Layer 2 — Bridge):
    - Produces: data/raw/rainfall_Ligne_400.csv
    - Consumed by: ``src/engine/swi_calculator.py`` (SWI calculation)
    - Orchestrated by: ``src/api/routers/engine.py`` (POST /api/v1/engine/cycle)

Class: RainfallIngestor
    Dual-mode class:
      1. Live mode  — ``fetch_live_data()``   → calls Météo-France / OpenWeatherMap API
      2. Demo mode  — ``generate_demo_scenario()`` → synthetic 48-hour flash-flood event

Output File (data/raw/rainfall_Ligne_400.csv):
    | Column          | Type   | Description                  |
    |-----------------|--------|------------------------------|
    | timestamp       | str    | ISO datetime of observation  |
    | intensity_mm_h  | float  | Rainfall rate (mm per hour)  |
    | source          | str    | "DEMO_SCENARIO" or "API_LIVE"|

Database / File Relationship:
    READS:   nothing (source of truth for raw rainfall)
    WRITES:  data/raw/rainfall_<corridor_id>.csv
    NEXT:    src/engine/swi_calculator.py reads that CSV to compute SWI

Example Usage:
    # 1. Generate a synthetic high-intensity flash-flood for demonstration:
    from src.engine.data_ingestion import RainfallIngestor
    ingestor = RainfallIngestor(corridor_id="Ligne_400")
    df = ingestor.generate_demo_scenario(intensity="high")
    # df has 48 rows with random 25-45 mm/h peak between hours 18-30.

    # 2. Fetch live data (stub — replace body with real API call):
    live = ingestor.fetch_live_data()
    # Returns: {"timestamp": datetime.now(), "intensity": 1.5, "source": "API_LIVE"}

    # 3. Run from terminal to seed raw data:
    #    python src/engine/data_ingestion.py
    #    → Saves: data/raw/rainfall_Ligne_400.csv
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import random
import sys

# Import our central path manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import RAW_DATA, STAGING_DATA

class RainfallIngestor:
    """Handles both live API fetching and historical demo simulations."""
    
    def __init__(self, corridor_id="Ligne_400"):
        self.corridor_id = corridor_id
        self.output_file = RAW_DATA / f"rainfall_{corridor_id}.csv"

    def fetch_live_data(self):
        """Placeholder for OpenWeatherMap / Météo-France API integration."""
        # In a real scenario, this would use 'requests' to fetch JSON
        print(f"Fetching live data for {self.corridor_id}...")
        now = datetime.now()
        # Mocking 1.5mm/h rain
        return {"timestamp": now, "intensity": 1.5, "source": "API_LIVE"}

    def generate_demo_scenario(self, intensity="high"):
        """Creates a synthetic rainfall event for contest demonstration."""
        print(f"Generating '{intensity}' intensity scenario...")
        data = []
        base_time = datetime.now() - timedelta(hours=24)
        
        for i in range(48): # 48 hours of data
            time = base_time + timedelta(hours=i)
            # Sigmoid-like peak in the middle
            if 18 < i < 30 and intensity == "high":
                rain = random.uniform(25.0, 45.0) # Flash flood peak
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

if __name__ == "__main__":
    ingestor = RainfallIngestor()
    # For the contest, we run the high intensity demo
    ingestor.generate_demo_scenario(intensity="high")
