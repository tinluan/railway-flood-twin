import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.paths import paths
from src.utils.viz import set_academic_style, save_for_report
from src.engine.swi_calculator import SWICalculator
from src.engine.fragility_curves import FragilityEvaluator

# Ensure output directory exists
paths.ensure_directories()

def generate_swi_decay_figure():
    """Generates Figure 2: SWI Half-Life Decay Verification."""
    print("Generating Fig02_SWI_Decay...")
    set_academic_style()
    
    calc = SWICalculator(half_life_days=10)
    
    # Manually start at 100mm and let it decay for 30 days (720 hours)
    swi_values = [100.0]
    for _ in range(30 * 24 - 1):
        swi_values.append(swi_values[-1] * calc.C)
        
    hours = np.arange(len(swi_values))
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(hours, swi_values, label="SWI (mm)", color='#003366')
    
    # Mark half-life points
    ax.axvline(x=240, color='#D95319', linestyle='--', alpha=0.7, label='T=10 days (50%)')
    ax.axhline(y=50, color='#D95319', linestyle='--', alpha=0.7)
    
    ax.axvline(x=480, color='#EDB120', linestyle='--', alpha=0.7, label='T=20 days (25%)')
    ax.axhline(y=25, color='#EDB120', linestyle='--', alpha=0.7)
    
    ax.set_title("SWI Leaky Bucket Decay (Half-Life = 10 Days)")
    ax.set_xlabel("Time (Hours)")
    ax.set_ylabel("Soil Water Index (mm)")
    ax.set_xlim(0, 720)
    ax.set_ylim(0, 105)
    ax.legend()
    
    save_for_report(fig, "Fig02_SWI_Decay")

def generate_sigmoid_curve_figure():
    """Generates Figure 3: Sigmoid Runoff Coefficient Curve."""
    print("Generating Fig03_Sigmoid_Curve...")
    set_academic_style()
    
    calc = SWICalculator()
    swi_range = np.linspace(0, 300, 300)
    runoff = [calc.calculate_runoff_coefficient(s) for s in swi_range]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(swi_range, runoff, label="Runoff Coefficient", color='#7E2F8E', linewidth=3)
    
    # Mark critical points
    ax.axvline(x=150, color='gray', linestyle=':', label='Midpoint (150mm)')
    ax.axhline(y=0.5, color='gray', linestyle=':')
    ax.axhline(y=0.9, color='#D95319', linestyle='--', label='C_max (0.9)', alpha=0.6)
    ax.axhline(y=0.1, color='#003366', linestyle='--', label='C_min (0.1)', alpha=0.6)
    
    ax.set_title("Sigmoid Runoff Coefficient vs. Soil Saturation")
    ax.set_xlabel("Soil Water Index (mm)")
    ax.set_ylabel("Runoff Coefficient (C_runoff)")
    ax.set_xlim(0, 300)
    ax.set_ylim(0, 1.0)
    ax.legend(loc='upper left')
    
    save_for_report(fig, "Fig03_Sigmoid_Curve")

def generate_fragility_curve_figure():
    """Generates Figure 4: Log-Normal Fragility Curve."""
    print("Generating Fig04_Fragility_Curve...")
    set_academic_style()
    
    evaluator = FragilityEvaluator()
    depths = np.linspace(0, 1.0, 200)
    p_fail = [evaluator.calculate_p_failure(d) for d in depths]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(depths, p_fail, label="P(Failure)", color='#003366', linewidth=3)
    
    # Mark RAMS thresholds
    ax.axhline(y=0.2, color='#EDB120', linestyle='--', label='YELLOW Threshold (P=0.20)')
    ax.axhline(y=0.5, color='#D95319', linestyle='--', label='RED Threshold (P=0.50)')
    
    # Mark Median
    ax.axvline(x=0.30, color='gray', linestyle=':', label='Median Depth (0.3m)')
    
    # Add colored background for RAMS zones
    ax.axhspan(0, 0.20, facecolor='#10b981', alpha=0.1) # Green zone
    ax.axhspan(0.20, 0.50, facecolor='#f59e0b', alpha=0.1) # Yellow zone
    ax.axhspan(0.50, 1.0, facecolor='#ef4444', alpha=0.1) # Red zone
    
    ax.set_title("Ballast Scour Fragility Curve (Log-Normal)")
    ax.set_xlabel("Water Depth above Terrain (m)")
    ax.set_ylabel("Probability of Failure (0-1)")
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.05)
    ax.legend(loc='lower right')
    
    save_for_report(fig, "Fig04_Fragility_Curve")

def generate_storm_response_figure():
    """Generates Figure 5: SWI Response to Cévenol Storm."""
    print("Generating Fig05_SWI_Storm_Response...")
    set_academic_style()
    
    swi_file = paths.PROCESSED / "swi_results.csv"
    if not swi_file.exists():
        print(f"[WARNING] Cannot find {swi_file}. Run SWI calculation first.")
        return
        
    df = pd.read_csv(swi_file)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    
    # Top Plot: Rain vs SWI
    ax1.bar(df.index, df['intensity_mm_h'], color='#64748b', alpha=0.5, label='Rainfall (mm/h)')
    
    ax1_twin = ax1.twinx()
    ax1_twin.plot(df.index, df['swi_mm'], color='#003366', linewidth=3, label='SWI (mm)')
    ax1_twin.axhline(y=100, color='#D95319', linestyle='--', label='HEC-RAS Trigger (100mm)')
    
    ax1.set_ylabel("Rainfall (mm/h)", color='#64748b')
    ax1_twin.set_ylabel("Soil Water Index (mm)", color='#003366')
    ax1.set_title("Hydrological Response: Cévenol Storm Scenario")
    
    # Bottom Plot: Runoff Coefficient
    ax2.plot(df.index, df['runoff_coeff'], color='#7E2F8E', linewidth=3, label='Runoff Coeff')
    ax2.fill_between(df.index, 0.1, df['runoff_coeff'], color='#7E2F8E', alpha=0.2)
    ax2.set_ylabel("Runoff Fraction")
    ax2.set_xlabel("Time (Hours)")
    ax2.set_ylim(0, 1.0)
    
    fig.tight_layout()
    save_for_report(fig, "Fig05_SWI_Storm_Response")

if __name__ == "__main__":
    generate_swi_decay_figure()
    generate_sigmoid_curve_figure()
    generate_fragility_curve_figure()
    generate_storm_response_figure()
    print("All validation figures generated successfully!")
