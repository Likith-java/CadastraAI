import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\vectorization.py")
text = path.read_text(encoding="utf-8")

old = """        polygons.append({
            "instance_id": int(value),
            "geometry": poly,
            "confidence": round(conf_by_id.get(int(value), 0.0), 4),
        })"""

new = """        polygons.append({
            "instance_id": int(value),
            "feature_id": int(value),
            "geometry": poly,
            "confidence": round(conf_by_id.get(int(value), 0.0), 4),
        })"""

count = text.count(old)
if count != 1:
    print(f"[FAIL] expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("vectorization.py patched successfully.")
