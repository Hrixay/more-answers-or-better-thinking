"""Study 1b and length-sweep tables: the plan's TAB-10 (tests B1-B3), TAB-11 (per-shape readings and views), TAB-12 (effort sweep),
TAB-13 (length sweep), TAB-16 (where the money goes) and TAB-18 (cross-set comparison at 6 steps). Every cell is read from the pinned
files by key (`s1b`, `s1b_k`, `curve_d90`, `curve`, and for TAB-16 and TAB-18 the Study 1 files `main` and `main_k`; for TAB-18
also the top-up's same-model check, `topup`); see paper_out_core.py for the rules. A collapsed interval is replaced by free analysis
4's exact one (`fa4`, revision 2, post hoc), found with core.fa4_exact under the cell's own source and key. Revision 2 gives one for
every collapsed `ci95` in the stamped files except the length sweep's q and main's item 20 cells below k = 40 (which no output prints),
so a collapsed interval without one refuses the build, except TAB-13's q and q^N bands, which are flagged "(zero width)" with free
analysis 4's stated reason; TAB-18's run dates are the spend log's (`spend_log`, pinned in paper_out_ops). Nothing is computed beyond
unit changes and the few simple differences and ratios marked `derive`.

Typed clauses that state what a Lock 4 specification says (the error ratio's tier in TAB-10, the pre-registered flag, cost per correct
answer and list price in TAB-10 and TAB-12, the same-model arm in TAB-18) carry unprinted guards on the pinned specification
(`spec1b`, `topup_spec_s1b`, pinned here), so the build stops if the record no longer says it. So do the other typed clauses that rest
on a record: TAB-11's and TAB-12's "separate bootstrap draws" (the specification and Study 1b's driver and bootstrap as run,
`s1b_driver_s1b` and `s1b_curve_py_s1b`), TAB-16's "pre-specified" for Study 1's reporting definitions (`s1_defs_s1b`) and TAB-18's
"after Study 1b" (the spend log's recorded times).

TAB-10, TAB-12 and TAB-16 are main-text tables (paper_out_names.main_text: no item number, keep-list C-number or E-number is printed in
either version). Each sets `main_table`, the paper's own version (see "the paper's versions" below), with its own notes and caption
facts; they have no narrow version (paper_out_narrow.NARROW) and no `main_notes` or `main_caption`.
Every output passes `print_rules`: no decision id, internal record name or voice other than "we" is printed, and no caption fact names
an item number.

Supplement layouts (batch g; D-159 to D-162): every full table and every panel carries a layout mark (`layout`, and `font` or
`groups` where the page or the rows need it), chosen by measuring each file typeset at its width (a float 6.5 in wide; a landscape table
9.0 in; `split` where even 9.0 in is too narrow, with the key columns repeated in every part). The notes of every file print once under
the table's last float, so the last file of each table is the short one (TAB-16's panels are in that order for it). A column that prints
one value in every row moves to a note (`fold_constants`). The vocabulary is D-161's (setting, sample, puzzle, cost-matched, shown no
worse (Holm-adjusted), the drift check between runs); a stamped wording that holds a retired term is printed in quotation marks with the
paper's word beside it. The paper's versions (<id>.main) are unchanged by this pass.

Units in these files: Study 1b's analysis.json and Study 1's item_24 hold accuracies in points (0-100); the two length-sweep files hold
proportions (0-1), and Study 1's `main_run_markers` and item_8b vote curve do too. Each formatter call below says which it reads.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paper_out_core import (EMPTY, MINUS, NBSP, Cell, Ref, Source, Store, Table, YES_NO, _col_spec, _width_plan, ci_refs, dec, derive, exact,
                             stamped_count,
                             fa4_exact, integer,
                             interval, is_num, join_key, joined, label, num, num_d, output, parse_key, pct, pvalue, pvalue_bound, pts,
                             ratio, register_source, text_of, usd)
from .paper_out_names import (EFFORT_ORDER, MAIN_TEXT_ID, STUDY1B_TAGS, STUDY1B_TESTS, STUDY1_ARMS, STUDY1_TESTS, _printed,
                              main_text, shape, shape_word)
from .paper_out_ops import cell_ref, extract, guard, line_of, single_value, unprinted
from .paper_out_overview import DECISION_FORMULA, UNBOUNDED_NOTE, _decision    # the decision words of the paper's Table 2 (TAB-01's paper version)

# The two Lock 4 specifications whose words this module's notes rest on (text, pinned at the commit that last changed each, the
# commit the stamped analysis files name in their `spec` field; the bytes are the same at the Lock 4 commit). Named for this module, so
# that its pins do not depend on another module's (paper_out_ops does the same for the files it shares with paper_out_timeline).
register_source(Source("spec1b", "research/study1b-spec.md", "9c007e5",
                       "4b6779502c26ae1da96b55573b0f9e62d153caa4509ef543b748c5d70a72c879", kind="text",
                       what="The Study 1b specification, frozen with Lock 4 (section 4: the error-rate ratio beside every test)"))
register_source(Source("topup_spec_s1b", "research/topup-run-spec.md", "9c007e5",
                       "f048e73a8ccc843f9d575e4fd51a0d462d1e39d5c1635bbad5d1a493170b41c5", kind="text",
                       what="The top-up run's specification, frozen with Lock 4 (section 3: the same-model check is Haiku-medium)"))
# Study 1's reporting definitions at the commit the Study 1 file's group-B note names (93334b8, also the file's last change): its header
# says they were fixed after Lock 3 and before any main-run result was opened, which is why TAB-16 calls Study 1's costs per answer and
# per correct answer, token means and thinking estimates "pre-specified", not "pre-registered".
register_source(Source("s1_defs_s1b", "research/reporting-definitions-main.md", "93334b8",
                       "bddab72761b4111f6d4ed439f13ddbd63427bc14a9c61b58d0ceadb32f18bf81", kind="text",
                       what="Study 1's reporting definitions (header: fixed after Lock 3, before any main-run result was opened)"))
# Study 1b's analysis driver and the bootstrap it calls, as run for the Study 1b file (once, at the lock-4 tag d1c565f; curve.py is
# unchanged there since a8f0acd): the per-test, effort-sweep and vote-curve intervals all come from `_boot` with the file's draws, each
# seeded by its own bootstrap name (TAB-11's and TAB-12's note on separate draws, Edith's Q7).
register_source(Source("s1b_driver_s1b", "harness/analysis/study1b.py", "d1c565f",
                       "957f63276197fdcf9c2eee0e8f43b542c63ee8c1be76a4f3ef72b6226a2295d3", kind="text",
                       what="Study 1b's analysis driver as run: per_form, the effort sweep and the vote curve all call _boot with the draws"))
register_source(Source("s1b_curve_py_s1b", "harness/analysis/curve.py", "d1c565f",
                       "948261958e81e6ddf460f9f7391f586162eebd0435754e3d01aab637e793a732", kind="text",
                       what="The cluster bootstrap Study 1b's driver calls: its random draws are seeded by the bootstrap's name"))

DASH = label("—")                                   # does not apply
TESTS_1B = ("B1", "B2", "B3")
PRIM = ("confirmatory", "primary_margin_5")
SEC = ("confirmatory", "secondary_margin_10")
SENS = "sensitivity_exposed_bases_excluded"
FRT = "descriptive.format_refusals_truncations_missing"
ZERO = "(zero width)"                               # flag on a collapsed interval that free analysis 4 gives no exact replacement for
FA4_CELLS = ("result", "cells")                     # free analysis 4 (post hoc): one entry per collapsed cell, by source path and key
INTERVAL_TYPES = {"cluster bootstrap": "cluster bootstrap", "clopper-pearson": "Clopper–Pearson (exact)", "wilson": "Wilson (exact)"}
MODEL_ORDER = ("haiku", "sonnet", "opus")
VIEWS = (("as_deployed", "as deployed"), ("refusals_out", "refusals out"), ("truncations_out", "truncations out"))


# ---------------------------------------------------------------- helpers


def L(text: str) -> Cell:
    return label(text)


def note(*parts: Any) -> List[Cell]:
    """A footnote: strings become labels, cells stay as they are."""
    return [L(p) if isinstance(p, str) else p for p in parts]


ITEM_ID = re.compile(r"(?i)\bitems? \d")                # a pre-registration item number: never in any output's caption facts (Q22)
# Never printed by any output of this module (cells, notes, titles, panels, captions, main-text versions): a decision id (Jarvis's
# PO-1 ruling: the decision register is not released; the ids stay in the cells' sources), an internal record's name (the chat names
# among them), and any voice but "we" (Edith's Q24).
NEVER_PRINTED = re.compile(r"\bD-\d|LOG\.md|\b(?:Jarvis|Karen|Friday|Edith|Vision)\b"
                           r"|(?i:findings register|decision register|spend log|the authors|the user)")


def print_rules(t: Table) -> Table:
    """Every output of this module: nothing in NEVER_PRINTED is printed anywhere, and no caption fact (of the full or the main-text
    version) names a pre-registration item number (Edith's Q22: the paper's captions use none; an appendix table's cells and notes
    may). A main-text table is also checked whole by paper_out_names.main_text."""
    bad = sorted({x for x in _printed(t) if NEVER_PRINTED.search(x)})
    if bad:
        raise ValueError(f"printed text names a decision id, an internal record or another voice: {bad}")
    for k, cells in [*t.caption.items(), *(getattr(t, "main_caption", None) or {}).items()]:
        text = " ".join(c.printed for c in cells)
        if ITEM_ID.search(text):
            raise ValueError(f"caption fact {k!r} names an item number: {text!r}")
    return t


# ---------------------------------------------------------------- the paper's versions (D-159, D-160, D-161)
# TAB-10 (the three pooled tests and B2's ties-counted-wrong row; the per-shape rows are TAB-11's), TAB-11, TAB-12 and TAB-16 each set
# `main_table`: the paper's own version, built from the same refs as the full table at the paper's precision (percentages and point
# differences to one decimal), which the writer prints as <id>.main; the full table, with its exact values, goes to the supplement
# unchanged.

PAPER_MAX_COLUMNS = 8
PAPER_MAX_NOTES = 2
PAPER_NOTE_CHARS = 220                                 # about two printed lines at \footnotesize (batch (f) rule 5)
# The paper's vocabulary (D-161): the retired names and the words a paper cell or note never uses (C-165; "significant").
PAPER_BARRED = re.compile(r"(?i)\b(?:tr(?:y|ies)|arms?|base puzzles?|equal[- ]money|same-model|as[- ]deployed|non-inferior|declared"
                          r"|significant)\b")


def paper_table(cols: Sequence[str], rows: List[List[Cell]], notes: List[List[Cell]], caption: Dict[str, List[Cell]],
                layout: str = "float", text_cols: Sequence[int] = (0,), groups: Sequence[int] = (), once: Sequence[int] = (),
                spaced: bool = False, font: Optional[str] = None) -> Table:
    """A paper version with the house rules checked (batch (f), D-160 house style, D-161): at most eight columns and two notes, every
    note printed under the table (short) and at most about two printed lines; no unit in a cell ('%'), no column with one value in every
    row, every column but `text_cols` set as numbers (core._col_spec 'r': right-aligned, so equal decimals line up; polish §2.8), none of
    the retired or barred words in a header, cell, note or caption fact; and the module's print rules and the main-text id rule. The
    caption facts are the paper version's own: the full table's facts for what the paper version shows, in the paper's words (Vision
    writes the printed caption from them)."""
    t = Table([L(c) for c in cols], rows, notes, caption, short_notes=list(range(len(notes))), layout=layout, groups=list(groups),
              once=list(once), spaced=spaced, font=font)
    t.check()
    if len(t.columns) > PAPER_MAX_COLUMNS or len(notes) > PAPER_MAX_NOTES:
        raise ValueError(f"a paper version has {len(t.columns)} columns and {len(notes)} notes (at most 8 and 2)")
    for n in notes:
        text = " ".join(c.printed for c in n if c.printed)
        if len(text) > PAPER_NOTE_CHARS:
            raise ValueError(f"a paper note is {len(text)} characters, more than two printed lines: {text!r}")
    if any("%" in c.printed for r in rows for c in r):
        raise ValueError("a paper cell holds a unit ('%'); units go in the header")
    for j, c in enumerate(t.columns):
        if len(rows) > 1 and len({r[j].printed for r in rows}) == 1:
            raise ValueError(f"the paper column {c.printed!r} has one value in every row: it goes in a note or the caption")
        if j not in text_cols and _col_spec(t, j) != "r":
            raise ValueError(f"the paper column {c.printed!r} is not set as numbers (a text or dash cell in it); it would not align")
    texts = ([c.printed for c in t.columns] + [c.printed for r in rows for c in r] + [c.printed for n in notes for c in n]
             + [" ".join(c.printed for c in v if c.printed) for v in caption.values()])
    bad = sorted({x for x in texts if PAPER_BARRED.search(x) or MAIN_TEXT_ID.search(x)})
    if bad:
        raise ValueError(f"a paper version prints a retired word, a barred word or an internal id: {bad}")
    return print_rules(t)


def thousands(c: Cell) -> Cell:
    """A cell that is a whole number or a one-decimal mean with comma thousands from 1,000 up (polish §2.5), keeping its raw value,
    sources and formula."""
    m = re.fullmatch(r"(\d{4,})(\.\d+)?", c.printed)
    if m:
        return Cell(f"{int(m.group(1)):,}{m.group(2) or ''}", kind=c.kind, raw=c.raw, refs=c.refs, formula=c.formula, bold=c.bold)
    return c


def prose_pct(c: Cell) -> Cell:
    """A percentage, or a pair 'a / b' of them, in a sentence: the unit follows each number ('100.0% / 100.0%'; polish §2.6 keeps the
    '%' out of cells and in prose), the cell keeping its record."""
    parts = c.printed.split(" / ")
    if not all(re.fullmatch(r"\d+(?:\.\d+)?", x) for x in parts):
        raise ValueError(f"{c.printed!r} is not a number or a pair of numbers")
    return replace(c, printed=" / ".join(x + "%" for x in parts))


def tk(r: Ref, dp: int = 0) -> Cell:
    """A token count with comma thousands, from its ref: at 0 places (a total), or at 1 place for a token mean in the
    supplement's full table (Edith, proof 4: the supplement prints every mean as the paper's text prints it, 2,006.8)."""
    return thousands(num(r, dp=dp))


def tk_stamped(r: Ref) -> Cell:
    """A token median exactly as the file stamps it (Edith, #39 review S1: the supplement keeps exact values): a whole number has no
    ".0" padding ("600", "1,737") and a half keeps its ".5" ("7,604.5"). A median of whole token counts is a whole number or a half; any
    other value is not one, and stops the build rather than print at a precision it was not stamped to. The form is core's stamped_count,
    which FIG-07 prints too."""
    d = dec(r.value)
    if (d * 2) % 1 != 0:
        raise ValueError(f"{r.source}:{r.key} is {r.value!r}: a median of token counts is a whole number or a half")
    return stamped_count(r)                             # core's one form for a value printed as stamped (FIG-07 uses it too)


def right_align(t: Table, *titles: str, equal: bool = False) -> None:
    """Right-align the value columns named by `titles` (Edith, proof 4, §2.8/§7.7: "Panel 1's value columns are left-aligned"). The writer
    sets a column of numbers ragged-left (right-aligned: the point and its interval line up) only when three quarters of its cells read as
    numbers (core._numeric_column), and a cell that carries an "(exact, post hoc; … puzzles)" or "(zero width)" tag reads as text, so a
    column with many such cells came out ragged-right. This keeps the writer's own width plan for the table and sets those columns
    ragged-left (core's `fixed_plan`, the plan a split table's parts share); every other choice of the plan is unchanged. Call it last,
    once the table's rows are final. `equal`: the named columns take one width, their mean (the same cells then break the same way in
    every one of them)."""
    specs, w, numeric = _width_plan(t)
    numeric, w = dict(numeric), dict(w)
    named = [j for j, c in enumerate(t.columns) if c.printed in titles and specs[j] is None]
    if len(named) != sum(1 for c in t.columns if c.printed in titles):
        raise ValueError(f"right_align: a named column is not a wrapping column of the table: {titles}")
    mean = sum(w[k] for k in named) / len(named) if named else 0.0          # taken once, before any width changes
    for j in named:
        numeric[j] = True
        if equal:
            w[j] = mean
    t.fixed_plan = (specs, w, numeric)


def starts(rows: List[List[Cell]], key: Any) -> List[int]:
    """Row groups (polish §7.7): the indexes of the rows where `key(row)` changes (a little space opens above each)."""
    out: List[int] = []
    for i, r in enumerate(rows):
        if i and key(r) != key(rows[i - 1]):
            out.append(i)
    return out


def family(r: List[Cell]) -> str:
    """The model family a row's first cell names ('Haiku-max', 'Haiku, thinking off' and 'Haiku-medium vote, k = 6 ...' all read 'Haiku'):
    the key of the row groups of the tables whose rows run through the models."""
    m = re.match(r"[A-Za-z]+", r[0].printed)
    if m is None:
        raise ValueError(f"{r[0].printed!r} does not open with a model name")
    return m.group(0)


def fold_constants(cols: List[str], rows: List[List[Cell]], names: Sequence[str]) -> Dict[str, Cell]:
    """Columns that print one value in every row (polish §7.3: a constant column moves to a note), taken out of `cols` and `rows` in
    place. Each comes back as ONE cell that keeps every row's sources (paper_out_ops.single_value), after the check that every row
    prints the same text; the note that prints it, or carries it unprinted, so keeps the records the column rested on."""
    out: Dict[str, Cell] = {}
    for name in names:
        j = cols.index(name)
        if any(r[j].printed != rows[0][j].printed for r in rows):
            raise ValueError(f"column {name!r} no longer prints one value in every row; it cannot move to a note")
        one = single_value([r[j] for r in rows], name)
        out[name] = one if rows[0][j].formula else replace(one, formula=None)     # a plain count stays checkable (cells_check)
        del cols[j]
        for r in rows:
            del r[j]
    return out


def split(t: Table, landscape: bool, parts: Sequence[Any], key: Sequence[str] = ("Test",)) -> Table:
    """The supplement layout "split" / "split landscape" (core.split_columns proposes, this fixes): `parts` are lists of column titles
    (or (row indexes, titles) for a part with its own rows); the `key` columns repeat in every part. A title that is not exactly once
    in the table, or a column held twice by one row, refuses; so does a column left out for a row unless that cell is a dash (a column
    that does not apply to a block of rows may be left out of the part that prints the block; a note says so)."""
    titles = [c.printed for c in t.columns]

    def idx(x: str) -> int:
        if titles.count(x) != 1:
            raise KeyError(f"split: column {x!r} is not exactly once in {titles}")
        return titles.index(x)
    keys = [idx(k) for k in key]
    out: List[Tuple[Optional[List[int]], List[int]]] = []
    for part in parts:
        rows, names = part if isinstance(part, tuple) else (None, part)
        out.append((None if rows is None else list(rows), [idx(x) for x in names]))
    every = list(range(len(t.rows)))
    for j in range(len(titles)):
        if j in keys:
            continue
        held = [i for rows, cs in out if j in cs for i in (every if rows is None else rows)]
        if len(held) != len(set(held)) or any(t.rows[i][j].printed != DASH.printed for i in set(every) - set(held)):
            raise ValueError(f"split: column {titles[j]!r} is not held, in exactly one part, by every row that gives it a value")
    t.layout = "split landscape" if landscape else "split"
    t.split_parts, t.split_key = out, keys
    return t


def tokens(r: Ref) -> Cell:
    """A mean token count at 0 places with comma thousands (house style; core.num prints none), from the same ref as the full table's
    cell, so the raw value and its rounding are the same."""
    c = num(r, dp=0)
    if c.printed.startswith(MINUS) or not c.printed.isdigit():
        raise ValueError(f"{r.source}:{r.key}: {c.printed!r} is not a token count")
    return Cell(f"{int(c.printed):,}", raw=c.raw, refs=c.refs, formula=c.formula)


def pair(a: Cell, b: Cell) -> Cell:
    """'chains / pieces' in one cell, each value keeping its ref."""
    return joined(a, L("/"), b)


def R(S: Store, src: str, *segs: Any) -> Ref:
    return S.ref(src, join_key(*segs))


def G(S: Store, src: str, *segs: Any) -> Any:
    return S.get(src, join_key(*segs))


def P(r: Ref, dp: int = 1, prop: bool = False) -> Cell:
    """An accuracy or share in %, from points (default) or from a proportion; one more decimal if rounding would reach 100."""
    return pct(r, dp=dp, from_proportion=prop, bounds=(100.0,))


class Marks:
    """What one table did with its collapsed intervals: those replaced by free analysis 4's exact interval (`exact`: the block's
    source and key, and the base key of free analysis 4's cell, 'result.cells.<i>') and those left flagged '(zero width)' (`zero`: the
    source and the interval's key). The notes are written from it."""

    def __init__(self) -> None:
        self.exact: List[Tuple[str, str, str]] = []
        self.zero: List[Tuple[str, str]] = []


def _exact(S: Store, src: str, block: List[Any], dp: int, prop: bool, marks: Optional[Marks], short: Any = False) -> Optional[Cell]:
    """Free analysis 4's exact (Clopper–Pearson) interval for the collapsed one stamped at `src`:`block`.ci95, with its n of base
    puzzles, or None where it has none. core.fa4_exact finds the cell by the block's own source and key and checks that it is fa4's copy
    of this collapsed interval; here its mean, n and unit must also be the block's (x / n is the stamped mean), and the interval must be
    a bootstrap one, as the exact note says (a block's `interval` field, where it has one, says 'cluster bootstrap'; the length-sweep
    files name only their Wilson intervals). `short`: the paper's mark, "(exact)" (a paper note defines it), in place of the full
    table's "(exact, post hoc; … puzzles)"; "bare": the interval alone, the caller marks the row (a mark inside a cell shifts the numbers
    of its column: Edith, proof 4, §2.8)."""
    fc = fa4_exact(S, src, join_key(*block))
    if fc is None:
        return None
    if S.has(src, join_key(*block, "interval")) and G(S, src, *block, "interval") != "cluster bootstrap":
        raise ValueError(f"{src}:{join_key(*block)}: a collapsed {G(S, src, *block, 'interval')!r} interval, not a bootstrap one")
    mean, n_base = G(S, src, *block, "mean"), G(S, src, *block, "n_base")
    if S.get("fa4", fc.base + ".stamped_mean") != mean:
        raise ValueError(f"free analysis 4 {fc.base}: stamped mean differs from {src}:{join_key(*block)}")
    if fc.n != n_base or fc.scale != (100.0 if prop else 1.0):
        raise ValueError(f"free analysis 4 {fc.base}: n or unit differs from {src}:{join_key(*block)}")
    if fc.x not in (0, fc.n) or abs(fc.x / fc.n * (1.0 if prop else 100.0) - mean) > 1e-9:
        raise ValueError(f"free analysis 4 {fc.base}: x / n is not the stamped mean")
    ex = interval(fc.lo, fc.hi, dp=dp, scale=fc.scale, bounds=(100.0,))
    if marks is not None:
        marks.exact.append((src, join_key(*block), fc.base))
    if short == "bare":
        return ex
    if short:
        return joined(ex, L("(exact)"))
    # the puzzle count is a count of puzzles, never "n" (n is samples per puzzle in the paper: Edith, proof 4, §3.7); "post hoc" and
    # "20 puzzles" never split
    return joined(ex, L(EXACT_OPEN), joined(integer(S.ref("fa4", fc.base + ".n")), L("puzzles)"), sep=NBSP))


def interval_up(lo: Ref, hi: Ref, dp: int = 1, scale: float = 1.0) -> Cell:
    """An accuracy interval for a paper table whose upper end never takes the one-more-decimal guard at 100 (Edith, proof 3, A.23: Opus-low's
    "[93.2, 99.97]" in a column of one decimal prints "[93.2, 100.0]"; an upper bound rounds up to the safe side, polish §2.2). The lower
    end keeps the guard (a lower end is never rounded up past its value); the upper end is rounded half up at `dp` places, which is
    100.0 for any end from 99.95 up. Everything else is core.interval's."""
    guarded = interval(lo, hi, dp=dp, scale=scale, bounds=(100.0,))
    plain = interval(lo, hi, dp=dp, scale=scale)
    low_end, high_end = guarded.printed[1:-1].split(", ")[0], plain.printed[1:-1].split(", ")[1]
    rule = (f"lower end at {dp} decimals with the one-more-decimal guard at 100; upper end rounded half up at {dp} decimals with no "
            "guard (an upper bound rounds to the safe side: polish 2.2, Edith proof 3 A.23)")
    return Cell(f"[{low_end}, {high_end}]", raw=guarded.raw, refs=guarded.refs,
                formula=(guarded.formula + "; " if guarded.formula else "") + rule)


def CI(S: Store, src: str, segs: Sequence[Any], dp: int = 1, prop: bool = False, flag: bool = True, marks: Optional[Marks] = None,
       no_exact: bool = False, short: Any = False, up: bool = False) -> Cell:
    """A stamped 95% interval in %. Where the file stamps a collapsed one (both ends equal), free analysis 4's exact Clopper–Pearson
    interval replaces it (post hoc, labelled with its n). Revision 2 gives one for every collapsed `ci95` in the stamped files but the
    length sweep's q and main's item 20 cells below k = 40 (which no output prints), so a collapsed interval without one refuses the
    build unless the caller says it has none (`no_exact`: TAB-13's q and q^N bands, flagged '(zero width)'; the table's notes give free
    analysis 4's reason and check that it covers them). `up`: a paper table's interval (`interval_up`: the upper end rounds to 100.0)."""
    lo, hi = ci_refs(S, src, join_key(*segs))
    scale = 100.0 if prop else 1.0
    c = interval_up(lo, hi, dp=dp, scale=scale) if up else interval(lo, hi, dp=dp, scale=scale, bounds=(100.0,))
    if not (flag and is_num(lo.value) and is_num(hi.value) and lo.value == hi.value):
        return c
    ex = _exact(S, src, list(segs[:-1]), dp, prop, marks, short) if segs[-1] == "ci95" else None
    if ex is not None:
        return ex
    if not no_exact:
        raise ValueError(f"{src}:{join_key(*segs)} collapsed and free analysis 4 (revision 2) has no exact interval for it")
    if marks is not None:
        marks.zero.append((src, join_key(*segs)))
    return joined(c, L(ZERO))


def acc_ci(S: Store, src: str, segs: Sequence[Any], dp: int = 1, prop: bool = False, marks: Optional[Marks] = None,
           short: Any = False, up: bool = False, tie: bool = False) -> Cell:
    """'mean [lo, hi]' for a block with `mean` and `ci95`. `up`: a paper table's interval (`interval_up`). `tie`: a no-break space between
    the mean and its interval, so a wrapping column never sets them on two lines (Edith, proof 3, Table S24's "100.0 [83.9, 100.0]" cells)."""
    mean = P(R(S, src, *segs, "mean"), dp, prop)
    return joined(mean, CI(S, src, [*segs, "ci95"], dp, prop, marks=marks, short=short, up=up), sep=NBSP if tie else " ")


EXACT_OPEN = "(exact, post\u00a0hoc;"                 # the mark's opening words, "post hoc" tied; the puzzle count follows


def define_exact(t: Table) -> None:
    """Each panel that prints "(exact, post hoc; … puzzles)" carries the note that defines it too (polish §7.5: a symbol a file prints
    is defined in a note of that file; the converter prints equal notes once)."""
    for _, p in t.panels:
        if any(EXACT_OPEN in c.printed for r in p.rows for c in r) and not any(
                "(exact, post hoc; … puzzles)" in c.printed for n in p.notes for c in n):
            p.notes.append(exact_note())


def exact_note(what: str = "") -> List[Cell]:
    """The note for the exact replacements (only when the table has one)."""
    return note("\"(exact, post hoc; … puzzles)\" marks a bootstrap interval that collapsed to one value (every puzzle right, or every "
                "one wrong), replaced by the exact two-sided 95% Clopper–Pearson interval from free analysis 4 (post hoc; it changes no "
                "test). The count in the mark is the number of puzzles, not of samples (the conservative unit)." + what)


def quoted_text(r: Ref) -> Cell:
    """A stamped string printed in quotation marks, as the file's own words (Edith, proof 4, rule 4)."""
    return joined(L("\""), text_of(r), L("\""), sep="")


def quoted_reading(r: Ref) -> Cell:
    """A Study 1b template reading ("holds (no worse in all three views)", "inconclusive (could not show)") printed in quotation marks as
    the file's own words (Edith, proof 4, rule 4: stamped words that are not the paper's ruled wording print in quotation marks; the
    paper's ruled reading, shown no worse (Holm-adjusted), is the Holm-adjusted column). The cell keeps the stamped string as its raw
    value; a short parenthesis ("could not show") is tied whole, a longer one ("no worse in all three views") by its last four words, so
    that a wrapping column never breaks "inconclusive (could not / show)" and breaks the long reading only after "worse" (the column
    is as wide as "in all three views)", and the reading sets on two lines, never three with "in" or "in all" alone in the middle)."""
    words = str(text_of(r).printed)

    def tie(m: "re.Match[str]") -> str:
        words_ = m.group(1).split(" ")
        keep = len(words_) if len(m.group(1)) <= 16 else 4          # the whole short parenthesis, or the last four words of a long one
        return "(" + " ".join(words_[:-keep]) * (len(words_) > keep) + " " * (len(words_) > keep) + NBSP.join(words_[-keep:]) + ")"
    shown = re.sub(r"\(([^)]*)\)", tie, words)
    return Cell('"' + shown + '"', raw=r.value, refs=(r,),
                formula="the Study 1b file's template reading, in quotation marks (as the file words it; spaces in its parenthesis tied)")


def setting_label(name: str) -> Cell:
    """A setting's name as a table cell: "Haiku, thinking off" never breaks across lines in a narrow column (Edith, proof 4, p. 114)."""
    return L(name.replace("Haiku, thinking off", "Haiku,\u00a0thinking\u00a0off"))


