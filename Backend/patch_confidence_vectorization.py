import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\vectorization.py")
text = path.read_text(encoding="utf-8")

old_func = """def labels_to_polygons(labels: np.ndarray, transform: Affine):
    polygons = []
    for geom, value in rio_shapes(labels.astype("int32"), mask=labels > 0, transform=transform):
        if value == 0:
            continue
        poly = shape(geom)
        if poly.is_empty:
            continue
        polygons.append({"instance_id": int(value), "geometry": poly})
    return polygons"""

new_func = """def labels_to_polygons(labels: np.ndarray, transform: Affine, mask_prob: np.ndarray = None):
    polygons = []
    conf_by_id = {}
    if mask_prob is not None:
        ids = np.unique(labels)
        ids = ids[ids != 0]
        if len(ids) > 0:
            means = ndi.mean(mask_prob, labels=labels, index=ids)
            conf_by_id = {int(i): float(m) for i, m in zip(ids, np.atleast_1d(means))}
    for geom, value in rio_shapes(labels.astype("int32"), mask=labels > 0, transform=transform):
        if value == 0:
            continue
        poly = shape(geom)
        if poly.is_empty:
            continue
        polygons.append({
            "instance_id": int(value),
            "geometry": poly,
            "confidence": round(conf_by_id.get(int(value), 0.0), 4),
        })
    return polygons"""

count = text.count(old_func)
if count != 1:
    print(f"[FAIL] labels_to_polygons: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_func, new_func)

old_call_1 = "detected_polys = labels_to_polygons(labels, Affine.identity())"
new_call_1 = "detected_polys = labels_to_polygons(labels, Affine.identity(), mask_prob)"
if text.count(old_call_1) != 1:
    print("[FAIL] call 1 not found")
    sys.exit(1)
text = text.replace(old_call_1, new_call_1)

old_call_2 = "geo_polys = labels_to_polygons(labels, transform)"
new_call_2 = "geo_polys = labels_to_polygons(labels, transform, mask_prob)"
if text.count(old_call_2) != 1:
    print("[FAIL] call 2 not found")
    sys.exit(1)
text = text.replace(old_call_2, new_call_2)

path.write_text(text, encoding="utf-8")
print("vectorization.py patched successfully.")
