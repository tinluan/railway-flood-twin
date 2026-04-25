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
