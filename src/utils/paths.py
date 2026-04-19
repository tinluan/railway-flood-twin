from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class ProjectPaths:
    """Manages project-wide paths, supporting local and remote shared data roots."""
    
    # The directory containing this file
    _INTERNAL_UTILS = Path(__file__).resolve().parent
    
    # Project Root (c:\Users\...\railway-flood-twin)
    # Move up 2 levels from src/utils/
    ROOT = _INTERNAL_UTILS.parents[1]
    
    # -------------------------------------------------------------------
    # DATA ROOT SELECTION
    # -------------------------------------------------------------------
    # Priority:
    # 1. DATA_ROOT from .env (Manual override for Google Drive / external disks)
    # 2. Local 'data' folder in the project root (Default if cloned with data)
    
    _env_data_root = os.getenv("DATA_ROOT")
    if _env_data_root:
        DATA = Path(_env_data_root)
    else:
        DATA = ROOT / "data"
        
    # Standard subdirectories
    RAW = DATA / "raw"
    STAGING = DATA / "staging"
    PROCESSED = DATA / "processed"
    
    # Specific Domain folders
    DTM_RAW = RAW / "dtm"
    GIS_STAGING = STAGING / "gis"
    TERRAIN_STAGING = STAGING / "terrain"
    TERRAIN_PROCESSED = PROCESSED / "terrain"
    REFERENCES = DATA / "references"
    REFERENCES_MD = DATA / "references" / "markdown"
    CONTEST = DATA / "contest"
    THESIS = DATA / "thesis"
    
    # Other root folders
    DOCS = ROOT / "docs"
    SQL = ROOT / "sql"
    SRC = ROOT / "src"
    OUTPUTS = ROOT / "outputs"
    NOTEBOOKS = ROOT / "notebooks"
    
    # Academic / Report folders
    REPORT = ROOT / "report"
    REPORT_FIGURES = REPORT / "figures"
    REPORT_TABLES = REPORT / "tables"
    REPORT_DRAFTS = REPORT / "drafts"
    PRESENTATION = ROOT / "presentation"

    @classmethod
    def ensure_directories(cls):
        """Ensure that all critical processed/staging/academic directories exist."""
        for path in [
            cls.TERRAIN_STAGING, 
            cls.TERRAIN_PROCESSED, 
            cls.OUTPUTS,
            cls.REPORT_FIGURES,
            cls.REPORT_TABLES,
            cls.REPORT_DRAFTS,
            cls.PRESENTATION
        ]:
            path.mkdir(parents=True, exist_ok=True)

# Global project paths instance
paths = ProjectPaths
