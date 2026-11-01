"""Disclosure tables: TAB-21 (the tuning-bias table), TAB-22 (the data README: stamped labels and the paper's wording) and TAB-23
(reproducibility: files, hashes and commits). TAB-20 (the timeline) is in paper_out_timeline.py.

The text sources (the Study 1 spec, LOG.md, the spend log, the findings register, the decision register, the claims-ledger format,
the harness requirements and Study 1's reporting definitions) are read by line and markdown-cell keys; all but the requirements and the
reporting definitions are pinned in paper_out_ops.py. Wording cells in TAB-22's last column follow the master plan's data-README item
(7b43f91, "Disclosures") and the settlement's rulings; they are checked like any ledger text.

What the printed text may name (Edith's PR 27 review, rulings PO-1, Q22 to Q24, N-11; Jarvis's ruling of 2026-10-15):
- **No decision id prints anywhere** (the decision register is not released). In TAB-22's verbatim quotes of stamped labels each id is
  replaced in place by a bracketed plain-words gloss read from the register (`GLOSSES`), and a table note says so; elsewhere the
  wording is plain ("our ruling of <date>"). The ids stay in each cell's provenance (refs, raw, formula).
- **Internal record names print in plain words**: the spend log is "our cost records", LOG.md "our work log", findings register 5.4
  "our record of the code used after the locks". The chats' names stay out (style sheet, D-122): stamped text that carries one is shown
  with the name replaced. The keep-list and arm codes C13, E2 and E3, and the spec's short codes (F3, L2, TI, TI_house), print as words.
- **The paper's voice is "we"**; caption facts hold no item numbers. `_printed_plain` checks all of this on every built table.
- TAB-23 lists Study 1's reporting definitions (research/reporting-definitions-main.md), the file that numbers the "(item N)" the
  appendix tables cite, at the revision the stamped Study 1 analyses name. Its "Commit" column is the claims-ledger field of that
  name; what its note says about each commit (the last to touch the file; for a data file, the one that added it) is checked
  against the git history of the commit being built (`_pin_history`).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

from . import paper_out_lint as lint
from .paper_out_core import need_history
from .paper_out_core import (SOURCES, Cell, Ref, Source, Store, Table, derive, integer, join_key, joined, label, num_d, output, pct,
                             register_source, text_of)
from .paper_out_names import MAIN_TEXT_ID, _printed
from .paper_out_ops import (_hours_of_main_start, _spend_rows, _seq, cell_ref, en_dash, extract, group_starts, guard, line_of,
                            paper_words_check, reg_line, set_widths, unprinted)

register_source(Source("requirements", "harness/requirements.txt", "88d5c72",
                       "e426975f7680eba153716fbec5de1762092e50628cbb9731fc395cd3abedb019", kind="text", what="The paid-run harness's pinned dependency (anthropic)"))
# Study 1's reporting definitions at the last commit on main that changed them (Addendum C4), the revision the stamped Study 1 analysis
# and keep-list analyses name; a name of this module's own, so that no other module's pin of the same file can clash with it.
register_source(Source("reporting_defs_release", "research/reporting-definitions-main.md", "93334b8",
                       "bddab72761b4111f6d4ed439f13ddbd63427bc14a9c61b58d0ceadb32f18bf81", kind="text",
                       what="Study 1's reporting definitions (items 1-24, Addenda A to C4): the numbering of the appendix tables' items"))

# Karen's claims ledger at the last commit on main that changed it (all 264 rows cleared): row C-219 is the caption of TAB-06, the words
# that TAB-22's keep-list row quotes. The jsonl is the file the ledger's checker reads (the .md is rendered from it).
register_source(Source("claims_ledger", "research/paper-notes/claims-ledger.jsonl", "f3d0e6d",
                       "8b05cf0b07f986d1bcd8f2a5ff0cbd7ed8fed3b2ca12c870ccefb42cf26e7c7e", kind="text",
                       what="The claims ledger: row C-219 holds TAB-06's caption, whose first clause TAB-22's keep-list row quotes"))

DASH = label("—")
CHAT_NAMES = ("Jarvis", "Karen", "Friday", "Edith", "Vision")
_CHAT_RX = re.compile(r"\b(?:" + "|".join(CHAT_NAMES) + r")\b")
_DNUM_RX = re.compile(r"\bD-\d+")

# Internal record names, codes and voice the printed text must not use (PO-1, Q24, Q26, N-11): each prints in plain words instead.
_BARRED = re.compile(r"\bD-\d|LOG\.md|[Ff]indings register|[Ss]pend[- ]log|[Dd]ecision register|\b[Tt]he (?:user|authors)\b|"
                     r"India Standard Time|UTC calendar|\b(?:C13|E2|E3)\b")
# The one sentence that names the decision register, as Jarvis's ruling words it (TAB-22's note on the glossed decision ids).
REGISTER_NOTE = ("The released data files' labels cite internal decision numbers; the decision register is not released, so each is "
                 "given here in plain words.")


def _no_internal_names(cells: List[Cell], where: str, dnums: bool = True) -> None:
    """Refuses a printed cell that names a chat (or, with dnums, a decision number): no decision id prints anywhere in the paper (the
    register is not released), and the chats' names stay out of it."""
    for c in cells:
        if _CHAT_RX.search(c.printed) or (dnums and _DNUM_RX.search(c.printed)):
            raise ValueError(f"{where}: {c.printed!r} names a chat or a decision number")


def _printed_plain(t: Table, where: str) -> None:
    """Every printed text of a built table (columns, cells, notes, caption, panel titles and panels) is free of decision ids, chats'
    names, internal record names and codes (`_BARRED`; REGISTER_NOTE alone may name the register, as ruled), and its caption facts
    hold no item number (Q22: captions use none)."""
    for text in _printed(t):
        if text == REGISTER_NOTE:
            continue
        if _CHAT_RX.search(text) or _BARRED.search(text):
            raise ValueError(f"{where}: printed text names an internal record, id, code or chat: {text!r}")
    for cells in t.caption.values():
        for c in cells:
            if MAIN_TEXT_ID.search(c.printed):
                raise ValueError(f"{where}: a caption fact names an item number or internal id: {c.printed!r}")


_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def _day_month(r: Ref) -> Cell:
    """A stamped ISO date ('2026-10-12') printed as day and month name ('12 October')."""
    m = re.fullmatch(r"\d{4}-(\d\d)-(\d\d)", str(r.value))
    if not m:
        raise ValueError(f"{r.source}:{r.key} = {r.value!r} is not an ISO date")
    return Cell(f"{int(m.group(2))} {_MONTHS[int(m.group(1)) - 1]}", raw=r.value, refs=(r,),
                formula="the ISO date's day and month name")


def _verbatim(c: Cell) -> Cell:
    """A stamped text that holds a term the paper no longer uses (D-161: Karen's retired list) is printed as stamped, in quotation marks
    (a frozen source's words stay verbatim, Edith's ruling); any other stamped text is printed as it is."""
    return replace(c, printed='"' + c.printed + '"') if lint.vocabulary_texts([c.printed]) else c


def _quote_all(c: Cell) -> Cell:
    """A stamped value in double quotation marks whatever it holds (the table's rule for a value with a word the paper's text does not use)."""
    return replace(c, printed='"' + c.printed + '"')


def _gloss_d93(S: Store) -> Cell:
    """The plain-words gloss of the decision that allowed the public stamp of Study 1's analysis code before any main-run result was
    opened: its date and what it did, read from its register row (the wording stops if the row no longer says so)."""
    n = reg_line(S, "D-93")
    dec = cell_ref(S, "register", n, "Decision (plain)")
    return _seq("the", _day_month(cell_ref(S, "register", n, "Date")), "analysis",            # read before "stamp" (Edith, §33)
                guard(dec, r"`harness/analysis/main_rows\.py` and `(main_analysis)\.py`", "the ruling is about the analysis code"),
                guard(dec, r"their (commit hash) is posted on a public gist", "the ruling posts the analysis code's hash publicly"),
                guard(dec, r"(BEFORE any main-run result is opened)", "the stamp comes before any result is opened"))


# Decision ids that stamped labels cite -> their plain-words gloss (a stamped id with no gloss here stops the build).
GLOSSES: Dict[str, Callable[[Store], Cell]] = {"D-93": _gloss_d93}


