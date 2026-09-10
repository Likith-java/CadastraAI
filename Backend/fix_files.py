import re, pathlib

def patch_vector_file(path):
    p = pathlib.Path(path)
    content = p.read_text(encoding="utf-8")
    orig = content

    anchor = "gdf_geo_3857 = gdf_geo\n\n    return {"
    if anchor not in content:
        print(f"[SKIP] anchor not found in {path} -- no changes made, check manually")
        return
    replacement = (
        "gdf_geo_3857 = gdf_geo\n\n"
        "    from vector_postprocess import clean_for_frontend\n"
        "    gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_geo_3857.empty else gdf_geo_3857\n\n"
        "    return {"
    )
    content = content.replace(anchor, replacement, 1)
    content = content.replace(
        '"quality": json.loads(gdf_geo_3857.to_json())',
        '"quality": json.loads(gdf_clean.to_json())',
        1,
    )
    content = content.replace("if not gdf_geo_3857.empty else", "if not gdf_clean.empty else", 1)
    content = content.replace("len(gdf_geo_3857)", "len(gdf_clean)", 1)

    if content == orig:
        print(f"[WARN] {path}: no substitutions applied")
    else:
        p.write_text(content, encoding="utf-8")
        print(f"[OK] patched {path}")

patch_vector_file("frame_field_polygonize.py")
patch_vector_file("vectorization.py")

# --- remove the duplicated endpoint block in main.py ---
main_path = pathlib.Path("main.py")
content = main_path.read_text(encoding="utf-8")

pattern = re.compile(
    r'(from frame_field_polygonize import vectorize_frame_field\n'
    r'\n'
    r'@app\.post\("/aoi/\{aoi_id\}/vectorize/frame_field"\)\n'
    r'def vectorize_aoi_frame_field\(aoi_id: str\):\n'
    r'(?:.*\n)*?'
    r'    return result\n)'
    r'\n'
    r'\1'
)

new_content, n = pattern.subn(r'\1', content)
if n:
    main_path.write_text(new_content, encoding="utf-8")
    print(f"[OK] removed {n} duplicate block(s) from main.py")
else:
    print("[WARN] duplicate block pattern not found in main.py -- check manually, no changes made")
