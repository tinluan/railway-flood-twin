# HEC-RAS Model Construction & Integration Guide
## For Ligne_400 (Himalayas Corridor) Railway Flood-Risk Digital Twin

This guide provides step-by-step GIS and hydraulic engineering instructions to build the HEC-RAS model and integrate it into the **SNCF Railway Flood-Twin** codebase.

---

## 1. Concept: How HEC-RAS Fits in the 4-Layer Architecture

The digital twin runs on a **15-minute operational cycle** structured as follows:

```
[Layer 1: Rainfall Ingestion] 
       │ (reads weather data / csv)
       ▼
[Layer 2: SWI Calculator] 
       │ (calculates soil moisture & sigmoid runoff coefficient)
       ▼
[Layer 3: HEC-RAS Simulation] ◄─── YOU ARE HERE
       │ (takes runoff/rain, computes unsteady 2D hydraulics)
       ▼
[Layer 4: Fragility & Alerts] 
         (extracts WSE, computes P_failure, triggers speed restrictions/halt)
```

To complete this loop, the twin needs a real HEC-RAS project file (`FloodTwin.prj`) saved in `model/hec_ras/` that can be triggered dynamically.

---

## 2. Horizontal & Vertical Alignment (CRITICAL)

Before opening HEC-RAS, make sure you align your spatial parameters.

1. **Horizontal CRS**: **EPSG:2154 (Lambert 93)**. Unit: Metres.
   * All staging GIS layers (` voie_fixed.gpkg`, `Buse_fixed.gpkg`, etc.) and the DTM raster (`dtm_fixed.tif`) use this coordinate reference system.
2. **Vertical Datum**: **NGF (Nivellement Général de la France)**. Unit: Metres.
   * The terrain heights in `dtm_fixed.tif` range from **~200m to ~250m NGF**.
   * Your HEC-RAS boundary conditions, cross-sections, and structures must use elevations referencing this datum.

### Creating the Projection File for HEC-RAS
HEC-RAS requires an ESRI `.prj` or WKT file to set the coordinate system in RAS Mapper.
Since your existing geospatial datasets (voie_fixed.gpkg or dtm_fixed.tif) are already mapped to EPSG:2154, you can let a GIS engine write a completely clean, native .prj sidecar file for you.  
1. Open QGIS and load either your vector tracks (voie_fixed.gpkg) or your terrain raster (dtm_fixed.tif).  
2. Right-click the layer in your layers panel and select Export ➔ Save Features As...
3. Change the format dropdown to ESRI Shapefile.
4. Make sure the CRS option is explicitly set to EPSG:2154 - RGF93 / Lambert-93.
5. Choose any temporary output folder and click OK.
6. Navigate to that output folder. QGIS will have generated a companion file ending in .prj.
7. Copy that .prj file, rename it to Lambert93.prj, and select it inside RAS Mapper.  

---

## 3. Modelling Strategy: 1D Reach vs. 2D Flow Area

You have two options for building the HEC-RAS geometry:

| Metric | 1D River Reach Model | 2D Flow Area Model (Recommended) |
| :--- | :--- | :--- |
| **Description** | Traditional river centerline with 1D cross-sections. | A 2D mesh covering the corridor buffer. |
| **Effort** | **High**: Must manually draw 120+ cross-sections perpendicular to the track axis for every asset. | **Low**: Draw one single boundary polygon, generate the mesh, and run. |
| **Accuracy** | Good for deep, defined channels. Poor for lateral overland runoff. | Excellent for overland flow, ditch overflows, and embankment wetting. |
| **Code Integration** | Fits the current legacy `hecras_bridge.py` COM calls. | Requires updating the bridge to read the Plan `.hdf` file using python (provided below). |

> [!TIP]
> **We strongly recommend the 2D Flow Area Model**.
> Drawing 120+ 1D cross-sections across a complex railway corridor is extremely tedious. A 2D mesh solves this, and we can easily query cell water surface elevations (WSE) by finding the closest 2D cell to each asset centroid.

