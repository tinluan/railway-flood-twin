import json
from pathlib import Path
from src.engine.alert_dispatcher import AlertDispatcher
from src.utils.paths import paths

def test_alert_logic_synthetic_demo_transitions():
    """
    Verifies that the Synthetic Demonstration Storm WSE transitions correctly:
      - Starts completely GREEN (T=0)
      - Becomes ORANGE (T=7) via Section_19 drainage ditch
      - Peak reaches RED (T=85) with 3 RED groups and 2 ORANGE groups
      - Recedes back to ORANGE (T=95)

    Cosine wave profile (127 timesteps, 10-min intervals = 21.2h):
      Phase 0 (T=0-14):  ALL DRY → GREEN
      Phase 1 (T=15-45): Fosse terre_13 → ORANGE
      Phase 2 (T=31-80): Voie_seg_18   → ORANGE
      Phase 3 (T=46-95): Pont Rail_3   → RED (bridge soffit)
      Phase 4 (T=71-112):Voie_seg_14   → RED (track submergence)
      Peak RED: T=85 (Sections 11, 13, 14 all RED)
    """
    grouped_path = paths.PROCESSED / "z_config_grouped.json"
    wse_path = paths.PROCESSED / "hecras_wse_demo_showcase.json"

    assert grouped_path.exists(), "z_config_grouped.json must exist"
    assert wse_path.exists(), "hecras_wse_demo_showcase.json must exist"

    with open(grouped_path, "r", encoding="utf-8") as f:
        grouped_cfg = json.load(f)
    with open(wse_path, "r", encoding="utf-8") as f:
        wse_results = json.load(f)

    dispatcher = AlertDispatcher()

    # 1. T=0: starts completely GREEN
    alerts_t0 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=0)
    summary_t0 = dispatcher.summarise_system(alerts_t0)
    assert summary_t0["overall_status"] == "GREEN", \
        f"Expected GREEN at T=0, got {summary_t0['overall_status']}"

    # 2. T=7: Section_19 drainage ditch reaches ORANGE zone
    alerts_t7 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=7)
    summary_t7 = dispatcher.summarise_system(alerts_t7)
    assert summary_t7["overall_status"] == "ORANGE", \
        f"Expected ORANGE at T=7, got {summary_t7['overall_status']}"

    # 3. T=85: peak RED — bridge soffit and track submergence
    alerts_t85 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=85)
    summary_t85 = dispatcher.summarise_system(alerts_t85)
    assert summary_t85["overall_status"] == "RED", \
        f"Expected RED at T=85, got {summary_t85['overall_status']}"
    assert summary_t85["counts"]["RED"] == 3, \
        f"Expected 3 RED groups at T=85, got {summary_t85['counts'].get('RED', 0)}"
    assert summary_t85["counts"]["ORANGE"] == 2, \
        f"Expected 2 ORANGE groups at T=85, got {summary_t85['counts'].get('ORANGE', 0)}"

    # Verify the RED group IDs at peak
    red_groups = sorted([g["group_id"] for g in alerts_t85 if g["status"] == "RED"])
    assert red_groups == ["Section_11", "Section_13", "Section_14"], \
        f"Unexpected RED groups at peak: {red_groups}"

    # 4. T=95: recession back to ORANGE (all REDs cleared)
    alerts_t95 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=95)
    summary_t95 = dispatcher.summarise_system(alerts_t95)
    assert summary_t95["overall_status"] == "ORANGE", \
        f"Expected ORANGE at T=95 (recession), got {summary_t95['overall_status']}"
    assert summary_t95["counts"].get("RED", 0) == 0, \
        f"Expected 0 RED groups at T=95, got {summary_t95['counts'].get('RED', 0)}"

