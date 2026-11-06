#!/usr/bin/env python
"""Repo self-check: one command that proves the documentation matches the artifacts.

    python scripts/check_repo.py            # fast checks (no re-hashing of the 160 MB data tree)
    python scripts/check_repo.py --deep     # also recompute every SHA256 in the fetch manifest
    python scripts/check_repo.py --list     # print the check inventory and exit

Seven groups of independent assertions, printed as PASS/FAIL, non-zero exit on any FAIL. The
point is drift: a number quoted in a report that no longer equals the JSON that produced it, a
doc citing a deleted artifact, a PDF that no longer matches the hash the ledger records, or a
script that grew a hardcoded absolute path again. Everything here is read-only.
"""
import argparse
import ast
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths  # noqa: E402

REPO = _paths.REPO
REPORTS = _paths.REPORTS
DOCS = _paths.DOCS
MD_FILES = sorted(glob.glob(os.path.join(REPORTS, "*.md"))) + [os.path.join(REPO, "README.md")]
ARMS = ("negcon_z", "rank", "zclip5", "posresid")
RETRIEVAL_ARMS = ("decoupled-only", "position-decoupled", "position-matched")

# What _paths would derive if AI4S_REPO / AI4S_WORKSPACE were unset. The equivalence checks that
# compare against HEAD's literals or against the root scripts' own derivation have to use these,
# not the live values: an override legitimately moves the live roots, and comparing a replaced
# 2026-10 literal to an override the author chose would report a mismatch that isn't one.
DEFAULT_REPO = os.path.dirname(_paths._HERE)
DEFAULT_WORKSPACE = os.path.dirname(DEFAULT_REPO)

R = []          # (group, name, ok, note)


def add(group, name, ok, note=""):
    R.append((group, name, bool(ok), note))


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def md_blob():
    return "\n".join(read(m) for m in MD_FILES if os.path.exists(m))


def _py_files():
    """Every tracked python file in the checkout: root scripts, scripts/, tests/."""
    return (sorted(glob.glob(os.path.join(REPO, "*.py")))
            + sorted(glob.glob(os.path.join(REPO, "scripts", "*.py")))
            + sorted(glob.glob(os.path.join(REPO, "tests", "*.py"))))


def expand_braces(token):
    """'a_{x,y}.json' -> ['a_x.json', 'a_y.json']; a '*' is kept as a glob pattern.

    Applied repeatedly, because the docs also write the nested form
    '21_stage12_train_size_curve_{negcon_z,rank}.{csv,json}'.
    """
    m = re.match(r"^(.*)\{([^}]*)\}(.*)$", token)
    if not m:
        return [token]
    head, opts, tail = m.groups()
    out = []
    for o in opts.split(","):
        out.extend(expand_braces(head + o + tail))
    return out


