"""Scoring views, the D-76 trace score and the slip analysis for the ledger (rulings D-39, D-67, D-68, D-76; Karen's definitions in
`research/pilot-plan-ledger.md` and `research/fixtures/sim-main-v2/README.md`).

No model calls. Everything here reads rows that are already graded and, for grading and the slip analysis, the printed lines of a reply.

Puzzle length (D-86). The study may run at N steps, N in 4, 6, 8, 12, 16 or 24. The text below says "1x24" and "24x1" for the
24-step shapes; everything holds the same way for one chain of N steps ("1xN", `is_chain_shape`) and N one-step pieces ("Nx1",
`is_pieces_shape`): the step count of a try comes from its key (`grade_1x24` reads `len(key_states)`, `grade_24x1` reads
`len(answer)`), and a row is a trace row by its shape's form, not by the literal "1x24". `grade_chain`, `grade_pieces` and
`rates_chain` are the same functions under names that do not say 24.

The three scores (D-76). On the 1x24 shape (step-line prompt, every arm but E3):
- `official`: a try is right only if its reply parses under the fixed rules (`trace_parse`, status ok; ok includes the Answer line
  being equal to line 24) AND its 24 step lines equal the key's states. Anything else is wrong; in a vote it is a vote for nothing
  when the status is not ok, and a vote for its own trace otherwise. The vote key is the whole trace (`trace_key`);
- `final` (secondary): the Answer state is right, whatever the step lines say; the vote key is the Answer state (`final_key`). Its
  excess over the official score is the measured absorption: tries whose final answer is right but whose trace is wrong;
- `copy_forgiven` (sensitivity): status ok and the trace is right or a COPY SLIP: it differs from the key at exactly one line, and the
  line after it is right (so the wrong state was not carried forward; a last line that differs is not a copy slip). In the vote a
  copy-slip trace counts for the right trace.
24x1, E3 (product of per-step accuracies) and answer-only rows (the D-36(5) fallback prompt without step lines, flagged `answer_only`,
scored by the final answer for every arm) keep `correct` / `answer_key` in all three scores. The fallback is used for every 1x24 arm
but E3 or for none (D-76: answer-only fallback): `check_answer_only` refuses a mix, and every set-level scorer here (`arm_scores`,
`format_compliance`, `rates_1x24`) calls it. The `answer_only` flag is strict: True, False, None or missing (the last two mean False);
anything else (the string "False", 0, 1) raises ValueError (`answer_only_flag`).
Rows on the 1x24 step-line prompt carry `format_status`, `trace_key`, `final_key`, `slip_type`, `correct` (official), `correct_final`
and `correct_copy_forgiven`, as `grade_1x24` writes them (and as Karen's v2 fixtures hold them).

Scoring views (D-68 F3). An arm's score on a base puzzle is its accuracy in percentage points under one of the scores:
- `as_deployed` (primary): refusals, truncations and unparseable replies count as wrong;
- `refusals_out`: the blocked calls are left out of the average (a base puzzle with none left is left out);
- `truncations_out`: the same for calls cut off at max_tokens.
`paired_differences` pairs two arms by base puzzle. E3 is the PRODUCT of its per-step accuracies on correct inputs, which is exactly the chance
that a chain of independent step calls gets every step right (Edith, F7); `all_step_lines_right` scores a reply by its printed step lines
(the official D-76 score at 1x24).

Slips (the fairness check). PRIMARY, the local-slip table: each step's rule plus house rule is applied to the model's OWN previous balances (the
given start in a 24x1 piece; the model's own line for the step before in a 1x24 chain, the key's start for step 1), so a wrong state carried
forward is not counted again. SENSITIVITY, the first-slip view: a piece, or the chain steps up to and including the first wrong one, each checked
from the key's states. Blame, in order: house rule missed, house rule misapplied (both HOUSE slips: they count toward the house index only),
decoy confusion (counts toward the step's kind and gets its own row), then a slip of the step's own kind. T / G is decided by the step's own kind
(T: repick2, repeat_fixed, sweep; G: two_clause, compare_move, avg_donors, rank_move, count_move); the house rule is analysed puzzle-wide.
A try is `unplaceable` and left out of every table (the plan's "Fairness check", item 4) when its step lines are missing or unreadable, or when
every step is right but the Answer line is wrong. 1x24: a step line missing, repeated, misnumbered or breaking the value rules; or a failure
only on the Answer line (`no_answer`, its value rules, `answer_mismatch`) with no slip in the 24 step lines. A try whose step lines are
readable and hold a slip is placed whatever its Answer line says (Edith F25-1), although it stays wrong in the official score. 24x1: a
missing piece or a piece that breaks the value rules. The parse status is kept with the reason (`status`), so the unplaceable tries can be
counted by reason.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..pareto.table import is_block
from ..taskgen import ledger, ledger_check
from . import trace_parse

T_KINDS = ("repick2", "repeat_fixed", "sweep")
G_KINDS = ("two_clause", "compare_move", "avg_donors", "rank_move", "count_move")
VIEWS = ("as_deployed", "refusals_out", "truncations_out")
SCORES = ("official", "final", "copy_forgiven", "original")   # "original": the official score under prereg-lock-2's repeat rule (D-90)
TRACE_SHAPE = "1x24"                              # the 24-step chain shape; any 1xN chain is scored the same way (`is_chain_shape`)
STEPS = trace_parse.STEPS                         # the original puzzle length (24); D-86 also allows N in 4, 6, 8, 12, 16
RIGHT_TRACE = "\x00the right trace\x00"          # the copy-forgiven vote key of a right or copy-slip trace (never a real key)
_SHAPE_RE = re.compile(r"^(\d+)x(\d+)$")


# ---------------------------------------------------------------- shapes at any N (D-86)

def shape_dims(shape: object) -> Optional[Tuple[int, int]]:
    """(width, depth) of a shape written "WxD" ("1x6" gives (1, 6)), or None when it is not written that way."""
    m = _SHAPE_RE.match(str(shape)) if shape is not None else None
    return (int(m.group(1)), int(m.group(2))) if m else None


def is_chain_shape(shape: object) -> bool:
    """One chain of several steps: "1xN" with N above 1 (the 1x24 shape and its shorter forms). These are scored by their trace."""
    d = shape_dims(shape)
    return d is not None and d[0] == 1 and d[1] > 1


def is_pieces_shape(shape: object) -> bool:
    """Several one-step pieces: "Nx1" with N above 1 (the 24x1 shape and its shorter forms). These are scored piece by piece."""
    d = shape_dims(shape)
    return d is not None and d[1] == 1 and d[0] > 1


def chain_shape(n: int) -> str:
    """The chain shape at N steps: "1xN" ("1x24" at 24)."""
    return f"1x{int(n)}"


def pieces_shape(n: int) -> str:
    """The pieces shape at N steps: "Nx1" ("24x1" at 24)."""
    return f"{int(n)}x1"


def shape_steps(shape: object) -> Optional[int]:
    """How many steps a puzzle of this shape has (width times depth), or None for a shape not written "WxD"."""
    d = shape_dims(shape)
    return None if d is None else d[0] * d[1]


# ---------------------------------------------------------------- scoring views

def _dropped(row: Dict[str, object], view: str) -> bool:
    if view == "refusals_out":
        return row.get("stop_reason") == "refusal" or is_block(row)           # a refusal stop, or an error that names a safety or policy reason
    if view == "truncations_out":
        return row.get("kind") == "truncated" or row.get("stop_reason") == "max_tokens"
    if view == "as_deployed":
        return False
    raise ValueError(f"unknown view {view!r}")


def arm_scores(rows: Iterable[Dict[str, object]], view: str = "as_deployed", score: str = "official") -> Dict[str, float]:
    """{base_id: accuracy in percentage points} for ONE arm (one setup in one shape) under one of the three scores (`row_correct`). Each
    row holds `base_id`, `correct` (and, on the 1x24 step-line prompt, the D-76 fields) and `kind` / `stop_reason` for the views. A mix
    of answer-only and step-line 1x24 rows is refused (`check_answer_only`)."""
    rows = list(rows)
    check_answer_only(rows)
    kept: Dict[str, List[bool]] = defaultdict(list)
    for r in rows:
        if _dropped(r, view):
            continue
        kept[str(r["base_id"])].append(row_correct(r, score))
    return {b: 100.0 * sum(v) / len(v) for b, v in kept.items() if v}


# ---------------------------------------------------------------- the D-76 trace score

def state_key(state: Sequence[int]) -> str:
    """The canonical text of one state: its integers joined by commas (`[0950, 3]` and `(950,3)` give "950,3")."""
    return ",".join(str(int(v)) for v in state)


def trace_key(states: Sequence[Sequence[int]]) -> str:
    """The canonical key of a whole trace: the state keys joined by "|". Two traces vote together only if every state is equal."""
    return "|".join(state_key(s) for s in states)


def copy_slip_line(states: Sequence[Sequence[int]], key_states: Sequence[Sequence[int]]) -> Optional[int]:
    """The step (1-based) of a COPY SLIP, or None: the trace differs from the key at exactly one line and the line after it is right
    (every other line equal implies the lines before and after are right; the last line has no line after it, so it never qualifies)."""
    if len(states) != len(key_states):
        return None
    diff = [k for k, (a, b) in enumerate(zip(states, key_states), 1) if tuple(a) != tuple(b)]
    return diff[0] if len(diff) == 1 and diff[0] < len(key_states) else None


def slip_type(states: Sequence[Sequence[int]], key_states: Sequence[Sequence[int]]) -> str:
    """"none" (the trace is right), "copy" (`copy_slip_line`), "absorbed" (wrong elsewhere but the last state is right) or "real"."""
    if [tuple(s) for s in states] == [tuple(s) for s in key_states]:
        return "none"
    if copy_slip_line(states, key_states) is not None:
        return "copy"
    return "absorbed" if tuple(states[-1]) == tuple(key_states[-1]) else "real"


def grade_1x24(reply: Optional[str], key_states: Sequence[Sequence[int]], line_count: int, kind: str = "answered",
               answer_only: bool = False, repeats: str = trace_parse.REPEATS) -> Dict[str, object]:
    """The D-76 row fields for one 1x24 try: format_status, trace_key, final_key, slip_type, copy_line, correct (official), correct_final,
    correct_copy_forgiven, answer_only. A call that did not answer (`kind` not "answered") is not parsed: its status is its kind and every
    score is False. With `answer_only` (the D-36(5) fallback prompt, no step lines) the reply is read for its Answer line only and every
    score is the final answer (`answer_key` is set, as on 24x1 rows). `answer_only` must be True or False (`answer_only_flag`).
    D-90 (Deviation 2): the row is graded under `repeats` (the official rule by default: a step line repeated with the identical state
    is read once) and ALSO under the original rule of prereg-lock-2 (any repeat fails): `format_status_original` and `correct_original`
    hold that reading, the named sensitivity view "original" (`row_correct(row, "original")`). `repeats_rule` records the rule used."""
    answer_only = answer_only_flag(answer_only)
    key_states = [tuple(s) for s in key_states]
    final = key_states[-1]
    out: Dict[str, object] = {"format_status": kind, "trace_key": None, "final_key": None, "slip_type": None, "copy_line": None,
                              "correct": False, "correct_final": False, "correct_copy_forgiven": False, "answer_only": answer_only,
                              "repeats_rule": repeats, "format_status_original": kind, "correct_original": False}
    if kind != "answered":
        if answer_only:
            out["answer_key"] = None
        return out
    if answer_only:
        status, ans = trace_parse.parse_final(reply or "", line_count)
        right = ans is not None and tuple(ans) == final
        out.update(format_status=status, final_key=None if ans is None else state_key(ans), answer_key=None if ans is None else state_key(ans),
                   correct=right, correct_final=right, correct_copy_forgiven=right, format_status_original=status, correct_original=right)
        return out
    tp = trace_parse.parse_trace(reply or "", line_count, len(key_states), repeats=repeats)
    out["format_status"] = tp.status
    out["final_key"] = None if tp.answer is None else state_key(tp.answer)
    out["correct_final"] = tp.answer is not None and tuple(tp.answer) == final
    if tp.ok:
        st = tp.states  # type: ignore[assignment]
        out["trace_key"] = trace_key(st)  # type: ignore[arg-type]
        out["slip_type"] = slip_type(st, key_states)  # type: ignore[arg-type]
        out["copy_line"] = copy_slip_line(st, key_states)  # type: ignore[arg-type]
        out["correct"] = out["slip_type"] == "none"
        out["correct_copy_forgiven"] = out["slip_type"] in ("none", "copy")
    strict = tp if repeats == trace_parse.REPEATS_STRICT else trace_parse.parse_trace(reply or "", line_count, len(key_states),
                                                                                   repeats=trace_parse.REPEATS_STRICT)
    out["format_status_original"] = strict.status
    out["correct_original"] = bool(out["correct"]) and strict.ok                  # the strict reading is ok only where the official one is
    return out


def grade_24x1(reply: Optional[str], answer: Sequence[Sequence[int]], line_count: int, kind: str = "answered") -> Dict[str, object]:
    """A 24x1 try: format_status (`trace_parse.parse_pieces`), answer_key (all pieces, only when the status is ok), correct (every piece
    right) and pieces_right (per-piece credit, D-23: entries that pass the value rules and equal the key)."""
    if kind != "answered":
        return {"format_status": kind, "answer_key": None, "correct": False, "pieces_right": 0}
    pp = trace_parse.parse_pieces(reply or "", len(answer), line_count)
    right = sum(1 for i, a in enumerate(answer, 1) if pp.entries.get(i) == tuple(a))
    return {"format_status": pp.status, "answer_key": trace_key([pp.entries[i] for i in range(1, len(answer) + 1)]) if pp.ok else None,
            "correct": pp.ok and right == len(answer), "pieces_right": right}


def answer_only_flag(value: object) -> bool:
    """The `answer_only` flag read strictly: True or False as given, None (or a missing field) as False; anything else (the string
    "False", 0, 1, ...) raises ValueError, so a flag written as text is never read as True."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    raise ValueError(f"answer_only must be True, False or None, not {value!r}")


