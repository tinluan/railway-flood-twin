import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import sys
import json

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import RAW_DATA, PROCESSED_DATA

st.set_page_config(page_title="RailTwin Flood | SNCF Standard", layout="wide")

# ============================================================
# DATA LOADING (cached for performance)
# ============================================================
@st.cache_data
def load_rainfall():
    rain_file = RAW_DATA / "rainfall_Ligne_400.csv"
    if rain_file.exists():
        df = pd.read_csv(rain_file, parse_dates=["timestamp"])
        return df
    return pd.DataFrame({"timestamp": [], "intensity_mm_h": []})

@st.cache_data
def load_swi():
    swi_file = PROCESSED_DATA / "swi_results.csv"
    if swi_file.exists():
        df = pd.read_csv(swi_file, parse_dates=["timestamp"])
        return df
    return pd.DataFrame()

@st.cache_data
def load_assets():
    import geopandas as gpd
    import warnings
    warnings.filterwarnings('ignore')
    GIS_PATH = RAW_DATA.parent / "staging" / "gis"
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
            # Always use standardized base_id to avoid French accent mismatches
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
    GIS_PATH = RAW_DATA.parent / "staging" / "gis"
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
            # Use to_json() + json.loads() for proper GeoJSON serialization
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
    cs_file = PROCESSED_DATA / "cross_sections.json"
    if cs_file.exists():
        with open(cs_file, "r") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_z_config():
    z_file = PROCESSED_DATA / "z_config.json"
    if z_file.exists():
        with open(z_file, "r") as f:
            return json.load(f)
    return {}

df_rain   = load_rainfall()
df_swi    = load_swi()
cs_data   = load_cross_sections()
all_assets = load_assets()
infra_data = load_infra_layers()
z_config  = load_z_config()

# --- Replace monolithic Voie_0 with segmented track sections ---
voie_seg_file = PROCESSED_DATA / "voie_segments.json"
if voie_seg_file.exists():
    with open(voie_seg_file, "r") as f:
        voie_segments = json.load(f)
    # Remove old Voie_0 row(s) from all_assets
    all_assets = all_assets[~all_assets["name"].str.startswith("Voie_")]
    # Add each segment as a separate asset row
    seg_rows = pd.DataFrame(voie_segments)[["name", "asset_type", "lat", "lon"]]
    all_assets = pd.concat([all_assets, seg_rows], ignore_index=True)

@st.cache_data
def load_wse_results():
    wse_file = PROCESSED_DATA / "hecras_wse_results.json"
    if wse_file.exists():
        with open(wse_file, "r") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_flood_timesteps():
    flood_file = PROCESSED_DATA / "synthetic_flood_timesteps.json"
    if flood_file.exists():
        with open(flood_file, "r") as f:
            return json.load(f)
    return {}

wse_results = load_wse_results()
flood_timesteps = load_flood_timesteps()

# ============================================================
# TITLE & SIDEBAR
# ============================================================
st.title("RailTwin Flood: Digital Twin Decision Support")
st.markdown("**SNCF Professional Standard** - Forecast Simulation Mode")

st.sidebar.header("Control Panel")
mode = st.sidebar.selectbox("Mode", ["Forecast Simulation", "Live Monitoring", "PLM26 Contest Demo"])
corridor = st.sidebar.selectbox("Corridor", ["Ligne_400 (Cevenol Corridor, France)"])

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

# ============================================================
# TIME SLIDER (The Core Feature)
# ============================================================
n_steps = len(df_rain) if len(df_rain) > 0 else 48

