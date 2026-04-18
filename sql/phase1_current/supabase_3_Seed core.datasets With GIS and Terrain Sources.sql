insert into core.dataset (
    dataset_name,
    dataset_type,
    source_uri,
    source_format,
    source_crs,
    target_srid,
    notes
)
values
('voie_fixed', 'rail_gis', 'data/staging/gis/voie_fixed.gpkg', 'gpkg', 'EPSG:2154', 2154, 'Track area polygon'),
('Buse_fixed', 'rail_gis', 'data/staging/gis/Buse_fixed.gpkg', 'gpkg', 'EPSG:2154', 2154, 'Culvert-related layer'),
('Pont Rail_fixed', 'rail_gis', 'data/staging/gis/Pont Rail_fixed.gpkg', 'gpkg', 'EPSG:2154', 2154, 'Bridge layer'),
('Descente d''eau_fixed', 'rail_gis', 'data/staging/gis/Descente d''eau_fixed.gpkg', 'gpkg', 'EPSG:2154', 2154, 'Drainage asset layer'),
('DTM PK520_PK535_NO_HOLES', 'terrain', 'data/raw/dtm/PK520_PK535_NO_HOLES.asc', 'asc', 'EPSG:2154', 2154, 'Terrain raster used later for elevation summaries');
