"""The main run's cost outputs, thinking tokens, run window and later re-pricing, exactly as Karen's dated note defines them
(`research/reporting-definitions-main.md` at 93334b8, Edith CLEAN: Addendum A item 9 (9a to 9h), Addendum B items 19, 22 and 23,
and Addendum C's pins X1-X8 and C1). Plumbing only: every number, seed, draw count, rounding, threshold and price comes from the note,
from the locked code (`harness/pareto/prices.py`: the pinned table and `cost`; `curve.cluster_bootstrap`; `five_tests`; `votes`;
`kscript`) or from the spec. A point the note still leaves open is NOT computed: it is returned as `{"not_computed": <the question>}`
and listed in `OPEN_QUESTIONS`.

    from harness.analysis import report_costs
    out = report_costs.report(ctx)

THE SHARED COPIES (Addendum C, C3). This module holds the one copy of
- item 9a, the list cost of one call: `list_cost(record)` and, per final record of the run, `calls(ctx)`;
- item 9b, dollars per puzzle: `base_costs(ctx, arm, shape)` and its mean / median block `cost_block(ctx, arm, shape, k)`;
- item 9c, cost per correct answer: `cpc_block(ctx, arm, shape, k)`;
`report_votes` and `report_arms` import them. The vote curve (item 8) has its one copy in `report_votes.arm_curve`, used here.

`ctx` (a dict):
- "rows": the five-test rows (`main_rows.build(...)["tests"]`, E3 rows and kind "missing" rows included);
- "other": the other arms' rows (hl, sl, ho, hx, hv, rt*);
- "records": the FINAL call-log records (custom_id, meta, kind, stop_reason, refusal_category, refusal_billed_by_rule, cost_usd,
  usage_raw, latency_s, batch_id, mode, thinking, answer_text, requested_model);
- "items", "set_id", "n" (6), "k" (the k.json dict: k_o per shape, k_s);
- "run_dir" (a Path or None; may hold window.json and ledger.jsonl);
- "B" (optional; tests only): the 10,000-draw statistics' draws (the k-sensitivity rows and 9h), and the shared cluster draws when
  "draws" is not given; "draws" (optional; tests only): the shared cluster bootstrap's 2,000 draws;
- "later_prices" (optional; item 23 only): {"date": "YYYY-MM-DD", "table": {model: prices.Rates}, "long_prompt_table": {model:
  prices.Rates} (optional)} (C1 and C4, item 23).
Shared per-call costs and cells are memoised in ctx["_report_costs_cache"]; the vote curve in report_votes' ctx["_cache"].

Pins applied (Addendum C): X1 the bootstrap names use the main_rows arm names and one name per statistic family, shared across k;
X2 "samples drawn" is the designed number (40; 3 for Haiku-max); X3 a bootstrap draw with no correct answer gives CPC = +inf, kept, an
infinite end is "unbounded" and the share of such draws is reported; X4 a designed call with no record costs $0 and its puzzle stays in
(counted); C1 9a: an error record with no usage is $0, counted, and the real-time calls' logged cost is labelled "real time (list)";
C1 9c: CPC at each k for every Haiku arm with a vote curve; C1 9d: a $0 comparator gives rho* = +inf, kept; C1 9e: no usable vote among
samples 1..k_c gives share 0 (escalates); six paired statistics per "cascade:<shape>:<k_c>"; C1 9f/9g: input tokens are
Usage.prompt_tokens, billed tokens only (a B5-free refusal counts 0); 9g's Haiku tokens per sample are pooled over the shape's samples,
the comparator's are the mean over puzzles; cached k = 0 leaves tests 1-3 not run in that row; C1 9h: 10,000 draws, seed 20261012,
names "ovs:<stat>:<a>-vs-<b>:<shape>", err_ratio by item 1's +inf rule; C1 19: p90 "n < 2"; C1 22: Friday's window, accepted; C1 23:
the later table has the shape of prices.PRICES, items 9a-9d and 9f are re-priced, k never. C4 (Karen, 93334b8): 9d, Haiku's side at $0
in a draw gives R_list* = +inf, rho* = 0, kept and counted; 9h, one ratio rule for cost, CPC and error (x/0 = +inf, 0/x = 0, inf/finite =
+inf, finite/inf = 0, kept; 0/0 and inf/inf dropped and counted; the interval over the kept draws, never withheld); 23, a request over
100,000 prompt tokens uses the later table's long-prompt rows if given, else it is "not re-priced (no long-prompt row)" at its pinned
cost.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from . import bootstrap, five_tests, kscript, scoring, votes
from .curve import cluster_bootstrap
from .main_rows import E3_TAG, FIVE_TEST_ARMS, OTHER_ARMS
from ..pareto import prices
from ..pareto.main import BY_NAME, RT_SETUPS
from ..pareto.outcome import usage_from_raw

NOTE = "research/reporting-definitions-main.md (93334b8), Addendum A item 9, Addendum B items 19, 22, 23, Addendum C"

SHARED_DRAWS = 2_000                       # Addendum A, shared conventions: 2,000 draws
SHARED_SEED = 20261012                     # Addendum A, shared conventions: base seed 20261012
FAMILY_B = bootstrap.DRAWS                 # Addendum A: B = 10,000
FAMILY_SEED = bootstrap.SEED               # Addendum A: base seed 20261011
OVS_DRAWS = 10_000                         # C1 9h: "10,000 draws, seed 20261012"
KMAX = kscript.CAP                         # "k from 1 to 40" (9c, 9g); "min(40, samples drawn)" (9d, 9f)
CASCADE_KC = (5, 10, 20)                   # 9e
CASCADE_TAU = tuple(Fraction(t, 10) for t in range(3, 9))   # 9e: 0.3, 0.4, ..., 0.8
CASCADE_MARGIN_POINTS = 10                 # 9e: "Opus-medium's odd-base accuracy minus 10 points"
VISIBLE_CHARS_PER_TOKEN = 3                # 19: characters of the visible reply / 3, rounded down
TAG_ARM = {**FIVE_TEST_ARMS, **OTHER_ARMS, E3_TAG: "e3"}
ARM_TAG = {arm: tag for tag, arm in TAG_ARM.items()}
HAIKU_VOTE_ARMS = ("haiku-med", "haiku-low", "haiku-thinking-off", "haiku-max")   # C1 9c: every Haiku arm with a vote curve
OVS_PAIRS = (("opus-med", "sonnet-med"), ("opus-low", "sonnet-med"))                # C1 9h
UNDEFINED_CPC = "undefined (no correct answer)"            # 9c
NO_BREAK_EVEN = "no break-even within 40 samples"          # 9d
UNBOUNDED = "unbounded"                                    # items 1, 9d, X3
BATCH_LABEL, REALTIME_LABEL = "Batch", "real time (list)"  # 9a; C1 9a

OPEN_QUESTIONS: Dict[str, str] = {}             # the last three are pinned by Addendum C4 (items 2-4)
NOT_REPRICED = "not re-priced (no long-prompt row)"   # C4 item 4
RHO_DIFFERS = "the price ratio differs between input and output on this table"   # 9d (Edith driver review r8, C-2)
UNDEFINED_0_0 = "undefined (0/0)"                     # 9h (C-3)


# ---------------------------------------------------------------- shared helpers

def cluster_draws(ctx: Mapping[str, object]) -> int:
    """The shared cluster bootstrap's draws (Addendum A: 2,000); tests override with ctx "draws" (or "B")."""
    return int(ctx.get("draws") or ctx.get("B") or SHARED_DRAWS)                          # type: ignore[call-overload]


def family_draws(ctx: Mapping[str, object], default: int = FAMILY_B) -> int:
    """The 10,000-draw statistics (the confirmatory machinery, 9h); tests override with ctx "B"."""
    return int(ctx.get("B") or default)                                                    # type: ignore[call-overload]


def _shapes(ctx: Mapping[str, object]) -> Tuple[str, str]:
    n = int(ctx["n"])                                                                      # type: ignore[call-overload]
    return scoring.pieces_shape(n), scoring.chain_shape(n)


def _all_rows(ctx: Mapping[str, object]) -> List[Mapping[str, object]]:
    return list(ctx.get("rows") or []) + list(ctx.get("other") or [])                     # type: ignore[call-overload]


def _cache(ctx: dict) -> dict:
    return ctx.setdefault("_report_costs_cache", {})


