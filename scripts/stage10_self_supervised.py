# -*- coding: utf-8 -*-
"""Stage 10 - Experiment 1: Self-supervised representation comparison (DINOv2 / OpenPhenom vs ResNet18)
Protocol mirror: 06_deep_representation_pipeline.py Part 3
- 12 sites (6 treated + 6 DMSO) from BR00116991 plate
- Site embeddings -> well-level mean aggregation (6 wells)
- Logistic regression (C=1.0, standardized), LeaveOneGroupOut by well -> AUC/AP/ACC
"""
import os, glob, time, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut, GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score, accuracy_score
import torch
import torch.nn as nn

RANDOM_STATE = 42

# HF mirror (mainland China network): timm / transformers weights via hf-mirror.com
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ.setdefault("HF_HOME", os.path.join(os.environ.get("TEMP", os.getcwd()), "hf_home"))


BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
RAW_TRT = os.path.join(DATA, "raw", "BR00116991")
RAW_DMSO = os.path.join(DATA, "raw", "BR00116991_dmso")
PROFILES_DIR = os.path.join(DATA, "profiles")
REPO = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science\github_repo"
FIG = os.path.join(REPO, "reports", "figures")
os.makedirs(FIG, exist_ok=True)
REPORTS = os.path.join(REPO, "reports")
os.makedirs(REPORTS, exist_ok=True)

SITE_WELL = {"r01c01": "A01", "r01c03": "A03", "r01c04": "A04",
             "r01c02": "A02", "r01c09": "A09", "r01c17": "A17"}
SITE_LABEL = {"r01c01": 1, "r01c03": 1, "r01c04": 1, "r01c02": 0, "r01c09": 0, "r01c17": 0}
WELL_ORDER = ["A01", "A02", "A03", "A04", "A09", "A17"]
WELL_LABEL = {"A01": 1, "A02": 0, "A03": 1, "A04": 1, "A09": 0, "A17": 0}
FEATURE_PREFIXES = ("Cells_", "Cytoplasm_", "Nuclei_")


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)


def collect_sites():
    sites = {}
    for d in (RAW_TRT, RAW_DMSO):
        for p in glob.glob(os.path.join(d, "*-ch1sk1fk1fl1.tiff")):
            base = os.path.basename(p)
            site = base.split("-")[0]
            channels = [glob.glob(os.path.join(d, f"{site}-ch{c}sk1fk1fl1.tiff"))[0] for c in range(1, 9)]
            sites[site] = {"dir": d, "label": SITE_LABEL[site[:6]], "well": SITE_WELL[site[:6]], "channels": channels}
    return sites


def read_site_channels(site_info):
    import tifffile
    chans = [tifffile.imread(p).astype(np.float32) / 65535.0 for p in site_info["channels"]]
    rgb = np.clip(np.stack([chans[0], chans[3], chans[1]], axis=-1), 0, 1)  # ch1/ch4/ch2
    all8 = np.clip(np.stack(chans, axis=0), 0, 1)  # (8, H, W)
    return rgb, all8


def load_timm_dinov2(name):
    import timm
    model = timm.create_model(name, pretrained=True)
    model.eval()
    return model


def embed_timm(model, rgb, size=None, device="cuda"):
    from torchvision import transforms
    import tifffile
    if size is None:
        size = model.patch_embed.img_size[0]  # e.g. DINOv2 lvd142m -> 518
    tf = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    img = tf((rgb * 255.0).astype(np.uint8)).unsqueeze(0).to(device)
    with torch.no_grad():
        feats = model.forward_features(img)  # (1, 1+N, D)
    if feats.dim() == 3:
        vec = feats[0, 1:, :].mean(0)  # avg pool over tokens
    else:
        vec = feats[0]
    return vec.cpu().numpy()


