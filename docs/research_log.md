# 🧪 Research Log: Railway Flood-Risk Digital Twin Case Study

This log tracks the "daily" breakthroughs, anomalies, and key decisions. This content is designed to be copy-pasted directly into the **Methodology** and **Discussion** sections of your final Microsoft Word report.

---

## Log Template (Copy this for new entries)
### 🗓️ [YYYY-MM-DD] - [Brief Title]
- **Goal**: What were we trying to achieve?
- **Action**: What did we run/change?
- **Result**: Success or Fail?
- **Insight**: Why does this matter for the final report? (e.g. "We found the DTM needs EPSG:2154 to align with QGIS").

---

## 🏛️ Project Ledger

### 🗓️ 2026-04-18 - Project Infrastructure & GitHub Setup
- **Goal**: Transition from Google Drive to a professional local/remote hybrid setup.
- **Action**: Move project to `C:`, initialize Git, and push to [GitHub](https://github.com/tinluan/railway-flood-twin).
- **Result**: Success. Git and Conda installed and verified.
- **Insight**: Moving to local `C:` drive was necessary to avoid 1GB DTM file-locking errors on Google Drive. This decision will be documented in the **"Implementation Constraints"** section of the paper.

### 🗓️ 2026-04-18 - Academic Workflow Initialization
- **Goal**: Set up the repository for continuous report drafting.
- **Action**: Created `report/` and `presentation/` folders. Implemented `paths.py` for cross-border collaboration.
- **Result**: Success.
- **Insight**: Established a "Case Study" methodology. By isolating data roots via `.env`, we ensure reproducibility across different team members' hardware.
