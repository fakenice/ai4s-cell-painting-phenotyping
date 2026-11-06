#!/usr/bin/env python
"""Record what the analysis actually ran on, and prove the record is not stale.

    python scripts/record_environment.py            # write reports/23_environment_fingerprint.json
    python scripts/record_environment.py --check    # compare that file to this environment, write nothing

Two separate questions get conflated in a `requirements.txt`, so this file keeps them apart:

1. **Declared** - what `pip install -r requirements.txt` would build. The pinned block at the top
   of that file claims to be "the environment that produced the submitted results"; that claim is
   about 2026-10-05 and cannot be re-measured now, so the file records the *live* version beside
   each pin instead of asserting they agree. Measured 2026-11-06: of the twelve `==` pins, three
   equal this machine, seven differ, two are not installed at all.
2. **Imported** - what the committed code actually needs. An AST sweep splits each third-party
   import by how reachable it is: module-level (the script cannot start without it),
   module-guarded (inside a module-level `try` that catches ImportError, so the script starts and
   the handler is expected to report the absence), or deferred (inside a function, so only the
   code path that reaches it does). Eight distributions were imported by committed code and absent
   from `requirements.txt` when this recorder was written; they are declared now - unpinned,
   because no version of theirs can be tied back to the 2026-10-05 build.

`scripts/check_repo.py` group B re-derives both lists and fails if the recorded fingerprint no
longer equals the live environment, so an upgraded library is reported instead of silently
changing 4th-decimal results (see reports/12 §10.6). That comparison only runs where it means
something: the fingerprint records a machine, and on a checkout whose python or platform differs
the row reports itself as skipped rather than failing a reader who changed computers (reports/12
§10.7).
"""
import argparse
import ast
import importlib.metadata as md
import json
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths  # noqa: E402

REPO = _paths.REPO
OUT = os.path.join(_paths.REPORTS, "23_environment_fingerprint.json")

# import name -> distribution name, for the ones that differ
DIST = {
    "sklearn": "scikit-learn", "PIL": "pillow", "fitz": "pymupdf", "umap": "umap-learn",
    "imageio_ffmpeg": "imageio-ffmpeg", "skimage": "scikit-image", "yaml": "pyyaml",
    "dateutil": "python-dateutil", "bs4": "beautifulsoup4",
}

# declared in requirements.txt as a comment-only optional extra (boto3) - kept out of the
# undeclared-import failure only if the code never imports it
LOCAL_MODULES = {"_paths", "stage12_external_site", "demo", "make_demo_video",
                 "make_demo_video_live", "make_demo_video_v8", "record_environment",
                 "check_repo", "clone_probe", "check_paths_equal", "adopt_paths_data", "legacy_p3"}


def parse_requirements(path):
    """[(dist, op, spec, note)] - `op` is '==', '>=', or None for a bare name."""
    rows = []
    for line in open(path, encoding="utf-8").read().split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(==|>=|<=|~=)\s*([0-9][A-Za-z0-9_.\-]*)", stripped)
        if m:
            rows.append((m.group(1).lower(), m.group(2), m.group(3)))
        else:
            m = re.match(r"^([A-Za-z0-9_.\-]+)$", stripped)
            if m:
                rows.append((m.group(1).lower(), None, None))
    return rows


def installed(dist):
    try:
        return md.version(dist)
    except Exception:
        return None


def _vnum(s):
    """Leading dotted-numeric prefix of a version, as a tuple of ints (drops '+cu124')."""
    parts = []
    for p in re.split(r"[.\-+]", s or ""):
        m = re.match(r"^(\d+)", p)
        if not m:
            break
        parts.append(int(m.group(1)))
    return tuple(parts)


def _meets(got, floor):
    """True when `got` is at or above a '>=' floor, zero-padded so '0.5' <= '0.5.12'."""
    g, f = _vnum(got), _vnum(floor)
    n = max(len(g), len(f))
    return g + (0,) * (n - len(g)) >= f + (0,) * (n - len(f))


