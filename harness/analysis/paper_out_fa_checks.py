"""The free-analysis check tables (post hoc, D-131): TAB-26, the exact intervals where a bootstrap collapsed (free analysis 4, `fa4`,
revision 3), and TAB-27, Tests 1-4 under a multiplicity correction (free analysis 5, `fa5`, E-19). Every cell is read from the pinned
files by key; see paper_out_core.py for the rules.

TAB-26 prints every fa4 cell the paper reports: item 20's (the FIG-02 bars whose bootstrap interval collapsed, counted against all of
FIG-02's bars) in a compact panel, the others in the main table. Revision 3's nine 90% exact intervals for the fairness check's
misapplied-rule rates were computed beyond the approved scope (Edith's ruling, record section 15; the user has not decided): they are
checked and counted in the scope note, never printed as rows, and the build refuses while another output could print them (it names
the rates or an exact 90% interval, calls core.fa4_exact with a field other than a row field, or reads an exact interval at a level it
does not spell out). The scope note's word "unchanged" for revision 2's cells rests on fa4's own stamped account and check (the build refuses without them); the full
comparison would need fa4r2.json, which is not one of the paper's pinned sources. Per cell: its
stamped description (a cell of the first version) or its family (a cell added by rule, checked to be that family, field and key), its
study or run (fa4's stamped source path, printed through SOURCE_NAMES, or PILOT1_NAMES for a Pilot 1 marker the length-sweep files
carry, so run ids stay in the provenance fields), its key (fa4 writes plain dotted paths; printed in the ledger's syntax, with the
interval's field name where it is not ci95), the collapsed interval from the original pinned source at that key and field (checked equal
to fa4's own copy, and found by core.fa4_exact), the stamped interval's own tier (its source's label, or, where the source stamps none,
the plan's tier for the output that reports it), the tries per base puzzle from that source (a vote: its k), and the puzzles right out
of the cell's puzzles and the exact interval from fa4 (checked to be the closed-form Clopper–Pearson interval for all right or all
wrong, at the cell's own level). A
collapsed interval that is a paired difference (the keep-list C10 rows: the stamped object holds `d` and `accuracy_means`) goes in its
own column, in points, and the accuracy column is a dash, so every column holds one quantity. The scope notes recount EVERY two-number
stamped field in every file fa4's scan read, under any field name (as the scan does), and check that the cells, the fa4-listed
exclusions and the unreported nine account for each file and field exactly as result.scan.zero_width_by_field says, and that the
scan's field counts and its one non-interval field (quartiles) are what the recount finds; the counts and reasons printed are fa4's own
(a reason without its file tag, the study being printed beside it; the scan's field-name rule in words, the stamped rule checked to be
the one the words describe).
TAB-27 reads d, the unadjusted 95% interval, the error-rate ratio, the reading under the pre-registered decision rule and the locked
one-sided p from the main analysis, and the inferiority p, the Holm thresholds, the Holm reading and the stricter interval from fa5.
Test 5 is in the Holm family as its fifth member only: its confirmatory result is its Holm-adjusted result in the pre-registered
family of one-sided tests, given in a note from the stamped keys; its inferiority-reading cells are dashes. Every reading is printed in
the paper's words (READING_WORDS: the stamped "non-inferior" is "shown no worse by > margin (Holm-adjusted)", checked against the test's
own `declared` flag; the stamped label stays the cell's raw value). The Holm column is headed by what it holds, the inferiority p below
its Holm threshold (checked against fa5's Holm reading and Holm's step-down order), not in test words.
D-161 and batch (g): the supplement's layouts (TAB-26: a sideways split in four row chunks and two column groups, every part repeating
the description and the stamped key, rows grouped by family, its item 20 panel a long table; TAB-27: two sideways parts), the retired
words swapped (a stamped name, such as a row's description, in the paper's word, its
stamped text kept as the cell's raw value; a stamped key or sentence that holds a retired word printed as stamped, in quotation marks).
Typed sentences are guarded: each is printed only while the stamped values say what it says (Test 3's lines, Test 5's result,
the scope, unreported, left-out and scan lines, the length-sweep (against fa4's own q note and its reason for leaving q out, both cited
in the sentence's provenance), key-legend, item 9e (against the stamped block's base counts and rule, and the reporting definitions'
item 9e section), item 20 panel and exact-method lines, the C10 direction, the tiers (the Pilot 1 markers' from the plan's length-sweep
table), the Pilot 1 study names, the near-ceiling label, the error-rate ratio's tier (Study 1's reporting definitions)).
"""
from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, localcontext
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .paper_out_core import (Cell, KeyMissing, Ref, Source, Store, Table, YES_NO, ci_refs, derive, exact, fa4_exact, format_key,
                             integer, interval, is_num, join_key, joined, label, num, num_d, output, parse_key, pct, pts, pvalue, pvalue_bound,
                             register_source, text_of)
from .paper_out_lint import karen_vocab, vocabulary_texts
from .paper_out_names import STUDY1B_TAGS, STUDY1_ARMS, STUDY1_TESTS, challenger_name, shape, shape_word

DASH = label("—")
VIEW = "confirmatory.views.as_deployed"
FA4 = "result.cells"
FA5 = "result.tests"
# fa4 stamps each cell's unit; a share (0-1) is printed in % (x 100), a value in points as stamped.
UNIT_SCALE = {"points": 1.0, "share (0-1)": 100.0}
TEST_NAMES = {t: v[0] for t, v in STUDY1_TESTS.items()}
# The study or run of each pinned source fa4 names, printed in place of its repo path (the path, which holds run ids, stays in the
# cell's provenance: the cell is fa4's stamped path through this mapping).
SOURCE_NAMES = {"main": "Study 1, main run", "groupc": "Study 1, keep-list analyses", "s1b": "Study 1b", "topup": "Top-up run",
                "curve_d90": "Length sweep, scored under Deviation 2", "curve": "Length sweep, original marking rule",
                "fa2": "Study 1b's samples, free analysis 2 (post hoc)"}
# A Pilot 1 marker (key pilot1.<tag>.<name>) is a Pilot 1 result the length-sweep files carry beside the sweep (checked by its stamped
# label): its study is Pilot 1, printed with the file that carries it.
PILOT1_NAMES = {"curve": "Pilot 1, carried beside the length sweep (in its original-rule file)",
                "curve_d90": "Pilot 1, carried beside the length sweep (in its Deviation 2 file)"}
# The paper's plain names where the shared display name carries an internal arm code (the names TAB-02 prints).
PLAIN_NAME = {"e3": "Step voting"}
# Top-up comparators that are a main-run arm, rebuilt in the top-up file from the main run's log: top-up tag -> main-run arm.
TOPUP_MAIN_ARMS = {"main-om": "opus-med"}
ITEM7_ARMS = "reporting.group_b.item_7.per_piece_accuracy.arms"         # item 7 stamps each main-run arm's designed tries per puzzle


# D-161's one name per term, for the paper's versions of tables (Table.main_table; batch (f)): a header, cell or note of a paper version
# prints none of the retired words (try, arm, base puzzle, equal-money, same-model, tier, three-way reading, run window, as deployed,
# setup) or the locked ones ("non-inferior", "declared", "significant"). The caption is the full table's facts, from which Vision writes.
PAPER_BARRED = re.compile(r"(?i)non-inferior|\bdeclared\b|\bsignifican|\btr(?:y|ies)\b|\barms?\b|base puzzles?|equal-money|same-model"
                          r"|\btiers?\b|three-way|run window|as deployed|\bsetups?\b")


def check_paper_words(t: Table, oid: str) -> Table:
    """A paper version's house rules that the builder can check alone: at most 8 columns, at most 2 notes and every one printed as a
    short note, and no retired or locked word (PAPER_BARRED) in its headers, cells or notes."""
    if len(t.columns) > 8:
        raise ValueError(f"{oid}'s paper version has {len(t.columns)} columns (at most 8)")
    if len(t.notes) > 2 or sorted(t.short_notes) != list(range(len(t.notes))):
        raise ValueError(f"{oid}'s paper version prints only short notes, at most 2 ({len(t.notes)} notes, short {t.short_notes})")
    texts = [c.printed for c in t.columns] + [c.printed for r in t.rows for c in r] + [c.printed for n in t.notes for c in n]
    bad = sorted({x for x in texts if PAPER_BARRED.search(x)})
    if bad:
        raise ValueError(f"{oid}'s paper version prints a retired or locked word (D-161): {bad}")
    return t


def _glue(*parts: Cell) -> Cell:
    """Cells printed with no space between them (a number and its trailing punctuation)."""
    return joined(*parts, sep="")


# D-161's plain swaps for a stamped NAME that a row prints (free analysis 4's description or family of a cell): the stamped text stays the
# cell's raw value and source, and only the retired words change (a note says so). A stamped key and a stamped sentence are never
# reworded: they are printed as stamped, in quotation marks (_quoted).
PLAIN_SWAPS = ((re.compile(r"\ban arm\b"), "a setting"), (re.compile(r"\barms\b"), "settings"), (re.compile(r"\barm\b"), "setting"),
               (re.compile(r"\bbase puzzles\b"), "puzzles"), (re.compile(r"\bbase puzzle\b"), "puzzle"),
               (re.compile(r"\b(\d+)-try\b"), r"\1-sample"), (re.compile(r"\btries\b"), "samples"),
               (re.compile(r"\bequal-money\b"), "cost-matched"),
               # one name per setting (Edith C.31): the tables write Haiku with thinking off as "Haiku, thinking off"
               (re.compile(r"\bHaiku thinking-off\b"), "Haiku, thinking off"),
               # one form for a vote (proof 4, p. 42): "10-sample vote" beside the "3-sample vote" of Study 1's rows
               (re.compile(r"\bvote@(\d+)\b"), r"\1-sample vote"))


DOUBLE_QUOTED = re.compile(r"\u201c[^\u201d]*\u201d|\"[^\"\n]*\"")


def _retired(text: str) -> bool:
    """Does the text hold a term D-161 retires (Karen's list), outside double quotation marks? (Not the lint's own mask, which also
    skips text between two apostrophes: "difference's [0, 0]; each arm's" is no quotation.)"""
    plain = DOUBLE_QUOTED.sub(" ", text)
    return any(rx.search(plain) for rx, _ in karen_vocab())


def _plain_name(r: Ref) -> Cell:
    """A stamped name printed in the paper's words (PLAIN_SWAPS); a name with no retired word is printed as stamped."""
    v = str(r.value)
    out = v
    for rx, to in PLAIN_SWAPS:
        out = rx.sub(to, out)
    if _retired(out):
        raise ValueError(f"{r.source}:{r.key} = {v!r} still holds a retired term after the plain swaps: {out!r}")
    return Cell(out[:1].upper() + out[1:], raw=r.value, refs=(r,))     # a row name starts with a capital (proof 4, p. 44)


SWEEP_FAMILY = re.compile(r"^(Length sweep \((?:original|Deviation 2) rule\)): per-step or whole-answer accuracy$")
SWEEP_MEASURE = {"per_step": "per-step", "whole_answer": "whole-answer"}
SWEEP_SHAPE = {"1xn": "chains", "nx1": "pieces", "pooled": "pooled"}


def _sweep_row_name(S: Store, r: "_Row", family: Cell) -> Cell:
    """A length-sweep row added by rule, named in full as the first version's rows are ("Length sweep Opus-medium per-step, 6 steps,
    pooled"; proof 4, p. 44: the rows of one family all carried one generic name): its family's name, which says the marking rule,
    then the model, the measure, the length and the shape that its key gives. The model is the key's tag checked against the file's
    stamped model and effort; the length is the key's name (by_n.<N>)."""
    segs = parse_key(r.key)
    m = SWEEP_FAMILY.match(family.printed)
    if not m or len(segs) != 6 or segs[:1] != ["models"] or segs[2] != "by_n" or not segs[3].isdigit() \
            or segs[4] not in SWEEP_MEASURE or segs[5] not in SWEEP_SHAPE:
        raise ValueError(f"fa4 cell {r.i}: {family.printed!r} / {r.key} is not a length-sweep by-length row of the form the full name reads")
    step = Ref(int(segs[3]), r.src, join_key(*segs[:4]))
    printed = f"{m.group(1)}, {_model_name(S, r.src, segs[1])} {SWEEP_MEASURE[segs[4]]}, {segs[3]} steps, {SWEEP_SHAPE[segs[5]]}"
    return Cell(printed, raw=family.raw, refs=family.refs + (step,),
                formula="the family's name, then the model (its tag, checked against the file's stamped model and effort), the measure, "
                        "the length (the key's name) and the shape, read from the row's key")


def _quoted(cell: Cell) -> Cell:
    """A stamped text that holds a word D-161 retires, printed as stamped in quotation marks (Edith's ruling: a frozen source is quoted,
    not reworded); the cell keeps its raw value and source."""
    return joined(label('"'), cell, label('"'), sep="")


def _source_name(S: Store, path: str) -> str:
    """The pinned source at the repo path fa4 names. The collapsed interval is re-read there (pinned commit, SHA-256 checked) and must
    equal fa4's own copy, so a row cannot print an interval its source file does not stamp."""
    names = [n for n, s in S.sources.items() if s.path == path]
    if len(names) != 1:
        raise KeyMissing(f"fa4 names {path!r}, which is not one pinned source ({names})")
    return names[0]


def _level_from_key(source: str, key: str) -> Cell:
    """The interval level named in a stamped key such as '...ci99', printed '99%' (fa5 stamps no separate level field)."""
    last = parse_key(key)[-1]
    m = re.fullmatch(r"ci(\d+)", last)
    if not m:
        raise ValueError(f"{key} does not name a level")
    return Cell(m.group(1) + "%", raw=last, refs=(Ref(last, source, format_key(parse_key(key))),),
                formula="digits of the interval key's name, then %")


def _caption(tier: List[Cell], study: str, set_: List[Cell], n: List[Cell], interval_cells: List[Cell],
             price: str) -> Dict[str, List[Cell]]:
    return {"tier": tier, "study": [label(study)], "set": set_, "n": n, "interval": interval_cells, "price": [label(price)]}


def _names_in(text: str, name: str) -> bool:
    """`name` appears in `text` as a whole name (not inside a longer arm name such as 'Opus-low' in 'Opus-lower')."""
    return re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text) is not None


def _and_list(cells: Sequence[Cell]) -> Cell:
    """'a', 'a and b', 'a, b and c' as one cell, keeping every part's refs."""
    if len(cells) == 1:
        return cells[0]
    return joined(joined(*cells[:-1], sep=", "), label("and"), cells[-1])


def _key_name(source: str, parent: str, name: str) -> Cell:
    """A step count the source stamps only as the NAME of a key (e.g. `models.om.by_n.12`): printed as that name, with the key as
    its provenance (the audit checks the printed text is the key's last segment)."""
    r = Ref(int(name), source, join_key(*parse_key(parent), name))
    return Cell(name, raw=int(name), refs=(r,), formula="the key name (steps)")


def _arm_name(arm: str) -> str:
    return PLAIN_NAME.get(arm, STUDY1_ARMS[arm][0])


def _challenger(test: str) -> str:
    """A test's challenger as TAB-02 names it: the Haiku-medium vote for Tests 1-3, else the arm's plain name."""
    ch = STUDY1_TESTS[test][1]
    return challenger_name(test) if ch == "haiku-med" else _arm_name(ch)


# ================================================================ TAB-26

R2, ADDED = "result.revision_2_cells", "result.added_cells"
I20 = ["reporting", "group_b", "item_20"]
FEW = "too few wrong tries"
# Item 20's agreement thirds in words (FIG-02's names, "too few wrong samples" for the stamped group "too few wrong tries", D-161); the
# order is checked against each puzzle's stamped agreement share.
THIRD_WORDS = {"t1": "lowest third", "t2": "middle third", "t3": "highest third", FEW: "too few wrong samples"}
# Where a source stamps no tier for a block, the plan's tier for the output that reports it: (source, block) -> (plan id, a fragment
# that plan entry's source_keys must name, the block in words).
PLAN_TIERS = {("main", "item_20"): ("FIG-02", "item_20", "item 20"), ("main", "item_24"): ("TAB-04", "item_24.table", "item 24's table"),
              ("s1b", "per_form"): ("TAB-11", "per_form", "Study 1b's per-test cells")}
CURVES = ("curve", "curve_d90")
# Study 1b's per_form.<test>.<shape>.<side>: the model of a side that is one arm (the test's other blocks are d and v).
PER_FORM_SIDE = {"o": "opus", "h": "haiku"}
# The result files whose rows TAB-26 prints, in the caption's words and order (checked against the rows).
SOURCE_ORDER = ("main", "groupc", "s1b", "fa2", "topup", "curve", "curve_d90")
CAPTION_SOURCES = set(SOURCE_ORDER)
PANEL = ("Item 20: the FIG-02 bars whose bootstrap interval collapsed (the Haiku-medium vote at its largest k, by single-sample "
         "accuracy bin and agreement third)")
