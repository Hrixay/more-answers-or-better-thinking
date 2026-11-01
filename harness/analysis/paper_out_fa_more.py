"""TAB-29 (Sonnet at its default effort on Study 1b's six-step bases; free analysis 9) and TAB-30 (re-pricing at other price ratios;
free analysis 12), both approved under D-133 and labelled post hoc. Every number is read from the pinned free-analysis files (fa9, fa12)
or, for the rows Edith's rules give to the locked analyses, from the stamped Study 1 and Study 1b files.

Edith's rules (ops/reviews/2026-10-15-labelling-and-fa9-fa12-definitions.md §2-3): at rho' = rho_list each test's row prints the locked
d and interval (fa12's own interval for that row is printed nowhere); a re-priced row that is the same comparison as a printed result
takes that result and its tier (B2 at k = 1 is Test B1, B2 at another k is free analysis 3's row at that k, Test 1 held at the locked k
is Test 1 as run); rows held at the sample cap are flagged with the cap ("held at 40", "held at 10"); the break-even reports its
replicates with no break-even; fa9 carries the C-066 note. The C-066 note is printed in plain words (no internal names, ids or paths:
style sheet, D-122); the stamped note stays in the cell's provenance.
"""

from __future__ import annotations

import re
from typing import List, Mapping, Optional, Tuple

from .paper_out_core import (Cell, Ref, Store, Table, _width_plan, ci_refs, derive, format_key, integer, interval, join_key, joined,
                             label, num, num_d, output, parse_key, pct, pts, text_of)
from .paper_out_fa_checks import _glue, _quoted, check_paper_words
from .paper_out_names import STUDY1_TESTS, STUDY1B_TAGS, STUDY1B_TESTS, main_text, shape, shape_word

DASH = label("—")
NBSP = "\u00a0"                                      # a no-break space: the writer prints it "~", so a narrow column never breaks there
SHAPE_PLURAL = {"chain": "chains", "pieces": "pieces"}           # the paper's Shape cells say "chains", as the prose and Tables 2, 3, 7 and 13 do
CV_TITLE = "Cached view (Study 1, offline re-pricing)"         # TAB-30's second panel, in the stamped label's words (checked)
TESTS = tuple((t, STUDY1_TESTS[t][0]) for t in ("t1", "t2", "t3")) + (("B2", STUDY1B_TESTS["B2"][0]),)
FORMS = ("1x6", "6x1", "pooled")
FRT = ("descriptive", "format_refusals_truncations_missing", "format_report")
MARGIN = -10.0                                   # Study 1's margin (confirmatory.views.as_deployed.margin; checked in tab_30)
S1_VIEW = "confirmatory.views.as_deployed"
S1B_VIEW = "confirmatory.primary_margin_5.views.as_deployed"

# fa9's stamped note (free_analyses.py, written at a0ecfba) and its plain-words form for the printed table. The mapping ties the printed
# wording to this exact stamped text: a changed note refuses the build. Internal names, ids and paths stay in the provenance only.
FA9_NOTE = ("The 6-step set includes the two partly shown bases (C-066), which were never shown to a model under test; no sensitivity run "
            "is needed (Edith, ops/reviews/2026-10-15-labelling-and-fa9-fa12-definitions.md).")
FA9_NOTE_PRINTED = ("puzzles for which parts of the answer keys were shown in our own work sessions; those parts were never shown "
                    "to a model under test, so no sensitivity run was needed.")
# the paper version's shorter form of the same stamped note (D-161 words), kept with the table it qualifies (Edith's condition 2)
FA9_NOTE_PAPER = "puzzles whose answer keys were partly shown in our own work sessions, never to a model under test, so no sensitivity run was needed."
# The paper version's comparator names (D-161: "sample" for try; one name per setting, as TAB-01's paper version prints them; a row
# name starts with a capital, as the rows of the paper's other tables do): fa9's stamped comparator, through a typed mapping that
# refuses any other stamped name. Opus-medium has several samples per puzzle on this set, averaged into its one-answer accuracy, so it
# is "One Opus-medium answer" (TAB-01's B3 row, the same six-step set); Haiku-max's one-sample accuracy is "One Haiku-max sample";
# Opus-low and Sonnet-medium have one sample per puzzle and keep their plain names (TAB-01's Test 5 row). tab_29 checks each name
# against the tag's house name and its stamped samples per puzzle.
PAPER_COMPARATOR = {"Opus-low": "Opus-low", "Opus-medium": "One Opus-medium answer", "Sonnet-medium": "Sonnet-medium",
                    "Haiku-max, one try": "One Haiku-max sample"}
# The full table's comparator names: fa9's stamped names, with the one that holds a retired word ("try", D-161) in the paper's word.
FULL_COMPARATOR = {"Opus-low": "Opus-low", "Opus-medium": "Opus-medium", "Sonnet-medium": "Sonnet-medium",
                   "Haiku-max, one try": "Haiku-max, one sample"}


def _line(*parts: Cell) -> List[Cell]:
    """A note or caption line as ONE cell, its parts joined with no separator (labels carry their own spaces)."""
    return [joined(*parts, sep="")]


