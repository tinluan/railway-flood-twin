import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.paths import paths
from src.engine.swi_calculator import SWICalculator
from src.engine.fragility_curves import FragilityEvaluator

def run_sensitivity_analysis():
    print("Running OAT Sensitivity Analysis...")
    
    # Base scenario: 100mm storm over 4 hours
    rainfall = [0]*10 + [25, 25, 25, 25] + [0]*10
    
    # We will test sensitivity of:
    # 1. Peak SWI to half_life (8, 10, 12 days)
    # 2. Peak Runoff Coeff to SWI_mid (120, 150, 180 mm)
    # 3. P_failure to median_depth (0.24, 0.30, 0.36 m) at fixed 0.30m water depth
    
    results = []
    
    # 1. Half-Life Sensitivity
    base_half_life = 10
    for hl in [8, 10, 12]:
        calc = SWICalculator(half_life_days=hl)
        swi_vals = calc.compute_swi_recursive(rainfall)
        peak_swi = max(swi_vals)
        results.append({
            "Parameter": "Half-Life (days)",
            "Variation": f"{hl} ({(hl/base_half_life - 1)*100:+.0f}%)",
            "Target Metric": "Peak SWI (mm)",
            "Metric Value": round(peak_swi, 1)
        })
        
    # 2. SWI Midpoint Sensitivity
    base_swi_mid = 150
    test_swi = 100 # Evaluate at 100mm SWI
    for mid in [120, 150, 180]:
        calc = SWICalculator()
        calc.SWI_mid = mid
        runoff = calc.calculate_runoff_coefficient(test_swi)
        results.append({
            "Parameter": "SWI Midpoint (mm)",
            "Variation": f"{mid} ({(mid/base_swi_mid - 1)*100:+.0f}%)",
            "Target Metric": "Runoff Coeff @ SWI=100",
            "Metric Value": round(runoff, 3)
        })
        
    # 3. Fragility Median Sensitivity
    base_median = 0.30
    test_depth = 0.30 # Evaluate at 30cm depth
    for med in [0.24, 0.30, 0.36]:
        evaluator = FragilityEvaluator()
        evaluator.median_depth = med
        p_fail = evaluator.calculate_p_failure(test_depth)
        results.append({
            "Parameter": "Fragility Median (m)",
            "Variation": f"{med:.2f} ({(med/base_median - 1)*100:+.0f}%)",
            "Target Metric": "P_fail @ depth=0.30m",
            "Metric Value": round(p_fail, 3)
        })
        
    df = pd.DataFrame(results)
    
    paths.ensure_directories()
    out_path = paths.REPORT_TABLES / "Table02_Sensitivity_Analysis.csv"
    df.to_csv(out_path, index=False)
    
    print(df)
    print(f"\nSensitivity analysis saved to {out_path}")

if __name__ == "__main__":
    run_sensitivity_analysis()