# The interval fields whose cells are rows (or panel rows): ci95, the field of every cell of revision 2, and item 9e's
# opus_accuracy_ci95, the one field revision 3 added that the paper reports. Revision 3's other added field, ci90 (the fairness check's
# misapplied-rule rates, nine cells), was computed beyond the approved scope: it is checked and counted, never printed as a row.
ROW_FIELDS = ("ci95", "opus_accuracy_ci95")
UNREPORTED_FIELD = "ci90"
I9E = ["reporting", "group_b", "item_9e", "shapes"]
# The sentence in fa4's stamped account of revision 3 that the scope note's word "unchanged" (revision 2's cells) rests on, and the
# words of the stamped check that counts them: a changed account or check refuses the build.
FA4_KEEPS = "keeps revision 2's cells unchanged"
FA4_CHECK = "revision 2's cells"
# fa4's stamped rule for which two-number fields are intervals, and the same rule in words (what the Scan note prints, so a regular
# expression does not reach the paper); the rule is checked to be exactly this one when the note is built, and the words are held to the
# no-typed-number rule.
# n is samples per puzzle in the paper, so no x of n (proof 4). The header's pieces are tied so that a narrow column never leaves "the"
# alone on a line or splits "post / hoc)". In the sideways parts only "of the" is tied: the column is as wide as its longest piece
# ("puzzles;", 27.9 pt) and tying "post hoc)" (33.4 pt) would widen it, which makes the first part 6.39 in tall (over the 6.33 in that
# section 5.4 allows of the 6.5 in block). The item 20 panel is a long table whose columns have room, so it ties both.
PUZZLES_RIGHT = "Puzzles right (of\u00a0the cell's puzzles; post hoc)"
PUZZLES_RIGHT_PANEL = "Puzzles right (of\u00a0the cell's puzzles; post\u00a0hoc)"
FA4_RULE = r"^(?:.*_)?(?:ci|cp|wilson)\d\d$|^band$|_bars$"
FA4_RULE_WORDS = ("is one of: ci, cp or wilson followed by two digits (for example ci95), with or without a prefix that ends in an "
                  "underscore; exactly 'band'; or any name ending in _bars")


@dataclass
class _Row:
    """One fa4 cell as TAB-26 prints it."""
    i: int
    base: str                   # result.cells.<i> in fa4
    src: str                    # the pinned source of the collapsed interval
    key: str                    # its key, in the ledger's syntax
    desc: str
    x: int
    n: int
    scale: float
    pair: bool = False
    tries_kind: str = ""        # "vote", "single" or "unstamped"
    plan_tier: Optional[Tuple[str, str]] = None   # (plan id, block in words) when the tier is the plan's
    field: str = "ci95"         # the field the collapsed interval is stamped under (revision 2's cells: ci95)
    point: str = "mean"         # the field beside it that holds the point estimate
    pct: int = 95               # the interval's level, in %


def _ledger_key(plain: str, i: int) -> str:
    """fa4 writes its keys as plain dotted paths ('...bins.[0,10).thirds...'); the ledger's syntax brackets a segment holding a
    bracket or a quote. fa4's segments hold no dot (checked when the zero-width intervals are recounted, in _scope)."""
    segs = plain.split(".")
    key = format_key(segs)
    if parse_key(key) != segs:
        raise ValueError(f"fa4 cell {i}: key {plain!r} does not convert to the ledger's syntax")
    return key


def _cell_spec(cd: Dict[str, object], i: int, n_r2: int) -> Tuple[str, str, int]:
    """The interval field, point field and level (in %) of an fa4 cell. A cell of revision 2 carries none of them (it is a ci95 with a
    `mean`, at 95%); a cell revision 3 added carries all three, and its field's name must end in the level it states (ci90 for 0.9)."""
    named = [k for k in ("field", "point_field", "level") if k in cd]
    if i < n_r2:
        if named:
            raise ValueError(f"fa4 cell {i}: a cell of revision 2 now carries {named}: its ci95 / mean / 95% reading would be wrong")
        return "ci95", "mean", 95
    if len(named) != 3:
        raise ValueError(f"fa4 cell {i}: a cell revision 3 added lacks its field, point_field or level ({named})")
    pct = int(round(100 * float(cd["level"])))                                      # type: ignore[arg-type]
    if abs(100 * float(cd["level"]) - pct) > 1e-9 or not str(cd["field"]).endswith(f"ci{pct}"):                # type: ignore[arg-type]
        raise ValueError(f"fa4 cell {i}: field {cd['field']!r} does not name the level {cd['level']!r} it states")
    return str(cd["field"]), str(cd["point_field"]), pct


def _check_family(S: Store, i: int, path: str, plain: str, field: str) -> None:
    """A cell added by rule: its key is in its family (fa4's file, key pattern and interval field for it), and its description is that
    family and the key, so printing the family beside the key drops nothing."""
    c = f"{FA4}.{i}"
    fam = S.get("fa4", f"{c}.family")
    defs = [f for f in S.get("fa4", "result.families") if f["family"] == fam]
    if len(defs) != 1 or defs[0]["file"] != path or defs[0].get("field", "ci95") != field \
            or not re.fullmatch(defs[0]["key_pattern"], plain):
        raise ValueError(f"fa4 cell {i}: {plain!r} is not in its family {fam!r} (its file, interval field and key pattern)")
    if S.get("fa4", f"{c}.cell") != f"{fam} ({plain})":
        raise ValueError(f"fa4 cell {i}: its description is not its family and key: printing the family would drop what it says")


def _check_counts(S: Store, r: _Row, n_key: Optional[str]) -> None:
    """The zero-width note's facts (x is 0 or n), the exact method (for x = 0 or n the two-sided Clopper–Pearson interval at the cell's
    level, 95% or 90%, has the closed form [t^(1/n), 1] or [0, 1 - t^(1/n)] with t = (1 - level) / 2), and, for an estimate, the stamped
    point value and n of the source block (a block's presets: the sum of its base puzzles)."""
    c = r.base
    if r.x not in (0, r.n):
        raise ValueError(f"fa4 cell {r.i}: {r.x} of {r.n} is neither all right nor all wrong: the zero-width note would be wrong")
    full = 100.0 / r.scale                                              # all right, in the cell's unit (100 points, or a share of 1)
    tail = ((100 - r.pct) / 200.0) ** (1.0 / r.n)
    want = [tail, 1.0] if r.x == r.n else [0.0, 1.0 - tail]
    if any(abs(float(v) - w * full) > 1e-9 * full for v, w in zip(S.get("fa4", f"{c}.exact{r.pct}"), want)):
        raise ValueError(f"fa4 cell {r.i}: exact{r.pct} is not the two-sided {r.pct}% Clopper–Pearson interval for {r.x} of {r.n}")
    if S.has(r.src, f"{r.key}.interval") and S.get(r.src, f"{r.key}.interval") != "cluster bootstrap":
        raise ValueError(f"fa4 cell {r.i}: {r.src}:{r.key} is a {S.get(r.src, f'{r.key}.interval')!r} interval, not a bootstrap one")
    if r.pair:
        return                                                          # a C10 pair: checked by arm in tab_26
    mean = S.get(r.src, f"{r.key}.{r.point}")
    if S.get("fa4", f"{c}.stamped_mean") != mean or mean != (full if r.x == r.n else 0.0):
        raise ValueError(f"fa4 cell {r.i}: {r.x} of {r.n} is not {r.src}:{r.key}'s stamped {r.point} {mean}")
    if n_key is not None:
        nk = _ledger_key(n_key, r.i)
    else:
        nk = next((f"{r.key}.{f}" for f in ("n_base", "n_puzzles") if S.has(r.src, f"{r.key}.{f}")), "")
    got = S.get(r.src, nk) if nk else None
    if isinstance(got, dict) and parse_key(nk)[-1] == "presets":
        got = sum(int(v) for v in got.values())                         # a block's presets: the base puzzles of each, together
    if not nk or got != r.n:
        raise ValueError(f"fa4 cell {r.i}: n {r.n} is not the base puzzles stamped for {r.src}:{r.key}")


def _check_unreported(S: Store, i: int, cd: Dict[str, object], field: str, point: str, pct: int) -> None:
    """A cell revision 3 added that the paper does not report: the fairness check's misapplied-rule rate with its 90% exact interval.
    Checked to be what the scope note says it is (the main analysis; a share; 90%; the stamped interval collapsed; the closed-form exact
    interval for all right or all wrong, at 90%; in its family), so the note's count and words are true. It is never printed as a row."""
    c = f"{FA4}.{i}"
    path, plain = str(cd["source"]), str(cd["key"])
    src, key = _source_name(S, path), _ledger_key(plain, i)
    if (src != "main" or field != UNREPORTED_FIELD or pct != 90 or point != "point" or cd["unit"] != "share (0-1)"
            or cd["note"] is not None or not str(cd["family"]).startswith("fairness check:") or parse_key(key)[-3:-1] != ["misapplied", "rate"]):
        raise ValueError(f"fa4 cell {i}: {plain!r} ({field}) is not the fairness check's misapplied-rule rate at 90%: the scope note's "
                         "words for the cells not reported would be wrong")
    _check_family(S, i, path, plain, field)
    lo, hi = ci_refs(S, src, f"{key}.{field}")
    if [lo.value, hi.value] != cd[f"stamped_ci{pct}"] or lo.value != hi.value:
        raise ValueError(f"fa4 cell {i}: {src}:{key}.{field} {[lo.value, hi.value]} is not fa4's collapsed copy")
    _check_counts(S, _Row(i, c, src, key, str(cd["cell"]), int(cd["x"]), int(cd["n"]), UNIT_SCALE[str(cd["unit"])], field=field,    # type: ignore[call-overload]
                          point=point, pct=pct), cd.get("n_key"))                                                                       # type: ignore[arg-type]


def _pair(S: Store, src: str, key: str, i: int) -> Tuple[str, str, str]:
    """A collapsed interval that is a paired difference (the stamped object holds `d` and `accuracy_means`): its two arms and shape,
    read from the pair's key name ('<a>-vs-<b>:<shape>'), with the direction checked: d = mean(a) - mean(b)."""
    m = re.fullmatch(r"(.+)-vs-(.+):(\d+x\d+)", parse_key(key)[-1])
    if not m:
        raise ValueError(f"fa4 cell {i}: paired-difference key {key!r} does not name '<a>-vs-<b>:<shape>'")
    a, b, sh = m.groups()
    means = S.get(src, f"{key}.accuracy_means")
    if sorted(means) != sorted([a, b]) or a not in STUDY1_ARMS or b not in STUDY1_ARMS:
        raise ValueError(f"fa4 cell {i}: {key} arms {sorted(means)} are not the pair its name says ({a}, {b})")
    if not math.isclose(float(S.get(src, f"{key}.d")), float(means[a]) - float(means[b]), abs_tol=1e-9):
        raise ValueError(f"fa4 cell {i}: {key}.d is not {a} minus {b}: the direction printed below would be wrong")
    return a, b, sh


def _s1b_arm_tries(S: Store, arm_key: str, i: int) -> Cell:
    """Tries per base puzzle of an arm of Study 1b's effort sweep (descriptive.arms.<tag>@<N>.<shape>): constants.designed_tries for
    its tag, checked against the arm's designed count, or, for a tag it does not list, designed tries over base puzzles (simple
    arithmetic, checked whole)."""
    tag = parse_key(arm_key)[2].split("@")[0]
    designed, n_base = S.get("s1b", f"{arm_key}.designed"), S.get("s1b", f"{arm_key}.n_base")
    if S.has("s1b", f"constants.designed_tries.{tag}"):
        r = S.ref("s1b", f"constants.designed_tries.{tag}")
        if r.value * n_base != designed:
            raise ValueError(f"fa4 cell {i}: {arm_key} designed {designed} is not {r.value} tries per base puzzle")
        return integer(r)
    if designed % n_base:
        raise ValueError(f"fa4 cell {i}: {arm_key} designed {designed} is not a whole number of tries per base puzzle")
    return num_d(derive("designed / n_base", lambda a, b: a / b, S.ref("s1b", f"{arm_key}.designed"),
                        S.ref("s1b", f"{arm_key}.n_base")), dp=0)


def _s1b_copy(S: Store, key: str, arm_key: str, i: int) -> None:
    """A Study 1b figure's copy of an arm: the same mean, interval and designed tries as the arm it copies."""
    segs = parse_key(arm_key)
    if segs[:2] != ["descriptive", "arms"] or len(segs) != 4:
        raise ValueError(f"fa4 cell {i}: {arm_key} is not an arm of Study 1b's effort sweep")
    for f in ("mean", "ci95", "designed"):
        if S.get("s1b", f"{key}.{f}") != S.get("s1b", f"{arm_key}.{f}"):
            raise ValueError(f"fa4 cell {i}: {key}.{f} is not {arm_key}'s: the row is not a copy of that arm")


def _tries(S: Store, r: _Row, arm: Optional[str], n_key: Optional[str]) -> Tuple[Cell, str]:
    """Tries per base puzzle behind a row, from the stamped key that holds it in the row's own source (a vote: its k), and the kind
    of row ('vote', 'single' for one or several single tries, 'unstamped'). A row of a kind not listed here refuses the build."""
    src, key, i = r.src, r.key, r.i
    segs = parse_key(key)
    item7 = parse_key(ITEM7_ARMS)
    if src == "main" and segs[:-1] == item7:
        return integer(S.ref(src, join_key(*segs, "designed_tries"))), "single"
    if src == "groupc" and arm is not None:
        return integer(S.ref("main", join_key(*item7, arm, "designed_tries"))), "single"
    if src == "topup" and segs[0] == "accuracy" and segs[1] in TOPUP_MAIN_ARMS:
        main_arm = TOPUP_MAIN_ARMS[segs[1]]
        if "(main run)" not in r.desc or not _names_in(r.desc, STUDY1_ARMS[main_arm][0]):
            raise ValueError(f"fa4 cell {i}: {r.desc!r} is not the main run's {STUDY1_ARMS[main_arm][0]}")
        if S.get(src, f"{key}.n_base") != S.get("main", join_key(*item7, main_arm, "n_puzzles")):
            raise ValueError(f"fa4 cell {i}: {key} does not cover the main run's base puzzles")
        return integer(S.ref("main", join_key(*item7, main_arm, "designed_tries"))), "single"
    if src == "main" and segs[:3] == I20:
        if segs[-2] != "mean_vote_at_k" or int(segs[-1]) != len(S.get(src, join_key(*segs[:-1]))) - 1:
            raise ValueError(f"fa4 cell {i}: {key} is not item 20's vote at its largest k (the one FIG-02 draws)")
        return integer(S.ref(src, f"{key}.k")), "vote"
    if src == "main" and segs[:3] == ["reporting", "group_b", "item_24"] and segs[-2] == "vote_at_own_k":
        k = S.ref(src, f"{key}.k")
        if S.get(src, f"{key}.cpc.k") != k.value or S.get(src, f"{key}.cost_per_puzzle.k") != k.value:
            raise ValueError(f"fa4 cell {i}: {key}'s k is not the k of its cost rows")
        return integer(k), "vote"
    if src == "main" and segs[:4] == I9E and len(segs) == 7 and segs[6] == "even" and r.field == "opus_accuracy_ci95":
        # Item 9e's Opus-medium accuracy on the even bases: the cascade escalates to Opus-medium's answer (the stamped rule names it), the
        # main run's Opus-medium arm, whose designed tries per puzzle item 7 stamps. The digit in the key is the cascade's k_c, not a try.
        arm = "opus-med"
        if not _names_in(str(S.get(src, join_key(*segs[:6], "rule"))), STUDY1_ARMS[arm][0]) or not segs[5].isdigit() \
                or S.get(src, f"{key}.bootstrap_name") != f"cascade:{segs[4]}:{segs[5]}":
            raise ValueError(f"fa4 cell {i}: {key} is not item 9e's {STUDY1_ARMS[arm][0]} accuracy on the even bases of one cascade")
        return integer(S.ref("main", join_key(*item7, arm, "designed_tries"))), "single"
    if "vote_curve" in segs or "vote_curve_n16" in segs:
        j = segs.index("points") + 1
        k_ref = S.ref(src, join_key(*segs[:j + 1], "k"))
        if S.has(src, f"{key}.designed") and S.get(src, f"{key}.designed") != k_ref.value * S.get(src, f"{key}.n_base"):
            raise ValueError(f"fa4 cell {i}: {key}'s designed tries are not k per base puzzle")
        return integer(k_ref), "vote"
    if src == "fa2" and len(segs) == 5 and segs[0] == "result" and segs[2] == "curve":
        return integer(S.ref(src, join_key(*segs[:4], "k"))), "vote"
    if src in CURVES and segs[0] == "models" and segs[2] == "by_n":
        return integer(S.ref(src, join_key("models", segs[1], "tries_per_puzzle"))), "single"
    if src in CURVES and segs[0] == "pilot1":
        if any("tries" in f for f in S.keys(src, key)):
            raise ValueError(f"fa4 cell {i}: {src}:{key} now stamps its tries: print them")
        return label("not stamped"), "unstamped"
    if src == "s1b" and segs[:2] == ["descriptive", "arms"]:
        return _s1b_arm_tries(S, key, i), "single"
    if src == "s1b" and segs[0] == "per_form" and len(segs) == 4:
        t, sh, side = segs[1:]
        tags = [g for g in S.keys(src, f"completeness.{t}.arms") if STUDY1B_TAGS[g][1] == PER_FORM_SIDE.get(side)]
        if len(tags) != 1:
            raise ValueError(f"fa4 cell {i}: {key}'s side {side!r} is not one arm of {t}")
        arm_key = join_key("descriptive", "arms", f"{tags[0]}@{S.get(src, f'completeness.{t}.N')}", sh)
        if any(S.get(src, f"{key}.{f}") != S.get(src, f"{arm_key}.{f}") for f in ("mean", "n_base")):
            raise ValueError(f"fa4 cell {i}: {key} is not the arm, shape and base puzzles of {arm_key}")
        return _s1b_arm_tries(S, arm_key, i), "single"
    if src == "s1b" and segs[:2] == ["descriptive", "effort_figure"] and len(segs) == 6:
        arm_id = S.get(src, join_key(*segs[:5], "arm"))
        arm_key = join_key("descriptive", "arms", arm_id, segs[5])
        if segs[2] != "N=" + arm_id.split("@")[1] or n_key is None or _ledger_key(n_key, i) != f"{arm_key}.n_base":
            raise ValueError(f"fa4 cell {i}: {key} is not the figure's copy of {arm_key}")
        _s1b_copy(S, key, arm_key, i)
        return _s1b_arm_tries(S, arm_key, i), "single"
    if src == "s1b" and segs[:2] == ["descriptive", "length_curve"] and segs[2] != "ladder" and len(segs) == 5:
        arm_key = _ledger_key(n_key, i)[:-len(".n_base")] if n_key and n_key.endswith(".n_base") else ""
        a = parse_key(arm_key) if arm_key else []
        if len(a) != 4 or a[2].split("@") != [a[2].split("@")[0], segs[3]] or a[3] != segs[4] \
                or STUDY1B_TAGS.get(a[2].split("@")[0], ("",))[0].lower() != segs[2]:
            raise ValueError(f"fa4 cell {i}: {key} names no matching arm of Study 1b ({n_key})")
        _s1b_copy(S, key, arm_key, i)
        return _s1b_arm_tries(S, arm_key, i), "single"
    if src == "s1b" and segs[:3] == ["descriptive", "length_curve", "ladder"] and len(segs) == 6:
        lad = "descriptive.length_curve.ladder"
        if S.get(src, f"{lad}.source") != S.sources["curve_d90"].path or S.get(src, f"{lad}.source_sha256") != S.sources["curve_d90"].sha256:
            raise ValueError(f"fa4 cell {i}: Study 1b's ladder copy is not of the pinned length-sweep file (Deviation 2 rule)")
        block = S.get(src, join_key(*segs[:5]))
        tags = [m for m in S.keys("curve_d90", "models") if STUDY1B_TAGS[m][0].lower() == segs[3]
                and S.has("curve_d90", join_key("models", m, "by_n", segs[4], "whole_answer"))
                and S.get("curve_d90", join_key("models", m, "by_n", segs[4], "whole_answer")) == block]
        if len(tags) != 1:
            raise ValueError(f"fa4 cell {i}: {key} is not a copy of one length-sweep whole-answer block")
        return integer(S.ref("curve_d90", join_key("models", tags[0], "tries_per_puzzle"))), "single"
    raise ValueError(f"fa4 cell {i}: no stamped tries per base puzzle known for {src}:{key}")


