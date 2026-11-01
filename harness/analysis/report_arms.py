"""Reporting items 10-17, 21 and 24 of Karen's dated note `research/reporting-definitions-main.md` (93334b8, Edith CLEAN; Addenda A, B
and C; inventory group B, `research/reporting-inventory-main.md`): the exploratory arms, tests 3 and 5 at 6x1, exact single-arm intervals,
the first-slip repeat share, slips per rule kind, the near-ceiling label, refusals / truncations / missing / retries, the format flag, E3
fixed-3 and every setup's results with the three-model chart. Plumbing only: every number, seed, B, threshold and edge rule comes from the
note or from the locked code it names; each function cites its section. The readings Edith ruled on (r7: I1-I8) are listed in
`INTERPRETATIONS` as ruled.

    res = report_arms.report(ctx)

`ctx` keys: "rows" (main_rows.build(...)["tests"], with the missing rows of `planned`), "other" (main_rows.build(...)["other"]), "missing"
(main_rows.build(...)["missing"]), "records" (the final call-log records: answer_text, usage_raw, kind, stop_reason, batch_id, meta),
"all_records" (every call-log line, final or not, batch_* lines included), "items" ({item_id: frozen item}), "set_id", "n" (6), "k"
(k.json: k_o per shape, k_s), "run_dir" (or None). Tests only: "B" (the 10,000 paired-bootstrap draws) and "draws" (the 2,000 cluster /
fairness draws).

Shared copies (Addendum C, C3): the list cost (9a), dollars per puzzle (9b) and CPC (9c) are report_costs' (`calls`, `cost_block`,
`cpc_block`); the vote curve (item 8) is report_votes' (`arm_answers`, `curve_summary`). Bootstrap names use the main_rows arm names
(X1): "explore:<arm>:<comparator>:<shape>", "accuracy:<arm>:<shape>" (X6), and the shared modules' names. No model or API call;
standard library only.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import bootstrap, fairness, fairness_input, five_tests, kscript, main_analysis, main_rows, report_costs, report_votes, scoring, votes
from .curve import _puzzle, cluster_bootstrap, wilson
from ..pareto import e3 as e3mod
from ..pareto import main as mainmod
from ..pareto import prices
from ..pareto.outcome import usage_from_raw

NOTE = "research/reporting-definitions-main.md (93334b8)"
TEST_SEED = bootstrap.SEED                    # 20261011, Addendum A shared conventions ("tests and test-like rows")
TEST_B = bootstrap.DRAWS                      # 10,000
MARGIN = bootstrap.MARGIN                     # -10
CAP = kscript.CAP                             # 40
FORMAT_FLAG_PERCENT = 5                       # item 17: "above 5.0%"
FAILURE_KINDS = ("empty", "unexpected_stop", "error")   # item 16 (Edith r7): real results, reported as their own kinds
OUTSIDE_HOLM_LABEL = "unadjusted (exploratory, outside Holm)"   # item 11 (Edith r7, I1)
TAG_OF = {name: tag for tag, name in {**main_rows.FIVE_TEST_ARMS, **main_rows.OTHER_ARMS}.items()}
TAG_OF["e3"] = main_rows.E3_TAG
ARM_OF_TAG = {tag: name for name, tag in TAG_OF.items()}
MAIN_ARMS = tuple(main_rows.FIVE_TEST_ARMS.get(su.name) or main_rows.OTHER_ARMS[su.name] for su in mainmod.MAIN_SETUPS)   # X5
HAIKU_EXPLORE = ("haiku-low", "haiku-thinking-off", "haiku-max")        # item 10: hl x40, ho x40, hx x3
ONE_TRY_ARMS = ("opus-med", "opus-low", "sonnet-med", "sonnet-low")    # item 12
SLIP_ARMS = ("haiku-med", "opus-med", "opus-low", "sonnet-med", "sonnet-low", "haiku-low", "haiku-thinking-off", "haiku-max")  # item 14
T_PLUS = scoring.T_KINDS + ("avg_donors", "rank_move", "count_move")    # item 14
G_MINUS = ("two_clause", "compare_move")                                # item 14
NEAR_CEILING_LABEL = "near ceiling (Amendment 1)"                       # item 15
E3_RATES_LABEL = "over the E3 calls actually made (E3 has no designed count; C1 item 16)"
NO_MISSING = "no missing items in the five tests' arms"   # item 16; Edith driver review r8, A-2 (other arms: item 16's rates)

OPEN_QUESTIONS: Dict[str, str] = {}           # every question of 5dfaf07 is answered by Addendum C (X1-X6, C1, C2) or Edith r7

INTERPRETATIONS: Dict[str, str] = {
    "I1": "Accepted (Edith r7): item 11's three-way reading 'outside the Holm family' is a family of one, bootstrap.holm_one_sided({test: "
          "p}) declaring it iff p <= 0.025, then bootstrap.three_way at margin -10; labelled 'unadjusted (exploratory, outside Holm)'.",
    "I2": "Accepted (Edith r7): item 14 T+/G- is the driver's fairness family (fairness.fairness_indices over Haiku-, Opus- and "
          "Sonnet-medium, comparison Opus, local_steps view) with each step's class relabelled T+ / G- / other by its kind; flag K in that "
          "output is reported, never used as a flag.",
    "I3": "Replaced (Edith r7; C1 item 16): 'missing' is a planned try with no final record, the converter's kind 'missing' only (it "
          "matches the driver's missing_left_out). Final records of kind empty, unexpected_stop or error are real results: wrong, reported "
          "as their own kinds in the rates (count / designed calls), and kept by the exclude-missing view. E3: only an unfinished chain is "
          "missing.",
    "I4": "Accepted (Edith r7): item 16 retries: every real-time error record with HTTP status 429 or 5xx is counted (by status group), "
          "with how many of them were followed by another attempt of the same custom_id; Batch resubmits are later `batch_submitting` "
          "records that hold an errored / expired / canceled custom_id again.",
    "I5": "Accepted (Edith r7; C2): item 24's pooled Haiku median is the median over all 2 x bases puzzle values (both shapes), as "
          "curve._panels defines the pooled median.",
    "I6": "Accepted (Edith r7; C2): an arm's accuracy is the mean over base puzzles of scoring.arm_scores (points); a Haiku arm's chart "
          "point uses its single-try cost (9b at k = 1); its own k uses the arm's mean list cost per call against the comparator's mean "
          "per puzzle of its calls' list cost, as kscript.k_table defines both.",
    "I7": "Accepted (Edith r7; C2): item 8's per-k curve diagnostics are the method counts, the largest mc_se and the mean tie-decided "
          "share over base puzzles (report_votes.curve_summary).",
    "I8": "Accepted (Edith r7; C2): item 14: a try that did not answer (refusal, truncated, missing, ...) counts as unplaceable with its "
          "kind as the reason, as the driver's fairness input does (main_analysis._tries_for_fairness).",
}


# ---------------------------------------------------------------- shared plumbing

def _B(ctx: Mapping[str, object]) -> int:
    return report_costs.family_draws(ctx)


def _draws(ctx: Mapping[str, object]) -> int:
    return report_costs.cluster_draws(ctx)


def _all_rows(ctx: Mapping[str, object]) -> List[Mapping[str, object]]:
    return list(ctx["rows"]) + list(ctx.get("other") or [])                              # type: ignore[call-overload]


def _arm(rows: Iterable[Mapping[str, object]], setup: str, shape: str) -> List[Mapping[str, object]]:
    return [r for r in rows if r["setup"] == setup and r["shape"] == shape]


def _shapes(ctx: Mapping[str, object]) -> Tuple[str, str]:
    n = int(ctx["n"])                                                                    # type: ignore[call-overload]
    return scoring.pieces_shape(n), scoring.chain_shape(n)


def _mean(xs: Sequence[float]) -> Optional[float]:
    return math.fsum(xs) / len(xs) if xs else None


def _ci(lohi: Tuple[Optional[float], Optional[float]]) -> List[Optional[float]]:
    return [lohi[0], lohi[1]]


def _mean_scores(scores: Mapping[str, float]) -> Optional[float]:
    return _mean(list(scores.values()))


def _designed(setup: str) -> int:
    return mainmod.BY_NAME[TAG_OF[setup]].n


def _list_usd(ctx: Mapping[str, object], rs: Iterable[Mapping[str, object]]) -> str:
    """Item 9a's list cost (report_costs' copy) summed over the rows' real calls; a row with no record $0 (X4)."""
    cs = report_costs.calls(ctx)                                                         # type: ignore[arg-type]
    return str(sum((cs[str(r["custom_id"])]["list"] for r in rs if str(r.get("custom_id")) in cs), Decimal(0)))   # type: ignore[misc]


