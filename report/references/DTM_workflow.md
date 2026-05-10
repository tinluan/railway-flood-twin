# DTM Workflow — Railway Flood-Risk Digital Twin MVP

## Purpose
This document defines the practical workflow for using the **DTM raster** in the current student-project MVP.

At the current project stage, the DTM is **not** loaded into the database yet. Instead, it is used **externally in Python** to derive terrain information that can later enrich the railway GIS layers stored in PostGIS.

---

## Current project context

### Current available terrain source
- Main DTM source file:
  - `data/raw/dtm/PK520_PK535_NO_HOLES.asc`

### Current database status
The current database implementation already contains:
- `core.dataset`
- `rail.corridor`
- `rail.gis_asset`

The first cleaned GIS layers have already been loaded into:

```sql
rail.gis_asset
```

with the following asset types already present:
- `track_area`
- `culvert`
- `bridge`
- `drainage_asset`

### Important implementation note
At this stage, the current `voie` layer is polygon-based (`track_area`) rather than line-based. Therefore, the first DTM workflow must work with the currently available GIS representation.

---

## Why the DTM matters

The DTM provides the terrain surface needed to:
- understand relative elevation of railway assets
- identify low-lying areas
- compare different rail-related assets against the surrounding ground
- support future flood-risk interpretation
- prepare the project for later segment-based terrain or risk analysis

---

## Recommended DTM strategy for the current phase

### Do **not** load the raster into Supabase yet
For the current MVP, the safest and simplest workflow is:

1. keep the original DTM in `data/raw/dtm/`
2. inspect it in QGIS and Python
3. use Python to derive terrain summaries externally
4. store the derived summary values later in database tables or exported summary files

### Why this is recommended
This approach is:
- easier for a student project
- easier to debug
- lighter than trying to manage raster storage in the database immediately
- sufficient for the first implementation phase

---

## Current DTM workflow phases

### Phase 1 — Inspect the DTM
Goal:
- confirm CRS
- confirm extent
- confirm resolution
- confirm nodata handling

### Phase 2 — Relate the DTM to current GIS assets
Goal:
- confirm the GIS assets spatially overlap the DTM
- confirm they are in the same CRS

### Phase 3 — Derive terrain summaries
Goal:
- extract elevation information for current GIS assets
- create summary outputs for later use in the database and documentation

### Phase 4 — Store or export results
Goal:
- write terrain summaries into CSV / GeoPackage / database tables
- document the results and prepare for later risk interpretation

---

## DTM workflow details

---

## Step 1 — Inspect the raster

### Input
```text
data/raw/dtm/PK520_PK535_NO_HOLES.asc
```

### Tasks
- open the DTM in QGIS
- verify CRS
- verify extent
- verify pixel size / raster resolution
- verify nodata value
- confirm the DTM visually overlaps the railway data

### Expected current CRS
The current project inspections indicate the DTM is in:

```text
RGF_1993_Lambert_93 / EPSG:2154
```

### Output
- confirmed terrain metadata for the project documents
- confidence that GIS and terrain data are spatially aligned

---

## Step 2 — Prepare the GIS target layer for terrain analysis

### Current target layer choice
At the current phase, the available GIS target in the database is:

```sql
rail.gis_asset
```

with polygon features such as:
- `track_area`
- `culvert`
- `bridge`
- `drainage_asset`

### Current practical recommendation
For the first terrain workflow, use one of these strategies:

#### Option A — Start with `track_area` polygons only
This is the simplest first terrain analysis step.

#### Option B — Compute terrain summaries for all GIS asset polygons
This is more complete but also slightly more work.

### Recommended choice
Start with:

```text
asset_type = 'track_area'
```

Then extend to `culvert`, `bridge`, and `drainage_asset` later.

---

## Step 3 — Choose the first terrain metrics

### Recommended first metrics
For the current polygon-based GIS assets, calculate:
- minimum elevation
- maximum elevation
- mean elevation

### Why these metrics first?
These are simple, interpretable, and useful for later flood-risk logic.

### Possible later metrics
Later, you may also calculate:
- elevation range
- local slope
- relative elevation versus nearby assets
- distance to low-lying terrain clusters

---

## Step 4 — Decide where to store the terrain summary results

### Recommended current storage options
For the current project stage, use one of these:

#### Option A — CSV output
Save a summary table such as:

```text
data/processed/terrain/gis_asset_elevation_summary.csv
```