def set_widths(t: Table, widths: Mapping[str, float], spare: float = 0.11) -> None:
    """Give some wrapping columns the widths (inches, as the writer's plan counts them) that keep their cells one line shorter, and keep
    the writer's own plan for every other column (core's `fixed_plan`, as paper_out_study1b.right_align does). The writer hands the room
    out greedily and cannot reach every such width at once. It keeps 0.1 in of the line spare for its estimate's error, so `spare` (the
    most these widths may add to the writer's total) lets them use that 0.1 in. The estimate itself counts 0.04 in beyond a column's text;
    a width at or above the estimate's width for the wanted line count keeps that margin, and one below it does not. Such a width fits
    only if TeX's own setting does, with less margin: the estimate (and so `height_in`) does not see it, and only the measure tool
    does. Call it last, once the table's rows and layout are final; the measure tool reports an overfull cell and the height."""
    specs, w, numeric = _width_plan(t)
    named = {j: widths[c.printed] for j, c in enumerate(t.columns) if c.printed in widths}
    if len(named) != len(widths) or any(specs[j] is not None for j in named):
        raise ValueError(f"set_widths: a named column is not a wrapping column of the table: {sorted(widths)}")
    plan = {**w, **named}
    if sum(plan.values()) > sum(w.values()) + spare:
        raise ValueError(f"set_widths: the widths add {sum(plan.values()) - sum(w.values()):.3f} in to the writer's plan (at most {spare})")
    t.fixed_plan = (specs, plan, numeric)


def tied(text: str, *phrases: str) -> Cell:
    """A typed label (checked as any label) whose phrases never break at their spaces ("post hoc", "free analysis 12"): the spaces inside
    each phrase print as no-break spaces."""
    label(text)
    out = text
    for ph in phrases:
        if ph not in out:
            raise ValueError(f"{ph!r} is not in {text!r}")
        out = out.replace(ph, ph.replace(" ", NBSP))
    return Cell(out, kind="label")


TIES = ("post hoc", "free analysis 3", "free analysis 12")      # phrases of the source labels that never break


def _which(text: str) -> Cell:
    """A source label (Edith, proof 4: one form, "tier (source)"), its tied phrases kept whole."""
    return tied(text, *[ph for ph in TIES if ph in text])


def _prose_interval(lo: Ref, hi: Ref, dp: int = 2, bounds=()) -> Cell:
    """A 95% interval inside a note sentence, in the prose form "-13.58 to +14.95" (Edith §2.4): each end signed, as a point estimate is;
    a table cell keeps "[lo, hi]"."""
    return joined(num(lo, dp=dp, signed=True, bounds=bounds), label("to"), num(hi, dp=dp, signed=True, bounds=bounds))


def _none_text(r: Ref) -> Cell:
    """A break-even cell that is stamped text, not a number ("no break-even within 10 tries" for fa12's Haiku-max rows, "... within 40
    samples" for item 9d's), printed with D-161's word: "tries" becomes "samples". The stamped text stays the cell's raw value and
    source; only that one word changes."""
    v = str(r.value)
    if not v.startswith("no break-even within"):
        raise ValueError(f"{r.source}:{r.key} = {v!r} is not the stamped 'no break-even within ...' text")
    return Cell(re.sub(r"\btries\b", "samples", v), raw=r.value, refs=(r,))


def _form(f: str) -> Cell:
    return label("pooled" if f == "pooled" else shape(f))


def _fmt(S: Store, tag: str, f: str) -> Cell:
    """Format compliance (%) of a setting's samples at 6 steps, at two decimals as the accuracies beside it (the supplement keeps every
    exact value): per shape, or chains / pieces for a pooled row (no pooled value is stamped)."""
    if f == "pooled":
        return joined(_fmt(S, tag, "1x6"), label("/"), _fmt(S, tag, "6x1"))
    return pct(S.ref("s1b", join_key(*FRT, tag, f, "format_compliance")), dp=2)


def _exposed_count(S: Store) -> Cell:
    """The number of partly shown base puzzles in the six-step set: fa9's base puzzles minus those Test B3 (the six-step test) keeps in
    the pre-registered exposed-base sensitivity; checked against the stamped list of left-out ids for that set."""
    set6 = S.get("s1b", "completeness.B3.set_id")
    if S.get("s1b", "completeness.B3.N") != 6 or S.get("s1b", "constants.test_sets.B3") != set6:
        raise ValueError("Test B3 is not on the six-step set: the partly-shown count below would be wrong")
    d = derive("fa9 base puzzles (6-step set) minus the base puzzles Test B3 keeps in the exposed-base sensitivity", lambda a, b: a - b,
               S.ref("fa9", "result.sh-vs-om.paired.pooled.n"), S.ref("s1b", "sensitivity_exposed_bases_excluded.bases_per_test.B3"))
    if d.value != len(S.get("s1b", join_key("sensitivity_exposed_bases_excluded", "excluded", set6))):
        raise ValueError("the derived partly-shown count differs from the stamped list of left-out ids")
    return num_d(d, dp=0)


def _count_word(c: Cell, words: Mapping[int, str]) -> Cell:
    """A derived count printed as a word ("two"), through a typed mapping that refuses any other value (the cell keeps its refs and
    formula; Edith's number style: a count under ten is a word in a sentence)."""
    if c.raw not in words:
        raise ValueError(f"the count {c.raw!r} has no printed word in {dict(words)}: the note's sentence would be wrong")
    return Cell(words[int(c.raw)], raw=c.raw, refs=c.refs, formula=c.formula)


