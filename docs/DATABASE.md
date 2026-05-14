# Railway Flood-Risk Digital Twin — Database Technical Reference

<!-- AI_READABLE: YES — Read this file to understand the full database architecture before writing any DB-related code. -->

**Project**: SNCF Ligne_400 (PK520–PK535) Flood Risk Demonstrator
**Database**: Supabase (PostgreSQL 15 + PostGIS 3)
**Version**: Phase 1 — GIS Asset Foundation
**Last Updated**: 2026-05-14
**Maintained by**: Tin Luan

---

## Contents

1. [System Overview](#1-system-overview)
2. [Connection & Configuration](#2-connection--configuration)
3. [CRS Strategy](#3-crs-strategy)
4. [Schema Architecture](#4-schema-architecture)
5. [Table Specifications](#5-table-specifications)
6. [Indexes](#6-indexes)
7. [Seed Data](#7-seed-data)
8. [Ingestion Pipeline](#8-ingestion-pipeline)
9. [Validation Results (Phase 1)](#9-validation-results-phase-1)
10. [Future Schema Roadmap](#10-future-schema-roadmap)
11. [SQL Script Index](#11-sql-script-index)
12. [Rules & Constraints](#12-rules--constraints)

---

## 1. System Overview

The database is the **Mirror Database** — the central hub of the 4-layer digital twin architecture that merges GIS, BIM, and meteorological data before feeding the risk engine.

```
Layer 1: Data Sources  →  BIM (IFC/Civil3D), GIS (DTM/LiDAR), Météo-France
Layer 2: Bridge        →  Mirror Database (this document) + Python pre-processor
Layer 3: Simulation    →  HEC-RAS 2D + SWI Calculator (reads from DB)
Layer 4: Alert         →  Dashboard + FastAPI (reads from DB)
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Host | Supabase (managed PostgreSQL) |
| Engine | PostgreSQL 15 |
| Spatial extension | PostGIS 3 (enabled) |
| Client driver | `psycopg2` / `SQLAlchemy` |
| Python ORM | `GeoAlchemy2` + `GeoPandas.to_postgis()` |
| Connection config | `.env` → `DATABASE_URL` |

### Phase 1 Scope

Phase 1 establishes the minimal, stable foundation:
- Dataset metadata registry (`core.dataset`)
- Corridor reference table (`rail.corridor`)
- Generic GIS asset storage (`rail.gis_asset`)
- **30 GIS asset records** loaded across 4 asset types
- All geometry in **EPSG:2154** — verified and validated

---

## 2. Connection & Configuration

### Environment Variable

All database connections use the `DATABASE_URL` from `.env`:

```ini
# .env (project root — DO NOT commit this file)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

Copy `.env.example` to `.env` and fill in the Supabase credentials (ask Tin).

### Python Connection Pattern

```python
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
```

> **Special characters in passwords**: The loader script (`src/ingestion/load_gis_assets_dotenv.py`) automatically URL-encodes credentials via `normalize_database_url()`. Passwords with `@`, `)`, `(` etc. are handled safely.

### Running the Health Check

```powershell
$env:PYTHONPATH = "."
.\.conda\python.exe src/utils/check_health.py
```

---

## 3. CRS Strategy

### Rule: Single Internal CRS

| Context | CRS | Unit | Reason |
|---------|-----|------|--------|
| All database geometry | **EPSG:2154** (Lambert 93) | metres | French national standard, metre-accurate |
| Dashboard / PyDeck display | **EPSG:4326** (WGS84) | decimal degrees | Required by web map APIs |

**Conversion rule**: Convert `2154 → 4326` only at the final display step in `src/dashboard/app_main.py`. Never store WGS84 in the database.

### Source Layer CRS Audit (Phase 1)

All cleaned GIS layers in `data/staging/gis/` were confirmed as Lambert-93 compatible (GRS80 ellipsoid, Lambert Conformal Conic 2SP matching EPSG:2154 parameters). No reprojection was needed for these layers.

| File | Source CRS | Status |
|------|-----------|--------|
| `voie_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Buse_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Pont Rail_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Descente d'eau_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Dalot_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Talus Terre_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Fossé terre_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Fossé terre revêtu_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `Drainage_longitudinal_à_ciel_ouvert_fixed.gpkg` | Lambert 93 (GRS80) | ✅ OK |
| `PK520_PK535_NO_HOLES.asc` (DTM) | EPSG:2154 | ⚠️ Verify SRID in raster header |

### Vertical Datum (Z)

| Source | Raw Z Range | Offset | Notes |
|--------|------------|--------|-------|
| 2D Shapefiles (`maquette_2d/`) | ~95–185 m | **+107.0166 m** | CAD origin vs NGF-IGN69 |
| 3D MULTIPATCH (`maquette_3d/`) | ~175–290 m | None (pending) | Task 6: verify vs DTM |
| DTM raster (`dtm_fixed.tif`) | ~200–250 m | Reference | EPSG:2154 + NGF-IGN69 |

> **CRITICAL**: Never apply the +107 m offset to 3D BIM assets. Datum comparison (Task 6) required first.

---

## 4. Schema Architecture

```
PostgreSQL (Supabase)
├── core                    ← Dataset metadata registry
│   └── dataset             ← Source file provenance tracking
│
├── rail                    ← Railway infrastructure
│   ├── corridor            ← Study corridor definitions
│   ├── gis_asset           ← ✅ Active: 30 records loaded (Phase 1)
│   └── track_segment       ← 🔲 Planned: awaiting line-based centerline
│
├── env                     ← Environmental data (Phase 2)
│   ├── rain_station        ← 🔲 Planned
│   └── rainfall_observation ← 🔲 Planned
│
└── bim                     ← BIM-derived assets (Phase 3)
    ├── ifc_model           ← 🔲 Planned
    ├── bim_asset           ← 🔲 Planned
    └── asset_gis_link      ← 🔲 Planned
```

---

## 5. Table Specifications

### 5.1 `core.dataset`

Tracks the provenance of every source file loaded into the database.

```sql
CREATE TABLE core.dataset (
    dataset_id    BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    dataset_name  TEXT NOT NULL,
    dataset_type  TEXT NOT NULL,      -- 'rail_gis' | 'terrain' | 'rainfall' | 'bim'
    source_uri    TEXT,               -- relative path, e.g. data/staging/gis/Buse_fixed.gpkg
    source_format TEXT,               -- 'gpkg' | 'asc' | 'ifc' | 'csv'
    source_crs    TEXT,               -- original CRS string
    target_srid   INTEGER NOT NULL,   -- always 2154
    version_tag   TEXT,
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes         TEXT
);
```

**Data Dictionary**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `dataset_id` | bigint | NO | Auto-generated primary key |
| `dataset_name` | text | NO | Unique human-readable name matching the source file base name |
| `dataset_type` | text | NO | High-level category: `rail_gis`, `terrain`, `rainfall`, `bim` |
| `source_uri` | text | YES | Relative path from project root to source file |
| `source_format` | text | YES | File format: `gpkg`, `asc`, `csv`, `ifc` |
| `source_crs` | text | YES | Original CRS of the source (before any reprojection) |
| `target_srid` | integer | NO | Target database SRID — always `2154` |
| `version_tag` | text | YES | Optional version label (e.g. `v1`, `2026-05`) |
| `ingested_at` | timestamptz | NO | Auto-set to `now()` on insert |
| `notes` | text | YES | Free-text notes about the dataset |

---

### 5.2 `rail.corridor`

One row per study corridor. Currently contains one corridor: `PK520_PK535`.

```sql
CREATE TABLE rail.corridor (
    corridor_id   BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    corridor_code TEXT NOT NULL UNIQUE,   -- e.g. 'PK520_PK535'
    corridor_name TEXT NOT NULL,
    description   TEXT
);
```

**Data Dictionary**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `corridor_id` | bigint | NO | Auto-generated primary key |
| `corridor_code` | text | NO | Short unique code used in Python config (`CORRIDOR_CODE`) |
| `corridor_name` | text | NO | Human-readable full name |
| `description` | text | YES | Context or scope description |

**Current data**

| corridor_id | corridor_code | corridor_name | description |
|-------------|--------------|---------------|-------------|
| 1 | `PK520_PK535` | Rail corridor PK520 to PK535 | Initial corridor for the railway flood-risk digital twin MVP |

---

### 5.3 `rail.gis_asset`

The primary spatial table for Phase 1. Stores all railway infrastructure GIS features as generic geometry records with provenance links back to `core.dataset` and `rail.corridor`.

```sql
CREATE TABLE rail.gis_asset (
    gis_asset_id      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    corridor_id       BIGINT NOT NULL REFERENCES rail.corridor(corridor_id) ON DELETE CASCADE,
    asset_type        TEXT NOT NULL,       -- 'track_area' | 'culvert' | 'bridge' | 'drainage_asset'
    asset_subtype     TEXT,
    asset_name        TEXT,
    asset_code        TEXT,
    status            TEXT,
    source_dataset_id BIGINT REFERENCES core.dataset(dataset_id) ON DELETE SET NULL,
    properties        JSONB,              -- all original source attributes
    geom              GEOMETRY(Geometry, 2154) NOT NULL
);
```

**Data Dictionary**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `gis_asset_id` | bigint | NO | Auto-generated primary key |
| `corridor_id` | bigint | NO | FK → `rail.corridor`. Cascades on delete. |
| `asset_type` | text | NO | Main classification — see Asset Type Vocabulary below |
| `asset_subtype` | text | YES | Optional finer classification |
| `asset_name` | text | YES | Human-readable name if available in source data |
| `asset_code` | text | YES | Source or project code |
| `status` | text | YES | Operational/lifecycle status if known |
| `source_dataset_id` | bigint | YES | FK → `core.dataset`. Set NULL if dataset is deleted. |
| `properties` | jsonb | YES | All original attributes from the source GeoPackage layer |
| `geom` | geometry | NO | PostGIS geometry — any type, SRID 2154 |

**Asset Type Vocabulary (Phase 1)**

| `asset_type` value | Source Layer | Description |
|--------------------|-------------|-------------|
| `track_area` | `voie_fixed.gpkg` | Railway track polygon (polygon-based, not yet a centerline) |
| `culvert` | `Buse_fixed.gpkg` | Culvert / drainage pipe under embankment |
| `bridge` | `Pont Rail_fixed.gpkg` | Rail bridge structure |
| `drainage_asset` | `Descente d'eau_fixed.gpkg` | Surface water drainage element |

**Planned additional asset types (Phase 2+)**

| `asset_type` value | Future Source |
|--------------------|--------------|
| `open_drain` | `Fossé terre_fixed.gpkg` |
| `lined_drain` | `Fossé terre revêtu_fixed.gpkg` |
| `slope` | `Talus Terre_fixed.gpkg` |
| `longitudinal_drain` | `Drainage_longitudinal_à_ciel_ouvert_fixed.gpkg` |

---

### 5.4 `rail.track_segment` *(Planned — Phase 2)*

Will store 100-metre rail centerline segments with terrain-derived elevation attributes. Blocked until a true line-geometry centerline layer is available or derived from `voie_fixed`.

```sql
-- Planned schema (do not create yet)
CREATE TABLE rail.track_segment (
    track_segment_id  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    corridor_id       BIGINT NOT NULL REFERENCES rail.corridor(corridor_id),
    segment_code      TEXT NOT NULL UNIQUE,  -- e.g. 'SEG_0001'
    line_name         TEXT,
    track_name        TEXT,
    start_chainage_m  FLOAT,
    end_chainage_m    FLOAT,
    length_m          FLOAT,
    elevation_min_m   FLOAT,   -- sampled from DTM
    elevation_max_m   FLOAT,   -- sampled from DTM
    geom              GEOMETRY(LineString, 2154) NOT NULL
);
```

---

## 6. Indexes

All indexes are created in `sql/phase1_current/supabase_1_GIS Dataset and Rail Corridor Schema.sql`.

| Index Name | Table | Column | Type | Purpose |
|-----------|-------|--------|------|---------|
| `gis_asset_geom_gix` | `rail.gis_asset` | `geom` | GiST | Spatial queries, intersection, bbox |
| `gis_asset_corridor_idx` | `rail.gis_asset` | `corridor_id` | B-tree | Filter by corridor |
| `gis_asset_source_dataset_idx` | `rail.gis_asset` | `source_dataset_id` | B-tree | Join back to dataset metadata |

```sql
CREATE INDEX IF NOT EXISTS gis_asset_geom_gix
    ON rail.gis_asset USING GIST (geom);

CREATE INDEX IF NOT EXISTS gis_asset_corridor_idx
    ON rail.gis_asset (corridor_id);

CREATE INDEX IF NOT EXISTS gis_asset_source_dataset_idx
    ON rail.gis_asset (source_dataset_id);
```

---

## 7. Seed Data

SQL scripts in `sql/phase1_current/` must be run in numbered order:

### Script 1 — Create Schemas & Tables
`sql/phase1_current/supabase_1_GIS Dataset and Rail Corridor Schema.sql`

Creates: `core` schema, `rail` schema, `core.dataset`, `rail.corridor`, `rail.gis_asset`, and all indexes.

### Script 2 — Seed Corridor
`sql/phase1_current/Supabase_2_Seed rail corridor reference data.sql`

```sql
INSERT INTO rail.corridor (corridor_code, corridor_name, description)
VALUES (
    'PK520_PK535',
    'Rail corridor PK520 to PK535',
    'Initial corridor for the railway flood-risk digital twin MVP'
)
ON CONFLICT (corridor_code) DO NOTHING;
```

### Script 3 — Register Source Datasets
`sql/phase1_current/supabase_3_Seed core.datasets With GIS and Terrain Sources.sql`

Registers 5 datasets in `core.dataset`:

| `dataset_id` | `dataset_name` | `dataset_type` | `source_format` |
|---|---|---|---|
| 1 | `voie_fixed` | `rail_gis` | `gpkg` |
| 2 | `Buse_fixed` | `rail_gis` | `gpkg` |
| 3 | `Pont Rail_fixed` | `rail_gis` | `gpkg` |
| 4 | `Descente d'eau_fixed` | `rail_gis` | `gpkg` |
| 5 | `DTM PK520_PK535_NO_HOLES` | `terrain` | `asc` |

### Script 4 — Load GIS Assets (Python)

Run the reusable Python ingestion script (not SQL — see Section 8):

```powershell
$env:PYTHONPATH = "."
.\.conda\python.exe src/ingestion/load_gis_assets_dotenv.py
```

---

## 8. Ingestion Pipeline

**Script**: `src/ingestion/load_gis_assets_dotenv.py`

This is the authoritative, reusable GIS loader. It must be used for all future GIS layer loads.

### Pipeline Steps (per layer)

```
[1] Read LAYER_CONFIG list
[2] Resolve corridor_id from rail.corridor WHERE corridor_code = 'PK520_PK535'
[3] For each layer config:
    [3a] Resolve source_dataset_id from core.dataset WHERE dataset_name = config.dataset_name
    [3b] Read GeoPackage with GeoPandas
    [3c] Validate CRS → reproject to EPSG:2154 if needed
    [3d] Drop NULL geometries
    [3e] Repair invalid geometries (buffer(0))
    [3f] Attach corridor_id, asset_type, source_dataset_id, properties JSON
    [3g] Rename geometry column to 'geom'
    [3h] Append to rail.gis_asset via GeoDataFrame.to_postgis()
```

### LAYER_CONFIG (current)

```python
LAYER_CONFIG = [
    {"file_name": "voie_fixed.gpkg",         "dataset_name": "voie_fixed",          "asset_type": "track_area"},
    {"file_name": "Buse_fixed.gpkg",          "dataset_name": "Buse_fixed",           "asset_type": "culvert"},
    {"file_name": "Pont Rail_fixed.gpkg",     "dataset_name": "Pont Rail_fixed",      "asset_type": "bridge"},
    {"file_name": "Descente d'eau_fixed.gpkg","dataset_name": "Descente d'eau_fixed", "asset_type": "drainage_asset"},
]
```

### Adding a New Layer

1. Export the cleaned GeoPackage to `data/staging/gis/`
2. Register it in `core.dataset` (via Script 3 pattern)
3. Add an entry to `LAYER_CONFIG` in the loader script
4. Run the loader: `.\.conda\python.exe src/ingestion/load_gis_assets_dotenv.py`
5. Run validation queries (Section 9) to confirm

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `if_exists="append"` in `to_postgis()` | Allows incremental loading without wiping existing records |
| `properties JSONB` column | Preserves all original source attributes without schema changes |
| `ON DELETE SET NULL` for `source_dataset_id` | Dataset metadata can be updated/deleted without orphaning asset records |
| `ON DELETE CASCADE` for `corridor_id` | Deleting a corridor removes all its assets cleanly |
| URL-encoding password in `normalize_database_url()` | Handles special characters in Supabase passwords |

---

## 9. Validation Results (Phase 1)

Run these queries in Supabase SQL Editor after any load to verify integrity.

### V1 — Total Asset Count

```sql
SELECT COUNT(*) AS total_assets FROM rail.gis_asset;
```

**Phase 1 result: `30`**

### V2 — Count by Asset Type

```sql
SELECT asset_type, COUNT(*) AS asset_count
FROM rail.gis_asset
GROUP BY asset_type
ORDER BY asset_type;
```

**Phase 1 result:**

| asset_type | asset_count |
|-----------|------------|
| `bridge` | 8 |
| `culvert` | 14 |
| `drainage_asset` | 6 |
| `track_area` | 2 |

### V3 — SRID Consistency

```sql
SELECT DISTINCT ST_SRID(geom) AS srid FROM rail.gis_asset;
```

**Phase 1 result: `2154`** ✅ — All geometries use EPSG:2154.

### V4 — Invalid Geometry Check

```sql
SELECT COUNT(*) AS invalid_geometries
FROM rail.gis_asset
WHERE NOT ST_IsValid(geom);
```

**Phase 1 result: `0`** ✅

### V5 — Null Geometry Check

```sql
SELECT COUNT(*) AS null_geometries
FROM rail.gis_asset
WHERE geom IS NULL;
```

**Phase 1 result: `0`** ✅

### V6 — Count by Source Dataset (with names)

```sql
SELECT d.dataset_name, COUNT(*) AS asset_count
FROM rail.gis_asset ga
LEFT JOIN core.dataset d ON ga.source_dataset_id = d.dataset_id
GROUP BY d.dataset_name
ORDER BY d.dataset_name;
```

**Phase 1 result:**

| dataset_name | asset_count |
|---|---|
| `Buse_fixed` | 14 |
| `Descente d'eau_fixed` | 6 |
| `Pont Rail_fixed` | 8 |
| `voie_fixed` | 2 |

### V7 — Corridor Assignment Check

```sql
SELECT corridor_id, COUNT(*) AS asset_count
FROM rail.gis_asset
GROUP BY corridor_id;
```

**Phase 1 result: `corridor_id=1`, `asset_count=30`** ✅ — All assets linked to PK520_PK535.

### V8 — Foreign Key Integrity

```sql
-- Assets with valid corridor links
SELECT COUNT(*) FROM rail.gis_asset ga
JOIN rail.corridor c ON ga.corridor_id = c.corridor_id;

-- Assets with valid dataset links
SELECT COUNT(*) FROM rail.gis_asset ga
JOIN core.dataset d ON ga.source_dataset_id = d.dataset_id;
```

Both should return `30` for Phase 1.

---

## 10. Future Schema Roadmap

### Phase 2 — Rail Track Segments

**Trigger**: A true line-geometry centerline is available or derived from `voie_fixed` polygon centreline extraction.

```sql
-- Create when ready
CREATE TABLE rail.track_segment (
    track_segment_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    corridor_id      BIGINT NOT NULL REFERENCES rail.corridor(corridor_id),
    segment_code     TEXT NOT NULL UNIQUE,
    start_chainage_m FLOAT,
    end_chainage_m   FLOAT,
    length_m         FLOAT,
    elevation_min_m  FLOAT,    -- from DTM sampling
    elevation_max_m  FLOAT,    -- from DTM sampling
    z_ballast_m      FLOAT,    -- from BIM/IFC
    slope_pct        FLOAT,
    soil_type        TEXT,
    land_cover       TEXT,
    is_hotspot       BOOLEAN DEFAULT FALSE,
    geom             GEOMETRY(LineString, 2154) NOT NULL
);
```

This table implements the **Mirror Database Contract** (see `docs/legacy_archive/handoff_schema.md`) — the mandatory columns required by the risk engine.

### Phase 2 — Environmental / Rainfall

**Trigger**: Live Météo-France API key available.

```sql
CREATE SCHEMA env;

CREATE TABLE env.rain_station (
    station_id   BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    station_code TEXT NOT NULL UNIQUE,
    station_name TEXT,
    geom         GEOMETRY(Point, 2154)
);

CREATE TABLE env.rainfall_observation (
    obs_id        BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    station_id    BIGINT NOT NULL REFERENCES env.rain_station(station_id),
    observed_at   TIMESTAMPTZ NOT NULL,
    rainfall_mm   FLOAT NOT NULL,        -- cumulative mm in observation window
    window_min    INTEGER DEFAULT 60     -- observation window in minutes
);
```

### Phase 3 — BIM Integration

**Trigger**: IFC files from SNCF BIM environment are available.

```sql
CREATE SCHEMA bim;

CREATE TABLE bim.ifc_model (
    ifc_model_id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    model_name   TEXT NOT NULL,
    source_uri   TEXT,
    ifc_schema   TEXT,    -- 'IFC2x3' | 'IFC4'
    imported_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bim.bim_asset (
    bim_asset_id  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ifc_model_id  BIGINT REFERENCES bim.ifc_model(ifc_model_id),
    global_id     TEXT,   -- IFC GlobalId
    ifc_type      TEXT,   -- IfcRailing, IfcSlab, etc.
    asset_name    TEXT,
    z_ballast_m   FLOAT,  -- Top of ballast from IFC geometry
    properties    JSONB
);

CREATE TABLE bim.asset_gis_link (
    link_id      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    bim_asset_id BIGINT REFERENCES bim.bim_asset(bim_asset_id),
    gis_asset_id BIGINT REFERENCES rail.gis_asset(gis_asset_id),
    match_method TEXT,    -- 'spatial_centroid' | 'manual' | 'code_match'
    confidence   FLOAT    -- 0.0–1.0
);
```

---

## 11. SQL Script Index

All scripts are in `sql/phase1_current/`. Run in this exact order for a clean install.

| Order | File | Action |
|-------|------|--------|
| 1 | `supabase_1_GIS Dataset and Rail Corridor Schema.sql` | Create schemas, tables, indexes |
| 2 | `Supabase_2_Seed rail corridor reference data.sql` | Insert PK520_PK535 corridor |
| 3 | `supabase_3_Seed core.datasets With GIS and Terrain Sources.sql` | Register 5 source datasets |
| 4 | *(Python)* `src/ingestion/load_gis_assets_dotenv.py` | Load 30 GIS assets into `rail.gis_asset` |
| 5 | `sql_validation_results_phase_1.sql` | Validation queries + documented results |

---

## 12. Rules & Constraints

These rules apply to all database work in this project:

| Rule | Detail |
|------|--------|
| **EPSG:2154 everywhere** | All geometry stored in Lambert 93. Convert to 4326 only at display time. |
| **ASCII-only keys** | Asset names in code and JSON must not contain French accents (`é`, `ê`, etc.). Filenames on disk may keep accents. |
| **No hardcoded paths** | Use `src/utils/paths.py` (`ProjectPaths`) or `src/paths.py` (dashboard legacy). Never write `C:/Users/...` in code. |
| **`core.dataset` first** | Always register a source dataset in `core.dataset` before loading geometry. The `source_dataset_id` FK enforces provenance. |
| **`rail.corridor` first** | The `corridor_id` FK in `rail.gis_asset` requires the corridor to exist. Run Script 2 before Script 4. |
| **`if_exists="append"` only** | Never use `if_exists="replace"` — it would drop the table and lose all data. |
| **Validate after every load** | Run V1–V8 queries (Section 9) after each new layer is loaded. |
| **No direct push to `main`** | All schema changes go through a feature branch and are reviewed before merge. |
| **Update STATUS.md** | After completing any DB milestone, check off the task in `STATUS.md`. |

---

*For the engineering model and risk formulas, see `ARCHITECTURE.md`.*
*For sprint tasks and current project status, see `STATUS.md`.*
*For the ingestion script source, see `src/ingestion/load_gis_assets_dotenv.py`.*
