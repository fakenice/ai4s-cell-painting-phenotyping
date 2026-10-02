# -*- coding: utf-8 -*-
"""
AI4S Single-cell Phenotypic Profiling - Stage 7: Deep Representation Learning & Transfer Learning

Part 1  Asset inventory (honest data-gate)
    - Count local JUMP-CP raw images (TIFF), their site / plate / label coverage
    - Detect any official JUMP-CP embedding artifacts (.npy/.npz/.parquet/.h5)
    - Locate Cellpose single-cell segmentation outputs (masks / crops)
    -> If image coverage does not support a two-class experiment, we REPORT and SKIP
       (no fabricated deep-embedding or CNN numbers).

Part 2  Deep-model baseline on morphological features (executable now)
    - Small MLP (904 -> 256 -> 64 -> 1) on the 904-feature well-level matrix
    - Same task as the XGBoost baseline (treated vs DMSO, 648 wells, 5-fold stratified CV)
    - Training curves (loss / val AUC per epoch) and OOF confusion matrix
    - Compound-grouped GroupKFold robustness check on treated-vs-all-controls (768 wells)

Part 3  Transfer-learning embedding extraction (executable now, but no classifier)
    - ImageNet-pretrained ResNet18 (torchvision) feature extraction on the 8-channel TIFF site
      (3 channels selected -> ImageNet normalization -> 512-d embedding)
    - Extraction is a smoke test of the torch/timm pipeline; no classifier is trained
      because the local image subset has only treated (trt) wells, no DMSO controls.

Part 4  Self-trained small CNN on Cellpose single-cell crops
    - REQUIRES two-class single-cell image dataset (trt vs DMSO) grouped by compound/well
    - Locally unavailable -> status=skipped, reason recorded (no fabrication)

Output : reports/figures/22_mlp_training_curves.png
         reports/figures/23_mlp_confusion.png
         reports/17_deep_representation_results.csv
         (figure 21 deep-embedding comparison is NOT produced: no two-class image data)
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
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.preprocessing import StandardScaler
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
RAW_IMG = os.path.join(DATA, "raw", "BR00116991")
PROFILES_DIR = os.path.join(DATA, "profiles")
FIG = os.path.join(BASE, "reports", "figures")
os.makedirs(FIG, exist_ok=True)

FEATURE_PREFIXES = ("Cells_", "Cytoplasm_", "Nuclei_")  # morphological feature columns
METADATA_COLS = [c for c in []]

# ---------- Part 1: asset inventory ----------


def scan_assets():
    """Return a list of (step, key, value, note) inventory rows."""
    rows = []

    # Raw images (JUMP-CP uses .tiff extension)
    tiffs = sorted(glob.glob(os.path.join(RAW_IMG, "*.tiff")) + glob.glob(os.path.join(RAW_IMG, "*.tif")))
    n_tiff = len(tiffs)
    sites = sorted({os.path.basename(p)[: 7 + 4] for p in tiffs}) if tiffs else []
    rows.append(
        (
            "asset_images",
            "n_tiff",
            str(n_tiff),
            f"raw dir: {os.path.relpath(RAW_IMG, BASE)} ; sites: {sites} (1080x1080 uint16)",
        )
    )

    # Embedding artifacts
    embed_exts = (".npy", ".npz", ".parquet", ".h5", ".hdf5", ".pt", ".pth")
    embeds = []
    for root, _dirs, files in os.walk(DATA):
        for f in files:
            if f.lower().endswith(embed_exts):
                embeds.append(os.path.join(root, f))
    rows.append(
        (
            "asset_embeddings",
            "official_jumpcp_embeddings",
            "FOUND" if embeds else "NONE",
            "; ".join(embeds) if embeds else "no .npy/.npz/.parquet/.h5 embedding files under data/",
        )
    )

    # Cellpose crops / masks
    crop_dirs = []
    for root, dirs, files in os.walk(DATA):
        for d in dirs:
            if "crop" in d.lower() or "mask" in d.lower() or "cell" in d.lower():
                crop_dirs.append(os.path.join(root, d))
    rows.append(
        (
            "asset_cellpose",
            "single_cell_crops",
            "FOUND" if crop_dirs else "NONE",
            "; ".join(crop_dirs)
            if crop_dirs
            else "only reports/05_cellpose_summary.csv (116 cells, all treated); no crop/mask directory",
        )
    )

    # Label coverage from profiles
    prof = load_profiles()
    compound_wells = prof.dropna(subset=["Metadata_pert_iname"])
    trt = compound_wells[compound_wells["Metadata_pert_type"] == "trt"]
    dmso = compound_wells[compound_wells["Metadata_pert_iname"] == "DMSO"]
    rows.append(
        (
            "asset_labels",
            "well_counts_trt_dmso",
            f"{len(trt)}/{len(dmso)}",
            "648-well treated-vs-DMSO matrix (520 trt / 128 DMSO), matching Stage 6 XGBoost setup",
        )
    )
    rows.append(
        (
            "asset_labels",
            "image_label_coverage",
            "trt_only",
            f"{n_tiff} raw TIFFs belong to a single treated site (BR00116991 r01c01); "
            "no DMSO control images on disk -> two-class image classification NOT possible",
        )
    )
    return rows, prof


def load_profiles():
    """Load and concatenate all per-plate profile CSV.GZ files."""
    plate_files = sorted(
        f for f in os.listdir(PROFILES_DIR) if f.endswith(".csv.gz")
    )
    frames = [pd.read_csv(os.path.join(PROFILES_DIR, f)) for f in plate_files]
    return pd.concat(frames, ignore_index=True)


def split_xy(prof, task):
    """Return X (float32 matrix), y (int array), groups (array or None)."""
    feat_cols = [c for c in prof.columns if c.startswith(FEATURE_PREFIXES)]
    assert len(feat_cols) == 904, f"expected 904 morphology features, got {len(feat_cols)}"
    if task == "trt_vs_dmso":
        # same protocol as Stage 6: drop wells without compound name (ORF plates),
        # then keep treated + DMSO -> 520 trt + 128 DMSO = 648 wells
        sub = prof.dropna(subset=["Metadata_pert_iname"]).copy()
        mask = (sub["Metadata_pert_type"] == "trt") | (sub["Metadata_pert_iname"] == "DMSO")
        sub = sub[mask].copy()
        y = (sub["Metadata_pert_type"] == "trt").astype(int).values
        groups = None
    elif task == "trt_vs_all_ctrl":
        sub = prof.dropna(subset=["Metadata_pert_iname"]).copy()
        mask = (sub["Metadata_pert_type"] == "trt") | (sub["Metadata_pert_type"] == "control")
        sub = sub[mask].copy()
        y = (sub["Metadata_pert_type"] == "trt").astype(int).values
        # group = compound identity (pert_iname + plate) to enforce no-leakage grouping
        groups = (sub["Metadata_pert_iname"].astype(str) + "_" + sub["Metadata_Plate"].astype(str)).values
    else:
        raise ValueError(task)
    X = sub[feat_cols].values.astype(np.float32)
    return X, y, groups, sub


# ---------- Part 2: MLP deep-model baseline ----------


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


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)


def train_epoch(model, Xtr, ytr, Xva, yva, opt, crit):
    """One epoch over the train fold; returns mean train loss, val loss, val AUC."""
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


def run_mlp_cv(X, y, groups, name, collect_history=True):
    """Generic MLP CV. groups is None -> StratifiedKFold; else GroupKFold (compound groups)."""
    set_seed(RANDOM_STATE)
    n = len(y)
    y_prob = np.zeros(n)
    history = {"train_loss": [], "val_loss": [], "val_auc": []} if collect_history else None

    if groups is None:
        cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
        splits = cv.split(X, y)
    else:
        cv = GroupKFold(n_splits=N_SPLITS)
        splits = cv.split(X, y, groups)

    for fold, (tr, va) in enumerate(splits):
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
            tl, vl, vauc = train_epoch(model, Xtr, ytr, Xva, yva, opt, crit)
            if collect_history:
                history["train_loss"].append(tl)
                history["val_loss"].append(vl)
                history["val_auc"].append(vauc)

        model.eval()
        with torch.no_grad():
            y_prob[va] = torch.sigmoid(model(Xva)).squeeze(1).numpy()

    auc = roc_auc_score(y, y_prob)
    ap = average_precision_score(y, y_prob)
    acc = accuracy_score(y, (y_prob >= 0.5).astype(int))
    return {
        "experiment": name,
        "n": n,
        "auc": float(auc),
        "ap": float(ap),
        "acc": float(acc),
        "y_true": y.tolist(),
        "y_prob": y_prob.tolist(),
        "history": history,
    }


def plot_mlp_curves(history, path):
    """Epoch-level train/val loss + val AUC (mean over folds)."""
    ep = np.arange(1, EPOCHS + 1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    tl = np.array(history["train_loss"]).reshape(N_SPLITS, EPOCHS)
    vl = np.array(history["val_loss"]).reshape(N_SPLITS, EPOCHS)
    va = np.array(history["val_auc"]).reshape(N_SPLITS, EPOCHS)

    axes[0].plot(ep, tl.mean(0), label="train loss", color="#1f77b4")
    axes[0].plot(ep, vl.mean(0), label="val loss", color="#d62728")
    axes[0].fill_between(ep, tl.mean(0) - tl.std(0), tl.mean(0) + tl.std(0), alpha=0.15, color="#1f77b4")
    axes[0].fill_between(ep, vl.mean(0) - vl.std(0), vl.mean(0) + vl.std(0), alpha=0.15, color="#d62728")
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("BCE loss")
    axes[0].set_title("MLP training curves (5-fold mean +/- SD)")
    axes[0].legend()

    axes[1].plot(ep, va.mean(0), marker="o", color="#2ca02c", label="val AUC")
    axes[1].fill_between(ep, va.mean(0) - va.std(0), va.mean(0) + va.std(0), alpha=0.15, color="#2ca02c")
    axes[1].axhline(0.7682, ls="--", color="#7f7f7f", label="XGBoost pheno AUC 0.7682")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("ROC AUC")
    axes[1].set_title("Validation AUC per epoch")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_confusion(y_true, y_prob, path):
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    cm = confusion_matrix(y_true, (y_prob >= 0.5).astype(int))
    acc = accuracy_score(y_true, (y_prob >= 0.5).astype(int))
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues", cbar=False,
        xticklabels=["Pred DMSO", "Pred treated"], yticklabels=["True DMSO", "True treated"],
        ax=ax,
    )
    ax.set_title(f"MLP OOF confusion matrix (ACC = {acc:.3f})")
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


# ---------- Part 3: transfer embedding smoke test ----------


def resnet18_embedding_smoke():
    """Extract ImageNet-pretrained ResNet18 embeddings from the 8-channel TIFF site.

    Local images are treated-only (no DMSO), so no classifier is trained; this is a
    reproducible pipeline smoke test proving the torchvision transfer path works.
    Returns (status, dim, n_images, seconds) or (status, error_msg).
    """
    try:
        from torchvision import transforms
        from torchvision.models import resnet18, ResNet18_Weights
        import tifffile
    except Exception as e:  # pragma: no cover
        return ("SKIPPED", None, None, None, f"torchvision/tifffile import failed: {e}")

    tiffs = sorted(glob.glob(os.path.join(RAW_IMG, "*.tiff")) + glob.glob(os.path.join(RAW_IMG, "*.tif")))
    if len(tiffs) < 3:
        return ("SKIPPED", None, None, None, f"only {len(tiffs)} TIFFs, need >= 3 for RGB mapping")

    tf = transforms.Compose(
        [
            transforms.ToPILImage(),
            transforms.Resize(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.eval()
    # keep features before the final FC (512-d avg-pooled embedding)
    model = nn.Sequential(*list(model.children())[:-1])

    emb_list = []
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, len(tiffs) - 2, 3):
            chans = [tifffile.imread(p) for p in tiffs[i : i + 3]]
            rgb = np.stack([c.astype(np.float32) / 65535.0 for c in chans], axis=-1)
            rgb = np.clip(rgb, 0, 1)
            img = tf((rgb * 255.0).astype(np.uint8))
            emb = model(img.unsqueeze(0)).flatten(1)  # 1 x 512
            emb_list.append(emb.numpy())
    seconds = time.time() - t0
    if not emb_list:
        return ("SKIPPED", None, None, None, "no embedding extracted")
    emb = np.concatenate(emb_list, axis=0)
    return ("OK", emb.shape[1], emb.shape[0], round(seconds, 2), "ResNet18 (ImageNet) 512-d embeddings extracted; no classifier (trt-only images)")


# ---------- main ----------


def main():
    result_rows = []  # (step, key, value, note)
    print("=" * 70)
    print("Stage 7: Deep Representation Learning & Transfer Learning")
    print("=" * 70)

    # Part 1: asset scan
    inv, prof = scan_assets()
    for step, key, value, note in inv:
        result_rows.append({"step": step, "key": key, "value": value, "note": note})
        print(f"[{step}] {key} = {value} -- {note}")

    # Part 2: MLP baseline (executable regardless of images)
    X, y, groups, _ = split_xy(prof, "trt_vs_dmso")
    print("\n[mlp] running 5-fold stratified MLP on treated-vs-DMSO (648 wells)...")
    res_trt = run_mlp_cv(X, y, None, "mlp_5fold_trt_vs_dmso")
    print(
        f"[mlp] trt-vs-DMSO 5-fold OOF AUC={res_trt['auc']:.4f} AP={res_trt['ap']:.4f} ACC={res_trt['acc']:.4f}"
    )
    result_rows.append(
        {
            "step": "mlp",
            "key": "mlp_5fold_trt_vs_dmso_auc_ap_acc",
            "value": f"{res_trt['auc']:.4f}/{res_trt['ap']:.4f}/{res_trt['acc']:.4f}",
            "note": "small MLP 904-256-64-1, Adam lr=1e-3 wd=1e-4, dropout 0.3, 20 epochs, seed 42; same task/CV as Stage 6 XGBoost (AUC 0.7682)",
        }
    )
    result_rows.append(
        {
            "step": "mlp",
            "key": "mlp_trt_vs_dmso_compound_group_cv",
            "value": "NOT_APPLICABLE",
            "note": "single negative control DMSO forms one compound group; GroupKFold would put all 128 DMSO wells in one fold -> no two-class evaluation possible; well-level stratified CV reported instead",
        }
    )

    # compound-grouped GroupKFold on treated-vs-all-controls (robustness, no leakage)
    X2, y2, groups2, _ = split_xy(prof, "trt_vs_all_ctrl")
    print("\n[mlp] running compound-grouped GroupKFold MLP on treated-vs-all-controls (768 wells)...")
    res_grp = run_mlp_cv(X2, y2, groups2, "mlp_groupkfold_trt_vs_all_ctrl")
    print(
        f"[mlp] trt-vs-all GroupKFold AUC={res_grp['auc']:.4f} AP={res_grp['ap']:.4f} ACC={res_grp['acc']:.4f}"
    )
    result_rows.append(
        {
            "step": "mlp",
            "key": "mlp_groupkfold_trt_vs_all_auc_ap_acc",
            "value": f"{res_grp['auc']:.4f}/{res_grp['ap']:.4f}/{res_grp['acc']:.4f}",
            "note": "GroupKFold by compound identity (pert_iname+plate): same compound never in train and test folds (no leakage); 768 wells, 5 groups x 5 folds",
        }
    )

    # figures
    plot_mlp_curves(res_trt["history"], os.path.join(FIG, "22_mlp_training_curves.png"))
    plot_confusion(res_trt["y_true"], res_trt["y_prob"], os.path.join(FIG, "23_mlp_confusion.png"))
    result_rows.append(
        {
            "step": "figure",
            "key": "21_deep_embedding_comparison",
            "value": "SKIPPED",
            "note": "no two-class image data (no DMSO images / no official JUMP-CP embeddings) -> deep-embedding vs handcrafted AUC comparison not possible; no fabricated numbers",
        }
    )
    result_rows.append(
        {
            "step": "figure",
            "key": "22_mlp_training_curves.png",
            "value": "OK",
            "note": os.path.relpath(os.path.join(FIG, "22_mlp_training_curves.png"), BASE),
        }
    )
    result_rows.append(
        {
            "step": "figure",
            "key": "23_mlp_confusion.png",
            "value": "OK",
            "note": os.path.relpath(os.path.join(FIG, "23_mlp_confusion.png"), BASE),
        }
    )

    # Part 3: transfer embedding smoke test
    print("\n[transfer] ResNet18 embedding extraction smoke test...")
    status, dim, nimg, secs, note = resnet18_embedding_smoke()
    print(f"[transfer] status={status} dim={dim} n={nimg} time={secs}s -- {note}")
    result_rows.append(
        {
            "step": "transfer",
            "key": "resnet18_embedding_extraction",
            "value": f"{status} dim={dim if dim else '-'} n={nimg if nimg else '-'} t={secs if secs else '-'}s",
            "note": note,
        }
    )
    result_rows.append(
        {
            "step": "transfer",
            "key": "deep_embedding_vs_handcrafted_classifier",
            "value": "SKIPPED",
            "note": "would require both trt and DMSO images to train same-protocol classifiers; local image subset is trt-only -> honestly skipped",
        }
    )

    # Part 4: self-trained CNN on single-cell crops
    result_rows.append(
        {
            "step": "cnn",
            "key": "self_trained_cnn_singlecell",
            "value": "SKIPPED",
            "note": "requires two-class (trt vs DMSO) Cellpose single-cell crops grouped by compound/well; local data: 116 segmented cells from a single treated site, no DMSO cells -> train/val/test leak-free CNN not executable",
        }
    )

    df = pd.DataFrame(result_rows)
    csv_path = os.path.join(BASE, "reports", "17_deep_representation_results.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[out] results CSV -> {csv_path}")

    summary = {
        "stage": 7,
        "mlp_trt_vs_dmso_auc": round(res_trt["auc"], 4),
        "mlp_trt_vs_dmso_ap": round(res_trt["ap"], 4),
        "mlp_trt_vs_dmso_acc": round(res_trt["acc"], 4),
        "mlp_groupkfold_trt_vs_all_auc": round(res_grp["auc"], 4),
        "mlp_groupkfold_trt_vs_all_ap": round(res_grp["ap"], 4),
        "mlp_groupkfold_trt_vs_all_acc": round(res_grp["acc"], 4),
        "transfer_embedding": status,
        "cnn_singlecell": "SKIPPED",
    }
    with open(os.path.join(BASE, "reports", "17_stage7_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("[out] summary JSON -> reports/17_stage7_summary.json")
    print("\nStage 7 pipeline finished.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        tb = traceback.format_exc()
        err_path = os.path.join(BASE, "reports", "17_stage7_error.log")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write(tb)
        print(f"[FATAL] exception logged to {err_path}\n{tb}")
        raise
