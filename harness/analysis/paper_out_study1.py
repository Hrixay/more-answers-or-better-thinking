"""Study 1 tables (main run, 6 steps, 80 bases): the plan's TAB-02 and the Study 1 appendix tables. Every cell is read from the pinned
Study 1 files (`main`, `main_k`, `groupc`) by key; the few notes and rules that quote a text (the spec's Amendment 1, the reporting
definitions, the pre-registered pilot plan, the analysis code as run) read it from that text pinned below. See paper_out_core.py for
the rules.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .paper_out_core import (split_rows_by_space, fa4_exact, pvalue_bound, DASHES, EMPTY, Cell, KeyMissing, Ref, Source, Store, Table, YES_NO, _need_num, ci_refs, dec, derive, exact, fmt_fixed, fmt_sf,
                             integer, interval, join_key, joined, label, num, num_d, output, parse_key, pct, pvalue, pts, register_source,
                             text_of, usd)
from .paper_out_names import MAIN_TEXT_ID, STUDY1B_TAGS, STUDY1_ARMS, STUDY1_TESTS, main_text, shape, shape_word
from .paper_out_overview import UNBOUNDED_NOTE, BARRED, RATIO_DP, T4_RATIO_TIER, T5_RATIO_DP, _s1_reading, _s1_what, _to

MARGIN = -10.0
VIEW = "confirmatory.views.as_deployed"
DASH = label("—")

# The paper's plain names where the shared display name carries an internal arm code (the style sheet keeps codes such as E3 out of
# the main text; "step voting" is the glossary name).
_PLAIN_NAME = {"e3": "Step voting"}

# ---------------------------------------------------------------- pinned text sources (this module's own names, so that its pins
# never depend on another module's). Each SHA-256 is that of `git show <commit>:<path>`.
# The Study 1 spec, last changed on main by f773d83 (Amendment 1 per Edith's review): Amendment 1's item 6 defines the near-ceiling
# label (Edith's Q17: the notes define "near ceiling (Amendment 1)" from Amendment 1's own text).
register_source(Source(
    name="s1_spec", path="studies/1-real-price/spec.md", commit="f773d83",
    sha256="0ab437934a8df843db20ff9eb4aa57dd6e8228605f38df4b77e138d942e6c169", kind="text",
    what="The Study 1 pre-registration spec: Amendment 1, item 6 (the near-ceiling label)"))
# Study 1's reporting definitions as stamped before any result was opened (the analysis stamp's definitions commit, 93334b8, which is
# also the last change on main): the error-rate ratio's scope (all five tests) and the low-information flag's threshold.
register_source(Source(
    name="s1_defs", path="research/reporting-definitions-main.md", commit="93334b8",
    sha256="bddab72761b4111f6d4ed439f13ddbd63427bc14a9c61b58d0ceadb32f18bf81", kind="text",
    what="Study 1's reporting definitions: the error-rate ratio (which tests) and the low-information flag (its threshold)"))
# The pre-registered pilot plan, last changed by 7bcc8d1 for lock 2: the fairness check's Flag K and Flag R thresholds.
register_source(Source(
    name="s1_pilot_plan", path="research/pilot-plan-ledger.md", commit="7bcc8d1",
    sha256="51c811bdb99e22ad0168d1a02ed4334841b0153beff90b5368ca6942371911f9", kind="text",
    what="The pre-registered pilot plan (lock 2): the fairness check's Flag K and Flag R"))
# The analysis code that produced the Study 1 result file, at the commit the stamped driver ran at (c273eb9; neither file changed on
# main after it). TAB-07's thresholds that the result file does not stamp are read from these lines (Edith's Q18).
register_source(Source(
    name="s1_fairness_py", path="harness/analysis/fairness.py", commit="c273eb9",
    sha256="6af248e7aaa70f179aa53b922cbae7b3255ca0512568e5aff20a685984319587", kind="text",
    what="The fairness check's code as run (Flag K's and Flag R's thresholds, the assessability minima)"))
register_source(Source(
    name="s1_main_analysis_py", path="harness/analysis/main_analysis.py", commit="c273eb9",
    sha256="5fb0ab788aef57759e3a90f3b4b8dd5064bc36c2c25fac9fb9de74fba1695627", kind="text",
    what="The Study 1 analysis driver as run (Flag R's minimum pairs, the low-information flag's threshold)"))
# The console log of that driver's one run, committed with the result file: it names the commit the driver ran at.
register_source(Source(
    name="s1_driver_log", path="data/main/main-l14n6-1/driver-run.log", commit="8be72ec",
    sha256="bb77248f86b282d4b87f540591079b27eaec67bc01d2316aec2a9542488fe7fe", kind="text",
    what="The Study 1 driver's console log (the commit it ran at)"))
# Our work log at the commit paper_out_ops.py pins it (as "log"), under this module's own name: its entry for the Study 1 driver run
# names the commit the run's checkout was at, the code commit TAB-23 prints for the Study 1 analysis. TAB-07's Rule note points the
# reader there for the code's commit (the file's name is internal and never prints).
register_source(Source(
    name="s1_work_log", path="LOG.md", commit="bec30e3",
    sha256="16a220dae12460a5a8e9b0dc9c4371a50ed0d51901357ba30efe4a0f6339e1b8", kind="text",
    what="Our work log: the Study 1 driver run's entry (the commit its checkout was at)"))


def _one_line(S: Store, source: str, pattern: str) -> int:
    """The number of the one line of a pinned text source that matches `pattern` (refused unless exactly one does)."""
    hits = S.find_lines(source, pattern)
    if len(hits) != 1:
        raise KeyMissing(f"{source}: {len(hits)} lines match {pattern!r}")
    return hits[0]


def _code_number(S: Store, source: str, pattern: str) -> Cell:
    """A threshold as the pinned code writes it: group 1 of the one line matching `pattern`, read by its line key."""
    return _stamped_number_in(S, source, f"L{_one_line(S, source, pattern)}", pattern)


def _cite(S: Store, source: str, pattern: str) -> Cell:
    """A citation with nothing printed: the one line matching `pattern` joins the cell's sources (e.g. the code line that sets the
    assessability minima a rule depends on)."""
    r = S.ref(source, f"L{_one_line(S, source, pattern)}")
    return Cell("", raw=r.value, refs=(r,), formula="cited line (not printed): the code or text that sets this rule")


def _code_ran(S: Store) -> None:
    """The pinned code is the code that produced the Study 1 result file: the driver's console log, committed with that file, names
    the commit it ran at, which must be the code pins' commit."""
    if S.sources["s1_driver_log"].commit != S.sources["main"].commit:
        raise ValueError("the driver log is not the one committed with the Study 1 result file")
    pat = r"now: ([0-9a-f]{40})\)"
    ran = re.search(pat, S.get("s1_driver_log", "L" + str(_one_line(S, "s1_driver_log", pat)))).group(1)
    for src in ("s1_fairness_py", "s1_main_analysis_py"):
        if not ran.startswith(S.sources[src].commit):
            raise ValueError(f"{src} is pinned at {S.sources[src].commit}; the driver ran at {ran}")


def _arm_name(arm: str) -> str:
    return _PLAIN_NAME.get(arm, STUDY1_ARMS[arm][0])


def _challenger(test: str) -> str:
    """A test's challenger in plain words: the Haiku-medium vote for Tests 1-3, else the arm's name."""
    ch = STUDY1_TESTS[test][1]
    return "Haiku-medium vote" if ch == "haiku-med" else _arm_name(ch)


def _set_cells(S: Store) -> List[Cell]:
    """The Study 1 puzzle set in plain words (set ids stay in the methods appendix): refuse to build unless the main file is at
    6 steps and every stamped real-time puzzle id names one set."""
    ids = S.get("main", "reporting.realtime.puzzles")
    sets = {re.sub(r"-\d+-(?:1x6|6x1)$", "", p) for p in ids}
    if S.get("main", "n") != 6 or len(sets) != 1:
        raise ValueError(f"Study 1 set: n = {S.get('main', 'n')}, set ids {sorted(sets)}")
    return [label("the Study 1 main-run puzzle set at 6 steps: each puzzle as a chain (1×6) and as pieces (6×1)")]


def _thousands(r: Ref, dp: int = 0) -> Cell:
    """A stamped number rounded by the core's rule (on the stamped decimal, half away from zero), printed with a thousands separator."""
    _need_num(r)
    s = fmt_fixed(dec(r.value), dp)
    sign, body = (s[0], s[1:]) if not s[0].isdigit() else ("", s)
    whole, _, frac = body.partition(".")
    return Cell(sign + f"{int(whole):,}" + ("." + frac if frac else ""), raw=r.value, refs=(r,))


def _fc_cell(S: Store, arm: str, sh: str) -> Cell:
    """An arm's format compliance (%) at a shape, from the first block that stamps it: confirmatory.format_compliance (the
    confirmatory arms), item 10's per-arm block (the other Haiku settings and Sonnet-low), item 24's row; a dash where none does."""
    for key in (f"confirmatory.format_compliance.{arm}.{sh}.format_compliance",
                join_key("reporting", "group_b", "item_10", "arms", f"{arm} {sh}", "format_compliance", "format_compliance"),
                join_key("reporting", "group_b", "item_24", "table", f"{arm} {sh}", "format_compliance", "format_compliance")):
        if S.has("main", key):
            return pct(S.ref("main", key), dp=2)
    return DASH


def _k_cells(S: Store, test: str) -> List[Cell]:
    """k, raw k and cap from k.json's k_from_rows (Tests 1-3); a dash for Tests 4-5 (no vote)."""
    _, ch, cmp_, sh, kk = STUDY1_TESTS[test]
    if kk is None:
        return [DASH, DASH, DASH]
    base = f"k_from_rows.{'opus' if kk == 'O' else 'sonnet'}.{sh}"
    return [integer(S.ref("main_k", f"{base}.k")), integer(S.ref("main_k", f"{base}.raw_k")), integer(S.ref("main_k", f"{base}.cap"))]


def _spend_ratio(S: Store, test: str) -> Cell:
    """The vote's realised spend over the comparator's at the test's k, at list price: item 8b's realised_spend row k+0 (k.json holds
    the same ratio from Batch-priced costs). Refuse to build if that row's k is not k.json's k or the block is not list-priced."""
    _, ch, cmp_, sh, kk = STUDY1_TESTS[test]
    if test == "t5":
        # Test 5 has no vote: Opus-low's list cost over Sonnet-medium's, the same stamped ratio and interval TAB-01 prints, with
        # item 9h's stamped tier (exploratory; Edith and Vision, so the table shows what the caption says)
        pair = join_key("reporting", "group_b", "item_9h", sh, "pairs", f"{ch}-vs-{cmp_}")
        return joined(num(S.ref("main", f"{pair}.point.cost_ratio"), dp=T5_RATIO_DP), label(" "),
                      interval(*ci_refs(S, "main", f"{pair}.intervals.cost_ratio.ci95"), dp=T5_RATIO_DP), label("; cost ratio, "),
                      text_of(S.ref("main", "reporting.group_b.item_9h.label")), sep="")
    if test == "t4":
        # Test 4 has no vote, so no spend share; Table S14 (TAB-01) prints its cost ratio, the two settings' mean list costs per puzzle
        # divided (post hoc arithmetic on pre-specified means), and this table carries the same cell with its label (Edith, proof 3, p. 70)
        r = derive("challenger mean list cost per puzzle / comparator's", lambda a, b: a / b,
                   S.ref("main", join_key(*ITEM24.split("."), f"{ch} {sh}", "cost_per_puzzle", "mean")),
                   S.ref("main", join_key(*ITEM24.split("."), f"{cmp_} {sh}", "cost_per_puzzle", "mean")))
        return joined(num_d(r, dp=RATIO_DP), label("; cost ratio, " + T4_RATIO_TIER), sep="")
    if kk is None:
        return DASH
    rs = "reporting.group_b.item_8b.realised_spend"
    row = join_key(*rs.split("."), "tests", test, "by_row", "k+0")
    k_kj = S.get("main_k", f"k_from_rows.{'opus' if kk == 'O' else 'sonnet'}.{sh}.k")
    if (S.get("main", f"{row}.k") != k_kj or S.get("main", f"{rs}.tests.{test}.shape") != sh
            or not str(S.get("main", f"{rs}.priced")).startswith("list")):
        raise ValueError(f"{test}: item 8b's realised spend row is not the list-priced spend at k.json's k {k_kj}")
    return joined(label("spend share"), num(S.ref("main", f"{row}.haiku_over_comparator"), dp=3, bounds=(1.0,)), sep=" ")   # names the quantity as TAB-01 does


def _error_ratio(S: Store, test: str) -> List[Cell]:
    """R with its 95% interval; Test 1's is undefined (0 comparator errors), printed with the comparator's exact upper error rate."""
    e = f"reporting.error_ratios.{test}"
    if not S.get("main", f"{e}.defined"):
        return [text_of(S.ref("main", f"{e}.defined"), {False: "undefined"}),
                joined(label("comparator error rate at most "), pct(S.ref("main", f"{e}.comparator_error_rate_upper95"), dp=2),
                       label(" (exact 95%)"), sep="")]      # no % sign in a cell (§2.6): the unit is in the near-ceiling note
    lo, hi = ci_refs(S, "main", f"{e}.ci95")
    return [num(S.ref("main", f"{e}.R"), dp=2), interval(lo, hi, dp=2)]


def _line(*parts: Cell) -> List[Cell]:
    """A note or caption line as ONE cell, its parts joined with no separator (labels carry their own spaces), so no stray space
    lands before a semicolon or a closing bracket."""
    return [joined(*parts, sep="")]


def _near_ceiling_note(S: Store, where: str = "") -> List[Cell]:
    """The near-ceiling label in plain words, from Amendment 1's own text (Edith's Q17; TAB-02 and TAB-07). Amendment 1's item 6 reads
    '- Opus-medium's pooled whole-answer accuracy at n = 6 is 40 of 40 (1.00 ≥ 0.95): …' and '- So tests 1–2 are labelled near
    ceiling, and the paper reports the error-rate ratio (Haiku-vote errors ÷ Opus errors), with its' / 'interval, next to the
    non-inferiority result.' Every number is read from that line; refuse to build unless item 6 sits under Amendment 1 (the values the
    pre-set rules chose after the ladder, i.e. the length sweep), the stamped label is on beside Tests 1 and 2 (whose comparator is
    Opus-medium), and the stamped source sentence gives the same counts at the same length. `where` names the table that prints the
    error ratios when it is not this one."""
    amend = _one_line(S, "s1_spec", r"^### Amendment 1 \(.*\): the values the pre-set rules chose after the ladder$")
    head = _one_line(S, "s1_spec", r"^\*\*6\. The near-ceiling label: ON\.\*\*$")
    later = [n for n in S.find_lines("s1_spec", r"^##") if n > amend]
    if not (amend < head < later[0]):
        raise KeyMissing("spec: the near-ceiling item is not under Amendment 1")
    pat = r"^- Opus-medium's pooled whole-answer accuracy at n = (\d+) is (\d+) of (\d+) \((\d\.\d+) ≥ (\d\.\d+)\)"
    if _one_line(S, "s1_spec", pat) != head + 1:
        raise KeyMissing("spec: Amendment 1's near-ceiling accuracy line is not under item 6")
    so = _one_line(S, "s1_spec", r"^- So tests 1–2 are labelled near ceiling, and the paper reports the error-rate ratio \(Haiku-vote "
                                 r"errors ÷ Opus errors\), with its$")
    if so != head + 3 or S.get("s1_spec", f"L{so + 1}") != "interval, next to the non-inferiority result. The bias-table row is added.":
        raise KeyMissing("spec: Amendment 1's near-ceiling consequence is not as quoted")
    key = f"L{head + 1}"
    n, right, tries, share, bar = (re.match(pat, S.get("s1_spec", key)).group(i) for i in range(1, 6))
    i15 = "reporting.group_b.item_15"
    if (S.get("main", f"{i15}.source") != f"the ladder: Opus-medium {right} of {tries} at n = {n}" or int(n) != S.get("main", "n")
            or S.get("main", f"{i15}.beside_tests") != ["t1", "t2"] or S.get("main", f"{i15}.on") is not True
            or {STUDY1_TESTS[t][2] for t in ("t1", "t2")} != {"opus-med"} or not float(share) >= float(bar)):
        raise ValueError("the near-ceiling note no longer fits Amendment 1 or the stamped label")
    # the last clause: a labelled test whose comparator made no errors has no ratio, and TAB-02 gives the comparator's exact upper error
    # rate instead (refuse to build unless at least one labelled test is such a case, and every undefined ratio has zero comparator
    # errors and that bound)
    undefined = [t for t in S.get("main", f"{i15}.beside_tests") if not S.get("main", f"reporting.error_ratios.{t}.defined")]
    for t in undefined:
        e = f"reporting.error_ratios.{t}"
        if S.get("main", f"{e}.E_cmp") != 0 or not S.has("main", f"{e}.comparator_error_rate_upper95"):
            raise ValueError(f"{t}: an undefined error ratio without zero comparator errors and their exact upper rate")
    if not undefined:
        raise ValueError("no near-ceiling test has an undefined error ratio: drop the note's last clause")
    num_at = lambda g: _stamped_number_in(S, "s1_spec", key, pat, group=g)                                # noqa: E731
    pct_at = lambda g, dp: _stamped_share_pct(S, "s1_spec", key, pat, g, dp)                              # noqa: E731 (Edith, proof 5, B2-S6)
    return _line(label("Near ceiling (Amendment 1): a label that the pre-registration's Amendment 1 turned on for Tests 1 and 2 because "
                       "their comparator, Opus-medium, was right on "), num_at(2), label(" of "), num_at(3),
                 label(" answers in the length sweep at 6 steps, a pooled whole-answer accuracy of "), pct_at(4, 2),
                 label(", at or above the pre-set "), pct_at(5, 0),
                 label("; it marks a comparator at or near a perfect score. With it, the error-rate ratio (the challenger's errors over "
                       "Opus-medium's) is reported with its interval next to the no-worse-than reading" + where + "; where Opus-medium "
                       "made no errors the ratio is undefined, and its exact 95% upper error rate, in %, is given instead."))


def _error_ratio_tier(S: Store) -> None:
    """Edith's Q14: the error ratio is 'pre-specified descriptive, reported beside the test', never under 'confirmatory'. Refuse to
    build unless the reporting definitions (stamped before any result was opened) define it for each of the five tests and Amendment 1
    has it reported next to the non-inferiority result, and the result file stamps one for every test."""
    head = _one_line(S, "s1_defs", r"^## 1\. The error-rate ratio$")
    which = _one_line(S, "s1_defs", r"^\*\*Which tests\.\*\* Each of the five tests that ran \(k ≥ 1\), in the as_deployed view\.$")
    nxt = _one_line(S, "s1_defs", r"^## 2\. ")
    if not head < which < nxt or set(S.keys("main", "reporting.error_ratios")) != set(STUDY1_TESTS):
        raise ValueError("the error ratio's tier wording no longer fits the reporting definitions or the result file")
    _near_ceiling_note(S)              # its guards include Amendment 1's 'reports the error-rate ratio … next to the non-inferiority result'


ER_TIER = "pre-specified descriptive, reported beside the test"


def _test_accuracies(S: Store, t: str, dp: int = 2, bounds=()) -> List[Cell]:
    """Challenger and comparator accuracy (%) for a test, each followed by its format compliance (%), from stamped keys: the
    Haiku-medium vote at the test's own k from item 24's vote_at_own_k (Tests 1-3), item 24's accuracy_mean for the single-call arms
    and step voting; format compliance from confirmatory.format_compliance (step voting has none stamped: a dash). `dp` and `bounds`
    are the printing (the full table: 2 decimals; the paper's version: 1 decimal with the guard at 100, D-161)."""
    _, ch, cmp_, sh, kk = STUDY1_TESTS[t]
    if kk is not None:
        v = join_key("reporting", "group_b", "item_24", "table", f"{ch} {sh}", "vote_at_own_k", f"k_{kk}")
        k_kj = S.get("main_k", f"k_from_rows.{'opus' if kk == 'O' else 'sonnet'}.{sh}.k")
        if S.get("main", f"{v}.k") != k_kj:
            raise ValueError(f"{t}: item 24's vote k {S.get('main', f'{v}.k')} is not k.json's k {k_kj}")
        acc_ch = pct(S.ref("main", f"{v}.mean"), dp=dp, from_proportion=False, bounds=bounds)
    else:
        acc_ch = _acc24(S, ch, sh, dp=dp, bounds=bounds)
    out = [acc_ch]
    for arm in (ch, cmp_):
        fc = f"confirmatory.format_compliance.{arm}.{sh}.format_compliance"
        if S.has("main", fc):
            out.append(pct(S.ref("main", fc), dp=dp, bounds=bounds))
        elif S.get("main", join_key("reporting", "group_b", "item_24", "table", f"{arm} {sh}", "format_compliance")) is None:
            out.append(DASH)
        else:
            raise ValueError(f"{t}: {arm} {sh} has a format block in item 24 but none in confirmatory.format_compliance")
        if arm == ch:
            out.append(_acc24(S, cmp_, sh, dp=dp, bounds=bounds))
    return out


# ---------------------------------------------------------------- the paper's versions (D-159, D-160; D-161's one decimal)

# D-161's one name per term, in a paper version's headers, cells and notes (its caption is the full table's facts, which Vision writes
# the caption from): the retired names (spec rules 4 and 5: arm, try, base puzzle and its shorthand 'bases', equal-money in either
# spelling, the same-model check, tier, run window, three-way reading, as deployed) and the locked words that never print in a paper
# cell or note.
_RETIRED = re.compile(r"\b(?:non-inferior|declared|significant|try|tries|arms?|base puzzles?|bases?|equal[- ]money|three-way|as deployed"
                      r"|tiers?|run windows?|same[- ]model)\b", re.IGNORECASE)
# A claim's companions (spec rule 5): they belong in the caption, never in a paper version's notes.
_NOTE_ONLY = re.compile(r"\b(?:post hoc|exploratory|confirmatory|pre-specified|offline simulation)\b", re.IGNORECASE)


def _paper_check(t: Table) -> Table:
    """A paper version (D-160 house style, Edith's polish standard §7): at most 8 columns; at most 2 notes, each printed under the table
    (a short note) and at most 220 characters (two printed lines); no column with one value in every row; no retired name, internal id
    or internal record in its headers, cells or notes; no claim's companion (a tier label) in its notes."""
    t.check()
    if len(t.columns) > 8:
        raise ValueError(f"a paper version has {len(t.columns)} columns (at most 8)")
    if len(t.notes) > 2 or sorted(t.short_notes) != list(range(len(t.notes))):
        raise ValueError(f"a paper version prints only its notes, at most 2, all short ({len(t.notes)} notes, short {t.short_notes})")
    for n in t.notes:
        if len(" ".join(c.printed for c in n if c.printed)) > 220:
            raise ValueError(f"a paper version's note is longer than two printed lines: {' '.join(c.printed for c in n)!r}")
    for j, c in enumerate(t.columns):
        if len({r[j].printed for r in t.rows}) < 2:
            raise ValueError(f"column {c.printed!r} has one value in every row: move it to a note or the caption")
    texts = [c.printed for c in t.columns] + [c.printed for r in t.rows for c in r] + [c.printed for n in t.notes for c in n]
    bad = sorted({s for s in texts if _RETIRED.search(s) or MAIN_TEXT_ID.search(s) or BARRED.search(s)})
    if bad:
        raise ValueError(f"a paper version prints a retired name, an internal id or an internal record: {bad}")
    companions = sorted({c.printed for n in t.notes for c in n if _NOTE_ONLY.search(c.printed)})
    if companions:
        raise ValueError(f"a paper version's note carries a claim's companion (it belongs in the caption): {companions}")
    return t


def _t3_views() -> List[tuple]:
    """TAB-03's views other than the confirmatory one, as (its column name in TAB-03, its tests prefix): the view columns, then the
    cached re-pricing and the equal-token view. The superiority sign-flip p is a check against no difference, not a view at a margin,
    so it is not one of them."""
    views = [(name, p) for name, p, _m in _T3_VIEWS if p != VIEW] + [("Cached re-pricing", _T3_CACHED), ("Equal-token view", _T3_TOKEN)]
    if len(views) != len(_T3_VIEWS) + 1:
        raise ValueError("TAB-03's view columns no longer hold the confirmatory view once")
    return views


def _view_readings(S: Store, t: str) -> List[tuple]:
    """(TAB-03 column name, reading ref) for the confirmatory view (first, named None) and every other view of test t; a reading that is
    not one of Study 1's three refuses the build."""
    out = [(None, S.ref("main", f"{VIEW}.tests.{t}.reading"))] + [(n, S.ref("main", f"{p}.tests.{t}.reading")) for n, p in _t3_views()]
    known = set(_s1_reading(STUDY1_ARMS[STUDY1_TESTS[t][2]][0]))
    if any(r.value not in known for _, r in out):
        raise ValueError(f"{t}: a view's reading is not stamped as one of Study 1's: {[r.value for _, r in out]}")
    return out


def _views_agree(S: Store, t: str) -> Cell:
    """TAB-03's views of a test, as one cell of TAB-02's paper version: 'yes' when every view TAB-03 prints for the test (its view columns,
    the cached re-pricing and the equal-token view; not the sign-flip p), each read at its own stamped margin, stamps the same reading
    as the confirmatory view whose decision the Decision column prints, 'no' when any differs. Only the readings are compared, because
    they are what TAB-03 prints for each view (round 3: TAB-03 prints no Holm flag, and none of its views is a test). Every reading is a
    source of the cell."""
    rs = _view_readings(S, t)
    r0 = rs[0][1]
    return Cell(YES_NO[all(r.value == r0.value for _, r in rs[1:])], raw=[r.value for _, r in rs], refs=tuple(r for _, r in rs),
                formula="yes if every view's stamped reading (TAB-03's views but the sign-flip p, each at its own margin) equals the "
                        "confirmatory view's, else no")


