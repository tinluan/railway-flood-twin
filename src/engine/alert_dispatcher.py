"""
src/engine/alert_dispatcher.py — RAMS Alert Dispatcher (Layer 4: Vulnerability & Alert)
=========================================================================================
Consolidates hydraulic WSE output and fragility-curve P_failure into structured,
RAMS-compliant operational alerts that can be issued to train dispatchers or the
ETCS/RBC signalling system.

Two operating modes are supported:
  1. **Legacy flat mode** (backward-compatible with the old z_config.json):
       AlertDispatcher.generate_verdict(segment_id, wse, z_ballast, p_failure, category)
  2. **Grouped mode** (new F5 architecture, using z_config_grouped.json):
       AlertDispatcher.evaluate_group(group_id, group_cfg, wse_results, timestep_idx)
       AlertDispatcher.evaluate_all_groups(grouped_config, wse_results, timestep_idx)

Architecture Position (Layer 4 — Vulnerability & Alert):
    - RECEIVES:  WSE (m NGF), z_ballast (m NGF), p_failure (0–1), risk category
    - PRODUCES:  Structured alert dict → serves API and Streamlit dashboard
    - CALLED BY: ``src/api/routers/alerts.py``  (GET /api/v1/alerts/current)
    - CALLED BY: ``src/api/routers/engine.py``  (POST /api/v1/engine/simulate)

Alert Hierarchy (RAMS — ETCS Compatible):
    Category  │ Color  │ WSE condition             │ Directive
    ──────────┼────────┼───────────────────────────┼──────────────────────────
    LOW       │ GREEN  │ Below yellow_z of all sub │ Standby / Standard Speed
    MEDIUM    │ YELLOW │ Above yellow_z             │ Speed Restriction: 60 km/h
    HIGH      │ ORANGE │ Above orange_z             │ Speed Restriction: 30 km/h
    CRITICAL  │ RED    │ Above red_z (submergence)  │ EMERGENCY HALT (ETCS Stop)

Group Roll-up Rule:
    The group verdict is the WORST colour among:
      - track_talus alert (WSE vs Track DTM thresholds)
      - drainage_assets alerts (WSE vs each drainage asset's thresholds)
      - bridges alerts (WSE vs bridge soffit thresholds)

WSE Override Rule:
    If WSE > red_z_m for any sub-asset, the whole group is always RED.

Grouped Alert Output Dict Structure:
    {
        "group_id":         "Section_11",
        "timestamp":        "2025-09-21 14:32:00",
        "status":           "ORANGE",          # worst-case colour across all sub-assets
        "directive":        "Speed Restriction: 30 km/h",
        "track_talus": {
            "track_id":     "Voie_seg_11",
            "wse_m":        209.75,
            "status":       "ORANGE",
            "margin_m":     0.34,              # WSE - orange_z (positive = exceeded)
        },
        "drainage_alerts": [
            {
                "id":       "Buse_0",
                "type":     "Circular Culvert",
                "wse_m":    203.80,
                "status":   "YELLOW",
                "margin_m": 0.19,
            }
        ],
        "bridge_alerts": [],
    }

Relationship with other files:
    UPSTREAM:
      fragility_curves.py → provides p_failure + category
      hecras_bridge.py    → provides WSE (Water Surface Elevation)
      z_config.json       → legacy flat thresholds (backward compat)
      z_config_grouped.json → new grouped thresholds (F5 schema)
    DOWNSTREAM:
      api/routers/alerts.py → wraps output in AlertVerdict (Pydantic schema)
      dashboard/app_main.py → displays traffic-light HMI
      (future) ETCS/RBC sync → triggers speed restriction or halt

Example Usage (legacy):
    from src.engine.alert_dispatcher import AlertDispatcher
    dispatcher = AlertDispatcher()
    verdict = dispatcher.generate_verdict(
        segment_id="SEG_142",
        wse=222.1,
        z_ballast=221.5,
        p_failure=0.65,
        category="HIGH"
    )
    # → {"timestamp": "...", "status": "RED", "directive": "EMERGENCY HALT ...", ...}

Example Usage (grouped, F5):
    import json
    from src.engine.alert_dispatcher import AlertDispatcher

    with open("data/processed/z_config_grouped.json") as f:
        grouped_cfg = json.load(f)
    with open("data/processed/hecras_wse_results.json") as f:
        wse_results = json.load(f)

    dispatcher = AlertDispatcher()
    all_alerts = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=59)
    for grp in all_alerts:
        print(grp["group_id"], "→", grp["status"], grp["directive"])
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_ALERT_HIERARCHY: Dict[str, int] = {
    "GREEN":  0,
    "YELLOW": 1,
    "ORANGE": 2,
    "RED":    3,
}
_DIRECTIVES: Dict[str, str] = {
    "GREEN":  "Standby / Standard Speed",
    "YELLOW": "Speed Restriction: 60 km/h",
    "ORANGE": "Speed Restriction: 30 km/h",
    "RED":    "EMERGENCY HALT (ETCS Stop)",
}


def _worst_color(a: str, b: str) -> str:
    """Return the higher-severity of two alert colours."""
    return a if _ALERT_HIERARCHY[a] >= _ALERT_HIERARCHY[b] else b


def _wse_to_color(wse: float, yellow_z: Optional[float], orange_z: Optional[float], red_z: Optional[float]) -> str:
    """Map a WSE value against three thresholds to a colour string."""
    if red_z is not None and wse > red_z:
        return "RED"
    if orange_z is not None and wse > orange_z:
        return "ORANGE"
    if yellow_z is not None and wse > yellow_z:
        return "YELLOW"
    return "GREEN"


# ---------------------------------------------------------------------------
# Main Dispatcher Class
# ---------------------------------------------------------------------------
class AlertDispatcher:
    """
    Consolidates all risk metrics into RAMS-compliant operational alerts.

    Supports both the legacy flat z_config schema and the new F5 grouped schema.
    """

    def __init__(self) -> None:
        # Legacy mapping kept for backward compatibility
        self.risk_mapping = {
            "LOW":    {"color": "GREEN",  "action": _DIRECTIVES["GREEN"]},
            "MEDIUM": {"color": "YELLOW", "action": _DIRECTIVES["YELLOW"]},
            "HIGH":   {"color": "RED",    "action": _DIRECTIVES["RED"]},
        }

    # ------------------------------------------------------------------
    # Legacy API (backward-compatible)
    # ------------------------------------------------------------------
    def generate_verdict(
        self,
        segment_id: str,
        wse: float,
        z_ballast: float,
        p_failure: float,
        category: str,
    ) -> Dict[str, Any]:
        """
        Creates a structured alert record (legacy flat mode).

        Parameters
        ----------
        segment_id : str
        wse        : float  Water Surface Elevation in m NGF
        z_ballast  : float  Ballast top elevation from z_config (red_z_m)
        p_failure  : float  Probability of failure 0–1
        category   : str    'LOW' | 'MEDIUM' | 'HIGH'
        """
        is_over_ballast = wse > z_ballast
        final_cat = "HIGH" if is_over_ballast else category

        return {
            "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "segment_id":    segment_id,
            "wse_m":         round(wse, 3),
            "z_ballast_m":   z_ballast,
            "p_failure_pct": round(p_failure * 100, 1),
            "status":        self.risk_mapping[final_cat]["color"],
            "directive":     self.risk_mapping[final_cat]["action"],
        }

    def log_alert(self, alert: Dict[str, Any]) -> None:
        """Prints a professional operational alert to the console."""
        print(f"\n[RAIL-TWIN ALERT] {alert['timestamp']}")
        print(f"Segment: {alert.get('segment_id', alert.get('group_id', 'N/A'))}")
        print(f"Risk: {alert['status']} ({alert.get('p_failure_pct', 'N/A')}% Failure Prob)")
        print(f"Directive: {alert['directive']}")
        if alert["status"] == "RED":
            print("CRITICAL: Water Surface Elevation exceeds Ballast Height!")

    # ------------------------------------------------------------------
    # F5 Grouped API
    # ------------------------------------------------------------------
    def evaluate_group(
        self,
        group_id: str,
        group_cfg: Dict[str, Any],
        wse_results: Dict[str, Any],
        timestep_idx: int = 0,
    ) -> Dict[str, Any]:
        """
        Evaluate a single corridor section group and produce a roll-up alert.

        The group worst-case colour is the maximum severity among:
          • track_talus alert (uses WSE at the Voie_seg centroid)
          • each drainage_asset alert
          • each bridge alert

        Parameters
        ----------
        group_id     : str   e.g. "Section_11"
        group_cfg    : dict  One entry from z_config_grouped.json
        wse_results  : dict  hecras_wse_results.json (asset_id → {wse_m, base_z_m})
        timestep_idx : int   Timestep to evaluate (default 0)

        Returns
        -------
        Dict  See module docstring for output structure.
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        overall_color = "GREEN"

        # ── 1. Track-Talus evaluation ─────────────────────────────────
        tt = group_cfg.get("track_talus", {})
        track_id = tt.get("track_id", "")

        track_wse = self._get_wse(track_id, wse_results, timestep_idx)
        track_entry = wse_results.get(track_id, {})
        track_base_z = track_entry.get("base_z_m", 0.0)
        is_track_dry = track_wse <= track_base_z + 0.02

        if is_track_dry:
            track_color = "GREEN"
        else:
            track_color = _wse_to_color(track_wse, tt.get("yellow_z_m"), tt.get("orange_z_m"), tt.get("red_z_m"))

        track_margin = round(track_wse - (tt.get("orange_z_m") or track_wse), 3) if track_color in ("ORANGE", "RED") else round(track_wse - (tt.get("yellow_z_m") or track_wse), 3)

        track_alert = {
            "track_id":  track_id,
            "talus_id":  tt.get("talus_id"),
            "wse_m":     round(track_wse, 3),
            "z_dtm_m":   tt.get("z_dtm_m"),
            "yellow_z_m": tt.get("yellow_z_m"),
            "orange_z_m": tt.get("orange_z_m"),
            "red_z_m":   tt.get("red_z_m"),
            "status":    track_color,
            "margin_m":  track_margin,
        }
        overall_color = _worst_color(overall_color, track_color)

        # ── 2. Drainage assets evaluation ────────────────────────────
        drainage_alerts: List[Dict[str, Any]] = []
        for da in group_cfg.get("drainage_assets", []):
            da_id = da["id"]
            da_wse = self._get_wse(da_id, wse_results, timestep_idx)
            da_entry = wse_results.get(da_id, {})
            da_base_z = da_entry.get("base_z_m", 0.0)
            is_da_dry = da_wse <= da_base_z + 0.02

            if is_da_dry:
                da_color = "GREEN"
            else:
                da_color = _wse_to_color(da_wse, da.get("yellow_z_m"), da.get("orange_z_m"), da.get("red_z_m"))

            # Margin: positive means WSE exceeds that threshold
            if da_color == "RED":
                margin = round(da_wse - da["red_z_m"], 3)
            elif da_color == "ORANGE":
                margin = round(da_wse - da["orange_z_m"], 3)
            elif da_color == "YELLOW":
                margin = round(da_wse - da["yellow_z_m"], 3)
            else:
                margin = round(da_wse - da.get("yellow_z_m", da_wse), 3)

            drainage_alerts.append({
                "id":          da_id,
                "type":        da.get("type", "Drainage"),
                "wse_m":       round(da_wse, 3),
                "yellow_z_m":  da.get("yellow_z_m"),
                "orange_z_m":  da.get("orange_z_m"),
                "red_z_m":     da.get("red_z_m"),
                "status":      da_color,
                "margin_m":    margin,
            })
            overall_color = _worst_color(overall_color, da_color)

        # ── 3. Bridge assets evaluation ───────────────────────────────
        bridge_alerts: List[Dict[str, Any]] = []
        for br in group_cfg.get("bridges", []):
            br_id = br["id"]
            br_wse = self._get_wse(br_id, wse_results, timestep_idx)
            br_entry = wse_results.get(br_id, {})
            br_base_z = br_entry.get("base_z_m", 0.0)
            is_br_dry = br_wse <= br_base_z + 0.02

            if is_br_dry:
                br_color = "GREEN"
            else:
                br_color = _wse_to_color(br_wse, br.get("yellow_z_m"), br.get("orange_z_m"), br.get("red_z_m"))

            bridge_alerts.append({
                "id":     br_id,
                "type":   br.get("type", "Bridge"),
                "wse_m":  round(br_wse, 3),
                "yellow_z_m": br.get("yellow_z_m"),
                "orange_z_m": br.get("orange_z_m"),
                "red_z_m":    br.get("red_z_m"),
                "status": br_color,
            })
            overall_color = _worst_color(overall_color, br_color)

        return {
            "group_id":        group_id,
            "timestamp":       ts,
            "status":          overall_color,
            "directive":       _DIRECTIVES[overall_color],
            "track_alert":     track_alert,
            "drainage_alerts": drainage_alerts,
            "bridge_alerts":   bridge_alerts,
        }

    def evaluate_all_groups(
        self,
        grouped_config: Dict[str, Any],
        wse_results: Dict[str, Any],
        timestep_idx: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate every section group and return a sorted list of group alerts.

        Groups are ordered by severity (worst first) then by group_id.

        Parameters
        ----------
        grouped_config : dict  Full z_config_grouped.json content
        wse_results    : dict  Full hecras_wse_results.json content
        timestep_idx   : int   Timestep to evaluate

        Returns
        -------
        List[dict]  One alert dict per group (see evaluate_group for structure)
        """
        results: List[Dict[str, Any]] = []
        for group_id, group_cfg in grouped_config.items():
            alert = self.evaluate_group(group_id, group_cfg, wse_results, timestep_idx)
            results.append(alert)

        # Sort: worst colour first, then alphabetically by group_id
        results.sort(
            key=lambda a: (-_ALERT_HIERARCHY[a["status"]], a["group_id"])
        )
        return results

    def summarise_system(self, group_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Produce a system-wide summary from a list of group alert dicts.

        Returns
        -------
        Dict with keys: overall_status, total_groups, counts (per colour),
        worst_groups (list of group_ids at worst level)
        """
        counts = {"GREEN": 0, "YELLOW": 0, "ORANGE": 0, "RED": 0}
        overall = "GREEN"
        for a in group_alerts:
            c = a["status"]
            counts[c] += 1
            overall = _worst_color(overall, c)

        worst = [a["group_id"] for a in group_alerts if a["status"] == overall and overall != "GREEN"]

        return {
            "overall_status": overall,
            "directive":      _DIRECTIVES[overall],
            "total_groups":   len(group_alerts),
            "counts":         counts,
            "worst_groups":   worst,
            "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_wse(
        asset_id: str,
        wse_results: Dict[str, Any],
        timestep_idx: int,
    ) -> float:
        """Return the WSE for asset_id at timestep_idx, or 0.0 if unavailable."""
        entry = wse_results.get(asset_id, {})
        series = entry.get("wse_m", [])
        if not series:
            return entry.get("base_z_m", 0.0)
        idx = min(timestep_idx, len(series) - 1)
        return float(series[idx])


# ---------------------------------------------------------------------------
# Standalone test / demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os

    dispatcher = AlertDispatcher()

    # ── Legacy test ──────────────────────────────────────────────────
    print("=== Legacy flat verdict ===")
    verdict = dispatcher.generate_verdict("SEG_142", 222.1, 221.5, 0.65, "HIGH")
    dispatcher.log_alert(verdict)

    # ── Grouped test ─────────────────────────────────────────────────
    project_root = Path(__file__).resolve().parents[2]
    grouped_path = project_root / "data" / "processed" / "z_config_grouped.json"
    wse_path     = project_root / "data" / "processed" / "hecras_wse_results.json"

    if grouped_path.exists() and wse_path.exists():
        with open(grouped_path, encoding="utf-8") as f:
            grouped_cfg = json.load(f)
        with open(wse_path, encoding="utf-8") as f:
            wse_results = json.load(f)

        print("\n=== Grouped group alerts (timestep 59) ===")
        all_alerts = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=59)
        summary    = dispatcher.summarise_system(all_alerts)

        print(f"Overall system: {summary['overall_status']} — {summary['directive']}")
        print(f"Groups: {summary['counts']}")
        if summary["worst_groups"]:
            print(f"Critical sections: {summary['worst_groups']}")

        # Show top 5 groups by severity
        print("\nTop 5 groups:")
        for grp in all_alerts[:5]:
            n_drain = len([d for d in grp["drainage_alerts"] if d["status"] != "GREEN"])
            print(
                f"  {grp['group_id']:15s} -> {grp['status']:6s} | "
                f"track={grp['track_alert']['status']:6s} wse={grp['track_alert']['wse_m']:.2f}m "
                f"| drainage alerts={n_drain}"
            )
    else:
        print("\n(Grouped config or WSE results not found – skipping grouped test)")