def shp(s: str) -> Cell:
    """The shape's name in a cell: "chains (1×6)", "pieces (6×1)" (the shape is "chains" in cells and headers: Edith, M2-12)."""
    return L(f"{'chains' if shape_word(s) == 'chain' else shape_word(s)} ({shape(s)})")


def steps_label(S: Store, n: Ref) -> Cell:
    return integer(n)


def shapes_of(n: int) -> Tuple[str, str]:
    """Chain then pieces for a Study 1b length."""
    return f"1x{n}", f"{n}x1"


def tag_name(tag: str) -> str:
    return STUDY1B_TAGS[tag][0]


def arm_order(arm: str) -> Tuple[int, int, int]:
    tag, n = arm.split("@")
    _, model, effort = STUDY1B_TAGS[tag]
    return MODEL_ORDER.index(model), EFFORT_ORDER.index(effort), int(n)


def point_index(S: Store, k_ref: Any) -> int:
    """Index of the k-sample vote in the Study 1b vote curve (k = 1..10 in file order; checked against each point's own k)."""
    pts_ = S.get("s1b", "descriptive.vote_curve_n16.points")
    for i, p in enumerate(pts_):
        if p["k"] == k_ref:
            return i
    raise KeyError(f"no vote-curve point at k = {k_ref}")


def b2_k(S: Store) -> Ref:
    """B2's k, read from the vote curve (the same value as k.json's k; checked)."""
    r = R(S, "s1b", "descriptive", "vote_curve_n16", "k_from_k_json")
    if r.value != S.get("s1b_k", "k"):
        raise ValueError("vote curve k differs from k.json's k")
    return r


def ch_pooled_ref(S: Store, t: str, what: str = "mean") -> Ref:
    """The challenger's pooled accuracy block entry for B1/B3 (Haiku-max single sample at the test's length) or B2 (the k-sample vote)."""
    n = int(G(S, "s1b", "completeness", t, "N"))
    if t == "B2":
        i = point_index(S, G(S, "s1b", "descriptive", "vote_curve_n16", "k_from_k_json"))
        return R(S, "s1b", "descriptive", "vote_curve_n16", "points", i, "pooled", what)
    return R(S, "s1b", "descriptive", "arms", f"hx@{n}", "pooled", what)


def om_pooled_ref(S: Store, t: str, what: str = "mean") -> Ref:
    n = int(G(S, "s1b", "completeness", t, "N"))
    return R(S, "s1b", "descriptive", "arms", f"om@{n}", "pooled", what)


def fmt_pair(S: Store, tag: str, n: int, dp: int = 1) -> Cell:
    """Format compliance (%) of a setting's samples, chains / pieces: at one decimal in the paper's versions, at two in the supplement's
    full tables (D-161 (2): the supplement keeps every exact value)."""
    ch, pc = shapes_of(n)
    a = P(R(S, "s1b", *FRT.split("."), "format_report", tag, ch, "format_compliance"), dp, prop=True)
    b = P(R(S, "s1b", *FRT.split("."), "format_report", tag, pc, "format_compliance"), dp, prop=True)
    return joined(a, L("/"), b)


def margins(S: Store) -> Tuple[float, float]:
    return float(G(S, "s1b", *PRIM, "margin")), float(G(S, "s1b", *SEC, "margin"))


def holm_check(S: Store, fam: Sequence[str]) -> None:
    """Holm's step-down order: a test is declared only if its p is below its threshold and every test before it in the stamped Holm
    order is declared. The stamped `declared` must follow it (a check; nothing is printed from it)."""
    for vk, _ in VIEWS:
        v = [*fam, "views", vk]
        ok = True
        for t in G(S, "s1b", *v, "holm_order"):
            ok = ok and G(S, "s1b", *v, "tests", t, "p") < G(S, "s1b", *v, "holm_thresholds", t)
            if G(S, "s1b", *v, "tests", t, "declared") != ok:
                raise ValueError(f"{join_key(*v)} {t}: declared does not follow Holm's step-down order")


def s1b_set_at(S: Store, n: int) -> str:
    """The Study 1b set at a length: the one entry of inputs.sets with that n (for checks only; set ids are never printed)."""
    hits = [k for k, v in G(S, "s1b", "inputs", "sets").items() if v["n"] == n]
    if len(hits) != 1:
        raise ValueError(f"Study 1b has {len(hits)} sets at {n} steps")
    return hits[0]


def test_sets(S: Store) -> List[Cell]:
    """Caption 'set' of the test tables, in words: Study 1b's set at the B1/B2 length and its set at the B3 length (checked against the
    file's set ids, which stay out of the paper outside the methods appendix)."""
    for t in TESTS_1B:
        sid = G(S, "s1b", "completeness", t, "set_id")
        if sid != G(S, "s1b", "constants", "test_sets", t) or sid != s1b_set_at(S, int(G(S, "s1b", "completeness", t, "N"))):
            raise ValueError(f"{t}: its set is not Study 1b's one set at its length")
    if G(S, "s1b", "completeness", "B1", "set_id") != G(S, "s1b", "completeness", "B2", "set_id"):
        raise ValueError("B1 and B2 ran on different sets")
    return [L("Study 1b's own puzzle set at"), integer(R(S, "s1b", "completeness", "B1", "N")), L("steps (Tests B1 and B2) and its set at"),
            integer(R(S, "s1b", "completeness", "B3", "N")), L("steps (Test B3)")]


def test_tries(S: Store) -> List[Cell]:
    """Samples per puzzle and shape on the two sides of Tests B1-B3 (the designed samples; each test side's stamped tries agree)."""
    for t in TESTS_1B:
        n = int(G(S, "s1b", "completeness", t, "N"))
        for tag in ("hx", "om"):
            if G(S, "s1b", "descriptive", "arms", f"{tag}@{n}", "tries_per_item") != G(S, "s1b", "constants", "designed_tries", tag):
                raise ValueError(f"{tag}@{n}: tries per item differ from the designed tries")
    return [L("samples per puzzle and shape: Haiku-max"), integer(R(S, "s1b", "constants", "designed_tries", "hx")),
            L("and Opus-medium"), integer(R(S, "s1b", "constants", "designed_tries", "om"))]


# ---------------------------------------------------------------- the specifications' words behind typed clauses
# A typed clause that states what a specification says is joined with unprinted guard cells (paper_out_ops.guard): the build stops
# unless the pinned specification still says it, and the cell's sources name the line it rests on.


def with_evidence(text: str, evidence: Sequence[Cell]) -> Cell:
    """A typed clause (a label) with the records it rests on as unprinted guard cells: printed as the clause alone."""
    return joined(L(text), *evidence)


def frozen_spec(S: Store, spec: str, src: str) -> List[Cell]:
    """The evidence behind "<a specification>, frozen with Lock 4": the pinned file is the one the stamped analysis file `src` names in
    its `spec` field (path, commit and SHA-256), which calls it the spec frozen in lock 4, and the file's own header says it is frozen
    at the Lock 4 tag."""
    s = S.sources[spec]
    stamped = R(S, src, "spec")
    if not str(stamped.value).startswith(f"{s.path} at {s.commit} (") or s.sha256 not in str(stamped.value):
        raise ValueError(f"{src}: its stamped spec is not the pinned {spec} ({s.path} at {s.commit})")
    head = line_of(S, spec, r"frozen (?:at the tag|in) `prereg-lock-4`", expect=1)
    return [guard(stamped, r"(the spec frozen in lock 4)", "its analysis ran under the specification frozen in lock 4"),
            guard(cell_ref(S, spec, head), r"(frozen (?:at the tag|in) `prereg-lock-4`)", "the specification is frozen at the Lock 4 tag")]


def spec1b_line(S: Store, pattern: str, why: str, section: Optional[str] = None) -> List[Cell]:
    """A guard on the one line of Study 1b's specification that matches `pattern` (one group: the words the clause rests on), and,
    with `section`, on the heading of the section it must sit in (the line is below that heading and above the next one)."""
    n = line_of(S, "spec1b", pattern, expect=1)
    out = [guard(cell_ref(S, "spec1b", n), pattern.replace(r"^\s*", "^"), why)]
    if section is not None:
        h = line_of(S, "spec1b", section, expect=1)
        nxt = [i for i in S.find_lines("spec1b", r"^## ") if i > h]
        if not h < n < (nxt[0] if nxt else n + 1):
            raise ValueError(f"spec1b line {n} is not in the section at line {h}")
        out.append(guard(cell_ref(S, "spec1b", h), section, f"that line sits in the section {section!r}"))
    return out


SPEC1B_S6 = r"^## \d+\. Descriptive outputs \((pre-registered), no tests\)$"     # Study 1b's descriptive outputs, pre-registered


def er_beside_tests(S: Store) -> List[Cell]:
    """The evidence behind "pre-specified descriptive, reported beside the test" for Study 1b's error ratio R (Edith's Q14 ruling):
    Study 1b's specification, frozen with Lock 4, lists the error-rate ratio under "Beside every test", after the tests' readings."""
    n = line_of(S, "spec1b", r"^- \*\*Beside every test:\*\*\s*$", expect=1)
    return [guard(cell_ref(S, "spec1b", n), r"^- \*\*(Beside every test):\*\*$", "the outputs beside every test"),
            guard(cell_ref(S, "spec1b", n + 1), r"^- the \*\*(error-rate ratio)\*\*, by the rules of",
                  "the error-rate ratio is reported beside every test"),
            *frozen_spec(S, "spec1b", "s1b")]


# ---------------------------------------------------------------- TAB-10


ER_TIER = "pre-specified descriptive, reported beside the test"     # the error ratio's tier in every table (Edith's Q14 ruling)



def pb(S: Store, test: List[str]) -> Cell:
    """A Study 1b test's one-sided p (5 places, as TAB-02's; Edith's TP-11), or "≤" its bootstrap floor rounded up at 5 places when no
    resample reached the margin (core.pvalue_bound; Edith's PR 27 §20). `test` is the key path of the test's block
    (…views.<view>.tests.<test>); its view stamps B."""
    view = test[:-2]
    return pvalue_bound(R(S, "s1b", *test, "p"), R(S, "s1b", *test, "z0"), R(S, "s1b", *test, "a"), R(S, "s1b", *view, "B"), dp=5)

@output("TAB-10")
@main_text
def tab_10(S: Store) -> Table:
    m5, m10 = margins(S)
    cols = ["Test", "Challenger", "Comparator", "Steps", "Puzzles", "Challenger accuracy (%)", "Opus-medium accuracy (%)",
            "Format compliance, challenger, chains / pieces (%)", "Format compliance, Opus-medium, chains / pieces (%)",
            "d (points)", "d 95% interval",
            "5-point margin: p", "5-point margin: Holm threshold", "5-point margin: reading",
            "5-point margin: shown no worse (Holm-adjusted)",
            "10-point margin: p", "10-point margin: Holm threshold", "10-point margin: reading",
            "10-point margin: shown no worse (Holm-adjusted)",
            "Error-rate ratio R", "Error-rate ratio 95% interval"]
    rows: List[List[Cell]] = []
    cost_rows: List[List[Cell]] = []
    sens_rows: List[List[Cell]] = []
    for t in TESTS_1B:
        name, ch_name, cmp_name = STUDY1B_TESTS[t]
        n = int(G(S, "s1b", "completeness", t, "N"))
        t5 = [*PRIM, "views", "as_deployed", "tests", t]
        t10 = [*SEC, "views", "as_deployed", "tests", t]
        if G(S, "s1b", *t5, "d") != G(S, "s1b", *t10, "d") or G(S, "s1b", *t5, "ci95") != G(S, "s1b", *t10, "ci95"):
            raise ValueError(f"{t}: d or its interval differs between the two margins")
        lo, hi = ci_refs(S, "s1b", join_key(*t5, "ci95"))
        er = ["error_ratios", t]
        if not G(S, "s1b", *er, "defined"):
            raise ValueError(f"{t}: error-rate ratio undefined; the table needs a branch for it")
        elo, ehi = ci_refs(S, "s1b", join_key(*er, "ci95"))
        rows.append([
            L(name), L(ch_name), L(cmp_name), integer(R(S, "s1b", "completeness", t, "N")), integer(R(S, "s1b", *t5, "n")),
            P(ch_pooled_ref(S, t), 2), P(om_pooled_ref(S, t), 2), fmt_pair(S, "hx", n, 2), fmt_pair(S, "om", n, 2),
            pts(R(S, "s1b", *t5, "d"), margin=m5), interval(lo, hi, dp=2, signed=True, bounds=(0.0, m5, m10)),
            pb(S, t5), exact(R(S, "s1b", *PRIM, "views", "as_deployed", "holm_thresholds", t)),
            quoted_reading(R(S, "s1b", *PRIM, "template", t)), text_of(R(S, "s1b", *t5, "declared"), YES_NO),
            pb(S, t10), exact(R(S, "s1b", *SEC, "views", "as_deployed", "holm_thresholds", t)),
            quoted_reading(R(S, "s1b", *SEC, "template", t)), text_of(R(S, "s1b", *t10, "declared"), YES_NO),
            num(R(S, "s1b", *er, "R"), dp=2), interval(elo, ehi, dp=2)])
        # panel 1: costs beside the tests (list price)
        cb = ["costs_beside_tests", t]
        ch_s, pc_s = shapes_of(n)
        k_ref = b2_k(S) if t == "B2" else R(S, "s1b", *cb, "k_measured")
        cost_rows.append([
            L(name), integer(k_ref), joined(L("\""), text_of(R(S, "s1b", *cb, "wording")), L("\""), sep=""),
            usd(R(S, "s1b", *cb, "challenger", "pooled", "list_usd")), usd(R(S, "s1b", *cb, "comparator", "pooled", "list_usd")),
            ratio(R(S, "s1b", *cb, "ratio_challenger_over_comparator"), dp=3),
            usd(R(S, "s1b", *cb, "challenger", ch_s, "list_usd")), usd(R(S, "s1b", *cb, "challenger", pc_s, "list_usd")),
            usd(R(S, "s1b", *cb, "comparator", ch_s, "list_usd")), usd(R(S, "s1b", *cb, "comparator", pc_s, "list_usd"))])
        # panel 2: the exposed-base sensitivity
        s5 = [SENS, "confirmatory", "primary_margin_5", "views", "as_deployed", "tests", t]
        s10 = [SENS, "confirmatory", "secondary_margin_10"]
        slo, shi = ci_refs(S, "s1b", join_key(*s5, "ci95"))
        sr = [SENS, "error_ratios", t]
        selo, sehi = ci_refs(S, "s1b", join_key(*sr, "ci95"))
        sens_rows.append([
            L(name), integer(R(S, "s1b", SENS, "bases_per_test", t)), pts(R(S, "s1b", *s5, "d"), margin=m5),
            interval(slo, shi, dp=2, signed=True, bounds=(0.0, m5, m10)), pb(S, s5),
            quoted_reading(R(S, "s1b", SENS, "confirmatory", "primary_margin_5", "template", t)),
            quoted_reading(R(S, "s1b", *s10, "template", t)),
            num(R(S, "s1b", *sr, "R"), dp=2), interval(selo, sehi, dp=2)])
    # Panel 1's ratio column holds B2's spend share beside B1's and B3's cost ratios, so it names both (Edith, proof 3, p. 92; as Table S14)
    cost_cols = ["Test", "k (measured)", "Wording", "Challenger list cost per answer ($)", "Opus-medium list cost per answer ($)",
                 "Spend share or cost ratio (challenger / Opus-medium)", "Challenger list cost, chain ($)", "Challenger list cost, pieces ($)",
                 "Opus-medium list cost, chain ($)", "Opus-medium list cost, pieces ($)"]
    sens_cols = ["Test", "Puzzles (exposed ones left out)", "d (points)", "d 95% interval", "5-point margin: p",
                 "5-point margin: reading", "10-point margin: reading", "Error-rate ratio R", "Error-rate ratio 95% interval"]
    # polish §7.3: a column with one value in every row moves to a note (each is checked to print one value)
    FMT_OM, READ10, SHOWN10 = ("Format compliance, Opus-medium, chains / pieces (%)", "10-point margin: reading",
                               "10-point margin: shown no worse (Holm-adjusted)")
    const = fold_constants(cols, rows, ["Comparator", FMT_OM, READ10, SHOWN10])
    if const[SHOWN10].printed != "yes" or const["Comparator"].printed != "Opus-medium":
        raise ValueError("TAB-10's constant columns no longer read as the note says")
    sens_const = fold_constants(sens_cols, sens_rows, [READ10])
    holm_check(S, PRIM)
    holm_check(S, SEC)
    holm_check(S, [SENS, "confirmatory", "primary_margin_5"])           # Panel 2's shown-no-worse column follows Holm's order too
    holm_check(S, [SENS, "confirmatory", "secondary_margin_10"])
    er_B = _error_ratio_checks(S)
    # the ruled reading's column must exist in the table (the note names it); Panel 2 has none, so the note gives its ruled readings
    ruled = "5-point margin: shown no worse (Holm-adjusted)"
    if ruled not in cols or ruled in sens_cols:
        raise ValueError(f"the column {ruled!r} that the readings note names is not in the table only")
    sens5 = [SENS, "confirmatory", "primary_margin_5", "views", "as_deployed", "tests"]
    # Panel 2's ruled readings at the 5-point margin, in words, from the same stamped flags (the sentence needs both outcomes)
    sens_flags = {x: text_of(R(S, "s1b", *sens5, x, "declared"), YES_NO) for x in TESTS_1B}
    shown_b = [x for x in TESTS_1B if sens_flags[x].raw is True]
    not_b = [x for x in TESTS_1B if sens_flags[x].raw is False]
    if not shown_b or not not_b or len(shown_b) + len(not_b) != len(TESTS_1B):
        raise ValueError("Panel 2's ruled readings no longer split the tests into shown and not shown: reword the readings note")

    def test_names(ts: List[str]) -> str:
        return ("Test " if len(ts) == 1 else "Tests ") + (ts[0] if len(ts) == 1 else ", ".join(ts[:-1]) + " and " + ts[-1])
    readings = note("Readings in quotation marks are the Study 1b file's own template words: \"holds\" only if the test is no worse in "
                    "all three views; an inconclusive test reads \"inconclusive (could not show)\" and is never called worse. The ruled "
                    "reading, shown no worse (Holm-adjusted), is the column \"" + ruled + "\" of this table. Panel 2 has no such "
                    "column: at the 5-point margin",
                    with_evidence(f"{test_names(shown_b)} {'is' if len(shown_b) == 1 else 'are'} shown no worse (Holm-adjusted) and "
                                  f"{test_names(not_b)} {'is' if len(not_b) == 1 else 'are'} not.",
                                  [unprinted(c, "Panel 2's Holm-adjusted result at the 5-point margin, one per test")
                                   for c in sens_flags.values()]))
    d_note = note("d is the same at both margins: Haiku-max (or its vote) minus Opus-medium, in points, paired over puzzles. A "
                  "positive d means Haiku-max scored higher.")
    er_ev = er_beside_tests(S)
    r_note = note("Error-rate ratio R is the challenger's error rate divided by Opus-medium's, over the same puzzles (an error rate is "
                  "the share of answers not right, the complement of the accuracy); R above one means the challenger made more errors.",
                  with_evidence("R is " + ER_TIER + ": Study 1b's specification, frozen with Lock 4, reports it beside every test, "
                                "and it is not part of any test's reading.", er_ev),
                  "Its 95% interval is a bootstrap over puzzles; an unbounded upper end means Opus-medium made no error in too many "
                  "resamples for the interval to have a finite top.")
    k_note = note("The B2 challenger is the vote of k Haiku-max samples, k =", integer(b2_k(S)),
                  "(cost-matched with Opus-medium, by the pre-registered cost-matched k rule).")
    fmt_note = _b2_format_note()
    notes = [
        readings,
        note("Holm's correction runs within Study 1b only; Study 1 and Study 1b are never pooled. Shown no worse (Holm-adjusted) is yes "
             "where p is below the test's Holm threshold at that margin, in Holm's step-down order: a test is shown no worse "
             "(Holm-adjusted) only if every test before it in Holm's order is too."),
        d_note, r_note, k_note, fmt_note,
        note("Costs: list price per answer; the vote at k costs k answers. Each test's cost wording, k and per-shape costs (B2's included) "
             "are in Panel 1 (costs). Its ratio column holds Test B2's spend share (the vote's cost over its cost-matched comparator's) "
             "and the cost ratios of Tests B1 and B3."),
        note("Panel 2 (sensitivity) leaves out the puzzles that were exposed before the run (the file lists them under excluded); it "
             "is a sensitivity, not a test."),
        note("Panel 1's wordings are the Study 1b file's own, in quotation marks; its \"tries\" are the paper's samples."),
        # one note for the constant columns of the table and of Panel 2 (Edith, proof 3, p. 92: the two notes repeated one another); Panel 2
        # reads the same at the 10-point margin as the table does (checked), so the one sentence covers both
        note("Columns that print one value in every row are left out. In every test the comparator is",
             joined(const["Comparator"], L(", whose format compliance is"), sep=""),
             joined(prose_pct(const[FMT_OM]), L("(chains / pieces);")),
             "at the 10-point margin every test reads", const[READ10],
             with_evidence("and is shown no worse (Holm-adjusted).",
                           [unprinted(const[SHOWN10], "each test's Holm-adjusted result at the 10-point margin")]),
             with_evidence("Panel 2's 10-point readings are the same.",
                           [unprinted(sens_const[READ10], "Panel 2's 10-point reading, the same in every row and the same as the table's")])),
    ]
    if sens_const[READ10].printed != const[READ10].printed:
        raise ValueError("Panel 2's 10-point reading is no longer the table's; the merged note must name both")
    t = Table([L(c) for c in cols], rows, notes, {})
    t.panels = [("Costs beside the tests, list price", Table([L(c) for c in cost_cols], cost_rows)),
                ("Sensitivity: exposed puzzles left out", Table([L(c) for c in sens_cols], sens_rows))]

    def caption(price: List[Cell]) -> Dict[str, List[Cell]]:
        return {
            "tier": [with_evidence("confirmatory (Holm within Study 1b only); error-rate ratio R: " + ER_TIER, er_ev)],
            "study": [L("Study 1b: Tests B1 and B2 at"), integer(R(S, "s1b", "completeness", "B1", "N")), L("steps, Test B3 at"),
                      integer(R(S, "s1b", "completeness", "B3", "N")), L("steps")],
            "set": test_sets(S),
            "n": [L("puzzles:"), integer(R(S, "s1b", *PRIM, "views", "as_deployed", "tests", "B1", "n")), L("(B1, B2);"),
                  integer(R(S, "s1b", *PRIM, "views", "as_deployed", "tests", "B3", "n")), L("(B3);"), *test_tries(S)],
            "interval": [joined(joined(L("d: paired BCa bootstrap, B ="), integer(R(S, "s1b", *PRIM, "views", "as_deployed", "B"))),
                                L(";"), sep=""), L("error-rate ratio R: bootstrap over puzzles, B ="), integer(er_B)],
            "price": price}
    # the cost beside each test is pre-registered at list price (Study 1b's specification, "Beside every test": the cost)
    cost_ev = spec1b_line(S, r"^\s*- \*\*the cost\*\*, by .+ \((list price); ", "the cost beside every test is at list price")
    t.caption = caption([with_evidence("list price per answer (pre-registered)", cost_ev)])
    t.main_table = _tab10_paper(S, t.caption, m5, m10, er_ev, er_B)
    # the supplement's layouts (batch g): sideways pages for a table of one or two inches would each be nearly empty (polish §1.4), so
    # the full table is split in three portrait parts at footnotesize (what was run, with the accuracies and the format compliance; d
    # with the 5-point margin's test and reading; the 10-point margin's test beside the error ratio reported with it) and the cost
    # panel in two (the cost beside each test, then the per-shape costs); the sensitivity panel is a float. The notes of the whole
    # table print under the last float, the sensitivity panel.
    split(t, False, [["Challenger", "Steps", "Puzzles", "Challenger accuracy (%)", "Opus-medium accuracy (%)",
                      "Format compliance, challenger, chains / pieces (%)"],
                     ["d (points)", "d 95% interval", "5-point margin: p", "5-point margin: Holm threshold", "5-point margin: reading",
                      "5-point margin: shown no worse (Holm-adjusted)"],
                     ["10-point margin: p", "10-point margin: Holm threshold", "Error-rate ratio R", "Error-rate ratio 95% interval"]])
    t.font = "footnotesize"
    costs, sens = t.panels[0][1], t.panels[1][1]
    split(costs, False, [["k (measured)", "Wording", "Challenger list cost per answer ($)", "Opus-medium list cost per answer ($)",
                          "Spend share or cost ratio (challenger / Opus-medium)"],
                         ["Challenger list cost, chain ($)", "Challenger list cost, pieces ($)", "Opus-medium list cost, chain ($)",
                          "Opus-medium list cost, pieces ($)"]])
    costs.font = "footnotesize"
    sens.layout, sens.font = "float", "footnotesize"
    return print_rules(t)


# The ties-counted-wrong row of TAB-10.main: Test B2's pooled d with every tie scored wrong (post hoc), with Decision "—" (the row carries d
# and its interval only). Its Shape cell reads "ties†": the label names what the row is, so it no longer reads as a second "B2 pooled" row
# that differs by a dagger only (Edith's checker, proof 3, A.22), and the dagger marks it post hoc, as everywhere in the paper; the note
# defines the row ("† Pooled, ties counted wrong (post hoc): ..." in TAB-11's words, shortened: the vote, the tied top answers and the right
# one named exactly, as the full TAB-11 says). A short label, because a long one wraps the narrow Shape column over four lines (Edith, proof 3,
# A.22): the checker's "ties wrong†" wraps over two lines in the built table, and joined with a no-break space it widens the column and leaves
# Decision three lines (measured, TAB-10.main 2.60 in against 2.34 in); "ties†" keeps one line and Decision at two. The row sits in a group
# of its own, with a little space above it, so it reads as a row of the table and not as stray text (Edith, p. 31).
TIES_LABEL = "ties\u2020"
TIES_DEFINITION = ("\u2020\u00a0Pooled, ties counted wrong (post hoc): a vote whose tied top answers include the right one scores nothing.")
# (the dagger is tied to its definition with a no-break space, so that the note never ends a line on the dagger: Edith, proof 4, p. 32)


def _decision_both(S: Store, t5: List[str], t10: List[str]) -> Cell:
    """TAB-10.main's Decision cell for a test: both margins' decision (Vision's plan §3). Table 2's words (overview._decision, reused as
    is) already give both where the test is inconclusive at the primary margin ("inconclusive at 5; shown no worse by > 10
    (Holm-adjusted)") and for a test that is worse; where the test is shown no worse at the primary margin, Table 2 prints that margin
    only, so this cell adds the secondary's reading in the same words ("shown no worse by > 5 and by > 10 (Holm-adjusted)"), with the
    secondary's stamped reading and Holm flag checked. Both margins are read from the stamped margins, never typed."""
    reading, declared = R(S, "s1b", *t5, "reading"), R(S, "s1b", *t5, "declared")
    sec = (R(S, "s1b", *t10, "reading"), R(S, "s1b", *t10, "declared"), R(S, "s1b", *SEC, "margin"))
    m = R(S, "s1b", *PRIM, "margin")
    if not (declared.value is True and reading.value == "non-inferior"):
        return _decision(S, reading, declared, sec, m)
    if not (sec[0].value == "non-inferior" and sec[1].value is True):
        raise ValueError(f"{t5[-1]}: shown no worse at the primary margin but not at the secondary one; no decision words for it")
    if not abs(float(m.value)) < abs(float(sec[2].value)):
        raise ValueError(f"{t5[-1]}: the primary margin is not the narrower one")
    size = lambda r, what: num_d(derive(what, lambda x: abs(x), r), dp=0)              # noqa: E731
    c = joined(L("shown no worse by >"), size(m, "the primary margin's size"), L("and by >"), size(sec[2], "the secondary margin's size"),
               L("(Holm-adjusted)"))
    return Cell(c.printed, raw=[reading.value, declared.value, sec[0].value, sec[1].value], refs=(reading, declared, m, *sec),
                formula=DECISION_FORMULA)


def _no_holm(c: Cell) -> Cell:
    """A Decision cell without its closing "(Holm-adjusted)" (Edith, p. 32: Decision takes one or two lines; the note says once that the
    decisions are Holm-adjusted). The cell keeps its refs, raw value and formula; a cell that does not end so (a decision that is not a
    Holm-adjusted one) refuses, since the note would no longer hold."""
    tail = " (Holm-adjusted)"
    if not c.printed.endswith(tail):
        raise ValueError(f"TAB-10's paper decision {c.printed!r} is not a Holm-adjusted one; the note says every decision is")
    return Cell(c.printed[:-len(tail)], kind=c.kind, raw=c.raw, refs=c.refs, formula=c.formula, bold=c.bold)