# Study 1's tests in full (Vision's plan §3: TAB-02 merged with TAB-03's views; Edith-accepted), laid out for proof 2 (Edith's p. 27): two
# rows per test (the challenger's row above its comparator's, so each side's accuracy and format compliance are in their own rows, and
# d and the error-rate ratio each print their value above its interval for every test), a row group per test, and the decision in short
# words. TAB-03's views are the second line of the Decision cell ('views agree' or 'views differ'): a view is not a decision, and a
# column of its own would not fit the 6.5 in beside the others at 8 pt (the paper's tables have at most 8 columns, and words are never
# broken). The vote's size k is printed with the vote it sizes. Headers are short; the notes keep to two lines together.
# The last column's header carries the margin ("Decision (by > 10 points) and views", read from the margin's ref): the margin is the same
# in every row, so the cells keep the label's words ("worse"; "shown no worse" for Test 5, never cut: Edith's ruling on proof 3, A.21,
# D-161 condition 3), "shown no worse" held on one line (no-break spaces), so Test 5's cell takes two lines with its views line.
_TAB02_PAPER_COLS = ("Test", "Challenger vs comparator", "Accuracy (%)", "Format compliance (%)", "d (points) [95% interval]",
                     "Error-rate ratio [95% interval]")
# The paper's word for each shape (the same words Table 2 prints; the 1×6 / 6×1 codes are not defined in the paper).
_SHAPE_WORD = {"chain": "chains", "pieces": "pieces"}
_NBSP = "\u00a0"
# Two of the full table's notes, also given (without their full stops) to the paper version's caption facts.
_DEV1 = "Study 1's tests were pre-registered at 24 steps and run at 6 steps (Deviation 1)"
_SONNET_MEDIUM = "Sonnet ran at medium effort, one level below its default, in Tests 3 and 5"


def _tab02_paper_caption(S: Store, caption: Dict[str, List[Cell]]) -> Dict[str, List[Cell]]:
    """The paper version's caption facts: every fact of the full table's caption, unchanged (spec rule 5), plus what the merge and the
    cut need Vision to know (a superset, for Friday to accept; round 3). 'views': what the second line of the Decision cell ('views
    agree' or 'views differ') means and the tier of TAB-03's views (TAB-03's own caption tier, so a confirmatory table does not carry
    views of other tiers unlabelled). 'views_differ': for each test whose views differ, the views (by TAB-03's column names) that read
    differently and how they read. 'format': what the printed notes leave out because the caption carries it (a vote's format
    compliance is its samples', step voting's dash, one row per side). 'companions': the
    labels and caveats the full table's cells and notes tie to the tests this version prints, none of which it prints in a cell, so the
    caption states them: the near-ceiling label on Tests 1 and 2, Deviation 1, Sonnet at medium, and the original marking rule's changed
    reading (Deviation 2), in the full table's own words. 'full_table_only': the values the full caption's facts describe that this
    version does not print."""
    i15 = "reporting.group_b.item_15"
    if S.get("main", f"{i15}.beside_tests") != ["t1", "t2"] or S.get("main", f"{i15}.on") is not True:
        raise ValueError("the companions fact names Tests 1 and 2 as the near-ceiling tests")
    if {t for t, (_, ch, cmp_, _s, _k) in STUDY1_TESTS.items() if "sonnet-med" in (ch, cmp_)} != {"t3", "t5"}:
        raise ValueError("the companions fact names Tests 3 and 5 as the Sonnet-medium tests")
    if set(caption) != {"tier", "study", "set", "n", "interval", "price", "cap"}:
        raise ValueError(f"the full table's caption facts changed ({sorted(caption)}): check the 'full_table_only' fact")
    out = dict(caption)
    out["views"] = [label("Views (the second line of the Decision cell): 'views agree' if every view TAB-03 prints (all but the sign-flip p, "
                          "each read at its own margin) gives the same reading as the Decision, 'views differ' if one does not; TAB-03's "
                          + _T3_TIER + " (each view's label is in TAB-03's notes)")]
    # what the printed notes leave out because the caption carries it (the paper version's notes are two lines together)
    out["format"] = [label("format compliance: a vote's is that of its samples; step voting has none recorded (a dash in the table); "
                           "the table's accuracy and format compliance are one row per side, the challenger's above its comparator's")]
    # the views that differ, test by test, grouped by how they read (the cell says only 'no')
    differ: List[Cell] = []
    for t, (name, _ch, cmp_, _sh, _kk) in STUDY1_TESTS.items():
        rs = _view_readings(S, t)
        words = _s1_reading(STUDY1_ARMS[cmp_][0])
        odd = [(n, r) for n, r in rs[1:] if r.value != rs[0][1].value]
        if not odd:
            continue
        parts: List[Cell] = [label(("; " if differ else "") + f"{name} (views differ) reads ")]
        for i, val in enumerate(dict.fromkeys(r.value for _, r in odd)):
            names = [n + (" (the sensitivity check Deviation 2 kept)" if n == "Original marking rule" else "")
                     for n, r in odd if r.value == val]
            parts += [label(", " if i else ""), text_of(next(r for _, r in odd if r.value == val), words),
                      label(" in TAB-03's " + ("views " + ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1
                                               else "view " + names[0]))]
        parts += [label(" instead of "), text_of(rs[0][1], words), label("; every other view reads as its Decision")]
        differ += parts
    if not differ:
        raise ValueError("no test has a view that differs: drop the 'views_differ' fact")
    out["views_differ"] = _line(*differ)
    # the Decision column's words (proof 3, A.21): the margin moved to the header, so the caption says what the two words stand for
    margin = S.ref("main", f"{VIEW}.margin")
    out["decision"] = _line(label("Decision cells: 'worse' is a reading of worse by more than the margin from the pre-registered decision rule on "
                                  "the unadjusted interval (Tests 1–4); 'shown no worse' is shown no worse by more than the margin, Holm-adjusted (Test 5); "
                                  "the margin is "), _margin_size(margin), label(" points and is in the column header"))
    # Deviation 2's changed reading, as the full table's note gives it (only the tests whose reading changes)
    dev2: List[Cell] = []
    for t in ("t3", "t5"):
        o, c = S.ref("main", f"secondary.original_repeat_rule.tests.{t}.reading"), S.ref("main", f"{VIEW}.tests.{t}.reading")
        if o.value != c.value:
            words = _s1_reading(STUDY1_ARMS[STUDY1_TESTS[t][2]][0])
            dev2 += [label(("; " if dev2 else "") + f"{STUDY1_TESTS[t][0]} would read "), text_of(o, words), label(" instead of "),
                     text_of(c, words)]
    if not dev2:
        raise ValueError("no test's reading changes under the original marking rule: drop that companion")
    out["companions"] = _line(label("to state in the caption (this version prints none of them in a cell): the label "),
                              text_of(S.ref("main", f"{i15}.label")),
                              label(" on Tests 1 and 2 (defined in the supplement's full table); " + _DEV1 + "; " + _SONNET_MEDIUM
                                    + "; under the original pre-registered marking rule, which Deviation 2 kept as a sensitivity check, "),
                              *dev2)
    out["full_table_only"] = [label("printed in the supplement's full table only: the spend shares and cost ratios (the 'price' fact), raw k and "
                                    "the cap (the 'cap' fact: the cap is in the full table's note), the p-values and Holm thresholds, the tie-decided share, the near-ceiling label's column "
                                    "and its definition, the original marking rule's scores and d, and Test 1's exact upper bound on its "
                                    "comparator's error rate (the 'interval' fact's last clause)")]
    return out


def _margin_size(margin: Ref) -> Cell:
    """The margin's size in points (10), read from its ref."""
    return num_d(derive("the margin's size", lambda x: abs(x), margin), dp=0)


def _decision_words(reading: Ref, declared: Ref, margin: Ref) -> Cell:
    """A Study 1 test's decision in the paper's short words (Edith, proof 2: the qualifier moves to the note): 'worse' for a reading of
    worse by more than the margin that is not Holm-adjusted (the pre-registered rule on the unadjusted interval), 'shown no worse' for a
    Holm-adjusted one 'shown no worse' ('(Holm-adjusted)' is in the note). The margin ('by > 10 points') is in the column header (proof 3,
    A.21), read from the same ref, which stays a source of the cell; any other reading and flag refuses the build."""
    r, d = reading.value, declared.value
    if d is True and r == "non-inferior":
        words = f"shown{_NBSP}no{_NBSP}worse"                   # the ruled label, whole and on one line
    elif d is False and str(r).startswith("worse"):
        words = "worse"
    else:
        raise ValueError(f"TAB-02: no decision words for reading {r!r}, Holm-adjusted {d!r}")
    return Cell(words, raw=[r, d], refs=(reading, declared, margin),
                formula="the stamped reading and Holm flag in the Method legend's words; the margin (by more than its size in points) is in "
                        "the column header and the qualifier (pre-registered rule, Holm-adjusted) in the note")


def _ratio_two_cells(S: Store, e: str) -> List[Cell]:
    """An error-rate ratio over two lines, the same for every test (Edith, proof 2, p. 27): the ratio (one decimal) above and its 95%
    interval below; an undefined ratio (the comparator made no errors) says so above and gives the comparator's error count below, as
    Table 2 (TAB-01.main) prints them from the same refs."""
    if not S.get("main", f"{e}.defined"):
        return [text_of(S.ref("main", f"{e}.defined"), {False: "undefined"}),
                joined(label("(comparator errors "), integer(S.ref("main", f"{e}.E_cmp")), label(" of "), integer(S.ref("main", f"{e}.n")),
                       label(")"), sep="")]
    return [num(S.ref("main", f"{e}.R"), dp=1), interval(*ci_refs(S, "main", f"{e}.ci95"), dp=1)]


def _views_words(S: Store, t: str) -> Cell:
    """TAB-03's views of a test as the Decision cell's second line: 'views agree' when every view gives the test's decision (the
    'Views agree' column's yes of the full table), 'views differ' when one does not (its no). The refs are the full table's."""
    c = _views_agree(S, t)
    return Cell({"yes": "views agree", "no": "views differ"}[c.printed], raw=c.raw, refs=c.refs,
                formula="views agree if every view TAB-03 prints (all but the sign-flip p, each at its own margin) stamps the confirmatory "
                        "view's reading, else views differ")


def _tab02_paper(S: Store, caption: Dict[str, List[Cell]]) -> Table:
    """TAB-02's paper version (D-160, D-161; Edith's proof 2): Tests 1–5, two rows per test, the challenger's row above its comparator's
    ('vs Opus-medium, pieces', the shape in the paper's words): each side's accuracy and format compliance on its own row, d with its
    95% interval and the error-rate ratio with its interval one under the other (one decimal), then the decision in short words (its
    qualifier is in the note) and under it whether TAB-03's views agree. Every value is read from the refs the full
    table (or TAB-03) prints, except Test 1's ratio cell, which prints its comparator's error count over its puzzles as Table 2
    (TAB-01.main) prints them from the same refs; d and the decision are printed as Table 2 prints them. TAB-03 has no paper version
    (supplement only). Each test is a row group (a little space above it)."""
    if _T3_VIEWS[0][1] != VIEW:
        raise ValueError("TAB-03's first view is not the confirmatory one this table's d and decision are read from")
    m = S.ref("main", f"{VIEW}.margin")
    # the note says Test 5 is Holm-adjusted and Tests 1–4 are read by the pre-registered rule: refuse unless the flags say so
    if {t for t in STUDY1_TESTS if S.get("main", f"{VIEW}.tests.{t}.declared")} != {"t5"}:
        raise ValueError("the note names Test 5 as the only Holm-adjusted test")
    rows, starts = [], []
    for t, (name, ch, cmp_, sh, kk) in STUDY1_TESTS.items():
        tk = f"{VIEW}.tests.{t}"
        what = f"{_challenger(t)} vs {_arm_name(cmp_)}, {shape(sh)}"
        if what != _s1_what(t):
            raise ValueError(f"{name}: this table names the comparison {what!r}, Table 2 (TAB-01) {_s1_what(t)!r}")
        # the vote's k after the vote's name (the full table's k cell); Tests 4 and 5 have no vote, so no k
        if (kk is None) != (_k_cells(S, t)[0] is DASH) or (kk is not None) != (_challenger(t) == "Haiku-medium vote"):
            raise ValueError(f"{name}: k is printed after 'Haiku-medium vote', for the vote tests only")
        # a vote's name and its k stay on one line (no-break spaces, which the writer prints as '~')
        challenger = (joined(label(f"{_challenger(t).replace(' ', _NBSP)},{_NBSP}k{_NBSP}={_NBSP}"), _k_cells(S, t)[0], sep="")
                      if kk is not None else label(_challenger(t)))
        acc_ch, fc_ch, acc_cmp, fc_cmp = _test_accuracies(S, t, dp=1, bounds=(100.0,))
        if (fc_ch is DASH) != (ch == "e3") or fc_cmp is DASH:
            raise ValueError(f"{name}: the 'format' caption fact says only step voting has no format compliance")
        lo, hi = ci_refs(S, "main", f"{tk}.ci95")
        ratio_top, ratio_below = _ratio_two_cells(S, f"reporting.error_ratios.{t}")
        starts.append(len(rows))
        rows.append([label(name), challenger, acc_ch, fc_ch, pts(S.ref("main", f"{tk}.d"), dp=1, margin=float(m.value)), ratio_top,
                     _decision_words(S.ref("main", f"{tk}.reading"), S.ref("main", f"{tk}.declared"), m)])
        rows.append([EMPTY, label(f"vs {_arm_name(cmp_)}, {_SHAPE_WORD[shape_word(sh)]}"), acc_cmp, fc_cmp,
                     interval(lo, hi, dp=1, signed=False, bounds=(0.0, float(m.value))), ratio_below, _views_words(S, t)])
    # 'unbounded' prints only as an error-rate ratio's upper end (column 5, the interval's row); 'undefined' prints only above it,
    # with the comparator's zero errors below it (as Table 2 prints them)
    if (not any(c.printed.endswith(", unbounded]") for c in [r[5] for r in rows])
            or any("unbounded" in c.printed for r in rows for j, c in enumerate(r) if j != 5)):
        raise ValueError("the note says the error-rate ratio is unbounded above in some draws: it must print there, and only there")
    if (any("undefined" in c.printed and (j != 5 or c.printed != "undefined") for r in rows for j, c in enumerate(r))
            or any(c.printed.startswith("(comparator errors") and not c.printed.startswith("(comparator errors 0 of ")
                   for r in rows for c in r)):
        raise ValueError("'undefined' prints only as an error-rate ratio, with its comparator's zero errors below it")
    # the notes (two lines together, Edith §7.5): the decisions' qualifiers, the one caveat of the ratio, and the views line; d's and
    # the ratio's definitions are in the Method legend, and a vote's format compliance, step voting's dash and the views' definition
    # (each at its own margin) are in the caption facts. The views line points to TAB-03, which prints in the paper as "Table S16 in the
    # supplement" when TAB-03 is not placed there (the longest form a pointer takes): the two notes are typeset with that form (Edith's
    # proof 2 checker) and take two lines with room to spare (they take three with the older "same decision in every TAB-03 view").
    notes = [[label("Decision: Tests 1–4 by the pre-registered rule, Test 5 shown no worse (Holm-adjusted). " + UNBOUNDED_NOTE)],
             [label("Views agree: each view in TAB-03 gives the Decision's reading.")]]
    cols = [label(c) for c in _TAB02_PAPER_COLS] + [joined(label(f"Decision (by{_NBSP}>{_NBSP}"), _margin_size(m), label(f"{_NBSP}points) and views"), sep="")]
    t = Table(cols, rows, notes, _tab02_paper_caption(S, caption), short_notes=[0, 1], layout="float", font="footnotesize")
    # the caption fact quotes the Decision cells' words: each word the cells print is quoted there, and nothing else (Edith, PR #38, MUST 1)
    printed = {r[-1].printed.replace(_NBSP, " ") for r in rows if r[-1].printed and r[-1].printed not in ("views agree", "views differ")
               and not r[-1].printed.startswith("views ")}
    quoted = set(re.findall(r"'([^']+)' is ", " ".join(c.printed for c in t.caption["decision"])))
    if not printed or printed != quoted:
        raise ValueError(f"TAB-02.main: the caption fact quotes {sorted(quoted)}, the Decision cells print {sorted(printed)}")
    t.groups = starts[1:]
    return _paper_check(t)


# PLAN NOTE (TAB-02): the plan says 'declared (Test 5 only)'. Only Test 5 is declared; the column prints the stamped declared field for every
# test ('no' for Tests 1-4, which are in the Holm family and were not declared), so the reader sees that Tests 1-4 were tested under Holm and
# not declared. The paper's version (`_tab02_paper`, D-160) prints the decision's short words ('worse', 'shown no worse'; the margin is in the column
# header, proof 3) instead, and merges in TAB-03's views.
@output("TAB-02")
@main_text
def tab_02(S: Store) -> Table:
    # Column titles 'p (one-sided)' and 'Near-ceiling label' say what they hold (the one-sided test's p; the near-ceiling label).
    cols = ["Test", "Shape", "Challenger", "Comparator", "k", "Raw k", "Spend share or cost ratio (challenger / comparator)",
            "Challenger accuracy (%)", "Challenger format compliance (%)", "Comparator accuracy (%)", "Comparator format compliance (%)",
            "d (points)", "95% interval", "p (one-sided)", "Holm threshold", "Shown no worse (Holm-adjusted)",
            "Reading (pre-registered decision rule)", "Error-rate ratio", "Error-rate ratio 95% interval", "Tie-decided share (%)", "Near-ceiling label"]
    rows, caps = [], []
    for t, (name, ch, cmp_, sh, kk) in STUDY1_TESTS.items():
        tk = f"{VIEW}.tests.{t}"
        lo, hi = ci_refs(S, "main", f"{tk}.ci95")
        declared = text_of(S.ref("main", f"{tk}.declared"), YES_NO)
        # Edith's ruling C: the Holm-adjusted result reads 'shown no worse ... (Holm-adjusted)'; the others keep the decision rule's
        # unadjusted words. Only a declared test may read non-inferior (a non-inferior reading that Holm did not pass would need
        # 'not Holm-adjusted' wording): refuse to build otherwise.
        reading = S.ref("main", f"{tk}.reading")
        if S.get("main", f"{tk}.declared") != (reading.value == "non-inferior"):
            raise ValueError(f"{name}: declared {S.get('main', f'{tk}.declared')} but reading {reading.value!r}: reword the reading cell")
        words = _s1_reading(STUDY1_ARMS[cmp_][0])
        if S.get("main", f"{tk}.declared"):
            words = {**words, "non-inferior": words["non-inferior"] + " (Holm-adjusted)"}
        k_cells = _k_cells(S, t)
        if kk is not None:
            caps.append(k_cells[2])
        tie = pct(S.ref("main", f"ties.tie_decided_share.{t}"), dp=2) if S.has("main", f"ties.tie_decided_share.{t}") else DASH
        near = (text_of(S.ref("main", "reporting.group_b.item_15.label"))
                if t in S.get("main", "reporting.group_b.item_15.beside_tests") else DASH)           # a dash where there is no label (as the neighbours print)
        rows.append([label(name), label(shape(sh)), label(_challenger(t)), label(_arm_name(cmp_)),
                     *k_cells[:2], _spend_ratio(S, t), *_test_accuracies(S, t),
                     pts(S.ref("main", f"{tk}.d"), margin=MARGIN), interval(lo, hi, dp=2, signed=True, bounds=(0.0, MARGIN)),
                     pvalue_bound(S.ref("main", f"{tk}.p"), S.ref("main", f"{tk}.z0"), S.ref("main", f"{tk}.a"), S.ref("main", f"{VIEW}.B"), dp=5),
                     exact(S.ref("main", f"{VIEW}.holm_thresholds.{t}")), declared,
                     text_of(reading, words), *_error_ratio(S, t), tie, near])
    # The companions the style sheet ties to Tests 1-5 (Deviation 1; Sonnet below its default) and the original-rule line for Tests 3
    # and 5, worded as Edith's ruling E-09 gives it: Deviation 2 kept the original rule as a sensitivity check (not a secondary view).
    sonnet_tests = {t for t, (_, ch, cmp_, _s, _k) in STUDY1_TESTS.items() if "sonnet-med" in (ch, cmp_)}
    if sonnet_tests != {"t3", "t5"}:
        raise ValueError(f"Sonnet-medium tests are {sorted(sonnet_tests)}, the note names Tests 3 and 5")
    notes = [_line(label(_DEV1 + ".")), _line(label(_SONNET_MEDIUM + "."))]
    # Edith's E-09 sentence also gives Sonnet-medium's chain score under the original rule, which is why Test 3's reading flips. The
    # secondary rates block is the chain shape's: refuse to build unless its official score is item 24's Sonnet-medium 1x6 accuracy.
    rs = "secondary.rates.sonnet-med"
    if (STUDY1_TESTS["t3"][2:4] != ("sonnet-med", "1x6") or STUDY1_TESTS["t5"][2:4] != ("sonnet-med", "1x6")
            or abs(100 * S.get("main", f"{rs}.official_acc") - S.get("main", f"{ITEM24}.sonnet-med 1x6.accuracy_mean")) > 1e-9):
        raise ValueError("the original-rule note assumes Tests 3 and 5 compare with Sonnet-medium on chains, and secondary.rates is the chain score")
    for i, t in enumerate(("t3", "t5")):
        o = f"secondary.original_repeat_rule.tests.{t}"
        lo, hi = ci_refs(S, "main", f"{o}.ci95")
        name = STUDY1_TESTS[t][0]
        # the readings in the paper's words, as the table's reading column prints them (Edith's N-3: not the bare stamped 'non-inferior')
        words = _s1_reading(STUDY1_ARMS[STUDY1_TESTS[t][2]][0])
        lead = ([label("Under the original pre-registered marking rule, which Deviation 2 kept as a sensitivity check, Sonnet-medium's chain "
                       "score is "), pct(S.ref("main", f"{rs}.original_acc"), dp=2), label("% instead of "),
                 pct(S.ref("main", f"{rs}.official_acc"), dp=2), label("%, and ")] if i == 0
                else [label("Under the same rule, ")])
        if S.get("main", f"{o}.reading") != S.get("main", f"{VIEW}.tests.{t}.reading"):
            verdict = [*lead, label(f"{name} would read "), text_of(S.ref("main", f"{o}.reading"), words), label(" instead of "),
                       text_of(S.ref("main", f"{VIEW}.tests.{t}.reading"), words)]
        else:
            verdict = [*lead, label(f"{name}'s reading is unchanged: "), text_of(S.ref("main", f"{o}.reading"), words)]
        notes.append(_line(*verdict, label(" (d = "), pts(S.ref("main", f"{o}.d"), margin=MARGIN), label(" points, 95% interval "),
                           interval(lo, hi, dp=2, bounds=(0.0, MARGIN)), label(").")))
    # The columns a reader cannot decode from their titles alone (definitions: harness/analysis/kscript.py, five_tests.tie_report,
    # reporting definitions item 1 for the error ratio).
    _error_ratio_tier(S)
    # the cap is the same for every vote (a column of one value and dashes would be a constant column): it is given here, with its refs
    notes.append(_line(label("Columns. k is the number of Haiku-medium samples in the vote; raw k is the cost-matched k before the cap (the "
                             "comparator's mean cost per puzzle over Haiku-medium's mean cost per sample, rounded down); the cap is the most "
                             "samples a vote may use, "), _same_in_every_row(caps),
                       label(" for every vote. p (one-sided) is the bootstrap p of the one-sided test of d against the margin (the "
                             "no-worse-than reading); the Holm threshold is the level that Holm's order sets for that test. The error-rate ratio "
                             "is the challenger's errors over the comparator's, counted over the puzzles "
                             "(for a vote, its expected errors); it is " + ER_TIER + ", not part of its reading. The tie-decided share is "
                             "the mean over puzzles of the share of the vote's draws of k samples in which a tie that included the right "
                             "answer decided the credit.")))
    notes.append(_near_ceiling_note(S))
    notes.append(_line(label("Format compliance is the share of samples in the required answer format; for Tests 1–3 it is that of the "
                             "Haiku-medium samples the vote is drawn from. No format-compliance figure is stamped for step voting "
                             "(Test 4's challenger), so that cell is a dash.")))
    caption = {"tier": [label("Tests 1–5 confirmatory: Test 5 shown no worse (Holm-adjusted across Study 1's tests); Tests 1–4 read by "
                              "the pre-registered decision rule on unadjusted intervals; error-rate ratios " + ER_TIER + "; spend shares and cost "
                              "ratios not tested (descriptive, except Test 4's cost ratio, which is " + T4_RATIO_TIER.replace(", not tested", "")
                              + ", and Test 5's, which is exploratory)")],
               "study": [label("Study 1, main run, 6 steps")],
               "set": _set_cells(S),
               "n": _tab02_n(S),
               "interval": _line(label("d: paired BCa bootstrap, 95%, B = "), integer(S.ref("main", f"{VIEW}.B")), label(", margin "),
                                 num(S.ref("main", f"{VIEW}.margin"), dp=0, signed=True),
                                 label(" points; error-rate ratio: paired percentile bootstrap over puzzles, 95% (replicates not stamped); "
                                       "Test 1's undefined ratio: the comparator's "),
                                 text_of(S.ref("main", "reporting.error_ratios.t1.comparator_interval"),
                                         {"clopper-pearson": "exact (Clopper–Pearson)"}),
                                 label(" upper bound on its error rate")),
               "price": _line(text_of(S.ref("main", "reporting.group_b.item_8b.realised_spend.priced"), {"list (item 9a)": "list price"}),
                              label(": the spend share is the vote's realised list spend over the comparator's at the test's k; Test "
                                    "4's cost ratio is step voting's mean list cost per puzzle over Opus-medium's; Test "
                                    "5's cost ratio is Opus-low's list cost per answer over Sonnet-medium's")),
               # the cap is in the note, not a column (the columns k and raw k are): the caption says so (Edith, proof 3, p. 70)
               "cap": _line(label("the vote's size k and its raw k (the cost-matched k before the cap) are columns; the cap on k, "),
                            _same_in_every_row(caps), label(" samples, is the same for every vote, so it is given in the note and is not a column"))}
    if [t for t in STUDY1_TESTS if not S.get("main", f"reporting.error_ratios.{t}.defined")] != ["t1"]:
        raise ValueError("the interval caption names Test 1 as the only undefined error ratio")
    t = Table([label(c) for c in cols], rows, notes, caption)
    t.main_table = _tab02_paper(S, caption)
    # supplement layout: 22 columns are wider than a landscape page even at their minimum widths, so four portrait parts (the test and its
    # vote; accuracy and format compliance; the difference and the pre-registered decision rule; the error-rate ratio, the tie-decided share and the near-ceiling label)
    _split(t, [["Shape", "Challenger", "Comparator", "k", "Raw k", "Spend share or cost ratio (challenger / comparator)"],
               ["Challenger", "Comparator", "Challenger accuracy (%)", "Challenger format compliance (%)", "Comparator accuracy (%)",
                "Comparator format compliance (%)"],
               ["d (points)", "95% interval", "p (one-sided)", "Holm threshold", "Shown no worse (Holm-adjusted)",
                "Reading (pre-registered decision rule)"],
               ["Error-rate ratio", "Error-rate ratio 95% interval", "Tie-decided share (%)", "Near-ceiling label"]], key=["Test"])
    return t


