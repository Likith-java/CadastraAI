import pathlib, re, sys

path = pathlib.Path(r"C:\Users\navaneeth\CadastraAI\Frontend\src\styles.css")
text = path.read_text(encoding="utf-8")

# Main rule: find .upload-tools{position:absolute...} regardless of current values
main_pattern = re.compile(r"\.upload-tools\{position:absolute;[^}]*\}")
main_matches = main_pattern.findall(text)
if len(main_matches) != 1:
    print(f"[FAIL] main rule: expected 1 match, found {len(main_matches)}")
    sys.exit(1)

new_main = ".upload-tools{position:absolute;z-index:600;top:14px;left:50%;transform:translateX(-50%);background:#fff;border:1px solid #dce3eb;border-radius:8px;padding:9px 11px;display:flex;align-items:center;gap:9px;box-shadow:0 2px 10px #0002;font-size:9px}"
text = main_pattern.sub(new_main, text)
print("[OK] main .upload-tools rule centered")

# Mobile media-query rule: .upload-tools{left:8px;top:8px} -> also center
mobile_pattern = re.compile(r"\.upload-tools\{left:8px;top:8px\}")
mobile_matches = mobile_pattern.findall(text)
if len(mobile_matches) == 1:
    text = mobile_pattern.sub(".upload-tools{left:50%;top:8px;transform:translateX(-50%)}", text)
    print("[OK] mobile .upload-tools rule centered")
else:
    print(f"[WARN] mobile rule: expected 1 match, found {len(mobile_matches)} (skipped)")

path.write_text(text, encoding="utf-8")
print("styles.css patched successfully.")