---

## 4. Step-by-Step Model Building in HEC-RAS (v6.7)

### Step 4.1: Project Setup
1. Open HEC-RAS (v6.7).
2. Go to **File ➔ New Project**.
3. Save the project as **`FloodTwin.prj`** inside a new folder named `model/hec_ras/` under your project root:
   `c:\Users\ktstr\Documents\railway-flood-twin\model\hec_ras\FloodTwin.prj`.

### Step 4.2: RAS Mapper & Terrain Creation
1. Click the **RAS Mapper** button on the main toolbar (or go to **GIS Tools ➔ RAS Mapper**).
2. Set the coordinate reference system:
   * Go to **Project ➔ Set Project Spatial Reference System**.
   * Browse and select the `Lambert93.prj` file you created in Section 2. Click **Apply**.
3. Create the Terrain layer:
   * Right-click **Terrains** in the left panel ➔ **Create New RAS Terrain**.
   * Click the **+** (Add files) button.
   * Navigate to `data/staging/terrain/dtm_fixed.tif` and select it.
   * HEC-RAS will ask to convert/re-project the raster. Set the SRS to Project CRS.
   * Click **Create** to compile the terrain. HEC-RAS creates a `.hdf` terrain file.

### Step 4.3: Drawing the 2D Flow Area Geometry
1. In the left panel of RAS Mapper, right-click **Geometries** ➔ **Add New Geometry**. Name it `Corridor_Geometry`.
2. Expand `Corridor_Geometry` and right-click **2D Flow Areas** ➔ **Edit Geometry**.
3. Draw a polygon covering your railway corridor. It should surround the track line (`voie_fixed.gpkg`) and adjacent ditches with a buffer of at least 50m on each side.
4. Double-click the polygon to open its properties:
5. Set the **Cell Spacing** (DX and DY) to **5m** or **10m** (a 5m grid provides detailed resolution of embankments while keeping computation times under 10 seconds for a short corridor).
6. Click **Generate Computation Points on edit/close**.
7. Stop editing (Right-click **Geometries** ➔ **Stop Editing** ➔ **Save Changes**).

### Step 4.4: Boundary Conditions
To simulate the Cevenol storm, you will apply rain directly to the 2D mesh ("Rain on Grid").
1. In RAS Mapper (while editing the geometry), right-click **Boundary Condition Lines** ➔ **Edit Geometry**.
2. Draw boundary lines at:
   * **Upstream**: Where you want to simulate external water inflow.
   * **Downstream**: At the lowest points of the corridor boundaries to let water exit.
3. Name the downstream boundary line `Downstream_BC`. Double-click it and set its type to **Normal Depth** (enter a friction slope like `0.01`).

---

## 5. Unsteady Flow Data & Simulation Plan

1. Close RAS Mapper and return to the HEC-RAS main window.
2. Open the **Unsteady Flow Data** editor (Click the icon or go to **Edit ➔ Unsteady Flow Data**).
3. Set the boundary conditions:
   * For the 2D Flow Area (e.g. `2D Flow Area`):
     * Click **Precipitation** and enter the rainfall time series from `data/raw/rainfall_Ligne_400.csv` (the Cevenol storm has a peak of 40.9 mm/h at Hour 15).
   * For `Downstream_BC`:
     * Set to **Normal Depth** (friction slope = `0.01`).
4. Save the flow data as **`Cevenol_Storm_Flow`** (**File ➔ Save Flow Data**).
5. Open the **Unsteady Flow Simulation** window (Click the run icon or **Run ➔ Unsteady Flow Analysis**).
6. Select your Geometry (`Corridor_Geometry`) and Flow Data (`Cevenol_Storm_Flow`).
7. Check the boxes for **Geometry Preprocessor**, **Unsteady Flow Simulation**, and **Post Processor**.
8. Set the simulation time window to match your 48-hour scenario.
9. Save the Plan (**File ➔ Save Plan As**) and name it **`RealTime_Flood`** (Short ID: `p01`).
10. Click **Compute** to test the run. It should run successfully in a few seconds.

