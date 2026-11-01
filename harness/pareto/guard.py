"""SpendGuard: the code that stops Pareto spending more API credit than a run is allowed.

Rules (CHATS.md rule 7, harness/README.md "Rules for every paid call", ops/review-checklist.md 2a,
Edith's PR #11 reviews: round 1 B1, H1, H2, H5; round 2 R1, R2, R4, R8, R10, R11; round 3 T1, T5-T7; round 4 U1-U3):

- Dry run is the default. `require_live()` passes only with live=True AND a clearance file that names
  this run, its cap, the machine-wide ledger root, the main checkout's .env path, the git commit being
  run (with a clean checkout), today's price table, an expiry at most 7 days away, a review file with
  the line `CLEARED: <run_id> <commit> <ledger_root>`, and `user_go: "go: ..."`. Nothing here reads
  environment variables, opens .env, or touches the network; the only subprocess is `git`, run with
  an empty environment.
- A live guard keeps every ledger and the live-run lock under ONE root for all checkouts:
  <main checkout>/data/raw/ (from `git rev-parse --git-common-dir`). It holds an exclusive lock on its
  ledger and the one live-run lock (raw/.live.lock), so only one live run on this machine spends at a
  time. It adds up earlier spend per run from the spend log's rows and every other live ledger.
  A dry guard is given global_spent_usd.
- Before a call is sent, `reserve()` books its worst case: at LIST price for a real-time call, at the
  Batch price (half of list) for batch=True. It refuses unless spent + open reservations + this one
  fit under BOTH the run cap and the global cap. The Batch price is an assumption checked ONCE for the
  whole machine (T1, U1-U3): until a PASSING record_console_check() exists in some live ledger, all
  live runs' Batch reservations together may not pass $1; a FAILED check (Console over the ledgers by
  more than 5% + 1 cent) halts its run and blocks every live Batch reservation until a human calls
  clear_console_block(note). Batch items are committed at the Batch price, so a commit alone would NOT
  notice Batch billed at list; the Console check does.
- Lifecycle of one call:  reserve -> mark_sent -> (network) -> commit(usage).
  * commit() replaces the reservation with the real cost from the reported usage.
  * Refusals, truncations, and errors that report usage are COMMITTED, never released.
  * If a call was sent but no usage came back, leave the reservation OPEN: it counts at its worst
    case until a human commits the real usage (after checking the Console).
  * release() is only for a call known never to have been sent. It refuses once mark_sent() ran.
- If a commit costs more than its reservation, or spend passes a cap, the guard HALTS: every later
  reserve() and mark_sent() raises GuardHalted. commit() and release() still work. A halt is never
  undone: replay() recomputes it from every commit instead of trusting a separate halt line.
- Ledger: one JSON line per event, written and fsynced BEFORE memory changes. `SpendGuard.replay()`
  rebuilds the exact state; a torn final line (no newline, from a crash mid-write) is dropped with a
  warning and recorded in the next ledger line. Reservations a crash left open stay counted.
- One threading lock guards all state, so concurrent reserves can never jointly pass a cap.
"""

from __future__ import annotations

import fcntl
import json
import os  # os.fsync and os.defpath only; nothing here reads the environment
import re
import subprocess
import threading
import warnings
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import prices
from .prices import Usage

REPO_ROOT = Path(__file__).resolve().parents[2]
Request = Tuple[str, str, int, int, bool]  # (key, model, est_input_tokens, max_tokens, batch)
GitRunner = Callable[[List[str]], str]
# R11/T7: the whole tree must be clean, except raw run data and Edith's review files (data/tasks counts).
# --untracked-files=all lists each new file, so an untracked data/tasks/x is not folded into "data/".
DIRTY_CHECK = ["status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)data/raw",
               ":(exclude)ops/reviews"]
# T1 Console check. These numbers are OUR choice (Edith accepted them), not from any source:
CONSOLE_TOLERANCE = (Decimal("1.05"), Decimal("0.01"))  # the Console may exceed the ledgers by 5% + 1 cent
CONSOLE_MIN_SHARE = Decimal("0.95")  # below 95% of the ledger, the Console has not caught up yet
# Fixed, not an argument (Edith, T1): Batch spend X billed at list shows as 2X, which trips the halt
# once 2X > 1.05X + 0.01, i.e. X > $0.0105; $0.05 detects it with about 5x margin.
MIN_BATCH_SPEND_FOR_CHECK = Decimal("0.05")
# Billing rule B5 (research/facts-checked.md): a refusal BEFORE any output is free in these categories
# ("none" is a refusal with no category). bio, frontier_llm and reasoning_extraction are billed.
B5_FREE_CATEGORIES = ("cyber", "general_harms", "none")
# U2: until a PASSING Console check exists, the Batch reservations of all live runs together (worst case)
# may not pass $1, so the first Batch that the check confirms is always small (the smoke's is $0.29).
UNCHECKED_BATCH_LIMIT = Decimal("1")


class ConsoleNotUpdated(Exception):
    """The Console figure is below 95% of the ledgers: it has not caught up yet. Nothing was recorded."""


def console_over(dollars_seen: Decimal, ledger_total: Decimal) -> bool:
    """True when the Console exceeds the ledgers by more than 5% + 1 cent (a FAILED check)."""
    ratio, cents = CONSOLE_TOLERANCE  # our choice (Edith accepted it), not a sourced figure
    with prices.money_context():
        return dollars_seen > ledger_total * ratio + cents


GO_PATTERN = r"go:\s*\S"  # R8: user_go starts with "go:" and the user's words
MAX_CLEARANCE_DAYS = 7  # R8: a clearance expires at most 7 days ahead
Clock = Callable[[], datetime]


class CapExceeded(Exception):
    """A reservation would pass the run cap or the global cap."""


class GuardHalted(Exception):
    """The guard has halted; no new call may be reserved or sent."""


class NotLive(Exception):
    """Live spending is not cleared for this run."""


class LedgerBusy(Exception):
    """Another guard (in this or another process) holds the ledger or the live-run lock."""


class ConsoleCheckNeeded(Exception):
    """T1: no live ledger has a Console check yet, and Batch items already exist: check before more Batch."""


@dataclass
class Reservation:
    model: str
    amount: Decimal
    batch: bool
    sent: bool = False


# ---------------------------------------------------------------------------- module helpers

def read_spent_from_spend_log(path: Path) -> Decimal:
    """The "Spent (rows below)" figure from ops/spend-log.md's summary table. Exactly one line."""
    text = Path(path).read_text(encoding="utf-8")
    found = re.findall(r"^\|\s*Spent \(rows below\)\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|\s*$", text, re.M)
    if len(found) != 1:
        raise ValueError(f"expected exactly one 'Spent (rows below)' line in {path}, found {len(found)}")
    return Decimal(found[0])


def ledger_path_for(data_root: Path, run_id: str) -> Path:
    """The one ledger path of a run: <data_root>/raw/<run_id>/ledger.jsonl."""
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError(f"run_id {run_id!r} must be letters, digits, '.', '_' or '-'")
    return Path(data_root) / "raw" / run_id / "ledger.jsonl"


