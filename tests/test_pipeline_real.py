import pytest
import pandas as pd
from src.engine.rainfall_provider import RainfallProvider
from src.engine.swi_calculator import SWICalculator

def test_real_pipeline_rainfall_to_swi():
    """
    Integration test: Fetches real API forecast data, passes it through the SWI 
    calculator, and verifies the pipeline produces valid output without mocks.
    """
    # 1. Fetch real forecast
    provider = RainfallProvider()
    try:
        # Only fetch 1 day, no history to keep the test fast
        df_rain = provider.fetch_forecast(include_history=False, forecast_days=1)
    except Exception as e:
        pytest.skip(f"Could not connect to Open-Meteo API for real test: {e}")
        
    assert len(df_rain) >= 24, "Should have at least 24 hours of forecast"
    assert "intensity_mm_h" in df_rain.columns
    
    # 2. Compute SWI
    calc = SWICalculator(half_life_days=10)
    swi_series = calc.compute_swi_recursive(df_rain["intensity_mm_h"])
    
    assert len(swi_series) == len(df_rain)
    assert all(s >= 0 for s in swi_series), "SWI cannot be negative"
    
    # Check max value is reasonable (not infinity)
    peak_swi = max(swi_series)
    assert peak_swi < 1000.0, f"Unrealistically high peak SWI: {peak_swi}"
    
    # 3. Check Runoff
    runoff_coeffs = [calc.calculate_runoff_coefficient(s) for s in swi_series]
    assert all(0.09 < r < 0.91 for r in runoff_coeffs), "Runoff coefficient out of bounds"