def _quoted(S: Store, r: Ref) -> Cell:
    """A stamped string quoted verbatim, except for two editorial changes in square brackets: each decision id is replaced in place
    by its bracketed plain-words gloss (`GLOSSES`), and a reviewing session's name (and its review round, e.g. 'r6') by
    '[review note]'. The cell keeps the stamped string as its raw value and the register rows among its refs."""
    v = str(r.value)
    ids = sorted(set(_DNUM_RX.findall(v)))
    missing = [i for i in ids if i not in GLOSSES]
    if missing:
        raise ValueError(f"{r.source}:{r.key} cites {missing}, which have no plain-words gloss")
    gl = {i: GLOSSES[i](S) for i in ids}
    out = _DNUM_RX.sub(lambda m: "[" + gl[m.group(0)].printed + "]", v)
    named = re.sub(r"\b(?:" + "|".join(CHAT_NAMES) + r")(?: r\d+)?\b", REVIEW_NOTE, out)
    done = [f"decision id {i} {GLOSSED}" for i in ids]
    if named != out:
        done.append(REDACTED)
    if not done:
        return text_of(r)
    refs = (r,) + tuple(x for g in gl.values() for x in g.refs)
    formula = "; ".join(done + [g.formula for g in gl.values() if g.formula])
    return Cell(named, raw=r.value, refs=refs, formula=formula)


# ================================================================ TAB-21: the tuning-bias table

# Applied in order to the spec's bias-table cells; each cell's formula lists the ones that changed it, and the table note says them all
# (the build stops if one of them changes no cell, so the note never names a change that was not made). The fourth field, for a
# spec code written out in words, holds the spec lines the words rest on (the line that defines the code, and any line that supports
# a further typed word): each must match exactly one line, together they must lie in one block of the spec (no blank line between
# the first and the last), and a cell the relabel changed cites them all among its sources. The absorption caps' "puzzle generator's"
# rests on the heading of the build conditions whose second item (L2) defines the caps: "build conditions (L1 to L5), as built
# (generator ledger-…)", ledger being the puzzle family.
RELABEL: List[Tuple[str, str, str, Optional[Tuple[str, ...]]]] = [
    (r"24×1", "6×1", "24×1 → 6×1", None),
    (r"1×24", "1×6", "1×24 → 1×6", None),
    (r"\s*\(D-\d+\)|,\s*D-\d+$", "", "decision number removed", None),
    (r"\bKaren's power simulation\b", "a power simulation", "a session's name removed", None),
    (r"\ba match must hold\b", "a result shown no worse must hold", "'a match' → 'a result shown no worse'", None),
    (r"\bBoth arms\b", "Both sides", "'Both arms' → 'Both sides'", None),
    (r"\bArms that slip more\b", "Designs that slip more", "'Arms that slip more' → 'Designs that slip more'", None),
    (r"\bThe three-way reading\b", "The pre-registered decision rule", "'the three-way reading' → 'the pre-registered decision rule'",
     None),
    (r"^F3\b", "The headline rule", "the headline rule's code → 'The headline rule'", (r"^### The headline rule \(D-\d+ F3\)$",)),
    (r"\bthe caps \(L2: ", "the puzzle generator's absorption caps (", "the absorption caps' code → words",
     (r"^\*\*\w+'s build conditions \(L1 to L5\), as built \(generator ledger-[\d.]+\)\.\*\* ",
      r"^- L2: absorption is measured on the composite step by simulation and capped at ")),
    (r"\bTI_house\b", "the house-rule index", "the house-rule index's code → words", (r"and TI_house = \(house rule missed",)),
    (r"\bTI\b", "the targeting index", "the targeting index's code → words", (r"the targeting index TI = RR_Haiku",)),
]
# The note names the replaced words without printing them (the style sheet bans the shorthand in the paper, and the codes are internal;
# the cell's raw value keeps the spec's text).
RELABEL_NOTE = ("relabelled for 6 steps (Deviation 1): 24×1 → 6×1, 1×24 → 1×6; decision numbers and a session's name are "
                "removed; a range written \"a to b%\" reads \"a\u2013b%\"; the pre-registration's short codes for its headline rule, its "
                "absorption caps, its targeting index and its house-rule index are written out in words; the pre-registration's "
                "one-word shorthand for a result shown no worse, "
                "which the paper does not use, reads \"a result shown no worse\"; and its older words are the paper's: \"arms\" reads "
                "\"sides\" or \"designs\", and \"the three-way reading\" reads \"the pre-registered decision rule\"")
# Codes the printed cells and notes must not hold once relabelled (N-11).
_SPEC_CODES = re.compile(r"\b(?:F\d+|L\d+|TI(?:_house)?)\b")
# The full table's one further relabel, applied after RELABEL (the paper version has its own, below): Edith's polish standard (2.4)
# and (12.2) write a range with an en dash in the supplement too. The percent sign stays, as in the stamped text.
FULL_RELABEL: List[Tuple[str, str, str, Optional[Tuple[str, ...]]]] = [
    (r"\b(\d+) to (\d+)%", "\\1\u2013\\2%", "house style: 'a to b%' \u2192 'a\u2013b%'", None),
]
# The paper version's further relabels, applied after RELABEL; each must change a cell of the paper version, and each changed cell's
# formula lists them:
# - the house style's en-dash range;
# - shapes in the paper's words, as the body writes them ("pieces", "chain"; the batch spec's rule 4: one form a table).
PAPER_RELABEL: List[Tuple[str, str, str, Optional[Tuple[str, ...]]]] = [
    (r"\b(\d+) to (\d+)%", "\\1–\\2%", "house style: 'a to b%' → 'a–b%'", None),
    (r"^6×1 near the ceiling\b", "Pieces near the ceiling", "paper wording: '6×1 near the ceiling' → 'Pieces near the ceiling'", None),
    (r"\bAbsorption in 1×6\b", "Absorption in chains", "paper wording: 'Absorption in 1×6' → 'Absorption in chains'", None),
    (r"\bThe official 1×6 score\b", "The official chain score", "paper wording: 'The official 1×6 score' → 'The official chain score'",
     None),
    # Edith's polish standard §2.6 and the batch spec's rule 3: no "%" sign in a table cell. The pre-registration's two percentages
    # (its band and its flag's threshold) are prose, not a column's values, so the unit is written out (British, as the paper spells).
    (r"(\d)%", "\\1 per cent", "house style: no '%' in a cell: 'n%' → 'n per cent'", None),
]
# The paper's one short note (the converter prints the short notes as one paragraph, which must stay within two lines): what the first
# three columns are, and what the last one gives. The spec heading's caveat (the net direction is not known in advance) is the full
# table's note and the body's sentence before the table, not a definition the paper's note needs.
TAB21_NOTE = ("First three columns: the bias table of Study 1's pre-registration, relabelled for 6 steps (Deviation 1), in the "
              "paper's words and without internal references. Last column: each check's outcome or where it is reported.")
# The paper's Outcome header carries the unit of the two accuracies in that column (no "%" in a cell the paper writes itself).
TAB21_OUTCOME_HEADER = "Outcome (accuracies in %)"
# The stamped margin of the 5-point view (signed, as the analysis stamps it; the view's name prints its size).
FIVE_POINT_MARGIN = "reporting.five_point_view.margin"


def _evidence_lines(S: Store, evidence: Tuple[str, ...]) -> List[Ref]:
    """The spec lines a relabel's words rest on: each pattern matches exactly one line, and the lines lie in one block of the spec
    (no blank line from the first to the last), so a heading supports only the items under it."""
    ns = [line_of(S, "spec1", rx, expect=1) for rx in evidence]
    lines = S.doc("spec1").split("\n")
    if ns != sorted(ns) or any(not lines[i - 1].strip() for i in range(ns[0], ns[-1] + 1)):
        raise ValueError(f"TAB-21: the spec lines {ns} that a relabel rests on are not in order in one block")
    return [cell_ref(S, "spec1", n) for n in ns]


