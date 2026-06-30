"""
Test Suite for the Railway Flood-Twin REST API
===============================================
Uses FastAPI's TestClient (backed by httpx) to exercise every endpoint
against the real data/processed/ files without starting a live server.

Run with:
    .conda\\python.exe -m pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ========================== Health ==========================

class TestHealth:
    """Root and /health endpoints."""

    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "operational"
        assert body["version"] == "0.1.0"

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ========================== Assets ==========================

class TestAssets:
    """GET /api/v1/assets and /api/v1/assets/{asset_id}."""

    def test_list_assets(self):
        r = client.get("/api/v1/assets")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) > 0
        # Check first asset has required fields
        first = body[0]
        assert "asset_id" in first
        assert "thresholds" in first

    def test_list_assets_filter_by_type(self):
        r = client.get("/api/v1/assets", params={"asset_type": "Buse"})
        assert r.status_code == 200
        body = r.json()
        # All returned assets should be Buse type (or empty if none match)
        for asset in body:
            if asset.get("asset_type"):
                assert asset["asset_type"] == "Buse"

    def test_get_asset_detail(self):
        # First, get the list to find a valid asset_id
        r = client.get("/api/v1/assets")
        assert r.status_code == 200
        assets = r.json()
        asset_id = assets[0]["asset_id"]

        r2 = client.get(f"/api/v1/assets/{asset_id}")
        assert r2.status_code == 200
        detail = r2.json()
        assert detail["asset_id"] == asset_id
        assert "thresholds" in detail

    def test_get_asset_not_found(self):
        r = client.get("/api/v1/assets/NONEXISTENT_ASSET_XYZ")
        assert r.status_code == 404


# ========================== Cross-Sections ==========================

class TestCrossSections:
    """GET /api/v1/cross-sections/{asset_id}."""

    def test_get_cross_section(self):
        # Use a known cross-section asset (Talus Terre assets have them)
        r = client.get("/api/v1/assets")
        assets = r.json()
        # Try to find an asset that likely has a cross-section
        asset_ids = [a["asset_id"] for a in assets if "Talus" in a["asset_id"]]
        if not asset_ids:
            asset_ids = [a["asset_id"] for a in assets]

        r2 = client.get(f"/api/v1/cross-sections/{asset_ids[0]}")
        # Could be 200 or 404 depending on coverage
        assert r2.status_code in (200, 404)

        if r2.status_code == 200:
            body = r2.json()
            assert body["asset_id"] == asset_ids[0]
            assert isinstance(body["profile"], list)
            if body["profile"]:
                pt = body["profile"][0]
                assert "distance_m" in pt
                assert "elevation_m" in pt

    def test_cross_section_not_found(self):
        r = client.get("/api/v1/cross-sections/NONEXISTENT_XYZ")
        assert r.status_code == 404


# ========================== Hydrology / SWI ==========================

class TestHydrology:
    """GET /api/v1/hydrology/swi and flood polygon endpoints."""

    def test_get_swi(self):
        r = client.get("/api/v1/hydrology/swi")
        assert r.status_code == 200
        body = r.json()
        assert "count" in body
        assert "records" in body
        assert body["count"] > 0
        rec = body["records"][0]
        assert "swi_mm" in rec
        assert "runoff_coeff" in rec
        assert "intensity_mm_h" in rec

    def test_get_swi_with_range(self):
        r = client.get("/api/v1/hydrology/swi", params={"start_hour": 0, "end_hour": 5})
        assert r.status_code == 200
        body = r.json()
        assert body["count"] <= 6  # At most 6 records (hours 0-5)

    def test_list_flood_timesteps(self):
        r = client.get("/api/v1/flood-polygons")
        assert r.status_code == 200
        body = r.json()
        assert "total_timesteps" in body
        assert body["total_timesteps"] > 0

    def test_get_flood_polygon(self):
        # Get available timesteps first
        r = client.get("/api/v1/flood-polygons")
        body = r.json()
        if body.get("range"):
            ts = body["range"]["start"]
            r2 = client.get(f"/api/v1/flood-polygons/{ts}")
            assert r2.status_code == 200
            poly = r2.json()
            assert poly["timestep"] == ts
            assert "geojson" in poly

    def test_flood_polygon_not_found(self):
        r = client.get("/api/v1/flood-polygons/99999")
        assert r.status_code == 404


# ========================== Alerts ==========================

class TestAlerts:
    """GET /api/v1/alerts/current and /api/v1/alerts/hotspots."""

    def test_current_alerts(self):
        r = client.get("/api/v1/alerts/current")
        assert r.status_code == 200
        body = r.json()
        assert "overall_status" in body
        assert body["overall_status"] in ("GREEN", "YELLOW", "ORANGE", "RED")
        assert body["total_assets"] > 0
        assert "alerts" in body
        assert len(body["alerts"]) == body["total_assets"]

    def test_current_alerts_specific_timestep(self):
        r = client.get("/api/v1/alerts/current", params={"timestep": 0})
        assert r.status_code == 200
        body = r.json()
        assert body["total_assets"] > 0

    def test_hotspots(self):
        r = client.get("/api/v1/alerts/hotspots")
        assert r.status_code == 200
        body = r.json()
        assert "count" in body
        assert "hotspots" in body
        assert body["count"] <= 5  # default top_n=5

        if body["hotspots"]:
            hs = body["hotspots"][0]
            assert hs["rank"] == 1
            assert "asset_id" in hs
            assert "wse_m" in hs
            assert "margin_m" in hs

    def test_hotspots_custom_n(self):
        r = client.get("/api/v1/alerts/hotspots", params={"top_n": 3, "timestep": 24})
        assert r.status_code == 200
        body = r.json()
        assert body["count"] <= 3


# ========================== Engine ==========================

class TestEngine:
    """POST /api/v1/engine/cycle and /api/v1/engine/simulate."""

    def test_simulate_custom_rainfall(self):
        payload = {
            "rainfall_mm_h": [0, 2, 5, 10, 20, 30, 15, 8, 3, 1],
            "half_life_days": 10.0,
        }
        r = client.post("/api/v1/engine/simulate", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["timesteps"] == 10
        assert len(body["swi_series"]) == 10
        assert len(body["runoff_series"]) == 10
        assert body["peak_swi_mm"] > 0
        assert isinstance(body["alerts"], list)
        assert len(body["alerts"]) == 10

    def test_simulate_single_hour(self):
        payload = {"rainfall_mm_h": [50.0]}
        r = client.post("/api/v1/engine/simulate", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["timesteps"] == 1

    def test_cycle_trigger(self):
        """Test the operational cycle trigger (reads real rainfall data)."""
        r = client.post("/api/v1/engine/cycle", json={"force_hecras": False})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("success", "error")
        if body["status"] == "success":
            assert body["swi_peak_mm"] is not None
            assert body["swi_peak_mm"] >= 0


# ========================== OpenAPI / Docs ==========================

class TestDocs:
    """Verify auto-generated documentation is accessible."""

    def test_openapi_schema(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema["info"]["title"] == "Railway Flood-Risk Digital Twin API"
        assert schema["info"]["version"] == "0.1.0"
        # Verify all critical paths exist in the schema
        paths = schema["paths"]
        assert "/api/v1/assets" in paths
        assert "/api/v1/alerts/current" in paths
        assert "/api/v1/hydrology/swi" in paths
        assert "/api/v1/engine/simulate" in paths

    def test_swagger_ui(self):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_redoc(self):
        r = client.get("/redoc")
        assert r.status_code == 200
