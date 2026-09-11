import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Backend\main.py")
text = path.read_text(encoding="utf-8")

old = '''@app.post("/aoi/upload")
async def upload_aoi(
    file: UploadFile = File(...),
    north: float | None = None,
    south: float | None = None,
    east: float | None = None,
    west: float | None = None,
):'''

new = '''@app.post("/aoi/upload")
async def upload_aoi(
    file: UploadFile = File(...),
    north: float | None = Form(None),
    south: float | None = Form(None),
    east: float | None = Form(None),
    west: float | None = Form(None),
):'''

count = text.count(old)
if count != 1:
    print(f"[FAIL] expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old, new)

if "Form" not in text.split("\n")[7]:  # quick check import line exists somewhere
    pass

old_import = "from fastapi import FastAPI, UploadFile, File, HTTPException"
new_import = "from fastapi import FastAPI, UploadFile, File, HTTPException, Form"
count_imp = text.count(old_import)
if count_imp != 1:
    print(f"[FAIL] import: expected 1 match, found {count_imp}")
    sys.exit(1)
text = text.replace(old_import, new_import)

path.write_text(text, encoding="utf-8")
print("main.py patched successfully.")