def show(x: Optional[float]) -> object:
    """An infinite end is reported as "unbounded" (items 1, 9d; X3)."""
    return UNBOUNDED if x is not None and math.isinf(x) else x


def _f(x: Optional[Fraction]) -> Optional[float]:
    return None if x is None else float(x)


def at_least(a: float, b: float) -> bool:
    """"At least" (9d's k_match, 9e's tau) compared after rounding both sides to 1e-9, the rule C1 pins for item 20's "reaches" (Edith
    driver review r8, C-1): an exact rational tie such as 2/3 must not fail on float rounding."""
    return round(a, 9) >= round(b, 9)


def _base_index(base_id: str) -> int:
    return int(str(base_id).rsplit("-", 1)[1])


def designed_samples(tag: str) -> Optional[int]:
    """Designed samples per puzzle for a setup tag, from the runner (main.BY_NAME; main.RT_SETUPS for rt*); None for E3."""
    if tag == E3_TAG:
        return None
    if tag in BY_NAME:
        return BY_NAME[tag].n
    if tag.startswith("rt") and tag[2:] in dict(RT_SETUPS):
        return dict(RT_SETUPS)[tag[2:]]
    raise ValueError(f"unknown setup tag {tag!r}")


def kmax_of(arm: str) -> int:
    """min(40, samples drawn) with samples drawn = the arm's DESIGNED samples per puzzle (X2): 40, or 3 for Haiku-max."""
    return min(KMAX, int(designed_samples(ARM_TAG[arm]) or 0))


def _boot(bases: Sequence[str], stat, name: str, draws: int) -> List[object]:
    lo, hi = cluster_bootstrap([list(bases)], stat, name, draws=draws, seed=SHARED_SEED)
    return [show(lo), show(hi)]


def test_ks(ctx: Mapping[str, object]) -> Dict[str, Tuple[str, str, int]]:
    """{t1/t2/t3: (comparator arm, shape, k)} from five_tests.tests_for and the k file."""
    k = ctx["k"]
    out = {}
    for name, (chal, comp, shape, which) in five_tests.tests_for(int(ctx["n"])).items():   # type: ignore[call-overload]
        if which == "O":
            out[name] = (comp, shape, int(k["k_o"][shape]))                                # type: ignore[index]
        elif which == "S":
            out[name] = (comp, shape, int(k["k_s"]))                                       # type: ignore[index]
    return out


# ---------------------------------------------------------------- 9a: the list cost of one call (the shared copy)

class LongPromptNotRepriced(ValueError):
    """Item 23 (C4): a long-prompt request and a later table with no long-prompt row for its model."""


def _price(model: str, usage: prices.Usage, table: Optional[Mapping[str, prices.Rates]] = None,
           long_table: Optional[Mapping[str, prices.Rates]] = None) -> Decimal:
    """prices.cost(model, usage, batch=False) on the pinned table; with `table` (item 23) the same sum on that table's row, a request over
    the long-prompt threshold on `long_table`'s row for its model (C4 item 4; none given: LongPromptNotRepriced)."""
    if table is None:
        return prices.cost(model, usage, batch=False)
    r = table[model]
    if model in prices.LONG_PROMPT_PRICES and usage.prompt_tokens > prices.LONG_PROMPT_THRESHOLD:
        if not long_table or model not in long_table:
            raise LongPromptNotRepriced(NOT_REPRICED)
        r = long_table[model]
    with prices.money_context():
        return (usage.input_tokens * r.input + usage.output_tokens * r.output + usage.cache_read_tokens * r.cache_read
                + usage.cache_write_5m_tokens * r.cache_write_5m + usage.cache_write_1h_tokens * r.cache_write_1h) / prices.MILLION


def is_free_b5(rec: Mapping[str, object], free_ids: frozenset = frozenset()) -> bool:
    """9a: a refusal that rule B5 says is not billed: `refusal_billed_by_rule` false, or marked `free_by_rule` (on the record or in the
    run's ledger)."""
    return rec.get("kind") == "refusal" and (rec.get("refusal_billed_by_rule") is False or rec.get("free_by_rule") is True
                                             or str(rec.get("custom_id")) in free_ids)


def list_cost(rec: Mapping[str, object], free_ids: frozenset = frozenset(),
              table: Optional[Mapping[str, prices.Rates]] = None, long_table: Optional[Mapping[str, prices.Rates]] = None) -> Decimal:
    """Note 9a, the ONE copy: `prices.cost(requested_model, Usage(input, output, cache_read, cache_write_5m, cache_write_1h from
    usage_raw), batch=False)` on the pinned table; $0 for a refusal that rule B5 does not bill; every other call (answered, truncated,
    unparseable, billed refusal) what its usage says; a record with no usage (an `error` after its retries) $0, as the guard commits it
    (C1 9a)."""
    if is_free_b5(rec, free_ids):
        return Decimal(0)
    return _price(str(rec.get("requested_model")), usage_from_raw(dict(rec.get("usage_raw") or {})), table, long_table)


def _ledger_free_ids(run_dir: Optional[Path]) -> Tuple[frozenset, bool]:
    """custom_ids whose ledger commit is flagged free_by_rule or carries a free_by_rule_marked event (B5); (ids, ledger read)."""
    if run_dir is None or not (Path(run_dir) / "ledger.jsonl").is_file():
        return frozenset(), False
    ids = set()
    for ln in (Path(run_dir) / "ledger.jsonl").read_text().splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        if (d.get("event") == "commit" and d.get("free_by_rule") is True) or d.get("event") == "free_by_rule_marked":
            ids.add(str(d["key"]).split("@")[0].split("#a")[0])             # keys are <cid>@<n> (Batch) or <cid>#a<n> (real time)
    return frozenset(ids), True


def calls(ctx: dict) -> Dict[str, Dict[str, object]]:
    """Note 9a, per final record: the list cost (`list_cost`, B5-free refusals at $0, the run's ledger read for free_by_rule), the
    logged cost_usd beside it ("Batch"; "real time (list)" for the rt* calls, C1 9a), and the BILLED tokens (C1 9f/9g: prompt_tokens
    and output tokens; a B5-free refusal counts 0)."""
    c = _cache(ctx)
    if "calls" in c:
        return c["calls"]
    free_ledger, _ = _ledger_free_ids(ctx.get("run_dir"))                                # type: ignore[arg-type]
    table, long_table = ctx.get("_price_table"), ctx.get("_long_price_table")
    out: Dict[str, Dict[str, object]] = {}
    for rec in ctx.get("records") or []:
        cid = str(rec["custom_id"])
        raw = rec.get("usage_raw")
        usage = usage_from_raw(dict(raw or {}))
        free = is_free_b5(rec, free_ledger)
        logged = rec.get("cost_usd")
        meta = rec.get("meta") or {}
        tag = str(meta.get("setup"))
        repriced = True
        try:
            lst = list_cost(rec, free_ledger, table, long_table)                           # type: ignore[arg-type]
        except LongPromptNotRepriced:
            lst, repriced = list_cost(rec, free_ledger), False                             # C4 item 4: the pinned-table cost stays
        out[cid] = {"list": lst, "repriced": repriced,
                    "batch": None if logged in (None, "") else Decimal(str(logged)),
                    "batch_label": REALTIME_LABEL if tag.startswith("rt") else BATCH_LABEL, "free_b5": free,
                    "no_usage": raw is None, "usage": usage, "model": str(rec.get("requested_model")), "tag": tag,
                    "arm": TAG_ARM.get(tag, tag),
                    "billed_in": 0 if free else usage.prompt_tokens, "billed_out": 0 if free else usage.output_tokens,
                    "shape": f"{meta.get('width')}x{meta.get('depth')}" if meta.get("width") is not None else None,
                    "base_id": (f"{meta.get('set_id')}-{int(meta['base_index']):03d}"            # type: ignore[call-overload]
                                if meta.get("base_index") is not None else None),
                    "answer_text": rec.get("answer_text"), "kind": rec.get("kind")}
    c["calls"] = out
    return out