def _relabel(S: Store, r: Ref, fired: set, rules: Optional[List[Tuple[str, str, str, Optional[Tuple[str, ...]]]]] = None) -> Cell:
    v = r.value
    out, done, refs = v, [], [r]
    for rx, new, what, evidence in (RELABEL if rules is None else rules):
        nxt = re.sub(rx, new, out)
        if nxt != out:
            done.append(what)
            fired.add(what)
            if evidence is not None:
                refs.extend(_evidence_lines(S, evidence))
        out = nxt
    return Cell(out, raw=v, refs=tuple(refs), formula=("relabelled: " + "; ".join(done)) if done else None)


def _flag_k_outcome(S: Store, paper: bool = False) -> List[Cell]:
    """Flag K's outcome with its stamped reason in plain words (the house-rule index was not assessable: too few Opus and Sonnet
    house-rule slips), plus flag R's status. The wording is written for the stamped state; the build stops if that state differs.
    The paper's wording (`paper`) names flag K by what it is, the fairness check's flag (the body's words), and writes Flag R as the
    body does, with the cell's first word capitalised. The full table writes both check names capitalised, "Flag K" and "Flag R", as
    Table S12 (the table it cites) and the supplement's text do (Edith, proof 4)."""
    fk, th = "fairness.flag_k", "fairness.TI_house"
    pooled = "opus+sonnet"
    if (S.get("main", f"{fk}.fires") or S.get("main", f"{th}.assessable") or S.get("main", f"{th}.comparison") != pooled
            or S.get("main", "fairness.TI.fires")):
        raise ValueError("TAB-21: flag K's stamped state is not the one this wording describes")
    slips = S.ref("main", f"{th}.assess_counts.{pooled}.exposed_slips")
    need = extract(S.ref("main", f"{th}.assess_reason"), r"exposed slips < (\d+)")
    if not slips.value < int(need.raw):
        raise ValueError("TAB-21: the stamped slip count is not below the stamped minimum")
    k_name, r_name = ("The fairness check's flag", "Flag R") if paper else ("Flag K", "Flag R")
    return [text_of(S.ref("main", f"{fk}.fires"), {False: f"{k_name} did not fire", True: f"{k_name} fired"}),
            label(" (the targeting index "), text_of(S.ref("main", "fairness.TI.fires"), {False: "did not trigger the flag", True: "triggered the flag"}),   # a flag fires, an index does not (B2-S8)
            label("; the house-rule index was "),
            text_of(S.ref("main", f"{th}.assessable"), {False: "not assessable", True: "assessable"}),
            label(": Opus and Sonnet together had "), integer(slips), label(" house-rule slips, fewer than the "), need,
            label(f" it needs); {r_name} "), text_of(S.ref("main", "reporting.flag_r.flag_r.fires"), {False: "did not fire", True: "fired"}),
            label(" (TAB-07)")]


@output("TAB-21")
def tab_21(S: Store) -> Table:
    head = line_of(S, "spec1", r"^\| Choice \| Favours \| Bounded or measured by \|$", expect=1)
    rows: List[List[Cell]] = []
    n = head + 2
    outcome = {
        "Rule kinds tuned": _flag_k_outcome(S),
        "The 10-point margin": [label("the 5-point view of Tests 1–5 (TAB-03)")],
        "Refusals and truncations": [label("the refusals-out and truncations-out views (TAB-03)")],
        # TAB-18 prints this stamped marker (Study 1 pooled), at two decimals; TAB-04 prints only the two shapes' points.
        "Haiku band": [label("Haiku-medium single sample, pooled: "), pct(S.ref("main", "main_run_markers.haiku-med.pooled.mean"), dp=2),
                       label("% (TAB-18, Study 1 pooled)")],
        "near the ceiling": [text_of(S.ref("main", "reporting.low_information_flag.fires"),
                                     {False: "low-information flag did not fire", True: "low-information flag fired"}),
                             label("; Haiku-medium pieces: "), pct(S.ref("main", "reporting.low_information_flag.haiku_med_accuracy"), dp=2),
                             label("% (TAB-07)")],            # two decimals, as TAB-07 (Table S12, the table it cites) prints this value (Edith, proof 4)
        "Absorption": [label("the final-answer view (TAB-03)")],
    }
    # The paper version's outcomes (D-161): the two accuracies at one decimal, from the same stamped values, with their unit in the
    # header; "sample" for try; an en-dash range; the 5-point view's size read from its stamped margin; each cell's first word a capital.
    five = num_d(derive("the 5-point view's size: minus its stamped (signed) margin, -x", lambda x: -x,
                        S.ref("main", FIVE_POINT_MARGIN)), dp=0)
    paper_outcome = {
        "Rule kinds tuned": _flag_k_outcome(S, paper=True),
        "The 10-point margin": [label("The "), five, label("-point view of Tests 1–5 (TAB-03)")],
        "Refusals and truncations": [label("The refusals-out and truncations-out views (TAB-03)")],
        "Haiku band": [label("Study 1 pooled, Haiku-medium single sample: "),
                       pct(S.ref("main", "main_run_markers.haiku-med.pooled.mean"), dp=1), label(" (TAB-18)")],
        "near the ceiling": [text_of(S.ref("main", "reporting.low_information_flag.fires"),
                                     {False: "Low-information flag did not fire", True: "Low-information flag fired"}),
                             label("; Haiku-medium pieces: "), pct(S.ref("main", "reporting.low_information_flag.haiku_med_accuracy"), dp=1),
                             label(" (TAB-07)")],
        "Absorption": [label("The final-answer view (TAB-03)")],
    }
    if set(paper_outcome) != set(outcome):
        raise ValueError("TAB-21: the paper version's outcomes are not the full table's rows")
    lines = S.doc("spec1").split("\n")
    fired: set = set()
    paper_fired: set = set()
    paper_rows: List[List[Cell]] = []
    while n <= len(lines) and lines[n - 1].strip().startswith("|"):
        choice = S.ref("spec1", f"L{n}['Choice']")
        key = next((k for k in outcome if k in choice.value), None)
        if key is None:
            raise KeyError(f"no outcome mapped for bias-table row {choice.value!r}")
        spec_cells = [choice, S.ref("spec1", f"L{n}['Favours']"), S.ref("spec1", f"L{n}['Bounded or measured by']")]
        rows.append([*[_relabel(S, r, fired, RELABEL + FULL_RELABEL) for r in spec_cells], joined(*outcome[key], sep="")])
        paper_rows.append([*[_relabel(S, r, paper_fired, RELABEL + PAPER_RELABEL) for r in spec_cells],
                           joined(*paper_outcome[key], sep="")])
        n += 1
    if len(rows) != len(outcome):
        raise ValueError(f"bias table has {len(rows)} rows, {len(outcome)} outcomes mapped")
    unused = [w for _, _, w, _ in RELABEL + FULL_RELABEL if w not in fired]
    if unused:
        raise ValueError(f"TAB-21: the note names relabels that changed no cell: {unused}")
    unused = [w for _, _, w, _ in RELABEL + PAPER_RELABEL if w not in paper_fired]
    if unused:
        raise ValueError(f"TAB-21: the paper version's note names relabels that changed no cell: {unused}")
    _no_internal_names([c for r in rows + paper_rows for c in r], "TAB-21")
    if any(re.search(r"\bmatch(es|ed)?\b", c.printed) for r in rows + paper_rows for c in r):
        raise ValueError("TAB-21: a cell still holds 'match'")
    # The paper version shows the same rows, in the same order, at its own precision: its marker is the full table's value rounded. Its
    # outcomes cite the full table's sources, and one more: the stamped margin that gives the 5-point view's size.
    def provs(c: Cell) -> List[Tuple[str, str]]:
        return [(r.source, r.key) for r in c.refs]
    for full, paper in zip(rows, paper_rows):
        extra = [p for p in provs(paper[3]) if p not in provs(full[3])]
        if ([c.raw for c in full[:3]] != [c.raw for c in paper[:3]] or not set(provs(full[3])) <= set(provs(paper[3]))
                or extra not in ([], [("main", FIVE_POINT_MARGIN)])):
            raise ValueError(f"TAB-21: the paper version's row {paper[0].printed!r} is not the full table's")
    # The size the 5-point view's name prints is the spec's own secondary view's (the margin row's third cell says "a 5-point
    # secondary view"); no shape code is left once the shapes are in words.
    secondary = [m.group(1) for p in paper_rows for m in re.finditer(r"\ba (\d+)-point secondary view\b", p[2].printed)]
    if secondary != [five.printed]:
        raise ValueError("TAB-21: the stamped 5-point view's margin is not the spec's secondary view's")
    if any(re.search(r"\d\s*×\s*\d", c.printed) for r in paper_rows for c in r):
        raise ValueError("TAB-21: a paper cell still prints a shape code")
    # The note's "bias table" and "net direction" are the spec's own heading over the table (its F5 code is not printed).
    f5 = cell_ref(S, "spec1", line_of(S, "spec1", r"^\*\*The bias table \(F5; the net direction is not known in advance\):\*\*$", expect=1))
    if f5.key != f"L{head - 2}":
        raise ValueError("TAB-21: the spec's bias-table heading is not the line just above the table")
    notes = [[_seq("The first three columns are the bias table of Study 1's pre-registration,", RELABEL_NOTE + ". The last column "
                   "points to where each check's outcome is reported. The net direction was not known in advance.",
                   guard(f5, r"the net direction (is not known in advance)", "the bias table's net direction is not known in advance"))]]
    paper_notes = [[label(TAB21_NOTE)]]
    if any(re.search(r"\bmatch(es|ed)?\b", c.printed) for n in notes + paper_notes for c in n):
        raise ValueError("TAB-21: a note still holds 'match'")
    left = sorted({m for r in rows + paper_rows for c in r for m in _SPEC_CODES.findall(c.printed)} |
                  {m for n in notes + paper_notes for c in n for m in _SPEC_CODES.findall(c.printed)})
    if left:
        raise ValueError(f"TAB-21: printed text still holds the spec's short codes {left}")
    caption = {"tier": [label("disclosure")], "study": [label("Study 1 (main run, 6 steps)")]}
    cols = ("Choice", "Favours", "Bounded or measured by", "Outcome")
    t = Table([label(c) for c in cols], rows, notes, caption, layout="float")
    _printed_plain(t, "TAB-21")
    # The paper's TAB-21 (D-159/D-160; Vision's plan §3: as is, with at most two short notes; D-161's precision and wording).
    if any("%" in c.printed for r in paper_rows for c in r):
        raise ValueError("TAB-21: a paper cell prints a '%' sign; the unit goes in the header")
    t.main_table = Table([label(c) for c in (*cols[:3], TAB21_OUTCOME_HEADER)], paper_rows, paper_notes, caption, short_notes=[0],
                         layout="float")
    _printed_plain(t.main_table, "TAB-21 (paper)")
    paper_words_check(t.main_table, "TAB-21 (paper)")
    return t