def _plan_tier(S: Store, oid: str, fragment: str) -> Cell:
    """The plan's tier (label) for output `oid`, which must list `fragment` among its source keys."""
    entries = S.get("plan", "plan.tables_figures")
    js = [j for j, e in enumerate(entries) if e["id"] == oid]
    if len(js) != 1 or fragment not in entries[js[0]]["source_keys"]:
        raise ValueError(f"the plan's {oid} does not list {fragment}: its tier would not be these cells' tier")
    return text_of(S.ref("plan", f"plan.tables_figures.{js[0]}.label"))


PILOT1_TIER = "exploratory"


def _pilot1_tier(S: Store, src: str, key: str, i: int) -> Cell:
    """A Pilot 1 marker the length-sweep files carry is exploratory, not the sweep's descriptive tier (Edith's Q13 ruling): the plan's
    entry for the length-sweep table, which reads these markers (its source keys name `pilot1`), gives its 24-step markers, the Pilot
    1 markers, that tier. The cell is printed from that plan label, which it cites; the marker must be stamped as a Pilot 1 result."""
    stamped = str(S.get(src, join_key(*parse_key(key), "label")))
    if not stamped.startswith("pilot-1,") or not stamped.endswith("before lock-2 (different rule mix, sets and timing)"):
        raise ValueError(f"fa4 cell {i}: {src}:{key} is not stamped as a Pilot 1 result before Lock 2 (the tiers note says so)")
    js = [j for j, e in enumerate(S.get("plan", "plan.tables_figures")) if e["id"] == "TAB-13"]
    if len(js) != 1:
        raise ValueError("the plan has no one length-sweep table (TAB-13): the Pilot 1 markers' tier has no source")
    e = f"plan.tables_figures.{js[0]}"
    lab = S.ref("plan", f"{e}.label")
    if "pilot1" not in S.get("plan", f"{e}.source_keys") or not str(lab.value).endswith(f"24-step markers {PILOT1_TIER}"):
        raise ValueError("the plan's length-sweep table no longer gives its Pilot 1 (24-step) markers the tier printed here")
    return Cell(PILOT1_TIER, raw=lab.value, refs=(lab,),
                formula="the tier the plan's length-sweep table (TAB-13) gives its 24-step markers, the Pilot 1 markers")


def _tier(S: Store, src: str, key: str, i: int) -> Tuple[Cell, Optional[Tuple[str, str]]]:
    """The stamped interval's own tier, from its source: C10's stamped exploratory label, a Study 1 reporting item's label, the top-up
    file's label, Study 1b's descriptive block (its key name), the length sweep's plan line (descriptive only), free analysis 2's tier
    label; where the source stamps none (items 20 and 24, Study 1b's per-test cells), the plan's tier for the output that reports it."""
    segs = parse_key(key)
    head = segs[2] if src == "main" and segs[:2] == ["reporting", "group_b"] else segs[0]
    if src == "main" and segs[:3] == ITEM24 and len(segs) == 7 and segs[3] == "table" and segs[5] == "vote_at_own_k":
        # Edith, proof 3 (p. 49), option (a): one result, one label. Item 24's own-k votes are item 10's own-k votes (checked equal in
        # _item24_label_note), so they print item 10's stamped label, as TAB-05 does
        return text_of(S.ref("main", join_key(*ITEM10, "label"))), None
    if (src, head) in PLAN_TIERS:
        oid, frag, words = PLAN_TIERS[(src, head)]
        own = join_key(*segs[:3], "label") if src == "main" else join_key(head, "label")
        if S.has(src, own):
            raise ValueError(f"{src}:{own} is now stamped: print the source's own tier")
        return _plan_tier(S, oid, frag), (oid, words)
    if src == "groupc" and segs[0] == "item_C10":
        return text_of(S.ref(src, "item_C10.exploratory")), None
    if src == "main" and segs[:2] == ["reporting", "group_b"]:
        return text_of(S.ref(src, join_key(*segs[:3], "label"))), None
    if src == "topup":
        return text_of(S.ref(src, "label")), None
    if src == "s1b" and segs[0] == "descriptive":
        return Cell(segs[0], raw=segs[0], refs=(Ref(segs[0], src, segs[0]),), formula="the key name"), None
    if src in CURVES:
        if "(descriptive only)" not in S.get(src, "plan"):
            raise ValueError(f"{src}: the length sweep's stamped plan line no longer says 'descriptive only'")
        if segs[0] == "pilot1":
            return _pilot1_tier(S, src, key, i), None
        return label("descriptive"), None
    if src == "fa2":
        return text_of(S.ref(src, "definition.tier_label")), None
    raise ValueError(f"fa4 cell {i}: no stamped tier known for {src}:{key}")


def _equal_pair(v: object) -> bool:
    return isinstance(v, list) and len(v) == 2 and all(is_num(x) for x in v) and v[0] == v[1]


def _two_numbers(v: object) -> bool:
    """A list of exactly two numbers, as free analysis 4's scan reads one (a bool is no number)."""
    return isinstance(v, list) and len(v) == 2 and all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in v)


def _scan_fields(doc: object, path: Tuple[str, ...] = ()):
    """Every two-number field of a stamped file, under any name, as (segments of the dict holding it, its name, its two ends): the
    fields fa4's scan reads (a dict's value). A two-number list that is a list's element is no such field and the scan does not read
    it, so it refuses the recount (the scan's reach would be overstated)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            if _two_numbers(v):
                yield list(path), str(k), v
        for k, v in doc.items():
            yield from _scan_fields(v, path + (str(k),))
    elif isinstance(doc, list):
        for j, v in enumerate(doc):
            if _two_numbers(v):
                raise ValueError(f"{'.'.join(path + (str(j),))}: a two-number list that is a list's element: fa4's scan does not read it")
            yield from _scan_fields(v, path + (str(j),))


def _model_name(S: Store, src: str, tag: str) -> str:
    """A length-sweep model's display name from its key tag, checked against the file's stamped model family and effort."""
    m = join_key("models", tag)
    fam = re.match(r"claude-([a-z]+)-", str(S.get(src, f"{m}.model")))
    if tag not in STUDY1B_TAGS or not fam or (fam.group(1), S.get(src, f"{m}.effort")) != STUDY1B_TAGS[tag][1:3]:
        raise ValueError(f"{src}:{m}: its stamped model and effort are not {STUDY1B_TAGS.get(tag, ('?',))[0]}")
    return STUDY1B_TAGS[tag][0]


def _excluded_kind(rest: str) -> str:
    """The kind of zero-width interval an fa4 excluded entry's reason names (the part of its `what` after the file name): item 20 below
    its largest k, q's q^N bands, or q's own interval (the original-rule file's reason and the Deviation 2 file's 'as for' it)."""
    if rest.startswith("item 20 at k below"):
        return "item20"
    if rest.startswith("q's q^N bands"):
        return "bands"
    if re.search(r"\bq\b", rest):
        return "q"
    raise ValueError(f"fa4's excluded entry {rest!r} names no kind of cell that the scope note knows")


def _left_kind(S: Store, src: str, field: str, holder: List[str]) -> str:
    """The kind of a zero-width interval no fa4 cell covers, checked to be what fa4's excluded entries say: the length sweep's q (the
    interval pooled over every length, under ci95), q's q^N bands (under band: q's interval to the power N, recomputed here), or item 20
    below its largest k (under ci95). Any other refuses the build: the scope note would not name it."""
    k = ".".join(holder)
    if field == "ci95" and src in CURVES and re.fullmatch(r"models\.[^.]+\.q", k):
        return "q"
    if field == "ci95" and src == "main" and holder[:3] == I20 and holder[-2] == "mean_vote_at_k" \
            and int(holder[-1]) < len(S.get(src, format_key(holder[:-1]))) - 1:
        return "item20"
    if field == "band" and src in CURVES and holder[0] == "models" and holder[2] == "q" and (
            (len(holder) == 5 and holder[3] == "by_n" and holder[4].isdigit()) or (len(holder) == 4 and holder[3].isdigit())):
        q, steps = S.get(src, join_key("models", holder[1], "q", "ci95")), int(holder[-1])
        if not _equal_pair(q) or any(abs(float(b) - float(e) ** steps) > 1e-9 for b, e in zip(S.get(src, join_key(*holder, "band")), q)):
            raise ValueError(f"{src}:{k}.band is not q's zero-width interval to the power {steps}: fa4's reason for the q^N bands would be wrong")
        return "bands"
    raise ValueError(f"{src}:{k}.{field} is a zero-width interval that is no fa4 cell and none of the kinds fa4 lists as left out")


def _could_print_the_nine(name: str, text: str) -> Optional[str]:
    """Why another paper-output module (not core, which defines the lookups, and not this one) could print one of the nine 90% exact
    intervals, or None. The ways: naming the misapplied-rule rates or an exact 90% interval; calling core.fa4_exact with a field other
    than a row field (a 90% interval is read by its field, e.g. field="ci90"), with one it does not spell out, or passing the function
    on instead of calling it; reading a cell's exact interval at a level it does not spell out (a key built as exact<level>). A text and
    syntax guard, not a proof: it refuses what a module would have to write to reach them. Other modules name ci90 for Flag R's
    intervals and read fa4's cells for the 95% exact intervals, so neither alone is a reason to refuse."""
    if "misapplied" in text or "exact90" in text:
        return "names the misapplied-rule rates or an exact 90% interval"
    tree = ast.parse(text)
    called = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if (isinstance(f, ast.Name) and f.id == "fa4_exact") or (isinstance(f, ast.Attribute) and f.attr == "fa4_exact"):
                called.add(id(f))
                if len(n.args) > 3 or any(isinstance(a, ast.Starred) for a in n.args):
                    return "calls fa4_exact with its interval field as a positional argument"
                for k in n.keywords:
                    if k.arg != "field" or not (isinstance(k.value, ast.Constant) and k.value.value in ROW_FIELDS):
                        return f"calls fa4_exact with a field that is not spelled out as one of {ROW_FIELDS}"
        elif isinstance(n, ast.ImportFrom) and any(a.name == "fa4_exact" and a.asname for a in n.names):
            return "imports fa4_exact under another name"
    for n in ast.walk(tree):
        if (isinstance(n, ast.Name) and n.id == "fa4_exact" and id(n) not in called) \
                or (isinstance(n, ast.Attribute) and n.attr == "fa4_exact" and id(n) not in called):
            return "passes fa4_exact on instead of calling it"
        if isinstance(n, ast.JoinedStr):
            for a, b in zip(n.values, n.values[1:]):
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.endswith("exact") \
                        and isinstance(b, ast.FormattedValue):
                    return "reads an exact interval at a level it does not spell out"
    return None


def _nothing_else_prints_the_nine(texts: Optional[Mapping[str, str]] = None) -> None:
    """The scope note says no table or figure prints the nine 90% exact intervals. Another paper-output module that could (see
    _could_print_the_nine) would break that sentence: the build refuses until it is rewritten. `texts` (module file name -> source
    text) is for a test; by default every paper_out_*.py beside this module is read."""
    here = Path(__file__).resolve()
    if texts is None:
        texts = {f.name: f.read_text("utf-8") for f in sorted(here.parent.glob("paper_out_*.py")) if f != here}
    for name, text in texts.items():
        if name == "paper_out_core.py":
            if "misapplied" in text:
                raise ValueError(f"{name} names the misapplied-rule rates: the scope note's 'no table or figure prints them' would be wrong")
            continue
        why = _could_print_the_nine(name, text)
        if why:
            raise ValueError(f"{name} {why}: the scope note's 'no table or figure prints them' would be wrong")


