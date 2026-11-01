"""The core of the paper-outputs script (D-118, D-120; the master plan's "Tables and figures (for Friday)", 7b43f91): pinned sources,
keys, cells with their provenance, formatting, and the writers. The tables and figures themselves are in the `paper_out_*` modules;
`paper_outputs.py` is the command.

The rules this module enforces:
- **Sources are pinned.** Each source is a file named by its repo path, the main commit that added it (the claims ledger's `commit`) and
  its SHA-256. The bytes are read from that commit with `git show <commit>:<path>`, so the working tree's state never matters, and a
  SHA-256 that differs refuses the whole build (`SourceMismatch`).
- **Disk mode (D-207: the public copy has no development history).** With `--from-disk`, `PARETO_FROM_DISK=1`, or a repository that
  lacks a pinned commit (or has no .git), each pinned file is read from `<repo>/<path>` instead, and its SHA-256 is checked exactly as
  above; the commit is then provenance only. A pinned file the copy does not hold refuses with `NotShipped`; a check that reads the
  history itself (git log, a commit object) refuses with `NeedsHistory`. The outputs they stop ship as built (MANIFEST.json).
- **Keys use the claims ledger's syntax** (research/paper-notes/claims-ledger-format.md, section 2): a dotted path, list items as `.0`.
  A segment that itself holds a dot or a bracket is written `['…']`, e.g. `reporting.group_b.item_9e.shapes.1x6['0.3']`. A digit segment
  is a list index on a list and a key on a dict.
- **No value is typed.** Every printed number comes from a `Ref` (one source, one key) or from a `Derived` value (a named formula over
  Refs, e.g. `100 * x` for a proportion printed in %). Typed text is allowed only as a *label* (row and column names, units); a label
  holding a digit passes only if every digit sits in an allowed name (`LABEL_ALLOWED`: test names, shapes, step counts and the
  like), so a typed number cannot hide in a label.
- **Formatting follows the style sheet** (Vision's paper/notes/style-sheet.md, D-122): a true minus (U+2212) and a leading "+" on
  signed differences; accuracies in %, differences in points, costs in US dollars at list price; and the ledger's rounding rule: if
  rounding would move a value across 0 or across a margin, one more decimal is printed.
- **Outputs are deterministic:** the same sources and code give byte-identical files (no dates, sorted keys, fixed figure metadata).

Standard library only, except matplotlib and numpy for the figures (pinned in harness/requirements-paper.txt; checked at start-up).
"""

from __future__ import annotations

import csv
import hashlib
from decimal import ROUND_HALF_UP, Decimal, localcontext
import io
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

MINUS = "−"
TIMES = "×"

# ---------------------------------------------------------------- sources


@dataclass(frozen=True)
class Source:
    """A pinned input file. `commit` is the main commit that added it (the claims ledger's `source.commit`)."""
    name: str
    path: str
    commit: str
    sha256: str
    kind: str = "json"                  # "json" or "text"
    what: str = ""

    def ledger(self) -> Dict[str, str]:
        return {"path": self.path, "commit": self.commit, "sha256": self.sha256}


SOURCES: Dict[str, Source] = {s.name: s for s in (
    Source("main", "data/main/main-l14n6-1/analysis.json", "8be72ec",
           "43d18eed62604aab9006cae76a6ee04445170866486d14246fb933646823cfef", what="Study 1 analysis (the D-93 stamped driver's one run)"),
    Source("main_k", "data/main/main-l14n6-1/k.json", "da61c76",
           "b0f8b05f729b5e6cee6deaa2384c986646217adf72a96772d5096bd2d6e3234b", what="Study 1 k.json"),
    Source("groupc", "data/main/main-l14n6-1/groupc.json", "2830340",
           "e1cbd4057ed94e6735d7a3ca079213d8ea6eba1240b6f5d90244545bb3f773a9", what="Study 1 keep-list analyses (group C)"),
    Source("s1b", "data/main/study1b-1/analysis.json", "fb301dd",
           "239173fc617f832e7a793e57d0b3fa3dc5c968b395dade10e0720c0f1dc74332", what="Study 1b analysis"),
    Source("s1b_k", "data/main/study1b-1/k.json", "534e415",
           "4204d537769f63c1317909b4d98112fff6c4d550555568ef5aa0cd20bc4c8427", what="Study 1b k.json"),
    Source("topup", "data/main/topup-1/analysis.json", "5c305db",
           "c76478bfd6783fed2a43f146c587d03ace739ba4f67efe6f3da5de2c1f773558", what="Top-up analysis"),
    Source("curve_d90", "data/pilot/curve-ladder-l14n-1-d90.json", "b6c1de5",
           "33ab260979cffd6a720f96aeab57f6384c9e6bd49b8730d0a4eab543184120f0", what="Length sweep curve, Deviation 2 rule (D-90)"),
    Source("curve", "data/pilot/curve-ladder-l14n-1.json", "4547097",
           "1300a410d652323f9969fd2e44ff843619e72205a5e74cdf1ade01346fdc36ad", what="Length sweep curve, original rule"),
    Source("plan", "decisions/briefings/2026-10-15-compiler/plan-result.json", "7b43f91",
           "07d38a4c790dc37c936ac3a6f1ab9bfc0eeae5f7a3cf66035e439205d4f47a28", what="The D-118 master plan (raw): titles, sections, labels"),
)}

# The free analyses (D-131), each written once by harness/analysis/free_analyses.py and committed (post hoc).
_FA = (("fa1", "a2d93ba", "a9dd18fed80c2d693824e742e60d5c07e4c8314fb5c1a39d6d23f4f993e4c5bb", "equal money: one Haiku-max try vs a lower-effort vote"),
       ("fa2", "4935d15", "92aa3cfe2fb26c00b34d11edbf54b627b938a4f2db06d1306830a2f9b8e94838", "Haiku-max vote curves at 6 and 12 steps (revision 2, fa2r2.json)"),
       ("fa3", "a2d93ba", "265701337861586facf1e86cd2553819f8277eeab3bcb5716f0a38df6d18ab4e", "B2's k-sensitivity at 16 steps"),
       ("fa4", "d9cc189", "61ecbaf4ae31a1be4ba280323af0224be375d496a1a022d581b3f9a96e6b2f91",
        "exact intervals wherever a stamped interval collapsed (revision 3, fa4r3.json)"),
       ("fa5", "a2d93ba", "13fe74329bebcb83e1a4cc15ba90b393e98a625781ba2233d2bf349ae26ec21e", "Tests 1-4 under Holm in the inferiority direction (E-19)"),
       ("fa6a", "a2d93ba", "6af8ea0b47f938fcb3855ed3e58caf417393f45f9925a64af86a990018874258", "E-20 bin occupancy (Haiku-medium at 16 steps)"),
       ("fa6b", "c0dcddc", "76d0baaf276c045dc63fa5d38a83d045a9f1fcdc9f342aa86cb9a296e8486c45", "repeat shares; Haiku-max vote by E-20 bins"),
       ("fa7", "a2d93ba", "9f71dc7893cf35c1b1e96fbeee9dd189c678731e88b47ae86949e063b387db26", "Study 1: one Haiku-max try vs one Opus-medium answer"),
       ("fa8", "a2d93ba", "33f5ed5fad5bb936cd7aa96d9b6718be6900547a4044fb9c1ba23a63ac912f0c", "Haiku thinking-off: unparseable vs wrong"),
       ("fa10", "a2d93ba", "74bdca2c18c23b6542af2e32555c1e62fd1f8e96f7789ac1f807c1711154df54", "API thinking-token counts and token structure (N1)"),
       ("fa9", "a0ecfba", "88db8da4553ea4b6359bdbbc8e77ad070682c1441a85dba12ead6174b5a94f44", "Sonnet-high on Study 1b's six-step set (D-133)"),
       ("fa12", "a0ecfba", "63d009747ae20318f3332a61fd6f088c4eead9694a754e122af5146f68c34a81", "re-pricing at other price ratios (D-133)"),
       ("fa13", "c1b33af", "ca4d0805ded485d6787fc3b099064101d47c4e3f8b9f70c27937ce45d2f92a32", "the tie view for Test B2 (D-157)"))
_FILE = {"fa2": "fa2r2",                 # fa2.json's bands collapsed (a coding error); revision 2 is the one read
         "fa4": "fa4r3"}                 # fa4.json: a hand list of 13 cells; fa4r2: every collapsed ci95 by rule; fa4r3: every interval field
for _n, _c, _h, _w in _FA:
    SOURCES[_n] = Source(_n, f"data/main/free-analyses/{_FILE.get(_n, _n)}.json", _c, _h, what=f"free analysis (post hoc): {_w}")


class SourceMismatch(RuntimeError):
    """A pinned source's bytes do not have the pinned SHA-256: nothing is built."""


class KeyMissing(KeyError):
    """A key does not resolve in its source."""


class NotShipped(RuntimeError):
    """Disk mode: a pinned file is not in this copy of the repository (the released package does not ship it)."""


class NeedsHistory(RuntimeError):
    """Disk mode: a check reads the git history itself (a log, a commit object), which a copy without the history does not have."""


AS_BUILT = "ships as built: check it with data/paper-outputs/MANIFEST.json"


def git_bytes(repo: Path, commit: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], check=True, capture_output=True).stdout


def disk_bytes(repo: Path, commit: str, path: str) -> bytes:
    """A pinned file's bytes from `<repo>/<path>` (disk mode; the commit is named for provenance only). The caller checks the SHA-256."""
    p = Path(repo) / path
    if not p.is_file():
        raise NotShipped(f"{path} (pinned at {commit}) is not in this copy of the repository: the released package does not ship it, "
                         f"so what reads it is not rebuilt here; it {AS_BUILT}")
    return p.read_bytes()


FROM_DISK_ENV = "PARETO_FROM_DISK"     # "1": read pinned files from disk (library use; the command's flag is --from-disk)
_FORCED: set = set()                   # repositories set to disk mode by --from-disk (set_from_disk)
_DETECTED: Dict[Path, bool] = {}       # per repository: lacks a pinned commit (decided once, said once)


def set_from_disk(repo: Path) -> None:
    _FORCED.add(Path(repo).resolve())


def _missing_commits(repo: Path, commits: Iterable[str]) -> List[str]:
    """The commits `repo`'s git cannot find (all of them if there is no repository or no git), one `git cat-file --batch-check`."""
    want = sorted(set(commits))
    probe = "".join(f"{c}^{{commit}}\n" for c in want).encode()
    try:
        r = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch-check"], input=probe, capture_output=True)
    except OSError:
        return want
    lines = r.stdout.decode("utf-8", "replace").splitlines()
    if r.returncode != 0 or len(lines) != len(want):
        return want
    return [c for c, ln in zip(want, lines) if ln.split()[1:2] != ["commit"]]


def from_disk(repo: Path, commits: Iterable[str]) -> bool:
    """Whether pinned files are read from `<repo>/<path>`: asked for (`--from-disk`, PARETO_FROM_DISK=1), or because the repository
    lacks one of `commits` (a copy without the development history, or no .git at all), which is said in one line on stderr."""
    key = Path(repo).resolve()
    if key in _FORCED or os.environ.get(FROM_DISK_ENV) == "1":
        return True
    if key not in _DETECTED:
        missing = _missing_commits(key, commits)
        if missing:
            print(f"{key}: {len(missing)} pinned commit(s) not in this repository (e.g. {missing[0]}); reading the pinned files from "
                  f"disk, SHA-256 checked", file=sys.stderr)
        _DETECTED[key] = bool(missing)
    return _DETECTED[key]


