# Task Tracker

This tracker reflects the **current project status** after:
- organizing the project folders
- fixing/exporting cleaned GIS files
- generating the documentation drafts
- creating the minimal Supabase database structure
- loading the first cleaned GIS layers into `rail.gis_asset`
- validating the first GIS asset loading phase

---

## Current task status

| Task | Status | Priority | Owner | Notes |
|---|---|---|---|---|
| Organize raw project folders | Done | High | Team | Main raw folders prepared |
| Define Team Workflow Guide | Done | High | Tin | `team_workflow_guide.md` & `antigravity_rules.md` created |
| Create Onboarding Infrastructure | Done | High | Tin | `setup_team.ps1` and AI instructions ready |
| Setup GitHub Code Repository | Done | High | Tin | Repository pushed to `https://github.com/tinluan/railway-flood-twin.git` |
| Review architecture document | Done | Medium | Team | Kept as conceptual reference |
| Inspect CRS of `voie` | Done | High |  | Checked in QGIS / Python |
| Inspect CRS of DTM | Done | High |  | Confirmed DTM CRS |
| Export cleaned GIS files to `data/staging/gis/` | Done | High |  | Cleaned `.gpkg` files created |
| Generate project docs from staging data | Done | High |  | `generate_docs_from_staging.py` ran successfully |
| Create minimal schemas in Supabase | Done | High |  | `core`, `rail` created; optional `env`, `bim` deferred |
| Create `core.dataset` table | Done | High |  | Dataset metadata table working |
| Create `rail.corridor` table | Done | High |  | Corridor row inserted |
| Create `rail.gis_asset` table | Done | High |  | Main current GIS asset storage table |
| Register visible datasets in `core.dataset` | Done | High |  | `voie_fixed`, `Buse_fixed`, `Pont Rail_fixed`, `Descente d'eau_fixed`, DTM registered |
| Load `voie_fixed` into `rail.gis_asset` | Done | High |  | Loaded as `asset_type = track_area` |
| Load `Buse_fixed` into `rail.gis_asset` | Done | High |  | Loaded as `asset_type = culvert` |
| Load `Pont Rail_fixed` into `rail.gis_asset` | Done | High |  | Loaded as `asset_type = bridge` |
| Load `Descente d'eau_fixed` into `rail.gis_asset` | Done | High |  | Loaded as `asset_type = drainage_asset` |
| Validate initial GIS asset load | Done | High |  | 30 total assets, SRID 2154, invalid geometry = 0, null geometry = 0 |
| Decide handling of `rail.track_segment` | Pending | Medium |  | Current `voie` is polygon-based; line/centerline representation still needed later |
| Run fast DTM terrain summary for `track_area` polygons | Pending | High |  | Use `derive_track_area_elevation_fast.py` |
| Inspect terrain summary outputs | Pending | High |  | Review CSV and GeoPackage outputs |
| Validate terrain summary values | Pending | High |  | Check counts, overlap, min/max/mean reasonableness |
| Decide whether to store terrain summaries in database | Pending | Medium |  | CSV/GPKG first, DB later if needed |
| Add more 2D GIS layers to `rail.gis_asset` | Pending | Medium |  | Extend beyond first 4 cleaned files |
| Add rainfall documents/data later | Pending | Low |  | Future phase |
| Add BIM documents/data later | Pending | Low |  | Future phase |
| Add line-based `rail.track_segment` later | Pending | Low |  | Depends on centerline source or derived line |
| Add IoT / advanced flood modelling later | Pending | Low |  | Future phase |

---

## Current milestone summary

### Milestone 1 — Project setup and database foundation
**Status:** Done

Completed:
- project folder structure prepared
- cleaned GIS files prepared
- documentation pack created
- collaboration workflow established
- minimal database schema created
- corridor and dataset metadata inserted

### Milestone 2 — First GIS loading phase
**Status:** Done

Completed:
- first cleaned GIS layers loaded into `rail.gis_asset`
- initial validation queries completed successfully

### Milestone 3 — Terrain / DTM workflow
**Status:** In progress

Next target:
- run the fast terrain summary workflow for `track_area`
- inspect and validate terrain summary outputs

---

## Recommended next action

### Immediate next task
Run:

```bash
python src/transform/derive_track_area_elevation_fast.py
```

Then review the outputs in:

```text
data/processed/terrain/
```

---

## Suggested update rule
Update this file after each **meaningful milestone**, for example:
- DTM summary completed
- terrain outputs validated
- new GIS layers loaded
- `rail.track_segment` added later
- rainfall or BIM integration starts
