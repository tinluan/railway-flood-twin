import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import json
import time

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.paths import paths

st.set_page_config(page_title="RailTwin Flood | SNCF Standard", layout="wide")

import json as _json, base64 as _base64

def _b64_style(style_dict):
    """Encode a GL style dict as a base64 data-URL (bypasses Streamlit map_style type check)."""
    return f"data:application/json;base64,{_base64.b64encode(_json.dumps(style_dict).encode()).decode()}"

# ESRI World Hillshade — exact grey terrain basemap used by HEC-RAS Mapper
_HILLSHADE_STYLE_URL = _b64_style({
    "version": 8,
    "sources": {
        "esri-hillshade": {
            "type": "raster",
            "tiles": ["https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}.jpg"],
            "tileSize": 256,
            "attribution": "Tiles \u00a9 Esri"
        }
    },
    "layers": [{"id": "esri-hillshade", "type": "raster", "source": "esri-hillshade"}]
})

# CartoDB Positron (light street map, used for 3D mode)
_CARTODB_STYLE_URL = _b64_style({
    "version": 8,
    "sources": {
        "cartodb": {
            "type": "raster",
            "tiles": ["https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"],
            "tileSize": 256
        }
    },
    "layers": [{"id": "cartodb-layer", "type": "raster", "source": "cartodb"}]
})

# ============================================================
# DATA LOADING (cached for performance)
# ============================================================
@st.cache_data
def load_rainfall():
    rain_file = paths.RAW / "rainfall_Ligne_400.csv"
    if rain_file.exists():
        df = pd.read_csv(rain_file, parse_dates=["timestamp"])
        return df
    return pd.DataFrame({"timestamp": [], "intensity_mm_h": []})

@st.cache_data
def load_swi():
    swi_file = paths.PROCESSED / "swi_results.csv"
    if swi_file.exists():
        df = pd.read_csv(swi_file, parse_dates=["timestamp"])
        return df
    return pd.DataFrame()

@st.cache_data
def load_assets():
    import geopandas as gpd
    import warnings
    warnings.filterwarnings('ignore')
    GIS_PATH = paths.RAW.parent / "staging" / "gis"
    records = []
    configs = [
        ("Pont Rail (Bridge)",          GIS_PATH / "Pont Rail_fixed.gpkg", "Pont Rail"),
        ("Buse (Culvert)",              GIS_PATH / "Buse_fixed.gpkg", "Buse"),
        ("Dalot (Box Culvert)",         GIS_PATH / "Dalot_fixed.gpkg", "Dalot"),
        ("Fosse terre (Earth Ditch)",   GIS_PATH / "Fossé terre_fixed.gpkg", "Fosse terre"),
        ("Fosse terre revetu (Lined Ditch)", GIS_PATH / "Fossé terre revêtu_fixed.gpkg", "Fosse terre revetu"),
        ("Talus Terre (Embankment)",    GIS_PATH / "Talus Terre_fixed.gpkg", "Talus Terre"),
        ("Voie (Track)",                GIS_PATH / "voie_fixed.gpkg", "Voie"),
    ]
    for asset_type_label, path, base_id in configs:
        if not path.exists():
            continue
        gdf = gpd.read_file(path).to_crs("EPSG:4326")
        for idx, row in gdf.iterrows():
            pt = row.geometry.centroid
            std_name = f"{base_id}_{idx}"
            records.append({
                "asset_type": asset_type_label,
                "name": std_name,
                "lat": pt.y,
                "lon": pt.x,
            })
    return pd.DataFrame(records)

@st.cache_resource
def load_infra_layers():
    import geopandas as gpd
    import json
    import warnings
    warnings.filterwarnings('ignore')
    GIS_PATH = paths.RAW.parent / "staging" / "gis"
    results = []
    infra_configs = [
        ("Voie (Track)",              GIS_PATH / "voie_fixed.gpkg",                        [220, 30,  30,  220], 4),
        ("Talus (Embankment)",        GIS_PATH / "Talus Terre_fixed.gpkg",                 [139, 90,  43,  160], 2),
        ("Fosse terre revetu",        GIS_PATH / "Fossé terre revêtu_fixed.gpkg",          [30, 100, 200, 200], 2),
        ("Fosse terre",               GIS_PATH / "Fossé terre_fixed.gpkg",                 [30,  80, 170, 180], 2),
        ("Drainage longitudinal",     GIS_PATH / "Drainage_longitudinal_à_ciel_ouvert_fixed.gpkg", [60, 140, 220, 180], 1),
    ]
    for name, path, color, width in infra_configs:
        if not path.exists():
            continue
        try:
            gdf = gpd.read_file(path).to_crs("EPSG:4326")
            geojson_str = gdf.to_json()
            geojson_dict = json.loads(geojson_str)
            results.append({
                "geojson": geojson_dict,
                "color": color,
                "width": width,
            })
        except Exception as e:
            print(f"Warning: Could not load {name}: {e}")
    return results

@st.cache_data
def load_cross_sections():
    cs_file = paths.PROCESSED / "cross_sections.json"
    if cs_file.exists():
        with open(cs_file, "r") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_z_config():
    z_file = paths.PROCESSED / "z_config.json"
    if z_file.exists():
        with open(z_file, "r") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_z_config_grouped():
    """Load the F5 grouped z_config (21 corridor sections with track-talus + drainage groups)."""
    z_file = paths.PROCESSED / "z_config_grouped.json"
    if z_file.exists():
        with open(z_file, "r") as f:
            return json.load(f)
    return {}

