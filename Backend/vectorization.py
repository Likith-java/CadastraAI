"""
vectorization.py
CadastraAI - Stage A: edge-guided watershed vectorization
"""

import json
from pathlib import Path

import numpy as np
import geopandas as gpd
from shapely.geometry import shape
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from scipy import ndimage as ndi
from rasterio.features import shapes as rio_shapes
from rasterio.transform import Affine

AOI_ROOT = Path("aois")

MASK_THRESH = 0.5
EDGE_THRESH = 0.3
MIN_INSTANCE_PIXELS = 15
PEAK_MIN_DISTANCE = 3


def load_inference(aoi_id: str):
    npz_path = AOI_ROOT / aoi_id / "inference" / "output.npz"
    if not npz_path.exists():
        raise FileNotFoundError(f"No cached inference for {aoi_id} at {npz_path}")
    data = np.load(npz_path)
    return data["mask"], data["edge"]


def load_geo_meta(aoi_id: str):
    meta_path = AOI_ROOT / aoi_id / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No meta.json for {aoi_id}")
    meta = json.loads(meta_path.read_text())
    tf = meta["transform"]
    transform = Affine(tf["resolution"], 0, tf["left"], 0, -tf["resolution"], tf["top"])
    crs = meta.get("crs", "EPSG:4326")
    return transform, crs


def watershed_instances(mask_prob: np.ndarray, edge_prob: np.ndarray) -> np.ndarray:
    binary_mask = mask_prob > MASK_THRESH
    edge_barrier = edge_prob > EDGE_THRESH

    interior = binary_mask & ~edge_barrier
    interior = ndi.binary_opening(interior, structure=np.ones((3, 3)))

    distance = ndi.distance_transform_edt(interior)
    coords = peak_local_max(distance, min_distance=PEAK_MIN_DISTANCE, labels=interior)
    local_max_mask = np.zeros_like(distance, dtype=bool)
    if coords.size:
        local_max_mask[tuple(coords.T)] = True
    markers, _ = ndi.label(local_max_mask)

    labels = watershed(-distance, markers, mask=binary_mask)
    return labels


def labels_to_polygons(labels: np.ndarray, transform: Affine, mask_prob: np.ndarray = None):
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
            "feature_id": int(value),
            "geometry": poly,
            "confidence": round(conf_by_id.get(int(value), 0.0), 4),
        })
    return polygons


def vectorize_watershed(aoi_id: str) -> dict:
    mask_prob, edge_prob = load_inference(aoi_id)
    transform, crs = load_geo_meta(aoi_id)

    labels = watershed_instances(mask_prob, edge_prob)

    detected_polys = labels_to_polygons(labels, Affine.identity(), mask_prob)
    gdf_detected = gpd.GeoDataFrame(detected_polys, geometry="geometry", crs=None)
    if not gdf_detected.empty:
        gdf_detected = gdf_detected[gdf_detected.geometry.area >= MIN_INSTANCE_PIXELS]
    kept_ids = set(gdf_detected["instance_id"]) if not gdf_detected.empty else set()

    geo_polys = labels_to_polygons(labels, transform, mask_prob)
    gdf_geo = gpd.GeoDataFrame(geo_polys, geometry="geometry", crs=crs)
    if not gdf_geo.empty:
        gdf_geo = gdf_geo[gdf_geo["instance_id"].isin(kept_ids)]
        gdf_geo_3857 = gdf_geo.to_crs(epsg=3857)
        gdf_geo_3857["area_m2"] = gdf_geo_3857.geometry.area.round(2)
    else:
        gdf_geo_3857 = gdf_geo

    from vector_postprocess import clean_for_frontend
    gdf_clean = clean_for_frontend(gdf_geo_3857) if not gdf_geo_3857.empty else gdf_geo_3857

    return {
        "detected": json.loads(gdf_detected.to_json()) if not gdf_detected.empty else {"type": "FeatureCollection", "features": []},
        "quality": json.loads(gdf_clean.to_json()) if not gdf_geo_3857.empty else {"type": "FeatureCollection", "features": []},
        "n_instances": int(len(gdf_clean)),
    }