# ================================================================ TAB-22: the data README

REVIEW_NOTE = "[review note]"
# The formulas `_quoted` records for its two editorial changes (the table notes are added when a printed cell carries one).
GLOSSED = "replaced in place by a bracketed plain-words gloss from its register row"
REDACTED = f"a chat's name and review round replaced by {REVIEW_NOTE}"
# The first column's file names (the analysis files TAB-23 lists, under its row names; checked against ANALYSES below).
FILE_WORDS: Dict[str, str] = {"main": "the Study 1 analysis", "groupc": "the Study 1 keep-list analyses", "topup": "the top-up analysis"}
# Study 1's reporting item 24 (its every-setup table): which arm and shape step voting ran at in the main run.
ITEM24 = "reporting.group_b.item_24.table"


def _readme_rows(S: Store) -> List[List[Cell]]:
    def key_text(src: str, key: str) -> Cell:
        r = S.ref(src, key)
        path = f"{src}: {r.key}"
        return Cell(f"{src}: \"{r.key}\"" if lint.vocabulary_texts([path]) else path, raw=r.key, refs=(r,),
                    formula="the stamped key path")

    th = "fairness.TI_house"
    t4 = "test4_pieces"
    hw = "confirmatory.headline_wording"
    others = [S.ref("main", f"{hw}.{t}") for t in ("t1", "t2", "t3", "t4")]
    if len({r.value for r in others}) != 1:
        raise ValueError("TAB-22: the headline wording of Tests 1-4 is not one stamped value")
    others_cell = Cell(others[0].value, raw=[r.value for r in others], refs=tuple(others),
                       formula="the one value stamped for each of Tests 1-4")
    run = line_of(S, "spend_log", r"^\| \d{4}-\d\d-\d\d \| \w+ \| topup-1 \|", expect=1)
    drv = cell_ref(S, "log", line_of(S, "log", r"^`python3 -m harness\.analysis\.topup_analysis --plan ", expect=1))
    cleared = extract(drv, r"plan ([0-9a-f]{8})… and all \d+ run-file hashes checked first")
    n_checked = extract(drv, r"and all (\d+) run-file hashes checked first")
    # The count is the top-up's run files plus the main run's stamped ones (the driver reads both runs): each run's spend-log row lists
    # its files' hashes, and the two counts must add up to LOG.md's.
    n_files = {run: len(names) for _, run, _, _, names in _run_files(S) if run in ("topup-1", "main-l14n6-1")}
    if len(n_files) != 2 or sum(n_files.values()) != int(n_checked.raw):
        raise ValueError(f"TAB-22: LOG.md's {n_checked.raw} run-file hashes are not the top-up's and the main run's ({n_files})")
    if len(S.get("topup", "inputs.main_run_stamp.files")) != n_files["main-l14n6-1"] or not S.get("topup", "inputs.main_run_stamp.all_match"):
        raise ValueError("TAB-22: the top-up file's main-run stamp check is not the main run's spend-log files, all matching")
    if not re.search(rf"plan_sha256 {cleared.raw}", str(S.get("spend_log", join_key(f"L{run}", "What ran")))):
        raise ValueError("TAB-22: the plan hash checked before the driver ran is not the cleared plan's in the spend-log row")
    if S.get("topup", "inputs.plan_sha256") != _spend_hash(S, "topup-1", S.get("topup", "inputs.plan")):
        raise ValueError("TAB-22: the top-up's inputs.plan_sha256 is not its plan copy's hash in the spend-log row")
    d112 = line_of(S, "register", r"^\| D-112 \|", expect=1)
    # The real-time arms' cost fields: every one is labelled real time at list price and its batch_mean is its list mean.
    b9 = "reporting.group_b.item_9b.arms"
    rt = [a for a in S.keys("main", b9) if a.startswith("rt-")]
    if len(rt) != 6 or len({a.split(":")[0] for a in rt}) * 2 != len(rt) or any(
            S.get("main", join_key(*b9.split("."), a, "batch_label")) != "real time (list)"
            or S.get("main", join_key(*b9.split("."), a, "batch_mean")) != S.get("main", join_key(*b9.split("."), a, "mean"))
            or "list price" not in S.get("main", join_key(*b9.split("."), a, "unit")) for a in rt):
        raise ValueError("TAB-22: the real-time arms' batch_mean is not their list mean, labelled real time (list), at both shapes")
    rt_arm = join_key(*b9.split("."), "rt-haiku-med:1x6")
    # The comparison on pieces whose key names the main run's step voting is against the top-up's step voting on pieces.
    cmp_key = "comparisons['topup:e2-e3:6x1']"
    if (S.get("topup", f"{cmp_key}.challenger"), S.get("topup", f"{cmp_key}.comparator"), S.get("topup", f"{cmp_key}.shape")) != (
            "e2", "c13", "6x1"):
        raise ValueError("TAB-22: comparisons['topup:e2-e3:6x1'] is no longer the Haiku team against the top-up's step voting on pieces")
    if S.has("main", join_key(*ITEM24.split("."), "e3 6x1")) or not S.has("main", join_key(*ITEM24.split("."), "e3 1x6")):
        raise ValueError("TAB-22: the main run's step voting is no longer on chains only")
    tab06_clause, tab06_row = _tab06_caption_clause(S)
    return [
        [key_text("main", f"{hw}.t5"), text_of(S.ref("main", f"{hw}.t5")),
         joined(label("Test 5's stamped headline word, the pre-registration's own word for the no-worse-than reading within the margin. "
                      "The paper writes: shown no worse than the comparator by more than the margin (Holm-adjusted). The values for Tests 1–4 "
                      "read '"), others_cell,
                label("'; the paper uses the pre-registered decision rule."), sep="")],
        [key_text("main", "original_repeat_rule_appendix.format_compliance"),
         joined(label("[repeats the official-rule values, e.g. Sonnet-medium chain: "),
                pct(S.ref("main", "original_repeat_rule_appendix.format_compliance.sonnet-med.1x6.format_compliance"), dp=2),
                label("%]"), sep=""),
         joined(label("Original-rule format compliance is read from secondary.rates (and item 10 for the other settings), e.g. "
                      "Sonnet-medium chain: "), pct(S.ref("main", "secondary.rates.sonnet-med.format_compliance_original"), dp=2),
                label("% (TAB-03, Panel 1)."), sep="")],
        # (The printed title of TAB-03's panel is "Panel 1", Edith's proof 3, C.38. That panel prints these two values at two decimals, 97.50
        # and 65.00, so both cells here do too: a cell that cites another supplement table prints its precision, Edith's C.37.)
        # The paper's label for the keep-list (group C) rows is Edith's Q19 wording; the stamped label must state both of its facts.
        [key_text("groupc", "label"), _quoted(S, S.ref("groupc", "label")),
         # The paper never prints a label for these rows (Edith, proof 4, p. 39: a whole-text search finds none). The words that do print
         # are the caption of the table that holds the keep-list analyses, TAB-06 (Table S19 in the supplement), which is Karen's ledger
         # row C-219's first clause: read from the ledger (research/paper-notes/claims-ledger.jsonl, the `claims_ledger` pin), not typed.
         _seq("The keep-list definitions were fixed before any result was opened, inside the public analysis stamp; they were computed "
              "after the confirmatory results were opened. Table TAB-06, which holds these analyses, says so in its caption:",
              tab06_clause,
              ". That caption uses this wording, not the stamped label's.",
              tab06_row,
              guard(S.ref("groupc", "label"), r"(definition fixed and timestamped before the data)", "the definitions were stamped first"),
              guard(S.ref("groupc", "label"), r"(computed after the confirmatory results were opened)",
                    "the rows were computed after the confirmatory results were opened"))],
        # The two SHA-256 values are compared in Panel 1, one under the other in typewriter type (Edith, proof 4, pp. 39-40: they were set in
        # roman and broken at different points, so their equality was hard to check by eye); the build checks they are equal.
        [key_text("groupc", "inputs.k"), label("[a scratch path on the build machine]"),
         _seq("The k.json used is the committed Study 1 k.json: its SHA-256 equals the pinned file's (both in Panel 1).",
              _equal_hashes(S.ref("groupc", "inputs.k_json_sha256"), S.ref("main_k", "@sha256")))],
        [key_text("topup", "costs.price_table_date"), text_of(S.ref("topup", "costs.price_table_date")),
         _seq("The analysis code's own price-table date; the run's price date is",
              extract(cell_ref(S, "register", d112, "Decision (plain)"), r"the price date is (\d{4}-\d\d-\d\d)"), ", as our ruling of",
              text_of(cell_ref(S, "register", d112, "Date")), "records",
              guard(cell_ref(S, "register", d112, "ID"), r"^(D-\d+)$", "the ruling's id, kept in provenance and not printed"),
              ". The prices it applies are the same list prices the run was cleared on, re-checked unchanged before the run; the "
              "paper states list prices once, with their check date.")],
        [key_text("topup", "inputs.plan_sha256"), _hash_described(S.ref("topup", "inputs.plan_sha256")),
         _seq("The driver was given the run folder's own copy of the plan (", text_of(S.ref("topup", "inputs.plan")),
              "), so its plan check compares that copy with itself; the value is that copy's file hash, as in the run's row of our cost "
              "records. Before the driver ran, the cleared plan's hash (", joined(cleared, label("…"), sep=""),
              ", as in that row) and all", n_checked,
              "run-file hashes (the top-up's and the main run's, as in their rows of our cost records) were checked (our work log's "
              "entry for the driver run).")],
        [key_text("main", f"{rt_arm}.batch_mean"),
         joined(label("[equals its list mean; its batch_label reads '"), text_of(S.ref("main", f"{rt_arm}.batch_label")), label("']"),
                sep=""),
         label("The six real-time settings were billed at list price, so their 'batch_mean' holds the list cost; the paper reports them at list.")],
        [key_text("topup", f"{cmp_key}.comparator"), text_of(S.ref("topup", f"{cmp_key}.comparator")),
         _seq("The comparison's key reads as", text_of(S.ref("topup", f"{cmp_key}.challenger"), {"e2": "the Haiku team"}),
              "against the main run's step voting, but on", text_of(S.ref("topup", f"{cmp_key}.shape"), {"6x1": "pieces"}),
              "its comparator is", text_of(S.ref("topup", f"{cmp_key}.comparator"), {"c13": "the top-up's step voting on pieces"}),
              ", as this field says; in the main run, step voting ran on chains only. The paper follows this field and calls the "
              "comparator", text_of(S.ref("topup", f"{cmp_key}.comparator"), {"c13": "step voting on pieces"}), ".")],
        [key_text("topup", f"{t4}.label"), text_of(S.ref("topup", f"{t4}.label")),
         joined(label("The key's name reads as Test 4 at pieces, the top-up spec's convenience label. The paper never names it a "
                      "test (only Tests 1–5 and B1–B3 are tests). It writes: step voting on pieces against one Opus-medium answer (the "
                      "pieces counterpart of Test 4), unadjusted, exploratory, outside the pre-registered family; the drift check between runs:"),
                text_of(S.ref("topup", f"{t4}.same_model_flag")), label("(TAB-14).")),
         ],
        [key_text("topup", f"{t4}.methods_note"), _verbatim(_quoted(S, S.ref("topup", f"{t4}.methods_note"))),
         _seq("The top-up was a run of its own, which started within", _hours_of_main_start(S),
              "hours of the main run's start by a disclosed change; comparisons across the two runs carry the status of the drift check "
              "between runs (TAB-07). In the stamped value, the words 'arm' and 'window' read, in the paper, design and run.")],
        [key_text("main", "fairness.flag_k.reason"), _quote_all(text_of(S.ref("main", "fairness.flag_k.reason"))),   # holds "pilot scale", a word
         # the paper's own text does not use: the table's rule sets such a value in double quotation marks (Edith, M2-6)
         joined(label("Flag K did not fire because the house-rule targeting index could not be assessed: Opus and Sonnet together had"),
                integer(S.ref("main", f"{th}.assess_counts['opus+sonnet'].exposed_slips")), label("house-rule slips, fewer than the"),
                extract(S.ref("main", f"{th}.assess_reason"), r"exposed slips < (\d+)"),
                label("the index needs. The main run is not a pilot: the paper gives the counts and does not repeat 'pilot scale' (TAB-21).")),
         ],
    ]


