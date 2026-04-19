# 🤖 AI Instructions: Project Quick Start

This file covers how to brief **any AI assistant** — including Antigravity and GitHub Copilot — so they work effectively within the project rules.

---

## Option A: Using Antigravity (Full Agent)

Antigravity is the recommended AI for complex tasks like environment setup, multi-file edits, and milestone execution. Copy the prompt below and paste it into the Antigravity chat.

### COPY THIS PROMPT:

> "Hi! I am a team member on the Railway Flood-Risk Digital Twin project.
>
> 1. We use a local `.conda` environment inside the project root on my `C:` drive.
> 2. Large data (3GB) is on a Google Shared Drive.
> 3. **Please read and strictly follow all rules in `docs/antigravity_rules.md` for every operation.**
>
> **Please perform these steps:**
> - [ ] Run `./setup_team.ps1` to create my local environment.
> - [ ] Check if I have a `.env` file. If not, help me create one.
> - [ ] Set `DATA_ROOT` in `.env` to my Google Shared Drive path.
> - [ ] Run `python src/utils/check_health.py` to verify my setup.
> - [ ] Confirm `src/utils/paths.py` can resolve the DTM file.
>
> Let's get started!"

---

## Option B: Using GitHub Copilot (Inline Suggestions)

GitHub Copilot works inside VS Code to suggest code completions. It does **not** read chat prompts automatically, so follow these steps to keep it aligned with the project:

### Step 1: Add a `.github/copilot-instructions.md` file (already set up by Tin)
This file tells Copilot about the project context automatically when you open the repo.

### Step 2: Follow These Rules for Copilot
- **Always review** Copilot's suggestions before accepting — it does not know your team's `paths.py` pattern unless you show it.
- **If Copilot uses a hardcoded path**, reject it and type the correct `paths.DATA` pattern manually.
- **After using Copilot for a significant feature**, log the change in `docs/version_ledger.md` with the note `"AI-assisted"`.

### Step 3: Copilot Briefing Comment
At the top of any new Python file, add this comment block so Copilot has context:
```python
# PROJECT: Railway Flood-Risk Digital Twin
# PATHS: Use src/utils/paths.py — never hardcode absolute paths.
# DB: Connect via DATABASE_URL in .env using psycopg/sqlalchemy.
# STYLE: Follow PEP8. Add docstrings to all functions.
```

---

## 💡 How to Brainstorm with Any AI
1. **Ask for Research**: *"Search for the latest methods in [topic] and summarize the top 3 for our Research Log."*
2. **Create a Sandbox**: *"Let's create a new Brainstorming document for our ideas on [topic]."*
3. **Evaluate Impact**: *"How would this idea affect our Case Study? Categorize by Effort vs. Research Value."*

---

## 📜 Rules All AI Tools Must Follow
See [`docs/antigravity_rules.md`](../antigravity_rules.md) — these rules apply regardless of which AI tool you use.
