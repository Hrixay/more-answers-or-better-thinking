"""Opening a LIVE guard for a run, and the Console check, shared by the smoke run and the pilot commands.

A live run's ledger lives at one machine-wide place, `<shared data root>/raw/<run_id>/ledger.jsonl` (guard.py). If that ledger
already has events the guard is REPLAYED, not created again: the pilot stops after its first Batch wave on purpose (the Console
check), and the next command must pick up exactly where the ledger left off. The run's output folder (call log, manifest, compact
table) is the ledger's own folder, so everything of one run sits together.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple

from .guard import REPO_ROOT, SpendGuard, git_runner_for, ledger_path_for, shared_data_root


def run_folder(run_id: str, data_root: Optional[Path] = None) -> Path:
    root = Path(data_root) if data_root is not None else shared_data_root(REPO_ROOT, git_runner_for(REPO_ROOT))
    return ledger_path_for(root, run_id).parent


def open_live_guard(run_id: str, cap: Decimal, clearance: Path, **roots) -> Tuple[SpendGuard, Path]:
    """(guard, output folder). Replays an existing ledger, otherwise starts a new one. `roots` (data_root, repo_root, git,
    now) are for tests."""
    folder = run_folder(run_id, roots.get("data_root"))
    ledger = folder / "ledger.jsonl"
    if ledger.exists() and ledger.stat().st_size > 0:
        guard = SpendGuard.replay(ledger, run_id, cap, live=True, clearance_path=clearance, **roots)
    else:
        guard = SpendGuard(run_id, cap, live=True, clearance_path=clearance, **roots)
    return guard, folder


def record_console_check(run_id: str, cap: Decimal, clearance: Path, usd: Decimal, note: str, roots: Optional[dict] = None,
                         **kw) -> None:
    """Record what the Anthropic Console shows for this run so far (Edith R10/T1). The guard decides whether the figure is
    acceptable and halts the run if the Console shows clearly more than the ledger."""
    guard, _ = open_live_guard(run_id, cap, clearance, **(roots or {}))
    try:
        guard.require_live()          # an expired or uncleared clearance must not let anyone write a check (Edith U5)
        guard.record_console_check(usd, note, **kw)
    finally:
        guard.close()


def clear_console_block(run_id: str, cap: Decimal, clearance: Path, note: str, roots: Optional[dict] = None):
    """A failed Console check blocks every live Batch reservation on the machine until a human clears it (Edith U1). This calls the
    guard's `clear_console_block(note)` after `require_live()`. It does not un-halt the run that failed and it does not open the
    gate: a new passing check is still needed for anything over the guard's $1 unchecked-Batch limit."""
    guard, _ = open_live_guard(run_id, cap, clearance, **(roots or {}))
    try:
        guard.require_live()
        return guard.clear_console_block(note)
    finally:
        guard.close()
