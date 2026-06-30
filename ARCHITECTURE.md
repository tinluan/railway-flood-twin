# Railway Flood-Risk Digital Twin — ARCHITECTURE

**Project**: SNCF Ligne_400 (Himalayas Corridor) Flood Risk Demonstrator
**Version**: v0.4.0
**Last Updated**: 2026-05-10

This file is the single source of truth for all engineering decisions.
When in doubt, follow the rules defined here.

---

## 1. Data Alignment

### 1.1 Horizontal (X, Y)
- All GIS files use **EPSG:2154 (Lambert 93)**. Unit: metres.
- CRS-fixed GeoPackages are in `data/staging/gis/`.
- Convert to **EPSG:4326** only at the final display step in the dashboard.

### 1.2 Vertical (Z) — Two Datum Systems
| Source | Raw Z Range | Offset Required | Notes |
|--------|-------------|-----------------|-------|
| 2D Shapefiles (`maquette_2d/`) | ~95-185m | **+107.0166m** | CAD origin vs NGF |
| 3D MULTIPATCH (`maquette_3d/`) | ~175-290m | **None (verified)** | Z already near NGF |
| DTM raster (`dtm_fixed.tif`) | ~200-250m | Reference datum | EPSG:2154 + NGF |

> **CRITICAL**: Never apply the +107m offset to 3D BIM assets. Datum verification
> is complete and confirmed they are already in the NGF range.

### 1.3 3D BIM Asset Inventory (MULTIPATCH in `data/raw/maquette_3d/`)
| Layer | Feature Count | Z Range (m) |
|-------|--------------|-------------|
| Buse  | 7  | 201 – 221 |
| Dalot | 1  | 213 – 216 |
| Fosse terre | 31 | 175 – 258 |
| Fosse terre revetu | 22 | 178 – 288 |
| Talus Terre | 36 | 178 – 284 |
| Voie | 1 | 180 – 290 |
| Descente eau | 3 | 210 – 267 |
| Drainage longitudinal | 10 | 204 – 222 |

---

## 2. Naming Convention (ASCII-Only — Mandatory)

All asset keys in code and JSON must be **ASCII-only** to prevent Windows
encoding errors. French accents are removed everywhere.

| Original French | Standardized Key |
|----------------|-----------------|
| Fossé terre | `Fosse terre` |
| Fossé terre revêtu | `Fosse terre revetu` |
| Drainage longitudinal à ciel ouvert | `Drainage longitudinal a ciel ouvert` |
| Voie_0, Pont Rail_3, Buse_7 | Keep these exact formats |

Applies to: `z_config.json`, `cross_sections.json`, `hecras_wse_results.json`,
all Python dicts, and GeoPackage layer names.

> **Note**: The GeoPackage _filenames_ on disk still use French accents
> (e.g. `Fossé terre_fixed.gpkg`). This is acceptable — the ASCII-only rule
> applies to **code keys** and **JSON keys**, not to filesystem paths.

---

## 3. Risk & Alert Hierarchy

System follows the engineering chain: **Hydraulics → Geotechnics → Operations**

| Level | CAP Color | Trigger | Engineering Meaning | Assets |
|-------|-----------|---------|---------------------|--------|
| YELLOW | Monitoring | WSE > `yellow_z_m` | Drainage at 100% capacity | Buse, Dalot, Drainage |
| ORANGE | Warning | WSE > `orange_z_m` | Water soaks embankment, erosion risk | Fosse, Talus |
| RED | Emergency | WSE > `red_z_m` | Water on rail track — halt trains | Voie |

### Key Rules
- Use `Voie_min_m` (the absolute lowest track elevation) for RED — not the mean.
- If `red_z < orange_z` (statistical anomaly), fallback to `orange_z + 0.5m`.
- Risk is evaluated **per segment**, not per corridor, enabling hotspot detection.

---

## 4. Cross-Section Rendering Strategy

### 4.1 DTM Raster Sampling (73/103 assets have coverage)
- Source: `data/staging/terrain/dtm_fixed.tif` (~1GB, on shared drive)
- Method: Sample a **60m East-West** line at **1m intervals** from the asset centroid.
  (Ligne 400 runs roughly N-S, so E-W ≈ perpendicular to track.)
- Results stored in: `data/processed/cross_sections.json`
- Extractor: `src/engine/extract_cross_sections.py`

### 4.2 Synthetic Geometric Fallback (30 assets outside DTM coverage)
For assets without DTM data, construct a mathematical profile using z_config thresholds.

**Profile Type A — Concave (Ditch/Culvert)**: Buse, Dalot, Fosse
- Center (distance=0) is the LOWEST point.
- Shape: flat bottom → slopes up → embankment.

