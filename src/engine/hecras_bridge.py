"""
src/engine/hecras_bridge.py — HEC-RAS 6.7 Full Bridge (Layer 3: Simulation Engine)
=====================================================================================
Connects to HEC-RAS 6.7 via the COM (Component Object Model) interface.
This is the *production-grade* bridge used by the Digital Twin Dashboard to:
  1. Open a HEC-RAS project file (.prj)
  2. Run a steady or unsteady flow computation
  3. Extract Water Surface Elevation (WSE) at specific cross-sections
  4. Export results to JSON for dashboard / API consumption
  5. Close cleanly without leaving zombie processes

Architecture Position (Layer 3 — Simulation Engine):
    - TRIGGERED BY: dashboard/app_main.py (Streamlit Run button)
                    src/api/routers/engine.py (POST /api/v1/engine/cycle)
    - READS:        model/hec_ras/FloodTwin.prj   (HEC-RAS 6.7 project)
    - WRITES:       data/processed/hecras_wse_results.json  (via export_wse_to_json)
    - FEEDS:        src/engine/fragility_curves.py  (water_depth = WSE - z_terrain)
                    src/api/routers/alerts.py       (reads hecras_wse_results.json)

Difference vs hec_ras_runner.py:
    hec_ras_runner.py  → simple compute trigger, HEC-RAS 6.1, mock mode available
    hecras_bridge.py   → full WSE extraction, HEC-RAS 6.7, no mock mode, production

Dependency:
    pip install pywin32          (Windows only — COM interface)
    HEC-RAS 6.7 Beta 5 must be installed.
    COM ProgID: RAS67.HECRASController

WSE Output JSON Format (hecras_wse_results.json):
    {
      "station_1000": 222.145,   # Water Surface Elevation in metres NGF
      "station_950":  221.890,
      ...
    }
    → This is read by alerts.py to evaluate WSE vs. z_ballast per asset.

Context Manager Support:
    The class implements __enter__ / __exit__ for use with `with` statements,
    ensuring COM resources are always released even if an exception occurs.

Relationship with other files:
    UPSTREAM:
      hec_ras_runner.py → triggers the HEC-RAS compute (simpler trigger)
      preprocessor.py   → z_ballast values (for WSE comparison)
    DOWNSTREAM:
      data/processed/hecras_wse_results.json → consumed by alerts.py router
      fragility_curves.py → water_depth = WSE - base_z → P_failure
      dashboard/app_main.py → displays WSE time series on map

Authors: TRAN Trong-Tin, Amal, Szilvi
Project: SNCF Railway Flood-Risk Digital Twin (Master Capstone)

Example Usage:
    from src.engine.hecras_bridge import HECRASBridge

    # --- 1. Using as a context manager (recommended — auto-closes COM): ---
    with HECRASBridge() as bridge:
        bridge.open_project("C:/model/hec_ras/FloodTwin.prj")
        bridge.compute_current_plan(wait=True)
        wse_dict = bridge.get_wse_profile()
        # wse_dict: {"station_1000": 222.145, "station_950": 221.89, ...}

    # --- 2. Export WSE to JSON for dashboard / API: ---
    with HECRASBridge() as bridge:
        bridge.open_project("C:/model/hec_ras/FloodTwin.prj")
        bridge.compute_current_plan()
        bridge.export_wse_to_json(
            output_path="data/processed/hecras_wse_results.json"
        )
        # → saves {station: wse_m} mapping for all cross-sections

    # --- 3. Get HEC-RAS version string: ---
    bridge = HECRASBridge()
    print(bridge.get_version())  # e.g. "6.7 Beta 5"
    bridge.close()

    # --- 4. Extract stations on a specific river/reach: ---
    with HECRASBridge() as bridge:
        bridge.open_project("C:/model/hec_ras/FloodTwin.prj")
        stations = bridge.get_river_stations("Rivière_X", "Reach_A")
        # → ["1000", "950", "900", "850", ...]
"""

import win32com.client
import os
import json
import time
import pandas as pd
from pathlib import Path