def _tab06_caption_clause(S: Store) -> Tuple[Cell, Cell]:
    """The first clause of TAB-06's caption, read from Karen's claims ledger row C-219 (Edith, #39 review S2: TAB-22 had it as typed text),
    and the guard on the row. The build stops unless exactly one row is C-219, it is the caption of TAB-06, and its clause still says the
    analyses were computed after the confirmatory results were opened, which is what TAB-22's cell relies on the quotation for. The cut
    ends at the first " (" and may not cross a full stop or a semicolon, so a row that loses its first parenthesis stops the build instead
    of quoting several sentences as one clause."""
    n = line_of(S, "claims_ledger", r'^\{"id": "C-219", ', expect=1)
    row = cell_ref(S, "claims_ledger", n)
    caption_of = guard(row, r'("used_in": \["Caption of TAB-06"\])', "row C-219 is the caption of TAB-06")
    clause = extract(row, r'"text": "([^"\\(.;]+?) \(')
    if "computed after the confirmatory results were opened" not in clause.printed:
        raise ValueError(f"TAB-22: the claims ledger's row C-219 (TAB-06's caption) no longer says the planned analyses were computed after "
                         f"the confirmatory results were opened; its first clause reads {clause.printed!r}")
    return joined(label('"'), clause, label('"'), sep=""), caption_of