def status_label(op, spec, got):
    """One row of the fingerprint table, as a sentence that only claims what the file claimed.

    Extracted from `build()` because the first version of it called the four unpinned rows
    "installed, equals the pin" - a version claim `requirements.txt` never made, and exactly the
    kind of sentence a reader would later quote as a verified pin. The seven situations:

      no operator at all, installed      -> "declared without a pin, installed"
      no operator at all, absent         -> "declared without a pin, not installed here"
      '==' , absent                      -> "pinned, not installed here"
      '==' , present, unequal            -> "installed, differs from the pin"
      '==' , present, equal              -> "installed, equals the pin"
      '>=', present, at/above the floor  -> "declared as a range, installed at or above the floor"
      '>=', present, below the floor     -> "declared as a range, installed below the floor"

    Any other operator (e.g. '~=', which the file does not use today) is reported as declared
    without being compared, because comparing it would be a claim this code has not defined.
    """
    if not op:
        return "declared without a pin, installed" if got \
            else "declared without a pin, not installed here"
    if got is None:
        return "pinned, not installed here"
    if op == "==":
        return "installed, equals the pin" if got == spec else "installed, differs from the pin"
    if op == ">=":
        return ("declared as a range, installed at or above the floor" if _meets(got, spec)
                else "declared as a range, installed below the floor")
    return f"declared as {op} {spec}, installed (not compared)"


def sweep_imports():
    """{module: {level: [files]}} over the tracked scripts, split by how reachable the import is.

    module            - a statement in the module body: the script cannot even start without it
    module-guarded    - inside a module-level try whose handlers catch ImportError: the script
                        starts, and the absence is meant to be reported by that handler
    deferred          - inside a function or class body: only the code path that reaches it needs it
    """
    std = set(sys.stdlib_module_names)
    found = {}
    for f in (sorted(glob_root("*.py")) + sorted(glob_root("scripts/*.py"))
              + sorted(glob_root("tests/*.py"))):
        tree = ast.parse(open(f, encoding="utf-8", errors="replace").read(), filename=f)
        hard, guarded, deferred = set(), set(), set()
        walk_body(tree.body, False, hard, guarded, deferred)
        rel = os.path.relpath(f, REPO).replace("\\", "/")
        for level, names in (("module", hard), ("module-guarded", guarded), ("deferred", deferred)):
            for m in names:
                if m in std or m in LOCAL_MODULES or m.startswith("."):
                    continue
                found.setdefault(m, {}).setdefault(level, []).append(rel)
    return found


def _names(node):
    if isinstance(node, ast.Import):
        return {a.name.split(".")[0] for a in node.names}
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return {node.module.split(".")[0]}
    return set()