def embed_openphenom(model, tensor_8_or_3, size=256, device="cuda"):
    """tensor: (C, H, W) float [0,1], C in {3, 8}. Returns 384-d avg-pooled encoder latent."""
    import torch.nn.functional as F
    import torchvision.transforms.functional as TF
    x = torch.from_numpy(tensor_8_or_3).unsqueeze(0).to(device)  # (1, C, H, W)
    if x.dim() == 4 and x.shape[1] not in (3, 8, 11):  # HWC -> CHW
        x = x.permute(0, 3, 1, 2)
    x = F.interpolate(x, size=(size, size), mode="bilinear", align_corners=False)
    x = x * 255.0
    with torch.no_grad():
        xn = model.input_norm(x)
        latent, _mask, _ir = model.encoder.forward_masked(xn, 0.0, None)
        vec = latent[0, 1:, :].mean(0)
    return vec.cpu().numpy()


def evaluate_lr(X, y, groups, name):
    y = np.asarray(y); groups = np.asarray(groups)
    logo = LeaveOneGroupOut()
    y_prob = np.zeros(len(y))
    for tr, te in logo.split(X, y, groups):
        clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
        sc = StandardScaler().fit(X[tr])
        clf.fit(sc.transform(X[tr]), y[tr])
        y_prob[te] = clf.predict_proba(sc.transform(X[te]))[:, 1]
    auc = roc_auc_score(y, y_prob) if np.unique(y).size == 2 else float("nan")
    return {"name": name, "n": len(y), "auc": float(auc),
            "ap": float(average_precision_score(y, y_prob)),
            "acc": float(accuracy_score(y, (y_prob >= 0.5).astype(int)))}


