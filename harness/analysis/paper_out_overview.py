"""TAB-01, the eight tests at a glance (Introduction): Study 1's Tests 1-5 and Study 1b's B1-B3, one row each, read from both studies'
pinned files. Holm runs within each study only; the two studies are never pooled. Study 1b's secondary 10-point margin is shown
beside the primary, quoted only as the secondary (style sheet).

The typed tier and footnote wording states which tests Holm declared; `_check_wording` refuses the build if the stamped flags or
readings ever disagree with that wording. This is a main-text table: no run ids, set ids, item numbers or file names in its text, and
(`_check_plain_words`) no decision ids or internal record names anywhere it prints.

Tiers (Edith's rulings on PR 27, Q14 and Q15): each row's Tier cell names the tier of each thing the row prints. The test (d and its
pre-registered reading) is confirmatory; the error-rate ratio is pre-specified descriptive, reported beside the test, never under
"confirmatory"; k and the spend or cost ratio are not tested (k is the vote's size, set by the study's pre-registered equal-money
rule; Test 4's cost ratio is post hoc arithmetic on pre-specified means; Test 5's carries its stamped label). The notes and the
caption's tier fact say the same. "Pre-registered" is checked against each study's locked text: Study 1's spec as locked in
prereg-lock-3 (pinned here) and the section of Study 1b's spec that B2's k file names.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import floor
from typing import Iterator, List, Optional, Tuple

from . import paper_out_core as core
from .paper_out_core import (FLOOR_NOTE, Cell, Ref, Source, Store, Table, YES_NO, ci_refs, derive, integer, interval, join_key, joined, label, num,
                             pvalue_bound,
                             num_d, output, pct, pts, pvalue, register_source, text_of, usd)
from .paper_out_names import shape_word, STUDY1_ARMS, STUDY1_TESTS, main_text, shape

# The Study 1 spec as locked: pinned at the commit of the prereg-lock-3 tag (086fbfd, cut before any main-run call), whose bytes are
# those of f773d83 (the spec's last change, Amendment 1) and the SHA-256 the lock manifest's hash block lists for it. The k note and the
# Tier cells say Tests 1-3's k is set by Study 1's pre-registered equal-money rule; `_check_wording` refuses the build unless this
# locked text names that rule, lists Test 3's Sonnet-matched vote among the five tests, and locks the k script's rule (the floor of
# the cost ratio per shape and effort, capped at a fixed number and at the samples drawn). Named for this module, so that its pin
# does not depend on another module's.
SPEC1_LOCK = register_source(Source(
    "overview_s1_spec_lock3", "studies/1-real-price/spec.md", "086fbfd",
    "0ab437934a8df843db20ff9eb4aa57dd6e8228605f38df4b77e138d942e6c169", kind="text",
    what="The Study 1 spec as locked in prereg-lock-3, before the main run: the equal-money rule and the k script's lock line"))
EQ_RULE_LINE = r"^- \*\*D-33\*\* \(.*\), the equal-money rule \(the vote size k\)\."
T3_ROW_LINE = r"^\| 3 \| Haiku-medium vote at k \(Sonnet-matched\) \| Sonnet-medium \|"
K_SCRIPT_LINE = (r"the \*\*k script\*\* \(`harness/analysis/kscript\.py`.*\): floor of the cost ratio per shape and effort, "
                 r"cap at (\d+) and at the samples drawn")

DASH = label("—")
S1 = "confirmatory.views.as_deployed"
S1B = "confirmatory.primary_margin_5.views.as_deployed"
S1B_SEC = "confirmatory.secondary_margin_10.views.as_deployed"
FIVE = "reporting.five_point_view"
ORIG = "secondary.original_repeat_rule.tests"
SPEND = "reporting.group_b.item_8b.realised_spend.tests"
ITEM24 = "reporting.group_b.item_24.table"
ITEM9H = "reporting.group_b.item_9h"
B_TESTS = ("B1", "B2", "B3")
B_SHORT = {"B1": "Haiku-max sample vs Opus-medium", "B2": "Haiku-max vote vs Opus-medium", "B3": "Haiku-max sample vs Opus-medium"}
B_WHAT = {"B1": "One Haiku-max sample vs one Opus-medium answer", "B2": "Haiku-max vote vs one Opus-medium answer",
          "B3": "One Haiku-max sample vs one Opus-medium answer"}
# Three decimals for the point spend and cost ratios (the ruled Test 3 wording prints 0.970). Test 5's exploratory cost ratio carries
# its stamped interval and is printed as TAB-05 and the claims ledger print it (2.48 [2.36, 2.59]): one comparison, one printing.
RATIO_DP = 3
T5_RATIO_DP = 2
DP_WORDS = {1: "one", 2: "two", 3: "three", 4: "four"}     # a note's decimals in words, from the constants that print them
PAPER_RATIO_DP = 1        # Table 2's error-rate ratios and their intervals, as the cleared prose prints them (Edith §2.1, PR #33 review)
COST_RATIO_DP = 2         # the paper's cost ratios (Edith's §2.1): Test 4, Test 5, B1 and B3 in Table 2; spend shares keep RATIO_DP

# Labels, chosen by the stamped `declared` flag (the cell records the flag as its source). Edith's D-161 wordings (rulings A, C, D):
# "shown no worse (Holm-adjusted across the study's tests)" and the decision rule's reading of the unadjusted interval. A rule is
# applied and a reading is what it gives, so the label says "read by the pre-registered decision rule" (as the caption fact and
# note 1 do). Ruling A has two senses of "not Holm-declared": "not Holm-adjusted" qualifies the unadjusted interval's reading (all of
# Study 1's tests that Holm did not pass, and Study 1b's tests read at the primary margin), and "not shown no worse (Holm-adjusted)"
# records that Holm's correction did not pass B1 and B3 at the primary 5-point margin (sense ii, named for exactly this case).
S1_TIER = {True: "confirmatory, shown no worse (Holm-adjusted across Study 1's tests)",
           False: "confirmatory, read by the pre-registered decision rule on the unadjusted interval (not Holm-adjusted)"}
S1B_TIER = {True: "confirmatory, shown no worse (Holm-adjusted across Study 1b's tests) at the primary 5-point margin",
            False: "confirmatory, read by the pre-registered decision rule on the unadjusted interval (not Holm-adjusted); not shown no "
                   "worse (Holm-adjusted) at the primary 5-point margin"}
# The other columns' tiers (Q14, Q15): typed once, printed in the Tier cells, the notes and the caption alike.
ER_TIER = "pre-specified descriptive, reported beside the test"
K_TIER = "set by the pre-registered rule for a cost-matched vote, not tested"
RATIO_TIER = "pre-specified descriptive, not tested"
T4_RATIO_TIER = "post hoc arithmetic on pre-specified means, not tested"

# PO-1 and the notes check (N-11, Q24, Q26): printed text names no decision id and no internal record, voice or time-zone wording.
# The error-rate ratio's unbounded upper end, in one wording for Tables 2, 7 and 9 (TAB-01.main, TAB-02.main, TAB-10.main; Edith,
# proof 4 §9.1: Table 9's "too many bootstrap draws" is the accurate condition). The comparator differs between tests, so it is named
# generically, and the word "unbounded" prints only as an error-rate ratio's upper end (each table checks it), so the note defines the
# word itself and keeps the two notes within two lines. Each table prints it only if an error-rate ratio there prints "unbounded".
UNBOUNDED_NOTE = "Unbounded: the comparator made no error in too many bootstrap draws."

BARRED = re.compile(r"\bD-\d|LOG\.md|findings register|decision register|spend log|\bthe user\b|\bthe authors\b|India Standard Time"
                    r"|UTC calendar|helper session|free trial read|degeneracy rule|\bthe ledger\b|\bk_O\b|TI_house", re.IGNORECASE)


def _s1_reading(cmp_name: str):
    """Study 1's stamped readings in the style sheet's words (as TAB-11 prints them): a non-inferior reading is 'shown no worse than X
    by more than the margin' (D-161 B: a passed reading keeps 'shown'; Edith, proof 4: as Table 6's cell); an inconclusive one 'could not
    show'. (paper_out_study1 imports this; TAB-01 prints `RULE_READING` instead.)"""
    return {"non-inferior": f"shown no worse than {cmp_name} by more than the margin",
            "worse by more than the margin": "worse by more than the margin",
            "inconclusive": "inconclusive (could not show)"}


