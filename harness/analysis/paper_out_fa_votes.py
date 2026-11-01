"""Free analyses 1, 3 and 7 (post hoc, labelled so): the plan's TAB-24 (same money, same puzzles: one Haiku-max try against a
lower-effort Haiku vote) and TAB-25 (B2's Haiku-max vote at every k, 16 steps). Every cell is read by key from the pinned files: the
free-analysis results `fa1`, `fa3` and `fa7` (and `fa4` only if a printed accuracy interval collapsed), with the stamped points of Study 1
(`main`) and Study 1b (`s1b`, `s1b_k`) beside them; see paper_out_core.py for the rules. Nothing is computed beyond unit changes and the
few products and ratios marked `derive`.

Units in these files: Study 1's item 24 (table and vote line), Study 1b's analysis.json and the free analyses hold accuracies and d in
points (0-100); format compliance is a share (0-1), printed in %; costs are US dollars at list price (Study 1 per puzzle, item 24;
Study 1b per answer, item 9b).

Tiers: every paired difference, k and cost ratio read from a free analysis is post hoc (free analyses 1, 3, 7: no p-value, no Holm, no
verdict; each row within one study; Study 1 and Study 1b never pooled). The points read from Study 1's item 24 and Study 1b's stamped
arms, vote curve and costs are pre-specified descriptive. Two kinds of cell are neither: Study 1b's lower-effort vote accuracies in
TAB-24's side panels are free analysis 1's (post hoc; Study 1b stamps no such vote), and those votes' costs are derived (k times the
stamped one-try cost). TAB-25's row at B2's own k (k.json) prints Test B2's stamped confirmatory pooled d and interval, unchanged, with
Test B2's stamped error ratio beside them (near the ceiling the error ratio travels with d; pre-specified descriptive, not part of the
test); its accuracy, format compliance and costs are pre-specified descriptive; free analysis 3's own interval for that vote is not
printed (one comparison, one interval), and its d is only checked against the stamped test. TAB-25 prints no per-shape d in its main
table; the per-shape d and intervals are the side panel's (each shape's own equal-money k, free analysis 3).
Every row's Tier cell and every table's (and panel's) caption say which is which.

Cost-ratio precision: a ratio that sets an equal-money k (one try's cost over another's) has 2 decimals; a vote's cost over
Opus-medium's (a spend ratio) has 3, as Study 1b's tables and the claims ledger quote B2's pooled and per-shape spend ratios.
"""

from __future__ import annotations

import math
from typing import Any, List, Sequence, Tuple

from .paper_out_core import (Cell, Ref, Source, Store, Table, ci_refs, derive, exact, fa4_exact, fmt_sf, integer, interval, join_key, joined, label,
                             num, num_d, output, pct, pvalue, pvalue_bound, FLOOR_NOTE, pts, register_source, text_of, usd)
from .paper_out_names import STUDY1B_TAGS, main_text, shape, shape_word
from .paper_out_overview import B_READING     # Study 1b's reading in the pre-registered decision rule's words, as TAB-01 prints it
from .paper_out_topup import flat, paper_decimals, paper_ids, paper_note_lengths

# The Study 1b specification, frozen with Lock 4 (pinned at the commit that last changed it on main; this module's own name, so that its
# pin does not depend on another module's): its list of outputs "Beside every test" names the error-rate ratio, the evidence for
# printing Test B2's error ratio as "pre-specified descriptive, reported beside the test" (Edith's Q14 ruling), never as confirmatory.
SPEC1B = register_source(Source("fa_votes_spec1b", "research/study1b-spec.md", "9c007e5",
                                "4b6779502c26ae1da96b55573b0f9e62d153caa4509ef543b748c5d70a72c879", kind="text",
                                what="The Study 1b specification, frozen with Lock 4 (the error-rate ratio beside every test)"))
ER_TIER = "pre-specified descriptive, reported beside the test"     # the error ratio's tier (Edith's Q14 ruling)

DASH = label("—")                                   # not stamped / does not apply
TOL = 1e-9                                          # float tolerance for the consistency checks (never used to print)
SHAPES1 = ("1x6", "6x1")                            # Study 1: chain, pieces
LOWER_TAGS = ("hm", "hh", "hxh")                    # free analysis 1's lower-effort Haiku arms in Study 1b
STEPS_1B = (16, 6)                                  # free analysis 1's Study 1b lengths, in its own order
T24 = ("reporting", "group_b", "item_24", "table")
CHART = ("reporting", "group_b", "item_24", "chart")
VOTE8B = ("reporting", "group_b", "item_8b", "vote_curve")
FRT = ("descriptive", "format_refusals_truncations_missing", "format_report")
VC16 = ("descriptive", "vote_curve_n16")
PRIM = ("confirmatory", "primary_margin_5")
SEC = ("confirmatory", "secondary_margin_10")
# "cluster bootstrap" is tied in the one-sample rows of the Study 1b panels, so their Interval type cells wrap alike and never split the
# name (the column is then as wide as the name, as the panel's Setting column has room; proof 4)
INTERVAL_TYPES = {"cluster bootstrap": "cluster\u00a0bootstrap", "clopper-pearson": "Clopper–Pearson (exact)", "wilson": "Wilson (exact)"}


# ---------------------------------------------------------------- helpers


def L(text: str) -> Cell:
    return label(text)


def cat(*parts: Cell) -> Cell:
    """Cells printed with no space between them: a number and the punctuation after it ('4,' or '0.00833;'), keeping every ref."""
    return joined(*parts, sep="")


def inputs_match(S: Store, fa: str, pins: Sequence[Tuple[str, str, str]]) -> None:
    """A free analysis was computed from the very files pinned here: its stamped input hashes (`inputs.<study>.<key>`) must equal the
    pinned SHA-256 of each source (read through the store, so the pin itself is checked against the file's bytes)."""
    for study, key, src in pins:
        if G(S, fa, "inputs", study, key) != G(S, src, "@sha256"):
            raise ValueError(f"{fa}: inputs.{study}.{key} is not the pinned SHA-256 of {src}")


PINS_1 = (("study1", "analysis_json_sha256", "main"), ("study1", "k_json_sha256", "main_k"))
PINS_1B = (("study1b", "analysis_json_sha256", "s1b"), ("study1b", "k_json_sha256", "s1b_k"))


def R(S: Store, src: str, *segs: Any) -> Ref:
    return S.ref(src, join_key(*segs))


def G(S: Store, src: str, *segs: Any) -> Any:
    return S.get(src, join_key(*segs))


def P(r: Ref) -> Cell:
    """An accuracy in % from points; one more decimal if rounding would reach 0 or 100."""
    return pct(r, dp=2, from_proportion=False, bounds=(0.0, 100.0))


def F(r: Ref) -> Cell:
    """Format compliance in % from a share (0-1), at the supplement's 2 decimals (D-161 (2); the paper versions print none of it);
    one more decimal if rounding would reach 100."""
    return pct(r, dp=2, from_proportion=True, bounds=(100.0,))


def usd_d(d: Any, sf: int = 3) -> Cell:
    """A derived dollar amount, printed like `usd` (significant figures), keeping the formula and refs."""
    return Cell(fmt_sf(d.value, sf), raw=d.value, refs=d.refs, formula=d.formula)


def d_cells(S: Store, src: str, block: Sequence[Any], bounds: Tuple[float, ...] = (0.0,), d_key: str = "d") -> List[Cell]:
    """[d, its 95% interval] in points from a block holding `d` (or `mean`) and `ci95`."""
    lo, hi = ci_refs(S, src, join_key(*block, "ci95"))
    return [num(R(S, src, *block, d_key), dp=2, signed=True, bounds=bounds),
            interval(lo, hi, dp=2, signed=True, bounds=bounds)]


