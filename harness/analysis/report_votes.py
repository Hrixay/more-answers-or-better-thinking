"""Reporting items 7, 8 (8a, 8b), 18 and 20 of Karen's note `research/reporting-definitions-main.md` (93334b8, Edith CLEAN:
Addendum A items 7 and 8, Addendum B items 18 and 20, Addendum C's pins), by the LOCKED code only.

Plumbing, like `main_analysis`: every number, seed, draw count, rounding, threshold and edge case comes from the note or from locked code
(`five_tests`, `votes`, `kscript`, `k_step`, `bootstrap`, `curve`, `scoring`, `trace_parse`, `main_analysis`, `harness.pareto.main`), and
each function cites its section. A detail the note still leaves open is LEFT OUT and its question written into the output
(`OPEN_QUESTIONS`), never decided here. No model call.

THE SHARED COPY (Addendum C, C3): the vote curve of item 8 lives here, `arm_curve(ctx, arm, shape)` (per base puzzle, votes.vote_curve
over the arm's samples, official, as_deployed, k = 1..min(40, designed samples), tie "random") and `curve_summary(ctx, arm, shape)` (the
mean over bases with the shared cluster bootstrap "vote_curve:<arm>:<shape>" and the Monte-Carlo diagnostics); `report_costs` and
`report_arms` use them. The list cost (9a) and the dollars per puzzle (9b) used here are report_costs' copies.

    ctx = {"rows": main_rows.build(...)["tests"],       # the five-test rows, kind "missing" rows included
           "other": main_rows.build(...)["other"],      # every other arm's rows
           "records": main_rows.final_records(logs),    # the final call-log records (custom_id, meta, kind, cost_usd, usage_raw, ...)
           "items": {item_id: frozen item}, "set_id": ..., "n": 6,
           "k": json.load(k.json),                      # k_step's output: k_o {shape: int}, k_s, k_from_rows
           "run_dir": Path or None,                     # read for the ledger's B5 free_by_rule marks (9a)
           "B": None, "draws": None}                    # tests only: the 10,000-draw family and the 2,000 cluster draws
    report(ctx) -> {"item_7": ..., "item_8a": ..., "item_8b": ..., "item_18": ..., "item_20": ..., "open_questions": {...}}

`ctx["_cache"]` holds the per-arm vote curves and other intermediate results so the items (and the other two modules) share one
computation.

Pins applied (Addendum C): X1 names with the main_rows arm names, `<k-name>` "k_O" / "k_S", one name per statistic family shared across
k; X2 "samples drawn" is the designed number (40; 3 for Haiku-max) for k*, the band and the curves; X5 "every arm" in item 7 is the
80-base arms (the D-42 and real-time arms are out); X6 the lookup chart's bands; X7 cost per task for a multi-try arm; X8 (with Edith r8 /
r9) a test whose k + d falls outside 1..min(40, designed) is HELD at the nearest allowed k, labelled "held at the limit", and keeps its
real p in a whole five-test row; C1 item 20 (the thirds, "reaches" after rounding to 1e-9) and item 7 (partial piece credit); C4 item 1
(the per-piece vote curve has one name, "per_piece_vote_curve:haiku-med", and its k_O and k_S points are its values and bands there).
"""

from __future__ import annotations

import math
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from . import bootstrap, five_tests, k_step, kscript, report_costs, scoring, trace_parse, votes
from .curve import cluster_bootstrap
from .main_analysis import _per_puzzle_share

NOTE = "research/reporting-definitions-main.md (93334b8), Addendum A items 7-8, Addendum B items 18 and 20, Addendum C"
CAP = kscript.CAP                                     # 40 (D-33)
DESIGNED = five_tests.DESIGNED_HAIKU_SAMPLES          # 40 Haiku-medium samples per puzzle: "samples drawn" (X2)
HAIKU = "haiku-med"
TIE = "random"                                        # the D-33 tie rule (1/m)
SIGN_FLIP_NFLIPS = 100_000                            # item 8b
SIGN_FLIP_SEED = 20261011                             # item 8b: derive_seed(20261011, f"{test}:sign_flip")
ROW_LABEL = "k-sensitivity (not confirmatory)"        # item 8b
HELD_LABEL = "held at the limit"                      # X8
SIGN_FLIP_LABEL = "sensitivity (superiority, d = 0)"  # item 8b
PER_PIECE_LABEL = "secondary, descriptive (no test)"  # item 7: "Reported as secondary and descriptive ... No test."
BAND_NAMES = ("k−2", "k−1", "k+0", "k+1", "k+2")      # item 8b, spelled as the note spells them
ROW_NAMES = ("median ratio", "pilot", "k*") + BAND_NAMES
REACH_DIGITS = 9                                      # C1 item 20: "compared after rounding both to 1e-9"

# Item 8a, "k from the pilot": the ladder-l14n-1 cost ratios at n = 6, computed by kscript.k_table (include_realtime=False) on that run's
# compact_table.csv (SHA-256 below; only k_step.COLUMNS read), set ladder-ledger-l14n6-v1. Exact fractions; the note's table prints them
# rounded (36.782, 43.910, 12.947, 14.224). `pilot_ratios_from_table` recomputes them from the file.
PILOT_TABLE_SHA256 = "a4f60c97206d5245fe5177fcabe05a36de9d78fb77d708194cd3af4a600d8585"
PILOT_SET = "ladder-ledger-l14n6-v1"
PILOT_RATIO = {("opus-medium", "1x6"): Fraction(16635840, 452279), ("opus-medium", "6x1"): Fraction(1980984, 45115),
               ("sonnet-medium", "1x6"): Fraction(5855720, 452279), ("sonnet-medium", "6x1"): Fraction(91676, 6445)}
COMPARATOR_KEY = {"O": "opus-medium", "S": "sonnet-medium"}     # kscript.k_table's comparator keys

