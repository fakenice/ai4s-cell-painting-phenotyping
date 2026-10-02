# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 7+8: Deep Representation Learning & Transfer Learning

Stage 8 (this run)  -  DMSO control images downloaded + deep representation completed
  Part 0  Image download (JUMP-CP official AWS S3 registry, no-sign URL)
      - Registry: https://registry.opendata.aws/jump-cell-painting/
      - Image URL pattern:
        https://s3.amazonaws.com/images.cellprofiler.org/jump-cp/pilot/source_4/BR00116991/BR00116991__2020-03-05T20_31_41-Measurement1/Images/r01c01f01p01-ch1sk1fk1fl1.tiff
      (sample-set plate BR00116991; treated wells A01/A03/A04; DMSO wells A02/A09/A17)
      - Downloaded 96 TIFFs (8 channels x 12 sites): 6 treated sites (A01 x3, A03 x2, A04 x1)
        + 6 DMSO sites (A02 x2, A09 x2, A17 x2), each site 1080x1080 uint16, into
        data/raw/BR00116991 (treated) and data/raw/BR00116991_dmso (DMSO).
  Part 1  Asset inventory (honest data-gate) - updated for trt + DMSO images
  Part 2  Deep-model baseline on handcrafted morphology features (small MLP, same as Stage 7)
  Part 3  Deep embedding comparison (ResNet18 ImageNet pretrained)
      - 512-d embeddings from 3-channel RGB composites (ch1/ch4/ch2) per site
      - Well-level aggregation (mean over sites) for matched-protocol comparison
      - Logistic regression (C=1.0, standardized): handcrafted-904 vs deep-512 vs concat-1416
      - Well-grouped Leave-One-Out CV -> AUC / AP / ACC; figure 24
  Part 4  Self-trained single-cell CNN (leakage-free)
      - Cellpose cpsam_v2 (float32) segmentation of trt + DMSO sites -> single-cell crops
      - Small CNN (3 conv blocks + FC) binary classifier trt vs DMSO
      - Grouped CV by well (DMSO wells included in every test fold across folds), epochs 10-30
      - Reports test AUC / ACC / AP, training curves (fig 25) + confusion matrix (fig 26)

Output : reports/figures/24_embedding_comparison.png
         reports/figures/25_cnn_training_curves.png
         reports/figures/26_cnn_confusion.png
         reports/17_deep_representation_results.csv  (final, Stage 8)
         reports/17_stage8_summary.json