def d_ci1(S: Store, src: str, block: Sequence[Any], bounds: Tuple[float, ...]) -> Cell:
    """The paper's 'd [95% interval]' (D-161): d at one decimal, signed, and its interval with the positive end unsigned, each with the
    one-more-decimal guard at 0 and the margins (as TAB-01's paper version prints Test B2)."""
    lo, hi = ci_refs(S, src, join_key(*block, "ci95"))
    return flat(num(R(S, src, *block, "d"), dp=1, signed=True, bounds=bounds), interval(lo, hi, dp=1, signed=False, bounds=bounds))


def acc_ci1(S: Store, src: str, block: Sequence[Any]) -> Cell:
    """The paper's 'accuracy [95% interval]' in % from points at one decimal (D-161), with the guard at 0 and 100. A collapsed interval
    stops the build: the paper version has no note for free analysis 4's exact replacement (the full table prints it)."""
    lo, hi = ci_refs(S, src, join_key(*block, "ci95"))
    if lo.value == hi.value:
        raise ValueError(f"{src}:{join_key(*block)}: the interval collapsed; the paper version has no note for its exact replacement")
    return flat(pct(R(S, src, *block, "mean"), dp=1, from_proportion=False, bounds=(0.0, 100.0)),
                interval(lo, hi, dp=1, bounds=(0.0, 100.0)))


FA4_EXACT = "(exact, post hoc)"                     # free analysis 4's exact interval in place of a collapsed bootstrap
FA4_TYPE = "Clopper–Pearson (exact, post hoc: free analysis 4)"   # the interval-type cell of a row that prints one


def acc_interval(S: Store, src: str, block: Sequence[Any], ci_name: str = "ci95") -> Tuple[Cell, bool]:
    """An accuracy's 95% interval in %, and whether free analysis 4 replaced it. A bootstrap interval that collapsed to one value is
    replaced by free analysis 4's exact one (core.fa4_exact: fa4's copy of that very interval), marked '(exact, post hoc)'; the row's
    interval-type cell then says FA4_TYPE and fa4_note adds the note and the caption clause. If free analysis 4 stamps none, nothing
    is built."""
    lo, hi = ci_refs(S, src, join_key(*block, ci_name))
    if lo.value != hi.value:
        return interval(lo, hi, dp=2, bounds=(0.0, 100.0)), False
    key = join_key(*block)
    ex = fa4_exact(S, src, key) if ci_name == "ci95" else None
    if ex is None:
        raise ValueError(f"{src}:{key}: the interval collapsed and free analysis 4 stamps no exact replacement")
    return joined(interval(ex.lo, ex.hi, dp=2, scale=ex.scale, bounds=(0.0, 100.0)), L(FA4_EXACT)), True


def fa4_note(t: Table) -> Table:
    """Where a table's cells (or its panels' cells) print free analysis 4's exact interval: the note on it, and a clause in the
    interval caption of the table and of each panel that prints one (the captions otherwise name only the stamped interval types).
    A row that prints one must say so in its interval-type cell, where the table has one."""
    def has(tb: Table) -> bool:
        return any(FA4_EXACT in c.printed for r in tb.rows for c in r)
    tables = [t] + [p for _, p in t.panels]
    for tb in tables:
        types = [j for j, c in enumerate(tb.columns) if c.printed == "Interval type"]
        for r in tb.rows:
            if types and any(FA4_EXACT in c.printed for c in r) != (r[types[0]].printed == FA4_TYPE):
                raise ValueError(f"a row's interval type does not match its interval: {[c.printed for c in r]}")
    if not any(has(tb) for tb in tables):
        return t
    t.notes.append([L("(exact, post hoc): free analysis 4's exact (Clopper–Pearson) 95% interval over puzzles, printed in place "
                      "of a bootstrap interval that collapsed to one value: post hoc, a presentation only, not a test.")])
    for tb in tables:
        if (tb is t or has(tb)) and tb.caption.get("interval"):
            *head, last = tb.caption["interval"]
            tb.caption["interval"] = [*head, cat(last, L("; where a bootstrap interval collapsed to one value, free analysis 4's exact "
                                                         "(Clopper–Pearson) 95% interval, post hoc (marked \"" + FA4_EXACT + "\")"))]
    return t


def er_beside_test(S: Store) -> None:
    """ER_TIER's evidence: the Study 1b spec's one "Beside every test" list starts with the error-rate ratio. Refuses otherwise."""
    hits = S.find_lines(SPEC1B.name, r"^- \*\*Beside every test:\*\*\s*$")
    if len(hits) != 1 or not str(S.get(SPEC1B.name, f"L{hits[0] + 1}")).startswith("- the **error-rate ratio**, by the rules of"):
        raise ValueError("the Study 1b spec no longer lists the error-rate ratio beside every test: the error ratio's tier would be wrong")


def close(a: Any, b: Any, what: str) -> None:
    if abs(float(a) - float(b)) > TOL:
        raise ValueError(f"{what}: {a!r} != {b!r}")


def tag_name(tag: str) -> str:
    return STUDY1B_TAGS[tag][0]


# ================================================================ TAB-24


def _s1_vote_index(S: Store, sh: str, k: int) -> int:
    """Index of the k-try point on item 24's Haiku-medium vote line (checked against item 8b's vote curve, the same points in shares)."""
    line = G(S, "main", *CHART, sh, "haiku_med_vote_line")
    hits = [i for i, p in enumerate(line) if p["k"] == k]
    if len(hits) != 1:
        raise ValueError(f"Study 1 {sh}: {len(hits)} vote-line points at k = {k}")
    i = hits[0]
    c8 = G(S, "main", *VOTE8B, sh)
    if c8["arm"] != "haiku-med" or c8["points"][i]["k"] != k:
        raise ValueError(f"Study 1 {sh}: item 8b's vote curve is not Haiku-medium's at k = {k}")
    close(100.0 * c8["points"][i]["mean"], line[i]["mean"], f"Study 1 {sh} vote@{k}: item 8b against item 24's vote line")
    return i


def _s1_accuracy(S: Store, b: Sequence[Any]) -> Tuple[Cell, Cell]:
    """Item 24's interval for a one-try arm, with its type: cluster bootstrap for Haiku (free analysis 4's exact one where that
    collapsed), Clopper–Pearson for the one-try Opus arm."""
    r = G(S, "main", *b)
    if "accuracy_interval" in r:
        ci, fa4 = acc_interval(S, "main", [*b, "accuracy_interval"])
        return ci, L(FA4_TYPE if fa4 else "cluster bootstrap")
    return acc_interval(S, "main", [*b, "accuracy_cp95"], ci_name="cp95")[0], L("Clopper–Pearson (exact)")


def _s1_single(S: Store, sh: str, arm: str, name: str, ratio: Cell, d: List[Cell], tier: str) -> List[Cell]:
    b = [*T24, f"{arm} {sh}"]
    if G(S, "main", *b, "cpc", "how") != "single try":
        raise ValueError(f"{arm} {sh}: item 24's row is not a single try")
    ci, itype = _s1_accuracy(S, b)
    return [L(shape(sh)), L(name), integer(R(S, "main", *b, "cpc", "k")), P(R(S, "main", *b, "accuracy_mean")), ci, itype,
            F(R(S, "main", *b, "format_compliance", "format_compliance")), usd(R(S, "main", *b, "cost_per_puzzle", "mean")),
            ratio, *d, L(tier)]


def _s1_vote(S: Store, sh: str, k: int, name: str, ratio: Cell, d: List[Cell], tier: str) -> List[Cell]:
    i = _s1_vote_index(S, sh, k)
    p = [*CHART, sh, "haiku_med_vote_line", i]
    hm = [*T24, f"haiku-med {sh}"]
    ci, fa4 = acc_interval(S, "main", p)
    return [L(shape(sh)), L(name), integer(R(S, "main", *p, "k")), P(R(S, "main", *p, "mean")), ci,
            L(FA4_TYPE if fa4 else "cluster bootstrap"), F(R(S, "main", *hm, "format_compliance", "format_compliance")),
            usd(R(S, "main", *p, "cost_per_puzzle")), ratio, *d, L(tier)]


