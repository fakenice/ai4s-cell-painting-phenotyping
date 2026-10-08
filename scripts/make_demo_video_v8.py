# -*- coding: utf-8 -*-
"""
Build demo_video_shape2target_v8.mp4 -- new-science-storyline render.

Storyline (aligned with the 17-page technical report, mainline sections):
  Problem/task definition -> evaluation protocol -> cross-plate generalization
  & same-compound retrieval -> exploration & negative results (Appendix) ->
  reproducibility.

Real-run evidence:
  - stage11 P3 cross-plate log (BR00116991 -> BR00116992), freshly re-run:
      trt-vs-DMSO cross_plate AUC 0.6825 / AP 0.9107
      compound identity LR top-1 0.331 / top-5 0.512
      prototype discrimination mean AUC 0.985 / sign acc 0.927
  - stage11 P0 structural log (soft-grouped CV), freshly re-run:
      scaffold-grouped pheno+fp AUC 0.4775 (Tanimoto>0.5, 282 groups)
      soft tau=0.6 pheno+fp AUC 0.5222  -> honest generalization floor
      ECFP4 SAR control: DMSO Tanimoto 0.968 (MW p=5.9e-148)
  - Cellpose (cpsam_v2) real inference frames from .demo_capture
      (115 cells, 96.97s CPU) -- kept as real-run evidence.

Render rules (from v3 static-card lineage):
  - All on-screen text in English (no CJK), no watermark, no overflow.
  - Static presentation: NO zoompan; only fade transitions; static figure
    frames are letterboxed with a caption panel.
  - Output 1280x720 / 30fps / H.264 (libx264, crf 20, yuv420p, +faststart).

Usage:  python make_demo_video_v8.py
Output: demo_video_shape2target_v8.mp4 in the repository root.
"""
import os
import json
import subprocess
import time

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- config
W, H = 1280, 720
FPS = 30
CRF = 20
FADE = 0.4                      # fade in/out seconds per clip
BG = (14, 16, 24)               # deep blue-black
BG2 = (22, 26, 38)              # panel
ACCENT = (74, 204, 255)         # cyan accent
ACCENT2 = (255, 178, 74)        # amber accent
WHITE = (240, 244, 255)
GRAY = (150, 160, 180)
TERM_BG = (18, 18, 20)
TERM_FG = (214, 228, 214)

BASE = os.path.dirname(os.path.abspath(__file__))          # github_repo/scripts
ROOT = os.path.dirname(BASE)                                # github_repo/
PROJ = os.path.normpath(os.path.join(ROOT, ".."))           # project root
FIG = os.path.join(ROOT, "reports", "figures")
CAPTURE = os.path.join(ROOT, ".demo_capture")
LOG_DIR = os.path.join(CAPTURE, "logs")
FRAME_DIR = os.path.join(CAPTURE, "frames")
REPORTS = os.path.join(ROOT, "reports")
OUT = os.path.join(ROOT, "demo_video_shape2target_v8.mp4")

BUILD = os.path.join(os.environ.get("MARVIS_TEMP", os.path.join(PROJ, ".v8_build")), "v8_build")
FRAMES = os.path.join(BUILD, "frames")
os.makedirs(FRAMES, exist_ok=True)