# TAB-01's Reading column: the stamped readings as the pre-registered decision rule's three outcomes (Edith's ruling C). A
# "non-inferior" reading is a test shown no worse (Holm-adjusted); `_check_wording` checks that for every test that has one.
RULE_READING = {"non-inferior": "shown no worse by > margin (Holm-adjusted)",
                "worse by more than the margin": "worse by > margin",
                "inconclusive": "inconclusive"}


# Study 1b's stamped template readings, as the same three outcomes ("holds" is a test shown no worse in all three views).
B_READING = {"holds (no worse in all three views)": "shown no worse by > margin (Holm-adjusted), in all three views",
             "inconclusive (could not show)": "inconclusive"}


def _check_wording(S: Store) -> None:
    """The typed tier, caption and footnote wording names Test 5 and B2 as the only Holm-declared tests at the primary margins, all of
    B1-B3 as declared at the secondary 10-point margin, and Test 3 (not Test 5) as changing its reading under the original marking
    rule; the notes also state the margins (Study 1's 10-point one, its secondary 5-point view, Study 1b's 5 and 10 points) and how
    k was set (the floor of the cost ratio, only Test 1 capped, at the tries drawn; Study 1's k file at Batch prices, exactly half of
    list, with its stamped ratio the quotient of those two costs; Study 1's rule as locked in its spec; B2's k by Study 1b's spec rule
    on list costs) and that Test 4's means are the pre-specified ones. Refuse the build if the stamped values or the locked spec say
    otherwise."""
    s1 = {t for t in STUDY1_TESTS if S.get("main", f"{S1}.tests.{t}.declared")}
    s1b = {b for b in B_TESTS if S.get("s1b", f"{S1B}.tests.{b}.declared")}
    sec = {b for b in B_TESTS if S.get("s1b", f"{S1B_SEC}.tests.{b}.declared")}
    if s1 != {"t5"} or s1b != {"B2"} or sec != set(B_TESTS):
        raise ValueError(f"TAB-01 wording assumes Holm declared t5; B2 (5 points); B1-B3 (10 points); stamped: {s1}, {s1b}, {sec}")
    for b in B_TESTS:
        if S.get("s1b", f"{S1B_SEC}.tests.{b}.p") > S.get("s1b", f"{S1B_SEC}.holm_thresholds.{b}"):
            raise ValueError(f"TAB-01: {b}'s secondary p is not below its Holm threshold")
    if S.get("main", f"{ORIG}.t3.reading") == S.get("main", f"{S1}.tests.t3.reading"):
        raise ValueError("TAB-01: Test 3's reading no longer changes under the original marking rule")
    if S.get("main", f"{ORIG}.t5.reading") != S.get("main", f"{S1}.tests.t5.reading"):
        raise ValueError("TAB-01: Test 5's reading changes under the original marking rule")
    # a "non-inferior" reading prints as "shown no worse (Holm-adjusted)": only a test the Holm flag declared may have one
    for t in STUDY1_TESTS:
        if (S.get("main", f"{S1}.tests.{t}.reading") == "non-inferior") != bool(S.get("main", f"{S1}.tests.{t}.declared")):
            raise ValueError(f"TAB-01: {t}'s reading and its Holm flag disagree: 'shown no worse (Holm-adjusted)' would be wrong")
    for b in B_TESTS:
        if (S.get("s1b", f"{S1B}.tests.{b}.reading") == "non-inferior") != bool(S.get("s1b", f"{S1B}.tests.{b}.declared")):
            raise ValueError(f"TAB-01: {b}'s reading and its Holm flag disagree: 'shown no worse (Holm-adjusted)' would be wrong")
    if len({S.get("main", f"{S1}.tests.{t}.n") for t in STUDY1_TESTS}) != 1:
        raise ValueError("TAB-01: the caption gives one puzzle count for all of Study 1's tests; the stamped counts differ")
    if S.get("s1b", f"{S1B}.tests.B1.n") != S.get("s1b", f"{S1B}.tests.B2.n"):
        raise ValueError("TAB-01: the caption gives one puzzle count for B1 and B2; the stamped counts differ")
    if S.get("s1b_k", "samples_drawn") != S.get("s1b", "constants.designed_tries.hx") or S.get("s1b_k", "k") >= S.get(
            "s1b_k", "samples_drawn"):
        raise ValueError("TAB-01: B2's note says its k-try vote is computed from the designed Haiku-max tries (k below them)")
    for t in ("t1", "t2", "t3"):
        k_json = S.get("main_k", _k_key(t, "k"))
        if S.get("main", join_key(*SPEND.split("."), t, "by_row", "k+0", "k")) != k_json:
            raise ValueError(f"TAB-01: {t}'s list-priced spend row is not at k.json's k")
        # the k note: k is the most tries whose mean list cost fits within the comparator's, capped at the tries drawn
        if k_json != min(floor(Fraction(S.get("main_k", _k_key(t, "ratio")))), S.get("main_k", _k_key(t, "cap"))):
            raise ValueError(f"TAB-01: the k note says k is the floor of the cost ratio, capped; {t}'s stamped k is not")
    if {t for t in ("t1", "t2", "t3") if S.get("main_k", _k_key(t, "capped"))} != {"t1"}:
        raise ValueError("TAB-01: the k note says only Test 1's k is capped")
    if S.get("main_k", _k_key("t1", "cap")) != S.get("main_k", _k_key("t1", "samples_drawn")):
        raise ValueError("TAB-01: the k note says Test 1's cap is the number of tries drawn per puzzle and shape")
    # note 1 and the caption name Study 1's 10-point margin (its only confirmatory one) and a secondary 5-point view; Study 1b's
    # primary 5-point and secondary 10-point margins
    if (S.get("main", f"{S1}.margin") != -10 or S.get("main", f"{FIVE}.margin") != -5
            or not S.get("main", f"{FIVE}.label").startswith("secondary")):
        raise ValueError("TAB-01: note 1 assumes Study 1's 10-point confirmatory margin and a secondary 5-point view")
    if S.get("s1b", f"{S1B}.margin") != -5 or S.get("s1b", f"{S1B_SEC}.margin") != -10:
        raise ValueError("TAB-01: the wording assumes Study 1b's primary 5-point and secondary 10-point margins")
    # the k note (Edith's N-10): Study 1's k file prices each call at the Batch rate (the logged cost_usd, as item 9a's label says),
    # exactly half the list prices item 8b's spend uses, so its k is the k at list prices
    if ("cost_usd" not in S.get("main_k", "columns_read")
            or "Batch = the logged cost_usd" not in S.get("main", "reporting.group_b.item_9a.label")
            or not S.get("main", "reporting.group_b.item_8b.realised_spend.priced").startswith("list")):
        raise ValueError("TAB-01: the k note says k's file uses Batch prices and the spend ratio list prices; the stamped files differ")
    for t in ("t1", "t2", "t3"):
        sp = join_key(*SPEND.split("."), t)
        cmp_cost = Fraction(S.get("main_k", _k_key(t, "comparator_cost_per_puzzle")))
        hk_cost = Fraction(S.get("main_k", _k_key(t, "haiku_cost_per_sample")))
        if (cmp_cost * 2 != Fraction(S.get("main", f"{sp}.comparator_list_cost_per_puzzle"))
                or hk_cost * 2 != Fraction(S.get("main", f"{sp}.haiku_list_cost_per_sample"))):
            raise ValueError(f"TAB-01: the k note says k's file prices {t}'s calls at exactly half the list price; it does not")
        # ... and that the stamped ratio k is floored from is the quotient of those two Batch costs, so it equals the list-price
        # quotient and "k is the same at list prices" holds
        if Fraction(S.get("main_k", _k_key(t, "ratio"))) != cmp_cost / hk_cost:
            raise ValueError(f"TAB-01: the k note says {t}'s k comes from the ratio of its two costs; k.json's stamped ratio is not "
                             "their quotient")
    # k's tier ("set by each study's pre-registered equal-money rule"), Study 1's half: the locked spec names the equal-money rule,
    # pre-registers Test 3's Sonnet-matched vote, and locks the k script's rule (the floor of the cost ratio per shape and effort,
    # capped at a fixed number and at the samples drawn); each of Tests 1-3's stamped caps is that rule's
    eq, t3row, ks = (S.find_lines(SPEC1_LOCK.name, p) for p in (EQ_RULE_LINE, T3_ROW_LINE, K_SCRIPT_LINE))
    if len(eq) != 1 or len(t3row) != 1 or len(ks) != 1:
        raise ValueError("TAB-01: the k tier says Study 1's k is set by its pre-registered equal-money rule; the locked spec does not "
                         f"name the rule, Test 3's Sonnet-matched vote and the k script's rule once each ({eq}, {t3row}, {ks})")
    spec_cap = int(re.search(K_SCRIPT_LINE, S.get(SPEC1_LOCK.name, f"L{ks[0]}")).group(1))
    for t in ("t1", "t2", "t3"):
        if S.get("main_k", _k_key(t, "cap")) != min(spec_cap, S.get("main_k", _k_key(t, "samples_drawn"))):
            raise ValueError(f"TAB-01: {t}'s stamped cap is not the locked k rule's (cap at {spec_cap} and at the samples drawn)")
    # B2's k (its note and the k note): the floor of Opus-medium's mean list cost per try over Haiku-max's, capped, by Study 1b's
    # pre-registered rule (section 4 of its spec)
    r = Fraction(S.get("s1b_k", "ratio"))
    if (S.get("s1b_k", "challenger") != "hx" or S.get("s1b_k", "comparator") != "om"
            or r != Fraction(S.get("s1b_k", "mean_list_cost_per_try.om")) / Fraction(S.get("s1b_k", "mean_list_cost_per_try.hx"))
            or S.get("s1b_k", "k") != min(floor(r), S.get("s1b_k", "cap")) or "study1b-spec §4" not in S.get("s1b_k", "rule")):
        raise ValueError("TAB-01: B2's k is not the floor of the two arms' mean list costs per try by Study 1b's spec rule")
    # Test 4's cost ratio is "post hoc arithmetic on pre-specified means" (Q15): item 24's means are defined in the reporting
    # definitions pinned before any main-run result was opened
    if not S.get("main", "reporting.group_b.item_24.note").startswith("research/reporting-definitions-main.md"):
        raise ValueError("TAB-01: Test 4's cost-ratio tier says its means are pre-specified; item 24 no longer cites its definitions")


