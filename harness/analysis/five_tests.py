"""The five confirmatory tests from scored rows (D-39, D-68): rows in, per-base differences, the bootstrap family, the readings.

Rows are the scored-call records of the main run, one per call, with at least: `base_id`, `shape` ("24x1" | "1x24"), `setup` ("haiku-med" |
"opus-med" | "opus-low" | "sonnet-med" | "e3"), `kind` ("answered" | "refusal" | "truncated" | "unparseable"), `correct`, `cost_usd`; 24x1
rows carry `answer_key` (the parsed final answer as a canonical string, or None); E3 rows carry `step_correct` (a list of per-step booleans;
`harness.pareto.e3.e3_rows` writes them) and no `answer_key`, since nothing in test 4 reads one.
1x24 rows of the other arms carry the D-76 fields (`format_status`, `trace_key`, `final_key`, `slip_type`, `correct` = the official trace score,
`correct_final`, `correct_copy_forgiven`; `scoring.grade_1x24` writes them). (The same format as Karen's simulated datasets,
`research/fixtures/sim-main-v2/`; v1 rows are the 24x1 format and, at 1x24, the answer-only fallback, see below.)

Scores (D-76, `scoring.SCORES`): "official" (the default: at 1x24 a try is right only if all 24 step lines are right; the Haiku vote is over the
whole trace, a try whose format is not ok is a vote for nothing), "final" (secondary: the Answer state, voted as such) and "copy_forgiven"
(sensitivity: a copy-slip trace counts as the right trace, in the vote too), plus "original" (D-90's sensitivity view: the official score
under prereg-lock-2's rule, where any repeated step line fails; `correct_original`). 24x1 and E3 are the same in all four. The answer-only fallback
(D-36(5)): 1x24 rows flagged `answer_only` are scored by the final answer (`answer_key`, `correct`) in every score; it is used for ALL arms or for
none (a mix is refused by every function here that scores 1x24 rows). Format compliance (D-76: format compliance) is reported per setup and shape
(`format_report`) in the official bundle (`analyse_all_views`) and in the secondary one.

Tests (spec section 7b):
  t1 Haiku-medium vote at k_O vs Opus-medium, 24x1      t2 the same at 1x24      t3 Haiku-medium vote at k_S vs Sonnet-medium, 1x24
  t4 E3 vs Opus-medium, 1x24                            t5 Opus-low vs Sonnet-medium, 1x24
Views (D-68 F3): "as_deployed" (refusals, truncations and unparseable replies are wrong; in a vote they are votes for nothing; a Haiku puzzle with
fewer than the designed 40 rows is padded with votes for nothing), "refusals_out" (blocked calls: a refusal stop or an error that names a safety or
policy reason) and "truncations_out" (those calls are left out: a blocked or truncated single answer drops that base puzzle from the test; a blocked or
truncated Haiku sample is dropped from the vote, with k capped at what is left). An unparseable reply is wrong in every view. The vote score is the
exact expected vote@k over the k-subsets of the samples (D-33: plurality, a tie of m answers that includes the right one scores 1/m, or 0 when ties are
scored as wrong, a None is a vote for nothing). Test 4 scores E3 as the PRODUCT of its per-step accuracies (F7). `headline_match` is true for a test only if
it reads non-inferior in all three views (F3). A test whose k is 0 (Haiku costs more per sample than the comparator) is not run (D-33): it keeps its place
in the Holm family with p = 1, so the thresholds stay those of five tests.

Puzzle length (D-86). The study may run at N steps (N in 4, 6, 8, 12, 16, or the original 24). The five tests are the same at any N,
with "Nx1" in place of 24x1 and "1xN" in place of 1x24 (`tests_for(n)`; `TESTS` is `tests_for(24)`). Every function that runs the
tests takes `n`; when it is not given it is read from the rows' shapes (`steps_of`): rows of one length give that length, rows of
several lengths are refused, and no shaped rows give 24. So 24-step rows give exactly the 24-step results as before. `k_o` is keyed by
the shapes at that N ({"6x1": .., "1x6": ..} at N = 6), and `k_from_rows` returns its k under those shapes.
"""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import bootstrap, kscript, scoring, votes