def pinned_bytes(repo: Path, commit: str, path: str) -> bytes:
    """A pinned tool file's bytes (lint's and anon's pins): from its commit, or from disk in disk mode. The caller checks the SHA-256."""
    return (disk_bytes if from_disk(repo, [commit]) else git_bytes)(repo, commit, path)


def need_history(S: "Store", what: str) -> None:
    """Refuses, in disk mode, a check that reads the git history itself; `what` names the check and the output it is for."""
    if S.from_disk:
        raise NeedsHistory(f"{what} needs the development history (git), which this copy does not have; that output {AS_BUILT}")


# ---------------------------------------------------------------- keys (the claims ledger's syntax)

_SEG = re.compile(r"\['((?:[^'\\]|\\.)*)'\]|([^.\[\]]+)")


def parse_key(key: str) -> List[str]:
    """`a.b.0['x.y'].c` -> ['a', 'b', '0', 'x.y', 'c']. Refuses empty segments and stray characters."""
    out: List[str] = []
    pos, n = 0, len(key)
    while pos < n:
        m = _SEG.match(key, pos)
        if not m:
            raise ValueError(f"bad key {key!r} at {pos}")
        out.append(m.group(1).replace("\\'", "'") if m.group(1) is not None else m.group(2))
        pos = m.end()
        if pos < n:
            if key[pos] == ".":
                pos += 1
                if pos == n:
                    raise ValueError(f"bad key {key!r}: ends with '.'")
            elif key[pos] != "[":
                raise ValueError(f"bad key {key!r} at {pos}")
    if not out:
        raise ValueError("empty key")
    return out


def format_key(segs: Sequence[Union[str, int]]) -> str:
    """The inverse of parse_key: dotted, a segment holding '.', '[', ']' or "'" (or empty) bracketed."""
    parts: List[str] = []
    for s in segs:
        s = str(s)
        if s == "" or any(c in s for c in ".[]'"):
            parts.append("['" + s.replace("'", "\\'") + "']")
        else:
            parts.append(("." if parts else "") + s)
    return "".join(parts)


def resolve(doc: Any, segs: Sequence[str]) -> Any:
    cur = doc
    for i, s in enumerate(segs):
        if isinstance(cur, dict):
            if s not in cur:
                raise KeyMissing(f"{format_key(segs[:i + 1])}: no key {s!r} (have {sorted(cur)[:12]})")
            cur = cur[s]
        elif isinstance(cur, list):
            if not s.isdigit() or int(s) >= len(cur):
                raise KeyMissing(f"{format_key(segs[:i + 1])}: no index {s!r} in a list of {len(cur)}")
            cur = cur[int(s)]
        else:
            raise KeyMissing(f"{format_key(segs[:i + 1])}: {type(cur).__name__} has no children")
    return cur


def md_cells(line: str) -> List[str]:
    """The cells of a markdown table line '| a | b |' (a backslash-escaped pipe stays inside its cell)."""
    t = line.strip()
    if not (t.startswith("|") and t.endswith("|")):
        raise KeyMissing(f"not a table line: {line[:60]!r}")
    parts, cur, i = [], "", 1
    while i < len(t) - 1:
        if t[i] == "\\" and t[i + 1] == "|":
            cur += "|"
            i += 2
            continue
        if t[i] == "|":
            parts.append(cur.strip())
            cur = ""
        else:
            cur += t[i]
        i += 1
    parts.append(cur.strip())
    return parts


def resolve_text(text: str, segs: Sequence[str]) -> Any:
    """Text-source keys: 'L<n>' is line n (1-based, stripped); "L<n>['<column>']" is that markdown table row's cell under the column
    named in the table's header (the first line of the contiguous block of '|' lines holding line n)."""
    if not re.fullmatch(r"L\d+", segs[0]) or len(segs) > 2:
        raise KeyMissing(f"text key {format_key(segs)!r}: use L<n> or L<n>['<column>']")
    lines = text.split("\n")
    n = int(segs[0][1:])
    if not 1 <= n <= len(lines):
        raise KeyMissing(f"line {n} of {len(lines)}")
    if len(segs) == 1:
        return lines[n - 1].strip()
    top = n
    while top > 1 and lines[top - 2].strip().startswith("|"):
        top -= 1
    header = md_cells(lines[top - 1])
    if segs[1] not in header:
        raise KeyMissing(f"line {n}: no column {segs[1]!r} in {header}")
    row = md_cells(lines[n - 1])
    if len(row) != len(header):
        raise KeyMissing(f"line {n}: {len(row)} cells, the header {len(header)}")
    return row[header.index(segs[1])]


# A source's own identity: '@path', '@commit' (the main commit that added it) and '@sha256' (checked against the bytes before use).
FILE_KEYS = ("@path", "@commit", "@sha256")


# ---------------------------------------------------------------- the store


@dataclass(frozen=True)
class Ref:
    """A value read from one source at one key."""
    value: Any
    source: str
    key: str

    def prov(self) -> Dict[str, str]:
        return {"source": self.source, "key": self.key}


class Store:
    """Loads the pinned sources (lazily, from git, or from disk in disk mode), checks their SHA-256, and resolves keys. Records which
    sources each output used."""

    def __init__(self, repo: Path, sources: Mapping[str, Source] = SOURCES, reader: Optional[Callable[[Source], bytes]] = None):
        self.repo = Path(repo)
        self.sources = dict(sources)
        self.from_disk = reader is None and from_disk(self.repo, [s.commit for s in self.sources.values()])
        read = disk_bytes if self.from_disk else git_bytes
        self._reader = reader or (lambda s: read(self.repo, s.commit, s.path))
        self._docs: Dict[str, Any] = {}
        self.used: set = set()

    def doc(self, name: str) -> Any:
        if name not in self._docs:
            src = self.sources[name]
            raw = self._reader(src)
            got = hashlib.sha256(raw).hexdigest()
            if got != src.sha256:
                where = f"{src.path} on disk (pinned at {src.commit})" if self.from_disk else f"{src.path} at {src.commit}"
                raise SourceMismatch(f"{where}: SHA-256 {got}, pinned {src.sha256}")
            self._docs[name] = json.loads(raw) if src.kind == "json" else raw.decode("utf-8")
        self.used.add(name)
        return self._docs[name]

    def _resolve(self, source: str, segs: List[str]) -> Any:
        if len(segs) == 1 and segs[0] in FILE_KEYS:
            self.doc(source)                                   # the pin is checked before its fields are printed
            return getattr(self.sources[source], segs[0][1:])
        doc = self.doc(source)
        if self.sources[source].kind == "text":
            return resolve_text(doc, segs)
        return resolve(doc, segs)

    def ref(self, source: str, key: str) -> Ref:
        segs = parse_key(key)
        return Ref(self._resolve(source, segs), source, format_key(segs))

    def get(self, source: str, key: str) -> Any:
        """The raw value (for structure: which arms exist, list lengths). A printed number must go through `ref`."""
        return self._resolve(source, parse_key(key))

    def find_lines(self, source: str, pattern: str) -> List[int]:
        """1-based numbers of the lines of a text source matching a regex (to locate a row; the cell is then read by `ref`)."""
        rx = re.compile(pattern)
        return [i for i, line in enumerate(self.doc(source).split("\n"), 1) if rx.search(line)]

    def has(self, source: str, key: str) -> bool:
        try:
            self.get(source, key)
            return True
        except KeyMissing:
            return False

    def keys(self, source: str, key: str) -> List[str]:
        v = self.get(source, key)
        if not isinstance(v, dict):
            raise KeyMissing(f"{key} is not a dict")
        return list(v)


def join_key(*parts: Union[str, int]) -> str:
    """Builds a key from segments (each may hold dots; they are bracketed as needed)."""
    return format_key([str(p) for p in parts])


# ---------------------------------------------------------------- formatting


def dec(x: object) -> Decimal:
    """A stamped or derived number as an exact decimal: a float by its shortest repr (the number as the file prints it), an exact
    decimal or fraction string exactly (fractions to 40 significant digits). All rounding is done on this, so a stamped 0.8925 shown in %
    is 89.25 and rounds half away from zero to 89.3, never 89.2 through binary floating point. A float whose shortest repr still carries
    binary noise (723/800 computed as 0.9037499999999999) is cut to 12 significant digits first, so a tie rounds as its exact value does
    (Karen, 2026-10-20, D-154's half-away rule: 90.375 prints 90.38, not 90.37); no stamped value has that many real digits."""
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        raise TypeError(f"{x!r} is not a number")
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, str):
        if "/" in x:
            from fractions import Fraction
            f = Fraction(x)
            with localcontext() as c:
                c.prec = 40
                return Decimal(f.numerator) / Decimal(f.denominator)
        return Decimal(x)
    f = float(x)
    d = Decimal(repr(f))
    if f.is_integer() or len(d.as_tuple().digits) <= FLOAT_DIGITS:   # a whole float is exact: never cut (the Opus check, S3)
        return d
    return Decimal(f"{f:.12g}")


FLOAT_DIGITS = 12           # significant digits a float keeps before rounding (dec): above it, a repr's last digits are binary noise


def _round_half_away(x: object, dp: int) -> Decimal:
    return dec(x).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def fmt_fixed(x: object, dp: int, signed: bool = False) -> str:
    d = dec(x)
    r = _round_half_away(d, dp)
    s = f"{abs(r):.{dp}f}"
    if r < 0 or (r == 0 and d < 0 and Decimal(s) != 0):
        return MINUS + s
    if signed and r > 0:
        return "+" + s
    return s


def guarded_dp(x: object, dp: int, bounds: Iterable[float] = (0.0,), max_extra: int = 3) -> int:
    """The ledger's rule: if rounding x to dp would move it onto or across a bound it is not on, use one more decimal (up to max_extra)."""
    d = dec(x)
    for extra in range(max_extra + 1):
        r = _round_half_away(d, dp + extra)
        if all((d - dec(b)) * (r - dec(b)) > 0 or d == dec(b) for b in bounds):
            return dp + extra
    return dp + max_extra


def fmt_sf(x: object, sf: int) -> str:
    d = dec(x)
    if d == 0:
        return "0"
    dp = max(sf - 1 - d.adjusted(), 0)
    return fmt_fixed(d, dp)


def is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# ---------------------------------------------------------------- cells

# Digits a typed label may hold: names, not values. Every match is blanked out; a digit left over refuses the label.
LABEL_ALLOWED = [re.compile(p) for p in (
    r"\b(?:Tests?|Study|Studies|Pilot|Locks?|Deviations?|Amendments?|Items?|items?|Addend(?:um|a)|free analys[ie]s)\s+"
    r"\d+[a-z]?(?:\s*(?:[-\u2013,]|and|or)\s*\d+[a-z]?)*",          # Test 3, Tests 1-4, Tests 3 and 5, Study 1b, item 24
    r"\b[BCEF]\d+\b",                                                  # B2, C13, E3, F5
    r"\b\d+\s*[\u00d7x]\s*\d+\b",                                       # shapes 1×6, 16x1
    r"\b(?:4|6|8|12|16|24)(?:\s+|-)steps?\b",                            # the design lengths
    r"\b(?:5|10)-point\b",                                              # the margins
    r"\b(?:90|95)%",                                                    # interval levels
    r"\b(?:Haiku|Sonnet|Opus|Fable) 5\.[15]\b",                          # model names
    r"@\d+\b",                                                         # arm keys such as hx@16
    r"\b(?:TAB|FIG)-\d{2}\b",                                            # cross-references to other outputs
    r"\bSections?\s+\d+(?:\.\d+)*\b",                                    # cross-references to the paper's sections (Vision's)
    r"\bPanels?\s+\d+(?:\s*(?:[-\u2013,]|and)\s*\d+)*\b",                    # a table's own panels, as the converter names them
    r"\bSHA-256\b",                                                     # the hash's name
    r"\b(?:pilot|lock|ladder|main|ext)\d*-\d+\b|\b[a-z]{1,3}\d+\b",            # identifiers: pilot-1, lock-2, presets l14, n6
)]


