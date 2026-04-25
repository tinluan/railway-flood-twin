# CRS Strategy

## Purpose
This document records the coordinate reference system strategy for the project.

## Current rule
Before loading any GIS or raster dataset into the database, confirm the source CRS.

## Project target CRS
**Preferred analytical target:** `EPSG:2154` *(if confirmed appropriate for the project area)*

## Why a single target CRS matters
Using one target CRS simplifies:
- spatial joins
- distance calculations
- terrain overlay
- asset-to-track linking
- map consistency

## Current action items
- inspect CRS of all 2D shapefiles
- inspect CRS of the DTM raster
- record source CRS in `core.dataset.source_crs`
- transform GIS layers during ingestion if needed

## Conversion rule
- raw files remain unchanged in `data/raw/`
- transformed versions may be written to `data/staging/`
- database tables should use the target project SRID

## Recording format
For each dataset, record:
- source CRS name
- EPSG code if known
- whether transformation is required
- target SRID used in database

## Current status
- CRS not yet confirmed for all visible datasets
- CRS inspection required before first load
