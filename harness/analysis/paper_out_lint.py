"""The table checks Edith's polish standard gives Friday (ops/reviews/polish-standard.md §13: "Table cells: decimals per column,
constant columns, headers and units, note length, symbols defined (§2.8, §7.2-6)"), run on every table the build writes, plus the
spelling system (§3.3, D-162: British) on every printed text of a table.

Each check returns readable problems (never a cell's raw value beyond what it prints). paper_outputs records them in the manifest and
refuses a paper version (<id>.main) or a body table that has any; a full table's problems are reported until the supplement pass
(batch g) gives every full table a layout.
"""

from __future__ import annotations

import ast
import functools
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Optional, Pattern, Sequence, Tuple

from . import paper_out_core as core
from .paper_out_core import Cell, Table

BODY_TABLES = ("TAB-35", "TAB-01", "TAB-24")      # Tables 1-3 (D-159): at most 8 columns and 12 rows (§7.2)
MAX_COLUMNS, MAX_BODY_ROWS = 8, 12
NOTE_LINES = 2                                     # a note prints in at most two lines of \footnotesize (§7.5)

# A number as printed: an optional sign, digits with comma thousands, an optional decimal part (its length is the decimals).
NUMBER = re.compile(r"(?<![\w.])[−+]?\d{1,3}(?:,\d{3})+(?:\.(\d+))?(?![\w])|(?<![\w.])[−+]?\d+(?:\.(\d+))?(?![\w])")
BRACKET = re.compile(r"\[[^\]]*\]")
# Where the one-more-decimal rule (core.guarded_dp) may add a decimal: near 0, 100, the margins, and 1 (a share's upper end, which
# a spend share of 0.9998 would otherwise print as 1.000).
BOUNDS = (0.0, 1.0, 5.0, -5.0, 10.0, -10.0, 100.0)
# Symbols a reader must find defined in the caption or a note (§7.5).
SYMBOLS = ("≤", "†", "‡", "*", "exact")
# Words that keep their capital inside a sentence-case header (proper names, §3.4).
PROPER = {"Haiku", "Sonnet", "Opus", "Fable", "Claude", "Study", "Studies", "Test", "Tests", "Holm", "Wilson", "Pilot", "Lock",
          "Locks", "US", "SHA", "CI", "Bonferroni", "Wald", "Newcombe", "Clopper", "Pearson", "Anthropic", "TMLR", "Batch", "Table",
          "Figure", "Section", "Appendix", "I", "II", "N", "R", "O", "S"}
# A capitalised word followed by a number or a one-letter name is a name ("Deviation 2", "Flag R", "Lock 4").
NAMED = re.compile(r"\b([A-Z][a-z]+)\s+(?:\d|[A-Z]\b)")
# A header may start with a symbol in lower case ("k; cost ratio", "d (points)", "p", "q^N").
SYMBOL_START = re.compile(r"^(?:[a-z](?:_[a-zA-Z])?|q\^N|local\^N)(?:\W|$)")

# American spellings the paper does not use (D-162: British throughout). Words that only end in -ize are listed as exceptions.
AMERICAN = re.compile(r"\b(?:\w+(?:iz(?:e|es|ed|ing|ation|ations|er|ers))|\w*yz(?:e|es|ed|ing)|behaviou?rs?|colors?|colored|favou?r(?:s|ed|ing)?"
                      r"|honors?|labeled|labeling|modeled|modeling|traveled|canceled|centers?|centered|grays?|defense|fulfill)\b", re.I)
NOT_AMERICAN = {"size", "sizes", "sized", "prize", "prizes", "seize", "seized", "capsize", "maize", "behaviour", "behaviours",
                "favour", "favours", "favoured", "favouring"}


def _numbers(text: str) -> Tuple[List[Tuple[float, int]], List[Tuple[float, int]]]:
    """A cell's printed numbers as (value, decimals): the points (outside brackets) and the interval ends (inside), each in order."""
    def parse(s: str) -> List[Tuple[float, int]]:
        out = []
        for m in NUMBER.finditer(s):
            frac = m.group(1) if m.group(1) is not None else m.group(2)
            out.append((float(m.group(0).replace(",", "").replace("−", "-")), len(frac or "")))
        return out
    ends = [x for b in BRACKET.findall(text) for x in parse(b)]
    return parse(BRACKET.sub(" ", text)), ends


def _guarded(v: float, dp: int) -> bool:
    """Could the one-more-decimal rule have printed v with dp + 1 decimals: is it within one unit of the dp-th place of a bound?"""
    return any(abs(v - b) <= 10 ** -dp + 1e-12 for b in BOUNDS)


