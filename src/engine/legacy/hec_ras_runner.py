"""
src/engine/hec_ras_runner.py — HEC-RAS COM Controller (Layer 3: Simulation Engine)
====================================================================================
Provides a thin Python wrapper around the HEC-RAS 6.1 COM (Component Object Model)
API to launch a 2D unsteady-flow hydraulic simulation from within the 15-minute
operational cycle.

Architecture Position (Layer 3 — Simulation Engine):
    - TRIGGERED BY: src/api/routers/engine.py  (POST /api/v1/engine/cycle)
    - READS:        model/hec_ras/FloodTwin.prj  (HEC-RAS project file)
    - PRODUCES:     HEC-RAS HDF5 output files (read by hecras_bridge.py)
    - SUPERSEDED BY: src/engine/hecras_bridge.py  (more complete, use that for HEC-RAS 6.7)

Difference vs hecras_bridge.py:
    ┌──────────────────────┬───────────────────────────────────────────────┐
    │ hec_ras_runner.py    │ Simple: open → compute → close                │
    │                      │ COM ProgID: RAS610.HECRASController           │
    │                      │ Has built-in MOCK mode if win32com missing     │
    ├──────────────────────┼───────────────────────────────────────────────┤
    │ hecras_bridge.py     │ Full: connect → open → compute → extract WSE  │
    │                      │ COM ProgID: RAS67.HECRASController             │
    │                      │ Supports WSE extraction + JSON export          │
    └──────────────────────┴───────────────────────────────────────────────┘

Mock Mode (No HEC-RAS Installed):
    If the `pywin32` package is missing or HEC-RAS is not installed, the class
    runs in MOCK mode — it simulates a 2-second compute delay and returns True.
    This allows the full API + dashboard to run without HEC-RAS for demonstration.

Dependency:
    pip install pywin32   (Windows only — required for COM integration)
    HEC-RAS 6.1 must be installed and the project .prj file must exist.

Relationship with other files:
    UPSTREAM:
      preprocessor.py    → provides hotspot segment list (tells which plan to run)
      swi_calculator.py  → SWI > threshold triggers this runner
    DOWNSTREAM:
      hecras_bridge.py   → reads HEC-RAS output (WSE per cross-section)
      fragility_curves.py → uses extracted water depth to compute P_failure

Example Usage:
    from src.engine.hec_ras_runner import HECRASController

    # 1. Connect and run with real HEC-RAS (Windows, pywin32 installed):
    ctrl = HECRASController(project_path="C:/model/FloodTwin.prj")
    if ctrl.connect():
        success = ctrl.run_simulation(plan_name="RealTime_Flood")
        print("Simulation succeeded:", success)

    # 2. Mock mode — works without HEC-RAS (demo/CI environment):
    ctrl = HECRASController()   # project_path defaults from PROJECT_ROOT
    ctrl.connect()              # prints WARNING: running in MOCK mode
    ctrl.run_simulation()       # simulates 2s delay, returns True

Run standalone to test the controller:
    python src/engine/hec_ras_runner.py
"""

import os
import sys
import time
# Note: Requires 'pip install pywin32'
try:
    import win32com.client
except ImportError:
    win32com = None

# Import our central path manager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paths import PROJECT_ROOT

class HECRASController:
    """Python Controller for HEC-RAS via COM API."""
    
    def __init__(self, project_path=None):
        self.project_path = project_path or str(PROJECT_ROOT / "model/hec_ras/FloodTwin.prj")
        self.rc = None

    def connect(self):
        """Initialize the HEC-RAS Controller."""
        if win32com is None:
            print("WARNING: win32com not found. HEC-RAS integration will run in MOCK mode.")
            return False
        
        try:
            self.rc = win32com.client.Dispatch("RAS610.HECRASController")
            print("Connected to HEC-RAS Controller (v6.1.0)")
            return True
        except Exception as e:
            print(f"ERROR: Failed to connect to HEC-RAS: {e}")
            return False

    def run_simulation(self, plan_name="RealTime_Flood"):
        """Executes the 2D simulation for the current active runoff."""
        if not self.rc:
            print(f"[MOCK MODE] Simulating HEC-RAS 2D Plan: {plan_name}...")
            time.sleep(2) # Simulate compute time
            print("[MOCK MODE] Simulation Complete.")
            return True

        # Real HEC-RAS Command Sequence
        self.rc.Project_Open(self.project_path)
        print(f"Opened Project: {self.project_path}")
        
        # Trigger the compute
        print(f"Running Unsteady Flow Simulation (Plan: {plan_name})...")
        success = self.rc.Compute_Unsteady(None, None, None)
        
        if success:
            print("HEC-RAS Simulation Successful.")
        else:
            print("ERROR: HEC-RAS Simulation Failed.")
            
        self.rc.Project_Close()
        return success

if __name__ == "__main__":
    # Test the controller
    ctrl = HECRASController()
    ctrl.connect()
    ctrl.run_simulation()