def find_font(bold=False):
    cands = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"]
    if not bold:
        cands = [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\DejaVuSans.ttf"]
    for c in cands:
        if os.path.exists(c):
            return c
    return r"C:\Windows\Fonts\arial.ttf"


def get_font(size, bold=False):
    try:
        return ImageFont.truetype(find_font(bold), size)
    except Exception:
        return ImageFont.load_default()


def fit_font(draw, text, font_size, max_w, bold=False, min_size=14):
    """Shrink font size until text fits max_w (anti-overflow)."""
    size = font_size
    while size > min_size:
        f = get_font(size, bold)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return get_font(min_size, bold)


def fit_multiline(draw, lines, font_size, max_w, bold=False, min_size=12):
    """Shrink font size so every line fits max_w."""
    size = font_size
    while size > min_size:
        f = get_font(size, bold)
        if all(draw.textlength(t, font=f) <= max_w for t in lines):
            return f
        size -= 1
    return get_font(min_size, bold)


def wrap_text(draw, text, font, max_w):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def new_frame(bg=BG):
    im = Image.new("RGB", (W, H), bg)
    return im, ImageDraw.Draw(im)


def save_frame(im, seg, idx):
    p = os.path.join(FRAMES, f"seg{seg:02d}_{idx:06d}.png")
    im.save(p)
    return p


def solid_clip(seg, seconds, im):
    """Write `seconds` identical frames for a static card."""
    n = int(round(seconds * FPS))
    for i in range(n):
        save_frame(im, seg, i)
    return n


def card(kicker, title, body, accent=ACCENT, footer=None, seg=0, seconds=6.0):
    """Standard chapter/result card: kicker (small), title, body lines."""
    im, d = new_frame()
    d.rectangle([0, 0, W, 10], fill=accent)
    d.text((70, 110), kicker, font=get_font(30, True), fill=accent)
    tf = fit_font(d, title, 62, W - 140, bold=True)
    d.text((70, 160), title, font=tf, fill=WHITE)
    d.line([70, 230, 330, 230], fill=accent, width=4)
    lines = body if isinstance(body, list) else [body]
    y = 280
    for ln in lines:
        f = fit_font(d, ln, 30, W - 140)
        d.text((70, y), ln, font=f, fill=GRAY)
        y += 46
    if footer:
        ff = fit_font(d, footer, 24, W - 140)
        d.text((70, H - 120), footer, font=ff, fill=(110, 120, 140))
    d.line([0, H - 4, W, H - 4], fill=accent, width=4)
    return solid_clip(seg, seconds, im)


# ---------------------------------------------------------------- terminal frames
TERM_FONT_CAND = [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf",
                  r"C:\Windows\Fonts\DejaVuSansMono.ttf", r"C:\Windows\Fonts\arial.ttf"]


def term_font(size):
    for c in TERM_FONT_CAND:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return get_font(size)


def terminal_clip(logfile, cmdline, seconds, seg, title=None):
    with open(logfile, encoding="utf-8", errors="replace") as fh:
        raw = [l.rstrip("\n") for l in fh]
    lines = [l for l in raw if l.strip()]
    total = int(seconds * FPS)
    row_h = 22
    top = 96 if title else 66
    max_rows = (H - top - 20) // row_h
    n = 0
    for f in range(total):
        visible = min(len(lines), int((f / total) * (len(lines) + max_rows)))
        start = max(0, visible - max_rows)
        shown = lines[start:visible]
        im = Image.new("RGB", (W, H), TERM_BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 38], fill=(60, 62, 68))
        d.text((14, 19), cmdline, font=get_font(16), fill=(235, 235, 235), anchor="lm")
        if title:
            tf = fit_font(d, title, 22, W - 40, bold=True)
            d.text((14, 60), title, font=tf, fill=ACCENT)
        fnt = term_font(16)
        y = top
        for t in shown:
            while t and d.textlength(t, font=fnt) > W - 36:
                t = t[:-1]
            d.text((18, y), t, font=fnt, fill=TERM_FG)
            y += row_h
        if visible < len(lines):
            d.rectangle([16, y - row_h + 5, 26, y - row_h + 19], fill=TERM_FG)
        save_frame(im, seg, f)
        n += 1
    return n


