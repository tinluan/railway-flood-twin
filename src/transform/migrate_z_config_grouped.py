"""
F5.2 — Migration script: flat z_config.json → grouped z_config_grouped.json
=============================================================================
Groups all assets by their nearest track segment (nearest_voie), creating
unified Track-Talus + Drainage sections per the F5 architecture.

Run from project root:
    python src/transform/migrate_z_config_grouped.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC  = ROOT / "data" / "processed" / "z_config.json"
DST  = ROOT / "data" / "processed" / "z_config_grouped.json"

# Asset categories
TRACK_TYPES    = {"Voie_seg"}
TALUS_TYPES    = {"Talus Terre"}
DRAINAGE_TYPES = {"Buse", "Dalot", "Fosse terre revetu", "Fosse terre"}
BRIDGE_TYPES   = {"Pont Rail"}
TUNNEL_TYPES   = {"Tunnel"}

def asset_category(asset_id: str) -> str:
    """Return the broad category of an asset from its ID prefix."""
    for t in TRACK_TYPES:
        if asset_id.startswith(t):
            return "track"
    for t in TALUS_TYPES:
        if asset_id.startswith(t):
            return "talus"
    for t in BRIDGE_TYPES:
        if asset_id.startswith(t):
            return "bridge"
    for t in TUNNEL_TYPES:
        if asset_id.startswith(t):
            return "tunnel"
    for t in DRAINAGE_TYPES:
        if asset_id.startswith(t):
            return "drainage"
    return "unknown"

def drainage_asset_type(asset_id: str) -> str:
    """Return a human-readable type label for drainage assets."""
    if asset_id.startswith("Buse"):
        return "Circular Culvert"
    if asset_id.startswith("Dalot"):
        return "Rectangular Culvert"
    if asset_id.startswith("Fosse terre revetu"):
        return "Concrete-Lined Ditch"
    if asset_id.startswith("Fosse terre"):
        return "Earthen Ditch"
    return "Unknown Drainage"

def seg_sort_key(seg_id: str) -> int:
    """Sort Voie_seg_XX by segment number."""
    m = re.search(r"(\d+)$", seg_id)
    return int(m.group(1)) if m else 9999

def migrate(src_path: Path, dst_path: Path) -> None:
    with open(src_path, "r", encoding="utf-8") as f:
        flat = json.load(f)

    # ------------------------------------------------------------------
    # Step 1: Gather all Voie_seg entries -> one group per segment
    # ------------------------------------------------------------------
    groups: dict = {}

    # First pass: create group skeletons from Voie_seg entries
    for asset_id, cfg in flat.items():
        if not asset_id.startswith("Voie_seg"):
            continue
        seg_num = asset_id.split("_")[-1]
        group_key = f"Section_{seg_num}"

        groups[group_key] = {
            "group_id":   group_key,
            "voie_id":    asset_id,
            "track_talus": {
                "track_id":    asset_id,
                "talus_id":    cfg.get("nearest_talus", None),  # will be updated below
                "z_dtm_m":     cfg["red_z_m"],          # red_z = top-of-rail DTM
                "yellow_z_m":  cfg["yellow_z_m"],       # yellow = -2m from rail
                "orange_z_m":  cfg["orange_z_m"],       # orange = -0.5m from rail
                "red_z_m":     cfg["red_z_m"],           # red = top of rail (submergence)
            },
            "drainage_assets": [],
            "bridges":         [],     # Pont Rail assets servicing this section
            "tunnels":         [],     # Tunnel assets (if any)
        }

    # ------------------------------------------------------------------
    # Step 2: Assign Talus entries to groups
    # ------------------------------------------------------------------
    for asset_id, cfg in flat.items():
        cat = asset_category(asset_id)
        if cat != "talus":
            continue
        nearest_voie = cfg.get("nearest_voie")
        if not nearest_voie:
            continue
        seg_num = nearest_voie.split("_")[-1]
        gk = f"Section_{seg_num}"
        if gk not in groups:
            continue
        # Set the talus_id on track_talus if it isn't set yet
        if groups[gk]["track_talus"]["talus_id"] is None:
            groups[gk]["track_talus"]["talus_id"] = asset_id

    # ------------------------------------------------------------------
    # Step 3: Assign drainage/bridge/tunnel assets to groups
    # ------------------------------------------------------------------
    for asset_id, cfg in flat.items():
        cat = asset_category(asset_id)
        if cat not in ("drainage", "bridge", "tunnel"):
            continue
        nearest_voie = cfg.get("nearest_voie")
        if not nearest_voie:
            continue
        seg_num = nearest_voie.split("_")[-1]
        gk = f"Section_{seg_num}"
        if gk not in groups:
            continue

        if cat == "drainage":
            # Infer physical dimensions from threshold spacing:
            #   yellow = invert bottom, orange = mid-height, red = top of asset
            yellow_z = cfg["yellow_z_m"]
            red_z    = cfg["red_z_m"]
            height_m = round(red_z - yellow_z, 3)
            groups[gk]["drainage_assets"].append({
                "id":              asset_id,
                "type":            drainage_asset_type(asset_id),
                "invert_bottom_m": yellow_z,
                "height_m":        height_m,
                "yellow_z_m":      yellow_z,
                "orange_z_m":      cfg["orange_z_m"],
                "red_z_m":         red_z,
            })

        elif cat == "bridge":
            groups[gk]["bridges"].append({
                "id":         asset_id,
                "type":       "Railway Bridge",
                "yellow_z_m": cfg["yellow_z_m"],
                "orange_z_m": cfg["orange_z_m"],
                "red_z_m":    cfg["red_z_m"],
            })

        elif cat == "tunnel":
            groups[gk]["tunnels"].append({
                "id":         asset_id,
                "type":       "Tunnel",
                "yellow_z_m": cfg["yellow_z_m"],
                "orange_z_m": cfg["orange_z_m"],
                "red_z_m":    cfg["red_z_m"],
            })

    # ------------------------------------------------------------------
    # Step 4: Sort groups by segment number and write output
    # ------------------------------------------------------------------
    sorted_groups = dict(
        sorted(groups.items(), key=lambda kv: seg_sort_key(kv[0]))
    )

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(sorted_groups, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Summary report
    # ------------------------------------------------------------------
    print(f"Migration complete -> {dst_path}")
    print(f"  Sections created  : {len(sorted_groups)}")
    total_drainage = sum(len(g["drainage_assets"]) for g in sorted_groups.values())
    total_bridges  = sum(len(g["bridges"])          for g in sorted_groups.values())
    total_tunnels  = sum(len(g["tunnels"])           for g in sorted_groups.values())
    print(f"  Drainage assets   : {total_drainage}")
    print(f"  Bridge assets     : {total_bridges}")
    print(f"  Tunnel assets     : {total_tunnels}")

    # Show sample group
    sample_key = list(sorted_groups.keys())[10]  # Section_10 or nearby
    print(f"\nSample group '{sample_key}':")
    print(json.dumps(sorted_groups[sample_key], indent=4))


if __name__ == "__main__":
    migrate(SRC, DST)
