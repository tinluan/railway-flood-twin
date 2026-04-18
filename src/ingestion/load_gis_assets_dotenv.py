from pathlib import Path
import json
import os
import sys
from urllib.parse import quote, unquote
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Reusable GIS asset loader for the railway flood-risk digital twin MVP
#
# Save this file to:
#   src/ingestion/load_gis_assets.py
#
# Create a file named .env in the project root with:
#   DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
#
# Run from the project root:
#   python src/ingestion/load_gis_assets.py
# -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_GIS = PROJECT_ROOT / "data" / "staging" / "gis"
TARGET_EPSG = 2154
CORRIDOR_CODE = "PK520_PK535"
SCHEMA_NAME = "rail"
TABLE_NAME = "gis_asset"

# Load environment variables from railway-flood-twin/.env
load_dotenv(PROJECT_ROOT / ".env")

# -------------------------------------------------------------------
# CONFIGURATION
# Edit this list if you add more cleaned GIS files later.
# dataset_name must match the value already inserted in core.dataset.dataset_name
# -------------------------------------------------------------------
LAYER_CONFIG = [
    {
        "file_name": "voie_fixed.gpkg",
        "dataset_name": "voie_fixed",
        "asset_type": "track_area",
        "asset_subtype": None,
        "asset_name_field": None,
        "asset_code_field": None,
        "status_field": None,
    },
    {
        "file_name": "Buse_fixed.gpkg",
        "dataset_name": "Buse_fixed",
        "asset_type": "culvert",
        "asset_subtype": None,
        "asset_name_field": None,
        "asset_code_field": None,
        "status_field": None,
    },
    {
        "file_name": "Pont Rail_fixed.gpkg",
        "dataset_name": "Pont Rail_fixed",
        "asset_type": "bridge",
        "asset_subtype": None,
        "asset_name_field": None,
        "asset_code_field": None,
        "status_field": None,
    },
    {
        "file_name": "Descente d'eau_fixed.gpkg",
        "dataset_name": "Descente d'eau_fixed",
        "asset_type": "drainage_asset",
        "asset_subtype": None,
        "asset_name_field": None,
        "asset_code_field": None,
        "status_field": None,
    },
]


def require_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Create a .env file in the project root and add DATABASE_URL=..."
        )
    return db_url



def get_engine():
    db_url = require_database_url()
    normalized_url = normalize_database_url(db_url)
    return create_engine(normalized_url)



def get_corridor_id(engine, corridor_code: str) -> int:
    sql = text(
        """
        select corridor_id
        from rail.corridor
        where corridor_code = :corridor_code
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, {"corridor_code": corridor_code}).fetchone()
    if row is None:
        raise ValueError(
            f"No corridor found for corridor_code='{corridor_code}'. "
            "Insert the corridor row first."
        )
    return int(row[0])



def get_dataset_id(engine, dataset_name: str) -> int:
    sql = text(
        """
        select dataset_id
        from core.dataset
        where dataset_name = :dataset_name
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, {"dataset_name": dataset_name}).fetchone()
    if row is None:
        raise ValueError(
            f"No dataset found for dataset_name='{dataset_name}'. "
            "Insert the dataset metadata first into core.dataset."
        )
    return int(row[0])



def safe_extract_field(gdf: gpd.GeoDataFrame, field_name: str):
    if field_name is None:
        return pd.Series([None] * len(gdf), index=gdf.index)
    if field_name not in gdf.columns:
        print(f"[WARNING] Field '{field_name}' not found. Filling with NULL.")
        return pd.Series([None] * len(gdf), index=gdf.index)
    return gdf[field_name].astype(str)



def build_properties_json(gdf: gpd.GeoDataFrame) -> pd.Series:
    geom_col = gdf.geometry.name
    attr_cols = [c for c in gdf.columns if c != geom_col]

    def row_to_json(row):
        data = {}
        for col in attr_cols:
            value = row[col]
            if pd.isna(value):
                data[col] = None
            else:
                try:
                    json.dumps(value)
                    data[col] = value
                except TypeError:
                    data[col] = str(value)
        return json.dumps(data, ensure_ascii=False)

    return gdf.apply(row_to_json, axis=1)