def _texts(t: Table) -> Iterator[str]:
    """Every printed text of a built table: columns, rows, notes, caption facts, main-text notes and caption, panels."""
    for c in t.columns:
        yield c.printed
    for r in t.rows:
        yield from (c.printed for c in r)
    for n in list(t.notes) + list(t.main_notes or []):
        yield from (c.printed for c in n)
    for v in list(t.caption.values()) + list((t.main_caption or {}).values()):
        yield from (c.printed for c in v)
    for name, p in t.panels:
        yield name
        yield from _texts(p)


def _check_plain_words(t: Table) -> Table:
    """PO-1 and the notes check: no decision id, internal record name, 'the user'/'the authors' or time-zone guess prints."""
    bad = sorted({s for s in _texts(t) if BARRED.search(s)})
    if bad:
        raise ValueError(f"TAB-01 prints a decision id or an internal name (use plain words): {bad}")
    return t


def _tier(test: Cell, ratio_name: str, ratio_tier: Cell, has_k: bool) -> Cell:
    """A row's Tier cell: the test's tier (from its stamped Holm flag), then the error-rate ratio's, k's (where the row has a vote)
    and the spend or cost ratio's, so no column beside the test reads as confirmatory."""
    parts = [label("the test: "), test, label(f"; error-rate ratio: {ER_TIER}")]
    if has_k:
        parts.append(label(f"; k: {K_TIER}"))
    parts += [label(f"; {ratio_name}: "), ratio_tier]
    return joined(*parts, sep="")


