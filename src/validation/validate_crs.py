"""
src/validation/validate_crs.py — Coordinate Reference System Validation
=======================================================================
Checks that all spatial data (GeoPackages and GeoTIFFs) in the staging directory 
are correctly projected in EPSG:2154 (RGF93 v1 / Lambert-93). 

Architecture Position (Layer 1 -> 2 / QA):
    - Ensures spatial consistency before any HEC-RAS or clipping operations occur.
    - Fails fast if data is in EPSG:4326 (WGS84) or other CRS.

Example Usage:
    python src/validation/validate_crs.py
"""