def check_passed(line: dict) -> bool:
    """A console_check line passed only if it says so AND its own figures agree: the Console within
    tolerance of its ledger_total (the B5-adjusted total, S2), and its BILLED Batch spend (B5-free
    Batch refusals taken out; P1) at least the $0.05 floor (N61: a hand-written "0 vs 0" line is not
    a pass). Anything else is a failed check."""
    try:
        ledger_total, batch_billed = Decimal(line["ledger_total"]), Decimal(line["batch_billed"])
        return (line.get("passed") is True and batch_billed >= MIN_BATCH_SPEND_FOR_CHECK
                and not console_over(Decimal(line["dollars_seen"]), ledger_total))
    except (KeyError, ArithmeticError, TypeError):
        return False


def marker_valid(marker: dict, commit: dict) -> bool:
    """P3: a free_by_rule_marked event is valid only if it names a B5-free category, carries a note,
    and its commit (same key, same ledger) is not free already and reported no output tokens: a refusal
    before any output, the only kind B5 can make free."""
    try:
        return (marker.get("category") in B5_FREE_CATEGORIES and str(marker.get("note", "")).strip() != ""
                and not commit.get("_free", commit.get("free_by_rule") is True)
                and commit["usage"]["output_tokens"] == 0)
    except (KeyError, TypeError):
        return False


def ledger_check_consistent(line: dict, committed: Decimal, free: Decimal,
                            batch_raw: Decimal, batch_free: Decimal) -> bool:
    """N61: a pass read from ANOTHER ledger must be about that ledger alone. Its `spent` equals the sum
    of that ledger's own commits before it, its raw_total equals that too, and its ledger_total (the
    B5-adjusted figure the Console was compared with, S2) equals those commits minus the ones flagged
    free_by_rule; P2: its batch_raw equals that ledger's own Batch commits before it, and its
    batch_billed equals those minus the free_by_rule ones. (The real first check, the smoke's, is made
    when its ledger is the only live one, so it qualifies; a check recorded while other live ledgers
    existed counts only inside its own run.)"""
    try:
        return (Decimal(line["spent"]) == committed and Decimal(line["raw_total"]) == committed
                and Decimal(line["ledger_total"]) == committed - free
                and Decimal(line["batch_raw"]) == batch_raw
                and Decimal(line["batch_billed"]) == batch_raw - batch_free)
    except (KeyError, ArithmeticError, TypeError):
        return False


def scan_ledger(path: Path) -> Dict[str, object]:
    """One ledger, from its complete lines: run_id, live, spent, exposure (spent + open reservations),
    and for the Console gate: batch_reserved (worst case of every Batch reservation ever made),
    batch_spent (committed at the Batch price), open_batch (Batch keys still open), passes and failed
    ((run_id, seq) of each passing / failed console_check), cleared (failed checks a
    console_halt_cleared event cleared) and voided (passes it voided, V1). A torn final line is ignored,
    which leaves any reservation it would have settled counted.
    N61: this ledger is not fully replayed, so a pass read from it counts only if check_passed() holds
    AND ledger_check_consistent() does (its figures equal this ledger's own commits before it, with
    the free_by_rule ones taken out of the adjusted total). free_spent sums the free_by_rule commits (S2). A line failing check_passed() counts as a FAILED check (it blocks: fails closed);
    a passing line that is not consistent is ignored (it opens nothing)."""
    data = Path(path).read_bytes()
    lines = [json.loads(raw) for raw in data[:data.rfind(b"\n") + 1].decode("utf-8").splitlines()]
    if not lines or lines[0].get("event") != "open":
        raise ValueError(f"ledger {path} does not start with an 'open' line")
    run_id = lines[0].get("run_id")
    spent = exposure = Decimal("0")
    for line in reversed(lines):
        if "spent" in line:
            spent = Decimal(line["spent"])
            exposure = spent + Decimal(line["reserved"])
            break
    facts = {"batch_reserved": Decimal("0"), "batch_spent": Decimal("0"), "open_batch": set(),
             "passes": set(), "failed": set(), "cleared": set(), "voided": set()}
    committed = Decimal("0")  # this ledger's own spend, summed from its commit lines
    free = Decimal("0")  # S2: the part of it that billing rule B5 makes free (free_by_rule commits)
    batch_free = Decimal("0")  # P1: the free_by_rule commits that were Batch items
    commits: Dict[str, dict] = {}  # P3: key -> its commit line, so a later marker can be checked
    with prices.money_context():
        for line in lines:
            event, key = line.get("event"), line.get("key")
            if event == "reserve" and line.get("batch") is True:
                facts["batch_reserved"] += Decimal(line["amount"])
                facts["open_batch"].add(key)
            elif event in ("commit", "release"):
                facts["open_batch"].discard(key)
                if event == "commit":
                    commits[key] = dict(line, _free=line.get("free_by_rule") is True)
                    committed += Decimal(line["amount"])
                    if line.get("free_by_rule") is True:
                        free += Decimal(line["amount"])
                    if line.get("batch") is True:
                        facts["batch_spent"] += Decimal(line["amount"])
                        if line.get("free_by_rule") is True:
                            batch_free += Decimal(line["amount"])
            elif event == "free_by_rule_marked":
                # P3: honoured only if it marks a real, not-yet-free commit of THIS ledger with no output;
                # anything else is ignored (it then stays billed, the safe direction).
                target = commits.get(key)
                if target is not None and marker_valid(line, target):
                    target["_free"] = True
                    free += Decimal(target["amount"])
                    if target.get("batch") is True:
                        batch_free += Decimal(target["amount"])
            elif event == "console_check":
                if not check_passed(line):
                    facts["failed"].add((run_id, line.get("seq")))
                elif ledger_check_consistent(line, committed, free, facts["batch_spent"], batch_free):
                    facts["passes"].add((run_id, line.get("seq")))
                # else: a pass this ledger cannot vouch for; it is neither a pass nor a failure
            elif event == "console_halt_cleared":
                facts["cleared"] |= {(r, s) for r, s in line.get("clears", [])}
                facts["voided"] |= {(r, s) for r, s in line.get("voids", [])}
    facts.update({"run_id": run_id, "live": lines[0].get("live") is True, "spent": spent, "exposure": exposure,
                  "free_spent": free, "batch_free": batch_free})
    return facts