def _scope(S: Store, n_first: int, n_r2: int, unreported: List[int], printed: List[int], pair_keys: set) -> List[List[Cell]]:
    """The scope notes. The rows (main table and panel) are every zero-width interval in the files fa4's scan read, under any interval
    field name, but fa4's own exclusions and the nine 90% cells that are not reported. Checked by recounting EVERY two-number field of
    each of those files, under any name (as the scan does): the counts by field name equal result.scan's (the intervals by its rule, and
    the one field it does not count, quartiles); the zero-width ones by file and field equal result.scan.zero_width_by_field; and, per
    file and field, they are exactly fa4's cells plus the ones fa4's excluded entries count, each of the kind its reason names (else the
    build is refused). The not-reported cells are checked to be what the note says, and the note's tallies add up to the scan's."""
    rev, scan, inputs = S.get("fa4", "result.revision"), S.get("fa4", "result.scan"), S.get("fa4", "inputs.stamped_files")
    cells, excluded = S.get("fa4", FA4), S.get("fa4", "result.excluded")
    checks = S.get("fa4", "checks")
    if rev["number"] != 3 or not all(ch["equal"] is True for ch in checks):
        raise ValueError("fa4 is not revision 3 with its own checks equal: the scope note would be wrong")
    if FA4_KEEPS not in str(rev["why"]) or not any(FA4_CHECK in str(ch["what"]) for ch in checks):
        raise ValueError(f"fa4 no longer says that revision 3 {FA4_KEEPS} (result.revision.why) with a stamped check on {FA4_CHECK}: "
                         "the scope note's word 'unchanged' would have nothing behind it")
    name_of = {f["path"]: n for n, f in inputs.items()}
    if any(p not in name_of for p in scan["files"]) or \
            {inputs[n]["path"].rsplit("/", 1)[-1] for n in inputs if inputs[n]["path"] not in scan["files"]} != {"fa4.json", rev["of"]}:
        raise ValueError("fa4's scan read other files than its inputs less its two earlier revisions: the scope note would be wrong")
    rx = re.compile(scan["interval_field_rule"])
    src_of: Dict[str, str] = {}                                    # input name -> pinned source
    seen: Dict[str, int] = {}                                      # interval fields by name, counted
    skipped: Dict[str, int] = {}                                   # two-number fields the rule does not count as intervals
    zero: Dict[Tuple[str, str], List[List[str]]] = {}              # (input name, field) -> holders of its zero-width intervals
    for path in scan["files"]:
        name = name_of[path]
        src = _source_name(S, path)
        if S.sources[src].sha256 != inputs[name]["sha256"] or src not in SOURCE_NAMES:
            raise ValueError(f"fa4 read {path} with another SHA-256 than the pinned one, or it has no printed name")
        src_of[name] = src
        for holder, field, v in _scan_fields(S.doc(src)):
            counted = rx.search(field) is not None
            bucket = seen if counted else skipped
            bucket[field] = bucket.get(field, 0) + 1
            if v[0] == v[1]:
                if not counted:
                    raise ValueError(f"{src}:{'.'.join(holder)}.{field} is a zero-width two-number field that fa4's rule does not count")
                zero.setdefault((name, field), []).append(holder)
    not_int = scan["two_number_fields_not_intervals"]
    if seen != scan["interval_fields"] or len(not_int) != 1 or skipped != {k: d["count"] for k, d in not_int.items()}:
        raise ValueError("the two-number fields recounted in fa4's files are not the scan's interval fields and its one non-interval field")
    if {f"{n}: {f}": len(h) for (n, f), h in zero.items()} != scan["zero_width_by_field"]:
        raise ValueError("the zero-width intervals recounted in fa4's files are not result.scan.zero_width_by_field")
    covered: Dict[Tuple[str, str], set] = {}
    for cd in cells:
        if cd["source"] not in name_of or name_of[cd["source"]] not in src_of:
            raise ValueError(f"fa4 has a cell of {cd['source']!r}, which its scan did not read")
        covered.setdefault((name_of[cd["source"]], cd.get("field", "ci95")), set()).add(cd["key"])
    left_n: Dict[Tuple[str, str], int] = {}                        # (input name, kind) -> zero-width intervals no cell covers
    for name, field in sorted(set(zero) | set(covered)):
        holders = zero.get((name, field), [])
        if any("." in s for h in holders for s in h):
            raise ValueError(f"{src_of[name]}: a zero-width interval's key segment holds a dot: fa4's plain keys would be ambiguous")
        plain = {".".join(h) for h in holders}
        mine = covered.get((name, field), set())
        if mine - plain:
            raise ValueError(f"{src_of[name]}: fa4 cells that are not zero-width {field} intervals of the file: {sorted(mine - plain)[:3]}")
        for k in sorted(plain - mine):
            kind = _left_kind(S, src_of[name], field, k.split("."))
            left_n[(name, kind)] = left_n.get((name, kind), 0) + 1
    ex_n: Dict[Tuple[str, str], int] = {}
    for e in excluded:
        name, rest = str(e["what"]).split(":", 1)
        if name not in src_of:
            raise ValueError(f"fa4's excluded entry names no file its scan read ({name!r})")
        kind = _excluded_kind(rest.strip())
        ex_n[(name, kind)] = ex_n.get((name, kind), 0) + int(e["zero_width_intervals"])
    if ex_n != left_n:
        raise ValueError(f"the zero-width intervals no fa4 cell covers {left_n} are not the ones fa4's excluded entries count {ex_n}")
    triple = lambda i: (cells[i]["source"], cells[i]["key"], cells[i].get("field", "ci95"))                       # noqa: E731
    shown, hidden = {triple(i) for i in printed}, {triple(i) for i in unreported}
    total = sum(scan["zero_width_by_field"].values())
    n_left = sum(ex_n.values())
    if len(shown) + len(hidden) + n_left != total or shown & hidden or len(shown | hidden) != len({triple(i) for i in range(len(cells))}):
        raise ValueError(f"the intervals in the rows ({len(shown)}), not reported ({len(hidden)}) and left out ({n_left}) are not the "
                         f"scan's {total}")
    if len(printed) != len(shown) and any(_ledger_key(cells[i]["key"], i) not in pair_keys for i in printed
                                          if sum(triple(j) == triple(i) for j in printed) > 1):
        raise ValueError("two printed rows share one stamped interval, and it is not a paired difference's")
    if not unreported or not any(i >= n_r2 for i in printed):
        raise ValueError("fa4 has no unreported cells, or none of revision 3's added cells is a row: the scope note's words assume both")
    new_rows = [i for i in printed if i >= n_r2]
    if n_r2 + S.get("fa4", ADDED) != len(cells) or sorted(new_rows + unreported) != list(range(n_r2, len(cells))):
        raise ValueError("revision 3's added cells are not exactly the rows added and the cells not reported")
    if any(cells[i]["field"] != "opus_accuracy_ci95" or cells[i]["key"].split(".")[:4] != I9E
           or not cells[i]["key"].endswith(".even") or not str(cells[i]["family"]).startswith("item 9e: the cascade's Opus-medium accuracy")
           for i in new_rows):
        raise ValueError("a row revision 3 added is not item 9e's Opus-medium accuracy on the even bases: the scope note's words would be wrong")
    if len({cells[i]["field"] for i in unreported}) != 1 or {cells[i]["field"] for i in unreported} != {UNREPORTED_FIELD}:
        raise ValueError("the cells not reported are not all under one field, ci90")
    _nothing_else_prints_the_nine()

    def tally(n: int, refs: Sequence[Ref], formula: str) -> Cell:
        return Cell(f"{n:,}", raw=n, refs=tuple(refs), formula=formula)

    def file_cell(name: str) -> Cell:
        """The study or run of a file fa4's scan read, printed from fa4's stamped path for it."""
        return text_of(S.ref("fa4", join_key("inputs", "stamped_files", name, "path")), {inputs[name]["path"]: SOURCE_NAMES[src_of[name]]})

    files = joined(*[file_cell(n) for n in sorted(src_of, key=lambda n: SOURCE_ORDER.index(src_of[n]))], sep="; ")
    c_r2, c_add = integer(S.ref("fa4", R2)), integer(S.ref("fa4", ADDED))
    c_first = tally(n_first, [S.ref("fa4", f"{FA4}.{i}.cell") for i in range(n_first)],
                    "count of fa4's cells that carry no family (the first version's)")
    c_rule = tally(n_r2 - n_first, [S.ref("fa4", f"{FA4}.{i}.family") for i in range(n_first, n_r2)],
                   "count of the cells of revision 2 that carry a family (added by rule)")
    c_new = tally(len(new_rows), [S.ref("fa4", f"{FA4}.{i}.key") for i in new_rows],
                  "count of the cells revision 3 added that are rows here (item 9e's Opus-medium accuracy)")
    c_unrep = tally(len(unreported), [S.ref("fa4", f"{FA4}.{i}.key") for i in unreported],
                    "count of the cells revision 3 added that are not reported (the fairness check's 90% intervals)")
    # prints nothing; carries fa4's account of "unchanged" (the checked sentence is its raw value: the account also names a decision)
    why_rec = Cell("", raw=FA4_KEEPS, refs=(S.ref("fa4", "result.revision.why"),),
                   formula="fa4's own account that this revision keeps the previous revision's cells unchanged (checked to say so)")
    f_new = text_of(S.ref("fa4", f"{FA4}.{new_rows[0]}.field"))
    f_unrep = text_of(S.ref("fa4", f"{FA4}.{unreported[0]}.field"))
    if len({cells[i]["field"] for i in new_rows}) != 1:
        raise ValueError("the rows revision 3 added are under more than one field: name each")
    notes: List[List[Cell]] = [
        [_glue(label("Scope (free analysis 4, revision "), integer(S.ref("fa4", "result.revision.number")),
               label("): the rows of this table and of its item 20 panel are every zero-width interval (a stamped interval whose two ends are "
                     "equal) that free analysis 4 covers, under any interval field name, in the result files its scan reads ("),
               files, label("),")), label("except the"), c_unrep, label("that are not reported (below).")],
        [label("Cells: the previous revision's"), c_r2, _glue(label("cells, unchanged"), why_rec), label("(the first version's"),
         _glue(c_first, label(",")), label("and"), c_rule,
         label("added by rule, all under the key ci95), and the"), c_add, label("that this revision added by scanning every interval "
                                                                              "field by name:"),
         c_new, label("are rows here (item 9e's Opus-medium accuracy on the even-indexed puzzles, stamped under"), _glue(f_new, label(") and")),
         c_unrep, label("are not reported.")],
        [label("Not reported: this revision also computed"), c_unrep, label("exact 90% intervals (Clopper–Pearson, at the stamped interval's "
                                                                       "own level) for the fairness check's misapplied-rule rates, "
                                                                       "stamped under"), _glue(f_unrep, label(";")),
         label("they are not reported (beyond the approved scope), and no table or figure prints them.")]]
    order = sorted(range(len(excluded)), key=lambda j: SOURCE_ORDER.index(src_of[str(excluded[j]["what"]).split(":", 1)[0]]))
    left_out: List[Cell] = []
    if excluded:
        left_out.append(label("Left out (each keeps its zero-width stamped interval and has no exact interval), with free analysis 4's "
                              "counts and reasons:"))
        for pos, j in enumerate(order):
            cnt = S.ref("fa4", f"result.excluded.{j}.zero_width_intervals")
            what = S.ref("fa4", f"result.excluded.{j}.what")
            tag, reason = str(what.value).split(":", 1)                  # fa4's file tag ("main", "curve"): the study is printed beside
            left_out += [integer(cnt), label("zero-width interval" + ("" if cnt.value == 1 else "s") + " in"), file_cell(tag),
                         _glue(label('("'), text_of(what, {what.value: reason.strip()}),
                               label('")' + (";" if pos < len(order) - 1 else ".")))]
        notes.append(left_out)
    c_total = tally(total, [S.ref("fa4", join_key("result", "scan", "zero_width_by_field", k)) for k in scan["zero_width_by_field"]],
                    "sum of the scan's zero-width counts by file and field")
    c_shown = tally(len(shown), [S.ref("fa4", f"{FA4}.{i}.key") for i in printed],
                    "count of the distinct stamped intervals behind the rows and the item 20 panel")
    c_left = tally(n_left, [S.ref("fa4", f"result.excluded.{j}.zero_width_intervals") for j in range(len(excluded))],
                   "sum of the zero-width counts of fa4's excluded entries")
    notes.append([label("Recount: the scan finds"), c_total, label("zero-width intervals in these files, under any field name;"), c_shown,
                  label("are behind the rows and the item 20 panel" + (" (a paired difference's one interval has a row for each of its "
                                                                        "two settings)" if len(printed) != len(shown) else "") + ","),
                  c_left, label("are left out and"), c_unrep, label("are not reported.")])
    q_name = next(iter(not_int))
    q_cnt = S.ref("fa4", join_key("result", "scan", "two_number_fields_not_intervals", q_name, "count"))
    c_fields = tally(sum(scan["interval_fields"].values()),
                     [S.ref("fa4", join_key("result", "scan", "interval_fields", k)) for k in scan["interval_fields"]],
                     "sum of the scan's counts of the two-number fields it counts as intervals")
    rule = S.ref("fa4", "result.scan.interval_field_rule")
    if rule.value != FA4_RULE:
        raise ValueError(f"fa4's interval-field rule is now {rule.value!r}, not the one the Scan note describes in words ({FA4_RULE_WORDS})")
    notes.append([label("Scan: free analysis 4 reads every two-number field in these files; it counts"), c_fields,
                  label("of them as intervals, those whose field name"),
                  _glue(text_of(rule, {FA4_RULE: FA4_RULE_WORDS}), label(",")),
                  label("and the only one it does not count as an interval is"),
                  Cell(q_name, raw=q_name, refs=(Ref(q_name, "fa4", join_key("result", "scan", "two_number_fields_not_intervals", q_name)),),
                       formula="the key name"),
                  _glue(label("("), integer(q_cnt), label(" fields: "),
                        text_of(S.ref("fa4", join_key("result", "scan", "two_number_fields_not_intervals", q_name, "why"))), label(").")),
                  ])
    return notes


def _collapsed(S: Store, source: str, key: str) -> bool:
    v = S.get(source, key)
    return isinstance(v, list) and len(v) == 2 and v[0] == v[1]


# fa4's own note on the length sweep's q, which the typed length-sweep sentence replaces in print (Edith's Q20: the sentence is guarded
# against it), and the words of fa4's stamped reason for leaving q out that the sentence also rests on: q pools every piece-step over
# the lengths (the sentence's "pooled over the sweep's lengths"), and q to the power N is the compounded reference (its "q to the power
# N is the reference for a chain of N steps"). A changed note or reason refuses the build.
FA4_Q_NOTE = "the length sweep's q is estimated from pieces only, so its exact counterpart is the pieces per-step row"
FA4_Q_EXCLUDED = ("curve: q pools every piece-step over all lengths and sets", "its q^N bands are powers of its interval")


def _q_records(S: Store) -> Tuple[Cell, Cell]:
    """fa4's q note and its reason for leaving the original-rule file's q out, each checked against the words the length-sweep
    sentence rests on, as cells that print nothing and carry the two records into the sentence's provenance."""
    note = S.ref("fa4", "result.q_note")
    if note.value != FA4_Q_NOTE:
        raise ValueError(f"fa4's q note is now {note.value!r}: rewrite the length-sweep sentence that replaces it")
    hits = [j for j, e in enumerate(S.get("fa4", "result.excluded")) if str(e["what"]).startswith(FA4_Q_EXCLUDED[0])]
    if len(hits) != 1:
        raise ValueError("fa4 no longer stamps one reason for leaving the length sweep's q out: the length-sweep sentence has no source")
    why = S.ref("fa4", f"result.excluded.{hits[0]}.what")
    if not all(w in why.value for w in FA4_Q_EXCLUDED):
        raise ValueError(f"fa4's reason for leaving q out no longer says {FA4_Q_EXCLUDED}: rewrite the length-sweep sentence")
    return text_of(note, {FA4_Q_NOTE: ""}), text_of(why, {why.value: ""})


def _sweep_note(S: Store, rows: List[_Row], n_first: int) -> List[List[Cell]]:
    """The length-sweep note. q pools the pieces of every length of the sweep (fa4's q note: estimated from pieces only), so the
    pieces per-step rows are q's inputs, each at its own length; the one model's q has a zero-width stamped interval and fa4 leaves it
    out (the scope note gives the reason); the other models' q intervals have width. A first-version row's description names the
    model (its stamped model and effort) and carries the mark (q's input) exactly when its key is a pieces per-step row; rows added by
    rule carry their family's name and never the mark. Each typed clause is checked against the stamped values; lengths are read from
    the key names."""
    sweep = [r for r in rows if r.src in CURVES and parse_key(r.key)[0] == "models"]
    if not sweep:
        return []
    if any(parse_key(r.key)[0] not in ("models", "pilot1") for r in rows if r.src in CURVES):
        raise ValueError("a length-sweep row is neither a by-length row nor a Pilot 1 marker")
    q_note, q_excl = _q_records(S)
    tags = {parse_key(r.key)[1] for r in sweep}
    if len(tags) != 1 or any(parse_key(r.key)[2] != "by_n" for r in sweep):
        raise ValueError(f"fa4's length-sweep rows are not one model's by-length rows ({sorted(tags)})")
    tag = tags.pop()
    srcs = [s for s in CURVES[::-1] if any(r.src == s for r in sweep)]          # the Deviation 2 file first, where present
    model = {_model_name(S, s, tag) for s in srcs}.pop()
    by_n = join_key("models", tag, "by_n")
    lengths = sorted(S.keys(srcs[0], by_n), key=int)
    q_in: Dict[str, List[str]] = {}
    for src in srcs:
        if sorted(S.keys(src, by_n), key=int) != lengths:
            raise ValueError(f"{src}: the sweep's lengths differ between the two files")
        if not _collapsed(S, src, join_key("models", tag, "q", "ci95")) or \
                any(parse_key(r.key)[:3] == ["models", tag, "q"] for r in rows if r.src == src):
            raise ValueError(f"{src}: q's stamped interval is not zero-width, or fa4 now replaces it: the q clause would be wrong")
        rest = [m for m in S.keys(src, "models") if m != tag]
        if not rest or any(_collapsed(S, src, join_key("models", m, "q", "ci95")) for m in rest):
            raise ValueError(f"{src}: no other model, or another model's q interval is zero-width too: the q clause would be wrong")
        q_in[src] = sorted({parse_key(r.key)[3] for r in sweep if r.src == src and parse_key(r.key)[4:] == ["per_step", "nx1"]},
                           key=int)
        for m in lengths:
            if m not in q_in[src] and _collapsed(S, src, join_key(*parse_key(by_n), m, "per_step", "nx1", "ci95")):
                raise ValueError(f"{src}: q's input at {m} steps is zero-width but not a row: the note would be wrong")
    others = [STUDY1B_TAGS[t][0] for t in STUDY1B_TAGS if STUDY1B_TAGS[t][0] != model]
    marked = []
    for r in rows:
        if "(q's input)" in r.desc and (r.src not in CURVES or parse_key(r.key)[-2:] != ["per_step", "nx1"]):
            raise ValueError(f"{r.desc!r} is marked as q's input, but its key {r.key} is not a pieces per-step row")
    for r in sweep:
        q_input = parse_key(r.key)[4:] == ["per_step", "nx1"]
        if r.i >= n_first:
            if "(q's input)" in r.desc:
                raise ValueError(f"fa4 cell {r.i}: a row added by rule carries the first version's mark (q's input)")
            continue
        if not _names_in(r.desc, model) or any(_names_in(r.desc, o) for o in others):
            raise ValueError(f"fa4 cell {r.i}: {r.desc!r} does not name {model} alone, the stamped model and effort of {r.src}:{tag}")
        if ("(q's input)" in r.desc) != q_input:
            raise ValueError(f"fa4 cell {r.i}: {r.desc!r} is marked as q's input {'(q' in r.desc}, but its key says {q_input}")
        marked += [r] if q_input else []
    if len({tuple(v) for v in q_in.values()}) != 1:
        raise ValueError("q's inputs among the rows differ between the two marking rules: write the note per rule")
    q_rows = q_in[srcs[0]]
    if not q_rows:
        raise ValueError("fa4 has length-sweep rows but none of q's inputs: the length-sweep note would be wrong")
    q_other = [m for m in lengths if m not in q_rows]
    names = lambda ms: _and_list([_key_name(srcs[0], by_n, m) for m in ms])          # noqa: E731
    both = len(srcs) == 2
    note = [q_note, q_excl,
            label("Length sweep: q is a model's per-step accuracy, the share of all its pieces right pooled over the sweep's "
                  "lengths ("), names(lengths),
            label(f" steps), and q to the power N is the reference for a chain of N steps. The length sweep's by-length rows here "
                  f"are all {model}'s, and the inputs of q are its pieces per-step rows (keys ending per_step.nx1), here at "), names(q_rows),
            label(" steps" + (" under both marking rules" if both else "") + ", each over that length's puzzles")]
    if marked:
        note += [label("; the mark (q's input) in a row's name is the first version's own wording, so only its rows carry it (the rows "
                       "added by rule are named by their family, model, measure, length and shape, and their keys show which are inputs "
                       "of q)")]
    if q_other:
        note += [label("; at "), names(q_other), label(" steps their stamped intervals have width, so they are not rows")]
    note += [label(f"; {model}'s q itself, pooled over every length, has a zero-width stamped interval"
                   + (" under each rule" if both else "") + " and no exact interval (the scope note gives free analysis 4's reason), "
                   "while the other models' q intervals have width.")]
    return [[_glue(*note)]]


