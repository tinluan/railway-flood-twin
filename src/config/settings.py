"""src/config/settings.py — Application Configuration
==================================================
Centralized configuration file that loads environment variables and 
defines global constants for the FastAPI application and backend scripts.

Architecture Position (Utilities):
    - Acts as a single source of truth for config variables, preventing
      scattered `os.getenv` calls.
    - Works in tandem with `src/utils/paths.py`.

Example Usage:
    from src.config.settings import APP_NAME, DEBUG_MODE
"""