# Bootstrap names (X1, X6, C4): "per_piece:<arm>", "per_piece_vote_curve:haiku-med" (the whole per-piece vote curve; its points at k_O
# and k_S are its values and bands at those k), "vote_curve:<arm>:<shape>", "lookup:<shape>:<bin>:<third>"; <arm> the main_rows arm name.
K_NAMES = {"O": "k_O", "S": "k_S"}
PER_PIECE_CURVE_NAME = f"per_piece_vote_curve:{HAIKU}"   # C4 item 1
OUT_OF_DESIGN = "out (Addendum C, X5): not an arm of the 80-base design; reported in its own item (3: D-42; 6: real time)"

OPEN_QUESTIONS: Dict[str, str] = {}           # the last one (the per-piece curve's band) is pinned by Addendum C4, item 1


# ---------------------------------------------------------------- shared helpers (no analysis choice)

def _n(ctx: Mapping[str, object]) -> int:
    return int(ctx["n"])                                                                          # type: ignore[call-overload]


def _shapes(ctx: Mapping[str, object]) -> Tuple[str, str]:
    return scoring.pieces_shape(_n(ctx)), scoring.chain_shape(_n(ctx))


def _family_draws(ctx: Mapping[str, object]) -> int:
    """The confirmatory machinery's B (Addendum A conventions: 10,000), or the tests' override."""
    return report_costs.family_draws(ctx)


def _cluster_draws(ctx: Mapping[str, object]) -> int:
    """The shared cluster bootstrap's draws (Addendum A conventions: 2,000), or the tests' override."""
    return report_costs.cluster_draws(ctx)


def _cache(ctx: Dict[str, object]) -> Dict[object, object]:
    return ctx.setdefault("_cache", {})                                                            # type: ignore[return-value]


def _shape_of(item: Mapping[str, object]) -> str:
    return f"{item['width']}x{item['depth']}"


def _puzzles(ctx: Mapping[str, object], shape: str) -> List[str]:
    """Every item of the set at `shape` (80 in the main set), sorted."""
    return sorted(i for i, it in ctx["items"].items() if _shape_of(it) == shape)                  # type: ignore[union-attr]


def _base_of(ctx: Mapping[str, object], item_id: str) -> str:
    """main_rows' base_id: "<set_id>-<base index, 3 digits>"."""
    return f"{ctx['set_id']}-{int(ctx['items'][item_id]['base_index']):03d}"                      # type: ignore[index]


def _k_o(ctx: Mapping[str, object]) -> Dict[str, int]:
    return {str(sh): int(v) for sh, v in ctx["k"]["k_o"].items()}                                # type: ignore[index, union-attr]


def _k_s(ctx: Mapping[str, object]) -> int:
    return int(ctx["k"]["k_s"])                                                                   # type: ignore[index]


def _vote_tests(ctx: Mapping[str, object]) -> Dict[str, Tuple[str, str, str]]:
    """{test: (comparator setup, shape, "O" | "S")} for the vote tests t1-t3, from five_tests.tests_for."""
    return {t: (comp, shape, which) for t, (_, comp, shape, which) in five_tests.tests_for(_n(ctx)).items() if which in ("O", "S")}


def _confirmatory_k(ctx: Mapping[str, object], shape: str, which: str) -> int:
    return _k_o(ctx)[shape] if which == "O" else _k_s(ctx)


def _ks_for_family(ctx: Mapping[str, object], k_by_test: Mapping[str, int]) -> Tuple[Dict[str, int], int]:
    """(k_o, k_s) in five_tests' form from one k per vote test."""
    k_o = dict(_k_o(ctx))
    k_s = _k_s(ctx)
    for t, (_, shape, which) in _vote_tests(ctx).items():
        if which == "O":
            k_o[shape] = int(k_by_test[t])
        else:
            k_s = int(k_by_test[t])
    return k_o, k_s


def _rec_by_id(ctx: Dict[str, object]) -> Dict[str, Mapping[str, object]]:
    c = _cache(ctx)
    if "rec_by_id" not in c:
        c["rec_by_id"] = {str(r["custom_id"]): r for r in ctx["records"]}                        # type: ignore[union-attr, index]
    return c["rec_by_id"]                                                                          # type: ignore[return-value]


def _interval(bases: Sequence[str], values: Mapping[str, float], name: str, draws: int) -> List[Optional[float]]:
    """The shared cluster bootstrap (Addendum A conventions: curve.cluster_bootstrap, seed 20261012, percentile 95%) of the mean over
    the drawn base puzzles."""
    bs = sorted(bases)
    return list(cluster_bootstrap([bs], lambda s: (math.fsum(values[b] for b in s) / len(s)) if s else None, name, draws=draws))


def _mean(values: Sequence[float]) -> Optional[float]:
    return math.fsum(values) / len(values) if values else None


def designed(arm: str) -> int:
    """The arm's designed samples per puzzle (the runner's n; X2's "samples drawn")."""
    return int(report_costs.designed_samples(report_costs.ARM_TAG[arm]) or 0)


# ---------------------------------------------------------------- the vote curve (item 8): the ONE copy

def arm_answers(ctx: Dict[str, object], arm: str, shape: str) -> Dict[str, Dict[str, object]]:
    """Per base puzzle, the arm's samples' official vote keys (as_deployed: a missing sample is a vote for nothing, padded to the arm's
    DESIGNED samples) and the right key, by the locked five_tests._haiku_answers (written for Haiku-medium; another Haiku arm's rows are
    passed under that setup name, nothing else changes)."""
    c = _cache(ctx)
    key = ("answers", arm, shape)
    if key not in c:
        rows = [dict(r, setup=HAIKU) for r in list(ctx["rows"]) + list(ctx.get("other") or [])     # type: ignore[call-overload]
                if r["setup"] == arm and r["shape"] == shape]
        scoring.check_answer_only(rows)
        c[key] = five_tests._haiku_answers(rows, shape, "as_deployed", designed(arm), "official")
    return c[key]                                                                                  # type: ignore[return-value]