@output("TAB-29")
@main_text
def tab_29(S: Store) -> Table:
    rows: List[List[Cell]] = []
    paper: List[List[Cell]] = []                     # the paper's version (D-159, D-160, D-161): the same refs, d at one decimal
    acc_refs: List[Ref] = []                         # Sonnet-high's accuracy in every row: one value, so a note, not a column
    n_refs: List[Ref] = []                           # the puzzle count of every row: one value, so a note, not a column
    fmt_cells: List[Cell] = []                       # Sonnet-high's format compliance in every row: one value, so a note, not a column
    n_ref = S.ref("fa9", "result.sh-vs-om.paired.pooled.n")
    for tag in ("ol", "om", "hx", "sm"):
        b = f"result['sh-vs-{tag}']"
        cmp_name = S.get("fa9", f"{b}.comparator")
        house = STUDY1B_TAGS[tag][0]
        several = S.get("s1b", join_key("descriptive", "arms", f"{tag}@6", "tries_per_item")) > 1
        want = f"One {house} sample" if tag == "hx" else (f"One {house} answer" if several else house)
        if PAPER_COMPARATOR.get(cmp_name) != want or (tag == "hx" and not several):
            raise ValueError(f"fa9 {b}: the stamped comparator {cmp_name!r} is not printed as {want!r} in the paper's names")
        for f in FORMS:
            p = f"{b}.paired.{f}"
            if S.get("fa9", p + ".n") != n_ref.value:
                raise ValueError(f"fa9 {p}: n differs from the caption's puzzle count")
            n_refs.append(S.ref("fa9", p + ".n"))
            lo, hi = ci_refs(S, "fa9", p + ".ci95")
            ratio = num(S.ref("fa9", f"{b}.cost_ratio.{f}"), dp=2)
            acc_refs.append(S.ref("fa9", f"{b}.sonnet_high_mean.{f}"))
            fmt_cells.append(_fmt(S, "sh", f))
            rows.append([text_of(S.ref("fa9", f"{b}.comparator"), FULL_COMPARATOR), _form(f),
                         num(S.ref("fa9", f"{b}.comparator_mean.{f}"), dp=2), _fmt(S, tag, f),
                         pts(S.ref("fa9", p + ".d")), interval(lo, hi, dp=2, signed=True, bounds=(0.0,)),
                         ratio, num(S.ref("fa9", f"{b}.cpc_ratio.{f}"), dp=2)])
            paper.append([text_of(S.ref("fa9", f"{b}.comparator"), PAPER_COMPARATOR),
                          label("pooled" if f == "pooled" else SHAPE_PLURAL[shape_word(f)]),
                          joined(pts(S.ref("fa9", p + ".d"), dp=1), interval(lo, hi, dp=1, signed=False, bounds=(0.0,))), ratio])
    cols = ["Comparator", "Shape", "Comparator accuracy (%)", "Comparator format compliance (%)",
            "d (points), Sonnet-high minus comparator", "95% interval (paired bootstrap)",
            "List cost ratio per answer (Sonnet-high / comparator)", "Cost-per-correct ratio (Sonnet-high / comparator)"]
    # Sonnet-high's format compliance is stamped by shape (a pooled row printed the chain's and the pieces' as "x / y"): the distinct
    # stamped values, in the order the rows read them
    fmt_refs: List[Ref] = []
    for c in fmt_cells:
        fmt_refs += [r for r in c.refs if all((r.source, r.key) != (q.source, q.key) for q in fmt_refs)]
    fmt_value = pct(fmt_refs[0], dp=2).printed
    if len({r.value for r in acc_refs}) != 1 or len({num(r, dp=2).printed for r in acc_refs}) != 1 \
            or len({S.get("fa9", f"result['sh-vs-{tag}'].paired.{f}.n") for tag in ("ol", "om", "hx", "sm") for f in FORMS}) != 1 \
            or {pct(r, dp=2).printed for r in fmt_refs} != {fmt_value} \
            or {c.printed for c in fmt_cells} - {fmt_value, f"{fmt_value} / {fmt_value}"}:
        raise ValueError("TAB-29: Sonnet-high's accuracy or format compliance, or the puzzle count, differs between rows: the three "
                         "dropped constant columns would need to be printed again")
    # each dropped column's one value keeps every row's refs (the ledger ties each row's value to its own stamped key)
    n_cell = Cell(integer(n_ref).printed, raw=n_ref.value, refs=tuple(n_refs), formula="one value, equal in every row (checked)")
    acc_cell = Cell(num(acc_refs[0], dp=2).printed, raw=acc_refs[0].value, refs=tuple(acc_refs),
                    formula="one value, equal in every row (checked)")
    fmt_cell = Cell(pct(fmt_refs[0], dp=2).printed, raw=fmt_refs[0].value, refs=tuple(fmt_refs),
                    formula="one value, equal in every row and shape (checked)")
    notes = [[label("Label:"), _glue(text_of(S.ref("fa9", "result.label")), label("."))],
             [label("Every row is on the"), n_cell, label("puzzles of Study 1b's 6-step set, as a chain and as pieces. In every row, "
                                                          "Sonnet-high's accuracy is"),
              _glue(acc_cell, label("%")), label("and its format compliance, in both shapes, is"), _glue(fmt_cell, label("%."))],
             [label("The 6-step set includes"), _exposed_count(S), text_of(S.ref("fa9", "result.note"), {FA9_NOTE: FA9_NOTE_PRINTED})],
             [label("95% interval: the paired BCa (bias-corrected and accelerated) bootstrap over puzzles, B ="),
              _glue(integer(S.ref("fa9", "code.B")), label("."))],
             [label("Sonnet's default effort is high; Test 5 compared Opus-low with Sonnet-medium on Study 1's puzzles. These rows are on "
                    "Study 1b's 6-step set, so set beside Test 5 they are a reading across studies: our reading, not a test.")],
             [label("Format compliance is the share of answered samples in the required answer format; in the pooled rows it is given per "
                    "shape, 1×6 / 6×1.")]]
    tries = [("Sonnet-high", "sh"), ("Opus-low", "ol"), ("Sonnet-medium", "sm"), ("Opus-medium", "om"), ("Haiku-max", "hx")]
    n_cap: List[Cell] = [label("puzzles: "), integer(n_ref), label(" (Study 1b's 6-step set), each as a chain (1×6) and as pieces "
                                                                   "(6×1); samples per puzzle and shape: ")]
    for i, (name, tag) in enumerate(tries):
        sep = "" if i == 0 else (" and " if i == len(tries) - 1 else ", ")
        n_cap += [label(sep + name + " "), integer(S.ref("s1b", join_key("descriptive", "arms", f"{tag}@6", "tries_per_item")))]
    n_cap += [label("; a setting with several samples contributes each puzzle's mean over them (its one-sample accuracy)")]
    caption = {"tier": [label("post hoc exploratory (free analysis 9); beside Test 5, a reading across studies: our reading, not a test")],
               "study": [label("Study 1b, 6-step set")],
               "n": _line(*n_cap),
               "interval": [label("paired BCa bootstrap over puzzles, 95%, B ="), integer(S.ref("fa9", "code.B"))],
               "price": [label("list price")]}
    t = Table([label(c) for c in cols], rows, notes, caption, layout="landscape", groups=[3, 6, 9], spaced=True)
    # the paper's version (Vision's plan §3: Comparator · Shape · d [95% interval] · Cost ratio; D-161): d and its interval at one decimal
    # (the interval's positive end unsigned), the list cost ratio at 2 decimals as the full table prints it; accuracies, format
    # compliance, n and the cost-per-correct ratio stay in the supplement's full table. d and its interval share one cell, as in TAB-01's
    # and TAB-24's paper versions. Four comparator groups, the comparator printed once per group (Edith's proof-2 reading, §7.7).
    # Notes, two lines together: the two columns' definitions (what d is the difference of, the cost ratio's two ends) are in their
    # headers, as the full table has them; the caption carries "paired", the bootstrap and the list price. The one note that remains
    # besides the pooled rows' meaning is fa9's disclosure of the partly shown puzzles (the full table's note 3), a companion of every
    # Sonnet-high result on this set (Edith's labels reading, condition 2), printed from the same stamped note.
    # The paper's caption drops the free-analysis number and keeps the post hoc mark (Vision and Edith, proof 2).
    main_caption = {**caption, "tier": [label("post hoc\u2020 exploratory; beside Test 5, a reading across studies: our reading, not a test")]}
    main_notes = [[label("Pooled: each puzzle's chain and pieces together.")],
                  [label("The 6-step set includes"), _count_word(_exposed_count(S), {2: "two"}),
                   text_of(S.ref("fa9", "result.note"), {FA9_NOTE: FA9_NOTE_PAPER})]]
    main_cols = ("Comparator", "Shape", "d (points), Sonnet-high minus comparator [95% interval]",
                 "Cost ratio per answer (Sonnet-high / comparator)")
    t.main_table = check_paper_words(Table([label(c) for c in main_cols], paper, main_notes, main_caption, short_notes=[0, 1],
                                           layout="float", groups=[3, 6, 9], once=[0]), "TAB-29")
    return t


