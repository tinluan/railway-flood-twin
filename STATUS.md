# Railway Flood-Risk Digital Twin — STATUS

**Last Updated**: 2026-04-26
**Branch**: `dev/master-solution-trial`
**Version**: v0.3.0-demo
**Dashboard**: `python -m streamlit run src/dashboard/app_main.py` (port 8501)

---

## Project File Map

```
README.md          -> Quickstart for new teammates
ARCHITECTURE.md    -> Engineering rules, formulas, data models (read this first)
STATUS.md          -> This file: live task tracker
.github/copilot-instructions.md -> AI context loaded automatically by VS Code Copilot
src/dashboard/app_main.py       -> Main Streamlit application
src/engine/synthetic_inundation.py -> Task 1: Bathtub flood map (TODO)
src/engine/hecras_bridge.py     -> HEC-RAS COM connector (ready, needs .prj)
src/engine/extract_cross_sections.py -> DTM section extractor
src/utils/paths.py              -> Canonical path resolver (use this for all paths)
data/processed/z_config.json   -> 103 assets, risk thresholds
data/processed/cross_sections.json -> 73 DTM profiles
data/processed/hecras_wse_results.json -> Synthetic 48h WSE per asset
```

---

## Completed

- [x] 103 assets registered (Buse, Dalot, Fosse terre, Fosse revetu, Talus, Voie, Pont Rail)
- [x] Naming standardized: ASCII-only keys, no French accents in code/JSON
- [x] Risk Hierarchy: Yellow/Orange/RED thresholds operational for all 103 assets
- [x] 73 cross-sections extracted from DTM raster
- [x] 48h Cevenol flash-flood storm scenario running (peak 40.9 mm/h at T+15h)
- [x] SWI Leaky Bucket model (capacity 150mm, decay 0.02/h)
- [x] HEC-RAS COM bridge verified and ready for .prj
- [x] Dashboard live: map, time slider, WSE chart, cross-section, event log
- [x] 3D BIM MULTIPATCH data confirmed in `data/raw/maquette_3d/`
- [x] Documentation consolidated into 4 master files (README, ARCHITECTURE, STATUS, copilot-instructions)

---

## In Progress (Sprint Tasks for Teammates)

> See `.github/copilot-instructions.md` for the exact Copilot instructions per task.
> Each task has a `# TODO (AI COPILOT)` block in the code. Open the file and use Ctrl+I.

- [ ] **Task 1 — Synthetic 2D Inundation Map**
  `src/engine/synthetic_inundation.py`
  Bathtub flood mask: DTM < peak_WSE → GeoJSON polygon → `data/processed/synthetic_flood.geojson`

- [ ] **Task 2 — Map Flood Layer**
  `src/dashboard/app_main.py` (line ~360)
  Load `synthetic_flood.geojson` and add blue GeoJsonLayer to PyDeck map.

- [ ] **Task 3 — Stitched Synthetic Cross-Section**
  `src/dashboard/app_main.py` (line ~495)
  Rebuild `make_synthetic_profile()` to produce integrated 30m platform profile.

- [ ] **Task 4 — UI Hotspot Lock**
  `src/dashboard/app_main.py` (line ~400)
  `st.checkbox("Lock Asset Focus")` using st.session_state to freeze selection.

- [ ] **Task 5 — Bridge Longitudinal View** (lower priority)
  `src/dashboard/app_main.py`
  For Pont Rail assets, rotate sampling vector from perpendicular to parallel.

- [ ] **Task 6 — Verify 3D MULTIPATCH datum**
  Compare Z from `maquette_3d/voie/Voie.shp` against DTM at same X,Y.
  Use `pyshp` to read MULTIPATCH. Document result in this file.

---

## Blocked

- [ ] HEC-RAS Full Simulation — waiting for actual `.prj` project file (from team)
- [ ] Live MeteoFrance API — waiting for API key

---

## Next Steps Priority Order

1. Task 1 + Task 2 together (flood polygon generation + map display)
2. Task 3 (stitched profile — biggest visual improvement)
3. Task 4 (UI lock — needed for smooth live demo)
4. Task 6 (datum verification — prerequisite for 3D BIM integration)
5. Integrate HEC-RAS `.prj` when team member provides it