**Profile Type B — Convex (Embankment/Track)**: Voie, Talus
- Center (distance=0) is the HIGHEST point.
- Shape: track plateau → slopes down → ditch.

**Stitched Platform Model (Target Implementation)**:
Combine all asset types into a 30m wide integrated section:
```
X:  -15  -11    -5     0     5     11   15
Z:  Fosse Talus  Talus  Voie  Talus Talus Fosse
     bot  base   top    top   top   base  bot
```
Use `z_config.json` `nearest_talus` and `nearest_voie` fields to get neighbor Z values.

### 4.3 Bridge Logic (Pont Rail)
- Do NOT cut across the bridge — use a **longitudinal section** (parallel to track).
- Extend 30m each side of the bridge to capture the Talus approaches.
- Display as a "sandwich": top=deck level, bottom=ground/riverbed, fill=water clearance.

### 4.4 Hotspot Auto-Focus (with UI Lock)
The dashboard auto-selects the highest-risk asset at each timestep. The
`st.checkbox("Lock Asset Focus")` (Task 4, DONE) prevents the cross-section
view from jumping when scrubbing the timeline — it freezes the selected asset
via `st.session_state["locked_asset"]`.

---

## 5. Hydrological Model (SWI + Synthetic WSE)

- **SWI Recursive Exponential Filter** (`src/engine/swi_calculator.py`):
  - Formula: `SWI(t) = R(t) * (1 - C) + SWI(t-1) * C` where `C = 0.5^(1/T)`, `T = 240h` (half-life 10 days)
  - **Not** a leaky bucket — there is no hard capacity ceiling.
- **Sigmoid Runoff Coefficient**: `C_runoff = C_max / (1 + e^(-k * (SWI - SWI_mid)))`
  - Parameters: `C_max=0.9`, `C_min=0.1`, `k=0.05`, `SWI_mid=150mm`
- **WSE Formula**: Rational Method + Manning's approximation + elevation-dependent
  valley accumulation effect.
- **Data**: `data/raw/rainfall_Ligne_400.csv` — 48h Cevenol storm (peak 40.9 mm/h at T+15h)
- **Output**:
  - `data/processed/swi_results.csv` — SWI, runoff_coeff, active_runoff per hour
  - `data/processed/hecras_wse_results.json` — 120+ assets × 48 timesteps (after Voie segmentation)

### 5.1 Synthetic Flood Polygons (`src/engine/synthetic_inundation.py`)
- **Method**: Corridor buffer around track + low-lying assets (Buse, Dalot)
- Buffer scales with WSE intensity: `MIN_BUFFER=5m` to `MAX_BUFFER=120m` (quadratic scaling)
- **Output**: `data/processed/synthetic_flood_timesteps.json` — 48 GeoJSON FeatureCollections
  keyed by timestep index (`"0"` through `"47"`), each in EPSG:4326.

---

## 6. HEC-RAS Integration (ACTIVE — pre-computed results available)

### 6.1 HEC-RAS Project (`data/New_data/HEC_RAS/`)
- **Project**: `CAPSTONE_JN_L752_PK` (Ligne 752, PK534 — South Head Tartaiguille)
- **Version**: HEC-RAS 6.60, SI Units, EPSG:2154
- **Mesh**: 2D flow area `PK534_FA_5M2`, 950,122 cells (~5m² resolution)
- **Boundary**: `PK534_BL`, friction slope 0.01
- **Structures**: 9 SA/2D connections (CULVERT_MAIN, CULVERT_ACCESS ×5, CULVERT_2, CULVERT_MAIN_3, CULVERT_VOIE_2)

### 6.2 Simulation Plans (Pre-Computed)
| Plan | Title | Duration | Timesteps | Δt Compute | Δt Output | Peak Depth |
|------|-------|----------|-----------|------------|-----------|------------|
| p01 | R100_1HR | 30MAR2026 13:00→14:00 | 13 | 1s | 5min | 9.79m |
| p02 | 21092025 | 21SEP2025 07:00→22SEP 04:00 | 127 | 5s | 10min | TBD |

### 6.3 Two Access Methods
- **COM Bridge** (`src/engine/hecras_bridge.py`): For live HEC-RAS runs via `RAS67.HECRASController`
- **HDF5 Reader** (`src/engine/hecras_hdf5_reader.py`): For reading pre-computed results (no HEC-RAS needed)

### 6.4 HDF5 Result Structure
```
Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/
  Time Date Stamp              → (N_timesteps,) timestamps
  2D Flow Areas/PK534_FA_5M2/
    Water Surface              → (N_timesteps, 950122) WSE in metres NGF
    Face Velocity              → (N_timesteps, 1894408) m/s
    Cell Cumulative Precip     → (N_timesteps, 950122) mm
Geometry/2D Flow Areas/PK534_FA_5M2/
  Cells Center Coordinate      → (950122, 2) Lambert 93 X,Y
  Cells Minimum Elevation      → (950122,) terrain Z per cell
```

