# -*- coding: utf-8 -*-
"""Stage 11 - P0-4: Retrieval track switch. Replicate retrieval AP with deep embeddings
(DINOv2 / OpenPhenom / ResNet18) vs hand-crafted 904 features under the same protocol.

Protocol (mirror stage10_retrieval well_ap_metrics):
  - embeddings per site (12 sites BR00116991), well-level mean -> 6 well vectors
  - cosine similarity retrieval, query well -> same-compound wells AP
  - metrics: mean_replicate_AP, chance_AP, pair_AUC (same vs different compound)
  - also report field-level (site-level) retrieval AP: query site -> same-well sites

The 904-feature baseline here is computed on the SAME 6 wells (well-level mean),
so it is directly comparable to deep embeddings. (Stage 10's 0.2451 was computed on
the full 648-well maskA; both numbers are reported with their scopes.)
"""
import os, glob, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import normalize
from sklearn.metrics import average_precision_score, roc_auc_score
import torch
import torch.nn as nn

RANDOM_STATE = 42
BASE = r"E:\Desktop\Kaggle_2026\2026-10-10 AI4S Open Innovation：AI for Life Science"
DATA = os.path.join(BASE, "data")
REPO = os.path.join(BASE, "github_repo")
FIG = os.path.join(REPO, "reports", "figures")
FIG_ROOT = os.path.join(REPO, "figures")
REPORTS = os.path.join(REPO, "reports")
os.makedirs(FIG, exist_ok=True)
os.makedirs(FIG_ROOT, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

SITE_WELL = {"r01c01": "A01", "r01c03": "A03", "r01c04": "A04",
             "r01c02": "A02", "r01c09": "A09", "r01c17": "A17"}
SITE_LABEL = {"r01c01": 1, "r01c03": 1, "r01c04": 1, "r01c02": 0, "r01c09": 0, "r01c17": 0}
WELL_COMPOUND = {"A01": "gabapentin-enacarbil", "A02": "DMSO", "A03": "amlodipine",
                 "A04": "hexestrol", "A09": "DMSO", "A17": "DMSO"}


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)


def collect_sites():
    sites = {}
    for d in (os.path.join(DATA, "raw", "BR00116991"), os.path.join(DATA, "raw", "BR00116991_dmso")):
        for p in glob.glob(os.path.join(d, "*-ch1sk1fk1fl1.tiff")):
            base = os.path.basename(p)
            site = base.split("-")[0]  # full site id, e.g. r01c01f01p01
            site6 = site[:6]
            channels = [glob.glob(os.path.join(d, f"{site}-ch{c}sk1fk1fl1.tiff"))[0] for c in range(1, 9)]
            sites[site] = {"dir": d, "label": SITE_LABEL[site6], "well": SITE_WELL[site6], "channels": channels}
    return sites


def read_site_channels(site_info):
    import tifffile
    chans = [tifffile.imread(p).astype(np.float32) / 65535.0 for p in site_info["channels"]]
    rgb = np.clip(np.stack([chans[0], chans[3], chans[1]], axis=-1), 0, 1)
    all8 = np.clip(np.stack(chans, axis=0), 0, 1)
    return rgb, all8