def _tab02_n(S: Store) -> List[Cell]:
    """Base puzzles per test and tries per base puzzle and shape: Haiku-medium's samples drawn (k.json, the same for Tests 1-3 and equal
    to item 24's tries over base puzzles), one try for the single-call arms (item 24's tries over base puzzles), step voting's calls."""
    drawn = {S.get("main_k", f"k_from_rows.{'opus' if kk == 'O' else 'sonnet'}.{sh}.samples_drawn")
             for t, (_n, ch, _c, sh, kk) in STUDY1_TESTS.items() if kk is not None}
    for sh in SHAPES:
        hm = join_key("reporting", "group_b", "item_24", "table", f"haiku-med {sh}")
        if {S.get("main", f"{hm}.refusals_and_truncations.tries") / S.get("main", f"{hm}.base_puzzles")} != drawn:
            raise ValueError(f"Haiku-medium {sh}: item 24's tries per base puzzle differ from k.json's samples drawn {drawn}")
    one = [f"{a} {s_}" for t, (_n, ch, c, s_, kk) in STUDY1_TESTS.items() for a in (ch, c) if a not in ("haiku-med", "e3")]
    for k24 in one:
        b = join_key("reporting", "group_b", "item_24", "table", k24)
        if S.get("main", f"{b}.refusals_and_truncations.tries") != S.get("main", f"{b}.base_puzzles"):
            raise ValueError(f"{k24} is not a one-try arm")
    b0 = join_key("reporting", "group_b", "item_24", "table", one[0])
    one_try = num_d(derive("tries / base_puzzles", lambda a, c: a / c, S.ref("main", f"{b0}.refusals_and_truncations.tries"),
                           S.ref("main", f"{b0}.base_puzzles")), dp=0)
    names = sorted({_arm_name(k.split(" ")[0]) for k in one})
    e3 = join_key("reporting", "group_b", "item_24", "table", "e3 1x6", "refusals_and_truncations", "calls_made")
    return _line(label("puzzles per test: "), integer(S.ref("main", f"{VIEW}.tests.t1.n")),
                 label("; samples per puzzle and shape: Haiku-medium "), integer(S.ref("main_k", "k_from_rows.opus.6x1.samples_drawn")),
                 label(" drawn (each vote uses its k of them), " + ", ".join(names[:-1]) + " and " + names[-1] + " "), one_try,
                 label("; step voting made "), integer(S.ref("main", e3)), label(" calls in all on the chains"))


# ================================================================ shared helpers for TAB-03 .. TAB-09

SHAPES = ("1x6", "6x1")
# Study 1's arms in reading order (Haiku settings, step voting, Opus, Sonnet); the files' own key order is alphabetical.
ARM_ORDER = ("haiku-thinking-off", "haiku-low", "haiku-med", "haiku-max", "e3", "opus-low", "opus-med", "sonnet-low", "sonnet-med")
ITEM24 = "reporting.group_b.item_24.table"
ITEM10 = "reporting.group_b.item_10.arms"


def _get(S: Store, source: str, key: str):
    """The raw value at a key, or None when the key is absent (structure only; printed numbers go through `ref`)."""
    try:
        return S.get(source, key)
    except KeyMissing:
        return None


def _arm_label(arm: str) -> Cell:
    return label(_arm_name(arm))


def _shape_cell(sh: str) -> Cell:
    return label(shape(sh))


def _usd_interval(lo: Ref, hi: Ref, sf: int = 3) -> Cell:
    """'[lo, hi]' in US dollars to `sf` significant figures; no '+' on a positive end (Edith §2.4: "[−0.0072, 0.0049]"); a stamped
    'unbounded' end is printed as such."""
    parts = []
    for r in (lo, hi):
        if isinstance(r.value, str) and not _NUM_RE.match(r.value):
            if r.value != "unbounded":
                raise TypeError(f"{r.source}:{r.key} = {r.value!r}")
            parts.append("unbounded")
        else:
            parts.append(fmt_sf(dec(_need_num(r)), sf))
    return Cell(f"[{parts[0]}, {parts[1]}]", raw=[lo.value, hi.value], refs=(lo, hi))


def _usd_end(r: Ref, sf: int = 3) -> Cell:
    """One end of a dollar interval, printed in a column of its own (the writer decimal-aligns the column): `sf` significant figures,
    no '+' on a positive end (Edith §2.4), a stamped 'unbounded' end printed as such. TAB-08's cost-difference interval uses it, as
    TAB-04's cost-per-correct interval uses usd() twice (Edith §2.8: a dollar column is never plainly right-aligned)."""
    if isinstance(r.value, str) and not _NUM_RE.match(r.value):
        if r.value != "unbounded":
            raise TypeError(f"{r.source}:{r.key} = {r.value!r}")
        return Cell("unbounded", raw=r.value, refs=(r,))
    return usd(r, sf)


_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?(?:/\d+)?$")


def _sig_figs(printed: str) -> int:
    """The significant figures of a printed decimal ('−0.000822' has 3, '0.0310' has 3, '+1.50' has 3)."""
    return len(re.sub(r"^[−+]?[0.]*", "", printed).replace(".", ""))


def _usd_signed(r: Ref, sf: int = 3) -> Cell:
    """A signed difference in US dollars to `sf` significant figures (D-161 rule 2), with '+' on a positive one and a true minus on a
    negative one; refuses a zero (it has no significant figure) or a value whose rounding gains a digit (0.009996 to 0.0100)."""
    v = _need_num(r)
    d = dec(v)
    if d == 0:
        raise ValueError(f"{r.source}:{r.key} is zero: no significant figures to print")
    dp = max(sf - 1 - d.adjusted(), 0)
    out = fmt_fixed(d, dp, signed=True)
    if _sig_figs(out) != sf:
        raise ValueError(f"{r.source}:{r.key} = {v!r} prints as {out!r}, not {sf} significant figures")
    return Cell(out, raw=r.value, refs=(r,))           # no formula: a plain rounding, as usd() records it


def _ci_or_dash(S: Store, source: str, key: str, **kw) -> Cell:
    """A 95% interval cell from a stamped 2-list; a dash when the key is absent or the ends are null (e.g. an undefined correlation)."""
    v = _get(S, source, key)
    if v is None or any(x is None for x in v):
        return DASH
    lo, hi = ci_refs(S, source, key)
    return interval(lo, hi, **kw)


def _reading_cell(d: Cell, ci: Cell, reading: Cell) -> Cell:
    """'d [lo, hi] (reading)' as one cell, every part keeping its refs."""
    return joined(d, ci, joined(label("("), reading, label(")"), sep=""))


def _key_cell(source: str, entry_key: str, name: str, as_int: bool = False) -> Cell:
    """A name that is itself a dict key in a file (a bin '[0,10)', a cascade size '5'), printed as stamped. `entry_key` is the key of
    that dict entry (it resolves, so the key's presence can be checked); the printed text is the entry's own name."""
    val: object = int(name) if as_int else name
    return Cell(str(name), raw=val, refs=(Ref(val, source, entry_key),), formula="the name of this dict entry")


def _pct_text(r: Ref) -> Cell:
    """A markdown table cell such as '79.2%' printed without its '%' (the column name carries the unit)."""
    v = r.value
    if not (isinstance(v, str) and re.fullmatch(r"\d+(?:\.\d+)?%", v)):
        raise TypeError(f"{r.source}:{r.key} = {v!r} is not a percentage cell")
    return Cell(v[:-1], raw=v, refs=(r,), formula="strip the trailing %")


def _share_pts(r: Ref, dp: int = 1, signed: bool = False, bounds=()) -> Cell:
    """A share (0-1) or a difference of shares printed in points."""
    return num(r, dp=dp, signed=signed, scale=100.0, bounds=bounds)


def _level_from_key(source: str, key: str) -> Cell:
    """The interval level named in a stamped key such as '...ci90' or '...difference_ci95', printed '90' (the column's header gives the
    unit, %); Flag R's intervals carry no separate level field."""
    last = key.split(".")[-1]
    m = re.search(r"(?:^|_)ci(\d+)$", last)
    if not m:
        raise ValueError(f"{key} does not name a level")
    return Cell(m.group(1), raw=last, refs=(Ref(last, source, key),), formula="digits of the interval key's name")


def _idx(t: Table, *titles: str) -> List[int]:
    """The indexes of the columns with these printed titles (each title must name exactly one column)."""
    names = [c.printed for c in t.columns]
    for n in titles:
        if names.count(n) != 1:
            raise KeyError(f"column {n!r} is not exactly once in {names}")
    return [names.index(n) for n in titles]


def _split(t: Table, parts: Sequence[object], key: Sequence[str], landscape: bool = False, font: Optional[str] = None) -> None:
    """Lay a table out as a split (the supplement's layout for a table too wide for a page even at its columns' minimum widths): each
    part holds the key columns and its own columns, named by their printed titles (a part is a list of titles, or a pair of row
    indexes and titles to print only those rows). The parts keep related columns together (split_columns proposes a greedy cut; this
    is the reading order's). Nothing may be left out: the build refuses unless every cell of the table is in a part, except a dash or
    an empty cell, which a part with fewer rows or columns may leave out."""
    t.layout = "split landscape" if landscape else "split"
    t.font = font
    t.split_key = _idx(t, *key)
    t.split_parts = [((None, _idx(t, *p)) if isinstance(p, list) else (list(p[0]), _idx(t, *p[1]))) for p in parts]
    for i, r in enumerate(t.rows):
        for j, c in enumerate(r):
            shown = j in t.split_key or any(j in cols and (rows is None or i in rows) for rows, cols in t.split_parts)
            if not shown and c.printed not in DASHES:
                raise ValueError(f"row {i + 1}, column {t.columns[j].printed!r} ({c.printed!r}) is in no part of the split")


def _groups(t: Table, block) -> None:
    """Row groups (Edith's §7.7): a little space above each row whose `block(row)` differs from the row before it."""
    t.groups = [i for i in range(1, len(t.rows)) if block(t.rows[i]) != block(t.rows[i - 1])]


def _stamped_in_quotes(r: Ref, lead: str = "", tail: str = ".") -> List[Cell]:
    """A stamped text of a frozen source (a locked result file or ledger) that holds a retired term, printed verbatim in quotation marks
    (D-161, Edith's ruling): `lead`, the text, then `tail`, as ONE cell so no space lands inside the quotes. A quotation mark inside
    the stamped text becomes a single one (a quotation within a quotation)."""
    if not isinstance(r.value, str):
        raise TypeError(f"{r.source}:{r.key} is {r.value!r}, not a stamped text")
    return [Cell(lead + "\"" + r.value.replace("\"", "'") + "\"" + tail, raw=r.value, refs=(r,),
                 formula="the stamped text, verbatim in quotation marks (a quotation mark inside it as a single one)")]


def _same_in_every_row(cells: List[Cell]) -> Cell:
    """The one value a column would print in every row (the polish standard's constant-column rule, §7.3: it moves to a note). The cell
    keeps every row's refs; the build refuses a column whose rows do not all print the same."""
    if len({c.printed for c in cells}) != 1:
        raise ValueError(f"the column is not constant: {sorted({c.printed for c in cells})}")
    return Cell(cells[0].printed, raw=[c.raw for c in cells], refs=tuple(r for c in cells for r in c.refs),
                formula="the value every row of the table prints (the build refuses a column that is not constant)")


def _caption(tier: str, study: str, n: List[Cell], interval_cells: List[Cell], price: List[Cell],
             set_: List[Cell] = None) -> Dict[str, List[Cell]]:
    out = {"tier": [label(tier)], "study": [label(study)], "n": n, "interval": interval_cells, "price": price}
    if set_ is not None:
        out["set"] = set_
    return out


# ================================================================ TAB-03

# (column name, tests prefix, key of the view's margin). Each view holds tests.t1-t5 with d, ci95, reading.
_T3_VIEWS = (
    ("As deployed", VIEW, f"{VIEW}.margin"),
    ("Refusals out", "confirmatory.views.refusals_out", "confirmatory.views.refusals_out.margin"),
    ("Truncations out", "confirmatory.views.truncations_out", "confirmatory.views.truncations_out.margin"),
    ("Final answer", "secondary.final_answer", "secondary.final_answer.margin"),
    ("Copy slips forgiven", "secondary.copy_slips_forgiven", "secondary.copy_slips_forgiven.margin"),
    ("Original marking rule", "secondary.original_repeat_rule", "secondary.original_repeat_rule.margin"),
    ("Ties as wrong", "ties.ties_as_wrong", "ties.ties_as_wrong.margin"),
    ("5-point margin", "reporting.five_point_view", "reporting.five_point_view.margin"),
)
# The views' tier (TAB-03's caption; TAB-02's paper version carries it as its 'views' caption fact).
_T3_TIER = ("views of Tests 1–5, not tests: pre-registered secondary views and sensitivity checks, the sensitivity check Deviation 2 "
            "fixed in Lock 3, and reporting views fixed after Lock 3, before any result was opened")
_T3_CACHED = "reporting.group_b.item_9f.family_row"
_T3_TOKEN = "reporting.group_b.item_9g.family_row"
_T3_HAIKU_ORIGINAL = ("haiku-low", "haiku-max", "haiku-thinking-off", "sonnet-low")      # chains: item 10 rates
_T3_RATES_ORIGINAL = ("haiku-med", "opus-low", "opus-med", "sonnet-med")                 # chains: secondary.rates


def _t3_view_cell(S: Store, tests_prefix: str, margin: float, t: str) -> Cell:
    """'d [lo, hi] (reading)', the reading in the paper's words as TAB-02 prints it (Edith's N-3), its own brackets made a comma inside
    the cell's brackets ('inconclusive, could not show'); a stamped reading outside the mapping refuses the build."""
    base = f"{tests_prefix}.tests.{t}"
    lo, hi = ci_refs(S, "main", f"{base}.ci95")
    words = {k: v.replace(" (", ", ").replace(")", "") for k, v in _s1_reading(STUDY1_ARMS[STUDY1_TESTS[t][2]][0]).items()}
    return _reading_cell(pts(S.ref("main", f"{base}.d"), margin=margin),
                         interval(lo, hi, dp=2, signed=True, bounds=(0.0, margin)), text_of(S.ref("main", f"{base}.reading"), words))


def _t3_k_cell(S: Store, prefix: str, t: str) -> Cell:
    return integer(S.ref("main", f"{prefix}.tests.{t}.k")) if S.has("main", f"{prefix}.tests.{t}.k") else DASH


def _t3_format_panel(S: Store) -> Table:
    """Format compliance per arm under both rules. Official: confirmatory.format_compliance for the four confirmatory arms and
    item 10's per-arm block for the others (both shapes). Original marking rule: only the chain shape has a stamped figure; the
    four confirmatory arms from secondary.rates[arm].format_compliance_original, the four others from item 10's rates block.
    original_repeat_rule_appendix.format_compliance is NOT used: it repeats the official values."""
    cols = ["Setting", "Shape", "Samples", "Format compliance, official rule (%)", "Format compliance, original marking rule (%)"]
    rows = []
    for arm in ("haiku-low", "haiku-med", "haiku-max", "haiku-thinking-off", "opus-low", "opus-med", "sonnet-low", "sonnet-med"):
        for sh in SHAPES:
            if arm in _T3_RATES_ORIGINAL:
                off = f"confirmatory.format_compliance.{arm}.{sh}"
                orig = f"secondary.rates.{arm}.format_compliance_original" if sh == "1x6" else None
            else:
                off = join_key("reporting", "group_b", "item_10", "arms", f"{arm} {sh}", "format_compliance")
                orig = join_key("reporting", "group_b", "item_10", "arms", f"{arm} {sh}", "rates", "format_compliance_original") if sh == "1x6" else None
            rows.append([_arm_label(arm), _shape_cell(sh), integer(S.ref("main", f"{off}.tries")),
                         pct(S.ref("main", f"{off}.format_compliance"), dp=2),
                         pct(S.ref("main", orig), dp=2) if orig else DASH])
    # one name per setting, a list of whole items with semicolons (Edith, proof 4: "Haiku, thinking off"); the analysis file's own appendix
    # copy of the format block is the one the note says is not used
    notes = [[label("The original marking rule has a stamped format figure for the 1×6 chains only; the pieces cells are dashes. The original-rule figures for "
                    "Haiku-low; Haiku-max; Haiku, thinking off; and Sonnet-low come from the exploratory settings' own rate blocks, those for the other four settings from the "
                    "secondary views' rates; the analysis file's appendix copy of the format block repeats the official values and is not used.")]]
    p = Table([label(c) for c in cols], rows, notes, {}, layout="float")
    _groups(p, lambda r: r[0].printed)                      # a setting's two shapes together
    return p


# PLAN NOTE (TAB-03): the plan names no cell content for the format side panel's pieces shape under the original marking rule; the files stamp
# a figure for the 1x6 chains only (secondary.rates and item 10's rates are chain-only), so the pieces cells are dashes. The view cells are
# 'd [95%] (reading)' in one cell each, with the cached and equal-token k in their own columns. Superiority p is item 8b's sign_flip (stamped label says d = 0).
@output("TAB-03")
def tab_03(S: Store) -> Table:
    cols = ["Test", "Shape", "Challenger", "Comparator", *[v[0] for v in _T3_VIEWS[:-1]] , "5-point margin",
            "k (cached re-pricing)", "Cached re-pricing", "Equal-token view", "Superiority sign-flip p"]
    rows = []
    token_k: List[Cell] = []         # the equal-token view's k: one value for every vote, so a note gives it, not a column (polish §7.3; Edith, proof 4)
    for t, (name, ch, cmp_, sh, kk) in STUDY1_TESTS.items():
        cells: List[Cell] = [label(name), _shape_cell(sh), label(_challenger(t)), _arm_label(cmp_)]
        for _, prefix, mkey in _T3_VIEWS:
            cells.append(_t3_view_cell(S, prefix, S.get("main", mkey), t))
        cmargin = S.get("main", f"{_T3_CACHED}.family.margin")
        tmargin = S.get("main", f"{_T3_TOKEN}.family.margin")
        cells += [_t3_k_cell(S, _T3_CACHED, t), _t3_view_cell(S, _T3_CACHED, cmargin, t), _t3_view_cell(S, _T3_TOKEN, tmargin, t)]
        if _t3_k_cell(S, _T3_TOKEN, t) is not DASH:
            token_k.append(_t3_k_cell(S, _T3_TOKEN, t))
        sf = f"reporting.group_b.item_8b.sign_flip.{t}"
        cells.append(pvalue(S.ref("main", f"{sf}.p")) if S.get("main", f"{sf}.ran") else DASH)
        rows.append(cells)
    # The note below says one margin holds in every view but the 5-point one: refuse to build if the files say otherwise. Item 9g's stamped
    # label ('token-matched view') is not repeated in the notes: the style sheet bans 'matched'; the column is named 'Equal-token view'.
    margins = {S.get("main", mkey) for name_, _, mkey in _T3_VIEWS if name_ != "5-point margin"} | {cmargin, tmargin}
    if margins != {S.get("main", f"{VIEW}.margin")}:
        raise ValueError(f"views do not share one margin: {margins}")
    notes = [
        _line(label("Every view cell reads: d in points (challenger minus comparator), its 95% interval, and its reading by the pre-registered decision rule against that view's margin. "
                    "Margin in every view except the 5-point view: "), num(S.ref("main", f"{VIEW}.margin"), dp=0, signed=True),
              label(" points; the 5-point view's margin: "), num(S.ref("main", "reporting.five_point_view.margin"), dp=0, signed=True), label(" points.")),
        # the file's own labels are its words, so they print in quotation marks (Edith, proof 4: the sign-off exempts stamped text only there)
        _line(label("Stamped view labels, in the file's own words. 5-point margin: \""), text_of(S.ref("main", "reporting.five_point_view.label")),
              label("\"; cached re-pricing: \""), text_of(S.ref("main", "reporting.group_b.item_9f.label")),
              label("\"; sign-flip\u00a0p: \""), text_of(S.ref("main", "reporting.group_b.item_8b.sign_flip.label")),
              label("\" (a superiority check against no difference, not against the margin).")),
        _line(*_stamped_in_quotes(S.ref("main", "missing_left_out"), "Refusals out and truncations out, as stamped: ", " (the file's \"arms\" are this paper's settings)"),
              label(". Tests 4 and 5 have no vote size k, so no k is shown for them in the cached re-pricing view. In the equal-token view k is "),
              _same_in_every_row(token_k), label(" for every vote (Tests 1–3), so it is given here and is not a column.")),
        # Each column's tier (Edith g1 C-024 and E-09; E-05 for the sign-flip; the style sheet bars "pre-registered" for the reporting
        # definitions: the 5-point view is reporting item 2, the cached and equal-token views items 9f and 9g).
        [label("Label of each column. As deployed: the confirmatory reading (as in TAB-02). Final answer and copy slips forgiven: pre-registered "
               "secondary views. Refusals out, truncations out and ties as wrong: pre-registered sensitivity checks. Original marking rule: "
               "the sensitivity check Deviation 2 fixed in Lock 3, before any main-run data (not a pre-registered secondary view). 5-point "
               "margin, cached re-pricing and equal-token view: reporting views fixed after Lock 3, before any result was opened. Superiority "
               "sign-flip\u00a0p: a pre-specified sensitivity check against no difference. None of these views is a test.")],
        # The views' definitions, in plain words: harness/analysis/five_tests.py (views), scoring.py (copy slips), votes.py (ties), and the
        # reporting definitions items 9f (cached) and 9g (equal-token).
        [label("What each view changes. Refusals out and truncations out: blocked or truncated calls are left out instead of counted wrong. Final answer: a sample is marked, and the vote counted, by "
               "its final answer only, not its step lines. Copy slips forgiven: a sample whose step lines differ from the key at one line only, "
               "with the next line right, counts as right. Ties as wrong: a vote whose top answers tie, the right one among them, scores "
               "nothing instead of an equal share. Cached re-pricing: the vote's repeated input is priced at cache rates, so the same money "
               "can buy a larger k. Equal-token view: k is the number of Haiku-medium samples whose mean total tokens fit within the "
               "comparator's (at least one), instead of its money.")],
        [label(_SONNET_MEDIUM + ".")],
    ]
    caption = _caption(_T3_TIER + " (each column's label is in the notes)",
                       "Study 1, main run, 6 steps",
                       _tab02_n(S),
                       _line(label("paired BCa bootstrap, B = "), integer(S.ref("main", f"{VIEW}.B")), label("; 95% intervals, unadjusted")),
                       [label("list price (the cached re-pricing view prices the vote's repeated input at cache rates)")], _set_cells(S))
    t = Table([label(c) for c in cols], rows, notes, caption)
    t.panels = [("Format compliance per setting under both rules", _t3_format_panel(S))]
    # supplement layout: twelve wide view cells cannot share a page, so three landscape parts, grouped as the notes label the columns
    # (the confirmatory reading and the secondary views; the sensitivity checks; the reporting views fixed after Lock 3)
    _split(t, [["Shape", "Challenger", "Comparator", "As deployed", "Final answer", "Copy slips forgiven"],
               ["Shape", "Refusals out", "Truncations out", "Ties as wrong", "Original marking rule", "Superiority sign-flip p"],
               ["Shape", "5-point margin", "k (cached re-pricing)", "Cached re-pricing", "Equal-token view"]],
           key=["Test"], landscape=True)
    return t


# ================================================================ TAB-04


def _tests_using(arm: str, sh: str) -> str:
    """The confirmatory tests whose design (names.STUDY1_TESTS) uses this arm at this shape, e.g. 'Test 2, Test 3, Test 4'."""
    return ", ".join(name for t, (name, ch, cmp_, s_, kk) in STUDY1_TESTS.items() if s_ == sh and arm in (ch, cmp_))


def _role_label(in_five_test_arms: bool, tests: str) -> Cell:
    """confirmatory = used in a test; 'five-test setting' = in counts.five_test_arms but in no test at this shape; else exploratory."""
    if tests:
        return label("confirmatory")
    return label("five-test setting, in no test at this shape") if in_five_test_arms else label("exploratory")


