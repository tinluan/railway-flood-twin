# Team Workflow Guide: Railway Flood-Risk Digital Twin

This guide defines how **Tin**, **Szilvi**, and **Amal** will collaborate on this student project using GitHub, Google Shared Drive, and Supabase.

---

## 1. Team Roles

To prevent "too many cooks in the kitchen," we assign clear primary responsibilities:

| Name | Role | Primary Responsibilities |
| :--- | :--- | :--- |
| **Tin** | **Project Lead & DBA** | GitHub Admin, Supabase Schema, `task_tracker.md`, Overall Integration. |
| **Szilvi** | **GIS Specialist** | DTM Rasters, Vector Layer Cleaning (QGIS/Python), Coordinate Systems (CRS). |
| **Amal** | **Backend Developer** | Risk Engine logic, Python Analytics, API development, SQL Queries. |

---

## 2. The "Golden Rule" of Data vs. Code

To prevent project corruption and Google Drive sync errors:

*   **GitHub (Small Files)**: Use for your `.py` scripts, `.sql` files, and `.md` documentation.
    *   *Rule: Never upload a file larger than 50MB to GitHub.*
*   **Google Shared Drive (Large Data)**: Use for the `data/` folder (Rasters, Shapefiles, `.zip` backups).
    *   *Rule: Never initialize Git inside the Google Shared Drive folders.*

---

## 3. GitHub Collaborative Workflow

### Step 1: Clone to your LOCAL `C:` drive
All three members must clone the code repository to their own computer's local hard drive (e.g., `C:\Users\Documents\Project`).

### Step 2: The "Sync" Routine
Before you start working and after you finish, follow this sequence:
1.  **`git checkout <your-branch>`**: Never work directly on `main`. Create a branch for your task.
2.  **`git pull origin main`**: Get the latest stable updates.
3.  **Work**: Write your code.
4.  **`git commit -m "..."`**: Save your progress.
5.  **`git push origin <your-branch>`**: Send your branch to GitHub.
6.  **Open Pull Request**: Go to GitHub and open a PR into `main`. Tin will review it.

### Step 3: Commit Message Convention
Use a consistent commit format so anyone can read the history without guessing:

| Prefix | When to use |
| :--- | :--- |
| `feat:` | Adding a new script or significant new functionality |
| `fix:` | Fixing a bug or broken output |
| `docs:` | Adding or updating documentation / markdown |
| `data:` | Adding, cleaning, or updating GIS/raster data references |
| `refactor:` | Restructuring code without changing its behaviour |
| `test:` | Adding or running validation/test scripts |

**Examples:**
```
feat: add terrain elevation summary for track_area polygons
fix: correct CRS mismatch in voie_fixed.gpkg loading
docs: update version_ledger with milestone 3 results
```

---

## 4. Shared Database (Supabase)

We use **one central database** for the whole team.
*   **Connection**: Everyone connects using the same `DATABASE_URL` in their `.env`.
*   **Coordination**: If you want to change a table structure (add a column, etc.), **message the team first** (Discord/WhatsApp). Changing a table might break your teammates' scripts!

---

## 5. Coding Standards

*   **Portability**: Always use `pathlib` via `src/utils/paths.py` — never hardcode absolute paths.
*   **Environment**: Use `requirements.txt` to keep Python libraries identical across machines.
*   **Comments**: If you write a complex function, add a docstring and inline comments for your teammates.
*   **AI Pair Programming**: If you use any AI tool, it must follow the rules in [`docs/antigravity_rules.md`](antigravity_rules.md).

---

## 6. Cross-Job Change Management

If you need to edit a file **outside your primary role** (e.g., Tin modifies Szilvi's GIS script):

1.  **Notify the owner**: Send a message before or immediately after the change.
2.  **Log it**: Add an entry to [`docs/version_ledger.md`](version_ledger.md) under the "Cross-Job Change Register."
3.  **Commit with context**: Use a commit message like `fix(gis): correct CRS in voie script — see version_ledger`.
4.  **Do not silently refactor**: Never rename, reorganize, or delete someone else's logic without explicit approval.

> 💡 **Calling back old versions**: Use `git log --oneline` to find the hash of the last "Well-Run" state, then `git checkout <hash> -- <file>` to restore it.

---

## 7. Academic Workflow & Reporting

*   **Research Log**: Every time you make a finding, add a note to `docs/research_log.md`. This is our "rough draft" for the final paper.
*   **Figures & Tables**: Always save plot exports to `report/figures/`. Use `src/utils/viz.py` to keep colors and fonts consistent.
*   **Drafting**: Use `report/drafts/` for writing your sections so Tin can review them before they go into the final report.

---

## 8. Communication & Progress

*   **Task Tracker**: Update `docs/task_tracker.md` whenever you finish a major task.
*   **Version Ledger**: Log all "big" changes — especially Well-Run validations and Cross-Job modifications — in `docs/version_ledger.md`.
*   **Meetings**: A quick 10-minute sync once a week to show what you have built.

---

## 9. Release Strategy & Safety

To prevent "Trials" from breaking the "Final" version:

### The "Stable Main" Rule
- **Main Branch**: Only push code to `main` if it is **Well-Run** and passes the `check_health.py`.
- **Trial Branches**: If you are experimenting, create a local branch (`git checkout -b <name>-trial`). Only merge it to `main` when it is stable.

### Creating a "Final" Version (Tags)
When a Milestone is complete, Tin will create a **Git Tag**. This "freezes" the code so you can always return to it.
- **To Create**: `git tag -a v1.0-m2 -m "Final version for Milestone 2"`
- **To Return to a Release**: `git checkout v1.0-m2`

### The 3-Step Quality Gate (Checklist for Merging to Main)
Before merging any "Trial" code into the `main` branch, the developer must verify:

1.  **Output Validation**: The script has run successfully and produced the expected data (e.g., a CSV with plausible numbers, a report figure, or a updated database table).
2.  **Environment Health**: Run `python src/utils/check_health.py` and ensure it returns **SUCCESS**.
3.  **Engineering Standards**: Code uses `paths.py` (no absolute paths), includes comments, and has been updated in the [`version_ledger.md`](version_ledger.md).

### The Version Ledger
Always check [`docs/version_ledger.md`](version_ledger.md) before starting work. If a component is marked as `Trial` 🔬, do not rely on its output for your final report yet. Only use components marked as `Well-Run` ✅.

---

## 10. The Approval Process (Hard Lock)

The `main` branch is protected. No one can push to it directly.

### How to get your code into Main:
1.  **Submit**: Open a Pull Request from your branch.
2.  **AI Review**: Antigravity (Tin's assistant) will automatically review the code for path standards and health.
3.  **Human Approval**: Tin will review the AI's report.
4.  **Merge**: Tin (or Antigravity with Tin's permission) will click "Merge Pull Request."

*This ensures the project remains 100% stable and "Well-Run" at all times.*

