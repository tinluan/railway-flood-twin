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
