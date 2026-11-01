"""TAB-20: the pre-registration timeline (Method appendix; disclosure). The plan entry (7b43f91): locks 1-4 with their public proofs
(lock 2 by Zenodo only; lock 3's Zenodo v3 during the main run), the analysis and data stamps, each paid run's window (invocation,
window start, pauses, last commit), what was sealed when, and the exposed-base sensitivity; free analysis 31's text adds the
deviations and amendment, and the lock-proof column of Edith's settlement item E-16.

The table is a chronological list of events (one row each) with three panels:
1. the lock fingerprints and public proofs (E-16's lock-proof column; its "Next paid data" entries mix first calls with Study 1b's
   first invocation, so a note says which each is, checked against the records the timeline prints: `_next_paid_note`);
2. every run's window (every run that sent an API call, smoke-1's rejected and unbilled one included), in the spend log's order
   (oldest first);
3. Study 1b's exposed-base sensitivity (D-97), readings only (its d, interval and p are TAB-10's).

Where the facts come from. Every date, time, commit, hash, DOI and gist or Wayback id is cut from a pinned text source by a regex
(`paper_out_ops.extract`, which records the regex as the cell's formula) or read whole from a markdown cell; nothing is typed:
- the text sources pinned in paper_out_ops.py: the spend log, the lock manifest, the decision register, the findings register
  (section 5), the Study 1 spec and LOG.md;
- five more, pinned here at the main commit that last changed each: Edith's plan settlement g4 (item E-16: the tag times read from git,
  the lock-proof table, the Study 1b sets' commit, the length sweep's first send and last commit, the C4 commit and the lock-4
  lineage, and her wording on Lock 2's missing gist) and g3 (item E-04: the helper, build and review sessions the exposed bases were
  shown in), the public lock-4 fingerprint file (all four locks' commit IDs and tar SHA-256s), and Edith's Study 1b and top-up
  clearance reviews (each data stamp's live gist time and her byte-identical re-run; the Study 1b run record of each invocation);
- Study 1b's analysis file (`s1b`, pinned in paper_out_core) for the sensitivity panel, and Study 1b's k.json pin (its commit).
Typed text is limited to digit-free labels (event names and short summaries); Edith fact-checks those. A typed clause that states a
fact (a round in flight, a re-submit, which lock a seal named) is guarded by `guard` or `evidence`: the build stops if its record no
longer says so (`evidence` also keeps the record in the cell's provenance, unprinted).

What never prints (PO-1, Q24, Q26; `_NOT_PRINTED`, checked on every printed text of the table, its notes, caption and panels): decision
ids (the register is not released; each id stays in cells.json as an unprinted ref and its raw value, see `kept` and `rid`), internal
record names (LOG.md, the findings register, the decision register, the spend log: plain words instead), a time zone no record states,
and "the authors" or "the user" for ourselves ("we").

A date is printed on the first row of each UTC day only. Every other sourced date on a row is checked at build time against the day it
sits under, and the times within a day are checked to run in order, so a moved row fails the build instead of printing a wrong day.
UTC dates (the spend log's Date column, git times, the public records' ISO times) are checked against the UTC day itself; local dates
(LOG.md's entry headers and the decision register's Date column) against the local date of the row's UTC time, or, for a row with no
time, against the local dates of the timed rows around it (`Timeline`, `_local_day`). Deviation 1's ruling has no recorded time and may
fall on either side of midnight UTC, so it prints its own local date and sits between the events that bound it. The paper names no time
zone for these local dates (Q26): it says only that they are local calendar dates, not UTC ones (`_local_dates_evidence`).

A cell made of two or more cut or read parts (`cat`) records one formula entry per ref, in ref order, so a checker can repeat each cut.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paper_out_core import (EMPTY, YES_NO, Cell, KeyMissing, Ref, Source, Store, Table, integer, join_key, label, output,
                             register_source, text_of)
from .paper_out_names import STUDY1B_TESTS, _printed
from .paper_out_ops import cell_ref, en_dash, extract, group_starts, line_of, set_widths

# ---------------------------------------------------------------- further pinned text sources (main commit that last changed each)

register_source(Source("settle_g4", "ops/reviews/2026-10-15-plan-settlement/g4.md", "05fddf9",
                       "f609e65d2b4a6fbc4d1706d1b333083a8d0d8506c649adab656a793f7de2075b", kind="text",
                       what="Edith's plan settlement, group 4 (item E-16: tag and commit times from git, the lock-proof table)"))
register_source(Source("settle_g3", "ops/reviews/2026-10-15-plan-settlement/g3.md", "05fddf9",
                       "92f48d733d8986a72edc3d19b18bb24906a4dc9700c9a44ebe7274218d771745", kind="text",
                       what="Edith's plan settlement, group 3 (item E-04: the sessions the exposed bases were shown in)"))
register_source(Source("fp_lock4", "decisions/briefings/2026-10-13-zenodo-v4/fingerprint-lock4.txt", "4d60335",
                       "600b53eb5664a0be248db85aa2dad5857145baaf18bd2bf573195f030a1629ad", kind="text",
                       what="The public lock-4 fingerprint file (Zenodo v4): each lock's tag, commit ID and tar SHA-256"))
register_source(Source("clr_1b", "ops/reviews/2026-10-13-clearance-study1b-1.md", "5b0f8f5",
                       "042a5e2d41e775c64db2dc581f771a7c9d53a459158f39ada4a6e6526660e645", kind="text",
                       what="Edith's Study 1b clearance review: the live data stamp and her byte-identical re-run"))
register_source(Source("clr_topup", "ops/reviews/2026-10-13-clearance-topup-1.md", "ea3181d",
                       "dc5989d53a19c5aafa67f02401bfa007f856a0e4bd431c69fdb0f70aa24965a3", kind="text",
                       what="Edith's top-up clearance review: the live data stamp and her byte-identical re-run"))

DASH = label("—")
DATE_RX = r"(\d{4}-\d\d-\d\d)"
SENS = "sensitivity_exposed_bases_excluded"
PRIM = ("confirmatory", "primary_margin_5")
ID = "decision id: the register is not released, so the id is kept here, not printed (PO-1)"
# The top-up's lock (group 1, printed) and the rulings behind it (group 2, decision ids, kept unprinted). The pattern needs the spend
# log's own words "with the declared start change": they are the guard for our printed "with the disclosed start change" (D-161).
TU_LOCK = r"\(D-99, D-100; (prereg-lock-4) with the declared start change ([^)]+)\)"
TU_CHANGE = "with the disclosed start change"

# Never printed anywhere in TAB-20 (cells, notes, caption, panel titles and panels): a decision id; an internal record's name; a time
# zone or a 'UTC calendar' claim no record states; the third person for ourselves; 'helper sessions' (our own work sessions).
_NOT_PRINTED = re.compile(r"\bD-\d|India|\bIST\b|Standard Time|UTC calendar|LOG\.md|[Ff]indings register|[Dd]ecision register|"
                          r"register date|[Ss]pend log|\b[Tt]he authors\b|\b[Tt]he user\b|helper session|helper, build")

# ---------------------------------------------------------------- small helpers


# The per-ref formula list of each multi-ref cell built by `cat` (keyed by id; the cell is kept so that an id is never reused).
_PER_REF: Dict[int, Tuple[Cell, List[str]]] = {}


def _ref_formulas(c: Cell) -> List[str]:
    """One formula entry per ref of a cell, in ref order: 'whole value' for a part read whole (text_of), else its cut."""
    hit = _PER_REF.get(id(c))
    if hit is not None and hit[0] is c:
        return hit[1]
    if len(c.refs) == 1:
        return [c.formula or "whole value"]
    raise ValueError(f"cell {c.printed!r} has {len(c.refs)} refs and no per-ref formulas: build it with cat")


def cat(*parts: Any, sep: Optional[str] = None) -> Cell:
    """Typed text (str) and read or cut cells joined into one printed cell, keeping every part's source. With no `sep`, a space goes
    between parts, except before , ; : . ) and after (; with `sep`, the parts are joined by it. A cell with one ref keeps that ref's
    formula (none for a part read whole, so the audit checks its raw value); a cell with two or more refs records one formula entry per
    ref, in ref order ('ref 2: text cut /…/ group 1', or 'ref 1: whole value')."""
    cells = [label(p) if isinstance(p, str) else p for p in parts]
    out = ""
    for c in cells:
        if not c.printed:
            continue
        if out:
            if sep is not None:
                out += sep
            elif not (c.printed[0] in ",;:.)" or out.endswith("(")):
                out += " "
        out += c.printed
    refs = tuple(r for c in cells for r in c.refs)
    if not refs:
        return label(out)
    raws = [c.raw for c in cells if c.kind == "num"]
    raw = raws[0] if len(raws) == 1 else raws
    if len(refs) == 1:
        return Cell(out, raw=raw, refs=refs, formula=next(c.formula for c in cells if c.refs))
    per_ref = [f for c in cells if c.refs for f in _ref_formulas(c)]
    cell = Cell(out, raw=raw, refs=refs, formula="; ".join(f"ref {i}: {f}" for i, f in enumerate(per_ref, 1)))
    _PER_REF[id(cell)] = (cell, per_ref)
    return cell


def md_time(S: Store, src: str, pattern: str, rx: str, offset: int = 0) -> Cell:
    """A record's ISO stamp ("2026-10-11T19:35:19Z") printed as "10-11 19:35:19": month-day and time, UTC, with no T and no Z, the form
    of the lock panel's "Tag cut (UTC, month-day)" column, so that every timestamp of the panel reads one way (Edith, proof 4, p. 37:
    three forms in one panel, the ISO one broken at its T). `rx` holds the word STAMP where the record's ISO stamp sits; the cell keeps
    both cuts (the month-day and the time of day) as its sources."""
    day = cut(S, src, pattern, rx.replace("STAMP", r"\d{4}-(\d\d-\d\d)T\d\d:\d\d:\d\dZ"), offset=offset)
    hms = cut(S, src, pattern, rx.replace("STAMP", r"\d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z"), offset=offset)
    return cat(day, hms)


def span(a: Cell, b: Cell) -> Cell:
    """'a–b' with no spaces (a time range), keeping both sources."""
    return cat(a, "–", b, sep="")


def line(S: Store, src: str, pattern: str, offset: int = 0) -> Ref:
    """The whole line `offset` lines below the one line of `src` that matches `pattern`."""
    return cell_ref(S, src, line_of(S, src, pattern, expect=1) + offset)


def cut(S: Store, src: str, pattern: str, rx: str, group: int = 1, offset: int = 0) -> Cell:
    return extract(line(S, src, pattern, offset), rx, group=group)


def spend_ref(S: Store, run: str, col: str) -> Ref:
    n = line_of(S, "spend_log", rf"^\| \d{{4}}-\d\d-\d\d \| \w+ \| {re.escape(run)} \|", expect=1)
    return cell_ref(S, "spend_log", n, col)


def spend_cut(S: Store, run: str, col: str, rx: str, group: int = 1) -> Cell:
    return extract(spend_ref(S, run, col), rx, group=group)


def reg_ref(S: Store, did: str, col: str) -> Ref:
    return cell_ref(S, "register", line_of(S, "register", rf"^\| {re.escape(did)} \|", expect=1), col)


def reg_id(S: Store, did: str) -> Cell:
    return text_of(reg_ref(S, did, "ID"))


def reg_cut(S: Store, did: str, rx: str, col: str = "Decision (plain)") -> Cell:
    return extract(reg_ref(S, did, col), rx)


def find_cell(S: Store, row_pattern: str, col: str) -> Ref:
    """A cell of the findings register's section 5.1 timeline table (the row found by its first cell)."""
    return cell_ref(S, "findings", line_of(S, "findings", row_pattern, expect=1), col)