def get_active_hydrology_data(selected_plan, is_real_hecras, hecras_timestamps, n_steps, df_swi_base):
    """Generates or loads the active rainfall and SWI DataFrame based on selection."""
    import datetime

    if "P02_DEMO" in selected_plan:
        # ─────────────────────────────────────────────────────────────────
        # Extreme Design Storm: Synthetic Cevenol Category-3 scenario
        # 127 timesteps x 10 min = 21.2 hours, total rainfall ~220 mm
        # Hyetograph mirrors the WSE wave injected into PostProcessing_demo.hdf:
        #   Quiet onset (0–2h) → storm onset (2–5h) → main burst (5–12h, peak 55mm/h)
        #   → secondary peak (12–16h) → recession (16–21h)
        # ─────────────────────────────────────────────────────────────────
        DEMO_HOURLY_RAIN = [
            # H0  H1   H2    H3    H4    H5    H6    H7    H8    H9
            0.0,  0.0,  1.2,  4.5,  8.0,  18.0, 32.0, 48.0, 55.0, 50.0,
            # H10  H11  H12   H13   H14   H15   H16   H17   H18   H19
            38.0, 22.0, 28.0, 30.0, 18.0,  8.0,  4.0,  1.8,  0.6,  0.2,
            # H20  H21 (partial)
            0.1,   0.0,
        ]

        base_dt = datetime.datetime(2025, 9, 21, 7, 0)
        interval_h = 10 / 60.0   # 10-minute steps

        T = 240.0
        C = 0.5 ** (interval_h / T)
        swi_val = 0.0
        C_min, C_max, k, SWI_mid = 0.1, 0.9, 0.05, 150.0

        records = []
        for idx in range(127):
            dt = base_dt + datetime.timedelta(minutes=10 * idx)
            hours_elapsed = idx * interval_h
            hour_idx = int(hours_elapsed)
            intensity = DEMO_HOURLY_RAIN[hour_idx] if hour_idx < len(DEMO_HOURLY_RAIN) else 0.0

            swi_val = (intensity * interval_h) + swi_val * C
            runoff_coeff = C_min + (C_max - C_min) / (1 + np.exp(-k * (swi_val - SWI_mid)))
            active_runoff = intensity * runoff_coeff

            records.append({
                "timestamp":        dt,
                "intensity_mm_h":   intensity,
                "swi_mm":           swi_val,
                "runoff_coeff":     runoff_coeff,
                "active_runoff_mm": active_runoff,
            })
        return pd.DataFrame(records)

    elif is_real_hecras and "P02" in selected_plan:
        # Historical Showcase (Sept 2025 Cevenol storm)
        p02_hourly_rain = [0.0, 0.1, 0.8, 0.0, 0.3, 1.4, 6.7, 15.1, 5.8, 6.3,
                            4.3, 2.8, 1.0, 2.3, 9.8, 3.0, 3.7, 1.9, 1.6, 3.9,
                            2.5, 0.5]
        records = []
        try:
            start_dt = datetime.datetime.strptime(hecras_timestamps[0], "%d%b%Y %H:%M:%S")
        except Exception:
            start_dt = datetime.datetime(2025, 9, 21, 7, 0)

        T = 240.0
        C = 0.5 ** ((10/60) / T) # 10-minute interval
        swi_val = 0.0

        C_min = 0.1
        C_max = 0.9
        k = 0.05
        SWI_mid = 150.0

        for idx, ts_str in enumerate(hecras_timestamps):
            try:
                dt = datetime.datetime.strptime(ts_str, "%d%b%Y %H:%M:%S")
            except Exception:
                dt = start_dt + datetime.timedelta(minutes=10*idx)

            hours_elapsed = (dt - start_dt).total_seconds() / 3600.0
            hour_idx = int(hours_elapsed)
            intensity = p02_hourly_rain[hour_idx] if hour_idx < len(p02_hourly_rain) else 0.0

            swi_val = (intensity * (10/60.0)) + swi_val * C
            runoff_coeff = C_min + (C_max - C_min) / (1 + np.exp(-k * (swi_val - SWI_mid)))
            active_runoff = intensity * runoff_coeff

            records.append({
                "timestamp": dt,
                "intensity_mm_h": intensity,
                "swi_mm": swi_val,
                "runoff_coeff": runoff_coeff,
                "active_runoff_mm": active_runoff
            })
        return pd.DataFrame(records)

        
    elif is_real_hecras and "P01" in selected_plan:
        # Design Storm (100mm/1h)
        records = []
        import datetime
        try:
            start_dt = datetime.datetime.strptime(hecras_timestamps[0], "%d%b%Y %H:%M:%S")
        except Exception:
            start_dt = datetime.datetime(2026, 3, 30, 13, 0)
            
        T = 240.0
        C = 0.5 ** ((5/60) / T) # 5-minute interval
        swi_val = 0.0
        
        C_min = 0.1
        C_max = 0.9
        k = 0.05
        SWI_mid = 150.0
        
        for idx, ts_str in enumerate(hecras_timestamps):
            try:
                dt = datetime.datetime.strptime(ts_str, "%d%b%Y %H:%M:%S")
            except Exception:
                dt = start_dt + datetime.timedelta(minutes=5*idx)
            
            hours_elapsed = (dt - start_dt).total_seconds() / 3600.0
            intensity = 100.0 if hours_elapsed <= 1.0 else 0.0
            
            swi_val = (intensity * (5/60.0)) + swi_val * C
            runoff_coeff = C_min + (C_max - C_min) / (1 + np.exp(-k * (swi_val - SWI_mid)))
            active_runoff = intensity * runoff_coeff
            
            records.append({
                "timestamp": dt,
                "intensity_mm_h": intensity,
                "swi_mm": swi_val,
                "runoff_coeff": runoff_coeff,
                "active_runoff_mm": active_runoff
            })
        return pd.DataFrame(records)
        
    else:
        return df_swi_base

df_rain   = load_rainfall()
df_swi_base = load_swi()
cs_data   = load_cross_sections()
all_assets = load_assets()
infra_data = load_infra_layers()
z_config         = load_z_config()
z_config_grouped = load_z_config_grouped()

# --- Replace monolithic Voie_0 with segmented track sections ---
voie_seg_file = paths.PROCESSED / "voie_segments.json"
if voie_seg_file.exists():
    with open(voie_seg_file, "r") as f:
        voie_segments = json.load(f)
    # Remove old Voie_0 row(s) from all_assets
    all_assets = all_assets[~all_assets["name"].str.startswith("Voie_")]
    # Add each segment as a separate asset row
    seg_rows = pd.DataFrame(voie_segments)[["name", "asset_type", "lat", "lon"]]
    all_assets = pd.concat([all_assets, seg_rows], ignore_index=True)

@st.cache_data
def load_wse_results(plan_key="synthetic"):
    """Load WSE results for the selected HEC-RAS plan.
    Plans: 'synthetic' (48h), 'p01' (R100_1HR, 13 steps), 'p02' (21092025, 127 steps)
    """
    plan_files = {
        "Active Simulation (Latest Recomputed)": paths.PROCESSED / "hecras_wse_results.json",
        "synthetic": paths.PROCESSED / "hecras_wse_results.json",
        "P01: R100_1HR (100mm rainfall storm, 1h)": paths.PROCESSED / "hecras_wse_p01_dashboard.json",
        "P02: 21SEP2025 (Historical event, 21h)": paths.PROCESSED / "hecras_wse_p02_dashboard.json",
        "P02_DEMO: Synthetic Demonstration Storm": paths.PROCESSED / "hecras_wse_demo_showcase.json",
    }
    wse_file = plan_files.get(plan_key, plan_files["Active Simulation (Latest Recomputed)"])
    if wse_file.exists():
        with open(wse_file, "r") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_flood_timesteps():
    flood_file = paths.PROCESSED / "synthetic_flood_timesteps.json"
    if flood_file.exists():
        with open(flood_file, "r") as f:
            return json.load(f)
    return {}

flood_timesteps = load_flood_timesteps()

# ============================================================
# TITLE & SIDEBAR
# ============================================================
st.title("RailTwin Flood: Digital Twin Decision Support")
st.markdown("**SNCF Professional Standard** - Forecast Simulation Mode | HEC-RAS 2D Integration")

st.sidebar.header("Control Panel")
corridor = st.sidebar.selectbox("Corridor", ["L752 PK534 (South Head Tartaiguille, LGV)"])

# ============================================================
# F1: DUAL-MODE DASHBOARD (Live Monitoring vs Historical Showcase)
# ============================================================
st.sidebar.divider()
st.sidebar.subheader("Operational Mode")
app_mode = st.sidebar.radio(
    "Select Mode",
    options=["🔴 Historical Showcase (Sept 2025)", "⚡ Synthetic Demonstration Storm", "🟢 Live Monitoring"],
    index=0,
    help="Switch between the historical Cevenol storm showcase, synthetic demonstration storm showcase, and real-time weather monitoring."
)

if app_mode == "🔴 Historical Showcase (Sept 2025)":
    # --- Showcase Mode: Lock to Plan 2 (Historical Sept 2025 event) ---
    st.sidebar.info("Showcasing the September 21, 2025 Cevenol flood event (Plan 2: 21h, 127 timesteps) using real model results.")
    selected_plan = "P02: 21SEP2025 (Historical event, 21h)"
    is_real_hecras = True
    data_source = "Demo (48h Cevenol)"  # Use demo rainfall data for SWI context
elif app_mode == "⚡ Synthetic Demonstration Storm":
    # --- Synthetic Demonstration Storm: Lock to custom demo results ---
    st.sidebar.warning("Showcasing all warning statuses (GREEN, YELLOW, ORANGE, RED) with a custom generated flood event.")
    selected_plan = "P02_DEMO: Synthetic Demonstration Storm"
    is_real_hecras = True
    data_source = "Demo (48h Cevenol)"  # Use demo rainfall data for SWI context