def decimals(t: Table) -> List[str]:
    """§2.8: every cell in a column has the same number of decimals (a dollar column: three significant figures, §2.1, a whole
    number of more digits allowed). Numbers are compared by role (points; interval ends) and by
    position counted from the right ("40; 0.909" against "—; 2.48" compares 0.909 with 2.48). A text cell is not compared. The one
    exception is a number one decimal longer than its column's that the one-more-decimal rule could have printed (near 0, 100 or a
    margin)."""
    out = []
    for j, head in enumerate(t.columns):
        cells = [(i, r[j].printed) for i, r in enumerate(t.rows)
                 if r[j].printed not in core.DASHES and core.NUMERIC_TEXT.match(r[j].printed)]
        if "threshold" in head.printed.lower():           # thresholds and constants: exact, never padded (§2.1, §2.8)
            for i, p in cells:
                for m in NUMBER.finditer(p):
                    if re.search(r"\.\d*0$", m.group(0)):
                        out.append(f"column {head.printed!r}, row {i + 1}: {m.group(0)} is padded with zeros (a threshold prints exact)")
            continue
        if "median" in head.printed.lower() and "token" in head.printed.lower():    # token medians print as stamped (Edith, #39 review
            for i, p in cells:                                                       # S1): a whole number or a half, aligned by the point
                for m in NUMBER.finditer(p):
                    if not re.fullmatch(r"[−+]?\d[\d,]*(?:\.5)?", m.group(0)):
                        out.append(f"column {head.printed!r}, row {i + 1}: {m.group(0)} is not a token median as stamped (whole or a half)")
            continue
        if "$" in head.printed:                           # dollars: three significant figures (§2.1), not one decimal count
            for i, p in cells:
                for m in NUMBER.finditer(p):
                    digits = re.sub(r"^[−+]?[0,.]*", "", m.group(0)).replace(".", "").replace(",", "")
                    if len(digits) != 3 and not (len(digits) > 3 and "." not in m.group(0)):
                        out.append(f"column {head.printed!r}, row {i + 1}: {m.group(0)} is not three significant figures")
            continue
        for role in (0, 1):
            seqs = [(i, _numbers(p)[role]) for i, p in cells]
            depth = max([len(s) for _, s in seqs] + [0])
            for k in range(1, depth + 1):
                at = [(i, s[-k]) for i, s in seqs if len(s) >= k]
                if len(at) < 2:
                    continue
                # the column's own count: its commonest, or its smallest when the longer ones are all guard cells
                def odd(base: int) -> List[Tuple[int, int]]:
                    return [(i, dp) for i, (v, dp) in at if dp != base and not (dp == base + 1 and _guarded(v, base))]
                mode = sorted(Counter(dp for _, (_, dp) in at).items(), key=lambda x: (-x[1], x[0]))[0][0]
                base = min((mode, min(dp for _, (_, dp) in at)), key=lambda b: (len(odd(b)), b != mode))
                for i, dp in odd(base):
                    what = "interval end" if role else "number"
                    out.append(f"column {head.printed!r}, row {i + 1}: a {what} with {dp} decimals where the column has {base}")
    return out


def constant_columns(t: Table) -> List[str]:
    """§7.3: no column with one value in every row (it belongs in the caption or a note)."""
    if len(t.rows) < 2:
        return []
    return [f"column {c.printed!r} prints {t.rows[0][j].printed!r} in every row" for j, c in enumerate(t.columns)
            if len({r[j].printed for r in t.rows}) == 1]


def headers(t: Table) -> List[str]:
    """§3.4 and §7.4: sentence-case headers (a symbol may start one in lower case; proper names keep their capitals), and units in
    the header, never a % or $ in a cell."""
    out = []
    for c in t.columns:
        h = c.printed
        words = re.findall(r"\b[A-Za-z][A-Za-z']*\b(?!\d)", h)                         # "B1" is a name, not a word
        named = set(NAMED.findall(h))
        if words and not h[0].isupper() and not SYMBOL_START.match(h) and not h[0].isdigit():
            out.append(f"header {h!r} does not start with a capital")
        for w in words[1:]:
            if w[0].isupper() and w not in PROPER and w not in named and not (len(w) > 1 and w.isupper()):
                out.append(f"header {h!r}: {w!r} is capitalised (sentence case)")
    for i, r in enumerate(t.rows):
        for j, c in enumerate(r):
            if c.kind == "num" and core.NUMERIC_TEXT.match(c.printed) and re.search(r"\d\s*%|\$\s*\d", c.printed):
                out.append(f"column {t.columns[j].printed!r}, row {i + 1}: a unit in the cell ({c.printed!r}); it belongs in the header")
    return out