def is_trace_row(row: Mapping[str, object]) -> bool:
    """A row scored by its trace under D-76: a chain shape (1x24, or 1xN at any N, `is_chain_shape`), not E3, not the answer-only
    fallback prompt."""
    return is_chain_shape(row.get("shape")) and row.get("setup") != "e3" and not answer_only_flag(row.get("answer_only"))


def check_answer_only(rows: Iterable[Mapping[str, object]]) -> None:
    """The answer-only fallback is used for all 1x24 arms (E3 aside) or for none (D-76: answer-only fallback): a mix raises ValueError.
    So does an `answer_only` flag that is not True, False or None, on any row."""
    rows = list(rows)
    for r in rows:
        answer_only_flag(r.get("answer_only"))
    flags = {answer_only_flag(r.get("answer_only")) for r in rows if is_chain_shape(r.get("shape")) and r.get("setup") != "e3"}
    if len(flags) > 1:
        raise ValueError("some 1x24 rows are answer-only and some are not: the answer-only fallback is scored for ALL arms or for none")


def _need_fields(row: Mapping[str, object]) -> None:
    if "format_status" not in row:
        raise ValueError(f"{row.get('base_id')}: a 1x24 step-line row has no D-76 fields (format_status ...); grade it with grade_1x24, or "
                         f"flag it answer_only if it came from the answer-only prompt")