def item_9a(ctx: dict) -> Dict[str, object]:
    """Note 9a. Per call: list cost (B5-free refusals at $0) and the logged cost_usd ("Batch"; "real time (list)" for rt*); per arm and
    shape the totals. Records without usage (error records: $0, C1 9a) are counted. Pinned table PRICE_TABLE_DATE."""
    cs = calls(ctx)
    _, ledger_read = _ledger_free_ids(ctx.get("run_dir"))                                # type: ignore[arg-type]
    per_arm: Dict[str, Dict[str, object]] = {}
    for c in cs.values():
        d = per_arm.setdefault(f"{c['arm']}:{c['shape']}", {"calls": 0, "list_usd": Decimal(0), "batch_usd_logged": Decimal(0),
                                                             "batch_cost_missing": 0, "free_b5_refusals": 0, "records_without_usage": 0,
                                                             "batch_label": c["batch_label"]})
        d["calls"] += 1                                                                    # type: ignore[operator]
        d["list_usd"] += c["list"]                                                         # type: ignore[operator]
        if c["batch"] is None:
            d["batch_cost_missing"] += 1                                                   # type: ignore[operator]
        else:
            d["batch_usd_logged"] += c["batch"]                                            # type: ignore[operator]
        d["free_b5_refusals"] += int(bool(c["free_b5"]))                                   # type: ignore[operator]
        d["records_without_usage"] += int(bool(c["no_usage"]))                             # type: ignore[operator]
    return {"price_table_date": ctx.get("_price_table_date") or prices.PRICE_TABLE_DATE, "ledger_read_for_free_by_rule": ledger_read,
            "records_without_usage": sum(1 for c in cs.values() if c["no_usage"]),
            "per_call": {cid: {"list_usd": str(c["list"]), "batch_usd_logged": None if c["batch"] is None else str(c["batch"]),
                               "batch_label": c["batch_label"], "free_b5": c["free_b5"], "no_usage": c["no_usage"]}
                         for cid, c in sorted(cs.items())},
            "by_arm_shape": {k: {kk: (str(v) if isinstance(v, Decimal) else v) for kk, v in d.items()} for k, d in sorted(per_arm.items())},
            "label": "list price (9a); Batch = the logged cost_usd ('real time (list)' for the rt* calls)"}


# ---------------------------------------------------------------- 9b: dollars per puzzle (the shared copy)

def cells(ctx: dict) -> Dict[Tuple[str, str], Dict[str, object]]:
    """{(arm, shape): {"tag", "how" ("single" | "per_sample" | "sum"), "designed", "bases": {base_id: [custom_ids of its real calls]}}}:
    every arm's designed bases (from its rows, missing rows included) and the real calls on each; E3's step calls grouped by base."""
    c = _cache(ctx)
    if "cells" in c:
        return c["cells"]
    cs = calls(ctx)
    out: Dict[Tuple[str, str], Dict[str, object]] = {}
    for r in _all_rows(ctx):
        cid = str(r.get("custom_id"))
        if r["setup"] == "e3":
            out.setdefault(("e3", str(r["shape"])), {"tag": E3_TAG, "how": "sum", "designed": None, "bases": {}})["bases"].setdefault(  # type: ignore[union-attr]
                str(r["base_id"]), [])
            continue
        tag = str(r.get("tag") or ARM_TAG.get(str(r["setup"])) or (cs[cid]["tag"] if cid in cs else ""))
        n = designed_samples(tag)
        cell = out.setdefault((str(r["setup"]), str(r["shape"])), {"tag": tag, "how": "single" if n == 1 else "per_sample",
                                                                    "designed": n, "bases": {}})
        lst = cell["bases"].setdefault(str(r["base_id"]), [])                             # type: ignore[union-attr]
        if cid in cs:
            lst.append(cid)
    for cid, cc in cs.items():
        if cc["tag"] == E3_TAG:
            cell = out.setdefault(("e3", str(cc["shape"])), {"tag": E3_TAG, "how": "sum", "designed": None, "bases": {}})
            cell["bases"].setdefault(str(cc["base_id"]), []).append(cid)                   # type: ignore[union-attr]
    c["cells"] = out
    return out


def base_costs(ctx: dict, arm: str, shape: str, field: str = "list") -> Tuple[Dict[str, Optional[Fraction]], int]:
    """Note 9b, the ONE copy: the arm's cost on each base puzzle (exact): a single-call arm, that call's cost; E3, the sum over its step
    calls; a sampled arm, the puzzle's mean cost per sample over its drawn samples, which X2 / X4 make the DESIGNED samples, a designed
    call with no record costing $0 (the vote at k costs k times this). Every base puzzle of the arm stays in (X4). `field` "batch" uses
    the logged cost (None if a real call logged none). Returns ({base: cost}, designed calls with no record)."""
    cell = cells(ctx).get((arm, shape))
    if cell is None:
        return {}, 0
    cs = calls(ctx)
    out: Dict[str, Optional[Fraction]] = {}
    no_record = 0
    for b, cids in sorted(cell["bases"].items()):                                        # type: ignore[union-attr]
        vals = [cs[cid][field] for cid in cids]
        if cell["how"] == "per_sample":
            if len(cids) > int(cell["designed"]):                                          # type: ignore[call-overload]
                raise ValueError(f"{arm} {shape} {b}: {len(cids)} calls, {cell['designed']} designed")
            no_record += int(cell["designed"]) - len(cids)                                 # type: ignore[call-overload]
        elif cell["how"] == "single" and not cids:
            no_record += 1
        if any(v is None for v in vals):
            out[b] = None
            continue
        tot = sum((Fraction(v) for v in vals), Fraction(0))                              # type: ignore[arg-type]
        out[b] = tot / int(cell["designed"]) if cell["how"] == "per_sample" else tot      # type: ignore[call-overload]
    return out, no_record


def _stats(costs: Mapping[str, Fraction], arm: str, shape: str, draws: int, scale: int = 1) -> Dict[str, object]:
    bases = sorted(costs)
    vals = {b: float(costs[b] * scale) for b in bases}
    if not bases:
        return {"n_bases": 0, "mean": None, "median": None, "mean_ci95": [None, None], "median_ci95": [None, None]}
    mean = sum((costs[b] for b in bases), Fraction(0)) * scale / len(bases)
    med = statistics.median([costs[b] * scale for b in bases])
    return {"n_bases": len(bases), "mean": float(mean), "median": float(med),
            "mean_ci95": _boot(bases, lambda s: math.fsum(vals[b] for b in s) / len(s), f"cost_mean:{arm}:{shape}", draws),  # type: ignore[index]
            "median_ci95": _boot(bases, lambda s: statistics.median([vals[b] for b in s]), f"cost_median:{arm}:{shape}", draws)}  # type: ignore[index]


def cost_block(ctx: dict, arm: str, shape: str, k: int = 1) -> Dict[str, object]:
    """Note 9b at k (k = 1 for single-call arms, E3 and one Haiku sample): the mean over base puzzles (headline) and the median
    (sensitivity) of the list cost per puzzle, each with the shared cluster bootstrap "cost_mean:<arm>:<shape>" /
    "cost_median:<arm>:<shape>" (one name for every k: X1); the number of designed calls with no record (X4). Memoised."""
    memo = _cache(ctx).setdefault("cost_block", {})
    key = (arm, shape, k)
    if key not in memo:
        costs, no_record = base_costs(ctx, arm, shape)
        known = {b: v for b, v in costs.items() if v is not None}
        memo[key] = dict(_stats(known, arm, shape, cluster_draws(ctx), scale=k), k=k, calls_without_record=no_record,
                         unit="USD, list price")
    return memo[key]


def item_9b(ctx: dict) -> Dict[str, object]:
    """Note 9b. Per arm and shape: the mean over base puzzles (headline) and the median (sensitivity) of the list cost per puzzle (a
    sampled arm per sample, = the vote at k = 1), with the shared cluster bootstrap. For every Haiku arm with a vote curve the vote's
    mean cost for k = 1..min(40, designed); for Haiku-medium also the vote at each test's k (same names: X1). The mean of the logged
    cost per puzzle is given beside it ("Batch", or "real time (list)" for the rt* arms)."""
    out: Dict[str, object] = {}
    for (arm, shape), cell in sorted(cells(ctx).items()):
        batch, _ = base_costs(ctx, arm, shape, "batch")
        d = dict(cost_block(ctx, arm, shape), how=cell["how"])
        bvals = [v for v in batch.values() if v is not None]
        d["batch_mean"] = float(sum(bvals, Fraction(0)) / len(bvals)) if bvals and len(bvals) == len(batch) else None
        d["batch_label"] = REALTIME_LABEL if str(cell["tag"]).startswith("rt") else BATCH_LABEL
        if cell["how"] == "per_sample":
            d["label"] = "per sample (the vote at k = 1); the vote at k costs k times this"
        if arm in HAIKU_VOTE_ARMS:
            m = d["mean"]
            d["vote_mean_by_k"] = [None if m is None else k * m for k in range(1, kmax_of(arm) + 1)]   # type: ignore[operator]
        if arm == "haiku-med":
            d["vote_at_test_k"] = {t: cost_block(ctx, arm, shape, k) for t, (_, sh, k) in test_ks(ctx).items() if sh == shape and k >= 1}
        out[f"{arm}:{shape}"] = d
    return {"label": "list price, mean dollars per puzzle (headline) and median (sensitivity)", "arms": out}


