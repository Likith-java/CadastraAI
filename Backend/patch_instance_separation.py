import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\frame_field_polygonize.py")
text = path.read_text(encoding="utf-8")

# 1. Add the watershed_instances import if not already present
if "from vectorization import watershed_instances" not in text:
    text = text.replace(
        "from rasterio.transform import Affine",
        "from rasterio.transform import Affine\nfrom vectorization import watershed_instances\nfrom skimage import measure as _measure_mod",
        1,
    )

# 2. Load edge_prob from the npz (currently only mask + frame_field are loaded)
old_load = '    data = np.load(npz_path)\n    mask_prob, frame_field = data["mask"], data["frame_field"]'
new_load = '    data = np.load(npz_path)\n    mask_prob, frame_field = data["mask"], data["frame_field"]\n    edge_prob = data["edge"]'
count = text.count(old_load)
if count != 1:
    print(f"[FAIL] load block: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_load, new_load)

# 3. Replace the naive whole-mask contour tracing with per-instance labeling first
old_block = """    theta_map = decode_frame_field(frame_field)
    binary_mask = (mask_prob > MASK_THRESH).astype(np.uint8)
    contours = measure.find_contours(binary_mask, level=0.5)

    detected_polys, geo_polys = [], []
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
        detected_polys.append({"instance_id": i, "feature_id": i, "geometry": reg_poly, "confidence": confidence})
        geo_coords = [transform * (x, y) for x, y in reg_poly.exterior.coords]
        geo_polys.append({"instance_id": i, "feature_id": i, "geometry": Polygon(geo_coords), "confidence": confidence})"""

new_block = """    theta_map = decode_frame_field(frame_field)

    # Separate touching buildings FIRST (same approach as the watershed path),
    # then regularize each instance's own contour with the frame field.
    labels = watershed_instances(mask_prob, edge_prob)
    instance_ids = [int(v) for v in np.unique(labels) if v != 0]

    detected_polys, geo_polys = [], []
    for i in instance_ids:
        inst_mask = (labels == i).astype(np.uint8)
        inst_contours = _measure_mod.find_contours(inst_mask, level=0.5)
        if not inst_contours:
            continue
        # a label can occasionally produce more than one contour ring; keep the largest
        contour = max(inst_contours, key=lambda c: Polygon([(x, y) for y, x in c]).area if len(c) >= 3 else 0)
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
        detected_polys.append({"instance_id": i, "feature_id": i, "geometry": reg_poly, "confidence": confidence})
        geo_coords = [transform * (x, y) for x, y in reg_poly.exterior.coords]
        geo_polys.append({"instance_id": i, "feature_id": i, "geometry": Polygon(geo_coords), "confidence": confidence})"""

count = text.count(old_block)
if count != 1:
    print(f"[FAIL] main block: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_block, new_block)

path.write_text(text, encoding="utf-8")
print("frame_field_polygonize.py patched successfully.")
