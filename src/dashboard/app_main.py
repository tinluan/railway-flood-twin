import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import sys

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
        ("Pont Rail (Bridge)",    GIS_PATH / "Pont Rail_fixed.gpkg"),
        ("Buse (Culvert)",        GIS_PATH / "Buse_fixed.gpkg"),
        ("Dalot (Box Culvert)",   GIS_PATH / "Dalot_fixed.gpkg"),
    ]
    for asset_type, path in configs:
        if not path.exists():
            continue
        gdf = gpd.read_file(path).to_crs("EPSG:4326")
        for idx, row in gdf.iterrows():
            pt = row.geometry.centroid
            name_val = row.get("name", f"{asset_type}_{idx}")
            records.append({
                "asset_type": asset_type,
                "name": name_val if name_val else f"{asset_type}_{idx}",
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
        ("Voie (Track)",       GIS_PATH / "voie_fixed.gpkg",         [220, 30,  30,  220], 4),
        ("Talus (Embankment)", GIS_PATH / "Talus Terre_fixed.gpkg",  [139, 90,  43,  160], 2),
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

df_rain = load_rainfall()
df_swi = load_swi()
all_assets = load_assets()
infra_data = load_infra_layers()

# ============================================================
# TITLE & SIDEBAR
# ============================================================
st.title("RailTwin Flood: Digital Twin Decision Support")
st.markdown("**SNCF Professional Standard** - Forecast Simulation Mode")

st.sidebar.header("Control Panel")
mode = st.sidebar.selectbox("Mode", ["Forecast Simulation", "Live Monitoring", "PLM26 Contest Demo"])
corridor = st.sidebar.selectbox("Corridor", ["Ligne_400 (Himalayas)"])

# --- Asset Filter ---
asset_types = st.sidebar.multiselect(
    "Show Asset Types",
    ["Pont Rail (Bridge)", "Buse (Culvert)", "Dalot (Box Culvert)"],
    default=["Pont Rail (Bridge)", "Buse (Culvert)", "Dalot (Box Culvert)"]
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

# --- Compute risk per asset at this timestep ---
def compute_risk_at_t(row, rain_mm, swi_mm, runoff_mm):
    """Per-asset risk using real GPS position as terrain vulnerability proxy.
    
    Logic: Along the Ligne 400 corridor (lat 44.649 to 44.663),
    southern points (lower lat) are in the valley = flood FIRST.
    Northern points (higher lat) are on higher ground = flood LATER.
    This creates a realistic 'flood wave' progression.
    """
    # --- GPS-based vulnerability ---
    # Corridor bounds from real QGIS data
    lat_min, lat_max = 44.6498, 44.6628  # southern valley → northern ridge
    lat = row.get("lat", (lat_min + lat_max) / 2)
    
    # Normalize: 0.0 = highest (safe), 1.0 = lowest (most vulnerable)
    if lat_max > lat_min:
        vulnerability = 1.0 - (lat - lat_min) / (lat_max - lat_min)
    else:
        vulnerability = 0.5
    vulnerability = max(0.0, min(1.0, vulnerability))
    
    # --- Physics components ---
    base = min(rain_mm * 2.5, 40)           # rain (0-40)
    swi_factor = min(swi_mm * 150, 25)      # saturation (0-25)
    runoff_factor = min(runoff_mm * 80, 15)  # runoff (0-15)
    
    # Raw risk from global weather (same for all points)
    weather_risk = base + swi_factor + runoff_factor  # max ~80
    
    # Local terrain modifier: valley points get up to +35% risk
    terrain_boost = weather_risk * (0.15 + 0.35 * vulnerability)
    
    # Structural fragility: Bridges more critical than culverts
    if "Bridge" in row["asset_type"] or "Pont" in row["asset_type"]:
        struct_mult = 1.15
    else:
        struct_mult = 1.0
    
    final_risk = (weather_risk + terrain_boost) * struct_mult
    return min(int(final_risk), 100)

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
        lambda r: compute_risk_at_t(r, current_rain, current_swi, current_runoff_mm), axis=1
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
    # WSE CHART with TIME CURSOR
    # ============================================================
    st.subheader("Hydraulic Forecast (48h Timeline)")
    fig = go.Figure()

    if len(df_rain) > 0:
        # Convert timestamps to strings for Plotly compatibility
        timestamps = [str(t) for t in df_rain['timestamp']]
        z_ballast_val = 221.5
        z_terrain_val = 220.2
        z_ballast = [z_ballast_val] * len(df_rain)
        z_terrain = [z_terrain_val] * len(df_rain)
        wse = [z_terrain_val + (r * 0.05) for r in df_rain['intensity_mm_h']]

        wse_max = max(wse)
        y_min = z_terrain_val - 0.5
        y_max = max(wse_max, z_ballast_val) + 0.5

        fig.add_trace(go.Scatter(x=timestamps, y=z_ballast, name="Z_Ballast (Danger)",
                                 line=dict(color='red', dash='dash', width=2)))
        fig.add_trace(go.Scatter(x=timestamps, y=z_terrain, name="Z_Terrain",
                                 fill='tozeroy', fillcolor='rgba(139,90,43,0.15)',
                                 line=dict(color='saddlebrown', width=1)))
        fig.add_trace(go.Scatter(x=timestamps, y=wse, name="WSE (Predicted)",
                                 line=dict(color='royalblue', width=3),
                                 fill='tonexty', fillcolor='rgba(65,105,225,0.25)'))

        # --- VERTICAL CURSOR LINE at current slider position ---
        cursor_ts = timestamps[t_idx]
        cursor_wse = wse[t_idx]
        # Use add_shape instead of add_vline to avoid Plotly Timestamp arithmetic bug
        fig.add_shape(
            type="line", x0=cursor_ts, x1=cursor_ts, y0=y_min, y1=y_max,
            line=dict(color="orange", width=2, dash="solid"),
        )
        fig.add_annotation(
            x=cursor_ts, y=y_max, text=f"T+{t_idx}h",
            showarrow=False, font=dict(color="orange", size=12),
            yshift=10,
        )
        fig.add_trace(go.Scatter(
            x=[cursor_ts], y=[cursor_wse],
            mode="markers",
            marker=dict(size=12, color="orange", symbol="diamond", line=dict(width=2, color="white")),
            name=f"Cursor (WSE={cursor_wse:.2f}m)",
            showlegend=True,
        ))

        fig.update_layout(
            yaxis=dict(title="Elevation (m)", range=[y_min, y_max]),
            xaxis=dict(title="Forecast Timeline"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=60, r=20, t=40, b=60),
            hovermode="x unified",
        )
    else:
        fig.update_layout(title="No data -- run ingestion first")

    st.plotly_chart(fig, width="stretch")

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