# ---------------------------------------------------------------- the vote curve (item 8's one copy lives in report_votes)

def vote_points(ctx: dict, arm: str, shape: str, k: int) -> Dict[str, float]:
    """Per base, the arm's vote@k in points from the ONE item 8 curve (report_votes.arm_curve: official, as_deployed, designed samples,
    tie "random"); vote@k here equals five_tests.vote_scores at k for Haiku-medium."""
    from . import report_votes
    return {b: 100.0 * float(c[k - 1]["acc"]) for b, c in report_votes.arm_curve(ctx, arm, shape).items() if len(c) >= k}  # type: ignore[arg-type]


# ---------------------------------------------------------------- 9c: cost per correct answer (the shared copy)

def _cpc(costs: Mapping[str, Fraction], scores: Mapping[str, float], name: str, draws: int, scale: int = 1) -> Dict[str, object]:
    bases = sorted(set(costs) & set(scores))
    c = {b: float(costs[b] * scale) for b in bases}
    right = math.fsum(scores[b] for b in bases) / 100.0
    total = math.fsum(c.values())
    no_correct = [0]

    def stat(sample):
        s = math.fsum(scores[b] for b in sample) / 100.0
        if s == 0:
            no_correct[0] += 1                                                           # X3: CPC = +inf, kept
            return math.inf
        return math.fsum(c[b] for b in sample) / s
    ci = _boot(bases, stat, name, draws) if bases else [None, None]
    return {"n_bases": len(bases), "total_usd": total, "correct": right, "cpc": (total / right) if right > 0 else UNDEFINED_CPC,
            "ci95": ci, "share_draws_no_correct": (no_correct[0] / draws) if bases else None,
            "bases_left_out": sorted(set(costs) ^ set(scores))}


def _batch_cpc(batch: Mapping[str, Optional[Fraction]], scores: Mapping[str, float], k: int) -> object:
    """Fix 7's Batch-price CPC beside 9c's (point only): the logged cost (k x the per-sample cost for the vote) over the same bases;
    None if any of the arm's calls logged no cost."""
    if any(v is None for v in batch.values()):
        return None
    bases = sorted(set(batch) & set(scores))
    right = math.fsum(scores[b] for b in bases) / 100.0
    return math.fsum(float(batch[b] * k) for b in bases) / right if right > 0 else UNDEFINED_CPC     # type: ignore[operator]


def single_scores(ctx: dict, arm: str, shape: str, view: str = "as_deployed") -> Dict[str, float]:
    """Official per-base scores in points: E3 five_tests.e3_arm_scores; every other arm five_tests.single_scores (a sampled arm: its
    single-try accuracy over its tries)."""
    if arm == "e3":
        return five_tests.e3_arm_scores(list(ctx["rows"]), shape, view)                   # type: ignore[arg-type]
    return five_tests.single_scores(_all_rows(ctx), arm, shape, view)                     # type: ignore[arg-type]


def cpc_block(ctx: dict, arm: str, shape: str, k: Optional[int] = None) -> Dict[str, object]:
    """Note 9c, the ONE copy. CPC = sum_b cost_b / (sum_b score_b / 100) with 9b's list costs and the official, as_deployed per-base
    scores: k None, the single try (single_scores; a sampled arm at its per-sample cost); k >= 1, the arm's vote at k (cost k x the
    per-sample cost, score vote@k from the item 8 curve). No right answer: "undefined (no correct answer)". Interval: the shared cluster
    bootstrap "cpc:<arm>:<shape>" (one name for every k, X1); a draw with no correct answer gives +inf, kept (X3), with its share. The
    Batch-price CPC (Fix 7) beside it, point only. Memoised."""
    memo = _cache(ctx).setdefault("cpc_block", {})
    key = (arm, shape, k)
    if key not in memo:
        costs, _ = base_costs(ctx, arm, shape)
        batch, _ = base_costs(ctx, arm, shape, "batch")
        costs = {b: v for b, v in costs.items() if v is not None}
        scores = single_scores(ctx, arm, shape) if k is None else vote_points(ctx, arm, shape, k)
        d = _cpc(costs, scores, f"cpc:{arm}:{shape}", cluster_draws(ctx), 1 if k is None else k)
        d.update(k=1 if k is None else k, batch_cpc=_batch_cpc(batch, scores, 1 if k is None else k),
                 how="single try" if k is None else "vote at k")
        memo[key] = d
    return memo[key]


def item_9c(ctx: dict) -> Dict[str, object]:
    """Note 9c (and Fix 7). Per arm and shape: CPC of the single try; for every Haiku arm with a vote curve (C1 9c) the vote's CPC at
    every k = 1..min(40, designed), and for Haiku-medium at each test's k."""
    out: Dict[str, object] = {}
    for (arm, shape), cell in sorted(cells(ctx).items()):
        if arm in HAIKU_VOTE_ARMS:
            by_k = {k: cpc_block(ctx, arm, shape, k) for k in range(1, kmax_of(arm) + 1)}
            d: Dict[str, object] = {"vote_by_k": by_k}
            if arm == "haiku-med":
                d["vote_at_test_k"] = {t: by_k[k] for t, (_, sh, k) in test_ks(ctx).items() if sh == shape and 1 <= k <= kmax_of(arm)}
        else:
            d = dict(cpc_block(ctx, arm, shape))
            if cell["how"] == "per_sample":
                d["label"] = "single try (k = 1): per-sample cost and single-try score (C1 9c: no vote curve)"
        out[f"{arm}:{shape}"] = d
    return {"label": "cost per correct answer, list price (9c)", "arms": out}


# ---------------------------------------------------------------- 9d: the break-even price ratio

COMPARATOR_MODEL = {"opus-med": prices.OPUS, "sonnet-med": prices.SONNET}


def _rho_list(comp_model: str, table: Optional[Mapping[str, prices.Rates]] = None) -> Fraction:
    """9d: the list price ratio per token, comparator / Haiku, read from the pinned table (or item 23's); the note says it is the same
    for input and output (40 for Opus, 20 for Sonnet), which is checked."""
    t = table or prices.PRICES
    a, h = t[comp_model], t[prices.HAIKU]
    r_in, r_out = Fraction(a.input) / Fraction(h.input), Fraction(a.output) / Fraction(h.output)
    if r_in != r_out:
        raise ValueError(f"{comp_model}: input ratio {r_in} differs from output ratio {r_out}; 9d assumes one ratio")
    return r_in


