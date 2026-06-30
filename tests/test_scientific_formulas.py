import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.engine.swi_calculator import SWICalculator
from src.engine.fragility_curves import FragilityEvaluator
from src.engine.alert_dispatcher import AlertDispatcher

# =====================================================================
# 1. SWI Calculator Tests
# =====================================================================

class TestSWICalculator:
    def test_half_life_decay(self):
        """Test that SWI exactly halves after the specified half-life period with zero rainfall."""
        calc = SWICalculator(half_life_days=10)
        
        # Manually compute decay over 240 hours (10 days)
        # Starting with an arbitrary SWI of 100mm
        swi = 100.0
        for _ in range(240):
            swi = 0.0 * (1 - calc.C) + swi * calc.C
            
        # After exactly 1 half-life, it should be 50.0mm
        assert np.isclose(swi, 50.0, rtol=1e-3), f"Expected 50.0, got {swi}"

    def test_double_half_life_decay(self):
        """Test that SWI reduces to a quarter after 2 half-lives."""
        calc = SWICalculator(half_life_days=10)
        swi = 100.0
        for _ in range(480):  # 20 days
            swi = swi * calc.C
        assert np.isclose(swi, 25.0, rtol=1e-3), f"Expected 25.0, got {swi}"

    def test_sigmoid_runoff_boundaries(self):
        """Test the sigmoid runoff coefficient limits and midpoint."""
        calc = SWICalculator()
        
        # Dry boundary (should approach C_min = 0.1)
        dry_runoff = calc.calculate_runoff_coefficient(0.0)
        assert dry_runoff > 0.09 and dry_runoff < 0.11
        
        # Midpoint (should be exactly halfway between 0.1 and 0.9 = 0.5)
        mid_runoff = calc.calculate_runoff_coefficient(calc.SWI_mid)
        assert np.isclose(mid_runoff, 0.50, rtol=1e-3)
        
        # Saturated boundary (should approach C_max = 0.9)
        wet_runoff = calc.calculate_runoff_coefficient(300.0)
        assert wet_runoff > 0.89 and wet_runoff <= 0.90

# =====================================================================
# 2. Fragility Curve Tests
# =====================================================================

class TestFragilityCurves:
    def test_fragility_median_combined(self):
        """At median depth of 'combined' mode (0.22m), P_failure must be exactly 50%."""
        evaluator = FragilityEvaluator(mode="combined")
        p_fail = evaluator.calculate_p_failure(water_depth_m=0.22)
        assert np.isclose(p_fail, 0.50, rtol=1e-2)

    def test_fragility_median_conservative(self):
        """At median depth of 'conservative' mode (0.30m), P_failure must be exactly 50%."""
        evaluator = FragilityEvaluator(mode="conservative")
        p_fail = evaluator.calculate_p_failure(water_depth_m=0.30)
        assert np.isclose(p_fail, 0.50, rtol=1e-3)

    def test_fragility_dry(self):
        """At zero or negative depth, probability of failure must be 0."""
        evaluator = FragilityEvaluator()
        assert evaluator.calculate_p_failure(0.0) == 0.0
        assert evaluator.calculate_p_failure(-1.0) == 0.0

    def test_fragility_extreme(self):
        """At extreme depths, probability should approach 1.0."""
        evaluator = FragilityEvaluator()
        p_fail = evaluator.calculate_p_failure(2.0)
        assert p_fail > 0.99
        
    def test_fragility_categories(self):
        """Check that the category mapping is correct."""
        evaluator = FragilityEvaluator()
        assert evaluator.get_risk_category(0.10) == "LOW"
        assert evaluator.get_risk_category(0.30) == "MEDIUM"
        assert evaluator.get_risk_category(0.60) == "HIGH"

    def test_fragility_modes_exist(self):
        """All three calibration modes must be instantiable."""
        for mode in ["ballast_only", "combined", "conservative"]:
            ev = FragilityEvaluator(mode=mode)
            assert ev.median_depth > 0
            assert ev.sigma > 0
            assert len(ev.citation) > 0

# =====================================================================
# 3. RAMS Alert Dispatcher Tests
# =====================================================================

class TestAlertDispatcher:
    def test_alert_categories_normal(self):
        """Test standard RAMS threshold mapping based on P_failure."""
        dispatcher = AlertDispatcher()
        
        # Low risk (P < 0.20)
        res_low = dispatcher.generate_verdict(
            segment_id="Test_01", wse=200.1, z_ballast=202.0, p_failure=0.10, category="LOW"
        )
        assert res_low["status"] == "GREEN"
        
        # Warning (P between 0.2 and 0.5)
        res_warn = dispatcher.generate_verdict(
            segment_id="Test_02", wse=200.25, z_ballast=202.0, p_failure=0.32, category="MEDIUM"
        )
        assert res_warn["status"] == "YELLOW"
        
        # High Risk (P > 0.5)
        res_high = dispatcher.generate_verdict(
            segment_id="Test_03", wse=200.40, z_ballast=202.0, p_failure=0.76, category="HIGH"
        )
        assert res_high["status"] == "RED"

    def test_wse_override_red(self):
        """CRITICAL: If WSE > z_ballast, verdict MUST be RED regardless of P_fail."""
        dispatcher = AlertDispatcher()
        
        # Small depth (P_fail is LOW) but WSE > z_ballast (e.g. ballast is very low relative to terrain or terrain=ballast)
        # Real scenario: track is flooded
        res = dispatcher.generate_verdict(
            segment_id="Voie_0", wse=202.1, z_ballast=202.0, p_failure=0.04, category="LOW"
        )
        
        # BECAUSE wse (202.1) > z_ballast (202.0), it MUST trigger RED
        assert res["status"] == "RED"
        assert "HALT" in res["directive"]