def arm_curve(ctx: Dict[str, object], arm: str, shape: str) -> Dict[str, List[Dict[str, object]]]:
    """Note item 8b's 1-40 vote curve, the ONE copy (Addendum C, C3): {base_id: votes.vote_curve(answers, correct, kmax=min(40, designed
    samples) (X2), detail=True, tie="random")} over the arm's answers (official score, as_deployed). For Haiku-medium vote@k equals
    five_tests.vote_scores at k / 100."""
    c = _cache(ctx)
    key = ("curve", arm, shape)
    if key not in c:
        kmax = min(CAP, designed(arm))
        c[key] = {b: votes.vote_curve(d["answers"], d["correct"], kmax=kmax, detail=True, tie=TIE)  # type: ignore[arg-type]
                  for b, d in sorted(arm_answers(ctx, arm, shape).items()) if d["answers"]}
    return c[key]                                                                                  # type: ignore[return-value]


def _curve_summary(per_base: Mapping[str, Sequence[Mapping[str, object]]], k: int) -> Dict[str, object]:
    """Item 18 (and 8b's "Monte-Carlo error and tie-decided share"), at one k: the method of each base's vote@k and their counts, the
    largest mc_se, and the mean tie-decided share over bases (as five_tests.tie_report averages it)."""
    at = [v[k - 1] for v in per_base.values() if len(v) >= k]
    return {"exact": sum(1 for r in at if r["method"] == "exact"), "sampled": sum(1 for r in at if r["method"] == "sampled"),
            "max_mc_se": max((float(r["mc_se"]) for r in at), default=None),                     # type: ignore[arg-type]
            "tie_decided_share_mean": _mean([float(r["tie_decided_share"]) for r in at])}         # type: ignore[arg-type]


def curve_summary(ctx: Dict[str, object], arm: str, shape: str) -> Dict[str, object]:
    """Note item 8b, "The 1-40 vote curve" (D-33 item 5), for one arm and shape (Haiku-medium here; the exploratory Haiku arms in item 10):
    vote@k for k = 1..min(40, designed) from `arm_curve`; the mean over bases (a share, 0-1) with the shared cluster bootstrap named
    "vote_curve:<arm>:<shape>", the same name (common draws) at every k (X1); the method counts, the largest Monte-Carlo error and the
    mean tie-decided share (D-33 items 7 and 8). Memoised."""
    c = _cache(ctx)
    key = ("curve_summary", arm, shape)
    if key not in c:
        per_base = arm_curve(ctx, arm, shape)
        name = f"vote_curve:{arm}:{shape}"
        points = []
        for k in range(1, min(CAP, designed(arm)) + 1):
            vals = {b: float(v[k - 1]["acc"]) for b, v in per_base.items() if len(v) >= k}       # type: ignore[arg-type]
            points.append(dict({"k": k, "mean": _mean(list(vals.values())), "n_base": len(vals),
                                "ci95": _interval(list(vals), vals, name, _cluster_draws(ctx))}, **_curve_summary(per_base, k)))
        c[key] = {"arm": arm, "shape": shape, "unit": "share right (0-1)", "bootstrap_name": name, "k_max": len(points),
                  "points": points}
    return c[key]                                                                                  # type: ignore[return-value]


# ---------------------------------------------------------------- the cost-only rows of item 8a

def _cost_columns(ctx: Dict[str, object]) -> List[Dict[str, str]]:
    """k_step's cost-only rows (custom_id, requested_model, effort, kind, cost_usd: the logged cost) for the confirmatory tags hm / om / sm
    only (item 8a: "the same cost-only rows the confirmatory k uses"; k_step.confirmatory_cost_rows checks each row's model and effort)."""
    recs = ctx["records"]                                                                          # type: ignore[assignment]
    cols = [{c: ("" if r.get(c) is None else str(r.get(c))) for c in k_step.COLUMNS} for r in recs]  # type: ignore[union-attr]
    k_step.confirmatory_cost_rows(cols)                                                            # raises on a wrong model or effort
    return [c for c in cols if kscript.parse_custom_id(c["custom_id"])["setup"] in k_step.K_TAGS]


def _k_cells(ctx: Dict[str, object]) -> Dict[Tuple[str, str], Dict[str, object]]:
    """{(which, shape): kscript.k_table cell} (include_realtime=False) on the cost-only rows (item 8a); `which` "O" or "S"."""
    c = _cache(ctx)
    key = "k_cells"
    if key not in c:
        t = kscript.k_table(_cost_columns(ctx), cap=CAP, include_realtime=False)
        c[key] = {(w, str(cell["shape"])): cell for w, side in (("O", "opus"), ("S", "sonnet")) for cell in t[side]}
    return c[key]                                                                                  # type: ignore[return-value]


def k_s_pieces(ctx: Dict[str, object]) -> Dict[str, object]:
    """Item 11's k_S(6x1), which item 7's per-piece vote uses for the Sonnet side: `kscript.k_value` on the 6x1 Sonnet-medium and Haiku-medium
    costs "from the same cost-only cell type as the confirmatory k". That cell type is five_tests.k_from_rows (designed cap 40) on
    k_step.confirmatory_cost_rows; k_from_rows computes the Sonnet cell at the chain shape only, so it is called on the same rows with the two
    shape labels swapped, which makes its chain-shape Sonnet cell the 6x1 one. The swap is checked: its Opus k at each swapped shape must
    equal k.json's k_O at the other."""
    pieces, chain = _shapes(ctx)
    cols = _cost_columns(ctx)
    rows = k_step.confirmatory_cost_rows(cols)["rows"]
    swap = {pieces: chain, chain: pieces}
    k = five_tests.k_from_rows([dict(r, shape=swap[str(r["shape"])]) for r in rows], n=_n(ctx))   # type: ignore[arg-type]
    for sh in (pieces, chain):
        if int(k["opus"][swap[sh]]["k"]) != _k_o(ctx)[sh]:                                         # type: ignore[index]
            raise ValueError(f"the shape-swapped k_from_rows gives k_O({sh}) = {k['opus'][swap[sh]]['k']}, k.json {_k_o(ctx)[sh]}")  # type: ignore[index]
    return dict(k["sonnet"][chain], shape=pieces)                                                  # type: ignore[index]


# ---------------------------------------------------------------- item 7: the per-piece view at 6x1

def _arm_tags() -> Dict[str, str]:
    """{row setup name: runner tag} for the arms of harness.pareto.main.MAIN_SETUPS, the 80-base design (X5; E3 did not run at 6x1)."""
    from ..pareto.main import MAIN_SETUPS
    return {report_costs.TAG_ARM[su.name]: su.name for su in MAIN_SETUPS}