def _tab10_paper(S: Store, full_caption: Dict[str, List[Cell]], m5: float, m10: float, er_ev: List[Cell], er_B: Ref) -> Table:
    """"Study 1b's tests in full", the paper's version of TAB-10 (Vision's plan §3; D-161; Edith's proof-2 rows for p. 32): for each of
    Tests B1-B3 one pooled row (the test: both sides' accuracy, d with its 95% interval, the error-rate ratio at one decimal and the
    decision at both margins, `_decision_both` without its "(Holm-adjusted)", which the note says once) and, for B2, the
    ties-counted-wrong row of TAB-11's Panel 1, after B2's pooled row and set apart by a little space (post hoc: d and its interval
    only; its Shape cell reads "ties†", which the note defines; Decision "—"). The chain and pieces rows that the merge with TAB-11 put
    here are gone (Edith, proof 4, p. 32: the caption named the wrong method and no tier for those six rows; TAB-11.main prints them with
    their own method and tier). Every row carries its test (the cells file and the CSV keep it); the table prints it once per test
    (`once`) and sets the tests apart (`groups`, polish §7.7). The Steps column is left out: the caption's study fact names each test's
    steps. The error-rate ratio's point and interval are tied (no-break space) so the cell never splits (Edith: widen the ratio column).
    Panel 1's three views print as one clause of the caption's study fact ("leaving out refusals or truncations changes no test"; the two
    printed notes had no room for it, polish §7.5), which holds because every test is identical in all three views and no refusal or
    truncation touched a test's samples (`_views_agree`, checked). Percentages and points at one decimal from the same refs as the full
    tables, with the one-more-decimal guard at the margins and at 0, except for the ties-counted-wrong row's d, which is -0.03 and prints
    "0.0" (polish §2.3: zero has no sign, and a guard cell is no help in a one-decimal column); the error-rate ratio and its interval
    print at one decimal (polish §2.1, amended 2026-10-19). Every number column holds numbers or empty cells only, so it is
    right-aligned. Its caption facts are TAB-10's, in the paper's words, under the six standard keys; no analysis is named by its number
    in a paper version."""
    bnd = (0.0, m5, m10)

    def d_ci(d: Ref, lo: Ref, hi: Ref, zero_ok: bool = False) -> Cell:
        # tied (no-break space): every cell of the column stays on one line, so the estimates and the brackets line up (Edith, proof 4)
        return joined(num(d, dp=1, signed=True, bounds=(m5, m10) if zero_ok else bnd), interval(lo, hi, dp=1, signed=False, bounds=bnd),
                      sep=NBSP)

    _views_agree(S)
    _b2_ties_check(S)
    rows: List[List[Cell]] = []
    groups: List[int] = []
    unbounded = False
    singles: List[str] = []
    for t in TESTS_1B:
        n = int(G(S, "s1b", "completeness", t, "N"))
        t5 = [*PRIM, "views", "as_deployed", "tests", t]
        t10 = [*SEC, "views", "as_deployed", "tests", t]
        key = "v" if t == "B2" else "h"
        if STUDY1B_TESTS[t][1] != ("Haiku-max vote" if t == "B2" else "One Haiku-max sample"):
            raise ValueError(f"{t}: the names table's challenger is {STUDY1B_TESTS[t][1]!r}, not the one the paper note names")
        if t != "B2":
            singles.append(t)
        # the pooled test (each side's accuracy and d) is the mean of its two shapes, so "pooled" says what the row is
        for side, pooled in ((key, ch_pooled_ref(S, t).value), ("o", om_pooled_ref(S, t).value), ("d", G(S, "s1b", *t5, "d"))):
            _same(pooled, sum(G(S, "s1b", "per_form", t, s, side, "mean") for s in shapes_of(n)) / 2,
                  f"{t}: the pooled {side} is the mean of its two shapes")
        er = ["error_ratios", t]
        elo, ehi = ci_refs(S, "s1b", join_key(*er, "ci95"))
        unbounded = unbounded or ehi.value == "unbounded"
        if rows:
            groups.append(len(rows))
        rows.append([L(t), L("pooled"), P(ch_pooled_ref(S, t), 1), P(om_pooled_ref(S, t), 1),
                     d_ci(R(S, "s1b", *t5, "d"), *ci_refs(S, "s1b", join_key(*t5, "ci95"))),
                     joined(num(R(S, "s1b", *er, "R"), dp=1), interval(elo, ehi, dp=1), sep="\u00a0"), _no_holm(_decision_both(S, t5, t10))])
        if t == "B2":
            groups.append(len(rows))                  # a little space above it: a post hoc row of its own, not a stray line (Edith, p. 31)
            # after B2's pooled row (it is B2's pooled d, rescored); the full tables print no accuracies for this row (TAB-11's Panel 1
            # gives d and its interval only): empty, not a dash; no decision: a dash
            rows.append([L(t), L(TIES_LABEL), EMPTY, EMPTY,
                         d_ci(R(S, "fa13", *FA13_TIES, "d"), *ci_refs(S, "fa13", join_key(*FA13_TIES, "ci95")), zero_ok=True), EMPTY, DASH])
    k = b2_k(S)
    if not int(k.value) > 1:
        raise ValueError("B2's k is not a vote")
    # the notes (two lines together in TeX, polish §7.5; measured, not estimated): the decisions' Holm adjustment, the error-rate ratio's
    # unbounded end (its definition is the Method legend's; the condition is the full table's: too many draws, not one) and the
    # ties-counted-wrong scoring (TAB-11's words); the views, the challenger, d and the 95% brackets are in the caption facts and the
    # headers
    notes = [note("Decisions: Holm-adjusted."),
             note((UNBOUNDED_NOTE + " " if unbounded else "")
                  + TIES_DEFINITION)]
    return paper_table(["Test", "Shape", "Challenger (%)", "Opus-medium (%)", "d (points) [95% interval]",
                        "Error-rate ratio [95% interval]", "Decision (margins in points)"],
                       rows, notes, _tab10_paper_caption(S, full_caption, er_ev, er_B, singles, k), layout="float",
                       text_cols=(0, 1, 6), groups=groups, once=[0], font="footnotesize")


def _per_shape_d_evidence(S: Store) -> List[Cell]:
    """The records behind "paired percentile bootstrap over puzzles, with the file's draws" for the per-shape d intervals (TAB-11's
    rows; unprinted guards): the driver as run takes each puzzle's challenger minus comparator as d, gives each per-shape block's
    interval by _boot (a percentile cluster bootstrap over puzzles) with the draws it is given, and passes per_form the draws the file
    stamps."""
    d = S1B_DRIVER
    return [
        _code_line(S, d, r'"d": \{b: (c\[b\] - o\[b\]) for b in bases\}', "per_form", "per_form's d is paired: each puzzle's challenger "
                   "minus its comparator"),
        _code_line(S, d, r'"ci95": _boot\(bases, v, (f"1b:\{t\}:\{n\}:\{shape\}:\{s\}"), draws\)', "per_form",
                   "each per-shape interval is _boot under its own name"),
        _code_line(S, d, r'''"""The cluster bootstrap \(curve\.cluster_bootstrap, (percentile 95%)\) of the mean over drawn base puzzles''',
                   "_boot", "_boot is a percentile bootstrap"),
        _code_line(S, d, r'"per_form": (per_form\(rows, k, dv\)),', "analyse", "the per-test intervals get the file's draws"),
        _code_line(S, d, r'"constants": \{.*("draws": dv),', "analyse", "the file stamps the draws the driver used"),
    ]


def _tab10_paper_caption(S: Store, full: Dict[str, List[Cell]], er_ev: List[Cell], er_B: Ref, singles: Sequence[str],
                         k: Ref) -> Dict[str, List[Cell]]:
    """TAB-10.main's caption facts: TAB-10's for the pooled rows (the tests) and TAB-11's Panel 1's for the ties-counted-wrong row (post
    hoc, with a paired BCa bootstrap), in the paper's words (D-161: puzzle, sample; no analysis is named by its number), under the six
    standard keys (the tier names each group of rows; the note defines the ties-counted-wrong scoring). The study fact names the
    challenger of each test and the interval fact defines d, since the paper's notes carry neither (two lines); there is no cost
    column. The chain and pieces rows are TAB-11.main's, with their own method and tier (Edith, proof 4, p. 32)."""
    test_tries(S)                                                  # the designed samples on both sides of every test (checks)
    n_ref = {t: R(S, "s1b", *PRIM, "views", "as_deployed", "tests", t, "n") for t in TESTS_1B}
    if n_ref["B1"].value != n_ref["B2"].value:
        raise ValueError("B1 and B2 are on different numbers of puzzles; the caption gives one count for both")
    return {
        "tier": [with_evidence("pooled rows (the tests): confirmatory (Holm within Study 1b only); error-rate ratio: " + ER_TIER
                               + "; the ties-counted-wrong row for Test B2: post hoc", er_ev)],
        "study": [L("Study 1b: Tests B1 and B2 at"), integer(R(S, "s1b", "completeness", "B1", "N")), L("steps, Test B3 at"),
                  integer(R(S, "s1b", "completeness", "B3", "N")),
                  L("steps; the challenger is one Haiku-max sample in Tests " + " and ".join(singles) + " and the vote of"), integer(k),
                  L("Haiku-max samples in Test B2, each against Opus-medium; leaving out refusals or truncations changes no test")],
        "set": full["set"],
        "n": [L("puzzles:"), integer(n_ref["B1"]), L("(B1, B2);"), integer(n_ref["B3"]),
              L("(B3), each in both shapes; samples per puzzle and shape: Haiku-max"),
              integer(R(S, "s1b", "constants", "designed_tries", "hx")), L("and Opus-medium"),
              integer(R(S, "s1b", "constants", "designed_tries", "om"))],
        "interval": [L("d: the challenger's accuracy minus Opus-medium's, in points, paired over puzzles; 95% intervals: paired BCa "
                       "bootstrap, B ="), joined(_side_panel_B(S), L(";"), sep=""), L("error-rate ratio: bootstrap over puzzles, B ="), integer(er_B)],
        "price": [L("not applicable (no cost column)")]}


def _error_ratio_checks(S: Store) -> Ref:
    """The checks behind the error-ratio note and caption (nothing is printed from them but the shared B): R is the challenger's summed
    errors over Opus-medium's (E_ch / E_cmp, the same ratio as their error rates in points), an unbounded upper end comes with resamples
    in which Opus-medium made no error, and the three tests used one number of resamples (returned for the caption)."""
    B = R(S, "s1b", "error_ratios", "B1", "B")
    for t in TESTS_1B:
        er = ["error_ratios", t]
        _same(G(S, "s1b", *er, "R"), G(S, "s1b", *er, "E_ch") / G(S, "s1b", *er, "E_cmp"), f"{t}: R against E_ch / E_cmp")
        _same(G(S, "s1b", *er, "R"), G(S, "s1b", *er, "e_ch_points") / G(S, "s1b", *er, "e_cmp_points"), f"{t}: R against the error rates")
        _same(G(S, "s1b", *er, "e_ch_points"), 100.0 - _f(ch_pooled_ref(S, t).value), f"{t}: the challenger's error rate, 100 - accuracy")
        _same(G(S, "s1b", *er, "e_cmp_points"), 100.0 - _f(om_pooled_ref(S, t).value), f"{t}: Opus-medium's error rate, 100 - accuracy")
        if G(S, "s1b", *er, "ci95", 1) == "unbounded" and not G(S, "s1b", *er, "share_replicates_E_cmp_zero") > 0:
            raise ValueError(f"{t}: an unbounded error-ratio end without resamples in which Opus-medium made no error")
        if G(S, "s1b", *er, "B") != B.value:
            raise ValueError(f"{t}: the error-ratio bootstrap used another number of resamples")
    return B


def _b2_format_note() -> List[Cell]:
    """Final-check finding F7: the compliance printed for the B2 vote is its single samples'."""
    return note("For Test B2 the challenger's format compliance is that of the single Haiku-max samples the vote is taken over.")


# ---------------------------------------------------------------- TAB-11


def _view_reading(S: Store, tv: List[str], margin: Ref) -> Cell:
    """A test's reading in one view at one margin, in TAB-10's label wording (Edith's proof-2 row for the three-views panel; D-161):
    "shown no worse by > 5 (Holm-adjusted)" or "inconclusive at 5", from the view's stamped reading and Holm flag (each reading and
    flag agree, or the build stops) and the stamped margin."""
    reading, declared = R(S, "s1b", *tv, "reading"), R(S, "s1b", *tv, "declared")
    size = num_d(derive("the margin's size", lambda x: abs(x), margin), dp=0)
    if reading.value == "non-inferior" and declared.value is True:
        c = joined(L("shown no worse by >"), size, L("(Holm-adjusted)"))
    elif reading.value == "inconclusive" and declared.value is False:
        c = joined(L("inconclusive at"), size)
    else:
        raise ValueError(f"{join_key(*tv)}: no reading words for reading {reading.value!r}, Holm-adjusted {declared.value!r}")
    return Cell(c.printed, raw=[reading.value, declared.value], refs=(reading, declared, margin), formula=DECISION_FORMULA)


def _views_agree(S: Store) -> None:
    """The check behind TAB-11's note that the three views agree because no refusal or truncation touched a test arm: each test's
    stamped result is the same in all views at both margins, and item 16 counts no refusal, truncation or missing call for either test
    arm on either shape at the test's length (nothing is printed from it)."""
    for fam in (PRIM, SEC):
        for t in TESTS_1B:
            got = [G(S, "s1b", *fam, "views", vk, "tests", t) for vk, _ in VIEWS]
            if any(g != got[0] for g in got[1:]):
                raise ValueError(f"{join_key(*fam)} {t}: the views differ; TAB-11's note no longer holds")
    for t in TESTS_1B:
        n = int(G(S, "s1b", "completeness", t, "N"))
        sid = G(S, "s1b", "completeness", t, "set_id")
        for tag in ("hx", "om"):
            for s in shapes_of(n):
                r = G(S, "s1b", *FRT.split("."), "item_16_rates", sid, f"{tag} {s}")
                if r["refusals_by_category"] or r["truncations"]["count"] or r["missing"]["count"]:
                    raise ValueError(f"{t} {tag} {s}: a refusal, truncation or missing call touched a test arm")


def _per_form_twin(S: Store, t: str, n: int, side: str, s: str) -> List[Any]:
    """The effort-sweep (or vote-curve) block for the same arm, shape and base puzzles as per_form.<t>.<s>.<side>."""
    if side == "v":
        return ["descriptive", "vote_curve_n16", "points", point_index(S, G(S, "s1b", "descriptive", "vote_curve_n16", "k_from_k_json")), s]
    return ["descriptive", "arms", f"{'hx' if side == 'h' else 'om'}@{n}", s]


S1B_DRIVER = "s1b_driver_s1b"
SPEC1B_S4 = r"^## \d+\. (The confirmatory tests): B1, B2, B3 \(F-3\)$"          # Study 1b's tests section (its "Per shape" outputs)


def _in_def(S: Store, src: str, line: int, fn: str) -> None:
    """The line sits in the body of the function `fn` of a pinned code file (the nearest `def` above it is `fn`'s)."""
    defs = [i for i in S.find_lines(src, r"^def \w+\(") if i < line]
    if not defs or defs[-1] not in S.find_lines(src, rf"^def {re.escape(fn)}\("):
        raise ValueError(f"{src} line {line} is not in {fn}")


def _code_line(S: Store, src: str, pattern: str, fn: str, why: str) -> Cell:
    """A guard on the one line of a pinned code file that matches `pattern` (one group), which must sit in the function `fn`."""
    n = line_of(S, src, pattern, expect=1)
    _in_def(S, src, n, fn)
    return guard(cell_ref(S, src, n), pattern, why)


def _spec_draws(S: Store, pattern: str, why: str, section: str) -> List[Cell]:
    """spec1b_line for a line that names a bootstrap's draws (group 2, e.g. '2,000'): they must be the Study 1b file's stamped draws."""
    ev = spec1b_line(S, pattern, why, section=section)
    drawn = extract(cell_ref(S, "spec1b", line_of(S, "spec1b", pattern, expect=1)), pattern.replace(r"^\s*", "^"), group=2)
    if int(str(drawn.raw).replace(",", "")) != G(S, "s1b", "constants", "draws"):
        raise ValueError(f"Study 1b's specification names {drawn.raw} draws, not the file's {G(S, 's1b', 'constants', 'draws')}")
    return ev


def _same_resampling(S: Store) -> List[Cell]:
    """The records behind "separate bootstrap draws ... differ only by resampling" (unprinted guards): Study 1b's specification gives
    the per-test intervals per shape (section 4) and the effort sweep's multi-try intervals (section 6) as a cluster bootstrap over base
    puzzles with the draws the file stamps; the driver as run computes the per-test, effort-sweep and vote-curve intervals with the one
    `_boot` (the cluster bootstrap over base puzzles), each under its own name and with those draws; and the bootstrap seeds its draws
    by the name, so two names are two separate draws."""
    d, c = S1B_DRIVER, "s1b_curve_py_s1b"
    curve_seed = _code_line(S, c, r"rng = random\.Random\((derive_seed\(seed, name\))\)", "cluster_bootstrap",
                            "the cluster bootstrap seeds its draws by the bootstrap's name")
    return [
        *_spec_draws(S, r"^\s*- \*\*Per shape:\*\* h, o, v and d for each shape, with a (cluster bootstrap over base puzzles) "
                        r"\((\d,\d{3}) draws, seed \d+\)\. Descriptive\.$",
                     "the per-test intervals per shape are a cluster bootstrap over base puzzles", SPEC1B_S4),
        *_spec_draws(S, r"^\s*- Each point carries its interval: a (cluster bootstrap for multi-try arms), Clopper–Pearson for one-try "
                        r"arms, (\d,\d{3}) draws, seed$",
                     "the effort sweep's multi-try intervals are a cluster bootstrap", SPEC1B_S6),
        guard(R(S, "s1b", "constants", "draws"), r"^(\d+)$", "the bootstrap draws the Study 1b file used"),
        _code_line(S, d, r'"""The (cluster bootstrap) \(curve\.cluster_bootstrap, percentile 95%\) of the mean over drawn base puzzles',
                   "_boot", "_boot is the cluster bootstrap over base puzzles"),
        _code_line(S, d, r'lambda s: math\.fsum\(values\[b\] for b in s\) / len\(s\), (name, draws=draws),', "_boot",
                   "_boot draws under the name and with the draws it is given"),
        _code_line(S, d, r'"ci95": _boot\(bases, v, (f"1b:\{t\}:\{n\}:\{shape\}:\{s\}"), draws\)', "per_form",
                   "each per-test interval is _boot under its own name"),
        _code_line(S, d, r'name = (f"1b:\{su\.name\}:\{n\}:\{shape\}")', "_accuracy", "the effort sweep's per-shape bootstrap name"),
        _code_line(S, d, r'd\.update\(ci95=_boot\(bases, per\[shape\], name, draws\), interval="(cluster bootstrap)", '
                         r'bootstrap_name=name\)', "_accuracy", "the effort sweep's per-shape interval of a multi-try arm is _boot"),
        _code_line(S, d, r'"ci95": _boot\(sorted\(v\), v, (f"1b:hx-vote:\{n\}:\{label\}"), draws\)', "vote_curve",
                   "each vote-curve interval is _boot under its own name"),
        _code_line(S, d, r'out\.update\((_accuracy\(ctx, ar, su, n, draws, final_only=False\))\)', "arm_point",
                   "an effort-sweep arm's entry is _accuracy with the draws it is given"),
        _code_line(S, d, r'= (arm_point\(ctx, rows, su, int\(s\["n"\]\), draws, h\))', "descriptive_arms",
                   "every effort-sweep arm gets the draws"),
        _code_line(S, d, r'arms = (descriptive_arms\(ctx, rows, plan, dv\))', "analyse", "the effort sweep gets the file's draws"),
        _code_line(S, d, r'"per_form": (per_form\(rows, k, dv\)),', "analyse", "the per-test intervals get the file's draws"),
        _code_line(S, d, r'"vote_curve_n16": (vote_curve\(ctx, rows, k, dv\)),', "analyse", "the vote curve gets the file's draws"),
        _code_line(S, d, r'"constants": \{.*("draws": dv),', "analyse", "the file stamps the draws the driver used"),
        curve_seed]


def _twins_differ_only_by_resampling(S: Store) -> Tuple[List[Cell], bool]:
    """The checks behind TAB-11's and TAB-12's note (Edith's Q7) that a per-test interval (per_form) and the effort-sweep (or, for the
    B2 vote, the vote-curve) interval for the same arm and shape come from separate bootstrap draws over the same base puzzles and differ
    only by resampling: the two blocks have the same point and the same base puzzles; each stamped bootstrap name is the one the driver
    gives that interval (per test, effort sweep, vote curve), so the two names differ; the effort-sweep interval is a cluster bootstrap;
    and the records in `_same_resampling` (returned as the note's evidence) say all three are the same cluster bootstrap with the same
    draws, seeded by the name. A pair that collapsed to one value in both must take the same exact interval from free analysis 4 (the
    second value returned says one did, for the note's closing clause); a pair that collapsed in one only refuses the build (the note
    does not cover it)."""
    vote_names = str(G(S, "s1b", "descriptive", "vote_curve_n16", "bootstrap_names"))
    if "<" not in vote_names:
        raise ValueError("the vote curve's bootstrap names no longer have the form '<prefix><form|pooled> ...'")
    both = False
    for t in TESTS_1B:
        n = int(G(S, "s1b", "completeness", t, "N"))
        for s in shapes_of(n):
            for side in ("v" if t == "B2" else "h", "o"):
                pf, tw = ["per_form", t, s, side], _per_form_twin(S, t, n, side, s)
                if G(S, "s1b", *pf, "mean") != G(S, "s1b", *tw, "mean") or G(S, "s1b", *pf, "n_base") != G(S, "s1b", *tw, "n_base"):
                    raise ValueError(f"{t} {s} {side}: the per-test and effort-sweep blocks differ in point or base puzzles")
                name = str(G(S, "s1b", *pf, "bootstrap_name"))
                if name != f"1b:{t}:{n}:{s}:{side}":
                    raise ValueError(f"{t} {s} {side}: the per-test bootstrap name {name!r} is not the driver's per_form name")
                if side == "v":
                    if not vote_names.startswith(f"1b:hx-vote:{n}:<"):
                        raise ValueError(f"the vote curve's bootstrap names {vote_names!r} are not the driver's vote_curve names")
                    if name.startswith(vote_names.split("<")[0]):
                        raise ValueError(f"{t} {s}: the per-test vote interval shares the vote curve's bootstrap draw")
                else:
                    tag = "hx" if side == "h" else "om"
                    if (G(S, "s1b", *tw, "bootstrap_name") != f"1b:{tag}:{n}:{s}" or name == G(S, "s1b", *tw, "bootstrap_name")
                            or G(S, "s1b", *tw, "interval") != "cluster bootstrap"):
                        raise ValueError(f"{t} {s} {side}: the per-test and effort-sweep intervals are not two separate bootstrap draws")
                collapsed = [len(set(G(S, "s1b", *b, "ci95"))) == 1 for b in (pf, tw)]
                if collapsed[0] != collapsed[1]:
                    raise ValueError(f"{t} {s} {side}: one of the two intervals collapsed and the other did not; the note does not cover it")
                if all(collapsed):
                    ex = [fa4_exact(S, "s1b", join_key(*b)) for b in (pf, tw)]
                    if None in ex or len({(e.lo.value, e.hi.value, e.x, e.n) for e in ex}) != 1:     # type: ignore[union-attr]
                        raise ValueError(f"{t} {s} {side}: collapsed in both, but free analysis 4 gives them different exact intervals")
                    both = True
    return _same_resampling(S), both


def separate_draws(S: Store, what: str) -> List[Cell]:
    """Edith's Q7 note, shared by TAB-11 and TAB-12: `what` names the two sets of intervals; the sentence rests on the records in
    `_same_resampling` (unprinted), and closes on the pairs that collapsed in both, where there is one exact interval and no resampling."""
    ev, both = _twins_differ_only_by_resampling(S)
    return note(with_evidence(what + " come from separate bootstrap draws over the same puzzles, with the same points, and differ "
                              "only by resampling, so their ends can differ slightly"
                              + ("; where both collapsed to one value, both show the same exact interval." if both else "."), ev))


FA13_TIES = ("result", "ties_as_wrong", "paired", "pooled")
FA13_SHARE = ("result", "tie_decided", "pooled")


def _b2_ties_check(S: Store) -> None:
    """Free analysis 13 is B2's tie view: its reproduced B2 (d, interval, p and reading at both margins) is the Study 1b file's as
    deployed, its k is B2's k, its view is as deployed, and its paired differences cover B2's base puzzles."""
    if G(S, "fa13", "result", "test") != "B2" or G(S, "fa13", "result", "view") != "as_deployed":
        raise ValueError("free analysis 13 is not B2's as-deployed tie view")
    if G(S, "fa13", "result", "k") != b2_k(S).value:
        raise ValueError("free analysis 13's k is not B2's k")
    for fam in (PRIM, SEC):
        for key in ("d", "ci95", "p", "reading"):
            if G(S, "fa13", "result", "reproduced", fam[1], key) != G(S, "s1b", *fam, "views", "as_deployed", "tests", "B2", key):
                raise ValueError(f"free analysis 13's reproduced B2 {key} at {fam[1]} differs from the Study 1b file")
    if G(S, "fa13", *FA13_TIES, "n") != G(S, "s1b", *PRIM, "views", "as_deployed", "tests", "B2", "n"):
        raise ValueError("free analysis 13's paired differences do not cover B2's base puzzles")


def _b2_ties_wrong_row(S: Store, m5: float, m10: float) -> List[Cell]:
    """TAB-11's Panel 1's post hoc row (free analysis 13): B2's pooled d with every tie scored wrong, with its paired interval; no p and no
    reading. The base puzzles left out are the as-deployed view's (the tie view rescores that view's tries)."""
    _b2_ties_check(S)
    no_reading = DASH                                           # the row has no reading (Edith: Decision "—")
    return [L(STUDY1B_TESTS["B2"][0]), L("ties counted wrong (post hoc)"), integer(R(S, "fa13", *FA13_TIES, "n")),
            integer(R(S, "s1b", *PRIM, "views", "as_deployed", "bases_left_out", "B2")),
            pts(R(S, "fa13", *FA13_TIES, "d"), margin=m5),
            interval(*ci_refs(S, "fa13", join_key(*FA13_TIES, "ci95")), dp=2, signed=True, bounds=(0.0, m5, m10)),
            DASH, no_reading, DASH, no_reading]


def _b2_ties_note(S: Store) -> List[Cell]:
    """The ties-counted-wrong row's note: what it changes, its tier, and how often a tie decided B2's vote (all ties, as the Study 1
    tests table's tie-decided share, and three-against-three ties alone), from free analysis 13; the shares at 2 places and "votes",
    as the appendix prints them (Edith, §33 addendum)."""
    _b2_ties_check(S)
    return note("Panel 1's ties-counted-wrong row for Test B2 is post hoc (free analysis 13): the vote is scored as deployed, "
                "except that a vote whose top answers tie, the right one among them, scores nothing instead of an equal share; d and its "
                "paired bootstrap interval only, with no p and no reading, and B2's reading is unchanged. A tie that included the right "
                "answer decided",
                joined(P(R(S, "fa13", *FA13_SHARE, "tie_decided_share"), 2, prop=True), L("% of B2's"), sep=""),
                joined(integer(b2_k(S)), L("-sample votes (a mean over puzzles, each over all of its possible votes; "
                                           "three-against-three ties alone"), sep=""),
                joined(P(R(S, "fa13", *FA13_SHARE, "tie_decided_share_3_3"), 2, prop=True), L("%); such a tie decided at least one vote "
                                                                                                   "in"), sep=""),
                integer(R(S, "fa13", *FA13_SHARE, "bases_with_a_decided_tie_in_either_form")), "of the",
                integer(R(S, "fa13", *FA13_SHARE, "n_base")),
                "puzzles (in either shape). TAB-02 gives the tie-decided share for Tests 1\u20133.")


def _side_panel_B(S: Store) -> Cell:
    """Panel 1's bootstrap resamples, one printed count for both its sources (Karen's caption fact): the Study 1b tests' B (the
    as-deployed view at both margins) and free analysis 13's B; refuses unless all are equal."""
    refs = [R(S, "s1b", *fam, "views", "as_deployed", "B") for fam in (PRIM, SEC)] + [R(S, "fa13", "code", "B")]
    if len({r.value for r in refs}) != 1:
        raise ValueError(f"TAB-11: Panel 1's bootstrap counts differ ({[r.value for r in refs]})")
    one = integer(refs[0])
    return Cell(one.printed, raw=refs[0].value, refs=tuple(refs), formula="one value, equal in every source")