def _equal_hashes(a: Ref, b: Ref) -> Cell:
    """The build stops unless two SHA-256 values are the same string; the cell prints nothing and keeps both refs."""
    if a.value != b.value:
        raise ValueError(f"TAB-22: {a.source}:{a.key} and {b.source}:{b.key} are not the same SHA-256")
    return Cell("", raw=[a.value, b.value], refs=(a, b), formula="not printed: the two SHA-256 values are equal (the build checks it); "
                                                                 "Panel 1 prints them")


def _hash_described(r: Ref) -> Cell:
    """A stamped SHA-256 in the 'Stamped value' column as a description, since Panel 1 prints the hash in full (typewriter type)."""
    return Cell("[a SHA-256 hash, in full in Panel 1]", raw=r.value, refs=(r,),
                formula="a description of the stamped value; the value itself is printed in Panel 1")


def _hash_panel(S: Store) -> Table:
    """Panel 1: the SHA-256 values the README rows name, in full and in typewriter type (a column set in `mono` breaks a hash every 8
    characters, never at random), the two copies of Study 1's k.json hash one under the other."""
    def field(src: str, key: str) -> Cell:
        r = S.ref(src, key)
        return Cell(f"{src}: {r.key}", raw=r.key, refs=(r,), formula="the stamped key path")
    rows = [[field("groupc", "inputs.k_json_sha256"), text_of(S.ref("groupc", "inputs.k_json_sha256"))],
            [label("The pinned Study 1 k.json (TAB-23)"), text_of(S.ref("main_k", "@sha256"))],
            [field("topup", "inputs.plan_sha256"), text_of(S.ref("topup", "inputs.plan_sha256"))]]
    # sideways, so it shares the last part's page (an upright float cannot, and the last part would stand alone under 60% full)
    return Table([label(c) for c in ("Field", "SHA-256")], rows, layout="landscape", mono=[1], font="footnotesize")


def _files_note(rows: List[List[Cell]]) -> Cell:
    """The first column's file names, in order of first use: each source a key path cites must be one of TAB-23's analysis files, named
    as TAB-23 names it."""
    used: List[str] = []
    for r in rows:
        src = r[0].refs[0].source
        if src not in used:
            used.append(src)
    if any("[" in r[0].printed for r in rows):
        raise ValueError("TAB-22: a key path holds a bracketed segment, so its keys are not simply joined by dots: reword the note")
    rows23 = {src: name for name, src, _ in ANALYSES}
    for src in used:
        if src not in FILE_WORDS or src not in rows23 or FILE_WORDS[src].lower() != "the " + rows23[src].lower():
            raise ValueError(f"TAB-22: the key paths' file {src!r} is not named as TAB-23 names it")
    return label("The first column gives the file (" + "; ".join(f"{src}: {FILE_WORDS[src]}" for src in used) + "; TAB-23 gives "
                 "their paths) and the field's key path in it, its keys joined by dots.")


@output("TAB-22")
def tab_22(S: Store) -> Table:
    rows = _readme_rows(S)
    # No decision id prints anywhere (the register is not released): the stamped labels' ids are glossed in place by `_quoted`.
    _no_internal_names([c for r in rows for c in r], "TAB-22")
    formulas = [c.formula or "" for r in rows for c in r]
    glossed, redacted = any(GLOSSED in f for f in formulas), any(REDACTED in f for f in formulas)
    notes = [[label("Each row is a stamped field that the paper does not repeat as written, beside the wording or key the paper uses "
                    "instead.")],
             [_files_note(rows)],
             [label("The key paths and the values in the 'Stamped value' column are quoted verbatim from the stamped files, as is every "
                    "stamped word in single quotes in the 'In the paper' column; some are words the paper's own text does not use, and a "
                    "key path or value that holds one is set in double quotation marks. Square brackets mark our "
                    "changes: a value wholly in square brackets describes the stamped value rather than quoting it" +
                    (", and a bracketed phrase inside a quoted value replaces the words the next notes name." if glossed or redacted
                     else ".") + " Panel 1 gives the SHA-256 values these rows name, in full.")]]
    if glossed:
        notes.append([label(REGISTER_NOTE)])
    if redacted:
        notes.append([label(f"In stamped text, a reviewing session's name and review round are replaced by {REVIEW_NOTE}.")])
    caption = {"tier": [label("disclosure (data README)")]}
    # Edith, proof 3 (p. 39): the parts were split by columns, so one landscape page held only the field and the stamped value (about 40%
    # filled) and the next only the field and the paper's wording. Split by rows instead: every part carries all three columns, so the
    # caption's "beside the wording" is true on every page. Her checker (page-fill, §1.4: at least 60% of the 6.5-in page): the rows
    # are tall and wrap, so they are spaced (a little air between rows, more where the file changes: main, groupc, topup), which
    # also reads better. Measured (footnotesize, 9 in): 4, 3 and 4 rows take 4.58, 4.26 and 3.97 in of the 6.5-in page (70%, 66% and
    # 61%, the last with the notes). Every other split of the 11 rows into three parts leaves a part under 60% (3, 4, 4: 57%;
    # 5, 2, 4: 46%) or taller than the page (two parts were taller still, unspaced): the build stops if the rows change.
    if len(rows) != 11:
        raise ValueError("TAB-22: the row split (4, 3 and 4 rows, spaced) was measured for 11 rows: measure the parts again")
    t = Table([label(c) for c in ("Stamped field", "Stamped value (or [a description])", "In the paper")], rows, notes, caption,
              layout="split landscape", split_key=[0], font="footnotesize", spaced=True,
              groups=[i for i in range(1, len(rows)) if rows[i][0].printed.split(":")[0] != rows[i - 1][0].printed.split(":")[0]],
              split_parts=[(list(range(0, 4)), [1, 2]), (list(range(4, 7)), [1, 2]), (list(range(7, 11)), [1, 2])])
    t.panels = [("SHA-256 values named in the rows", _hash_panel(S))]
    _printed_plain(t, "TAB-22")
    return t


# ================================================================ TAB-23: reproducibility

# Every commit is printed by its first seven characters (each resolves to one commit in the repository), whatever length the record
# writes it at: the cut takes the first seven hex digits of the recorded id.
SHORT = r"([0-9a-f]{7})[0-9a-f]*"
# (row name, pinned source, (text source, line regex, commit regex) for the commit the analysis ran at, or None). The rows are the
# released files the paper's tables cite: the analysis files, and Study 1's reporting definitions, whose numbered items the appendix
# tables cite as "(item N)" (Q22).
REPORTING_DEFS = "reporting_defs_release"
ANALYSES = (
    ("Study 1 analysis", "main", ("log", r"^`python3 -m harness\.analysis\.main_analysis ", r"checkout at " + SHORT)),
    ("Study 1 k.json", "main_k", ("log", r"^`python3 -m harness\.analysis\.k_step`", r"clean checkout at the stamped " + SHORT)),
    ("Study 1 keep-list analyses", "groupc", ("log", r"^`python3 -m harness\.analysis\.report_groupc", r"checkout at " + SHORT)),
    ("Study 1 reporting definitions", REPORTING_DEFS, None),
    ("Study 1b analysis", "s1b", ("log", r"^`python3 -m harness\.analysis\.study1b --run", r"commit " + SHORT)),
    ("Study 1b k.json", "s1b_k", ("log", r"^`python3 -m harness\.analysis\.study1b_k", r"commit " + SHORT)),
    ("Top-up analysis", "topup", None),
    ("Length sweep curve (Deviation 2 rule)", "curve_d90", None),
    ("Length sweep curve (original rule)", "curve", None),
)
# The nine rows' names, in order: what TAB-23's caption fact says the table lists (checked at build).
FILE_ROWS = ["Study 1 analysis", "Study 1 k.json", "Study 1 keep-list analyses", "Study 1 reporting definitions", "Study 1b analysis",
             "Study 1b k.json", "Top-up analysis", "Length sweep curve (Deviation 2 rule)", "Length sweep curve (original rule)"]