def _k_key(t: str, field: str) -> str:
    """Study 1's k.json row for a vote test (Tests 1-3): the Opus or Sonnet k at the test's shape."""
    name, ch, cmp_, sh, kk = STUDY1_TESTS[t]
    return f"k_from_rows.{'opus' if kk == 'O' else 'sonnet'}.{sh}.{field}"


# The paper's word for each shape (Edith's PR #33 review: the paper never defines the 1×6 / 6×1 codes, and Table 1's "×N" means samples)
SHAPE_PLURAL = {"chain": "chains", "pieces": "pieces"}


def _s1_what(t: str, words: bool = False) -> str:
    name, ch, cmp_, sh, kk = STUDY1_TESTS[t]
    left = {"haiku-med": "Haiku-medium vote", "e3": "Step voting"}.get(ch, STUDY1_ARMS[ch][0])
    return f"{left} vs {STUDY1_ARMS[cmp_][0]}, {SHAPE_PLURAL[shape_word(sh)] if words else shape(sh)}"


def _s1_k_spend(S: Store, t: str, ratio_dp: int = RATIO_DP) -> List[Cell]:
    """Tests 1-3: k (k.json) and the vote's realised spend over the comparator's at list price (item 8b, priced by item 9a's list
    prices). Test 4: no stamped ratio, so the two arms' mean list costs per puzzle (item 24) are divided for this table (post hoc
    arithmetic on pre-specified means). Test 5: item 9h's stamped cost ratio with its stamped interval (exploratory, no test), printed
    as TAB-05 prints it."""
    name, ch, cmp_, sh, kk = STUDY1_TESTS[t]
    if kk is not None:
        k = integer(S.ref("main_k", _k_key(t, "k")))
        return [k, num(S.ref("main", join_key(*SPEND.split("."), t, "by_row", "k+0", "haiku_over_comparator")), dp=RATIO_DP)]
    if t == "t5":
        pair = join_key(*ITEM9H.split("."), sh, "pairs", f"{ch}-vs-{cmp_}")
        return [DASH, joined(num(S.ref("main", f"{pair}.point.cost_ratio"), dp=T5_RATIO_DP),
                             interval(*ci_refs(S, "main", f"{pair}.intervals.cost_ratio.ci95"), dp=T5_RATIO_DP))]
    r = derive("challenger mean list cost per puzzle / comparator's", lambda a, b: a / b,
               S.ref("main", join_key(*ITEM24.split("."), f"{ch} {sh}", "cost_per_puzzle", "mean")),
               S.ref("main", join_key(*ITEM24.split("."), f"{cmp_} {sh}", "cost_per_puzzle", "mean")))
    return [DASH, num_d(r, dp=ratio_dp)]


def _named(name: str, c: Cell) -> Cell:
    """The full table's spend share or cost ratio cell with its quantity named in the cell (Edith's §2.8: the column holds two quantities,
    each at its own precision). A dash stays a dash."""
    return c if c.printed in core.DASHES else joined(label(name), c)


def _paper_k_spend(k_spend: List[Cell], cost_ratio: Optional[Cell]) -> Cell:
    """Table 2's "k; spend share" cell (Edith's ruling on §2.1/§2.8, 2026-10-17): a cost-matched vote's k and spend share (3 decimals,
    as the ledger and the ruled wording print it); any other test's cell names its quantity, "cost ratio 0.09", at a cost ratio's 2
    decimals."""
    if cost_ratio is None:
        return joined(*k_spend, sep="; ")
    return joined(label("cost ratio"), cost_ratio)


def _s1_ratio_tier(S: Store, t: str) -> Tuple[str, Cell]:
    """Study 1's spend share or cost ratio, named and labelled as _s1_k_spend prints it: Tests 1-3 a spend share (pre-specified descriptive),
    Test 4 a cost ratio (post hoc arithmetic on pre-specified means), Test 5 a cost ratio under item 9h's stamped label."""
    if STUDY1_TESTS[t][4] is not None:
        return "spend share", label(RATIO_TIER)
    if t == "t5":
        return "cost ratio", text_of(S.ref("main", f"{ITEM9H}.label"))
    return "cost ratio", label(T4_RATIO_TIER)


# A blank line inside a cell is a paragraph break in its wrapping column, so a forced line break (the writer passes it through; the CSV
# keeps it). The paper's Table 2 stacks every error-rate ratio over its interval with it, as its d column stacks (Edith, proof 4, §2.8): a
# one-line "2.2 [1.5, 3.9]" would stand 34 pt out of line beside the stacked "11.0 / [4.7, unbounded]".
BREAK = "\n\n"