else:
    # --- Live Mode: Full control panel ---
    st.sidebar.success("Monitoring live meteorological updates.")
    data_source = st.sidebar.radio(
        "Rainfall Source",
        options=["Demo (48h Cevenol)", "Live Forecast (Open-Meteo)"],
        index=0,
        help="Demo uses a static 48h flash flood scenario. Live uses real forecast data."
    )

    if st.sidebar.button("🔄 Fetch & Recompute Cycle"):
        with st.spinner("Running 15-min Operational Cycle (Forced HEC-RAS)..."):
            from src.engine.pipeline_orchestrator import PipelineOrchestrator
            orc = PipelineOrchestrator()
            source_mode = "live" if "Live" in data_source else "demo"
            result = orc.run_cycle(source_mode=source_mode, force_hecras=True)
            st.cache_data.clear()
            st.sidebar.success(f"Cycle completed! Peak SWI: {result['peak_swi_mm']} mm")
            time.sleep(1)
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("HEC-RAS Scenario")
    hecras_plan_options = [
        "Active Simulation (Latest Recomputed)",
        "P02: 21SEP2025 (Historical event, 21h)",
        "P01: R100_1HR (100mm rainfall storm, 1h)",
    ]
    selected_plan = st.sidebar.selectbox(
        "Simulation Plan",
        hecras_plan_options,
        help="Select a simulation plan. 'Active Simulation' shows the latest live/demo cycle run results."
    )
    is_real_hecras = selected_plan in [
        "Active Simulation (Latest Recomputed)",
        "P02: 21SEP2025 (Historical event, 21h)",
        "P01: R100_1HR (100mm rainfall storm, 1h)"
    ]

wse_results = load_wse_results(selected_plan)

# --- Asset Filter ---
ALL_ASSET_TYPES = [
    "Buse (Culvert)", "Dalot (Box Culvert)",
    "Fosse terre (Earth Ditch)", "Fosse terre revetu (Lined Ditch)",
    "Talus Terre (Embankment)", "Voie (Track)",
    "Pont Rail (Bridge)",
]
asset_types = st.sidebar.multiselect(
    "Show Asset Types",
    ALL_ASSET_TYPES,
    default=ALL_ASSET_TYPES
)

st.sidebar.divider()
st.sidebar.subheader("Map Visual Settings")
map_overlay_layer = st.sidebar.selectbox(
    "HEC-RAS 2D Flow Overlay",
    [
        "Water Depth",
        "Water Surface Elevation (WSE)",
        "Flow Velocity",
        "None",
    ],
    index=0,
    help="Select the HEC-RAS 2D model variable to show as an animated overlay on the map."
)

map_basemap = st.sidebar.selectbox(
    "Map Basemap Style",
    ["Terrain Hillshade", "CartoDB Light"],
    index=0,
    help="Toggle between shaded relief terrain elevation and simple light cartography."
)

# ============================================================
# TIME SLIDER & PLAY BUTTON (F2: Automatic Timeline Animation)
# ============================================================
# Determine timestep count from WSE data source
if is_real_hecras and wse_results:
    # Find the first dictionary value containing the WSE series (skips string metadata keys like "plan")
    asset_data = next((v for k, v in wse_results.items() if isinstance(v, dict) and "wse_m" in v), {})
    n_steps = len(asset_data.get("wse_m", []))
    
    # Use global timesteps list if available, otherwise fall back to asset-specific list
    if isinstance(wse_results.get("timesteps"), list):
        hecras_timestamps = wse_results["timesteps"]
    else:
        hecras_timestamps = asset_data.get("timestamps", [])
else:
    n_steps = len(df_rain) if len(df_rain) > 0 else 48
    hecras_timestamps = []

# --- Dynamic Hydrology Data Routing ---
df_swi = get_active_hydrology_data(selected_plan, is_real_hecras, hecras_timestamps, n_steps, df_swi_base)
df_rain = df_swi
n_steps = len(df_swi)

st.sidebar.divider()
st.sidebar.subheader("Forecast Timeline")

# --- Play / Pause Animation Controls ---
col_play, col_speed = st.sidebar.columns([1, 1])
with col_play:
    is_playing = st.toggle("▶ Play", value=False)
    loop_animation = st.checkbox("Loop", value=False)
with col_speed:
    animation_speed_ms = st.select_slider(
        "Speed",
        options=[200, 500, 1000, 2000],
        value=500,
        format_func=lambda x: f"{x}ms",
    )

if "timeline_idx" not in st.session_state:
    st.session_state["timeline_idx"] = 0

if n_steps == 216:
    # Live Forecast: 168h history (past) + 48h forecast (future)
    options = []
    for i in range(216):
        rel_h = i - 168
        label = f"T{rel_h}h" if rel_h < 0 else ("T+0h (Current)" if rel_h == 0 else f"T+{rel_h}h")
        if hecras_timestamps and i < len(hecras_timestamps):
            label += f" | {hecras_timestamps[i]}"
        options.append(label)
elif n_steps == 48:
    # Demo Cevenol Storm: 24h warm-up (past) + 24h event (future)
    options = []
    for i in range(48):
        rel_h = i - 24
        label = f"T{rel_h}h" if rel_h < 0 else ("T+0h (Current)" if rel_h == 0 else f"T+{rel_h}h")
        if hecras_timestamps and i < len(hecras_timestamps):
            label += f" | {hecras_timestamps[i]}"
        options.append(label)
elif is_real_hecras and hecras_timestamps:
    options = hecras_timestamps
else:
    options = [f"T+{i}h" for i in range(n_steps)]

# Ensure state is within bounds when switching plans
if st.session_state["timeline_idx"] >= n_steps:
    st.session_state["timeline_idx"] = max(n_steps - 1, 0)

selected_time = st.sidebar.select_slider(
    "Forecast Timeline",
    options=options,
    value=options[st.session_state["timeline_idx"]],
    help="Drag this slider to see the predicted state of your railway at each timestep."
)

# Sync the index back
t_idx = options.index(selected_time)
if t_idx != st.session_state["timeline_idx"]:
    st.session_state["timeline_idx"] = t_idx

# --- Compute current state at time t_idx ---
if len(df_swi) > 0 and t_idx < len(df_swi):
    current_rain = df_swi.iloc[t_idx]["intensity_mm_h"]
    current_swi = df_swi.iloc[t_idx]["swi_mm"]
    current_runoff_c = df_swi.iloc[t_idx]["runoff_coeff"]
    current_runoff_mm = df_swi.iloc[t_idx]["active_runoff_mm"]
    current_ts = df_swi.iloc[t_idx]["timestamp"]
    if t_idx > 0:
        prev_swi = df_swi.iloc[t_idx - 1]["swi_mm"]
        delta_swi = current_swi - prev_swi
    else:
        delta_swi = 0
else:
    current_rain = 0
    current_swi = 0
    current_runoff_c = 0
    current_runoff_mm = 0
    current_ts = "N/A"
    delta_swi = 0

