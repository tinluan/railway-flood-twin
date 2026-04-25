import os
import pandas as pd
from datetime import datetime

class AlertDispatcher:
    """Consolidates all risk metrics into a RAMS-compliant operational alert."""
    
    def __init__(self):
        self.risk_mapping = {
            "LOW": {"color": "GREEN", "action": "Standby / Standard Speed"},
            "MEDIUM": {"color": "YELLOW", "action": "Speed Restriction: 60 km/h"},
            "HIGH": {"color": "RED", "action": "EMERGENCY HALT (ETCS Stop)"}
        }

    def generate_verdict(self, segment_id, wse, z_ballast, p_failure, category):
        """
        Creates a structured alert record.
        """
        is_over_ballast = wse > z_ballast
        
        # Override category if water is physically over the ballast
        final_cat = "HIGH" if is_over_ballast else category
        
        alert = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "segment_id": segment_id,
            "wse_m": round(wse, 3),
            "z_ballast_m": z_ballast,
            "p_failure_pct": round(p_failure * 100, 1),
            "status": self.risk_mapping[final_cat]["color"],
            "directive": self.risk_mapping[final_cat]["action"]
        }
        
        return alert

    def log_alert(self, alert):
        """Prints a professional operational alert to the console."""
        print(f"\n[RAIL-TWIN ALERT] {alert['timestamp']}")
        print(f"Segment: {alert['segment_id']}")
        print(f"Risk: {alert['status']} ({alert['p_failure_pct']}% Failure Prob)")
        print(f"Directive: {alert['directive']}")
        if alert['status'] == "RED":
            print("CRITICAL: Water Surface Elevation exceeds Ballast Height!")

if __name__ == "__main__":
    dispatcher = AlertDispatcher()
    # Mock data
    verdict = dispatcher.generate_verdict("SEG_142", 222.1, 221.5, 0.65, "HIGH")
    dispatcher.log_alert(verdict)
