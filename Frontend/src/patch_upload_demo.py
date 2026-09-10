import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Frontend\src\App.jsx")
text = path.read_text(encoding="utf-8")

patches = [
    (
        "const API_BASE = 'http://localhost:8000'; // confirm this matches your uvicorn port\nconst AOI_ID = '313e0e44cae54ef299065c8ceff7cf6d'; // TODO backlog item 6: hardcoded until multi-AOI support exists",
        "const API_BASE = 'http://localhost:8000'; // confirm this matches your uvicorn port\nconst DEFAULT_AOI_ID = '313e0e44cae54ef299065c8ceff7cf6d'; // fallback demo AOI; live upload+infer swaps this at runtime"
    ),
    (
        """  const [reviewOverrides, setReviewOverrides] = useState({}), [editing, setEditing] = useState(false), [draftGeometry, setDraftGeometry] = useState(null);

  useEffect(() => {
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
        """  const [reviewOverrides, setReviewOverrides] = useState({}), [editing, setEditing] = useState(false), [draftGeometry, setDraftGeometry] = useState(null);
  const [aoiId, setAoiId] = useState(DEFAULT_AOI_ID), [uploadStatus, setUploadStatus] = useState(null);

  const loadAoi = (id, opts) => {
    const includeSource = !!(opts && opts.includeSource);
    setLoading(true);
    setSelected(null);
    setReviewOverrides({});
    Promise.all([
      fetch(`${API_BASE}/aoi/${id}/transform`).then(r => r.json()),
      fetch(`${API_BASE}/aoi/${id}/vectorize/frame_field`, { method: 'POST' }).then(r => r.json()),
      includeSource ? fetch(DATA.polygons).then(r => r.json()).catch(() => ({ type: 'FeatureCollection', features: [] })) : Promise.resolve({ type: 'FeatureCollection', features: [] }),
    ])
      .then(([transform, result, p]) => {
        Object.assign(TIFF, transform); // real per-AOI geotransform replaces the hardcoded fallback
        setQuality(worldToPixelGeoJSON(result.quality)); // EPSG:3857 -> pixel space
        setDetected(result.detected); // already pixel-space (Affine.identity() upstream)
        setPolygons(worldToPixelGeoJSON(p));
      })
      .catch(e => console.error('Live backend fetch failed:', e)).finally(() => setLoading(false));
  };

  useEffect(() => { loadAoi(DEFAULT_AOI_ID, { includeSource: true }); }, []);

  const uploadAndInfer = async (file) => {
    setUploadStatus('Uploading image\u2026');
    try {
      const form = new FormData();
      form.append('file', file);
      const meta = await fetch(`${API_BASE}/aoi/upload`, { method: 'POST', body: form }).then(r => r.json());
      setUploadStatus('Running live inference\u2026');
      await fetch(`${API_BASE}/aoi/${meta.aoi_id}/infer`, { method: 'POST' }).then(r => r.json());
      setUploadStatus('Vectorizing detected footprints\u2026');
      setAoiId(meta.aoi_id);
      loadAoi(meta.aoi_id, { includeSource: false });
      setUploadStatus(`Live inference complete \u2014 new AOI ${meta.aoi_id.slice(0, 8)}\u2026`);
      setPage('map');
    } catch (e) {
      console.error('Upload/infer failed:', e);
      setUploadStatus('Upload or inference failed \u2014 check backend console');
    }
  };""",
    ),
    (
        "<div className=\"content\">{loading?<Loader/>:<Page page={page} stats={stats} quality={effectiveQuality} rawQuality={quality} detected={detected} polygons={polygons} selected={selected} setSelected={selectFeature} setPage={setPage} updateReview={updateReview} accept={accept} reject={reject} startEdit={startEdit} saveEdit={saveEdit} editing={editing} draftGeometry={draftGeometry} updateVertex={updateVertex} setEditing={setEditing} setDraftGeometry={setDraftGeometry} exportData={exportData}/>}</div>",
        "<div className=\"content\">{loading?<Loader/>:<Page page={page} stats={stats} quality={effectiveQuality} rawQuality={quality} detected={detected} polygons={polygons} selected={selected} setSelected={selectFeature} setPage={setPage} updateReview={updateReview} accept={accept} reject={reject} startEdit={startEdit} saveEdit={saveEdit} editing={editing} draftGeometry={draftGeometry} updateVertex={updateVertex} setEditing={setEditing} setDraftGeometry={setDraftGeometry} exportData={exportData} aoiId={aoiId} uploadAndInfer={uploadAndInfer} uploadStatus={uploadStatus}/>}</div>",
    ),
    (
        "function GISMap({quality,detected,polygons,selected,setSelected,accept,reject,startEdit,saveEdit,editing,draftGeometry,updateVertex,setEditing,setDraftGeometry,setPage}){",
        "function GISMap({quality,detected,polygons,selected,setSelected,accept,reject,startEdit,saveEdit,editing,draftGeometry,updateVertex,setEditing,setDraftGeometry,setPage,aoiId,uploadAndInfer,uploadStatus}){",
    ),
    (
        "<ImageOverlay url={`${API_BASE}/aoi/${AOI_ID}/preview.jpg`} bounds={bounds} opacity={0.96}/>",
        "<ImageOverlay url={`${API_BASE}/aoi/${aoiId}/preview.jpg`} bounds={bounds} opacity={0.96}/>",
    ),
    (
        "<div className=\"map-tools\"><label><input type=\"checkbox\" checked={showQC} onChange={e=>setShowQC(e.target.checked)}/> QC features</label><label><input type=\"checkbox\" checked={showAI} onChange={e=>setShowAI(e.target.checked)}/> AI regions</label><label><input type=\"checkbox\" checked={showSource} onChange={e=>setShowSource(e.target.checked)}/> Source</label></div>",
        "<div className=\"map-tools\"><label><input type=\"checkbox\" checked={showQC} onChange={e=>setShowQC(e.target.checked)}/> QC features</label><label><input type=\"checkbox\" checked={showAI} onChange={e=>setShowAI(e.target.checked)}/> AI regions</label><label><input type=\"checkbox\" checked={showSource} onChange={e=>setShowSource(e.target.checked)}/> Source</label></div><div className=\"map-tools\" style={{marginTop:6}}><label className=\"primary\" style={{cursor:'pointer',padding:'6px 12px',borderRadius:6,display:'inline-block'}}>\u21ea Upload new image (live inference)<input type=\"file\" accept=\"image/*,.tif,.tiff\" style={{display:'none'}} onChange={e=>{const f=e.target.files&&e.target.files[0];if(f)uploadAndInfer(f);e.target.value='';}}/></label>{uploadStatus&&<span style={{marginLeft:10,fontSize:13}}>{uploadStatus}</span>}</div>",
    ),
]

for i, (old, new) in enumerate(patches, 1):
    count = text.count(old)
    if count != 1:
        print(f"[FAIL] patch {i}: expected 1 match, found {count}")
        sys.exit(1)
    text = text.replace(old, new)
    print(f"[OK] patch {i} applied")

path.write_text(text, encoding="utf-8")
print("All patches applied successfully.")
