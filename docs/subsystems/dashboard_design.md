# 📊 Subsystem Blueprint: Dashboard & HMI Design

**Objective**: Provide a real-time "Command and Control" interface for railway dispatchers to monitor flood risk and execute operational decisions (RAMS).

---

## 🏗️ UI Architecture (Streamlit / ArcGIS)

```text
  [ TOP BAR: NETWORK HEALTH ]
  🟢 SAFE: 92% | 🟡 CAUTION: 5% | 🔴 ALERT: 3% (Segments)

  +-----------------------+----------------------------------+
  |    [ 🗺️ LIVE MAP ]    |       [ 📈 SEGMENT DETAIL ]       |
  |                       |                                  |
  | (Railway corridor     |  [ WSE vs Ballast Height Plot ]  |
  |  with color-coded     |                                  |
  |  segment risk)        |  [ Current SWI: 142 mm        ]  |
  |                       |  [ Current Rain: 12 mm/h      ]  |
  |                       |                                  |
  +-----------------------+----------------------------------+
  |    [ 📋 ALERT LOG ]   |       [ 🚨 OPERATIONAL ACTION ]   |
  |                       |                                  |
  | 14:15 - Segment #142  |  **PROBABILITY OF FAILURE: 68%** |
  | Trigger: WSE > Ballast|                                  |
  | Action: RED ALERT     |  [ BUTTON: SYNC ETCS HALT ]      |
  +-----------------------+----------------------------------+
```

---

## 🚦 The Traffic Light System (RAMS)

The dashboard logic maps our **Fragility Curve** output to operational reality:

| Dashboard Color | Risk Probability | Signalling Logic | Action Required |
| :--- | :--- | :--- | :--- |
| 🟢 **Green** | < 20% | Clear Path | No action. Continuous monitoring. |
| 🟡 **Yellow** | 20% - 50% | Speed Restricted | Alert Driver. Reduce to 60 km/h. |
| 🔴 **Red** | > 50% | Emergency Stop | Trigger ETCS Stop Command. |

---

## 📈 Key Visualizations

### 1. The Verdict Plot (Real-Time)
- **Y-Axis**: Elevation (m)
- **X-Axis**: Time (Last 24h + 6h Forecast)
- **Lines**: 
  - `Z_ballast` (Static Red Dash)
  - `Z_terrain` (Static Brown Line)
  - `WSE` (Dynamic Blue Wave from HEC-RAS)
- **Insight**: When the Blue Wave crosses the Red Dash, the Red Alert is automatically triggered.

### 2. The Soil Saturation Gauge
- **Indicator**: SWI (Soil Water Index).
- **Threshold**: 150mm (Calibrated half-life threshold).
- **Insight**: Shows how "primed" the ground is for a flash flood even before the rain starts.

---

## 📋 Task List

- [ ] **Task 4.1**: Build the Sidebar (Corridor selection and Scenario mode).
- [ ] **Task 4.2**: Integrate **PyDeck / Folium** for the interactive railway map.
- [ ] **Task 4.3**: Create the `plotly` chart for the WSE vs Ballast height comparison.
- [ ] **Task 4.4**: Implement the **"Explainability Panel"** (Show the math: SWI, Sigmoid, and Fragility values).
- [ ] **Task 4.5**: Add the "Download Report" button (Generate PDF summary of the risk event).

---

## 🏁 Expected Outcome
A high-performance dashboard where a user can toggle between **"Live Mode"** (Météo-France API) and **"Contest Mode"** (Historical Flash Floods) to witness the Digital Twin's autonomous decision-making in action.
