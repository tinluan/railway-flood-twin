# Calibration & Validation Strategy — Railway Flood-Risk Digital Twin

> **Standard**: ISO 23247 (Digital Twin Manufacturing Framework), adapted for SNCF RAMS
> **Philosophy**: A Digital Twin is only as reliable as the evidence that its outputs match reality.
> **Structure**: Calibrate each layer individually, then validate the integrated system end-to-end.

---

## Terminology

| Term | Definition | Your Project Example |
|------|-----------|---------------------|
| **Calibration** | Tuning model parameters so outputs match known observations | Adjusting SWI half-life `T` until the model correctly predicts past flooding events |
| **Validation** | Testing the calibrated model against *independent* data it has never seen | Running a historical storm the model was NOT calibrated on and checking if it predicts the correct WSE |
| **Verification** | Confirming the code correctly implements the mathematical equations | Unit-testing that `SWI(t) = Rt*(1-C) + SWI(t-1)*C` produces expected numerical output |
| **Sensitivity Analysis** | Measuring how much output changes when you vary one input parameter | "If I change Manning's n by ±20%, how much does WSE change?" |

---

## Phase 1: Verification (Does the Code Match the Math?)

> **Goal**: Prove that every formula in the codebase is implemented correctly, independent of real-world accuracy.

### 1.1 SWI Leaky Bucket — Unit Test

**What to prove**: The recursive filter `SWI(t) = Rt*(1-C) + SWI(t-1)*C` with `C = 0.5^(1/T)` is implemented correctly.

**Test procedure**:
```powershell
.\.conda\python.exe -m pytest tests/test_pipeline.py -v
```

**Manual check — Zero-Rain Decay**:
| Input | Expected Output | Pass Criteria |
|-------|----------------|---------------|
| 240 hours of 0 mm/h rain after a 100mm SWI spike | SWI decays to exactly 50mm at t=240h (half-life = 10 days = 240h) | `abs(SWI[240] - 50.0) < 0.01` |
| 480 hours of 0 mm/h rain | SWI decays to exactly 25mm | `abs(SWI[480] - 25.0) < 0.01` |

**Manual check — Constant Rain Steady-State**:
| Input | Expected Steady-State | Formula |
|-------|----------------------|---------|
| Constant 10 mm/h indefinitely | `SWI_ss = Rt * (1-C) / (1-C) = Rt` → converges to ~10 / (1-C) | SWI must plateau, not grow infinitely |

> [!IMPORTANT]
> If the Zero-Rain test fails, the decay constant `C` is wrong — recalculate `C = 0.5^(1/T)`.

### 1.2 Sigmoid Runoff — Boundary Check

**What to prove**: `C_runoff = C_max / (1 + e^(-k * (SWI - SWI_mid)))` with `C_max=0.9`, `k=0.05`, `SWI_mid=150mm`.

| SWI (mm) | Expected C_runoff | Physical Meaning |
|----------|------------------|------------------|
| 0 | ≈ 0.001 (near zero) | Dry soil absorbs everything |
| 150 | = 0.45 (exactly C_max / 2) | Midpoint by definition |
| 300 | ≈ 0.899 (near C_max) | Saturated — almost all rain becomes runoff |

### 1.3 Fragility Curve — Log-Normal CDF

**What to prove**: `P_failure = Φ(ln(depth / 0.30) / 0.40)` matches expected values.

| Water Depth (m) | Expected P_failure | Risk Category |
|------------------|--------------------|---------------|
| 0.00 | 0.000 | LOW |
| 0.05 | ≈ 0.010 | LOW |
| 0.15 | ≈ 0.123 | LOW |
| 0.30 | = 0.500 | HIGH |
| 0.60 | ≈ 0.905 | HIGH |

```powershell
# Quick verification script
.\.conda\python.exe -c "from src.engine.fragility_curves import FragilityEvaluator; e=FragilityEvaluator(); [print(f'{d}m -> P={e.calculate_p_failure(d):.3f} -> {e.get_risk_category(e.calculate_p_failure(d))}') for d in [0, 0.05, 0.15, 0.30, 0.60]]"
```

### 1.4 Alert Dispatcher — WSE Override Logic

**What to prove**: If WSE > z_ballast, the verdict is always RED regardless of P_failure.

| WSE (m) | z_ballast (m) | P_failure | Category Input | Expected Verdict |
|---------|--------------|-----------|----------------|-----------------|
| 220.0 | 221.5 | 0.10 | LOW | GREEN (no override) |
| 222.0 | 221.5 | 0.10 | LOW | **RED** (WSE override) |
| 222.0 | 221.5 | 0.65 | HIGH | RED (both agree) |

---

## Phase 2: Calibration (Tuning Models to Match Reality)

> **Goal**: Adjust free parameters so model outputs reproduce observed historical events.

### 2.1 SWI Half-Life Calibration (Parameter `T`)

**The key parameter**: `half_life_days` (currently set to 10 days in `settings.py`).