def blank_allowed(text: str) -> str:
    for rx in LABEL_ALLOWED:
        text = rx.sub(" ", text)
    return text


def label_ok(text: str) -> bool:
    return not re.search(r"\d", blank_allowed(text))


@dataclass(frozen=True)
class Cell:
    """One printed cell. `kind` is 'label' (typed text), 'num' (from refs) or 'empty'. `refs` and `formula` record where it came from."""
    printed: str
    kind: str = "num"
    raw: Any = None
    refs: Tuple[Ref, ...] = ()
    formula: Optional[str] = None
    bold: bool = False            # the paper's headline cells only (Karen's house style: bold only for the headline decision)

    def record(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"printed": self.printed, "kind": self.kind}
        if self.kind == "num":
            out["raw"] = self.raw
            out["refs"] = [r.prov() for r in self.refs]
            if self.formula:
                out["formula"] = self.formula
        if self.bold:
            out["bold"] = True
        return out


def label(text: str) -> Cell:
    if not label_ok(text):
        raise ValueError(f"label {text!r} holds a digit outside the allowed patterns: read the number from a source instead")
    return Cell(text, kind="label")


EMPTY = Cell("", kind="empty")


_NUM_STR = re.compile(r"^-?\d+(?:\.\d+)?(?:/\d+)?$")


def _need_num(r: Ref) -> float:
    """A stamped number: a JSON number, or a stamped exact decimal or fraction string (k.json's '0.0201205', '257542400/7041099')."""
    v = r.value
    if isinstance(v, str) and _NUM_STR.match(v):
        from fractions import Fraction
        return float(Fraction(v))
    if not is_num(v):
        raise TypeError(f"{r.source}:{r.key} is {v!r}, not a number")
    return float(v)


def num(r: Ref, dp: int = 2, signed: bool = False, scale: float = 1.0, bounds: Iterable[float] = (), suffix: str = "",
        formula: Optional[str] = None) -> Cell:
    """A number from a Ref. `scale` (e.g. 100 for a proportion printed in %) is recorded as a formula. `bounds` applies the ledger's
    one-more-decimal rule (pass (0, margin) for differences and interval ends)."""
    _need_num(r)
    x = dec(r.value) * dec(scale)
    d = guarded_dp(x, dp, bounds) if bounds else dp
    f = formula or (f"{scale:g} * x" if scale != 1.0 else None)
    return Cell(fmt_fixed(x, d, signed) + suffix, raw=r.value, refs=(r,), formula=f)


def pct(r: Ref, dp: int = 1, from_proportion: bool = True, bounds: Iterable[float] = ()) -> Cell:
    """An accuracy or share in %: from a proportion (x 100) or from a value already in points/%."""
    return num(r, dp=dp, scale=100.0 if from_proportion else 1.0, bounds=bounds)


def pts(r: Ref, dp: int = 2, margin: Optional[float] = None) -> Cell:
    """A signed difference in points, with the one-more-decimal guard at 0 and the margin."""
    return num(r, dp=dp, signed=True, bounds=(0.0,) + ((margin,) if margin is not None else ()))


def exact(r: Ref, sf: int = 3) -> Cell:
    """A threshold or constant (Edith §2.1: printed exact; §2.8: never padded with zeros): the stamped value as it is when it has at
    most `sf` significant figures (0.005, 0.00625, 0.0125, 0.025), else at `sf` significant figures (0.025 / 3 as 0.00833)."""
    _need_num(r)
    s = fmt_sf(r.value, sf)
    if "." in s:
        short = s.rstrip("0").rstrip(".")
        if Decimal(short) == dec(r.value):
            s = short
    return Cell(s, raw=r.value, refs=(r,))


def usd(r: Ref, sf: int = 3) -> Cell:
    _need_num(r)
    return Cell(fmt_sf(r.value, sf), raw=r.value, refs=(r,))


def integer(r: Ref, thousands: bool = True) -> Cell:
    v = r.value
    if isinstance(v, str) and re.match(r"^-?\d+$", v):
        v = int(v)
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{r.source}:{r.key} is {r.value!r}, not an integer")
    s = f"{abs(v):,}" if thousands else str(abs(v))
    return Cell((MINUS if v < 0 else "") + s, raw=r.value, refs=(r,))


def stamped_count(r: Ref) -> Cell:
    """A stamped count-like number printed exactly as stamped, with comma thousands from 1,000 (Edith's PR #40 review, S1: the supplement
    keeps exact values): a whole number has no '.0' padding ('600', '1,737'), a stamped half keeps its '.5' ('7,604.5'); nothing is
    rounded and nothing is padded (any other stamped decimals print as they are, without trailing zeros). For a token count, or the
    median of token counts (a median of whole counts is a whole number or a half). The cell records the ref and the raw value."""
    _need_num(r)
    d = dec(r.value)
    if d == d.to_integral_value():
        s = f"{abs(int(d)):,}"
    else:
        whole, _, frac = format(abs(d).normalize(), "f").partition(".")
        s = f"{int(whole):,}.{frac}"
    return Cell((MINUS if d < 0 else "") + s, raw=r.value, refs=(r,))


def joined(*parts: Cell, sep: str = " ") -> Cell:
    """One printed cell made of several cells (labels and numbers), keeping every part's refs, e.g. '40 (raw 44)'."""
    refs = tuple(r for p in parts for r in p.refs)
    printed = sep.join(p.printed for p in parts if p.printed)
    if not refs:
        return label(printed)
    raws = [p.raw for p in parts if p.kind == "num"]
    return Cell(printed, raw=raws[0] if len(raws) == 1 else raws, refs=refs,
                formula="; ".join(p.formula for p in parts if p.formula) or None)


def ratio(r: Ref, dp: int = 2) -> Cell:
    return num(r, dp=dp)


def pvalue(r: Ref, dp: int = 4) -> Cell:
    x = _need_num(r)
    if not isinstance(r.value, str):
        x = r.value
    if 0 < x < 10 ** -dp:
        return Cell("<" + fmt_fixed(10 ** -dp, dp), raw=r.value, refs=(r,))
    if 1 - 10 ** -dp < x < 1:
        return Cell(">" + fmt_fixed(1 - 10 ** -dp, dp), raw=r.value, refs=(r,))
    return Cell(fmt_fixed(x, dp), raw=r.value, refs=(r,))


FLOOR_NOTE = "≤ marks a p at the smallest value the bootstrap can return (no resample reached the margin)"


def bca_p_extreme(z0: float, a: float, B: int, upper: bool = False) -> float:
    """The smallest (upper=False) or largest (upper=True) one-sided p the locked BCa bootstrap can return: bootstrap.p_value with the
    share of resamples at or below the margin clipped to 1/(B+1) or B/(B+1), by the locked module's own clip and normal."""
    from . import bootstrap as _bs
    w = _bs._PHI.inv_cdf(_bs._clip(1.0 if upper else 0.0, B)) - z0
    return _bs._PHI.cdf((w * (1.0 - a * z0) - z0) / (1.0 + a * w))


def pvalue_bound(p: Ref, z0: Ref, a: Ref, B: Ref, dp: int = 5, complement: bool = False, floor_dp: int = 5) -> Cell:
    """A one-sided p printed as pvalue(), unless it sits at the bootstrap's floor (no resample reached the margin): then "≤ x", x the
    floor rounded UP at `floor_dp` places (5 everywhere, Edith's ruling, PR 27 §20), so the bound is true; FLOOR_NOTE explains the sign. With complement=True, p is
    1 minus a locked p (an inferiority p), whose floor is 1 minus the largest p the bootstrap can return. The cell records z0, a and B
    with p, and the build refuses a p that is near but not exactly at its floor (it would hide a real resample)."""
    floor = (1.0 - bca_p_extreme(float(z0.value), float(a.value), int(B.value), upper=True)) if complement else \
        bca_p_extreme(float(z0.value), float(a.value), int(B.value))
    x = float(p.value)
    if x != floor:
        if math.isclose(x, floor, rel_tol=1e-9):
            raise ValueError(f"{p.source}:{p.key}: p {x!r} is within rounding of its floor {floor!r} but not equal to it")
        return pvalue(p, dp)
    with localcontext() as ctx:
        ctx.prec = 50
        up = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-floor_dp), rounding="ROUND_CEILING")   # from the float's shortest
        # repr, not dec()'s 12-digit cut: a bound must stay true (the Opus check, S2)
    return Cell("\u2264 " + f"{up:.{floor_dp}f}", raw=x, refs=(p, z0, a, B),
                formula=f"p at the bootstrap's floor ({'1 minus ' if complement else ''}bootstrap.p_value at the clipped share, from z0, a "
                        f"and B); printed as a bound rounded up at {floor_dp} places")


def text_of(r: Ref, mapping: Optional[Mapping[Any, str]] = None) -> Cell:
    """A stamped string or boolean printed as is (or through a typed mapping, e.g. True -> 'yes')."""
    v = r.value
    if mapping is not None:
        if v not in mapping:
            raise KeyError(f"{r.source}:{r.key} = {v!r} has no printed form in {mapping}")
        return Cell(mapping[v], raw=v, refs=(r,))
    if not isinstance(v, (str, bool)) and v is not None:
        raise TypeError(f"{r.source}:{r.key} is {v!r}: use a number formatter")
    return Cell("" if v is None else str(v), raw=v, refs=(r,))


YES_NO = {True: "yes", False: "no"}


def interval(lo: Ref, hi: Ref, dp: int = 2, signed: bool = False, scale: float = 1.0, bounds: Iterable[float] = (),
             open_text: Mapping[str, str] = {"unbounded": "unbounded"}) -> Cell:
    """'[lo, hi]' from two Refs; a stamped string end (e.g. 'unbounded') is printed through open_text. A table's interval never
    carries "+" on a positive end (Edith §2.4: "[−1.2, 2.4]"), so `signed` is accepted and ignored."""
    parts = []
    for r in (lo, hi):
        if isinstance(r.value, str):
            if r.value not in open_text:
                raise TypeError(f"{r.source}:{r.key} = {r.value!r}")
            parts.append(open_text[r.value])
        else:
            _need_num(r)
            x = dec(r.value) * dec(scale)
            d = guarded_dp(x, dp, bounds) if bounds else dp
            parts.append(fmt_fixed(x, d))
    f = f"{scale:g} * x" if scale != 1.0 else None
    return Cell(f"[{parts[0]}, {parts[1]}]", raw=[lo.value, hi.value], refs=(lo, hi), formula=f)


def ci_refs(S: Store, source: str, key: str) -> Tuple[Ref, Ref]:
    """The two ends of a stamped 2-list interval at `key`."""
    return S.ref(source, key + ".0"), S.ref(source, key + ".1")


