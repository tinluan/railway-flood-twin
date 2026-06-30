"""
src/engine/preprocessor.py — Mirror Database Builder (Layer 2: Bridge)
=======================================================================
Merges BIM (IFC/Civil3D) and GIS (DTM/LiDAR) data into the "Mirror Database"
(Handoff Schema) used as input for HEC-RAS 2D and the fragility chain.

Architecture Position (Layer 2 — Bridge):
    - READS:   data/staging/gis/voie_fixed.gpkg (Rail geometry)
               data/New_data/DTM/Terrain.lhd_fx_lasd1.tif (Terrain elevation)
    - WRITES:  data/processed/handoff_segments.csv  (the Mirror DB)

Mirror Database Schema (handoff_segments.csv):
    | Column      | Description                          |
    |-------------|--------------------------------------|
    | segment_id  | Unique rail section ID               |
    | lat / lon   | Centroid coordinates (WGS 84)        |
    | x / y       | Coordinates (Lambert 93)             |
    | z_terrain   | Ground elevation (m NGF)             |
    | z_ballast   | Top of ballast elevation (m NGF)     |
    | is_hotspot  | True if in critical zone             |

Example Usage:
    from src.engine.preprocessor import MirrorDBProcessor
    processor = MirrorDBProcessor()
    hotspots = processor.generate_mirror_db()
"""

import os
import pandas as pd
import geopandas as gpd
import rasterio
import sys
from pathlib import Path

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.paths import paths

class MirrorDBProcessor:
    """Merges BIM and GIS data to create the Handoff Schema for HEC-RAS."""
    
    def __init__(self):
        self.crs = "EPSG:2154" # Lambert 93
        self.gis_path = paths.STAGING / "gis" / "voie_fixed.gpkg"
        # User requested explicitly to use the newest DTM
        self.dtm_path = paths.DATA / "New_data" / "DTM" / "Terrain.lhd_fx_lasd1.tif"

    def generate_mirror_db(self):
        """
        Intersects GIS (track) with DTM (terrain height).
        """
        print("Generating Mirror Database (Handoff Schema)...")
        
        if not self.dtm_path.exists():
            raise FileNotFoundError(f"Cannot find DTM at {self.dtm_path}")
            
        if not self.gis_path.exists():
            raise FileNotFoundError(f"Cannot find GIS data at {self.gis_path}")
            
        # 1. Load Track Segments
        print(f"Loading GIS data from {self.gis_path.name}")
        gdf = gpd.read_file(self.gis_path)
        
        # Ensure CRS
        if gdf.crs != self.crs:
            gdf = gdf.to_crs(self.crs)
            
        # Extract centroids
        centroids = gdf.geometry.centroid
        x_coords = centroids.x.values
        y_coords = centroids.y.values
        
        # Also compute WGS84 (Lat/Lon)
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        centroids_wgs84 = gdf_wgs84.geometry.centroid
        lons = centroids_wgs84.x.values
        lats = centroids_wgs84.y.values
        
        # 2. Sample Terrain (DTM)
        print(f"Sampling DTM from {self.dtm_path.name}")
        z_terrain = []
        with rasterio.open(self.dtm_path) as src:
            for x, y in zip(x_coords, y_coords):
                # Sample returns a generator of values for each band
                try:
                    val = next(src.sample([(x, y)]))[0]
                    z_terrain.append(float(val))
                except StopIteration:
                    z_terrain.append(0.0) # Fallback if out of bounds
                    
        # 3. Create Mirror DB
        data = {
            "segment_id": [f"Voie_seg_{i:02d}" for i in range(len(gdf))],
            "lat": lats,
            "lon": lons,
            "x": x_coords,
            "y": y_coords,
            "z_terrain": z_terrain,
            # We assume top of ballast is roughly 0.6m above the terrain for this DB
            "z_ballast": [round(z + 0.6, 2) for z in z_terrain],
            "is_hotspot": [True] * len(gdf) # Default all to hotspot for now
        }
        
        df = pd.DataFrame(data)
        
        # Format the terrain strictly
        df['z_terrain'] = df['z_terrain'].round(2)
        
        # Filter for Hotspots (The Funnel Strategy)
        hotspots = df[df['is_hotspot'] == True]
        
        output_path = paths.PROCESSED / "handoff_segments.csv"
        df.to_csv(output_path, index=False)
        
        print(f"Mirror DB created with {len(hotspots)} active hotspots.")
        print(f"Saved to {output_path}")
        return hotspots

if __name__ == "__main__":
    processor = MirrorDBProcessor()
    processor.generate_mirror_db()
