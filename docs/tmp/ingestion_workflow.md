# Ingestion Workflow

## Goal
Define the step-by-step workflow for bringing source files into the project database.

## Phase 1 workflow — current MVP

### Step 1 — Organize raw files
- Keep original source files in `data/raw/`
- Keep each dataset together with all companion files

### Step 2 — Inspect source layers
For each dataset:
- confirm geometry type
- confirm CRS
- review key attribute fields
- decide target database table

### Step 3 — Register datasets
Insert one metadata record into `core.dataset` for each source dataset.

### Step 4 — Load main rail alignment
- source: `data/raw/maquette_2d/voie/`
- target: `rail.track_segment`

### Step 5 — Load rail GIS assets
- source: selected 2D GIS layers
- target: `rail.gis_asset`

### Step 6 — Link assets to track segments
Use intersection and/or nearest-segment logic.

### Step 7 — Process terrain
- source: DTM raster in `data/raw/dtm/`
- derive segment elevation summaries in Python
- write `elevation_min_m` and `elevation_max_m` into `rail.track_segment`

### Step 8 — Validate
Run geometry, CRS, and row-count checks.

## Future workflow extensions
### Rainfall
- register rain stations
- load rainfall observations

### BIM / IFC
- register IFC file metadata
- extract BIM assets
- link BIM assets to GIS assets or rail segments
