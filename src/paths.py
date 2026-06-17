"""
src/paths.py — Legacy Path Resolver (Layer 2: Bridge)
=======================================================
This module resolves all filesystem paths for the Railway Flood-Risk Digital Twin.
It is the *original* flat-module version; newer code should use
``src/utils/paths.py`` (``ProjectPaths`` class) instead.

Architecture Position (Layer 2 — Bridge):
    - Bridges local machine paths with the remote Google Drive data root.
    - All engine modules (swi_calculator, data_ingestion, preprocessor) import
      from this module to avoid any hardcoded paths in business logic.
    - ``src/utils/paths.py`` is the successor and is used by the API layer.

Key Variables Exported:
    PROJECT_ROOT  — Root of the repository on the local machine
    DATA_ROOT     — Google Drive shared folder (G:/Shared drives/...)
    OUTPUT_ROOT   — Local outputs folder
    RAW_DATA      — DATA_ROOT/raw (incoming rainfall CSVs, raw GIS files)
    STAGING_DATA  — DATA_ROOT/staging (cleaned GeoPackages, fixed TIFFs)
    PROCESSED_DATA — DATA_ROOT/processed (SWI results, handoff segments)

Environment Variables (read from .env):
    PROJECT_ROOT  — Override if repo is cloned to a non-default path
    DATA_ROOT     — Override if Google Drive is mounted at a different letter
    OUTPUT_ROOT   — Override for CI/CD or server deployments

Relationship with other files:
    - ``src/engine/data_ingestion.py`` imports RAW_DATA, STAGING_DATA
    - ``src/engine/swi_calculator.py`` imports RAW_DATA, PROCESSED_DATA
    - ``src/engine/preprocessor.py``   imports STAGING_DATA, PROCESSED_DATA
    - ``src/engine/hec_ras_runner.py`` imports PROJECT_ROOT
    - Newer modules use ``src/utils/paths.py::ProjectPaths`` instead.

Example Usage:
    # From any engine module:
    from paths import RAW_DATA, PROCESSED_DATA
    df.to_csv(PROCESSED_DATA / "swi_results.csv", index=False)

    # Ensure output directories exist before writing:
    from paths import ensure_paths
    ensure_paths()

Run standalone to verify path resolution on a new machine:
    python src/paths.py
    # Expected output:
    #   Project Root: C:/Users/.../<repo_name>
    #   Data Root:    G:/Shared drives/DigiTwin/...
    #   Raw Data Path: G:/.../data/raw
    #   Creating missing directory: ...  (if outputs/logs don't exist)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Root Paths ---
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "C:/Users/ktstr/Documents/railway-flood-twin"))
DATA_ROOT = Path(os.getenv("DATA_ROOT", "G:/Shared drives/DigiTwin/railway-flood-twin/data"))
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "C:/Users/ktstr/Documents/railway-flood-twin/outputs"))

# --- Subdirectories (Data) ---
RAW_DATA = DATA_ROOT / "raw"
STAGING_DATA = DATA_ROOT / "staging"
PROCESSED_DATA = DATA_ROOT / "processed"
CONTEST_DATA = DATA_ROOT / "Contest"

# --- Subdirectories (Local) ---
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"
SRC_DIR = PROJECT_ROOT / "src"

def ensure_paths():
    """Ensure that critical local paths exist."""
    local_paths = [OUTPUT_ROOT, LOGS_DIR]
    for path in local_paths:
        if not path.exists():
            print(f"Creating missing directory: {path}")
            path.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    # Test path resolution
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Data Root: {DATA_ROOT}")
    print(f"Raw Data Path: {RAW_DATA}")
    ensure_paths()
