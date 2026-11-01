"""The kept group-C items of the D-93 inventory: C2, C3, C5, C7, C9 and C10, coded WORD FOR WORD from their definitions in
`research/reporting-inventory-main.md` at 93334b8 (section C, the "If kept, the definition" column; that commit is inside the D-93
public stamp, gist 2026-10-12T14:18:44Z; the user kept them before any data, D-94(5)), under Edith's ruling on group C
(`ops/reviews/2026-10-13-study1b-plan-and-groupC.md`, 958894b, Part 2: "Ruling: the kept group-C items").

    python3 -m harness.analysis.report_groupc --set <set dir> --run <run folder> --k <k.json> --extras sl,ho,hx --out <file>

Edith's ruling, applied here:
- every item carries the label "pre-specified descriptive (definition fixed and timestamped before the data, D-93 stamp; computed after
  the confirmatory results were opened, because it was not in the stamped driver)";
- the code follows the 93334b8 definitions word for word (each item's own text is copied into its output, "definition");
- wherever a definition leaves a choice, the choice is NOT settled silently: it is made as consistently as possible with the locked code
  and the reporting definitions (`research/reporting-definitions-main.md`, 93334b8: items 1-24 and Addenda A-C4) and recorded in
  `POST_HOC_CHOICES` (id, item, the choice made, why), which is written into the output under "post_hoc_choices";
- it runs once on the same run folder, after Edith's review of this code against 93334b8.

NOT coded here: C1, C4, C6, C8 and C12 (dropped), C11 (a sentence only) and C13 (E3 at 6x1, a later run).

Plumbing only, like the stamped driver: the context is the driver's own (`main_analysis.group_b_context`, built by the same code path
as `main_analysis.analyse_run`, the k.json table hash checked the same way), and every score, vote, cost and bootstrap comes from the
locked or group-B code (`scoring`, `five_tests`, `votes` via `report_votes.arm_curve`, `main_analysis`, `report_costs`, `report_arms`,
`report_votes`, `bootstrap`, `curve.cluster_bootstrap`). The only new arithmetic is the Pearson and Spearman correlations (C2, C9), which
no locked module has. No model or API call; standard library only.

    ctx = main_analysis.group_b_context(...)     # rows, other, missing, records, all_records, items, set_id, n, k, run_dir, B, draws
    report(ctx) -> {"note", "label", "item_C2", "item_C3", "item_C5", "item_C7", "item_C9", "item_C10", "post_hoc_choices"}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from . import bootstrap, five_tests, main_analysis, main_rows, report_arms, report_costs, report_votes, scoring
from .curve import cluster_bootstrap

SOURCE = "research/reporting-inventory-main.md at 93334b8 (inside the D-93 public stamp), section C"
RULING = "Edith's ruling on the kept group-C items: ops/reviews/2026-10-13-study1b-plan-and-groupC.md (958894b), Part 2"
NOTE = (f"{SOURCE}; {RULING}. Conventions from research/reporting-definitions-main.md (93334b8), items 1-24 and Addenda A-C4. "
        "C1, C4, C6, C8 and C12 are dropped, C11 is a sentence only and C13 is a later run: none is computed here.")
LABEL = ("pre-specified descriptive (definition fixed and timestamped before the data, D-93 stamp; computed after the confirmatory "
         "results were opened, because it was not in the stamped driver)")
SCORE = "official"                            # Addendum A: every statistic uses the official score (D-76 with D-90)
VIEW = "as_deployed"                          # POST_HOC_CHOICES G1
HAIKU = report_votes.HAIKU                    # "haiku-med"
OPUS = "opus-med"
DESIGNED = report_votes.DESIGNED              # 40 designed Haiku-medium samples per puzzle (X2)
CAP = report_votes.CAP                        # 40
REACH_DIGITS = report_votes.REACH_DIGITS      # C1 item 20: "reaches" after rounding both to 1e-9
RANK_DIGITS = 9                               # POST_HOC_CHOICES C9-4: values rounded to 1e-9 before ranking
EFFORT_PAIRS = (("opus-low", "opus-med"), ("haiku-low", "haiku-med"))   # C10, in the definition's order
UNDEFINED_R = "undefined (no variation)"

# The arms of the 80-base design (Addendum C, X5) that ran at BOTH shapes: E3 ran at 1x6 only (POST_HOC_CHOICES C2-1).
BOTH_SHAPE_ARMS = tuple(a for a in report_arms.MAIN_ARMS if a != "e3")

# ---------------------------------------------------------------- the definitions, verbatim (93334b8, section C, "If kept")

DEFINITIONS: Dict[str, str] = {
    "C2": ("Per arm, across the 80 base puzzles: the Pearson correlation of per-puzzle accuracy at 6×1 and at 1×6. For the Haiku arms "
           "that is each puzzle's share right of its tries; for one-try arms it is 0/1, which gives the phi coefficient. Shared cluster "
           "bootstrap 95%. Descriptive"),
    "C3": ("Per arm: the paired difference in whole-answer accuracy, 6×1 minus 1×6, over the 80 bases, with the shared cluster bootstrap "
           "95%. Descriptive. This is also the \"structure effect\""),
    "C5": ("For tests 1/2 only: (Haiku vote at k_O minus Opus) at 6×1, minus the same at 1×6, paired by base. Shared cluster bootstrap "
           "95%. Descriptive"),
    "C7": ("The crossover is the per-bin smallest k at which the vote reaches Opus's accuracy (item 20, step 3). In the text: \"the "
           "lowest single-try accuracy bin at which a vote within k_O reaches Opus\""),
    "C9": ("Per shape, across the 80 bases: the Spearman correlation between each puzzle's wrong-try agreement (item 4's per-puzzle share) "
           "and its vote gain (vote@k_O − single-try accuracy). Puzzles with fewer than 2 wrong tries are left out and counted. Shared "
           "cluster bootstrap 95%. No test"),
    "C10": ("Per shape: the paired difference in single-try whole-answer accuracy (Opus-low − Opus-medium; Haiku-low − Haiku-medium, each "
            "over its tries), with `bootstrap.paired_bca(margin=−10, B=10,000, seed=derive_seed(20261011, \"effort:<pair>:<shape>\"))`. "
            "Report d and the 95% interval. Cost difference from item 9b beside it. No Holm, no verdict"),
}
KEEP_AS: Dict[str, str] = {"C2": "Keep", "C3": "Keep", "C5": "Keep, narrow",
                           "C7": "Keep, through the vote lookup chart (B 20). Its bins are exactly \"each puzzle's Haiku single-try accuracy\"",
                           "C9": "Keep, descriptive", "C10": "Keep, exploratory"}

# ---------------------------------------------------------------- every choice a definition leaves open (Edith's ruling, point 3)

POST_HOC_CHOICES: Dict[str, Dict[str, str]] = {
    "G1": {"item": "all",
           "choice": "The official score (D-76 with D-90's repeat rule) in the as_deployed view: a missing, refused, truncated or "
                     "unparseable try is wrong and stays in its denominator.",
           "why": "No definition names a score or a view. Addendum A: every statistic uses the official score unless the item says "
                  "otherwise; as_deployed is the headline view, and the one items 1, 2, 9c and 20 and C1 item 10 (exploratory differences) "
                  "use."},
    "G2": {"item": "C2, C3, C5, C9",
           "choice": "\"Shared cluster bootstrap 95%\" is Addendum A's shared convention: curve.cluster_bootstrap, 2,000 draws, base seed "
                     "20261012, percentile 95% (order statistics), base puzzles drawn with replacement, a drawn base bringing both its "
                     "shapes, all its tries and all arms. Names (one per statistic, X1 style with main_rows arm names): "
                     "\"rho:<arm>\" (C2), \"shape_diff:<arm>\" (C3), \"shape_x_setup:haiku-med-vs-opus-med\" (C5), "
                     "\"repeat_vs_gain:haiku-med:<shape>\" (C9).",
           "why": "The definitions name the shared bootstrap but no statistic names; X1 fixes the style (arm names, shapes 6x1 / 1x6)."},
    "G3": {"item": "all",
           "choice": "\"The 80 base puzzles\" are the base puzzles the arm (or the paired arms) has rows for at the shapes used; with the "
                     "driver's rows (planned tries with no record are rows of kind \"missing\") that is every base of the set.",
           "why": "The driver's rows include every planned try, so this is the whole set; stated so the count is checked, not assumed."},
    "C2-1": {"item": "C2",
             "choice": "\"Per arm\" is every arm of the 80-base design (X5) that ran at both shapes: haiku-med, opus-med, opus-low, "
                       "sonnet-med, haiku-low, haiku-thinking-off, haiku-max, sonnet-low. E3 is out (it ran at 1x6 only); the D-42 and "
                       "real-time arms are out (X5).",
             "why": "X5 defines \"every arm\" for items 7 and 24; a correlation across shapes needs both shapes."},
    "C2-2": {"item": "C2",
             "choice": "Per-puzzle accuracy is scoring.arm_scores (official, as_deployed): a Haiku arm's share right over its tries (the "
                       "designed tries, a missing try wrong), a one-try arm's 0 or 100. In points; r is unchanged by the scale.",
             "why": "The same per-puzzle single-try accuracy items 12 and 24 report (I6)."},
    "C2-3": {"item": "C2",
             "choice": "r is the sample Pearson correlation, sum((x - mean x)(y - mean y)) / sqrt(sum((x - mean x)^2) sum((y - mean y)^2)), "
                       "sums by math.fsum; in a bootstrap draw a base drawn twice enters twice. If either shape's values are all equal "
                       "(for example Opus-medium right on every puzzle at one shape), r is \"undefined (no variation)\": the point "
                       "estimate says so, and a draw where it happens is dropped and counted; the interval is over the kept draws, with "
                       "the share dropped reported.",
             "why": "The definition gives no rule for a constant variable. Addendum C4 item 3 is the reporting definitions' rule for a "
                    "statistic with no value in a draw (0/0): dropped and counted, the interval over the kept draws, never withheld."},
    "C3-1": {"item": "C3",
             "choice": "The arms of C2-1. A Haiku arm's \"whole-answer accuracy\" is its single-try accuracy (scoring.arm_scores), not a "
                       "vote; d = the mean over bases of (6x1 score - 1x6 score), in points, and the interval is the shared cluster "
                       "bootstrap's percentile interval of that mean (not BCa).",
             "why": "The definition names no k, and \"whole-answer accuracy\" of an arm is the single-try value in items 12 and 24; it "
                    "names the shared cluster bootstrap and \"descriptive\", so not the confirmatory BCa machinery."},
    "C5-1": {"item": "C5",
             "choice": "k_O is each shape's own confirmatory k from k.json (test 1's k_O(6x1), test 2's k_O(1x6)); the per-base scores are "
                       "exactly tests 1 and 2's (main_analysis._test_scores: five_tests.vote_scores at that k against "
                       "five_tests.single_scores of Opus-medium); the value per base is (t1's difference) - (t2's difference), over the "
                       "bases both tests have. If either k_O is 0, C5 is not computed.",
             "why": "\"For tests 1/2 only\": the tests' own k and scores; k_O differs by shape (D-33, one k per shape)."},
    "C7-1": {"item": "C7",
             "choice": "Bins as item 20 step 1 (each puzzle's Haiku-medium single-try share over its 40 designed samples, a missing sample "
                       "wrong; 10-point bins, the last including 100). \"Per-bin\" is the whole bin: all its puzzles together (item 20's "
                       "thirds and its \"too few wrong tries\" group pooled). Item 20 step 3 is applied to the bin: the smallest k in "
                       "1..40 at which the bin's mean vote@k (item 8 curve, report_votes.arm_curve) reaches Opus-medium's mean accuracy "
                       "on the same puzzles, \"reaches\" being >= after rounding both to 1e-9 (C1 item 20); else \"none up to 40\".",
             "why": "The definition says \"per-bin\" (item 20 computes step 3 per cell); every other rule is item 20's and C1's."},
    "C7-2": {"item": "C7",
             "choice": "\"Within k_O\" is k <= that shape's confirmatory k_O (k.json). The crossover, per shape, is the lowest bin (by its "
                       "lower edge) whose smallest reaching k is within k_O; if no bin qualifies, \"no bin reaches Opus within k_O\". "
                       "Every bin's values are listed beside it, so a non-monotone pattern is visible.",
             "why": "k_O is per shape (D-33); the text sentence is per shape because the bins are."},
    "C7-3": {"item": "C7",
             "choice": "No interval: the smallest k and the crossover are point values.",
             "why": "X6: item 20's \"smallest k reaching Opus\" is a point value with no band; the C7 definition names no interval."},
    "C9-1": {"item": "C9",
             "choice": "The arm is Haiku-medium. A puzzle's wrong-try agreement is item 20 step 2's per-puzzle share (item 4's pairing): "
                       "unordered pairs of its WRONG real tries (kind \"missing\" left out) with an identical official vote key, a None "
                       "key never agreeing (D-72.1), by scoring.pairwise_agreement.",
             "why": "Item 4's share is Haiku-medium's; item 20 is the reporting definitions' per-puzzle use of it."},
    "C9-2": {"item": "C9",
             "choice": "Vote gain = vote@k_O - single-try accuracy, in points: vote@k_O by five_tests.vote_scores at that shape's "
                       "confirmatory k_O (k.json; official, as_deployed, tie \"random\"), single-try accuracy the share right over the 40 "
                       "designed samples (main_analysis._per_puzzle_share, as item 20 step 1). If k_O is 0 at a shape, C9 is not computed "
                       "there.",
             "why": "k_O is per shape (D-33); the single-try share is item 20's."},
    "C9-3": {"item": "C9",
             "choice": "Spearman's rho is the Pearson correlation (C2-3's formula) of the ranks, ties given their average (mid) rank; the "
                       "values are rounded to 1e-9 before ranking so equal rationals tie. Ranks are recomputed within each bootstrap draw, a "
                       "base drawn twice entering twice. If either variable is constant, rho is \"undefined (no variation)\", and such a "
                       "draw is dropped and counted (C2-3).",
             "why": "The definition names Spearman but no tie rule; mid-ranks are the standard form; the 1e-9 rounding is C1 item 20's "
                    "rule for comparing such values; the undefined rule is C4 item 3's."},
    "C9-4": {"item": "C9",
             "choice": "The bootstrap draws from the KEPT puzzles only (those with at least 2 wrong tries); the left-out puzzles are "
                       "counted and listed.",
             "why": "The left-out puzzles do not enter the statistic; X6 draws item 20's bands from the cell's own base puzzles in the "
                    "same way."},
    "C10-1": {"item": "C10",
              "choice": "<pair> is spelt \"opus-low-vs-opus-med\" and \"haiku-low-vs-haiku-med\", <shape> \"6x1\" / \"1x6\": seeds "
                        "derive_seed(20261011, \"effort:opus-low-vs-opus-med:6x1\") and so on. The call is report_arms._paired "
                        "(bootstrap.paired_bca, margin -10, B 10,000, seed derive_seed(20261011, name)), as item 10 uses it.",
              "why": "X1: main_rows arm names; C1 9h: the \"<a>-vs-<b>\" form of a pair."},
    "C10-2": {"item": "C10",
              "choice": "as_deployed only. Per-base scores are scoring.arm_scores (official): \"each over its tries\" is the share right "
                        "over the arm's tries (one try for Opus); the differences are scoring.paired_differences over the bases both arms "
                        "have. Only d and the 95% interval are reported (no p, no reading).",
              "why": "C1 item 10 pins as_deployed for exploratory differences against a comparator; the definition says \"Report d and "
                     "the 95% interval\" and \"No Holm, no verdict\"."},
    "C10-3": {"item": "C10",
              "choice": "The cost difference is the difference of the two item 9b headline means (report_costs.cost_block: mean list cost "
                        "per puzzle; a Haiku arm at one sample, i.e. its single try), arm minus comparator, in USD, a point value; each "
                        "arm's 9b block (mean, median and their bands) is shown beside it.",
              "why": "The definition says \"cost difference from item 9b\"; 9b's headline is the list-price mean; it gives no interval for "
                     "the difference."},
}

ITEM_CHOICES: Dict[str, List[str]] = {
    "C2": ["G1", "G2", "G3", "C2-1", "C2-2", "C2-3"], "C3": ["G1", "G2", "G3", "C3-1"], "C5": ["G1", "G2", "G3", "C5-1"],
    "C7": ["G1", "C7-1", "C7-2", "C7-3"], "C9": ["G1", "G2", "G3", "C9-1", "C9-2", "C9-3", "C9-4"],
    "C10": ["G1", "G3", "C10-1", "C10-2", "C10-3"]}


# ---------------------------------------------------------------- shared plumbing

def _n(ctx: Mapping[str, object]) -> int:
    return int(ctx["n"])                                                                      # type: ignore[call-overload]


def _shapes(ctx: Mapping[str, object]) -> Tuple[str, str]:
    return scoring.pieces_shape(_n(ctx)), scoring.chain_shape(_n(ctx))


def _all_rows(ctx: Mapping[str, object]) -> List[Mapping[str, object]]:
    return list(ctx["rows"]) + list(ctx.get("other") or [])                                  # type: ignore[call-overload]


def _arm_rows(ctx: Mapping[str, object], arm: str, shape: str) -> List[Dict[str, object]]:
    return [dict(r) for r in _all_rows(ctx) if r["setup"] == arm and r["shape"] == shape]


def _scores(ctx: Mapping[str, object], arm: str, shape: str) -> Dict[str, float]:
    """{base_id: points}: scoring.arm_scores in the official score, as_deployed (G1, C2-2)."""
    return scoring.arm_scores(_arm_rows(ctx, arm, shape), VIEW, SCORE)


def _k_o(ctx: Mapping[str, object]) -> Dict[str, int]:
    return {str(sh): int(v) for sh, v in ctx["k"]["k_o"].items()}                            # type: ignore[index, union-attr]


def _draws(ctx: Mapping[str, object]) -> int:
    return report_costs.cluster_draws(ctx)


def _head(item: str) -> Dict[str, object]:
    return {"label": LABEL, "keep_as": KEEP_AS[item], "definition": DEFINITIONS[item], "source": f"{SOURCE}, row {item}",
            "post_hoc_choices": list(ITEM_CHOICES[item])}


def _mean(xs: Sequence[float]) -> Optional[float]:
    return math.fsum(xs) / len(xs) if xs else None


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """C2-3: the sample Pearson correlation (math.fsum sums); None when fewer than 2 pairs or either variable has no variation (all its
    values equal, checked on the values themselves so float rounding of the mean cannot fake a variance)."""
    if len(xs) != len(ys):
        raise ValueError("pearson needs paired values")
    m = len(xs)
    if m < 2 or len(set(xs)) == 1 or len(set(ys)) == 1:
        return None
    mx, my = math.fsum(xs) / m, math.fsum(ys) / m
    sxy = math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = math.fsum((x - mx) ** 2 for x in xs)
    syy = math.fsum((y - my) ** 2 for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return None
    return max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))


def mid_ranks(xs: Sequence[float], digits: int = RANK_DIGITS) -> List[float]:
    """C9-3: 1-based ranks, tied values (after rounding to `digits`) sharing their average rank."""
    keyed = [round(float(x), digits) for x in xs]
    order = sorted(range(len(keyed)), key=lambda i: keyed[i])
    ranks = [0.0] * len(keyed)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and keyed[order[j + 1]] == keyed[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """C9-3: Pearson on mid-ranks; None when undefined."""
    return pearson(mid_ranks(xs), mid_ranks(ys))


def _correlation_band(bases: Sequence[str], x: Mapping[str, float], y: Mapping[str, float], fn: Callable, name: str,
                      draws: int) -> Dict[str, object]:
    """The shared cluster bootstrap (G2) of a correlation over the drawn bases; a draw where it is undefined is dropped and counted
    (C2-3); the interval is over the kept draws."""
    dropped = [0]

    def stat(sample: List[object]) -> Optional[float]:
        v = fn([x[b] for b in sample], [y[b] for b in sample])                                # type: ignore[index]
        if v is None:
            dropped[0] += 1
        return v
    lo, hi = cluster_bootstrap([sorted(bases)], stat, name, draws=draws) if bases else (None, None)
    return {"ci95": [lo, hi], "bootstrap_name": name, "draws": draws if bases else 0, "draws_dropped_undefined": dropped[0],
            "share_draws_dropped": (dropped[0] / draws) if bases else None}


# ---------------------------------------------------------------- C2: rho, how alike the two shapes behave

def item_C2(ctx: Mapping[str, object]) -> Dict[str, object]:
    """C2 (D-28): per arm (C2-1), over the base puzzles with a value at both shapes, the Pearson correlation of per-puzzle accuracy at
    6x1 and at 1x6 (C2-2: arm_scores, official, as_deployed; for one-try arms 0/100, the phi coefficient), with the shared cluster
    bootstrap "rho:<arm>" (G2); an undefined r (no variation) as C2-3."""
    pieces, chain = _shapes(ctx)
    out: Dict[str, object] = _head("C2")
    arms: Dict[str, object] = {}
    for arm in BOTH_SHAPE_ARMS:
        x, y = _scores(ctx, arm, pieces), _scores(ctx, arm, chain)
        if not x and not y:
            continue
        bases = sorted(set(x) & set(y))
        r = pearson([x[b] for b in bases], [y[b] for b in bases])
        d: Dict[str, object] = {"n_bases": len(bases), "r": UNDEFINED_R if r is None else r,
                                "statistic": "phi (Pearson on 0/1)" if report_arms._designed(arm) == 1 else "Pearson",
                                "bases_with_one_shape_only": sorted(set(x) ^ set(y))}
        if r is None:
            d["why_undefined"] = {pieces: len(set(x[b] for b in bases)) <= 1, chain: len(set(y[b] for b in bases)) <= 1}
        d.update(_correlation_band(bases, x, y, pearson, f"rho:{arm}", _draws(ctx)))
        arms[arm] = d
    out["arms"] = arms
    return out


# ---------------------------------------------------------------- C3: the like-for-like shape comparison (the structure effect)

def item_C3(ctx: Mapping[str, object]) -> Dict[str, object]:
    """C3 (D-23): per arm (C3-1), the paired difference in whole-answer (single-try) accuracy, 6x1 minus 1x6, over the bases with both:
    d = the mean of the per-base differences in points, with the shared cluster bootstrap "shape_diff:<arm>" (G2)."""
    pieces, chain = _shapes(ctx)
    out: Dict[str, object] = _head("C3")
    arms: Dict[str, object] = {}
    for arm in BOTH_SHAPE_ARMS:
        x, y = _scores(ctx, arm, pieces), _scores(ctx, arm, chain)
        if not x and not y:
            continue
        bases = sorted(set(x) & set(y))
        diff = {b: x[b] - y[b] for b in bases}
        name = f"shape_diff:{arm}"
        arms[arm] = {"n_bases": len(bases), "d": _mean(list(diff.values())), "unit": "points",
                     f"accuracy_{pieces}": _mean([x[b] for b in bases]), f"accuracy_{chain}": _mean([y[b] for b in bases]),
                     "ci95": report_votes._interval(bases, diff, name, _draws(ctx)) if bases else [None, None],
                     "bootstrap_name": name, "bases_with_one_shape_only": sorted(set(x) ^ set(y))}
    out["arms"] = arms
    return out


# ---------------------------------------------------------------- C5: the shape x setup interaction

def item_C5(ctx: Mapping[str, object]) -> Dict[str, object]:
    """C5 (spec section 8, narrow): per base, (Haiku vote at k_O minus Opus-medium) at 6x1 minus the same at 1x6, i.e. test 1's per-base
    difference minus test 2's (C5-1: each test's own k and scores, main_analysis._test_scores); the mean over the bases both tests have,
    in points, with the shared cluster bootstrap "shape_x_setup:haiku-med-vs-opus-med" (G2)."""
    pieces, chain = _shapes(ctx)
    k_o = _k_o(ctx)
    out: Dict[str, object] = _head("C5")
    out["k_O"] = dict(k_o)
    if min(k_o[pieces], k_o[chain]) < 1:
        out.update(computed=False, reason="a k_O is 0: test 1 or test 2 did not run (D-33)")
        return out
    ts = main_analysis._test_scores(list(ctx["rows"]), k_o, int(ctx["k"]["k_s"]), _n(ctx), VIEW, SCORE)   # type: ignore[index, call-overload]
    (c6, o6, _), (c1, o1, _) = ts["t1"], ts["t2"]
    bases = sorted(set(c6) & set(o6) & set(c1) & set(o1))
    per = {b: (float(c6[b]) - float(o6[b])) - (float(c1[b]) - float(o1[b])) for b in bases}
    name = "shape_x_setup:haiku-med-vs-opus-med"
    out.update(computed=True, n_bases=len(bases), unit="points", interaction=_mean(list(per.values())),
               t1_mean_difference=_mean([float(c6[b]) - float(o6[b]) for b in bases]),
               t2_mean_difference=_mean([float(c1[b]) - float(o1[b]) for b in bases]),
               ci95=report_votes._interval(bases, per, name, _draws(ctx)) if bases else [None, None], bootstrap_name=name,
               sign="(t1: 6x1) minus (t2: 1x6); each is Haiku vote at its k_O minus Opus-medium")
    return out


# ---------------------------------------------------------------- C7: results by difficulty and the crossover

def _bins(ctx: Mapping[str, object], shape: str) -> Tuple[Dict[int, List[str]], Dict[str, float], Dict[str, float], int]:
    """Item 20 step 1 (C7-1): ({bin index: item_ids}, Haiku-medium share per item, Opus-medium share per item, missing Haiku tries)."""
    rows = list(ctx["rows"])                                                                   # type: ignore[call-overload]
    puzzles = report_votes._puzzles(ctx, shape)
    hm = [r for r in rows if r["setup"] == HAIKU and r["shape"] == shape]
    share, missing = main_analysis._per_puzzle_share(hm, DESIGNED, puzzles)
    opus, _ = main_analysis._per_puzzle_share([r for r in rows if r["setup"] == OPUS and r["shape"] == shape], 1, puzzles)
    bins: Dict[int, List[str]] = defaultdict(list)
    for i in puzzles:
        right = round(share[i] * DESIGNED)
        if right / DESIGNED != share[i]:
            raise ValueError(f"{i}: share {share[i]} is not a count over {DESIGNED}")
        bins[min(9, (100 * right) // (10 * DESIGNED))].append(i)
    return bins, share, opus, missing


def item_C7(ctx: Dict[str, object]) -> Dict[str, object]:
    """C7 (D-21), through item 20's bins: per shape and per bin (C7-1: the whole bin), the bin's mean vote@k for k = 1..40 (the item 8
    curve) and the smallest k at which it reaches Opus-medium's mean on the same puzzles (item 20 step 3, C1's 1e-9 rule); the crossover
    is the lowest bin whose smallest k is within that shape's k_O (C7-2). Point values, no band (C7-3)."""
    out: Dict[str, object] = _head("C7")
    k_o = _k_o(ctx)
    kmax = min(CAP, DESIGNED)
    shapes: Dict[str, object] = {}
    for shape in _shapes(ctx):
        bins, share, opus, missing = _bins(ctx, shape)
        curve = report_votes.arm_curve(ctx, HAIKU, shape)
        k_sh = k_o[shape]
        table: Dict[str, object] = {}
        crossover: Optional[str] = None
        for b in range(10):
            ids = bins.get(b, [])
            if not ids:
                continue
            bases = [report_votes._base_of(ctx, i) for i in ids]
            absent = [x for x in bases if x not in curve]
            if absent:
                raise ValueError(f"{absent[0]}: no Haiku-medium row at {shape} (build the rows with the planned requests)")
            m = len(ids)
            opus_mean = math.fsum(opus[i] for i in ids) / m
            means = [math.fsum(float(curve[x][k - 1]["acc"]) for x in bases) / m for k in range(1, kmax + 1)]   # type: ignore[arg-type]
            reach = next((k for k, v in enumerate(means, 1) if round(v, REACH_DIGITS) >= round(opus_mean, REACH_DIGITS)), None)
            within = reach is not None and k_sh >= 1 and reach <= k_sh
            if within and crossover is None:
                crossover = report_votes.BIN_LABELS[b]
            table[report_votes.BIN_LABELS[b]] = {
                "bin_lower_edge": 10 * b, "puzzles": m, "base_ids": sorted(bases), "unit": "share right (0-1)",
                "haiku_med_single_try_mean": math.fsum(share[i] for i in ids) / m, "opus_med_mean": opus_mean,
                "mean_vote_at_k": [{"k": k, "mean": v} for k, v in enumerate(means, 1)],
                "mean_vote_at_k_O": means[k_sh - 1] if 1 <= k_sh <= kmax else None,
                "smallest_k_reaching_opus": reach if reach is not None else f"none up to {kmax}",
                "reaches_within_k_O": within}
        shapes[shape] = {"k_O": k_sh, "missing_haiku_tries": missing, "bins": table,
                         "crossover_bin": crossover if crossover is not None else "no bin reaches Opus within k_O",
                         "sentence": ("the lowest single-try accuracy bin at which a vote within k_O reaches Opus: "
                                      + (crossover if crossover is not None else "none") + f" (k_O = {k_sh})")}
    out["shapes"] = shapes
    return out


