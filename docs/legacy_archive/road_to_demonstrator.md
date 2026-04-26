# 🗺️ Technical Roadmap: Road to the Demonstrator

> **North Star**: Deliver a working PLM26 contest demonstrator that proves a 4-layer Digital Twin can autonomously detect flood risk and trigger operational decisions on the French railway network.

---

## 🏛️ 1. Architecture Alignment
The contest requires a 4-layer architecture with **Automatic Data Flow**.

### Layer 1: Data Sources - [DONE ✅]
- [x] BIM Environment (Rail Alignment, Drainage Network/IFC, Embankment Slopes)
- [x] GIS Environment (5m DTM Raster, LiDAR, Land Cover/Roughness)
- [x] Meteorological (Météo-France API → JSON/CSV)

### Layer 2: The Bridge (Python Pre-Processor & Mirror Database) - [NEXT]
- [ ] **Task 2.0: Hotspot Identification ("The Funnel")**: Use RiskVIP static maps + Historical Accident dates to filter 400km line → ~50km critical segments. [See Blueprint](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/handoff_schema.md)
- [ ] **Task 2.1: BIM-GIS Intersection**: Extract Z_ballast (IFC) and Z_terrain (LiDAR/DTM) for each rail segment via GDAL/Fiona.
- [ ] **Task 2.2: Mirror Database Export**: Write validated GeoPackage (EPSG:2154) with all mandatory schema columns.
- [ ] **Task 2.3: Rainfall Ingestion**: Implement the Fetcher/Simulator to feed the twin. [See Blueprint](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/rainfall_ingestion.md)

### Layer 3: Simulation Engine - [PHASE 3]
- [ ] **Task 3.1: SWI Calculator**: Implement the Leaky Bucket formula (`SWI(t) = Rt*(1-C) + SWI(t-1)*C`).
- [ ] **Task 3.2: SWI Calibrator**: Optimize T (half-life) using 10-year AUC loop against accident data.
- [ ] **Task 3.3: HEC-RAS Trigger**: Execute HEC-RAS 2D when Rain or SWI exceeds thresholds.
- [ ] **Task 3.4: HEC-RAS Reader**: Extract WSE & Velocity from HDF5 output files.
- [ ] **Task 3.5: Fragility Curve Evaluator**: Convert WSE → Probability of Failure. [See Blueprint](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/risk_engine.md)

### Layer 4: Vulnerability & Alert Dashboard - [PHASE 4]
- [ ] **Task 4.1**: Compare WSE vs Z_ballast → Green/Yellow/Red classification.
- [ ] **Task 4.2**: ArcGIS/Streamlit Dashboard with Traffic Light system.
- [ ] **Task 4.3**: Sync decision with Signalling System (ETCS/RBC simulation).
- [ ] **Task 4.4**: Operator Verification & HMI loop.

---

## 🎯 2. The "Funnel" Hotspot Strategy
To make HEC-RAS 2D computationally feasible:
```
Full 400km Railway Line
         |
  [RiskVIP Static Maps]  +  [Historical Accidents (Known Failures)]
         |
  Is Location Critical?
   YES: Selected Hotspots (~50km total)  --> Full HEC-RAS 2D simulation
   NO:  Skip (SWI-only risk estimate)
```

---

## 📋 3. Module-to-File Mapping

| Python Module | Layer | Blueprint |
| :--- | :--- | :--- |
| `src/engine/data_ingestion.py` | 2 | [rainfall_ingestion.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/rainfall_ingestion.md) |
| `src/engine/preprocessor.py` | 2 | [handoff_schema.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/handoff_schema.md) |
| `src/engine/swi_calculator.py` | 3 | [risk_engine.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/risk_engine.md) |
| `src/engine/hec_ras_runner.py` | 3 | [risk_engine.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/risk_engine.md) |
| `src/engine/fragility_curves.py` | 3 | [risk_engine.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/risk_engine.md) |
| `src/engine/alert_dispatcher.py` | 4 | [risk_engine.md](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/subsystems/risk_engine.md) |
| `src/dashboard/app_main.py` | 4 | (To be drafted) |
