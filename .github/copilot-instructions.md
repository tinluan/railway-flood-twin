# GitHub Copilot Project Context: Railway Flood-Twin
# SNCF Railway Flood-Risk Digital Twin — Master Capstone Project
# Last Updated: 2026-05-10

You are a senior Python/Streamlit/GIS engineer assisting the team on a
production-ready Digital Twin for railway flood risk monitoring.
Always read ARCHITECTURE.md for engineering rules before writing code.

---

## Core Architecture Rules

1. NO HARDCODED PATHS: All paths MUST come from `src/utils/paths.py`.
   - Use `paths.PROCESSED_DATA / 'file.json'` not `'C:/Users/...'`.
   - The dashboard still imports from `src/paths.py` (legacy). Do not change that.

2. PORTABILITY FIRST: Code must work for Tin (C:), Szilvi, and Amal regardless
   of their local drive letter. The `.env` file controls the DATA_ROOT variable.

3. NAMING CONVENTION (CRITICAL): Use ASCII-only keys for every asset.
   - CORRECT:   `Fosse terre`, `Fosse terre revetu`, `Voie_0`, `Pont Rail_3`
   - INCORRECT: `Fossé terre`, `Fossé terre revêtu`, `Voie0`
   - This applies to: z_config.json, cross_sections.json, hecras_wse_results.json,
     and all Python dictionaries. French accents cause silent Windows encoding bugs.

4. COORDINATE SYSTEMS:
   - Internal GIS processing: EPSG:2154 (Lambert 93) — unit is metres.
   - Frontend (PyDeck/Streamlit map): EPSG:4326 (WGS84) — unit is decimal degrees.
   - Always convert with `.to_crs("EPSG:4326")` only at the last step before display.

5. PROJECT STRUCTURE:
   - `data/raw/`          — Original unmodified source files (read-only).
   - `data/staging/gis/`  — CRS-fixed GeoPackages (.gpkg) for all assets.
   - `data/staging/terrain/` — DTM raster: `dtm_fixed.tif` (~1GB, on shared drive).
   - `data/processed/`    — Computed outputs (z_config.json, cross_sections.json, etc.)
   - `src/engine/`        — Python computation scripts (risk, hydrology, BIM).
   - `src/dashboard/`     — Streamlit dashboard (`app_main.py`).
   - `src/utils/`         — Shared utilities (paths.py, check_health.py).

6. DOCUMENTATION: ARCHITECTURE.md is the single source of truth for engineering
   blueprints, formulas, alert thresholds, and data models.

---

## Governance Rules

- NO DIRECT PUSH TO MAIN: Always work on a feature branch.
- GATEKEEPER: After every task, update the checkbox in STATUS.md.
- HEALTH CHECK: Run `python src/utils/check_health.py` after any environment change.
- DO NOT use `print()` in production scripts — use `logging`.

---

## Risk Alert Logic (Summary — see ARCHITECTURE.md Section 3 for full detail)

| Alert Level | Trigger Condition            | Asset Types Affected              |
|-------------|------------------------------|-----------------------------------|
| YELLOW      | WSE > yellow_z_m (Buse max)  | Buse, Dalot, Drainage longitudinal|
| ORANGE      | WSE > orange_z_m (Talus mean)| Fosse terre, Fosse revetu, Talus  |
| RED         | WSE > red_z_m  (Voie min)    | Voie (Track)                      |

Red alert triggers when the LOWEST point of a track segment is reached,
even if other metrics are not yet exceeded.

---

## Cross-Section Rendering Rules (see ARCHITECTURE.md Section 4)

1. Ditch assets (Buse, Dalot, Fosse): Profile is CONCAVE — center is lowest point.
2. Embankment assets (Voie, Talus): Profile is CONVEX — center is highest point.
3. Bridge assets (Pont Rail): Use a LONGITUDINAL section (parallel to track),
   showing deck level (top) vs ground/riverbed (bottom) = clearance.
4. Synthetic fallback (no DTM): Build stitched 30m platform (DONE in `make_stitched_profile()`):
   [Fosse L] -- [Talus L slope] -- [Voie flat top] -- [Talus R slope] -- [Fosse R]
   Uses the asset's own Yellow/Orange/Red thresholds to shape the profile.
   Note: `nearest_voie` in z_config.json still references deleted `Voie_0` — needs remapping.

---

## Completed Tasks (v0.3 → v0.4)

The following tasks from the v0.3 sprint are **done** and merged:

- ✅ **Task 1**: Synthetic 2D inundation map → `generate_time_varying_flood()` in
  `src/engine/synthetic_inundation.py`. Output: `data/processed/synthetic_flood_timesteps.json`
  (48 GeoJSON FeatureCollections, one per hour).
- ✅ **Task 2**: Flood layer loaded in dashboard from `synthetic_flood_timesteps.json`.
- ✅ **Task 3**: Stitched 30m platform cross-section → `make_stitched_profile()` in
  `app_main.py`. Layout: Fosse-Talus-Voie-Talus-Fosse using asset thresholds.
- ✅ **Task 4**: UI Hotspot Lock → `st.checkbox("Lock Asset Focus")` with `st.session_state`.

---

## Current Sprint Tasks (Demonstrator v0.4)

### Task 5: Bridge Longitudinal View (lower priority)
- File: `src/dashboard/app_main.py`
- What: For Pont Rail assets, rotate sampling vector from perpendicular to parallel.
- Show a "sandwich" cross-section: deck level (top) vs ground/riverbed (bottom).

### Task 6: Verify 3D MULTIPATCH Datum
- Compare Z from `maquette_3d/voie/Voie.shp` against DTM at same X,Y.
- Use `pyshp` to read MULTIPATCH. Document result in STATUS.md.

### Task 7: Fix Stale `nearest_voie` in z_config.json
- All non-Voie assets reference deleted `Voie_0`. Remap to nearest `Voie_seg_XX`.
- Impacts stitched profile accuracy when using neighbor lookups.

### Task 8: Migrate Engine Scripts to `logging`
- Replace all `print()` calls with `logging` in `src/engine/*.py`.
- Only `synthetic_inundation.py` currently uses `logging` correctly.

---

## Coding Style

- PEP8 compliance.
- Type hints on all function signatures.
- Docstrings on all public functions.
- Use `logging` not `print()`.
- No hardcoded paths — always use `paths.*`.
