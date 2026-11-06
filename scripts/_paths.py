"""Single source of truth for the workspace layout used by scripts/*.py.

Every stage script used to hardcode ``E:\\Desktop\\Kaggle_2026\\...``; that made the repo
unrunnable anywhere else. Paths are now derived from this file's location:

    _paths.py lives at <workspace>/<repo>/scripts/_paths.py
      REPO      = the checkout that contains scripts/   (default: ../ from here)
      WORKSPACE = the directory holding the gitignored data/ tree (default: parent of REPO)
      DATA      = <WORKSPACE>/data

Override either one without touching code:

    AI4S_REPO       absolute path of the checkout (contains reports/, scripts/)
    AI4S_WORKSPACE  absolute path of the directory that contains data/

``DATA`` then picks whichever of ``<REPO>/data`` and ``<WORKSPACE>/data`` exists (see
``_resolve_data``), so both the layout this project grew up in and a plain standalone clone work.

``python scripts/check_repo.py`` asserts these resolve to existing directories, that the data
tree is where the scripts expect it, and that the paths replaced at ``HEAD`` equal the derived
ones; the data rule itself is covered by ``tests/test_stage12_units.py``.
"""
import os

_ENV_REPO = os.environ.get("AI4S_REPO")
_ENV_WS = os.environ.get("AI4S_WORKSPACE")

# scripts/ -> repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(_ENV_REPO) if _ENV_REPO else os.path.dirname(_HERE)
WORKSPACE = os.path.abspath(_ENV_WS) if _ENV_WS else os.path.dirname(REPO)

BASE = WORKSPACE          # historical name kept so the stage scripts need no other edit


def _resolve_data():
    """Where the gitignored data tree lives.

    Order: an explicit AI4S_WORKSPACE (which means ``<that>/data`` unconditionally), then
    ``<repo>/data`` if it exists, else ``<workspace>/data``. The last two matter because both
    in use: this checkout keeps ``data/`` one level *above* the repo (it predates the repo), while
    someone who clones the repository standalone follows ``README.md`` §3 and puts it *inside*.
    Preferring whichever exists keeps both working without moving 160 MB of inputs.
    """
    if _ENV_WS:
        return os.path.join(WORKSPACE, "data")
    inside, above = os.path.join(REPO, "data"), os.path.join(WORKSPACE, "data")
    if os.path.isdir(inside):
        return inside
    return above


DATA = _resolve_data()
REPORTS = os.path.join(REPO, "reports")
FIG = os.path.join(REPORTS, "figures")
FIG_ROOT = os.path.join(REPO, "figures")
DOCS = os.path.join(REPO, "docs")
LOGS = os.path.join(REPO, "logs")

PROFILES = os.path.join(DATA, "profiles")
METADATA = os.path.join(DATA, "metadata")
RAW = os.path.join(DATA, "raw")
EXTERNAL = os.path.join(DATA, "external")

PILOT_PLATES = ("BR00116991", "BR00116992")


def profile_csv(plate, suffix="normalized_feature_select_negcon_batch"):
    """Path of one pilot plate's published profile table."""
    return os.path.join(PROFILES, f"{plate}_{suffix}.csv.gz")


def describe():
    return {"WORKSPACE": WORKSPACE, "REPO": REPO, "DATA": DATA, "REPORTS": REPORTS,
            "DATA exists": os.path.isdir(DATA), "REPORTS exists": os.path.isdir(REPORTS),
            "profiles exist": os.path.isdir(PROFILES),
            "candidate data dirs": [os.path.join(REPO, "data"), os.path.join(WORKSPACE, "data")],
            "overrides in use": {k: os.environ[k] for k in ("AI4S_REPO", "AI4S_WORKSPACE")
                                 if os.environ.get(k)}}
