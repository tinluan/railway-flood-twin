# 🚀 5-Step Team Onboarding Guide

Tin, send this guide to **Szilvi** and **Amal** to get them set up on their private laptops.

---

### Step 0: GitHub Invitation (Action for Tin)
- [ ] Go to the [GitHub Repo Settings](https://github.com/tinluan/railway-flood-twin/settings/access) and invite Szilvi and Amal as **Collaborators**.

---

### Step 1: Create a Local C: Folder
- Create a folder on your **C: drive** (e.g., `C:\Master_Project\railway-flood-twin`).
- *Warning*: Do not use your Google Drive folder for the code; it will cause errors during analysis.

### Step 2: Clone the Code
Open your terminal/command prompt and run:
```bash
git clone https://github.com/tinluan/railway-flood-twin.git
```

### Step 3: Run the Setup Script
- In your new folder, right-click **`setup_team.ps1`** and select **"Run with PowerShell."**
- This will automatically create your Python environment and install all GIS libraries.

### Step 4: Link your Shared Data
- When the script asks, paste the path to your **Google Shared Drive "data" folder** (e.g., `G:\Shared drives\DigiTwin\railway-flood-twin\data`).
- This will create your local `.env` file automatically.

### Step 5: Start your AI Assistant
- Open the project in VS Code.
- Open `docs/onboarding/AI_INSTRUCTIONS.md`.
- Copy the prompt and paste it into **Antigravity**.
- *Result*: Your AI is now briefed on the project and ready to help you with your specific role!

---
*For more details, see `docs/onboarding/README.md`*
