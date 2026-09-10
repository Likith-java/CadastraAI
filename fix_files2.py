import re, sys, pathlib, py_compile

def patch(path, old, new, label):
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        print(f"[FAIL] {label}: expected 1 occurrence of target string in {path}, found {count}. ABORTING — no changes written.")
        sys.exit(1)
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[OK] {label}: patched {path}")

# --- Fix 1: UnboundLocalError in frame_field_polygonize.py ---
patch(
    "Backend/frame_field_polygonize.py",
    'gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_clean.empty else gdf_geo_3857',
    'gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_geo_3857.empty else gdf_geo_3857',
    "frame_field_polygonize.py gdf_clean self-reference bug"
)

# --- Fix 2: same bug in vectorization.py ---
patch(
    "Backend/vectorization.py",
    'gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_clean.empty else gdf_geo_3857',
    'gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_geo_3857.empty else gdf_geo_3857',
    "vectorization.py gdf_clean self-reference bug"
)

# --- Fix 3: CRS mismatch in vector_postprocess.py ---
patch(
    "Backend/vector_postprocess.py",
    '''def clean_for_frontend(gdf_3857: gpd.GeoDataFrame, min_area_m2: float = 9.0, tolerance_m: float = 0.35) -> gpd.GeoDataFrame:
    """Input: gdf already in EPSG:3857 (your gdf_geo_3857). Output: cleaned, EPSG:4326, Leaflet-ready."""
    gdf = fix_invalid(gdf_3857)
    gdf = drop_small(gdf, min_area_m2)
    gdf = simplify(gdf, tolerance_m)
    gdf = fix_invalid(gdf)
    return gdf.to_crs(epsg=4326)''',
    '''def clean_for_frontend(gdf_3857: gpd.GeoDataFrame, min_area_m2: float = 9.0, tolerance_m: float = 0.35) -> gpd.GeoDataFrame:
    """Input: gdf already in EPSG:3857 (your gdf_geo_3857). Output: cleaned, still EPSG:3857 —
    the frontend's worldToPixelGeoJSON() expects Web Mercator meters, NOT lat/lng. Do not reproject to 4326."""
    gdf = fix_invalid(gdf_3857)
    gdf = drop_small(gdf, min_area_m2)
    gdf = simplify(gdf, tolerance_m)
    gdf = fix_invalid(gdf)
    return gdf''',
    "vector_postprocess.py CRS fix (stop reprojecting to 4326)"
)

# --- Verify: syntax-check all three patched files ---
for f in ["Backend/frame_field_polygonize.py", "Backend/vectorization.py", "Backend/vector_postprocess.py"]:
    py_compile.compile(f, doraise=True)
    print(f"[OK] {f} compiles cleanly")

# --- Verify: no leftover bad references anywhere ---
for f in ["Backend/frame_field_polygonize.py", "Backend/vectorization.py"]:
    t = pathlib.Path(f).read_text(encoding="utf-8")
    assert "not gdf_clean.empty" not in t, f"[FAIL] {f} still has the self-reference bug!"
    print(f"[OK] {f} no longer references gdf_clean before assignment")

t = pathlib.Path("Backend/vector_postprocess.py").read_text(encoding="utf-8")
assert "epsg=4326" not in t, "[FAIL] vector_postprocess.py still reprojects to 4326!"
print("[OK] vector_postprocess.py no longer reprojects to EPSG:4326")

print("\nAll patches applied and verified. Restart the server and hit both /vectorize endpoints for real before trusting this.")
