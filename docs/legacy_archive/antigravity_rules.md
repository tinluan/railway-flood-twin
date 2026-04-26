# AI Collaboration Rules: Pair Programming Protocol

> These rules apply to **all AI tools** used in this project — including Antigravity, GitHub Copilot, ChatGPT, or any other AI assistant. Every team member (Tin, Szilvi, Amal) must follow these rules when using AI support.

---

### 🛡️ Rule 1: Safety & Backups (The "Pre-Flight" Check)
Before performing any major changes (e.g., database schema updates, DTM processing):
- **Health Check First**: Run `python src/utils/check_health.py` to ensure the environment and data links are valid.
- **Git Sync**: Always `git pull origin main` to a branch before working, and submit your work via a **Pull Request (PR)**.
- **DB/Data Backup**: A SQL snapshot or data state must be logged to `data/backups/`.
- *Goal*: Never lose a version of the "Logic" or "Data". GitHub holds the single source of truth.

---

### 🗺️ Rule 2: The "Blueprint" Policy
For any task categorized as a "High Priority" or "Milestone":
- **Implementation Plan**: The AI must present a written step-by-step plan for review **before** executing.
- **Authorization**: The human team member must give an explicit "Yes" before any code is modified.
- *Goal*: The team always maintains structural control over the Digital Twin.

---

### 📝 Rule 3: The "Live Ledger" (Task Tracking)
AI assistants are responsible for administrative transparency:
- Update `docs/task_tracker.md` after every major milestone.
- Log all significant changes in `docs/version_ledger.md` (who changed what, when, and the Git hash).
- *Goal*: Anyone on the team can see the project status without asking.

---

### ⚖️ Rule 4: Portable Paths
- **Rule**: Never use absolute paths (like `C:\Users\Tin\...`) in code.
- **Requirement**: Use `src/utils/paths.py` and `.env` variables (`DATA_ROOT`).
- *Goal*: Ensure logic written by Szilvi in one country works for Amal in another without modification.

---

### 🔀 Rule 5: Cross-Job Change Management
If an AI (or a team member) edits a file **outside** their primary role area:
- **Notify**: Message the file owner (on Discord/WhatsApp) to explain what and why you changed.
- **Log it**: Add an entry to `docs/version_ledger.md` with the date, your name, the file, and the reason.
- **Do not refactor silently**: Never rename, restructure, or delete another member's logic without approval.
- *Goal*: Prevent silent breakage. Every change that affects another person's work must be traceable.

---

### 🕵️ Rule 6: Final Review (The "Codex" Check)
- **Notice**: AI output may be reviewed by a second AI or human reviewer to verify technical accuracy and documentation compliance.
- *Goal*: Ensure all AI-generated content meets the capstone's professional and academic standards.

---

### 🚀 Rule 7: Engineering Excellence
- **Standard**: Always aim for the "Best Coding" practices (clean architecture, DRY principles, thorough documentation).
- **Execution**: Every script must be a "Well-Run Program" — self-contained, robustly error-handled, and performance-optimized.
- **Verification**: If an AI produces a script, it must be run and its output validated before being marked "Well-Run" in the version ledger.
- *Goal*: Build a Digital Twin that is not just functional, but technically superior and reliable.

---

| Complex multi-step coding, project setup, file creation | **Antigravity** (full agent) |
| Quick code completion, single-function suggestions | **GitHub Copilot** (inline) |
| Research, explanations, academic writing | **ChatGPT / Gemini** (chat) |

---

### 🛡️ Rule 8: The "Hard Lock" (PR Policy)
- **Rule**: No one pushes directly to the `main` branch. 
- **Requirement**: All code must be submitted via a **Pull Request**. The Lead (Tin) must approve the PR before it is merged.
- *Goal*: Prevent accidental breakage and ensure human-in-the-loop review.

---

### 🤖 Rule 9: The "Assistant Gatekeeper" Role
- **Requirement**: Antigravity serves as the first-line reviewer for team PRs. 
- **Function**: The AI will scan PRs for absolute paths, health check compliance, and documentation before the Lead performs the final approval.
- *Goal*: Automate code review so the Lead can focus on high-level decisions.

---

### 💡 Which AI tool should I use?
| Task | Recommended Tool |
| :--- | :--- |
| Complex multi-step coding, project setup, file creation | **Antigravity** (full agent) |
| Quick code completion, single-function suggestions | **GitHub Copilot** (inline) |
| Research, explanations, academic writing | **ChatGPT / Gemini** (chat) |

> All tools must adhere to the same rules above. The **human is always the final authority**.