def _side_shape(t: str) -> Tuple[str, str]:
    """Study 1's k.json side and shape for Tests 1-3 (from the names module's design table)."""
    _, _ch, cmp_, shp, kk = STUDY1_TESTS[t]
    return ("opus" if kk == "O" else "sonnet"), shp


def _locked(S: Store, t: str) -> Tuple[Ref, Tuple[Ref, Ref]]:
    """The locked d and 95% interval: Study 1's as_deployed test, or Study 1b's (primary margin) B1 or B2."""
    src, base = ("s1b", f"{S1B_VIEW}.tests.{t}") if t in ("B1", "B2") else ("main", f"{S1_VIEW}.tests.{t}")
    return S.ref(src, base + ".d"), ci_refs(S, src, base + ".ci95")


def _same_comparison(S: Store, t: str, k: int, at_list: bool) -> Optional[Tuple[Ref, Tuple[Ref, Ref], str]]:
    """Edith's rule (ops/reviews/2026-10-15-free-analyses-1.md §11): one comparison, one interval. A re-priced row that is the same
    comparison (same arms, same k, same set) as a result printed elsewhere takes that result and its tier: the locked test at its own k
    (Tests 1-3, B2; this covers every rho_list row and Test 1 held at k = 40); B2's vote at k = 1 is Test B1 (one Haiku-max try against
    Opus-medium on the same 16-step set); B2's vote at another k from 2 to 10 is free analysis 3's pooled row at that k. Returns (d,
    (lo, hi), source text) or None (the row keeps free analysis 12's own interval)."""
    if t == "B2":
        if k == int(S.get("s1b_k", "k")):
            d, ci = _locked(S, "B2")
            return d, ci, "confirmatory (" + STUDY1B_TESTS["B2"][0] + ")"
        if k == 1:
            d, ci = _locked(S, "B1")
            return d, ci, "confirmatory (" + STUDY1B_TESTS["B1"][0] + ": the same comparison as a one-sample vote)"
        for i, r in enumerate(S.get("fa3", "result.by_k")):
            if int(r["k"]) == k:
                b = f"result.by_k.{i}.pooled"
                return S.ref("fa3", b + ".d"), ci_refs(S, "fa3", b + ".ci95"), "post hoc (free analysis 3 at this\u00a0k)"
        return None
    side, shp = _side_shape(t)
    if at_list or k == int(S.get("main_k", f"k_from_rows.{side}.{shp}.k")):
        d, ci = _locked(S, t)
        return d, ci, "confirmatory (" + STUDY1_TESTS[t][0] + ")"
    return None


def _cap(S: Store, t: str) -> Ref:
    """The samples drawn per puzzle and shape that fa12 holds k' to: 40 Haiku-medium samples (Study 1), 10 Haiku-max samples (B2)."""
    if t == "B2":
        return S.ref("s1b_k", "samples_drawn")
    side, shp = _side_shape(t)
    return S.ref("main_k", f"k_from_rows.{side}.{shp}.samples_drawn")


