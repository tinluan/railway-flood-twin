# Project Overview

## Project title
Railway Flood-Risk Digital Twin MVP

## Problem statement
Railway infrastructure is vulnerable to flooding, especially in areas where terrain, drainage conditions, and heavy rainfall combine to create exposure for tracks and rail assets.

## Project goal
Develop a student-level digital twin MVP that integrates:
- railway GIS data
- terrain / DTM data
- later rainfall data
- later BIM-derived asset information

The system should support basic flood-risk analysis for a selected railway corridor.

## Main objectives
1. Organize and document the available source data.
2. Build a PostgreSQL + PostGIS database on Supabase.
3. Load the current Rail GIS layers into the database.
4. Use the DTM to enrich rail segments with elevation information.
5. Prepare the project for later integration of rainfall and BIM data.

## Current in-scope datasets
- `maquette_2d` vector layers
- `maquette_3d` vector layers *(kept mainly for later use)*
- DTM raster (`.asc`)

## Current out of scope for first implementation
- full LiDAR processing
- complex hydrodynamic modelling
- advanced machine learning
- live IoT integration

## Target platform
- Database: Supabase PostgreSQL + PostGIS
- ETL / transformation: Python
- GIS inspection: QGIS
- Documentation: Markdown

## Deliverables
- organized project folder structure
- documented source data inventory
- database schema and SQL scripts
- populated Rail GIS tables
- elevation-enriched track segments
- project documentation pack

## Success criteria for MVP
- `rail.track_segment` created and populated from `voie`
- `rail.gis_asset` created and populated from selected 2D layers
- CRS validated and standardized
- DTM processed to derive segment elevation summaries
- at least a few working spatial SQL queries demonstrated
