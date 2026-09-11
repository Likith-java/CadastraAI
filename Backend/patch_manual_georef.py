import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\main.py")
text = path.read_text(encoding="utf-8")

old_sig = '''@app.post("/aoi/upload")
async def upload_aoi(file: UploadFile = File(...)):'''

new_sig = '''@app.post("/aoi/upload")
async def upload_aoi(
    file: UploadFile = File(...),
    north: float | None = None,
    south: float | None = None,
    east: float | None = None,
    west: float | None = None,
):'''

count = text.count(old_sig)
if count != 1:
    print(f"[FAIL] signature: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_sig, new_sig)

old_body = '''    with rasterio.open(raster_path) as src:
        transform_affine = src.transform
        width, height = src.width, src.height
        crs = src.crs.to_string() if src.crs else None

        left = transform_affine.c
        top = transform_affine.f
        resolution = transform_affine.a
'''

new_body = '''    with rasterio.open(raster_path) as src:
        transform_affine = src.transform
        width, height = src.width, src.height
        crs = src.crs.to_string() if src.crs else None

        left = transform_affine.c
        top = transform_affine.f
        resolution_x = transform_affine.a
        resolution_y = -transform_affine.e

        manual_bounds_used = False
        if crs is None and None not in (north, south, east, west):
            crs = "EPSG:4326"
            left = west
            top = north
            resolution_x = (east - west) / width
            resolution_y = (north - south) / height
            manual_bounds_used = True
'''

count = text.count(old_body)
if count != 1:
    print(f"[FAIL] body: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_body, new_body)

old_transform_dict = '''    transform = {
        "left": left,
        "top": top,
        "resolution": resolution,
        "width": width,
        "height": height,
    }'''

new_transform_dict = '''    transform = {
        "left": left,
        "top": top,
        "resolution_x": resolution_x,
        "resolution_y": resolution_y,
        "width": width,
        "height": height,
    }'''

count = text.count(old_transform_dict)
if count != 1:
    print(f"[FAIL] transform dict: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_transform_dict, new_transform_dict)

old_meta = '''    meta = {
        "aoi_id": aoi_id,
        "original_filename": file.filename,
        "crs": crs,
        "transform": transform,
    }'''

new_meta = '''    meta = {
        "aoi_id": aoi_id,
        "original_filename": file.filename,
        "crs": crs,
        "transform": transform,
        "manual_bounds_used": manual_bounds_used,
    }'''

count = text.count(old_meta)
if count != 1:
    print(f"[FAIL] meta dict: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_meta, new_meta)

path.write_text(text, encoding="utf-8")
print("main.py patched successfully.")