@dataclass(frozen=True)
class Fa4Cell:
    """Free analysis 4's exact replacement for one collapsed stamped interval: the cell's base key in fa4 (result.cells.<i>), its
    exact 95% ends as Refs, the count, and the scale that prints it in points (100 for a share, 1 for points)."""
    base: str
    lo: Ref
    hi: Ref
    x: int
    n: int
    scale: float


def fa4_exact(S: "Store", source: str, key: str, field: str = "ci95") -> Optional[Fa4Cell]:
    """The fa4 (revision 3) cell for the collapsed interval stamped at `source`:`key`.`field` (`key` is the dict holding the interval,
    in the ledger's key syntax; `field` its name, `ci95` unless the file stores it under another, e.g. item 9e's `opus_accuracy_ci95`),
    or None when fa4 has none. fa4 writes its keys as plain dotted paths ('...bins.[0,10).thirds...'), so the two are compared segment
    by segment. The cell must be fa4's copy of that very interval (same stamped ends, collapsed); its exact interval is at the stamped
    interval's own level (`exact95`, or `exact90` for a 90% interval). A C10 pair cell (two arms on one stamped pair key) is not looked
    up here."""
    path = S.sources[source].path
    want = parse_key(key)
    hits = [i for i, c in enumerate(S.get("fa4", "result.cells"))
            if c["source"] == path and c["key"].split(".") == want and c.get("field", "ci95") == field]
    if not hits:
        return None
    if len(hits) != 1:
        raise ValueError(f"{source}:{key}: {len(hits)} fa4 cells (a paired difference's arms are read by arm, not here)")
    b = f"result.cells.{hits[0]}"
    pct = int(round(100 * float(S.get("fa4", b + ".level")))) if S.has("fa4", b + ".level") else 95
    lo, hi = ci_refs(S, source, f"{key}.{field}")
    if S.get("fa4", f"{b}.stamped_ci{pct}") != [lo.value, hi.value] or lo.value != hi.value:
        raise ValueError(f"{source}:{key}: fa4's stamped copy {S.get('fa4', f'{b}.stamped_ci{pct}')} is not the collapsed {[lo.value, hi.value]}")
    elo, ehi = ci_refs(S, "fa4", f"{b}.exact{pct}")
    scale = {"points": 1.0, "share (0-1)": 100.0}[S.get("fa4", b + ".unit")]
    return Fa4Cell(b, elo, ehi, int(S.get("fa4", b + ".x")), int(S.get("fa4", b + ".n")), scale)


@dataclass(frozen=True)
class Derived:
    """A value computed from Refs by a named formula (kept to unit changes and simple arithmetic; recorded in the cells file)."""
    value: float
    formula: str
    refs: Tuple[Ref, ...]


def derive(formula: str, fn: Callable[..., float], *refs: Ref) -> Derived:
    return Derived(fn(*[_need_num(r) for r in refs]), formula, tuple(refs))


def num_d(d: Derived, dp: int = 2, signed: bool = False, bounds: Iterable[float] = ()) -> Cell:
    dd = guarded_dp(d.value, dp, bounds) if bounds else dp
    return Cell(fmt_fixed(d.value, dd, signed), raw=d.value, refs=d.refs, formula=d.formula)


# ---------------------------------------------------------------- outputs


@dataclass
class Meta:
    """An output's plan entry, read from the pinned plan file (never retyped)."""
    id: str
    kind: str
    title: str
    section: str
    label: str
    content: str
    source_keys: str


@dataclass
class Table:
    columns: List[Cell]
    rows: List[List[Cell]]
    notes: List[List[Cell]] = field(default_factory=list)          # footnotes: each a list of label and number cells
    caption: Dict[str, List[Cell]] = field(default_factory=dict)    # caption facts: tier, study, set, n, interval type, price basis
    panels: List[Tuple[str, "Table"]] = field(default_factory=list)  # optional extra panels (e.g. a side panel), each its own table
    # the main-text version's own notes and caption (used by narrow() when the builder gives them; None = the full table's)
    main_notes: Optional[List[List[Cell]]] = None
    main_caption: Optional[Dict[str, List[Cell]]] = None
    # D-159/D-160 (Vision's converter): the indexes of the notes the paper prints under the table (at most 2; the rest print in the
    # supplement only), and the layout mark written as the .tex's first comment line (float, landscape, longtable or split).
    short_notes: List[int] = field(default_factory=list)
    layout: Optional[str] = None
    # the same two for the narrow main-text version (narrow() carries them over; main_notes then holds only what the paper prints)
    main_short_notes: Optional[List[int]] = None
    main_layout: Optional[str] = None
    # the paper's own version, built from the same refs at the paper's precision (D-161: percentages and point differences to one
    # decimal); when set it is written as <id>.main in place of narrow(), and the full table (exact values) goes to the supplement
    main_table: Optional["Table"] = None
    font: Optional[str] = None    # "footnotesize" for a dense table (the house style's floor), written as a "% font:" line
    # a split table's parts (layout "split" or "split landscape"): each part is (row indexes or None for all rows, column indexes);
    # the key columns (split_key) are repeated in every part. Written as <stem>.tex, <stem>.part2.tex, ... (Vision's converter)
    split_parts: Optional[List[Tuple[Optional[List[int]], List[int]]]] = None
    split_key: List[int] = field(default_factory=lambda: [0])
    # columns printed in typewriter type (hashes, commits): a long hexadecimal run may break every 8 characters (\allowbreak)
    mono: List[int] = field(default_factory=list)
    # row groups (Edith §7.7): the indexes of the rows that start a new group get a little space above them (booktabs \addlinespace)
    groups: List[int] = field(default_factory=list)
    # columns whose value prints once per group (Edith §7.7): a cell equal to the one above it, in a row that starts no group, prints
    # blank in the .tex (the CSV and the cells file keep every value)
    once: List[int] = field(default_factory=list)
    # a little space between every two rows (a table of tall wrapped rows, Edith §7.7); a group's start then gets more
    spaced: bool = False
    # sideways packing (Vision's converter, proof 3 C.30): this unit shares the previous unit's sideways float page ("% pack:
    # with-previous"); for a split table, the indexes (from 1) of the parts that share the previous part's page. Set by plan_packing.
    pack: bool = False
    pack_parts: List[int] = field(default_factory=list)
    # a split table whose parts all hold the same columns (a split by rows) may set its column widths once, on all its rows, so every
    # part has one column layout (Edith, proof 3, p. 55); split_tables hands each part the plan (fixed_plan)
    share_widths: bool = False
    fixed_plan: Optional[Tuple[List[Optional[str]], Dict[int, float], Dict[int, bool]]] = None
    # a part of a split table reads a column as numbers or as text by all the table's rows, not by its own, so that a column keeps one
    # alignment on every page (Edith, M2-8: Table S8's interval column was right-aligned on one page and left-aligned on the next)
    numeric_cols: Optional[List[bool]] = None

    def check(self) -> None:
        w = len(self.columns)
        for i, r in enumerate(self.rows):
            if len(r) != w:
                raise ValueError(f"row {i} has {len(r)} cells, the header {w}")


def narrow(t: Table, spec: Sequence[object]) -> Table:
    """A narrow version of a table for the main text, made only by choosing and joining the full table's columns (by their printed
    titles), so every cell keeps its source and key. `spec` items: a column title (kept as is), or (new title, [titles], separator) to
    join several columns into one cell (e.g. ("d [95% interval]", ["d (points)", "95% interval"], " ")). A title that does not exist
    refuses, so a changed full table cannot silently drop a column."""
    titles = [c.printed for c in t.columns]

    def idx(title: str) -> int:
        if titles.count(title) != 1:
            raise KeyError(f"narrow: column {title!r} is not exactly once in {titles}")
        return titles.index(title)
    cols: List[Cell] = []
    picks: List[Tuple[List[int], str]] = []
    for item in spec:
        if isinstance(item, str):
            cols.append(t.columns[idx(item)])
            picks.append(([idx(item)], ""))
        else:
            title, parts, sep = item                                                          # type: ignore[misc]
            cols.append(label(title))
            picks.append(([idx(x) for x in parts], sep))
    rows = []
    for r in t.rows:
        out = []
        for ix, sep in picks:
            cells = [r[i] for i in ix]
            if len(cells) == 1:
                out.append(cells[0])
            elif all(c.kind != "num" for c in cells):
                out.append(Cell(sep.join(c.printed for c in cells if c.printed), kind="label"))
            else:
                out.append(joined(*cells, sep=sep))
        rows.append(out)
    if t.main_notes is not None:
        notes = list(t.main_notes)
    else:
        notes = [[label("Main-text version: a choice of the full table's columns, some joined; the full table, with every column "
                        "these notes describe, is in the appendix.")]] + list(t.notes)
    caption = dict(t.main_caption) if t.main_caption is not None else dict(t.caption)
    return Table(cols, rows, notes, caption, short_notes=list(t.main_short_notes or []), layout=t.main_layout)


@dataclass
class FigureOut:
    fig: Any                                   # a matplotlib Figure
    points: List[Dict[str, Any]]               # every plotted value: {"series", "x", "y", ...} each a Cell record
    alt: List[Cell]                            # alt text, as label and number cells
    caption: Dict[str, List[Cell]] = field(default_factory=dict)
    variants: List[Tuple[str, "FigureOut"]] = field(default_factory=list)   # e.g. [("appendix", FigureOut(...))]: <id>.appendix.pdf


@dataclass
class Stub:
    waits_for: List[str]
    why: str
    partial: Optional[Table] = None


@dataclass
class Spec:
    id: str
    build: Callable[["Store"], Union[Table, FigureOut, Stub]]
    module: str


REGISTRY: Dict[str, Spec] = {}
DATA_REGISTRY: Dict[str, Spec] = {}


def data_output(name: str) -> Callable[[Callable], Callable]:
    """Registers a derived-values file (not a plan id): the builder returns a dict whose every value is a Cell record or a nested dict
    of them; it is written as `<name>.json` and audited like a table's cells (e.g. the claims ledger's derived values)."""
    def deco(fn: Callable) -> Callable:
        if name in DATA_REGISTRY:
            raise ValueError(f"data output {name} registered twice")
        DATA_REGISTRY[name] = Spec(name, fn, fn.__module__)
        return fn
    return deco


def register_source(src: Source) -> Source:
    """A builder module pins an extra source (e.g. a text file at a commit). The same name twice must be the same pin."""
    if src.name in SOURCES and SOURCES[src.name] != src:
        raise ValueError(f"source {src.name} pinned twice differently")
    SOURCES[src.name] = src
    return src


def output(oid: str) -> Callable[[Callable], Callable]:
    """Registers a builder for a plan id (TAB-nn or FIG-nn). The title, section and label come from the plan file."""
    def deco(fn: Callable) -> Callable:
        if oid in REGISTRY:
            raise ValueError(f"{oid} registered twice ({REGISTRY[oid].module}, {fn.__module__})")
        REGISTRY[oid] = Spec(oid, fn, fn.__module__)
        return fn
    return deco


