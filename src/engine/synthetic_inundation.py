"""
Synthetic 2D Inundation Map Generator (Bathtub Model)
=====================================================
Generates time-varying flood extent polygons based on the WSE from
hecras_wse_results.json and the railway corridor geometry.

For the DEMO MODE: Since the full DTM (~1GB) may not be locally available,
this script uses a corridor-based buffer approach around the track and
low-lying assets to create realistic-looking flood polygons at each timestep.

When the real HEC-RAS 2D output is available, replace this with actual
RAS Mapper flood boundary shapefiles.

Output: data/processed/synthetic_flood_timesteps.json
  A JSON file containing 48 GeoJSON FeatureCollections (one per hour),
  keyed by timestep index ("0", "1", ..., "47").
"""

import json
import sys
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path setup — use canonical paths when available, fallback for standalone run
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.utils.paths import ProjectPaths
    paths = ProjectPaths()
    PROCESSED = paths.PROCESSED_DATA
    GIS_DIR = paths.STAGING / "gis" if hasattr(paths, 'STAGING') else paths.ROOT / "data" / "staging" / "gis"
except Exception:
    PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
    GIS_DIR = Path(__file__).resolve().parents[2] / "data" / "staging" / "gis"


def generate_time_varying_flood(
    wse_path: Path = None,
    voie_path: Path = None,
    output_path: Path = None,
) -> Path:
    """
    Generate time-varying synthetic flood polygons for 48 timesteps.

    Strategy (Demo Mode — Corridor Buffer):
    1. Load the Voie (track) centerline geometry.
    2. For each timestep, compute a "flood intensity" ratio from WSE.
    3. Buffer the track geometry by an amount proportional to flood intensity.
    4. Export all 48 GeoJSON FeatureCollections in a single JSON file.
    """
    import geopandas as gpd
    from shapely.ops import unary_union
    from shapely.geometry import mapping

    if wse_path is None:
        wse_path = PROCESSED / "hecras_wse_results.json"
    if voie_path is None:
        voie_path = GIS_DIR / "voie_fixed.gpkg"
    if output_path is None:
        output_path = PROCESSED / "synthetic_flood_timesteps.json"

    # --- 1. Load WSE data ---
    with open(wse_path, "r") as f:
        wse_data = json.load(f)

    voie_wse = wse_data.get("Voie_0", {})
    wse_series = voie_wse.get("wse_m", [])
    base_z = voie_wse.get("base_z_m", 203.81)
    peak_wse = max(wse_series) if wse_series else base_z

    logger.info(f"WSE range: {base_z:.2f}m (base) to {peak_wse:.2f}m (peak)")
    logger.info(f"Timesteps: {len(wse_series)}")

    # --- 2. Load track geometry (EPSG:2154, metres) ---
    gdf_voie = gpd.read_file(voie_path)
    # Ensure we work in projected CRS (metres) for buffering
    if gdf_voie.crs is None or gdf_voie.crs.to_epsg() != 2154:
        gdf_voie = gdf_voie.set_crs("EPSG:2154", allow_override=True)

    track_union = unary_union(gdf_voie.geometry)

    # Also load low-lying asset geometries for more realistic flood shape
    flood_seed_geoms = [track_union]
    for asset_file in ["Buse_fixed.gpkg", "Dalot_fixed.gpkg"]:
        asset_path = GIS_DIR / asset_file
        if asset_path.exists():
            try:
                gdf_asset = gpd.read_file(asset_path)
                if gdf_asset.crs is None or gdf_asset.crs.to_epsg() != 2154:
                    gdf_asset = gdf_asset.set_crs("EPSG:2154", allow_override=True)
                flood_seed_geoms.append(unary_union(gdf_asset.geometry))
            except Exception:
                pass

    seed_union = unary_union(flood_seed_geoms)

    # --- 3. Generate flood polygons per timestep ---
    # Flood intensity = how far WSE is above base, as fraction of (peak - base)
    wse_range = peak_wse - base_z
    if wse_range <= 0:
        wse_range = 1.0  # prevent division by zero

    # Max buffer = 120m corridor width at peak flood (realistic for a valley)
    MAX_BUFFER_M = 120.0
    MIN_BUFFER_M = 5.0  # tiny sliver even at low water (shows the channel)

    timestep_geojsons = {}

    for t_idx, wse_val in enumerate(wse_series):
        intensity = max(0.0, min(1.0, (wse_val - base_z) / wse_range))

        if intensity < 0.01:
            # No visible flood at this timestep
            timestep_geojsons[str(t_idx)] = {
                "type": "FeatureCollection",
                "features": []
            }
            continue

        # Buffer distance scales with intensity (quadratic for visual drama)
        buffer_m = MIN_BUFFER_M + (MAX_BUFFER_M - MIN_BUFFER_M) * (intensity ** 1.5)

        # Create the flood polygon by buffering the seed geometry
        flood_poly = seed_union.buffer(buffer_m, resolution=8)

        # Simplify for performance (tolerance 2m — invisible at map zoom)
        flood_poly = flood_poly.simplify(2.0)

        # Convert to EPSG:4326 for PyDeck
        flood_gdf = gpd.GeoDataFrame(
            [{"geometry": flood_poly, "wse_m": round(wse_val, 2), "intensity": round(intensity, 3)}],
            crs="EPSG:2154"
        )
        flood_gdf = flood_gdf.to_crs("EPSG:4326")

        # Build GeoJSON FeatureCollection
        features = []
        for _, row in flood_gdf.iterrows():
            features.append({
                "type": "Feature",
                "geometry": mapping(row.geometry),
                "properties": {
                    "wse_m": row["wse_m"],
                    "intensity": row["intensity"],
                }
            })

        timestep_geojsons[str(t_idx)] = {
            "type": "FeatureCollection",
            "features": features
        }

        if t_idx % 10 == 0:
            logger.info(f"  T+{t_idx}h: WSE={wse_val:.2f}m, intensity={intensity:.2f}, buffer={buffer_m:.0f}m")

    # --- 4. Save ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(timestep_geojsons, f)

    logger.info(f"Saved {len(timestep_geojsons)} timestep flood polygons to {output_path}")
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = generate_time_varying_flood()
    if out:
        logger.info(f"Done. Output: {out}")
