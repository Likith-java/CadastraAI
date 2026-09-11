import pathlib, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Frontend\src\App.jsx")
text = path.read_text(encoding="utf-8")

old = '{showGeoRef&&<>><input placeholder="North"'
new = '{showGeoRef&&<><input placeholder="North"'

count = text.count(old)
if count != 1:
    print(f"[FAIL] expected 1 match, found {count}")
    sys.exit(1)
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("App.jsx typo fixed successfully.")
