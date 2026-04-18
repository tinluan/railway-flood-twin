from pathlib import Path
import argparse
import sys
import time

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from affine import Affine

# -------------------------------------------------------------------
# Fast terrain summary for track_area polygons from DTM
#
# Run from project root:
#   python src/transform/derive_track_area_elevation_fast.py
#
# Example with custom speed settings:
#   python src/transform/derive_track_area_elevation_fast.py --sample-step 6 --simplify 1.5
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DTM_DIR = PROJECT_ROOT / "data" / "raw" / "dtm"
STAGING_GIS = PROJECT_ROOT / "data" / "staging" / "gis"
PROCESSED_TERRAIN = PROJECT_ROOT / "data" / "processed" / "terrain"

DEFAULT_DTM_FILE = None
DEFAULT_VOIE_FILE = STAGING_GIS / "voie_fixed.gpkg"

CANDIDATE_ID_FIELDS = [
    "id", "ID", "Id", "fid", "FID", "code", "CODE", "Code", "name", "NAME", "Name"
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Derive elevation summaries for voie polygons with configurable speed/accuracy settings."
    )
    parser.add_argument("--dtm-file", default=DEFAULT_DTM_FILE, help="Optional .asc filename in data/raw/dtm")
    parser.add_argument("--voie-file", default=str(DEFAULT_VOIE_FILE), help="Path to voie GeoPackage")
    parser.add_argument(
        "--sample-step",
        type=int,
        default=4,
        help="Pixel sampling stride (1=full resolution, 2=every 2nd pixel, 4=every 4th pixel)",
    )
    parser.add_argument(
        "--simplify",
        type=float,
        default=1.0,
        help="Simplification tolerance in CRS units before raster sampling",
    )
    parser.add_argument(
        "--accurate",
        action="store_true",
        help="Disable speed optimizations and run at full pixel resolution",
    )
    return parser.parse_args()


def find_dtm_file(configured_name):
    if configured_name:
        candidate = RAW_DTM_DIR / configured_name
        if not candidate.exists():
            raise FileNotFoundError(f"Configured DTM file not found: {candidate}")
        return candidate

    # Prefer an ASC that has a matching PRJ because it is more likely to preserve CRS metadata.
    asc_files = sorted(RAW_DTM_DIR.glob("*.asc"))
    if not asc_files:
        raise FileNotFoundError(f"No .asc DTM file found in: {RAW_DTM_DIR}")

    for asc in asc_files:
        prj = asc.with_suffix(".prj")
        if prj.exists():
            return asc

    return asc_files[0]


def choose_label_field(gdf):
    for field in CANDIDATE_ID_FIELDS:
        if field in gdf.columns:
            return field
    return None


