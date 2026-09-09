# CADASTRA AI frontend demo — actual data

This frontend uses the supplied CADASTRA AI GIS assets directly. No synthetic parcel geometry is included.

## Supplied assets
- `btm_layout_0015_georeferenced.tif` — original georeferenced raster, EPSG:3857, 512x512, 4 bands.
- `btm_layout_0015_preview.jpeg` — browser display preview generated from the supplied TIFF. The TIFF itself is retained unchanged in `public/data/`.
- `btm_layout_0015_polygons.geojson` — supplied source polygons.
- `cadastraai_gis_quality_controlled.geojson` — supplied QC GIS output. Dashboard/review/analytics read its attributes.
- `cadastraai_detected_regions.geojson` — supplied AI segmentation regions in 512x512 pixel space.
- `cadastraai_gis_frontend_handoff.txt` — supplied handoff notes.

## Coordinate handling
The supplied QC/source polygons are in EPSG:3857 coordinates. The frontend converts those coordinates to the 512x512 local image coordinate system using the exact transform from the supplied georeferenced TIFF, then displays them with Leaflet `CRS.Simple` over the raster preview. The AI detected-region file remains in its documented pixel coordinate space.

## Model note
No model binary (`.onnx`, `.pt`, `.pth`, etc.) was present among the supplied conversation files, so this build does not pretend to run browser inference. It displays the actual AI segmentation output that was supplied. When the model file is supplied in a browser-compatible format, inference can be added without replacing the GIS viewer.
