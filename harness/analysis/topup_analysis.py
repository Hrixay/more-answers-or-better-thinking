"""The top-up run's analysis (spec `research/topup-run-spec.md` at 9c007e5, Karen, Edith CLEAN: section 3 the same-model check, section 4
the definitions, section 5 what is reported; with Edith's rulings on the runner, `ops/reviews/2026-10-13-topup-spec-r1.md`). Plumbing: the
rows come from `topup_rows` (the locked scorers), every statistic from the locked functions named below; it writes one JSON file.

    python3 -m harness.analysis.topup_analysis --plan <topup-plan.json> --run <top-up run folder> --main-run <main run folder> --out <file>

It runs ONCE, after Edith's check, on the finished top-up log (spec section 7, step 6), and refuses to overwrite its output. Everything
here is EXPLORATORY: no Holm, and no verdict except Test 4 at pieces (section 5). Inputs are recorded as file names and SHA-256, never as
paths.

What it computes, in order:
0. the main run's six run-folder files (calls.jsonl, compact_table.csv, ledger.jsonl, manifest.json, runner.log, window.json) against
   the D-93 analysis stamp's SHA-256 values (`MAIN_RUN_STAMP`, copied from
   decisions/briefings/2026-10-12-analysis-stamp/analysis-stamp.txt): any mismatch, a missing file or another main run id STOPS the
   driver (`StampMismatch`; spec 4c "the stamped main-run rows", Edith code r1 T-D1). The output records the expected value beside the
   observed one, and the code identity (the git commit of the tree and whether harness/ is dirty, and the SHA-256 of the imported
   main_rows.py and of this driver's own files).
1. rows (`topup_rows.build`): the plan and the run's own copy of it, the set (deep-verified), the top-up records, the main run's rows
   (main_rows on its log, the planned list checked against its manifest), and the joins (4c: every picker puzzle to main-run Haiku-medium
   samples 1-8, every same-model puzzle to samples 1-5; a failed join stops). The run folder must hold manifest.json; its round-1 list
   is rebuilt (`topup.plan_round` on an empty log) and checked against it. The same-model check must be the spec's size (section 3:
   20 bases x 5 tries, both shapes, 200 calls), else the driver stops.
2. the same-model check (section 3): per puzzle the share right of its 5 tries (official, as deployed: `scoring.arm_scores`), top-up and
   main-run samples 1-5; d = mean over the puzzles (top-up - main) per shape and pooled; a 95% cluster bootstrap over the bases
   (`curve.cluster_bootstrap`, 2,000 draws, seed derive_seed(20261014, "same_model:<6x1|1x6|pooled>")); mean output tokens per call in
   both runs and the relative change; refusal and truncation counts in both runs; the flag (fires if the pooled interval excludes 0 and
   |d| > 10 points, or the mean output tokens move by more than 25%). A flag, not a gate. Its rows are never mixed into anything else.
3. accuracy per arm and shape (the shared cluster bootstrap, 2,000 draws, seed 20261014, names "topup:acc:<arm>:<shape|pooled>"): E2
   (the team's graded answer; plan_failed and unfinished wrong), H-pick8 (the joined sample's official score; no pick wrong) with vote@8
   (`five_tests.vote_scores` at k = 8, designed = 8: `votes.vote_accuracy_at_k`, a sample that did not answer a vote for nothing, ties at
   1/m), any@8 and the single try (samples 1-8 mean) beside it (4d), C13 (`five_tests.e3_arm_scores` at 6x1: the product over the pieces,
   F7), and the main-run comparators (E3 at 1x6, Opus-medium).
4. the comparisons (section 5): `bootstrap.paired_bca(diffs, margin=-10, B=10,000, seed=derive_seed(20261014, name))` over base puzzles,
   as deployed, d and the 95% interval: E2 - step voting ("topup:e2-e3:<shape>": main E3 at 1x6, C13 at 6x1), E2 - Opus-medium
   ("topup:e2-om:<shape>"), the picker - vote@8 / any@8 / the single try ("topup:hp8-<vote8|any8|single>:<shape>"). Each cross-window
   comparison carries the same-model flag's status.
5. Test 4 at pieces (section 5, as reporting-definitions item 11 reads tests 3 and 5 at the other shape): C13 - Opus-medium at 6x1, in
   all three views, paired_bca with seed derive_seed(20261011, "t4@6x1"), B = 10,000, margin -10, a family of one
   (`bootstrap.holm_one_sided`), the three-way reading (`bootstrap.three_way`), labelled exploratory and outside the Holm family, with the
   different-window note and the flag's status.
6. the counts (4e): aggregator changes (wrong to right, right to wrong), failed tasks, failed plans (each with the planner's kind and
   stop_reason: Edith's ruling 2), unfinished puzzles; the picker's position distribution (descriptive).
7. costs (4f; list price by `report_costs.list_cost` with each run's ledger's B5-free refusals at $0; the logged Batch cost beside):
   per puzzle E2 (planner + every helper draw + aggregator), the picker's extra cost over vote@8's 8 samples and the total, C13 (its step
   draws); mean and median per shape with report_costs' shared cluster bootstrap (`_stats`), and the cost per correct answer (item 9c,
   `report_costs._cpc`) for E2, C13 and the picker's total only (`h-pick8-total`).
8. format compliance, refusals, truncations, failures and missing items per part and shape (items 16 and 17's rules).
1a. a run cut short (the user's ruling D-106(G); spec section 5 "A run cut short" at 9c007e5; Edith's audit pass-2 ruling on P14, and
   her detail: counts only, no score, no flag, no reading): `topup_rows.completeness` counts each arm's designed, final and missing
   calls. An arm with any missing call (the Haiku team, the Haiku picker, step voting on pieces, the same-model check) reads
   NOT_COMPLETED_TOPUP ("not completed") with those counts only, everywhere it would appear: no accuracy, no cost per puzzle or CPC,
   no 4e counts or position distribution, and it enters no comparison (each such comparison keeps its place and labels and reads
   "not completed", with no n, d or interval). Test 4 at pieces gets no reading if step voting on pieces is not completed. A
   same-model check not completed gets no d, interval or flag, and its flag reads "not completed" beside every cross-window
   comparison and Test 4. The main-run comparators (vote@8, any@8, the single try, E3 at chain, Opus-medium) are not top-up arms and
   stay as they are; so do items 16 and 17 (section 8), which report the missing calls themselves.
`choices` lists every point the spec left open and the option this file implements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import bootstrap, five_tests, report_arms, report_costs, scoring, topup_rows
from .curve import cluster_bootstrap
from ..pareto import e3, prices, topup
from ..pareto.outcome import usage_from_raw

SPEC = topup_rows.SPEC
BASE_SEED = 20261014                         # section 5 and section 3
T4_SEED = bootstrap.SEED                     # 20261011: "derive_seed(20261011, 't4@6x1')" (section 5, as item 11)
T4_NAME = "t4@6x1"
B_PAIRED = bootstrap.DRAWS                   # 10,000
DRAWS = 2_000                                # the shared cluster bootstrap
MARGIN = -10.0
FLAG_D_POINTS = 10.0                         # section 3: |d| > 10 points
FLAG_TOKENS_SHARE = 0.25                     # section 3: output tokens move by more than 25%
FLAG_FIRED, FLAG_NOT_FIRED = "fired", "not fired"
EXPLORATORY = "exploratory (no Holm, no verdict)"
WINDOW_NOTE = ("this arm ran in a different window from its comparator (the top-up run's own window, after the main run's; spec "
               "section 1, Edith r6)")
NO_PAIRS = "no paired base puzzles"
# D-106(G): the label of a top-up arm not completed. It must match the top-up spec's text word for word (section 5 "A run cut short"
# at 9c007e5, the same string as Study 1b's spec section 4); set it here, in this one line.
NOT_COMPLETED_TOPUP = "not completed"

# Edith code r1 T-D1: the D-93 analysis stamp of the main run, copied from decisions/briefings/2026-10-12-analysis-stamp/analysis-stamp.txt
# ("Raw data of the main run (SHA-256 of each file)"; the same six values are in ops/spend-log.md's main-l14n6-1 row). The CLI always
# checks against these; `analyse(stamp=...)` exists for the tests' fixture main run only.
MAIN_RUN_STAMP: Dict[str, object] = {
    "source": "decisions/briefings/2026-10-12-analysis-stamp/analysis-stamp.txt",
    "run_id": "main-l14n6-1",
    "sha256": {
        "calls.jsonl": "0d04ce3870704017d79a7cd2f3603a7f124379f241f13fb3b3ce416bdd02c123",
        "compact_table.csv": "984da2841cd56f0026bb0e750968d59845d8a842af70b2aff04dcd82269df6b4",
        "ledger.jsonl": "5f175b8764dd44c1e028d9887ff88945b96489bc2e4eb368bd362ab83313957e",
        "manifest.json": "702cd7ca22da2ecd97ef7d5fe4bf8c970a92adf9de7bfeef76e5d55252de6993",
        "runner.log": "1a213c8db3f40a672cba6c18b15a56e3834b16deae059ad1a0ab83cdceacf13f",
        "window.json": "684fcddd46eeaa0c4761356469583834a5ccd6ccb2a96cd0ee1894eec6919a65",
    },
}
STAMP_FILES = ("calls.jsonl", "compact_table.csv", "ledger.jsonl", "manifest.json", "runner.log", "window.json")
# Spec section 3 (Edith, D-99): the same-model check is 20 bases x 5 tries, both shapes (200 calls). The CLI always checks this size.
SAME_MODEL_SIZE = (20, 5)


class StampMismatch(RuntimeError):
    """The main run's folder is not the stamped one (spec 4c: the D-93 stamp's hashes)."""


class SpecSizeError(ValueError):
    """The plan's same-model check is not the spec's size."""

CHOICES = {
    "main_rows_source": "The main-run comparators are rebuilt from the main run's call log by main_rows.build with the planned list of "
                        "main_rows.planned_requests (extras sl, ho, hx and D-42 on, the run's clearance) checked against its "
                        "manifest, exactly as main_analysis.analyse_run builds Study 1's rows, restricted to Haiku-medium samples 1-8, "
                        "Opus-medium and E3 (spec 4c). A missing Opus-medium try or an unfinished E3 chain is Study 1's missing row "
                        "(wrong as deployed); Study 1's analysis.json is not read.",
    "join": "The picker and the same-model joins use only FINAL main-run records: topup.main_run_replies (the runner's own check: run "
            "id, model, effort, setup, sample) and then every (item_id, sample) must give exactly one scored row; any failure stops the "
            "driver (JoinError), no per-puzzle skip (Edith's ruling 1: a pre-flight refusal of the whole run, not a quiet skip). A "
            "missing main manifest also stops it, and before any of this the main run's six files must match the D-93 stamp.",
    "same_model_missing": "A planned same-model try with no final top-up record is a missing row (counted); under D-106(G) it makes "
                          "the check 'not completed' (counts only, no d and no flag).",
    "same_model_pooled": "Pooled d is the mean over all same-model puzzles (both shapes); its cluster bootstrap resamples bases and "
                         "averages over the drawn bases' puzzles.",
    "same_model_tokens": "Mean output tokens per call (usage output_tokens as logged) over the final records that carry usage; records "
                         "without usage are left out of the mean and counted. Relative change = (top-up - main) / main; 'more than "
                         "25%' is |change| > 0.25; a main mean of 0 makes the token condition not computable (reported as None).",
    "same_model_refusals_truncations": "Refusals are the rows the refusals_out view drops (a refusal stop, or a block: table.is_block); "
                                       "truncations the rows the truncations_out view drops (kind truncated or stop_reason max_tokens).",
    "flag_rule": "'The pooled 95% interval excludes 0' is lo > 0 or hi < 0; '|d| > 10' is strict. The token condition alone fires it too.",
    "e2_unfinished": "An E2 puzzle the run did not finish (no final aggregator and not plan_failed) is a missing row in topup_rows "
                     "(wrong, counted); under D-106(G) it makes the whole Haiku team arm 'not completed' (counts only), so that row is "
                     "never scored.",
    "cut_short": "D-106(G) (spec section 5 at 9c007e5; Edith's pass-2 ruling on P14 and her detail): per arm, designed / final / missing "
                 "calls from the final records (a refusal, truncation or unparseable answer is final). Picker: one call per puzzle; "
                 "same-model check: one per planned try. The Haiku team and step voting on pieces are adaptive (lead by 2, cap 9): "
                 "their missing calls are the ones the runner's own logic still plans when the driver runs (topup.e2_puzzle's next "
                 "requests for a puzzle neither done nor plan_failed; e3.plan_round on topup.c13_steps), designed = final + missing (a "
                 "lower bound). Any missing call: the arm reads 'not completed' (NOT_COMPLETED_TOPUP) with its counts only, in "
                 "accuracy, costs (per puzzle and CPC; the run's totals by tag stay, as spend), the 4e counts and the picker's "
                 "positions; every section 5 comparison that uses it keeps its place and labels and reads 'not completed' with no n, "
                 "d or interval; Test 4 at pieces has no view and no reading if C13 is not completed. A same-model check not completed "
                 "has no d, interval, tokens or flag; the flag status beside every cross-window comparison and Test 4 reads 'not "
                 "completed'. The main-run comparators are not top-up arms and stay. Items 16 and 17 (section 8) stay: they report "
                 "the missing calls themselves.",
    "plan_failed": "A planner that is refused, truncated or otherwise does not answer, or whose reply has no exact Task 1..6, is "
                   "plan_failed (Edith's ruling 2): graded by the locked scorer with kind 'plan_failed' (wrong), listed with the "
                   "planner's kind and stop_reason.",
    "pieces_no_result": "At pieces a task with no result stays at its own place only, because pieces are independent (Edith's ruling 4; "
                        "the runner's e2_puzzle). At chain the later tasks are never started.",
    "aggregator_change": "The final answer 'differs from the helpers' chain' when the aggregator's graded whole answer (the step-line "
                         "trace at 1x6, the pieces at 6x1) is not the helpers' results in order; an unreadable aggregator answer or a "
                         "helpers' chain with a '(no result)' place counts as differing (sub-counted). The helpers' chain is right when "
                         "every result equals the key the scorer uses. Counted over puzzles with a final aggregator.",
    "c13_rows": "C13 rows: e3.e3_rows on the runner's own step list (topup.c13_steps: piece s from its printed start, "
                "ledger.step_call(p, s, 1); Edith's spec note 1), relabelled 6x1 (e3_rows writes 1x1 for depth 1), scored as the product "
                "over the 6 pieces (F7, five_tests.e3_arm_scores; Edith's ruling 7). An unfinished pieces puzzle is a missing row as "
                "main_rows._e3_missing_rows makes one: done pieces keep their voted result, open pieces wrong.",
    "picker_pick_of_no_reply": "A pick of a sample that did not answer (shown as '(no reply)') is that sample's own row, which is wrong.",
    "picker_score_points": "The picker's per-puzzle score is 100 or 0 points (one try); any@8 likewise; vote@8 via five_tests.vote_scores "
                           "(its right key from the samples marked right; none right gives 0).",
    "comparisons_output": "Section 5's comparisons report n, d, the 95% interval, the seed and its name only (no p-value, no reading): "
                          "'Report d and the 95% interval'. As deployed only. Unpaired bases are counted.",
    "seed_names": "<shape> in the seed names is written '1x6' / '6x1'; the picker's <ref> is 'vote8', 'any8' or 'single'.",
    "t4_views": "Test 4 at pieces runs in all three views (as item 11 does for tests 3 and 5), each a family of one (declared iff p <= "
                "0.025), labelled report_arms.OUTSIDE_HOLM_LABEL.",
    "cross_window": "Cross-window comparisons (flag status attached): E2 - E3 at 1x6, E2 - Opus-medium, every picker comparison (its "
                    "comparators are main-run samples) and Test 4 at pieces. E2 - C13 at 6x1 is within the top-up window.",
    "accuracy_names": "Accuracy intervals: curve.cluster_bootstrap over base puzzles, seed 20261014, names 'topup:acc:<arm>:<shape|pooled>' "
                      "(arms e2, h-pick8, vote8, any8, single8, c13, main-e3, main-om); pooled = each base's mean over its two shapes "
                      "(Study 1b's form pooling).",
    "costs": "List cost per call by report_costs.list_cost (B5-free refusals at $0, each run's own ledger.jsonl read for free_by_rule); a "
             "designed call with no record costs $0 (X4). Mean / median per shape with report_costs._stats (report_costs' own seed "
             "20261012, names 'cost_mean|cost_median:<arm>:<shape>'), CPC with report_costs._cpc (names 'cpc:<arm>:<shape>'). The "
             "picker: arm 'h-pick8-extra' (the picker call alone, the headline) and 'h-pick8-total' (its 8 main-run samples plus the "
             "picker) beside it; CPC on h-pick8-total only (the extra alone is not the cost of an answer). Pooled cost per answer is each base's mean over its two shapes (point only). The Batch "
             "figure is the logged cost_usd, None if any call of the arm logged none.",
    "compliance": "Items 16 and 17's rules per part and shape: refusals by category, truncations (stop_reason max_tokens), failures of "
                  "kind empty / unexpected_stop / error, and missing items, as count / designed with Wilson 95% (report_arms._rate) and "
                  "their list cost. Designed: the same-model tries, one picker, planner per puzzle, one aggregator per puzzle with a "
                  "plan; E2 helper draws and C13 draws over the calls made (as item 16 does for E3). Item 17's 5% format flag on the "
                  "graded rows (E2 aggregators, the same-model check); the picker's unreadable picks and the planner's plan_failed "
                  "among answered calls beside it.",
    "manifest_check": "The run folder must hold manifest.json with an item_set_sha256, and it must equal round 1 rebuilt by "
                      "topup.plan_round on an empty log; otherwise the driver refuses.",
    "main_run_stamp": "The main run's six run-folder files are compared with the D-93 analysis stamp's SHA-256 values (constants copied "
                      "from decisions/briefings/2026-10-12-analysis-stamp/analysis-stamp.txt), and the plan's main_run.run_id must be the "
                      "stamp's run; any mismatch or missing file stops the driver before anything is read. Expected and observed are "
                      "recorded side by side, with the code identity (git commit, harness/ dirty, SHA-256 of main_rows.py and the driver).",
    "same_model_size": "The plan's same-model check must be the spec's 20 bases x 5 tries (both shapes, 200 planned calls); the driver "
                       "stops otherwise.",
    "e2_task_detail": "Each E2 task row carries its agreed result (`answer`: the voted state key, None for no result or not reached) "
                      "and each draw's vote key (`votes`: draw number, the record's kind, e3.record_vote's key or None).",
    "plan_copy": "The run folder must hold the runner's copy of its plan (topup_plan.json) and it must equal the plan given; otherwise "
                 "the driver refuses.",
}


# ---------------------------------------------------------------- small helpers

def _sha(path: Path) -> Optional[str]:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _mean(xs: Iterable[float]) -> Optional[float]:
    xs = list(xs)
    return math.fsum(xs) / len(xs) if xs else None


def _shapes(items: Sequence[Mapping[str, object]]) -> List[str]:
    n = {int(it["width"]) * int(it["depth"]) for it in items}                                         # type: ignore[call-overload]
    (steps,) = n
    return [scoring.pieces_shape(steps), scoring.chain_shape(steps)]


def _boot(per_base: Mapping[str, float], name: str, draws: int, seed: int = BASE_SEED) -> List[Optional[float]]:
    """curve.cluster_bootstrap (percentile 95%) of the mean over drawn base puzzles."""
    bases = sorted(per_base)
    if not bases:
        return [None, None]
    return list(cluster_bootstrap([bases], lambda s: math.fsum(per_base[b] for b in s) / len(s), name, draws=draws, seed=seed))


def _acc(per_base: Mapping[str, float], name: str, draws: int) -> Dict[str, object]:
    return {"mean": _mean(per_base.values()), "n_base": len(per_base), "unit": "points", "ci95": _boot(per_base, name, draws),
            "bootstrap_name": name, "seed": BASE_SEED}


def _pooled(per_shape: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
    """Each base's mean over its shapes (a base needs every shape)."""
    vals = list(per_shape.values())
    common = set(vals[0]).intersection(*[set(v) for v in vals[1:]]) if vals else set()
    return {b: math.fsum(v[b] for v in vals) / len(vals) for b in sorted(common)}