def _lines(text: str, landscape: bool) -> int:
    width = (9.0 if landscape else 6.5) * core.PT_PER_IN
    return core._wrapped_lines(core._pieces(core.label(text) if core.label_ok(text) else Cell(text), "footnotesize"), width)


def notes(t: Table, short_only: bool) -> List[str]:
    """§7.5: a note is at most two lines of \\footnotesize at the table's width (the paper prints the short notes; the supplement
    every note). Vision's converter prints a paper table's notes as one paragraph, so in the paper that paragraph is the note (Edith's
    proof 2 reading): all its short notes together take at most two lines."""
    land = (t.layout or "").endswith("landscape")
    out = []
    shown = []
    for k, n in enumerate(t.notes):
        if short_only and k not in t.short_notes:
            continue
        text = " ".join(c.printed for c in n if c.printed)
        shown.append(text)
        if _lines(text, land) > NOTE_LINES:
            out.append(f"note {k + 1} takes {_lines(text, land)} lines (at most {NOTE_LINES}): {text[:60]!r}…")
    block = " ".join(shown)
    if short_only and len(shown) > 1 and _lines(block, land) > NOTE_LINES:
        out.append(f"the printed notes take {_lines(block, land)} lines together (at most {NOTE_LINES}, one paragraph): {block[:60]!r}…")
    return out


ERROR_RATIO = re.compile(r"error[- ]rate ratio|error ratio", re.I)


def paper_precision(t: Table) -> List[str]:
    """§2.1 (amended 2026-10-19): an error-rate ratio prints at 1 decimal in every paper table (the supplement keeps more)."""
    out = []
    for j, head in enumerate(t.columns):
        if not ERROR_RATIO.search(head.printed):
            continue
        for i, r in enumerate(t.rows):
            if r[j].printed in core.DASHES or not core.NUMERIC_TEXT.match(r[j].printed):
                continue                                  # a text cell ("undefined (comparator errors 0 of 80)") holds counts
            pts, ends = _numbers(r[j].printed)
            for v, dp in pts + ends:
                if dp != 1 and not (dp == 2 and _guarded(v, 1)):
                    out.append(f"column {head.printed!r}, row {i + 1}: an error-rate ratio with {dp} decimals (1 in the paper)")
    return out


RANGE_HYPHEN = re.compile(r"\b(?:Tests?|Sections?|Tables?|Figures?|Locks?|Studies|Pilots?|pp?\.)\s+\d+-\d+\b|\bB\d-B\d\b")
LOCK_LOWER = re.compile(r"\block \d")


def forms(t: Table, short_only: bool = False) -> List[str]:
    """§2.4: a table's interval carries no "+" ("[−1.2, 2.4]") and a range takes an en dash ("Tests 1–3"); one name per term:
    "Lock 1" to "Lock 4" (Edith, proof 2)."""
    out = []
    for x in printed_texts(t, short_only):
        plain = QUOTED.sub(" ", x)
        if any("+" in b for b in BRACKET.findall(plain)):
            out.append(f"a '+' inside a bracketed interval: {x[:60]!r}")
        out += [f"a range with a hyphen {m.group(0)!r} (an en dash)" for m in RANGE_HYPHEN.finditer(plain)]
        out += [f"{m.group(0)!r}: the lock's name is capitalised ('Lock N')" for m in LOCK_LOWER.finditer(plain)]
    return sorted(set(out))


def symbols(t: Table, short_only: bool) -> List[str]:
    """§7.5: every symbol a cell prints (≤, †, ‡, *, "exact") is defined in the caption facts or a printed note."""
    shown = [n for k, n in enumerate(t.notes) if not short_only or k in t.short_notes]
    defined = " ".join(c.printed for n in shown for c in n) + " " + " ".join(c.printed for v in (t.caption or {}).values() for c in v)
    used = {s for r in t.rows for c in r for s in SYMBOLS if s in c.printed}
    return [f"{s!r} is printed in a cell but not defined in a printed note or the caption" for s in sorted(used) if s not in defined]


def bold(t: Table) -> List[str]:
    """§7.6: bold marks only the decision column's headline."""
    return [f"a bold cell in column {t.columns[j].printed!r} (bold is for the decision column only)"
            for r in t.rows for j, c in enumerate(r) if c.bold and "decision" not in t.columns[j].printed.lower()]


def size(t: Table, oid: str, paper: bool) -> List[str]:
    """§7.2 and D-160: a paper table has at most 8 columns; a body table (Tables 1-3) at most 12 rows."""
    out = []
    if paper and len(t.columns) > MAX_COLUMNS:
        out.append(f"{len(t.columns)} columns (at most {MAX_COLUMNS} in the paper)")
    if paper and oid in BODY_TABLES and len(t.rows) > MAX_BODY_ROWS:
        out.append(f"{len(t.rows)} rows (at most {MAX_BODY_ROWS} in a body table)")
    return out


