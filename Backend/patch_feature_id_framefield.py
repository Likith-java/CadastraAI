import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\frame_field_polygonize.py")
text = path.read_text(encoding="utf-8")

old_1 = """        detected_polys.append({"instance_id": i, "geometry": reg_poly, "confidence": confidence})"""
new_1 = """        detected_polys.append({"instance_id": i, "feature_id": i, "geometry": reg_poly, "confidence": confidence})"""

old_2 = """        geo_polys.append({"instance_id": i, "geometry": Polygon(geo_coords), "confidence": confidence})"""
new_2 = """        geo_polys.append({"instance_id": i, "feature_id": i, "geometry": Polygon(geo_coords), "confidence": confidence})"""

for old, new, label in [(old_1, new_1, "detected_polys"), (old_2, new_2, "geo_polys")]:
    count = text.count(old)
    if count != 1:
        print(f"[FAIL] {label}: expected 1 match, found {count}")
        sys.exit(1)
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print("frame_field_polygonize.py patched successfully.")
