"""
src/validation/validate_database.py — Database Schema Validation
================================================================
Verifies that the required tables (`rail.gis_asset`) and constraints 
exist in the connected PostGIS database.

Architecture Position (Layer 2 / QA):
    - Run after `load_gis_assets_dotenv.py` to ensure the Mirror Database
      is correctly initialized.

Example Usage:
    python src/validation/validate_database.py
"""