def _tab24_study1(S: Store) -> Tuple[List[List[Cell]], List[List[Cell]]]:
    rows: List[List[Cell]] = []
    k_chain = int(G(S, "fa1", "result", "study1", SHAPES1[0], "k"))
    # the Opus-medium rows' d is "(free analysis 7; post hoc, exploratory)": free analysis 7's stamped label says post hoc and its
    # stamped tier says exploratory
    if not (str(G(S, "fa7", "label")).startswith("post hoc") and str(G(S, "fa7", "definition", "tier_label")).startswith("exploratory")):
        raise ValueError("free analysis 7 is no longer stamped post hoc and exploratory: rewrite the Opus-medium rows' tier")
    above: List[Tuple[str, int]] = []
    for sh in SHAPES1:
        f1 = ["result", "study1", sh]
        k = int(G(S, "fa1", *f1, "k"))
        hx, hm = [*T24, f"haiku-max {sh}"], [*T24, f"haiku-med {sh}"]
        # the free analyses' own numbers must agree with the stamped points printed beside them
        close(G(S, "fa1", *f1, "haiku_max_single"), G(S, "main", *hx, "accuracy_mean"), f"fa1 Haiku-max {sh}")
        close(G(S, "fa7", "result", sh, "haiku_max_single"), G(S, "main", *hx, "accuracy_mean"), f"fa7 Haiku-max {sh}")
        close(G(S, "fa7", "result", sh, "opus_medium"), G(S, "main", *T24, f"opus-med {sh}", "accuracy_mean"), f"fa7 Opus-medium {sh}")
        close(G(S, "fa1", *f1, "vote_at_k"), G(S, "main", *CHART, sh, "haiku_med_vote_line", _s1_vote_index(S, sh, k), "mean"),
              f"fa1 Haiku-medium vote@{k} {sh}")
        close(G(S, "fa1", *f1, "cost_ratio"),
              G(S, "main", *hx, "cost_per_puzzle", "mean") / G(S, "main", *hm, "cost_per_puzzle", "mean"), f"fa1 cost ratio {sh}")
        if k != math.floor(G(S, "fa1", *f1, "cost_ratio")):
            raise ValueError(f"fa1 Study 1 {sh}: k is not the floor of the cost ratio")
        hx_cost = G(S, "main", *hx, "cost_per_puzzle", "mean")
        if G(S, "main", *CHART, sh, "haiku_med_vote_line", _s1_vote_index(S, sh, k), "cost_per_puzzle") > hx_cost:
            raise ValueError(f"Study 1 {sh}: the equal-money vote costs more than one Haiku-max try")

        rows.append(_s1_single(S, sh, "haiku-max", "One Haiku-max sample", DASH, [DASH, DASH],
                               "exploratory setting; point pre-specified descriptive (Study 1)"))
        rows.append(_s1_single(S, sh, "haiku-med", "One Haiku-medium sample", DASH, [DASH, DASH], "pre-specified descriptive (Study 1)"))
        rows.append(_s1_vote(S, sh, k, "Haiku-medium vote, cost-matched", num(R(S, "fa1", *f1, "cost_ratio"), dp=2),
                             d_cells(S, "fa1", [*f1, "paired"]),
                             "post hoc paired d and samples per Haiku-max sample (free analysis 1); vote point pre-specified "
                             "descriptive (Study 1)"))
        if k != k_chain:
            # the plan's 4-try vote is the chains' equal-money vote; on this shape the same k costs more than one Haiku-max try
            if G(S, "main", *CHART, sh, "haiku_med_vote_line", _s1_vote_index(S, sh, k_chain), "cost_per_puzzle") <= hx_cost:
                raise ValueError(f"Study 1 {sh}: the chains' k does not cost more than one Haiku-max try; the note would be wrong")
            above.append((sh, k))
            rows.append(_s1_vote(S, sh, k_chain, "Haiku-medium vote at the chains' cost-matched k", DASH, [DASH, DASH],
                                 "pre-specified descriptive (Study 1); above the cost match on this shape, no paired interval"))
        rows.append(_s1_single(S, sh, "opus-med", "One Opus-medium answer", DASH, d_cells(S, "fa7", ["result", sh, "paired"]),
                               "paired d (free analysis 7; post hoc, exploratory); point pre-specified descriptive (Study 1)"))
    notes = []
    for sh, k in above:
        notes.append([L(f"On {shape_word(sh)} ({shape(sh)}) the chains' cost-matched vote, k ="),
                      cat(integer(R(S, "fa1", "result", "study1", SHAPES1[0], "k")),
                          L(", costs more than one Haiku-max sample (cost column), so it is shown without a paired interval; the "
                            "cost-matched vote on this shape has k =")),
                      cat(integer(R(S, "fa1", "result", "study1", sh, "k")), L("."))])
    return rows, notes


def _s1b_single(S: Store, tag: str, n: int, tier: str, n_tail: int) -> List[Cell]:
    ch, pc = f"1x{n}", f"{n}x1"
    a = ["descriptive", "arms", f"{tag}@{n}"]
    if G(S, "s1b", *a, ch, "cpc", "how") != "single try" or int(G(S, "s1b", *a, "N")) != n:
        raise ValueError(f"{tag}@{n}: not a single-try arm block at {n} steps")
    itype = G(S, "s1b", *a, "pooled", "interval")
    ci, fa4 = acc_interval(S, "s1b", [*a, "pooled"])
    return [L(f"One {tag_name(tag)} sample"), integer(R(S, "s1b", *a, ch, "cpc", "k")), P(R(S, "s1b", *a, "pooled", "mean")),
            ci, L(FA4_TYPE) if fa4 else text_of(R(S, "s1b", *a, "pooled", "interval"), {itype: INTERVAL_TYPES[itype]}),
            joined(F(R(S, "s1b", *FRT, tag, ch, "format_compliance")), L("/"), F(R(S, "s1b", *FRT, tag, pc, "format_compliance"))),
            usd(R(S, "s1b", *a, "pooled", "cost_per_answer")), DASH, *([DASH] * n_tail), L(tier)]


def _s1b_vote(S: Store, tag: str, n: int) -> List[Cell]:
    ch, pc = f"1x{n}", f"{n}x1"
    f1 = ["result", "study1b", f"{tag}@{n}"]
    a = ["descriptive", "arms", f"{tag}@{n}"]
    hx = ["descriptive", "arms", f"hx@{n}"]
    k = int(G(S, "fa1", *f1, "k"))
    close(G(S, "fa1", *f1, "haiku_max_single_pooled"), G(S, "s1b", *hx, "pooled", "mean"), f"fa1 hx@{n} pooled")
    close(G(S, "fa1", *f1, "cost_ratio"), G(S, "s1b", *hx, "pooled", "cost_per_answer") / G(S, "s1b", *a, "pooled", "cost_per_answer"),
          f"fa1 cost ratio {tag}@{n}")
    if G(S, "fa1", *f1, "designed_tries") != G(S, "s1b", *a, "tries_per_item"):
        raise ValueError(f"fa1 {tag}@{n}: designed tries differ from the arm's tries per item")
    if k != min(math.floor(G(S, "fa1", *f1, "cost_ratio")), G(S, "fa1", *f1, "designed_tries")):
        raise ValueError(f"fa1 {tag}@{n}: k is not the floor of the cost ratio held to the designed tries")
    cost = derive("k * one-try list cost per answer (pooled)", lambda kk, c: kk * c, R(S, "fa1", *f1, "k"),
                  R(S, "s1b", *a, "pooled", "cost_per_answer"))
    if cost.value > G(S, "s1b", *hx, "pooled", "cost_per_answer") + TOL:
        raise ValueError(f"{tag}@{n}: the equal-money vote costs more than one Haiku-max try")
    return [L(f"{tag_name(tag)} vote, cost-matched"), integer(R(S, "fa1", *f1, "k")), P(R(S, "fa1", *f1, "vote_at_k_pooled")), DASH, DASH,
            joined(F(R(S, "s1b", *FRT, tag, ch, "format_compliance")), L("/"), F(R(S, "s1b", *FRT, tag, pc, "format_compliance"))),
            usd_d(cost), num(R(S, "fa1", *f1, "cost_ratio"), dp=2),
            *d_cells(S, "fa1", [*f1, "paired", "pooled"]), *d_cells(S, "fa1", [*f1, "paired", ch]),
            *d_cells(S, "fa1", [*f1, "paired", pc]),
            L("post hoc (free analysis 1): k, accuracy, samples per Haiku-max sample and d; cost derived (k times the one-sample cost); "
              "format compliance pre-specified descriptive")]


