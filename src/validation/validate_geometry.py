"""
src/validation/validate_geometry.py — GIS Geometry Validation
=============================================================
Checks for invalid geometries (self-intersections, nulls, slivers) in 
the staging GIS files.

Architecture Position (Layer 1 -> 2 / QA):
    - Cleans up artifacts from QGIS or Civil3D exports before ingestion.
    - Prevents topology errors during HEC-RAS mesh generation.

Example Usage:
    python src/validation/validate_geometry.py
"""