def _seg_cell(rows: List[_Row], seg: str) -> Cell:
    """A key segment named in the key legend (e.g. '1xn'), printed as the name of a key it ends in one of the rows."""
    for r in rows:
        segs = parse_key(r.key)
        if seg in segs:
            k = join_key(*segs[:segs.index(seg) + 1])
            return Cell(seg, raw=seg, refs=(Ref(seg, r.src, k),), formula="the key name")
    raise ValueError(f"no row's key holds {seg!r}")


def _keys_note(S: Store, rows: List[_Row]) -> List[List[Cell]]:
    """A legend for the stamped keys printed in the main table, one clause per kind of key present (each checked)."""
    segs_of = [(r, parse_key(r.key)) for r in rows]
    allsegs = [s for _, segs in segs_of for s in segs]
    parts: List[Cell] = []
    if any(re.search(r"\d+x\d+", r.key) for r in rows):
        parts.append(label("a shape is written with the letter x, so 6x1 is the shape 6×1"))
    sides = [g for g in ("1xn", "nx1") if g in allsegs]
    if sides:
        words = {"1xn": "the chain", "nx1": "the pieces"}
        cells = [_seg_cell(rows, g) for g in sides]
        parts.append(joined(_and_list(cells), label(("are " if len(sides) > 1 else "is ")
                                                    + " and ".join(words[g] for g in sides) + " at the row's length")))
    if "by_n" in allsegs or any(s.startswith("N=") for s in allsegs):
        # no placeholder letter: the writer sets a bare N in math italic, and "N=N" would read as an identity (Edith, proof 3)
        parts.append(label("the number after 'by_n.' or after 'N=' in a key is the row's length in steps"))
    if "per_step" in allsegs or "whole_answer" in allsegs:
        parts.append(label("per_step is per-step accuracy and whole_answer whole-answer accuracy"))
    tags: Dict[str, None] = {}
    at = False
    for r, segs in segs_of:
        if r.src == "s1b" and segs[:2] == ["descriptive", "arms"]:
            tag, n_steps = segs[2].split("@")
            arm = join_key("descriptive", "arms", segs[2])
            if (S.get("s1b", f"{arm}.tag") != tag or str(S.get("s1b", f"{arm}.N")) != n_steps
                    or S.get("s1b", f"{arm}.effort") != STUDY1B_TAGS[tag][2] or STUDY1B_TAGS[tag][1] not in S.get("s1b", f"{arm}.model")):
                raise ValueError(f"{arm}: its stamped tag, length, model or effort is not what the key legend says")
            tags[tag], at = None, True
        if r.src in CURVES and segs[0] in ("models", "pilot1"):
            tag = segs[1]
            m = join_key("models", tag)
            if S.get(r.src, f"{m}.effort") != STUDY1B_TAGS[tag][2] or STUDY1B_TAGS[tag][1] not in S.get(r.src, f"{m}.model"):
                raise ValueError(f"{r.src}:{m}: its stamped model or effort is not what the key legend says")
            tags[tag] = None
    if tags:
        parts.append(label("a model is written as a tag (" + "; ".join(f"{t}: {STUDY1B_TAGS[t][0]}" for t in tags) + ")"
                           + (", and tag@N is that model at N steps" if at else "")))
    if "points" in allsegs or "curve" in allsegs:
        parts.append(label("points.j and curve.j are a point of a vote curve by its place in the list (its k is in the samples column)"))
    if any(r.src == "s1b" and segs[:2] in (["descriptive", "effort_figure"], ["descriptive", "length_curve"]) for r, segs in segs_of):
        parts.append(label("Study 1b's descriptive.effort_figure and descriptive.length_curve keys are the copies its figures draw of a "
                           "setting, or, under length_curve.ladder, of a length-sweep block, each checked equal to what it copies"))
    own = sorted({segs[-1] for r, segs in segs_of if r.src == "main" and len(segs) > 1 and segs[-2] == "vote_at_own_k"})
    for o in own:
        m = re.fullmatch(r"own k vs (.+)", o)
        if not m or m.group(1) not in STUDY1_ARMS:
            raise ValueError(f"item 24 key {o!r} does not name a comparator arm")
        parts.append(label(f"'{o}' (item 24) is the vote at the row's own cost-matched k against {STUDY1_ARMS[m.group(1)][0]}"))
    for r, segs in segs_of:
        if r.src == "s1b" and segs[0] == "per_form":
            tag = [g for g in S.keys("s1b", f"completeness.{segs[1]}.arms") if STUDY1B_TAGS[g][1] == PER_FORM_SIDE[segs[3]]][0]
            parts.append(joined(text_of(S.ref("fa4", f"{r.base}.key")),
                                label(f"is Test {segs[1]}'s cell on the {shape_word(segs[2])} for its {STUDY1B_TAGS[tag][0]} setting "
                                      "(the test's per-shape breakdown)")))
    p1: Dict[str, _Row] = {}
    for r, segs in segs_of:
        if r.src in CURVES and segs[0] == "pilot1":
            p1.setdefault(r.key, r)
    for k, r in p1.items():
        if len({str(S.get(q.src, f"{k}.label")) for q, _ in segs_of if q.key == k and q.src in CURVES}) != 1:
            raise ValueError(f"{k}: the two length-sweep files stamp different labels")
        parts.append(joined(text_of(S.ref("fa4", f"{r.base}.key")),
                            label("is a Pilot 1 result that the length-sweep files carry beside the sweep, stamped"),
                            _glue(label('"'), text_of(S.ref(r.src, f"{k}.label")), label('"'))))
    if not parts:
        return []
    out: List[Cell] = [label("Keys:")]
    for j, p in enumerate(parts):
        out.append(_glue(p, label(";" if j < len(parts) - 1 else ".")))
    return [out]


# The words of Study 1's reporting definitions for item 9e that the typed 'Item 9e' name rests on (the result file stamps neither the
# model that votes nor which half of the base puzzles the cascade is scored on): the vote is Haiku-medium's samples 1..k_c, the stopping
# value is chosen on the odd base puzzles, and the cascade is scored on the even ones. All three must be in the item's own section.
I9E_DEFS = ("the vote uses Haiku-medium samples **1..k_c by sample index**", "chosen on the **odd** base puzzles (base index odd)",
            "**Scored on the even bases only.**")


def _i9e_basis(S: Store, blocks: Sequence[str]) -> None:
    """The 'Item 9e' name's typed words: each block it prints (shape and k_c) stamps its even and odd base counts and a rule that
    chooses its threshold on the odd bases, and the reporting definitions' item 9e section says that the vote is Haiku-medium's samples
    1..k_c, the threshold is chosen on the odd base puzzles, and the cascade is scored on the even ones."""
    for b in blocks:
        rule = S.get("main", f"{b}.rule")
        if not all(isinstance(S.get("main", f"{b}.{f}"), int) for f in ("even_bases", "odd_bases")) \
                or not re.search(r"\bodd[ -]base", str(rule)):
            raise ValueError(f"{b}: it stamps no even and odd base counts, or a rule that chooses on the odd bases: the 'Item 9e' name's "
                             "words on the even and odd bases would be wrong")
    head, tail = S.find_lines(S1_DEFS.name, r"^### 9e\. "), S.find_lines(S1_DEFS.name, r"^### 9f\. ")
    if len(head) != 1 or len(tail) != 1 or not head[0] < tail[0]:
        raise ValueError(f"{S1_DEFS.name}: item 9e's section is not one section ending where item 9f's begins")
    section = "\n".join(S.doc(S1_DEFS.name).split("\n")[head[0]:tail[0] - 1])
    if not all(w in section for w in I9E_DEFS):
        raise ValueError(f"{S1_DEFS.name}: item 9e's section no longer says {I9E_DEFS}: the 'Item 9e' name's words on the vote and the "
                         "even and odd bases would be wrong")


ITEM24 = ["reporting", "group_b", "item_24"]
ITEM10 = ["reporting", "group_b", "item_10"]


def _item24_label_note(S: Store, rows: List[_Row]) -> List[List[Cell]]:
    """Item 24's own-k votes are item 10's own-k votes, which the main analysis stamps exploratory and TAB-05 prints; the main
    analysis stamps no label for item 24. By Edith's ruling (proof 3, p. 49, option (a): one result, one label) the rows print item
    10's stamped label (`_tier`) and the note points to TAB-05. It is printed only while the stamped values say what it says: each
    row's vote (k, accuracy, cost per puzzle, cost per correct answer) is checked equal to the item 10 vote it names, and the plan's
    TAB-05 lists item 10's own-k votes and opens with them."""
    rows24 = [r for r in rows if r.src == "main" and parse_key(r.key)[:3] == ITEM24]
    if not rows24:
        return []
    for r in rows24:
        segs = parse_key(r.key)
        if r.plan_tier is not None or len(segs) != 7 or segs[3] != "table" \
                or segs[5] != "vote_at_own_k" or not segs[6].startswith("own k vs ") or r.field != "ci95":
            raise ValueError(f"{r.key}: not an item 24 vote at its own k with item 10's label: the item 24 label note would be wrong")
        arm = segs[4]
        twin = join_key(*ITEM10, "arms", arm, "own_k", "vs " + segs[6][len("own k vs "):])
        mine = r.key
        pairs = ((f"{mine}.k", f"{twin}.k_value.k"), (f"{mine}.mean", f"{twin}.vote_mean"),
                 (f"{mine}.cost_per_puzzle", f"{twin}.cost_per_puzzle"), (f"{mine}.cpc", f"{twin}.cpc"))
        if any(S.get("main", a) != S.get("main", b) for a, b in pairs):
            raise ValueError(f"{r.key} is not the vote that {twin} stamps (k, accuracy, cost): the item 24 label note would be wrong")
    entries = S.get("plan", "plan.tables_figures")
    plan = {e["id"]: e for e in entries}
    if not str(plan["TAB-05"]["content"]).startswith("Own-k votes") or "own_k" not in plan["TAB-05"]["source_keys"]:
        raise ValueError("the plan's TAB-05 is no longer item 10's own-k votes: the item 24 label note would be wrong")
    stamped = S.ref("main", join_key(*ITEM10, "label"))
    if not str(stamped.value).startswith("exploratory"):
        raise ValueError("item 10's stamped label is no longer exploratory: the item 24 label note would be wrong")
    if len(rows24) != 2 or S.has("main", join_key(*ITEM24, "label")):
        raise ValueError("item 24 has other than two cells here, or stamps a label of its own: re-read the item 24 label note")
    return [[label("Item 24: its two rows are item 10's own-k votes (checked equal in k, accuracy and cost), and the main analysis "
                   "stamps no label for item 24, so they carry item 10's stamped label,"), _glue(label('"'), text_of(stamped), label('",')),
             label("as ⟦TAB-05⟧ prints them.")]]


def _names_note(S: Store, rows: List[_Row], pairs: bool) -> List[List[Cell]]:
    descriptions = [r.desc for r in rows]
    names = []
    if any(_names_in(d, "Item 7") for d in descriptions):
        names.append("Item 7 is a Study 1 reporting item, per-piece accuracy: the share of a sample's pieces that are right, averaged "
                     "over the puzzle's designed samples and then over puzzles")
    i9e = [r for r in rows if r.src == "main" and parse_key(r.key)[:4] == I9E]
    if i9e:
        by_shape: Dict[str, set] = {}
        for r in i9e:
            segs = parse_key(r.key)
            if (len(segs) != 7 or segs[6] != "even" or not segs[5].isdigit() or r.field != "opus_accuracy_ci95"
                    or S.get("main", f"{r.key}.bootstrap_name") != f"cascade:{segs[4]}:{segs[5]}"):
                raise ValueError(f"{r.key}: not item 9e's Opus-medium accuracy on the even bases of the cascade it names: the 'Item 9e' name "
                                 "would be wrong")
            by_shape.setdefault(segs[4], set()).add(S.get("main", f"{r.key}.{r.point}"))
        _i9e_basis(S, sorted({join_key(*parse_key(r.key)[:6]) for r in i9e}))
        stamped = str(S.get("main", "reporting.group_b.item_9e.label"))
        if any(len(v) != 1 for v in by_shape.values()) or "escalate-to-Opus cascade" not in stamped or "offline" not in stamped:
            raise ValueError("item 9e's Opus-medium accuracy differs between its k_c rows, or its stamped label is no longer the offline "
                             "escalate-to-Opus cascade: the 'Item 9e' name would be wrong")
        names.append("Item 9e is a Study 1 reporting item, the offline escalate-to-Opus cascade: its key ends in the number of "
                     "Haiku-medium samples in the cascade's vote (k_c) and then even, the even-indexed puzzles, where the cascade is "
                     "scored; Opus-medium's accuracy there is one estimate, the same for every k_c, so these rows repeat it")
    if pairs:
        names.append("C10 is the keep-list analysis of the paired difference in single-sample accuracy between two effort levels "
                     "of one model")
    if any(r.tries_kind == "vote" for r in rows):
        names.append("a vote of k samples scores one answer per puzzle from those samples; a vote-curve point is the vote "
                     "at one k")
    pooled = [r for r in rows if re.search(r"\bpooled\b", r.desc) or parse_key(r.key)[-1] == "pooled"]
    for r in pooled:
        segs = parse_key(r.key)
        sweep = r.src in CURVES and segs[0] == "models" and segs[2] == "by_n" and segs[4] in ("per_step", "whole_answer")
        ladder = r.src == "s1b" and segs[:3] == ["descriptive", "length_curve", "ladder"]
        if segs[-1] != "pooled" or not (sweep or ladder):
            raise ValueError(f"{r.src}:{r.key}: a pooled row that is not a length-sweep block: the 'pooled' name would be wrong")
        nx1 = join_key(*segs[:-1], "nx1")
        if S.get(r.src, f"{r.key}.n_base") != S.get(r.src, f"{nx1}.n_base"):
            raise ValueError(f"{r.src}:{r.key}: pooled over other base puzzles than the pieces: the 'pooled' name would be wrong")
    if pooled:
        names.append("'pooled' in a row name or key means both shapes together, each puzzle counted once, not pooled over "
                     "lengths")
    if any(re.search(r"\bchains\b", d) for d in descriptions):
        names.append("'chains' is the chain shape")
    return [[label("Names: " + "; ".join(names) + ".")]] if names else []


def _fig02_bars(S: Store) -> List[str]:
    """The stamped keys of FIG-02's bars, chosen as FIG-02 chooses them: per item 20 shape and bin, each agreement third it stamps (t1
    to t3) and, where stamped, the bin's 'too few wrong tries' group, each at its largest k (the last entry of mean_vote_at_k)."""
    out: List[str] = []
    for sh in S.keys("main", join_key(*I20)):
        if not S.has("main", join_key(*I20, sh, "bins")):
            continue
        for b in S.keys("main", join_key(*I20, sh, "bins")):
            base = [*I20, sh, "bins", b]
            thirds = S.keys("main", join_key(*base, "thirds"))
            groups = [["thirds", t] for t in ("t1", "t2", "t3") if t in thirds] + ([[FEW]] if S.get("main", join_key(*base, FEW)) else [])
            for g in groups:
                votes = join_key(*base, *g, "mean_vote_at_k")
                out.append(join_key(*base, *g, "mean_vote_at_k", len(S.get("main", votes)) - 1))
    return out


