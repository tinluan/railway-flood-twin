import os
import json
import rasterio
import numpy as np
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point, LineString

# Hardcoded paths based on the project structure
DATA_DIR = Path(r"G:\Shared drives\DigiTwin\railway-flood-twin\data")
GIS_DIR = DATA_DIR / "staging" / "gis"
TERRAIN_DIR = DATA_DIR / "staging" / "terrain"
OUT_DIR = DATA_DIR / "processed"

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
