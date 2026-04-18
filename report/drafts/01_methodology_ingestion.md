# Methodology Section 01: Data Foundation & Ingestion

*Drafted by Antigravity (AI) on 2026-04-18*

## 3.1 Digital Twin Architecture
The technical foundation of this case study is built upon a hybrid architecture designed for cross-border collaboration. Recognizing the limitations of cloud-synced storage for large geospatial datasets (specifically the 1GB Digital Terrain Model), the project utilizes a split-storage model:

1.  **Logical Layer (Code and Documentation)**: Hosted on a central GitHub repository, ensuring version control and traceability for all analytical scripts.
2.  **Physical Layer (Geospatial Data)**: Large-scale rasters and vector files are maintained on a Shared Google Drive, linked to the logical layer through a dynamic environment configuration (`.env`).

## 3.2 Data Ingestion & Cleaning
The primary inputs for the digital twin include four key railway asset categories and a High-Resolution Digital Terrain Model (DTM).

### 3.2.1 Asset Categories
The case study focuses on 30 specific assets within the study corridor:
- **Culverts (n=14)**: Critical for transverse drainage.
- **Bridges (n=8)**: Major structures requiring elevation delta analysis.
- **Drainage Assets (n=6)**: Surface water management components.
- **Track Areas (n=2)**: Large-scale polygons defining the railway platform.

### 3.2.2 Coordinate Reference System (CRS) Optimization
To ensure spatial alignment between the DTM (raster) and the railway assets (vector), the project standardized all data into the **RGF93 / Lambert-93 (EPSG:2154)** projection. This coordinate system was chosen for its accuracy within the French metropolitan context.

## 3.3 Provenance and Reproducibility
Every analysis performed in this study is logged with its specific source dataset (Table [X]). This ensures that results can be audited and reproduced by any team member regardless of their physical location or hardware configuration.
