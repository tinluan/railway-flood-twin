# GIS Asset Loading Validation — SQL Queries, Results, Notes, and Instructions

## Purpose
This document records the SQL validation queries used after loading the first cleaned GIS layers into `rail.gis_asset`, together with the observed results, interpretation notes, and next-step instructions.

## Context
The first cleaned GIS layers were loaded into the database using the reusable Python loader.

### Current loaded layer interpretation
- `voie_fixed.gpkg` → `asset_type = 'track_area'`
- `Buse_fixed.gpkg` → `asset_type = 'culvert'`
- `Pont Rail_fixed.gpkg` → `asset_type = 'bridge'`
- `Descente d'eau_fixed.gpkg` → `asset_type = 'drainage_asset'`

At this stage, the validation target is the table:

```sql
rail.gis_asset
```

---

## Validation Query 1 — Total number of loaded GIS assets

### SQL
```sql
select count(*) as total_assets
from rail.gis_asset;
```

### Observed result
```text
total_assets = 30
```

### Interpretation
A total of **30 GIS asset records** are currently stored in `rail.gis_asset`.

### What this tells us
- the first database loading process inserted rows successfully
- the table is no longer empty
- the loader worked across multiple cleaned source files

---

## Validation Query 2 — Count by `asset_type`

### SQL
```sql
select asset_type, count(*) as asset_count
from rail.gis_asset
group by asset_type
order by asset_type;
```

### Observed result
```text
bridge          8
culvert         14
drainage_asset  6
track_area      2
```

### Interpretation
The current data distribution by asset type is:

- **bridge** = 8
- **culvert** = 14
- **drainage_asset** = 6
- **track_area** = 2

### What this tells us
- multiple asset categories were loaded correctly
- `culvert` is currently the largest class
- `track_area` currently contains 2 polygon records
- the configured mapping in the Python loader is functioning as expected

### Recommended note
Keep this result in the project log because it is a useful milestone summary for the first GIS ingestion phase.

---

## Validation Query 3 — SRID consistency

### SQL
```sql
select distinct ST_SRID(geom) as srid
from rail.gis_asset;
```

### Observed result
```text
srid = 2154
```

### Interpretation
All loaded GIS assets currently use:

```text
EPSG:2154
```

### What this tells us
- the geometry column is spatially consistent
- the cleaned files were loaded with the expected project CRS
- the current GIS asset table is aligned with the DTM target CRS strategy

### Why this is important
Using one consistent SRID is essential for:
- spatial joins
- overlay with terrain
- later asset-to-segment or asset-to-BIM linking
- reliable map display

---

## Validation Query 4 — Preview loaded rows

### SQL
```sql
select
    gis_asset_id,
    corridor_id,
    asset_type,
    source_dataset_id
from rail.gis_asset
order by gis_asset_id;
```

### Observed pattern from preview
The preview shows that:

- all visible rows use `corridor_id = 1`
- `track_area` rows use `source_dataset_id = 1`
- `culvert` rows use `source_dataset_id = 2`
- `bridge` rows use `source_dataset_id = 3`
- `drainage_asset` rows use `source_dataset_id = 4`

### Interpretation
This confirms that:
- the loader correctly linked inserted records to the correct corridor
- the loader correctly linked inserted records to the correct source dataset metadata

### Why this matters
This proves that:
- `core.dataset` and `rail.corridor` were integrated properly into the loading process
- provenance tracking is working

---

## Validation Query 5 — Invalid geometry check

### SQL
```sql
select count(*) as invalid_geometries
from rail.gis_asset
where not ST_IsValid(geom);
```

### Observed result
```text
invalid_geometries = 0
```

### Interpretation
No invalid geometries are currently present in `rail.gis_asset`.

### What this tells us
- geometry repair / cleaning was sufficient for the first load
- the current GIS assets are valid for further spatial work

### Why this is important
Invalid geometries often break:
- intersections
- distance operations
- overlays
- export and visualization workflows

A result of **0** is very good.

---

## Validation Query 6 — Null geometry check

### SQL
```sql
select count(*) as null_geometries
from rail.gis_asset
where geom is null;
```

### Observed result
```text
null_geometries = 0
```

### Interpretation
No records in `rail.gis_asset` currently have a missing geometry.

### What this tells us
- all inserted GIS asset records are spatially usable
- the first ingestion pass did not create empty spatial rows

---

## Validation Query 7 — Count by source dataset

### SQL
```sql
select
    d.dataset_name,
    count(*) as asset_count
from rail.gis_asset ga
left join core.dataset d
  on ga.source_dataset_id = d.dataset_id
group by d.dataset_name
order by d.dataset_name;
```

### Observed result
```text
Buse_fixed               14
Descente d'eau_fixed      6
Pont Rail_fixed           8
voie_fixed                2
```

### Interpretation
The count by source dataset confirms that the inserted rows match the loaded cleaned files:

- `Buse_fixed` → 14 records
- `Descente d'eau_fixed` → 6 records
- `Pont Rail_fixed` → 8 records
- `voie_fixed` → 2 records

### What this tells us
- source dataset metadata links are correct
- each source file contributed records to the GIS asset table
- the loader script mapping between file and `source_dataset_id` worked correctly

---

## Validation Query 8 — Count by corridor

### SQL
```sql
select corridor_id, count(*) as asset_count
from rail.gis_asset
group by corridor_id;
```

### Observed result
```text
corridor_id = 1, asset_count = 30
```

### Interpretation
All currently loaded GIS assets belong to the same corridor:

```text
corridor_id = 1
```

### What this tells us
- the current phase is internally consistent
- the inserted GIS assets are associated with the expected study corridor

---

# Overall validation conclusion

## Current validation status
The first GIS loading phase is **successful**.

### Key outcomes
- total assets loaded: **30**
- all loaded geometries use **EPSG:2154**
- invalid geometries: **0**
- null geometries: **0**
- dataset provenance links are working
- corridor assignment is working

## Meaning for the project
This means the project now has a valid first-phase spatial database layer for:
- rail-related GIS assets
- source dataset traceability
- corridor association
- future terrain and flood-risk enrichment

---

# Notes and instructions for use

## How to reuse these queries later
Keep these SQL queries in a validation file such as:

```text
sql/07_validation_queries.sql
```

You can rerun them after each future loading phase, for example after loading:
- additional 2D GIS layers
- future line-based `rail.track_segment`
- rainfall tables
- BIM-derived asset tables

## When to update the results in this document
Update this document whenever:
- more GIS layers are loaded
- rows are deleted or corrected
- a new corridor is added
- geometry is repaired or reprocessed

## Recommended project management actions now
Update:
- `docs/task_tracker.md`
- `docs/implementation_notes.md`

### Tasks that can now be marked as done
- create minimal schemas in Supabase
- create `core.dataset`
- create `rail.corridor`
- create `rail.gis_asset`
- register visible datasets in `core.dataset`
- load cleaned GIS layers into `rail.gis_asset`
- validate initial GIS asset load

---

# Recommended next step

## Next implementation phase
Proceed to **terrain / DTM-based analysis**.

### Suggested next work
1. inspect and document the DTM in more detail if needed
2. decide whether to derive terrain summaries for current polygon assets
3. later, if a line-based rail centerline becomes available, create `rail.track_segment`
4. then attach terrain-derived metrics to the rail network representation

---

# Suggested file name
This document can be saved as:

```text
docs/sql_validation_results_phase_1.md
```

or

```text
docs/gis_asset_validation_results.md
```
