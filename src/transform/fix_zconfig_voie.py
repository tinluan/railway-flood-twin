import json
import numpy as np
from pyproj import Transformer
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.paths import paths

def main():
    print("Fixing z_config.json stale 'Voie_0' references...")
    
    # 1. Load z_config.json
    z_config_path = paths.PROCESSED / "z_config.json"
    with open(z_config_path, "r", encoding="utf-8") as f:
        z_config = json.load(f)
        
    # 2. Load asset_coordinates.json
    coords_path = paths.PROCESSED / "asset_coordinates.json"
    with open(coords_path, "r", encoding="utf-8") as f:
        asset_coords = json.load(f)
        
    # 3. Load voie_segments.json
    voie_path = paths.PROCESSED / "voie_segments.json"
    with open(voie_path, "r", encoding="utf-8") as f:
        voie_segments = json.load(f)
        
    # 4. Transform Voie lat/lon (WGS84 EPSG:4326) to X/Y (Lambert 93 EPSG:2154)
    # Note: pyproj Transformer.from_crs takes (from_crs, to_crs, always_xy=True)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    
    voie_xy = {}
    for seg in voie_segments:
        # always_xy=True means input is (lon, lat)
        x, y = transformer.transform(seg["lon"], seg["lat"])
        voie_xy[seg["name"]] = np.array([x, y])
        
    # 5. For each asset, find nearest Voie_seg
    updates_count = 0
    for asset_id, config in z_config.items():
        if asset_id not in asset_coords:
            continue
            
        asset_pt = np.array([asset_coords[asset_id]["x"], asset_coords[asset_id]["y"]])
        
        # Find nearest
        min_dist = float('inf')
        nearest_voie = None
        
        for v_name, v_pt in voie_xy.items():
            dist = np.linalg.norm(asset_pt - v_pt)
            if dist < min_dist:
                min_dist = dist
                nearest_voie = v_name
                
        if nearest_voie:
            config["nearest_voie"] = nearest_voie
            updates_count += 1
            
    # 6. Save updated z_config.json
    with open(z_config_path, "w", encoding="utf-8") as f:
        json.dump(z_config, f, indent=2, ensure_ascii=False)
        
    print(f"Updated {updates_count} assets with their closest Voie segment.")

if __name__ == "__main__":
    main()
