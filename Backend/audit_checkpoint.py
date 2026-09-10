import torch

ckpt_path = "models/best_epoch12_val4.4813.pth"
sd = torch.load(ckpt_path, map_location="cpu")

print(f"Total keys: {len(sd)}\n")

heads = {"mask_head": [], "edge_head": [], "frame_field_head": [], "encoder": [], "decoder": [], "other": []}
for k, v in sd.items():
    matched = False
    for prefix in ["mask_head", "edge_head", "frame_field_head", "encoder", "decoder"]:
        if k.startswith(prefix):
            heads[prefix].append((k, tuple(v.shape)))
            matched = True
            break
    if not matched:
        heads["other"].append((k, tuple(v.shape)))

for group, items in heads.items():
    print(f"--- {group} ({len(items)} tensors) ---")
    for k, shape in items[:5]:
        print(f"  {k}: {shape}")
    if len(items) > 5:
        print(f"  ... and {len(items)-5} more")
    print()

has_frame_field = len(heads["frame_field_head"]) > 0
has_edge = len(heads["edge_head"]) > 0
print(f"Has frame_field_head: {has_frame_field}")
print(f"Has edge_head: {has_edge}")