#### Option B — GeoPackage output
Save enriched features such as:

```text
data/processed/terrain/gis_asset_with_elevation.gpkg
```

#### Option C — Later store results in the database
Once you decide the final database structure for terrain-enriched assets, add the derived attributes to a database table.

### Recommended current choice
Start with **CSV** or **GeoPackage** output first.

This is easier to inspect and validate before changing the database schema again.

---

## Step 5 — Two implementation versions: fast vs accurate

For the current polygon-based GIS assets, there are **two good ways** to derive terrain summaries from the DTM.

### Version 1 — Fast version (recommended first)
Use a **simple and lightweight zonal-statistics workflow** or a simplified polygon-based raster summary.

#### Main idea
For each target polygon (for example `track_area`):
- intersect the polygon footprint with the raster
- summarize the raster cells inside the polygon
- calculate:
  - minimum elevation
  - maximum elevation
  - mean elevation

#### Typical outputs
- one row per polygon
- CSV or GeoPackage output

#### Why it is called “fast”
Because it is:
- simpler to implement
- faster to run
- easier to debug
- sufficient for the first student-project MVP

#### Best current target
```text
track_area polygons
```

#### Recommended use case
Use this version when you want:
- a first working terrain summary quickly
- something easy to explain in the report
- a reliable first result without overengineering

---

### Version 2 — More accurate version
Use a **more careful polygon-based terrain workflow** that gives more spatially trustworthy results and can be extended later.

#### Main idea
For each target geometry:
- confirm exact CRS match
- clip or mask the raster to the polygon footprint if needed
- use proper raster-cell inclusion logic
- optionally handle nodata cells more carefully
- optionally compute additional statistics beyond min / max / mean
- optionally create intermediate clipped rasters for visual validation

#### Possible accurate workflow variants
1. **Whole-geometry clipping / masking**
   - crop the raster to the full `voie` polygon footprint
   - keep only the raster values inside the polygon
   - use the clipped raster for validation or later statistics

2. **Polygon zonal statistics with better control**
   - calculate min / max / mean using the raster cells inside each polygon
   - handle nodata and edge cells carefully
   - optionally compare different inclusion methods if needed

#### Why it is called “more accurate”
Because it is better for:
- handling exact spatial overlap
- controlling nodata behavior
- validating the raster inside the geometry visually
- supporting later research-quality analysis

#### Recommended use case
Use this version when you want:
- more confidence in the terrain summaries
- more detailed QA / validation
- a better foundation for later flood-risk modelling

---

## Comparison — Fast vs Accurate version

### Fast version
**Advantages**
- quicker to implement
- easier for a beginner
- easier to debug
- good for first MVP results
- produces directly usable summary values

**Limitations**
- less explicit control over raster masking details
- less suitable for detailed QA or publication-grade analysis
- may hide edge-cell and nodata issues if used too simplistically

### Accurate version
**Advantages**
- more rigorous spatial handling
- better for checking exactly what part of the raster is used
- easier to validate visually with clipped rasters
- better long-term basis for advanced modelling

**Limitations**
- slower to implement
- more processing steps
- more complexity for a first student MVP

---

## Recommended decision for the current phase

### Practical recommendation
Use the **fast version first** to get the first usable terrain summary for:

```text
asset_type = 'track_area'
```

Then, if the results look important enough or you need stronger validation, repeat selected areas using the **more accurate version**.

### Why this recommendation fits the project
At the current project stage:
- the database is already working for GIS assets
- the DTM is available and aligned
- the project still needs a simple, working terrain workflow before adding more complexity

So the best sequence is:
1. fast version first
2. accurate version second if needed

---

## Recommended current implementation workflow in Python

### Inputs
- DTM raster:
  - `data/raw/dtm/PK520_PK535_NO_HOLES.asc`
- GIS features:
  - current cleaned GIS layers in `data/staging/gis/`
  - or data already loaded in `rail.gis_asset`

### Recommended Python libraries
- `rasterio`
- `geopandas`
- `pandas`
- `shapely`

### Recommended first workflow
1. read the raster
2. read the target GIS asset layer
3. ensure CRS consistency
4. apply the **fast terrain summary version** first
5. calculate min / max / mean elevation
6. export the results to `data/processed/terrain/`
7. validate the outputs
8. if needed, rerun selected polygons using the **more accurate version**

---

## Two practical terrain-analysis approaches

