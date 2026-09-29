# -*- coding: utf-8 -*-
"""
Build demo_video.mp4 as a REAL-RUN screen-capture style video.

Instead of static slides, this script:
  1. Actually runs src/01_03 scripts and captures their real stdout logs;
  2. Runs a real Cellpose (cpsam_v2) inference on one 1080x1080 DNA well
     (downsampled to 256x256 for CPU speed) and records masks/flows;
  3. Renders real chart frames from the produced result CSVs
     (UMAP points appear one batch at a time, ROC curve grows along
     thresholds, target-class strength bars appear one by one);
  4. Assembles a terminal-scrolling + live-inference + live-plotting video
     at 1280x720 / 30 fps / H.264 with English title bars and cross-fades.

Usage:  python make_demo_video_live.py
Output: demo_video.mp4 in the repository root.

NOTE: this live pipeline needs the project data (data/profiles, data/raw/BR00116991)
and Python deps: pandas numpy scipy scikit-learn matplotlib seaborn umap-learn
xgboost statsmodels tifffile cellpose imageio-ffmpeg pillow.
"""
import os
import sys
import glob
import json
import shutil
import subprocess
import time

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- config
W, H = 1280, 720
FPS = 30
CRF = 20
FADE_FRAMES = int(0.5 * FPS)          # 0.5 s cross-fade between clips
FONT_SIZE = 26
TERM_FONT = r"C:\Windows\Fonts\consola.ttf"   # monospace terminal font

BASE = os.path.dirname(os.path.abspath(__file__))          # github_repo/scripts
ROOT = os.path.dirname(BASE)                                # github_repo/
PROJ = os.path.normpath(os.path.join(ROOT, ".."))           # project root (has src/, data/, reports/)
SRC = os.path.join(PROJ, "src")
FIG = os.path.join(PROJ, "reports", "figures")
OUT = os.path.join(ROOT, "demo_video.mp4")
CAPTURE = os.path.join(ROOT, ".demo_capture")               # intermediate artifacts (gitignored)
LOG_DIR = os.path.join(CAPTURE, "logs")
FRAME_DIR = os.path.join(CAPTURE, "frames")

# ---------------------------------------------------------------- helpers
_LOG_STREAM = None


def log(msg):
    print(msg, flush=True)
    if _LOG_STREAM:
        try:
            _LOG_STREAM.write(str(msg) + "\n")
            _LOG_STREAM.flush()
        except Exception:
            pass


def find_font(bold=False):
    cands = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"]
    if not bold:
        cands = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\DejaVuSans.ttf"]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def get_font(size, path=None):
    path = path or find_font()
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def run_script(name, logfile):
    """Run a project stage script, capture stdout+stderr to logfile, return rc."""
    script = os.path.join(SRC, name)
    log(f"[capture] running {name} ...")
    t0 = time.time()
    with open(logfile, "w", encoding="utf-8", errors="replace") as fh:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        rc = subprocess.call([sys.executable, "-X", "utf8", script],
                             stdout=fh, stderr=subprocess.STDOUT, env=env)
    log(f"[capture] {name} rc={rc} in {time.time()-t0:.1f}s")
    return rc


