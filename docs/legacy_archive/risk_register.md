# Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| CRS mismatch between GIS layers and DTM | High | Medium | Inspect all layers before load; document target CRS |
| `voie` is not the correct main alignment layer | High | Low-Medium | Inspect attributes and geometry carefully before loading |
| Some source layers have invalid geometry | Medium | Medium | Run geometry validation and clean before load |
| DTM extent does not fully cover all segments | High | Medium | Check overlap early; clip or find missing terrain data |
| Asset semantic meaning is unclear (`base`, `reseau_tiers`) | Medium | Medium | Inspect attributes and postpone uncertain mapping |
| 3D layers add too much complexity too early | Medium | High | Keep 3D for later phase |
| LiDAR introduces unnecessary complexity | Medium | High | Use DTM only for MVP |
| Rainfall data not available yet | Low | High | Keep schema ready; postpone ingestion |
| BIM / IFC not available yet | Low | High | Keep schema ready; postpone ingestion |
| Scope creep into advanced modelling | High | High | Focus on 2D GIS + DTM + PostGIS MVP |
| Supabase ingestion issues from large files | Medium | Medium | Use Python ETL and staged processing |