def item_9d(ctx: dict) -> Dict[str, object]:
    """Note 9d, per shape and comparator (Opus-medium, Sonnet-medium). k_match: the smallest k in 1..min(40, designed 40) (X2) whose
    Haiku-medium mean vote@k (item 8 curve) is at least the comparator's mean accuracy on the same bases; else "no break-even within 40
    samples". R_list: the comparator's mean list cost per puzzle / Haiku's mean list cost per sample (9b; X4). rho* = rho_list x k_match
    / R_list. Interval: k_match, R_list and rho* recomputed in each replicate of the shared cluster bootstrap
    "break_even:<comparator>:<shape>"; no k_match gives +inf, kept; a $0 comparator gives R_list* = 0, rho* = +inf, kept (C1 9d); an
    infinite end is "unbounded"; Haiku's side at $0 gives R_list* = +inf, rho* = 0, kept (C4 item 2); both sides at $0 is 0/0, dropped
    and counted (item 1's rule); the shares of such replicates are reported."""
    from . import report_votes
    draws = cluster_draws(ctx)
    out: Dict[str, object] = {}
    for comp in ("opus-med", "sonnet-med"):
        try:
            rho = _rho_list(COMPARATOR_MODEL[comp], ctx.get("_price_table"))              # type: ignore[arg-type]
        except ValueError:                                                                 # C-2: an item 23 table can have two ratios
            for shape in _shapes(ctx):
                out[f"{comp}:{shape}"] = {"not_computed": RHO_DIFFERS}
            continue
        for shape in _shapes(ctx):
            curves = report_votes.arm_curve(ctx, "haiku-med", shape)
            kmax = kmax_of("haiku-med")
            comp_scores = single_scores(ctx, comp, shape)
            comp_cost, _ = base_costs(ctx, comp, shape)
            h_cost, _ = base_costs(ctx, "haiku-med", shape)
            bases = sorted(b for b in curves if b in comp_scores and comp_cost.get(b) is not None and h_cost.get(b) is not None)
            if not bases or kmax < 1:
                out[f"{comp}:{shape}"] = {"n_bases": len(bases), "computed": False}
                continue

            def solve(sample, curves=curves, comp_scores=comp_scores, comp_cost=comp_cost, h_cost=h_cost, kmax=kmax):
                m = len(sample)
                target = math.fsum(comp_scores[b] for b in sample) / m
                km = None
                for k in range(1, kmax + 1):
                    if at_least(math.fsum(100.0 * float(curves[b][k - 1]["acc"]) for b in sample) / m, target):   # type: ignore[index, arg-type]
                        km = k
                        break
                c_pp = sum((comp_cost[b] for b in sample), Fraction(0)) / m               # type: ignore[misc]
                h_ps = sum((h_cost[b] for b in sample), Fraction(0)) / m                  # type: ignore[misc]
                return km, c_pp, h_ps, target
            km, c_pp, h_ps, target = solve(bases)
            infs, zero_c, zero_h, both = [0], [0], [0], [0]

            def stat(sample, rho=rho, solve=solve, infs=infs, zero_c=zero_c, zero_h=zero_h, both=both):
                k2, c2, h2, _ = solve(sample)
                if k2 is None:
                    infs[0] += 1
                    return math.inf
                if h2 == 0 and c2 == 0:
                    both[0] += 1                                                           # R_list* = 0/0: dropped and counted
                    return None
                if h2 == 0:
                    zero_h[0] += 1                                                         # C4 item 2: R_list* = +inf, rho* = 0, kept
                    return 0.0
                if c2 == 0:
                    zero_c[0] += 1                                                         # C1 9d: R_list* = 0, rho* = +inf, kept
                    return math.inf
                return float(rho * k2 / (c2 / h2))
            ci = _boot(bases, stat, f"break_even:{comp}:{shape}", draws)
            r = (c_pp / h_ps) if h_ps else None
            if km is None:
                star: object = NO_BREAK_EVEN
            elif not h_ps and not c_pp:
                star = "undefined (both sides $0: R_list = 0/0)"
            elif not h_ps:
                star = 0.0                                                                 # C4 item 2
            elif not c_pp:
                star = UNBOUNDED
            else:
                star = float(rho * km / r)                                                 # type: ignore[operator]
            out[f"{comp}:{shape}"] = {"n_bases": len(bases), "k_cap": kmax, "comparator_accuracy": target,
                                      "k_match": km if km is not None else NO_BREAK_EVEN, "R_list": _f(r), "rho_list": float(rho),
                                      "rho_star": star, "ci95": ci, "R_list_infinite": not h_ps and bool(c_pp),
                                      "share_replicates_zero_haiku_cost": zero_h[0] / draws,
                                      "replicates_dropped_both_sides_zero": both[0],
                                      "share_replicates_no_k_match": infs[0] / draws,
                                      "share_replicates_zero_comparator_cost": zero_c[0] / draws}
    return {"label": "break-even price ratio (offline, D-27)", "cells": out}


# ---------------------------------------------------------------- 9e: the escalate-to-Opus cascade

def item_9e(ctx: dict) -> Dict[str, object]:
    """Note 9e (Fix 7). Per shape and k_c in {5, 10, 20}: the vote over Haiku-medium samples 1..k_c by sample index (top answer = the
    most common non-empty vote key; its share = count / k_c; a top tie scored by D-33 at 1/m: votes.vote_accuracy_at_k at k = k_c over
    exactly those samples, a missing sample a vote for nothing); no usable vote among them gives share 0, so the puzzle escalates (C1
    9e). For tau in {0.3, ..., 0.8}: share < tau takes Opus-medium's answer (right or wrong), else the vote. Per base: official accuracy;
    cost = list cost of samples 1..k_c (a missing one $0, X4) + Opus-medium's list cost if escalated. Frontier: mean accuracy, mean cost
    and escalation rate for every (k_c, tau). Recommended tau per k_c on the ODD bases: the cheapest tau with odd-base accuracy >= Opus's
    odd-base accuracy - 10 points (none: the highest accuracy); ties to the lower cost, then the lower tau. Scored on the EVEN bases beside
    Opus-medium, with the shared cluster bootstrap over the even bases "cascade:<shape>:<k_c>" for six paired statistics (C1 9e): the
    cascade's accuracy and mean cost, Opus-medium's, and the two differences (cascade - Opus). Exploratory."""
    draws = cluster_draws(ctx)
    cs = calls(ctx)
    out: Dict[str, object] = {}
    for shape in _shapes(ctx):
        ans = five_tests._haiku_answers(list(ctx["rows"]), shape, "as_deployed", five_tests.DESIGNED_HAIKU_SAMPLES, "official")  # type: ignore[arg-type]
        by_sample: Dict[str, Dict[int, Mapping[str, object]]] = defaultdict(dict)
        for r in ctx["rows"]:                                                             # type: ignore[union-attr]
            if r["setup"] == "haiku-med" and r["shape"] == shape:
                by_sample[str(r["base_id"])][int(r["sample"])] = r
        o_score = single_scores(ctx, "opus-med", shape)
        o_cost, _ = base_costs(ctx, "opus-med", shape)
        bases = sorted(b for b in by_sample if b in o_score and o_cost.get(b) is not None)
        sh: Dict[str, object] = {"n_bases": len(bases), "bases_left_out": sorted(set(by_sample) - set(bases))}   # no Opus row
        for kc in CASCADE_KC:
            per: Dict[str, Tuple[Fraction, float, Fraction]] = {}
            no_vote = []
            for b in bases:
                rows = [by_sample[b].get(s) for s in range(1, kc + 1)]
                keys = [scoring.vote_key(r, "official") if r is not None else None for r in rows]
                counts = Counter(k for k in keys if k is not None)
                hcost = sum((Fraction(cs[str(r["custom_id"])]["list"]) for r in rows                    # type: ignore[arg-type]
                             if r is not None and str(r.get("custom_id")) in cs), Fraction(0))
                if not counts:
                    no_vote.append(b)
                    per[b] = (Fraction(0), 0.0, hcost)                                      # C1 9e: share 0, always escalates
                    continue
                share = Fraction(max(counts.values()), kc)
                acc = float(votes.vote_accuracy_at_k(keys, str(ans[b]["correct"]), kc, tie="random")["acc"])  # type: ignore[arg-type]
                per[b] = (share, acc, hcost)

            def run(tau: Fraction, bs: Sequence[str], per=per):
                acc, cost, esc = [], [], 0
                for b in bs:
                    share, va, hc = per[b]
                    if share < tau:
                        esc += 1
                        acc.append(o_score[b] / 100.0)
                        cost.append(hc + o_cost[b])                                       # type: ignore[operator]
                    else:
                        acc.append(va)
                        cost.append(hc)
                return acc, cost, esc
            frontier = {}
            for tau in CASCADE_TAU:
                acc, cost, esc = run(tau, bases)
                frontier[str(float(tau))] = {"accuracy": 100.0 * math.fsum(acc) / len(acc) if acc else None,
                                             "mean_cost": float(sum(cost, Fraction(0)) / len(cost)) if cost else None,
                                             "escalation_rate": esc / len(bases) if bases else None}
            odd = [b for b in bases if _base_index(b) % 2 == 1]
            even = [b for b in bases if _base_index(b) % 2 == 0]
            rec: Dict[str, object] = {"frontier": frontier, "odd_bases": len(odd), "even_bases": len(even), "bases_without_a_vote": no_vote}
            if odd and even:
                o_odd = math.fsum(o_score[b] for b in odd) / len(odd)
                cand = []
                for tau in CASCADE_TAU:
                    acc, cost, _ = run(tau, odd)
                    cand.append((tau, 100.0 * math.fsum(acc) / len(acc), sum(cost, Fraction(0)) / len(cost)))
                ok = [c for c in cand if at_least(c[1], o_odd - CASCADE_MARGIN_POINTS)]
                if ok:
                    tau_r = min(ok, key=lambda c: (c[2], c[0]))[0]
                    rule = "cheapest tau within 10 points of Opus-medium on the odd bases"
                else:
                    tau_r = min(cand, key=lambda c: (-c[1], c[2], c[0]))[0]
                    rule = "none within 10 points: the highest odd-base accuracy"
                acc_e, cost_e, esc_e = run(tau_r, even)
                ca = {b: 100.0 * a for b, a in zip(even, acc_e)}
                cc = {b: float(c) for b, c in zip(even, cost_e)}
                oa = {b: o_score[b] for b in even}
                oc = {b: float(o_cost[b]) for b in even}                                 # type: ignore[arg-type]
                da = {b: ca[b] - oa[b] for b in even}
                dc = {b: cc[b] - oc[b] for b in even}
                name = f"cascade:{shape}:{kc}"

                def mean_of(v):
                    return lambda s: math.fsum(v[b] for b in s) / len(s)

                def m(v):
                    return math.fsum(v.values()) / len(v)
                rec.update(opus_odd_accuracy=o_odd, recommended_tau=float(tau_r), rule=rule,
                           even={"bootstrap_name": name,
                                 "cascade_accuracy": m(ca), "cascade_accuracy_ci95": _boot(even, mean_of(ca), name, draws),
                                 "cascade_mean_cost": m(cc), "cascade_mean_cost_ci95": _boot(even, mean_of(cc), name, draws),
                                 "cascade_escalation_rate": esc_e / len(even),
                                 "opus_accuracy": m(oa), "opus_accuracy_ci95": _boot(even, mean_of(oa), name, draws),
                                 "opus_mean_cost": m(oc), "opus_mean_cost_ci95": _boot(even, mean_of(oc), name, draws),
                                 "accuracy_difference": m(da), "accuracy_difference_ci95": _boot(even, mean_of(da), name, draws),
                                 "cost_difference": m(dc), "cost_difference_ci95": _boot(even, mean_of(dc), name, draws)})
            sh[str(kc)] = rec
        out[shape] = sh
    return {"label": "escalate-to-Opus cascade (offline, exploratory)", "unit": "points; USD, list price", "shapes": out}