# ---------------------------------------------------------------- C9: more repeated wrong answers, smaller gain from voting

def item_C9(ctx: Dict[str, object]) -> Dict[str, object]:
    """C9 (spec section 7): per shape, over the base puzzles with at least 2 wrong Haiku-medium tries, Spearman's rho between the
    puzzle's wrong-try agreement (C9-1) and its vote gain, vote@k_O minus single-try accuracy in points (C9-2); the left-out puzzles
    counted; the shared cluster bootstrap "repeat_vs_gain:haiku-med:<shape>" over the kept puzzles (C9-4). No test."""
    out: Dict[str, object] = _head("C9")
    k_o = _k_o(ctx)
    rows = list(ctx["rows"])                                                                   # type: ignore[call-overload]
    shapes: Dict[str, object] = {}
    for shape in _shapes(ctx):
        k = k_o[shape]
        if k < 1:
            shapes[shape] = {"k_O": k, "computed": False, "reason": "k_O is 0: the vote at k_O did not run (D-33)"}
            continue
        puzzles = report_votes._puzzles(ctx, shape)
        hm = [r for r in rows if r["setup"] == HAIKU and r["shape"] == shape]
        share, missing = main_analysis._per_puzzle_share(hm, DESIGNED, puzzles)
        wrong: Dict[str, List[object]] = defaultdict(list)
        for r in hm:                                                     # item 20 step 2's pairing (item 4; main_analysis.repeat_share)
            if r.get("kind") == "missing" or scoring.row_correct(r, SCORE):
                continue                                                 # real calls only (Edith N-4)
            key = scoring.vote_key(r, SCORE)
            wrong[str(r["item_id"])].append(key if key is not None else object())   # a None key never agrees (D-72.1)
        vote = five_tests.vote_scores(rows, shape, k, VIEW, score=SCORE)
        agreement: Dict[str, float] = {}
        gain: Dict[str, float] = {}
        left_out: List[str] = []
        per: Dict[str, object] = {}
        for i in puzzles:
            b = report_votes._base_of(ctx, i)
            agr = scoring.pairwise_agreement(wrong.get(i, []))
            single = 100.0 * share[i]
            if not agr["pairs"]:
                left_out.append(b)
                per[b] = {"wrong_tries": len(wrong.get(i, [])), "left_out": "fewer than 2 wrong tries"}
                continue
            if b not in vote:
                raise ValueError(f"{b}: no Haiku-medium vote at {shape}")
            agreement[b] = float(agr["share"])
            gain[b] = float(vote[b]) - single                                                   # type: ignore[arg-type]
            per[b] = {"wrong_tries": len(wrong[i]), "agreement_share": agreement[b], "vote_at_k_O": float(vote[b]),   # type: ignore[arg-type]
                      "single_try": single, "vote_gain": gain[b]}
        kept = sorted(agreement)
        rho = spearman([agreement[b] for b in kept], [gain[b] for b in kept])
        d: Dict[str, object] = {"k_O": k, "computed": True, "n_kept": len(kept), "n_left_out": len(left_out), "left_out": sorted(left_out),
                                "missing_haiku_tries": missing, "rho": UNDEFINED_R if rho is None else rho,
                                "unit": "vote gain in points; agreement a share", "per_puzzle": per}
        d.update(_correlation_band(kept, agreement, gain, spearman, f"repeat_vs_gain:{HAIKU}:{shape}", _draws(ctx)))
        shapes[shape] = d
    out["shapes"] = shapes
    return out