def _points(rows: Iterable[Mapping[str, object]]) -> Dict[str, float]:
    return {str(r["base_id"]): 100.0 if r.get("correct") else 0.0 for r in rows}


# ---------------------------------------------------------------- 2. the same-model check

def same_model(built: Mapping[str, object], draws: int) -> Dict[str, object]:
    top_rows: List[Mapping[str, object]] = list(built["same_model"])                                    # type: ignore[call-overload]
    joined: Mapping[str, List[Mapping[str, object]]] = built["same_model_joined"]                       # type: ignore[assignment]
    main_rows_ = [r for rs in joined.values() for r in rs]
    shapes = _shapes(built["items"])                                                                    # type: ignore[arg-type]
    diffs: Dict[str, Dict[str, float]] = {}
    out: Dict[str, object] = {"label": "a flag, not a gate; these answers are never mixed into Study 1",
                              "tries_per_puzzle": int(built["plan"]["same_model"]["tries"]),           # type: ignore[index, call-overload]
                              "bases": int(built["plan"]["same_model"]["bases"])}                      # type: ignore[index, call-overload]
    for shape in shapes:
        t = scoring.arm_scores([dict(r) for r in top_rows if r["shape"] == shape], "as_deployed", "official")
        m = scoring.arm_scores([dict(r) for r in main_rows_ if r["shape"] == shape], "as_deployed", "official")
        if set(t) != set(m):
            raise topup_rows.JoinError(f"same-model check at {shape}: top-up and main-run puzzles differ")
        diffs[shape] = {b: t[b] - m[b] for b in sorted(t)}
        name = f"same_model:{shape}"
        out[shape] = {"top_up_accuracy": _mean(t.values()), "main_accuracy": _mean(m.values()), "n_puzzles": len(t),
                      "d": _mean(diffs[shape].values()), "ci95": _boot(diffs[shape], name, draws), "bootstrap_name": name,
                      "seed": BASE_SEED}
    per_base: Dict[str, List[float]] = defaultdict(list)
    for shape in shapes:
        for b, v in diffs[shape].items():
            per_base[b].append(v)
    bases = sorted(per_base)
    stat = (lambda s: math.fsum(math.fsum(per_base[b]) for b in s) / sum(len(per_base[b]) for b in s))
    ci = list(cluster_bootstrap([bases], stat, "same_model:pooled", draws=draws, seed=BASE_SEED)) if bases else [None, None]
    d = _mean([v for b in bases for v in per_base[b]])
    out["pooled"] = {"d": d, "ci95": ci, "n_puzzles": sum(len(v) for v in per_base.values()), "n_base": len(bases),
                     "bootstrap_name": "same_model:pooled", "seed": BASE_SEED, "unit": "points (top-up - main)"}
    # output tokens, refusals and truncations, both runs
    finals: Mapping[str, Mapping[str, object]] = built["finals"]                                        # type: ignore[assignment]
    main_recs = {str(r["custom_id"]): r for r in built["main_records"]}                                 # type: ignore[union-attr]

    def tokens(recs: Sequence[Optional[Mapping[str, object]]]) -> Dict[str, object]:
        with_usage = [r for r in recs if r is not None and r.get("usage_raw") is not None]
        outs = [usage_from_raw(dict(r["usage_raw"])).output_tokens for r in with_usage]                # type: ignore[arg-type]
        return {"mean_output_tokens": _mean(outs), "calls_with_usage": len(with_usage), "calls_without_usage": len(recs) - len(with_usage)}
    top_tok = tokens([finals.get(str(r["custom_id"])) for r in top_rows])
    main_tok = tokens([main_recs.get(str(r["custom_id"])) for r in main_rows_])
    a, b = top_tok["mean_output_tokens"], main_tok["mean_output_tokens"]
    change = (a - b) / b if a is not None and b else None                                               # type: ignore[operator]
    out["output_tokens"] = {"top_up": top_tok, "main": main_tok, "relative_change": change}

    def counts(rows: Sequence[Mapping[str, object]]) -> Dict[str, int]:
        return {"calls": len(rows), "refusals": sum(1 for r in rows if scoring._dropped(dict(r), "refusals_out")),
                "truncations": sum(1 for r in rows if scoring._dropped(dict(r), "truncations_out")),
                "missing": sum(1 for r in rows if r.get("kind") == "missing")}
    out["refusals_truncations"] = {"top_up": counts(top_rows), "main": counts(main_rows_)}
    lo, hi = ci
    acc_cond = bool(lo is not None and hi is not None and d is not None and (lo > 0 or hi < 0) and abs(d) > FLAG_D_POINTS)
    tok_cond = None if change is None else abs(change) > FLAG_TOKENS_SHARE
    fires = acc_cond or bool(tok_cond)
    out["flag"] = {"status": FLAG_FIRED if fires else FLAG_NOT_FIRED, "fires": fires, "accuracy_condition": acc_cond,
                   "tokens_condition": tok_cond,
                   "rule": "fires if the pooled 95% interval excludes 0 and |d| > 10 points, or mean output tokens move by more than 25%; "
                           "a flag, not a gate"}
    return out


