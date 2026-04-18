from pathlib import Path
import sys
import json
import time
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds

# -------------------------------------------------------------------
# Derive terrain summaries for track_area polygons from the DTM
#
# Save this file to:
#   src/transform/derive_track_area_elevation.py
#
# Run from the project root:
#   python src/transform/derive_track_area_elevation.py
#
# Inputs:
#   - data/raw/dtm/PK520_PK535_NO_HOLES.asc (or first .asc in raw/dtm)
#   - data/staging/gis/voie_fixed.gpkg
#
# Outputs:
#   - data/processed/terrain/track_area_elevation_summary.csv
#   - data/processed/terrain/voie_with_elevation.gpkg
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DTM_DIR = PROJECT_ROOT / "data" / "raw" / "dtm"
STAGING_GIS = PROJECT_ROOT / "data" / "staging" / "gis"
PROCESSED_TERRAIN = PROJECT_ROOT / "data" / "processed" / "terrain"

DTM_FILE = None  # if None, the script will use the first .asc file found
VOIE_FILE = STAGING_GIS / "voie_fixed.gpkg"
TARGET_EPSG = 2154

# Optional candidate ID/code/name fields. The script will use the first one it finds.
CANDIDATE_ID_FIELDS = [
    "id", "ID", "Id", "fid", "FID", "code", "CODE", "Code", "name", "NAME", "Name"
]


def find_dtm_file() -> Path:
    if DTM_FILE:
        path = RAW_DTM_DIR / DTM_FILE
        if not path.exists():
            raise FileNotFoundError(f"Configured DTM file not found: {path}")
        return path

    asc_files = sorted(RAW_DTM_DIR.glob("*.asc"))
    if not asc_files:
        raise FileNotFoundError(f"No .asc DTM file found in: {RAW_DTM_DIR}")
    return asc_files[0]



def choose_label_field(gdf: gpd.GeoDataFrame):
    for field in CANDIDATE_ID_FIELDS:
        if field in gdf.columns:
            return field
    return None



def summarize_polygon(src, geom):
    """Return min, max, mean, count for one polygon geometry."""
    if geom is None or geom.is_empty:
        return {
            "valid_pixel_count": 0,
            "elev_min_m": None,
            "elev_max_m": None,
            "elev_mean_m": None,
            "notes": "Null or empty geometry",
        }

    full_window = Window(0, 0, src.width, src.height)
    nodata = src.nodata

    total_count = 0
    total_sum = 0.0
    total_min = None
    total_max = None

    geoms = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]

    for part in geoms:
        if part.is_empty:
            continue

        # Slight simplification keeps processing stable for dense boundaries.
        part = part.simplify(0.2, preserve_topology=True)

        minx, miny, maxx, maxy = part.bounds
        try:
            window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
            window = window.round_offsets().round_lengths()
            window = window.intersection(full_window)
        except ValueError:
            continue

        if window.width <= 0 or window.height <= 0:
            continue

        band = src.read(1, window=window)
        if band.size == 0:
            continue

        w_transform = src.window_transform(window)
        inside = geometry_mask(
            [part.__geo_interface__],
            out_shape=band.shape,
            transform=w_transform,
            invert=True,
        )
        if not inside.any():
            continue

        valid = band[inside]
        if nodata is not None:
            valid = valid[valid != nodata]
        valid = valid[np.isfinite(valid)]

        if valid.size == 0:
            continue

        part_min = float(valid.min())
        part_max = float(valid.max())
        part_sum = float(valid.sum())
        part_count = int(valid.size)

        total_count += part_count
        total_sum += part_sum
        total_min = part_min if total_min is None else min(total_min, part_min)
        total_max = part_max if total_max is None else max(total_max, part_max)

    if total_count == 0:
        return {
            "valid_pixel_count": 0,
            "elev_min_m": None,
            "elev_max_m": None,
            "elev_mean_m": None,
            "notes": "No overlap with DTM or only nodata",
        }

    return {
        "valid_pixel_count": total_count,
        "elev_min_m": total_min,
        "elev_max_m": total_max,
        "elev_mean_m": float(total_sum / total_count),
        "notes": None,
    }



def main():
    try:
        PROCESSED_TERRAIN.mkdir(parents=True, exist_ok=True)

        dtm_path = find_dtm_file()
        print(f"[INFO] Using DTM: {dtm_path}")
        print(f"[INFO] Using track_area file: {VOIE_FILE}")

        if not VOIE_FILE.exists():
            raise FileNotFoundError(f"Track area file not found: {VOIE_FILE}")

        # Read GIS layer
        gdf = gpd.read_file(VOIE_FILE)
        if gdf.empty:
            raise ValueError("voie_fixed.gpkg is empty")

        print(f"[INFO] voie features: {len(gdf)}")
        print(f"[INFO] voie CRS: {gdf.crs}")
        print(f"[INFO] voie geometry types: {sorted(set(gdf.geom_type.astype(str)))}")

        # Ensure vector CRS is set and aligned
        if gdf.crs is None:
            raise ValueError("voie_fixed.gpkg has no CRS")

        with rasterio.open(dtm_path) as src:
            print(f"[INFO] DTM CRS: {src.crs}")
            print(f"[INFO] DTM resolution: {src.res}")
            print(f"[INFO] DTM bounds: {src.bounds}")
            print(f"[INFO] DTM nodata: {src.nodata}")

            if src.crs is None:
                raise ValueError("DTM has no CRS")

            if gdf.crs != src.crs:
                print(f"[INFO] Reprojecting voie to DTM CRS: {src.crs}")
                gdf = gdf.to_crs(src.crs)

            invalid_count = int((~gdf.geometry.is_valid).sum())
            if invalid_count > 0:
                print(f"[INFO] Repairing {invalid_count} invalid geometry(ies) with buffer(0)")
                gdf["geometry"] = gdf.geometry.buffer(0)

            label_field = choose_label_field(gdf)
            if label_field:
                print(f"[INFO] Using label field: {label_field}")
            else:
                print("[INFO] No obvious ID/code/name field found; using feature_index")

            summary_rows = []
            enriched = gdf.copy()
            total_features = len(gdf)
            started = time.time()

            for idx, row in gdf.iterrows():
                elapsed = time.time() - started
                print(
                    f"[INFO] Processing feature {idx + 1}/{total_features} (elapsed: {elapsed:.1f}s)",
                    flush=True,
                )
                geom = row.geometry
                if geom is None or geom.is_empty:
                    summary = {
                        "valid_pixel_count": 0,
                        "elev_min_m": None,
                        "elev_max_m": None,
                        "elev_mean_m": None,
                        "notes": "Null or empty geometry"
                    }
                else:
                    summary = summarize_polygon(src, geom)

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

            print(f"[INFO] Completed {total_features} feature(s) in {time.time() - started:.1f}s", flush=True)

        # Save CSV summary
        summary_df = pd.DataFrame(summary_rows)
        csv_path = PROCESSED_TERRAIN / "track_area_elevation_summary.csv"
        summary_df.to_csv(csv_path, index=False, encoding="utf-8")

        # Save enriched GeoPackage
        gpkg_path = PROCESSED_TERRAIN / "voie_with_elevation.gpkg"
        enriched.to_file(gpkg_path, driver="GPKG")

        print("\n[SUCCESS] Terrain summaries created successfully")
        print(f"[OUTPUT] CSV summary: {csv_path}")
        print(f"[OUTPUT] Enriched GeoPackage: {gpkg_path}")
        print("\n[INFO] Preview of summary:")
        print(summary_df)

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
