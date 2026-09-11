import React, { useEffect, useMemo, useState } from 'react';
import { MapContainer, ImageOverlay, GeoJSON, useMap, CircleMarker, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const API_BASE = 'http://localhost:8000'; // confirm this matches your uvicorn port
const DEFAULT_AOI_ID = '313e0e44cae54ef299065c8ceff7cf6d'; // fallback demo AOI; live upload+infer swaps this at runtime

const DATA = {
  // no backend endpoint produces source/ground-truth polygons yet - stays static
  polygons: '/data/btm_layout_0015_polygons.geojson'
};
// fallback defaults; overwritten in place by the live /aoi/{aoi_id}/transform fetch below
const TIFF = { left: 8639830.18113004, top: 1450316.1746829334, resolution: 0.5971642834780747, width: 512, height: 512 };

const pixelToLatLng = ([x, y]) => L.latLng(TIFF.height - y, x);
const latLngToPixel = (latlng) => [latlng.lng, TIFF.height - latlng.lat];

function worldToPixelFeature(feature) {
  const convert = c => [(c[0] - TIFF.left) / TIFF.resolution, (TIFF.top - c[1]) / TIFF.resolution];
  const walk = coords => Array.isArray(coords[0]) ? coords.map(walk) : convert(coords);
  return { ...feature, geometry: { ...feature.geometry, coordinates: walk(feature.geometry.coordinates) } };
}
function worldToPixelGeoJSON(data) { return { ...data, features: (data.features || []).map(worldToPixelFeature) }; }
function pixelToWorldFeature(feature) {
  const convert = c => [c[0] * TIFF.resolution + TIFF.left, TIFF.top - c[1] * TIFF.resolution];
  const walk = coords => Array.isArray(coords[0]) ? coords.map(walk) : convert(coords);
  return { ...feature, geometry: { ...feature.geometry, coordinates: walk(feature.geometry.coordinates) } };
}
function FitBounds({ bounds }) { const map = useMap(); useEffect(() => { map.fitBounds(bounds, { padding: [18, 18] }); }, [map, bounds]); return null; }
function Logo() { return <div className="brand"><div className="brand-mark">C</div><div><div className="brand-name">CADASTRA <span>AI</span></div><div className="brand-sub">GEOSPATIAL INTELLIGENCE</div></div></div>; }
const nav = [['dashboard','Dashboard','⌂'],['surveys','Surveys','▣'],['map','GIS Map Explorer','⌖'],['review','Review Queue','✓'],['analytics','Analytics','◒'],['data','Data','▤'],['export','Export','⇩']];
const STATUS = { pending: 'Pending', approved: 'Approved', rejected: 'Rejected' };

function App() {
  const [page, setPage] = useState('dashboard'), [logged, setLogged] = useState(false);
  const [quality, setQuality] = useState(null), [detected, setDetected] = useState(null), [polygons, setPolygons] = useState(null);
  const [loading, setLoading] = useState(true), [dark, setDark] = useState(false), [selected, setSelected] = useState(null);
  const [reviewOverrides, setReviewOverrides] = useState({}), [editing, setEditing] = useState(false), [draftGeometry, setDraftGeometry] = useState(null);
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

  const uploadAndInfer = async (file, bounds) => {
    setUploadStatus('Uploading image…');
    try {
      const form = new FormData();
      form.append('file', file);
      if (bounds && bounds.north !== '' && bounds.south !== '' && bounds.east !== '' && bounds.west !== '') {
        form.append('north', bounds.north);
        form.append('south', bounds.south);
        form.append('east', bounds.east);
        form.append('west', bounds.west);
      }
      const meta = await fetch(`${API_BASE}/aoi/upload`, { method: 'POST', body: form }).then(r => r.json());
      setUploadStatus('Running live inference…');
      await fetch(`${API_BASE}/aoi/${meta.aoi_id}/infer`, { method: 'POST' }).then(r => r.json());
      setUploadStatus('Vectorizing detected footprints…');
      setAoiId(meta.aoi_id);
      loadAoi(meta.aoi_id, { includeSource: false });
      setUploadStatus(`Live inference complete — new AOI ${meta.aoi_id.slice(0, 8)}…`);
      setPage('map');
    } catch (e) {
      console.error('Upload/infer failed:', e);
      setUploadStatus('Upload or inference failed — check backend console');
    }
  };

  const effectiveFeature = f => {
    if (!f) return null;
    const id = f.properties?.feature_id;
    const o = reviewOverrides[id] || {};
    return { ...f, geometry: o.geometry || f.geometry, properties: { ...f.properties, ...(o.properties || {}) } };
  };
  const effectiveQuality = useMemo(() => ({ ...(quality || {}), features: (quality?.features || []).map(effectiveFeature) }), [quality, reviewOverrides]);
  const stats = useMemo(() => {
    const fs = effectiveQuality.features || [];
    const pending = fs.filter(f => (f.properties?.review_status || 'pending') === 'pending').length;
    const approved = fs.filter(f => f.properties?.review_status === 'approved').length;
    const rejected = fs.filter(f => f.properties?.review_status === 'rejected').length;
    const reviewRequired = fs.filter(f => f.properties?.review_required === true).length;
    const totalArea = fs.reduce((s,f) => s + Number(f.properties?.area_m2 || 0), 0);
    return { total: fs.length, pending, approved, rejected, reviewRequired, totalArea, detected: detected?.features?.length || 0 };
  }, [effectiveQuality, detected]);

  const selectFeature = f => { setSelected(effectiveFeature(f)); setEditing(false); setDraftGeometry(null); };
  const updateReview = (id, changes) => setReviewOverrides(prev => ({ ...prev, [id]: { ...(prev[id] || {}), properties: { ...(prev[id]?.properties || {}), ...changes } } }));
  const accept = id => updateReview(id, { review_status: 'approved', review_required: false, reviewed_at: new Date().toISOString(), review_note: reviewOverrides[id]?.properties?.review_note || '' });
  const reject = (id, reason, note) => updateReview(id, { review_status: 'rejected', review_required: false, rejection_reason: reason, review_note: note || '', reviewed_at: new Date().toISOString() });
  const startEdit = feature => { const ring = feature?.geometry?.coordinates?.[0]; if (ring?.length >= 3) { setDraftGeometry(ring.map(p => [...p])); setEditing(true); } };
  const saveEdit = id => {
    if (!draftGeometry) return;
    setReviewOverrides(prev => ({ ...prev, [id]: { ...(prev[id] || {}), geometry: { type: 'Polygon', coordinates: [draftGeometry] }, properties: { ...(prev[id]?.properties || {}), review_status: 'pending', review_required: true, boundary_edited: true } } }));
    setEditing(false); setDraftGeometry(null); setSelected(effectiveFeature({ ...selected, geometry: { type: 'Polygon', coordinates: [draftGeometry] } }));
  };
  const updateVertex = (index, latlng) => setDraftGeometry(prev => prev.map((p,i) => i === index ? latLngToPixel(latlng) : p));

  const exportData = () => {
    const reviewedPixel = { ...quality, features: (quality?.features || []).map(effectiveFeature) };
    const out = { ...reviewedPixel, features: reviewedPixel.features.map(pixelToWorldFeature), crs: quality?.crs || { type: 'name', properties: { name: 'EPSG:3857' } } };
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/geo+json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'cadastraai_reviewed_qc_output.geojson'; a.click(); URL.revokeObjectURL(a.href);
  };

  if (!logged) return <Login onLogin={() => setLogged(true)} />;
  return <div className={dark ? 'app dark' : 'app'}>
    <aside className="sidebar"><Logo/><div className="section-label">WORKSPACE</div>{nav.map(([id,label,icon]) => <button key={id} className={page===id?'nav active':'nav'} onClick={() => setPage(id)}><span className="nav-icon">{icon}</span>{label}{id==='review' && stats.pending > 0 && <span className="nav-count">{stats.pending}</span>}</button>)}<div className="sidebar-bottom"><button className="nav" onClick={() => setPage('settings')}><span className="nav-icon">⚙</span>Settings</button><button className="nav" onClick={() => setPage('help')}><span className="nav-icon">?</span>Help</button><div className="user-mini"><div className="avatar">PV</div><div><b>Project Admin</b><small>DoLR Workspace</small></div></div></div></aside>
    <main className="main"><header><div><div className="crumb">DoLR / CADASTRA AI</div><h1>{pageTitle(page)}</h1></div><div className="header-actions"><span className="live"><i/> Live GIS Dataset</span><button className="icon-btn" onClick={() => setDark(!dark)}>{dark?'☀':'◐'}</button></div></header><div className="content">{loading?<Loader/>:<Page page={page} stats={stats} quality={effectiveQuality} rawQuality={quality} detected={detected} polygons={polygons} selected={selected} setSelected={selectFeature} setPage={setPage} updateReview={updateReview} accept={accept} reject={reject} startEdit={startEdit} saveEdit={saveEdit} editing={editing} draftGeometry={draftGeometry} updateVertex={updateVertex} setEditing={setEditing} setDraftGeometry={setDraftGeometry} exportData={exportData} aoiId={aoiId} uploadAndInfer={uploadAndInfer} uploadStatus={uploadStatus}/>}</div></main>
  </div>;
}
function pageTitle(p){return ({dashboard:'Dashboard',surveys:'Surveys',map:'GIS Map Explorer',review:'Review Queue',analytics:'Analytics',data:'Data Management',export:'Export',settings:'Settings',help:'Help'})[p]||'Dashboard'}
function Loader(){return <div className="loader-card"><div className="spinner"/><h2>Loading actual GIS dataset</h2><p>Reading CADASTRA AI quality-controlled polygons and detected regions.</p></div>}
function Login({onLogin}){const [mode,setMode]=useState('login'); return <div className="auth"><div className="auth-visual"><div className="visual-copy"><div className="big-c">C</div><h1>CADASTRA <span>AI</span></h1><p>AI-powered cadastral intelligence for faster, cleaner and more reliable urban mapping.</p><div className="auth-points"><span>✓ AI-assisted feature extraction</span><span>✓ GIS quality control</span><span>✓ Human-in-the-loop review</span></div></div></div><div className="auth-panel"><Logo/><div className="auth-box"><div className="eyebrow">SECURE WORKSPACE</div><h2>{mode==='login'?'Welcome back':'Create workspace account'}</h2><p>{mode==='login'?'Sign in to continue to your geospatial workspace.':'Set up your CADASTRA AI workspace.'}</p>{mode==='signup'&&<input placeholder="Full name"/>}<input placeholder="Email address" type="email"/><input placeholder="Password" type="password"/><button className="primary wide" onClick={onLogin}>{mode==='login'?'Sign in':'Create account'}</button><button className="text-btn" onClick={()=>setMode(mode==='login'?'signup':'login')}>{mode==='login'?"Don't have an account? Create one":"Already have an account? Sign in"}</button></div></div></div>}

function Page(props){const {page}=props;if(page==='dashboard')return <Dashboard {...props}/>;if(page==='map')return <GISMap {...props}/>;if(page==='review')return <Review {...props}/>;if(page==='analytics')return <Analytics {...props}/>;if(page==='data')return <DataPage/>;if(page==='export')return <Export {...props}/>;if(page==='surveys')return <Surveys {...props}/>;return <Placeholder title={pageTitle(page)}/>;}
function Dashboard({stats,setPage}){return <><div className="hero-row"><div><div className="eyebrow">URBAN PARCEL MAPPING / AOI-0015</div><h2 className="hero-title">Geospatial Intelligence Overview</h2><p className="muted">Actual GIS outputs loaded from the supplied CADASTRA AI dataset.</p></div><button className="primary" onClick={()=>setPage('map')}>Open GIS Explorer →</button></div><div className="stat-grid"><Stat label="QC Features" value={stats.total} note="quality-controlled polygons"/><Stat label="AI Detections" value={stats.detected} note="segmentation regions"/><Stat label="Needs Review" value={stats.pending} note="human verification queue"/><Stat label="Approved / Rejected" value={`${stats.approved} / ${stats.rejected}`} note="review decisions"/></div><div className="grid-two"><div className="card"><CardHead title="Processing status"/><div className="process"><div className="process-icon">✓</div><div><b>GIS quality control loaded</b><p>{stats.total} supplied QC features are available for inspection.</p></div><span className="badge success">READY</span></div><div className="process"><div className="process-icon blue">AI</div><div><b>AI segmentation output loaded</b><p>{stats.detected} detected regions from the supplied mask handoff.</p></div><span className="badge">LOADED</span></div></div><div className="card"><CardHead title="Review workload" action="Review queue" onClick={()=>setPage('review')}/><div className="big-number">{stats.pending}<small> items pending</small></div><div className="bar"><span style={{width:Math.min(100,(stats.pending/Math.max(stats.total,1))*100)+'%'}}/></div><p className="muted">Accept, reject or edit flagged features through human verification.</p></div></div></>}
function Stat({label,value,note}){return <div className="card stat"><span className="muted">{label}</span><strong>{value}</strong><small>{note}</small></div>}
function CardHead({title,action,onClick}){return <div className="card-head"><h3>{title}</h3>{action&&<button className="link-btn" onClick={onClick}>{action} →</button>}</div>}

function GISMap({quality,detected,polygons,selected,setSelected,accept,reject,startEdit,saveEdit,editing,draftGeometry,updateVertex,setEditing,setDraftGeometry,setPage,aoiId,uploadAndInfer,uploadStatus}){
  const bounds=[[0,0],[512,512]];
  const [showQC,setShowQC]=useState(true),[showAI,setShowAI]=useState(true),[showSource,setShowSource]=useState(true);
  const [showGeoRef,setShowGeoRef]=useState(false);
  const [manualBounds,setManualBounds]=useState({north:'',south:'',east:'',west:''});
  const [rejecting,setRejecting]=useState(false),[reason,setReason]=useState(''),[note,setNote]=useState('');
  const styleQ=f=>{const s=f.properties?.review_status||'pending';return {color:s==='approved'?'#16a34a':s==='rejected'?'#dc2626':f.properties?.review_required?'#f59e0b':'#2563eb',weight:3,fillOpacity:.13};};
  const doReject=()=>{if(!selected)return;reject(selected.properties.feature_id,reason||'Other',note);setRejecting(false);setReason('');setNote('');setSelected({...selected,properties:{...selected.properties,review_status:'rejected',review_required:false,rejection_reason:reason||'Other',review_note:note}});};
  return <div className="map-layout"><div className="map-card"><MapContainer crs={L.CRS.Simple} bounds={bounds} maxBounds={bounds} minZoom={-2} maxZoom={3} zoom={0} style={{height:'100%',width:'100%'}}><ImageOverlay url={`${API_BASE}/aoi/${aoiId}/preview.jpg`} bounds={bounds} opacity={0.96}/>{showSource&&polygons&&<GeoJSON data={polygons} style={()=>({color:'#22c55e',weight:1,fillOpacity:.035})} coordsToLatLng={pixelToLatLng}/>} {showAI&&detected&&<GeoJSON data={detected} style={()=>({color:'#7c3aed',weight:1,fillOpacity:.06,dashArray:'4 4'})} coordsToLatLng={pixelToLatLng}/>} {showQC&&quality&&<GeoJSON data={quality} style={styleQ} onEachFeature={(f,l)=>l.on({click:()=>setSelected(f)})} coordsToLatLng={pixelToLatLng}/>} {editing&&draftGeometry&&<EditVertices ring={draftGeometry} updateVertex={updateVertex}/>}<FitBounds bounds={bounds}/></MapContainer><div className="map-tools"><label><input type="checkbox" checked={showQC} onChange={e=>setShowQC(e.target.checked)}/> QC features</label><label><input type="checkbox" checked={showAI} onChange={e=>setShowAI(e.target.checked)}/> AI regions</label><label><input type="checkbox" checked={showSource} onChange={e=>setShowSource(e.target.checked)}/> Source</label></div><div className="upload-tools"><label className="primary" style={{cursor:'pointer',padding:'6px 12px',borderRadius:6,display:'inline-block'}}>⇪ Upload new image (live inference)<input type="file" accept="image/*,.tif,.tiff" style={{display:'none'}} onChange={e=>{const f=e.target.files&&e.target.files[0];if(f)uploadAndInfer(f, showGeoRef?manualBounds:null);e.target.value='';}}/></label><label style={{fontSize:9,display:'flex',alignItems:'center',gap:4,whiteSpace:'nowrap'}}><input type="checkbox" checked={showGeoRef} onChange={e=>setShowGeoRef(e.target.checked)}/> Manual bounds</label>{showGeoRef&&<><input placeholder="North" value={manualBounds.north} onChange={e=>setManualBounds({...manualBounds,north:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/><input placeholder="South" value={manualBounds.south} onChange={e=>setManualBounds({...manualBounds,south:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/><input placeholder="East" value={manualBounds.east} onChange={e=>setManualBounds({...manualBounds,east:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/><input placeholder="West" value={manualBounds.west} onChange={e=>setManualBounds({...manualBounds,west:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/></>}{uploadStatus&&<span style={{fontSize:9}}>{uploadStatus}</span>}</div><div className="map-legend"><b>Legend</b><span><i className="line blue"/> Pending</span><span><i className="line green"/> Approved</span><span><i className="line red"/> Rejected</span><span><i className="line purple"/> AI output</span></div></div><div className="side-panel"><div className="eyebrow">GIS EXPLORER</div><h2>Feature inspection</h2><p className="muted">Click a QC feature on the map to open its human-verification workflow.</p>{selected?<ReviewPanel feature={selected} accept={accept} setSelected={setSelected} rejecting={rejecting} setRejecting={setRejecting} reason={reason} setReason={setReason} note={note} setNote={setNote} doReject={doReject} startEdit={startEdit} saveEdit={saveEdit} editing={editing} setEditing={setEditing}/>:<><div className="layer-list"><div><b>QC features</b><span>{quality?.features?.length||0}</span></div><div><b>AI regions</b><span>{detected?.features?.length||0}</span></div><div><b>Source polygons</b><span>{polygons?.features?.length||0}</span></div></div><div className="empty-select"><div>⌖</div><b>Select a QC feature</b><p>Choose a polygon to inspect attributes and record a review decision.</p></div></>}{editing&&<div className="edit-hint"><b>Boundary editing mode</b><p>Drag the vertex handles on the map, then save the boundary.</p><button className="small-btn" onClick={()=>{setEditing(false);setDraftGeometry(null)}}>Cancel edit</button></div>}</div></div>
}
function EditVertices({ring,updateVertex}){return <>{ring.map((p,i)=><Marker key={i} position={pixelToLatLng(p)} draggable eventHandlers={{dragend:e=>updateVertex(i,e.target.getLatLng())}} icon={L.divIcon({className:'vertex-handle',html:'<span></span>',iconSize:[14,14],iconAnchor:[7,7]})}/>)}</>}
function ReviewPanel({feature,accept,setSelected,rejecting,setRejecting,reason,setReason,note,setNote,doReject,startEdit,saveEdit,editing,setEditing}){const p=feature.properties||{}, status=p.review_status||'pending';return <div className="feature-details"><div className="review-title"><div><span className="eyebrow">FEATURE REVIEW</span><h3>Detected Feature #{p.feature_id??'—'}</h3></div><span className={`status ${status}`}>{STATUS[status]||status}</span></div><div className="prop"><span>Feature type</span><b>{p.class||'Detected feature'}</b></div><div className="prop"><span>Area</span><b>{p.area_m2==null?'—':`${Number(p.area_m2).toFixed(2)} m²`}</b></div><div className="prop"><span>Quality flag</span><b>{p.quality_flag||'—'}</b></div><div className="prop"><span>Review required</span><b>{p.review_required?'Yes':'No'}</b></div><div className="prop"><span>Confidence</span><b>{p.confidence==null?'Not available':p.confidence}</b></div>{p.rejection_reason&&<div className="prop"><span>Rejection reason</span><b>{p.rejection_reason}</b></div>}{p.boundary_edited&&<div className="edited-note">Boundary has been edited.</div>}<div className="review-question">Is this detection correct?</div><div className="review-actions"><button className="approve-btn" disabled={status==='approved'} onClick={()=>{accept(p.feature_id);setSelected({...feature,properties:{...p,review_status:'approved',review_required:false}})}}>✓ Accept</button><button className="reject-btn" disabled={status==='rejected'} onClick={()=>setRejecting(true)}>✕ Reject</button><button className="edit-btn" onClick={()=>startEdit(feature)}>{editing?'Editing…':'✎ Edit Boundary'}</button></div>{rejecting&&<div className="reject-box"><label>Rejection reason</label><select value={reason} onChange={e=>setReason(e.target.value)}><option value="">Select reason</option><option>Wrong boundary</option><option>False detection</option><option>Duplicate</option><option>Missing/incorrect feature</option><option>Other</option></select><label>Review notes</label><textarea value={note} onChange={e=>setNote(e.target.value)} placeholder="Add reviewer notes…"/><div className="inline-actions"><button className="small-btn" onClick={()=>setRejecting(false)}>Cancel</button><button className="reject-btn compact" onClick={doReject}>Confirm Reject</button></div></div>}{editing&&<button className="primary wide save-boundary" onClick={()=>saveEdit(p.feature_id)}>Save Boundary & Continue Review</button>}<div className="review-note"><b>Reviewer guidance</b><span>Accept only when the mapped boundary is suitable for the current QC workflow. Rejected items remain in the exported review history.</span></div></div>}

function Review({quality,selected,setSelected,setPage,accept,reject,startEdit,saveEdit,editing,draftGeometry,updateVertex,setEditing,setDraftGeometry}){const [filter,setFilter]=useState('all'),[query,setQuery]=useState('');const [reason,setReason]=useState(''),[note,setNote]=useState('');const [rejectingId,setRejectingId]=useState(null);const items=(quality?.features||[]).filter(f=>{const s=f.properties?.review_status||'pending';const q=query.toLowerCase();return (filter==='all'||s===filter)&&(String(f.properties?.feature_id||'').includes(q)||String(f.properties?.quality_flag||'').toLowerCase().includes(q));});const confirmReject=()=>{if(!rejectingId)return;reject(rejectingId,reason||'Other',note);setRejectingId(null);setReason('');setNote('');};return <div><div className="hero-row"><div><div className="eyebrow">HUMAN-IN-THE-LOOP</div><h2 className="hero-title">Review Queue</h2><p className="muted">Inspect, accept, reject, or edit the supplied QC features. Decisions are kept in the browser until exported.</p></div><button className="primary" onClick={()=>setPage('map')}>Open map →</button></div><div className="review-toolbar"><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search feature ID or quality flag…"/><div className="filter-pills">{['all','pending','approved','rejected'].map(s=><button key={s} className={filter===s?'filter active':'filter'} onClick={()=>setFilter(s)}>{s==='all'?'All':STATUS[s]} <span>{(quality?.features||[]).filter(f=>(f.properties?.review_status||'pending')===s).length}</span></button>)}</div></div><div className="table-card"><table><thead><tr><th>Feature</th><th>Area</th><th>Quality flag</th><th>Review</th><th>Status</th><th>Action</th></tr></thead><tbody>{items.map(f=>{const p=f.properties||{},s=p.review_status||'pending';return <React.Fragment key={p.feature_id}><tr className={selected?.properties?.feature_id===p.feature_id?'row-selected':''}><td><b>#{p.feature_id}</b></td><td>{Number(p.area_m2||0).toFixed(2)} m²</td><td><span className="badge warning">{p.quality_flag||'—'}</span></td><td>{p.review_required?'Required':'Complete'}</td><td><span className={`status ${s}`}>{STATUS[s]}</span></td><td><div className="row-actions"><button className="small-btn" onClick={()=>{setSelected(f);setPage('map')}}>Inspect</button>{s==='pending'&&<><button className="approve-mini" onClick={()=>accept(p.feature_id)}>Accept</button><button className="reject-mini" onClick={()=>setRejectingId(p.feature_id)}>Reject</button></>}</div></td></tr>{rejectingId===p.feature_id&&<tr><td colSpan="6"><div className="table-reject"><select value={reason} onChange={e=>setReason(e.target.value)}><option value="">Reason</option><option>Wrong boundary</option><option>False detection</option><option>Duplicate</option><option>Missing/incorrect feature</option><option>Other</option></select><input value={note} onChange={e=>setNote(e.target.value)} placeholder="Reviewer note"/><button className="small-btn" onClick={()=>setRejectingId(null)}>Cancel</button><button className="reject-mini" onClick={confirmReject}>Confirm</button></div></td></tr>}</React.Fragment>})}</tbody></table></div></div>}

function Analytics({stats,quality}){const items=quality?.features||[],flags={};items.forEach(f=>{const k=f.properties?.quality_flag||'none';flags[k]=(flags[k]||0)+1});return <><div className="hero-row"><div><div className="eyebrow">DATA QUALITY</div><h2 className="hero-title">Analytics</h2><p className="muted">Metrics recalculate as reviewers accept or reject features.</p></div></div><div className="stat-grid"><Stat label="Features" value={stats.total} note="QC GeoJSON"/><Stat label="Pending" value={stats.pending} note="awaiting review"/><Stat label="Approved" value={stats.approved} note="accepted by reviewer"/><Stat label="Rejected" value={stats.rejected} note="rejected by reviewer"/></div><div className="card"><CardHead title="Quality flags"/><div className="flag-grid">{Object.entries(flags).map(([k,v])=><div className="flag" key={k}><b>{k}</b><strong>{v}</strong><span>{((v/stats.total)*100).toFixed(1)}%</span></div>)}</div></div></>}
function Surveys({stats,setPage}){return <><div className="hero-row"><div><div className="eyebrow">SURVEY WORKSPACE</div><h2 className="hero-title">AOI-0015</h2><p className="muted">BTM Layout dataset supplied for CADASTRA AI frontend integration.</p></div><button className="primary" onClick={()=>setPage('map')}>View survey map →</button></div><div className="card survey-card"><div><span className="badge success">READY</span><h3>BTM Layout 0015</h3><p className="muted">Georeferenced orthomosaic + AI/GIS vector outputs</p></div><div className="survey-meta"><span><b>{stats.total}</b> QC features</span><span><b>{stats.detected}</b> AI regions</span><span><b>512×512</b> source raster</span></div></div></>}
function DataPage(){const files=[['btm_layout_0015_georeferenced.tif','Georeferenced raster','EPSG:3857 · 512×512 · 4 bands'],['btm_layout_0015_polygons.geojson','Source polygons','30 polygon features'],['cadastraai_gis_quality_controlled.geojson','GIS QC output','30 features · quality flags'],['cadastraai_detected_regions.geojson','AI segmentation output','25 pixel-space regions'],['cadastraai_gis_frontend_handoff.txt','GIS handoff notes','Coordinate-system integration notes']];return <><div className="hero-row"><div><div className="eyebrow">SOURCE ASSETS</div><h2 className="hero-title">Data Management</h2><p className="muted">These are the actual files supplied for this demo.</p></div></div><div className="file-grid">{files.map(([name,type,meta])=><div className="card file-card" key={name}><div className="file-icon">{name.endsWith('.tif')?'IMG':name.endsWith('.txt')?'TXT':'GIS'}</div><div><b>{name}</b><span>{type}</span><small>{meta}</small></div></div>)}</div></>}
function Export({quality,exportData}){const pending=quality?.features?.filter(f=>(f.properties?.review_status||'pending')==='pending').length||0;return <div className="export-card"><div className="eyebrow">DATA DELIVERY</div><h2 className="hero-title">Export reviewed GIS output</h2><p className="muted">Download the current QC GeoJSON with reviewer decisions, rejection reasons, notes, and edited boundaries.</p><button className="primary" onClick={exportData}>Download Reviewed QC GeoJSON ↓</button><div className="notice"><b>Source:</b> cadastraai_gis_quality_controlled.geojson<br/><b>Features:</b> {quality?.features?.length||0}<br/><b>Pending:</b> {pending}<br/><b>Format:</b> GeoJSON with current client-side review state</div></div>}
function Placeholder({title}){return <div className="placeholder card"><div className="eyebrow">CADASTRA AI</div><h2>{title}</h2><p className="muted">Workspace section ready for the next demo increment.</p></div>}
export default App;