@output("TAB-11")
def tab_11(S: Store) -> Table:
    m5, m10 = margins(S)
    cols = ["Test", "Shape", "Challenger", "Challenger accuracy (%)", "Challenger 95% interval", "Opus-medium accuracy (%)",
            "Opus-medium 95% interval", "d (points)", "d 95% interval", "Format compliance, challenger (%)",
            "Format compliance, Opus-medium (%)"]
    rows: List[List[Cell]] = []
    marks = Marks()
    for t in TESTS_1B:
        name, ch_name, _ = STUDY1B_TESTS[t]
        n = int(G(S, "s1b", "completeness", t, "N"))
        key = "v" if t == "B2" else "h"
        t5 = [*PRIM, "views", "as_deployed", "tests", t]
        for s in shapes_of(n):
            pf = ["per_form", t, s]
            frt = [*FRT.split("."), "format_report"]
            # the per-shape rows are on the test's own puzzles (Edith, #39 review M2: these three checks came with the rows from the old
            # merged TAB-10; moving the rows to TAB-11 had dropped them): each block's n is the test's n, the d interval is the driver's
            # per_form bootstrap under its own name, and d is the challenger's accuracy minus Opus-medium's
            n_test = G(S, "s1b", *t5, "n")
            for side in (key, "o", "d"):
                if G(S, "s1b", *pf, side, "n_base") != n_test:
                    raise ValueError(f"{t} {s}: the per-shape {side!r} block's n is {G(S, 's1b', *pf, side, 'n_base')!r}, not the test's "
                                     f"{n_test!r}: the per-shape blocks are not on the test's puzzles")
            if G(S, "s1b", *pf, "d", "bootstrap_name") != f"1b:{t}:{n}:{s}:d":
                raise ValueError(f"{t} {s}: the per-shape d interval's bootstrap is {G(S, 's1b', *pf, 'd', 'bootstrap_name')!r}, not the "
                                 f"driver's per_form bootstrap {f'1b:{t}:{n}:{s}:d'!r}")
            _same(G(S, "s1b", *pf, "d", "mean"), G(S, "s1b", *pf, key, "mean") - G(S, "s1b", *pf, "o", "mean"),
                  f"{t} {s}: the per-shape d is not the challenger's accuracy minus Opus-medium's")
            for side in (key, "o"):
                tw = _per_form_twin(S, t, n, side, s)
                if side != "v" and G(S, "s1b", *pf, side, "bootstrap_name") == G(S, "s1b", *tw, "bootstrap_name"):
                    raise ValueError(f"{t} {s} {side}: the per-test and effort-sweep intervals share a bootstrap draw")
            rows.append([
                L(name), shp(s), L(ch_name),
                P(R(S, "s1b", *pf, key, "mean"), 2),
                CI(S, "s1b", [*pf, key, "ci95"], dp=2, marks=marks),
                P(R(S, "s1b", *pf, "o", "mean"), 2),
                CI(S, "s1b", [*pf, "o", "ci95"], dp=2, marks=marks),
                pts(R(S, "s1b", *pf, "d", "mean"), dp=2, margin=m5),
                interval(*ci_refs(S, "s1b", join_key(*pf, "d", "ci95")), dp=2, signed=True, bounds=(0.0, m5, m10)),
                P(R(S, "s1b", *frt, "hx", s, "format_compliance"), 2, prop=True),
                P(R(S, "s1b", *frt, "om", s, "format_compliance"), 2, prop=True)])
    vcols = ["Test", "View", "Puzzles used", "Puzzles left out", "d (points)", "d 95% interval", "5-point margin: p",
             "5-point margin: reading in this view", "10-point margin: p", "10-point margin: reading in this view"]
    vrows: List[List[Cell]] = []
    for t in TESTS_1B:
        for vk, vname in VIEWS:
            tv5 = [*PRIM, "views", vk, "tests", t]
            tv10 = [*SEC, "views", vk, "tests", t]
            vrows.append([
                L(STUDY1B_TESTS[t][0]), L(vname), integer(R(S, "s1b", *tv5, "n")), integer(R(S, "s1b", *PRIM, "views", vk, "bases_left_out", t)),
                pts(R(S, "s1b", *tv5, "d"), margin=m5),
                interval(*ci_refs(S, "s1b", join_key(*tv5, "ci95")), dp=2, signed=True, bounds=(0.0, m5, m10)),
                pb(S, tv5), _view_reading(S, tv5, R(S, "s1b", *PRIM, "margin")),
                pb(S, tv10), _view_reading(S, tv10, R(S, "s1b", *SEC, "margin"))])
        if t == "B2":
            vrows.append(_b2_ties_wrong_row(S, m5, m10))
    # polish §7.3: a column with one value in every row moves to a note
    FMT_OM11, LEFT_OUT = "Format compliance, Opus-medium (%)", "Puzzles left out"
    const11 = fold_constants(cols, rows, [FMT_OM11])
    vconst = fold_constants(vcols, vrows, [LEFT_OUT])
    notes = [
        note("Per-shape numbers are descriptive: the tests are the pooled ones in TAB-10. A chain is one puzzle whose answer "
             "carries all the steps; pieces are separate one-step puzzles."),
        note("The B2 challenger is the vote of k Haiku-max samples, k =", joined(integer(b2_k(S)), L(";"), sep=""),
             "B1 and B3 use one Haiku-max sample. Intervals are cluster bootstrap over puzzles (accuracies) and paired bootstrap (d)."),
        _b2_format_note(),
        separate_draws(S, "The per-test intervals here and TAB-12's intervals for the same setting and shape (for the B2 vote, FIG-03's)"),
    ]
    if marks.exact:
        notes.append(exact_note())
    _views_agree(S)
    notes.append(note("Panel 1 gives the pooled tests in the three views; its readings are per view, and a test holds only if it is no "
                      "worse in all three views (TAB-10). The three views agree to every printed digit because no refusal or truncation "
                      "touched either side of a test."))
    notes.append(_b2_ties_note(S))
    # one note for the constant columns of the table and of Panel 1 (Edith, proof 3, p. 88: two notes opened with the same sentence)
    notes.append(note("Columns that print one value in every row are left out: Opus-medium's format compliance is",
                      joined(prose_pct(const11[FMT_OM11]), L("for every test and shape,")),
                      "and Panel 1's number of puzzles left out is", joined(vconst[LEFT_OUT], L("in every row."), sep=" ")))
    t = Table([L(c) for c in cols], rows, notes, {
        "tier": [L("descriptive per-shape breakdown of the confirmatory tests (Holm within Study 1b only)"
                   + ("; the exact intervals are post hoc (free analysis 4)" if marks.exact else "")
                   + "; Panel 1's ties-counted-wrong row for Test B2 is post hoc (free analysis 13)")],
        "study": [L("Study 1b; Tests B1 and B2 at"), integer(R(S, "s1b", "completeness", "B1", "N")), L("steps, Test B3 at"),
                  integer(R(S, "s1b", "completeness", "B3", "N")), L("steps")],
        "set": test_sets(S),
        "n": [L("puzzles per shape:"), integer(R(S, "s1b", "per_form", "B1", "1x16", "d", "n_base")), L("(B1, B2);"),
              integer(R(S, "s1b", "per_form", "B3", "1x6", "d", "n_base")), L("(B3);"), *test_tries(S)],
        # the per-shape intervals are percentile bootstraps with the file's draws (the records behind it are guards); Panel 1's are BCa
        "interval": [with_evidence("cluster bootstrap over puzzles for accuracies; paired bootstrap for d,", _per_shape_d_evidence(S)),
                     integer(R(S, "s1b", "constants", "draws")),
                     L("draws" + ("; exact Clopper–Pearson over puzzles (free analysis 4, post hoc) where a bootstrap interval collapsed"
                                  if marks.exact else "") + "; Panel 1's d intervals are paired BCa bootstraps with"),
                     _side_panel_B(S), L("resamples (the tests' own, and free analysis 13's for the ties-counted-wrong row)")],
        "price": [L("not applicable (no cost column)")]})
    t.panels = [("Pooled tests in the three views", Table([L(c) for c in vcols], vrows))]
    # the supplement's layouts (batch g): sideways; the three views' panel at footnotesize, since the notes of the whole table print
    # under it, and its two long reading columns make it the taller one; rows grouped by test, each test's label printed once per group
    # (polish §7.7; the CSV and the cells file keep it in every row)
    t.layout = "landscape"
    t.groups = starts(rows, lambda r: r[0].printed)
    t.once = [0]
    view = t.panels[0][1]
    view.layout, view.font = "landscape", "footnotesize"
    view.groups = starts(vrows, lambda r: r[0].printed)
    view.once = [0]
    t.main_table = _tab11_paper(S, m5, m10)
    return print_rules(t)


SHAPE_PAPER = {"chain": "chains", "pieces": "pieces"}          # a paper table's Shape cell: the plural, as the text writes it (Edith, proof 4)


def shape_plural(sh: str) -> str:
    return SHAPE_PAPER[shape_word(sh)]


def _tab11_paper(S: Store, m5: float, m10: float) -> Table:
    """TAB-11.main, the paper's Table 10 (Vision's choice, 2026-10-19: the paper version has no panel, since the converter's paper variant
    prints one file; the three-views panel stays in the supplement's full TAB-11): the per-shape rows of Tests B1-B3 at TAB-10.main's
    precision (one decimal for percentages and points, from the same refs, with the same guards; the interval's ends never carry "+"),
    each test printed once (`once`) and the tests set apart (`groups`). Its columns are the full table's but for the challenger's name,
    which the first note gives (a text column would take the room of the numbers), with each accuracy and its 95% interval in one cell and
    Opus-medium's format compliance, which is the same in every row, in the note (polish §7.3). A collapsed interval takes the exact one
    (free analysis 4, post hoc); the row's Shape cell carries a dagger for it, which a note defines (a tag inside the cell, "(exact)",
    pushed its numbers out of line with the rest of the column: Edith, proof 4, §2.8; the full table's tag carries the puzzle count too);
    the caption facts name no analysis by its number. Two short notes, two lines together: the compliance of the vote (the single
    samples', final-check finding F7) with Opus-medium's, and the dagger. The tests themselves are TAB-10's; the caption's tier fact says
    so, and that this table is descriptive."""
    bnd = (0.0, m5, m10)
    frt = [*FRT.split("."), "format_report"]
    k = b2_k(S)
    marks = Marks()
    cols = ["Test", "Shape", "Challenger accuracy (%) [95% interval]", "Opus-medium accuracy (%) [95% interval]",
            "d (points) [95% interval]", "Format compliance, challenger (%)", "Format compliance, Opus-medium (%)"]
    rows: List[List[Cell]] = []
    groups: List[int] = []
    singles: List[str] = []
    exact_sides: List[Tuple[str, ...]] = []                # per row: whose interval is the exact one ("challenger", "Opus-medium")
    for t in TESTS_1B:
        n = int(G(S, "s1b", "completeness", t, "N"))
        key = "v" if t == "B2" else "h"
        if STUDY1B_TESTS[t][1] != ("Haiku-max vote" if t == "B2" else "One Haiku-max sample"):
            raise ValueError(f"{t}: the names table's challenger is {STUDY1B_TESTS[t][1]!r}, not the one the note names")
        if t != "B2":
            singles.append(t)
        if rows:
            groups.append(len(rows))
        for sh in shapes_of(n):
            pf = ["per_form", t, sh]
            before = len(marks.exact)
            chal = acc_ci(S, "s1b", [*pf, key], marks=marks, short="bare", tie=True)     # (interval_up is Table 10's ruling only, A.23)
            mid = len(marks.exact)
            opus = acc_ci(S, "s1b", [*pf, "o"], marks=marks, short="bare", tie=True)
            sides = tuple(w for w, hit in (("challenger", mid > before), ("Opus-medium", len(marks.exact) > mid)) if hit)
            exact_sides.append(sides)
            rows.append([
                L(t), L(shape_plural(sh) + ("\u2020" if sides else "")), chal, opus,
                joined(num(R(S, "s1b", *pf, "d", "mean"), dp=1, signed=True, bounds=bnd),
                       interval(*ci_refs(S, "s1b", join_key(*pf, "d", "ci95")), dp=1, signed=False, bounds=bnd), sep=NBSP),
                P(R(S, "s1b", *frt, "hx", sh, "format_compliance"), 1, prop=True),
                P(R(S, "s1b", *frt, "om", sh, "format_compliance"), 1, prop=True)])
    om = "Format compliance, Opus-medium (%)"
    const = fold_constants(cols, rows, [om])
    notes = [note("Challenger: one Haiku-max sample (" + ", ".join(singles) + ") or the vote of", integer(k),
                  "(B2); a vote's format compliance is its samples'; Opus-medium's is", joined(const[om], L("% throughout."), sep=""))]
    if marks.exact:
        marked = sorted({x for x in exact_sides if x})
        if len(marked) != 1 or len(marked[0]) != 1:
            raise ValueError(f"TAB-11.main's dagger note names one side's interval; the exact intervals are on {marked}")
        side = marked[0][0]
        notes.append(note("\u2020\u00a0" + ("Opus-medium's" if side == "Opus-medium" else "The challenger's") + " interval: exact "
                          "Clopper\u2013Pearson (post hoc), where the bootstrap one collapsed."))
    _views_agree(S)
    caption = {
        "tier": [L("descriptive per-shape breakdown of the confirmatory tests in TAB-10 (Holm within Study 1b only)"
                   + ("; the exact intervals are post hoc" if marks.exact else ""))],
        "study": [L("Study 1b; Tests B1 and B2 at"), integer(R(S, "s1b", "completeness", "B1", "N")), L("steps, Test B3 at"),
                  integer(R(S, "s1b", "completeness", "B3", "N")), L("steps")],
        "set": test_sets(S),
        "n": [L("puzzles per shape:"), integer(R(S, "s1b", "per_form", "B1", "1x16", "d", "n_base")), L("(B1, B2);"),
              integer(R(S, "s1b", "per_form", "B3", "1x6", "d", "n_base")), L("(B3);"), *test_tries(S)],
        "interval": [with_evidence("cluster bootstrap over puzzles for accuracies; paired bootstrap for d,", _per_shape_d_evidence(S)),
                     integer(R(S, "s1b", "constants", "draws")),
                     L("draws" + ("; exact Clopper–Pearson over puzzles (post hoc) where a bootstrap interval collapsed" if marks.exact else ""))],
        "price": [L("not applicable (no cost column)")]}
    return paper_table(cols, rows, notes, caption, layout="float", text_cols=(0, 1), groups=groups, once=[0])


# ---------------------------------------------------------------- TAB-12


def _limit_index(S: Store, tag: str, n: int) -> Optional[int]:
    for i, lim in enumerate(S.get("s1b", "plan_as_run.limits")):
        if lim["tag"] == tag and lim["steps"] == n:
            return i
    return None


def _cpc_cell(S: Store, segs: Sequence[Any]) -> Cell:
    r = R(S, "s1b", *segs)
    if isinstance(r.value, (int, float)):
        return usd(r)
    return quoted_text(r)


# The Study 1b file's one label for its refusal counts and its format flag (`descriptive.format_refusals_truncations_missing.label`); the
# flag note prints the flag's rule as cut from it (group 1), in the file's words, and checks the flags against its threshold (group 2).
FLAG_RULE = r"^item 16: count / designed calls with .+; item 17: (non-compliance above (\d+(?:\.\d+)?)% of answered tries)$"


def _count(v: Any, what: str) -> int:
    """A stamped count: a number, or a block with a `count` (the Study 1b file's refusal categories may be either)."""
    c = v["count"] if isinstance(v, dict) else v
    if isinstance(c, bool) or not isinstance(c, int):
        raise ValueError(f"{what}: {v!r} is not a count")
    return c


def _answered_leaves_out(S: Store, tag: str, s: str) -> None:
    """The check behind the flag note's "refusals, truncations and missing calls are counted apart ... and do not enter the flag": the
    arm and shape's answered tries (the flag's denominator) are its designed calls less the refusals, truncations and missing calls that
    the Study 1b file counts apart (its item 16 counts, for the set at the shape's length), the file counts no other failure there, and
    the format report's own count of truncated tries is the same."""
    n = max(int(x) for x in s.split("x"))                     # the length of a shape '1xN' (chain) or 'Nx1' (pieces)
    if s not in shapes_of(n):
        raise ValueError(f"{tag} {s}: not a Study 1b shape")
    r16 =G(S, "s1b", *FRT.split("."), "item_16_rates", s1b_set_at(S, n), f"{tag} {s}")
    rep = G(S, "s1b", *FRT.split("."), "format_report", tag, s)
    if r16["failures_by_kind"]:
        raise ValueError(f"{tag} {s}: item 16 counts other failures {r16['failures_by_kind']!r}; the flag note does not name them")
    refused = sum(_count(v, f"{tag} {s} refusals") for v in r16["refusals_by_category"].values())
    truncated, missing = _count(r16["truncations"], f"{tag} {s} truncations"), _count(r16["missing"], f"{tag} {s} missing")
    if rep["answered"] != r16["designed_calls"] - refused - truncated - missing:
        raise ValueError(f"{tag} {s}: answered tries are not the designed calls less the refusals, truncations and missing calls")
    if rep["status_counts"].get("truncated", 0) != truncated:
        raise ValueError(f"{tag} {s}: the format report's truncated tries differ from item 16's count")


# D-176's ruled line (the decision register, ruled 2026-10-20, "yes add Karen's line"): the effort sweep's two format-compliance cells
# that sit exactly on the flag's threshold and do not fire. Printed word for word; "Two", "5.0" and the threshold's "5" are read from
# the stamped flags and the stamped rule, and the build stops unless the printed line is this one.
D176_LINE = "Two cells sit at exactly 5.0% and are not flagged, as the rule says 'more than 5%'."


def _unflagged_boundary(S: Store) -> List[Cell]:
    """D-176's line for TAB-12: every arm and shape whose non-compliance is exactly the stamped rule's threshold (exact decimal
    arithmetic: one minus 0.95 is 0.05) is counted; the build stops unless there are two and neither fires (the rule is "above" the
    threshold, the locked check's whole-number test (answered - format ok) x 100 > 5 x answered)."""
    lab = R(S, "s1b", *FRT.split("."), "label")
    five = extract(lab, FLAG_RULE, group=2)
    limit = dec(five.raw) / dec(100)
    hits: List[Ref] = []
    refs: List[Ref] = []
    for key, f in G(S, "s1b", *FRT.split("."), "item_17_flags").items():
        tag, sh = key.split(" ")
        fc = R(S, "s1b", *FRT.split("."), "format_report", tag, sh, "format_compliance")
        if dec(1) - dec(fc.value) != limit:
            continue
        fires = R(S, "s1b", *FRT.split("."), "item_17_flags", key, "fires")
        if fires.value is not False:
            raise ValueError(f"{key} sits exactly on the format flag's threshold and fires; D-176's line says not flagged")
        hits.append(fc)
        refs += [fc, fires]
    if len(hits) != 2:
        raise ValueError(f"{len(hits)} effort-sweep cells sit exactly on the format flag's threshold; D-176's line says two")
    _same(hits[0].value, hits[1].value, "the two cells on the threshold share one compliance")
    two = Cell("Two", raw=len(hits), refs=tuple(refs),
               formula="the number of the effort sweep's arm and shape cells whose non-compliance is exactly the format flag's threshold "
                       "and whose stamped flag does not fire (printed as a word)")
    at = num_d(derive("non-compliance of the cells on the threshold, 100 x (1 - format compliance)", lambda c: 100.0 * (1.0 - c), hits[0]),
               dp=1)
    cells = [two, L("cells sit at exactly"), joined(at, L("%"), sep=""), L("and are not flagged, as the rule says"),
             joined(L("'more than"), joined(five, L("%'."), sep=""))]
    printed = " ".join(c.printed for c in cells if c.printed)
    if printed != D176_LINE:
        raise ValueError(f"TAB-12's unflagged-boundary line is not D-176's ruled line: {printed!r}")
    return cells


def _flag_rule(S: Store) -> Cell:
    """The format flag's rule, cut from the stamped label (a recorded pattern), and the check that every stamped flag follows it: an arm
    and shape's non-compliance is one minus its format compliance (format ok / answered), its answered tries leave out the refusals,
    truncations and missing calls counted apart (`_answered_leaves_out`), and the flag fires exactly when it is above the label's
    threshold."""
    lab = R(S, "s1b", *FRT.split("."), "label")
    rule = extract(lab, FLAG_RULE)
    threshold = float(extract(lab, FLAG_RULE, group=2).raw) / 100.0
    flags = G(S, "s1b", *FRT.split("."), "item_17_flags")
    for key, f in flags.items():
        tag, s = key.split(" ")
        rep = G(S, "s1b", *FRT.split("."), "format_report", tag, s)
        if f["answered"] != rep["answered"] or f["format_ok"] != rep["format_ok"]:
            raise ValueError(f"format flag {key}: its counts differ from the format report's")
        _answered_leaves_out(S, tag, s)
        _same(f["non_compliance"], 1.0 - rep["format_ok"] / rep["answered"], f"format flag {key}: non-compliance, 1 - format ok / answered")
        if f["fires"] != (f["non_compliance"] > threshold):
            raise ValueError(f"format flag {key}: fires is not 'non-compliance above the label's threshold'")
    if set(flags) != {f"{tag} {s}" for tag, by in G(S, "s1b", *FRT.split("."), "format_report").items() for s in by}:
        raise ValueError("the format flags and the format report cover different arms and shapes")
    return rule


def _flag_cell(S: Store, tag: str, n: int) -> Cell:
    """TAB-12.main's "Flagged shape" cell: the shape (or "both") on which the pre-registered format check flags the setting (the words
    the figures' captions use: "flagged"), empty where neither shape is flagged; from the two stamped flags (item 17), kept as its refs."""
    ch, pc = shapes_of(n)
    fl = [R(S, "s1b", *FRT.split("."), "item_17_flags", f"{tag} {s}", "fires") for s in (ch, pc)]
    if any(r.value not in (True, False) for r in fl):
        raise ValueError(f"{tag} at {n} steps: a format flag is not true or false: {[r.value for r in fl]}")
    words = [w for w, r in zip(("chains", "pieces"), fl) if r.value]
    return Cell("both" if len(words) == 2 else (words[0] if words else ""), raw=[r.value for r in fl], refs=tuple(fl),
                formula="the shapes whose format flag fires (chains, pieces; both when both do)")


@output("TAB-12")
@main_text
def tab_12(S: Store) -> Table:
    # one structure for the three accuracy groups: each accuracy and its interval in two columns, so that the estimates line up on their
    # decimal points (Edith, proof 4, p. 106: the pooled estimate and interval stood apart, chain and pieces in one cell)
    # the three interval headers are tied whole, so that each sets on one line (Edith, proof 4, p. 106: "Pooled 95% / interval" took two
    # lines, the other two one); the writer gives a column at least the width of its longest unbreakable piece
    pooled_ci, chain_ci, pieces_ci = (f"{g}\u00a095%\u00a0interval (%)" for g in ("Pooled", "Chain", "Pieces"))
    cols = ["Setting", "Steps", "Puzzles", "Samples per puzzle", "Pooled accuracy (%)", pooled_ci, "Interval type",
            "Chain accuracy (%)", chain_ci, "Pieces accuracy (%)", pieces_ci,
            "Format compliance, chain (%)", "Format flag, chain", "Format compliance, pieces (%)", "Format flag, pieces",
            "List cost per answer ($)", "List cost per correct answer ($)", "Token limit (max_tokens)", "Trial round: largest output (tokens)"]
    arms = sorted(S.keys("s1b", "descriptive.arms"), key=arm_order)
    rows: List[List[Cell]] = []
    paper: List[List[Cell]] = []                       # the paper's version (D-161): the same refs, pooled only
    paper_models: List[str] = []                       # each paper row's model (the paper's rows are grouped by it)
    marks = Marks()
    paper_marks = Marks()
    for arm in arms:
        tag, _ = arm.split("@")
        name, model, effort = STUDY1B_TAGS[tag]
        a = ["descriptive", "arms", arm]
        if G(S, "s1b", *a, "effort") != effort or not str(G(S, "s1b", *a, "model")).startswith(f"claude-{model}"):
            raise ValueError(f"{arm}: stamped model or effort differs from the names table")
        n = int(G(S, "s1b", *a, "N"))
        ch, pc = shapes_of(n)
        for s in (ch, pc):
            if G(S, "s1b", *a, s, "interval") != G(S, "s1b", *a, "pooled", "interval"):
                raise ValueError(f"{arm} {s}: interval type differs from the pooled one")
        # the notes and caption say Clopper–Pearson for the arms with one try per item and cluster bootstrap for the others
        if (G(S, "s1b", *a, "pooled", "interval") == "clopper-pearson") != (G(S, "s1b", *a, "tries_per_item") == 1):
            raise ValueError(f"{arm}: interval type does not follow its tries per item")
        if G(S, "s1b", *a, "pooled", "interval") not in ("clopper-pearson", "cluster bootstrap"):
            raise ValueError(f"{arm}: interval type {G(S, 's1b', *a, 'pooled', 'interval')!r} is not one the notes name")
        if tag not in G(S, "s1b", "inputs", "sets", s1b_set_at(S, n), "arms_sent"):
            raise ValueError(f"{arm}: not sent on Study 1b's set at its length")
        li = _limit_index(S, tag, n)
        lim_cells = ([integer(R(S, "s1b", "plan_as_run", "limits", li, "max_tokens")),
                      integer(R(S, "s1b", "plan_as_run", "limits", li, "wave0_output_tokens_max"))] if li is not None else [EMPTY, EMPTY])
        frt = [*FRT.split(".")]
        rows.append([
            setting_label(name), integer(R(S, "s1b", *a, "N")), integer(R(S, "s1b", *a, "pooled", "n_base")), integer(R(S, "s1b", *a, "tries_per_item")),
            P(R(S, "s1b", *a, "pooled", "mean"), 2), CI(S, "s1b", [*a, "pooled", "ci95"], dp=2, marks=marks),
            text_of(R(S, "s1b", *a, "pooled", "interval"), INTERVAL_TYPES),
            P(R(S, "s1b", *a, ch, "mean"), 2), CI(S, "s1b", [*a, ch, "ci95"], dp=2, marks=marks),
            P(R(S, "s1b", *a, pc, "mean"), 2), CI(S, "s1b", [*a, pc, "ci95"], dp=2, marks=marks),
            P(R(S, "s1b", *frt, "format_report", tag, ch, "format_compliance"), 2, prop=True),
            text_of(R(S, "s1b", *frt, "item_17_flags", f"{tag} {ch}", "fires"), YES_NO),
            P(R(S, "s1b", *frt, "format_report", tag, pc, "format_compliance"), 2, prop=True),
            text_of(R(S, "s1b", *frt, "item_17_flags", f"{tag} {pc}", "fires"), YES_NO),
            usd(R(S, "s1b", *a, "pooled", "cost_per_answer")), _cpc_cell(S, [*a, "pooled", "cpc", "cpc"]), *lim_cells])
        # the accuracy and its interval in two columns, so that the estimates line up on their decimal points (Edith, proof 4, §2.8: in one
        # cell the estimates stood 4.6 pt out of line, "0.5" against "100.0")
        paper.append([setting_label(name), integer(R(S, "s1b", *a, "N")), integer(R(S, "s1b", *a, "tries_per_item")),
                      P(R(S, "s1b", *a, "pooled", "mean"), 1), CI(S, "s1b", [*a, "pooled", "ci95"], marks=paper_marks, short=True, up=True),
                      fmt_pair(S, tag, n), _flag_cell(S, tag, n), usd(R(S, "s1b", *a, "pooled", "cost_per_answer"))])
        paper_models.append(model)
    if paper_marks.zero:
        raise ValueError("a pooled interval in TAB-12's paper version collapsed and has no exact replacement")
    paper_groups = [i for i in range(1, len(paper_models)) if paper_models[i] != paper_models[i - 1]]      # Haiku, Sonnet, Opus
    if len(G(S, "s1b", "inputs", "sets")) != len({int(G(S, "s1b", "descriptive", "arms", a, "N")) for a in arms}):
        raise ValueError("Study 1b's sets are not one per length")
    flag_ev = spec1b_line(S, r"^\s*- \*\*(Format compliance, refusals, truncations and missing items)\*\* for every arm",
                          "format compliance and its flag are pre-registered for every arm", section=SPEC1B_S6)
    flag_note = note(with_evidence("Format flag: yes means the pre-registered format-compliance flag fires for that setting and shape. Its "
                                   "rule, in the file's words:", flag_ev),
                     joined(L("\""), _flag_rule(S), L("\";"), sep=""),
                     "non-compliance is the share of answered samples (the file's \"tries\") whose format was not ok, one minus the format "
                     "compliance (checked). "
                     "Refusals, truncations and missing calls are counted apart in the Study 1b file (not in this table) and do not enter "
                     "the flag: the answered samples leave them out (checked).")
    shared = [
        note("Pooled accuracy is each puzzle's mean over its two shapes. Intervals are cluster bootstrap over puzzles for settings "
             "with several samples and Clopper–Pearson for one-sample settings (the interval type the file records for each setting, "
             "in the Interval type column that opens the table's second part); per-shape intervals are of the same type."),
        separate_draws(S, "Haiku-max's and Opus-medium's intervals here at the lengths of Tests B1\u2013B3 and those in TAB-11 "
                          "(Tests B1\u2013B3 by shape)"),
    ]
    if marks.exact:
        shared.append(exact_note())
    limit_note = note("Token limit and the trial round's largest output are recorded only for the settings whose limit the trial round set; "
                      "the Study 1b file records no limit for the other settings, so those cells are empty.")
    for tag, by_shape in G(S, "s1b", *FRT.split("."), "format_report").items():     # the definition the next note gives (a check)
        for s, f in by_shape.items():
            _same(f["format_compliance"], f["format_ok"] / f["answered"], f"format compliance {tag} {s}: format ok / answered")
    fmt_note = note("Format compliance is the share of answered samples whose format was ok, per shape.")
    twins = _twin_notes(S, arms)
    cpc_ev = spec1b_line(S, r"^\s*- \*\*(Cost per correct answer)\*\* for every arm", "cost per correct answer is pre-registered for "
                         "every arm", section=SPEC1B_S6)
    cpc_note = note(with_evidence("Cost per correct answer is list-price dollars per correct answer, as pre-registered; no setting in "
                                  "this table is a vote.", cpc_ev))
    # no version names a pre-registration item (TAB-12 is a main-text table; Edith's Q22)
    notes = [flag_note, note(*_unflagged_boundary(S))] + shared + [limit_note, fmt_note, cpc_note] + twins
    at12 = [a for a in arms if int(G(S, "s1b", "descriptive", "arms", a, "N")) == int(G(S, "s1b", "descriptive", "arms", "hx@12", "N"))]
    if [a.split("@")[0] for a in at12] != ["hx", "om"]:
        raise ValueError(f"the settings at the middle length are {at12}, not Haiku-max and Opus-medium")
    caption = {
        "tier": [L("pre-specified descriptive (no tests)" + ("; the exact intervals are post hoc (free analysis 4)" if marks.exact else ""))],
        "study": _sweep_scope(S, arms),
        "set": [L("Study 1b's own puzzle sets, one per length (each setting ran on the set of its length): the set at"),
                integer(R(S, "s1b", "completeness", "B3", "N")), L("steps is Test B3's, the set at"),
                integer(R(S, "s1b", "completeness", "B1", "N")), L("steps that of Tests B1 and B2, and there is one set at"),
                integer(R(S, "s1b", "descriptive", "arms", "hx@12", "N")), L("steps")],
        "n": [L("puzzles:"), integer(R(S, "s1b", "descriptive", "arms", "hh@6", "pooled", "n_base")), L("at"),
              integer(R(S, "s1b", "descriptive", "arms", "hh@6", "N")), L("steps;"),
              integer(R(S, "s1b", "descriptive", "arms", "hx@12", "pooled", "n_base")), L("at"),
              integer(R(S, "s1b", "descriptive", "arms", "hx@12", "N")), L("steps;"),
              integer(R(S, "s1b", "descriptive", "arms", "hh@16", "pooled", "n_base")), L("at"),
              integer(R(S, "s1b", "descriptive", "arms", "hh@16", "N")), L("steps; samples per puzzle and shape in the Samples per "
                                                                         "puzzle column")],
        "interval": [L("cluster bootstrap (several samples) or Clopper–Pearson (one sample), as recorded per setting"
                       + ("; exact Clopper–Pearson over puzzles (free analysis 4, post hoc) where a bootstrap interval collapsed"
                          if marks.exact else ""))],
        "price": [with_evidence("list price in US dollars (pre-registered)", spec1b_line(
            S, r"^\s*- (The list cost per answer is beside each point)\.$", "the effort figure's points carry the list cost per answer"))]}
    t = Table([L(c) for c in cols], rows, notes, caption)
    # the paper's version (Vision's plan §3; D-161; Edith's proof-2 rows for p. 35): setting, steps, samples, pooled accuracy with its
    # interval, format compliance (chains / pieces) with the shape the format check flags, and list cost per answer, the rows grouped by
    # model and each setting printed once (`once`); chain and pieces accuracy, the limits and cost per correct answer stay in the
    # supplement's full table. Every cell here is read from the Study 1b file (checked): the caption's study fact names the study (TAB-16.main's
    # 6-step rows are Study 1's, with different costs), and with the notes cut to two lines (polish §7.5) it no longer repeats it
    if {r.source for row in paper for c in row for r in c.refs} != {"s1b"} or not caption["study"][0].printed.startswith(
            "Study 1b effort sweep"):
        raise ValueError("TAB-12's paper rows are not all read from Study 1b's effort sweep; the caption's study fact names the study")
    lab = R(S, "s1b", *FRT.split("."), "label")
    _flag_rule(S)                                                  # every stamped flag follows the label's rule (checks)
    threshold = joined(extract(lab, FLAG_RULE, group=2), L("%"), sep="")
    pnotes = [note("Flagged: over", threshold, "of answered samples non-compliant.")]
    twins = _twins(S, arms)
    if len(twins) > 1:
        raise ValueError(f"the paper version's twin note names one pair; there are {len(twins)}")
    # rows that look copied: one-sample settings with equal pooled accuracy share one interval (checked), and the twin pair matches on
    # each shape too (the full table shows the shapes; the paper version does not)
    same_ci = "Equal accuracies of one-sample settings at one length give equal Clopper–Pearson intervals"
    if not _equal_one_sample_intervals(S, arms):
        same_ci = ""
    for a, b in twins:
        pnotes.append(note((same_ci + "; " if same_ci else "") + tag_name(a.split("@")[0]), "and", tag_name(b.split("@")[0]),
                           joined(joined(L("("), integer(R(S, "s1b", "descriptive", "arms", a, "N")), sep=""),
                                  L("steps) match in accuracy on each shape," if same_ci else "steps) have the same accuracies and intervals "
                                    "on both shapes and pooled")), "not in list cost." if same_ci else "but differ in list cost."))
    if same_ci and not twins:
        pnotes.append(note(same_ci + "."))
    if paper_marks.exact:
        pnotes.append(note("(exact): exact Clopper–Pearson interval (post hoc) where the bootstrap interval collapsed."))
    # the paper version's own caption facts: the full table's, for what it shows and in the paper's words (D-161: setting, puzzle,
    # sample; no analysis is named by its number); the notes' definitions the two lines have no room for are here: how accuracy is
    # pooled, which intervals are which (the study and interval facts), and the pre-registered format check behind the flags
    pcap = {
        "tier": [L("pre-specified descriptive (no tests)" + ("; the exact intervals are post hoc" if paper_marks.exact else ""))],
        "study": caption["study"],
        "set": [L("Study 1b's own puzzle sets, one per length (each setting ran on the set of its length): the set at"),
                *caption["set"][1:]],
        "n": [L("puzzles:"), *caption["n"][1:-1], L("steps, each in both shapes; accuracy is each puzzle's mean over its two shapes; "
                                                     "samples per puzzle and shape in the Samples per puzzle column")],
        "interval": [L("cluster bootstrap over puzzles (several samples) or Clopper–Pearson (one sample), as recorded per setting"
                       + ("; exact Clopper–Pearson over puzzles (post hoc) where a bootstrap interval collapsed"
                          if paper_marks.exact else ""))],
        "format": [L("format compliance: the share of answered samples in the required answer format, chains / pieces; the "
                     "pre-registered format check flags a shape whose non-compliance is above"), threshold,
                   L("of its answered samples (the flagged shape column; blank where neither shape is flagged)")],
        "price": caption["price"]}
    if caption["n"][-1].printed != "steps; samples per puzzle and shape in the Samples per puzzle column" or not caption["set"][0].printed.startswith(
            "Study 1b's own puzzle sets, one per length (each setting ran"):
        raise ValueError("TAB-12's caption facts changed; the paper version's words no longer follow them")
    t.main_table = paper_table(["Setting", "Steps", "Samples per puzzle", "Accuracy (%)", "95% interval (%)",
                                "Format compliance (%), chains / pieces", "Flagged shape", "List cost per answer ($)"],
                               paper, pnotes, pcap, text_cols=(0, 6), groups=paper_groups, once=[0], font="footnotesize")
    # the supplement's layout (batch g): 17 columns split in two, sideways, at footnotesize (the notes print under the second part, and
    # its 25 rows leave no room for them at \small); a setting runs at several lengths, so Setting and Steps repeat. The interval type
    # belongs beside the intervals, but part 1 has no room for it (measured: with it the part is 7.5 in tall and overfull at 9.0 in wide):
    # it opens part 2, and the note on the intervals points to its column
    split(t, True, [["Samples per puzzle", "Puzzles", "Pooled accuracy (%)", pooled_ci, "Chain accuracy (%)",
                     chain_ci, "Pieces accuracy (%)", pieces_ci],
                    ["Interval type", "Format compliance, chain (%)", "Format flag, chain", "Format compliance, pieces (%)",
                     "Format flag, pieces", "List cost per answer ($)", "List cost per correct answer ($)", "Token limit (max_tokens)",
                     "Trial round: largest output (tokens)"]], key=("Setting", "Steps"))
    t.font = "footnotesize"
    t.groups = starts(rows, family)                                  # Haiku, Sonnet, Opus (polish §7.7)
    return print_rules(t)


