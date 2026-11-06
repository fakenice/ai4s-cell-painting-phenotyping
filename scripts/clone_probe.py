#!/usr/bin/env python
"""Simulate a fresh clone - the tracked files, no `data/` tree - and run both entry points on it.

    python scripts/clone_probe.py            # build the stand-in clone, test it, remove it
    python scripts/clone_probe.py --keep     # leave it on disk for inspection

The repo's own claims about what a reader sees *without the inputs* are measurements, not
expectations, so they have to be re-measurable by someone who does not have the author's `data/`.
This script copies `git ls-files` (minus `data/`, which is not tracked anyway) into
`<workspace>/_tmp_clone_probe/github_repo`, one level above the workspace's real `data/` so that
`scripts/_paths.py` resolves to a tree that does not exist, and runs the unit suite and the
checker there with any `AI4S_*` override cleared.

Two things it is not: it is not a `git clone` (no `.git`, so the history-dependent checks report
themselves as skipped, which is one of the outcomes being probed), and it writes nothing inside the
repo. The expected shape of the output, measured 2026-11-06:

    20/20 tests pass (1 skipped: paths_data_rule_prefers_the_repo_and_falls_back_to_the_workspace)
    46/49 checks pass      # three FAILs, all data-dependent, each naming the path it looked at
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths  # noqa: E402

REPO = _paths.REPO
PROBE = os.path.join(os.path.dirname(REPO), "_tmp_clone_probe", "github_repo")


def build():
    """Copy the tracked files (working-tree contents, so an uncommitted stage can be probed)."""
    tracked = subprocess.run(["git", "-C", REPO, "ls-files"], capture_output=True,
                             text=True, check=True).stdout.split("\n")
    files = [f for f in tracked if f and not f.startswith("data/")]
    if os.path.exists(PROBE):
        shutil.rmtree(PROBE)
    n = 0
    for rel in files:
        src = os.path.join(REPO, rel.replace("/", os.sep))
        if not os.path.isfile(src):
            continue                       # tracked but deleted locally: nothing to copy
        dst = os.path.join(PROBE, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        n += 1
    return n


def run():
    env = {k: v for k, v in os.environ.items()
           if k not in ("AI4S_WORKSPACE", "AI4S_REPO", "AI4S_DATA")}
    env["PYTHONUTF8"] = "1"
    rc = 0
    for cmd in (["python", "tests/test_stage12_units.py"], ["python", "scripts/check_repo.py"]):
        p = subprocess.run(cmd, cwd=PROBE, env=env, capture_output=True, text=True)
        tail = (p.stdout + p.stderr).strip().splitlines()
        print("$ " + " ".join(cmd))
        for line in tail:
            if re_show(line):
                print("   " + line.rstrip())
        print(f"   exit={p.returncode}\n")
        rc = rc or p.returncode      # non-zero is the *expected* result without the inputs
    return rc


def re_show(line):
    """Print the summary line and every FAIL, so the claim 'only the data rows fail' is testable."""
    return line.lstrip().startswith("FAIL") or " tests pass" in line or " checks pass" in line


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="leave the stand-in clone on disk")
    a = ap.parse_args(argv)
    print(f"cloned {build()} files to {PROBE}\n")
    rc = run()
    if a.keep:
        print(f"kept at {PROBE}")
    else:
        shutil.rmtree(PROBE)
        print(f"removed {PROBE}")
    print("\n(Exit 1 here is the expected outcome: the checker has no inputs to verify against.)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
