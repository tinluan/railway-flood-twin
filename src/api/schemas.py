"""
src/api/schemas.py — Pydantic Data Models (API Schemas)
=======================================================
Defines all request and response schemas used by the FastAPI endpoints.
These models ensure type safety, automatic validation, and generate the OpenAPI
specification (Swagger documentation).

Naming Convention:
    All JSON keys follow the project's ASCII-only naming convention to avoid
    encoding issues.

Key Enums:
    AlertColor: CAP-standard RAMS colors (GREEN, YELLOW, ORANGE, RED).
    RiskCategory: Fragility-curve risk classes (LOW, MEDIUM, HIGH).
    AssetType: Supported infrastructure types (Voie, Buse, Pont Rail, etc.).

Key Models:
    AssetSummary / AssetDetail: Infrastructure metadata and Z-thresholds.
    CrossSectionResponse: DTM terrain profiles (60m East-West).
    SWIResponse: Hydrological time-series (rainfall, SWI, runoff).
    AlertVerdict: Single-asset operational alert.
    SystemAlertSummary: System-wide risk snapshot (used by dashboard header).
    HotspotResponse: Ranked list of critical assets.
    SimulationRequest: Payload for running custom rainfall scenarios.

Relationship with other files:
    - Imported by ALL routers in `src/api/routers/*.py` to define endpoint signatures.
    - Matches the JSON outputs of the `src/engine/` modules (e.g., `AlertVerdict`
      schema matches the dictionary returned by `alert_dispatcher.py`).

Example Usage:
    from src.api.schemas import AlertVerdict, AlertColor

    # Create a validated alert verdict object
    alert = AlertVerdict(
        segment_id="SEG_142",
        wse_m=222.1,
        z_ballast_m=221.5,
        p_failure_pct=65.3,
        status=AlertColor.RED,
        directive="EMERGENCY HALT"
    )
    # FastApi automatically serializes this to JSON in responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AlertColor(str, Enum):
    """CAP-standard colour palette used by the RAMS alert hierarchy."""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    RED = "RED"


class RiskCategory(str, Enum):
    """Fragility-curve risk class (maps to RAMS colours)."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssetType(str, Enum):
    """Infrastructure asset types monitored by the digital twin."""
    BUSE = "Buse"
    DALOT = "Dalot"
    FOSSE_TERRE = "Fosse terre"
    FOSSE_TERRE_REVETU = "Fosse terre revetu"
    TALUS_TERRE = "Talus Terre"
    VOIE = "Voie"
    PONT_RAIL = "Pont Rail"
    DRAINAGE = "Drainage longitudinal"
    DESCENTE_EAU = "Descente eau"


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------
class AssetThresholds(BaseModel):
    """Yellow / Orange / Red Z-thresholds for a single asset."""
    yellow_z_m: Optional[float] = Field(None, description="Drainage-at-capacity threshold (m NGF)")
    orange_z_m: Optional[float] = Field(None, description="Embankment erosion threshold (m NGF)")
    red_z_m: Optional[float] = Field(None, description="Water-on-rail emergency threshold (m NGF)")


class AssetSummary(BaseModel):
    """Lightweight asset record returned by the list endpoint."""
    asset_id: str = Field(..., description="Unique asset key (ASCII-only)")
    asset_type: Optional[str] = None
    thresholds: Optional[AssetThresholds] = None


class AssetDetail(AssetSummary):
    """Full detail for a single asset including all z_config fields."""
    z_min_m: Optional[float] = None
    z_max_m: Optional[float] = None
    z_mean_m: Optional[float] = None
    nearest_voie: Optional[str] = None
    nearest_talus: Optional[str] = None
    extra: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Any additional z_config fields not captured above",
    )


# ---------------------------------------------------------------------------
# Cross-section schemas
# ---------------------------------------------------------------------------
class CrossSectionPoint(BaseModel):
    """Single point on a cross-section profile."""
    distance_m: float
    elevation_m: float


class CrossSectionResponse(BaseModel):
    """DTM cross-section for an asset (60 m E-W, 1 m resolution)."""
    asset_id: str
    source: str = Field("dtm", description="'dtm' if from DTM raster, 'synthetic' if generated")
    profile: List[CrossSectionPoint]


# ---------------------------------------------------------------------------
# Hydrology / SWI schemas
# ---------------------------------------------------------------------------
class SWIRecord(BaseModel):
    """One row of SWI results."""
    timestamp: Optional[str] = None
    hour: Optional[int] = None
    intensity_mm_h: float
    swi_mm: float
    runoff_coeff: float
    active_runoff_mm: float


class SWIResponse(BaseModel):
    """Full SWI time-series."""
    count: int
    records: List[SWIRecord]


# ---------------------------------------------------------------------------
# Flood polygon schemas
# ---------------------------------------------------------------------------
class FloodPolygonResponse(BaseModel):
    """GeoJSON FeatureCollection for a single timestep."""
    timestep: int
    geojson: Dict[str, Any]


# ---------------------------------------------------------------------------
# Alert / verdict schemas
# ---------------------------------------------------------------------------
class AlertVerdict(BaseModel):
    """Operational alert for a single asset at the current evaluation."""
    segment_id: str
    wse_m: float
    z_ballast_m: Optional[float] = None
    p_failure_pct: float
    status: AlertColor
    directive: str
    timestamp: Optional[str] = None


class SystemAlertSummary(BaseModel):
    """System-wide risk snapshot."""
    overall_status: AlertColor
    total_assets: int
    green_count: int = 0
    yellow_count: int = 0
    orange_count: int = 0
    red_count: int = 0
    alerts: List[AlertVerdict]


class HotspotEntry(BaseModel):
    """One entry in the top-N hotspot list."""
    rank: int
    asset_id: str
    wse_m: float
    threshold_exceeded: Optional[AlertColor] = None
    margin_m: float = Field(..., description="WSE minus critical threshold (positive = overtopping)")


class HotspotResponse(BaseModel):
    """Top-N critical assets."""
    count: int
    hotspots: List[HotspotEntry]


# ---------------------------------------------------------------------------
# Engine trigger schemas
# ---------------------------------------------------------------------------
class CycleRequest(BaseModel):
    """Optional parameters for triggering the 15-minute operational cycle."""
    force_hecras: bool = Field(False, description="Run HEC-RAS even if SWI is below limit")


class CycleResult(BaseModel):
    """Result of a cycle execution."""
    status: str
    swi_peak_mm: Optional[float] = None
    alerts_generated: int = 0
    message: str = ""


class SimulationRequest(BaseModel):
    """Custom rainfall payload for a projected simulation."""
    rainfall_mm_h: List[float] = Field(
        ...,
        min_length=1,
        description="Hourly rainfall intensities (mm/h) — one value per hour",
    )
    half_life_days: float = Field(10.0, gt=0, description="SWI half-life in days")


class SimulationResult(BaseModel):
    """Projected SWI + alert output from a custom simulation."""
    timesteps: int
    swi_series: List[float]
    runoff_series: List[float]
    peak_swi_mm: float
    alerts: List[AlertVerdict]
