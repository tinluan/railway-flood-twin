# GitHub Copilot Project Context: Railway Flood-Twin
# SNCF Railway Flood-Risk Digital Twin — Master Capstone Project
# Last Updated: 2026-04-26

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
4. Synthetic fallback (no DTM): Build stitched 30m platform:
   [Fosse L] -- [Talus L slope] -- [Voie flat top] -- [Talus R slope] -- [Fosse R]
   Use `z_config.json` nearest_talus / nearest_voie links to get neighbor Z values.

---

## Current Sprint Tasks (Demonstrator v0.3)

Each task has a TODO block in the code. Use Copilot inline chat (Ctrl+I) on the
TODO block to implement it.

### Task 1: Synthetic 2D Inundation Map
- File: `src/engine/synthetic_inundation.py`
- What: Implement `generate_flood_polygon()` using the pseudo-code in its docstring.
- Output: `data/processed/synthetic_flood.geojson` in EPSG:4326.
- Libraries: rasterio, numpy, geopandas, shapely, rasterio.features.

### Task 2: Flood Layer on the Map
- File: `src/dashboard/app_main.py` — find `TODO (AI COPILOT): Add Synthetic 2D Inundation Layer`
- What: Load synthetic_flood.geojson and add a semi-transparent blue GeoJsonLayer
  to the PyDeck layers list.
- Color: [0, 100, 255, 100]

### Task 3: Stitched Synthetic Cross-Section
- File: `src/dashboard/app_main.py` — find `TODO (AI COPILOT): Implement Stitched Synthetic Profile`
- What: Rewrite `make_synthetic_profile()` to produce a 30m stitched platform
  instead of a single trapezoid. Use z_config nearest_voie / nearest_talus.
- Profile shape (X from -15m to +15m):
  * [-15, -11] : Fosse bottom rising to Talus base (Concave)
  * [-11, -5]  : Talus slope up to track level
  * [-5,   5]  : Voie flat plateau
  * [5,   11]  : Talus slope back down
  * [11,  15]  : Fosse bottom

### Task 4: UI Hotspot Lock
- File: `src/dashboard/app_main.py` — find `TODO (AI COPILOT): Implement UI Hotspot Lock`
- What: Add `st.checkbox("Lock Asset Focus", key="lock_focus")`.
  If checked: use `st.session_state.get("locked_asset", asset_options[0])`.
  If unchecked: use `critical_idx` auto-selection as current.

---

## Coding Style

- PEP8 compliance.
- Type hints on all function signatures.
- Docstrings on all public functions.
- Use `logging` not `print()`.
- No hardcoded paths — always use `paths.*`.
