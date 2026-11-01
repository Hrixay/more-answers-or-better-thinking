"""The paper's figures FIG-01 to FIG-07 (D-118, D-120; the master plan's "Tables and figures (for Friday)"). Every plotted number is read
from a pinned source by key (a `Ref`), scaled only for units (a proportion x 100 to %), and recorded with its source and key in the
figure's `.data.json`. Nothing is computed: no bootstrap, no fit, no frontier. The only reference lines are the ones the plan names,
drawn from stamped values (FIG-05's q^N line from the stamped `q_n`; the chains' local^N line from the stamped per-step accuracy,
labelled post hoc). Style: Vision's style sheet (D-122) through `paper_out_style` -- one colour per model, effort by shade, a marker shape
per model, log cost axes, 95% bars, hollow markers for exploratory or other-set points, text in ink colours.

FIG-03's optional post hoc panels at 6 and 12 steps read free analysis 2 (D-131; pinned as `fa2`, its revision 2 file fa2r2.json, whose
pooled cluster-bootstrap bands have width; the first file's bands collapsed through a coding error and are not used). Two of that
file's per-shape intervals have no width (chains at 6 steps, the last two vote sizes; free analysis 4 revision 2 stamps their exact
intervals), but FIG-03 draws the pooled vote only (the per-shape curves are not drawn: by shape, Test B2's vote is in TAB-11 and its difference from Opus-medium at each shape's own
cost-matched size is in TAB-25), so none of them is drawn. A band
drawn with no exact fallback is checked to have width (`has_width`), else the build stops. FIG-04 follows the user's framing ruling
on F-11 (D-132, the merged option): the main effort figure has no fitted line and no marked "best buys"; the cost-for-target view
is TAB-34 in the appendix. Left out because it is not stamped: see the notes in each builder.

FIG-05 has an appendix version (FigureOut.variants, written as FIG-05.appendix.*): the same figure with every length-sweep value under
the original marking rule (the `curve` file; the plan's "original-rule Sonnet in the appendix version"), and Pilot 1's markers under
both rules (Edith's settlement N2).

Rounding: every accuracy, share or interval end in % carries the ledger's one-more-decimal guard at 0 and 100 (`pv`, `pct`), so an end
of 99.968 prints 99.97, never 100.0.

Alt text: the writer joins alt cells with spaces, so `tight` attaches closing punctuation to the cell before it. Interval methods are
printed from the stamped method through `METHOD` ('clopper-pearson' -> 'exact (Clopper–Pearson)').

Collapsed intervals (FIG-01, FIG-02, FIG-05, FIG-06): where a stamped bootstrap interval has no width, free analysis 4 (D-131, pinned as
`fa4`; revision 2, fa4r2.json, which takes every zero-width interval of the stamped result files by rule) stamps an exact
(Clopper–Pearson) interval over base puzzles; `fa4_bar` finds it through the core's `fa4_exact` by the point's source and key, checks
fa4's stamped mean and collapsed interval against the plotted ones, and the figure draws it as a dotted bar labelled post hoc, with
the ends and the count behind them in the point's record. Revision 2 leaves out only the length sweep's q (no single count carries
it; FIG-05 draws Haiku-medium's q, whose bands are checked to have width) and item 20 below k = 40 (drawn nowhere), so a collapsed
point without an fa4 cell stops the build: no point lacks a bar. Every other bar or band is checked to have width (`has_width`).

Main-text names (Edith's settlement E-06 and P-2): step voting, the Haiku team and step voting on pieces are written in plain words; the
keep-list codes stay out of every figure. Set ids, run ids and preset ids are never printed in a caption, note or label (the style
sheet keeps them for the methods appendix's disclosure tables); each figure's sources name its files.

Item numbers and decision ids (Edith's PR 27 rulings Q22 and PO-1): no caption fact, alt text or drawn text of any figure names an
item number, a keep-list C-number or an E-number, and no printed text names a decision id; the stamped keys behind them stay in
each cell's provenance. `plain_ids` checks every figure for this (the plotted points' text included: each plain-string field and
the printed text of each cell field), and for the main-text figures (FIG-01, FIG-03 to FIG-06, `plain_ids(main=True)`; FIG-02 and
FIG-07 are in the appendix) it also refuses an internal id in the plotted points' text, cell fields included; `main_text`
(paper_out_names) checks their plain-string fields as well. Tiers that changed in that round:
FIG-04's hollow Study 1 points are "Study 1 (other puzzles; across studies, descriptive)", with each Study 1 arm's role read as
TAB-04 reads it and an exploratory arm marked by a dot; FIG-05's Pilot 1 markers are exploratory (Q13); FIG-03's band method is read
from Study 1b's driver (`_boot` in harness/analysis/study1b.py, pinned at the lock-4 commit it ran at; Q28).
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Sequence, Tuple

from . import paper_out_style as style
from .paper_out_core import (Cell, FigureOut, Ref, Source, Store, _need_num, ci_refs, derive, fa4_exact, integer, interval,
                             joined, join_key, label, num_d, num, output, parse_key, register_source, stamped_count, text_of, usd)
from .paper_out_core import pct as _core_pct
from .paper_out_names import MAIN_TEXT_ID, STUDY1_ARMS, STUDY1_TESTS, STUDY1B_TAGS, main_text
from .paper_out_style import INK, INK_2, MODEL_MARKER, MUTED, THINKING_OFF, color

plt = style.plt
np = style.numpy
from matplotlib.lines import Line2D                      # noqa: E402
from matplotlib.patches import Patch                     # noqa: E402
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec   # noqa: E402

COL1, COLW = 4.5, 6.5           # one-panel and full-width figure widths at print size, in inches (Edith §8.1)
LAB = 8.0                       # font size of direct labels (8-10 pt at print size, Edith §8.2)
MODEL_NAME = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus"}
SHAPE_WORD = {"1x6": "chains", "6x1": "pieces", "1x16": "chains", "16x1": "pieces", "1x12": "chains", "12x1": "pieces"}


# ---------------------------------------------------------------- helpers


@dataclass
class V:
    """A plotted value: the Ref it came from, its printed cell (with provenance) and the float that is drawn."""
    ref: Ref
    cell: Cell
    val: float


PCT_BOUNDS = (0.0, 100.0)       # the ledger's one-more-decimal guard for a value in %: 99.968 prints 99.97, never 100.0


def val(S: Store, source: str, key: str, scale: float = 1.0, dp: int = 1, bounds: Sequence[float] = ()) -> V:
    r = S.ref(source, key)
    return V(r, num(r, dp=dp, scale=scale, bounds=bounds), _need_num(r) * scale)


def pv(S: Store, source: str, key: str, dp: int = 1, prop: bool = True) -> V:
    """An accuracy in %: from a proportion (x 100) or from a value already in points (guarded at 0 and 100)."""
    return val(S, source, key, 100.0 if prop else 1.0, dp, PCT_BOUNDS)


def pct(r: Ref, dp: int = 1, from_proportion: bool = True) -> Cell:
    """The core's `pct` with the guard at 0 and 100 (every % in these figures is a share between 0 and 100)."""
    return _core_pct(r, dp=dp, from_proportion=from_proportion, bounds=PCT_BOUNDS)


def ci(S: Store, source: str, key: str, dp: int = 1, prop: bool = True) -> Tuple[V, V]:
    return pv(S, source, key + ".0", dp, prop), pv(S, source, key + ".1", dp, prop)


def kval(S: Store, source: str, key: str) -> Tuple[Cell, float]:
    """An integer count (k, n, steps) from a stamped number: its cell and its float."""
    r = S.ref(source, key)
    return integer(r), float(_need_num(r))


def key_cell(source: str, parent: str, key: str) -> Tuple[Cell, float]:
    """A step count that the source stamps only as the NAME of a key (e.g. `models.hm.by_n.12`): the cell records that key as its
    provenance, with the formula 'the key name'."""
    n = int(key)
    r = Ref(n, source, join_key(*[p for p in _split(parent)], key))
    return Cell(str(n), raw=n, refs=(r,), formula="the key name (steps)"), float(n)


def _split(k: str) -> List[str]:
    from .paper_out_core import parse_key
    return parse_key(k)


def rec(series: str, panel: str, **cells: Any) -> Dict[str, Any]:
    """One plotted mark: its series and panel (typed names) and each value as a Cell record."""
    d: Dict[str, Any] = {"series": series, "panel": panel}
    for k, v in cells.items():
        if isinstance(v, V):
            d[k] = v.cell.record()
        elif isinstance(v, Cell):
            d[k] = v.record()
        elif v is not None:
            d[k] = v
    return d


def P(c: Cell) -> Cell:
    """A percent cell for alt text: '43.7%'."""
    return joined(c, label("%"), sep="")


def L(text: str) -> Cell:
    return label(text)


# ---------------------------------------------------------------- what a figure may print (Edith's PR 27 rulings Q22 and PO-1)

DECISION_ID = re.compile(r"\bD-\d")


def _drawn(fo: FigureOut) -> Iterator[str]:
    """Every text drawn in a figure (titles, legends, annotations, axis labels)."""
    from matplotlib.text import Text
    for t in fo.fig.findobj(Text):
        if t.get_text():
            yield t.get_text()


def _point_texts(fo: FigureOut) -> List[str]:
    """Every printed text of a figure's plotted points, at any depth: each plain-string field (series, panel, note, tier) and the
    printed text of each cell field (a Cell, or the Cell record `rec` stores: any dict with 'printed' and 'kind'). A cell's provenance
    (refs, raw, formula) is not printed and is not read."""
    out: List[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, Cell):
            out.append(v.printed)
        elif isinstance(v, dict):
            if "printed" in v and "kind" in v:
                out.append(str(v["printed"]))
            else:
                for x in v.values():
                    walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
    for p in fo.points:
        for v in p.values():
            walk(v)
    return out


def plain_ids(fn: Optional[Callable[[Store], FigureOut]] = None, *, main: bool = False) -> Any:
    """For every figure builder, main text or appendix, and each of its variants: no decision id (D-nn) in any printed text (alt text,
    caption facts, drawn text, the plotted points' text: plain-string fields and the printed text of cell fields, `_point_texts`; the
    decision register is not released, so ids stay in provenance only), and no internal id (an item number, a keep-list C-number or
    an E-number: `MAIN_TEXT_ID`) in the alt text, the caption facts or the drawn text, which print with the figure (Q22: captions and
    alt text use no item numbers). A main-text figure is decorated `plain_ids(main=True)`: its plotted points' text, cell fields
    included, names no internal id either (it also carries `main_text`, which reads the points' plain-string fields only). An appendix
    figure's points may keep "(item N)". Refuses the build otherwise."""
    if fn is None:
        return functools.partial(plain_ids, main=main)

    @functools.wraps(fn)
    def checked(S: Store) -> FigureOut:
        out = fn(S)
        for name, fo in [("", out)] + [(f".{s}", v) for s, v in out.variants]:
            shown = [c.printed for c in fo.alt] + [c.printed for v in fo.caption.values() for c in v] + list(_drawn(fo))
            points = _point_texts(fo)
            bad = sorted({t for t in shown + points if DECISION_ID.search(t)} |
                         {t for t in shown + (points if main else []) if MAIN_TEXT_ID.search(t)})
            if bad:
                raise ValueError(f"{fn.__name__}{name}: printed text names a decision or internal id (plain words instead): {bad}")
        return out
    return checked


# A stamped interval method in the paper's words (FIG-01's caption wording).
METHOD = {"cluster bootstrap": "cluster bootstrap", "clopper-pearson": "exact (Clopper–Pearson)", "wilson": "Wilson"}


def method(S: Store, source: str, key: str) -> Cell:
    """The stamped interval method at `key` ('cluster bootstrap', 'clopper-pearson', 'wilson'), printed through METHOD."""
    return text_of(S.ref(source, key), METHOD)


def ci_words(lo: Cell, hi: Cell, paren: bool = False) -> List[Cell]:
    """An interval in the style sheet's words for alt text and captions: '95% interval 97.1% to 99.5%' (two percent cells), or in
    parentheses: '(95% interval 97.1% to 99.5%)'."""
    if paren:
        return [L("(95% interval"), P(lo), L("to"), P(hi), L(")")]
    return [L("95% interval"), P(lo), L("to"), P(hi)]


# The length sweep's analysis plan (D-87; research/pilot-plan-ledger.md, last changed by 7bcc8d1, before which the curve files were
# written from it): the curve files stamp their draws but not the name of the bootstrap they used, so FIG-05 quotes the method from the
# plan's own line (located by its words, quoted only if the line holds them).
CURVE_PLAN = register_source(Source(
    name="curve_plan", path="research/pilot-plan-ledger.md", commit="7bcc8d1",
    sha256="51c811bdb99e22ad0168d1a02ed4334841b0153beff90b5368ca6942371911f9", kind="text",
    what="the length sweep's analysis plan (D-87): its interval section names the bootstrap the curve files stamp without naming"))


def quoted(S: Store, source: str, pattern: str, words: str) -> Cell:
    """`words` quoted from the one line of a pinned text source that matches `pattern` (refused unless exactly one line matches and it
    holds the words): the cell records that line as its source."""
    lines = S.find_lines(source, pattern)
    if len(lines) != 1:
        raise ValueError(f"{source}: {len(lines)} lines match {pattern!r}; quote from exactly one")
    r = S.ref(source, f"L{lines[0]}")
    if words not in str(r.value):
        raise ValueError(f"{source} line {lines[0]} does not hold {words!r}")
    return Cell(words, raw=r.value, refs=(r,), formula="quoted from this line")


def quoted_field(S: Store, source: str, key: str, words: str) -> Cell:
    """`words` quoted from a stamped text field (refused unless the field holds them): the cell records the field as its source."""
    r = S.ref(source, key)
    if not isinstance(r.value, str) or words not in r.value:
        raise ValueError(f"{source}:{key} does not hold {words!r}")
    return Cell(words, raw=r.value, refs=(r,), formula="quoted from this field")


# Study 1b's analysis driver as it ran (Edith's ruling Q28: FIG-03's band method is read from a source, not typed). The Study 1b file
# (s1b, fb301dd) was written by `harness/analysis/study1b.py` run once at the lock-4 tag (d1c565f, fb301dd's own message); the file is
# unchanged from c99814f to d1c565f and fb301dd (same SHA-256). Its vote curve at 16 steps stamps its bootstrap names
# ('1b:hx-vote:16:...') but no method; the bands come from the driver's `_boot`, whose docstring names the method.
S1B_DRIVER = register_source(Source(
    name="s1b_driver", path="harness/analysis/study1b.py", commit="d1c565f",
    sha256="957f63276197fdcf9c2eee0e8f43b542c63ee8c1be76a4f3ef72b6226a2295d3", kind="text",
    what="Study 1b's analysis driver at the lock-4 tag, as run for the Study 1b file: `_boot` names the vote curve's band method"))


def s1b_band_method(S: Store) -> Tuple[Cell, Cell, Cell]:
    """FIG-03 panel A's band method, read from Study 1b's driver (Q28): the method words of `_boot`'s docstring ('cluster bootstrap',
    'percentile'), each quoted from that line, and the bootstrap draws (the file's `constants.draws`). Structure checks: the driver
    defines `_boot` once, its docstring line holds the method; the vote curve calls `_boot` under the bootstrap names the file stamps,
    and the driver passes the file's draws to the vote curve. Refuses the build otherwise."""
    d = "s1b_driver"
    defs = S.find_lines(d, r"^def _boot\(")
    if len(defs) != 1:
        raise ValueError(f"{d}: {len(defs)} definitions of _boot")
    doc = S.ref(d, f"L{defs[0] + 1}")
    if not str(doc.value).startswith('"""The cluster bootstrap (curve.cluster_bootstrap, percentile 95%) of the mean over drawn base'):
        raise ValueError(f"{d} line {defs[0] + 1} is not _boot's docstring naming its method")
    stamped = str(S.get("s1b", "descriptive.vote_curve_n16.bootstrap_names"))
    if (not stamped.startswith("1b:hx-vote:16:") or len(S.find_lines(d, r'"ci95": _boot\(sorted\(v\), v, f"1b:hx-vote:\{n\}:\{label\}", draws\)')) != 1
            or len(S.find_lines(d, r'"vote_curve_n16": vote_curve\(ctx, rows, k, dv\)')) != 1
            or len(S.find_lines(d, r'"constants": \{.*"draws": dv,')) != 1):
        raise ValueError("FIG-03: the vote curve's bands are no longer the driver's _boot over the file's draws: reword the band method")
    words = [Cell(w, raw=doc.value, refs=(doc,), formula="quoted from this line") for w in ("cluster bootstrap", "percentile")]
    return words[0], words[1], integer(S.ref("s1b", "constants.draws"))


# ---------------------------------------------------------------- format compliance beside accuracy (style sheet, D-122)

T24 = "reporting.group_b.item_24.table"
S1B_FR = "descriptive.format_refusals_truncations_missing"
FLAG_RING = dict(linestyle="none", marker="o", markersize=8.5, markerfacecolor="none", markeredgecolor=INK, markeredgewidth=0.8)


def s1_format(S: Store, arm: str, shape: str) -> Optional[Tuple[Cell, Ref]]:
    """Study 1: an arm's format compliance at a shape (item 24's row, in % with two decimals as in the Study 1 tables) and its item 17
    format flag; None where item 24 stamps none (step voting)."""
    key = join_key(*T24.split("."), f"{arm} {shape}", "format_compliance", "format_compliance")
    if not S.has("main", key):
        return None
    return (pct(S.ref("main", key), dp=2),
            S.ref("main", join_key("reporting", "group_b", "item_17", "flags", f"{arm} {shape}", "fires")))


FIVE = "counts.five_test_arms"


def s1_role(S: Store, arm: str, shape: str) -> str:
    """An arm's role at a shape in Study 1, read from the sources TAB-04 reads it from: 'confirmatory' where a test's design
    (names.STUDY1_TESTS, copied from five_tests.py) uses the arm at that shape as challenger or comparator (Haiku-medium through its
    votes); 'five-test arm' where the file's own list (counts.five_test_arms) holds the arm at that shape but no test uses it there;
    'exploratory' otherwise. An arm a test uses that the file's list lacks refuses the build."""
    listed = f"{arm} {shape}" in set(S.keys("main", FIVE))
    if any(sh == shape and arm in (ch, cmp_) for _, ch, cmp_, sh, _ in STUDY1_TESTS.values()):
        if not listed:
            raise ValueError(f"{arm} {shape}: a test uses it but counts.five_test_arms does not list it")
        return "confirmatory"
    return "five-test arm" if listed else "exploratory"


def s1b_format(S: Store, tag: str, sk: str) -> Tuple[Cell, Ref]:
    """Study 1b: an arm's format compliance at a shape key ('1x16') from its format report (in %, one decimal as in the Study 1b
    tables) and its item 17 format flag."""
    return (pct(S.ref("s1b", join_key(*S1B_FR.split("."), "format_report", tag, sk, "format_compliance"))),
            S.ref("s1b", join_key(*S1B_FR.split("."), "item_17_flags", f"{tag} {sk}", "fires")))


def fmt_list(items: Sequence[Tuple[str, Sequence[Tuple[Cell, Ref, str]]]]) -> Tuple[List[Cell], bool]:
    """'Haiku-medium 98.59% and 99.72%; Opus-medium 97.50% (chains: flagged) and 100.00%' from (name, [(format cell, flag ref, shape
    word)]) items; also whether any value is flagged (so the caption's 'none is flagged' is read, not assumed)."""
    out, any_flag = [], False
    for name, vals in items:
        it: List[Cell] = [L(name)]
        for j, (fc, fl, sw) in enumerate(vals):
            if j:
                it.append(L("and"))
            it.append(P(fc))
            if fl.value is True:
                it.append(text_of(fl, {True: f"({sw}: flagged)"}))
                any_flag = True
            elif fl.value is not False:
                raise ValueError(f"{fl.source}:{fl.key} is {fl.value!r}, not a flag")
        out.append(it)
    return _seq(out, sep=";"), any_flag


def flag_tail(any_flag: bool) -> List[Cell]:
    """The format check's verdict on the listed values (the pre-registered format flag, whose rule TAB-07 prints; named in plain words:
    no item number in a caption fact)."""
    return [L("; the format check flags only the values marked flagged, and a flagged point carries a ring" if any_flag else
              "; the format check flags none of these")]


# ---------------------------------------------------------------- Test 3's marking-rule companion (style sheet; Edith's ruling E-09)

def test3_qualifier(S: Store) -> List[Cell]:
    """Test 3 always travels with its marking-rule qualifier: Sonnet-medium's chain score and Test 3's reading under the original
    pre-registered marking rule, which Deviation 2 kept as a sensitivity check, against the official rule (read, not typed)."""
    rates, o3, t3 = "secondary.rates.sonnet-med", "secondary.original_repeat_rule.tests.t3", "confirmatory.views.as_deployed.tests.t3"
    if S.get("main", o3 + ".reading") == S.get("main", t3 + ".reading"):
        raise ValueError("Test 3's reading no longer changes under the original marking rule: reword its qualifier")
    if STUDY1_TESTS["t3"][2:4] != ("sonnet-med", "1x6"):
        raise ValueError("Test 3 is not the chains comparison with Sonnet-medium: reword its qualifier")
    return [L("Test 3 (chains) depends on how answers are marked: under the original pre-registered marking rule, which Deviation 2 kept"
              " as a sensitivity check, Sonnet-medium's chain score is"), P(pct(S.ref("main", rates + ".original_acc"))),
            L("instead of"), P(pct(S.ref("main", rates + ".official_acc"))), L(", and Test 3 would read"),
            text_of(S.ref("main", o3 + ".reading")), L("instead of"), text_of(S.ref("main", t3 + ".reading"))]


# ---------------------------------------------------------------- price basis, one wording in every figure (style sheet)

def _no_price_date(S: Store, source: str) -> None:
    """A structure check behind 'its file stamps no price-table date': no key of the source names a price table."""
    def walk(x: Any) -> bool:
        if isinstance(x, dict):
            return any("price_table" in str(k) or walk(v) for k, v in x.items())
        if isinstance(x, list):
            return any(walk(v) for v in x)
        return False
    if walk(S.doc(source)):
        raise ValueError(f"{source} stamps a price table: print its date")


def price_study1b(S: Store) -> List[Cell]:
    """Study 1b's price basis: its stamped unit is 'USD per answer, list price (item 9b)' (checked), and it stamps no price-table date.
    The caption names the basis in plain words (no item number in a caption fact, Q22)."""
    u = str(S.get("s1b", "descriptive.vote_curve_n16.opus_medium_cost_per_answer.unit"))
    if not u.startswith("USD per answer, list price (item 9b)"):
        raise ValueError(f"Study 1b's cost unit is {u!r}: reword the price line")
    _no_price_date(S, "s1b")
    return [L("US dollars per answer at list price (Study 1b's stamped cost unit; its file stamps no price-table date)")]


# ---------------------------------------------------------------- exact intervals where a bootstrap collapsed (free analysis 4)

EXACT_DASH = (0, (1.0, 1.0))     # the dotted bar of an exact interval from free analysis 4 (post hoc)
EXACT_NOTE = ("the bootstrap interval collapsed to a point; the dotted bar is the exact (Clopper–Pearson) 95% interval from free "
              "analysis 4 (post hoc), over exact_n base puzzles, exact_x of them right")


def collapsed(lo: "V", hi: "V") -> bool:
    return hi.val - lo.val <= 1e-9


class Exact(NamedTuple):
    """Free analysis 4's exact (Clopper–Pearson) 95% interval for one plotted point, in the plotted unit (%): its two ends as plotted
    values (each with its fa4 ref), and the count behind it (x right of n base puzzles, read from the same fa4 cell)."""
    lo: V
    hi: V
    x: Cell
    n: Cell


def fa4_bar(S: Store, source: str, key: str, y: V, lo: V, hi: V) -> Exact:
    """The exact (Clopper–Pearson) 95% interval that free analysis 4 (revision 2) stamps for the collapsed interval at `source`:`key`
    (the dict holding `mean` and `ci95`), found by the core's `fa4_exact` (which checks it is fa4's copy of that very interval). fa4's
    stamped mean and collapsed ends must also equal the plotted ones (in %), so the bar cannot attach to another point. Nothing is
    computed: the ends are read (x 100 for a share). Revision 2 takes every zero-width interval of the files these figures draw from by
    rule; its only exclusions are the length sweep's q (FIG-05 draws Haiku-medium's, whose bands are checked to have width) and item 20
    below k = 40 (FIG-02 draws k = 40 only). So a collapsed point with no fa4 cell refuses the build rather than losing its bar."""
    c = fa4_exact(S, source, key)
    if c is None:
        raise ValueError(f"{source}:{key} has a collapsed interval and free analysis 4 stamps no exact one: draw none only with the reason")
    got = [_need_num(S.ref("fa4", c.base + ".stamped_mean")) * c.scale] + [_need_num(S.ref("fa4", f"{c.base}.stamped_ci95.{j}")) * c.scale
                                                                           for j in (0, 1)]
    if any(abs(g - w) > 1e-6 for g, w in zip(got, (y.val, lo.val, hi.val))):
        raise ValueError(f"fa4 {c.base} ({source}:{key}) stamps {got}, the plotted point is {(y.val, lo.val, hi.val)}")
    ends = [V(r, num(r, dp=1, scale=c.scale, bounds=PCT_BOUNDS), _need_num(r) * c.scale) for r in (c.lo, c.hi)]
    return Exact(ends[0], ends[1], integer(S.ref("fa4", c.base + ".x")), integer(S.ref("fa4", c.base + ".n")))


def has_width(what: str, lo: V, hi: V) -> None:
    """A structure check for a bar or band drawn without an exact fallback: its stamped interval has width (a collapsed one would be
    drawn as nothing while the legend says '95%'). Refuses the build otherwise: draw free analysis 4's exact bar there (`fa4_bar`)."""
    if collapsed(lo, hi):
        raise ValueError(f"{what}: the stamped interval has no width; draw free analysis 4's exact bar and say so in the caption")


def exact_rec(ex: Optional[Exact]) -> Dict[str, Any]:
    """A plotted point's record fields for its exact bar (none when the point has no exact bar)."""
    return {} if ex is None else {"exact_lo": ex.lo, "exact_hi": ex.hi, "exact_x": ex.x, "exact_n": ex.n}


def exact_bar(ax, x: float, y: float, lo: float, hi: float, col: str, lw: float = 0.8, cap: float = 0.0, zorder: int = 2,
              halo: float = 0.0) -> None:
    """The exact 95% interval read from free analysis 4 (post hoc) where the bootstrap collapsed: drawn as an ordinary bar (Karen's
    page 3 and Edith §8.6: intervals one way everywhere; dotted is kept for margins), and named in the caption. `halo` (points, 0 for none)
    sets the bar on a white outline just under it, so that a reference line it crosses is cut round it and the bar's end reads as its own
    (FIG-01: Haiku-max's exact stub ends within a point of Opus-medium's line)."""
    if halo > 0.0:
        ax.errorbar([x], [y], yerr=[[max(y - lo, 0.0)], [max(hi - y, 0.0)]], fmt="none", ecolor="white", elinewidth=lw + 2.0 * halo,
                    capsize=cap, zorder=zorder - 0.05)
    ax.errorbar([x], [y], yerr=[[max(y - lo, 0.0)], [max(hi - y, 0.0)]], fmt="none", ecolor=col, elinewidth=lw, capsize=cap,
                zorder=zorder)


def exact_handle(text: str = "dotted bar: exact 95% interval where the bootstrap collapsed (post hoc, free analysis 4)") -> Line2D:
    return Line2D([0], [0], color=INK_2, linewidth=1.0, linestyle=EXACT_DASH, label=text)


_CLOSING = (",", ".", ";", ":", ")")
_NAME_FORMULAS = ("the name of this dict entry", "the key name (steps)", "the key name")


def tight(cells: Sequence[Cell]) -> List[Cell]:
    """Alt-text cells with closing punctuation attached to the cell before it: the writer joins cells with spaces, so without this the
    text reads '(lower edge 0 ) ,'. A label that starts with , . ; : or ) is joined to the previous cell with no space (every cell keeps
    its refs)."""
    out: List[Cell] = []
    for c in cells:
        # a cell that prints a key's own name must print exactly that name (the audit checks it), so nothing is attached to it
        if out and c.kind == "label" and c.printed[:1] in _CLOSING and out[-1].formula not in _NAME_FORMULAS:
            out[-1] = joined(out[-1], c, sep="")
        else:
            out.append(c)
    return out


def tight_caption(caption: Dict[str, List[Cell]]) -> Dict[str, List[Cell]]:
    """`tight` applied to each caption fact (they are read the same way, cells joined with spaces)."""
    return {k: tight(v) for k, v in caption.items()}


def fig_axes(width: float, height: float, **kw):
    fig = plt.figure(figsize=(width, height))
    return fig


def tidy(ax, xlabel: Optional[str] = None, ylabel: Optional[str] = None) -> None:
    ax.set_axisbelow(True)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)


# Axis titles, worded the same in every figure (Edith §8.4; Karen's page 3). A dollar sign is escaped: in matplotlib it starts math.
ACC_LABEL = "Accuracy (%)"
COST_ANSWER = "Cost per answer (\\$, log scale)"
COST_PUZZLE = COST_ANSWER       # one name for the one quantity: Figures 1, 3 and 8 all say "Cost per answer" (Edith, proof 5, job K row 4)
K_LABEL = "Vote size $k$"


def panel_tag(ax, tag: str) -> None:
    """The panel letter (A, B, ...), bold, 9 pt, at the panel's top left: the same place and font in every figure (Edith §8.5)."""
    ax.text(0.0, 1.03, tag, transform=ax.transAxes, fontsize=9, color=INK, ha="left", va="bottom", **style.BOLD)


def style_for(model: str, effort: str) -> Dict[str, Any]:
    """Colour and marker for a model and effort ('off' is thinking off)."""
    if effort == "off":
        return {"color": THINKING_OFF["color"], "marker": THINKING_OFF["marker"]}
    return {"color": color(model, effort), "marker": MODEL_MARKER[model]}


# A marker's half-height in points at size 5 (a diamond's point reaches 1.41 times further than a circle's or a square's).
MARK_HALF_PT = {"haiku": 2.8, "sonnet": 2.8, "opus": 3.84}


BAR_TOL_PT = 1.0     # a bar end that sticks out less than this past its marker's edge reads as a smudge on the marker, not a bar


def _bar_pts(ax, model: str, size: float):
    """A panel's points per unit of y (from its final y range: set the axis limits before drawing marks) and a marker's half-height in
    points, the two numbers the bar rule reads."""
    bottom, top = ax.get_ylim()
    return ax.get_position().height * ax.figure.get_figheight() * 72.0 / (top - bottom), MARK_HALF_PT[model] * size / 5.0


def bar_hidden(ax, model: str, lo: Optional[float], hi: Optional[float], size: float = 5.0, y: Optional[float] = None) -> bool:
    """Edith's rule for every figure (PR #34 review, 2026-10-18; polish standard §8.6, which allows hiding only a bar that is shorter than
    its marker; her PR #40 review, 2026-10-20, M3, restored the span test), decided PER POINT and PER ARM: a 95% bar is not drawn only
    if it lies behind its marker, that is, its whole span is shorter than the marker's height AND (given the estimate y) neither arm
    sticks out BAR_TOL_PT or more past the marker's edge. A bar at least as long as its marker is always drawn, however little its arms
    stick out (`bar_sliver` says which of those need drawing in front of the marker). A one-sided bar (an estimate at 100%, its upper
    end the estimate itself) has a short span but its lower arm can reach past the marker: it is drawn. The panel's points per unit come
    from its final y range, so set the axis limits before drawing marks. Captions name the hidden ones from this same test."""
    if lo is None or hi is None or hi - lo <= 1e-9:
        return False
    pt_per_unit, half = _bar_pts(ax, model, size)
    if (hi - lo) * pt_per_unit >= 2.0 * half:
        return False                                  # the span is not shorter than the marker: drawn
    if y is None:
        return True
    return max(y - lo, hi - y) * pt_per_unit - half < BAR_TOL_PT


SLIVER_HALO_PT = 0.4      # the white outline each side of a sliver bar drawn in front of its marker (a bar in the marker's own colour would not show)


def bar_sliver(ax, model: str, lo: Optional[float], hi: Optional[float], size: float = 5.0, y: Optional[float] = None) -> bool:
    """A bar the rule draws (`bar_hidden` is False) whose arms still stick out less than BAR_TOL_PT past the marker's edge: its span is a
    little longer than the marker, so behind the marker it would be a sub-point smudge, the sliver Edith's D-168 LOW named. (Her PR #40
    review, M3: hiding it is not allowed, since it is not shorter than the marker; so it is drawn where it shows: in front of the marker,
    on a thin white outline, as `sliver_bar` does.) Only FIG-04's caption has words for such a bar (`mark(..., sliver_ok=True)`); every
    other site that draws a 95% bar asks `forbid_sliver`, which stops the build if one turns up there."""
    if y is None or lo is None or hi is None or hi - lo <= 1e-9 or bar_hidden(ax, model, lo, hi, size, y=y):
        return False
    pt_per_unit, half = _bar_pts(ax, model, size)
    return max(y - lo, hi - y) * pt_per_unit - half < BAR_TOL_PT


def forbid_sliver(where: str, ax, model: str, lo: Optional[float], hi: Optional[float], size: float = 5.0, y: Optional[float] = None) -> None:
    """For a figure whose caption has no words for a bar drawn in front of its marker (only FIG-04's has them): stop the build if a 95% bar
    there is only just longer than its marker (`bar_sliver`). Without this, a later change of a panel's height or y range could make a
    sliver there that is drawn with nothing in the caption saying so, and no figure check would catch it (Friday's checker on Edith's
    PR #40 review, M3 round: SHOULD 3). Today it never fires. To allow a sliver at a site: add the caption words, as FIG-04's note has."""
    if bar_sliver(ax, model, lo, hi, size, y=y):
        raise ValueError(f"{where}: the 95% bar {lo} to {hi} of a {model} point at {y} is only just longer than its marker, so it would be drawn in "
                         f"front of the marker (`bar_sliver`), and this figure's caption has no words for that: add them, as FIG-04's note has")


def sliver_bar(ax, x: float, y: float, lo: float, hi: float, col: str, zorder: float, lw: float = 0.8, dx_pt: float = 0.0) -> None:
    """A sliver bar (`bar_sliver`): the bar in the mark's colour, offset `dx_pt` points to the right of its marker, so that the whole
    bar shows beside the marker. (Drawn through the marker on a white outline it read as a split marker, Edith's job K row 11; with no
    offset, `dx_pt` = 0, it is drawn in front on a white outline `SLIVER_HALO_PT` wide each side.) The offset is display only: the bar
    spans the stamped interval at the marker's own cost."""
    from matplotlib.transforms import ScaledTranslation
    yerr = [[max(y - lo, 0.0)], [max(hi - y, 0.0)]]
    if dx_pt == 0.0:
        ax.errorbar([x], [y], yerr=yerr, fmt="none", ecolor="white", elinewidth=lw + 2.0 * SLIVER_HALO_PT, capsize=0.0, zorder=zorder - 0.05)
    cont = ax.errorbar([x], [y], yerr=yerr, fmt="none", ecolor=col, elinewidth=lw, capsize=0.0, zorder=zorder)
    if dx_pt:
        shift = ScaledTranslation(dx_pt / 72.0, 0.0, ax.figure.dpi_scale_trans)
        for art in cont[2]:
            art.set_transform(ax.transData + shift)


def mark(ax, x, y, lo, hi, model: str, effort: str, hollow: bool = False, size: float = 5.0, zorder: int = 3, bar_alpha: float = 1.0,
         lw: float = 0.8, cap: float = 0.0, label_: Optional[str] = None, bar_over: Optional[bool] = None,
         bar_zorder: Optional[float] = None, sliver_ok: bool = False) -> bool:
    """A point with its 95% bar in the mark's colour behind the marker (drawn only if the stamped interval has width and is not wholly
    hidden by the marker: `bar_hidden`); hollow = white fill, coloured edge. Returns True when the bar was not drawn (the caption names
    such points). `bar_over` is no longer used: the rule is the same in every figure. `bar_zorder` (default: one level behind the marker)
    lets a bar stand above another model's marker (FIG-04: Sonnet-max's bar over the Opus diamonds). A bar that is drawn but only just
    longer than its marker (`bar_sliver`) is drawn in front of the marker, on a thin white outline, whatever `bar_zorder` says; only a
    figure whose caption has words for that passes `sliver_ok=True` (FIG-04), and for any other the build stops instead."""
    st = style_for(model, effort)
    hidden = bar_hidden(ax, model, lo, hi, size, y=y)
    if lo is not None and hi is not None and hi - lo > 1e-9 and not hidden:
        if bar_sliver(ax, model, lo, hi, size, y=y):
            if not sliver_ok:
                forbid_sliver("mark", ax, model, lo, hi, size, y=y)                # no caption words for it here: the build stops
            sliver_bar(ax, x, y, lo, hi, st["color"], zorder + 0.5, lw=lw, dx_pt=size / 2.0 + 2.0)   # a bar only just longer than its marker: beside it, so it shows
        else:
            ax.errorbar([x], [y], yerr=[[max(y - lo, 0.0)], [max(hi - y, 0.0)]], fmt="none", ecolor=st["color"], elinewidth=lw,
                        capsize=cap, capthick=lw, alpha=bar_alpha, zorder=zorder - 1 if bar_zorder is None else bar_zorder)
    ax.plot([x], [y], linestyle="none", marker=st["marker"], markersize=size, markerfacecolor="white" if hollow else st["color"],
            markeredgecolor=st["color"], markeredgewidth=1.1 if hollow else 0.6, zorder=zorder, label=label_)
    return hidden


def model_handle(model: str, effort: str, text: str, hollow: bool = False) -> Line2D:
    st = style_for(model, effort)
    return Line2D([0], [0], linestyle="none", marker=st["marker"], markersize=5, markerfacecolor="white" if hollow else st["color"],
                  markeredgecolor=st["color"], markeredgewidth=1.1 if hollow else 0.6, label=text)


def fmt_cost(x: float, pos=None) -> str:
    """A dollar tick label ("\\$0.01"; Karen's F10), the dollar sign escaped (in matplotlib a plain one starts math)."""
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "\\$" + s


def cost_axis(ax, lo: float, hi: float, ticks: Sequence[float]) -> None:
    ax.set_xscale("log")
    ax.set_xlim(lo, hi)
    ax.set_xticks(list(ticks))
    ax.set_xticklabels([fmt_cost(t) for t in ticks])
    ax.minorticks_off()


def acc_axis(ax, lo: float = 0.0, hi: float = 100.0) -> None:
    """An accuracy axis: never past 100 (Karen's F10), horizontal gridlines on (F9), round ticks."""
    ax.set_ylim(lo, min(hi, 100.0))
    span = min(hi, 100.0) - lo
    ax.yaxis.set_major_locator(plt.MultipleLocator(20 if span > 60 else 10 if span > 25 else 5 if span > 10 else 2))
    ax.grid(axis="y")


def count_text(c: Cell) -> str:
    return c.printed


# ---------------------------------------------------------------- caption pieces

PRICE_STUDY1 = "reporting.group_b.item_9a.price_table_date"


def price_study1(S: Store, per: str = "") -> List[Cell]:
    """Study 1's price basis, worded as FIG-03's and FIG-04's Study 1b line: US dollars (per puzzle where the axis is per puzzle) at
    list price, with the stamped date of Study 1's price table (item 9a's key; the item number stays in the provenance, Q22)."""
    return [L(f"US dollars{per} at list price (Study 1's price table, dated"), joined(text_of(S.ref("main", PRICE_STUDY1)), L(")"), sep="")]


def set_study1_plain(also_topup: bool = False) -> List[Cell]:
    """The Study 1 set in plain words for a main-text caption (the style sheet keeps set ids for the methods appendix)."""
    return [L("the Study 1 puzzle set at 6 steps" + (", which the top-up run also used" if also_topup else "")
              + ": each base puzzle as a chain and as pieces")]


def same_both_shapes(S: Store, source: str, key_1x6: str) -> None:
    """A structure check: the value stamped for the chains (1x6) equals the one for pieces (6x1), so one 'per shape' cell is true for
    both. Refuses the build otherwise."""
    a, b = S.get(source, key_1x6), S.get(source, key_1x6.replace("1x6", "6x1"))
    if a != b:
        raise ValueError(f"{source}:{key_1x6} is {a!r} on chains and {b!r} on pieces: print both")


# ================================================================ FIG-01
# Batch (h): redesigned to Karen's recipe 2 (vote-size curves) and her FIG-01 list ("seven layers, one claim"): one claim, that a vote
# of medium-effort Haiku samples levels off below one Opus-medium and one Sonnet-medium answer. Per shape, one panel: the Haiku-medium
# vote against its size k on a log-2 axis (the curve with its 95% band from k = 1), the two comparators as labelled dashed lines with
# their exact 95% interval as one bar at the panel's right edge, and the vote sizes at the comparators' prices (the sizes Tests 1 to 3
# test) as one filled marker each on the curve, with a coloured tick on the k axis. Marks are filled in both panels (the panel names the
# shape; hollow means pieces only, F6). Names and flags: a marked size carries its test's name; the caption facts keep every other
# label (the shapes, the tiers, the exact bars, the caps).
# Nothing the figure showed before the redesign is dropped (a change of what a figure shows is for Vision and the user): Haiku-max's one
# sample and its vote of 3 samples (the exploratory setting, drawn in Haiku blue and labelled beside its second dot, joined by a thin
# line; where its bootstrap collapsed, free analysis 4's exact bar, drawn as an ordinary bar) sit at the top left of each panel, and step
# voting (Test 4), which has no vote size, sits in its own narrow strip beside panel A, with its own "no k" label and the Opus-medium
# level it is compared with. Corrections after Edith's PR #34 review (2026-10-18): each marked vote size is labelled with its test and
# its k (13, 36, 40); one bar rule, decided per point and per arm (`_fig0001_bar_hidden`, shared with FIG-00: a bar is not drawn only if it
# lies behind its marker, that is, its whole span is shorter than the marker and neither arm sticks out a point or more past the marker's
# edge (the shared rule; Edith's PR #40 review, M3, restored the span test that Friday's D-168 change had dropped); a one-sided bar at 100%
# is drawn; the axes' limits are set before any mark is drawn), applied to the exact bars too, and the caption fact 'bars' names the points
# that same test hides.

FIG01_X_MIN, FIG01_X_MAX = 0.85, 58.0      # the k axis runs from just left of 1 (so a mark at k = 1 is not cut by the axis) to here; the comparators' bars sit at the right edge
FIG01_BAR_X = {"sonnet-med": 46.0, "opus-med": 52.0}      # each comparator's dashed line ends at its own bar; both clear the vote's last marker (k = 40)
FIG01_H = 2.30               # inches, at print size (F14): panel 1.61 in, the titles above and the k title under the ticks
FIG01_M_L, FIG01_M_R, FIG01_M_B, FIG01_M_T = 0.55, 0.03, 0.42, 0.27      # margins in inches
FIG01_TITLE_Y = 0.03         # inches from the bottom edge: the shared k title sits about 0.08 in under the tick labels
FIG01_MAIN_W, FIG01_STRIP_W, FIG01_STRIP_GAP = 2.55, 0.52, 0.05      # inches: each vote-size panel, panel A's step-voting strip, and the gap between them
FIG01_STUB_HALO = 2.2        # points: the white outline round Haiku-max's exact bars (the bar crosses Opus-medium's dashed line and ends within a point of it)
FIG01_HX_LW = 0.8            # the line joining Haiku-max's two dots: thinner than the 1.5 pt vote curve, so that it reads as secondary
FIG0001_BAR_TOL_PT = 1.0     # FIG-00 and FIG-01: a bar that sticks out less than this far past its marker's edge reads as a smudge on the marker, not as a bar


def _fig0001_bar_hidden(ax, model: str, y: float, lo: Optional[float], hi: Optional[float], size: float = 5.0) -> bool:
    """The bar rule of FIG-00 and FIG-01, decided per point and per arm (Edith's PR #34 review, FIG-01: 'apply the rule per arm'; the
    checker's round-2 finding on the shared whole-span test): a 95% bar is not drawn only if it lies behind its marker, that is, its whole
    span is shorter than the marker AND neither arm sticks out FIG0001_BAR_TOL_PT or more past the marker's edge (the shared `bar_hidden`).
    A one-sided bar (the estimate at 100%, whose upper end is the estimate itself) is a short span but its lower arm can reach well past the
    marker: it is drawn. Every bar the shared test draws is drawn here too. The panel's points per unit come from its final y range, so set
    the axis limits before drawing marks. Friday's call: promote this to the shared `bar_hidden` or keep it figure-local."""
    if lo is None or hi is None or hi - lo <= 1e-9:
        return False
    return bar_hidden(ax, model, lo, hi, size, y=y)            # the per-arm test is the shared rule now


def _fig0001_point(ax, x: float, y: float, lo: Optional[float], hi: Optional[float], model: str, effort: str, hollow: bool = False,
                   size: float = 5.0, zorder: int = 3, lw: float = 0.8) -> bool:
    """The shared mark (`mark`) with its 95% bar drawn by the per-arm rule above, in the mark's colour one level behind the marker.
    Returns True when the bar was not drawn (the caption names such points). A bar only just longer than its marker (`bar_sliver`) stops
    the build: these captions have no words for a bar drawn in front of its marker (FIG-04's has)."""
    hidden = _fig0001_bar_hidden(ax, model, y, lo, hi, size)
    if lo is not None and hi is not None and hi - lo > 1e-9 and not hidden:
        forbid_sliver("FIG-00/FIG-01", ax, model, lo, hi, size, y=y)      # a bar only just longer than its marker has no words in these captions
        ax.errorbar([x], [y], yerr=[[max(y - lo, 0.0)], [max(hi - y, 0.0)]], fmt="none", ecolor=style_for(model, effort)["color"], elinewidth=lw,
                    capsize=0.0, capthick=lw, zorder=zorder - 1)
    mark(ax, x, y, None, None, model, effort, hollow=hollow, size=size, zorder=zorder)
    return hidden


def _fig01_axis(ax) -> None:
    """The vote-size axis: log 2, ticks at 1, 2, 4, 8, 16 and 32 (Karen F10)."""
    ax.set_xscale("log", base=2)
    ax.set_xlim(FIG01_X_MIN, FIG01_X_MAX)
    ax.set_xticks([1, 2, 4, 8, 16, 32])
    ax.set_xticklabels(["1", "2", "4", "8", "16", "32"])
    ax.minorticks_off()
    acc_axis(ax, 0.0, 100.0)


def _fig01_unclipped(ax, n_collections: int, n_lines: int) -> None:
    """The artists drawn since the given counts are not clipped at the panel's edge (a mark at 100% keeps its upper half)."""
    for art in list(ax.collections[n_collections:]) + list(ax.lines[n_lines:]):
        art.set_clip_on(False)


@output("FIG-01")
@main_text
@plain_ids(main=True)
def fig_01(S: Store) -> FigureOut:
    vc = "reporting.group_b.item_8b.vote_curve"
    t24 = "reporting.group_b.item_24.table"
    fig = plt.figure(figsize=(COLW, FIG01_H))
    avail = COLW - FIG01_M_L - FIG01_M_R
    a_total = FIG01_MAIN_W + FIG01_STRIP_GAP + FIG01_STRIP_W
    gap_ab = avail - a_total - FIG01_MAIN_W
    outer = GridSpec(1, 2, figure=fig, left=FIG01_M_L / COLW, right=1 - FIG01_M_R / COLW, top=1 - FIG01_M_T / FIG01_H, bottom=FIG01_M_B / FIG01_H,
                     wspace=gap_ab / ((a_total + FIG01_MAIN_W) / 2), width_ratios=[a_total, FIG01_MAIN_W])
    inner = GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[0], wspace=FIG01_STRIP_GAP / ((FIG01_MAIN_W + FIG01_STRIP_W) / 2),
                                    width_ratios=[FIG01_MAIN_W, FIG01_STRIP_W])
    ax_c = fig.add_subplot(inner[0])
    ax_e = fig.add_subplot(inner[1], sharey=ax_c)
    ax_p = fig.add_subplot(outer[1], sharey=ax_c)
    panels = {"1x6": ax_c, "6x1": ax_p}
    _fig01_axis(ax_c)                    # every axis's limits are set before any mark is drawn (the bar rule reads them)
    _fig01_axis(ax_p)
    ax_e.set_xlim(0.0, 1.0)
    acc_axis(ax_e, 0.0, 100.0)
    layout = {id(ax_): (ax_.get_ylim(), tuple(ax_.get_position().bounds)) for ax_ in (ax_c, ax_p, ax_e)}   # the bar rule reads these: fixed before any mark
    points: List[Dict[str, Any]] = []
    c_h, c_o, c_s = color("haiku", "medium"), color("opus", "medium"), color("sonnet", "medium")
    t_h, t_o, t_s = style.MODEL_TEXT["haiku"], style.MODEL_TEXT["opus"], style.MODEL_TEXT["sonnet"]
    eqk: Dict[str, Dict[str, Cell]] = {}
    caps: Dict[Tuple[str, str], Tuple[Cell, Cell]] = {}     # (shape, comparator) -> (raw k, the vote's list cost over the comparator's)
    hx_exact: List[Tuple[str, Cell, Exact, bool]] = []      # (shape word, k cell, fa4 exact interval, whether its bar is drawn) where Haiku-max's bootstrap collapsed
    bars_hidden: List[List[Cell]] = []                      # the points whose 95% bar the per-arm test hides (named in the caption fact 'bars')
    hx_k: Dict[int, Cell] = {}
    vys: Dict[Tuple[str, str], V] = {}                       # (shape, comparator) -> the vote's accuracy at the cost-matched k
    levels: Dict[Tuple[str, str], V] = {}                    # (shape, comparator) -> the comparator's accuracy
    alt: List[Cell] = [L("Two panels of accuracy (%) against vote size k on a logarithmic axis at 6 steps, chains on the left and pieces on the right; "
                         "the vote's 95% band is shaded.")]
    ends: Dict[str, Tuple[Ref, Ref, Ref]] = {}
    test_of: Dict[Tuple[str, str], str] = {}

    for shape, ax in panels.items():
        name = SHAPE_WORD[shape]
        pts = S.get("main", f"{vc}.{shape}.points")
        ks, ys, los, his = [], [], [], []
        # one sample (k = 1) carries the setting's own stamped interval (item 24), the one FIG-06 draws for the same value (one value,
        # one interval); the vote curve's own k = 1 interval is a separate bootstrap and is not drawn. The band starts at k = 1 from
        # that interval and follows the curve's own bootstrap bands from k = 2.
        one = f"{t24}.haiku-med {shape}.accuracy_interval"
        y1 = pv(S, "main", one + ".mean", prop=False)
        lo1, hi1 = ci(S, "main", one + ".ci95", prop=False)
        has_width(f"FIG-01: Haiku-medium's one sample on {name}", lo1, hi1)
        for i in range(len(pts)):
            base = join_key(*vc.split("."), shape, "points", i)
            kc, kf = kval(S, "main", base + ".k")
            y = pv(S, "main", base + ".mean")
            lo, hi = ci(S, "main", base + ".ci95")
            if i:
                has_width(f"FIG-01: the Haiku-medium vote band at k = {kc.printed} on {name}", lo, hi)
            if i == 0:
                if kf != 1.0 or abs(y.val - y1.val) > 1e-6:
                    raise ValueError(f"FIG-01: the vote curve's first point on {name} is not the single sample item 24 stamps")
                ks.append(kf); ys.append(y.val); los.append(lo1.val); his.append(hi1.val)
                points.append(rec(f"Haiku-medium, one sample, {name}", name, x=kc, y=y1, lo=lo1, hi=hi1,
                                  note="one sample: the 95% band starts from the setting's own stamped single-sample interval (as in TAB-04)"))
            else:
                ks.append(kf); ys.append(y.val); los.append(lo.val); his.append(hi.val)
                points.append(rec(f"Haiku-medium vote, {name}", name, x=kc, y=y, lo=lo, hi=hi))
        ax.fill_between(ks, los, his, color=c_h, alpha=0.18, linewidth=0, zorder=1)
        ax.plot(ks, ys, color=c_h, linewidth=1.5, zorder=3)
        ends[shape] = (S.ref("main", f"{vc}.{shape}.points.0.mean"), S.ref("main", f"{vc}.{shape}.points.{len(pts) - 1}.mean"),
                       S.ref("main", f"{vc}.{shape}.points.{len(pts) - 1}.k"))

        # Opus-medium and Sonnet-medium, one sample each: a labelled dashed line (the setting's reference level) and its exact
        # (Clopper–Pearson) 95% interval as one bar at the panel's right edge; the labels end left of both bars
        for arm, nm, col, tcol in (("opus-med", "Opus-medium", c_o, t_o), ("sonnet-med", "Sonnet-medium", c_s, t_s)):
            base = f"{t24}.{arm} {shape}.accuracy_cp95"
            a = pv(S, "main", base + ".accuracy", prop=False)
            lo, hi = ci(S, "main", base + ".cp95", prop=False)
            has_width(f"FIG-01: {nm}'s one-sample interval on {name}", lo, hi)
            levels[(shape, arm)] = a
            bx = FIG01_BAR_X[arm]
            ax.plot([FIG01_X_MIN, bx], [a.val, a.val], color=col, linewidth=1.0, linestyle=(0, (4, 2)), zorder=2, clip_on=False)
            ax.plot([bx, bx], [lo.val, hi.val], color=col, linewidth=0.8, solid_capstyle="butt", zorder=2, clip_on=False)
            points.append(rec(f"{nm}, one sample, {name}", name, x=None, y=a, lo=lo, hi=hi,
                              note="dashed line: its accuracy; bar at the panel's right edge: its exact 95% interval"))
            # a label sits below its line near the line's right end, except Sonnet-medium on pieces, whose line sits under the vote's band
            # there: its label goes at the line's left end, just under it (above it the 80% gridline would run through the text), where
            # the band is low
            if arm == "sonnet-med" and shape == "6x1":
                ax.text(FIG01_X_MIN * 1.06, a.val - 1.5, nm, color=tcol, fontsize=LAB, ha="left", va="top", zorder=5)
            else:
                ax.text(min(FIG01_BAR_X.values()) / 1.1, a.val - 4.8, nm, color=tcol, fontsize=LAB, ha="right", va="center",
                        zorder=5, bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none"))

        # the vote sizes at the comparators' prices: one filled marker on the curve and a coloured tick on the k axis
        marks = [("opus", c_o, t_o)] + ([("sonnet", c_s, t_s)] if shape == "1x6" else [])
        for who, col, tcol in marks:
            kbase = f"k_from_rows.{who}.{shape}"
            kc, kf = kval(S, "main_k", kbase + ".k")
            vy = pv(S, "main", join_key(*vc.split("."), shape, "points", int(kf) - 1, "mean"))
            mark(ax, kf, vy.val, None, None, "haiku", "medium", zorder=6)
            ax.plot([kf], [0.0], linestyle="none", marker=3, markersize=7, markeredgewidth=1.3, color=col,
                    transform=ax.get_xaxis_transform(), clip_on=False, zorder=6)
            tests = [n_ for n_, ch, cmp_, sh, kk in STUDY1_TESTS.values() if sh == shape and kk == who[0].upper() and ch == "haiku-med"]
            if len(tests) != 1:
                raise ValueError(f"FIG-01: no single test uses the {who} k on {shape}")
            test_of[(shape, who)] = tests[0]
            points.append(rec(f"Haiku-medium vote at the cost-matched k for {who.capitalize()}-medium ({tests[0]}), {name}", name, x=kc, y=vy,
                              note="vote size at which the vote costs about as much as the comparator, from k.json"))
            capped = bool(S.get("main_k", kbase + ".capped"))
            if capped:
                rk, _ = kval(S, "main_k", kbase + ".raw_k")
                spend = num(S.ref("main_k", kbase + ".spend.haiku_over_comparator"), dp=3)
                points[-1]["raw_k"] = rk.record()
                points[-1]["haiku_over_comparator"] = spend.record()
                caps[(shape, who)] = (rk, spend)
            # the marker is labelled with its test and its vote size k (from k.json), two lines, under its dot; the gridline behind the
            # words is cut (the white patch of FIG-05's labels, under the band and everything else), so that no gridline touches or crosses
            # a test label (Opus checker, proof 4 group F1: the 40% line at 'k = 13', the 60% line through 'Test 1')
            # the labels hang under the band's own lower edge at that vote size (Edith, job K row 15: the label's white patch notched the band)
            band_lo = min(lo_ for k_, lo_ in zip(ks, los) if abs(k_ - kf) < 1e-9) if any(abs(k_ - kf) < 1e-9 for k_ in ks) else vy.val
            t_lab = ax.text(kf / 1.07, min(vy.val - 4.5, band_lo - 2.5), f"{tests[0]}\n$k$ = {kc.printed}" + (" (capped)" if capped else ""), color=INK, fontsize=LAB,
                            ha="right", va="top", zorder=7, linespacing=1.1)
            _fig05_grid_gap(ax, [t_lab])
            # the two cost labels stand 2.5 points of accuracy lower than before (Opus at 2.5, Sonnet at 11.5), so that the Sonnet label's
            # capitals no longer touch the 20% gridline
            ax.text(kf, 2.5 if who == "opus" else 11.5, f"{who.capitalize()}-medium\u2019s cost, capped" if capped else f"same cost as {who.capitalize()}-medium",
                    color=tcol, fontsize=LAB, ha="right", va="bottom", zorder=5)
            eqk.setdefault(shape, {})[who] = kc
            vys[(shape, who)] = vy
        # the series name sits under the band's left end, clear of its lower edge and of the test labels further right
        ax.text(1.0, min(l for k_, l in zip(ks, los) if k_ <= 5.0) - 3.0, "Haiku-medium vote", color=t_h, fontsize=LAB, ha="left", va="top", zorder=5)

        # Haiku-max (exploratory: its role read as TAB-04 reads it): one sample and the vote of the samples drawn, in Haiku blue, joined by a
        # thin line and labelled beside its second dot; where its bootstrap collapsed, free analysis 4's exact bar (an ordinary bar). Not
        # clipped at 100. Each bar follows the per-arm rule (`_fig0001_bar_hidden`), decided for that point alone, and the points whose bar it
        # hides are named in the caption facts (the exact bars too).
        if s1_role(S, "haiku-max", shape) != "exploratory":
            raise ValueError(f"FIG-01: Haiku-max on {name} is not an exploratory setting in Study 1: reword its tier")
        hm = f"reporting.group_b.item_10.arms.haiku-max {shape}.vote_curve.points"
        hk, hy = [], []
        for idx in (0, 2):
            b = f"{hm}.{idx}"
            kc, kf = kval(S, "main", b + ".k")
            y = pv(S, "main", b + ".mean")
            lo, hi = ci(S, "main", b + ".ci95")
            n_c, n_l = len(ax.collections), len(ax.lines)
            what = "one sample" if idx == 0 else f"{kc.printed}-sample vote"
            ex, note = None, None
            if collapsed(lo, hi):
                ex = fa4_bar(S, "main", b, y, lo, hi)
                mark(ax, kf, y.val, None, None, "haiku", "max", zorder=6)
                hidden = _fig0001_bar_hidden(ax, "haiku", y.val, ex.lo.val, ex.hi.val)
                if not hidden:
                    forbid_sliver("FIG-01", ax, "haiku", ex.lo.val, ex.hi.val, y=y.val)       # no caption words for a bar only just longer than its marker
                    exact_bar(ax, kf, y.val, ex.lo.val, ex.hi.val, color("haiku", "max"), zorder=5, halo=FIG01_STUB_HALO)
                note = ("the bootstrap interval collapsed to a point; the exact (Clopper–Pearson) 95% interval from free analysis 4 (post hoc), over "
                        "exact_n puzzles, exact_x of them right, " + ("is drawn as the bar" if not hidden else "is not drawn: it does not stick out past the marker"))
                hx_exact.append((name, kc, ex, not hidden))
            else:
                hidden = _fig0001_point(ax, kf, y.val, lo.val, hi.val, "haiku", "max", zorder=6)
            if hidden:
                bars_hidden.append([L("Haiku-max's one sample on " + name)] if idx == 0 else
                                   [L("Haiku-max's vote of"), kc, L(f"samples on {name}" + (" (its exact bar, post hoc†)" if ex is not None else ""))])
            _fig01_unclipped(ax, n_c, n_l)
            points.append(rec(f"Haiku-max, {what}, {name} (exploratory)", name, x=kc, y=y, lo=lo, hi=hi, note=note, **exact_rec(ex)))
            hx_k[idx] = kc
            hk.append(kf); hy.append(y.val)
        ax.plot(hk, hy, color=color("haiku", "max"), linewidth=FIG01_HX_LW, zorder=5, clip_on=False)
        # its label sits beside its second dot: above Opus-medium's line where the dot does (chains), under it where the dot is under it (pieces)
        opus_y = levels[(shape, "opus-med")].val
        if hy[1] > opus_y:
            ax.text(hk[1] * 1.18, opus_y + 1.9, "Haiku-max‡", color=t_h, fontsize=LAB, ha="left", va="bottom", zorder=5,
                    bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none"))
        else:
            ax.text(hk[1] * 1.18, hy[1] - 0.8, "Haiku-max‡", color=t_h, fontsize=LAB, ha="left", va="top", zorder=5)
        panel_tag(ax, "A" if shape == "1x6" else "B")
        ax.text(0.06, 1.03, "Chains" if shape == "1x6" else "Pieces", transform=ax.transAxes, ha="left", va="bottom", fontsize=LAB, color=INK)

    # step voting (Test 4), chains only: a step-by-step vote has no whole-answer vote size, so it sits in a side strip of panel A
    e3 = f"{t24}.e3 1x6.accuracy_interval"
    ey = pv(S, "main", e3 + ".mean", prop=False)
    elo, ehi = ci(S, "main", e3 + ".ci95", prop=False)
    has_width("FIG-01: step voting", elo, ehi)
    if _fig0001_point(ax_e, 0.5, ey.val, elo.val, ehi.val, "haiku", "medium", zorder=4):
        bars_hidden.append([L("step voting")])
    # Opus-medium's chains level, the comparator of Test 4, continues across the strip (the same dashed line as in panel A)
    ax_e.plot([0.0, 1.0], [levels[("1x6", "opus-med")].val] * 2, color=c_o, linewidth=1.0, linestyle=(0, (4, 2)), zorder=2,
              transform=ax_e.get_yaxis_transform(), clip_on=False)
    ax_e.text(0.5, 24.0, "step\nvoting,\nchains\n(Test 4)", color=INK, fontsize=LAB, ha="center", va="center", linespacing=1.1)
    ax_e.set_xticks([0.5])
    ax_e.set_xticklabels(["no $k$"])
    ax_e.tick_params(axis="x", length=0)
    ax_e.tick_params(axis="y", length=0)
    points.append(rec("step voting, chains (Test 4)", "chains", x=None, y=ey, lo=elo, hi=ehi,
                      note="side strip: step voting has no whole-answer vote size"))

    plt.setp(ax_p.get_yticklabels(), visible=False)
    plt.setp(ax_e.get_yticklabels(), visible=False)
    ax_c.set_ylabel(ACC_LABEL)
    fig.text(0.54, FIG01_TITLE_Y / FIG01_H, K_LABEL, ha="center", va="bottom", fontsize=8)

    oc, op = levels[("1x6", "opus-med")], levels[("6x1", "opus-med")]
    sc, sp = levels[("1x6", "sonnet-med")], levels[("6x1", "sonnet-med")]

    def rise(shape: str) -> List[Cell]:
        """'rises from 43.7% at one sample to 58.6% at 36 samples, the vote size at Opus-medium's price, and is 57.5% at 40 samples' (the
        curve is not monotone, so its value at the Opus-medium k is named before the last one; nothing is searched for a maximum)."""
        first, last, k_last = ends[shape]
        out = [L("rises from"), P(pct(first)), L("at one sample to")]
        if eqk[shape]["opus"].raw != k_last.value:
            out += [P(vys[(shape, "opus")].cell), L("at"), eqk[shape]["opus"], L("samples, the vote size at Opus-medium's price, and is")]
        return out + [P(pct(last)), L("at"), integer(k_last), L("samples")]
    alt += ([L("On chains the Haiku-medium vote")] + rise("1x6") + [L(", against"), P(oc.cell),
            L("for one Opus-medium answer and"), P(sc.cell), L("for one Sonnet-medium answer, drawn as dashed lines with their exact 95% intervals as bars at the right edge.")] +
            [L("On pieces the vote")] + rise("6x1") + [L(", against"), P(op.cell), L("for Opus-medium and"), P(sp.cell), L("for Sonnet-medium.")] +
            [L("A coloured tick on the vote-size axis and a marker on the curve, labelled with its test and its vote size, show the vote size that costs about as much as the comparator:")])

    def eq_cells(shape: str, who: str, words: str) -> List[Cell]:
        """The cost-matched k and its test, with its cap where k.json stamps one: '40 samples on pieces (Test 1; capped, raw k 44; at the
        cap the vote costs 0.909 of ...)'."""
        out = [eqk[shape][who], L(words + f" ({test_of[(shape, who)]}")]
        if (shape, who) in caps:
            rk, spend = caps[(shape, who)]
            out += [L("; capped, raw k"), rk, L("; at the cap the vote costs"), spend, L(f"of one {who.capitalize()}-medium answer's list cost")]
        return out + [L(")")]
    alt += (eq_cells("1x6", "opus", "samples on chains") + [L(",")] + eq_cells("6x1", "opus", "samples on pieces") +
            [L("for Opus-medium, and")] + eq_cells("1x6", "sonnet", "samples on chains") + [L("for Sonnet-medium.")] +
            [L("Two filled marks joined by a line near the top left of both panels show Haiku-max, exploratory‡: one sample and the vote of"),
             hx_k[2], L("samples.")])
    for nm, kc, ex, drawn in hx_exact:
        alt += [L("Haiku-max's vote of"), kc, L("samples on"), L(nm), L("has an exact interval from" if not drawn else "has a bar from"), P(ex.lo.cell),
                L("to"), P(ex.hi.cell),
                L(": its bootstrap interval collapsed to a point, and the " + ("exact interval from free analysis 4 (post hoc†) is not drawn, since it does not stick out past its marker."
                                                                              if not drawn else "bar is the exact interval from free analysis 4 (post hoc†).")),]
    alt += [L("Step voting (Test 4) is a single point at"), P(pct(S.ref("main", f"{t24}.e3 1x6.accuracy_interval.mean"), from_proportion=False)),
            L("on chains, in a narrow strip beside the chains panel because it has no vote size; the dashed line of Opus-medium's chains level, the "
              "comparator of Test 4, continues across the strip.")]
    if bars_hidden:
        alt += [L("A 95% bar that does not stick out past its marker is not drawn:")] + _seq(bars_hidden, sep=";", last=".")

    # n: base puzzles and samples per shape (each count is checked equal on both shapes before one cell is printed for both)
    fc = "format_compliance.tries"
    for k in (f"{vc}.1x6.points.0.n_base", f"{vc}.1x6.k_max", f"{t24}.haiku-med 1x6.{fc}", f"{t24}.haiku-max 1x6.{fc}",
              f"{t24}.opus-med 1x6.{fc}", f"{t24}.sonnet-med 1x6.{fc}"):
        same_both_shapes(S, "main", k)
    n_cells = [L("puzzles per shape:"), integer(S.ref("main", f"{vc}.1x6.points.0.n_base")),
               L("; samples per shape (the same on chains and pieces): Haiku-medium"), integer(S.ref("main", f"{t24}.haiku-med 1x6.{fc}")),
               L("(votes of up to"), integer(S.ref("main", f"{vc}.1x6.k_max")), L("samples per puzzle are drawn from them), Haiku-max"),
               integer(S.ref("main", f"{t24}.haiku-max 1x6.{fc}")), L("(its vote has"), hx_k[2], L("samples per puzzle), Opus-medium"),
               integer(S.ref("main", f"{t24}.opus-med 1x6.{fc}")), L("and Sonnet-medium"), integer(S.ref("main", f"{t24}.sonnet-med 1x6.{fc}")),
               L("(one sample per puzzle); step voting on chains:"), integer(S.ref("main", "reporting.group_b.item_19.arms['e3:1x6'].calls")),
               L("calls")]
    interval_cells = [L("95%: cluster bootstrap for the Haiku-medium vote's band (at one sample, the setting's own stamped single-sample "
                        "interval, as in TAB-04, the one FIG-06 draws for the same sample), Haiku-max and step voting; exact (Clopper–Pearson) for "
                        "one Opus-medium or Sonnet-medium answer, the bar at each panel's right edge")]
    tier_cells = [L("pre-specified descriptive; the marked vote sizes are the challengers of Tests 1–3 (pre-registered decision rule, "
                    "not Holm-adjusted); the step-voting point is Test 4 (confirmatory); Haiku-max is an exploratory setting‡")]
    for nm, kc, ex, drawn in hx_exact:
        interval_cells += [L("; Haiku-max's vote of"), kc, L("samples on"), L(nm),
                           L(": its bootstrap interval collapsed to a point, so " + ("its bar is the exact" if drawn else "the exact")
                             + " (Clopper–Pearson) 95% interval from free analysis 4 (post hoc†)" + ("," if drawn else " replaces it (not drawn: it does not stick out past the marker),")),
                           P(ex.lo.cell), L("to"), P(ex.hi.cell)]
        tier_cells += [L("; the exact interval on Haiku-max's vote on"), L(nm), L("is post hoc† (free analysis 4)")]
    # format compliance beside accuracy: each plotted setting's samples, chains then pieces (item 24), with item 17's flag
    fmt_items = []
    for arm, words in (("haiku-med", "Haiku-medium (the samples the votes are drawn from)"), ("haiku-max", "Haiku-max"),
                       ("opus-med", "Opus-medium"), ("sonnet-med", "Sonnet-medium")):
        vals = []
        for sh in ("1x6", "6x1"):
            fcv = s1_format(S, arm, sh)
            if fcv is None:
                raise ValueError(f"FIG-01: item 24 stamps no format compliance for {arm} {sh}")
            vals.append((fcv[0], fcv[1], SHAPE_WORD[sh]))
        fmt_items.append((words, vals))
    if s1_format(S, "e3", "1x6") is not None:
        raise ValueError("FIG-01: item 24 now stamps step voting's format compliance: print it")
    fmt_cells, any_flag = fmt_list(fmt_items)
    if any_flag:
        raise ValueError("FIG-01: a plotted setting is flagged by the format check: name the flag in the caption facts")
    fmt = ([L("format compliance, the share of samples in the required answer format (as in TAB-04), chains then pieces:")] + fmt_cells +
           [L("; the format check flags none of these; Study 1's file stamps none for step voting")])
    # the vote sizes at the comparators' prices are those of Tests 1-3; Test 3 travels with its marking-rule qualifier
    def k_test(shape: str, who: str) -> List[Cell]:
        out = [L(test_of[(shape, who)] + ","), L("$k$ ="), eqk[shape][who], L("on " + SHAPE_WORD[shape] + " against " + who.capitalize() + "-medium")]
        if (shape, who) in caps:             # the vote size is capped at the samples drawn: the raw size and the spend at the cap are named
            rk, spend = caps[(shape, who)]
            out += [L("(capped at the samples drawn, raw $k$"), rk, L("; the vote costs"), spend, L(f"of one {who.capitalize()}-medium answer's list cost)")]
        return out
    k_tests = [k_test(shape, who) for shape, who in (("6x1", "opus"), ("1x6", "opus"), ("1x6", "sonnet"))]
    rule = [L("the vote sizes at the comparators' prices are those of the tests:")] + _seq(k_tests, sep=";", last=".")
    # Required labels carry their plain key; optional detail (the puzzle set, counts, format compliance) carries the prefix "detail_" so
    # that Vision can fit the required ones into the cap and drop the rest first. The set is worded here, not by the shared helper
    # `set_study1_plain`, which still says "base puzzle" (a retired word, D-161): Friday's shared-helper fix.
    caption = {"tier": tier_cells,
               "rule": rule,
               "test3": test3_qualifier(S),
               "study": [L("Study 1, main run, 6 steps")],
               "marking": [L("every value uses the official marking rule (Deviation 2)")],
               "interval": interval_cells,
               "bars": ([L("a bar that does not stick out past its marker is not drawn:")] + _seq(bars_hidden, sep=";", last="")) if bars_hidden else [],
               "marks": [L("a filled marker on the curve, labelled with its test and its vote size $k$, and a tick of the comparator's colour on the "
                           "vote-size axis mark the vote size at which the vote costs about as much as the comparator; dashed lines are the "
                           "comparators' accuracy; the two marks joined by a line are Haiku-max, one sample and its vote of"), hx_k[2],
                         L("samples; step voting has no vote size, so it sits in its own strip, with Opus-medium's level (the comparator of Test 4) continued across it")],
               "price": price_study1(S),
               "detail_set": [L("the Study 1 puzzle set at 6 steps: each puzzle as a chain and as pieces")],
               "detail_n": n_cells,
               "detail_format": fmt}
    if any(layout[id(ax_)] != (ax_.get_ylim(), tuple(ax_.get_position().bounds)) for ax_ in (ax_c, ax_p, ax_e)):
        raise ValueError("FIG-01: an axis's limits or position changed after its marks were drawn: the bar rule (`_fig0001_bar_hidden`) read the old ones")
    return FigureOut(fig, points, tight(alt), tight_caption(caption))


# ================================================================ FIG-02

# Batch (h), as revised for Edith's chart review of PR #34 (2026-10-18; MUST 4 and the SHOULDs of FIG-02) and for the checker's round 2:
# Karen's recipe 6 (a dot plot, the counts in one fixed row under the axis, no hatching, never past 100). Each bin of single-sample
# accuracy holds up to three dots, one per third of agreement among the puzzles' wrong samples, in fixed slots (the lowest third on the
# left) and in three shades of Haiku's blue (the lowest third darkest), each with its 95% bar. NO LINE JOINS THE DOTS: a cell holds only a
# few puzzles (one to six), so a line from bin to bin would draw a trend, and a zig-zag, that the cells cannot carry. The thirds are told
# apart by their slot first (the key says "left to right in each bin") and by the shade second. The darkest shade is the palette's blue
# with the palette's black laid over it (a flat tint, wherever a bar or dot crosses another), the middle one is the blue, and the lightest
# one is the blue at 75% over white. The lightest shade and the grey dot must keep 3:1 (F5's floor) against white AND against the grey
# bands behind alternate bins: the build measures both and refuses below 3:1 (the bands are the grid grey at FIG02_BAND_ALPHA; the
# lightest shade on them is 3.04:1). The puzzles with too few wrong samples to split are one more dot in the palette's context grey, so
# no shade of blue has two meanings; it stands in a column of its own (0.7 of a bin wide, with its own band and count) right of the last
# bin, and is named by a direct label. The bins are told apart by the bands (the counts row runs through them); the pitch between
# neighbouring dots of one bin is 5.5 pt (the dots are 5 pt), and from the last dot of one bin to the first of the next it is about 7.9 pt:
# the build refuses a layout in which the gap between bins is not clearly larger than the pitch within a bin (a reader groups dots and
# digits by distance). No value is printed beside a dot: the 95% bars of the cells run through most of the panel, so no text can stand
# next to its dot without crossing a bar, its outline or a neighbour's dot (Edith's D-168, page 64: no value, halo or box may cross a
# bar), and a leader long enough to reach clear space would cross more bars than the text would. The cells strictly between 0 and 100
# are read from the axis, and their five values are in the caption facts and the alt text (printed_values below). The bins are labelled as ranges ("0-10"), on
# two staggered rows because a range is wider than its bin. The accuracy axis runs 0 to 100 exactly.
FIG02_THIRDS = (("t1", "lowest third of agreement", "lowest third", "dark", -1.0),
                ("t2", "middle third", "middle third", "mid", 0.0),
                ("t3", "highest third of agreement", "highest third", "light", 1.0))       # (key, series name, key text, shade, slot)
FIG02_DARK = 0.35               # the palette's black laid over the blue at the darkest step (opacity of the black)
FIG02_LIGHT = 0.75              # the lightest step: the blue at this opacity over white (3.31:1 on white, 3.04:1 on the bands: F5's floor is 3:1)
FIG02_PITCH = 5.5               # points between neighbouring dots of one bin (the dots are 5 pt; a bin is about 18.9 pt wide)
FIG02_FEW_COL = 0.7             # the width, in bins, of the column of puzzles with too few wrong samples (a dot, its band and its count)
FIG02_XLIM = (-0.6, 10.2)       # bins 0 to 9 (each centred on its number, 1 wide), then the column of puzzles with too few wrong samples
FIG02_MIN_FLOOR = 3.0           # F5: the lowest contrast ratio a mark may have against its background
FIG02_SPINE_PT = 4.0            # the x axis sits this far under the zero line, so a dot at 0 clears it
FIG02_COUNT_PT = 13.0           # the counts' row centre, points under the zero line (between the axis and the bin labels)
FIG02_LABEL_PT = (23.5, 33.0)   # the two staggered rows of bin labels (even bins on the first, odd bins on the second), points under the zero line
FIG02_BAND_ALPHA = 0.40         # the light grey bands behind alternate bins: the grid grey at this opacity
FIG02_TAG_LIFT = 3.0            # the panel tag stands this many points higher than the shared offset: dots at 100 reach 2.5 pt past the axes' top
FIG02_FEW_NAME = "too few wrong samples"
FIG02_FEW_DX = 9.0              # the direct label's right end sits this many points left of its dot (the leader slants from it to the dot)
FIG02_EXACT_NOTE = ("the bootstrap interval collapsed to a point; the bar is the exact (Clopper–Pearson) 95% interval from free analysis 4"
                    " (post hoc), over exact_n puzzles, exact_x of them right")


def _at_last_k(S: Store, base: str) -> Tuple[str, Cell]:
    """The key of the last entry of a stamped `mean_vote_at_k` list (the largest k) and that k's cell."""
    n = len(S.get("main", base))
    kc, _ = kval(S, "main", f"{base}.{n - 1}.k")
    return f"{base}.{n - 1}", kc


def _fig02_min_wrong(S: Store) -> Cell:
    """The fewest wrong samples a puzzle needs to be split into thirds (puzzles with fewer form the group 'too few wrong samples'): the
    number in the sentence 'Puzzles with fewer than N wrong tries are left out' of the C9 definition in the group C file, which is what
    the ledger's C-040.min_wrong reads. Checked against item 20's own per-puzzle rows: a puzzle is in the 'too few' group exactly when it
    has fewer wrong samples than N (the chart splits only puzzles with at least N); refuses the build otherwise."""
    ref = S.ref("groupc", "item_C9.definition")
    m = re.search(r"Puzzles with fewer than (\d+) wrong tries are left out", str(ref.value))
    if not m:
        raise ValueError("FIG-02: the C9 definition no longer states the fewest wrong samples a puzzle needs: reword the thirds fact")
    n = int(m.group(1))
    for sh in ("1x6", "6x1"):
        for pid, row in S.get("main", f"reporting.group_b.item_20.{sh}.per_puzzle").items():
            if (row["group"] == "too few wrong tries") != (row["wrong_tries"] < n):
                raise ValueError(f"FIG-02: {pid} ({sh}) has {row['wrong_tries']} wrong samples and is in group {row['group']!r}, "
                                 f"against a threshold of {n}: reword the thirds fact")
    return Cell(str(n), raw=n, refs=(ref,), formula="the number in the sentence 'Puzzles with fewer than N wrong tries are left out' (C-040.min_wrong)")


def _fig02_layers(col: str, step: str) -> List[Tuple[str, float]]:
    """One flat tint as a stack of layers, bottom first, so a bar or dot of a step looks the same wherever it crosses another mark:
    'dark' is the blue with the palette's black laid over it, 'mid' the blue, 'light' the blue at 75% over a white underlay, and 'grey'
    the palette's context grey (the puzzles with too few wrong samples). Every colour is the palette's own (a layer's opacity is not a colour)."""
    if step == "dark":
        return [(col, 1.0), ("#000000", FIG02_DARK)]
    if step == "mid":
        return [(col, 1.0)]
    if step == "light":
        return [("#ffffff", 1.0), (col, FIG02_LIGHT)]
    if step == "grey":
        return [(style.CONTEXT, 1.0)]
    raise ValueError(f"FIG-02: unknown shade {step!r}")


def _fig02_dot(ax, x: float, y: float, lo: float, hi: float, col: str, step: str) -> None:
    """One cell: its 95% bar (0.8 pt, no caps, in the dot's shade) and a 5 pt circle in the same shade, with no rim. Bar and dot are each
    one flat tint, and the dot lies over the bar, so the bar does not show through it."""
    from matplotlib.colors import to_rgba
    for j, (c, a) in enumerate(_fig02_layers(col, step)):
        ax.plot([x, x], [lo, hi], color=to_rgba(c, a), linewidth=0.8, solid_capstyle="butt", zorder=1.0 + 0.01 * j, clip_on=False)
    for j, (c, a) in enumerate(_fig02_layers(col, step)):
        ax.plot([x], [y], linestyle="none", marker="o", markersize=5, markerfacecolor=to_rgba(c, a), markeredgecolor="none",
                markeredgewidth=0, zorder=4.0 + 0.01 * j, clip_on=False)


class _Fig02Key:
    """A key entry for the legend: a third's shade (the handler below draws it as the plotted dot)."""

    def __init__(self, col: str, step: str) -> None:
        self.col, self.step = col, step


from matplotlib.legend_handler import HandlerBase           # noqa: E402


class _Fig02KeyHandler(HandlerBase):
    """Draws a key entry exactly as a panel draws the dot (the same layers); no line, because none joins the dots."""

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        from matplotlib.colors import to_rgba
        yc = ydescent + height / 2.0
        return [Line2D([xdescent + width / 2.0], [yc], linestyle="none", marker="o", markersize=5, markerfacecolor=to_rgba(c, a),
                       markeredgecolor="none", markeredgewidth=0, transform=trans) for c, a in _fig02_layers(orig_handle.col, orig_handle.step)]


def _fig02_band(ax, x0: float, x1: float, bottom_pt: float) -> None:
    """A light grey band behind one bin (x in data units), from just above the top of the axes down through the counts row."""
    from matplotlib.patches import Rectangle
    from matplotlib.transforms import blended_transform_factory
    h_pt = ax.get_position().height * ax.figure.get_figheight() * 72.0
    y0, y1 = -bottom_pt / h_pt, 1.0 + 3.0 / h_pt
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, transform=blended_transform_factory(ax.transData, ax.transAxes),
                           facecolor=style.GRID, alpha=FIG02_BAND_ALPHA, edgecolor="none", linewidth=0, zorder=0.2, clip_on=False))


def _fig02_tag(ax, letter: str, title: str) -> None:
    """The panel letter (the shared bold letter) and a title of at most four words beside it (Karen's F16; as FIG-01 and FIG-05 set
    theirs), both lifted by FIG02_TAG_LIFT points."""
    panel_tag(ax, letter)
    h_pt = ax.get_position().height * ax.figure.get_figheight() * 72.0
    ax.texts[-1].set_y(1.03 + FIG02_TAG_LIFT / h_pt)
    ax.annotate(title, xy=(0, 1.03), xycoords="axes fraction", xytext=(12, FIG02_TAG_LIFT), textcoords="offset points", fontsize=LAB,
                color=INK, ha="left", va="bottom")


def _fig02_lum(rgb: Sequence[float]) -> float:
    """WCAG relative luminance of an sRGB colour (channels 0 to 1)."""
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _fig02_contrast(a: Sequence[float], b: Sequence[float]) -> float:
    """WCAG contrast ratio of two sRGB colours (channels 0 to 1)."""
    la, lb = _fig02_lum(a), _fig02_lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _fig02_flat(layers: Sequence[Tuple[str, float]]) -> Tuple[float, float, float]:
    """The colour a stack of layers (bottom first, over white) ends up as."""
    from matplotlib.colors import to_rgb
    cur = (1.0, 1.0, 1.0)
    for c, a in layers:
        cur = tuple(a * x + (1.0 - a) * y for x, y in zip(to_rgb(c), cur))
    return cur  # type: ignore[return-value]


def _fig02_check_contrast(c_h: str) -> Dict[str, float]:
    """F5's floor (3:1) for the lightest shade and the grey dot against white and against the bands' rendered colour (the grid grey at
    FIG02_BAND_ALPHA over white). Refuses the build below the floor; returns the measured ratios."""
    white = (1.0, 1.0, 1.0)
    band = _fig02_flat([(style.GRID, FIG02_BAND_ALPHA)])
    out: Dict[str, float] = {}
    for step in ("dark", "mid", "light", "grey"):
        dot = _fig02_flat(_fig02_layers(c_h, step))
        for bg_name, bg in (("white", white), ("band", band)):
            out[f"{step} on {bg_name}"] = _fig02_contrast(dot, bg)
    for k, v in out.items():
        if v < FIG02_MIN_FLOOR:
            raise ValueError(f"FIG-02: the {k} has a contrast of {v:.2f}:1, under F5's floor of {FIG02_MIN_FLOOR}:1: lighten the bands or darken the shade")
    return out


def _fig02_curly(cells: Sequence[Cell]) -> List[Cell]:
    """Typed text with curly quotes and apostrophes (no straight quotes in print, Edith §3.6): a straight one in a label cell (some of
    them come from a shared helper) is replaced; number cells are untouched."""
    out: List[Cell] = []
    for c in cells:
        if c.kind == "label" and ("'" in c.printed or '"' in c.printed):
            t = re.sub(r'(^|[\s(\[])"', "\\1“", c.printed.replace("'", "’")).replace('"', "”")
            c = L(t)
        out.append(c)
    return out


@output("FIG-02")
@plain_ids
def fig_02(S: Store) -> FigureOut:
    """Two vote panels (chains, pieces: shared axes) over one panel of the repeat shares. A cell's vote accuracy is a dot with its
    95% bar, no line joining the dots; the number of puzzles in the cell prints in one row under the dots."""
    from matplotlib.transforms import blended_transform_factory
    i20 = "reporting.group_b.item_20"
    W, H = COLW, 4.58
    left, right, gap = 0.56, 0.12, 0.16
    w_ab = (W - left - right - gap) / 2
    h_ab, y_ab = 1.36, 2.58                                # the zero line's height; panels A and B span 0 to 100 exactly
    h_c, y_c = 1.2, 0.43

    def box(x0: float, y0: float, w: float, h: float) -> List[float]:
        return [x0 / W, y0 / H, w / W, h / H]

    fig = plt.figure(figsize=(W, H))
    ax_a = fig.add_axes(box(left, y_ab, w_ab, h_ab))
    ax_b = fig.add_axes(box(left + w_ab + gap, y_ab, w_ab, h_ab), sharey=ax_a)
    ax_c = fig.add_axes(box(left, y_c, W - left - right, h_c))
    axes = {"1x6": ax_a, "6x1": ax_b}
    c_h = style.MODEL_BASE["haiku"]
    _fig02_check_contrast(c_h)                             # every shade and the grey dot keep 3:1 on white and on the bands (refuses the build)
    xlim = FIG02_XLIM
    w_pt = w_ab * 72.0
    pt_per_bin = w_pt / (xlim[1] - xlim[0])
    pitch = FIG02_PITCH / pt_per_bin                       # the dodge between neighbouring dots, in bin units
    # a reader groups dots (and the digits under them) by distance: the gap from the last dot of one bin to the first of the next must be
    # clearly larger than the pitch inside a bin, and the dots (5 pt) must not touch inside a bin
    gap_between = pt_per_bin - 2.0 * FIG02_PITCH
    if FIG02_PITCH < 5.0 + 0.4 or gap_between < 1.25 * FIG02_PITCH:
        raise ValueError(f"FIG-02: dots {FIG02_PITCH} pt apart inside a bin and {gap_between:.1f} pt apart between bins: widen the bins "
                         f"(narrow the too-few column) or the pitch, so that the gap between bins is at least 1.25 times the pitch")
    if abs(xlim[1] - (len(S.keys("main", f"{i20}.1x6.bins")) - 0.5 + FIG02_FEW_COL)) > 1e-9:
        raise ValueError("FIG-02: the x range does not end at the too-few column's right edge")
    points: List[Dict[str, Any]] = []
    sample: Dict[Tuple[int, str], Tuple[Cell, V]] = {}
    exact_cells: List[float] = []           # cells whose bootstrap interval has no width (all at 0% or 100%; checked): fa4's exact bar
    kc_vote = None
    n_cells: List[Cell] = []                # the number of puzzles in every cell (the fewest and the most are named in a caption fact)
    printed_values: List[Tuple[str, Cell, str, Cell]] = []  # (shape, the bin's range, the third as the key names it, value) of the cells strictly between 0 and 100 (read from the axis; their values are in the alt text and the caption facts)
    few_n: Dict[str, Cell] = {}                             # the number of puzzles with too few wrong samples, per shape
    few_bin: Dict[str, Cell] = {}                           # the range of the bin those puzzles fall in, per shape
    width_cell: Optional[Cell] = None       # the bins' common width in points (from the stamped bin keys)
    for shape, ax in axes.items():
        name = SHAPE_WORD[shape]
        bins = S.keys("main", f"{i20}.{shape}.bins")
        if len(bins) != 10:
            raise ValueError(f"FIG-02: {shape} has {len(bins)} bins, not 10: the axis, the bands and the bin labels are laid out for 10")
        edges = [kval(S, "main", join_key(*i20.split("."), shape, "bins", b, "bin_lower_edge")) for b in bins]
        # a bin's upper edge is stamped only in the name of its key ('[10,20)', '[90,100]'): read it from there, and check it against the
        # next bin's lower edge and the common width
        uppers: List[Cell] = []
        for i, b in enumerate(bins):
            m = re.fullmatch(r"\[(\d+),(\d+)[)\]]", b)
            if not m or int(m.group(1)) != int(edges[i][1]):
                raise ValueError(f"FIG-02: bin key {b!r} does not match its lower edge {edges[i][1]}: reword the bin labels")
            up = int(m.group(2))
            if i + 1 < len(bins) and up != int(edges[i + 1][1]):
                raise ValueError(f"FIG-02: bin {b!r} does not end where the next bin starts")
            if up - int(m.group(1)) != 10:
                raise ValueError(f"FIG-02: bin {b!r} is not 10 points wide: reword the axis title")
            uref = Ref(up, "main", join_key(*i20.split("."), shape, "bins", b))
            uppers.append(Cell(str(up), raw=up, refs=(uref,), formula="the upper edge in the bin's key name"))
            if width_cell is None:
                lref = S.ref("main", join_key(*i20.split("."), shape, "bins", b, "bin_lower_edge"))
                width_cell = num_d(derive("upper edge in the bin's key name - bin_lower_edge", lambda hi, lo: hi - lo, uref, lref), dp=0)
        rng = [joined(edges[i][0], L("–"), uppers[i], sep="") for i in range(len(bins))]       # each bin as a range ("10–20")
        few_at: List[int] = []
        for i, b in enumerate(bins):
            base = join_key(*i20.split("."), shape, "bins", b)
            thirds = S.keys("main", base + ".thirds")
            few = S.get("main", base + ".too few wrong tries")
            key_text = {t: kt for t, _, kt, _, _ in FIG02_THIRDS}          # the third as the key names it ("lowest third")
            slots = [(t, sname, step, slot) for t, sname, _, step, slot in FIG02_THIRDS if t in thirds]
            if few:
                slots.append(("few", FIG02_FEW_NAME, "grey", 0.0))
            for t, bname, step, slot in slots:
                x = (i + slot * pitch) if t != "few" else (len(bins) - 0.5 + FIG02_FEW_COL / 2.0)       # the grey dot: the middle of its own column
                tb = base + (f".thirds.{t}" if t != "few" else ".too few wrong tries")
                vb, kc_vote = _at_last_k(S, tb + ".mean_vote_at_k")
                y = pv(S, "main", vb + ".mean")
                lo, hi = ci(S, "main", vb + ".ci95")
                n_c, _ = kval(S, "main", tb + ".n")
                n_cells.append(n_c)
                ex, note = None, None
                if collapsed(lo, hi):
                    # a cell whose vote is right on all or none of its puzzles (checked: the caption says so): its bootstrap interval
                    # has no width, and the bar is free analysis 4's exact interval for the same cell (revision 3 stamps one for every
                    # collapsed item 20 cell at k = 40; one missing refuses the build)
                    if y.val not in (0.0, 100.0):
                        raise ValueError(f"FIG-02: {vb} collapsed at {y.val}, not at 0% or 100%: reword the caption")
                    ex = fa4_bar(S, "main", vb, y, lo, hi)
                    if ex.n.raw != n_c.raw:
                        raise ValueError(f"FIG-02: fa4's exact interval for {vb} is over {ex.n.raw} puzzles, the cell has {n_c.raw}")
                    note = FIG02_EXACT_NOTE
                    exact_cells.append(y.val)
                elif y.val in (0.0, 100.0):
                    raise ValueError(f"FIG-02: {vb} is at {y.val} with a bootstrap interval of width: reword the caption (cells at 0 and 100)")
                bar_lo, bar_hi = (ex.lo.val, ex.hi.val) if ex else (lo.val, hi.val)
                _fig02_dot(ax, x, y.val, bar_lo, bar_hi, c_h, step)
                if 0.0 < y.val < 100.0:
                    printed_values.append((shape, rng[i], key_text[t], y.cell))
                ax.annotate(n_c.printed, xy=(x, 0), xycoords="data", xytext=(0, -FIG02_COUNT_PT), textcoords="offset points",
                            ha="center", va="center", fontsize=LAB, color=INK_2, zorder=4, annotation_clip=False)
                points.append(rec(f"Haiku-medium vote, {name}, {bname}", name, x=edges[i][0], x_upper=uppers[i], y=y, lo=lo, hi=hi, n=n_c,
                                  k=kc_vote, note=note, **exact_rec(ex)))
                if t == "few":
                    few_at.append(i)
                    few_n[shape], few_bin[shape] = n_c, rng[i]
                if shape == "1x6" and i in (1, 3, 4) and t in ("t1", "t2", "t3"):
                    sample[(i, t)] = (rng[i], y)
        if any(i != len(bins) - 1 for i in few_at):
            raise ValueError("FIG-02: puzzles with too few wrong samples are not in the last bin only: reword the caption, the alt text and the key")
        if not few_at:
            raise ValueError(f"FIG-02: no puzzles with too few wrong samples in {shape}: the grey column and its label have nothing to name")
        # light grey bands behind alternate bins (the even ones), through the counts row; the column of too few wrong samples follows bin 9
        # and is a band of its own (0.7 of a bin wide)
        bottom_pt = FIG02_COUNT_PT + 5.0
        for i in range(0, len(bins), 2):
            _fig02_band(ax, i - 0.5, i + 0.5, bottom_pt)
        _fig02_band(ax, len(bins) - 0.5, len(bins) - 0.5 + FIG02_FEW_COL, bottom_pt)
        # the direct label of the grey dot: above the panel and left of the dot, with a short diagonal leader from the label's lower
        # right end to the dot
        ax.annotate(FIG02_FEW_NAME, xy=(len(bins) - 0.5 + FIG02_FEW_COL / 2.0, 100.0), xytext=(-FIG02_FEW_DX, 9.0), textcoords="offset points",
                    ha="right", va="bottom", fontsize=LAB, color=INK, annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=style.REFERENCE, linewidth=0.6, relpos=(1.0, 0.0), shrinkA=1.5, shrinkB=3.6,
                                    patchA=None))
        # the bins' labels as ranges ("0-10"), on two staggered rows (a range is wider than its bin)
        for i, b in enumerate(bins):
            ax.annotate(rng[i].printed, xy=(i, 0), xycoords="data",
                        xytext=(0, -FIG02_LABEL_PT[i % 2]), textcoords="offset points", ha="center", va="center", fontsize=LAB, color=INK_2,
                        annotation_clip=False)
        ax.set_xticks([])
        ax.set_xlim(*xlim)
        acc_axis(ax, 0.0, 100.0)
        tidy(ax)
        ax.grid(axis="x", visible=False)
        ax.spines["bottom"].set_position(("outward", FIG02_SPINE_PT))
        _fig02_tag(ax, {"1x6": "A", "6x1": "B"}[shape], {"1x6": "Chains", "6x1": "Pieces"}[shape])
    if not printed_values:
        raise ValueError("FIG-02: no cell lies strictly between 0 and 100: the printed values have nothing to mark")
    ax_a.set_ylabel(ACC_LABEL)
    ax_b.tick_params(labelleft=False)
    # the fixed row's name, at the left of panel A's row (the dots' own counts are the numbers)
    ax_a.annotate("puzzles", xy=(0.0, 0.0), xycoords=("axes fraction", "data"), xytext=(-6, -FIG02_COUNT_PT), textcoords="offset points",
                  ha="right", va="center", fontsize=LAB, color=INK_2)
    assert width_cell is not None
    fig.text((left + (2 * w_ab + gap) / 2) / W, (y_ab - 0.66) / H,
             "Haiku-medium single-sample accuracy (%), in bins of " + width_cell.printed + " points",
             ha="center", va="center", fontsize=LAB, color=INK)

    # panel C: how often two wrong samples repeat each other (horizontal bars from 0: the measure's name inside the bar in white,
    # the value outside the bar's end in dark text)
    groups = (("1x6", "chains"), ("6x1", "pieces"), ("both_shapes", "both"))
    measures = (("haiku_repeat_share", "same wrong answer", 0.2), ("reporting.group_b.item_13", "same first slip", -0.2))
    sh_refs: Dict[Tuple[str, str], V] = {}
    pair_cells: Dict[Tuple[str, str], Cell] = {}
    for g, (gk, gname) in enumerate(groups):
        for mk, mname, dy in measures:
            y = pv(S, "main", f"{mk}.{gk}.share")
            sh_refs[(gk, mk)] = y
            yy = 2 - g + dy
            ax_c.barh([yy], [y.val], height=0.36, color=c_h, edgecolor=c_h, linewidth=0, zorder=2)
            ax_c.annotate(mname, xy=(0, yy), xytext=(4, 0), textcoords="offset points", ha="left", va="center", fontsize=LAB,
                          color="white", zorder=3)
            ax_c.annotate(y.cell.printed + "%", xy=(y.val, yy), xytext=(3, 0), textcoords="offset points", ha="left", va="center",
                          fontsize=LAB, color=INK)
            pairs = integer(S.ref("main", f"{mk}.{gk}.pairs"))
            pair_cells[(gk, mk)] = pairs
            over = "wrong and placeable" if mk.endswith("item_13") else "wrong"
            points.append(rec(f"share of Haiku-medium wrong-sample pairs that repeat, {mname}, {gname}", "repeat shares", x=None, y=y,
                              pairs=pairs, note=f"over pairs of Haiku-medium samples that are both {over}"))
    ax_c.set_yticks([2, 1, 0])
    ax_c.set_yticklabels([g for _, g in groups])
    ax_c.set_ylim(-0.6, 2.6)
    ax_c.set_xlim(0, 100)
    ax_c.set_xticks([0, 20, 40, 60, 80, 100])
    ax_c.grid(axis="y", visible=False)
    tidy(ax_c, xlabel="Share of pairs (%)")
    _fig02_tag(ax_c, "C", "Repeat shares")

    # the key above the panels: what the vote is, then one row (the thirds' order, then the three swatches, which are the plotted dots)
    y_key1, y_key2 = 1 - 0.11 / H, 1 - 0.29 / H
    fig.text(left / W, y_key1, "Haiku-medium vote of " + kc_vote.printed + " samples, by agreement among wrong samples", ha="left",
             va="center", fontsize=LAB, color=INK)
    lead = fig.text(left / W, y_key2, "Left to right in each bin:", ha="left", va="center", fontsize=LAB, color=INK)
    lead_in = lead.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi
    handles = [_Fig02Key(c_h, step) for _, _, _, step, _ in FIG02_THIRDS]
    fig.legend(handles=handles, labels=[kt for _, _, kt, _, _ in FIG02_THIRDS], handler_map={_Fig02Key: _Fig02KeyHandler()}, loc="center left",
               ncol=3, bbox_to_anchor=((left + lead_in + 0.10) / W, y_key2), frameon=False, handlelength=0.8, handletextpad=0.4,
               columnspacing=1.6, borderaxespad=0.0, borderpad=0.0)

    min_wrong = _fig02_min_wrong(S)
    lo_n, hi_n = min(n_cells, key=lambda c: c.raw), max(n_cells, key=lambda c: c.raw)

    def values_in(shape_key: str) -> List[Cell]:
        """The printed values of one shape, each attached to its bin: 'in the 10–20 bin the lowest third 83.3%, and in the 40–50 bin the
        middle third 66.7% and the highest third 16.7%' (bins in axis order, thirds left to right)."""
        by_bin: Dict[str, Tuple[Cell, List[List[Cell]]]] = {}
        for sh_, r_, nm, c in printed_values:
            if sh_ == shape_key:
                by_bin.setdefault(r_.printed, (r_, []))[1].append([L("the " + nm), P(c)])
        out: List[Cell] = []
        for j, (r_, items) in enumerate(by_bin.values()):
            out += [L(", and in the") if j else L("in the"), r_, L("bin")] + _fig07_and(items)
        return out

    vals_chains, vals_pieces = values_in("1x6"), values_in("6x1")
    few_last = few_bin["1x6"]
    if few_bin["6x1"].printed != few_last.printed:
        raise ValueError("FIG-02: the puzzles with too few wrong samples are not in the same bin on both shapes: reword the alt text and the facts")
    alt = [L("Three panels. Panels A (chains) and B (pieces) are dot plots of the whole-answer accuracy of the Haiku-medium vote of"), kc_vote,
           L("samples. Puzzles are grouped by their single-sample accuracy bin (bins of"), width_cell,
           L("points, each labelled by its range on the x axis, in two staggered rows) and, within each bin, by thirds of how often their wrong samples agree with each"
             " other: up to three dots per bin, from left to right the lowest, middle and highest third (three shades of Haiku’s blue,"
             " darkest for the lowest third), each with a 95% bar. No line joins the dots: each cell holds"), lo_n, L("to"), hi_n,
           L("puzzles, so the dots show where a cell sits, not a trend. One more dot, in grey and labelled “too few wrong samples”, in a"
             " column of its own right of the"), few_last, L("bin (whose puzzles they are), stands for the puzzles with fewer than"), min_wrong,
           L("wrong samples, too few to split into thirds:"), few_n["1x6"], L("chains and"), few_n["6x1"],
           L("pieces. The number of puzzles in each cell prints in one row under the dots, in light grey bands that run behind every"
             " second bin and behind the grey dot’s column. No value is printed beside a dot; the cells that are neither at zero nor at the"
             " top of the axis are, in the chains panel:"), *vals_chains, L(". In the pieces panel:"), *vals_pieces, L("."),
           L("In the chains panel the lowest, middle and highest thirds reach"), P(sample[(1, "t1")][1].cell), L(","),
           P(sample[(1, "t2")][1].cell), L("and"), P(sample[(1, "t3")][1].cell), L("in the"), sample[(1, "t1")][0], L("bin,"),
           P(sample[(3, "t1")][1].cell), L(","), P(sample[(3, "t2")][1].cell), L("and"), P(sample[(3, "t3")][1].cell),
           L("in the"), sample[(3, "t1")][0], L("bin, and"), P(sample[(4, "t1")][1].cell), L(","),
           P(sample[(4, "t2")][1].cell), L("and"), P(sample[(4, "t3")][1].cell), L("in the"), sample[(4, "t1")][0], L("bin"),
           L("."),
           L("Panel C shows, as horizontal bars, that over both shapes a pair of wrong Haiku-medium samples gave the same wrong answer in"),
           P(sh_refs[("both_shapes", "haiku_repeat_share")].cell),
           L("of pairs and the same first slip in"), P(sh_refs[("both_shapes", "reporting.group_b.item_13")].cell),
           L("of the pairs whose first slips can both be placed; on chains alone the shares are"),
           P(sh_refs[("1x6", "haiku_repeat_share")].cell), L("and"), P(sh_refs[("1x6", "reporting.group_b.item_13")].cell),
           L(", on pieces alone"), P(sh_refs[("6x1", "haiku_repeat_share")].cell), L("and"), P(sh_refs[("6x1", "reporting.group_b.item_13")].cell),
           L(".")]
    if exact_cells:
        alt += [L("Where a cell’s vote is right on all or none of its puzzles (a dot at zero or at the top of the axis), its bootstrap interval has no width and its"
                  " bar shows the exact 95% interval over that cell’s puzzles from free analysis 4 (post hoc).")]
    caption = {"tier": [L("pre-specified descriptive; no test and no cause")] + ([L(
                   "; the exact intervals (the bars on cells at zero and at the top of the axis) are post hoc (free analysis 4)")] if exact_cells else []),
               "study": [L("Study 1, main run, 6 steps; all three panels are Haiku-medium’s samples: the whole-answer accuracy of its vote of"),
                         kc_vote, L("samples, split by the single-sample accuracy bins, and the pairs of wrong samples in panel C")],
               "set": [L("the Study 1 puzzle set at 6 steps: each puzzle as a chain and as pieces")],
               "thirds": [L("within each bin, puzzles are split into thirds by how often their wrong samples repeat each other: the dots run"
                            " left to right from the lowest third (darkest) through the middle third to the highest third (lightest); no"
                            " line joins the dots, because each cell holds"), lo_n, L("to"), hi_n,
                          L("puzzles, so the dots show where a cell sits, not a trend; the grey dot labelled “too few wrong samples”, in a"
                            " column of its own right of the"), few_last, L("bin (whose puzzles they are), stands for the puzzles with fewer than"),
                          min_wrong, L("wrong samples, too few to split into thirds (chains:"), few_n["1x6"], L("puzzles; pieces:"), few_n["6x1"],
                          L("puzzles); no value is printed beside a dot, so the cells that are neither at zero nor at the top of the axis are given here (chains:")] +
                         vals_chains + [L("; pieces:")] + vals_pieces + [L(")")],
               "n": [L("puzzles in each cell: the number under each dot, in light grey bands that run behind every second bin and behind the grey dot’s column; panel C, both shapes: the same-wrong-answer share is over"),
                     pair_cells[("both_shapes", "haiku_repeat_share")], L("pairs of wrong samples and the first-slip share over"),
                     pair_cells[("both_shapes", "reporting.group_b.item_13")],
                     L("pairs: the first-slip share counts only wrong samples whose first slip can be placed")],
               "interval": [L("panels A and B: 95% cluster bootstrap within each cell (the bar on its dot) where it has width")] + ([L(
                   "; a cell whose vote is right on all or on none of its puzzles has a bootstrap interval of no width, and its bar"
                   " is the exact (Clopper–Pearson) 95% interval over the cell’s puzzles from free analysis 4 (post hoc)")]
                   if exact_cells else []) + [L("; panel C: none (Study 1’s file stamps no interval for the repeat shares)")],
               "price": [L("not applicable (no cost on this figure)")]}
    return FigureOut(fig, points, tight(_fig02_curly(alt)), tight_caption({k: _fig02_curly(v) for k, v in caption.items()}))


# ================================================================ FIG-03


def usd_val(S: Store, source: str, key: str) -> V:
    r = S.ref(source, key)
    return V(r, usd(r), _need_num(r))


def s1b_sets_check(S: Store) -> None:
    """A structure check behind the plain-words set lines of FIG-03 and FIG-04 (set ids stay out of captions): Study 1b has one set per
    length (6, 12 and 16 steps, from `inputs.sets.*.n`), Tests B1 and B2 ran on the 16-step set and Test B3 on the 6-step set
    (`constants.test_sets`). Refuses the build otherwise."""
    by_n: Dict[int, List[str]] = {}
    for sid in S.keys("s1b", "inputs.sets"):
        by_n.setdefault(S.get("s1b", join_key("inputs", "sets", sid, "n")), []).append(sid)
    ts = S.get("s1b", "constants.test_sets")
    if (sorted(by_n) != [6, 12, 16] or any(len(v) != 1 for v in by_n.values()) or not ts["B1"] == ts["B2"] == by_n[16][0]
            or ts["B3"] != by_n[6][0]):
        raise ValueError("Study 1b's sets are not one per length with B1/B2 at 16 steps and B3 at 6 steps: reword the set lines")


# Redrawn for proof 4 (group F2, Edith's PR #34 review of FIG-03 and her round 2; nothing it shows changes in value or meaning): one row of
# three accuracy panels, A (16 steps) and the post hoc panels B (6 steps) and C (12 steps), 6.5 x 2.34 in. The pooled vote is the one line
# (the chains' and pieces' lines are gone: by shape, Test B2's vote is in TAB-11 and its difference from Opus-medium at each shape's own
# cost-matched size is in TAB-25); its band starts at k = 1 from the setting's stamped
# interval, as FIG-01's does, so the stray one-sample bar is gone; the cost panel is replaced by a second axis above panel A (Edith's
# preferred fix) that prints the shares of Opus-medium's price the text quotes; the k ticks are labelled at the sizes the text quotes; the
# comparator's dashed line is drawn over the vote line; and the cost-matched tick is FIG-01's (Opus-medium's colour, below the axis).
FA2_LENGTHS = (("N=6", "B", "6 steps"), ("N=12", "C", "12 steps"))
FIG03_XLIM = (0.85, 11.9)       # vote size k on a log-2 axis, with room at the right for a comparator's interval bar
FIG03_XBAR = 11.3               # where Opus-medium's interval bar sits: the panel's right edge (display only)
FIG03_K_MAJOR = (1, 2, 3, 5, 6, 10)     # the vote sizes the text quotes, each a labelled tick (Edith's PR #34 SHOULD: label the k the text quotes)
FIG03_K_ALL = tuple(range(1, 11))       # every vote size from 1 to 10 is plotted: the others are minor ticks
FIG03_SHARE_K = (1, 3, 5, 10)           # the vote sizes whose share of Opus-medium's price the second axis prints (6, Test B2's, is in its label)
SHARE_TITLE = "Share of Opus-medium’s price"

# layout, inches at print size (F14: one row 2.0-2.6 in): one row of three accuracy panels. Panel A is wider (its second axis prints four
# shares); panels B and C share its y axis, so their y tick labels and title are left out.
FIG03_H = 2.34
FIG03_M_L, FIG03_M_R, FIG03_M_B = 0.62, 0.10, 0.47
FIG03_AH = 1.28                                 # every panel's height: one y scale in all three
FIG03_W_A, FIG03_GAP = 2.10, 0.14
FIG03_W_P = (COLW - FIG03_M_L - FIG03_M_R - FIG03_W_A - 2 * FIG03_GAP) / 2.0     # panels B and C
FIG03_SHARE_RISE = 23.0                         # points: panel A's second axis (ticks, labels, title) stands between its axes and its letter
FIG03_A_LABEL_AT = (6.0, 94.3)                  # where Test B2's label stands in panel A (display: data units, centred under its marker)
FIG03_TICK_PAD = 4.5                            # points between the k axis and its labels: clear of the 7 pt cost-matched tick (as FIG-01's)


def _fig03_kaxis(ax) -> None:
    """The vote-size axis (Karen's F10): log base 2; a labelled tick at each vote size the text quotes (1, 2, 3, 5, 6, 10) and an unlabelled
    minor tick at each other whole size (4, 7, 8, 9), so that every k from 1 to 10 is on the axis (Edith's PR #34 SHOULD)."""
    from matplotlib.ticker import FixedLocator, NullFormatter
    ax.set_xscale("log", base=2)
    ax.set_xlim(*FIG03_XLIM)
    ax.set_xticks(list(FIG03_K_MAJOR))
    ax.set_xticklabels([str(k) for k in FIG03_K_MAJOR])
    ax.xaxis.set_minor_locator(FixedLocator([k for k in FIG03_K_ALL if k not in FIG03_K_MAJOR]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="x", which="minor", length=1.5, width=0.5)
    ax.tick_params(axis="x", which="major", pad=FIG03_TICK_PAD)


def _fig03_tag(ax, letter: str, title: str, rise: float = 0.0) -> None:
    """The panel letter (the shared bold letter) and a title of at most four words beside it (Karen's F16); `rise` lifts both by that many
    points (panel A's letter stands above its second axis)."""
    ax.annotate(letter, xy=(0, 1), xycoords="axes fraction", xytext=(0, 2.8 + rise), textcoords="offset points", fontsize=9, color=INK,
                ha="left", va="bottom", **style.BOLD)
    ax.annotate(title, xy=(0, 1), xycoords="axes fraction", xytext=(12, 2.8 + rise), textcoords="offset points", fontsize=LAB, color=INK,
                ha="left", va="bottom")


def _fig03_share_axis(ax, labels: Dict[float, str]) -> None:
    """Panel A's second horizontal axis (Edith's preferred fix for the cost shares): the vote's list cost per answer as a share of one
    Opus-medium answer's price, one tick at every vote size and a printed share at the vote sizes in `labels` (k -> the share's printed
    value, read from the cells). The cost of a vote is k samples' at one sample's price, so this is the k axis read in price. Drawn by hand
    (an axes line, ticks, labels and a title above the panel), so that every text is a checked text of the figure."""
    h_pt = ax.get_position().height * ax.figure.get_figheight() * 72.0
    tr = ax.get_xaxis_transform()               # x in data units, y as a fraction of the axes' height
    tick, pad, lab_h = 3.0, 2.0, 6.5
    x0, x1 = ax.get_xlim()
    ax.plot([x0, x1], [1.0, 1.0], transform=tr, color=style.REFERENCE, linewidth=0.6, solid_capstyle="butt", clip_on=False, zorder=3)
    for kf in FIG03_K_ALL:
        big = kf in labels
        ax.plot([kf, kf], [1.0, 1.0 + (tick if big else 1.5) / h_pt], transform=tr, color=style.REFERENCE, linewidth=0.6 if big else 0.5,
                solid_capstyle="butt", clip_on=False, zorder=3)
    for kf, text in labels.items():
        ax.text(kf, 1.0 + (tick + pad) / h_pt, text, transform=tr, fontsize=LAB, color=INK_2, ha="center", va="bottom")
    ax.text(0.5, 1.0 + (tick + pad + lab_h + 2.0) / h_pt, SHARE_TITLE, transform=ax.transAxes, fontsize=LAB, color=INK, ha="center", va="bottom")


def _fig03_cm_label(ax, kf: float, kcell: Cell, capped: bool, col: str) -> None:
    """The label of the cost-matched tick (right-aligned, just left of the tick), in the text colour of the comparator the tick is matched to
    (FIG-01's style: Opus-medium's). Panels B and C only: in panel A the cost-matched size is Test B2's, named once by the label of its
    larger marker."""
    ax.text(kf * 0.94, 0.07, f"cost-matched $k={kcell.printed}$" + (" (capped)" if capped else ""), transform=ax.get_xaxis_transform(),
            fontsize=LAB, color=col, ha="right", va="bottom")


def _fig03_cm_tick(ax, kf: float, col: str) -> None:
    """The cost-matched vote size, drawn as FIG-01 draws it (Edith's PR #34 LOW: one style in both figures): a tick in the comparator's colour
    below the horizontal axis, 7 pt long."""
    ax.plot([kf], [0.0], linestyle="none", marker=3, markersize=7, markeredgewidth=1.3, color=col, transform=ax.get_xaxis_transform(),
            clip_on=False, zorder=6)


def _fig03_b2_marker(ax, x: float, y: float, c_hx: str) -> None:
    """Test B2's vote size: the one enlarged marker of the figure, with a white edge."""
    ax.plot([x], [y], linestyle="none", marker="o", markersize=5.5, markerfacecolor=c_hx, markeredgecolor="white", markeredgewidth=0.8,
            zorder=7, clip_on=False)


def _fig03_draw_acc(ax, d: Dict[str, Any], c_hx: str, c_o: str, ylo: float) -> None:
    """One accuracy panel of FIG-03: the Haiku-max vote pooled over shapes as the one thick line, with its 95% band from the first vote
    size (as FIG-01 draws its band: at one sample the band's ends are the setting's own stamped interval, from the second vote size on the
    curve's own bootstrap band), Opus-medium's one-answer level as a dashed line drawn OVER the vote line (so that a tie shows, Edith's LOW:
    panel B's vote ends on the dashed line) with its 95% interval as one bar at the right edge, and the cost-matched vote size as a tick
    below the axis. The axis limits are set before any mark is drawn (the bar rule reads them)."""
    ks = d["ks"]
    _fig03_kaxis(ax)
    acc_axis(ax, ylo, 100.0)
    _, lo1, hi1 = d["one"]
    ax.fill_between(ks, [lo1] + list(d["plo"]), [hi1] + list(d["phi"]), color=c_hx, alpha=0.18, linewidth=0, zorder=1)
    ax.plot(ks, d["pm"], color=c_hx, linewidth=1.5, zorder=3, clip_on=False)
    ax.axhline(d["om"][0], color=c_o, linewidth=1.0, linestyle=(0, (4, 2)), zorder=4)
    mark(ax, FIG03_XBAR, d["om"][0], d["om"][1], d["om"][2], "opus", "medium", zorder=5)
    _fig03_cm_tick(ax, d["cm"][0], c_o)
    tidy(ax)


def _fig03_posthoc(S: Store, N: str, tag: str, steps: str, points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One post hoc panel's values from free analysis 2 (D-131): the Haiku-max vote curve at k = 1..10, pooled with its stamped 95% band
    from the second vote size on (drawn only where the band has width); one sample (k = 1) carries Study 1b's stamped setting interval (the
    same value as the curve's k = 1, checked; one value, one interval: FIG-04 and FIG-05 draw that interval too), which is where the band
    starts; Opus-medium's one-answer level and interval from Study 1b's stamped setting; the cost-matched k from fa2, with its raw
    (before the hold to the samples drawn) size checked. The per-shape curves are not drawn (by shape, Test B2's vote is in TAB-11 and the difference from Opus-medium at each
    shape's own cost-matched size is in TAB-25).
    Returns what the panel draws and the cells its alt text and caption facts use."""
    import math
    cb = join_key("result", N, "curve")
    npts = len(S.get("fa2", cb))
    n_int = int(N.split("=")[1])
    ks, pm, plo, phi = [], [], [], []
    kcells = []
    lows: List[V] = []                  # every plotted accuracy value and interval end (the axis start is read from the lowest)
    for i in range(npts):
        base = join_key("result", N, "curve", i)
        kc, kf = kval(S, "fa2", base + ".k")
        y = pv(S, "fa2", base + ".pooled.mean", prop=False)
        ks.append(kf); pm.append(y.val); kcells.append(kc); lows.append(y)
        if i == 0:                      # one sample: its interval is the setting's (below), not fa2's own bootstrap of the same value
            if kf != 1.0:
                raise ValueError(f"fa2 {N}: the curve does not start at one sample")
            points.append(rec(f"Haiku-max vote, pooled over shapes, {steps} (post hoc)", f"{tag} {steps}", x=kc, y=y,
                              note="one sample: its 95% band starts from Study 1b's stamped setting interval (the next record); free analysis 2's own"
                                   " interval for this value is not drawn (one value, one interval)"))
        else:
            lo, hi = ci(S, "fa2", base + ".pooled.ci95", prop=False)
            # the pinned file is revision 2, whose pooled bands have width; a pooled interval of no width would pinch the band to nothing
            has_width(f"FIG-03: free analysis 2's pooled band at {steps}, k = {kc.printed}", lo, hi)
            plo.append(lo.val); phi.append(hi.val); lows.append(lo)
            points.append(rec(f"Haiku-max vote, pooled over shapes, {steps} (post hoc)", f"{tag} {steps}", x=kc, y=y, lo=lo, hi=hi))
    # one sample's 95% interval: Study 1b's stamped setting (the curve's k = 1 is the same single sample); the band starts from it
    arm = join_key("descriptive", "arms", f"hx@{n_int}", "pooled")
    sy = pv(S, "s1b", arm + ".mean", prop=False)
    slo, shi = ci(S, "s1b", arm + ".ci95", prop=False)
    has_width(f"FIG-03: Study 1b's one Haiku-max sample at {steps}", slo, shi)
    lows.append(slo)
    s_int = method(S, "s1b", arm + ".interval")
    if abs(sy.val - pm[0]) > 1e-6:
        raise ValueError(f"fa2 {N}: the curve's one sample is not Study 1b's stamped single sample")
    points.append(rec(f"one Haiku-max sample, pooled, {steps}: Study 1b's stamped setting (the 95% band starts from this interval at the first vote size)",
                      f"{tag} {steps}", x=kcells[0], y=sy, lo=slo, hi=shi, interval=s_int.printed))
    # Opus-medium, one answer: Study 1b's stamped setting
    om = join_key("descriptive", "arms", f"om@{n_int}", "pooled")
    oy = pv(S, "s1b", om + ".mean", prop=False)
    olo, ohi = ci(S, "s1b", om + ".ci95", prop=False)
    has_width(f"FIG-03: Opus-medium's interval at {steps}", olo, ohi)
    lows.append(olo)
    o_int = method(S, "s1b", om + ".interval")
    o_tries = integer(S.ref("s1b", join_key("descriptive", "arms", f"om@{n_int}", "tries_per_item")))
    points.append(rec(f"Opus-medium, one answer, pooled, {steps}", f"{tag} {steps}", x=None, y=oy, lo=olo, hi=ohi, interval=o_int.printed,
                      note="dashed line, drawn over the vote line: the level; the bar at the right edge: Study 1b's stamped 95% interval"))
    # the cost-matched k (fa2): floor(Opus-medium's pooled cost per answer / Haiku-max's), held to the samples drawn. The raw size (before
    # the hold) is checked: the label says "(capped)" where the hold lowered it (Edith's LOW: check fa2's raw k at 6 steps)
    em = join_key("result", N, "equal_money")
    ek, ekf = kval(S, "fa2", em + ".k")
    ey = pv(S, "fa2", em + ".vote_mean_pooled", prop=False)
    ratio_ref, held_ref = S.ref("fa2", em + ".om_over_hx_cost_ratio"), S.ref("fa2", em + ".held_to_tries")
    raw_k = num_d(derive("floor of Opus-medium's list cost per answer over one Haiku-max sample's (free analysis 2), before the hold to the"
                         " samples drawn", lambda r: float(math.floor(r)), ratio_ref), dp=0)
    held = integer(held_ref)
    if abs(ekf - min(raw_k.raw, float(held.raw))) > 1e-9:
        raise ValueError(f"fa2 {N}: the cost-matched k is not the raw size held to the samples drawn")
    capped = raw_k.raw > float(held.raw)
    points.append(rec(f"Haiku-max vote at the cost-matched k, pooled, {steps} (post hoc)", f"{tag} {steps}", x=ek, y=ey, raw_k=raw_k, held_to=held,
                      note="tick below the horizontal axis: the largest vote size whose list cost per answer is at most one Opus-medium answer's,"
                           " held to the samples drawn (free analysis 2)" + ("; the hold lowered it (capped)" if capped else "; the hold did not lower it")))
    return {"ks": ks, "pm": pm, "plo": plo, "phi": phi, "one": (sy.val, slo.val, shi.val), "om": (oy.val, olo.val, ohi.val),
            "cm": (ekf, ek, ey.val), "lows": lows, "k_first": kcells[0], "k_second": kcells[1], "k_last": kcells[-1],
            "first": points_cell(S, "fa2", join_key("result", N, "curve", 0, "pooled", "mean")),
            "last": points_cell(S, "fa2", join_key("result", N, "curve", npts - 1, "pooled", "mean")), "ek": ek, "ey": ey, "oy": oy,
            "o_ci": ci_words(olo.cell, ohi.cell, paren=True), "o_int": o_int, "o_tries": o_tries, "s_int": s_int, "raw_k": raw_k, "held": held,
            "capped": capped, "n_base": integer(S.ref("fa2", join_key("result", N, "curve", 0, "pooled", "n_base")))}


def _fig03_axis_start(lows: List[V]) -> Cell:
    """The accuracy panels' common lower end, as a derived value (no typed number in the axis title): the lowest plotted value or
    interval end, less two points (room for the axis break above the start, Karen's F10), rounded down to an even number."""
    import math
    lowest = min(lows, key=lambda v: v.val)
    return num_d(derive("floor((x - 2) / 2) * 2: the lowest plotted value or interval end, less 2, rounded down to an even number",
                        lambda x: float(math.floor((x - 2.0) / 2.0) * 2), lowest.ref), dp=0)


def points_cell(S: Store, source: str, key: str) -> Cell:
    """An accuracy already in points, printed to one decimal (for alt text), guarded at 0 and 100."""
    return pct(S.ref(source, key), from_proportion=False)


@output("FIG-03")
@main_text
@plain_ids(main=True)
def fig_03(S: Store) -> FigureOut:
    s1b_sets_check(S)
    vb = "descriptive.vote_curve_n16"
    npts = len(S.get("s1b", vb + ".points"))
    W, H = COLW, FIG03_H
    fig = plt.figure(figsize=(W, H))
    # one row of three accuracy panels (display layout, inches): A (16 steps, with the share axis above it), then the post hoc panels at 6 and
    # 12 steps; panels B and C read the y axis of A (one scale, so their y tick labels and title are left out, as FIG-01's second panel's are)

    def add(x0: float, w: float):
        return fig.add_axes([x0 / W, FIG03_M_B / H, w / W, FIG03_AH / H])
    ax_a = add(FIG03_M_L, FIG03_W_A)
    ax_ph = {}
    for i, (N, _, _) in enumerate(FA2_LENGTHS):
        ax_ph[N] = add(FIG03_M_L + FIG03_W_A + FIG03_GAP + i * (FIG03_W_P + FIG03_GAP), FIG03_W_P)
    c_hx, c_o = color("haiku", "max"), color("opus", "medium")
    t_o = style.MODEL_TEXT["opus"]
    points: List[Dict[str, Any]] = []
    lows: List[V] = []                  # every plotted accuracy value and interval end (the axis start is read from the lowest)
    ks, pm, plo, phi, kcs, shares = [], [], [], [], [], []
    b2_i = None
    # one sample (k = 1) carries the Haiku-max setting's own stamped interval, the one FIG-04 and FIG-05 draw for the same value (one
    # value, one interval); the vote curve's own k = 1 interval is a separate bootstrap of it and is not drawn. The band starts from it.
    hx1 = "descriptive.arms.hx@16.pooled"
    hx1_y = pv(S, "s1b", hx1 + ".mean", prop=False)
    hx1_lo, hx1_hi = ci(S, "s1b", hx1 + ".ci95", prop=False)
    has_width("FIG-03: Study 1b's one Haiku-max sample at 16 steps", hx1_lo, hx1_hi)
    lows.append(hx1_lo)
    hx1_int = method(S, "s1b", hx1 + ".interval")
    oc_ref = S.ref("s1b", vb + ".opus_medium_cost_per_answer.pooled.list_usd")
    for i in range(npts):
        base = join_key(*vb.split("."), "points", i)
        kc, kf = kval(S, "s1b", base + ".k")
        y = pv(S, "s1b", base + ".pooled.mean", prop=False)
        cv = usd_val(S, "s1b", base + ".pooled.cost_per_answer")
        # the vote's list cost per answer over one Opus-medium answer's (the share the second axis prints: a price share at a vote size, so
        # a cost ratio at 2 decimals; only a cost-matched design's own spend share, Test B2's label, keeps 3: Edith, M1-12)
        share = num_d(derive("the vote's list cost per answer over one Opus-medium answer's, pooled over shapes", lambda a, b: a / b,
                             S.ref("s1b", base + ".pooled.cost_per_answer"), oc_ref), dp=2)
        ks.append(kf); pm.append(y.val); kcs.append(kc); shares.append(share); lows.append(y)
        if i == 0:
            if kf != 1.0 or abs(y.val - hx1_y.val) > 1e-6:
                raise ValueError("FIG-03: the vote curve's first point is not Study 1b's single Haiku-max sample")
            lo, hi = hx1_lo, hx1_hi
            points.append(rec("one Haiku-max sample, pooled over shapes (accuracy): Study 1b's stamped setting", "A accuracy", x=kc, y=hx1_y,
                              lo=lo, hi=hi, interval=hx1_int.printed,
                              note="one sample: the 95% band starts from the setting's stamped interval; from the second vote size on it is the curve's own"))
        else:
            lo, hi = ci(S, "s1b", base + ".pooled.ci95", prop=False)
            has_width(f"FIG-03: the pooled band at 16 steps, k = {kc.printed}", lo, hi)
            plo.append(lo.val); phi.append(hi.val); lows.append(lo)
            points.append(rec("Haiku-max vote, pooled over shapes (accuracy)", "A accuracy", x=kc, y=y, lo=lo, hi=hi))
        points.append(rec("Haiku-max vote, pooled over shapes (cost per answer, and its share of one Opus-medium answer's)", "A second axis", x=kc, y=cv,
                          share=share))
        if S.get("s1b", base + ".equal_money_k"):
            b2_i, b2_k, b2_y, b2_lo, b2_hi, b2_c = i, kc, y, lo, hi, cv
            b2_kf = kf
    # Opus-medium: one answer's accuracy interval and cost per answer (pooled over shapes)
    om = "descriptive.arms.om@16.pooled"
    oy = pv(S, "s1b", om + ".mean", prop=False)
    olo, ohi = ci(S, "s1b", om + ".ci95", prop=False)
    has_width("FIG-03: Opus-medium's interval at 16 steps", olo, ohi)
    lows.append(olo)
    oc = usd_val(S, "s1b", vb + ".opus_medium_cost_per_answer.pooled.list_usd")
    o16_int = method(S, "s1b", om + ".interval")
    o16_tries = integer(S.ref("s1b", "descriptive.arms.om@16.tries_per_item"))
    points.append(rec("Opus-medium, one answer, pooled (accuracy)", "A accuracy", x=None, y=oy, lo=olo, hi=ohi, interval=o16_int.printed,
                      note="dashed line, drawn over the vote line: the level; the bar at the right edge: Study 1b's stamped 95% interval"))
    points.append(rec("Opus-medium, one answer, pooled (cost per answer)", "A second axis", x=None, y=oc))
    ratio = num(S.ref("s1b", "costs_beside_tests.B2.ratio_challenger_over_comparator"), dp=3)
    if abs(shares[b2_i].raw - _need_num(S.ref("s1b", "costs_beside_tests.B2.ratio_challenger_over_comparator"))) > 1e-12:
        raise ValueError("FIG-03: Test B2's stamped list cost ratio is not the share the second axis reads at its vote size")
    points.append(rec("annotation in panel A: Test B2's list cost ratio, the Haiku-max vote over one Opus-medium answer", "A second axis", x=None,
                      ratio=ratio))

    # panels B and C (post hoc, free analysis 2): the same Haiku-max samples at 6 and 12 steps (read first: the axis start is common)
    ph = {N: _fig03_posthoc(S, N, tag, steps, points) for N, tag, steps in FA2_LENGTHS}
    for d in ph.values():
        lows += d["lows"]
    ystart = _fig03_axis_start(lows)
    ylo = float(ystart.raw)
    points.append(rec("the accuracy panels' lower end (display; read from the lowest plotted value)", "A accuracy", y=ystart))

    # panel A (accuracy at 16 steps): the vote's tested size is one marker, labelled once; the second axis above it prints the price shares
    dA = {"ks": ks, "pm": pm, "plo": plo, "phi": phi, "one": (hx1_y.val, hx1_lo.val, hx1_hi.val), "om": (oy.val, olo.val, ohi.val),
          "cm": (b2_kf, b2_k, b2_y.val)}
    _fig03_draw_acc(ax_a, dA, c_hx, c_o, ylo)
    _fig03_b2_marker(ax_a, b2_kf, b2_y.val, c_hx)
    ax_a.annotate(f"Test B2,\ncost-matched $k={b2_k.printed}$,\nspend share {ratio.printed}", xy=(b2_kf, b2_y.val),
                  xytext=FIG03_A_LABEL_AT, fontsize=LAB, color=INK, ha="center", va="top",
                  arrowprops=dict(arrowstyle="-", linewidth=0.6, color=style.REFERENCE, shrinkA=1, shrinkB=3))
    ax_a.set_ylabel(ACC_LABEL)                        # Karen's F10 (2026-10-20): the cut is drawn on the axis, its start said in the caption
    share_at = {kf: shares[i].printed for i, kf in enumerate(ks) if int(kf) in FIG03_SHARE_K}
    _fig03_share_axis(ax_a, share_at)
    _fig03_tag(ax_a, "A", "16 steps", rise=FIG03_SHARE_RISE)
    _fig0305_axis_break(ax_a, min(v.val for v in lows))       # the zoomed axis's cut, drawn (Karen's F10); its start is in the caption

    # panels B and C (post hoc, free analysis 2)
    for N, tag, steps in FA2_LENGTHS:
        ax = ax_ph[N]
        _fig03_draw_acc(ax, ph[N], c_hx, c_o, ylo)
        _fig03_cm_label(ax, ph[N]["cm"][0], ph[N]["ek"], ph[N]["capped"], t_o)
        ax.tick_params(axis="y", labelleft=False)
        _fig03_tag(ax, tag, steps + ", post hoc†")
        _fig0305_axis_break(ax, min(v.val for v in lows))
    # one horizontal-axis title for the row (the cost-matched tick in panel A is Test B2's own vote size, stamped as the cost-matched size at 16 steps)
    span_x = FIG03_M_L + (W - FIG03_M_L - FIG03_M_R) / 2
    fig.text(span_x / W, 0.02 / H, K_LABEL, ha="center", va="bottom", fontsize=LAB, color=INK)

    # one shared legend row above the panels (at most 4 entries; swatches are the plotted marks)
    from matplotlib.legend_handler import HandlerTuple
    handles = [(Patch(facecolor=c_hx, alpha=0.18, linewidth=0), Line2D([0], [0], color=c_hx, linewidth=1.5)),
               Line2D([0], [0], color=c_o, linewidth=1.0, linestyle=(0, (4, 2)), marker="D", markersize=5, markerfacecolor=c_o,
                      markeredgewidth=0.6)]
    leg_x = FIG03_M_L + FIG03_W_A + FIG03_GAP + (2 * FIG03_W_P + FIG03_GAP) / 2     # centred over panels B and C: the row beside panel A's letter
    fig.legend(handles=handles, labels=["Haiku-max vote, pooled", "Opus-medium, one answer"], loc="upper center",
               ncol=2, bbox_to_anchor=(leg_x / W, 1.0), handlelength=2.0, columnspacing=1.6, handletextpad=0.6, frameon=False,
               handler_map={tuple: HandlerTuple(ndivide=1, pad=0)})

    # Test B2's per-shape costs travel with it (style sheet): the vote and one Opus-medium answer, list price per answer, by shape, as
    # stamped beside the test; the pooled pair must be the one the second axis reads (one value, one key's number)
    b2c = "costs_beside_tests.B2"
    for side, drawn in (("challenger", b2_c), ("comparator", oc)):
        if abs(_need_num(S.ref("s1b", f"{b2c}.{side}.pooled.list_usd")) - drawn.val) > 1e-12:
            raise ValueError(f"FIG-03: Test B2's pooled {side} cost is not the one the second axis reads")
    for sh in ("1x16", "16x1"):
        if abs(_need_num(S.ref("s1b", f"{b2c}.challenger.{sh}.list_usd")) - _need_num(S.ref("s1b", f"{vb}.points.{b2_i}.{sh}.cost_per_answer"))) > 1e-12:
            raise ValueError(f"FIG-03: Test B2's {sh} vote cost is not the vote curve's at k = {b2_k.printed}")
    b2_shape_costs: List[Cell] = []
    b2_share: Dict[str, Cell] = {}              # the vote's list cost over one Opus-medium answer's, by shape (Edith's section 2.1: a spend share, 3 decimals)
    for j, sh in enumerate(("1x16", "16x1")):
        vr, cr = S.ref("s1b", f"{b2c}.challenger.{sh}.list_usd"), S.ref("s1b", f"{b2c}.comparator.{sh}.list_usd")
        b2_share[sh] = num_d(derive("the vote's list cost per answer over one Opus-medium answer's, on this shape", lambda a, b: a / b, vr, cr), dp=3)
        b2_shape_costs += [L(("; " if j else "") + "on " + SHAPE_WORD[sh]), usd(vr), L("against"), usd(cr),
                           joined(L("(spend share"), b2_share[sh], sep=" "), L(")")]
    more_less = {sh: ("more" if b2_share[sh].raw > 1.0 else "less") for sh in b2_share}
    first, last = S.ref("s1b", f"{vb}.points.0.pooled.mean"), S.ref("s1b", f"{vb}.points.{npts - 1}.pooled.mean")
    k_lo_c, k_hi_c = integer(S.ref("s1b", f"{vb}.points.0.k")), integer(S.ref("s1b", f"{vb}.points.{npts - 1}.k"))
    share_ks = [kcs[i] for i, kf in enumerate(ks) if int(kf) in FIG03_SHARE_K]
    share_cells = [shares[i] for i, kf in enumerate(ks) if int(kf) in FIG03_SHARE_K]

    def and_list(items: List[Cell]) -> List[Cell]:
        out: List[Cell] = []
        for j, c in enumerate(items):
            out += ([L("and")] if j and j == len(items) - 1 else [L(",")] if j else []) + [c]
        return out
    alt = [L("Three panels for Haiku-max votes, with the vote size k on the horizontal axis, a log scale from"), k_lo_c, L("to"), k_hi_c,
           L("samples: A at 16 steps; B at 6 steps and C at 12 steps, both post hoc."),
           L("In each panel the vote pooled over chains and pieces is a thick line with a 95% band, which starts at the first vote size from the"
             " setting's own stamped one-sample interval; one Opus-medium answer is a dashed line, drawn over the vote line where the two meet,"
             " with a diamond and its 95% interval as a bar at the right edge; a tick below the horizontal axis, in Opus-medium's colour, marks"
             " the cost-matched vote size, labelled in B and C. In panel A the vote size tested in Test B2, which is also the cost-matched size at"
             " 16 steps, is the one larger marker, with its label. A second horizontal axis above panel A gives the vote's list cost per answer as a"
             " share of one Opus-medium answer's price, at vote sizes"), *and_list(share_ks), L(":"), *and_list(share_cells),
           L("; Test B2's label gives its share,"), ratio, L(". The accuracy axes start at"),
           ystart, L(", not at zero."),
           L("Panel A: whole-answer accuracy, pooled over chains and pieces, rises from"), P(pct(first, from_proportion=False)),
           L("at one sample to"), P(pct(last, from_proportion=False)), L("at"),
           integer(S.ref("s1b", f"{vb}.points.{npts - 1}.k")), L("samples. At k ="), b2_k, L("(Test B2, confirmatory, the cost-matched size) it is"),
           P(b2_y.cell), L(","), *ci_words(b2_lo.cell, b2_hi.cell), L(", beside"), P(oy.cell), L("for one Opus-medium answer"),
           *ci_words(olo.cell, ohi.cell, paren=True), L("."),
           L("Cost, on the second axis of panel A: the list cost of the vote per answer is"), usd_val(S, "s1b", f"{vb}.points.0.pooled.cost_per_answer").cell,
           L("US dollars at one sample and"), b2_c.cell, L("at k ="), b2_k, L(", against"), oc.cell, L("for one Opus-medium answer, pooled over"
           " shapes: a spend share of"), ratio, L(". By shape, as stamped beside Test B2, the vote's list cost per answer against one"
           " Opus-medium answer's is, in US dollars,")] + b2_shape_costs + [L(".")]
    for N, tag, steps in FA2_LENGTHS:
        d = ph[N]
        alt += [L(f"Panel {tag}, post hoc, at {steps}: the pooled vote rises from"), P(d["first"]), L("at one sample to"), P(d["last"]), L("at"),
                d["k_last"], L("samples; the cost-matched vote size is k ="), d["ek"], L(", where the vote is at"), P(d["ey"].cell),
                L(", beside"), P(d["oy"].cell), L("for one Opus-medium answer"), *d["o_ci"], L(".")]
    alt += [L("The panels at different lengths use different puzzle sets; the gap to Opus-medium is not compared across lengths.")]
    c6, c12 = ph["N=6"], ph["N=12"]
    # the band methods are read, not typed (Q28): panel A's from Study 1b's driver, panels B and C's from free analysis 2's definition
    a_boot, a_pctl, a_draws = s1b_band_method(S)
    ph_interval = [L("panels B and C: 95%"), quoted_field(S, "fa2", "definition.analysis", "cluster bootstrap"),
                   L("bands from free analysis 2, from the second vote size on; at one sample the band starts from Study 1b's stamped"), c6["s_int"],
                   L("interval for one Haiku-max sample, at each length")]

    def samples_word(c: Cell) -> str:
        return "sample" if c.raw == 1 else "samples"
    # format compliance beside accuracy: the Haiku-max samples the votes are drawn from, and Opus-medium, at each length (Study 1b's report)
    fmt3: List[Cell] = [L("format compliance, the share of samples in the required answer format (Study 1b's format report; for a vote,"
                          " that of the Haiku-max samples it is drawn from), chains then pieces:")]
    any3 = False
    for j, n in enumerate((16, 6, 12)):
        items = [(words, [(*s1b_format(S, tag, sk), SHAPE_WORD[sk]) for sk in (f"1x{n}", f"{n}x1")])
                 for tag, words in (("hx", "Haiku-max"), ("om", "Opus-medium"))]
        cells, fl = fmt_list(items)
        any3 = any3 or fl
        fmt3 += [L(("; " if j else "") + f"at {n} steps")] + cells
    if any3:
        raise ValueError("FIG-03: a plotted setting is flagged by the format check: name it in the caption")
    fmt3 += flag_tail(any3)
    # where the hold to the samples drawn lowered a cost-matched size, the tick's label says "(capped)"; the fact names the raw sizes either way
    held_c = c6["held"]
    cap_words: List[Cell] = [L("rounded down (to k ="), c6["raw_k"], L("at 6 steps and"), c12["raw_k"], L("at 12 steps) and held to the"), held_c,
                             L("samples drawn")]
    if c6["capped"] or c12["capped"]:
        cap_words += [L("; a size the hold lowered is labelled capped")]
    else:
        cap_words += [L("; the hold lowers neither size, so neither is capped")]
    caption = {"tier": [L("pre-specified descriptive; only the vote size of Test B2 is a confirmatory test (the marked point in panel A); the other"
                          " vote sizes are descriptive; panels B and C are post hoc† descriptive (free analysis 2), with no test")],
               "study": [L("Study 1b, 16 steps, Haiku-max votes estimated from the designed samples per puzzle:"),
                         integer(S.ref("s1b", "constants.designed_tries.hx")),
                         L("; panels B and C: Study 1b's Haiku-max samples at 6 steps and 12 steps, vote sizes"), c6["k_first"], L("to"), c6["k_last"],
                         L("(free analysis 2)")],
               "set": [L("Study 1b's 16-step set, on which Tests B1 and B2 ran (fresh, never-sent puzzles); panels B and C: Study 1b's"
                         " 6-step set, on which Test B3 ran, and its 12-step set")],
               "n": [L("puzzles:"), integer(S.ref("s1b", f"{vb}.points.0.pooled.n_base")), L("at 16 steps;"), c6["n_base"], L("at 6 steps;"),
                     c12["n_base"], L("at 12 steps")],
               "interval": [L("panel A: a 95%"), a_boot, L("band for the pooled vote curve from the second vote size on, as Study 1b's"
                              " analysis code draws it:"), a_pctl, L("intervals over"), a_draws,
                            L("draws; at one sample the band starts from the Haiku-max setting's stamped"), hx1_int, L("interval, the one that the effort figure and the appendix version of"
                              " the length figure draw for the same sample (one value, one interval); Opus-medium's interval, drawn as one bar at the right edge of each accuracy panel, is Study 1b's stamped"), o16_int,
                            L("95% interval, over"), o16_tries, L(f"{samples_word(o16_tries)} per puzzle;")] + ph_interval +
                           [L("; Opus-medium's bars in B and C: Study 1b's stamped"), c6["o_int"], L("interval at 6 steps, over"), c6["o_tries"],
                            L(f"{samples_word(c6['o_tries'])} per puzzle, and"), c12["o_int"], L("interval at 12 steps, over"), c12["o_tries"],
                            L(f"{samples_word(c12['o_tries'])} per puzzle")],
               "price": price_study1b(S),
               "cost": [L("Test B2's list cost per answer in US dollars, as stamped beside the test, the vote at k ="), b2_k,
                        L("against one Opus-medium answer:")] + b2_shape_costs + [L("; pooled over shapes"), b2_c.cell, L("against"), oc.cell,
                        L(", the spend share of"), ratio, L("printed in Test B2's label; the second axis above panel A prints the same share, the vote's list cost per answer over"
                          " one Opus-medium answer's, at vote sizes")] + and_list(share_ks) + [L(":")] + and_list(share_cells),
               "format": fmt3,
               "marks": [L("in each accuracy panel the thick line is the vote pooled over chains and pieces, with its 95% band from the first vote size"
                           " (at one sample, the setting's stamped interval); the dashed line, with its diamond, is one Opus-medium answer's accuracy,"
                           " drawn over the vote line where the two meet; the one larger marker is the vote size of Test B2; the second axis above panel A"
                           " gives the vote's list cost per answer as a share of one Opus-medium answer's price (the vote costs k samples at one"
                           " sample's price); the tick below the horizontal axis, in Opus-medium's colour, marks the"
                           " cost-matched vote size, the largest whose list cost per answer, pooled over shapes, is at most one Opus-medium answer's"
                           " (in panel A it is Test B2's vote size, k ="),
                           b2_k, L(f", labelled on its larger marker; by shape that vote costs {more_less['1x16']} than one Opus-medium answer on"
                                   f" chains and {more_less['16x1']} on pieces, see cost; in B and C it is free analysis 2's, k ="), c6["ek"], L("at 6 steps and"),
                           c12["ek"], L("at 12 steps, labelled on the tick)")],
               "note": [L("the accuracy axes start at"), ystart, L(", not at zero, and none runs past the top of the scale; each length has its own puzzle set, so no trend in the gap between"
                          " the vote and Opus-medium is read across lengths; chains and pieces are not drawn separately (by shape, Test B2's vote is in TAB-11"
                          " and its difference from Opus-medium at each shape's own cost-matched size is in TAB-25); the cost-matched vote size in B and C is free analysis 2's: the list cost of"
                          " one Opus-medium answer over one Haiku-max sample's,")] + cap_words}
    return FigureOut(fig, points, tight(alt), tight_caption(caption))


# ================================================================ FIG-04

# Redrawn to the house style (Karen's page 3, recipe 1; Edith's §8): accuracy against cost per answer, each model's efforts joined in
# effort order with an effort label on every point, the setting's name once on its path, Opus-medium as a dashed reference line in its
# colour, no legend, no ring or dot. One study per figure: Study 1b only (its sweep at 6 and 16 steps); Study 1's 6-step points on other
# puzzles (hollow in the earlier figure) are in TAB-04 and, by shape, FIG-06.
# ONE ROW of two panels (Vision's and Edith's ruling, with Jarvis's zoom rule: no sentence relies on the enlargements, so both are
# dropped): A (6 steps, every model) with an accuracy axis that starts near its data (the start is in the axis title), B (16 steps, Haiku
# and Opus-medium) on its own range. Where markers still overlap in A their values are in TAB-12 and the caption facts say so (§8.5).


def _fig0305_axis_break(ax, lowest: float, centre_pt: float = 7.0) -> None:
    """The break mark of a zoomed accuracy axis (Edith's PR 34 review: the title stays 'Accuracy (%)' and the cut is drawn; Karen's F10,
    2026-10-20): the left spine is interrupted just above the horizontal axis by two short slanted strokes, in the spine's grey, with a
    white gap between them. No tick stands at or below the break (a label under it would read as a gap the axis does not have): the first
    tick is above it. The number the axis starts at is said once in the caption. The build stops unless the lowest plotted value or
    interval end (`lowest`, in the axis's units) clears the break's top, as the start rule can leave only one point below it."""
    fig = ax.figure
    pos = ax.get_position()
    w_pt, h_pt = pos.width * fig.get_figwidth() * 72.0, pos.height * fig.get_figheight() * 72.0
    gap, dx, dy = 1.6, 3.0, 1.8                       # points: the white gap, and each stroke's half-width and half-rise
    lo, hi = ax.get_ylim()
    top = lo + (centre_pt + gap + dy) * (hi - lo) / h_pt        # the break's top, in the axis's units
    if lowest <= top:
        raise ValueError(f"the zoomed axis's lowest mark ({lowest}) does not clear its break (top at {top:.2f}): lower the axis start")
    ax.set_yticks([t for t in ax.get_yticks() if top < t <= hi + 1e-9])     # F10: no tick at or below the break; the first stands above it
    yc = centre_pt / h_pt
    ax.plot([0.0, 0.0], [yc - gap / h_pt, yc + gap / h_pt], transform=ax.transAxes, color="white", linewidth=1.6, solid_capstyle="butt",
            clip_on=False, zorder=20)
    for sgn in (-1.0, 1.0):
        y = yc + sgn * gap / h_pt
        ax.plot([-dx / w_pt, dx / w_pt], [y - dy / h_pt, y + dy / h_pt], transform=ax.transAxes, color=style.REFERENCE, linewidth=0.6,
                solid_capstyle="butt", clip_on=False, zorder=21)


FIG04_H = 2.4                   # print height in inches (one row)
FIG04_X = {"N=6": (0.0002, 0.15), "N=16": (0.0006, 0.12)}     # each panel's cost range (layout only; the same inches per decade in both); B's starts under its first tick, so that "$0.001" does not stand at the panel's left edge, beside A's "$0.1"
FIG04_TICKS = (0.001, 0.003, 0.01, 0.03, 0.1)
FIG04_YLIM = (0.0, 100.0)       # both panels' accuracy range (layout only)
FIG04_ORDER = {e: i for i, e in enumerate(style.EFFORTS)}
# geometry in inches: left margin (the one accuracy title and the tick labels), the gap between the panels (B has no tick labels of its
# own), the right margin, the bottom margin (tick labels and the cost title) and the top margin (the panel letters and the labels over
# A's top row); the two panels share the rest in proportion to their cost ranges, so that both draw the same inches per decade of cost
FIG04_GEOM = {"left": 0.52, "gap": 0.20, "right": 0.12, "bottom": 0.42, "top": 0.27}
# a marker's half-height in points: a 5 pt marker plus half its 0.6 pt edge (a diamond's point reaches 1.41 times further); layout only
_FIG0406_MARK_HALF_PT = {"haiku": 2.8, "sonnet": 2.8, "opus": 3.84}


def _fig0406_bar_short(ax, model: str, y: float, lo: float, hi: float) -> bool:
    """FIG-04's and FIG-06's points: the shared rule (`bar_hidden`, decided per point from the panel's final axis limits); True means the
    point's 95% bar is shorter than its marker and is not drawn, and the caption names the point ("bars shorter than the marker are not
    drawn")."""
    return bar_hidden(ax, model, lo, hi, y=y)


def _fig0406_tag(ax, letter: str, title: str) -> None:
    """The panel letter (the shared bold letter) and a title of at most four words beside it (Karen's F16), written like FIG-03's and
    FIG-05's: a capital first, regular weight, 8 pt."""
    panel_tag(ax, letter)
    ax.annotate(title, xy=(0, 1.03), xycoords="axes fraction", xytext=(12, 0), textcoords="offset points", fontsize=LAB, color=INK,
                ha="left", va="bottom")


def _fig0406_en_dash(c: Cell) -> Cell:
    """The same cell with the paper's en dash in 'Clopper–Pearson' (one form everywhere, Edith §2.9)."""
    import dataclasses
    return dataclasses.replace(c, printed=c.printed.replace("Clopper-Pearson", "Clopper–Pearson"))


def _fig0406_study1_flags(S: Store, drawn: Sequence[str]) -> List[Cell]:
    """Study 1's settings that the figure does not draw and that the format check flags on a shape, each with its format compliance (one
    decimal): a flag must not be lost when its point moves to a table (Edith §8.7). Empty where none is flagged."""
    items: List[List[Cell]] = []
    for arm in STUDY1_ARMS:
        if arm in drawn:
            continue
        for shape in ("1x6", "6x1"):
            key = join_key(*T24.split("."), f"{arm} {shape}", "format_compliance", "format_compliance")
            fkey = join_key("reporting", "group_b", "item_17", "flags", f"{arm} {shape}", "fires")
            if S.has("main", key) and S.has("main", fkey) and S.get("main", fkey) is True:
                items.append([L(f"{STUDY1_ARMS[arm][0]} on {SHAPE_WORD[shape]}"), joined(L("("), P(pct(S.ref("main", key))), L(")"), sep="")])
    return _seq(items, sep=";")


def _fig04_text(ax, x: float, y: float, text: str, dx: float, dy: float, ha: str, color: str = INK, va: str = "center") -> None:
    """A direct label 8 pt, offset in points from its point (no leader lines: a label stays beside its point)."""
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=LAB, color=color, ha=ha, va=va, zorder=7,
                annotation_clip=False, linespacing=1.0)


def _fig04_point(ax, x, y, lo, hi, model: str, effort: str, zorder: float = 4.0, bar_zorder: Optional[float] = None) -> bool:
    """The shared `mark` (the 95% bar 0.8 pt in the mark's colour, behind the marker), the marker unclipped (so a point at 100% is drawn
    whole). The return value says that the bar is shorter than the marker and is not drawn (see `_fig0406_bar_short`); the axis limits
    are set before the marks are drawn, since that test depends on them."""
    short = _fig0406_bar_short(ax, model, y, lo, hi)
    if mark(ax, x, y, lo, hi, model, effort, size=5.0, zorder=zorder, bar_zorder=bar_zorder, sliver_ok=True) != short:      # FIG-04's note says it
        raise ValueError("FIG-04: the marker and the caption disagree on which bars are not drawn")
    ax.lines[-1].set_clip_on(False)
    return short


def _fig04_groups(pts: Sequence[Tuple[str, str, float, float]]) -> List[List[str]]:
    """Sets of markers that overlap or touch in one panel: (tag, model, x pt, y pt) in, the tags of each connected set of two or more out.
    Two markers touch when their centres are closer than the sum of their own half-sizes (a diamond's is larger than a circle's)."""
    parent = {t: t for t, _, _, _ in pts}

    def root(t: str) -> str:
        while parent[t] != t:
            t = parent[t]
        return t
    for i, (ta, ma, xa, ya) in enumerate(pts):
        for tb, mb, xb, yb in pts[i + 1:]:
            if np.hypot(xa - xb, ya - yb) < _FIG0406_MARK_HALF_PT[ma] + _FIG0406_MARK_HALF_PT[mb]:
                parent[root(ta)] = root(tb)
    sets: Dict[str, List[str]] = {}
    for t, _, _, _ in pts:
        sets.setdefault(root(t), []).append(t)
    return [g for g in sets.values() if len(g) > 1]


# Panel A's inset (Edith's proof 3, Figure S4: the Opus settings low to xhigh and Sonnet-max overlap, and a marker is never moved to
# separate it): the five markers enlarged, at their measured positions, in the empty lower right of A, with a box on the panel that says
# where they come from and two connectors to it. Markers only: a bar or a line through a frame this small would run off it, and both are
# in the panel. Each label is the effort for an Opus setting (the legend-free reading of the panel's own labels) and the setting's name for
# Sonnet-max; the text is read from the tag table, only its offset is typed.
FIG04_INSET = {"box": (0.645, 0.12, 0.34, 0.41),       # the inset's frame in A's axes fractions: left, bottom, width, height
               "pad_x": 0.045, "pad_y": 1.5}              # the zoom range's margin: decades of cost either side of the five markers; points of accuracy below the lowest
# each label's offset from its marker in points and its alignment: (dx, dy, ha, va)
FIG04_INSET_LABELS = {"ol": (-5.0, 0.0, "right", "center"),
                      "om": (5.0, -3.0, "left", "center"),
                      "oh": (-5.0, 0.0, "right", "center"),
                      "oxh": (0.0, -5.0, "center", "top"),
                      "sx": (6.0, 6.0, "right", "bottom")}


def _fig04_inset(axA, rows: Dict[Tuple[str, str], Tuple[V, V, V, V]], tags: Sequence[str]) -> Any:
    """The inset of the markers that overlap in panel A (`tags`, read from the same rows as the panel's own markers) with its zoom box and
    connectors; returns the inset's axes. Cost is on a log axis like the panel's; accuracy stops at 100 as the panel's does (a marker at
    100 stands on the frame, whole, as it does on the panel's top edge)."""
    from matplotlib.patches import ConnectionPatch, Rectangle
    if sorted(tags) != sorted(FIG04_INSET_LABELS):
        raise ValueError(f"FIG-04: the inset is laid out for {sorted(FIG04_INSET_LABELS)}, not {sorted(tags)}: place its labels again")
    pts = [(t, rows[("N=6", t)]) for t in tags]
    cx = [r[3].val for _, r in pts]
    cy = [r[0].val for _, r in pts]
    xlo, xhi = min(cx) * 10.0 ** (-FIG04_INSET["pad_x"]), max(cx) * 10.0 ** FIG04_INSET["pad_x"]
    ylo = min(cy) - FIG04_INSET["pad_y"]
    pa = axA.get_position()
    bx, by, bw, bh = FIG04_INSET["box"]
    # a figure-level axes lying inside A's frame (a child of A would not have its tick labels read as ticks by the figure's text check)
    ins = axA.figure.add_axes([pa.x0 + bx * pa.width, pa.y0 + by * pa.height, bw * pa.width, bh * pa.height])
    ins.set_xscale("log")
    ins.set_xlim(xlo, xhi)
    ins.set_ylim(ylo, 100.0)
    ins.minorticks_off()
    for sp in ("top", "right"):
        ins.spines[sp].set_visible(True)
    tick_x = [t for t in (0.03, 0.04, 0.05, 0.06) if xlo < t < xhi]
    ins.set_xticks(tick_x)
    ins.set_xticklabels([fmt_cost(t) for t in tick_x])
    ins.set_yticks([v for v in range(int(np.ceil(ylo)), 101) if v % 2 == 0])
    ins.tick_params(length=2, pad=1.5)
    ins.set_axisbelow(True)
    ins.patch.set_facecolor("white")
    for t, r in pts:
        name, model, effort = STUDY1B_TAGS[t]
        st = style_for(model, effort)
        ins.plot([r[3].val], [r[0].val], linestyle="none", marker=st["marker"], markersize=5.0, markerfacecolor=st["color"],
                 markeredgecolor=st["color"], markeredgewidth=0.6, zorder=4.2 if model == "sonnet" else 4.0, clip_on=False)
        dx, dy, ha, va = FIG04_INSET_LABELS[t]
        ins.annotate(name if model == "sonnet" else effort, (r[3].val, r[0].val), xytext=(dx, dy), textcoords="offset points", fontsize=LAB,
                     color=style.MODEL_TEXT[model], ha=ha, va=va, zorder=7, annotation_clip=False, linespacing=1.0)
    # the zoom box on the panel and its two connectors (the box's lower corners to the inset's upper corners)
    axA.add_patch(Rectangle((xlo, ylo), xhi - xlo, 100.0 - ylo, facecolor="none", edgecolor=style.REFERENCE, linewidth=0.6, zorder=1.5,
                            clip_on=False))
    for xa, xb in ((xlo, 0.0), (xhi, 1.0)):
        axA.figure.add_artist(ConnectionPatch(xyA=(xa, ylo), coordsA=axA.transData, xyB=(xb, 1.0), coordsB=ins.transAxes, axesA=axA,
                                              axesB=ins, color=style.REFERENCE, linewidth=0.6, zorder=1.5, clip_on=False))
    return ins


@output("FIG-04")
@main_text
@plain_ids(main=True)
def fig_04(S: Store) -> FigureOut:
    """Accuracy against list cost per answer by model and effort (Study 1b). Per the user's ruling on F-11 (D-132, the merged option)
    the figure plots every measured setting with its tier in the caption, no fitted line and no point marked as a "best buy"; the
    cost-for-target view is the appendix table TAB-34."""
    s1b_sets_check(S)
    ef = "descriptive.effort_figure"
    W = COLW
    H = FIG04_H
    G = FIG04_GEOM
    fig = plt.figure(figsize=(W, H))

    def box(l: float, b: float, w: float, h: float) -> List[float]:
        return [l / W, b / H, w / W, h / H]
    # both panels draw the same inches per factor of ten in cost: the room left after the margins is shared in proportion to each
    # panel's cost range in decades
    dec_a, dec_b = (float(np.log10(FIG04_X[N][1] / FIG04_X[N][0])) for N in ("N=6", "N=16"))
    room = W - G["left"] - G["gap"] - G["right"]
    wA = room * dec_a / (dec_a + dec_b)
    wB = room - wA
    h_ax = H - G["bottom"] - G["top"]
    axA = fig.add_axes(box(G["left"], G["bottom"], wA, h_ax))
    axB = fig.add_axes(box(G["left"] + wA + G["gap"], G["bottom"], wB, h_ax), sharey=axA)
    axes = {"N=6": axA, "N=16": axB}
    panel_of = {"N=6": "A", "N=16": "B"}
    steps_of = {"N=6": "6 steps", "N=16": "16 steps"}
    points: List[Dict[str, Any]] = []
    rows: Dict[Tuple[str, str], Tuple[V, V, V, V]] = {}
    path: Dict[Tuple[str, str], List[Tuple[str, str, V, V, V, V]]] = {}        # (N, model) -> points in effort order
    recs: Dict[Tuple[str, str], Dict[str, Any]] = {}                # (N, tag) -> the point's data-file record, given its note once the layout is known
    flagged: List[List[Cell]] = []                                  # caption items: points whose format check fires on a shape
    for N in axes:
        steps_txt = steps_of[N]
        n_int = int(N.split("=")[1])
        for model in ("haiku", "sonnet", "opus"):
            if not S.has("s1b", f"{ef}.{N}.{model}"):
                continue
            ents = list(enumerate(S.get("s1b", f"{ef}.{N}.{model}")))
            for i, ent in sorted(ents, key=lambda t: FIG04_ORDER[t[1]["effort"]]):
                base = f"{ef}.{N}.{model}.{i}"
                tag = ent["tag"]
                # each point is a copy of the setting's stamped pooled values (checked), so it carries the setting's one interval
                for f in ("mean", "ci95", "interval", "cost_per_answer"):
                    if S.get("s1b", f"{base}.pooled.{f}") != S.get("s1b", join_key("descriptive", "arms", f"{tag}@{n_int}", "pooled", f)):
                        raise ValueError(f"FIG-04: {base}.pooled.{f} differs from descriptive.arms.{tag}@{n_int}")
                y = pv(S, "s1b", base + ".pooled.mean", prop=False)
                lo, hi = ci(S, "s1b", base + ".pooled.ci95", prop=False)
                cv = usd_val(S, "s1b", base + ".pooled.cost_per_answer")
                effort = ent["effort"]
                name = STUDY1B_TAGS[tag][0]
                has_width(f"FIG-04: {name} at {steps_txt}", lo, hi)        # the caption says that the vertical bars are 95% intervals
                # format compliance beside accuracy: stamped per shape (none for a pooled point), with the format flag
                fmts = [(SHAPE_WORD[sk], *s1b_format(S, tag, sk)) for sk in (f"1x{n_int}", f"{n_int}x1")]
                fires = [(sw, fc) for sw, fc, fl in fmts if fl.value is True]
                if fires:
                    flagged.append([L(f"{name} at {steps_txt}")] +
                                   _seq([[L(("(" if j == 0 else "") + sw), P(fc)] for j, (sw, fc) in enumerate(fires)]) + [L(")")])
                path.setdefault((N, model), []).append((tag, effort, y, lo, hi, cv))
                interval_type = method(S, "s1b", base + ".pooled.interval")
                tries = S.get("s1b", join_key("descriptive", "arms", f"{tag}@{N.split('=')[1]}", "tries_per_item"))
                # the caption names the interval methods by group: cluster bootstrap for the Haiku settings and Opus-medium (repeated
                # samples), exact for the other Opus and Sonnet settings (one sample); refuse a file that breaks that grouping
                boot = model == "haiku" or tag == "om"
                om_same = tag != "om" or tries == S.get("s1b", "descriptive.arms.om@6.tries_per_item")     # the caption prints om@6's
                if (interval_type.raw == "cluster bootstrap") != boot or (tries > 1) != boot or not om_same:
                    raise ValueError(f"FIG-04: {name} at {steps_txt} has interval {interval_type.raw!r} over {tries} samples per puzzle;"
                                     " the caption's interval grouping no longer holds")
                fmt_rec = {f"format_compliance_{sw}": fc for sw, fc, _ in fmts}
                fmt_rec.update({f"format_flag_{sw}": text_of(fl, {True: "flagged", False: "not flagged"}) for sw, _, fl in fmts})
                recs[(N, tag)] = rec(f"{name}, {steps_txt}", steps_txt, x=cv, y=y, lo=lo, hi=hi, interval=interval_type.printed, **fmt_rec)
                rows[(N, tag)] = (y, lo, hi, cv)

    # both panels draw accuracy from 0 to 100 on one shared axis (B reads A's range: the bars of Haiku with thinking off at 16 steps, 0.0 to
    # 1.1, are whole), and cost on their own ranges at one scale; the limits are set before any mark is drawn, since the test for a bar
    # shorter than its marker depends on them
    for N, ax in axes.items():
        cost_axis(ax, *FIG04_X[N], FIG04_TICKS)
    for ax in axes.values():
        acc_axis(ax, *FIG04_YLIM)
    plt.setp(axB.get_yticklabels(), visible=False)
    # one accuracy title for the row, on the left; one cost title for the row, centred under both panels
    tidy(axA, xlabel=COST_ANSWER, ylabel=ACC_LABEL)
    axA.xaxis.label.set_x((wA + G["gap"] + wB) / (2.0 * wA))
    for N, ax in axes.items():
        _fig0406_tag(ax, panel_of[N], steps_of[N])
    om_line = dict(color=style.MODEL_BASE["opus"], linestyle=(0, (4, 2.5)), linewidth=1.0, zorder=1)
    for N, ax in axes.items():
        ax.axhline(rows[(N, "om")][0].val, **om_line)         # Opus-medium's accuracy in each panel
    short_names: Dict[str, List[str]] = {"A": [], "B": []}   # the panel -> the points whose bar is shorter than the marker (not drawn)
    short_tags = set()                                       # (N, tag) of those points, for the data file's notes
    sliver_names: Dict[str, List[str]] = {"A": [], "B": []}  # the panel -> the points whose bar is only just longer than the marker (drawn in front)
    sliver_tags = set()                                      # (N, tag) of those points, for the data file's notes
    centres: Dict[str, List[Tuple[str, str, float, float]]] = {"A": [], "B": []}      # (tag, model, x pt, y pt) of every marker drawn
    n_drawn = {"A": 0, "B": 0}
    for (N, model), pts in path.items():
        ax, letter = axes[N], panel_of[N]
        col = style.MODEL_BASE[model]
        if len(pts) > 1:
            ax.plot([p[5].val for p in pts], [p[2].val for p in pts], color=col, linewidth=1.0, zorder=2, solid_capstyle="round")
        for tag, effort, y, lo, hi, cv in pts:
            px, py = ax.transData.transform((cv.val, y.val)) * 72.0 / fig.dpi
            ax_l, ax_r = (ax.transData.transform((x, 0.0))[0] * 72.0 / fig.dpi for x in FIG04_X[N])
            if px - _FIG0406_MARK_HALF_PT[model] < ax_l or px + _FIG0406_MARK_HALF_PT[model] > ax_r:
                raise ValueError(f"FIG-04: {STUDY1B_TAGS[tag][0]} at {steps_of[N]} is not whole inside its panel's cost range; widen the range")
            centres[letter].append((tag, model, float(px), float(py)))
            n_drawn[letter] += 1
            # Sonnet's markers and bars are drawn over Opus's where they overlap, so that Sonnet-max's square and its bar stay seen (Edith's
            # PR 34 round 2: Sonnet-max's bar stood under the Opus diamonds)
            if _fig04_point(ax, cv.val, y.val, lo.val, hi.val, model, effort, zorder=4.2 if model == "sonnet" else 4.0,
                            bar_zorder=4.1 if model == "sonnet" else None):
                short_names[letter].append(STUDY1B_TAGS[tag][0])
                short_tags.add((N, tag))
            elif bar_sliver(ax, model, lo.val, hi.val, y=y.val):       # drawn, in front of the marker (`mark`): the caption says why
                sliver_names[letter].append(STUDY1B_TAGS[tag][0])
                sliver_tags.add((N, tag))

    # markers that overlap or touch: named in the caption with their values in TAB-12, since moving a point to separate it would misplace
    # it; the labels below are placed for exactly these sets, and a data change that makes other sets stops the build
    groups = {letter: [sorted(g, key=lambda t: (STUDY1B_TAGS[t][1] != "opus", FIG04_ORDER[STUDY1B_TAGS[t][2]])) for g in _fig04_groups(pts)]
              for letter, pts in centres.items()}
    expected = {"A": [{"hl", "hm"}, {"sl", "sm"}, {"ol", "om", "oh", "oxh", "sx"}], "B": []}
    for letter in ("A", "B"):
        if sorted(sorted(g) for g in groups[letter]) != sorted(sorted(g) for g in expected[letter]):
            raise ValueError(f"FIG-04: the markers that overlap or touch in {letter} are now {groups[letter]}, not {expected[letter]}: place the labels again")
    in_group = {(letter, t): g for letter, gs in groups.items() for g in gs for t in g}
    for (N, tag), r in recs.items():
        g = in_group.get((panel_of[N], tag))
        r["note"] = (f"its marker overlaps or touches {len(g) - 1} other{'s' if len(g) > 2 else ''} in panel {panel_of[N]}, so its value is read in TAB-12"
                     + ("; the inset in panel A enlarges it, with the four others it overlaps" if g and len(g) > 2 else "")
                     if g else f"drawn in panel {panel_of[N]}") + (
            "; its 95% bar is shorter than its marker, and neither end reaches a printed point past the marker’s edge, so it is not drawn (its ends are lo and hi)"
            if (N, tag) in short_tags else
            "; its 95% bar is only just longer than its marker (neither end reaches a printed point past the marker’s edge), so it is drawn just to"
            " the right of the marker" if (N, tag) in sliver_tags else "")
        points.append(r)

    # direct labels, each in its model's text colour (so that a label next to another model's marker is read as its own model's)
    ct = style.MODEL_TEXT

    def lab(N: str, tag: str, text: str, dx: float, dy: float, ha: str, va: str = "center", under_bar: bool = False) -> None:
        """A label beside its marker, or (under_bar) under the lower end of its 95% bar."""
        y, lo, hi, cv = rows[(N, tag)]
        _fig04_text(axes[N], cv.val, lo.val if under_bar else y.val, text, dx, dy, ha, ct[STUDY1B_TAGS[tag][1]], va)

    def vtxt(N: str, tag: str, word: str, sep: str = " ") -> str:
        return f"{word}{sep}{rows[(N, tag)][0].cell.printed}%"

    def pair(N: str, a: str, b: str, text: str, dx: float, dy: float, ha: str, va: str = "center", where: str = "mid") -> None:
        """One label for two overlapping markers: at the first one's cost, at the pair's mean accuracy ('mid') or under the pair's lower bar."""
        ya, yb = rows[(N, a)][0].val, rows[(N, b)][0].val
        y = (ya + yb) / 2.0 if where == "mid" else min(rows[(N, a)][1].val, rows[(N, b)][1].val)
        _fig04_text(axes[N], rows[(N, a)][3].val, y, text, dx, dy, ha, ct[STUDY1B_TAGS[a][1]], va)
    # A: Haiku's path. Low and medium are one label (their markers touch), set left of the pair at its mean height, where it stands apart
    # from the other settings' labels (right of the pair it read as belonging to high)
    lab("N=6", "ho", vtxt("N=6", "ho", "off"), 6, -1, "left")
    pair("N=6", "hl", "hm", "low, medium", -6.5, 0, "right")
    lab("N=6", "hh", "high", 6, 0, "left")
    lab("N=6", "hxh", "xhigh", 5, -6, "left")
    lab("N=6", "hx", vtxt("N=6", "hx", "Haiku-max", "\n"), 0, -7, "left", "top")
    # Sonnet: low and medium are one marker (the same accuracy, costs a hair apart), named once under its bar, in two lines that end left of
    # the inset's connector; high and xhigh share a label in the row above the plot. Sonnet-max, which sits among the Opus diamonds, is
    # named in the inset
    pair("N=6", "sl", "sm", "Sonnet-low,\nmedium", -9, -3, "right", "top", where="low")
    x_sh = float(np.exp(np.mean([np.log(rows[("N=6", t)][3].val) for t in ("sh", "sxh")])))
    _fig04_text(axA, x_sh, FIG04_YLIM[1], "Sonnet-high, xhigh", 3, 5, "right", ct["sonnet"], "bottom")
    # the Opus settings low to xhigh and Sonnet-max overlap each other: the inset below enlarges them and names each; Opus-max, clear of them,
    # has its own label over its diamond
    _fig04_text(axA, rows[("N=6", "ox")][3].val, FIG04_YLIM[1], "Opus-max", 0, 5, "center", ct["opus"], "bottom")
    big = [g for g in groups["A"] if len(g) > 2]
    if len(big) != 1:
        raise ValueError("FIG-04: panel A has no single cluster of more than two markers for the inset: place the labels again")
    _fig04_inset(axA, rows, big[0])
    # B
    lab("N=16", "ho", vtxt("N=16", "ho", "off"), 12, 5, "left")
    lab("N=16", "hl", "low", -6, 3, "right")
    lab("N=16", "hm", "medium", 6, 0, "left")
    lab("N=16", "hh", "high", 6, 0, "left")
    lab("N=16", "hxh", "xhigh", 6, 0, "left")
    lab("N=16", "hx", vtxt("N=16", "hx", "Haiku-max", "\n"), 6, -9, "left")
    # the dashed line is named with its value at its left end, below it
    for N, ax in axes.items():
        om_val = rows[(N, "om")][0].cell.printed
        ax.annotate(f"Opus-medium\n{om_val}%", (0.0, rows[(N, "om")][0].val), xycoords=ax.get_yaxis_transform(), xytext=(4, -3),
                    textcoords="offset points", fontsize=LAB, color=ct["opus"], ha="left", va="top", zorder=7, linespacing=1.0)

    def ent(N, tag):
        return rows[(N, tag)]

    # the alt text says Sonnet-low and Sonnet-medium score the same, and that high and max bound the Opus settings at 6 steps: checked
    o6 = {t: rows[("N=6", t)][0].val for t in ("ol", "om", "oh", "oxh", "ox")}
    if ent("N=6", "sl")[0].cell.printed != ent("N=6", "sm")[0].cell.printed or min(o6, key=o6.get) != "oh" or max(o6, key=o6.get) != "ox":
        raise ValueError("FIG-04: Sonnet-low and Sonnet-medium differ, or high and max no longer bound the Opus settings: reword the alt text")

    # caption facts for what the plot cannot show on its own: bars hidden by their markers, and markers that overlap
    def names_of(ns: Sequence[str]) -> str:
        """'A and B' (two), 'A, B and C'; where a name holds a comma ('Haiku, thinking off': one name per setting, Edith's proof 4) three or
        more items are separated by semicolons, as 'A; B, C; and D' (as `_fig07_and`)."""
        if len(ns) == 1:
            return ns[0]
        if len(ns) >= 3 and any("," in n for n in ns):
            return "; ".join(ns[:-1]) + "; and " + ns[-1]
        return ", ".join(ns[:-1]) + " and " + ns[-1]
    # one entry per panel: 'every point in A', or 'Opus-medium in A'; where a name holds a comma the entries read 'in B: Haiku, thinking off;
    # Haiku-max; and Opus-medium', so that the semicolons inside an entry and between entries stay apart
    def panel_bits(by_panel: Dict[str, List[str]]) -> str:
        comma = any("," in n for letter in ("A", "B") for n in by_panel[letter])
        return "; ".join(("every point in " + letter) if len(by_panel[letter]) == n_drawn[letter] else
                         ("in " + letter + ": " + names_of(by_panel[letter]) if comma else names_of(by_panel[letter]) + " in " + letter)
                         for letter in ("A", "B") if by_panel[letter])
    short_bits = panel_bits(short_names)
    sliver_bits = panel_bits(sliver_names)
    # one test for every figure (`bar_hidden`, per point): a bar whose whole span is shorter than its marker, and neither end of which reaches 1 pt
    # past the marker's edge, is not drawn, and only those; a drawn bar that stands under 1 pt past the edge (`bar_sliver`) is drawn in front
    short_note = ([L("; 95% bars shorter than their markers, with neither end reaching a printed point past the marker’s edge, are not drawn (" + short_bits + "),"
                     " and their interval ends are in TAB-12 and this figure's data file")] if short_bits else [])
    sliver_note = ([L("; a 95% bar only just longer than its marker, with neither end reaching a printed point past the marker’s edge, is drawn just to"
                      " the right of the marker (" + sliver_bits + ")")] if sliver_bits else [])
    touch_bits: List[Cell] = []
    for letter in ("A", "B"):
        for g in sorted(groups[letter], key=lambda gg: min(centres[letter][[c[0] for c in centres[letter]].index(t)][2] for t in gg)):
            N = "N=6" if letter == "A" else "N=16"
            ys = [rows[(N, t)][0] for t in g]
            item: List[Cell] = [L(names_of([STUDY1B_TAGS[t][0] for t in g]) + " in " + letter + (", enlarged in its inset" if len(g) > 2 else ""))]
            if len({y.cell.printed for y in ys}) == 1:
                item += [L("(both"), joined(P(ys[0].cell), L(")"), sep="")]
            else:
                # '(52.8% and 54.5%)', '(98.8%, 99.4%, 96.3%, 97.5% and 100.0%)': the values in the order of the names
                n = len(ys)
                for j, y in enumerate(ys):
                    if j == n - 1:
                        item.append(L("and"))
                    item.append(joined(*(([L("(")] if j == 0 else []) + [P(y.cell)] + ([L(")")] if j == n - 1 else [L(",")] if j < n - 2 else [])), sep=""))
            touch_bits += ([L(";")] if touch_bits else []) + item
    touch_note = ([L("; markers that overlap or touch are drawn at their measured values, which are in TAB-12 and this figure's data file;"
                     " the inset in A, boxed on the panel, enlarges the cluster of five markers that overlap (markers only: their lines and 95% bars"
                     " are in the panel), and an effort label that cannot be placed beside such a marker names the set:")] + touch_bits) if touch_bits else []
    s1_flags = _fig0406_study1_flags(S, drawn=())
    fmt4: List[Cell] = [L("format compliance, the share of answered samples in the required format, is stamped per shape (none for a pooled"
                          " point): each point's chain and pieces values and format flags are in this figure's data file and in TAB-12")]
    if flagged:
        fmt4 += [L("; the format check (its rule is in TAB-07) flags these points on the shape named:")] + _seq(flagged, sep=";") + [
            L("; no other point is flagged, and no flagged point is marked in the plot")]
    else:
        fmt4 += [L("; the format check flags no point drawn")]
    if s1_flags:
        fmt4 += [L("; of Study 1's settings, which are not drawn here (their values are in TAB-04, which prints format compliance to two"
                   " decimals where this figure prints one), the format check flags")] + s1_flags + [L(", and its rule is in TAB-07")]
    alt = [L("Two panels of whole-answer accuracy against list cost per answer on a log axis, from Study 1b's effort sweep, with each model's"
             " settings joined in effort order and each point labelled with its setting: 6 steps (A), for all three models, and 16 steps (B), for"
             " Haiku and Opus-medium. Both panels share one accuracy axis, from zero to one hundred percent. Points pool chains and pieces. A dashed"
             " line marks Opus-medium's accuracy in each panel. In A the markers for Haiku-low and Haiku-medium, for Sonnet-low and"
             " Sonnet-medium, and for the Opus settings low to xhigh with Sonnet-max overlap, so their values are in TAB-12. A small box at the top right of"
             " A, around the five overlapping markers of the Opus settings low to xhigh and Sonnet-max, is joined by two lines to an inset below"
             " it that enlarges them: the same markers at their measured cost and accuracy, each labelled, with no bars or lines."),
           L("At 6 steps Haiku accuracy rises with effort from"), P(ent("N=6", "ho")[0].cell), L("with thinking off, through"), P(ent("N=6", "hl")[0].cell),
           L("at low and"), P(ent("N=6", "hm")[0].cell), L("at medium, to"), P(ent("N=6", "hx")[0].cell), L("at max, while its cost per answer rises from"),
           ent("N=6", "ho")[3].cell, L("to"), ent("N=6", "hx")[3].cell, L("US dollars. Sonnet-low and Sonnet-medium are both at"),
           P(ent("N=6", "sl")[0].cell), L("and Sonnet-max is at"), P(ent("N=6", "sx")[0].cell), L(". The Opus settings lie between"),
           P(ent("N=6", "oh")[0].cell), L("at high and"), P(ent("N=6", "ox")[0].cell), L("at max; Opus-medium is at"), P(ent("N=6", "om")[0].cell),
           L("for"), ent("N=6", "om")[3].cell, L("dollars."),
           L("At 16 steps Haiku rises from"), P(ent("N=16", "ho")[0].cell), L("with thinking off to"), P(ent("N=16", "hm")[0].cell), L("at medium and"),
           P(ent("N=16", "hx")[0].cell), L("at max for"), ent("N=16", "hx")[3].cell, L("dollars, beside"), P(ent("N=16", "om")[0].cell),
           L("for Opus-medium at"), ent("N=16", "om")[3].cell, L("dollars.")]
    caption = {"tier": [L("pre-specified descriptive (effort sweep, no tests)")],
               "study": [L("Study 1b effort sweep at 6 steps and 16 steps")],
               "set": [L("Study 1b's 6-step set, on which Test B3 ran, and its 16-step set, on which Tests B1 and B2 ran")],
               "n": [L("puzzles:"), integer(S.ref("s1b", "descriptive.arms.hm@6.pooled.n_base")), L("at 6 steps and"),
                     integer(S.ref("s1b", "descriptive.arms.hm@16.pooled.n_base")), L("at 16 steps, each pooled over chains and pieces")],
               "interval": [L("vertical bars are 95% intervals:"), _fig0406_en_dash(method(S, "s1b", "descriptive.arms.hm@6.pooled.interval")),
                            L("for the Haiku settings (several samples per puzzle) and for Opus-medium, over"),
                            integer(S.ref("s1b", "descriptive.arms.om@6.tries_per_item")), L("samples per puzzle;"),
                            _fig0406_en_dash(method(S, "s1b", "descriptive.arms.ol@6.pooled.interval")),
                            L("for the other Opus and Sonnet settings (one sample per puzzle)")],
               "price": price_study1b(S),
               "format": fmt4,
               "note": [L("points pool chains and pieces; the words beside the points are efforts (off is thinking off); the dashed line is"
                          " Opus-medium's accuracy in each panel; both panels draw accuracy on the same axis, from zero to one hundred percent, and cost"
                          " on their own ranges at the same distance per factor of ten")] + short_note + sliver_note + touch_note + [
                   L("; Study 1's 6-step settings on other puzzles, one point per shape, are not drawn here: they are in TAB-04 (and"
                     " Haiku-medium, Haiku-max and Opus-medium are in FIG-06); nothing is fitted and no point is marked as a best buy: the points are"
                     " measured values, each with its label, and the cheapest measured setting for a target accuracy is in TAB-34 (appendix, post hoc)")]}
    return FigureOut(fig, points, tight(alt), tight_caption(caption))


# ================================================================ FIG-05

LC_TAG = {"haiku-max": "hx", "opus-medium": "om"}           # Study 1b length_curve keys -> their descriptive.arms tags
PRESET_WORDS = {"l14_to_l16": "three rule-set presets", "l14_only": "the one preset used later"}   # g5's plain words for l14-l16, l14
PANEL_WORDS = {"chain": "chains", "pieces": "pieces", "pooled": "pooled over shapes"}
# The length sweep's file under each marking rule: the official rule (Deviation 2; the d90 re-score) and the original rule (as locked in
# Lock 2). The main figure reads the first, its appendix version the second.
RULE_SRC = {"official": "curve_d90", "original": "curve"}
RULE_WORDS = {"official": "the official marking rule (Deviation 2)", "original": "the original marking rule (as locked in Lock 2, before Deviation 2)"}
P1_TIER = "exploratory"         # Pilot 1's markers (Edith's PR 27 ruling Q13: exploratory, after C-079 and E-12; E-01's tier withdrawn)
LADDER = (("hm", "Haiku-medium"), ("sm", "Sonnet-medium"), ("om", "Opus-medium"))
SWEEP_SHAPE = {"chain": "1xn", "pieces": "nx1", "pooled": "pooled"}
FIG05_PANELS = ("chain", "pieces", "pooled")
FIG05_DODGE = {"hm": 0.0, "sm": -0.55, "om": 0.55}            # horizontal shifts in steps (display only): the markers and bars of one length stay apart
                                                              # (0.4 left a marker 0.4 to 0.8 pt from a neighbouring series' bar or marker; 0.55 leaves
                                                              # at least 1.7 pt, and keeps Opus-medium at one length 0.9 steps from Sonnet-medium at the next);
                                                              # Haiku-medium, the series set against q^N, stands at its true length
FIG05_BAND_ALPHA = 0.16                                       # the q^N band's opacity (Karen's F8: a curve's band at 15 to 20%)
FIG05_N_PT = LAB                                              # the exponent of q^N prints at the label size (the superscript of a math label would print at
                                                              # 70% of 8 pt, 5.6 pt: under Edith's floor for figure text, 8 pt, section 8.2, and the
                                                              # style's own check, which asks 8 to 10 pt for text that is not a tick label)
FIG05_N_RAISE = 3.0                                           # points: the exponent's baseline stands this far above the label's
# Pilot 1's recount of its 24-step Opus-medium marker (the stamped file that says which marking rule the marker is under and what the format
# check says under each rule); pinned at the commit that added it
FIG05_RECOUNT = register_source(Source(
    name="pilot1_recount", path="data/pilot/pilot1-recount-e12.json", commit="e585a6d",
    sha256="a31c905f25113112ab23539445cb2e7edae04222b0290918e8c934bfb22d32aa", kind="json",
    what="Pilot 1's 24-step Opus-medium marker recounted: its chain format compliance and the format check's verdict under each marking rule"))
FIG05_Z = {"hm": 4, "sm": 5, "om": 3}                         # drawing order: Sonnet-medium above Haiku-medium above Opus-medium (a line of one
                                                              # series does not run through another's marker)
FIG05_XLIM = (2.6, 17.4)                                     # the length axis: 4 to 16 steps
FIG05_TITLE = {"chain": "Chains", "pieces": "Pieces (hollow)", "pooled": "Pooled over shapes"}   # the legend's swatches are filled: panel B says its markers are hollow
FIG05_LW = 1.0                                                # the joining lines are thin (Edith's PR 34 review): the markers and bars carry the reading
FIG05_EXACT_NOTE = ("the bootstrap interval collapsed to a point; the bar is the exact (Clopper–Pearson) 95% interval from free analysis 4"
                    " (post hoc†), over exact_n puzzles, exact_x of them right")


def _seq(cells: List[Cell], sep: str = ",", last: str = "") -> List[Cell]:
    """`cells` grouped as items (each a list) joined by a separator label, the last item followed by `last` (if any)."""
    out: List[Cell] = []
    for i, item in enumerate(cells):
        out += item
        if i < len(cells) - 1:
            out.append(L(sep))
        elif last:
            out.append(L(last))
    return out


def _same_both_rules(S: Store, key: str) -> bool:
    return S.get("curve", key) == S.get("curve_d90", key)


FIG05_TAG_LIFT = 2.0            # points: the panel letter and title stand this much higher than the shared helper puts them (see _fig05_tag)
FIG05_GAP_PAD_PT = (1.5, 0.5)   # points: the margin (across, up and down) round a direct label's text where the gridlines stop (see _fig05_grid_gap); a gridline just above or below the text stays whole
FIG05_APP_YLO = -4.0            # the appendix's row-one accuracy axes start this far below zero (Edith's D-168, page 105: Pilot 1's Haiku-medium markers, at 0.8% and 2.0%, stood on the axis); the three panels share it, so that their gridlines line up (display only)
FIG05_GAP_Z = 0.6               # the gridlines (axisbelow) stand at 0.5: the gap patch lies just above the grid and under all data
FIG05_BAND_Z = 0.7              # the q^N band (translucent) stands just above the gap patch, so that the patch never whitens its edge


def _fig05_tag(ax, letter: str, title: str) -> None:
    """The panel letter (the shared bold letter) and a title of at most four words beside it (Karen's F16), both lifted by FIG05_TAG_LIFT
    points: Opus-medium's markers at 100% stand on the top edge of the axes, and with the shared offset (1.03 axes heights, 2.8 to 3.5 pt in
    these panels) their tips touch the title text. A shared change of `panel_tag` would make this lift unnecessary."""
    panel_tag(ax, letter)
    height_pt = ax.get_position().height * ax.figure.get_figheight() * 72.0
    ax.texts[-1].set_y(1.03 + FIG05_TAG_LIFT / height_pt)
    ax.annotate(title, xy=(0, 1.03), xycoords="axes fraction", xytext=(12, FIG05_TAG_LIFT), textcoords="offset points", fontsize=LAB,
                color=INK, ha="left", va="bottom")


def _fig05_grid_gap(ax, texts: Sequence[Any], pad_pt: Tuple[float, float] = FIG05_GAP_PAD_PT) -> None:
    """The gridlines stop at a direct label instead of running through its text (Edith's PR 34 round 2, FIG-05 and its appendix: gridlines
    cross labels): a white patch the size of the label (its texts' joint box, with a margin), drawn just above the gridlines and under
    everything else (band, lines, bars, markers), so that the grid is cut behind the words and nothing that is data is."""
    from matplotlib.patches import Rectangle
    fig = ax.figure
    rend = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(rend) for t in texts]
    px, py = (v * fig.dpi / 72.0 for v in pad_pt)
    (x0, y0), (x1, y1) = ax.transData.inverted().transform(
        [(min(b.x0 for b in boxes) - px, min(b.y0 for b in boxes) - py), (max(b.x1 for b in boxes) + px, max(b.y1 for b in boxes) + py)])
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="white", edgecolor="none", linewidth=0, zorder=FIG05_GAP_Z, clip_on=False))


def _fig05_qn(ax, x: float, y: float, color_: str, tail: str = "", head: str = "", dy_pt: float = 2.2) -> List[Any]:
    """The label 'q^N' (preceded by `head` and followed by `tail`, if any), centred on the data point (x, y) with its baseline `dy_pt` points
    above y, built from separate texts: $q$ and $N$ at the label size (8 pt), $N$ raised by FIG05_N_RAISE points, then the tail. A one-piece
    math label would set the exponent at 70% of the label size, 5.6 pt, below Edith's floor for figure text (section 8.2; the paper's PDF
    check reads the size of every span). The texts are laid out from their measured widths."""
    fig = ax.figure
    rend = fig.canvas.get_renderer()
    parts = ([(head, LAB, 0.0, 2.2)] if head else []) + [("$q$", LAB, 0.0, -1.3), ("$N$", FIG05_N_PT, FIG05_N_RAISE, -1.2 if tail[:1] == "," else 1.2)] + (
        [(tail, LAB, 0.0, 0.0)] if tail else [])
    widths = []
    for text, size, _, _ in parts:
        t = fig.text(0, 0, text, fontsize=size)
        widths.append(t.get_window_extent(rend).width * 72.0 / fig.dpi)
        t.remove()
    total = sum(widths) + sum(g for *_, g in parts[:-1])
    at = -total / 2.0
    drawn = []
    for (text, size, raise_pt, gap), w in zip(parts, widths):
        drawn.append(ax.annotate(text, xy=(x, y), xycoords="data", xytext=(at, dy_pt + raise_pt), textcoords="offset points", fontsize=size,
                                 color=color_, ha="left", va="baseline"))
        at += w + gap
    return drawn


FIG05_REF_AT = 12.0             # steps: where the reference label's block is centred in panel A (display)
FIG05_REF_LEFT = 8.6            # steps: the block's left end; its bottom stands above the band there, where the band is highest under the block
FIG05_REF_LEAD = 13.0           # steps: where the label's leader meets the dashed line (clear of Haiku-medium's 95% bar at 12 steps and of the blue line)


def _fig05_ref_label(ax, q: Dict[str, Any], color_: str) -> None:
    """The reference line is named once, in panel A, in the grey of the line and with its model (Edith's PR 34 review: a reader could apply
    q^N to Sonnet or Opus): 'Haiku-medium' over 'q^N (not fitted)', as a two-line block centred at FIG05_REF_AT steps and standing just above
    the band's upper edge at the block's left end (the band falls to the right)."""
    top = float(np.interp(FIG05_REF_LEFT, q["x"], q["hi"]))
    height_pt = ax.get_position().height * ax.figure.get_figheight() * 72.0
    y = top + 2.5 * 100.0 / height_pt                      # the baseline of the lower line: 2.5 pt above the band
    texts = _fig05_qn(ax, FIG05_REF_AT, y, color_, tail="(not fitted)", dy_pt=0.0)
    texts.append(ax.annotate("Haiku-medium", xy=(FIG05_REF_AT, y), xycoords="data", xytext=(0, 9.6), textcoords="offset points", fontsize=LAB,
                             color=color_, ha="center", va="baseline"))
    _fig05_grid_gap(ax, texts)
    # a short leader in the line's grey from under the block to the dashed line, so that the grey block reads as the dashed line's name and
    # not as the name of the blue line that runs beside it (Edith's PR 34 review; the checker's round 2)
    y_line = float(np.interp(FIG05_REF_LEAD, q["x"], q["y"]))
    ax.plot([FIG05_REF_LEAD, FIG05_REF_LEAD], [y_line + 1.0 * 100.0 / height_pt, y - 3.4 * 100.0 / height_pt], color=color_, linewidth=0.6,
            solid_capstyle="butt", zorder=2)


def _fig05_series(ax, xs: List[float], ys: List[float], los: List[float], his: List[float], exact: List[Optional["Exact"]], model: str,
                  effort: str, hollow: bool = False, lw: float = FIG05_LW, size: float = 5.0, zorder: int = 4) -> List[bool]:
    """One model's points at the lengths it ran, joined by a line in length order: a 95% bar on each (0.8 pt, no caps; free analysis 4's
    exact interval, post hoc, drawn the same way where the bootstrap collapsed), the marker filled (chains, or pooled) or hollow
    (pieces); markers at the panel's edge are drawn whole. The bar is left out only where the shared rule (`bar_hidden`, per point: its
    whole span is shorter than its marker and neither arm sticks out) says so, and the result says for which points (True), so that the
    caption names them. A bar only just longer than its marker (`bar_sliver`) stops the build: the captions have no words for it. The
    panel's axis limits must be set before the call."""
    st = style_for(model, effort)
    hidden: List[bool] = []
    for x, y, lo, hi, ex in zip(xs, ys, los, his, exact):
        blo, bhi = (ex.lo.val, ex.hi.val) if ex is not None else (lo, hi)
        hidden.append(bar_hidden(ax, model, blo, bhi, size, y=y))
        if hidden[-1]:
            continue
        forbid_sliver("FIG-05", ax, model, blo, bhi, size, y=y)        # a bar only just longer than its marker has no words in these captions
        if ex is not None:
            exact_bar(ax, x, y, blo, bhi, st["color"], zorder=zorder - 1)
        else:
            ax.errorbar([x], [y], yerr=[[y - lo], [hi - y]], fmt="none", ecolor=st["color"], elinewidth=0.8, capsize=0, zorder=zorder - 1)
    ax.plot(xs, ys, color=st["color"], linewidth=lw, zorder=zorder, clip_on=False)
    ax.plot(xs, ys, linestyle="none", marker=st["marker"], markersize=size, markerfacecolor="white" if hollow else st["color"],
            markeredgecolor=st["color"], markeredgewidth=1.1 if hollow else 0.6, zorder=zorder + 1, clip_on=False)
    return hidden


def _fig05_hidden_items(items: List[Tuple[str, Optional[Cell], V, V]]) -> List[Cell]:
    """The points whose 95% bar the shared short-bar rule leaves out (`bar_hidden`: the bar's whole span is shorter than its marker, so
    it would stand behind the marker), as words: each item is (what, its length in steps or None, the interval's lower end, its upper
    end), the ends as drawn (free analysis 4's exact ends where the bootstrap collapsed)."""
    out: List[Cell] = []
    for i, item in enumerate(items):
        what, nc, lo, hi = item[:4]
        est = item[4] if len(item) > 4 else None          # the point's own value, where the drawing cannot show it (Pilot 1 on the axis)
        out += [L(("; " if i else "") + what + (", at" if nc is not None else ""))] + ([nc, L("steps")] if nc is not None else []) + (
            [L("scores"), P(est.cell)] if est is not None else []) + [L("(95% interval"), P(lo.cell), L("to"), P(hi.cell), L(")")]
    return out


def _fig05_hidden_words(items: List[Tuple[str, Optional[Cell], V, V]], lead: str = "") -> List[Cell]:
    """The caption words for those points (empty when no bar is left out); `lead` is put before the first word."""
    if not items:
        return []
    return [L(lead + "bars shorter than the marker are not drawn (a 95% bar that lies behind its marker, neither end reaching a printed point past its"
                     " edge); the points concerned, with their interval ends:")] + _fig05_hidden_items(items)


def _fig05_hidden_alt(items: List[Tuple[str, Optional[Cell], V, V]]) -> List[Cell]:
    """The alt text's sentence for those points (empty when no bar is left out)."""
    if not items:
        return []
    return [L("Bars shorter than the marker are not drawn, for:")] + _fig05_hidden_items(
        items) + [L(".")]


# ---------------------------------------------------------------- reading (no drawing)


def _fig05_read_sweep(S: Store, ns: List[str], rule: str, points: List[Dict[str, Any]], drawn: Tuple[str, ...] = FIG05_PANELS) -> Dict[str, Any]:
    """The length sweep under one marking rule: Haiku-medium, Sonnet-medium and Opus-medium, whole-answer accuracy, for chains, pieces
    and both pooled, with each point's 95% interval (free analysis 4's exact interval where the bootstrap collapsed), and on chains
    each point's format compliance and flag. The curve file stamps 'wilson' on the one-sample Sonnet-medium and Opus-medium entries by
    shape and no method name elsewhere; there the method is quoted from the plan (checked: a stamped method elsewhere, or a missing
    one on a by-shape one-sample entry, refuses the build). A panel the figure does not draw (not in `drawn`) is read and recorded all
    the same, its records say so, and its exact bars are not listed as drawn."""
    R = RULE_SRC[rule]
    plan_boot = quoted(S, "curve_plan", r"^- \*\*Haiku:\*\* a cluster bootstrap over base puzzles", "a cluster bootstrap")
    plan_pooled = quoted(S, "curve_plan", r"^- \*\*Opus and Sonnet:\*\* a Wilson interval for each shape",
                         "The pooled panel uses the same cluster bootstrap")
    plan_wilson = quoted(S, "curve_plan", r"^- \*\*Opus and Sonnet:\*\* a Wilson interval for each shape", "a Wilson interval for each shape")
    out: Dict[str, Any] = {"R": R, "rule": rule, "rows": {}, "exact": [], "wilson_key": None, "firsts": {}, "flags": {}, "lows": [],
                           "plan": (plan_boot, plan_pooled, plan_wilson)}
    for m, nm in LADDER:
        for pn in FIG05_PANELS:
            rows = []
            for n in ns:
                nc, nf = key_cell(R, f"models.{m}.by_n", n)
                bn = f"models.{m}.by_n.{n}"
                base = f"{bn}.whole_answer.{SWEEP_SHAPE[pn]}"
                y = pv(S, R, base + ".mean")
                lo, hi = ci(S, R, base + ".ci95")
                stamped = S.get(R, base + ".interval") if S.has(R, base + ".interval") else None
                one_try_by_shape = m != "hm" and pn != "pooled"
                if (stamped == "wilson") != one_try_by_shape or stamped not in (None, "wilson"):
                    raise ValueError(f"FIG-05: {R}:{base} stamps interval {stamped!r}; the caption's method grouping no longer holds")
                if stamped and out["wilson_key"] is None:
                    out["wilson_key"] = base + ".interval"
                meth_cell = method(S, R, base + ".interval") if stamped else (plan_boot if m == "hm" else plan_pooled)
                ex, note = None, None
                if collapsed(lo, hi):
                    ex = fa4_bar(S, R, base, y, lo, hi)
                    if pn in drawn:
                        out["exact"].append((f"length-sweep {nm}", nc, pn, ex))
                    note = FIG05_EXACT_NOTE
                    out["lows"].append(ex.lo)
                else:
                    out["lows"].append(lo)
                if pn not in drawn:
                    note = "; ".join(x for x in (note, "not drawn in this version: the same values as the main version's pieces panel (checked)") if x)
                extra: Dict[str, Any] = {}
                if pn == "chain":
                    fc = pct(S.ref(R, bn + ".format_compliance_1xn"))
                    flag = S.get(R, bn + ".format_flag") is True
                    extra = {"format_compliance_1xn": fc,
                             "format_flag": text_of(S.ref(R, bn + ".format_flag"), {True: "flagged", False: "not flagged"})}
                    out["flags"][(m, n)] = (fc, flag, nc)
                points.append(rec(f"{nm}, length sweep", pn, x=nc, y=y, lo=lo, hi=hi, interval=meth_cell, rule=RULE_WORDS[rule],
                                  note=note, **exact_rec(ex), **extra))
                out["firsts"][(m, pn, n)] = (nc, y, lo, hi)
                rows.append({"nc": nc, "nf": nf, "y": y, "lo": lo, "hi": hi, "ex": ex})
            out["rows"][(m, pn)] = rows
    return out


def _fig05_read_q(S: Store, R: str, ns: List[str], points: List[Dict[str, Any]], extend: bool) -> Dict[str, Any]:
    """The q^N reference (Haiku-medium's per-piece rate q, from pieces only, raised to the number of steps) with its 95% band: at the
    sweep's lengths for the main version (`extend` False), and for the appendix version only its extension to 24 steps (`extend` True),
    read for the Pilot 1 panel (the 4 to 16 step values are the same under both rules, checked by the caller, and are drawn in the main
    version)."""
    out: Dict[str, Any] = {"x": [], "y": [], "lo": [], "hi": [], "first": {}}
    if not extend:
        for n in ns:
            nc, nf = key_cell(R, "models.hm.by_n", n)
            qb = f"models.hm.q.by_n.{n}"
            y = pv(S, R, qb + ".q_n")
            lo, hi = ci(S, R, qb + ".band")
            # a band of no width could not be replaced by an exact interval (free analysis 4 has none for q: no single count carries it)
            has_width(f"FIG-05: the q^N band at {n} steps", lo, hi)
            out["x"].append(nf); out["y"].append(y.val); out["lo"].append(lo.val); out["hi"].append(hi.val)
            out["first"][n] = (nc, y)
            for pn in FIG05_PANELS:
                points.append(rec("Haiku-medium q^N reference (q from pieces only)", pn, x=nc, y=y, lo=lo, hi=hi))
    else:
        q24c, q24f = key_cell(R, "models.hm.q", "24")
        q24 = pv(S, R, "models.hm.q.24.q_n")
        q24lo, q24hi = ci(S, R, "models.hm.q.24.band")
        has_width("FIG-05: the q^N band's extension to 24 steps", q24lo, q24hi)
        q24_label = text_of(S.ref(R, "models.hm.q.24.label"))
        points.append(rec("Haiku-medium q^N reference, extended to 24 steps", "Pilot 1 panel", x=q24c, y=q24, lo=q24lo, hi=q24hi,
                          note=q24_label.printed))
        out.update({"q24c": q24c, "q24f": q24f, "q24": q24, "q24lo": q24lo, "q24hi": q24hi, "q24_label": q24_label})
    return out


def _fig05_read_s1b(S: Store, points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Study 1b's Haiku-max and Opus-medium at the lengths that study ran (its own puzzle sets; its own series), lengths in numeric
    order, for chains, pieces and both pooled, with each point's 95% interval and, on chains, its format compliance and flag."""
    lcs = "descriptive.length_curve"
    out: Dict[str, Any] = {"rows": {}, "lens": {}, "cp": [], "exact": [], "flags": {}, "lows": []}
    for key, nm, tag in (("haiku-max", "Haiku-max", "hx"), ("opus-medium", "Opus-medium", "om")):
        lens = sorted(S.keys("s1b", f"{lcs}.{key}"), key=int)
        out["lens"][key] = lens
        for n in lens:            # structure check: each length-curve entry is the setting's own stamped value
            for sk in (f"1x{n}", f"{n}x1", "pooled"):
                for f in ("mean", "ci95", "interval"):
                    if S.get("s1b", f"{lcs}.{key}.{n}.{sk}.{f}") != S.get("s1b", f"descriptive.arms.{tag}@{n}.{sk}.{f}"):
                        raise ValueError(f"s1b {lcs}.{key}.{n}.{sk}.{f} differs from descriptive.arms.{tag}@{n}")
        for pn in FIG05_PANELS:
            rows = []
            for n in lens:
                nc, nf = key_cell("s1b", f"{lcs}.{key}", n)
                sk = {"chain": f"1x{n}", "pieces": f"{n}x1", "pooled": "pooled"}[pn]
                base = f"{lcs}.{key}.{n}.{sk}"
                y = pv(S, "s1b", base + ".mean", prop=False)
                lo, hi = ci(S, "s1b", base + ".ci95", prop=False)
                mc = method(S, "s1b", base + ".interval")
                if S.get("s1b", base + ".interval") == "clopper-pearson":
                    out["cp"].append((nm, nc, pn, mc))
                ex, note = None, None
                if collapsed(lo, hi):
                    # fa4's cell for the length curve's own copy (the key plotted); the setting's own cell, where fa4 stamps one, must
                    # carry the same exact ends (one value, one interval)
                    ex = fa4_bar(S, "s1b", base, y, lo, hi)
                    arm = fa4_exact(S, "s1b", f"descriptive.arms.{tag}@{n}.{sk}")
                    if arm is not None and any(abs(_need_num(r) * arm.scale - e.val) > 1e-9 for r, e in ((arm.lo, ex.lo), (arm.hi, ex.hi))):
                        raise ValueError(f"FIG-05: fa4's exact interval for {base} differs from the setting's {tag}@{n} {sk}")
                    out["exact"].append((f"Study 1b {nm}", nc, pn, ex))
                    note = FIG05_EXACT_NOTE
                    out["lows"].append(ex.lo)
                else:
                    out["lows"].append(lo)
                extra: Dict[str, Any] = {}
                if pn == "chain":
                    fr = "descriptive.format_refusals_truncations_missing"
                    fc = pct(S.ref("s1b", join_key(*fr.split("."), "format_report", tag, sk, "format_compliance")))
                    fl = S.ref("s1b", join_key(*fr.split("."), "item_17_flags", f"{tag} {sk}", "fires"))
                    extra = {"format_compliance_1xn": fc, "format_flag": text_of(fl, {True: "flagged", False: "not flagged"})}
                    out["flags"][(key, n)] = (fc, fl.value is True, nc)
                points.append(rec(f"{nm}, Study 1b", pn, x=nc, y=y, lo=lo, hi=hi, interval=mc.printed, note=note, **exact_rec(ex), **extra))
                rows.append({"nc": nc, "nf": nf, "y": y, "lo": lo, "hi": hi, "ex": ex})
            out["rows"][(key, pn)] = rows
    return out


def _fig05_p1_flag(S: Store) -> Dict[str, Any]:
    """The format check's verdict on Pilot 1's 24-step Opus-medium marker on the three rule-set presets (chains), under each marking rule,
    read from the stamped recount (the curve files stamp no format compliance for Pilot 1). Checks that the recount's pooled means and
    puzzle count are the markers the figure reads from the curve files and that the check flags the chains under the original rule and
    not under the official rule (the caption fact says so); else the build stops and the words need rewriting."""
    out: Dict[str, Any] = {}
    for prule, key in (("original", "original"), ("official", "d2")):
        base = f"result.{key}"
        for f, ck in (("pooled_mean", "mean"), ("n_base", "n_base")):
            if abs(_need_num(S.ref("pilot1_recount", f"{base}.{f}")) - _need_num(S.ref(RULE_SRC[prule], f"pilot1.om.l14_to_l16.{ck}"))) > 1e-9:
                raise ValueError(f"FIG-05: Pilot 1's recount ({base}.{f}) is not the curve file's marker ({RULE_SRC[prule]}): reword the flag")
        out[prule] = {"fc": pct(S.ref("pilot1_recount", f"{base}.by_shape.1x24.format_compliance")),
                      "flag": text_of(S.ref("pilot1_recount", f"{base}.flag_above_5pct_non_compliance.1x24"),
                                      {True: "flagged", False: "not flagged"}),
                      "pieces": S.get("pilot1_recount", f"{base}.flag_above_5pct_non_compliance.24x1")}
    if (out["original"]["flag"].printed, out["official"]["flag"].printed) != ("flagged", "not flagged") or any(
            v["pieces"] is not False for v in out.values()):
        raise ValueError("FIG-05: Pilot 1's format flag is no longer 'chains, original rule only': reword the caption")
    out["rule"] = quoted_field(S, "pilot1_recount", "flag_rule", "above 5%")
    return out


def _fig05_read_p1(S: Store, points: List[Dict[str, Any]], q24c: Cell, draw_rule: str) -> Dict[str, Any]:
    """Pilot 1 at 24 steps (pooled over shapes only, as stamped) under both marking rules, for each model and each of its two preset
    groups. A marker the two rules draw alike is recorded under both rules and drawn once; where they differ, the marker of `draw_rule` is
    drawn and the other is recorded as not drawn (its value is in the caption)."""
    out: Dict[str, Any] = {"v": {}, "nb": {}, "exact": [], "lows": []}
    for m, model in (("hm", "haiku"), ("sm", "sonnet"), ("om", "opus")):
        for which in ("l14_to_l16", "l14_only"):
            got: Dict[str, Dict[str, Any]] = {}
            for prule in ("official", "original"):
                src = RULE_SRC[prule]
                base = f"pilot1.{m}.{which}"
                if S.has(src, base + ".interval"):
                    raise ValueError(f"FIG-05: {src}:{base} now names its interval method: print it")
                y = pv(S, src, base + ".mean")
                lo, hi = ci(S, src, base + ".ci95")
                nb = integer(S.ref(src, base + ".n_base"))
                if which in out["nb"] and out["nb"][which].raw != nb.raw:
                    raise ValueError(f"Pilot 1 {which}: puzzles differ between models or rules")
                out["nb"].setdefault(which, nb)
                ex = None
                if collapsed(lo, hi):
                    ex = fa4_bar(S, src, base, y, lo, hi)
                    if ex.n.raw != nb.raw:
                        raise ValueError(f"FIG-05: fa4's exact interval for {src}:{base} is over {ex.n.raw} puzzles, Pilot 1's {nb.raw}")
                    out["lows"].append(ex.lo)
                else:
                    out["lows"].append(lo)
                got[prule] = {"y": y, "lo": lo, "hi": hi, "ex": ex, "model": model, "nb": nb}
                out["v"][(m, which, prule)] = got[prule]
            same = all(a.ref.value == b.ref.value for a, b in zip((got["official"][k] for k in ("y", "lo", "hi")),
                                                                  (got["original"][k] for k in ("y", "lo", "hi"))))
            for prule in ("official", "original"):
                v = got[prule]
                drawn_here = same or prule == draw_rule
                if prule == draw_rule and v["ex"] is not None:
                    out["exact"].append((f"Pilot 1 {STUDY1B_TAGS[m][0]} on {PRESET_WORDS[which]}", None, "pooled", v["ex"]))
                where = ("drawn once: the two rules give the same marker" if same else
                         "drawn in this version" if drawn_here else "not drawn in this version (the value is in the caption)")
                flag = {}
                if (m, which) == ("om", "l14_to_l16"):          # the one Pilot 1 marker whose chain format compliance is stamped (the recount)
                    fl = _fig05_p1_flag(S)[prule]
                    flag = {"format_compliance_1xn": fl["fc"], "format_flag": fl["flag"]}
                points.append(rec(f"{STUDY1B_TAGS[m][0]}, Pilot 1 ({PRESET_WORDS[which]})", "Pilot 1 panel", x=q24c, y=v["y"], lo=v["lo"],
                                  hi=v["hi"], puzzles=v["nb"], rule=RULE_WORDS[prule], tier=P1_TIER, **exact_rec(v["ex"]), **flag,
                                  note=f"Pilot 1, before Lock 2 (different rule mix, sets and timing), on {PRESET_WORDS[which]}; pooled over"
                                       f" shapes; {where}" + ("; " + FIG05_EXACT_NOTE if v["ex"] else "")))
    return out


# ---------------------------------------------------------------- caption pieces shared by the main figure and its appendix version


def _fig05_steps_list(cells: List[Cell]) -> List[Cell]:
    """'6 steps, 12 steps and 16 steps' from step cells (each read as a key name)."""
    out: List[Cell] = []
    for i, c in enumerate(cells):
        out += [c, L("steps" + ("," if i < len(cells) - 2 else (" and" if i == len(cells) - 2 else "")))]
    return out


def _fig05_paren(c: Cell) -> Cell:
    """'(94.5%' for a bracketed value (the closing bracket is attached by `tight`)."""
    return joined(L("("), c, sep="")


def _fig05_format_fact(S: Store, ns: List[str], sw: Dict[str, Any], s1b: Optional[Dict[str, Any]]) -> Tuple[List[Cell], List[Cell]]:
    """Format compliance on chains beside each length (the length sweep under its rule; Study 1b where the figure draws it), and the
    names of the points the pre-registered format check flags (Edith §8.7: a flag is named in the caption, not drawn)."""
    R, rule = sw["R"], sw["rule"]
    fmt: List[Cell] = [L("format compliance on chains, the share of chain answers in the required format, beside each length. Length sweep, under "
                         + RULE_WORDS[rule] + ":")]
    flagged: List[Cell] = []
    for m, nm in LADDER:
        items = []
        for n in ns:
            bn = f"models.{m}.by_n.{n}"
            it = [P(pct(S.ref(R, bn + ".format_compliance_1xn"))), L("at"), key_cell(R, f"models.{m}.by_n", n)[0], L("steps")]
            if S.get(R, bn + ".format_flag") is True:
                it.append(text_of(S.ref(R, bn + ".format_flag"), {True: "(flagged)"}))
                flagged.append([L(nm), L("at"), key_cell(R, f"models.{m}.by_n", n)[0], L("steps"),
                                _fig05_paren(P(pct(S.ref(R, bn + ".format_compliance_1xn")))), L(")")])
            items.append(it)
        fmt += [L(nm)] + _seq(items, last=";" if (s1b is not None or m != LADDER[-1][0]) else "")
    if s1b is not None:
        fmt.append(L("Study 1b, read from its own analysis file (the same in both versions of this figure):"))
        fr = "descriptive.format_refusals_truncations_missing"
        for i, (key, nm) in enumerate((("haiku-max", "Haiku-max"), ("opus-medium", "Opus-medium"))):
            tag, items = LC_TAG[key], []
            for n in s1b["lens"][key]:
                sk = f"1x{n}"
                fc = pct(S.ref("s1b", join_key(*fr.split("."), "format_report", tag, sk, "format_compliance")))
                it = [P(fc), L("at"), key_cell("s1b", f"descriptive.length_curve.{key}", n)[0], L("steps")]
                fl = S.ref("s1b", join_key(*fr.split("."), "item_17_flags", f"{tag} {sk}", "fires"))
                if fl.value is True:
                    it.append(text_of(fl, {True: "(flagged)"}))
                    flagged.append([L(f"Study 1b {nm}"), L("at"), key_cell("s1b", f"descriptive.length_curve.{key}", n)[0], L("steps"),
                                    _fig05_paren(P(fc)), L(")")])
                items.append(it)
            fmt += [L(nm)] + _seq(items, last=";" if i == 0 else "")
        fmt.append(L("; Pilot 1's format compliance is not stamped in the curve files"))
    if flagged:
        flag_fact = [L("points flagged by the pre-registered format check, all on chains (their format compliance in brackets):")] + _seq(flagged, sep=";")
    else:
        flag_fact = [L("no point is flagged by the format check")]
    return fmt, flag_fact


def _fig05_interval_fact(S: Store, sw: Dict[str, Any], exact_used: List[Tuple[str, Optional[Cell], str, "Exact"]],
                         s1b: Optional[Dict[str, Any]], pilot: bool) -> List[Cell]:
    """The 95% intervals' methods as stamped, and where a bar is free analysis 4's exact interval (post hoc†)."""
    R = sw["R"]
    plan_boot, plan_pooled, plan_wilson = sw["plan"]

    def q(c: Cell) -> Cell:
        return joined(L("\u201c"), c, L("\u201d"), sep="")
    icap: List[Cell] = [L("95%, drawn as bars, as stamped. Length sweep:"), method(S, R, sw["wilson_key"]),
                        L("for one-sample Sonnet-medium and Opus-medium by shape, as the curve file stamps it (the plan:"), q(plan_wilson),
                        L("); for Haiku-medium and every pooled point the curve file stamps"), integer(S.ref(R, "draws")),
                        L("draws and no method name, and the length sweep's analysis plan names it:"), q(plan_boot), L("over puzzles for Haiku, and"),
                        q(plan_pooled)]
    if s1b is not None:
        lcs = "descriptive.length_curve"
        icap += [L(". Study 1b:"), method(S, "s1b", f"{lcs}.haiku-max.{s1b['lens']['haiku-max'][0]}.pooled.interval")]
        if s1b["cp"]:                 # grouped by series and length: 'Opus-medium at 12 steps (chains, pieces, pooled over shapes)'
            groups: Dict[Tuple[str, str], Tuple[Cell, List[str]]] = {}
            for nm, nc, pn, _ in s1b["cp"]:
                groups.setdefault((nm, nc.printed), (nc, []))[1].append(PANEL_WORDS[pn])
            icap += [L(", and"), s1b["cp"][0][3], L("where stamped:")]
            icap += _seq([[L(nm), L("at"), nc, L("steps (" + ", ".join(pns) + ")")] for (nm, _), (nc, pns) in groups.items()], sep=";")
    if exact_used:
        icap += [L(". Where a bootstrap interval collapsed to a point, the bar is free analysis 4's exact (Clopper–Pearson) 95%"
                   " interval over puzzles, post hoc†:")]
        icap += _seq([_exact_where(words, nc, pn) + [L(","), P(ex.lo.cell), L("to"), P(ex.hi.cell)] for words, nc, pn, ex in exact_used],
                     sep=";")
    if pilot:
        p1_exact = any(nc is None for _, nc, _, _ in exact_used)
        icap += [L(". Pilot 1" + (" (where no exact bar is drawn)" if p1_exact else "") + ": the curve file's stamped interval; the file"
                   " names no method, and the plan draws these markers"),
                 q(quoted(S, "curve_plan", r"pooled pilot-1 whole-answer mean for those presets", "with the cluster-bootstrap interval"))]
    return icap


def _fig05_n_fact(S: Store, R: str, ns: List[str], s1b: Optional[Dict[str, Any]], p1_nb: Optional[Dict[str, Cell]]) -> List[Cell]:
    """Puzzles and samples per puzzle: the length sweep's puzzles are one stamped value at every length, model and shape (checked)."""
    nbk = [f"models.{m}.by_n.{n}.whole_answer.{sh}.n_base" for m, _ in LADDER for n in ns for sh in ("1xn", "nx1", "pooled")]
    if len({S.get(R, k) for k in nbk}) != 1:
        raise ValueError("length sweep puzzles differ between lengths, models or shapes: print each")
    ncap: List[Cell] = [L("length sweep: puzzles per length, model and shape:"), integer(S.ref(R, nbk[0])),
                        L("(the same at every length); samples per puzzle and shape: Haiku-medium"),
                        integer(S.ref(R, "models.hm.tries_per_puzzle")), L(", Sonnet-medium"),
                        integer(S.ref(R, "models.sm.tries_per_puzzle")), L(", Opus-medium"),
                        integer(S.ref(R, "models.om.tries_per_puzzle"))]
    if s1b is not None:
        ncap.append(L("; Study 1b (puzzles, then samples per puzzle and shape):"))
        for i, (key, nm) in enumerate((("haiku-max", "Haiku-max"), ("opus-medium", "Opus-medium"))):
            tag = LC_TAG[key]
            items = [[key_cell("s1b", f"descriptive.length_curve.{key}", n)[0], L("steps:"),
                      integer(S.ref("s1b", f"descriptive.arms.{tag}@{n}.pooled.n_base")), L("and"),
                      integer(S.ref("s1b", f"descriptive.arms.{tag}@{n}.tries_per_item"))] for n in s1b["lens"][key]]
            ncap += [L(nm)] + _seq(items, last=";" if i == 0 else "")
    if p1_nb is not None:
        ncap += [L("; Pilot 1:"), p1_nb["l14_to_l16"], L("puzzles on"), L(PRESET_WORDS["l14_to_l16"]), L("and"), p1_nb["l14_only"], L("on"),
                 L(PRESET_WORDS["l14_only"]), L("(its samples per puzzle are not stamped in the curve files)")]
    return ncap


def _fig05_local(S: Store, src: str, ns: List[str], rule: str, points: List[Dict[str, Any]]) -> List[Cell]:
    """The chains' own local^N values (post hoc†) under one marking rule, not drawn (Karen's F3: at most four series in a panel): Haiku-medium's
    per-step accuracy on chains, among placeable chain samples (conditional on format), raised to the number of steps, each with its
    placeable count. Each value is recorded as a point of the figure (its record names it as not drawn) and returned as caption cells."""
    items: List[List[Cell]] = []
    for n in ns:
        nc, nf = key_cell(src, "models.hm.by_n", n)
        bn = f"models.hm.by_n.{n}"
        d = derive(f"100 * x ** {int(n)}", lambda x, n=int(n): 100.0 * x ** n, S.ref(src, f"{bn}.per_step.1xn.mean"))
        ra, ru = S.ref(src, bn + ".answered_1xn"), S.ref(src, bn + ".unplaceable_1xn")
        plc = num_d(derive("answered_1xn - unplaceable_1xn", lambda a_, u_: a_ - u_, ra, ru), dp=0)
        value = num_d(d, dp=1, bounds=PCT_BOUNDS)
        points.append(rec("Haiku-medium chains' own local^N (post hoc†; not drawn, printed in the caption)", "chain", x=nc, y=value,
                          placeable_samples=plc, answered_samples=integer(ra), unplaceable_samples=integer(ru), rule=RULE_WORDS[rule],
                          note="the stamped per-step accuracy on chains (each step judged from the model's own previous balances), among"
                               " placeable samples (conditional on format), raised to N"))
        items.append([P(value), L("at"), nc, L("steps"), _fig05_paren(plc), L("of"), integer(ra), L("answered samples placeable"), L(")")])
    return _seq(items)


# ---------------------------------------------------------------- the figure


@output("FIG-05")
@main_text
@plain_ids(main=True)
def fig_05(S: Store) -> FigureOut:
    """Length curve, with its appendix version as a variant (written as FIG-05.appendix.*).

    The main version: the length sweep (Haiku-medium, Sonnet-medium, Opus-medium) under the official marking rule (Deviation 2; the d90
    curve file) in three panels (chains, pieces, pooled over shapes), with the q^N reference as one grey dashed line with its band.
    Study 1b's and Pilot 1's points are not in it (approved through Jarvis; Edith's conditions, f38f53d): they are printed in the
    appendix version.
    The appendix version: the length sweep under the original marking rule (chains and pooled; pieces are the same under both rules;
    the official rule's Sonnet-medium, the one series the rules change, is not drawn: the main version draws it, and its values are the
    caption fact `both_rules`); Pilot 1's markers at 24 steps, under the original rule like the rest of the row (the one marker that the
    official rule changes, Opus-medium on the three presets, is named with its value and interval in the caption fact `rule`, not drawn;
    under the original rule its chain format check is flagged, named in the caption fact `flagged`); and Study 1b's Haiku-max and
    Opus-medium at the lengths that study ran, on its own puzzle sets, on zoomed accuracy axes whose cut is drawn as a break mark (the title
    stays Accuracy (%); the start is in the caption), named by a key of its own above the row, headed by the row's tier (the legend above row
    one names row one's settings; Haiku-max has Haiku-medium's colour and shape).

    Both: a flagged point is named in the caption facts, not ringed (Edith §8.7; Karen's F2). The chains' own local^N line (post hoc) is
    not drawn in either version (Karen's F3: at most four series in a panel); its values, with their placeable counts, are the caption fact
    `local` of both versions (the appendix version prints both marking rules), and each is recorded as a point of the figure.
    Intervals are bars, not bands: each length has its own puzzle set, so a band would imply intervals between the lengths, and three models'
    bands overlap (Sonnet-medium's and Opus-medium's on chains)."""
    ns = sorted(S.keys("curve_d90", "models.hm.by_n"), key=int)
    for m, _ in LADDER:
        for src in RULE_SRC.values():
            if sorted(S.keys(src, f"models.{m}.by_n"), key=int) != ns:
                raise ValueError(f"{src}: models.{m} has other lengths than the d90 file's Haiku-medium")
    main = _fig05_body(S, ns)
    main.variants = [("appendix", _fig05_appendix(S, ns))]
    return main


def _fig05_body(S: Store, ns: List[str]) -> FigureOut:
    W, H = COLW, 2.6
    left, right, gap, top, bottom = 0.58, 0.10, 0.14, 0.50, 0.50
    pw, ph = (W - left - right - 2 * gap) / 3, H - top - bottom
    fig = plt.figure(figsize=(W, H))
    ax = {pn: fig.add_axes([(left + i * (pw + gap)) / W, bottom / H, pw / W, ph / H]) for i, pn in enumerate(FIG05_PANELS)}
    points: List[Dict[str, Any]] = []
    sw = _fig05_read_sweep(S, ns, "official", points)
    R = sw["R"]
    q = _fig05_read_q(S, R, ns, points, extend=False)
    c_ref = style.REFERENCE
    hidden: List[Tuple[str, Optional[Cell], V, V]] = []        # the points whose bar the shared short-bar rule leaves out (named in the caption)
    for pn, a in ax.items():
        a.set_xlim(*FIG05_XLIM)
        a.set_xticks([int(n) for n in ns])
        acc_axis(a, 0.0, 100.0)                                 # the limits first: the bars are decided from them
        tidy(a)
        a.fill_between(q["x"], q["lo"], q["hi"], color=c_ref, alpha=FIG05_BAND_ALPHA, linewidth=0, zorder=FIG05_BAND_Z)
        a.plot(q["x"], q["y"], color=c_ref, linewidth=1.0, linestyle=(0, (4, 2)), zorder=2)
        for m, nm in LADDER:
            rows = sw["rows"][(m, pn)]
            model = STUDY1B_TAGS[m][1]
            flags = _fig05_series(a, [r["nf"] + FIG05_DODGE[m] for r in rows], [r["y"].val for r in rows], [r["lo"].val for r in rows],
                                  [r["hi"].val for r in rows], [r["ex"] for r in rows], model, "medium", hollow=(pn == "pieces"),
                                  zorder=FIG05_Z[m])
            hidden += [(f"{nm}, {PANEL_WORDS[pn]}", r["nc"], *((r["ex"].lo, r["ex"].hi) if r["ex"] is not None else (r["lo"], r["hi"])))
                       for r, h in zip(rows, flags) if h]
        _fig05_tag(a, "ABC"[FIG05_PANELS.index(pn)], FIG05_TITLE[pn])
    ax["chain"].set_ylabel(ACC_LABEL)
    for pn in ("pieces", "pooled"):
        ax[pn].tick_params(labelleft=False)
    ax["pieces"].set_xlabel("Steps in the puzzle")
    # the reference line is named once, in the first panel, in the grey of the line
    n_last = ns[-1]
    _fig05_ref_label(ax["chain"], q, c_ref)
    # a legend, not direct labels (F13): a name needs about half an inch at a line's end, and the right-hand ends of the three series are
    # taken by each other's 95% bars in every panel (Sonnet-medium's and Opus-medium's bars at 16 steps, Haiku-medium's under the q^N band),
    # so a name there would sit on a bar, or the lengths would have to be squeezed by a quarter of the panel's width
    handles = [Line2D([0], [0], color=color(model, "medium"), linewidth=FIG05_LW, marker=MODEL_MARKER[model], markersize=5, markeredgewidth=0.6)
               for _, model in (("hm", "haiku"), ("sm", "sonnet"), ("om", "opus"))]
    fig.legend(handles=handles, labels=[nm for _, nm in LADDER], loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), frameon=False,
               handlelength=2.0, columnspacing=2.0, handletextpad=0.6)

    # alt text
    firsts = sw["firsts"]
    n_first = ns[0]

    def y_of(m: str, pn: str, n: str) -> Cell:
        return firsts[(m, pn, n)][1].cell
    alt = [L("Three panels of whole-answer accuracy against puzzle length, for chains, pieces and both pooled, in the length sweep on other"
             " puzzles. Each model's accuracies are joined by a line in length order, with a 95% bar on each point (hollow markers in the pieces"
             " panel); Sonnet-medium and Opus-medium are shifted a little to the left and to the right of each length to keep the markers and bars of"
             " one length apart, and Haiku-medium stands at its true length. A grey dashed line with a light band is the reference q^N, built from Haiku-medium's per-piece"
             " accuracy; it is labelled once, in panel A, Haiku-medium q^N (not fitted), with a short grey leader from the label to the line. Panel B's"
             " title says its markers are hollow."),
           L("Haiku-medium pooled accuracy falls from"), P(y_of("hm", "pooled", n_first)), L("at"), firsts[("hm", "pooled", n_first)][0],
           L("steps to"), P(y_of("hm", "pooled", n_last)), L("at"), firsts[("hm", "pooled", n_last)][0], L("steps, while Opus-medium is at"),
           P(y_of("om", "pooled", n_first)), L("and"), P(y_of("om", "pooled", n_last)), L("and Sonnet-medium goes from"),
           P(y_of("sm", "pooled", n_first)), L("to"), P(y_of("sm", "pooled", n_last)), L("."),
           L("The reference line, the independent-pieces line, reaches"), P(q["first"][n_last][1].cell), L("at"), q["first"][n_last][0],
           L("steps. The points that the format check flags on chains are named in the caption. The chains' own per-step line (post hoc†) is not"
             " drawn; its values, with their placeable counts, are in this figure's data file."),
           L("Study 1b's Haiku-max and Opus-medium and Pilot 1's markers at 24 steps are in the appendix version of this figure.")]
    if sw["exact"]:
        alt += [L("Bars drawn from exact 95% intervals, post hoc, where a bootstrap interval collapsed to a point:")]
        alt += _seq([_exact_where(words, nc, pn) for words, nc, pn, _ in sw["exact"]], sep=";", last=".")
    alt += _fig05_hidden_alt(hidden)

    # caption facts
    fmt, flag_fact = _fig05_format_fact(S, ns, sw, None)
    tier = [L("pre-registered descriptive: the length sweep and the q^N line with its band; the exact intervals drawn as bars (listed with the"
              " intervals) and the chains' own per-step values (listed under local) are post hoc†")]
    local = [L("the chains' own per-step rate raised to the length (post hoc†; Haiku-medium, among placeable chain samples, conditional on format;"
               " not drawn) under the official marking rule:")] + _fig05_local(S, R, ns, "official", points)
    s1b_lens = sorted(S.keys("s1b", "descriptive.length_curve.haiku-max"), key=int)
    hm_1b_lens = sorted(S.keys("s1b", "descriptive.length_curve.haiku-medium"), key=int)
    elsewhere = [L("Study 1b's Haiku-max and Opus-medium at"),
                 *_fig05_steps_list([key_cell("s1b", "descriptive.length_curve.haiku-max", n)[0] for n in s1b_lens]),
                 L("(other puzzle sets; descriptive) and Pilot 1's markers at"), key_cell(R, "models.hm.q", "24")[0],
                 L("steps (exploratory‡: run before Lock 2, on other sets and rules) are not in this figure; they are in its appendix version."
                   " Study 1b's Haiku-medium at"),
                 *_fig05_steps_list([key_cell("s1b", "descriptive.length_curve.haiku-medium", n)[0] for n in hm_1b_lens]),
                 L("(other puzzle sets; descriptive) is in neither version of this figure: it is in TAB-12")]
    caption = {"tier": tier,
               "rule": [L("every length-sweep value uses the official marking rule (Deviation 2's repeated-line rule); the appendix version of this"
                          " figure draws the length sweep under the original marking rule as locked in Lock 2")],
               "study": [L("the length sweep with Haiku-medium, Sonnet-medium and Opus-medium")],
               "set": [L("the length sweep's ladder sets, one per length from 4 steps to 16 steps (other puzzles than Study 1)")],
               "n": _fig05_n_fact(S, R, ns, None, None),
               "format": fmt,
               "flagged": flag_fact,
               "local": local,
               "interval": _fig05_interval_fact(S, sw, sw["exact"], None, False),
               "reference": [L("the dashed grey line is q^N: Haiku-medium's per-piece rate q, from pieces pooled over the lengths, raised to the"
                               " number of steps N, with its 95% band; it compounds the rate over the steps, is not fitted and is not a test; panel A labels it once, with"
                               " Haiku-medium's name and \u201cnot fitted\u201d")],
               "elsewhere": elsewhere,
               "marks": [L("each model's points are joined by a line in length order, with a 95% bar on each; filled markers are chains and both shapes pooled,"
                           " hollow markers are pieces (panel B)")] + _fig05_hidden_words(hidden, "; "),
               "note": [L("the accuracy axes run from zero to the top of the scale; Sonnet-medium and Opus-medium are shifted a little to the left and"
                          " to the right of each length (display only) to keep the markers and bars of one length apart, while Haiku-medium, the series"
                          " set against the q^N line, stands at its true length; the lengths use different puzzle sets")],
               "price": [L("not applicable (no cost on this figure)")]}
    return FigureOut(fig, points, tight(alt), tight_caption(caption))


def _fig05_axis_start(lows: List["V"]) -> Cell:
    """The common lower end of the zoomed accuracy panels, as a derived value (no typed number in an axis title): the lowest plotted
    value or interval end, less two points (room for the axis break above the start, Karen's F10), rounded down to an even number."""
    import math
    lowest = min(lows, key=lambda v: v.val)
    return num_d(derive("floor((x - 2) / 2) * 2: the lowest plotted value or interval end, less 2, rounded down to an even number",
                        lambda x: float(math.floor((x - 2.0) / 2.0) * 2), lowest.ref), dp=0)


def _fig05_appendix(S: Store, ns: List[str]) -> FigureOut:
    """The appendix version: two rows of three panels. Row one (medium-effort settings, one legend above it): the length sweep under the
    original marking rule (A chains, B pooled over shapes; pieces are the same under both rules and are in the main version, checked),
    and C, Pilot 1's markers at 24 steps under the original rule. The official rule's Sonnet-medium, the one series the two rules change,
    is not drawn here (the main version draws it with its bars; its values are the caption fact `both_rules`). Row two: Study 1b's
    Haiku-max and Opus-medium at the lengths that study ran (D chains, E pieces, F pooled), on a zoomed accuracy axis with a break mark,
    named by a key of its own above the row (Edith's PR 34 review, MUST 5: the legend above row one calls the blue circle Haiku-medium)."""
    W, H = COLW, 4.6
    left, right, gap = 0.58, 0.10, 0.17
    pw = (W - left - right - 2 * gap) / 3
    top, mid, bottom = 0.48, 1.02, 0.58
    row_h = (H - top - mid - bottom) / 2
    row2_y, row1_y = bottom, bottom + row_h + mid
    fig = plt.figure(figsize=(W, H))

    def add(col: int, row_y: float):
        return fig.add_axes([(left + col * (pw + gap)) / W, row_y / H, pw / W, row_h / H])
    axA, axB, axC = (add(i, row1_y) for i in range(3))
    axD, axE, axF = (add(i, row2_y) for i in range(3))
    points: List[Dict[str, Any]] = []
    rule = "original"
    sw = _fig05_read_sweep(S, ns, rule, points, drawn=("chain", "pooled"))
    R = sw["R"]
    # the same values under both rules, as the caption says (checked, else the build stops); only Sonnet-medium's chain and pooled values
    # differ, so those are the lines drawn here and pieces are not drawn again
    for m in ("hm", "om"):
        for n in ns:
            for sh in SWEEP_SHAPE.values():
                for f in ("mean", "ci95"):
                    if not _same_both_rules(S, f"models.{m}.by_n.{n}.whole_answer.{sh}.{f}"):
                        raise ValueError(f"FIG-05 appendix: {m} {sh} at {n} steps differs between the rules; reword the caption")
    for n in ns:
        for f in ("mean", "ci95"):
            if not _same_both_rules(S, f"models.sm.by_n.{n}.whole_answer.nx1.{f}"):
                raise ValueError(f"FIG-05 appendix: Sonnet-medium pieces at {n} steps differs between the rules; reword the caption")
    for f in ("q", "ci95"):
        if not _same_both_rules(S, f"models.hm.q.{f}"):
            raise ValueError("FIG-05 appendix: Haiku-medium's q differs between the rules; reword the caption")
    for n in ns:
        if not _same_both_rules(S, f"models.hm.q.by_n.{n}"):
            raise ValueError("FIG-05 appendix: the q^N line differs between the rules; reword the caption")
    if not _same_both_rules(S, "models.hm.q.24"):
        raise ValueError("FIG-05 appendix: the q^N line at 24 steps differs between the rules; reword the caption")
    hm_fc_diff = [n for n in ns if not _same_both_rules(S, f"models.hm.by_n.{n}.format_compliance_1xn")]
    hm_ps_diff = [n for n in ns if not _same_both_rules(S, f"models.hm.by_n.{n}.per_step.1xn.mean")]
    om_all_same = all(_same_both_rules(S, f"models.om.by_n.{n}") for n in ns)

    # Sonnet-medium under the official rule: read for the caption (fact both_rules) and the alt text, recorded, not drawn (the main version
    # draws it in full, with its bars)
    sm_both: Dict[Tuple[str, str], Tuple[V, V]] = {}                 # (panel, n) -> (original, official) whole-answer accuracy
    for pn in ("chain", "pooled"):          # pieces are the same under both rules and are in the main version (checked above)
        for n in ns:
            nc, nf = key_cell("curve_d90", "models.sm.by_n", n)
            y = pv(S, "curve_d90", f"models.sm.by_n.{n}.whole_answer.{SWEEP_SHAPE[pn]}.mean")
            points.append(rec("Sonnet-medium, length sweep, official marking rule", pn, x=nc, y=y, rule=RULE_WORDS["official"],
                              note="not drawn in this version: the main version draws it with its bars; the values are in the caption"))
            sm_both[(pn, n)] = (sw["firsts"][("sm", pn, n)][1], y)
    # panels A and B (the limits first: the bars are decided from them; a bar the shared short-bar rule leaves out is named in the caption)
    hidden: List[Tuple[str, Optional[Cell], V, V]] = []
    for pn, a, letter in (("chain", axA, "A"), ("pooled", axB, "B")):
        a.set_xlim(*FIG05_XLIM)
        a.set_xticks([int(n) for n in ns])
        acc_axis(a, FIG05_APP_YLO, 100.0)
        tidy(a)
        for m, nm in LADDER:
            rows = sw["rows"][(m, pn)]
            flags = _fig05_series(a, [r["nf"] + FIG05_DODGE[m] for r in rows], [r["y"].val for r in rows], [r["lo"].val for r in rows],
                                  [r["hi"].val for r in rows], [r["ex"] for r in rows], STUDY1B_TAGS[m][1], "medium", zorder=FIG05_Z[m])
            hidden += [(f"{nm}, {PANEL_WORDS[pn]}", r["nc"], *((r["ex"].lo, r["ex"].hi) if r["ex"] is not None else (r["lo"], r["hi"])))
                       for r, h in zip(rows, flags) if h]
        _fig05_tag(a, letter, "Chains, original rule" if pn == "chain" else "Pooled, original rule")
    axA.set_ylabel(ACC_LABEL)
    axB.tick_params(labelleft=False)

    # panel C: Pilot 1 at 24 steps under the original rule, like the rest of the row (only Opus-medium on the three presets differs under the
    # official rule, and its official-rule value is named in the caption, not drawn), with the q^N reference extended to 24 steps
    q = _fig05_read_q(S, R, ns, points, extend=True)
    # the q^N line at the sweep's own lengths is the main version's, the same in both rules' files (checked above): its values are recorded
    # here under both files (not drawn in this version), and the official file's copy of the 24-step value beside the one drawn
    for src in RULE_SRC.values():
        for n in ns:
            qnc, _ = key_cell(src, "models.hm.by_n", n)
            qy, (qlo, qhi) = pv(S, src, f"models.hm.q.by_n.{n}.q_n"), ci(S, src, f"models.hm.q.by_n.{n}.band")
            points.append(rec("Haiku-medium q^N reference at the sweep's lengths (the main version's line; not drawn in this version)",
                              "A chains, B pooled", x=qnc, y=qy, lo=qlo, hi=qhi, rule=RULE_WORDS["official" if src == "curve_d90" else "original"]))
    q24o = pv(S, "curve_d90", "models.hm.q.24.q_n")
    points.append(rec("Haiku-medium q^N reference at 24 steps, the official rule's file (the same value as the one drawn)", "Pilot 1 panel",
                      x=q["q24c"], y=q24o, lo=ci(S, "curve_d90", "models.hm.q.24.band")[0], hi=ci(S, "curve_d90", "models.hm.q.24.band")[1]))
    p1 = _fig05_read_p1(S, points, q["q24c"], rule)
    c_ref = style.REFERENCE
    axC.axhspan(q["q24lo"].val, q["q24hi"].val, color=c_ref, alpha=FIG05_BAND_ALPHA, linewidth=0, zorder=FIG05_BAND_Z)
    axC.axhline(q["q24"].val, color=c_ref, linewidth=1.0, linestyle=(0, (4, 2)), zorder=2)
    p1_dodge = {"sm": -0.24, "hm": 0.0, "om": 0.24}                  # the order of the sweep's panels: Sonnet-medium, Haiku-medium, Opus-medium
    p1_vals: Dict[Tuple[str, str, str], Tuple[V, V, V]] = {}
    for (m, which, prule), v in p1["v"].items():
        p1_vals[(m, which, prule)] = (v["y"], v["lo"], v["hi"])
    differs = _p1_differs(p1_vals)
    axC.set_xlim(-0.6, 1.75)
    axC.set_xticks([0, 1])
    axC.set_xticklabels([f"three presets\n{p1['nb']['l14_to_l16'].printed} puzzles", f"one preset\n{p1['nb']['l14_only'].printed} puzzles"])
    acc_axis(axC, FIG05_APP_YLO, 100.0)                 # the limits first: the bars are decided from them
    tidy(axC)
    axC.tick_params(labelleft=False)
    p1_hidden: List[Tuple] = []     # Pilot 1 markers whose bar the shared short-bar rule leaves out (named in the caption)
    for gi, which in enumerate(("l14_to_l16", "l14_only")):
        for m, _ in LADDER:
            v = p1["v"][(m, which, rule)]
            x = gi + p1_dodge[m]
            st = style_for(v["model"], "medium")
            blo, bhi = (v["ex"].lo, v["ex"].hi) if v["ex"] is not None else (v["lo"], v["hi"])
            if bar_hidden(axC, v["model"], blo.val, bhi.val, y=v["y"].val):       # the marker covers the whole bar: it stands whole on the axis
                p1_hidden.append((f"Pilot 1's {STUDY1B_TAGS[m][0]} on {PRESET_WORDS[which]}", None, blo, bhi, v["y"]))   # on the axis: value printed
            else:
                forbid_sliver("FIG-05.appendix", axC, v["model"], blo.val, bhi.val, y=v["y"].val)     # no caption words for a bar only just longer than its marker
                if v["ex"] is not None:
                    exact_bar(axC, x, v["y"].val, blo.val, bhi.val, st["color"])
                else:
                    axC.errorbar([x], [v["y"].val], yerr=[[v["y"].val - v["lo"].val], [v["hi"].val - v["y"].val]], fmt="none",
                                 ecolor=st["color"], elinewidth=0.8, capsize=0, zorder=3)
            axC.plot([x], [v["y"].val], linestyle="none", marker=st["marker"], markersize=5, markerfacecolor=st["color"],
                     markeredgecolor=st["color"], markeredgewidth=0.6, zorder=4, clip_on=False)
    # the reference line names its model; the markers beside it are on other sets and rules (Edith's PR 34 review)
    y_qn = q["q24hi"].val + 3.0
    ref_texts = _fig05_qn(axC, 0.6, y_qn, c_ref, head="Haiku-medium", tail=", extrapolated", dy_pt=9.6)
    ref_texts.append(axC.annotate("(other sets and rules)", xy=(0.6, y_qn), xycoords="data", xytext=(0, 0), textcoords="offset points", fontsize=LAB,
                                  color=c_ref, ha="center", va="baseline"))
    _fig05_grid_gap(axC, ref_texts)
    _fig05_tag(axC, "C", f"Pilot 1‡, {q['q24c'].printed} steps, pooled")

    # row two: Study 1b's Haiku-max and Opus-medium on its own puzzle sets, on a zoomed accuracy axis (read first: the start is common)
    s1b = _fig05_read_s1b(S, points)
    ystart = _fig05_axis_start(s1b["lows"])
    ylo = float(ystart.raw)
    hidden_two: List[Tuple[str, Optional[Cell], V, V]] = []     # row two's points whose bar the shared short-bar rule leaves out
    points.append(rec("the Study 1b panels' lower end (display; read from the lowest plotted value)", "D chains", y=ystart))
    for pn, a, letter in (("chain", axD, "D"), ("pieces", axE, "E"), ("pooled", axF, "F")):
        a.set_xlim(*FIG05_XLIM)
        acc_axis(a, ylo, 100.0)                         # the limits first: the bars are drawn from them
        for key, model, effort in (("haiku-max", "haiku", "max"), ("opus-medium", "opus", "medium")):
            rows = s1b["rows"][(key, pn)]
            dx = -FIG05_DODGE["om"] if key == "haiku-max" else FIG05_DODGE["om"]
            flags = _fig05_series(a, [r["nf"] + dx for r in rows], [r["y"].val for r in rows], [r["lo"].val for r in rows],
                                  [r["hi"].val for r in rows], [r["ex"] for r in rows], model, effort, hollow=(pn == "pieces"))
            hidden_two += [(f"Study 1b's {key.capitalize()}, {PANEL_WORDS[pn]}", r["nc"],
                        *((r["ex"].lo, r["ex"].hi) if r["ex"] is not None else (r["lo"], r["hi"]))) for r, h in zip(rows, flags) if h]
        a.set_xticks([int(n) for n in s1b["lens"]["haiku-max"]])
        tidy(a)
        _fig0305_axis_break(a, min(v.val for v in s1b["lows"]))     # the zoomed axis: its cut is drawn, its start is said in the caption
        _fig05_tag(a, letter, "Study 1b, " + {"chain": "chains", "pieces": "pieces (hollow)", "pooled": "pooled"}[pn])   # the main version's panel B says "(hollow)" too
    axD.set_ylabel(ACC_LABEL)
    for a in (axE, axF):
        a.tick_params(labelleft=False)
    # one horizontal-axis title per row (row one: under the two length panels; panel C's own title is its length)
    fig.text((left + (2 * pw + gap) / 2) / W, (row1_y - 0.38) / H, "Steps in the puzzle", ha="center", va="top", fontsize=LAB, color=INK)
    fig.text((left + 2.5 * pw + 2 * gap) / W, (row1_y - 0.38) / H, f"{q['q24c'].printed} steps", ha="center", va="top", fontsize=LAB, color=INK)
    fig.text((left + (3 * pw + 2 * gap) / 2) / W, (row2_y - 0.38) / H, "Steps in the puzzle", ha="center", va="top", fontsize=LAB, color=INK)

    # one legend above row one (Karen's F13, Edith's section 8.5): its three medium-effort settings, swatches the plotted marks. Row two has
    # its own key (Edith's PR 34 review, MUST 5: the blue circles of row two are Haiku-max, not the legend's Haiku-medium; direct labels do not
    # fit in D and E, where the two series cross the panel from top to bottom between each other's bars): one line above row two, headed by
    # the row's tier, with two entries (Haiku-max has the colour and shape of Haiku-medium)
    def hl(model: str, effort: str, **kw: Any) -> Line2D:
        return Line2D([0], [0], color=color(model, effort), linewidth=kw.pop("lw", FIG05_LW), marker=kw.pop("marker", MODEL_MARKER[model]),
                      markersize=5, markeredgewidth=0.6, **kw)
    fig.legend(handles=[hl("haiku", "medium"), hl("sonnet", "medium"), hl("opus", "medium")], labels=[nm for _, nm in LADDER],
               loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), frameon=False, handlelength=2.0, columnspacing=2.0, handletextpad=0.6)
    key_y = (row2_y + row_h + 0.36) / H                  # the key's centre line: between row one's title and row two's panel titles
    head = fig.text(left / W, key_y, "Study 1b (other puzzle sets; descriptive):", ha="left", va="center", fontsize=LAB, color=INK)
    head_w = head.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi          # inches
    fig.legend(handles=[hl("haiku", "max"), hl("opus", "medium")], labels=["Haiku-max", "Opus-medium"], loc="center left", ncol=2,
               bbox_to_anchor=((left + head_w + 0.12) / W, key_y), frameon=False, handlelength=2.0, columnspacing=1.6, handletextpad=0.6,
               borderaxespad=0.0, borderpad=0.0)

    hidden_all = hidden + p1_hidden + hidden_two

    # ---- alt text
    firsts = sw["firsts"]
    n_first, n_last = ns[0], ns[-1]
    q24c = q["q24c"]
    hm_1b_lens = sorted(S.keys("s1b", "descriptive.length_curve.haiku-medium"), key=int)
    hm_1b_steps = _fig05_steps_list([key_cell("s1b", "descriptive.length_curve.haiku-medium", n)[0] for n in hm_1b_lens])
    p1fl = _fig05_p1_flag(S)
    alt = [L("Appendix version of the length curve: six panels in two rows, with a legend above row one and a key of its own above row two. Row"
             " one, the medium-effort settings (the legend names them), on accuracy axes that run from just below zero (so that a marker at zero stands clear of the horizontal axis) to the top of the scale: A and B show the"
             " length sweep under the original marking rule as locked in Lock 2, before Deviation 2, for chains and pooled over shapes (pieces are"
             " the same under both rules and are in the main version); C shows Pilot 1's markers at"), q24c,
           L("steps (exploratory‡), under the original rule, pooled over shapes, beside the q^N reference extended to"), q24c,
           L("steps. Row two shows Study 1b's Haiku-max and Opus-medium at the lengths that study ran, on that study's own puzzle sets (other"
             " puzzle sets; descriptive): D chains, E pieces (hollow markers) and F pooled over shapes, on accuracy axes titled Accuracy (%) that"
             " start at"), ystart,
           L(", not at zero, each with a break mark on the vertical axis just above the horizontal one. A key of its own above row two, headed"
             " Study 1b (other puzzle sets; descriptive), names Haiku-max, which has Haiku-medium's colour and shape, and Opus-medium."),
           L("Under the original rule Sonnet-medium's chain accuracy is"), P(sm_both[("chain", n_first)][0].cell), L("at"),
           firsts[("sm", "chain", n_first)][0], L("steps and"), P(sm_both[("chain", n_last)][0].cell), L("at"),
           firsts[("sm", "chain", n_last)][0], L("steps, against"), P(sm_both[("chain", n_first)][1].cell), L("and"),
           P(sm_both[("chain", n_last)][1].cell), L("under the official rule, which this version does not draw (the main version draws it,"
                                                    " with its bars). " + (
               "Haiku-medium's whole-answer values and q, and every length-sweep Opus-medium value, are" if om_all_same else
               "Haiku-medium's and Opus-medium's whole-answer values and Haiku-medium's q are") + " the same under both rules" +
               (";" if hm_ps_diff or hm_fc_diff else "."))]

    def at_steps(nl: List[str]) -> List[Cell]:
        return _fig05_steps_list([key_cell(R, "models.hm.by_n", n)[0] for n in nl])
    hm_diff: List[Cell] = []
    if hm_fc_diff:
        hm_diff += [L("Haiku-medium's chain format compliance differs at")] + at_steps(hm_fc_diff)
    if hm_ps_diff:
        hm_diff += [L(("and its" if hm_fc_diff else "Haiku-medium's") + " chain per-step rate, whose post hoc† values are in this figure's data file, at")] + at_steps(hm_ps_diff)
    if hm_diff:
        alt += hm_diff + [L("(the figure's data file lists both).")]
    alt += [L("Pilot 1's markers at"), q24c, L("steps are the dots in panel C, drawn under the original marking rule, one colour per model, for"
                                               " the three rule-set presets (left) and the one preset used later (right); the grey dashed line is the"
                                               " reference q^N at"), q24c,
            L("steps, with its band, labelled Haiku-medium q^N, extrapolated, with a second line (other sets and rules), beyond the sweep's"
              " lengths; Pilot 1 cannot judge that line (other presets,"
              " rules and puzzles, and an earlier time). Pilot 1's Opus-medium marker on the"
              " three presets, drawn under the original rule, is"), p1fl["original"]["flag"],
            L("on chains by the plan's format check (its format compliance is in the caption); it carries no mark in the panel.")]
    for (m, which), (off, org) in differs.items():
        alt += [L("Pilot 1's"), L(STUDY1B_TAGS[m][0]), L("marker on"), L(PRESET_WORDS[which]), L("is"), P(org[0].cell),
                L("under the original rule, as drawn, and"), P(off[0].cell), L("under the official rule, which is not drawn.")]
    alt += [L("The other Pilot 1 markers are the same under both rules.")]
    s_h = s1b["rows"][("haiku-max", "pooled")]
    s_o = s1b["rows"][("opus-medium", "pooled")]
    alt += [L("Study 1b, pooled over shapes: Haiku-max is at"), P(s_h[0]["y"].cell), L("at"), s_h[0]["nc"], L("steps and"), P(s_h[-1]["y"].cell),
            L("at"), s_h[-1]["nc"], L("steps, and Opus-medium at"), P(s_o[0]["y"].cell), L("and"), P(s_o[-1]["y"].cell), L("at the same lengths."),
            L("Study 1b's Haiku-medium at"), *hm_1b_steps, L("is not drawn in this figure; it is in TAB-12.")]
    exact_all = sw["exact"] + s1b["exact"] + p1["exact"]
    if exact_all:
        alt += [L("Bars drawn from exact 95% intervals, post hoc, where a bootstrap interval collapsed to a point:")]
        alt += _seq([_exact_where(words, nc, pn) for words, nc, pn, _ in exact_all], sep=";", last=".")
    alt += _fig05_hidden_alt(hidden_all)

    # ---- caption facts
    fmt, flag_fact = _fig05_format_fact(S, ns, sw, s1b)
    tier = [L("pre-registered descriptive: the length sweep, here under the original marking rule as locked in Lock 2 (the paper's official rule,"
              " Deviation 2, is in the main version); Study 1b's Haiku-max and Opus-medium: other puzzle sets; descriptive, compared by no"
              " test; the q^N line with its band, which panel C extends to"), q24c,
            L("steps, beyond the sweep's lengths (an extrapolation; see reference); " + P1_TIER + "‡: Pilot 1's markers at"), q24c,
            L("steps (Pilot 1 ran before Lock 2, on other sets and rules); the exact intervals drawn as bars (listed with the intervals) and the"
              " chains' own per-step values (listed under local) are post hoc†")]
    rule_cap = [L("every length-sweep value uses the original marking rule as locked in Lock 2, before Deviation 2; the official rule's"
                  " Sonnet-medium, the one series that differs on chains and so pooled, is not drawn in this version (the main version draws it"
                  " with its bars, and its values are in both_rules). Haiku-medium's and Opus-medium's whole-answer values, Haiku-medium's"
                  " q, and Sonnet-medium's values on pieces are the same under both rules" + (";" if hm_diff else "."))]
    if hm_diff:
        rule_cap += hm_diff + [L("(see format and local below).")]
    if differs:
        rule_cap += [L("Pilot 1's markers are the same under both rules, except")]
        for i, ((m, which), (off, org)) in enumerate(differs.items()):
            for v in (off, org):
                if collapsed(v[1], v[2]):
                    raise ValueError(f"FIG-05 appendix: Pilot 1 {m} {which} differs between the rules and an interval has no width: print"
                                     " free analysis 4's exact interval there")
            if i:
                rule_cap.append(L(";"))
            rule_cap += [L(STUDY1B_TAGS[m][0]), L("on"), L(PRESET_WORDS[which]), L("is"), P(off[0].cell), L("(95% interval"),
                         P(off[1].cell), L("to"), P(off[2].cell), L(") under the official rule and"), P(org[0].cell), L("(95% interval"),
                         P(org[1].cell), L("to"), P(org[2].cell), L(") under the original rule, which panel C draws, like the rest of its row; the"
                                                                    " official rule's value is not drawn")]
    else:
        rule_cap += [L("Pilot 1's markers are the same under both rules")]
    rule_cap += [L("; the q^N line, at the sweep's lengths and at"), q24c, L("steps, is the same under both rules")]
    # the chains' own local^N values (post hoc†): not drawn (Karen's F3), kept under both rules with their placeable counts
    local_org = _fig05_local(S, RULE_SRC["original"], ns, "original", points)
    local_off = _fig05_local(S, RULE_SRC["official"], ns, "official", points)
    both: List[Cell] = [L("Sonnet-medium's whole-answer accuracy under the original rule, then the official rule: on chains")]
    for pn, words in (("chain", None), ("pooled", "; pooled over shapes")):
        if words:
            both.append(L(words))
        both += _seq([[P(sm_both[(pn, n)][0].cell), L("and"), P(sm_both[(pn, n)][1].cell), L("at"), key_cell("curve", "models.sm.by_n", n)[0],
                       L("steps")] for n in ns])
    both.append(L("; on pieces the two rules give the same values"))
    exact_used = sw["exact"] + s1b["exact"] + p1["exact"]
    # Pilot 1's Opus-medium marker on the three presets is flagged on chains under the original rule, the rule panel C draws; the panel
    # does not mark it (Edith's section 8.7: a flag is named in the caption), and the recount's values travel with the sentence
    p1_flag_fact = [L("; in panel C, Pilot 1's Opus-medium marker on the three rule-set presets, drawn under the original rule, is"),
                    p1fl["original"]["flag"], L("by the plan's format check on chains: its chain format compliance is"),
                    P(p1fl["original"]["fc"]), L("under the original rule, where the plan flags format non-compliance"), p1fl["rule"],
                    L("(under the official rule its chain format compliance is"), P(p1fl["official"]["fc"]), L(", and it is"),
                    p1fl["official"]["flag"], L(")"),
                    L("; the panel carries no mark for it, and the same flag is stated in the paper's text on this marker")]
    if flag_fact[0].printed.startswith("no point is flagged"):
        flag_fact = [L("no length-sweep or Study 1b point is flagged by the format check")]
    # the panels, said once (Edith's proof 3, Figure S11: a caption that says "chains, pieces and pooled" for row one describes a pieces panel
    # that is not drawn, and panel E's hollow markers were explained nowhere): row one has no pieces panel, pieces being the same under both
    # rules (checked above) and drawn in the main version; hollow means pieces and nothing else
    panels_cap = [L("six panels in two rows. Row one is the length sweep under the original marking rule: A chains and B pooled over shapes"
                    " (there is no pieces panel in row one: pieces give the same values under both rules and are in the main version, FIG-05),"
                    " and C Pilot 1 at"), q24c,
                  L("steps, pooled over shapes. Row two is Study 1b's Haiku-max and Opus-medium on that study's own puzzle sets: D chains,"
                    " E pieces and F pooled over shapes. Hollow markers are pieces (panel E only) and filled markers are chains and pooled"
                    " (A, B, C, D and F)")]
    caption = {"tier": tier,
               "panels": panels_cap,
               "rule": rule_cap,
               "study": [L("the length sweep with Haiku-medium, Sonnet-medium and Opus-medium; Study 1b's Haiku-max and Opus-medium as a"
                           " separate series; Pilot 1 at"), q24c,
                         L("steps; Study 1b's Haiku-medium at"), *hm_1b_steps,
                         L("(other puzzle sets; descriptive) is not drawn in either version of this figure: it is in TAB-12")],
               "set": [L("the length sweep's ladder sets, one per length from 4 steps to 16 steps (other puzzles than Study 1); Study 1b's own sets"
                         " at each of its lengths; Pilot 1's own sets")],
               "n": _fig05_n_fact(S, R, ns, s1b, p1["nb"]),
               "format": fmt,
               "flagged": flag_fact + p1_flag_fact,
               "interval": _fig05_interval_fact(S, sw, exact_used, s1b, True),
               "both_rules": both,
               "local": [L("the chains' own per-step rate raised to the length (post hoc†; Haiku-medium, among placeable chain samples, conditional on"
                           " format; not drawn in this version) under the original rule:")] + local_org +
                        [L("; under the official rule, the main version's:")] + local_off,
               "reference": [L("the grey dashed line in panel C is q^N at"), q24c, L("steps:"), P(q["q24"].cell), L("with a 95% band from"),
                             P(q["q24lo"].cell), L("to"), P(q["q24hi"].cell), L("; it is Haiku-medium's per-piece rate q, from pieces pooled over the"
                             " lengths, raised to the number of steps N. The sweep's own lengths end at"), key_cell(R, "models.hm.by_n", n_last)[0],
                             L("steps, so the value at"), q24c, L("steps is an extrapolation beyond the lengths the sweep ran (labelled so in the"
                             " panel; pre-registered descriptive; the curve file's stamped label for it is"), joined(L("\u201c"), q["q24_label"], L("\u201d"), sep=""),
                             L("; drawn dashed here, because a dotted line means a margin). The line at the sweep's own lengths is in the main version"
                               " and is the same under both rules. The line is not fitted and is not a test. Pilot 1 used other rule presets, a"
                               " different rule mix, other puzzles and an earlier time, so its markers, drawn beside the line, cannot judge it")],
               "marks": [L("row one (its legend above the panels): the lines are the length sweep under the original rule (Sonnet-medium under"
                           " the official rule is not drawn here: the main version draws it, and its values are in both_rules), and the accuracy axes run"
                           " from just below zero (display only, so that a marker at zero stands clear of the horizontal axis; the tick at zero is"
                           " labelled) to the top of the scale; panel C: one dot per"
                           " model and preset group, under the original rule like the rest of the row (the official rule's Opus-medium value on the"
                           " three presets is in rule), with the left group's three presets and"), p1["nb"]["l14_to_l16"],
                           L("puzzles and the right group's one preset and"), p1["nb"]["l14_only"],
                           L("puzzles written under it")] + _fig05_hidden_words(hidden_all, "; ") + [
                           L("; row two (a key of its own above the row, headed Study 1b (other puzzle sets;"
                             " descriptive), names the series): Study 1b's Haiku-max, which has Haiku-medium's"
                             " colour and shape, and Opus-medium (E pieces, hollow markers; filled markers are chains and pooled); in row one Sonnet-medium"
                             " and Opus-medium, and in row two Haiku-max and Opus-medium, are shifted a little to the left and to the right of each"
                             " length (display only) to keep the markers and bars apart, while Haiku-medium stands at its true length; the Study 1b"
                             " panels' accuracy axes are titled Accuracy (%) and start at"), ystart, L(", not at zero, each with a break mark just above the"
                             " horizontal axis")],
               "price": [L("not applicable (no cost on this figure)")]}
    return FigureOut(fig, points, tight(alt), tight_caption(caption))


def _exact_where(words: str, nc: Optional[Cell], pn: str) -> List[Cell]:
    """Where FIG-05 draws an exact bar: 'length-sweep Opus-medium at 6 steps, pooled over shapes' (a Pilot 1 marker has no step cell:
    'Pilot 1 Opus-medium on the one preset used later, pooled over shapes')."""
    return [L(words)] + ([L("at"), nc, L("steps,")] if nc is not None else [L(",")]) + [L(PANEL_WORDS[pn])]


def _p1_differs(p1: Dict[Tuple[str, str, str], Tuple[V, V, V]]) -> Dict[Tuple[str, str], Tuple[Tuple[V, V, V], Tuple[V, V, V]]]:
    """Pilot 1 markers whose stamped mean or interval differs between the rules: (model tag, preset group) -> (official, original)."""
    out = {}
    for (m, which, prule), v in p1.items():
        if prule != "official" or (m, which, "original") not in p1:
            continue
        o = p1[(m, which, "original")]
        if any(a.ref.value != b.ref.value for a, b in zip(v, o)):
            out[(m, which)] = (v, o)
    return out


# ================================================================ FIG-06

# Redrawn to the house style (Karen's page 3, recipe 1; Edith's §8): one message, drawn: a single Haiku-max sample sits as high as
# Opus-medium (the dashed line) and far above every Haiku-medium design, at a fraction of Opus-medium's cost. Seven points a panel, one
# shape per model (circle for Haiku, diamond for Opus), the designs told apart by direct labels; no legend, hollow mark or ring. Left out
# of the figure, and in the tables: Study 1's other single samples (Haiku with thinking off, Haiku-low, Sonnet-low and -medium, Opus-low)
# and the Haiku-medium vote at Sonnet-medium's cost (TAB-04, TAB-02, TAB-05), the Haiku-max vote (FIG-01, TAB-05), and the top-up designs'
# own comparators (TAB-14).
FIG06_H = 2.5
FIG06_X = (0.0004, 0.12)        # the cost range (layout only): the costliest point is $0.0481, so no empty third on the right
TOPUP_FLAGS = "format_refusals_truncations_missing.item_17_flags"
# label placement by shape and point id: (where, dx points, dy points, ha); where is r (right of the marker), l (left), a (above the bar), b (below
# the bar); layout only. A top-up design's label carries a second line, "(top-up)", in grey, on the side of the label away from its point
FIG06_LABELS: Dict[Tuple[str, str], Tuple[str, float, float, str]] = {
    ("1x6", "hm"): ("b", 0, 0, "center"), ("1x6", "step"): ("a", 0, 0, "center"), ("1x6", "team"): ("b", 0, 0, "center"),   # neighbours 15 pt apart: two-line labels
    ("1x6", "pick"): ("r", 0, 0, "left"), ("1x6", "vote"): ("b", 0, 0, "center"), ("1x6", "hx"): ("b", 0, -1, "center"),
    ("1x6", "om"): ("b", 0, 0, "center"),
    ("6x1", "hm"): ("b", 0, 0, "center"), ("6x1", "step"): ("b", -4, 0, "left"), ("6x1", "team"): ("l", 0, 3, "right"),
    ("6x1", "pick"): ("r", 0, 0, "left"), ("6x1", "vote"): ("b", 0, 0, "center"), ("6x1", "hx"): ("l", 0, 0, "right"),   # left of its marker: below it the label stood just above the Haiku team's bar and read as the team's (Edith's PR 34 round 2)
    ("6x1", "om"): ("b", 0, 0, "center"),
}
FIG06_TOP_UP = "(top-up)"
FIG06_NAME = {"hm": "the Haiku-medium sample", "vote": "the cost-matched vote", "step": "step voting", "team": "the Haiku team",
              "pick": "the picker", "hx": "the Haiku-max sample", "om": "Opus-medium"}


def tests_using(arm: str, shape: str, vote_kind: Optional[str] = None) -> List[str]:
    """Study 1's tests that use this arm at this shape (the design in paper_out_names.STUDY1_TESTS, copied from five_tests.py): a single
    call as comparator or as a single-call challenger (vote_kind None), or the Haiku-medium vote at the k kind 'O' / 'S'. The one-sample
    Haiku-medium arm is used by no test: Tests 1-3 use its votes."""
    out = []
    for name, ch, cmp_, sh, kk in STUDY1_TESTS.values():
        if sh != shape:
            continue
        if vote_kind is None and (cmp_ == arm or (ch == arm and kk is None)):
            out.append(name)
        elif vote_kind is not None and ch == arm and kk == vote_kind:
            out.append(name)
    return out


def _fig06_tests(names: Sequence[str]) -> str:
    """'Tests 1, 2 and 4' (or 'Test 4') from test names such as 'Test 1'; an empty list stops the build, since the caption names the tests."""
    nums = sorted({n.split()[1] for n in names})
    if not nums:
        raise ValueError("FIG-06: a point the caption says a test uses is used by no test: reword the tier fact")
    return ("Tests " + ", ".join(nums[:-1]) + " and " + nums[-1]) if len(nums) > 1 else "Test " + nums[0]


def _fig06_format(S: Store, arm: str, shape: str) -> Optional[Tuple[Cell, Ref]]:
    """Study 1's format compliance of an arm at a shape in % with one decimal (the paper's rounding for a percentage; `s1_format` keeps the
    two decimals of the Study 1 tables) and its format flag; None where item 24 stamps none."""
    key = join_key(*T24.split("."), f"{arm} {shape}", "format_compliance", "format_compliance")
    if not S.has("main", key):
        return None
    return pct(S.ref("main", key), dp=1), S.ref("main", join_key("reporting", "group_b", "item_17", "flags", f"{arm} {shape}", "fires"))


def _fig06_label(ax, x: float, lo: float, y: float, hi: float, text: str, where: str, dx: float, dy: float, ha: str, color: str = INK,
                 suffix: Optional[str] = None) -> None:
    """A direct label 8 pt beside its point: right or left of the marker, or above the top or below the bottom of its 95% bar. A suffix
    (a top-up design's "(top-up)") is a second line in grey, beyond the label on the side away from the point (below it for a label
    beside the marker); the label's height is measured, so that it follows the label's own line count."""
    xy, off, va = {"r": ((x, y), (7 + dx, dy), "center"), "l": ((x, y), (-7 + dx, dy), "center"),
                   "a": ((x, hi), (dx, 3 + dy), "bottom"), "b": ((x, lo), (dx, -3 + dy), "top")}[where]
    t = ax.annotate(text, xy, xytext=off, textcoords="offset points", fontsize=LAB, color=color, ha=ha, va=va, zorder=7,
                    annotation_clip=False, linespacing=1.0)
    if suffix:
        fig = ax.figure
        h_pt = t.get_window_extent(fig.canvas.get_renderer()).height * 72.0 / fig.dpi
        gap = 1.0
        off2, va2 = {"a": ((off[0], off[1] + h_pt + gap), "bottom"), "b": ((off[0], off[1] - h_pt - gap), "top"),
                     "r": ((off[0], off[1] - h_pt / 2.0 - gap), "top"), "l": ((off[0], off[1] - h_pt / 2.0 - gap), "top")}[where]
        ax.annotate(suffix, xy, xytext=off2, textcoords="offset points", fontsize=LAB, color=style.INK_2, ha=ha, va=va2, zorder=7,
                    annotation_clip=False, linespacing=1.0)


@output("FIG-06")
@main_text
@plain_ids(main=True)
def fig_06(S: Store) -> FigureOut:
    """Where each design landed at 6 steps. Main-text names (Edith's settlement E-06, P-2): step voting (on chains, Test 4; on pieces, its
    counterpart from the top-up run), the Haiku team and the picker, with no keep-list codes."""
    t24 = "reporting.group_b.item_24.table"
    five = set(S.keys("main", "counts.five_test_arms"))
    W, H = COLW, FIG06_H
    fig = plt.figure(figsize=(W, H))

    def box(l: float, b: float, w: float, h: float) -> List[float]:
        return [l / W, b / H, w / W, h / H]
    ax_c = fig.add_axes(box(0.62, 0.52, 2.74, 1.75))
    ax_p = fig.add_axes(box(3.62, 0.52, 2.74, 1.75), sharey=ax_c)
    axes = {"1x6": ax_c, "6x1": ax_p}
    points: List[Dict[str, Any]] = []
    status = text_of(S.ref("topup", "same_model_check.flag.status"))
    got: Dict[Tuple[str, str], Tuple[V, V, V, V]] = {}
    c_hm, c_hx, c_om = color("haiku", "medium"), color("haiku", "max"), color("opus", "medium")
    # both panels' limits are set before any mark is drawn: the test for a bar shorter than its marker depends on them
    for ax in axes.values():
        cost_axis(ax, *FIG06_X, [0.001, 0.003, 0.01, 0.03, 0.1])
        acc_axis(ax, 0.0, 100.0)
    short_pts: Dict[str, List[str]] = {}         # point id -> the shapes on which its 95% bar is shorter than the marker (not drawn)
    topup_pts: Dict[str, List[str]] = {}         # point id -> the shapes on which it comes from the top-up run
    fmt_singles: Dict[str, List[Tuple[Cell, Ref, str]]] = {}
    e2_fmt: List[List[Cell]] = []
    flagged_drawn: List[List[Cell]] = []
    vote_k: Dict[str, Cell] = {}
    if set(S.keys("topup", TOPUP_FLAGS)) != {"e2 1x6", "e2 6x1", "same-model-check 1x6", "same-model-check 6x1"}:
        raise ValueError("FIG-06: the top-up file's format checks cover other arms now: print them")

    def put(shape: str, pid: str, name: str, model: str, effort: str, y: V, lo: V, hi: V, cost: V, tier: str, label: str,
            text_color: str = INK, k: Optional[Cell] = None, fmt: Optional[Dict[str, Cell]] = None, note: Optional[str] = None,
            topup: bool = False) -> None:
        """One point with its 95% bar (an interval with no width stops the build) and its direct label; a top-up design (read from the
        top-up run, which came after the main run) has "(top-up)" under its label."""
        has_width(f"FIG-06: {name} on {SHAPE_WORD[shape]}", lo, hi)
        where, dx, dy, ha = FIG06_LABELS[(shape, pid)]
        ax = axes[shape]
        short = _fig0406_bar_short(ax, model, y.val, lo.val, hi.val)          # the bar is shorter than the marker: not drawn, and the caption names it
        if short:
            short_pts.setdefault(pid, []).append(SHAPE_WORD[shape])
            note = "; ".join(x for x in (note, "its 95% bar is shorter than its marker, and neither end reaches a printed point past the marker’s edge, so it is not drawn (its ends are lo and hi)") if x)
        if mark(ax, cost.val, y.val, lo.val, hi.val, model, effort, size=5.0, zorder=4) != short:
            raise ValueError("FIG-06: the marker and the caption disagree on which bars are not drawn")
        ax.lines[-1].set_clip_on(False)
        _fig06_label(ax, cost.val, lo.val, y.val, hi.val, label, where, dx, dy, ha, text_color, FIG06_TOP_UP if topup else None)
        if topup:
            topup_pts.setdefault(pid, []).append(SHAPE_WORD[shape])
        points.append(rec(f"{name}, {SHAPE_WORD[shape]}", SHAPE_WORD[shape], x=cost, y=y, lo=lo, hi=hi, tier=tier, note=note, k=k, **(fmt or {})))
        got[(shape, pid)] = (y, lo, hi, cost)

    def single(shape: str, arm: str) -> Tuple[V, V, V, V, Cell, Ref]:
        """A Study 1 single-call row: accuracy with its 95% interval, cost per puzzle, format compliance and its flag."""
        row = f"{t24}.{arm} {shape}"
        iv = row + (".accuracy_interval" if S.has("main", row + ".accuracy_interval") else ".accuracy_cp95")
        if iv.endswith(".accuracy_interval"):
            y = pv(S, "main", row + ".accuracy_interval.mean", prop=False)
            lo, hi = ci(S, "main", row + ".accuracy_interval.ci95", prop=False)
        else:                               # an exact interval as stamped: never of no width (checked in `put`)
            y = pv(S, "main", row + ".accuracy_cp95.accuracy", prop=False)
            lo, hi = ci(S, "main", row + ".accuracy_cp95.cp95", prop=False)
        cost = usd_val(S, "main", row + ".cost_per_puzzle.mean")
        fc = _fig06_format(S, arm, shape)
        if fc is None:
            raise ValueError(f"FIG-06: item 24 stamps no format compliance for {arm} {shape}")
        fmt_singles.setdefault(arm, []).append((fc[0], fc[1], SHAPE_WORD[shape]))
        if fc[1].value is True:
            flagged_drawn.append([L(f"{STUDY1_ARMS[arm][0]} on {SHAPE_WORD[shape]}"), joined(L("("), P(fc[0]), L(")"), sep="")])
        return y, lo, hi, cost, fc[0], fc[1]

    def fmt_rec(fc: Cell, fl: Ref) -> Dict[str, Cell]:
        return {"format_compliance": fc, "format_flag": text_of(fl, {True: "flagged", False: "not flagged"})}

    for shape, ax in axes.items():
        sw = SHAPE_WORD[shape]
        # one Haiku-medium sample (Study 1; used in no test: Tests 1-3 use its votes)
        y, lo, hi, cost, fcell, fl = single(shape, "haiku-med")
        tier = ("pre-specified descriptive: this single sample is not tested; the tests use its votes"
                if f"haiku-med {shape}" in five else "exploratory setting")
        put(shape, "hm", "Haiku-medium, one sample", "haiku", "medium", y, lo, hi, cost, tier, "Haiku-medium,\none sample",
            fmt=fmt_rec(fcell, fl))
        # the Haiku-medium vote at Opus-medium's cost (Test 1 on pieces, Test 2 on chains)
        vb = f"{t24}.haiku-med {shape}.vote_at_own_k.k_O"
        y = pv(S, "main", vb + ".mean", prop=False)
        lo, hi = ci(S, "main", vb + ".ci95", prop=False)
        kc, _ = kval(S, "main", vb + ".k")
        vote_k[shape] = kc
        cost = usd_val(S, "main", vb + ".cost_per_puzzle.mean")
        used = tests_using("haiku-med", shape, "O")
        put(shape, "vote", "Haiku-medium vote, cost-matched to Opus-medium", "haiku", "medium", y, lo, hi, cost,
            "Haiku-medium vote at the Opus-medium cost-matched k; " + ("used in " + ", ".join(used) if used else "exploratory"),
            f"cost-matched\nvote, $k = {kc.printed}$", k=kc)
        # step voting: on chains (Study 1, Test 4); on pieces (the top-up run: the pieces counterpart of Test 4)
        if shape == "1x6":
            row = f"{t24}.e3 1x6"
            y = pv(S, "main", row + ".accuracy_interval.mean", prop=False)
            lo, hi = ci(S, "main", row + ".accuracy_interval.ci95", prop=False)
            cost = usd_val(S, "main", row + ".cost_per_puzzle.mean")
            used = tests_using("e3", shape)
            put(shape, "step", "step voting", "haiku", "medium", y, lo, hi, cost, "used in " + ", ".join(used) if used else "exploratory",
                "step\nvoting")
        else:
            y = pv(S, "topup", "accuracy.c13.6x1.mean", prop=False)
            lo, hi = ci(S, "topup", "accuracy.c13.6x1.ci95", prop=False)
            cost = usd_val(S, "topup", "costs.per_puzzle.c13.6x1.mean")
            put(shape, "step", "step voting", "haiku", "medium", y, lo, hi, cost,
                "the pieces counterpart of Test 4: unadjusted, exploratory, outside the pre-registered family; top-up run, after the main run",
                "step voting‡", note="the drift check between runs: " + status.printed, topup=True)
        # top-up: the Haiku team, and the picker with its samples
        y = pv(S, "topup", f"accuracy.e2.{shape}.mean", prop=False)
        lo, hi = ci(S, "topup", f"accuracy.e2.{shape}.ci95", prop=False)
        cost = usd_val(S, "topup", f"costs.per_puzzle.e2.{shape}.mean")
        e2f = join_key(*TOPUP_FLAGS.split("."), f"e2 {shape}")
        e2_ok, e2_ans, e2_fl = (integer(S.ref("topup", e2f + ".format_ok")), integer(S.ref("topup", e2f + ".answered")),
                                S.ref("topup", e2f + ".fires"))
        e2_fmt.append([e2_ok, L("of"), e2_ans, L("on " + sw)] + ([text_of(e2_fl, {True: "(flagged)"})] if e2_fl.value is True else []))
        if e2_fl.value is True:
            flagged_drawn.append([L("the Haiku team on " + sw), joined(L("("), e2_ok, L("of"), e2_ans, L(")"), sep=" ")])
        put(shape, "team", "the Haiku team", "haiku", "medium", y, lo, hi, cost, "exploratory, top-up run, after the main run",
            "Haiku\nteam‡" if shape == "1x6" else "Haiku team‡",
            fmt={"answers_in_format": e2_ok, "answers": e2_ans, "format_flag": text_of(e2_fl, {True: "flagged", False: "not flagged"})},
            topup=True)
        y = pv(S, "topup", f"accuracy.h-pick8.{shape}.mean", prop=False)
        lo, hi = ci(S, "topup", f"accuracy.h-pick8.{shape}.ci95", prop=False)
        cost = usd_val(S, "topup", f"costs.per_puzzle.h-pick8-total.{shape}.mean")
        put(shape, "pick", "the picker with its samples", "haiku", "medium", y, lo, hi, cost, "exploratory, top-up run, after the main run", "picker‡", topup=True)
        # the finding: one Haiku-max sample (exploratory arm)
        y, lo, hi, cost, fcell, fl = single(shape, "haiku-max")
        put(shape, "hx", "Haiku-max, one sample", "haiku", "max", y, lo, hi, cost, "exploratory setting",
            "Haiku-max‡",                                          # neither panel prints a percentage (job K row 6, option 2; Edith's O-7:
            text_color=style.MODEL_TEXT["haiku"], fmt=fmt_rec(fcell, fl))                # the values are in Table 12)
        # the comparator: Opus-medium, a dashed reference line and its point
        y, lo, hi, cost, fcell, fl = single(shape, "opus-med")
        used = tests_using("opus-med", shape)
        ax.axhline(y.val, color=style.MODEL_BASE["opus"], linestyle=(0, (4, 2.5)), linewidth=1.0, zorder=1, clip_on=False)
        put(shape, "om", "Opus-medium", "opus", "medium", y, lo, hi, cost, "used in " + ", ".join(used) if used else "descriptive",
            "Opus-medium", text_color=style.MODEL_TEXT["opus"], fmt=fmt_rec(fcell, fl))

    for shape, ax in axes.items():
        tidy(ax, ylabel=ACC_LABEL if shape == "1x6" else None)
        _fig0406_tag(ax, "A" if shape == "1x6" else "B", "Chains" if shape == "1x6" else "Pieces")
    plt.setp(ax_p.get_yticklabels(), visible=False)
    # one cost-axis title under both panels, at the ordinary label distance: the first panel's own title, centred between the two
    ax_c.set_xlabel(COST_PUZZLE)
    ax_c.xaxis.label.set_x(((0.62 + 6.36) / 2 - 0.62) / 2.74)

    def g(shape, pid):
        return got[(shape, pid)]
    # the alt text says every Haiku-medium design sits far below Opus-medium, that one Haiku-max sample sits near it and far above every
    # Haiku-medium design, at a fraction of its cost: refuse a data change that breaks that (more than 20 points, within 6 points, under a fifth)
    for sh in axes:
        best_hm = max(g(sh, k)[0].val for k in ("hm", "vote", "step", "team", "pick"))
        o_y, x_y, o_c, x_c = g(sh, "om")[0].val, g(sh, "hx")[0].val, g(sh, "om")[3].val, g(sh, "hx")[3].val
        if o_y - best_hm <= 20 or x_y - best_hm <= 20 or abs(o_y - x_y) > 6 or x_c >= 0.2 * o_c:
            raise ValueError(f"FIG-06 ({SHAPE_WORD[sh]}): the alt text says every Haiku-medium design is over 20 points below Opus-medium, one Haiku-max"
                             " sample is within 6 points of it and over 20 points above every Haiku-medium design, at under a fifth of its cost: reword")
    alt = [L("Two panels, chains on the left and pieces on the right, of whole-answer accuracy against list cost per puzzle on a log axis at 6 steps, one"
             " point per design, each labelled with its design. A dashed line marks Opus-medium's accuracy. Every Haiku-medium design sits far below it; one Haiku-max sample sits near it, far above"
             " every Haiku-medium design, at a fraction of Opus-medium's cost."),
           L("On chains, one Opus-medium answer is at"), P(g("1x6", "om")[0].cell), L("for"), g("1x6", "om")[3].cell, L("US dollars; the Haiku-medium vote, cost-matched"
           " to Opus-medium with k ="), vote_k["1x6"], L(", is at"), P(g("1x6", "vote")[0].cell), L("for"), g("1x6", "vote")[3].cell,
           L("dollars; one Haiku-max sample is at"), P(g("1x6", "hx")[0].cell), L("for"), g("1x6", "hx")[3].cell,
           L("dollars; step voting is at"), P(g("1x6", "step")[0].cell), L("for"), g("1x6", "step")[3].cell, L("dollars; the Haiku team is at"),
           P(g("1x6", "team")[0].cell), L("for"), g("1x6", "team")[3].cell, L("dollars; the picker is at"), P(g("1x6", "pick")[0].cell), L("for"),
           g("1x6", "pick")[3].cell, L("dollars; one Haiku-medium sample is at"), P(g("1x6", "hm")[0].cell), L("for"), g("1x6", "hm")[3].cell, L("dollars."),
           L("On pieces, one Opus-medium answer is at"), P(g("6x1", "om")[0].cell), L("for"), g("6x1", "om")[3].cell,
           L("dollars; the Haiku-medium vote, cost-matched to Opus-medium with k ="), vote_k["6x1"], L(", is at"), P(g("6x1", "vote")[0].cell), L("for"),
           g("6x1", "vote")[3].cell, L("dollars; one Haiku-max sample is at"), P(g("6x1", "hx")[0].cell), L("for"), g("6x1", "hx")[3].cell,
           L("dollars; step voting, from the top-up run, is at"), P(g("6x1", "step")[0].cell), L("for"), g("6x1", "step")[3].cell,
           L("dollars, with the drift check between runs"), status,
           L("; the Haiku team is at"), P(g("6x1", "team")[0].cell), L("for"), g("6x1", "team")[3].cell, L("dollars; the picker is at"),
           P(g("6x1", "pick")[0].cell), L("for"), g("6x1", "pick")[3].cell, L("dollars; one Haiku-medium sample is at"), P(g("6x1", "hm")[0].cell),
           L("for"), g("6x1", "hm")[3].cell, L("dollars."),
           L("A double dagger marks the exploratory points: Haiku-max, the Haiku team, the picker and step voting on pieces. The labels of the"
             " Haiku team and the picker on both shapes, and of step voting on pieces, also say top-up, the run that came after the main run.")]

    singles = ("haiku-med", "haiku-max", "opus-med")
    s1_flags = _fig0406_study1_flags(S, drawn=singles)       # Study 1's flagged settings that this figure leaves to TAB-04: not lost with their points
    om_tests = _fig06_tests([t for sh in axes for t in tests_using("opus-med", sh)])
    vote_tests = _fig06_tests([t for sh in axes for t in tests_using("haiku-med", sh, "O")])
    step_tests = _fig06_tests(tests_using("e3", "1x6"))
    tier = [L("descriptive and exploratory, no frontier or fitted line. Values used in Study 1's tests: Opus-medium (the comparator in " + om_tests + "), the"
              " Haiku-medium vote cost-matched to Opus-medium (" + vote_tests + ") and step voting on chains (" + step_tests + "); the Haiku-medium sample is"
              " pre-specified descriptive, and its votes are what the tests use. Exploratory‡: one Haiku-max sample, the Haiku team, the picker"
              " and step voting on pieces (the pieces counterpart of Test 4: unadjusted, outside the pre-registered family; the drift check between runs:"), status,
            L("); the Haiku team, the picker and step voting on pieces ran in the top-up run, after the main run. Not drawn: Study 1's other single"
              " samples (in TAB-04" + ("; the format check flags" if s1_flags else ""))] + s1_flags + [
            L((", and its rule is in TAB-07" if s1_flags else "") + "), Tests 3 and 5 with their comparators (in TAB-02; their"
              " pieces counterparts and the Haiku-max vote are in TAB-05; the Haiku-max vote's exact 95% interval, post hoc†, is in TAB-26), and the"
              " top-up run's comparators (in TAB-14)")]
    fc = "format_compliance.tries"
    for arm in singles:
        same_both_shapes(S, "main", f"{t24}.{arm} 1x6.{fc}")
        same_both_shapes(S, "main", f"{t24}.{arm} 1x6.base_puzzles")
    if len({S.get("main", f"{t24}.{a} 1x6.base_puzzles") for a in singles + ("e3",)}) != 1:
        raise ValueError("Study 1 arms differ in puzzles: print each")
    ncap = ([L("puzzles per shape:"), integer(S.ref("main", f"{t24}.haiku-med 1x6.base_puzzles")),
             L("(every design); samples per shape (the same on chains and pieces):")] +
            _seq([[L(STUDY1_ARMS[a][0]), integer(S.ref("main", f"{t24}.{a} 1x6.{fc}"))] for a in singles]) +
            [L("; the Haiku-medium votes are drawn from the Haiku-medium samples; step voting on chains:"),
             integer(S.ref("main", "reporting.group_b.item_19.arms['e3:1x6'].calls")), L("calls. Top-up run, over both shapes: the Haiku team"),
             integer(S.ref("topup", "completeness.arms.e2.final")), L("calls on"), integer(S.ref("topup", "completeness.arms.e2.puzzles")),
             L("puzzle runs; the picker"), integer(S.ref("topup", "completeness.arms.h_pick8.final")),
             L("calls (it reads the main run's Haiku-medium samples); step voting on pieces"), integer(S.ref("topup", "completeness.arms.c13.final")),
             L("calls")])
    fmt_cells, any_flag = fmt_list([(STUDY1_ARMS[a][0], fmt_singles[a]) for a in singles])
    fmt6 = ([L("format compliance, the share of samples in the required answer format (TAB-04 prints it to two decimals, this figure to one), chains then pieces:")] + fmt_cells +
            [L("; the votes carry the format compliance of the Haiku-medium samples they are drawn from; Study 1's file stamps none for step voting."
               " Top-up run, answers in the required format (its format check): the Haiku team")] + _seq(e2_fmt, sep="and") +
            [L("; the top-up file stamps none for the picker or step voting on pieces; the format check flags only the values marked flagged,"
               " which are named here and not marked in the plot" if (any_flag or flagged_drawn) else
               "; the top-up file stamps none for the picker or step voting on pieces; the format check flags none of the points drawn")])
    icap = [L("vertical bars are 95% intervals: cluster bootstrap for the Haiku-medium and Haiku-max samples, the votes, step voting and the top-up designs; exact"
              " (Clopper\u2013Pearson) for the one-sample Opus-medium answers")]
    short_bits = [FIG06_NAME[pid] + " on " + " and ".join(short_pts[pid]) for pid in FIG06_NAME if pid in short_pts]
    topup_bits = [FIG06_NAME[pid] + " on " + " and ".join(topup_pts[pid]) for pid in FIG06_NAME if pid in topup_pts]
    # one test for every figure (`bar_hidden`, per point): a bar whose whole span is shorter than its marker, and neither end of which reaches 1 pt
    # past the marker's edge, is not drawn, and only those (a one-sided bar at 100% that is short but whose lower arm reaches past the marker is
    # drawn: FIG-06's Opus-medium on pieces); the words say both conditions, as FIG-04's and FIG-05.appendix's do (Edith's PR #40 review round)
    note = [L("the dashed line is Opus-medium's accuracy in each panel; every point except Haiku-max and Opus-medium is a Haiku-medium design;"
              " a double dagger marks an exploratory point; the grey word top-up under a label marks a design from the top-up run, which came"
              " after the main run (" + "; ".join(topup_bits) + "); the labels name each design,"
              " and the cost-matched vote's k is the vote size; the picker's cost includes the main run's Haiku-medium samples that it reads"
              + ("; 95% bars shorter than their markers, with neither end reaching a printed point past the marker’s edge, are not drawn ("
                 + "; ".join(short_bits) + "), and their interval ends are in this figure's data file" if short_bits else ""))]
    caption = {"tier": tier,
               "study": [L("Study 1, main run, 6 steps, and the top-up run, which came after the main run")],
               "set": [L("the Study 1 puzzle set at 6 steps, which the top-up run also used: each puzzle as a chain and as pieces")],
               "n": ncap,
               "format": fmt6,
               "interval": icap,
               "price": price_study1(S, " per puzzle"),
               "note": note}
    return FigureOut(fig, points, tight(alt), tight_caption(caption))


# ================================================================ FIG-07

# Batch (h), as revised for Edith's chart review of PR #34 (2026-10-18; the SHOULDs of FIG-07): Karen's recipe 7 (horizontal stacked
# bars, the share printed outside the bar end in dark text, the token medians printed as stamped (`stamped_count`: '600', '1,737', a half
# keeps its '.5'; Edith's PR #40 review, S1), narrow column headers, the rows the caption is about marked by a bracket and four words). The bars of the bracketed rows (the settings for which the API reports no thinking) are drawn in
# the palette's context grey, not in the model's colour: their whole bar is the estimate's bias, and a model colour would read as thinking.
# A short dark tick on every other bar marks the thinking share by the API's own count (free analysis 10, post hoc), so the figure shows
# the estimate's overstatement row by row (the bracketed rows' API share is zero: the bracket says so). Chains over pieces, one x axis scale,
# one row order in both panels (a setting sits in the same place in each; chains-only Step voting comes last). The settings for which the
# API reports no thinking tokens are read per panel from free analysis 10 (a setting is marked exactly when its mean thinking tokens
# there is zero: checked below); the order puts every setting that is zero on either shape first, so the bracket spans the first rows
# of each panel. A setting that Study 1 ran as exploratory (read as TAB-04 reads it, `s1_role`) carries a double dagger on its row
# label, and a format flag that fires (item 17, through `s1_format`) is named in the caption facts.
FIG07_ARMS = ("haiku-thinking-off", "sonnet-low", "sonnet-med", "haiku-low", "haiku-med", "haiku-max", "opus-low", "opus-med", "e3")
FIG07_REST = "#E6E6E6"                                      # the rest of list cost: the palette's light grey (the grid grey)
FIG07_BRACKET_WORDS = "API reports\nno thinking†"      # four words and the dagger (set on two lines): the API's counts are post hoc (free analysis 10)
FIG07_EXPLORATORY = "‡"                                     # beside the row label of a setting Study 1 ran as exploratory
FIG07_SHARE_PT = 5.0            # the shares print (and the first column header starts) this many points right of the bars' end
FIG07_HDR_GAP = 19.0            # points between the share column and the tokens column (whose header is right-aligned over its numbers)
FIG07_DESIGNS = ("e3",)         # plotted rows that are designs (several calls per answer), not single-sample settings: D-161 (3)
FIG07_SHARE_HEAD = ("Est.", "share")                              # the column headers, one entry per line (narrow: over their numbers)
FIG07_TOKEN_HEAD = ("Median est.", "thinking", "tokens")
FIG07_BIAS_WORDS = "estimate’s bias"                               # the direct label on the grey bar of the first (bracketed) row of each panel
FIG07_TICK_WORDS = "tick: thinking share by the API’s own count†"  # the one key of the ticks (the dagger: post hoc, free analysis 10)
FIG07_TICK_KEY_PT = 62.0        # the tick key starts this many points right of the axes' left edge (right of the panel tag and its title)
FIG07_ROLE_WORDS = {"confirmatory": "confirmatory", "five-test arm": "five-test setting, in no test at this shape", "exploratory": "exploratory"}


def fig07_name(arm: str) -> str:
    """The setting's display name in the paper's words: step voting in plain words (no keep-list code, as in FIG-01 and FIG-06) and
    'Haiku, thinking off' (the paper's one name for that setting, from `STUDY1_ARMS`: never 'Haiku with thinking off', Edith's D-168, page 104)."""
    if arm == "e3":
        return "Step voting"
    return STUDY1_ARMS[arm][0]


def _fig07_kind(arm: str) -> str:
    """'design' for a plotted row that takes several calls per answer (Step voting), 'setting' for a single-sample row (D-161 (3))."""
    return "design" if arm in FIG07_DESIGNS else "setting"


def _fig07_text_width(text: str, W: float) -> float:
    """The width in points of a text set at the figure's label size (measured on a scratch figure; the longest line of several)."""
    tmp = plt.figure(figsize=(W, 1.0))
    try:
        r = tmp.canvas.get_renderer()
        return max(tmp.text(0, 0, line, fontsize=LAB).get_window_extent(r).width * 72.0 / tmp.dpi for line in text.split("\n"))
    finally:
        plt.close(tmp)


def _fig07_label(arm: str, role: str) -> str:
    """A row's label: the setting's name, with a double dagger where Study 1 ran it as exploratory."""
    return fig07_name(arm) + (FIG07_EXPLORATORY if role == "exploratory" else "")


def _fig07_tag(ax, letter: str, title: str) -> None:
    """The panel letter (the shared bold letter) and a title beside it (Karen's F16; as FIG-01, FIG-02 and FIG-05 set theirs)."""
    panel_tag(ax, letter)
    ax.annotate(title, xy=(0, 1.03), xycoords="axes fraction", xytext=(12, 0), textcoords="offset points", fontsize=LAB, color=INK,
                ha="left", va="bottom")


def _fig07_comma(items: Sequence[List[Cell]]) -> bool:
    """True when an item's name (the first cell of each item, a list of cells) holds a comma ('Haiku, thinking off')."""
    return any("," in it[0].printed for it in items if it)


def _fig07_semi(items: Sequence[List[Cell]]) -> bool:
    """True when a list's items must be separated by semicolons: three or more, and a name holds a comma (Edith, proof 4: 'Haiku-low;
    Haiku-max; Haiku, thinking off; and Sonnet-low'). Two items are joined by 'and' alone, whatever their names ('Haiku, thinking off and
    Sonnet-low'; the checker, proof 4 group F1: 'A; and B' is not English)."""
    return len(items) >= 3 and _fig07_comma(items)


def _fig07_and(items: List[List[Cell]]) -> List[Cell]:
    """Items (each a list of cells) as 'A and B' (two), 'A, B and C', or as 'A; B; and C' (three or more) where a name holds a comma."""
    semi = _fig07_semi(items)
    out: List[Cell] = []
    for i, it in enumerate(items):
        if i:
            if semi:
                out.append(L("; and") if i == len(items) - 1 else L(";"))
            else:
                out.append(L("and") if i == len(items) - 1 else L(","))
        out += it
    return out


def _fig07_curly(cells: Sequence[Cell]) -> List[Cell]:
    """Typed text with curly quotes and apostrophes (no straight quotes in print, Edith §3.6): a straight one in a label cell (some of
    them come from a shared helper) is replaced; number cells are untouched."""
    out: List[Cell] = []
    for c in cells:
        if c.kind == "label" and ("'" in c.printed or '"' in c.printed):
            t = re.sub(r'(^|[\s(\[])"', "\\1“", c.printed.replace("'", "’")).replace('"', "”")
            c = L(t)
        out.append(c)
    return out


@output("FIG-07")
@plain_ids
def fig_07(S: Store) -> FigureOut:
    """Item 19's estimate of the thinking share of list cost per setting and shape (the coloured bar, against the rest of the cost),
    with the median estimated thinking tokens. Item 19 is kept as defined (Edith's settlement N1): its visible-token estimate is biased,
    so the figure carries that note; the API's own thinking counts come with free analysis 10."""
    from matplotlib.transforms import blended_transform_factory
    base = "reporting.group_b.item_19"
    est = text_of(S.ref("main", f"{base}.label"))
    if not str(S.get("fa10", "label")).startswith("post hoc"):
        raise ValueError("FIG-07: free analysis 10 is no longer labelled post hoc")
    W = COLW
    left, pad_r = 1.38, 0.05
    pitch_pt, gap_rows = 11.0, 0.6              # points per row; the extra gap after the marked rows, in rows
    shapes = ("1x6", "6x1")
    # the API's own mean thinking tokens per call (free analysis 10, post hoc) for every plotted setting and shape; a setting is marked
    # exactly when it is zero, and its calls must equal item 19's
    plotted = {sh: [a for a in FIG07_ARMS if S.has("main", f"{base}.arms['{a}:{sh}']")] for sh in shapes}
    api_ref: Dict[Tuple[str, str], Ref] = {}
    api_share: Dict[Tuple[str, str], V] = {}              # the thinking share of list cost by the API's own count (the ticks)
    for sh in shapes:
        for arm in plotted[sh]:
            fb = join_key("result", "study1", f"{arm} {sh}")
            if not S.has("fa10", fb + ".mean_thinking_tokens"):
                raise ValueError(f"FIG-07: free analysis 10 stamps no thinking tokens for {arm} {sh}: the bracket cannot be read")
            if S.get("fa10", fb + ".calls") != S.get("main", f"{base}.arms['{arm}:{sh}'].calls"):
                raise ValueError(f"FIG-07: free analysis 10's {arm} {sh} calls differ from item 19's")
            api_ref[(arm, sh)] = S.ref("fa10", fb + ".mean_thinking_tokens")
            if not S.has("fa10", fb + ".thinking_share_of_list_cost"):
                raise ValueError(f"FIG-07: free analysis 10 stamps no thinking share of list cost for {arm} {sh}: the tick cannot be placed")
            api_share[(arm, sh)] = val(S, "fa10", fb + ".thinking_share_of_list_cost", 100.0, 1, PCT_BOUNDS)
    # the right of the bars holds two columns, each with its own narrow header (set on two or three lines, over its numbers), then the
    # bracket and its words. The shares' header starts where the shares start; the tokens, right-aligned, have their header right-aligned
    # over them (it may not run into the shares' header: checked).
    share_w = max(_fig07_text_width("\n".join(FIG07_SHARE_HEAD), W), _fig07_text_width("96.6%", W))
    tok_l = FIG07_SHARE_PT + share_w + FIG07_HDR_GAP                         # the tokens column's left edge (the header starts here)
    # the medians print as stamped (`stamped_count`: '1,737', '7,604.5'), and the column is set on the units digit: a whole median ends where
    # the whole part of a half ends, so '1,052.5' does not read as larger than '8,228' for being longer (the checker's SHOULD on Edith's
    # PR #40 review, S1). `tail_w` is the width of what follows a median's units digit ('.5'; nothing for a whole number), `tok_pt` the right
    # edge of the widest tail, and the header stays right-aligned at `tok_pt`.
    med_cell = {(a, sh): stamped_count(S.ref("main", f"{base}.arms['{a}:{sh}'].median")) for sh in shapes for a in plotted[sh]}
    tail_w = {k: _fig07_text_width(c.printed, W) - _fig07_text_width(c.printed.partition(".")[0], W) for k, c in med_cell.items()}
    tail_max = max(tail_w.values())
    tok_w = max(_fig07_text_width(c.printed.partition(".")[0], W) for c in med_cell.values()) + tail_max     # the widest whole part, then the tail
    tok_pt = tok_l + tok_w                                                   # the tokens' right edge
    med_right = {k: tok_pt - tail_max + tail_w[k] for k in med_cell}         # each median's right edge: its units digit stands at tok_pt - tail_max
    words_w = _fig07_text_width(FIG07_BRACKET_WORDS, W)
    for sh_line, tk_line in zip(reversed(FIG07_SHARE_HEAD), reversed(FIG07_TOKEN_HEAD)):       # the headers' last lines share a baseline
        if tok_pt - _fig07_text_width(tk_line, W) < FIG07_SHARE_PT + _fig07_text_width(sh_line, W) + 4.0:
            raise ValueError("FIG-07: the tokens header, right-aligned over its numbers, runs into the share header: widen FIG07_HDR_GAP")
    right_in = (tok_pt + 16.0 + words_w) / 72.0 + 0.03                         # room right of the bars: the bracket's words are the widest
    w_ax = W - left - right_in - pad_r
    marked_of = {sh: [a for a in plotted[sh] if _need_num(api_ref[(a, sh)]) == 0] for sh in shapes}
    rows_of = {sh: list(plotted[sh]) for sh in shapes}          # one order in both panels (FIG07_ARMS)
    for sh in shapes:                           # the bracket spans the first rows, and only the settings whose API mean is zero
        if rows_of[sh][:len(marked_of[sh])] != marked_of[sh] or any(
                (a in marked_of[sh]) != (_need_num(api_ref[(a, sh)]) == 0) for a in rows_of[sh]):
            raise ValueError(f"FIG-07: the bracketed rows on {sh} are not exactly the first settings, and exactly the settings whose API"
                             f" thinking tokens are zero: reorder FIG07_ARMS")
    if not all(marked_of[sh] for sh in shapes):
        raise ValueError("FIG-07: a panel has no setting without API thinking tokens: reword the bracket's words and the caption facts")
    n_b = len(rows_of["6x1"])
    if rows_of["1x6"][:n_b] != rows_of["6x1"]:
        raise ValueError("FIG-07: the pieces panel's settings are not the chains panel's first rows in the same order: reword the order fact")
    chains_only = rows_of["1x6"][n_b:]          # rows plotted on chains only (Step voting), last in the chains panel
    if any(_fig07_kind(a) != "design" for a in chains_only) or any(_fig07_kind(a) == "design" for sh in shapes for a in rows_of[sh][:len(
            marked_of[sh])]):
        raise ValueError("FIG-07: the rows plotted on chains only are no longer exactly the designs: reword 'setting or design' and the order fact")
    designs = [a for a in FIG07_DESIGNS if a in rows_of["1x6"]]
    d_names = _fig07_and([[L(fig07_name(a))] for a in designs])
    d_one = "a design" if len(designs) == 1 else "designs"
    sd = " or design" if designs else ""             # 'setting or design' wherever a sentence covers every plotted row
    # each setting's role in Study 1 (read as TAB-04 reads it) and its format check (item 24's compliance, item 17's flag)
    role = {(a, sh): s1_role(S, a, sh) for sh in shapes for a in plotted[sh]}
    fmt_of = {(a, sh): s1_format(S, a, sh) for sh in shapes for a in plotted[sh]}
    flagged = []
    for (a, sh), fc in fmt_of.items():
        if fc is None:
            continue
        if fc[1].value is True:
            flagged.append((a, sh))
        elif fc[1].value is not False:
            raise ValueError(f"FIG-07: {fc[1].source}:{fc[1].key} is {fc[1].value!r}, not a flag")
    no_format = sorted({a for (a, sh), fc in fmt_of.items() if fc is None})
    # format compliance prints at one decimal in a figure (Edith §2.1: a percentage in prose has one decimal, as TAB-16 prints it); the
    # shared s1_format gives two, so the same stamped value is re-rounded here
    fmt1 = {k: pct(fc[0].refs[0], dp=1) for k, fc in fmt_of.items() if fc is not None}
    hgt = {sh: (len(rows_of[sh]) - 1 + gap_rows + 1.4) * pitch_pt / 72.0 for sh in shapes}
    top_m, mid_m, bot_m = 0.52, 0.50, 0.46
    H = top_m + hgt["1x6"] + mid_m + hgt["6x1"] + bot_m
    boxes = {"1x6": [left / W, (H - top_m - hgt["1x6"]) / H, w_ax / W, hgt["1x6"] / H]}
    boxes["6x1"] = [left / W, bot_m / H, w_ax / W, hgt["6x1"] / H]
    fig = plt.figure(figsize=(W, H))
    axes = {sh: fig.add_axes(boxes[sh]) for sh in shapes}
    points: List[Dict[str, Any]] = []
    shares: Dict[Tuple[str, str], V] = {}
    api_tok: Dict[Tuple[str, str], Cell] = {}
    row_y: Dict[str, List[float]] = {}
    for sh in shapes:
        ax = axes[sh]
        arms = rows_of[sh]
        n_marked = len(marked_of[sh])
        ys, y = [], len(arms) - 1 + gap_rows
        for k, arm in enumerate(arms):
            ys.append(y)
            y -= 1.0 + (gap_rows if k == n_marked - 1 else 0.0)
        row_y[sh] = ys
        for arm, y in zip(arms, ys):
            key = f"{base}.arms['{arm}:{sh}']"
            _, model, effort = STUDY1_ARMS[arm]
            name = fig07_name(arm)
            s_v = val(S, "main", key + ".share_of_list_cost", 100.0, 1, PCT_BOUNDS)
            medc = med_cell[(arm, sh)]               # as stamped (Edith's PR #40 review, S1): '600', '1,737', and a stamped half keeps its '.5' ('7,604.5')
            rest = derive("100 - 100 * share_of_list_cost", lambda x: 100.0 - 100.0 * x, s_v.ref)
            bias_row = arm in marked_of[sh]          # the API reports no thinking here: the whole bar is the estimate's bias
            a_v = api_share[(arm, sh)]
            if (a_v.val == 0.0) != bias_row or a_v.val >= s_v.val:
                raise ValueError(f"FIG-07: the API's thinking share for {arm} {sh} ({a_v.val}) must be zero exactly on the bracketed rows and "
                                 f"strictly below the estimate ({s_v.val}): reword the tick key, the bracket and the 'below the estimate' facts")
            # the estimate's bias is drawn one way on every bar (Edith's PR 34 round 2: grey only where the API count is 0, solid elsewhere):
            # the model's colour from zero to the thinking share by the API's own count (the tick), grey from there to the end of the
            # estimate, and the rest of the cost in light grey; on the bracketed rows the API count is zero, so the whole estimate is grey
            if a_v.val > 0.0:
                ax.barh([y], [a_v.val], height=0.72, color=style_for(model, effort)["color"], linewidth=0, zorder=2)
            ax.barh([y], [s_v.val - a_v.val], left=[a_v.val], height=0.72, color=style.CONTEXT, linewidth=0, zorder=2)
            ax.barh([y], [rest.value], left=[s_v.val], height=0.72, color=FIG07_REST, edgecolor=style.CONTEXT, linewidth=0.5, zorder=2)
            ax.annotate(s_v.cell.printed + "%", xy=(100, y), xytext=(FIG07_SHARE_PT, 0), textcoords="offset points", ha="left", va="center",
                        fontsize=LAB, color=INK, annotation_clip=False)
            ax.annotate(medc.printed, xy=(100, y), xytext=(med_right[(arm, sh)], 0), textcoords="offset points", ha="right", va="center",
                        fontsize=LAB, color=INK_2, annotation_clip=False)
            shares[(arm, sh)] = s_v
            if a_v.val > 0.0:
                # the tick: the thinking share by the API's own count, a short dark mark across the bar (over a thin white edge, so it
                # shows on every model colour); where it is zero (the bracketed rows) it is not drawn: the bracket says so
                ax.plot([a_v.val, a_v.val], [y - 0.5, y + 0.5], color="white", linewidth=2.6, solid_capstyle="butt", zorder=3, clip_on=False)
                ax.plot([a_v.val, a_v.val], [y - 0.5, y + 0.5], color=INK, linewidth=1.1, solid_capstyle="butt", zorder=4, clip_on=False)
            tok = num(api_ref[(arm, sh)], dp=0)
            api_tok[(arm, sh)] = tok
            if (arm in marked_of[sh]) != (tok.printed == "0"):
                raise ValueError(f"FIG-07: the API's thinking tokens for {arm} {sh} print as {tok.printed}: mark exactly the zero ones")
            extra = {"api_mean_thinking_tokens": tok, "api_thinking_share": a_v.cell}
            if arm in marked_of[sh]:
                extra["api_note"] = "the API reports no thinking tokens (post hoc, free analysis 10); the bar is drawn in grey: it is the estimate's bias"
            extra["tier"] = FIG07_ROLE_WORDS[role[(arm, sh)]].replace("setting", _fig07_kind(arm))
            fc = fmt_of[(arm, sh)]
            if fc is not None:
                extra["format_compliance"] = fmt1[(arm, sh)]
                extra["format_flag"] = text_of(fc[1], {True: "flagged", False: "not flagged"})
            points.append(rec(f"{name}, {SHAPE_WORD[sh]}", SHAPE_WORD[sh], y=s_v, rest=num_d(rest, dp=1, bounds=PCT_BOUNDS),
                              median_thinking_tokens=medc, note="estimate", **extra))
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.7, len(arms) - 1 + gap_rows + 0.7)
        ax.set_xticks([0, 20, 40, 60, 80, 100])
        ax.set_yticks(ys)
        ax.set_yticklabels([_fig07_label(a, role[(a, sh)]) for a in arms], fontsize=LAB)       # the row labels carry the flags: 8 pt
        for lab, arm in zip(ax.get_yticklabels(), arms):
            lab.set_color(style.MODEL_TEXT[STUDY1_ARMS[arm][1]])
        ax.grid(axis="y", visible=False)
        tidy(ax)
        _fig07_tag(ax, {"1x6": "A", "6x1": "B"}[sh], {"1x6": "Chains", "6x1": "Pieces"}[sh])
        # the bar of the first (bracketed) row is named where it stands: the estimate's bias
        ax.text(shares[(arms[0], sh)].val / 2.0, ys[0], FIG07_BIAS_WORDS, ha="center", va="center", fontsize=LAB, color=INK, zorder=3)
        # the bracket right of the marked rows (x in axes fractions past the axis, y in data), with its four words
        tr = blended_transform_factory(ax.transAxes, ax.transData)
        y_hi, y_lo = ys[0] + 0.4, ys[n_marked - 1] - 0.4
        x_sp, x_tick = (tok_pt + 10.0) / (w_ax * 72) + 1.0, (tok_pt + 6.0) / (w_ax * 72) + 1.0
        for xs, yy in (([x_sp, x_sp], [y_lo, y_hi]), ([x_tick, x_sp], [y_hi, y_hi]), ([x_tick, x_sp], [y_lo, y_lo])):
            ax.add_line(Line2D(xs, yy, transform=tr, color=style.REFERENCE, linewidth=0.8, solid_capstyle="butt", clip_on=False))
        ax.text(1.0 + (tok_pt + 16.0) / (w_ax * 72), (y_hi + y_lo) / 2, FIG07_BRACKET_WORDS, transform=tr, ha="left", va="center",
                fontsize=LAB, color=INK, linespacing=1.05)
    # the two column headers, narrow, over panel A's columns (panel B's columns align under them): the shares' header from the shares'
    # left edge, the tokens' header right-aligned over the tokens
    ax_a = axes["1x6"]
    ax_a.annotate("\n".join(FIG07_SHARE_HEAD), xy=(100, 1.0), xycoords=("data", "axes fraction"),
                  xytext=(FIG07_SHARE_PT, 4), textcoords="offset points", ha="left", va="bottom", fontsize=LAB, color=INK_2,
                  annotation_clip=False, linespacing=1.05)
    ax_a.annotate("\n".join(FIG07_TOKEN_HEAD), xy=(100, 1.0), xycoords=("data", "axes fraction"),
                  xytext=(tok_pt, 4), textcoords="offset points", ha="right", va="bottom", fontsize=LAB, color=INK_2,
                  annotation_clip=False, linespacing=1.05)
    # the one key of the ticks, on the line of panel A's tag: the tick as drawn, then its words (which must fit left of the column headers)
    if FIG07_TICK_KEY_PT + 7.0 + _fig07_text_width(FIG07_TICK_WORDS, W) > w_ax * 72.0:
        raise ValueError("FIG-07: the tick key does not fit above panel A: shorten FIG07_TICK_WORDS")
    h_a = hgt["1x6"] * 72.0
    x_k = FIG07_TICK_KEY_PT / (w_ax * 72.0)
    ax_a.add_line(Line2D([x_k, x_k], [1.0 + 3.0 / h_a, 1.0 + 11.0 / h_a], transform=ax_a.transAxes, color=INK, linewidth=1.1,
                         solid_capstyle="butt", clip_on=False))
    ax_a.annotate(FIG07_TICK_WORDS, xy=(0, 1.0), xycoords="axes fraction", xytext=(FIG07_TICK_KEY_PT + 7.0, 3.0), textcoords="offset points",
                  ha="left", va="bottom", fontsize=LAB, color=INK)
    # direct label of the grey: the first row's remainder
    first = rows_of["1x6"][0]
    ax_a.text(shares[(first, "1x6")].val + 2.0, row_y["1x6"][0], "visible output and input", ha="left",
              va="center", fontsize=LAB, color=INK_2, zorder=3)
    axes["6x1"].set_xlabel("Estimated thinking share of list cost (%)")

    # the marked settings by shape, each with its own free analysis 10 cell (the zero) and its estimated share
    zero_items = {sh: [[L(fig07_name(a)), joined(L("("), api_tok[(a, sh)], L(")"), sep="")] for a in marked_of[sh]] for sh in shapes}
    share_items = {sh: [[L(fig07_name(a)), P(shares[(a, sh)].cell)] for a in marked_of[sh]] for sh in shapes}

    def by_shape(items: Dict[str, List[List[Cell]]]) -> List[Cell]:
        """'on chains, A and B; on pieces, A, B and C'; where an item's name holds a comma the shapes are set apart by a full stop (the
        items take semicolons from three on): 'on chains, A and B. On pieces, A; B; and C'."""
        semi = any(_fig07_comma(items[sh]) for sh in shapes)
        out: List[Cell] = []
        for j, sh in enumerate(shapes):
            out += ([L(".") if semi else L(";")] if j else []) + [L(("On " if semi and j else "on ") + SHAPE_WORD[sh] + ",")] + _fig07_and(items[sh])
        return out

    # the exploratory settings (the double dagger on their row labels), the settings that run first and last, and the format check's flags
    expl_items = []
    for a in FIG07_ARMS:
        shs = [sh for sh in shapes if role.get((a, sh)) == "exploratory"]
        if shs:
            where = "" if shs == [sh for sh in shapes if (a, sh) in role] else " on " + " and ".join(SHAPE_WORD[sh] for sh in shs)
            expl_items.append([L(fig07_name(a) + where)])
    flag_items = [[L(fig07_name(a) + " on " + SHAPE_WORD[sh]), joined(L("(format compliance "), P(fmt1[(a, sh)]), L(")"), sep="")]
                  for a, sh in flagged]
    if expl_items:
        expl_alt = ([L("The row labels marked " + FIG07_EXPLORATORY + " are the settings Study 1 ran as exploratory:")] + _fig07_and(expl_items) +
                    [L(". No other plotted setting" + sd + " is exploratory.")])
        expl_cap = ([L(FIG07_EXPLORATORY + " marks the settings that Study 1 ran as exploratory:")] + _fig07_and(expl_items) +
                    [L(". No other plotted setting" + sd + " is exploratory")])
    else:
        expl_alt = [L("No plotted setting" + sd + " is exploratory.")]
        expl_cap = [L("no plotted setting" + sd + " is exploratory")]
    no_fmt_names = _fig07_and([[L(fig07_name(a))] for a in no_format])
    if flagged:
        fmt_alt = ([L("The format check (the share of samples in the required answer format) flags only")] + _fig07_and(flag_items) + [L(".")])
        fmt_cap = ([L("the format check (the share of samples in the required answer format) flags only")] + _fig07_and(flag_items))
    else:
        fmt_alt, fmt_cap = [L("The format check flags none of the plotted settings.")], [L("the format check flags none of the plotted settings")]
    if no_format:
        fmt_cap += [L("; Study 1’s file stamps no format compliance for")] + no_fmt_names
    order_words = [L("Both panels list the settings in the same order, the settings for which the API reports no thinking tokens first")]
    if chains_only:
        order_words += [L("and"), *d_names, L("(" + d_one + ", plotted on chains only) last")]

    sh_head, tk_head = " ".join(FIG07_SHARE_HEAD), " ".join(FIG07_TOKEN_HEAD)
    # a setting bracketed on one shape but not on the other (the API reports some thinking where it is not bracketed): its tick explains why
    # it is bracketed on one shape only. Read from marked_of, never typed; the thinking there must be a little (under a tenth of its cost).
    partly = [(a, [sh for sh in shapes if a in marked_of[sh]], [sh for sh in shapes if a in plotted[sh] and a not in marked_of[sh]])
              for a in FIG07_ARMS if len({a in marked_of[sh] for sh in shapes if a in plotted[sh]}) == 2]
    partly_cells: List[Cell] = []
    for a, shs_marked, shs_free in partly:
        for sh_free in shs_free:
            if not 0.0 < api_share[(a, sh_free)].val < 10.0:
                raise ValueError(f"FIG-07: {a} on {sh_free} has an API thinking share of {api_share[(a, sh_free)].val}%: it is no longer 'a little': "
                                 f"reword the caption fact about the setting bracketed on one shape only")
            partly_cells += [L(";" + " " + fig07_name(a) + " is bracketed on " + " and ".join(SHAPE_WORD[x] for x in shs_marked) +
                               " but not on " + SHAPE_WORD[sh_free] + " because on " + SHAPE_WORD[sh_free] + " the API reports a little"
                               " thinking there (a thinking share of"), P(api_share[(a, sh_free)].cell),
                             L("of its list cost), and on " + " and ".join(SHAPE_WORD[x] for x in shs_marked) + " none")]
    # the thinking share by the API's own count (the ticks) against the estimate, for every row that has a tick (the bracketed rows' is zero)
    tick_items = {sh: [[L(fig07_name(a)), P(api_share[(a, sh)].cell), L("against"), P(shares[(a, sh)].cell)]
                       for a in rows_of[sh] if a not in marked_of[sh]] for sh in shapes}
    alt = [L("Two panels, chains above pieces, of horizontal bars for each Study 1 setting" +
             (" and, on chains only, for" if designs else "")), *d_names, L(("(" + d_one + ")" if designs else "") +
             ": the estimated thinking share of list cost, drawn the same way on every bar: in the model’s colour up to the thinking share by"
             " the API’s own count (the tick), and in grey, the estimate’s bias, from there to the end of the estimate (wholly grey on"
             " the bracketed rows), against the rest (light grey: visible output and input), with the estimated"
             " share printed at the right of each bar (under the header “" + sh_head + "”) and the median estimated thinking tokens in a"
             " column beside it (under the header “" + tk_head + "”)."), *order_words, L(". Estimated thinking takes"),
           P(shares[("haiku-max", "1x6")].cell), L("of Haiku-max’s chain cost,"),
           P(shares[("haiku-med", "1x6")].cell), L("of Haiku-medium’s,"), P(shares[("opus-med", "1x6")].cell), L("of Opus-medium’s and"),
           P(shares[("sonnet-med", "1x6")].cell), L("of Sonnet-medium’s. A bracket at the right of the top rows of each panel, with the words “" +
                                                     FIG07_BRACKET_WORDS.replace("\n", " ").rstrip("†") + "” and a dagger (post hoc), marks the"
                                                     " settings for which the API reports no thinking tokens; their bars are drawn wholly in grey, and"
                                                     " the first bar of each panel is labelled “" + FIG07_BIAS_WORDS + "”; the API’s mean"
                                                     " thinking tokens per call (free analysis 10, post hoc) is in parentheses:")]
    alt += by_shape(zero_items) + [L(". For each of these settings the estimate still shows a share of its cost as thinking, the estimate’s bias:")]
    alt += by_shape(share_items)
    alt += [L(". On every other bar a short dark tick marks the thinking share of list cost by the API’s own count (free analysis 10, post"
              " hoc; the key above panel A reads “" + FIG07_TICK_WORDS + "”): the bar is in the model’s colour up to the tick and grey"
              " from the tick to the end of the estimate, which is the estimate’s bias, as on the bracketed rows; the tick lies below the estimate on every bar:")]
    alt += by_shape(tick_items)
    alt += [L(". Study 1’s file stamps these numbers as"), joined(L("“"), est, L("”."), sep="")]
    alt += expl_alt + fmt_alt
    t24 = "reporting.group_b.item_24.table"
    arms_shapes = [(a, sh) for a in FIG07_ARMS for sh in shapes if (a in rows_of[sh])]
    if len({S.get("main", f"{t24}.{a} {sh}.base_puzzles") for a, sh in arms_shapes}) != 1:
        raise ValueError("FIG-07 settings differ in puzzles: print each")
    calls = []
    for a in FIG07_ARMS:
        c = [integer(S.ref("main", f"{base}.arms['{a}:{sh}'].calls")) for sh in shapes if (a, sh) in arms_shapes]
        calls.append([L(fig07_name(a))] + (c if len(c) == 1 else [c[0], L("and"), c[1]]) + ([L("(chains only)")] if len(c) == 1 else []))
    caption = {"tier": [L("pre-specified descriptive (Study 1’s estimate of the thinking share of list cost), labelled estimates; the settings"
                          " marked " + FIG07_EXPLORATORY + " are exploratory; the API’s own thinking counts (the bracketed settings’ zeros, the"
                          " ticks and the split of each bar at its tick) are post hoc (free analysis 10)")],
               "exploratory": expl_cap,
               "format": fmt_cap,
               "study": [L("Study 1, main run, 6 steps")],
               "set": [L("the Study 1 puzzle set at 6 steps: each puzzle as a chain and as pieces")],
               "n": [L("puzzles per shape:"), integer(S.ref("main", f"{t24}.haiku-med 1x6.base_puzzles")),
                     L("(every setting" + sd + "); calls per setting" + sd + " on chains and on pieces, as Study 1’s file counts them for this estimate:")]
                    + _seq(calls, sep=";"),
               "interval": [L("none: point estimates (Study 1’s file stamps no interval for the share or the median)")],
               "estimate": [L("Study 1’s file stamps these numbers as"), joined(L("“"), est, L("”"), sep=""),
                            L("; this overstates thinking where little or none happens, so the API’s own thinking counts replace the"
                              " estimate in the main text")],
               "marked": [L("both panels list the settings in the same order, the settings for which the API reports no thinking tokens first"
                            + (" and " + " and ".join(fig07_name(a) for a in chains_only) + " (" + d_one + ", chains only) last" if chains_only else "") +
                            "; the bracket (dagger: post hoc) marks the settings for which the API reports no thinking tokens (free analysis 10;"
                            " each setting’s mean thinking tokens per call in parentheses):")] + by_shape(zero_items) +
                         [L(". For each of these settings the estimate nonetheless shows a share of its cost as thinking, so its bar is drawn wholly in"
                            " grey (the estimate’s bias, drawn the same way on every bar: see ticks); the first bar of each panel is labelled “"
                            + FIG07_BIAS_WORDS + "”; the estimated shares:")] + by_shape(share_items),
               "ticks": [L("the dark tick on every other bar (the key above panel A) is the thinking share of list cost by the API’s own count"
                           " (free analysis 10, post hoc); the bar is in the model’s colour up to the tick and in grey from the tick to the end"
                           " of the estimate, the estimate’s bias, drawn as on the bracketed rows; the tick lies below the estimate on every bar, so the"
                           " estimate overstates thinking in every plotted setting; the tick against the estimate:")] + by_shape(tick_items) +
                        partly_cells,
               "price": price_study1(S)}
    if chains_only:
        # the rows plotted on chains only (Step voting): why panel B has none, and where their values are (Edith's proof 3, Figure S12: no
        # table prints them; her D-168, page 104: the caption must say so, so the fact leads with it). Study 1's main run ran step voting on chains only (the file has the design's estimate on chains only: checked
        # above by `plotted`); the estimate and the median are item 19's, the tick is free analysis 10's, and the figure's data file holds all
        # three. Table TAB-16 has no row for the design (it prints settings; the design's API counts are in free analysis 10).
        # "no table prints them" is checked on the tables as built: no row of TAB-16 (or of its panels), the one table whose plan
        # lists item 19 and free analysis 10, names the design (Edith, PR #38 review)
        from . import paper_outputs as po
        t16 = po.load_registry()["TAB-16"].build(type(S)(S.repo, S.sources))     # its own store: TAB-16's sources stay out of FIG-07's
        printed_rows = [c.printed.lower() for tab in [t16] + [p for _, p in t16.panels] for r in tab.rows for c in r]
        for a in chains_only:
            if any(fig07_name(a).lower() in x for x in printed_rows):
                raise ValueError(f"FIG-07: TAB-16 now prints a row for {fig07_name(a)}: 'no table prints them' is wrong")
        sv = []
        for a in chains_only:
            med = stamped_count(S.ref("main", f"{base}.arms['{a}:1x6'].median"))
            sv.append([L(fig07_name(a) + "’s bar is in no table (TAB-16 has no row for it): its estimated share"), P(shares[(a, "1x6")].cell),
                       L(", its median estimated thinking tokens"), med, L("and its thinking share by the API’s own count (the tick)"),
                       P(api_share[(a, "1x6")].cell),
                       L("come from Study 1’s file (the estimate and the median) and free analysis 10 (the tick, post hoc), and they are in this"
                         " figure’s data file; " + fig07_name(a) + " is plotted on chains only because it ran on chains only in Study 1’s main run,"
                         " so panel B has no row for it")])
        caption["step_voting"] = _seq(sv, sep=";")
    return FigureOut(fig, points, tight(_fig07_curly(alt)), tight_caption({k: _fig07_curly(v) for k, v in caption.items()}))
