"""Operations and disclosure tables: the plan's TAB-17 (runs, completeness and spend), TAB-19 (deviations and disclosed changes),
TAB-20 (pre-registration timeline), TAB-21 (tuning bias), TAB-22 (data README) and TAB-23 (reproducibility).

Where the numbers come from:
- The JSON analysis files already pinned in `paper_out_core.SOURCES` (`main`, `main_k`, `groupc`, `s1b`, `s1b_k`, `topup`), by key.
- Text files pinned here (`register_source`, kind "text"): the spend log, the lock manifest, the decision register, the Study 1 spec,
  the findings register, the claims-ledger format note, LOG.md, and six review files (the main-run, Study 1b and top-up clearances, the
  plan settlement with its groups 3 and 4). Each is read at the commit that last changed it, with its SHA-256.
  A table cell is read by `L<n>['<column>']` (a markdown table cell) or `L<n>` (a whole line); the line number is found by a regex on
  the line (`S.find_lines`), never typed.

No number, date, time, commit or hash is typed. A fact that sits inside a longer stamped cell or line is cut out by `extract`, which
keeps the whole stamped cell as the cell's source and records the regex as the cell's formula, so a reader (or Edith's checker) can
repeat the cut. Typed text is limited to short digit-free labels (row and column names, one-line explanations); a typed clause
that states a fact is guarded by the record's own words (`guard`), and that record is kept in the cell's sources without being printed.

What prints and what stays in the sources (Edith's PR 27 rulings, Jarvis's PO-1): no decision id (D-nn) and no internal record name
(the decision register, the findings register, LOG.md, the spend log) prints. A ruling prints in plain words (`ruling`), with its
register id and the decision text the words rest on kept, unprinted, in the cell's sources; the other records are named by what they
are ("our cost records", "our log"). The appendix voice is "we". The top-up's start is described by its times and the disclosed change
only (D-142: the paper does not say it started earlier than intended, and gives no reason for the pause).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paper_out_core import need_history
from .paper_out_core import (EMPTY, PT_PER_IN, SOURCES, Cell, KeyMissing, Ref, Source, Store, Table, _pieces, _width_plan, _wrapped_lines,
                             ci_refs, fmt_fixed, format_key,
                             integer, interval, joined, join_key, label, num, output, parse_key, pct, register_source, split_rows_by_space,
                             text_of)
from .paper_out_names import EFFORT_ORDER, STUDY1_ARMS, STUDY1B_TAGS, STUDY1_TESTS, shape

# ---------------------------------------------------------------- pinned text sources
# Each is pinned at the commit on origin/main that last changed the file; the SHA-256 is of the bytes at that commit.

register_source(Source("spend_log", "ops/spend-log.md", "b216f07",
                       "ea0ad353622b9d88a591d0afa6748fe5640cff696bb99fa66b83a237bf998929", kind="text",
                       what="The spend log: one row per paid run, the summary and the raw-backup hashes"))
register_source(Source("lock_manifest", "ops/lock/LOCK-MANIFEST.md", "d1c565f",
                       "64a276d42e352cb716004c9f78f4d95a033bc6f9ad0122870da14df51f3ad1a5", kind="text",
                       what="The lock manifest (tag commits, hashes, versions, exposed bases), as cut for lock 4"))
register_source(Source("register", "decisions/register.md", "28944cb",
                       "2fb8de56a0abf0053fa1f1499b003a93c0cf27fc37f1b36cad6f718e910fed95", kind="text",
                       what="The decision register (one row per ruling; through D-141, so D-134's acceptance of Addendum C is in)"))
register_source(Source("spec1", "studies/1-real-price/spec.md", "f773d83",
                       "0ab437934a8df843db20ff9eb4aa57dd6e8228605f38df4b77e138d942e6c169", kind="text",
                       what="The Study 1 pre-registration spec (bias table, Deviations 1 and 2, Amendment 1)"))
register_source(Source("findings", "research/paper-notes/findings-register.md", "b6e1788",
                       "4c92d9979b511683d0fd2443a8809e95dd9443c892cb42f0da8b76b3aa36bf28", kind="text",
                       what="The findings register (section 5: process and integrity disclosures, 5.7 with D-134's acceptance of "
                            "Addendum C; section 6: costs)"))
register_source(Source("claims_format", "research/paper-notes/claims-ledger-format.md", "c59ccfa",
                       "12635ab5ed6a58c6f1560aad1bddf86b4f791cb144be277370eb50ed58e81fe9", kind="text",
                       what="The claims-ledger format (section 2: the source field; section 7: renamed `sources`, one entry per file)"))
register_source(Source("clr_main", "ops/reviews/2026-10-12-clearance-main-l14n6-1.md", "f4a14d1",
                       "46f7dc88fe60f98054d987615bf99949628302836a137a560886d958f07aba2f", kind="text",
                       what="The main-run clearance review (step 5: the clearance's expiry)"))
# The same files and commits paper_out_timeline.py pins as clr_topup and settle_g3, under names of this module's own, so that
# neither module's pins depend on the other's.
register_source(Source("topup_clearance", "ops/reviews/2026-10-13-clearance-topup-1.md", "ea3181d",
                       "dc5989d53a19c5aafa67f02401bfa007f856a0e4bd431c69fdb0f70aa24965a3", kind="text",
                       what="The top-up clearance review (the run record: no final record when the run was paused)"))
register_source(Source("settlement_g3", "ops/reviews/2026-10-15-plan-settlement/g3.md", "05fddf9",
                       "92f48d733d8986a72edc3d19b18bb24906a4dc9700c9a44ebe7274218d771745", kind="text",
                       what="The plan settlement, group 3 (item E-13: the neutral footnote on the top-up pause)"))
register_source(Source("log", "LOG.md", "bec30e3",
                       "16a220dae12460a5a8e9b0dc9c4371a50ed0d51901357ba30efe4a0f6339e1b8", kind="text",
                       what="LOG.md: dated entries for each lock, public timestamp, stamp and driver run"))
# The same files and commits paper_out_timeline.py pins as settle_g4 and clr_1b, again under names of this module's own.
register_source(Source("settlement_g4", "ops/reviews/2026-10-15-plan-settlement/g4.md", "05fddf9",
                       "f609e65d2b4a6fbc4d1706d1b333083a8d0d8506c649adab656a793f7de2075b", kind="text",
                       what="The plan settlement, group 4 (item E-16: tag and commit times from git; the lock-proof table; the analysis "
                            "stamp's gist time; Lock 4's lineage)"))
register_source(Source("study1b_clearance", "ops/reviews/2026-10-13-clearance-study1b-1.md", "5b0f8f5",
                       "042a5e2d41e775c64db2dc581f771a7c9d53a459158f39ada4a6e6526660e645", kind="text",
                       what="The Study 1b clearance review (the byte-identical re-run whose end cleared Study 1b's results to be read)"))
register_source(Source("settlement_main", "ops/reviews/2026-10-15-plan-settlement.md", "05fddf9",
                       "ca84a5e312dec0107845c67bd2fc2be32698420ff30fb211a683151035683ec7", kind="text",
                       what="The plan settlement (plan problem N2: Amendment 1's understatement and the ruling that corrects it as a "
                            "disclosed erratum)"))

DASH = label("—")
STUDY_1B = "Study 1b"

# ---------------------------------------------------------------- helpers


def _unique(vals: Sequence[Any], what: str) -> Any:
    first = vals[0]
    if any(v != first for v in vals[1:]):
        raise KeyMissing(f"{what}: the pattern matches different values {sorted(set(vals))}")
    return first


def extract(r: Ref, pattern: str, group: int = 1, dp: Optional[int] = None, first: bool = False) -> Cell:
    """A fact cut out of one stamped text cell or line (`r`) by a regex. The cell's source is the whole stamped cell; the regex and
    the group are recorded as the formula, so the cut can be repeated. With `dp` the cut is a decimal number printed to that many
    places (half away from zero); otherwise it is printed as written. The pattern must match exactly one distinct value unless
    `first` is set."""
    text = str(r.value)
    hits = [m.group(group) for m in re.finditer(pattern, text)]
    if not hits:
        raise KeyMissing(f"{r.source}:{r.key}: no match for /{pattern}/")
    got = hits[0] if first else _unique(hits, f"{r.source}:{r.key} /{pattern}/")
    printed = got
    formula = f"text cut /{pattern}/ group {group}"
    if dp is not None:
        printed = fmt_fixed(float(got.replace(",", "")), dp)
        formula += f"; rounded to {dp} places"
    return Cell(printed, raw=got, refs=(r,), formula=formula)


def unprinted(c: Cell, why: str) -> Cell:
    """A cut that is checked but not printed. Joined into a cell by `_seq`, it adds its source and its cut to that cell's record, so a
    typed clause beside it names the record it rests on."""
    return Cell("", raw=c.raw, refs=c.refs, formula="; ".join(x for x in (c.formula, f"not printed: {why}") if x))


def guard(r: Ref, pattern: str, why: str) -> Cell:
    """A typed clause's evidence: the build stops unless the stamped cell or line `r` matches `pattern` (one group, one distinct
    value); the cut is recorded, not printed (see `unprinted`)."""
    try:
        c = extract(r, pattern)
    except KeyMissing:
        raise ValueError(f"{r.source}:{r.key} no longer records that {why}") from None
    return unprinted(c, f"the record for '{why}'")


def en_dash(c: Cell, count: int = 1) -> Cell:
    """A cut or a stamped text whose record writes a range with a hyphen ('samples 1-8', 'w6-w8', 'items 7-24'), printed with an en
    dash (Edith's polish standard §2.4, proof 3: 'items 7–24'). Every hyphen between a digit and the digit (or the letter and digit,
    as in 'w6-w8') that ends the range is set as an en dash; the build stops unless exactly `count` hyphens change. The cell keeps its
    source and raw value, and its formula records the change."""
    rx = re.compile(r"(?<=\d)-(?=[a-z]?\d)")
    n = len(rx.findall(c.printed))
    if n != count:
        raise ValueError(f"en_dash: {n} hyphen(s) between numbers in {c.printed!r}, expected {count}")
    return replace(c, printed=rx.sub("\u2013", c.printed),
                   formula="; ".join(x for x in (c.formula, "the record's hyphen in a range is printed as an en dash (house style)") if x))


def single_value(cells: Sequence[Cell], what: str) -> Cell:
    """The one value a constant column printed in every row (Edith's polish standard, section 7.3: a column with one value in every
    row moves to a note). The cell keeps every row's source; the build stops if the rows no longer print the same value, so the
    column has to come back."""
    if not cells:
        raise ValueError(f"{what}: no cells")
    printed = {c.printed for c in cells}
    if len(printed) != 1:
        raise ValueError(f"{what}: the rows no longer print one value ({sorted(printed)}); keep the column")
    first = cells[0]
    refs = tuple(r for c in cells for r in c.refs)
    if not refs:
        return label(first.printed)
    raws = [c.raw for c in cells]
    return Cell(first.printed, kind=first.kind, raw=first.raw if all(x == raws[0] for x in raws) else raws, refs=refs,
                formula=first.formula or "the same printed value in every row of the dropped column (the build stops otherwise)")


def set_widths(t: Table, **widths: float) -> None:
    """Set the widths of named wrapping columns (inches, in the writer's plan's units) and keep the writer's own plan for the rest (core's
    `fixed_plan`, as study1b.right_align does). Keys are column titles with every run of other characters written as one underscore
    ("First call (UTC)" is First_call_UTC). For a table whose columns the
    writer's estimate cannot size, e.g. a column whose cells become longer text in print (a cross-reference the converter expands), or a
    table that spreads room to columns that do not need it. Call it last, once the table's rows are final."""
    specs, w, numeric = _width_plan(t)
    w = dict(w)
    titles = {re.sub(r"[^A-Za-z0-9]+", "_", c.printed).strip("_"): j for j, c in enumerate(t.columns)}
    for name, inches in widths.items():
        if name not in titles or specs[titles[name]] is not None:
            raise ValueError(f"set_widths: {name!r} is not a wrapping column of the table: {sorted(titles)}")
        w[titles[name]] = inches
    t.fixed_plan = (specs, w, numeric)


def group_starts(rows: Sequence[Sequence[Cell]], *cols: int) -> List[int]:
    """Row groups (Edith's polish standard, section 7.7): the indexes of the rows that start a new group, where the printed cells of
    `cols` differ from the row above (a setting, a study, a run); the writer puts a little space above those rows."""
    def key(r: Sequence[Cell]) -> Tuple[str, ...]:
        return tuple(r[c].printed for c in cols)
    return [i for i in range(1, len(rows)) if key(rows[i]) != key(rows[i - 1])]


