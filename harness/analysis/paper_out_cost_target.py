"""TAB-34, cost for a target accuracy (appendix; the user's F-11 choice, D-132: "a post hoc cost-for-target table, cheapest arm whose
point, and whose lower end, clears 90%, 95%, 98%, goes in the appendix"). A post hoc reading on point estimates and stamped intervals:
nothing is fitted, no frontier is drawn, every row is labelled by tier and study, and points from different studies, sets and run
windows sit side by side only as "our reading, not a test".

The candidates are every measured setup with a stamped accuracy, interval and list cost per answer, per length (6 and 16 steps) and shape:
- 6 steps, Study 1 (main set, 80 bases): item 24's single-call arms and E3; the Haiku-medium vote line (item 24's chart, k = 2-40);
  Haiku-max's 3-try vote (item 24, vote at its own k);
- 6 steps, Study 1b (ext40 set, 40 bases): the effort sweep's arms at 6 steps; Haiku-max's vote at k = 2-10 (free analysis 2, post hoc;
  its cost is k times Haiku-max's cost per answer);
- 6 steps, the top-up run (Study 1 set, its own window): the team (E2), the picker with its samples, C13 (pieces);
- 16 steps, Study 1b (main 16-step set, 80 bases): the effort sweep's arms at 16 steps; Haiku-max's vote at k = 2-10 (its stamped curve).
"Clears" is "at or above the target". The lower end is the stamped 95% interval's: cluster bootstrap over base puzzles for the Haiku arms
with several tries per base puzzle and for every vote; Clopper–Pearson for the arms with one try per base puzzle (Opus and Sonnet); the
Clopper–Pearson end from free analysis 4 (post hoc) where a bootstrap collapsed to one value, read with core.fa4_exact for that very
stamped interval. Revision 2 of free analysis 4 takes every zero-width interval in this table's source files by rule (it leaves out only
the length sweep's q and item 20 below k = 40, neither of which is read here), so a collapsed interval it lacks stops the build: no
candidate is left out of the lower-end ranking. A note names and counts the candidates whose lower end is exact. Each row prints its
interval type; format compliance sits beside accuracy (for a vote, that of the tries it is drawn from). The table is long, in two blocks
(Edith's Q21: reshaped rather than set landscape): first the cheapest setup whose point clears each target, then the cheapest whose lower
end does, the first column naming the block on every row. Printed names are plain (the top-up's team, picker and step voting on pieces;
Study 1's step voting); the internal codes stay in the keys.

PLAN NOTE (source keys): the plan also lists item_9c and free analysis 3. Neither holds an accuracy: item 9c stamps costs per correct
answer and free analysis 3 stamps B2's paired differences and cost ratios by k, so neither can make or rank a candidate and neither is
read. Free analysis 11 is this table itself.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

from .paper_out_core import (EMPTY, Cell, Derived, Fa4Cell, Ref, Store, Table, ci_refs, dec, derive, fa4_exact, fmt_sf, integer, joined,
                             label, num, num_d, output, pct, text_of, usd)
from .paper_out_fa_checks import check_paper_words
from .paper_out_names import STUDY1_ARMS, STUDY1B_TAGS, shape, shape_word

T24 = "reporting.group_b.item_24"
FRT = "descriptive.format_refusals_truncations_missing.format_report"
STUDY1_SINGLE = ("haiku-thinking-off", "haiku-low", "haiku-med", "haiku-max", "sonnet-low", "sonnet-med", "opus-low", "opus-med")
STUDY1_EXPLORATORY = {"haiku-thinking-off", "haiku-low", "haiku-max", "sonnet-low"}
S1B_6 = ("ho", "hl", "hm", "hh", "hxh", "hx", "sl", "sm", "sh", "sxh", "sx", "ol", "om", "oh", "oxh", "ox")
S1B_16 = ("ho", "hl", "hm", "hh", "hxh", "hx", "om")
# The top-up arms in plain names (the internal codes stay in the keys): the team of Haiku tries, the picker with its samples, and step
# voting on pieces (the top-up's step voting ran on pieces only; checked in `candidates`).
TOPUP = (("e2", "e2", "the Haiku team"), ("h-pick8", "h-pick8-total", "the picker with its samples"),
         ("c13", "c13", "step voting on pieces"))
PLAIN_NAME = {"e3": "Step voting"}                  # Study 1's step voting by its plain name (the shared display name holds a code)
S1, S1B6, S1B16, TOP = "Study 1, main set", "Study 1b, 6-step set", "Study 1b, 16-step set", "top-up run, Study 1 set"

# Interval types, printed per row (the style sheet, D-122: the interval type is stated)
BOOT = "cluster bootstrap"
CP = "Clopper–Pearson (exact)"
CP_FA4 = "Clopper–Pearson (exact; free analysis 4, post hoc)"
S1B_INTERVAL = {"cluster bootstrap": BOOT, "clopper-pearson": CP}       # the stamped `interval` values of Study 1b's arms
DASH = label("—")


Pool = Tuple[str, List[Cell], Ref]


class Cand:
    """One candidate setup at one length and shape. `pool` names the tries behind it (for the caption's n): a key, its cells and the
    stamped count of base puzzles."""

    def __init__(self, name: str, study: str, tier: Cell, acc: Ref, cost: Union[Ref, Derived], itype: Cell, fc: Optional[Ref],
                 pool: Pool, k: Optional[Ref] = None):
        self.name, self.study, self.tier, self.k = name, study, tier, k
        self.acc, self.cost, self.fc, self.pool = acc, cost, fc, pool
        self.itype = itype
        self.lo: Optional[Ref] = None
        self.lo_scale = 1.0
        self.collapsed: Tuple[Ref, ...] = ()        # the stamped interval's two ends, when it collapsed to one value
        self.exact: Optional[Fa4Cell] = None        # then free analysis 4's exact interval, which gives the lower end

    @property
    def a(self) -> float:
        return float(self.acc.value)

    @property
    def l(self) -> Optional[float]:
        return None if self.lo is None else float(dec(self.lo.value) * dec(self.lo_scale))

    @property
    def c(self) -> float:
        return float(self.cost.value)

    def cost_cell(self) -> Cell:
        if isinstance(self.cost, Ref):
            return usd(self.cost)
        return Cell(fmt_sf(self.cost.value, 3), raw=self.cost.value, refs=self.cost.refs, formula=self.cost.formula)

    def name_cell(self) -> Cell:
        if self.k is None:
            return label(self.name)
        return joined(label(self.name + ", k = "), integer(self.k), sep="")


def _interval(S: Store, c: Cand, src: str, ci_dict: str) -> Cand:
    """Sets the candidate's lower end from the stamped 95% interval at `ci_dict`.ci95 (`ci_dict` is the stamped dict holding ci95, in
    the ledger's key syntax); where it collapsed to one value, from free analysis 4's exact interval for that very stamped interval
    (core.fa4_exact, which checks the cell is fa4's copy of it), scaled to points. Free analysis 4's revision 2 takes every zero-width
    interval in this table's source files by rule, so a collapsed interval with no exact one is an error, not a row to leave out."""
    lo, hi = ci_refs(S, src, ci_dict + ".ci95")
    if lo.value != hi.value:
        c.lo = lo
        return c
    fe = fa4_exact(S, src, ci_dict)
    if fe is None:
        raise ValueError(f"{src}:{ci_dict}.ci95 collapsed to one value and free analysis 4 has no exact interval for it, though its "
                         "revision 2 takes every zero-width interval in this table's source files: check fa4 before printing a dash")
    # the exact cell must be this setup's: its stamped mean, in points, is the candidate's accuracy, over the same base puzzles
    if dec(S.get("fa4", fe.base + ".stamped_mean")) * dec(fe.scale) != dec(c.acc.value):
        raise ValueError(f"free analysis 4 {fe.base}: stamped mean is not {c.name}'s accuracy {c.acc.value}")
    if fe.n != int(c.pool[2].value):
        raise ValueError(f"free analysis 4 {fe.base}: n = {fe.n} puzzles, not {c.name}'s {c.pool[2].value}")
    c.lo, c.lo_scale, c.itype, c.collapsed, c.exact = fe.lo, fe.scale, label(CP_FA4), (lo, hi), fe
    return c


def _s1_pool(S: Store, arm: str, sh: str) -> Pool:
    row = f"{T24}.table['{arm} {sh}']"
    nb = S.ref("main", row + ".base_puzzles")
    cells = [label(f"{S1}, {STUDY1_ARMS[arm][0]}: "), integer(nb), label(" puzzles")]
    if S.has("main", row + ".refusals_and_truncations.tries"):
        per = derive("samples / puzzles", lambda t, b: t / b, S.ref("main", row + ".refusals_and_truncations.tries"), nb)
        cells += [label(", "), num_d(per, dp=0), label(" sample each" if per.value == 1 else " samples each")]
    return f"{S1}|{arm}", cells, nb


def _s1b_pool(S: Store, tag: str, n: int, study: str, n_base: Ref) -> Pool:
    per = S.ref("s1b", f"descriptive.arms['{tag}@{n}'].tries_per_item")
    return f"{study}|{tag}", [label(f"{study}, {STUDY1B_TAGS[tag][0]}: "), integer(n_base), label(" puzzles, "), integer(per),
                              label(" sample each" if per.value == 1 else " samples each")], n_base


def _need_bootstrap(S: Store, src: str, key: str) -> None:
    """A vote or multi-try interval printed as a cluster bootstrap must carry a stamped bootstrap name."""
    if not S.get(src, key):
        raise ValueError(f"{src}:{key}: no stamped bootstrap name")


def candidates(S: Store, n: int, sh: str) -> List[Cand]:
    out: List[Cand] = []
    if n == 6:
        for arm in STUDY1_SINGLE + (("e3",) if sh == "1x6" else ()):
            row = f"{T24}.table['{arm} {sh}']"
            tier = label("Study 1, exploratory setting" if arm in STUDY1_EXPLORATORY else "Study 1, pre-specified descriptive (item 24)")
            fc = S.ref("main", row + ".format_compliance.format_compliance") if S.get("main", row + ".format_compliance") else None
            name = PLAIN_NAME.get(arm, STUDY1_ARMS[arm][0]) + (ONE_SAMPLE if arm != "e3" else "")
            if S.has("main", row + ".accuracy_cp95"):
                c = Cand(name, S1, tier, S.ref("main", row + ".accuracy_mean"), S.ref("main", row + ".cost_per_puzzle.mean"), label(CP),
                         fc, _s1_pool(S, arm, sh))
                c.lo = S.ref("main", row + ".accuracy_cp95.cp95.0")
            else:
                _need_bootstrap(S, "main", row + ".accuracy_interval.bootstrap_name")
                c = _interval(S, Cand(name, S1, tier, S.ref("main", row + ".accuracy_mean"), S.ref("main", row + ".cost_per_puzzle.mean"),
                                      label(BOOT), fc, _s1_pool(S, arm, sh)),
                              "main", row + ".accuracy_interval")
            out.append(c)
        if S.get("main", f"reporting.group_b.item_8b.vote_curve['{sh}'].arm") != "haiku-med":     # item 24's vote line is item 8b's curve
            raise ValueError(f"item 8b's vote curve ({sh}) is not Haiku-medium's")
        _need_bootstrap(S, "main", f"reporting.group_b.item_8b.vote_curve['{sh}'].bootstrap_name")
        hm =f"{T24}.table['haiku-med {sh}']"
        for i, p in enumerate(S.get("main", f"{T24}.chart.{sh}.haiku_med_vote_line")):
            if int(p["k"]) < 2:
                continue
            base = f"{T24}.chart.{sh}.haiku_med_vote_line.{i}"
            c = Cand("Haiku-medium vote", S1, label("Study 1, pre-specified descriptive (vote curve)"), S.ref("main", base + ".accuracy"),
                     S.ref("main", base + ".cost_per_puzzle"), label(BOOT), S.ref("main", hm + ".format_compliance.format_compliance"),
                     _s1_pool(S, "haiku-med", sh), k=S.ref("main", base + ".k"))
            out.append(_interval(S, c, "main", base))
        hx = f"{T24}.table['haiku-max {sh}']"
        hv = hx + ".vote_at_own_k['own k vs opus-med']"
        _need_bootstrap(S, "main", hv + ".bootstrap_name")
        c = Cand("Haiku-max vote", S1, label("Study 1, exploratory setting"), S.ref("main", hv + ".mean"), S.ref("main", hv + ".cost_per_puzzle.mean"),
                 label(BOOT), S.ref("main", hx + ".format_compliance.format_compliance"), _s1_pool(S, "haiku-max", sh),
                 k=S.ref("main", hv + ".k"))
        out.append(_interval(S, c, "main", hv))
        for tag in S1B_6:
            a = f"descriptive.arms['{tag}@6'].{sh}"
            if not S.has("s1b", a):
                continue
            itype = S.get("s1b", a + ".interval")
            c = Cand(STUDY1B_TAGS[tag][0] + ONE_SAMPLE, S1B6, label("Study 1b, pre-specified descriptive (effort sweep)"),
                     S.ref("s1b", a + ".mean"), S.ref("s1b", a + ".cost_per_answer"),
                     text_of(S.ref("s1b", a + ".interval"), {itype: S1B_INTERVAL[itype]}), S.ref("s1b", f"{FRT}.{tag}.{sh}.format_compliance"),
                     _s1b_pool(S, tag, 6, S1B6, S.ref("s1b", a + ".n_base")))
            out.append(_interval(S, c, "s1b", a))
        cost1 = S.ref("fa2", f"result['N=6'].hx_cost_per_answer.{sh}.list_usd")
        if S.get("fa2", f"result['N=6'].hx_cost_per_answer.{sh}.list_usd") != S.get("s1b", f"descriptive.arms['hx@6'].{sh}.cost_per_answer"):
            raise ValueError(f"free analysis 2's Haiku-max cost per answer ({sh}) is not Study 1b's")
        for i, p in enumerate(S.get("fa2", "result['N=6'].curve")):
            k = int(p["k"])
            if k < 2:
                continue
            base = f"result['N=6'].curve.{i}.{sh}"
            _need_bootstrap(S, "fa2", base + ".bootstrap_name")
            kref = S.ref("fa2", f"result['N=6'].curve.{i}.k")
            cost = derive("k * Haiku-max list cost per answer", lambda c_, kk: kk * c_, cost1, kref)
            c = Cand("Haiku-max vote", S1B6, label("post hoc (free analysis 2)"), S.ref("fa2", base + ".mean"), cost, label(BOOT),
                     S.ref("s1b", f"{FRT}.hx.{sh}.format_compliance"), _s1b_pool(S, "hx", 6, S1B6, S.ref("fa2", base + ".n_base")), k=kref)
            out.append(_interval(S, c, "fa2", base))
        for arm, cost_arm, nm in TOPUP:
            if not S.has("topup", f"accuracy.{arm}.{sh}"):
                continue
            if arm == "c13" and shape_word(sh) != "pieces":
                raise ValueError(f"the top-up's step voting has a {sh} row: its plain name 'step voting on pieces' would be wrong")
            _need_bootstrap(S, "topup", f"accuracy.{arm}.{sh}.bootstrap_name")
            # no per-arm format-compliance share is stamped for the top-up arms (a dash if one were ever picked)
            nb = S.ref("topup", f"accuracy.{arm}.{sh}.n_base")
            c = Cand(nm, TOP, label("exploratory (top-up run)"), S.ref("topup", f"accuracy.{arm}.{sh}.mean"),
                     S.ref("topup", f"costs.per_puzzle.{cost_arm}.{sh}.mean"), label(BOOT), None,
                     (f"{TOP}|{arm}", [label(f"{TOP}, {nm}: "), integer(nb), label(" puzzles")], nb))
            out.append(_interval(S, c, "topup", f"accuracy.{arm}.{sh}"))
    else:
        for tag in S1B_16:
            a = f"descriptive.arms['{tag}@16'].{sh}"
            if not S.has("s1b", a):
                continue
            itype = S.get("s1b", a + ".interval")
            c = Cand(STUDY1B_TAGS[tag][0] + ONE_SAMPLE, S1B16, label("Study 1b, pre-specified descriptive (effort sweep)"),
                     S.ref("s1b", a + ".mean"), S.ref("s1b", a + ".cost_per_answer"),
                     text_of(S.ref("s1b", a + ".interval"), {itype: S1B_INTERVAL[itype]}), S.ref("s1b", f"{FRT}.{tag}.{sh}.format_compliance"),
                     _s1b_pool(S, tag, 16, S1B16, S.ref("s1b", a + ".n_base")))
            out.append(_interval(S, c, "s1b", a))
        if S.get("s1b", "descriptive.vote_curve_n16.arm") != "hx" or not S.get("s1b", "descriptive.vote_curve_n16.bootstrap_names"):
            raise ValueError("Study 1b's 16-step vote curve is not Haiku-max's bootstrapped curve")
        k_b2 = S.ref("s1b_k", "k")
        for i, p in enumerate(S.get("s1b", "descriptive.vote_curve_n16.points")):
            k = int(p["k"])
            if k < 2:
                continue
            base = f"descriptive.vote_curve_n16.points.{i}.{sh}"
            kref = S.ref("s1b", f"descriptive.vote_curve_n16.points.{i}.k")
            if k == int(k_b2.value):
                tier = joined(label("Study 1b, pre-specified descriptive (vote curve, at B2's k = "), integer(k_b2), label(")"), sep="")
            else:
                tier = label("Study 1b, pre-specified descriptive (vote curve)")
            c = Cand("Haiku-max vote", S1B16, tier, S.ref("s1b", base + ".mean"), S.ref("s1b", base + ".cost_per_answer"), label(BOOT),
                     S.ref("s1b", f"{FRT}.hx.{sh}.format_compliance"), _s1b_pool(S, "hx", 16, S1B16, S.ref("s1b", base + ".n_base")), k=kref)
            out.append(_interval(S, c, "s1b", base))
    return out


def _pick(cands: List[Cand], target: float, by: str) -> Optional[Cand]:
    """The cheapest candidate whose point (or lower end) is at or above the target."""
    ok = [c for c in cands if (c.a >= target if by == "point" else (c.l is not None and c.l >= target))]
    return min(ok, key=lambda c: (c.c, c.name)) if ok else None


WIDTH = 8   # cells per pick: setting, study and set, label, accuracy, format compliance, lower end, interval type, cost
BLOCKS = (("point", "point estimate"), ("lower", "95% lower end"))      # the two blocks: how a setup clears, in the first column's words


def _cells(c: Optional[Cand], t: float) -> List[Cell]:
    if c is None:
        # the row says so in its setting cell; every cell of the numbers is a dash (the split's number part would otherwise show an
        # empty row), and the study and label cells stay empty because there is no setting to name them for
        return [label("no measured setting clears"), EMPTY, EMPTY] + [DASH] * (WIDTH - 3)
    b = (0.0, t, 100.0)        # one more decimal where rounding would put a value on the target (or on 0 or 100)
    lo = num(c.lo, dp=2, scale=c.lo_scale, bounds=b) if c.lo is not None else DASH
    fc = pct(c.fc, dp=2, bounds=(100.0,)) if c.fc is not None else DASH
    return [c.name_cell(), label(c.study), c.tier, num(c.acc, dp=2, bounds=b), fc, lo, c.itype, c.cost_cell()]


# The paper's version (D-159, D-160; Vision's plan §3: Target · cheapest setting (point) · cheapest setting (lower end), at 6 and 16
# steps; D-161): each pick named in the paper's words with its study and label in parentheses, so that every entry still names its
# study and label (the caption's and the Discussion appendix's "every row labelled by tier and study"); the puzzle set is the study's
# own at that length (a short note says so). Accuracy, lower end, format compliance and interval type stay in the supplement; each pick's
# list cost per answer is printed beside it (Edith, proof 2: the caption promises it). The steps are a "Steps" column (bare 6 or 16,
# the unit in the header), second after Shape, with the rows in the columns' order: shape, then steps, then target. Four row groups
# (chains at 6 and 16 steps, pieces at 6 and 16), the shape and the steps printed once per group, a little space between rows (Edith §7.7). (The full table's rows are grouped by length and shape too: see `t.groups` in tab_34.)
# The label of a pick is printed only where it is not the plain one (Edith, proof 2): none for pre-specified descriptive, else the words
# "post hoc" or "exploratory" after the study, defined once in the note (the figures' marks † and ‡ have no LaTeX form in the writer).
PAPER_STUDY = {S1: "Study 1", S1B6: "Study 1b", S1B16: "Study 1b", TOP: "top-up run"}
PAPER_LABELS = ("pre-specified descriptive", "exploratory", "post hoc")      # the label words of the Method's legend
PAPER_PRINTED = {"pre-specified descriptive": "", "exploratory": ", exploratory", "post hoc": ", post\u00a0hoc"}   # after the study
PAPER_SHAPE = {"chain": "chains", "pieces": "pieces"}       # the cells say "chains", as the prose does (Edith, p. 38)
ONE_SAMPLE = ", one sample"


def _paper_label(tier: Cell) -> str:
    """The legend's label word of a candidate's typed tier cell (exactly one of PAPER_LABELS, or the build stops)."""
    hits = [w for w in PAPER_LABELS if w in tier.printed]
    if len(hits) != 1:
        raise ValueError(f"TAB-34 paper version: the tier {tier.printed!r} names {len(hits)} of the legend's labels {PAPER_LABELS}")
    return hits[0]


def _paper_pick(c: Optional[Cand]) -> Cell:
    """One pick in the paper's words (D-161: "sample" for try, "setting" for setup): 'one Haiku-max sample (Study 1b)', or
    'Haiku-max vote, k = 3 (Study 1b, post hoc)' with k read from its source. The plain label (pre-specified descriptive) is not
    printed; the others follow the study (PAPER_PRINTED), "post hoc" never breaking."""
    if c is None:
        return label("no measured setting clears")
    where = f" ({PAPER_STUDY[c.study]}{PAPER_PRINTED[_paper_label(c.tier)]})"
    if c.k is not None:
        return joined(label(c.name + ", k = "), integer(c.k), label(where), sep="")
    if c.name.endswith(ONE_SAMPLE):
        base = c.name[:-len(ONE_SAMPLE)]
        return label((f"{base}, one sample" if "," in base else f"one {base} sample") + where)
    return label(c.name + where)


def _paper_cost(c: Optional[Cand]) -> Cell:
    """A pick's list cost per answer (US dollars, three significant figures, as the full table prints it); a dash where nothing clears."""
    return c.cost_cell() if c is not None else DASH


def _paper_steps(S: Store, n: int) -> Cell:
    """The length as a bare number under the header "Steps" (units in the header, never in the cells: spec rule 3, polish §7.4), in
    the second column, so the writer aligns it right (it sets the first column, Shape, flush left), as TAB-01's paper version does. Its
    number is read from Study 1b's Haiku-max arm at that length (its stamped N); at 6 steps Study 1's main analysis (whose settings, and
    the top-up run's, are candidates there too) must be at 6 steps as well."""
    r = S.ref("s1b", f"descriptive.arms['hx@{n}'].N")
    if r.value != n or (n == 6 and S.get("main", "n") != 6):
        raise ValueError(f"TAB-34 paper version: the stamped length {r.value} is not {n} steps")
    return integer(r)


def _seq(parts: Sequence[List[Cell]], sep: str = "; ") -> List[Cell]:
    out: List[Cell] = []
    for i, p in enumerate(parts):
        if i:
            out.append(label(sep))
        out += p
    return out


def _flat(*parts: Union[str, Cell, List[Cell]]) -> List[Cell]:
    out: List[Cell] = []
    for p in parts:
        out += [label(p)] if isinstance(p, str) else (p if isinstance(p, list) else [p])
    return out


def _line(*parts: Union[str, Cell, List[Cell]]) -> List[Cell]:
    """A note or caption line as one printed cell (strings are labels; every number keeps its source and key)."""
    return [joined(*_flat(*parts), sep="")]


def _k_range(S: Store, src: str, key: str) -> List[Cell]:
    """'2 to 40': the first vote size of at least 2 and the last, read from the curve at `key`."""
    pts = S.get(src, key)
    first = min(i for i, p in enumerate(pts) if int(p["k"]) >= 2)
    return [integer(S.ref(src, f"{key}.{first}.k")), label(" to "), integer(S.ref(src, f"{key}.{len(pts) - 1}.k"))]


def _pool_note(S: Store) -> List[Cell]:
    hv = f"{T24}.table['haiku-max 1x6'].vote_at_own_k['own k vs opus-med'].k"
    if S.get("main", hv) != S.get("main", f"{T24}.table['haiku-max 6x1'].vote_at_own_k['own k vs opus-med'].k"):
        raise ValueError("Study 1's Haiku-max own-k vote has a different k per shape")
    return _line("Candidates (every measured setting with a stamped accuracy, 95% interval and list cost per answer at that length and "
                 "shape): at 6 steps, Study 1's single-call settings and step voting (chains only), its Haiku-medium vote line (k = ",
                 _k_range(S, "main", f"{T24}.chart.1x6.haiku_med_vote_line"), ") and Haiku-max's vote of k = ", integer(S.ref("main", hv)),
                 " samples; Study 1b's effort-sweep settings on the 6-step set and Haiku-max votes of k = ",
                 _k_range(S, "fa2", "result['N=6'].curve"), " (free analysis 2, post hoc); the top-up run's Haiku team, its picker "
                 "(whose cost includes its samples) and its step voting (pieces only). At 16 steps, Study 1b's effort-sweep settings and "
                 "its Haiku-max vote curve (k = ", _k_range(S, "s1b", "descriptive.vote_curve_n16.points"), ").")


def _vote_note(S: Store) -> List[Cell]:
    def per(arm: str) -> Cell:
        row = f"{T24}.table['{arm} 1x6']"
        return num_d(derive("samples / puzzles", lambda t, b: t / b, S.ref("main", row + ".refusals_and_truncations.tries"),
                            S.ref("main", row + ".base_puzzles")), dp=0)
    return _line("Every vote row is estimated from the samples made per puzzle, not from separate runs of k calls: Study 1b's Haiku-max "
                 "votes from ", integer(S.ref("s1b", "descriptive.arms['hx@6'].tries_per_item")), " samples per puzzle on the 6-step "
                 "set and ", integer(S.ref("s1b", "descriptive.arms['hx@16'].tries_per_item")), " on the 16-step set (the expected "
                 "accuracy of a vote of k of them, a tie credited as a share split evenly among the tied answers); Study 1's Haiku-max "
                 "vote from its ", per("haiku-max"), " samples and its Haiku-medium vote line from ", per("haiku-med"), ". A vote's list "
                 "cost per answer is k times one sample's.")


@output("TAB-34")
def tab_34(S: Store) -> Table:
    from .paper_out_ops import extract
    content = None
    for i, e in enumerate(S.get("plan", "plan.tables_figures")):
        if e["id"] == "TAB-34":
            content = S.ref("plan", f"plan.tables_figures.{i}.content")
    tcells = [extract(content, r"(\d+)%, (\d+)% and (\d+)%", group=g) for g in (1, 2, 3)]     # the plan's targets, read, not typed
    targets = [(float(c.raw), c) for c in tcells]
    rows: List[List[Cell]] = []
    exact: List[Tuple[Cand, str]] = []
    picked: List[Cand] = []
    unmet = 0                                       # rows where no measured setup clears the target (the note says so only if any)
    # Long format in two blocks (Edith's Q21): first every pick by the point estimate, then every pick by the 95% lower end; the first
    # column names the block on every row.
    blocks: Dict[str, List[List[Cell]]] = {by: [] for by, _ in BLOCKS}
    # the paper's version: one row per shape, length and target, the two picks side by side; rows in the order of its columns (shape,
    # then steps, then target), so the first column changes once and the steps column once per shape
    paper_by: Dict[Tuple[str, int], List[List[Cell]]] = {}
    for n, shapes in ((6, ("1x6", "6x1")), (16, ("1x16", "16x1"))):
        steps = _paper_steps(S, n)
        for sh in shapes:
            cands = candidates(S, n, sh)
            if any(c.lo is None for c in cands):         # _interval stops on a collapsed interval with no exact one; never a dash here
                raise ValueError(f"a candidate at {n} steps, {sh}, has no lower end: no note says why")
            exact += [(c, sh) for c in cands if c.exact is not None]
            for t, tc in targets:
                picks: Dict[str, Optional[Cand]] = {}
                for by, word in BLOCKS:
                    c = _pick(cands, t, by)
                    picks[by] = c
                    picked += [c] if c is not None else []
                    unmet += c is None
                    blocks[by].append([label(word), label(f"{n} steps"), label(shape(sh)), tc, *_cells(c, t)])
                paper_by.setdefault((shape_word(sh), n), []).append(
                    [label(PAPER_SHAPE[shape_word(sh)]), steps, tc,
                     *[x for by, _ in BLOCKS for x in (_paper_pick(picks[by]), _paper_cost(picks[by]))]])
    rows = [r for by, _ in BLOCKS for r in blocks[by]]
    cols = ["Cleared by", "Length", "Shape", "Target (%)", "Cheapest setting that clears", "Study and set", "Label", "Accuracy (%)",
            "Format compliance (%)", "95% lower end (%)", "Interval type", "List cost per answer ($)"]
    if len(cols) != 4 + WIDTH:
        raise ValueError("TAB-34's columns do not match its cells")
    if any(c.lo is None for c in picked) or any(c.fc is None for c in picked):
        raise ValueError("a printed setup has no lower end or no format compliance: add the note that explains its dash")
    # Edith (proof 3, page log p. 131; polish §7.3): a column with one value in every row is a note, not a column. When every printed
    # row's interval is a cluster bootstrap the column goes and the note says so (the caption's interval fact already names the one type);
    # with any other mix the column stays.
    itypes = sorted({c.itype.printed for c in picked})
    drop_itype = itypes == [BOOT]
    if drop_itype:
        ij = cols.index("Interval type")
        cols = cols[:ij] + cols[ij + 1:]
        rows = [r[:ij] + r[ij + 1:] for r in rows]
    nb = (0.0,) + tuple(t for t, _ in targets) + (100.0,)      # one more decimal where rounding would put a value on a target, 0 or 100
    if exact:
        count = Cell(str(len(exact)), raw=len(exact),
                     refs=tuple(r for c, _ in exact for r in c.collapsed + (c.exact.lo, c.exact.hi)),
                     formula="count of candidates whose stamped 95% interval has zero width (both ends recorded); each one's lower "
                             "end is free analysis 4's exact interval for that very interval (its ends recorded)")
        items = [_flat(c.name_cell(), f", on {'chains' if shape_word(sh) == 'chain' else 'pieces'} ({c.study}; ", c.tier,
                       "): accuracy ", num(c.acc, dp=2, bounds=nb), "%, lower end ", num(c.lo, dp=2, scale=c.lo_scale, bounds=nb),
                       "% (exact, post hoc; ", integer(S.ref("fa4", c.exact.base + ".n")), " puzzles)") for c, sh in exact]
        collapsed = _line("Where a candidate's bootstrap interval collapsed to one value, its lower end is that of the exact "
                          "(Clopper–Pearson) 95% interval from free analysis 4 (post hoc) over the same puzzles, so no candidate is "
                          "left out of the lower-end ranking. That holds for ", count, " candidate: " if len(exact) == 1 else " candidates: ",
                          _seq(items), ".")
    else:
        collapsed = _line("No candidate's bootstrap interval collapsed to one value, so no lower end comes from free analysis 4 and no "
                          "candidate is left out of the lower-end ranking.")
    notes = [
        _line("Post hoc reading on point estimates and stamped 95% intervals: nothing is fitted and no frontier is drawn. Settings from "
              "different studies, puzzle sets and runs are compared only as our reading, not a test; each row names its study, set and "
              "label."),
        _line("Two blocks, named in the first column. In the first, a setting clears a target when its accuracy (the point estimate) is "
              "at or above the target; in the second, when the lower end of its 95% interval is at or above the target. Each row gives "
              "the cheapest setting that clears the target at that length and shape" + (", or says that no measured setting clears it "
                                                                                       "(a dash stands for each number it then lacks)"
                                                                                       if unmet else "") +
              ". Where rounding would put a value on the target, one more decimal is printed."),
        _pool_note(S),
        _vote_note(S),
        _line("Lower ends are those of the stamped 95% intervals over puzzles, as each setting's file stamps them: Clopper–Pearson "
              "(exact) for the Opus and Sonnet settings with one sample per puzzle; cluster bootstrap for every other setting (the Haiku "
              "settings, Study 1b's Opus-medium, step voting, the top-up designs and every vote); Clopper–Pearson from free analysis 4 "
              "(post hoc) where a bootstrap interval collapsed to one value. "
              + ("Every lower end printed in this table is that of a " + BOOT + "." if drop_itype else "Each row gives its interval type.")),
        _line("Format compliance is the share of answered samples in the required format; for a vote, that of the samples it is drawn "
              "from."),
        collapsed,
    ]
    order = {s: i for i, s in enumerate((S1, S1B6, S1B16, TOP))}
    picked.sort(key=lambda c: order[c.study])                                  # stable: within a study, the order of the rows
    pools: Dict[str, List[Cell]] = {}
    for c in picked:
        pools.setdefault(c.pool[0], c.pool[1])
    studies = sorted({c.study for c in picked}, key=lambda s: order[s])
    caption = {"tier": [label("post hoc reading on point estimates (first block) and stamped 95% lower ends (second block); every row "
                              "carries its study and its label; no fitted frontier")],
               "study": [label("the printed rows come from " + "; ".join(studies) + " (each row names its study and set)")],
               "n": _line("puzzles and samples per puzzle behind the printed rows: ", _seq(list(pools.values()))),
               "interval": [label("95% over puzzles; " + ("every printed row: " if len(itypes) == 1 else "per row, one of: ")
                                  + "; ".join(itypes))],
               "price": [label("US dollars per answer at list price")]}
    t = Table([label(c) for c in cols], rows, notes, caption)
    # the supplement's layout (Edith, proof 3, page log pp. 129-132: four portrait parts, each half a page, with a constant column):
    # two landscape pages, each row's identity (block, length, shape, target), setting, study, label and numbers together. The notes
    # print under the last part, which therefore holds the fewest rows: at \small the notes (about 2.9 in) and a block of 12 rows do not
    # fit one landscape page (7.8 in against 6.5), and a three-part split leaves a page at 60%; at \footnotesize (8 pt, the floor) the first
    # part takes the point-estimate block and the 6-step half of the lower-end block, the second the 16-step half of the lower-end block
    # (each of the four row groups is three targets of one length and shape).
    per_block = len(rows) // 2
    cut = per_block + per_block // 2
    t.layout = "split landscape"
    t.font = "footnotesize"
    t.split_key = [0, 1, 2, 3]
    ncol = list(range(4, len(cols)))
    t.split_parts = [(list(range(cut)), ncol), (list(range(cut, len(rows))), ncol)]
    t.share_widths = True       # the parts hold the same columns: one set of widths, so the same cell wraps alike in both (proof 4)
    t.once = [0, 1, 2]          # the block, the length and the shape print once per group of three rows (one target each)
    # row groups (Edith 7.7): a little space above the first of the three targets of each length and shape (the writer carries the groups
    # into the parts, dropping one that falls on a part's first row)
    t.groups = [i for i in range(1, len(rows)) if (rows[i][1].printed, rows[i][2].printed) != (rows[i - 1][1].printed, rows[i - 1][2].printed)]
    if [by for by, _ in BLOCKS] != ["point", "lower"]:
        raise ValueError("TAB-34 paper version: its two pick columns are the point block's, then the lower end's")
    order = [(w, n) for w in ("chain", "pieces") for n in (6, 16)]
    if sorted(paper_by) != sorted(order) or any(len(paper_by[k]) != len(targets) for k in order):
        raise ValueError(f"TAB-34 paper version: the shapes and lengths {sorted(paper_by)} are not chain and pieces at 6 and 16 steps, "
                         "one row per target")
    paper = [r for k in order for r in paper_by[k]]
    # Edith §7.5 (proof 2): the two printed notes take two lines together. The pick headers say how a setting clears (by its point
    # estimate or its 95% lower end) and the cost columns what each pick costs; the labels in the cells are defined here
    main_notes = [
        [label("Clears: at or above the target, by accuracy or by the 95% interval's lower end. A pick with no label is pre-specified "
               "descriptive.")],
        [label("At 6 steps, Study 1 and Study 1b used different puzzles; a vote of k samples costs k times one sample.")]]
    # the pick headers are the design's words, each on one line of its column; note 1 says what "clears" means. The cost headers are the
    # other paper tables' name for the quantity ("List cost per answer ($)", §3.1; §7.4's form, the caption's price fact says US dollars);
    # "per answer" is tied with a no-break space, so a wrapped header reads "List cost / per answer / ($)" (3 lines), not four (the width
    # the estimate gives the cost column)
    cost_head = "List cost per\u00a0answer ($)"
    t.main_table = check_paper_words(Table(
        [label(c) for c in ("Shape", "Steps", "Target (%)", "Cheapest setting (point estimate)", cost_head,
                            "Cheapest setting (95% lower end)", cost_head)],
        paper, main_notes, caption, short_notes=[0, 1], layout="float"), "TAB-34")
    # four groups (chains and pieces, 6 and 16 steps), the shape and the steps printed once per group, space between wrapped rows
    mt = t.main_table
    mt.groups = [i for i in range(len(targets), len(paper), len(targets))]
    mt.once = [0, 1]
    mt.spaced = True
    return t