---

## 6. Code Integration: Updating the Python Bridge for 2D

Because HEC-RAS 2D results are written directly to a binary HDF5 file (`FloodTwin.p01.hdf`), reading this file using Python is **thousands of times faster** and far more stable than querying cells via the COM API.

Below is a production-grade script to replace the 1D logic in [hecras_bridge.py](file:///c:/Users/ktstr/Documents/railway-flood-twin/src/engine/hecras_bridge.py) with 2D extraction.

### Install HDF5 Support
Open a terminal in the project root and run:
```powershell
.\.conda\python.exe -m pip install h5py
```

### 2D Results Extractor Script (`src/engine/hecras_bridge_2d.py`)
This script locates the closest 2D cell center to each asset centroid (from `z_config.json`) and extracts the full WSE hydrograph directly from the HDF5 file:

```python
import os
import json
import numpy as np
import h5py
import geopandas as gpd
from pathlib import Path
from scipy.spatial import KDTree

from src.utils.paths import ProjectPaths

def extract_2d_wse_to_json(plan_hdf_path: str, output_path: str):
    """
    Extracts WSE time series from a HEC-RAS 2D HDF5 file for all assets in z_config.json.
    Maps each asset centroid to the nearest 2D computation cell center.
    """
    paths = ProjectPaths
    
    # 1. Load z_config.json to get the list of assets
    z_config_path = paths.PROCESSED / "z_config.json"
    if not z_config_path.exists():
        raise FileNotFoundError(f"z_config.json not found at {z_config_path}")
    
    with open(z_config_path, "r", encoding="utf-8") as f:
        z_config = json.load(f)
    
    # 2. Extract asset coordinates from GeoPackages
    asset_coords = {}
    gis_dir = paths.STAGING / "gis"
    
    # Mapping of asset type prefix in JSON to their GPKG file
    asset_files = {
        "Buse": gis_dir / "Buse_fixed.gpkg",
        "Dalot": gis_dir / "Dalot_fixed.gpkg",
        "Fosse terre": gis_dir / "Fossé terre_fixed.gpkg",
        "Fosse terre revetu": gis_dir / "Fossé terre revêtu_fixed.gpkg",
        "Talus Terre": gis_dir / "Talus Terre_fixed.gpkg",
        "Pont Rail": gis_dir / "Pont Rail_fixed.gpkg",
    }
    
    # Collect coordinates for each asset in EPSG:2154
    for prefix, file_path in asset_files.items():
        if not file_path.exists():
            continue
        gdf = gpd.read_file(file_path)
        for idx, row in gdf.iterrows():
            asset_id = f"{prefix}_{idx}"
            if asset_id in z_config:
                centroid = row.geometry.centroid
                asset_coords[asset_id] = (centroid.x, centroid.y)
                
    # Also load track segments from voie_segments.json
    voie_seg_path = paths.PROCESSED / "voie_segments.json"
    if voie_seg_path.exists():
        with open(voie_seg_path, "r") as f:
            segments = json.load(f)
        # Note: voie_segments coordinates on disk are stored in EPSG:4326.
        # We re-project centroids back to EPSG:2154 to match the HEC-RAS projection.
        seg_gdf = gpd.GeoDataFrame(
            segments, 
            geometry=[gpd.points_from_xy([s["lon"]], [s["lat"]])[0] for s in segments],
            crs="EPSG:4326"
        ).to_crs("EPSG:2154")
        
        for idx, row in seg_gdf.iterrows():
            asset_coords[row["name"]] = (row.geometry.x, row.geometry.y)

    print(f"Loaded coordinates for {len(asset_coords)} assets.")

    # 3. Read HEC-RAS 2D HDF5 Output File
    hdf_file = Path(plan_hdf_path).resolve()
    if not hdf_file.exists():
        raise FileNotFoundError(f"HEC-RAS HDF5 output not found: {hdf_file}")
        
    with h5py.File(hdf_file, "r") as hdf:
        # Navigate to 2D Flow Area cell coordinates
        # Assumes the first 2D Flow Area name in the geometry structure
        flow_area_names = list(hdf["/Geometry/2D Flow Areas/"].keys())
        if not flow_area_names:
            raise ValueError("No 2D Flow Areas found in the HEC-RAS project.")
        area_name = flow_area_names[0]
        
        cell_points = hdf[f"/Geometry/2D Flow Areas/{area_name}/Cell Points"][:] # Shape: (N_cells, 2)
        print(f"Found 2D Flow Area: '{area_name}' with {len(cell_points)} cells.")
        
        # Read Timestamps
        time_stamps_raw = hdf["/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time Date Stamp"][:]
        timestamps = [t.decode("utf-8") for t in time_stamps_raw]
        n_steps = len(timestamps)
        
        # Read Water Surface Elevation (WSE) array
        # Shape: (n_steps, N_cells)
        wse_dataset_path = f"/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/{area_name}/Water Surface"
        wse_data = hdf[wse_dataset_path][:] # Load into memory
        
        # 4. Build a KDTree of HEC-RAS 2D cell center coordinates for quick nearest-neighbour query
        tree = KDTree(cell_points)
        
        # 5. Extract time series for each asset
        wse_results = {}
        for asset_id, (ax, ay) in asset_coords.items():
            # Find the index of the nearest HEC-RAS cell
            dist, cell_idx = tree.query((ax, ay))
            
            # WSE time series for this cell
            wse_series = list(wse_data[:, cell_idx])
            # HEC-RAS uses NaN or -9999 for dry cells. Convert to base elevation.
            base_z = z_config[asset_id].get("yellow_z_m", 200.0) - 2.0
            wse_series_cleaned = [round(float(v), 2) if not np.isnan(v) and v > -9999 else round(base_z, 2) for v in wse_series]
            
            wse_results[asset_id] = {
                "timestamps": timestamps,
                "wse_m": wse_series_cleaned,
                "base_z_m": round(base_z, 2),
                "yellow_z_m": z_config[asset_id]["yellow_z_m"],
                "orange_z_m": z_config[asset_id]["orange_z_m"],
                "red_z_m": z_config[asset_id]["red_z_m"],
                "peak_wse_m": round(float(max(wse_series_cleaned)), 2),
                "peak_hour": int(np.argmax(wse_series_cleaned)),
            }
            
    # 6. Save results to data/processed/hecras_wse_results.json
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(wse_results, f, indent=2)
        
    print(f"Successfully exported WSE results to {out_file} for {len(wse_results)} assets.")

if __name__ == "__main__":
    # Test path inside project
    plan_hdf = "model/hec_ras/FloodTwin.p01.hdf"
    out_json = "data/processed/hecras_wse_results.json"
    
    if os.path.exists(plan_hdf):
        extract_2d_wse_to_json(plan_hdf, out_json)
    else:
        print(f"HDF file not found at {plan_hdf}. Please run the simulation first.")
```

---

## 7. How to Verify Everything Works

Once the model is built and the script is set up, follow these steps to run a full cycle test:

1. **Place Project Files**: Ensure `FloodTwin.prj`, `FloodTwin.g01`, `FloodTwin.u01`, `FloodTwin.p01`, and `FloodTwin.p01.hdf` are in `model/hec_ras/`.
2. **Run HEC-RAS Runner**:
   ```powershell
   $env:PYTHONPATH = "."
   .\.conda\python.exe src/engine/hec_ras_runner.py
   ```
   This will open HEC-RAS and trigger the unsteady simulation.
3. **Run 2D Extraction**:
   Run the extractor script to update `hecras_wse_results.json` with the new simulated depths.
4. **Launch Dashboard**:
   ```powershell
   .\.conda\python.exe -m streamlit run src/dashboard/app_main.py
   ```
   Verify that moving the timeline slider updates the map points, charts, and table with the new water elevations computed by HEC-RAS!