def _equal_one_sample_intervals(S: Store, arms: List[str]) -> bool:
    """The check behind TAB-12's paper note that equal accuracies of one-sample settings at one length give equal intervals: every two
    one-sample settings at one length with the same pooled accuracy have the same pooled interval, and it is a Clopper–Pearson one.
    True when at least one such pair exists (the note is needed only then)."""
    one = [a for a in arms if G(S, "s1b", "descriptive", "arms", a, "tries_per_item") == 1]
    found = False
    for i, a in enumerate(one):
        for b in one[i + 1:]:
            pa, pb_ = (["descriptive", "arms", x, "pooled"] for x in (a, b))
            if G(S, "s1b", "descriptive", "arms", a, "N") != G(S, "s1b", "descriptive", "arms", b, "N") or \
                    G(S, "s1b", *pa, "mean") != G(S, "s1b", *pb_, "mean"):
                continue
            if G(S, "s1b", *pa, "ci95") != G(S, "s1b", *pb_, "ci95") or G(S, "s1b", *pa, "n_base") != G(S, "s1b", *pb_, "n_base") or \
                    {G(S, "s1b", *pa, "interval"), G(S, "s1b", *pb_, "interval")} != {"clopper-pearson"}:
                raise ValueError(f"{a} and {b}: same accuracy, but not one Clopper–Pearson interval over the same puzzles")
            found = True
    return found


def _sweep_scope(S: Store, arms: List[str]) -> List[Cell]:
    """TAB-12's caption 'study' fact: every model at every effort level, and Haiku, thinking off, at the short length; Haiku at every
    effort level, Haiku, thinking off, and Opus-medium at the long one; Haiku-max and Opus-medium at the middle one (checked against
    the stamped arms)."""
    by_n: Dict[int, List[str]] = {}
    for a in arms:
        by_n.setdefault(int(G(S, "s1b", "descriptive", "arms", a, "N")), []).append(a.split("@")[0])
    short, mid, long_ = (int(G(S, "s1b", "descriptive", "arms", a, "N")) for a in ("hh@6", "hx@12", "hh@16"))
    if sorted(by_n) != [short, mid, long_]:
        raise ValueError(f"Study 1b's arms run at {sorted(by_n)} steps, not three lengths")
    levels = [e for e in EFFORT_ORDER if e != "off"]
    held = {n: sorted(STUDY1B_TAGS[t][1:] for t in tags) for n, tags in by_n.items()}
    if held[short] != sorted([(m, e) for m in MODEL_ORDER for e in levels] + [("haiku", "off")]):
        raise ValueError("the short length does not hold every model at every effort level and Haiku with thinking off")
    if held[long_] != sorted([("haiku", e) for e in EFFORT_ORDER] + [("opus", "medium")]):
        raise ValueError("the long length does not hold exactly Haiku at every effort level and with thinking off, and Opus-medium")
    if sorted(by_n[mid]) != ["hx", "om"]:
        raise ValueError("the middle length does not hold exactly Haiku-max and Opus-medium")
    # one name per setting (Edith, proof 4, §3.5): "Haiku, thinking off", never "Haiku with thinking off"; a list with it separates its
    # items with semicolons
    return [L("Study 1b effort sweep. At"), integer(R(S, "s1b", "descriptive", "arms", "hh@6", "N")),
            L("steps: every model at every effort level, and Haiku, thinking off. At"),
            integer(R(S, "s1b", "descriptive", "arms", "hh@16", "N")),
            L("steps: Haiku at every effort level; Haiku, thinking off; and Opus-medium. At"),
            integer(R(S, "s1b", "descriptive", "arms", "hx@12", "N")), L("steps: Haiku-max and Opus-medium")]


def _twins(S: Store, arms: List[str]) -> List[Tuple[str, str]]:
    """Two efforts of one model at one length whose stamped accuracies and intervals are the same on both shapes and pooled (it reads
    as a copying error otherwise); refuses a pair whose list costs per answer are the same too (then it may be one)."""
    out: List[Tuple[str, str]] = []
    for i, a in enumerate(arms):
        for b in arms[i + 1:]:
            na, nb = int(G(S, "s1b", "descriptive", "arms", a, "N")), int(G(S, "s1b", "descriptive", "arms", b, "N"))
            blocks = [*shapes_of(na), "pooled"]
            if STUDY1B_TAGS[a.split("@")[0]][1] != STUDY1B_TAGS[b.split("@")[0]][1]:
                continue                                 # only two efforts of one model read as a copying error
            if na != nb or any(G(S, "s1b", "descriptive", "arms", a, s, k) != G(S, "s1b", "descriptive", "arms", b, s, k)
                               for s in blocks for k in ("mean", "ci95")):
                continue
            if G(S, "s1b", "descriptive", "arms", a, "pooled", "cost_per_answer") == G(S, "s1b", "descriptive", "arms", b, "pooled",
                                                                                       "cost_per_answer"):
                raise ValueError(f"{a} and {b}: same accuracies and the same cost")
            out.append((a, b))
    return out


def _twin_notes(S: Store, arms: List[str]) -> List[List[Cell]]:
    """A note for each pair of `_twins`: their list costs per answer and chain format compliance, read from the file, show two separate
    settings."""
    out: List[List[Cell]] = []
    frt = [*FRT.split("."), "format_report"]
    for a, b in _twins(S, arms):
        na = int(G(S, "s1b", "descriptive", "arms", a, "N"))
        ca, cb = (R(S, "s1b", "descriptive", "arms", x, "pooled", "cost_per_answer") for x in (a, b))
        ch = shapes_of(na)[0]
        out.append(note(tag_name(a.split("@")[0]), "and", tag_name(b.split("@")[0]), "at", integer(R(S, "s1b", "descriptive", "arms", a, "N")),
                        "steps have the same accuracies and intervals on both shapes and pooled. They are separate settings: list cost "
                        "per answer", joined(L("$"), usd(ca), sep=""), "against", joined(L("$"), usd(cb), L(";"), sep=""),
                        "chain format compliance",
                        joined(P(R(S, "s1b", *frt, a.split("@")[0], ch, "format_compliance"), 2, prop=True), L("%"), sep=""), "against",
                        joined(P(R(S, "s1b", *frt, b.split("@")[0], ch, "format_compliance"), 2, prop=True), L("%."), sep="")))
    return out


# ---------------------------------------------------------------- TAB-13

CURVE_SRC = (("curve_d90", "Deviation 2 rule"), ("curve", "original rule"))
CURVE_MODELS = ("hm", "om", "sm")
CURVE_SHAPES = (("1xn", "chain"), ("nx1", "pieces"), ("pooled", "pooled"))


def _curve_lengths(S: Store) -> List[str]:
    a = sorted(S.keys("curve_d90", "models.hm.by_n"), key=int)
    for src, _ in CURVE_SRC:
        for m in CURVE_MODELS:
            if sorted(S.keys(src, join_key("models", m, "by_n")), key=int) != a:
                raise ValueError("the two curve files hold different lengths")
    return a


def _steps(n: str, parent: str = "models.hm.by_n") -> Cell:
    """The length, as the bare number under the "Steps" header (the header carries the unit, polish §7.4; TAB-12 and TAB-16 print it so).
    The sweep's files stamp it only as the NAME of a key (`models.<m>.by_n.<n>`; the same lengths for every model), so the cell
    records that key as its provenance, with the formula 'the key name (steps)'."""
    r = Ref(int(n), "curve_d90", join_key(*parse_key(parent), n))
    return Cell(n, raw=int(n), refs=(r,), formula="the key name (steps)")


# Pilot 1 marker keys -> the words printed for them (the stamped labels carry run, lock and preset ids, which stay in the methods
# appendix; the plain words are the settlement's, plan-settlement-g5 C-079, as FIG-05 uses them); each stamped label must name these
# presets (checked) and the marker must cover that many sets.
PILOT1_MARKERS = {"l14_only": ("Pilot 1, the one preset used\u00a0later", "presets l14, before", 1),
                  "l14_to_l16": ("Pilot 1, three rule-set presets", "presets l14, l15, l16, before", 3)}
VOTE_WORDS = {"not cost-matched": "not cost-matched"}   # the stamped vote label, printed as stamped (D-161: "cost-matched" replaces "equal money")


@output("TAB-13")
def tab_13(S: Store) -> Table:
    lengths = _curve_lengths(S)
    marks = Marks()
    n_ref = R(S, "curve_d90", "models", "hm", "by_n", lengths[0], "n_base")
    for src, _ in CURVE_SRC:
        for m in CURVE_MODELS:
            for n in lengths:
                if G(S, src, "models", m, "by_n", n, "n_base") != n_ref.value:
                    raise ValueError(f"{src} {m} {n}: base puzzles differ between lengths or models")
                if G(S, src, "models", m, "by_n", n, "set_id") != G(S, "curve_d90", "models", "hm", "by_n", n, "set_id"):
                    raise ValueError(f"{src} {m} {n}: the three models did not run on the same set at this length")
    if len({G(S, "curve_d90", "models", "hm", "by_n", n, "set_id") for n in lengths}) != len(lengths):
        raise ValueError("two lengths of the sweep share a set")
    tries = {m: R(S, "curve_d90", "models", m, "tries_per_puzzle") for m in CURVE_MODELS}
    if tries["om"].value != tries["sm"].value:
        raise ValueError("Opus-medium and Sonnet-medium have different tries per puzzle")
    if any(not S.has("curve_d90", join_key("models", "hm", "by_n", n, f"vote_at_{tries['hm'].value}")) for n in lengths):
        raise ValueError("the Haiku-medium vote is not over all its tries")
    vote_key = f"vote_at_{tries['hm'].value}"
    cols = ["Model", "Steps", "Puzzles", "Samples per puzzle"]
    for _, rule in CURVE_SRC:
        cols += [f"Whole answer, chain (%) [95% interval], {rule}", f"Whole answer, pieces (%) [95% interval], {rule}",
                 f"Whole answer, pooled (%) [95% interval], {rule}", f"Format compliance, chain (%), {rule}", f"Format flag fires, {rule}"]
    rows: List[List[Cell]] = []
    ps_rows: List[List[Cell]] = []
    vote_rows: List[List[Cell]] = []
    fmt_rows: List[List[Cell]] = []
    q_rows: List[List[Cell]] = []

    def sweep_ci(src: str, segs: List[Any], tie: bool = True) -> Cell:
        """A length-sweep cell under one marking rule; a collapsed interval takes free analysis 4's exact one for that rule's own file
        (revision 2 names the cells of both files)."""
        return acc_ci(S, src, segs, dp=2, prop=True, marks=marks, tie=tie)

    for m in CURVE_MODELS:
        name = tag_name(m)
        for n in lengths:
            b = ["models", m, "by_n", n]
            row = [L(name), _steps(n, f"models.{m}.by_n"), integer(R(S, "curve_d90", *b, "n_base")), integer(tries[m])]
            for src, _ in CURVE_SRC:
                for sk, sw in CURVE_SHAPES:
                    row.append(sweep_ci(src, [*b, "whole_answer", sk]))
                # format compliance beside the accuracy (settlement E-01): chain tries only (the files hold none for pieces)
                row += [P(R(S, src, *b, "format_compliance_1xn"), 2, prop=True), text_of(R(S, src, *b, "format_flag"), YES_NO)]
            rows.append(row)
            ps = [L(name), _steps(n, f"models.{m}.by_n")]
            for src, _ in CURVE_SRC:
                for sk, sw in CURVE_SHAPES:
                    ps.append(sweep_ci(src, [*b, "per_step", sk]))
            ps_rows.append(ps)
            if m == "hm":
                vote_rows.append([_steps(n, f"models.{m}.by_n")] + [acc_ci(S, "curve_d90", [*b, vote_key, sk], dp=2, prop=True, marks=marks, tie=True)
                                                for sk, _ in CURVE_SHAPES])
            f = [L(name), _steps(n, f"models.{m}.by_n"), integer(R(S, "curve_d90", *b, "answered_1xn"))]
            for src, _ in CURVE_SRC:
                f += [P(R(S, src, *b, "format_compliance_1xn"), 2, prop=True), text_of(R(S, src, *b, "format_flag"), YES_NO),
                      integer(R(S, src, *b, "unplaceable_1xn"))]
            f.append(integer(R(S, "curve_d90", *b, "truncated")))
            fmt_rows.append(f)
            qr = [L(name), _steps(n, f"models.{m}.by_n"), P(R(S, "curve_d90", "models", m, "q", "by_n", n, "q_n"), 2, prop=True),
                  CI(S, "curve_d90", ["models", m, "q", "by_n", n, "band"], dp=2, prop=True, marks=marks, no_exact=True)]
            for src, _ in CURVE_SRC:
                for sk, _ in CURVE_SHAPES:
                    qr.append(num(R(S, src, "models", m, "q", "by_n", n, "observed_over_q_n", sk), dp=2))
            qr.append(EMPTY)
            q_rows.append(qr)
        # the 24-step extrapolation: a dotted reference only, no observed value
        q24 = ["models", m, "q", "24"]
        q_rows.append([L(name), _steps("24", f"models.{m}.q"), P(R(S, "curve_d90", *q24, "q_n"), 2, prop=True),
                       CI(S, "curve_d90", [*q24, "band"], dp=2, prop=True, marks=marks, no_exact=True), *[EMPTY] * 6,
                       quoted_text(R(S, "curve_d90", *q24, "label"))])
    # per-model q table as its own panel
    q_head = ["Model", "q (%): share of pieces right, pieces only, pooled over the lengths", "q 95% interval (%)"]
    q_model_rows = [[L(tag_name(m)), P(R(S, "curve_d90", "models", m, "q", "q"), 2, prop=True),
                     CI(S, "curve_d90", ["models", m, "q", "ci95"], dp=2, prop=True, marks=marks, no_exact=True)] for m in CURVE_MODELS]
    pil_rows: List[List[Cell]] = []
    for m in CURVE_MODELS:
        for pk in S.keys("curve_d90", join_key("pilot1", m)):
            pb = ["pilot1", m, pk]
            if G(S, "curve", *pb, "sets") != G(S, "curve_d90", *pb, "sets") or G(S, "curve", *pb, "label") != G(S, "curve_d90", *pb, "label"):
                raise ValueError(f"pilot1 {m} {pk}: sets or label differ between the two files")
            words, presets, n_sets = PILOT1_MARKERS[pk]
            if presets not in str(G(S, "curve_d90", *pb, "label")) or len(G(S, "curve_d90", *pb, "sets")) != n_sets:
                raise ValueError(f"pilot1 {m} {pk}: the stamped label or sets do not fit the printed words")
            pil_rows.append([L(tag_name(m)), L(words), integer(R(S, "curve_d90", *pb, "n_base")),
                             acc_ci(S, "curve_d90", pb, dp=2, prop=True, marks=marks, tie=True),
                             acc_ci(S, "curve", pb, dp=2, prop=True, marks=marks, tie=True)])

    # the note's "the one preset used later, whose rules the length sweep keeps at every length": each length's stamped preset is that
    # preset's rules at n steps (l14n<n>), the preset the first marker's label names (checks; preset ids are never printed)
    for m in CURVE_MODELS:
        for n in lengths:
            if G(S, "curve_d90", "models", m, "by_n", n, "preset") != f"l14n{n}":
                raise ValueError(f"{m} {n}: the sweep's preset is not the l14 rules at {n} steps")

    def rule_cols(prefix: str) -> List[str]:
        out = []
        for _, rule in CURVE_SRC:
            out += [f"{prefix}, chain, {rule}", f"{prefix}, pieces, {rule}", f"{prefix}, pooled, {rule}"]
        return out

    ps_cols = ["Model", "Steps"] + [c + " (%) [95% interval]" for c in rule_cols("Per-step accuracy")]
    vote_cols = ["Steps", "Haiku-medium vote of its samples, chain (%) [95% interval]",
                 "Haiku-medium vote of its samples, pieces (%) [95% interval]", "Haiku-medium vote of its samples, pooled (%) [95% interval]"]
    fmt_cols = ["Model", "Steps", "Chain samples answered"]
    for _, rule in CURVE_SRC:
        fmt_cols += [f"Format compliance, chain (%), {rule}", f"Format flag fires, {rule}", f"Chain samples not placeable, {rule}"]
    fmt_cols.append("Truncated calls")
    q_cols = ["Model", "Steps", "Reference q^N (%)", "q^N band (95% interval)"] + rule_cols("Observed\u00a0/ q^N") + [
        "Note"]
    pil_cols = ["Model", "Marker", "Puzzles", "Whole answer, pooled (%) [95% interval], Deviation 2 rule",
                "Whole answer, pooled (%) [95% interval], original rule"]
    vote_label = R(S, "curve_d90", "models", "hm", "by_n", lengths[0], vote_key, "label")
    for n in lengths:                                   # one label for the vote at every length (it is printed once, in plain words)
        if G(S, "curve_d90", "models", "hm", "by_n", n, vote_key, "label") != vote_label.value:
            raise ValueError(f"the vote's label differs at {n} steps")
    # polish §7.3: a column with one value in every row moves to a note (each is checked to print one value)
    const13 = fold_constants(cols, rows, ["Puzzles"])
    if const13["Puzzles"].printed != integer(n_ref).printed:
        raise ValueError("TAB-13's puzzles column is not the set size the note gives")
    fconst = fold_constants(fmt_cols, fmt_rows, ["Truncated calls"])
    t = Table([L(c) for c in cols], rows, [], {})
    t.panels = [("Per-step accuracy", Table([L(c) for c in ps_cols], ps_rows)),
                (f"Haiku-medium vote of its samples ({VOTE_WORDS[vote_label.value]})", Table([L(c) for c in vote_cols], vote_rows)),
                ("Format compliance and unplaceable samples on chains", Table([L(c) for c in fmt_cols], fmt_rows, [
                    note("Columns that print one value in every row are left out: the number of truncated calls is",
                         joined(fconst["Truncated calls"], L("in every row."), sep=" "))])),
                ("q per model (pieces only)", Table([L(c) for c in q_head], q_model_rows)),
                ("Independent-pieces reference and observed / q^N", Table([L(c) for c in q_cols], q_rows)),
                ("Pilot 1 markers (24 steps, exploratory)", Table([L(c) for c in pil_cols], pil_rows))]
    flag_words, boundary = _boundary_flags(S, lengths)
    notes = [
        note("Whole-answer accuracy is the share of samples with every step right; a chain is right only if every step line and the answer "
             "line are right. Both marking rules are shown side by side: the Deviation 2 rule, which is official, and the "
             "original rule, under which a step line written more than once fails even when the repeats are identical."),
        # the format flag's rule, in the locked check's own words, and D-166's ruled line on the flags that sit exactly on it (Edith, proof 3,
        # C.42 and p. 104); both are checked against the pinned code and the stamped flags (`_boundary_flags`)
        note("Format compliance sits beside the whole-answer accuracy: the share of answered chain samples whose format was ok under each "
             "marking rule (the files give it for chains only), with the format flag, which fires when", flag_words,
             "of the answered chain samples are not ok. Panel 3 adds the chain samples answered and not placeable."),
        boundary,
        note("Per-step accuracy (Panel 1): for pieces, the share of a sample's pieces that are right (a missing or unanswered "
             "sample scores nothing); for chains, each step is judged from the model's own previous step, and only samples whose step "
             "lines could be placed count: unplaceable chain samples are left out (Panel 3 counts them)."),
        note("Each length has its own small set:", integer(n_ref),
             unprinted(const13["Puzzles"], "every model and length prints this set size"), "puzzles. Haiku-medium has",
             integer(tries["hm"]),
             "samples per puzzle; Opus-medium and Sonnet-medium have", joined(integer(tries["om"]), L("."), sep="")),
        note("Intervals are 95% and unadjusted: cluster bootstrap over puzzles with", integer(R(S, "curve_d90", "draws")),
             "resamples, except Opus-medium and Sonnet-medium per-shape whole-answer intervals, which are Wilson (the file's interval field)."),
    ]
    _sweep_exact_cover(S, marks)
    if marks.exact:
        notes.append(exact_note())
        chain_words = _chain_n_words(S, marks, n_ref, tries)
        if chain_words:
            notes.append(note(chain_words.strip()))
    q_models = _q_zero_models(S, marks, lengths)
    if q_models:
        notes.append(_q_zero_note(S, q_models, marks))
    notes += [
        note("Haiku-medium's vote (Panel 2) is over all", integer(tries["hm"]), "of its samples per puzzle and is",
             joined(text_of(vote_label, VOTE_WORDS), L(":"), sep=""), "its cost is not set equal to that of another model's answer."),
        note("q is each model's share of pieces right, estimated from the pieces puzzles only and pooled over the lengths; q^N is the "
             "independent-pieces reference and observed / q^N compares the observed whole-answer accuracy with it. The 24-step row is an extrapolation "
             "only; its label, quoted as stamped, says \"dotted\", and the figures draw the line dashed."),
        note("Pilot 1 markers are at 24 steps, exploratory, and ran before Lock 2 with a different rule mix, different sets and different "
             "timing; they never enter q. A preset is one setting of the puzzle generator (its rule kinds and dials). One marker pools "
             "Pilot 1's sets of three rule-set presets; the other only those of the one preset used later, whose rules the length sweep "
             "keeps at every length."),
        note("The sweep is descriptive (pre-registered as such); no test is run on it."),
    ]
    t.notes = notes
    t.caption = {
        "tier": [L("pre-registered descriptive (the length sweep); 24-step markers exploratory"
                   + ("; the exact intervals are post hoc (free analysis 4)" if marks.exact else ""))],
        "study": [L("Length sweep: Haiku-medium, Opus-medium and Sonnet-medium at"), *_length_cells(lengths)],
        "set": [L("the length sweep's own puzzle set at each length, the same set for the three models; the Pilot 1 markers come from "
                  "Pilot 1's sets")],
        "n": [L("puzzles per length:"), joined(integer(n_ref), L(";"), sep=""), L("samples per puzzle:"), integer(tries["hm"]),
              L("(Haiku-medium) and"), integer(tries["om"]), L("(Opus-medium and Sonnet-medium)")],
        "interval": [L("95%, unadjusted: cluster bootstrap over puzzles; Wilson for Opus-medium and Sonnet-medium per-shape whole-answer "
                       "accuracy" + ("; exact Clopper–Pearson over puzzles (free analysis 4, post hoc) where a bootstrap interval "
                                     "collapsed" if marks.exact else "")
                       + ("; q and its q^N bands have no exact interval (zero width where they collapsed)" if q_models else ""))],
        "price": [L("not applicable (no cost column)")]}
    define_exact(t)
    # the supplement's layouts (batch g): the full table is too wide even for a sideways page at its columns' widths, so it splits by
    # marking rule, sideways (Model and Steps repeat); the panels hold both rules side by side where they fit sideways at footnotesize
    # (the notes of the whole table print under the last panel, a float)
    rule_cols_of = lambda rule: [c.printed for c in t.columns if c.printed.endswith(rule)]                      # noqa: E731
    split(t, True, [["Samples per puzzle"] + rule_cols_of(CURVE_SRC[0][1]), rule_cols_of(CURVE_SRC[1][1])], key=("Model", "Steps"))
    t.groups = starts(rows, family)                                  # a model's five lengths together (polish §7.7)
    t.spaced = True       # a little space after every row: each sideways part fills its page (Edith §1.4: 59% and 55% before)
    per_step, vote, fmt_p, q_model, q_n, pilot = (tab for _, tab in t.panels)
    per_step.layout, per_step.font = "landscape", "footnotesize"
    per_step.groups = starts(ps_rows, lambda r: r[0].printed)
    right_align(per_step, *ps_cols[2:], equal=True)     # the value columns, right-aligned and as wide as each other (Edith, proof 4, p. 98)
    vote.layout = "landscape"        # a short panel between sideways ones: it shares panel 1's sideways page (alone it was 20% of a page)
    fmt_p.layout, fmt_p.font = "landscape", "footnotesize"          # its columns' whole words need more than 6.5 in (proof 2)
    fmt_p.groups = starts(fmt_rows, lambda r: r[0].printed)
    q_model.layout = "landscape"      # three rows: sideways, so that it can share Panel 3's page (a portrait float of it stood alone, p. 105)
    q_n.layout, q_n.font = "landscape", "footnotesize"
    q_n.groups = starts(q_rows, lambda r: r[0].printed)
    right_align(q_n, "q^N band (95% interval)")
    pilot.layout = "float"
    pilot.groups = starts(pil_rows, lambda r: r[0].printed)
    return print_rules(t)