---

## 7. Dashboard Architecture

- **Framework**: Streamlit (`src/dashboard/app_main.py`)
- **Map**: PyDeck with CARTO base tiles + GeoJSON infrastructure layers + flood polygons
- **Assets Monitored**: 7 types, 120+ total (after Voie segmentation into ~20 track sections)
- **Point Assets**: Buse, Dalot, Pont Rail, Fosse terre, Fosse revetu, Talus Terre, Voie segments
- **Infrastructure Line Layers**: Voie, Talus, Fosse terre, Fosse revetu, Drainage longitudinal
- **Charts**: WSE 48h time-series + Stitched Platform Cross-Section with water fill
- **Features**: CAP-standard color alerts, Hotspot Lock checkbox, Top-5 Critical Asset table

### Path Module Note
The dashboard imports from the **legacy** `src/paths.py` (uses `RAW_DATA`, `PROCESSED_DATA`).
Engine scripts may use either `src/paths.py` or the canonical `src/utils/paths.py` (`ProjectPaths`).
Both resolve via `.env` `DATA_ROOT`. Do not break the legacy import in `app_main.py`.

### To Start the Dashboard
```powershell
.\.conda\python.exe -m streamlit run src/dashboard/app_main.py
```

---

## 8. Key Data Files

| File | Description |
|------|-------------|
| `data/processed/z_config.json` | 120+ assets with Yellow/Orange/Red Z thresholds |
| `data/processed/cross_sections.json` | 73 DTM terrain profiles (60m E-W, 1m res) |
| `data/processed/hecras_wse_results.json` | Synthetic 48h WSE per asset |
| `data/processed/voie_segments.json` | Voie segment metadata with DTM elevations |
| `data/processed/synthetic_flood_timesteps.json` | 48 GeoJSON flood polygon timesteps |
| `data/processed/swi_results.csv` | SWI + runoff coefficient per hour |
| `data/raw/rainfall_Ligne_400.csv` | 48h Cevenol storm input |
| `data/raw/maquette_3d/` | 3D BIM MULTIPATCH shapefiles (all assets) |
| `data/New_data/HEC_RAS/*.prj` | HEC-RAS 6.6 project file (CAPSTONE_JN_L752_PK) |
| `data/New_data/HEC_RAS/*.p01.hdf` | Plan 1: R100_1HR pre-computed results (512 MB) |
| `data/New_data/HEC_RAS/*.p02.hdf` | Plan 2: 21092025 pre-computed results (422 MB) |
| `data/New_data/INFRA_SNCF/*.xlsx` | SNCF infrastructure database V2 (28K rainfall rows) |
| `data/New_data/CAPSTONE/2D_OBJECTS/` | BIM 2D shapefiles (English naming, 10 asset types) |
| `data/New_data/CAPSTONE/3D_OBJECTS/` | BIM 3D MULTIPATCH (English naming, incl. Tunnel) |
| `src/dashboard/app_main.py` | Main Streamlit dashboard |
| `src/api/main.py` | FastAPI application and REST endpoints |
| `tests/test_api.py` | API validation test suite |
| `src/engine/hecras_bridge.py` | HEC-RAS 6.7 COM API connector (live runs) |
| `src/engine/hecras_hdf5_reader.py` | HEC-RAS HDF5 result reader (pre-computed) |
| `src/engine/synthetic_inundation.py` | Bathtub flood polygon generator (DONE) |
| `src/engine/segment_voie.py` | Splits Voie into DTM-sampled ~100m segments |
| `src/engine/swi_calculator.py` | SWI recursive filter + sigmoid runoff |
| `src/engine/fragility_curves.py` | Log-normal ballast scour P(failure) |
| `src/engine/alert_dispatcher.py` | RAMS-compliant operational alert generator |

---

## 9. API Architecture

- **Framework**: FastAPI (`src/api/main.py`)
- **Purpose**: Programmatic access to Ligne_400 Digital Twin data (Layer 4 vulnerability verdicts).
- **Endpoints**:
  - `GET /api/v1/assets`: Static infrastructure config.
  - `GET /api/v1/alerts/current`: Real-time RAMS verdicts & hotspot auto-focus.
  - `GET /api/v1/hydrology/swi`: SWI values & synthetic flood polygons.
  - `POST /api/v1/engine/simulate`: Run custom rainfall array memory-only simulations.
- **Testing**: `tests/test_api.py` (23 passing tests via TestClient).
