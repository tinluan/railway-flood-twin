# How to use `derive_track_area_elevation.py`

## Purpose
This script reads the DTM raster and the cleaned `voie_fixed.gpkg` layer, then calculates:
- minimum elevation
- maximum elevation
- mean elevation
- valid pixel count

for each `track_area` polygon.

## Save the script to
`src/transform/derive_track_area_elevation.py`

## Run from the project root
```bash
python src/transform/derive_track_area_elevation.py
```

## Expected outputs
- `data/processed/terrain/track_area_elevation_summary.csv`
- `data/processed/terrain/voie_with_elevation.gpkg`

## Current assumptions
- DTM is in `data/raw/dtm/`
- cleaned `voie_fixed.gpkg` is in `data/staging/gis/`
- both should be in the same CRS or the script will reproject `voie` to the DTM CRS
