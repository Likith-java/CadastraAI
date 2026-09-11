import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Frontend\src\App.jsx")
text = path.read_text(encoding="utf-8")

# 1. Update uploadAndInfer to accept optional bounds and send them as form fields
old_fn = """  const uploadAndInfer = async (file) => {
    setUploadStatus('Uploading image\u2026');
    try {
      const form = new FormData();
      form.append('file', file);
      const meta = await fetch(`${API_BASE}/aoi/upload`, { method: 'POST', body: form }).then(r => r.json());"""

new_fn = """  const uploadAndInfer = async (file, bounds) => {
    setUploadStatus('Uploading image\u2026');
    try {
      const form = new FormData();
      form.append('file', file);
      if (bounds && bounds.north !== '' && bounds.south !== '' && bounds.east !== '' && bounds.west !== '') {
        form.append('north', bounds.north);
        form.append('south', bounds.south);
        form.append('east', bounds.east);
        form.append('west', bounds.west);
      }
      const meta = await fetch(`${API_BASE}/aoi/upload`, { method: 'POST', body: form }).then(r => r.json());"""

count = text.count(old_fn)
if count != 1:
    print(f"[FAIL] uploadAndInfer: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_fn, new_fn)

# 2. Add local state for the manual-bounds toggle + values inside GISMap
old_state = "  const [showQC,setShowQC]=useState(true),[showAI,setShowAI]=useState(true),[showSource,setShowSource]=useState(true);"
new_state = """  const [showQC,setShowQC]=useState(true),[showAI,setShowAI]=useState(true),[showSource,setShowSource]=useState(true);
  const [showGeoRef,setShowGeoRef]=useState(false);
  const [manualBounds,setManualBounds]=useState({north:'',south:'',east:'',west:''});"""

count = text.count(old_state)
if count != 1:
    print(f"[FAIL] state block: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_state, new_state)

# 3. Extend the upload-tools UI with a checkbox + 4 bounds inputs, pass bounds through
old_upload_div = """<div className=\"upload-tools\"><label className=\"primary\" style={{cursor:'pointer',padding:'6px 12px',borderRadius:6,display:'inline-block'}}>\u21ea Upload new image (live inference)<input type=\"file\" accept=\"image/*,.tif,.tiff\" style={{display:'none'}} onChange={e=>{const f=e.target.files&&e.target.files[0];if(f)uploadAndInfer(f);e.target.value='';}}/></label>{uploadStatus&&<span style={{fontSize:9}}>{uploadStatus}</span>}</div>"""

new_upload_div = """<div className=\"upload-tools\"><label className=\"primary\" style={{cursor:'pointer',padding:'6px 12px',borderRadius:6,display:'inline-block'}}>\u21ea Upload new image (live inference)<input type=\"file\" accept=\"image/*,.tif,.tiff\" style={{display:'none'}} onChange={e=>{const f=e.target.files&&e.target.files[0];if(f)uploadAndInfer(f, showGeoRef?manualBounds:null);e.target.value='';}}/></label><label style={{fontSize:9,display:'flex',alignItems:'center',gap:4,whiteSpace:'nowrap'}}><input type=\"checkbox\" checked={showGeoRef} onChange={e=>setShowGeoRef(e.target.checked)}/> Manual bounds</label>{showGeoRef&&<>><input placeholder=\"North\" value={manualBounds.north} onChange={e=>setManualBounds({...manualBounds,north:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/><input placeholder=\"South\" value={manualBounds.south} onChange={e=>setManualBounds({...manualBounds,south:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/><input placeholder=\"East\" value={manualBounds.east} onChange={e=>setManualBounds({...manualBounds,east:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/><input placeholder=\"West\" value={manualBounds.west} onChange={e=>setManualBounds({...manualBounds,west:e.target.value})} style={{width:58,fontSize:9,padding:'3px 5px'}}/></>}{uploadStatus&&<span style={{fontSize:9}}>{uploadStatus}</span>}</div>"""

count = text.count(old_upload_div)
if count != 1:
    print(f"[FAIL] upload-tools div: expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old_upload_div, new_upload_div)

path.write_text(text, encoding="utf-8")
print("App.jsx patched successfully.")
