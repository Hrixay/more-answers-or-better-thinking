"""The fixed reply parser of ruling D-76 (the rules agreed between Friday and Karen; the same for every arm). No model calls.

A 1x24 reply is read as its step lines `1.1` .. `1.24` and its `Answer` line. `parse_trace` returns the status, the 24 states
and the Answer state; the OFFICIAL score (scoring.grade_1x24) is "status ok and every state equals the key's". It also returns
`step_states`: the 24 states whenever the step lines themselves are readable, even when the Answer line fails (`no_answer`, its value
rules, `answer_mismatch`). Only the fairness check's slip view reads them (the plan's "Fairness check", item 4: a try with readable step
lines and a slip in them is placed, whatever its Answer line says); the status and `states` are unchanged, so the official score is too.
This text is the one list of the parse rules (D-76: the fixed parse rules); the scoring, the analysis and the preset choice all use
this parser.

ACCEPTED (status ok):
- whitespace anywhere: around `=`, after commas, inside brackets, leading and trailing, tabs, CRLF, blank lines between step lines;
  any Unicode space counts (a no-break space U+00A0, the U+2000 spaces, ...), and so do the zero-width characters U+200B, U+200C,
  U+200D, U+2060 and U+FEFF;
- markdown or bullets around the label or the line: `**1.3** = [...]`, `__1.3__ = [...]`, a backticked line, `- 1.3 = [...]`, `> `, `#`;
- `:` in place of `=`;
- the state in `[...]`, in `(...)` or with no brackets, as long as it is exactly L comma-separated integers (L = the preset's line
  count, a parameter); leading zeros (`0950` is 950);
- ONE period or comma right after the state, on a step line or the Answer line (`1.3 = [...].`, `Answer: 1 = [...].`): a harmless
  formatting variant. Only one, and only right after the closing bracket (or the last digit); anything else after the state is
  `non_integer`;
- step lines in any order, as long as each number 1..24 appears (D-90, Deviation 2: a number written more than once is read ONCE when
  every copy has the IDENTICAL state, compared after reading, so spacing and markup do not matter; for example a model that repeats its
  step lines as a summary block); prose lines before, between and after them (a prose line
  is any line that is neither a step line nor an Answer line, see below: `Answer check: done` is a prose line);
- a code fence around everything (a fence line is a prose line);
- the LAST Answer line wins (an earlier draft Answer line is ignored); `answer` in any case, with or without `:`, bold or italic
  (`**Answer**:`, `__Answer__:`, `_Answer_:`) allowed, with or without the `1 =` (or `1:`) label before the state;
- the label word `Sequence` or `Piece` (any case, then whitespace) before an entry number, at both shapes: `Answer: Sequence 1 = [...]`,
  `Answer: Piece 1 = [...]`, and at 24x1 `Answer: Sequence 1 = [...], Sequence 2 = [...]` (Karen, 2026-10-11). The prompts call each item
  a "sequence", so a model may echo the word; "piece" is harmless. Only these two words, and only singular: `Answer check: done` stays a
  prose line, and `Answer: Sequences 1 = [...]` is not an Answer line (no_answer when it is the only one);
- markup around the label word and the entry number (`Answer: **Sequence 1** = [...]`, `Answer: **1** = [...]`), and `:` in place of `=`
  after an entry number at both shapes (`Answer: Sequence 1: [...], Sequence 2: [...]`, `Answer: 1: [...], 2: [...]`) (Karen, r2 cases).
REJECTED (status not ok), checked in this order (the reason labels are advisory; `ok` or not is what binds):
- `misnumbered`     a step line whose sequence is not 1 or whose place is outside 1..24 (`1.0`, `1.25`, `2.3`);
- `extra_line`      a step number written more than once with DIFFERENT states (D-90). Under the original rule of prereg-lock-2
                    (`repeats="strict"`, the named sensitivity view "original") ANY repeat is `extra_line`, even with the same state;
- `missing_line`    a step number from 1..24 that is not written;
- `non_integer`     a value that is not a whole number (`2002.0`, a word, `~7150`, an empty slot), brackets that do not close, or text
                    after the state other than one period or comma (`[1, 2] (house rule)`, `[1, 2]..`);
- `wrong_length`    not exactly L values (a thousands separator such as `2,002` splits into an extra value, so it lands here);
- `no_answer`       no Answer line;
- the Answer state is checked by the same value rules (`non_integer`, `wrong_length`);
- `answer_mismatch` the Answer state differs from line 24.

What counts as a step line: after leading whitespace and markup (`*`, backtick, `_`, `-`, `+`, `>`, `#`), the label `S.K` (digits, a dot,
digits), optional closing markup, then `=` or `:`. Everything after that separator, less surrounding whitespace and markup (`*`,
backtick, `_`), is the state. A sign `-` before a digit is read as part of an integer (a negative balance is a wrong value, not a format
failure).

What counts as an Answer line: after leading whitespace and markup, the word `answer` (any case; not followed by a letter or digit, so
`Answers` and `Answered` are not), optional closing markup, an optional `:`, then, after whitespace and markup, text that STARTS LIKE A
STATE: an optional entry label (a number then `=` or `:`, the number optionally after the word `Sequence` or `Piece`, markup allowed
around both), followed by `[`, `(`, a digit, or `-` and a digit. A label with any number counts, so `Answer: Sequence 2 = [...]` is an
Answer line exactly like `Answer: 2 = [...]`, and both fail the value rules at 1x24 (non_integer). Any other line that starts with `answer` is a prose line and does not replace an earlier Answer line (`Answer check: every
line verified.`, `Answer verified above.`, `## Answer` on its own). The same definition is used for the answer-only fallback prompt
(`parse_final`).

24x1 replies (`parse_pieces`) find their Answer line by the SAME definition as 1x24 (`last_answer_text`, Edith R3-a): markup and `_`
around `answer`, an optional `:`, the last line whose text starts like a state wins, and a prose line such as `Answer check: done` or a
`## Answer` heading never replaces the real one. The entries are read as before (`N = [...]`, `N: [...]` or `N = value`, optionally after the word
`Sequence` or `Piece`, markup allowed around both; a repeated N keeps its last value, anything between entries is skipped), and the D-76 value rules apply to each
entry: exactly L integers, integers only. An entry
that breaks them is left out of `entries` and named in `bad`. Compared with the pilot grader's reader (`prompt_d31.parse_answer`), this
reads `**Answer**: ...`, `+ Answer: ...` and `Answer 1 = ...` (no colon), ignores prose Answer lines after the real one, and keeps a sign
(`-5` is -5; the old reader dropped the `-` inside brackets). The 24x1 scoring rule itself (D-39: every piece right) is unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..taskgen import prompt_d31

STEPS = 24                                                        # the default only: `parse_trace(..., steps=N)` reads a 1xN chain (D-86)
REPEATS_IDENTICAL = "identical"   # D-90 (Deviation 2), the official rule: a step line repeated with the identical state is read once
REPEATS_STRICT = "strict"         # the original D-76 rule (prereg-lock-2): any repeated step line fails; kept as the sensitivity view "original"
REPEAT_RULES = (REPEATS_IDENTICAL, REPEATS_STRICT)
REPEATS = REPEATS_IDENTICAL       # the default everywhere: the official rule
STATUSES = ("ok", "misnumbered", "extra_line", "missing_line", "non_integer", "wrong_length", "no_answer", "answer_mismatch")

State = Tuple[int, ...]

_ZERO_WIDTH = {ord(c): " " for c in "\u200b\u200c\u200d\u2060\ufeff"}   # read as spaces: Python's \s and str.strip() do not see them
_LEAD = r"^[\s*`_\-+>#]*"
_STEP = re.compile(_LEAD + r"(\d+)\.(\d+)[*`_]*\s*[=:]\s*(.*)$")
_ANSWER = re.compile(_LEAD + r"answer(?![a-z0-9])[*`_]*\s*:?(.*)$", re.I)
_M = r"[*`_]*"                                                   # markup that may wrap a label word or an entry number
_WORD = r"(?:(?:sequence|piece)" + _M + r"\s+)?"                # the optional label word before an entry number (any case)
_ENTRY_LABEL = _M + _WORD + _M + r"(\d+)" + _M + r"\s*[=:]"     # e.g. `1 =`, `**Sequence 1** =`, `Piece 2:`
_STATE_START = re.compile(r"^[\s*`_]*(?:" + _ENTRY_LABEL + r"[\s*`_]*)?(?:[\[(]|-?\d)", re.I)
_LABEL = re.compile(r"^" + _M + _WORD + _M + r"1" + _M + r"\s*[=:]\s*", re.I)
_EDGES = re.compile(r"^[\s*`_]+|[\s*`_]+$")                       # whitespace (any Unicode space) and markup at both ends
_INT = re.compile(r"^-?\d+$")
_ENTRY = re.compile(_ENTRY_LABEL + r"\s*(\[[^\]]*\]|-?\d+)", re.I)   # a 24x1 entry: prompt_d31._ENTRY plus a sign, a label word, markup and `:`


@dataclass(frozen=True)
class TraceParse:
    """`status` is "ok" or a reject reason. `states` (the 24 states in step order) only when ok. `answer` is the state of the last Answer
    line whenever that line passes the value rules, even when the trace is not ok (the secondary final-answer view uses it); None
    otherwise. `detail` says what went wrong, in words. `step_states` is the 24 states whenever every step line is readable: equal to
    `states` when ok, and also set when the only failure is on the Answer line (`no_answer`, `non_integer` / `wrong_length` on the
    Answer line, `answer_mismatch`); None when a step line is missing, repeated, misnumbered or breaks the value rules. It is for the
    slip view only (`scoring.local_steps`); the scores read `status` and `states`."""
    status: str
    states: Optional[Tuple[State, ...]]
    answer: Optional[State]
    detail: str = ""
    step_states: Optional[Tuple[State, ...]] = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class PiecesParse:
    """A 24x1 reply. `entries` holds the entries that pass the value rules; `bad` maps an entry number to why it failed."""
    status: str
    entries: Dict[int, State] = field(default_factory=dict)
    bad: Dict[int, str] = field(default_factory=dict)
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def _clean(text: str) -> str:
    """`text` less whitespace (any Unicode space, the zero-width characters) and markup (`*`, backtick, `_`) at both ends."""
    return _EDGES.sub("", text.translate(_ZERO_WIDTH))


def _body(text: str) -> str:
    """The written state as read: cleaned, then ONE period or comma dropped when it comes right after the state (after `]`, `)` or a
    digit)."""
    v = _clean(text)
    if len(v) >= 2 and v[-1] in ".," and (v[-2] in "])" or v[-2] in "0123456789"):
        v = _clean(v[:-1])
    return v


def _n_values(text: str) -> int:
    """How many values a written state holds (for the `wrong_length` detail)."""
    return len([t for t in _body(text).strip("[]()").split(",") if t.strip()])


def read_state(text: str, line_count: int) -> Tuple[Optional[State], Optional[str]]:
    """One written state: (the integers, None) or (None, "non_integer" | "wrong_length")."""
    v = _body(text)
    if v[:1] in ("[", "("):
        close = "]" if v[0] == "[" else ")"
        if not v.endswith(close):
            return None, "non_integer"
        v = v[1:-1]
    if any(ch in v for ch in "[]()"):
        return None, "non_integer"
    if not v.strip():
        return None, "wrong_length"
    toks = [t.strip() for t in v.split(",")]
    if not all(_INT.match(t) for t in toks):
        return None, "non_integer"
    if len(toks) != line_count:
        return None, "wrong_length"
    return tuple(int(t) for t in toks), None


def last_answer_text(reply: str) -> Optional[str]:
    """What follows `answer` (and its `:`) on the LAST Answer line, or None if there is none. A line that starts with `answer` but whose
    text does not start like a state is a prose line (see the module text)."""
    found = None
    for ln in reply.translate(_ZERO_WIDTH).splitlines():
        m = _ANSWER.match(ln)
        if m and _STATE_START.match(m.group(1)):
            found = m.group(1)
    return found


def parse_final(reply: str, line_count: int) -> Tuple[str, Optional[State]]:
    """The last Answer line of a one-sequence reply, read by the value rules: ("ok", state) or (reason, None). The `1 =` label is
    optional. Used for the Answer line of a trace and for the answer-only fallback prompt (D-36(5); D-76: answer-only fallback)."""
    text = last_answer_text(reply)
    if text is None:
        return "no_answer", None
    state, why = read_state(_LABEL.sub("", _clean(text), count=1), line_count)
    return ("ok", state) if why is None else (why, None)


def _same_state(a: str, b: str, line_count: int) -> bool:
    """Two copies of one step line agree (D-90): both read to the same state, or (when either cannot be read) the same text after
    the surrounding whitespace and markup are removed, so the value rules then judge the line once."""
    sa, wa = read_state(a, line_count)
    sb, wb = read_state(b, line_count)
    if wa is None and wb is None:
        return sa == sb
    return _EDGES.sub("", a) == _EDGES.sub("", b)


def parse_trace(reply: str, line_count: int, steps: int = STEPS, repeats: str = REPEATS) -> TraceParse:
    """A 1x`steps` reply under the D-76 rules (see the module text). `repeats`: "identical" (D-90, the official rule) or "strict"
    (the original rule of prereg-lock-2: any repeated step line fails)."""
    if repeats not in REPEAT_RULES:
        raise ValueError(f"repeats must be one of {REPEAT_RULES}, not {repeats!r}")
    lines: List[Tuple[int, int, str]] = []
    for ln in reply.translate(_ZERO_WIDTH).splitlines():
        m = _STEP.match(ln)
        if m:
            lines.append((int(m.group(1)), int(m.group(2)), m.group(3)))
    a_status, answer = parse_final(reply, line_count)

    def bad(status: str, detail: str) -> TraceParse:
        return TraceParse(status, None, answer, detail)

    for s, k, _ in lines:
        if s != 1 or not 1 <= k <= steps:
            return bad("misnumbered", f"step line {s}.{k} is outside 1.1 to 1.{steps}")
    seen: Dict[int, str] = {}
    for _, k, v in lines:
        if k in seen:
            if repeats == REPEATS_STRICT:
                return bad("extra_line", f"step line 1.{k} is written more than once")
            if not _same_state(seen[k], v, line_count):
                return bad("extra_line", f"step line 1.{k} is written more than once with different states")
            continue                                                  # an identical repeat is read once (D-90)
        seen[k] = v
    for k in range(1, steps + 1):
        if k not in seen:
            return bad("missing_line", f"step line 1.{k} missing")
    states: List[State] = []
    first_len = None
    for k in range(1, steps + 1):
        st, why = read_state(seen[k], line_count)
        if why == "non_integer":
            return bad("non_integer", f"step line 1.{k} has a value that is not a whole number: {seen[k].strip()!r}")
        if why == "wrong_length" and first_len is None:
            first_len = f"step line 1.{k} has {_n_values(seen[k])} balances, not {line_count}"
        states.append(st)  # type: ignore[arg-type]
    if first_len is not None:
        return bad("wrong_length", first_len)
    read = tuple(states)                                              # every step line is readable from here on

    def answer_bad(status: str, detail: str) -> TraceParse:
        return TraceParse(status, None, answer, detail, read)

    if a_status == "no_answer":
        return answer_bad("no_answer", "no Answer line")
    if a_status != "ok":
        return answer_bad(a_status, f"the Answer line breaks the value rules ({a_status})")
    if answer != states[-1]:
        return answer_bad("answer_mismatch", f"the Answer line differs from line 1.{steps}")
    return TraceParse("ok", read, answer, "", read)


def parse_pieces(reply: str, width: int, line_count: int) -> PiecesParse:
    """A 24x1 reply: the last Answer line (`last_answer_text`, the same definition as 1x24) with the D-76 value rules for each entry. Status, in order:
    `no_answer`, `misnumbered` (an entry number outside 1..width), `non_integer` / `wrong_length` (the first bad entry), `missing_line`
    (a number not given)."""
    text = last_answer_text(reply)
    if text is None:
        return PiecesParse("no_answer", detail="no answer line")
    raw: Dict[int, str] = {}
    for m in _ENTRY.finditer(text):
        raw[int(m.group(1))] = m.group(2)                             # a repeated number keeps its last value (as before)
    out = [i for i in raw if not 1 <= i <= width]
    entries: Dict[int, State] = {}
    bad: Dict[int, str] = {}
    for i, v in raw.items():
        if not 1 <= i <= width:
            continue
        st, why = read_state(v, line_count)
        if why is None:
            entries[i] = st  # type: ignore[assignment]
        else:
            bad[i] = why
    if out:
        return PiecesParse("misnumbered", entries, bad, f"entry {out[0]} is outside 1 to {width}")
    if bad:
        i = min(bad)
        detail = (f"piece {i} has {_n_values(raw[i])} balances, not {line_count}" if bad[i] == "wrong_length"
                  else f"piece {i} has a value that is not a whole number")
        return PiecesParse(bad[i], entries, bad, detail)
    missing = [i for i in range(1, width + 1) if i not in raw]
    if missing:
        return PiecesParse("missing_line", entries, bad, f"piece {missing[0]} missing")
    return PiecesParse("ok", entries, bad, "")