def _piece_entries(ctx: Dict[str, object], row: Mapping[str, object]) -> List[Optional[str]]:
    """Item 7, "Pieces": one try's vote per piece (`scoring.state_key` of `trace_parse.parse_pieces(reply, 6, 6).entries[i]`), None for a
    missing or unreadable entry and for every piece of a try that did not answer (refused, truncated, missing, ...). Readable entries of a
    partly unreadable reply keep their credit (C1 item 7: the locked grade_24x1 `pieces_right`); the count of right entries is checked
    against the converter's `pieces_right`."""
    n = _n(ctx)
    if row.get("kind") != "answered":
        return [None] * n
    item = ctx["items"][str(row["item_id"])]                                                       # type: ignore[index]
    rec = _rec_by_id(ctx)[str(row["custom_id"])]
    pp = trace_parse.parse_pieces(str(rec.get("answer_text") or ""), n, int(item["params"]["lines"]))
    out = [scoring.state_key(pp.entries[i]) if i in pp.entries else None for i in range(1, n + 1)]
    right = sum(1 for e, c in zip(out, _piece_keys(item)) if e == c)
    if "pieces_right" in row and int(row["pieces_right"]) != right:                               # type: ignore[call-overload]
        raise ValueError(f"{row['custom_id']}: {right} pieces right here, {row['pieces_right']} in the row")
    return out


def _piece_keys(item: Mapping[str, object]) -> List[str]:
    return [scoring.state_key(a) for a in item["answer"]]                                          # type: ignore[union-attr]


def _pieces_by_puzzle(ctx: Dict[str, object], setup: str, n_designed: int) -> Dict[str, List[List[Optional[str]]]]:
    """{item_id: the designed tries' piece votes} at 6x1 for one arm, a missing try filled as all None; more rows than designed raises."""
    pieces = _shapes(ctx)[0]
    key = ("pieces", setup)
    c = _cache(ctx)
    if key not in c:
        by: Dict[str, List[List[Optional[str]]]] = {i: [] for i in _puzzles(ctx, pieces)}
        for r in list(ctx["rows"]) + list(ctx["other"]):                                           # type: ignore[call-overload]
            if r["setup"] == setup and r["shape"] == pieces:
                by[str(r["item_id"])].append(_piece_entries(ctx, r))
        for i, tries in by.items():
            if len(tries) > n_designed:
                raise ValueError(f"{i} {setup}: {len(tries)} rows, {n_designed} designed")
            tries += [[None] * _n(ctx)] * (n_designed - len(tries))
        c[key] = by
    return c[key]                                                                                  # type: ignore[return-value]


def _present_at_pieces(ctx: Mapping[str, object]) -> set:
    pieces = _shapes(ctx)[0]
    return {str(r["setup"]) for r in list(ctx["rows"]) + list(ctx["other"]) if r["shape"] == pieces}  # type: ignore[call-overload]


def per_piece_accuracy(ctx: Dict[str, object]) -> Dict[str, object]:
    """Item 7, "Per-piece accuracy, for every arm" (X5: the arms of the 80-base design): per try the share of its 6 pieces right; per
    puzzle the mean over its DESIGNED tries (a missing try counts 0); the mean over the base puzzles; the shared cluster bootstrap named
    "per_piece:<arm>". The D-42 and real-time arms are out (X5)."""
    present = _present_at_pieces(ctx)
    out: Dict[str, object] = {}
    for setup in _arm_tags():
        if setup not in present:
            continue
        n_designed = designed(setup)
        by = _pieces_by_puzzle(ctx, setup, n_designed)
        per: Dict[str, float] = {}
        for i, tries in by.items():
            keys = _piece_keys(ctx["items"][i])                                                    # type: ignore[index]
            per[_base_of(ctx, i)] = math.fsum(sum(1 for e, c in zip(t, keys) if e == c) / _n(ctx) for t in tries) / n_designed
        out[setup] = {"designed_tries": n_designed, "n_puzzles": len(per), "mean": _mean(list(per.values())),
                      "ci95": _interval(list(per), per, f"per_piece:{setup}", _cluster_draws(ctx))}
    left = sorted(s for s in present if s not in _arm_tags())
    return {"arms": out, "out_of_design": {s: OUT_OF_DESIGN for s in left}}


def _piece_answers(ctx: Dict[str, object]) -> Dict[str, Tuple[List[List[Optional[str]]], List[str]]]:
    """{item_id: (for each piece, the 40 Haiku-medium samples' votes; the right key per piece)} at 6x1 (item 7)."""
    by = _pieces_by_puzzle(ctx, HAIKU, DESIGNED)
    out = {}
    for i, tries in by.items():
        out[i] = ([[t[p] for t in tries] for p in range(_n(ctx))], _piece_keys(ctx["items"][i]))  # type: ignore[index]
    return out


def per_piece_vote_at(ctx: Dict[str, object], k: int) -> Dict[str, object]:
    """Item 7, "The per-piece vote" at k (k_O or k_S): the per-piece vote curve's value and band at that k (C4 item 1: the points need no
    names of their own; they use the curve's one name and draws)."""
    return dict(item_7_curve_points(ctx)[k - 1])


def per_piece_curve(ctx: Dict[str, object]) -> Dict[str, object]:
    """Item 7, "Also the per-piece vote curve for k = 1 to 40, computed the same way" (held to min(40, designed 40), X2):
    {item_id: per piece, votes.vote_curve(detail=True)}."""
    c = _cache(ctx)
    if "piece_curve" not in c:
        kmax = min(CAP, DESIGNED)
        c["piece_curve"] = {i: [votes.vote_curve(a, key, kmax=kmax, detail=True, tie=TIE) for a, key in zip(answers, keys)]
                            for i, (answers, keys) in _piece_answers(ctx).items()}
    return c["piece_curve"]                                                                        # type: ignore[return-value]


