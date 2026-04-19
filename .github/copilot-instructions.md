# Copilot Instructions: Railway Flood-Risk Digital Twin

## Context
This is a Master's capstone project building a railway flood-risk digital twin.
Team: Tin (Lead/DBA), Szilvi (GIS), Amal (Backend).

## Critical Rules
- NEVER use hardcoded absolute paths (e.g., `C:\Users\...`).
- ALWAYS use `from src.utils.paths import paths` for file resolution.
- ALL database connections must use `os.getenv("DATABASE_URL")` from `.env`.
- Use `pathlib.Path` everywhere, never `os.path.join` strings.

## Python Style
- Follow PEP 8.
- Add docstrings to all functions using Google style.
- Use `sys.exit(1)` for fatal errors, not bare `raise`.
- Wrap scripts in `if __name__ == "__main__": main()`.

## Project Structure
- `src/utils/paths.py` — all path constants
- `src/utils/check_health.py` — environment validation
- `src/utils/viz.py` — academic figure style
- `data/staging/gis/` — cleaned GIS layers (.gpkg)
- `data/raw/dtm/` — raw DTM rasters (.asc)
- `data/staging/terrain/` — working DTM GeoTIFFs (.tif)
- `report/figures/` — output figures for academic report

## CRS Standard
- All GIS data must be in EPSG:2154 (Lambert-93).
- Always check and align CRS before raster masking operations.
