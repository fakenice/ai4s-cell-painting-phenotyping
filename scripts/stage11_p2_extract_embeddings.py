# -*- coding: utf-8 -*-
"""Stage 11 P2-A: extract ResNet18 512-d embeddings for BR00116992 wells and merge with BR00116991."""
import os, json
import numpy as np
import torch
import torch.nn as nn
import tifffile
from torchvision import transforms
from torchvision.models import resnet18, ResNet18_Weights

BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
RAW92 = os.path.join(BASE, "data", "raw", "BR00116992")
RAW91 = os.path.join(BASE, "data", "raw", "BR00116991")
RAW91D = os.path.join(BASE, "data", "raw", "BR00116991_dmso")
REPORTS = os.path.join(BASE, "github_repo", "reports")
OUT_NPZ = os.path.join(REPORTS, "19_stage11_p2_embeddings.npz")

SITE_WELL = {"r01c01": "A01", "r01c03": "A03", "r01c04": "A04",
             "r01c02": "A02", "r01c09": "A09", "r01c17": "A17"}

def well_to_site(w):
    return f"r{ord(w[0])-ord('A')+1:02d}c{int(w[1:]):02d}"

def extract_for_dir(d, plate):
    sites = sorted({os.path.basename(p).split("-")[0] for p in __import__("glob").glob(os.path.join(d, "*.tiff"))})
    emb = {}
    for site in sites:
        chans = []
        for c in range(1, 9):
            p = os.path.join(d, f"{site}-ch{c}sk1fk1fl1.tiff")
            if not os.path.exists(p):
                raise FileNotFoundError(f"missing channel {c} for {site} in {d}")
            chans.append(tifffile.imread(p).astype(np.float32) / 65535.0)
        rgb = np.stack([chans[0], chans[3], chans[1]], axis=-1)
        emb[f"deep_resnet18_512|{plate}|{site}"] = rgb
    return emb

dev = "cuda" if torch.cuda.is_available() else "cpu"
tf = transforms.Compose([
    transforms.ToPILImage(), transforms.Resize(224), transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
rn = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1).eval().to(dev)
rn = nn.Sequential(*list(rn.children())[:-1])

# build all rgb composites
rgb_all = {}
for d, plate in ((RAW91, "BR00116991"), (RAW91D, "BR00116991"), (RAW92, "BR00116992")):
    for k, rgb in extract_for_dir(d, plate).items():
        rgb_all[k] = rgb

emb_site = {}
with torch.no_grad():
    for k, rgb in sorted(rgb_all.items()):
        img = tf((rgb * 255.0).astype(np.uint8)).unsqueeze(0).to(dev)
        emb_site[k] = rn(img).flatten(1).cpu().numpy()[0]

print("total sites:", len(emb_site))
plates = sorted(set(k.split("|")[1] for k in emb_site))
print("plates:", plates)
for p in plates:
    ks = [k for k in emb_site if k.split("|")[1] == p]
    print(p, len(ks), "sites")

ok = {"deep_resnet18_512": True}
np.savez(OUT_NPZ, emb_site=emb_site, ok=ok)
print("saved:", OUT_NPZ)
