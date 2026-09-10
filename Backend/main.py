import uuid
import json
from pathlib import Path

import numpy as np
import rasterio
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image

from model import load_model

app = FastAPI(title="CadastraAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AOI_ROOT = Path("aois")
AOI_ROOT.mkdir(exist_ok=True)

DEVICE = "cpu"
CHECKPOINT_PATH = "models/best_epoch12_val4.4813.pth"
model = load_model(CHECKPOINT_PATH, device=DEVICE)


def aoi_dir(aoi_id: str) -> Path:
    d = AOI_ROOT / aoi_id
    if not d.exists():
        raise HTTPException(status_code=404, detail="AOI not found")
    return d


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/aoi/upload")
async def upload_aoi(file: UploadFile = File(...)):
    aoi_id = uuid.uuid4().hex
    d = AOI_ROOT / aoi_id
    d.mkdir(parents=True)

    raster_path = d / "original.tif"
    with raster_path.open("wb") as f:
        f.write(await file.read())

    with rasterio.open(raster_path) as src:
        transform_affine = src.transform
        width, height = src.width, src.height
        crs = src.crs.to_string() if src.crs else None

        left = transform_affine.c
        top = transform_affine.f
        resolution = transform_affine.a

        band_count = min(src.count, 3)
        arr = src.read(list(range(1, band_count + 1)))

        arr = arr.astype(np.float32)
        for b in range(arr.shape[0]):
            band = arr[b]
            lo, hi = np.percentile(band, [2, 98])
            if hi > lo:
                band = np.clip((band - lo) / (hi - lo), 0, 1)
            else:
                band = np.zeros_like(band)
            arr[b] = band
        arr = (arr * 255).astype(np.uint8)

        if band_count == 1:
            img = Image.fromarray(arr[0], mode="L").convert("RGB")
        else:
            img = Image.fromarray(np.transpose(arr, (1, 2, 0)), mode="RGB")

    preview_path = d / "preview.jpg"
    img.save(preview_path, "JPEG", quality=90)

    transform = {
        "left": left,
        "top": top,
        "resolution": resolution,
        "width": width,
        "height": height,
    }

    meta = {
        "aoi_id": aoi_id,
        "original_filename": file.filename,
        "crs": crs,
        "transform": transform,
    }
    with (d / "meta.json").open("w") as f:
        json.dump(meta, f, indent=2)

    return meta


@app.post("/aoi/{aoi_id}/infer")
def infer_aoi(aoi_id: str):
    d = aoi_dir(aoi_id)
    raster_path = d / "original.tif"
    if not raster_path.exists():
        raise HTTPException(status_code=404, detail="AOI raster not found")

    with rasterio.open(raster_path) as src:
        band_count = min(src.count, 3)
        arr = src.read(list(range(1, band_count + 1))).astype(np.float32)
        if band_count == 1:
            arr = np.repeat(arr, 3, axis=0)

    # scale 0-1, no mean/std (matches training preprocessing)
    arr = arr / 255.0 if arr.max() > 1.0 else arr
    tensor = torch.from_numpy(arr).unsqueeze(0).float()

    with torch.no_grad():
        out = model(tensor)

    mask_prob = torch.sigmoid(out["mask"]).squeeze().numpy()
    edge_prob = torch.sigmoid(out["edge"]).squeeze().numpy()
    frame_field = out["frame_field"].squeeze().numpy()  # cos2theta, sin2theta - no activation

    infer_dir = d / "inference"
    infer_dir.mkdir(exist_ok=True)
    np.savez(
        infer_dir / "output.npz",
        mask=mask_prob,
        edge=edge_prob,
        frame_field=frame_field,
    )

    result = {
        "aoi_id": aoi_id,
        "checkpoint": CHECKPOINT_PATH,
        "shapes": {
            "mask": list(mask_prob.shape),
            "edge": list(edge_prob.shape),
            "frame_field": list(frame_field.shape),
        },
        "mask_mean_prob": float(mask_prob.mean()),
        "edge_mean_prob": float(edge_prob.mean()),
        "cached_to": str(infer_dir / "output.npz"),
    }

    with (d / "infer_meta.json").open("w") as f:
        json.dump(result, f, indent=2)

    return result


@app.get("/aoi/{aoi_id}/transform")
def get_transform(aoi_id: str):
    d = aoi_dir(aoi_id)
    with (d / "meta.json").open() as f:
        meta = json.load(f)
    return meta["transform"]


@app.get("/aoi/{aoi_id}/preview.jpg")
def get_preview(aoi_id: str):
    d = aoi_dir(aoi_id)
    preview_path = d / "preview.jpg"
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview not found")
    return FileResponse(preview_path, media_type="image/jpeg")


@app.get("/aoi")
def list_aois():
    out = []
    for d in AOI_ROOT.iterdir():
        meta_path = d / "meta.json"
        if meta_path.exists():
            with meta_path.open() as f:
                out.append(json.load(f))
    return out

from frame_field_polygonize import vectorize_frame_field

@app.post("/aoi/{aoi_id}/vectorize/frame_field")
def vectorize_aoi_frame_field(aoi_id: str):
    d = aoi_dir(aoi_id)
    try:
        result = vectorize_frame_field(aoi_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    out_path = d / "vectorize" / "frame_field.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result))
    return result

from vectorization import vectorize_watershed

@app.post("/aoi/{aoi_id}/vectorize")
def vectorize_aoi(aoi_id: str):
    d = aoi_dir(aoi_id)
    try:
        result = vectorize_watershed(aoi_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    out_path = d / "vectorize" / "watershed.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result))
    return result