def _ratio_cell(S: Store, src: str, e: str, dp: int = 2, stacked: bool = False) -> Cell:
    """An error-rate ratio with its 95% interval (a comparator without errors: the comparator's error count instead); `stacked` puts the
    interval (or the count) on a line of its own under the ratio (the paper's Table 2)."""
    sep = BREAK if stacked else " "
    if not S.get(src, f"{e}.defined"):
        return joined(text_of(S.ref(src, f"{e}.defined"), {False: "undefined"}),
                      joined(label("(comparator errors "), integer(S.ref(src, f"{e}.E_cmp")), label(" of "), integer(S.ref(src, f"{e}.n")),
                             label(")"), sep=""), sep=sep)
    lo, hi = ci_refs(S, src, f"{e}.ci95")
    return joined(num(S.ref(src, f"{e}.R"), dp=dp), interval(lo, hi, dp=dp), sep=sep)


def _to(lo, hi, margin: float) -> List[Cell]:
    """'lo to hi' (the style sheet's interval form in prose, Polish §2.4: "−1.2 to +2.4"; the bracketed form in a table drops the "+"),
    signed, with the one-more-decimal guard at 0 and the margin."""
    return [num(lo, dp=2, signed=True, bounds=(0.0, margin)), label(" to "), num(hi, dp=2, signed=True, bounds=(0.0, margin))]