def _same_value(S: Store, what: str, refs: List[Tuple[str, str]]) -> None:
    """A caption states one value for several stamped keys: refuse unless they are all equal."""
    vals = {S.get(src, key) for src, key in refs}
    if len(vals) != 1:
        raise ValueError(f"{what}: the stamped values differ ({sorted(map(str, vals))})")


def _tab30_n(S: Store) -> List[Cell]:
    """Puzzles and samples behind each part of TAB-30, every count read from its stamped key (checks that one printed count holds
    for every row it covers)."""
    s1_n = "result.tests.t1.by_rho.0.paired.n"
    _same_value(S, "Study 1 base puzzles", [("fa12", f"result.tests.{t}.by_rho.{i}.paired.n") for t, _ in TESTS[:3]
                                             for i, e in enumerate(S.get("fa12", f"result.tests.{t}.by_rho")) if int(e.get("k", 0)) >= 1]
                + [("fa12", s1_n)] + [("main", f"{S1_VIEW}.tests.{t}.n") for t, _ in TESTS[:3]])
    _same_value(S, "Study 1 samples drawn", [("main_k", f"k_from_rows.{_side_shape(t)[0]}.{_side_shape(t)[1]}.samples_drawn")
                                             for t, _ in TESTS[:3]])
    item24 = ("reporting", "group_b", "item_24", "table")
    one = sorted({f"{STUDY1_TESTS[t][2]} {STUDY1_TESTS[t][3]}" for t, _ in TESTS[:3]})
    for a in one:
        if S.get("main", join_key(*item24, a, "refusals_and_truncations", "tries")) != S.get("main", join_key(*item24, a, "base_puzzles")):
            raise ValueError(f"{a} is not a one-try arm")
    one_try = num_d(derive("tries / base_puzzles", lambda a, c: a / c,
                           S.ref("main", join_key(*item24, one[0], "refusals_and_truncations", "tries")),
                           S.ref("main", join_key(*item24, one[0], "base_puzzles"))), dp=0)
    cells9d = list(S.get("main", "reporting.group_b.item_9d.cells"))
    _same_value(S, "item 9d base puzzles", [("main", join_key("reporting", "group_b", "item_9d", "cells", c, "n_bases")) for c in cells9d]
                + [("fa12", s1_n)])
    b2 = S.get("fa12", "result.tests.B2.by_rho")
    _same_value(S, "Test B2 base puzzles", [("fa12", f"result.tests.B2.by_rho.{i}.paired.n") for i, e in enumerate(b2) if int(e.get("k", 0)) >= 1]
                + [("s1b", f"{S1B_VIEW}.tests.B1.n"), ("s1b", f"{S1B_VIEW}.tests.B2.n")])
    if S.get("s1b", "completeness.B2.N") != 16 or S.get("s1b", "completeness.B1.N") != 16:
        raise ValueError("Tests B1 and B2 are not both at 16 steps")
    be = "result.break_even_haiku_max"
    for n in ("6", "12", "16"):
        forms = list(S.get("fa12", join_key(*be.split("."), f"N={n}")))
        _same_value(S, f"break-even base puzzles at {n} steps",
                    [("fa12", join_key(*be.split("."), f"N={n}", f, "n_bases")) for f in forms])
        _same_value(S, "break-even k cap", [("fa12", join_key(*be.split("."), f"N={n}", f, "k_cap")) for f in forms]
                    + [("s1b_k", "samples_drawn")])
    _same_value(S, "break-even base puzzles at 12 and 16 steps",
                [("fa12", join_key(*be.split("."), f"N={n}", "pooled", "n_bases")) for n in ("12", "16")])
    _same_value(S, "Haiku-max tries per base puzzle and shape", [("s1b_k", "samples_drawn")]
                + [("s1b", join_key("descriptive", "arms", f"hx@{n}", "tries_per_item")) for n in ("6", "12", "16")])
    om = lambda n: integer(S.ref("s1b", join_key("descriptive", "arms", f"om@{n}", "tries_per_item")))   # noqa: E731
    return _line(
        label("Study 1: "), integer(S.ref("fa12", s1_n)), label(" puzzles per test, in the test's shape; the Haiku-medium vote "
                                                                "draws its k from "),
        integer(S.ref("main_k", "k_from_rows.opus.6x1.samples_drawn")), label(" samples per puzzle, and the comparator gives "),
        one_try, label(" sample per puzzle; Study 1's pre-specified Haiku-medium break-even uses the same puzzles per shape. "
                       "Study 1b: "
                       + STUDY1B_TESTS["B2"][0] + " and " + STUDY1B_TESTS["B1"][0] + " on "),
        integer(S.ref("fa12", "result.tests.B2.by_rho.0.paired.n")),
        label(" puzzles at 16 steps, each puzzle's chain and pieces pooled; the Haiku-max break-even on "),
        integer(S.ref("fa12", join_key(*be.split("."), "N=6", "pooled", "n_bases"))), label(" puzzles at 6 steps and "),
        integer(S.ref("fa12", join_key(*be.split("."), "N=12", "pooled", "n_bases"))),
        label(" at 12 steps and 16 steps. In Study 1b the Haiku-max vote draws its k from "), integer(S.ref("s1b_k", "samples_drawn")),
        label(" samples per puzzle and shape at every length, and Opus-medium's samples per puzzle and shape ("), om("6"),
        label(", "), om("12"), label(" and "), om("16"), label(" on the 6-step, 12-step and 16-step sets) are averaged"))