# ---------------------------------------------------------------- tokens (9f, 9g)

def _per_base_tokens(ctx: dict, arm: str, shape: str) -> Dict[str, Tuple[Fraction, Fraction]]:
    """{base: (input, output)} BILLED tokens (C1 9f/9g: prompt_tokens; a B5-free refusal 0): for a sampled arm the puzzle's mean per
    designed sample (a missing call 0, X4, as 9b's cost), for a single-call arm the puzzle's call."""
    cell = cells(ctx).get((arm, shape))
    if cell is None:
        return {}
    cs = calls(ctx)
    out = {}
    for b, cids in cell["bases"].items():                                                # type: ignore[union-attr]
        i = sum(int(cs[c]["billed_in"]) for c in cids)                                   # type: ignore[call-overload]
        o = sum(int(cs[c]["billed_out"]) for c in cids)                                  # type: ignore[call-overload]
        d = int(cell["designed"]) if cell["how"] == "per_sample" else 1                   # type: ignore[call-overload]
        out[b] = (Fraction(i, d), Fraction(o, d))
    return out


def _family_row(ctx: dict, ks: Mapping[str, int], label: str) -> Dict[str, object]:
    """One k-sensitivity row (8b): the whole five-test family re-run with t1-t3 at the given k (as_deployed, official), through
    five_tests._family (bootstrap.run_family, B 10,000, seed 20261011, margin -10, Holm; k = 0 not run, p = 1)."""
    tk = test_ks(ctx)
    k_o = {tk[t][1]: ks[t] for t in ("t1", "t2")}
    diffs = five_tests.test_differences(list(ctx["rows"]), k_o, ks["t3"], "as_deployed", n=int(ctx["n"]))   # type: ignore[arg-type, call-overload]
    res = five_tests._family(diffs, family_draws(ctx), FAMILY_SEED)
    rows = {t: {kk: res["tests"][t].get(kk) for kk in ("n", "d", "ci95", "p", "declared", "reading")} for t in res["tests"]}   # type: ignore[index, union-attr]
    for t in ("t1", "t2", "t3"):
        rows[t]["k"] = ks[t]
    return {"label": label, "tests": rows, "family": res}


def item_9f(ctx: dict, family: bool = True) -> Dict[str, object]:
    """Note 9f. For a Haiku vote of k on a puzzle: input billed once as a 5-minute cache write and k - 1 times as a cache read, output
    in full: cached cost(k) = (in x w + (k - 1) x in x r + k x out x o) / 1,000,000, in and out the puzzle's mean BILLED Haiku-medium
    input (prompt_tokens) and output tokens per sample (C1), w / r / o read from prices.PRICES[prices.HAIKU] (cache_write_5m,
    cache_read, output). Single-call arms unchanged. The cached k: the largest k <= min(40, designed 40) (X2) with mean cached cost(k)
    over puzzles <= the comparator's mean list cost per puzzle (9b), per test t1-t3, 0 if none (C1: tests 1-3 then not run in that
    row); the family at those k as one more k-sensitivity row, "cached view (offline re-pricing)"."""
    rates = (ctx.get("_price_table") or prices.PRICES)[prices.HAIKU]                       # type: ignore[index]
    w, r, o = Fraction(rates.cache_write_5m), Fraction(rates.cache_read), Fraction(rates.output)
    out: Dict[str, object] = {"rates_per_mtok": {"cache_write_5m": str(rates.cache_write_5m), "cache_read": str(rates.cache_read),
                                                 "output": str(rates.output)}, "label": "cached view (offline re-pricing)"}
    ks: Dict[str, int] = {}
    blocked = False
    for t, (comp, shape, _) in test_ks(ctx).items():
        toks = _per_base_tokens(ctx, "haiku-med", shape)
        comp_cost, no_record = base_costs(ctx, comp, shape)
        cc = [v for v in comp_cost.values() if v is not None]
        kmax = kmax_of("haiku-med")
        if not toks or not cc:
            out[t] = {"computed": False, "reason": "no Haiku-medium or comparator rows in this shape"}
            blocked = True
            continue
        target = sum(cc, Fraction(0)) / len(cc)

        def cached(k: int, toks=toks) -> Fraction:
            tot = Fraction(0)
            for i, op in toks.values():
                tot += (i * w + (k - 1) * i * r + k * op * o) / 1_000_000
            return tot / len(toks)
        by_k = [cached(k) for k in range(1, kmax + 1)]
        kc = max((k for k in range(1, kmax + 1) if by_k[k - 1] <= target), default=0)
        ks[t] = kc
        out[t] = {"comparator": comp, "shape": shape, "comparator_mean_list_cost": float(target), "k_cap": kmax, "cached_k": kc,
                  "mean_cached_cost_by_k": [float(x) for x in by_k]}
        if kc == 0:
            out[t]["note"] = "cached k = 0: this test is not run in the cached row (C1 9f, the k = 0 rule)"   # type: ignore[index]
    if family:
        out["family_row"] = {"not_computed": "a cached k is not computed (see above)"} if blocked else \
            _family_row(ctx, ks, "cached view (offline re-pricing)")
    return out


