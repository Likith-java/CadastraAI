import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\frame_field_polygonize.py")
text = path.read_text(encoding="utf-8")

# Add rasterize import if missing
if "from rasterio.features import rasterize" not in text:
    text = text.replace(
        "from rasterio.transform import Affine",
        "from rasterio.transform import Affine\nfrom rasterio.features import rasterize",
        1,
    )

old_loop = """    detected_polys, geo_polys = [], []
    for i, contour in enumerate(contours):
        reg_poly = regularize_contour(contour, theta_map)
        if reg_poly is None:
            continue
        detected_polys.append({"instance_id": i, "geometry": reg_poly})
        geo_coords = [transform * (x, y) for x, y in reg_poly.exterior.coords]
        geo_polys.append({"instance_id": i, "geometry": Polygon(geo_coords)})"""

new_loop = """    detected_polys, geo_polys = [], []
    for i, contour in enumerate(contours):
        reg_poly = regularize_contour(contour, theta_map)
        if reg_poly is None:
            continue
        poly_mask = rasterize(
            [(reg_poly, 1)],
            out_shape=mask_prob.shape,
            fill=0,
            dtype="uint8",
        ).astype(bool)
        if poly_mask.any():
            confidence = round(float(mask_prob[poly_mask].mean()), 4)
        else:
            confidence = 0.0
        detected_polys.append({"instance_id": i, "geometry": reg_poly, "confidence": confidence})
        geo_coords = [transform * (x, y) for x, y in reg_poly.exterior.coords]
        geo_polys.append({"instance_id": i, "geometry": Polygon(geo_coords), "confidence": confidence})"""

count = text.count(old_loop)
if count != 1:
    print(f"[FAIL] loop: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_loop, new_loop)

path.write_text(text, encoding="utf-8")
print("frame_field_polygonize.py patched successfully.")
