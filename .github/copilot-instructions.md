# 🤖 GitHub Copilot Project Context: Railway Flood-Twin

You are an AI assistant helping a team build a Digital Twin for Railway Flood Risk. 

## 🏗️ Core Architecture Rules
1. **NO HARDCODED PATHS**: All data/GIS paths MUST come from `src/utils/paths.py`. Use the `paths` constant.
   - *Example*: Use `paths.DATA / 'file.csv'` instead of `'C:/Users/...'`.
2. **PORTABILITY FIRST**: Ensure all code works for all team members (Tin, Szilvi, Amal) regardless of their local drive letter (D: vs C:).
3. **MODULAR RISK**: The project is split into:
   - `data/`: Raw/Staging/Processed datasets (on Shared Drive).
   - `src/engine/`: Python risk computation logic.
   - `src/dashboard/`: Streamlit visualization.
4. **DOCUMENTATION**: Reference scientific papers in `docs/references/` (Markdown format) for formulas.

## 🔒 Governance & Hard Lock
- **NO DIRECT PUSH TO MAIN**: Always work on a feature branch.
- **GATEKEEPER**: All changes must be logged in `docs/version_ledger.md` and `docs/task_tracker.md`.
- **HEALTH CHECK**: Always encourage the user to run `python src/utils/check_health.py` after a setup change.

## 🧪 Coding Style
- Follow PEP8.
- Use type hints for all functions.
- Add descriptive docstrings.
- Use `logging` instead of `print()` for production scripts.