def item_7_curve_points(ctx: Dict[str, object]) -> List[Dict[str, object]]:
    """Item 7's per-piece vote curve (and item 8b's "at 6x1, also in the per-piece unit"), k = 1..40: per base puzzle the mean over its 6
    pieces of the piece's vote@k (votes.vote_accuracy_at_k over the 40 samples' entries, a missing or unreadable entry a vote for nothing,
    the D-33 tie rule); the mean over puzzles, with the shared cluster bootstrap under ONE name for the whole curve,
    "per_piece_vote_curve:haiku-med", every k sharing its draws (C4 item 1). Memoised."""
    c = _cache(ctx)
    if "piece_curve_points" not in c:
        curve = per_piece_curve(ctx)
        n = _n(ctx)
        points = []
        for k in range(1, min(CAP, DESIGNED) + 1):
            per = {_base_of(ctx, i): math.fsum(float(pc[k - 1]["acc"]) for pc in curve[i]) / n for i in sorted(curve)}   # type: ignore[arg-type]
            points.append({"k": k, "n_puzzles": len(per), "mean": _mean(list(per.values())),
                           "ci95": _interval(list(per), per, PER_PIECE_CURVE_NAME, _cluster_draws(ctx)),
                           "bootstrap_name": PER_PIECE_CURVE_NAME})
        c["piece_curve_points"] = points
    return c["piece_curve_points"]                                                                 # type: ignore[return-value]


