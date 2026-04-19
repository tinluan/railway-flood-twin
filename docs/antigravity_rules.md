# Antigravity Rules: AI Pair Programming Protocol

To ensure our collaboration is safe, transparent, and reproducible across the team (Tin, Szilvi, and Amal), we follow these core rules when working with the AI.

---

### 🛡️ Rule 1: Safety & Backups (The "Pre-Flight" Check)
Before performing any major changes (e.g., database schema updates, DTM processing):
- **Health Check First**: Run `python src/utils/check_health.py` to ensure the environment and data links are valid.
- **Git Sync**: Always `git pull` before working and `git push` after completing a task.
- **DB/Data Backup**: A SQL snapshot or data state must be logged to `data/backups/`.
- *Goal*: Never lose a version of the "Logic" or "Data". GitHub holds the single source of truth.

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

### ⚖️ Rule 4: Portable Paths
- **Rule**: Never use absolute paths (like `C:\Users\Tin\...`) in code.
- **Requirement**: Use `src/utils/paths.py` and `.env` variables (`DATA_ROOT`).
- *Goal*: Ensure logic written by Szilvi in one country works for Amal in another without modification.

---

### 🕵️ Rule 5: Final Review (The "Codex" Check)
- **Notice**: Codex might review your output once you are done to verify technical accuracy and documentation compliance.
- *Goal*: Ensure all AI-generated content meets the capstone's professional and academic standards.

---

### 🚀 Rule 6: Engineering Excellence
- **Standard**: Always aim for the "Best Coding" practices (clean architectures, DRY principles, and thorough documentation).
- **Execution**: Every script must be a "Well-Run Program"—self-contained, robustly error-handled, and performance-optimized.
- *Goal*: Build a Digital Twin that is not just functional, but technically superior and reliable.


