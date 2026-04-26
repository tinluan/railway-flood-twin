# Project Status: Mission Control
*Current Snapshot of the Railway Flood-Risk Digital Twin*
**Last Updated: 2026-04-25 23:50 CET**

---

## Project Integration Map
*How our files work together*

```text
[ STRATEGY ] --> [   DESIGN   ] --> [  EXECUTION  ]
  Roadmap    -->   Blueprints  -->    Python Code
 (The Why)        (The How)          (The What)

1. Roadmap: docs/brainstorming/road_to_demonstrator.md
2. Blueprints: docs/brainstorming/alignment_and_risk_logic_summary.md
3. Subsystems: docs/subsystems/ (Rain, Risk, UI)
4. Code: src/engine/ and src/dashboard/
```

---

## Live Status
| Component | Status | Last Updated |
| :--- | :--- | :--- |
| **Branch** | `brainstorm/plm26-contest-logic` | 2026-04-25 |
| **Project Health** | :green_circle: Operational | 2026-04-25 |
| **Main Release** | `v0.3.0-demo` | 2026-04-25 |
| **Dashboard** | Running (port 8506) | 2026-04-25 |

---

## Current Phase: Demonstrator v0.3

### Completed
- [x] **103 Assets Registered**: All drainage infrastructure (Buse, Dalot, Fosse terre, Fosse terre revetu, Talus Terre, Voie, Pont Rail) loaded into risk engine.
- [x] **Naming Standardized**: Removed French accents from all code/data keys (Fosse instead of Fosse with accents).
- [x] **Risk Hierarchy**: Multi-disciplinary Yellow/Orange/Red thresholds operational.
- [x] **73 Cross-Sections Extracted**: DTM-based terrain profiles for assets within coverage area.
- [x] **48h Storm Simulation**: Synthetic Cevenol flash-flood scenario with SWI memory running.
- [x] **HEC-RAS Bridge**: COM API connector verified and ready for `.prj` file.
- [x] **Dashboard Live**: Streamlit with map, time slider, WSE charts, SWI panel, event log.
- [x] **3D BIM Discovered**: MULTIPATCH shapefiles in `maquette_3d/` confirmed to have full Z vertices for all assets.

### In Progress
- [ ] **Synthetic 2D Inundation Map**: Create a "bathtub" script to generate a dynamic blue flood polygon (GeoJSON) for the dashboard showcase, proving 2D UI capability before actual HEC-RAS Mapper integration.
- [ ] **Stitched Synthetic Profile**: Rebuild the UI cross-section to show an integrated platform (Voie + Talus + Fosse) rather than an isolated asset.
- [ ] **Longitudinal Bridge View**: Refactor cross-section logic for `Pont Rail` to sample parallel to the track.
- [ ] **UI Hotspot Lock**: Add a toggle to disable "Auto-Focus" so the user can lock the dashboard on a single asset while moving the time slider.
- [ ] **3D BIM Cross-Sections**: Extract perpendicular profiles from 3D MULTIPATCH geometry (100% coverage).
- [ ] **Verify 3D Vertical Datum**: Compare MULTIPATCH Z(raw) vs DTM to determine if offset is needed.

### Blocked
- [ ] **HEC-RAS Full Run**: Requires actual `.prj` project file.
- [ ] **Live MeteoFrance API**: Requires API key for real forecast data.

---

## Recent Achievements (This Session)
- [x] Expanded asset monitoring from 3 types to 7 types (103 assets total).
- [x] Implemented Cevenol flash-flood simulation (peak 40.9 mm/h).
- [x] Added SWI Leaky Bucket model (capacity 150mm, decay 0.02/h).
- [x] Standardized all naming conventions to ASCII-only.
- [x] Mass-extracted 73 DTM cross-section profiles.
- [x] Discovered 3D BIM MULTIPATCH data with native Z coordinates.

---

## Next Technical Steps
1. **Develop Synthetic 2D Inundation Map** — Extract flood extent polygons from DTM + WSE for UI showcase.
2. **Build Stitched Synthetic Profile** — Re-engineer the synthetic geometric fallback to show connected infrastructure.
3. **Implement Bridge View** — Apply the longitudinal section logic for `Pont Rail`.
4. **Verify 3D MULTIPATCH datum** — Compare raw Z vs DTM at same coordinates.
5. **Build 3D cross-section extractor** — Slice profiles from BIM vertex data (100% coverage).
6. **Acquire HEC-RAS `.prj` file** — Enable real hydraulic simulation.

---

## Key Data Files
| File | Description |
| :--- | :--- |
| `data/processed/z_config.json` | 103 assets, Yellow/Orange/Red Z thresholds |
| `data/processed/cross_sections.json` | 73 DTM terrain profiles |
| `data/processed/hecras_wse_results.json` | Synthetic WSE time-series |
| `data/raw/maquette_3d/` | 3D MULTIPATCH BIM models (all assets) |
| `src/dashboard/app_main.py` | Main Dashboard |
| `src/engine/hecras_bridge.py` | HEC-RAS COM connector |