# A draw count, under any of these key names, anywhere in a stamped block (the shares and counts of particular replicates are not one).
DRAW_KEYS = ("B", "draws", "n_draws", "n_boot", "replicates", "n_replicates", "resamples", "n_resamples")


# The blocks of Study 1's locked file that stamp a draw count for their own resampling, none of them item 9d's break-even: the locked
# tests' views, the fairness checks, the secondary and ties analyses, the five-point view and group-B items 8b, 9f, 9g and 14.
OTHER_DRAWS = ("confirmatory", "fairness", "fairness_first_slip", "original_repeat_rule_appendix", "secondary", "ties",
               "reporting.five_point_view", "reporting.group_b.item_8b", "reporting.group_b.item_9f", "reporting.group_b.item_9g",
               "reporting.group_b.item_14")


def _no_draw_count(S: Store, src: str, key: str, others: Tuple[str, ...] = OTHER_DRAWS) -> None:
    """TAB-30's note says the locked file does not stamp item 9d's draw count (Edith's Q28). Walk the whole file and refuse a draw count
    under any key name anywhere except inside a block in `others` (each another analysis's own resampling): one in item 9d's block, at
    file level, at the reporting or group-B level, or in any new block stops the build."""
    own = parse_key(key)
    allowed = [parse_key(o) for o in others]
    for a in allowed:
        if own[:len(a)] == a or a[:len(own)] == own:
            raise ValueError(f"{src}:{key} overlaps the other-analysis block {format_key(a)}: its draw counts may be item 9d's")
        S.get(src, format_key(a))                    # each allowed block exists (a renamed block is not silently skipped)
    S.get(src, key)

    def walk(v: object, at: List[str]) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                here = at + [k]
                if any(here[:len(a)] == a for a in allowed):
                    continue                         # another analysis's block: its draw counts are its own
                if k in DRAW_KEYS:
                    raise ValueError(f"{src}:{format_key(here)} stamps a draw count outside the blocks of other analyses: it may be "
                                     "item 9d's, so print it instead of saying it is not stamped")
                walk(x, here)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, at + [str(i)])
    walk(S.doc(src), [])


def _tab30_interval(S: Store) -> List[Cell]:
    """The interval types: paired BCa (B read from fa12, checked equal for the locked tests, free analysis 3 and item 9f's cached view)
    and the cluster bootstrap of the break-even (fa12's draws; item 9d's draw count is not stamped, checked)."""
    _same_value(S, "paired BCa B", [("fa12", "code.B"), ("fa3", "code.B"), ("main", f"{S1_VIEW}.B"), ("s1b", f"{S1B_VIEW}.B"),
                                    ("main", "reporting.group_b.item_9f.family_row.family.B")])
    _no_draw_count(S, "main", "reporting.group_b.item_9d")
    return _line(label("gaps d and the cached view: paired BCa bootstrap over puzzles, 95%, B = "), integer(S.ref("fa12", "code.B")),
                 label(" (the same for the locked tests, free analysis 3 and free analysis 12); break-even: cluster bootstrap over "
                       "puzzles, 95%, "), integer(S.ref("fa12", "code.draws")),
                 label(" draws for the Haiku-max rows (free analysis 12); Study 1's pre-specified Haiku-medium break-even rows: the same "
                       "kind of interval from the locked analysis, whose draw count is not stamped"))