# ---------------------------------------------------------------- cellpose frames
def cellpose_clip(seg, seconds, kind, title):
    meta = json.load(open(os.path.join(FRAME_DIR, "cellpose_meta.json"), encoding="utf-8"))
    gray = np.load(os.path.join(FRAME_DIR, "cellpose_input_gray.npy"))
    masks = np.load(os.path.join(FRAME_DIR, "cellpose_masks.npy"))
    n_cells = meta["n_cells"]
    infer_s = meta["infer_s"]
    g8 = (np.clip(gray, 0, 1) * 255).astype(np.uint8)
    if kind == "input":
        im = Image.fromarray(g8, "L").convert("RGB")
    elif kind == "mask":
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        cmap = plt.get_cmap("tab20")
        col = np.zeros((*masks.shape, 3), dtype=np.uint8)
        for j, u in enumerate(np.unique(masks)):
            if u == 0:
                continue
            c = np.array(cmap((j * 7) % 20)[:3]) * 255
            col[masks == u] = c.astype(np.uint8)
        im = Image.fromarray(col)
    else:  # overlay
        from scipy import ndimage as ndi
        cont = np.zeros_like(masks, dtype=bool)
        for u in np.unique(masks):
            if u == 0:
                continue
            cont |= ndi.binary_erosion(masks == u, iterations=1) ^ (masks == u)
        # upscale contour mask to input resolution (1080x1080)
        cont_img = Image.fromarray((cont.astype(np.uint8) * 255))
        cont_img = cont_img.resize((g8.shape[1], g8.shape[0]), Image.NEAREST)
        bp = np.asarray(Image.fromarray(g8, "L").convert("RGB")).copy()
        bp[np.asarray(cont_img) > 0] = [0, 255, 0]
        im = Image.fromarray(bp)
    # scale to fit 640x460 stage area (keep aspect), center on left
    im.thumbnail((620, 460), Image.LANCZOS)
    frame = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(frame)
    d.text((40, 40), title, font=fit_font(d, title, 34, W - 80, bold=True), fill=WHITE)
    # stage panel
    panel_w, panel_h = 660, 520
    d.rectangle([40, 90, 40 + panel_w, 90 + panel_h], fill=(16, 20, 30))
    frame.paste(im, (40 + (panel_w - im.width) // 2, 90 + (panel_h - im.height) // 2))
    # right side info panel
    xr = 740
    rows = [
        ("Model", "Cellpose cpsam_v2 (CPU)"),
        ("Input", "DNA channel, 1080x1080 -> 256"),
        ("Cells detected", str(n_cells)),
        ("Inference time", f"{infer_s:.1f}s"),
        ("Source", "data/raw/BR00116991"),
    ]
    d.rectangle([xr, 90, W - 40, 90 + panel_h], fill=BG2)
    d.text((xr + 24, 120), "REAL INFERENCE", font=get_font(24, True), fill=ACCENT)
    yy = 170
    for k, v in rows:
        d.text((xr + 24, yy), k, font=get_font(20), fill=GRAY)
        d.text((xr + 24, yy + 28), v, font=fit_font(d, v, 24, W - xr - 64, bold=True), fill=WHITE)
        yy += 86
    n = int(seconds * FPS)
    for i in range(n):
        save_frame(frame, seg, i)
    return n


# ---------------------------------------------------------------- figure frames
def figure_clip(seg, seconds, fig_path, fig_label, caption_lines, crop_top=0):
    """Letterbox figure into 1280x720 with top FIG strip + bottom caption panel."""
    im = Image.open(fig_path).convert("RGB")
    if crop_top > 0:
        w, h = im.size
        im = im.crop((0, crop_top, w, h))
    im.thumbnail((1160, 500), Image.LANCZOS)
    frame = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(frame)
    # top strip
    d.rectangle([0, 0, W, 56], fill=BG2)
    d.text((40, 28), fig_label, font=fit_font(d, fig_label, 26, W - 80, bold=True), fill=ACCENT)
    # figure centered in upper area
    area_top = 56
    area_bot = H - 170
    avail_h = area_bot - area_top
    im2 = im.copy()
    if im2.height > avail_h:
        ratio = avail_h / im2.height
        im2 = im2.resize((int(im2.width * ratio), avail_h), Image.LANCZOS)
    frame.paste(im2, ((W - im2.width) // 2, area_top + (avail_h - im2.height) // 2))
    # caption panel
    d.rectangle([0, H - 170, W, H], fill=BG2)
    d.line([0, H - 170, W, H - 170], fill=(50, 56, 76), width=2)
    yy = H - 156
    for ln in caption_lines:
        f = fit_font(d, ln, 26, W - 80)
        d.text((40, yy), ln, font=f, fill=WHITE)
        yy += 38
    n = int(seconds * FPS)
    for i in range(n):
        save_frame(frame, seg, i)
    return n


# ---------------------------------------------------------------- assembly
def ffmpeg_exe():
    return imageio_ffmpeg.get_ffmpeg_exe()


def encode(segments):
    """segments: list of (seg_id, num_frames). One filter_complex concat."""
    cmd = [ffmpeg_exe(), "-y"]
    inputs = []
    for seg_id, nf in segments:
        cmd += ["-framerate", str(FPS), "-i", os.path.join(FRAMES, f"seg{seg_id:02d}_%06d.png")]
        inputs.append(seg_id)
    flt = []
    for i, (seg_id, nf) in enumerate(segments):
        dur = nf / FPS
        f = (f"[{i}:v]format=yuv420p,"
             f"fade=t=in:st=0:d={FADE},"
             f"fade=t=out:st={max(0.0, dur - FADE):.3f}:d={FADE}[v{i}]")
        flt.append(f)
    concat_in = "".join(f"[v{i}]" for i in range(len(segments)))
    flt.append(f"{concat_in}concat=n={len(segments)}:v=1:a=0[vout]")
    cmd += ["-filter_complex", ";".join(flt), "-map", "[vout]",
            "-c:v", "libx264", "-crf", str(CRF), "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", str(FPS), OUT]
    t0 = time.time()
    print("[encode] running ffmpeg ...")
    rc = subprocess.call(cmd)
    print(f"[encode] rc={rc} in {time.time()-t0:.1f}s -> {OUT}")
    return rc == 0


def main():
    t0 = time.time()
    seg = 1
    segments = []

    # S1 opening card
    im, d = new_frame()
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    d.text((W // 2, 210), "AI4S OPEN INNOVATION 2026", font=get_font(34, True), fill=GRAY, anchor="mm")
    title = "Organ-on-a-Chip Single-Cell Phenotyping"
    tf = fit_font(d, title, 54, W - 120, bold=True)
    d.text((W // 2, 280), title, font=tf, fill=WHITE, anchor="mm")
    d.text((W // 2, 370), "Live real-run demo  ·  open repository  ·  17-page technical report",
           font=get_font(26), fill=ACCENT, anchor="mm")
    d.line([0, H - 4, W, H - 4], fill=ACCENT, width=4)
    n = solid_clip(seg, 6.0, im); segments.append((seg, n)); seg += 1

    # S2 chapter task definition
    n = card("SECTION 1", "TASK DEFINITION",
             ["384-well organ-on-a-chip plates, single-cell morphology",
              "treatment signatures from Cellpose + structure-aware features",
              "readout: trt vs DMSO  ·  compound identity  ·  SAR control"],
             footer="17-page technical report  ·  mainline storyline",
             seg=seg, seconds=6.0); segments.append((seg, n)); seg += 1

    # S3 UMAP figure
    n = figure_clip(seg, 9.0, os.path.join(FIG, "01_umap_overview.png"),
                    "FIG.01 · PHENOTYPIC FINGERPRINTS (UMAP)",
                    ["Compound phenotypic fingerprints, 303 compounds (k=12)",
                     "DMSO negcons and positive controls separated by morphology"],
                    crop_top=0); segments.append((seg, n)); seg += 1

    # S4 chapter evaluation protocol
    n = card("SECTION 3", "EVALUATION PROTOCOL",
             ["cross-plate train/test: BR00116991 -> BR00116992 (zero new downloads)",
              "well-level (plate-aware) plus compound-grouped / scaffold-grouped CV",
              "honest splits: no compound leakage into the training set"],
             seg=seg, seconds=6.0); segments.append((seg, n)); seg += 1

    # S5 soft-grouped CV figure (29b, crop old P0-2 title)
    n = figure_clip(seg, 9.0, os.path.join(FIG, "29b_soft_grouped_cv.png"),
                    "FIG.29b · SCAFFOLD-GROUPED CV",
                    ["Grouped CV drops in-distribution AUC 1.0 -> 0.47-0.53",
                     "soft tau=0.6 pheno+fp AUC 0.5222  ·  honest generalization floor"],
                    crop_top=70); segments.append((seg, n)); seg += 1

    # S6 ECFP4 SAR control figure (29c, crop old P0-3 title)
    n = figure_clip(seg, 8.0, os.path.join(FIG, "29c_fp_distance_distribution.png"),
                    "FIG.29c · ECFP4 AS SAR CONTROL",
                    ["ECFP4 Tanimoto: DMSO vs compounds mean 0.968 (MW p=5.9e-148)",
                     "fingerprint separation is structure, not phenotype -> control only"],
                    crop_top=70); segments.append((seg, n)); seg += 1

    # S7 chapter cross-plate
    n = card("SECTION 4", "CROSS-PLATE GENERALIZATION & RETRIEVAL",
             ["train one plate, test a different plate (same protocol)",
              "same-compound retrieval across plates  ·  prototype discrimination",
              "all numbers below from fresh stage11 re-runs"],
             seg=seg, seconds=6.0); segments.append((seg, n)); seg += 1

    # S8 terminal: stage11 P3 cross-plate real log
    p3log = os.path.join(BUILD, "..", "logs_v8", "stage11_p3_cross_plate.log")
    if not os.path.exists(p3log):
        p3log = os.path.join(LOG_DIR, "stage11_p3_cross_plate.log")
    n = terminal_clip(p3log,
                      "python scripts/stage11_p3_cross_plate.py",
                      14.0, seg,
                      title="STAGE 11 · CROSS-PLATE GENERALIZATION (REAL RUN)"); segments.append((seg, n)); seg += 1

    # S9 cross-plate result card
    n = card("MAIN RESULT", "CROSS-PLATE trt vs DMSO",
             ["train BR00116991 -> test BR00116992  ·  AUC 0.6825  ·  AP 0.9107",
              "compound identity: top-1 0.331  ·  top-5 0.512 (LR 256-class)",
              "prototype discrimination: mean AUC 0.985  ·  sign acc 0.927"],
             accent=ACCENT2, seg=seg, seconds=9.0); segments.append((seg, n)); seg += 1

    # S10 retrieval figure (28c, no old numbering)
    n = figure_clip(seg, 8.0, os.path.join(FIG, "28c_retrieval_replicate_ap.png"),
                    "FIG.28c · SAME-COMPOUND REPLICATE RETRIEVAL",
                    ["replicate AP: raw 904 features vs harmony-corrected",
                     "retrieval AP 0.2451 vs chance 0.0401 -> 6.1x"],
                    crop_top=0); segments.append((seg, n)); seg += 1

    # S11 retrieval result card
    n = card("MAIN RESULT", "SAME-COMPOUND RETRIEVAL",
             ["mean AP 0.2451 vs chance 0.0401  ->  6.1x above chance",
              "cross-plate 260-well retrieval: mean AP 0.416 (10x chance)",
              "ECFP4 fingerprints: SAR control only, not a phenotype input"],
             accent=ACCENT2, seg=seg, seconds=8.0); segments.append((seg, n)); seg += 1

    # S12 chapter appendix / negative results
    n = card("APPENDIX", "EXPLORATION & NEGATIVE RESULTS",
             ["self-supervised CNN AUC 0.0955  ·  Harmony 0.4679 -> 0.4136",
              "deep ResNet18 embeddings: no advantage over handcrafted 904-features",
              "all negative results reported honestly in the appendix"],
             seg=seg, seconds=6.0); segments.append((seg, n)); seg += 1

    # S13-S15 cellpose real inference
    n = cellpose_clip(seg, 5.0, "input", "CELL SEGMENTATION · REAL RUN"); segments.append((seg, n)); seg += 1
    n = cellpose_clip(seg, 5.0, "mask", "CELL SEGMENTATION · REAL RUN"); segments.append((seg, n)); seg += 1
    n = cellpose_clip(seg, 5.0, "overlay", "CELL SEGMENTATION · REAL RUN"); segments.append((seg, n)); seg += 1

    # S16 terminal: stage11 P0 structural (soft-grouped CV) real log
    p0log = os.path.join(BUILD, "..", "logs_v8", "stage11_p0_structural.log")
    if not os.path.exists(p0log):
        p0log = os.path.join(LOG_DIR, "stage11_p0_structural.log")
    n = terminal_clip(p0log,
                      "python scripts/stage11_p0_structural.py",
                      12.0, seg,
                      title="STAGE 11 · SOFT-GROUPED CV & SAR CONTROL (REAL RUN)"); segments.append((seg, n)); seg += 1

    # S17 scaffold CV result card
    n = card("HONEST METHODOLOGY", "SCAFFOLD-GROUPED CV",
             ["scaffold-grouped pheno+fp AUC 0.4775 (Tanimoto>0.5, 282 groups)",
              "soft tau=0.6 pheno+fp AUC 0.5222 (default protocol)",
              "structure-aware features generalize, but far below in-distribution 1.0"],
             accent=ACCENT2, seg=seg, seconds=8.0); segments.append((seg, n)); seg += 1

    # S18 end card
    im, d = new_frame()
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    d.text((W // 2, 260), "REPRODUCIBILITY & THANKS", font=get_font(44, True), fill=WHITE, anchor="mm")
    d.text((W // 2, 340), "scripts + real logs + 17-page report on GitHub Pages",
           font=get_font(26), fill=GRAY, anchor="mm")
    d.text((W // 2, 400), "demo_video_shape2target_v8  ·  live run demo",
           font=get_font(24), fill=ACCENT, anchor="mm")
    d.line([0, H - 4, W, H - 4], fill=ACCENT, width=4)
    n = solid_clip(seg, 6.0, im); segments.append((seg, n)); seg += 1

    print(f"[frames] generated {len(segments)} segments, {sum(x[1] for x in segments)} frames "
          f"({sum(x[1] for x in segments) / FPS:.1f}s)")
    ok = encode(segments)
    print(f"[done] total {time.time()-t0:.1f}s, ok={ok}")
    return ok


if __name__ == "__main__":
    main()
