# 🌩️ Subsystem Blueprint: Rainfall Ingestion

**Objective**: Provide a reliable stream of rainfall data for the Digital Twin, supporting both live API fetching and historical scenario simulation.

---

## 📐 Architecture Diagram

```text
  EXTERNAL SOURCES           RAIN INGESTION MODULE           OUTPUT
  ================           =====================           ======

 [ OpenWeather API ] ----+
                         |     +---------------+
                         +---> | MODE SELECTOR |
                         |     | (Live / Demo) |
 [ Historical CSV  ] ----+     +-------+-------+
                                       |
                                       v
                               +-------+-------+       +-------------------+
                               | DATA FORMATER | ----> | data/rainfall.csv |
                               +---------------+       +---------+---------+
                                                                 |
                                                                 v
                                                       +-------------------+
                                                       | RISK ENGINE TRIGGER |
                                                       +-------------------+
```

---

## 🛠️ Module Specifications: `data_ingestion.py`

### 1. `fetch_live_rain(api_key, coords)`
- **Input**: Lat/Long of the railway corridor.
- **Output**: Current rainfall (mm/h) and 24h forecast.
- **Failure Mode**: If API is down, automatically fallback to the last cached value.

### 2. `simulate_scenario(scenario_id)`
- **Scenario 1**: "The 2023 Flash Flood" (High intensity, short duration).
- **Scenario 2**: "The Long Soak" (Medium intensity, 48h duration).
- **Purpose**: Essential for the PLM26 contest demonstration to show "Red Alerts."

---

## 📋 Task List

- [ ] **Task 1.1**: Define the `RainfallRecord` data structure (Timestamp, Intensity, Unit).
- [ ] **Task 1.2**: Implement the `SimulationEngine` for historical playback.
- [ ] **Task 1.3**: Integrate **OpenWeatherMap** API (requires free API Key).
- [ ] **Task 1.4**: Add a "Data Health" check to ensure the CSV output is valid.

---

## 🏁 Expected Outcome
A single command `python src/engine/data_ingestion.py --mode demo` will create a rainfall event that the **Risk Engine** can immediately process.