def _set_word(S: Store, n: int) -> str:
    """Which Study 1b set holds the n-step puzzles: the test at that length's stamped set (its id says main or extension)."""
    tests = [t for t in ("B1", "B3") if int(G(S, "s1b", "completeness", t, "N")) == n]
    if len(tests) != 1:
        raise ValueError(f"Study 1b: {len(tests)} tests at {n} steps")
    sid = G(S, "s1b", "completeness", tests[0], "set_id")
    if sid.startswith("main-"):
        return "main set"
    if sid.startswith("ext"):
        return "extension set"
    raise ValueError(f"Study 1b set {sid!r}: neither main nor extension")


def _tab24_study1b_panel(S: Store, n: int) -> Table:
    ch, pc = f"1x{n}", f"{n}x1"
    cols = ["Setting", "Samples voted (k)", "Accuracy, pooled (%)", "Accuracy 95% interval", "Interval type",
            f"Format compliance of the setting's samples, {shape(ch)}\u00a0/\u00a0{shape(pc)} (%)", "List cost per answer ($)",
            "Samples per Haiku-max sample (Haiku-max cost per answer\u00a0/ one sample of this setting)",
            "d pooled: one Haiku-max sample minus this row (points)",
            "d pooled 95% interval (paired)", f"d, {shape(ch)} (points)", f"d, {shape(ch)}: 95% interval",
            f"d, {shape(pc)} (points)", f"d, {shape(pc)}: 95% interval", "Label"]
    rows = [_s1b_single(S, "hx", n, "pre-specified descriptive (effort sweep)", 6)]
    for tag in LOWER_TAGS:
        rows.append(_s1b_single(S, tag, n, "pre-specified descriptive (effort sweep)", 6))
        rows.append(_s1b_vote(S, tag, n))
    f1 = ["result", "study1b", f"hm@{n}"]
    # the supplement prints every panel's notes once, under the table's last float, so the note says which rows it describes: the main
    # table's own vote rows (Study 1) print per-shape accuracies with intervals, and its one-sample rows are Study 1's (Edith, proof 4)
    notes = [
        [L("Panels 1 and 2 (Study 1b): vote rows: free analysis 1 (post hoc) stamps the vote's k, pooled accuracy, samples per "
           "Haiku-max sample and paired d, with no accuracy interval and no per-shape vote accuracy; Study 1b's own file stamps no "
           "lower-effort vote; the vote's list cost per answer is k times the setting's stamped one-sample cost per answer (derived); "
           "one-sample rows: Study 1b's pre-specified effort sweep (descriptive), as stamped.")],
    ]
    caption = {
        "tier": [L("post hoc (free analysis 1): the vote rows' k, accuracy, samples per Haiku-max sample and paired d, with no Holm "
                   "correction and no verdict; derived: the vote rows' costs; pre-specified descriptive: the one-sample rows and format "
                   "compliance")],
        "study": [L("Study 1b at"), integer(R(S, "s1b", "descriptive", "arms", f"hx@{n}", "N")), L("steps")],
        "set": [L(f"Study 1b's {_set_word(S, n)} at this length; every puzzle as a chain and as pieces")],
        "n": [integer(R(S, "fa1", *f1, "paired", "pooled", "n")), L("puzzles; designed samples per item:"),
              integer(R(S, "s1b", "constants", "designed_tries", "hx")), L("for Haiku-max,"),
              integer(R(S, "s1b", "descriptive", "arms", f"hm@{n}", "tries_per_item")),
              L("each for Haiku-medium, Haiku-high and Haiku-xhigh")],
        "interval": [L("d: paired BCa bootstrap over puzzles (free analysis 1), B ="),
                     cat(integer(R(S, "fa1", "code", "B")), L("; one-sample accuracies: the interval type in each row; the vote "
                                                               "accuracies have no stamped interval"))],
        "price": [L("list price per answer; a vote of k samples costs k times one sample's list cost per answer")],
    }
    t = Table([L(c) for c in cols], rows, notes, caption)
    # the supplement's layout: 15 columns are too many for one page, so the panel splits into four parts (portrait, 6.5 in), each with
    # its Setting column: the vote size and the accuracy (with its interval, type and format compliance), the cost beside the cost ratio
    # (as the main table puts them) and the pooled d, d per shape, and the label. Rows fall into groups: the Haiku-max sample, then each
    # lower-effort setting's one-sample row with its cost-matched vote.
    t.layout = "split"
    t.split_parts = [(None, [1, 2, 3, 4, 5]), (None, [6, 7, 8, 9]), (None, [10, 11, 12, 13]), (None, [14])]
    t.groups = [1 + 2 * j for j in range(len(LOWER_TAGS))]
    return t