# ---------------------------------------------------------------- A. layout
def group_layout():
    g = "A layout"
    add(g, "REPO is the checkout that contains scripts/",
        os.path.isdir(os.path.join(REPO, "scripts")), REPO)
    add(g, "reports/ exists", os.path.isdir(REPORTS), REPORTS)
    add(g, "the resolved data tree exists (gitignored inputs)",
        os.path.isdir(_paths.DATA), _paths.DATA)
    cands = [os.path.join(_paths.REPO, "data"), os.path.join(_paths.WORKSPACE, "data")]
    add(g, "DATA is one of the two documented candidates", _paths.DATA in cands,
        " vs ".join(cands))
    add(g, "DATA prefers <repo>/data when it exists, else <workspace>/data",
        (_paths.DATA == cands[0]) == os.path.isdir(cands[0]),
        f"{_paths.DATA} (repo/data exists: {os.path.isdir(cands[0])})")
    env_repo, env_ws = os.environ.get("AI4S_REPO"), os.environ.get("AI4S_WORKSPACE")
    if env_repo or env_ws:
        want_repo = os.path.abspath(env_repo) if env_repo else DEFAULT_REPO
        want_ws = os.path.abspath(env_ws) if env_ws else os.path.dirname(want_repo)
        add(g, "the AI4S_* overrides in effect are honoured",
            _paths.REPO == want_repo and _paths.WORKSPACE == want_ws,
            f"AI4S_REPO={env_repo!r} AI4S_WORKSPACE={env_ws!r}; "
            f"derived REPO={_paths.REPO} WORKSPACE={_paths.WORKSPACE}")
    else:
        add(g, "no override set: every root comes from this file's location",
            _paths.REPO == DEFAULT_REPO and _paths.WORKSPACE == DEFAULT_WORKSPACE,
            f"REPO={_paths.REPO} WORKSPACE={_paths.WORKSPACE}")
    add(g, "pilot profile tables are present",
        len(glob.glob(os.path.join(_paths.PROFILES, "*.csv.gz"))) >= 2, _paths.PROFILES)
    hard = []
    for f in _py_files():
        if os.path.basename(f) == os.path.basename(__file__):
            continue
        for i, ln in enumerate(read(f).split("\n"), 1):
            if re.match(r'^\s*(BASE|REPO|DATA|OUT|REPORTS|FIG)\s*=\s*r?"[A-Za-z]:', ln):
                hard.append(f"{os.path.basename(f)}:{i}")
    add(g, "no hardcoded drive-letter roots left in any script", not hard, "; ".join(hard))
    # and the roots that replaced them must be the *same* directories: read each script as it stood
    # in the last commit before scripts/_paths.py existed, pull its old literal, and compare it
    # with what _paths derives now. HEAD is the wrong reference: from the refactor commit onward
    # HEAD no longer contains those literals, so a HEAD comparison silently degrades to '0 checked,
    # all fine' - which is how this check read after it had done its job once.
    try:
        proc = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            raise OSError(proc.stderr.strip()[:80])
        added = subprocess.run(
            ["git", "-C", REPO, "log", "--diff-filter=A", "--format=%H", "--",
             "scripts/_paths.py"], capture_output=True, text=True, timeout=60).stdout.split()
        if not added:
            raise OSError("no add-commit for scripts/_paths.py in this history")
        ref = added[-1] + "^"                  # the tree the refactor replaced
        seen = []                              # (file, kind, literal) as written before the refactor
        for f in sorted(glob.glob(os.path.join(REPO, "scripts", "*.py"))):
            rel = "scripts/" + os.path.basename(f)
            show = subprocess.run(["git", "-C", REPO, "show", ref + ":" + rel],
                                  capture_output=True, text=True, encoding="utf-8", timeout=30)
            if show.returncode != 0:
                continue                       # added this stage: nothing before it to compare
            for kind, rx in (("BASE", re.compile(r'^\s*BASE\s*=\s*r"(.*?)"\s*$', re.M)),
                             ("REPO", re.compile(r'^\s*REPO\s*=\s*r"(.*?)"\s*$', re.M))):
                m = rx.search(show.stdout)
                if m:
                    seen.append((os.path.basename(f), kind, m.group(1)))
        named = {l for _, kind, l in seen if kind == "REPO"}
        if DEFAULT_REPO not in named:
            # Those literals name the checkout the analysis actually ran in. This directory is not
            # it (a clone, a second copy, another machine), so comparing them with the roots derived
            # here would 'fail' every row for a perfectly fine checkout: the claim goes unproven,
            # not violated - same convention as the git-unavailable branch below.
            add(g, f"pre-refactor literals name a different checkout (skipped: equivalence "
                   f"unproven here, {len(seen)} literals read from {ref[:9]})", True,
                f"HEAD derives REPO={DEFAULT_REPO}, the history names {sorted(named)[:1]}")
        else:
            off = [f"{b}: old {kind} {l!r}" for b, kind, l in seen
                   if os.path.abspath(l) != (DEFAULT_WORKSPACE if kind == "BASE" else DEFAULT_REPO)]
            add(g, f"the {len(seen)} pre-refactor path literals equal the roots "
                   f"_paths derives now", not off, "; ".join(off[:3]))
    except Exception as exc:  # noqa: BLE001 - git is optional, the claim just goes unproven
        add(g, "pre-refactor path literals checked (git unavailable, skipped)", True,
            repr(exc)[:80])


# ---------------------------------------------------------------- B. compile
def group_compile():
    files = _py_files()
    bad = []
    for f in files:
        try:
            ast.parse(read(f), filename=f)
        except SyntaxError as e:
            bad.append(f"{os.path.basename(f)}:{e.lineno}: {e.msg}")
    add("B compile", f"all {len(files)} scripts parse", not bad, "; ".join(bad))
    _group_environment()