class HECRASBridge:
    """Bridge between the Digital Twin Dashboard and HEC-RAS 6.7."""

    # COM ProgID for HEC-RAS 6.7
    PROG_ID = "RAS67.HECRASController"

    def __init__(self):
        self._rc = None
        self._project_path = None
        self._is_open = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def connect(self):
        """Create a COM connection to HEC-RAS Controller."""
        if self._rc is not None:
            return
        self._rc = win32com.client.Dispatch(self.PROG_ID)
        print(f"[HECRASBridge] Connected to {self._rc.HECRASVersion()}")

    def open_project(self, prj_path: str):
        """Open a HEC-RAS .prj project file.
        
        Args:
            prj_path: Absolute path to the .prj file.
        """
        if self._rc is None:
            self.connect()
        abs_path = str(Path(prj_path).resolve())
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"HEC-RAS project not found: {abs_path}")
        self._rc.Project_Open(abs_path)
        self._project_path = abs_path
        self._is_open = True
        print(f"[HECRASBridge] Opened project: {abs_path}")

    def close(self):
        """Close the HEC-RAS project and release COM resources."""
        if self._rc is not None:
            try:
                self._rc.Project_Close()
                self._rc.QuitRas()
            except Exception:
                pass
            self._rc = None
            self._is_open = False
            print("[HECRASBridge] Connection closed.")

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    def compute_current_plan(self, wait=True):
        """Run the currently active plan in HEC-RAS.
        
        Args:
            wait: If True, block until computation finishes.
        
        Returns:
            Tuple (n_messages, messages_list, block_flag)
        """
        if not self._is_open:
            raise RuntimeError("No project is open. Call open_project() first.")
        
        # Compute_CurrentPlan returns (success_flag, nMsg, msgList, blockingMode)
        res = self._rc.Compute_CurrentPlan(0, None, wait)
        if isinstance(res, tuple) and len(res) >= 4:
            success, n_msg, msg_list, blocking = res[:4]
        elif isinstance(res, tuple) and len(res) == 3:
            success, n_msg, msg_list = res
            blocking = wait
        else:
            n_msg, msg_list, blocking = 0, [], wait
            
        print(f"[HECRASBridge] Computation finished. Messages: {n_msg}")
        return n_msg, msg_list, blocking

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------
    def get_river_stations(self, river_name: str = "", reach_name: str = ""):
        """Get the list of cross-section stations along a river/reach.
        
        If river_name and reach_name are empty, uses the first river/reach.
        
        Returns:
            List of station IDs (strings).
        """
        if not self._is_open:
            raise RuntimeError("No project is open.")
        
        # Get river/reach info if not provided
        if not river_name or not reach_name:
            n_rivers = self._rc.Geometry_GetRivers(0, None, None)[0]
            river_names = self._rc.Geometry_GetRivers(0, None, None)[1]
            if n_rivers == 0:
                return []
            river_name = river_names[0]
            
            n_reaches = self._rc.Geometry_GetReaches(river_name, 0, None, None)[0]
            reach_names = self._rc.Geometry_GetReaches(river_name, 0, None, None)[1]
            if n_reaches == 0:
                return []
            reach_name = reach_names[0]
        
        # Get stations
        result = self._rc.Geometry_GetNodes(river_name, reach_name, 0, None, None)
        n_nodes = result[0]
        node_ids = result[1]
        
        print(f"[HECRASBridge] Found {n_nodes} stations on {river_name}/{reach_name}")
        return list(node_ids) if node_ids else []

    def get_wse_profile(self, river_name: str = "", reach_name: str = "", 
                        profile_idx: int = 1):
        """Extract Water Surface Elevation (WSE) for all stations in a profile.
        
        Args:
            river_name: Name of the river (empty = first river).
            reach_name: Name of the reach (empty = first reach).
            profile_idx: 1-based profile index.
        
        Returns:
            Dict mapping station_id -> WSE (meters NGF).
        """
        if not self._is_open:
            raise RuntimeError("No project is open.")
        
        stations = self.get_river_stations(river_name, reach_name)
        if not stations:
            return {}
        
        # If names were auto-detected, re-detect them
        if not river_name or not reach_name:
            river_names = self._rc.Geometry_GetRivers(0, None, None)[1]
            river_name = river_names[0]
            reach_names = self._rc.Geometry_GetReaches(river_name, 0, None, None)[1]
            reach_name = reach_names[0]
        
        wse_dict = {}
        for station in stations:
            try:
                # Output_NodeOutput parameters:
                # (riverID, reachID, nodeID, upDn, profileIdx, outputVarIdx)
                # outputVarIdx=2 is Water Surface Elevation (WSE)
                wse = self._rc.Output_NodeOutput(
                    river_name, reach_name, station, 0, profile_idx, 2
                )
                wse_dict[station] = round(float(wse), 4)
            except Exception as e:
                wse_dict[station] = None
                print(f"  Warning: Could not read WSE at station {station}: {e}")
        
        print(f"[HECRASBridge] Extracted WSE for {len(wse_dict)} stations (Profile {profile_idx})")
        return wse_dict

    def export_wse_to_json(self, output_path: str, **kwargs):
        """Extract WSE and save to JSON for Dashboard consumption.
        
        Args:
            output_path: Path to save the JSON file.
            **kwargs: Passed to get_wse_profile().
        """
        wse_data = self.get_wse_profile(**kwargs)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(wse_data, f, indent=2)
        print(f"[HECRASBridge] WSE exported to {out}")
        return wse_data

    # ------------------------------------------------------------------
    # Recomputation Pipeline
    # ------------------------------------------------------------------
    def update_precipitation(self, rainfall_csv_path: str, plan_id: str = "p01") -> bool:
        """
        Updates the HEC-RAS Unsteady Flow (.uXX) file to inject new rainfall data.
        This modifies the plain-text unsteady flow file programmatically since the
        COM API lacks a SetPrecipitation() method.
        
        Args:
            rainfall_csv_path: Path to the CSV with hourly rainfall (intensity_mm_h).
            plan_id: The plan ID (e.g., 'p01'). Will find corresponding .uXX file.
            
        Returns:
            True if updated successfully.
        """
        if not self._project_path:
            raise RuntimeError("No project is open. Call open_project() first.")
            
        prj_path = Path(self._project_path)
        # Parse .prj to find the unsteady flow file for the given plan
        # Simplification: Assume .u01 corresponds to .p01 for this demonstrator
        u_ext = plan_id.replace('p', 'u')
        u_file = prj_path.with_suffix(f".{u_ext}")
        
        if not u_file.exists():
            print(f"[HECRASBridge] Unsteady flow file not found: {u_file}")
            return False
            
        try:
            df = pd.read_csv(rainfall_csv_path)
            intensities = df['intensity_mm_h'].tolist()
            
            # Read .uXX file
            with open(u_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            print(f"[HECRASBridge] Injecting {len(intensities)} rainfall records into {u_file.name}")
            
            # Find the "Precipitation Hydrograph=" block and replace it
            new_lines = []
            skip = False
            for line in lines:
                if line.startswith("Precipitation Hydrograph="):
                    # Write the new header
                    new_lines.append(f"Precipitation Hydrograph= {len(intensities)} \n")
                    
                    # Format values in 8-character right-aligned blocks, 10 per line
                    current_line = ""
                    for i, val in enumerate(intensities):
                        # Format as a string, e.g. "     1.5" or "       0"
                        val_str = f"{val:g}"
                        if len(val_str) > 8:
                            val_str = f"{val:.1f}"[:8]
                        current_line += val_str.rjust(8)
                        
                        if (i + 1) % 10 == 0 or i == len(intensities) - 1:
                            new_lines.append(current_line + "\n")
                            current_line = ""
                            
                    skip = True # Skip the existing lines of the old hydrograph
                    continue
                
                if skip:
                    # We are currently skipping the old hydrograph values.
                    # HEC-RAS block ends when we hit a line that isn't just spaces/numbers,
                    # typically the next keyword starts with a letter, like "DSS Path="
                    if "=" in line or line.strip().isalpha() or line.startswith("DSS Path="):
                        skip = False
                        new_lines.append(line)
                    continue
                    
                if not skip:
                    new_lines.append(line)
            
            # Write back
            with open(u_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            return True
        except Exception as e:
            print(f"[HECRASBridge] Failed to update precipitation: {e}")
            return False

    def recompute_and_extract(self, rainfall_csv_path: str, plan_id: str = "p01", wait: bool = True):
        """
        Full pipeline: Update precipitation, run HEC-RAS, and trigger HDF5 extraction.
        
        Args:
            rainfall_csv_path: Path to new rainfall data.
            plan_id: Plan to execute.
            wait: Block until complete.
        """
        print(f"[HECRASBridge] Starting recomputation pipeline for plan {plan_id}...")
        
        # 1. Update Precipitation
        self.update_precipitation(rainfall_csv_path, plan_id)
        
        # 2. Compute
        # COM API Compute_CurrentPlan uses whichever plan was active when saved, 
        # but we can force it or just use Compute_CurrentPlan for the demo.
        self.compute_current_plan(wait=wait)
        
        # 3. Inform reader to refresh (this would trigger the 2D HDF5 reader, not COM)
        # The actual extraction should be done by hecras_hdf5_reader.py for 2D.
        print("[HECRASBridge] Recomputation complete. Ready for HDF5 extraction.")
        return True

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def get_version(self):
        """Return the HEC-RAS version string."""
        if self._rc is None:
            self.connect()
        return self._rc.HECRASVersion()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self.close()


# ======================================================================
# Standalone test
# ======================================================================
if __name__ == "__main__":
    bridge = HECRASBridge()
    bridge.connect()
    version = bridge.get_version()
    print(f"\nHEC-RAS Version: {version}")
    print("Bridge is ready. Provide a .prj path to test full workflow.")
    bridge.close()