# PLAN NOTE (TAB-24): the plan's "4-try Haiku-medium vote" is the chains' equal-money vote (free analysis 1's k on chains); on chains it is
# the equal-money row, on pieces it is shown as its own row (it costs more than one Haiku-max try there). Study 1b's rows are two side
# panels (16 and 6 steps), since each has its own shapes and base puzzles; there free analysis 1 stamps the vote's pooled accuracy only
# (post hoc), with no interval (Study 1b's own file stamps no lower-effort vote), and the vote's cost per answer is derived (k times the
# arm's stamped one-try cost per answer). Item 8b's vote curve is used only as a check (the same vote points as item 24's vote line).
# Study 1's k.json is not the k here: its k (k_from_rows, 36 and 40) is Haiku-medium's equal-money vote against one Opus-medium answer,
# not against one Haiku-max try, so nothing is printed from it. It is read only to check that free analyses 1 and 7 were computed from
# the pinned files (their stamped input hashes against the pins of Study 1's and Study 1b's analysis.json and k.json); the equal-money k
# printed here is free analysis 1's (the floor of its stamped cost ratio, checked against item 24's stamped costs).
@output("TAB-24")
@main_text
def tab_24(S: Store) -> Table:
    cols = ["Shape", "Setting", "Samples voted (k)", "Accuracy (%)", "Accuracy 95% interval", "Interval type",
            "Format compliance of the setting's samples (%)", "List cost per puzzle ($)",
            "Samples per Haiku-max sample (Haiku-max cost per puzzle\u00a0/ one sample of this setting)",
            "d: one Haiku-max sample minus this row (points)",
            "d 95% interval (paired)", "Label"]
    for fa in ("fa1", "fa7"):
        inputs_match(S, fa, PINS_1 + PINS_1B)
    rows, shape_notes = _tab24_study1(S)

    # caption counts: one value per arm, the same on both shapes (checked)
    b0 = [*T24, f"haiku-max {SHAPES1[0]}"]
    for arm in ("haiku-max", "haiku-med", "opus-med"):
        for sh in SHAPES1:
            b = [*T24, f"{arm} {sh}"]
            if G(S, "main", *b, "base_puzzles") != G(S, "main", *b0, "base_puzzles"):
                raise ValueError(f"{arm} {sh}: base puzzles differ")
            if G(S, "main", *b, "refusals_and_truncations", "tries") != G(S, "main", *T24, f"{arm} {SHAPES1[0]}", "refusals_and_truncations", "tries"):
                raise ValueError(f"{arm}: tries differ between shapes")
    for n in STEPS_1B:
        for tag in LOWER_TAGS:
            if G(S, "fa1", "result", "study1b", f"{tag}@{n}", "paired", "pooled", "n") != G(S, "fa1", "result", "study1b", f"hm@{n}", "paired", "pooled", "n"):
                raise ValueError(f"fa1 {tag}@{n}: base puzzles differ")
            if G(S, "s1b", "descriptive", "arms", f"{tag}@{n}", "tries_per_item") != G(S, "s1b", "descriptive", "arms", "hm@16", "tries_per_item"):
                raise ValueError(f"{tag}@{n}: tries per item differ")
        if G(S, "s1b", "descriptive", "arms", f"hx@{n}", "tries_per_item") != G(S, "s1b", "constants", "designed_tries", "hx"):
            raise ValueError(f"hx@{n}: tries per item differ from the designed tries")

    # "Haiku-max was an exploratory arm in Study 1": item 10 (Study 1's exploratory arms) holds it on both shapes, and its stamped
    # label says exploratory (the main-text note names no item number)
    if not (all(f"haiku-max {sh}" in G(S, "main", "reporting", "group_b", "item_10", "arms") for sh in SHAPES1)
            and str(G(S, "main", "reporting", "group_b", "item_10", "label")).startswith("exploratory")):
        raise ValueError("Study 1's Haiku-max is no longer one of item 10's exploratory arms: rewrite the format note")
    notes = [
        [joined(L('Stamped note of free analysis 1, in its own words: "'), text_of(R(S, "fa1", "result", "note")), L('"'), sep="")],
        [joined(L('Stamped note of free analysis 7, in its own words: "'), text_of(R(S, "fa7", "result", "note")), L('"'), sep="")],
        [L('In those two stamped notes, a "try" is a sample, an "arm" is a setting and "at the same money" is cost-matched.')],
        [L("Samples per Haiku-max sample: one Haiku-max sample's list cost divided by the list cost of one sample of the setting in "
           "the row. Cost-matched: the vote's k is the floor of the samples per Haiku-max sample, held to the setting's designed "
           "samples, so the vote costs no more than one Haiku-max sample. Study 1 costs are in US dollars per puzzle and Study 1b costs "
           "in US dollars per answer, as each study stamps them.")],
        *shape_notes,
        [L("Format compliance (pre-specified descriptive) is that of the setting's own samples; a vote is taken over the same "
           "samples. Haiku-max was an exploratory setting in Study 1.")],
        [L("No row is a test: the paired differences carry no p-value, no Holm correction and no verdict. Each row stays within one "
           "study.")],
    ]
    caption = {
        "tier": [L("post hoc (free analyses 1 and 7): the paired differences, the cost-matched k and the samples per Haiku-max "
                   "sample, exploratory, with no Holm correction and no verdict, each within one study, the two studies never pooled. "
                   "Pre-specified descriptive: Study 1's accuracy and cost points, Study 1b's one-sample rows and every format "
                   "compliance. Study 1b's vote "
                   "accuracies are post hoc (free analysis 1) and its vote costs are derived (k times the stamped one-sample cost per "
                   "answer)")],
        "study": [L("Study 1 at 6 steps (main table); Study 1b at 16 steps and at 6 steps (Panels 1 and 2)")],
        "set": [L("Study 1: the Main run's puzzle set; Study 1b: its 16-step main set and its 6-step extension set; every puzzle "
                  "as a chain and as pieces")],
        "n": [L("Study 1:"), integer(R(S, "main", *b0, "base_puzzles")), L("puzzles per shape; samples per shape:"),
              integer(R(S, "main", *b0, "refusals_and_truncations", "tries")), L("for Haiku-max,"),
              integer(R(S, "main", *T24, f"haiku-med {SHAPES1[0]}", "refusals_and_truncations", "tries")), L("for Haiku-medium,"),
              integer(R(S, "main", *T24, f"opus-med {SHAPES1[0]}", "refusals_and_truncations", "tries")),
              L("for Opus-medium. Study 1b:"), integer(R(S, "fa1", "result", "study1b", "hm@16", "paired", "pooled", "n")),
              L("puzzles at 16 steps and"), integer(R(S, "fa1", "result", "study1b", "hm@6", "paired", "pooled", "n")),
              L("at 6 steps; designed samples per item:"), integer(R(S, "s1b", "constants", "designed_tries", "hx")),
              L("for Haiku-max,"), integer(R(S, "s1b", "descriptive", "arms", "hm@16", "tries_per_item")),
              L("each for Haiku-medium, Haiku-high and Haiku-xhigh")],
        "interval": [L("d: paired BCa bootstrap over puzzles, B ="), integer(R(S, "fa1", "code", "B")),
                     L("in free analysis 1 (the vote rows) and"), integer(R(S, "fa7", "code", "B")),
                     L("in free analysis 7 (the Opus-medium rows);"),
                     L("accuracies: cluster bootstrap over puzzles (percentile) for the Haiku settings and Study 1's votes, "
                       "Clopper–Pearson (exact) for the one-sample Opus-medium setting; Study 1b's vote accuracies have no stamped "
                       "interval")],
        "price": [L("list price: Study 1 per puzzle, Study 1b per answer; a vote of k samples costs k times one sample's list cost")],
    }
    t = Table([L(c) for c in cols], rows, notes, caption)
    # the supplement's layout: 12 columns with a long label split into three parts (portrait, 6.5 in), each with the Shape and Setting
    # columns: the accuracy with its interval and format compliance; the cost, the cost ratio and d; and the label
    t.layout = "split"
    t.split_key = [0, 1]
    t.split_parts = [(None, [2, 3, 4, 5, 6]), (None, [7, 8, 9, 10]), (None, [11])]
    t.groups = [i for i in range(1, len(rows)) if rows[i][0].printed != rows[i - 1][0].printed]     # a space above the pieces' first row
    t.panels = [(f"Study 1b, {n} steps: one Haiku-max sample against cost-matched lower-effort Haiku votes", _tab24_study1b_panel(S, n))
                for n in STEPS_1B]
    t.main_table = _table3(S, caption)
    return fa4_note(t)


def _table3(S: Store, caption) -> Table:
    """Table 3 of the paper (D-160; Vision's plan §0c; D-161): one Haiku-max sample against each lower-effort Haiku vote at no more than
    its cost, on the same puzzles, at one decimal: Study 1 per shape at 6 steps, Study 1b pooled at 16 and 6 steps. Every value is free
    analysis 1's (already checked equal to the stamped points in tab_24)."""
    def d_ci(f: Sequence[Any]) -> Cell:
        lo, hi = ci_refs(S, "fa1", join_key(*f, "ci95"))
        return joined(pts(R(S, "fa1", *f, "d"), dp=1), interval(lo, hi, dp=1, signed=False, bounds=(0.0,)))

    def one(r: Ref) -> Cell:
        return pct(r, dp=1, from_proportion=False, bounds=(100.0,))

    rows: List[List[Cell]] = []
    for sh in SHAPES1:
        f1 = ["result", "study1", sh]
        rows.append([joined(L("Study 1,"), integer(R(S, "main_plan", "steps"))),
                     L({"chain": "chains"}.get(shape_word(sh), shape_word(sh))),
                     joined(L("Haiku-medium, k ="), integer(R(S, "fa1", *f1, "k"))), one(R(S, "fa1", *f1, "vote_at_k")),
                     one(R(S, "fa1", *f1, "haiku_max_single")), d_ci([*f1, "paired"])])
    for n in STEPS_1B:
        for tag in LOWER_TAGS:
            f1 = ["result", "study1b", f"{tag}@{n}"]
            rows.append([joined(L("Study 1b,"), integer(R(S, "s1b", "descriptive", "arms", f"hx@{n}", "N"))), L("pooled"),
                         joined(L(f"Haiku-{STUDY1B_TAGS[tag][2]}, k ="), integer(R(S, "fa1", *f1, "k"))),
                         one(R(S, "fa1", *f1, "vote_at_k_pooled")), one(R(S, "fa1", *f1, "haiku_max_single_pooled")),
                         d_ci([*f1, "paired", "pooled"])])
    # Edith §7.2 and §7.5 (proof 2): the study and its steps print once per block (Study 1 at 6 steps; Study 1b at 16; Study 1b at 6),
    # the shape once per block where it does not change ("pooled"), a little space between the blocks; the printed notes take two lines
    notes = [[L("Each row: one Haiku-max sample against a lower-effort Haiku vote of k samples costing no more at list price "
                "(cost-matched); difference: Haiku-max minus the vote, paired over puzzles. Study 1b's rows pool each puzzle's two "
                "shapes.")]]
    t = Table([L(c) for c in ("Study, steps", "Shape", "Vote (effort, k)", "Vote accuracy (%)", "One Haiku-max sample (%)",
                              "Difference (points) [95% interval]")],
              rows, notes, caption, short_notes=[0], layout="float")
    t.groups = [i for i in range(1, len(rows)) if rows[i][0].printed != rows[i - 1][0].printed]
    t.once = [0, 1]
    return t


