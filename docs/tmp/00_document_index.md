# Document Index — Railway Flood-Risk Digital Twin

This pack completes the core management and implementation documents for the student project.

## Recommended reading order
1. `project_overview.md`
2. `architecture_review.md`
3. `railway_flood_twin_design_v1_1.md` *(existing project-specific database design)*
4. `data_inventory.md`
5. `source_to_table_mapping.md`
6. `crs_strategy.md`
7. `ingestion_workflow.md`
8. `validation_plan.md`
9. `data_dictionary.md`
10. `task_tracker.md`
11. `risk_register.md`
12. `implementation_notes.md`
13. `changelog.md`

## Current project implementation focus
- First implementation target: **2D Rail GIS + DTM + Supabase/PostGIS**
- Later phases: **Rainfall**, **BIM/IFC**, **IoT**, **risk modelling enhancements**

## Current visible source data
- `data/raw/dtm/`
- `data/raw/maquette_2d/`
- `data/raw/maquette_3d/`
- `data/raw/bim_ifc/`

## Immediate technical priority
- Inspect CRS and geometry types
- Create the minimal database tables
- Load `voie` into `rail.track_segment`
- Load asset layers into `rail.gis_asset`
- Derive elevation summaries from the DTM
