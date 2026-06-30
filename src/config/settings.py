"""src/config/settings.py — Application Configuration
==================================================
Centralized configuration file that loads environment variables and
defines global constants for the FastAPI application and backend scripts.

Architecture Position (Utilities):
    - Acts as a single source of truth for config variables, preventing
      scattered `os.getenv` calls.
    - Works in tandem with `src/utils/paths.py`.

Example Usage:
    from src.config.settings import APP_NAME, DEBUG_MODE
    from src.config.settings import CORRIDOR_LAT, CORRIDOR_LON
"""

import os

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
APP_NAME = "Railway Flood-Risk Digital Twin"
APP_VERSION = "0.2.0"
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Rainfall API — Open-Meteo (free, no API key required)
# ---------------------------------------------------------------------------
RAINFALL_API_URL = "https://api.open-meteo.com/v1/forecast"

# Corridor centre point (WGS84 — L752 PK534, South Head Tartaiguille, Drôme)
CORRIDOR_LAT = float(os.getenv("CORRIDOR_LAT", "44.65"))
CORRIDOR_LON = float(os.getenv("CORRIDOR_LON", "4.91"))

# Forecast & history windows
FORECAST_HOURS = int(os.getenv("FORECAST_HOURS", "48"))
HISTORICAL_DAYS = int(os.getenv("HISTORICAL_DAYS", "7"))

# Cache TTL — avoid hitting the API on every dashboard refresh
RAINFALL_CACHE_TTL_SEC = int(os.getenv("RAINFALL_CACHE_TTL", "900"))  # 15 min

# ---------------------------------------------------------------------------
# Pipeline thresholds
# ---------------------------------------------------------------------------
SWI_HECRAS_TRIGGER_MM = float(os.getenv("SWI_HECRAS_TRIGGER", "100.0"))
CYCLE_INTERVAL_MIN = int(os.getenv("CYCLE_INTERVAL_MIN", "15"))

# ---------------------------------------------------------------------------
# HEC-RAS paths (relative to DATA_ROOT)
# ---------------------------------------------------------------------------
HECRAS_PROJECT_DIR = os.getenv(
    "HECRAS_PROJECT_DIR",
    "hec-ras"
)
HECRAS_PRJ_NAME = os.getenv(
    "HECRAS_PRJ_NAME",
    "CAPSTONE_JN_L752_PK"
)