# ================================================================ TAB-25


def _vc_index(S: Store, k: int) -> int:
    """Index of the k-try point on Study 1b's 16-step Haiku-max vote curve."""
    hits = [i for i, p in enumerate(G(S, "s1b", *VC16, "points")) if p["k"] == k]
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} vote-curve points at k = {k}")
    return hits[0]


# PLAN NOTE (TAB-25): the vote's pooled accuracy at each k (Study 1b's stamped vote curve, with its cluster-bootstrap interval) and the
# tries' format compliance are added beside d, with Opus-medium's one-answer row as the reference. At B2's own k (k.json) the row prints
# Test B2's stamped values (confirmatory pooled d and interval; costs), unchanged, with Test B2's stamped error ratio beside d (the style
# sheet's near-ceiling companion; free analysis 3 stamps no error ratio, so the post hoc rows have none); free analysis 3's own d for
# that vote is only checked against the test and its interval is not printed. The plan's "k = 6 vote's per-shape cost" is in the side
# panel with each shape's own equal-money k; B2's per-shape spend share there is derived (the quotient of the two stamped per-shape costs).
@output("TAB-25")
def tab_25(S: Store) -> Table:
    inputs_match(S, "fa3", PINS_1B)
    m5, m10 = float(G(S, "s1b", *PRIM, "margin")), float(G(S, "s1b", *SEC, "margin"))
    bnd = (0.0, m5, m10)
    n = int(G(S, "s1b", "completeness", "B2", "N"))
    ch, pc = f"1x{n}", f"{n}x1"
    if int(G(S, "s1b", *VC16, "N")) != n or G(S, "s1b", *VC16, "arm") != "hx":
        raise ValueError("the vote curve is not Haiku-max's at B2's length")
    k_b2 = R(S, "s1b_k", "k")
    if G(S, "s1b", *VC16, "k_from_k_json") != k_b2.value:
        raise ValueError("the vote curve's k differs from k.json's k")
    t2 = [*PRIM, "views", "as_deployed", "tests", "B2"]
    t2_10 = [*SEC, "views", "as_deployed", "tests", "B2"]
    if G(S, "s1b", *t2, "d") != G(S, "s1b", *t2_10, "d") or G(S, "s1b", *t2, "ci95") != G(S, "s1b", *t2_10, "ci95"):
        raise ValueError("B2's d or interval differs between the two margins")
    p_b2, thr_b2 = G(S, "s1b", *t2, "p"), G(S, "s1b", *PRIM, "views", "as_deployed", "holm_thresholds", "B2")
    if not (p_b2 < thr_b2 and G(S, "s1b", *t2, "declared") is True):
        raise ValueError("the note says B2's p is below its Holm threshold; the file says otherwise")
    hx_fmt = joined(F(R(S, "s1b", *FRT, "hx", ch, "format_compliance")), L("/"), F(R(S, "s1b", *FRT, "hx", pc, "format_compliance")))
    om_fmt = joined(F(R(S, "s1b", *FRT, "om", ch, "format_compliance")), L("/"), F(R(S, "s1b", *FRT, "om", pc, "format_compliance")))

    # a slash in a header is tied to the word before it and a shape pair kept whole, so no header line starts with "/" or splits "1×6 / 6×1"
    cols = ["Setting", "Samples voted (k)", "Accuracy, pooled (%)", "Accuracy 95% interval",
            f"Format compliance of the samples, {shape(ch)}\u00a0/\u00a0{shape(pc)} (%)", "List cost per answer, pooled ($)",
            "Spend share or cost ratio (vote\u00a0/ Opus-medium), pooled", "d pooled: vote minus Opus-medium (points)",
            "d pooled 95% interval (paired)", "Error-rate ratio R (vote\u00a0/ Opus-medium) [95% interval]", "Label"]
    om = ["descriptive", "arms", f"om@{n}"]
    close(G(S, "s1b", *om, "pooled", "cost_per_answer"), G(S, "s1b", *VC16, "opus_medium_cost_per_answer", "pooled", "list_usd"),
          "Opus-medium cost per answer")
    if G(S, "s1b", *om, "pooled", "interval") != "cluster bootstrap":
        raise ValueError("the caption says every accuracy interval is a cluster bootstrap; Opus-medium's is not")
    # Test B2's error ratio (the near-ceiling companion of d): defined, on the same base puzzles as the test
    er = ["error_ratios", "B2"]
    er_beside_test(S)
    if G(S, "s1b", *er, "defined") is not True or G(S, "s1b", *er, "n") != G(S, "s1b", *t2, "n"):
        raise ValueError("Test B2's error ratio is undefined or on other base puzzles than the test")
    elo, ehi = ci_refs(S, "s1b", join_key(*er, "ci95"))
    er_cell = joined(num(R(S, "s1b", *er, "R"), dp=2), interval(elo, ehi, dp=2))
    rows: List[List[Cell]] = [[L("One Opus-medium answer (the\u00a0comparator)"), DASH, P(R(S, "s1b", *om, "pooled", "mean")),
                               acc_interval(S, "s1b", [*om, "pooled"])[0], om_fmt, usd(R(S, "s1b", *om, "pooled", "cost_per_answer")),
                               DASH, DASH, DASH, DASH, L("pre-specified descriptive (comparator of Tests B1 and B2)")]]
    by_k = G(S, "fa3", "result", "by_k")
    n_base = G(S, "fa3", "result", "by_k", 0, "pooled", "n")
    seen_b2 = False
    paper: List[List[Cell]] = []                        # the paper's version: the same refs at one decimal (D-161)
    for j, e in enumerate(by_k):
        k = e["k"]
        for part in ("pooled", ch, pc):
            if e[part]["n"] != n_base:
                raise ValueError(f"fa3 k = {k} {part}: base puzzles differ")
        i = _vc_index(S, k)
        vp = [*VC16, "points", i]
        close(e["cost_ratio_pooled"], G(S, "s1b", *vp, "pooled", "cost_per_answer") / G(S, "s1b", *om, "pooled", "cost_per_answer"),
              f"fa3 cost ratio at k = {k}")
        acc = [P(R(S, "s1b", *vp, "pooled", "mean")), acc_interval(S, "s1b", [*vp, "pooled"])[0], hx_fmt]
        if k == k_b2.value:
            seen_b2 = True
            cb = ["costs_beside_tests", "B2"]
            close(G(S, "s1b", *cb, "challenger", "pooled", "list_usd"), G(S, "s1b", *vp, "pooled", "cost_per_answer"), "B2 vote cost")
            close(G(S, "s1b", *cb, "ratio_challenger_over_comparator"), e["cost_ratio_pooled"], "B2 cost ratio")
            close(e["pooled"]["d"], G(S, "s1b", *t2, "d"), "fa3's d at B2's k against the stamped test")
            if G(S, "s1b", "per_form", "B2", ch, "d", "n_base") != n_base or G(S, "s1b", *t2, "n") != n_base:
                raise ValueError("B2's base puzzles differ from free analysis 3's")
            # the Test B2 row's setting is kept on one line in every part of the split table (proof 4, p. 92)
            rows.append([L("Haiku-max\u00a0vote:\u00a0Test B2"), integer(k_b2), *acc, usd(R(S, "s1b", *cb, "challenger", "pooled", "list_usd")),
                         num(R(S, "s1b", *cb, "ratio_challenger_over_comparator"), dp=3), *d_cells(S, "s1b", t2, bnd), er_cell,
                         L("confirmatory: the pooled d and its interval (Test B2, 5-point margin), stamped values unchanged. "
                           f"Error-rate ratio: {ER_TIER}, not part of it. Accuracy, format compliance and costs: pre-specified "
                           "descriptive")])
            paper.append([joined(integer(k_b2), L("(Test B2)")), acc_ci1(S, "s1b", [*vp, "pooled"]), d_ci1(S, "s1b", t2, bnd),
                          num(R(S, "s1b", *cb, "ratio_challenger_over_comparator"), dp=3)])
        else:
            f3 = ["result", "by_k", j]
            rows.append([L("Haiku-max vote"), integer(R(S, "fa3", *f3, "k")), *acc, usd(R(S, "s1b", *vp, "pooled", "cost_per_answer")),
                         num(R(S, "fa3", *f3, "cost_ratio_pooled"), dp=3), *d_cells(S, "fa3", [*f3, "pooled"], bnd), DASH,
                         L("post hoc descriptive sensitivity: d and cost ratio (free analysis 3); accuracy, format compliance and "
                           "cost pre-specified descriptive (vote curve)")])
            paper.append([integer(R(S, "fa3", *f3, "k")), acc_ci1(S, "s1b", [*vp, "pooled"]), d_ci1(S, "fa3", [*f3, "pooled"], bnd),
                          num(R(S, "fa3", *f3, "cost_ratio_pooled"), dp=3)])
    if not seen_b2:
        raise ValueError("free analysis 3 has no row at B2's k")
    j_b2 = next(j for j, e in enumerate(by_k) if e["k"] == k_b2.value)

    # side panel: each shape's own equal-money k, and B2's vote's per-shape cost
    # the third column is Opus-medium's cost per answer over one Haiku-max sample's, comparator over challenger: not the defined "cost
    # ratio" (challenger over comparator), so it is named for what it counts (Edith, proof 4, pp. 112 and 115, for the same fault in S27)
    pcols = ["Shape", "Own cost-matched k",
             "Samples per comparator answer (Opus-medium cost per answer\u00a0/ one Haiku-max sample)",
             "One Haiku-max sample: list cost per answer ($)", "Vote at own k: list cost per answer ($)",
             "Opus-medium: list cost per answer ($)", "d: vote at own k minus Opus-medium (points)", "d 95% interval (paired)",
             "B2's vote: list cost per answer ($)", "B2's vote\u00a0/ Opus-medium spend share (derived)"]
    prows: List[List[Cell]] = []
    hx = ["descriptive", "arms", f"hx@{n}"]
    cb = ["costs_beside_tests", "B2"]
    for sh in (ch, pc):
        o = ["result", "own_equal_money_k", sh]
        if G(S, "fa3", *o, "k") != min(math.floor(G(S, "fa3", *o, "om_over_hx_cost_ratio")), G(S, "s1b", "constants", "designed_tries", "hx")):
            raise ValueError(f"fa3 own k {sh}: not the floor of the cost ratio held to the designed tries")
        # the one-try costs are printed from Study 1b's stamped (pre-specified) keys; free analysis 3's copies must agree
        close(G(S, "fa3", *o, "om_cost_per_answer"), G(S, "s1b", *cb, "comparator", sh, "list_usd"), f"Opus cost {sh}")
        close(G(S, "fa3", "result", "hx_cost_per_answer", sh, "list_usd"), G(S, "s1b", *hx, sh, "cost_per_answer"), f"Haiku-max cost {sh}")
        close(G(S, "fa3", *o, "om_over_hx_cost_ratio"),
              G(S, "s1b", *cb, "comparator", sh, "list_usd") / G(S, "s1b", *hx, sh, "cost_per_answer"), f"fa3 own-k cost ratio {sh}")
        close(G(S, "fa3", *o, "vote_cost_per_answer"), G(S, "fa3", *o, "k") * G(S, "s1b", *hx, sh, "cost_per_answer"),
              f"fa3 own-k vote cost {sh}")
        if G(S, "fa3", *o, "paired", "n") != n_base:
            raise ValueError(f"fa3 own k {sh}: base puzzles differ")
        b2r = derive("B2 vote list cost per answer / Opus-medium list cost per answer", lambda a, b: a / b,
                     R(S, "s1b", *cb, "challenger", sh, "list_usd"), R(S, "s1b", *cb, "comparator", sh, "list_usd"))
        prows.append([L(shape(sh)), integer(R(S, "fa3", *o, "k")), num(R(S, "fa3", *o, "om_over_hx_cost_ratio"), dp=2),
                      usd(R(S, "s1b", *hx, sh, "cost_per_answer")), usd(R(S, "fa3", *o, "vote_cost_per_answer")),
                      usd(R(S, "s1b", *cb, "comparator", sh, "list_usd")), *d_cells(S, "fa3", [*o, "paired"], bnd),
                      usd(R(S, "s1b", *cb, "challenger", sh, "list_usd")), num_d(b2r, dp=3)])
    o0 = ["result", "own_equal_money_k", ch]
    pnotes = [
        [L("Label of every row: post hoc (free analysis 3) for own k, samples per comparator answer, vote cost and d; pre-specified "
           "descriptive for the one-sample costs and B2's vote cost; derived for B2's spend share.")],
        [L("Post hoc (free analysis 3): each shape's own cost-matched k is the floor of Opus-medium's list cost per answer over one "
           "Haiku-max sample's on that shape, held to the designed samples; the vote's cost at that k and its paired d against "
           "Opus-medium are free analysis 3's.")],
        [L("Pre-specified descriptive: one Haiku-max sample's and Opus-medium's list cost per answer on each shape (Study 1b's settings and "
           "costs beside Test B2), and B2's vote's cost per shape (costs beside Test B2). Derived: B2's vote / Opus-medium spend share "
           "per shape, the quotient of those two stamped costs.")],
    ]
    pcaption = {
        "tier": [L("post hoc (free analysis 3): own k, samples per comparator answer, the vote's cost and d, with no p-value, no Holm "
                   "correction and no reading against the margin; pre-specified descriptive: the stamped one-sample costs and B2's vote "
                   "cost; derived: B2's spend share per shape")],
        "study": [L("Study 1b at"), integer(R(S, "s1b", "completeness", "B2", "N")), L("steps")],
        "set": [L(f"Study 1b's {_set_word(S, n)} at this length; each shape on its own")],
        "n": [integer(R(S, "fa3", *o0, "paired", "n")), L("puzzles per shape; designed samples per item:"),
              integer(R(S, "s1b", "constants", "designed_tries", "hx")), L("for Haiku-max,"),
              integer(R(S, "s1b", "constants", "designed_tries", "om")), L("for Opus-medium")],
        "interval": [L("d: paired BCa bootstrap over puzzles (free analysis 3, its own seed), B ="),
                     integer(R(S, "fa3", "code", "B"))],
        "price": [L("list price per answer, as Study 1b's analysis stamps it; a vote of k samples costs k times one sample's list cost "
                    "per answer")],
    }

    p_b2 = pvalue_bound(R(S, "s1b", *t2, "p"), R(S, "s1b", *t2, "z0"), R(S, "s1b", *t2, "a"), R(S, "s1b", *t2[:-2], "B"), dp=5)
    notes = [
        [L("d is the vote of k Haiku-max samples minus one Opus-medium answer, in points, paired over the same puzzles; a positive d "
           "means the vote scored higher.")],
        [L("The Test B2 row is the pre-registered test at B2's own k ="), integer(k_b2),
         L("(Study 1b's rule for a cost-matched vote). Its pooled d and interval are Test B2's stamped confirmatory values, unchanged: p" +
           ("" if p_b2.printed.startswith(chr(0x2264)) else " =")),
         cat(p_b2, L(", below its Holm threshold of")),
         cat(exact(R(S, "s1b", *PRIM, "views", "as_deployed", "holm_thresholds", "B2")), L("; reading:")),
         cat(text_of(R(S, "s1b", *PRIM, "template", "B2"), B_READING), L(".")),
         L("Its accuracy, format compliance and costs are pre-specified descriptive, not part of the test. One comparison, one "
           "interval: free analysis 3's own interval for this vote is not printed.")],
        [L("Error-rate ratio R: the vote's errors over Opus-medium's on the same puzzles. Near the ceiling it sits beside d; on the "
           f"Test B2 row it is Study 1b's stamped value for Test B2, {ER_TIER} and not part of it. The post hoc rows have none: free "
           "analysis 3 stamps no error-rate ratio.")],
        [L("The other vote rows are post hoc descriptive sensitivity: Study 1b's spec set no sensitivity analysis over k, so their d and cost "
           "ratio carry no p-value, no Holm correction and no reading against the margin, and they leave B2 unchanged. Their accuracy, "
           "format compliance and cost are Study 1b's pre-specified vote curve.")],
        [L("One Haiku-max sample (k ="), cat(integer(R(S, "s1b", *VC16, "points", _vc_index(S, 1), "k")), L(")")),
         L("is Test B1's challenger and is reported with the Study 1b tests.")],
        [L("Cost:"), cat(text_of(R(S, "s1b", *VC16, "opus_medium_cost_per_answer", "unit"),
                                 {"USD per answer, list price (item 9b)": "US dollars per answer at list price (item 9b)"}), L(";")),
         L("a vote of k samples costs k times one sample's list cost per answer. Every value in the spend share or cost ratio column "
           "is the vote's pooled list cost per answer over Opus-medium's: a cost ratio on the post hoc rows and, on the Test B2 row, "
           "B2's spend share, as ⟦TAB-01⟧ prints it. The samples per comparator answer that set a cost-matched k (Opus-medium's "
           "cost per answer over one Haiku-max sample's, as in Panel 1) are printed to two decimals; a vote's cost over Opus-medium's, "
           "as reported for Test B2 with the Study 1b tests, to three.")],
        [L("Format compliance: the Haiku-max samples the votes are taken over, and Opus-medium's answers on its row.")],
        [L("Panel 1: per-shape intervals are printed only here (one comparison, one interval): free analysis 3 also stamps per-shape "
           "intervals at each k, drawn with other seeds, and they are not printed.")],
    ]
    if p_b2.printed.startswith(chr(0x2264)):
        notes.append([L(FLOOR_NOTE + ".")])
    caption = {
        "tier": [L("post hoc descriptive sensitivity (free analysis 3) for the vote rows' d and cost ratio, with no p-value, no Holm "
                   "correction and no reading against the margin; the Test B2 row's pooled d and interval are confirmatory (Test B2), "
                   f"stamped values unchanged; the Test B2 row's error-rate ratio is {ER_TIER}; every accuracy, format compliance and cost "
                   "is pre-specified descriptive")],
        "study": [L("Study 1b at"), integer(R(S, "s1b", "completeness", "B2", "N")), L("steps")],
        "set": [L("Study 1b's 16-step main set; every puzzle as a chain and as pieces")],
        "n": [integer(R(S, "fa3", "result", "by_k", 0, "pooled", "n")), L("puzzles; designed samples per item:"),
              integer(R(S, "s1b", "constants", "designed_tries", "hx")), L("for Haiku-max,"),
              integer(R(S, "s1b", "constants", "designed_tries", "om")), L("for Opus-medium")],
        "interval": [L("d: paired BCa bootstrap over puzzles (free analysis 3), B ="),
                     cat(integer(R(S, "fa3", "code", "B")), L("; the Test B2 row's pooled d: Study 1b's confirmatory paired BCa "
                                                               "bootstrap, B =")),
                     cat(integer(R(S, "s1b", *PRIM, "views", "as_deployed", "B")),
                         L("; its error-rate ratio: Study 1b's paired percentile bootstrap over puzzles, B =")),
                     cat(integer(R(S, "s1b", "error_ratios", "B2", "B")),
                         L("; accuracies: cluster bootstrap over puzzles (percentile)"))],
        "price": [L("list price per answer, as Study 1b's analysis stamps it; a vote of k samples costs k times one sample's list cost "
                    "per answer")],
    }
    t = Table([L(c) for c in cols], rows, notes, caption)
    # the supplement's layout: 11 columns with a long label split into three parts (portrait, 6.5 in), each with the Setting and the
    # Samples voted (k) columns, so that every row of every part names the vote it belongs to: the accuracy, format compliance and cost;
    # the cost ratio, d and the error ratio; and the label. The comparator row (one Opus-medium answer) stands apart from the vote
    # rows, k = 2 to 10, by a little space.
    t.layout = "split"
    t.split_key = [0, 1]
    t.split_parts = [(None, [2, 3, 4, 5]), (None, [6, 7, 8, 9]), (None, [10])]
    t.groups = [1]
    side = Table([L(c) for c in pcols], prows, pnotes, pcaption)
    # the side panel's 10 columns split in two parts (portrait): the costs and the cost ratio, then d and B2's vote
    side.layout = "split"
    side.split_parts = [(None, [1, 2, 3, 4, 5]), (None, [6, 7, 8, 9])]
    t.panels = [("Each shape's own cost-matched k, and B2's vote's per-shape cost", side)]
    t.main_table = _paper_25(paper, caption, acc_ci1(S, "s1b", [*om, "pooled"]), bnd)
    return fa4_note(t)