def _length_cells(lengths: List[str]) -> List[Cell]:
    """The sweep's lengths, from the file's by_n keys, as step-count labels."""
    return [L(f"{n} steps" + ("," if i < len(lengths) - 1 else "")) for i, n in enumerate(lengths)]


# Free analysis 4's stated reasons for leaving the length sweep's q without an exact interval (result.excluded, one entry per file,
# each opening with the file's source name): the original rule's gives the reason, the Deviation 2 rule's points to it. The note prints
# the reason without the source name and the closing "no exact interval", which the note says in words.
FA4_Q_REASON = re.compile(r"^curve: (q pools .+, and its q\^N bands are powers of its interval); no exact interval$")
FA4_Q_SAME = "curve_d90: as for the original rule's q"


def _sweep_exact_cover(S: Store, marks: Marks) -> None:
    """The check behind TAB-13's exact intervals (nothing is printed from it): the table prints every cell free analysis 4 gives for the
    two length-sweep files, each once, under its own rule."""
    paths = {S.sources[src].path for src, _ in CURVE_SRC}
    want = {join_key(*FA4_CELLS, i) for i, c in enumerate(G(S, "fa4", *FA4_CELLS)) if c["source"] in paths}
    got = [b for src, _, b in marks.exact if S.sources[src].path in paths]
    if set(got) != want or len(got) != len(want):
        raise ValueError(f"TAB-13 prints {len(set(got))} of free analysis 4's {len(want)} length-sweep cells ({len(got)} times)")


def _chain_n_words(S: Store, marks: Marks, n_ref: Ref, tries: Dict[str, Ref]) -> str:
    """The exact note's sentence for a length-sweep cell whose n is below the set's base puzzles ('' when none is). Every exact per-step
    chain cell of a model with one try per puzzle has n = the set's base puzzles less that length's unplaceable chain tries (Panel 3's
    count), whether or not it is short, so the sentence holds for each of that model's exact per-step chain cells; every
    other exact length-sweep cell has n = the set's base puzzles."""
    short: List[str] = []
    for src, key, base in marks.exact:
        segs = parse_key(key)
        if segs[0] != "models":
            continue
        n_fa4 = S.get("fa4", base + ".n")
        m, n = segs[1], segs[3]
        if segs[4:] == ["per_step", "1xn"] and tries[m].value == 1:
            if n_ref.value - n_fa4 != G(S, src, "models", m, "by_n", n, "unplaceable_1xn"):
                raise ValueError(f"{src}:{key}: n is not the set's base puzzles less the unplaceable chain tries")
        elif n_fa4 != n_ref.value:
            raise ValueError(f"{src}:{key}: n other than the set's base puzzles outside a one-try model's per-step chain cell")
        if n_fa4 != n_ref.value and tag_name(m) not in short:
            short.append(tag_name(m))
    if not short:
        return ""
    return (" In " + _and_list([f"{s}'s" for s in short]) + " per-step chain cells the count in the mark is only the puzzles whose "
            "chain sample could be placed: the set's puzzles less the unplaceable chain samples (Panel 3).")


def _q_zero_models(S: Store, marks: Marks, lengths: List[str]) -> List[str]:
    """The models whose q interval TAB-13 flags '(zero width)', in table order. Only q and its q^N bands may be flagged (CI refuses any
    other collapsed interval that free analysis 4 does not cover); a model's bands are its q interval to the power N (checked), so all of
    them are flagged with its q and none without it."""
    q_models = [m for m in CURVE_MODELS if ("curve_d90", join_key("models", m, "q", "ci95")) in marks.zero]
    want = set()
    for m in q_models:
        lo, hi = G(S, "curve_d90", "models", m, "q", "ci95")
        want.add(("curve_d90", join_key("models", m, "q", "ci95")))
        for at in [["by_n", n] for n in lengths] + [["24"]]:
            band, N = G(S, "curve_d90", "models", m, "q", *at, "band"), int(at[-1])
            if abs(band[0] - lo ** N) > 1e-9 or abs(band[1] - hi ** N) > 1e-9:
                raise ValueError(f"{m} q at {N} steps: the q^N band is not q's interval to the power N")
            want.add(("curve_d90", join_key("models", m, "q", *at, "band")))
    if set(marks.zero) != want or len(marks.zero) != len(want):
        raise ValueError(f"TAB-13 flags {sorted(marks.zero)}, not exactly the q intervals and q^N bands of {q_models}")
    return q_models


def _fa4_excluded(S: Store, src: str, bands: bool = False) -> int:
    """The index of free analysis 4's one `excluded` entry for a pinned source (its text opens with the source's name): the entry for
    q itself, or (bands=True) revision 3's entry for q's q^N bands, which revision 3 lists separately."""
    hits = [i for i, e in enumerate(G(S, "fa4", "result", "excluded")) if str(e["what"]).startswith(src + ": ")
            and ("q^N bands:" in str(e["what"])) == bands]
    if len(hits) != 1:
        raise ValueError(f"free analysis 4 has {len(hits)} excluded {'q^N band' if bands else 'q'} entries for {src}")
    return hits[0]


def _q_zero_note(S: Store, q_models: List[str], marks: Marks) -> List[Cell]:
    """The note for the flagged q intervals and q^N bands: free analysis 4's stated reason (read from its `excluded` entries, whose
    counts of left-out intervals must be the files' collapsed q intervals) and its q_note, whose 'exact counterpart', the pieces
    per-step cells of the models whose q is flagged, must carry exact intervals at every length under both rules in this table (checked;
    the note's closing clause names those models and says so)."""
    i90, i = _fa4_excluded(S, "curve_d90"), _fa4_excluded(S, "curve")
    if G(S, "fa4", "result", "excluded", i90, "what") != FA4_Q_SAME:
        raise ValueError("free analysis 4's entry for the Deviation 2 rule's q no longer points to the original rule's reason")
    what = G(S, "fa4", "result", "excluded", i, "what")
    mt = FA4_Q_REASON.match(what)
    if not mt:
        raise ValueError(f"free analysis 4's reason for leaving q out is not the one the note prints: {what!r}")
    for src, ii in (("curve_d90", i90), ("curve", i)):
        collapsed = [m for m in CURVE_MODELS if len(set(G(S, src, "models", m, "q", "ci95"))) == 1]
        if G(S, "fa4", "result", "excluded", ii, "zero_width_intervals") != len(collapsed):
            raise ValueError(f"free analysis 4 leaves out a number of {src} intervals other than its collapsed q intervals")
        if src == "curve_d90" and collapsed != q_models:
            raise ValueError("the flagged q intervals are not the Deviation 2 file's collapsed ones")
        # revision 3 also lists q's q^N bands as left out: its count must be the file's collapsed bands of those models
        bands = [(m, at) for m in collapsed for at in ([["by_n", n] for n in S.keys(src, join_key("models", m, "q", "by_n"))] +
                                                      [[k] for k in S.keys(src, join_key("models", m, "q")) if k.isdigit()])
                 if len(set(G(S, src, "models", m, "q", *at, "band"))) == 1]
        if G(S, "fa4", "result", "excluded", _fa4_excluded(S, src, bands=True), "zero_width_intervals") != len(bands):
            raise ValueError(f"free analysis 4's q^N band count for {src} is not the file's collapsed bands")
    exact = {(src, key) for src, key, _ in marks.exact}
    for m in q_models:
        for src, _ in CURVE_SRC:
            for n in S.keys(src, join_key("models", m, "by_n")):
                if (src, join_key("models", m, "by_n", n, "per_step", "nx1")) not in exact:
                    raise ValueError(f"{src} {m} {n}: the pieces per-step cell, q's exact counterpart, has no exact interval here")
    names = _and_list([f"{tag_name(m)}'s" for m in q_models])
    return note("\"(zero width)\" marks " + names + " q interval" + ("s" if len(q_models) > 1 else "") + " (Panel 4) and "
                "q^N bands (Panel 5), which collapsed to one value; free analysis 4 gives them no exact interval (post hoc):",
                joined(L("\""), text_of(R(S, "fa4", "result", "excluded", i, "what"), {what: mt.group(1)}), L("\"."), sep=""),
                "Its note on q adds:", joined(L("\""), text_of(R(S, "fa4", "result", "q_note")), L("\";"), sep=""),
                names + " pieces per-step cells carry exact intervals at every length under both marking rules (Panel 1). "
                "In the first quotation the file's \"base puzzles\" are the paper's puzzles.")


# D-166's ruled line (the decision register, ruled 2026-10-16, "Okay."): the disclosure of the length sweep's format flags that sit exactly on
# the flag's threshold. It is printed word for word (Edith, proof 3, C.42); the numbers and the rule's words are read from the stamped flags
# and the locked code (`_boundary_flags`), and the build stops unless the printed line is this one.
D166_LINE = ("Three flags sit at exactly 5.0% non-compliance; the locked check raises them through floating-point rounding, though its rule "
             "reads 'more than 5%'; we report them as stamped.")
# D-181 (ruled 2026-10-20, "yes add the clause"): under Table S24 (TAB-13) only, D-166's line gains one clause, so the line matches the
# five flagged 5.0% cells TAB-13 prints under both marking rules; set at the line's end, before its full stop.
D181_CLAUSE = "(Opus-medium's two cells sit at exactly 5.0% under the original rule's columns too, raised the same way)"
D166_S24_LINE = D166_LINE[:-1] + " " + D181_CLAUSE + "."
CURVE_PY = "s1b_curve_py_s1b"        # the length sweep's code, curve.py (unchanged since a8f0acd, before the sweep's files were written)


def _boundary_flags(S: Store, lengths: List[str]) -> Tuple[Cell, List[Cell]]:
    """The format flag's rule in the locked check's own words ("more than 5%", cut from the code's comment on its threshold) and D-166's
    ruled line as a note, for TAB-13. The line counts the Deviation 2 rule's flags, the official ones (the original rule has two of them
    on the same boundary, Opus-medium at 4 and 12 steps): the build checks that exactly three of the Deviation 2 file's flags fire at a
    chain format compliance whose non-compliance is exactly the threshold in exact decimal arithmetic (one minus 0.95 is 0.05), that the
    locked check `1 - fc > FORMAT_FLAG_ABOVE` (floating point) does raise each of them, and that no flag sits on the threshold without
    firing; the printed "Three" and "5.0" come from those cells. Returns the rule's words (a cell, joined into the format note) and the
    note."""
    above = line_of(S, CURVE_PY, r"^FORMAT_FLAG_ABOVE = 0\.05 +# flagged when more than 5% of answered 1xn tries are not format-ok$", expect=1)
    rule_ref = cell_ref(S, CURVE_PY, above)
    threshold = extract(rule_ref, r"^FORMAT_FLAG_ABOVE = (\d\.\d+) +#")
    words = extract(rule_ref, r"# flagged when (more than \d+%) of answered 1xn tries")
    use = line_of(S, CURVE_PY, r'^\s*"format_flag": fc is not None and 1 - fc > FORMAT_FLAG_ABOVE,$', expect=1)
    guards = [unprinted(words, "the locked check's rule, in its own words"),
              guard(cell_ref(S, CURVE_PY, use), r'^\s*"format_flag": fc is not None and (1 - fc > FORMAT_FLAG_ABOVE),$',
                    "the locked check flags a chain format compliance fc when 1 - fc is above the threshold, in floating point")]
    limit = float(threshold.raw)
    hits: List[Ref] = []
    refs: List[Ref] = []
    for m in CURVE_MODELS:
        for n in lengths:
            b = ["models", m, "by_n", n]
            fc, fl = R(S, "curve_d90", *b, "format_compliance_1xn"), R(S, "curve_d90", *b, "format_flag")
            if dec(1) - dec(fc.value) != dec(threshold.raw):
                continue
            if fl.value is not True or not 1 - float(fc.value) > limit:
                raise ValueError(f"{m} at {n} steps sits exactly on the format flag's threshold without the float check raising it; "
                                 "D-166's line does not describe it")
            hits.append(fc)
            refs += [fc, fl]
    if len(hits) != 3:
        raise ValueError(f"{len(hits)} Deviation 2 flags sit exactly on the threshold; D-166's line says three")
    for fc in hits[1:]:
        _same(fc.value, hits[0].value, "the flags on the threshold share one compliance")
    three = Cell("Three", raw=len(hits), refs=tuple(refs),
                 formula="the number of the Deviation 2 rule's length-sweep format flags that fire at exactly the threshold (counted from each "
                         "model's and length's stamped compliance and flag; printed as a word)")
    non_compliance = num_d(derive("non-compliance of the flags on the threshold, 100 x (1 - chain format compliance)",
                                  lambda c: 100.0 * (1.0 - c), hits[0]), dp=1)
    # D-181's clause: the original rule's file has Opus-medium's cells on the same boundary, flagged the same way (counted and checked
    # like the Deviation 2 rule's: exactly two, both Opus-medium, both raised by the float check)
    orig: List[Ref] = []
    orig_refs: List[Ref] = []
    for m in CURVE_MODELS:
        for n in lengths:
            b = ["models", m, "by_n", n]
            fc, fl = R(S, "curve", *b, "format_compliance_1xn"), R(S, "curve", *b, "format_flag")
            if dec(1) - dec(fc.value) != dec(threshold.raw):
                continue
            if m != "om" or fl.value is not True or not 1 - float(fc.value) > limit:
                raise ValueError(f"original rule: {m} at {n} steps sits exactly on the threshold, not as D-181's clause says")
            orig.append(fc)
            orig_refs += [fc, fl]
    if len(orig) != 2:
        raise ValueError(f"{len(orig)} original-rule cells sit exactly on the threshold; D-181's clause says two")
    two = Cell("two", raw=len(orig), refs=tuple(orig_refs),
               formula="the number of the original rule's length-sweep format flags at exactly the threshold, all Opus-medium's (counted from "
                       "each model's and length's stamped compliance and flag; printed as a word)")
    at = num_d(derive("non-compliance of those cells, 100 x (1 - chain format compliance)", lambda c: 100.0 * (1.0 - c), orig[0]), dp=1)
    cells = [three, L("flags sit at exactly"), joined(non_compliance, L("%"), sep=""),
             L("non-compliance; the locked check raises them through floating-point rounding, though its rule reads"),
             joined(L("'"), words, L("';"), sep=""), with_evidence("we report them as stamped", guards),
             L("(Opus-medium's"), two, L("cells sit at exactly"), joined(at, L("%"), sep=""),
             L("under the original rule's columns too, raised the same way).")]
    printed = " ".join(c.printed for c in cells if c.printed)
    if printed != D166_S24_LINE:
        raise ValueError(f"TAB-13's boundary-flag line is not D-166's ruled line with D-181's clause: {printed!r}")
    return words, note(*cells)


# ---------------------------------------------------------------- TAB-18

# Study 1 arm ids (item_24 keys) with their Study 1b tags, the eight arms both studies ran at 6 steps
CROSS_ARMS = (("haiku-thinking-off", "ho"), ("haiku-low", "hl"), ("haiku-med", "hm"), ("haiku-max", "hx"),
              ("sonnet-low", "sl"), ("sonnet-med", "sm"), ("opus-low", "ol"), ("opus-med", "om"))
ITEM24 = ("reporting", "group_b", "item_24", "table")


def _and_list(names: Sequence[str]) -> str:
    """'A', 'A and B', 'A, B and C' (arm names, labels only)."""
    if not names:
        raise ValueError("an empty list of names")
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _diff(ref_b: Ref, ref_a: Ref, dp: int = 2) -> Cell:
    d = derive("Study 1b minus Study 1 (points)", lambda b, a: b - a, ref_b, ref_a)
    return num_d(d, dp=dp, signed=True, bounds=(0.0,))


def _run_date(S: Store, src: str) -> Cell:
    """The spend log's date for the paid run that a pinned analysis file comes from (the run id is the file's folder name; it is used
    to find the row and is never printed)."""
    run = S.sources[src].path.split("/")[2]
    return text_of(cell_ref(S, "spend_log", _run_line(S, src), "Date"))


def _run_line(S: Store, src: str) -> int:
    run = S.sources[src].path.split("/")[2]
    return line_of(S, "spend_log", rf"^\| \d{{4}}-\d\d-\d\d \| \w+ \| {re.escape(run)} \|", expect=1)


# The cuts from the spend log's "What ran" cells that order Study 1b and the top-up run, which share a date: Study 1b's last commit
# (the end of its window) and the top-up run's first invocation (the start of its window), each a UTC time.
S1B_END = r"Last commit (\d\d:\d\d:\d\d)Z\."
TOPUP_START = r"INVOCATIONs (\d\d:\d\d:\d\d)Z and \d\d:\d\d:\d\dZ"


def _same_model_after(S: Store) -> List[Cell]:
    """The checks behind TAB-18's "after Study 1b" and its oldest-first run windows (returned as unprinted evidence): the top-up's
    same-model check ran on Study 1's main set (its set id is the prefix of Study 1's own puzzle ids); the spend log lists its rows
    newest first (its header says so), so each later run's row is above, on the same or a later date; and where two runs share a date
    the recorded times decide (Edith's Q26: chronological, not by row order): Study 1's main run is on an earlier date than Study 1b,
    and Study 1b's last commit comes before the top-up run's first invocation."""
    sid = G(S, "topup", "inputs", "set", "set_id")
    ids = G(S, "main", "reporting", "realtime", "puzzles")
    if not ids or any(not str(p).startswith(sid + "-") for p in ids):
        raise ValueError("the top-up's same-model check did not run on Study 1's main set")
    head = line_of(S, "spend_log", r"^## Rows \(newest first\)\s*$", expect=1)
    order = [_run_line(S, src) for src in ("topup", "s1b", "main")]
    dates = [str(S.get("spend_log", join_key(f"L{n}", "Date"))) for n in order]
    if not head < order[0] < order[1] < order[2] or not dates[0] >= dates[1] >= dates[2]:
        raise ValueError(f"the spend log does not put the top-up after Study 1b after Study 1 ({order}, {dates})")
    if not dates[2] < dates[1]:
        raise ValueError(f"Study 1's main run and Study 1b share a date ({dates[1]}): order them by their recorded times")
    end_1b = extract(cell_ref(S, "spend_log", order[1], "What ran"), S1B_END)
    start_top = extract(cell_ref(S, "spend_log", order[0], "What ran"), TOPUP_START)
    if not (dates[1], str(end_1b.raw)) < (dates[0], str(start_top.raw)):
        raise ValueError(f"Study 1b's last commit ({dates[1]} {end_1b.raw}Z) is not before the top-up run's first invocation "
                         f"({dates[0]} {start_top.raw}Z)")
    return [guard(cell_ref(S, "spend_log", order[1], "What ran"), S1B_END, "Study 1b's run ended at its last commit"),
            guard(cell_ref(S, "spend_log", order[0], "What ran"), TOPUP_START, "the top-up run started at its first invocation"),
            guard(cell_ref(S, "spend_log", head), r"^## Rows \((newest first)\)$", "the spend log lists its rows newest first")]


def _same_model_arm(S: Store) -> List[Cell]:
    """The evidence behind TAB-18's "Haiku-medium" for the top-up run's same-model check (Edith's Q26: cite the top-up spec that
    defines it): the top-up run's specification, frozen with Lock 4, defines the check in its same-model section as Haiku-medium at the
    main run's Haiku-medium settings, with as many tries per puzzle as the stamped check ran (checked)."""
    spec = "topup_spec_s1b"
    what = r"^\*\*What it is:\*\* (Haiku-medium) ×(\d+), at the main run's Haiku-medium settings exactly"
    n = line_of(S, spec, what, expect=1)
    head = line_of(S, spec, r"^## \d+\. .*same-model check", expect=1)
    nxt = [i for i in S.find_lines(spec, r"^## ") if i > head]
    if not head < n < (nxt[0] if nxt else n + 1):
        raise ValueError("the top-up specification's definition of the check is not in its same-model section")
    r = cell_ref(S, spec, n)
    if int(extract(r, what, group=2).raw) != G(S, "topup", "same_model_check", "tries_per_puzzle"):
        raise ValueError("the top-up specification's tries per puzzle for the same-model check differ from the stamped check's")
    return [guard(r, what.replace("(\\d+)", "\\d+"), "the drift check between runs is Haiku-medium with the main run's configuration"),
            guard(cell_ref(S, spec, head), r"^## \d+\. .*(same-model check)", "the specification's section on the drift check between runs"),
            *frozen_spec(S, spec, "topup")]


@output("TAB-18")
def tab_18(S: Store) -> Table:
    cols = ["Setting", "Study 1 chain (%)", "Study 1b chain (%)", "Difference, chain (points)",
            "Study 1 pieces (%)", "Study 1b pieces (%)", "Difference, pieces (points)",
            "Study 1 pooled (%)", "Study 1b pooled (%)", "Difference, pooled (points)",
            "Format compliance, chain, Study 1 (%)", "Format compliance, chain, Study 1b (%)",
            "Format compliance, pieces, Study 1 (%)", "Format compliance, pieces, Study 1b (%)",
            "Samples per puzzle and shape, Study 1", "Samples per puzzle and shape, Study 1b"]
    rows: List[List[Cell]] = []
    n1b = int(G(S, "s1b", "completeness", "B3", "N"))
    if int(G(S, "main", "n")) != n1b or G(S, "s1b", "completeness", "B3", "set_id") != s1b_set_at(S, n1b):
        raise ValueError("Study 1's length and Study 1b's B3 set do not meet at one length")
    sent = G(S, "s1b", "inputs", "sets", s1b_set_at(S, n1b), "arms_sent")
    # the 1b file's own copy of Study 1's points must agree with Study 1's file (checked here, not printed twice)
    copy = {(p["arm"], p["shape"]): p["mean"] for p in G(S, "s1b", "descriptive", "effort_figure", "study1_points", "points")}
    marked: List[str] = []                           # the arms whose Study 1 pooled point is stamped (names, for the note)
    for arm1, tag in CROSS_ARMS:
        name, model, effort = STUDY1B_TAGS[tag]
        if STUDY1_ARMS[arm1][0] != name:
            raise ValueError(f"{arm1} and {tag} are not the same setting in the names tables")
        if tag not in sent or int(G(S, "s1b", "descriptive", "arms", f"{tag}@6", "N")) != n1b:
            raise ValueError(f"{tag}@6 did not run on Study 1b's set at the B3 length")
        cells: List[Cell] = [setting_label(name)]
        pooled_parts: Dict[str, Ref] = {}
        fmt: List[Cell] = []
        for s1, sb in (("1x6", "1x6"), ("6x1", "6x1")):
            a1 = R(S, "main", *ITEM24, f"{arm1} {s1}", "accuracy_mean")
            if copy[(arm1, s1)] != a1.value:
                raise ValueError(f"{arm1} {s1}: the Study 1b file's copy of Study 1's point differs from Study 1's own")
            ab = R(S, "s1b", "descriptive", "arms", f"{tag}@6", sb, "mean")
            pooled_parts[s1] = a1
            cells += [P(a1, 2), P(ab, 2), _diff(ab, a1)]
            fmt += [P(R(S, "main", *ITEM24, f"{arm1} {s1}", "format_compliance", "format_compliance"), 2, prop=True),
                    P(R(S, "s1b", *FRT.split("."), "format_report", tag, sb, "format_compliance"), 2, prop=True)]
        ab_pool = R(S, "s1b", "descriptive", "arms", f"{tag}@6", "pooled", "mean")
        marker = join_key("main_run_markers", arm1, "pooled", "mean")
        if S.has("main", marker):
            # Study 1's stamped pooled point (a proportion, printed in %); its shape points must be the descriptive table's (a check)
            for s1 in ("1x6", "6x1"):
                _same(100.0 * _f(G(S, "main", "main_run_markers", arm1, s1, "mean")),
                      G(S, "main", *ITEM24, f"{arm1} {s1}", "accuracy_mean"), f"{arm1} {s1}: the stamped marker against item 24")
            mk = S.ref("main", marker)
            a1_pool = P(mk, 2, prop=True)
            d_pool = derive("Study 1b pooled minus 100 * Study 1 pooled", lambda b, m: b - 100.0 * m, ab_pool, mk)
            marked.append(name)
        else:
            x, y = pooled_parts["1x6"], pooled_parts["6x1"]
            a1_pool = num_d(derive("mean of the two shape means (each base puzzle's mean over its two shapes)",
                                   lambda u, v: (u + v) / 2.0, x, y), dp=2)
            d_pool = derive("Study 1b pooled minus the mean of Study 1's two shape means", lambda b, u, v: b - (u + v) / 2.0, ab_pool, x, y)
        cells += [a1_pool, P(ab_pool, 2), num_d(d_pool, dp=2, signed=True, bounds=(0.0,))]
        # tries per base puzzle and shape: Study 1 stamps the tries and the base puzzles per arm and shape (the two shapes must agree);
        # Study 1b stamps tries per item
        t1 = [ITEM24 + (f"{arm1} {s}",) for s in ("1x6", "6x1")]
        if (G(S, "main", *t1[0], "refusals_and_truncations", "tries") != G(S, "main", *t1[1], "refusals_and_truncations", "tries")
                or G(S, "main", *t1[0], "base_puzzles") != G(S, "main", *t1[1], "base_puzzles")):
            raise ValueError(f"{arm1}: tries or base puzzles differ between the shapes")
        if G(S, "main", *t1[0], "refusals_and_truncations", "tries") % G(S, "main", *t1[0], "base_puzzles"):
            raise ValueError(f"{arm1}: tries are not a whole number per base puzzle; the printed integer would hide a remainder")
        tries1 = num_d(derive("tries / base_puzzles", lambda a, c: a / c, R(S, "main", *t1[0], "refusals_and_truncations", "tries"),
                              R(S, "main", *t1[0], "base_puzzles")), dp=0)
        rows.append(cells + fmt + [tries1, integer(R(S, "s1b", "descriptive", "arms", f"{tag}@6", "tries_per_item"))])
    if "same_model" in json.dumps(S.doc("s1b")):
        raise ValueError("the Study 1b file stamps a same-model check: the note must give its status")
    d1, d1b, dtop = _run_date(S, "main"), _run_date(S, "s1b"), _run_date(S, "topup")
    after_ev = _same_model_after(S)
    status = R(S, "topup", "same_model_check", "flag", "status")
    arm_ev = _same_model_arm(S)
    notes = [
        note("A reading across studies: our reading, not a test. The two studies used different puzzle sets, different runs and "
             "different puzzles, and nothing is paired. The difference is Study 1b's point minus Study 1's point, in points; there "
             "is no interval and no p-value."),
        # the runs in time order, oldest first (Edith's Q26), not in the spend log's newest-first row order: by date, and on the date
        # Study 1b and the top-up share, by their recorded times (_same_model_after, whose cuts are the evidence for "after Study 1b")
        note("Runs, oldest first: Study 1's main run on", joined(d1, L(";"), sep=""), "Study 1b's run on",
             joined(d1b, L(";"), sep=""), "the top-up run on", joined(dtop, L(","), sep=""), with_evidence("after Study 1b.", after_ev),
             "The drift check between runs: none was run for Study 1b itself (the Study 1b file records none).",
             with_evidence("The top-up run's drift check, which the top-up run's specification (frozen with Lock 4) defines as "
                           "Haiku-medium with the main run's configuration, re-ran Haiku-medium on Study 1's main set and compared it "
                           "with Study 1's answers; its flag:", arm_ev),
             joined(text_of(status), L("."), sep=""), "It covers Haiku-medium only, not the other settings of this table."),
        note("Study 1 used", integer(R(S, "main", *ITEM24, "opus-med 1x6", "base_puzzles")), "puzzles on its main set. Study 1b's set at",
             integer(R(S, "s1b", "completeness", "B3", "N")), "steps (the Test B3 set) has",
             integer(R(S, "s1b", "descriptive", "arms", "om@6", "pooled", "n_base")), "puzzles."),
        note("Study 1 points are from its pre-specified descriptive table; Study 1b points are from the effort sweep. Study 1's file records "
             "the pooled point of " + _and_list(marked) + " (its shape points equal the table's; checked); for the other settings Study 1's "
             "pooled point is the mean of its two shape means, which is the same pooling (each puzzle's mean over its two shapes)."),
        note("Samples per puzzle and shape differ between the studies and between settings (Panel 1's last two columns). Study 1's is "
             "its recorded samples divided by its recorded puzzles; Study 1b's is recorded in its file."),
        note("Format compliance (Panel 1): share of answered samples whose format was ok, per shape and study."),
    ]
    caption = {
        "tier": [L("cross-study descriptive; our reading, not a test")],
        "study": [L("Study 1 main run at"), integer(R(S, "main", "n")), L("steps, run on"), joined(d1, L(","), sep=""),
                  L("against Study 1b's run on"), joined(d1b, L(","), sep=""), L("its set at"),
                  integer(R(S, "s1b", "completeness", "B3", "N")), L("steps")],
        "set": [L("Study 1's main set against Study 1b's set at"), integer(R(S, "s1b", "completeness", "B3", "N")),
                with_evidence("steps (the Test B3 set); the drift check between runs: none for Study 1b itself; the top-up run's drift check "
                              "on Haiku-medium, run after Study 1b:", [*arm_ev, *after_ev]), text_of(status)],
        "n": [L("puzzles:"), integer(R(S, "main", *ITEM24, "opus-med 1x6", "base_puzzles")), L("(Study 1);"),
              integer(R(S, "s1b", "descriptive", "arms", "om@6", "pooled", "n_base")),
              L("(Study 1b); samples per puzzle and shape by setting in Panel 1's last two columns")],
        "panels": [L("Panel 1: format compliance of the samples (chain and pieces, in each study) and samples per puzzle and shape")],
        "interval": [L("none (point differences only)")],
        "price": [L("not applicable (no cost column)")]}
    # the supplement's layout (batch g): the 16 columns are the accuracies (the table) and the format compliance and samples per puzzle
    # (Panel 1), each at footnotesize and sideways: once no word may break (proof 2), the accuracy part's columns need more than the 6.5 in
    # of a portrait page. The second block is a labelled panel (Edith, proof 4, p. 124: it had no panel label, and the caption says so)
    acc_titles = ["Study 1 chain (%)", "Study 1b chain (%)", "Difference, chain (points)", "Study 1 pieces (%)", "Study 1b pieces (%)",
                  "Difference, pieces (points)", "Study 1 pooled (%)", "Study 1b pooled (%)", "Difference, pooled (points)"]
    fmt_titles = ["Format compliance, chain, Study 1 (%)", "Format compliance, chain, Study 1b (%)",
                  "Format compliance, pieces, Study 1 (%)", "Format compliance, pieces, Study 1b (%)",
                  "Samples per puzzle and shape, Study 1", "Samples per puzzle and shape, Study 1b"]
    if sorted(acc_titles + fmt_titles + ["Setting"]) != sorted(cols):
        raise ValueError("TAB-18's blocks do not hold every column once")

    def block(titles: List[str]) -> Table:
        pick = [0] + [cols.index(x) for x in titles]
        tab = Table([L(cols[j]) for j in pick], [[r[j] for j in pick] for r in rows])
        tab.layout, tab.font = "landscape", "footnotesize"
        tab.groups = starts(rows, family)                              # Haiku, Sonnet, Opus (polish §7.7)
        return tab
    t = block(acc_titles)
    t.notes, t.caption = notes, caption
    t.panels = [("Format compliance and samples per puzzle", block(fmt_titles))]
    return print_rules(t)



