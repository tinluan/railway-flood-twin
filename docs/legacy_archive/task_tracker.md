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
| Organize raw project folders | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> | Team | Main raw folders prepared |
| Define Team Workflow Guide | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> | Tin | `team_workflow_guide.md` & `antigravity_rules.md` created |
| Create Onboarding Infrastructure | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> | Tin | `setup_team.ps1` and AI instructions ready |
| Setup GitHub Code Repository | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> | Tin | Repository pushed to `https://github.com/tinluan/railway-flood-twin.git` |
| Review architecture document | 🟢 <span style="color:green">Done</span> | 🟠 <span style="color:orange">Medium</span> | Team | Kept as conceptual reference |
| Inspect CRS of `voie` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Checked in QGIS / Python |
| Inspect CRS of DTM | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Confirmed DTM CRS |
| Export cleaned GIS files to `data/staging/gis/` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Cleaned `.gpkg` files created |
| Generate project docs from staging data | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | `generate_docs_from_staging.py` ran successfully |
| Create minimal schemas in Supabase | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | `core`, `rail` created; optional `env`, `bim` deferred |
| Create `core.dataset` table | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Dataset metadata table working |
| Create `rail.corridor` table | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Corridor row inserted |
| Create `rail.gis_asset` table | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Main current GIS asset storage table |
| Register visible datasets in `core.dataset` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | `voie_fixed`, `Buse_fixed`, `Pont Rail_fixed`, `Descente d'eau_fixed`, DTM registered |
| Load `voie_fixed` into `rail.gis_asset` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Loaded as `asset_type = track_area` |
| Load `Buse_fixed` into `rail.gis_asset` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Loaded as `asset_type = culvert` |
| Load `Pont Rail_fixed` into `rail.gis_asset` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Loaded as `asset_type = bridge` |
| Load `Descente d'eau_fixed` into `rail.gis_asset` | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Loaded as `asset_type = drainage_asset` |
| Validate initial GIS asset load | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | 30 total assets, SRID 2154, invalid geometry = 0, null geometry = 0 |
| Decide handling of `rail.track_segment` | 🟡 <span style="color:orange">Pending</span> | 🟠 <span style="color:orange">Medium</span> |  | Current `voie` is polygon-based; line/centerline representation still needed later |
| Run fast DTM terrain summary for `track_area` polygons | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Use `derive_track_area_elevation_updated.py` |
| Inspect terrain summary outputs | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Verified CSV and GeoPackage outputs |
| Validate terrain summary values | 🟢 <span style="color:green">Done</span> | 🔴 <span style="color:red">High</span> |  | Confirmed counts (16k pixels) and elevations |
| Decide whether to store terrain summaries in database | 🟡 <span style="color:orange">Pending</span> | 🟠 <span style="color:orange">Medium</span> |  | CSV/GPKG first, DB later if needed |
| Add more 2D GIS layers to `rail.gis_asset` | 🟡 <span style="color:orange">Pending</span> | 🟠 <span style="color:orange">Medium</span> |  | Extend beyond first 4 cleaned files |
| Add rainfall documents/data later | 🟡 <span style="color:orange">Pending</span> | 🔵 <span style="color:blue">Low</span> |  | Future phase |
| Add BIM documents/data later | 🟡 <span style="color:orange">Pending</span> | 🔵 <span style="color:blue">Low</span> |  | Future phase |
| Add line-based `rail.track_segment` later | 🟡 <span style="color:orange">Pending</span> | 🔵 <span style="color:blue">Low</span> |  | Depends on centerline source or derived line |
| Add IoT / advanced flood modelling later | 🟡 <span style="color:orange">Pending</span> | 🔵 <span style="color:blue">Low</span> |  | Future phase |

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
**Status:** Done ✅

Completed:
- ran the updated terrain summary workflow for `track_area`
- inspected outputs: 16,453 pixels analyzed; mean elevation 226.46m
- validated results against DTM bounds

---

## 🏛️ Milestone 4 — Subsystem Design & Brainstorming
**Status:** In Progress 🧪

Completed:
- [x] Architecture upgraded to **4-Layer SNCF Professional Standard**
- [x] **Rainfall Ingestion Blueprint** ([Link](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/rainfall_ingestion.md))
- [x] **Risk Engine Blueprint** (SWI + HEC-RAS + Fragility) ([Link](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/risk_engine.md))
- [x] **Spatial Handoff / Mirror DB Blueprint** ([Link](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/handoff_schema.md))
- [x] **SNCF Architecture Doc** ([Link](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/Architecture%20for%20a%20Railway%20Flood%E2%80%91Risk%20Digital%20Twin%20(SNCF%20Professional%20Standard).md))
- [x] **Contest Submission Mirror** updated to 4-layer architecture

Pending:
- [x] **Dashboard Blueprint** (Traffic Light HMI) ([Link](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/dashboard_design.md))

---

## Recommended next action

### Immediate next task
1.  **Dashboard Blueprint**: Draft the Traffic Light HMI design (`docs/subsystems/dashboard_design.md`).
2.  **Begin Code Generation**: Once all 4 blueprints are complete, execute the "Master Coding Session."
3.  **SWI Calibration**: Run the T optimization loop against historical accident data.

---

## Suggested update rule
Update this file after each **meaningful milestone**, for example:
- DTM summary completed
- terrain outputs validated
- new GIS layers loaded
- `rail.track_segment` added later
- rainfall or BIM integration starts
