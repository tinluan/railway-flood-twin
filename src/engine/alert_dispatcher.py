"""
src/engine/alert_dispatcher.py — RAMS Alert Dispatcher (Layer 4: Vulnerability & Alert)
=========================================================================================
Consolidates hydraulic WSE output and fragility-curve P_failure into a structured,
RAMS-compliant operational alert that can be issued to train dispatchers or the
ETCS/RBC signalling system.

Architecture Position (Layer 4 — Vulnerability & Alert):
    - RECEIVES:  WSE (m NGF), z_ballast (m NGF), p_failure (0–1), risk category
    - PRODUCES:  Structured alert dict → serves API and Streamlit dashboard
    - CALLED BY: ``src/api/routers/alerts.py``  (GET /api/v1/alerts/current)
    - CALLED BY: ``src/api/routers/engine.py``  (POST /api/v1/engine/simulate)

Alert Hierarchy (RAMS — ETCS Compatible):
    Category  │ Color  │ P_failure  │ WSE condition      │ Directive
    ──────────┼────────┼────────────┼────────────────────┼──────────────────────────
    LOW       │ GREEN  │ < 20%      │ Below yellow_z     │ Standby / Standard Speed
    MEDIUM    │ YELLOW │ 20–50%     │ Above yellow_z     │ Speed Restriction: 60 km/h
    HIGH      │ RED    │ > 50%      │ Above z_ballast    │ EMERGENCY HALT (ETCS Stop)

WSE Override Rule:
    If WSE > z_ballast (water physically on the track), the verdict is always RED
    regardless of the p_failure category.

Output Dict Structure:
    {
        "timestamp":     "2025-01-15 14:32:00",
        "segment_id":    "SEG_142",
        "wse_m":         222.143,        # Water Surface Elevation (m NGF)
        "z_ballast_m":   221.500,        # Top of ballast (m NGF) from z_config.json
        "p_failure_pct": 65.3,           # Probability of ballast failure (%)
        "status":        "RED",          # RAMS color
        "directive":     "EMERGENCY HALT (ETCS Stop)"
    }

Relationship with other files:
    UPSTREAM:
      fragility_curves.py → provides p_failure + category
      hecras_bridge.py    → provides WSE (Water Surface Elevation)
      z_config.json       → provides z_ballast, yellow_z, orange_z, red_z per asset
    DOWNSTREAM:
      api/routers/alerts.py → wraps output in AlertVerdict (Pydantic schema)
      dashboard/app_main.py → displays traffic-light HMI
      (future) ETCS/RBC sync → triggers speed restriction or halt

Example Usage:
    from src.engine.alert_dispatcher import AlertDispatcher

    dispatcher = AlertDispatcher()

    # 1. Generate a verdict for one segment:
    verdict = dispatcher.generate_verdict(
        segment_id="SEG_142",
        wse=222.1,           # water surface from HEC-RAS (m NGF)
        z_ballast=221.5,     # ballast top from z_config.json (m NGF)
        p_failure=0.65,      # from FragilityEvaluator.calculate_p_failure()
        category="HIGH"      # from FragilityEvaluator.get_risk_category()
    )
    # → {"timestamp": "...", "status": "RED", "directive": "EMERGENCY HALT ...", ...}

    # 2. Print a formatted operational alert:
    dispatcher.log_alert(verdict)
    # Output:
    #   [RAIL-TWIN ALERT] 2025-01-15 14:32:00
    #   Segment: SEG_142
    #   Risk: RED (65.0% Failure Prob)
    #   Directive: EMERGENCY HALT (ETCS Stop)
    #   CRITICAL: Water Surface Elevation exceeds Ballast Height!
"""

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