def _catches_import_error(handler):
    t = handler.type
    if isinstance(t, ast.Name):
        names = {t.id}
    elif isinstance(t, ast.Tuple):
        names = {e.id for e in t.elts if isinstance(e, ast.Name)}
    else:
        names = set()
    return bool(names & {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"})


def walk_body(stmts, in_guard, hard, guarded, deferred):
    """Walk the module body: descend conditionals, loops and tries; stop at function bodies."""
    for st in stmts:
        if isinstance(st, (ast.Import, ast.ImportFrom)):
            (guarded if in_guard else hard).update(_names(st))
        elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for n in ast.walk(st):                       # everything inside is deferred
                deferred.update(_names(n))
        elif isinstance(st, ast.Try):
            guard = in_guard or any(_catches_import_error(h) for h in st.handlers)
            walk_body(st.body, guard, hard, guarded, deferred)
            for h in st.handlers:
                walk_body(h.body, True, hard, guarded, deferred)
            walk_body(st.orelse, guard, hard, guarded, deferred)
            walk_body(st.finalbody, guard, hard, guarded, deferred)
        elif isinstance(st, (ast.If, ast.While, ast.For, ast.With)):
            for attr in ("body", "orelse"):
                walk_body(getattr(st, attr, None) or [], in_guard, hard, guarded, deferred)


def glob_root(pattern):
    import glob
    return glob.glob(os.path.join(REPO, pattern))


def build():
    reqs = parse_requirements(os.path.join(REPO, "requirements.txt"))
    declared = {d for d, _, _ in reqs}
    requirements = []
    for dist, op, spec in reqs:
        got = installed(dist)
        requirements.append({"distribution": dist, "declared": f"{op or ''}{spec or ''}".strip(),
                             "installed": got, "status": status_label(op, spec, got)})
    imports = []
    for mod, where in sorted(sweep_imports().items()):
        dist = DIST.get(mod, mod)
        level = ("module" if "module" in where else
                 "module-guarded" if "module-guarded" in where else "deferred")
        files = sorted(set(sum(where.values(), [])))
        imports.append({"module": mod, "distribution": dist, "level": level,
                        "files": files[:8], "n_files": len(files),
                        "declared_in_requirements": dist in declared,
                        "installed_here": installed(dist) or installed(mod)})
    undeclared = {lvl: sorted({i["distribution"] for i in imports
                               if i["level"] == lvl and not i["declared_in_requirements"]})
                  for lvl in ("module", "module-guarded", "deferred")}
    return {
        "recorded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "requirements_txt": requirements,
        "imports": imports,
        "summary": {
            "declared": len(requirements),
            "status_counts": {k: v for k, v in sorted(Counter(
                r["status"] for r in requirements).items())},
            "pinned_equal_to_this_machine": sum(1 for r in requirements
                                                if r["status"] == "installed, equals the pin"),
            "third_party_modules_imported": len(imports),
            "undeclared_module_level_imports": undeclared["module"],
            "undeclared_module_guarded_imports": undeclared["module-guarded"],
            "undeclared_deferred_imports": undeclared["deferred"],
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="compare the recorded fingerprint with this environment, write nothing")
    a = ap.parse_args(argv)
    now = build()
    if not a.check:
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            json.dump(now, f, indent=1, sort_keys=True)
            f.write("\n")
        s = now["summary"]
        print(f"wrote {os.path.relpath(OUT, REPO)}")
        print(f"  declared {s['declared']} distributions: " + ", ".join(
            f"{v} {k}" for k, v in s["status_counts"].items()))
        print(f"  third-party modules imported: {s['third_party_modules_imported']}")
        print(f"  undeclared, module level (the script cannot start): "
              f"{s['undeclared_module_level_imports'] or 'none'}")
        print(f"  undeclared, module-guarded (behind try/ImportError): "
              f"{s['undeclared_module_guarded_imports'] or 'none'}")
        print(f"  undeclared, deferred (inside a function): {s['undeclared_deferred_imports'] or 'none'}")
        return 0
    if not os.path.isfile(OUT):
        print(f"FAIL  no recorded fingerprint at {os.path.relpath(OUT, REPO)}")
        return 1
    rec = json.load(open(OUT, encoding="utf-8"))
    bad = []
    if rec["python"] != now["python"]:
        bad.append(f"python {rec['python']} -> {now['python']}")
    live = {r["distribution"]: r["installed"] for r in now["requirements_txt"]}
    for r in rec["requirements_txt"]:
        if live.get(r["distribution"]) != r["installed"]:
            bad.append(f"{r['distribution']} recorded {r['installed']!r}, live "
                       f"{live.get(r['distribution'])!r}")
    li = {i["module"]: i["installed_here"] for i in now["imports"]}
    for i in rec["imports"]:
        if li.get(i["module"]) != i["installed_here"]:
            bad.append(f"import {i['module']} recorded {i['installed_here']!r}, live "
                       f"{li.get(i['module'])!r}")
    # the import *surface* too, so new code cannot hide behind unchanged versions
    missing = sorted({i["module"] for i in now["imports"]} - {i["module"] for i in rec["imports"]})
    extra = sorted({i["module"] for i in rec["imports"]} - {i["module"] for i in now["imports"]})
    if missing:
        bad.append("imported now, absent from the record: " + ", ".join(missing))
    if extra:
        bad.append("in the record, no longer imported: " + ", ".join(extra))
    if now["summary"]["undeclared_module_level_imports"]:
        bad.append("undeclared module-level imports: "
                   + ", ".join(now["summary"]["undeclared_module_level_imports"]))
    if bad:
        print(f"STALE - the environment or the import surface moved since {rec['recorded_utc']}:")
        for b in bad[:20]:
            print("  ", b)
        print("re-record with: python scripts/record_environment.py")
        return 1
    print(f"CURRENT - python {now['python']}, {now['summary']['declared']} declared, "
          f"{len(rec['requirements_txt'])} version rows + {len(rec['imports'])} import rows "
          f"still match, no undeclared module-level import (recorded {rec['recorded_utc']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