# ---------------------------------------------------------------- 3. per-base scores and accuracy

def scores(built: Mapping[str, object], not_completed: Sequence[str] = ()) -> Dict[str, Dict[str, Dict[str, float]]]:
    """{arm: {shape: {base: points}}}, as deployed, official. An arm in `not_completed` (D-106(G)) is never scored."""
    shapes = _shapes(built["items"])                                                                    # type: ignore[arg-type]
    pieces, chain = shapes
    main = list(built["main_rows"])                                                                     # type: ignore[call-overload]
    out: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(dict)
    joined: Mapping[str, List[Mapping[str, object]]] = built.get("joined_hm") or {}                    # type: ignore[assignment]
    hm8 = [dict(r) for rs in joined.values() for r in rs]
    for shape in shapes:
        if "e2" in built and "e2" not in not_completed:
            out["e2"][shape] = five_tests.single_scores(list(built["e2"]), topup_rows.E2_SETUP, shape)   # type: ignore[call-overload]
        if "picker" in built:
            if "h-pick8" not in not_completed:
                out["h-pick8"][shape] = _points(r for r in built["picker"] if r["shape"] == shape)      # type: ignore[union-attr]
            out["vote8"][shape] = five_tests.vote_scores(hm8, shape, topup_rows.PICK_SAMPLES, "as_deployed",  # type: ignore[assignment]
                                                         designed=topup_rows.PICK_SAMPLES)
            right: Dict[str, bool] = defaultdict(bool)
            for r in hm8:
                if r["shape"] == shape:
                    right[str(r["base_id"])] |= scoring.row_correct(r, "official")
            out["any8"][shape] = {b: 100.0 if v else 0.0 for b, v in right.items()}
            out["single8"][shape] = five_tests.single_scores(hm8, "haiku-med", shape)
        out["main-om"][shape] = five_tests.single_scores(main, "opus-med", shape)
    out["main-e3"][chain] = five_tests.e3_arm_scores(main, chain)
    if "c13" in built and "c13" not in not_completed:
        out["c13"][pieces] = five_tests.e3_arm_scores(list(built["c13"]), pieces)                     # type: ignore[call-overload]
    return dict(out)


