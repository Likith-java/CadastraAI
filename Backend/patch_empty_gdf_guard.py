import pathlib, sys

# --- vectorization.py ---
path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\vectorization.py")
text = path.read_text(encoding="utf-8")

old = """    geo_polys = labels_to_polygons(labels, transform, mask_prob)
    gdf_geo = gpd.GeoDataFrame(geo_polys, geometry="geometry", crs=crs)
    if not gdf_geo.empty:
        gdf_geo = gdf_geo[gdf_geo["instance_id"].isin(kept_ids)]
        gdf_geo_3857 = gdf_geo.to_crs(epsg=3857)
        gdf_geo_3857["area_m2"] = gdf_geo_3857.geometry.area.round(2)
    else:
        gdf_geo_3857 = gdf_geo"""

new = """    geo_polys = labels_to_polygons(labels, transform, mask_prob)
    if geo_polys:
        gdf_geo = gpd.GeoDataFrame(geo_polys, geometry="geometry", crs=crs)
        gdf_geo = gdf_geo[gdf_geo["instance_id"].isin(kept_ids)]
    else:
        gdf_geo = gpd.GeoDataFrame(columns=["instance_id", "feature_id", "geometry", "confidence"], geometry="geometry", crs=crs)
    if not gdf_geo.empty:
        gdf_geo_3857 = gdf_geo.to_crs(epsg=3857)
        gdf_geo_3857["area_m2"] = gdf_geo_3857.geometry.area.round(2)
    else:
        gdf_geo_3857 = gdf_geo.set_crs(epsg=3857, allow_override=True)
        gdf_geo_3857["area_m2"] = []"""

count = text.count(old)
if count != 1:
    print(f"[FAIL] vectorization.py: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("vectorization.py patched successfully.")

# --- frame_field_polygonize.py ---
path2 = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\frame_field_polygonize.py")
text2 = path2.read_text(encoding="utf-8")

old2 = """    gdf_detected = gpd.GeoDataFrame(detected_polys, geometry="geometry", crs=None)
    gdf_geo = gpd.GeoDataFrame(geo_polys, geometry="geometry", crs=crs)
    if not gdf_geo.empty:
        gdf_geo_3857 = gdf_geo.to_crs(epsg=3857)
        gdf_geo_3857["area_m2"] = gdf_geo_3857.geometry.area.round(2)
    else:
        gdf_geo_3857 = gdf_geo"""

new2 = """    if detected_polys:
        gdf_detected = gpd.GeoDataFrame(detected_polys, geometry="geometry", crs=None)
    else:
        gdf_detected = gpd.GeoDataFrame(columns=["instance_id", "feature_id", "geometry", "confidence"], geometry="geometry", crs=None)

    if geo_polys:
        gdf_geo = gpd.GeoDataFrame(geo_polys, geometry="geometry", crs=crs)
    else:
        gdf_geo = gpd.GeoDataFrame(columns=["instance_id", "feature_id", "geometry", "confidence"], geometry="geometry", crs=crs)

    if not gdf_geo.empty:
        gdf_geo_3857 = gdf_geo.to_crs(epsg=3857)
        gdf_geo_3857["area_m2"] = gdf_geo_3857.geometry.area.round(2)
    else:
        gdf_geo_3857 = gdf_geo.set_crs(epsg=3857, allow_override=True)
        gdf_geo_3857["area_m2"] = []"""

count2 = text2.count(old2)
if count2 != 1:
    print(f"[FAIL] frame_field_polygonize.py: expected 1 match, found {count2}")
    sys.exit(1)
text2 = text2.replace(old2, new2)
path2.write_text(text2, encoding="utf-8")
print("frame_field_polygonize.py patched successfully.")