DESIGNED_HAIKU_SAMPLES = 40
SCORES = scoring.SCORES
NO_RIGHT_ANSWER = "\x00no-correct-answer\x00"
STEPS = scoring.STEPS                       # the original puzzle length (24)
VIEWS = scoring.VIEWS


def tests_for(n: int = STEPS) -> Dict[str, tuple]:
    """The five tests at N steps (D-86): the same challengers, comparators and k, with "Nx1" for the pieces shape and "1xN" for the
    chain shape. `tests_for(24)` is the original table."""
    pieces, chain = scoring.pieces_shape(n), scoring.chain_shape(n)
    return {
        "t1": ("haiku-med", "opus-med", pieces, "O"),
        "t2": ("haiku-med", "opus-med", chain, "O"),
        "t3": ("haiku-med", "sonnet-med", chain, "S"),
        "t4": ("e3", "opus-med", chain, None),
        "t5": ("opus-low", "sonnet-med", chain, None),
    }


TESTS = tests_for(STEPS)


def steps_of(rows: Iterable[Mapping[str, object]], n: Optional[int] = None) -> int:
    """The puzzle length the tests run at: `n` when given; else the one length of the rows' shapes (width times depth); 24 when no row
    has a shape. Rows of several lengths raise ValueError (pass `n` to choose one)."""
    if n is not None:
        return int(n)
    found = {scoring.shape_steps(r.get("shape")) for r in rows} - {None}
    if len(found) > 1:
        raise ValueError(f"the rows hold puzzles of several lengths {sorted(found)}; pass n to say which one the tests run at")  # type: ignore[type-var]
    return int(found.pop()) if found else STEPS  # type: ignore[arg-type]


def load_rows(path: object) -> List[Dict[str, object]]:
    """Rows from a .jsonl or .jsonl.gz file."""
    p = Path(str(path))
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt") as f:  # type: ignore[call-overload]
        return [json.loads(ln) for ln in f if ln.strip()]


def _arm(rows: Iterable[Mapping[str, object]], setup: str, shape: str) -> List[Mapping[str, object]]:
    return [r for r in rows if r["setup"] == setup and r["shape"] == shape]


def _dropped(r: Mapping[str, object], view: str) -> bool:
    return scoring._dropped(dict(r), view)


def _check_answer_only(rows: Iterable[Mapping[str, object]]) -> None:
    """The answer-only fallback is used for all 1x24 arms (E3 aside) or for none (D-76: answer-only fallback; `scoring.check_answer_only`)."""
    scoring.check_answer_only(rows)


def _haiku_answers(rows: Iterable[Mapping[str, object]], shape: str, view: str, designed: int,
                   score: str = "official") -> Dict[str, Dict[str, object]]:
    """Per base puzzle: the Haiku-medium samples' vote keys under `score` (None for a vote for nothing, `scoring.vote_key`) after the view's
    drops, and the right key (the key of the samples that are right under `score`)."""
    by_base: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for r in _arm(rows, "haiku-med", shape):
        by_base[str(r["base_id"])].append(r)
    out: Dict[str, Dict[str, object]] = {}
    for base, rs in by_base.items():
        kept = [r for r in rs if not _dropped(r, view)]
        answers = [scoring.vote_key(r, score) for r in kept]
        if view == "as_deployed" and len(answers) < designed:
            answers += [None] * (designed - len(answers))              # a missing sample is a vote for nothing (D-48 row 23)
        right = {scoring.vote_key(r, score) for r in rs if scoring.row_correct(r, score)} - {None}
        if len(right) > 1:
            raise ValueError(f"{base}: samples marked correct disagree on the answer")
        out[base] = {"answers": answers, "correct": next(iter(right)) if right else NO_RIGHT_ANSWER}
    return out


