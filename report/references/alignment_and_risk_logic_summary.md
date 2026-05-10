# Digital Twin Synchronization & Risk Logic Summary
**Project: SNCF Railway Flood-Risk Digital Twin (Master Capstone)**
**Last Updated: 2026-04-25 23:50 CET**

This document is the authoritative engineering blueprint for the Digital Twin system. It summarizes all data alignment, risk logic, simulation architecture, and naming conventions agreed upon during the brainstorming sessions.

---

## 1. Data Alignment (Horizontal & Vertical)

### 1.1 Horizontal (X, Y)
- All raw 2D/3D models have been assigned **EPSG:2154 (Lambert 93)** CRS by generating missing `.prj` files.
- Aligned GeoPackages are stored in `data/staging/gis/`.

### 1.2 Vertical (Z) — Two Datum Systems
- **2D Shapefiles** (`maquette_2d/`): A discrepancy of **+107.0166m** was identified between the raw CAD models and the DTM (NGF). Aligned attribute tables are in `data/processed/maquette_3d_aligned/` with Z shifted by +107.02m.
- **3D MULTIPATCH** (`maquette_3d/`): These contain true 3D vertex Z values. Preliminary analysis shows Z(raw) ranges are already close to DTM NGF values (e.g., Buse raw Z: 201-221m vs DTM area: 200-250m). **Verification pending**: compare 3D Z against DTM at the same XY coordinates to confirm whether offset is needed.

### 1.3 3D BIM Asset Inventory (MULTIPATCH)

| Layer | Features | Z Range (raw, m) | Geometry Type |
| :--- | :--- | :--- | :--- |
| Buse (base/) | 7 | 201 - 221 | MULTIPATCH |
| Dalot | 1 | 213 - 216 | MULTIPATCH |
| Fosse terre | 31 | 175 - 258 | MULTIPATCH |
| Fosse terre revetu | 22 | 178 - 288 | MULTIPATCH |
| Talus Terre | 36 | 178 - 284 | MULTIPATCH |
| Voie | 1 | 180 - 290 | MULTIPATCH |
| Descente eau | 3 | 210 - 267 | MULTIPATCH |
| Drainage longitudinal | 10 | 204 - 222 | MULTIPATCH |
| Tunnel | 1 | 249 - 266 | MULTIPATCH |
| Routes | 2 | 201 - 268 | MULTIPATCH |

---

## 2. Naming Convention (Standardized — No French Accents)

To prevent encoding errors across Windows, Python, and JSON, all asset names use **ASCII-only** identifiers:

| Original (French) | Standardized (Code/Data) |
| :--- | :--- |
| Fossé terre | **Fosse terre** |
| Fossé terre revêtu | **Fosse terre revetu** |
| Drainage longitudinal à ciel ouvert | **Drainage longitudinal a ciel ouvert** |

This convention applies to: `z_config.json`, `cross_sections.json`, `hecras_wse_results.json`, `app_main.py`, and all future data files.

---

## 3. Risk & Alert Hierarchy (Multi-disciplinary)

The system follows **Hydraulics → Geotechnics → Operations** logic:

| Alert Level | Trigger Point | Engineering Rationale | Assets Monitored |
| :--- | :--- | :--- | :--- |
| **YELLOW (Monitoring)** | Water > `Buse_max_m` | **Hydraulic Capacity**: Drainage network is 100% full. | Buse, Dalot, Drainage longitudinal |
| **ORANGE (Warning)** | Water > `Talus_mean_m` | **Geotechnical Risk**: Water overflows ditches, soaks embankment. Erosion/instability risk. | Fosse terre, Fosse terre revetu, Talus Terre |
| **RED (Emergency)** | Water > `Voie_min_m` | **Operational Failure**: Water has reached the rail track. Immediate halt required. | Voie (Track) |

### Engineering Precision
- **Conservative Approach**: `Voie_min_m` (absolute lowest point of a track segment) is used for Red Alerts.
- **Segmented Analysis**: Risk is calculated locally per asset/segment, enabling "Hotspot" identification.
- **Safety Fallback**: If `red_z < orange_z` due to min vs mean statistics, system defaults to `orange_z + 0.5m`.

---

## 4. Cross-Section Strategy

### 4.1 Current: DTM Raster Sampling
- Source: `data/staging/terrain/dtm_fixed.tif` (EPSG:2154, ~1GB)
- Method: 24m perpendicular profile sampled at 0.5m intervals from the DTM at each asset's midpoint.
- Result: **73 of 103 assets** have cross-sections. The remaining 30 are outside DTM spatial coverage.
- Storage: `data/processed/cross_sections.json`

### 4.2 Next Step: 3D BIM-Based Sections (Planned)
- Source: `data/raw/maquette_3d/` (MULTIPATCH shapefiles with full Z vertices)
- Advantage: **100% asset coverage** — every asset has its own 3D engineered geometry.
- Advantage: More precise than DTM raster — represents as-built/designed shape of ditches, culverts, embankments.
- Requires: `pyshp` library (installed) to read MULTIPATCH, then slice perpendicular profiles from vertex data.
- **Blocker**: Must verify the vertical datum of 3D MULTIPATCH vs DTM before applying to Dashboard.

