# Antigravity Rules: AI Pair Programming Protocol

To ensure our collaboration is safe, transparent, and reproducible across the team (Tin, Szilvi, and Amal), we follow these core rules when working with the AI.

---

### 🛡️ Rule 1: The "Pre-Flight" Snapshot
Before performing any major changes (e.g., database schema updates or large data processing):
- **Git Commit**: Antigravity will commit the current stable state.
- **DB Backup**: A SQL snapshot will be saved to `data/backups/`.
- *Goal*: Never lose a version of the "Logic" or "Data".

### 🗺️ Rule 2: The "Blueprint" Policy
For any task categorized as a "High Priority" or "Milestone":
- **Implementation Plan**: Antigravity will present a written design for review.
- **Authorization**: The human team member must give a "Yes" before any code is modified.
- *Goal*: The team always maintains structural control over the Digital Twin.

### 📝 Rule 3: The "Live Ledger" (Task Tracking)
Antigravity is responsible for administrative transparency:
- Update `docs/task_tracker.md` after every major milestone.
- Maintain a local `task.md` for daily technical items.
- *Goal*: Anyone on the team can see the project status without asking.

### 🚀 Rule 4: The "Final Sync"
At the end of every work session:
- **Git Push**: All logic and documentation is pushed to GitHub.
- **Summary**: A walkthrough of changes is provided.
- *Goal*: GitHub always holds the "Single Source of Truth."

---

### ⚖️ Rule 5: Portable Paths
- **Rule**: Never use absolute paths (like `C:\Users\Tin\...`) in code.
- **Requirement**: Use `src/utils/paths.py` and `.env` variables.
- *Goal*: Ensure logic written by Szilvi in one country works for Amal in another.
