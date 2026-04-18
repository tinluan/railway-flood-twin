# Updated DTM terrain summary script

## Save to
`src/transform/derive_track_area_elevation.py`

## Main changes
- uses a fixed GeoTIFF working DTM from `data/staging/terrain/`
- avoids auto-picking the wrong `.asc` copy
- prints progress for each feature
- safer CRS alignment for the cleaned `voie_fixed.gpkg`

## Expected working DTM location
Preferred:
```text
data/staging/terrain/dtm_2154.tif
```

If that exact file does not exist, the script will use the first `.tif` found in:
```text
data/staging/terrain/
```

## Run from the project root
```bash
python src/transform/derive_track_area_elevation.py
```

## Outputs
- `data/processed/terrain/track_area_elevation_summary.csv`
- `data/processed/terrain/voie_with_elevation.gpkg`
