import pathlib, sys

path = "Frontend/src/App.jsx"
text = pathlib.Path(path).read_text(encoding="utf-8")

def patch(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        print(f"[FAIL] {label}: expected 1 match, found {count}. ABORTING - no changes written.")
        print("----- First 300 chars of what I searched for -----")
        print(old[:300])
        sys.exit(1)
    text = text.replace(old, new)
    print(f"[OK] {label}")

# --- 1. DATA/TIFF block -> add API_BASE/AOI_ID, keep only static `polygons` ---
patch(
"""const DATA = {
  quality: '/data/cadastraai_gis_quality_controlled.geojson',
  detected: '/data/cadastraai_detected_regions.geojson',
  polygons: '/data/btm_layout_0015_polygons.geojson',
  image: '/data/btm_layout_0015_preview.jpeg',
  tif: '/data/btm_layout_0015_georeferenced.tif'
};
const TIFF = { left: 8639830.18113004, top: 1450316.1746829334, resolution: 0.5971642834780747, width: 512, height: 512 };""",
"""const API_BASE = 'http://localhost:8000'; // confirm this matches your uvicorn port
const AOI_ID = '313e0e44cae54ef299065c8ceff7cf6d'; // TODO backlog item 6: hardcoded until multi-AOI support exists

const DATA = {
  // no backend endpoint produces source/ground-truth polygons yet - stays static
  polygons: '/data/btm_layout_0015_polygons.geojson'
};
// fallback defaults; overwritten in place by the live /aoi/{aoi_id}/transform fetch below
const TIFF = { left: 8639830.18113004, top: 1450316.1746829334, resolution: 0.5971642834780747, width: 512, height: 512 };""",
"DATA/TIFF block + API_BASE/AOI_ID constants"
)

# --- 2. useEffect: static fetches -> live backend ---
patch(
"""  useEffect(() => {
    Promise.all([fetch(DATA.quality).then(r => r.json()), fetch(DATA.detected).then(r => r.json()), fetch(DATA.polygons).then(r => r.json())])
      .then(([q,d,p]) => { setQuality(worldToPixelGeoJSON(q)); setDetected(d); setPolygons(worldToPixelGeoJSON(p)); })
      .catch(e => console.error('Actual GIS data load failed:', e)).finally(() => setLoading(false));
  }, []);""",
"""  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/aoi/${AOI_ID}/transform`).then(r => r.json()),
      fetch(`${API_BASE}/aoi/${AOI_ID}/vectorize/frame_field`, { method: 'POST' }).then(r => r.json()),
      fetch(DATA.polygons).then(r => r.json()).catch(() => ({ type: 'FeatureCollection', features: [] })),
    ])
      .then(([transform, result, p]) => {
        Object.assign(TIFF, transform); // real per-AOI geotransform replaces the hardcoded fallback
        setQuality(worldToPixelGeoJSON(result.quality)); // EPSG:3857 -> pixel space
        setDetected(result.detected); // already pixel-space (Affine.identity() upstream)
        setPolygons(worldToPixelGeoJSON(p));
      })
      .catch(e => console.error('Live backend fetch failed:', e)).finally(() => setLoading(false));
  }, []);""",
"useEffect fetch: static files -> live /transform + /vectorize/frame_field"
)

# --- 3. ImageOverlay: static jpeg -> live preview ---
patch(
'url={DATA.image}',
'url={`${API_BASE}/aoi/${AOI_ID}/preview.jpg`}',
"ImageOverlay: static jpeg -> live /preview.jpg"
)

pathlib.Path(path).write_text(text, encoding="utf-8")
print("\\nAll 3 patches applied successfully.")