@output("TAB-01")
@main_text
def tab_01(S: Store) -> Table:
    _check_wording(S)
    cols = ["Test", "Study", "Puzzles", "What is compared", "Margin (points)", "k", "Spend share or cost ratio",
            "d (points)", "95% interval", "Reading (pre-registered decision rule)", "Shown no worse (Holm-adjusted)",
            "Shown no worse (Holm-adjusted) at Study 1b's secondary 10-point margin", "Error-rate ratio [95%]", "Label", "Steps",
            "Decision"]
    rows = []
    paper = []                                        # Table 2 of the paper: the same refs at one decimal (D-161)
    for t, (name, ch, cmp_, sh, kk) in STUDY1_TESTS.items():
        tk = f"{S1}.tests.{t}"
        lo, hi = ci_refs(S, "main", f"{tk}.ci95")
        m = S.ref("main", f"{S1}.margin")
        k_cell, ratio_cell = _s1_k_spend(S, t)
        rows.append([label(name), label("Study 1"), integer(S.ref("main", f"{tk}.n")), label(_s1_what(t)),
                     num(m, dp=0, signed=True), k_cell, _named("spend share" if kk is not None else "cost ratio", ratio_cell),
                     pts(S.ref("main", f"{tk}.d"), margin=float(m.value)),
                     interval(lo, hi, dp=2, signed=True, bounds=(0.0, float(m.value))),
                     text_of(S.ref("main", f"{tk}.reading"), RULE_READING),
                     text_of(S.ref("main", f"{tk}.declared"), YES_NO), DASH,
                     _ratio_cell(S, "main", f"reporting.error_ratios.{t}"),
                     _tier(text_of(S.ref("main", f"{tk}.declared"), S1_TIER), *_s1_ratio_tier(S, t), has_k=kk is not None),
                     integer(S.ref("main_plan", "steps")),
                     _decision(S, S.ref("main", f"{tk}.reading"), S.ref("main", f"{tk}.declared"), None, m,
                               qualifier=("marking rule as run", S.ref("main", "secondary.original_repeat_rule.tests.t3.reading"))
                               if t == "t3" else None)])
        paper.append([label(name), integer(S.ref("main_plan", "steps")), label(_s1_what(t, words=True)),
                      _paper_k_spend(_s1_k_spend(S, t), None if kk is not None else _s1_k_spend(S, t, ratio_dp=COST_RATIO_DP)[1]),
                      _d_ci(S, "main", tk, m),
                      _ratio_cell(S, "main", f"reporting.error_ratios.{t}", dp=PAPER_RATIO_DP, stacked=True),
                      _decision(S, S.ref("main", f"{tk}.reading"), S.ref("main", f"{tk}.declared"), None, m, bold=t in BOLD_DECISIONS,
                                qualifier=("marking rule as run", S.ref("main", "secondary.original_repeat_rule.tests.t3.reading"))
                                if t == "t3" else None)])
    for b in B_TESTS:
        tk = f"{S1B}.tests.{b}"
        lo, hi = ci_refs(S, "s1b", f"{tk}.ci95")
        m = S.ref("s1b", f"{S1B}.margin")
        if b == "B2":
            k_spend = [integer(S.ref("s1b_k", "k")), num(S.ref("s1b", "costs_beside_tests.B2.ratio_challenger_over_comparator"),
                                                         dp=RATIO_DP)]
        else:
            k_spend = [DASH, num(S.ref("s1b", f"costs_beside_tests.{b}.ratio_challenger_over_comparator"), dp=RATIO_DP)]
        rows.append([label(b), label("Study 1b"), integer(S.ref("s1b", f"{tk}.n")), label(B_WHAT[b]),
                     num(m, dp=0, signed=True), k_spend[0], _named("spend share" if b == "B2" else "cost ratio", k_spend[1]),
                     pts(S.ref("s1b", f"{tk}.d"), margin=float(m.value)),
                     interval(lo, hi, dp=2, signed=True, bounds=(0.0, float(m.value))),
                     text_of(S.ref("s1b", f"confirmatory.primary_margin_5.template.{b}"), B_READING),
                     text_of(S.ref("s1b", f"{tk}.declared"), YES_NO),
                     text_of(S.ref("s1b", f"{S1B_SEC}.tests.{b}.declared"), YES_NO),
                     _ratio_cell(S, "s1b", f"error_ratios.{b}"),
                     _tier(text_of(S.ref("s1b", f"{tk}.declared"), S1B_TIER), "spend share" if b == "B2" else "cost ratio", label(RATIO_TIER),
                           has_k=b == "B2"),
                     integer(S.ref("s1b", f"completeness.{b}.N")),
                     _decision(S, S.ref("s1b", f"{tk}.reading"), S.ref("s1b", f"{tk}.declared"),
                               (S.ref("s1b", f"{S1B_SEC}.tests.{b}.reading"), S.ref("s1b", f"{S1B_SEC}.tests.{b}.declared"),
                                S.ref("s1b", f"{S1B_SEC}.margin")), m)])
        paper.append([label(b), integer(S.ref("s1b", f"completeness.{b}.N")), label(B_SHORT[b]),
                      _paper_k_spend(k_spend, None if b == "B2" else num(S.ref("s1b", f"costs_beside_tests.{b}.ratio_challenger_over_comparator"),
                                                                         dp=COST_RATIO_DP)),
                      _d_ci(S, "s1b", tk, m), _ratio_cell(S, "s1b", f"error_ratios.{b}", dp=PAPER_RATIO_DP, stacked=True),
                      _decision(S, S.ref("s1b", f"{tk}.reading"), S.ref("s1b", f"{tk}.declared"),
                                (S.ref("s1b", f"{S1B_SEC}.tests.{b}.reading"), S.ref("s1b", f"{S1B_SEC}.tests.{b}.declared"),
                                 S.ref("s1b", f"{S1B_SEC}.margin")), m, bold=b in BOLD_DECISIONS)])

    sec = []
    floored_p = False
    for i, b in enumerate(B_TESTS):
        pc = pvalue_bound(S.ref("s1b", f"{S1B_SEC}.tests.{b}.p"), S.ref("s1b", f"{S1B_SEC}.tests.{b}.z0"),
                          S.ref("s1b", f"{S1B_SEC}.tests.{b}.a"), S.ref("s1b", f"{S1B_SEC}.B"), dp=5)          # Edith's TP-11
        floored_p = floored_p or pc.printed.startswith(chr(0x2264))
        sec += [label(("; " if i else "") + f"{b}: p " + ("" if pc.printed.startswith(chr(0x2264)) else "= ")), pc,
                label(", below its Holm threshold of "), core.exact(S.ref("s1b", f"{S1B_SEC}.holm_thresholds.{b}"))]
    o3, o5 = f"{ORIG}.t3", f"{ORIG}.t5"
    rates = "secondary.rates.sonnet-med"
    b2c = "costs_beside_tests.B2"
    notes = [
        [label("In the reading columns, \"> margin\" stands for \"by more than the margin\": \"worse by > margin\" is worse by more than the margin, "
               "as the other tables of this supplement write it.")],
        [label("Holm's correction runs within each study only; the two studies are never pooled. At Study 1's 10-point margin (its only "
               "confirmatory margin; a secondary 5-point view is in ⟦TAB-03⟧) only Test 5 was shown no worse (Holm-adjusted), and at "
               "Study 1b's primary 5-point margin only B2. Tests 1–4, B1 and B3 carry the pre-registered decision rule's reading of the "
               "unadjusted 95% interval, which is never a Holm-adjusted result.")],
        [joined(label("At Study 1b's pre-registered secondary 10-point margin, quoted only as the secondary, B1, B2 and B3 were each "
                      "shown no worse than Opus-medium by more than the margin (Holm-adjusted; "), *sec, label(")."), sep="")],
        *([[label(FLOOR_NOTE + ".")]] if floored_p else []),
        [joined(label("Under the original pre-registered marking rule, which Deviation 2 kept as a sensitivity check (fixed in "
                      "Lock 3, before any main-run data; not a pre-registered secondary view), Sonnet-medium's chain score is "),
                pct(S.ref("main", f"{rates}.original_acc"), dp=2), label("% instead of "),
                pct(S.ref("main", f"{rates}.official_acc"), dp=2), label("% (format compliance "),
                pct(S.ref("main", f"{rates}.format_compliance_original"), dp=2), label("% instead of "),
                pct(S.ref("main", f"{rates}.format_compliance"), dp=2), label("%). Test 3 would read "),
                text_of(S.ref("main", f"{o3}.reading")), label(" (d = "), pts(S.ref("main", f"{o3}.d"), margin=-10.0),
                label(" points, 95% interval "), interval(*ci_refs(S, "main", f"{o3}.ci95"), dp=2, bounds=(0.0, -10.0)), label(") instead of "),
                text_of(S.ref("main", f"{S1}.tests.t3.reading")), label(". Test 5's reading is unchanged (d = "),
                pts(S.ref("main", f"{o5}.d"), margin=-10.0), label(" points, 95% interval "),
                interval(*ci_refs(S, "main", f"{o5}.ci95"), dp=2, bounds=(0.0, -10.0)), label(")."), sep="")],
        [label("Sonnet ran at medium effort, one level below its default (high), in Tests 3 and 5.")],
        [label("Study 1's tests were pre-registered at 24 steps and run at 6 steps (Deviation 1).")],
        [joined(label("B2's accuracy is the expected accuracy of a vote of k = "), integer(S.ref("s1b_k", "k")),
                label(" Haiku-max samples, computed from the "), integer(S.ref("s1b", "constants.designed_tries.hx")),
                label(" designed samples per puzzle and shape (no vote of that size was run separately); k was measured from the two "
                      "settings' mean list costs per sample. Per shape, the vote costs $"),
                usd(S.ref("s1b", f"{b2c}.challenger.1x16.list_usd")),
                label(" per answer on chains against Opus-medium's $"), usd(S.ref("s1b", f"{b2c}.comparator.1x16.list_usd")),
                label(", and $"), usd(S.ref("s1b", f"{b2c}.challenger.16x1.list_usd")), label(" on pieces against $"),
                usd(S.ref("s1b", f"{b2c}.comparator.16x1.list_usd")), label(" (list price)."), sep="")],
        [joined(label("d (points): the challenger (named first) minus the comparator, in accuracy points, paired over puzzles "
                      "(in Study 1b both shapes of a puzzle are pooled); a positive d means the challenger scored higher. "
                      "Shapes: "), label(shape("1x6")), label(" is the chain form of a puzzle and "), label(shape("6x1")),
                label(" the pieces form. k (Tests 1–3): the size of the cost-matched Haiku-medium vote, the most samples whose combined "
                      "mean cost fits within the comparator's mean cost per puzzle; the k computation prices each call at the Batch "
                      "rate, exactly half the list price, so k is the same at list prices (B2's k is in the note above). Test 1's k is "
                      "capped at "), integer(S.ref("main_k", _k_key("t1", "cap"))),
                label(", the number of samples drawn per puzzle and shape, from the cost-matched "),
                integer(S.ref("main_k", _k_key("t1", "raw_k"))), label("."), sep="")],
        [joined(label("k, spend share and cost ratio (none is tested; k is defined in the notes above). Each cell of the spend share or cost "
                      "ratio column names its "
                      f"quantity; spend shares and the cost ratios of Test 4, B1 and B3 print to {DP_WORDS[RATIO_DP]} decimals and Test 5's cost "
                      f"ratio to {DP_WORDS[T5_RATIO_DP]}, as ⟦TAB-05⟧ prints it. Spend share: Tests 1–3, the vote's realised spend over the comparator's at list price "
                      "(pre-specified descriptive); B2, the vote's list cost per answer over Opus-medium's, as reported beside the "
                      "test (pre-specified descriptive). Cost ratio: Test 4, step voting's mean list cost per puzzle over "
                      "Opus-medium's, computed for this table from the two reported means (post hoc arithmetic on pre-specified "
                      "means); Test 5, Opus-low's list cost per answer over Sonnet-medium's with its 95% interval, labelled "),
                text_of(S.ref("main", f"{ITEM9H}.label")),
                label("; B1 and B3, the challenger's list cost per answer over Opus-medium's, as reported beside each test "
                      "(pre-specified descriptive). The file's own words for one Haiku-max sample's cost are, for B1, \""),
                text_of(S.ref("s1b", "costs_beside_tests.B1.wording")),
                label("\" and, for B3, \""), text_of(S.ref("s1b", "costs_beside_tests.B3.wording")), label("\"."), sep="")],
        [label(f"Error-rate ratio ({ER_TIER}; not part of any test's reading): the challenger's errors over the comparator's. An "
               "unbounded upper end comes from bootstrap draws in which the comparator made no errors.")],
        *[[joined(label(f"{STUDY1_TESTS[t][0]}'s error-rate ratio is undefined: the comparator made no errors, so its error rate is "
                        "at most "), pct(S.ref("main", f"reporting.error_ratios.{t}.comparator_error_rate_upper95"), dp=2),
                  label("%, the upper end of the exact 95% interval."), sep="")]
          for t in STUDY1_TESTS if not S.get("main", f"reporting.error_ratios.{t}.defined")],
    ]
    caption = {
        "tier": [joined(label("the tests (d and the pre-registered reading): confirmatory; Test 5 (at Study 1's 10-point margin) and "
                              "B2 (at Study 1b's primary 5-point margin) shown no worse (Holm-adjusted); Tests 1–4, B1 and B3 read by the "
                              "pre-registered decision rule on the unadjusted interval (not Holm-adjusted); B1–B3 also shown at Study "
                              f"1b's secondary 10-point margin, quoted only as the secondary. Error-rate ratios: {ER_TIER} (not part of "
                              "any test's reading). k, the spend shares and the cost ratios: not tested (labels in the notes); k is each "
                              "vote's size, set by its study's pre-registered rule for a cost-matched vote; the spend shares of Tests 1–3 "
                              "and B2 and the cost ratios of B1 and B3: pre-specified descriptive; Test 5's cost ratio: "),
                        text_of(S.ref("main", f"{ITEM9H}.label")),
                        label("; Test 4's cost ratio: post hoc arithmetic on pre-specified means"), sep="")],
        "study": [label("Study 1 (main run, 6 steps) and Study 1b (16 steps and 6 steps); Holm within each study only, never pooled")],
        "set": [label("Study 1: the main-run puzzle set at 6 steps (Test 1 on pieces, Tests 2–5 on chains); Study 1b: fresh puzzle "
                      "sets at 16 steps (B1, B2) and at 6 steps (B3), chains and pieces pooled per puzzle")],
        "n": [label("Study 1:"), integer(S.ref("main", f"{S1}.tests.t1.n")),
              label("puzzles per test; the Haiku-medium vote drawn from"),
              integer(S.ref("main_k", "k_from_rows.opus.1x6.samples_drawn")),
              label("samples per puzzle and shape; step voting made"),
              integer(S.ref("main", join_key(*ITEM24.split("."), "e3 1x6", "refusals_and_truncations", "calls_made"))),
              label("calls over its"), integer(S.ref("main", join_key(*ITEM24.split("."), "e3 1x6", "base_puzzles"))),
              label("puzzles; Opus and Sonnet one answer per puzzle. Study 1b:"),
              integer(S.ref("s1b", f"{S1B}.tests.B1.n")), label("puzzles for B1 and B2 and"),
              integer(S.ref("s1b", f"{S1B}.tests.B3.n")), label("for B3, each in both shapes, with"),
              integer(S.ref("s1b", "constants.designed_tries.hx")), label("Haiku-max samples and"),
              integer(S.ref("s1b", "constants.designed_tries.om")), label("Opus-medium samples per puzzle and shape")],
        "interval": [label("95%. d: paired BCa bootstrap over puzzles, B ="), integer(S.ref("main", f"{S1}.B")),
                     label("(Study 1) and"), integer(S.ref("s1b", f"{S1B}.B")),
                     label("(Study 1b); error-rate ratio: paired percentile bootstrap over puzzles; an error-rate ratio's upper end "
                           "is unbounded where the comparator made no errors in some bootstrap draws; Test 1's comparator bound:"),
                     text_of(S.ref("main", "reporting.error_ratios.t1.comparator_interval"),
                             {"clopper-pearson": "exact Clopper–Pearson;"}),
                     label("Test 5's cost ratio: paired cluster bootstrap over puzzles, two-sided, unadjusted (exploratory)")],
        "price": [label("list price, US dollars")],
    }
    t = Table([label(c) for c in cols], rows, notes, caption)
    # the supplement's layout: 16 columns are too many for one page, so the table splits into four parts, each beginning with the Test
    # column (portrait, 6.5 in), in the order identity, estimate, interval, decision (Edith §7.7): what was compared (study, puzzles,
    # steps, margin), the vote size, spend share or cost ratio and the estimates (d, its interval, the error-rate ratio), the reading of
    # the pre-registered decision rule with the Holm-adjusted columns and the decision, and last the label of each thing the row prints
    # (long text, which would take most of a part's width). The Length column of the first build is gone: the Steps column prints the
    # stamped count. Rows fall into two groups, Study 1's tests and Study 1b's, with a little space above Study 1b's first row.
    t.layout = "split"
    # 8 pt (the floor): the last part (the labels, with every note of the table under it) was 8.84 of 9.0 in with a two-line caption
    # stand-in, and too tall by 2.3 pt in Vision's build once a caption is followed by a full line (proof 3 template)
    t.font = "footnotesize"
    t.split_parts = [(None, [1, 2, 14, 3, 4]), (None, [5, 6, 7, 8, 12]), (None, [9, 10, 11, 15]), (None, [13])]
    t.groups = [i for i in range(1, len(rows)) if rows[i][1].printed != rows[i - 1][1].printed]
    # Table 2 of the paper (D-160; Vision's plan §0c, Edith a1c9fef; D-161): seven columns at one decimal and one short note (what d is,
    # the error-rate ratio's unbounded end, and the untested spend shares; Edith, proof 2: the printed notes take two lines together).
    # Holm's scope is in the caption (D-180's form, Vision c05f4eab), so the note gives the unbounded end in its place (Edith, proof 4
    # §9.1). The error-rate ratio's definition is in the Method legend; every other note prints in the supplement's full table.
    if not any(r[5].printed.endswith(", unbounded]") for r in paper) or any(
            "unbounded" in c.printed for r in paper for j, c in enumerate(r) if j != 5):
        raise ValueError("Table 2's note says an error-rate ratio is unbounded above: it must print there, and only there")
    main_notes = [
        [label("d: challenger (named first) minus comparator, in accuracy points, paired over puzzles. " + UNBOUNDED_NOTE
               + " Spend shares and cost ratios are not tested (Test 5's is exploratory).")]]
    t.main_table = _check_plain_words(Table(
        [label(c) for c in ("Test", "Steps", "Comparison", "k; spend share", "d (points) [95% interval]",
                            "Error-rate ratio [95% interval]", "Decision")],
        paper, main_notes, caption, short_notes=[0], layout="float", font="footnotesize"))
    # Table 2 stays at 8 pt (the floor): at \small its float grows 1.71 in and the review body, already 12.08 pp at Vision's f8eb3518,
    # would go further past 12.00 (Edith A.20: waived in writing if the body does not hold)
    # Edith §7.7 (proof 2): a break between Study 1 (Tests 1–5) and Study 1b (B1–B3), and a little space between the tests' rows
    t.main_table.groups = [len(STUDY1_TESTS)]
    t.main_table.spaced = True
    return _check_plain_words(t)


