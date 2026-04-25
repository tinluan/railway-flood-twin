# 🗺️ Roadmap to the RailTwin Flood Demonstrator

This roadmap translates the **PLM26 Contest Requirements** into the technical building blocks for the Railway Flood-Risk Digital Twin.

---

## 🏛️ 1. Architecture Alignment
The contest requires a 3-layer architecture with **Automatic Data Flow**.

### Layer 1: Spatial Preparation (QGIS) - [DONE]
- [x] CRS Harmonization (Lambert 93)
- [x] Terrain Indicators (Slope, Aspect, Flow Accumulation)
- [x] Rail Segmentation (Corridor-scale)

### Layer 2: Risk Computation (Python) - [NEXT]
- [ ] **Input Handoff**: Automate export from GIS to Python-readable format (Parquet/GPKG).
- [ ] **Exposure Model**: Compute rainfall exposure for each rail segment.
- [ ] **Rule-Based Engine**: Apply scientific risk classes (Low/Medium/High).

### Layer 3: Visualization (Streamlit) - [PHASE 3]
- [ ] Interactive Risk Map.
- [ ] Explainable Dashboard (Why is this segment at risk?).
- [ ] Decision Support (Prioritized inspection list).

---

## 🌩️ 2. Operational Scenarios
We must demonstrate the twin's value in three distinct timeframes:

1. **Pre-Event (Forecast)**: Identify vulnerabilities *before* the rain starts.
2. **During-Event (Real-Time)**: Update risk scores as new rainfall data arrives.
3. **Post-Event (Recovery)**: Prioritize inspection crews based on final scour estimates.

---

## 📊 3. Feature Backlog (Prioritized)
| ID | Feature | Priority | Best AI Tool |
| :--- | :--- | :--- | :--- |
| **ENG-01** | `handoff_manager.py` (GIS -> Risk Engine bridge) | 🔴 High | Antigravity |
| **ENG-02** | `risk_formulas.py` (Literature-based scoring) | 🔴 High | Antigravity + References |
| **DASH-01** | `dashboard_main.py` (Streamlit skeleton) | 🟡 Med | VS Code Copilot |
| **DASH-02** | `map_view.py` (Folium/Leaflet risk map) | 🟡 Med | VS Code Copilot |

---

## 🏁 The "North Star" Milestone
**Goal**: A fully synchronized workflow where dropping a CSV rainfall file into the `data/` folder automatically updates the Streamlit dashboard map.
