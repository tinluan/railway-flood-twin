# Data Inventory

> Update this file every time a new dataset is added, inspected, reprojected, or loaded.

| Dataset name | Source path | Type | Geometry / Raster | CRS | Target table | Current status | Notes |
|---|---|---|---|---|---|---|---|
| Voie (2D) | `data/raw/maquette_2d/voie/` | Shapefile | LineString *(to verify)* | TBD | `rail.track_segment` | To inspect | Main track/alignment layer |
| Dalot (2D) | `data/raw/maquette_2d/dalot/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Likely culvert layer |
| Pont Rail (2D) | `data/raw/maquette_2d/pont_rail/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Likely rail bridge layer |
| Descente eau (2D) | `data/raw/maquette_2d/descente_eau/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Drainage-related asset |
| Drainage longitudinal ciel ouvert (2D) | `data/raw/maquette_2d/drainage_longitudinal_ciel_ouvert/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Open drainage layer |
| Fosse terre (2D) | `data/raw/maquette_2d/fosse_terre/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Earth ditch layer |
| Fosse terre revetu (2D) | `data/raw/maquette_2d/fosse_terre_revetu/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Lined ditch layer |
| Talus terre (2D) | `data/raw/maquette_2d/talus_terre/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Earth slope / embankment |
| Routes (2D) | `data/raw/maquette_2d/routes/` | Shapefile | TBD | TBD | `rail.gis_asset` | To inspect | Road / context layer |
| Base (2D) | `data/raw/maquette_2d/base/` | Shapefile | TBD | TBD | TBD | To inspect | Needs semantic review |
| Reseau tiers (2D) | `data/raw/maquette_2d/reseau_tiers/` | Shapefile or GIS layer | TBD | TBD | TBD | To inspect | Needs interpretation |
| Voie (3D) | `data/raw/maquette_3d/voie/` | Shapefile / GIS layer | Z-aware? TBD | TBD | Later | Not immediate | Keep for later enrichment |
| Dalot (3D) | `data/raw/maquette_3d/dalot/` | Shapefile / GIS layer | Z-aware? TBD | TBD | Later | Not immediate | Keep for later enrichment |
| Tunnel (3D) | `data/raw/maquette_3d/tunnel/` | Shapefile / GIS layer | TBD | TBD | Later | Not immediate | Tunnel context / future asset support |
| DTM PK520_PK535_NO_HOLES | `data/raw/dtm/` | Raster ASCII grid | Raster | TBD | external terrain workflow / `env.terrain_raster` later | To inspect | Use first for elevation summaries |
| BIM IFC folder | `data/raw/bim_ifc/` | IFC / related files | N/A | TBD | `bim.ifc_model` later | Empty / pending | Future phase |
| Rainfall folder | `data/raw/rainfall/` | CSV / XLSX / API exports | N/A | N/A | `env.rain_station`, `env.rainfall_observation` later | Empty / pending | Future phase |

## Inspection checklist for each dataset
- Confirm geometry type
- Confirm CRS
- Check attribute fields
- Check null geometry count
- Check invalid geometry count
- Confirm whether it belongs to `rail.track_segment` or `rail.gis_asset`
