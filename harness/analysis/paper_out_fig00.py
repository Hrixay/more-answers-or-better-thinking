"""FIG-00, the paper's Figure 1: the story at a glance (D-141; redesigned in batch (h) to Karen's house style, page 3, with Edith's
conditions on it, f38f53d, and her polish standard §8; corrected after her PR #34 chart review, 2026-10-18). One row of two panels,
accuracy against cost per answer on a log axis, one message: a vote of cheap-model answers that costs about one Opus-medium answer
was worse than it at medium effort (Study 1), and a small vote at max effort was shown no worse (Study 1b).

Panel A is Study 1 at 6 steps with its two shapes drawn separately (filled = chains, hollow = pieces), because Tests 1 and 2 are
separate tests by shape: one Haiku-medium sample, its cost-matched vote (Tests 1 and 2), one Haiku-max sample (exploratory) and
one Opus-medium answer per shape. Unlabelled arrows run from the one Haiku-medium sample to the vote and to the Haiku-max sample
(Edith, 2026-10-17: no values, no words; only the arrows to the Haiku-max sample carry †, post hoc). Panel B is
Study 1b at 16 steps with both shapes pooled (B1 to B3 score each puzzle as the mean over its two shapes; the panel's title says
"shapes pooled"): one Haiku-medium sample, one Haiku-max sample (Test B1's challenger), the 6-sample Haiku-max vote (Test B2,
estimated from 10 samples) and Opus-medium; no Haiku-medium vote was run at 16 steps, so none is drawn. The key (filled = chains,
hollow = pieces, in dark grey because filled and hollow also apply to Opus-medium's diamonds) sits above panel A only.

Printed values (Edith §8.8): only the paired differences of Tests 1, 2 and B2, as Table 2 prints them (one decimal), in Table 2's
row order. No reading crosses the panels: they use different puzzle sets and lengths and no drift check links them. Annotation lines
(arrows, one leader line) are thin solid context grey. The pieces arrow to the vote is a curve that comes down onto its mark from above
the chains vote's 95% bar (a straight arrow to it must pass through that bar, whose range holds the pieces vote); it rises only just
enough to clear that bar (the build checks both). The two arrows
that leave the two Haiku-medium samples (one to a vote, one to Haiku-max) cross once near their tails: with the chains sample below
the pieces sample and the chains Haiku-max sample to the right of the pieces one, one crossing cannot be avoided in one panel. Marks sit
at their measured costs except in panel A, where the two shapes of one setting would overlap: each of the two is then set sideways by
about eight percent of cost, and the caption fact 'marks' says so. Panel B draws every mark at its measured cost: the vote's circle
(in front) overlaps Opus-medium's diamond in part, which is the comparison B2 rests on (the vote costs 0.894 of Opus-medium's). Marks,
colours, axes and helpers are the shared style's (paper_out_style, the shared helpers of paper_out_figures); 95% bars are exact
(Clopper–Pearson) where the stamped interval is one, or, post hoc, where free analysis 4 replaces a collapsed bootstrap one (the
caption facts name that case only when some point is drawn with it). One bar rule, decided per point and per arm (FIG-01's
`_fig0001_bar_hidden`, which FIG-00 shares): a bar is not drawn only if it lies behind its marker, that is, its whole span is shorter than
the marker and neither arm sticks out BAR_TOL_PT (a point) or more past the marker's edge (a one-sided bar at 100% is drawn); the axes' limits are set
before any mark is drawn, and the caption fact 'bars' names the points the same test hides.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .paper_out_core import (Cell, FigureOut, Ref, Store, derive, fa4_exact, integer, joined, label, num, num_d, output, pct, pts, usd)
from .paper_out_figures import (ACC_LABEL, COST_ANSWER, MARK_HALF_PT, _fig0001_point, acc_axis, cost_axis, panel_tag, rec, tight, tight_caption)
from .paper_out_names import STUDY1_TESTS, STUDY1B_TESTS, main_text
from .paper_out_style import CONTEXT, INK, MODEL_TEXT, REFERENCE

import matplotlib.pyplot as plt                                         # noqa: E402
from matplotlib.lines import Line2D                               # noqa: E402
from matplotlib.patches import ConnectionStyle                    # noqa: E402
from matplotlib.path import Path                                  # noqa: E402
from matplotlib.transforms import ScaledTranslation               # noqa: E402

T24 = "reporting.group_b.item_24"
S1 = "confirmatory.views.as_deployed"                  # Study 1's tests (main analysis file)
S1B = "confirmatory.primary_margin_5.views.as_deployed"  # Study 1b's tests at the primary 5-point margin
SHAPE_WORD = {"1x6": "chains", "6x1": "pieces", "1x16": "chains", "16x1": "pieces", "pooled": "chains and pieces pooled"}

T_H, T_O = MODEL_TEXT["haiku"], MODEL_TEXT["opus"]
LAB = 8.0


class P:
    """One plotted point: accuracy (points) with its 95% ends, and its list cost per answer, each a Ref."""

    INTERVAL = {"": "cluster bootstrap", "cp": "exact (Clopper–Pearson)", "fa4": "exact (Clopper–Pearson, post hoc: free analysis 4)"}

    def __init__(self, acc: Ref, lo: Ref, hi: Ref, cost: Ref, exact: str = ""):
        self.acc, self.lo, self.hi, self.cost, self.exact = acc, lo, hi, cost, exact

    def xy(self) -> Tuple[float, float, float, float]:
        return float(self.cost.value), float(self.acc.value), float(self.lo.value), float(self.hi.value)

    def rec(self, series: str, panel: str, shape_: str, k: Optional[Ref] = None) -> Dict[str, Any]:
        d = {"series": series, "panel": panel, "shape": shape_, "x": usd(self.cost).record(), "y": num(self.acc, dp=1).record(),
             "lo": num(self.lo, dp=1).record(), "hi": num(self.hi, dp=1).record(),
             "interval": self.INTERVAL[self.exact]}
        if k is not None:
            d["k"] = integer(k).record()
        return d


def _boot(S: Store, src: str, base: str, acc_key: str, cost_key: str) -> P:
    """A point with a stamped bootstrap 95% interval (the dict at `base` holds `ci95`). Where it collapsed, free analysis 4's exact
    (Clopper–Pearson) interval replaces it (core.fa4_exact checks it is fa4's copy of that very interval; the bars are drawn in points,
    so its unit must be points); a collapsed interval free analysis 4 does not cover refuses the build."""
    lo, hi = S.ref(src, base + ".ci95.0"), S.ref(src, base + ".ci95.1")
    exact = ""
    if lo.value == hi.value:
        e = fa4_exact(S, src, base)
        if e is None or e.scale != 1.0:
            raise ValueError(f"{src}:{base}: collapsed interval with no exact replacement in points")
        lo, hi, exact = e.lo, e.hi, "fa4"
    return P(S.ref(src, acc_key), lo, hi, S.ref(src, cost_key), exact)


def _s1b(S: Store, base: str) -> P:
    """A Study 1b point pooled over the two shapes (B1 to B3 score each puzzle as the mean over its shapes): accuracy, 95% bar and
    list cost per answer, all stamped under the pooled entry."""
    return _boot(S, "s1b", base, base + ".mean", base + ".cost_per_answer")


DODGE = 2.5          # points: in panel A, where the two shapes of one setting would overlap, each is set this far to its own side of its measured cost (panel B has no shift)
FIG_H = 2.44         # inches: print size, no tight box (F14)
M_L, M_R, M_B, M_T = 0.55, 0.03, 0.42, 0.46       # the panels' margins in inches: left (accuracy ticks and title), right, bottom (ticks and the cost title), top (key row, two-line titles)
WSPACE, RATIOS = 0.25, [1.1, 1.0]    # the gap between the panels (a fraction of their mean width: room for panel B's own accuracy ticks and title) and the panels' width ratio (job: GPT review point D)
DIVIDER_GAP = 0.05   # inches: the least clear space on each side of the thin grey divider between the panels (panel A's furthest label to its left, panel B's accuracy title to its right)
TITLE_Y = 0.03       # inches from the bottom edge: the shared cost-axis title sits about 0.08 in under the tick labels
ANN = CONTEXT        # annotation lines (arrows, the leader line): thin solid context grey; no dimension lines
VOTE_ARROW_DAGGER = False      # ledger row C-050, the only source of the gains, reads all four arrows as post hoc: every gain carries the dagger (False: only the arrows to the Haiku-max sample, as Edith's condition 3 names)
HUMP = (0.85, 0.14)  # the pieces arrow to the vote: its curve's control point lies this fraction (u) of the way to the head and this multiple (h) of the arrow's length above the head
HUMP_CLEAR_PT = 1.5  # build check: the curve passes at least this far above the chains vote's 95% bar ...
HUMP_OVER = 5.0      # ... and its highest point is at most this many accuracy points above that bar's top (it "rises only just enough", not to about 83%)
B_DROP = 9.0         # points: panel B's vote label hangs this far under the vote's centre (6 pt under the circle's lower edge)
KEY_COLOR = REFERENCE      # the key's swatches and words: dark grey, since filled and hollow also apply to Opus-medium's diamonds
# where each arrow's gain is written: (setting, shape) -> (fraction of the arrow's path, offset x and y in points, horizontal and vertical alignment)
ARROW_LABELS_A = {("vote", "1x6"): (0.62, 0.0, 0.0, "left", "top"), ("vote", "6x1"): (0.60, 0.0, 3.0, "center", "bottom"),
                  ("hx", "1x6"): (0.60, 3.5, 0.0, "left", "center"), ("hx", "6x1"): (0.42, -3.5, 0.0, "right", "center")}


class _Hump(ConnectionStyle._Base):
    """A quadratic curve from an arrow's tail to its head whose control point lies a fraction `u` of the way to the head and `h` times the
    arrow's length above it: the curve rises gently, then comes down onto the head from above and from the left (all in display units,
    so the shape does not depend on the resolution)."""

    def __init__(self, u: float, h: float):
        self.u, self.h = u, h

    def control(self, a, b) -> np.ndarray:
        a, b = np.asarray(a, float), np.asarray(b, float)
        return np.array([a[0] + self.u * (b[0] - a[0]), b[1] + self.h * float(np.hypot(*(b - a)))])

    def connect(self, posA, posB):
        return Path([tuple(posA), tuple(self.control(posA, posB)), tuple(posB)], [Path.MOVETO, Path.CURVE3, Path.CURVE3])


def _fig00_tr(ax, dx: float):
    """Data coordinates shifted sideways by `dx` points (a display offset: the plotted values are untouched)."""
    return ax.transData + ScaledTranslation(dx / 72.0, 0.0, ax.figure.dpi_scale_trans)


def _fig00_mark(ax, p: P, model: str, effort: str, hollow: bool, dx: float, zorder: int = 4) -> bool:
    """The shared mark (5 pt marker, 0.8 pt uncapped bar; hollow = pieces) shifted sideways by dx points (0 = at its measured cost);
    never clipped at 100. The bar follows the per-arm rule, decided for this point alone (`_fig0001_point`, from the axes' final limits:
    set them before calling): it is not drawn only if it lies behind the marker (whole span shorter than the marker and no arm sticking
    out a point or more past its edge); the return value says so (True = not drawn), and the caption fact 'bars' names those points. The
    bar sits one level behind the marker."""
    n_c, n_l = len(ax.collections), len(ax.lines)
    x, y, lo, hi = p.xy()
    hidden = _fig0001_point(ax, x, y, lo, hi, model, effort, hollow=hollow, zorder=zorder)
    if dx:
        tr = _fig00_tr(ax, dx)
        for art in list(ax.collections[n_c:]) + list(ax.lines[n_l:]):
            art.set_transform(tr)
    for art in list(ax.collections[n_c:]) + list(ax.lines[n_l:]):
        art.set_clip_on(False)
    return hidden


def _fig00_arrow(ax, tail: P, head: P, dx_tail: float, dx_head: float, gain: Optional[Cell], where: Tuple[float, float, float, str, str],
                 dagger: bool = False, curve: Optional[Tuple[float, float]] = None) -> None:
    """A thin grey arrow from the tail's mark to the head's, straight or (curve = (u, h)) the _Hump curve. Its gain is written at
    `where` = (fraction t of the arrow's path, offset x and y in points, ha, va); there is no backing box, so no line is hidden."""
    (x0, y0, _, _), (x1, y1, _, _) = tail.xy(), head.xy()
    ap = dict(arrowstyle="-|>", color=ANN, linewidth=0.7, shrinkA=5, shrinkB=3.5, mutation_scale=6)
    if curve is not None:
        ap["connectionstyle"] = _Hump(*curve)
    ax.annotate("", xy=(x1, y1), xycoords=_fig00_tr(ax, dx_head), xytext=(x0, y0), textcoords=_fig00_tr(ax, dx_tail), zorder=2, arrowprops=ap)
    text = (gain.printed if gain is not None else "") + ("†" if dagger else "")
    if not text:
        return
    p0 = _fig00_tr(ax, dx_tail).transform((x0, y0))
    p1 = _fig00_tr(ax, dx_head).transform((x1, y1))
    t, ox, oy, ha, va = where
    if curve is None:
        q = p0 + t * (p1 - p0)
    else:
        c = _Hump(*curve).control(p0, p1)
        q = (1 - t) ** 2 * p0 + 2 * t * (1 - t) * c + t ** 2 * p1
    qd = ax.transData.inverted().transform(q)
    ax.annotate(text, xy=(qd[0], qd[1]), xycoords="data", xytext=(ox, oy), textcoords="offset points",
                ha=ha, va=va, fontsize=LAB, color=INK, zorder=5)


def _fig00_hump_check(ax, tail: P, head: P, chains_vote: P, dx_tail: float, dx_head: float, dx_chains: float) -> None:
    """The curved pieces arrow must clear the chains vote's 95% bar (a straight arrow would cross it) and rise only just enough to do so:
    at the bar it passes at least HUMP_CLEAR_PT above the bar's top, and its highest point is at most HUMP_OVER accuracy points above it.
    Measured in display units on the final layout, from the same curve the arrow draws; refuses the build otherwise."""
    fig = ax.figure
    t0 = _fig00_tr(ax, dx_tail).transform(tail.xy()[:2])
    t1 = _fig00_tr(ax, dx_head).transform(head.xy()[:2])
    c = _Hump(*HUMP).control(t0, t1)
    t = np.linspace(0.0, 1.0, 801)[:, None]
    curve = (1 - t) ** 2 * t0 + 2 * t * (1 - t) * c + t ** 2 * t1
    bx, _, _, bar_hi = chains_vote.xy()
    bar_x, bar_top = _fig00_tr(ax, dx_chains).transform((bx, bar_hi))
    y_at_bar = float(np.interp(bar_x, curve[:, 0], curve[:, 1]))
    pt = 72.0 / fig.dpi
    clear = (y_at_bar - bar_top) * pt
    peak = ax.transData.inverted().transform((0.0, float(curve[:, 1].max())))[1]
    if clear < HUMP_CLEAR_PT or peak > bar_hi + HUMP_OVER:
        raise ValueError(f"FIG-00 panel A: the pieces arrow's curve passes {clear:.1f} pt above the chains vote's bar (at least {HUMP_CLEAR_PT}) "
                         f"and peaks at {peak:.1f} against the bar's top at {bar_hi:.1f} (at most {HUMP_OVER} more): adjust HUMP")


def _fig00_key_handle(hollow: bool) -> Line2D:
    """A key swatch: the Haiku circle's size and edge, in dark grey (filled = chains, hollow = pieces)."""
    return Line2D([0], [0], linestyle="none", marker="o", markersize=5, markerfacecolor="white" if hollow else KEY_COLOR,
                  markeredgecolor=KEY_COLOR, markeredgewidth=1.1 if hollow else 0.6)


def _fig00_off(ax, p: P, dx: float, ox: float, oy: float, text: str, ha: str, color: str, va: str = "center", y: Optional[float] = None,
               align: Optional[str] = None) -> None:
    """A label placed (ox, oy) points from a mark (data coordinates plus the mark's sideways shift); `align` sets how its lines align."""
    x, yy, _, _ = p.xy()
    ax.annotate(text, xy=(x, yy if y is None else y), xycoords=_fig00_tr(ax, dx), xytext=(ox, oy), textcoords="offset points", ha=ha, va=va,
                fontsize=LAB, color=color, linespacing=1.1, annotation_clip=False, multialignment=align or ha)


@output("FIG-00")
@main_text
def fig_00(S: Store) -> FigureOut:
    # ---- Study 1, 6 steps (the main set), chains (1x6) and pieces (6x1) drawn separately
    a: Dict[Tuple[str, str], P] = {}                 # (setting, shape) -> point
    ks: Dict[str, Ref] = {}
    for sh in ("1x6", "6x1"):
        t = f"{T24}.table['haiku-med {sh}']"
        a[("hm", sh)] = _boot(S, "main", t + ".accuracy_interval", t + ".accuracy_mean", t + ".cost_per_puzzle.mean")
        o = f"{T24}.table['opus-med {sh}']"
        a[("om", sh)] = P(S.ref("main", o + ".accuracy_mean"), S.ref("main", o + ".accuracy_cp95.cp95.0"),
                          S.ref("main", o + ".accuracy_cp95.cp95.1"), S.ref("main", o + ".cost_per_puzzle.mean"), "cp")
        h = f"{T24}.table['haiku-max {sh}']"
        a[("hx", sh)] = _boot(S, "main", h + ".accuracy_interval", h + ".accuracy_mean", h + ".cost_per_puzzle.mean")
        k = S.ref("main_k", f"k_from_rows.opus.{sh}.k")                       # the cost-matched vote size (Tests 1 and 2)
        line = S.get("main", f"{T24}.chart.{sh}.haiku_med_vote_line")
        i = next(j for j, p in enumerate(line) if int(p["k"]) == int(k.value))
        v = f"{T24}.chart.{sh}.haiku_med_vote_line.{i}"
        a[("vote", sh)] = _boot(S, "main", v, v + ".accuracy", v + ".cost_per_puzzle")
        ks[sh] = k
    # ---- Study 1b, 16 steps, both shapes pooled
    kb2 = S.ref("s1b_k", "k")
    vc = S.get("s1b", "descriptive.vote_curve_n16.points")
    iv = next(j for j, p in enumerate(vc) if int(p["k"]) == int(kb2.value))
    b: Dict[str, P] = {"hm": _s1b(S, "descriptive.arms['hm@16'].pooled"), "hx": _s1b(S, "descriptive.arms['hx@16'].pooled"),
                       "vote": _s1b(S, f"descriptive.vote_curve_n16.points.{iv}.pooled"),
                       "om": _s1b(S, "descriptive.arms['om@16'].pooled")}
    # ---- the paired differences Table 2 prints (Tests 1, 2 and B2), at its one decimal with the guard at 0 and the margin
    m1, mb = S.ref("main", f"{S1}.margin"), S.ref("s1b", f"{S1B}.margin")
    test_of = {sh: next(t for t, v in STUDY1_TESTS.items() if v[3] == sh and v[4] == "O") for sh in ("1x6", "6x1")}
    d_test = {sh: pts(S.ref("main", f"{S1}.tests.{t}.d"), dp=1, margin=float(m1.value)) for sh, t in test_of.items()}
    test_name = {sh: STUDY1_TESTS[t][0] for sh, t in test_of.items()}
    d_b2 = pts(S.ref("s1b", f"{S1B}.tests.B2.d"), dp=1, margin=float(mb.value))
    test_name_b2 = STUDY1B_TESTS["B2"][0]

    fig = plt.figure(figsize=(6.5, FIG_H))
    gs = fig.add_gridspec(1, 2, left=M_L / 6.5, right=1 - M_R / 6.5, bottom=M_B / FIG_H, top=1 - M_T / FIG_H, wspace=WSPACE,
                          width_ratios=RATIOS)
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])             # its own accuracy axis: the two studies share nothing (job: GPT review point D)
    XLIM, TICKS = (0.0006, 0.8), [0.001, 0.01, 0.1]       # job K row 12 (a $0.003 and $0.03 tick): tried; panel B is 0.82 in per decade, so "$0.001" and "$0.003" touch
    for ax in (ax_a, ax_b):
        cost_axis(ax, XLIM[0], XLIM[1], TICKS)
        acc_axis(ax, 0.0, 100.0)
    layout = {id(ax): (ax.get_ylim(), tuple(ax.get_position().bounds)) for ax in (ax_a, ax_b)}   # the bar rule reads these: fixed before any mark
    ax_a.set_ylabel(ACC_LABEL)
    ax_b.set_ylabel(ACC_LABEL)
    for ax in (ax_a, ax_b):             # each panel its own cost-axis title
        pos = ax.get_position()
        fig.text((pos.x0 + pos.x1) / 2.0, TITLE_Y / FIG_H, COST_ANSWER, ha="center", va="bottom", fontsize=8)
    panel_tag(ax_a, "A")
    panel_tag(ax_b, "B")
    n_main = integer(S.ref("main", f"{S1}.tests.t1.n"))      # Test 1's n: the puzzles of Study 1's main set (the key claim C-006 reads)
    ax_a.text(0.055, 1.03, f"Study 1: 6-step puzzles\nmain set, {n_main.printed} puzzles", transform=ax_a.transAxes, ha="left", va="bottom", fontsize=LAB, color=INK,
              linespacing=1.1)
    ax_b.text(0.07, 1.03, "Study 1b: 16-step puzzles\nfresh set, shapes pooled", transform=ax_b.transAxes, ha="left", va="bottom", fontsize=LAB, color=INK,
              linespacing=1.1)
    # the key is panel A's only (F13, §8.5; Edith's PR #34 review): filled = chains, hollow = pieces, in dark grey; panel B says "shapes pooled" in its title
    fig.legend([_fig00_key_handle(False), _fig00_key_handle(True)], ["chains (B: pooled)", "pieces"], loc="upper center",     # B's filled marks are pooled, not chains (job K row 13)
               bbox_to_anchor=((ax_a.get_position().x0 + ax_a.get_position().x1) / 2.0, 1.0), ncol=2, borderaxespad=0.0, handletextpad=0.2,
               columnspacing=1.6, fontsize=LAB, frameon=False, labelcolor=KEY_COLOR)
    # panel A's sideways shift in cost terms, checked against the words the caption uses for it ("about eight percent" of cost to each mark's
    # own side, so a pair looks "about seventeen percent" further apart than measured); panel B has no shift
    pt_per_decade = ax_a.get_position().width * 6.5 * 72.0 / (math.log10(XLIM[1]) - math.log10(XLIM[0]))
    side = 10.0 ** (DODGE / pt_per_decade)
    if not (1.06 < side < 1.10 and 1.14 < side ** 2 < 1.20):
        raise ValueError(f"FIG-00 panel A: the sideways shift of {DODGE} pt is a factor {side:.3f} per mark in cost ({side ** 2:.3f} "
                         f"between the pair), not 'about eight percent' (17 percent for the pair): reword the caption fact 'marks'")

    points: List[Dict[str, Any]] = []
    over_names: Dict[str, Dict[str, List[str]]] = {"A": {}, "B": {}}     # panel -> setting -> shapes whose bar is not drawn (the per-arm test; named in the caption facts)
    names = {"hm": "one Haiku-medium sample", "vote": "cost-matched Haiku-medium vote", "hx": "one Haiku-max sample (exploratory)",
             "om": "one Opus-medium answer"}
    # ---------------- panel A: marks (chains filled, pieces hollow), then arrows and labels
    shift: Dict[Tuple[str, str], float] = {}
    for what in ("om", "hm", "vote", "hx"):
        left = min(("1x6", "6x1"), key=lambda sh: a[(what, sh)].xy()[0])     # the cheaper shape goes left, so the order of costs holds
        for sh in ("1x6", "6x1"):
            shift[(what, sh)] = -DODGE if sh == left else DODGE
    for what, effort, model in (("om", "medium", "opus"), ("hm", "medium", "haiku"), ("vote", "medium", "haiku"), ("hx", "max", "haiku")):
        # each point on its own (Edith's PR #34 review): a bar is hidden only if it lies behind the marker (the per-arm rule)
        for sh in ("1x6", "6x1"):
            if _fig00_mark(ax_a, a[(what, sh)], model, effort, sh == "6x1", shift[(what, sh)]):
                over_names["A"].setdefault(what, []).append(SHAPE_WORD[sh])
            points.append(a[(what, sh)].rec(names[what], "Study 1, 6 steps", SHAPE_WORD[sh], k=ks[sh] if what == "vote" else None))
    for sh in ("1x6", "6x1"):
        points.append(rec(f"{test_name[sh]}: Haiku-medium vote minus Opus-medium, {SHAPE_WORD[sh]}", "Study 1, 6 steps", d=d_test[sh]))
    # arrows run from one Haiku-medium sample to the vote (shallow) and to the Haiku-max sample (steep); each gain is written beside its
    # arrow on the side that keeps it clear of the other shape's arrow; the pieces arrow to the vote is the curve that clears the chains vote's bar
    for (what, sh), where in ARROW_LABELS_A.items():
        # Edith's ruling (2026-10-17): the arrows print no value and no words; only the arrows to the Haiku-max sample carry † (post hoc)
        _fig00_arrow(ax_a, a[("hm", sh)], a[(what, sh)], shift[("hm", sh)], shift[(what, sh)], None, where,
                     (what == "hx") or VOTE_ARROW_DAGGER, curve=HUMP if (what, sh) == ("vote", "6x1") else None)
    # the arrow's curve must clear the chains vote's bar without overshooting (the build refuses a curve that does not)
    _fig00_hump_check(ax_a, a[("hm", "6x1")], a[("vote", "6x1")], a[("vote", "1x6")], shift[("hm", "6x1")], shift[("vote", "6x1")], shift[("vote", "1x6")])
    # the vote's label carries the two tests' values under it, each named by its shape, in Table 2's row order (Test 1, pieces; Test 2, chains)
    _fig00_off(ax_a, a[("vote", "6x1")], shift[("vote", "6x1")], 9, 4, "cost-matched\nHaiku-medium vote", "left", T_H, va="bottom")
    _fig00_off(ax_a, a[("vote", "6x1")], shift[("vote", "6x1")], 9, 2, f"minus Opus-medium:\n{test_name['6x1']} (pieces) {d_test['6x1'].printed}\n"
               f"{test_name['1x6']} (chains) {d_test['1x6'].printed}", "left", INK, va="top")
    # the Haiku-medium sample's label sits just under the two 95% bars (about 32%), in Haiku blue
    ax_a.text(0.00063, 33.0, "Haiku-medium\nsample", ha="left", va="top", fontsize=LAB, color=T_H, linespacing=1.1)
    _fig00_off(ax_a, a[("hx", "1x6")], shift[("hx", "1x6")], 9, -5, "Haiku-max\nsample‡", "left", T_H)
    _fig00_off(ax_a, a[("om", "6x1")], shift[("om", "6x1")], 8, -4, "Opus-medium", "left", T_O)

    # ---------------- panel B: pooled, filled marks, every one at its measured cost (no sideways shift: the vote costs 0.894 of Opus-medium's
    # and the two marks overlap in part; the vote's circle is drawn in front of Opus-medium's diamond)
    bnames = {"hm": "one Haiku-medium sample", "hx": "one Haiku-max sample (Test B1)", "om": "one Opus-medium answer",
              "vote": f"{integer(kb2).printed}-sample Haiku-max vote (Test B2)"}
    for what, effort, model in (("om", "medium", "opus"), ("hm", "medium", "haiku"), ("hx", "max", "haiku"), ("vote", "max", "haiku")):
        if _fig00_mark(ax_b, b[what], model, effort, False, 0.0, zorder=6 if what == "vote" else 4):
            over_names["B"].setdefault(what, []).append("pooled")
        points.append(b[what].rec(bnames[what], "Study 1b, 16 steps", SHAPE_WORD["pooled"], k=kb2 if what == "vote" else None))
    points.append(rec("Test B2: Haiku-max vote minus Opus-medium", "Study 1b, 16 steps", d=d_b2))
    # the caption fact 'marks' and the alt text say that the vote's circle overlaps Opus-medium's diamond in part: the build checks it
    centre = {w: ax_b.transData.transform(b[w].xy()[:2]) * 72.0 / fig.dpi for w in ("vote", "om")}
    if float(np.hypot(*(centre["vote"] - centre["om"]))) >= MARK_HALF_PT["haiku"] + MARK_HALF_PT["opus"]:
        raise ValueError("FIG-00 panel B: the vote's circle and Opus-medium's diamond no longer overlap at their measured costs: reword the caption fact 'marks' and the alt text")
    _fig00_off(ax_b, b["hm"], 0.0, 8, 0, "Haiku-medium\nsample", "left", T_H)
    _fig00_off(ax_b, b["hx"], 0.0, -8, 0, "Haiku-max\nsample (Test B1)", "right", T_H)
    # the vote's label: a block of three lines under the pair, its right end on the panel's edge (it cannot start at the circle: it would
    # run past the figure), at least 6 pt clear of Test B1's marker and joined to the circle by a short leader straight down; its value line
    # is worded as panel A's ("minus Opus-medium:")
    rend = fig.canvas.get_renderer()
    vx, vy, _, _ = b["vote"].xy()
    head = ax_b.annotate(f"{integer(kb2).printed}-sample Haiku-max vote", xy=(1.0, vy), xycoords=ax_b.get_yaxis_transform(),
                         xytext=(0, -B_DROP), textcoords="offset points", ha="right", va="top", fontsize=LAB, color=T_H, annotation_clip=False)
    bb = head.get_window_extent(rend)
    w_pt, h_pt = bb.width * 72.0 / fig.dpi, bb.height * 72.0 / fig.dpi
    x_left = 1.0 - w_pt / (ax_b.get_window_extent(rend).width * 72.0 / fig.dpi)
    head.set_ha("left")
    head.xy = (x_left, vy)
    ax_b.annotate(f"minus Opus-medium:\n{test_name_b2} {d_b2.printed}", xy=(x_left, vy), xycoords=ax_b.get_yaxis_transform(),
                  xytext=(0, -B_DROP - h_pt), textcoords="offset points", ha="left", va="top", fontsize=LAB, color=INK, linespacing=1.1,
                  annotation_clip=False)
    ax_b.annotate("", xy=(vx, vy), xycoords="data", xytext=(0, -B_DROP + 1.0), textcoords="offset points",
                  arrowprops=dict(arrowstyle="-", color=ANN, linewidth=0.6, shrinkA=0, shrinkB=3.5), zorder=2)
    b1x = ax_b.transData.transform(b["hx"].xy()[:2])[0] * 72.0 / fig.dpi
    if head.get_window_extent(rend).x0 * 72.0 / fig.dpi - b1x < MARK_HALF_PT["haiku"] + 6.0:
        raise ValueError("FIG-00 panel B: the vote's label comes within 6 pt of Test B1's marker")
    _fig00_off(ax_b, b["om"], 0.0, 9, -1, "Opus-medium", "left", T_O)
    # the divider: midway between the right end of everything panel A draws and the left end of panel B's accuracy title and ticks
    in_px = fig.dpi
    fig.canvas.draw()                    # the tick labels and axis titles are laid out at the first draw
    a_right = max([ax_a.get_window_extent(rend).x1] + [t.get_window_extent(rend).x1 for t in ax_a.texts if t.get_text().strip()])
    b_left = min([ax_b.yaxis.label.get_window_extent(rend).x0] + [t.get_window_extent(rend).x0 for t in ax_b.get_yticklabels()])
    if (b_left - a_right) / in_px < 2 * DIVIDER_GAP:
        raise ValueError(f"FIG-00: only {(b_left - a_right) / in_px:.2f} in between panel A's furthest label and panel B's accuracy title: no room for the divider")
    xd = (a_right + b_left) / 2.0 / (6.5 * in_px)
    fig.add_artist(Line2D([xd, xd], [0.5 * M_B / FIG_H, 1 - 0.1 / FIG_H], transform=fig.transFigure, color=CONTEXT, linewidth=0.5))

    # ---------------- alt text and caption facts
    def acc(p: P) -> Cell:
        return joined(pct(p.acc, dp=1, from_proportion=False), label("%"), sep="")

    def cst(p: P) -> Cell:
        return joined(label("$"), usd(p.cost), sep="")

    def two(what: str, fn) -> List[Cell]:
        return [fn(a[(what, "1x6")]), label("and"), fn(a[(what, "6x1")])]

    exact_fa4 = any(p.exact == "fa4" for p in list(a.values()) + list(b.values()))
    word = {"hm": "the Haiku-medium sample", "hx": "the Haiku-max sample", "vote": "the vote", "om": "Opus-medium"}
    word_b = {"hm": "the Haiku-medium sample", "hx": "the Haiku-max sample (Test B1)", "vote": "the vote (Test B2)", "om": "Opus-medium"}

    def over_words(letter: str) -> str:
        """The points of one panel whose bar is not drawn (the per-arm test, per point): 'Opus-medium (pieces), the Haiku-max sample
        (chains)'; every point of the panel is named 'every point'."""
        d = over_names[letter]
        if letter == "B" and len(d) == 4:
            return "every point"
        if letter == "B":
            return ", ".join(word_b[w] for w in word_b if w in d)
        return ", ".join(word[w] + f" ({'both shapes' if len(d[w]) == 2 else d[w][0]})" for w in word if w in d)

    over_bits = [f"in panel {letter}: {over_words(letter)}" for letter in ("A", "B") if over_names[letter]]
    over_which = ([label("a bar that does not stick out past its marker is not drawn (" + "; ".join(over_bits) + ")")] if over_bits else [])
    n_hx = integer(S.ref("s1b", "constants.designed_tries.hx"))
    alt: List[Cell] = [
        label("Two panels of accuracy (%) against cost per answer ($, log scale), with a key in dark grey above panel A only (filled marks: "
              "chains; hollow marks: pieces). Panel A, Study 1 at 6 steps, shows chains as filled marks and "
              "pieces as hollow marks, the two shapes' marks of one setting set slightly apart sideways. One Haiku-medium sample scores"), *two("hm", acc), label("on chains and pieces, at"), *two("hm", cst),
        label("per answer. The cost-matched Haiku-medium vote, of"), integer(ks["1x6"]), label("samples on chains and"), integer(ks["6x1"]),
        label("on pieces, scores"), *two("vote", acc), label("at"), *two("vote", cst), label(". One Opus-medium answer scores"),
        *two("om", acc), label("at"), *two("om", cst), label(". The vote minus Opus-medium is"), d_test["1x6"],
        label("points on chains (Test 2) and"), d_test["6x1"],
        label("on pieces (Test 1), read by the pre-registered decision rule, not Holm-adjusted. One Haiku-max sample (exploratory‡) scores"),
        *two("hx", acc), label("at"), *two("hx", cst),
        label(". Unlabelled arrows run from the Haiku-medium sample to the vote and to the Haiku-max sample on each shape; the arrows to "
              "the Haiku-max sample are marked † (post hoc, our reading, not a test). Panel B, Study 1b at 16 steps, is titled shapes pooled: its filled marks pool chains and pieces. One Haiku-medium sample scores"),
        acc(b["hm"]), label("at"), cst(b["hm"]), label("; one Haiku-max sample (Test B1) scores"), acc(b["hx"]), label("at"), cst(b["hx"]),
        label("; the vote of"), integer(kb2), label("Haiku-max samples (Test B2, estimated from"), n_hx, label("samples) scores"), acc(b["vote"]),
        label("at"), cst(b["vote"]), label("; one Opus-medium answer scores"), acc(b["om"]), label("at"), cst(b["om"]),
        label(", so the vote minus Opus-medium is"), d_b2, label("points (Holm-adjusted); every mark in panel B is at its measured cost, and "
                                                                 "the vote's circle, drawn in front, overlaps Opus-medium's diamond in part. "
                                                                 + ("A 95% bar that does not stick out past its marker is not drawn (" + "; ".join(over_bits) + "). "
                                                                    if over_bits else "")
                                                                 + "The two panels use different puzzle sets and lengths and no test compares them.")]
    # B2's cost beside Opus-medium's per shape (Edith's label: more on chains, less on pieces), as spend shares at three decimals (§2.1)
    b2c = "costs_beside_tests.B2"
    share = {sh: num_d(derive("the vote's list cost over Opus-medium's on this shape",
                              lambda v, o: v / o, S.ref("s1b", f"{b2c}.challenger.{sh}.list_usd"), S.ref("s1b", f"{b2c}.comparator.{sh}.list_usd")),
                       dp=3) for sh in ("1x16", "16x1")}
    # the cost-matched vote sizes of Tests 1 and 2 and their spend shares, as Table 2 prints them (the vote's list cost over Opus-medium's)
    spend = {sh: num(S.ref("main", f"reporting.group_b.item_8b.realised_spend.tests.{test_of[sh]}.by_row.k+0.haiku_over_comparator"), dp=3)
             for sh in ("1x6", "6x1")}
    kcap = S.get("main_k", "k_from_rows.opus.6x1.capped")
    k_cells = [label("cost-matched votes: $k$ ="), integer(ks["1x6"]), label(f"samples on chains ({test_name['1x6']}; the vote costs"), spend["1x6"],
               label("of one Opus-medium answer's list cost) and"), integer(ks["6x1"]), label(f"on pieces ({test_name['6x1']};")]
    if kcap:
        k_cells += [label("capped at the samples drawn, raw $k$"), integer(S.ref("main_k", "k_from_rows.opus.6x1.raw_k")), label(";")]
    k_cells += [label("the vote costs"), spend["6x1"], label("of Opus-medium's); Test B2's vote, $k$ ="), integer(kb2), label(", costs"),
                num(S.ref("s1b", f"{b2c}.ratio_challenger_over_comparator"), dp=3), label("of one Opus-medium answer's list cost, pooled")]
    # Required labels carry their plain key; optional detail (counts) carries the prefix "detail_" so that Vision can fit the required ones
    # into the cap and drop the rest first.
    caption = {
        "tier": [label("descriptive summary; each study keeps its own panel and no reading crosses the panels (our reading, not a test): the "
                       "vote points are the challengers of confirmatory tests, Tests 1 and 2 in Study 1 and Test B2 in Study 1b; one "
                       "Haiku-max sample is exploratory‡ in Study 1 and Test B1's challenger in Study 1b; one Haiku-medium sample is "
                       "pre-specified descriptive (not tested)")],
        "values": [label("printed values, in points: $d$, the vote minus one Opus-medium answer (Tests 1 and 2: pre-registered decision rule, "
                         "not Holm-adjusted; Test B2: Holm-adjusted); the arrows carry no values: those to the Haiku-max sample are "
                         "post hoc† (our reading, not a test), those to the vote show pre-specified descriptive results")],
        "study": [label("Study 1 (main run, 6 steps; chains filled, pieces hollow, as the key above panel A says) and Study 1b (16 steps; "
                        "both shapes pooled, as panel B's title says)")],
        "k": k_cells,
        "b2": [label("Test B2's vote is estimated from"), n_hx, label("samples per puzzle and shape; it costs"), share["1x16"],
               label("times Opus-medium's list cost per answer on chains and"), share["16x1"], label("on pieces (more on chains, less on pieces)")],
        "interval": [label("95% bars: exact (Clopper–Pearson) for one Opus-medium answer in Study 1"
                           + (" and, post hoc†, wherever free analysis 4 replaces a collapsed bootstrap" if exact_fa4 else "")
                           + "; cluster bootstrap otherwise")],
        "bars": over_which,
        "marks": [label("marks are drawn at their measured costs, except that in panel A the two shapes of one setting, whose marks would "
                        "overlap, are each set sideways by about eight percent of cost, so that each such pair looks about seventeen percent "
                        "further apart than measured; panel B has no shift: the vote's circle, drawn in front, overlaps Opus-medium's diamond "
                        "in part, at the measured costs")],
        "price": [label("list price per answer (Batch, which we used, bills half)")],
        "title_n": [label("panel A's title: Study 1's main set of"), n_main, label("puzzles")],
        "detail_n": [label("puzzles: Study 1"), integer(S.ref("main", f"{T24}.table['opus-med 1x6'].base_puzzles")),
                     label("per shape; Study 1b"), integer(S.ref("s1b", "descriptive.arms['om@16'].1x16.n_base")),
                     label("per shape, pooled over the two shapes")]}
    if any(layout[id(ax)] != (ax.get_ylim(), tuple(ax.get_position().bounds)) for ax in (ax_a, ax_b)):
        raise ValueError("FIG-00: an axis's limits or position changed after its marks were drawn: the bar rule (`_fig0001_bar_hidden`) read the old ones")
    return FigureOut(fig, points, tight(alt), tight_caption(caption))