# --- Compute risk per asset using ACTUAL WSE from hecras_wse_results.json ---
# Physics: one corridor-wide WSE at each timestep. Each asset's risk is
# determined by comparing its elevation thresholds against the actual water level.
def compute_risk_at_t(row, t_idx, wse_results, config):
    """Per-asset risk using actual WSE from synthetic HEC-RAS results.
    
    Logic:
    1. Get this asset's WSE at timestep t_idx from wse_results.
    2. Check if the asset is dry (water depth <= 2cm). If dry, risk is 0.
    3. If absolute thresholds in config are lower than the ground elevation (due to mismatch),
       fallback to relative depth thresholds (Yellow: 5cm, Orange: 20cm, Red: 50cm).
    4. Otherwise, compare WSE against the asset's Yellow/Orange/Red Z-thresholds.
    """
    asset_id = row["name"]
    asset_config = config.get(asset_id)
    
    if not asset_config:
        return 0  # No config = no risk evaluation possible
    
    # Get the WSE for this asset at this timestep
    asset_wse_data = wse_results.get(asset_id, {})
    wse_series = asset_wse_data.get("wse_m", [])
    
    if wse_series and t_idx < len(wse_series):
        current_wse = wse_series[t_idx]
    else:
        return 0
    
    base_z = asset_wse_data.get("base_z_m", 0.0)
    
    # If the asset is dry (depth <= 2cm), risk is 0%
    if current_wse <= base_z + 0.02:
        return 0
        
    yellow_z = asset_config["yellow_z_m"]
    orange_z = asset_config["orange_z_m"]
    red_z = asset_config["red_z_m"]
    
    # If the ground elevation is above the red threshold (database mismatch),
    # fall back to depth-based relative thresholds.
    if base_z > red_z:
        depth = current_wse - base_z
        if depth >= 0.5:
            return 100  # RED: over 50cm water depth
        elif depth >= 0.2:
            frac = (depth - 0.2) / 0.3
            return int(75 + frac * 24)  # ORANGE: 20cm - 50cm
        elif depth >= 0.05:
            frac = (depth - 0.05) / 0.15
            return int(50 + frac * 24)  # YELLOW: 5cm - 20cm
        else:
            frac = depth / 0.05
            return int(frac * 25)  # GREEN: <5cm
    
    # Risk Hierarchy: compare actual WSE against thresholds
    if current_wse >= red_z:
        return 100  # RED: asset fully submerged
    elif current_wse >= orange_z:
        # Scale 75-99 within orange zone
        frac = (current_wse - orange_z) / max(red_z - orange_z, 0.1)
        return int(75 + frac * 24)
    elif current_wse >= yellow_z:
        # Scale 50-74 within yellow zone
        frac = (current_wse - yellow_z) / max(orange_z - yellow_z, 0.1)
        return int(50 + frac * 24)
    else:
        # GREEN: water below drainage capacity
        if current_wse > base_z:
            frac = (current_wse - base_z) / max(yellow_z - base_z, 0.1)
            return int(frac * 25)
        return 0

# --- CAP International Standard Alert Levels ---
# GREEN 0-25% | YELLOW 25-50% | ORANGE 50-75% | RED 75-100%
CAP_COLORS_RGBA = {
    "GREEN":  [76, 175, 80, 200],    # #4CAF50
    "YELLOW": [255, 235, 59, 200],   # #FFEB3B
    "ORANGE": [255, 152, 0, 200],    # #FF9800
    "RED":    [244, 67, 54, 200],    # #F44336
}
CAP_COLORS_HEX = {
    "GREEN": "#4CAF50", "YELLOW": "#FFEB3B", "ORANGE": "#FF9800", "RED": "#F44336",
}

def risk_to_cap_level(r):
    if r >= 75: return "RED"
    if r >= 50: return "ORANGE"
    if r >= 25: return "YELLOW"
    return "GREEN"

if not all_assets.empty:
    # Compute WSE and depth per asset at current timestep
    def get_wse_depth(row):
        asset_id = row["name"]
        asset_wse_data = wse_results.get(asset_id, {})
        wse_series = asset_wse_data.get("wse_m", [])
        if wse_series and t_idx < len(wse_series):
            wse = wse_series[t_idx]
            base_z = asset_wse_data.get("base_z_m", 0.0)
            depth = max(0.0, wse - base_z)
            return pd.Series([wse, depth])
        return pd.Series([None, None])
        
    all_assets[["wse_val", "depth_val"]] = all_assets.apply(get_wse_depth, axis=1)

    all_assets["risk_level"] = all_assets.apply(
        lambda r: compute_risk_at_t(r, t_idx, wse_results, z_config), axis=1
    )
    all_assets["cap_level"] = all_assets["risk_level"].apply(risk_to_cap_level)
    all_assets["color"] = all_assets["cap_level"].apply(lambda lv: CAP_COLORS_RGBA[lv])
    
    # Formatted strings for unified PyDeck tooltip
    all_assets["wse_m"] = all_assets["wse_val"].apply(lambda w: f"{w:.2f}" if pd.notna(w) else "N/A")
    all_assets["depth_m"] = all_assets["depth_val"].apply(lambda d: f"{d:.2f}" if pd.notna(d) else "N/A")
    all_assets["tooltip_risk"] = all_assets["risk_level"].apply(lambda r: f"{r}%")

# Filter by selected asset types
filtered = all_assets[all_assets["asset_type"].isin(asset_types)] if (asset_types and not all_assets.empty) else all_assets

# Determine overall alert level
if not filtered.empty:
    max_risk = filtered["risk_level"].max()
else:
    max_risk = 0

# ============================================================
# SIDEBAR: Current Timestamp Display
# ============================================================
st.sidebar.divider()
st.sidebar.metric("Current Time", str(current_ts)[:16] if current_ts != "N/A" else "N/A")
st.sidebar.metric("Rain Intensity", f"{current_rain:.1f} mm/h")

