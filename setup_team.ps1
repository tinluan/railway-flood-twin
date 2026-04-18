# -------------------------------------------------------------------
# Setup Team Member Environment
# Railway Flood-Risk Digital Twin
# -------------------------------------------------------------------
#
# This script automates the installation of the local Python environment
# for Szilvi and Amal. It is designed to be "zero-footprint" on your 
# global system.
#
# Instructions:
# 1. Right-click this file and select "Run with PowerShell"
# 2. Or run in terminal: ./setup_team.ps1
# -------------------------------------------------------------------

$ErrorActionPreference = "Stop"

Write-Host "`n--- Railway Digital Twin: Team Onboarding ---" -ForegroundColor Cyan

# 1. Check for Conda
Write-Host "[1/4] Checking for Conda..." -NoNewline
$conda_path = "$env:USERPROFILE\anaconda3\Scripts\conda.exe"
if (-not (Test-Path $conda_path)) {
    $conda_path = "$env:USERPROFILE\miniconda3\Scripts\conda.exe"
}

if (-not (Test-Path $conda_path)) {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "Error: Conda not found in standard user paths." -ForegroundColor Red
    Write-Host "Please install Anaconda or Miniconda first, or update the script with your path."
    exit 1
}
Write-Host " FOUND at $conda_path" -ForegroundColor Green

# 2. Create Local Environment
Write-Host "[2/4] Creating local environment in ./.conda..."
if (Test-Path ".conda") {
    Write-Host " Local environment already exists. Skipping creation." -ForegroundColor Yellow
} else {
    & $conda_path create --prefix ./.conda python=3.9 -y
    Write-Host " Environment created." -ForegroundColor Green
}

# 3. Install Dependencies
Write-Host "[3/4] Installing dependencies from requirements.txt..."
$pip_path = "./.conda/Scripts/pip.exe"
if (-not (Test-Path $pip_path)) {
    $pip_path = "./.conda/bin/pip" # For Linux/Mac compatibility if needed in future
}

& $pip_path install -r requirements.txt
Write-Host " Dependencies installed." -ForegroundColor Green

# 4. Initialize .env file
Write-Host "[4/4] Configuring .env file..."
if (-not (Test-Path ".env")) {
    $db_url = Read-Host "Enter Supabase DATABASE_URL (or press Enter to skip)"
    $data_root = Read-Host "Enter path to your shared Data folder (e.g. G:\Shared drives\DigiTwin\railway-flood-twin\data)"
    
    $env_content = "DATABASE_URL=$db_url`nDATA_ROOT=$data_root"
    Set-Content -Path ".env" -Value $env_content
    Write-Host " .env file created." -ForegroundColor Green
} else {
    Write-Host " .env already exists. Update it manually if your Data path is different." -ForegroundColor Yellow
}

Write-Host "`n[SUCCESS] Onboarding Complete!" -ForegroundColor Cyan
Write-Host "You can now open this folder in VS Code and start the DTM Analysis."
Write-Host "Logic/Docs: On your local C: drive (GitHub)"
Write-Host "Large Data: On the Google Shared Drive (linked via .env)"
