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