def row_correct(row: Mapping[str, object], score: str = "official") -> bool:
    """Whether one try is right under `score` ("official", "final", "copy_forgiven" or "original"). "original" is the official score
    under prereg-lock-2's repeat rule (D-90's sensitivity view, `correct_original`); a row with no `correct_original` field was graded
    before D-90, under that same rule, so it reads its `correct`. Rows that are not trace rows use `correct`. This
    reads ONE row, so it cannot see an answer-only / step-line mix: that check is set-level (`check_answer_only`, called by
    `arm_scores`, `format_compliance` and `rates_1x24`)."""
    if score not in SCORES:
        raise ValueError(f"unknown score {score!r}")
    if not is_trace_row(row):
        return bool(row.get("correct"))
    _need_fields(row)
    if score == "official":
        right = bool(row.get("correct"))
        if right and row.get("format_status") != "ok":
            raise ValueError(f"{row.get('base_id')}: a row marked correct has format status {row.get('format_status')!r}")
        return right
    if score == "original":
        return bool(row.get("correct_original", row.get("correct")))
    return bool(row.get("correct_final" if score == "final" else "correct_copy_forgiven"))


def vote_key(row: Mapping[str, object], score: str = "official") -> Optional[str]:
    """What one try votes for under `score`, or None (a vote for nothing): no answer (kind not "answered"); on a trace row, official and
    copy-forgiven: a format that is not ok. Official votes the whole trace; final votes the Answer state; copy-forgiven votes RIGHT_TRACE
    for a right or copy-slip trace and the trace otherwise. Rows that are not trace rows vote their `answer_key`."""
    if score not in SCORES:
        raise ValueError(f"unknown score {score!r}")
    if row.get("kind") != "answered":
        return None
    if not is_trace_row(row):
        return row.get("answer_key")  # type: ignore[return-value]
    _need_fields(row)
    if score == "final":
        return row.get("final_key")  # type: ignore[return-value]
    if row.get("format_status") != "ok":
        return None
    if score == "original" and row.get("format_status_original", "ok") != "ok":
        return None                                                    # under the original rule a repeated step line is a vote for nothing
    if score == "copy_forgiven" and row.get("correct_copy_forgiven"):
        return RIGHT_TRACE
    return row.get("trace_key")  # type: ignore[return-value]