# ---------------------------------------------------------------- TAB-16
# Sources: Study 1 `main` (items 9a-9c, 9g, 19, 24) and `main_k`; Study 1b `s1b` and `s1b_k`; free analysis 10 (`fa10`, post hoc: measured
# token usage and thinking tokens as the API reports them, Edith's settlement N1), free analysis 3 (`fa3`, post hoc: each shape's own
# equal-money k at 16 steps) and free analysis 2 (`fa2`, post hoc: the equal-money k at 6 and 12 steps). Item 19's thinking figures stay,
# labelled as biased estimates.

ITEM = ("reporting", "group_b")
S1_SINGLE = ("haiku-thinking-off", "haiku-low", "haiku-med", "haiku-max", "sonnet-low", "sonnet-med", "opus-low", "opus-med")
S1_SHAPES = ("1x6", "6x1")
S1_VOTES = (("t2", "O"), ("t1", "O"), ("t3", "S"))                  # tests whose k is an equal-money k: (test, comparator kind)
FA10_S1 = ("result", "study1")                                     # keys '<Study 1 arm> <shape>'
FA10_S1B = ("result", "study1b")                                   # keys '<tag>@<N> <shape>'
FA10_RATIO = ("result", "haiku_max_over_opus_medium")              # keys 'study1:<N>:<shape>' and 'study1b:<N>:<shape>'
FA10_LABEL = ("result", "label_n1")
# The ruling's label for the API counts (the stamped label_n1 opens with it and goes on with an internal reference, which stays out of
# the paper; checked against the stamped label when the table is built).
FA10_WORDS = "post hoc; thinking tokens as the API reports them"
FA2_ARMS = ("hx@6", "hx@12")                                       # free analysis 2's lengths: result['N=<n>'].equal_money
API_DASH = 3                                                       # the three API thinking cells (does not apply to a vote)
EST_DASH = 2                                                       # the two item 19 estimate cells
# The Study 1b file's stamped cost unit in plain words, for both versions (the stamped string names a pre-registration item, which a
# main-text table does not; Edith's Q22). A changed stamped unit has no printed form: text_of refuses it.
UNIT_WORDS = {"USD per answer, list price (item 9b)": "US dollars per answer at list price"}


def _f(v: Any) -> float:
    """A stamped number as a float (k.json stamps exact decimal strings); for checks only, never printed."""
    from fractions import Fraction
    return float(Fraction(v)) if isinstance(v, str) else float(v)


S1_DEFS_NOTE = r"^research/reporting-definitions-main\.md \((\w+); [^)]*\), items (\d+)-(\d+), "     # the Study 1 file's group-B note
S1_DEFS_ITEMS = (9, 19)          # the definitions TAB-16 calls pre-specified: items 9b, 9c and 9g (costs, CPC, token means) and 19


def _defs_fixed(S: Store) -> List[Cell]:
    """The evidence behind TAB-16's "pre-specified" (not "pre-registered") for Study 1's costs per answer and per correct answer, token
    means and thinking estimates (unprinted guards): the Study 1 file's group-B note says those items follow Study 1's reporting
    definitions at the pinned commit, a range that holds items 9 and 19, and the definitions' header says the paper calls them
    "reporting definitions fixed after prereg-lock-3 and before any main-run result was opened"."""
    src, s = "s1_defs_s1b", S.sources["s1_defs_s1b"]
    gb = R(S, "main", *ITEM, "note")
    if str(extract(gb, S1_DEFS_NOTE).raw) != s.commit:
        raise ValueError(f"the Study 1 file's group-B items follow another revision of the reporting definitions than {s.commit}")
    lo, hi = (int(extract(gb, S1_DEFS_NOTE, group=g).raw) for g in (2, 3))
    if not all(lo <= i <= hi for i in S1_DEFS_ITEMS):
        raise ValueError(f"the Study 1 file's group-B note covers items {lo}-{hi}, not items 9 and 19")
    n = line_of(S, src, r'^4\. \*The paper says: "reporting definitions fixed after prereg-lock-3 and before any main-run result was$',
                expect=1)
    return [guard(gb, r"^(research/reporting-definitions-main\.md) \(\w+; [^)]*\), items \d+-\d+, ",
                  "Study 1's group-B items follow its reporting definitions"),
            guard(cell_ref(S, src, n), r'"(reporting definitions fixed after prereg-lock-3 and before any main-run result) was$',
                  "the reporting definitions were fixed after Lock 3, before any main-run result was opened"),
            guard(cell_ref(S, src, n + 1), r'^(opened)"\.\*$', "the header's sentence ends: opened")]


def _thinking_estimate(S: Store, defs_ev: List[Cell]) -> List[Cell]:
    """The definition of Study 1's pre-specified thinking estimates for TAB-16's note (Edith, proof 3, p. 116: the note gave only the
    file's label, "estimates (visible tokens = characters / 3)", after "defined as:", and no definition): per call, visible tokens are
    estimated as the characters of the visible reply divided by 3, rounded down, and thinking tokens are the output tokens less that
    estimate, never below zero. The words are the reporting definitions' (section 19, pinned) and the divisor is cut from that section's
    line; the build stops unless the stamped label names the same divisor, so the label, quoted after the definition, says the same."""
    src = "s1_defs_s1b"
    head = line_of(S, src, r"^## 19\. Thinking tokens", expect=1)
    vis = line_of(S, src, r"^- visible tokens are estimated as the number of characters of the visible reply \u00f7 \d+, rounded down", expect=1)
    thk = line_of(S, src, r"^- thinking tokens = max\(0, output tokens \u2212 visible estimate\)\.$", expect=1)
    nxt = [i for i in S.find_lines(src, r"^## ") if i > head]
    if not head < vis < thk < (nxt[0] if nxt else thk + 1):
        raise ValueError("the reporting definitions' thinking-estimate lines are not in their section 19")
    divisor = extract(cell_ref(S, src, vis), r"characters of the visible reply \u00f7 (\d+), rounded down")
    lab = R(S, "main", *ITEM, "item_19", "label")
    if extract(lab, r"visible tokens = characters / (\d+)\)").raw != divisor.raw:
        raise ValueError("Study 1's stamped thinking-estimate label names another divisor than the reporting definitions")
    guards = [guard(cell_ref(S, src, head), r"^## 19\. (Thinking tokens)", "section 19 of the reporting definitions defines the thinking estimates"),
              guard(cell_ref(S, src, thk), r"^- (thinking tokens = max\(0, output tokens \u2212 visible estimate\))\.$",
                    "a call's thinking tokens are its output tokens less the visible estimate, never below zero")]
    return [with_evidence("The two estimate columns are Study 1's pre-specified thinking estimates. Per call, visible tokens are estimated as "
                          "the number of characters of the visible reply divided by", [*defs_ev, *guards]),
            joined(divisor, L(", rounded down, and thinking tokens are the output tokens less that estimate, never below zero (the "
                              "file's label:"), sep=""),
            joined(L("\""), text_of(lab), L("\")."), sep="")]


def _fa10_words(S: Store) -> str:
    if not str(G(S, "fa10", *FA10_LABEL)).startswith(FA10_WORDS):
        raise ValueError("free analysis 10's stamped label no longer opens with the ruling's words")
    return FA10_WORDS


def _opt(S: Store, src: str, segs: Sequence[Any], fn) -> Cell:
    """A cell from a key the file may not hold: empty when it is not there."""
    if S.has(src, join_key(*segs)):
        return fn(R(S, src, *segs))
    return EMPTY


def _usd_or_text(r: Ref) -> Cell:
    """A cost, or the file's own word where there is none ("undefined (no correct answer)"), in quotation marks (rule 4)."""
    return usd(r) if isinstance(r.value, (int, float)) else quoted_text(r)


def _cost_ratio(cost: Ref, opus: Ref) -> Cell:
    return num_d(derive("arm cost / Opus-medium cost (same shape)", lambda a, b: a / b, cost, opus), dp=3)


def _s1_k(S: Store, kind: str, sh: str) -> str:
    return "opus" if kind == "O" else "sonnet"


def _same(a: Any, b: Any, what: str) -> None:
    """Two stamped values that must agree to float rounding (a check; nothing is printed from it). Exact decimal strings are read too."""
    try:
        x, y = _f(a), _f(b)
    except (TypeError, ValueError):
        raise ValueError(f"{what}: {a!r} or {b!r} is not a number")
    if isinstance(a, bool) or isinstance(b, bool) or abs(x - y) > 1e-9 * max(1.0, abs(y)):
        raise ValueError(f"{what}: {a!r} != {b!r}")


def _vote_setting(S: Store, kk: Sequence[Any], cmp_name: str) -> Cell:
    """A Study 1 vote's Setting cell from its k.json entry: 'k = 36 (cost-matched with Opus-medium)', or for a k held to the cap
    'k = 40 (capped; cost-matched k = 44 with Opus-medium)', since a capped vote spends less than its comparator (final-check F11)."""
    k_ref, raw = R(S, "main_k", *kk, "k"), R(S, "main_k", *kk, "raw_k")
    if G(S, "main_k", *kk, "capped"):
        if not (raw.value > k_ref.value == G(S, "main_k", *kk, "cap") == G(S, "main_k", *kk, "samples_drawn")):
            raise ValueError(f"k.json {join_key(*kk)}: capped, but k is not the cap (the samples drawn) below the raw k")
        return joined(L("Haiku-medium vote, k ="), integer(k_ref), L("(capped; cost-matched k ="), integer(raw), L("with " + cmp_name + ")"))
    if raw.value != k_ref.value:
        raise ValueError(f"k.json {join_key(*kk)}: not capped, but k differs from the raw k")
    return joined(L("Haiku-medium vote, k ="), integer(k_ref), L("(cost-matched with " + cmp_name + ")"))


def _api_cells(S: Store, block: Sequence[Any]) -> List[Cell]:
    """Mean thinking tokens per call, thinking share of output tokens and of list cost, as the API reports them (free analysis 10)."""
    return [tk(R(S, "fa10", *block, "mean_thinking_tokens"), 1),
            P(R(S, "fa10", *block, "thinking_share_of_output"), 2, prop=True),
            P(R(S, "fa10", *block, "thinking_share_of_list_cost"), 2, prop=True)]


def _fa10_1b_block(S: Store, arm: str, sh: str) -> List[Any]:
    """Free analysis 10's block for a Study 1b arm and shape; its call count must be the Study 1b file's final count for that shape."""
    b = [*FA10_S1B, f"{arm} {sh}"]
    if G(S, "fa10", *b, "calls") != G(S, "s1b", "descriptive", "arms", arm, sh, "final"):
        raise ValueError(f"free analysis 10 {arm} {sh}: calls differ from the Study 1b file's final count")
    return b


def _s1_tokens(S: Store, arm: str, sh: str) -> Tuple[Ref, Ref]:
    """Mean input and output tokens per try of a Study 1 single-call arm: item 9g's where it stamps them (pre-specified), free analysis
    10's otherwise (post hoc). Where both files hold a value they must agree."""
    f10 = [*FA10_S1, f"{arm} {sh}"]
    if arm == "haiku-med":
        b = [*ITEM, "item_9g", sh, "by_k", 0]
        if G(S, "main", *b, "k") != 1:
            raise ValueError("item 9g's first vote-curve point is not k = 1")
        refs = (R(S, "main", *b, "haiku_mean_input_tokens"), R(S, "main", *b, "haiku_mean_output_tokens"))
    elif arm in ("opus-med", "sonnet-med"):
        b = [*ITEM, "item_9g", sh, "comparators", arm]
        refs = (R(S, "main", *b, "mean_input_tokens"), R(S, "main", *b, "mean_output_tokens"))
    else:
        return R(S, "fa10", *f10, "mean_input_tokens"), R(S, "fa10", *f10, "mean_output_tokens")
    _same(refs[0].value, G(S, "fa10", *f10, "mean_input_tokens"), f"{arm} {sh}: input tokens, item 9g against free analysis 10")
    _same(refs[1].value, G(S, "fa10", *f10, "mean_output_tokens"), f"{arm} {sh}: output tokens, item 9g against free analysis 10")
    return refs


def _hx_ratio_ref(S: Store, study: str, n: int, sh: str, what: str, hx: Ref, om: Ref) -> Ref:
    """Free analysis 10's stamped Haiku-max / Opus-medium ratio (`what`: 'output_tokens' or 'list_cost_per_call') on one length and
    shape, checked against the two stamped values it divides."""
    r = R(S, "fa10", *FA10_RATIO, f"{study}:{n}:{sh}", what)
    _same(r.value, float(hx.value) / float(om.value), f"free analysis 10 {study}:{n}:{sh} {what}")
    return r


