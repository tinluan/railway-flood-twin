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
# Risk model: higher runoff + higher rain intensity = higher risk
# Bridges are more vulnerable than culverts at equal water levels
def compute_risk_at_t(row, rain_mm, swi_mm, runoff_mm):
    """Simplified per-asset risk score based on physics state."""
    base = min(rain_mm * 3.5, 50)  # rain contribution (0-50)
    swi_factor = min(swi_mm * 200, 30)  # saturation contribution (0-30)
    runoff_factor = min(runoff_mm * 50, 20)  # active runoff contribution (0-20)
    # Bridges are more fragile
    if "Bridge" in row["asset_type"]:
        multiplier = 1.3
    elif "Culvert" in row["asset_type"]:
        multiplier = 1.0
    else:
        multiplier = 0.8
    return min(int((base + swi_factor + runoff_factor) * multiplier), 100)

if not all_assets.empty:
    all_assets["risk_level"] = all_assets.apply(
        lambda r: compute_risk_at_t(r, current_rain, current_swi, current_runoff_mm), axis=1
    )
    all_assets["color"] = all_assets["risk_level"].apply(
        lambda r: [220, 20, 20, 200] if r > 60 else ([255, 165, 0, 200] if r > 30 else [30, 180, 30, 200])
    )

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
        st.dataframe(
            top5.style.background_gradient(subset=["Risk (%)"], cmap="RdYlGn_r"),
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

    if max_risk > 60:
        st.error(f"RED ALERT: {max_risk}% Probability of Failure")
        st.warning("ACTION: EMERGENCY HALT (ETCS/RBC Stop)")
    elif max_risk > 30:
        st.warning(f"YELLOW ALERT: {max_risk}% Probability of Failure")
        st.info("ACTION: Speed Restriction 60 km/h")
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
st.caption("Developed for Tin Luan - SNCF Digital Twin Research | Forecast Simulation Engine v2.0")