### 4.3 Structural Profile Logic (Synthetic/BIM)
- **Type A (Concave/Ditch)**: For `Buse`, `Dalot`, `Fosse`. The center of the profile is the lowest point (the ditch bottom).
- **Type B (Convex/Embankment)**: For `Voie`, `Talus`. The center of the profile is the highest point (the track or top of embankment).

### 4.4 Bridge Logic (Pont Rail)
- **Longitudinal Profiling**: Bridges use a sampling vector **parallel (0°)** to the track, extending beyond the bridge to capture the approaches (Talus).
- **Clearance Analysis**: The visual profile acts as a "sandwich": the top line is the bridge deck (Asset Z), the bottom line is the ground/riverbed (DTM), and the space between is the clearance for water (WSE).

---

## 5. HEC-RAS Integration

- **Connection Method**: COM API via `pywin32` (ProgID: `RAS67.HECRASController`).
- **HEC-RAS Version**: 6.7 Beta 5 Development (installed at `C:\Program Files (x86)\HEC\HEC-RAS\6.7 Beta 5\`).
- **Bridge Module**: `src/engine/hecras_bridge.py` — Opens `.prj` projects, runs simulations, extracts WSE profiles.
- **Status**: Connection verified ✅. Awaiting `.prj` project file for full simulation.
- **Workflow**: Dashboard button → inject rainfall → HEC-RAS compute → extract WSE → update charts.

### Current Demo Mode (Synthetic WSE)
Until a real HEC-RAS `.prj` is available, the system uses a **synthetic WSE simulation** based on:
- Rational Method + Manning's approximation
- Elevation-dependent inflow (valley accumulation effect)
- Data files: `data/raw/rainfall_Ligne_400.csv` (48h Cevenol scenario), `data/processed/hecras_wse_results.json`

---

## 6. Hydrological Forecasting & SWI Memory

- **Rolling Window**: 30 Days History (Observed Rain) + 48 Hours Forecast (Predicted Rain).
- **SWI as Initial Condition**: Soil Water Index calculated using "Leaky Bucket" model (capacity: 150mm, decay: 0.02/h).
- **T=0 Hand-off**: At forecast start, current SWI is passed to HEC-RAS as initial saturation ("Hotstart").
- **Simulation Mode**: Single 48-hour "Batch Run" when new forecast data is ingested.
- **Data**: `data/processed/swi_results.csv` contains SWI, runoff coefficient, and active runoff per timestep.

---

## 7. Dashboard Architecture

- **Framework**: Streamlit (`src/dashboard/app_main.py`)
- **Map**: Pydeck with OpenStreetMap base + GeoJSON infrastructure overlays
- **7 Asset Types Monitored**: Buse, Dalot, Fosse terre, Fosse terre revetu, Talus Terre, Voie, Pont Rail
- **5 Infrastructure Line Layers**: Voie (red), Talus (brown), Fosse terre revetu (blue), Fosse terre (blue), Drainage longitudinal (cyan)
- **Time Slider**: 0-47h forecast timeline driving all charts and map colors
- **Charts**: WSE time-series with threshold lines + Contextual Cross-Section with water fill

### 7.1 Hotspot Auto-Focus
- The dashboard automatically selects and displays the asset with the **highest risk percentage** for the currently selected hour on the timeline.
- Because of this, the cross-section view may visually "jump" between different assets (e.g., from a DTM-based profile to a Synthetic profile) as the user scrubs through time and the primary hotspot shifts.

---

## 8. Integrated Platform Model (Future)

To eliminate isolated, disconnected synthetic profiles, the system will move towards an **Integrated Platform Model**:
- **Goal**: Render a complete infrastructure cross-section: `[Fosse L] -- [Talus L] -- [VOIE] -- [Talus R] -- [Fosse R]`.
- **Method**: Utilize the spatial neighbors mapped in `z_config.json` (`nearest_talus`, `nearest_voie`) to "stitch" together a full 30m wide profile. The UI will then highlight the specific asset being analyzed within this continuous chain.

---

## 9. Key Data Files

| File | Purpose |
| :--- | :--- |
| `data/processed/z_config.json` | 103 assets with Yellow/Orange/Red Z thresholds |
| `data/processed/cross_sections.json` | 73 DTM-based terrain profiles |
| `data/processed/hecras_wse_results.json` | 103 synthetic WSE time-series (48h) |
| `data/processed/swi_results.csv` | SWI + runoff per timestep |
| `data/raw/rainfall_Ligne_400.csv` | 48h Cevenol storm scenario (peak 40.9 mm/h at T+15h) |
| `src/engine/hecras_bridge.py` | Python-HEC-RAS COM connector |
| `src/dashboard/app_main.py` | Main Dashboard application |
