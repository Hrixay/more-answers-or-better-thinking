"""The anonymous TMLR copy's variants of the tables that name the public proofs (D-150, D-152): TAB-19 and TAB-20, each with its panels.
Vision's anonymous build (paper/tools/build_overleaf.py --anonymous) takes `X.anon.tex` in place of `X.tex` wherever one exists, so
a panel's variant is `X.panelN.anon.tex`.

D-150 keeps the commit IDs and SHA-256 fingerprints and withholds the gist IDs, Zenodo DOIs and Wayback IDs; D-152 gives the words.
A variant is made from the built table by rule, never retyped: every cell, column title and note keeps its sources, and its printed text
is rewritten by ANON_RULES in order (identifiers first, then the services' names in neutral words: a public posting, an archived
snapshot, an archive record; a capital only where a cell or sentence starts); times, commits and hashes are left as they are. A note gives D-152's sentence, cut from the register row.
The result must pass Vision's anonymous scan (her SERVICES, PEOPLE and HANDLES patterns, read from paper/tools/anon.py at ANON_PIN),
or the build stops; the rules' firing counts are recorded in the variant's cells file.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Pattern, Sequence, Tuple

from . import paper_out_core as core
from .paper_out_core import Cell, Source, Store, Table, register_source
from .paper_out_ops import cell_ref, extract, line_of

ANON = ("TAB-19", "TAB-20")
ROOT = Path(__file__).resolve().parents[2]
ANON_PIN = ("paper/tools/anon.py", "18afa75", "7e82a4142d00a920d8a9215951377f2e5b3030440b3536f4756a38e08ebb608e")
D152 = "D-152"

register_source(Source("register_d152", "decisions/register.md", "ac8ac83",
                       "b227fdaa8dcffe9a465a3b703adfc0c99c7f182b089e1530c83df7a47386556f", kind="text",
                       what="The decision register at the commit that added D-152 (the anonymous copy's words)"))

# (pattern, replacement), applied in order to every printed text. Identifiers first, then names; replacements keep a capital.
ANON_RULES: Tuple[Tuple[str, str], ...] = (
    (r"\bgist [0-9a-f]{6,}…?; Wayback \d{14}\b", "withheld for review"),
    (r"\bDOI 10\.5281/zenodo\.\d+\b", "DOI withheld for review"),
    (r"^10\.5281/zenodo\.\d+$", "withheld for review"),
    (r"^\d{14}$", "withheld for review"),                                   # a Wayback snapshot id (the panel's snapshot column only)
    (r"\bgist with a Wayback snapshot\b", "public posting with an archived snapshot"),
    (r"\bno gist or Wayback\b", "no posting or snapshot"),
    (r"\bZenodo was unavailable\b", "the data archive was unavailable"),
    (r"\ba Zenodo record\b", "an archive record"),
    (r"\bZenodo (v\d) record created\b", r"archive record \1 created"),
    (r"\bZenodo (v\d)\b", r"archive record \1"),
    (r"\bZenodo record\b", "archive record"),
    (r"\bZenodo API\b", "archive's API"),
    (r"\bZenodo DOI\b", "Archive DOI"),
    (r"\bZenodo time\b", "Archive record time"),
    (r"\bpublic gist\b", "public posting"),
    (r"\bGist created\b", "Posting created"),
    (r"\bWayback snapshot\b", "archived snapshot"),
    (r"\bgists\b", "postings"),
    (r"\bgist\b", "posting"),
    (r"\bWayback\b", "snapshot"),
    (r"\bZenodo\b", "archive"),
)
SNAPSHOT_COLUMN = r"^Wayback snapshot$"
# Panels whose anonymous variant is set at the body size (\small) with a little space between rows, not in the footnotesize and
# unspaced layout of its twin (a variant keeps its twin's width, but not necessarily its type size): (table, the panel's title).
# The lock panel's anonymous cells are short ("withheld for review" replaces the gist, snapshot and DOI identifiers, whose unbreakable
# pieces keep the named panel's commit columns narrow and tall), so at footnotesize it fills 2.9 in of its 6.5-in landscape page
# (45%, Edith's proof 3, p. 36); at \small, spaced, 4.3 in (66%; §1.4's floor is 60%). Checked when the variant is made.
ANON_BODY_SIZE = (("TAB-20", "Locks (fingerprints and public proofs)"),)


def vision_patterns() -> Sequence[Pattern]:
    """Vision's SERVICES, PEOPLE and HANDLES from paper/tools/anon.py at the pinned commit (SHA-256 checked; parsed, not executed)."""
    raw = core.pinned_bytes(ROOT, ANON_PIN[1], ANON_PIN[0])      # from its commit, or from disk in disk mode
    if hashlib.sha256(raw).hexdigest() != ANON_PIN[2]:
        raise ValueError(f"{ANON_PIN[0]} at {ANON_PIN[1]}: SHA-256 differs from the pinned one")
    out = []
    for node in ast.parse(raw.decode("utf-8")).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("SERVICES", "PEOPLE", "HANDLES"):
            call = node.value
            pattern = ast.literal_eval(call.args[0])                                                   # type: ignore[attr-defined]
            flags = re.I if any(isinstance(a, ast.Attribute) and a.attr in ("I", "IGNORECASE") for a in call.args[1:]) else 0  # type: ignore[attr-defined]
            out.append(re.compile(pattern, flags))
    if len(out) != 3:
        raise ValueError(f"{ANON_PIN[0]}: expected SERVICES, PEOPLE and HANDLES, found {len(out)}")
    return out