# Outputs added after the master plan by a later user ruling (id -> Meta); the ruling is named in the Meta's content.
EXTRA_META: Dict[str, Meta] = {
    "FIG-00": Meta("FIG-00", "figure", "The story at a glance: accuracy against cost per answer for the key setups", "Introduction",
                   "descriptive summary of confirmatory and exploratory points; each study's points kept separate; our reading, not a test",
                   "D-141 (the user's ruling): a simplified, labelled accuracy-against-cost picture: one Opus-medium answer, the "
                   "equal-money quick Haiku-medium vote (Study 1, 6 steps), one Haiku-max answer, the 6-try Haiku-max vote (B2, 16 steps)",
                   "main item_24 (table, chart); main_k; s1b descriptive.arms, vote_curve_n16; s1b_k; fa4"),
    "TAB-35": Meta("TAB-35", "table", "Settings at a glance", "Method",
                   "design summary: every setting's samples per puzzle, puzzles, steps and role; no results",
                   "D-160 (the user's ruling): three main tables, Table 1 the settings at a glance (Vision's plan §0c, from C-140, C-142, "
                   "C-144 and C-145)",
                   "main_plan setups, e3, puzzles, steps; main reporting.d42_robustness; s1b descriptive.arms; curve_d90 models; topup "
                   "accuracy.e2"),
}


# Plan ids dropped from the outputs (id -> why). They are left out of the build and listed under "dropped" in the manifest.
DROPPED: Dict[str, str] = {
    "TAB-32": "dropped: its free analyses 14 and 15 were never approved (D-131/D-133 approved only 1-10 and 12); the top-up text "
              "already reports the picker positions and the aggregator counts. Source: Jarvis; LOG 2026-10-15 (TAB-32 and TAB-33 DROPPED)",
    "TAB-33": "dropped: its free analysis 37 was never approved (D-131/D-133 approved only 1-10 and 12); the claims ledger, published "
              "with the code, already lists every estimate with its tier. Source: Jarvis; LOG 2026-10-15 (TAB-32 and TAB-33 DROPPED)",
}


# Plan titles changed for print (id -> (title, why)); the plan's own title stays in the manifest's "title_edits".
TITLE_EDITS: Dict[str, Tuple[str, str]] = {
    "TAB-34": ("Cost for a target accuracy", "the plan's title names an internal finding id; the printed title drops it"),
}


def plan_entries(S: Store) -> List[Dict[str, Any]]:
    return list(S.get("plan", "plan.tables_figures"))


def plan_meta(S: Store) -> Dict[str, Meta]:
    out = {}
    entries = plan_entries(S)
    missing = sorted((set(DROPPED) | set(TITLE_EDITS)) - {e["id"] for e in entries})
    if missing:
        raise ValueError(f"dropped ids not in the plan: {missing}")
    for i, e in enumerate(entries):
        if e["id"] in DROPPED:
            continue
        title = TITLE_EDITS[e["id"]][0] if e["id"] in TITLE_EDITS else e["title"]
        out[e["id"]] = Meta(e["id"], e["kind"], title, e["section"], e["label"], e["content"], e["source_keys"])
    for k, m in EXTRA_META.items():
        if k in out:
            raise ValueError(f"{k} is in the plan already")
        out[k] = m
    return out


# ---------------------------------------------------------------- writers

_TEX = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", MINUS: r"\ensuremath{-}", TIMES: r"\ensuremath{\times}",
        "≤": r"\ensuremath{\leq}", "≥": r"\ensuremath{\geq}", "–": "--", "—": "---", "…": r"\ldots{}",
        "’": "'", "‘": "`", "“": "``", "”": "''", "±": r"\ensuremath{\pm}", "∞": r"\ensuremath{\infty}", "τ": r"\ensuremath{\tau}",
        "ρ": r"\ensuremath{\rho}", "<": r"\ensuremath{<}", ">": r"\ensuremath{>}", "|": r"\ensuremath{|}", "→": r"\ensuremath{\rightarrow}", "§": r"\S{}", "≈": r"\ensuremath{\approx}",
        "†": r"\ensuremath{^{\dagger}}", "‡": r"\ensuremath{^{\ddagger}}",
        "\u00a0": "~"}


# A cross-reference placeholder (⟦TAB-24⟧, ⟦FIG-05⟧) passes through untouched: Vision's converter replaces it with the whole reference
# ("Table~\\ref{tab:TAB-24}", or words naming the other document), and her --final refuses any left over (D-159, Edith's H3).
PLACEHOLDER = re.compile(r"⟦(?:TAB|FIG)-\d{2}⟧")


# The paper's print form of a table text (Edith's H3 and M6; Vision's converter): an output id becomes a ⟦…⟧ placeholder that the
# converter expands to the whole reference (so a "Table"/"Figure" word before it goes), and a symbol written as text becomes LaTeX
# math. The CSV and the cells file keep the plain text.
ID_REF = re.compile(r"(?:\b(?:Tables?|Figures?)\s+)?(?<!⟦)\b((?:TAB|FIG)-\d{2})\b(?!⟧)")
# Symbols set as math (Edith §3.7: math italic wherever they are symbols): q^N, local^N, k_c / k_O / k_S, and a one-letter symbol
# standing alone (d, k, n, p, N, R: "d (points)", "k = 4", "p (one-sided)", "×N"), never a letter inside a word, name or id.
MATH_TEX = {"q^N": r"$q^{N}$", "local^N": r"$\mathrm{local}^{N}$", "k_c": r"$k_c$", "k_O": r"$k_O$", "k_S": r"$k_S$",
            **{c: f"${c}$" for c in "dknpqxmrBNR"}}
# (q is the share of pieces right, beside q^N; a letter that names a flag, "flag R", stays a name)
# Edith, proof 3 (§3.7): also x (a count of x of n), m, r, B where it is the bootstrap's "B = ...", a symbol after a word's hyphen
# ("own-k"), and the p of "p-value" (the k of a stamped key's "own k" stays as stamped: Edith, M2-8). A symbol with a possessive "'s" is still a symbol (q's input, k's value: Edith, proof 5, B2-M9).
MATH_TOKEN = re.compile(r"(?<![A-Za-z])(q\^N|local\^N|k_[cOS])(?![A-Za-z0-9])"
                        r"|(?<![A-Za-z0-9_'‘’./])(?<![0-9]-)(?<![Ff]lag[ \u00a0])(?<![Ll]etter[ \u00a0])(?<!\b[A-Za-z]-)(?<!_k\.own[ \u00a0])"
                        r"([dknpqxmrNR]|B(?=[ \u00a0]=))(?![A-Za-z0-9_/\-])(?![’'](?!s(?![A-Za-z0-9])))(?!\.[A-Za-z])"
                        r"|(?<![A-Za-z0-9_'‘’./\-])(p)(?=-value)"
                        r"|(?<=[0-9]/)(m)(?![A-Za-z0-9_'’/\-])")             # the m of a "1/m" share


# Spaces a wrapping column must not break at, printed as no-break spaces (~): after a comparison sign ("> 10", "> margin"),
# around an equals sign ("k = 4"), before a "×N" count ("Haiku-medium ×40"), and before ≤ and ≥ ("(p ≤ 0.00004": Edith, proof 5, B2-M10).
GLUE = re.compile(r"(?<=[<>≤≥]) (?=\S)|(?<==) (?=[\d−+])| (?==\s)| (?=×\d)| (?=[≤≥]\s)")
# ... and between a name and the number or letter that names it ("Deviation 2", "Test B1", "Study 1b", "Lock 4", "flag R")
NAMED_NUMBER = re.compile(r"\b(Deviation|Amendment|Studies|Section|Appendix|Pilot|Study|Tests|Test|Locks|Lock|Flag|flag|item|Item|Panel|Part"
                          r"|Table|Figure) (?=(?:[0-9]+[a-z]?|[A-Z][0-9]?)\b)")


def glue(s: str) -> str:
    return NAMED_NUMBER.sub(lambda m: m.group(1) + "\u00a0", GLUE.sub("\u00a0", s))


# Quotation marks print curly (Edith §8.2, no straight quotes): a straight one opens at the start of a text or after a space, a bracket
# or a dash, else it closes (a single one is then an apostrophe, which is the closing mark). The CSV and cells keep the plain text.
OPENS_AFTER = " \u00a0([{—–/"


def curly(s: str) -> str:
    out = []
    for k, ch in enumerate(s):
        opening = k == 0 or s[k - 1] in OPENS_AFTER or (out and out[-1] == "“")
        if ch == '"':
            out.append("“" if opening else "”")
        elif ch == "'" and opening and k + 1 < len(s) and not s[k + 1].isspace():
            out.append("‘")
        else:
            out.append(ch)
    return "".join(out)


# A hash in a text cell (a run of 9 or more hexadecimal characters with a letter and a digit) may break every 8 characters, as in a
# typewriter column; a plain number (a Wayback timestamp) never does.
HEX_TEXT = r"(?<![0-9a-f])(?=[0-9a-f]*?[a-f])(?=[0-9a-f]*?[0-9])[0-9a-f]{9,}"


# A date (2026-10-12) never breaks at its hyphens; a time joined to it (2026-10-12T09:00Z) may break only before the "T".
DATE = r"\d{4}-\d{2}-\d{2}"
DATE_TIME = re.compile(DATE + r"(T[\d:.]+Z?)?")


def tex_text(s: str) -> str:
    """A table text in print form: ids as placeholders, symbols as math, every interval "[lo, hi]" and every date in an \\mbox (so a
    wrapping column never breaks inside it), GLUE's spaces unbreakable, quotation marks curly, everything else escaped."""
    s = glue(ID_REF.sub(lambda m: f"⟦{m.group(1)}⟧", curly(s)))
    out = []
    pos = 0
    for m in re.finditer(r"\[[^\]⟦⟧]*\]|" + DATE_TIME.pattern + "|" + HEX_TEXT, s):
        out.append(_tex_plain(s[pos:m.start()]))
        if re.fullmatch(HEX_TEXT, m.group(0)):
            out.append(r"\allowbreak{}".join(m.group(0)[k:k + 8] for k in range(0, len(m.group(0)), 8)))
        elif m.group(1):
            out.append(r"\mbox{" + _tex_plain(m.group(0)[:-len(m.group(1))]) + r"}\allowbreak{}\mbox{" + _tex_plain(m.group(1)) + "}")
        else:
            out.append(r"\mbox{" + _tex_plain(m.group(0)) + "}")
        pos = m.end()
    out.append(_tex_plain(s[pos:]))
    return "".join(out)


def _tex_plain(s: str) -> str:
    out = []
    pos = 0
    for m in MATH_TOKEN.finditer(s):
        out.append(tex_escape(s[pos:m.start()]))
        out.append(MATH_TEX[m.group(1) or m.group(2) or m.group(3) or m.group(4)])
        pos = m.end()
    out.append(tex_escape(s[pos:]))
    return "".join(out)


