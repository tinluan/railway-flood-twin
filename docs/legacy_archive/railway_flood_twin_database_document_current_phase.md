# Railway Flood-Risk Digital Twin — Database Document

## Version
Current implementation status document (Phase 1)

## Current status
The database has been initialized in Supabase/PostGIS.

### Confirmed completed steps
- PostGIS enabled in Supabase
- Minimal schemas created:
  - `core`
  - `rail`
- Minimal tables created:
  - `core.dataset`
  - `rail.corridor`
  - `rail.gis_asset`
- One corridor row inserted:
  - `corridor_code = PK520_PK535`
  - `corridor_name = Rail corridor PK520 to PK535`
- Source datasets registered in `core.dataset`:
  - `voie_fixed`
  - `Buse_fixed`
  - `Pont Rail_fixed`
  - `Descente d'eau_fixed`
  - `DTM PK520_PK535_NO_HOLES`

## Why the current schema is minimal
At this stage, the currently inspected `voie` layer is polygon-based, not line-based.
Therefore, the implementation is starting with:
- dataset metadata
- corridor metadata
- generic GIS asset storage

The `rail.track_segment` table is postponed until a true line / centerline layer is available or derived.

---

## Current database structure

### Schema: `core`

#### Table: `core.dataset`
Stores metadata for each source dataset.

**Fields**
- `dataset_id` — primary key
- `dataset_name` — source dataset name
- `dataset_type` — `rail_gis`, `terrain`, etc.
- `source_uri` — path or source location
- `source_format` — `gpkg`, `asc`, etc.
- `source_crs` — original CRS
- `target_srid` — target SRID in database
- `version_tag` — optional version
- `ingested_at` — timestamp
- `notes` — extra notes

---

### Schema: `rail`

#### Table: `rail.corridor`
Stores corridor-level metadata.

**Fields**
- `corridor_id` — primary key
- `corridor_code` — unique corridor code
- `corridor_name` — corridor name
- `description` — corridor description

#### Current inserted row
- `corridor_id = 1`
- `corridor_code = PK520_PK535`
- `corridor_name = Rail corridor PK520 to PK535`
- `description = Initial corridor for the railway flood-risk digital twin MVP`

---

#### Table: `rail.gis_asset`
Stores generic GIS assets as geometry features.

**Purpose in current phase**
This table is the main storage table for the cleaned GIS layers currently available.

**Fields**
- `gis_asset_id` — primary key
- `corridor_id` — foreign key to `rail.corridor`
- `asset_type` — e.g. `track_area`, `culvert`, `bridge`, `drainage_asset`
- `asset_subtype` — optional subtype
- `asset_name` — optional asset name
- `asset_code` — optional source/project code
- `status` — optional lifecycle/operational status
- `source_dataset_id` — foreign key to `core.dataset`
- `properties` — JSON attributes from source data
- `geom` — PostGIS geometry column (`geometry(Geometry, 2154)`)

**Indexes**
- GiST index on `geom`
- B-tree index on `corridor_id`
- B-tree index on `source_dataset_id`

---

## Current interpretation of source layers

### Loaded / registered source datasets
| Dataset name | Type | Current interpretation |
|---|---|---|
| `voie_fixed` | rail_gis | track area polygon |
| `Buse_fixed` | rail_gis | culvert-related asset |
| `Pont Rail_fixed` | rail_gis | bridge asset |
| `Descente d'eau_fixed` | rail_gis | drainage asset |
| `DTM PK520_PK535_NO_HOLES` | terrain | terrain raster source |

### Important implementation note
Because `voie_fixed` is polygon-based, it should currently be loaded into `rail.gis_asset` with:
- `asset_type = 'track_area'`

It should **not** be loaded into `rail.track_segment` yet.

---

## Recommended next implementation step

### Step 3 — Load cleaned GIS layers into `rail.gis_asset`
Start with:
1. `voie_fixed.gpkg`
2. `Buse_fixed.gpkg`
3. `Pont Rail_fixed.gpkg`
4. `Descente d'eau_fixed.gpkg`

### Suggested `asset_type` values
- `voie_fixed` → `track_area`
- `Buse_fixed` → `culvert`
- `Pont Rail_fixed` → `bridge`
- `Descente d'eau_fixed` → `drainage_asset`

---

## Should `task_tracker.md` be updated after every step?

### Recommended practice
Yes — but not after every tiny click.

Update `task_tracker.md` after each **meaningful milestone**, for example:
- after fixing CRS and exporting cleaned files
- after generating the documents successfully
- after creating the database tables
- after inserting corridor and dataset metadata
- after loading the first GIS layer
- after validating the first loaded records

### Good rule
Update the tracker whenever a step changes the project state in a useful way.

### Example tasks that can now be marked as done
- Review architecture document
- Inspect CRS of DTM
- Create minimal schemas in Supabase
- Create `core.dataset` table
- Create `rail.corridor` table
- Create `rail.gis_asset` table
- Register visible datasets in `core.dataset`

Tasks that should remain pending:
- Load `voie` into `rail.gis_asset`
- Load `Buse` into `rail.gis_asset`
- Load `Pont Rail` into `rail.gis_asset`
- Run validation checks on loaded GIS assets
- Derive elevation summaries from DTM

---

## Suggested next database extension (later)
Once a line-based rail centerline is available, add:
- `rail.track_segment`

Once rainfall becomes available, add:
- `env.rain_station`
- `env.rainfall_observation`

Once BIM becomes available, add:
- `bim.ifc_model`
- `bim.bim_asset`
- `bim.asset_gis_link`

---

## Summary
It now has a valid Phase-1 database foundation:
- metadata table
- corridor table
- generic GIS asset table
- confirmed CRS strategy (`EPSG:2154`)
- cleaned GIS files in `data/staging/gis/`

The next practical step is to load the first cleaned GIS layers into `rail.gis_asset`.