def format_compliance(rows: Iterable[Mapping[str, object]], by: Sequence[str] = ("setup",)) -> Dict[Tuple[object, ...], Dict[str, object]]:
    """Per group (`by` fields, default the setup; D-76: format compliance). `format_compliance` is the share of ANSWERED tries (`kind ==
    "answered"`) whose reply parses (format_status "ok"): that is its denominator. Tries that did not answer (`refusal`, `truncated`,
    `empty`, `unexpected_stop`, any kind other than "answered") are outside it; they appear only in `format_compliance_all_tries` (ok over
    every try, a non-answer counting as not ok) and in the counts of each status (`status_counts`). Rows without a `format_status` are
    skipped. A mix of answer-only and step-line 1x24 rows is refused (`check_answer_only`)."""
    rows = list(rows)
    check_answer_only(rows)
    groups: Dict[Tuple[object, ...], List[Mapping[str, object]]] = defaultdict(list)
    for r in rows:
        if "format_status" in r:
            groups[tuple(r.get(f) for f in by)].append(r)
    out: Dict[Tuple[object, ...], Dict[str, object]] = {}
    for g, rs in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        answered = [r for r in rs if r.get("kind") == "answered"]
        ok = sum(1 for r in answered if r.get("format_status") == "ok")
        out[g] = {"tries": len(rs), "answered": len(answered), "format_ok": ok,
                  "format_compliance": ok / len(answered) if answered else float("nan"),
                  "format_compliance_all_tries": ok / len(rs),
                  "status_counts": dict(sorted(Counter(str(r.get("format_status")) for r in rs).items()))}
    return out