assert [a[0] for a in ANALYSES] == FILE_ROWS
# The run file whose SHA-256 each analysis file records about its own inputs: (key in that file, the file's name, the run).
RECORDED: Dict[str, Tuple[str, str, str]] = {
    "main": ("k.compact_table_sha256", "compact_table.csv", "main-l14n6-1"),
    "main_k": ("compact_table_sha256", "compact_table.csv", "main-l14n6-1"),
    "groupc": ("inputs.calls_jsonl_sha256", "calls.jsonl", "main-l14n6-1"),
    "s1b": ("inputs.calls_sha256", "calls.jsonl", "study1b-1"),
    "s1b_k": ("compact_table_sha256", "compact_table.csv", "study1b-1"),
    "topup": ("inputs.run['calls.jsonl_sha256']", "calls.jsonl", "topup-1"),
}
# The run commit as each spend-log row's "What ran" cell states it.
RUN_COMMIT_RX = r"(?:clean detached checkout at (?:the price-date commit )?|run from M \()" + SHORT
_HASHED = r"`([\w.]+)` ([0-9a-f]{64})"


def _run_files(S: Store) -> List[Tuple[int, str, Ref, Ref, List[str]]]:
    """(line, run id, What-ran ref, Notes ref, hashed file names) for every spend-log row that states a run commit, oldest first."""
    out = []
    for n, run in _spend_rows(S):
        what = cell_ref(S, "spend_log", n, "What ran")
        if not re.search(RUN_COMMIT_RX, str(what.value)):
            continue
        notes = cell_ref(S, "spend_log", n, "Notes")
        out.append((n, run, what, notes, [m.group(1) for m in re.finditer(_HASHED, str(notes.value))]))
    return out


def _spend_hash(S: Store, run: str, name: str) -> Optional[str]:
    for n, r, what, notes, names in _run_files(S):
        if r == run and name in names:
            return re.search(rf"`{re.escape(name)}` ([0-9a-f]{{64}})", str(notes.value)).group(1)
    return None


def _git_commits(S: Store, *args: str) -> List[str]:
    """The full ids `git log` lists for `args`, newest first (read-only). Disk mode refuses: a copy without the history has no log."""
    need_history(S, f"TAB-23's pin check (git log {' '.join(args)})")
    out = subprocess.run(["git", "-C", str(S.repo), "log", "--format=%H", *args], check=True, capture_output=True, text=True).stdout
    return out.split()


def _pin_history(S: Store, src: str, data_file: bool) -> Cell:
    """The evidence for TAB-23's note on a listed file's commit, checked in the history of the commit being built (HEAD; main once the
    outputs are merged): the pinned commit is the last commit that touched the file, and, for a data file, also the one commit that
    added it (so the file has not changed since it was committed). Returned unprinted, with the pin among its sources."""
    pin = S.sources[src]
    last = _git_commits(S, "-1", "HEAD", "--", pin.path)
    if len(last) != 1 or not last[0].startswith(pin.commit):
        raise ValueError(f"TAB-23: {pin.path}: the pinned {pin.commit} is not the last commit that touched it ({last})")
    what = "the pin is the last commit in HEAD's history that touched the file"
    if data_file:
        added = _git_commits(S, "--diff-filter=A", "HEAD", "--", pin.path)
        if added != last:
            raise ValueError(f"TAB-23: {pin.path}: the pinned {pin.commit} is not the one commit that added it ({added})")
        what += ", and the one commit that added it"
    return unprinted(Cell(pin.commit, raw=pin.commit, refs=(S.ref(src, "@commit"),),
                          formula=f"git log -1 HEAD -- {pin.path}" + (" and git log --diff-filter=A HEAD" if data_file else "")), what)


def _f54(S: Store) -> Cell:
    """Findings register section 5.4's heading, which the printed words "our record of the code used after the locks" name: checked
    and kept in the cell's sources, not printed (the register's name and section number are internal)."""
    return guard(cell_ref(S, "findings", line_of(S, "findings", r"^\*\*5\.4 Code used after the locks", expect=1)),
                 r"^\*\*5\.4 (Code used after the locks)\.\*\*", "section 5.4 is the record of the code used after the locks")


def _run_panel(S: Store) -> Table:
    rows: List[List[Cell]] = []
    for n, run, what, notes, names in _run_files(S):
        rid, commit = text_of(cell_ref(S, "spend_log", n, "Run ID")), extract(what, RUN_COMMIT_RX)
        if not names:
            rows.append([rid, commit, DASH, DASH])
        for name in names:
            rows.append([rid, commit, extract(notes, rf"`({re.escape(name)})` [0-9a-f]{{64}}"),
                         extract(notes, rf"`{re.escape(name)}` ([0-9a-f]{{64}})")])
    # The main run's commit must be the one findings register 5.4 names as the commit it ran from.
    main = [r for r in _run_files(S) if r[1] == "main-l14n6-1"][0]
    f54 = cell_ref(S, "findings", line_of(S, "findings", r"^  - main runner d364c24", expect=1))
    ran = extract(f54, r"→ ([0-9a-f]{7}) \(the commit the main run ran from")
    if extract(main[2], RUN_COMMIT_RX).raw != ran.raw:
        raise ValueError("TAB-23: the spend log's main-run commit is not findings register 5.4's")
    # The spend log prints as "our cost records" and findings register 5.4 as "our record of the code used after the locks" (PO-1).
    notes = [[_seq("Run commit: the commit each paid run ran from, as its row in our cost records states it; raw files: the SHA-256 of "
                   "each run file its row lists (our cost records at commit", text_of(S.ref("spend_log", "@commit")),
                   "). Rows with a dash list no file hashes. The main run's commit is also the one "
                   "our record of the code used after the locks names as the commit it ran from:", ran, ".", _f54(S))]]
    return Table([label(c) for c in ("Run", "Run commit", "Raw file", "SHA-256")], rows, notes, layout="longtable", mono=[1, 3],
                 groups=group_starts(rows, 0))


def _release_note(S: Store) -> List[Cell]:
    """The release note: Study 1's reporting definitions are listed as written. Its two clauses about that file are guarded on the file
    itself: it cites a decision number and names one of our own work sessions. (Until the release terms were set, 2026-11-01, D-206 and
    D-207, it began "This list of released files is provisional, pending the release terms."; the caption says which listed files are not
    released, so which hashes cannot be checked from the release.)"""
    ids = cell_ref(S, REPORTING_DEFS, line_of(S, REPORTING_DEFS, r"\bD-93\b"))
    names = cell_ref(S, REPORTING_DEFS, line_of(S, REPORTING_DEFS, r"\bFriday's three group-B modules\b"))
    return [_seq("Study 1's reporting definitions are listed as written: they cite internal decision numbers",
                 guard(ids, r"\b(D-93)\b", "the file cites a decision number"),
                 "and name our own work sessions",
                 guard(names, r"\b(Friday)'s three group-B modules\b", "the file names one of our work sessions"),
                 "; the record those numbers refer to is not released.")]