def _batch_key(S: Store, arm: str, sh: str) -> str:
    """Item 9b's Batch mean for an arm and shape. The caption calls it the Batch price, half the list price: refuse to build if the
    file's own label for the column is not 'Batch' or the Batch mean is not half the list mean."""
    b = join_key("reporting", "group_b", "item_9b", "arms", f"{arm}:{sh}")
    lab, lst, bat = S.get("main", f"{b}.batch_label"), S.get("main", f"{b}.mean"), S.get("main", f"{b}.batch_mean")
    if lab != "Batch" or abs(2 * bat - lst) > 1e-12 * max(1.0, abs(lst)):
        raise ValueError(f"item 9b {arm}:{sh}: batch_label {lab!r}, batch_mean {bat} against list mean {lst}")
    return f"{b}.batch_mean"


# PLAN NOTE (TAB-04): 'tries per puzzle' is the stamped tries over the stamped base puzzles (derive, recorded); Step voting (E3) has no designed count
# and no stamped refusal count, so those cells are dashes. The bootstrap replicate count of the accuracy intervals is not stamped on item 24's rows,
# so the caption names the interval type only. 'Role' comes from the file (counts.five_test_arms) and the tests' design (names.STUDY1_TESTS).
@output("TAB-04")
@main_text
def tab_04(S: Store) -> Table:
    cols = ["Setting", "Shape", "Role", "Used in", "Samples per puzzle", "Accuracy (%)", "Accuracy 95% interval", "Interval type",
            "Median over puzzles (%)", "Format compliance (%)", "List cost per sample ($)",
            "Batch cost per sample ($)", "Cost per correct answer ($)", "Cost per correct answer, lower end of the 95% interval ($)",
            "Cost per correct answer, upper end of the 95% interval ($)"]
    present = set(S.keys("main", ITEM24))
    confirmatory_rows = set(S.keys("main", "counts.five_test_arms"))
    rows, used, truncs, refusal_cells, no_refusal = [], set(), [], [], []
    for arm in ARM_ORDER:
        for sh in SHAPES:
            k24 = f"{arm} {sh}"
            if k24 not in present:
                continue
            used.add(k24)
            b = join_key("reporting", "group_b", "item_24", "table", k24)
            r = S.get("main", b)
            # accuracy: cluster bootstrap for the multi-sample Haiku settings and E3, Clopper–Pearson for the one-sample settings
            if "accuracy_interval" in r:
                acc = pct(S.ref("main", f"{b}.accuracy_mean"), dp=2, from_proportion=False)
                lo, hi = ci_refs(S, "main", f"{b}.accuracy_interval.ci95")
                itype = label("cluster bootstrap")
            else:
                acc = pct(S.ref("main", f"{b}.accuracy_mean"), dp=2, from_proportion=False)
                lo, hi = ci_refs(S, "main", f"{b}.accuracy_cp95.cp95")
                itype = label("Clopper–Pearson (exact)")
            rt = r["refusals_and_truncations"]
            tries = (num_d(derive("tries / base_puzzles", lambda a, c: a / c, S.ref("main", f"{b}.refusals_and_truncations.tries"),
                                  S.ref("main", f"{b}.base_puzzles")), dp=0) if "tries" in rt else DASH)
            if "refusals" in rt:                  # the refusal counts are the same in every row that stamps one: a note, not a column
                refusal_cells.append(integer(S.ref("main", f"{b}.refusals_and_truncations.refusals")))
            else:
                no_refusal.append(k24)
            truncs.append(integer(S.ref("main", f"{b}.refusals_and_truncations.truncations")) if isinstance(rt["truncations"], int)
                          else integer(S.ref("main", f"{b}.refusals_and_truncations.truncations.count")))
            fmt = (pct(S.ref("main", f"{b}.format_compliance.format_compliance"), dp=2) if r.get("format_compliance") else DASH)
            med = pct(S.ref("main", f"{b}.median_over_puzzles"), dp=2, from_proportion=False) if "median_over_puzzles" in r else DASH
            clo, chi = ci_refs(S, "main", f"{b}.cpc.ci95")
            rows.append([_arm_label(arm), _shape_cell(sh),
                         _role_label(k24 in confirmatory_rows, _tests_using(arm, sh)),
                         label(_tests_using(arm, sh)) if _tests_using(arm, sh) else DASH,
                         tries, acc, interval(lo, hi, dp=2), itype, med, fmt,
                         usd(S.ref("main", f"{b}.cost_per_puzzle.mean")),
                         usd(S.ref("main", _batch_key(S, arm, sh))),
                         usd(S.ref("main", f"{b}.cpc.cpc")), usd(clo), usd(chi)])
    if used != present:
        raise ValueError(f"item 24 rows not covered: {sorted(present - used)}")
    e3 = join_key("reporting", "group_b", "item_24", "table", "e3 1x6", "refusals_and_truncations")
    # The note says every step-voting call is stamped as answered, with no refusal category: refuse to build if the file says otherwise.
    e3_rt = S.get("main", e3)
    if (e3_rt.get("kinds") != {"answered": e3_rt.get("calls_made")} or e3_rt.get("refusals_by_category") != {}
            or e3_rt.get("failures_by_kind") != {} or "refusals" in e3_rt or no_refusal != ["e3 1x6"]):
        raise ValueError(f"step voting's refusal fields changed: {sorted(e3_rt)}, rows without a refusal count {no_refusal}")
    notes = [
        [label("Role: confirmatory settings are those a test uses at that shape; a five-test setting is a setting of the confirmatory run (the file's own list) that no test uses at that shape; the rest are exploratory. "
               "Haiku-medium enters Tests 1–3 as a vote of k samples; the row here is its single sample, and the votes are in the Study 1 test tables.")],
        _line(label("Samples per puzzle is the stamped samples divided by the stamped puzzles. Step voting has no designed number of calls, "
                    "so its samples-per-puzzle cell is a dash; it made "), integer(S.ref("main", f"{e3}.calls_made")), label(" calls.")),
        # one value for both counts in every row; step voting's row is the one that stamps no refusal count
        _line(label("Refusals and truncations: "), _same_in_every_row(refusal_cells + truncs),
              label(" in every row; the one exception is step voting's refusal count, which its row does not stamp (the file stamps all "),
              integer(S.ref("main", f"{e3}.kinds.answered")), label(" of its calls as answered, with no refusal category).")),
        [label("Cost per sample: for the Haiku settings, one sample's mean list cost (a vote of k samples costs k times this); for step voting, all its calls "
               "on a puzzle; for Opus and Sonnet, their one answer. The Batch column is the same at the Batch price (half the list price). Cost per "
               "correct answer is the total cost of one sample per puzzle over the expected number of those samples that are right, at list price. "
               "Costs are in US dollars.")],
        [label("Interval type: the Haiku settings' and step voting's accuracy intervals are cluster bootstraps over puzzles; the one-sample Opus and Sonnet settings' "
               "are Clopper–Pearson intervals, which are exact: they come from the binomial distribution itself, with no resampling.")],
    ]
    # The cost-per-try note: refuse to build unless item 9b stamps the Haiku rows per sample (k = 1), step voting as the sum of its calls and
    # the Opus and Sonnet rows as their single call, and item 24's cost rows are at k = 1.
    how = {"haiku": "per_sample", "e3": "sum", "opus": "single", "sonnet": "single"}
    for k24 in present:
        arm, sh = k24.split(" ")
        b9 = join_key("reporting", "group_b", "item_9b", "arms", f"{arm}:{sh}")
        if (S.get("main", f"{b9}.how") != how[arm.split("-")[0]] or S.get("main", f"{b9}.k") != 1
                or S.get("main", join_key("reporting", "group_b", "item_24", "table", k24, "cost_per_puzzle", "k")) != 1):
            raise ValueError(f"{k24}: the cost-per-try note does not fit item 9b's or item 24's cost basis")
    caption = _caption("pre-specified descriptive (every setting and shape)", "Study 1, main run, 6 steps",
                       _line(label("puzzles per setting and shape: "), integer(S.ref("main", f"{ITEM24}.haiku-med 1x6.base_puzzles")),
                             label("; samples per puzzle as in the Samples per puzzle column")),
                       [label("95%: cluster bootstrap over puzzles for Haiku and step voting (replicates not stamped on these rows), "
                              "Clopper–Pearson (exact) for the one-sample Opus and Sonnet settings")],
                       [label("list price per sample (for step voting, its whole run on a puzzle); the Batch column is at the Batch price, half the list price")],
                       _set_cells(S))
    t = Table([label(c) for c in cols], rows, notes, caption)
    # supplement layout: two landscape parts (the setting, its role and accuracy; the answers' quality and cost)
    _split(t, [["Shape", "Role", "Used in", "Samples per puzzle", "Accuracy (%)", "Accuracy 95% interval", "Interval type", "Median over puzzles (%)"],
               ["Shape", "Format compliance (%)", "List cost per sample ($)", "Batch cost per sample ($)",
                "Cost per correct answer ($)", "Cost per correct answer, lower end of the 95% interval ($)",
                "Cost per correct answer, upper end of the 95% interval ($)"]], key=["Setting"], landscape=True)
    _groups(t, lambda r: r[0].printed)                      # a setting's two shapes together (the writer carries the groups into the parts)
    return t


# ================================================================ TAB-05

_T5_COLS = ["Group", "Challenger", "Comparator", "Shape", "k", "Raw k", "Capped by", "Spend share",
            "Challenger accuracy (%)", "Challenger format compliance (%)", "Comparator accuracy (%)", "Comparator format compliance (%)",
            "d (points)", "d 95% interval", "Cost ratio (challenger / comparator) [95% interval]",
            "Cost per correct answer ratio [95% interval]", "Cost difference ($ per sample)", "Status (stamped)"]


_CAPPED_BY = {None: "", "cap": "cap on k", "samples_drawn": "samples drawn"}     # the stamped capped_by values


def _t5_row(S: Store, arms, group: str, challenger: Cell, comparator: Cell, sh: str, k: Cell, raw_k: Cell, capped: Cell, spend: Cell,
            acc_ch: Cell, acc_cmp: Cell, d: Cell, d_ci: Cell, cost_ratio: Cell, cpc_ratio: Cell, cost_diff: Cell, status: Cell) -> List[Cell]:
    """One row; `arms` (challenger setting, comparator setting) give each side's format compliance at the row's shape, beside its accuracy
    (for a vote, that of the setting's samples the vote is drawn from). `spend` is a vote's spend share (its spend over the comparator's,
    a point); `cost_ratio` is a cost ratio with its interval: two quantities, each in its own column (Edith's §2.8)."""
    return [label(group), challenger, comparator, _shape_cell(sh), k, raw_k, capped, spend, acc_ch, _fc_cell(S, arms[0], sh), acc_cmp,
            _fc_cell(S, arms[1], sh), d, d_ci, cost_ratio, cpc_ratio, cost_diff, status]


def _acc24(S: Store, arm: str, sh: str, dp: int = 2, bounds=()) -> Cell:
    """A setting's single-sample accuracy at a shape (points) from item 24."""
    return pct(S.ref("main", join_key("reporting", "group_b", "item_24", "table", f"{arm} {sh}", "accuracy_mean")), dp=dp,
               from_proportion=False, bounds=bounds)


def _ratio_ci(S: Store, source: str, point_key: str, ci_key: str) -> Cell:
    return joined(num(S.ref(source, point_key), dp=2), interval(*ci_refs(S, source, ci_key), dp=2))


def _fa4_cell(S: Store, source: str, key: str, arm: str):
    """The index of free analysis 4's exact-interval cell for this arm of a stamped paired block, or None when fa4 has none. A C10 pair's
    two arms share the pair's key in fa4 (core.fa4_exact reads one cell per key, so it is not used here): the arm is found by its
    display name in fa4's cell name, the key is compared segment by segment (fa4 writes plain dotted paths), one match at most, and
    fa4's copy of the stamped interval must be the pair's own, collapsed."""
    path, want = S.sources[source].path, parse_key(key)
    hits = [i for i, c in enumerate(S.get("fa4", "result.cells"))
            if c["source"] == path and c["key"].split(".") == want
            and re.search(r"\b" + re.escape(STUDY1_ARMS[arm][0]) + r",", c["cell"])]
    if len(hits) > 1:
        raise ValueError(f"fa4: {len(hits)} cells for {arm} at {key}")
    if not hits:
        return None
    lo, hi = S.get(source, key + ".ci95")
    if S.get("fa4", f"result.cells.{hits[0]}.stamped_ci95") != [lo, hi] or lo != hi:
        raise ValueError(f"fa4 cell {hits[0]} is not the copy of {source}:{key}'s collapsed interval")
    return hits[0]


# fa4's own note on a C10 pair's arm cells; the effort-pair notes say the same in plain words, so a changed note refuses the build
FA4_PAIR_NOTE = "each arm's exact accuracy interval is given instead"


def _c10_exact_arms(S: Store, p: str, a: str, b_: str) -> int:
    """How many arms of the C10 pair `p` carry free analysis 4's exact interval: both where the pair's bootstrap interval of d collapsed,
    none otherwise. The notes say the arms are then at the ceiling and that fa4 gives no exact interval for the difference itself, only
    each arm's: anything else refuses the build."""
    lo, hi = S.get("groupc", f"{p}.ci95")
    have = [i for i in (_fa4_cell(S, "groupc", p, x) for x in (a, b_)) if i is not None]
    if len(have) not in (0, 2) or (lo == hi) != (len(have) == 2):
        raise ValueError(f"C10 {p}: interval {[lo, hi]} with {len(have)} fa4 arm cells; the effort-pair notes no longer hold")
    for i in have:
        c = S.get("fa4", f"result.cells.{i}")
        if c["x"] != c["n"] or FA4_PAIR_NOTE not in str(c["note"]):
            raise ValueError(f"fa4 cell {i}: not at the ceiling, or its note no longer says {FA4_PAIR_NOTE!r}")
    return len(have)


def _acc_with_exact(S: Store, acc: Cell, source: str, key: str, arm: str) -> Cell:
    """An accuracy cell; where free analysis 4 stamps an exact (Clopper–Pearson) interval for this arm of the block (both arms at the
    ceiling, so the bootstrap interval of d collapsed), the exact interval follows, labelled post hoc."""
    i = _fa4_cell(S, source, key, arm)
    if i is None:
        return acc
    if S.get("fa4", f"result.cells.{i}.unit") != "points":
        raise ValueError(f"fa4 cell {i} is not in points")
    return joined(acc, label(" "), interval(*ci_refs(S, "fa4", f"result.cells.{i}.exact95"), dp=2), label(" post hoc† (exact)"), sep="")


def _d_ci_cell(S: Store, source: str, key: str) -> Cell:
    """A d interval; one that collapsed to a single point is marked so (the note says what replaces it)."""
    lo, hi = S.get(source, key)
    cell = interval(*ci_refs(S, source, key), dp=2, signed=True, bounds=(0.0,))
    return joined(cell, label(" (collapsed)"), sep="") if lo == hi else cell


_OWN_K_ARMS = ("haiku-low", "haiku-thinking-off", "haiku-max")


def _own_k_caps_note(S: Store) -> List[Cell]:
    """Edith's N-7: the own-k note names every capped k, read from the stamped k computations of item 10's own-k blocks (k, raw k,
    the cap or the samples drawn). Refuse to build unless only votes against Opus-medium are capped, each held exactly at its cap or at
    its samples drawn, one reason and one held value per arm."""
    parts: List[Cell] = []
    for arm in _OWN_K_ARMS:
        kv = {(sh, c): join_key("reporting", "group_b", "item_10", "arms", f"{arm} {sh}", "own_k", f"vs {c}", "k_value")
              for sh in SHAPES for c in ("opus-med", "sonnet-med")}
        if any(S.get("main", f"{b}.capped_by") is not None for (sh, c), b in kv.items() if c == "sonnet-med"):
            raise ValueError(f"{arm}: a vote against Sonnet-medium is capped; the note says none is")
        capped = [(sh, kv[(sh, "opus-med")]) for sh in SHAPES if S.get("main", f"{kv[(sh, 'opus-med')]}.capped_by") is not None]
        if not capped:
            continue
        why = {S.get("main", f"{b}.capped_by") for _, b in capped}
        held_key = {"cap": "cap", "samples_drawn": "samples_drawn"}[why.pop()] if len(why) == 1 else None
        if held_key is None or any(S.get("main", f"{b}.k") != S.get("main", f"{b}.{held_key}") for _, b in capped) \
                or len({S.get("main", f"{b}.{held_key}") for _, b in capped}) != 1:
            raise ValueError(f"{arm}: its capped ks are not all held at one {held_key or 'reason'}")
        b0 = capped[0][1]
        held = (joined(label("held at the cap on k of "), integer(S.ref("main", f"{b0}.cap")), sep="") if held_key == "cap"
                else joined(label("held at its "), integer(S.ref("main", f"{b0}.samples_drawn")), label(" samples drawn"), sep=""))
        raws = [integer(S.ref("main", f"{b}.raw_k")) for _, b in capped]
        raw_text = raws[0] if len(raws) == 1 else joined(*raws[:-1], sep=", ")
        raw_cells = [raw_text] if len(raws) == 1 else [raw_text, label(" and "), raws[-1]]
        parts += [label("; " if parts else ""), label(f"{STUDY1_ARMS[arm][0]} on " + " and ".join(shape(sh) for sh, _ in capped) + ", "),
                  held, label(" (raw k "), *raw_cells, label(")")]
    if not parts:
        raise ValueError("no own-k vote is capped: rewrite the own-k note")
    return _line(label("The own-k votes use each Haiku setting's own cost-matched k against Opus-medium and against Sonnet-medium; where "
                       "a k is capped, the Raw k column gives the cost-matched k before the cap. Capped, all against Opus-medium: "),
                 *parts, label(". Against Sonnet-medium no k is capped. The spend share of a vote is its spend over the comparator's (the file's \"spend ratio\"), a point with no interval."))


def _is_test_pair(ch: str, cmp_: str, sh: str):
    """The confirmatory test whose design is this challenger, comparator and shape, or None."""
    hits = [t for t, (_, c, m, s_, _k) in STUDY1_TESTS.items() if (c, m, s_) == (ch, cmp_, sh)]
    return hits[0] if hits else None


