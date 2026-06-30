"""
src/engine/rainfall_provider.py — Live Rainfall Data Provider (Layer 1: Data Sources)
======================================================================================
Fetches real-time and forecast hourly rainfall data from the Open-Meteo API for
the SNCF railway corridor.

Architecture Position (Layer 1 — Data Sources):
    - PRODUCES: Hourly rainfall DataFrame (timestamp, intensity_mm_h, source)
    - CONSUMED BY: ``src/engine/data_ingestion.py`` (saves to CSV)
    - ORCHESTRATED BY: ``src/engine/pipeline_orchestrator.py``

Open-Meteo API:
    - Free, open-source, no API key required
    - Provides Météo-France AROME model data for France
    - Returns hourly 'rain' (large-scale) and 'showers' (convective) in mm
    - Combined: intensity_mm_h = rain + showers
    - Documentation: https://open-meteo.com/en/docs

Caching:
    Results are cached for 15 minutes (configurable via RAINFALL_CACHE_TTL_SEC)
    to avoid unnecessary API calls on dashboard refreshes.

Relationship with other files:
    DOWNSTREAM: src/engine/data_ingestion.py → saves to rainfall CSV
                src/engine/swi_calculator.py  → reads the CSV for SWI computation
    CONFIG:     src/config/settings.py         → API URL, lat/lon, cache TTL

Example Usage:
    from src.engine.rainfall_provider import RainfallProvider

    provider = RainfallProvider()

    # 1. Fetch live forecast (next 48h + past 7 days):
    df = provider.fetch_forecast()
    # DataFrame with columns: timestamp, intensity_mm_h, source

    # 2. Fetch only the forecast window (no historical warm-up):
    df_future = provider.fetch_forecast(include_history=False)

    # 3. Custom coordinates:
    provider = RainfallProvider(lat=44.55, lon=4.78)

Authors: TRAN Trong-Tin (Antigravity-generated)
Project: SNCF Railway Flood-Risk Digital Twin (Master Capstone)
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (overridden by settings.py when imported via the pipeline)
# ---------------------------------------------------------------------------
_DEFAULT_API_URL = "https://api.open-meteo.com/v1/forecast"
_DEFAULT_LAT = 44.65      # Tartaiguille corridor (Drôme, France) - matched to HEC-RAS mesh center
_DEFAULT_LON = 4.91
_DEFAULT_FORECAST_DAYS = 2   # Open-Meteo: forecast_days (max 16)
_DEFAULT_PAST_DAYS = 7       # Open-Meteo: past_days (max 92)
_DEFAULT_CACHE_TTL = 900     # 15 minutes


class RainfallProvider:
    """
    Fetches hourly rainfall from Open-Meteo API for the railway corridor.

    The provider combines 'rain' (large-scale/stratiform precipitation) and
    'showers' (convective precipitation) into a single intensity field, which
    matches the format expected by the SWI calculator.
    """

    def __init__(
        self,
        lat: float = _DEFAULT_LAT,
        lon: float = _DEFAULT_LON,
        api_url: str = _DEFAULT_API_URL,
        cache_ttl_sec: int = _DEFAULT_CACHE_TTL,
    ):
        self.lat = lat
        self.lon = lon
        self.api_url = api_url
        self.cache_ttl = cache_ttl_sec

        # Simple in-memory cache
        self._cache: Optional[pd.DataFrame] = None
        self._cache_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_forecast(
        self,
        include_history: bool = True,
        forecast_days: int = _DEFAULT_FORECAST_DAYS,
        past_days: int = _DEFAULT_PAST_DAYS,
    ) -> pd.DataFrame:
        """
        Fetch hourly rainfall forecast (and optionally recent history).

        Args:
            include_history: If True, includes past_days of historical data
                             (needed for SWI warm-up so the leaky-bucket starts
                             from a realistic soil moisture state).
            forecast_days:   Number of forecast days (1–16).
            past_days:       Number of past days to include (0–92).

        Returns:
            DataFrame with columns:
                - timestamp (datetime, UTC)
                - intensity_mm_h (float, mm per hour)
                - source (str, "OPEN_METEO_FORECAST" or "OPEN_METEO_HISTORY")
        """
        # Check cache
        if self._cache is not None and (time.time() - self._cache_time) < self.cache_ttl:
            logger.info("Using cached rainfall data (age: %.0fs)",
                        time.time() - self._cache_time)
            return self._cache.copy()

        # Build request
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "hourly": "rain,showers,precipitation",
            "forecast_days": forecast_days,
            "timezone": "Europe/Paris",
        }
        if include_history and past_days > 0:
            params["past_days"] = past_days

        logger.info(
            "Fetching rainfall from Open-Meteo: lat=%.2f, lon=%.2f, "
            "forecast_days=%d, past_days=%s",
            self.lat, self.lon, forecast_days,
            past_days if include_history else "none"
        )

        try:
            resp = requests.get(self.api_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Open-Meteo API request failed: %s", e)
            raise RuntimeError(f"Failed to fetch rainfall data: {e}") from e

        # Parse the response
        df = self._parse_response(data, include_history, past_days)

        # Update cache
        self._cache = df.copy()
        self._cache_time = time.time()

        logger.info(
            "Fetched %d hourly records (%.1f–%.1f mm/h range, peak=%.1f mm/h)",
            len(df),
            df["intensity_mm_h"].min(),
            df["intensity_mm_h"].max(),
            df["intensity_mm_h"].max(),
        )
        return df

    def fetch_current(self) -> dict:
        """
        Fetch just the current hour's rainfall.

        Returns:
            Dict with keys: timestamp, intensity_mm_h, source
        """
        df = self.fetch_forecast(include_history=False, forecast_days=1)
        now = datetime.now()

        # Find the row closest to the current time
        df["_diff"] = abs(pd.to_datetime(df["timestamp"]) - now)
        closest = df.loc[df["_diff"].idxmin()]

        return {
            "timestamp": str(closest["timestamp"]),
            "intensity_mm_h": float(closest["intensity_mm_h"]),
            "source": "OPEN_METEO_LIVE",
        }

    def invalidate_cache(self):
        """Force a fresh API call on next fetch."""
        self._cache = None
        self._cache_time = 0.0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _parse_response(
        self,
        data: dict,
        include_history: bool,
        past_days: int,
    ) -> pd.DataFrame:
        """Parse the Open-Meteo JSON response into a clean DataFrame."""
        hourly = data.get("hourly", {})

        if not hourly:
            raise ValueError("Open-Meteo response missing 'hourly' data block")

        timestamps = hourly.get("time", [])
        rain = hourly.get("rain", [])          # large-scale / stratiform (mm)
        showers = hourly.get("showers", [])    # convective (mm)

        if not timestamps:
            raise ValueError("Open-Meteo response has empty timestamp array")

        # Combine rain + showers into total intensity
        # Both fields are in mm per hour (Open-Meteo provides hourly accumulation)
        records = []
        now = datetime.now()

        for i, ts_str in enumerate(timestamps):
            ts = pd.Timestamp(ts_str)
            r = rain[i] if i < len(rain) and rain[i] is not None else 0.0
            s = showers[i] if i < len(showers) and showers[i] is not None else 0.0
            intensity = round(r + s, 2)

            # Label source based on whether it's past or future
            source = ("OPEN_METEO_HISTORY" if ts < pd.Timestamp(now)
                      else "OPEN_METEO_FORECAST")

            records.append({
                "timestamp": ts,
                "intensity_mm_h": intensity,
                "source": source,
            })

        df = pd.DataFrame(records)
        df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    def get_status(self) -> dict:
        """Return provider status info for dashboard display."""
        cache_age = (time.time() - self._cache_time) if self._cache is not None else None
        return {
            "provider": "Open-Meteo",
            "api_url": self.api_url,
            "latitude": self.lat,
            "longitude": self.lon,
            "cache_ttl_sec": self.cache_ttl,
            "cache_age_sec": round(cache_age, 1) if cache_age else None,
            "cached_records": len(self._cache) if self._cache is not None else 0,
        }


# ======================================================================
# Standalone test
# ======================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )

    provider = RainfallProvider()

    print("\n=== Fetching Live Rainfall (Tartaiguille Corridor) ===")
    df = provider.fetch_forecast()

    print(f"\nTotal records: {len(df)}")
    print(f"Time range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"Peak intensity: {df['intensity_mm_h'].max():.1f} mm/h")
    print(f"Mean intensity: {df['intensity_mm_h'].mean():.2f} mm/h")

    # Show recent + forecast
    print("\n--- Last 6 hours + Next 6 hours ---")
    now = pd.Timestamp.now()
    window = df[
        (df["timestamp"] >= now - pd.Timedelta(hours=6)) &
        (df["timestamp"] <= now + pd.Timedelta(hours=6))
    ]
    for _, row in window.iterrows():
        marker = "→" if abs(row["timestamp"] - now) < pd.Timedelta(hours=1) else " "
        print(f"  {marker} {row['timestamp']}  {row['intensity_mm_h']:5.1f} mm/h  [{row['source']}]")

    print(f"\nProvider status: {provider.get_status()}")
    print("\nDone.")
