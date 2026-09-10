# CadastraAI — Automated Cadastral Mapping with Frame-Field Learning

> **Smart India Hackathon (SIH) Project**
> AI-powered building footprint extraction and cadastral boundary delineation from satellite imagery using deep learning and frame-field regularization.

---

##  Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Model Details](#model-details)
- [Backend API](#backend-api)
  - [Endpoints](#endpoints)
  - [Pipeline Flow](#pipeline-flow)
- [Vectorization Methods](#vectorization-methods)
  - [Watershed Segmentation (Stage A)](#watershed-segmentation-stage-a)
  - [Frame-Field Regularization (Stage B)](#frame-field-regularization-stage-b)
  - [Comparison Results](#comparison-results)
- [Frontend](#frontend)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Project Structure](#project-structure)
- [Technical References](#technical-references)
- [License](#license)

---

## Overview

**CadastraAI** automates the extraction of building footprints and cadastral (land parcel) boundaries from high-resolution satellite/aerial imagery. The system combines:

1. **Deep Learning Inference** — A custom multi-head U-Net with ResNet-34 encoder that simultaneously predicts building masks, edge maps, and frame-field orientation vectors.
2. **Dual Vectorization Pipeline** — Two complementary methods convert raster predictions into clean vector polygons:
   - **Watershed segmentation** for instance separation in dense layouts.
   - **Frame-field regularization** for geometrically clean, rectilinear polygon output.
3. **Interactive GIS Frontend** — A React + Leaflet web viewer for visualizing satellite imagery, AI predictions, and quality-controlled vector outputs.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CadastraAI                                │
│                                                                  │
│  ┌────────────────────┐      ┌────────────────────────────────┐  │
│  │     Frontend        │      │          Backend (FastAPI)      │  │
│  │  React + Leaflet    │◄────►│                                │  │
│  │  Vite Dev Server    │ REST │  ┌──────────┐  ┌────────────┐  │  │
│  │  :5173              │      │  │  Upload   │  │  Inference  │  │  │
│  └────────────────────┘      │  │  & Geo    │  │  Engine     │  │  │
│                               │  │  Metadata │  │  (PyTorch)  │  │  │
│                               │  └──────────┘  └──────┬─────┘  │  │
│                               │                       │         │  │
│                               │              ┌────────▼───────┐ │  │
│                               │              │  Vectorization  │ │  │
│                               │              │  ┌───────────┐  │ │  │
│                               │              │  │ Watershed  │  │ │  │
│                               │              │  │ (Stage A)  │  │ │  │
│                               │              │  ├───────────┤  │ │  │
│                               │              │  │Frame Field │  │ │  │
│                               │              │  │ (Stage B)  │  │ │  │
│                               │              │  └───────────┘  │ │  │
│                               │              └────────────────┘ │  │
│                               └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Model Details

| Property | Value |
|---|---|
| **Architecture** | Multi-head U-Net (`FrameFieldUnetDeep`) |
| **Encoder** | ResNet-34 (ImageNet weights not used at inference) |
| **Input** | 3-channel RGB, 512 × 512 px |
| **Checkpoint** | `best_epoch12_val4.4813.pth` |
| **Framework** | PyTorch + Segmentation Models PyTorch (SMP) |

### Output Heads

The model produces **three simultaneous outputs** from a shared decoder:

| Head | Output Shape | Activation | Description |
|---|---|---|---|
| `mask_head` | `[1, 512, 512]` | Sigmoid → probability | Building/parcel occupancy mask |
| `edge_head` | `[1, 512, 512]` | Sigmoid → probability | Boundary edge map between adjacent parcels |
| `frame_field_head` | `[2, 512, 512]` | Raw (cos2θ, sin2θ) | Frame-field orientation vectors for polygon regularization |

### Verified Inference Output

```
mask        [512, 512]    mean_prob = 0.42
edge        [512, 512]    mean_prob = 0.20
frame_field [2, 512, 512]
```

---

## Backend API

The backend is a **FastAPI** application served via Uvicorn. It handles raster upload, model inference, and vectorization.

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/aoi/upload` | Upload a GeoTIFF raster, extract geo-metadata and preview |
| `GET` | `/aoi` | List all uploaded AOIs |
| `GET` | `/aoi/{id}/preview.jpg` | Retrieve the RGB preview image |
| `GET` | `/aoi/{id}/transform` | Get the geo-transform (CRS, resolution, origin) |
| `POST` | `/aoi/{id}/infer` | Run model inference, cache `output.npz` |
| `POST` | `/aoi/{id}/vectorize` | Watershed vectorization → GeoJSON |
| `POST` | `/aoi/{id}/vectorize/frame_field` | Frame-field vectorization → GeoJSON |

### Pipeline Flow

```
Upload GeoTIFF
     │
     ▼
 /aoi/upload ──► Store raster, extract CRS/transform, generate preview.jpg
     │
     ▼
 /aoi/{id}/infer ──► Load model → forward pass → save mask, edge, frame_field (.npz)
     │
     ├──► /aoi/{id}/vectorize           → Watershed instance segmentation → GeoJSON
     │
     └──► /aoi/{id}/vectorize/frame_field → Frame-field regularized polygons → GeoJSON
```

Each vectorization endpoint returns:
- **`detected`** — Polygons in pixel coordinate space (for overlay on the 512×512 raster).
- **`quality`** — Polygons in projected CRS (EPSG:3857) with `area_m2` computed for each instance.
- **`n_instances`** — Total count of extracted building/parcel polygons.

---

## Vectorization Methods

### Watershed Segmentation (Stage A)

**File:** `vectorization.py`

Edge-guided watershed segmentation that uses the predicted edge map to separate touching buildings.

**Algorithm:**
1. Threshold the mask probability at 0.5 to get a binary building mask.
2. Threshold the edge probability at 0.3 to create an edge barrier.
3. Compute interior regions: `binary_mask AND NOT edge_barrier`.
4. Apply morphological opening to clean noise.
5. Compute Euclidean distance transform → find local maxima as watershed seeds.
6. Run watershed segmentation to assign instance labels.
7. Convert labeled regions to vector polygons via `rasterio.features.shapes`.
8. Filter by minimum area (15 px) and compute `area_m2` in EPSG:3857.

**Strengths:** Correctly separates individual buildings in dense residential layouts where buildings share walls or are closely packed.

---

### Frame-Field Regularization (Stage B)

**File:** `frame_field_polygonize.py`

Polygon regularization using the predicted frame-field orientation vectors, inspired by [Girard et al. (2020)](https://arxiv.org/abs/2004.14875).

**Algorithm:**
1. Decode frame-field: convert `(cos2θ, sin2θ)` → orientation angle θ at each pixel.
2. Threshold mask → extract outer contours via `skimage.measure.find_contours`.
3. Simplify each contour polygon (tolerance = 1.5 px).
4. For each polygon edge segment:
   - Sample the frame-field angle at the segment midpoint.
   - Snap the segment to the nearest axis-aligned direction from the field (0°, 90°, 180°, 270° relative to field angle).
5. Rebuild polygon from snapped segments, buffer(0) to fix topology.
6. Transform to geo-coordinates and compute `area_m2`.

**Strengths:** Produces geometrically regular (rectilinear) polygons that align with building wall orientations — critical for cadastral mapping where property boundaries follow building geometry.

---

### Comparison Results

Tested on AOI `btm_layout_0015` (BTM Layout, Bangalore — dense residential subdivision):

| Metric | Watershed (Stage A) | Frame-Field (Stage B) |
|---|---|---|
| **Instances detected** | 557 | 34 |
| **Mean area (m²)** | 86.71 | 1,404.34 |
| **Min area (m²)** | 6.78 | 4.62 |
| **Max area (m²)** | 1,090.50 | 4,633.62 |

**Analysis:**

- **Watershed** correctly separates individual plots in the dense layout. The average area of ~87 m² (~930 sq ft) is consistent with typical 30×40 ft residential plots in BTM Layout, Bangalore. A small number of instances at the lower end (< 10 m²) are likely noise slivers that can be filtered.

- **Frame-field** produces fewer, larger polygons because the current contour-based approach traces outer boundaries of connected mask components without splitting touching buildings. Multiple adjacent plots that share walls merge into single blobs. However, the polygon geometry produced is more regular and rectilinear — the method's core strength.

**Key Finding:** Conventional edge-guided watershed correctly separates individual plots in dense layouts; the frame-field regularizer improves polygon geometry (rectilinearity) but needs the full skeleton-splitting step from the original paper to match watershed's instance separation capability.

---

## Frontend

| Property | Value |
|---|---|
| **Framework** | React 18 + Vite 5 |
| **Map Library** | Leaflet + React-Leaflet |
| **CRS** | `CRS.Simple` (pixel-space overlay on raster preview) |

The frontend provides an interactive GIS viewer that displays:
- Satellite imagery preview (from uploaded GeoTIFF).
- AI-detected segmentation regions.
- Quality-controlled vector polygon overlays.
- Coordinate transform handling between EPSG:3857 and 512×512 pixel space.

### Data Assets

| File | Description |
|---|---|
| `btm_layout_0015_georeferenced.tif` | Source GeoTIFF (EPSG:3857, 512×512, 4 bands) |
| `btm_layout_0015_preview.jpeg` | Browser display preview |
| `btm_layout_0015_polygons.geojson` | Source reference polygons |
| `cadastraai_gis_quality_controlled.geojson` | QC GIS output with attributes |
| `cadastraai_detected_regions.geojson` | AI segmentation regions (pixel space) |

---

## Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **CUDA** (optional, for GPU inference — CPU works out of the box)

### Backend Setup

```bash
cd Backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Place your model checkpoint
# └── Backend/models/best_epoch12_val4.4813.pth

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd Frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# → http://localhost:5173
```

### Quick Test

```powershell
# 1. Health check
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"

# 2. Upload a GeoTIFF
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/aoi/upload" `
  -Method Post -Form @{ file = Get-Item "path/to/your.tif" }
$aoi_id = $response.aoi_id

# 3. Run inference
Invoke-RestMethod -Uri "http://127.0.0.1:8000/aoi/$aoi_id/infer" -Method Post

# 4. Vectorize (both methods)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/aoi/$aoi_id/vectorize" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8000/aoi/$aoi_id/vectorize/frame_field" -Method Post
```

---

## Project Structure

```
CadastraAI/
├── Backend/
│   ├── models/
│   │   └── best_epoch12_val4.4813.pth   # Trained model checkpoint
│   ├── aois/                             # Uploaded AOI data (runtime)
│   │   └── <aoi_id>/
│   │       ├── original.tif
│   │       ├── preview.jpg
│   │       ├── meta.json
│   │       ├── infer_meta.json
│   │       ├── inference/output.npz
│   │       └── vectorize/
│   │           ├── watershed.json
│   │           └── frame_field.json
│   ├── main.py                           # FastAPI application & endpoints
│   ├── model.py                          # FrameFieldUnetDeep model definition
│   ├── vectorization.py                  # Stage A: Watershed vectorization
│   ├── frame_field_polygonize.py         # Stage B: Frame-field regularization
│   ├── audit_checkpoint.py              # Utility: inspect checkpoint structure
│   ├── test_model_load.py              # Utility: verify model loads correctly
│   └── requirements.txt
├── Frontend/
│   ├── src/
│   │   ├── App.jsx                       # Main React application
│   │   ├── main.jsx                      # Entry point
│   │   └── styles.css                    # Application styles
│   ├── public/                           # Static assets & GIS data
│   ├── index.html
│   └── package.json
├── LICENSE                               # GPL-3.0
└── README.md
```

---

## Technical References

1. **Girard, N. et al.** (2020). *Polygonal Building Segmentation by Frame Field Learning.* [arXiv:2004.14875](https://arxiv.org/abs/2004.14875) — The theoretical foundation for the frame-field regularization pipeline.
2. **Segmentation Models PyTorch (SMP)** — [GitHub](https://github.com/qubvel/segmentation_models.pytorch) — Backbone library for the U-Net encoder/decoder architecture.
3. **Rasterio** — [Docs](https://rasterio.readthedocs.io/) — Raster I/O and coordinate transforms.
4. **GeoPandas + Shapely** — Vector geometry operations and GeoJSON serialization.

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <b>CadastraAI</b> · Smart India Hackathon · 2026
</p>
