# 🧠 Subsystem Blueprint: Risk Engine (SNCF Réseau Edition)

**Objective**: Compute railway flood risk using a two-stage pipeline: a Hydrological model (SWI Leaky Bucket) to estimate runoff, followed by a Hydraulic model (HEC-RAS 2D) to calculate inundation depth, with a Fragility Curve to convert depth into a Probability of Failure.

---

## 📐 The Operational Cycle (15-minute trigger)

```text
  START 15-MIN CYCLE
         |
         v
 [Fetch Live Radar/Gauge] --> [Quality Control?]
                                    |          |
                               Noisy/Error   Clean
                                    |          |
                          [Apply Kalman Filter] |
                                    |          |
                                    +------>---+
                                               |
                                               v
                                  [Update SWI & Runoff Coeff]
                                               |
                              +--NO--[Is Rain or SWI > Limit?]--YES--+
                              |                                       |
                              v                                       v
                       [Standby / Log]               [Execute HEC-RAS 2D Physics]
                                                              |
                                                              v
                                                  [Extract WSE & Velocity from HDF5]
                                                              |
                                                              v
                                                  [Calculate Failure Probability
                                                   via Fragility Curves]
                                                              |
                              +--<20%--[Risk Level?]--20-50%--+-->50%--+
                              |                |                       |
                       [GREEN: Standby] [YELLOW: Speed Restriction] [RED: Emergency Halt]
                              |                |                       |
                              +----------------+-----------------------+
                                               |
                                        [Sync Signalling System]
```

---

## 🧪 Scientific Formulas

### Stage 1: Hydrological Model — SWI (The "Volume")
**Purpose**: *"How much rain turns into runoff?"*

**Leaky Bucket Formula:**
```
SWI(t) = Rt * (1 - C) + SWI(t-1) * C
C = (0.5)^(1/T)
SWI(0) = 0
```
- **Rt**: 60-minute cumulative rainfall (mm).
- **C**: Decay factor. T = calibrated half-life (optimized via AUC against historical accidents).
- **High SWI** → soil is saturated → runoff coefficient is HIGH.

**Sigmoid Runoff Coefficient:**
```
C_runoff = C_max / (1 + e^(-k * (SWI - SWI_mid)))
```
- High SWI: C_runoff → **0.9** (90% of rain becomes surface runoff)
- Low SWI: C_runoff → **0.2** (soil absorbs most rain)

---

### Stage 2: Hydraulic Model — HEC-RAS 2D (The "Danger")
**Purpose**: *"How deep will that runoff be at the railway embankment?"*

**The Verdict Formula:**
```
WSE = Z_terrain + Depth_water
```
- **WSE**: Water Surface Elevation (from HEC-RAS HDF5 output).
- **Z_terrain**: Ground elevation at segment (from DTM / LiDAR).
- Compare WSE against **Z_ballast** (from BIM IFC model):
  - `WSE > Z_ballast` → 🔴 UNSAFE
  - `WSE < Z_ballast` → 🟢 SAFE

---

### Stage 3: Vulnerability Assessment — Fragility Curves
**Purpose**: Convert hydraulic depth/velocity into a **Probability of Failure (%)**
- Source: *"Development of Fragility Curves for Railway Embankment and Ballast Scour"* (Key Ref in `references_ledger.md`).

| Probability of Failure | Risk Class | Operational Decision |
| :--- | :--- | :--- |
| < 20% | 🟢 LOW | Standby / Log Data |
| 20% - 50% | 🟡 MEDIUM | Speed Restriction (RAMS) |
| > 50% | 🔴 HIGH | Emergency Halt (ETCS/RBC) |

---

## 🎯 The "Funnel" Hotspot Strategy
To make HEC-RAS computationally feasible on a 400km railway line:
1. **Full 400km line** filtered by **RiskVIP static maps** + **Historical Accidents**.
2. Output: **~50km of critical hotspots** where HEC-RAS is run.
3. Remaining segments get the simplified SWI-only risk estimate.

---

## 📋 Task List

- [ ] **Task 2.1**: Implement `SWI_Calculator` (Leaky Bucket, recursive formula).
- [ ] **Task 2.2**: Implement `SWI_Calibrator` (10-year AUC optimization loop, T=1 to 60 days).
- [ ] **Task 2.3**: Implement `RunoffSigmoid` to convert SWI to a dynamic runoff coefficient.
- [ ] **Task 2.4**: Implement `HEC_RAS_Trigger` (call HEC-RAS 2D when threshold exceeded).
- [ ] **Task 2.5**: Implement `HEC_RAS_Reader` (extract WSE/Velocity from HDF5 output).
- [ ] **Task 2.6**: Implement `FragilityCurveEvaluator` (convert WSE to Probability of Failure).
- [ ] **Task 2.7**: Implement the `AlertDispatcher` (Green/Yellow/Red + ETCS sync).

---

## 🏁 Expected Outcome
A full 15-minute operational cycle that takes live radar data as input and outputs a **Traffic Light Alert** synchronized with the railway signalling system, justified by a probabilistic failure analysis.