def item_9g(ctx: dict) -> Dict[str, object]:
    """Note 9g. Per shape, k = 1..40: vote@k (item 8 curve, mean over bases, points), the mean billed input and output tokens of k
    Haiku-medium samples per puzzle (k x the per-puzzle means), beside each comparator's mean billed input and output tokens per puzzle.
    The token-matched k per test: floor(comparator mean total tokens per puzzle (the mean over puzzles) / Haiku mean total tokens per
    sample (pooled over the shape's samples, as kscript pools cost per sample; C1 9g)), total = input + output as billed, held to 1..40;
    the family at those k as one more k-sensitivity row, "token-matched"."""
    out: Dict[str, object] = {"label": "token-matched view"}
    cs = calls(ctx)
    for shape in _shapes(ctx):
        toks = _per_base_tokens(ctx, "haiku-med", shape)
        mi = sum((v[0] for v in toks.values()), Fraction(0)) / len(toks) if toks else None
        mo = sum((v[1] for v in toks.values()), Fraction(0)) / len(toks) if toks else None
        rows = []
        for k in range(1, KMAX + 1):
            pts = vote_points(ctx, "haiku-med", shape, k)
            rows.append({"k": k, "vote_at_k": (math.fsum(pts.values()) / len(pts)) if pts else None,
                         "haiku_mean_input_tokens": float(k * mi) if mi is not None else None,
                         "haiku_mean_output_tokens": float(k * mo) if mo is not None else None})
        comps = {}
        for comp in ("opus-med", "sonnet-med"):
            ct = _per_base_tokens(ctx, comp, shape)
            comps[comp] = {"mean_input_tokens": float(sum((v[0] for v in ct.values()), Fraction(0)) / len(ct)) if ct else None,
                           "mean_output_tokens": float(sum((v[1] for v in ct.values()), Fraction(0)) / len(ct)) if ct else None,
                           "n_bases": len(ct)}
        out[shape] = {"by_k": rows, "comparators": comps}
    ks: Dict[str, int] = {}
    blocked = False
    tm: Dict[str, object] = {}
    for t, (comp, shape, _) in test_ks(ctx).items():
        hcell = cells(ctx).get(("haiku-med", shape)) or {"bases": {}}
        hcids = [c for v in hcell["bases"].values() for c in v]                           # type: ignore[union-attr]
        ct = _per_base_tokens(ctx, comp, shape)
        total_h = sum(int(cs[c]["billed_in"]) + int(cs[c]["billed_out"]) for c in hcids)  # type: ignore[call-overload]
        if not hcids or not ct or total_h == 0:
            tm[t] = {"computed": False, "reason": "no billed Haiku-medium tokens or no comparator rows in this shape"}
            blocked = True
            continue
        comp_total = sum((v[0] + v[1] for v in ct.values()), Fraction(0)) / len(ct)
        pooled = Fraction(total_h, len(hcids))
        raw = math.floor(comp_total / pooled)
        k = max(1, min(KMAX, raw))
        ks[t] = k
        tm[t] = {"comparator": comp, "shape": shape, "comparator_mean_total_tokens": float(comp_total),
                 "haiku_mean_total_tokens_per_sample": float(pooled), "haiku_samples_pooled": len(hcids), "raw_floor": raw,
                 "token_matched_k": k}
    out["token_matched_k"] = tm
    out["family_row"] = {"not_computed": "a token-matched k is not computed (see token_matched_k)"} if blocked else \
        _family_row(ctx, ks, "token-matched")
    return out


# ---------------------------------------------------------------- 9h: Opus vs Sonnet

def _ratio(a: float, b: float) -> Optional[float]:
    """C4 item 3, the one ratio rule (cost, CPC, error; the same as item 1): x / 0 (x > 0) = +inf, 0 / x = 0, +inf / finite = +inf,
    finite / +inf = 0, all kept; None (dropped and counted) for 0 / 0 and +inf / +inf."""
    if math.isinf(a) and math.isinf(b):
        return None
    if math.isinf(b):
        return 0.0
    if b == 0:
        return None if a == 0 else math.inf
    return a / b


def _ovs_pair(ctx: dict, a: str, b: str, shape: str) -> Dict[str, object]:
    """C1 9h for one pair (a vs b) and shape: the paired cluster bootstrap over base puzzles (both arms' answers of a base drawn together),
    10,000 draws, seed 20261012, one name per statistic "ovs:<stat>:<a>-vs-<b>:<shape>". acc_diff = A(a) - A(b) in points; cost_ratio
    = C(a) / C(b); cpc_ratio = CPC(a) / CPC(b), each CPC +inf in a draw with no correct answer (X3); err_ratio = (1 - A(b)) / (1 - A(a)).
    Every ratio in a draw follows C4 item 3's one rule (`_ratio`): 0/0 and inf/inf are dropped and counted, everything else kept; the
    interval is the percentile over the kept draws and is never withheld. Official, as_deployed; list price (9b)."""
    sa, sb = single_scores(ctx, a, shape), single_scores(ctx, b, shape)
    ca, _ = base_costs(ctx, a, shape)
    cb, _ = base_costs(ctx, b, shape)
    bases = sorted(set(sa) & set(sb) & {x for x, v in ca.items() if v is not None} & {x for x, v in cb.items() if v is not None})
    if not bases:
        return {"n_bases": 0}
    ca_f = {x: float(ca[x]) for x in bases}                                               # type: ignore[arg-type]
    cb_f = {x: float(cb[x]) for x in bases}                                               # type: ignore[arg-type]
    draws = family_draws(ctx, OVS_DRAWS)

    def parts(s):
        m = len(s)
        Aa, Ab = math.fsum(sa[x] for x in s) / m / 100.0, math.fsum(sb[x] for x in s) / m / 100.0
        Ca, Cb = math.fsum(ca_f[x] for x in s) / m, math.fsum(cb_f[x] for x in s) / m
        Ea, Eb = math.fsum(100.0 - sa[x] for x in s) / 100.0, math.fsum(100.0 - sb[x] for x in s) / 100.0
        return Aa, Ab, Ca, Cb, Ea, Eb
    Aa, Ab, Ca, Cb, Ea, Eb = parts(bases)
    cpc = lambda C, A: C / A if A > 0 else math.inf                                       # noqa: E731
    cost_r = _ratio(Ca, Cb)
    cpc_r = _ratio(cpc(Ca, Aa), cpc(Cb, Ab)) if Aa > 0 and Ab > 0 else None
    point = {"acc_diff": 100.0 * (Aa - Ab), "cost_ratio": UNDEFINED_0_0 if cost_r is None else show(cost_r),
             "cpc_ratio": (UNDEFINED_CPC if not (Aa > 0 and Ab > 0) else UNDEFINED_0_0 if cpc_r is None else show(cpc_r)),   # C-3: x/0 = +inf
             "err_ratio": (Eb / Ea) if Ea > 0 else f"undefined ({a} has no errors)"}
    intervals: Dict[str, object] = {}
    for stat in ("acc_diff", "cost_ratio", "cpc_ratio", "err_ratio"):
        inf, dropped = [0], [0]

        def f(s, stat=stat, inf=inf, dropped=dropped):
            A1, A2, C1, C2, E1, E2 = parts(s)
            if stat == "acc_diff":
                return 100.0 * (A1 - A2)
            v = (_ratio(E2, E1) if stat == "err_ratio" else _ratio(C1, C2) if stat == "cost_ratio"
                 else _ratio(cpc(C1, A1), cpc(C2, A2)))
            if v is None:
                dropped[0] += 1                                                           # C4 item 3: 0/0 or inf/inf, dropped
            elif math.isinf(v):
                inf[0] += 1
            return v
        name = f"ovs:{stat}:{a}-vs-{b}:{shape}"
        ci = _boot(bases, f, name, draws)
        d: Dict[str, object] = {"bootstrap_name": name, "ci95": ci}
        if stat != "acc_diff":
            d.update(share_draws_infinite=inf[0] / draws, share_draws_dropped=dropped[0] / draws, draws_dropped=dropped[0])
        intervals[stat] = d
    return {"n_bases": len(bases), "point": point, "intervals": intervals}