# ============================================================
# MAIN LAYOUT
# ============================================================
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live Risk Map -- Real Infrastructure")

    import pydeck as pdk

    if not filtered.empty:
        center_lat = filtered["lat"].mean()
        center_lon = filtered["lon"].mean()

        risk_layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered,
            get_position=["lon", "lat"],
            get_radius=12,
            radius_units="pixels",
            radius_min_pixels=8,
            radius_max_pixels=18,
            get_fill_color="color",
            get_line_color=[255, 255, 255, 200],
            stroked=True,
            line_width_min_pixels=1,
            pickable=True,
            auto_highlight=True,
        )

        # --- 2D Flow Map Overlay (F4) ---
        flow_bitmap_layer = None
        flow_tooltip_layer = None
        hdf5_plan_files = {
            "Active Simulation (Latest Recomputed)": paths.RAW.parent / "hec-ras" / "CAPSTONE_JN_L752_PK.p02.hdf",
            "P01: R100_1HR (100mm rainfall storm, 1h)": paths.RAW.parent / "hec-ras" / "CAPSTONE_JN_L752_PK.p01.hdf",
            "P02: 21SEP2025 (Historical event, 21h)": paths.RAW.parent / "hec-ras" / "CAPSTONE_JN_L752_PK.p02.hdf",
            "P02_DEMO: Synthetic Demonstration Storm": paths.RAW.parent / "hec-ras" / "21092025" / "PostProcessing_demo.hdf",
        }
        hdf5_path = hdf5_plan_files.get(selected_plan)

        # Build overlay layer based on sidebar choice
        wse_min_val = None
        wse_max_val = None
        if hdf5_path and hdf5_path.exists() and map_overlay_layer != "None":
            try:
                from src.engine.hecras_hdf5_reader import extract_downsampled_flow_data, rasterize_flow_to_bitmap

                # 1. Generate smooth raster overlay using BitmapLayer
                raster_data = rasterize_flow_to_bitmap(
                    hdf5_path=hdf5_path,
                    timestep_idx=t_idx,
                    variable=map_overlay_layer,
                    grid_size=512
                )
                if raster_data and raster_data.get("img_b64"):
                    from pydeck.types import String
                    flow_bitmap_layer = pdk.Layer(
                        "BitmapLayer",
                        image=String(f"data:image/png;base64,{raster_data['img_b64']}"),
                        bounds=raster_data["bounds"],
                        opacity=0.7,
                        pickable=False,
                    )
                    wse_min_val = raster_data.get("vmin")
                    wse_max_val = raster_data.get("vmax")

                # 2. Extract downsampled point cloud for transparent tooltip layer
                flow_data = extract_downsampled_flow_data(
                    hdf5_path=hdf5_path,
                    timestep_idx=t_idx,
                    max_cells=5000,
                    depth_threshold=0.02,
                    dry_sample_rate=50
                )
                if flow_data and flow_data.get("points"):
                    df_flow = pd.DataFrame(flow_data["points"])

                    df_flow["name"] = "2D Mesh Cell"
                    df_flow["asset_type"] = f"2D Flow Area ({map_overlay_layer})"
                    df_flow["tooltip_risk"] = "N/A"
                    df_flow["velocity_ms_val"] = df_flow["velocity_ms"]
                    df_flow["velocity_ms"] = df_flow["velocity_ms_val"].apply(lambda v: f"{v:.2f}")
                    df_flow["depth_m"] = df_flow["depth_m"].apply(lambda d: f"{d:.2f}")
                    df_flow["wse_m"] = df_flow["wse_m"].apply(lambda w: f"{w:.2f}" if pd.notna(w) else "N/A")

                    flow_tooltip_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=df_flow,
                        get_position=["lon", "lat"],
                        get_radius=20,
                        radius_units="meters",
                        get_fill_color=[0, 0, 0, 0],  # fully transparent
                        pickable=True,
                    )
            except Exception as e:
                st.warning(f"Could not load 2D flow mapping: {e}")

        # Format asset fields to match overlay properties for unified hover tooltip
        if not filtered.empty:
            filtered["velocity_ms"] = "N/A"

        # Unified tooltip for both layers
        tooltip = {
            "html": (
                "<b>{name}</b><br/>"
                "Type: {asset_type}<br/>"
                "Asset Risk: {tooltip_risk}<br/>"
                "Water Depth: {depth_m} m<br/>"
                "WSE: {wse_m} m<br/>"
                "Velocity: {velocity_ms} m/s"
            ),
            "style": {"backgroundColor": "#1a1a2e", "color": "white", "fontSize": "13px"}
        }

        # Build infrastructure GeoJson layers (wrapped for safety)
        infra_layers = []
        try:
            for item in infra_data:
                infra_layers.append(pdk.Layer(
                    "GeoJsonLayer",
                    data=item["geojson"],
                    get_line_color=item["color"],
                    get_fill_color=[*item["color"][:3], 60],
                    line_width_min_pixels=item["width"],
                    pickable=False,
                ))
        except Exception:
            infra_layers = []

        # Basemap selection:
        #   Terrain Hillshade → ESRI World Hillshade (grey terrain, same as HEC-RAS Mapper) + 2D flat
        #   CartoDB Light     → CartoDB Positron raster + 3D perspective
        # Both delivered as base64 GL style (no map_provider needed, avoids indexOf crash)
        is_hecras_style = (map_basemap == "Terrain Hillshade")
        basemap_style_url = _HILLSHADE_STYLE_URL if is_hecras_style else _CARTODB_STYLE_URL

        try:
            deck_layers = []
            deck_layers.extend(infra_layers)
            if flow_bitmap_layer:
                deck_layers.append(flow_bitmap_layer)
            if flow_tooltip_layer:
                deck_layers.append(flow_tooltip_layer)
            deck_layers.append(risk_layer)

            # HEC-RAS mode: flat 2D top-down view. CartoDB mode: 3D perspective.
            # key= forces a full remount when basemap changes, so pitch/bearing are re-applied.
            st.pydeck_chart(pdk.Deck(
                map_style=basemap_style_url,
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=13,
                    pitch=0 if is_hecras_style else 30,
                    bearing=0 if is_hecras_style else -10,
                ),
                layers=deck_layers,
                tooltip=tooltip,
            ), key=f"map_{map_basemap}")

            # --- Inline Map Legend (F4.7) ---
            if map_overlay_layer != "None":
                if map_overlay_layer == "Water Depth":
                    legend_html = """
                    <div style='display:flex; align-items:center; gap:10px; padding:6px 12px; background:#1e293b; border-radius:6px; margin-top:8px; border:1px solid #334155'>
                        <span style='color:white; font-size:12px; font-weight:bold'>Legend (Depth):</span>
                        <span style='color:#94a3b8; font-size:11px'>0.0 m</span>
                        <div style='flex:1; width:150px; height:12px; border-radius:3px; background: linear-gradient(to right, rgb(173, 216, 230), rgb(65, 105, 225), rgb(75, 0, 130))'></div>
                        <span style='color:#94a3b8; font-size:11px'>2.0+ m</span>
                    </div>
                    """
                elif map_overlay_layer == "Water Surface Elevation (WSE)":
                    wmin_str = f"{wse_min_val:.2f} m" if wse_min_val is not None else "Min"
                    wmax_str = f"{wse_max_val:.2f} m" if wse_max_val is not None else "Max"
                    legend_html = f"""
                    <div style='display:flex; align-items:center; gap:10px; padding:6px 12px; background:#1e293b; border-radius:6px; margin-top:8px; border:1px solid #334155'>
                        <span style='color:white; font-size:12px; font-weight:bold'>Legend (WSE):</span>
                        <span style='color:#94a3b8; font-size:11px'>{wmin_str}</span>
                        <div style='flex:1; width:150px; height:12px; border-radius:3px; background: linear-gradient(to right, rgb(0, 200, 100), rgb(255, 215, 0), rgb(255, 140, 0), rgb(200, 0, 0))'></div>
                        <span style='color:#94a3b8; font-size:11px'>{wmax_str}</span>
                    </div>
                    """
                elif map_overlay_layer == "Water Depth (Max)":
                    legend_html = """
                    <div style='display:flex; align-items:center; gap:10px; padding:6px 12px; background:#1e293b; border-radius:6px; margin-top:8px; border:1px solid #334155'>
                        <span style='color:white; font-size:12px; font-weight:bold'>Legend (Depth Max):</span>
                        <span style='color:#94a3b8; font-size:11px'>0.2 m</span>
                        <div style='flex:1; width:150px; height:12px; border-radius:3px; background: linear-gradient(to right, rgb(173, 216, 230), rgb(65, 105, 225), rgb(75, 0, 130))'></div>
                        <span style='color:#94a3b8; font-size:11px'>3.0+ m</span>
                    </div>
                    """
                elif map_overlay_layer == "Channel Flooding (>0.5m)":
                    legend_html = """
                    <div style='display:flex; align-items:center; gap:10px; padding:6px 12px; background:#1e293b; border-radius:6px; margin-top:8px; border:1px solid #334155'>
                        <span style='color:white; font-size:12px; font-weight:bold'>Legend (Channel Flood):</span>
                        <span style='color:#94a3b8; font-size:11px'>&gt;0.5 m</span>
                        <div style='flex:1; width:150px; height:12px; border-radius:3px; background: linear-gradient(to right, rgb(173, 216, 230), rgb(65, 105, 225), rgb(75, 0, 130))'></div>
                        <span style='color:#94a3b8; font-size:11px'>3.0+ m</span>
                    </div>
                    """
                else:  # Flow Velocity
                    legend_html = """
                    <div style='display:flex; align-items:center; gap:10px; padding:6px 12px; background:#1e293b; border-radius:6px; margin-top:8px; border:1px solid #334155'>
                        <span style='color:white; font-size:12px; font-weight:bold'>Legend (Velocity):</span>
                        <span style='color:#94a3b8; font-size:11px'>0.0 m/s</span>
                        <div style='flex:1; width:150px; height:12px; border-radius:3px; background: linear-gradient(to right, rgb(50, 205, 50), rgb(255, 165, 0), rgb(255, 69, 0), rgb(148, 0, 211))'></div>
                        <span style='color:#94a3b8; font-size:11px'>2.0+ m/s</span>
                    </div>
                    """
                st.markdown(legend_html, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Map rendering issue: {e}")

        # --- Top 5 Critical Assets Table ---
        st.subheader("Top 5 Critical Assets at T+{}h".format(t_idx))
        top5 = filtered.sort_values("risk_level", ascending=False).head(5)[
            ["name", "asset_type", "lat", "lon", "risk_level"]
        ].reset_index(drop=True)
        top5.columns = ["Asset ID", "Type", "Latitude", "Longitude", "Risk (%)"]

        # Color each Risk cell with fixed CAP-standard colors (matching map dots)
        def color_risk_cell(val):
            lv = risk_to_cap_level(val)
            bg = CAP_COLORS_HEX[lv]
            fg = "#000" if lv in ("GREEN", "YELLOW") else "#FFF"
            return f"background-color: {bg}; color: {fg}; font-weight: bold"

        st.dataframe(
            top5.style.map(color_risk_cell, subset=["Risk (%)"]),
            width="stretch"
        )
        # ============================================================
        # F5.4 — Section Group Alerts (Track-Talus + Drainage Roll-up)
        # ============================================================
        if z_config_grouped and wse_results:
            try:
                from src.engine.alert_dispatcher import AlertDispatcher
                _dispatcher = AlertDispatcher()
                group_alerts = _dispatcher.evaluate_all_groups(
                    z_config_grouped, wse_results, timestep_idx=t_idx
                )
                system_summary = _dispatcher.summarise_system(group_alerts)

                # --- System-wide banner ---
                overall_st = system_summary["overall_status"]
                banner_color = CAP_COLORS_HEX.get(overall_st, "#4CAF50")
                banner_fg = "#000" if overall_st in ("GREEN", "YELLOW") else "#FFF"
                directive_txt = system_summary["directive"]
                counts = system_summary["counts"]

                st.markdown(
                    f"""
                    <div style='margin-top:18px; padding:10px 16px; border-radius:8px;
                                background:{banner_color}; border:2px solid rgba(255,255,255,0.2)'>
                        <span style='color:{banner_fg}; font-size:14px; font-weight:bold'>
                            CORRIDOR STATUS: {overall_st} &mdash; {directive_txt}
                        </span>
                        <span style='color:{banner_fg}; font-size:12px; margin-left:16px'>
                            {counts['RED']} RED &bull; {counts['ORANGE']} ORANGE &bull;
                            {counts['YELLOW']} YELLOW &bull; {counts['GREEN']} GREEN
                        </span>
                    </div>""",
                    unsafe_allow_html=True
                )

                st.subheader("Corridor Section Group Alerts (T+{})".format(t_idx))

                # Build DataFrame from group alerts for display
                _group_rows = []
                for ga in group_alerts:
                    tt = ga["track_alert"]
                    n_drain_warn = sum(
                        1 for d in ga["drainage_alerts"]
                        if d["status"] in ("YELLOW", "ORANGE", "RED")
                    )
                    n_drain_total = len(ga["drainage_alerts"])
                    n_bridge_warn = sum(
                        1 for b in ga["bridge_alerts"]
                        if b["status"] in ("YELLOW", "ORANGE", "RED")
                    )

                    def status_to_emoji_label(status):
                        emojis = {
                            "RED": "🔴 RED",
                            "ORANGE": "🟠 ORANGE",
                            "YELLOW": "🟡 YELLOW",
                            "GREEN": "🟢 GREEN",
                        }
                        return emojis.get(status, status)

                    _group_rows.append({
                        "Section":        ga["group_id"],
                        "Overall":        status_to_emoji_label(ga["status"]),
                        "Track ID":       tt["track_id"],
                        "Track Status":   status_to_emoji_label(tt["status"]),
                        "Track WSE (m)":  tt["wse_m"],
                        "Red Z (m)":      tt.get("red_z_m", "-"),
                        "Track Margin (m)": tt.get("margin_m", 0.0),
                        "Drainage Alerts": f"{n_drain_warn}/{n_drain_total}",
                        "Bridge Alerts":  str(n_bridge_warn) if ga["bridge_alerts"] else "-",
                    })

                df_groups = pd.DataFrame(_group_rows)

                # Colour-map the Overall and Track Status columns
                def _color_status_cell(val):
                    clean_val = val.split()[-1] if isinstance(val, str) else val
                    c = CAP_COLORS_HEX.get(clean_val, "#4CAF50")
                    fg = "#000" if clean_val in ("GREEN", "YELLOW") else "#FFF"
                    return f"background-color:{c}; color:{fg}; font-weight:bold"

                def _color_margin_cell(val):
                    if isinstance(val, (int, float)):
                        if val > 0:
                            return "color: #ff4d4d; font-weight: bold" # red/orange warning text
                        else:
                            return "color: #2ecc71; font-weight: bold" # green safe text
                    return ""

                styled_groups = (
                    df_groups.style
                    .map(_color_status_cell, subset=["Overall", "Track Status"])
                    .map(_color_margin_cell, subset=["Track Margin (m)"])
                    .format({
                        "Track WSE (m)": "{:.2f}", 
                        "Red Z (m)": lambda v: f"{v:.2f}" if isinstance(v, float) else v,
                        "Track Margin (m)": lambda v: f"{v:+.2f} m" if isinstance(v, (int, float)) else v
                    })
                )
                st.dataframe(styled_groups, use_container_width=True)

                # --- Expandable detail per RED/ORANGE section ---
                critical = [ga for ga in group_alerts if ga["status"] in ("RED", "ORANGE")]
                if critical:
                    with st.expander(
                        f"{len(critical)} Critical Section(s) — Drainage & Bridge Detail", expanded=False
                    ):
                        for ga in critical:
                            col_h, col_d = st.columns([1, 3])
                            with col_h:
                                st_color = CAP_COLORS_HEX.get(ga["status"], "#4CAF50")
                                st_fg = "#FFF"
                                st.markdown(
                                    f"<div style='background:{st_color}; border-radius:6px; padding:8px; "
                                    f"text-align:center; color:{st_fg}; font-weight:bold'>"
                                    f"{ga['group_id']}<br>{ga['status']}<br>{ga['directive']}</div>",
                                    unsafe_allow_html=True
                                )
                            with col_d:
                                # Drainage detail
                                for da in ga["drainage_alerts"]:
                                    if da["status"] != "GREEN":
                                        da_c = CAP_COLORS_HEX.get(da["status"], "#4CAF50")
                                        da_fg = "#000" if da["status"] in ("GREEN", "YELLOW") else "#FFF"
                                        st.markdown(
                                            f"<span style='background:{da_c}; color:{da_fg}; border-radius:4px; "
                                            f"padding:2px 6px; font-size:11px; font-weight:bold'>{da['status']}</span> "
                                            f"<b>{da['id']}</b> ({da['type']}) &mdash; "
                                            f"WSE={da['wse_m']:.2f}m / Red@{da.get('red_z_m', '?')}m "
                                            f"(margin {da['margin_m']:+.2f}m)",
                                            unsafe_allow_html=True
                                        )
                                # Bridge detail
                                for br in ga["bridge_alerts"]:
                                    if br["status"] != "GREEN":
                                        br_c = CAP_COLORS_HEX.get(br["status"], "#4CAF50")
                                        br_fg = "#FFF"
                                        st.markdown(
                                            f"<span style='background:{br_c}; color:{br_fg}; border-radius:4px; "
                                            f"padding:2px 6px; font-size:11px; font-weight:bold'>{br['status']}</span> "
                                            f"<b>{br['id']}</b> ({br['type']}) &mdash; "
                                            f"WSE={br['wse_m']:.2f}m / Red@{br.get('red_z_m', '?')}m",
                                            unsafe_allow_html=True
                                        )
            except Exception as _ge:
                st.warning(f"Group alert panel error: {_ge}")
    else:
        st.warning("No assets selected. Use the sidebar filter to choose asset types.")

    # ============================================================
    # GLOBAL ASSET SELECTOR with HOTSPOT LOCK
    # ============================================================
    st.subheader("Asset-Specific Hydraulic Forecast")
    
    asset_options = filtered["name"].tolist() if not filtered.empty else []
    
    # Hotspot Lock: prevents auto-jumping when scrubbing the timeline
    lock_focus = st.checkbox("Lock Asset Focus", value=False, key="lock_focus",
                             help="Check to keep the selected asset fixed while moving the time slider.")
    
    if lock_focus and "locked_asset" in st.session_state and st.session_state["locked_asset"] in asset_options:
        critical_idx = asset_options.index(st.session_state["locked_asset"])
    else:
        critical_idx = 0
        if not filtered.empty and "risk_level" in filtered.columns:
            critical_name = filtered.sort_values("risk_level", ascending=False).iloc[0]["name"]
            if critical_name in asset_options:
                critical_idx = asset_options.index(critical_name)
    
    selected_asset = st.selectbox("Select Critical Asset to Analyze:", asset_options, index=critical_idx) if asset_options else None
    if selected_asset:
        st.session_state["locked_asset"] = selected_asset
    
    # Get dynamic thresholds
    z_yellow = 220.0
    z_orange = 220.5
    z_red = 221.5
    if selected_asset and z_config and selected_asset in z_config:
        z_yellow = z_config[selected_asset]["yellow_z_m"]
        z_orange = z_config[selected_asset]["orange_z_m"]
        z_red = z_config[selected_asset]["red_z_m"]

    # ============================================================
    # WSE CHART with TIME CURSOR — driven by per-asset HEC-RAS results
    # ============================================================
    fig = go.Figure()

    if len(df_swi) > 0 and selected_asset:
        timestamps = [str(t) for t in df_swi['timestamp']]

        # --- Load per-asset WSE from hecras_wse_results.json ---
        if selected_asset in wse_results:
            asset_wse_data = wse_results[selected_asset]
            wse = asset_wse_data['wse_m']
            base_z = asset_wse_data['base_z_m']
            if is_real_hecras and asset_wse_data.get('timestamps'):
                timestamps = asset_wse_data['timestamps']
        else:
            # Fallback: estimate from rain+runoff (for assets not in wse_results)
            base_z = z_yellow - 1.5
            wse = [base_z + ((r * 0.05) + (df_swi.iloc[i]["active_runoff_mm"] * 0.1))
                   for i, r in enumerate(df_swi['intensity_mm_h'])]

        # Clamp wse length to match timestamps
        wse = wse[:len(timestamps)]
        wse_max = max(wse)
        y_min = min(base_z - 1.0, min(wse) - 0.5)
        y_max = max(wse_max, z_red) + 1.0

        # Threshold Lines
        fig.add_trace(go.Scatter(x=timestamps, y=[z_red]*len(timestamps),
                                 name="RED: Voie Min",
                                 line=dict(color='red', dash='dash', width=2)))
        fig.add_trace(go.Scatter(x=timestamps, y=[z_orange]*len(timestamps),
                                 name="ORANGE: Talus Mean",
                                 line=dict(color='orange', dash='dash', width=2)))
        fig.add_trace(go.Scatter(x=timestamps, y=[z_yellow]*len(timestamps),
                                 name="YELLOW: Buse Max",
                                 line=dict(color='gold', dash='dot', width=2)))

        # Terrain Bottom (flat, asset-specific base)
        fig.add_trace(go.Scatter(x=timestamps, y=[base_z]*len(timestamps),
                                 name="Terrain Bottom",
                                 fill='tozeroy', fillcolor='rgba(139,90,43,0.15)',
                                 line=dict(color='saddlebrown', width=1)))

        # Water Surface Elevation (WSE)
        fig.add_trace(go.Scatter(x=timestamps, y=wse,
                                 name="WSE (Predicted)",
                                 line=dict(color='royalblue', width=3),
                                 fill='tonexty', fillcolor='rgba(65,105,225,0.25)'))

        # Vertical time cursor
        cursor_ts  = timestamps[t_idx]
        cursor_wse = wse[t_idx]
        fig.add_shape(
            type="line", x0=cursor_ts, x1=cursor_ts, y0=y_min, y1=y_max,
            line=dict(color="darkgrey", width=2, dash="solid"),
        )
        fig.add_trace(go.Scatter(
            x=[cursor_ts], y=[cursor_wse],
            mode="markers",
            marker=dict(size=12, color="blue", symbol="diamond",
                        line=dict(width=2, color="white")),
            name=f"Current WSE ({cursor_wse:.2f}m)",
            showlegend=True,
        ))

        fig.update_layout(
            yaxis=dict(title="Elevation NGF (m)", range=[y_min, y_max]),
            xaxis=dict(title="Forecast Timeline (48h)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
            margin=dict(l=60, r=20, t=40, b=60),
            hovermode="x unified",
        )
    else:
        fig.update_layout(title="No data or asset selected")
        cursor_wse = None

    st.plotly_chart(fig, config={"displayModeBar": True, "scrollZoom": False}, use_container_width=True)

    # ============================================================
    # CONTEXTUAL CROSS-SECTION VIEWER — Stitched Integrated Platform
    # ============================================================
    st.subheader("Integrated Platform Cross-Section")

    def make_stitched_profile(asset_name, z_yellow_val, z_orange_val, z_red_val, config):
        """Generate a 30m wide stitched railway platform cross-section.
        Layout: [Fosse L] -- [Talus L] -- [Voie] -- [Talus R] -- [Fosse R]
        Uses THIS asset's own thresholds to build the profile shape.
        """
        # Use the asset's own thresholds directly — no distant neighbor lookups
        # red_z = track surface elevation (from DTM for segments)
        # orange_z = embankment level
        # yellow_z = drainage capacity level
        voie_top = z_red_val          # Track surface = RED threshold
        fosse_bottom = z_yellow_val - 1.8  # Ditch bottom below drainage level

        # Build the profile points (X from -15 to +15)
        x_pts = []
        z_pts = []
        # Left Fosse: -15 to -11 (flat bottom)
        for xi in np.linspace(-15, -11, 9):
            x_pts.append(round(xi, 1))
            z_pts.append(round(fosse_bottom, 2))
        # Left Talus slope: -11 to -5 (rises from fosse_bottom to voie_top)
        for xi in np.linspace(-11, -5, 13)[1:]:
            frac = (xi - (-11)) / ((-5) - (-11))
            z_val = fosse_bottom + frac * (voie_top - fosse_bottom)
            x_pts.append(round(xi, 1))
            z_pts.append(round(z_val, 2))
        # Voie plateau: -5 to +5 (flat at voie_top)
        for xi in np.linspace(-5, 5, 21)[1:]:
            x_pts.append(round(xi, 1))
            z_pts.append(round(voie_top, 2))
        # Right Talus slope: +5 to +11 (descends from voie_top to fosse_bottom)
        for xi in np.linspace(5, 11, 13)[1:]:
            frac = (xi - 5) / (11 - 5)
            z_val = voie_top - frac * (voie_top - fosse_bottom)
            x_pts.append(round(xi, 1))
            z_pts.append(round(z_val, 2))
        # Right Fosse: +11 to +15 (flat bottom)
        for xi in np.linspace(11, 15, 9)[1:]:
            x_pts.append(round(xi, 1))
            z_pts.append(round(fosse_bottom, 2))
        return x_pts, z_pts

    if selected_asset:
        asset_key = selected_asset
        has_dtm_profile = asset_key in cs_data

        if has_dtm_profile:
            profile = cs_data[asset_key]
            x_dist  = profile["distances"]
            z_elev  = profile["elevations"]
            source_label = "DTM (LiDAR)"
        else:
            # Stitched integrated platform from z_config thresholds
            x_dist, z_elev = make_stitched_profile(asset_key, z_yellow, z_orange, z_red, z_config)
            source_label = "Integrated Platform (Fosse-Talus-Voie-Talus-Fosse)"

        fig_cs = go.Figure()

        # Terrain / Structural Profile
        fig_cs.add_trace(go.Scatter(
            x=x_dist, y=z_elev,
            name=f"Profile ({source_label})",
            fill='tozeroy', fillcolor='rgba(139,90,43,0.3)',
            line=dict(color='saddlebrown', width=3)
        ))

        # Water level at cursor time step
        if cursor_wse is not None:
            wse_arr = [cursor_wse] * len(x_dist)
            # Only fill where water is above terrain
            fig_cs.add_trace(go.Scatter(
                x=x_dist, y=wse_arr,
                name=f"Water Level (WSE={cursor_wse:.2f}m)",
                line=dict(color='royalblue', width=2, dash='dash'),
                fill='tonexty', fillcolor='rgba(65,105,225,0.35)'
            ))

        # Danger threshold lines across profile width
        fig_cs.add_trace(go.Scatter(
            x=[min(x_dist), max(x_dist)], y=[z_red, z_red],
            name="RED: Voie Min",
            line=dict(color='red', width=2, dash='dot')
        ))
        fig_cs.add_trace(go.Scatter(
            x=[min(x_dist), max(x_dist)], y=[z_orange, z_orange],
            name="ORANGE: Talus Mean",
            line=dict(color='orange', width=2, dash='dash')
        ))
        fig_cs.add_trace(go.Scatter(
            x=[min(x_dist), max(x_dist)], y=[z_yellow, z_yellow],
            name="YELLOW: Buse Max",
            line=dict(color='gold', width=1, dash='dot')
        ))

        fig_cs.update_layout(
            yaxis=dict(title="Elevation NGF (m)",
                       range=[min(z_elev) - 1, max(z_elev) + 2]),
            xaxis=dict(title="Distance from Asset Center (m)"),
            margin=dict(l=40, r=20, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
            height=350
        )
        st.plotly_chart(fig_cs, config={"displayModeBar": False}, use_container_width=True)

        # Caption with metadata
        asset_info = all_assets[all_assets["name"] == selected_asset]
        if not asset_info.empty:
            row = asset_info.iloc[0]
            icon = "📡" if has_dtm_profile else "📐"
            st.caption(
                f"{icon} **{selected_asset}** | {row['asset_type']} | "
                f"{row['lat']:.4f}°N, {row['lon']:.4f}°E | "
                f"Source: _{source_label}_"
            )
    else:
        st.info("Select an asset above to view its terrain cross-section.")



# ============================================================
# RIGHT PANEL: Alerts, SWI, Event Log (all driven by time slider)
# ============================================================
with col2:
    st.subheader("Operational Alerts")

    cap = risk_to_cap_level(max_risk)
    if cap == "RED":
        st.error(f"RED ALERT: {max_risk}% -- EMERGENCY HALT (ETCS/RBC Stop)")
    elif cap == "ORANGE":
        st.warning(f"ORANGE WARNING: {max_risk}% -- Speed Restriction 30 km/h")
    elif cap == "YELLOW":
        st.info(f"YELLOW WATCH: {max_risk}% -- Enhanced Monitoring Active")
    else:
        st.success(f"GREEN: Network Safe ({max_risk}% risk)")

    st.subheader("Soil Saturation (SWI)")
    delta_str = f"{delta_swi:+.4f} mm" if delta_swi != 0 else "stable"
    ts_label = str(current_ts)[11:16] if ":" in str(current_ts) else f"T+{t_idx}h"
    st.metric(label=f"SWI at {ts_label}", value=f"{current_swi:.4f} mm", delta=delta_str)

    st.subheader("Runoff Coefficient")
    st.metric(label=f"C_runoff at {ts_label}", value=f"{current_runoff_c:.6f}")

    st.subheader("Active Runoff")
    st.metric(label=f"Runoff at {ts_label}", value=f"{current_runoff_mm:.4f} mm/h")

    # ============================================================
    # F3: ACCUMULATED RAINFALL GRAPH
    # ============================================================
    st.subheader("Rainfall Profile")

    def calculate_accumulated_rainfall(df_r, interval_hours=1.0):
        """Compute step depth and cumulative accumulated rainfall from intensity series."""
        df_r = df_r.copy()
        df_r["step_depth_mm"] = df_r["intensity_mm_h"] * interval_hours
        df_r["accumulated_mm"] = df_r["step_depth_mm"].cumsum()
        return df_r

    if len(df_swi) > 0 and "intensity_mm_h" in df_swi.columns:
        if is_real_hecras:
            if "P02" in selected_plan:
                interval_h = 10 / 60.0
            elif "P01" in selected_plan:
                interval_h = 5 / 60.0
            else:
                interval_h = 1.0
        else:
            interval_h = 1.0
        df_acc = calculate_accumulated_rainfall(df_swi[["timestamp", "intensity_mm_h"]].copy(), interval_hours=interval_h)
        df_display = df_acc.copy()

        total_rain = df_acc["accumulated_mm"].max()
        current_accum = df_acc.iloc[t_idx]["accumulated_mm"] if t_idx < len(df_acc) else 0
        st.metric("Total Storm Rainfall", f"{total_rain:.1f} mm",
                  delta=f"{current_accum:.1f} mm so far")

        fig_rain = make_subplots(specs=[[{"secondary_y": True}]])

        # Bars: intensity
        fig_rain.add_trace(
            go.Bar(
                x=df_display["timestamp"],
                y=df_display["intensity_mm_h"],
                name="Intensity (mm/h)",
                marker_color=["rgba(41,128,185,0.85)" if i <= t_idx
                               else "rgba(41,128,185,0.25)"
                               for i in range(len(df_display))],
            ),
            secondary_y=False,
        )

        # Line: accumulated depth
        fig_rain.add_trace(
            go.Scatter(
                x=df_display["timestamp"],
                y=df_display["accumulated_mm"],
                name="Accumulated (mm)",
                mode="lines",
                line=dict(color="#e67e22", width=2),
            ),
            secondary_y=True,
        )

        # Current timestep marker
        if t_idx < len(df_display):
            fig_rain.add_vline(
                x=df_display.iloc[t_idx]["timestamp"],
                line_width=1.5, line_dash="dash", line_color="darkgrey"
            )

        fig_rain.update_xaxes(title_text="Time")
        fig_rain.update_yaxes(title_text="Intensity (mm/h)", secondary_y=False)
        fig_rain.update_yaxes(title_text="Accumulated (mm)", secondary_y=True)
        fig_rain.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=20, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_rain, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Rainfall time-series not available for current mode.")

    st.subheader("Event Log")
    events = []
    if len(df_swi) > 0:
        for i in range(min(t_idx + 1, len(df_swi))):
            row = df_swi.iloc[i]
            ts_short = str(row["timestamp"])[11:16] if ":" in str(row["timestamp"]) else f"T+{i}h"
            if row["intensity_mm_h"] > 8:
                events.append(f"{ts_short} - Heavy rain detected ({row['intensity_mm_h']:.1f} mm/h)")
            if row["swi_mm"] > 0.1:
                events.append(f"{ts_short} - SWI threshold rising ({row['swi_mm']:.3f} mm)")
    if not events:
        events = ["No significant events up to this timestep."]
    st.text_area("System Logs", "\n".join(events[-8:]), height=180)

st.divider()
st.caption("Developed by TRAN Trong-Tin, Amal, Szilvi | SNCF Digital Twin Research | Forecast Simulation Engine v2.0")

# ============================================================
# AUTO-ADVANCE LOGIC (Must run last so the UI renders fully first)
# ============================================================
if is_playing:
    if t_idx < n_steps - 1:
        time.sleep(animation_speed_ms / 1000.0)
        st.session_state["timeline_idx"] = t_idx + 1
        st.rerun()
    elif loop_animation:
        time.sleep(animation_speed_ms / 1000.0)
        st.session_state["timeline_idx"] = 0
        st.rerun()
    else:
        # Reached end but loop is disabled. Do nothing.
        pass