@output("TAB-05")
def tab_05(S: Store) -> Table:
    rows: List[List[Cell]] = []
    st10 = text_of(S.ref("main", "reporting.group_b.item_10.label"))
    st11 = text_of(S.ref("main", "reporting.group_b.item_11.label"))
    st9h = text_of(S.ref("main", "reporting.group_b.item_9h.label"))
    stc10 = text_of(S.ref("groupc", "item_C10.exploratory"))

    # --- own-k votes of the other Haiku settings against Opus-medium and Sonnet-medium (item 10); Haiku-max is capped at its drawn samples
    for arm in ("haiku-low", "haiku-thinking-off", "haiku-max"):
        for sh in SHAPES:
            for cmp_ in ("opus-med", "sonnet-med"):
                b = join_key("reporting", "group_b", "item_10", "arms", f"{arm} {sh}", "own_k", f"vs {cmp_}")
                rows.append(_t5_row(S, (arm, cmp_), f"Own-k vote vs {STUDY1_ARMS[cmp_][0]}", label(f"{STUDY1_ARMS[arm][0]} vote"), _arm_label(cmp_), sh,
                                    integer(S.ref("main", f"{b}.k_value.k")), integer(S.ref("main", f"{b}.k_value.raw_k")),
                                    text_of(S.ref("main", f"{b}.k_value.capped_by"), _CAPPED_BY),
                                    num(S.ref("main", f"{b}.k_value.spend.haiku_over_comparator"), dp=3, bounds=(1.0,)),
                                    pct(S.ref("main", f"{b}.vote_mean"), dp=2, from_proportion=False), _acc24(S, cmp_, sh),
                                    pts(S.ref("main", f"{b}.paired.d")), interval(*ci_refs(S, "main", f"{b}.paired.ci95"), dp=2, signed=True, bounds=(0.0,)),
                                    DASH, DASH, DASH, st10))
    # --- Sonnet-low against Sonnet-medium and Opus-low (item 10): single-try pairs
    for sh in SHAPES:
        b = join_key("reporting", "group_b", "item_10", "arms", f"sonnet-low {sh}")
        for cmp_ in ("sonnet-med", "opus-low"):
            pb = f"{b}.paired.vs {cmp_}"
            rows.append(_t5_row(S, ("sonnet-low", cmp_), "Sonnet-low vs Sonnet-medium and Opus-low", _arm_label("sonnet-low"), _arm_label(cmp_), sh,
                                integer(S.ref("main", f"{b}.cost_per_puzzle.k")), DASH, EMPTY, DASH,
                                pct(S.ref("main", f"{b}.accuracy_cp95.accuracy"), dp=2, from_proportion=False), _acc24(S, cmp_, sh),
                                pts(S.ref("main", f"{pb}.d")), interval(*ci_refs(S, "main", f"{pb}.ci95"), dp=2, signed=True, bounds=(0.0,)),
                                DASH, DASH, DASH, st10))
    # --- item 11 counterparts at 6x1 (Test 3 and Test 5 re-run at the pieces shape); never the declared flag
    ks = "reporting.group_b.item_11.k_s_6x1"
    t3 = "reporting.group_b.item_11.t3@6x1.as_deployed"
    rows.append(_t5_row(S, ("haiku-med", "sonnet-med"), "Pieces counterpart of Test 3", label("Haiku-medium vote"), _arm_label("sonnet-med"), "6x1",
                        integer(S.ref("main", f"{ks}.k")), integer(S.ref("main", f"{ks}.raw_k")), text_of(S.ref("main", f"{ks}.capped_by"), _CAPPED_BY),
                        num(S.ref("main", f"{ks}.spend.haiku_over_comparator"), dp=3, bounds=(1.0,)),
                        pct(S.ref("main", join_key("reporting", "group_b", "item_24", "table", "haiku-med 6x1", "vote_at_own_k", "k_S", "mean")), dp=2, from_proportion=False),
                        _acc24(S, "sonnet-med", "6x1"), pts(S.ref("main", f"{t3}.d")),
                        interval(*ci_refs(S, "main", f"{t3}.ci95"), dp=2, signed=True, bounds=(0.0,)),
                        DASH, DASH, DASH, st11))
    t5 = "reporting.group_b.item_11.t5@6x1.as_deployed"
    # The pieces counterparts printed here, by (challenger, comparator, shape): the Opus-against-Sonnet block below never prints a second
    # d or interval for one of them (Edith: one comparison, one interval).
    counterparts = {(STUDY1_TESTS["t3"][1], STUDY1_TESTS["t3"][2], "6x1"): "Pieces counterpart of Test 3",
                    (STUDY1_TESTS["t5"][1], STUDY1_TESTS["t5"][2], "6x1"): "Pieces counterpart of Test 5"}
    rows.append(_t5_row(S, ("opus-low", "sonnet-med"), "Pieces counterpart of Test 5", _arm_label("opus-low"), _arm_label("sonnet-med"), "6x1",
                        DASH, DASH, EMPTY, DASH, _acc24(S, "opus-low", "6x1"), _acc24(S, "sonnet-med", "6x1"), pts(S.ref("main", f"{t5}.d")),
                        interval(*ci_refs(S, "main", f"{t5}.ci95"), dp=2, signed=True, bounds=(0.0,)), DASH, DASH, DASH, st11))
    # --- C10 effort pairs (keep-list): low effort minus medium effort, single try; free analysis 4's exact per-arm intervals at the ceiling
    n_exact = 0
    for a, b_ in (("haiku-low", "haiku-med"), ("opus-low", "opus-med")):
        for sh in SHAPES:
            p = join_key("item_C10", "pairs", f"{a}-vs-{b_}:{sh}")
            rows.append(_t5_row(S, (a, b_), "Effort pair", _arm_label(a), _arm_label(b_), sh,
                                integer(S.ref("groupc", f"{p}.cost_9b.{a}.k")), DASH, EMPTY, DASH,
                                _acc_with_exact(S, pct(S.ref("groupc", f"{p}.accuracy_means.{a}"), dp=2, from_proportion=False), "groupc", p, a),
                                _acc_with_exact(S, pct(S.ref("groupc", f"{p}.accuracy_means.{b_}"), dp=2, from_proportion=False), "groupc", p, b_),
                                pts(S.ref("groupc", f"{p}.d")), _d_ci_cell(S, "groupc", f"{p}.ci95"),
                                DASH, DASH, usd(S.ref("groupc", f"{p}.cost_difference_usd")), stc10))
            n_exact += _c10_exact_arms(S, p, a, b_)
    # --- item 9h: Opus against Sonnet at each shape, with cost and cost-per-correct ratios. Opus-low against Sonnet-medium on chains is
    # Test 5's comparison: item 9h's separate exploratory interval is never printed for it (Edith, E-05(a)); the row points to TAB-02. On
    # pieces the same pair is item 11's counterpart of Test 5, printed above from item 11: item 9h's d and interval are not printed again
    # (Edith's final check S1-01: one comparison, one interval); the row points to that row.
    test_pair_rows: List[str] = []
    counterpart_rows: List[str] = []
    for sh in SHAPES:
        for a in ("opus-low", "opus-med"):
            pk = join_key("reporting", "group_b", "item_9h", sh, "pairs", f"{a}-vs-sonnet-med")
            ab = join_key("reporting", "group_b", "item_9h", sh, "arms")
            test = _is_test_pair(a, "sonnet-med", sh)
            if test is not None:        # Test 5's own comparison: its d and interval are the confirmatory ones (TAB-02), never item 9h's
                test_pair_rows.append(test)
                d_cells = [DASH, label(f"{STUDY1_TESTS[test][0]}: see TAB-02")]
            elif (a, "sonnet-med", sh) in counterparts:      # printed once, in its pieces-counterpart row above
                counterpart_rows.append(counterparts[(a, "sonnet-med", sh)])
                name = counterparts[(a, "sonnet-med", sh)]
                d_cells = [DASH, label(f"see the {name[0].lower() + name[1:]} row")]
            else:
                d_cells = [pts(S.ref("main", f"{pk}.point.acc_diff")),
                           interval(*ci_refs(S, "main", f"{pk}.intervals.acc_diff.ci95"), dp=2, signed=True, bounds=(0.0,))]
            rows.append(_t5_row(S, (a, "sonnet-med"), "Opus against Sonnet", _arm_label(a), _arm_label("sonnet-med"), sh, DASH, DASH, EMPTY, DASH,
                                _share_pts(S.ref("main", f"{ab}.{a}.A.as_deployed"), dp=2), _share_pts(S.ref("main", f"{ab}.sonnet-med.A.as_deployed"), dp=2),
                                *d_cells,
                                _ratio_ci(S, "main", f"{pk}.point.cost_ratio", f"{pk}.intervals.cost_ratio.ci95"),
                                _ratio_ci(S, "main", f"{pk}.point.cpc_ratio", f"{pk}.intervals.cpc_ratio.ci95"), DASH, st9h))
    # PLAN NOTE: the plan asks for "cost ratios [95%]" on every row. Only item 9h stamps cost-ratio intervals; item 10's own-k blocks stamp the
    # spend ratio (point) and item 11's k_s block likewise, and nothing is stamped for Sonnet-low or the item 11 Test 5 counterpart, so those cells
    # are dashes (no ratio is computed here).
    # Item 11 did not compute Test 4's comparison at 6x1; the stamped string's process wording is not printed. Step voting on pieces ran
    # later, in the top-up (topup-1 test4_pieces, TAB-14): refuse to build if either fact changes.
    t4 = S.get("main", "reporting.group_b.item_11.t4@6x1")
    if not (isinstance(t4, str) and t4.startswith("not computed")) or not S.has("topup", "test4_pieces.as_deployed"):
        raise ValueError(f"item 11 t4@6x1 is {t4!r}: the note on the pieces counterpart of Test 4 no longer holds")
    if test_pair_rows != ["t5"] or counterpart_rows != ["Pieces counterpart of Test 5"]:
        raise ValueError(f"item 9h rows that are a test's comparison or a pieces counterpart: {test_pair_rows}, {counterpart_rows}")
    # Haiku-max's own k is capped by its samples drawn against Opus-medium only (the note says so): refuse to build if that changes.
    hx = {(sh, c): S.get("main", join_key("reporting", "group_b", "item_10", "arms", f"haiku-max {sh}", "own_k", f"vs {c}", "k_value",
                                          "capped_by"))
          for sh in SHAPES for c in ("opus-med", "sonnet-med")}
    if ({v for (sh, c), v in hx.items() if c == "opus-med"} != {"samples_drawn"}
            or {v for (sh, c), v in hx.items() if c == "sonnet-med"} != {None}):
        raise ValueError(f"Haiku-max's caps changed: {hx}")
    c10_B = {S.get("groupc", f"item_C10.pairs.{k}.B") for k in S.keys("groupc", "item_C10.pairs")}
    if c10_B != {S.get("groupc", "item_C10.pairs.opus-low-vs-opus-med:1x6.B")}:
        raise ValueError(f"C10 pairs differ in B: {c10_B}")
    notes = [
        [label("Every comparison is exploratory, unadjusted and outside the Holm family: no verdict is printed. The status column repeats each block's stamped label.")],
        _own_k_caps_note(S),
        [label("The pieces counterparts repeat Test 3's and Test 5's comparisons at 6×1. Test 4's comparison was not computed at 6×1 in the main run, because step "
               "voting did not run on pieces there. Step voting on pieces against one Opus-medium answer (the pieces counterpart of Test 4; unadjusted, exploratory, "
               "outside the pre-registered family) ran later, in the top-up run, and is reported in TAB-14.")],
        [label("Neither pieces counterpart is shown no worse (Holm-adjusted): both are outside the Holm family. The file's own \"declared\" field on the counterpart of Test 5 "
               "means its p fell below the one-sided level for that comparison alone, not under Holm, and is not shown.")],
        [label("Format compliance is the share of each side's samples in the required answer format; for a vote, that of the setting's samples the vote is drawn from.")],
        [label("Effort pairs are low effort minus medium effort at one sample; the cost difference is the stamped difference of the two mean list costs of one sample (in US dollars; for Opus, its one answer).")],
        [label("Opus-low against Sonnet-medium at 1×6 is Test 5's comparison. Its confirmatory d and interval are in TAB-02; the Opus-against-Sonnet block's separate "
               "exploratory interval for the same pair is not printed, and that row keeps the block's accuracies and cost ratios only. At 6×1 the same pair is the "
               "pieces counterpart of Test 5: its d and interval are printed once, in that row, and the Opus-against-Sonnet row keeps its accuracies and cost ratios only.")],
        # only the dashes that print: the raw k and spend share columns (a vote's), the k of the rows whose file stamps none (item 9h's
        # pairs and item 11's t5@6x1 hold no k; the Sonnet-low rows and the effort pairs print k = 1), the cost part's cost ratios (item 9h's
        # rows only) and cost difference (the effort pairs' only: item 9h stamps each arm's cost per answer but no dollar difference), and
        # the two d cells; the cost part drops the rows with no cost figure (Sonnet-low, the pieces counterparts, the own-k votes), so
        # their dashes do not print (proof 4, group 1 checks)
        [label("Dashes mark cells that do not apply (a spend share and a raw k belong to the votes, a cost ratio to the Opus-against-Sonnet rows), "
               "cells the files do not stamp (the k of the Opus-against-Sonnet rows and of the pieces counterpart of Test 5, and the cost difference "
               "in dollars of the Opus-against-Sonnet rows) and the d cells of the two Opus-against-Sonnet rows whose comparison is printed "
               "elsewhere. The cost columns are in a part of their own "
               "that prints only the rows with a cost figure, so the dashes of the other rows are not printed there; the accuracy columns are in two "
               "parts, one for the own-k votes and one for the other rows.")],
        [label("Sonnet-medium ran at medium effort, one level below Sonnet's default, in every row where it appears.")],
    ]
    if S.get("main", "reporting.group_b.item_11.t5@6x1.as_deployed.declared") is not True:
        raise ValueError("the note on item 11's declared field assumes the Test 5 counterpart stamps declared: true")
    if not n_exact:          # the caption and this note name the exact per-arm intervals at the ceiling
        raise ValueError("TAB-05: no effort pair carries free analysis 4's exact per-arm intervals; rewrite the note and the caption")
    # The waiver (Edith, proof 3, D: 0.9998 in the spend share column): a spend share prints at three decimals, and one that three
    # decimals would round to 1.000 keeps a fourth, so it does not read as equal to its comparator's. The note says so and names the row.
    sj = _T5_COLS.index("Spend share")
    four = [r for r in rows if re.fullmatch(r"\d\.\d{4}", r[sj].printed)]
    if len(four) != 1 or four[0][sj].printed[0] != "0" or not four[0][0].printed.startswith("Own-k vote"):
        raise ValueError(f"the spend-share note names one own-k vote that keeps a fourth decimal: {[r[sj].printed for r in four]}")
    r4 = four[0]
    # the note's "three" is the column's own precision: every other spend share prints at three decimals (checked)
    dp = 3
    if any(re.fullmatch(r"\d\.\d+", r[sj].printed) and len(r[sj].printed.split(".")[1]) != dp for r in rows if r is not four[0]):
        raise ValueError("TAB-05's spend shares no longer print at three decimals (with one guard cell at four): reword the note")
    three = Cell(fmt_fixed(r4[sj].raw, dp), raw=r4[sj].raw, refs=r4[sj].refs, formula="the spend share rounded to three decimals (what it would print without its fourth)")
    notes.insert(2, _line(label("Spend shares print at three decimals; "), r4[sj],
                          label(f" ({r4[1].printed} against {r4[2].printed} at {r4[3].printed}) keeps a fourth decimal, because at three it would print as "),
                          three, label(" and read as equal to the comparator's spend.")))
    notes.insert(6 + 1, [label("Where both settings of an effort pair are at the ceiling, the bootstrap interval of d collapses to one point (marked collapsed). "
                           "The difference itself has no exact interval in free analysis 4, which gives each setting's exact 95% interval instead "
                           "(Clopper–Pearson over puzzles), printed in that setting's accuracy cell as post hoc† (exact): a presentation only, not a test.")])
    caption = _caption("exploratory, unadjusted, outside Holm; the exact per-setting intervals at the ceiling are post hoc", "Study 1, main run, 6 steps",
                       _line(label("puzzles per pair: "), integer(S.ref("main", f"{t3}.n")),
                             label("; a vote uses k samples per puzzle (the k column); the other rows compare single-sample accuracies (for a Haiku setting, "
                                   "the mean over its samples)")),
                       _line(label("95% intervals. Paired BCa bootstrap for the own-k votes, the Sonnet-low rows, the pieces counterparts and the effort pairs "
                                   "(B = "), integer(S.ref("groupc", "item_C10.pairs.opus-low-vs-opus-med:1x6.B")),
                             label(", stamped on the effort pairs; not stamped on the other rows). Paired cluster bootstrap over puzzles for "
                                   "the Opus-against-Sonnet rows (draw count not stamped). Exact Clopper–Pearson for the post hoc per-setting intervals at the ceiling.")),
                       [label("list price")], _set_cells(S))
    t = Table([label(c) for c in _T5_COLS], rows, notes, caption)
    # supplement layout: 18 columns, so four parts that each repeat the block, the pair and the shape: the vote's size, spend and
    # status; the accuracies and the difference (the own-k votes, then the other rows); the cost figures
    own = [i for i, r in enumerate(t.rows) if r[0].printed.startswith("Own-k vote")]
    rest = [i for i in range(len(t.rows)) if i not in own]
    if own != list(range(len(own))):
        raise ValueError("the own-k votes are not the first rows of TAB-05")
    acc = ["Challenger accuracy (%)", "Challenger format compliance (%)", "Comparator accuracy (%)", "Comparator format compliance (%)",
           "d (points)", "d 95% interval"]
    cost = ["Cost ratio (challenger / comparator) [95% interval]", "Cost per correct answer ratio [95% interval]", "Cost difference ($ per sample)"]
    with_cost = [i for i in rest if any(t.rows[i][j].printed not in DASHES for j in _idx(t, *cost))]      # the rows with a cost figure
    _split(t, [["k", "Raw k", "Capped by", "Spend share", "Status (stamped)"], (own, acc), (rest, acc),
               (with_cost, cost)],
           key=["Group", "Challenger", "Comparator", "Shape"], landscape=True, font="footnotesize")

    def block(r):
        """The row's block: one Haiku setting's own-k votes (they alternate comparators, so not by the Group cell), the two pieces
        counterparts together, else the Group cell."""
        if r[0].printed.startswith("Own-k vote"):
            return ("own-k", r[1].printed)
        return "pieces counterparts" if r[0].printed.startswith("Pieces counterpart") else r[0].printed
    _groups(t, block)
    t.once = [0]              # a block's name prints once, on its first row (a long one no longer wraps on every row of its block)
    return t


# ================================================================ TAB-06 (keep-list analyses C2, C3, C5, C7, C9, C10; groupc.json)

_C_ARMS = ("haiku-thinking-off", "haiku-low", "haiku-med", "haiku-max", "opus-low", "opus-med", "sonnet-low", "sonnet-med")


def _c2_c3_main(S: Store):
    """The C2/C3 table and the puzzle count its rows share (every row's, one cell: it goes to a note, not a column)."""
    cols = ["Setting", "C2 statistic", "C2 correlation, 6×1 against 1×6", "C2 95% interval", "C2 undefined where", "C3 accuracy 1×6 (%)",
            "Format compliance 1×6 (%)", "C3 accuracy 6×1 (%)", "Format compliance 6×1 (%)", "C3 d: 6×1 minus 1×6 (points)",
            "C3 95% interval"]
    if set(S.keys("groupc", "item_C2.arms")) != set(_C_ARMS) or set(S.keys("groupc", "item_C3.arms")) != set(_C_ARMS):
        raise ValueError("C2/C3 settings differ from the expected eight")
    rows, ns = [], []
    for arm in _C_ARMS:
        c2, c3 = f"item_C2.arms.{arm}", f"item_C3.arms.{arm}"
        r = S.ref("groupc", f"{c2}.r")
        corr = text_of(r) if isinstance(r.value, str) else num(r, dp=2, signed=True, bounds=(0.0,))
        why = _get(S, "groupc", f"{c2}.why_undefined")
        undefined = (joined(text_of(S.ref("groupc", f"{c2}.why_undefined.1x6"), {True: "1×6 has no variation", False: ""}),
                            text_of(S.ref("groupc", f"{c2}.why_undefined.6x1"), {True: "6×1 has no variation", False: ""}), sep="; ")
                     if why is not None else EMPTY)
        rows.append([_arm_label(arm), text_of(S.ref("groupc", f"{c2}.statistic")), corr,
                     _ci_or_dash(S, "groupc", f"{c2}.ci95", dp=2, signed=True, bounds=(0.0,)), undefined,
                     pct(S.ref("groupc", f"{c3}.accuracy_1x6"), dp=2, from_proportion=False), _fc_cell(S, arm, "1x6"),
                     pct(S.ref("groupc", f"{c3}.accuracy_6x1"), dp=2, from_proportion=False), _fc_cell(S, arm, "6x1"),
                     pts(S.ref("groupc", f"{c3}.d")), interval(*ci_refs(S, "groupc", f"{c3}.ci95"), dp=2, signed=True, bounds=(0.0,))])
        ns.append(integer(S.ref("groupc", f"{c3}.n_bases")))
    return Table([label(c) for c in cols], rows), _same_in_every_row(ns)


def _k_o_note(S: Store, k_o_key: str) -> List[Cell]:
    """k_O in plain words, at its first use in each panel that prints it (Edith's N-11). `k_o_key` formats a shape into the panel's
    stamped k_O key; refuse to build unless that k_O is k.json's Opus k at each shape, the k of Tests 1 (6×1) and 2 (1×6). That k is the
    equal-money k held at the cap where k.json caps it (TAB-02's columns: raw k is the equal-money k before the cap), so the note names
    each capped shape with its cap and raw k, read from k.json; refuse to build unless the shapes named are exactly those k.json caps by
    the cap (capped_by 'cap', k = cap < raw k) and every other shape's k is its raw k."""
    for sh in SHAPES:
        if S.get("groupc", k_o_key.format(sh=sh)) != S.get("main_k", f"k_from_rows.opus.{sh}.k"):
            raise ValueError(f"{k_o_key.format(sh=sh)} is not k.json's Opus k")
    tests = {t: (ch, cmp_, sh, kk) for t, (_n, ch, cmp_, sh, kk) in STUDY1_TESTS.items() if t in ("t1", "t2")}
    if tests != {"t1": ("haiku-med", "opus-med", "6x1", "O"), "t2": ("haiku-med", "opus-med", "1x6", "O")}:
        raise ValueError("the k_O note assumes Tests 1 and 2 are the Haiku-medium vote against Opus-medium at 6×1 and 1×6")
    capped = []
    for t in ("t1", "t2"):
        b = f"k_from_rows.opus.{tests[t][2]}"
        k, raw, cap, by, flag = (S.get("main_k", f"{b}.{f}") for f in ("k", "raw_k", "cap", "capped_by", "capped"))
        if by not in (None, "cap") or bool(flag) != (by == "cap"):
            raise ValueError(f"{b}: capped {flag!r} by {by!r}; the k_O note covers only a k held at the cap")
        if by == "cap" and not (k == cap < raw):
            raise ValueError(f"{b}: k {k}, cap {cap}, raw k {raw} is not a k held at the cap")
        if by is None and k != raw:
            raise ValueError(f"{b}: uncapped, but k {k} is not its raw k {raw}")
        if by == "cap":
            capped.append(b)
    if not capped:
        raise ValueError("no k_O is capped: rewrite the k_O note")
    held: List[Cell] = []
    for b in capped:
        held += [label(", " if held else ""), label("held at the cap of "), integer(S.ref("main_k", f"{b}.cap")),
                 label(" on " + shape(b.rsplit(".", 1)[1]) + " (raw k "), integer(S.ref("main_k", f"{b}.raw_k")), label(")")]
    shapes_capped = [_cited(S.ref("main_k", f"k_from_rows.opus.{tests[t][2]}.capped_by"), "which shapes k.json caps, and by what")
                     for t in ("t1", "t2")]
    return _line(label("k_O is the Haiku-medium vote's k against Opus-medium at that shape, the k of Test 1 (6×1) and of Test 2 (1×6) in "
                       "TAB-02: its cost-matched k, "), *held, label("."), *shapes_capped)


def _c5_panel(S: Store) -> Table:
    cols = ["Quantity", "k", "Value (points)", "95% interval"]
    n = integer(S.ref("groupc", "item_C5.n_bases"))                  # the same in every row: a note, not a column
    # Tests 1 and 2 are printed from their confirmatory result (d and interval, as in TAB-02), not from C5's own copy of the two means:
    # one comparison, one interval (Edith's final check S1-09). Refuse to build unless C5's stamped means and k are exactly those.
    rows = []
    for t, sh, mean_key in (("t1", "6x1", "t1_mean_difference"), ("t2", "1x6", "t2_mean_difference")):
        tk = f"{VIEW}.tests.{t}"
        if (S.get("groupc", f"item_C5.{mean_key}") != S.get("main", f"{tk}.d")
                or S.get("groupc", f"item_C5.k_O.{sh}") != S.get("main_k", f"k_from_rows.opus.{sh}.k")):
            raise ValueError(f"C5's {t} mean or k is not the confirmatory one")
        rows.append([label(f"{STUDY1_TESTS[t][0]} ({shape(sh)}): Haiku-medium vote minus Opus-medium (confirmatory, as in TAB-02)"),
                     integer(S.ref("groupc", f"item_C5.k_O.{sh}")), pts(S.ref("main", f"{tk}.d"), margin=MARGIN),
                     interval(*ci_refs(S, "main", f"{tk}.ci95"), dp=2, signed=True, bounds=(0.0, MARGIN))])
    rows.append([label("Shape-by-setup interaction: Test 1 minus Test 2"), DASH, pts(S.ref("groupc", "item_C5.interaction")),
                 interval(*ci_refs(S, "groupc", "item_C5.ci95"), dp=2, signed=True, bounds=(0.0,))])
    # The stamped sign string names the tests t1/t2; the paper says "Test N" (style sheet), so the sign is typed from the design.
    for t, sh in (("t1", "6x1"), ("t2", "1x6")):
        if STUDY1_TESTS[t][1:4] != ("haiku-med", "opus-med", sh):
            raise ValueError(f"C5's sign note assumes {t} is the Haiku-medium vote against Opus-medium at {sh}")
    notes = [_k_o_note(S, "item_C5.k_O.{sh}"),
             [label("Sign: Test 1 (6×1) minus Test 2 (1×6), each the Haiku-medium vote at its k_O minus Opus-medium.")],
             [label("Tests 1 and 2's rows repeat their confirmatory d and interval (paired BCa bootstrap, as in TAB-02); the interaction's interval is "
                    "the shared cluster bootstrap.")],
             _line(label("C5 panel: "), n, label(" puzzles in every row."))]
    return Table([label(c) for c in cols], rows, notes, layout="float")


def _c7_panel(S: Store) -> Table:
    cols = ["Shape", "k_O", "Single-sample accuracy bin (%)", "Puzzles", "Haiku-medium single sample (%)", "Haiku-medium vote at k_O (%)",
            "Opus-medium (%)", "Vote reaches Opus within k_O", "Smallest k reaching Opus"]
    rows, notes = [], [_k_o_note(S, "item_C7.shapes.{sh}.k_O")]
    for sh in SHAPES:
        base = join_key("item_C7", "shapes", sh)
        k_o = integer(S.ref("groupc", f"{base}.k_O"))
        for bin_name in S.keys("groupc", f"{base}.bins"):
            bb = join_key("item_C7", "shapes", sh, "bins", bin_name)
            small = S.ref("groupc", f"{bb}.smallest_k_reaching_opus")
            rows.append([_shape_cell(sh), k_o, _key_cell("groupc", bb, bin_name), integer(S.ref("groupc", f"{bb}.puzzles")),
                         pct(S.ref("groupc", f"{bb}.haiku_med_single_try_mean"), dp=2), pct(S.ref("groupc", f"{bb}.mean_vote_at_k_O"), dp=2),
                         pct(S.ref("groupc", f"{bb}.opus_med_mean"), dp=2),
                         text_of(S.ref("groupc", f"{bb}.reaches_within_k_O"), YES_NO),
                         # the stamped words; the number stays with its "up to" (no-break spaces: Edith, proof 4, never "none up / to 40")
                         Cell(re.sub(r"(?<=\bup) (to) (?=\d)", rf"{_NBSP}\1{_NBSP}", small.value), raw=small.value, refs=(small,))
                         if isinstance(small.value, str) else integer(small)])
        notes.append(_line(*_stamped_in_quotes(S.ref("groupc", f"{base}.sentence"), shape(sh) + ", as stamped: ")))        # a full stop after each quotation (Edith, proof 3, p. 82)
    p = Table([label(c) for c in cols], rows, notes, layout="float")
    _groups(p, lambda r: r[0].printed)                      # the two shapes' bins apart
    # the last column ("none up to 40" beside 39 and 3) is set ragged-left like the value columns before it, so its integers stand right-aligned
    # (Edith, M2-8: Table S18's Panel 2); the writer's own width plan is kept
    from .paper_out_core import _width_plan
    specs, w, numeric = _width_plan(p)
    p.fixed_plan = (specs, w, {**numeric, len(cols) - 1: True})
    return p


def _c9_panel(S: Store) -> Table:
    cols = ["Shape", "k_O", "Spearman rho, wrong-sample agreement against vote gain", "95% interval", "Puzzles kept", "Puzzles left out (fewer than two wrong samples)"]
    rows = []
    for sh in SHAPES:
        b = join_key("item_C9", "shapes", sh)
        rows.append([_shape_cell(sh), integer(S.ref("groupc", f"{b}.k_O")), num(S.ref("groupc", f"{b}.rho"), dp=2, signed=True, bounds=(0.0,)),
                     interval(*ci_refs(S, "groupc", f"{b}.ci95"), dp=2, signed=True, bounds=(0.0,)),
                     integer(S.ref("groupc", f"{b}.n_kept")), integer(S.ref("groupc", f"{b}.n_left_out"))])
    notes = [_k_o_note(S, "item_C9.shapes.{sh}.k_O"),
             _line(label("The file's own words for the unit: \""), text_of(S.ref("groupc", "item_C9.shapes.1x6.unit")),
                   label("\"; the puzzles left out are counted, not used in the correlation."))]
    return Table([label(c) for c in cols], rows, notes, layout="float")


def _c10_panel(S: Store) -> Table:
    cols = ["Pair (low minus medium effort)", "Shape", "Low-effort accuracy (%)", "Low-effort format compliance (%)", "Medium-effort accuracy (%)",
            "Medium-effort format compliance (%)", "d (points)", "d 95% interval", "Low-effort list cost per sample ($)",
            "Medium-effort list cost per sample ($)", "Cost difference ($ per sample)"]
    rows = []
    n_exact = 0
    for a, b_ in (("haiku-low", "haiku-med"), ("opus-low", "opus-med")):
        for sh in SHAPES:
            p = join_key("item_C10", "pairs", f"{a}-vs-{b_}:{sh}")
            n_exact += _c10_exact_arms(S, p, a, b_)
            rows.append([joined(_arm_label(a), label("minus"), _arm_label(b_)), _shape_cell(sh),
                         _acc_with_exact(S, pct(S.ref("groupc", f"{p}.accuracy_means.{a}"), dp=2, from_proportion=False), "groupc", p, a),
                         _fc_cell(S, a, sh),
                         _acc_with_exact(S, pct(S.ref("groupc", f"{p}.accuracy_means.{b_}"), dp=2, from_proportion=False), "groupc", p, b_),
                         _fc_cell(S, b_, sh),
                         pts(S.ref("groupc", f"{p}.d")), _d_ci_cell(S, "groupc", f"{p}.ci95"),
                         usd(S.ref("groupc", f"{p}.cost_9b.{a}.mean")), usd(S.ref("groupc", f"{p}.cost_9b.{b_}.mean")),
                         usd(S.ref("groupc", f"{p}.cost_difference_usd"))])
    # The stamped cost_difference_note names arm ids and reads "(a Haiku arm at one sample)" on the Opus pairs too; the note is typed.
    notes = [_line(label("Costs are the mean list cost of one sample (for Opus, its one answer); the cost difference is low effort minus medium effort. The file's own words for the status: \""),
                   text_of(S.ref("groupc", "item_C10.exploratory")), label("\"."))]
    if not n_exact:          # TAB-06's caption names the exact per-arm intervals at the ceiling
        raise ValueError("TAB-06: no effort pair carries free analysis 4's exact per-arm intervals; rewrite the C10 note and the caption")
    notes.append([label("Where both settings are at the ceiling, the bootstrap interval of d collapses to one point (marked collapsed). The difference "
                        "itself has no exact interval in free analysis 4, which gives each setting's exact 95% interval instead (Clopper–Pearson over "
                        "puzzles), printed in that setting's accuracy cell as post hoc† (exact): a presentation only, not a test.")])
    p = Table([label(c) for c in cols], rows, notes)
    # eleven columns do not fit a landscape page at their minimum widths: two portrait parts (accuracies; the difference and the costs)
    _split(p, [["Shape", "Low-effort accuracy (%)", "Low-effort format compliance (%)", "Medium-effort accuracy (%)", "Medium-effort format compliance (%)"],
               ["Shape", "d (points)", "d 95% interval", "Low-effort list cost per sample ($)", "Medium-effort list cost per sample ($)",
                "Cost difference ($ per sample)"]], key=["Pair (low minus medium effort)"])
    _groups(p, lambda r: r[0].printed)                      # a pair's two shapes together (the writer carries the groups into the parts)
    return p