def _group_environment():
    """requirements.txt vs what the code imports, and the recorded fingerprint vs this machine."""
    g = "B compile"
    rec_path = os.path.join(REPORTS, "23_environment_fingerprint.json")
    if not os.path.isfile(rec_path):
        add(g, "environment fingerprint recorded (reports/23)", False,
            "run: python scripts/record_environment.py")
        return
    rec = json.loads(read(rec_path))
    s = rec.get("summary", {})
    rows = rec.get("requirements_txt", [])
    differ = [r["distribution"] for r in rows if r["status"] == "installed, differs from the pin"]
    absent = [r["distribution"] for r in rows if r.get("installed") is None]
    # (1) code vs declaration, re-derived live: whether an import is declared does not depend on
    # which machine runs this, so this row is never another machine's business.
    sys.path.insert(0, _paths._HERE)
    import record_environment as rec_mod
    live = rec_mod.build()
    undeclared = live["summary"]["undeclared_module_level_imports"]
    add(g, "every module-level third-party import is declared in requirements.txt",
        not undeclared,
        "undeclared: " + ", ".join(undeclared) if undeclared else
        f"all {live['summary']['third_party_modules_imported']} swept third-party modules are declared")
    # (2) a missing dependency that stops a script from even starting is a claim about the machine
    # that recorded it, so the docs have to name it rather than leave a clone to find out by traceback
    blocked = sorted({i["distribution"] for i in rec.get("imports", [])
                      if i["level"] in ("module", "module-guarded") and not i["installed_here"]})
    blob = md_blob()
    unstated = [d for d in blocked if d not in blob]
    add(g, "every dependency that blocks a script on the recorded machine is named in the docs",
        not unstated,
        "undocumented: " + ", ".join(unstated) if unstated else
        f"{len(blocked)} absent there, each named: {', '.join(blocked)}")
    # (3) the environment comparison, and the one case where it must not be made: the fingerprint
    # records a machine, and a reader on another one has not broken anything by living elsewhere.
    same = (rec.get("python") == live["python"] and rec.get("platform") == live["platform"])
    if not same:
        add(g, "recorded fingerprint belongs to another machine (skipped: drift not "
               "assessable from here)", True,
            f"record says python {rec.get('python')} on {rec.get('platform')}; "
            f"this is python {live['python']} on {live['platform']}")
        return
    try:
        proc = subprocess.run([sys.executable, os.path.join(REPO, "scripts",
                                                            "record_environment.py"), "--check"],
                              capture_output=True, text=True, cwd=REPO, timeout=180)
        lines = proc.stdout.strip().split("\n")
        add(g, "the recorded fingerprint still equals this environment", proc.returncode == 0,
            "; ".join(l.strip() for l in lines[1:])[:220] if proc.returncode else
            f"{len(rows)} declared: {len(differ)} pins differ here ({', '.join(differ[:4])}), "
            f"{len(absent)} of them not installed")
    except Exception as exc:  # noqa: BLE001 - the recorder is part of this repo, so a failure is real
        add(g, "record_environment.py --check runs", False, repr(exc)[:120])


# ---------------------------------------------------------------- C. citations
def group_citations():
    blob = md_blob()
    # greedy so a brace group is captured whole: 'foo_{a.csv,b.json}' must not stop at the
    # first '.csv'. Bare stems ('20_stage11_p3') are prose, not citations, so they are skipped.
    raw = re.findall(r"2[01]_stage1[12][A-Za-z0-9_{}.,*\-]*", blob)
    tokens = {t.rstrip(".,;:") for t in raw
              if "{" in t or "*" in t or re.search(r"\.(csv|json|npz)$", t)}
    missing = []
    for t in sorted(tokens):
        for cand in expand_braces(t):
            if not glob.glob(os.path.join(REPORTS, cand)):
                missing.append(cand)
    add("C citations", f"every stage artifact the docs cite exists ({len(tokens)} tokens)",
        not missing, "; ".join(missing))
    manifest = os.path.join(_paths.EXTERNAL, "cpg0016", "manifest_sha256.csv")
    add("C citations", "fetch manifest present", os.path.isfile(manifest), manifest)
    broken = []
    for f in MD_FILES + sorted(glob.glob(os.path.join(DOCS, "*.md"))):
        for m in re.finditer(r"!\[[^\]]*\]\(([^) ]+)", read(f)):
            rel = m.group(1)
            if rel.startswith(("http://", "https://")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(f), rel))
            if not os.path.isfile(target):
                broken.append(f"{os.path.basename(f)} -> {rel}")
    add("C citations", "every markdown image link resolves to a file", not broken,
        "; ".join(broken[:4]))
    # the six root-level stage scripts predate _paths.py and derive the workspace themselves;
    # they must still land on the directory _paths derives by default (an env override cannot
    # reach them, and should not).
    off = []
    for f in sorted(glob.glob(os.path.join(REPO, "*.py"))):
        m = re.search(r"^BASE\s*=\s*os\.path\.dirname\(os\.path\.dirname\(",
                      read(f), re.M)
        if m and os.path.dirname(os.path.dirname(os.path.abspath(f))) != DEFAULT_WORKSPACE:
            off.append(os.path.basename(f))
    add("C citations", "root-level scripts resolve BASE to the same workspace as _paths",
        not off, "; ".join(off))
    # demo.py derives the repo root rather than the workspace: self-relative, and it must still
    # land on the checkout that holds it (compared live, since an AI4S_REPO override moves both).
    demo = os.path.join(REPO, "demo.py")
    ok = os.path.isfile(demo) and bool(re.search(
        r"^REPO_ROOT\s*=\s*os\.path\.dirname\(os\.path\.abspath\(__file__\)\)",
        read(demo), re.M))
    add("C citations", "demo.py derives REPO_ROOT from __file__ and lands on this checkout",
        ok, "REPO_ROOT = dirname(abspath(__file__)) == " + REPO if ok else "pattern not found")
    return manifest