def rates_1x24(rows: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """Per setup, over the 1x24 step-line rows (E3 and answer-only rows are left out): Karen's `rates_1x24` (over ANSWERED tries:
    format_compliance, trace_wrong = format ok but the trace is wrong, the absorbed and copy shares of those, official_acc, final_acc,
    copyfree_acc) plus `absorption` (D-76: the share of answered tries whose final answer is right but whose trace is not, which is
    final_acc - official_acc) and the same accuracies over every try (`*_all_tries`, non-answers wrong). A mix of answer-only and
    step-line 1x24 rows is refused (`check_answer_only`)."""
    rows = list(rows)
    check_answer_only(rows)
    by: Dict[str, List[Mapping[str, object]]] = defaultdict(list)
    for r in rows:
        if is_trace_row(r):
            _need_fields(r)
            by[str(r["setup"])].append(r)
    out: Dict[str, Dict[str, object]] = {}
    for setup in sorted(by):
        rs = by[setup]
        ans = [r for r in rs if r.get("kind") == "answered"]
        ok = [r for r in ans if r.get("format_status") == "ok"]
        tw = [r for r in ok if not r.get("correct")]
        n = len(ans) or 1
        acc = {s: sum(row_correct(r, s) for r in ans) for s in SCORES}
        out[setup] = {
            "tries": len(rs), "answered": len(ans), "format_ok": len(ok),
            "format_compliance": len(ok) / len(ans) if ans else float("nan"),
            "format_compliance_all_tries": len(ok) / len(rs),
            "trace_wrong": len(tw),
            "absorbed_share_of_trace_wrong": sum(r.get("slip_type") == "absorbed" for r in tw) / len(tw) if tw else float("nan"),
            "copy_share_of_trace_wrong": sum(r.get("slip_type") == "copy" for r in tw) / len(tw) if tw else float("nan"),
            "official_acc": acc["official"] / n, "final_acc": acc["final"] / n, "copyfree_acc": acc["copy_forgiven"] / n,
            "original_acc": acc["original"] / n,
            "format_compliance_original": sum(1 for r in ans if r.get("format_status_original", r.get("format_status")) == "ok") / len(ans)
                                          if ans else float("nan"),
            "absorption": sum(1 for r in ans if row_correct(r, "final") and not row_correct(r, "official")) / n,
            "official_acc_all_tries": sum(row_correct(r, "official") for r in rs) / len(rs),
            "final_acc_all_tries": sum(row_correct(r, "final") for r in rs) / len(rs),
            "copyfree_acc_all_tries": sum(row_correct(r, "copy_forgiven") for r in rs) / len(rs)}
    return out


grade_chain = grade_1x24          # the same function at any N: the step count is the key's length (D-86)
grade_pieces = grade_24x1        # the same function at any N: the piece count is the key's length (D-86)
rates_chain = rates_1x24         # the same function at any N: every chain shape is a trace shape (D-86)


def paired_differences(challenger: Dict[str, float], comparator: Dict[str, float]) -> List[float]:
    """challenger - comparator for every base puzzle both arms have, in base-id order (the same inputs always give the same list)."""
    return [challenger[b] - comparator[b] for b in sorted(set(challenger) & set(comparator))]


def e3_scores(step_correct_by_base: Dict[str, Sequence[Sequence[bool]]]) -> Dict[str, float]:
    """E3 per base puzzle: for each step the share of runs that got it right, multiplied over the steps, in percentage points.
    `step_correct_by_base[base]` is a list of runs, each a list of per-step booleans (all runs the same length)."""
    out: Dict[str, float] = {}
    for base, runs in step_correct_by_base.items():
        if not runs:
            continue
        n_steps = len(runs[0])
        if any(len(r) != n_steps for r in runs):
            raise ValueError(f"{base}: runs with different numbers of steps")
        p = 1.0
        for s in range(n_steps):
            p *= sum(1 for r in runs if r[s]) / len(runs)
        out[base] = 100.0 * p
    return out


def _check_shape(puzzle: ledger.LPuzzle) -> None:
    if puzzle.depth > 1 and puzzle.width != 1:
        raise ValueError(f"the D-76 parse rules are defined for one chain (1xN) or single pieces (Nx1), not {puzzle.width}x{puzzle.depth}")


def all_step_lines_right(reply: str, puzzle: ledger.LPuzzle, repeats: str = trace_parse.REPEATS) -> bool:
    """The official D-76 score of one reply. 1x24: the reply parses (status ok, so the Answer line equals line 24) and every step line
    equals the key; a missing, repeated or misnumbered line, or a value that breaks the value rules, is wrong. 24x1: there are no step
    lines, so it is the whole-answer score (every piece present, passing the value rules and right)."""
    _check_shape(puzzle)
    if puzzle.depth == 1:
        return bool(grade_24x1(reply, puzzle.answer, puzzle.params.lines)["correct"])
    return bool(grade_1x24(reply, puzzle.chains[0].states, puzzle.params.lines, repeats=repeats)["correct"])


# ---------------------------------------------------------------- the slip tables

def _step_class(kind: str) -> str:
    """T / G by the step's OWN kind; the house rule is analysed puzzle-wide, not as a class."""
    if kind in T_KINDS:
        return "T"
    return "G" if kind in G_KINDS else "other"


def _decoy_twin(puzzle: ledger.LPuzzle, label: str) -> Optional[str]:
    """The printed decoy that is a near-duplicate of rule `label`: same kind, the most similar sentence (ratio >= 0.7). A heuristic read from the
    printed rulebook; it is only used to name one specific mistake."""
    kinds = {lab: k for lab, k, _ in puzzle.rulebook}
    texts = {lab: t for lab, _, t in puzzle.rulebook}
    best, best_r = None, 0.0
    for d in puzzle.decoys:
        if kinds[d] != kinds[label]:
            continue
        r = difflib.SequenceMatcher(None, texts[label], texts[d]).ratio()
        if r > best_r:
            best, best_r = d, r
    return best if best_r >= 0.7 else None


def _forced_house(house: ledger.House, state: Sequence[int]) -> Tuple[int, ...]:
    """`state` with the house move made whatever the threshold says (the 'misapplied' check)."""
    s = list(state)
    lo, hi = s.index(min(s)), s.index(max(s))
    if lo != hi:
        mv = min(house.a, s[hi])
        s[hi] -= mv
        s[lo] += mv
    return tuple(s)


class _Rules:
    """The puzzle's rules as separate functions (bare, composite, decoys), all read from the PRINTED prompt by the independent re-solver."""

    def __init__(self, puzzle: ledger.LPuzzle):
        self.puzzle = puzzle
        self.names, self.composite, _ = ledger_check.parse(puzzle.prompt)
        self.bare = {lab: ledger_check.parse_rule(txt, self.names) for lab, _, txt in puzzle.rulebook}
        self.house = ledger.House(**puzzle.house) if puzzle.house else None
        self.kind = {lab: k for lab, k, _ in puzzle.rulebook}

    def judge(self, seq: int, k: int, label: str, previous: Sequence[int], written: Sequence[int]) -> Dict[str, object]:
        """One step checked from `previous`. R = the rule alone, H = R then the house rule. The blame follows Karen's order."""
        r = tuple(self.bare[label](list(previous)))
        h = tuple(self.house.after(r)) if self.house else r
        w = tuple(written)
        should_act = h != r
        row: Dict[str, object] = {"sequence": seq, "step": k, "label": label, "kind": self.kind[label], "cls": _step_class(self.kind[label]),
                                  "house_should_act": should_act, "written": w, "expected": h, "slipped": w != h, "blame": None}
        if w == h:
            return row
        twin = _decoy_twin(self.puzzle, label)
        twin_results = set()
        if twin is not None:
            alt = tuple(self.bare[twin](list(previous)))
            twin_results = {alt, tuple(self.house.after(alt)) if self.house else alt}
        if self.house is not None and should_act and w == r:
            row["blame"] = "house_missed"
        elif self.house is not None and not should_act and w == _forced_house(self.house, r):
            row["blame"] = "house_misapplied"
        elif w in twin_results:
            row["blame"] = "decoy_confusion"
        else:
            row["blame"] = "kind"
        return row


def local_steps(reply: str, puzzle: ledger.LPuzzle, repeats: str = trace_parse.REPEATS) -> Dict[str, object]:
    """THE PRIMARY SLIP VIEW. Returns {"unplaceable": reason or None, "status": the parse status, "steps": [row, ...]}; each row says which
    rule kind the step had, whether the house rule should have acted, what was written, what it should have been, and the blame
    ("house_missed", "house_misapplied", "decoy_confusion", "kind" or None when the step is right). 1x24: the steps are placed from the
    parser's `step_states`, so a try whose only failure is its Answer line is placed when a step slipped, and unplaceable (with the
    parser's reason) when every step is right."""
    _check_shape(puzzle)
    rules = _Rules(puzzle)
    out: List[Dict[str, object]] = []
    if puzzle.depth == 1:
        pp = trace_parse.parse_pieces(reply, puzzle.width, puzzle.params.lines)
        if not pp.ok:
            return {"unplaceable": pp.detail, "status": pp.status, "steps": []}
        for i, ch in enumerate(puzzle.chains, 1):
            out.append(rules.judge(i, 1, ch.names[0], ch.start, pp.entries[i]))
        return {"unplaceable": None, "status": pp.status, "steps": out}
    tp = trace_parse.parse_trace(reply, puzzle.params.lines, puzzle.depth, repeats=repeats)
    if tp.step_states is None:                                        # a step line missing or unreadable
        return {"unplaceable": tp.detail, "status": tp.status, "steps": []}
    ch = puzzle.chains[0]
    previous: Sequence[int] = ch.start
    for k, (label, written) in enumerate(zip(ch.names, tp.step_states), 1):
        out.append(rules.judge(1, k, label, previous, written))
        previous = written
    if not tp.ok and not any(row["slipped"] for row in out):           # every step right, the Answer line wrong
        return {"unplaceable": tp.detail, "status": tp.status, "steps": []}
    return {"unplaceable": None, "status": tp.status, "steps": out}


def first_slip_steps(reply: str, puzzle: ledger.LPuzzle, repeats: str = trace_parse.REPEATS) -> Dict[str, object]:
    """THE SENSITIVITY VIEW: a piece, or the chain steps up to and including the first wrong one, each checked from the KEY's previous state.
    Same shape as `local_steps`, plus "signature": the first slip as (sequence, step, written balances), or None."""
    res = local_steps(reply, puzzle, repeats=repeats)
    if res["unplaceable"] is not None:
        return dict(res, signature=None)
    out: List[Dict[str, object]] = []
    signature = None
    if puzzle.depth == 1:
        for row in res["steps"]:
            out.append(row)
            if row["slipped"] and signature is None:
                signature = (row["sequence"], 1, row["written"])
        return {"unplaceable": None, "status": res["status"], "steps": out, "signature": signature}
    rules = _Rules(puzzle)
    states = trace_parse.parse_trace(reply, puzzle.params.lines, puzzle.depth, repeats=repeats).step_states
    ch = puzzle.chains[0]
    previous: Sequence[int] = ch.start
    for k, (label, written) in enumerate(zip(ch.names, states), 1):  # type: ignore[arg-type]
        row = rules.judge(1, k, label, previous, written)
        out.append(row)
        if row["slipped"]:
            signature = (1, k, row["written"])
            break
        previous = ch.states[k - 1]
    return {"unplaceable": None, "status": res["status"], "steps": out, "signature": signature}


def slip_table(placed: Iterable[Tuple[str, Dict[str, object]]]) -> Dict[Tuple[str, str], Dict[str, int]]:
    """Counts per (model, row) from `(model, local_steps(...) or first_slip_steps(...))` pairs. Rows:
    - (model, <kind>) and (model, "class T" / "class G" / "class other"): steps checked (`at_risk`) and KIND slips (`slips`: blame "kind" or
      "decoy_confusion"); house slips are not counted here;
    - (model, "house"): `steps_checked` (every step checks the house rule), `steps_house_fires` (steps where it should act),
      `steps_house_should_not_fire`, `missed` (the house rule should have acted but did not), `misapplied` (it should not have acted but the
      house move was made) and `house_slips` (their sum). The refined index uses missed ÷ steps_house_fires and, separately, misapplied ÷
      steps_house_should_not_fire;
    - (model, "decoy confusion"): `slips` of that kind (also counted under their step's kind);
    - (model, "unplaceable"): `tries` left out."""
    t: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(Counter)
    for model, res in placed:
        if res["unplaceable"] is not None:
            t[(model, "unplaceable")]["tries"] += 1
            continue
        for st in res["steps"]:
            blame = st["blame"]
            kind_slip = blame in ("kind", "decoy_confusion")
            for key in ((model, str(st["kind"])), (model, "class " + str(st["cls"]))):
                t[key]["at_risk"] += 1
                t[key]["slips"] += kind_slip
            h = t[(model, "house")]
            h["steps_checked"] += 1
            h["steps_house_fires"] += bool(st["house_should_act"])
            h["steps_house_should_not_fire"] += not st["house_should_act"]
            h["missed"] += blame == "house_missed"
            h["misapplied"] += blame == "house_misapplied"
            h["house_slips"] += blame in ("house_missed", "house_misapplied")
            if blame == "decoy_confusion":
                t[(model, "decoy confusion")]["slips"] += 1
    return {k: dict(v) for k, v in t.items()}


# ---------------------------------------------------------------- repeat share

def pairwise_agreement(signatures: Sequence[object]) -> Dict[str, float]:
    """For the WRONG tries of one puzzle (signatures: final answers, or first-slip signatures): the share of pairs that give the same value,
    and the share held by the most common value. Needs at least 2 wrong tries."""
    n = len(signatures)
    if n < 2:
        return {"pairs": 0, "agree": 0, "share": float("nan"), "top_share": float("nan")}
    pairs = n * (n - 1) // 2
    agree = sum(1 for a, b in combinations(signatures, 2) if a == b)
    return {"pairs": pairs, "agree": agree, "share": agree / pairs, "top_share": max(Counter(signatures).values()) / n}


def pooled_repeat_share(wrong_by_puzzle: Dict[str, Sequence[object]]) -> Dict[str, float]:
    """Pairwise agreement pooled over puzzles that have at least 2 wrong tries (pairs and agreeing pairs added up)."""
    pairs = agree = 0
    tops: List[float] = []
    for sigs in wrong_by_puzzle.values():
        r = pairwise_agreement(list(sigs))
        if r["pairs"]:
            pairs += int(r["pairs"])
            agree += int(r["agree"])
            tops.append(r["top_share"])
    return {"pairs": pairs, "agree": agree, "share": agree / pairs if pairs else float("nan"),
            "mean_top_share": sum(tops) / len(tops) if tops else float("nan"), "puzzles": len(tops)}
