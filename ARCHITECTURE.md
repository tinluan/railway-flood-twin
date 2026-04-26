# Railway Flood-Risk Digital Twin — ARCHITECTURE

**Project**: SNCF Ligne_400 (Himalayas Corridor) Flood Risk Demonstrator
**Version**: v0.3.0
**Last Updated**: 2026-04-26

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
| 3D MULTIPATCH (`maquette_3d/`) | ~175-290m | **None (pending verification)** | Z already near NGF |
| DTM raster (`dtm_fixed.tif`) | ~200-250m | Reference datum | EPSG:2154 + NGF |

> **CRITICAL**: Never apply the +107m offset to 3D BIM assets. Datum verification
> required first (compare 3D Z vs DTM at the same X,Y point).

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
- Method: Sample a 24m perpendicular line at 0.5m intervals from the asset centroid.
- Results stored in: `data/processed/cross_sections.json`

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

### 4.4 Hotspot Auto-Focus (Known UI Behavior)
The dashboard auto-selects the highest-risk asset at each timestep. This causes the
cross-section view to "jump" assets as the timeline moves. Fix: implement UI Lock (Task 4).

---

## 5. Hydrological Model (SWI + Synthetic WSE)

- **SWI Leaky Bucket**: capacity=150mm, decay_rate=0.02/h
- **WSE Formula**: Rational Method + Manning's approximation + elevation-dependent
  valley accumulation effect.
- **Data**: `data/raw/rainfall_Ligne_400.csv` — 48h Cevenol storm (peak 40.9 mm/h at T+15h)
- **Output**: `data/processed/hecras_wse_results.json` — 103 assets × 48 timesteps

---

## 6. HEC-RAS Integration (Blocked — waiting for .prj file)

- **Method**: COM API via `pywin32`, ProgID: `RAS67.HECRASController`
- **Bridge**: `src/engine/hecras_bridge.py`
- **Status**: COM connection verified. Awaiting `.prj` project file from team.
- **Workflow**: Rainfall inject → HEC-RAS compute → WSE extract → chart update.

---

## 7. Dashboard Architecture

- **Framework**: Streamlit (`src/dashboard/app_main.py`)
- **Map**: PyDeck with OpenStreetMap base tiles + GeoJSON infrastructure layers
- **Assets Monitored**: 7 types, 103 total
- **Infrastructure Layers**: Voie, Talus, Fosse terre, Fosse revetu, Drainage
- **Charts**: WSE 48h time-series + Contextual Cross-Section with water fill

### To Start the Dashboard
```powershell
.\.conda\python.exe -m streamlit run src/dashboard/app_main.py
```

---

## 8. Key Data Files

| File | Description |
|------|-------------|
| `data/processed/z_config.json` | 103 assets with Yellow/Orange/Red Z thresholds |
| `data/processed/cross_sections.json` | 73 DTM terrain profiles |
| `data/processed/hecras_wse_results.json` | Synthetic 48h WSE per asset |
| `data/processed/swi_results.csv` | SWI + runoff coefficient per hour |
| `data/raw/rainfall_Ligne_400.csv` | 48h Cevenol storm input |
| `data/raw/maquette_3d/` | 3D BIM MULTIPATCH shapefiles (all assets) |
| `src/dashboard/app_main.py` | Main Streamlit dashboard |
| `src/engine/hecras_bridge.py` | HEC-RAS COM API connector |
| `src/engine/synthetic_inundation.py` | Bathtub flood polygon generator (TODO) |