def e16(S: Store, lock: str, col: str) -> Ref:
    """A cell of E-16's lock-proof table in the settlement (the row found by its lock number, read from the row itself)."""
    head = line_of(S, "settle_g4", r"^\s*\| Lock \| Tag \(UTC\) \| Public proof \(UTC\) \| Next paid data \|$", expect=1)
    for n in range(head + 2, head + 6):
        if S.get("settle_g4", join_key(f"L{n}", "Lock")) == lock:
            return cell_ref(S, "settle_g4", n, col)
    raise KeyMissing(f"E-16 table: no row for lock {lock}")


def guard(r: Ref, rx: str, what: str) -> None:
    """A typed (digit-free) clause stays true only while its record says so: the build stops if the record no longer matches."""
    if not re.search(rx, str(r.value)):
        raise ValueError(f"TAB-20: {r.source}:{r.key} no longer records that {what}")


def kept(c: Cell, why: str) -> Cell:
    """A read or cut kept in a cell's record but not printed: `cat` adds its ref and its formula (with why it is not printed) to the
    cell, and skips its text. Used for decision ids (no id prints; each stays in cells.json as the ref and its raw value) and for the
    record a typed clause rests on."""
    return Cell("", raw=c.raw, refs=c.refs, formula=f"{c.formula or 'whole value'}; not printed: {why}")


def rid(S: Store, did: str) -> Cell:
    """A decision's id from its register row, kept in the cell's provenance and not printed (PO-1)."""
    return kept(reg_id(S, did), ID)


def evidence(r: Ref, rx: str, what: str) -> Cell:
    """`guard`, and the record kept (unprinted) in the cell that states the typed clause: the cut is the regex's group 1."""
    guard(r, rx, what)
    return kept(extract(r, rx), f"the record for '{what}'")


def no_internal_names(out: Table) -> Table:
    """The build stops if any printed text of the table (cells, notes, caption, panel titles, panels) shows a decision id or another
    word in `_NOT_PRINTED`."""
    bad = sorted({t for t in _printed(out) if _NOT_PRINTED.search(t)})
    if bad:
        raise ValueError(f"TAB-20 prints a decision id or an internal name (plain words instead; ids stay in provenance): {bad}")
    return out


def trunc(c: Cell) -> Cell:
    """A cut prefix of a longer stamped id (a gist id or SHA-256) printed with an ellipsis, as the records shorten them."""
    return cat(c, "…", sep="")


def smoke1_note(S: Store) -> Cell:
    """smoke-1's one call: rejected by the API and not billed (its spend-log row)."""
    return cat(spend_cut(S, "smoke-1", "What ran", r"(rejected by the API: HTTP \d+) invalid"), ";",
               spend_cut(S, "smoke-1", "Notes", r"is (unbilled) \("))


def topup_once(S: Store) -> Cell:
    """The top-up's calls were each sent once: the round in flight at the pause was collected on resume, not re-sent (its spend-log
    row; settlement E-13). Printed after the typed 'every call'."""
    return spend_cut(S, "topup-1", "Notes", r"every custom id (at attempt 1 \(no re-send, no crash re-run, no failed submit\))")


# A lock's name prints as "Lock N" (Edith, proof 2: one name per term). Where a record writes it "lock N", the cell types the capitalised
# word and cuts the rest of the record's words (its number onward), so every cut is still verbatim.
def pilot_lock(S: Store) -> Cell:
    """What Pilot 1 ran at, beyond Lock 1 (the findings register's timeline)."""
    return cat("Lock", extract(find_cell(S, r"^\| Pilot, first paid call \|", "Public proof"),
                               r"\(lock (1 plus a reviewed real-time fix, [0-9a-f]{7})\)"))


def main_lock(S: Store) -> Cell:
    """What the main run's runner was, beyond Lock 3 (the findings register's timeline)."""
    return cat("Lock", extract(find_cell(S, r"^\| Main run \|", "Public proof"), r"= lock (3 plus reviewed runner code)$"))


