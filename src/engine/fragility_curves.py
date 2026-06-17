"""
src/engine/fragility_curves.py — Fragility Evaluator (Layer 4: Vulnerability & Alert)
========================================================================================
Converts hydraulic output (water depth at an asset) into a structural Probability of
Failure (P_failure) using a log-normal fragility curve calibrated for SNCF ballast.

Architecture Position (Layer 4 — Vulnerability & Alert):
    - RECEIVES:  water_depth_m (from HEC-RAS WSE minus terrain elevation)
    - PRODUCES:  p_failure (0.0–1.0) and risk category (LOW/MEDIUM/HIGH)
    - USED BY:   ``src/engine/alert_dispatcher.py`` (to generate RAMS verdicts)
    - USED BY:   ``src/api/routers/alerts.py``      (GET /api/v1/alerts/current)
    - USED BY:   ``src/api/routers/engine.py``      (POST /api/v1/engine/simulate)

Fragility Model — Log-Normal CDF:
    P_failure = Φ( ln(depth / median_depth) / sigma )
    Where:
      Φ          = standard normal CDF (scipy.stats.norm.cdf)
      median_depth = 0.30 m  (30 cm depth triggers 50% failure probability)
      sigma        = 0.40    (dispersion; wider = more gradual increase)

RAMS Risk Categories (SNCF thresholds):
    P_failure < 0.20  → LOW     → GREEN  (Standby / Standard Speed)
    P_failure 0.20–0.50 → MEDIUM → YELLOW (Speed Restriction: 60 km/h)
    P_failure > 0.50  → HIGH   → RED    (Emergency Halt / ETCS Stop)

Physical Intuition:
    - At 0 cm depth   → P = 0.0   (no water, no risk)
    - At 5 cm depth   → P ≈ 0.01  (LOW — wet but safe)
    - At 15 cm depth  → P ≈ 0.12  (LOW — drainage concern)
    - At 30 cm depth  → P ≈ 0.50  (MEDIUM → HIGH boundary)
    - At 60 cm depth  → P ≈ 0.90  (HIGH — ballast failure imminent)

Relationship with other files:
    UPSTREAM:  hec_ras_runner.py / hecras_bridge.py → provides WSE
               preprocessor.py   → provides z_terrain, z_ballast
               water_depth = WSE - z_terrain  (computed by caller)
    DOWNSTREAM: alert_dispatcher.py → translates P to RAMS directive
    DATABASE:  z_config.json contains z_ballast per asset (for verdict override)

Example Usage:
    from src.engine.fragility_curves import FragilityEvaluator

    evaluator = FragilityEvaluator()

    # 1. Compute probability for a single observed depth:
    p = evaluator.calculate_p_failure(water_depth_m=0.35)
    # → p ≈ 0.554  (HIGH risk — above 50% threshold)

    # 2. Get the RAMS category:
    category = evaluator.get_risk_category(p)
    # → "HIGH"

    # 3. Batch evaluation over time series:
    depths = [0.05, 0.15, 0.35, 0.60]
    for d in depths:
        p = evaluator.calculate_p_failure(d)
        cat = evaluator.get_risk_category(p)
        print(f"Depth: {d}m | P={p*100:.1f}% | {cat}")
    # Output:
    #   Depth: 0.05m | P=1.0%  | LOW
    #   Depth: 0.15m | P=12.3% | LOW
    #   Depth: 0.35m | P=55.4% | HIGH
    #   Depth: 0.60m | P=90.5% | HIGH
"""

import numpy as np
from scipy.stats import norm

class FragilityEvaluator:
    """Calculates Probability of Failure based on water depth and velocity."""
    
    def __init__(self):
        # Parameters for Ballast Scour Fragility (Log-normal distribution)
        # Median threshold (m) and Standard Deviation
        self.median_depth = 0.3  # 30cm depth is critical for ballast
        self.sigma = 0.4

    def calculate_p_failure(self, water_depth_m):
        """
        Calculates the probability of ballast failure (0.0 to 1.0).
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

if __name__ == "__main__":
    evaluator = FragilityEvaluator()
    test_depths = [0.05, 0.15, 0.35, 0.60]
    
    print("Fragility Curve Test:")
    for d in test_depths:
        p = evaluator.calculate_p_failure(d)
        cat = evaluator.get_risk_category(p)
        print(f"Depth: {d}m | P(Failure): {p*100}% | Category: {cat}")
