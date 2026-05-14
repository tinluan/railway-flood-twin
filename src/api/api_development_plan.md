# API Feature Development Plan — Railway Flood-Twin

**Objective:** Build a RESTful API layer to expose the digital twin's data, risk verdicts, and computational engine to external systems. This is a critical step for Layer 4 (Vulnerability & Alert) to programmatically sync with the signaling system (ETCS/RBC) and allow external dashboards or services to consume the 15-minute operational cycle outputs.

**Technology Choice:** **FastAPI** + **Uvicorn**
*(FastAPI is highly performant, automatically generates Swagger/OpenAPI documentation, and works natively with Pydantic for strict JSON schema validation, which aligns well with our data requirements.)*

---

## Phase 1: Setup & Architecture Preparation
- [x] **1.1. Add Dependencies:** Update `requirements.txt` to include `fastapi`, `uvicorn`, and `pydantic`.
- [x] **1.2. Directory Structure:** Create the `src/api/` module:
  ```text
  src/api/
  ├── __init__.py
  ├── main.py             # FastAPI application instance & config
  ├── routers/            # API Route groupings (e.g., assets.py, alerts.py, engine.py)
  └── schemas.py          # Pydantic data models for request/response validation
  ```
- [x] **1.3. Path Management:** Ensure the API strictly uses `src/utils/paths.py` (`ProjectPaths`) to resolve the locations of `data/processed/` files (e.g., `z_config.json`, `hecras_wse_results.json`).

---

## Phase 2: Data Models (Pydantic)
*Note: All JSON keys must strictly adhere to the project's **ASCII-only** naming convention (e.g., `Fosse terre`, `Voie_seg_01`).*
- [x] **2.1. Asset Model:** Define schema for an asset including its properties (`segment_id`, `geometry`, `z_terrain`, `z_ballast`, etc.) and thresholds (`yellow_z_m`, `orange_z_m`, `red_z_m`).
- [x] **2.2. Risk Status Model:** Define schema for the current risk state (Green, Yellow, Orange, Red) and calculated probabilities from fragility curves.
- [x] **2.3. SWI & Weather Model:** Define schema for returning current/historical SWI, active runoff, and rainfall.

---

## Phase 3: Read-Only Data Endpoints (GET)
Expose the processed data and configuration to external consumers.
- [x] **3.1. `GET /api/v1/assets`**: Retrieve the list of monitored assets and their static configurations (reads `data/processed/z_config.json` and `data/processed/voie_segments.json`).
- [x] **3.2. `GET /api/v1/assets/{asset_id}`**: Retrieve details and current status for a specific asset.
- [x] **3.3. `GET /api/v1/cross-sections/{asset_id}`**: Retrieve the 60m E-W synthetic or sampled DTM cross-section for a specific asset (reads `data/processed/cross_sections.json`).
- [x] **3.4. `GET /api/v1/hydrology/swi`**: Return the current and historical SWI and runoff coefficient (reads `data/processed/swi_results.csv`).
- [x] **3.5. `GET /api/v1/flood-polygons/{timestep}`**: Return the synthetic inundation GeoJSON for a specific timestep (reads `data/processed/synthetic_flood_timesteps.json`).

---

## Phase 4: RAMS Alert & Signalling Endpoints
Crucial for syncing with the ETCS/RBC systems.
- [x] **4.1. `GET /api/v1/alerts/current`**: Returns a system-wide risk verdict. Evaluates if any asset is currently in `YELLOW`, `ORANGE`, or `RED` state based on WSE vs Z_ballast.
- [x] **4.2. `GET /api/v1/alerts/hotspots`**: Returns the top N critical assets (Hotspot Auto-Focus logic from the dashboard).

---

## Phase 5: Engine Trigger Endpoints (POST)
Expose triggers to manually or programmatically start the 15-minute operational cycle.
- [x] **5.1. `POST /api/v1/engine/cycle`**: Trigger the 15-Minute Operational Cycle:
  1. Fetch Weather Data (Data Ingestion)
  2. Update SWI (`swi_calculator.py`)
  3. If SWI > limit, trigger HEC-RAS (`hecras_bridge.py` / `synthetic_inundation.py`)
  4. Dispatch Alerts (`alert_dispatcher.py`)
- [x] **5.2. `POST /api/v1/engine/simulate`**: Accept a custom rainfall payload and run a projected simulation returning the forecasted WSE and alerts.

---

## Phase 6: Code Quality & Integration
- [ ] **6.1. Logging Migration:** The API should integrate seamlessly with the ongoing Task 8 (Migrate engine scripts from `print()` to `logging`) to capture internal engine events properly in API logs.
- [x] **6.2. CORS Configuration:** Configure Cross-Origin Resource Sharing in `main.py` to allow the Streamlit dashboard or a future React/Vue frontend to make API calls.
- [x] **6.3. API Documentation:** Review the auto-generated Swagger UI (`/docs`) to ensure endpoint descriptions match the SNCF 4-Layer Architecture context.
- [x] **6.4. Testing:** Add a `tests/test_api.py` using `fastapi.testclient.TestClient` to verify the endpoints correctly read the `data/processed` files without crashing.

---

## Execution Log
| Date | Phase | Status | Notes |
|:-----|:------|:-------|:------|
| 2026-05-10 | Phase 1 | ✅ DONE | Dependencies in requirements.txt, directory structure created, ProjectPaths used |
| 2026-05-10 | Phase 2 | ✅ DONE | 13 Pydantic models in schemas.py (enums, assets, cross-sections, SWI, alerts, engine) |
| 2026-05-10 | Phase 3 | ✅ DONE | 5 GET endpoints across assets.py & hydrology.py routers |
| 2026-05-10 | Phase 4 | ✅ DONE | 2 GET endpoints in alerts.py (system verdict + hotspot ranking) |
| 2026-05-10 | Phase 5 | ✅ DONE | 2 POST endpoints in engine.py (cycle trigger + custom simulation) |
| 2026-05-10 | Phase 6 | ✅ DONE (3/4) | CORS configured, Swagger verified, 23/23 tests passing. Task 6.1 pending Task 8 |

## How to Run
```bash
# Start the API server
.conda\python.exe -m uvicorn src.api.main:app --reload --port 8000

# Run tests
.conda\python.exe -m pytest tests/test_api.py -v

# Access docs
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
# Health:     http://localhost:8000/health
```
