# Railway Flood-Risk Digital Twin — Official Team Quickstart
<!-- AI_READABLE: YES — This file is the first document an AI assistant should read when initializing this project. -->

**Project**: SNCF Ligne_400 (Himalayas Corridor) Flood Risk Demonstrator
**Version**: v0.4.0-demo
**Target Audience**: New human teammates AND AI coding assistants (Antigravity, GitHub Copilot)
**Canonical Repo**: https://github.com/tinluan/railway-flood-twin

> **AI ASSISTANT — READ THIS FIRST**: If you are Antigravity, GitHub Copilot, or any other AI
> coding assistant, treat this file as your boot sequence. Execute each numbered step in order.
> After completing setup, read `ARCHITECTURE.md` and `.github/copilot-instructions.md` for all
> engineering rules and the current sprint task list.

---

## Prerequisites

Before you begin, ensure the following tools are installed on your machine.

| Tool | Version | Why It Is Needed | Download |
|------|---------|-----------------|----------|
| **Git** | ≥ 2.40 | Clone the repository | https://git-scm.com |
| **Anaconda or Miniconda** | any | `setup_team.ps1` creates the `.conda` Python 3.9 environment | https://www.anaconda.com/download |
| **VS Code** | ≥ 1.85 | IDE with Copilot + Antigravity support | https://code.visualstudio.com |
| **Google Drive Desktop** | latest | Mounts the shared `G:\Shared drives\DigiTwin\` data folder | https://www.google.com/drive/download |

> **⚠ IMPORTANT — Do NOT clone into a Google Drive folder.**
> Google Drive's real-time sync locks files during analysis and causes silent I/O errors.
> Clone to a local drive (e.g. `C:\Master_Project\`) only.

---

## Step 0 — Get Repository Access (Action for Tin)

- [ ] Ask **Tin** to invite you as a **Collaborator** via:
      `https://github.com/tinluan/railway-flood-twin/settings/access`
- [ ] Confirm that Google Drive access to `DigiTwin/railway-flood-twin/data/` has been shared with
      your Google account.

---

## Step 1 — Clone the Repository

Open a **PowerShell** or **Git Bash** terminal and run:

```powershell
# Create a local working folder (NOT inside Google Drive)
mkdir C:\Master_Project
cd C:\Master_Project

# Clone the repo
git clone https://github.com/tinluan/railway-flood-twin.git
cd railway-flood-twin
```

Expected result: A `railway-flood-twin\` folder with `README.md`, `ARCHITECTURE.md`,
`setup_team.ps1`, `requirements.txt`, and the full `src/` tree visible.

---

## Step 2 — Run the Automated Setup Script

This single script creates your isolated Python 3.9 environment, installs all GIS and
dashboard dependencies, and writes your `.env` configuration file.

```powershell
# Run from inside the railway-flood-twin directory
./setup_team.ps1
```

**What the script does (4 phases):**

| Phase | Action |
|-------|--------|
| `[1/4]` | Checks that Conda is installed (`Anaconda3` or `Miniconda3`). **Fails fast** if missing. |
| `[2/4]` | Creates a local `.conda/` Python 3.9 environment (isolated, zero global footprint). |
| `[3/4]` | Installs `requirements.txt` (pandas, geopandas, streamlit, fastapi, pytest, pywin32, …). |
| `[4/4]` | Creates your `.env` file and runs the health check (`src/utils/check_health.py`). |

**During Step [4/4] the script will ask two questions:**

```
Enter Supabase DATABASE_URL (or press Enter to skip):
> postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

Enter path to your shared Data folder:
> G:\Shared drives\DigiTwin\railway-flood-twin\data
```

- Get the `DATABASE_URL` from Tin (Supabase project credentials).
- The `DATA folder` path is where Google Drive Desktop mounts the shared drive.
  Common Windows path: `G:\Shared drives\DigiTwin\railway-flood-twin\data`

If the script prints `[🚀 NEXT STEPS]` at the end, setup was successful.

---

## Step 3 — Select the Python Interpreter in VS Code

1. Open the project folder in VS Code: `code .` (or **File → Open Folder**)
2. Press `Ctrl + Shift + P` → type **`Python: Select Interpreter`**
3. Choose the interpreter inside `./.conda/` — it will look like:
   `.\.conda\python.exe` (Python 3.9)

> **Note for AI assistants**: The correct Python executable for all terminal commands is
> `.\.conda\python.exe` (Windows) or `./.conda/bin/python` (Linux/Mac).

---

## Step 4 — Verify the Installation (Health Check)

Run the built-in health check to confirm the environment is correctly configured:

```powershell
$env:PYTHONPATH = "."
.\.conda\python.exe src/utils/check_health.py
```

Expected output: All green `[OK]` lines confirming that `DATA_ROOT`, `DATABASE_URL`,
processed data files, and key Python imports are all reachable.

**Manual verification (if health check is unavailable):**

```powershell
# 1. Check that processed data files exist
Test-Path "data/processed/z_config.json"            # → True
Test-Path "data/processed/hecras_wse_results.json"  # → True
Test-Path "data/processed/swi_results.csv"          # → True

