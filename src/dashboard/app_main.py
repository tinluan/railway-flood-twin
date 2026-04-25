import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import RAW_DATA, PROCESSED_DATA

st.set_page_config(page_title="RailTwin Flood | SNCF Standard", layout="wide")

# --- Title & Status ---
st.title("🛰️ RailTwin Flood: Digital Twin Decision Support")
st.markdown("### SNCF Professional Standard - Flood Risk Monitoring")

# --- Sidebar ---
st.sidebar.header("🕹️ Control Panel")
mode = st.sidebar.selectbox("Select Mode", ["Live Monitoring", "PLM26 Contest Demo"])
corridor = st.sidebar.selectbox("Corridor", ["Ligne_400 (Himalayas)", "Ligne_Paris_Lyon"])

if st.sidebar.button("🚀 Trigger Full 15-min Cycle"):
    st.sidebar.success("Cycle Executed: Rain -> SWI -> HEC-RAS -> Alert")

# --- Mock Data Loading ---
def load_data():
    rain_file = RAW_DATA / "rainfall_Ligne_400.csv"
    if rain_file.exists():
        return pd.read_csv(rain_file)
    return pd.DataFrame({"timestamp": [], "intensity_mm_h": []})

df_rain = load_data()

# --- Main Layout ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ Live Risk Map — Real Infrastructure (3D View)")

    import pydeck as pdk
    import geopandas as gpd
    import warnings
    warnings.filterwarnings('ignore')

    # --- Asset Filter in sidebar ---
    asset_types = st.sidebar.multiselect(
        "Show Asset Types",
        ["Pont Rail (Bridges)", "Buse (Culverts)", "Dalot (Box Culverts)"],
        default=["Pont Rail (Bridges)", "Buse (Culverts)", "Dalot (Box Culverts)"]
    )

    # --- Load real GeoPackage files ---
    @st.cache_data
    def load_assets():
        GIS_PATH = RAW_DATA.parent / "staging" / "gis"
        records = []
        configs = [
            ("Pont Rail (Bridges)",   GIS_PATH / "Pont Rail_fixed.gpkg",  [255, 30,  30,  200]),
            ("Buse (Culverts)",        GIS_PATH / "Buse_fixed.gpkg",       [255, 165, 0,   200]),
            ("Dalot (Box Culverts)",   GIS_PATH / "Dalot_fixed.gpkg",      [180, 0,   180, 200]),
        ]
        for asset_type, path, color in configs:
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
                    "risk_level": 0,   # will be updated by risk engine
                    "color": color,
                })
        return pd.DataFrame(records)

    all_assets = load_assets()

    # --- Apply Risk Scores (mock — will be replaced by fragility engine output) ---
    import numpy as np
    np.random.seed(42)
    all_assets["risk_level"] = np.random.randint(10, 95, size=len(all_assets))
    all_assets["color"] = all_assets["risk_level"].apply(
        lambda r: [220, 20, 20, 200] if r > 60 else ([255, 165, 0, 200] if r > 30 else [30, 180, 30, 200])
    )

    # --- Filter by selected asset types ---
    filtered = all_assets[all_assets["asset_type"].isin(asset_types)] if asset_types else all_assets

    # --- Load real infrastructure lines (track geometry) ---
    @st.cache_data
    def load_infra_geojson():
        GIS_PATH = RAW_DATA.parent / "staging" / "gis"
        layers = []
        infra_configs = [
            ("Voie (Track)",        GIS_PATH / "voie_fixed.gpkg",          [220, 30,  30,  220], 4),
            ("Talus (Embankment)",  GIS_PATH / "Talus Terre_fixed.gpkg",   [139, 90,  43,  160], 2),
            ("Fossé (Ditch)",       GIS_PATH / "Fossé terre_fixed.gpkg",   [80,  120, 80,  130], 1),
        ]
        for name, path, color, width in infra_configs:
            if not path.exists():
                continue
            gdf = gpd.read_file(path).to_crs("EPSG:4326")
            geojson = gdf.__geo_interface__
            layers.append(pdk.Layer(
                "GeoJsonLayer",
                data=geojson,
                get_line_color=color,
                get_fill_color=[*color[:3], 60],
                line_width_min_pixels=width,
                pickable=False,
            ))
        return layers

    infra_layers = load_infra_geojson()

    # --- PyDeck 3D Map with fixed-size icons ---
    if not filtered.empty:
        center_lat = filtered["lat"].mean()
        center_lon = filtered["lon"].mean()

        # ScatterplotLayer: radiusUnits="pixels" keeps size CONSTANT at any zoom
        risk_layer = pdk.Layer(
            "ScatterplotLayer",
            data=filtered,
            get_position=["lon", "lat"],
            get_radius=12,                  # always 12 pixels regardless of zoom
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
                *infra_layers,   # Railway track + embankments (real geometry)
                risk_layer,      # Fixed-size risk dots on top
            ],
            tooltip=tooltip,
        ))

        # --- Top 5 High-Risk Table ---
        st.subheader("📍 Top 5 Critical Assets")
        top5 = filtered.sort_values("risk_level", ascending=False).head(5)[
            ["name", "asset_type", "lat", "lon", "risk_level"]
        ].reset_index(drop=True)
        top5.columns = ["Asset ID", "Type", "Latitude", "Longitude", "Risk (%)"]
        st.dataframe(
            top5.style.background_gradient(subset=["Risk (%)"], cmap="RdYlGn_r"),
            use_container_width=True
        )
    else:
        st.warning("No assets selected. Use the sidebar filter to choose asset types.")

    # WSE vs Ballast Plot
    st.subheader("📉 Hydraulic Verdict (Segment SEG_142)")
    fig = go.Figure()

    if len(df_rain) > 0:
        time_steps = list(df_rain['timestamp'] if 'timestamp' in df_rain.columns else range(len(df_rain)))
        z_ballast_val = 221.5
        z_terrain_val = 220.2
        z_ballast = [z_ballast_val] * len(df_rain)
        z_terrain = [z_terrain_val] * len(df_rain)
        wse = [z_terrain_val + (r * 0.05) for r in df_rain['intensity_mm_h']]

        wse_max = max(wse)
        y_min = z_terrain_val - 0.5
        y_max = max(wse_max, z_ballast_val) + 0.5

        fig.add_trace(go.Scatter(x=time_steps, y=z_ballast, name="Z_Ballast (Danger Limit)",
                                 line=dict(color='red', dash='dash', width=2)))
        fig.add_trace(go.Scatter(x=time_steps, y=z_terrain, name="Z_Terrain (Ground)",
                                 fill='tozeroy', fillcolor='rgba(139,90,43,0.2)',
                                 line=dict(color='saddlebrown', width=1)))
        fig.add_trace(go.Scatter(x=time_steps, y=wse, name="WSE (Water Level)",
                                 line=dict(color='royalblue', width=3),
                                 fill='tonexty', fillcolor='rgba(65,105,225,0.3)'))

        fig.update_layout(
            yaxis=dict(title="Elevation (m)", range=[y_min, y_max]),
            xaxis=dict(title="Time (Hours)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=60, r=20, t=40, b=60),
            hovermode="x unified"
        )
    else:
        fig.update_layout(title="No rainfall data yet — run ingestion first")

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🚦 Operational Alerts")
    
    # Mock Alert Display
    risk_prob = 68.4
    if risk_prob > 50:
        st.error(f"🔴 RED ALERT: {risk_prob}% Probability of Failure")
        st.warning("🚉 ACTION: EMERGENCY HALT (ETCS/RBC Stop)")
    elif risk_prob > 20:
        st.warning(f"🟡 YELLOW ALERT: {risk_prob}% Probability of Failure")
        st.info("🚉 ACTION: Speed Restriction 60 km/h")
    else:
        st.success("🟢 GREEN: Network Safe")

    st.subheader("🧠 Soil Saturation (SWI)")
    st.metric(label="Current SWI", value="142.5 mm", delta="4.2 mm (Increasing)")
    
    st.subheader("📋 Event Log")
    st.text_area("System Logs", "15:22 - Rainfall API Synced\n15:24 - SWI threshold exceeded\n15:25 - HEC-RAS Solver Triggered\n15:26 - Red Alert Dispatched", height=150)

st.divider()
st.caption("Developed by Antigravity AI for Tin Luan - SNCF Digital Twin Research")
