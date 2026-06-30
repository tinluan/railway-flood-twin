"""
report/generate_figures.py — Scientific Figure Generator for Thesis Report
===========================================================================
Generates all validation and comparison figures required by the weakness
remediation plan. Each figure is publication-quality (300 DPI, proper labels).

Figures generated:
    Fig06: SWI Sensitivity to Half-Life T
    Fig07: Fragility Curve Comparison (3 modes vs Tsubaki 2016)
    Fig08: Historical Storm Replay (Cévenol scenario through full pipeline)
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

FIGURE_DIR = Path(__file__).parent / "figures"
FIGURE_DIR.mkdir(exist_ok=True)


# ===================================================================
# Fig 06: SWI Sensitivity Analysis — Half-life T
# ===================================================================
def generate_fig06_swi_sensitivity():
    """
    Shows how the peak SWI varies with the half-life parameter T
    for the Cévenol storm scenario (40.9 mm/h peak at T+15h).
    """
    from src.engine.swi_calculator import SWICalculator

    # Simulate a Cévenol storm: 48h with peak at hour 15
    rainfall = np.zeros(48)
    for i in range(48):
        if 12 <= i <= 18:
            rainfall[i] = 30.0 + 10.0 * np.exp(-0.5 * ((i - 15) / 1.5) ** 2)
        elif 8 <= i <= 22:
            rainfall[i] = np.random.uniform(2.0, 8.0)
        else:
            rainfall[i] = np.random.uniform(0.0, 2.0)

    # Test range of T values
    T_values = [3, 5, 7, 10, 15, 20, 30, 45, 60]
    peak_swi = []
    trigger_count = []
    peak_runoff = []

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Fig. 6: SWI Sensitivity to Half-Life Parameter T\n"
                 "(Cévenol Storm Scenario, Peak ≈ 40.9 mm/h)",
                 fontsize=14, fontweight='bold')

    # Panel A: SWI curves for different T
    ax_swi = axes[0, 0]
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(T_values)))
    for T, color in zip(T_values, colors):
        calc = SWICalculator(half_life_days=T)
        swi = calc.compute_swi_recursive(rainfall)
        peak_swi.append(max(swi))
        trigger_count.append(sum(1 for s in swi if s > 100))
        peak_runoff.append(calc.calculate_runoff_coefficient(max(swi)))
        ax_swi.plot(range(48), swi, color=color, label=f"T={T}d", linewidth=1.5)

    ax_swi.axhline(y=100, color='red', linestyle='--', alpha=0.7, label='Trigger (100mm)')
    ax_swi.set_xlabel("Time (hours)")
    ax_swi.set_ylabel("SWI (mm)")
    ax_swi.set_title("(a) SWI Accumulation Curves")
    ax_swi.legend(fontsize=7, ncol=2)
    ax_swi.grid(True, alpha=0.3)

    # Panel B: Peak SWI vs T
    ax_peak = axes[0, 1]
    ax_peak.bar(range(len(T_values)), peak_swi, color=colors, edgecolor='black')
    ax_peak.set_xticks(range(len(T_values)))
    ax_peak.set_xticklabels([str(t) for t in T_values])
    ax_peak.set_xlabel("Half-Life T (days)")
    ax_peak.set_ylabel("Peak SWI (mm)")
    ax_peak.set_title("(b) Peak SWI vs Half-Life")
    ax_peak.axhline(y=100, color='red', linestyle='--', alpha=0.7)
    # Highlight T=10
    idx_10 = T_values.index(10)
    ax_peak.bar(idx_10, peak_swi[idx_10], color='red', edgecolor='black', alpha=0.8)
    ax_peak.annotate(f"T=10d\n{peak_swi[idx_10]:.1f}mm",
                     xy=(idx_10, peak_swi[idx_10]),
                     xytext=(idx_10+1.5, peak_swi[idx_10]*0.8),
                     arrowprops=dict(arrowstyle='->', color='red'),
                     fontsize=9, color='red', fontweight='bold')
    ax_peak.grid(True, alpha=0.3)

    # Panel C: Rainfall input
    ax_rain = axes[1, 0]
    ax_rain.bar(range(48), rainfall, color='steelblue', alpha=0.8, edgecolor='navy')
    ax_rain.set_xlabel("Time (hours)")
    ax_rain.set_ylabel("Rainfall Intensity (mm/h)")
    ax_rain.set_title("(c) Cévenol Storm Hyetograph")
    ax_rain.grid(True, alpha=0.3)

    # Panel D: Summary table
    ax_table = axes[1, 1]
    ax_table.axis('off')
    table_data = []
    for i, T in enumerate(T_values):
        table_data.append([
            f"{T}",
            f"{peak_swi[i]:.1f}",
            f"{trigger_count[i]}",
            f"{peak_runoff[i]:.3f}",
        ])
    table = ax_table.table(
        cellText=table_data,
        colLabels=["T (days)", "Peak SWI (mm)", "Hours > 100mm", "Peak C_runoff"],
        loc='center',
        cellLoc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    # Highlight T=10 row
    for col in range(4):
        table[idx_10 + 1, col].set_facecolor('#ffcccc')
    ax_table.set_title("(d) Sensitivity Summary", fontsize=11, fontweight='bold')

    plt.tight_layout()
    out_path = FIGURE_DIR / "Fig06_SWI_Sensitivity_T.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")
    return out_path


# ===================================================================
# Fig 07: Fragility Curve Comparison — 3 Modes
# ===================================================================
def generate_fig07_fragility_comparison():
    """
    Compares the three fragility curve modes against each other
    and shows how RAMS alert zones shift between calibrations.
    """
    from src.engine.fragility_curves import FragilityEvaluator, FRAGILITY_MODES

    depths = np.linspace(0.01, 0.80, 200)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Fig. 7: Fragility Curve Comparison\n"
                 "Current Model vs. Tsubaki et al. (2016) Field-Calibrated Curves",
                 fontsize=13, fontweight='bold')

    # Panel A: Full curves
    ax = axes[0]
    mode_styles = {
        "ballast_only": ("tab:green", "-.", "Ballast Only\n(Tsubaki, σ=0.035)"),
        "combined": ("tab:blue", "-", "Combined Bal.+Emb.\n(Tsubaki, σ=0.15)"),
        "conservative": ("tab:red", "--", "Original SNCF-DT\n(Uncalibrated, σ=0.40)"),
    }

    for mode, (color, ls, label) in mode_styles.items():
        ev = FragilityEvaluator(mode=mode)
        p_vals = [ev.calculate_p_failure(d) for d in depths]
        ax.plot(depths * 100, p_vals, color=color, linestyle=ls, linewidth=2.5, label=label)

    # RAMS zones
    ax.axhspan(0.0, 0.20, alpha=0.08, color='green', label='GREEN (P<20%)')
    ax.axhspan(0.20, 0.50, alpha=0.08, color='gold', label='YELLOW (20-50%)')
    ax.axhspan(0.50, 1.0, alpha=0.08, color='red', label='RED (P>50%)')
    ax.axhline(y=0.20, color='gold', linestyle=':', alpha=0.5)
    ax.axhline(y=0.50, color='red', linestyle=':', alpha=0.5)

    ax.set_xlabel("Overtopping Water Depth (cm)", fontsize=11)
    ax.set_ylabel("Probability of Failure P(f)", fontsize=11)
    ax.set_title("(a) Log-Normal Fragility Curves", fontsize=11)
    ax.legend(fontsize=8, loc='lower right')
    ax.set_xlim(0, 80)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)

    # Panel B: Alert trigger depth comparison
    ax2 = axes[1]
    thresholds = {"P=20% (YELLOW)": 0.20, "P=50% (RED)": 0.50}
    modes_list = list(mode_styles.keys())
    x_pos = np.arange(len(modes_list))
    width = 0.35

    for i, (thresh_name, thresh_val) in enumerate(thresholds.items()):
        trigger_depths = []
        for mode in modes_list:
            ev = FragilityEvaluator(mode=mode)
            # Binary search for the depth that gives thresh_val
            lo, hi = 0.001, 2.0
            for _ in range(50):
                mid = (lo + hi) / 2
                if ev.calculate_p_failure(mid) < thresh_val:
                    lo = mid
                else:
                    hi = mid
            trigger_depths.append(mid * 100)  # in cm

        color = 'gold' if i == 0 else 'red'
        bars = ax2.bar(x_pos + i * width, trigger_depths, width,
                       label=thresh_name, color=color, edgecolor='black', alpha=0.8)
        for bar, val in zip(bars, trigger_depths):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                     f"{val:.1f}cm", ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax2.set_xticks(x_pos + width / 2)
    ax2.set_xticklabels(["Ballast Only\n(Tsubaki)", "Combined\n(Tsubaki)", "Original\n(SNCF-DT)"],
                        fontsize=9)
    ax2.set_ylabel("Trigger Depth (cm)", fontsize=11)
    ax2.set_title("(b) Alert Trigger Depths by Mode", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    out_path = FIGURE_DIR / "Fig07_Fragility_Comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")
    return out_path


# ===================================================================
# Fig 08: Historical Storm Replay (Full Pipeline Proof)
# ===================================================================
def generate_fig08_storm_replay():
    """
    Replays the embedded Cévenol storm scenario through the full SWI pipeline
    and shows the end-to-end response: Rainfall → SWI → Trigger → Runoff.
    """
    from src.engine.swi_calculator import SWICalculator

    # Use the demo scenario data if available, otherwise generate synthetic
    demo_path = Path(__file__).parent.parent / "data" / "raw" / "rainfall_Ligne_400.csv"

    if demo_path.exists():
        import pandas as pd
        df = pd.read_csv(demo_path)
        rainfall = df['intensity_mm_h'].values
        timestamps = df['timestamp'].values
        source = f"Real file: {demo_path.name}"
    else:
        # Generate synthetic Cévenol scenario
        np.random.seed(42)
        rainfall = np.zeros(48)
        for i in range(48):
            if 12 <= i <= 18:
                rainfall[i] = 30.0 + 10.0 * np.exp(-0.5 * ((i - 15) / 1.5) ** 2)
            elif 8 <= i <= 22:
                rainfall[i] = np.random.uniform(2.0, 8.0)
            else:
                rainfall[i] = np.random.uniform(0.0, 2.0)
        timestamps = [f"T+{i}h" for i in range(48)]
        source = "Synthetic Cévenol (seed=42)"

    # Run through SWI calculator
    calc = SWICalculator(half_life_days=10)
    swi_values = calc.compute_swi_recursive(rainfall)
    runoff_coeffs = [calc.calculate_runoff_coefficient(s) for s in swi_values]
    active_runoff = [r * c for r, c in zip(rainfall, runoff_coeffs)]

    # Find trigger point
    trigger_threshold = 100.0
    trigger_hours = [i for i, s in enumerate(swi_values) if s > trigger_threshold]

    fig, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True)
    fig.suptitle("Fig. 8: Historical Storm Replay — Full Pipeline Proof\n"
                 f"Source: {source} | T_half=10d | Trigger=100mm",
                 fontsize=13, fontweight='bold')
    hours = range(len(rainfall))

    # Panel A: Rainfall
    ax = axes[0]
    ax.bar(hours, rainfall, color='steelblue', alpha=0.8, edgecolor='navy')
    ax.set_ylabel("Rainfall\n(mm/h)", fontsize=10)
    ax.set_title("(a) Rainfall Input (Hyetograph)", fontsize=11)
    peak_idx = int(np.argmax(rainfall))
    if rainfall[peak_idx] > 0:
        ax.annotate(f"Peak: {rainfall[peak_idx]:.1f} mm/h\nat T+{peak_idx}h",
                    xy=(peak_idx, rainfall[peak_idx]),
                    xytext=(peak_idx+5, rainfall[peak_idx]*0.9),
                    arrowprops=dict(arrowstyle='->', color='navy'),
                    fontsize=9, fontweight='bold', color='navy')
    ax.grid(True, alpha=0.3)

    # Panel B: SWI
    ax = axes[1]
    ax.fill_between(hours, swi_values, alpha=0.3, color='darkorange')
    ax.plot(hours, swi_values, color='darkorange', linewidth=2)
    ax.axhline(y=trigger_threshold, color='red', linestyle='--', linewidth=1.5,
               label=f'HEC-RAS Trigger ({trigger_threshold}mm)')
    if trigger_hours:
        ax.axvspan(trigger_hours[0], trigger_hours[-1], alpha=0.1, color='red',
                   label=f'HEC-RAS Active ({len(trigger_hours)}h)')
    peak_swi = max(swi_values)
    ax.annotate(f"Peak SWI: {peak_swi:.1f} mm",
                xy=(int(np.argmax(swi_values)), peak_swi),
                xytext=(int(np.argmax(swi_values))+3, peak_swi*0.85),
                arrowprops=dict(arrowstyle='->', color='darkorange'),
                fontsize=9, fontweight='bold', color='darkorange')
    ax.set_ylabel("SWI\n(mm)", fontsize=10)
    ax.set_title("(b) Soil Water Index (Leaky Bucket, T=10 days)", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # Panel C: HEC-RAS trigger indicator
    ax = axes[2]
    trigger_binary = [1 if s > trigger_threshold else 0 for s in swi_values]
    ax.fill_between(hours, trigger_binary, alpha=0.5, color='red', step='mid')
    ax.set_ylabel("HEC-RAS\nTriggered", fontsize=10)
    ax.set_title("(c) HEC-RAS 2D Trigger (SWI > 100mm → Execute)", fontsize=11)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["OFF", "ON"])
    ax.grid(True, alpha=0.3)

    # Panel D: Active Runoff
    ax = axes[3]
    ax.bar(hours, active_runoff, color='darkred', alpha=0.7, edgecolor='darkred')
    ax2 = ax.twinx()
    ax2.plot(hours, runoff_coeffs, color='purple', linewidth=2, linestyle='--',
             label='Runoff Coefficient')
    ax2.set_ylabel("C_runoff", fontsize=10, color='purple')
    ax2.set_ylim(0, 1.0)
    ax2.legend(fontsize=9, loc='upper right')
    ax.set_xlabel("Time (hours)", fontsize=11)
    ax.set_ylabel("Active Runoff\n(mm/h)", fontsize=10)
    ax.set_title("(d) Active Runoff = Rainfall × C_runoff (Sigmoid)", fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = FIGURE_DIR / "Fig08_Historical_Storm_Replay.png"
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")
    return out_path


# ===================================================================
# Main — Generate All Figures
# ===================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Generating Thesis Report Figures")
    print("=" * 60)

    generate_fig06_swi_sensitivity()
    generate_fig07_fragility_comparison()
    generate_fig08_storm_replay()

    print("\nAll figures generated successfully.")