# 2. Check that the environment can import the key libraries
.\.conda\python.exe -c "import geopandas, streamlit, fastapi; print('OK')"
```

---

## Step 5 — Start the Dashboard

```powershell
.\.conda\python.exe -m streamlit run src/dashboard/app_main.py
```

- Opens automatically at `http://localhost:8501`
- The dashboard shows the **Ligne_400 map**, **48h WSE time-slider**, **CAP alert colors**
  (Green / Yellow / Orange / Red), and the **cross-section chart** for any selected asset.

---

## Step 6 — Start the API Server (Optional)

```powershell
.\.conda\python.exe -m uvicorn src.api.main:app --reload --port 8000
```

- Swagger UI available at `http://localhost:8000/docs`
- Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/assets` | Full static infrastructure config (120+ assets) |
| `GET` | `/api/v1/alerts/current` | Real-time RAMS verdicts + hotspot auto-focus |
| `GET` | `/api/v1/hydrology/swi` | SWI values + synthetic flood polygons |
| `POST` | `/api/v1/engine/simulate` | Run a custom rainfall array simulation |

**Run the full API test suite:**

```powershell
$env:PYTHONPATH = "."
.\.conda\python.exe -m pytest tests/test_api.py -v
```

Expected: `23 passed` ✅

---

## Step 7 — Load AI Context (GitHub Copilot / Antigravity)

### For GitHub Copilot (VS Code)
`.github/copilot-instructions.md` is **auto-loaded** by VS Code Copilot when you open this
project. No action required — Copilot is already briefed.

### For Antigravity (Google DeepMind AI)
Paste the following boot prompt into Antigravity to fully initialize it on this project:

```
I am working on the Railway Flood-Risk Digital Twin project.
Repository: C:\Master_Project\railway-flood-twin

Please read the following files in this order to initialize yourself:
1. ARCHITECTURE.md            — Engineering rules, formulas, alert hierarchy, data models
2. .github/copilot-instructions.md — Governance rules, coding style, current sprint tasks
3. STATUS.md                  — Live task tracker: what is done, in progress, and blocked
4. src/utils/paths.py         — How all file paths are resolved (never hardcode paths)

After reading, confirm you understand:
- The 4-layer architecture (Data → Bridge → Simulation → Alert)
- The ASCII-only naming convention for all asset keys
- The NO HARDCODED PATHS rule (always use paths.py)
- The current open sprint tasks (Tasks 5–8 in STATUS.md)

You are now ready to assist. What should I work on first?
```

---

## Project Structure Overview

```
railway-flood-twin/
│
├── README.md                    # Human quickstart (VS Code focus)
├── ARCHITECTURE.md              # ⭐ Engineering bible — read before writing code
├── STATUS.md                    # Live task tracker
├── .github/
│   └── copilot-instructions.md  # AI context (auto-loaded by VS Code Copilot)
│
├── setup_team.ps1               # Automated onboarding script
├── requirements.txt             # All Python dependencies
├── .env.example                 # Template — copy to .env and fill in values
├── .env                         # Local secrets — DO NOT commit to Git
│
├── src/
│   ├── dashboard/app_main.py    # 🖥  Streamlit Digital Twin UI
│   ├── api/main.py              # 🌐 FastAPI REST API
│   ├── engine/                  # ⚙️  Risk computation scripts
│   │   ├── swi_calculator.py    # SWI recursive filter + sigmoid runoff
│   │   ├── fragility_curves.py  # Log-normal ballast scour P(failure)
│   │   ├── alert_dispatcher.py  # RAMS-compliant alert generator
│   │   ├── synthetic_inundation.py  # Flood polygon generator (DONE)
│   │   └── hecras_bridge.py     # HEC-RAS 6.7 COM connector
│   └── utils/
│       ├── paths.py             # Canonical path resolver (use this everywhere)
│       └── check_health.py      # Environment health check
│
├── data/
│   ├── raw/                     # 🔒 Read-only source files
│   ├── staging/gis/             # CRS-fixed GeoPackages (EPSG:2154)
│   ├── staging/terrain/         # DTM raster: dtm_fixed.tif (~1GB, shared drive)
│   └── processed/               # ✅ Computed outputs (committed to repo)
│       ├── z_config.json        # 120+ assets with Yellow/Orange/Red Z thresholds
│       ├── hecras_wse_results.json  # Synthetic 48h WSE per asset
│       ├── cross_sections.json  # 73 DTM terrain profiles (60m E-W, 1m res)
│       ├── synthetic_flood_timesteps.json  # 48 GeoJSON flood polygons
│       └── swi_results.csv      # SWI + runoff coefficient per hour
│
└── tests/
    └── test_api.py              # API test suite (23 tests)