# ---------------------------------------------------------------- C10: effort contrasts

def _exact_mean_cost(ctx: Dict[str, object], arm: str, shape: str) -> Optional[Fraction]:
    """Item 9b's headline mean, exactly: the mean over base puzzles of report_costs.base_costs (the one 9b copy; a Haiku arm per sample),
    over the bases with a known cost, as report_costs.cost_block averages them (C10-3)."""
    costs, _ = report_costs.base_costs(ctx, arm, shape)
    known = [v for v in costs.values() if v is not None]
    return sum(known, Fraction(0)) / len(known) if known else None


def item_C10(ctx: Dict[str, object]) -> Dict[str, object]:
    """C10 (D-30's notes; exploratory): per shape, the paired difference in single-try whole-answer accuracy, Opus-low - Opus-medium and
    Haiku-low - Haiku-medium (C10-2: arm_scores, official, as_deployed), by bootstrap.paired_bca(margin -10, B 10,000,
    seed derive_seed(20261011, "effort:<pair>:<shape>")) (C10-1: report_arms._paired); d and the 95% interval; the item 9b cost
    difference beside it (C10-3). No Holm, no verdict."""
    out: Dict[str, object] = _head("C10")
    out["exploratory"] = "exploratory: no Holm, no verdict"
    B = report_costs.family_draws(ctx)
    pairs: Dict[str, object] = {}
    for arm, comp in EFFORT_PAIRS:
        pair = f"{arm}-vs-{comp}"
        for shape in _shapes(ctx):
            a, c = _scores(ctx, arm, shape), _scores(ctx, comp, shape)
            key = f"{pair}:{shape}"
            if not a or not c:
                pairs[key] = {"computed": False, "reason": f"no rows for {arm if not a else comp} at {shape}"}
                continue
            diffs = scoring.paired_differences(a, c)
            res = report_arms._paired(diffs, B, f"effort:{pair}:{shape}")
            ca, cc = report_costs.cost_block(ctx, arm, shape), report_costs.cost_block(ctx, comp, shape)
            ma, mc = _exact_mean_cost(ctx, arm, shape), _exact_mean_cost(ctx, comp, shape)
            pairs[key] = {"computed": True, "n": res["n"], "d": res["d"], "ci95": res["ci95"], "unit": "points",
                          "seed_name": res.get("seed_name"), "B": B, "margin": bootstrap.MARGIN,
                          "accuracy_means": {arm: _mean(list(a.values())), comp: _mean(list(c.values()))},
                          "cost_difference_usd": float(ma - mc) if ma is not None and mc is not None else None,
                          "cost_difference_note": f"item 9b mean list cost per puzzle, {arm} minus {comp} (a Haiku arm at one sample)",
                          "cost_9b": {arm: ca, comp: cc}}
    out["pairs"] = pairs
    return out


