# 🎥 Screen Recording Script — Feature Demonstration Video
## Project: Railway Flood-Risk Digital Twin for the SNCF Tartaiguille Corridor

> **Target Duration**: 3–5 minutes  
> **Tool**: Browser Subagent (automated) or manual screen recording (OBS Studio / ShareX)  
> **Dashboard URL**: `http://localhost:8501/`  
> **Output Format**: MP4 or WebP video  

---

## Recording Plan Overview

| Scene # | Title | Duration | Dashboard Action |
| :---: | :--- | :---: | :--- |
| 1 | Initial State & Mode Selection | 30s | Show sidebar, switch between modes |
| 2 | Historical Showcase Timeline Scrub | 60s | Scrub slider from T+0 to T+44h |
| 3 | Map Interaction & Flow Depth Overlay | 30s | Zoom/pan map, observe flood channel rendering |
| 4 | Group Alerts Table & Drainage Detail | 45s | Scroll to alerts table, open critical section expander |
| 5 | Cross-Section Analysis (Voie_seg_18) | 45s | Select asset, show WSE vs threshold plot |
| 6 | Synthetic Demo Storm Comparison | 30s | Switch to Synthetic mode, scrub timeline |
| 7 | Right Panel Metrics (SWI & Runoff) | 30s | Show SWI gauge, runoff coefficient, event log |

---

## Scene 1: Initial State & Mode Selection (0:00 – 0:30)

### Browser Actions:
1. Navigate to `http://localhost:8501/`
2. Wait 3 seconds for full page load.
3. **Show** the left sidebar with:
   - Operational Mode radio buttons (Historical Showcase / Synthetic Demonstration Storm / Live Monitoring)
   - Timeline Step slider
   - Base Map selector
4. **Click** "Historical Showcase (Sept 2025)" radio button.
5. Wait 2 seconds for data reload.

### Prompt for Browser Subagent:
```
Open http://localhost:8501/. Wait for the page to fully load. 
Capture a screenshot of the initial state.
Click the "Historical Showcase (Sept 2025)" radio button in the left sidebar.
Wait 3 seconds for data to reload.
Capture a screenshot showing the mode is selected.
```

---

## Scene 2: Historical Showcase Timeline Scrub (0:30 – 1:30)

### Browser Actions:
1. Locate the **Timeline Step** slider in the sidebar.
2. **Slowly drag** the slider from step 0 (T+0h) to step 44 (T+44h, which corresponds to 21SEP2025 14:20:00).
   - Move in increments of ~5 steps, pausing 1 second at each position.
   - The map and all metrics should update dynamically at each step.
3. **Pause** at step 44 for 3 seconds. This is the peak flooding moment.

### Prompt for Browser Subagent:
```
On the Streamlit page http://localhost:8501/, find the timeline slider in the left sidebar.
Set the slider to step 0. Wait 1 second.
Set the slider to step 10. Wait 1 second.
Set the slider to step 20. Wait 1 second.
Set the slider to step 30. Wait 1 second.
Set the slider to step 40. Wait 1 second.
Set the slider to step 44. Wait 3 seconds.
Capture a screenshot of the dashboard at step 44.
```

### What to Observe:
- The PyDeck map updates with an evolving blue/cyan flow depth overlay.
- The right-panel SWI gauge should increase.
- The "Top 5 Critical Assets" list should populate with colored severity badges.

---

## Scene 3: Map Interaction & Flow Depth Overlay (1:30 – 2:00)

### Browser Actions:
1. **Zoom in** on the main map area where flooding is visible (the river valley running through the corridor).
2. **Pan** slightly to center the most intense flood zone.
3. Observe the **alpha-masked flow depth overlay**:
   - Hillside sheet flow (<20 cm) is filtered out (transparent).
   - Main flood channels (>35 cm) are rendered with strong blue/cyan color.
4. **Switch base map** from "World Hillshade" to "OpenStreetMap" to show infrastructure context.

### Prompt for Browser Subagent:
```
On the Streamlit dashboard map, zoom in by scrolling the mouse wheel up 3 times
on the center of the map.
Wait 2 seconds. Capture a screenshot.
Then find the "Base Map" dropdown in the left sidebar and change it to "OpenStreetMap".
Wait 2 seconds. Capture a screenshot.
```

---

## Scene 4: Group Alerts Table & Drainage Detail (2:00 – 2:45)

### Browser Actions:
1. **Scroll down** the main content area past the map to reveal the "Corridor Section Group Alerts" table.
2. **Observe** the table rows:
   - Section_18 and Section_19 should show 🟠 ORANGE.
   - Section_11 should show 🟡 YELLOW.
   - Most other sections should show 🟢 GREEN.
