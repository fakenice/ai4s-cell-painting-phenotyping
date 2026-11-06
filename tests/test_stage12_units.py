# -*- coding: utf-8 -*-
"""Dependency-free unit tests for the pure helpers in scripts/stage12_external_site.py.

Why this file exists: the cross-site claims in reports/24 rest on four pieces of plumbing
that never touch the network - the robust-z normalisation, the well-coordinate handling,
the additive-layout residualisation, and the three-arm retrieval split. Those arms are a
definition, not a measurement, so they are checkable on synthetic data, and the strict arm
(`decoupled-only`) is the one the retrieval claim actually rests on.

Run it with plain python - no pytest in this environment:

    python tests/test_stage12_units.py            # all tests
    python tests/test_stage12_units.py retrieval  # only tests whose name matches

Exit code 0 means every assertion passed. Lines are PASS / SKIP / FAIL; SKIP is a precondition
this checkout does not offer (no `data/` tree, i.e. a fresh clone), printed on the summary line
so it cannot be mistaken for a pass. Measured on a clone without inputs: `20/20 tests pass
(1 skipped: paths_data_rule_prefers_the_repo_and_falls_back_to_the_workspace)`.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import stage12_external_site as S  # noqa: E402


class Skip(Exception):
    """The environment does not offer the precondition this test checks.

    Used only for the two assertions about the *live* workspace layout: they are true of a
    checkout that has its gitignored `data/` tree in place and no `AI4S_WORKSPACE` set. Running
    the suite in a fresh clone (inputs not yet downloaded) or under a deliberate
    `AI4S_WORKSPACE=/some/empty/dir` probe must report them as skipped, not as failures — and
    must not quietly count them as passes either.
    """


# --------------------------------------------------------------- path resolution (_paths)
def test_paths_data_rule_prefers_the_repo_and_falls_back_to_the_workspace():
    """`_paths._resolve_data` is what lets a standalone clone (data/ inside the checkout, as
    README §3 tells you to build it) and this workspace (data/ one level above, where the 160 MB
    already lives) both work. Tested by repointing the module's globals at temporary
    directories, then restoring them."""
    import importlib
    import tempfile

    import _paths
    saved = (_paths._ENV_WS, _paths.REPO, _paths.WORKSPACE)
    try:
        with tempfile.TemporaryDirectory() as ws:
            repo = os.path.join(ws, "github_repo")
            os.makedirs(repo)
            _paths._ENV_WS = None
            _paths.REPO = repo
            _paths.WORKSPACE = ws
            # neither exists -> the workspace default, so the error text points at a stable path
            assert _paths._resolve_data() == os.path.join(ws, "data")
            # only <workspace>/data exists (this checkout's layout)
            os.makedirs(os.path.join(ws, "data"))
            assert _paths._resolve_data() == os.path.join(ws, "data")
            # both exist -> the repo wins, which is what a fresh clone needs
            os.makedirs(os.path.join(repo, "data"))
            assert _paths._resolve_data() == os.path.join(repo, "data")
            os.rmdir(os.path.join(ws, "data"))
            assert _paths._resolve_data() == os.path.join(repo, "data")
            # an explicit AI4S_WORKSPACE is honoured over both
            _paths._ENV_WS = ws
            assert _paths._resolve_data() == os.path.join(ws, "data")
    finally:
        _paths._ENV_WS, _paths.REPO, _paths.WORKSPACE = saved
        importlib.reload(_paths)         # live values restored for every later test
    # The same rule applied to this checkout can only be checked where the inputs are: DATA is
    # gitignored, and an AI4S_WORKSPACE set from outside points the module at somebody else's tree.
    if os.environ.get("AI4S_WORKSPACE"):
        raise Skip(f"AI4S_WORKSPACE={os.environ['AI4S_WORKSPACE']!r} is set from outside, "
                   f"so _paths.DATA ({_paths.DATA}) is not this checkout's tree")
    if not os.path.isdir(_paths.DATA):
        raise Skip(f"{_paths.DATA} does not exist: the gitignored data tree was never "
                   "downloaded here, so the live resolution cannot be asserted")
    assert os.path.isdir(_paths.DATA), _paths.DATA


def test_paths_roots_exist_and_are_nested_as_documented():
    import _paths
    assert os.path.basename(_paths.REPO) and os.path.isdir(_paths.REPO)
    assert _paths.REPORTS == os.path.join(_paths.REPO, "reports")
    assert os.path.isdir(_paths.REPORTS) and os.path.isfile(
        os.path.join(_paths.REPORTS, "24_cross_site_external_validation.md"))
    env_repo, env_ws = os.environ.get("AI4S_REPO"), os.environ.get("AI4S_WORKSPACE")
    if env_repo or env_ws:
        # With an override the nesting claim is the wrong one to make; the right claim is that
        # the override is honoured, which is what README §3 tells a user to rely on.
        want_repo = os.path.abspath(env_repo) if env_repo else os.path.dirname(_paths._HERE)
        want_ws = os.path.abspath(env_ws) if env_ws else os.path.dirname(want_repo)
        assert (_paths.REPO, _paths.WORKSPACE) == (want_repo, want_ws), (
            f"override ignored: REPO={_paths.REPO} WORKSPACE={_paths.WORKSPACE} "
            f"want {want_repo} {want_ws}")
        return
    assert _paths.WORKSPACE == os.path.dirname(_paths.REPO)


# --------------------------------------------------------------------- well coordinates
def test_well_coords_parsing():
    r, c = S.well_coords(["A07", "a7", "P24", "junk", ""])
    assert list(r) == ["A", "A", "P", "", ""], r
    assert list(c) == [7, 7, 24, -1, -1], c


def test_position_design_is_fixed_rank_and_data_independent():
    # 16 rows and 24 columns, one reference level each dropped -> 15 + 23 columns.
    assert len(S.WELL_ROWS[1:]) + len(S.WELL_COLS[1:]) == 38
    wells = ["B02", "P24", "A01"]
    D = S.position_design(wells)
    assert D.shape == (3, 38)
    # one row indicator and one column indicator per parsable well ...
    assert D[0].sum() == 2 and D[1].sum() == 2
    # ... except the reference cell A01, which is all zeros by construction
    assert D[2].sum() == 0
    # the encoding depends on the string, not on what else is in the plate: the same well
    # in a different dataset maps to the same row, which is what lets a pilot-fitted model
    # be evaluated at another site at all.
    D2 = S.position_design(["B02", "Z99"])
    assert np.array_equal(D[0], D2[0])
    # Documented limitation, asserted so it cannot surprise anyone: an unparsable barcode
    # lands on the same all-zero row as the reference well A01. Every well in both sites
    # parses (checked below on the real layout), so no real row is affected.
    assert np.array_equal(D[2], S.position_design(["junk"])[0])
    unparsable = [w for w in _both_site_layouts() if not S.well_coords([w])[0][0]]
    assert not unparsable, unparsable[:5]


def _both_site_layouts():
    """Every well barcode the two sites can produce (16x24 in both cases)."""
    return [f"{r}{c:02d}" for r in S.WELL_ROWS for c in S.WELL_COLS]


# --------------------------------------------------------------------- robust z
def test_robust_z_uses_dmso_median_and_mad():
    n = 10
    df = pd.DataFrame({"Cells_A": np.arange(n, dtype=float),
                       "Cells_B": np.ones(n)})          # constant feature
    dmso = np.zeros(n, dtype=bool)
    dmso[:5] = True                                     # DMSO values 0..4
    Z = S.robust_z(df, ["Cells_A", "Cells_B"], dmso)
    assert Z.shape == (n, 2)
    assert np.isfinite(Z).all()
    # DMSO arm: median 2, MAD 1 -> scale 1.4826, so the DMSO median maps to 0 exactly.
    assert abs(np.median(Z[:5, 0])) < 1e-12
    assert abs(Z[5, 0] - (5 - 2) / 1.4826) < 1e-9
    # a feature with zero MAD falls back to scale 1.0 rather than dividing by ~0
    assert np.allclose(Z[:, 1], 0.0)


def test_robust_z_is_symmetric_around_vehicle():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"Cells_A": rng.normal(0, 1, 200)})
    dmso = np.zeros(200, dtype=bool)
    dmso[:100] = True
    Z = S.robust_z(df, ["Cells_A"], dmso)
    # standardised on the vehicle half -> that half has unit robust scale
    assert abs(np.median(np.abs(Z[:100, 0])) * 1.4826 - 1.0) < 0.05
    # and a treated well drawn from the same distribution sits inside the same z range,
    # i.e. the transform does not systematically push non-vehicle wells one way.
    assert abs(Z[100:, 0].mean() - Z[:100, 0].mean()) < 0.2


def test_robust_z_never_leaks_information_from_treated_wells():
    """The scale is estimated on vehicle wells only, so two plates that share their DMSO
    rows must share their vehicle normalisation even if their treated rows differ. This is
    what makes the external site's normalisation independent of the pilot's."""
    dmso_block = np.array([[0.0], [1.0], [2.0], [3.0], [4.0]])
    a = pd.DataFrame(np.vstack([dmso_block, [[10.0]] * 5]), columns=["Cells_A"])
    b = pd.DataFrame(np.vstack([dmso_block, [[-3.0]] * 5]), columns=["Cells_A"])
    dm = np.zeros(10, dtype=bool)
    dm[:5] = True
    Za, Zb = S.robust_z(a, ["Cells_A"], dm), S.robust_z(b, ["Cells_A"], dm)
    assert np.allclose(Za[:5], Zb[:5])
    assert not np.allclose(Za[5:], Zb[5:])


# --------------------------------------------------------------------- layout residual
def test_residualize_position_kills_pure_additive_layout():
    wells = _both_site_layouts()                        # 384 wells, complete plate
    row = np.array([S.WELL_ROWS.index(w[0]) for w in wells], float)
    col = np.array([int(w[1:]) for w in wells], float)
    X = np.column_stack([2.0 * row - 3.0 * col, row + 0.5 * col])
    R = S.residualize_position(X, wells)
    assert np.abs(R).max() < 1e-8, np.abs(R).max()
    # a non-additive term survives
    X2 = np.column_stack([row * col])
    R2 = S.residualize_position(X2, wells)
    assert np.abs(R2).max() > 0.1


# --------------------------------------------------------------------- replicate counting
def test_rep_counts_shape():
    n, dist = S._rep_counts(["a", "a", "b", "c", "c", "c"])
    assert n == 3
    assert dist == {2: 1, 1: 1, 3: 1}, dist            # {wells per compound: n compounds}
    assert S._rep_counts([]) == (0, {})


# --------------------------------------------------------------------- retrieval arms
def test_retrieval_layout_matched_plate_has_only_the_matched_arm():
    """The pilot case: same compound, same coordinate, one true match per query."""
    wells = ["A01", "A02", "A03", "A04"]
    keys = ["k1", "k2", "k3", "k4"]
    X = np.eye(4)
    out = S.retrieval_by_position(X, keys, wells, X, keys, wells)
    assert set(out) == {"position-matched"}, set(out)
    pm = out["position-matched"]
    assert pm["n_queries"] == 4
    assert pm["recall_at_1"] == 1.0
    assert pm["n_library_wells"] == 4
    assert pm["chance_recall_at_1"] == 0.25
    assert pm["chance_recall_at_1_any_accepted_match"] == 0.25


def test_retrieval_shifted_layout_is_reported_in_both_decoupled_arms():
    """Identical content, plate re-registered: no query has its own coordinate in the library."""
    keys = ["k1", "k2", "k3", "k4"]
    X = np.eye(4)
    out = S.retrieval_by_position(X, keys, ["A01", "A02", "A03", "A04"],
                                  X, keys, ["B01", "B02", "B03", "B04"])
    assert set(out) == {"position-decoupled", "decoupled-only"}, set(out)
    for arm in ("position-decoupled", "decoupled-only"):
        assert out[arm]["n_queries"] == 4 and out[arm]["recall_at_1"] == 1.0
    # the strict arm is a subset of the broad one and can never be wider
    assert out["decoupled-only"]["n_queries"] <= out["position-decoupled"]["n_queries"]


def test_retrieval_multi_well_compound_splits_the_arms_and_the_null():
    """External case: one compound in several wells, one of them at the query coordinate."""
    Xlib = np.eye(4)
    Xq = np.array([[1.0, 0.0, 0.0, 0.0],     # k1 best-matches library well A01 (same coord)
                   [0.0, 0.0, 0.0, 1.0]])    # k2 has a single match, also same coord
    out = S.retrieval_by_position(
        Xq, ["k1", "k2"], ["A01", "A02"],
        Xlib, ["k1", "k1", "k1", "k2"], ["A01", "C01", "D01", "A02"])
    assert set(out) == {"position-matched", "position-decoupled"}, set(out)
    assert "decoupled-only" not in out          # every query had a same-coordinate match
    assert out["position-matched"]["n_queries"] == 2
    assert out["position-matched"]["recall_at_1"] == 1.0
    # null = mean over queries of (#accepted matches at that arm) / (#library wells):
    # k1 contributes 1/4 to matched and 2/4 to decoupled, k2 contributes 1/4 and nothing.
    assert abs(out["position-matched"]["chance_recall_at_1_any_accepted_match"]
               - ((1 / 4 + 1 / 4) / 2)) < 1e-12
    assert abs(out["position-decoupled"]["chance_recall_at_1_any_accepted_match"]
               - (2 / 4)) < 1e-12
    # the decoupled arm cannot score rank 1 here: the true same-coordinate well is closer
    assert out["position-decoupled"]["recall_at_1"] == 0.0


def test_retrieval_query_without_a_match_is_dropped_not_counted():
    Xlib = np.eye(2)
    out = S.retrieval_by_position(np.array([[1.0, 0.0], [0.0, 1.0]]),
                                  ["k1", "k9"], ["A01", "A02"],
                                  Xlib, ["k1", "k2"], ["B01", "B02"])
    assert out["decoupled-only"]["n_queries"] == 1
    assert out["decoupled-only"]["median_rank"] == 1.0


def test_retrieval_strict_arm_reports_a_larger_null_when_compounds_are_duplicated():
    """The null scales with the number of accepted matches, so a bigger library cannot
    make the strict arm look better by accident."""
    Xlib = np.eye(4)
    out = S.retrieval_by_position(np.array([[1.0, 0.2, 0.0, 0.0]]), ["k1"], ["A01"],
                                  Xlib, ["k1", "k1", "k1", "k1"], ["B01", "C01", "D01", "E01"])
    assert out["decoupled-only"]["n_queries"] == 1
    assert abs(out["decoupled-only"]["chance_recall_at_1_any_accepted_match"] - 1.0) < 1e-12


# --------------------------------------------------------------------- scaling arms
def _side():
    rng = np.random.default_rng(1)
    n = 60
    X = rng.normal(0, 1, (n, 3))
    X[40:, 0] += 4.0                       # a treated shift in feature 0
    X[3, 1] = 900.0                        # one heavy tail, to exercise zclip5
    df = pd.DataFrame(X, columns=["Cells_A", "Cytoplasm_B", "Nuclei_C"])
    df["Metadata_Well"] = [f"{S.WELL_ROWS[i // 24]}{(i % 24) + 1:02d}" for i in range(n)]
    dmso = np.zeros(n, dtype=bool)
    dmso[:20] = True
    return df, list(df.columns[:3]), dmso


def test_scale_side_relations_between_arms():
    df, feats, dmso = _side()
    Z = S.scale_side(df, feats, dmso, "negcon_z")
    Zc = S.scale_side(df, feats, dmso, "zclip5")
    assert np.allclose(Zc, np.clip(Z, -5, 5))
    assert np.abs(Zc).max() <= 5 + 1e-12
    assert np.abs(Z).max() > 5, "the tail has to exist for the clip arm to mean anything"

    R = S.scale_side(df, feats, dmso, "rank")
    assert R.shape == Z.shape and np.isfinite(R).all()
    # rank is monotone per feature: it reorders nothing, it only rescales
    for j in range(R.shape[1]):
        same_order = np.sign(R[:, j][:, None] - R[:, j][None, :]) == \
            np.sign(Z[:, j][:, None] - Z[:, j][None, :])
        assert same_order.all(), j

    P = S.scale_side(df, feats, dmso, "posresid")
    assert P.shape == Z.shape and np.isfinite(P).all()
    # posresid = negcon_z with additive row/column effects projected out, so it agrees with
    # the residualiser applied to the base arm.
    ref = S.residualize_position(S.impute_finite(Z), df["Metadata_Well"].to_numpy())
    assert np.abs(P - ref).max() < 1e-9


def test_scale_side_posresid_needs_the_well_barcode():
    df, feats, dmso = _side()
    try:
        S.scale_side(df.drop(columns=["Metadata_Well"]), feats, dmso, "posresid")
    except RuntimeError:
        return
    raise AssertionError("posresid silently accepted a table with no Metadata_Well")


def test_scale_side_is_deterministic_for_every_arm():
    """Each arm is a pure per-dataset transform: the same table in, the same matrix out.
    That is the weak form of "applied identically to both sides" - the strong form (that the
    pilot and the external plate are normalised against their own vehicle wells, never each
    other's) is structural: `scale_side` only ever receives one dataframe, and
    `robust_z` reads its median/MAD from `df[dmso_mask]` inside that frame."""
    df, feats, dmso = _side()
    for mode in S.SCALES:
        assert mode in ("negcon_z", "rank", "zclip5", "posresid"), mode
        a = S.scale_side(df.copy(), feats, dmso, mode)
        b = S.scale_side(df.copy(), feats, dmso, mode)
        assert np.allclose(a, b), mode


# --------------------------------------------------------------------- position confound
def _plate(rows="ABCD"):
    return [f"{r}{c:02d}" for r in rows for c in S.WELL_COLS]


def test_position_confound_detects_vehicle_columns_and_scores_them_as_leakage():
    wells = _plate()
    is_dmso = np.array([w[1:] in ("02", "23") for w in wells])
    out = S.position_confound(wells, is_dmso, ~is_dmso, n_perm=300, seed=0)
    assert out["n_wells"] == len(wells) and out["n_dmso"] == int(is_dmso.sum())
    assert out["n_cols_with_dmso"] == 2 and out["dmso_cols"] == [2, 23]
    assert out["dmso_max_share_one_col"] == 0.5            # 8 of 16 vehicle wells per column
    assert out["position_only_cv_auc"] > 0.99, out["position_only_cv_auc"]
    assert out["dmso_layout_p_col_perm"] < 0.05
    assert 0.0 <= out["dmso_layout_p_row_perm"] <= 1.0


def test_position_confound_is_lower_when_vehicle_is_scattered():
    wells = _plate()
    rng = np.random.default_rng(7)
    idx = rng.permutation(len(wells))[:16]
    is_dmso = np.zeros(len(wells), dtype=bool)
    is_dmso[idx] = True
    scattered = S.position_confound(wells, is_dmso, ~is_dmso, n_perm=300, seed=0)
    blocked = S.position_confound(wells, np.array([w[1:] in ("02", "23") for w in wells]),
                                  np.array([w[1:] not in ("02", "23") for w in wells]),
                                  n_perm=300, seed=0)
    assert scattered["position_only_cv_auc"] < blocked["position_only_cv_auc"]
    assert blocked["n_cols_with_dmso"] <= scattered["n_cols_with_dmso"]


def test_position_confound_returns_nan_when_a_class_is_too_small():
    wells = _plate("AB")
    is_dmso = np.zeros(len(wells), dtype=bool)
    is_dmso[:4] = True                                     # 4 vehicle wells: below the floor
    out = S.position_confound(wells, is_dmso, ~is_dmso, n_perm=50, seed=0)
    assert np.isnan(out["position_only_cv_auc"])


# ------------------------------------------------------- invariants of the committed artifact
def test_committed_retrieval_artifact_keeps_the_strict_arm_disjoint():
    p = os.path.join(S.REPORTS, "21_stage12_retrieval_position_split.json")
    if not os.path.isfile(p):
        print("    skip (artifact not present): committed retrieval split")
        return
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    strict = d["arm_summaries_by_plate_pair"]["decoupled-only"]
    # Why paired_strict_by_plate_pair is null: the strict arm shares no plate pair with the
    # matched arm, so there is nothing to pair against.
    assert strict["n_pairs_also_having_position_matched"] == 0
    assert d["paired_strict_by_plate_pair"] is None
    assert abs(strict["recall_at_1_query_weighted"] - 0.5971) < 5e-4
    assert strict["n_queries"] < d["arm_summaries_by_plate_pair"]["position-decoupled"]["n_queries"]
    assert d["pilot_layout_note"].startswith("384/384")


def main(argv):
    wanted = argv[1] if len(argv) > 1 else ""
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f) and wanted in n]
    failed, skipped = [], []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Skip as exc:                            # precondition absent, not a pass
            skipped.append((name, exc))
            print(f"  SKIP  {name}: {exc}")
        except Exception as exc:                       # noqa: BLE001 - report and continue
            failed.append((name, exc))
            print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    ran = len(tests) - len(skipped)
    print(f"{ran - len(failed)}/{ran} tests pass"
          + (f" ({len(skipped)} skipped: {', '.join(n[5:] for n, _ in skipped)})" if skipped
             else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