def not_completed_entry(g: Mapping[str, object]) -> Dict[str, object]:
    """D-106(G): an arm not completed, as counts only (designed, final, missing; puzzles unfinished for E2 and C13)."""
    return {"reading": NOT_COMPLETED_TOPUP, **{k: g[k] for k in ("designed", "final", "missing", "puzzles", "puzzles_unfinished")
                                              if k in g}}


def not_completed_arms(gate: Mapping[str, Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """{arm name: its counts-only entry} for the arms the gate holds (D-106(G))."""
    return {str(g["arm"]): not_completed_entry(g) for g in gate.values() if not g["completed"]}


def accuracy(sc: Mapping[str, Mapping[str, Mapping[str, float]]], draws: int,
             held: Optional[Mapping[str, Mapping[str, object]]] = None) -> Dict[str, object]:
    """Accuracy per arm and shape; an arm in `held` (not completed, D-106(G)) is its counts-only entry."""
    out: Dict[str, object] = {arm: dict(e) for arm, e in (held or {}).items()}
    for arm, per in sc.items():
        d: Dict[str, object] = {shape: _acc(v, f"topup:acc:{arm}:{shape}", draws) for shape, v in per.items()}
        if len(per) == 2:
            d["pooled"] = _acc(_pooled(per), f"topup:acc:{arm}:pooled", draws)
        out[arm] = d
    out["label"] = "accuracy in points (official, as deployed); the main-run arms are the comparators, rebuilt from the main run's log"
    return out


# ---------------------------------------------------------------- 4. section 5's comparisons, 5. Test 4 at pieces

def _paired(c: Mapping[str, float], o: Mapping[str, float], name: str, B: int) -> Dict[str, object]:
    diffs = scoring.paired_differences(dict(c), dict(o))
    unpaired = len(set(c) ^ set(o))
    if not diffs:
        return {"n": 0, "reading": NO_PAIRS, "seed_name": name, "unpaired_bases": unpaired}
    r = bootstrap.paired_bca(diffs, margin=MARGIN, B=B, seed=bootstrap.derive_seed(BASE_SEED, name))
    return {"n": r["n"], "d": r["d"], "ci95": list(r["ci95"]), "B": B, "seed": r["seed"], "seed_name": name,  # type: ignore[call-overload]
            "seed_base": BASE_SEED, "unpaired_bases": unpaired, "unit": "points"}


def comparisons(sc: Mapping[str, Mapping[str, Mapping[str, float]]], flag: Optional[Mapping[str, object]], B: int,
                shapes: Sequence[str], held: Sequence[str] = ()) -> Dict[str, object]:
    """Section 5's comparisons. One that uses an arm in `held` (not completed, D-106(G)) keeps its place and labels and reads
    NOT_COMPLETED_TOPUP, with no n, d or interval."""
    pieces, chain = shapes
    status = None if flag is None else flag["status"]
    out: Dict[str, object] = {"label": EXPLORATORY, "method": "bootstrap.paired_bca(diffs, margin=-10, B=10,000, "
                              "seed=derive_seed(20261014, name)) over base puzzles, as deployed; d and the 95% interval"}

    def add(key: str, challenger: str, comparator: str, shape: str, cross: bool) -> None:
        name = f"topup:{key}:{shape}"
        stopped = [a for a in (challenger, comparator) if a in held]
        c, o = sc.get(challenger, {}).get(shape), sc.get(comparator, {}).get(shape)
        if stopped and all(a in held or sc.get(a, {}).get(shape) is not None for a in (challenger, comparator)):
            res: Dict[str, object] = {"reading": NOT_COMPLETED_TOPUP, "not_completed_arms": stopped, "seed_name": name}
        elif c is None or o is None:
            return
        else:
            res = _paired(c, o, name, B)
        res.update(challenger=challenger, comparator=comparator, shape=shape, cross_window=cross)
        if cross:
            res["same_model_flag"] = status
        out[name] = res
    for shape in shapes:
        add("e2-e3", "e2", "main-e3" if shape == chain else "c13", shape, shape == chain)
        add("e2-om", "e2", "main-om", shape, True)
        for ref, arm in (("vote8", "vote8"), ("any8", "any8"), ("single", "single8")):
            add(f"hp8-{ref}", "h-pick8", arm, shape, True)
    return out


def test4_pieces(built: Mapping[str, object], flag: Optional[Mapping[str, object]], B: int,
                 c13_held: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    """Test 4 at pieces in all three views; if step voting on pieces is not completed (`c13_held`, its counts-only entry; D-106(G)), no
    view and no reading: it reads NOT_COMPLETED_TOPUP with C13's counts."""
    pieces = _shapes(built["items"])[0]                                                                 # type: ignore[arg-type]
    out: Dict[str, object] = {"label": report_arms.OUTSIDE_HOLM_LABEL, "exploratory": True, "outside_holm_family": True,
                              "methods_note": WINDOW_NOTE, "same_model_flag": None if flag is None else flag["status"],
                              "seed_name": T4_NAME, "seed_base": T4_SEED, "margin": MARGIN, "B": B,
                              "challenger": "c13 (step voting on pieces, top-up)", "comparator": "opus-med (main run)", "shape": pieces}
    if "c13" not in built:
        out["reading"] = "not computed: C13 is not in the plan's parts"
        return out
    if c13_held is not None:
        out.update(reading=NOT_COMPLETED_TOPUP, c13=dict(c13_held))
        return out
    for view in scoring.VIEWS:
        c = five_tests.e3_arm_scores(list(built["c13"]), pieces, view)                                 # type: ignore[call-overload]
        o = five_tests.single_scores(list(built["main_rows"]), "opus-med", pieces, view)              # type: ignore[call-overload]
        diffs = scoring.paired_differences(c, o)
        if not diffs:
            out[view] = {"n": 0, "reading": NO_PAIRS}
            continue
        r = bootstrap.paired_bca(diffs, margin=MARGIN, B=B, seed=bootstrap.derive_seed(T4_SEED, T4_NAME))
        declared = bootstrap.holm_one_sided({T4_NAME: float(r["p_one_sided"])})[T4_NAME]            # type: ignore[arg-type]
        out[view] = {"n": r["n"], "d": r["d"], "ci95": list(r["ci95"]), "p": r["p_one_sided"], "declared": declared,  # type: ignore[call-overload]
                     "reading": bootstrap.three_way(declared, r["ci95"], MARGIN), "seed": r["seed"],  # type: ignore[arg-type]
                     "label": report_arms.OUTSIDE_HOLM_LABEL}
    return out


# ---------------------------------------------------------------- 6. counts

def e2_counts(rows: Sequence[Mapping[str, object]], shapes: Sequence[str]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for shape in shapes:
        rs = [r for r in rows if r["shape"] == shape]
        done = [r for r in rs if r["stage"] == "done"]
        changed = [r for r in done if r.get("answer_key_whole") is None or r["answer_key_whole"] != r.get("helper_results_key")]
        failed = [r for r in rs if r["stage"] == topup_rows.PLAN_FAILED]
        out[shape] = {
            "puzzles": len(rs),
            "aggregator_changes": {"changed": len(changed),
                                   "wrong_chain_turned_right": sum(1 for r in changed if not r["helpers_right"] and r["correct"]),
                                   "right_chain_turned_wrong": sum(1 for r in changed if r["helpers_right"] and not r["correct"]),
                                   "of_which_aggregator_unreadable": sum(1 for r in changed if r.get("answer_key_whole") is None),
                                   "of_which_helpers_had_no_result": sum(1 for r in changed if r.get("helper_results_key") is None),
                                   "over_puzzles_with_a_final_aggregator": len(done)},
            "failed_tasks": {"puzzles": sum(1 for r in rs if r["tasks_no_result"]),
                             "tasks": sum(len(r["tasks_no_result"]) for r in rs)},                     # type: ignore[arg-type]
            "failed_plans": {"puzzles": len(failed),
                             "list": [{"item_id": r["item_id"], "planner_kind": r["planner_kind"],
                                       "planner_stop_reason": r["planner_stop_reason"]} for r in failed]},
            "unfinished_puzzles": sum(1 for r in rs if r.get("kind") == "missing"),
            "helper_draws": sum(int(r["helper_draws"]) for r in rs)}                                   # type: ignore[call-overload]
    return out


def picker_positions(rows: Sequence[Mapping[str, object]], shapes: Sequence[str]) -> Dict[str, object]:
    out: Dict[str, object] = {"label": "descriptive: how often each of samples 1-8 is picked; position effects are not studied"}
    for shape in list(shapes) + ["pooled"]:
        rs = [r for r in rows if shape == "pooled" or r["shape"] == shape]
        c = Counter(r["pick"] for r in rs)
        out[shape] = {**{str(k): c.get(k, 0) for k in range(1, topup_rows.PICK_SAMPLES + 1)}, "none": c.get(None, 0), "puzzles": len(rs)}
    return out


# ---------------------------------------------------------------- 7. costs

def _call_costs(records: Iterable[Mapping[str, object]], run_dir: Path) -> Dict[str, Dict[str, object]]:
    free, ledger_read = report_costs._ledger_free_ids(run_dir)
    out: Dict[str, Dict[str, object]] = {}
    for rec in records:
        logged = rec.get("cost_usd")
        out[str(rec["custom_id"])] = {"list": report_costs.list_cost(rec, free), "batch": None if logged in (None, "") else Decimal(str(logged)),
                                      "tag": str((rec.get("meta") or {}).get("setup")), "ledger_read": ledger_read}  # type: ignore[union-attr]
    return out


def _sum(cids: Iterable[str], costs: Mapping[str, Mapping[str, object]], field: str) -> Optional[Fraction]:
    tot = Fraction(0)
    for cid in cids:
        v = costs[cid][field]
        if v is None:
            return None
        tot += Fraction(v)                                                                              # type: ignore[arg-type]
    return tot


def _cost_arm(arm: str, shape: str, per_base: Mapping[str, Sequence[str]], top: Mapping[str, Mapping[str, object]],
              extra: Mapping[str, Optional[Fraction]], extra_batch: Mapping[str, Optional[Fraction]], score: Mapping[str, float],
              draws: int, cpc: bool = True) -> Dict[str, object]:
    lst = {b: (_sum(c, top, "list") or Fraction(0)) + (extra.get(b) or Fraction(0)) for b, c in per_base.items()}
    bat: Dict[str, Optional[Fraction]] = {}
    for b, c in per_base.items():
        s, e = _sum(c, top, "batch"), extra_batch.get(b, Fraction(0))
        bat[b] = None if s is None or e is None else s + e
    d = dict(report_costs._stats(lst, arm, shape, draws), unit="USD per puzzle, list price (item 9a)")
    known = [v for v in bat.values() if v is not None]
    d["batch_mean"] = float(sum(known, Fraction(0)) / len(known)) if known and len(known) == len(bat) else None
    d["cpc"] = report_costs._cpc(lst, score, f"cpc:{arm}:{shape}", draws) if lst and cpc else None
    d["_per_base"] = lst
    return d


def costs(built: Mapping[str, object], sc: Mapping[str, Mapping[str, Mapping[str, float]]], run_dir: Path, main_dir: Path,
          draws: int, held: Optional[Mapping[str, Mapping[str, object]]] = None) -> Dict[str, object]:
    """Section 4f. An arm in `held` (not completed, D-106(G)) has no cost per puzzle or CPC: its counts-only entry (the picker's under
    both h-pick8-extra and h-pick8-total). The run's totals by tag (spend) are always given."""
    held = held or {}
    top = _call_costs(built["records"], run_dir)                                                        # type: ignore[arg-type]
    main = _call_costs(built["main_records"], main_dir)                                                # type: ignore[arg-type]
    shapes = _shapes(built["items"])                                                                    # type: ignore[arg-type]
    out: Dict[str, object] = {"label": "list price (item 9a; B5-free refusals at $0); the logged Batch cost beside",
                              "price_table_date": prices.PRICE_TABLE_DATE}
    arms: Dict[str, Dict[str, Dict[str, object]]] = defaultdict(dict)
    for shape in shapes:
        if "e2" in built and "e2" not in held:
            per = {str(r["base_id"]): list(r["custom_ids"]) for r in built["e2"] if r["shape"] == shape}  # type: ignore[union-attr]
            arms["e2"][shape] = _cost_arm("e2", shape, per, top, {}, {}, sc["e2"][shape], draws)
        if "picker" in built and "h-pick8" not in held:
            prs = [r for r in built["picker"] if r["shape"] == shape]                                 # type: ignore[union-attr]
            per = {str(r["base_id"]): [str(r["custom_id"])] if str(r["custom_id"]) in top else [] for r in prs}
            arms["h-pick8-extra"][shape] = _cost_arm("h-pick8-extra", shape, per, top, {}, {}, sc["h-pick8"][shape], draws,
                                                     cpc=False)          # Edith code r1: CPC on h-pick8-total only
            samples = {str(r["base_id"]): _sum(r["sample_custom_ids"], main, "list") for r in prs}   # type: ignore[arg-type]
            samples_b = {str(r["base_id"]): _sum(r["sample_custom_ids"], main, "batch") for r in prs}  # type: ignore[arg-type]
            arms["h-pick8-total"][shape] = _cost_arm("h-pick8-total", shape, per, top, samples, samples_b, sc["h-pick8"][shape], draws)
    if "c13" in built and "c13" not in held:
        pieces = shapes[0]
        per = {str(r["base_id"]): list(r["custom_ids"]) for r in built["c13"]}                        # type: ignore[union-attr]
        arms["c13"][pieces] = _cost_arm("c13", pieces, per, top, {}, {}, sc["c13"][pieces], draws)
    for arm, per_shape in arms.items():
        if len(per_shape) == 2:
            pooled = _pooled({s: {b: float(v) for b, v in d["_per_base"].items()} for s, d in per_shape.items()})  # type: ignore[union-attr]
            per_shape["pooled"] = {"mean": _mean(pooled.values()), "n_bases": len(pooled), "unit": "USD per puzzle (each base's mean over its shapes)"}
        for d in per_shape.values():
            d.pop("_per_base", None)
    out["per_puzzle"] = dict(arms)
    for arm, e in held.items():
        for name in (("h-pick8-extra", "h-pick8-total") if arm == "h-pick8" else (arm,)):
            out["per_puzzle"][name] = dict(e)                                                           # type: ignore[index]
    out["picker_note"] = ("h-pick8-extra is the picker call alone: the extra cost over vote@8's 8 samples (the headline); h-pick8-total "
                          "adds those 8 main-run samples; cost per correct answer is given for h-pick8-total only")
    by_tag: Dict[str, Dict[str, object]] = {}
    for c in top.values():
        d = by_tag.setdefault(str(c["tag"]), {"calls": 0, "list_usd": Decimal(0), "batch_usd_logged": Decimal(0), "batch_cost_missing": 0})
        d["calls"] += 1                                                                                 # type: ignore[operator]
        d["list_usd"] += c["list"]                                                                      # type: ignore[operator]
        if c["batch"] is None:
            d["batch_cost_missing"] += 1                                                                # type: ignore[operator]
        else:
            d["batch_usd_logged"] += c["batch"]                                                         # type: ignore[operator]
    out["run_totals_by_tag"] = {t: {k: (str(v) if isinstance(v, Decimal) else v) for k, v in d.items()} for t, d in sorted(by_tag.items())}
    out["ledger_read_for_free_by_rule"] = {"top_up": report_costs._ledger_free_ids(run_dir)[1], "main": report_costs._ledger_free_ids(main_dir)[1]}
    return out


# ---------------------------------------------------------------- 8. compliance

def _rates(rs: Sequence[Mapping[str, object]], designed: int, top: Mapping[str, Mapping[str, object]]) -> Dict[str, object]:
    def usd(xs: Iterable[Mapping[str, object]]) -> str:
        return str(sum((top[str(x["custom_id"])]["list"] for x in xs if str(x.get("custom_id")) in top), Decimal(0)))  # type: ignore[misc]
    cats: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for r in rs:
        if r.get("kind") == "refusal":
            cats[str(r.get("refusal_category"))].append(r)
    trunc = [r for r in rs if r.get("stop_reason") == "max_tokens"]
    return {"designed_calls": designed, "kinds": dict(sorted(Counter(str(r.get("kind")) for r in rs).items())),
            "refusals_by_category": {c: dict(report_arms._rate(len(v), designed), list_cost_usd=usd(v)) for c, v in sorted(cats.items())},
            "truncations": dict(report_arms._rate(len(trunc), designed), list_cost_usd=usd(trunc)),
            "failures_by_kind": {kd: dict(report_arms._rate(len(v), designed), list_cost_usd=usd(v)) for kd in report_arms.FAILURE_KINDS
                                 if (v := [r for r in rs if r.get("kind") == kd])},
            "missing": report_arms._rate(sum(1 for r in rs if r.get("kind") == "missing"), designed)}


def compliance(built: Mapping[str, object], run_dir: Path) -> Dict[str, object]:
    top = _call_costs(built["records"], run_dir)                                                        # type: ignore[arg-type]
    finals: Mapping[str, Mapping[str, object]] = built["finals"]                                        # type: ignore[assignment]
    items = built["items"]
    shapes = _shapes(items)                                                                             # type: ignore[arg-type]
    shape_of = {str(it["id"]): f"{it['width']}x{it['depth']}" for it in items}                         # type: ignore[union-attr]
    tp = topup.team_prompts()
    lines_of = {str(it["id"]): int(it["params"]["lines"]) for it in items}                             # type: ignore[union-attr, index]
    out: Dict[str, object] = {"label": "items 16 and 17's rules (count / designed with Wilson 95%, list cost)"}
    rates: Dict[str, object] = {}
    by_tag: Dict[tuple, List[Mapping[str, object]]] = defaultdict(list)
    for r in finals.values():
        meta = r.get("meta") or {}
        by_tag[(str(meta.get("setup")), shape_of[str(meta.get("item_id"))])].append(r)                # type: ignore[union-attr]
    for shape in shapes:
        if "same_model" in built:
            rs = [r for r in built["same_model"] if r["shape"] == shape]                              # type: ignore[union-attr]
            rates[f"same_model {shape}"] = _rates(rs, len(rs), top)
        if "picker" in built:
            rs = [r for r in built["picker"] if r["shape"] == shape]                                  # type: ignore[union-attr]
            d = _rates(rs, len(rs), top)
            answered = [r for r in rs if r["kind"] == "answered"]
            bad = sum(1 for r in answered if r["pick"] is None)
            d["unreadable_pick_among_answered"] = {"count": bad, "answered": len(answered),
                                                   "above_5_percent": (bad * 100 > 5 * len(answered)) if answered else None}
            rates[f"h_pick8 {shape}"] = d
        if "e2" in built:
            e2r = [r for r in built["e2"] if r["shape"] == shape]                                     # type: ignore[union-attr]
            pl = by_tag.get((topup.TAG_PLANNER, shape), [])
            planned_ids = {f"{r['item_id']}-{topup.TAG_PLANNER}-01" for r in e2r}
            pl_rows = list(pl) + [{"custom_id": c, "kind": "missing"} for c in sorted(planned_ids - {str(x["custom_id"]) for x in pl})]
            d = _rates(pl_rows, len(e2r), top)
            ans = [r for r in pl if r.get("kind") == "answered"]
            n_items = {str(it["id"]): int(it["width"]) * int(it["depth"]) for it in items}             # type: ignore[union-attr, call-overload]
            bad = sum(1 for r in ans if tp.parse_plan(str(r.get("answer_text") or ""), n_items[str(r["meta"]["item_id"])]) is None)  # type: ignore[index]
            d["plan_failed_among_answered"] = {"count": bad, "answered": len(ans),
                                               "above_5_percent": (bad * 100 > 5 * len(ans)) if ans else None}
            rates[f"e2_planner {shape}"] = d
            hl = by_tag.get((topup.TAG_HELPER, shape), [])
            d = _rates(hl, len(hl), top)
            d["label"] = "over the helper calls actually made (no designed count, as item 16 does for E3)"
            d["unreadable_votes"] = sum(1 for r in hl if e3.record_vote(r, lines_of[str(r["meta"]["item_id"])]) is None)  # type: ignore[index]
            rates[f"e2_helpers {shape}"] = d
            agg = [r for r in e2r if r["stage"] != topup_rows.PLAN_FAILED]
            rates[f"e2_aggregator {shape}"] = _rates(agg, len(agg), top)
    if "c13" in built:
        pieces = shapes[0]
        es = by_tag.get((topup.TAG_C13, pieces), [])
        d = _rates(es, len(es), top)
        d["label"] = "over the C13 calls actually made (no designed count, as item 16 does for E3)"
        rows = list(built["c13"])                                                                       # type: ignore[call-overload]
        d["missing_puzzles"] = dict(report_arms._rate(sum(1 for r in rows if r.get("kind") == "missing"), len(rows)),
                                    denominator="C13 pieces puzzles")
        rates[f"c13 {pieces}"] = d
    out["rates"] = rates
    graded = list(built.get("e2") or []) + list(built.get("same_model") or [])                         # type: ignore[call-overload]
    out["item_17_flags"] = report_arms.item_17({"rows": graded, "other": []})["flags"]
    return out


# ---------------------------------------------------------------- inputs

def manifest_check(built: Mapping[str, object], main_dir: Path, run_dir: Path) -> Dict[str, object]:
    from ..pareto.manifest import item_set_hash
    mpath = Path(run_dir) / "manifest.json"
    if not mpath.is_file():
        raise ValueError(f"{Path(run_dir).name} has no manifest.json: not a finished top-up run folder (Edith code r1)")
    m = json.loads(mpath.read_text())
    if not m.get("item_set_sha256"):
        raise ValueError(f"{Path(run_dir).name}/manifest.json has no item_set_sha256: round 1 cannot be checked")
    plan, man, items = dict(built["plan"]), dict(built["man"]), list(built["items"])                   # type: ignore[call-overload]
    replies = (topup.main_run_replies(main_dir, items, plan["main_run"]["run_id"], plan["main_run"]["setup"])
               if "h_pick8" in plan["parts"] else None)
    first = topup.plan_round(topup.Context(plan, man, items, replies), [])
    if m["item_set_sha256"] != item_set_hash(first) or int(m.get("n_items", -1)) != len(first):
        raise ValueError("the run manifest's round-1 list does not match round 1 rebuilt from the plan (wrong plan or run?)")
    return {"checked": True, "round_1_calls": len(first)}


def _files(folder: Path, names: Sequence[str]) -> Dict[str, Optional[str]]:
    return {f"{n}_sha256": _sha(Path(folder) / n) for n in names}


def stamp_check(main_dir: Path, plan: Mapping[str, object], stamp: Mapping[str, object]) -> Dict[str, object]:
    """Edith code r1 T-D1: every one of the six main-run files must have the stamp's SHA-256, and the plan's main run must be the
    stamp's run. Returns expected beside observed; raises StampMismatch (nothing else is read) on any difference or missing file."""
    want: Mapping[str, str] = stamp["sha256"]                                                           # type: ignore[assignment]
    if tuple(sorted(want)) != tuple(sorted(STAMP_FILES)):
        raise StampMismatch(f"the stamp must name exactly {list(STAMP_FILES)}")
    run_id = (plan.get("main_run") or {}).get("run_id")                                                  # type: ignore[union-attr]
    files = {n: {"expected": want[n], "observed": _sha(Path(main_dir) / n)} for n in STAMP_FILES}
    for d in files.values():
        d["match"] = d["observed"] == d["expected"]
    bad = [n for n, d in files.items() if not d["match"]]
    if run_id != stamp["run_id"]:
        raise StampMismatch(f"the plan's main run is {run_id!r}, the stamp's is {stamp['run_id']!r}")
    if bad:
        raise StampMismatch(f"{Path(main_dir).name}: {bad} do not match the D-93 stamp ({stamp['source']}); the driver reads only the "
                            "stamped main run (spec 4c). Expected / observed: "
                            + "; ".join(f"{n} {files[n]['expected'][:12]}... / {(files[n]['observed'] or 'missing')[:12]}" for n in bad))
    return {"source": stamp["source"], "run_id": stamp["run_id"], "files": files, "all_match": True}


def code_identity() -> Dict[str, object]:
    """The tree's git commit (and whether harness/ is dirty: manifest.git_state), and the SHA-256 of the imported main_rows.py and of
    the driver's own files, so the analysis output names the code that made it."""
    from ..pareto.manifest import git_state
    from . import main_rows
    try:
        g: Dict[str, object] = dict(git_state())
    except Exception as e:                                                                              # no git: say so
        g = {"commit": None, "dirty": None, "error": type(e).__name__}
    mods = {"main_rows.py": main_rows, "topup_rows.py": topup_rows, "topup_analysis.py": sys.modules[__name__], "topup.py": topup}
    return {"git": {"commit": g.get("commit") or None, "harness_dirty": g.get("dirty"), **({"error": g["error"]} if "error" in g else {})},
            "sha256": {n: _sha(Path(m.__file__)) for n, m in mods.items()}}                            # type: ignore[arg-type]


def same_model_size_check(plan: Mapping[str, object], built: Mapping[str, object], size: Sequence[int]) -> Dict[str, object]:
    """Spec section 3: bases x tries as `size`, both shapes; the converter's rows must be bases x 2 x tries."""
    if "same_model" not in plan["parts"]:                                                               # type: ignore[operator]
        return {"checked": False, "reason": "same_model is not in the plan's parts"}
    bases, tries = int(size[0]), int(size[1])
    sm = plan["same_model"]
    got = (int(sm["bases"]), int(sm["tries"]))                                                          # type: ignore[index, call-overload]
    n = len(built["same_model"])                                                                        # type: ignore[arg-type]
    if got != (bases, tries) or n != bases * 2 * tries:
        raise SpecSizeError(f"the same-model check is {got[0]} bases x {got[1]} tries ({n} rows), not the spec's {bases} x {tries} "
                            f"({bases * 2 * tries} rows, section 3)")
    return {"checked": True, "bases": bases, "tries": tries, "rows": n}


# ---------------------------------------------------------------- the run

def analyse(plan_path: Path, run_dir: Path, main_dir: Path, B: Optional[int] = None, draws: Optional[int] = None,
            extras: Sequence[str] = topup_rows.MAIN_EXTRAS, loader=None, stamp: Optional[Mapping[str, object]] = None,
            same_model_size: Optional[Sequence[int]] = None) -> Dict[str, object]:
    """Every step of the module text, in order. `B`, `draws`, `stamp` and `same_model_size` are for tests only (None: 10,000, 2,000,
    MAIN_RUN_STAMP and SAME_MODEL_SIZE; the CLI never passes them)."""
    Bv = int(B) if B is not None else B_PAIRED
    dv = int(draws) if draws is not None else DRAWS
    run_dir, main_dir = Path(run_dir), Path(main_dir)
    plan = json.loads(Path(plan_path).read_text())
    stamped = stamp_check(main_dir, plan, stamp if stamp is not None else MAIN_RUN_STAMP)   # first: nothing is read from an unstamped run
    built = topup_rows.build(plan, run_dir, main_dir, extras, loader=loader)
    mcheck = manifest_check(built, main_dir, run_dir)
    size = same_model_size_check(built["plan"], built, same_model_size if same_model_size is not None else SAME_MODEL_SIZE)  # type: ignore[arg-type]
    shapes = _shapes(built["items"])                                                                    # type: ignore[arg-type]
    gate = topup_rows.completeness(built)                                                               # D-106(G)
    held = not_completed_arms(gate)
    if "same_model" not in built:
        sm = None
    elif topup_rows.SAME_MODEL_SETUP in held:
        sm = dict(held[topup_rows.SAME_MODEL_SETUP], flag={"status": NOT_COMPLETED_TOPUP},
                  label="a flag, not a gate; not completed (D-106(G)): counts only, no d, interval or flag")
    else:
        sm = same_model(built, dv)
    flag = None if sm is None else sm["flag"]
    sc = scores(built, tuple(held))
    arm_held = {a: e for a, e in held.items() if a != topup_rows.SAME_MODEL_SETUP}
    res: Dict[str, object] = {
        "spec": SPEC, "label": EXPLORATORY,
        "inputs": {"plan": Path(plan_path).name, "plan_sha256": _sha(plan_path),
                   "run": _files(run_dir, ("calls.jsonl", "topup_plan.json", "manifest.json", "ledger.jsonl", "compact_table.csv")),
                   "main_run": dict(_files(main_dir, ("calls.jsonl", "manifest.json", "ledger.jsonl")), extras=list(extras)),
                   "set": {"set_id": built["man"]["set_id"], "items_sha256": built["man"].get("items_sha256")},  # type: ignore[index, union-attr]
                   "team_prompts_sha256": topup.TEAM_PROMPTS_SHA256, "run_manifest_check": mcheck,
                   "main_run_stamp": stamped, "same_model_size_check": size},
        "code": code_identity(),
        "constants": {"seed_base": BASE_SEED, "t4_seed_base": T4_SEED, "B": Bv, "draws": dv, "margin": MARGIN,
                      "flag_d_points": FLAG_D_POINTS, "flag_tokens_share": FLAG_TOKENS_SHARE},
        "records": {"top_up_final": len(built["records"]),                                              # type: ignore[arg-type]
                    "by_tag": dict(sorted(Counter(str((r.get("meta") or {}).get("setup")) for r in built["records"]).items())),  # type: ignore[union-attr]
                    "main_rows_used": len(built["main_rows"]), "main_missing_rows": len(built["main_missing"])},  # type: ignore[arg-type]
        "completeness": {"label": NOT_COMPLETED_TOPUP + " (D-106(G)): an arm with a designed call that has no final record; counts only",
                         "arms": gate, "not_completed": sorted(p for p, g in gate.items() if not g["completed"])},
        "same_model_check": sm if sm is not None else {"computed": False, "reason": "same_model is not in the plan's parts"},
        "accuracy": accuracy(sc, dv, arm_held),
        "comparisons": comparisons(sc, flag, Bv, shapes, tuple(arm_held)),
        "test4_pieces": test4_pieces(built, flag, Bv, arm_held.get(topup_rows.C13_ARM)),
        "e2_counts": (None if "e2" not in built else dict(arm_held["e2"]) if "e2" in arm_held
                      else e2_counts(list(built["e2"]), shapes)),                                       # type: ignore[call-overload]
        "picker_positions": (None if "picker" not in built else dict(arm_held["h-pick8"]) if "h-pick8" in arm_held
                             else picker_positions(list(built["picker"]), shapes)),                     # type: ignore[call-overload]
        "costs": costs(built, sc, run_dir, main_dir, dv, arm_held),
        "format_refusals_truncations_missing": compliance(built, run_dir),
        "choices": CHOICES}
    return res


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True, help="the top-up plan (data/plans/topup-plan.json)")
    ap.add_argument("--run", type=Path, required=True, help="the top-up run folder (calls.jsonl, topup_plan.json, manifest.json)")
    ap.add_argument("--main-run", type=Path, required=True, help="the main run's folder (calls.jsonl, manifest.json)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--main-extras", default=",".join(topup_rows.MAIN_EXTRAS),
                    help="the extras the main run was cleared with (main-l14n6-1: sl,ho,hx)")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out.name} exists: the driver runs once")
    try:                                     # always the stamp's values and the spec's size: no override from the command line
        res = analyse(a.plan, a.run, a.main_run, extras=tuple(x for x in a.main_extras.split(",") if x))
    except (StampMismatch, SpecSizeError, topup_rows.JoinError) as e:
        print(f"REFUSED: {e}")
        return 2
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {a.out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