def _d_ci(S: Store, src: str, tk: str, m: Ref) -> Cell:
    """d with its 95% interval at the paper's one decimal (D-161), with the one-more-decimal guard at 0 and the margin; the interval's
    positive end unsigned (house style: "[−1.1, 2.4]")."""
    lo, hi = ci_refs(S, src, f"{tk}.ci95")
    return joined(pts(S.ref(src, f"{tk}.d"), dp=1, margin=float(m.value)),
                  interval(lo, hi, dp=1, signed=False, bounds=(0.0, float(m.value))))


# The decision column's words (Edith a1c9fef; D-161 option B, "Holm-adjusted"; C-165 keeps the locked word in quotation marks only):
# each is the stamped reading and
# Holm flag (and, for Study 1b, the secondary margin's) in the Method legend's words; the margins are read, never typed.
def _decision(S: Store, reading: Ref, declared: Ref, secondary, margin: Ref, bold: bool = False,
              qualifier: Optional[Tuple[str, Ref]] = None) -> Cell:
    """The decision words. `qualifier` (words, the stamped reading that supports them) adds a companion inside the rule's bracket,
    e.g. Test 3's "worse by > 10 (pre-registered rule; marking rule as run)" with the original marking rule's different reading as its
    source (Vision's request, so the caption meets Edith's 30 words)."""
    r, d = reading.value, declared.value
    refs = [reading, declared, margin]
    if secondary is not None:
        refs += list(secondary)
    size = lambda m, what: num_d(derive(what, lambda x: abs(x), m), dp=0)
    if d is True and r == "non-inferior":
        c = joined(label("shown no worse by >"), size(margin, "the margin's size"), label("(Holm-adjusted)"))
        raw = [r, d]
    elif d is False and str(r).startswith("worse") and (secondary is None or secondary[1].value is False):
        c = joined(label("worse by >"), size(margin, "the margin's size"),
                   label("(pre-registered rule)" if qualifier is None else f"(pre-registered rule; {qualifier[0]})"))
        raw = [r, d]
        if qualifier is not None:
            if qualifier[1].value == r:
                raise ValueError(f"TAB-01: the qualifier {qualifier[0]!r} needs a different reading under the other rule")
            refs.append(qualifier[1])
    elif d is False and r == "inconclusive" and secondary is not None and secondary[0].value == "non-inferior" and secondary[1].value is True:
        c = joined(label("inconclusive at"), joined(size(margin, "the primary margin's size"), label(";"), sep=""),
                   label("shown no worse by >"), size(secondary[2], "the secondary margin's size"), label("(Holm-adjusted)"))
        raw = [r, d, secondary[0].value, secondary[1].value]
    else:
        raise ValueError(f"TAB-01: no decision words for reading {r!r}, Holm-adjusted {d!r}, secondary "
                         f"{None if secondary is None else (secondary[0].value, secondary[1].value)!r}")
    return Cell(c.printed, raw=raw, refs=tuple(refs), formula=DECISION_FORMULA, bold=bold)


# Bold in Table 2's decision cells: none. The anchors (Tests 1 and 2, and B2) were bold, but once the caption is cut to Edith's 30
# words a note would have to say what bold marks, and both short notes are full (Vision's choice, 2026-10-17: drop the bold).
BOLD_DECISIONS: tuple = ()


DECISION_FORMULA = "the stamped reading and Holm flags (and Study 1b's secondary-margin ones) in the Method legend's words"
