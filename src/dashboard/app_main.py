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

@st.cache_data
def load_wse_results():
    wse_file = PROCESSED_DATA / "hecras_wse_results.json"
    if wse_file.exists():
        with open(wse_file, "r") as f:
            return json.load(f)
    return {}

wse_results = load_wse_results()

# ============================================================
# TITLE & SIDEBAR
# ============================================================
st.title("RailTwin Flood: Digital Twin Decision Support")
st.markdown("**SNCF Professional Standard** - Forecast Simulation Mode")

st.sidebar.header("Control Panel")
mode = st.sidebar.selectbox("Mode", ["Forecast Simulation", "Live Monitoring", "PLM26 Contest Demo"])
corridor = st.sidebar.selectbox("Corridor", ["Ligne_400 (Himalayas)"])

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

# --- Compute risk per asset at this timestep ---
def compute_risk_at_t(row, rain_mm, swi_mm, runoff_mm, config):
    """Per-asset risk using precise 3D vertical thresholds.
    
    Logic: 
    1. Simulates local Water Surface Elevation (WSE) based on rain intensity and runoff.
    2. Compares WSE against asset-specific Yellow/Orange/Red Z-thresholds.
    """
    asset_id = row["name"]
    asset_config = config.get(asset_id)
    
    # 1. Physics: Simulate Water Rise (WSE)
    # Heavy rain and high runoff increase the water level (simulated HEC-RAS proxy for now)
    water_rise_m = (rain_mm * 0.05) + (runoff_mm * 0.1) # e.g. 40mm/h rain + 15mm runoff = 3.5m rise
    
    if asset_config:
        # We assume the ditch/culvert bottom is roughly 1.5m below its top (yellow_z)
        base_z = asset_config["yellow_z_m"] - 1.5 
        current_wse = base_z + water_rise_m
        
        # 2. Risk Hierarchy Evaluation
        if current_wse >= asset_config["red_z_m"]:
            # RED: Track submerged
            return 100
        elif current_wse >= asset_config["orange_z_m"]:
            # ORANGE: Embankment soaked / Ditch overflowing
            return 75
        elif current_wse >= asset_config["yellow_z_m"]:
            # YELLOW: Drainage capacity reached
            return 50
        else:
            # GREEN: Safe
            return int((water_rise_m / 1.5) * 25) # Scale 0-25 based on how full the ditch is
            
    else:
        # Fallback for assets not in config (e.g. roads)
        lat_min, lat_max = 44.6498, 44.6628
        lat = row.get("lat", (lat_min + lat_max) / 2)
        vulnerability = 1.0 - (lat - lat_min) / (lat_max - lat_min) if lat_max > lat_min else 0.5
        vulnerability = max(0.0, min(1.0, vulnerability))
        
        base = min(rain_mm * 2.5, 40)
        swi_factor = min(swi_mm * 150, 25)
        runoff_factor = min(runoff_mm * 80, 15)
        weather_risk = base + swi_factor + runoff_factor
        terrain_boost = weather_risk * (0.15 + 0.35 * vulnerability)
        final_risk = weather_risk + terrain_boost
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
        lambda r: compute_risk_at_t(r, current_rain, current_swi, current_runoff_mm, z_config), axis=1
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
                    # =========================================================
                    # TODO (AI COPILOT): Add Synthetic 2D Inundation Layer Here
                    # =========================================================
                    # 1. Check if `data/processed/synthetic_flood.geojson` exists.
                    # 2. If yes, read it and create a new pdk.Layer("GeoJsonLayer").
                    # 3. Set get_fill_color=[0, 100, 255, 100] (semi-transparent blue).
                    # 4. Insert it into this layers list just below the TileLayer.
                    
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
    # GLOBAL ASSET SELECTOR
    # ============================================================
    st.subheader("Asset-Specific Hydraulic Forecast")
    
    asset_options = filtered["name"].tolist() if not filtered.empty else []
    critical_idx = 0
    if not filtered.empty and "risk_level" in filtered.columns:
        critical_name = filtered.sort_values("risk_level", ascending=False).iloc[0]["name"]
        if critical_name in asset_options:
            critical_idx = asset_options.index(critical_name)
            
    selected_asset = st.selectbox("📌 Select Critical Asset to Analyze:", asset_options, index=critical_idx) if asset_options else None
    
    # =========================================================
    # TODO (AI COPILOT): Implement UI Hotspot Lock
    # =========================================================
    # 1. Add a `st.checkbox("Lock Auto-Focus")` above the selectbox.
    # 2. If checked, store the `selected_asset` in `st.session_state`.
    # 3. If unchecked, let the `critical_idx` logic (above) run freely.
    
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
    # CONTEXTUAL CROSS-SECTION VIEWER
    # ============================================================
    st.subheader("Contextual Cross-Section (Terrain + Ditch)")

    # =========================================================
    # TODO (AI COPILOT): Implement Stitched Synthetic Profile
    # =========================================================
    # 1. Modify `make_synthetic_profile` below to return an "Integrated Platform".
    # 2. Instead of a single trapezoid, build a 30m wide section.
    # 3. Logic: Look up `nearest_talus` and `nearest_voie` in `z_config` for the `asset_name`.
    #    - If it's a Fosse, draw a V-shape.
    #    - If it's a Talus, draw a slope.
    #    - If it's a Voie, draw a flat plateau at the top.
    # 4. Stitch them together so X runs from -15m to +15m.
    # 5. BONUS: Color the specific asset the user selected in a brighter color.
    
    def make_synthetic_profile(asset_name, z_yellow_val, z_orange_val):
        """Generate a standard trapezoidal railway cross-section from engineering defaults."""
        import numpy as np
        ditch_bottom_z = z_yellow_val - 1.8  # 1.8m ditch depth below yellow threshold
        bank_z         = z_orange_val          # Bank top = orange threshold
        # Trapezoidal cross-section: 24m wide, 3:1 side slopes
        x = np.linspace(-12, 12, 49)
        z = []
        for xi in x:
            if abs(xi) > 9:        # outer embankment slopes up
                z.append(round(bank_z + (abs(xi) - 9) * 0.5, 3))
            elif abs(xi) > 4:      # ditch side slopes
                z.append(round(ditch_bottom_z + (abs(xi) - 4) * ((bank_z - ditch_bottom_z) / 5), 3))
            else:                   # ditch flat bottom
                z.append(round(ditch_bottom_z, 3))
        return list(x.round(2)), z

    if selected_asset:
        asset_key = selected_asset
        has_dtm_profile = asset_key in cs_data

        if has_dtm_profile:
            profile = cs_data[asset_key]
            x_dist  = profile["distances"]
            z_elev  = profile["elevations"]
            source_label = "DTM (LiDAR)"
        else:
            # Synthetic geometric fallback from z_config thresholds
            x_dist, z_elev = make_synthetic_profile(asset_key, z_yellow, z_orange)
            source_label = "Synthetic Geometry (no DTM coverage)"

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
