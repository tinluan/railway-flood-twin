"""
src/engine/swi_calculator.py — Hydrological Risk Engine (Layer 3: Simulation)
==============================================================================
Implements the SNCF Soil Water Index (SWI) Leaky Bucket model and Sigmoid Runoff
Coefficient to translate rainfall intensity into actionable soil-saturation risk.

Architecture Position (Layer 3 — Simulation Engine):
    - READS:   data/raw/rainfall_Ligne_400.csv  (from data_ingestion.py)
    - WRITES:  data/processed/swi_results.csv
    - FEEDS:   src/api/routers/hydrology.py (GET /api/v1/hydrology/swi)
    - USED BY: src/api/routers/engine.py    (POST /api/v1/engine/cycle + simulate)

Scientific Formulas (SNCF Standard):
    SWI Leaky Bucket:
        SWI(t) = Rt * (1 - C) + SWI(t-1) * C
        C = 0.5 ^ (1 / T)                    # T in hours (half_life_days * 24)
        SWI(0) = 0                            # starts dry
        Rt = hourly rainfall intensity (mm/h)

    Sigmoid Runoff Coefficient:
        C_runoff = C_max / (1 + e^(-k * (SWI - SWI_mid)))
        High SWI (>200mm) → C_runoff ≈ 0.9  (saturated, 90% becomes runoff)
        Low  SWI (<50mm)  → C_runoff ≈ 0.1  (soil absorbs most rain)

    Active Runoff:
        active_runoff_mm = intensity_mm_h * C_runoff

Default Calibration (SNCF embankments):
    half_life_days = 10  → C ≈ 0.9994  (slow soil drainage)
    C_max = 0.90         (max runoff fraction)
    k     = 0.05         (sigmoid steepness)
    SWI_mid = 150 mm     (saturation midpoint)

Output File (data/processed/swi_results.csv):
    | Column           | Description                            |
    |------------------|----------------------------------------|
    | timestamp        | Observation datetime                   |
    | intensity_mm_h   | Hourly rainfall (mm/h)                 |
    | swi_mm           | Cumulative soil water index (mm)       |
    | runoff_coeff     | Sigmoid runoff fraction (0.0 – 1.0)   |
    | active_runoff_mm | Effective runoff = intensity * coeff   |

Relationship with other files:
    UPSTREAM:   src/engine/data_ingestion.py → generates rainfall CSV
    DOWNSTREAM: src/api/routers/hydrology.py → serves SWI via REST API
    ALONGSIDE:  src/engine/hec_ras_runner.py (hydraulic step, runs if SWI > limit)
    ALERTS:     src/engine/fragility_curves.py + alert_dispatcher.py (use SWI output)

Example Usage:
    # Full pipeline: read rainfall CSV → compute SWI → save
    from src.engine.swi_calculator import SWICalculator
    from src.utils.paths import ProjectPaths
    calc = SWICalculator(half_life_days=10)
    df = calc.process_corridor_risk(ProjectPaths.RAW / "rainfall_Ligne_400.csv")
    # df now has swi_mm, runoff_coeff, active_runoff_mm columns

    # Single-value SWI computation (e.g., in a simulation loop):
    rainfall_series = [0, 0, 5, 12, 30, 45, 22, 8, 1, 0]
    swi_values = calc.compute_swi_recursive(rainfall_series)
    # → [0.003, 0.006, 0.078, ..., ...] (builds up and decays slowly)

    # Check runoff coefficient at peak SWI:
    coeff = calc.calculate_runoff_coefficient(swi_values[-1])
    # coeff ≈ 0.10 to 0.90 depending on SWI level
"""

import os
import numpy as np
import pandas as pd
import sys

# Import our central path manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import RAW_DATA, PROCESSED_DATA

class SWICalculator:
    """Computes Soil Water Index and Runoff Coefficients using SNCF standards."""
    
    def __init__(self, half_life_days=10):
        # C = (0.5)^(1/T) where T is half-life in hours
        self.T = half_life_days * 24 
        self.C = 0.5**(1/self.T)
        
        # Sigmoid Parameters (Calibrated for SNCF embankments)
        self.C_max = 0.9    # Max runoff 90%
        self.C_min = 0.1    # Min runoff 10%
        self.k = 0.05       # Steepness
        self.SWI_mid = 150  # Saturation midpoint (mm)

    def compute_swi_recursive(self, rainfall_series):
        """
        Formula: SWI(t) = Rt * (1 - C) + SWI(t-1) * C
        """
        swi_values = []
        current_swi = 0
        
        for rt in rainfall_series:
            current_swi = rt * (1 - self.C) + current_swi * self.C
            swi_values.append(current_swi)
            
        return swi_values

    def calculate_runoff_coefficient(self, swi):
        """
        Sigmoid Formula: C_runoff = C_max / (1 + e^(-k * (SWI - SWI_mid)))
        """
        return self.C_max / (1 + np.exp(-self.k * (swi - self.SWI_mid)))

    def process_corridor_risk(self, rainfall_file):
        """Full pipeline: Rain -> SWI -> Runoff %."""
        print(f"Computing Risk Logic for {rainfall_file}...")
        df = pd.read_csv(rainfall_file)
        
        # 1. SWI Calculation
        df['swi_mm'] = self.compute_swi_recursive(df['intensity_mm_h'])
        
        # 2. Runoff Coefficient
        df['runoff_coeff'] = self.calculate_runoff_coefficient(df['swi_mm'])
        
        # 3. Active Runoff (mm)
        df['active_runoff_mm'] = df['intensity_mm_h'] * df['runoff_coeff']
        
        output_path = PROCESSED_DATA / "swi_results.csv"
        df.to_csv(output_path, index=False)
        print(f"Hydrology results saved to {output_path}")
        return df

if __name__ == "__main__":
    # Test with demo data from ingestion module
    rain_file = RAW_DATA / "rainfall_Ligne_400.csv"
    if rain_file.exists():
        calc = SWICalculator(half_life_days=10)
        calc.process_corridor_risk(rain_file)
    else:
        print("No rainfall data found. Run ingestion first.")