@output("TAB-16")
@main_text
def tab_16(S: Store) -> Table:
    import math

    cols = ["Study", "Steps", "Setting", "Shape", "Accuracy (%)", "Format compliance (%)", "List cost per answer ($)",
            "Batch cost per answer ($)", "List cost per correct answer ($)", "Batch cost per correct answer ($)",
            # the long qualifiers of three headers are in the notes (which ratios and token means are post hoc: the cost-ratio note and the
            # token-means note), so the header row is not seven lines tall and the first float fits its page (Edith, proof 3, p. 108)
            "Cost ratio (see note)",
            "Spend share of a vote (see note)",
            "Calls (usage records)",
            "Mean input tokens per answer (see note)",
            "Mean output tokens per answer (see note)",
            "Mean thinking tokens per call (API count, post hoc)", "Thinking share of output tokens (%, API count, post hoc)",
            "Thinking share of list cost (%, API count, post hoc)",
            "Thinking share of list cost (%), estimate (biased, see note)",
            "Median thinking tokens, estimate (biased, see note)"]
    rows: List[List[Cell]] = []
    steps1 = integer(R(S, "main", "n"))
    s1n = int(G(S, "main", "n"))

    # ---- Study 1, 6 steps: single-call settings
    for arm in S1_SINGLE:
        for sh in S1_SHAPES:
            rk = f"{arm} {sh}"
            ik = f"{arm}:{sh}"
            f10 = [*FA10_S1, rk]
            if G(S, "fa10", *f10, "calls") != G(S, "main", *ITEM, "item_19", "arms", ik, "calls"):
                raise ValueError(f"{rk}: free analysis 10 and item 19 count different calls")
            opus = R(S, "main", *ITEM, "item_24", "table", f"opus-med {sh}", "cost_per_puzzle", "mean")
            cost = R(S, "main", *ITEM, "item_24", "table", rk, "cost_per_puzzle", "mean")
            if arm == "opus-med":
                ratio_cell = DASH
            elif arm == "haiku-max":
                ratio_cell = ratio(_hx_ratio_ref(S, "study1", s1n, sh, "list_cost_per_call", cost, opus), dp=3)
            else:
                ratio_cell = _cost_ratio(cost, opus)
            tin, tout = _s1_tokens(S, arm, sh)
            rows.append([
                L("Study 1"), steps1, setting_label(STUDY1_ARMS[arm][0]), shp(sh),
                P(R(S, "main", *ITEM, "item_24", "table", rk, "accuracy_mean"), 2),
                P(R(S, "main", *ITEM, "item_24", "table", rk, "format_compliance", "format_compliance"), 2, prop=True),
                usd(cost), usd(R(S, "main", *ITEM, "item_9b", "arms", ik, "batch_mean")),
                _usd_or_text(R(S, "main", *ITEM, "item_24", "table", rk, "cpc", "cpc")),
                _usd_or_text(R(S, "main", *ITEM, "item_24", "table", rk, "cpc", "batch_cpc")),
                ratio_cell, DASH, integer(R(S, "main", *ITEM, "item_19", "arms", ik, "calls")), tk(tin, 1), tk(tout, 1),
                *_api_cells(S, f10),
                P(R(S, "main", *ITEM, "item_19", "arms", ik, "share_of_list_cost"), 2, prop=True),
                tk_stamped(R(S, "main", *ITEM, "item_19", "arms", ik, "median"))])
    # ---- Study 1, votes at their equal-money k
    for t, kind in S1_VOTES:
        _, ch, cmp_, sh, _ = STUDY1_TESTS[t]
        who = _s1_k(S, kind, sh)
        kk = ["k_from_rows", who, sh]
        k_ref = R(S, "main_k", *kk, "k")
        k = int(k_ref.value)
        pt = ["reporting", "group_b", "item_8b", "vote_curve", sh, "points", k - 1]
        if G(S, "main", *pt, "k") != k:
            raise ValueError(f"vote-curve point {k - 1} is not k = {k}")
        if G(S, "main", *ITEM, "item_9g", sh, "by_k", k - 1, "k") != k:
            raise ValueError(f"item 9g point {k - 1} is not k = {k}")
        ik = f"haiku-med:{sh}"
        opus = R(S, "main", *ITEM, "item_24", "table", f"opus-med {sh}", "cost_per_puzzle", "mean")
        cost = R(S, "main", *ITEM, "item_9b", "arms", ik, "vote_at_test_k", t, "mean")
        # k.json's spend is in Batch dollars: its cost per try is item 9b's Batch mean, and the vote's spend is k such tries (checks)
        _same(G(S, "main_k", *kk, "haiku_cost_per_sample"), G(S, "main", *ITEM, "item_9b", "arms", ik, "batch_mean"),
              f"{t}: k.json's Haiku cost per try against item 9b's Batch mean")
        _same(G(S, "main_k", *kk, "spend", "haiku_arm"), k * _f(G(S, "main_k", *kk, "haiku_cost_per_sample")),
              f"{t}: k.json's vote spend against k tries")
        _same(G(S, "main_k", *kk, "spend", "comparator_arm"), G(S, "main", *ITEM, "item_9b", "arms", f"{cmp_}:{sh}", "batch_mean"),
              f"{t}: k.json's comparator spend against item 9b's Batch mean")
        rows.append([
            L("Study 1"), steps1, _vote_setting(S, kk, STUDY1_ARMS[cmp_][0]), shp(sh),
            P(R(S, "main", *pt, "mean"), 2, prop=True),
            P(R(S, "main", *ITEM, "item_24", "table", f"haiku-med {sh}", "format_compliance", "format_compliance"), 2, prop=True),
            usd(cost), usd(R(S, "main_k", *kk, "spend", "haiku_arm")),
            _usd_or_text(R(S, "main", *ITEM, "item_9c", "arms", ik, "vote_at_test_k", t, "cpc")),
            _usd_or_text(R(S, "main", *ITEM, "item_9c", "arms", ik, "vote_at_test_k", t, "batch_cpc")),
            _cost_ratio(cost, opus), num(R(S, "main_k", *kk, "spend", "haiku_over_comparator"), dp=3), DASH,
            tk(R(S, "main", *ITEM, "item_9g", sh, "by_k", k - 1, "haiku_mean_input_tokens"), 1),
            tk(R(S, "main", *ITEM, "item_9g", sh, "by_k", k - 1, "haiku_mean_output_tokens"), 1),
            *[DASH] * API_DASH, *[DASH] * EST_DASH])

    # ---- Study 1b, 16 steps
    arms16 = [a for a in sorted(S.keys("s1b", "descriptive.arms"), key=arm_order) if a.endswith("@16")]
    om16 = ["descriptive", "arms", "om@16"]
    frt = [*FRT.split("."), "format_report"]
    cb_arm = {"hx@16": ("B1", "challenger"), "om@16": ("B1", "comparator")}       # arms whose Batch cost per answer is stamped
    fa10_arms: Dict[str, List[str]] = {}
    for key in S.keys("fa10", join_key(*FA10_S1B)):
        a_, s_ = key.split(" ")
        fa10_arms.setdefault(a_, []).append(s_)
    if sorted(a for a in fa10_arms if a.endswith("@16")) != sorted(arms16):
        raise ValueError("free analysis 10's 16-step arms differ from the Study 1b file's")

    def one_b(arm: str, sh: str) -> List[Cell]:
        tag = arm.split("@")[0]
        a = ["descriptive", "arms", arm]
        n = int(G(S, "s1b", *a, "N"))
        cost = R(S, "s1b", *a, sh, "cost_per_answer") if sh != "pooled" else R(S, "s1b", *a, "pooled", "cost_per_answer")
        opus = R(S, "s1b", *om16, sh, "cost_per_answer")
        if sh == "pooled":
            fmt = EMPTY
            ratio_cell = (ratio(R(S, "s1b", "costs_beside_tests", "B1", "ratio_challenger_over_comparator"), dp=3) if arm == "hx@16"
                          else (DASH if arm == "om@16" else _cost_ratio(cost, opus)))
            shape_cell = L("pooled")
            # the pooled call count is the Study 1b file's own; it must be the two shapes' counts together (a check)
            if G(S, "s1b", *a, "pooled", "final") != sum(G(S, "s1b", *a, s, "final") for s in shapes_of(n)):
                raise ValueError(f"{arm}: pooled final count is not the two shapes' counts together")
            tok = [integer(R(S, "s1b", *a, "pooled", "final"))] + [EMPTY] * (2 + API_DASH)
        else:
            fmt = P(R(S, "s1b", *frt, tag, sh, "format_compliance"), 2, prop=True)
            if arm == "om@16":
                ratio_cell = DASH
            elif arm == "hx@16":
                ratio_cell = ratio(_hx_ratio_ref(S, "study1b", n, sh, "list_cost_per_call", cost, opus), dp=3)
            else:
                ratio_cell = _cost_ratio(cost, opus)
            shape_cell = shp(sh)
            f10 = _fa10_1b_block(S, arm, sh)
            tok = [integer(R(S, "s1b", *a, sh, "final")), tk(R(S, "fa10", *f10, "mean_input_tokens"), 1),
                   tk(R(S, "fa10", *f10, "mean_output_tokens"), 1), *_api_cells(S, f10)]
        if arm in cb_arm:
            b, side = cb_arm[arm]
            batch = usd(R(S, "s1b", "costs_beside_tests", b, side, sh, "batch_usd"))
        else:
            batch = EMPTY
        blk = [*a, sh]
        return [L("Study 1b"), integer(R(S, "s1b", *a, "N")), setting_label(tag_name(tag)), shape_cell, P(R(S, "s1b", *blk, "mean"), 2), fmt,
                usd(cost), batch, _usd_or_text(R(S, "s1b", *blk, "cpc", "cpc")),
                _opt(S, "s1b", [*blk, "cpc", "batch_cpc"], _usd_or_text), ratio_cell, DASH, *tok, *[DASH] * EST_DASH]

    for arm in arms16:
        n = int(G(S, "s1b", "descriptive", "arms", arm, "N"))
        ch, pc = shapes_of(n)
        for sh in (ch, pc, "pooled"):
            rows.append(one_b(arm, sh))
        if arm == "hx@16":
            # the Haiku-max vote at B2's equal-money k, per shape and pooled
            kref = b2_k(S)
            if G(S, "s1b_k", "capped") or G(S, "s1b_k", "raw_k") != G(S, "s1b_k", "k"):
                raise ValueError("Study 1b's k is capped: its Setting label needs the capped form (_vote_setting)")
            i = point_index(S, kref.value)
            for sh in (ch, pc, "pooled"):
                pt = ["descriptive", "vote_curve_n16", "points", i, sh]
                cost = R(S, "s1b", *pt, "cost_per_answer")
                opus = R(S, "s1b", *om16, sh, "cost_per_answer")
                batch = usd(R(S, "s1b", "costs_beside_tests", "B2", "challenger", sh, "batch_usd"))
                b2_ratio = R(S, "s1b", "costs_beside_tests", "B2", "ratio_challenger_over_comparator")
                if sh == "pooled":
                    _same(b2_ratio.value, _f(cost.value) / _f(opus.value), "the ratio stamped beside Test B2 against the pooled vote and "
                          "Opus-medium costs")
                rows.append([
                    L("Study 1b"), integer(R(S, "s1b", "completeness", "B2", "N")),
                    joined(L("Haiku-max vote, k ="), integer(kref), L("(cost-matched with Opus-medium)")),
                    L("pooled") if sh == "pooled" else shp(sh), P(R(S, "s1b", *pt, "mean"), 2),
                    EMPTY if sh == "pooled" else P(R(S, "s1b", *frt, "hx", sh, "format_compliance"), 2, prop=True),
                    usd(cost), batch, usd(R(S, "s1b", *pt, "cpc", "cpc")), EMPTY,
                    ratio(b2_ratio, dp=3) if sh == "pooled" else _cost_ratio(cost, opus),
                    # the equal-money spend share is stamped for the pooled vote only (k.json's k is a pooled k); per shape it is the same
                    # quotient from the two recorded costs, derived (post hoc arithmetic) and printed beside the cost ratio (Edith, proof 5,
                    # B2-S6: 1.091 and 0.733 are spend shares, as Table S23 labels them)
                    ratio(b2_ratio, dp=3) if sh == "pooled" else _cost_ratio(cost, opus),
                    DASH, EMPTY, EMPTY, *[DASH] * API_DASH, *[DASH] * EST_DASH])

    # ---- panel 1: cost-matched k (the pre-registered k.json values, and each shape's own k at 16 steps, post hoc)
    kcols = ["Study", "Steps", "Challenger", "Comparator", "Shape", "k", "Raw k", "Cap", "Capped", "Samples per comparator answer (comparator cost per answer / one challenger sample)",
             "Spend share, challenger vote / comparator", "Label"]
    krows: List[List[Cell]] = []
    for t, kind in S1_VOTES:
        _, ch, cmp_, sh, _ = STUDY1_TESTS[t]
        who = _s1_k(S, kind, sh)
        kk = ["k_from_rows", who, sh]
        krows.append([L("Study 1"), steps1, L(STUDY1_ARMS[ch][0]), L(STUDY1_ARMS[cmp_][0]), shp(sh), integer(R(S, "main_k", *kk, "k")),
                      integer(R(S, "main_k", *kk, "raw_k")), integer(R(S, "main_k", *kk, "cap")),
                      text_of(R(S, "main_k", *kk, "capped"), YES_NO), num(R(S, "main_k", *kk, "ratio"), dp=2),
                      num(R(S, "main_k", *kk, "spend", "haiku_over_comparator"), dp=3), L("pre-registered cost-matched k rule")])
    krows.append([L("Study 1b"), integer(R(S, "s1b_k", "n")), L("Haiku-max"), L("Opus-medium"), L("pooled"), integer(R(S, "s1b_k", "k")),
                  integer(R(S, "s1b_k", "raw_k")), integer(R(S, "s1b_k", "cap")), text_of(R(S, "s1b_k", "capped"), YES_NO),
                  num(R(S, "s1b_k", "ratio"), dp=2), ratio(R(S, "s1b", "costs_beside_tests", "B2", "ratio_challenger_over_comparator"), dp=3),
                  L("pre-registered cost-matched k rule (Study 1b)")])
    n_k = int(G(S, "s1b_k", "n"))
    cap_hx = G(S, "s1b", "constants", "designed_tries", "hx")
    for sh in shapes_of(n_k):
        o = ["result", "own_equal_money_k", sh]
        if G(S, "fa3", *o, "k") != min(math.floor(G(S, "fa3", *o, "om_over_hx_cost_ratio")), cap_hx):
            raise ValueError(f"free analysis 3 own k {sh}: not the floor of the cost ratio held to the designed tries")
        _same(G(S, "fa3", *o, "om_cost_per_answer"), G(S, "s1b", *om16, sh, "cost_per_answer"), f"free analysis 3 Opus-medium cost {sh}")
        spend = derive("vote list cost per answer at the shape's own k / Opus-medium list cost per answer (same shape)", lambda v, c: v / c,
                       R(S, "fa3", *o, "vote_cost_per_answer"), R(S, "fa3", *o, "om_cost_per_answer"))
        krows.append([L("Study 1b"), integer(R(S, "s1b_k", "n")), L("Haiku-max"), L("Opus-medium"), shp(sh), integer(R(S, "fa3", *o, "k")),
                      EMPTY, EMPTY, EMPTY, num(R(S, "fa3", *o, "om_over_hx_cost_ratio"), dp=2), num_d(spend, dp=3),
                      L("post\u00a0hoc (free analysis\u00a03): the shape's own cost-matched k")])     # "post hoc" and "analysis 3" never break
    # the cost-matched k at 6 and 12 steps (free analysis 2, post hoc): its stamped k, the samples it is held to and the samples per comparator answer;
    # the vote's spend ratio is its stamped vote cost per answer over Opus-medium's (no stamped key holds that ratio)
    for arm in FA2_ARMS:
        n = int(G(S, "s1b", "descriptive", "arms", arm, "N"))
        e = ["result", f"N={n}"]
        em = [*e, "equal_money"]
        hx_p, om_p = [*e, "hx_cost_per_answer", "pooled", "list_usd"], [*e, "om_cost_per_answer", "pooled", "list_usd"]
        _same(G(S, "fa2", *hx_p), G(S, "s1b", "descriptive", "arms", arm, "pooled", "cost_per_answer"),
              f"free analysis 2 Haiku-max cost at {n} steps")
        _same(G(S, "fa2", *om_p), G(S, "s1b", "descriptive", "arms", f"om@{n}", "pooled", "cost_per_answer"),
              f"free analysis 2 Opus-medium cost at {n} steps")
        _same(G(S, "fa2", *em, "om_over_hx_cost_ratio"), _f(G(S, "fa2", *om_p)) / _f(G(S, "fa2", *hx_p)),
              f"free analysis 2 cost ratio at {n} steps")
        if G(S, "fa2", *em, "k") != min(math.floor(G(S, "fa2", *em, "om_over_hx_cost_ratio")), G(S, "fa2", *em, "held_to_tries")):
            raise ValueError(f"free analysis 2 k at {n} steps: not the floor of the cost ratio held to the tries drawn")
        _same(G(S, "fa2", *em, "vote_cost_per_answer_pooled"), G(S, "fa2", *em, "k") * _f(G(S, "fa2", *hx_p)),
              f"free analysis 2 vote cost at {n} steps: not k tries")
        tier = "post\u00a0hoc (free analysis\u00a02), not a test"                    # tied: no break inside "post hoc" or before the "2"
        if n == int(G(S, "s1b", "completeness", "B3", "N")):
            if G(S, "fa2", *em, "k") != G(S, "s1b", "costs_beside_tests", "B3", "k_measured"):
                raise ValueError("free analysis 2's k at the B3 length differs from the k measured beside Test B3")
            tier += "; the same k as measured beside Test B3"
        spend = derive("vote list cost per answer at k / Opus-medium list cost per answer (pooled)", lambda v, c: v / c,
                       R(S, "fa2", *em, "vote_cost_per_answer_pooled"), R(S, "fa2", *om_p))
        krows.append([L("Study 1b"), integer(R(S, "s1b", "descriptive", "arms", arm, "N")), L("Haiku-max"), L("Opus-medium"),
                      L("pooled"), integer(R(S, "fa2", *em, "k")), EMPTY, integer(R(S, "fa2", *em, "held_to_tries")), EMPTY,
                      num(R(S, "fa2", *em, "om_over_hx_cost_ratio"), dp=2), num_d(spend, dp=3), L(tier)])

    # ---- panel 2: Haiku-max against Opus-medium by length and shape
    lcols = ["Study", "Steps", "Shape", "Haiku-max mean output tokens per call (post\u00a0hoc)",
             "Opus-medium mean output tokens per call (Study 1: pre-specified; Study 1b: post\u00a0hoc)",
             "Output-token ratio, Haiku-max / Opus-medium (post\u00a0hoc)", "Haiku-max list cost per answer ($)",
             "Opus-medium list cost per answer ($)", "List-cost ratio, Haiku-max / Opus-medium", "Ratio source"]
    lrows: List[List[Cell]] = []
    fa10_src = L("free analysis\u00a010 (post\u00a0hoc)")           # "post hoc" and "analysis 10" never break (Edith, proof 4, p. 113)
    for sh in S1_SHAPES:
        hx_t = R(S, "fa10", *FA10_S1, f"haiku-max {sh}", "mean_output_tokens")
        om_t = R(S, "main", *ITEM, "item_9g", sh, "comparators", "opus-med", "mean_output_tokens")
        _same(om_t.value, G(S, "fa10", *FA10_S1, f"opus-med {sh}", "mean_output_tokens"), f"opus-med {sh}: output tokens")
        hx_c = R(S, "main", *ITEM, "item_24", "table", f"haiku-max {sh}", "cost_per_puzzle", "mean")
        om_c = R(S, "main", *ITEM, "item_24", "table", f"opus-med {sh}", "cost_per_puzzle", "mean")
        lrows.append([L("Study 1"), steps1, shp(sh), tk(hx_t, 1), tk(om_t, 1),
                      ratio(_hx_ratio_ref(S, "study1", s1n, sh, "output_tokens", hx_t, om_t), dp=2), usd(hx_c), usd(om_c),
                      ratio(_hx_ratio_ref(S, "study1", s1n, sh, "list_cost_per_call", hx_c, om_c), dp=3), fa10_src])
    for n, stamped in (("6", ("B3", "recorded beside Test B3")), ("12", None), ("16", ("B1", "recorded beside Test B1"))):
        hx_a, om_a = ["descriptive", "arms", f"hx@{n}"], ["descriptive", "arms", f"om@{n}"]
        steps_cell = integer(R(S, "s1b", *hx_a, "N"))
        for sh in shapes_of(int(n)):
            fh, fo = _fa10_1b_block(S, f"hx@{n}", sh), _fa10_1b_block(S, f"om@{n}", sh)
            hx_t, om_t = R(S, "fa10", *fh, "mean_output_tokens"), R(S, "fa10", *fo, "mean_output_tokens")
            hx_c, om_c = R(S, "s1b", *hx_a, sh, "cost_per_answer"), R(S, "s1b", *om_a, sh, "cost_per_answer")
            lrows.append([L("Study 1b"), integer(R(S, "s1b", *hx_a, "N")), shp(sh), tk(hx_t, 1), tk(om_t, 1),
                          ratio(_hx_ratio_ref(S, "study1b", int(n), sh, "output_tokens", hx_t, om_t), dp=2), usd(hx_c), usd(om_c),
                          ratio(_hx_ratio_ref(S, "study1b", int(n), sh, "list_cost_per_call", hx_c, om_c), dp=3), fa10_src])
        hx = R(S, "s1b", *hx_a, "pooled", "cost_per_answer")
        om = R(S, "s1b", *om_a, "pooled", "cost_per_answer")
        if stamped is not None:
            rc = ratio(R(S, "s1b", "costs_beside_tests", stamped[0], "ratio_challenger_over_comparator"), dp=3)
            src = L(stamped[1])
        else:
            # Study 1b's file stamps no ratio at this length; free analysis 2 stamps the inverse (Opus-medium / Haiku-max), checked here
            _same(G(S, "fa2", "result", f"N={n}", "equal_money", "om_over_hx_cost_ratio"), _f(om.value) / _f(hx.value),
                  f"free analysis 2's inverse ratio at {n} steps")
            rc = num_d(derive("Haiku-max cost / Opus-medium cost", lambda a, b: a / b, hx, om), dp=3)
            src = L("computed from the two recorded costs (post\u00a0hoc arithmetic); free analysis\u00a02 gives the inverse ratio "
                    "(post\u00a0hoc; Panel 1)")
        lrows.append([L("Study 1b"), steps_cell, L("pooled"), EMPTY, EMPTY, EMPTY, usd(hx), usd(om), rc, src])
    # ---- panel 3: the trial round
    tcols = ["Steps", "Setting", "Calls", "Input tokens", "Output tokens", "Mean output tokens per call", "List cost, all calls ($)"]
    trows: List[List[Cell]] = []
    # The printed step count is the stamped `steps` of the limit the trial round set for that arm (plan_as_run.limits, the trial round's
    # wave 0); the set id is used only to find that limit, and the match must be one to one with the same call count.
    entries = []
    used_limits: set = set()
    for key in S.keys("s1b", "trial_round.by_set_and_tag"):
        set_id, tag = key.rsplit(" ", 1)
        n_from_id = int(set_id.split("l14n")[1].split("-")[0])
        li = _limit_index(S, tag, n_from_id)
        if li is None or li in used_limits:
            raise ValueError(f"trial round {key}: no limit of its own in plan_as_run.limits")
        used_limits.add(li)
        if G(S, "s1b", "plan_as_run", "limits", li, "wave0_calls") != G(S, "s1b", "trial_round", "by_set_and_tag", key, "calls"):
            raise ValueError(f"trial round {key}: call count differs from its limit's wave-0 calls")
        name, model, effort = STUDY1B_TAGS[tag]
        entries.append(((n_from_id, MODEL_ORDER.index(model), EFFORT_ORDER.index(effort)), key, li, name))
    if len(used_limits) != len(S.get("s1b", "plan_as_run.limits")):
        raise ValueError("the trial round's entries and the stamped limits do not match one to one")
    for _, key, li, name in sorted(entries):
        tb = ["trial_round", "by_set_and_tag", key]
        out = R(S, "s1b", *tb, "output_tokens")
        calls = R(S, "s1b", *tb, "calls")
        trows.append([integer(R(S, "s1b", "plan_as_run", "limits", li, "steps")), setting_label(name), integer(calls),
                      integer(R(S, "s1b", *tb, "input_tokens")), integer(out),
                      thousands(num_d(derive("output tokens / calls", lambda o, c: o / c, out, calls), dp=1)), usd(R(S, "s1b", *tb, "list_usd"))])
    # ---- panel 4: the other Study 1b arms (6 steps and 12 steps), free analysis 10
    ocols = ["Steps", "Setting", "Shape", "Calls (usage records)", "Mean input tokens per call", "Mean output tokens per call",
             "Mean thinking tokens per call (API count)", "Thinking share of output tokens (%, API count)",
             "Thinking share of list cost (%, API count)"]
    orows: List[List[Cell]] = []
    others = sorted((a for a in fa10_arms if not a.endswith("@16")), key=lambda a: (int(a.split("@")[1]), arm_order(a)))
    for arm in others:
        n = int(G(S, "s1b", "descriptive", "arms", arm, "N"))
        if sorted(fa10_arms[arm]) != sorted(shapes_of(n)):
            raise ValueError(f"free analysis 10 {arm}: shapes {fa10_arms[arm]}")
        for sh in shapes_of(n):
            f10 = _fa10_1b_block(S, arm, sh)
            orows.append([integer(R(S, "s1b", "descriptive", "arms", arm, "N")), setting_label(tag_name(arm.split("@")[0])), shp(sh),
                          integer(R(S, "s1b", "descriptive", "arms", arm, sh, "final")), tk(R(S, "fa10", *f10, "mean_input_tokens"), 1),
                          tk(R(S, "fa10", *f10, "mean_output_tokens"), 1), *_api_cells(S, f10)])

    tconst = fold_constants(tcols, trows, ["Calls"])          # polish §7.3: the trial round made the same number of calls for every setting
    # the panels, in this order (Panels 1 to 4; the notes and the caption's panels fact name them so): the notes of the whole table print
    # under the last one, so the last is the short trial-round panel
    # (a float, which carries them), and the 36-row panel of the other settings comes before it
    panels = [("Cost-matched k", Table([L(c) for c in kcols], krows)),
              ("Haiku-max against Opus-medium by length and shape (output tokens and list cost per answer)", Table([L(c) for c in lcols], lrows)),
              ("Token structure of the other Study 1b settings (6 steps and 12 steps; post hoc, thinking tokens as the API reports them)",
               Table([L(c) for c in ocols], orows)),
              ("Trial round (Study 1b): tokens and list cost by setting", Table([L(c) for c in tcols], trows, [
                  note("Columns that print one value in every row are left out: every setting made",
                       joined(tconst["Calls"], L("calls in the trial round."), sep=" "))]))]
    n19 = [*ITEM, "item_19", "arms"]
    off = [*FA10_S1, "haiku-thinking-off"]
    words = _fa10_words(S)
    unit_1b = R(S, "s1b", "costs_beside_tests", "B1", "challenger", "unit")
    for t in TESTS_1B:                       # every Study 1b cost block this table reads states the same unit
        for side in ("challenger", "comparator"):
            u = str(G(S, "s1b", "costs_beside_tests", t, side, "unit"))
            if not u.startswith(str(unit_1b.value)):
                raise ValueError(f"costs_beside_tests.{t}.{side}: unit {u!r} differs")
    # one price note for both versions: no version names a pre-registration item (TAB-16 is a main-text table; Edith's Q22)
    price_note = note("Price basis: list price per answer. Study 1: the pre-registered price table, dated",
                      joined(text_of(R(S, "main", *ITEM, "item_9a", "price_table_date")), L("."), sep=""),
                      "Study 1b: its file gives the unit as", text_of(unit_1b, UNIT_WORDS), "and no price-table date.")
    api_note = note("Columns marked API count are counted from the usage records by free analysis 10, labelled \"" + words + "\". They "
                    "are post hoc and have no interval. The thinking share of list cost is the thinking tokens priced at the model's list "
                    "output rate, summed over the calls, divided by the summed list cost.")
    empty_note = note("Cells left empty are not given in the result files; a dash means the column does not apply.")
    # Study 1's costs per answer and per correct answer, token means and thinking estimates are its reporting definitions, fixed after
    # Lock 3 and before any result was opened: "pre-specified", never "pre-registered" (the style sheet; TAB-03's note says the same)
    defs_ev = _defs_fixed(S)
    notes = [
        price_note + [L("The Batch cost we paid is given where the files give it and is empty otherwise.")],
        api_note,
        note(with_evidence("Calls are the pre-specified counts: for Study 1 those recorded with its pre-specified thinking estimates, for "
                           "Study 1b the Study 1b file's final count; free analysis 10 counts the same calls (checked when the table is "
                           "built).", defs_ev)),
        note(with_evidence("Mean input and output tokens per answer are Study 1's pre-specified token means only for its Haiku-medium, "
                           "Opus-medium and Sonnet-medium rows and its votes.", defs_ev),
             "Every other row's, including every Study 1b row's, are free analysis 10's (post hoc). Where both files hold a value they "
             "are equal (checked when the table is built)."),
        note(*_thinking_estimate(S, defs_ev),
             "They are biased: Haiku, thinking off gets",
             joined(P(R(S, "main", *n19, "haiku-thinking-off:1x6", "share_of_list_cost"), 2, prop=True), L("%"), sep=""), "/",
             joined(P(R(S, "main", *n19, "haiku-thinking-off:6x1", "share_of_list_cost"), 2, prop=True), L("%"), sep=""),
             "of its list cost as estimated thinking (chains / pieces), while the API counts a mean of",
             num(R(S, "fa10", *FA10_S1, "haiku-thinking-off 1x6", "mean_thinking_tokens"), dp=1), "/",
             num(R(S, "fa10", *FA10_S1, "haiku-thinking-off 6x1", "mean_thinking_tokens"), dp=1),
             "thinking tokens per call for it. The estimate stays as defined; the API columns are the thinking figures to read."),
        note("Study 1b rows: format compliance is given per shape only (the files give none for a pooled row). A pooled row's calls are the "
             "Study 1b file's pooled count; free analysis 10 gives tokens per shape only, so the pooled rows' token cells are empty.",
             with_evidence("Study 1's pre-specified thinking estimates do not apply to Study 1b (dash; the part of the table that gives "
                           "Study 1b's token columns leaves those two columns out).", defs_ev)),
        note("Cost ratio is the setting's list cost per answer divided by Opus-medium's on the same shape. For Haiku-max per shape "
             "it is free analysis 10's ratio (post hoc; checked against the two recorded costs); for Study 1b's pooled Haiku-max row and the "
             "pooled Haiku-max vote it is the ratio recorded beside Tests B1 and B2; elsewhere it is computed from the two recorded costs "
             "(post hoc arithmetic)."),
        note("Spend share of a vote: the vote's spend over its cost-matched comparator's. For the Study 1 votes it is the pre-registered k "
             "file's, in Batch dollars; for the pooled Study 1b vote it is the ratio recorded beside Test B2, at list price. The Study 1b "
             "file gives it for the pooled vote only, so its per-shape cells are the same quotient from the two recorded costs (post hoc "
             "arithmetic). A capped k is held to the samples drawn, below its "
             "cost-matched k; its Setting cell gives both."),
        note("A vote at k costs k answers; its cost per correct answer and accuracy are those of the vote.",
             with_evidence("A Study 1 vote's Batch cost per answer is its spend in the pre-registered k file (k samples at the "
                           "pre-specified Batch cost per sample; checked). A Study 1 vote's tokens per answer are those of its k samples "
                           "together (pre-specified); the Study 1b vote's are not given.", defs_ev),
             "Calls and thinking figures are not given for a vote (dash): it reuses its single samples, which are counted in their own "
             "rows. The format compliance shown for a vote is that of its single samples."),
        empty_note,
        note("The vote at the cost-matched k follows the pre-registered k rule of each study. In Panel 1, each shape's own "
             "cost-matched k at 16 steps is post hoc (free analysis 3), and so is the cost-matched k at 6 steps and at 12 steps (free "
             "analysis 2: its k, the samples it is held to and its samples per comparator answer; the spend share is its vote cost over "
             "Opus-medium's, post hoc arithmetic). "
             "Neither changes a test, and no trend across lengths is read from them."),
        note("Panel 2: per shape, the output-token and list-cost ratios are free analysis 10's ratios (post hoc); Study 1's "
             "Opus-medium tokens and both studies' costs are the pre-specified recorded values. The pooled rows give the list costs per "
             "answer and the ratio recorded beside Tests B3 and B1. At 12 steps the Study 1b file gives no ratio, so it is computed from the "
             "two recorded costs (post hoc arithmetic); free analysis 2 gives its inverse (post hoc, Panel 1). No pooled "
             "output-token ratio is given."),
        note("Panel 3: the Study 1b settings at 6 steps and 12 steps, with token figures counted by free analysis 10 (post hoc) "
             "and calls from the Study 1b file; the 16-step settings are in the main table. Panel 4: the trial round ran on "
             "separate sets; its step counts are those of the limits it set, and its list cost is the total over all of a setting's "
             "calls, not per answer."),
    ]
    caption = {
        "tier": [with_evidence("pre-specified descriptive (Study 1's pre-registered settings table, vote curve and price table, and its "
                               "pre-specified costs per answer and per correct answer, token means and thinking estimates; Study 1b's "
                               "effort sweep and the costs recorded beside its tests; the pre-registered k files); the two "
                               "thinking-estimate columns are biased estimates; post hoc: the API-count columns, the token means outside "
                               "Study 1's pre-specified ones and the per-shape Haiku-max / Opus-medium ratios (free analysis 10, labelled "
                               "\"" + words + "\"), the cost ratios and spend shares computed from two recorded costs (post hoc arithmetic), "
                               "each shape's own cost-matched k at 16 steps (free analysis 3) and the cost-matched k at 6 steps and at 12 "
                               "steps (free analysis 2)", defs_ev)],
        "study": [L("Study 1 (main run,"), integer(R(S, "main", "n")), L("steps) and Study 1b (effort sweep,"),
                  integer(R(S, "s1b", "descriptive", "arms", "hx@16", "N")), L("steps; Haiku-max and Opus-medium also at"),
                  integer(R(S, "s1b", "descriptive", "arms", "hx@6", "N")), L("and"), integer(R(S, "s1b", "descriptive", "arms", "hx@12", "N")),
                  L("steps, and the other effort-sweep settings at"), integer(R(S, "s1b", "descriptive", "arms", "hh@6", "N")),
                  L("steps, in Panels 2 and 3)")],
        "set": [L("Study 1 main set; Study 1b's set for Tests B1 and B2 (16 steps), with its set for Test B3 (6 steps) and its 12-step set "
                  "in Panels 2 and 3; the trial round (Panel 4) ran on separate sets")],
        # the panels in their printed order, so a caption that names them follows it (Edith, proof 3, p. 108: a caption put the token
        # structure fourth and the trial round third)
        # Panel 1 also holds Study 1's pre-registered votes (at 6 steps), so "post hoc" is pinned to the rows that are: each shape's own k at 16
        # steps (free analysis 3) and Study 1b's k at 6 and 12 steps (free analysis 2), as the note and the tier fact say (Edith's checker, p. 108)
        "panels": [L("Panel 1: the cost-matched k of each vote (the pre-registered rule; post hoc for each shape's own k at"),
                   integer(R(S, "s1b", "descriptive", "arms", "hx@16", "N")), L("steps and for Study 1b's k at"),
                   integer(R(S, "s1b", "descriptive", "arms", "hx@6", "N")), L("and"),
                   integer(R(S, "s1b", "descriptive", "arms", "hx@12", "N")),
                   L("steps); Panel 2: Haiku-max against Opus-medium by length and shape (output tokens and list cost per "
                     "answer); Panel 3: the token structure of the other Study 1b settings at"),
                   integer(R(S, "s1b", "descriptive", "arms", "hh@6", "N")), L("and"),
                   integer(R(S, "s1b", "descriptive", "arms", "hx@12", "N")),
                   L("steps; Panel 4: the trial round's tokens and list cost by setting")],
        "n": [L("puzzles:"), integer(R(S, "main", *ITEM, "item_24", "table", "opus-med 1x6", "base_puzzles")), L("(Study 1);"),
              integer(R(S, "s1b", "descriptive", "arms", "hx@16", "pooled", "n_base")), L("(Study 1b, 16 steps); calls per setting and shape "
              "in the Calls columns (one call is one sample)")],
        "interval": [L("none (point values; API counts have no interval; intervals are in the Study 1 settings table and the effort-sweep table)")],
        "price": [L("list price per answer; Study 1: the pre-registered price table, dated"),
                  joined(text_of(R(S, "main", *ITEM, "item_9a", "price_table_date")), L(";"), sep=""), L("Study 1b:"),
                  text_of(unit_1b, UNIT_WORDS), L("as its file gives it, with no price-table date")]}
    t = Table([L(c) for c in cols], rows, notes, caption)
    t.panels = panels
    t.main_table = _tab16_paper(S, caption, defs_ev, words)
    # the supplement's layouts (batch g). The full table (20 columns, 43 rows with long headers) splits in two column sets (accuracy and
    # costs; tokens and thinking) and, for each, two row blocks (Study 1's rows, then Study 1b's), sideways at footnotesize; the key
    # (study, steps, setting, shape) repeats. The notes of the whole table (thirteen, about five inches) print under the last panel, so
    # that is the short trial-round panel; a long table is never set after floats (they would be placed behind it).
    heads = [c.printed for c in t.columns]
    n_s1 = [r[0].printed for r in rows].count("Study 1")
    if [r[0].printed for r in rows[:n_s1]] != ["Study 1"] * n_s1 or any(r[0].printed != "Study 1b" for r in rows[n_s1:]):
        raise ValueError("TAB-16's rows are not Study 1's, then Study 1b's")
    block_1, block_1b = list(range(n_s1)), list(range(n_s1, len(rows)))
    money = heads[4:12]                                   # accuracy, format compliance, the four costs, the two ratios
    tokens_ = heads[12:]                                  # calls, token means, thinking counts and estimates
    # Study 1b's rows leave out the two estimate columns that are dashes for them (batch g check). Their token columns were once split
    # by rows in two, because with the long headers they were taller than a sideways page (6.7 in against 6.5) and each half left its page
    # 40% and 51% filled (Edith, proof 3, pp. 111-112); with the qualifiers of the token headers in the note, one part fits its page
    split(t, True, [(block_1, money), (block_1b, money), (block_1, tokens_), (block_1b, tokens_[:-EST_DASH])],
          key=("Study", "Steps", "Setting", "Shape"))
    t.font = "footnotesize"
    # a study's model families, its votes apart (polish §7.7); a group for every setting would leave part 2 almost no spare height
    t.groups = starts(rows, lambda r: (r[0].printed, family([r[2]]), "vote" in r[2].printed))
    k_p, hx_p, other_p, trial_p = (tab for _, tab in t.panels)
    k_p.layout = "landscape"
    k_p.groups = starts(krows, lambda r: (r[0].printed, "fa3" if "free analysis 3" in r[-1].printed.replace(NBSP, " ") else
                                          "fa2" if "free analysis 2" in r[-1].printed.replace(NBSP, " ") else "pre"))
    hx_p.layout = "landscape"
    hx_p.groups = starts(lrows, lambda r: (r[0].printed, r[1].printed))
    trial_p.layout = "float"
    trial_p.groups = starts(trows, lambda r: r[0].printed)
    other_p.layout, other_p.font = "float", "footnotesize"          # nine columns with one-decimal token means and two-decimal shares
    other_p.groups = starts(orows, lambda r: (r[0].printed, re.match(r"[A-Za-z]+", r[1].printed).group(0)))     # a model's settings
    return print_rules(t)


# TAB-16's paper version (Vision's plan §3): the settings the text discusses, as (Study 1 arm, Study 1b tag), in the full table's order
TAB16_PAPER = (("haiku-med", "hm"), ("haiku-max", "hx"), ("sonnet-med", "sm"), ("opus-med", "om"))


def _tab16_paper(S: Store, caption: Dict[str, List[Cell]], defs_ev: List[Cell], words: str) -> Table:
    """The paper's version of TAB-16 (Vision's plan §3; D-161): Haiku-medium, Haiku-max, Sonnet-medium and Opus-medium at 6 steps (Study
    1's rows) and at 16 steps (Study 1b's rows; a setting with no 16-step row in Study 1b shows 6 steps only), one row per setting and
    length: list cost per answer, mean output tokens per answer and the API's thinking share of list cost, each as 'chains / pieces' (the
    files give Study 1 per shape only, and Study 1b's pooled rows no tokens). Every value is the full table's cell, from the same ref (the
    thinking share at one decimal; tokens with comma thousands). Its caption facts are the full table's for what it shows, in the paper's
    words, and name the rows whose token means are post hoc (free analysis 10's), read from the cells' own sources."""
    s1n = R(S, "main", "n")
    arms = set(S.keys("s1b", "descriptive.arms"))
    n16 = R(S, "s1b", "descriptive", "arms", "hx@16", "N")
    rows6: List[List[Cell]] = []
    rows16: List[List[Cell]] = []
    post6: List[str] = []                                  # the 6-step settings whose token means are free analysis 10's (post hoc)
    pre6: List[str] = []                                   # those whose token means are Study 1's pre-specified ones
    for arm, tag in TAB16_PAPER:
        if STUDY1_ARMS[arm][0] != tag_name(tag):
            raise ValueError(f"{arm} and {tag} are not one setting")
        # Study 1, 6 steps (the full table's single-call rows)
        cost, tok, share = [], [], []
        for sh in S1_SHAPES:
            if shape_word(sh) != ("chain", "pieces")[len(cost)]:
                raise ValueError(f"Study 1's shapes are not chain then pieces: {S1_SHAPES}")
            cost.append(usd(R(S, "main", *ITEM, "item_24", "table", f"{arm} {sh}", "cost_per_puzzle", "mean")))
            tok.append(tokens(_s1_tokens(S, arm, sh)[1]))
            share.append(P(R(S, "fa10", *FA10_S1, f"{arm} {sh}", "thinking_share_of_list_cost"), 1, prop=True))
        src = {r.source for c in tok for r in c.refs}
        if src not in ({"main"}, {"fa10"}):
            raise ValueError(f"{arm}: its two token means come from {sorted(src)}, not from one file")
        (pre6 if src == {"main"} else post6).append(STUDY1_ARMS[arm][0])
        rows6.append([L(STUDY1_ARMS[arm][0]), integer(s1n), pair(*cost), pair(*tok), pair(*share)])
        # Study 1b, 16 steps (the effort sweep's rows), where the setting ran at 16 steps
        a = f"{tag}@{int(n16.value)}"
        if a not in arms:
            continue
        cost, tok, share = [], [], []
        for sh in shapes_of(int(n16.value)):
            f10 = _fa10_1b_block(S, a, sh)
            cost.append(usd(R(S, "s1b", "descriptive", "arms", a, sh, "cost_per_answer")))
            tok.append(tokens(R(S, "fa10", *f10, "mean_output_tokens")))
            share.append(P(R(S, "fa10", *f10, "thinking_share_of_list_cost"), 1, prop=True))
        rows16.append([L(tag_name(tag)), integer(R(S, "s1b", "descriptive", "arms", a, "N")), pair(*cost), pair(*tok), pair(*share)])
    if not pre6 or not post6:
        raise ValueError("TAB-16's paper caption names both pre-specified and post hoc token means at 6 steps")
    # the notes, two lines together (polish §7.5): which study each row is, how a cell reads, and the thinking share's definition; the
    # token means' unit ("per answer") is in the header
    notes = [note("Rows at", integer(s1n), "steps are Study 1's settings, rows at", integer(n16), "steps Study 1b's; each cell is chain / "
                  "pieces."),
             note("Thinking share of list cost: the thinking tokens the API reports, priced at the model's list output rate and summed over "
                  "calls, over the summed list cost.")]
    # the full table's caption facts for what this version shows, in the paper's words (D-161): its price fact is the full table's, its
    # study and set facts are the full table's narrowed to its rows (no side panel), its puzzle count names no column it does not have,
    # and its tier names the post hoc token means by row
    for k, starts in (("n", "puzzles:"), ("interval", "none (point values; API counts have no interval")):
        if not caption[k][0].printed.startswith(starts):
            raise ValueError(f"TAB-16's caption fact {k!r} changed; the paper version's words no longer follow it")
    pcap = {
        "tier": [with_evidence("pre-specified descriptive (Study 1's pre-specified costs per answer at its pre-registered price table, and "
                               "its token means for " + _and_list(pre6) + "; Study 1b's effort sweep); post hoc: the thinking shares, "
                               "and the token means for " + _and_list(post6) + " at", defs_ev), integer(s1n),
                 L("steps and for every row at"), integer(n16),
                 L("steps (labelled \"" + words + "\")")],
        "study": [L("Study 1 (main run,"), integer(s1n), L("steps) and Study 1b (effort sweep,"), integer(n16), L("steps)")],
        "set": [L("Study 1 main set; Study 1b's set for Tests B1 and B2 (16 steps)")],
        "n": [L("puzzles:"), *caption["n"][1:4], L("(Study 1b, 16 steps), each in both shapes")],
        "interval": [L("none (point values; API counts have no interval)")],
        "price": caption["price"]}
    return paper_table(["Setting", "Steps", "List cost per answer ($)", "Mean output tokens per answer",
                        "Thinking share of list cost (%)"],
                       rows6 + rows16, notes, pcap, groups=[len(rows6)])