def commit_time_utc(S: Store, full_id: Cell) -> str:
    """The committer time (UTC, 'YYYY-MM-DDTHH:MM:SSZ') of the commit whose full 40-hex id was cut from a pinned record (`full_id`).
    The id is the SHA-1 of the commit object and the object holds the time, so the record pins the time as a SHA-256 pins a file;
    the object's bytes are hashed and checked against the id before the time is read. For a guard only (never printed)."""
    cid = str(full_id.raw)
    if not re.fullmatch(r"[0-9a-f]{40}", cid):
        raise ValueError(f"{cid!r} is not a full commit id")
    need_history(S, f"the committer time of commit {cid} (TAB-19: the disclosed change came before Study 1b was cleared)")
    body = subprocess.run(["git", "-C", str(S.repo), "cat-file", "commit", cid], check=True, capture_output=True).stdout
    if hashlib.sha1(b"commit %d\0" % len(body) + body).hexdigest() != cid:
        raise ValueError(f"commit {cid}: the object's bytes do not hash to its id")
    m = re.search(rb"^committer .* (\d+) [+-]\d{4}$", body, re.M)
    if not m:
        raise ValueError(f"commit {cid}: no committer line")
    return datetime.fromtimestamp(int(m.group(1)), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc(c: Cell) -> Cell:
    """A time cut with its record's "Z" ("11:52:36Z") printed in the form every other time of the paper's tables has, "11:52:36 UTC"
    (Edith, proof 4, S7: "Z" beside "UTC" in one row, and never explained). The cell keeps its source and raw value."""
    if not c.printed.endswith("Z") or not re.fullmatch(r"\d\d:\d\d:\d\dZ", c.printed):
        raise ValueError(f"utc: {c.printed!r} is not a time with a Z")
    return replace(c, printed=c.printed[:-1] + " UTC",
                   formula="; ".join(x for x in (c.formula, "the record's Z is printed UTC (house style)") if x))


def kj(base: str, *segs: str) -> str:
    """A key made of a dotted base path and further single segments (each bracketed if it holds a dot)."""
    return format_key((parse_key(base) if base else []) + [str(x) for x in segs])


def cell_ref(S: Store, source: str, line: int, col: Optional[str] = None) -> Ref:
    return S.ref(source, join_key(f"L{line}", col) if col else f"L{line}")


def line_of(S: Store, source: str, pattern: str, nth: int = 0, expect: Optional[int] = None) -> int:
    """The 1-based line of a text source that matches `pattern` (the `nth` match). `expect` pins how many lines must match so that a
    changed file cannot silently move a row."""
    hits = S.find_lines(source, pattern)
    if expect is not None and len(hits) != expect:
        raise KeyMissing(f"{source}: /{pattern}/ matches {len(hits)} lines, expected {expect}")
    if not hits:
        raise KeyMissing(f"{source}: no line matches /{pattern}/")
    return hits[nth]


def plan_label(S: Store, oid: str) -> Cell:
    """The plan entry's label (the tier), read from the pinned plan file."""
    for i, e in enumerate(S.get("plan", "plan.tables_figures")):
        if e["id"] == oid:
            return text_of(S.ref("plan", f"plan.tables_figures.{i}.label"))
    raise KeyMissing(oid)


def pinned(name: str, field: str) -> Cell:
    """A pinned source's own path, commit or SHA-256 (no stamped text records it elsewhere)."""
    v = getattr(SOURCES[name], field)
    return Cell(v, raw=v, refs=(), formula=f"pinned source {name}: {field}")


def key_of(r: Ref) -> Cell:
    """The key path of a stamped field, printed as the file spells it (it exists: the Ref resolved)."""
    return Cell(r.key, raw=r.key, refs=(r,), formula="the stamped key path")


def sum_dict(r: Ref) -> Cell:
    """A count held as a dict of category counts (empty = none): the sum, with the categories if any."""
    v = r.value
    if not isinstance(v, dict) or not all(isinstance(n, int) for n in v.values()):
        raise TypeError(f"{r.source}:{r.key} is {v!r}, not a dict of counts")
    total = sum(v.values())
    printed = str(total) if not v else f"{total} (" + ", ".join(f"{k} {n}" for k, n in sorted(v.items())) + ")"
    return Cell(printed, raw=v, refs=(r,), formula="sum of the category counts")


def tag_name(tag: str) -> str:
    return STUDY1B_TAGS[tag][0]


# ================================================================ TAB-17: runs, completeness and spend

# Run id (as the spend log spells it in its "Run ID" column) -> the part of the project it belongs to (a typed label).
RUN_PART = {
    "smoke-1": "Setup check", "smoke-2": "Setup check", "smoke-2 (markers)": "Setup check",
    "check-ledger-1": "Setup check", "s3-ledger-1": "Setup check",
    "pilot-ledger-1": "Pilot 1", "diag-haiku-effort-1": "Effort diagnostic", "ladder-l14n-1": "Length sweep",
    "main-l14n6-1": "Main run", "study1b-1": "Study 1b", "topup-1": "Top-up",
}

# Counts the spend-log row states in its Notes cell (regex on that cell). Absent = the row does not state it (printed as a dash).
_REFUSED = r"(\d+) refusals"
RUN_COUNTS: Dict[str, Dict[str, str]] = {
    "smoke-2": {"refusals": r"(\d+) of \d+ calls were refused"},
    "check-ledger-1": {"refusals": _REFUSED},
    "s3-ledger-1": {"refusals": _REFUSED},
    "pilot-ledger-1": {"refusals": _REFUSED, "truncations": r"\+ (\d+) truncated"},
    "diag-haiku-effort-1": {"refusals": _REFUSED, "truncations": r"(\d+) truncated at"},
    "ladder-l14n-1": {"refusals": _REFUSED, "truncations": r"(\d+) truncated"},
    "main-l14n6-1": {"refusals": _REFUSED, "truncations": r"(\d+) truncations", "missing": r"(\d+) missing"},
    "study1b-1": {"refusals": _REFUSED, "truncations": r"(\d+) truncated:", "missing": r"(\d+) missing"},
    "topup-1": {"refusals": _REFUSED, "truncations": r"(\d+) truncated \(", "missing": r"(\d+) missing"},
}

# Totals to date and Console readings, each cut from a named column of the run's own row (or, for Study 1b, from the register row
# that records the post-run ledger totals). (column, regex) pairs; the regex has one group.
RUN_RAW_TOTAL: Dict[str, Tuple[str, str]] = {
    "smoke-2": ("Notes", r"LEDGER figure ([\d.]+)"),
    "main-l14n6-1": ("Console check", r"\(raw \$([\d.]+)\)"),
    "topup-1": ("Notes", r"raw ([\d.]+), B5 [\d.]+"),
}
RUN_B5_TOTAL: Dict[str, Tuple[str, str]] = {
    "smoke-2": ("Notes", r"B5 figure about ([\d.]+)"),
    "smoke-2 (markers)": ("Console check", r"rule-adjusted figure is now \$([\d.]+)"),
    "main-l14n6-1": ("Console check", r"B5 total \$([\d.]+)"),
    "topup-1": ("Notes", r"raw [\d.]+, B5 ([\d.]+)"),
}
_CREDITS_USED = r"credits / \$([\d.]+) used"
RUN_CONSOLE_BEFORE: Dict[str, Tuple[str, str]] = {
    "pilot-ledger-1": ("Console check", r"pass, \$([\d.]+) read"),
    "ladder-l14n-1": ("Console check", _CREDITS_USED),
    "main-l14n6-1": ("Console check", _CREDITS_USED),
    "study1b-1": ("Console check", _CREDITS_USED),
    "topup-1": ("Console check", _CREDITS_USED),
}
RUN_CONSOLE_AFTER: Dict[str, Tuple[str, str]] = {
    "smoke-2": ("Console check", r"\(\$([\d.]+)\)"),
    "main-l14n6-1": ("Console check", r"Spend this month \$([\d.]+) of"),
    "study1b-1": ("Console check", r"after the run: \$([\d.]+) used"),
    "topup-1": ("Console check", r"after the run: \$([\d.]+) used"),
}


def _spend_rows(S: Store) -> List[Tuple[int, str]]:
    """(line, run id) for every row of the spend log's rows table, oldest first."""
    out = []
    for n in S.find_lines("spend_log", r"^\| \d{4}-\d\d-\d\d \|"):
        out.append((n, S.get("spend_log", join_key(f"L{n}", "Run ID"))))
    return list(reversed(out))


def _cut(S: Store, n: int, run: str, spec: Dict[str, Tuple[str, str]], dp: Optional[int]) -> Cell:
    if run not in spec:
        return DASH
    col, rx = spec[run]
    return extract(cell_ref(S, "spend_log", n, col), rx, dp=dp)


def _count(S: Store, n: int, run: str, which: str) -> Cell:
    rx = RUN_COUNTS.get(run, {}).get(which)
    return extract(cell_ref(S, "spend_log", n, "Notes"), rx) if rx else DASH


# Plain names for arms whose shared display name carries an internal code (Edith's N-11: "E3", "E2", "C13" print as plain names).
_PLAIN_ARM = {"e3": "Step voting"}


def _arm_label(model_arm: str) -> str:
    return _PLAIN_ARM.get(model_arm, STUDY1_ARMS[model_arm][0])


MADE = "*"          # marks a setting whose figure is the calls actually made (an adaptive design has no designed count)


def is_made(S: Store, source: str, entry: str) -> bool:
    """Does the stamped entry's own label say its count is over the calls actually made (an adaptive design with no designed count)?"""
    return "actually made" in S.get(source, entry).get("label", "")


def made_name(name: str, made: bool) -> Cell:
    """A setting's name, marked with MADE where its count is the calls made. The mark sits on the name, not on the count, so the digits of
    the count stay in line (Edith, proof 4, S6: "1,086 (made)" pushed its digits 31 pt left of the column)."""
    return label(name + MADE if made else name)


# Rows of the completeness panel by model, then effort, then shape (chains first), the special rows last (Edith, proof 4, S6: the keys'
# order put Haiku's efforts high, low, medium, thinking off, max, xhigh, the real-time rows mid-group and the pieces rows first at 12 and 16
# steps). The model order is the paper's tables' (Haiku, Sonnet, Opus).
MODEL_ORDER = ("haiku", "sonnet", "opus")
SPECIAL_ARMS = ("haiku-med-d42-variant", "rt-haiku-med", "rt-sonnet-med", "rt-opus-med")     # the rewording check, then the real-time rows
TOPUP_ORDER = ("e2_planner", "e2_helpers", "e2_aggregator", "h_pick8", "c13", "same_model")     # the Haiku team's steps in order, the picker, step voting, the check last


def _shape_rank(shape_key: str) -> int:
    """Chains (1xN) before pieces (Nx1), at every length."""
    return 0 if shape_key.split("x")[0] == "1" else 1


def _arm_order(key: str) -> Tuple[Any, ...]:
    """Sort key of a Study 1 item-16 key ('haiku-low 1x6'): the ordinary settings by model and effort, then the special ones."""
    arm, sh = key.split(" ")
    name, model, effort = STUDY1_ARMS[arm]
    if arm in SPECIAL_ARMS:
        return (1, SPECIAL_ARMS.index(arm), 0, 0, _shape_rank(sh))
    return (0, MODEL_ORDER.index(model), EFFORT_ORDER.index(effort), 0, _shape_rank(sh))


def _tag_order(key: str) -> Tuple[Any, ...]:
    """Sort key of a Study 1b item-16 key ('hl 1x6'): model, effort, shape."""
    tag, sh = key.split(" ")
    name, model, effort = STUDY1B_TAGS[tag]
    return (MODEL_ORDER.index(model), EFFORT_ORDER.index(effort), _shape_rank(sh))


def _topup_order(key: str) -> Tuple[Any, ...]:
    part, sh = key.split(" ")
    return (TOPUP_ORDER.index(part), _shape_rank(sh))


def _item16_rows(S: Store, run_label: str, source: str, base: str, arm_name, shape_of, items: Sequence[str]) -> List[List[Cell]]:
    rows = []
    for k in items:
        name, sh = arm_name(k)
        rows.append([label(run_label), made_name(name, is_made(S, source, kj(base, k))), label(shape(sh)),
                     integer(S.ref(source, kj(base, k, "designed_calls"))),
                     integer(S.ref(source, kj(base, k, "missing", "count"))),
                     integer(S.ref(source, kj(base, k, "truncations", "count"))),
                     sum_dict(S.ref(source, kj(base, k, "refusals_by_category")))])
    return rows


TOPUP_PARTS = {"c13": "Step voting on pieces", "e2_aggregator": "Haiku team, aggregator",
               "e2_helpers": "Haiku team, helper draws", "e2_planner": "Haiku team, planner",
               "h_pick8": "Haiku picker", "same_model": "Drift check"}


def _calls_in(S: Store, source: str, base: str, count_key: str = "designed_calls") -> int:
    """The raw sum of a block's per-arm call counts (for the check against the spend log only; never printed)."""
    return sum(int(S.get(source, kj(base, k, count_key))) for k in S.keys(source, base))


def _spend_calls(S: Store, run: str) -> int:
    n = [n for n, r in _spend_rows(S) if r == run]
    if len(n) != 1:
        raise KeyMissing(f"spend log: {len(n)} rows for {run}")
    return int(str(S.get("spend_log", join_key(f"L{n[0]}", "Calls"))).replace(",", ""))


def _completeness_panel(S: Store) -> Table:
    cols = ["Run", "Setting", "Shape", "Designed calls (calls made where marked)", "Missing", "Truncations", "Refusals"]
    rows: List[List[Cell]] = []
    # Study 1 (item 16): the settings by shape; step voting (E3) has no designed count and is listed beside them.
    m16 = "reporting.group_b.item_16.rates"
    rows += _item16_rows(S, "Main run", "main", m16, lambda k: (_arm_label(k.split(" ")[0]), k.split(" ")[1]), None,
                         sorted(S.keys("main", m16), key=_arm_order))
    # step voting, the last of the main run's rows: its figure is the calls made (MADE), and its missing count is over its chains (said
    # in the note under the same mark)
    e3 = "reporting.group_b.item_16.e3"
    if not is_made(S, "main", e3):
        raise ValueError("TAB-17: step voting's entry no longer says its count is over the calls actually made: rewrite the note on '*'")
    rows.append([label("Main run"), made_name(_arm_label("e3"), True), label(shape("1x6")),
                 integer(S.ref("main", f"{e3}.calls_made")), integer(S.ref("main", f"{e3}.missing_chains.count")),
                 integer(S.ref("main", f"{e3}.truncations.count")), sum_dict(S.ref("main", f"{e3}.refusals_by_category"))])
    # Study 1b (item 16): every set (16, 12 and 6 steps) and setting that was sent, then the trial round, which item 16 leaves out.
    b16 = "descriptive.format_refusals_truncations_missing.item_16_rates"
    starts: List[int] = []                                   # row groups (section 7.7): each Study 1b set, its trial round, the top-up
    for setid in S.keys("s1b", b16):
        starts.append(len(rows))
        rows += _item16_rows(S, STUDY_1B, "s1b", kj(b16, setid), lambda k: (tag_name(k.split(" ")[0]), k.split(" ")[1]), None,
                             sorted(S.keys("s1b", kj(b16, setid)), key=_tag_order))
    trial = S.ref("s1b", "trial_round.calls")
    if trial.value != S.get("s1b", "records.trial_round_ignored"):
        raise ValueError("Study 1b: the trial round's calls are not the records' trial_round_ignored")
    starts.append(len(rows))
    rows.append([label(STUDY_1B), label("Trial round (all its settings; answers never scored)"), DASH, integer(trial), DASH, DASH, DASH])
    # Top-up (item 16 rules): the planner, helpers and aggregator of the Haiku team, the picker, step voting and the drift check.
    t16 = "format_refusals_truncations_missing.rates"
    starts.append(len(rows))
    rows += _item16_rows(S, "Top-up", "topup", t16, lambda k: (TOPUP_PARTS[k.split(" ")[0]], k.split(" ")[1]), None,
                         sorted(S.keys("topup", t16), key=_topup_order))
    # Each run's rows must add up to its spend-log calls (a check; the sums are not printed).
    got = {"main-l14n6-1": _calls_in(S, "main", m16) + int(S.get("main", f"{e3}.calls_made")),
           "study1b-1": sum(_calls_in(S, "s1b", kj(b16, setid)) for setid in S.keys("s1b", b16)) + int(trial.value),
           "topup-1": _calls_in(S, "topup", t16)}
    for run, n in got.items():
        if n != _spend_calls(S, run):
            raise ValueError(f"completeness panel: {run} rows add up to {n} calls, the spend log says {_spend_calls(S, run)}")
    notes = [[label("Counts are over the designed calls. *: step voting (in the main run, and on pieces in the top-up) and the "
                    "Haiku team's helper draws are adaptive and have no designed count, so their figure is the calls actually made (each "
                    "analysis file's label says so). Step voting's missing count in the main run is over its chains.")],
             [joined(label("Study 1b's trial round is outside item 16: the analysis file stamps its calls, tokens and costs only (dashes), "
                           "and its records leave out"), integer(S.ref("s1b", "records.trial_round_ignored")),
                     label("trial-round calls. With the trial round, each run's rows add up to the calls in its row of the main panel."))],
             [label("Refusals are the sum of the analysis file's category counts; an empty list sums to zero.")]]
    caption = {"tier": [plan_label(S, "TAB-17")], "study": [label("Study 1, Study 1b and the top-up, each from its own analysis file")],
               "n": [label("calls per setting, as designed (calls made, for the adaptive designs marked \"(made)\")")]}
    # 87 rows of seven short columns: a long table (it breaks across pages under a repeated header)
    return Table([label(c) for c in cols], rows, notes, caption, layout="longtable", groups=sorted(set(starts)))


@output("TAB-17")
def tab_17(S: Store) -> Table:
    cols = ["Run", "Part", "Date", "Calls", "Refusals", "Truncations", "Missing", "Raw spend (USD)",
            "Raw total to date (USD)", "Billing-rule total to date (USD)", "Console used before (USD)", "Console used after (USD)"]
    rows: List[List[Cell]] = []
    for n, run in _spend_rows(S):
        if run not in RUN_PART:
            raise KeyMissing(f"spend-log run {run!r} has no part label: add it to RUN_PART")
        r = lambda col: cell_ref(S, "spend_log", n, col)  # noqa: E731
        rows.append([text_of(r("Run ID")), label(RUN_PART[run]), text_of(r("Date")), integer(r("Calls")),
                     _count(S, n, run, "refusals"), _count(S, n, run, "truncations"), _count(S, n, run, "missing"),
                     num(r("USD (computed)"), dp=2),
                     _cut(S, n, run, RUN_RAW_TOTAL, 2), _cut(S, n, run, RUN_B5_TOTAL, 2),
                     _cut(S, n, run, RUN_CONSOLE_BEFORE, None), _cut(S, n, run, RUN_CONSOLE_AFTER, None)])
    # Study 1b's post-run ledger totals are recorded in the register (D-109 note), not in its spend-log row: fill that row from there.
    d109 = line_of(S, "register", r"^\| D-109 \|", expect=1)
    note = cell_ref(S, "register", d109, "Notes")
    for row, (n, run) in zip(rows, _spend_rows(S)):
        if run == "study1b-1":
            row[8] = extract(note, r"Spent ([\d.]+) raw", dp=2)
            row[9] = extract(note, r"about \$([\d.]+) under B5")
    cent = _within_one_cent(S, note)
    # The all-runs total: the summary table's raw figure and the billing-rule figure the last row records.
    summ = line_of(S, "spend_log", r"^\| Spent \(rows below\) \|", expect=1)
    last = [(n, run) for n, run in _spend_rows(S) if run == "topup-1"][0][0]
    # The total row is not a run's row: a date, a run's own spend and the Console's readings do not apply to it, so those cells are empty,
    # not dashes (a dash means a run's row does not state the figure, Edith, proof 4, S6).
    rows.append([label("All runs"), label("Total"), EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
                 num(cell_ref(S, "spend_log", summ, "USD"), dp=2),
                 extract(cell_ref(S, "spend_log", last, "Notes"), r"raw [\d.]+, B5 ([\d.]+)", dp=2), EMPTY, EMPTY])
    # Study 1b's note names the record in plain words (PO-1): the ruling on its data stamp, whose note holds the post-run reading.
    s1b_note = _seq("Study 1b's totals are read from the note on its post-run Console reading, kept with",
                    ruling(S, "our ruling on Study 1b's data stamp",
                           ("D-109", r"^\*\*(A public data stamp for Study 1b) before its results are opened\*\*")),
                    guard(note, r"Also (the post-run Console reading): credits", "the ruling's note holds the post-run Console reading"),
                    "; the other rows' are from their own rows in our cost records. The Console reports whole cents.")
    notes = [
        [label("A dash means the run's row in our cost records does not state that figure; an empty cell means the figure does not apply "
               "to the total. Dollar columns are rounded to whole cents, as the Console reports them; the notes give more decimals where "
               "a check needs them.")],
        [label("Raw spend is the figure from our per-call cost records: every call priced from its logged usage at the price paid (Batch "
               "calls at half of list price), refusals included. The billing rule bills a refusal that stopped before any output at "
               "zero, so its total is a little lower where such refusals exist.")],
        [label("Totals to date and the Console's after-run reading are cumulative over the runs up to and including the row. The "
                "before-run reading covers the earlier runs only, so it checks the spend of all earlier runs.")],
        [s1b_note],
        _console_before_note(S),
        cent,
    ]
    caption = {"tier": [plan_label(S, "TAB-17")], "study": [_logged_runs_caption(S)],
               "n": [label("calls as logged per run")],
               "price": [label("US dollars at the price paid (Batch at half of list price). Raw spend and raw totals: from our per-call "
                               "cost records. Billing-rule total: the same, with refusals that stopped before any output at zero. "
                               "Console: the 'used' figure read from the vendor's dashboard and recorded with each run")]}
    # the total is a row group of its own (Edith's polish standard, section 7.7): a gap above the "All runs" row
    return Table([label(c) for c in cols], rows, notes, caption, layout="landscape", groups=[len(rows) - 1], spaced=True,
                 panels=[("Completeness by setting (analysis files, item 16)", _completeness_panel(S))])


def _logged_runs_caption(S: Store) -> Cell:
    """The caption's study fact: every spend-log row, including the unbilled first smoke run and the bookkeeping row with no call."""
    def row_of(rid: str) -> int:
        return line_of(S, "spend_log", rf"^\| \d{{4}}-\d\d-\d\d \| \w+ \| {re.escape(rid)} \|", expect=1)
    s1, mk = row_of("smoke-1"), row_of("smoke-2 (markers)")
    if not re.search(r"^Not billed", str(S.get("spend_log", join_key(f"L{s1}", "Notes")))):
        raise ValueError("TAB-17: smoke-1's spend-log row no longer says it was not billed")
    if not re.search(r"^Bookkeeping only", str(S.get("spend_log", join_key(f"L{mk}", "What ran")))):
        raise ValueError("TAB-17: the markers row no longer says it is bookkeeping only")
    return _seq("every logged run (one row per run in our cost records), in time order, including",
                text_of(cell_ref(S, "spend_log", s1, "Run ID")), "(",
                extract(cell_ref(S, "spend_log", s1, "What ran"), r"(rejected by the API)"), "; not billed) and the bookkeeping row",
                text_of(cell_ref(S, "spend_log", mk, "Run ID")), ", with", integer(cell_ref(S, "spend_log", mk, "Calls")), "calls")


def _console_before_note(S: Store) -> List[Cell]:
    """The before-run Console figures are the spend log's 'used' readings. For the main run that figure is the credit less the credits
    left; the same dashboard reading's own 'Spend this month' (quoted in register D-94's note) can differ by a cent. Both are read; the
    build stops unless the spend log's figure is the credit less the credits left. The register row is named in plain words (PO-1),
    its id kept in the sources."""
    n = [n for n, run in _spend_rows(S) if run == "main-l14n6-1"][0]
    con = cell_ref(S, "spend_log", n, "Console check")
    left = extract(con, r"Console dashboard \$([\d.]+) credits / \$[\d.]+ used")
    used = extract(con, r"Console dashboard \$[\d.]+ credits / \$([\d.]+) used")
    d94 = cell_ref(S, "register", reg_line(S, "D-94"), "Notes")
    month = extract(d94, r"\"Spend this month \$([\d.]+) of \$\d+ limit\"")
    credit = extract(d94, r"\"Spend this month \$[\d.]+ of \$(\d+) limit\"")
    if abs(float(credit.raw) - float(left.raw) - float(used.raw)) > 1e-9:
        raise ValueError("TAB-17: the main run's before-run 'used' figure is not the credit less the credits left")
    if extract(d94, r"\"Organization credits \$([\d.]+)\"").raw != left.raw:
        raise ValueError("TAB-17: register D-94's reading is not the spend log's before-run reading")
    return [_seq("Console readings are the 'used' figures recorded with each run. Before the main run, that figure (",
                 used, ") is the credit of", credit, "less the", left, "left; the same dashboard reading's 'Spend this month' read",
                 month, "(quoted with", ruling(S, "our rulings before the main run", ("D-94", RULE_D94)), ").")]


ONE_CENT = 0.01


def _at_most_4(c: Cell) -> Cell:
    """A cut decimal as recorded, or rounded to four places (half away from zero) if it is recorded to more."""
    got = str(c.raw)
    if "." not in got or len(got.split(".")[1]) <= 4:
        return c
    return Cell(fmt_fixed(got, 4), raw=c.raw, refs=c.refs, formula=f"{c.formula}; rounded to 4 places")


def _within_one_cent(S: Store, d109_note: Ref) -> List[Cell]:
    """The 'within one cent' note: each Console reading after a run against the billing-rule total to date in the same row, as each
    record states it, a figure recorded to more than four decimals rounded to four (settlement E-14 quotes the top-up's as 104.1353).
    Every printed figure is cut from its record; the build stops if a pair is more than one cent apart, or if the raw total after the
    top-up is not (the note says so). The checks use the recorded figures, not the rounded ones."""
    parts: List[Any] = ["Within one cent: each Console reading after a run agrees with the billing-rule total to date within one cent "
                        "(billing-rule total against the Console's used figure, as each record states it; a figure recorded to more "
                        "than four decimals is rounded to four):"]
    last_con = None
    pairs = [(n, run) for n, run in _spend_rows(S) if run in RUN_CONSOLE_AFTER]
    for i, (n, run) in enumerate(pairs):
        con = _cut(S, n, run, RUN_CONSOLE_AFTER, None)
        b5 = extract(d109_note, r"about \$([\d.]+) under B5") if run == "study1b-1" else _cut(S, n, run, RUN_B5_TOTAL, None)
        if abs(float(con.raw) - float(b5.raw)) > ONE_CENT + 1e-9:
            raise ValueError(f"{run}: billing-rule total {b5.raw} and Console {con.raw} are more than one cent apart")
        parts += [text_of(cell_ref(S, "spend_log", n, "Run ID")), _at_most_4(b5), "against", _at_most_4(con),
                  ";" if i < len(pairs) - 1 else "."]
        last_con = (n, run, con)
    n, run, con = last_con
    raw = _cut(S, n, run, RUN_RAW_TOTAL, None)
    if abs(float(con.raw) - float(raw.raw)) <= ONE_CENT:
        raise ValueError(f"{run}: the raw total {raw.raw} is within one cent of the Console; the note would be wrong")
    mk = line_of(S, "spend_log", r"^\| \d{4}-\d\d-\d\d \| \w+ \| smoke-2 \(markers\) \|", expect=1)
    parts += ["The raw total to date after", text_of(cell_ref(S, "spend_log", n, "Run ID")), ",", _at_most_4(raw),
              ", is more than one cent above that reading: it also prices the",
              extract(cell_ref(S, "spend_log", mk, "What ran"), r"for its (\w+) zero-output `cyber` refusals"),
              "zero-output setup-check refusals that the vendor does not bill (row", text_of(cell_ref(S, "spend_log", mk, "Run ID")), ")."]
    return [_seq(*parts)]


# ================================================================ TAB-19: deviations and disclosed changes

DEC = "Decision (plain)"
# What the rulings before the main run (D-94) are, in the register's own words (the plain-words name below rests on it).
RULE_D94 = r"^(The user's rulings before the main run) main-l14n6-1"


def reg_line(S: Store, did: str) -> int:
    """The register line of one decision (found by its id at the start of the row)."""
    return line_of(S, "register", rf"^\| {re.escape(did)} \|", expect=1)


def reg_id(S: Store, did: str) -> Cell:
    return text_of(cell_ref(S, "register", reg_line(S, did), "ID"))


def reg_date(S: Store, did: str) -> Cell:
    return text_of(cell_ref(S, "register", reg_line(S, did), "Date"))


def reg_cut(S: Store, did: str, col: str, rx: str, dp: Optional[int] = None) -> Cell:
    return extract(cell_ref(S, "register", reg_line(S, did), col), rx, dp=dp)


def ruling(S: Store, words: str, *rules: Tuple[str, str]) -> Cell:
    """One or more rulings in plain words (PO-1: no decision id prints; the register is not released). `words` prints; for each
    (id, regex) the register's id cell and the decision text the words rest on (the regex, one group, on the row's 'Decision (plain)'
    cell) are kept in the cell's sources without being printed, and the build stops if that text no longer matches."""
    parts: List[Any] = [words]
    for did, rx in rules:
        n = reg_line(S, did)
        parts += [unprinted(text_of(cell_ref(S, "register", n, "ID")), "the ruling's internal decision number"),
                  guard(cell_ref(S, "register", n, DEC), rx, f"{did} is among what '{words}' names")]
    return _seq(*parts)


def _seq(*parts: Any) -> Cell:
    """Typed text (str) and cut/read cells joined into one printed cell, keeping every part's source. A space goes between parts,
    except before , ; : . ) and after (."""
    cells = [label(p) if isinstance(p, str) else p for p in parts]
    out = ""
    for c in cells:
        if not c.printed:
            continue
        if out and not (c.printed[0] in ",;:.)" or out.endswith("(")):
            out += " "
        out += c.printed
    refs = tuple(r for c in cells for r in c.refs)
    if not refs:
        return label(out)
    return Cell(out, raw=[c.raw for c in cells if c.kind == "num"], refs=refs,
                formula="; ".join(c.formula for c in cells if c.formula) or None)


def _lock_row(S: Store, k: int) -> int:
    """The line of lock k's row in the settlement's lock-proof table (tag, public proof and next paid data, in UTC)."""
    return line_of(S, "settlement_g4", rf"^\s*\| {k} \| \d\d-\d\d \d\d:\d\d:\d\d \|", expect=1)


def _lock_cell(S: Store, k: int, col: str) -> Ref:
    return cell_ref(S, "settlement_g4", _lock_row(S, k), col)


def _spend_line(S: Store, run: str) -> int:
    return line_of(S, "spend_log", rf"^\| \d{{4}}-\d\d-\d\d \| \w+ \| {re.escape(run)} \|", expect=1)


def _hours_of_main_start(S: Store) -> Cell:
    """The number of hours from the main run's start to the end of its original 48-hour window, which the top-up started inside
    (Edith, proof 3, p. 40: the paper's word for a run window is 'run', so a cell says 'within 48 hours of the main run's start', not
    'inside the 48-hour window'; TAB-19's top-up row and TAB-22 use it alike). The register's ruling on the top-up's own run gives the
    hours and the time they ended; the build stops unless that is the hours after the main run's first invocation (the spend log), to
    the minute, so 'of the main run's start' is the record's own meaning."""
    dec = cell_ref(S, "register", reg_line(S, "D-99"), "Decision (plain)")
    hours = extract(dec, r"main run's (\d+)-hour window closes \(\d\d-\d\d \d\d:\d\d UTC\)")
    closes = extract(dec, r"main run's \d+-hour window closes \((\d\d-\d\d \d\d:\d\d) UTC\)")
    n = [n for n, run in _spend_rows(S) if run == "main-l14n6-1"][0]
    start = extract(cell_ref(S, "spend_log", n, "What ran"), r"INVOCATION (\d{4}-\d\d-\d\dT\d\d:\d\d):\d\dZ; one invocation")
    due = datetime.strptime(str(start.raw), "%Y-%m-%dT%H:%M") + timedelta(hours=int(hours.raw))
    if due.strftime("%m-%d %H:%M") != closes.raw:
        raise ValueError(f"the main run's {hours.raw} hours end at {closes.raw}, not {hours.raw} hours after its first invocation {start.raw}")
    return Cell(hours.printed, raw=hours.raw, refs=hours.refs + closes.refs + start.refs,
                formula=f"{hours.formula}; the build checks that the stated close ({closes.raw}) is this many hours after the "
                        f"main run's first invocation ({start.raw})")


def _stamp_guards(S: Store, driver: Optional[Cell] = None) -> List[Cell]:
    """The main run's public analysis stamp, as the records give it: it names the reporting-definitions commit and (when `driver` is
    given) the driver commit our list names, and its gist came after collection ended and before any result was opened. Unprinted
    guards for the typed clauses that name the stamp."""
    defs = cell_ref(S, "settlement_g4", line_of(S, "settlement_g4", r"^\s*\"Reporting definitions and inventory commit \(SHA-1\): ", expect=1))
    when = cell_ref(S, "settlement_g4", line_of(S, "settlement_g4", r"after collection ended \(\d\d:\d\d:\d\dZ\) and before any result was "
                                                                      r"opened\.$", expect=1))
    out = [guard(defs, r"^\"(Reporting definitions and inventory commit) \(SHA-1\): [0-9a-f]{40}\"", "the stamp names the definitions"),
           guard(when, r"(after collection ended) \(\d\d:\d\d:\d\dZ\) and before any result was opened\.$",
                 "the stamp came after collection ended and before any result was opened")]
    if driver is not None:
        st = cell_ref(S, "log", line_of(S, "log", r"^## \S+ \(\w+\) — ANALYSIS STAMP posted \(D-\d+\): driver [0-9a-f]{7} \+", expect=1))
        got = extract(st, r"driver ([0-9a-f]{7}) \+")
        if got.raw != driver.raw:
            raise ValueError(f"TAB-19: the analysis stamp's driver {got.raw} is not our list's {driver.raw}")
        out.append(unprinted(got, "the stamp names the converter and driver commit"))
    return out


# The "Where reported" pointers, as Vision gives them for the paper's numbered sections (proof 2, Edith's page log rows for pp. 19-20; Vision's
# Method numbering: 3.1 The puzzles, 3.2 Models, effort and settings, 3.3 The runs, 3.4 Cost-matched votes and scoring, 3.5 Statistics,
# 3.6 Fixed in advance, and the release): each row points to a section or an appendix that exists, an appendix subsection by its title in
# parentheses after its letter (Appendix B is the method details, E the effort and length; 'Changes to the locked plans' summarises each
# row). An output id becomes a numbered reference ("Table TAB-03"). These are the paper's own wording (the paper's Table 5 prints them as
# they stand); the supplement's full table prints each section of the paper as "Section N of the paper" (the supplement's own rule, in its
# introduction, since it has sectioning of its own and its converter does not rewrite table cells): see where_full().
_CHANGES = "Appendix B (Changes to the locked plans)"
WHERE = {
    "deviation 1": "Section 3.3; Section 4.1, where Tests 1–5 are first reported; Appendix B",
    "deviation 2": "Section 3.4; Appendix E (Deviation 2 and the length curve); Table TAB-03",       # Vision moved Deviation 2 into 3.4 (OR-11 b)
    "amendment 1": _CHANGES + "; Table TAB-13",
    "changes": _CHANGES,
    "post-lock code": _CHANGES + "; Table TAB-23",
    "reporting definitions": "Appendix B (Locks and public fingerprints; Changes to the locked plans)",
}


# A paper section or appendix named in a pointer: "Section 3.3", "Appendix B".
_PAPER_PART = re.compile(r"\b(Section \d+(?:\.\d+)*|Appendix [A-Z])\b")


def where_full(pointer: str) -> str:
    """The supplement's form of a paper pointer: each section or appendix of the paper followed by "of the paper" (the supplement's
    introduction: sections of the paper are cited as "Section N of the paper"), so a reader of the supplement does not take it for
    one of the supplement's own."""
    return _PAPER_PART.sub(r"\1 of the paper", pointer)


def _where(key: str) -> Cell:
    """The full table's "Where reported" cell for a WHERE key."""
    return label(where_full(WHERE[key]))


# The supplement's form back to the paper's own wording, for the paper's version (which prints the pointers as WHERE gives them).
_WHERE_PAPER = {where_full(v): v for v in WHERE.values()}
assert len(_WHERE_PAPER) == len(WHERE), "two WHERE pointers read alike in the supplement's form"


# The most lines a cell of the full TAB-19 may run to, in the writer's wrap estimate. The longest cell, Amendment 1's Change, estimates 14
# and typesets 14; the next longest typeset 12 (Top-up start's and Post-lock code's Trigger), 11 and 10, so Edith's 8-10 lines is missed
# (to be put to her). Seven text columns cannot do better with one shared set of widths on a 9.0 in page: 10 lines would need about 8.5 in
# of text columns where 7.7 in are left, and 12 lines fit only with widths set by hand, which core's split_tables does not honour (it
# plans the shared widths itself). Edith (proof 4, rulings of 2026-10-20): cells of 18-25 lines (the upright table) are a readability
# fault; the build stops if the table's own text ever makes a cell longer than the sideways layout's.
MAX_CELL_LINES = 14


def _longest_cell(t: Table) -> int:
    """The most lines any cell of a table to be split by rows runs to at the one set of column widths its parts share (the writer's own
    estimate, `_width_plan` on a sideways page; the header excluded)."""
    idx = list(t.split_key) + [j for j in range(len(t.columns)) if j not in t.split_key]
    full = Table([t.columns[j] for j in idx], [[r[j] for j in idx] for r in t.rows], layout="landscape", font=t.font)
    specs, w, _ = _width_plan(full)
    return max(_wrapped_lines(_pieces(c, t.font), (w[j] - 0.04) * PT_PER_IN) for r in full.rows for j, c in enumerate(r) if specs[j] is None)


@output("TAB-19")
def tab_19(S: Store) -> Table:
    cols = ["Item", "Ruling or record", "Date", "Change", "Trigger", "Data existing at the time", "Where reported"]
    rows: List[List[Cell]] = []
    # The paper version's own cells, where they differ from the full table's, by (item, paper column): built here from the same records
    # (each says less than its full cell, never something else; every source it cites is one its full row cites, checked).
    paper: Dict[Tuple[str, str], Cell] = {}

    # --- Deviation 1: the number of steps per puzzle (spec Amendments; D-86)
    d1 = cell_ref(S, "spec1", line_of(S, "spec1", r"^### Deviation 1 \(", expect=1))
    steps_before = extract(cell_ref(S, "spec1", line_of(S, "spec1", r"\) fixed \d+-step puzzles", expect=1)), r"fixed (\d+)-step puzzles")
    n_chosen = extract(cell_ref(S, "spec1", line_of(S, "spec1", r"^\*\*1\. N = \d+ \(preset", expect=1)), r"N = (\d+)")
    # The Haiku-only effort diagnostic ran before D-86 and D-86 cites its result (the deviation note cites the diagnostic too).
    diag = line_of(S, "spend_log", r"^\| \d{4}-\d\d-\d\d \| \w+ \| diag-haiku-effort-1 \|", expect=1)
    diag_date = cell_ref(S, "spend_log", diag, "Date")
    if not str(diag_date.value) <= str(reg_date(S, "D-86").raw):
        raise ValueError("TAB-19: the effort diagnostic's spend-log date is not on or before D-86's")
    rows.append([label("Deviation 1"),
                 _seq(ruling(S, "Our ruling on shorter puzzles (a disclosed deviation)",
                             ("D-86", r"\*\*(declared deviation \(shorter puzzles\))\*\*")),
                      "; spec Amendments, heading", extract(d1, r"^### (Deviation 1) ")),
                 reg_date(S, "D-86"),
                 _seq("Puzzle length moved from", steps_before, "steps to", n_chosen,
                      "steps; the new length was picked by a Haiku-only rule fixed before the length sweep ran"),
                 _seq("Pilot 1 scored Haiku-medium at about zero at every preset, so the pre-registered preset rule returned the decision to us",
                      guard(cell_ref(S, "register", reg_line(S, "D-86"), DEC),
                            r"\((pilot-ledger-1 returned to the user): Haiku-medium whole-answer about", "the preset rule returned the decision")),
                 _seq("Pilot 1 had run; its Haiku results were read and its Opus and Sonnet answers and scores were still sealed; the Haiku-only "
                      "effort diagnostic had run and was read",
                      unprinted(text_of(diag_date), "the diagnostic's run date, on or before the ruling's"),
                      guard(cell_ref(S, "register", reg_line(S, "D-86"), "Notes"), r"`ops/reviews/[\d-]+-(diag-haiku-effort-1)-result\.md`",
                            "the ruling cites the diagnostic's result"),
                      "; no length-sweep, main-run or later data"),
                 _where("deviation 1")])

    # --- Deviation 2: the marking rule for repeated step lines (D-90)
    d2 = cell_ref(S, "spec1", line_of(S, "spec1", r"^### Deviation 2 \(", expect=1))
    what2 = cell_ref(S, "spec1", line_of(S, "spec1", r"^> \*\*What happened\.\*\* In the ladder, Sonnet-medium often wrote every step line", expect=1))
    hit2 = cell_ref(S, "spec1", line_of(S, "spec1", r"^> with identical balances, before its Answer line\. At the chosen \d+ steps this marked", expect=1))
    rows.append([label("Deviation 2"),
                 _seq(ruling(S, "Our ruling on the marking rule (a disclosed deviation)",
                             ("D-90", r"^\*\*Declared Deviation 2 \((marking rule)\), before any main-run data:\*\*")),
                      "; spec Amendments, heading", extract(d2, r"^### (Deviation 2) ")),
                 reg_date(S, "D-90"),
                 label("A step line written more than once with identical balances is accepted; a repeat with different balances still fails; "
                       "the same rule for every model"),
                 _seq("Sonnet-medium's length-sweep replies", extract(what2, r"Sonnet-medium (often) wrote every step line"),
                      "repeated every step line, which the old rule marked wrong even when every value was right (at the chosen",
                      extract(hit2, r"At the chosen (\d+) steps this marked"), "steps,",
                      extract(hit2, r"steps this marked (\d+ of its \d+ chain answers) wrong"), ")"),
                 label("The length sweep had run and its Sonnet and Opus replies were read after the Haiku-only pick was committed; no main-run data"),
                 _where("deviation 2")])

    # --- Amendment 1: the values the pre-set rules chose after the length sweep
    a1 = cell_ref(S, "spec1", line_of(S, "spec1", r"^### Amendment 1 \(", expect=1))
    four = extract(cell_ref(S, "findings", line_of(S, "findings", r"^\*\*5\.6 Amendment 1's \w+ disclosures", expect=1)),
                   r"Amendment 1's (\w+) disclosures")
    same = extract(cell_ref(S, "spec1", line_of(S, "spec1", r"^  - Haiku's and Opus's numbers are the same, apart from", expect=1)),
                   r"^- (Haiku's and Opus's numbers are the same, apart from) ")
    # Pilot 1's 24-step marker, as TAB-13's Pilot 1 panel prints it (mean and stamped 95% interval, in %); Pilot 1's 24-step results
    # are exploratory.
    pb = "pilot1.om.l14_to_l16"

    def marker(src: str) -> Cell:
        if S.get(src, f"{pb}.ci95.0") == S.get(src, f"{pb}.ci95.1"):
            raise ValueError(f"TAB-19: {src} {pb} has a collapsed interval; print free analysis 4's exact one as TAB-13 does")
        # two decimals, as TAB-13's Pilot 1 panel prints these values ("94.00 [88.00, 98.00]"): a note that quotes a cell prints it as the cell
        # does (Edith, proof 4, supplement precision)
        return joined(joined(pct(S.ref(src, f"{pb}.mean"), dp=2), label("%"), sep=""),
                      interval(*ci_refs(S, src, f"{pb}.ci95"), dp=2, scale=100.0, bounds=(100.0,)))
    # The paper's version: the same claims without the quoted line and the marker's numbers (TAB-13 prints them; the paper's body
    # says "one of its lines" too), so no quotation marks and no percentages print in the cell.
    paper[("Amendment 1", "Change")] = _seq(
        "Filled in only the values the locked rules chose after the length sweep, plus", four,
        "disclosures; no test added and no rule changed. One of its lines", unprinted(same, "the line, which the full table quotes"),
        "understates what moved under Deviation 2's rule (TAB-13) and is corrected as a disclosed erratum", *_erratum_guards(S))
    rows.append([label("Amendment 1"), _seq("spec Amendments, heading", extract(a1, r"^### (Amendment 1) ")),
                 extract(a1, r"\((\d{4}-\d\d-\d\d)\)"),
                 _seq("Filled in only the values the locked rules chose after the length sweep, plus", four,
                      "disclosures; no test added and no rule changed. Its line", joined(label("'"), same, label(" …'"), sep=""),
                      "understates what moved under Deviation 2's rule (among them Pilot 1's Opus-medium 24-step marker, exploratory, with "
                      "95% intervals:", marker("curve"), "under the original rule,", marker("curve_d90"),
                      "under Deviation 2; TAB-13) and is corrected as a disclosed erratum", *_erratum_guards(S)),
                 label("The length sweep: its pre-set rules chose the values"),
                 label("Length-sweep data; the pick was committed on Haiku data before any Opus or Sonnet length-sweep answer was opened; no main-run data"),
                 _where("amendment 1")])

    # --- The main-run rules (D-94). The expiry D-94(2) names ("the 10-13 expiry") is the main-run clearance's, not the credit's:
    # the date is read from the clearance and must end in D-94's month-day.
    exp_line = cell_ref(S, "clr_main", line_of(S, "clr_main", r"^- The clearance expires at the end of \d{4}-\d\d-\d\d UTC\.", expect=1))
    exp_date = extract(exp_line, r"expires at the end of (\d{4}-\d\d-\d\d) UTC")
    d94_exp = reg_cut(S, "D-94", DEC, r"could pass the (\d\d-\d\d) expiry")
    if not exp_date.raw.endswith("-" + d94_exp.raw):
        raise ValueError(f"TAB-19: D-94's expiry {d94_exp.raw} is not the main-run clearance's {exp_date.raw}")
    # The paper's version names neither the cap's amount (no "$" in a cell; the body does not give it either) nor the archive service
    # (the anonymous build's scan refuses its name): "Zenodo v3" is lock 3's archive record, which the ruling's own sentence says.
    # The pause is named in the body's words ("the pause on truncated replies", the appendix's 'Changes to the locked plans').
    paper[("Main-run rules", "Change")] = _seq(
        "A hard spending cap replaced the pre-registered multiple of the projected cost; the pause on truncated replies was kept; the "
        "run was allowed to start before Lock 3's archive record was published",
        unprinted(reg_cut(S, "D-94", DEC, r"the (\$\d+) cap"), "the cap's amount, which the full table prints"),
        guard(cell_ref(S, "register", reg_line(S, "D-94"), DEC), r"start before (Zenodo v3 is published)\*\* \(D-90's order\): lock 3's "
              r"public proof is the gist", "the run could start before Zenodo v3, lock 3's archive record, was published"))
    rows.append([label("Main-run rules"), ruling(S, "Our rulings before the main run", ("D-94", RULE_D94)), reg_date(S, "D-94"),
                 _seq("A hard cap of", reg_cut(S, "D-94", DEC, r"the (\$\d+) cap"),
                      "replaced the pre-registered multiple of the projected cost; the truncation pause was kept; the run was allowed to start before",
                      reg_cut(S, "D-94", DEC, r"start before (Zenodo v\d)")),
                 _seq("Speed: the old formula would have forced many small waves (up to about",
                      reg_cut(S, "D-94", DEC, r"would need up to ~(\d+) waves"), ") and could have run past the main-run clearance's "
                      "expiry (the end of", exp_date, "UTC);", unprinted(d94_exp, "the ruling's own expiry, the clearance's month-day"),
                      "actual spend was unaffected"),
                 label("Pilot 1, the length sweep and Lock 3 existed; no main-run data"),
                 _where("changes")])

    # --- The 12-step retry (D-108)
    # The paper's version leads with the body's name for the row ("Study 1b's 12-step point", TAB19_WORDS), so its Change cell does not
    # repeat the step count; the ruling's own count is kept unprinted (its regex requires the 12 the name prints).
    paper[("12-step retry", "Change")] = _seq(
        "A final attempt to send it after", reg_cut(S, "D-108", DEC, r"The (three) failed submits"),
        "failed submits; a disclosed deviation from the resubmit limit; descriptive only",
        unprinted(reg_cut(S, "D-108", DEC, r"at (12) steps"), "the point's step count, which the paper's row name prints"))
    rows.append([label("12-step retry"),
                 ruling(S, "Our ruling on one final 12-step attempt", ("D-108", r"^\*\*(One final attempt) of Study 1b's 12-step point")),
                 reg_date(S, "D-108"),
                 _seq("A final attempt to send Study 1b's point at", reg_cut(S, "D-108", DEC, r"at (12) steps"), "steps after",
                      reg_cut(S, "D-108", DEC, r"The (three) failed submits"),
                      "failed submits; a disclosed deviation from the resubmit limit; descriptive only"),
                 label("The earlier submits failed to upload; no batch was created and nothing was charged"),
                 label("Study 1b's other waves had returned; only counts, stop reasons and costs had been seen, no answer or score"),
                 _where("changes")])

    # --- Lock 4's lineage clarification (LOG)
    rows.append(_lineage_row(S))

    # --- The top-up start (D-110 to D-112)
    up = _spend_line(S, "topup-1")
    up_what = cell_ref(S, "spend_log", up, "What ran")
    # Edith, proof 4 (rulings of 2026-10-20): "window_check in harness/pareto/main.py records started_utc at the live start, before the first
    # batch is sent." So the time our cost records log as the top-up's "window started" is when the live run started, not its first call
    # (no record we read gives the first send's time). The build stops unless the clearance's launch line gives window.json's
    # started_utc as the same time as the cost records' window start.
    live = extract(up_what, r"window started (\d\d:\d\d:\d\dZ)")
    lau = cell_ref(S, "topup_clearance", line_of(S, "topup_clearance", r"^- \*\*The launch:\*\* INVOCATION \d\d:\d\d:\d\dZ\.", expect=1))
    own = extract(lau, r"`window\.json` started_utc \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\dZ)")
    if own.raw != live.raw:
        raise ValueError(f"TAB-19: the top-up's window.json started_utc ({own.raw}) is not its logged window start ({live.raw})")
    # No "window" in our own words (Edith, proof 3, p. 40: the paper's word for a run window is "run"; batch (g) rule E): the top-up
    # started "within 48 hours of the main run's start", the hours read and checked against the main run's first invocation.
    up_change = ["The top-up started within", _hours_of_main_start(S),
                 "hours of the main run's start by a disclosed change to the locked plan (its earliest start was brought forward)",
                 guard(cell_ref(S, "register", reg_line(S, "D-111"), DEC), r"\((not_before moved earlier), D-110\)",
                       "the disclosed change moved the not-before time earlier"),
                 guard(cell_ref(S, "register", reg_line(S, "D-112"), DEC), r"; (inside the main run's original \d+-hour window), disclosed",
                       "the run started inside the main run's original window"),
                 unprinted(own, "the run's own start record (window.json started_utc) gives the same time as the cost records' window start"),
                 "; the live run started at"]
    # The paper's version prints the time in the form of every other time it prints ("hh:mm:ss UTC"); the same stamped time, cut
    # without its "Z". The paper's cell ends in the same words as the full table's (proof 3, p. 40, and Edith's proof 4 pass search the
    # whole text for "window"); only its time takes the paper's form.
    paper[("Top-up start", "Change")] = _seq(*up_change, utc(live))
    rows.append([label("Top-up start"),
                 ruling(S, "Our rulings on the top-up's go, timing and run commit",
                        ("D-110", r"^\*\*(The user's go for the top-up run) \(`topup-1`\)"), ("D-111", r"^\*\*(Top-up timing): "),
                        ("D-112", r"so it runs at (the prepared declared-change commit) [0-9a-f]{7} \(")),
                 reg_date(S, "D-112"),
                 _seq(*up_change, utc(live)),
                 _topup_start_trigger(S, up),
                 _topup_start_data(S, up),
                 _where("changes")])

    # --- Code used after the locks (findings register 5.4)
    rows.append(_post_lock_code_row(S))

    # --- Reporting definitions written after lock 3 (findings register 5.7; D-94(4))
    f57 = cell_ref(S, "findings", line_of(S, "findings", r"^\*\*5\.7 Reporting definitions were written after lock 3", expect=1))
    items = cell_ref(S, "findings", line_of(S, "findings", r"^- Items \d+–\d+ were approved by the user \(D-94\(4\)\) before launch", expect=1))
    add_c4 = cell_ref(S, "findings", line_of(S, "findings", r"^- Addendum C, which also rewords item \d+", expect=1))
    # The later acceptance (D-134(3), 2026-10-15): the findings register's date must be the register's ruling date, the register's
    # row must say (3) accepted Addendum C, and the ruling must come after the Study 1 driver's verified run (the results were open).
    acc = r"\*\*The user accepted (Addendum C, C4 included), on (\d{4}-\d\d-\d\d) \((D-134) (\(3\))\)"
    acc_date = extract(add_c4, acc, group=2)
    if acc_date.raw != reg_date(S, "D-134").raw or extract(add_c4, acc, group=3).raw != reg_id(S, "D-134").printed:
        raise ValueError("TAB-19: findings register 5.7's acceptance is not register D-134's ruling and date")
    opened = cell_ref(S, "log", line_of(S, "log", r"^## \d{4}-\d\d-\d\d \(\w+\) — Driver's one run VERIFIED: ", expect=1))
    if not extract(opened, r"^## (\d{4}-\d\d-\d\d) ").raw < acc_date.raw:
        raise ValueError("TAB-19: the acceptance is not dated after the Study 1 driver's verified run")
    rows.append([label("Reporting definitions after Lock 3"),
                 _seq(ruling(S, "Our rulings before the main run and our later acceptance of Addendum C", ("D-94", RULE_D94),
                             ("D-134", r"(\(3\)) \*\*Addendum C accepted\*\*")),
                      unprinted(extract(f57, r"^\*\*(5\.7) "), "the section of our findings record (internal)")),
                 reg_date(S, "D-94"),
                 _seq("Reporting items", extract(items, r"^- Items (\d+–\d+) were approved"), "were approved by name in our rulings before "
                      "the main run",
                      unprinted(extract(items, r"\((D-94\(4\))\)"), "the ruling's internal number, as the findings record cites it"),
                      guard(cell_ref(S, "register", reg_line(S, "D-94"), DEC), r"\(4\) \*\*(yes to the reporting definitions), items \d+–\d+\*\*",
                            "the rulings before the main run approved the reporting items"),
                      ", after Lock 3 and before launch. Addendum C (committed before launch; it rewords", extract(add_c4, r"rewords (item \d+)"),
                      ") and Addendum C4 (committed", extract(add_c4, r"committed (about \d+ minutes) \*\*after\*\* launch"),
                      "after launch) were checked, but", extract(add_c4, r"\*\*(neither was ruled on by name)\*\*"),
                      extract(add_c4, r"\*\*neither was ruled on by name\*\* (at the time)\."), "; we accepted",
                      extract(add_c4, acc), ", on", acc_date,
                      unprinted(joined(reg_id(S, "D-134"), extract(add_c4, acc, group=4), sep=""),
                                "the acceptance's internal decision number and part"),
                      guard(cell_ref(S, "register", reg_line(S, "D-134"), DEC), r"(\(3\)) \*\*Addendum C accepted\*\*",
                            "D-134 (3) accepted Addendum C"),
                      ", after the results had been opened",
                      unprinted(extract(opened, r"^## (\d{4}-\d\d-\d\d) "), "the date of the Study 1 driver's verified run, before the acceptance")),
                 _seq("Pre-registered descriptive outputs lacked locked definitions; the definitions were written and reviewed before the main "
                      "run's public analysis stamp", *_stamp_guards(S)),
                 _seq("No main-run result had been opened when the definitions and Addendum C4 were committed; the definitions are inside the "
                      "main run's public analysis stamp; the first main-run calls were already sent when Addendum C4 was committed",
                      *_stamp_guards(S)),
                 _where("reporting definitions")])

    # Date order (Edith, proof 4, then Table 4, now Table 5: "Reporting definitions after Lock 3" came after the 2026-10-13 rows and the undated post-lock-code
    # row): it is dated 2026-10-12, like "The main run's rules", so it follows that row; the undated row stays last. The build stops if
    # the dates no longer run in order.
    names = [r[0].printed for r in rows]
    rows.insert(names.index("Main-run rules") + 1, rows.pop(names.index("Reporting definitions after Lock 3")))
    dates = [r[2].printed for r in rows if re.fullmatch(r"\d{4}-\d\d-\d\d", r[2].printed)]
    if dates != sorted(dates) or rows[-1][0].printed != "Post-lock code":
        raise ValueError(f"TAB-19: the rows are not in date order, the undated one last: {[(r[0].printed, r[2].printed) for r in rows]}")

    # The paper's version prints each pointer as the paper words it (WHERE), not the supplement's "... of the paper" form.
    for r in rows:
        if r[-1].printed not in _WHERE_PAPER:
            raise ValueError(f"TAB-19: the pointer {r[-1].printed!r} is not one of WHERE's, in the supplement's form")
        paper[(r[0].printed, "Where reported")] = label(_WHERE_PAPER[r[-1].printed])

    # Note 2 names the folder, not the file: the paper's converter turns output ids into table numbers, so an id inside a file name
    # could be rewritten. It claims only what label() enforces: a digit in typed text sits inside a name; every other digit is read.
    notes = [_dates_note(S), _commit_chain_note(S),
             [label("The change, trigger and data cells are short summaries of the records each cell cites in this table's source "
                    "file, released with the paper outputs in data/paper-outputs/; every number printed in digits (dates, times, counts, "
                    "measured values and commit IDs) is read from those records, except digits that are part of a name, such as "
                    "Lock 1, Tests 1–5, the 24-step marker, 95% intervals or a table's number.")]]
    caption = {"tier": [plan_label(S, "TAB-19")], "study": [label("Study 1, Study 1b and the top-up")]}
    # Sideways, split by rows (Edith, proof 4 rulings of 2026-10-20, ruling 4: "cells of 18-25 lines are a readability fault, and the
    # supplement has no page limit"): seven text columns are 0.9 in each at 6.5 in, 1.2 in at the 9.0 in of a sideways page. footnotesize
    # (8 pt, the floor) gives wider columns and fewer lines; the anonymous copy takes the font and the split from this table, the paper
    # version (t.main_table) is its own Table and keeps \small. Every part keeps every column at one shared set of widths and the rows
    # are cut by space (core.split_rows_by_space, as TAB-07 does). Tall wrapped rows: a little space after every row, so the reader
    # sees where a row ends (Edith §7.7, proof 2 p. 20).
    t = Table([label(c) for c in cols], rows, notes, caption, font="footnotesize", spaced=True)
    split_rows_by_space(t, [0], list(range(1, len(cols))))
    if _longest_cell(t) > MAX_CELL_LINES:
        raise ValueError(f"TAB-19: a cell runs to {_longest_cell(t)} lines at the sideways page's widths (at most {MAX_CELL_LINES})")
    t.main_table = _tab19_paper(S, t, paper)
    return t


# The paper's TAB-19 (D-159/D-160; Vision's plan §3, "Change · when · data that existed · where reported", mock-review fix #9): the full
# table's columns, minus the internal labels (the ruling-or-record column) and the trigger, which stay in the supplement's full table.
# Each row's item names its change, so the item leads the Change cell.
TAB19_PAPER = {"Change": ("Item", "Change"), "When": ("Date",), "Data that existed": ("Data existing at the time",),
               "Where reported": ("Where reported",)}
# The paper's wording, as (item, paper column, old words, new words), applied in order to the paper's cell: typed words of the full
# table's cell, never a cut; each must occur once in its cell when it is applied, and each must change a cell.
# - D-161's vocabulary: "design" for step voting (several calls a puzzle), "setting" for the rewording check (one call).
# - The batch spec's rule 4: no "declared" in a paper cell; the full table's cells already say "disclosed" where the word carries the
#   meaning (the paper's appendix corrects Amendment 1 "as a disclosed erratum").
# - The anonymous build's scan (Vision's anon.py, D-152's neutral words): Lock 4's gist is its public posting.
# - The body's words for the same things: the rows the appendix's 'Changes to the locked plans' lists as bullets lead with the
#   bullets' names ("The main run's rules", "Study 1b's 12-step point", "Lock 4's record merge", "Code written after the locks",
#   "The top-up run's start"), and Lock 4's "earliest start" (the appendix's 'The top-up run's earlier start').
TAB19_WORDS: List[Tuple[str, str, str, str]] = [
    ("Main-run rules", "Change", "Main-run rules. ", "The main run's rules. "),
    ("12-step retry", "Change", "12-step retry. ", "Study 1b's 12-step point. "),
    ("Lock 4 lineage clarification", "Change", "Lock 4 lineage clarification. ", "Lock 4's record merge. "),
    ("Lock 4 lineage clarification", "Data that existed", "Lock 4's public gist", "Lock 4's public posting"),
    ("Top-up start", "Change", "Top-up start. ", "The top-up run's start. "),
    ("Top-up start", "Data that existed", "after the disclosed change was committed", "after the change was committed"),
    ("Post-lock code", "Change", "Post-lock code. Code used in paid runs or the analysis after the locks:",
     "Code written after the locks and used in paid runs or the analysis:"),
]
# The paper's one short note (at most two printed lines): the When column's dates, with the full table's note 1's records.
TAB19_DATES = ("When: the date of our ruling or log entry (a local calendar date, not UTC) or of the pre-registration's amendment "
               "heading; a dash means no single date is stamped.")
# The digits of a printed text (a date, a time, a count, a name's number), for the check that a paper cell prints no number its full
# row does not.
_DIGITS = re.compile(r"\d+(?:[.:–-]\d+)*")


def reword(c: Cell, old: str, new: str, why: str) -> Cell:
    """A cell in the paper's wording: typed words `old`, found exactly once in the printed text, become `new` (no digit outside the
    label patterns); the cell's sources, raw values and cuts are kept, and the change is recorded in its formula."""
    if c.printed.count(old) != 1:
        raise ValueError(f"reword: {old!r} is not exactly once in {c.printed!r}")
    if not label(new).printed:
        raise ValueError("reword: empty words")
    text = c.printed.replace(old, new)
    if c.kind != "num":
        return label(text)
    return replace(c, printed=text, formula="; ".join(x for x in (c.formula, f"paper wording ({why}): {old!r} -> {new!r}") if x))


# Words the paper versions never print (D-161's vocabulary, the batch spec's rule 4, and the locked words of Edith's polish standard
# §3.1-3.2): the retired project terms, and "declared" and "significant" anywhere (in no sense, so no Holm result reads "declared").
PAPER_RETIRED = re.compile(r"\b(?:[Aa]rms?|[Tt]ry|[Tt]ries|[Bb]ase puzzles?|[Ee]qual[- ]money|[Ss]ame-model check|[Rr]un windows?|"
                           r"[Tt]iers?|[Tt]hree-way reading|[Aa]s[- ]deployed|k measured|[Ss]ignifican(?:t|tly|ce)|"
                           r"[Dd]eclar(?:e|ed|es|ing|ations?))\b")
# "non-inferior" (and "non-inferiority") prints only inside quotation marks (C-165): it is looked for after the quoted spans are cut.
NON_INFERIOR = re.compile(r"\b[Nn]on-inferior")
# A quoted span: an opening quote (not after a letter or digit), then anything but a quote, except an apostrophe inside a word
# ("Haiku's"), then a closing quote (not before a letter or digit).
QUOTED = re.compile(r"(?<!\w)['‘\"“](?:[^'’\"”]|(?<=\w)['’](?=\w))*['’\"”](?!\w)")
# The anonymous build's scan of the services' names (Vision's SERVICES, paper/tools/anon.py; D-150, D-152): a paper version that
# passes it prints the same in the named and the anonymous build, so it needs no anonymous variant.
ANON_SERVICES = re.compile(r"\bgists?\b|zenodo|wayback|web\.archive|10\.5281/", re.I)
# A straight quotation mark (Edith's polish standard §3.6: curly quotes only, and the writer has no curly opening quote): a double quote
# anywhere, or a single quote that does not follow a letter or digit (so an apostrophe, "Haiku's" or "results'", passes).
STRAIGHT_QUOTE = re.compile(r"\"|(?<![\w])'")


def paper_words_check(t: Table, where: str) -> Table:
    """The paper version's printed text (headers, cells and notes) holds no retired term or locked word (PAPER_RETIRED), no
    "non-inferior" outside quotation marks, no straight quotation mark, and no service's name that the anonymous build's scan
    refuses."""
    texts = [c.printed for cs in [t.columns, *t.rows, *t.notes] for c in cs]
    quoted = [x for x in texts if STRAIGHT_QUOTE.search(x)]
    if quoted:
        raise ValueError(f"{where}: the paper version prints straight quotation marks in {len(quoted)} text(s): {quoted[:2]}")
    bad = sorted({m.group(0) for x in texts for m in PAPER_RETIRED.finditer(x)} |
                 {m.group(0) for x in texts for m in NON_INFERIOR.finditer(QUOTED.sub(" ", x))})
    if bad:
        raise ValueError(f"{where}: the paper version prints retired or locked words {bad}")
    named = sorted({m.group(0) for x in texts for m in ANON_SERVICES.finditer(x)})
    if named:
        raise ValueError(f"{where}: the paper version names services the anonymous build's scan refuses: {named}")
    return t


def _tab19_paper(S: Store, t: Table, paper: Dict[Tuple[str, str], Cell]) -> Table:
    """TAB-19's paper version, read from the full table's cells (so every value is the full table's, at its own precision: this
    table prints dates, times and counts) or from the paper's own cells (`paper`), which tab_19 builds from the same records and which
    say less than the full cells: each cites only sources its full row cites and prints no number its full row does not. Then the
    paper's wording (TAB19_WORDS). Its note is the paper's one short note."""
    titles = [c.printed for c in t.columns]
    ix = {name: [titles.index(x) for x in parts] for name, parts in TAB19_PAPER.items()}
    items = [r[0].printed for r in t.rows]
    if (len(set(items)) != len(items) or not {i for i, _ in paper} <= set(items) or not {i for i, *_ in TAB19_WORDS} <= set(items)
            or not {c for _, c in paper} | {c for _, c, *_ in TAB19_WORDS} <= set(TAB19_PAPER)):
        raise ValueError("TAB-19: the paper version's items are not the full table's, once each, or its columns are not the paper's")
    rows: List[List[Cell]] = []
    applied = 0
    for r in t.rows:
        item = r[0].printed
        sources = {(x.source, x.key) for c in r for x in c.refs}
        digits = set(_DIGITS.findall(" ".join(c.printed for c in r)))
        out: List[Cell] = []
        for name, parts in ix.items():
            cells = [r[j] for j in parts]
            if (item, name) in paper:
                own = paper[(item, name)]
                if not {(x.source, x.key) for x in own.refs} <= sources or not set(_DIGITS.findall(own.printed)) <= digits:
                    raise ValueError(f"TAB-19: the paper's {name} for {item!r} cites a source or prints a number its full row does not")
                cells = cells[:-1] + [own]
            c = joined(*cells, sep=". ") if len(cells) > 1 else cells[0]
            for it, col, old, new in TAB19_WORDS:
                if (it, col) == (item, name):
                    c = reword(c, old, new, why="D-161 vocabulary, the batch spec's rule 4, the anonymous scan, the body's names and "
                                                 "house style")
                    applied += 1
            out.append(c)
        rows.append(out)
    if applied != len(TAB19_WORDS):
        raise ValueError("TAB-19: a paper wording changed no cell")
    if rows[items.index("Post-lock code")][1].printed != DASH.printed:
        raise ValueError("TAB-19: the post-lock code row's When is no longer the dash the dates note explains")
    # A float, not a longtable: the writer writes a plain tabular (no longtable environment and no caption placeholder), so a
    # longtable mark would print the table with no caption or label. It does not yet fit one page: at the writer's 5 cm columns it is
    # wider than the text block, and even at widths that fill the 6.5-inch line (ragged right) the nine rows run to about 1.2 pages
    # at \small. Fitting needs the writer's column widths and either shorter summaries (a content call) or a ruling that allows an
    # appendix table to run past one page (with a real longtable from the writer).
    out_t = Table([label(c) for c in TAB19_PAPER], rows, [_dates_note(S, TAB19_DATES)], t.caption, short_notes=[0], layout="longtable",
                  spaced=True)  # nine changes in words: taller than one page as a float; space after every row
    # "Where reported" wider, "Change" narrower (Edith, proof 4, then Table 4, now Table 5: the narrow column made Deviation 2's cell run 8 lines and left a
    # lone "the" in "Table S17 in / the / supplement"). The writer sizes the column from "Table 12", but the converter prints "Table S17
    # in the supplement" (or "Table S24 ...", "Table S34 ...") for each Table cell id, so the column is sized here for that longer text.
    set_widths(out_t, Change=2.35, Where_reported=1.1, Data_that_existed=1.64)
    return paper_words_check(out_t, "TAB-19 (paper)")


DATES_NOTE = ("Dates are the dates of our rulings (local calendar dates, not UTC), the spec heading's date or our log entry's date "
              "(also a local calendar date); a dash means no single date is stamped.")


def _dates_note(S: Store, words: str = DATES_NOTE) -> List[Cell]:
    """Note 1 (TP-2, worded under PO-1): the Date column's dates. Our rulings' dates (the register's Date column) are local calendar
    dates, not UTC (no time zone is named): the go for the S3 bill check is dated a day after the UTC date our cost records give its
    run (whose times are UTC). Our log's dates are local too: Lock 1's cut is logged a day after the tag's UTC date in the
    settlement's lock-proof table. The note does not name the register (PO-1: it is internal and not released)."""
    s3 = _spend_line(S, "s3-ledger-1")
    s3_what = cell_ref(S, "spend_log", s3, "What ran")
    s3_date = cell_ref(S, "spend_log", s3, "Date")
    under = extract(s3_what, r"\((D-\d+); pilot plan step \d\)")
    utc = extract(s3_what, r"(\d\d:\d\d–\d\d:\d\d) UTC;")
    go = reg_cut(S, under.raw, DEC, r"go for the S3 bill check `(s3-ledger-1)`")
    if not str(s3_date.value) < reg_date(S, under.raw).raw:
        raise ValueError("TAB-19: the S3 go is no longer dated after its run's UTC date; 'local calendar dates' rests on it")
    cut1 = cell_ref(S, "log", line_of(S, "log", r"^## \d{4}-\d\d-\d\d \(\w+\) — LOCK CUT: prereg-lock-1 ", expect=1))
    cut1_day = extract(cut1, r"^## \d{4}-(\d\d-\d\d) ")
    tag1_day = extract(_lock_cell(S, 1, "Tag (UTC)"), r"^(\d\d-\d\d) \d\d:\d\d:\d\d$")
    if not tag1_day.raw < cut1_day.raw:
        raise ValueError("TAB-19: our log's Lock 1 entry is no longer dated after the tag's UTC date")
    why = "the dates are local: "
    return [_seq(words,
                 unprinted(text_of(s3_date), why + "the S3 run's UTC date"), unprinted(utc, why + "the S3 run's UTC times"),
                 unprinted(under, why + "the ruling the run went under"), unprinted(go, why + "the ruling is the go for that run"),
                 unprinted(reg_date(S, under.raw), why + "the go's later date"),
                 unprinted(tag1_day, why + "Lock 1's tag date, UTC"), unprinted(cut1_day, why + "our log's later date for the cut"))]


def _commit_chain_note(S: Store) -> List[Cell]:
    """The note on the post-lock code row's two commit symbols (Edith, proof 3, C.39: neither "→" nor "/" was defined). Our record of the
    code used after the locks (findings register 5.4) lists the main runner as three commits joined by "→", the last being "the commit the
    main run ran from", and the step-voting design (E3) as two commits joined by "/". The note says what each joins; the build stops unless
    the record still writes them so, and the step-voting design is still a main-run arm. The records stay, unprinted, in the cell."""
    def bullet(pat: str) -> Ref:
        return cell_ref(S, "findings", line_of(S, "findings", pat, expect=1))
    main_b, e3_b = bullet(r"^  - main runner d364c24"), bullet(r"^  - E3 aa228e1")
    e3 = S.ref("main", "reporting.group_b.item_16.e3")
    if _PLAIN_ARM["e3"] != "Step voting" or not S.has("main", "reporting.group_b.item_16.e3"):
        raise ValueError("TAB-19: E3 is no longer the step-voting arm of the main run")
    return [_seq("In the commit list of the post-lock code row, \u201c\u2192\u201d leads from one commit of the main runner to the next, the "
                 "last being the commit the main run ran from, and \u201c/\u201d separates the two commits of the step-voting design.",
                 guard(main_b, r"^- main runner [0-9a-f]{7} (\u2192) [0-9a-f]{7} \u2192 [0-9a-f]{7} \(the commit the main run ran from, per its",
                       "the main runner is a chain of three commits joined by an arrow, the last the commit the main run ran from"),
                 guard(e3_b, r"^- E3 [0-9a-f]{7} (/) [0-9a-f]{7};$", "step voting's two commits are joined by a slash"),
                 unprinted(key_of(e3), "E3, whose two commits the slash joins, is the step-voting arm of the main run"))]


def _erratum_guards(S: Store) -> List[Cell]:
    """The Amendment 1 erratum's record (TP-8): the plan settlement's problem N2 names the understatement, lists more than one change
    under Deviation 2's rule with Pilot 1's Opus marker among them ("among them"), and rules that the appendix corrects Amendment 1's
    sentence as a disclosed erratum. Unprinted guards."""
    n2 = line_of(S, "settlement_main", r"^- \*\*N2\. Amendment 1 understates what changed under Deviation 2's rule\.\*\*$", expect=1)
    rule = line_of(S, "settlement_main", r"^\s*- \*\*Ruling:\*\* the appendix gives the Pilot 1 marker under both rules and corrects", expect=1)
    changes = [n for n in S.find_lines("settlement_main", r"^ {4}- \*\*[^*]+\*\* (?:moved|fell) ") if n2 < n < rule]
    if len(changes) < 2:
        raise ValueError(f"TAB-19: N2 lists {len(changes)} change(s); 'among them' needs more than one")
    out = [guard(cell_ref(S, "settlement_main", n2), r"^- \*\*N2\. (Amendment 1 understates what changed under Deviation 2's rule)\.\*\*$",
                 "the settlement names the understatement")]
    out += [guard(cell_ref(S, "settlement_main", n), r"^- \*\*([^*]+)\*\* (?:moved|fell) ", "a change N2 lists") for n in changes]
    marker = [n for n in changes if re.search(r"Pilot 1's Opus 24-step marker", S.get("settlement_main", f"L{n}"))]
    if len(marker) != 1:
        raise ValueError("TAB-19: Pilot 1's Opus marker is not among N2's listed changes")
    out.append(guard(cell_ref(S, "settlement_main", rule), r"(corrects Amendment 1's sentence as a disclosed erratum)\.",
                     "the ruling corrects the sentence as a disclosed erratum"))
    return out


def _lineage_row(S: Store) -> List[Cell]:
    """Lock 4's lineage clarification: the record merge is read from our log's correction entry, and its time, the public Lock 4 gist
    and Study 1b's first launch (all UTC) from the plan settlement's group 4, which must name the same merge commit."""
    lin = cell_ref(S, "log", line_of(S, "log", r"^## \d{4}-\d\d-\d\d \(Jarvis\) — Correction: merging the lock-4 tag commit", expect=1))
    merge = extract(lin, r"into main \(([0-9a-f]{7})\)")
    g4m = cell_ref(S, "settlement_g4", line_of(S, "settlement_g4", r"^\s*- \*\*[0-9a-f]{7}\*\* \(main's record merge, ", expect=1))
    if extract(g4m, r"^- \*\*([0-9a-f]{7})\*\* \(main's record merge").raw != merge.raw:
        raise ValueError("TAB-19: the settlement's record merge is not our log's")
    merged = extract(g4m, r"\*\*(\d\d:\d\d:\d\d)Z\*\*, after the gist at")
    gist = extract(g4m, r"after the gist at (\d\d:\d\d:\d\d)Z\)")
    if extract(_lock_cell(S, 4, "Public proof (UTC)"), r"^gist (\d\d:\d\d:\d\d);").raw != gist.raw:
        raise ValueError("TAB-19: the merge line's gist is not Lock 4's public gist")
    launch = extract(_lock_cell(S, 4, "Next paid data"), r"^Study 1b first INVOCATION (\d\d:\d\d:\d\d)$")
    if not gist.raw < merged.raw < launch.raw:
        raise ValueError("TAB-19: the record merge is not between Lock 4's gist and Study 1b's launch")
    return [label("Lock 4 lineage clarification"), _seq("record merge", merge),
            extract(lin, r"^## (\d{4}-\d\d-\d\d)"),
            _seq("Merging the Lock 4 tag commit into main made", extract(lin, r"made (a second child) of the tag"),
                 "of the tag; ruled a disclosed clarification: the run commit is the tag's only first-parent child and the merge is a "
                 "record merge with no run code"),
            label("The record merge of the tag commit into main, after the tag was cut"),
            _seq("No Study 1b or top-up data: the merge (", merged, "UTC) came after Lock 4's public gist (", gist,
                 "UTC) and before Study 1b's first launch (", launch, "UTC)"),
            _where("changes")]


def _topup_start_trigger(S: Store, up: int) -> Cell:
    """The top-up row's trigger, in the neutral form the user ruled (D-142: the paper does not say the run started earlier than
    intended, and gives no reason for the pause): our request to start before 48 hours had passed since the main run's start (D-110:
    "TONIGHT instead of after" the time they ended; the hours are read and checked by `_hours_of_main_start`, and no "window" is
    printed), then the pause and resume times read from the run's spend-log row, and the neutral footnote's other facts: no reply had
    been collected before the pause (the top-up clearance's run record: 0 final records when the runner stopped, at the same time), the
    round in flight was collected on resume and not sent again, every call was sent once, and no request, setting or analysis changed
    (the footnote's own sentence). The typed clauses are guarded by the records' own words, and each guard's record is kept in the
    cell's sources."""
    what = cell_ref(S, "spend_log", up, "What ran")
    notes = cell_ref(S, "spend_log", up, "Notes")
    paused = extract(what, r"paused (\d\d:\d\d:\d\dZ)")
    stop = cell_ref(S, "topup_clearance", line_of(S, "topup_clearance", r"^\*\*The runner was terminated at \d\d:\d\d:\d\dZ\*\*", expect=1))
    if extract(stop, r"terminated at (\d\d:\d\d:\d\dZ)\*\*").raw != paused.raw:
        raise ValueError("TAB-19: the clearance's stop time is not the spend log's pause time")
    if extract(stop, r"(\d+) final records so far").raw != "0":
        raise ValueError("TAB-19: the clearance no longer records zero final records at the pause")
    # D-110's own time ("instead of after" it) is the main run's 48-hour close: the build stops unless it is that many hours after the
    # main run's first invocation (Edith, PR #38 review: the early start is checked against the close it names)
    hours = _hours_of_main_start(S)
    d110 = extract(cell_ref(S, "register", reg_line(S, "D-110"), DEC), r"also asked to run it TONIGHT instead of after (\d{4}-\d\d-\d\d \d\d:\d\d)Z")
    n_main = [n for n, run in _spend_rows(S) if run == "main-l14n6-1"][0]
    start = extract(cell_ref(S, "spend_log", n_main, "What ran"), r"INVOCATION (\d{4}-\d\d-\d\dT\d\d:\d\d):\d\dZ; one invocation")
    due = datetime.strptime(str(start.raw), "%Y-%m-%dT%H:%M") + timedelta(hours=int(hours.raw))
    if due.strftime("%Y-%m-%d %H:%M") != d110.raw:
        raise ValueError(f"TAB-19: D-110's time {d110.raw} is not the main run's {hours.raw}-hour close {due:%Y-%m-%d %H:%M}")
    foot1 = cell_ref(S, "settlement_g3", line_of(S, "settlement_g3", r"^> submitted and before any reply had been collected,", expect=1))
    foot2 = cell_ref(S, "settlement_g3", line_of(S, "settlement_g3", r"each sent once\. No request, setting or analysis changed\.$", expect=1))
    return _seq("We asked to start it before", hours, "hours had passed since the main run's start",
                unprinted(d110, "D-110's time is the main run's 48-hour close (checked)"),
                guard(cell_ref(S, "register", reg_line(S, "D-110"), DEC),
                      r"(also asked to run it TONIGHT instead of after) \d{4}-\d\d-\d\d \d\d:\d\dZ", "we asked to start it early"),
                ". It was paused at", utc(paused), "with its first batch of requests in flight,",
                guard(what, r"(with w1 in flight)", "its first round was in flight"),
                extract(foot1, r"^> submitted and (before any reply had been collected),"),
                unprinted(extract(stop, r"(\d+ final records so far)"), "the run record at the pause: no reply collected"),
                ", and resumed at", utc(extract(what, r"INVOCATIONs [\d:]+Z and (\d\d:\d\d:\d\dZ)")),
                ", collecting that batch without sending it again; each call was sent once (TAB-20).",
                guard(notes, r"every custom id at attempt 1 \((no re-send)", "each call was sent once"),
                extract(foot2, r"each sent once\. (No request, setting or analysis changed)\.$"))


def _topup_start_data(S: Store, up: int) -> Cell:
    """The top-up row's data at the time (TP-7): Study 1's results were open (the Study 1 driver's verified run is logged on a local
    date before the run's UTC date); Study 1b's were cleared to read when Edith's byte-identical re-run ended (its time is printed),
    which came after the disclosed change was committed (the committer time of the run commit, whose full id the top-up clearance
    records and the rulings name as the prepared declared-change commit) and before the top-up's clearance was issued and the run
    launched (both from the top-up clearance)."""
    day_run = str(S.get("spend_log", join_key(f"L{up}", "Date")))
    opened = cell_ref(S, "log", line_of(S, "log", r"^## \d{4}-\d\d-\d\d \(\w+\) — Driver's one run VERIFIED: ", expect=1))
    s1 = extract(opened, r"^## (\d{4}-\d\d-\d\d) ")
    if not s1.raw < day_run:
        raise ValueError("TAB-19: Study 1's verified run is not logged before the top-up's date")
    hd = cell_ref(S, "study1b_clearance", line_of(S, "study1b_clearance", r"^## The analysis: driver run once, and my byte-identical re-run "
                                                                             r"\(\d{4}-\d\d-\d\d\)$", expect=1))
    rerun = cell_ref(S, "study1b_clearance", line_of(S, "study1b_clearance", r"^- \*\*My re-run:\*\* ", expect=1))
    seal = cell_ref(S, "study1b_clearance", line_of(S, "study1b_clearance", r"^- \*\*The seal is lifted:\*\* ", expect=1))
    day = extract(hd, r"re-run \((\d{4}-\d\d-\d\d)\)$")
    cleared = extract(rerun, r", \d\d:\d\d:\d\d–(\d\d:\d\d:\d\d)Z, exit 0\.")
    # The change commit: the top-up clearance's full run commit, the commit the rulings name as the prepared declared change.
    tc = cell_ref(S, "topup_clearance", line_of(S, "topup_clearance", r"^- \*\*The commit:\*\* `[0-9a-f]{40}`\.", expect=1))
    cid = extract(tc, r"^- \*\*The commit:\*\* `([0-9a-f]{40})`\.")
    short = reg_cut(S, "D-112", DEC, r"the prepared declared-change commit ([0-9a-f]{7}) \(")
    if not cid.raw.startswith(short.raw):
        raise ValueError("TAB-19: the top-up clearance's run commit is not the rulings' declared-change commit")
    committed = commit_time_utc(S, cid)
    if not committed < f"{day.raw}T{cleared.raw}Z":
        raise ValueError(f"TAB-19: the disclosed change ({committed}) was not committed before Study 1b was cleared to read")
    chk = cell_ref(S, "topup_clearance", line_of(S, "topup_clearance", r"^## Checks before issue \(\w+, about \d\d:\d\dZ\)$", expect=1))
    issued = extract(chk, r"about (\d\d:\d\d)Z\)$")
    lau = cell_ref(S, "topup_clearance", line_of(S, "topup_clearance", r"^- \*\*The launch:\*\* INVOCATION \d\d:\d\d:\d\dZ\.", expect=1))
    launched = extract(lau, r"INVOCATION (\d\d:\d\d:\d\d)Z\.")
    if extract(lau, r"started_utc (\d{4}-\d\d-\d\d)T").raw != day.raw:
        raise ValueError("TAB-19: the top-up launched on another day than Study 1b's clearance to read")
    if not (cleared.raw < issued.raw + ":00" and cleared.raw < launched.raw):
        raise ValueError("TAB-19: Study 1b was not cleared to read before the top-up's clearance and launch")
    change = Cell("", raw=committed, refs=cid.refs + short.refs,
                  formula=f"{cid.formula}; the commit object's committer time (its bytes hashed against the id): {committed}; "
                          f"not printed: the disclosed change was committed before Study 1b's results were cleared to read")
    return _seq("Study 1's results were open; Study 1b's were cleared to read at", cleared,
                "UTC, after the disclosed change was committed and before the run's clearance and launch; no top-up data; the top-up's "
                "definitions were written before any top-up data",
                unprinted(s1, "the Study 1 driver's verified run, logged before the top-up's date"),
                unprinted(day, "the date of Study 1b's clearance to read"),
                guard(seal, r"\*\*(The Study 1b results may now be read)\.\*\*", "the re-run's end cleared Study 1b's results to be read"),
                change,
                unprinted(issued, "the top-up clearance's issue, after Study 1b was cleared to read"),
                unprinted(launched, "the top-up's launch, after Study 1b was cleared to read"))


def _post_lock_code_row(S: Store) -> List[Cell]:
    """The 'code used after the locks' row (TP-3 to TP-5): the commit lists are read from findings register 5.4's bullets. The pilot
    fix and the diagnostic runner were used after Lock 1 and before Lock 2 (Pilot 1's first call is after Lock 1's tag; the diagnostic
    ran after Pilot 1, on a UTC date before Lock 2's tag); the main runner, the two arms and the converter and driver after Lock 3 (the
    main run's first call is after Lock 3's tag; the converter and driver are not in Lock 3). Each was reviewed before use, and the
    converter and driver are in the main run's public analysis stamp. The trigger cell carries the same timing records as the change
    cell, plus why each was needed: the fix is the spec's post-lock runner fix (the pilot's real-time check on a ledger set), and the
    diagnostic runner served the separate Haiku-only effort diagnostic (the commit its spend-log row ran from), neither an
    operational need nor an arm."""
    c54 = cell_ref(S, "findings", line_of(S, "findings", r"^\*\*5\.4 Code used after the locks", expect=1))

    def bullet(pat: str) -> Ref:
        return cell_ref(S, "findings", line_of(S, "findings", pat, expect=1))
    pilot_b, main_b, drv_b = bullet(r"^  - 5e2b860 \(the pilot\)"), bullet(r"^  - main runner d364c24"), bullet(r"^  - converter and driver")
    pilot = extract(pilot_b, r"^- (5e2b860)")
    diag = extract(bullet(r"^  - 0b45978, the diagnostic runner"), r"^- (0b45978)")
    main = extract(main_b, r"runner ([0-9a-f]{7} → [0-9a-f]{7} → [0-9a-f]{7})")
    e3 = extract(bullet(r"^  - E3 aa228e1"), r"^- E3 ([0-9a-f]{7} / [0-9a-f]{7})")
    d42 = extract(bullet(r"^  - the D-42 arm"), r"arm ([0-9a-f]{7})")
    drv = extract(drv_b, r"driver ([0-9a-f]{7})")
    # After Lock 1 and before Lock 2: Pilot 1 (the pilot fix) and the effort diagnostic (its runner).
    tag1 = extract(_lock_cell(S, 1, "Tag (UTC)"), r"^(\d\d-\d\d \d\d:\d\d:\d\d)$")
    p1 = extract(_lock_cell(S, 1, "Next paid data"), r"^Pilot 1 first call (\d\d:\d\d)$")
    tag2 = extract(_lock_cell(S, 2, "Tag (UTC)"), r"^(\d\d-\d\d \d\d:\d\d:\d\d)$")
    order = [run for _, run in _spend_rows(S)]
    pilot_day = cell_ref(S, "spend_log", _spend_line(S, "pilot-ledger-1"), "Date")
    diag_day = cell_ref(S, "spend_log", _spend_line(S, "diag-haiku-effort-1"), "Date")
    if not (str(pilot_day.value)[5:] == tag1.raw[:5] and p1.raw > tag1.raw[6:11]):
        raise ValueError("TAB-19: Pilot 1's first call is not after Lock 1's tag")
    if not (order.index("pilot-ledger-1") < order.index("diag-haiku-effort-1") and str(diag_day.value)[5:] < tag2.raw[:5]):
        raise ValueError("TAB-19: the effort diagnostic did not run after Pilot 1 and before Lock 2's tag")
    # After Lock 3: the main run (its runner and its arms); the converter and driver are not in Lock 3.
    tag3 = extract(_lock_cell(S, 3, "Tag (UTC)"), r"^(\d\d-\d\d \d\d:\d\d:\d\d)$")
    m1 = extract(_lock_cell(S, 3, "Next paid data"), r"^main run (\d\d:\d\d:\d\d)–")
    main_day = cell_ref(S, "spend_log", _spend_line(S, "main-l14n6-1"), "Date")
    if not (str(main_day.value)[5:] == tag3.raw[:5] and m1.raw > tag3.raw[6:]):
        raise ValueError("TAB-19: the main run's first call is not after Lock 3's tag")
    d42_keys = [k for k in S.keys("main", "reporting.group_b.item_16.rates") if k.startswith("haiku-med-d42-variant ")]
    if not (S.has("main", "reporting.group_b.item_16.e3") and d42_keys):
        raise ValueError("TAB-19: the step-voting and rewording-check arms are not main-run arms")
    arms = [unprinted(key_of(S.ref("main", "reporting.group_b.item_16.e3")), "the step-voting arm is a main-run arm"),
            unprinted(key_of(S.ref("main", kj("reporting.group_b.item_16.rates", d42_keys[0]))),
                      "the rewording-check arm is a main-run arm")]
    # The trigger's after-Lock-1 clause: the fix is the spec's post-lock runner fix (so that the pilot's real-time check runs on a
    # ledger set), and the diagnostic runner is the commit the separate Haiku-only effort diagnostic ran from (its own spend-log row,
    # under its own rulings).
    fix_l = cell_ref(S, "spec1", line_of(S, "spec1", r"^- \*\*The post-lock runner fix\*\* `[0-9a-f]{7}` \(", expect=1))
    if extract(fix_l, r"^- \*\*The post-lock runner fix\*\* `([0-9a-f]{7})` \(").raw != pilot.raw:
        raise ValueError("TAB-19: the spec's post-lock runner fix is not our list's pilot fix")
    diag_what = cell_ref(S, "spend_log", _spend_line(S, "diag-haiku-effort-1"), "What ran")
    diag_notes = cell_ref(S, "spend_log", _spend_line(S, "diag-haiku-effort-1"), "Notes")
    if extract(diag_what, r"from a clean detached checkout at ([0-9a-f]{7}) ").raw != diag.raw:
        raise ValueError("TAB-19: the effort diagnostic did not run from our list's diagnostic runner")
    fix_why = cell_ref(S, "spec1", line_of(S, "spec1", r"^> \*\*Other changes since `prereg-lock-1`\.\*\* One runner fix, so that ",
                                           expect=1))
    why1 = [guard(fix_l, r"^- \*\*The post-lock runner fix\*\* `[0-9a-f]{7}` \((the real-time check on a ledger set)\)",
                  "the fix let the pilot's real-time check run on a ledger set"),
            guard(fix_why, r"One runner fix, (so that the pilot's real-time check runs on a)$", "the fix's purpose, in the spec's words"),
            unprinted(extract(diag_what, r"from a clean detached checkout at ([0-9a-f]{7}) "), "the diagnostic ran from this runner"),
            guard(diag_what, r"^(The Haiku effort diagnostic) \(D-\d+, D-\d+\)", "the run is the effort diagnostic"),
            unprinted(extract(diag_what, r"^The Haiku effort diagnostic \((D-\d+, D-\d+)\)"),
                      "the diagnostic's own rulings (internal decision numbers)"),
            guard(diag_notes, r"(Haiku only, a diagnostic)\.", "the diagnostic was Haiku only")]
    lock1 = [unprinted(tag1, "Lock 1's tag (UTC)"), unprinted(p1, "Pilot 1's first call, after Lock 1's tag"),
             unprinted(text_of(pilot_day), "Pilot 1's UTC date, Lock 1's tag date"),
             unprinted(text_of(diag_day), "the diagnostic's UTC date, after Pilot 1 and before Lock 2's tag"),
             unprinted(tag2, "Lock 2's tag (UTC)"),
             guard(pilot_b, r"^- 5e2b860 \((the pilot)\)", "the fix was used for the pilot")]
    lock3 = [unprinted(tag3, "Lock 3's tag (UTC)"), unprinted(m1, "the main run's first call, after Lock 3's tag"),
             guard(main_b, r"\((the commit the main run ran from), per its", "the main runner is the main run's commit"),
             guard(drv_b, r"lines are (not in lock 3)\.", "the converter and driver are not in Lock 3")]
    return [label("Post-lock code"),
            _seq(extract(c54, r"^\*\*5\.4 (Code used after the locks)\."), "(our list); commits", pilot, ",", diag, ",", main, ",", e3, ",",
                 d42, ",", drv, unprinted(extract(c54, r"^\*\*(5\.4) "), "the section of our findings record (internal)")),
            DASH,
            _seq("Code used in paid runs or the analysis after the locks: after Lock 1 (the pilot fix, the effort-diagnostic runner) and "
                 "after Lock 3 (the main runner with operational changes to the batch and transport code, the step-voting design and "
                 "the rewording-check setting, and the converter and driver)", *lock1, *lock3, *arms),
            _seq("After Lock 1, a runner fix so that the pilot's real-time check could run on a ledger set, and a runner for the separate "
                 "Haiku-only effort diagnostic (a run with its own rulings); after Lock 3, operational needs (crash resume and read "
                 "retries) and new settings; the converter and driver were written after Lock 3",
                 *why1, *lock1, *lock3, *arms,
                 guard(main_b, r"(crash resume and read retries)", "the main runner's changes were crash resume and read retries")),
            _seq("Each runner was committed and reviewed before its own run; the converter and driver are in the main run's public "
                 "analysis stamp, made after collection ended and before any result was opened",
                 guard(bullet(r"^- Each was reviewed CLEAN before use\."), r"^- (Each was reviewed CLEAN before use)\.",
                       "each was reviewed before use"),
                 *_stamp_guards(S, driver=drv)),
            _where("post-lock code")]