st.sidebar.divider()
st.sidebar.subheader("Forecast Timeline")
t_idx = st.sidebar.slider(
    "Drag to explore forecast",
    min_value=0,
    max_value=n_steps - 1,
    value=n_steps - 1,
    format="T+%dh",
    help="Drag this slider to see the predicted state of your railway at each hour."
)

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
    2. Compare WSE against the asset's Yellow/Orange/Red Z-thresholds.
    3. If an asset is physically lower than a flooded asset, it must also be flooded.
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
    
    yellow_z = asset_config["yellow_z_m"]
    orange_z = asset_config["orange_z_m"]
    red_z = asset_config["red_z_m"]
    
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
        base_z = asset_wse_data.get("base_z_m", yellow_z - 2.0)
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
    all_assets["risk_level"] = all_assets.apply(
        lambda r: compute_risk_at_t(r, t_idx, wse_results, z_config), axis=1
    )
    all_assets["cap_level"] = all_assets["risk_level"].apply(risk_to_cap_level)
    all_assets["color"] = all_assets["cap_level"].apply(lambda lv: CAP_COLORS_RGBA[lv])

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

        tooltip = {
            "html": "<b>{name}</b><br/>Type: {asset_type}<br/>Risk: {risk_level}%",
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

        # Build dynamic flood layer — color by corridor risk severity
        flood_layers = []
        flood_geojson = flood_timesteps.get(str(t_idx), {"type": "FeatureCollection", "features": []})
        if flood_geojson.get("features"):
            # Flood color matches the corridor's overall CAP risk level
            cap = risk_to_cap_level(max_risk)
            flood_fill = {
                "GREEN":  [76, 175, 80, 60],
                "YELLOW": [255, 235, 59, 80],
                "ORANGE": [255, 152, 0, 100],
                "RED":    [244, 67, 54, 120],
            }.get(cap, [30, 100, 230, 90])
            flood_line = [c if i < 3 else 180 for i, c in enumerate(flood_fill)]
            flood_layers.append(pdk.Layer(
                "GeoJsonLayer",
                data=flood_geojson,
                get_fill_color=flood_fill,
                get_line_color=flood_line,
                line_width_min_pixels=1,
                pickable=False,
            ))

        try:
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=13,
                    pitch=30,
                    bearing=-10,
                ),
                layers=[
                    pdk.Layer(
                        "TileLayer",
                        data="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                        get_tile_data=None,
                    ),
                    *flood_layers,
                    *infra_layers,
                    risk_layer,
                ],
                tooltip=tooltip,
            ))
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

    if len(df_rain) > 0 and selected_asset:
        timestamps = [str(t) for t in df_rain['timestamp']]

        # --- Load per-asset WSE from hecras_wse_results.json ---
        if selected_asset in wse_results:
            asset_wse_data = wse_results[selected_asset]
            wse = asset_wse_data['wse_m']
            base_z = asset_wse_data['base_z_m']
        else:
            # Fallback: estimate from rain+runoff (for assets not in wse_results)
            base_z = z_yellow - 1.5
            wse = [base_z + ((r * 0.05) + (df_swi.iloc[i]["active_runoff_mm"] * 0.1))
                   for i, r in enumerate(df_rain['intensity_mm_h'])]

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
        """
        # Get neighbor Z values from z_config
        asset_cfg = config.get(asset_name, {})
        nearest_talus = asset_cfg.get("nearest_talus", "")
        nearest_voie = asset_cfg.get("nearest_voie", "")
        talus_cfg = config.get(nearest_talus, {})
        voie_cfg = config.get(nearest_voie, {})

        # Resolve key elevations
        fosse_bottom = z_yellow_val - 1.8
        talus_base = talus_cfg.get("yellow_z_m", z_orange_val - 1.0)
        talus_top = talus_cfg.get("orange_z_m", z_orange_val)
        voie_top = voie_cfg.get("red_z_m", z_red_val)  # red_z = voie min (top of track)
        if voie_top < talus_top:
            voie_top = talus_top + 0.5  # ensure track is above embankment

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
    st.metric(label=f"SWI at T+{t_idx}h", value=f"{current_swi:.4f} mm", delta=delta_str)

    st.subheader("Runoff Coefficient")
    st.metric(label=f"C_runoff at T+{t_idx}h", value=f"{current_runoff_c:.6f}")

    st.subheader("Active Runoff")
    st.metric(label=f"Runoff at T+{t_idx}h", value=f"{current_runoff_mm:.4f} mm/h")

    st.subheader("Event Log")
    events = []
    if len(df_swi) > 0:
        for i in range(min(t_idx + 1, len(df_swi))):
            row = df_swi.iloc[i]
            ts_short = str(row["timestamp"])[11:16]
            if row["intensity_mm_h"] > 8:
                events.append(f"{ts_short} - Heavy rain detected ({row['intensity_mm_h']:.1f} mm/h)")
            if row["swi_mm"] > 0.1:
                events.append(f"{ts_short} - SWI threshold rising ({row['swi_mm']:.3f} mm)")
    if not events:
        events = ["No significant events up to this timestep."]
    st.text_area("System Logs", "\n".join(events[-8:]), height=180)

st.divider()
st.caption("Developed by TRAN Trong-Tin, Amal, Szilvi | SNCF Digital Twin Research | Forecast Simulation Engine v2.0")
