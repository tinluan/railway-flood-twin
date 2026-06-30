# Implementation Plan: Future Features from new_feature.md

This plan breaks down all 7 future features into implementable tasks, recommends the optimal AI model for each, and specifies exactly which files to have open to prevent redundant token re-reading.

---

## Feature Inventory (from [new_feature.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/new_feature.md))

| # | Feature | Priority | Complexity |
|:--|:--------|:---------|:-----------|
| F1 | Dual-Mode Dashboard (Live + Showcase) | 🔴 High | Medium |
| F2 | Play Button — Timeline Animation | 🔴 High | Low |
| F3 | Accumulated Rainfall Graph | 🟡 Medium | Low |
| F4 | HEC-RAS 2D Flow Mapping Overlay | ✅ Completed | High |
| F5 | Group-Based Asset & Alert Management | 🟡 Medium | High |
| F6 | DTM & Asset Database Sync | 🟢 Low (Manual) | Medium |
| F7 | Satellite Remote Sensing SWI Validation | 🟢 Low (Thesis Future) | High |
| F8 | ML Hydraulic Emulator | 🟢 Low (Thesis Future) | Very High |

> [!IMPORTANT]
> **Recommended execution order**: F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8
> Features F1–F3 are dashboard UI changes that can be completed quickly and give immediate visual impact. F4–F5 require deeper GIS/engine work. F6–F8 are longer-term thesis improvements.

---

## Feature F1: Dual-Mode Dashboard (Live + Showcase)

### Goal
Replace the current multi-option sidebar with a clean 2-mode radio: **Live Monitoring** vs **Historical Showcase (Sept 2025)**.

### Tasks

| Task | Model | Cost | Details |
|:-----|:------|:-----|:--------|
| F1.1 Refactor sidebar mode selector | **Gemini Flash** | 💰 | Replace `st.sidebar.selectbox("Mode", ...)` and `st.sidebar.selectbox("Simulation Plan", ...)` with a single `st.sidebar.radio` |
| F1.2 Add conditional plan/data routing | **Gemini Flash** | 💰 | Route `load_wse_results()` and rainfall source based on mode |
| F1.3 Adjust timeline slider range | **Gemini Flash** | 💰 | 21h / 127 steps for Showcase, 48h for Live |
| F1.4 Test both modes | **Gemini Flash** | 💰 | Run dashboard, verify switching works |

### Files to have open
Only open **one file** at a time:
- `src/dashboard/app_main.py` — this is the only file being edited

### Context to provide in prompt
> *"Refactor the sidebar in app_main.py (lines 166–205) to use a radio button with two modes: 'Live Monitoring' and 'Historical Showcase (Sept 2025)'. In Showcase mode, lock the plan to P02 and load hecras_wse_p02_dashboard.json. Use the code snippets from docs/new_feature.md Section F7 (Dual-Mode Dashboard)."*

---

## Feature F2: Play Button — Timeline Animation

### Goal
Add a ▶ Play / ⏸ Pause toggle that auto-advances the timeline slider.

### Tasks

| Task | Model | Cost | Details |
|:-----|:------|:-----|:--------|
| F2.1 Add play toggle + speed slider | **Gemini Flash** | 💰 | Place above or beside the existing timeline slider |
| F2.2 Implement auto-advance with `st.rerun()` | **Gemini Flash** | 💰 | Use `time.sleep()` + `st.session_state` increment pattern |
| F2.3 Add loop checkbox | **Gemini Flash** | 💰 | Optional: reset to 0 at end |
| F2.4 Test animation smoothness | Manual | Free | Run dashboard, click Play, watch it animate |

### Files to have open
- `src/dashboard/app_main.py` only

### Context to provide in prompt
> *"Add a Play/Pause animation button to app_main.py. The play toggle should auto-advance the timeline slider using st.session_state and st.rerun(). Use the code from docs/new_feature.md Section 4 (Play Button)."*

---

## Feature F3: Accumulated Rainfall Graph

### Goal
Add a dual-axis chart showing hourly rainfall bars + cumulative rainfall line.

### Tasks

| Task | Model | Cost | Details |
|:-----|:------|:-----|:--------|
| F3.1 Add `calculate_accumulated_rainfall()` helper | **Gemini Flash** | 💰 | Can be placed in `app_main.py` or a utility file |
| F3.2 Add Plotly dual-axis chart | **Gemini Flash** | 💰 | Bar chart (intensity) + Line (accumulated) |
| F3.3 Add "Total Storm Rainfall" metric box | **Gemini Flash** | 💰 | `st.metric()` at top of hydrology section |
| F3.4 Test with demo and live data | Manual | Free | Verify both data sources render correctly |

### Files to have open
- `src/dashboard/app_main.py` only

### Context to provide in prompt
> *"Add an accumulated rainfall graph to the dashboard. Use the Plotly dual-axis code from docs/new_feature.md (Accumulated Rainfall Graph, Section 3). Place it in the hydrology section of app_main.py."*

---

## Feature F4: HEC-RAS 2D Flow Mapping Overlay (HEC-RAS Mapper Style)

