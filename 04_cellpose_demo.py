# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 5 Demo: Cellpose Segmentation

Segments nuclei (DNA channel) from 8-channel Cell Painting TIFFs with Cellpose
(cyto2 model) and renders a 2x2 montage with cell outlines.

Input  : data/raw/BR00116991 (8-channel tiff, ch1 = DNA)
Output : reports/figures/05_cellpose_segmentation.png
         reports/05_cellpose_summary.csv

Optional dependency: cellpose + torch (see README).
"""
import os

import numpy as np
import pandas as pd
import tifffile
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cellpose import models

# ---------- Configuration ----------
SITES = ["r01c01f01p01", "r01c05f01p01", "r01c10f01p01", "r01c20f01p01"]
DIAMETER = 40
FLOW_THRESHOLD = 0.4
CELLPOSE_MODEL = "cyto2"
CELLPOSE_GPU = True
DPI = 150

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "BR00116991")
FIG = os.path.join(BASE, "reports", "figures")
os.makedirs(FIG, exist_ok=True)

# Pick 4 different wells (different treatments) using the DNA channel
paths = {s: os.path.join(RAW, f"{s}-ch1sk1fk1fl1.tiff") for s in SITES}
existing = {s: p for s, p in paths.items() if os.path.exists(p)}
if len(existing) < 4:
    # Fall back to other wells if the preferred ones are missing
    all_files = sorted(f for f in os.listdir(RAW) if f.endswith("-ch1sk1fk1fl1.tiff"))
    for s in SITES:
        if s not in existing and all_files:
            existing[s] = os.path.join(RAW, all_files[len(existing)])
    print(f"Actually used sites: {list(existing.keys())}")

model = models.Cellpose(gpu=CELLPOSE_GPU, model_type=CELLPOSE_MODEL)

fig, axes = plt.subplots(2, 2, figsize=(14, 14))
summary = []
for ax, (site, p) in zip(axes.ravel(), existing.items()):
    img = tifffile.imread(p).astype(np.float32)
    img = (img - img.min()) / (img.max() - img.min() + 1e-8)
    masks, flows, styles, diams = model.eval(
        img, diameter=DIAMETER, channels=[0, 0], flow_threshold=FLOW_THRESHOLD
    )
    n_cells = int(masks.max())
    summary.append({"site": site, "n_cells": n_cells, "diameter": float(diams[0])})
    ax.imshow(img, cmap="gray")
    ax.contour(masks, levels=0.5, colors="lime", linewidths=0.6)
    ax.set_title(f"{site}: {n_cells} cells")
    ax.axis("off")

plt.suptitle("Cellpose (cyto2) segmentation demo - JUMP Cell Painting DNA channel", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "05_cellpose_segmentation.png"), dpi=DPI)
plt.close()

summary_df = pd.DataFrame(summary)
summary_df.to_csv(os.path.join(BASE, "reports", "05_cellpose_summary.csv"), index=False)
print(summary_df.to_string(index=False))
print("Saved: reports/figures/05_cellpose_segmentation.png")