def item_9h(ctx: dict, c9b: Optional[Mapping[str, object]] = None, c9c: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    """Note 9h and research/paper-notes/opus-vs-sonnet-exploratory.md. For m in {Opus-medium, Sonnet-medium, Opus-low} and each shape:
    A (share of puzzles right, official; as_deployed, refusals_out and truncations_out), C (9b's mean list cost per puzzle; Batch
    alongside), CPC (9c; "undefined (no correct answer)" when A = 0). Then, for the pairs opus-med vs sonnet-med and opus-low vs
    sonnet-med (C1 9h): the cost ratio, the CPC ratio, the accuracy difference in points and the error-rate ratio, each with its 95%
    paired cluster-bootstrap interval (10,000 draws, seed 20261012). Exploratory, no test."""
    c9b = c9b or item_9b(ctx)
    c9c = c9c or item_9c(ctx)
    out: Dict[str, object] = {"label": "exploratory, no test (intervals two-sided, unadjusted)"}
    for shape in _shapes(ctx):
        per: Dict[str, Dict[str, object]] = {}
        for arm in ("opus-med", "sonnet-med", "opus-low"):
            a = {}
            for view in scoring.VIEWS:
                s = single_scores(ctx, arm, shape, view)
                a[view] = (math.fsum(s.values()) / len(s) / 100.0) if s else None
            cost = c9b["arms"].get(f"{arm}:{shape}") or {}                               # type: ignore[union-attr]
            cpc = c9c["arms"].get(f"{arm}:{shape}") or {}                                 # type: ignore[union-attr]
            per[arm] = {"A": a, "C": cost.get("mean"), "C_ci95": cost.get("mean_ci95"), "C_batch": cost.get("batch_mean"),
                        "CPC": cpc.get("cpc"), "CPC_ci95": cpc.get("ci95")}
        out[shape] = {"arms": per, "pairs": {f"{a}-vs-{b}": _ovs_pair(ctx, a, b, shape) for a, b in OVS_PAIRS}}
    return out


# ---------------------------------------------------------------- 19: thinking tokens

def item_19(ctx: dict) -> Dict[str, object]:
    """Note item 19 (Fix 7). Per call: visible tokens = floor(characters of the visible reply / 3); thinking = max(0, BILLED output tokens
    - visible), so a B5-free refusal counts 0 (Edith driver review r8, C-4; as 9a and C1 9f/9g). Per arm and shape: median, p90 (statistics.quantiles(n=10, method="inclusive")[8]; "n < 2" for fewer than 2 calls, C1 19)
    and maximum of thinking tokens; thinking's share of list cost = sum(thinking x output rate) / sum(list cost) (9a). Labelled
    estimates."""
    groups: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for c in calls(ctx).values():
        groups[f"{c['arm']}:{c['shape']}"].append(c)
    out: Dict[str, object] = {}
    for key, cs in sorted(groups.items()):
        th: List[int] = []
        th_cost = Fraction(0)
        for c in cs:
            u = c["usage"]
            visible = len(str(c["answer_text"] or "")) // VISIBLE_CHARS_PER_TOKEN
            t = max(0, int(c["billed_out"]) - visible)                                     # type: ignore[call-overload]  # C-4: billed only
            th.append(t)
            th_cost += t * Fraction(prices.rates_for(str(c["model"]), u.prompt_tokens).output) / 1_000_000   # type: ignore[attr-defined]
        total = sum((Fraction(c["list"]) for c in cs), Fraction(0))                       # type: ignore[arg-type]
        out[key] = {"calls": len(th), "median": statistics.median(th) if th else None,
                    "p90": statistics.quantiles(th, n=10, method="inclusive")[8] if len(th) >= 2 else "n < 2",
                    "max": max(th) if th else None, "share_of_list_cost": float(th_cost / total) if total else None}
    return {"label": "estimates (visible tokens = characters / 3)", "arms": out}


# ---------------------------------------------------------------- 22: the run window

def _t(s: str) -> datetime:
    return datetime.fromisoformat(str(s))


def item_22(ctx: dict) -> Dict[str, object]:
    """Note item 22 (D-45; C1 22, as Friday proposed): from the ledger's first `send` of a key reserved as Batch to its last `commit` of
    any call (real time included), in hours, with the hours to the last Batch result alongside; the window.json and any D-45 extension
    with its note."""
    run_dir = ctx.get("run_dir")
    out: Dict[str, object] = {}
    wpath = Path(run_dir) / "window.json" if run_dir else None                           # type: ignore[arg-type]
    if wpath is not None and wpath.is_file():
        w = json.loads(wpath.read_text())
        out["window_json"] = {"started_utc": w.get("started_utc"), "hours_allowed": w.get("hours"), "extensions": w.get("extensions") or []}
    else:
        out["window_json"] = None
    lpath = Path(run_dir) / "ledger.jsonl" if run_dir else None                          # type: ignore[arg-type]
    if lpath is None or not lpath.is_file():
        out.update(hours=None, note="no ledger.jsonl in the run folder: the window is not computed")
        return out
    batch_keys = set()
    first_send = last_commit = last_batch_commit = None
    for ln in lpath.read_text().splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        ev = d.get("event")
        if ev == "reserve" and d.get("batch") is True:
            batch_keys.add(d["key"])
        elif ev == "send" and d.get("key") in batch_keys:
            t = _t(d["time"])
            first_send = t if first_send is None or t < first_send else first_send
        elif ev == "commit":
            t = _t(d["time"])
            last_commit = t if last_commit is None or t > last_commit else last_commit
            if d.get("key") in batch_keys:
                last_batch_commit = t if last_batch_commit is None or t > last_batch_commit else last_batch_commit
    hours = (last_commit - first_send).total_seconds() / 3600 if first_send and last_commit else None
    out.update(first_batch_submission_utc=first_send.isoformat() if first_send else None,
               last_result_utc=last_commit.isoformat() if last_commit else None, hours=hours,
               last_batch_result_utc=last_batch_commit.isoformat() if last_batch_commit else None,
               hours_to_last_batch_result=(last_batch_commit - first_send).total_seconds() / 3600 if first_send and last_batch_commit else None)
    return out


# ---------------------------------------------------------------- 23: re-pricing at later prices

def item_23(ctx: dict) -> Dict[str, object]:
    """Note item 23 (D-48 row 24; C1 23): only if the pricing page changes before publication (after Karen's dated re-check in
    facts-checked.md), item 9's costs are recomputed on the new table beside the pinned ones, labelled with its date; otherwise nothing.
    ctx["later_prices"] = {"date": ..., "table": {model: prices.Rates}, "long_prompt_table": {model: prices.Rates} (optional)}, a table of
    the same shape as prices.PRICES. Items 9a-9d and 9f are re-priced (9f without its family row or cached k, C-5); k is never
    re-priced (the tests keep k.json's k). A request over 100,000 prompt tokens uses the later long-prompt row; with none it is listed as "not re-priced (no
    long-prompt row)" and keeps its pinned-table cost (C4 item 4)."""
    lp = ctx.get("later_prices")
    if not lp:
        return {"applies": False, "pinned_table_date": prices.PRICE_TABLE_DATE,
                "note": "nothing: no later price table was given (prices unchanged before publication)"}
    table, date = lp["table"], str(lp["date"])                                            # type: ignore[index]
    missing = sorted(set(prices.PRICES) - set(table))
    if missing or not all(isinstance(v, prices.Rates) for v in table.values()):
        raise ValueError(f"the later table must have the shape of prices.PRICES (missing {missing})")
    sub = {k: v for k, v in ctx.items() if k != "_report_costs_cache"}
    sub.update(_price_table=table, _price_table_date=date, _long_price_table=lp.get("long_prompt_table"))   # type: ignore[union-attr]
    c9f = item_9f(sub, family=False)
    for t in ("t1", "t2", "t3"):                                                          # C-5: k is never re-priced, so no cached k
        if isinstance(c9f.get(t), dict):
            c9f[t] = {kk: v for kk, v in c9f[t].items() if kk not in ("cached_k", "note")}   # type: ignore[union-attr]
    items = {"item_9a": item_9a(sub), "item_9b": item_9b(sub), "item_9c": item_9c(sub), "item_9d": item_9d(sub), "item_9f": c9f}
    kept = sorted(cid for cid, c in calls(sub).items() if not c["repriced"])
    return {"applies": True, "table_date": date, "pinned_table_date": prices.PRICE_TABLE_DATE,
            "label": f"offline re-pricing at the {date} table", "k": "never re-priced: tests keep k.json's k",
            "not_repriced": {cid: NOT_REPRICED for cid in kept}, "items": items}


# ---------------------------------------------------------------- all of them

def report(ctx: dict) -> Dict[str, object]:
    """Every item above, in note order, with the questions still open."""
    c9b = item_9b(ctx)
    c9c = item_9c(ctx)
    return {"note": NOTE, "price_table_date": prices.PRICE_TABLE_DATE,
            "item_9a": item_9a(ctx), "item_9b": c9b, "item_9c": c9c, "item_9d": item_9d(ctx), "item_9e": item_9e(ctx),
            "item_9f": item_9f(ctx), "item_9g": item_9g(ctx), "item_9h": item_9h(ctx, c9b, c9c), "item_19": item_19(ctx),
            "item_22": item_22(ctx), "item_23": item_23(ctx), "open_questions": OPEN_QUESTIONS}