@output("TAB-23")
def tab_23(S: Store) -> Table:
    rows = []
    for name, src, code in ANALYSES:
        if src == "topup":
            code_cell = extract(S.ref("topup", "code.git.commit"), "^" + SHORT)
        elif code is not None:
            tsrc, line_rx, cut = code
            code_cell = extract(cell_ref(S, tsrc, line_of(S, tsrc, line_rx, expect=1)), cut)
        else:
            code_cell = DASH
        if src in RECORDED:
            key, fname, run = RECORDED[src]
            rec = S.ref(src, key)
            if rec.value != _spend_hash(S, run, fname):
                raise ValueError(f"TAB-23: {src}:{key} is not the SHA-256 of {fname} in {run}'s spend-log row")
            fcell, hcell = label(fname), text_of(rec)
        else:
            fcell, hcell = DASH, DASH
        rows.append([label(name), text_of(S.ref(src, "@path")), text_of(S.ref(src, "@commit")), text_of(S.ref(src, "@sha256")),
                     code_cell, fcell, hcell])
    # The claims-ledger format's source field (section 2), and its short SHA-256s of the three analyses, which must start the pinned ones.
    src_line = cell_ref(S, "claims_format", line_of(S, "claims_format", r"^\| `source` \|", expect=1), "What it holds")
    for short, pin in (("Study 1", "main"), ("Study 1b", "s1b"), ("the top-up", "topup")):
        got = extract(src_line, rf"{re.escape(short)} `([0-9a-f]+)…`")
        if not SOURCES[pin].sha256.startswith(got.raw):
            raise ValueError(f"TAB-23: the claims-ledger format's {short} hash {got.raw} does not start the pinned {pin} SHA-256")
    req = cell_ref(S, "requirements", line_of(S, "requirements", r"^anthropic==", expect=1))
    tools = cell_ref(S, "findings", line_of(S, "findings", r"^- Tools: anthropic==", expect=1))
    client = extract(req, r"^(anthropic==\S+)$")
    if client.raw not in str(tools.value):
        raise ValueError("TAB-23: the requirements pin and findings register 5.4's tool list name different API clients")
    # Section 7 of the format renames the row's `source` field `sources`, one {path, commit, sha256} entry per file, and keeps the pins:
    # `commit` is the last commit on main that touched the file. The note's further claims are checked, not assumed: in the history
    # of the commit being built, every listed file's pin is the last commit that touched it and each data file's is also the one
    # commit that added it (`_pin_history`); the reporting definitions' pin is the revision both Study 1 analyses cite
    # (`_reporting_defs_cited`).
    sources7 = cell_ref(S, "claims_format", line_of(S, "claims_format", r"^\d\. \*\*More than one source per row\.\*\* `source` becomes `sources: ",
                                                    expect=1))
    pins7 = cell_ref(S, "claims_format", line_of(S, "claims_format", r"The pins are unchanged: `commit` is the last commit on main that "
                                                 r"touched the file", expect=1))
    if pins7.key != f"L{int(sources7.key[1:]) + 1}":
        raise ValueError("TAB-23: the claims-ledger format's pin rule is not the line after its `sources` rule")
    data_srcs = [src for _, src, _ in ANALYSES if src != REPORTING_DEFS]
    if any(not S.sources[src].path.startswith("data/") for src in data_srcs) or S.sources[REPORTING_DEFS].path.startswith("data/"):
        raise ValueError("TAB-23: the rows other than Study 1's reporting definitions are not all data files")
    cited, items_main, items_groupc = _reporting_defs_cited(S)
    notes = [[_seq("Path, Commit and SHA-256 are each file's entry in the claims ledger's",
                   extract(sources7, r"`source` becomes `(sources): \{"), "field,",
                   extract(src_line, r"^`(\{path, commit, sha256\})`"),
                   ", so a ledger row and this table cite a file the same way. The commit is",
                   extract(pins7, r"`commit` is (the last commit on main that touched the file)"),
                   ": for each data file, the commit that added it; for Study 1's reporting definitions, the revision that the Study 1 "
                   "analysis and the keep-list analyses cite. Each file is read from that commit, and its SHA-256 is checked against the "
                   "bytes before any table is built.",
                   *[_pin_history(S, src, src != REPORTING_DEFS) for _, src, _ in ANALYSES], *cited)],
             [_seq("Item numbers in the appendix tables ('item N') refer to the numbered items of Study 1's reporting definitions at that "
                   "revision: the Study 1 analysis cites items", items_main, "there, and the keep-list analyses items", items_groupc,
                   ".", *cited)],
             [label("Code commit: the commit the analysis ran at, from our work log's entry for each driver run (the top-up file stamps its "
                    "own). Run file recorded: the run file whose SHA-256 the analysis file itself records about its inputs (for the Study "
                    "1 analysis, the compact table that k was computed from); each equals the hash in that run's row of our cost records "
                    "(the run panel). A dash: no such record (our work log names no commit for the curve runs, and the curve files "
                    "record no run-file hash; the reporting definitions are a text file, not a run's output). Commits here and in the "
                    "run panel are shortened to their first seven characters.")],
             [_seq("Tools for the paid runs and the analyses:", extract(tools, r"^- Tools: (.+)\.$"),
                   "(our record of the code used after the locks", _f54(S), "); the API client pinned in harness/requirements.txt:",
                   client, ".")],
             [label("The paper-outputs code, its figure-library pins and every output's SHA-256 are in data/paper-outputs/MANIFEST.json.")],
             _release_note(S)]
    # Edith, proof 3 (p. 129): the supplement's text said the table lists "the three analysis files", but it lists nine files, the three
    # analysis files among them. The caption fact names them; the build stops if the rows are not these.
    if [r[0].printed for r in rows] != FILE_ROWS:
        raise ValueError("TAB-23: the listed files are not the nine the caption fact names: rewrite its 'files' fact")
    # Edith, proof 4 (p. 131): three rows print a dash for the code commit (no record names one), so "each with its ... code commit" was
    # not true of every file: the fact says "where one is recorded", and the build stops unless the dash rows are exactly those three.
    if [r[0].printed for r in rows if r[4].printed == DASH.printed] != [
            "Study 1 reporting definitions", "Length sweep curve (Deviation 2 rule)", "Length sweep curve (original rule)"]:
        raise ValueError("TAB-23: the files with no code commit are no longer the reporting definitions and the two curve files: "
                         "rewrite the 'files' fact")
    caption = {"tier": [label("disclosure (reproducibility)")],
               "files": [label("nine files: the three analysis files (Study 1, Study 1b and the top-up), the two k.json files (Study 1 and "
                               "Study 1b), Study 1's keep-list analyses and reporting definitions, and the length sweep's two curves "
                               "(Deviation 2 rule and original rule), each with its SHA-256 hash and, where one is recorded, its code "
                               "commit (the reporting definitions and the two curve files have none); the paid-runs panel lists each "
                               "run's commit and the SHA-256 of each raw file its cost record lists")]}
    # "Commit" is the claims-ledger field's own name (`commit`): the last commit that touched the file, which for the reporting
    # definitions is a revision, not the commit that added them (note 1).
    # Eight footnotesize points: at \small the float was 6.41 in of the 6.5 in sideways block, inside the 0.17 in the printed floats can
    # run taller than the estimate (Edith, proof 4, S34; §5.4 has no tolerance). At 8 pt the writer widened both hash columns to 1.46 in
    # (about 25 typewriter characters), which broke the 64-character hashes 24/24/16; proof 4 printed them in lines of 16, which Edith's S9
    # row names as the form to follow, so the two hash columns are set to hold 16 characters but not 17 (16 x 4.2 pt + 0.04 in = 0.97 in;
    # 0.98 in with a margin for the width estimate). The widths are the writer's plan in inches, which add up to the 7.33 in the seven
    # columns share (the writer's plan: File 0.945, Path 2.046, hashes 1.459 each, Code commit 0.447, Run file recorded 0.976): the hash
    # columns' spare (0.96 in) goes to File and Path in proportion.
    t = Table([label(c) for c in ("File", "Path", "Commit", "SHA-256", "Code commit", "Run file recorded", "Recorded SHA-256")],
              rows, notes, caption, layout="landscape", mono=[2, 3, 4, 6], font="footnotesize")
    set_widths(t, File=1.247, Path=2.701, SHA_256=0.98, Recorded_SHA_256=0.98)
    t.panels = [("Paid runs: run commit and raw-file SHA-256s (our cost records)", _run_panel(S))]
    _printed_plain(t, "TAB-23")
    return t


def _reporting_defs_cited(S: Store) -> Tuple[List[Cell], Cell, Cell]:
    """The stamped notes that name Study 1's reporting definitions: the Study 1 analysis's reporting items (group B) and the keep-list
    analyses' conventions. Each must name the pinned path at the pinned commit, so the listed revision is the one both analyses cite.
    Returns those checks (unprinted) and the item range each note cites there (printed)."""
    rd = S.sources[REPORTING_DEFS]
    cited, items = [], []
    for src, key in (("main", "reporting.group_b.note"), ("groupc", "note")):
        r = S.ref(src, key)
        got = extract(r, re.escape(rd.path) + r" \(([0-9a-f]{7})\b")
        if not rd.commit.startswith(got.raw):
            raise ValueError(f"TAB-23: {src}:{key} names Study 1's reporting definitions at {got.raw}, not the pinned {rd.commit}")
        cited.append(unprinted(got, f"{src}:{key} names the reporting definitions at the pinned commit"))
        items.append(extract(r, re.escape(rd.path) + r" \([0-9a-f]{7}[^)]*\), items (\d+-\d+)\b"))
    return cited, en_dash(items[0]), en_dash(items[1])          # "items 7–24" (Edith §2.4: a range takes an en dash)