def embed_timm(model, rgb, size=None, device="cuda"):
    from torchvision import transforms
    if size is None:
        size = model.patch_embed.img_size[0]
    tf = transforms.Compose([
        transforms.ToPILImage(), transforms.Resize(size), transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    img = tf((rgb * 255.0).astype(np.uint8)).unsqueeze(0).to(device)
    with torch.no_grad():
        feats = model.forward_features(img)
    if feats.dim() == 3:
        vec = feats[0, 1:, :].mean(0)
    else:
        vec = feats[0]
    return vec.cpu().numpy()


def embed_openphenom(model, tensor_8_or_3, size=256, device="cuda"):
    import torch.nn.functional as F
    x = torch.from_numpy(tensor_8_or_3).unsqueeze(0).to(device)
    x = F.interpolate(x, size=(size, size), mode="bilinear", align_corners=False)
    x = x * 255.0
    with torch.no_grad():
        xn = model.input_norm(x)
        latent, _mask, _ir = model.encoder.forward_masked(xn, 0.0, None)
        vec = latent[0, 1:, :].mean(0)
    return vec.cpu().numpy()


def retrieval_metrics(X, groups):
    """X: (n, d) feature matrix; groups: compound/well labels. Cosine retrieval AP + pair AUC."""
    Xn = normalize(X, norm="l2", axis=1)
    S = Xn @ Xn.T
    n = len(groups)
    groups = np.asarray(groups)
    aps, npos = np.zeros(n), np.zeros(n)
    valid = np.zeros(n, dtype=bool)
    for i in range(n):
        scores = S[i].copy()
        scores[i] = -1e9
        y = (groups == groups[i]).astype(int)
        y[i] = 0
        if y.sum() > 0:
            aps[i] = average_precision_score(y, scores)
            npos[i] = y.sum()
            valid[i] = True
    mean_ap = float(aps[valid].mean()) if valid.any() else float("nan")
    mean_chance = float((npos[valid] / (n - 1)).mean()) if valid.any() else float("nan")
    y_all = (groups[:, None] == groups[None, :]).astype(int)
    triu = np.triu_indices(n, k=1)
    pair_auc = roc_auc_score(y_all[triu], S[triu]) if np.unique(y_all[triu]).size > 1 else float("nan")
    return {"mean_AP": mean_ap, "chance_AP": mean_chance, "pair_AUC": float(pair_auc),
            "n_queries_valid": int(valid.sum()), "n": int(n)}


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", dev, flush=True)
    NPZ = os.path.join(REPORTS, "19_stage11_p0_embeddings.npz")
    if os.path.exists(NPZ):
        z = np.load(NPZ, allow_pickle=True)
        emb_site = dict(z["emb_site"].item())
        ok = dict(z["ok"].item())
        site_order = list(emb_site.keys())
        print("loaded cached embeddings:", len(site_order), flush=True)
    else:
        sites = collect_sites()
        site_order = sorted(sites)
        print("sites:", len(site_order), flush=True)

        imgs = {}
        for s in site_order:
            rgb, all8 = read_site_channels(sites[s])
            imgs[s] = (rgb, all8)
        print("images loaded", flush=True)

        # ---- ResNet18 ----
        from torchvision.models import resnet18, ResNet18_Weights
        from torchvision import transforms
        tf = transforms.Compose([
            transforms.ToPILImage(), transforms.Resize(224), transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        rn = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1).eval().to(dev)
        rn = nn.Sequential(*list(rn.children())[:-1])
        emb_site = {}
        with torch.no_grad():
            for s in site_order:
                rgb, _ = imgs[s]
                img = tf((rgb * 255.0).astype(np.uint8)).unsqueeze(0).to(dev)
                emb_site[f"deep_resnet18_512|{s}"] = rn(img).flatten(1).cpu().numpy()[0]
        print("resnet18 done", flush=True)

        # ---- DINOv2 ----
        import timm
        dino_models = {"deep_dinov2_vits14_384": ("vit_small_patch14_dinov2.lvd142m", None),
                       "deep_dinov2_vitb14_768": ("vit_base_patch14_dinov2.lvd142m", None)}
        ok = {"deep_resnet18_512": True}
        for name, (mname, size) in dino_models.items():
            try:
                m = timm.create_model(mname, pretrained=True).eval().to(dev)
                for s in site_order:
                    emb_site[f"{name}|{s}"] = embed_timm(m, imgs[s][0], size, dev)
                ok[name] = True
                print(name, "done", flush=True)
            except Exception as e:
                print(name, "FAILED", type(e).__name__, str(e)[:200], flush=True)
                ok[name] = False

        # save after resnet + dino so partial results survive OpenPhenom issues
        np.savez(NPZ, emb_site=emb_site, ok=ok)
        print("embeddings checkpoint saved:", NPZ, flush=True)

        # ---- OpenPhenom ----
        from transformers import AutoModel
        cache = os.path.join(os.environ["TEMP"], "openphenom", "models--recursionpharma--OpenPhenom",
                             "snapshots", "0f92333685f6e9f031b804c70fe246f9b05ae90d")
        try:
            op = AutoModel.from_pretrained(cache, trust_remote_code=True, local_files_only=True).eval().to(dev)
        except Exception as e:
            print("OpenPhenom LOAD FAILED:", type(e).__name__, str(e)[:200], flush=True)
            op = None
        if op is not None:
            for name, ch in (("deep_openphenom_vits16_384_rgb3", 0), ("deep_openphenom_vits16_384_ch8", 1)):
                for s in site_order:
                    emb_site[f"{name}|{s}"] = embed_openphenom(op, imgs[s][ch])
                ok[name] = True
                print(name, "done", flush=True)
            np.savez(NPZ, emb_site=emb_site, ok=ok)
            print("embeddings saved:", NPZ, flush=True)
        else:
            print("OpenPhenom skipped; using resnet+dino embeddings", flush=True)

    # well mapping from site keys ("model|r01c01f01p01")
    SITES = sorted(set(k.split("|")[1] for k in emb_site))
    site_order = SITES
    well_of = np.array([SITE_WELL[s[:6]] for s in SITES])
    print("sites:", len(SITES), "well_of:", well_of, flush=True)
    prof_files = sorted(f for f in os.listdir(os.path.join(DATA, "profiles")) if f.endswith(".csv.gz"))
    prof = pd.concat([pd.read_csv(os.path.join(DATA, "profiles", f)) for f in prof_files], ignore_index=True)
    feat_cols = [c for c in prof.columns if not c.startswith("Metadata")]
    well_feat = {}
    for w in sorted(WELL_COMPOUND):
        sub = prof[(prof["Metadata_Plate"] == "BR00116991") & (prof["Metadata_Well"] == w)]
        well_feat[w] = sub[feat_cols].mean(0).values
    X904 = np.vstack([well_feat[w] for w in sorted(WELL_COMPOUND)])
    comps904 = np.array([WELL_COMPOUND[w] for w in sorted(WELL_COMPOUND)])
    r904_well = retrieval_metrics(X904, comps904)
    print("904 well-level (6 wells):", r904_well)

    # ---- build embedding matrices per model ----
    rows = []
    emb_well_all = {}
    for name in ["deep_resnet18_512", "deep_dinov2_vits14_384", "deep_dinov2_vitb14_768",
                 "deep_openphenom_vits16_384_rgb3", "deep_openphenom_vits16_384_ch8"]:
        if not ok.get(name, True):
            continue
        Es = np.vstack([emb_site[f"{name}|{s}"] for s in site_order])
        Ew = np.vstack([Es[well_of == w].mean(0) for w in sorted(WELL_COMPOUND)])
        comps = np.array([WELL_COMPOUND[w] for w in sorted(WELL_COMPOUND)])
        r_well = retrieval_metrics(Ew, comps)
        r_field = retrieval_metrics(Es, well_of)
        emb_well_all[name] = Ew
        rows.append({"embedding": name, "scope": "well6", "mean_replicate_AP": r_well["mean_AP"],
                     "chance_AP": r_well["chance_AP"], "pair_AUC": r_well["pair_AUC"],
                     "n_queries_valid": r_well["n_queries_valid"]})
        rows.append({"embedding": name, "scope": "site12", "mean_replicate_AP": r_field["mean_AP"],
                     "chance_AP": r_field["chance_AP"], "pair_AUC": r_field["pair_AUC"],
                     "n_queries_valid": r_field["n_queries_valid"]})
        print(name, "well6:", r_well, "site12:", r_field)

    rows.append({"embedding": "manual_904_features", "scope": "well6", "mean_replicate_AP": r904_well["mean_AP"],
                 "chance_AP": r904_well["chance_AP"], "pair_AUC": r904_well["pair_AUC"],
                 "n_queries_valid": r904_well["n_queries_valid"]})
    print("904 baseline well6:", r904_well)

    pd.DataFrame(rows).to_csv(os.path.join(REPORTS, "19_stage11_p0_retrieval_results.csv"), index=False)

    # ---- figure 29d ----
    well_rows = [r for r in rows if r["scope"] == "well6"]
    site_rows = [r for r in rows if r["scope"] == "site12"]
    labels = [r["embedding"].replace("deep_", "").replace("_vits16_384", "-vits16").replace("_vitb14_768", "-vitb14").replace("_vits14_384", "-vits14").replace("_resnet18_512", "-resnet18") for r in well_rows]
    wap = [r["mean_replicate_AP"] for r in well_rows]
    wch = [r["chance_AP"] for r in well_rows]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(labels))
    axes[0].bar(x, wap, color="#4C72B0", label="well-level mean AP")
    for i, (v, c) in enumerate(zip(wap, wch)):
        axes[0].text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=8)
    axes[0].plot(x, wch, "o--", color="#C44E52", label="chance AP")
    axes[0].set_xticks(x); axes[0].set_xticklabels(labels, rotation=18, ha="right", fontsize=8)
    axes[0].set_ylim(0, 1.0); axes[0].set_ylabel("mean replicate AP")
    axes[0].set_title("P0-4 well-level retrieval (6 wells BR00116991)\nsame protocol as Stage-10 904 feature (AP=0.2451 on 648 wells)")
    axes[0].legend(fontsize=8)
    sl = [r["embedding"].replace("deep_", "").replace("_vits16_384", "-vits16").replace("_vitb14_768", "-vitb14").replace("_vits14_384", "-vits14").replace("_resnet18_512", "-resnet18") for r in site_rows]
    sap = [r["mean_replicate_AP"] for r in site_rows]
    sch = [r["chance_AP"] for r in site_rows]
    x2 = np.arange(len(sl))
    axes[1].bar(x2, sap, color="#55A868", label="field-level mean AP")
    for i, (v, c) in enumerate(zip(sap, sch)):
        axes[1].text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=8)
    axes[1].plot(x2, sch, "o--", color="#C44E52", label="chance AP")
    axes[1].set_xticks(x2); axes[1].set_xticklabels(sl, rotation=18, ha="right", fontsize=8)
    axes[1].set_ylim(0, 1.0); axes[1].set_ylabel("mean replicate AP")
    axes[1].set_title("P0-4 field-level retrieval (12 sites)\nsame-well site retrieval")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "29d_retrieval_track_switch.png"), dpi=150)
    fig.savefig(os.path.join(FIG_ROOT, "29d_retrieval_track_switch.png"), dpi=150)
    plt.close(fig)

    summary = {"p0_4_retrieval": {"rows": rows, "note": "Stage-10 904-feature baseline 0.2451 is on 648-well maskA; here 904 re-computed on same 6 wells for direct comparison."}}
    with open(os.path.join(REPORTS, "19_stage11_p0_retrieval_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("DONE. reports/19_stage11_p0_retrieval_results.csv + 29d")


if __name__ == "__main__":
    main()