```

---

## Core Engineering Rules (Must Know)

These rules are enforced in all code reviews. Full detail in `ARCHITECTURE.md`.

| Rule | What It Means |
|------|--------------|
| **No hardcoded paths** | Always import from `src/utils/paths.py`. Never write `C:/Users/...` in code. |
| **ASCII-only asset keys** | Use `Fosse terre`, not `Fossé terre`. French accents cause silent Windows bugs. |
| **EPSG:2154 internally** | All GIS processing uses Lambert 93. Convert to EPSG:4326 only at display time. |
| **No direct push to `main`** | Always work on a feature branch. |
| **`logging`, not `print()`** | Use Python `logging` module in all engine scripts. |
| **Update STATUS.md** | After completing any task, check off the checkbox in `STATUS.md`. |
| **Run health check** | Run `python src/utils/check_health.py` after any environment change. |

---

## Scientific Model Summary

The system implements a **4-layer pipeline** running on a 15-minute operational cycle:

```
Layer 1: Data Sources     → BIM (IFC/Civil3D), GIS (DTM/LiDAR), Météo-France API
Layer 2: Bridge           → Mirror DB, Coordinate Projection (EPSG:2154), SWI Calculator
Layer 3: Simulation       → SWI Leaky Bucket + HEC-RAS 2D Hydraulics + HDF5 Processing
Layer 4: Alert            → Fragility Curves + WSE vs Z_ballast + HMI Dashboard
```

**Key formula — WSE Verdict:**
```
WSE = Z_terrain + Depth_water
WSE > Z_ballast  →  UNSAFE (Red Alert — halt trains)
WSE < Z_ballast  →  SAFE   (Green)
```

**Alert thresholds:**
| CAP Color | Trigger | Assets Affected |
|-----------|---------|-----------------|
| 🟡 YELLOW | WSE > `yellow_z_m` (culvert capacity) | Buse, Dalot, Drainage |
| 🟠 ORANGE | WSE > `orange_z_m` (embankment saturation) | Fosse, Talus |
| 🔴 RED | WSE > `red_z_m` (track elevation minimum) | Voie (track) |

Full scientific formulas (SWI Leaky Bucket, Sigmoid Runoff, Fragility Curves) are in `ARCHITECTURE.md` Section 5.

---

## Open Sprint Tasks (v0.4)

Pick any of these tasks to contribute. Each is self-contained.

| Task | File | Status | Description |
|------|------|--------|-------------|
| **Task 5** | `src/dashboard/app_main.py` | 🔲 Open | Bridge longitudinal view — rotate DTM sampling to parallel for Pont Rail assets |
| **Task 6** | `data/raw/maquette_3d/` | 🔲 Open | Verify 3D MULTIPATCH datum: compare Z from `Voie.shp` vs DTM at same X,Y |
| **Task 7** | `data/processed/z_config.json` | 🔲 Open | Remap stale `nearest_voie: Voie_0` references to nearest `Voie_seg_XX` |
| **Task 8** | `src/engine/*.py` | 🔲 Open | Migrate all `print()` calls to `logging` module |

**Blocked (waiting on external inputs):**
- HEC-RAS Full Simulation — needs `.prj` project file from team
- Live Météo-France feed — needs API key

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` on `streamlit` | Wrong Python interpreter selected | Press `Ctrl+Shift+P` → `Python: Select Interpreter` → choose `.conda/python.exe` |
| `DATA_ROOT not set` in health check | `.env` file missing or incomplete | Copy `.env.example` to `.env` and fill in both variables |
| `FileNotFoundError` on `.tif` | Google Drive not mounted or wrong path | Open Google Drive Desktop and verify `G:\Shared drives\DigiTwin\` is accessible |
| Conda not found in `setup_team.ps1` | Anaconda/Miniconda installed in non-standard path | Edit line 21 in `setup_team.ps1` with your actual conda path |
| French accent encoding errors | Asset keys contain `é`, `ê`, etc. | Use only ASCII keys — see `ARCHITECTURE.md` Section 2 |
| Port 8501 already in use | Streamlit already running | Kill the existing process: `Get-Process python | Stop-Process` |

---

*This document was last updated: 2026-05-14*
*Maintainer: Tin Luan — tinluan/railway-flood-twin*
