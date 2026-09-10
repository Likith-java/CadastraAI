import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Frontend\src\App.jsx")
text = path.read_text(encoding="utf-8")

old = "<div className=\"map-tools\" style={{marginTop:6}}><label className=\"primary\" style={{cursor:'pointer',padding:'6px 12px',borderRadius:6,display:'inline-block'}}>\u21ea Upload new image (live inference)<input type=\"file\" accept=\"image/*,.tif,.tiff\" style={{display:'none'}} onChange={e=>{const f=e.target.files&&e.target.files[0];if(f)uploadAndInfer(f);e.target.value='';}}/></label>{uploadStatus&&<span style={{marginLeft:10,fontSize:13}}>{uploadStatus}</span>}</div>"
new = "<div className=\"upload-tools\"><label className=\"primary\" style={{cursor:'pointer',padding:'6px 12px',borderRadius:6,display:'inline-block'}}>\u21ea Upload new image (live inference)<input type=\"file\" accept=\"image/*,.tif,.tiff\" style={{display:'none'}} onChange={e=>{const f=e.target.files&&e.target.files[0];if(f)uploadAndInfer(f);e.target.value='';}}/></label>{uploadStatus&&<span style={{fontSize:9}}>{uploadStatus}</span>}</div>"

count = text.count(old)
if count != 1:
    print(f"[FAIL] expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("App.jsx patched successfully.")