def _kind_counts(arm_rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    return {"tries": len(arm_rows),
            "refusals": sum(1 for r in arm_rows if r.get("kind") == "refusal"),
            "truncations": sum(1 for r in arm_rows if r.get("stop_reason") == "max_tokens"),
            "kinds": dict(sorted(Counter(str(r.get("kind")) for r in arm_rows).items()))}


def _accuracy_views(arm_rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    """scoring.arm_scores (official) in all three views: the mean over base puzzles, in points (I6)."""
    out: Dict[str, object] = {}
    for view in scoring.VIEWS:
        s = scoring.arm_scores([dict(r) for r in arm_rows], view, "official")
        out[view] = {"mean": _mean_scores(s), "n_base": len(s)}
    return out


def _accuracy_band(scores: Mapping[str, float], arm: str, shape: str, draws: int) -> Dict[str, object]:
    """X6: a multi-try arm's accuracy (the Haiku arms; E3's per-base score), items 12 and 24: the mean over base puzzles in points with the
    shared cluster bootstrap (2,000 draws, seed 20261012) named "accuracy:<arm>:<shape>"."""
    bases = sorted(scores)
    name = f"accuracy:{arm}:{shape}"
    ci = _ci(cluster_bootstrap([bases], lambda s: _mean([scores[b] for b in s]), name, draws=draws)) if bases else [None, None]  # type: ignore[arg-type]
    return {"mean": _mean_scores(scores), "n_base": len(bases), "ci95": ci, "bootstrap_name": name, "unit": "points"}


def _points(p: Mapping[str, object]) -> Dict[str, object]:
    """A report_votes curve point (a share, 0-1) in points."""
    ci = p["ci95"]
    return {"k": p["k"], "mean": None if p["mean"] is None else 100.0 * float(p["mean"]),                  # type: ignore[arg-type]
            "ci95": [None if x is None else 100.0 * float(x) for x in ci], "unit": "points"}              # type: ignore[union-attr]


# ---------------------------------------------------------------- item 12 (needed by 10 and 24)

def _binom_cdf(x: int, n: int, p: float) -> float:
    return math.fsum(math.comb(n, i) * p ** i * (1.0 - p) ** (n - i) for i in range(0, x + 1))


def clopper_pearson(x: int, n: int, level: float = 0.95) -> Tuple[float, float]:
    """Item 12: the two-sided Clopper-Pearson interval for x of n, by bisection on the binomial CDF (math.comb), pure Python. Lower end:
    the p with P(X >= x; p) = (1 - level)/2 (0 when x = 0); upper end: the p with P(X <= x; p) = (1 - level)/2 (1 when x = n). The
    bisection runs to the limit of float resolution (200 halvings)."""
    if not (0 <= x <= n and n > 0):
        raise ValueError(f"need 0 <= x <= n, n > 0; got x={x}, n={n}")
    tail = (1.0 - level) / 2.0

    def solve(f: Callable[[float], float], target: float) -> float:   # f increasing in p; returns the p with f(p) = target
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2.0
            if f(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0
    lower = 0.0 if x == 0 else solve(lambda p: 1.0 - _binom_cdf(x - 1, n, p), tail)      # P(X >= x; p) = tail
    upper = 1.0 if x == n else solve(lambda p: -_binom_cdf(x, n, p), -tail)             # P(X <= x; p) = tail (decreasing in p)
    return lower, upper


def _one_try(arm_rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    by: Dict[str, List[bool]] = defaultdict(list)
    for r in arm_rows:
        by[str(r["base_id"])].append(scoring.row_correct(r, "official"))
    many = sorted(b for b, v in by.items() if len(v) != 1)
    if many:
        raise ValueError(f"{many[0]}: a one-try arm with {len(by[many[0]])} rows on one base puzzle")
    x, n = sum(v[0] for v in by.values()), len(by)
    lo, hi = clopper_pearson(x, n) if n else (None, None)
    return {"x": x, "n": n, "accuracy": (100.0 * x / n) if n else None, "cp95": [None if lo is None else 100.0 * lo,
                                                                                   None if hi is None else 100.0 * hi], "unit": "points"}


def _multi_try_scores(ctx: Mapping[str, object], arm: str, shape: str) -> Dict[str, float]:
    """Official, as_deployed per-base scores in points: a Haiku arm's single-try accuracy over its tries (scoring.arm_scores); E3 its
    product-of-steps score (five_tests.e3_arm_scores)."""
    if arm == "e3":
        return five_tests.e3_arm_scores(list(ctx["rows"]), shape, "as_deployed")         # type: ignore[call-overload]
    return scoring.arm_scores([dict(r) for r in _arm(_all_rows(ctx), arm, shape)], "as_deployed", "official")


def item_12(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 12 (Addendum A; D-48 row 27, 7b): for every arm with one try per puzzle (Opus-medium, Opus-low, Sonnet-medium, Sonnet-low), per
    shape, x right out of n base puzzles (official score, as_deployed: a missing, refused, truncated or unparseable try is wrong) with
    the two-sided 95% Clopper-Pearson interval. The arms with several tries per puzzle (the Haiku arms) and E3's per-base score carry the
    shared cluster bootstrap "accuracy:<arm>:<shape>" instead (X6)."""
    rows = _all_rows(ctx)
    out: Dict[str, object] = {"note": f"{NOTE}, item 12", "one_try_arms": {}, "multi_try_arms": {}}
    for arm in ONE_TRY_ARMS:
        for shape in _shapes(ctx):
            ar = _arm(rows, arm, shape)
            if ar:
                out["one_try_arms"][f"{arm} {shape}"] = _one_try(ar)                       # type: ignore[index]
    for arm in tuple(a for a in MAIN_ARMS if _designed(a) > 1) + ("e3",):
        for shape in _shapes(ctx):
            scores = _multi_try_scores(ctx, arm, shape)
            if scores:
                out["multi_try_arms"][f"{arm} {shape}"] = _accuracy_band(scores, arm, shape, _draws(ctx))   # type: ignore[index]
    return out


# ---------------------------------------------------------------- item 10

def _own_k(ctx: Mapping[str, object], rows: Sequence[Mapping[str, object]], setup: str, comparator: str, shape: str) -> Dict[str, object]:
    """Item 10: kscript.k_value(comparator's mean list cost per puzzle, the arm's own mean list cost per sample, cap 40, held to the samples
    drawn = the arm's designed samples (X2)), the costs as kscript.k_table defines them (I6): over the real calls, at list price (item 9a,
    report_costs' copy)."""
    cs = report_costs.calls(ctx)                                                         # type: ignore[arg-type]
    comp: Dict[str, List[Decimal]] = defaultdict(list)
    for r in _arm(rows, comparator, shape):
        if str(r.get("custom_id")) in cs:
            comp[str(r["base_id"])].append(cs[str(r["custom_id"])]["list"])               # type: ignore[arg-type]
    calls = [cs[str(r["custom_id"])]["list"] for r in _arm(rows, setup, shape) if str(r.get("custom_id")) in cs]
    if not comp or not calls:
        return {"k": None, "reason": "no comparator or arm calls"}
    from fractions import Fraction
    comp_mean = sum((Fraction(sum(v, Decimal(0))) for v in comp.values()), Fraction(0)) / len(comp)
    h = Fraction(sum(calls, Decimal(0))) / len(calls)                                    # type: ignore[arg-type]
    if h <= 0:
        return {"k": None, "reason": "the arm's calls cost $0 at list price"}
    return kscript.k_value(comp_mean, h, cap=CAP, samples_drawn=_designed(setup))


def _paired(diffs: List[float], B: int, name: str) -> Dict[str, object]:
    if not diffs:
        return {"n": 0, "d": None, "ci95": None}
    r = bootstrap.paired_bca(diffs, margin=MARGIN, B=B, seed=bootstrap.derive_seed(TEST_SEED, name))
    return {"n": r["n"], "d": r["d"], "ci95": list(r["ci95"]), "seed_name": name}


def item_10(ctx: dict) -> Dict[str, object]:
    """Item 10 (Addendum A; D-39 item 6, D-33 item 3): the exploratory arms Haiku-low, Haiku thinking-off, Haiku-max and Sonnet-low, every
    number labelled exploratory, no Holm, no verdict. For each arm and shape: single-try whole-answer accuracy (scoring.arm_scores,
    official, all three views); format compliance and the rates (five_tests.format_report, five_tests.rates); refusal and truncation
    counts; list cost per puzzle (9b) and CPC (9c). Haiku arms: the vote curve k = 1..min(40, designed) as in item 8
    (report_votes.curve_summary) and the vote's CPC at each k (C1 9c); each arm's own equal-money k (kscript.k_value on its own mean list
    cost per sample) against Opus-medium and against Sonnet-medium per shape, held to the designed samples; the vote at that k against its
    comparator: paired per-base differences, as_deployed only (C1 item 10), bootstrap.paired_bca(margin -10, B 10,000, seed
    derive_seed(20261011, f"explore:{arm}:{comparator}:{shape}")), d and the 95% interval only. Sonnet-low: the same paired_bca against
    Sonnet-medium and against Opus-low, seed name f"explore:sonnet-low:{comparator}:{shape}". Names: main_rows arm names (X1)."""
    rows = _all_rows(ctx)
    B = _B(ctx)
    out: Dict[str, object] = {"note": f"{NOTE}, item 10", "label": "exploratory (no Holm, no verdict)", "arms": {}}
    for arm in HAIKU_EXPLORE + ("sonnet-low",):
        for shape in _shapes(ctx):
            ar = _arm(rows, arm, shape)
            if not ar:
                continue
            fr = five_tests.format_report(ar).get(arm, {}).get(shape)
            d: Dict[str, object] = {"accuracy": _accuracy_views(ar), "format_compliance": fr,
                                    "rates": five_tests.rates(ar).get(arm) if scoring.is_chain_shape(shape) else None,
                                    "counts": _kind_counts(ar)}
            scores = scoring.arm_scores([dict(r) for r in ar], "as_deployed", "official")
            if arm == "sonnet-low":
                d["cost_per_puzzle"] = report_costs.cost_block(ctx, arm, shape)
                d["cpc"] = report_costs.cpc_block(ctx, arm, shape)
                d["accuracy_cp95"] = _one_try(ar)
                d["paired"] = {}
                for comp in ("sonnet-med", "opus-low"):
                    c = five_tests.single_scores(rows, comp, shape, "as_deployed")
                    d["paired"][f"vs {comp}"] = _paired(scoring.paired_differences(scores, c), B,          # type: ignore[index]
                                                        f"explore:{arm}:{comp}:{shape}")
            else:
                n_designed = _designed(arm)
                curve = report_votes.curve_summary(ctx, arm, shape)
                d["vote_curve"] = curve
                d["cost_per_puzzle_single_try"] = report_costs.cost_block(ctx, arm, shape)
                d["cpc_by_k"] = [report_costs.cpc_block(ctx, arm, shape, k) for k in range(1, int(curve["k_max"]) + 1)]  # type: ignore[call-overload]
                d["own_k"] = {}
                for comp in ("opus-med", "sonnet-med"):
                    kv = _own_k(ctx, rows, arm, comp, shape)
                    entry: Dict[str, object] = {"k_value": kv}
                    k = kv.get("k")
                    if k:
                        v = five_tests.vote_scores([dict(r, setup="haiku-med") for r in ar], shape, int(k),  # type: ignore[call-overload]
                                                   "as_deployed", designed=n_designed)
                        c = five_tests.single_scores(rows, comp, shape, "as_deployed")
                        entry["vote_mean"] = _mean_scores(v)                                       # type: ignore[arg-type]
                        entry["paired"] = _paired(scoring.paired_differences(v, c), B, f"explore:{arm}:{comp}:{shape}")  # type: ignore[arg-type]
                        entry["cost_per_puzzle"] = report_costs.cost_block(ctx, arm, shape, int(k))   # type: ignore[call-overload]
                        entry["cpc"] = report_costs.cpc_block(ctx, arm, shape, int(k))                # type: ignore[call-overload]
                    else:
                        entry["vote"] = "not computed: k = 0 (the arm costs more per sample than the comparator) or no costs"
                    d["own_k"][f"vs {comp}"] = entry                                               # type: ignore[index]
            out["arms"][f"{arm} {shape}"] = d                                                      # type: ignore[index]
    return out


# ---------------------------------------------------------------- item 11

def k_s_pieces(ctx: dict) -> Dict[str, object]:
    """Item 11's k_S(6x1): report_votes.k_s_pieces, the one copy (the locked five_tests.k_from_rows on k_step's guarded cost rows; Edith
    driver review r8, A-1)."""
    return report_votes.k_s_pieces(ctx)


def item_11(ctx: dict) -> Dict[str, object]:
    """Item 11 (Addendum A; 7b "the other shape for tests 3 to 5 is exploratory"): test 5 at 6x1 (Opus-low against Sonnet-medium,
    single_scores, official) and test 3 at 6x1 (the Haiku-medium vote at k_S(6x1) against Sonnet-medium). For each, in all three views:
    d, the 95% BCa interval and the three-way reading at margin 10, bootstrap.paired_bca with seed derive_seed(20261011, f"{test}@6x1"),
    a family of one (declared iff p <= 0.025; C2, Edith r7 I1), labelled "unadjusted (exploratory, outside Holm)". Test 4 at 6x1 is not
    computed (E3 did not run at 6x1)."""
    rows = list(ctx["rows"])                                                               # type: ignore[call-overload]
    pieces = _shapes(ctx)[0]
    B = _B(ctx)
    ks = k_s_pieces(ctx)
    out: Dict[str, object] = {"note": f"{NOTE}, item 11", "label": OUTSIDE_HOLM_LABEL, "k_s_6x1": ks,
                              "t4@6x1": "not computed: E3 did not run at 6x1 (the choice is put to the user; readiness checklist)"}
    for test in ("t3", "t5"):
        name = f"{test}@6x1"
        res: Dict[str, object] = {}
        for view in scoring.VIEWS:
            if test == "t3":
                if int(ks["k"]) < 1:                                                          # type: ignore[call-overload]
                    res[view] = {"reading": "not run (k = 0: Haiku costs more per sample than the comparator)"}
                    continue
                c = five_tests.vote_scores(rows, pieces, int(ks["k"]), view)                   # type: ignore[call-overload]
            else:
                c = five_tests.single_scores(rows, "opus-low", pieces, view)
            diffs = scoring.paired_differences(c, five_tests.single_scores(rows, "sonnet-med", pieces, view))  # type: ignore[arg-type]
            if not diffs:
                res[view] = {"n": 0, "reading": "no paired base puzzles"}
                continue
            r = bootstrap.paired_bca(diffs, margin=MARGIN, B=B, seed=bootstrap.derive_seed(TEST_SEED, name))
            declared = bootstrap.holm_one_sided({name: float(r["p_one_sided"])})[name]       # type: ignore[arg-type]
            res[view] = {"n": r["n"], "d": r["d"], "ci95": list(r["ci95"]), "p": r["p_one_sided"], "declared": declared,  # type: ignore[call-overload]
                         "reading": bootstrap.three_way(declared, r["ci95"], MARGIN), "seed_name": name,  # type: ignore[arg-type]
                         "label": OUTSIDE_HOLM_LABEL}
        out[name] = res
    return out


# ---------------------------------------------------------------- placing tries (items 13, 14)

class _Placer:
    """scoring.local_steps / first_slip_steps per try, cached; a try that did not answer is unplaceable with its kind as the reason (I8)."""

    def __init__(self, ctx: Mapping[str, object]):
        self.items: Mapping[str, Mapping[str, object]] = ctx["items"]                      # type: ignore[assignment]
        self.texts = {str(r["custom_id"]): str(r.get("answer_text") or "") for r in ctx.get("records") or []}  # type: ignore[union-attr]
        self.puzzles: Dict[str, object] = {}
        self.cache: Dict[Tuple[str, bool], Dict[str, object]] = {}

    def place(self, r: Mapping[str, object], first_slip: bool) -> Dict[str, object]:
        key = (str(r["custom_id"]), first_slip)
        if key in self.cache:
            return self.cache[key]
        if r.get("kind") != "answered":
            placed: Dict[str, object] = {"unplaceable": str(r.get("kind")), "status": str(r.get("kind")), "steps": [], "signature": None}
        else:
            iid = str(r["item_id"])
            if iid not in self.puzzles:
                self.puzzles[iid] = _puzzle(self.items[iid])
            fn = scoring.first_slip_steps if first_slip else scoring.local_steps
            placed = fn(self.texts[str(r["custom_id"])], self.puzzles[iid])                 # type: ignore[arg-type]
        self.cache[key] = placed
        return placed


# ---------------------------------------------------------------- item 13

def item_13(ctx: Mapping[str, object], placer: Optional[_Placer] = None) -> Dict[str, object]:
    """Item 13 (Addendum B; spec slip analysis): unordered pairs of Haiku-medium tries in the same base puzzle and shape that are WRONG
    (official score) and PLACEABLE (scoring.first_slip_steps, official parse); a pair agrees when both have the same first-slip signature
    (sequence, step, written balances); scoring.pooled_repeat_share per shape and summed over both shapes."""
    placer = placer or _Placer(ctx)
    out: Dict[str, object] = {"note": f"{NOTE}, item 13"}
    for shape in _shapes(ctx):
        sigs: Dict[str, List[object]] = defaultdict(list)
        for r in _arm(ctx["rows"], "haiku-med", shape):                                    # type: ignore[arg-type]
            if scoring.row_correct(r, "official"):
                continue
            p = placer.place(r, first_slip=True)
            if p["unplaceable"] is not None:
                continue
            if p["signature"] is None:
                raise ValueError(f"{r['custom_id']}: a wrong placed try with no first slip")
            sigs[str(r["base_id"])].append(p["signature"])
        res = scoring.pooled_repeat_share(sigs)
        res["wrong_placeable_tries"] = sum(len(v) for v in sigs.values())
        out[shape] = res
    shapes = _shapes(ctx)
    pairs = sum(int(out[s]["pairs"]) for s in shapes)                                       # type: ignore[index]
    agree = sum(int(out[s]["agree"]) for s in shapes)                                       # type: ignore[index]
    out["both_shapes"] = {"pairs": pairs, "agree": agree, "share": (agree / pairs) if pairs else None}
    return out


# ---------------------------------------------------------------- item 14

def _table(placed: Sequence[Dict[str, object]], arm: str) -> Dict[str, object]:
    t = scoring.slip_table([(arm, p) for p in placed])
    rows = {row: dict(v) for (_, row), v in sorted(t.items())}
    h = rows.get("house")
    if h:
        h["missed_rate"] = h["missed"] / h["steps_house_fires"] if h["steps_house_fires"] else None
        h["misapplied_rate"] = h["misapplied"] / h["steps_house_should_not_fire"] if h["steps_house_should_not_fire"] else None
    rows["unplaceable_by_reason"] = dict(sorted(Counter(str(p.get("status")) for p in placed if p["unplaceable"] is not None).items()))
    return rows


def _relabel(placed: Dict[str, object]) -> Dict[str, object]:
    def cls(kind: str) -> str:
        return "T" if kind in T_PLUS else "G" if kind in G_MINUS else "other"
    return dict(placed, steps=[dict(st, cls=cls(str(st["kind"]))) for st in placed["steps"]])  # type: ignore[union-attr]


def _final_right(r: Mapping[str, object], shape: str) -> bool:
    """Item 14's split by the final answer: the row's correct_final at 1xN; at 6x1 the final answer is the whole answer, so correct_final
    = correct (C1 item 14)."""
    return (r.get("correct_final") if scoring.is_chain_shape(shape) else r.get("correct")) is True


def item_14(ctx: Mapping[str, object], placer: Optional[_Placer] = None) -> Dict[str, object]:
    """Item 14 (Addendum B; D-67, 7b, spec section 8): scoring.slip_table over scoring.local_steps (primary) and first_slip_steps
    (sensitivity) for every arm whose replies hold steps or pieces (Haiku-medium, Opus-medium, Opus-low, Sonnet-medium, Sonnet-low,
    Haiku-low, Haiku thinking-off, Haiku-max), both shapes (at 6x1 each piece is one step): per kind and class, steps checked and kind
    slips; the house rows (missed over should-fire steps, misapplied over should-not-fire steps); decoy confusion; the unplaceable tries
    with the parse reason (I8). Also the same tables split by the final answer (correct_final; at 6x1 correct, C1), and the T+/G-
    sensitivity split (T+ = T plus avg_donors, rank_move, count_move; G- = two_clause, compare_move) through the fairness machinery,
    reported, never a flag (I2)."""
    placer = placer or _Placer(ctx)
    rows = _all_rows(ctx)
    draws = _draws(ctx)
    out: Dict[str, object] = {"note": f"{NOTE}, item 14", "tables": {}, "by_final_answer": {}}
    for arm in SLIP_ARMS:
        for shape in _shapes(ctx):
            ar = _arm(rows, arm, shape)
            if not ar:
                continue
            key = f"{arm} {shape}"
            out["tables"][key] = {"local_steps": _table([placer.place(r, False) for r in ar], arm),           # type: ignore[index]
                                  "first_slip_steps": _table([placer.place(r, True) for r in ar], arm)}
            field = "correct_final" if scoring.is_chain_shape(shape) else "correct (= correct_final at 6x1)"
            out["by_final_answer"][key] = {                                                                # type: ignore[index]
                f"correct_final {flag}": {"tries": len(grp), "field": field,
                                          "local_steps": _table([placer.place(r, False) for r in grp], arm),
                                          "first_slip_steps": _table([placer.place(r, True) for r in grp], arm)}
                for flag, grp in ((True, [r for r in ar if _final_right(r, shape)]),
                                  (False, [r for r in ar if not _final_right(r, shape)]))}
    out["t_plus_g_minus"] = t_plus_g_minus(ctx, placer, draws)
    out["interpretations"] = ["I2", "I8"]
    return out


def t_plus_g_minus(ctx: Mapping[str, object], placer: _Placer, draws: int) -> Dict[str, object]:
    """Item 14's T+/G- sensitivity split (I2; C1 item 14): the driver's fairness family (fairness_input.records_from_tries ->
    fairness.fairness_indices over Haiku-, Opus- and Sonnet-medium, comparison Opus, local_steps view) with each step's class relabelled
    T+ / G- / other by its kind. Reported, never a flag."""
    tries = []
    for r in ctx["rows"]:                                                                     # type: ignore[union-attr]
        model = main_analysis.FAIRNESS_MODELS.get(str(r["setup"]))
        if model is not None:
            tries.append((str(r.get("preset")), str(r["base_id"]), model, _relabel(placer.place(r, False))))
    recs = fairness_input.records_from_tries(tries)
    unplaced = fairness_input.unplaceable_from_tries(tries)
    if not any(x.model == fairness.HAIKU for x in recs) or not any(x.model == fairness.OPUS for x in recs):
        tg: Dict[str, object] = {"computed": False, "reason": "no placeable Haiku or Opus try (fairness_indices needs both)"}
    else:
        tg = {"computed": True, "indices": fairness.fairness_indices(recs, comparison=fairness.OPUS, B=draws, unplaceable=unplaced)}
    tg.update(label="T+/G- sensitivity split: reported, never a flag", T_plus=list(T_PLUS), G_minus=list(G_MINUS))
    return tg


# ---------------------------------------------------------------- item 15

def item_15(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 15 (Addendum B; Amendment 1 item 6): the label the ladder set, ON (Opus-medium 40 of 40 at n = 6), NOT re-decided on main-run
    data; printed "near ceiling (Amendment 1)" beside tests 1 and 2, with the main run's Opus-medium pooled accuracy beside it for
    information only (main_analysis.main_run_markers: the D-87 plan's pooled panel, each base puzzle the mean of its two shapes)."""
    markers = main_analysis.main_run_markers(list(ctx["rows"]), int(ctx["n"]), ctx["items"], str(ctx["set_id"]))  # type: ignore[arg-type, call-overload]
    return {"note": f"{NOTE}, item 15", "label": NEAR_CEILING_LABEL, "on": True, "source": "the ladder: Opus-medium 40 of 40 at n = 6",
            "re_decided_on_main_run": False, "beside_tests": ["t1", "t2"],
            "opus_med_pooled_accuracy_main_run": markers["opus-med"]["pooled"],                              # type: ignore[index]
            "for_information_only": True}


# ---------------------------------------------------------------- item 16

def is_missing(r: Mapping[str, object]) -> bool:
    """Item 16 (C1; Edith r7): a planned try with no final record after the retry and resubmit rules, the converter's kind "missing" (for
    E3, an unfinished chain). Final records of kind empty, unexpected_stop or error are real results, not missing."""
    return r.get("kind") == "missing"


def _rate(count: int, designed: int) -> Dict[str, object]:
    return {"count": count, "rate": count / designed if designed else None, "wilson95": list(wilson(count, designed))}


def _setup_of_record(rec: Mapping[str, object]) -> Optional[str]:
    tag = str((rec.get("meta") or {}).get("setup"))                                         # type: ignore[union-attr]
    return ARM_OF_TAG.get(tag)


def exclude_missing_view(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 16's exclude-missing view (Edith B-1, r7), the driver's `missing_left_out`: the five-test family as_deployed with only the
    missing items (kind "missing") left out: a missing single answer drops that base puzzle from its test; missing Haiku samples drop from
    the vote, with k held to what is left (the locked vote_scores(designed=0) on the real calls); unfinished E3 chains drop. Final records
    of kind empty, unexpected_stop or error are kept. Same k, B, seeds, margin and Holm (five_tests._family)."""
    rows = [r for r in ctx["rows"] if not is_missing(r)]                                    # type: ignore[union-attr]
    k = ctx["k"]
    k_o = {sh: int(v) for sh, v in k["k_o"].items()}                                        # type: ignore[index, union-attr]
    k_s = int(k["k_s"])                                                                      # type: ignore[index, call-overload]
    diffs: Dict[str, List[float]] = {}
    for name, (chal, comp, shape, which) in five_tests.tests_for(int(ctx["n"])).items():   # type: ignore[call-overload]
        if which in ("O", "S"):
            kk = k_o[shape] if which == "O" else k_s
            if kk < 1:
                diffs[name] = []
                continue
            c = five_tests.vote_scores(rows, shape, kk, "as_deployed", designed=0)
        elif chal == "e3":
            c = five_tests.e3_arm_scores(rows, shape, "as_deployed")
        else:
            c = five_tests.single_scores(rows, chal, shape, "as_deployed")
        diffs[name] = scoring.paired_differences(c, five_tests.single_scores(rows, comp, shape, "as_deployed"))  # type: ignore[arg-type]
    res = five_tests._family(diffs, _B(ctx), TEST_SEED)
    res["label"] = "exclude-missing view (only missing items left out; otherwise as_deployed)"
    res["missing_left_out"] = sum(1 for r in ctx["rows"] if is_missing(r))                  # type: ignore[union-attr]
    return res


def _e3_rates(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 16 for E3 (C1): its rates are over the E3 calls actually made, labelled as such; an unfinished chain is its missing item,
    counted over the E3 chain rows."""
    draws = [r for r in ctx.get("records") or [] if (r.get("meta") or {}).get("setup") == main_rows.E3_TAG]  # type: ignore[union-attr]
    made = len(draws)
    cs = report_costs.calls(ctx)                                                         # type: ignore[arg-type]

    def usd(rs: Iterable[Mapping[str, object]]) -> str:
        return str(sum((cs[str(r["custom_id"])]["list"] for r in rs if str(r["custom_id"]) in cs), Decimal(0)))   # type: ignore[misc]
    cats: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for r in draws:
        if r.get("kind") == "refusal":
            cats[str(r.get("refusal_category"))].append(r)
    trunc = [r for r in draws if r.get("stop_reason") == "max_tokens"]
    chains = [r for r in ctx["rows"] if r["setup"] == "e3"]                                 # type: ignore[union-attr]
    return {"label": E3_RATES_LABEL, "calls_made": made,
            "kinds": dict(sorted(Counter(str(r.get("kind")) for r in draws).items())),
            "refusals_by_category": {c: dict(_rate(len(v), made), list_cost_usd=usd(v)) for c, v in sorted(cats.items())},
            "truncations": dict(_rate(len(trunc), made), list_cost_usd=usd(trunc)),
            "failures_by_kind": {kd: dict(_rate(len(v), made), list_cost_usd=usd(v)) for kd in FAILURE_KINDS
                                 if (v := [r for r in draws if r.get("kind") == kd])},
            "missing_chains": dict(_rate(sum(1 for r in chains if is_missing(r)), len(chains)), denominator="E3 chain rows")}


def item_16(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 16 (Addendum B; D-48 rows 20, 23, 25; Fix 7; spec sections 4 and 5). Per arm and shape: each refusal category and the
    truncations (stop_reason "max_tokens"): count / designed calls, the Wilson 95% interval (curve.wilson) and the list cost of those calls
    (item 9a: free B5 refusals at $0); the failures of kind empty, unexpected_stop and error, each its own row the same way; missing items
    (kind "missing" only, C1 / Edith r7) as count / designed calls. Designed calls are the arm's rows (the final records plus main_rows'
    missing rows of `planned`), checked against the runner's samples per puzzle for the eight main setups. E3: over the calls actually
    made (C1). The exclude-missing view runs only if a five-test item is missing ("no missing items in the five tests' arms" otherwise). "vote@k uses the samples
    available": for tests 1-3, the base puzzles with fewer than 40 Haiku-medium samples, and their ids. Per setup: real-time retry events
    by status (429, 5xx) and the Batch items errored, expired or canceled with their resubmits (I4); requests whose prompt tokens exceed
    100,000 (prices.LONG_PROMPT_THRESHOLD)."""
    rows = _all_rows(ctx)
    items: Mapping[str, Mapping[str, object]] = ctx["items"]                                  # type: ignore[assignment]
    per_shape = Counter(f"{it['width']}x{it['depth']}" for it in items.values())
    out: Dict[str, object] = {"note": f"{NOTE}, item 16", "rates": {}}
    for setup in sorted({str(r["setup"]) for r in rows if r["setup"] != "e3"}):
        for shape in _shapes(ctx):
            ar = _arm(rows, setup, shape)
            if not ar:
                continue
            designed = len(ar)
            if setup in MAIN_ARMS and designed != _designed(setup) * per_shape[shape]:
                raise ValueError(f"{setup} {shape}: {designed} rows, {_designed(setup) * per_shape[shape]} designed; build the rows with "
                                 f"main_rows.build(planned=...) so every missing try is a row")
            cats: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
            for r in ar:
                if r.get("kind") == "refusal":
                    cats[str(r.get("refusal_category"))].append(r)
            trunc = [r for r in ar if r.get("stop_reason") == "max_tokens"]
            miss = [r for r in ar if is_missing(r)]
            out["rates"][f"{setup} {shape}"] = {                                                                # type: ignore[index]
                "designed_calls": designed,
                "refusals_by_category": {c: dict(_rate(len(v), designed), list_cost_usd=_list_usd(ctx, v)) for c, v in sorted(cats.items())},
                "truncations": dict(_rate(len(trunc), designed), list_cost_usd=_list_usd(ctx, trunc)),
                "failures_by_kind": {kd: dict(_rate(len(v), designed), list_cost_usd=_list_usd(ctx, v)) for kd in FAILURE_KINDS
                                     if (v := [r for r in ar if r.get("kind") == kd])},
                "missing": _rate(len(miss), designed)}
    out["e3"] = _e3_rates(ctx)
    test_missing = [r for r in ctx["rows"] if is_missing(r)]                                 # type: ignore[union-attr]
    out["exclude_missing_view"] = exclude_missing_view(ctx) if test_missing else NO_MISSING
    pieces, chain = _shapes(ctx)
    few: Dict[str, object] = {}
    for test, shape in (("t1", pieces), ("t2", chain), ("t3", chain)):
        have: Dict[str, int] = Counter()
        for r in _arm(ctx["rows"], "haiku-med", shape):                                     # type: ignore[arg-type]
            have[str(r["base_id"])] += 0 if is_missing(r) else 1
        short = sorted(b for b, c in have.items() if c < five_tests.DESIGNED_HAIKU_SAMPLES)
        few[test] = {"shape": shape, "base_puzzles_with_fewer_than_40_samples": len(short), "ids": short}
    out["vote_uses_samples_available"] = few
    out["retries_and_batch_failures"] = _retries(ctx)
    long: Dict[str, int] = Counter()
    for rec in ctx.get("records") or []:                                                      # type: ignore[union-attr]
        if usage_from_raw(dict(rec.get("usage_raw") or {})).prompt_tokens > prices.LONG_PROMPT_THRESHOLD:
            long[str(_setup_of_record(rec))] += 1
    out["requests_over_100k_prompt_tokens"] = {"by_setup": dict(sorted(long.items())), "total": sum(long.values()), "expected": 0}
    out["interpretations"] = ["I3", "I4"]
    return out


def _retries(ctx: Mapping[str, object]) -> Dict[str, object]:
    """I4: from every call-log line, in file order."""
    lines = list(ctx.get("all_records") or [])                                                # type: ignore[call-overload]
    rt: Dict[str, Dict[str, int]] = defaultdict(Counter)
    batch: Dict[str, Dict[str, int]] = defaultdict(Counter)
    submitted: Dict[str, int] = Counter()
    failed_cids: Dict[str, str] = {}
    for i, rec in enumerate(lines):
        if rec.get("kind") == "batch_submitting":
            for cid in (rec.get("keys") or {}):
                submitted[str(cid)] += 1
            continue
        cid = str(rec.get("custom_id"))
        err = rec.get("error")
        if rec.get("kind") != "error" or not isinstance(err, dict):
            continue
        setup = str(_setup_of_record(rec))
        if err.get("type") in ("errored", "expired", "canceled"):
            batch[setup][str(err["type"])] += 1
            failed_cids[cid] = setup
            continue
        status = err.get("status")
        if isinstance(status, int) and (status == 429 or 500 <= status <= 599):
            group = "429" if status == 429 else "5xx"
            rt[setup][group] += 1
            if any(str(x.get("custom_id")) == cid and int(x.get("attempt") or 0) > int(rec.get("attempt") or 0)  # type: ignore[call-overload]
                   for x in lines[i + 1:] if x.get("kind") != "batch_submitting"):
                rt[setup][group + "_followed_by_a_retry"] += 1
    for cid, setup in failed_cids.items():
        batch[setup]["resubmits"] += max(0, submitted[cid] - 1)
    return {"realtime_retry_events_by_status": {s: dict(v) for s, v in sorted(rt.items())},
            "batch_errored_expired_canceled": {s: dict(v) for s, v in sorted(batch.items())}}


# ---------------------------------------------------------------- item 17

def item_17(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 17 (Addendum B; D-76): the flag fires for an arm and shape when the non-compliance share of ANSWERED tries is above 5.0%, the
    share being 1 - format_compliance of five_tests.format_report (official D-90 rule). Compared exactly in integers:
    (answered - format_ok) x 100 > 5 x answered. No answered try: not assessable (None)."""
    out: Dict[str, object] = {"note": f"{NOTE}, item 17", "flags": {}}
    for setup, shapes in five_tests.format_report(_all_rows(ctx)).items():
        for shape, v in shapes.items():
            answered, ok = int(v["answered"]), int(v["format_ok"])                              # type: ignore[call-overload]
            out["flags"][f"{setup} {shape}"] = {                                                # type: ignore[index]
                "answered": answered, "format_ok": ok, "non_compliance": (answered - ok) / answered if answered else None,
                "fires": ((answered - ok) * 100 > FORMAT_FLAG_PERCENT * answered) if answered else None}
    return out


# ---------------------------------------------------------------- item 21

def item_21(ctx: Mapping[str, object]) -> Dict[str, object]:
    """Item 21 (Addendum B; D-27 E3 detail, Edith B-2, C1): for each E3 step position the fixed-3 vote is the plurality of the FIRST 3
    logged draws in draw order (e3.step_state's order); an unreadable draw (e3.record_vote None) votes for nothing, and so does a draw that
    is missing (errored or lost: only the draws present vote, C1); no readable draw makes the step wrong; tied top answers earn 1/m (D-33,
    votes.vote_accuracy_at_k at k = the draws used, one subset); a step that lead-by-2 stopped after 2 agreeing draws is exact on those 2.
    The base's fixed-3 score is the product of its steps' credits (F7's rule), in points, beside E3 lead-by-2 (five_tests.e3_arm_scores,
    as_deployed). Descriptive."""
    chain = _shapes(ctx)[1]
    items: Mapping[str, Mapping[str, object]] = ctx["items"]                                  # type: ignore[assignment]
    recs = list(ctx.get("records") or [])                                                      # type: ignore[call-overload]
    setting = next((r["meta"].get("setting") for r in recs if (r.get("meta") or {}).get("setup") == main_rows.E3_TAG), None)
    man = {"family": "ledger", "set_id": str(ctx["set_id"]), "setting": setting}
    steps = e3mod.chain_steps([(man, list(items.values()))])
    draws = e3mod.draws_by_step(recs)
    by_base: Dict[str, List[e3mod.Step]] = defaultdict(list)
    for st in steps:
        by_base[f"{st.set_id}-{st.base_index:03d}"].append(st)
    per: Dict[str, object] = {}
    for base, chs in sorted(by_base.items()):
        p = 1.0
        detail = []
        for st in sorted(chs, key=lambda s: s.k):
            got = draws.get((st.item_id, st.k), {})
            first = [got[d] for d in sorted(got)][:3]
            answers = [e3mod.record_vote(r, st.lines) for r in first]
            c = float(votes.vote_accuracy_at_k(answers, st.truth, len(answers))["acc"]) if answers else 0.0
            stop2 = len(first) == 2 and bool(e3mod.decide(answers)["decided"])
            p *= c
            detail.append({"step": st.k, "draws_logged": len(got), "draws_used": len(first), "credit": c,
                           "fewer_than_3": len(first) < 3 and not stop2})
        per[base] = {"fixed3": 100.0 * p, "steps": detail}
    lead2 = five_tests.e3_arm_scores(list(ctx["rows"]), chain, "as_deployed")                # type: ignore[call-overload]
    vals = [float(v["fixed3"]) for v in per.values()]                                           # type: ignore[index]
    return {"note": f"{NOTE}, item 21", "label": "E3 fixed-3, simulated offline (descriptive)", "unit": "points", "per_base": per,
            "e3_lead_by_2_per_base": lead2, "mean_fixed3": _mean(vals), "mean_lead_by_2": _mean_scores(lead2)}


# ---------------------------------------------------------------- item 24

def item_24(ctx: dict) -> Dict[str, object]:
    """Item 24 (Addendum B; D-39 item 6, ruled): one row per arm and shape for every arm of the 80-base design (X5: the eight main setups
    and E3 at 1x6; the D-42 and real-time arms are out): base puzzles; single-try whole-answer accuracy (official, as_deployed): one-try
    arms x of n with Clopper-Pearson (item 12), multi-try arms and E3 the shared cluster bootstrap "accuracy:<arm>:<shape>" (X6); for
    Haiku arms the median over puzzles per shape and pooled (I5); the vote at the arm's own k where it has one (Haiku-medium: the tests'
    k_O, k_S, and k_S(6x1) of item 11; Haiku-low / thinking-off / max: item 10's own k), with the item 8 curve's bootstrap at that k;
    format compliance (format_report); refusals and truncations (item 16; E3 over its calls made); mean list cost per puzzle (9b) and CPC
    (9c). The chart per shape: every arm as a point (mean accuracy against mean list cost per puzzle, I6) with the table's bars, plus the
    Haiku-medium vote curve k = 1..40 as a line (items 8 and 9b). Nothing is fitted."""
    rows = _all_rows(ctx)
    draws = _draws(ctx)
    pieces, chain = _shapes(ctx)
    k = ctx["k"]
    k_o = {sh: int(v) for sh, v in k["k_o"].items()}                                         # type: ignore[index, union-attr]
    k_s = {chain: int(k["k_s"]), pieces: int(k_s_pieces(ctx)["k"])}                          # type: ignore[index, call-overload]
    fr = five_tests.format_report(rows)
    table: Dict[str, object] = {}
    chart: Dict[str, Dict[str, object]] = {sh: {"points": [], "haiku_med_vote_line": []} for sh in (pieces, chain)}
    haiku_scores: Dict[str, Dict[str, float]] = {}
    for arm in MAIN_ARMS:
        for shape in (pieces, chain):
            ar = _arm(rows, arm, shape)
            if not ar:
                continue
            scores = scoring.arm_scores([dict(r) for r in ar], "as_deployed", "official")
            multi = _designed(arm) > 1
            cost = report_costs.cost_block(ctx, arm, shape)
            d: Dict[str, object] = {"base_puzzles": len(scores), "accuracy_mean": _mean_scores(scores), "unit": "points",
                                    "format_compliance": fr.get(arm, {}).get(shape), "refusals_and_truncations": _kind_counts(ar),
                                    "cost_per_puzzle": cost, "cpc": report_costs.cpc_block(ctx, arm, shape)}
            if multi:
                haiku_scores[f"{arm} {shape}"] = scores
                band = _accuracy_band(scores, arm, shape, draws)
                d["accuracy_interval"] = band
                d["median_over_puzzles"] = statistics.median(scores.values()) if scores else None
                own: List[Tuple[str, int]] = []
                if arm == "haiku-med":
                    own = [("k_O", k_o[shape]), ("k_S", k_s[shape])]
                else:
                    for comp in ("opus-med", "sonnet-med"):
                        kv = _own_k(ctx, rows, arm, comp, shape).get("k")
                        if kv:
                            own.append((f"own k vs {comp}", int(kv)))                              # type: ignore[call-overload]
                curve = report_votes.curve_summary(ctx, arm, shape)
                if own:
                    d["vote_at_own_k"] = {}
                    for label, kk in own:
                        if kk < 1:
                            d["vote_at_own_k"][label] = {"k": kk, "vote": "not computed (k = 0)"}  # type: ignore[index]
                            continue
                        if kk > int(curve["k_max"]):                                              # type: ignore[call-overload]
                            d["vote_at_own_k"][label] = {"k": kk, "vote": f"not computed (k above the curve's k_max {curve['k_max']})"}  # type: ignore[index]
                            continue
                        pt = _points(curve["points"][kk - 1])                                      # type: ignore[index]
                        d["vote_at_own_k"][label] = {"k": kk, "mean": pt["mean"], "ci95": pt["ci95"],  # type: ignore[index]
                                                     "bootstrap_name": curve["bootstrap_name"],
                                                     "cost_per_puzzle": report_costs.cost_block(ctx, arm, shape, kk),
                                                     "cpc": report_costs.cpc_block(ctx, arm, shape, kk)}
                if arm == "haiku-med":
                    m = cost["mean"]
                    chart[shape]["haiku_med_vote_line"] = [                                        # type: ignore[index]
                        dict(_points(p), accuracy=_points(p)["mean"], cost_per_puzzle=None if m is None else p["k"] * m)   # type: ignore[operator]
                        for p in curve["points"]]                                                  # type: ignore[union-attr]
                bars = band["ci95"]
            else:
                cp = _one_try(ar)
                d["accuracy_cp95"] = cp
                bars = cp["cp95"]
            table[f"{arm} {shape}"] = d
            chart[shape]["points"].append({"arm": arm, "accuracy": d["accuracy_mean"], "accuracy_bars": bars,       # type: ignore[union-attr]
                                           "cost_per_puzzle": cost["mean"], "cost_bars": cost["mean_ci95"]})
    e3_scores = five_tests.e3_arm_scores(list(ctx["rows"]), chain, "as_deployed")             # type: ignore[call-overload]
    if e3_scores:
        cost = report_costs.cost_block(ctx, "e3", chain)
        band = _accuracy_band(e3_scores, "e3", chain, draws)
        d = {"base_puzzles": len(e3_scores), "accuracy_mean": _mean_scores(e3_scores), "unit": "points",
             "accuracy_rule": "product of per-step accuracies (F7; test 4's scorer)", "accuracy_interval": band,
             "cost_per_puzzle": cost, "cpc": report_costs.cpc_block(ctx, "e3", chain),
             "format_compliance": None, "refusals_and_truncations": _e3_rates(ctx)}
        table[f"e3 {chain}"] = d
        chart[chain]["points"].append({"arm": "e3", "accuracy": d["accuracy_mean"], "accuracy_bars": band["ci95"],  # type: ignore[union-attr]
                                       "cost_per_puzzle": cost["mean"], "cost_bars": cost["mean_ci95"]})
    pooled: Dict[str, object] = {}
    for arm in MAIN_ARMS:
        if _designed(arm) > 1 and f"{arm} {pieces}" in haiku_scores and f"{arm} {chain}" in haiku_scores:
            pts = list(haiku_scores[f"{arm} {pieces}"].values()) + list(haiku_scores[f"{arm} {chain}"].values())
            pooled[arm] = statistics.median(pts)
    return {"note": f"{NOTE}, item 24", "table": table, "haiku_median_pooled": pooled, "chart": chart,
            "fitted": "nothing is fitted", "out_of_design": "the D-42 arm (item 3) and the real-time arms (item 6) are out (X5)",
            "interpretations": ["I5", "I6", "I7"]}


# ---------------------------------------------------------------- all of them

def report(ctx: dict) -> Dict[str, object]:
    """Every item of this module, in the note's order, with the readings Edith ruled on."""
    placer = _Placer(ctx)
    return {"note": NOTE, "module": "harness/analysis/report_arms.py",
            "item_10": item_10(ctx), "item_11": item_11(ctx), "item_12": item_12(ctx), "item_13": item_13(ctx, placer),
            "item_14": item_14(ctx, placer), "item_15": item_15(ctx), "item_16": item_16(ctx), "item_17": item_17(ctx),
            "item_21": item_21(ctx), "item_24": item_24(ctx), "open_questions": dict(OPEN_QUESTIONS), "interpretations": INTERPRETATIONS}
