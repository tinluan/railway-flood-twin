# Version Ledger: Railway Flood-Risk Digital Twin

> **Purpose**: This is the **single source of truth**. It separates "What is Being Tried" from "What is Final & Stable."

---

## 🔬 Section 1: Active Trials & Work-In-Progress (WIP)
*Log your current experiments here. This allows the team to see what you are changing **before** it is merged to main.*

| Started | Author | Feature / Script | Current Branch / Hash | Status | Intent |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-04-19 | AI:Antigravity | Milestone 3: DTM Summary | `1f1d64f` | ✅ Well-Run | Successfully extracted elevation stats (min 204m, max 288m) for track_area. |
| *(example)* | Szilvi | CRS Testing | `szilvi-crs-experiment` | 🔬 Trial | Testing if EPSG:3948 works better for local area. |

---

## ✅ Section 2: Final Change Log (Stable Releases)
*Only log items here once they are **Well-Run** and merged into the `main` branch. This is the master record for your final report.*

| Date | Author | Component | Git Hash | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-03-29 | Tin | `data/staging/gis/` | `5cadf50` | ✅ Well-Run | First cleaned GIS layers loaded. 30 assets. SRID 2154. |
| 2026-04-19 | Tin + AI | Governance Overhaul | `1f1d64f` | ✅ Well-Run | AI-agnostic rules, version ledger, and Copilot instructions synced. |
| 2026-04-19 | AI:Antigravity | `derive_track_area_elevation_updated.py` | `1f1d64f` | ✅ Well-Run | Generated elevation summary CSV and GPKG for `track_area`. |

---

## 🔀 Section 3: Cross-Job Change Register
*When you modify a file belonging to another member's primary role.*

| Date | Changed By | File Changed | Owner | Reason | Notified? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| *(None yet)* | | | | | |

---

## 📋 Well-Run Script Registry
*Verified "Trusted Versions" of core project tools.*

| Script | Version / Hash | Validated By | Date | Output |
| :--- | :--- | :--- | :--- | :--- |
| `src/utils/paths.py` | `5cadf50` | Tin | 2026-03-29 | Correctly resolves all project paths from `.env` |
| `src/utils/check_health.py` | `5cadf50` | Tin | 2026-04-19 | All 4 checks pass on local machine |
| `src/transform/generate_docs_from_staging.py` | `5cadf50` | Tin | 2026-03-29 | Generated 4 docs from staging GIS files |
| `src/transform/derive_track_area_elevation_updated.py` | `1f1d64f` | AI:Antigravity | 2026-04-19 | Extracted elevation for 16,453 track pixels |
