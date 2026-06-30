import json
import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.paths import paths
from src.engine.hecras_hdf5_reader import HECRASPlanReader
from src.config.settings import HECRAS_PROJECT_DIR, HECRAS_PRJ_NAME

def extract_real_wse():
    print("Extracting real WSE from HEC-RAS HDF5...")
    
    # 1. Path to HDF5
    prj_path = paths.DATA / HECRAS_PROJECT_DIR / f"{HECRAS_PRJ_NAME}.prj"
    hdf5_path = prj_path.with_suffix(".p02.hdf")
    
    if not hdf5_path.exists():
        print(f"ERROR: HDF5 file not found at {hdf5_path}")
        return
        
    # 2. Load Asset Coordinates
    coords_path = paths.PROCESSED / "asset_coordinates.json"
    if not coords_path.exists():
        print(f"ERROR: Asset coordinates not found at {coords_path}")
        return
        
    with open(coords_path, "r", encoding="utf-8") as f:
        coords_dict = json.load(f)
        
    asset_coords = {k: (v["x"], v["y"]) for k, v in coords_dict.items()}
    
    # 3. Read HDF5 and Export
    out_path = paths.PROCESSED / "hecras_wse_results.json"
    with HECRASPlanReader(str(hdf5_path)) as reader:
        reader.export_wse_json(out_path, asset_coords, max_dist=50.0)
        
    print(f"Successfully exported real WSE to {out_path}")

if __name__ == "__main__":
    extract_real_wse()
