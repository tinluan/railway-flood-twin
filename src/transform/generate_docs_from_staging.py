from pathlib import Path
import geopandas as gpd
import rasterio
from datetime import datetime

# -------------------------------------------------------------------
# Project paths
# This script is intended to be saved at:
#   railway-flood-twin/src/transform/generate_docs_from_staging.py
# and run from the project root with:
#   python src/transform/generate_docs_from_staging.py
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
STAGING_GIS = PROJECT_ROOT / "data" / "staging" / "gis"
RAW_DTM = PROJECT_ROOT / "data" / "raw" / "dtm"
TARGET_SRID = "EPSG:2154"

# Folder / file naming rules -> suggested DB mapping
LAYER_RULES = {
    "voie": {"target_table": "rail.gis_asset", "asset_type": "track_area", "priority": "High"},
    "dalot": {"target_table": "rail.gis_asset", "asset_type": "culvert", "priority": "High"},
    "pont rail": {"target_table": "rail.gis_asset", "asset_type": "bridge", "priority": "High"},
    "pont_rail": {"target_table": "rail.gis_asset", "asset_type": "bridge", "priority": "High"},
    "descente d'eau": {"target_table": "rail.gis_asset", "asset_type": "drainage_asset", "priority": "High"},
    "descente_eau": {"target_table": "rail.gis_asset", "asset_type": "drainage_asset", "priority": "High"},
    "drainage longitudinal à ciel ouvert": {"target_table": "rail.gis_asset", "asset_type": "open_drain", "priority": "High"},
    "drainage_longitudinal_a_ciel_ouvert": {"target_table": "rail.gis_asset", "asset_type": "open_drain", "priority": "High"},
    "drainage_longitudinal_à_ciel_ouvert": {"target_table": "rail.gis_asset", "asset_type": "open_drain", "priority": "High"},
    "fossé terre": {"target_table": "rail.gis_asset", "asset_type": "ditch_earth", "priority": "Medium"},
    "fosse terre": {"target_table": "rail.gis_asset", "asset_type": "ditch_earth", "priority": "Medium"},
    "fosse_terre": {"target_table": "rail.gis_asset", "asset_type": "ditch_earth", "priority": "Medium"},
    "fossé terre revêtu": {"target_table": "rail.gis_asset", "asset_type": "ditch_lined", "priority": "Medium"},
    "fosse terre revetu": {"target_table": "rail.gis_asset", "asset_type": "ditch_lined", "priority": "Medium"},
    "fosse_terre_revetu": {"target_table": "rail.gis_asset", "asset_type": "ditch_lined", "priority": "Medium"},
    "talus terre": {"target_table": "rail.gis_asset", "asset_type": "earth_slope", "priority": "Medium"},
    "talus_terre": {"target_table": "rail.gis_asset", "asset_type": "earth_slope", "priority": "Medium"},
    "routes": {"target_table": "rail.gis_asset", "asset_type": "road", "priority": "Medium"},
    "reseau tiers": {"target_table": "TBD", "asset_type": "TBD", "priority": "Low"},
    "reseau_tiers": {"target_table": "TBD", "asset_type": "TBD", "priority": "Low"},
    "base": {"target_table": "TBD", "asset_type": "TBD", "priority": "Low"},
    "tunnel": {"target_table": "rail.gis_asset", "asset_type": "tunnel", "priority": "Medium"},
}


def normalize_name(text: str) -> str:
    return (
        text.lower()
        .replace("_fixed", "")
        .replace(".gpkg", "")
        .replace(".shp", "")
        .replace("-", " ")
        .replace("__", " ")
        .strip()
    )


def guess_rule(file_stem: str):
    key = normalize_name(file_stem)
    # direct match first
    if key in LAYER_RULES:
        return LAYER_RULES[key]
    # partial match fallback
    for candidate, rule in LAYER_RULES.items():
        if candidate in key:
            return rule
    return {"target_table": "TBD", "asset_type": "TBD", "priority": "Low"}


def inspect_vector_file(path: Path):
    gdf = gpd.read_file(path)
    crs = str(gdf.crs) if gdf.crs else "Unknown"
    geometry_types = ", ".join(sorted(set(gdf.geom_type.astype(str))))
    feature_count = len(gdf)
    fields = ", ".join(list(gdf.columns))
    invalid_geoms = int((~gdf.geometry.is_valid).sum()) if gdf.geometry is not None else 0
    null_geoms = int(gdf.geometry.isna().sum()) if gdf.geometry is not None else 0

    rule = guess_rule(path.stem)

    return {
        "dataset_name": path.stem,
        "source_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "type": path.suffix.lower().replace(".", "").upper(),
        "geometry": geometry_types,
        "crs": crs,
        "target_table": rule["target_table"],
        "asset_type": rule["asset_type"],
        "priority": rule["priority"],
        "feature_count": feature_count,
        "fields": fields,
        "notes": f"null_geometries={null_geoms}; invalid_geometries={invalid_geoms}",
    }