def vote_scores(rows: Iterable[Mapping[str, object]], shape: str, k: int, view: str = "as_deployed", tie: str = "random",
                designed: int = DESIGNED_HAIKU_SAMPLES, detail: bool = False, score: str = "official") -> Dict[str, object]:
    """{base_id: expected vote@k accuracy in percentage points} for the Haiku-medium samples of one shape under `score` (at 1x24 officially a
    vote over whole traces). k is capped at the samples left in a base puzzle after the view's drops; a base puzzle with none left is left
    out. With detail=True each value is {"score", "tie_decided_share"}."""
    rows = list(rows)
    _check_answer_only(rows)
    out: Dict[str, object] = {}
    for base, d in _haiku_answers(rows, shape, view, designed, score).items():
        answers = d["answers"]
        if not answers:
            continue
        r = votes.vote_accuracy_at_k(answers, d["correct"], min(k, len(answers)), tie=tie)
        out[base] = {"score": 100.0 * r["acc"], "tie_decided_share": r["tie_decided_share"]} if detail else 100.0 * r["acc"]
    return out


def single_scores(rows: Iterable[Mapping[str, object]], setup: str, shape: str, view: str = "as_deployed",
                  score: str = "official") -> Dict[str, float]:
    rows = list(rows)
    _check_answer_only(rows)
    return scoring.arm_scores(_arm(rows, setup, shape), view, score)  # type: ignore[arg-type]


def e3_arm_scores(rows: Iterable[Mapping[str, object]], shape: str = "1x24", view: str = "as_deployed") -> Dict[str, float]:
    """E3 per base puzzle as the PRODUCT of its per-step accuracies (F7), in points. Every E3 row needs `step_correct`."""
    runs: Dict[str, List[Sequence[bool]]] = defaultdict(list)
    for r in _arm(rows, "e3", shape):
        if _dropped(r, view):
            continue
        if r.get("step_correct") is None:
            raise ValueError(f"{r['base_id']}: an E3 row has no step_correct list; the product estimator needs the per-step results")
        runs[str(r["base_id"])].append([bool(x) for x in r["step_correct"]])  # type: ignore[union-attr]
    return scoring.e3_scores(runs)


def test_differences(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, view: str = "as_deployed",
                     tie: str = "random", score: str = "official", n: Optional[int] = None) -> Dict[str, List[float]]:
    """Per-base differences (challenger minus comparator, points) for each of the five tests under `score`, at N steps (`n`, or read from
    the rows: `steps_of`). `k_o` maps shape -> Opus-matched k. A test whose k is 0 is returned as an empty list (it is not run)."""
    if score not in SCORES:
        raise ValueError(f"unknown score {score!r}")
    _check_answer_only(rows)
    out: Dict[str, List[float]] = {}
    for name, (chal, comp, shape, which) in tests_for(steps_of(rows, n)).items():
        if which in ("O", "S"):
            k = int(k_o[shape]) if which == "O" else int(k_s)
            if k < 1:
                out[name] = []
                continue
            c = vote_scores(rows, shape, k, view, tie=tie, score=score)
        elif chal == "e3":
            c = e3_arm_scores(rows, shape, view)
        else:
            c = single_scores(rows, chal, shape, view, score)
        out[name] = scoring.paired_differences(c, single_scores(rows, comp, shape, view, score))  # type: ignore[arg-type]
    return out


def _family(diffs: Dict[str, List[float]], B: int, seed: int) -> Dict[str, object]:
    """run_family on the tests that ran; a test that did not run keeps its Holm place with p = 1 (degenerate differences far below the margin)."""
    n = max((len(v) for v in diffs.values()), default=1) or 1
    not_run = [t for t, v in diffs.items() if not v]
    filled = {t: (v if v else [-1000.0] * n) for t, v in diffs.items()}
    res = bootstrap.run_family(filled, B=B, seed=seed)
    for t in not_run:
        res["tests"][t] = {"n": 0, "reading": "not run (k = 0: Haiku costs more per sample than the comparator)", "declared": False,
                           "d": None, "ci95": None, "p": 1.0}
    res["not_run"] = not_run
    return res


