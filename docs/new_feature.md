# Decoupled Hydrology-to-Hydraulics Handoff (Precipitation Scaling)

## Goal
Currently, the digital twin calculates soil saturation (SWI) and the Sigmoid Runoff Coefficient ($C_{\text{runoff}}$) in Python, but HEC-RAS is still run with the raw forecast rainfall series. This overestimates flood depths because HEC-RAS assumes 100% of the rain becomes runoff (as internal infiltration is disabled to prevent double-counting).

To align the codebase with the documented design, we must modify the pipeline to push the scaled **active runoff** ($R_{\text{active}}(t)$) into the HEC-RAS unsteady flow boundary condition.

---

## Proposed Changes (To Be Implemented)

### 1. Update HEC-RAS Bridge (`src/engine/hecras_bridge.py`)
Modify `update_precipitation` to read the active runoff column if present, falling back to raw rain for backward compatibility.

```diff
     def update_precipitation(self, rainfall_csv_path: str, plan_id: str = "p02") -> bool:
         ...
         try:
             df = pd.read_csv(rainfall_csv_path)
-            intensities = df['intensity_mm_h'].tolist()
+            # Read active runoff if calculated, otherwise fall back to raw intensity
+            col = 'active_runoff_mm' if 'active_runoff_mm' in df.columns else 'intensity_mm_h'
+            intensities = df[col].tolist()
```

### 2. Update Pipeline Orchestrator (`src/engine/pipeline_orchestrator.py`)
Modify `run_cycle` to pass the processed `swi_results.csv` path containing `active_runoff_mm` to the bridge, rather than the raw rainfall forecast CSV.

```diff
                     with HECRASBridge() as bridge:
                         bridge.open_project(str(prj_path))
                         # Operational plan is p02 (21SEP2025 Cévenol storm)
-                        success = bridge.recompute_and_extract(str(rain_path), plan_id="p02", wait=True)
+                        # Pass the calculated hydrology output containing active runoff
+                        swi_csv = paths.PROCESSED / "swi_results.csv"
+                        success = bridge.recompute_and_extract(str(swi_csv), plan_id="p02", wait=True)
```