# ---------------------------------------------------------------- the whole report, and the CLI

def report(ctx: Dict[str, object]) -> Dict[str, object]:
    """Every kept group-C item, with the post-hoc choices (Edith's ruling, point 3)."""
    return {"note": NOTE, "label": LABEL, "module": "harness/analysis/report_groupc.py",
            "item_C2": item_C2(ctx), "item_C3": item_C3(ctx), "item_C5": item_C5(ctx), "item_C7": item_C7(ctx),
            "item_C9": item_C9(ctx), "item_C10": item_C10(ctx),
            "post_hoc_choices": {cid: dict(v, id=cid) for cid, v in POST_HOC_CHOICES.items()}}


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_context(set_dir: Path, run_dir: Path, k_path: Path, extras: Sequence[str] = (), n: int = main_analysis.STEPS_AT_CHOSEN_N,
                  d42: bool = True, B: Optional[int] = None, draws: Optional[int] = None) -> Dict[str, object]:
    """The driver's ctx, by main_analysis.analyse_run's own code path with a run folder: the planned requests rebuilt
    (main_rows.planned_requests with the run's extras) and checked against the run's manifest, the rows built with them (a planned try
    with no record is a row of kind "missing"), k read from k.json (k_step.load_k), which must come from this run's compact_table.csv
    (its SHA-256) and equal k recomputed now from that table (k_step.k_from_table); then main_analysis.group_b_context. `B` and `draws`
    are for tests only (None: 10,000 and 2,000)."""
    from .k_step import k_from_table, load_k
    logs = [Path(run_dir) / "calls.jsonl"]
    man, items0 = main_rows.load_set(set_dir)
    planned = main_rows.planned_requests(man, list(items0.values()), extras, d42)
    main_rows.check_planned(run_dir, planned)
    built = main_rows.build(set_dir, logs, planned=planned)
    _, items = main_rows.load_set(set_dir)
    k = load_k(k_path)
    have = _sha256(Path(run_dir) / "compact_table.csv")
    if k.get("compact_table_sha256") != have:
        raise ValueError(f"{k_path} was computed from another compact_table.csv than {run_dir}'s")
    again = json.loads(json.dumps(k_from_table(Path(run_dir) / "compact_table.csv", n=n), default=str))
    if (again["k_o"], again["k_s"], again["k_from_rows"]) != (k["k_o"], k["k_s"], k["k_from_rows"]):
        raise ValueError(f"{k_path} differs from k recomputed now from {run_dir}/compact_table.csv (k_step)")
    recs = main_rows.final_records(logs)
    return main_analysis.group_b_context(built, recs, list(main_rows.all_records(logs)), items, str(man["set_id"]), n, k, run_dir, B,
                                         draws)