def analyse(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, view: str = "as_deployed",
            B: int = bootstrap.DRAWS, seed: int = bootstrap.SEED, tie: str = "random", score: str = "official",
            n: Optional[int] = None) -> Dict[str, object]:
    """The family result (d, 95% interval, p, Holm, the three-way reading for each test) in one view, under one score (official by default),
    at N steps (`n`, or read from the rows)."""
    res = _family(test_differences(rows, k_o, k_s, view, tie, score, n=n), B, seed)
    res["score"] = score
    return res


def analyse_all_views(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, B: int = bootstrap.DRAWS,
                      seed: int = bootstrap.SEED, score: str = "official", n: Optional[int] = None) -> Dict[str, object]:
    """All three views of one score (the official D-76 score by default), and `headline_match[t]`: true only if test t reads non-inferior in
    EVERY view (D-68 F3). Only then may the word "matches" appear in a headline; otherwise the result is "matches as deployed; driven by
    refusals or truncations"."""
    views = {v: analyse(rows, k_o, k_s, v, B, seed, score=score, n=n) for v in VIEWS}
    match = {t: all(views[v]["tests"][t]["reading"] == bootstrap.NON_INFERIOR for v in VIEWS) for t in TESTS}
    as_deployed = {t: views["as_deployed"]["tests"][t]["reading"] == bootstrap.NON_INFERIOR for t in TESTS}
    note = {t: ("matches" if match[t] else ("matches as deployed; driven by refusals or truncations" if as_deployed[t] else "does not match as deployed"))
            for t in TESTS}
    return {"score": score, "views": views, "headline_match": match, "headline_wording": note, "format_compliance": format_report(rows)}


def analyse_secondary(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, B: int = bootstrap.DRAWS,
                      seed: int = bootstrap.SEED, view: str = "as_deployed", n: Optional[int] = None) -> Dict[str, object]:
    """The non-official readings of D-76, as deployed by default: `final_answer` (secondary: scored and voted by the Answer state),
    `copy_slips_forgiven` (sensitivity: a copy-slip trace counts as the right trace, in the vote too) and `original_repeat_rule` (D-90's
    sensitivity view: the official score under prereg-lock-2's rule, where any repeated step line fails), with the per-arm rates (`rates`)
    that measure the gap: format compliance, absorption, and the absorbed and copy shares of wrong traces, and `format_compliance`
    (`format_report`)."""
    return {"final_answer": analyse(rows, k_o, k_s, view, B, seed, score="final", n=n),
            "copy_slips_forgiven": analyse(rows, k_o, k_s, view, B, seed, score="copy_forgiven", n=n),
            "original_repeat_rule": analyse(rows, k_o, k_s, view, B, seed, score="original", n=n),
            "rates": rates(rows), "format_compliance": format_report(rows)}


def rates(rows: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """Per arm at 1x24 (step-line rows): format compliance, absorption, the absorbed and copy shares of wrong traces and the three
    accuracies (`scoring.rates_1x24`)."""
    return scoring.rates_1x24(rows)


def format_report(rows: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, Dict[str, object]]]:
    """{setup: {shape: ...}}: each model's format compliance in each shape (D-76: format compliance), from the rows that carry
    `format_status` (`scoring.format_compliance`: the share of answered tries whose reply parses, the same over every try, the counts of
    each status). The denominator of `format_compliance` is the ANSWERED tries (`kind == "answered"`); tries that did not answer
    (`refusal`, `truncated`, `empty`, `unexpected_stop`, any other kind) are outside it and appear only in `format_compliance_all_tries`
    (and in `status_counts`).
    At 1x24 that is the step-line parse of every arm but E3 (or the Answer line, if the answer-only fallback is used); at 24x1 it is the
    pieces parse, when the rows carry it (`scoring.grade_24x1` writes it). E3 rows carry none and are not listed."""
    rows = list(rows)
    _check_answer_only(rows)
    out: Dict[str, Dict[str, Dict[str, object]]] = {}
    for (setup, shape), v in scoring.format_compliance(rows, by=("setup", "shape")).items():
        out.setdefault(str(setup), {})[str(shape)] = v
    return out


