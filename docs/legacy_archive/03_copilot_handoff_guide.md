# AI Handoff & Copilot Guide

This document is designed to be read by **human developers** and their **AI Assistants** (like GitHub Copilot or Claude in VS Code) to ensure seamless continuation of the Railway Flood-Risk Digital Twin project.

## 🤖 System Prompt for AI Assistant
If you are an AI assistant reading this file to help your human user, please adopt the following context:

**Role**: You are a senior Python/Streamlit engineer and GIS specialist working on an SNCF standard Railway Flood-Risk Digital Twin.
**Core Principle**: Maintain the "Antigravity Protocol" standards (found in `docs/antigravity_rules.md`).
**Current Data State**: We use standardized, ASCII-only keys for all assets (e.g., `Fosse_0` instead of `Fossé_0`). French accents must be removed in code.
**Coordinate System**: All geospatial operations must use `EPSG:2154` (Lambert 93) internally, converting to `EPSG:4326` (WGS84) only right before sending to the Streamlit PyDeck frontend.

---

## 🚀 Priority Tasks for the Team

The lead developer has prepared three specific architectural tasks for you to implement. The pseudo-code and requirements have already been injected into the respective python files. Your job is to fill in the actual Python implementation using libraries like `geopandas`, `rasterio`, and `plotly`.

### Task 1: Synthetic 2D Inundation Map ("Bathtub" Model)
**File**: `src/engine/synthetic_inundation.py` (New File)
**Goal**: Create a fake "HEC-RAS 2D output" by comparing the DTM (`data/staging/terrain/dtm_fixed.tif`) against the synthetic 1D WSE values (`data/processed/hecras_wse_results.json`). 
**Expected Output**: A set of GeoJSON files (or a single dynamic one) containing a polygon representing the flooded area (where Ground Z < Water Z). This will be displayed on the PyDeck map in the dashboard.

### Task 2: Stitched Synthetic Profile (Integrated Platform)
**File**: `src/dashboard/app_main.py`
**Goal**: Currently, the dashboard draws a "synthetic geometric profile" for assets outside DTM coverage, but it only draws *one* asset in isolation. We want to stitch them together into an "Integrated Platform" (`Fosse L` -> `Talus L` -> `Voie` -> `Talus R` -> `Fosse R`).
**Logic Needed**: Look up the `nearest_talus` and `nearest_voie` values in `data/processed/z_config.json` to build a 30m wide composite cross-section chart.

### Task 3: Vulnerability Target Selection (Fixing the Map Dot)
**File**: `src/dashboard/app_main.py`
**Goal**: Currently, the dashboard plots large assets like `Voie_0` at their geometric centroid. If the flood happens at the absolute lowest point of the track, the map point appears wrong. 
**Logic Needed**: For the `Voie` asset, replace its generic `lat`/`lon` in the dashboard with the specific `lat`/`lon` of its absolute lowest elevation point (the "Vulnerability Target" where `Z = red_z`).

---

## 🛠️ Getting Started for the Teammate

1. **Read the Blueprints**: Open `docs/brainstorming/alignment_and_risk_logic_summary.md` to understand the engineering logic behind the Yellow/Orange/Red risk thresholds and the cross-section strategies.
2. **Open the Python Files**: Open `src/engine/synthetic_inundation.py` and `src/dashboard/app_main.py`. You will see `TODO` blocks with detailed pseudo-code.
3. **Trigger Copilot**: Place your cursor inside the `TODO` blocks and use your AI assistant (e.g., `Cmd+I` in VS Code) and type: "Implement the pseudo-code described in this docstring."

Good luck, and maintain the SNCF engineering standard!
