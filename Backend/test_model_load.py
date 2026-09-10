import torch
from model import load_model

device = "cpu"
model = load_model("models/best_epoch12_val4.4813.pth", device=device)
print("Checkpoint loaded and state_dict matched exactly.\n")

dummy = torch.randn(1, 3, 512, 512)
with torch.no_grad():
    out = model(dummy)

print("Forward pass output shapes:")
for k, v in out.items():
    print(f"  {k}: {tuple(v.shape)}")
