import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Frontend\src\styles.css")
text = path.read_text(encoding="utf-8")

patches = [
    (
        ".dark .map-tools,.dark .review-toolbar input,.dark .filter,.dark .reject-box select,.dark .reject-box textarea,.dark .table-reject input,.dark .table-reject select{background:#18232e;color:#e5edf5;border-color:#344555}",
        ".upload-tools{position:absolute;z-index:600;top:14px;left:14px;background:#fff;border:1px solid #dce3eb;border-radius:8px;padding:9px 11px;display:flex;align-items:center;gap:9px;box-shadow:0 2px 10px #0002;font-size:9px}.dark .map-tools,.dark .upload-tools,.dark .review-toolbar input,.dark .filter,.dark .reject-box select,.dark .reject-box textarea,.dark .table-reject input,.dark .table-reject select{background:#18232e;color:#e5edf5;border-color:#344555}",
    ),
    (
        "@media(max-width:900px){.review-toolbar{flex-direction:column}.review-toolbar input{max-width:none}.table-reject{grid-template-columns:1fr}.map-tools{right:8px;top:8px}.map-legend{left:8px;right:8px;bottom:8px}}",
        "@media(max-width:900px){.review-toolbar{flex-direction:column}.review-toolbar input{max-width:none}.table-reject{grid-template-columns:1fr}.map-tools{right:8px;top:8px}.upload-tools{left:8px;top:8px}.map-legend{left:8px;right:8px;bottom:8px}}",
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
print("styles.css patched successfully.")