def _paper_25(rows: List[List[Cell]], caption, om_acc: Cell, bnd: Tuple[float, ...]) -> Table:
    """TAB-25 in the paper (D-160; Vision's plan §3, Edith-accepted; D-161): k · Accuracy [95% interval] · d [95% interval] (d against
    Opus-medium, defined in note 0) · cost ratio to Opus-medium (defined in note 1), one row per vote size, at one decimal for % and
    points (the cost ratio keeps the full table's three decimals). The Test B2 row is marked in its k cell, as the caption facts name
    it; its d and interval are Test B2's stamped values, as in the full table. Opus-medium's pooled accuracy [95% interval], the full
    table's comparator row, is given in note 0 (`om_acc`, the same refs at one decimal), so the accuracy column can be read against it.
    Format compliance (the same in every row), the list costs, the error ratio and the side panel stay in the supplement's full table.
    The rows were built beside the full table's, from the same refs."""
    if sum("(Test B2)" in r[0].printed for r in rows) != 1:
        raise ValueError("TAB-25's paper version marks Test B2's row once")
    # Edith §7.5 (proof 2): the two printed notes take two lines together; the positive-d reading and "k samples cost k times one" are
    # in the caption facts and the header, the unit of d in its header
    notes = [[L("d: the vote of k Haiku-max samples minus one Opus-medium answer, paired over puzzles (shapes pooled). "
                "Opus-medium's pooled accuracy (%):"), cat(om_acc, L("."))],
             [L("Spend share: the vote's pooled list cost per answer over Opus-medium's.")]]
    # Edith's §2.1 (334484c): a vote's cost over its comparator's is a spend share, printed at 3 decimals (B2's 0.894 in Table 2)
    t = Table([L(c) for c in ("Samples voted (k)", "Pooled accuracy (%) [95% interval]", "d (points) [95% interval]", "Spend share")],
              rows, notes, caption, short_notes=[0, 1], layout="float")
    paper_decimals(t, (0.0, 100.0, *bnd))
    paper_note_lengths(t)
    return paper_ids(t, "TAB-25")         # the full table is an appendix table (its note names an item); the paper version names none
