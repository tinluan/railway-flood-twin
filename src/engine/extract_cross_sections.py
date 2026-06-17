"""
src/engine/extract_cross_sections.py — DTM Terrain Profiler (Layer 2: Bridge)
===============================================================================
Extracts 60-metre East-West terrain cross-section profiles for each railway
infrastructure asset (bridges, culverts, dalots) by sampling the DTM raster.
The profiles are used by the Streamlit dashboard and API to visualise the
terrain shape around each asset and contextualise the flood risk.

Architecture Position (Layer 2 — Bridge):
    - READS:   data/staging/gis/Pont Rail_fixed.gpkg   (bridges)
               data/staging/gis/Buse_fixed.gpkg        (culverts)
               data/staging/gis/Dalot_fixed.gpkg       (box culverts, optional)
               data/staging/terrain/dtm_fixed.tif      (1m resolution DTM raster)
    - WRITES:  data/processed/cross_sections.json
    - SERVED BY: src/api/routers/assets.py  (GET /api/v1/cross-sections/{asset_id})

Profile Strategy:
    For each asset centroid (cx, cy) in EPSG:2154 (Lambert 93, metres):
    - Sample the DTM at 61 points from cx-30m to cx+30m (East-West transect)
    - Since Ligne 400 runs roughly North-South, this E-W cut acts as a
      transverse cross-section perpendicular to the track axis.
    - 1 m point spacing → 61 elevation readings per asset

Coverage Note:
    This script only covers Pont Rail, Buse, Dalot (3 asset types).
    Fosse terre, Fosse revetu, Talus, and Voie were added later.
    To extend coverage, add their GeoPackage paths to the load block.

Output JSON Structure (cross_sections.json):
    {
      "Pont_0": {
        "distances":   [-30, -29, ..., 0, ..., 29, 30],  # metres from centroid
        "elevations":  [221.4, 221.5, ..., 224.2, ...],  # metres NGF
        "asset_type":  "Pont Rail (Bridge)",
        "center_x":    657823.4,   # EPSG:2154 easting
        "center_y":    6512034.7   # EPSG:2154 northing
      },
      "Buse_1": { ... },
      ...
    }

Relationship with other files:
    UPSTREAM:
      src/ingestion/load_gis_assets_dotenv.py → loaded GIS layers into DB
      data/staging/gis/*.gpkg                 → cleaned GeoPackages (source)
      data/staging/terrain/dtm_fixed.tif      → terrain raster
    DOWNSTREAM:
      src/api/routers/assets.py  → GET /api/v1/cross-sections/{asset_id}
      src/api/schemas.py         → CrossSectionResponse, CrossSectionPoint
      dashboard/app_main.py      → terrain profile visualisation chart
    PATH RESOLVER:
      Uses src/utils/paths.py::ProjectPaths (NOT the legacy src/paths.py)

Example Usage:
    # Run the full extraction to regenerate cross_sections.json:
    python src/engine/extract_cross_sections.py
    # → prints per-asset progress and saves data/processed/cross_sections.json

    # Import and call from another script:
    from src.engine.extract_cross_sections import extract_profiles
    extract_profiles()
    # On success: "Successfully saved cross sections to ...cross_sections.json"

    # Access via the API after extraction:
    # GET http://localhost:8000/api/v1/cross-sections/Pont_0
    # → {"asset_id": "Pont_0", "source": "dtm", "profile": [...]}
"""

import os
import json
import sys
import logging
import rasterio
import numpy as np
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point, LineString

# Use canonical path resolver — never hardcode paths.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.utils.paths import ProjectPaths

paths = ProjectPaths()
logger = logging.getLogger(__name__)

# NOTE: This script only has 3 asset types (Pont Rail, Buse, Dalot).
# The remaining 4 types (Fosse terre, Fosse revetu, Talus, Voie)
# were added later in the project. Update `configs` below to include them.
# Their GeoPackage files follow the same naming pattern as the 3 listed.

GIS_DIR     = paths.STAGING / "gis"
TERRAIN_DIR = paths.STAGING / "terrain"
OUT_DIR     = paths.PROCESSED_DATA

def extract_profiles():
    print("Loading GIS data...")
    bridges = gpd.read_file(GIS_DIR / "Pont Rail_fixed.gpkg")
    bridges["asset_type"] = "Pont Rail (Bridge)"
    culverts = gpd.read_file(GIS_DIR / "Buse_fixed.gpkg")
    culverts["asset_type"] = "Buse (Culvert)"
    
    # Optional: Dalot
    try:
        box_culverts = gpd.read_file(GIS_DIR / "Dalot_fixed.gpkg")
        box_culverts["asset_type"] = "Dalot (Box Culvert)"
        assets = gpd.GeoDataFrame(pd.concat([bridges, culverts, box_culverts], ignore_index=True))
    except:
        import pandas as pd
        assets = gpd.GeoDataFrame(pd.concat([bridges, culverts], ignore_index=True))

    # Assume geometries are in EPSG:2154 (Lambert 93 - meters)
    # The files might not have CRS explicitly set correctly, but coordinates are in L93.
    # Take centroid for MultiPolygons/Lines
    assets["centroid"] = assets.geometry.centroid
    
    dtm_path = TERRAIN_DIR / "dtm_fixed.tif"
    if not dtm_path.exists():
        print(f"Error: DTM file not found at {dtm_path}")
        return

    print("Opening DTM...")
    results = {}
    
    with rasterio.open(dtm_path) as src:
        # For each asset, generate a 60m East-West profile (30m each side)
        for idx, row in assets.iterrows():
            asset_id = f"{row['asset_type'].split()[0]}_{idx}"
            
            c = row["centroid"]
            cx, cy = c.x, c.y
            
            # Generate points from -30m to +30m (East-West)
            # Since Ligne 400 is roughly N-S, an E-W cut acts as a transverse cross-section.
            distances = list(range(-30, 31, 1)) # 61 points, 1m apart
            sample_points = [(cx + d, cy) for d in distances]
            
            # Sample DTM
            elevations = []
            for val in src.sample(sample_points):
                elevations.append(round(float(val[0]), 2))
                
            results[asset_id] = {
                "distances": distances,
                "elevations": elevations,
                "asset_type": row["asset_type"],
                "center_x": cx,
                "center_y": cy
            }
            print(f"Extracted profile for {asset_id}")

    os.makedirs(OUT_DIR, exist_ok=True)
    out_file = OUT_DIR / "cross_sections.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Successfully saved cross sections to {out_file}")

if __name__ == "__main__":
    extract_profiles()
