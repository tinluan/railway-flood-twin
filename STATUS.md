# Railway Flood-Risk Digital Twin — STATUS

**Last Updated**: 2026-05-10
**Branch**: `dev/master-solution-trial`
**Version**: v0.4.0-demo
**Dashboard**: `.\.conda\python.exe -m streamlit run src/dashboard/app_main.py` (port 8501)

---

## Project File Map

```
README.md          -> Quickstart for new teammates
ARCHITECTURE.md    -> Engineering rules, formulas, data models (read this first)
STATUS.md          -> This file: live task tracker
.github/copilot-instructions.md -> AI context loaded automatically by VS Code Copilot
src/dashboard/app_main.py       -> Main Streamlit application
src/api/main.py                 -> FastAPI REST API and routes
tests/test_api.py               -> API test suite
src/engine/synthetic_inundation.py -> Bathtub flood polygon generator (DONE)
src/engine/hecras_bridge.py     -> HEC-RAS 6.7 COM connector (ready, needs .prj)
src/engine/hec_ras_runner.py    -> HEC-RAS 6.1 COM runner (legacy, superseded)
src/engine/extract_cross_sections.py -> DTM section extractor
src/engine/segment_voie.py      -> Splits Voie into ~100m DTM-sampled segments
src/engine/swi_calculator.py    -> SWI recursive filter + sigmoid runoff
src/engine/fragility_curves.py  -> Log-normal ballast scour P(failure)
src/engine/alert_dispatcher.py  -> RAMS-compliant operational alert generator
src/utils/paths.py              -> Canonical path resolver (use this for all paths)
src/paths.py                    -> Legacy path resolver (used by dashboard)
data/processed/z_config.json   -> 120+ assets, risk thresholds (Voie segmented)
data/processed/cross_sections.json -> 73 DTM profiles
data/processed/hecras_wse_results.json -> Synthetic 48h WSE per asset
data/processed/voie_segments.json -> Voie segment metadata with DTM elevations
data/processed/synthetic_flood_timesteps.json -> 48 GeoJSON flood polygons
data/processed/swi_results.csv  -> SWI + runoff coefficient per hour
```

---

## Completed

- [x] 103 base assets registered (Buse, Dalot, Fosse terre, Fosse revetu, Talus, Voie, Pont Rail)
- [x] Voie segmented into ~20 DTM-sampled track sections (`Voie_seg_00`..`Voie_seg_XX`)
- [x] Naming standardized: ASCII-only keys, no French accents in code/JSON
- [x] Risk Hierarchy: Yellow/Orange/RED thresholds operational for all assets
- [x] 73 cross-sections extracted from DTM raster (60m E-W profile, 1m resolution)
- [x] 48h Cevenol flash-flood storm scenario running (peak 40.9 mm/h at T+15h)
- [x] SWI recursive exponential filter (half-life 10d) + sigmoid runoff coefficient
- [x] HEC-RAS 6.7 COM bridge verified and ready for .prj
- [x] Dashboard live: map, time slider, WSE chart, cross-section, event log
- [x] 3D BIM MULTIPATCH data confirmed in `data/raw/maquette_3d/`
- [x] Documentation consolidated into 4 master files (README, ARCHITECTURE, STATUS, copilot-instructions)
- [x] RESTful API layer (FastAPI) exposing assets, alerts, hydrology, and engine endpoints
- [x] API test suite implemented (23/23 tests passing)
- [x] **Task 1** — Synthetic 2D inundation map: time-varying flood polygons → `synthetic_flood_timesteps.json`
- [x] **Task 2** — Flood layer loaded in dashboard from `synthetic_flood_timesteps.json`
- [x] **Task 3** — Stitched 30m platform cross-section (Fosse-Talus-Voie-Talus-Fosse)
- [x] **Task 4** — UI Hotspot Lock (`st.checkbox("Lock Asset Focus")` with session_state)

---

## In Progress (Sprint Tasks for Teammates)

> See `.github/copilot-instructions.md` for the exact Copilot instructions per task.

- [ ] **Task 5 — Bridge Longitudinal View** (lower priority)
  `src/dashboard/app_main.py`
  For Pont Rail assets, rotate sampling vector from perpendicular to parallel.

- [ ] **Task 6 — Verify 3D MULTIPATCH datum**
  Compare Z from `maquette_3d/voie/Voie.shp` against DTM at same X,Y.
  Use `pyshp` to read MULTIPATCH. Document result in this file.

- [ ] **Task 7 — Update `nearest_voie` references in z_config.json**
  All non-Voie assets still reference deleted `Voie_0`. Remap to nearest `Voie_seg_XX`.

- [ ] **Task 8 — Migrate engine scripts from `print()` to `logging`**
  Affects: `hecras_bridge.py`, `hec_ras_runner.py`, `segment_voie.py`, `swi_calculator.py`,
  `preprocessor.py`, `data_ingestion.py`, `extract_cross_sections.py`, `alert_dispatcher.py`.

---

## Blocked

- [ ] HEC-RAS Full Simulation — waiting for actual `.prj` project file (from team)
- [ ] Live MeteoFrance API — waiting for API key

---

## Next Steps Priority Order

1. Task 7 (fix stale `nearest_voie` → `Voie_seg_XX` in z_config.json)
2. Task 5 (bridge longitudinal view — visual improvement for Pont Rail)
3. Task 6 (datum verification — prerequisite for 3D BIM integration)
4. Task 8 (migrate print→logging — code quality)
5. Integrate HEC-RAS `.prj` when team member provides it
