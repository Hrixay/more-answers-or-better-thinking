"""Mark an earlier run's free refusals in its ledger (Edith's P3, ruling D-65): bookkeeping only, no API call, no new spend.

    python3 -m harness.pareto.markers plan  --run-id smoke-2
    python3 -m harness.pareto.markers apply --run-id smoke-2 --cap 2 --clearance FILE

smoke-2 was written before the guard had `free_by_rule`, so its two zero-output `cyber` refusals (the real-time Opus call and the
Batch Opus call) sit in the ledger as ordinary spend, and the Console check (which compares the Console total with the ledger MINUS the
free refusals) would be off by their cost. `apply` appends one `free_by_rule_marked` event per call (append-only; nothing already
written changes) through `SpendGuard.mark_free_by_rule`, which itself refuses anything that is not a refusal before any output in a
category billing rule B5 makes free. `plan` only reads: it lists the calls that would be marked and the evidence from the call log.

A call is a candidate only when ALL of these hold: the call log has a refusal record for it with a B5-free category (cyber,
general_harms, none) and zero output tokens; the ledger has a commit under the matching guard key (`<custom_id>#a<attempt>` for a
real-time call, `<custom_id>@<attempt>` for a Batch item) that reported zero output tokens and is not free already.
`apply` needs Edith's marker-only clearance and the user's yes (D-65); it never sends anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from .calllog import CallLog
from .guard import B5_FREE_CATEGORIES, REPO_ROOT, git_runner_for, ledger_path_for, shared_data_root


def guard_key(rec: Dict[str, object]) -> str:
    cid, attempt = str(rec["custom_id"]), rec.get("attempt", 1)
    return f"{cid}@{attempt}" if rec.get("mode") == "batch" else f"{cid}#a{attempt}"


def candidates(ledger: Path, calls: Path) -> List[Dict[str, object]]:
    """The free refusals of a run that its ledger does not yet mark. Reads only."""
    commits: Dict[str, dict] = {}
    marked = set()
    for ln in Path(ledger).read_text().splitlines():
        if not ln.strip():
            continue
        d = json.loads(ln)
        if d.get("event") == "commit":
            commits[d["key"]] = d
        elif d.get("event") == "free_by_rule_marked":
            marked.add(d["key"])
    out: List[Dict[str, object]] = []
    for rec in CallLog(calls).records():
        if rec.get("kind") != "refusal" or rec.get("refusal_category") not in B5_FREE_CATEGORIES:
            continue
        key = guard_key(rec)
        c = commits.get(key)
        if c is None or key in marked or c.get("free_by_rule") is True or c.get("usage", {}).get("output_tokens") != 0:
            continue
        if (rec.get("usage_raw") or {}).get("output_tokens", 0) not in (0, None):
            continue
        note = (f"call log {Path(calls).name}: custom_id {rec['custom_id']} attempt {rec.get('attempt', 1)} mode {rec.get('mode')}, "
                f"stop_reason {rec.get('stop_reason')}, refusal_category {rec.get('refusal_category')}, 0 output tokens, "
                f"request id {rec.get('request_id') or rec.get('http_request_id')}; billing rule B5: a {rec.get('refusal_category')} "
                f"refusal before any output is not billed")
        out.append({"key": key, "category": rec["refusal_category"], "amount": Decimal(c["amount"]), "note": note})
    return out


def _paths(run_id: str):
    root = shared_data_root(REPO_ROOT, git_runner_for(REPO_ROOT))
    ledger = ledger_path_for(root, run_id)
    return ledger, ledger.parent / "calls.jsonl"


def apply_markers(guard, cands: List[Dict[str, object]]) -> Decimal:
    """Append a marker for each candidate through the live guard. Returns the total marked."""
    total = Decimal("0")
    for c in cands:
        total += guard.mark_free_by_rule(str(c["key"]), str(c["category"]), str(c["note"]))
    return total


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "apply"))
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--cap", help="the run's cap in dollars, as in its clearance (apply only)")
    ap.add_argument("--clearance", type=Path, help="Edith's marker-only clearance (apply only)")
    a = ap.parse_args(argv)
    ledger, calls = _paths(a.run_id)
    cands = candidates(ledger, calls)
    for c in cands:
        print(f"{c['key']}  {c['category']}  ${c['amount']}")
    print(f"{len(cands)} call(s) to mark, ${sum((c['amount'] for c in cands), Decimal('0'))} in all")
    if a.mode == "plan":
        return 0
    if a.cap is None or a.clearance is None:
        ap.error("apply needs --cap and --clearance")
    from .live import open_live_guard
    guard, _ = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        before = guard.rule_adjusted_spent
        total = apply_markers(guard, cands)
        print(f"marked {len(cands)} call(s), ${total}. Spend unchanged at ${guard.spent}; rule-adjusted spend ${before} -> ${guard.rule_adjusted_spent}")
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