def main():
    import tifffile
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", dev)
    sites = collect_sites()
    site_order = sorted(sites)
    print("sites:", len(site_order), site_order)

    # ---- load all site images once (RGB + all8) ----
    imgs = {}
    for s in site_order:
        rgb, all8 = read_site_channels(sites[s])
        imgs[s] = (rgb, all8)
    y_site = np.array([sites[s]["label"] for s in site_order])
    well_site = np.array([sites[s]["well"] for s in site_order])
    y_well = np.array([WELL_LABEL[w] for w in WELL_ORDER])

    results = []

    def run_model(name, emb_site, agg="mean"):
        Xw = np.vstack([np.mean([emb_site[s] for s in site_order if sites[s]["well"] == w], axis=0) for w in WELL_ORDER])
        r = evaluate_lr(Xw, y_well, WELL_ORDER, name)
        # site-level GroupKFold(3) same as 06
        gkf = GroupKFold(n_splits=3)
        yp = np.zeros(len(site_order))
        Xs = np.vstack([emb_site[s] for s in site_order])
        for tr, te in gkf.split(Xs, y_site, well_site):
            clf = LogisticRegression(max_iter=2000, C=1.0, random_state=RANDOM_STATE)
            sc = StandardScaler().fit(Xs[tr])
            clf.fit(sc.transform(Xs[tr]), y_site[tr])
            yp[te] = clf.predict_proba(sc.transform(Xs[te]))[:, 1]
        r_site = {"name": name + "_site12_gkf3",
                  "n": len(y_site),
                  "auc": float(roc_auc_score(y_site, yp)),
                  "ap": float(average_precision_score(y_site, yp)),
                  "acc": float(accuracy_score(y_site, (yp >= 0.5).astype(int)))}
        results.append(r); results.append(r_site)
        return r, r_site

    # ---- ResNet18 baseline (re-run to verify reproducibility of 0.7778) ----
    from torchvision.models import resnet18, ResNet18_Weights
    from torchvision import transforms
    tf = transforms.Compose([
        transforms.ToPILImage(), transforms.Resize(224), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    rn = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1).eval().to(dev)
    rn = nn.Sequential(*list(rn.children())[:-1])
    emb_rn = {}
    with torch.no_grad():
        for s in site_order:
            rgb, _ = imgs[s]
            img = tf((rgb * 255.0).astype(np.uint8)).unsqueeze(0).to(dev)
            emb_rn[s] = rn(img).flatten(1).cpu().numpy()[0]
    r, rs = run_model("deep_resnet18_512_well6", emb_rn)
    print("ResNet18 well6:", r)

    # ---- DINOv2 vit_small ----
    dino_s = load_timm_dinov2("vit_small_patch14_dinov2.lvd142m").to(dev)
    emb_ds = {s: embed_timm(dino_s, imgs[s][0]) for s in site_order}
    r, rs = run_model("deep_dinov2_vits14_384_well6", emb_ds)
    print("DINOv2 vits14 well6:", r)

    # ---- DINOv2 vit_base ----
    try:
        dino_b = load_timm_dinov2("vit_base_patch14_dinov2.lvd142m").to(dev)
        emb_db = {s: embed_timm(dino_b, imgs[s][0]) for s in site_order}
        r, rs = run_model("deep_dinov2_vitb14_768_well6", emb_db)
        print("DINOv2 vitb14 well6:", r)
        dino_b_ok = True
    except Exception as e:
        print("DINOv2 vit_base FAILED:", type(e).__name__, str(e)[:300])
        dino_b_ok = False

    # ---- OpenPhenom (recursionpharma) ----
    import os as _os
    _os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    from transformers import AutoModel
    cache = _os.path.join(_os.environ["TEMP"], "openphenom", "models--recursionpharma--OpenPhenom",
                          "snapshots", "0f92333685f6e9f031b804c70fe246f9b05ae90d")
    op = AutoModel.from_pretrained(cache, trust_remote_code=True).eval().to(dev)
    emb_op3 = {s: embed_openphenom(op, imgs[s][0]) for s in site_order}
    r, rs = run_model("deep_openphenom_vits16_384_well6_rgb3", emb_op3)
    print("OpenPhenom RGB3 well6:", r)
    emb_op8 = {s: embed_openphenom(op, imgs[s][1]) for s in site_order}
    r, rs = run_model("deep_openphenom_vits16_384_well6_ch8", emb_op8)
    print("OpenPhenom CH8 well6:", r)

    # ---- save results ----
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(REPORTS, "18_stage10_selfsupervised_results.csv"), index=False)
    print(df.to_string(index=False))

    # ---- figure 28a: bar comparison of well6 LOO AUC/AP ----
    well_rows = [x for x in results if "well6" in x["name"] and "site12" not in x["name"]]
    names = [x["name"].replace("deep_", "").replace("_well6", "") for x in well_rows]
    aucs = [x["auc"] for x in well_rows]
    aps = [x["ap"] for x in well_rows]
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    xpos = np.arange(len(names))
    w = 0.36
    ax.bar(xpos - w / 2, aucs, w, label="AUC (well-grouped LOO)", color="#4C72B0")
    ax.bar(xpos + w / 2, aps, w, label="AP", color="#DD8452")
    for xi, a, ap in zip(xpos, aucs, aps):
        ax.text(xi - w / 2, a + 0.01, f"{a:.4f}", ha="center", fontsize=8)
        ax.text(xi + w / 2, ap + 0.01, f"{ap:.4f}", ha="center", fontsize=8)
    ax.set_xticks(xpos); ax.set_xticklabels(names, rotation=18, ha="right", fontsize=9)
    ax.set_ylim(0, 1.12); ax.set_ylabel("Score")
    ax.set_title("Stage 10 - Self-supervised representation comparison\n(12 sites BR00116991, well-grouped LOO, logistic regression)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "28a_self_supervised_comparison.png"))
    plt.close(fig)
    print("figure saved:", os.path.join(FIG, "28a_self_supervised_comparison.png"))

    summary = {"stage10_exp1_self_supervised": {
        "protocol": "12 sites -> well mean (6 wells) -> LR C=1.0 standardized, LeaveOneGroupOut",
        "results_well6": well_rows,
        "dinov2_vitb14_ok": dino_b_ok,
    }}
    with open(os.path.join(REPORTS, "18_stage10_selfsupervised_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
