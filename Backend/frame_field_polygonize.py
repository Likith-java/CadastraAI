"""
frame_field_polygonize.py
CadastraAI - Stage B: frame-field-guided polygon regularization
(practical approximation of Girard et al. 2004.14875 - see module notes)
"""

import json
from pathlib import Path

import numpy as np
from skimage import measure
from shapely.geometry import Polygon
import geopandas as gpd
from rasterio.transform import Affine
from rasterio.features import rasterize

AOI_ROOT = Path("aois")

MASK_THRESH = 0.5
SIMPLIFY_TOL_PX = 1.5
MIN_POLY_AREA_PX = 15


def decode_frame_field(frame_field: np.ndarray) -> np.ndarray:
    """frame_field: [2,H,W] = (cos2theta, sin2theta) -> theta in [-pi/2, pi/2)."""
    cos2t, sin2t = frame_field[0], frame_field[1]
    return 0.5 * np.arctan2(sin2t, cos2t)


def local_field_angle(theta_map: np.ndarray, x: float, y: float) -> float:
    h, w = theta_map.shape
    xi = int(np.clip(round(x), 0, w - 1))
    yi = int(np.clip(round(y), 0, h - 1))
    return theta_map[yi, xi]


def snap_segment_to_field(p0, p1, theta_map):
    mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
    field_theta = local_field_angle(theta_map, mx, my)
    seg_angle = np.arctan2(p1[1] - p0[1], p1[0] - p0[0])
    candidates = [field_theta, field_theta + np.pi / 2,
                  field_theta - np.pi / 2, field_theta + np.pi]
    target = min(candidates, key=lambda a: abs(((seg_angle - a) + np.pi) % (2 * np.pi) - np.pi))
    length = np.hypot(p1[0] - p0[0], p1[1] - p0[1])
    dx, dy = np.cos(target) * length / 2.0, np.sin(target) * length / 2.0
    return (mx - dx, my - dy), (mx + dx, my + dy)


def regularize_contour(contour_yx: np.ndarray, theta_map: np.ndarray):
    poly = Polygon([(x, y) for y, x in contour_yx])
    if not poly.is_valid or poly.area < MIN_POLY_AREA_PX:
        return None
    simplified = poly.simplify(SIMPLIFY_TOL_PX, preserve_topology=True)
    coords = list(simplified.exterior.coords)[:-1]
    if len(coords) < 3:
        return None
    new_pts = []
    for i in range(len(coords)):
        p0, p1 = coords[i], coords[(i + 1) % len(coords)]
        s0, s1 = snap_segment_to_field(p0, p1, theta_map)
        new_pts.append(s0)
        new_pts.append(s1)
    reg_poly = Polygon(new_pts).buffer(0)
    if reg_poly.is_empty:
        return None
    if reg_poly.geom_type == "MultiPolygon":
        reg_poly = max(reg_poly.geoms, key=lambda g: g.area)
    return reg_poly


def vectorize_frame_field(aoi_id: str) -> dict:
    npz_path = AOI_ROOT / aoi_id / "inference" / "output.npz"
    if not npz_path.exists():
        raise FileNotFoundError(f"No cached inference for {aoi_id}")
    data = np.load(npz_path)
    mask_prob, frame_field = data["mask"], data["frame_field"]

    meta_path = AOI_ROOT / aoi_id / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No meta.json for {aoi_id}")
    meta = json.loads(meta_path.read_text())
    tf = meta["transform"]
    transform = Affine(tf["resolution"], 0, tf["left"], 0, -tf["resolution"], tf["top"])
    crs = meta.get("crs", "EPSG:4326")

    theta_map = decode_frame_field(frame_field)
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
        geo_polys.append({"instance_id": i, "feature_id": i, "geometry": Polygon(geo_coords), "confidence": confidence})

    gdf_detected = gpd.GeoDataFrame(detected_polys, geometry="geometry", crs=None)
    gdf_geo = gpd.GeoDataFrame(geo_polys, geometry="geometry", crs=crs)
    if not gdf_geo.empty:
        gdf_geo_3857 = gdf_geo.to_crs(epsg=3857)
        gdf_geo_3857["area_m2"] = gdf_geo_3857.geometry.area.round(2)
    else:
        gdf_geo_3857 = gdf_geo

    from vector_postprocess import clean_for_frontend
    gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_geo_3857.empty else gdf_geo_3857

    return {
        "detected": json.loads(gdf_detected.to_json()) if not gdf_detected.empty else {"type": "FeatureCollection", "features": []},
        "quality": json.loads(gdf_clean.to_json()) if not gdf_geo_3857.empty else {"type": "FeatureCollection", "features": []},
        "n_instances": len(gdf_clean),
        "method": "frame_field_regularized",
    }

