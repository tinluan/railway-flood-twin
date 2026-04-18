from pathlib import Path
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from src.utils.paths import paths

# -------------------------------------------------------------------
# Updated terrain summary script for track_area polygons
#
# Save this file to:
#   src/transform/derive_track_area_elevation.py
#
# Run from the project root:
#   python src/transform/derive_track_area_elevation.py
#
# Main improvements in this version:
# - uses a fixed working GeoTIFF from data/staging/terrain/
# - no automatic picking of the wrong .asc copy
# - prints progress for each feature
# - safer CRS handling for the cleaned voie layer
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
# Preferred fixed working DTM file. 
FIXED_DTM_FILE = paths.TERRAIN_STAGING / "dtm_fixed.tif"

# Cleaned track area file
VOIE_FILE = paths.GIS_STAGING / "voie_fixed.gpkg"

# Expected target EPSG for this project
TARGET_EPSG = 2154

# Optional candidate label fields. The script uses the first one it finds.
CANDIDATE_LABEL_FIELDS = [
    "id", "ID", "Id", "fid", "FID", "code", "CODE", "Code", "name", "NAME", "Name"
]


def find_working_dtm() -> Path:
    """Return the working DTM file.
    Priority:
    1. data/staging/terrain/dtm_2154.tif
    2. first .tif in data/staging/terrain/
    """
    if FIXED_DTM_FILE.exists():
        return FIXED_DTM_FILE

    tif_files = sorted(paths.TERRAIN_STAGING.glob("*.tif"))
    if tif_files:
        return tif_files[0]

    raise FileNotFoundError(
        f"No working DTM GeoTIFF found in: {paths.TERRAIN_STAGING}. "
        "Export or place a clean GeoTIFF there first."
    )


def choose_label_field(gdf: gpd.GeoDataFrame):
    for field in CANDIDATE_LABEL_FIELDS:
        if field in gdf.columns:
            return field
    return None


def summarize_polygon(src, geom_mapping):
    """Return min, max, mean, count for one polygon geometry."""
    try:
        out_image, _ = mask(src, [geom_mapping], crop=True, filled=True)
    except ValueError:
        return {
            "valid_pixel_count": 0,
            "elev_min_m": None,
            "elev_max_m": None,
            "elev_mean_m": None,
            "notes": "No overlap with DTM",
        }

    band = out_image[0]
    nodata = src.nodata

    if nodata is not None:
        valid = band[band != nodata]
    else:
        valid = band.flatten()

    valid = valid[np.isfinite(valid)]

    if valid.size == 0:
        return {
            "valid_pixel_count": 0,
            "elev_min_m": None,
            "elev_max_m": None,
            "elev_mean_m": None,
            "notes": "Only nodata inside polygon",
        }

    return {
        "valid_pixel_count": int(valid.size),
        "elev_min_m": float(valid.min()),
        "elev_max_m": float(valid.max()),
        "elev_mean_m": float(valid.mean()),
        "notes": None,
    }


def align_voie_crs_to_dtm(gdf: gpd.GeoDataFrame, dtm_crs):
    """Handle CRS alignment conservatively.

    Cases:
    - if CRS is missing -> assume EPSG:2154 only if this is the cleaned project file
    - if CRS already equals DTM CRS -> keep as is
    - if CRS differs -> reproject to DTM CRS
    """
    if gdf.crs is None:
        print(f"[WARNING] voie has no CRS metadata. Assigning EPSG:{TARGET_EPSG}.")
        gdf = gdf.set_crs(TARGET_EPSG, allow_override=True)
        return gdf

    # Try exact EPSG match first
    try:
        gdf_epsg = gdf.crs.to_epsg()
    except Exception:
        gdf_epsg = None

    try:
        dtm_epsg = dtm_crs.to_epsg()
    except Exception:
        dtm_epsg = None

    if gdf_epsg == dtm_epsg and gdf_epsg is not None:
        print(f"[INFO] voie CRS already matches DTM EPSG:{gdf_epsg}")
        return gdf

    # If text differs but both look like Lambert-93 project workflow, still reproject safely.
    if gdf.crs != dtm_crs:
        print(f"[INFO] Reprojecting voie to DTM CRS: {dtm_crs}")
        gdf = gdf.to_crs(dtm_crs)
    else:
        print("[INFO] voie CRS already matches DTM CRS exactly")

    return gdf