GROUP_C_TIER = ("pre-specified descriptive (keep-list definitions stamped before the data; computed after the confirmatory results "
                "were opened)")


def _group_c_tier(S: Store) -> Cell:
    """The keep-list (group C) rows' tier in the paper's words (Edith's Q19, with Karen), printed in place of the file's own label, which
    holds a decision number; the label stays the cell's source. Refuse to build unless the label still says the definitions were fixed
    and timestamped before the data and the analyses computed after the confirmatory results were opened."""
    r = S.ref("groupc", "label")
    if not (isinstance(r.value, str) and r.value.startswith("pre-specified descriptive (definition fixed and timestamped before the data")
            and "computed after the confirmatory results were opened" in r.value):
        raise ValueError(f"groupc label {r.value!r} no longer supports the group C tier wording")
    return Cell(label(GROUP_C_TIER).printed, raw=r.value, refs=(r,), formula="the stamped label, in the paper's words")


# PLAN NOTE (TAB-06): the plan's 'C9 ... per-puzzle counts' is read as the stamped counts of puzzles kept and left out (n_kept, n_left_out); the 80 per-puzzle
# rows inside item_C9.shapes[*].per_puzzle are not printed. C7 prints each bin with its stamped puzzles, shares and smallest k; the crossover sentences are notes.
@output("TAB-06")
def tab_06(S: Store) -> Table:
    t, n_puzzles = _c2_c3_main(S)
    _split(t, [["C2 statistic", "C2 correlation, 6×1 against 1×6", "C2 95% interval", "C2 undefined where"],
               ["C3 accuracy 1×6 (%)", "Format compliance 1×6 (%)", "C3 accuracy 6×1 (%)", "Format compliance 6×1 (%)",
                "C3 d: 6×1 minus 1×6 (points)", "C3 95% interval"]], key=["Setting"])      # the correlation; the paired difference
    # The groupc file's own label is not printed here: it holds a D-number and wording the paper does not use (TAB-22 maps it); the
    # caption's tier says the same in the paper's words. Draw counts are printed once: refuse to build if C2's and C9's differ.
    draws = {S.get("groupc", f"item_C2.arms.{a}.draws") for a in S.keys("groupc", "item_C2.arms")} | \
            {S.get("groupc", f"item_C9.shapes.{sh}.draws") for sh in S.keys("groupc", "item_C9.shapes")}
    if draws != {S.get("groupc", "item_C2.arms.haiku-med.draws")}:
        raise ValueError(f"C2/C9 draws differ: {draws}")
    t.notes = [
        [label("C2 is the correlation, across the puzzles, of each puzzle's accuracy at 6×1 and at 1×6 (Pearson for the Haiku settings, phi for one-sample settings); "
               "C3 is the paired difference 6×1 minus 1×6. A correlation is undefined where a setting has no variation at one shape (the cell shows the stamped text).")],
        _line(*_stamped_in_quotes(S.ref("groupc", "item_C2.definition"), "C2 definition, as stamped: ")),
        _line(*_stamped_in_quotes(S.ref("groupc", "item_C3.definition"), "C3 definition, as stamped: ")),
        [label("In the stamped texts (the C2 and C3 definitions and the C7 sentences), \"arm\" means setting, \"base puzzle\" and \"bases\" mean puzzle and puzzles, "
               "and \"try\" and \"tries\" mean sample and samples.")],
        _line(label("C2 and C3: "), n_puzzles, label(" puzzles in every row.")),
        [label("Format compliance is the share of the setting's answered samples in the required answer format at that shape (from the main analysis), "
               "beside each C3 accuracy.")],
    ]
    # Bootstrap draws in which C2's correlation was undefined are dropped from its interval: say so where an interval is printed from fewer
    # than all draws (the arms whose every draw was dropped have no interval: their cell is a dash).
    for arm in _C_ARMS:
        c2 = f"item_C2.arms.{arm}"
        dropped, n_draws = S.get("groupc", f"{c2}.draws_dropped_undefined"), S.get("groupc", f"{c2}.draws")
        if 0 < dropped < n_draws:
            t.notes.append(_line(label(f"{_arm_name(arm)}'s C2 interval leaves out the "), integer(S.ref("groupc", f"{c2}.draws_dropped_undefined")),
                                 label(" of "), integer(S.ref("groupc", f"{c2}.draws")),
                                 label(" bootstrap draws in which the correlation was undefined ("),
                                 pct(S.ref("groupc", f"{c2}.share_draws_dropped"), dp=2), label("% of the draws).")))
        elif dropped == n_draws and _get(S, "groupc", f"{c2}.ci95") not in (None, [None, None]):
            raise ValueError(f"C2 {arm}: every draw dropped, yet an interval is stamped")
    t.caption = _caption("", "Study 1, main run, 6 steps",
                         _line(label("puzzles: "), integer(S.ref("groupc", "item_C2.arms.haiku-med.n_bases")),
                               label("; samples per puzzle and shape as in TAB-04 (the Haiku settings' accuracies are means over their samples)")),
                         _line(label("95% intervals. Shared cluster bootstrap for C2, C3, the C5 interaction and C9 ("),
                               integer(S.ref("groupc", "item_C2.arms.haiku-med.draws")),
                               label(" draws, stamped on C2 and C9); paired BCa bootstrap for Tests 1 and 2 in the C5 panel (their confirmatory "
                                     "intervals, B = "), integer(S.ref("main", f"{VIEW}.B")), label(") and for the C10 effort pairs (B = "),
                               integer(S.ref("groupc", "item_C10.pairs.opus-low-vs-opus-med:1x6.B")),
                               label("); exact Clopper–Pearson for the post hoc per-setting intervals at the ceiling.")),
                         [label("list price (effort pairs)")], _set_cells(S))
    t.caption["tier"] = _line(_group_c_tier(S), label("; Tests 1 and 2's rows in the C5 panel repeat their confirmatory results; the C10 pairs "
                                                      "are exploratory; the exact per-setting intervals at the ceiling are post hoc"))
    t.panels = [("C5: shape-by-setup interaction (Tests 1 and 2)", _c5_panel(S)),
                ("C7: difficulty bins and the crossover", _c7_panel(S)),
                ("C9: wrong-sample agreement against vote gain", _c9_panel(S)),
                ("C10: effort pairs with cost differences", _c10_panel(S))]
    return t


# ================================================================ TAB-07 (pre-specified checks and flags)

_T7_COLS = ["Check", "Quantity", "Value", "Interval", "Interval level (%)", "Count", "Rule", "Stamped reading", "Fired"]
_GROUP_NAME = {"haiku": "Haiku", "opus": "Opus", "sonnet": "Sonnet", "opus+sonnet": "Opus and Sonnet pooled"}
_S1_FORMAT_ARMS = ("haiku-thinking-off", "haiku-low", "haiku-med", "haiku-max", "haiku-med-d42-variant", "opus-low", "opus-med",
                   "sonnet-low", "sonnet-med", "rt-haiku-med", "rt-opus-med", "rt-sonnet-med")
_S1B_SHAPE_ORDER = ("1x6", "6x1", "1x12", "12x1", "1x16", "16x1")


def _t7(check: str, quantity, value: Cell, ci: Cell, level: Cell, count: Cell, rule: Cell, reading: Cell, fired: Cell) -> List[Cell]:
    return [label(check), quantity if isinstance(quantity, Cell) else label(quantity), value, ci, level, count, rule, reading, fired]


def _level_pct(S: Store) -> Cell:
    """The fairness check's stamped interval level, printed as '90' (the header gives the unit, %)."""
    return pct(S.ref("main", "fairness.level"), dp=0)


def _puzzle_count(S: Store, source: str, prefix: str, key: str, field: str) -> Cell:
    """A row's puzzle count in D-161's unit (a puzzle is one puzzle in both shapes). A one-shape row's count prints as stamped. The
    pooled row's stamped count is both shapes' puzzles added, so it prints as the puzzles in each shape, and the build refuses unless
    the two shapes hold the same number and the pooled count is their sum (so a pooled 40 is never read as 40 puzzles)."""
    ref = S.ref(source, f"{prefix}.{key}.{field}")
    if key != "pooled":
        return joined(integer(ref), label("puzzles"), sep=_NBSP)
    a, b = (S.ref(source, f"{prefix}.{k}.{field}") for k in ("1x6", "6x1"))
    if a.value != b.value or ref.value != a.value + b.value:
        raise ValueError(f"{prefix}: the pooled count {ref.value} is not twice the per-shape count ({a.value}, {b.value})")
    return joined(integer(a), label("puzzles in each shape"), _cited(ref, "the pooled count, the two shapes' counts added"), sep=_NBSP)


def _fired(S: Store, key: str, source: str = "main") -> Cell:
    return text_of(S.ref(source, key), YES_NO)


def _format_flag_panel(S: Store, source: str, flags_key: str, order: List[str], name_of, notes: List[List[Cell]]) -> Table:
    cols = ["Setting", "Shape", "Answered samples", "Format ok", "Non-compliance (%)", "Fired"]
    present = set(S.keys(source, flags_key))
    rows, used = [], set()
    for key in order:
        if key not in present:
            continue
        used.add(key)
        b = join_key(*flags_key.split("."), key) if source == "main" else f"{flags_key}.{key}"
        arm, sh = key.rsplit(" ", 1)
        rows.append([label(name_of(arm)), _shape_cell(sh), integer(S.ref(source, f"{b}.answered")), integer(S.ref(source, f"{b}.format_ok")),
                     pct(S.ref(source, f"{b}.non_compliance"), dp=2), _fired(S, f"{b}.fires", source)])
    if used != present:
        raise ValueError(f"format flags not covered: {sorted(present - used)}")
    p = Table([label(c) for c in cols], rows, notes, layout="float")
    _groups(p, lambda r: r[0].printed)                      # a setting's shapes together
    return p


def _stamped_number_in(S: Store, source: str, key: str, pattern: str, group: int = 1) -> Cell:
    """A number written inside a stamped string (e.g. the format rule's '5%' in Study 1b's label), printed as written there; the pattern
    must match exactly once, so a changed string refuses the build."""
    r = S.ref(source, key)
    hits = list(re.finditer(pattern, r.value)) if isinstance(r.value, str) else []
    if len(hits) != 1:
        raise ValueError(f"{source}:{key}: {len(hits)} matches of {pattern!r}")
    return Cell(hits[0].group(group), raw=r.value, refs=(r,), formula=f"the number matched by {pattern!r} in this stamped string")


def _stamped_share_pct(S: Store, source: str, key: str, pattern: str, group: int, dp: int) -> Cell:
    """A share written as a proportion inside a stamped string ('1.00', '0.95') printed as the percentage the supplement prints
    everywhere else ('100.00%', '95%'; Edith, proof 5, B2-S6: an accuracy is never a bare proportion); the pattern must match once."""
    c = _stamped_number_in(S, source, key, pattern, group)
    return Cell(f"{Decimal(c.printed) * 100:.{dp}f}%", raw=c.raw, refs=c.refs,
                formula=f"100 times the proportion matched by {pattern!r} in this stamped string, to {dp} decimals")


def _plain_reason(r: Ref, prefix: str, printed: str) -> Cell:
    """A stamped reason string that holds code names (key names, a raw dict), printed in plain words. The stamped string must start
    with `prefix`, so a changed reason refuses the build; the plain words are typed and pass the label check."""
    if not (isinstance(r.value, str) and r.value.startswith(prefix)):
        raise ValueError(f"{r.source}:{r.key} = {r.value!r} does not start with {prefix!r}")
    return Cell(label(printed).printed, raw=r.value, refs=(r,), formula="the stamped reason, in plain words")


def _ti_house_reading(S: Store) -> Cell:
    """The house-variant targeting index's stamped reason ('not assessable at pilot scale: opus+sonnet short (0 exposed slips < 3;
    counts {...})') in plain words, its counts read from assess_counts and its minimum from the reason string."""
    b = "fairness.TI_house"
    reason = S.ref("main", f"{b}.assess_reason")
    if S.get("main", f"{b}.assessable") is not False or "opus+sonnet short" not in str(reason.value):
        raise ValueError(f"{b}: the plain reading assumes Opus and Sonnet pooled fell short: {reason.value!r}")
    ac = join_key("fairness", "TI_house", "assess_counts", "opus+sonnet")
    if f"({S.get('main', f'{ac}.exposed_slips')} exposed slips <" not in reason.value:
        raise ValueError(f"{b}: the stamped reason and assess_counts disagree")
    return joined(_plain_reason(reason, "not assessable", "not assessable: Opus and Sonnet pooled had "),
                  integer(S.ref("main", f"{ac}.exposed_slips")), label(" exposed slips in "), integer(S.ref("main", f"{ac}.exposed_steps")),
                  label(" exposed steps, fewer than the "), _stamped_number_in(S, "main", f"{b}.assess_reason", r"exposed slips < (\d+);"),
                  label(" the index needs"), sep="")


def _near_ceiling_rule(S: Store) -> Cell:
    """The near-ceiling label's stamped source ('the ladder: Opus-medium 40 of 40 at n = 6') in plain words: the length sweep's
    Opus-medium right answers at 6 steps per shape, read from the length-sweep file (Deviation 2's rule; the original-rule file agrees).
    Refuse to build unless the stamped source sentence is exactly what those counts give."""
    w = "models.om.by_n.6.whole_answer"
    got = {}
    for src in ("curve_d90", "curve"):
        got[src] = tuple(S.get(src, f"{w}.{f}.{x}") for f in ("1xn", "nx1") for x in ("right", "tries"))
    r1, t1, r2, t2 = got["curve_d90"]
    if got["curve"] != got["curve_d90"] or S.get("main", "reporting.group_b.item_15.source") != f"the ladder: Opus-medium {r1 + r2} of {t1 + t2} at n = 6":
        raise ValueError(f"near-ceiling source does not match the length sweep's Opus-medium counts {got}")
    return joined(label("set on the length sweep at 6 steps: Opus-medium right on "), integer(S.ref("curve_d90", f"{w}.1xn.right")),
                  label(" of "), integer(S.ref("curve_d90", f"{w}.1xn.tries")), label(" chains and "), integer(S.ref("curve_d90", f"{w}.nx1.right")),
                  label(" of "), integer(S.ref("curve_d90", f"{w}.nx1.tries")), label(" pieces"), sep="")


AS_RUN = " (as the analysis code applies it)"


def _flag_r_rule(S: Store) -> Cell:
    """Flag R's rule with its thresholds as the code that produced the file applies them (Edith's Q18: a threshold the result file
    does not stamp cites its code file and commit as the cell's source): the multiple from fairness.flag_r, the minimum pairs from the
    driver's call. Refuse to build unless the pre-registered plan states the same ('at least twice', 'at least 10 pairs in each'), the
    minimum applies to both kinds, and the stamped counts give the stamped outcome under these thresholds."""
    _code_ran(S)
    mult = _code_number(S, "s1_fairness_py", r"fires = agree_t > 0 and agree_t \* pairs_g >= (\d+) \* agree_g \* pairs_t$")
    minp = _code_number(S, "s1_main_analysis_py", r"pts\[\"pairs_g\"\], min_pairs=(\d+)\)\)$")
    _one_line(S, "s1_fairness_py", r"^    if pairs_t < min_pairs or pairs_g < min_pairs:$")
    p1 = _one_line(S, "s1_pilot_plan", r"^- \*\*Flag R\*\* \(repeats\): Haiku's same-slip agreement on T steps is at least twice its "
                                       r"agreement on G steps,$")
    m = re.fullmatch(r"with at least (\d+) pairs in each\.", S.get("s1_pilot_plan", f"L{p1 + 1}"))
    if not m or int(m.group(1)) != int(minp.printed) or int(mult.printed) != 2:
        raise ValueError("Flag R's thresholds in the code differ from the pre-registered plan's")
    fr = "reporting.flag_r"
    at, pt, ag, pg = (S.get("main", f"{fr}.{k}") for k in ("agree_t", "pairs_t", "agree_g", "pairs_g"))
    k, mn = int(mult.printed), int(minp.printed)
    if S.get("main", f"{fr}.flag_r.fires") != (pt >= mn and pg >= mn and at > 0 and at * pg >= k * ag * pt):
        raise ValueError("Flag R's stamped outcome does not follow from its stamped counts under the code's thresholds")
    return joined(label("fires when T-step agreement is at least "), mult, label(" times G-step agreement, with at least "), minp,
                  label(" pairs in each" + AS_RUN), sep="")


def _ti_rule(S: Store) -> Cell:
    """The targeting indices' rule (Flag K fires when either fires) with its thresholds as the code applies them, citing the code's
    assessability minima (not printed; the house variant's shortfall is in its reading). Refuse to build unless the pre-registered plan
    states the same thresholds and each index's stamped outcome follows from its stamped point, interval and assessability."""
    _code_ran(S)
    pat_ti = r"^FLAG_TI = (\d+\.\d+)$"
    pat_lo = r"val >= FLAG_TI and lo is not None and lo > (\d+\.\d+)\)$"
    ti, lo1 = _code_number(S, "s1_fairness_py", pat_ti), _code_number(S, "s1_fairness_py", pat_lo)
    _one_line(S, "s1_fairness_py", r"^        fires = bool\(a\[\"assessable\"\] and val is not None and val >= FLAG_TI and lo is not None")
    minima = [_cite(S, "s1_fairness_py", r"^    \"TI\": \{\"haiku\": \("), _cite(S, "s1_fairness_py", r"^    \"TI_house\": \{\"haiku\": \(")]
    pk = r"^- \*\*Flag K\*\* \(slips\): TI or TI_house ≥ (\d+), with the interval's lower end above (\d+)\. "
    m = re.match(pk, S.get("s1_pilot_plan", f"L{_one_line(S, 's1_pilot_plan', pk)}"))
    if float(m.group(1)) != float(ti.printed) or float(m.group(2)) != float(lo1.printed):
        raise ValueError("the targeting index thresholds in the code differ from the pre-registered plan's")
    for idx in ("TI", "TI_house"):
        b = f"fairness.{idx}"
        pt, (lo, _hi) = S.get("main", f"{b}.point"), S.get("main", f"{b}.ci90")
        want = bool(S.get("main", f"{b}.assessable") and pt is not None and pt >= float(ti.printed) and lo is not None
                    and lo > float(lo1.printed))
        if S.get("main", f"{b}.fires") != want:
            raise ValueError(f"{b}: the stamped outcome does not follow from the code's thresholds")
    return joined(label("fires when the index is assessable and its point is at least "), ti,
                  label(", with its interval's lower end above "), lo1,
                  label(AS_RUN[:-1] + ", which also sets the fewest slips and steps an index needs to be assessable)"), *minima, sep="")


def _low_info_rule(S: Store) -> Cell:
    """The low-information flag's rule with its threshold as the driver applies it; refuse to build unless Study 1's reporting
    definitions (item 5, stamped before any result was opened) state the same threshold and the stamped outcome follows from it."""
    _code_ran(S)
    thr = _code_number(S, "s1_main_analysis_py", r"fires = acc is not None and 100\.0 \* acc > (\d+\.\d+)$")
    h5 = _one_line(S, "s1_defs", r"^## 5\. The low-information flag$")
    pd = r"^\*\*It fires if that is strictly above (\d+\.\d+)%\.\*\*$"
    ln = _one_line(S, "s1_defs", pd)
    if not h5 < ln < _one_line(S, "s1_defs", r"^## 6\. ") or re.match(pd, S.get("s1_defs", f"L{ln}")).group(1) != thr.printed:
        raise ValueError("the low-information threshold in the code differs from the reporting definitions'")
    li = "reporting.low_information_flag"
    if S.get("main", f"{li}.fires") != (100 * S.get("main", f"{li}.haiku_med_accuracy") > float(thr.printed)):
        raise ValueError("the low-information flag's stamped outcome does not follow from the code's threshold")
    return joined(label("fires when that accuracy is above "), thr, label("%" + AS_RUN), sep="")


def _format_rule_note(S: Store) -> List[Cell]:
    """The format flag's rule, with its share read from Study 1b's stamped label; refuse to build unless every flag in both panels
    fires exactly when non-compliance is above that share (the Study 1 file stamps the flags but not the rule)."""
    lab = "descriptive.format_refusals_truncations_missing.label"
    pat = r"non-compliance above (\d+)% of answered tries"
    share = _stamped_number_in(S, "s1b", lab, pat)
    thr = int(share.printed) / 100
    for src, fk in (("main", "reporting.group_b.item_17.flags"), ("s1b", "descriptive.format_refusals_truncations_missing.item_17_flags")):
        for key, f in S.get(src, fk).items():
            if f["fires"] != (f["non_compliance"] > thr):
                raise ValueError(f"{src} format flag {key}: fires {f['fires']} at non-compliance {f['non_compliance']}")
    return _line(label("Flag rule, the same in both studies: the flag fires when non-compliance is above "), share,
                 label("% of answered samples."))


# Our work log's entry for the Study 1 driver run: the line TAB-23 reads the Study 1 analysis's code commit from, and that commit.
_S1_RUN_LINE = r"^`python3 -m harness\.analysis\.main_analysis "
_S1_RUN_COMMIT = r"checkout at ([0-9a-f]{7})[0-9a-f]*"


def _cited(r: Ref, why: str) -> Cell:
    """A cited line or stamped value with nothing printed: it joins the note's sources."""
    return Cell("", raw=r.value, refs=(r,), formula=f"cited (not printed): {why}")


def _code_commit_cites(S: Store) -> List[Cell]:
    """TAB-07's Rule note says the code-only thresholds are as the Study 1 analysis code applies them (the fairness check's code and
    the analysis driver) at the code commit TAB-23 lists for the Study 1 analysis. Refuse to build unless the code pins are the code the
    driver ran (`_code_ran`: the driver log committed with the result file names that commit) and our work log's entry for that driver
    run (the line TAB-23's code commit is read from) names the result file and one checkout, at the code pins' commit. In a build that
    loads the disclosure module (every full build), also refuse unless TAB-23's 'Study 1 analysis' row is the result file and reads its
    code commit from that same file, commit and line, giving the same commit. Returns the cited lines (not printed)."""
    _code_ran(S)
    n = _one_line(S, "s1_work_log", _S1_RUN_LINE)
    entry = S.get("s1_work_log", f"L{n}")
    got = re.findall(_S1_RUN_COMMIT, entry)
    pins = {S.sources[s].commit for s in ("s1_fairness_py", "s1_main_analysis_py")}
    if f"Output `{S.sources['main'].path}`" not in entry or len(got) != 1 or pins != {got[0]}:
        raise ValueError(f"our work log's Study 1 driver entry does not name one checkout at the code pins' commit {sorted(pins)}: {got}")
    dis = sys.modules.get(f"{__package__}.paper_out_disclosure")
    if dis is not None:
        rows = [r for r in dis.ANALYSES if r[0] == "Study 1 analysis"]
        if len(rows) != 1 or rows[0][1] != "main" or rows[0][2] is None:
            raise ValueError("TAB-23 has no one 'Study 1 analysis' row for the result file with a code commit read from a record")
        tsrc, line_rx, cut = rows[0][2]
        mine, theirs = S.sources["s1_work_log"], S.sources.get(tsrc)
        if theirs is None or (theirs.path, theirs.commit, theirs.sha256) != (mine.path, mine.commit, mine.sha256):
            raise ValueError(f"TAB-23 reads the Study 1 analysis's code commit from {tsrc}, not the work log pinned here")
        m = re.search(cut, entry)
        if S.find_lines("s1_work_log", line_rx) != [n] or not m or m.group(1) != got[0]:
            raise ValueError("TAB-23's code commit for the Study 1 analysis is not the one this note relies on")
    log_pat = r"now: ([0-9a-f]{40})\)"
    return [_cited(S.ref("s1_work_log", f"L{n}"), "the Study 1 driver run's entry, which names the commit its checkout was at "
                                                   "(TAB-23's code commit for the Study 1 analysis)"),
            _cited(S.ref("s1_driver_log", f"L{_one_line(S, 's1_driver_log', log_pat)}"),
                   "the driver's console log, committed with the result file: the commit it ran at")]


