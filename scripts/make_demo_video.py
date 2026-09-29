# -*- coding: utf-8 -*-
"""
Build demo_video.mp4 from the 7 result figures.

- Resizes each PNG to 1280x720 (letterboxed, LANCZOS)
- Overlays an English title bar (Arial Bold)
- Encodes 7 clips x 6 s at 30 fps with 0.5 s cross-fade transitions
- Encoder: ffmpeg (libx264) via the imageio-ffmpeg static binary

Usage: python make_demo_video.py
Output: demo_video.mp4 (1280x720, ~42 s, 30 fps) in the repository root
"""
import os
import subprocess
import sys

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

# ---------- Configuration ----------
W, H = 1280, 720
FPS = 30
SECONDS_PER_CLIP = 6
FADE_FRAMES = int(0.5 * FPS)          # 15 frames cross-fade
CLIP_FRAMES = SECONDS_PER_CLIP * FPS  # 180 frames per clip
CRF = 20

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)                      # github_repo/
FIG_DIR = os.path.join(ROOT, "..", "reports", "figures")
OUT = os.path.join(ROOT, "demo_video.mp4")

TITLES = [
    "Morphological Profiling — UMAP Overview (DMSO vs Treatments)",
    "Compound Phenotypic Fingerprints — KMeans Clusters (k = 12)",
    "Classification Baseline — XGBoost 5-Fold CV (AUC 0.768)",
    "Cluster-Target Enrichment — Fisher Exact + BH Correction",
    "Refined Phenotype Clusters — UMAP by Cluster",
    "Cellpose Segmentation Demo — Cell Painting DNA Channel",
    "Target-Class Phenotypic Strength — Microtubule / Src / CDK",
]
PNGS = [
    "01_umap_overview.png",
    "02_compound_fingerprint_clusters.png",
    "03_classification_roc_pr.png",
    "04_enrichment_bubble.png",
    "04_refined_clusters_umap.png",
    "05_cellpose_segmentation.png",
    "12_target_class_strength.png",
]


def find_font():
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def make_title_frame(png_path, title):
    """Letterbox the image to 1280x720 and overlay an English title bar."""
    img = Image.open(png_path).convert("RGB")
    img.thumbnail((W, H - 90), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (12, 12, 14))
    x = (W - img.width) // 2
    y = 60 + (H - 90 - img.height) // 2
    canvas.paste(img, (x, y))

    # Semi-transparent title bar (top)
    bar = Image.new("RGBA", (W, 110), (0, 0, 0, 150))
    canvas.paste(bar, (0, 0), bar)

    draw = ImageDraw.Draw(canvas)
    font_path = find_font()
    size = 34 if len(title) <= 58 else 28
    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    draw.text((W // 2, 55), title, font=font, fill=(255, 255, 255), anchor="mm")
    return np.asarray(canvas, dtype=np.uint8)


def encode(clips, out_path):
    """Stream raw RGB frames into ffmpeg (libx264, yuv420p)."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", str(CRF), "-preset", "medium",
        out_path,
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    prev_tail = None
    total = 0
    for i, clip in enumerate(clips):
        for f in range(CLIP_FRAMES):
            frame = clip[f].copy()
            if i > 0 and f < FADE_FRAMES:
                alpha = (f + 1) / FADE_FRAMES
                frame = (
                    prev_tail[f].astype(np.float32) * (1 - alpha)
                    + clip[f].astype(np.float32) * alpha
                ).astype(np.uint8)
            proc.stdin.write(frame.tobytes())
            total += 1
        prev_tail = clip[-FADE_FRAMES:]
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with code {proc.returncode}")
    return total


def main():
    clips = []
    for png, title in zip(PNGS, TITLES):
        path = os.path.join(FIG_DIR, png)
        if not os.path.exists(path):
            print(f"[SKIP] missing: {path}", file=sys.stderr)
            continue
        frame = make_title_frame(path, title)
        clips.append(np.repeat(frame[None, ...], CLIP_FRAMES, axis=0))
        print(f"[OK] {png} -> {len(clips)} clip(s) so far")

    if len(clips) < 2:
        raise SystemExit("Need at least 2 figures to build a video.")

    total = encode(clips, OUT)
    duration = total / FPS
    print(f"\nWrote {OUT}")
    print(f"Frames={total}, Duration={duration:.1f}s, Size={W}x{H}, FPS={FPS}")
    print(f"Titles={len(clips)}, ClipLen={SECONDS_PER_CLIP}s, Fade={FADE_FRAMES / FPS:.1f}s")


if __name__ == "__main__":
    main()