def tie_report(rows: Sequence[Mapping[str, object]], k_o: Mapping[str, int], k_s: int, view: str = "as_deployed",
               B: int = bootstrap.DRAWS, seed: int = bootstrap.SEED, score: str = "official", n: Optional[int] = None) -> Dict[str, object]:
    """D-33's tie sensitivity: the family with ties scored as wrong, and for each Haiku test how often a tie decides (mean over base puzzles of the
    share of k-subsets in which a tie containing the right answer decided the credit)."""
    shares: Dict[str, float] = {}
    for name, (chal, comp, shape, which) in tests_for(steps_of(rows, n)).items():
        if which not in ("O", "S"):
            continue
        k = int(k_o[shape]) if which == "O" else int(k_s)
        d = vote_scores(rows, shape, k, view, detail=True, score=score) if k >= 1 else {}
        shares[name] = sum(v["tie_decided_share"] for v in d.values()) / len(d) if d else float("nan")  # type: ignore[index]
    return {"ties_as_wrong": analyse(rows, k_o, k_s, view, B, seed, tie="wrong", score=score, n=n), "tie_decided_share": shares}


def k_from_rows(rows: Iterable[Mapping[str, object]], cap: int = kscript.CAP, designed: int = DESIGNED_HAIKU_SAMPLES,
                n: Optional[int] = None) -> Dict[str, object]:
    """The equal-money k from the scored rows (D-33, D-70): floor of (mean comparator cost per puzzle ÷ mean Haiku-medium cost per sample), per
    shape for Opus-medium and for Sonnet-medium at 1x24, all-in (every call's logged cost, failures and refusals included), capped at 40 and at
    the DESIGNED number of Haiku samples (a puzzle with fewer rows does not lower k for every puzzle; it is reported in `warnings`). A missing
    cost counts as 0 and is counted in `rows_without_cost`. k = 0 comes back as k = 0 with `h1_not_run`. At N steps (`n`, or read from
    the rows) the shapes are "Nx1" and "1xN"."""
    rows = list(rows)
    pieces, chain = scoring.pieces_shape(steps_of(rows, n)), scoring.chain_shape(steps_of(rows, n))
    warnings: List[str] = []
    missing = 0

    def cost(r: Mapping[str, object]) -> Fraction:
        nonlocal missing
        c = r.get("cost_usd")
        if c in (None, ""):
            missing += 1
            return Fraction(0)
        return Fraction(str(c))

    def mean_cost(setup: str, shape: str, per_puzzle: bool) -> Fraction:
        rs = _arm(rows, setup, shape)
        total = sum((cost(r) for r in rs), Fraction(0))
        return total / (len({r["base_id"] for r in rs}) if per_puzzle else len(rs))      # exact: no rounding before the floor (Edith b6)

    for shape in (pieces, chain):
        counts: Dict[object, int] = defaultdict(int)
        for r in _arm(rows, "haiku-med", shape):
            counts[r["base_id"]] += 1
        short = sorted(str(b) for b, n in counts.items() if n < designed)
        if short:
            warnings.append(f"{shape}: {len(short)} Haiku puzzle(s) have fewer than {designed} rows (first: {short[0]}); k uses the designed {designed}")
    out: Dict[str, object] = {"opus": {}, "sonnet": {}}
    for shape in (pieces, chain):
        h = mean_cost("haiku-med", shape, False)
        out["opus"][shape] = kscript.k_value(mean_cost("opus-med", shape, True), h, cap=cap, samples_drawn=designed)  # type: ignore[index]
    out["sonnet"][chain] = kscript.k_value(mean_cost("sonnet-med", chain, True),  # type: ignore[index]
                                          mean_cost("haiku-med", chain, False), cap=cap, samples_drawn=designed)
    out["warnings"] = warnings
    out["rows_without_cost"] = missing
    return out
