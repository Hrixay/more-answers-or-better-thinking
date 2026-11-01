"""The main run's analysis, end to end, by the LOCKED code only (prereg-lock-3 with Amendment 1). Plumbing: it calls the locked functions
in the pre-registered order and writes one JSON file; it makes no analysis choice of its own.

    python3 -m harness.analysis.main_analysis --set data/tasks/main-ledger-l14n6-v1 --run <run folder> --out analysis.json

Sealing (Edith's clearance addendum, 2026-10-12): this is run ONCE, on the finished log, after this file and `main_rows.py` are CLEAN and
their commit is publicly timestamped; its output is committed with the log hashes.

What it computes, in order (each from the module named):
1. rows: `main_rows.build` (the call log and the frozen set -> scored rows; E3 rows from `harness.pareto.e3.e3_rows`).
2. k: READ from k.json (`k_step`: five_tests.k_from_rows on the confirmatory arms' costs only, fixed and committed before this
   runs; D-33, D-70, D-93); the driver refuses to run without it and checks it was made from this run's compact_table.csv.
3. the confirmatory family: `five_tests.analyse_all_views` under the official score (D-76 with D-90): the five tests, all three views,
   Holm, the three-way reading and the headline rule (D-68 F3).
4. the secondary readings: `five_tests.analyse_secondary` (final answer, copy slips forgiven, and D-90's original repeat rule), with
   `rates` and `format_report`; `five_tests.tie_report` (ties as wrong, and how often a tie decided).
5. D-90's appendix: `five_tests.analyse_all_views` under score "original" (the full original-rule tables).
6. the fairness check (D-67(2)): `scoring.local_steps` on every try of Haiku-medium, Opus-medium and Sonnet-medium (both shapes), counted
   by `fairness_input.records_from_tries` / `unplaceable_from_tries`, then `fairness.fairness_indices` (comparison Opus, pooling with
   Sonnet as the locked rule decides); the first-slip sensitivity view the same way from `scoring.first_slip_steps`.
7. Haiku's wrong-answer repeat share (D-67(2)): `scoring.pooled_repeat_share` over each base puzzle's WRONG Haiku-medium tries per shape,
   the signature being the official vote key (`scoring.vote_key`: the whole trace at 1xN, the answer at Nx1), a None key never agreeing
   (D-72.1's rule for wrong pairs); and over first-slip signatures (`first_slip_steps`).
8. per-arm counts for every arm (the five-test arms and the others): rows, kinds, stop reasons, refusal categories, truncations, cost.
9. to 14. the items the lock does not fix in code, under `reporting`, one function each, exactly as Karen's dated note
`research/reporting-definitions-main.md` (0d103c0, Edith CLEAN) defines them: the error-rate ratios, the 5-point view, the D-42
robustness table, flag R, the low-information flag and the real-time report; and the D-87 curve's main-run markers (`main_run_markers`,
the plan's own definitions).
15. group B, the rest of the note (items 7-24 with Addenda A, B and C, 93334b8, Edith CLEAN), under `reporting["group_b"]`, keyed
"item_<n>" exactly as the note numbers them: items 7, 8a, 8b, 18 and 20 from `report_votes.report`; 9a-9h, 19, 22 and 23 from
`report_costs.report`; 10-17, 21 and 24 from `report_arms.report`; plus `open_questions` (per module: what the note still leaves open,
left uncomputed) and `interpretations` (the readings Edith ruled on, r7). The three modules get one context dict (`group_b_context`):
rows, other, missing, records, all_records, items, set_id, n, k (k.json), run_dir, and, for tests only, B and draws (the driver passes its
`B` and `fairness_draws`; both None in the sealed run, so every draw count is the note's). Nothing beyond the driver's own inputs is read.
`missing_left_out` is item 16's exclude-missing view (`report_arms.exclude_missing_view`; Edith B-1 and r7: they are one and the same):
only kind "missing" left out, as_deployed, missing Haiku samples dropped from the vote with k held to what is left; "no missing items in
the five tests' arms" when none is (missing items of the other arms are in item 16's rates).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import bootstrap, fairness, fairness_input, five_tests, main_rows, scoring
from .curve import _puzzle

STEPS_AT_CHOSEN_N = 6                         # Amendment 1: N = 6
FAIRNESS_MODELS = {"haiku-med": fairness.HAIKU, "opus-med": fairness.OPUS, "sonnet-med": fairness.SONNET}


def k_values(k: Mapping[str, object], n: int) -> Dict[str, object]:
    """The integers five_tests needs (k_o per shape, k_s at the chain shape) from `k_from_rows`'s output, as computed there."""
    pieces, chain = scoring.pieces_shape(n), scoring.chain_shape(n)
    k_o = {shape: int(k["opus"][shape]["k"]) for shape in (pieces, chain)}                       # type: ignore[index]
    k_s = int(k["sonnet"][chain]["k"])                                                           # type: ignore[index]
    return {"k_o": k_o, "k_s": k_s}