def capture_cellpose():
    """Real Cellpose inference on single 1080x1080 DNA well -> masks/frames."""
    import tifffile
    from skimage.transform import resize
    from cellpose.models import CellposeModel

    os.makedirs(FRAME_DIR, exist_ok=True)
    raw = os.path.join(PROJ, "data", "raw", "BR00116991", "r01c01f01p01-ch1sk1fk1fl1.tiff")
    log("[capture] Cellpose inference on %s" % os.path.basename(raw))
    img = tifffile.imread(raw).astype(np.float32)
    img_n = (img - img.min()) / (img.max() - img.min() + 1e-8)
    small = resize(img_n, (256, 256), anti_aliasing=True, preserve_range=True)
    model = CellposeModel(gpu=False, pretrained_model="cpsam_v2")
    t0 = time.time()
    out = model.eval(small, channels=[0, 0], diameter=40)
    dt = time.time() - t0
    masks, diams = out[0], out[2]
    n_cells = int(masks.max())
    log(f"[capture] inference done in {dt:.1f}s, {n_cells} cells")
    np.save(os.path.join(FRAME_DIR, "cellpose_input_gray.npy"), img_n)
    np.save(os.path.join(FRAME_DIR, "cellpose_masks.npy"), masks)
    with open(os.path.join(FRAME_DIR, "cellpose_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"n_cells": n_cells, "diam": float(diams[0]), "infer_s": dt}, fh)
    return dt


def capture_plot_frames():
    """Render live-plotting frames from the real result CSVs."""
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve

    os.makedirs(FRAME_DIR, exist_ok=True)

    # UMAP points appear progressively
    prof = pd.read_csv(os.path.join(PROJ, "reports", "02_phenotype_results.csv"))
    n = len(prof)
    step = max(1, n // 26)
    for i in range(step, n + 1, step):
        sub = prof.iloc[:i]
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        ax.scatter(sub["UMAP1"], sub["UMAP2"], c=sub["cluster"], cmap="tab20", s=40, alpha=0.85)
        ax.set_title(f"Compound phenotypic fingerprints - UMAP (k=12)  [{i}/{n} compounds]", fontsize=16)
        ax.set_xlabel("UMAP1"); ax.set_ylabel("UMAP2")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(FRAME_DIR, f"umap_{i:03d}.png"), dpi=100)
        plt.close(fig)
    if n % step:
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        ax.scatter(prof["UMAP1"], prof["UMAP2"], c=prof["cluster"], cmap="tab20", s=40, alpha=0.85)
        ax.set_title(f"Compound phenotypic fingerprints - UMAP (k=12)  [{n}/{n} compounds]", fontsize=16)
        ax.set_xlabel("UMAP1"); ax.set_ylabel("UMAP2")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(FRAME_DIR, f"umap_{n:03d}.png"), dpi=100)
        plt.close(fig)

    # ROC curve grows along thresholds
    pred = pd.read_csv(os.path.join(PROJ, "reports", "03_pred_trt_vs_DMSO.csv"))
    fpr, tpr, _ = roc_curve(pred["y_true"].values, pred["y_prob"].values)
    auc = float(np.trapezoid(tpr, fpr))
    nr = len(fpr)
    step_r = max(1, nr // 22)
    for i in range(step_r, nr + 1, step_r):
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        ax.plot(fpr[:i], tpr[:i], "b-", lw=2)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
        ax.set_title(f"Classification baseline - ROC  [threshold {i}/{nr}]", fontsize=16)
        ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
        ax.text(0.6, 0.15, f"AUC = {auc:.3f}", fontsize=18, bbox=dict(facecolor="white", alpha=0.8))
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(FRAME_DIR, f"roc_{i:03d}.png"), dpi=100)
        plt.close(fig)

    # Target-class strength bars appear one by one
    strength = pd.read_csv(os.path.join(PROJ, "reports", "12_target_class_strength.csv"))
    strength = strength.sort_values("cliff_delta", ascending=False).reset_index(drop=True)
    for i in range(1, len(strength) + 1):
        sub = strength.iloc[:i]
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        colors = ["#d62728" if v > 0.5 else "#ff7f0e" for v in sub["cliff_delta"]]
        ax.barh(range(len(sub)), sub["cliff_delta"], color=colors)
        ax.set_yticks(range(len(sub)))
        ax.set_yticklabels([f"{t[:34]}..." if len(t) > 34 else t for t in sub["target_class"]], fontsize=11)
        ax.set_xlabel("Cliff's delta (phenotypic strength vs others)")
        ax.set_title(f"Target-class phenotypic strength  [{i}/{len(strength)} classes]", fontsize=16)
        ax.axvline(0, color="k", lw=0.8)
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(FRAME_DIR, f"strength_{i:02d}.png"), dpi=100)
        plt.close(fig)


