# ATOMIC TASK QUEUE

| Task ID | Node | Description | Verification Criterion | Status |
|---|---|---|---|---|
| TASK-01 | NODE_01_ENV_SETUP | Verify Python virtualenv, install geopandas, shapely, pmtiles; ensure tippecanoe is runnable | `tippecanoe --version` returns 0, python imports succeed | DONE |
| TASK-02 | NODE_02_DATA_INGESTION | Download Milan building footprints and construction epoch datasets (DBT / CENED / ISTAT census) | Valid non-empty files in `data/raw/` | DONE |
| TASK-03 | NODE_03_SPATIAL_ETL | Spatial join & attribute enrichment (height, construction year) | Valid GeoJSON in `data/processed/` with geometry, height, year | DONE |
| TASK-04 | NODE_04_TILE_GENERATION | Vector tiling into PMTiles using Tippecanoe | `data/tiles/milano_buildings.pmtiles` exists and valid | DONE |
| TASK-05 | NODE_05_FRONTEND_3D | Implement MapLibre GL 3D frontend with time-scrubber slider | `web/index.html`, `app.js`, `style.css` implemented | DONE |
| TASK-06 | NODE_06_VERIFICATION_E2E | End-to-end verification and local test server audit | `pipeline/verify_all.py` passes with exit code 0 | DONE |