def tex_escape(s: str) -> str:
    out = []
    parts = PLACEHOLDER.split(s)
    marks = PLACEHOLDER.findall(s)
    if len(parts) > 1:
        return "".join(tex_escape(x) + (marks[i] if i < len(marks) else "") for i, x in enumerate(parts))
    for ch in s:
        if ch in "'’”`‘“" and out and _TEX.get(ch, ch)[0] == out[-1][-1:]:
            out.append("{}")
        if ch in _TEX:
            out.append(_TEX[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            raise ValueError(f"no LaTeX form for {ch!r} (U+{ord(ch):04X}) in {s!r}")
    return "".join(out)


def table_csv(t: Table) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([c.printed.replace(NBSP, " ") for c in t.columns])
    for r in t.rows:
        w.writerow([c.printed.replace(NBSP, " ") for c in r])
    return buf.getvalue().encode("utf-8")


def _col_spec(t: Table, j: int) -> str:
    """'r' for a column of numbers, 'l' for short text, a wrapping p{} column for long text (the first column is always text)."""
    body = [r[j] for r in t.rows if r[j].printed]
    if j > 0 and body and all(c.kind == "num" and len(c.printed) <= 24 for c in body):
        return "r"
    longest = max([len(c.printed) for c in body] + [0])
    return "p{5cm}" if longest > 48 else "l"


LAYOUTS = ("float", "landscape", "longtable", "split", "split landscape")
SPLITS = ("split", "split landscape")
DASHES = ("", "—", "-")


SEP_IN = 12 / 72.27                 # the two \\tabcolsep paddings of a column
PT_PER_IN = 72.27
# Character widths in points at \\small (9 pt) in the paper's font, Latin Modern with T1 encoding (TMLR's tmlr.sty), measured with
# \\settowidth on every printable ASCII character and every symbol the writer prints (_TEX). Bold is about 13% wider; \\footnotesize
# is 8/9 of \\small. A character not listed counts as DEFAULT_PT.
CHAR_PT = {'!': 2.57, '"': 3.49, '#': 7.71, '$': 4.62, '%': 7.71, '&': 7.19, "'": 2.57, '(': 3.6, ')': 3.6, '*': 4.62, '+': 7.19,
           ',': 2.57, '-': 3.08, '.': 2.57, '/': 4.62, '0': 4.62, '1': 4.62, '2': 4.62, '3': 4.62, '4': 4.62, '5': 4.62,
           '6': 4.62, '7': 4.62, '8': 4.62, '9': 4.62, ':': 2.57, ';': 2.57, '<': 7.19, '=': 7.19, '>': 7.19, '?': 4.37,
           '@': 7.19, 'A': 6.94, 'B': 6.55, 'C': 6.68, 'D': 7.06, 'E': 6.29, 'F': 6.04, 'G': 7.26, 'H': 6.94, 'I': 3.34,
           'J': 4.75, 'K': 7.19, 'L': 5.78, 'M': 8.48, 'N': 6.94, 'O': 7.19, 'P': 6.29, 'Q': 7.19, 'R': 6.81, 'S': 5.14,
           'T': 6.68, 'U': 6.94, 'V': 6.94, 'W': 9.5, 'X': 6.94, 'Y': 6.94, 'Z': 5.65, '[': 2.57, '\\': 4.62, ']': 2.57,
           '^': 5.0, '_': 6.94, '`': 2.57, 'a': 4.62, 'b': 5.14, 'c': 4.11, 'd': 5.14, 'e': 4.11, 'f': 2.83, 'g': 4.62,
           'h': 5.14, 'i': 2.57, 'j': 2.83, 'k': 4.88, 'l': 2.57, 'm': 7.71, 'n': 5.14, 'o': 4.62, 'p': 5.14, 'q': 4.88,
           'r': 3.62, 's': 3.65, 't': 3.6, 'u': 5.14, 'v': 4.88, 'w': 6.68, 'x': 4.88, 'y': 4.88, 'z': 4.11, '{': 4.62,
           '|': 2.57, '}': 4.62, '~': 5.0, '§': 4.49, '±': 7.19, '×': 7.19, 'ρ': 4.76, 'τ': 5.1, '–': 4.62, '—': 9.25, '’': 2.57,
           '…': 12.33, '→': 9.25, '†': 3.94, '‡': 3.94, '‘': 2.57, '“': 4.37, '”': 4.37, '−': 7.19, '∞': 9.25, '≈': 7.19, '≤': 7.19, '≥': 7.19}
SPACE_PT, DEFAULT_PT, BOLD_SCALE = 3.08, 5.0, 1.13
MONO_PT = 4.725                     # Latin Modern Mono: every character 0.525 em, at \\small (9 pt)
HEX_RUN = re.compile(r"[0-9a-f]{9,}")


def _mono_chunks(word: str) -> List[str]:
    """A word of a typewriter column in its unbreakable chunks: a hexadecimal run of 9 or more characters in pieces of 8; a prefix
    before the run (such as "sha256:") stays with its first piece."""
    out: List[str] = []
    pos = 0
    for m in HEX_RUN.finditer(word):
        run = m.group(0)
        chunks = [run[k:k + 8] for k in range(0, len(run), 8)]
        chunks[0] = word[pos:m.start()] + chunks[0]
        out += chunks
        pos = m.end()
    if pos < len(word):
        if out:
            out[-1] += word[pos:]
        else:
            out.append(word[pos:])
    return out


def mono_tex(text: str) -> str:
    """A typewriter cell: \\texttt, with \\allowbreak{} between the 8-character chunks of a long hexadecimal run."""
    return r"\texttt{" + " ".join(r"\allowbreak{}".join(tex_escape(c) for c in _mono_chunks(w)) for w in text.split(" ")) + "}"
FONT_SCALE = {None: 1.0, "small": 1.0, "footnotesize": 8.0 / 9.0}
HI_CAP_IN = 3.2                     # a text column's share of spare room stops growing past this width (about 45 characters)


NUMERIC_TEXT = re.compile(r"^[\s\d.,+−\-\[\]();:%$×/≤≥<>~—–]*(?:unbounded|undefined|each|and|as above)?[\s\d.,+−\-\[\]();:%$×/≤≥<>~—–]*$")
# The unbreakable pieces of a cell: an interval "[lo, hi]" (tex_text keeps it in an \\mbox), a date, else a whole word: a wrapping
# column never breaks a word, at a hyphen ("Opus-/medium") or anywhere else (its X columns set \\hyphenpenalty and
# \\exhyphenpenalty to 10000; Edith, proof 2). A no-break space (U+00A0, printed "~") joins two pieces.
TOKEN = re.compile(r"\[[^\]]*\]|" + DATE + r"|\S+")
NBSP = "\u00a0"


SINGLE_NUMBER = re.compile(r"^[−+]?\d[\d,]*(?:\.(\d+))?$")


def _decimal_pads(t: Table) -> Dict[Tuple[int, int], int]:
    """Decimal-point alignment (Edith's §2.8): in a column of numbers whose single-number cells differ in decimals (a dollar column at
    3 significant figures, or a one-more-decimal guard cell), each shorter cell gets invisible digits (\\phantom{0}) after it, so
    the decimal points line up in the right-aligned column; a whole number gets an invisible point too (\\phantom{.0}: a token median
    printed as stamped, 600 beside 7,604.5; Edith's #39 review). Nothing printed changes."""
    pads: Dict[Tuple[int, int], int] = {}
    for j in range(len(t.columns)):
        if not _numeric_column(t, j):
            continue
        dps = {i: len(m.group(1) or "") for i, r in enumerate(t.rows) for m in [SINGLE_NUMBER.match(r[j].printed)] if m}
        if len(set(dps.values())) > 1:
            top = max(dps.values())
            pads.update({(i, j): top - d for i, d in dps.items() if d < top})
    return pads


def _numeric_column(t: Table, j: int) -> bool:
    """A column of numbers by what it prints (digits, signs, brackets, units), not by whether its cells have sources (a decision's words
    are sourced but are text)."""
    if t.numeric_cols is not None:
        return t.numeric_cols[j]
    printed = [r[j].printed for r in t.rows if r[j].printed not in DASHES]
    return j > 0 and bool(printed) and sum(1 for x in printed if NUMERIC_TEXT.match(x)) >= 0.75 * len(printed)


def _pieces(cell: "Cell", font: Optional[str] = None, mono: bool = False) -> List[Tuple[float, float]]:
    """A cell's unbreakable pieces as (space before, width) in points, as printed: a placeholder as the reference it becomes ("Table
    12"), a math symbol as its letters, bold wider, \\footnotesize smaller; in a typewriter column every character is MONO_PT wide
    and a long hexadecimal run breaks every 8 characters."""
    if mono:
        scale = FONT_SCALE.get(font, 1.0)
        out = []
        for m in re.finditer(r"\S+", cell.printed):
            gap = scale * SPACE_PT if m.start() and cell.printed[m.start() - 1].isspace() else 0.0
            for k, chunk in enumerate(_mono_chunks(m.group(0))):
                out.append((gap if k == 0 else 0.0, scale * MONO_PT * len(chunk)))
        return out
    text = glue(PLACEHOLDER.sub("Table 12", ID_REF.sub(lambda m: "Table 12", curly(cell.printed))))
    text = MATH_TOKEN.sub(lambda m: (m.group(1) or m.group(2) or m.group(3) or m.group(4)).replace("^", "").replace("_", ""), text)
    scale = FONT_SCALE.get(font, 1.0) * (BOLD_SCALE if cell.bold else 1.0)
    out: List[Tuple[float, float]] = []
    for m in TOKEN.finditer(text):
        tok = m.group(0)
        cuts = [0] + [c for h in re.finditer(HEX_TEXT, tok) for c in range(h.start() + 8, h.end(), 8)] + [len(tok)]
        for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
            w = scale * sum(CHAR_PT.get(c, DEFAULT_PT) for c in tok[a:b])
            before = (text[m.start() - 1] if m.start() else "") if k == 0 else ""
            if before == NBSP and out:                    # glued to the piece before it
                out[-1] = (out[-1][0], out[-1][1] + scale * SPACE_PT + w)
            else:
                out.append((scale * SPACE_PT if before.isspace() else 0.0, w))
    return out


def _one_line_pt(pieces: Sequence[Tuple[float, float]]) -> float:
    return sum(g + w for g, w in pieces) - (pieces[0][0] if pieces else 0.0)


def _wrapped_lines(pieces: Sequence[Tuple[float, float]], width_pt: float) -> int:
    """How many lines a cell takes in a column `width_pt` wide: its pieces laid out greedily, as LaTeX's ragged-right lines are (an
    estimate: LaTeX's interword spaces stretch and shrink a little)."""
    lines, cur = 1, None
    for gap, w in pieces:
        if cur is None:
            cur = w
        elif cur + gap + w <= width_pt:
            cur += gap + w
        else:
            lines, cur = lines + 1, w
    return lines


def _fewest_lines(cells: Mapping[int, Sequence[Sequence[Tuple[float, float]]]], lo: Mapping[int, float], avail: float,
                  step_pt: float = 1.0) -> Dict[int, float]:
    """Widths (inches) for the wrapping columns that make the table as short as the room allows (D-160: the main text's page budget).
    Each column starts at its minimum; the room left is handed out in steps. A step makes one row shorter (by one line or more): every
    cell of that row taller than the target is widened just enough to reach it. The step taken is the one that removes the most
    printed lines in the whole table per inch of width. A row's height is its tallest cell; the header is a row. Stops when no step
    fits the room; the caller shares what is left. Widths are tried on a 1 pt grid."""
    cols = list(lo)
    n_rows = len(next(iter(cells.values()))) if cells else 0
    base = {j: (lo[j] - 0.04) * PT_PER_IN for j in cols}
    top = {j: max([_one_line_pt(c) for c in cells[j]] + [base[j]]) for j in cols}
    grid = {j: [base[j] + k * step_pt for k in range(int((top[j] - base[j]) / step_pt) + 2)] for j in cols}
    table = {j: [[_wrapped_lines(c, g) for c in cells[j]] for g in grid[j]] for j in cols}
    room = avail - sum(lo.values())
    at = {j: 0 for j in cols}

    def row_height(i: int, where: Mapping[int, int]) -> int:
        return max([table[j][where[j]][i] for j in cols] + [1])

    def height(where: Mapping[int, int]) -> int:
        return sum(row_height(i, where) for i in range(n_rows))

    now = height(at)
    while True:
        best = None
        for i in range(n_rows):
            for target in range(row_height(i, at) - 1, 0, -1):
                mv: Dict[int, int] = {}
                for j in cols:
                    if table[j][at[j]][i] > target:
                        k = next((k for k in range(at[j] + 1, len(grid[j])) if table[j][k][i] <= target), None)
                        if k is None:
                            break
                        mv[j] = k
                else:
                    cost = sum((grid[j][k] - grid[j][at[j]]) / PT_PER_IN for j, k in mv.items())
                    if cost <= room + 1e-9:
                        gain = now - height({**at, **mv})
                        if gain > 0 and (best is None or gain / max(cost, 1e-6) > best[0] + 1e-12):
                            best = (gain / max(cost, 1e-6), mv, cost, gain)
                    continue
                break                                     # this row cannot get shorter than the target: no lower target either
        if best is None:
            break
        _, mv, cost, gain = best
        at.update(mv)
        room -= cost
        now -= gain
    return {j: grid[j][at[j]] / PT_PER_IN + 0.04 for j in cols}


def _fixed_width_cols(t: Table) -> str:
    specs, w, numeric = _width_plan(t)
    mean = sum(w.values()) / len(w) if w else 1.0
    out = []
    for j, spec in enumerate(specs):
        if spec is not None:
            out.append(spec)
            continue
        align = r"\raggedleft" if numeric[j] else r"\raggedright"
        out.append(rf">{{\hsize={w[j] / mean:.3f}\hsize{align}\hyphenpenalty=10000\exhyphenpenalty=10000\arraybackslash}}X")
    return "".join(out)


def _width_plan(t: Table) -> Tuple[List[Optional[str]], Dict[int, float], Dict[int, bool]]:
    """The column set of a table with a layout mark (D-160): the table is exactly \\linewidth wide (tabularx or xltabular; 6.5 in, or
    9.0 in for a landscape mark), so nothing runs off the page and nothing is shrunk. A column whose cells and header are all short
    stays natural ('r' for numbers, 'l' for text). Every other column is an X column that wraps (text ragged right, numbers ragged
    left), at least as wide as its longest unbreakable piece (header included). Widths are estimated from the paper font's measured
    character widths (CHAR_PT): the room left after the natural columns goes first where it removes the most printed lines
    (_fewest_lines), then to the text columns still short of their longest cell (up to HI_CAP_IN), then to all text columns in
    proportion. The widths become the hsize factors tabularx needs (they sum to the number of X columns)."""
    if t.fixed_plan is not None:
        return t.fixed_plan
    width = 9.0 if (t.layout or "").endswith("landscape") else 6.5
    specs: List[Optional[str]] = []
    numeric: Dict[int, bool] = {}
    lo: Dict[int, float] = {}
    hi: Dict[int, float] = {}
    cells: Dict[int, List[List[Tuple[float, float]]]] = {}
    fixed_in = 0.0
    for j in range(len(t.columns)):
        col = [t.columns[j]] + [r[j] for r in t.rows]
        pads = _decimal_pads(t)
        pieces = [_pieces(Cell(c.printed + "0" * pads.get((i, j), 0), c.kind, bold=c.bold), t.font, mono=j in t.mono)
                  for i, c in enumerate(col[1:])]
        pieces = [_pieces(col[0], t.font)] + pieces                          # the header is never typewriter
        numeric[j] = _numeric_column(t, j)
        longest = max([len(r[j].printed) for r in t.rows if r[j].printed not in DASHES] + [0])
        if longest <= 8 and len(t.columns[j].printed) <= 10:
            specs.append("r" if numeric[j] else "l")
            fixed_in += max(_one_line_pt(p) for p in pieces) / PT_PER_IN + SEP_IN
            continue
        widest = max([w for p in pieces for _, w in p] + [1.0]) / PT_PER_IN
        # a long unbreakable word (a stamped key) carries 2% for the estimate's error, which only matters at that length
        lo[j] = widest * (1.02 if widest > 1.5 else 1.0) + 0.04
        one = max(_one_line_pt(p) for p in pieces[1:]) / PT_PER_IN + 0.04 if len(pieces) > 1 else lo[j]
        # a number column only wraps between a point and its interval: it gets no share of the spare room past _fewest_lines
        hi[j] = lo[j] if numeric[j] else max(lo[j], min(one, HI_CAP_IN))
        cells[j] = pieces
        specs.append(None)
    avail = width - 0.1 - fixed_in - len(lo) * SEP_IN          # 0.1 in kept spare for the estimate's error
    if sum(lo.values()) > avail:
        w = dict(lo)                                     # cannot fit: the measurement reports it, and the table needs a split
    else:
        w = _fewest_lines(cells, lo, avail)
        extra = avail - sum(w.values())
        grow = [j for j in lo if not numeric[j]] or list(lo)
        short = {j: max(0.0, hi[j] - w[j]) for j in grow}
        if sum(short.values()) >= extra and sum(short.values()) > 0:
            w = {j: w[j] + extra * short.get(j, 0.0) / sum(short.values()) for j in lo}
        else:
            extra -= sum(short.values())
            w = {j: w[j] + short.get(j, 0.0) + (extra * hi[j] / sum(hi[k] for k in grow) if j in grow else 0.0) for j in lo}
    return specs, w, numeric


LINE_PT = {None: 11.0, "small": 11.0, "footnotesize": 9.5}      # \baselineskip at \small and \footnotesize in the 10 pt document
RULES_PT, ADDSPACE_EM = 10.0, 0.5                             # booktabs' three rules with their separations; \addlinespace


def height_in(t: Table) -> float:
    """An estimate of a marked float table's height (the tabular alone): each row as tall as its tallest cell at the planned column
    widths (the writer's own wrap estimate), plus the rules and the row-group spaces. Used to plan sideways packing (plan_packing);
    the measure tool reports the real height."""
    natural = _natural(t)
    specs, w, _ = (None, {}, {}) if natural else _width_plan(t)
    pads = _decimal_pads(t)
    scale = FONT_SCALE.get(t.font, 1.0)

    def lines(c: "Cell", j: int, i: Optional[int]) -> int:
        if natural or specs[j] is not None:
            return 1
        text = c.printed + ("0" * pads.get((i, j), 0) if i is not None else "")
        return _wrapped_lines(_pieces(Cell(text, c.kind, bold=c.bold), t.font, mono=i is not None and j in t.mono),
                              (w[j] - 0.04) * PT_PER_IN)

    n = max(lines(c, j, None) for j, c in enumerate(t.columns))
    n += sum(max(lines(c, j, i) for j, c in enumerate(r)) for i, r in enumerate(t.rows))
    em = 9.0 * scale
    space = sum((2 if t.spaced else 1) * ADDSPACE_EM * em for i in t.groups if 0 < i < len(t.rows))
    space += ADDSPACE_EM * em * (len(t.rows) - 1 - len([i for i in t.groups if 0 < i < len(t.rows)])) if t.spaced else 0.0
    return (n * LINE_PT.get(t.font, 11.0) + RULES_PT + space) / PT_PER_IN


def notes_height_in(notes: Sequence[str], width_in: float) -> float:
    """The supplement's notes paragraph (every note of every file, once, \\footnotesize, under the last float)."""
    if not notes:
        return 0.0
    n = _wrapped_lines(_pieces(Cell(" ".join(notes)), "footnotesize"), width_in * PT_PER_IN)
    return (n * 9.5 + 3.0) / PT_PER_IN


CAPTION_IN, CONT_IN, PACK_GAP_IN, PAGE_IN = 0.53, 0.33, 0.17, 6.5    # the first float's caption; a later unit's title; \bigskip
# (a caption is followed by \belowcaptionskip = \baselineskip in the paper's template, Edith's ruling at proof 3)
# (the estimate runs at most 3% under the measured height on this paper's 131 marked tables; packing allows 4%)


def split_rows_by_space(t: Table, key: Sequence[int], cols: Sequence[int]) -> None:
    """A sideways table too tall for one page, split by rows into parts that each hold the same columns (key, then cols) with one
    shared set of column widths (share_widths), the rows cut by space, not by group (Edith, proof 3, pp. 55-57): the fewest parts
    whose estimated heights fit a page (the caption on the first, every note under the last), the rows spread evenly over them so no
    page is left mostly empty. Sets t.split_parts, t.split_key and t.share_widths."""
    idx = list(key) + [j for j in cols if j not in key]
    full = Table([t.columns[j] for j in idx], [[r[j] for j in idx] for r in t.rows], layout="landscape", font=t.font,
                 mono=[p for p, j in enumerate(idx) if j in t.mono], groups=list(t.groups), spaced=t.spaced)
    specs, w, _ = _width_plan(full)
    full.fixed_plan = (specs, w, _)
    lh = LINE_PT.get(t.font, 11.0) / PT_PER_IN
    pads = _decimal_pads(full)

    def lines(c: "Cell", j: int, i: int) -> int:
        if specs[j] is not None:
            return 1
        return _wrapped_lines(_pieces(Cell(c.printed + "0" * pads.get((i, j), 0), c.kind, bold=c.bold), t.font, mono=j in full.mono),
                              (w[j] - 0.04) * PT_PER_IN)

    head = max(lines(c, j, -1) if specs[j] is None else 1 for j, c in enumerate(full.columns)) * lh + RULES_PT / PT_PER_IN
    em = 9.0 * FONT_SCALE.get(t.font, 1.0) / PT_PER_IN
    gap = [(2 if t.spaced else 1) * ADDSPACE_EM * em if i in t.groups and i > 0 else (ADDSPACE_EM * em if t.spaced and i > 0 else 0.0)
           for i in range(len(full.rows))]
    rows = [max(lines(c, j, i) for j, c in enumerate(r)) * lh + gap[i] for i, r in enumerate(full.rows)]
    # every note of the table prints once, under its last float: under the last part only when no panel follows the parts
    owners = [t] + [p for _, p in t.panels]
    notes = 0.0 if t.panels else notes_height_in([" ".join(c.printed for c in n if c.printed) for o in owners for n in o.notes], 9.0)
    m = len(rows)
    pre = [0.0]
    for h in rows:
        pre.append(pre[-1] + h)

    def load(a: int, b: int, first: bool, last: bool) -> float:   # a part's share of its page: rows a..b-1 with the header
        return (1.04 * (head + pre[b] - pre[a]) + (CAPTION_IN if first else CONT_IN) + (notes if last else 0.0)) / PAGE_IN

    # the fewest parts that all fit, and among those the cut whose fullest page is least full (rows spread evenly): dynamic
    # programming over (rows placed, parts used), the cost of a cut being its largest page load
    for n in range(1, m + 1):
        best = {(0, 0): (0.0, [0])}
        for k in range(1, n + 1):
            for i in range(1, m + 1):
                cand = None
                for j in range(k - 1, i):
                    prev = best.get((j, k - 1))
                    if prev is None:
                        continue
                    ld = load(j, i, k == 1, k == n and i == m)
                    if ld > 1.0:
                        continue
                    cost = max(prev[0], ld)
                    if cand is None or cost < cand[0]:
                        cand = (cost, prev[1] + [i])
                if cand is not None:
                    best[(i, k)] = cand
        if (m, n) in best:
            cuts = best[(m, n)][1]
            t.layout = "split landscape"
            t.split_key, t.share_widths = list(key), True
            t.split_parts = [(list(range(a, b)), [j for j in cols if j not in key]) for a, b in zip(cuts, cuts[1:])]
            return
    raise ValueError("split_rows_by_space: a single row is taller than a page")


def plan_packing(t: Table) -> None:
    """Vision's converter (proof 3, C.30) sets each unit of a table (its split parts, then its panels and their parts) as its own float,
    unless the unit is marked to share the previous unit's float ("% pack: with-previous"). Mark consecutive units of one
    orientation (sideways units on a 6.5 in page, upright ones on a 9.0 in page; a long table ends a run) while their estimated
    heights (the caption on the first, a title on each panel part, every note under the last) fit one page, so no float page is mostly
    empty (Edith §1.4: at least 60% full; upright float pages too since Vision's proof check counts them). The measure tool checks."""
    owners = [t] + [p for _, p in t.panels]
    units = []                                           # (owner, part index, orientation or None for a long table, height)
    for o in owners:
        o.pack, o.pack_parts = False, []
        parts = split_tables(o) if o.layout in SPLITS and o.split_parts else [o]
        for k, part in enumerate(parts):
            way = None if o.layout == "longtable" else ("sideways" if (o.layout or "").endswith("landscape") else "upright")
            units.append((o, k, way, height_in(part) if way else 0.0))
    notes = [" ".join(c.printed for c in n if c.printed) for o in owners for n in o.notes]
    used, run = None, None
    for u, (o, k, way, h) in enumerate(units):
        if way is None:
            used, run = None, None
            continue
        page = PAGE_IN if way == "sideways" else 9.0
        h = 1.04 * h + (notes_height_in(notes, 9.0 if way == "sideways" else 6.5) if u == len(units) - 1 else 0.0)
        title = CONT_IN if o is not t else 0.0                           # a panel's italic title, printed on each of its parts
        if used is not None and run == way and used + PACK_GAP_IN + title + h <= page:
            used += PACK_GAP_IN + title + h
            if k == 0:
                o.pack = True
            else:
                o.pack_parts.append(k)
        else:
            used, run = (CAPTION_IN if u == 0 else CONT_IN) + title + h, way   # a new float: the caption, or "(continued)"


def _natural(t: Table) -> Optional[str]:
    """A float or landscape table whose every column fits on one line within the width is set at its natural width (a plain tabular,
    centred by the converter), not stretched to \\linewidth with the spare room in one column (the batch (g) check, TAB-30). Returns
    its column spec, or None."""
    if t.layout not in ("float", "landscape"):
        return None
    width = 9.0 if t.layout.endswith("landscape") else 6.5
    pads = _decimal_pads(t)
    total, spec = 0.0, []
    for j in range(len(t.columns)):
        cells = [_pieces(t.columns[j], t.font)] + [
            _pieces(Cell(r[j].printed + "0" * pads.get((i, j), 0), r[j].kind, bold=r[j].bold), t.font, mono=j in t.mono)
            for i, r in enumerate(t.rows)]
        total += max(_one_line_pt(c) for c in cells) / PT_PER_IN + SEP_IN
        spec.append("r" if _numeric_column(t, j) else "l")
    return "".join(spec) if total <= width - 0.1 else None


def split_tables(t: Table) -> List[Table]:
    """A split table's parts as tables: each with the key columns then its own columns, its own rows; the notes go under the last part
    (Vision's converter prints every part's notes once, under the last). The layout mark is kept on the first part only by the writer.
    Typewriter columns, row groups, once-per-group columns and row spacing carry over to the parts (a group starts where it starts in
    the full table)."""
    parts = []
    plan = None
    if t.share_widths:
        sets = {tuple(list(t.split_key) + [j for j in cols if j not in t.split_key]) for _, cols in (t.split_parts or [])}
        if len(sets) != 1:
            raise ValueError("share_widths: the parts do not hold the same columns")
        idx = list(next(iter(sets)))
        full = Table([t.columns[j] for j in idx], [[r[j] for j in idx] for r in t.rows], layout=t.layout, font=t.font,
                     mono=[p for p, j in enumerate(idx) if j in t.mono])
        plan = _width_plan(full)
    for k, (rows, cols) in enumerate(t.split_parts or []):
        idx = list(t.split_key) + [j for j in cols if j not in t.split_key]
        sel = range(len(t.rows)) if rows is None else rows
        last = k == len(t.split_parts) - 1                                                  # type: ignore[arg-type]
        numeric = None
        if plan is None and len(sel) < len(t.rows):
            whole = Table([t.columns[j] for j in idx], [[r[j] for j in idx] for r in t.rows])
            numeric = [_numeric_column(whole, p) for p in range(len(idx))]
        parts.append(Table([t.columns[j] for j in idx], [[t.rows[i][j] for j in idx] for i in sel], t.notes if last else [], {},
                           short_notes=list(t.short_notes) if last else [], layout=t.layout, font=t.font,
                           mono=[p for p, j in enumerate(idx) if j in t.mono],
                           groups=[p for p, i in enumerate(sel) if p > 0 and i in t.groups],
                           once=[p for p, j in enumerate(idx) if j in t.once], spaced=t.spaced,
                           pack=t.pack if k == 0 else k in t.pack_parts, fixed_plan=plan, numeric_cols=numeric))
    return parts


def split_columns(t: Table, landscape: bool = True, key: Sequence[int] = (0,)) -> List[List[int]]:
    """A greedy column split for a table too wide for one page: columns in order, each part holding as many as fit beside the key
    columns, each column at its longest cell up to 24 characters' width and at least its longest piece (the same font estimate as
    _fixed_width_cols, with its 0.1 in spare)."""
    width = (9.0 if landscape else 6.5) - 0.1
    cap = 24 * CHAR_PT["n"] * FONT_SCALE.get(t.font, 1.0)

    def need(j: int) -> float:
        cells = [r[j] for r in t.rows if r[j].printed not in DASHES] + [t.columns[j]]
        pieces = [_pieces(c, t.font) for c in cells]
        token = max([w for p in pieces for _, w in p] + [1.0])
        longest = max(_one_line_pt(p) for p in pieces)
        return max(token, min(longest, cap)) / PT_PER_IN + 0.04 + SEP_IN

    base = sum(need(j) for j in key)
    parts: List[List[int]] = [[]]
    used = base
    for j in range(len(t.columns)):
        if j in key:
            continue
        if parts[-1] and used + need(j) > width:
            parts.append([])
            used = base
        parts[-1].append(j)
        used += need(j)
    return parts


# A long table's caption at the template's size and the full text width (Edith, M1-10). longtable sets the caption in a 4 in box at the
# surrounding size (the converter's \small wraps the table), and the \caption row takes no size command before it (a \normalsize line there
# stops the build with "Misplaced \noalign"), so longtable's own \LT@makecaption is redefined with \normalsize inside its box. The
# definition is local to the group the table is input in.
LONGTABLE_CAPTION_TEX = (r"\makeatletter\setlength{\LTcapwidth}{\linewidth}"
                         r"\def\LT@makecaption#1#2#3{\LT@mcol\LT@cols c{\hbox to\z@{\hss\parbox[t]\LTcapwidth{\normalsize"
                         r"\sbox\@tempboxa{#1{#2: }#3}\ifdim\wd\@tempboxa>\hsize #1{#2: }#3\else"
                         r" \hbox to\hsize{\hfil\box\@tempboxa\hfil}\fi\endgraf\vskip\baselineskip}\hss}}}\makeatother")


def table_tex(t: Table, oid: str, cells: Optional[str] = None, mark: bool = True) -> bytes:
    """A table's .tex. Without a layout mark: a natural-width tabular (the old form). With one: a \\linewidth tabularx (float,
    landscape, split), or an xltabular that breaks across pages (longtable) carrying its own caption placeholder and label."""
    natural = _natural(t)
    fixed = t.layout is not None and natural is None
    cols = natural or (_fixed_width_cols(t) if fixed else "".join(_col_spec(t, j) for j in range(len(t.columns))))
    if t.layout is not None and t.layout not in LAYOUTS:
        raise ValueError(f"{oid}: layout {t.layout!r} is not one of {LAYOUTS}")
    if len(t.short_notes) > 2 or any(not 0 <= i < len(t.notes) for i in t.short_notes):
        raise ValueError(f"{oid}: at most 2 short notes, each one of the table's notes ({t.short_notes})")
    head = " & ".join(tex_text(c.printed) for c in t.columns) + r" \\"
    lines = ([f"% layout: {t.layout}"] if t.layout and mark else []) + ([f"% font: {t.font}"] if t.font else []) + (
             ["% pack: with-previous"] if t.pack else []) + [
             f"% {oid}: generated by harness/analysis/paper_outputs.py; do not edit (every cell's source is in "
             f"{cells or oid + '.cells.json'})"]
    if t.layout == "longtable":
        lines += [LONGTABLE_CAPTION_TEX,
                  r"\begin{xltabular}{\linewidth}{" + cols + "}",
                  r"\caption{⟦CAPTION⟧}\label{⟦LABEL⟧}\\",
                  r"\toprule", head, r"\midrule", r"\endfirsthead",
                  r"\multicolumn{" + str(len(t.columns)) + r"}{c}{\normalsize \tablename~\thetable: (continued)}\\[6pt]",   # centred, at caption size,
                  r"\toprule", head,                                                                                    # with its colon (Edith, proof 5, B2-S9)
                  r"\midrule",
                  r"\endhead", r"\bottomrule", r"\endlastfoot"]
    elif fixed:
        lines += [r"\begin{tabularx}{\linewidth}{" + cols + "}", r"\toprule", head, r"\midrule"]
    else:
        lines += [r"\begin{tabular}{" + cols + "}", r"\toprule", head, r"\midrule"]
    pads = _decimal_pads(t)
    for i, r in enumerate(t.rows):
        if i in t.groups and i > 0:
            lines.append(r"\addlinespace[1em]" if t.spaced else r"\addlinespace")
        elif t.spaced and i > 0:
            lines.append(r"\addlinespace")
        blank = {j for j in t.once if i > 0 and i not in t.groups and r[j].printed == t.rows[i - 1][j].printed}
        cells_tex = [("" if j in blank else (mono_tex(c.printed) if j in t.mono and c.printed not in DASHES else tex_text(c.printed))
                      + (r"\phantom{" + ("" if "." in c.printed else ".") + "0" * pads[(i, j)] + "}" if (i, j) in pads else ""))
               for j, c in enumerate(r)]
        lines.append(" & ".join(r"\textbf{" + x + "}" if c.bold else x for x, c in zip(cells_tex, r)) + r" \\")
    if t.layout == "longtable":
        lines += [r"\end{xltabular}"]
    elif fixed:
        lines += [r"\bottomrule", r"\end{tabularx}"]
    else:
        lines += [r"\bottomrule", r"\end{tabular}"]
    for i, n in enumerate(t.notes):
        lines.append(("% note-short: " if i in t.short_notes else "% note: ") + tex_text(" ".join(c.printed for c in n if c.printed)))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _cells_doc(t: Table) -> Dict[str, Any]:
    return {"columns": [c.record() for c in t.columns], "rows": [[c.record() for c in r] for r in t.rows],
            "notes": [[c.record() for c in n] for n in t.notes],
            "caption": {k: [c.record() for c in v] for k, v in sorted(t.caption.items())}}


def dumps(obj: Any) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
