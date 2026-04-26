# Railway Flood-Risk Digital Twin

Welcome to the SNCF Railway Flood-Risk Digital Twin project! This repository contains the code for a 48-hour predictive simulation of flood risks along the `Ligne_400` corridor.

## 🚀 Teammate Quickstart Guide (VS Code)

If this is your first time opening this project in VS Code, follow these 4 simple steps to get the Digital Twin running on your machine:

### Step 1: Run the Automated Setup Script
Open your VS Code Terminal (`Ctrl + \``) and run the setup script. This will automatically create an isolated Python environment and install all dependencies:
```powershell
./setup_team.ps1
```
*(During setup, it may ask you to input the path to our shared Google Drive Data folder. Paste the path so the app knows where to find the heavy `.tif` and `.gpkg` files).*

### Step 2: Tell VS Code which Python to use
1. Press `Ctrl + Shift + P` (or `Cmd + Shift + P` on Mac) to open the Command Palette.
2. Type and select **`Python: Select Interpreter`**.
3. Choose the interpreter located inside the newly created `./.conda/` folder (e.g., `./.conda/python.exe`).

### Step 3: Run the Dashboard
In your terminal, start the Streamlit Digital Twin application using our local conda environment:
```powershell
.\.conda\python.exe -m streamlit run src/dashboard/app_main.py
```
This will open the dashboard in your web browser.

### Step 4: AI Handoff
If you are using GitHub Copilot to help you write code, please open the **`AI_HANDOFF.md`** file first so your AI understands the project's engineering rules.

---

## 📂 Project Architecture
Please read **`ARCHITECTURE.md`** to understand the engineering logic behind our Red/Orange/Yellow alerts and how the cross-sections are generated.

## 📌 Current Status & Tasks
Check **`STATUS.md`** to see what tasks are currently in progress and what you should work on next.
