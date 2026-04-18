# Validation Plan

## Purpose
Define the checks required to ensure the project database is consistent and usable.

## 1. Source data validation
For each source dataset:
- file exists
- expected companion files exist
- CRS is known or recoverable
- geometry type matches expectations
- attributes are readable

## 2. Geometry validation
Check that:
- geometries are not null
- geometries are valid
- geometry type matches the target table
- SRID is consistent across loaded layers

## 3. Database validation
### `rail.track_segment`
- row count looks reasonable
- no duplicate `segment_code`
- `length_m >= 0`
- no invalid geometries

### `rail.gis_asset`
- `asset_type` is populated
- `corridor_id` is populated
- geometry is valid
- `track_segment_id` is populated where possible after linking

## 4. CRS validation
- all loaded vector layers use the project target SRID
- source CRS is recorded in `core.dataset`

## 5. Terrain validation
- DTM raster CRS confirmed
- track segments overlap the expected terrain extent
- derived elevation values are numeric and plausible

## 6. Query validation
Test at least these queries:
- count track segments
- count assets by `asset_type`
- list assets linked to a segment
- list segment elevation ranges

## 7. Logging
Record validation results in:
- `docs/implementation_notes.md`
- optional logs in `outputs/logs/`