def item_7(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note Addendum A item 7, the per-piece view at 6x1 (D-23, D-39 item 3): per-piece accuracy for every arm of the design (X5), the
    Haiku-medium per-piece vote at k_O and at k_S(6x1) (item 11), the per-piece vote curve, and the cost per task (one piece is one task):
    a single-call arm's mean list cost per 6x1 puzzle (9b) / 6; a multi-try arm's single-try view, ONE sample's mean list cost per puzzle
    / 6 (X7); the vote at k, k x that / 6. Secondary, descriptive, no test."""
    pieces = _shapes(ctx)[0]
    n = _n(ctx)
    ks = k_s_pieces(ctx)
    k_by = {"O": _k_o(ctx)[pieces], "S": int(ks["k"])}                                            # type: ignore[call-overload]
    vote: Dict[str, object] = {}
    for w, k in k_by.items():
        name = K_NAMES[w]
        vote[name] = (per_piece_vote_at(ctx, k) if k >= 1
                      else {"k": k, "computed": False, "reason": "k = 0: not run (D-33)"})
    vote[K_NAMES["S"]]["k_value"] = ks                                                             # type: ignore[index]
    cost: Dict[str, object] = {}
    present = _present_at_pieces(ctx)
    for setup in _arm_tags():
        if setup not in present:
            continue
        b = report_costs.cost_block(ctx, setup, pieces)
        m = b["mean"]
        cost[setup] = {"cost_per_puzzle": m, "cost_per_task": (m / n) if m is not None else None,      # type: ignore[operator]
                       "unit": "one sample (X7)" if designed(setup) > 1 else "one call", "calls_without_record": b["calls_without_record"]}
    h = report_costs.cost_block(ctx, HAIKU, pieces)["mean"]
    for w, k in k_by.items():
        cost[f"{HAIKU} vote at {K_NAMES[w]}"] = {"k": k, "cost_per_puzzle": (k * h) if h is not None else None,   # type: ignore[operator]
                                                 "cost_per_task": (k * h / n) if h is not None else None}         # type: ignore[operator]
    return {"label": PER_PIECE_LABEL, "shape": pieces, "per_piece_accuracy": per_piece_accuracy(ctx), "per_piece_vote": vote,
            "per_piece_vote_curve": {"bootstrap_name": PER_PIECE_CURVE_NAME, "points": item_7_curve_points(ctx)},
            "cost_per_task": cost, "note": "list cost (item 9a); a vote at k costs k x the mean list cost per sample (9b)"}


# ---------------------------------------------------------------- item 8: the k-sensitivity set

def k_values(ctx: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    """Note item 8a, per vote test (t1 Opus at 6x1, t2 Opus at 1x6, t3 Sonnet at 1x6), from the kscript.k_table cell on the cost-only
    rows (Batch, rt* left out), with "samples drawn" the designed 40 (X2): k from the median ratio and k from the pilot
    (kscript.k_sensitivity, held to 1..min(40, 40)), the interpolated k* (kscript.k_star on the cell's exact cost ratio) and k-2..k+2 around
    the test's own confirmatory k (k.json), a value outside 1..40 HELD at the nearest allowed k and flagged "held at the limit" (X8). A test
    whose confirmatory k is 0 is not run in any row (kscript.k_sensitivity: "there is nothing to vary")."""
    cells = _k_cells(ctx)
    out: Dict[str, Dict[str, object]] = {}
    upper = min(CAP, DESIGNED)
    for t, (comp, shape, which) in _vote_tests(ctx).items():
        k_conf = _confirmatory_k(ctx, shape, which)
        cell = cells.get((which, shape))
        if cell is None:
            raise ValueError(f"{t}: no kscript.k_table cell for {COMPARATOR_KEY[which]} at {shape}")
        pilot = PILOT_RATIO[(COMPARATOR_KEY[which], shape)]
        sens = kscript.k_sensitivity(k_conf, cell["median_ratio"], pilot, CAP, DESIGNED)
        ks = kscript.k_star(cell["ratio"], 1, cap=CAP, samples_drawn=DESIGNED)                     # the cell's exact ratio over 1: k* = ratio, held
        ks = dict(ks, comparator_cost_per_puzzle=cell["comparator_cost_per_puzzle"], haiku_cost_per_sample=cell["haiku_cost_per_sample"])
        row_k: Dict[str, object] = {}
        held: Dict[str, Dict[str, int]] = {}
        if k_conf < 1:
            row_k = {name: 0 for name in ROW_NAMES}
        else:
            row_k["median ratio"] = sens["k_median_ratio"]
            row_k["pilot"] = sens["k_pilot_ratio"]
            row_k["k*"] = 0 if ks["h1_not_run"] else ks["k_star"]
            for d, name in zip(range(-2, 3), BAND_NAMES):
                v = k_conf + d
                row_k[name] = max(1, min(upper, v))
                if row_k[name] != v:
                    held[name] = {"k_plus_d": v, "held_at": int(row_k[name])}                      # type: ignore[call-overload]
        out[t] = {"comparator": comp, "shape": shape, "k_confirmatory": k_conf, "k_table_k": cell["k"],
                  "k_table_matches_confirmatory": int(cell["k"]) == k_conf, "samples_drawn_designed": DESIGNED,   # type: ignore[call-overload]
                  "k_table_samples_drawn": cell["samples_drawn"], "ratio": cell["ratio"], "median_ratio": cell["median_ratio"],
                  "pilot_ratio": pilot, "sensitivity": sens, "k_star": ks, "row_k": row_k, "held_at_the_limit": held}
    return out


def item_8a(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note Addendum A item 8a (D-33 item 9): the k values of every k-sensitivity row, per vote test."""
    return {"k_values": k_values(ctx), "pilot_table_sha256": PILOT_TABLE_SHA256, "pilot_set": PILOT_SET,
            "samples_drawn": f"the designed {DESIGNED} (Addendum C, X2)"}


def _kstar_scores(ctx: Dict[str, object], shape: str, kstar: Fraction) -> Dict[str, float]:
    """Item 8a: each base's challenger score at k* is votes.interpolated_vote_accuracy(answers, correct, k*) (official score, as_deployed,
    tie "random"), in points; the answers are five_tests' own (`_haiku_answers`: a missing sample is a vote for nothing)."""
    out = {}
    for base, d in arm_answers(ctx, HAIKU, shape).items():
        if d["answers"]:
            out[base] = 100.0 * float(votes.interpolated_vote_accuracy(d["answers"], d["correct"], kstar, cap=CAP, tie=TIE)["acc"])  # type: ignore[arg-type]
    return out


def sensitivity_rows(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note item 8b, "Each k-sensitivity row is the whole five-test family re-run": five_tests._family (bootstrap.run_family with the
    confirmatory B, seeds, margin and Holm; a test with k = 0 keeps its Holm place with p = 1) over five_tests.test_differences (official,
    as_deployed), t1-t3 at the row's k, t4 and t5 unchanged; the k* row uses the interpolated scores. A test held at the limit (X8) runs at
    its held k with its real p and is labelled "held at the limit"."""
    kv = k_values(ctx)
    rows = list(ctx["rows"])                                                                       # type: ignore[call-overload]
    n = _n(ctx)
    out: Dict[str, object] = {}
    for name in ROW_NAMES:
        k_by = {t: v["row_k"][name] for t, v in kv.items()}                                        # type: ignore[index]
        if name == "k*":
            diffs = five_tests.test_differences(rows, _k_o(ctx), _k_s(ctx), "as_deployed", n=n)
            for t, (comp, shape, _) in _vote_tests(ctx).items():
                ks = k_by[t]
                if not ks:
                    diffs[t] = []
                    continue
                c = _kstar_scores(ctx, shape, ks)                                                 # type: ignore[arg-type]
                diffs[t] = scoring.paired_differences(c, five_tests.single_scores(rows, comp, shape, "as_deployed"))
        else:
            k_o, k_s = _ks_for_family(ctx, k_by)                                                   # type: ignore[arg-type]
            diffs = five_tests.test_differences(rows, k_o, k_s, "as_deployed", n=n)
        fam = five_tests._family(diffs, _family_draws(ctx), bootstrap.SEED)
        held = {t: v["held_at_the_limit"][name] for t, v in kv.items() if name in v["held_at_the_limit"]}   # type: ignore[operator, index]
        for t, h in held.items():
            fam["tests"][t] = dict(fam["tests"][t], k_label=HELD_LABEL, **h)                       # type: ignore[index]
        out[name] = dict(fam, label=ROW_LABEL, computed=True, k_used=k_by, held_at_the_limit=sorted(held))
    return out


def realised_spend_at_k(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note item 8b, "Realised spend at k" (D-33 item 10): for each test and each row's k (a held k as held, X8),
    kscript.realised_spend(k, comparator list cost per puzzle, Haiku list cost per sample, n_puzzles), the costs being the ONE 9b copy
    (report_costs.base_costs, exact: the mean over the base puzzles of the comparator's cost per puzzle and of Haiku's cost per sample, a
    designed call with no record at $0 and its puzzle kept, X4; Edith driver review r8, V-1), and n_puzzles the set's base puzzles at the
    shape (80 in the main set). k* enters as its exact value."""
    kv = k_values(ctx)
    out: Dict[str, object] = {}

    def mean_cost(arm: str, shape: str) -> Fraction:
        costs, _ = report_costs.base_costs(ctx, arm, shape)
        vals = [v for v in costs.values() if v is not None]
        return sum(vals, Fraction(0)) / len(vals) if vals else Fraction(0)
    for t, (comp, shape, which) in _vote_tests(ctx).items():
        n_p = len(_puzzles(ctx, shape))
        comp_c, h_c = kscript._d(mean_cost(comp, shape)), kscript._d(mean_cost(HAIKU, shape))
        per: Dict[str, object] = {}
        for name in ROW_NAMES:
            k = kv[t]["row_k"][name]                                                               # type: ignore[index]
            if not k:
                per[name] = None
                continue
            kk = kscript._d(k) if isinstance(k, Fraction) else k
            per[name] = dict(kscript.realised_spend(kk, comp_c, h_c, n_p), k=k)                    # type: ignore[arg-type]
        out[t] = {"comparator": comp, "shape": shape, "n_puzzles": n_p, "comparator_list_cost_per_puzzle": comp_c,
                  "haiku_list_cost_per_sample": h_c, "by_row": per}
    return {"priced": "list (item 9a)", "tests": out}


def vote_curve(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note item 8b, "The 1-40 vote curve" (D-33 item 5), per shape, Haiku-medium (`curve_summary`); at 6x1 also the per-piece unit (item
    7)."""
    out: Dict[str, object] = {shape: curve_summary(ctx, HAIKU, shape) for shape in _shapes(ctx)}
    out["per_piece_" + _shapes(ctx)[0]] = item_7_curve_points(ctx)
    return out


def sign_flip_check(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note item 8b, "The sign-flip check for d = 0" (7b): for each test that ran, bootstrap.sign_flip_p(diffs, null=0.0, nflips=100_000,
    seed=derive_seed(20261011, f"{test}:sign_flip")) on its confirmatory per-base differences (official, as_deployed); one-sided p for "the
    challenger is better than the comparator", unadjusted."""
    diffs = five_tests.test_differences(list(ctx["rows"]), _k_o(ctx), _k_s(ctx), "as_deployed", n=_n(ctx))  # type: ignore[call-overload]
    out: Dict[str, object] = {"label": SIGN_FLIP_LABEL}
    for t, d in diffs.items():
        if not d:
            out[t] = {"ran": False, "p": None}
            continue
        out[t] = {"ran": True, "n": len(d), "p": bootstrap.sign_flip_p(d, null=0.0, nflips=SIGN_FLIP_NFLIPS,
                                                                        seed=bootstrap.derive_seed(SIGN_FLIP_SEED, f"{t}:sign_flip"))}
    return out


def item_8b(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note Addendum A item 8b (D-33 items 5, 9, 10; 7b): the k-sensitivity rows, the realised spend at k, the 1-40 vote curve and the
    sign-flip check."""
    return {"rows": sensitivity_rows(ctx), "realised_spend": realised_spend_at_k(ctx), "vote_curve": vote_curve(ctx),
            "sign_flip": sign_flip_check(ctx)}


# ---------------------------------------------------------------- item 18: how vote@k was computed

def item_18(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note Addendum B item 18 (D-33 item 8): for each test that uses a vote (t1-t3 at its confirmatory k, official score, each of the three
    views, with exactly vote_scores' call) and for the vote curve (each shape and k; also the per-piece curve), the method (exact or
    sampled) with the number of base puzzles of each and the largest mc_se (0 for exact), as votes.vote_accuracy_at_k returns them."""
    rows = list(ctx["rows"])                                                                       # type: ignore[call-overload]
    scoring.check_answer_only(rows)
    tests: Dict[str, object] = {}
    for t, (_, shape, which) in _vote_tests(ctx).items():
        k = _confirmatory_k(ctx, shape, which)
        if k < 1:
            tests[t] = {"k": k, "ran": False}
            continue
        views: Dict[str, object] = {}
        for view in scoring.VIEWS:
            res = [votes.vote_accuracy_at_k(d["answers"], d["correct"], min(k, len(d["answers"])), tie=TIE)  # type: ignore[arg-type]
                   for d in five_tests._haiku_answers(rows, shape, view, DESIGNED, "official").values() if d["answers"]]
            views[view] = {"exact": sum(1 for r in res if r["method"] == "exact"),
                           "sampled": sum(1 for r in res if r["method"] == "sampled"),
                           "max_mc_se": max((float(r["mc_se"]) for r in res), default=None)}      # type: ignore[arg-type]
        tests[t] = {"k": k, "ran": True, "views": views}
    curve: Dict[str, object] = {}
    for shape in _shapes(ctx):
        per_base = arm_curve(ctx, HAIKU, shape)
        curve[shape] = [dict({"k": k}, **{x: v for x, v in _curve_summary(per_base, k).items() if x != "tie_decided_share_mean"})
                        for k in range(1, min(CAP, DESIGNED) + 1)]
    pc = per_piece_curve(ctx)
    flat = {f"{i}:{p}": v for i, pieces in pc.items() for p, v in enumerate(pieces, 1)}            # type: ignore[union-attr]
    curve["per_piece_" + _shapes(ctx)[0]] = [dict({"k": k}, **{x: v for x, v in _curve_summary(flat, k).items()
                                                                if x != "tie_decided_share_mean"}) for k in range(1, min(CAP, DESIGNED) + 1)]
    return {"tests": tests, "vote_curve": curve,
            "note": "per-piece counts are per (puzzle, piece); votes over at most 40 samples are exact under mode 'auto' "
                    "(at most 40 distinct wrong answers <= votes.MAX_EXACT_DISTINCT)"}


# ---------------------------------------------------------------- item 20: the vote lookup chart

BIN_LABELS = tuple(f"[{10 * b},{10 * b + 10})" for b in range(9)) + ("[90,100]",)
TOO_FEW = "too few wrong tries"
THIRD_NAMES = ("t1", "t2", "t3")                       # X6: <third> is t1, t2, t3 or few
FEW_NAME = "few"


def _thirds(ctx: Mapping[str, object], shares: Mapping[str, float]) -> Dict[str, int]:
    """Item 20 step 2 (C1 item 20): sort the bin's puzzles by (agreement, base_id), ascending; puzzle i (from 0) goes to third
    floor(3i / n); a whole tie group (equal agreement) takes the third of its first member, so ties go to the lower third.
    Returns {item_id: 0 | 1 | 2}."""
    order = sorted(shares, key=lambda i: (shares[i], _base_of(ctx, i)))
    n = len(order)
    first: Dict[float, int] = {}
    out: Dict[str, int] = {}
    for idx, i in enumerate(order):
        out[i] = first.setdefault(shares[i], (3 * idx) // n)
    return out


def _cell(ctx: Dict[str, object], shape: str, puzzles: Sequence[str], opus: Mapping[str, float], name: str) -> Dict[str, object]:
    """Item 20 steps 3 and 4 for one cell: the mean vote@k for k = 1..min(40, designed) (item 8 curve), each with the shared cluster
    bootstrap drawn from the cell's own base puzzles, one name per cell (X6); and the smallest k at which the cell's mean vote@k reaches
    Opus-medium's mean accuracy on the same puzzles, "reaches" being >= after rounding both to 1e-9 (C1 item 20), else "none up to 40"
    (a point value, no band)."""
    kmax = min(CAP, DESIGNED)
    bases = [_base_of(ctx, i) for i in puzzles]
    m = len(bases)
    curve = arm_curve(ctx, HAIKU, shape)
    absent = [b for b in bases if b not in curve]
    if absent:
        raise ValueError(f"{absent[0]}: no Haiku-medium row at {shape} (build the rows with the planned requests: missing tries are rows)")
    opus_mean = math.fsum(opus[i] for i in puzzles) / m
    points, reach = [], None
    for k in range(1, kmax + 1):
        vals = {b: float(curve[b][k - 1]["acc"]) for b in bases}                                  # type: ignore[arg-type]
        mean = math.fsum(vals.values()) / m
        points.append({"k": k, "mean": mean, "ci95": _interval(bases, vals, name, _cluster_draws(ctx))})
        if reach is None and round(mean, REACH_DIGITS) >= round(opus_mean, REACH_DIGITS):
            reach = k
    return {"puzzles": list(puzzles), "n": m, "opus_med_mean": opus_mean, "bootstrap_name": name, "mean_vote_at_k": points,
            "smallest_k_reaching_opus": reach if reach is not None else f"none up to {kmax}"}


def item_20(ctx: Dict[str, object]) -> Dict[str, object]:
    """Note Addendum B item 20, the vote lookup chart (mock-review Fix 7), per shape: step 1, each base puzzle's Haiku-medium single-try
    accuracy (official, as_deployed, over its 40 designed samples: main_analysis._per_puzzle_share, a missing sample wrong) puts it in a
    10-point bin, the last bin including 100; step 2, its pairwise wrong-try agreement (item 4's per-puzzle share: main_analysis.repeat_share's
    pairing, real calls only, a None key never agreeing; scoring.pairwise_agreement), puzzles with fewer than 2 wrong tries forming the
    group "too few wrong tries" (`few`), the rest cut into thirds t1-t3 (`_thirds`, C1); steps 3 and 4 per cell (`_cell`), the band named
    "lookup:<shape>:<bin lower edge>:<third>" (X6)."""
    rows = list(ctx["rows"])                                                                       # type: ignore[call-overload]
    out: Dict[str, object] = {}
    for shape in _shapes(ctx):
        puzzles = _puzzles(ctx, shape)
        hm = [r for r in rows if r["setup"] == HAIKU and r["shape"] == shape]
        share, missing = _per_puzzle_share(hm, DESIGNED, puzzles)
        opus, _ = _per_puzzle_share([r for r in rows if r["setup"] == "opus-med" and r["shape"] == shape], 1, puzzles)
        wrong: Dict[str, List[object]] = defaultdict(list)
        for r in hm:
            if r.get("kind") == "missing" or scoring.row_correct(r, "official"):
                continue                                                                           # real calls only (Edith N-4)
            key = scoring.vote_key(r, "official")
            wrong[str(r["item_id"])].append(key if key is not None else object())                  # a None key never agrees (D-72.1)
        per: Dict[str, object] = {}
        bins: Dict[int, List[str]] = defaultdict(list)
        for i in puzzles:
            right = round(share[i] * DESIGNED)
            if right / DESIGNED != share[i]:
                raise ValueError(f"{i}: share {share[i]} is not a count over {DESIGNED}")
            b = min(9, (100 * right) // (10 * DESIGNED))
            agr = scoring.pairwise_agreement(wrong.get(i, []))
            per[i] = {"accuracy_points": 100.0 * share[i], "bin": BIN_LABELS[b], "wrong_tries": len(wrong.get(i, [])),
                      "agreement_share": None if not agr["pairs"] else agr["share"], "group": TOO_FEW if not agr["pairs"] else None}
            bins[b].append(i)
        table: Dict[str, object] = {}
        for b in range(10):
            ids = bins.get(b, [])
            if not ids:
                continue
            edge = 10 * b
            few = [i for i in ids if per[i]["group"] == TOO_FEW]                                   # type: ignore[index]
            rest = {i: float(per[i]["agreement_share"]) for i in ids if per[i]["group"] != TOO_FEW}  # type: ignore[index, arg-type]
            cut = _thirds(ctx, rest) if rest else {}
            for i, t in cut.items():
                per[i]["third"] = THIRD_NAMES[t]                                                   # type: ignore[index]
            for i in few:
                per[i]["third"] = FEW_NAME                                                         # type: ignore[index]
            entry: Dict[str, object] = {"puzzles": len(ids), "bin_lower_edge": edge,
                                        TOO_FEW: _cell(ctx, shape, few, opus, f"lookup:{shape}:{edge}:{FEW_NAME}") if few else None,
                                        "thirds": {THIRD_NAMES[t]: _cell(ctx, shape, sorted(i for i in rest if cut[i] == t), opus,
                                                                         f"lookup:{shape}:{edge}:{THIRD_NAMES[t]}")
                                                   for t in (0, 1, 2) if any(cut[i] == t for i in rest)}}
            table[BIN_LABELS[b]] = entry
        out[shape] = {"missing_haiku_tries": missing, "per_puzzle": per, "bins": table}
    return out


# ---------------------------------------------------------------- the pilot ratios, and the whole report

def pilot_ratios_from_table(table: Path) -> Dict[Tuple[str, str], Fraction]:
    """Item 8a's pilot ratios recomputed: kscript.k_table (include_realtime=False) on the ladder's compact_table.csv (its SHA-256 checked;
    only k_step.COLUMNS read), set ladder-ledger-l14n6-v1. Returns {(comparator key, shape): exact ratio}."""
    import hashlib
    have = hashlib.sha256(Path(table).read_bytes()).hexdigest()
    if have != PILOT_TABLE_SHA256:
        raise ValueError(f"{table}: SHA-256 {have}, the note names {PILOT_TABLE_SHA256}")
    rows = kscript.rows_of_sets(k_step.read_cost_columns(Path(table)), [PILOT_SET])
    t = kscript.k_table(rows, cap=CAP, include_realtime=False)
    return {(str(c["comparator_key"]), str(c["shape"])): c["ratio"] for side in ("opus", "sonnet") for c in t[side]
            if c["haiku_key"] == "haiku-medium"}


def report(ctx: Dict[str, object]) -> Dict[str, object]:
    """Every item of this module, under the note's numbering, with the questions still open."""
    return {"note": NOTE, "item_7": item_7(ctx), "item_8a": item_8a(ctx), "item_8b": item_8b(ctx), "item_18": item_18(ctx),
            "item_20": item_20(ctx), "open_questions": dict(OPEN_QUESTIONS)}