def normalize_database_url(db_url: str) -> str:
    """Encode credentials in DATABASE_URL so special chars don't break parsing."""
    if "@" not in db_url or "://" not in db_url:
        return db_url

    scheme, remainder = db_url.split("://", 1)
    if "@" not in remainder:
        return db_url

    userinfo, host_and_path = remainder.rsplit("@", 1)
    if ":" not in userinfo:
        encoded_user = quote(unquote(userinfo), safe="")
        return f"{scheme}://{encoded_user}@{host_and_path}"

    username, password = userinfo.split(":", 1)
    encoded_user = quote(unquote(username), safe="")
    encoded_password = quote(unquote(password), safe="")
    return f"{scheme}://{encoded_user}:{encoded_password}@{host_and_path}"


def prepare_layer(
    file_path: Path,
    config: dict,
    corridor_id: int,
    source_dataset_id: int,
) -> gpd.GeoDataFrame:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    print(f"\n[INFO] Reading: {file_path.name}")
    gdf = gpd.read_file(file_path)

    if gdf.empty:
        raise ValueError(f"Layer is empty: {file_path.name}")

    print(f"[INFO] Features: {len(gdf)}")
    print(f"[INFO] Original CRS: {gdf.crs}")
    print(f"[INFO] Geometry types: {sorted(set(gdf.geom_type.astype(str)))}")

    if gdf.crs is None:
        raise ValueError(
            f"Layer '{file_path.name}' has no CRS. "
            "Use the cleaned exported file with CRS written to disk."
        )

    if gdf.crs.to_epsg() != TARGET_EPSG:
        print(f"[INFO] Reprojecting to EPSG:{TARGET_EPSG}")
        gdf = gdf.to_crs(TARGET_EPSG)

    gdf = gdf[~gdf.geometry.isna()].copy()
    if len(gdf) == 0:
        raise ValueError(f"All geometries are NULL after cleanup for: {file_path.name}")

    invalid_count = int((~gdf.geometry.is_valid).sum())
    if invalid_count > 0:
        print(f"[INFO] Repairing {invalid_count} invalid geometries with buffer(0)")
        gdf["geometry"] = gdf.geometry.buffer(0)

    gdf["corridor_id"] = corridor_id
    gdf["asset_type"] = config["asset_type"]
    gdf["asset_subtype"] = config.get("asset_subtype")
    gdf["asset_name"] = safe_extract_field(gdf, config.get("asset_name_field"))
    gdf["asset_code"] = safe_extract_field(gdf, config.get("asset_code_field"))
    gdf["status"] = safe_extract_field(gdf, config.get("status_field"))
    gdf["source_dataset_id"] = source_dataset_id
    gdf["properties"] = build_properties_json(gdf)

    gdf = gdf[
        [
            "corridor_id",
            "asset_type",
            "asset_subtype",
            "asset_name",
            "asset_code",
            "status",
            "source_dataset_id",
            "properties",
            gdf.geometry.name,
        ]
    ].copy()

    geom_col = gdf.geometry.name
    if geom_col != "geom":
        gdf = gdf.rename(columns={geom_col: "geom"})
        gdf = gdf.set_geometry("geom")

    print(f"[INFO] Prepared {len(gdf)} records for loading")
    return gdf



def load_layer(engine, prepared_gdf: gpd.GeoDataFrame):
    prepared_gdf.to_postgis(
        name=TABLE_NAME,
        schema=SCHEMA_NAME,
        con=engine,
        if_exists="append",
        index=False,
    )



def main():
    try:
        engine = get_engine()
        corridor_id = get_corridor_id(engine, CORRIDOR_CODE)
        print(f"[INFO] corridor_id for {CORRIDOR_CODE}: {corridor_id}")

        for config in LAYER_CONFIG:
            dataset_name = config["dataset_name"]
            source_dataset_id = get_dataset_id(engine, dataset_name)
            file_path = STAGING_GIS / config["file_name"]

            print("-" * 70)
            print(f"[INFO] dataset_name: {dataset_name}")
            print(f"[INFO] source_dataset_id: {source_dataset_id}")
            print(f"[INFO] target asset_type: {config['asset_type']}")

            prepared_gdf = prepare_layer(
                file_path=file_path,
                config=config,
                corridor_id=corridor_id,
                source_dataset_id=source_dataset_id,
            )
            load_layer(engine, prepared_gdf)
            print(f"[SUCCESS] Loaded: {config['file_name']}")

        print("\nAll configured GIS layers loaded successfully into rail.gis_asset.")

    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