def summarize_polygon(src, geom, simplify_tolerance, sample_step):
    if geom is None or geom.is_empty:
        return {
            "valid_pixel_count": 0,
            "elev_min_m": None,
            "elev_max_m": None,
            "elev_mean_m": None,
            "notes": "Null or empty geometry",
        }

    nodata = src.nodata
    full_window = Window(0, 0, src.width, src.height)

    total_count = 0
    total_sum = 0.0
    total_min = None
    total_max = None

    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]

    for part in parts:
        if part.is_empty:
            continue

        geom_for_stats = part
        if simplify_tolerance > 0:
            geom_for_stats = part.simplify(simplify_tolerance, preserve_topology=True)

        minx, miny, maxx, maxy = geom_for_stats.bounds
        try:
            window = from_bounds(minx, miny, maxx, maxy, transform=src.transform)
            window = window.round_offsets().round_lengths().intersection(full_window)
        except ValueError:
            continue

        if window.width <= 0 or window.height <= 0:
            continue

        if sample_step > 1:
            out_h = max(1, int(np.ceil(window.height / sample_step)))
            out_w = max(1, int(np.ceil(window.width / sample_step)))
            band = src.read(1, window=window, out_shape=(out_h, out_w), resampling=rasterio.enums.Resampling.bilinear)

            base_transform = src.window_transform(window)
            scaled_transform = base_transform * Affine.scale(window.width / out_w, window.height / out_h)
            mask_inside = geometry_mask(
                [geom_for_stats.__geo_interface__],
                out_shape=band.shape,
                transform=scaled_transform,
                invert=True,
            )
        else:
            band = src.read(1, window=window)
            mask_inside = geometry_mask(
                [geom_for_stats.__geo_interface__],
                out_shape=band.shape,
                transform=src.window_transform(window),
                invert=True,
            )

        if not mask_inside.any():
            continue

        valid = band[mask_inside]
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
        args = parse_args()

        sample_step = 1 if args.accurate else max(1, args.sample_step)
        simplify_tolerance = 0.0 if args.accurate else max(0.0, args.simplify)

        PROCESSED_TERRAIN.mkdir(parents=True, exist_ok=True)

        dtm_path = find_dtm_file(args.dtm_file)
        voie_path = Path(args.voie_file)

        print(f"[INFO] Using DTM: {dtm_path}")
        print(f"[INFO] Using track_area file: {voie_path}")
        print(f"[INFO] Fast mode: {not args.accurate}")
        print(f"[INFO] Sampling step: {sample_step}")
        print(f"[INFO] Simplify tolerance: {simplify_tolerance}")

        if not voie_path.exists():
            raise FileNotFoundError(f"Track area file not found: {voie_path}")

        gdf = gpd.read_file(voie_path)
        if gdf.empty:
            raise ValueError("voie file is empty")

        print(f"[INFO] voie features: {len(gdf)}")
        print(f"[INFO] voie CRS: {gdf.crs}")

        if gdf.crs is None:
            raise ValueError("voie file has no CRS")

        with rasterio.open(dtm_path) as src:
            print(f"[INFO] DTM CRS: {src.crs}")
            print(f"[INFO] DTM resolution: {src.res}")

            if src.crs is None:
                raise ValueError("DTM has no CRS")

            if gdf.crs != src.crs:
                print(f"[INFO] Reprojecting voie to DTM CRS")
                gdf = gdf.to_crs(src.crs)

            invalid_count = int((~gdf.geometry.is_valid).sum())
            if invalid_count > 0:
                print(f"[INFO] Repairing {invalid_count} invalid geometry(ies)")
                gdf["geometry"] = gdf.geometry.buffer(0)

            label_field = choose_label_field(gdf)
            print(f"[INFO] Label field: {label_field if label_field else 'feature_index'}")

            enriched = gdf.copy()
            summary_rows = []

            total = len(gdf)
            started = time.time()

            for i, (idx, row) in enumerate(gdf.iterrows(), start=1):
                elapsed = time.time() - started
                print(f"[INFO] Processing feature {i}/{total} (elapsed {elapsed:.1f}s)", flush=True)

                summary = summarize_polygon(
                    src=src,
                    geom=row.geometry,
                    simplify_tolerance=simplify_tolerance,
                    sample_step=sample_step,
                )

                feature_label = row[label_field] if label_field else idx
                summary_rows.append({
                    "feature_index": idx,
                    "feature_label": feature_label,
                    **summary,
                })

                enriched.loc[idx, "elev_min_m"] = summary["elev_min_m"]
                enriched.loc[idx, "elev_max_m"] = summary["elev_max_m"]
                enriched.loc[idx, "elev_mean_m"] = summary["elev_mean_m"]
                enriched.loc[idx, "valid_pixel_count"] = summary["valid_pixel_count"]
                enriched.loc[idx, "dtm_notes"] = summary["notes"]

        duration = time.time() - started
        print(f"[INFO] Completed in {duration:.1f}s")

        summary_df = pd.DataFrame(summary_rows)
        csv_path = PROCESSED_TERRAIN / "track_area_elevation_summary_fast.csv"
        gpkg_path = PROCESSED_TERRAIN / "voie_with_elevation_fast.gpkg"

        summary_df.to_csv(csv_path, index=False, encoding="utf-8")
        enriched.to_file(gpkg_path, driver="GPKG")

        print("\n[SUCCESS] Fast terrain summaries created")
        print(f"[OUTPUT] {csv_path}")
        print(f"[OUTPUT] {gpkg_path}")

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