def main():
    try:
        paths.ensure_directories()

        dtm_path = find_working_dtm()
        print(f"[INFO] Using working DTM: {dtm_path}")
        print(f"[INFO] Using track_area file: {VOIE_FILE}")

        if not VOIE_FILE.exists():
            raise FileNotFoundError(f"Track area file not found: {VOIE_FILE}")

        # Read GIS layer
        gdf = gpd.read_file(VOIE_FILE)
        if gdf.empty:
            raise ValueError("voie_fixed.gpkg is empty")

        print(f"[INFO] voie feature count: {len(gdf)}")
        print(f"[INFO] voie CRS: {gdf.crs}")
        print(f"[INFO] voie geometry types: {sorted(set(gdf.geom_type.astype(str)))}")

        with rasterio.open(dtm_path) as src:
            print(f"[INFO] DTM CRS: {src.crs}")
            print(f"[INFO] DTM resolution: {src.res}")
            print(f"[INFO] DTM bounds: {src.bounds}")
            print(f"[INFO] DTM nodata: {src.nodata}")

            if src.crs is None:
                raise ValueError("DTM has no CRS")

            gdf = align_voie_crs_to_dtm(gdf, src.crs)

            label_field = choose_label_field(gdf)
            if label_field:
                print(f"[INFO] Using label field: {label_field}")
            else:
                print("[INFO] No obvious ID/code/name field found; using feature_index")

            summary_rows = []
            enriched = gdf.copy()
            total_features = len(gdf)

            for idx, row in gdf.iterrows():
                progress = len(summary_rows) + 1
                print(f"[INFO] Processing feature {progress} of {total_features}")

                geom = row.geometry
                if geom is None or geom.is_empty:
                    summary = {
                        "valid_pixel_count": 0,
                        "elev_min_m": None,
                        "elev_max_m": None,
                        "elev_mean_m": None,
                        "notes": "Null or empty geometry",
                    }
                else:
                    summary = summarize_polygon(src, geom.__geo_interface__)

                feature_label = row[label_field] if label_field else idx
                summary_row = {
                    "feature_index": idx,
                    "feature_label": feature_label,
                    **summary,
                }
                summary_rows.append(summary_row)

                enriched.loc[idx, "elev_min_m"] = summary["elev_min_m"]
                enriched.loc[idx, "elev_max_m"] = summary["elev_max_m"]
                enriched.loc[idx, "elev_mean_m"] = summary["elev_mean_m"]
                enriched.loc[idx, "valid_pixel_count"] = summary["valid_pixel_count"]
                enriched.loc[idx, "dtm_notes"] = summary["notes"]

                print(
                    f"[INFO] Finished feature {progress}: "
                    f"min={summary['elev_min_m']}, "
                    f"max={summary['elev_max_m']}, "
                    f"mean={summary['elev_mean_m']}, "
                    f"pixels={summary['valid_pixel_count']}"
                )

        # Save CSV summary
        summary_df = pd.DataFrame(summary_rows)
        csv_path = paths.TERRAIN_PROCESSED / "track_area_elevation_summary.csv"
        summary_df.to_csv(csv_path, index=False, encoding="utf-8")

        # Save enriched GeoPackage
        gpkg_path = paths.TERRAIN_PROCESSED / "voie_with_elevation.gpkg"
        enriched.to_file(gpkg_path, driver="GPKG")

        print("\n[SUCCESS] Terrain summaries created successfully")
        print(f"[OUTPUT] CSV summary: {csv_path}")
        print(f"[OUTPUT] Enriched GeoPackage: {gpkg_path}")
        print("\n[INFO] Summary table preview:")
        print(summary_df)

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