def _local_day(day: str, hms: str) -> str:
    """The local date of a UTC day and time: the date LOG.md's entry headers and the decision register's Date column carry. The
    check uses UTC+5:30, the offset git records on the project's commits (e.g. `git log` shows +0530); no pinned record names a time
    zone, so the paper names none (Q26) and says only 'a local calendar date, not a UTC one'. Evidence that they are local dates:
    LOG's 'LOCK CUT: prereg-lock-1' entry is headed 2026-10-12, for the tag at 10-11 19:32:37 UTC (E-16); see also
    `_local_dates_evidence`."""
    return (datetime.strptime(f"{day} {hms}", "%Y-%m-%d %H:%M:%S") + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")


def _local_dates_evidence(S: Store) -> List[Cell]:
    """The records behind TAB-20's note on Deviation 1's date ('our decision records give only its date, with no time or time zone';
    'a local calendar date, not a UTC one'), each kept unprinted in that note. The build stops unless:
    - D-86's register row gives a bare date in its Date column and no clock time or time zone anywhere in the row;
    - the register's dates are not UTC dates: D-82, the go for the bill check s3-ledger-1 (given before that run), is dated a day
      after the run's UTC date in the spend log (TP-2's own example: D-82 dated 2026-10-12 for a run at 19:09-19:18 UTC on 10-11)."""
    date86 = reg_ref(S, "D-86", "Date")
    guard(date86, r"^\d{4}-\d\d-\d\d$", "Deviation 1's ruling is dated with a bare date")
    row86 = cell_ref(S, "register", line_of(S, "register", r"^\| D-86 \|", expect=1))
    if re.search(r"\d\d?:\d\d|\bUTC\b|\bIST\b|\bGMT\b|\d[TZ]\b", str(row86.value)):
        raise ValueError("TAB-20: D-86's register row now gives a time or a time zone: re-word note 2")
    go82 = evidence(reg_ref(S, "D-82", "Decision (plain)"), r"^(The user's go for the S3 bill check `s3-ledger-1`), run BEFORE the lock",
                    "D-82 is the go for s3-ledger-1, given before that run")
    reg82, run82 = text_of(reg_ref(S, "D-82", "Date")), text_of(spend_ref(S, "s3-ledger-1", "Date"))
    if not str(reg82.raw) > str(run82.raw):
        raise ValueError(f"TAB-20: D-82 dated {reg82.raw} is no longer after its run's UTC date {run82.raw}: the register's dates may "
                         f"be UTC dates; re-word note 2")
    why = "the record for 'a local calendar date, not a UTC one'"
    return [kept(text_of(date86), "the record for 'only its date, with no time or time zone'"), go82, kept(reg82, why),
            kept(run82, why)]


# ---------------------------------------------------------------- the chronological rows


class Timeline:
    """Collects rows; prints a date on the first row of each UTC day and checks every other sourced date and the time order.

    `date` and `check` take UTC dates only (the spend log's Date column, git times, the public records' ISO times, E-16's month-day).
    `local` takes local dates (LOG.md's entry headers, the register's Date column): on a row with a time, each must be the local date of
    that UTC day and time; on a row with no time, it must lie between the local dates of the timed rows above and below it. `shown`
    prints a row's own date (a ruling known only by its local date) without starting a day."""

    def __init__(self) -> None:
        self.rows: List[List[Cell]] = []
        self.day: Optional[str] = None
        self.last_time: Optional[str] = None
        self.pending: List[Tuple[str, str]] = []           # local dates of untimed rows, awaiting the next timed row's bound

    @staticmethod
    def _start(t: Cell) -> Optional[str]:
        m = re.search(r"\d\d:\d\d(?::\d\d)?", t.printed)
        if not m:
            return None
        s = m.group(0)
        return s if len(s) == 8 else s + ":00"

    def add(self, date: Optional[Cell], time: Cell, event: Cell, record: Cell, seal: Cell, check: Sequence[Cell] = (),
            local: Sequence[Cell] = (), shown: Optional[Cell] = None) -> None:
        printed = EMPTY
        if date is not None:
            d = str(date.raw if isinstance(date.raw, str) else date.printed)
            if not re.fullmatch(r"\d{4}-\d\d-\d\d", d):
                raise ValueError(f"a row's date must be a full date: {d!r}")
            if d != self.day:
                if self.day is not None and d < self.day:
                    raise ValueError(f"timeline goes back from {self.day} to {d}")
                self.day, self.last_time, printed = d, None, date
        if self.day is None:
            raise ValueError("the first row needs a date")
        for c in check:
            v = str(c.raw)
            if not (v == self.day or (re.fullmatch(r"\d\d-\d\d", v) and self.day.endswith("-" + v))):
                raise ValueError(f"row {event.printed!r}: sourced date {v!r} is not the day it sits under ({self.day})")
        t = self._start(time)
        if t is not None:
            if self.last_time is not None and t < self.last_time:
                raise ValueError(f"row {event.printed!r} at {t} comes before the row above it ({self.last_time})")
            now = _local_day(self.day, t)
            for v, ev in self.pending:
                if v > now:
                    raise ValueError(f"row {ev!r}: local date {v} is after the next timed row's ({now})")
            self.pending = []
            for c in local:
                if str(c.raw) != now:
                    raise ValueError(f"row {event.printed!r}: local date {c.raw!r} is not the local date of {self.day} {t} ({now})")
            self.last_time = t
        else:
            low = _local_day(self.day, self.last_time or "00:00:00")
            for c in local:
                v = str(c.raw)
                if not re.fullmatch(r"\d{4}-\d\d-\d\d", v) or v < low:
                    raise ValueError(f"row {event.printed!r}: local date {v!r} is before the row above it ({low})")
                self.pending.append((v, event.printed))
        if shown is not None:
            if printed is not EMPTY:
                raise ValueError(f"row {event.printed!r} starts a day: it prints that day, not its own date")
            printed = shown
        self.rows.append([printed, time, event, record, seal])

    def done(self) -> List[List[Cell]]:
        end = _local_day(self.day or "", "23:59:59")
        for v, ev in self.pending:
            if v > end:
                raise ValueError(f"row {ev!r}: local date {v} is after the last day ({end})")
        return self.rows


def _main_rows(S: Store) -> List[List[Cell]]:
    T = Timeline()
    WR, NO = "What ran", "Notes"
    hhmm = r"(\d\d:\d\d–\d\d:\d\d) UTC"
    log_lock1 = r"^## \S+ \(\w+\) — LOCK CUT: prereg-lock-1 on "

    # ---- 10-10: the setup smoke runs (smoke-1's one call was rejected and not billed)
    T.add(text_of(spend_ref(S, "smoke-2", "Date")), DASH,
          cat("Setup checks:", text_of(spend_ref(S, "smoke-1", "Run ID")), "(", smoke1_note(S), ") and",
              text_of(spend_ref(S, "smoke-2", "Run ID")), "; the first API calls, before any lock"),
          cat(text_of(spend_ref(S, "smoke-2", "Run ID")), "run commit", spend_cut(S, "smoke-2", WR, r"run from M \(([0-9a-f]{7})\)")), DASH,
          check=[text_of(spend_ref(S, "smoke-1", "Date"))])

    # ---- 10-11: the two setup checks, lock 1 and its proofs, Pilot 1, the effort diagnostic
    # The check's seal names "the D-69 lock tag": that is Lock 1, whose LOG entry is headed "(D-69, D-71)".
    seal78 = r"\*\*Sealed \((D-78) C\): (the answers are not read or graded until) the (D-69) lock tag\.\*\*"
    guard(line(S, "log", log_lock1), r"prereg-lock-1 on [0-9a-f]{7} \(D-69, ", "Lock 1 is D-69's lock tag")
    T.add(text_of(spend_ref(S, "check-ledger-1", "Date")), spend_cut(S, "check-ledger-1", WR, hhmm),
          cat("Setup check", text_of(spend_ref(S, "check-ledger-1", "Run ID")), "(the refusal check on Opus and Sonnet;",
              extract(find_cell(S, r"^\| 20-call check, S3 ", "Public proof"), r"^(before any lock)$"), ")"),
          cat("run commit", spend_cut(S, "check-ledger-1", WR, r"checkout at ([0-9a-f]{7}) with")),
          cat("Sealed:", spend_cut(S, "check-ledger-1", NO, seal78, 2), "Lock 1's tag",
              kept(spend_cut(S, "check-ledger-1", NO, seal78, 1), ID), kept(spend_cut(S, "check-ledger-1", NO, seal78, 3), ID)))
    seal82 = (r"\*\*(Sealed for good) \((D-82)\): (the answers are never read or graded; the items are excluded from every "
              r"analysis)\.\*\*")
    T.add(text_of(spend_ref(S, "s3-ledger-1", "Date")), spend_cut(S, "s3-ledger-1", WR, hhmm),
          cat("Setup check", text_of(spend_ref(S, "s3-ledger-1", "Run ID")), "(the",
              reg_cut(S, "D-82", r"the S3 (bill check) `s3-ledger-1`"), ":",
              reg_cut(S, "D-82", r"run BEFORE the lock: (one Batch of 5 requests) \("), "on Opus and Sonnet; before any lock)"),
          cat("run commit", spend_cut(S, "s3-ledger-1", WR, r"checkout at ([0-9a-f]{7}) with")),
          cat(spend_cut(S, "s3-ledger-1", NO, seal82, 1), ":", spend_cut(S, "s3-ledger-1", NO, seal82, 3),
              kept(spend_cut(S, "s3-ledger-1", NO, seal82, 2), ID)))
    fp1 = line_of(S, "fp_lock4", r"^Tag: prereg-lock-1$", expect=1)
    T.add(None, extract(e16(S, "1", "Tag (UTC)"), r"^\d\d-\d\d (\d\d:\d\d:\d\d)$"),
          cat("Lock 1 cut (tag", extract(cell_ref(S, "fp_lock4", fp1), r"^Tag: (prereg-lock-1)$"), ")"),
          cat("commit", cut(S, "log", log_lock1, r"prereg-lock-1 on ([0-9a-f]{7}) ")), DASH,
          check=[extract(e16(S, "1", "Tag (UTC)"), r"^(\d\d-\d\d) "),
                 cut(S, "lock_manifest", r"^- \*\*Lock-1\.\*\* Tag `prereg-lock-1`", r"\(" + DATE_RX + r" \d\d:\d\d UTC\)")])
    wit1 = r"^- D-71 witnesses posted by the team: public gist "
    T.add(None, cut(S, "log", wit1, r"\(created \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\)"),
          cat("Lock 1 public proof: gist with a Wayback snapshot", rid(S, "D-71")),
          cat("gist", trunc(cut(S, "log", wit1, r"gist\.github\.com/Hrixay/([0-9a-f]{8})[0-9a-f]* \(created")), "; Wayback",
              cut(S, "log", wit1, r"web\.archive\.org/web/(\d{14})/")), DASH,
          check=[cut(S, "log", wit1, r"\(created " + DATE_RX + r"T")])
    z1 = r"^- \*\*Zenodo published \(D-71\):\*\* DOI "
    T.add(None, cut(S, "log", z1, r"DataCite registered \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z"),
          label("Lock 1 public proof: Zenodo v1 registered (DataCite)"),
          cat("DOI", cut(S, "log", z1, r"DOI (10\.5281/zenodo\.\d+) \(")), DASH,
          check=[cut(S, "log", z1, r"DataCite registered " + DATE_RX + r"T")])
    pilot_first = find_cell(S, r"^\| Pilot, first paid call \|", "Time")
    unopened = line(S, "findings", r"^- Haiku-medium's pilot medians were 0% at every preset\. ")
    # TP-10: the spend log says the pick was committed "before any Opus or Sonnet number was opened", but Opus and Sonnet counts,
    # tokens and costs were seen (the Deviation 1 row). The printed words are "answer or score": that is what stayed unopened, as the
    # findings register's line (cut in this same cell, printed: "answers and scores stayed sealed until after Lock 2") records; the build
    # stops if it no longer does. The spend log's own words stay in the cell's record, unprinted.
    pick1 = (r"Preset pick \(D-36\(4\), (Haiku only, committed [0-9a-f]{7}) (before any Opus or Sonnet number was opened)\): (none), "
             r"every preset below [\d.]+, returned to the user\.")
    guard(reg_ref(S, "D-86", "Decision (plain)"), r"^Ruling under D-36\(4\) tier 3 \(pilot-ledger-1 returned to the user: ",
          "Deviation 1 (D-86) was the ruling on Pilot 1's empty preset pick")
    T.add(text_of(spend_ref(S, "pilot-ledger-1", "Date")),
          cat(spend_cut(S, "pilot-ledger-1", WR, hhmm), "; first paid call", extract(pilot_first, r"^\d\d-\d\d (\d\d:\d\d)$")),
          cat("Pilot 1 (", text_of(spend_ref(S, "pilot-ledger-1", "Run ID")), ") under Lock 1"),
          cat("run commit", spend_cut(S, "pilot-ledger-1", WR, r"checkout at ([0-9a-f]{7}) with"), "(", pilot_lock(S), ")"),
          cat("Preset pick (", spend_cut(S, "pilot-ledger-1", NO, pick1, 1), "before any Opus or Sonnet answer or score was opened",
              kept(spend_cut(S, "pilot-ledger-1", NO, pick1, 2), "the spend log's wording, 'number', is not printed: counts, tokens and "
                   "costs were seen (TP-10)"),
              "):", spend_cut(S, "pilot-ledger-1", NO, pick1, 3), "(",
              "Haiku-medium's pilot medians were",
              # the findings register writes the median "0%": a measured value prints with its decimal (Edith, proof 4, p. 33: "0.0%")
              cat(extract(unopened, r"^- Haiku-medium's pilot medians were (\d+)% at every preset\. ", dp=1), "% at every preset", sep=""),
              "; this led to Deviation 1). Opus and Sonnet",
              extract(unopened, r"Opus and Sonnet pilot \*(answers and scores)\* stayed unopened"),
              "stayed sealed until after Lock 2; then Pilot 1's Opus and Sonnet results were opened as exploratory",
              # the log's own name for the run, "pilot-1", is a third name (the run is Pilot 1, pilot-ledger-1): our words replace it
              kept(cut(S, "log", r"^- Since lock 2: ladder-l14n-1 ran ", r"; (pilot-1 opened as exploratory) \("),
                   "the log's own words, with 'pilot-1', which our printed 'Pilot 1's Opus and Sonnet results' replaces (one name per run)")),
          check=[extract(pilot_first, r"^(\d\d-\d\d) ")])
    diag_t = find_cell(S, r"^\| Effort diagnostic \(", "Time")
    T.add(text_of(spend_ref(S, "diag-haiku-effort-1", "Date")),
          cat(spend_cut(S, "diag-haiku-effort-1", WR, hhmm), "; paid calls", extract(diag_t, r"^\d\d-\d\d (\d\d:\d\d–\d\d:\d\d) \(paid calls\)$")),
          cat("Effort diagnostic (", text_of(spend_ref(S, "diag-haiku-effort-1", "Run ID")), "),",
              text_of(find_cell(S, r"^\| Effort diagnostic \(", "Public proof"))),
          cat("run commit", spend_cut(S, "diag-haiku-effort-1", WR, r"checkout at ([0-9a-f]{7}) with")), DASH,
          check=[extract(diag_t, r"^(\d\d-\d\d) ")])

    # ---- Deviation 1: ruled between the effort diagnostic and the 10-12 puzzle-set commit; known only by its local date (the
    # register's Date column; the spec's Deviation 1 heading carries the same date, and both are checked)
    dev1 = cell_ref(S, "spec1", line_of(S, "spec1", r"^### Deviation 1 \(", expect=1))
    T.add(None, DASH,
          label("Deviation 1 ruled: shorter puzzles, the length to be picked by a Haiku-only rule on the length sweep"),
          cat("spec heading", extract(dev1, r"^### (Deviation 1) \("), rid(S, "D-86")),
          cat("At the time of the ruling,", extract(unopened, r"(Opus and Sonnet pilot) \*answers"),
              extract(unopened, r"pilot \*(answers and scores)\* stayed"),
              extract(unopened, r"\* (stayed unopened; their counts, tokens and costs were seen, for pricing)\.$")),
          local=[text_of(reg_ref(S, "D-86", "Date")), extract(dev1, r"^### Deviation 1 \(" + DATE_RX + r"\)$")],
          shown=cat(text_of(reg_ref(S, "D-86", "Date")), "(local date of the ruling)"))

    # ---- 10-12: the puzzle sets, lock 2, the length sweep, Deviation 2 and Amendment 1, lock 3, the main run, the analysis stamp
    sets = r"^   - \*\*Commit:\*\* [0-9a-f]{40}, author and committer "
    cite = r"^   - \*\*What the paper should cite:\*\* a git commit time is self-reported\. "
    T.add(cut(S, "settle_g4", r"^1\. \*\*Study 1b sets committed at ", r"on " + DATE_RX + r" \d\d:\d\dZ"),
          cut(S, "settle_g4", sets, r"author and committer \*\*(\d\d:\d\d:\d\d)Z\*\*"),
          label("Puzzle sets frozen at every candidate length for Lock 2, among them Study 1b's later test sets (unused by Study 1)"),
          cat("commit", cut(S, "settle_g4", sets, r"\*\*Commit:\*\* ([0-9a-f]{7})[0-9a-f]{33},"), "(",
              cut(S, "settle_g4", cite, r"(a git commit time is self-reported)\."), "); public proof:",
              "Lock", cut(S, "settle_g4", cite, r"is \*\*lock (2's Zenodo)$"), cut(S, "settle_g4", cite, r"^(record) \(", offset=1), "(",
              cut(S, "settle_g4", cite, r"^record \((\d\d:\d\d:\d\d)Z\)\*\*", offset=1), "),",
              cut(S, "settle_g4", cite, r"(before any Haiku-max API answer existed):", offset=1)),
          cat("Checked before Lock 4:", cut(S, "lock_manifest", r"^  - `data/plans/study1b-never-sent-lock4\.json`",
                                           r"\(verdict: (all three sets never sent and in no other file);"),
              "(the check", cut(S, "settle_g4", r"^\(`research/study1b-spec\.md` line \d+\)\. The never-sent file covers only",
                                r"The never-sent file (covers only API logs and repo files)\."),
              "); but see the exposure-scan row and the sensitivity panel"))
    T.add(None, extract(e16(S, "2", "Tag (UTC)"), r"^\d\d-\d\d (\d\d:\d\d:\d\d)$"),
          cat("Lock 2 cut (tag", extract(cell_ref(S, "fp_lock4", line_of(S, "fp_lock4", r"^Tag: prereg-lock-2$", expect=1)),
                                         r"^Tag: (prereg-lock-2)$"), ")"),
          cat("commit", cut(S, "log", r"^## \S+ \(\w+\) — LOCK 2 CUT and posted: ", r"prereg-lock-2 on ([0-9a-f]{7}) ")), DASH,
          check=[extract(e16(S, "2", "Tag (UTC)"), r"^(\d\d-\d\d) ")])
    z2 = r"^- Zenodo new version: DOI "
    T.add(None, cut(S, "log", z2, r"DataCite registered \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z"),
          cat("Lock 2 public proof: Zenodo v2 registered (DataCite) only (",
              cut(S, "settle_g4", r"Lock 2 has no gist or Wayback", r"Lock 2 has (no gist or Wayback)"), ")"),
          cat("DOI", cut(S, "log", z2, r"DOI (10\.5281/zenodo\.\d+) \(")), DASH,
          check=[cut(S, "log", z2, r"DataCite registered " + DATE_RX + r"T")])
    pick = find_cell(S, r"^\| Ladder; N pick committed \|", "Time")
    T.add(text_of(spend_ref(S, "ladder-l14n-1", "Date")),
          cat(spend_cut(S, "ladder-l14n-1", WR, hhmm), "; first call",
              cut(S, "settle_g4", r"The first `send` was at", r"first `send` was at \*\*(\d\d:\d\d:\d\d)\.\d+Z\*\*")),
          cat("Length sweep (", text_of(spend_ref(S, "ladder-l14n-1", "Run ID")), ") under",
              spend_cut(S, "ladder-l14n-1", WR, r"\(D-86 to D-89, under (prereg-lock-2)\)")),
          cat("run commit", spend_cut(S, "ladder-l14n-1", WR, r"checkout at ([0-9a-f]{7}) \(the prereg-lock-2 tag\)")),
          # the spend log says "ladder answer": its name for the length sweep (Edith, proof 3: one name per term); the record stays, unprinted
          cat("Haiku-only pick of the length committed at", extract(pick, r"; (\d\d:\d\d:\d\d)$"), ",",
              "before any Opus or Sonnet length-sweep answer was opened",
              kept(spend_cut(S, "ladder-l14n-1", NO, r"committed (before any Opus or Sonnet ladder answer was opened)"),
                   "the spend log's own words, 'ladder answer', which our printed 'length-sweep answer' replaces (one name per term)")))
    dev2 = cell_ref(S, "spec1", line_of(S, "spec1", r"^### Deviation 2 \(", expect=1))
    am1 = cell_ref(S, "spec1", line_of(S, "spec1", r"^### Amendment 1 \(", expect=1))
    T.add(None, DASH,
          label("Deviation 2 ruled (identical repeated step lines accepted, for every model); Amendment 1 written (only the values "
                "the pre-set rules chose after the length sweep)"),
          cat("spec headings", extract(dev2, r"^### (Deviation 2) \("), "and", extract(am1, r"^### (Amendment 1) \("), rid(S, "D-90")),
          cat("Ruled", reg_cut(S, "D-90", r"\*\*Declared Deviation 2 \(marking rule\), (before any main-run data):\*\*")),
          local=[text_of(reg_ref(S, "D-90", "Date")), extract(dev2, r"^### Deviation 2 \(" + DATE_RX + r"\)"),
                 extract(am1, r"^### Amendment 1 \(" + DATE_RX + r"\)")])
    T.add(None, extract(e16(S, "3", "Tag (UTC)"), r"^\d\d-\d\d (\d\d:\d\d:\d\d)$"),
          cat("Lock 3 cut (tag", extract(cell_ref(S, "fp_lock4", line_of(S, "fp_lock4", r"^Tag: prereg-lock-3$", expect=1)),
                                         r"^Tag: (prereg-lock-3)$"), "): Amendment 1 and Deviation 2"),
          cat("commit", cut(S, "log", r"^## \S+ \(\w+\) — LOCK 3 CUT: ", r"prereg-lock-3 on ([0-9a-f]{7}) ")), DASH,
          check=[extract(e16(S, "3", "Tag (UTC)"), r"^(\d\d-\d\d) ")])
    w3 = r"^## \S+ \(\w+\) — lock-3 public witness: gist \+ Wayback"
    T.add(None, cut(S, "log", w3, r"\(created \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\)", offset=2),
          cat("Lock 3 public proof: gist with a Wayback snapshot;",
              cut(S, "log", r"^Lock 3's record, with .* wording \(first public as the gist", r"; (Zenodo was unavailable);")),
          cat("gist", trunc(cut(S, "log", w3, r"gist\.github\.com/Hrixay/([0-9a-f]{8})[0-9a-f]* \(created", offset=2)), "; Wayback",
              cut(S, "log", w3, r"web\.archive\.org/web/(\d{14})/", offset=2)), DASH,
          check=[cut(S, "log", w3, r"\(created " + DATE_RX + r"T", offset=2)])
    main = "main-l14n6-1"
    # TP-9: like every other run row, the span starts at the run's invocation; the first send follows it.
    main_inv = r"INVOCATION \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z; one invocation"
    T.add(text_of(spend_ref(S, main, "Date")),
          cat(span(spend_cut(S, main, WR, main_inv), spend_cut(S, main, WR, r"last commit (\d\d:\d\d:\d\d)Z")), "; first call",
              spend_cut(S, main, WR, r"First send (\d\d:\d\d:\d\d)Z")),
          cat("Main run (", text_of(spend_ref(S, main, "Run ID")), ") under", spend_cut(S, main, WR, r"\(D-92, D-94; (prereg-lock-3)\)"),
              "; ruled before the run:", reg_cut(S, "D-94", r"\(3\) \*\*(the run may start before Zenodo v3 is published)\*\*"),
              rid(S, "D-94"),
              evidence(reg_ref(S, "D-94", "Decision (plain)"), r"^(The user's rulings before the main run) main-l14n6-1 ",
                       "D-94's rulings came before the main run")),
          cat("run commit", spend_cut(S, main, WR, r"checkout at ([0-9a-f]{7}) \("), "(", main_lock(S), ")"),
          cat("Sealed:", spend_cut(S, main, NO, r"\*\*Sealed:\*\* (no answer, score or accuracy opened) \(clearance addendum\); "), ";",
              spend_cut(S, main, NO, r"\*\*Sealed:\*\* [^(]+\(clearance addendum\); ([^.]+)\.")),
          check=[spend_cut(S, main, WR, r"INVOCATION (\d{4}-\d\d-\d\d)T\d\d:\d\d:\d\dZ; one invocation")])
    c4 = r"^   - \*\*Commit:\*\* C4 \("
    c4f = r"^- Addendum C, which also rewords item 7"
    # TP-6: C4 is Addendum C's last part, so "Addendum C, C4 included" (one addendum, not two), and "we" (Q24). The record's "neither
    # was ruled on by name" covers Addendum C as committed before launch and C4 after it; the acceptance date is the findings
    # register's, checked equal to the register's date for that ruling.
    acc_date = cut(S, "findings", c4f, r"\*\*The user accepted Addendum C, C4 included, on " + DATE_RX + r" \(D-134 \(3\)\)")
    d134 = text_of(reg_ref(S, "D-134", "Date"))
    if d134.raw != acc_date.raw:
        raise ValueError(f"TAB-20: Addendum C's acceptance is dated {acc_date.raw} in the findings register, {d134.raw} in the register")
    T.add(None, cut(S, "settle_g4", c4, r" at (\d\d:\d\d:\d\d)Z\*\*\.$"),
          cat("Addendum C4 (", cut(S, "findings", c4f, r"Addendum C4 \((four edge-case pins)\)"),
              "to the reporting definitions) committed", cut(S, "findings", c4f, r"committed (about \d+ minutes) \*\*after\*\* launch"),
              "after launch; Addendum C, C4 included, was not ruled on by name at the time",
              evidence(line(S, "findings", c4f), r"\*\*(neither was ruled on by name)\*\* at the time\.",
                       "Addendum C and its C4 were not ruled on by name at the time"),
              "; we accepted it on", acc_date, rid(S, "D-134"),
              evidence(reg_ref(S, "D-134", "Decision (plain)"), r"\(3\) \*\*(Addendum C accepted)\*\*", "the ruling accepted Addendum C"),
              kept(d134, "the register's date of that ruling, checked equal to the printed date")),
          cat("commit", cut(S, "settle_g4", c4, r"entered in \*\*([0-9a-f]{7}) at ")),
          cat("Addendum C4", cut(S, "findings", r"^- All of it came before any result was opened and is inside the stamp\.$",
                        r"^- All of it (came before any result was opened and is inside the stamp)\.$")))
    z3 = r"^## \S+ \(\w+\) — Zenodo v3 PUBLISHED: DOI "
    T.add(None, cut(S, "log", z3, r"\(DataCite \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\)$"),
          cat("Lock 3 public proof: Zenodo v3 registered (DataCite);",
              extract(find_cell(S, r"^\| Zenodo v3 \(", "Public proof"), r"^(deposited during the run, as the record says) \(D-94\(3\)\)$")),
          cat("DOI", cut(S, "log", z3, r"DOI (10\.5281/zenodo\.\d+) \(")), DASH,
          check=[cut(S, "log", z3, r"\(DataCite " + DATE_RX + r"T")])
    st = r"^## \S+ \(\w+\) — ANALYSIS STAMP posted \(D-93\): "
    T.add(None, cut(S, "log", st, r"\(created \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\)", offset=2),
          cat("Analysis stamp for Study 1:", rid(S, "D-93"), "driver", cut(S, "log", st, r"driver ([0-9a-f]{7}) \+"),
              "and reporting definitions", cut(S, "log", st, r"definitions ([0-9a-f]{7}) \+"), "with the main run's raw-file fingerprints"),
          cat("gist", trunc(cut(S, "log", st, r"gist\.github\.com/Hrixay/([0-9a-f]{8})[0-9a-f]* \(created", offset=2)), "; Wayback",
              cut(S, "log", st, r"web\.archive\.org/web/(\d{14})/", offset=2)),
          cat("No main-run result has been opened",
              kept(cut(S, "log", st, r"(No main-study result has been opened)\.", offset=2),
                   "the log's own words, with 'main-study', which our printed 'main-run' replaces (one name per term)")),
          check=[cut(S, "log", st, r"\(created " + DATE_RX + r"T", offset=2)])
    drv = r"^## \S+ \(\w+\) — the stamped driver RAN ONCE on main-l14n6-1 "
    ver = r"^## \S+ \(\w+\) — Driver's one run VERIFIED: "
    kj = find_cell(S, r"^\| k\.json committed; driver run \|", "Time")
    T.add(None, cut(S, "log", drv, r"exit 0, (\d\d:\d\d:\d\d–\d\d:\d\d:\d\d)Z;"),
          cat("k fixed from costs only, before any score was seen (k.json committed at", extract(kj, r"^(\d\d:\d\d:\d\d); "),
              "); then the stamped driver's", cut(S, "log", ver, r"Driver's (one run) VERIFIED")),
          cat("driver at", cut(S, "log", drv, r"checkout at ([0-9a-f]{7})[0-9a-f]* \(the stamped commit", offset=2), "; output SHA-256",
              trunc(cut(S, "log", drv, r"analysis\.json SHA-256 ([0-9a-f]{8})[0-9a-f]{56}$"))),
          cat(cut(S, "log", ver, r"(Results may now be read)$"), ", after a", cut(S, "log", ver, r"analysis\.json (byte-identical) \("),
              "re-run"),
          local=[cut(S, "log", drv, r"^## " + DATE_RX + " "), cut(S, "log", ver, r"^## " + DATE_RX + " ")])

    # ---- 10-13: the exposure scan, lock 4 and its proofs and lineage, Study 1b, the top-up, their stamps and driver runs
    scan = r"^  as frozen; the sensitivity without them is pre-registered in the spec and the driver\. The final pre-tag exposure scan "
    T.add(cut(S, "lock_manifest", scan, r"exposure scan \(\w+, " + DATE_RX + r"T"),
          cut(S, "lock_manifest", scan, r"exposure scan \(\w+, \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z,"),
          cat("Final exposure scan before Lock 4:", cut(S, "lock_manifest", scan, r"; (no new exposure)\.$"), ";",
              reg_cut(S, "D-97", r"^\*\*(Study 1b's three partly displayed test puzzles) are kept\.\*\*"), rid(S, "D-97"), "had",
              reg_cut(S, "D-97", r"had (parts of their answers shown inside Claude Code) helper and review sessions"),
              "during our own work sessions",
              evidence(line(S, "settle_g3", r"^\s*- They were shown in helper, build and review sessions, never to a model under test\.$"),
                       r"shown in (helper, build and review sessions), never", "the puzzles were shown in our own work sessions "
                       "(helper, build and review sessions)"),
              "; kept, disclosed, and given a pre-registered sensitivity without them (sensitivity panel)"),
          cat("scan file SHA-256", trunc(cut(S, "lock_manifest", scan, r"-final\.json` \(([0-9a-f]{8})[0-9a-f]{56}\)"))),
          cat("Those puzzles:", reg_cut(S, "D-97", r"; (they were never shown to a model under test, and nothing was tuned on them)\.")),
          local=[text_of(reg_ref(S, "D-97", "Date"))])
    l4 = r"^## \S+ \(\w+\) — LOCK 4 PUBLIC: prereg-lock-4 = "
    T.add(None, extract(e16(S, "4", "Tag (UTC)"), r"^\d\d-\d\d (\d\d:\d\d:\d\d)$"),
          cat("Lock 4 cut (tag", extract(cell_ref(S, "fp_lock4", line_of(S, "fp_lock4", r"^Tag: prereg-lock-4$", expect=1)),
                                         r"^Tag: (prereg-lock-4)$"), "): Study 1b and the top-up run, before either sent a call"),
          cat("commit", cut(S, "log", l4, r"prereg-lock-4 = ([0-9a-f]{7})[0-9a-f]{33} ")), DASH,
          check=[extract(e16(S, "4", "Tag (UTC)"), r"^(\d\d-\d\d) ")], local=[cut(S, "log", l4, r"^## " + DATE_RX + " ")])
    T.add(None, cut(S, "log", l4, r"\(\d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\) and Wayback"),
          label("Lock 4 public proof: gist with a Wayback snapshot"),
          cat("gist", trunc(cut(S, "log", l4, r"gist\.github\.com/Hrixay/([0-9a-f]{8})[0-9a-f]* \(")), "; Wayback",
              cut(S, "log", l4, r"and Wayback (\d{14});")), DASH,
          check=[cut(S, "log", l4, r"\(" + DATE_RX + r"T\d\d:\d\d:\d\dZ\) and Wayback")])
    merge = r"^     - \*\*[0-9a-f]{7}\*\* \(main's record merge, "
    corr = r"^## \S+ \(\w+\) — Correction: merging the lock-4 tag commit into main "
    T.add(None, cut(S, "settle_g4", merge, r", \*\*(\d\d:\d\d:\d\d)Z\*\*, after the gist"),
          cat("Record merge of the tag into main: it made", cut(S, "log", corr, r"made (a second child of the tag)\."), "; ruled a",
              "disclosed", kept(cut(S, "log", corr, r"ruled it a (declared) clarification:"), "our log's own word for this clarification, "
                                "which our printed 'disclosed' replaces (D-161)"),
              "clarification"),
          cat("commit", cut(S, "settle_g4", merge, r"^- \*\*([0-9a-f]{7})\*\* \(")),
          cut(S, "log", corr, r"and (2080573 is disclosed as a record merge with no run code)\."),
          local=[cut(S, "log", corr, r"^## " + DATE_RX + " ")])
    price = r"^     - \*\*[0-9a-f]{7}\*\* \(price-date commit, "
    launch1b = r"^## \S+ \(\w+\) — STUDY 1b LAUNCHED: "
    # Q27 (Edith's wording, as C-173): the commit changed only the date, the docstring's re-check note and the test's expected date;
    # no price changed. Its records: Edith's diff of the tag and the commit (only the price file and its test, three lines each way),
    # her lock-4 audit (the commit may also touch the re-check docstring line), and Karen's re-check (prices unchanged), which the
    # build checks came before the commit.
    recheck = r"^## \S+ \(Karen\) — Price re-check \d\d:\d\d UTC: UNCHANGED "
    t_recheck = cut(S, "log", recheck, r"Price re-check (\d\d:\d\d) UTC: UNCHANGED")
    t_price = cut(S, "settle_g4", price, r", \*\*(\d\d:\d\d:\d\d)Z\*\*\)\.")
    if not str(t_recheck.raw) + ":00" < str(t_price.raw):
        raise ValueError(f"TAB-20: the price re-check ({t_recheck.raw}) no longer comes before the price-date commit ({t_price.raw})")
    T.add(None, cut(S, "settle_g4", price, r", \*\*(\d\d:\d\d:\d\d)Z\*\*\)\."),
          cat("Price-date commit, the tag's", cut(S, "log", launch1b, r"\(the tag's (only first-parent child)\)"),
              "; it changed only the price table's date (with its re-check note and the test that checks it); no price changed",
              evidence(line(S, "settle_g4", price, offset=1),
                       r"^(`harness/pareto/prices\.py` and `harness/tests/test_prices\.py` \(3\+/3−\))\.$",
                       "the commit changed only the price file and its test, three lines"),
              evidence(line(S, "log", r"^## \S+ \(Edith\) — Karen's lock-4 spec diff \(\w+\) checked by program: "),
                       r"(the price-date commit may also touch the re-check docstring line)",
                       "the price-date commit may also touch the re-check docstring line"),
              evidence(line(S, "log", recheck), r"(UNCHANGED \(all four models = the locked table;)",
                       "the prices were re-checked unchanged before the commit"),
              kept(t_recheck, "the re-check's time, checked to come before the commit's")),
          cat("commit", cut(S, "settle_g4", price, r"^- \*\*([0-9a-f]{7})\*\* \(")), DASH,
          local=[cut(S, "log", recheck, r"^## " + DATE_RX + " ")])
    z4 = r"^## \S+ \(\w+\) — Zenodo v4 PUBLISHED: DOI "
    T.add(None, cut(S, "log", z4, r"\(record created \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\)"),
          label("Lock 4 public proof: Zenodo v4 record created"),
          cat("DOI", cut(S, "log", z4, r"DOI (10\.5281/zenodo\.\d+) \(record created")), DASH,
          check=[cut(S, "log", z4, r"\(record created " + DATE_RX + r"T")])
    s1b = "study1b-1"
    T.add(None, span(spend_cut(S, s1b, WR, r"INVOCATIONs (\d\d:\d\d:\d\d)Z,"), spend_cut(S, s1b, WR, r"Last commit (\d\d:\d\d:\d\d)Z\.")),
          cat("Study 1b (", text_of(spend_ref(S, s1b, "Run ID")), ") under", spend_cut(S, s1b, WR, r"\(D-96; (prereg-lock-4)\)")),
          cat("run commit", spend_cut(S, s1b, WR, r"price-date commit ([0-9a-f]{7})[0-9a-f]* \(")),
          cat("Sealed:", spend_cut(S, s1b, NO, r"\*\*Sealed:\*\* ([^.]+)\.")),
          check=[text_of(spend_ref(S, s1b, "Date"))])
    # Study 1b's k, fixed from costs only after the run and before the data stamp; its LOG entry gives a date only.
    k1b = r"^## \S+ \(\w+\) — Study 1b's k FIXED from costs only: k = "
    T.add(None, DASH,
          cat(cut(S, "log", k1b, r"— (Study 1b's k) FIXED"), "fixed", cut(S, "log", k1b, r" FIXED (from costs only): "), "(",
              cut(S, "log", k1b, r": (k = \d+) \("), ")"),
          cat("commit", text_of(S.ref("s1b_k", "@commit")), "; k.json SHA-256",
              trunc(cut(S, "log", k1b, r"k\.json SHA-256 ([0-9a-f]{8})[0-9a-f]{56}$"))),
          cut(S, "log", k1b, r"\. (No answer or score opened)\. ", offset=2),
          local=[cut(S, "log", k1b, r"^## " + DATE_RX + " ")])
    g1b =r"^- \*\*The gist\*\* https://gist\.github\.com/Hrixay/[0-9a-f]+: public, created "
    T.add(None, cut(S, "clr_1b", g1b, r"created \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z,"),
          cat("Study 1b data stamp: run-file and k.json fingerprints", rid(S, "D-109")),
          cat("gist", trunc(cut(S, "clr_1b", g1b, r"gist\.github\.com/Hrixay/([0-9a-f]{8})[0-9a-f]*:")), "; Wayback",
              cut(S, "clr_1b", r"^- \*\*Wayback\*\* snapshot \d{14} contains the calls\.jsonl hash, the k\.json hash", r"snapshot (\d{14}) ")),
          reg_cut(S, "D-109", r"(It holds no data and no results)\."),
          check=[cut(S, "clr_1b", g1b, r"created " + DATE_RX + r"T")])
    d1b = r"^## \S+ \(\w+\) — the Study 1b driver RAN ONCE after the D-109 data stamp: "
    re1b = r"^- \*\*My re-run:\*\* a fresh clean detached worktree at [0-9a-f]+, the same command \(`--run`"
    T.add(None, cut(S, "log", d1b, r"exit 0, (\d\d:\d\d:\d\d–\d\d:\d\d:\d\d)Z;"),
          cat("Study 1b", cut(S, "clr_1b", r"^## The analysis: driver run once, ", r"^## The analysis: (driver run once),"),
              "at the Lock 4 commit"),
          cat("driver at", cut(S, "log", d1b, r"the prereg-lock-4 commit ([0-9a-f]{7})[0-9a-f]*,", offset=2), "; output SHA-256",
              trunc(cut(S, "log", d1b, r"analysis\.json SHA-256 ([0-9a-f]{8})[0-9a-f]{56}$"))),
          cat(cut(S, "log", r"^## \S+ \(\w+\) — Study 1b analysis reproduced byte-identically", r"(The results may now be read)\."),
              ", after a byte-identical re-run (", cut(S, "clr_1b", re1b, r", (\d\d:\d\d:\d\d–\d\d:\d\d:\d\d)Z, exit 0\."), ")"),
          local=[cut(S, "log", d1b, r"^## " + DATE_RX + " ")])
    tu = "topup-1"
    guard(spend_ref(S, tu, WR), r"\(paused \d\d:\d\d:\d\dZ .*, with w1 in flight;", "the top-up's first round was in flight at the pause")
    T.add(None, span(spend_cut(S, tu, WR, r"INVOCATIONs (\d\d:\d\d:\d\d)Z and"), spend_cut(S, tu, WR, r"\d\d:\d\d-(\d\d:\d\d:\d\d)Z, EXIT 0")),
          cat("Top-up run (", text_of(spend_ref(S, tu, "Run ID")), ") under", spend_cut(S, tu, WR, TU_LOCK, 1), TU_CHANGE,
              kept(spend_cut(S, tu, WR, TU_LOCK, 2), ID), "; paused",
              spend_cut(S, tu, WR, r"\(paused (\d\d:\d\d:\d\d)Z"), "with its first batch of requests in flight, resumed",
              spend_cut(S, tu, WR, r"and (\d\d:\d\d:\d\d)Z \(paused"), "; every call", topup_once(S)),
          cat("run commit", spend_cut(S, tu, WR, r"checkout at ([0-9a-f]{7}) \(")),
          cat("Sealed:", spend_cut(S, tu, NO, r"\*\*Sealed:\*\* ([^.]+)\.")),
          check=[text_of(spend_ref(S, tu, "Date"))])
    gtu = r"^- \*\*The gist\*\* https://gist\.github\.com/Hrixay/[0-9a-f]+: public, created "
    T.add(None, cut(S, "clr_topup", gtu, r"created \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z,"),
          cat("Top-up data stamp: run-file fingerprints", rid(S, "D-113")),
          cat("gist", trunc(cut(S, "clr_topup", gtu, r"gist\.github\.com/Hrixay/([0-9a-f]{8})[0-9a-f]*:")), "; Wayback",
              cut(S, "clr_topup", r"^- \*\*Wayback\*\* snapshot \d{14} contains the calls\.jsonl hash [0-9a-f]+…, the topup_plan",
                  r"snapshot (\d{14}) ")),
          cat("It holds", reg_cut(S, "D-113", r"with (no data and no results)")),
          check=[cut(S, "clr_topup", gtu, r"created " + DATE_RX + r"T")])
    dtu = r"^## \S+ \(\w+\) — the top-up driver RAN ONCE after the D-113 data stamp: "
    retu = r"^- \*\*My re-run:\*\* a fresh clean detached worktree at [0-9a-f]+, the same interpreter and the same command"
    T.add(None, cut(S, "log", dtu, r"exit 0, (\d\d:\d\d:\d\d–\d\d:\d\d:\d\d)Z;"),
          cat("Top-up", cut(S, "clr_topup", r"^## The top-up analysis: driver run once, ", r"^## The top-up analysis: (driver run once),"),
              "at the Lock 4 commit"),
          cat("driver at", cut(S, "log", dtu, r"the prereg-lock-4 commit ([0-9a-f]{7})[0-9a-f]* \(", offset=2), "; output SHA-256",
              trunc(cut(S, "log", dtu, r"analysis\.json SHA-256 ([0-9a-f]{8})[0-9a-f]{56}$"))),
          cat(cut(S, "clr_topup", r"^  \*\*The top-up results may now be read\.\*\*", r"\*\*(The top-up results may now be read)\.\*\*"),
              ", after a byte-identical re-run (", cut(S, "clr_topup", retu, r", (\d\d:\d\d:\d\d–\d\d:\d\d:\d\d)Z, exit 0\."), ")"),
          local=[cut(S, "log", dtu, r"^## " + DATE_RX + " ")])
    return T.done()


# ---------------------------------------------------------------- panel 1: the lock-proof column (E-16)


def _lock_panel(S: Store) -> Table:
    # one form for every timestamp of the panel: month-day and time, UTC (md_time), as the tag cut column prints it
    cols = ["Lock", "Tag", "Commit", "Tar SHA-256", "Tag cut (UTC, month-day)", "Gist created (UTC, month-day)", "Wayback snapshot",
            "Zenodo DOI", "Zenodo time (UTC, month-day)", "Next paid data (UTC)"]
    rows: List[List[Cell]] = []

    def fp(lock: str) -> Tuple[Cell, Cell, Cell]:
        n = line_of(S, "fp_lock4", rf"^Tag: prereg-lock-{lock}$", expect=1)
        tag = extract(cell_ref(S, "fp_lock4", n), r"^Tag: (prereg-lock-\d)$")
        commit = extract(cell_ref(S, "fp_lock4", n + 1), r"^Git commit ID \(SHA-1\): ([0-9a-f]{40})$")
        tar = extract(cell_ref(S, "fp_lock4", n + 2),
                      rf"^SHA-256 of `git -c tar\.umask=0002 archive --format=tar prereg-lock-{lock}` \(uncompressed\): ([0-9a-f]{{64}})$")
        return tag, commit, tar

    def nxt(lock: str, rx: str) -> Cell:
        return extract(e16(S, lock, "Next paid data"), rx)

    wit1 = r"^- D-71 witnesses posted by the team: public gist "
    z1 = r"^- \*\*Zenodo published \(D-71\):\*\* DOI "
    rows.append([label("Lock 1"), *fp("1"), text_of(e16(S, "1", "Tag (UTC)")),
                 md_time(S, "log", wit1, r"\(created STAMP\)"), cut(S, "log", wit1, r"web\.archive\.org/web/(\d{14})/"),
                 cut(S, "log", z1, r"DOI (10\.5281/zenodo\.\d+) \("),
                 cat(md_time(S, "log", z1, r"DataCite registered STAMP"), "(DataCite)"),
                 nxt("1", r"^(Pilot 1 first call \d\d:\d\d)$")])
    z2 = r"^- Zenodo new version: DOI "
    rows.append([label("Lock 2"), *fp("2"), text_of(e16(S, "2", "Tag (UTC)")),
                 cut(S, "settle_g4", r"Lock 2 has no gist or Wayback", r"Lock 2 has (no gist or Wayback)"), DASH,
                 cut(S, "log", z2, r"DOI (10\.5281/zenodo\.\d+) \("),
                 cat(md_time(S, "log", z2, r"DataCite registered STAMP"), "(DataCite)"),
                 nxt("2", r"^(length sweep \d\d:\d\d:\d\d)$")])
    w3 = r"^## \S+ \(\w+\) — lock-3 public witness: gist \+ Wayback"
    z3 = r"^## \S+ \(\w+\) — Zenodo v3 PUBLISHED: DOI "
    rows.append([label("Lock 3"), *fp("3"), text_of(e16(S, "3", "Tag (UTC)")),
                 md_time(S, "log", w3, r"\(created STAMP\)", offset=2),
                 cut(S, "log", w3, r"web\.archive\.org/web/(\d{14})/", offset=2),
                 cut(S, "log", z3, r"DOI (10\.5281/zenodo\.\d+) \("),
                 cat(md_time(S, "log", z3, r"\(DataCite STAMP\)$"), "(DataCite; during the main run)"),
                 nxt("3", r"^(main run \d\d:\d\d:\d\d–\d\d:\d\d:\d\d), so v3 came ")])
    l4 = r"^## \S+ \(\w+\) — LOCK 4 PUBLIC: prereg-lock-4 = "
    z4 = r"^## \S+ \(\w+\) — Zenodo v4 PUBLISHED: DOI "
    rows.append([label("Lock 4"), *fp("4"), text_of(e16(S, "4", "Tag (UTC)")),
                 md_time(S, "log", l4, r"\(STAMP\) and Wayback"), cut(S, "log", l4, r"and Wayback (\d{14});"),
                 cut(S, "log", z4, r"DOI (10\.5281/zenodo\.\d+) \(record created"),
                 cat(md_time(S, "log", z4, r"\(record created STAMP\)"), "(record created)"),
                 # The record's capitals ("first INVOCATION", the spend log's style) print in lower case; the regex keeps the
                 # typed word honest (verifier, PR 27 round 1).
                 cat(nxt("4", r"^(Study 1b first) INVOCATION \d\d:\d\d:\d\d$"), "invocation",
                     nxt("4", r"^Study 1b first INVOCATION (\d\d:\d\d:\d\d)$"))])
    # Eight footnotesize points: with no word broken inside a cell (the writer's rule since proof 2), the DOI, the Wayback id and the
    # 8-character hash chunks need more than 9 in at \small (overfull by 0.04 in).
    return Table([label(c) for c in cols], rows, layout="landscape", mono=[2, 3], font="footnotesize")


def _next_paid_note(S: Store) -> Cell:
    """The note on the lock panel's last column. E-16's 'Next paid data' gives the first call for Locks 1-3 (the main run's entry runs
    on to its last commit) and Study 1b's first invocation for Lock 4, while the timeline's run rows start each span when the run's
    command started; so the main run shows two start times (verifier, PR 27 round 1). Each entry is checked equal to the record the
    timeline prints for that event (Pilot 1's first paid call, the length sweep's first send, the main run's first send and last
    commit, Study 1b's first invocation); the build stops if one differs. Both sides of each check stay in the note's record, unprinted."""
    main, s1b = "main-l14n6-1", "study1b-1"
    inv1b = r"INVOCATIONs (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z;"
    pairs = [
        (extract(e16(S, "1", "Next paid data"), r"^Pilot 1 first call (\d\d:\d\d)$"),
         extract(find_cell(S, r"^\| Pilot, first paid call \|", "Time"), r"^\d\d-\d\d (\d\d:\d\d)$"), "Pilot 1's first call"),
        (extract(e16(S, "2", "Next paid data"), r"^length sweep (\d\d:\d\d:\d\d)$"),
         cut(S, "settle_g4", r"The first `send` was at", r"first `send` was at \*\*(\d\d:\d\d:\d\d)\.\d+Z\*\*"),
         "the length sweep's first call"),
        (extract(e16(S, "3", "Next paid data"), r"^main run (\d\d:\d\d:\d\d)–\d\d:\d\d:\d\d, so "),
         spend_cut(S, main, "What ran", r"First send (\d\d:\d\d:\d\d)Z"), "the main run's first call"),
        (extract(e16(S, "3", "Next paid data"), r"^main run \d\d:\d\d:\d\d–(\d\d:\d\d:\d\d), so "),
         spend_cut(S, main, "What ran", r"last commit (\d\d:\d\d:\d\d)Z"), "the main run's last commit"),
        (extract(e16(S, "4", "Next paid data"), r"^Study 1b first INVOCATION (\d\d:\d\d:\d\d)$"),
         spend_cut(S, s1b, "What ran", inv1b, 1), "Study 1b's first invocation"),
    ]
    kept_parts: List[Cell] = []
    for a, b, what in pairs:
        if a.raw != b.raw:
            raise ValueError(f"TAB-20: the lock panel gives {a.raw} for {what}, its record {b.raw}")
        kept_parts += [kept(a, f"the lock panel's entry for {what}"),
                       kept(b, f"{what} as the timeline's record gives it, checked equal to the lock panel's entry")]
    return cat("Lock panel, last column: the next paid data after each lock, as our final fact-check lists it: the first call of "
               "Pilot 1, of the length sweep and of the main run (the main run's entry runs on to its last commit), and Study 1b's "
               "first invocation. The timeline's run rows instead start each run's span when its command started.", *kept_parts)


# ---------------------------------------------------------------- panel 2: every run's window (every run that sent an API call)


def _run_panel(S: Store) -> Table:
    WR, NO = "What ran", "Notes"
    cols = ["Run", "Date", "Lock in force", "Run commit", "Logged span (UTC)", "Invocations (UTC)", "Run started (UTC)",
            "Pauses", "First call (UTC)", "Last commit or end (UTC)"]
    hhmm = r"(\d\d:\d\d–\d\d:\d\d) UTC"
    commit_with = r"checkout at ([0-9a-f]{7}) with"
    setup = extract(find_cell(S, r"^\| 20-call check, S3 ", "Public proof"), r"^(before any lock)$")
    diag_t = find_cell(S, r"^\| Effort diagnostic \(", "Time")
    g4_send = r"The first `send` was at"

    def sc(run: str, col: str, rx: str, group: int = 1) -> Cell:
        return spend_cut(S, run, col, rx, group)

    spec: Dict[str, Dict[str, Any]] = {
        "smoke-1": {"lock": label("before any lock"), "note": smoke1_note(S)},
        "smoke-2": {"lock": label("before any lock"), "commit": sc("smoke-2", WR, r"run from M \(([0-9a-f]{7})\)")},
        "check-ledger-1": {"lock": setup, "commit": sc("check-ledger-1", WR, commit_with), "span": sc("check-ledger-1", WR, hhmm)},
        "s3-ledger-1": {"lock": setup, "commit": sc("s3-ledger-1", WR, commit_with), "span": sc("s3-ledger-1", WR, hhmm)},
        "pilot-ledger-1": {
            "lock": pilot_lock(S), "commit": sc("pilot-ledger-1", WR, commit_with), "span": sc("pilot-ledger-1", WR, hhmm),
            "pauses": sc("pilot-ledger-1", NO, r"; (no halts);"),
            "first": extract(find_cell(S, r"^\| Pilot, first paid call \|", "Time"), r"^\d\d-\d\d (\d\d:\d\d)$")},
        "diag-haiku-effort-1": {
            "lock": extract(find_cell(S, r"^\| Effort diagnostic \(", "Public proof"), r"^(under no lock);"),
            "commit": sc("diag-haiku-effort-1", WR, commit_with), "span": sc("diag-haiku-effort-1", WR, hhmm),
            "first": extract(diag_t, r"^\d\d-\d\d (\d\d:\d\d)–"), "last": extract(diag_t, r"–(\d\d:\d\d) \(paid calls\)$")},
        "ladder-l14n-1": {
            "lock": sc("ladder-l14n-1", WR, r"\(D-86 to D-89, under (prereg-lock-2)\)"),
            "commit": sc("ladder-l14n-1", WR, r"checkout at ([0-9a-f]{7}) \(the prereg-lock-2 tag\)"), "span": sc("ladder-l14n-1", WR, hhmm),
            # the spend log says "no stop" here and "no halts" for the pilot and the main run: one wording (Edith, proof 4, p. 38)
            "pauses": cat("no halts", kept(sc("ladder-l14n-1", NO, r"; (no stop)\."),
                                           "the spend log's own words, 'no stop', which our printed 'no halts' replaces (one wording)")),
            "first": cut(S, "settle_g4", g4_send, r"first `send` was at \*\*(\d\d:\d\d:\d\d)\.\d+Z\*\*"),
            "last": cut(S, "settle_g4", g4_send, r"^`commit` at (\d\d:\d\d:\d\d)Z\.$", offset=1)},
        "main-l14n6-1": {
            "lock": cat(sc("main-l14n6-1", WR, r"\(D-92, D-94; (prereg-lock-3)\)"), "(runner:", main_lock(S), ")"),
            "commit": sc("main-l14n6-1", WR, r"checkout at ([0-9a-f]{7}) \("),
            "inv": cat(sc("main-l14n6-1", WR, r"INVOCATION \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z; one invocation"), "(",
                       sc("main-l14n6-1", WR, r"INVOCATION \S+; (one invocation)\)"), ")"),
            "pauses": sc("main-l14n6-1", NO, r"; (no halts),"),
            "first": sc("main-l14n6-1", WR, r"First send (\d\d:\d\d:\d\d)Z"),
            "last": sc("main-l14n6-1", WR, r"last commit (\d\d:\d\d:\d\d)Z")},
        "study1b-1": {
            "lock": sc("study1b-1", WR, r"\(D-96; (prereg-lock-4)\)"),
            "commit": sc("study1b-1", WR, r"price-date commit ([0-9a-f]{7})[0-9a-f]* \("),
            "inv": cat(*[sc("study1b-1", WR, r"INVOCATIONs (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z;", g)
                         for g in (1, 2, 3, 4)], sep=", "),
            "window": sc("study1b-1", WR, r"window started (\d\d:\d\d:\d\d)Z"),
            "pauses": cat("truncation pause: none (", sc("study1b-1", NO, r"(every truncation check under \d+%) \(no pause\)"),
                          "); the run stopped after each failed upload of the 12-step point and was invoked again (see the notes)"),
            "last": sc("study1b-1", WR, r"Last commit (\d\d:\d\d:\d\d)Z")},
        "topup-1": {
            "lock": cat(sc("topup-1", WR, TU_LOCK, 1), TU_CHANGE, kept(sc("topup-1", WR, TU_LOCK, 2), ID)),
            "commit": sc("topup-1", WR, r"checkout at ([0-9a-f]{7}) \("),
            # TP-9: the spend log's own span for the run ('11:50-14:09:51Z, EXIT 0'), as for the other logged spans
            # both ends in seconds (Edith, proof 4, p. 37: "11:50–14:09:51" mixed minutes and seconds): the first invocation, as the timeline's
            # row gives the span, and the exit
            "span": span(sc("topup-1", WR, r"INVOCATIONs (\d\d:\d\d:\d\d)Z and"), sc("topup-1", WR, r"\d\d:\d\d-(\d\d:\d\d:\d\d)Z, EXIT 0")),
            "inv": cat(sc("topup-1", WR, r"INVOCATIONs (\d\d:\d\d:\d\d)Z and"), sc("topup-1", WR, r"and (\d\d:\d\d:\d\d)Z \(paused"),
                       sep=", "),
            # Edith, proof 4 (rulings of 2026-10-20): the time our cost records log as the top-up's "window started" is when the live run
            # started ("window_check in harness/pareto/main.py records started_utc at the live start, before the first batch is sent"),
            # as for every other run, so it is under "Run started" and S7 says "the live run started at" the same time. "First call" is
            # a dash: no stamped first-send time exists in the records this table reads (the work log gives the window as started and
            # then the first batch as sent, with no time for that send; checked in `_topup_first_send_untimed`).
            "window": sc("topup-1", WR, r"window started (\d\d:\d\d:\d\d)Z"),
            "pauses": cat("paused", sc("topup-1", WR, r"\(paused (\d\d:\d\d:\d\d)Z"), "with its first batch of requests in flight; resumed",
                          sc("topup-1", WR, r"and (\d\d:\d\d:\d\d)Z \(paused"), "; every call", topup_once(S)),
            "last": cat(sc("topup-1", WR, r"\d\d:\d\d-(\d\d:\d\d:\d\d)Z, EXIT 0"), "(run\u00a0end)")},
    }
    rows: List[List[Cell]] = []
    lines = list(reversed(S.find_lines("spend_log", r"^\| \d{4}-\d\d-\d\d \|")))
    for n in lines:
        run = S.get("spend_log", join_key(f"L{n}", "Run ID"))
        if "No API call." in S.get("spend_log", join_key(f"L{n}", WR)):
            continue                                            # bookkeeping rows (smoke-2's markers): no call, no window
        if run not in spec:
            raise KeyMissing(f"spend-log run {run!r} has no window spec: add it")
        sp = spec[run]
        run_cell = text_of(cell_ref(S, "spend_log", n, "Run ID"))
        if "note" in sp:
            run_cell = cat(run_cell, "(", sp["note"], ")")
        rows.append([run_cell, text_of(cell_ref(S, "spend_log", n, "Date")), sp["lock"],
                     sp.get("commit", DASH), sp.get("span", DASH), sp.get("inv", DASH), sp.get("window", DASH),
                     sp.get("pauses", DASH), sp.get("first", DASH), sp.get("last", DASH)])
    if len(rows) != len(spec):
        raise ValueError(f"run panel: {len(rows)} spend-log runs, {len(spec)} specs")
    # the table's note says a run's start comes after its first invocation: the build stops if a recorded start does not (times are
    # zero-padded hh:mm:ss, so they compare as text)
    for run, sp in spec.items():
        if "window" in sp and not ("inv" in sp and sp["window"].printed > sp["inv"].printed[:8]):
            raise ValueError(f"run panel: {run}'s run start is not after its first invocation, as the table's note says")
        if "inv" in sp and "first" in sp and len(sp["first"].printed) == 8 and not sp["first"].printed > sp["inv"].printed[:8]:
            raise ValueError(f"run panel: {run}'s first call is not after its first invocation")
    if "window" not in spec["topup-1"] or "first" in spec["topup-1"]:
        raise ValueError("run panel: the top-up's logged window start is its run start, under Run started, and its First call is a dash "
                         "(the note says no first-send time is stamped)")
    p = Table([label(c) for c in cols], rows, layout="landscape", groups=group_starts(rows, 1), font="footnotesize")
    # the last two columns wider, so "(run end)" sits on one line and the two headers take two lines, not three and four; the room comes
    # from "Lock in force" and "Pauses" (the writer's plan gave the last two columns their minimum width and kept the spare for the other
    # columns; Edith, proof 4, p. 37)
    set_widths(p, Run=0.96, Lock_in_force=0.70, Pauses=1.2, First_call_UTC=0.50, Last_commit_or_end_UTC=0.70)
    return p


# ---------------------------------------------------------------- panel 3: the exposed-base sensitivity (D-97)

NBSP = "\u00a0"


def quoted_reading(r: Ref) -> Cell:
    """A Study 1b template reading ("holds (no worse in all three views)", "inconclusive (could not show)") printed in quotation marks as
    the stamped file's own words (Edith, proof 4: stamped words that are not the paper's ruled wording print in quotation marks; the
    ruled reading, shown no worse (Holm-adjusted), is the table's Holm-adjusted columns). The cell keeps the stamped string as its raw
    value. A short parenthesis ("could not show") is tied whole and a longer one by its last four words, so that a wrapping column
    never breaks "inconclusive (could not / show)" (the same ties as TAB-22's Study 1b panels, paper_out_study1b.quoted_reading)."""
    words = str(text_of(r).printed)

    def tie(m: "re.Match[str]") -> str:
        parts = m.group(1).split(" ")
        keep = len(parts) if len(m.group(1)) <= 16 else 4
        head = " ".join(parts[:-keep]) + " " if len(parts) > keep else ""
        return "(" + head + NBSP.join(parts[-keep:]) + ")"
    return Cell('"' + re.sub(r"\(([^)]*)\)", tie, words) + '"', raw=r.value, refs=(r,),
                formula="the Study 1b file's template reading, in quotation marks (as the file words it; spaces in its parenthesis tied)")



def _exposed_panel(S: Store) -> Table:
    cols = ["Test", "Test set", "Puzzles", "Puzzles without the exposed ones", "Exposed puzzles left out",
            "Reading, 5-point margin", "Reading without them, 5-point margin", "Shown no worse (Holm-adjusted), as deployed, 5-point margin",
            "Shown no worse (Holm-adjusted) without them, as deployed, 5-point margin"]
    rows: List[List[Cell]] = []
    for t in ("B1", "B2", "B3"):
        setid = S.get("s1b", join_key("constants", "test_sets", t))
        ex = S.get("s1b", join_key(SENS, "excluded", setid))
        left = cat(*[text_of(S.ref("s1b", join_key(SENS, "excluded", setid, i))) for i in range(len(ex))], sep=", ")
        dep = [*PRIM, "views", "as_deployed", "tests", t]
        sen = [SENS, *PRIM, "views", "as_deployed", "tests", t]
        rows.append([label(STUDY1B_TESTS[t][0]), text_of(S.ref("s1b", join_key("constants", "test_sets", t))),
                     integer(S.ref("s1b", join_key(*dep, "n"))), integer(S.ref("s1b", join_key(SENS, "bases_per_test", t))), left,
                     quoted_reading(S.ref("s1b", join_key(*PRIM, "template", t))),
                     quoted_reading(S.ref("s1b", join_key(SENS, *PRIM, "template", t))),
                     text_of(S.ref("s1b", join_key(*dep, "declared")), YES_NO), text_of(S.ref("s1b", join_key(*sen, "declared")), YES_NO)])
    # footnotesize: the readings are quoted and tied (a long unbreakable piece), so the nine columns' minimum widths run past 9 in at \small
    return Table([label(c) for c in cols], rows, layout="landscape", font="footnotesize")


# ---------------------------------------------------------------- the table


def _s1b_resubmits(S: Store) -> Cell:
    """Why Study 1b has four invocations (the run panel): each later one re-submitted the 12-step point after its upload failed (D-108;
    TAB-19's 12-step retry row). The typed clause is guarded by the run record in Edith's Study 1b clearance review: each later
    invocation line submits the 12-step set's 1,760 keys or ends the run, and the last attempt is D-108's."""
    WR = "What ran"
    inv = r"INVOCATIONs (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z, (\d\d:\d\d:\d\d)Z;"
    for g in (2, 3, 4):
        t = spend_cut(S, "study1b-1", WR, inv, g).printed
        guard(cell_ref(S, "clr_1b", line_of(S, "clr_1b", rf"^- INVOCATION {re.escape(t)}Z", expect=1)),
              r"`batch_submitting` w\d+ \(1,760 keys|EXIT 0 at", f"the invocation at {t} re-submitted the 12-step point")
    line_of(S, "clr_1b", r"^- w9 \(`@4`, D-108\), msgbatch_\w+, 1,760 requests: submitted, collected", expect=1)
    # Edith's optional hedge (record §4): 'failed to upload' is the fact; the slow uplink was the likely cause, measured only after the
    # third failure, so it is not printed (the spend log's words stay in the cell's record). The ruling's id is kept, not printed.
    fail = r"Waves (w6-w8 \(the 12-step point\) failed to upload)( on a slow uplink); (no batch was created) \("
    fourth = r"\([\d,]+; (D-108)'s (4th attempt)\)"
    return cat("Study 1b's later invocations each re-submitted the 12-step point after its upload failed: waves",
               en_dash(spend_cut(S, "study1b-1", WR, fail, 1)), ", and", spend_cut(S, "study1b-1", WR, fail, 3),
               kept(spend_cut(S, "study1b-1", WR, fail, 2), "the cause the spend log names: the likely cause, measured after the "
                    "third failure (Edith, PR 27 record section 4)"),
               "; they were", spend_cut(S, "study1b-1", WR, r"; (closed at \$0) with"), ", and the 12-step point went through on its",
               spend_cut(S, "study1b-1", WR, fourth, 2), kept(spend_cut(S, "study1b-1", WR, fourth, 1), ID),
               ", a disclosed deviation (TAB-19).")


def _topup_first_send_untimed(S: Store) -> Cell:
    """The run panel's dash under the top-up's "First call" (Edith, proof 4, rulings of 2026-10-20): the build stops if a record this
    table reads gives a time for the top-up's first send, because the cell would then print it. The work log's sentence on the first
    round carries no clock time, and the spend log's row for the run has no "first send" (the main run's row has one). Kept,
    unprinted, in the note that says so."""
    sent = extract(line(S, "log", r"^## 2026-10-13 \(Friday\) — topup-1 running: ", 2), r"Round 1 sent: (.*?) Counts and costs only")
    if re.search(r"\d\d:\d\d", str(sent.raw)):
        raise ValueError(f"TAB-20: the work log now gives a time for the top-up's first send ({sent.raw!r}): print it under First call")
    if re.search(r"first send", str(spend_ref(S, "topup-1", "What ran").value), re.I):
        raise ValueError("TAB-20: the spend log now gives a first-send time for the top-up: print it under First call")
    return kept(sent, "the work log's sentence on the top-up's first batch has no time")


@output("TAB-20")
def tab_20(S: Store) -> Table:
    cols = ["Date", "Time (UTC)", "Event", "Commit or record", "Seal or note"]
    rows = _main_rows(S)
    z3e = r"^## \S+ \(\w+\) — Zenodo v3 published \(DOI "
    z3 = r"^## \S+ \(\w+\) — Zenodo v3 PUBLISHED: DOI "
    lock2_plan = r"^- \"Lock 2's only public timestamp is its Zenodo record, posted .* Our plan had called for a$"
    start_change = evidence(reg_ref(S, "D-111", "Decision (plain)"), r"declared-change commit ([0-9a-f]{7}) \(not_before moved earlier",
                            "the top-up's run commit moved the plan's earliest start (not_before) earlier")
    tu_commit = spend_cut(S, "topup-1", "What ran", r"checkout at ([0-9a-f]{7}) \(")
    if start_change.raw != tu_commit.raw:
        raise ValueError(f"TAB-20: the declared-change commit {start_change.raw} is not the top-up's run commit {tu_commit.raw}")
    notes = [
        [label("All times are UTC. The lock tag times, and the commit times of the puzzle sets, Addendum C4, the record merge and the "
               "price-date commit, are git's tagger and committer times, as re-read from git in our final fact-check; the commit times "
               "of the length pick and of Study 1's k.json are from our own process record; run times are from our records of each "
               "run (a logged span starts when the run's command started, before its first call); the exposure scan's time is "
               "the Lock 4 manifest's; gist, Wayback and Zenodo times are the public records' own. A date is printed on the first row "
               "of each UTC day; the rows below it fall on the same day. A row with no time is a ruling, or a run or step whose record "
               "gives only its date; it sits in order between the rows around it.")],
        # N-1 and Q26: no time zone is named (no pinned record states one); 'a local calendar date, not a UTC one' is Edith's wording.
        [cat("Deviation 1's ruling has no recorded time: our decision records give only its date, with no time or time zone. That "
             "date, printed beside it, is a local calendar date, not a UTC one. It was ruled after the effort diagnostic and before "
             "the puzzle sets were committed.", *_local_dates_evidence(S))],
        [cat("Run rows give each run's span from its records; the second panel splits it into invocations, the run's start, pauses, "
             "first call and last commit or end. \"Run started\" is the time our cost records log as the run's \"window started\" "
             "(after its first invocation). The top-up's \"First call\" is a dash: its work log records \"Window started\" and then its "
             "first batch of requests as sent, with no time for that send.",
             evidence(line(S, "log", r"^## 2026-10-13 \(Friday\) — topup-1 running: ", 2),
                      r"Window started \d\d:\d\d:\d\dZ \(48 h\)\. (Round 1 sent): ",
                      "the top-up's window start is followed by its first round sent"),
             _topup_first_send_untimed(S),
             "Commits, gists and hashes are shortened in the timeline; the lock panel prints each lock's full commit ID and tar "
             "SHA-256, and TAB-23 the analysis files' hashes.")],
        [_s1b_resubmits(S)],
        [cat("Lock 3's Zenodo v3: our project log records the DataCite registration at",
             cut(S, "log", z3, r"\(DataCite \d{4}-\d\d-\d\dT(\d\d:\d\d:\d\d)Z\)$"), "UTC and the publication time read from the Zenodo API "
             "at", cut(S, "log", z3e, r"zenodo\.\d+, (\d\d:\d\d:\d\d)Z\)"), "UTC; both fall inside the main run.")],
        # N-11: our lock procedure (D-71's ruling, kept unprinted) set the three proofs for each lock; Lock 1 has all three (E-16).
        [cat("Our lock procedure set a Zenodo record plus a gist with a Wayback snapshot as each lock's public proof; Lock 1 has all "
             "three.", rid(S, "D-71"),
             evidence(reg_ref(S, "D-71", "Decision (plain)"), r"^Where D-69's public fingerprint goes: (a Zenodo record) holding only",
                      "the lock procedure's Zenodo record"),
             evidence(reg_ref(S, "D-71", "Decision (plain)"),
                      r"Plus (a public GitHub gist with the same fingerprint and an Internet Archive \(Wayback\) snapshot)",
                      "the lock procedure's gist and Wayback snapshot"),
             evidence(e16(S, "1", "Public proof (UTC)"), r"^(gist) \d\d:\d\d:\d\d; Wayback \d{14}; Zenodo v1 \d\d:\d\d:\d\d ",
                      "Lock 1 has a gist, a Wayback snapshot and a Zenodo record"),
             # "Lock 2 has only its Zenodo record." The settlement's own sentence, "Our plan had called for a gist and an archive snapshot as well",
             # is not printed (Edith, proof 4, p. 39: it repeats the sentence before it, which says the procedure set all three, and
             # names the snapshot a third way); it stays in the cell's record, unprinted, for the claim that Lock 2 has only its Zenodo record
             "Lock 2 has only its Zenodo record.",
             kept(cut(S, "settle_g4", lock2_plan, r"(Our plan had called for a)$"), "the settlement's quotation of Lock 2's plan, not printed"),
             kept(cut(S, "settle_g4", lock2_plan, r"^(gist and an archive snapshot as well)\.\"$", offset=1),
                  "the settlement's quotation of Lock 2's plan, not printed (Lock 2 had a Zenodo record only)"),
             "Lock 3 was first public as a gist, with Zenodo v3 deposited during the main run, as its record states.")],
        # D-142: the start-time change is the plan's earliest start (a protocol fact); no intent and no reason for the pause is given.
        [cat("Study 1b ran at the tag's", cut(S, "log", r"^## \S+ \(\w+\) — STUDY 1b LAUNCHED: ", r"\(the tag's (only first-parent child)\)"),
             "; the top-up at a later commit that also moved the plan's earliest start time earlier, as a disclosed change (TAB-19).",
             start_change, kept(tu_commit, "the top-up's run commit, checked equal to the declared-change commit"))],
        # the register says the analysis "goes in the appendix only": inside the supplement that names nothing (Edith, proof 4, p. 39), so the
        # note says where it is reported; the register's words stay in the cell's record
        [cat("Exposed-puzzle sensitivity (third panel): a pre-registered sensitivity analysis. It is reported outside the main text (the "
             "paper's Appendix D; here, TAB-10's sensitivity panel, which gives its d, 95% interval, p and error-rate ratio) and never "
             "replaces the primary result.",
             kept(reg_cut(S, "D-97", r"(It goes in the appendix only and never replaces the primary result)"),
                  "the ruling's own words, 'in the appendix only', which our printed 'outside the main text' replaces (inside the supplement "
                  "'the appendix' names nothing)"),
             "Readings in quotation marks are the Study 1b "
             "file's own template words; the ruled reading, shown no worse (Holm-adjusted), is in the columns headed \"Shown no worse "
             "(Holm-adjusted)\".")],
        [label("A dash: the records give nothing for that cell; in the lock panel, Lock 2's dash means it has no Wayback snapshot.")],
        [_next_paid_note(S)],
    ]
    caption = {"tier": [label("disclosure")],
               "study": [cat("every run that sent an API call (", text_of(spend_ref(S, "smoke-1", "Run ID")), smoke1_note(S),
                             "): the setup checks, Pilot 1, the effort diagnostic, the length sweep, the main run, Study 1b "
                             "and the top-up run")],
               "set": [label("the sensitivity panel: Study 1b's test sets, with the exposed puzzles left out")],
               "n": [label("the sensitivity panel: puzzles per test, as read from Study 1b's analysis file")]}
    # row groups (Edith's polish standard, section 7.7): a little space above the first row of each day (the Date column prints a date
    # on the first row of its day only)
    days = [i for i, r in enumerate(rows) if i > 0 and r[0].printed.strip()]
    t = Table([label(c) for c in cols], rows, notes, caption, layout="longtable", groups=days)
    t.panels = [("Locks (fingerprints and public proofs)", _lock_panel(S)),
                ("Runs (every run that sent an API call)", _run_panel(S)),
                ("Exposed-puzzle sensitivity (Study 1b, pre-registered)", _exposed_panel(S))]
    return no_internal_names(t)