@output("TAB-30")
def tab_30(S: Store) -> Table:
    if float(S.get("main", f"{S1_VIEW}.margin")) != MARGIN:
        raise ValueError("Study 1's margin is not the module's MARGIN")
    rows: List[List[Cell]] = []
    for t, name in TESTS:
        tb = f"result.tests.{t}"
        rho_list = float(S.get("fa12", tb + ".rho_list"))
        for i, e in enumerate(S.get("fa12", tb + ".by_rho")):
            rb = f"{tb}.by_rho.{i}"
            rp = S.ref("fa12", rb + ".rho_prime")
            if int(e.get("k", 0)) < 1:
                rows.append([label(name), integer(rp), num(S.ref("fa12", rb + ".R_prime"), dp=2), integer(S.ref("fa12", rb + ".k")),
                             text_of(S.ref("fa12", rb + ".status")), DASH, DASH, DASH, DASH, DASH])
                continue
            src = _same_comparison(S, t, int(e["k"]), float(e["rho_prime"]) == rho_list)
            if src is not None:
                (d, (lo, hi), which_text) = src
                d_cell, ci_cell, which = pts(d), interval(lo, hi, dp=2, signed=True, bounds=(0.0,)), _which(which_text)
            else:
                p = rb + ".paired"
                lo, hi = ci_refs(S, "fa12", p + ".ci95")
                d_cell, ci_cell, which = pts(S.ref("fa12", p + ".d")), interval(lo, hi, dp=2, signed=True, bounds=(0.0,)), \
                    _which("post hoc (free analysis 12)")
            held_ref = S.ref("fa12", rb + ".held_to_samples")
            if held_ref.value is True:
                cap = _cap(S, t)
                if int(e["k"]) != int(cap.value):
                    raise ValueError(f"{t} at {e['rho_prime']}: held, but k {e['k']} is not the samples drawn {cap.value}")
                held = joined(text_of(held_ref, {True: "held at"}), integer(cap))
            else:
                held = text_of(held_ref, {False: ""})
            rows.append([label(name), integer(rp), num(S.ref("fa12", rb + ".R_prime"), dp=2), integer(S.ref("fa12", rb + ".k")),
                         held, num(S.ref("fa12", rb + ".vote_mean"), dp=2), num(S.ref("fa12", rb + ".comparator_mean"), dp=2), d_cell,
                         ci_cell, which])
    cols = ["Test", "Price ratio per token (comparator / Haiku)",
            "Samples per comparator answer", "Cost-matched k", "Held",
            "Vote accuracy at k (%)", "Comparator accuracy (%)", "Gap d (points)", "95% interval", "Source of d and interval"]
    # panel 1: item 9d's break-even for Haiku-max (fa12) and the stamped item 9d for Haiku-medium (Study 1)
    be_rows: List[List[Cell]] = []
    for n in ("6", "12", "16"):
        for f in ("1x6" if n == "6" else f"1x{n}", "6x1" if n == "6" else f"{n}x1", "pooled"):
            b = f"result.break_even_haiku_max['N={n}'].{f}"
            st = S.get("fa12", b + ".rho_star")
            lo, hi = ci_refs(S, "fa12", b + ".ci95")
            km = S.ref("fa12", b + ".k_match")
            be_rows.append([label(f"Haiku-max vs Opus-medium, {n} steps"), _form(f) if f == "pooled" else label(shape(f)),
                            integer(km) if isinstance(km.value, int) else _none_text(km), num(S.ref("fa12", b + ".R_list"), dp=2),
                            num(S.ref("fa12", b + ".rho_star"), dp=2) if isinstance(st, (int, float)) else _none_text(S.ref("fa12", b + ".rho_star")),
                            interval(lo, hi, dp=2, open_text={"unbounded": "unbounded"}),
                            pct(S.ref("fa12", b + ".share_replicates_no_k_match"), dp=2), _which("post hoc (free analysis 12)")])
    for cell in ("opus-med:1x6", "opus-med:6x1", "sonnet-med:1x6", "sonnet-med:6x1"):
        b = f"reporting.group_b.item_9d.cells['{cell}']"
        comp, sh_ = cell.split(":")
        st = S.get("main", b + ".rho_star")
        lo, hi = ci_refs(S, "main", b + ".ci95")
        km = S.ref("main", b + ".k_match")
        be_rows.append([label("Haiku-medium vs " + ("Opus-medium" if comp == "opus-med" else "Sonnet-medium") + ", 6 steps"),
                        label(shape(sh_)), integer(km) if isinstance(km.value, int) else _none_text(km), num(S.ref("main", b + ".R_list"), dp=2),
                        num(S.ref("main", b + ".rho_star"), dp=2) if isinstance(st, (int, float)) else _none_text(S.ref("main", b + ".rho_star")),
                        interval(lo, hi, dp=2, open_text={"unbounded": "unbounded"}),
                        pct(S.ref("main", b + ".share_replicates_no_k_match"), dp=2), label("pre-specified (item 9d, Study 1)")])
    be = Table([label(c) for c in ("Vote vs comparator", "Shape", "Smallest k reaching the comparator's accuracy",
                                   "Samples per comparator answer",
                                   "Break-even price ratio", "95% interval", "Replicates with no break-even (%)", "Label")], be_rows)
    # panel 2: item 9f's cached view (Study 1, stamped)
    cv_rows: List[List[Cell]] = []
    cv_reading: List[Ref] = []                       # each test's reading under the cached view: one reading in every row, so a note
    cv_held: List[Tuple[str, str]] = []
    fam = "reporting.group_b.item_9f.family_row.family.tests"
    for t, name in TESTS[:3]:
        f9 = f"reporting.group_b.item_9f.{t}"
        lo, hi = ci_refs(S, "main", f"{fam}.{t}.ci95")
        cv_rows.append([label(name), integer(S.ref("main", f"{f9}.cached_k")),
                        pts(S.ref("main", f"{fam}.{t}.d"), margin=MARGIN), interval(lo, hi, dp=2, signed=True, bounds=(0.0, MARGIN))])
        cv_reading.append(S.ref("main", f"{fam}.{t}.reading"))
        kc, cap = int(S.get("main", f"{f9}.cached_k")), int(S.get("main", f"{f9}.k_cap"))
        if kc == cap:
            if not float(S.get("main", f"{f9}.mean_cached_cost_by_k.{cap - 1}")) < float(S.get("main", f"{f9}.comparator_mean_list_cost")):
                raise ValueError(f"{t}: cached k at the cap, but the cached cost there is not below the comparator's")
            cv_held.append((name, f9))
    if len({r.value for r in cv_reading}) != 1:
        raise ValueError("the cached view's readings differ between the tests: the dropped constant column would need to be printed again")
    cv = Table([label(c) for c in ("Test", "Cached k", "d (points)", "95% interval")], cv_rows, layout="float")
    if S.get("main", "reporting.group_b.item_9f.label") != "cached view (offline re-pricing)":
        raise ValueError("Study 1's cached view is no longer stamped as offline re-pricing: the panel title would be wrong")
    # Test 3's marking-rule qualifier (style sheet: Test 3 always travels with it), worded and read as TAB-02's footer.
    o3 = "secondary.original_repeat_rule.tests.t3"
    t3_name = STUDY1_TESTS["t3"][0]
    o3lo, o3hi = ci_refs(S, "main", f"{o3}.ci95")
    lead = "Under the original pre-registered marking rule, which Deviation 2 kept as a sensitivity check, "
    if S.get("main", f"{o3}.reading") != S.get("main", f"{S1_VIEW}.tests.t3.reading"):
        verdict = [label(f"{lead}{t3_name} would read "), text_of(S.ref("main", f"{o3}.reading")), label(" instead of "),
                   text_of(S.ref("main", f"{S1_VIEW}.tests.t3.reading"))]
    else:
        verdict = [label(f"{lead}{t3_name}'s reading is unchanged: "), text_of(S.ref("main", f"{o3}.reading"))]
    notes = [[label("The stamped label of free analysis 12 reads"), _glue(_quoted(text_of(S.ref("fa12", "result.label"))), label(";")),
              label("its \"equal-money\" is cost-matched.")],
             [label("Samples per comparator answer: the comparator's cost per answer divided by the cost of one Haiku sample (at the "
                    "price ratio in the row; in Panel 1, at list price).")],
             [label("The price ratio is per token, comparator over Haiku, the same for input and output (the pinned table's is"),
              num(S.ref("fa12", "result.tests.t1.rho_list"), dp=0), label("for Opus and"), num(S.ref("fa12", "result.tests.t3.rho_list"), dp=0),
              label("for Sonnet); token counts are held as measured. At the list ratio each row is the locked test and prints its d and "
                    "interval.")],
             [label("One comparison, one interval: any other re-priced row that is the same comparison as a printed result (the same "
                    "settings, k and puzzle set) takes that result and its label, named in the last column. A Test 1 row held at the "
                    "locked test's k is Test 1 as run; Test B2's one-sample vote is Test B1 (one Haiku-max sample against Opus-medium on "
                    "the same 16-step set); its votes at other k are free analysis 3's rows at that k. The remaining rows are post hoc "
                    "(free analysis 12), with no reading.")],
             [label("Held: the cost-matched k at that price exceeds the samples drawn per puzzle and shape, so k is held at that "
                    "number.")],
             [label("Accuracies in the main panel are given to two decimals, as the tests' own tables give them, so a row that is a "
                    "locked test prints the same numbers; d always has two. d is the difference of the unrounded accuracies, so it can "
                    "differ in its last digit from the difference of the two printed accuracies.")],
             _line(*verdict, label(" (d = "), pts(S.ref("main", f"{o3}.d"), margin=MARGIN), label(" points, 95% interval "),
                   _prose_interval(o3lo, o3hi, bounds=(0.0, MARGIN)), label(").")),
             [label("A break-even interval end is \"unbounded\" when too many replicates never reach the comparator's accuracy within the "
                    "samples drawn; the share of such replicates is shown.")],
             _line(label("Break-even intervals (Panel 1): the Haiku-max rows' cluster bootstrap uses "),
                   integer(S.ref("fa12", "code.draws")),
                   label(" draws (free analysis 12); the Haiku-medium rows are Study 1's pre-specified break-even (item 9d), whose "
                         "interval comes from the locked analysis, and the locked file does not stamp its number of draws, so none is "
                         "given here."))]
    # the one reading keeps every test's ref (the ledger ties each test's reading to its own stamped key)
    cv_cell = Cell(text_of(cv_reading[0]).printed, raw=cv_reading[0].value, refs=tuple(cv_reading),
                   formula="one reading, equal in every test (checked)")
    notes.append(_line(label("Cached view: the reading from the pre-registered decision rule, applied to the cached view's interval, is "),
                       _glue(cv_cell, label(" in every test (Tests 1–3)."))))
    for name, f9 in cv_held:
        notes.append(_line(label(f"Cached view: {name}'s cached k is held at the cap of "), integer(S.ref("main", f"{f9}.k_cap")),
                           label(" samples drawn; the cached cost of that many samples is still below the comparator's list cost per "
                                 "answer.")))
    caption = {"tier": [label("post hoc sensitivity (free analysis 12), beside Study 1's pre-specified break-even price ratio and cached "
                              "view; a row that is the same comparison as a printed result reprints it with its label (confirmatory: Tests "
                              "1–3, B1 and B2 as run; post hoc: free analysis 3)")],
               "study": [label("Study 1, main run (Tests 1–3; the pre-specified break-even price ratio and cached view), and Study 1b "
                               "(Tests B1 and B2; the Haiku-max break-even)")],
               "set": [label("Study 1: the main-run puzzle set at 6 steps; Study 1b: the 16-step set for Tests B1 and B2, and the "
                             "6-step, 12-step and 16-step sets for the Haiku-max break-even")],
               "n": _tab30_n(S),
               "interval": _tab30_interval(S),
               "price": [label("list prices of the pinned table, re-scaled per row")]}
    be.layout, be.groups = "landscape", [3, 6, 9, 11]
    # Panel 1 at the widths that keep every row at two lines. The writer's plan leaves the six rows with "no break-even within N samples"
    # at three lines in both of its columns (0.76 in of height, proof 4 checker): "Samples per comparator answer" cannot break
    # "comparator", so that column takes 0.68 in and the two text columns get less. Three widths sit 0.003 to 0.008 in above the narrowest
    # at which the writer's wrap estimate sets the longest cell in two lines: 1.05 in "within 40 samples", 1.05 in the same in the
    # break-even column, 1.09 in "(item 9d, Study 1)". The first column, "Vote vs comparator", is the exception: its 1.352 in is below the
    # estimate's two-line width (1.379 in; at 1.352 the estimate sets "Haiku-medium vs Sonnet-medium, 6 steps" in three lines, so
    # height_in reads 5.26 in where the measured table is 5.00 in). TeX sets the longest line, "Sonnet-medium, 6 steps", inside it with
    # only about 0.7 pt to spare, less than the 0.04 in the estimate keeps beyond a column's text. That fit rests on TeX's own setting,
    # which the measure tool checks and the estimate does not. A width of 1.379 in would need `spare` raised from 0.11 to about 0.135 in.
    set_widths(be, {"Vote vs comparator": 1.352, "Smallest k reaching the comparator's accuracy": 1.052, "Break-even price ratio": 1.047,
                    "Label": 1.086})
    return Table([label(c) for c in cols], rows, notes, caption, layout="landscape", groups=[4, 8, 12],
                 panels=[("Break-even price ratio", be), (CV_TITLE, cv)])
