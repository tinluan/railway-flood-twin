# 🚞 Onboarding: Railway Flood-Risk Digital Twin

Welcome to the team! This guide will help you set up your local environment on your private laptop so you can work seamlessly with Tin and the rest of the team.

---

## 🏗️ The Project Architecture
- **GitHub (Logic)**: All your scripts, SQL, and documentation. You clone this to your **LOCAL C: DRIVE**.
- **Google Shared Drive (Data)**: All large rasters (DTM) and GIS files. You **LINK** this via a setting in your code.
- **Supabase (Database)**: One central database that everyone connects to.

---

## 🚀 3-Step Quick Start

### Step 1: Clone from GitHub
Open your terminal and clone the project to a folder on your **C: drive** (e.g., `C:\Work\railway-flood-twin`).
```bash
git clone https://github.com/tinluan/railway-flood-twin.git
```

### Step 2: Automated Setup (AI or Manual)
We have two ways to set up your Python environment:

*   **Option A (AI - Recommended)**: Open this folder in your IDE (VS Code) and follow the instructions in [AI_INSTRUCTIONS.md](AI_INSTRUCTIONS.md). Paste the prompt into your AI agent (Antigravity), and it will do the work for you.
*   **Option B (Manual)**: Right-click **`setup_team.ps1`** and select "Run with PowerShell." It will create a local `.conda` environment and install all libraries.

### Step 3: Configure your Data Link
Once the environment is ready, open your `.env` file and set your `DATA_ROOT`:
```text
DATA_ROOT=G:\Shared drives\DigiTwin\railway-flood-twin\data
```
*(Update the drive letter G: if yours is different).*

---

## 📜 Working Rules
Please read the [Antigravity Rules](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/antigravity_rules.md) and the [Team Workflow Guide](file:///c:/Users/ktstr/Documents/railway-flood-twin/docs/team_workflow_guide.md) before making your first commit.

Happy engineering!