def spend_log_rows(path: Path) -> Dict[str, Tuple[Decimal, str]]:
    """Run ID -> (sum of its "USD (computed)" cells, its Notes cells joined) from ops/spend-log.md's
    Rows table. Cross-checked: the rows must add up to the "Spent (rows below)" line exactly."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header = [i for i, line in enumerate(lines) if line.startswith("|") and "Run ID" in line]
    if len(header) != 1:
        raise ValueError(f"expected one rows table with a 'Run ID' column in {path}")
    names = [c.strip() for c in lines[header[0]].strip().strip("|").split("|")]
    run_col, usd_col, notes_col = names.index("Run ID"), names.index("USD (computed)"), names.index("Notes")
    rows: Dict[str, Tuple[Decimal, str]] = {}
    for line in lines[header[0] + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(names):
            raise ValueError(f"spend-log row has {len(cells)} cells, expected {len(names)}: {line}")
        run_id, usd = cells[run_col].strip("`"), cells[usd_col].lstrip("$")
        if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", usd):
            raise ValueError(f"spend-log row for {run_id!r} has USD {cells[usd_col]!r}, not a plain number")
        old_usd, old_notes = rows.get(run_id, (Decimal("0"), ""))
        rows[run_id] = (old_usd + Decimal(usd), (old_notes + " " + cells[notes_col]).strip())
    total = sum((usd for usd, _ in rows.values()), Decimal("0"))
    if total != read_spent_from_spend_log(path):
        raise ValueError(f"spend-log rows add up to {total}, not the 'Spent (rows below)' figure")
    return rows


def ledger_ok_amount(notes: str) -> Optional[Decimal]:
    """The figure in a spend-log Notes cell's `ledger-ok: <dollars>` (a human reconciled that run's
    row with its ledger against the Console), or None."""
    found = re.search(r"ledger-ok:\s*\$?([0-9]+(?:\.[0-9]+)?)", notes)
    return Decimal(found.group(1)) if found else None


def shared_data_root(repo_root: Path, git: "GitRunner") -> Path:
    """The ONE data folder for every checkout of this repo: <main checkout>/data, found from
    `git rev-parse --git-common-dir` (the main repo's .git, also from a worktree)."""
    common = Path(git(["rev-parse", "--git-common-dir"]).strip())
    if not common.is_absolute():
        common = Path(repo_root) / common
    return common.resolve().parent / "data"


def git_runner_for(repo_root: Path) -> GitRunner:
    """Runs `git -C repo_root ...` with an empty environment (so no GIT_DIR or similar can redirect it)."""
    def run(args: List[str]) -> str:
        done = subprocess.run(["git", "-C", str(repo_root)] + list(args), check=True, capture_output=True,
                              text=True, env={"PATH": os.defpath})
        return done.stdout
    return run


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_expiry(value: str) -> datetime:
    """An ISO date means the end of that UTC day; an ISO date-time without a zone is UTC."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = date.fromisoformat(value)
        return datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=1)
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _check_money(name: str, value: object) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise TypeError(f"{name} must be a finite, non-negative Decimal, got {value!r}")
    return value


def _lock_file(path: Path, busy_message: str):
    """Open (creating) and exclusively lock a file without waiting. Returns the open binary handle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+b")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        raise LedgerBusy(busy_message) from None
    return fh


class SpendGuard:
    def __init__(self, run_id: str, run_cap_usd: Decimal, global_cap_usd: Decimal = Decimal("200"),
                 global_spent_usd: Optional[Decimal] = None, live: bool = False,
                 ledger_path: Optional[Path] = None, clearance_path: Optional[Path] = None, *,
                 data_root: Optional[Path] = None, repo_root: Optional[Path] = None,
                 git: Optional[GitRunner] = None, now: Optional[Clock] = None, _replay: bool = False) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(live, bool):
            raise TypeError("live must be True or False")
        self.run_id, self.live = run_id, live
        self.run_cap = _check_money("run_cap_usd", run_cap_usd)
        self.global_cap = _check_money("global_cap_usd", global_cap_usd)
        if self.run_cap == 0:
            raise ValueError("run cap must be above 0")
        if live and global_spent_usd is not None:
            raise ValueError("a live guard works out global spend itself; do not pass global_spent_usd")
        self.global_spent = Decimal("0") if live else _check_money("global_spent_usd", global_spent_usd)
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        self._git = git if git is not None else git_runner_for(self.repo_root)
        if data_root is None and live:
            data_root = shared_data_root(self.repo_root, self._git)  # R1: one root for every checkout
        self.data_root = Path(data_root) if data_root is not None else None
        self.clearance_path = Path(clearance_path) if clearance_path is not None else None
        self._now = now if now is not None else _utc_now
        self._lock = threading.Lock()
        self._open: Dict[str, Reservation] = {}
        self._done: Dict[str, str] = {}  # key -> "committed" or "released"; keys are never reused
        self._booked: Dict[str, Decimal] = {}  # key -> the amount its reservation booked
        self._cost: Dict[str, Decimal] = {}  # key -> the amount its commit recorded
        self._spent = Decimal("0")
        self._reserved = Decimal("0")
        self._halted, self.halt_reason, self._halt_logged = False, "", False
        self._seq = 0
        self._git_cleared = ""  # the commit whose git check passed (the running code was loaded at start)
        # The Console gate (T1, U1-U3). This run's own facts, kept up to date (and rebuilt by replay):
        self._batch_reserved = Decimal("0")  # worst case of every Batch reservation this run ever made
        self._batch_spent = Decimal("0")  # this run's spend committed at the Batch price
        self._free_spent = Decimal("0")  # S2: commits flagged free_by_rule (billing rule B5 bills them $0)
        self._batch_free = Decimal("0")  # P1: the free_by_rule commits that were Batch items
        self._commits: Dict[str, dict] = {}  # P3: key -> {amount, batch, usage, _free} of each commit
        self._passes: Set[Tuple[str, int]] = set()  # (run_id, seq) of this run's passing checks
        self._failed_checks: Set[Tuple[str, int]] = set()  # (run_id, seq) of this run's failed checks
        self._cleared: Set[Tuple[str, int]] = set()  # failed checks a human cleared in this ledger
        self._voided: Set[Tuple[str, int]] = set()  # passes a clearing in this ledger voided (V1)
        # ... and the same facts summed over the OTHER live ledgers under the shared root (live guards only).
        self._others = {"spent": Decimal("0"), "batch_spent": Decimal("0"), "batch_reserved": Decimal("0"),
                        "open_batch": 0, "passes": set(), "failed": set(), "cleared": set(), "voided": set(),
                        "free_spent": Decimal("0"), "batch_free": Decimal("0")}
        self.env_file: Optional[Path] = None  # T6: set by require_live(); the guard never opens it
        self._ledger_fh = None
        self._live_fh = None
        self.ledger_path: Optional[Path] = None
        if self.data_root is not None:
            per_run = ledger_path_for(self.data_root, run_id)
            if ledger_path is not None and Path(ledger_path).resolve() != per_run.resolve():
                raise ValueError(f"the ledger of run {run_id!r} must be {per_run}")
            ledger_path = per_run
        if ledger_path is None and _replay:
            raise ValueError("replay needs a ledger path")
        try:
            if live:
                self._live_fh = _lock_file(self.data_root / "raw" / ".live.lock",
                                           "another live run is spending; only one at a time")
                self.global_spent = self._global_spent_from_records()
            if self.global_spent > self.global_cap:
                raise ValueError(f"global spent {self.global_spent} is already over the global cap")
            if ledger_path is not None:
                self._open_ledger(Path(ledger_path), _replay)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        """Release the ledger lock and the live-run lock. The guard must not be used afterwards."""
        for name in ("_ledger_fh", "_live_fh"):
            fh = getattr(self, name, None)
            if fh is not None:
                fh.close()  # closing the handle releases its flock
                setattr(self, name, None)

    def __enter__(self) -> "SpendGuard":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ read-only state

    @property
    def spent(self) -> Decimal:
        with self._lock:
            return self._spent

    @property
    def reserved(self) -> Decimal:
        with self._lock:
            return self._reserved

    @property
    def remaining_run(self) -> Decimal:
        with self._lock:
            return self._remaining()[0]

    @property
    def remaining_global(self) -> Decimal:
        with self._lock:
            return self._remaining()[1]

    @property
    def halted(self) -> bool:
        with self._lock:
            return self._halted

    def open_reservations(self) -> Dict[str, Reservation]:
        with self._lock:
            return {k: Reservation(r.model, r.amount, r.batch, r.sent) for k, r in self._open.items()}

    def status(self, key: str) -> Optional[str]:
        """'open', 'committed', 'released', or None for a key never reserved in this run."""
        with self._lock:
            return "open" if key in self._open else self._done.get(key)

    def used_keys(self) -> Set[str]:
        """Every key ever reserved in this run, open or settled, replayed ones included."""
        with self._lock:
            return set(self._open) | set(self._done)

    def open_keys(self) -> Set[str]:
        with self._lock:
            return set(self._open)

    def summary(self, keys: Iterable[str]) -> Dict[str, object]:
        """For logging one wave: reserved = what these keys' reservations booked, committed = what their
        commits recorded, open = how many are still open, done = how many are committed or released.
        A key never reserved in this run raises KeyError."""
        with self._lock, prices.money_context():
            keys = set(keys)
            unknown = keys - set(self._booked)
            if unknown:
                raise KeyError(f"never reserved in this run: {sorted(unknown)}")
            return {"reserved": sum((self._booked[k] for k in keys), Decimal("0")),
                    "committed": sum((self._cost.get(k, Decimal("0")) for k in keys), Decimal("0")),
                    "open": sum(1 for k in keys if k in self._open),
                    "done": sum(1 for k in keys if k in self._done)}

    def sent_unsettled_keys(self) -> Set[str]:
        """Keys marked sent and not yet committed: in flight, or lost and waiting for a human."""
        with self._lock:
            return {k for k, r in self._open.items() if r.sent}

    # ------------------------------------------------------------------ the live gate

    def require_live(self) -> None:
        """Raise NotLive unless live=True and the clearance file passes every check below. The
        transport calls this before every network call; mark_sent() also calls it in live mode."""
        if not self.live:
            raise NotLive("dry run: live=False")
        if self.halted:
            raise GuardHalted(self.halt_reason)
        if self.clearance_path is None or not self.clearance_path.is_file():
            raise NotLive(f"no clearance file at {self.clearance_path}")
        try:
            data = json.loads(self.clearance_path.read_text(encoding="utf-8"), parse_float=Decimal)
        except ValueError as exc:
            raise NotLive(f"clearance file is not valid JSON: {exc}") from None
        if not isinstance(data, dict) or data.get("run_id") != self.run_id:
            raise NotLive("clearance run_id does not match this run")
        cap = data.get("cap_usd")
        try:
            cap_ok = not isinstance(cap, bool) and isinstance(cap, (str, int, Decimal)) and Decimal(cap) == self.run_cap
        except ArithmeticError:
            cap_ok = False
        if not cap_ok:
            raise NotLive(f"clearance cap_usd {cap!r} does not equal the run cap {self.run_cap}")
        for field in ("edith_clearance", "user_go", "git_commit", "price_table_date", "expires", "ledger_root",
                      "env_file"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise NotLive(f"clearance field {field!r} is missing or empty")
        if not re.match(GO_PATTERN, data["user_go"]):
            raise NotLive("clearance user_go must start with 'go:' followed by the user's words")
        now = self._now().astimezone(timezone.utc)
        self._check_prices_and_expiry(data, now)
        root = Path(data["ledger_root"])
        if not root.is_absolute() or self.data_root is None or root.resolve() != self.data_root.resolve():
            raise NotLive(f"clearance ledger_root {data['ledger_root']!r} is not this guard's root {self.data_root} "
                          "(it must be an absolute path)")
        env_file = self._check_env_file(data["env_file"])
        commit = data["git_commit"].strip()
        self._check_git(commit)
        self._check_review_file(data["edith_clearance"], commit)
        self.env_file = env_file

    def _check_env_file(self, value: str) -> Path:
        """T6: the key file is the main checkout's .env (the main checkout holds the shared data root).
        Only the path is compared; the guard never opens, reads or even stats the file."""
        expected_env = self.data_root.resolve().parent / ".env"
        if not Path(value).is_absolute() or Path(value) != expected_env:
            raise NotLive(f"clearance env_file {value!r} is not the main checkout's {expected_env}")
        return expected_env

    def _check_prices_and_expiry(self, data: dict, now: datetime) -> None:
        if data["price_table_date"] != prices.PRICE_TABLE_DATE:
            raise NotLive(f"clearance price date {data['price_table_date']} is not the table's "
                          f"{prices.PRICE_TABLE_DATE}")
        try:
            checked = date.fromisoformat(prices.PRICE_TABLE_DATE)
            expires = _parse_expiry(data["expires"])
        except ValueError as exc:
            raise NotLive(f"bad date in clearance or price table: {exc}") from None
        if checked not in (now.date(), now.date() - timedelta(days=1)):
            raise NotLive(f"prices were checked {checked}; re-check them (today or yesterday, UTC)")
        if now > expires:
            raise NotLive(f"clearance expired at {expires.isoformat()}")
        if expires > now + timedelta(days=MAX_CLEARANCE_DAYS):
            raise NotLive(f"clearance expiry {expires.isoformat()} is more than {MAX_CLEARANCE_DAYS} days away")

    def _check_git(self, commit: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
            raise NotLive(f"clearance git_commit {commit!r} is not a commit hash")
        if self._git_cleared == commit:
            return
        try:
            head = self._git(["rev-parse", "HEAD"]).strip()
            dirty = self._git(DIRTY_CHECK).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise NotLive(f"cannot check git: {exc}") from None
        if not head.startswith(commit):
            raise NotLive(f"clearance is for commit {commit}, but HEAD is {head}")
        if dirty:
            raise NotLive(f"the checkout has uncommitted changes (outside data/raw/ and ops/reviews/):\n{dirty}")
        self._git_cleared = commit

    def _check_review_file(self, value: str, commit: str) -> None:
        reviews = (self.repo_root / "ops" / "reviews").resolve()
        path = (Path(value) if Path(value).is_absolute() else self.repo_root / value).resolve()
        if not path.is_relative_to(reviews) or not path.is_file():
            raise NotLive(f"edith_clearance {value!r} is not a file under ops/reviews/")
        # T5/T7: the whole line, from column 0, unstripped, naming the run, the commit and the ledger root.
        wanted = f"CLEARED: {self.run_id} {commit} {self.data_root.resolve()}"
        if wanted not in path.read_text(encoding="utf-8").splitlines():
            raise NotLive(f"{value} has no line exactly '{wanted}' (from the first column)")

    # ------------------------------------------------------------------ reserving

    def reserve(self, key: str, model: str, est_input_tokens: int, max_tokens: int,
                batch: bool = False) -> Decimal:
        """Book one call's worst case (list price; Batch price if batch=True). Returns the amount."""
        return self.reserve_many([(key, model, est_input_tokens, max_tokens, batch)])[0]

    def reserve_many(self, items: Sequence[Request]) -> List[Decimal]:
        """Book several calls at once, all or nothing."""
        priced = self._price(items)
        with self._lock, prices.money_context():
            total = sum((amount for _, _, amount, _ in priced), Decimal("0"))
            if self._halted:
                raise GuardHalted(self.halt_reason)
            for key, _, _, _ in priced:
                if key in self._open or key in self._done:
                    raise ValueError(f"duplicate key {key!r}: every attempt needs its own key")
            self._check_fits(total, priced[0][0] if len(priced) == 1 else f"{len(priced)} calls")
            batch_total = sum((amount for _, _, amount, batch in priced if batch), Decimal("0"))
            if batch_total > 0:
                closed = self._console_gate_reason(batch_total)
                if closed:
                    raise ConsoleCheckNeeded(closed)
            spent, reserved = self._spent, self._reserved
            lines = []
            for key, model, amount, batch in priced:
                reserved += amount
                lines.append({"event": "reserve", "key": key, "model": model, "batch": batch,
                              "amount": str(amount), "spent": str(spent), "reserved": str(reserved)})
            self._write(lines)
            for key, model, amount, batch in priced:
                self._open[key] = Reservation(model, amount, batch)
                self._booked[key] = amount
            self._reserved = reserved
            self._batch_reserved += batch_total
        return [amount for _, _, amount, _ in priced]

    def plan_waves(self, requests: Sequence[Request],
                   max_wave_size: Optional[int] = None) -> List[List[Request]]:
        """Split requests, in order, into the fewest consecutive waves whose worst case (as reserve()
        books it) each fits in what is left now. Reserves nothing. Real spend shrinks the room, so run only
        the FIRST wave, commit its results, then plan again for what is left; reserve_many checks
        every wave against the caps anyway. max_wave_size can hold a wave under the Batch API's own
        per-batch request limit."""
        if max_wave_size is not None and (isinstance(max_wave_size, bool) or not isinstance(max_wave_size, int)
                                          or max_wave_size < 1):
            raise ValueError("max_wave_size must be a positive int")
        requests = list(requests)
        priced = self._price(requests)
        with self._lock, prices.money_context():
            room = min(self._remaining())
        waves: List[List[Request]] = []
        current: List[Request] = []
        current_total = Decimal("0")
        with prices.money_context():
            for item, (key, _, amount, _) in zip(requests, priced):
                if amount > room:
                    raise CapExceeded(f"{key!r} alone needs {amount}, but only {room} is left")
                full = max_wave_size is not None and len(current) >= max_wave_size
                if current and (full or current_total + amount > room):
                    waves.append(current)
                    current, current_total = [], Decimal("0")
                current.append(item)
                current_total += amount
        if current:
            waves.append(current)
        return waves

    # ------------------------------------------------------------------ sending and settling

    def mark_sent(self, key: str) -> None:
        """Record that this call is about to go out: immediately before the network call (in dry
        run, before the fake response). In live mode it runs require_live() first. After this,
        release() is refused: the call must be committed, or left open if no usage ever comes back."""
        self.mark_sent_many([key])

    def mark_sent_many(self, keys: Iterable[str]) -> None:
        """Mark several keys sent in one ledger write, all or nothing (e.g. one Batch submission).
        A halt, a failed live gate, or any bad key marks none of them."""
        keys = list(keys)
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("mark_sent_many needs distinct keys")
        if self.live:
            self.require_live()
        with self._lock:
            if self._halted:
                raise GuardHalted(self.halt_reason)
            for key in keys:
                if self._get_open(key).sent:
                    raise ValueError(f"{key!r} is already marked sent")
            self._write([{"event": "send", "key": key, "spent": str(self._spent),
                          "reserved": str(self._reserved)} for key in keys])
            for key in keys:
                self._open[key].sent = True

    def commit(self, key: str, usage: Usage, batch: Optional[bool] = None, note: str = "",
               halt_reason: str = "", free_by_rule: bool = False) -> Decimal:
        """Replace the reservation with the real cost of the reported usage, and return that cost.
        Use it for every response that reports usage: answers, refusals, truncations, errors.
        batch defaults to the reservation's flag. batch=False on a Batch reservation prices it at list
        (allowed: it can only cost more); batch=True on a real-time reservation is refused. `note` goes into the
        ledger line (e.g. "http 529, assumed unbilled") so a zero-cost commit is never silent.
        halt_reason (e.g. a model mismatch) halts the guard in the SAME ledger write as the commit, so a
        crash cannot keep the commit and lose the halt; replay honours it.
        free_by_rule (S2): True for a refusal that billing rule B5 says is not billed. The amount stays
        the full usage cost, so spend and the caps are unchanged (conservative); the flag only takes it
        out of rule_adjusted_spent, which the Console check compares with."""
        if not isinstance(usage, Usage):
            raise TypeError("usage must be a prices.Usage")
        if not isinstance(halt_reason, str):
            raise TypeError("halt_reason must be a string")
        if not isinstance(free_by_rule, bool):
            raise TypeError("free_by_rule must be True or False")
        with self._lock, prices.money_context():
            res = self._get_open(key)
            billed_as_batch = res.batch if batch is None else batch
            if billed_as_batch and not res.batch:
                # A real-time reservation can never be settled at the cheaper Batch price.
                raise ValueError(f"{key!r} was reserved real-time; it cannot be committed at the Batch price")
            if not isinstance(billed_as_batch, bool):
                raise TypeError("batch must be True, False or None")
            # A Batch reservation committed with batch=False is priced at list: the safe direction. If it
            # costs more than the reservation (the 50% assumption was wrong), the guard halts below.
            actual = prices.cost(res.model, usage, billed_as_batch)
            spent, reserved = self._spent + actual, self._reserved - res.amount
            reason = self._halt_reason(key, actual, res.amount, spent) or halt_reason.strip()
            events = [{"event": "commit", "key": key, "model": res.model, "batch": billed_as_batch,
                       "amount": str(actual), "reservation": str(res.amount), "note": str(note),
                       "halt_reason": halt_reason.strip(), "free_by_rule": free_by_rule, "usage": asdict(usage),
                       "spent": str(spent), "reserved": str(reserved)}]
            if reason and not self._halted:
                events.append({"event": "halt", "reason": reason, "spent": str(spent),
                               "reserved": str(reserved)})
            self._write(events)
            del self._open[key]
            self._done[key] = "committed"
            self._cost[key] = actual
            self._commits[key] = {"amount": str(actual), "batch": billed_as_batch, "usage": asdict(usage),
                                  "_free": free_by_rule}
            self._spent, self._reserved = spent, reserved
            if billed_as_batch:
                self._batch_spent += actual
            if free_by_rule:
                self._free_spent += actual
                if billed_as_batch:
                    self._batch_free += actual
            if reason and not self._halted:
                self._halted, self.halt_reason, self._halt_logged = True, reason, True
        return actual

    def mark_free_by_rule(self, key: str, category: str, note: str) -> Decimal:
        """P3: mark an EARLIER commit of this ledger as free by billing rule B5, for ledgers written before
        commit(..., free_by_rule=True) existed (smoke-2). Append-only: it writes one
        `free_by_rule_marked` event and changes nothing already written. A human calls it on a live guard
        with a valid clearance (require_live() first), with the call-log line as evidence in `note`.
        Refused unless the commit exists in this ledger, reported zero output tokens (a refusal before
        any output), is not free already, and `category` is one B5 makes free (cyber, general_harms,
        none). Spend and caps are unchanged; only rule_adjusted_spent drops. Returns the amount marked."""
        self.require_live()
        if not isinstance(note, str) or not note.strip():
            raise ValueError("mark_free_by_rule needs a note citing the call-log evidence")
        with self._lock, prices.money_context():
            commit = self._commits.get(key)
            if commit is None:
                raise KeyError(f"{key!r} has no commit in this ledger")
            marker = {"event": "free_by_rule_marked", "key": key, "category": category, "note": note.strip()}
            if not marker_valid(marker, commit):
                raise ValueError(f"{key!r} cannot be marked free: the category must be one of "
                                 f"{B5_FREE_CATEGORIES}, the commit must report 0 output tokens, and it must not "
                                 "be free already")
            amount = Decimal(commit["amount"])
            self._write([dict(marker, amount=str(amount), spent=str(self._spent), reserved=str(self._reserved))])
            self._apply_marker(commit)
        return amount

    def _apply_marker(self, commit: dict) -> None:
        commit["_free"] = True
        self._free_spent += Decimal(commit["amount"])
        if commit["batch"] is True:
            self._batch_free += Decimal(commit["amount"])

    def release(self, key: str) -> None:
        """Drop a reservation at no cost. ONLY for a call known never to have been sent."""
        with self._lock, prices.money_context():
            res = self._get_open(key)
            if res.sent:
                raise ValueError(f"{key!r} was sent; commit its usage, or leave it open if none came back")
            reserved = self._reserved - res.amount
            self._write([{"event": "release", "key": key, "amount": str(res.amount),
                          "spent": str(self._spent), "reserved": str(reserved)}])
            del self._open[key]
            self._done[key] = "released"
            self._reserved = reserved

    def halt(self, reason: str) -> None:
        """Stop the run. Cannot be undone. When the halt follows a reply, use commit(halt_reason=...)."""
        with self._lock:
            self._halt(reason or "halted by caller")

    @property
    def rule_adjusted_spent(self) -> Decimal:
        """S2: this run's spend minus the commits flagged free_by_rule (what the Console should bill)."""
        with self._lock, prices.money_context():
            return self._spent - self._free_spent

    def _machine_batch(self) -> Tuple[Decimal, Decimal]:
        """(raw, billed) Batch spend over every live ledger; billed leaves out B5-free Batch refusals (P1)."""
        raw = self._batch_spent + self._others["batch_spent"]
        return raw, raw - self._batch_free - self._others["batch_free"]

    def _machine_totals(self) -> Tuple[Decimal, Decimal]:
        """(raw, B5-adjusted) spend over every live ledger under the shared root, this one included."""
        raw = self._spent + self._others["spent"]
        return raw, raw - self._free_spent - self._others["free_spent"]

    @property
    def console_checked(self) -> bool:
        """True when a PASSING Console check exists in any live ledger and no failed check is uncleared."""
        with self._lock:
            return self._passing_anywhere() and not self._unresolved_failures()

    def record_console_check(self, dollars_seen: Decimal, note: str) -> None:
        """Confirm ONCE that Batch really bills at 50% (T1, U1, U3). `dollars_seen` is the Anthropic
        Console's TOTAL cost since the first live run on this machine began; it is compared with the
        ledger total, which is the spend of every live ledger under the shared root (this one included;
        only one live run spends at a time). Refused, with nothing recorded, unless:
        - no Batch key is open in any live ledger;
        - Batch spend across all live ledgers is at least $0.05 (a fixed floor; zero means no Batch item);
        - the Console shows at least 95% of the ledger total (else ConsoleNotUpdated: wait, retry).
        S2: "the ledger total" here is the B5-ADJUSTED total: all live ledgers' spend minus the commits
        flagged free_by_rule (refusals billing rule B5 bills at $0). The check line records both it
        (ledger_total) and the raw total (raw_total).
        A Console figure above the adjusted total by more than 5% + 1 cent is recorded as a FAILED check,
        even if it is at or below the raw total: it means Batch was billed at list OR a refusal B5 calls
        free was billed, and either is what this check exists to catch; a human decides. It halts this
        guard and blocks every live Batch reservation on the machine until a human calls
        clear_console_block(note). Only a passing check opens the gate.
        V2: it runs require_live() first, so it needs a valid clearance for this run, like a paid call."""
        self.require_live()
        dollars_seen = _check_money("dollars_seen", dollars_seen)
        if not isinstance(note, str) or not note.strip():
            raise ValueError("record_console_check needs a note saying where the figure came from")
        with self._lock, prices.money_context():
            open_batch = sorted(k for k, r in self._open.items() if r.batch)
            if open_batch or self._others["open_batch"]:
                raise ValueError(f"Batch keys are still open (this run: {len(open_batch)}, other live runs: "
                                 f"{self._others['open_batch']}); settle them before the Console check")
            batch_raw, batch_billed = self._machine_batch()
            if batch_raw == 0:
                raise ValueError("no live ledger has a committed Batch item yet; there is nothing to check")
            if batch_billed < MIN_BATCH_SPEND_FOR_CHECK:
                raise ValueError(f"BILLED Batch spend across all live ledgers is {batch_billed} (raw {batch_raw}, "
                                 "B5-free Batch refusals taken out), below the "
                                 f"${MIN_BATCH_SPEND_FOR_CHECK} a meaningful check needs. Run one more small Batch "
                                 f"(the gate allows ${UNCHECKED_BATCH_LIMIT} of unchecked Batch reservations) and "
                                 "check after it")
            raw_total, ledger_total = self._machine_totals()  # S2: compare with the B5-adjusted total
            if dollars_seen < ledger_total * CONSOLE_MIN_SHARE:
                raise ConsoleNotUpdated(f"the Console shows {dollars_seen}, under 95% of the ledgers' B5-adjusted "
                                        f"{ledger_total}: it has not caught up yet; nothing recorded, try again later")
            passed = not console_over(dollars_seen, ledger_total)
            seq = self._seq + 1
            events = [{"event": "console_check", "dollars_seen": str(dollars_seen), "note": note.strip(),
                       "passed": passed, "ledger_total": str(ledger_total), "raw_total": str(raw_total),
                       "batch_billed": str(batch_billed), "batch_raw": str(batch_raw),
                       "spent": str(self._spent), "reserved": str(self._reserved)}]
            reason = "" if passed else (f"FAILED Console check: the Console shows {dollars_seen}, more than the "
                                        f"ledgers' B5-adjusted {ledger_total} + 5% and 1 cent (raw {raw_total}): "
                                        "Batch billed at list, or a refusal B5 calls free was billed?")
            if reason and not self._halted:
                events.append({"event": "halt", "reason": reason, "spent": str(self._spent),
                               "reserved": str(self._reserved)})
            self._write(events)
            if passed:
                self._passes.add((self.run_id, seq))
            else:
                self._failed_checks.add((self.run_id, seq))
                if not self._halted:
                    self._halted, self.halt_reason, self._halt_logged = True, reason, True

    def clear_console_block(self, note: str) -> List[Tuple[str, int]]:
        """U1: the ONLY way past a failed Console check. A human who has found out why the Console showed
        more than the ledgers (and fixed it, or decided Batch is safe) calls this on a LIVE guard with a
        note saying what they found. It writes one `console_halt_cleared` event listing every uncleared
        failed check (run_id, seq) on the machine, and returns that list. It does not un-halt the run
        that failed (halts are never undone), and it does not open the gate: it also VOIDS every passing
        check recorded so far on the machine (V1), so a NEW passing check is needed before any live Batch
        wave over the $1 limit. V2: it runs require_live() first (a valid clearance for this run)."""
        self.require_live()
        if not isinstance(note, str) or not note.strip():
            raise ValueError("clear_console_block needs a note saying what the human found and decided")
        with self._lock:
            pending = sorted(self._unresolved_failures())
            if not pending:
                raise ValueError("there is no failed Console check to clear")
            voids = sorted(self._valid_passes())
            self._write([{"event": "console_halt_cleared", "clears": [list(p) for p in pending],
                          "voids": [list(p) for p in voids], "note": note.strip(),
                          "spent": str(self._spent), "reserved": str(self._reserved)}])
            self._cleared |= set(pending)
            self._voided |= set(voids)
        return pending

    # ------------------------------------------------------------------ crash recovery

    @classmethod
    def replay(cls, ledger_path: Optional[Path], run_id: str, run_cap_usd: Decimal,
               global_cap_usd: Decimal = Decimal("200"), global_spent_usd: Optional[Decimal] = None,
               live: bool = False, clearance_path: Optional[Path] = None, **roots) -> "SpendGuard":
        """Rebuild a guard from its ledger, exactly: spend, open reservations (and whether each was
        sent), used keys, halt state (recomputed from every commit), and the sequence number. Later
        events append to the same file. Takes the ledger's lock, so a second replay in another
        process fails with LedgerBusy. Any gap, unknown event, other run's line or total mismatch
        raises: a human must look. roots: data_root, repo_root, git, now (as for the constructor)."""
        return cls(run_id, run_cap_usd, global_cap_usd, global_spent_usd, live, ledger_path, clearance_path,
                   _replay=True, **roots)

    def recover(self) -> Dict[str, Reservation]:
        """After replay(): list the reservations a crash left open, and log that they were found.
        They are NOT released. They stay reserved, so every cap check counts them as spent, until a
        human commits the real usage (e.g. a Batch result fetched later by custom_id) or releases one
        that was never sent. For the spend-log row, use spent + reserved while any remain open."""
        orphans = self.open_reservations()
        with self._lock:
            self._write([{"event": "recover", "open_keys": sorted(orphans),
                          "spent": str(self._spent), "reserved": str(self._reserved)}])
        return orphans

    # ------------------------------------------------------------------ internals (call under the lock)

    def _global_spent_from_records(self) -> Decimal:
        """Live only (R2): spend added up PER RUN. For each run id, the larger of its spend-log rows and
        its live ledger's spent + open reservations; rows with no ledger and ledgers with no row count
        too. This run's own ledger is left out (its spend is the guard's own). A row and a ledger that
        disagree refuse the start, unless the row's Notes say `ledger-ok: <the ledger's figure>` (a
        human checked the difference against the Console). Also records, for the T1 Console gate, the
        other live ledgers' committed Batch spend and whether any of them has a console_check."""
        rows = spend_log_rows(self.repo_root / "ops" / "spend-log.md")
        own = ledger_path_for(self.data_root, self.run_id).parent.resolve()
        ledgers: Dict[str, Decimal] = {}
        others = {"spent": Decimal("0"), "batch_spent": Decimal("0"), "batch_reserved": Decimal("0"),
                  "open_batch": 0, "passes": set(), "failed": set(), "cleared": set(), "voided": set(),
                  "free_spent": Decimal("0"), "batch_free": Decimal("0")}
        with prices.money_context():
            for path in sorted((self.data_root / "raw").glob("*/ledger.jsonl")):
                if path.parent.resolve() == own:
                    continue
                scan = scan_ledger(path)
                if scan["run_id"] != path.parent.name:
                    raise ValueError(f"ledger {path} belongs to run {scan['run_id']!r}, not its folder's name")
                if scan["live"]:
                    ledgers[scan["run_id"]] = scan["exposure"]
                    for name in ("spent", "batch_spent", "batch_reserved", "free_spent", "batch_free"):
                        others[name] += scan[name]
                    others["open_batch"] += len(scan["open_batch"])
                    for name in ("passes", "failed", "cleared", "voided"):
                        others[name] |= scan[name]
            total = Decimal("0")
            for run_id in sorted(set(rows) | set(ledgers)):
                row_usd, notes = rows.get(run_id, (None, ""))
                exposure = ledgers.get(run_id)
                if row_usd is not None and exposure is not None and row_usd != exposure:
                    if ledger_ok_amount(notes) != exposure:
                        raise ValueError(f"run {run_id}: spend log says {row_usd}, its ledger {exposure}; reconcile "
                                         f"with the Console and add 'ledger-ok: {exposure}' to the row's Notes")
                total += max(x for x in (row_usd, exposure) if x is not None)
        self._others = others
        return total

    def _unresolved_failures(self) -> Set[Tuple[str, int]]:
        return (self._failed_checks | self._others["failed"]) - (self._cleared | self._others["cleared"])

    def _valid_passes(self) -> Set[Tuple[str, int]]:
        """V1: passing checks on the machine that no later clearing has voided."""
        return (self._passes | self._others["passes"]) - (self._voided | self._others["voided"])

    def _passing_anywhere(self) -> bool:
        return bool(self._valid_passes())

    def _console_gate_reason(self, batch_amount: Decimal) -> str:
        """Why a live Batch reservation of `batch_amount` (worst case) must wait; "" if it may go.
        U1: any uncleared FAILED Console check, in any live ledger, blocks every live Batch reservation.
        U2: without a passing check, the Batch reservations of all live runs together (worst case,
        including this one, whatever became of them: errored, expired or crashed) may not pass $1.
        Dry guards are never gated."""
        if not self.live:
            return ""
        failed = self._unresolved_failures()
        if failed:
            return (f"a FAILED Console check ({sorted(failed)[0]}) blocks every live Batch reservation until a "
                    "human finds out why and calls clear_console_block(note), then records a passing check")
        if self._passing_anywhere():
            return ""
        unchecked = self._others["batch_reserved"] + self._batch_reserved + batch_amount
        if unchecked > UNCHECKED_BATCH_LIMIT:
            return (f"Batch billing has not passed a Console check yet: Batch reservations would reach {unchecked}, "
                    f"over the ${UNCHECKED_BATCH_LIMIT} allowed before it. Settle the Batch already sent, wait for the "
                    "Console to show it, then call record_console_check(dollars_seen, note)")
        return ""

    def _open_ledger(self, path: Path, replay: bool) -> None:
        self._ledger_fh = _lock_file(path, f"ledger {path} is in use by another guard")
        self._ledger_fh.seek(0)
        data = self._ledger_fh.read()
        self.ledger_path = path
        if not replay:
            if data:
                raise ValueError(f"ledger {path} already has events; use SpendGuard.replay() so earlier "
                                 "spend is not forgotten")
            with self._lock:
                self._write([{"event": "open", "run_cap": str(self.run_cap), "live": self.live,
                              "global_cap": str(self.global_cap), "global_spent": str(self.global_spent),
                              "price_table_date": prices.PRICE_TABLE_DATE}])
            return
        cut = data.rfind(b"\n") + 1
        torn = data[cut:]
        lines = data[:cut].decode("utf-8").splitlines()
        if not lines:
            raise ValueError(f"ledger {path} has no complete line; nothing was reserved, delete it to start")
        with self._lock, prices.money_context():
            for number, raw in enumerate(lines, start=1):
                self._apply(json.loads(raw), number)
            if torn:
                warnings.warn(f"ledger {path}: dropped a torn final line of {len(torn)} bytes")
                self._ledger_fh.truncate(cut)
                self._write([{"event": "torn_line_dropped", "fragment": torn.decode("utf-8", "replace")[:500],
                              "spent": str(self._spent), "reserved": str(self._reserved)}])
            if self._halted and not self._halt_logged:
                self._halt(self.halt_reason, force_log=True)

    def _price(self, items: Iterable[Request]) -> List[Tuple[str, str, Decimal, bool]]:
        priced = []
        keys = set()
        for item in items:
            key, model, est_input_tokens, max_tokens, batch = item
            if not isinstance(key, str) or not key:
                raise ValueError(f"key must be a non-empty string, got {key!r}")
            if key in keys:
                raise ValueError(f"duplicate key {key!r} in one request list")
            keys.add(key)
            if not isinstance(batch, bool):
                raise TypeError(f"batch must be True or False for {key!r}")
            # Batch items at the Batch price (half of list), real-time calls at list. A batch item that
            # were billed at list would cost more than its reservation, and commit() would halt the run.
            priced.append((key, model, prices.worst_case(model, est_input_tokens, max_tokens, batch=batch), batch))
        if not priced:
            raise ValueError("no requests given")
        return priced

    def _remaining(self) -> Tuple[Decimal, Decimal]:
        used = self._spent + self._reserved
        return self.run_cap - used, self.global_cap - self.global_spent - used

    def _check_fits(self, amount: Decimal, what: str) -> None:
        run_left, global_left = self._remaining()
        if amount > run_left:
            raise CapExceeded(f"{what} needs {amount}; only {run_left} left under the run cap {self.run_cap}")
        if amount > global_left:
            raise CapExceeded(f"{what} needs {amount}; only {global_left} left under the global cap")

    def _halt_reason(self, key: str, actual: Decimal, reservation: Decimal, spent: Decimal) -> str:
        """Why a commit of `actual` against `reservation`, bringing run spend to `spent`, halts the run."""
        if actual > reservation:
            return f"{key!r} cost {actual}, more than its reservation {reservation}"
        if spent > self.run_cap:
            return f"spent {spent} is over the run cap {self.run_cap}"
        if self.global_spent + spent > self.global_cap:
            return f"global spend {self.global_spent + spent} is over {self.global_cap}"
        return ""

    def _get_open(self, key: str) -> Reservation:
        if key not in self._open:
            state = self._done.get(key, "never reserved")
            raise KeyError(f"{key!r} has no open reservation ({state})")
        return self._open[key]

    def _halt(self, reason: str, force_log: bool = False) -> None:
        if not self._halted or force_log:
            self._write([{"event": "halt", "reason": reason, "spent": str(self._spent),
                          "reserved": str(self._reserved)}])
            self._halted, self.halt_reason, self._halt_logged = True, reason, True

    def _write(self, events: List[dict]) -> None:
        """Append events to the ledger and fsync, before the caller changes memory."""
        if self._ledger_fh is None:
            self._seq += len(events)
            return
        out = []
        for offset, event in enumerate(events, start=1):
            line = {"seq": self._seq + offset, "run_id": self.run_id, "time": self._now().isoformat()}
            line.update(event)
            out.append(json.dumps(line, sort_keys=True) + "\n")
        self._ledger_fh.write("".join(out).encode("utf-8"))
        self._ledger_fh.flush()
        os.fsync(self._ledger_fh.fileno())
        self._seq += len(events)

    def _apply(self, line: dict, number: int) -> None:
        """Re-apply one ledger line during replay."""
        if line.get("seq") != number or line.get("run_id") != self.run_id:
            raise ValueError(f"ledger line {number}: wrong seq or run_id")
        event, key = line.get("event"), line.get("key")
        if event == "open":
            if number != 1 or Decimal(line["run_cap"]) != self.run_cap or line.get("live") is not self.live:
                raise ValueError("ledger 'open' line is not first, or its run cap or live flag differs")
        elif number == 1:
            raise ValueError("ledger does not start with an 'open' line")
        elif event == "reserve":
            if key in self._open or key in self._done:
                raise ValueError(f"ledger line {number}: duplicate key {key!r}")
            self._open[key] = Reservation(line["model"], Decimal(line["amount"]), line["batch"])
            self._booked[key] = Decimal(line["amount"])
            self._reserved += Decimal(line["amount"])
            if line["batch"] is True:
                self._batch_reserved += Decimal(line["amount"])
        elif event == "send":
            self._get_open(key).sent = True
        elif event == "commit":
            res = self._open.pop(key)
            self._done[key] = "committed"
            self._cost[key] = Decimal(line["amount"])
            self._reserved -= res.amount
            self._spent += Decimal(line["amount"])
            if line.get("batch") is True:
                self._batch_spent += Decimal(line["amount"])
            if line.get("free_by_rule") is True:
                self._free_spent += Decimal(line["amount"])
                if line.get("batch") is True:
                    self._batch_free += Decimal(line["amount"])
            self._commits[key] = {"amount": line["amount"], "batch": line.get("batch") is True,
                                  "usage": line.get("usage"), "_free": line.get("free_by_rule") is True}
            # Recompute the halt from the commit itself (and the caller's halt_reason written with it);
            # never rely on a separate halt line.
            reason = (self._halt_reason(key, Decimal(line["amount"]), res.amount, self._spent)
                      or str(line.get("halt_reason", "")).strip())
            if reason and not self._halted:
                self._halted, self.halt_reason = True, reason
        elif event == "console_check":
            # Passing only if the line says so AND its own figures agree; otherwise a failed check
            # (it halts this run and blocks Batch everywhere until cleared).
            if check_passed(line):
                self._passes.add((self.run_id, number))
            else:
                self._failed_checks.add((self.run_id, number))
                if not self._halted:
                    self._halted, self.halt_reason = True, f"FAILED Console check (ledger line {number})"
        elif event == "console_halt_cleared":
            self._cleared |= {(r, s) for r, s in line.get("clears", [])}
            self._voided |= {(r, s) for r, s in line.get("voids", [])}
        elif event == "release":
            res = self._open.pop(key)
            self._done[key] = "released"
            self._reserved -= res.amount
        elif event == "halt":
            self._halted, self.halt_reason, self._halt_logged = True, line["reason"], True
        elif event == "free_by_rule_marked":
            commit = self._commits.get(key)
            if commit is None or not marker_valid(line, commit):  # this ledger's own: an invalid one is tampering
                raise ValueError(f"ledger line {number}: invalid free_by_rule_marked for {key!r}")
            self._apply_marker(commit)
        elif event not in ("recover", "torn_line_dropped"):
            raise ValueError(f"ledger line {number}: unknown event {event!r}")
        if "spent" in line and (Decimal(line["spent"]) != self._spent
                                or Decimal(line["reserved"]) != self._reserved):
            raise ValueError(f"ledger line {number}: totals do not match the replayed state")
        self._seq = number