def _assessable_minimum_note(S: Store) -> List[Cell]:
    """The house variant's reading says the comparison had fewer exposed slips than 'the 3 the index needs'. That 3 is set by the code
    alone (fairness.MINIMA, the house index's comparison entry, its second field); the pre-registered plan states the comparison's
    minimum as 'at least 10, with at least 5 in each group' and says 'The same rule applies to the house index, with house slips as one
    group'. The 3 is read from the code line, the 5 from the plan's line, the 0 from the stamped counts. Refuse to build unless the
    code's tuple fields are as its comment names them, the plan's lines are the ones read here, the stamped reason's minimum is the
    code's, the plan's number is not the code's, the comparison is Opus and Sonnet pooled, and the stamped exposed slips fall short of
    both numbers."""
    _code_ran(S)
    c = _one_line(S, "s1_fairness_py", r"^# Enough data, per index and role: \(min slips over both groups, min exposed slips, min G slips, "
                                        r"min steps in each group\)\.$")
    # Text lines are read stripped of their indent, so the number's pattern is not anchored at the indent; the layout check is.
    pat_code = r'"TI_house": \{"haiku": \(\d+, \d+, \d+, \d+\), "comparison": \(\d+, (\d+), \d+, \d+\)\},$'
    if (_one_line(S, "s1_fairness_py", r"^MINIMA = \{$") != c + 1
            or _one_line(S, "s1_fairness_py", r"^    \"TI\": \{\"haiku\": \(") != c + 2
            or _one_line(S, "s1_fairness_py", "^    " + pat_code) != c + 3):
        raise ValueError("fairness.MINIMA is not laid out as this note reads it")
    code_min = _code_number(S, "s1_fairness_py", pat_code)
    e = _one_line(S, "s1_pilot_plan", r"^- \*\*Enough data\?\*\*$")
    pat_plan = r"^    model at least \d+, with \*\*at least (\d+) in each group\*\* \(Edith's rule\)\.$"
    if (_one_line(S, "s1_pilot_plan", r"^  - Flag K is assessed only if Haiku has at least \d+ slips \(at least \d+ in each group\), and the "
                                      r"comparison$") != e + 1
            or _one_line(S, "s1_pilot_plan", pat_plan) != e + 2
            or _one_line(S, "s1_pilot_plan", r" The same rule applies to the house index, with house slips as$") != e + 4
            or _one_line(S, "s1_pilot_plan", r"^    one group\.$") != e + 5):
        raise ValueError("the pre-registered plan's minimum for the house index is not where this note reads it")
    plan_min = _stamped_number_in(S, "s1_pilot_plan", f"L{e + 2}", r"with \*\*at least (\d+) in each group\*\*")
    # "The plan states no such number": no line of its enough-data block (up to the next top-level item) asks for the code's number.
    end = min(n for n in S.find_lines("s1_pilot_plan", r"^- \*\*") if n > e)
    if any(re.search(rf"(?:at least|≥) ?{code_min.printed}\b", S.get("s1_pilot_plan", f"L{n}")) for n in range(e + 1, end)):
        raise ValueError("the pre-registered plan's enough-data block states the code's house minimum")
    b = "fairness.TI_house"
    ac = join_key("fairness", "TI_house", "assess_counts", "opus+sonnet")
    slips = S.get("main", f"{ac}.exposed_slips")
    if (S.get("main", "fairness.comparison").get("TI_house") != "opus+sonnet" or S.get("main", f"{b}.assessable") is not False
            or _stamped_number_in(S, "main", f"{b}.assess_reason", r"exposed slips < (\d+);").printed != code_min.printed
            or int(plan_min.printed) == int(code_min.printed)
            or not slips < min(int(code_min.printed), int(plan_min.printed))):
        raise ValueError("the house variant's minimum note no longer fits the code, the plan or the stamped counts")
    cites = [_cited(S.ref("s1_fairness_py", f"L{c}"), "the code's names for the minimum fields (the second is the fewest exposed slips)"),
             _cited(S.ref("main", f"{b}.assess_reason"), "the house variant's stamped reason, whose minimum is the code's"),
             *[_cited(S.ref("s1_pilot_plan", f"L{e + k}"), "the pre-registered plan's minimum and its rule for the house index")
               for k in (1, 4, 5)]]
    return _line(label("Assessability: the fewest slips and steps an index needs to be assessable are as the analysis code sets them. For "
                       "the house variant it asks the comparison (Opus and Sonnet pooled) for at least "), code_min,
                 label(" exposed slips, the number in its reading; the pre-registered plan states no such number, and applies its general "
                       "rule to the house index, which asks the comparison for at least "), plan_min,
                 label(" slips in each group, with its house-rule slips as one group. With "), integer(S.ref("main", f"{ac}.exposed_slips")),
                 label(" exposed slips, the house variant is not assessable under either number."), *cites)


# PLAN NOTE (TAB-07): the 'rule' column holds stamped text where the files stamp a rule (same-model flag; the near-ceiling label's source, in
# plain words; the format rule in the panels' note). For Flag R, Flag K and the low-information flag the result file stamps no threshold: the
# cell prints each as the code that produced the file applies it, read from that code's pinned lines (Edith's Q18: the cell's source names the
# code file and commit), and the build refuses unless the pre-registered plan or the reporting definitions state the same threshold and the
# stamped outcome follows from it. The Rule note names that code and its commit in words the paper defines (the code commit TAB-23
# lists for the Study 1 analysis); the Assessability note says the minima are the code's, and that the house variant's 3 is in no plan
# text (the plan applies its general rule to the house index). Flag R's intervals carry no stamped level field,
# so the level is read from the key name 'ci90'. Format flags (Study 1, Study 1b) are panels. TAB-07 is a main-text table: no item numbers, key
# names, code file names, run ids or D-numbers are printed, and stamped strings that hold them are put in plain words.
@output("TAB-07")
@main_text
def tab_07(S: Store) -> Table:
    rows: List[List[Cell]] = []
    lvl90 = _level_pct(S)

    # ---- Flag R
    fr = "reporting.flag_r"
    for scope, key, qual in (("pooled", "pooled", "both shapes"), ("1x6", "1x6", "1×6"), ("6x1", "6x1", "6×1")):
        for which, name in (("agreement_T", "T steps"), ("agreement_G", "G steps")):
            b = f"{fr}.{key}.{which}"
            rows.append(_t7("Flag R", f"Haiku-medium same-slip pairwise agreement on {name}, {qual} (%)", pct(S.ref("main", f"{b}.point"), dp=2),
                            interval(*ci_refs(S, "main", f"{b}.ci90"), dp=2, scale=100.0), _level_from_key("main", f"{b}.ci90"),
                            joined(integer(S.ref("main", f"{b}.pairs")), label("pairs"), sep=_NBSP), DASH, EMPTY, DASH))
    rows.append(_t7("Flag R", "Flag R: agreement on T steps against G steps (pooled)", DASH, DASH, DASH,
                    joined(joined(integer(S.ref("main", f"{fr}.pairs_t")), label(f"T{_NBSP}pairs,"), sep=_NBSP),
                           joined(integer(S.ref("main", f"{fr}.pairs_g")), label(f"G{_NBSP}pairs"), sep=_NBSP)),
                    _flag_r_rule(S),
                    text_of(S.ref("main", f"{fr}.flag_r.reason")), _fired(S, f"{fr}.flag_r.fires")))

    # ---- fairness check (exploratory): targeting indices, slip-rate ratios, Opus counts, Flag K
    ti_rule = _ti_rule(S)
    for idx in ("TI", "TI_house"):
        b = f"fairness.{idx}"
        reading = (text_of(S.ref("main", f"{b}.assess_reason"), {"assessable": "assessable"}) if S.get("main", f"{b}.assessable")
                   else _ti_house_reading(S) if idx == "TI_house" else None)
        if reading is None:
            raise ValueError(f"{b} is not assessable: no plain reading is written for it")
        comp = S.get("main", f"{b}.comparison")
        if S.get("main", join_key("fairness", idx, "correction_point", "haiku")) is not False:
            raise ValueError(f"{b}: the quantity marks only the comparison's zero-slip correction, but Haiku's is corrected too")
        rows.append(_t7("Fairness check", joined(label("Targeting index (ratio" if idx == "TI" else "Targeting index, house variant (ratio"),
                                                text_of(S.ref("main", join_key("fairness", idx, "correction_point", comp)),
                                                        {True: "; the comparison's ratio zero-slip corrected", False: ""}),
                                                label(") against "), text_of(S.ref("main", f"{b}.comparison"), _GROUP_NAME), sep=""),
                        num(S.ref("main", f"{b}.point"), dp=2), interval(*ci_refs(S, "main", f"{b}.ci90"), dp=2), lvl90, DASH,
                        ti_rule,
                        reading, _fired(S, f"{b}.fires")))
    if S.get("main", "fairness.flag_k.fires") is not False or S.get("main", "fairness.TI.fires") or S.get("main", "fairness.TI_house.assessable"):
        raise ValueError("Flag K's plain reading assumes it does not fire because the house-variant index is not assessable")
    rows.append(_t7("Fairness check", "Flag K (either index fires)", DASH, DASH, DASH, DASH, DASH,
                    _plain_reason(S.ref("main", "fairness.flag_k.reason"), "does not fire (TI_house not assessable",
                                  "does not fire (the targeting index does not fire; the house variant is not assessable)"),
                    _fired(S, "fairness.flag_k.fires")))
    for rr, nm in (("RR", "Slip-rate ratio, T steps over G steps"), ("RR_house", "Slip-rate ratio, house variant (missed house-rule steps over G steps)")):
        for grp in ("haiku", "opus", "sonnet", "opus+sonnet"):
            b = join_key("fairness", rr, grp)
            # A ratio whose model had no slips in one group carries the locked zero-slip correction (the stamped 'corrected' flag).
            quantity = joined(label(f"{nm}: {_GROUP_NAME[grp]} (ratio"),
                              text_of(S.ref("main", f"{b}.corrected"), {True: "; zero-slip corrected", False: ""}), label(")"), sep="")
            rows.append(_t7("Fairness check", quantity, num(S.ref("main", f"{b}.point"), dp=2),
                            interval(*ci_refs(S, "main", f"{b}.ci90"), dp=2), lvl90, DASH, DASH, EMPTY, DASH))
    oc = "fairness.counts.opus"
    rows.append(_t7("Fairness check", "Opus: slips on T steps, of steps checked (counts)", joined(integer(S.ref("main", f"{oc}.T_slips")), label("of"),
                                                                                                  integer(S.ref("main", f"{oc}.T_steps"))), DASH, DASH, DASH, DASH, EMPTY, DASH))
    rows.append(_t7("Fairness check", "Opus: slips on G steps, of steps checked (counts)", joined(integer(S.ref("main", f"{oc}.G_slips")), label("of"),
                                                                                                  integer(S.ref("main", f"{oc}.G_steps"))), DASH, DASH, DASH, DASH, EMPTY, DASH))
    rows.append(_t7("Fairness check", "Opus: house-rule slips missed, of steps that should fire (counts)",
                    joined(integer(S.ref("main", f"{oc}.house_missed")), label("of"), integer(S.ref("main", f"{oc}.house_should_fire"))),
                    DASH, DASH, DASH, DASH, EMPTY, DASH))

    # ---- low-information flag and near-ceiling label
    li = "reporting.low_information_flag"
    rows.append(_t7("Low-information flag", "Haiku-medium single-sample accuracy at 6×1 (pieces), mean over puzzles (%)", pct(S.ref("main", f"{li}.haiku_med_accuracy"), dp=2),
                    DASH, DASH, DASH, _low_info_rule(S),
                    text_of(S.ref("main", f"{li}.label_test_1")), _fired(S, f"{li}.fires")))
    rows.append(_t7("Low-information flag", "Median over puzzles of the same accuracy (%)", pct(S.ref("main", f"{li}.median"), dp=2), DASH, DASH, DASH, DASH, EMPTY, DASH))
    i15 = "reporting.group_b.item_15"
    beside = ", ".join(STUDY1_TESTS[t][0] for t in S.get("main", f"{i15}.beside_tests"))
    rows.append(_t7("Near-ceiling label", f"Opus-medium pooled accuracy, main run (%) (label shown beside {beside})",
                    pct(S.ref("main", f"{i15}.opus_med_pooled_accuracy_main_run.mean"), dp=2),
                    interval(*ci_refs(S, "main", f"{i15}.opus_med_pooled_accuracy_main_run.ci95"), dp=2, scale=100.0),
                    _level_from_key("main", f"{i15}.opus_med_pooled_accuracy_main_run.ci95"),
                    joined(integer(S.ref("main", f"{i15}.opus_med_pooled_accuracy_main_run.n_base")), label("puzzles"), sep=_NBSP), _near_ceiling_rule(S),
                    text_of(S.ref("main", f"{i15}.label")), _fired(S, f"{i15}.on")))

    # ---- rewording check: a check with no verdict stamped. Two decimals, as for every other difference in points; the lower ends are
    # floating-point zeros and print as 0.00 without a sign (Edith, E-07: no extra decimal for a true zero).
    rw = "reporting.d42_robustness"
    for key, qual in (("pooled", "both shapes"), ("1x6", "1×6"), ("6x1", "6×1")):
        b = f"{rw}.{key}"
        rows.append(_t7("Rewording check", f"Reworded prompt minus Haiku-medium on the same puzzles, {qual} (points)",
                        _share_pts(S.ref("main", f"{b}.difference"), dp=2, signed=True),
                        interval(*ci_refs(S, "main", f"{b}.difference_ci95"), dp=2, signed=True, scale=100.0),
                        _level_from_key("main", f"{b}.difference_ci95"),
                        _puzzle_count(S, "main", rw, key, "puzzles"), DASH, EMPTY, DASH))
    zero_ends = [k for k in ("pooled", "1x6", "6x1") if abs(S.get("main", f"{rw}.{k}.difference_ci95")[0]) < 1e-12]

    # ---- the drift check between runs (the top-up's re-run of Haiku-medium at the main run's settings): a flag, not a gate
    sm = "same_model_check"
    for key, qual in (("pooled", "both shapes"), ("1x6", "1×6"), ("6x1", "6×1")):
        b = f"{sm}.{key}"
        rows.append(_t7("Drift check (top-up)", f"Top-up minus main run, Haiku-medium, {qual} (points)", pts(S.ref("topup", f"{b}.d")),
                        interval(*ci_refs(S, "topup", f"{b}.ci95"), dp=2, signed=True, bounds=(0.0,)), _level_from_key("topup", f"{b}.ci95"),
                        _puzzle_count(S, "topup", sm, key, "n_puzzles"), DASH, EMPTY, DASH))
    rows.append(_t7("Drift check (top-up)", "Mean output tokens, relative change top-up against main (%)",
                    _share_pts(S.ref("topup", f"{sm}.output_tokens.relative_change"), dp=2, signed=True),
                    DASH, DASH, DASH, DASH, EMPTY, _fired(S, f"{sm}.flag.tokens_condition", "topup")))
    rows.append(_t7("Drift check (top-up)", "Accuracy condition", DASH, DASH, DASH, DASH, DASH, EMPTY, _fired(S, f"{sm}.flag.accuracy_condition", "topup")))
    rule = text_of(S.ref("topup", f"{sm}.flag.rule"))
    # the stamped rule's "|d| > 10 points" is one piece: no line break inside it (no-break spaces; Edith, proof 4, p. 59)
    rule = Cell(rule.printed.replace(" > ", f"{_NBSP}>{_NBSP}"), raw=rule.raw, refs=rule.refs)
    rows.append(_t7("Drift check (top-up)", "Drift-check flag", DASH, DASH, DASH, DASH, rule,
                    text_of(S.ref("topup", f"{sm}.flag.status")), _fired(S, f"{sm}.flag.fires", "topup")))

    # The terms, in plain words, from the fairness check's locked definition (research/pilot-plan-ledger.md, "Fairness check"; harness/
    # analysis/fairness.py) and Flag R's inputs (research/reporting-definitions-main.md item 4; main_analysis.flag_r_report): Flag R reads
    # Haiku-medium's tries; the fairness check's models are Haiku-medium, Opus-medium and Sonnet-medium (main_analysis.FAIRNESS_MODELS).
    # Refuse to build unless both indices compare with Opus and Sonnet pooled and the house variant's exposed counts are its should-fire
    # steps and misses (so the note's 'exposed' wording holds).
    hc = "fairness.TI_house.assess_counts"
    if (S.get("main", "fairness.comparison") != {"TI": "opus+sonnet", "TI_house": "opus+sonnet"}
            or S.get("main", f"{hc}.haiku.exposed_steps") != S.get("main", "fairness.counts.haiku.house_should_fire")
            or S.get("main", f"{hc}.haiku.exposed_slips") != S.get("main", "fairness.counts.haiku.house_missed")):
        raise ValueError("the fairness terms note no longer fits the stamped comparison or exposed counts")
    notes = [
        [label("Checks and flags, not tests. Each Quantity cell names its unit: % for shares and accuracies, points for differences, ratios and counts "
               "as named. Dashes mark cells with no stamped value for that column.")],
        [label("Terms. A slip is a step whose written balances differ from that step's rule applied to the model's own previous balances. T steps "
               "are steps of the targeted rule kinds: kinds added, or made more frequent, where Haiku slipped while the puzzles were tuned; G "
               "steps are steps of the other kinds. Same-slip pairwise agreement (Flag R): among pairs of Haiku-medium "
               "samples that slip at the same step of the same puzzle (on a chain only its first slip counts, on pieces every slipped piece), the "
               "share that wrote the same wrong balances there. Slip-rate ratio: a model's slip rate on T steps divided by its slip rate on G "
               "steps. House variant: the house rule is a puzzle-wide rule that should act on some steps; the ratio's numerator is the share "
               "of those steps (the exposed steps) where the model missed it (the exposed slips). Targeting index: Haiku-medium's ratio divided "
               "by the comparison's ratio, here Opus-medium and Sonnet-medium pooled; near one means the T kinds are no harder for Haiku in "
               "particular. Zero-slip corrected: the model had no slips in one group, so half a slip was added to both groups' counts before "
               "dividing, which pulls the ratio towards one.")],
        # Edith's Q18: the note says where the code-only thresholds come from (the code and its commit), in words a reader can follow
        # from the paper itself (TAB-23 prints the commit); the cited lines guard that wording and join the note's sources.
        _line(label("Rule column: the rule text is stamped for the flag of the drift check between runs and for the near-ceiling label's source (given in plain words), and the "
                    "format flag's rule is stamped and given under the format panels. For Flag R, the targeting indices behind Flag K and the "
                    "low-information flag, the result file stamps no threshold: the Rule cell gives each threshold as the Study 1 analysis code that "
                    "produced the result file applies it (the fairness check's code and the analysis driver, at the code commit TAB-23 lists for "
                    "the Study 1 analysis). The thresholds printed in those Rule cells are the ones the pre-registered plan (Flag R and Flag K) and "
                    "Study 1's reporting definitions (the low-information flag) state. The stamped reading column repeats the files' own reason "
                    "strings, in plain words where they hold code names."), *_code_commit_cites(S)),
        _assessable_minimum_note(S),
        [label("The rewording check (a robustness check planned in the pre-registered design, outside the confirmatory tests; no test): its wording, "
               "puzzles and comparison were fixed after Lock 3, before any result was opened. It was checked on Haiku-medium single samples only.")],
        _near_ceiling_note(S, where=" (in TAB-02)"),
        # Edith's N-4, in the paper's words (its Study 1 appendix): the stamped booleans stay the sentence's sources, printed as nothing
        # and refusing the build if either changes.
        _line(label("The near-ceiling label was set from the length sweep (Amendment 1) and was not re-decided afterwards"),
              text_of(S.ref("main", f"{i15}.re_decided_on_main_run"), {False: ""}),
              label("; the main run's Opus-medium pooled score (the near-ceiling row) is shown for information only"),
              text_of(S.ref("main", f"{i15}.for_information_only"), {True: ""}), label(".")),
        [label("The fairness check's first-slip variant is a separate stamped sensitivity and is not shown here.")],
    ]
    if zero_ends:
        notes.insert(4, [label("The rewording check's lower interval ends at zero are floating-point zeros in the file (exact zeros up to rounding error), printed as zero without a sign.")])
    fmt_note = [_format_rule_note(S)]
    p1 = _format_flag_panel(S, "main", "reporting.group_b.item_17.flags", [f"{a} {sh}" for a in _S1_FORMAT_ARMS for sh in SHAPES],
                            _arm_name, fmt_note)
    b_order = [f"{tag} {sh}" for tag in STUDY1B_TAGS for sh in _S1B_SHAPE_ORDER]
    p2 = _format_flag_panel(S, "s1b", "descriptive.format_refusals_truncations_missing.item_17_flags", b_order,
                            lambda a: STUDY1B_TAGS[a][0], fmt_note)
    caption = _caption("pre-specified checks (flags, not tests); the fairness check is exploratory", "Study 1, main run, 6 steps (format flags also Study 1b; the drift check between runs from the top-up)",
                       _line(label("puzzles for the fairness check: "), integer(S.ref("main", "fairness.presets.l14n6")),
                             label("; the other rows give their own pairs, puzzles or samples")),
                       _line(label("fairness check and Flag R: percentile bootstrap at level "), pct(S.ref("main", "fairness.level"), dp=0),
                             label("%, B = "), integer(S.ref("main", "fairness.B")), label("; other intervals 95%")),
                       [label("not applicable (no costs)")], _set_cells(S))
    t = Table([label(c) for c in _T7_COLS], rows, notes, caption)
    p2.layout = "longtable"                                  # 50 rows: one block of about a page, so it breaks across pages
    t.panels = [("Format flags, Study 1", p1), ("Format flags, Study 1b", p2)]
    # supplement layout: 33 rows with long rule texts are far taller than a landscape page (19 in), so five landscape parts by row, in
    # the table's row order (Flag R; the fairness check's targeting indices and Flag K, which carry a rule; the fairness check's
    # ratios and counts; the low-information flag and the near-ceiling label; the rewording and drift checks). The columns a part
    # leaves out hold only dashes in its rows (the build refuses otherwise).
    chk = [r[0].printed for r in rows]
    flag_r = [i for i, c in enumerate(chk) if c == "Flag R"]
    fair = [i for i, c in enumerate(chk) if c == "Fairness check"]
    flags = [i for i, c in enumerate(chk) if c in ("Low-information flag", "Near-ceiling label")]
    later = [i for i, c in enumerate(chk) if c == "Rewording check" or c.startswith("Drift check")]
    if (flag_r + fair + flags + later != list(range(len(rows))) or "Targeting index" not in rows[fair[0]][1].printed
            or "Flag K" not in rows[fair[2]][1].printed):
        raise ValueError("TAB-07's rows are not the blocks its split names, in row order")
    every = ["Value", "Interval", "Interval level (%)", "Count", "Rule", "Stamped reading", "Fired"]
    # Edith, proof 3, pp. 55-57: every part holds every column, with one shared set of column widths, and the rows are cut by space
    # (core.split_rows_by_space: the fewest sideways parts that fit, rows spread evenly), so the table keeps one column layout from page
    # to page and no page is mostly empty; a check's name prints once per group (and again at the top of a part)
    _groups(t, lambda r: r[0].printed)                      # a check's rows together (the writer carries the groups into the parts)
    t.once, t.font = [0], "footnotesize"                  # 8 pt: the long rule texts wrap to fewer lines (the house floor)
    heads = [c.printed for c in t.columns]
    split_rows_by_space(t, [heads.index("Check"), heads.index("Quantity")], [heads.index(c) for c in every])
    return t


# ================================================================ TAB-08 (escalate-to-Opus cascade, offline simulation; item 9e)


def _usd4(r: Ref, signed: bool = False) -> Cell:
    """A per-puzzle cost or cost difference in US$ to four decimals, with the one-more-decimal guard at zero."""
    return num(r, dp=4, signed=signed, bounds=(0.0,))


# The header of the Opus-medium cost column, with "puzzle ($)" tied: in the second part the rebalanced widths wrapped it as "Opus-medium /
# cost per puzzle / ($)", leaving "($)" alone on a line (proof 4, group 1 check). The split below finds its columns by printed title,
# so the one string is used in both places.
_T8_OPUS_COST = "Opus-medium cost per puzzle" + _NBSP + "($)"


