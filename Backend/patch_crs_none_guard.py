import pathlib, sys

files = [
    r"C:\Users\navaneeth\CadastraAI\Backend\vectorization.py",
    r"C:\Users\navaneeth\CadastraAI\Backend\frame_field_polygonize.py",
]

old = 'crs = meta.get("crs", "EPSG:4326")'
new = 'crs = meta.get("crs") or "EPSG:4326"'

for f in files:
    path = pathlib.Path(f)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        print(f"[SKIP] {path.name}: pattern not found")
        continue
    if count > 1:
        print(f"[WARN] {path.name}: found {count} matches, replacing all")
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"[OK] {path.name} patched ({count} replacement(s))")