def render_cellpose_frames():
    """Build final 1280x720 frames from real cellpose artifacts."""
    meta = json.load(open(os.path.join(FRAME_DIR, "cellpose_meta.json"), encoding="utf-8"))
    gray = np.load(os.path.join(FRAME_DIR, "cellpose_input_gray.npy"))
    masks = np.load(os.path.join(FRAME_DIR, "cellpose_masks.npy"))
    n_cells = meta["n_cells"]; infer_s = meta["infer_s"]

    # input grayscale
    g8 = (np.clip(gray, 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(g8, "L").convert("RGB").resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.text((W // 2, 30), "Cellpose input - DNA channel (ch1) 1080x1080, downsample to 256 for CPU",
           font=get_font(30), fill=(255, 255, 255), anchor="mm")
    input_np = np.asarray(im, dtype=np.uint8)

    # mask colored
    mask_col = np.zeros((*masks.shape, 3), dtype=np.uint8)
    cmap = plt_cmap = __import__("matplotlib").pyplot.get_cmap("tab20")
    uniq = np.unique(masks)
    for j, u in enumerate(uniq):
        if u == 0:
            continue
        c = np.array(cmap((j * 7) % 20)[:3]) * 255
        mask_col[masks == u] = c.astype(np.uint8)
    mask_img = Image.fromarray(mask_col).resize((W, H), Image.NEAREST)
    d = ImageDraw.Draw(mask_img)
    d.text((W // 2, 30), f"Cellpose masks (cpsam_v2) - {n_cells} cells detected",
           font=get_font(30), fill=(255, 255, 255), anchor="mm")
    mask_np = np.asarray(mask_img, dtype=np.uint8)

    # contour overlay
    from scipy import ndimage as ndi
    cont = np.zeros_like(masks, dtype=bool)
    for u in uniq:
        if u == 0:
            continue
        cont |= ndi.binary_erosion(masks == u, iterations=1) ^ (masks == u)
    cont_img = Image.fromarray((cont * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)
    base = np.asarray(Image.fromarray(g8, "L").convert("RGB").resize((W, H), Image.LANCZOS), dtype=np.uint8).copy()
    base[np.asarray(cont_img) > 0] = [0, 255, 0]
    overlay = Image.fromarray(base)
    d = ImageDraw.Draw(overlay)
    d.text((W // 2, 30), f"Cellpose contours on DNA channel - {n_cells} cells, {infer_s:.1f}s CPU inference",
           font=get_font(30), fill=(255, 255, 255), anchor="mm")
    overlay_np = np.asarray(overlay, dtype=np.uint8)
    return input_np, mask_np, overlay_np


def terminal_frames(logfile, cmdline, seconds, fg=(214, 228, 214)):
    """Render a terminal window with real log lines scrolling in."""
    with open(logfile, encoding="utf-8", errors="replace") as fh:
        lines = [l.rstrip("\n") for l in fh if l.strip()]
    total = int(seconds * FPS)
    n_lines = len(lines)
    # max visible text rows in the terminal body
    rows_h = H - 140
    row_h = 22
    max_rows = rows_h // row_h
    frames = []
    for f in range(total):
        # how many lines are visible at this frame (smooth typing then scroll)
        visible = min(n_lines, int((f / total) * (n_lines + max_rows)) )
        start = max(0, visible - max_rows)
        shown = lines[start:visible]

        # terminal background + title bar
        frame = Image.new("RGB", (W, H), (18, 18, 20))
        d = ImageDraw.Draw(frame)
        d.rectangle([0, 0, W, 34], fill=(60, 62, 68))
        d.text((14, 17), cmdline, font=get_font(18), fill=(235, 235, 235), anchor="lm")
        # body text
        font = ImageFont.truetype(TERM_FONT, 18) if os.path.exists(TERM_FONT) else get_font(18)
        y = 52
        for i, t in enumerate(shown):
            d.text((18, y), t[:110], font=font, fill=fg)
            y += row_h
        # cursor
        if visible < n_lines:
            d.rectangle([16, y - row_h + 4, 24, y - row_h + 18], fill=(214, 228, 214))
        frames.append(np.asarray(frame, dtype=np.uint8))
    return frames


def text_frame(lines, seconds, bg=(10, 12, 16), fg=(240, 240, 240), title=None):
    """Simple full-screen text frame(s)."""
    total = int(seconds * FPS)
    frames = []
    font = get_font(30)
    font_s = get_font(22)
    for _ in range(total):
        frame = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(frame)
        if title:
            d.text((W // 2, 50), title, font=get_font(38), fill=(255, 255, 255), anchor="mm")
            y = 130
        else:
            y = 120
        for t in lines:
            d.text((W // 2, y), t, font=font, fill=fg, anchor="mm")
            y += 52
        d.text((W // 2, H - 60), "AI4S Open Innovation 2026 - AI for Life Science",
               font=font_s, fill=(150, 150, 160), anchor="mm")
        frames.append(np.asarray(frame, dtype=np.uint8))
    return frames


def png_clip(path, seconds, letterbox=True):
    """Convert a PNG frame to a static clip of `seconds`."""
    total = int(seconds * FPS)
    im = Image.open(path).convert("RGB")
    if letterbox:
        im.thumbnail((W, H - 0), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H), (10, 12, 16))
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        arr = np.asarray(canvas, dtype=np.uint8)
    else:
        arr = np.asarray(im.resize((W, H), Image.LANCZOS), dtype=np.uint8)
    return np.repeat(arr[None, ...], total, axis=0)


def png_sequence_clip(paths, seconds):
    """Play a sequence of PNG frames, each shown for seconds/len."""
    total = int(seconds * FPS)
    arrs = []
    per = max(1, total // len(paths))
    for p in paths:
        im = Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
        arr = np.asarray(im, dtype=np.uint8)
        arrs.extend([arr] * per)
    while len(arrs) < total:
        arrs.append(arrs[-1])
    return np.stack(arrs[:total])


def encode(clips, out_path):
    """Stream raw RGB frames into ffmpeg (libx264, yuv420p)."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(CRF),
           "-preset", "medium", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    prev_tail = None
    total = 0
    for i, clip in enumerate(clips):
        n = len(clip)
        for f in range(n):
            frame = clip[f].copy()
            if i > 0 and f < FADE_FRAMES:
                alpha = (f + 1) / FADE_FRAMES
                frame = (prev_tail[f].astype(np.float32) * (1 - alpha)
                         + clip[f].astype(np.float32) * alpha).astype(np.uint8)
            proc.stdin.write(frame.tobytes())
            total += 1
        prev_tail = clip[-FADE_FRAMES:]
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with code {proc.returncode}")
    return total


# ---------------------------------------------------------------- pipeline
def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(FRAME_DIR, exist_ok=True)

    log("== Stage 1: capture real script runs ==")
    global _LOG_STREAM
    _LOG_STREAM = open(os.path.join(LOG_DIR, "04.log"), "w", encoding="utf-8")
    try:
        run_script("01_phenotypic_profiling.py", os.path.join(LOG_DIR, "01.log"))
        run_script("02_classification_target.py", os.path.join(LOG_DIR, "02.log"))
        run_script("03_enrichment_strength.py", os.path.join(LOG_DIR, "03.log"))
        capture_cellpose()
    finally:
        _LOG_STREAM.close()
        _LOG_STREAM = None
    log("== Stage 2: render live chart frames ==")
    capture_plot_frames()

    log("== Stage 3: assemble video ==")
    clips = []

    # opening title
    clips.append(text_frame([
        "AI4S Open Innovation 2026",
        "Cell Painting Morphological Profiling",
        "Real run: terminal logs, Cellpose inference, live charts",
    ], 3.0, title="Live Demo - Real Execution Screen"))

    # terminal scrolls (real stdout)
    clips.append(terminal_frames(os.path.join(LOG_DIR, "01.log"),
                                 "python src/01_phenotypic_profiling.py", 9.0))
    clips.append(terminal_frames(os.path.join(LOG_DIR, "02.log"),
                                 "python src/02_classification_target.py", 9.0))
    clips.append(terminal_frames(os.path.join(LOG_DIR, "03.log"),
                                 "python src/03_enrichment_strength.py", 7.0))
    clips.append(terminal_frames(os.path.join(LOG_DIR, "04.log"),
                                 "python src/04_cellpose_demo.py", 6.0))

    # cellpose live inference frames
    clips.append(text_frame([
        "Loading Cellpose model (cpsam_v2) ...",
        "Input: DNA channel 1080x1080 -> 256x256 for CPU inference",
    ], 3.0, title="Stage 04 - Live Cellpose Segmentation"))
    input_np, mask_np, overlay_np = render_cellpose_frames()
    clips.append(np.repeat(input_np[None, ...], int(2.5 * FPS), axis=0))
    clips.append(np.repeat(mask_np[None, ...], int(2.5 * FPS), axis=0))
    clips.append(np.repeat(overlay_np[None, ...], int(3.0 * FPS), axis=0))

    # live chart frames (real data)
    clips.append(text_frame([
        "Charts rendered from real result CSVs:",
        "02_phenotype_results.csv / 03_pred_trt_vs_DMSO.csv / 12_target_class_strength.csv",
    ], 3.0, title="Live Plotting - Real Data"))

    umap_paths = sorted(glob.glob(os.path.join(FRAME_DIR, "umap_*.png")))
    roc_paths = sorted(glob.glob(os.path.join(FRAME_DIR, "roc_*.png")))
    str_paths = sorted(glob.glob(os.path.join(FRAME_DIR, "strength_*.png")))
    clips.append(png_sequence_clip(umap_paths, 8.0))
    clips.append(png_sequence_clip(roc_paths, 7.0))
    clips.append(png_sequence_clip(str_paths, 6.0))

    # closing
    clips.append(text_frame([
        "Full pipeline: profiles -> UMAP -> XGBoost CV -> enrichment -> Cellpose",
        "All frames captured from real script execution on this machine.",
    ], 3.0, title="End of Live Demo"))

    total = encode(clips, OUT)
    duration = total / FPS
    size_mb = os.path.getsize(OUT) / 1e6
    log(f"\nWrote {OUT}")
    log(f"Frames={total}, Duration={duration:.1f}s, Size={W}x{H}, FPS={FPS}")
    log(f"File size={size_mb:.2f} MB")


if __name__ == "__main__":
    main()