@output("TAB-08")
def tab_08(S: Store) -> Table:
    cols = ["Shape", "k_c", "τ", "Rule for τ", "Cascade accuracy (%)", "Cascade accuracy 95% interval",
            "Opus-medium accuracy (%)", "Opus-medium accuracy 95% interval", "d: cascade minus Opus (points)", "d 95% interval",
            "Escalation rate (%)", "Cascade cost per puzzle ($)", "Cascade cost 95% interval ($)", _T8_OPUS_COST,
            "Opus-medium cost 95% interval ($)", "Cost difference ($ per puzzle)",
            "Cost difference, lower end of the 95% interval ($)", "Cost difference, upper end of the 95% interval ($)"]
    rows, odd = [], []
    base = "reporting.group_b.item_9e.shapes"
    as_above = label("as above")
    collapsed_shapes: List[str] = []
    for sh in SHAPES:
        sizes = sorted((k for k in S.keys("main", join_key("reporting", "group_b", "item_9e", "shapes", sh)) if k.isdigit()), key=int)
        # Opus-medium's accuracy and cost on the even bases are one estimate per shape, the same in every k_c row; each row's bootstrap
        # (named cascade:<shape>:<k_c>) gives it a slightly different interval. One estimate, one interval (Edith's final check S1-03):
        # they are printed once per shape, in its first k_c row, and the later rows say 'as above'. Refuse to build unless the points agree.
        evs = [join_key("reporting", "group_b", "item_9e", "shapes", sh, kc, "even") for kc in sizes]
        for f in ("opus_accuracy", "opus_mean_cost"):
            if len({S.get("main", f"{e}.{f}") for e in evs}) != 1:
                raise ValueError(f"item 9e {sh}: Opus-medium's {f} differs between the k_c rows")
        for i, kc in enumerate(sizes):
            b = join_key("reporting", "group_b", "item_9e", "shapes", sh, kc)
            ev = f"{b}.even"
            if i == 0:
                olo, ohi = S.get("main", f"{ev}.opus_accuracy_ci95")
                if olo == ohi:            # a zero-width bootstrap interval: free analysis 4 (revision 3) gives its exact replacement
                    collapsed_shapes.append(sh)
                    ex = fa4_exact(S, "main", ev, field="opus_accuracy_ci95")
                    if ex is None or ex.scale != 1.0:
                        raise ValueError(f"item 9e {sh}: the collapsed Opus-medium interval has no exact replacement in points in fa4")
                    if ex.n != S.get("main", f"{b}.even_bases"):
                        raise ValueError(f"item 9e {sh}: fa4's n {ex.n} is not the stamped even bases")
                    opus_ci = joined(interval(ex.lo, ex.hi, dp=2), label(" post hoc† (exact)"), sep="")
                else:
                    opus_ci = interval(*ci_refs(S, "main", f"{ev}.opus_accuracy_ci95"), dp=2)
                opus = [pct(S.ref("main", f"{ev}.opus_accuracy"), dp=2, from_proportion=False), opus_ci]
                opus_cost = [usd(S.ref("main", f"{ev}.opus_mean_cost")), _usd_interval(*ci_refs(S, "main", f"{ev}.opus_mean_cost_ci95"))]
            else:
                opus, opus_cost = [as_above, as_above], [as_above, as_above]
            rows.append([_shape_cell(sh), _key_cell("main", b, kc, as_int=True), num(S.ref("main", f"{b}.recommended_tau"), dp=1),
                         _stamped_in_quotes(S.ref("main", f"{b}.rule"), tail="")[0],             # the file's own words ("bases")
                         pct(S.ref("main", f"{ev}.cascade_accuracy"), dp=2, from_proportion=False),
                         interval(*ci_refs(S, "main", f"{ev}.cascade_accuracy_ci95"), dp=2),
                         *opus,
                         pts(S.ref("main", f"{ev}.accuracy_difference")),
                         interval(*ci_refs(S, "main", f"{ev}.accuracy_difference_ci95"), dp=2, signed=True, bounds=(0.0,)),
                         pct(S.ref("main", f"{ev}.cascade_escalation_rate"), dp=2),
                         usd(S.ref("main", f"{ev}.cascade_mean_cost")), _usd_interval(*ci_refs(S, "main", f"{ev}.cascade_mean_cost_ci95")),
                         *opus_cost,
                         _usd_signed(S.ref("main", f"{ev}.cost_difference")),
                         *[_usd_end(r) for r in ci_refs(S, "main", f"{ev}.cost_difference_ci95")]])    # one column per end: decimal-aligned (§2.8)
            odd.append(pct(S.ref("main", f"{b}.opus_odd_accuracy"), dp=2, from_proportion=False))      # the same in every row: a note
    if collapsed_shapes != ["6x1"]:
        raise ValueError(f"the note names 6x1 as the only shape whose Opus-medium interval collapsed: {collapsed_shapes}")
    sh0 = join_key("reporting", "group_b", "item_9e", "shapes", "1x6")
    first = [k for k in S.keys("main", sh0) if k.isdigit()][0]
    notes = [
        _line(label("Offline simulation: the cascade takes a vote of k_c Haiku-medium samples and escalates to Opus-medium when the top answer's share is below τ. "
                    "τ is chosen on the odd-numbered puzzles; the cascade and Opus-medium are compared on the even-numbered puzzles. "
                    "Every column except τ and its rule is on the even-numbered puzzles. The file's own label, in its words: \""),
              text_of(S.ref("main", "reporting.group_b.item_9e.label")), label("\"; its units: \""), text_of(S.ref("main", "reporting.group_b.item_9e.unit")),
              label("\".")),
        [label("The Rule for τ column is the file's own text, in quotation marks (its \"bases\" are puzzles): where no τ came within the margin on the "
               "odd-numbered puzzles, the highest accuracy on them was taken.")],
        _line(label("Opus-medium's accuracy on the odd-numbered puzzles is "), _same_in_every_row(odd), label("% in every row.")),
        [label("No test and no verdict: d is a point difference with an unadjusted 95% interval.")],
        [label("Opus-medium's accuracy and cost on the even-numbered puzzles are the same in every k_c row of a shape, so they are printed once per shape, with "
               "the interval from that shape's first row; each row's own bootstrap gives slightly different intervals for them, which are not "
               "printed again ('as above').")],
        [label("At 6×1 Opus-medium was right on every even-numbered puzzle, so its bootstrap interval collapses to one point; the exact two-sided 95% "
               "(Clopper–Pearson) interval over the even-numbered puzzles from free analysis 4 is printed in its place, labelled post hoc† (exact).")],
        [label("No format-compliance figure is stamped for the cascade; the format compliance of Haiku-medium's and Opus-medium's samples over all "
               "puzzles is in TAB-04.")],
    ]
    caption = _caption("pre-specified exploratory (offline simulation)", "Study 1, main run, 6 steps",
                       _line(label("even-numbered puzzles: "), integer(S.ref("main", join_key("reporting", "group_b", "item_9e", "shapes", "1x6", first, "even_bases"))),
                             label("; odd-numbered puzzles: "), integer(S.ref("main", join_key("reporting", "group_b", "item_9e", "shapes", "1x6", first, "odd_bases"))),
                             label("; per puzzle the cascade uses k_c Haiku-medium samples, plus one Opus-medium sample when it escalates")),
                       [label("bootstrap over puzzles, 95% intervals (bootstrap name stamped per row)")],
                       [label("list price per puzzle")], _set_cells(S))
    t = Table([label(c) for c in cols], rows, notes, caption)
    t.main_table = _tab08_paper(S, caption)
    # supplement layout: 17 columns, so two landscape parts (the setting, the accuracy and the difference; the costs)
    _split(t, [["τ", "Rule for τ", "Escalation rate (%)", "Cascade accuracy (%)", "Cascade accuracy 95% interval",
                "Opus-medium accuracy (%)", "Opus-medium accuracy 95% interval", "d: cascade minus Opus (points)", "d 95% interval"],
               ["Cascade cost per puzzle ($)", "Cascade cost 95% interval ($)", _T8_OPUS_COST,
                "Opus-medium cost 95% interval ($)", "Cost difference ($ per puzzle)",
                "Cost difference, lower end of the 95% interval ($)", "Cost difference, upper end of the 95% interval ($)"]],
           key=["Shape", "k_c"], landscape=True)
    _groups(t, lambda r: r[0].printed)                      # a shape's k_c rows together (the writer carries the groups into the parts)
    return t


# The cascade as the paper prints it (Vision's plan §3: 'as now, without the notes block'): the cascade's setting (shape, k_c, τ), how
# often it escalates, its accuracy and list cost with their intervals, and the two results against Opus-medium (d and the cost
# difference, each with its interval). Opus-medium's own accuracy and cost (one estimate per shape, 'as above' in later rows), its
# odd-base accuracy and the tau rule's text stay in the supplement's full table; the rule and its one exception are the second note.
# Round 2 (the width check): short headers, the threshold as the symbol τ (the core prints it as math). Round 3: the shape on every
# row (the CSV keeps it; the writer has no group rule yet), the cost named as list cost (as TAB-12, TAB-14 and TAB-16 name it), and
# both dollar columns at D-161's 3 significant figures (the writer's lint checks a dollar column by significant figures, not decimals).
_TAB08_PAPER_COLS = ("Shape", "k_c", "τ", "Escalated (%)", "Accuracy (%) [95% interval]", "d (points) [95% interval]",
                     "List cost per puzzle ($) [95% interval]", "Cost minus Opus-medium ($) [95% interval]")
# The two stamped tau rules (item 9e's 'rule'): the cheapest tau within the tolerance, or, where no tau came within it, the most
# accurate one on the odd bases.
_TAU_RULE = re.compile(r"cheapest tau within (\d+) points of Opus-medium on the odd bases")
_TAU_NONE = re.compile(r"none within (\d+) points: the highest odd-base accuracy")


def _tau_rule_note(S: Store) -> List[Cell]:
    """The second note: how τ was chosen, with the one setting where no τ came within the tolerance. The tolerance is read from every
    row's stamped rule (refuse unless all six rules are one of the two texts with one tolerance, and exactly one row is the exception);
    the exception's shape and k_c are read from its key. The shape is in the paper's word (chains, pieces), as the table prints it."""
    rules, exceptions = [], []
    for sh in SHAPES:
        sizes = sorted((k for k in S.keys("main", join_key("reporting", "group_b", "item_9e", "shapes", sh)) if k.isdigit()), key=int)
        for kc in sizes:
            b = join_key("reporting", "group_b", "item_9e", "shapes", sh, kc)
            r = S.ref("main", f"{b}.rule")
            m = _TAU_RULE.fullmatch(r.value) or _TAU_NONE.fullmatch(r.value)
            if not m:
                raise ValueError(f"item 9e {sh} {kc}: a tau rule the note does not describe: {r.value!r}")
            rules.append((r, m.group(1)))
            if _TAU_NONE.fullmatch(r.value):
                exceptions.append((sh, kc, b, r))
    if len({tol for _, tol in rules}) != 1 or len(exceptions) != 1:
        raise ValueError(f"the tau note assumes one tolerance and one exception: {[r.value for r, _ in rules]}")
    sh, kc, b, r = exceptions[0]
    tol = Cell(rules[0][1], raw=[x.value for x, _ in rules], refs=tuple(x for x, _ in rules),
               formula="the tolerance written in every row's stamped tau rule (all equal)")
    none = _plain_reason(r, "none within ", "none, so the most accurate")
    return _line(label("τ: the cheapest value within "), tol,
                 label(" points of Opus-medium on the odd-numbered puzzles (" + _SHAPE_WORD[shape_word(sh)] + ", k_c = "),
                 _key_cell("main", b, kc, as_int=True), label(": "), none, label(")."))


def _tab08_paper(S: Store, caption: Dict[str, List[Cell]]) -> Table:
    """TAB-08's paper version (D-160, D-161; Edith's proof 2): the full table's refs at the paper's precision. Percentages and points
    at one decimal (accuracies with the guard at 100, d and its interval with the guard at 0, the interval's positive end unsigned);
    the cascade's list cost, the cost difference and their intervals in US dollars at 3 significant figures (rule 2; the difference
    signed, its interval's positive end unsigned). The build refuses unless every dollar figure prints with exactly 3 significant
    figures (round 3: the full table's 4 fixed decimals left some differences with 1 or 2). The shape is in the paper's word (chains,
    pieces, as Table 2 prints it) and prints once per shape (the CSV keeps it on every row); the two shapes are the table's row groups,
    with a little space between rows (each row is two lines tall)."""
    rows, starts = [], []
    for sh in SHAPES:
        starts.append(len(rows))
        sizes = sorted((k for k in S.keys("main", join_key("reporting", "group_b", "item_9e", "shapes", sh)) if k.isdigit()), key=int)
        for kc in sizes:
            b = join_key("reporting", "group_b", "item_9e", "shapes", sh, kc)
            ev = f"{b}.even"
            # the accuracy and its interval stay on one line in every row (a no-break space; one layout for every cell)
            acc = joined(pct(S.ref("main", f"{ev}.cascade_accuracy"), dp=1, from_proportion=False, bounds=(100.0,)),
                         interval(*ci_refs(S, "main", f"{ev}.cascade_accuracy_ci95"), dp=1, bounds=(100.0,)), sep=_NBSP)
            d = joined(pts(S.ref("main", f"{ev}.accuracy_difference"), dp=1),
                       interval(*ci_refs(S, "main", f"{ev}.accuracy_difference_ci95"), dp=1, signed=False, bounds=(0.0,)))
            cost = joined(usd(S.ref("main", f"{ev}.cascade_mean_cost")), _usd_interval(*ci_refs(S, "main", f"{ev}.cascade_mean_cost_ci95")))
            diff = joined(_usd_signed(S.ref("main", f"{ev}.cost_difference")),
                          _usd_interval(*ci_refs(S, "main", f"{ev}.cost_difference_ci95")))
            rows.append([label(_SHAPE_WORD[shape_word(sh)]), _key_cell("main", b, kc, as_int=True),
                         num(S.ref("main", f"{b}.recommended_tau"), dp=1), pct(S.ref("main", f"{ev}.cascade_escalation_rate"), dp=1),
                         acc, d, cost, diff])
    bad = [x for r in rows for j in (6, 7) for x in re.findall(r"[−+]?\d+\.\d+", r[j].printed) if _sig_figs(x) != 3]
    if bad:
        raise ValueError(f"the cascade's dollar figures must print at 3 significant figures: {bad}")
    # the notes (two lines together, Edith §7.5): the cascade's two parameters and the rule for τ with its one exception; which puzzles
    # the columns are on and the sign of the differences are in the caption facts (and the cost header)
    notes = [[label("k_c: Haiku-medium samples per vote; the cascade escalates to Opus-medium when the top answer's share is below τ.")],
             _tau_rule_note(S)]
    if set(caption) != {"tier", "study", "set", "n", "interval", "price"}:
        raise ValueError(f"the full table's caption facts changed ({sorted(caption)}): check the 'full_table_only' fact")
    out = dict(caption)                 # every fact of the full table's caption, unchanged (spec rule 5), plus the two below
    out["columns"] = [label("what the printed notes leave out because the caption carries it: the cascade takes a vote of k_c "
                            "Haiku-medium samples and escalates to Opus-medium when the top answer's share is below τ; τ is chosen on the "
                            "odd-numbered puzzles and every other column is on the even-numbered puzzles; d and the cost difference are "
                            "the cascade minus Opus-medium on the same puzzles (the cost header says so)")]
    out["full_table_only"] = [label("printed in the supplement's full table only: Opus-medium's own accuracy and list cost with their "
                                    "intervals (on pieces its accuracy interval is the exact interval of free analysis 4, post hoc), its "
                                    "accuracy on the odd-numbered puzzles, and each row's tau-rule text (the second note gives the rule "
                                    "and its one exception); a caption for this version should not describe them")]
    t = Table([label(c) for c in _TAB08_PAPER_COLS], rows, notes, out, short_notes=[0, 1], layout="float")
    t.groups, t.once, t.spaced = starts[1:], [0], True
    return _paper_check(t)


# ================================================================ TAB-09 (real time against Batch, latency; Pilot 1 side panel)

# Pilot 1's ledger (a text file): last changed on origin/main by 2b28bc4; the SHA-256 is that of `git show 2b28bc4:<path>`.
PILOT1_LEDGER = register_source(Source(
    name="pilot1_ledger", path="data/pilot/pilot-ledger-1-exploratory.md", commit="2b28bc4",
    sha256="1fdf8225f044d6063b9c7f40bd52dbcf6a8d9d33ecc61ad275036430a77f201e", kind="text",
    what="Pilot 1 ledger (24 steps, exploratory), including the real-time check next to Batch (lines 74-85)"))

_PILOT_COLS = ("Model", "Mode", "24×1 whole", "24×1 per piece", "1×24 whole", "1×24 final", "1×24 lines = key", "1×24 local", "1×24 format ok")


def _pilot_panel(S: Store) -> Table:
    """Pilot 1's real-time table (the markdown table under '## The real-time check next to Batch'): each cell read by L<n>['<column>']."""
    head = S.find_lines("pilot1_ledger", r"^## The real-time check next to Batch")
    if len(head) != 1:
        raise KeyMissing(f"pilot ledger: {len(head)} headings for the real-time check")
    first = [n for n in S.find_lines("pilot1_ledger", r"^\| (haiku|opus|sonnet)-5-5 \| (real time|Batch)") if n > head[0]]
    lines = [n for i, n in enumerate(first) if n == first[0] + i]               # the contiguous block of data rows
    cols = [f"{c} (%)" if c not in ("Model", "Mode") else c for c in _PILOT_COLS]
    # The ledger's model cells are API-style ids; the paper names the settings (style sheet). Pilot 1's real-time setups rthm, rtom and
    # rtsm all ran at medium effort (harness/analysis/explore_pilot1.py, the SETUPS table), as did its Batch run (the ledger's run line).
    if len(S.find_lines("pilot1_ledger", r"Run `pilot-ledger-1` .*: Batch, effort medium;")) != 1:
        raise KeyMissing("pilot ledger: the run line naming medium effort is not found once")
    model_name = {"haiku-5-5": "Haiku-medium", "opus-5-5": "Opus-medium", "sonnet-5-5": "Sonnet-medium"}
    rows = []
    for n in lines:
        row = [text_of(S.ref("pilot1_ledger", join_key(f"L{n}", "Model")), model_name),
               _stamped_in_quotes(S.ref("pilot1_ledger", join_key(f"L{n}", "Mode")), tail="")[0]]       # the ledger's own words ("tries")
        row += [_pct_text(S.ref("pilot1_ledger", join_key(f"L{n}", c))) for c in _PILOT_COLS[2:]]
        rows.append(row)
    # The section heading holds a set id (methods appendix only): it is not printed; its puzzle count is.
    hr = S.ref("pilot1_ledger", f"L{head[0]}")
    m = re.search(r"base puzzles (\d+)\u2013(\d+), both shapes: (\d+) puzzles\)$", hr.value)
    if not m or (int(m.group(2)) - int(m.group(1)) + 1) * len(SHAPES) != int(m.group(3)):
        raise KeyMissing(f"pilot ledger heading {hr.value!r}: not 'base puzzles a\u2013b, both shapes: n puzzles' with n = 2 (b - a + 1)")
    puzzles = _stamped_number_in(S, "pilot1_ledger", f"L{head[0]}", r"both shapes: (\d+) puzzles\)$")      # the stamped heading counts each puzzle in both shapes
    n_bases = int(m.group(2)) - int(m.group(1)) + 1
    bases_cell = Cell(str(n_bases), raw=hr.value, refs=(hr,),
                      formula="the number of base puzzles in the stamped range 'base puzzles a\u2013b' of this heading: b - a + 1")
    # The ledger was scored with the scorers official at the time (the original marking rule), before Deviation 2: refuse to build
    # if the pinned ledger no longer says so.
    if len(S.find_lines("pilot1_ledger", r"official D-76 scorers")) != 1:
        raise KeyMissing("pilot ledger: the line naming its scorers is not found once")
    notes = [_line(label("Pilot 1 is exploratory (24 steps, a different puzzle set). The cells are for the "), bases_cell,
                   label(" Pilot 1 puzzles of its real-time check, each as a chain and as pieces ("), puzzles, label(" in all).")),
             _line(*_stamped_in_quotes(S.ref("pilot1_ledger", f"L{head[0] + 2}"), "As the ledger words it: ", "")),
             # the measures the headers name, in plain words, as the ledger defines them (its views of whole answers, of the answer line alone,
             # and per step); each definition's ledger line is a source of the note (Edith, proof 3, p. 67: the labels were undefined)
             _line(label("The measures, as Pilot 1's ledger defines them. 24×1 is the puzzle as separate pieces and 1×24 as one chain. Whole: the "
                         "whole-answer accuracy under the original marking rule. Per piece (24×1): the share of pieces right. Final (1×24): the "
                         "accuracy on the answer line alone (at 24×1 it equals the whole answer). Lines = key (1×24): the share of step lines "
                         "equal to the key, over samples whose lines can be placed. Local (1×24): the per-step accuracy with each step judged "
                         "from the model's own previous line, over samples whose lines can be placed. Format ok (1×24): the share of samples in the "
                         "required answer format."),
                   *(_cite(S, "pilot1_ledger", pat) for pat in (r"^## Whole-answer accuracy \(official D-76 score\)",
                                                                 r"^## Final-answer view \(the Answer line alone",
                                                                 r"^24×1: share of pieces right\. 1×24: \(a\) step lines equal to the key",
                                                                 r"^model's own previous line\), .*over tries whose lines can be placed\.$",
                                                                 r"^## Format compliance and truncations"))),
             [label("Pilot 1's results file gives percentages to one decimal; the cells are copied from it without the percent sign. Calls per cell "
                    "are the samples named in the Mode column, which keeps the ledger's own wording in quotation marks (its \"tries\" are samples).")],
             [label("Marking rule: Pilot 1's results file was scored with the scorers that were official at the time, under the original "
                    "marking rule, before Deviation 2. The paper's other tables use Deviation 2's rule; no re-score of these cells under it "
                    "is stamped.")]]
    p = Table([label(c) for c in cols], rows, notes, layout="float")
    _groups(p, lambda r: r[0].printed)                      # a model's two modes together
    return p


def _rt_format(S: Store, arm: str) -> Cell:
    """A real-time arm's format compliance (%) over both shapes: item 17's format-ok tries over its answered tries, summed over the two
    shapes (no pooled figure is stamped); refuse to build unless the answered tries add up to the arm's stamped calls."""
    f = [join_key("reporting", "group_b", "item_17", "flags", f"{arm} {sh}") for sh in SHAPES]
    if sum(S.get("main", f"{k}.answered") for k in f) != S.get("main", f"reporting.realtime.{arm}.calls"):
        raise ValueError(f"{arm}: item 17's answered tries do not add up to the real-time calls")
    return num_d(derive("100 * (format_ok 1x6 + format_ok 6x1) / (answered 1x6 + answered 6x1)", lambda a, b, c, d: 100 * (a + b) / (c + d),
                        S.ref("main", f"{f[0]}.format_ok"), S.ref("main", f"{f[1]}.format_ok"),
                        S.ref("main", f"{f[0]}.answered"), S.ref("main", f"{f[1]}.answered")), dp=2)


def _rt_puzzles(S: Store) -> List[Cell]:
    """The real-time subset's puzzle count and base-puzzle count, counted from the stamped list of puzzle ids (recorded as formulas)."""
    key = "reporting.realtime.puzzles"
    ids = S.get("main", key)
    m = [re.fullmatch(r".*-(\d+)-(1x6|6x1)", p) for p in ids]
    if not all(m) or len(set(ids)) != len(ids):
        raise ValueError(f"{key}: ids not in the form <set>-<base>-<shape>")
    bases = {x.group(1) for x in m}
    if {(b, sh) for b in bases for sh in SHAPES} != {(x.group(1), x.group(2)) for x in m}:
        raise ValueError(f"{key}: not every base puzzle in both shapes")
    r = Ref(ids, "main", key)
    return [Cell(str(len(bases)), raw=len(bases), refs=(r,), formula="the number of distinct base numbers in the stamped puzzle ids"),
            label(" puzzles, each as a chain and as pieces ("),
            Cell(str(len(ids)), raw=len(ids), refs=(r,), formula="the number of stamped puzzle ids"), label(" in all)")]


# PLAN NOTE (TAB-09): the plan's '5-call vote times' column heading holds a digit no file stamps as a number (it is in the key name vote_of_5), so the headings
# say 'the real-time calls'. Pilot 1's panel prints the ledger's cells without the percent sign (column names carry the unit).
@output("TAB-09")
def tab_09(S: Store) -> Table:
    cols = ["Setting", "Calls", "Accuracy, real time (%)", "Accuracy, Batch (%)", "Difference, real time minus Batch (points)",
            "Mean output tokens per call, real time", "Mean output tokens per call, Batch", "Latency median (s)", "Latency quartiles (s)",
            "Latency p95 (s)", "Latency max (s)"]
    rows, fmt, votes = [], [], []
    for arm in ("rt-haiku-med", "rt-opus-med", "rt-sonnet-med"):
        b = f"reporting.realtime.{arm}"
        lat = f"{b}.latency"
        if S.has("main", f"{b}.vote_of_5"):       # only one setting has repeated real-time calls: its two vote times go to the first note
            votes.append((arm, num(S.ref("main", f"{b}.vote_of_5.at_once_median"), dp=2),
                          num(S.ref("main", f"{b}.vote_of_5.one_after_another_median"), dp=2)))
        rows.append([_arm_label(arm), integer(S.ref("main", f"{b}.calls")),
                     pct(S.ref("main", f"{b}.accuracy_realtime"), dp=2), pct(S.ref("main", f"{b}.accuracy_batch"), dp=2),
                     _share_pts(S.ref("main", f"{b}.accuracy_difference"), dp=2, signed=True, bounds=(0.0,)),
                     _thousands(S.ref("main", f"{b}.output_tokens_realtime"), dp=1), _thousands(S.ref("main", f"{b}.output_tokens_batch"), dp=1),
                     num(S.ref("main", f"{lat}.median"), dp=2), interval(*ci_refs(S, "main", f"{lat}.quartiles"), dp=2),
                     num(S.ref("main", f"{lat}.p95"), dp=2), num(S.ref("main", f"{lat}.max"), dp=2)])
        fmt.append(_rt_format(S, arm))                      # 100.0 for every setting: a note, not a column
    if [v[0] for v in votes] != ["rt-haiku-med"]:
        raise ValueError(f"the vote-time note names Haiku-medium as the only setting with repeated real-time calls: {[v[0] for v in votes]}")
    notes = [
        _line(label("Vote times are computed from single calls, not measured: all at once is the slowest of a puzzle's real-time calls, one after another is their sum; "
                    "the figures are medians over puzzles. Only Haiku-medium has repeated real-time calls, so only it has vote times: a vote of its "
                    "real-time calls takes a median of "), votes[0][1], label(" s all at once and "), votes[0][2], label(" s one after another.")),
        [label("The real-time subset is a small check next to Batch; accuracy differences are of a few puzzles and carry no test.")],
        _line(label("Format compliance of Study 1's real-time calls is "), _same_in_every_row(fmt), label("% for all three settings: the format-ok share of their answered "
              "samples, both shapes together (the per-shape counts are in TAB-07's Study 1 format panel). No format figure is stamped for the Batch "
              "samples on this subset; the settings' full Batch figures are in TAB-04.")),
        [label("Latency is the time of answered calls; quartiles are the first and third quartile; p95 is the time that 95% of the calls did not "
               "exceed, and max is the slowest call's.")],
    ]
    caption = _caption("pre-specified descriptive (the real-time check); the Pilot 1 panel is exploratory", "Study 1, main run, 6 steps (real-time subset)",
                       _line(*_rt_puzzles(S), label("; real-time calls: Haiku-medium "), integer(S.ref("main", "reporting.realtime.rt-haiku-med.calls")),
                             label(", Opus-medium "), integer(S.ref("main", "reporting.realtime.rt-opus-med.calls")), label(", Sonnet-medium "),
                             integer(S.ref("main", "reporting.realtime.rt-sonnet-med.calls"))),
                       [label("none: counts, medians and quartiles only")], [label("not applicable (no costs)")], _set_cells(S))
    t = Table([label(c) for c in cols], rows, notes, caption)
    t.panels = [("Pilot 1 real time next to Batch (exploratory)", _pilot_panel(S))]
    # supplement layout: eleven columns do not fit 6.5 in in one table (measured: overfull by 0.09 in; the polish standard sets appendix
    # tables split rather than shrunk), so two portrait parts (accuracy and tokens; latency)
    _split(t, [["Calls", "Accuracy, real time (%)", "Accuracy, Batch (%)", "Difference, real time minus Batch (points)",
                "Mean output tokens per call, real time", "Mean output tokens per call, Batch"],
               ["Latency median (s)", "Latency quartiles (s)", "Latency p95 (s)", "Latency max (s)"]], key=["Setting"])
    return t