def _item20_panel(S: Store, rows20: List[_Row]) -> Table:
    """Item 20's cells in compact columns: the FIG-02 bars whose bootstrap interval collapsed, counted against all of FIG-02's bars
    (recounted here: the collapsed bars are exactly these cells). The words are checked: k is item 20's largest k and Haiku-medium's
    designed tries per puzzle; every puzzle of a bin has its single-try accuracy inside the bin's stamped range; the thirds are in
    order of stamped agreement share; the 'too few wrong tries' puzzles are that group; each third stamps a bootstrap."""
    cols = ["Shape", "Haiku-medium single-sample accuracy bin (%)", "Agreement third", PUZZLES_RIGHT_PANEL,
            "Exact 95% accuracy interval, Clopper–Pearson (%, post hoc)"]
    fams = {S.get("fa4", f"{r.base}.family") for r in rows20}
    ks = {S.get("main", f"{r.key}.k") for r in rows20}
    if len(fams) != 1 or len(ks) != 1:
        raise ValueError(f"item 20's fa4 cells are not one family at one k ({sorted(fams)}, {sorted(ks)})")
    k, fam = ks.pop(), fams.pop()
    if k != S.get("main", join_key(*parse_key(ITEM7_ARMS), "haiku-med", "designed_tries")) or not re.search(rf"\bk = {k}\b", fam):
        raise ValueError("item 20's k is not Haiku-medium's tries per puzzle, or not the k fa4's family names: the panel note is wrong")
    rows: List[List[Cell]] = []
    bins: Dict[Tuple[str, str], None] = {}
    for r in rows20:
        segs = parse_key(r.key)
        sh, b = segs[3], segs[5]
        third = segs[7] if segs[6] == "thirds" else segs[6]
        block = segs[:8] if segs[6] == "thirds" else segs[:7]
        if segs[4] != "bins" or len(segs) != len(block) + 2 or third not in THIRD_WORDS or \
                not S.has("main", join_key(*block, "bootstrap_name")):
            raise ValueError(f"fa4 cell {r.i}: {r.key} is not a bootstrap cell of an item 20 bin and third")
        bins[(sh, b)] = None
        bk = join_key(*segs[:6])
        elo, ehi = ci_refs(S, "fa4", f"{r.base}.exact95")
        rows.append([label(shape(sh)), Cell(b, raw=b, refs=(Ref(b, "main", bk),), formula="the key name"), label(THIRD_WORDS[third]),
                     joined(integer(S.ref("fa4", f"{r.base}.x")), label("of"), integer(S.ref("fa4", f"{r.base}.n"))),
                     interval(elo, ehi, dp=2, scale=r.scale, bounds=(0.0, 100.0))])
    for sh, b in bins:
        pp = S.get("main", join_key(*I20, sh, "per_puzzle"))
        m = re.fullmatch(r"\[(\d+),(\d+)([\])])", b)
        if not m:
            raise ValueError(f"item 20 bin {b!r} is not a stamped range")
        lo_e, hi_e, closed = int(m.group(1)), int(m.group(2)), m.group(3) == "]"
        thirds = S.get("main", join_key(*I20, sh, "bins", b, "thirds"))
        few = S.get("main", join_key(*I20, sh, "bins", b, FEW))
        prev = None
        for t in ("t1", "t2", "t3"):
            if t not in thirds:
                continue
            ps = thirds[t]["puzzles"]
            if any(pp[p]["third"] != t or pp[p]["bin"] != b for p in ps):
                raise ValueError(f"item 20 {sh} {b} {t}: a puzzle stamped in another third or bin")
            if prev is not None and min(pp[p]["agreement_share"] for p in ps) < prev:
                raise ValueError(f"item 20 {sh} {b}: the thirds are not in order of agreement: 'lowest/highest third' would be wrong")
            prev = max(pp[p]["agreement_share"] for p in ps)
        members = [p for t in thirds.values() for p in t["puzzles"]] + (list(few["puzzles"]) if few else [])
        if few and any(pp[p]["group"] != FEW for p in few["puzzles"]):
            raise ValueError(f"item 20 {sh} {b}: a 'too few wrong tries' puzzle is not in that group")
        acc = [pp[p]["accuracy_points"] for p in members]
        if len(members) != S.get("main", join_key(*I20, sh, "bins", b, "puzzles")) or \
                not all(lo_e <= a and (a <= hi_e if closed else a < hi_e) for a in acc):
            raise ValueError(f"item 20 {sh} {b}: a puzzle's single-sample accuracy is outside its bin, or the bin's count is off")
    k_cell = integer(S.ref("main", f"{rows20[0].key}.k"))
    has_few = any(parse_key(r.key)[6] == FEW for r in rows20)
    left_out = [e for e in S.get("fa4", "result.excluded") if e["what"].startswith("main: item 20 at k below")]
    bars = _fig02_bars(S)
    if sorted(k for k in bars if _collapsed(S, "main", f"{k}.ci95")) != sorted(r.key for r in rows20) or len(set(bars)) != len(bars) \
            or len(bars) == len(rows20):
        raise ValueError("item 20's fa4 cells are not exactly the FIG-02 bars whose interval collapsed, or every bar collapsed: the "
                         "panel's count and its 'other bars' would be wrong")
    n_rows = Cell(f"{len(rows20):,}", raw=len(rows20), refs=tuple(S.ref("fa4", f"{r.base}.key") for r in rows20),
                  formula="count of free analysis 4's item 20 cells (the FIG-02 bars whose stamped interval has zero width)")
    n_bars = Cell(f"{len(bars):,}", raw=len(bars), refs=tuple(S.ref("main", f"{k}.ci95") for k in bars),
                  formula="count of FIG-02's bars: item 20's stamped agreement thirds and 'too few wrong tries' groups per shape "
                          "and bin, each at its largest k")
    notes = [
        [label("Item 20 (Study 1, main run): the FIG-02 bars whose stamped bootstrap interval collapsed,"), n_rows,
         label("of FIG-02's"), _glue(n_bars, label(";")), label("each is the Haiku-medium vote at k ="), k_cell,
         label("(its largest k: all of a puzzle's samples) over the puzzles of one single-sample accuracy bin and one agreement third"
               + (" (or the bin's \"too few wrong samples\" group)" if has_few else "")
               + "; FIG-02's other bars keep stamped intervals with width and are not here, and free analysis 4 names these cells"),
         _glue(label('"'), text_of(S.ref("fa4", f"{rows20[0].base}.family")), label('".'))],
        [label("Each cell's stamped bootstrap interval has zero width, because every puzzle in it was right, or every one wrong (the "
               "count right out of the cell's puzzles says which); the exact interval replaces it. Agreement thirds split a bin's puzzles "
               "by how often their wrong samples "
               "repeat each other, lowest first"
               + ("; \"too few wrong samples\" holds the puzzles with too few wrong samples to be placed in a third" if has_few else "")
               + ".")],
        [label("Labels: each stamped interval keeps the plan's label for FIG-02, which draws it (the main analysis stamps no label for "
               "item 20):"), _glue(_plan_tier(S, *PLAN_TIERS[("main", "item_20")][:2]), label(";")),
         label("the counts and the exact intervals are"),
         _glue(text_of(S.ref("fa4", "definition.tier_label")), label(".")), label("Samples per puzzle:"), k_cell,
         label("(the vote's k); a puzzle counts once in the count of puzzles right.")]]
    if left_out:
        notes.append([label("Item 20's cells at smaller k are left out of free analysis 4 (the scope note gives its count and "
                            "reason).")])
    # a longtable (54 rows beside narrow columns: taller than a page, fits the text width); each bin (its thirds) is a group
    return Table([label(c) for c in cols], rows, notes, layout="longtable",
                 groups=[i for i in range(1, len(rows)) if rows[i][:2] != rows[i - 1][:2]])


@output("TAB-26")
def tab_26(S: Store) -> Table:
    cols = ["What it is", "Study or run", "Stamped key (of the collapsed interval; its field name follows where it is not ci95)",
            "Label of the stamped interval (from its source; see the labels note)",
            "Stamped bootstrap 95% accuracy interval (%)", "Stamped bootstrap 95% interval of a paired difference (points)",
            "Samples per puzzle (a\u00a0vote: its\u00a0k)", PUZZLES_RIGHT,
            "Exact 95% accuracy interval, Clopper–Pearson (%, post hoc)"]
    for v in [*SOURCE_NAMES.values(), *PILOT1_NAMES.values(), PANEL, FA4_RULE_WORDS]:
        label(v)                                                       # the printed study names, panel title and rule hold no typed number
    if "study1b-1" not in S.get("fa2", "definition.inputs"):
        raise ValueError("free analysis 2 no longer reads Study 1b's samples: its printed study name would be wrong")
    cells = S.get("fa4", FA4)
    n_r2 = S.get("fa4", R2)
    if n_r2 + S.get("fa4", ADDED) != len(cells):
        raise ValueError("fa4's revision 2 and added counts do not sum to its cells: the scope note would be wrong")
    n_first = next((j for j, cd in enumerate(cells) if "family" in cd), len(cells))     # the first version's cells carry no family
    if not 0 < n_first < n_r2 or any("family" not in cd for cd in cells[n_first:]):
        raise ValueError("fa4's cells with no family are not a first-version run at the start of revision 2's cells: the scope note "
                         "would be wrong")
    placed: List[Tuple[Tuple, List[Cell], _Row]] = []                 # (order, cells, row) of the main table
    swapped = {"names": False, "keys": False}                          # whether a row's name was reworded or a key was quoted
    unreported: List[int] = []                                         # revision 3's 90% cells, checked and counted, never printed
    fam_first: Dict[str, int] = {}
    for i, cd in enumerate(cells):
        fam_first.setdefault(cd.get("family", ""), i)
    rows20: List[_Row] = []                                             # item 20's, for the panel
    pairs: Dict[str, Tuple[int, str, str, str]] = {}                   # pair key -> (first fa4 cell, arm a, arm b, shape)
    for i, cd in enumerate(cells):
        c = f"{FA4}.{i}"
        path, plain = cd["source"], cd["key"]
        key = _ledger_key(plain, i)
        src = _source_name(S, path)
        if src not in SOURCE_NAMES:
            raise ValueError(f"fa4 cell {i}: source {src} has no study or run name to print")
        field, point, pct = _cell_spec(cd, i, n_r2)
        if field == UNREPORTED_FIELD:
            _check_unreported(S, i, cd, field, point, pct)
            unreported.append(i)
            continue
        if field not in ROW_FIELDS:
            raise ValueError(f"fa4 cell {i}: the interval field {field!r} is neither one the rows print ({ROW_FIELDS}) nor the one not "
                             f"reported ({UNREPORTED_FIELD}): the scope note would not name it")
        if i >= n_first:
            _check_family(S, i, path, plain, field)
        scale = UNIT_SCALE[cd["unit"]]
        lo, hi = ci_refs(S, src, f"{key}.{field}")                  # the collapsed interval, from the original file
        if [lo.value, hi.value] != cd[f"stamped_ci{pct}"] or lo.value != hi.value:
            raise ValueError(f"fa4 cell {i}: {src}:{key}.{field} {[lo.value, hi.value]} is not fa4's collapsed copy")
        is_pair = S.has(src, f"{key}.d") and S.has(src, f"{key}.accuracy_means")
        if is_pair and field != "ci95":
            raise ValueError(f"fa4 cell {i}: a paired difference stamped under {field!r}: the C10 note below would be wrong")
        r = _Row(i, c, src, key, cd["cell"], cd["x"], cd["n"], scale, pair=is_pair, field=field, point=point, pct=pct)
        _check_counts(S, r, cd.get("n_key"))
        arm: Optional[str] = None
        if is_pair:
            desc, note = r.desc, cd["note"]
            if note is None or parse_key(key)[0] != "item_C10" or not _names_in(desc, "C10"):
                raise ValueError(f"fa4 cell {i}: a paired difference that is not a noted C10 row: the C10 note below would be wrong")
            a, b, sh = _pair(S, src, key, i)
            arms = [x_ for x_ in (a, b) if _names_in(desc, STUDY1_ARMS[x_][0])]
            if len(arms) != 1 or not _names_in(desc, shape_word(sh)):
                raise ValueError(f"fa4 cell {i}: {desc!r} does not name exactly one of {a}, {b} and the shape {sh}")
            arm = arms[0]
            if not math.isclose(100.0 * r.x / r.n, float(S.get(src, f"{key}.accuracy_means.{arm}")), abs_tol=1e-9):
                raise ValueError(f"fa4 cell {i}: {r.x} of {r.n} is not {arm}'s stamped accuracy at {key}")
            if cd["unit"] != "points" or S.get(src, f"{key}.unit") != "points":
                raise ValueError(f"fa4 cell {i}: the paired difference is not stamped in points")
            pairs.setdefault(key, (i, a, b, sh))
            acc_cell, diff_cell = DASH, interval(lo, hi, dp=2, signed=True, bounds=(0.0,))
        else:
            if cd["note"] is not None:
                raise ValueError(f"fa4 cell {i} carries a note but is not a paired difference: its note would be dropped")
            fc = fa4_exact(S, src, key, field=field)                   # the shared lookup finds this very cell
            if fc is None or fc.base != c or (fc.x, fc.n, fc.scale) != (r.x, r.n, scale):
                raise ValueError(f"fa4 cell {i}: core.fa4_exact does not find it for {src}:{key} ({field})")
            acc_cell, diff_cell = interval(lo, hi, dp=2, scale=scale, bounds=(0.0, 100.0)), DASH
        tries, r.tries_kind = _tries(S, r, arm, cd.get("n_key"))
        tier, r.plan_tier = _tier(S, src, key, i)
        if src == "main" and parse_key(key)[:3] == I20:
            rows20.append(r)
            continue
        elo, ehi = ci_refs(S, "fa4", f"{c}.exact{pct}")
        # first-version cells in fa4's order; then each added family in fa4's order, its keys in natural order (lengths as numbers)
        order = (0, i) if i < n_first else (1, fam_first[cd["family"]],
                                            tuple((0, int(g), "") if g.isdigit() else (1, 0, g) for g in parse_key(key)))
        study = SOURCE_NAMES[src]
        if src in CURVES and parse_key(key)[0] == "pilot1":
            if not str(S.get(src, join_key(*parse_key(key), "label"))).startswith("pilot-1,"):
                raise ValueError(f"fa4 cell {i}: {src}:{key} is not stamped as a Pilot 1 result: its study would be wrong")
            study = PILOT1_NAMES[src]
        key_cell = text_of(S.ref("fa4", f"{c}.key"), {plain: key})
        if _retired(key):                                                # a stamped key holds a retired word: printed as stamped, quoted
            key_cell = _quoted(key_cell)
            swapped["keys"] = True
        if field != "ci95":                                              # a field named other than ci95 is printed beside its key
            key_cell = joined(key_cell, _glue(label("(field "), text_of(S.ref("fa4", f"{c}.field")), label(")")))
        row_name = _plain_name(S.ref("fa4", f"{c}.family" if i >= n_first else f"{c}.cell"))
        if i >= n_first and r.src in CURVES and parse_key(key)[0] == "models":
            row_name = _sweep_row_name(S, r, row_name)
        swapped["names"] = swapped["names"] or row_name.printed != row_name.raw
        placed.append((order, [row_name,
                               text_of(S.ref("fa4", f"{c}.source"), {path: study}),
                               key_cell, tier, acc_cell, diff_cell, tries,
                               joined(integer(S.ref("fa4", f"{c}.x")), label("of"), integer(S.ref("fa4", f"{c}.n"))),
                               interval(elo, ehi, dp=2, scale=scale, bounds=(0.0, 100.0))], r))
    placed.sort(key=lambda t: t[0])
    rows = [cells_ for _, cells_, _ in placed]
    kept = [r for _, _, r in placed]
    if not rows20:
        raise ValueError("fa4 has no item 20 cells: the scope note's item 20 panel would not exist")
    if {r.src for r in kept + rows20} != CAPTION_SOURCES:
        raise ValueError(f"the rows' studies {sorted({r.src for r in kept + rows20})} are not the caption's")
    printed = sorted(r.i for r in kept + rows20)
    if sorted(printed + unreported) != list(range(len(cells))) or not unreported:
        raise ValueError("fa4's cells are not exactly the rows, the panel's rows and the cells not reported: one would be dropped or "
                         "printed twice")

    method = S.get("fa4", "result.method")
    if not all(s in method for s in ("clopper_pearson(x, n)", "two-sided 95%", "over base puzzles")):
        raise ValueError(f"fa4's stamped method {method!r} no longer says what the typed method line says")
    tier = text_of(S.ref("fa4", "definition.tier_label"))
    notes = [[label("Each stamped bootstrap interval has zero width because every puzzle in the cell was right, or every one "
                    "wrong; the exact interval replaces it. Nothing here is a test, and nothing here changes a pre-registered "
                    "reading.")],
             [label("Exact interval: the two-sided 95% Clopper–Pearson interval for the puzzles right out of the cell's puzzles, with the "
                    "puzzle as the unit (the conservative unit: a puzzle with several samples, or a vote, counts once). It counts "
                    "puzzles, not samples.")],
             *_scope(S, n_first, n_r2, unreported, printed, set(pairs))]
    for key, (i, a, b, sh) in sorted(pairs.items(), key=lambda kv: kv[1][0]):
        note_c10 = text_of(S.ref("fa4", f"{FA4}.{i}.note"))
        diff = (f"The difference is {STUDY1_ARMS[a][0]} minus {STUDY1_ARMS[b][0]} on {shape_word(sh)}, in points, and is shown in its "
                "own column; a difference has no exact counterpart.")
        if _retired(note_c10.printed):                      # a stamped sentence that holds a retired word: quoted as stamped, glossed
            if not re.search(r"\barms?\b", note_c10.printed) or sum(len(rx.findall(note_c10.printed)) for rx, _ in karen_vocab()) != 1:
                raise ValueError("fa4's C10 note holds a retired word other than 'arm': the gloss below would be wrong")
            notes.append([label("C10 rows:"), _quoted(note_c10), label("(free analysis 4's note, where its \"arm\" is a setting). " + diff)])
        else:
            notes.append([label("C10 rows:"), _glue(note_c10, label(".")), label(diff)])
    notes += _sweep_note(S, kept, n_first)
    srcs = {r.src for r in kept}
    pilot1 = any(r.src in CURVES and parse_key(r.key)[0] == "pilot1" for r in kept)
    clauses = (["for Study 1b's descriptive blocks, the block's name"] if any(r.src == "s1b" and r.plan_tier is None for r in kept) else []) \
        + (["for the length sweep, its stamped plan line"] if any(r.src in CURVES and parse_key(r.key)[0] != "pilot1" for r in kept)
           else []) \
        + ([f"for the Pilot 1 markers the length-sweep files carry, {PILOT1_TIER}, the label the plan gives Pilot 1's 24-step markers "
            "(they ran before Lock 2, with a different rule mix, sets and timing)"] if pilot1 else []) \
        + (["for free analysis 2, its stamped label"] if "fa2" in srcs else [])
    plan_used = sorted({r.plan_tier for r in kept + rows20 if r.plan_tier})
    text = "each stamped interval keeps its source's label, given in its own column: the source's stamped label"
    text += (" (" + "; ".join(clauses) + ")") if clauses else ""
    if plan_used:
        text += (", or, where the source stamps none, the plan's label for the output that reports it ("
                 + "; ".join(f"{oid} for {words}" for oid, words in plan_used) + ")")
    text += (". Samples per puzzle: a vote row gives its k, the samples it votes over; a row with several single samples averages "
             "over them; either way the puzzle counts once in the count of puzzles right")
    if any(r.tries_kind == "unstamped" for r in kept):
        text += "; a Pilot 1 marker's samples are not stamped in the length-sweep files"
    notes.append([label("Labels: the counts and the exact intervals are"), _glue(tier, label(";")), label(text + ".")])
    notes += _item24_label_note(S, kept)
    notes += _names_note(S, kept, bool(pairs))
    notes += _keys_note(S, kept)
    if swapped["names"] or swapped["keys"]:
        notes.append([label("Words: " + ("each row's description is free analysis 4's own, in this paper's words where it used a word "
                                         "or a form of a name this paper no longer uses (setting for \"arm\", sample for \"try\", puzzle for \"base "
                                         "puzzle\", cost-matched for \"equal-money\", \"Haiku, thinking off\" for \"Haiku thinking-off\", \"-sample "
                                         "vote\" after a vote's k for \"vote@k\"), each name starting with a capital, and a length-sweep row added by rule "
                                         "named in full from its key (its family, then the model, measure, length and shape)"
                                         if swapped["names"] else "")
                            + ("; " if swapped["names"] and swapped["keys"] else "")
                            + ("a stamped key that holds such a word is printed as stamped, in quotation marks"
                               if swapped["keys"] else "") + ".")])
    notes.append([label("Values stamped as shares are printed in %.")])
    caption = _caption(
        [tier, label("for the counts and the exact intervals; each stamped interval keeps its source's label (its own column)")],
        "Study 1 (main run and keep-list analyses), Study 1b and free analysis 2 (on Study 1b's samples), the top-up run, and the length "
        "sweep under both marking rules" + (", with the Pilot 1 markers its files carry beside the sweep" if pilot1 else "")
        + "; each row within its own study, never pooled across studies or lengths",
        [label("each row's own study, puzzle set and length (both shapes together where its key says pooled), identified by its study "
               "or run and its stamped key")],
        [label("the puzzles right out of the cell's puzzles, per row, with the samples per puzzle in its own column; a puzzle with "
               "several samples, or a vote, counts once (the conservative unit)")],
        [label("stamped: bootstrap, collapsed to zero width; replacement: exact two-sided 95% Clopper–Pearson")],
        "not applicable (no cost column)")
    # the item 20 panel is part of the table (Edith, proof 3, p. 41): the caption says what it holds
    # (the rows are not "the other collapsed intervals": the scan finds more than the rows and the panel hold, so the fact says which
    # ones the rows are and where the rest are given; Edith, proof 3, p. 41)
    caption["panel"] = [label("a panel gives item 20's collapsed bars of FIG-02, each with its exact interval (the table's rows are the "
                              "other collapsed intervals within free analysis 4's scope; the notes give those left out and those not "
                              "reported)")]
    t = Table([label(c) for c in cols], rows, notes, caption, layout="split landscape", font="footnotesize")
    # Row groups (Edith §7.7): the first version's named rows are one group; after them each added family is a group, found where the
    # row's family changes: the stamped family string (the name cell's raw value), not the printed name, because each length-sweep row
    # prints its own full name (proof 4, p. 44) while the rows of one family are still one group. A Pilot 1 marker stays with the
    # length sweep it is carried beside (it follows that sweep's rows).
    n_head = sum(1 for r in kept if r.i < n_first)
    if not 0 < n_head < len(rows) or any(r.i >= n_first for r in kept[:n_head]):
        raise ValueError("the first version's rows are not the first rows of the table: the row groups would be wrong")

    def _pilot1(r: _Row) -> bool:
        return r.src in CURVES and parse_key(r.key)[0] == "pilot1"
    t.groups = [n_head] + [i for i in range(n_head + 1, len(rows))
                           if rows[i][0].raw != rows[i - 1][0].raw and not _pilot1(kept[i])]
    # Four row chunks, each in two column groups, so every part fits a sideways page: the first column group says where an interval
    # comes from (study or run, label), the second gives the interval, its samples and its exact replacement. Every part repeats the
    # description and the stamped key: the description alone is the same on many rows (a family), the pair is unique, so a row of a
    # number part can be matched to its key; the two parts of a chunk follow each other. The chunks are by row count (Edith, proof 3,
    # pp. 43-44: the earlier chunks, which broke at each marking rule of the length sweep, left one sideways page 33% and another 52%
    # filled, against section 1.4's 60%): the first version's rows, then three chunks of 14, 14 and 13 rows (proof 4: the longer row names of
    # the length sweep's rows and the longer "puzzles right" header made the 15-row chunk 6.8 in tall), measured at the paper's sideways
    # page with the printed captions (every part fills at least 60% of it and none is taller than 6.3 in of its 6.5, §5.4's 0.17 in
    # spare). A change in the row count refuses the build, so that the chunks are measured again.
    sizes = (n_head, 14, 14, 13)
    if sum(sizes) != len(rows):
        raise ValueError(f"TAB-26 has {len(rows)} rows, with {n_head} first-version rows: re-measure the four row chunks {sizes}")
    cut = [sum(sizes[:i]) for i in range(len(sizes) + 1)]
    if len({(r[0].printed, r[2].printed) for r in rows}) != len(rows):
        raise ValueError("a description and a stamped key do not identify a row: the number parts could not be matched to their rows")
    t.split_key = [0, 2]
    ident, numbers = [1, 3], [4, 5, 6, 7, 8]
    t.split_parts = [(list(range(a, b)), cols_) for a, b in zip(cut, cut[1:]) for cols_ in (ident, numbers)]
    t.panels = [(PANEL, _item20_panel(S, rows20))]
    return t


