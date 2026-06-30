import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime
from src.engine.rainfall_provider import RainfallProvider

class TestRainfallProvider:
    @patch("src.engine.rainfall_provider.requests.get")
    def test_fetch_forecast_success(self, mock_get):
        # Mock Open-Meteo response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2026-06-21T00:00", "2026-06-21T01:00"],
                "rain": [1.5, 2.0],
                "showers": [0.5, 0.0]
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = RainfallProvider(cache_ttl_sec=0)
        df = provider.fetch_forecast()

        assert len(df) == 2
        assert "intensity_mm_h" in df.columns
        assert df.iloc[0]["intensity_mm_h"] == 2.0  # 1.5 + 0.5
        assert df.iloc[1]["intensity_mm_h"] == 2.0  # 2.0 + 0.0

    @patch("src.engine.rainfall_provider.requests.get")
    def test_fetch_forecast_caching(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hourly": {"time": ["2026-06-21T00:00"], "rain": [1.0], "showers": [0.0]}
        }
        mock_get.return_value = mock_response

        provider = RainfallProvider(cache_ttl_sec=60)
        
        # First call hits the API
        df1 = provider.fetch_forecast()
        assert mock_get.call_count == 1
        
        # Second call uses cache
        df2 = provider.fetch_forecast()
        assert mock_get.call_count == 1
        assert len(df1) == len(df2)