def arm_counts(rows: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """Per (setup, shape): rows, kinds, stop reasons, refusal categories, truncations and the summed cost (as logged). No scores."""
    from decimal import Decimal
    out: Dict[str, Dict[str, object]] = {}
    for r in rows:
        key = f"{r['setup']} {r['shape']}"
        d = out.setdefault(key, {"rows": 0, "kinds": Counter(), "stop_reasons": Counter(), "refusal_categories": Counter(),
                                 "truncated": 0, "cost_usd": Decimal(0)})
        d["rows"] += 1                                                                            # type: ignore[operator]
        d["kinds"][str(r.get("kind"))] += 1                                                       # type: ignore[index]
        d["stop_reasons"][str(r.get("stop_reason"))] += 1                                         # type: ignore[index]
        if r.get("refusal_category"):
            d["refusal_categories"][str(r["refusal_category"])] += 1                              # type: ignore[index]
        d["truncated"] += int(r.get("kind") == "truncated" or r.get("stop_reason") == "max_tokens")  # type: ignore[operator]
        d["missing"] = int(d.get("missing", 0)) + int(r.get("kind") == "missing")                    # type: ignore[call-overload]
        if r.get("cost_usd") not in (None, ""):
            d["cost_usd"] += Decimal(str(r["cost_usd"]))                                          # type: ignore[operator]
    for v in out.values():
        v["missing_rate"] = int(v.get("missing", 0)) / int(v["rows"]) if v["rows"] else None     # type: ignore[call-overload]
    return {k: {kk: (dict(vv) if isinstance(vv, Counter) else str(vv) if kk == "cost_usd" else vv) for kk, vv in v.items()}
            for k, v in sorted(out.items())}


def _tries_for_fairness(rows: Sequence[Mapping[str, object]], items: Mapping[str, Mapping[str, object]], texts: Mapping[str, str],
                        first_slip: bool) -> List[tuple]:
    """(preset, base_id, model, placed) for every try of the fairness models, `placed` from local_steps (or first_slip_steps)."""
    cache: Dict[str, object] = {}
    out = []
    for r in rows:
        model = FAIRNESS_MODELS.get(str(r["setup"]))
        if model is None:
            continue
        if r.get("kind") != "answered":
            placed = {"unplaceable": str(r.get("kind")), "status": str(r.get("kind")), "steps": []}
        else:
            iid = str(r["item_id"])
            if iid not in cache:
                cache[iid] = _puzzle(items[iid])
            fn = scoring.first_slip_steps if first_slip else scoring.local_steps
            placed = fn(texts[str(r["custom_id"])], cache[iid])                                   # type: ignore[arg-type]
        out.append((str(r["preset"]), str(r["base_id"]), model, placed))
    return out


def repeat_share(rows: Sequence[Mapping[str, object]], n: int) -> Dict[str, object]:
    """Item 7 (pinned in the reporting note, section 4): unordered pairs of WRONG Haiku-medium tries within one base and shape with an
    identical official vote key (a None key never agrees, D-72.1), by `scoring.pooled_repeat_share`, per shape and summed over both."""
    out: Dict[str, object] = {}
    for shape in (scoring.pieces_shape(n), scoring.chain_shape(n)):
        wrong: Dict[str, List[object]] = defaultdict(list)
        for r in rows:
            if r.get("kind") == "missing":
                continue                                                    # real calls only (Edith N-4): a missing try is not a wrong answer
            if r["setup"] == "haiku-med" and r["shape"] == shape and not scoring.row_correct(r, "official"):
                key = scoring.vote_key(r, "official")
                wrong[str(r["base_id"])].append(key if key is not None else object())             # a None key never agrees (D-72.1)
        out[shape] = scoring.pooled_repeat_share(wrong)
    shapes = [scoring.pieces_shape(n), scoring.chain_shape(n)]
    pairs = sum(int(out[sh]["pairs"]) for sh in shapes)                                           # type: ignore[index]
    agree = sum(int(out[sh]["agree"]) for sh in shapes)                                           # type: ignore[index]
    out["both_shapes"] = {"pairs": pairs, "agree": agree, "share": (agree / pairs) if pairs else None}
    return out


# ---------------------------------------------------------------- items 9-14: research/reporting-definitions-main.md
# Karen's note (0d103c0; Edith CLEAN, ops/reviews/2026-10-12-reporting-gaps.md r2), implemented exactly: one function per item, each
# citing its section. Statistics at N = 6, the official score (D-76 with D-90), from the same per-base scores the tests use.

def _ends(values: List[float], lo: float, hi: float) -> List[Optional[float]]:
    """Order-statistic percentile ends over the kept values (bootstrap.py's rule): v[floor(lo*k)], v[ceil(hi*k)-1]; plain floats, +inf
    sorts last; no interpolation (Edith, note (c))."""
    v = sorted(float(x) for x in values)
    k = len(v)
    if not k:
        return [None, None]
    return [v[int(math.floor(lo * k))], v[int(math.ceil(hi * k)) - 1]]


def _show(x: Optional[float]) -> object:
    return "unbounded" if x is not None and math.isinf(x) else x


def _test_scores(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, n: int, view: str = "as_deployed",
                 score: str = "official") -> Dict[str, tuple]:
    """{test: (challenger per-base scores, comparator per-base scores, comparator setup)} for every test that ran (k >= 1), built exactly
    as five_tests.test_differences builds them, with challengers, comparators and k read from five_tests.tests_for and the k used."""
    out: Dict[str, tuple] = {}
    for name, (chal, comp, shape, which) in five_tests.tests_for(n).items():
        if which in ("O", "S"):
            k = int(k_o[shape]) if which == "O" else int(k_s)
            if k < 1:
                continue
            c = five_tests.vote_scores(rows, shape, k, view, score=score)
        elif chal == "e3":
            c = five_tests.e3_arm_scores(rows, shape, view)
        else:
            c = five_tests.single_scores(rows, chal, shape, view, score)
        out[name] = (c, five_tests.single_scores(rows, comp, shape, view, score), comp)
    return out


ERROR_RATIO_B = 10_000
ERROR_RATIO_SEED = 20261011


def error_ratios(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, n: int, B: int = ERROR_RATIO_B) -> Dict[str, object]:
    """Note section 1. Per test that ran, as_deployed: E_ch = sum_b (100 - c_b)/100 and E_cmp = sum_b (100 - o_b)/100 over the test's paired
    bases; R = E_ch / E_cmp; 95% percentile interval from B paired replicates (rng = Random(derive_seed(20261011, f"{test}:error_ratio")),
    rng.choices over the sorted base list): E_cmp* = 0 < E_ch* gives R* = +inf (kept), 0/0 is dropped and counted. If E_cmp = 0 in the data,
    R is not defined: report the comparator's 0 errors in n, the upper end of curve.wilson(0, n), and e_ch with its interval."""
    out: Dict[str, object] = {}
    for name, (c, comp, comp_setup) in _test_scores(rows, k_o, k_s, n).items():
        bases = sorted(set(c) & set(comp))
        ech = {b: (100.0 - float(c[b])) / 100.0 for b in bases}
        ecm = {b: (100.0 - float(comp[b])) / 100.0 for b in bases}
        out[name] = dict(ratio_from_errors(ech, ecm, name, B), comparator=comp_setup)
    return out


def ratio_from_errors(ech: Mapping[str, float], ecm: Mapping[str, float], name: str, B: int = ERROR_RATIO_B) -> Dict[str, object]:
    """Note section 1's arithmetic for one test, from the per-base errors (challenger, comparator; each (100 - score)/100). The
    zero-error comparator bound is the exact two-sided 95% Clopper-Pearson upper end for 0 of n, 1 - 0.025^(1/n) (Addendum A0)."""
    bases = sorted(set(ech) & set(ecm))
    m = len(bases)
    E_ch, E_cmp = math.fsum(ech[b] for b in bases), math.fsum(ecm[b] for b in bases)
    row: Dict[str, object] = {"n": m, "E_ch": E_ch, "E_cmp": E_cmp,
                              "e_ch_points": 100.0 * E_ch / m if m else None, "e_cmp_points": 100.0 * E_cmp / m if m else None}
    if True:
        rng = random.Random(bootstrap.derive_seed(ERROR_RATIO_SEED, f"{name}:error_ratio"))
        ratios: List[float] = []
        e_ch_star: List[float] = []
        dropped = zero_cmp = 0
        for _ in range(B if m else 0):
            draw = rng.choices(bases, k=m)
            a = math.fsum(ech[x] for x in draw)
            o = math.fsum(ecm[x] for x in draw)
            e_ch_star.append(100.0 * a / m)
            if o == 0:
                zero_cmp += 1
                if a == 0:
                    dropped += 1
                    continue
                ratios.append(float("inf"))
            else:
                ratios.append(a / o)
        row["share_replicates_E_cmp_zero"] = zero_cmp / B if m else None
        row["replicates_dropped_0_over_0"] = dropped
        if m and E_cmp > 0:
            lo, hi = _ends(ratios, 0.025, 0.975)
            row.update(R=E_ch / E_cmp, defined=True, ci95=[_show(lo), _show(hi)])
        else:
            lo, hi = _ends(e_ch_star, 0.025, 0.975)
            row.update(R=None, defined=False, comparator_note=f"comparator: 0 errors in {m}" if m else "no paired bases",
                       comparator_error_rate_upper95=(1.0 - 0.025 ** (1.0 / m) if m else None),   # A0: two-sided 95% Clopper-Pearson, 0 of m
                       comparator_interval="clopper-pearson", e_ch_ci95=[lo, hi])
    return row


def five_point_view(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, n: int, B: int = bootstrap.DRAWS,
                    seed: int = bootstrap.SEED) -> Dict[str, object]:
    """Note section 2. bootstrap.run_family over the confirmatory family's own per-base differences (official, as_deployed, same k, same
    B and seeds), margin -5.0 only; a test that did not run keeps its Holm place with p = 1 (five_tests._family). Labelled secondary."""
    diffs = five_tests.test_differences(rows, k_o, k_s, "as_deployed", n=n)
    m = max((len(v) for v in diffs.values()), default=1) or 1
    filled = {t: (v if v else [-1000.0] * m) for t, v in diffs.items()}
    res = bootstrap.run_family(filled, margin=-5.0, B=B, seed=seed)
    not_run = [t for t, v in diffs.items() if not v]
    for t in not_run:                                                          # exactly as five_tests._family writes a test that did not run
        res["tests"][t] = {"n": 0, "reading": "not run (k = 0: Haiku costs more per sample than the comparator)", "declared": False,
                           "d": None, "ci95": None, "p": 1.0}
    res["not_run"] = not_run
    res["label"] = "secondary, 5-point margin"
    return res


def _per_puzzle_share(rows: Iterable[Mapping[str, object]], planned: int, puzzles: Iterable[str],
                      samples: Optional[range] = None) -> tuple:
    """({item_id: right tries / planned tries} for EVERY puzzle in `puzzles`, missing tries): the D-87 plan's rule 1 (curve.py), "a
    planned try with no final record counts as wrong", used by the main-run markers and by note sections 3 and 5. Only rows of the
    given puzzles (and sample numbers) count; more rows than planned for a puzzle raises."""
    right: Dict[str, int] = defaultdict(int)
    count: Dict[str, int] = defaultdict(int)
    ids = list(puzzles)
    wanted = set(ids)
    for r in rows:
        if str(r["item_id"]) not in wanted or (samples is not None and int(r.get("sample") or 0) not in samples):  # type: ignore[call-overload]
            continue
        count[str(r["item_id"])] += 1
        right[str(r["item_id"])] += int(scoring.row_correct(r, "official"))
    over = [i for i in ids if count[i] > planned]
    if over:
        raise ValueError(f"{over[0]}: {count[over[0]]} rows, {planned} planned")
    return {i: right[i] / planned for i in ids}, sum(planned - count[i] for i in ids)


def _format_and_kinds(rows: Iterable[Mapping[str, object]]) -> Dict[str, object]:
    rows = list(rows)
    answered = [r for r in rows if r.get("kind") == "answered"]
    return {"tries": len(rows), "answered": len(answered),
            "format_compliance": (sum(1 for r in answered if r.get("format_status") == "ok") / len(answered)) if answered else None,
            "refusals": sum(1 for r in rows if r.get("kind") == "refusal" or r.get("stop_reason") == "refusal"),
            "truncations": sum(1 for r in rows if r.get("kind") == "truncated" or r.get("stop_reason") == "max_tokens")}


def d42_robustness(rows: Sequence[Mapping[str, object]], other: Sequence[Mapping[str, object]], n: int,
                   items: Mapping[str, Mapping[str, object]], set_id: str) -> Dict[str, object]:
    """Note section 3. hv (Haiku-medium x10, variant wording) against hm(1-10) (the main run's Haiku-medium samples 1-10) on the 40
    pinned puzzles (base 000-019, both shapes): per puzzle the share right among its 10 designed tries; per shape (20 puzzles) and pooled
    (40) the mean for each arm and the difference hv - hm, with a 95% cluster bootstrap over the 20 base puzzles of the mean of
    hv_b - hm_b (curve.cluster_bootstrap, 2,000 draws, seed 20261012, names d42:6x1 / d42:1x6 / d42:pooled; pooled: a drawn base brings
    both its shapes). Format compliance, refusals and truncations per arm and shape. No test."""
    from .curve import cluster_bootstrap
    from ..pareto.d42 import D42_BASES
    hv = [r for r in other if r["setup"] == "haiku-med-d42-variant"]
    pinned = sorted(i for i, it in items.items() if int(it["base_index"]) in D42_BASES)       # type: ignore[call-overload]
    hm = [r for r in rows if r["setup"] == "haiku-med" and str(r["item_id"]) in set(pinned)]
    v, v_missing = _per_puzzle_share(hv, 10, pinned)
    h, h_missing = _per_puzzle_share(hm, 10, pinned, range(1, 11))
    base_of = {i: f"{set_id}-{int(items[i]['base_index']):03d}" for i in pinned}                       # type: ignore[call-overload]
    shape_of = {i: f"{items[i]['width']}x{items[i]['depth']}" for i in pinned}
    out: Dict[str, object] = {"n_puzzles": len(pinned), "hv_missing_tries": v_missing, "hm_1_10_missing_tries": h_missing}
    for label, shapes in ((scoring.pieces_shape(n), {scoring.pieces_shape(n)}), (scoring.chain_shape(n), {scoring.chain_shape(n)}),
                          ("pooled", {scoring.pieces_shape(n), scoring.chain_shape(n)})):
        ids = sorted(i for i in pinned if shape_of.get(i) in shapes)
        vv = {i: v[i] for i in ids}
        hh = {i: h[i] for i in ids}
        by_base: Dict[str, List[str]] = defaultdict(list)
        for i in ids:
            by_base[base_of[i]].append(i)
        bases = sorted(by_base)

        def stat(sample, by_base=by_base, vv=vv, hh=hh):
            puzzles = [i for b in sample for i in by_base[b]]
            return (math.fsum(vv[i] - hh[i] for i in puzzles) / len(puzzles)) if puzzles else None
        mv = math.fsum(vv.values()) / len(ids) if ids else None
        mh = math.fsum(hh.values()) / len(ids) if ids else None
        out[label] = {"puzzles": len(ids), "hv": mv, "hm_1_10": mh, "difference": (mv - mh) if ids else None,  # type: ignore[operator]
                      "difference_ci95": list(cluster_bootstrap([bases], stat, f"d42:{label}")),
                      "hv_format_and_kinds": _format_and_kinds(r for r in hv if r["shape"] in shapes),
                      "hm_1_10_format_and_kinds": _format_and_kinds(r for r in hm if r["shape"] in shapes and int(r.get("sample") or 0) <= 10)}
    return out


FLAG_R_BLAMES = ("kind", "decoy_confusion")


def flag_r_report(rows: Sequence[Mapping[str, object]], items: Mapping[str, Mapping[str, object]], texts: Mapping[str, str], n: int,
                  B: int = 2_000) -> Dict[str, object]:
    """Note section 4. Haiku-medium's main-run tries (all samples, both shapes), answered and placeable under scoring.local_steps. Slip
    events: at 1xN the FIRST slipped step only, at Nx1 every slipped piece; only blames "kind" / "decoy_confusion". Cells are (base,
    shape, sequence, step); pairs are C(m, 2) per cell, T or G by the step's class; a pair agrees when both wrote identical balances.
    Point counts give fairness.flag_r(..., min_pairs=10); agreement T and G per shape and pooled with a 90% percentile bootstrap over base
    puzzles (B 2,000, seed derive_seed(20261012, "flag_r"); a drawn base brings both shapes and all tries). Unplaceable tries counted."""
    cache: Dict[str, object] = {}
    cells: Dict[tuple, List[tuple]] = defaultdict(list)            # (base, shape, seq, step, cls) -> written states
    unplaceable = 0
    for r in rows:
        if r["setup"] != "haiku-med" or r.get("kind") != "answered":
            continue
        iid = str(r["item_id"])
        if iid not in cache:
            cache[iid] = _puzzle(items[iid])
        placed = scoring.local_steps(texts[str(r["custom_id"])], cache[iid])                  # type: ignore[arg-type]
        if placed["unplaceable"] is not None:
            unplaceable += 1
            continue
        slipped = [st for st in placed["steps"] if st["slipped"]]                               # type: ignore[union-attr]
        if r["shape"] == scoring.chain_shape(n):
            slipped = slipped[:1]                                                                # the first slipped step only
        for st in slipped:
            if st["blame"] in FLAG_R_BLAMES and st["cls"] in ("T", "G"):
                cells[(str(r["base_id"]), str(r["shape"]), st["sequence"], st["step"], st["cls"])].append(tuple(st["written"]))

    def count(keep_bases: Optional[Sequence[str]] = None, shape: Optional[str] = None) -> Dict[str, int]:
        c = {"agree_t": 0, "pairs_t": 0, "agree_g": 0, "pairs_g": 0}
        weights = Counter(keep_bases) if keep_bases is not None else None
        for (base, sh, _, _, cls), written in cells.items():
            if shape is not None and sh != shape:
                continue
            w = 1 if weights is None else weights.get(base, 0)
            if not w:
                continue
            m = len(written)
            c["pairs_" + cls.lower()] += w * (m * (m - 1) // 2)
            c["agree_" + cls.lower()] += w * sum(v * (v - 1) // 2 for v in Counter(written).values())
        return c
    pts = count()
    out: Dict[str, object] = dict(pts, unplaceable_tries=unplaceable,
                                  flag_r=fairness.flag_r(pts["agree_t"], pts["pairs_t"], pts["agree_g"], pts["pairs_g"], min_pairs=10))
    bases = sorted({str(r["base_id"]) for r in rows if r["setup"] == "haiku-med"})
    rng = random.Random(bootstrap.derive_seed(20261012, "flag_r"))
    draws = [rng.choices(bases, k=len(bases)) for _ in range(B)] if bases else []
    for label, shape in ((scoring.pieces_shape(n), scoring.pieces_shape(n)), (scoring.chain_shape(n), scoring.chain_shape(n)), ("pooled", None)):
        c = count(shape=shape)
        d: Dict[str, object] = {}
        for cls in ("t", "g"):
            point = c["agree_" + cls] / c["pairs_" + cls] if c["pairs_" + cls] else None
            reps = []
            for dr in draws:
                cc = count(dr, shape)
                if cc["pairs_" + cls]:
                    reps.append(cc["agree_" + cls] / cc["pairs_" + cls])
            d["agreement_" + cls.upper()] = {"point": point, "ci90": _ends(reps, 0.05, 0.95), "pairs": c["pairs_" + cls]}
        out[label] = d
    return out


def low_information_flag(rows: Sequence[Mapping[str, object]], n: int, items: Mapping[str, Mapping[str, object]]) -> Dict[str, object]:
    """Note section 5. Haiku-medium's single-try whole-answer accuracy at Nx1: each puzzle's share right among its 40 designed samples
    (missing / refused / truncated / unparseable = wrong), the mean over base puzzles; fires strictly above 60.0%: then test 1 is labelled
    "low information: Haiku's single try is already above 60% at 6x1". Also the median, and per-piece accuracy (a try's right pieces / N,
    0 for an unparseable try, over the designed tries, then over puzzles)."""
    import statistics
    pieces = scoring.pieces_shape(n)
    puzzles = sorted(i for i, it in items.items() if f"{it['width']}x{it['depth']}" == pieces)
    hm = [r for r in rows if r["setup"] == "haiku-med" and r["shape"] == pieces]
    shares, missing = _per_puzzle_share(hm, five_tests.DESIGNED_HAIKU_SAMPLES, puzzles)
    per_piece: Dict[str, float] = {i: 0.0 for i in puzzles}
    for r in hm:
        per_piece[str(r["item_id"])] += int(r.get("pieces_right") or 0) / n
    acc = math.fsum(shares.values()) / len(shares) if shares else None
    fires = acc is not None and 100.0 * acc > 60.0
    return {"haiku_med_accuracy": acc, "missing_tries": missing, "median": statistics.median(shares.values()) if shares else None,
            "per_piece_accuracy": (math.fsum(v / five_tests.DESIGNED_HAIKU_SAMPLES for v in per_piece.values()) / len(per_piece)) if per_piece else None,
            "fires": fires, "label_test_1": "low information: Haiku's single try is already above 60% at 6x1" if fires else None}


def realtime_report(other: Sequence[Mapping[str, object]], rows: Sequence[Mapping[str, object]], records: Sequence[Mapping[str, object]],
                    set_dir: Path) -> Dict[str, object]:
    """Note section 6. The main run's own real-time subset (main.build_rt_requests: the first 10 puzzles, Haiku-medium x5, Sonnet-medium,
    Opus-medium): per setup the latency of answered calls (n, median, quartiles by statistics.quantiles(n=4, method="inclusive"), max);
    for Haiku per puzzle the time to a 5-sample vote at once (the largest) and one after another (the sum), with their medians over the
    puzzles; Batch against real time on the same puzzles: official accuracy (share right over tries; Batch Haiku samples 1-5 only) and
    mean output tokens per call, and the difference real time - Batch. No test."""
    import statistics
    from ..pareto.main import build_rt_requests
    from ..pareto.pilot import load_set as _verified_load
    man, items_list = _verified_load(set_dir)
    puzzles = {str(m["item_id"]) for _, _, m in build_rt_requests(man, items_list)}
    by_id = {str(r["custom_id"]): r for r in records}
    pairs = {"rt-haiku-med": ("haiku-med", range(1, 6)), "rt-sonnet-med": ("sonnet-med", None), "rt-opus-med": ("opus-med", None)}
    out: Dict[str, object] = {"puzzles": sorted(puzzles)}

    def tokens(rs):                                                            # over real calls only: a missing try has no record
        vals = [int((by_id[str(r["custom_id"])].get("usage_raw") or {}).get("output_tokens") or 0)   # type: ignore[union-attr]
                for r in rs if str(r["custom_id"]) in by_id]
        return (sum(vals) / len(vals)) if vals else None
    for rt, (batch, samples) in pairs.items():
        rr = [r for r in other if r["setup"] == rt and str(r["item_id"]) in puzzles]
        br = [r for r in rows if r["setup"] == batch and str(r["item_id"]) in puzzles
              and (samples is None or int(r.get("sample") or 0) in samples)]
        lat = sorted(float(by_id[str(r["custom_id"])]["latency_s"]) for r in rr                 # type: ignore[arg-type]
                     if r.get("kind") == "answered" and by_id[str(r["custom_id"])].get("latency_s") is not None)
        q = statistics.quantiles(lat, n=4, method="inclusive") if len(lat) >= 2 else [None, None, None]
        p95 = statistics.quantiles(lat, n=20, method="inclusive")[18] if len(lat) >= 2 else None    # A0
        acc_rt = (sum(scoring.row_correct(r, "official") for r in rr) / len(rr)) if rr else None
        acc_b = (sum(scoring.row_correct(r, "official") for r in br) / len(br)) if br else None
        d: Dict[str, object] = {"calls": len(rr), "latency": {"n": len(lat), "median": statistics.median(lat) if lat else None,
                                                             "quartiles": [q[0], q[2]], "p95": p95, "max": max(lat) if lat else None},
                                "accuracy_realtime": acc_rt, "accuracy_batch": acc_b,
                                "accuracy_difference": (acc_rt - acc_b) if acc_rt is not None and acc_b is not None else None,
                                "output_tokens_realtime": tokens(rr), "output_tokens_batch": tokens(br)}
        if rt == "rt-haiku-med":
            per: Dict[str, List[float]] = defaultdict(list)
            for r in rr:
                lt = by_id[str(r["custom_id"])].get("latency_s")
                if r.get("kind") == "answered" and lt is not None:
                    per[str(r["item_id"])].append(float(lt))                             # type: ignore[arg-type]
            at_once = [max(v) for v in per.values() if v]
            in_turn = [sum(v) for v in per.values() if v]
            d["vote_of_5"] = {"at_once_median": statistics.median(at_once) if at_once else None,
                              "one_after_another_median": statistics.median(in_turn) if in_turn else None}
        out[rt] = d
    return out


def batch_turnaround(run_dir: Path, all_records: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    """Addendum A0, item 6: each Batch wave's turnaround (submit to end), reported separately and not called latency. The call log's
    batch lines carry no time, so it is read from the guard's ledger (`ledger.jsonl`): from the wave's first `send` to its last
    `commit` (results are collected within one poll interval, 60 s, of the batch ending, so this is an upper bound by at most that).
    A wave whose first send and last commit straddle an `INVOCATION <UTC time>` line of the run folder's runner.log (clearance
    Addendum 3: each launch writes one) was settled in a later invocation: its turnaround includes downtime and is flagged."""
    from datetime import datetime
    ledger = Path(run_dir) / "ledger.jsonl"
    if not ledger.is_file():
        return {"computed": False, "reason": "no ledger.jsonl in the run folder"}
    times: Dict[str, Dict[str, str]] = defaultdict(dict)
    for ln in ledger.read_text().splitlines():
        if not ln.strip():
            continue
        e = json.loads(ln)
        if e.get("event") in ("send", "commit") and e.get("key"):
            times[str(e["key"])][str(e["event"])] = str(e["time"])
    invocations: List[datetime] = []
    log_file = Path(run_dir) / "runner.log"
    if log_file.is_file():
        for ln in log_file.read_text(errors="replace").splitlines():
            if ln.startswith("INVOCATION "):
                invocations.append(datetime.fromisoformat(ln.split(" ", 1)[1].strip().replace("Z", "+00:00")))
    out: Dict[str, object] = {"note": "first send to last commit of the wave's keys, from ledger.jsonl; at most one poll interval (60 s) "
                                      "above submit-to-end", "invocations": [x.isoformat() for x in invocations]}
    for r in all_records:
        if r.get("kind") != "batch_submitted":
            continue
        keys = list((r.get("keys") or {}).values())                                            # type: ignore[union-attr]
        sends = [times[k]["send"] for k in keys if "send" in times.get(k, {})]
        commits = [times[k]["commit"] for k in keys if "commit" in times.get(k, {})]
        if sends and commits:
            first, last = datetime.fromisoformat(min(sends)), datetime.fromisoformat(max(commits))
            later = any(first < x < last for x in invocations)
            out[str(r["batch_id"])] = {"wave_id": r.get("wave_id"), "requests": len(keys), "turnaround_s": (last - first).total_seconds(),
                                       "settled_in_a_later_invocation": later,
                                       **({"flag": "includes downtime (settled in a later invocation)"} if later else {})}
    return out


def main_run_markers(rows: Sequence[Mapping[str, object]], n: int, items: Mapping[str, Mapping[str, object]], set_id: str) -> Dict[str, object]:
    """The D-87 curve's main-run markers (research/pilot-plan-ledger.md line 554: "The main run's own Opus, Sonnet and Haiku accuracies at
    the chosen n (fresh sets) are added to the plot as separate markers, labelled "main run""), with the plan's own definitions: point 1,
    whole-answer accuracy per shape and pooled (each base puzzle weighted equally: the mean of its two shapes), each puzzle's share right
    over its PLANNED tries (Haiku 40, Opus and Sonnet 1; rule 1: a planned try with no final record counts as wrong, as curve.py does),
    the missing tries reported; point 2, Haiku with the cluster bootstrap over base puzzles (curve.cluster_bootstrap, seed 20261012),
    Opus and Sonnet with Wilson per shape and the cluster bootstrap pooled."""
    from .curve import cluster_bootstrap, wilson
    out: Dict[str, object] = {"label": "main run"}
    pieces, chain = scoring.pieces_shape(n), scoring.chain_shape(n)
    planned = {"haiku-med": five_tests.DESIGNED_HAIKU_SAMPLES, "opus-med": 1, "sonnet-med": 1}
    base_of = {i: f"{set_id}-{int(it['base_index']):03d}" for i, it in items.items()}              # type: ignore[call-overload]
    shape_of = {i: f"{it['width']}x{it['depth']}" for i, it in items.items()}
    for setup, k in planned.items():
        arm = [r for r in rows if r["setup"] == setup]
        per: Dict[str, Dict[str, float]] = {}
        missing = 0
        for sh in (pieces, chain):
            shares, miss = _per_puzzle_share(arm, k, sorted(i for i in items if shape_of[i] == sh))
            per[sh] = {base_of[i]: v for i, v in shares.items()}
            missing += miss
        bases = sorted(set(per[pieces]) | set(per[chain]))
        pooled = {b: (per[pieces][b] + per[chain][b]) / 2 for b in bases}
        d: Dict[str, object] = {"missing_tries": missing}
        for label, vals in ((pieces, per[pieces]), (chain, per[chain]), ("pooled", pooled)):
            bs = sorted(vals)
            mean = math.fsum(vals.values()) / len(vals) if vals else None
            if setup != "haiku-med" and label != "pooled":
                ci = list(wilson(sum(1 for v in vals.values() if v == 1.0), len(vals))) if vals else None
            else:
                ci = list(cluster_bootstrap([bs], lambda smp, vals=vals: (math.fsum(vals[b] for b in smp) / len(smp)) if smp else None,
                                            f"main:{setup}:{label}"))
            d[label] = {"mean": mean, "ci95": ci, "n_base": len(vals)}
        out[setup] = d
    return out


def analyse_run(set_dir: Path, logs: Sequence[Path], k_path: Path, B: Optional[int] = None, n: int = STEPS_AT_CHOSEN_N,
                fairness_draws: Optional[int] = None, run_dir: Optional[Path] = None, extras: Sequence[str] = (),
                d42: bool = True) -> Dict[str, object]:
    """With `run_dir`, the planned requests are rebuilt (`main_rows.planned_requests` with the run's `extras`), checked against its
    manifest, and every planned try with no final record is a missing row (D-48 row 23): wrong in every view. k is computed from the
    rows of real calls only (a missing row has no cost). The confirmatory family counts missing tries as wrong; `missing_left_out`
    is item 16's exclude-missing view beside it (report_arms.exclude_missing_view; Edith B-1, r7), "no missing items in the five tests' arms" when none is.
    `B` and `fairness_draws` are for tests only; group B (step 15) reads them as its B and draws."""
    planned = None
    if run_dir is not None:
        man0, items0 = main_rows.load_set(set_dir)
        planned = main_rows.planned_requests(man0, list(items0.values()), extras, d42)
        main_rows.check_planned(run_dir, planned)
    built = main_rows.build(set_dir, logs, planned=planned)
    rows, other = built["tests"], built["other"]
    _, items = main_rows.load_set(set_dir)
    texts = {str(r["custom_id"]): str(r.get("answer_text") or "") for r in main_rows.final_records(logs)}
    kw = {"B": B} if B is not None else {}
    from .k_step import load_k
    k = load_k(k_path)                                       # fixed from costs only, committed before this runs (k_step; D-93)
    if run_dir is not None:
        import hashlib
        have = hashlib.sha256((Path(run_dir) / "compact_table.csv").read_bytes()).hexdigest()
        if k.get("compact_table_sha256") != have:
            raise ValueError(f"{k_path} was computed from another compact_table.csv than {run_dir}'s")
        from .k_step import k_from_table
        again = json.loads(json.dumps(k_from_table(Path(run_dir) / "compact_table.csv", n=n), default=str))
        if (again["k_o"], again["k_s"], again["k_from_rows"]) != (k["k_o"], k["k_s"], k["k_from_rows"]):
            raise ValueError(f"{k_path} differs from k recomputed now from {run_dir}/compact_table.csv (k_step)")
    kv = {"k_o": {sh: int(v) for sh, v in k["k_o"].items()}, "k_s": int(k["k_s"])}              # type: ignore[union-attr]
    k_o, k_s = kv["k_o"], kv["k_s"]                                                               # type: ignore[assignment]
    res: Dict[str, object] = {"n": n, "k": k, "k_used": kv,
                              "confirmatory": five_tests.analyse_all_views(rows, k_o, k_s, n=n, **kw),  # type: ignore[arg-type]
                              "secondary": five_tests.analyse_secondary(rows, k_o, k_s, n=n, **kw),     # type: ignore[arg-type]
                              "ties": five_tests.tie_report(rows, k_o, k_s, n=n, **kw),                 # type: ignore[arg-type]
                              "original_repeat_rule_appendix": five_tests.analyse_all_views(rows, k_o, k_s, score="original", n=n, **kw)}  # type: ignore[arg-type]
    fkw = {"B": fairness_draws} if fairness_draws is not None else {}
    for label, first in (("fairness", False), ("fairness_first_slip", True)):
        tries = _tries_for_fairness(rows, items, texts, first)
        records = fairness_input.records_from_tries(tries)
        unplaced = fairness_input.unplaceable_from_tries(tries)
        if not any(r.model == fairness.HAIKU for r in records) or not any(r.model == fairness.OPUS for r in records):
            res[label] = {"computed": False, "reason": "no placeable Haiku or Opus try (fairness_indices needs both)", "unplaceable": unplaced}
        else:
            res[label] = fairness.fairness_indices(records, comparison=fairness.OPUS, unplaceable=unplaced, **fkw)
    res["haiku_repeat_share"] = repeat_share(rows, n)
    res["counts"] = {"five_test_arms": arm_counts(rows), "other_arms": arm_counts(other)}
    man, _ = main_rows.load_set(set_dir)
    res["main_run_markers"] = main_run_markers(rows, n, items, str(man["set_id"]))
    recs = main_rows.final_records(logs)
    latency = {str(r["custom_id"]): r.get("latency_s") for r in recs}
    res["reporting"] = {"note": "research/reporting-definitions-main.md (0d103c0; Edith CLEAN)",
                        "error_ratios": error_ratios(rows, k_o, k_s, n),                               # type: ignore[arg-type]
                        "five_point_view": five_point_view(rows, k_o, k_s, n, **kw),                     # type: ignore[arg-type]
                        "d42_robustness": d42_robustness(rows, other, n, items, str(man["set_id"])),
                        "flag_r": flag_r_report(rows, items, texts, n),
                        "low_information_flag": low_information_flag(rows, n, items),
                        "realtime": realtime_report(other, rows, recs, set_dir),
                        "batch_turnaround": (batch_turnaround(run_dir, list(main_rows.all_records(logs))) if run_dir is not None
                                             else {"computed": False, "reason": "no run folder"})}
    ctx = group_b_context(built, recs, list(main_rows.all_records(logs)), items, str(man["set_id"]), n, k, run_dir, B, fairness_draws)
    from . import report_arms
    res["missing_left_out"] = (report_arms.exclude_missing_view(ctx) if any(r.get("kind") == "missing" for r in rows)
                               else report_arms.NO_MISSING)
    res["reporting"]["group_b"] = group_b(ctx)                                                       # type: ignore[index]
    return res


def group_b_context(built: Mapping[str, object], records: Sequence[Mapping[str, object]], all_records: Sequence[Mapping[str, object]],
                    items: Mapping[str, Mapping[str, object]], set_id: str, n: int, k: Mapping[str, object], run_dir: Optional[Path],
                    B: Optional[int] = None, draws: Optional[int] = None) -> Dict[str, object]:
    """The one context dict the three group-B modules read (see their docstrings): the converter's rows ("tests", "other", "missing"), the
    final and all call-log records, the frozen items, the set id, N, k.json, the run folder; B and draws only in tests (None: the note's
    10,000 and 2,000)."""
    return {"rows": built["tests"], "other": built["other"], "missing": built.get("missing") or [], "records": list(records),
            "all_records": list(all_records), "items": items, "set_id": set_id, "n": n, "k": k, "run_dir": run_dir, "B": B, "draws": draws}


def group_b(ctx: Dict[str, object]) -> Dict[str, object]:
    """Step 15: the three group-B reports merged under the note's item numbers ("item_7" ... "item_24"), with each module's open questions
    and the arms module's ruled readings. One shared ctx, so the shared copies (9a-9c in report_costs, the vote curve in report_votes) are
    computed once."""
    from . import report_arms, report_costs, report_votes
    out: Dict[str, object] = {"note": "research/reporting-definitions-main.md (93334b8; Edith CLEAN), items 7-24, Addenda A-C"}
    questions: Dict[str, object] = {}
    for name, mod in (("report_votes", report_votes), ("report_costs", report_costs), ("report_arms", report_arms)):
        rep = mod.report(ctx)                                                                        # type: ignore[attr-defined]
        for key, value in rep.items():
            if key.startswith("item_"):
                if key in out:
                    raise ValueError(f"{key} is reported by two modules")
                out[key] = value
        questions[name] = rep["open_questions"]
        if "interpretations" in rep:
            out["interpretations"] = rep["interpretations"]
    out["open_questions"] = questions
    kv, ka = report_votes.k_s_pieces(ctx)["k"], report_arms.k_s_pieces(ctx)["k"]                    # type: ignore[index]
    if int(kv) != int(ka):                                                                            # type: ignore[call-overload]
        raise ValueError(f"k_S(6x1) differs: report_votes {kv} (items 7, 8), report_arms {ka} (items 11, 24)")
    out["k_s_6x1"] = int(kv)                                                                          # type: ignore[call-overload]
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True, help="the run folder holding calls.jsonl")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--extras", default="", help="the extras the run was cleared with (main-l14n6-1: sl,ho,hx)")
    ap.add_argument("--k", type=Path, required=True, help="k.json from harness.analysis.k_step, committed before this runs")
    a = ap.parse_args(argv)
    res = analyse_run(a.set, [a.run / "calls.jsonl"], a.k, run_dir=a.run, extras=tuple(x for x in a.extras.split(",") if x))
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