# ================================================================ TAB-27

MARGIN_KEY = "result.margin"
# Study 1's reporting definitions as stamped before any result was opened (the analysis stamp's definitions commit, 93334b8, the last
# change on main; this module's own name, so that its pin does not depend on another module's): item 1 defines the error-rate ratio for
# each of the five tests, the evidence for its tier, "pre-specified descriptive, reported beside the test" (Edith's Q14 ruling).
S1_DEFS = register_source(Source("fa_checks_s1_defs", "research/reporting-definitions-main.md", "93334b8",
                                 "bddab72761b4111f6d4ed439f13ddbd63427bc14a9c61b58d0ceadb32f18bf81", kind="text",
                                 what="Study 1's reporting definitions: item 1, the error-rate ratio, for each of the five tests"))
ER_TIER = "pre-specified descriptive, reported beside the test"
# A stamped reading of the pre-registered decision rule in the paper's words (Edith's ruling C, D-161: the Method's three outcomes
# "shown no worse by > margin (Holm-adjusted)", "worse by > margin" and "inconclusive"); every reading the file can stamp must have one.
# The stamped "non-inferior" is printed as the passed test it records; the stamped label stays the cell's raw value.
READING_WORDS = {"non-inferior": "shown no worse by > margin (Holm-adjusted)",
                 "worse by more than the margin": "worse by > margin", "inconclusive": "inconclusive"}


def _reading(S: Store, key: str) -> Cell:
    """A test's stamped reading under the pre-registered decision rule, printed in the paper's words (the stamped label stays the cell's
    raw value). A stamped "non-inferior" is the Holm-adjusted outcome only while the test's own `declared` flag says it passed."""
    ref = S.ref("main", key)
    parent = key.rsplit(".", 1)[0]
    if (ref.value == "non-inferior") != (S.get("main", f"{parent}.declared") is True):
        raise ValueError(f"{key}: a passed reading is not the test's Holm-adjusted one (its `declared` flag): the cell's "
                         "'(Holm-adjusted)' would be wrong")
    return text_of(ref, READING_WORDS)


def _er_tier(S: Store) -> None:
    """ER_TIER's evidence: the reporting definitions' item 1 is the error-rate ratio, defined for each of the five tests that ran, and
    the result file stamps one for each of them."""
    def one(pattern: str) -> int:
        hits = S.find_lines(S1_DEFS.name, pattern)
        if len(hits) != 1:
            raise KeyMissing(f"{S1_DEFS.name}: {len(hits)} lines match {pattern!r}")
        return hits[0]
    head = one(r"^## 1\. The error-rate ratio$")
    which = one(r"^\*\*Which tests\.\*\* Each of the five tests that ran \(k ≥ 1\), in the as_deployed view\.$")
    nxt = one(r"^## 2\. ")
    if not head < which < nxt or sorted(S.keys("main", "reporting.error_ratios")) != sorted(STUDY1_TESTS):
        raise ValueError("the error-rate ratio's tier wording no longer fits the reporting definitions or the result file")


def _error_ratio(S: Store, test: str) -> Cell:
    """The error-rate ratio with its 95% interval, as in TAB-02; Test 1's is undefined (0 comparator errors) and is printed with the
    comparator's stamped note and its exact upper error rate, to 2 decimals (the precision TAB-26 gives the same exact interval, as
    the ledger's 4.51% wording does)."""
    e = f"reporting.error_ratios.{test}"
    if not S.get("main", f"{e}.defined"):
        if S.get("main", f"{e}.comparator_interval") != "clopper-pearson":
            raise ValueError(f"{e}: the comparator's bound is not stamped as exact: the typed 'exact' would be wrong")
        return joined(text_of(S.ref("main", f"{e}.defined"), {False: "undefined"}),
                      _glue(label("("), text_of(S.ref("main", f"{e}.comparator_note")), label(";")),
                      label("its error rate at most"),
                      _glue(pct(S.ref("main", f"{e}.comparator_error_rate_upper95"), dp=2), label(", exact 95%)")))
    lo, hi = ci_refs(S, "main", f"{e}.ci95")
    return joined(num(S.ref("main", f"{e}.R"), dp=2), interval(lo, hi, dp=2))



def _p_locked(S: Store, t: str, p: Ref, complement: bool = False) -> Cell:
    """A Study 1 test's locked one-sided p (or free analysis 5's inferiority p, 1 minus it, with complement=True) at 5 places, or "≤"
    its bootstrap floor rounded up when no resample reached the margin (core.pvalue_bound, from the locked test's stamped z0, a and B;
    free analysis 5 reuses that same bootstrap and checks the locked p equal)."""
    tk = f"{VIEW}.tests.{t}"
    return pvalue_bound(p, S.ref("main", f"{tk}.z0"), S.ref("main", f"{tk}.a"), S.ref("main", f"{VIEW}.B"), dp=5, complement=complement)

