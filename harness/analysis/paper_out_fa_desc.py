"""Free-analysis descriptive tables (post hoc, D-131): the plan's TAB-28 (Haiku with thinking off: format failures and wrong answers;
free analysis 8) and TAB-31 (wrong-answer repeat share by effort and length, with a panel for the 16-step Haiku-max vote by Haiku-medium
difficulty bin and wrong-try agreement thirds within each bin, a post hoc variant of item 20's split; free analysis 6, bins per E-20).
Every cell is read by key from the pinned files: `fa8`, `fa6a`, `fa6b` and `fa4`, beside the locked Study 1 and Study 1b files
(`main`, `main_k`, `s1b`, `s1b_k`); see paper_out_core.py for the rules.

Nothing is computed here. Where a free-analysis file recounts a value the locked files already stamp (tries, format ok, status counts and
accuracy in fa8; Study 1's Haiku-medium repeat share in fa6b; the hm@16 bin occupancy in fa6a and fa6b; the unbinned 16-step Haiku-max
curve in fa6b), the builder checks that the two agree and refuses to build otherwise; the locked file's value is the one printed, except
for the columns the plan asks from the recount. fa8's accuracy on all tries equals the locked accuracy and is not printed twice.

Tiers (TAB-28): Study 1's thinking-off arm is exploratory (item 10; C-047), its format figures pre-specified descriptive (items 16-17);
Study 1b's thinking-off rows are pre-specified descriptive (C-075); the recount is post hoc descriptive. fa8's "unparseable" is printed
as "format not ok": such a try can still carry a readable, even right, final answer (item 10's final_acc on Study 1's chains).

Units: Study 1's item_24 accuracies and Study 1b's arm accuracies are points (0-100); fa8's accuracies, every format compliance, the
repeat shares and fa6a's largest_bin_share are proportions (0-1); fa6b's bin means are points; fa4's exact95 is in the unit of the cell
it replaces (points here).
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence, Tuple

from .paper_out_core import (Cell, Ref, Store, Table, YES_NO, ci_refs, fa4_exact, integer, interval, join_key, joined, label, label_ok,
                             output, pct, text_of)
from .paper_out_names import EFFORT_ORDER, STUDY1B_TAGS, STUDY1_ARMS, main_text, shape, shape_word

DASH = label("—")                                   # does not apply / not stamped
STUDY_NAMES = {"study1": "Study 1", "study1b": "Study 1b"}
STUDY_ORDER = ("study1", "study1b")
NBSP = "\u00a0"                                      # a no-break space: the writer prints it "~", so a narrow column never breaks there
STACK = "\n\n"                                      # a forced line break inside a cell (a blank line is a paragraph break in a wrapping column;
                                                    # the writer passes it through, the CSV keeps it), as the paper's Table 2 stacks its ratios


# ---------------------------------------------------------------- helpers


def L(text: str) -> Cell:
    return label(text)


def note(*parts: Any) -> List[Cell]:
    """A footnote: strings become labels, cells stay as they are."""
    return [L(p) if isinstance(p, str) else p for p in parts]


def R(S: Store, src: str, *segs: Any) -> Ref:
    return S.ref(src, join_key(*segs))


def G(S: Store, src: str, *segs: Any) -> Any:
    return S.get(src, join_key(*segs))


def P(r: Ref, prop: bool) -> Cell:
    """An accuracy or share in %, two decimals (the supplement keeps every exact value, D-161 (2)), from a proportion (prop=True) or
    from points; one more decimal if rounding would reach 0 or 100 from inside."""
    return pct(r, dp=2, from_proportion=prop, bounds=(0.0, 100.0))


def chain_first(shapes: Sequence[str]) -> List[str]:
    """Shapes in reading order: the chain (1xN) before the pieces (Nx1)."""
    return sorted(shapes, key=lambda s: (0 if s.startswith("1x") else 1, s))


def entry_name(S: Store, src: str, *segs: Any) -> Cell:
    """A name that is itself a dict key in a file (a bin '[0,10)'), printed as stamped; the key must resolve."""
    S.get(src, join_key(*segs))
    name = str(segs[-1])
    return Cell(name, raw=name, refs=(Ref(name, src, join_key(*segs)),), formula="the name of this dict entry")


def number_in_text(r: Ref, pattern: str) -> Cell:
    """A number written inside a stamped text (a rule's threshold), printed as written there. `pattern` has one group and must match
    exactly once."""
    if not isinstance(r.value, str):
        raise TypeError(f"{r.source}:{r.key} is not a text")
    found = re.findall(pattern, r.value)
    if len(found) != 1 or not re.fullmatch(r"\d+", found[0]):
        raise ValueError(f"{r.source}:{r.key}: {pattern!r} matched {found!r}")
    return Cell(found[0], raw=r.value, refs=(r,), formula=f"the number matched by {pattern} in the stamped text")


def acc_cell(S: Store, src: str, segs: Sequence[Any]) -> Tuple[Cell, bool]:
    """'mean' over '[lo, hi]' in %, at two decimals, from a block holding `mean` and `ci95` (points); the interval always stands on a
    line of its own under the mean (STACK), so every cell has one shape and the column is as narrow as its widest line, the interval (a
    one-line "22.00 [16.97, 27.31]" made the column wider and the not-ok statuses beside it taller). The writer's wrap estimate reads
    STACK's blank line as an ordinary space, so it plans the column a little wider than that line (it sizes the column for the
    one-line "1.00 [0.00, 2.25]", 0.85 in, where "[16.97, 27.31]" needs 0.71 in) and `height_in` reads the table short (2.62 in against
    2.79 in measured). A plan that knew about the breaks gives the same line counts, so the output is not affected; the measure tool has
    the real height. Where the stamped interval collapsed, free analysis 4's exact (Clopper–Pearson) 95% interval replaces it, marked
    '(exact)' on a line of its own (core.fa4_exact checks it is fa4's copy of that very interval); revision 2 covers every collapsed
    ci95 in these files, so a collapsed one it does not replace refuses the build. Returns the cell and whether it is exact."""
    mean = P(R(S, src, *segs, "mean"), prop=False)
    lo, hi = ci_refs(S, src, join_key(*segs, "ci95"))
    if lo.value != hi.value:
        return joined(mean, interval(lo, hi, dp=2, bounds=(0.0, 100.0)), sep=STACK), False
    ex = fa4_exact(S, src, join_key(*segs))
    if ex is None:
        raise ValueError(f"{src}:{join_key(*segs)}: the interval collapsed and free analysis 4 stamps no exact replacement")
    return joined(mean, interval(ex.lo, ex.hi, dp=2, scale=ex.scale, bounds=(0.0, 100.0)), L("(exact)"), sep=STACK), True


def check(cond: bool, what: str) -> None:
    if not cond:
        raise ValueError(f"cross-check failed: {what}")


# ================================================================ TAB-28

STATUS_NAMES = {"answer_mismatch": "answer mismatch", "extra_line": "extra line", "misnumbered": "misnumbered",
                "missing_line": "missing line", "no_answer": "no answer", "non_integer": "non-integer", "wrong_length": "wrong length"}
ITEM24 = ("reporting", "group_b", "item_24", "table")
FORMAT_REPORT = ("descriptive", "format_refusals_truncations_missing", "format_report")
OFF_TAG = "ho"                                      # Study 1b's tag for Haiku with thinking off
OFF_ARM = "haiku-thinking-off"                      # Study 1's arm id for it


def _fa8_keys(S: Store) -> List[Tuple[str, int, str, str]]:
    """fa8's rows as (study, steps, shape, key), Study 1 first, then by length, chain before pieces."""
    rows = []
    for k in S.keys("fa8", "result"):
        if k == "note":
            continue
        study, n, sh = k.split(":")
        rows.append((STUDY_ORDER.index(study), int(n), 0 if sh.startswith("1x") else 1, study, sh, k))
    return [(study, n, sh, k) for _, n, _, study, sh, k in sorted(rows)]


def _off_blocks(study: str, n: int, sh: str) -> Tuple[str, Tuple[Any, ...], Tuple[Any, ...], Tuple[Any, ...]]:
    """(source, steps key, format block, accuracy block) of the locked file's thinking-off row for one study, length and shape."""
    if study == "study1":
        return ("main", ("n",), (*ITEM24, f"{OFF_ARM} {sh}", "format_compliance"), (*ITEM24, f"{OFF_ARM} {sh}", "accuracy_interval"))
    return ("s1b", ("descriptive", "arms", f"{OFF_TAG}@{n}", "N"), (*FORMAT_REPORT, OFF_TAG, sh), ("descriptive", "arms", f"{OFF_TAG}@{n}", sh))


def _status_cell(S: Store, src: str, fmt: Sequence[Any]) -> Cell:
    """The not-ok format statuses with their counts, most frequent first (e.g. 'missing line 220; extra line 46')."""
    counts = G(S, src, *fmt, "status_counts")
    order = sorted((s for s in counts if s != "ok"), key=lambda s: (-counts[s], s))
    if not order:
        return L("none")
    # a status is tied to its count with no-break spaces, so a narrow column breaks the list only after a semicolon
    return joined(*[joined(L(STATUS_NAMES[s].replace(" ", NBSP)), integer(R(S, src, *fmt, "status_counts", s)), sep=NBSP)
                    for s in order], sep="; ")


ITEM10 = ("reporting", "group_b", "item_10", "arms")
ITEM14 = ("reporting", "group_b", "item_14", "by_final_answer")


def s1_tries_per_puzzle(S: Store, arm: str, sh: str) -> Ref:
    """Study 1's tries drawn per puzzle for an item 10 arm: its own-k block's stamped samples_drawn (the same for both comparators),
    checked against the arm's try count over its base puzzles and against its vote curve's largest vote size."""
    own = (*ITEM10, f"{arm} {sh}", "own_k")
    drawn = {G(S, "main", *own, c, "k_value", "samples_drawn") for c in S.keys("main", join_key(*own))}
    check(len(drawn) == 1, f"{arm} {sh}: one samples_drawn over the own-k comparators")
    r = R(S, "main", *own, "vs opus-med", "k_value", "samples_drawn")
    check(G(S, "main", *ITEM10, f"{arm} {sh}", "counts", "tries") == r.value * G(S, "main", *ITEM24, f"{arm} {sh}", "base_puzzles"),
          f"{arm} {sh}: tries = samples drawn x base puzzles")
    check(G(S, "main", *ITEM10, f"{arm} {sh}", "vote_curve", "k_max") == r.value, f"{arm} {sh}: samples drawn = the vote curve's k_max")
    return r


@output("TAB-28")
@main_text
def tab_28(S: Store) -> Table:
    # format compliance sits beside accuracy (style sheet, D-122)
    cols = ["Study", "Steps", "Shape", "Samples", "Format ok", "Format compliance (%)", "Accuracy (%) [95% interval]",
            "Not-ok format statuses", "Format not ok (post hoc)", "Format ok but wrong (post hoc)",
            "Right (post hoc)", "Accuracy on format-ok samples (%; conditional, post hoc)"]
    rows, any_exact = [], False
    for study, n, sh, k in _fa8_keys(S):
        src, steps_key, fmt, acc = _off_blocks(study, n, sh)
        steps = R(S, "main_k" if study == "study1" else src, *steps_key)
        fa = G(S, "fa8", "result", k)
        check(steps.value == n, f"{k}: steps")
        check(fa["tries"] == G(S, src, *fmt, "tries"), f"{k}: tries")
        check(fa["format_ok"] == G(S, src, *fmt, "format_ok"), f"{k}: format ok")
        check(fa["status_counts"] == G(S, src, *fmt, "status_counts"), f"{k}: status counts")
        check(fa["unparseable"] == fa["tries"] - fa["format_ok"], f"{k}: unparseable")
        check(fa["right_but_not_format_ok"] == 0, f"{k}: every right try is format ok")
        check(fa["unparseable"] + fa["parseable_but_wrong"] + fa["right"] == fa["tries"], f"{k}: the three counts add up to the tries")
        # the recount's accuracy on all tries is the locked accuracy (so it is not printed twice)
        check(abs(100.0 * fa["accuracy_all_tries"] - G(S, src, *acc, "mean")) < 1e-9, f"{k}: accuracy on all tries")
        cond = R(S, "fa8", "result", k, "accuracy_on_parseable_conditional")
        acc_c, ex = acc_cell(S, src, acc)
        any_exact = any_exact or ex
        rows.append([L(STUDY_NAMES[study]), integer(steps), L(shape(sh)), integer(R(S, src, *fmt, "tries")),
                     integer(R(S, src, *fmt, "format_ok")), P(R(S, src, *fmt, "format_compliance"), prop=True), acc_c,
                     _status_cell(S, src, fmt),
                     integer(R(S, "fa8", "result", k, "unparseable")), integer(R(S, "fa8", "result", k, "parseable_but_wrong")),
                     integer(R(S, "fa8", "result", k, "right")),
                     text_of(cond, {None: "no format-ok tries"}) if cond.value is None else P(cond, prop=True)])
    # Study 1's chains are the only thinking-off row with a stamped final-answer accuracy (item 10's rates block; pieces: none)
    rates = (*ITEM10, f"{OFF_ARM} 1x6", "rates")
    # the notes call the arm one of Study 1's pre-registered exploratory arms (item 10, named in plain words in this main-text table)
    check(all(f"{OFF_ARM} {sh}" in G(S, "main", *ITEM10) for sh in ("1x6", "6x1"))
          and str(G(S, "main", *ITEM10[:-1], "label")).startswith("exploratory"), "Study 1's thinking-off arm is an item 10 exploratory arm")
    check(G(S, "main", *ITEM10, f"{OFF_ARM} 6x1", "rates") is None, "Study 1 thinking-off pieces: no rates block")
    check(abs(100.0 * G(S, "main", *rates, "official_acc") - G(S, "main", *ITEM24, f"{OFF_ARM} 1x6", "accuracy_interval", "mean")) < 1e-9,
          "Study 1 thinking-off chains: item 10's official accuracy = item 24's accuracy")
    # on pieces the final answer is the whole answer: item 14 scores Study 1's thinking-off pieces by the official answer, and its
    # count of right tries is the recount's
    fin = (*ITEM14, f"{OFF_ARM} 6x1", "correct_final True")
    check(G(S, "main", *fin, "field") == "correct (= correct_final at 6x1)",
          "item 14: on pieces the final answer is the official answer")
    check(G(S, "main", *fin, "tries") == G(S, "fa8", "result", "study1:6:6x1", "right"), "item 14's right pieces tries = the recount's")
    notes = [
        note("Post hoc sample counts. Format not ok: the sample's official format status (the marking rule with Deviation 2) is not ok; "
             "the kinds are listed under not-ok format statuses. Format ok but wrong: format ok, answer wrong. Right: the official answer "
             "is right; every right sample is format ok, because the official rule scores a sample whose format is not ok as wrong. The "
             "three counts add up to the samples (both checked when the table is built)."),
        note("The post hoc analysis calls the format-not-ok samples \"unparseable\", but on chains such a sample can still carry a "
             "readable, even right, final answer. Scored on the final answer alone, Study 1's chains reach",
             joined(P(R(S, "main", *rates, "final_acc"), prop=True), L("%"), sep=""), "against the official",
             joined(P(R(S, "main", *rates, "official_acc"), prop=True), L("%"), sep=""),
             "(an exploratory setting). On pieces the final answer is the whole answer, so the two scores coincide (checked against Study "
             "1's stamped final-answer scoring); no other chain row has a stamped final-answer accuracy."),
        note("Accuracy on format-ok samples (the post hoc analysis calls it \"accuracy on parseable tries\") is the right answers among "
             "the format-ok samples divided by the format-ok samples. It is conditional on format and is not a whole-answer accuracy."),
        note("Labels. In Study 1, Haiku, thinking off, is one of the pre-registered exploratory settings, so its accuracy and 95% "
             "interval are exploratory values, read from Study 1's pre-specified table of every setup's results. The format columns (samples, "
             "format ok, format compliance and the not-ok statuses) are pre-specified descriptive in both studies (the pre-registered "
             "format rules). Study 1b's accuracy and interval are "
             "pre-specified descriptive. The columns marked post hoc are a post hoc descriptive recount of the per-sample scores; the "
             "recount's samples, format ok, statuses and accuracy on all samples agree with the locked values (checked when the table is "
             "built)."),
        note("Study 1 and Study 1b used different puzzle sets and different runs; set side by side, their rows are a reading across "
             "studies: our reading, not a test."),
    ]
    if any_exact:
        notes.append(note("(exact): the bootstrap interval collapsed to one value; the exact (Clopper–Pearson) 95% interval over "
                          "puzzles replaces it (post hoc presentation)."))
    t1 = (*ITEM24, f"{OFF_ARM} 1x6")
    tries_s1 = [s1_tries_per_puzzle(S, OFF_ARM, sh) for sh in ("1x6", "6x1")]
    check(tries_s1[0].value == tries_s1[1].value, "Study 1 thinking-off tries per puzzle by shape")
    tries_1b = [R(S, "s1b", "descriptive", "arms", f"{OFF_TAG}@{n}", "tries_per_item") for n in (6, 16)]
    check(tries_1b[0].value == tries_1b[1].value, "Study 1b thinking-off tries per item by length")
    itypes = {G(S, "s1b", "descriptive", "arms", f"{OFF_TAG}@{n}", sh, "interval") for n, sh in ((6, "1x6"), (6, "6x1"), (16, "1x16"),
                                                                                                    (16, "16x1"))}
    check(len(itypes) == 1, "one interval type for Study 1b's thinking-off rows")
    caption = {
        "tier": [L("Study 1: exploratory setting for the accuracy and its 95% interval, format columns pre-specified descriptive; Study 1b: "
                   "pre-specified descriptive; columns marked post hoc: post hoc descriptive recount")],
        "study": [L("Study 1 (main run, 6 steps) and Study 1b (6-step and 16-step sets), each row within one study")],
        "set": [L("Study 1: the main-run puzzle set; Study 1b: its 6-step and 16-step sets (other puzzles)")],
        "n": [L("puzzles: Study 1"), integer(R(S, "main", *t1, "base_puzzles")), L("; Study 1b 6-step set"),
              integer(R(S, "s1b", "descriptive", "arms", f"{OFF_TAG}@6", "1x6", "n_base")), L("; Study 1b 16-step set"),
              integer(R(S, "s1b", "descriptive", "arms", f"{OFF_TAG}@16", "1x16", "n_base")), L("; samples per puzzle: Study 1"),
              integer(tries_s1[0]), L("; Study 1b"), integer(tries_1b[0])],
        "interval": [L("95% over puzzles: Study 1b"), text_of(R(S, "s1b", "descriptive", "arms", f"{OFF_TAG}@6", "1x6", "interval")),
                     L("; Study 1 cluster bootstrap" + ("; exact (Clopper–Pearson, post hoc) where marked" if any_exact else ""))],
        "price": [L("no costs in this table")],
    }
    # a new group where the study or the puzzle set changes (Study 1; Study 1b's 6-step set; Study 1b's 16-step set: three puzzle sets)
    groups = [i for i in range(1, len(rows)) if [c.printed for c in rows[i][:2]] != [c.printed for c in rows[i - 1][:2]]]
    # twelve columns, two of them long text: footnotesize (8 pt) keeps the float, with its notes, clear of its sideways page (at \\small
    # it was 6.3 in of 6.5, the header six lines tall)
    return Table([L(c) for c in cols], rows, notes, caption, layout="landscape", font="footnotesize", groups=groups)


# ================================================================ TAB-31

REP = ("result", "repeat_share")
BINS = ("result", "bins_16")
STAMPED_REPEAT = ("study1:haiku-med@6", ("haiku_repeat_share",))     # the fa6b row the locked Study 1 file stamps as haiku_repeat_share
BIN_STATUS = {"read": "read", "shown, not read": "shown, not read", "empty": "empty"}
PANEL_NAME = "Haiku-max vote at 16 steps by Haiku-medium difficulty bin"


def _settings(S: Store) -> List[Tuple[str, str, int, str, str]]:
    """fa6b's repeat-share settings as (key, study, steps, arm or tag, display name), by effort, then study, then length."""
    out = []
    for key in S.keys("fa6b", "result.repeat_share"):
        study, rest = key.split(":")
        arm, n = rest.rsplit("@", 1)
        name, _, effort = (STUDY1_ARMS if study == "study1" else STUDY1B_TAGS)[arm]
        out.append((EFFORT_ORDER.index(effort), STUDY_ORDER.index(study), int(n), key, study, arm, name))
    return [(key, study, n, arm, name) for _, _, n, key, study, arm, name in sorted(out)]


def _tries_ref(S: Store, study: str, n: int, arm: str, sh: str) -> Ref:
    """Tries per puzzle: Study 1b's tries_per_item; Study 1's stamped samples drawn per puzzle (Haiku-medium: k.json's
    k_from_rows.opus.<shape>.samples_drawn, checked against item 24's tries over base puzzles and item 8b's vote curve; Haiku-max: item
    10's own-k samples_drawn, see s1_tries_per_puzzle)."""
    if study == "study1b":
        return R(S, "s1b", "descriptive", "arms", f"{arm}@{n}", "tries_per_item")
    if arm == "haiku-med":
        r = R(S, "main_k", "k_from_rows", "opus", sh, "samples_drawn")
        row = G(S, "main", *ITEM24, f"{arm} {sh}")
        check(row["format_compliance"]["tries"] == r.value * row["base_puzzles"], f"{arm} {sh}: tries = samples drawn x base puzzles")
        curve = G(S, "main", "reporting", "group_b", "item_8b", "vote_curve", sh)
        check(curve["arm"] == arm and curve["k_max"] == r.value, f"{arm} {sh}: samples drawn = item 8b's vote curve k_max")
        return r
    if arm == "haiku-max":
        return s1_tries_per_puzzle(S, arm, sh)
    raise KeyError(f"no tries-per-puzzle key for Study 1 arm {arm}")


def _share_cell(r: Ref) -> Cell:
    """A repeat share in %; a null share (no pair of wrong tries) is printed 'no pairs'."""
    return text_of(r, {None: "no pairs"}) if r.value is None else P(r, prop=True)


def _check_stamped_repeat(S: Store) -> None:
    key, base = STAMPED_REPEAT
    stamped, recount = G(S, "main", *base), G(S, "fa6b", *REP, key)
    check(set(stamped) == set(recount), "Study 1 Haiku-medium repeat-share shapes")
    for sh, block in stamped.items():
        for f in ("agree", "pairs", "puzzles", "share"):
            if f in block:
                check(block[f] == recount[sh][f], f"Study 1 Haiku-medium repeat share {sh}.{f}")


CURVE = ("descriptive", "vote_curve_n16")


def curve_point(S: Store, kval: Any) -> int:
    """Index of the k-try point in Study 1b's 16-step Haiku-max vote curve (checked against the point's own k)."""
    for i, pt in enumerate(G(S, "s1b", *CURVE, "points")):
        if pt["k"] == kval:
            return i
    raise KeyError(f"no vote-curve point at k = {kval}")


# fa6b's thirds, lowest wrong-try agreement first. fa6b cuts them as rest[j*L//3:(j+1)*L//3] over (share, puzzle id): the higher thirds
# take any extra puzzles and ties are broken by puzzle id. Item 20 (report_votes._thirds) puts puzzle i in third floor(3i/L) and a
# whole tie group in the lower third, so these are a post hoc variant of item 20's split; the note says so.
THIRDS = (("t1", "lowest"), ("t2", "middle"), ("t3", "highest"))
FORMAT_HX = (*FORMAT_REPORT, "hx")


def _cells_of(S: Store, blk: Sequence[Any], vk: str, vall: str) -> List[Cell]:
    """Haiku-max single try, vote at k and vote of all tries, in %, from an fa6b block holding the three means (points)."""
    return [P(R(S, "fa6b", *blk, f), prop=False) for f in ("single_try_mean", vk, vall)]


def _bins_panel(S: Store) -> Table:
    k = R(S, "s1b_k", "k")
    hx_tries = R(S, "s1b", "descriptive", "arms", "hx@16", "tries_per_item")
    hm_tries = R(S, "s1b", "descriptive", "arms", "hm@16", "tries_per_item")
    vk, vall = f"vote_at_{k.value}_mean", f"vote_at_{hx_tries.value}_mean"
    check(G(S, "s1b", *CURVE, "k_from_k_json") == k.value, "the vote curve's k and k.json's k")
    ik, iall = curve_point(S, k.value), curve_point(S, hx_tries.value)
    check(G(S, "s1b", *CURVE, "points", ik, "equal_money_k") is True, "the k-try point is the curve's equal-money point")
    rule = R(S, "s1b", *CURVE, "rule")
    check("ties at 1/m" in rule.value and "a missing or unreadable try votes for nothing" in rule.value,
          "the locked vote curve's tie and missing-try rules")
    # format compliance sits beside the accuracy columns (style sheet, D-122)
    cols = ["Shape", "Haiku-medium accuracy bin (%)", "Wrong-sample agreement third", "Puzzles", "Status",
            "Haiku-max single sample (%)", "Vote at k (%)", "Vote of all samples drawn (%)", "Haiku-max format compliance (%)",
            "Puzzles with too few wrong samples"]
    rows, flags = [], []
    shapes = chain_first([s for s in S.keys("fa6b", join_key(*BINS))])
    for sh in shapes:
        occ_bins = S.keys("fa6a", join_key("result", sh, "bins"))
        fab = (*BINS, sh, "bins")
        check(occ_bins == S.keys("fa6b", join_key(*fab)), f"{sh}: bin labels in fa6a and fa6b")
        check(G(S, "fa6b", *BINS, sh, "uninformative") == G(S, "fa6a", "result", sh, "uninformative"), f"{sh}: uninformative flag")
        not_read = []
        for b in occ_bins:
            check(G(S, "fa6a", "result", sh, "bins", b) == G(S, "fa6b", *fab, b, "puzzles"), f"{sh} {b}: occupancy")
            status = R(S, "fa6b", *fab, b, "status")
            if status.value == "shown, not read":
                not_read.append(b)
            lead = [L(shape(sh)), entry_name(S, "fa6b", *fab, b)]
            if status.value == "empty":
                rows.append(lead + [DASH, integer(R(S, "fa6a", "result", sh, "bins", b)), text_of(status, BIN_STATUS)] + [DASH] * 5)
                continue
            a = (*fab, b, "all")
            check(G(S, "fa6b", *a, "puzzles") == G(S, "fa6b", *fab, b, "puzzles"), f"{sh} {b}: puzzles in 'all'")
            rows.append(lead + [L("whole bin"), integer(R(S, "fa6a", "result", sh, "bins", b)), text_of(status, BIN_STATUS),
                                *_cells_of(S, a, vk, vall), DASH, integer(R(S, "fa6b", *fab, b, "too_few_wrong_tries"))])
            # the within-bin split by Haiku-max's own wrong-try agreement, a post hoc variant of item 20's (see THIRDS; sub-rows; a
            # bin whose puzzles all have too few wrong tries has no thirds and no sub-rows)
            thirds = G(S, "fa6b", *fab, b, "thirds")
            check(set(thirds) <= {t for t, _ in THIRDS}, f"{sh} {b}: third names")
            check(sum(v["puzzles"] for v in thirds.values()) + G(S, "fa6b", *fab, b, "too_few_wrong_tries") == G(S, "fa6b", *fab, b, "puzzles"),
                  f"{sh} {b}: thirds plus too few wrong tries = the bin's puzzles")
            if not thirds:
                continue
            for t, word in THIRDS:
                if t not in thirds:
                    rows.append(lead + [L(word), DASH, DASH, DASH, DASH, DASH, DASH, DASH])
                    continue
                th = (*fab, b, "thirds", t)
                rows.append(lead + [L(word), integer(R(S, "fa6b", *th, "puzzles")), DASH, *_cells_of(S, th, vk, vall), DASH, DASH])
        check(not_read == list(G(S, "fa6a", "result", sh, "bins_not_read")), f"{sh}: bins shown but not read")
        # the unbinned row: Study 1b's locked single-try accuracy and vote curve, which the post hoc recount must reproduce
        u = (*BINS, sh, "unbinned")
        locked = [R(S, "s1b", "descriptive", "arms", "hx@16", sh, "mean"), R(S, "s1b", *CURVE, "points", ik, sh, "mean"),
                  R(S, "s1b", *CURVE, "points", iall, sh, "mean")]
        for r, f in zip(locked, ("single_try_mean", vk, vall)):
            check(abs(float(r.value) - float(G(S, "fa6b", *u, f))) < 1e-9, f"{sh}: unbinned {f} against the locked curve")
        check(abs(float(locked[1].value) - float(G(S, "s1b", "per_form", "B2", sh, "v", "mean"))) < 1e-9,
              f"{sh}: the curve's k-try point is Test B2's per-shape challenger accuracy")
        check(G(S, "s1b", *FORMAT_HX, sh, "tries") == hx_tries.value * G(S, "fa6a", "result", sh, "puzzles"),
              f"{sh}: Haiku-max format report covers every 16-step try")
        rows.append([L(shape(sh)), L("all puzzles (unbinned)"), DASH, integer(R(S, "fa6a", "result", sh, "puzzles")), DASH,
                     *[P(r, prop=False) for r in locked], P(R(S, "s1b", *FORMAT_HX, sh, "format_compliance"), prop=True), DASH])
        # the uninformative flag, with the largest bin's count of puzzles and fa6a's stamped largest_bin_share (in %, at two decimals
        # as the cells print them, so 0.6125 prints 61.25), checked to be that count over the shape's puzzles
        occ = G(S, "fa6a", "result", sh, "bins")
        big = max(occ, key=lambda x: (occ[x], x))
        check(sum(1 for v in occ.values() if v == occ[big]) == 1, f"{sh}: one largest bin")
        check(abs(occ[big] / G(S, "fa6a", "result", sh, "puzzles") - G(S, "fa6a", "result", sh, "largest_bin_share")) < 1e-12,
              f"{sh}: the largest bin's count over the puzzles is the stamped largest_bin_share")
        unin = R(S, "fa6b", *BINS, sh, "uninformative")
        word = "Chains" if shape_word(sh) == "chain" else "Pieces"
        flags.append(note(L(f"{word} ({shape(sh)}): uninformative:"), joined(text_of(unin, YES_NO), L(";"), sep=""),
                          L("the largest bin"),
                          entry_name(S, "fa6a", "result", sh, "bins", big), L("holds"), integer(R(S, "fa6a", "result", sh, "bins", big)),
                          L("of its"), integer(R(S, "fa6a", "result", sh, "puzzles")),
                          joined(L("puzzles ("), P(R(S, "fa6a", "result", sh, "largest_bin_share"), prop=True), L("%);"), sep=""),
                          L("only the unbinned curve is read." if unin.value else "the bins marked read are read.")))
    rule_e20 = R(S, "fa6a", "result", "rule")
    notes = [
        note("Bins: each puzzle's Haiku-medium single-sample accuracy at 16 steps over its", integer(hm_tries), "samples, in 10-point bins "
             "with the top bin closed. The bins were fixed, and their occupancy written, before any Haiku-max value was binned; with so "
             "few samples some bins cannot hold a puzzle and are empty."),
        note("A bin with fewer than", number_in_text(rule_e20, r"fewer than (\d+) puzzles"), "puzzles is shown but not read; a shape whose "
             "largest bin holds more than", joined(number_in_text(rule_e20, r"more than (\d+)% of its puzzles"), L("%"), sep=""),
             "of its puzzles is uninformative, and then only the unbinned curve is read (rule fixed before computing)."),
        *flags,
        note("Haiku-max single sample: the mean over the bin's puzzles of each puzzle's single-sample accuracy. Vote at k: Haiku-max's "
             "majority vote of k samples as Test B2 scores it, estimated from the samples drawn; k =", integer(k), "(Test B2's k). Vote of "
             "all samples drawn: the vote of all", integer(hx_tries), "Haiku-max samples per puzzle. A missing sample, or a sample with "
             "no answer or whose official format is not ok, votes for nothing, and a tie among several leading answers scores an equal "
             "share of one right answer when the right answer is among them (the locked vote curve's rule). Means over puzzles, in %; no "
             "intervals."),
        note("Puzzles with too few wrong samples: the puzzles in the bin with fewer than two wrong Haiku-max samples, so no agreement "
             "between wrong answers can be measured."),
        note("Wrong-sample agreement thirds (a post hoc variant of the within-bin split in Study 1's pre-specified vote lookup chart): "
             "within a bin, the puzzles with at least two wrong Haiku-max samples are ordered by how often their wrong samples give the "
             "same answer (agreeing pairs over pairs; ties broken by puzzle) and cut into a lowest, middle and highest third so that "
             "the higher thirds take any extra puzzles. Study 1's chart gives the extra puzzles to the lower thirds and sends a whole "
             "group of tied puzzles to the lower third, so these are not its thirds, and a lower third can be empty here "
             "(dashes). A bin whose puzzles all have too few wrong samples has no thirds. The rule above on which bins are read applies "
             "to bins, not to thirds: each third rests on the few puzzles in its puzzles column."),
        note("Haiku-max format compliance: the locked share of the 16-step Haiku-max samples whose official format status is ok, for all "
             "puzzles of the shape (pre-specified descriptive); it is not stamped by bin."),
        note("The unbinned rows are Study 1b's locked single-sample accuracy and vote curve (pre-specified descriptive); the post hoc "
             "recount agrees with them (checked when the table is built). Their vote at k is Test B2's challenger at that shape: Test "
             "B2 is confirmatory and pools the two shapes, so this per-shape value is a descriptive breakdown, not a test. The binned "
             "rows and the thirds are post hoc exploratory, with no causal claim."),
    ]
    caption = {
        "tier": [L("post hoc exploratory (no causal claim), bins fixed before computing; the unbinned rows pre-specified descriptive, "
                   "their vote at k ="), integer(k), L("being Test B2's challenger at that shape (Test B2 is confirmatory and pools the "
                                                       "shapes; a per-shape value is not a test)")],
        "study": [L("Study 1b, 16 steps")],
        "set": [L("Study 1b's 16-step set")],
        "n": [L("puzzles per shape:"), integer(R(S, "fa6a", "result", shapes[0], "puzzles")), L("; Haiku-max samples per puzzle:"),
              integer(hx_tries), L("; Haiku-medium samples per puzzle (for the bins):"), integer(hm_tries)],
        "interval": [L("none: means over puzzles")],
        "price": [L("no costs in this table")],
    }
    # a new group at each bin (its whole-bin row, then its thirds) and at each shape's unbinned row
    groups = [i for i in range(1, len(rows)) if rows[i][:2] != rows[i - 1][:2]]
    # footnotesize, as the table the panel belongs to is: ten columns whose longest words no longer break (proof 2) overran the text width
    return Table([L(c) for c in cols], rows, notes, caption, layout="longtable", font="footnotesize", groups=groups)


def _fa6b_scope(S: Store) -> Cell:
    """The note's list of the settings free analysis 6 was defined to cover, checked against its stamped definition: Haiku-max at
    Study 1b's 6, 12 and 16 steps and on Study 1's tries, plus Haiku-high and Haiku-xhigh. Returns Study 1's Haiku-max tries per
    puzzle (stamped; the number the definition writes must be it), and checks that the rows outside that scope are exactly the Study 1b
    Haiku-medium rows and the Study 1 Haiku-medium row (which the locked Study 1 file stamps)."""
    defn = R(S, "fa6b", "definition", "analysis")
    for words in ("for Haiku-max at 6, 12 and 16 steps", "plus Haiku-high and Haiku-xhigh"):
        check(words in defn.value, f"fa6b's definition says {words!r}")
    tries = _tries_ref(S, "study1", 6, "haiku-max", "1x6")
    check(number_in_text(defn, r"on Study 1's (\d+) tries").printed == str(tries.value),
          "fa6b's definition names Study 1's Haiku-max tries per puzzle as stamped")
    covered = {("study1", "haiku-max"), *{("study1b", t) for t in ("hx", "hh", "hxh")}}
    outside = sorted({(study, arm) for _, study, _, arm, _ in _settings(S) if (study, arm) not in covered})
    check(outside == [("study1", "haiku-med"), ("study1b", "hm")], f"the rows outside fa6b's defined scope are {outside}")
    return integer(tries)


@output("TAB-31")
@main_text
def tab_31(S: Store) -> Table:
    _check_stamped_repeat(S)
    s1_hx_tries = _fa6b_scope(S)
    nulls = set(G(S, "fa6b", "undefined_as_null"))
    cols = ["Setting", "Study", "Steps", "Samples per puzzle", "Shape", "Puzzles kept", "Pairs", "Agreeing pairs", "Repeat share (%)",
            "Label"]
    rows = []
    for key, study, n, arm, name in _settings(S):
        stamped = key == STAMPED_REPEAT[0]
        src, base = ("main", STAMPED_REPEAT[1]) if stamped else ("fa6b", (*REP, key))
        tier = L("pre-specified descriptive" if stamped else "post hoc exploratory")
        steps = R(S, "main_k", "n") if study == "study1" else R(S, "s1b", "descriptive", "arms", f"{arm}@{n}", "N")
        check(steps.value == n, f"{key}: steps")
        shapes = chain_first([s for s in S.keys(src, join_key(*base)) if s != "both_shapes"])
        tries = [_tries_ref(S, study, n, arm, sh) for sh in shapes]
        check(len({t.value for t in tries}) == 1, f"{key}: tries per puzzle by shape")
        for sh, tr in zip(shapes + ["both_shapes"], tries + [tries[0]]):
            blk = (*base, sh)
            share = R(S, src, *blk, "share")
            if share.value is None:
                check(G(S, src, *blk, "pairs") == 0, f"{key} {sh}: a null share with pairs")
                check(src != "fa6b" or join_key(*REP[1:], key, sh, "share") in nulls, f"{key} {sh}: null share not declared")
            if sh == "both_shapes":
                # the dash in Puzzles kept: the stamped both-shapes block has no puzzle count, and its pairs and agreeing pairs are the
                # two shapes' added together (the note says so); its share is agreeing pairs over pairs
                check(not S.has(src, join_key(*blk, "puzzles")), f"{key}: a both-shapes block with a puzzle count: the dash would be wrong")
                for f in ("pairs", "agree"):
                    check(sum(G(S, src, *base, s_, f) for s_ in shapes) == G(S, src, *blk, f), f"{key}: both shapes' {f} = the shapes' sum")
                check(share.value is None or abs(float(share.value) - G(S, src, *blk, "agree") / G(S, src, *blk, "pairs")) < 1e-9,
                      f"{key}: both shapes' share = agreeing pairs over pairs")
            puzzles = integer(R(S, src, *blk, "puzzles")) if sh != "both_shapes" else DASH
            rows.append([L(name), L(STUDY_NAMES[study]), integer(steps), integer(tr), L(shape(sh) if sh != "both_shapes" else "both shapes"),
                         puzzles, integer(R(S, src, *blk, "pairs")), integer(R(S, src, *blk, "agree")), _share_cell(share), tier])
    notes = [
        note("Pairs: unordered pairs of wrong samples on the same puzzle and shape. Agreeing pairs give the identical official answer (a "
             "sample with no answer or whose official format is not ok never agrees). Repeat share: agreeing pairs divided by pairs, "
             "pooled over the puzzles kept (the puzzles with at least two wrong samples)."),
        note("No pairs: no puzzle had two wrong samples, so the share is undefined."),
        note("Both shapes: the chains' and the pieces' pairs and agreeing pairs added together, and the share is agreeing pairs over "
             "pairs; no count of puzzles is stamped for these rows, so Puzzles kept shows a dash."),
        note("The Study 1 Haiku-medium rows are Study 1's locked, pre-specified descriptive values; the post hoc recount gives the same "
             "counts (checked when the table is built). Every other row is post hoc."),
        note("The Study 1b Haiku-medium rows go beyond the settings this post hoc analysis was defined to cover (Haiku-max, Haiku-high "
             "and Haiku-xhigh in Study 1b, and Haiku-max on Study 1's", s1_hx_tries, "samples); the same post hoc recount computed them, "
             "and they are shown as the same-set medium-effort baseline for the higher efforts."),
        note("Rows differ in study, puzzle set, length and samples per puzzle; a share from few pairs or few puzzles is fragile. Setting "
             "rows side by side, above all across the two studies, is our reading, not a test."),
        note("Exploratory, no causal claim: the table does not show that repeated wrong answers cause or prevent anything."),
    ]
    caption = {
        "tier": [L("post hoc exploratory (no causal claim); the Study 1 Haiku-medium rows pre-specified descriptive")],
        "study": [L("Study 1 (main run, 6 steps) and Study 1b (6-step, 12-step and 16-step sets), each row within one study")],
        "set": [L("Study 1: the main-run puzzle set; Study 1b: its 6-step, 12-step and 16-step sets (other puzzles)")],
        "n": [L("puzzles per shape: Study 1"), integer(R(S, "main", *ITEM24, "haiku-med 1x6", "base_puzzles")),
              L("; Study 1b 6-step set"), integer(R(S, "s1b", "descriptive", "arms", "hx@6", "pooled", "n_base")),
              L("; 12-step set"), integer(R(S, "s1b", "descriptive", "arms", "hx@12", "pooled", "n_base")),
              L("; 16-step set"), integer(R(S, "s1b", "descriptive", "arms", "hx@16", "pooled", "n_base")),
              L("; puzzles kept and pairs per row")],
        "interval": [L("none: counts and shares only")],
        "price": [L("no costs in this table")],
    }
    if not label_ok(PANEL_NAME):
        raise ValueError(f"panel name {PANEL_NAME!r} holds a typed number")
    # each setting's rows (its shapes, then both shapes) are one group
    t = Table([L(c) for c in cols], rows, notes, caption, layout="landscape", font="footnotesize",
              groups=[i for i in range(1, len(rows)) if rows[i][:3] != rows[i - 1][:3]])
    t.panels.append((PANEL_NAME, _bins_panel(S)))
    return t
