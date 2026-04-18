# Source to Table Mapping

> Auto-generated from cleaned staging files. Review manually.

| Source file | Target database table | Suggested asset_type | Loading priority | Notes |
|---|---|---|---|---|
| `Buse_fixed.gpkg` | `TBD` | `TBD` | Low | geometry=MultiPolygon |
| `Dalot_fixed.gpkg` | `rail.gis_asset` | `culvert` | High | geometry=MultiPolygon |
| `Descente d'eau_fixed.gpkg` | `rail.gis_asset` | `drainage_asset` | High | geometry=MultiPolygon |
| `Drainage_longitudinal_à_ciel_ouvert_fixed.gpkg` | `rail.gis_asset` | `open_drain` | High | geometry=MultiPolygon |
| `Fossé terre revêtu_fixed.gpkg` | `rail.gis_asset` | `ditch_lined` | Medium | geometry=MultiPolygon |
| `Fossé terre_fixed.gpkg` | `rail.gis_asset` | `ditch_earth` | Medium | geometry=MultiPolygon |
| `Pont Rail_fixed.gpkg` | `rail.gis_asset` | `bridge` | High | geometry=MultiPolygon |
| `reseau tiers-fixed.gpkg` | `TBD` | `TBD` | Low | geometry=MultiPolygon |
| `routes_fixed.gpkg` | `rail.gis_asset` | `road` | Medium | geometry=MultiPolygon |
| `Talus Terre_fixed.gpkg` | `rail.gis_asset` | `earth_slope` | Medium | geometry=MultiPolygon |
| `voie_fixed.gpkg` | `rail.gis_asset` | `track_area` | High | geometry=MultiPolygon |
| `PK520_PK535_NO_HOLES (1).asc` | `external terrain workflow first` | `terrain_source` | High | geometry=Raster |
