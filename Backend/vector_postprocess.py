import geopandas as gpd
from shapely.validation import make_valid
from shapely.geometry import MultiPolygon


def fix_invalid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: make_valid(g) if g is not None and not g.is_valid else g
    )

    def strip_to_polygons(g):
        if g is None:
            return None
        if g.geom_type in ("Polygon", "MultiPolygon"):
            return g
        if g.geom_type == "GeometryCollection":
            polys = [x for x in g.geoms if x.geom_type in ("Polygon", "MultiPolygon")]
            if not polys:
                return None
            return polys[0] if len(polys) == 1 else MultiPolygon(polys)
        return None

    gdf["geometry"] = gdf.geometry.apply(strip_to_polygons)
    gdf = gdf[~gdf.geometry.isna()]
    return gdf[gdf.geometry.is_valid]


def drop_small(gdf: gpd.GeoDataFrame, min_area_m2: float = 9.0) -> gpd.GeoDataFrame:
    # area_m2 is already computed upstream in EPSG:3857 (approx meters at low latitude)
    if "area_m2" in gdf.columns:
        return gdf[gdf["area_m2"] >= min_area_m2].reset_index(drop=True)
    return gdf[gdf.geometry.area >= min_area_m2].reset_index(drop=True)


def simplify(gdf: gpd.GeoDataFrame, tolerance_m: float = 0.35) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(tolerance_m, preserve_topology=True)
    return gdf


def clean_for_frontend(gdf_3857: gpd.GeoDataFrame, min_area_m2: float = 9.0, tolerance_m: float = 0.35) -> gpd.GeoDataFrame:
    """Input: gdf already in EPSG:3857 (your gdf_geo_3857). Output: cleaned, still EPSG:3857 —
    the frontend's worldToPixelGeoJSON() expects Web Mercator meters, NOT lat/lng. Do not reproject to 4326."""
    gdf = fix_invalid(gdf_3857)
    gdf = drop_small(gdf, min_area_m2)
    gdf = simplify(gdf, tolerance_m)
    gdf = fix_invalid(gdf)
    return gdf