def inspect_raster():
    asc_files = sorted(RAW_DTM.glob("*.asc"))
    if not asc_files:
        return None

    asc = asc_files[0]
    with rasterio.open(asc) as src:
        crs = str(src.crs) if src.crs else "Unknown"
        return {
            "dataset_name": asc.stem,
            "source_path": str(asc.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "type": "ASC",
            "geometry": "Raster",
            "crs": crs,
            "target_table": "external terrain workflow first",
            "asset_type": "terrain_source",
            "priority": "High",
            "feature_count": f"{src.width}x{src.height}",
            "fields": f"resolution={src.res}; nodata={src.nodata}",
            "notes": "Terrain source for elevation summaries",
        }


def generate_data_inventory(records):
    lines = []
    lines.append("# Data Inventory\n")
    lines.append("> Auto-generated from `data/staging/gis/` and `data/raw/dtm/`. Review manually if needed.\n")
    lines.append("| Dataset name | Source path | Type | Geometry / Raster | CRS | Target table | Current status | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in records:
        lines.append(
            f"| {r['dataset_name']} | `{r['source_path']}` | {r['type']} | {r['geometry']} | {r['crs']} | "
            f"`{r['target_table']}` | Inspected | {r['notes']} |"
        )
    return "\n".join(lines) + "\n"


def generate_source_mapping(records):
    lines = []
    lines.append("# Source to Table Mapping\n")
    lines.append("> Auto-generated from cleaned staging files. Review manually.\n")
    lines.append("| Source file | Target database table | Suggested asset_type | Loading priority | Notes |")
    lines.append("|---|---|---|---|---|")
    for r in records:
        lines.append(
            f"| `{Path(r['source_path']).name}` | `{r['target_table']}` | `{r['asset_type']}` | {r['priority']} | geometry={r['geometry']} |"
        )
    return "\n".join(lines) + "\n"


def generate_crs_strategy(records):
    lines = []
    lines.append("# CRS Strategy\n")
    lines.append("> Auto-generated first draft from cleaned files.\n")
    lines.append(f"## Preferred project target CRS\n`{TARGET_SRID}`\n")
    lines.append("## Observed source CRS\n")
    lines.append("| Dataset | Source path | Observed CRS | Action |")
    lines.append("|---|---|---|---|")
    for r in records:
        action = "OK - already aligned" if r["crs"] != "Unknown" else "Investigate"
        lines.append(f"| {r['dataset_name']} | `{r['source_path']}` | {r['crs']} | {action} |")
    lines.append("\n## Rule")
    lines.append("- Keep raw files unchanged in `data/raw/`.")
    lines.append("- Run code on cleaned files in `data/staging/gis/`.")
    lines.append("- Use `EPSG:2154` for database loading if all cleaned layers are confirmed in Lambert-93.")
    return "\n".join(lines) + "\n"


def append_implementation_notes(records):
    notes_file = DOCS_DIR / "implementation_notes.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = [f"\n## {now}", "- Ran `generate_docs_from_staging.py`."]
    for r in records:
        block.append(
            f"- {r['dataset_name']}: path={r['source_path']}; geometry={r['geometry']}; CRS={r['crs']}; target={r['target_table']}"
        )
    existing = notes_file.read_text(encoding="utf-8") if notes_file.exists() else "# Implementation Notes\n"
    notes_file.write_text(existing + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    records = []

    # cleaned vector files from staging
    gpkg_files = sorted(STAGING_GIS.glob("*.gpkg"))
    for gpkg in gpkg_files:
        records.append(inspect_vector_file(gpkg))

    # raster from raw DTM
    raster_record = inspect_raster()
    if raster_record:
        records.append(raster_record)

    (DOCS_DIR / "data_inventory.md").write_text(generate_data_inventory(records), encoding="utf-8")
    (DOCS_DIR / "source_to_table_mapping.md").write_text(generate_source_mapping(records), encoding="utf-8")
    (DOCS_DIR / "crs_strategy.md").write_text(generate_crs_strategy(records), encoding="utf-8")
    append_implementation_notes(records)

    print("Documents updated successfully:")
    print("- docs/data_inventory.md")
    print("- docs/source_to_table_mapping.md")
    print("- docs/crs_strategy.md")
    print("- docs/implementation_notes.md")
    print(f"\nInspected {len(gpkg_files)} cleaned vector file(s) from data/staging/gis/")


if __name__ == "__main__":
    main()