def run(set_dir: Path, run_dir: Path, k_path: Path, extras: Sequence[str] = (), B: Optional[int] = None,
        draws: Optional[int] = None) -> Dict[str, object]:
    """build_context, then report, with the inputs' hashes."""
    ctx = build_context(set_dir, run_dir, k_path, extras, B=B, draws=draws)
    res = report(ctx)
    res["inputs"] = {"set": str(set_dir), "run": str(run_dir), "k": str(k_path), "extras": list(extras),
                     "calls_jsonl_sha256": _sha256(Path(run_dir) / "calls.jsonl"),
                     "compact_table_sha256": _sha256(Path(run_dir) / "compact_table.csv"), "k_json_sha256": _sha256(k_path)}
    return res


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True, help="the run folder holding calls.jsonl")
    ap.add_argument("--k", type=Path, required=True, help="k.json from harness.analysis.k_step, committed before the driver ran")
    ap.add_argument("--extras", default="", help="the extras the run was cleared with (main-l14n6-1: sl,ho,hx)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: this runs once and never overwrites its output")
    res = run(a.set, a.run, a.k, tuple(x for x in a.extras.split(",") if x))
    text = json.dumps(res, indent=1, sort_keys=True, default=str) + "\n"
    with open(a.out, "x") as f:                                                               # refuse a file that appeared meanwhile
        f.write(text)
    print(f"wrote {a.out} (SHA-256 {hashlib.sha256(text.encode('utf-8')).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