### Approach 1 — Polygon zonal summary (recommended first)
Use the current polygon assets directly.

#### Best first target
```text
track_area polygons
```

#### What to calculate
For each polygon:
- min elevation
- max elevation
- mean elevation

#### Advantages
- works directly with the current available GIS data
- no need to derive centerlines yet
- easy to explain in the report
- aligns well with the **fast version**

#### Limitation
This gives area-based summaries, not linear railway segment summaries.

---

### Approach 2 — Whole-geometry clipping / masking
Use the full polygon geometry to crop the raster before or during more careful analysis.

#### What it does
- crops the DTM using the `voie` polygon footprint
- keeps only raster cells inside that polygon
- produces a clipped raster or masked raster result

#### Best use
- visual verification
- accurate validation workflow
- selected detailed studies
- supports the **more accurate version**

#### Limitation
This often produces a raster subset rather than a direct final summary table, so it is usually a support step rather than the main final output.

---

### Approach 3 — Later line/segment sampling
Once a real rail centerline or derived line exists, sample the terrain along the line.

#### What to calculate later
- min elevation along segment
- max elevation along segment
- mean elevation along segment

#### Why later
This is the better long-term railway representation, but it depends on having a line-based track layer.

---

## Recommended current decision

### Current best practice for this project
Use:
- **Polygon zonal summary as the fast first version**
- **Whole-geometry clipping / masking as the accurate validation version when needed**

This gives both:
- a quick MVP result
- a more rigorous path for selected follow-up analysis

---

## Suggested output file structure

### Raw terrain source
```text
data/raw/dtm/
```

### Temporary terrain work
```text
data/staging/terrain/
```

Possible files:
- clipped raster
- temporary sample points
- temporary zonal summary tables
- validation raster subsets

### Final processed terrain outputs
```text
data/processed/terrain/
```

Suggested files:
- `gis_asset_elevation_summary.csv`
- `track_area_elevation_summary.csv`
- `gis_asset_with_elevation.gpkg`
- `voie_dtm_clip.tif` *(if clipping is used for validation)*

---

## Suggested documentation updates after DTM processing

After completing the first DTM workflow, update:

### `docs/data_inventory.md`
Add:
- processed terrain summary outputs
- optional clipped raster outputs if created

### `docs/implementation_notes.md`
Add:
- whether the fast or accurate version was used
- what terrain metrics were calculated
- which GIS layers were used
- any overlap or nodata issues

### `docs/task_tracker.md`
Mark as done when completed:
- DTM inspected
- first terrain summary workflow executed
- terrain summary output saved
- optional clipped raster validation completed

### `docs/changelog.md`
Add a new version line for terrain workflow completion

---

## Recommended validation checks for the DTM workflow

After generating the first terrain summaries, validate:

### Check 1 — Asset count consistency
The number of terrain summary rows should match the number of GIS target features processed.

### Check 2 — CRS consistency
The processed target layer and DTM must be in the same CRS.

### Check 3 — Missing values
Check how many assets received no terrain values because of nodata or lack of overlap.

### Check 4 — Reasonableness
Review min / max / mean values for obvious errors such as:
- impossible elevations
- all values equal when they should vary
- large unexpected gaps

### Check 5 — Visual verification for accurate version
If clipping/masking is used, visually inspect the clipped raster to confirm the polygon footprint and raster alignment are correct.

---

## Recommended next implementation order

### Current next steps after this workflow document
1. create a Python script for the **fast DTM summary version** on `track_area`
2. create the first terrain summary output
3. validate the values
4. if needed, create a second script for **accurate clipping / masking** on selected polygons
5. decide whether to store summary values in CSV first or directly in the database later

---

## Future extension of the DTM workflow

Later, once the project grows, this workflow can be extended to:
- rail centerline / segment elevation profiles
- slope analysis
- flood-exposure metrics based on terrain
- linkage with rainfall and hazard logic
- support for BIM asset elevation comparison

---

## Summary

The recommended DTM workflow for the current project phase is:

1. keep the DTM external
2. inspect and confirm its metadata
3. use Python to derive terrain summaries for the current GIS assets
4. start with the **fast version** on `track_area` polygons
5. use the **accurate version** later for validation or more rigorous analysis
6. export results to `data/processed/terrain/`
7. document and validate the results before changing the database again

This gives the project both:
- a practical MVP path
- and a more accurate analysis path when needed.