**Calibration method — AUC Optimization Loop**:
1. Obtain 10 years of historical daily rainfall for the Tartaiguille corridor (Météo-France station or ERA5 reanalysis).
2. Obtain historical flooding incident dates from SNCF accident database.
3. For each candidate `T` (sweep from 1 to 60 days):
   - Run the SWI model on the full 10-year series.
   - At each historical accident date, record the SWI value.
   - Compute the **AUC (Area Under ROC Curve)**: how well does "SWI > threshold" predict "accident occurred"?
4. Select the `T` that maximizes the AUC.

**What to report**:
- A plot of **AUC vs. T** (x-axis: half-life in days, y-axis: AUC score 0–1).
- The optimal `T` value and its AUC score.
- State whether `T=10 days` (your current default) is close to the optimum.

> [!NOTE]
> If you do not have access to historical SNCF accident data, state this as a limitation in the report. The current `T=10 days` is based on published Météo-France SWI literature for clay-rich soils in the Drôme valley.

### 2.2 HEC-RAS Manning's n Calibration

**The key parameter**: Surface roughness (Manning's n) in the 2D mesh.

**Calibration method — High-Water Mark Comparison**:
1. Identify a **known historical flood event** on the study reach (e.g., September 2002 Gard/Drôme event).
2. Find recorded high-water marks (laisse de crue) or gauging station peak levels.
3. Run HEC-RAS with the historical rainfall hydrograph.
4. Adjust Manning's n until the simulated WSE matches the observed high-water marks within ±10 cm.

**What to report**:
- A table comparing observed vs. simulated WSE at each calibration point.
- The final Manning's n values used per land cover type.
- If no local high-water data is available, justify the default values from HEC-RAS literature (e.g., Chow 1959).

### 2.3 Fragility Curve Parameters

**The key parameters**: `median_depth=0.30m`, `sigma=0.40`.

**Calibration method**:
- These are typically calibrated using **laboratory ballast scour experiments** or field failure records.
- For a capstone project: cite the source literature for your chosen values and state them as assumptions.

**What to report**:
- The source reference for `median_depth` and `sigma`.
- A sensitivity analysis: "If median_depth changes by ±50%, how does the RED alert threshold change?"

---

## Phase 3: Validation (Testing Against Independent Data)

> **Goal**: Prove the calibrated model predicts outcomes it was NOT trained on.

### 3.1 Split-Sample Validation (SWI)

**Method**: If you calibrated `T` using 2010–2019 data, validate using 2020–2025 data.
- Run the calibrated SWI model on the validation period.
- Check if it still correctly flags known incidents in the validation period.

**Metrics to report**:
| Metric | Target |
|--------|--------|
| AUC on validation set | > 0.70 |
| False Positive Rate | < 30% |
| False Negative Rate | < 10% (critical — cannot miss real floods) |

### 3.2 HEC-RAS Volume Conservation

**Method**: Check HEC-RAS computation log for mass balance errors.
1. Open `CAPSTONE_JN_L752_PK.prj` in HEC-RAS 6.7.
2. Run the Unsteady Flow simulation (Plan p01 or p02).
3. Check the **Volume Accounting** summary in the computation window.

**What to report**:
| Metric | Acceptable Threshold | Your Value |
|--------|---------------------|------------|
| Volume Accounting Error | < 1% | ___% |
| Max Courant Number | < 2.0 | ___ |
| Solution convergence | No "Solution went unstable" warnings | ✅ / ❌ |

> [!WARNING]
> If Volume Accounting Error exceeds 5%, the mesh resolution or timestep (Δt) is too coarse. Reduce `Δt Compute` or refine the mesh near culverts.

### 3.3 WSE Plausibility Check (Cross-Validation with Terrain)

**Method**: Compare extracted WSE values against the DTM to ensure physical plausibility.

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| WSE ≥ Terrain elevation | Compare `hecras_wse_results.json` against `dtm_fixed.tif` at same coordinates | No WSE below ground level |
| WSE within valley range | Check that max WSE does not exceed valley rim elevation (~250m NGF) | WSE < 250m for all cells |
| Depth at known culverts | WSE - terrain at Buse locations should be 0–3m for a 100-year event | Depths are physically reasonable |

### 3.4 Open-Meteo API Ground-Truth Check

**Method**: Compare the Open-Meteo AROME forecast against the official Météo-France observation for the same station and time window.

```powershell
# 1. Fetch live data from Open-Meteo
.\.conda\python.exe src/engine/rainfall_provider.py

# 2. Compare output in data/raw/rainfall_Ligne_400_live.csv against
#    the official Météo-France "Données Publiques" for station Montélimar (26198001)
#    URL: https://donneespubliques.meteofrance.fr
```

**What to report**:
| Metric | Target |
|--------|--------|
| RMSE (mm/h) between Open-Meteo and Météo-France observations | < 2.0 mm/h |
| Peak intensity error | < 20% |
| Timing offset of peak | < 2 hours |

---

## Phase 4: Sensitivity Analysis

> **Goal**: Quantify how much the final alert (GREEN/YELLOW/RED) changes when you vary uncertain inputs.

### 4.1 One-At-a-Time (OAT) Sensitivity

For each parameter, vary it by ±20% and record the change in output:

| Parameter | Default | -20% | +20% | Output Metric | Sensitivity |
|-----------|---------|------|------|--------------|-------------|
| `half_life_days` | 10 | 8 | 12 | Peak SWI (mm) at hour 24 | ___ |
| `SWI_mid` | 150 | 120 | 180 | Hour when C_runoff > 0.5 | ___ |
| `median_depth` (fragility) | 0.30 | 0.24 | 0.36 | P_failure at 0.25m depth | ___ |
| Manning's n | 0.035 | 0.028 | 0.042 | Peak WSE at Buse_41 (m) | ___ |
| `SWI_HECRAS_TRIGGER_MM` | 100 | 80 | 120 | Number of HEC-RAS triggers per year | ___ |

### 4.2 Scenario Stress Tests

| Scenario | Rainfall Input | Expected System Behavior |
|----------|---------------|-------------------------|
| **Dry Season** | 0 mm/h for 30 days | All alerts GREEN, SWI → 0, no HEC-RAS trigger |
| **Moderate Rain** | 5 mm/h constant for 48h | SWI rises gradually, alerts stay GREEN/YELLOW |
| **Cevenol Flash Flood** | Demo scenario (peak 40 mm/h) | SWI spikes, HEC-RAS triggers, RED alerts on Buse/Voie |
| **Extreme (1000-year)** | 80 mm/h for 6 hours | System must not crash; all alerts RED |

---

## Phase 5: End-to-End System Integration Test

> **Goal**: Prove the full 15-minute automated cycle works from rainfall API to operational alert.

### 5.1 Automated Test Suite
```powershell
.\.conda\python.exe -m pytest tests/ -v
```
All tests must pass. Current test coverage:
- `test_api.py`: 23 tests (REST API endpoints, Pydantic schema validation)
- `test_pipeline.py`: 2 tests (orchestrator demo mode, HEC-RAS trigger logic)
- `test_rainfall_provider.py`: API connectivity and JSON parsing

### 5.2 Live Fire Test (Manual — Full Pipeline)

| Step | Command / Action | What to Verify |
|------|-----------------|----------------|
| 1. Start API | `.\.conda\python.exe src/api/main.py` | FastAPI starts on port 8000 |
| 2. Start Dashboard | `.\.conda\python.exe -m streamlit run src/dashboard/app_main.py` | Streamlit UI loads with map |
| 3. Trigger Cycle | Click **"🔄 Fetch & Recompute"** | Terminal shows: API fetch → SWI calc → HEC-RAS trigger check |
| 4. Check Rainfall | Open `data/raw/rainfall_Ligne_400_live.csv` | Fresh timestamps from Open-Meteo (< 15 min old) |
| 5. Check SWI | Open `data/processed/swi_results.csv` | `swi_mm` column has realistic values (0–300mm range) |
| 6. Check Alerts | Dashboard shows color-coded assets | At least one asset changes alert level during the demo storm |
| 7. Check .u01 injection | Open `.u01` file in text editor | `Precipitation Hydrograph=` values match the live CSV |

### 5.3 Failure Recovery Test

| Failure Scenario | Expected Behavior |
|-----------------|-------------------|
| No internet (Open-Meteo unreachable) | System falls back to demo CSV data, logs warning |
| HEC-RAS not installed (no COM) | Pipeline skips HEC-RAS step, uses synthetic WSE, logs warning |
| Corrupted CSV (empty file) | Graceful error message, no crash |

---

## Summary: What to Include in the Report

> [!TIP]
> For each phase, include at least one **figure** or **table** as quantitative evidence.

| Evidence | Report Section | Figure/Table |
|----------|---------------|-------------|
| SWI half-life decay test | Verification | Fig: SWI decay curve (0→240h→480h) |
| Sigmoid runoff S-curve | Verification | Fig: C_runoff vs SWI (0–300mm) |
| Fragility curve shape | Verification | Fig: P_failure vs depth (0–1m) |
| AUC vs T optimization (if data available) | Calibration | Fig: AUC curve with optimal T marked |
| Manning's n justification | Calibration | Table: land cover → n values with source |
| HEC-RAS volume accounting | Validation | Screenshot: computation log showing < 1% error |
| WSE vs terrain plausibility | Validation | Table: WSE at each Buse location vs DTM elevation |
| Open-Meteo vs Météo-France comparison | Validation | Fig: overlay plot of both time series |
| OAT sensitivity table | Sensitivity | Table: parameter ±20% → output change |
| Stress test results | Sensitivity | Table: 4 scenarios → system response |
| Live fire test log | Integration | Screenshot: dashboard with alerts + terminal log |

> [!CAUTION]
> If you skip calibration entirely, state it explicitly as a limitation:
> *"The SWI half-life (T=10 days) and fragility parameters (median=0.30m) are adopted from published literature and have not been calibrated against local SNCF incident data. Future work should perform AUC optimization using the SNCF accident database."*
