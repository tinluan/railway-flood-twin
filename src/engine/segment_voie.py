"""Segment Voie_0 into ~100m sections with DTM elevation sampling."""
import json
import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import Point, LineString
from shapely.ops import unary_union

# 1. Load Voie geometry
gdf = gpd.read_file("data/staging/gis/voie_fixed.gpkg")
gdf = gdf.set_crs("EPSG:2154", allow_override=True)
voie_poly = unary_union(gdf.geometry)

# Extract one side of the polygon as reference line
exterior = voie_poly.exterior
coords = list(exterior.coords)
mid_idx = len(coords) // 2
side1 = LineString(coords[:mid_idx])
side2 = LineString(coords[mid_idx:])
ref_line = side1 if side1.length > side2.length else side2
track_length = ref_line.length
print(f"Track reference length: {track_length:.0f}m")

# 2. Segment into ~100m sections
SEGMENT_LENGTH = 100
n_segments = max(1, int(track_length / SEGMENT_LENGTH))
print(f"Creating {n_segments} segments")

# 3. Sample DTM at each segment centroid
src = rasterio.open("data/staging/terrain/dtm_fixed.tif")

segments = []
for i in range(n_segments):
    frac_mid = (i + 0.5) / n_segments
    pt = ref_line.interpolate(frac_mid, normalized=True)

    # Sample DTM — use windowed read to avoid loading entire 1GB band
    try:
        row, col = src.index(pt.x, pt.y)
        if 0 <= row < src.height and 0 <= col < src.width:
            window = rasterio.windows.Window(col, row, 1, 1)
            z_val = float(src.read(1, window=window)[0, 0])
            if z_val < -9000 or z_val > 5000:  # nodata check
                z_val = None
        else:
            z_val = None
    except Exception:
        z_val = None

    # Convert to EPSG:4326
    pt_gdf = gpd.GeoDataFrame([{"geometry": pt}], crs="EPSG:2154")
    pt_4326 = pt_gdf.to_crs("EPSG:4326")
    lon = float(pt_4326.geometry.iloc[0].x)
    lat = float(pt_4326.geometry.iloc[0].y)

    segments.append({
        "name": f"Voie_seg_{i:02d}",
        "asset_type": "Voie (Track)",
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "z_dtm": round(z_val, 2) if z_val is not None else None,
        "segment_idx": i,
    })

src.close()

# Interpolate missing Z values from nearest neighbors
valid_z = [(s["segment_idx"], s["z_dtm"]) for s in segments if s["z_dtm"] is not None]
if valid_z:
    for s in segments:
        if s["z_dtm"] is None:
            # Find nearest valid segment
            nearest = min(valid_z, key=lambda v: abs(v[0] - s["segment_idx"]))
            s["z_dtm"] = nearest[1]
            print(f"  Interpolated {s['name']}: Z={s['z_dtm']}m from seg_{nearest[0]:02d}")

# Filter out any still-None segments
segments = [s for s in segments if s["z_dtm"] is not None]

# Show results
segments_sorted = sorted(segments, key=lambda s: s["z_dtm"])
print(f"Z range: {segments_sorted[0]['z_dtm']}m to {segments_sorted[-1]['z_dtm']}m")
for s in segments:
    print(f"  {s['name']}: Z={s['z_dtm']}m  lat={s['lat']:.5f}")

# 4. Generate z_config entries and WSE results for each segment
z_config = json.load(open("data/processed/z_config.json"))
wse_results = json.load(open("data/processed/hecras_wse_results.json"))

# Get Voie_0's WSE series as template
voie0_wse = wse_results.get("Voie_0", {})
voie0_wse_series = voie0_wse.get("wse_m", [])
voie0_timestamps = voie0_wse.get("timestamps", [])

# Remove old monolithic Voie_0
if "Voie_0" in z_config:
    del z_config["Voie_0"]
if "Voie_0" in wse_results:
    del wse_results["Voie_0"]

for seg in segments:
    name = seg["name"]
    z = seg["z_dtm"]

    # Thresholds relative to this segment's actual elevation
    # Track surface = z_dtm, drainage is 2m below, embankment 1m below
    yellow_z = round(z - 2.0, 2)   # drainage capacity
    orange_z = round(z - 0.5, 2)   # embankment soaked
    red_z = round(z, 2)            # track submerged

    z_config[name] = {
        "yellow_z_m": yellow_z,
        "orange_z_m": orange_z,
        "red_z_m": red_z,
        "nearest_talus": "Talus Terre_12",
        "nearest_voie": name,
    }

    # WSE series: same corridor-wide water level for all segments
    wse_results[name] = {
        "timestamps": voie0_timestamps,
        "wse_m": voie0_wse_series,
        "base_z_m": round(z - 3.0, 2),
        "yellow_z_m": yellow_z,
        "orange_z_m": orange_z,
        "red_z_m": red_z,
        "peak_wse_m": max(voie0_wse_series) if voie0_wse_series else z,
        "peak_hour": 25,
    }

# Save updated configs
with open("data/processed/z_config.json", "w") as f:
    json.dump(z_config, f, indent=2)
with open("data/processed/hecras_wse_results.json", "w") as f:
    json.dump(wse_results, f, indent=2)

# Save segments metadata
with open("data/processed/voie_segments.json", "w") as f:
    json.dump(segments, f, indent=2)

print(f"\nSaved {len(segments)} segments to z_config, wse_results, and voie_segments.json")
print("Removed monolithic Voie_0 entry.")