"""
import os
import glob
import time
import json
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import StratifiedKFold, GroupKFold, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    confusion_matrix,
)

import torch
import torch.nn as nn

# ---------- Configuration ----------
RANDOM_STATE = 42
N_SPLITS = 5
EPOCHS = 20
BATCH_SIZE = 128
LR = 1e-3
WEIGHT_DECAY = 1e-4
MLP_HIDDEN = [256, 64]
DROPOUT = 0.3
DPI = 150

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
RAW_TRT = os.path.join(DATA, "raw", "BR00116991")
RAW_DMSO = os.path.join(DATA, "raw", "BR00116991_dmso")
INTERIM = os.path.join(DATA, "interim", "cellpose_crops")
PROFILES_DIR = os.path.join(DATA, "profiles")
FIG = os.path.join(BASE, "reports", "figures")
os.makedirs(FIG, exist_ok=True)

FEATURE_PREFIXES = ("Cells_", "Cytoplasm_", "Nuclei_")

SITE_WELL = {
    "r01c01": "A01", "r01c03": "A03", "r01c04": "A04",
    "r01c02": "A02", "r01c09": "A09", "r01c17": "A17",
}
SITE_LABEL = {"r01c01": 1, "r01c03": 1, "r01c04": 1, "r01c02": 0, "r01c09": 0, "r01c17": 0}
WELL_ORDER = ["A01", "A02", "A03", "A04", "A09", "A17"]
WELL_LABEL = {"A01": 1, "A02": 0, "A03": 1, "A04": 1, "A09": 0, "A17": 0}


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)


# ---------- Part 1: asset inventory ----------


def load_profiles():
    plate_files = sorted(f for f in os.listdir(PROFILES_DIR) if f.endswith(".csv.gz"))
    frames = [pd.read_csv(os.path.join(PROFILES_DIR, f)) for f in plate_files]
    return pd.concat(frames, ignore_index=True)


def scan_assets():
    rows = []

    def add(step, key, value, note):
        rows.append((step, key, value, note))

    tiffs_trt = sorted(glob.glob(os.path.join(RAW_TRT, "*.tiff")))
    tiffs_dmso = sorted(glob.glob(os.path.join(RAW_DMSO, "*.tiff")))
    sites_trt = sorted({os.path.basename(p).split("-")[0] for p in tiffs_trt})
    sites_dmso = sorted({os.path.basename(p).split("-")[0] for p in tiffs_dmso})
    add(
        "asset_images",
        "n_tiff_trt_dmso",
        f"{len(tiffs_trt)}/{len(tiffs_dmso)}",
        f"treated dir data/raw/BR00116991 sites {sites_trt}; DMSO dir data/raw/BR00116991_dmso sites {sites_dmso} (1080x1080 uint16, 8 channels/site)",
    )
    embeds = []
    for root, _dirs, files in os.walk(DATA):
        for f in files:
            if f.lower().endswith((".npy", ".npz", ".parquet", ".h5", ".hdf5", ".pt", ".pth")):
                embeds.append(os.path.join(root, f))
    add(
        "asset_embeddings",
        "official_jumpcp_embeddings",
        "FOUND" if embeds else "NONE",
        "; ".join(embeds) if embeds else "no official embedding files under data/; embeddings computed in-house via ResNet18",
    )
    crop_dirs = [INTERIM] if os.path.isdir(os.path.join(INTERIM, "crops")) else []
    n_crops = 0
    if crop_dirs:
        crop_root = os.path.join(INTERIM, "crops")
        n_crops = len(glob.glob(os.path.join(crop_root, "*", "*.npy")))
    add(
        "asset_cellpose",
        "single_cell_crops",
        f"FOUND {n_crops}" if n_crops else "NONE",
        "; ".join(crop_dirs) if crop_dirs else "no crop directory -> CNN not executable",
    )
    prof = load_profiles()
    compound_wells = prof.dropna(subset=["Metadata_pert_iname"])
    trt = compound_wells[compound_wells["Metadata_pert_type"] == "trt"]
    dmso = compound_wells[compound_wells["Metadata_pert_iname"] == "DMSO"]
    add(
        "asset_labels",
        "well_counts_trt_dmso",
        f"{len(trt)}/{len(dmso)}",
        "648-well treated-vs-DMSO matrix (520 trt / 128 DMSO) for handcrafted-feature classifier",
    )
    img_wells_trt = sorted({SITE_WELL[s[:6]] for s in sites_trt})
    img_wells_dmso = sorted({SITE_WELL[s[:6]] for s in sites_dmso})
    add(
        "asset_labels",
        "image_well_coverage",
        f"trt {img_wells_trt} / dmso {img_wells_dmso}",
        "same plate BR00116991, same source_4; trt wells A01/A03/A04, DMSO wells A02/A09/A17 (matched plate -> reduced batch effect)",
    )
    return rows, prof


# ---------- Part 2: MLP baseline (reuse Stage 7) ----------


def split_xy(prof, task="trt_vs_dmso"):
    feat_cols = [c for c in prof.columns if c.startswith(FEATURE_PREFIXES)]
    assert len(feat_cols) == 904, f"expected 904 morphology features, got {len(feat_cols)}"
    sub = prof.dropna(subset=["Metadata_pert_iname"]).copy()
    mask = (sub["Metadata_pert_type"] == "trt") | (sub["Metadata_pert_iname"] == "DMSO")
    sub = sub[mask].copy()
    y = (sub["Metadata_pert_type"] == "trt").astype(int).values
    X = sub[feat_cols].values.astype(np.float32)
    return X, y, sub


def make_mlp(n_in=904):
    layers = []
    prev = n_in
    for h in MLP_HIDDEN:
        layers.append(nn.Linear(prev, h))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(DROPOUT))
        prev = h
    layers.append(nn.Linear(prev, 1))
    return nn.Sequential(*layers)


def train_epoch(model, Xtr, ytr, Xva, yva, opt, crit):
    model.train()
    n = Xtr.shape[0]
    perm = torch.randperm(n)
    train_loss_sum, n_batches = 0.0, 0
    for i in range(0, n, BATCH_SIZE):
        idx = perm[i : i + BATCH_SIZE]
        xb, yb = Xtr[idx], ytr[idx]
        opt.zero_grad()
        out = model(xb).squeeze(1)
        loss = crit(out, yb)
        loss.backward()
        opt.step()
        train_loss_sum += loss.item()
        n_batches += 1
    model.eval()
    with torch.no_grad():
        vout = model(Xva).squeeze(1)
        vloss = crit(vout, yva).item()
        vauc = roc_auc_score(yva.numpy(), torch.sigmoid(vout).numpy())
    return train_loss_sum / n_batches, vloss, vauc


def run_mlp_cv(X, y, name="mlp_5fold_trt_vs_dmso"):
    set_seed(RANDOM_STATE)
    n = len(y)
    y_prob = np.zeros(n)
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    for fold, (tr, va) in enumerate(cv.split(X, y)):
        set_seed(RANDOM_STATE + fold)
        scaler = StandardScaler().fit(X[tr])
        Xtr = torch.tensor(scaler.transform(X[tr]), dtype=torch.float32)
        Xva = torch.tensor(scaler.transform(X[va]), dtype=torch.float32)
        ytr = torch.tensor(y[tr], dtype=torch.float32)
        yva = torch.tensor(y[va], dtype=torch.float32)
        model = make_mlp(X.shape[1])
        opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        crit = nn.BCEWithLogitsLoss()
        for ep in range(EPOCHS):
            train_epoch(model, Xtr, ytr, Xva, yva, opt, crit)
        model.eval()
        with torch.no_grad():
            y_prob[va] = torch.sigmoid(model(Xva)).squeeze(1).numpy()
    return {
        "experiment": name,
        "n": n,
        "auc": float(roc_auc_score(y, y_prob)),
        "ap": float(average_precision_score(y, y_prob)),
        "acc": float(accuracy_score(y, (y_prob >= 0.5).astype(int))),
    }


# ---------- Part 3: deep embedding comparison ----------


def collect_sites():
    sites = {}
    for d in (RAW_TRT, RAW_DMSO):
        for p in glob.glob(os.path.join(d, "*-ch1sk1fk1fl1.tiff")):
            base = os.path.basename(p)
            site = base.split("-")[0]
            channels = [glob.glob(os.path.join(d, f"{site}-ch{c}sk1fk1fl1.tiff"))[0] for c in range(1, 9)]
            sites[site] = {"dir": d, "label": SITE_LABEL[site[:6]], "well": SITE_WELL[site[:6]], "channels": channels}
    return sites


def extract_embeddings(sites):
    from torchvision import transforms
    from torchvision.models import resnet18, ResNet18_Weights
    import tifffile

    tf = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.eval()
    model = nn.Sequential(*list(model.children())[:-1])
    emb = {}
    t0 = time.time()
    with torch.no_grad():
        for site, info in sites.items():
            chans = [tifffile.imread(p).astype(np.float32) / 65535.0 for p in info["channels"]]
            rgb = np.stack([chans[0], chans[3], chans[1]], axis=-1)  # ch1/ch4/ch2 -> RGB
            rgb = np.clip(rgb, 0, 1)
            img = tf((rgb * 255.0).astype(np.uint8))
            emb[site] = model(img.unsqueeze(0)).flatten(1).numpy()[0]
    return emb, round(time.time() - t0, 1)


def evaluate_lr(X, y, groups, name, scale=True):
    y = np.asarray(y)
    groups = np.asarray(groups)
    logo = LeaveOneGroupOut()
    y_prob = np.zeros(len(y))
    for tr, te in logo.split(X, y, groups):
        clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
        if scale:
            sc = StandardScaler().fit(X[tr])
            Xtr, Xte = sc.transform(X[tr]), sc.transform(X[te])
        else:
            Xtr, Xte = X[tr], X[te]
        clf.fit(Xtr, y[tr])
        y_prob[te] = clf.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(y, y_prob) if np.unique(y).size == 2 else float("nan")
    return {
        "name": name,
        "n": len(y),
        "auc": float(auc),
        "ap": float(average_precision_score(y, y_prob)),
        "acc": float(accuracy_score(y, (y_prob >= 0.5).astype(int))),
    }


def embedding_comparison():
    sites = collect_sites()
    emb, secs = extract_embeddings(sites)
    hand, n_feat = load_handcrafted()
    site_order = sorted(sites)
    y_site = np.array([sites[s]["label"] for s in site_order])
    group_site = np.array([sites[s]["well"] for s in site_order])
    X_deep = np.vstack([emb[s] for s in site_order])

    # site-level deep embedding, GroupKFold by well (12 images)
    gkf = GroupKFold(n_splits=3)
    y_prob = np.zeros(len(site_order))
    for tr, te in gkf.split(X_deep, y_site, group_site):
        clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
        sc = StandardScaler().fit(X_deep[tr])
        clf.fit(sc.transform(X_deep[tr]), y_site[tr])
        y_prob[te] = clf.predict_proba(sc.transform(X_deep[te]))[:, 1]
    res_site = {
        "name": "deep_resnet18_512_site12_groupkfold",
        "n": len(y_site),
        "auc": float(roc_auc_score(y_site, y_prob)),
        "ap": float(average_precision_score(y_site, y_prob)),
        "acc": float(accuracy_score(y_site, (y_prob >= 0.5).astype(int))),
    }

    # well-level aggregation (matched protocol with 904 features)
    X_deep_well = np.vstack([
        np.mean([emb[s] for s in site_order if sites[s]["well"] == w], axis=0) for w in WELL_ORDER
    ])
    X_hand_well = np.vstack([hand[w] for w in WELL_ORDER])
    X_cat_well = np.hstack([X_hand_well, X_deep_well])
    y_well = np.array([WELL_LABEL[w] for w in WELL_ORDER])

    results = [res_site]
    results.append(evaluate_lr(X_hand_well, y_well, WELL_ORDER, "handcrafted_904_well6"))
    results.append(evaluate_lr(X_deep_well, y_well, WELL_ORDER, "deep_resnet18_512_well6"))
    results.append(evaluate_lr(X_cat_well, y_well, WELL_ORDER, "concat_1416_well6"))
    return results, secs


def load_handcrafted():
    df = pd.read_csv(os.path.join(PROFILES_DIR, "BR00116991_normalized_feature_select_negcon_batch.csv.gz"))
    feat = [c for c in df.columns if c.startswith(FEATURE_PREFIXES)]
    sub = df[df["Metadata_Well"].isin(WELL_ORDER)]
    well_map = dict(zip(sub["Metadata_Well"], sub[feat].values.astype(np.float32)))
    return well_map, len(feat)


# ---------- Part 4: self-trained single-cell CNN ----------


def make_cnn():
    """Small 3-block CNN for 64x64 single-cell crops (single channel -> 1 input)."""
    return nn.Sequential(
        nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Linear(64, 64), nn.ReLU(), nn.Dropout(0.3),
        nn.Linear(64, 1),
    )


def load_crops():
    """Load all single-cell crops; returns X (N,64,64), y, groups (well), meta."""
    crop_root = os.path.join(INTERIM, "crops")
    X, y, groups, meta = [], [], [], []
    for site_dir in sorted(glob.glob(os.path.join(crop_root, "*"))):
        if not os.path.isdir(site_dir):
            continue
        mj = os.path.join(site_dir, "meta.json")
        if not os.path.exists(mj):
            continue
        info = json.load(open(mj, encoding="utf-8"))
        well = info["well_name"]
        lbl = info["label"]
        for f in sorted(glob.glob(os.path.join(site_dir, "*_cell*.npy"))):
            X.append(np.load(f))
            y.append(lbl)
            groups.append(well)
            meta.append({"site": info["site"], "well": well})
    X = np.stack(X).astype(np.float32)[:, None, :, :]
    return X, np.array(y), np.array(groups), meta


def train_cnn_cv(X, y, groups, epochs=20):
    """Grouped CV by well. Reports OOF test metrics + per-fold history."""
    set_seed(RANDOM_STATE)
    n = X.shape[0]
    y_prob = np.zeros(n)
    history = {"train_loss": [], "val_loss": [], "val_auc": []}
    # GroupKFold with 4 splits; wells: A01,A02,A03,A04,A09,A17 -> each fold holds out 1-2 wells
    gkf = GroupKFold(n_splits=4)
    for fold, (tr, va) in enumerate(gkf.split(X, y, groups)):
        set_seed(RANDOM_STATE + fold)
        Xtr = torch.tensor(X[tr])
        Xva = torch.tensor(X[va])
        ytr = torch.tensor(y[tr], dtype=torch.float32)
        yva = torch.tensor(y[va], dtype=torch.float32)
        model = make_cnn()
        opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        crit = nn.BCEWithLogitsLoss()
        for ep in range(epochs):
            model.train()
            n_batches = 0
            perm = torch.randperm(len(Xtr))
            tl_sum = 0.0
            for i in range(0, len(Xtr), BATCH_SIZE):
                idx = perm[i : i + BATCH_SIZE]
                opt.zero_grad()
                out = model(Xtr[idx]).squeeze(1)
                loss = crit(out, ytr[idx])
                loss.backward()
                opt.step()
                tl_sum += loss.item()
                n_batches += 1
            model.eval()
            with torch.no_grad():
                vout = model(Xva).squeeze(1)
                vloss = crit(vout, yva).item()
                vauc = roc_auc_score(yva.numpy(), torch.sigmoid(vout).numpy())
            history["train_loss"].append(tl_sum / max(n_batches, 1))
            history["val_loss"].append(vloss)
            history["val_auc"].append(vauc)
        model.eval()
        with torch.no_grad():
            y_prob[va] = torch.sigmoid(model(Xva)).squeeze(1).numpy()
    return {
        "n": n,
        "auc": float(roc_auc_score(y, y_prob)),
        "ap": float(average_precision_score(y, y_prob)),
        "acc": float(accuracy_score(y, (y_prob >= 0.5).astype(int))),
        "y_true": y.tolist(),
        "y_prob": y_prob.tolist(),
        "history": history,
    }


# ---------- figures ----------


def plot_embedding_comparison(results, path):
    names = []
    aucs = []
    aps = []
    for r in results:
        names.append(r["name"])
        aucs.append(r["auc"])
        aps.append(r["ap"])
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.bar(x - 0.19, aucs, width=0.38, label="ROC AUC", color="#1f77b4")
    ax.bar(x + 0.19, aps, width=0.38, label="Average Precision", color="#2ca02c")
    ax.axhline(0.5, ls="--", color="#7f7f7f", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=12, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Embedding comparison: handcrafted-904 vs ResNet18-512 vs concat (well-level LOO, LR)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_cnn_curves(history, epochs, path):
    ep = np.arange(1, epochs + 1)
    tl = np.array(history["train_loss"]).reshape(-1, epochs).mean(0)
    vl = np.array(history["val_loss"]).reshape(-1, epochs).mean(0)
    va = np.array(history["val_auc"]).reshape(-1, epochs).mean(0)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].plot(ep, tl, label="train loss", color="#1f77b4")
    axes[0].plot(ep, vl, label="val loss", color="#d62728")
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("BCE loss")
    axes[0].set_title("Single-cell CNN training curves (well-grouped CV mean)")
    axes[0].legend()
    axes[1].plot(ep, va, marker="o", color="#2ca02c", label="val AUC")
    axes[1].axhline(0.5, ls="--", color="#7f7f7f")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("ROC AUC")
    axes[1].set_title("Validation AUC per epoch")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_cnn_confusion(y_true, y_prob, path):
    cm = confusion_matrix(y_true, (np.asarray(y_prob) >= 0.5).astype(int))
    acc = accuracy_score(y_true, (np.asarray(y_prob) >= 0.5).astype(int))
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Pred DMSO", "Pred treated"], yticklabels=["True DMSO", "True treated"], ax=ax)
    ax.set_title(f"Single-cell CNN OOF confusion matrix (ACC = {acc:.3f})")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------- main ----------


def main():
    result_rows = []
    print("=" * 70)
    print("Stage 7+8: Deep Representation Learning & Transfer Learning (with DMSO images)")
    print("=" * 70)

    inv, prof = scan_assets()
    for step, key, value, note in inv:
        result_rows.append({"step": step, "key": key, "value": value, "note": note})
        print(f"[{step}] {key} = {value} -- {note}")

    # Part 2: MLP baseline
    X, y, _ = split_xy(prof, "trt_vs_dmso")
    res_mlp = run_mlp_cv(X, y, "mlp_5fold_trt_vs_dmso")
    print(f"[mlp] trt-vs-DMSO 5-fold OOF AUC={res_mlp['auc']:.4f} AP={res_mlp['ap']:.4f} ACC={res_mlp['acc']:.4f}")
    result_rows.append({
        "step": "mlp",
        "key": "mlp_5fold_trt_vs_dmso_auc_ap_acc",
        "value": f"{res_mlp['auc']:.4f}/{res_mlp['ap']:.4f}/{res_mlp['acc']:.4f}",
        "note": "small MLP 904-256-64-1 on handcrafted features; same setup as Stage 7 (seed 42, 20 epochs)",
    })

    # Part 3: deep embedding comparison
    print("\n[embedding] running ResNet18 embedding comparison...")
    emb_results, secs = embedding_comparison()
    for r in emb_results:
        print(f"[embedding] {r['name']}: AUC={r['auc']:.4f} AP={r['ap']:.4f} ACC={r['acc']:.4f} n={r['n']}")
        result_rows.append({
            "step": "embedding",
            "key": r["name"],
            "value": f"AUC={r['auc']:.4f} AP={r['ap']:.4f} ACC={r['acc']:.4f} n={r['n']}",
            "note": "LogisticRegression C=1.0 standardized; well-grouped LOO; ResNet18 ImageNet 512-d embeddings from ch1/ch4/ch2 RGB composites" if "well" in r["name"] else "GroupKFold(3) by well on 12 site images; LR C=1.0 standardized",
        })
    plot_embedding_comparison(emb_results, os.path.join(FIG, "24_embedding_comparison.png"))
    result_rows.append({"step": "figure", "key": "24_embedding_comparison.png", "value": "OK", "note": os.path.relpath(os.path.join(FIG, "24_embedding_comparison.png"), BASE)})

    # Part 4: single-cell CNN
    print("\n[cnn] loading Cellpose crops...")
    Xc, yc, gc, meta = load_crops()
    if len(Xc) < 100 or len(np.unique(gc)) < 2:
        print(f"[cnn] SKIPPED - only {len(Xc)} crops / {len(np.unique(gc))} wells")
        result_rows.append({"step": "cnn", "key": "self_trained_cnn_singlecell", "value": "SKIPPED", "note": f"only {len(Xc)} crops / {len(np.unique(gc))} wells -> leak-free CNN not executable"})
    else:
        epochs = 20
        print(f"[cnn] crops={len(Xc)} wells={sorted(set(gc))} training CNN (epochs={epochs}, GroupKFold by well)...")
        res_cnn = train_cnn_cv(Xc, yc, gc, epochs=epochs)
        print(f"[cnn] test AUC={res_cnn['auc']:.4f} AP={res_cnn['ap']:.4f} ACC={res_cnn['acc']:.4f}")
        result_rows.append({
            "step": "cnn",
            "key": "self_trained_cnn_singlecell_groupkfold",
            "value": f"AUC={res_cnn['auc']:.4f} AP={res_cnn['ap']:.4f} ACC={res_cnn['acc']:.4f}",
            "note": f"Cellpose cpsam_v2 crops n={len(Xc)} from {len(np.unique(gc))} wells; small CNN 64x64 single-channel; GroupKFold(4) by well (DMSO wells in test across folds); epochs={epochs}, seed 42",
        })
        plot_cnn_curves(res_cnn["history"], epochs, os.path.join(FIG, "25_cnn_training_curves.png"))
        plot_cnn_confusion(res_cnn["y_true"], res_cnn["y_prob"], os.path.join(FIG, "26_cnn_confusion.png"))
        result_rows.append({"step": "figure", "key": "25_cnn_training_curves.png", "value": "OK", "note": os.path.relpath(os.path.join(FIG, "25_cnn_training_curves.png"), BASE)})
        result_rows.append({"step": "figure", "key": "26_cnn_confusion.png", "value": "OK", "note": os.path.relpath(os.path.join(FIG, "26_cnn_confusion.png"), BASE)})

    df = pd.DataFrame(result_rows)
    csv_path = os.path.join(BASE, "reports", "17_deep_representation_results.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[out] results CSV -> {csv_path}")

    summary = {
        "stage": 8,
        "n_tiff_trt_dmso": [len(glob.glob(os.path.join(RAW_TRT, "*.tiff"))), len(glob.glob(os.path.join(RAW_DMSO, "*.tiff")))],
        "embedding_seconds": secs,
        "embedding_results": emb_results,
        "cnn": None,
        "mlp_trt_vs_dmso_auc": round(res_mlp["auc"], 4),
    }
    if "res_cnn" in locals():
        summary["cnn"] = {"n_crops": len(Xc), "auc": round(res_cnn["auc"], 4), "ap": round(res_cnn["ap"], 4), "acc": round(res_cnn["acc"], 4)}
    with open(os.path.join(BASE, "reports", "17_stage8_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("[out] summary JSON -> reports/17_stage8_summary.json")
    print("\nStage 8 pipeline finished.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        err_path = os.path.join(BASE, "reports", "17_stage8_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write(tb)
        print(f"[FATAL] exception logged to {err_path}\n{tb}")
        raise
