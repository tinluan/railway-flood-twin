# Source to Table Mapping

| Source layer / folder | Target database table | Suggested asset_type | Loading priority | Notes |
|---|---|---|---|---|
| `voie` | `rail.track_segment` | - | High | Main rail alignment / track geometry |
| `dalot` | `rail.gis_asset` | `culvert` | High | Important flood-related asset |
| `pont_rail` | `rail.gis_asset` | `bridge` | High | Important flood-related structure |
| `descente_eau` | `rail.gis_asset` | `drainage_asset` | High | Drainage-related layer |
| `drainage_longitudinal_ciel_ouvert` | `rail.gis_asset` | `open_drain` | High | Open drainage line |
| `fosse_terre` | `rail.gis_asset` | `ditch_earth` | Medium | Drainage / ditch context |
| `fosse_terre_revetu` | `rail.gis_asset` | `ditch_lined` | Medium | Drainage / ditch context |
| `talus_terre` | `rail.gis_asset` | `earth_slope` | Medium | Slope / embankment context |
| `routes` | `rail.gis_asset` | `road` | Medium | Context / crossings |
| `base` | TBD | TBD | Low | Needs semantic inspection first |
| `reseau_tiers` | TBD | TBD | Low | Needs semantic inspection first |
| `maquette_3d/*` | Later / optional | Later | Low | Keep for future enrichment |
| `dtm` | external terrain workflow first | terrain source | High | Use for segment elevation summaries |
| `rainfall/*` | `env.rain_station`, `env.rainfall_observation` | N/A | Later | Not yet available |
| `bim_ifc/*` | `bim.ifc_model`, `bim.bim_asset` | N/A | Later | Not yet integrated |