# Karen's list of D-161's retired project terms (her `ledger.py lint --vocab`), read from her file at a pinned commit (SHA-256 checked;
# parsed, not executed), so the paper's text and Friday's outputs are checked against one list. A term inside quotation marks passes.
VOCAB_PIN = ("research/paper-notes/tools/ledger.py", "cbec674", "8dc841567e6e85f349ccc9d39f558f5679646bdd02f3d85b3cc653b70bbc09ac")
# Single quotes count only as a pair that opens before a word and closes after one, so two apostrophes ("the vote's ... each arm's")
# never hide the words between them.
QUOTED = re.compile(r"\u201c[^\u201d]*\u201d|\u2018[^\u2019\n]{1,40}\u2019(?![A-Za-z])|\"[^\"\n]*\"|(?<![A-Za-z0-9])'[^'\s][^'\n]{0,39}'(?![A-Za-z])")
ROOT = Path(__file__).resolve().parents[2]


@functools.lru_cache(maxsize=1)
def karen_vocab() -> Tuple[Tuple[Pattern, str], ...]:
    raw = core.pinned_bytes(ROOT, VOCAB_PIN[1], VOCAB_PIN[0])      # from its commit, or from disk in disk mode
    if hashlib.sha256(raw).hexdigest() != VOCAB_PIN[2]:
        raise ValueError(f"{VOCAB_PIN[0]} at {VOCAB_PIN[1]}: SHA-256 differs from the pinned one")
    for node in ast.parse(raw.decode("utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "VOCAB":
            return tuple((re.compile(p, re.I), why) for p, why in ast.literal_eval(node.value))
    raise ValueError(f"{VOCAB_PIN[0]}: no VOCAB list")


def vocabulary_texts(texts: Iterable[str]) -> List[str]:
    """§3.1 and D-161: no retired project term outside quotation marks (Karen's list)."""
    hits: Counter = Counter()
    why = {}
    for x in texts:
        plain = QUOTED.sub(" ", x)
        for rx, w in karen_vocab():
            for m in rx.finditer(plain):
                hits[m.group(0).lower()] += 1
                why[m.group(0).lower()] = w
    return [f"retired term {k!r} x{n} (D-161: {why[k]})" for k, n in sorted(hits.items())]


def printed_texts(t: Table, short_only: bool = False) -> Iterable[str]:
    """What prints: headers, cells and the printed notes (a paper version prints its short notes). Caption facts do not print: Vision
    writes each caption from them."""
    yield from (c.printed for c in t.columns)
    yield from (c.printed for r in t.rows for c in r)
    yield from (c.printed for k, n in enumerate(t.notes) if not short_only or k in t.short_notes for c in n)


def spelling(t: Table, short_only: bool = False) -> List[str]:
    """§3.3 and D-162: British spelling in every printed text (headers, cells, printed notes)."""
    found = sorted({m.group(0) for x in printed_texts(t, short_only) for m in AMERICAN.finditer(x) if m.group(0).lower() not in NOT_AMERICAN})
    return [f"American spelling {w!r} (D-162: British)" for w in found]


# Problems accepted for now, each with its reason and who decides: (file stem, the problem's start) -> reason. (Table 2's cost-ratio
# decimals, once waived here, are settled by Edith's §2.1/§2.8 ruling: the column names each cell's quantity.)
WAIVERS: dict = {}


def is_paper(oid: str, stem: str, t: Table) -> bool:
    """<id>.main is the paper's version; a body table's own file is its paper version when it has no .main; any other file is a full
    table for the supplement."""
    return stem.endswith(".main") or (oid in BODY_TABLES and stem == oid and t.main_table is None)


def unwaived(stem: str, problems: Sequence[str]) -> List[str]:
    return [p for p in problems if not any(stem == s and p.startswith(start) for s, start in WAIVERS)]


def table_problems(t: Table, oid: str, stem: str) -> List[str]:
    """Every check on one written table. A paper version is checked against the notes it prints (its short notes); a full table
    against every note (the supplement prints them all)."""
    paper = is_paper(oid, stem, t)
    short = paper
    # §7.5's two-line cap is for the notes the paper prints; a full table's notes keep their full text (Edith's ruling, §12.2)
    return (size(t, oid, paper) + decimals(t) + constant_columns(t) + headers(t) + (notes(t, short) if paper else [])
            + (paper_precision(t) if paper else []) + forms(t, short) + symbols(t, short) + bold(t)
            + spelling(t, short) + vocabulary_texts(printed_texts(t, short))
            + [f"caption fact: {p}" for p in vocabulary_texts(c.printed for v in (t.caption or {}).values() for c in v)])
