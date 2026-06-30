"""
src/engine/fragility_curves.py — Fragility Evaluator (Layer 4: Vulnerability & Alert)
========================================================================================
Converts hydraulic output (water depth at an asset) into a structural Probability of
Failure (P_failure) using a log-normal fragility curve.

Scientific Calibration Source:
    Tsubaki, R., Bricker, J.D., Ichii, K., & Kawahara, Y. (2016).
    "Development of fragility curves for railway embankment and ballast scour
     due to overtopping flood flow."
    Nat. Hazards Earth Syst. Sci., 16, 2455–2472.
    doi:10.5194/nhess-16-2455-2016

    Key findings from Tsubaki et al. (2016):
    - Ballast scour only:    median Δh = 0.30 m, σ = 0.035 m (normal), n=15 samples
    - Embankment scour:      median Δh = 0.22 m, σ = 0.15  m (log-normal), n=31 samples
    - Combined (bal.+emb.):  median Δh = 0.22 m, σ = 0.15  m (log-normal), n=31 samples
    - "The fragility curve for ballast and embankment scour is the most feasible"
      (Section 5.3, p. 2465)

Architecture Position (Layer 4 — Vulnerability & Alert):
    - RECEIVES:  water_depth_m (from HEC-RAS WSE minus terrain elevation)
    - PRODUCES:  p_failure (0.0–1.0) and risk category (LOW/MEDIUM/HIGH)
    - USED BY:   ``src/engine/alert_dispatcher.py`` (to generate RAMS verdicts)
    - USED BY:   ``src/api/routers/alerts.py``      (GET /api/v1/alerts/current)
    - USED BY:   ``src/api/routers/engine.py``      (POST /api/v1/engine/simulate)

Fragility Model — Log-Normal CDF:
    P_failure = Φ( ln(depth / median_depth) / sigma )
    Where:
      Φ            = standard normal CDF (scipy.stats.norm.cdf)
      median_depth = calibration-dependent (see FRAGILITY_MODES)
      sigma        = calibration-dependent (see FRAGILITY_MODES)

Available Fragility Modes:
    "ballast_only"  — Tsubaki (2016): median=0.30m, σ=0.035  (steep, conservative)
    "combined"      — Tsubaki (2016): median=0.22m, σ=0.15   (recommended by paper)
    "conservative"  — Original SNCF-DT: median=0.30m, σ=0.40 (gradual, for screening)

RAMS Risk Categories (SNCF thresholds):
    P_failure < 0.20  → LOW     → GREEN  (Standby / Standard Speed)
    P_failure 0.20–0.50 → MEDIUM → YELLOW (Speed Restriction: 60 km/h)
    P_failure > 0.50  → HIGH   → RED    (Emergency Halt / ETCS Stop)

Relationship with other files:
    UPSTREAM:  hec_ras_runner.py / hecras_bridge.py → provides WSE
               preprocessor.py   → provides z_terrain, z_ballast
               water_depth = WSE - z_terrain  (computed by caller)
    DOWNSTREAM: alert_dispatcher.py → translates P to RAMS directive
    DATABASE:  z_config.json contains z_ballast per asset (for verdict override)

Example Usage:
    from src.engine.fragility_curves import FragilityEvaluator

    # Use the Tsubaki (2016) combined curve (recommended):
    evaluator = FragilityEvaluator(mode="combined")

    # Compute probability for a single observed depth:
    p = evaluator.calculate_p_failure(water_depth_m=0.25)
    # → p ≈ 0.77  (HIGH risk)

    # Compare all modes:
    for mode in FragilityEvaluator.FRAGILITY_MODES:
        ev = FragilityEvaluator(mode=mode)
        p = ev.calculate_p_failure(0.25)
        print(f"{mode:20s} | P={p*100:.1f}%")
"""

import numpy as np
from scipy.stats import norm

# ---------------------------------------------------------------------------
# Fragility Mode Registry — each mode is a calibration source
# ---------------------------------------------------------------------------
FRAGILITY_MODES = {
    "ballast_only": {
        "median_depth": 0.30,
        "sigma": 0.035,
        "citation": "Tsubaki et al. (2016), ballast scour only, n=15, MLE fit",
        "description": "Steep curve — triggers alert at very shallow overtopping",
    },
    "combined": {
        "median_depth": 0.22,
        "sigma": 0.15,
        "citation": "Tsubaki et al. (2016), combined ballast+embankment, n=31, MLE fit",
        "description": "Recommended by Tsubaki — most feasible for field application",
    },
    "conservative": {
        "median_depth": 0.30,
        "sigma": 0.40,
        "citation": "Original SNCF-DT screening curve (uncalibrated)",
        "description": "Gradual transition — suitable for low-confidence screening only",
    },
}


class FragilityEvaluator:
    """Calculates Probability of Failure based on water depth using log-normal fragility.

    Args:
        mode: One of 'ballast_only', 'combined', or 'conservative'.
              Default is 'combined' (Tsubaki 2016 recommendation).
    """

    FRAGILITY_MODES = FRAGILITY_MODES  # expose at class level for iteration

    def __init__(self, mode: str = "combined"):
        if mode not in FRAGILITY_MODES:
            raise ValueError(
                f"Unknown fragility mode '{mode}'. "
                f"Choose from: {list(FRAGILITY_MODES.keys())}"
            )
        cfg = FRAGILITY_MODES[mode]
        self.mode = mode
        self.median_depth = cfg["median_depth"]
        self.sigma = cfg["sigma"]
        self.citation = cfg["citation"]

    def calculate_p_failure(self, water_depth_m):
        """
        Calculates the probability of ballast/embankment failure (0.0 to 1.0).

        Formula: P = Φ( ln(depth / median) / σ )
        Source:  Tsubaki et al. (2016), Eq. (2), p. 2460
        """
        if water_depth_m <= 0:
            return 0.0

        # Log-normal CDF
        p = norm.cdf(np.log(water_depth_m / self.median_depth) / self.sigma)
        return round(float(p), 3)

    def get_risk_category(self, p_failure):
        """Maps probability to RAMS risk classes."""
        if p_failure < 0.20:
            return "LOW"
        elif 0.20 <= p_failure <= 0.50:
            return "MEDIUM"
        else:
            return "HIGH"

    def __repr__(self):
        return (
            f"FragilityEvaluator(mode='{self.mode}', "
            f"median={self.median_depth}m, sigma={self.sigma}, "
            f"cite='{self.citation}')"
        )


if __name__ == "__main__":
    print("=" * 72)
    print("Fragility Curve Comparison — All Modes")
    print("=" * 72)

    test_depths = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]

    # Header
    modes = list(FRAGILITY_MODES.keys())
    header = f"{'Depth (m)':>10}"
    for m in modes:
        header += f" | {m:>16}"
    print(header)
    print("-" * len(header))

    for d in test_depths:
        row = f"{d:>10.2f}"
        for m in modes:
            ev = FragilityEvaluator(mode=m)
            p = ev.calculate_p_failure(d)
            cat = ev.get_risk_category(p)
            row += f" | {p*100:>6.1f}% {cat:>6}"
        print(row)

    print()
    for m in modes:
        cfg = FRAGILITY_MODES[m]
        print(f"  [{m}] {cfg['citation']}")
        print(f"    median={cfg['median_depth']}m, σ={cfg['sigma']}")
        print()