3. **Click** the expander below the table labeled "2 Critical Section(s) — Drainage & Bridge Detail" to open it.
4. **Observe** the expanded detail showing drainage alerts for Section_11 (Buse_0).

### Prompt for Browser Subagent:
```
On the Streamlit dashboard at http://localhost:8501/ (already in Historical mode, step 44),
scroll down past the map until you see the "Corridor Section Group Alerts" heading and table.
Wait 2 seconds. Capture a screenshot showing the table.
Then click on the expander text that contains "Critical Section" to expand it.
Wait 2 seconds. Capture a screenshot showing the expanded drainage details.
```

### What to Observe:
- The table demonstrates the **worst-case roll-up**: Section_11 is YELLOW because of `Buse_0` drainage alert, even though `Voie_seg_11` track is GREEN.
- The expanded detail shows which specific drainage assets triggered alerts.

---

## Scene 5: Cross-Section Analysis — Voie_seg_18 (2:45 – 3:30)

### Browser Actions:
1. **Scroll down** further to the "Asset-Specific Hydraulic Forecast" section.
2. Find the **asset select box** (dropdown).
3. **Type** "Voie_seg_18" in the select box and press Enter to select it.
4. Wait 3 seconds for the charts to render.
5. **Scroll down** slightly to show:
   - **Upper chart**: WSE time-series over 127 timesteps, with the current WSE line and colored threshold bands.
   - **Lower chart**: Integrated platform cross-section (Fossé–Talus–Voie–Talus–Fossé) with the blue water fill breaching the orange threshold line.

### Prompt for Browser Subagent:
```
On the Streamlit dashboard, scroll down to find the "Asset-Specific Hydraulic Forecast" section.
Find the asset select box (dropdown).
Click it, type "Voie_seg_18", and press Enter.
Wait 3 seconds for charts to render.
Scroll down to center the cross-section plot in the viewport.
Wait 2 seconds. Capture a screenshot showing the cross-section plot.
```

### What to Observe:
- The WSE time-series shows water levels rising over time.
- The cross-section plot clearly shows the water level (blue fill) **above the orange threshold line** but **below the red line**, confirming the ORANGE alert status for this segment.

---

## Scene 6: Synthetic Demonstration Storm (3:30 – 4:00)

### Browser Actions:
1. **Scroll back up** to the top of the sidebar.
2. **Click** "Synthetic Demonstration Storm" radio button.
3. Wait 3 seconds for data to reload.
4. **Scrub** the timeline slider to the peak moment (around step 60–80).
5. **Observe** how the synthetic storm produces more dramatic flooding across more sections.

### Prompt for Browser Subagent:
```
On the Streamlit dashboard, click the "Synthetic Demonstration Storm" radio button in the sidebar.
Wait 3 seconds for data reload.
Set the timeline slider to step 70. Wait 2 seconds.
Capture a screenshot of the dashboard showing the synthetic storm conditions.
```

---

## Scene 7: Right Panel Metrics — SWI & Runoff (4:00 – 4:30)

### Browser Actions:
1. **Focus** on the right-side panel of the dashboard (if visible), which shows:
   - **SWI Gauge**: Current soil water index value with a colored dial.
   - **Runoff Coefficient**: Current $C_{runoff}$ value.
   - **Event Log**: Timestamped log of alert-level changes.
2. **Hover** or point to each metric to highlight them.

### Prompt for Browser Subagent:
```
On the Streamlit dashboard, ensure the right panel metrics are visible.
If not visible, scroll up to the main dashboard view.
Capture a screenshot focusing on the right-side panel showing SWI gauge,
runoff coefficient, and event log.
```

---

## Post-Production Notes

### Combining Scenes:
- All browser subagent recordings are automatically saved as `.webp` files.
- Use a video editor (e.g., DaVinci Resolve, Clipchamp, or ffmpeg) to:
  1. Concatenate all scene recordings in order.
  2. Add title cards between scenes (optional).
  3. Add voiceover narration (optional) or text annotations.
  4. Export as MP4 (H.264, 1080p).

### Annotated Screenshots:
- For each scene, the captured screenshots can be annotated using Python (Pillow) to add:
  - Red rectangles highlighting key areas.
  - Arrow annotations pointing to critical values.
  - Text labels explaining what the viewer should focus on.

### Voiceover Script (Optional):
If adding narration to the video, use the script from the presentation guide (`presentation.md`) as a reference for each scene's talking points.