def withheld(S: Store) -> Cell:
    """D-152's sentence, cut from its register row (the quoted phrase), with the row as its source."""
    n = line_of(S, "register_d152", rf"^\| {re.escape(D152)} \|", expect=1)
    return extract(cell_ref(S, "register_d152", n), r'the anonymous copy\'s phrase becomes "([^"]+)"')


class Rewriter:
    def __init__(self) -> None:
        self.fired: Dict[str, int] = {p: 0 for p, _ in ANON_RULES}

    def text(self, s: str, snapshot_column: bool = False) -> str:
        for p, r in ANON_RULES:
            if p == r"^\d{14}$" and not snapshot_column:
                continue
            s, n = re.subn(p, lambda m, r=r: _keep_capital(m, m.expand(r)), s)
            self.fired[p] += n
        return s

    def cell(self, c: Cell, snapshot_column: bool = False) -> Cell:
        new = self.text(c.printed, snapshot_column)
        if new == c.printed:
            return c
        if c.kind == "label":
            return core.label(new)
        return Cell(new, kind=c.kind, raw=c.raw, refs=c.refs,
                    formula="; ".join(x for x in (c.formula, "anonymous copy: identifiers withheld and services named in neutral words") if x))

    def table(self, t: Table, top: bool = True) -> Table:
        if t.layout in core.SPLITS and not top:
            raise ValueError("an anonymous variant is one file per panel: a split panel would leave its later parts un-anonymised in the "
                             "anonymous build (only the table itself, not a panel, may be split: _write_anon writes its parts)")
        snap = [bool(re.match(SNAPSHOT_COLUMN, c.printed)) for c in t.columns]
        # the supplement layout of the named table (float, landscape or longtable, its font, row groups, typewriter columns) is kept,
        # so the anonymous copy is set at the same width and is not shrunk (Edith section 7.1)
        out = Table([self.cell(c) for c in t.columns], [[self.cell(c, snap[j]) for j, c in enumerate(r)] for r in t.rows],
                    [[self.cell(c) for c in n] for n in t.notes], {k: [self.cell(c) for c in v] for k, v in t.caption.items()},
                    [(self.text(name), self.table(p, top=False)) for name, p in t.panels],
                    layout=t.layout, font=t.font, groups=list(t.groups), mono=list(t.mono), once=list(t.once), spaced=t.spaced,
                    fixed_plan=t.fixed_plan,         # a width set by hand for the named table (paper_out_ops.set_widths) carries over
                    # a split table (by rows, with one set of widths: TAB-19) is split the same way, its parts written as X.anon.tex,
                    # X.part2.anon.tex, ... (the converter swaps each named part for its twin)
                    split_parts=[(None if rows is None else list(rows), list(cols)) for rows, cols in t.split_parts] if t.split_parts else None,
                    split_key=list(t.split_key), share_widths=t.share_widths)
        return out


def anonymous(S: Store, tables: Dict[str, Table]) -> Dict[str, Table]:
    """{id: its anonymous variant}, each checked by Vision's scan."""
    rw = Rewriter()
    out = {oid: rw.table(t) for oid, t in tables.items()}
    fired = dict(rw.fired)
    for oid, title in ANON_BODY_SIZE:
        if oid not in out:
            continue
        panels = [p for name, p in out[oid].panels if name == title]
        if len(panels) != 1 or panels[0].font != "footnotesize" or panels[0].layout != "landscape":
            raise ValueError(f"{oid}: the panel {title!r} is not once in the variant, in footnotesize on a landscape page: "
                             "measure the anonymous variant again and change ANON_BODY_SIZE")
        panels[0].font, panels[0].spaced = None, True
        # each lock its own group (1em between locks): at 12 pt below each caption (Vision's template) the spaced panel was 59-60% of
        # its sideways page (Vision's proof check, after PR #38); a lock's row is a unit the reader reads on its own
        panels[0].groups = list(range(1, len(panels[0].rows)))
    w = withheld(S)
    for oid, t in out.items():
        t.notes.append([core.label("Anonymous copy for review: the public proofs are"), w,
                        core.label("(commit IDs and SHA-256 fingerprints are kept).")])
    pats = vision_patterns()
    for oid, t in out.items():
        hits = sorted({m for tab in [t] + [p for _, p in t.panels] for txt in _texts(tab) for p in pats for m in p.findall(txt)})
        if hits:
            raise ValueError(f"{oid}: the anonymous variant still names {len(hits)} identifying string(s) Vision's scan refuses")
        t.anon_rules = fired                                                                   # type: ignore[attr-defined]
    return out


def _keep_capital(m: "re.Match", new: str) -> str:
    """A capital only where a sentence or a cell starts with one (a column title, a note's first word); elsewhere a plain word starts in
    lower case (the services' names are capitalised, the neutral words are not). An acronym (DOI) is left as it is."""
    start = m.start() == 0 or m.string[:m.start()].endswith(". ")
    if start and m.group(0)[:1].isupper():
        return new[:1].upper() + new[1:]
    return new[:1].lower() + new[1:] if new[:1].isupper() and new[1:2].islower() else new


def _texts(t: Table) -> List[str]:
    return ([c.printed for c in t.columns] + [c.printed for r in t.rows for c in r] + [" ".join(c.printed for c in n) for n in t.notes]
            + [" ".join(c.printed for c in v) for v in t.caption.values()])
