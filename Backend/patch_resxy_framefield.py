import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\frame_field_polygonize.py")
text = path.read_text(encoding="utf-8")

old = '''    tf = meta["transform"]
    transform = Affine(tf["resolution"], 0, tf["left"], 0, -tf["resolution"], tf["top"])
    crs = meta.get("crs") or "EPSG:4326"'''

new = '''    tf = meta["transform"]
    res_x = tf.get("resolution_x", tf.get("resolution"))
    res_y = tf.get("resolution_y", tf.get("resolution"))
    transform = Affine(res_x, 0, tf["left"], 0, -res_y, tf["top"])
    crs = meta.get("crs") or "EPSG:4326"'''

count = text.count(old)
if count != 1:
    print(f"[FAIL] expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("frame_field_polygonize.py patched successfully.")
