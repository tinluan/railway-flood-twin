"""
src/engine/preprocessor.py — Mirror Database Builder (Layer 2: Bridge)
=======================================================================
Merges BIM (IFC/Civil3D) and GIS (DTM/LiDAR) data into the "Mirror Database"
(Handoff Schema) used as input for HEC-RAS 2D and the fragility chain.

Architecture Position (Layer 2 — Bridge):
    - READS:   data/staging/  (cleaned GeoPackages from ingestion pipeline)
    - WRITES:  data/processed/handoff_segments.csv  (the Mirror DB)
    - FEEDS:   src/engine/hec_ras_runner.py  (hydraulic simulation input)
    - FEEDS:   src/api/routers/assets.py     (via z_config.json)

The "Funnel" Hotspot Strategy (implemented here):
    1. All 400 km rail segments are loaded from staging.
    2. is_hotspot flag marks the critical ~50 km zone (from RiskVIP + accident data).
    3. Only hotspot segments are passed to the full HEC-RAS 2D simulation.
    4. Non-hotspot segments use SWI-only risk estimation.

Mirror Database Schema (handoff_segments.csv):
    | Column      | Source        | Description                          |
    |-------------|---------------|--------------------------------------|
    | segment_id  | BIM (mock)    | Unique 100m rail section ID          |
    | lat / lon   | GIS           | Centroid coordinates (WGS 84)        |
    | z_terrain   | DTM / LiDAR   | Ground elevation (m NGF)             |
    | z_ballast   | BIM / IFC     | Top of ballast elevation (m NGF)     |
    | is_hotspot  | RiskVIP       | True if in critical ~50 km zone      |

CRS Note:
    All geometries must be in EPSG:2154 (Lambert 93 — metres) before being
    passed to HEC-RAS. The class stores self.crs = "EPSG:2154" as a reminder.

Relationship with other files:
    UPSTREAM (data sources):
      - data/staging/gis/*.gpkg            (cleaned GIS layers)
      - data/staging/terrain/dtm_fixed.tif (terrain elevation raster)
    DOWNSTREAM (consumers):
      - src/engine/hec_ras_runner.py → uses hotspot list for HEC-RAS plan
      - src/engine/extract_cross_sections.py → reads GIS layers for profiles
      - data/processed/z_config.json → enriched later by segment_voie.py

Example Usage:
    from src.engine.preprocessor import MirrorDBProcessor

    processor = MirrorDBProcessor()

    # Build Mirror DB and retrieve hotspot segments only:
    hotspots = processor.generate_mirror_db()
    # hotspots is a DataFrame with columns: segment_id, lat, lon, z_terrain,
    # z_ballast, is_hotspot (all True).
    print(hotspots[["segment_id", "z_terrain", "z_ballast"]])
    #   segment_id  z_terrain  z_ballast
    #   SEG_003     224.2      225.2
    #   SEG_004     219.8      220.8
    #   ...

    # Output also saved to:
    #   data/processed/handoff_segments.csv

Run standalone to regenerate the Mirror DB:
    python src/engine/preprocessor.py
"""

import os
import pandas as pd
import geopandas as gpd
import sys

# Import our central path manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import STAGING_DATA, PROCESSED_DATA

class MirrorDBProcessor:
    """Merges BIM and GIS data to create the Handoff Schema for HEC-RAS."""
    
    def __init__(self):
        self.crs = "EPSG:2154" # Lambert 93

    def generate_mirror_db(self):
        """
        Intersects BIM (ballast height) with GIS (terrain height).
        Implements the 'Funnel' hotspot strategy.
        """
        print("Generating Mirror Database (Handoff Schema)...")
        
        # 1. Load staging data (Mocking the merge for the demo)
        # In real usage, this would use gpd.overlay()
        data = {
            "segment_id": [f"SEG_{i:03}" for i in range(1, 11)],
            "lat": [45.75 + (i * 0.001) for i in range(1, 11)],
            "lon": [4.85 + (i * 0.001) for i in range(1, 11)],
            "z_terrain": [220.5, 221.0, 224.2, 219.8, 218.5, 222.1, 223.5, 220.2, 219.0, 221.5],
            "z_ballast": [221.5, 222.0, 225.2, 220.8, 219.5, 223.1, 224.5, 221.2, 220.0, 222.5],
            "is_hotspot": [False, False, True, True, True, False, False, True, False, False]
        }
        
        df = pd.DataFrame(data)
        
        # Filter for Hotspots (The Funnel Strategy)
        hotspots = df[df['is_hotspot'] == True]
        
        output_path = PROCESSED_DATA / "handoff_segments.csv"
        df.to_csv(output_path, index=False)
        
        print(f"Mirror DB created with {len(hotspots)} active hotspots.")
        return hotspots

if __name__ == "__main__":
    processor = MirrorDBProcessor()
    processor.generate_mirror_db()