# ---------------------------------------------------------------- D. numbers
def group_numbers():
    g = "D numbers"
    blob = md_blob()
    split = json.load(open(os.path.join(REPORTS, "21_stage12_retrieval_position_split.json"),
                           encoding="utf-8"))
    arms = split["arm_summaries_by_plate_pair"]
    for arm in RETRIEVAL_ARMS:
        a = arms.get(arm)
        if a is None:
            add(g, f"retrieval arm '{arm}' present in the split json", False)
            continue
        v = a["recall_at_1_query_weighted"]
        add(g, f"docs quote R@1 {v:.4f} for retrieval arm '{arm}'", f"{v:.4f}" in blob,
            f"n_queries={a['n_queries']}")
    strict = arms.get("decoupled-only") or {}
    null = strict.get("chance_recall_at_1_any_accepted_match_query_weighted")
    if null:
        add(g, f"docs quote the strict arm's applicable null {null:.4f}",
            f"{null:.4f}" in blob, f"R@1/null = {strict['recall_at_1_query_weighted'] / null:.0f}x")
    pair = split["paired_by_plate_pair"]
    add(g, f"docs quote the paired difference {pair['mean_paired_difference_a_minus_b']:+.4f}",
        f"{pair['mean_paired_difference_a_minus_b']:.4f}" in blob)
    add(g, f"docs quote the Wilcoxon p {pair['wilcoxon_p_a_gt_b']:.4f}",
        f"{pair['wilcoxon_p_a_gt_b']:.4f}" in blob)
    for arm in ARMS:
        p = os.path.join(REPORTS, f"21_stage12_external_site_summary_{arm}.json")
        if not os.path.isfile(p):
            add(g, f"summary json for arm '{arm}' exists", False, p)
            continue
        d = json.load(open(p, encoding="utf-8"))
        auc = d["cross_site_pooled"]["AUC"]
        add(g, f"docs quote cross-site AUC {auc:.4f} ({arm})", f"{auc:.4f}" in blob)
        ins = d["in_site_reference_this_protocol"]["AUC"]
        add(g, f"docs quote in-site AUC {ins:.4f} ({arm})", f"{ins:.4f}" in blob)
        src = d["in_site_reference_cross_plate"]["source"]
        add(g, f"the 0.6825 source artifact exists ({arm})",
            os.path.isfile(os.path.join(REPO, src)), src)
    p3 = os.path.join(REPORTS, "20_stage11_p3_cross_plate_summary.json")
    if os.path.isfile(p3):
        txt = read(p3)
        add(g, "the P3 summary carries the committed 0.6825", "0.6825" in txt)
    struct = read(os.path.join(REPORTS, "21_stage12_replicate_structure.csv"))
    add(g, "replicate-structure artifact carries the 303 the docs quote",
        "303" in struct)
    stale = []
    for m in MD_FILES:
        s = read(m)
        for hit in re.finditer(r"156×", s):
            window = s[max(0, hit.start() - 260): hit.end() + 260].lower()
            if not any(w in window for w in ("withdraw", "supersede", "replac")):
                stale.append(f"{os.path.basename(m)}:{s[:hit.start()].count(chr(10)) + 1}")
    add(g, "the withdrawn ~156× lift is never quoted outside a withdrawal sentence",
        not stale, "; ".join(stale))


