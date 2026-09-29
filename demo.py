#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo.py — One-command entry point for the AI4S Cell Painting phenotyping pipeline.

Chains the four pipeline stages (01 → 04) and/or prints a lightweight summary of
existing results.

Usage:
    python demo.py                  # lightweight demo: print summary of existing results
    python demo.py --full           # run ALL stages (01 → 04) in order
    python demo.py --stage 1        # run a single stage (1..4)
    python demo.py --list           # list available stages and exit

Lightweight demo mode (default, no flags):
  - Prints a pipeline overview (stage table).
  - For each stage, checks whether its key output files exist under ./reports/.
  - If result CSVs exist, prints a compact summary (row count, columns, head).
  - If no results are found yet, tells the user to run `python demo.py --full`.

All stage scripts read/write relative to the repository root, so run this file
from the repository root:
    python demo.py --full
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")

# stage number -> (script file, title, key outputs)
STAGES = {
    1: {
        "script": "01_phenotypic_profiling.py",
        "title": "Fingerprints & clustering (UMAP + KMeans)",
        "outputs": [
            os.path.join(FIGURES_DIR, "01_umap_overview.png"),
            os.path.join(FIGURES_DIR, "02_compound_fingerprint_clusters.png"),
            os.path.join(REPORTS_DIR, "02_phenotype_results.csv"),
        ],
    },
    2: {
        "script": "02_classification_target.py",
        "title": "Classification baseline + target consistency (XGBoost 5-fold CV)",
        "outputs": [
            os.path.join(FIGURES_DIR, "03_classification_roc_pr.png"),
            os.path.join(REPORTS_DIR, "03_target_validation.csv"),
        ],
    },
    3: {
        "script": "03_enrichment_strength.py",
        "title": "Refined clusters, Fisher enrichment, strength score",
        "outputs": [
            os.path.join(FIGURES_DIR, "04_enrichment_bubble.png"),
            os.path.join(FIGURES_DIR, "04_refined_clusters_umap.png"),
            os.path.join(REPORTS_DIR, "04_enrichment.csv"),
            os.path.join(REPORTS_DIR, "04_phenotypic_strength.csv"),
        ],
    },
    4: {
        "script": "04_cellpose_demo.py",
        "title": "Cellpose single-cell segmentation demo",
        "outputs": [
            os.path.join(FIGURES_DIR, "05_cellpose_segmentation.png"),
            os.path.join(REPORTS_DIR, "05_cellpose_summary.csv"),
        ],
    },
}


def check_file(path):
    """Return 'OK' if the file exists and is non-empty, else 'MISSING'."""
    try:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return "OK"
    except OSError:
        pass
    return "MISSING"


def summarize_csv(path, n_head=3):
    """Print a very compact summary of a CSV (if present)."""
    if not os.path.isfile(path):
        return
    try:
        import pandas as pd
    except ImportError:
        print(f"      (pandas not installed — skipping summary of {os.path.basename(path)})")
        return
    try:
        df = pd.read_csv(path)
        print(f"      {os.path.basename(path)}: {df.shape[0]} rows x {df.shape[1]} cols | "
              f"cols: {', '.join(df.columns[:8])}{' ...' if df.shape[1] > 8 else ''}")
        if n_head and len(df):
            print("      head:")
            print(df.head(n_head).to_string(index=False).replace("\n", "\n      "))
    except Exception as exc:  # noqa: BLE001 - best-effort summary
        print(f"      (could not summarize {os.path.basename(path)}: {exc})")


def print_stage_table():
    print("Pipeline stages (run in order):")
    print("  # | script                         | stage")
    print("  --+-------------------------------+--------------------------------------------")
    for num in sorted(STAGES):
        s = STAGES[num]
        print(f"  {num} | {s['script']:<29} | {s['title']}")
    print()


def run_stage(num):
    script = STAGES[num]["script"]
    script_path = os.path.join(REPO_ROOT, script)
    if not os.path.isfile(script_path):
        print(f"[demo] ERROR: stage script not found: {script_path}")
        return False
    print(f"[demo] Running stage {num}: {script} ({STAGES[num]['title']})")
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [sys.executable, script_path],
        cwd=REPO_ROOT,
        env=env,
    )
    if proc.returncode != 0:
        print(f"[demo] Stage {num} FAILED with exit code {proc.returncode}.")
        return False
    print(f"[demo] Stage {num} finished OK.")
    return True


def lightweight_demo():
    print("=" * 72)
    print("AI4S Cell Painting Phenotyping — lightweight demo")
    print("=" * 72)
    print()
    print_stage_table()

    any_result = False
    for num in sorted(STAGES):
        s = STAGES[num]
        statuses = [(os.path.basename(p), check_file(p)) for p in s["outputs"]]
        ok = all(st == "OK" for _, st in statuses)
        any_result = any_result or ok
        print(f"[Stage {num}] {s['title']}")
        for name, st in statuses:
            print(f"    {st:<8} {name}")
        if ok:
            for p in s["outputs"]:
                if p.lower().endswith(".csv"):
                    summarize_csv(p)
        print()

    print("-" * 72)
    if any_result:
        print("Existing results found. To re-run everything from scratch:")
        print("    python demo.py --full")
    else:
        print("No results found yet. To generate everything from scratch:")
        print("    python demo.py --full")
        print("(Stage 4 requires `pip install cellpose torch`; it is optional.)")
    print("To run only one stage, e.g. stage 3:")
    print("    python demo.py --stage 3")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="One-command entry point for the AI4S Cell Painting phenotyping pipeline."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--full", action="store_true", help="run all stages (01 -> 04) in order")
    group.add_argument("--stage", type=int, choices=sorted(STAGES),
                       help="run a single stage (1..4)")
    group.add_argument("--list", action="store_true", help="list available stages and exit")
    args = parser.parse_args()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    if args.list:
        print_stage_table()
        return

    if args.full:
        print("[demo] Full pipeline run started.")
        ok = True
        for num in sorted(STAGES):
            ok = run_stage(num) and ok
        print()
        if ok:
            print("[demo] All stages finished. See ./reports/ for results and figures.")
        else:
            print("[demo] One or more stages failed — see messages above.")
            sys.exit(1)
        return

    if args.stage is not None:
        ok = run_stage(args.stage)
        sys.exit(0 if ok else 1)
        return

    # default: lightweight demo
    lightweight_demo()


if __name__ == "__main__":
    main()
