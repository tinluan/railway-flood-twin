# Data Dictionary

## `core.dataset`
- `dataset_id`: unique dataset identifier
- `dataset_name`: human-readable dataset name
- `dataset_type`: high-level category such as `rail_gis`, `terrain`, `rainfall`, `bim`
- `source_uri`: file path or source reference
- `source_format`: file or source format
- `source_crs`: original CRS of the source dataset
- `target_srid`: SRID used in the database after transformation
- `version_tag`: optional version label
- `ingested_at`: timestamp of ingestion or registration
- `notes`: additional notes

## `rail.corridor`
- `corridor_id`: unique corridor identifier
- `corridor_code`: short project corridor code
- `corridor_name`: human-readable corridor name
- `description`: corridor description
- `geom`: corridor geometry

## `rail.track_segment`
- `track_segment_id`: unique segment identifier
- `corridor_id`: associated corridor
- `segment_code`: unique segment code
- `line_name`: rail line name if available
- `track_name`: track name if available
- `start_chainage_m`: start chainage in meters
- `end_chainage_m`: end chainage in meters
- `length_m`: segment length in meters
- `elevation_min_m`: minimum sampled terrain elevation along the segment
- `elevation_max_m`: maximum sampled terrain elevation along the segment
- `geom`: line geometry of the segment

## `rail.gis_asset`
- `gis_asset_id`: unique GIS asset identifier
- `corridor_id`: associated corridor
- `track_segment_id`: linked rail segment if known
- `asset_type`: main classification, e.g. `culvert`, `bridge`, `open_drain`
- `asset_subtype`: more detailed classification if needed
- `asset_name`: human-readable asset name
- `asset_code`: source or project asset code
- `status`: operational or lifecycle status if available
- `properties`: JSON attributes copied from source data
- `geom`: geometry of the GIS asset

## Future tables
### `env.rain_station`
Stores rainfall observation points.

### `env.rainfall_observation`
Stores rainfall time-series records.

### `bim.ifc_model`
Stores IFC file metadata.

### `bim.bim_asset`
Stores BIM-derived objects extracted from IFC.