### Goal
Replicate the exact look of HEC-RAS Mapper on the web dashboard: hillshade terrain basemap + continuous green→yellow→red color ramp overlay on flooded HEC-RAS 2D cells + crisp infrastructure vector lines + inline color legend. Two rendering modes are provided: a fast **Point Cloud** baseline and a smooth **Raster BitmapLayer** target.

### Progress
| Task | Status |
|:-----|:-------|
| F4.1 `extract_downsampled_flow_data()` | ✅ Done |
| F4.2 ScatterplotLayer point cloud with depth coloring | ✅ Done |
| F4.3 Sidebar layer selector (Depth / WSE / Velocity) + Hillshade basemap toggle | ✅ Done |
| F4.4 Performance test | ✅ Done |
| F4.5 *(Optional)* GDAL raster tiles | ✅ Done |
| F4.6 BitmapLayer raster mode (HEC-RAS Mapper style) | ✅ Done |
| F4.7 Inline CSS color legend panel | ✅ Done |

### Tasks

| Task | Model | Cost | Details |
|:-----|:------|:-----|:--------|
| F4.1 Write `extract_downsampled_flow_data()` | **Claude Sonnet** | ✅ Done | Reads HDF5, filters wet cells, reprojects L93→WGS84, returns `depth_m`, `wse_m`, `velocity_ms` per point |
| F4.2 ScatterplotLayer point cloud with depth coloring | **Gemini Flash** | ✅ Done | WebGL layer stack: Basemap → GeoJson infra → ScatterplotLayer water → Risk markers; discrete color buckets per variable |
| F4.3 Sidebar layer selector + basemap toggle | **Gemini Flash** | ✅ Done | `st.sidebar.selectbox("HEC-RAS 2D Flow Overlay", ["Water Depth", "WSE", "Velocity", "None"])` + `st.sidebar.selectbox("Map Basemap Style", ["Terrain Hillshade", "CartoDB Light"])` |
| F4.4 Performance test with 10K–50K points | **Gemini Flash** | ✅ Done | Adjust `max_cells` parameter if laggy |
| F4.5 *(Optional)* GDAL raster tile server | **Claude Opus** | ✅ Done | Only if point cloud approach proves too slow/sparse |
| F4.6 BitmapLayer raster mode ⭐ | **Claude Sonnet** | ✅ Done | Rasterize HDF5 depth/wse/velocity grid to in-memory RGBA PNG via `numpy`+`PIL`; serve to PyDeck `BitmapLayer` stretched over model bounding box (lon_min=4.879, lat_min=44.629, lon_max=4.942, lat_max=44.674); continuous color ramp: green→yellow→red normalized to per-timestep min/max |
| F4.7 Inline CSS color legend panel | **Gemini Flash** | ✅ Done | `st.markdown()` with CSS `linear-gradient` bar showing variable min/max values and color stops below the map |

### Visual Target (Mode B: BitmapLayer)
- **Hillshade basemap**: `https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}`
- **Continuous ramp (WSE)**: `#00c864` (low) → `#ffd700` → `#ff8c00` → `#c80000` (high)
- **Continuous ramp (Depth)**: `#add8e6` (shallow) → `#4169e1` (medium) → `#4b0082` (deep)
- **Continuous ramp (Velocity)**: `#32cd32` (slow) → `#ffa500` → `#ff4500` → `#9400d3` (fast)
- **Alpha channel**: 0 for dry cells (depth ≤ 0.02m), 180 for flooded cells
- **Legend**: inline HTML gradient bar below map with min/max labels

### Files to have open
- For F4.1: `src/engine/hecras_hdf5_reader.py` only
- For F4.2–F4.3: `src/dashboard/app_main.py` only
- For F4.6: `src/engine/hecras_hdf5_reader.py` + `src/dashboard/app_main.py`

### Context to provide in prompt (F4.6)
> *"In hecras_hdf5_reader.py, add `rasterize_flow_to_bitmap(hdf5_path, timestep_idx, variable, grid_resolution=5.0)` which: (1) loads the selected variable array and Lambert93 cell coordinates, (2) bins cells onto a regular 5m grid using scipy.stats.binned_statistic_2d or numpy histogram2d, (3) applies the continuous color ramp [green→yellow→red] normalized to the timestep min/max, (4) sets alpha=0 for dry cells, (5) saves as base64-encoded PNG and returns (img_b64, bounds_wgs84)."*

---

## Feature F5: Group-Based Asset & Alert Management

### Goal
Migrate from flat spatial-proximity asset mapping to unified Track-Talus physical groups.

### Tasks

| Task | Model | Cost | Details |
|:-----|:------|:-----|:--------|
| F5.1 Design new `z_config.json` grouped schema | **Claude Sonnet** | ✅ Done | `z_config_grouped.json` created: 21 sections, each with `track_talus` block + `drainage_assets` list + `bridges` list |
| F5.2 Write migration script (old → new format) | **Claude Sonnet** | ✅ Done | `src/transform/migrate_z_config_grouped.py` — produces 21 sections, 61 drainage, 4 bridges |
| F5.3 Update `alert_dispatcher.py` to use groups | **Claude Sonnet** | ✅ Done | Added `evaluate_group()`, `evaluate_all_groups()`, `summarise_system()` with worst-case roll-up; legacy API fully preserved |
| F5.4 Update dashboard alert table for groups | **Gemini Flash** | 💰 | UI formatting change |
| F5.5 Test alert logic with Sept 2025 scenario | **Gemini Flash** | 💰 | Run pipeline, verify alerts match expectations |

