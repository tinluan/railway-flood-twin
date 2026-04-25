# Architecture for a Railway Flood-Risk Digital Twin (SNCF Professional Standard)

## Executive Overview
This document outlines the professional-grade technical architecture for a Railway Flood-Risk Digital Twin, aligned with **SNCF Réseau** operational standards. This architecture moves beyond simple rule-based systems to incorporate a **High-Fidelity Physics Engine (HEC-RAS 2D)**, **Soil Saturation Logic (Leaky Bucket SWI)**, and **Probabilistic Failure Analysis (Fragility Curves)**.

The system is designed for a **15-minute operational cycle**, ensuring that the "Physical State" of the railway is continuously synchronized with the "Digital Twin" for real-time decision support.

---

## 🏛️ The 4-Layer Professional Architecture

### Layer 1: Data Sources (Input)
- **BIM Environment**: Infrastructure geometry (Civil 3D/Revit), Drainage networks (IFC), and Embankment Slopes.
- **GIS Environment**: 5m DTM Rasters, LiDAR cloud points, Land Cover, and Roughness datasets.
- **Live Meteorological**: Météo-France Radar/Gauge API (JSON/CSV) providing real-time and forecast cumulative rainfall.

### Layer 2: The Bridge (Integration & Mirror Database)
- **Coordinate Projection**: Synchronizing all data into **EPSG:2154 (Lambert 93)**.
- **Geometric Intersection**: Merging BIM Z-levels (Ballast Height) with GIS Terrain Z-levels.
- **SWI Algorithm (Leaky Bucket)**: Calculating soil saturation using recursive decay factors (`C = 0.5^(1/T)`).
- **Controller**: Python-based automation (ArcPy / GeoPandas) managing the data flow into the Mirror Database.

### Layer 3: Simulation Engine (Digital Twin Core)
- **Hydrological Model**: Using the **Sigmoid Runoff Coefficient** (`C_runoff`) to determine how much rainfall becomes active discharge based on the SWI.
- **Hydraulic Model (HEC-RAS 2D)**: Executing full-physics inundation simulations when Rain/SWI thresholds are exceeded.
- **Result Processing**: Extracting **WSE (Water Surface Elevation)** and Velocity from HEC-RAS HDF5 output files.

### Layer 4: Vulnerability & Alert (Output)
- **Fragility Curve Evaluation**: Comparing WSE and Velocity against asset-specific fragility curves to calculate a **Probability of Failure (%)**.
- **The Verdict**: Comparing `WSE` against `Z_ballast`.
- **HMI Dashboard**: A Traffic Light system (Green/Yellow/Red) synchronized with the Signalling System (ETCS/RBC).

---

## 📐 Scientific Logic & Formulas

### 1. Soil Water Index (Leaky Bucket)
`SWI(t) = Rt * (1 - C) + SWI(t-1) * C`
- **Rt**: Rainfall at day t.
- **C**: Decay factor (0.9 for deep soil).
- **Calibration**: The half-life `T` is optimized via a 10-year AUC hit-rate analysis against historical accidents.

### 2. Runoff Coefficient (Sigmoid)
`C_runoff = C_max / (1 + e^(-k * (SWI - SWI_mid)))`
- High SWI → High Runoff (0.9)
- Low SWI → Low Runoff (0.2)

### 3. Hydraulic Verdict
`WSE = Z_terrain + Depth_water`
- **SAFE**: `WSE < Z_ballast`
- **UNSAFE**: `WSE > Z_ballast` (Trigger Emergency Alert)

---

## 🏁 Operational Decision Matrix (RAMS)

| Risk Level | Probability | Dashboard Color | Operational Action |
| :--- | :--- | :--- | :--- |
| **Low** | < 20% | 🟢 Green | Standby / Log Data |
| **Medium** | 20% - 50% | 🟡 Yellow | Speed Restriction (60 km/h) |
| **High** | > 50% | 🔴 Red | Emergency Halt (ETCS Stop) |

---

## 🎯 The "Funnel" Hotspot Strategy
To manage the computational load of HEC-RAS 2D over 400km of track, the architecture uses a funnel approach:
1. **Full Network**: Screened via **RiskVIP Static Maps** and **Historical Accident Data**.
2. **Identification**: Hotspots (~50km total) are selected for active monitoring.
3. **Core Computing**: Real-time HEC-RAS 2D and SWI calculations are performed ONLY on these critical sections.
