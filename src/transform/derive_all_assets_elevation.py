import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from src.utils.paths import paths

# -------------------------------------------------------------------
# General Terrain Summary Script: All Railway Assets
# -------------------------------------------------------------------
# This script derives min, max, and mean elevation for every feature 
# in every GIS asset layer.
#
# Logic:
# 1. Finds the DTM (dtm_fixed.tif)
# 2. Loops through all .gpkg files in data/staging/gis/
# 3. Clips the DTM to each asset's footprint (Polygon/MultiPolygon).
# 4. Exports a single consolidated summary for the Digital Twin.
# -------------------------------------------------------------------

# Preferred fixed DTM file
FIXED_DTM_FILE = paths.TERRAIN_STAGING / "dtm_fixed.tif"

# Expected project CRS
TARGET_EPSG = 2154

# ID fields to try and use for labeling
CANDIDATE_LABEL_FIELDS = [
    "id", "ID", "Id", "fid", "FID", "code", "CODE", "Code", "name", "NAME", "Name"
]

def find_working_dtm():
    if FIXED_DTM_FILE.exists():
        return FIXED_DTM_FILE
    tif_files = sorted(paths.TERRAIN_STAGING.glob("*.tif"))
    if tif_files: return tif_files[0]
    raise FileNotFoundError(f"No DTM found in: {paths.TERRAIN_STAGING}")

def summarize_geometry(src, geom):
    """Return stats for a single geometry."""
    try:
        out_image, _ = mask(src, [geom], crop=True, filled=True)
        band = out_image[0]
        nodata = src.nodata
        valid = band[band != nodata] if nodata is not None else band.flatten()
        valid = valid[np.isfinite(valid)]
        
        if valid.size == 0:
            return {"count": 0, "min": None, "max": None, "mean": None, "notes": "No valid pixels"}
            
        return {
            "count": int(valid.size),
            "min": round(float(valid.min()), 2),
            "max": round(float(valid.max()), 2),
            "mean": round(float(valid.mean()), 2),
            "notes": None
        }
    except Exception as e:
        return {"count": 0, "min": None, "max": None, "mean": None, "notes": str(e)}

def main():
    print("--- Milestone 3: Full Asset Elevation Extraction ---")
    paths.ensure_directories()
    
    dtm_path = find_working_dtm()
    print(f"[INPUT] DTM: {dtm_path.name}")
    
    all_summaries = []
    
    # Process every GeoPackage in staging/gis
    asset_files = list(paths.GIS_STAGING.glob("*.gpkg"))
    print(f"[INFO] Found {len(asset_files)} asset layers.")

    with rasterio.open(dtm_path) as src:
        for asset_file in asset_files:
            asset_type = asset_file.stem.replace("_fixed", "")
            print(f"\n[LAYER] Processing {asset_type}...")
            
            gdf = gpd.read_file(asset_file)
            if gdf.crs != src.crs:
                gdf = gdf.to_crs(src.crs)
            
            # Find a label field for the report
            label_col = next((c for c in CANDIDATE_LABEL_FIELDS if c in gdf.columns), None)
            
            for idx, row in gdf.iterrows():
                label = row[label_col] if label_col else idx
                stats = summarize_geometry(src, row.geometry.__geo_interface__)
                
                all_summaries.append({
                    "layer": asset_type,
                    "asset_label": label,
                    "elev_min_m": stats["min"],
                    "elev_max_m": stats["max"],
                    "elev_mean_m": stats["mean"],
                    "pixel_count": stats["count"],
                    "notes": stats["notes"]
                })
                
                print(f"  > {asset_type} | {label}: {stats['mean']}m (px: {stats['count']})")

    # -------------------------------------------------------------------
    # EXPORT RESULTS
    # -------------------------------------------------------------------
    summary_df = pd.DataFrame(all_summaries)
    
    # Save Main Project Summary
    summary_path = paths.TERRAIN_PROCESSED / "all_assets_elevation_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    # Save Academic Report Table (Prettier names)
    table_path = paths.REPORT_TABLES / "Table01_Asset_Elevation_Summary.csv"
    summary_df.to_csv(table_path, index=False)
    
    print(f"\n[SUCCESS] Extraction complete for {len(summary_df)} assets.")
    print(f"[OUTPUT] Master Summary: {summary_path}")
    print(f"[OUTPUT] Academic Table: {table_path}")
    print("\nPreview of top assets:")
    print(summary_df.head(10))

if __name__ == "__main__":
    main()