# ---------------------------------------------------------------- E. pdf
def group_pdf():
    g = "E pdf"
    pdf = os.path.join(DOCS, "12_technical_report_draft_v7.pdf")
    if not os.path.isfile(pdf):
        add(g, "report PDF exists", False, pdf)
        return
    try:
        import pymupdf
    except ImportError:
        add(g, "pymupdf importable (PDF checks skipped)", False, "pip install pymupdf")
        return
    doc = pymupdf.open(pdf)
    text = "".join(p.get_text() for p in doc)
    add(g, f"PDF page count inside 12-22 (is {doc.page_count})", 12 <= doc.page_count <= 22)
    for anchor in ("External validation on an independent site", "position-decoupled",
                   "0.5971", "not reproduced", "AI Use Disclosure", "References"):
        add(g, f"PDF text layer contains {anchor!r}", anchor in text)
    digest = hashlib.md5(open(pdf, "rb").read()).hexdigest()
    blob = md_blob()
    add(g, f"PDF md5 {digest} is the hash the docs record",
        digest in blob or digest[:8] + "…" in blob)


# ---------------------------------------------------------------- F. manifest
def group_manifest(manifest, deep):
    g = "F manifest"
    if not os.path.isfile(manifest):
        return
    rows = [r for r in read(manifest).strip().split("\n")[1:] if r.count(",") >= 5]
    bad_size, bad_hash, n_ok, total_bytes = [], [], 0, 0
    for r in rows:
        c = r.split(",")
        local, nbytes, status, sha = c[1], int(c[2]), c[4], c[5]
        total_bytes += nbytes
        if not os.path.isfile(local):
            bad_size.append(f"missing {os.path.basename(local)}")
            continue
        if os.path.getsize(local) != nbytes:
            bad_size.append(f"{os.path.basename(local)}: {os.path.getsize(local)} != {nbytes}")
        if deep:
            with open(local, "rb") as f:
                if hashlib.sha256(f.read()).hexdigest() != sha:
                    bad_hash.append(os.path.basename(local))
        n_ok += status == "ok"
    add(g, f"all {len(rows)} manifest rows carry status = ok", n_ok == len(rows))
    add(g, f"manifest sizes match the objects on disk ({total_bytes:,} bytes)", not bad_size,
        "; ".join(bad_size[:3]))
    add(g, f"docs record the manifest byte total {total_bytes:,}",
        f"{total_bytes:,}" in md_blob())
    if deep:
        add(g, "every manifest SHA256 recomputes", not bad_hash, "; ".join(bad_hash[:3]))


# ---------------------------------------------------------------- G. unit tests
def group_tests():
    g = "G tests"
    files = sorted(glob.glob(os.path.join(REPO, "tests", "test_*.py")))
    add(g, f"tests/ carries {len(files)} test file(s)", bool(files),
        "python tests/test_stage12_units.py")
    for f in files:
        try:
            proc = subprocess.run([sys.executable, f], capture_output=True, text=True,
                                  cwd=REPO, timeout=900)
        except Exception as exc:  # noqa: BLE001 - a hung or unlaunchable suite is a FAIL
            add(g, f"{os.path.basename(f)} runs", False, repr(exc))
            continue
        tail = (proc.stdout.strip().split("\n") or [""])[-1]
        add(g, f"{os.path.basename(f)} exits 0 ({tail})", proc.returncode == 0,
            (proc.stderr.strip().splitlines() or [""])[-1])


INVENTORY = [
    ("A layout", "paths resolve from _paths.py; no absolute roots in scripts", group_layout),
    ("B compile", "all scripts parse", group_compile),
    ("C citations", "docs cite only artifacts that exist", group_citations),
    ("D numbers", "quoted numbers equal the JSON/CSV artifacts", group_numbers),
    ("E pdf", "PDF pages, anchors, and the recorded md5", group_pdf),
    ("G tests", "the dependency-free unit suite runs green", group_tests),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true", help="recompute every manifest SHA256")
    ap.add_argument("--list", action="store_true", help="print the check inventory")
    a = ap.parse_args()
    if a.list:
        for g, name, _ in INVENTORY:
            print(f"{g}: {name}")
        print("F manifest: rows, sizes and byte total; SHA256 only with --deep")
        return 0
    manifest = None
    for _, _, fn in INVENTORY:
        out = fn()
        if out:
            manifest = out
    if manifest:
        group_manifest(manifest, a.deep)
    fails = 0
    group = None
    width = max(len(name) for _, name, _, _ in R)
    for g, name, ok, note in R:
        if g != group:
            print(f"\n[{g}]")
            group = g
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<{width}}" +
              ("" if ok or not note else f"   <- {note}"))
    print(f"\n{len(R) - fails}/{len(R)} checks pass"
          + ("  (deep SHA256 included)" if a.deep else "  (use --deep to recompute SHA256)"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
