# Team Workflow Guide: Railway Flood-Risk Digital Twin

This guide defines how **Tin**, **Szilvi**, and **Amal** will collaborate on this student project using GitHub, Google Shared Drive, and Supabase.

---

## 1. Team Roles

To prevent "too many cooks in the kitchen," we suggest the following primary responsibilities:

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
1.  **`git pull`**: Get the latest changes from your teammates.
2.  **Work**: Write your code.
3.  **`git add .`** & **`git commit -m "Briefly explain what you did"`**.
4.  **`git push`**: Send your changes to GitHub for Tin, Szilvi, and Amal to see.

---

## 4. Shared Database (Supabase)

We use **one central database** for the whole team.
*   **Connection**: Everyone connects using the same `SUPABASE_URL` and `SUPABASE_KEY`.
*   **Coordination**: If you want to change a table structure (add a column, etc.), **Discord/Message the team first**. Changing a table might break your teammates' scripts!

---

## 5. Coding Standards

*   **Portability**: Always use `pathlib` for file paths so the code works on everyone's computer.
*   **Environment**: Use the `environment.yml` or `requirements.txt` to keep Python libraries identical.
*   **Comments**: If you write a complex function, add a `# Comment` explaining to your teammates what it does.
*   **AI Pair Programming**: If you use Antigravity, ensure it adheres to the [Antigravity Rules](antigravity_rules.md).

---

## 6. Academic Workflow & Reporting

*   **Research Log**: Every time you make a finding, add a quick note to `docs/research_log.md`. This is our "rough draft" for the final paper.
*   **Figures & Tables**: Always save plot exports to `report/figures/`. Use the `src/utils/viz.py` module to keep the colors and fonts consistent.
*   **Drafting**: Use `report/drafts/` for writing your sections. This makes it easy for Tin to review them before we move them into the final Microsoft Word report.

---

## 7. Communication & Progress

*   **Task Tracker**: Update `docs/task_tracker.md` whenever you finish a major task.
*   **Meetings**: A quick 10-minute sync once a week to show what you've built.