### Files to have open
- For F5.1–F5.2: `data/processed/z_config.json` only
- For F5.3: `src/engine/alert_dispatcher.py` only
- For F5.4: `src/dashboard/app_main.py` only

### Context to provide in prompt (F5.1)
> *"Redesign z_config.json to use the grouped schema from docs/new_feature.md (Group-Based Asset & Alert Management, Section 3). Each group contains a track_talus block and a drainage_assets array. The current z_config.json is at data/processed/z_config.json."*

---

## Feature F6: DTM & Asset Database Sync

> [!NOTE]
> This feature is mostly **manual file operations** (copying files, running existing scripts). AI assistance is minimal.

### Tasks

| Task | Model | Cost | Details |
|:-----|:------|:-----|:--------|
| F6.1 Replace staging DTM with new 1.24GB DTM | Manual | Free | File copy |
| F6.2 Update earthen ditch GPKG (31→41 features) | **Gemini Flash** | 💰 | Run the conversion script from new_feature.md |
| F6.3 Rename 3D BIM folders per mapping sheet | Manual | Free | Follow the table in new_feature.md |
| F6.4 Re-run `segment_voie.py` | **Gemini Flash** | 💰 | Execute and verify output |

---

## Features F7 & F8: Satellite Validation + ML Emulator

> [!TIP]
> These are **thesis future work recommendations**. Do not implement now unless you have extra time and credits. If you do implement them, use **Claude Sonnet** for the Python scientific code (scipy, scikit-learn) and **Gemini Flash** for testing/verification.

---

## Token Cost Management Strategy

### Rule 1: Close unrelated tabs before each task
Before starting any task, close all editor tabs except the **one file you are editing**. This prevents the AI from re-reading 5–6 large files as context on every prompt.

| Task Target | Keep Open | Close Everything Else |
|:------------|:----------|:---------------------|
| Dashboard UI (F1, F2, F3) | `app_main.py` | ✅ Close all docs, engine files |
| Engine/HDF5 (F4.1) | `hecras_hdf5_reader.py` | ✅ Close dashboard, docs |
| Alert logic (F5.3) | `alert_dispatcher.py` | ✅ Close dashboard, docs |
| Config/Schema (F5.1) | `z_config.json` | ✅ Close everything else |

### Rule 2: Reference new_feature.md by section name, don't paste code
Instead of pasting code blocks from `new_feature.md` into your prompt (which costs input tokens), tell the AI:
> *"Use the implementation from docs/new_feature.md, Section [X]"*

The AI will read just that section from the file, which is cheaper than you pasting it.

### Rule 3: Use the cheapest model that works

| Situation | Model | Why |
|:----------|:------|:----|
| Simple UI edits, adding widgets, formatting | **Gemini Flash (Low)** | Cheapest. Handles Streamlit code easily. |
| Standard Python logic, DataFrame ops, Plotly charts | **Gemini Flash (Medium)** | Slightly smarter, still very cheap. |
| GIS/coordinate math, schema design, multi-file refactors | **Claude Sonnet** | Better at reasoning across complex logic. |
| Debugging stubborn failures after 2+ attempts | **Claude Opus** | Last resort. Use only when others fail. |

### Rule 4: Batch related changes in one prompt
Instead of 3 separate prompts:
- ❌ "Add the play button" → "Now add the speed slider" → "Now add the loop checkbox"

Do one prompt:
- ✅ "Add the play button with speed slider and loop checkbox to app_main.py, using the code from new_feature.md Section 4."

This saves 2 round-trips of context re-reading.

### Rule 5: Use `/learn` after solving complex setups
If you solve a tricky configuration (like HEC-RAS COM connection, pyproj setup, or GDAL tiling), use the `/learn` command so the AI remembers the solution for future sessions without re-discovering it.

---

## Estimated Credit Budget

| Feature | # of Prompts | Model | Est. Cost |
|:--------|:-------------|:------|:----------|
| F1: Dual-Mode Dashboard | 2–3 | Gemini Flash | 💰 Very Low |
| F2: Play Button | 1–2 | Gemini Flash | 💰 Very Low |
| F3: Accumulated Rainfall | 2–3 | Gemini Flash | 💰 Very Low |
| F4: Flow Map Overlay | 3–5 | Sonnet + Flash | 💰💰 Medium |
| F5: Group-Based Alerts | 4–6 | Sonnet + Flash | 💰💰 Medium |
| F6: DTM/Asset Sync | 1–2 | Flash + Manual | 💰 Very Low |
| **Total for F1–F6** | **~15–20 prompts** | Mixed | **~$5–10 USD equiv.** |