@output("TAB-27")
def tab_27(S: Store) -> Table:
    if sorted(S.keys("fa5", FA5)) != sorted(STUDY1_TESTS):
        raise KeyMissing(f"fa5 tests {sorted(S.keys('fa5', FA5))} are not Study 1's five")
    _er_tier(S)
    margin = float(S.get("fa5", MARGIN_KEY))
    if margin != float(S.get("main", f"{VIEW}.margin")):
        raise ValueError("fa5's margin is not the locked margin")
    # note 2 says the inferiority p's bootstrap has the locked test's differences, seeds and B (and prints B, so that the symbol is
    # followed by its value): refused unless fa5's B is the locked test's
    if S.get("fa5", "code.B") != S.get("main", f"{VIEW}.B"):
        raise ValueError("fa5's B is not the locked test's B: note 2's 'the same bootstrap, B = ...' would be wrong")
    ns = {t: S.get("main", f"{VIEW}.tests.{t}.n") for t in STUDY1_TESTS}
    if len(set(ns.values())) != 1:
        raise ValueError(f"the five tests' n differ ({ns}): the caption's one n per test would be wrong")
    cols = ["Test", "Shape", "Challenger", "Comparator", "d (points)", "95% interval (unadjusted)",
            "Error-rate ratio (challenger's over comparator's, 95% interval)",
            "Reading (pre-registered decision rule)", "Locked p (one-sided)",
            "Inferiority p, one minus the locked p (post hoc)", "Holm threshold, inferiority direction (post hoc)",
            "Inferiority p below its Holm threshold (post hoc)", "Stricter interval (post hoc)",
            "Stricter interval wholly below the margin (post hoc)"]
    rows: List[List[Cell]] = []
    paper: List[List[Cell]] = []                     # the paper's version (D-159, D-160, D-161): the same refs, intervals at one decimal
    for t, (name, ch, cmp_, sh, kk) in STUDY1_TESTS.items():
        tk = f"{VIEW}.tests.{t}"
        fk = f"{FA5}.{t}"
        lo, hi = ci_refs(S, "main", f"{tk}.ci95")
        reading = _reading(S, f"{tk}.reading")   # every test's stamped reading under the pre-registered decision rule, in the paper's words
        p_inf = _p_locked(S, t, S.ref("fa5", f"{fk}.p_inferiority"), complement=True)
        threshold = exact(S.ref("fa5", f"{fk}.holm_threshold"))
        head = [label(name), label(shape(sh)), label(_challenger(t)), label(_arm_name(cmp_)),
                pts(S.ref("main", f"{tk}.d"), margin=margin), interval(lo, hi, dp=2, signed=True, bounds=(0.0, margin)),
                _error_ratio(S, t), reading, _p_locked(S, t, S.ref("main", f"{tk}.p")), p_inf, threshold]
        if t == "t5":                                   # the Holm family's fifth member only: no inferiority reading
            rows.append(head + [DASH, DASH, DASH])
            paper.append([label(name), _p_inf_paper(S, t, p_inf), threshold, DASH, DASH])
            continue
        clo, chi = ci_refs(S, "fa5", f"{fk}.ci99")
        holds = text_of(S.ref("fa5", f"{fk}.holm_inferior"), YES_NO)
        rows.append(head + [holds, interval(clo, chi, dp=2, signed=True, bounds=(0.0, margin)),
                            text_of(S.ref("fa5", f"{fk}.ci99_excludes_margin"), YES_NO)])
        paper.append([label(name), _p_inf_paper(S, t, p_inf), threshold, interval(clo, chi, dp=1, signed=False, bounds=(0.0, margin)),
                      _holds_paper(S, t, holds)])

    m_cell = num(S.ref("fa5", MARGIN_KEY), dp=0, signed=True)
    level = _level_from_key("fa5", f"{FA5}.t3.ci99")
    order = [text_of(S.ref("fa5", f"result.holm_order.{i}"), TEST_NAMES) for i in range(len(S.get("fa5", "result.holm_order")))]

    # The Holm column's header ("Inferiority p below its Holm threshold") is fa5's Holm reading only while, for every test with an
    # inferiority reading, that reading is its p below its threshold, and Holm's step-down order agrees (no test is read as inferior
    # after one in the Holm order that is not).
    holm = [str(x) for x in S.get("fa5", "result.holm_order")]
    seen_not = False
    for t in holm:
        if t == "t5":
            continue
        f5 = f"{FA5}.{t}"
        below = float(S.get("fa5", f"{f5}.p_inferiority")) < float(S.get("fa5", f"{f5}.holm_threshold"))
        if S.get("fa5", f"{f5}.holm_inferior") is not below or (below and seen_not):
            raise ValueError(f"{t}: fa5's Holm reading is not its inferiority p below its Holm threshold: the column header would be wrong")
        seen_not = seen_not or not below

    # Test 3's line, stated from the numbers; printed only while the stamped booleans say what it says.
    t3 = f"{FA5}.t3"
    if not (S.get("fa5", f"{t3}.holm_inferior") is True and S.get("fa5", f"{t3}.ci99_excludes_margin") is False):
        raise ValueError("Test 3's typed line no longer fits fa5's stamped readings: rewrite it from the numbers")
    c3lo, c3hi = ci_refs(S, "fa5", f"{t3}.ci99")
    # Test 3 under the original marking rule: E-09's label (the sensitivity check Deviation 2 fixed in Lock 3, before any main-run
    # data; not a secondary view), printed only while the files say this view is the original rule and the table's is the official one.
    o3 = "secondary.original_repeat_rule.tests.t3"
    if S.get("main", "secondary.original_repeat_rule.score") != "original" or S.get("main", f"{VIEW}.score") != "official":
        raise ValueError("the original-rule view or the as-deployed view is not stamped with the score the typed line names")
    o3lo, o3hi = ci_refs(S, "main", f"{o3}.ci95")

    # Test 5's line: its confirmatory result is its Holm-adjusted result in the pre-registered family of one-sided tests.
    t5 = f"{VIEW}.tests.t5"
    _, t5_ch, t5_cmp, _, _ = STUDY1_TESTS["t5"]
    if not (S.get("main", f"{t5}.declared") is True
            and float(S.get("main", f"{t5}.p")) < float(S.get("main", f"{VIEW}.holm_thresholds.t5"))):
        raise ValueError("Test 5's typed line ('declared', 'below its Holm threshold') no longer fits the stamped values")
    if STUDY1_ARMS[t5_cmp][1:] != ("sonnet", "medium"):
        raise ValueError("Test 5's comparator is not Sonnet-medium: the Sonnet-effort companion would be wrong")
    sonnet_tests = [TEST_NAMES[t] for t, v in STUDY1_TESTS.items() if STUDY1_ARMS[v[2]][1:] == ("sonnet", "medium")]
    margin_size = num_d(derive("minus the margin", lambda m: -m, S.ref("main", f"{VIEW}.margin")), dp=0)

    # The near-ceiling label (reporting item 15), printed only while it is on.
    i15 = "reporting.group_b.item_15"
    if S.get("main", f"{i15}.on") is not True:
        raise ValueError("item 15's near-ceiling label is not on: the note below would be wrong")
    beside = [text_of(S.ref("main", f"{i15}.beside_tests.{i}"), TEST_NAMES) for i in range(len(S.get("main", f"{i15}.beside_tests")))]

    notes = [
        [label("In the reading column, \"> margin\" stands for \"by more than the margin\": \"worse by > margin\" is worse by more than the margin, "
               "as the other tables of this supplement write it.")],
        [label("Post hoc sensitivity, not a test: the correction was fixed before this check was computed, but"),
         _quoted(text_of(S.ref("fa5", "result.disclosure"))),
         label('(free analysis 5\'s own words; its "three-way reading" is the reading from the pre-registered decision rule, '
               'applied to the unadjusted interval).')],
        [label("Holm in the inferiority direction (null hypothesis: d at or above the margin of"), m_cell,
         label("points) over all five pre-registered tests at one-sided alpha"),
         _glue(exact(S.ref("fa5", "result.alpha")), label(";")),
         label("each inferiority p is one minus the locked one-sided p, from the same bootstrap (same differences and seeds, B ="),
         _glue(integer(S.ref("fa5", "code.B")), label(").")),
         label("Holm order, smallest inferiority p first:"), _glue(joined(*order, sep=", "), label("."))],
        [label("The stricter interval is the two-sided"), level,
         label("interval from the same bootstrap draws; it is shown beside Holm, not as part of it.")],
        [label("Test 3 (post hoc): its inferiority p,"), _glue(_p_locked(S, "t3", S.ref("fa5", f"{t3}.p_inferiority"), complement=True), label(",")),
         label("is below its Holm threshold of"),
         _glue(exact(S.ref("fa5", f"{t3}.holm_threshold")), label(",")), label("but its"), level, label("interval"),
         interval(c3lo, c3hi, dp=2, signed=True, bounds=(0.0, margin)), label("does not lie wholly below the margin of"),
         m_cell, label("points.")],
        [label("Test 3 under the original marking rule (the sensitivity check Deviation 2 fixed in Lock 3, before any main-run "
               "data): d ="), pts(S.ref("main", f"{o3}.d"), margin=margin),
         label("points, 95% interval"), _glue(interval(o3lo, o3hi, dp=2, signed=True, bounds=(0.0, margin)), label(";")),
         label("reading:"), _glue(_reading(S, f"{o3}.reading"), label("."))],
        [label("Test 5's confirmatory result is its Holm-adjusted result in the pre-registered family of one-sided tests. "
               f"{_arm_name(t5_ch)} is shown no worse than {_arm_name(t5_cmp)} by more than"),
         margin_size, label("points (Holm-adjusted):"), text_of(S.ref("main", f"{t5}.declared"), YES_NO),
         label("(p" + ("" if _p_locked(S, "t5", S.ref("main", f"{t5}.p")).printed.startswith(chr(0x2264)) else " =")),
         _glue(_p_locked(S, "t5", S.ref("main", f"{t5}.p")), label(",")), label("below its Holm threshold of"),
         _glue(exact(S.ref("main", f"{VIEW}.holm_thresholds.t5")), label(").")),
         label(f"Sonnet ran at medium effort, one level below its default, in {' and '.join(sonnet_tests)}. Here Test 5 is only "
               f"the fifth member of the inferiority-direction Holm family, not an inferiority claim; its full report is in TAB-02.")],
        [label(f"The error-rate ratio is the challenger's error rate over the comparator's, given beside d as in TAB-02 ({ER_TIER}, not "
               "part of its reading); the main analysis labels"), joined(*beside, sep=" and "), label("as"),
         _glue(text_of(S.ref("main", f"{i15}.label")), label(",")), label("where the error-rate ratio travels with d. Exact: the comparator's "
                                                                      "error-rate bound, in %, is the upper end of its exact "
                                                                      "(Clopper–Pearson) 95% interval.")],
    ]
    if S.get("main", "n") != 6:
        raise ValueError(f"the main analysis is at {S.get('main', 'n')} steps: the caption's '6 steps' would be wrong")
    caption = _caption(
        [_glue(text_of(S.ref("fa5", "definition.tier_label")), label(";")),
         label(f"the reading from the pre-registered decision rule, applied to the unadjusted interval, stays the result; the error-rate ratio is {ER_TIER}")],
        "Study 1, main run, 6 steps (pre-registered at 24 steps; Deviation 1)",
        [label("Study 1's main-run puzzles at 6 steps, as-deployed view; score:"),
         text_of(S.ref("main", f"{VIEW}.score"), {"official": "the official marking rule (with Deviation 2's repeated-line rule)"})],
        _tab27_n(S),
        [label("paired BCa bootstrap, B ="), integer(S.ref("main", f"{VIEW}.B")),
         label("(95% unadjusted, as locked); the stricter interval is the"), level, label("interval from the same draws")],
        "not applicable (no cost column)")
    t = Table([label(c) for c in cols], rows, notes, caption, layout="split landscape")
    # two parts, each beside its Test column: the test and its pre-registered reading (columns 0-7), then the locked p and the post hoc
    # Holm check in the inferiority direction, whose p is one minus it (columns 8-13). Sideways, so that a setting's name (Haiku-medium
    # vote, Opus-medium) stays on one line and the reading takes two or three lines, not five (measured at 6.5 in: the names broke at
    # their hyphens)
    t.split_parts = [(None, list(range(1, 8))), (None, list(range(8, 14)))]
    # the paper's caption facts also carry what its two-line notes no longer say (Edith's proof-2 notes rule)
    holm_fact = [label("Holm in the inferiority direction over all five pre-registered tests at one-sided alpha"),
                 _glue(exact(S.ref("fa5", "result.alpha")), label(";")),
                 label("each inferiority p is one minus the locked one-sided p, from the same bootstrap draws; Test 5 is the family's "
                       "fifth member only (no inferiority reading, dashes in its row)")]
    t.main_table = _tab27_paper(S, paper, level, {**caption, "holm": holm_fact})
    return t


ORIG_VIEW = "secondary.original_repeat_rule"      # Study 1 under the original marking rule (E-09's sensitivity check; see tab_27)
AS_RUN_ONLY = "only under the marking rule as run"  # the house words for Test 3's companion (TAB-01's caption, paper/sections/91-captions.md)
# The same words as the paper version's cell prints them: the last five words tied with no-break spaces, so that a narrow column breaks
# the cell after "under" (two lines that read) and never leaves "run" alone on a second line (Edith, proof 2, p. 26).
AS_RUN_ONLY_TIED = "only under " + "\u00a0".join("the marking rule as run".split())


def _p_inf_paper(S: Store, t: str, p_inf: Cell) -> Cell:
    """The inferiority p as the paper version prints it: the full table's cell, except where the locked p sits at the bootstrap's
    floor ("≤", core.pvalue_bound). There the inferiority p, one minus it, is a lower bound, printed "≥" and rounded DOWN at 5
    places (Edith's polish standard §2.2: bounds round toward the safe side). Refused unless the stamped inferiority p is exactly one
    minus that locked p. The full table keeps its plain value: a p at the bootstrap's ceiling is printed plainly by every table (TAB-02
    too) until core.pvalue_bound prints the ceiling as a bound for all of them (reported to Friday)."""
    lp = S.ref("main", f"{VIEW}.tests.{t}.p")
    locked = _p_locked(S, t, lp)
    if not locked.printed.startswith("\u2264 "):
        return p_inf
    pr = S.ref("fa5", f"{FA5}.{t}.p_inferiority")
    x = float(pr.value)
    if p_inf.printed.startswith("\u2264") or x != 1.0 - float(lp.value):
        raise ValueError(f"TAB-27 paper version: {t}'s inferiority p is not one minus its locked p at the bootstrap's floor: "
                         "the '\u2265' bound would be wrong")
    with localcontext() as ctx:
        ctx.prec = 50
        down = Decimal(repr(x)).quantize(Decimal(1).scaleb(-5), rounding=ROUND_FLOOR)
    return Cell("\u2265 " + f"{down:.5f}", raw=x, refs=(pr,) + locked.refs,
                formula="1 minus a p at the bootstrap's floor (the locked p, recorded with its z0, a and B); printed as a bound rounded "
                        "down at 5 places")


def _holds_paper(S: Store, t: str, holds: Cell) -> Cell:
    """fa5's Holm reading as the paper version prints it, with Test 3's companion in the same cell (Edith's labels reading, condition 2:
    "Test 3's dependence on the marking rule" stays in the same table row; the cell is the one place in this table, and TAB-01's paper
    version carries the same words in its caption: reported to Friday). The companion is printed for any test whose stamped reading
    under the original marking rule differs from its reading as run (today Test 3 alone: inconclusive under the original rule), and only
    on a reading that holds.

    What "only" rests on: fa5 computed Holm under the marking rule as run alone; there is no Holm result under the original rule. The
    word rests on the stamped three-way reading under the original rule (inconclusive), which says that rule's 95% interval does not lie
    wholly below the margin. From the same kind of bootstrap, that puts its one-sided inferiority p at or above 0.025, the one-sided
    level, and every Holm threshold here is at most that level, so the reading could not hold under Holm on that rule either. The build
    checks each step it can from the stamps: the original rule's reading is not "worse", its 95% interval's upper end is not below the
    same margin, the 95% interval is the two-sided form of fa5's one-sided level, and no Holm threshold exceeds that level."""
    as_run = S.ref("main", f"{VIEW}.tests.{t}.reading")
    orig = S.ref("main", f"{ORIG_VIEW}.tests.{t}.reading")
    if orig.value == as_run.value:
        return holds
    if holds.raw is not True:
        raise ValueError(f"TAB-27 paper version: {t}'s companion '{AS_RUN_ONLY}' would qualify a reading that does not hold")
    margin, alpha = float(S.get("fa5", MARGIN_KEY)), float(S.get("fa5", "result.alpha"))
    _olo, ohi = ci_refs(S, "main", f"{ORIG_VIEW}.tests.{t}.ci95")
    if (orig.value == "worse by more than the margin" or float(S.get("main", f"{ORIG_VIEW}.margin")) != margin
            or float(ohi.value) < margin or abs((1.0 - 2.0 * alpha) - 0.95) > 1e-12
            or any(float(S.get("fa5", f"{FA5}.{u}.holm_threshold")) > alpha for u in STUDY1_TESTS)):
        raise ValueError(f"TAB-27 paper version: {t}'s '{AS_RUN_ONLY}' no longer follows from the original rule's stamped reading "
                         "and interval (see _holds_paper)")
    return Cell(f"{holds.printed}, {AS_RUN_ONLY_TIED}", raw=holds.raw, refs=holds.refs + (as_run, orig, ohi),
                formula="fa5's Holm reading (marking rule as run; fa5 computed no Holm result under the original rule); 'only' rests on "
                        "the stamped three-way reading under the original rule, which differs from the reading as run (its 95% interval's "
                        "upper end is not below the margin, so its one-sided inferiority p is at or above every Holm threshold here)")


def _tab27_paper(S: Store, rows: List[List[Cell]], level: Cell, caption: Dict[str, List[Cell]]) -> Table:
    """TAB-27's paper version (D-159/D-160; Vision's plan §3: Test · p · threshold · 99% interval · holds; D-161): Tests 1-5 under
    Holm in the inferiority direction, five columns: the inferiority p and its Holm threshold at 5 places (as the full table prints them;
    a p that is a bound carries ≤ or ≥, rounded toward the safe side), fa5's stricter interval of d at one decimal (the positive end
    unsigned), and fa5's Holm reading, with Test 3's companion in its cell. Test 5 is the family's fifth member only: dashes, as in the
    full table. Two short notes define the p (with the bounds' signs, when one prints) and the last column in the decision words
    (D-161). The last column's header is "Holds under Holm", not the confirmatory "(Holm-adjusted)" tag: this is a post hoc check, and
    its post hoc sensitivity label is the caption's (Vision). Test 3's 99% interval not lying wholly below the margin (the full table's
    last column and its note) is a companion of Test 3's row too; it does not fit the text width beside the marking-rule companion
    (measured), and spec rule 5 keeps companions out of the notes, so it goes to Vision's caption through Friday. The widest cell is
    Test 3's reading: the table fits the text width at \\small (measured in a proof), so a longer header or cell here needs a new
    measurement."""
    # note 2 calls each of Tests 1-4's pre-registered reading "worse by > <margin> (pre-registered rule)": refuse unless every one is
    if any(S.get("main", f"{VIEW}.tests.{t}.reading") != "worse by more than the margin" for t in STUDY1_TESTS if t != "t5"):
        raise ValueError("TAB-27 paper version: a pre-registered reading of Tests 1-4 is not 'worse by more than the margin'")
    if [r[0].printed for r in rows] != [v[0] for v in STUDY1_TESTS.values()]:
        raise ValueError("TAB-27 paper version: the rows are not Tests 1-5 in order")
    if rows[-1][3] is not DASH or rows[-1][4] is not DASH:             # note 2's "Test 5: no inferiority reading" explains its dashes
        raise ValueError("TAB-27 paper version: Test 5's interval and reading cells are not dashes")
    marks = [m for m in ("\u2264", "\u2265") if any(r[1].printed.startswith(m + " ") for r in rows)]
    bound = [label(" and ".join(marks) + (" mark bounds" if len(marks) > 1 else " marks a bound") + ": no resample reached the margin.")]
    size = num_d(derive("the margin's size", lambda m: abs(m), S.ref("fa5", MARGIN_KEY)), dp=0)
    # Two lines together (Edith's proof-2 rule: the converter prints a paper table's notes as one paragraph). What the notes no longer
    # say, the caption's facts carry (the Holm family and its one-sided level, the draws the p and the stricter interval share, the
    # sentence that Test 5 is the family's fifth member only; main_caption below) and Method section 3.5 states (one-sided level,
    # Holm across the five tests).
    notes = [
        [label("Inferiority p: one minus the pre-registered one-sided p.")] + (bound if marks else []),
        [label("Holds under Holm: inferiority p below its threshold, so worse by >"), size,
         label("(pre-registered rule) holds. The"), level, label("interval is not part of Holm.")],
    ]
    cols = [label("Test"), label("Inferiority\u00a0p"), label("Holm threshold"), joined(level, label("interval of d (points)")),
            label("Holds under Holm")]               # "Inferiority p" tied: a header that wraps never leaves the p alone on a line
    return check_paper_words(Table(cols, rows, notes, caption, short_notes=[0, 1], layout="float"), "TAB-27")


def _tab27_n(S: Store) -> List[Cell]:
    """Puzzles per test and samples per puzzle: the Haiku-medium vote's k per vote test (k.json, the keys TAB-02's k column
    reads), the single-answer arms' designed tries (item 7, one value for all of them), and step voting's calls on the chains (item
    24's calls made, as TAB-02's caption gives them)."""
    votes = [(name, sh, kk) for t, (name, ch, _c, sh, kk) in STUDY1_TESTS.items() if kk is not None]
    if any(ch != "haiku-med" for t, (_n, ch, _c, _s, kk) in STUDY1_TESTS.items() if kk is not None):
        raise ValueError("a vote test's challenger is not the Haiku-medium vote")
    ks = [joined(integer(S.ref("main_k", f"k_from_rows.{'opus' if kk == 'O' else 'sonnet'}.{sh}.k")), label(f"in {name}"))
          for name, sh, kk in votes]
    singles = sorted({a for t, (_n, ch, c, _s, _k) in STUDY1_TESTS.items() for a in (ch, c) if a not in ("haiku-med", "e3")},
                     key=_arm_name)
    item7 = parse_key(ITEM7_ARMS)
    if len({S.get("main", join_key(*item7, a, "designed_tries")) for a in singles}) != 1:
        raise ValueError(f"the single-answer arms {singles} differ in designed tries: the caption's one value would be wrong")
    e3 = [(name, sh) for t, (name, ch, _c, sh, _k) in STUDY1_TESTS.items() if ch == "e3"]
    if [sh for _, sh in e3] != ["1x6"]:
        raise ValueError(f"step voting is not one test on the chains ({e3})")
    calls = join_key("reporting", "group_b", "item_24", "table", "e3 1x6", "refusals_and_truncations", "calls_made")
    return [label("puzzles per test:"), integer(S.ref("main", f"{VIEW}.tests.t1.n")),
            label("(the same in all five tests); samples per puzzle: the Haiku-medium vote's k is"), _and_list(ks),
            label("(each vote counts once per puzzle);"),
            label(", ".join(_arm_name(a) for a in singles[:-1]) + " and " + _arm_name(singles[-1])),
            _glue(integer(S.ref("main", join_key(*item7, singles[0], "designed_tries"))), label(" each;")),
            label(f"step voting ({e3[0][0]}) made"), integer(S.ref("main", calls)), label("calls in all on the chains")]
