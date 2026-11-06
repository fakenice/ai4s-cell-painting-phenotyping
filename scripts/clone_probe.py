#!/usr/bin/env python
"""Simulate a fresh clone - the tracked files, no `data/` tree - and run the entry points on it.

    python scripts/clone_probe.py            # build the stand-in clone, test it, remove it
    python scripts/clone_probe.py --keep     # leave it on disk for inspection

The repo's own claims about what a reader sees *without the inputs* are measurements, not
expectations, so they have to be re-measurable by someone who does not have the author's `data/`.
This script copies `git ls-files` (minus `data/`, which is not tracked anyway) into
`<workspace>/_tmp_clone_probe/github_repo`, one level above the workspace's real `data/` so that
`scripts/_paths.py` resolves to a tree that does not exist, and runs three commands there with any
`AI4S_*` override cleared: the unit suite, the checker, and the checker again in the mode a CI or a
fresh clone would use (`--allow-missing-data`).

It then decides instead of just printing. Exit 0 requires that the suite passes, that the plain
checker fails *only* on the three rows whose subject is the absent `data/` tree (a data row that
passes, or a non-data row that fails, is a defect and is reported as one), and that the flagged run
exits 0. Measured 2026-11-06, on this repo:

    29/29 tests pass (1 skipped: paths_data_rule_prefers_the_repo_and_falls_back_to_the_workspace)
    48/51 checks pass      # exactly three FAILs, all data-dependent
    48/48 checks pass (3 skipped, they need data/)        # --allow-missing-data, exit 0

The recorder's labelling tests run here rather than skipping: they read `reports/23`, which is a
tracked artifact, and compare it with the rules in `scripts/record_environment.py` - no environment
and no input data involved. Two things it is not: it is not a `git clone` (no `.git`, so the
history-dependent checks report themselves as skipped, which is one of the outcomes being probed),
and it writes nothing inside the repo.
"""
import argparse
import os
import re
from collections import Counter
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


DATA_ROWS = {
    "the resolved data tree exists (gitignored inputs)",
    "pilot profile tables are present",
    "fetch manifest present",
}


def result_rows(result, category):
    """Validate the printed summary against the actual verdict rows; never trust exit alone."""
    rows = []
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*(PASS|FAIL|SKIP)\s{2,}(.+?)\s*$", line)
        if match:
            name = match.group(2).split("<-")[0].strip()
            if category == "tests":
                name = name.split(":", 1)[0]
            rows.append((match.group(1), name))
    summaries = re.findall(r"^(\d+)/(\d+) " + category + r" pass([^\n]*)$",
                           result.stdout, re.M)
    errors = []
    counts = Counter(kind for kind, _ in rows)
    if len(summaries) != 1 or not counts["PASS"]:
        errors.append("missing, duplicated or empty result summary")
    else:
        passed, ran, suffix = summaries[0]
        skipped = re.search(r"\((\d+) skipped", suffix)
        if (int(passed) != counts["PASS"] or
                int(ran) != counts["PASS"] + counts["FAIL"] or
                int(skipped.group(1) if skipped else 0) != counts["SKIP"]):
            errors.append("summary does not match verdict rows")
    if any(n > 1 for n in Counter(name for _, name in rows).values()):
        errors.append("duplicate verdict rows")
    if "Traceback (most recent call last)" in result.stdout + result.stderr:
        errors.append("unexpected traceback")
    return rows, errors


def run():
    env = {k: v for k, v in os.environ.items()
           if k not in ("AI4S_WORKSPACE", "AI4S_REPO", "AI4S_DATA")}
    env["PYTHONUTF8"] = "1"
    problems = []

    def execute(cmd):
        p = subprocess.run(cmd, cwd=PROBE, env=env, capture_output=True,
                           text=True, encoding="utf-8", timeout=600)
        lines = (p.stdout + p.stderr).strip().splitlines()
        print("$ " + " ".join(cmd))
        for line in lines:
            if worth_showing(line):
                print("   " + line.rstrip())
        print(f"   exit={p.returncode}\n")
        return p, lines

    suite, _ = execute([sys.executable, "tests/test_stage12_units.py"])
    suite_rows, errors = result_rows(suite, "tests")
    problems.extend("suite: " + e for e in errors)
    expected_test_skip = {"test_paths_data_rule_prefers_the_repo_and_falls_back_to_the_workspace"}
    if (suite.returncode != 0 or any(k == "FAIL" for k, _ in suite_rows) or
            {n for k, n in suite_rows if k == "SKIP"} != expected_test_skip):
        problems.append("suite must pass with exactly the one live-data assertion skipped")

    plain, _ = execute([sys.executable, "scripts/check_repo.py"])
    plain_rows, errors = result_rows(plain, "checks")
    problems.extend("plain checker: " + e for e in errors)
    if (plain.returncode != 1 or
            Counter(n for k, n in plain_rows if k == "FAIL") != Counter(DATA_ROWS) or
            any(k == "SKIP" for k, _ in plain_rows)):
        problems.append("plain checker must fail exactly once on each of the three data rows")

    gated, _ = execute([sys.executable, "scripts/check_repo.py", "--allow-missing-data"])
    gated_rows, errors = result_rows(gated, "checks")
    problems.extend("flagged checker: " + e for e in errors)
    if (gated.returncode != 0 or any(k == "FAIL" for k, _ in gated_rows) or
            Counter(n for k, n in gated_rows if k == "SKIP") != Counter(DATA_ROWS)):
        problems.append("flagged checker must skip exactly the three data rows, with no failures")
    if (Counter(n for k, n in plain_rows if k == "PASS") !=
            Counter(n for k, n in gated_rows if k == "PASS")):
        problems.append("non-data PASS rows changed between plain and flagged runs")
    for p in problems:
        print("PROBLEM: " + p)
    return 1 if problems else 0


def worth_showing(line):
    """Print the summary line and every FAIL/SKIP, so the claim 'only the data rows are left'
    is testable rather than asserted."""
    s = line.lstrip()
    return (s.startswith("FAIL") or s.startswith("SKIP") or " tests pass" in line
            or " checks pass" in line)



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
    print("\nverdict: " + ("PASS - the repo is green in a checkout that has no inputs, "
                           "once the data-dependent rows are counted as skips" if rc == 0 else
                           "see the PROBLEM lines above"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
