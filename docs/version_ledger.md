# Version Ledger: Railway Flood-Risk Digital Twin

> **Purpose**: This is the **single source of truth** for all significant changes to the project — regardless of who made them (Tin, Szilvi, Amal, or an AI). It enables traceability, accountability, and the ability to "call back" any well-run version.

---

## How to Use This Ledger

| Column | Meaning |
| :--- | :--- |
| **Date** | When the change was made |
| **Author** | Who made the change (name or `AI:ToolName`) |
| **Component** | File(s) or system changed |
| **Git Hash** | Short hash from `git log --oneline` — use to revert |
| **Status** | `Well-Run` ✅ / `Trial` 🔬 / `Deprecated` ❌ |
| **Notes** | What changed, why, and any cross-job impact |

> To get the Git hash of the latest commit: `git log --oneline -5`
> To revert to a specific hash: `git checkout <hash> -- <file>`

---

## Change Log

| Date | Author | Component | Git Hash | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-03-29 | Tin | `data/staging/gis/` — all GIS layers | `5cadf50` | ✅ Well-Run | First cleaned GIS layers loaded into `rail.gis_asset`. 30 assets. SRID 2154. |
| 2026-03-30 | Tin + AI:Antigravity | `src/transform/derive_track_area_elevation_fast.py` | — | 🔬 Trial | First terrain elevation summary run. Outputs in `data/processed/terrain/`. Validation pending. |
| 2026-04-19 | Tin + AI:Antigravity | `docs/antigravity_rules.md`, `docs/onboarding/AI_INSTRUCTIONS.md`, `docs/team_workflow_guide.md` | `2150371` | ✅ Well-Run | Governance overhaul: AI rules made AI-agnostic, cross-job management added, version ledger created. |

---

## Cross-Job Change Register

Use this section when a team member edits a file **outside their primary role**. Log it here **and** notify the file owner.

| Date | Changed By | File Changed | Owner | Reason | Notified? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| *(example)* | Tin | `src/transform/derive_track_area_elevation.py` | Szilvi | Fixed CRS bug blocking milestone | ✅ Yes |

---

## Well-Run Script Registry

Scripts that have been validated and confirmed as the "trusted version" for their function.

| Script | Version / Hash | Validated By | Date | Output |
| :--- | :--- | :--- | :--- | :--- |
| `src/utils/paths.py` | `5cadf50` | Tin | 2026-03-29 | Correctly resolves all project paths from `.env` |
| `src/utils/check_health.py` | `5cadf50` | Tin | 2026-04-19 | All 4 checks pass on local machine |
| `src/transform/generate_docs_from_staging.py` | `5cadf50` | Tin | 2026-03-29 | Generated 4 docs from staging GIS files |
