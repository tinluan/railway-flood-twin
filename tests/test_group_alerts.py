import json
from pathlib import Path
from src.engine.alert_dispatcher import AlertDispatcher
from src.utils.paths import paths

def test_alert_logic_sept_2025_scenario():
    """
    F5.5 - Test group alert logic with the historical Sept 2025 Cevenol storm scenario (Plan P02).
    Verifies that group statuses correctly transition over time:
      - Starts completely GREEN (T=0)
      - Becomes ORANGE as the flood rises (T=7)
      - Peak has multiple ORANGE/YELLOW alerts (T=26)
    """
    grouped_path = paths.PROCESSED / "z_config_grouped.json"
    wse_path = paths.PROCESSED / "hecras_wse_p02_dashboard.json"

    assert grouped_path.exists(), "z_config_grouped.json must exist"
    assert wse_path.exists(), "hecras_wse_p02_dashboard.json must exist"

    with open(grouped_path, "r", encoding="utf-8") as f:
        grouped_cfg = json.load(f)
    with open(wse_path, "r", encoding="utf-8") as f:
        wse_results = json.load(f)

    dispatcher = AlertDispatcher()

    # 1. Test timestep 0 (starts clean / GREEN due to dry cell filtering)
    alerts_t0 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=0)
    summary_t0 = dispatcher.summarise_system(alerts_t0)
    assert summary_t0["overall_status"] == "GREEN"
    assert summary_t0["counts"]["GREEN"] == 21
    assert summary_t0["counts"]["RED"] == 0
    assert summary_t0["counts"]["ORANGE"] == 0
    assert summary_t0["counts"]["YELLOW"] == 0

    # 2. Test timestep 7 (transitions to ORANGE)
    alerts_t7 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=7)
    summary_t7 = dispatcher.summarise_system(alerts_t7)
    assert summary_t7["overall_status"] == "ORANGE"
    assert summary_t7["counts"]["ORANGE"] == 1
    assert summary_t7["counts"]["YELLOW"] == 2

    # 3. Test peak timestep 26 (peak intensity)
    alerts_t26 = dispatcher.evaluate_all_groups(grouped_cfg, wse_results, timestep_idx=26)
    summary_t26 = dispatcher.summarise_system(alerts_t26)
    assert summary_t26["overall_status"] == "ORANGE"
    assert summary_t26["counts"]["ORANGE"] == 2
    assert summary_t26["counts"]["YELLOW"] == 4
    
    # Verify group order (worst first)
    assert alerts_t26[0]["status"] == "ORANGE"
    assert alerts_t26[1]["status"] == "ORANGE"
    orange_groups = sorted([alerts_t26[0]["group_id"], alerts_t26[1]["group_id"]])
    assert orange_groups == ["Section_18", "Section_19"]
