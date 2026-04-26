import json
import numpy as np
from pathlib import Path
import logging

# Use the canonical path resolver — never hardcode paths
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.utils.paths import ProjectPaths

paths = ProjectPaths()
logger = logging.getLogger(__name__)

# =====================================================================
# AI COPILOT TASK 1: SYNTHETIC 2D INUNDATION MAP (BATHTUB MODEL)
# =====================================================================
#
# GOAL: Compare the DTM terrain raster against the peak WSE for Voie_0.
#       Any area where (terrain Z < peak WSE) is "flooded".
#       Export these flooded pixels as a GeoJSON polygon file.
#
# WHY: This gives the dashboard a 2D blue flood overlay on the map,
#      proving the UI architecture supports spatial flood data before
#      the real HEC-RAS 2D results are available.
#
# LIBRARIES NEEDED: rasterio, numpy, geopandas, shapely, rasterio.features
#
# OUTPUT: data/processed/synthetic_flood.geojson  (EPSG:4326)
# =====================================================================


def generate_flood_polygon(
    dtm_path: Path = None,
    wse_path: Path = None,
    output_path: Path = None,
    asset_key: str = "Voie_0",
) -> Path:
    """
    Generate a synthetic flood extent polygon using the 'bathtub' method.

    The bathtub method marks any terrain pixel as flooded if its elevation
    is below the peak Water Surface Elevation (WSE) of the specified asset.

    Args:
        dtm_path: Path to the DTM GeoTIFF (EPSG:2154). Defaults to canonical path.
        wse_path: Path to hecras_wse_results.json. Defaults to canonical path.
        output_path: Where to save the GeoJSON polygon. Defaults to canonical path.
        asset_key: Which asset's peak WSE to use as the flood level. Default: Voie_0.

    Returns:
        Path to the written GeoJSON file.

    Pseudo-code for implementation:
    --------------------------------
    STEP 1 — Load peak WSE:
        Read hecras_wse_results.json.
        Get wse_series = data[asset_key]['wse_m']  (list of 48 floats)
        peak_wse = max(wse_series)
        Log: f"Using peak WSE = {peak_wse:.2f}m for asset {asset_key}"

    STEP 2 — Open DTM raster with rasterio:
        with rasterio.open(dtm_path) as src:
            dtm_array = src.read(1)           # 2D numpy array
            transform = src.transform
            crs = src.crs                     # Should be EPSG:2154

    STEP 3 — Create flood mask:
        nodata = src.nodata or -9999
        flood_mask = (dtm_array < peak_wse) & (dtm_array > nodata + 1)
        Convert flood_mask to uint8 (1=flooded, 0=dry) for rasterio.

    STEP 4 — Vectorize the mask:
        from rasterio.features import shapes
        from shapely.geometry import shape
        shapes_gen = shapes(flood_mask.astype('uint8'), transform=transform)
        polygons = [shape(geom) for geom, val in shapes_gen if val == 1]
        Log: f"Generated {len(polygons)} flood polygon(s)"

    STEP 5 — Export as GeoJSON in EPSG:4326:
        import geopandas as gpd
        gdf = gpd.GeoDataFrame(geometry=polygons, crs=crs)
        gdf = gdf.to_crs("EPSG:4326")         # Convert for PyDeck
        gdf.to_file(str(output_path), driver="GeoJSON")
        Return output_path
    """

    # TODO (AI COPILOT): Implement the pseudo-code above.
    # Use the paths below — do not hardcode.

    if dtm_path is None:
        dtm_path = paths.STAGING / "terrain" / "dtm_fixed.tif"
    if wse_path is None:
        wse_path = paths.PROCESSED_DATA / "hecras_wse_results.json"
    if output_path is None:
        output_path = paths.PROCESSED_DATA / "synthetic_flood.geojson"

    logger.info("Starting synthetic inundation generation...")

    # ---- Your implementation goes here ----
    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = generate_flood_polygon()
    if out:
        logger.info(f"Flood polygon saved to: {out}")
