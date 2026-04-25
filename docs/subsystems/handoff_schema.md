# 🌉 Subsystem Blueprint: Spatial Handoff Schema (SNCF Edition)

**Objective**: Standardize the "Mirror Database" — the central hub that merges BIM (IFC), GIS (DTM/LiDAR), and Meteorological data before feeding into the Risk Engine.

---

## 📐 The Mirror Database Flow

```text
  BIM ENVIRONMENT          GIS ENVIRONMENT          METEOROLOGICAL
  ===============          ===============          ==============
  Rail Alignment           5m DTM Raster            Live Radar API
  Drainage Network/IFC     LiDAR                    Forecast JSON
  Embankment Slopes        Land Cover/Roughness
         |                       |                        |
         +----------- PYTHON PRE-PROCESSOR ---------------+
                    (GDAL / Fiona / GeoPandas)
                             |
                  +----------+----------+
                  |                     |
         [Coordinate Projection]  [Geometric Intersection]
          (Lambert 93 / EPSG:2154)  (BIM Geometry over GIS)
                  |
                  v
         [MIRROR DATABASE]  ------>  [HEC-RAS Terrain Export]
         (GeoPackage / Parquet)
```

---

## 📋 The "Contract" — Mandatory Columns

Every handoff file exported from the Mirror Database must contain:

| Column Name | Source | Type | Description |
| :--- | :--- | :--- | :--- |
| **`segment_id`** | BIM | String | Unique 100m rail section ID. |
| **`geometry`** | GIS | WKB | Spatial line of segment (EPSG:2154). |
| **`z_terrain`** | DTM/LiDAR | Float | Ground elevation at segment centroid (meters). |
| **`z_ballast`** | BIM/IFC | Float | Top of ballast elevation (meters). Critical for WSE comparison. |
| **`slope_pct`** | DTM | Float | Average slope percentage along segment. |
| **`soil_type`** | GIS | String | Soil class (affects SWI decay constant T). |
| **`land_cover`** | GIS | String | Land cover (affects runoff coefficient). |
| **`asset_type`** | BIM | String | `Track`, `Culvert`, `Bridge` (changes fragility thresholds). |
| **`d_10y`** | HEC-RAS | Float | Pre-computed flood depth for 10-year return period (m). |
| **`d_100y`** | HEC-RAS | Float | Pre-computed flood depth for 100-year return period (m). |
| **`is_hotspot`** | RiskVIP | Boolean | `True` if segment is in the ~50km critical zone. |

---

## 🚦 Validation Rules

1.  **CRS Enforcement**: Must be **EPSG:2154 (Lambert 93)**. All other SRIDs will be rejected.
2.  **Null Check**: `z_terrain`, `z_ballast`, and `geometry` must NEVER be NULL.
3.  **Hotspot Flag**: Only segments with `is_hotspot = True` will trigger live HEC-RAS computation.
4.  **Format**: **`.gpkg`** (GeoPackage) is the required format for spatial indexing.

---

## 📋 Task List

- [ ] **Task 3.1**: Implement `PreProcessor.py` (GDAL/Fiona pipeline for BIM-GIS intersection).
- [ ] **Task 3.2**: Implement `MirrorDB_Writer.py` (export validated GeoPackage).
- [ ] **Task 3.3**: Implement `HandoffValidator.py` (check CRS, nulls, and schema).
- [ ] **Task 3.4**: Document the export SOP for Szilvi (GIS Lead).

---

## 🏁 Expected Outcome
A single validated `.gpkg` file per corridor that contains the full "Physical State" of the railway — geometry, elevations from BIM, terrain context from GIS — ready for the Risk Engine to consume in real-time.
