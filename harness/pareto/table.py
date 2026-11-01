"""The compact per-call table (D-37): what goes in git, built from the raw log that stays on this machine.

One row per final call: custom_id, model, effort, thinking, mode, token counts, cost, outcome kind, refusal category,
and `right` (1 / 0 / blank when not graded; for a ledger set it is the official D-76 score, from pilot.grader). The raw log (`data/raw/<run-id>/calls.jsonl`, git-ignored) keeps the answer
text, request ids and everything else. Grading is passed in as a function so this file knows nothing about the task
families: `grade(record) -> True / False / None`.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Optional

from .calllog import CallLog

COLUMNS = ["custom_id", "run_id", "mode", "requested_model", "returned_model", "effort", "thinking", "max_tokens",
           "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "cost_usd", "kind",
           "stop_reason", "refusal_category", "refusal_billed_by_rule", "latency_s", "batch_id", "right"]


def compact_rows(log: CallLog, grade: Optional[Callable[[Dict[str, object]], Optional[bool]]] = None):
    for r in log.records():
        if not r.get("final") or "requested_model" not in r:
            continue
        u = r.get("usage_raw") or {}
        right = grade(r) if grade is not None and r.get("kind") == "answered" else None
        yield {
            "custom_id": r["custom_id"], "run_id": r.get("run_id"), "mode": r.get("mode"),
            "requested_model": r.get("requested_model"), "returned_model": r.get("returned_model"),
            "effort": r.get("effort"), "thinking": r.get("thinking"), "max_tokens": r.get("max_tokens"),
            "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),  # type: ignore[union-attr]
            "cache_read_tokens": u.get("cache_read_input_tokens"), "cache_write_tokens": u.get("cache_creation_input_tokens"),  # type: ignore[union-attr]
            "cost_usd": r.get("cost_usd"), "kind": r.get("kind"), "stop_reason": r.get("stop_reason"),
            "refusal_category": r.get("refusal_category"),
            "refusal_billed_by_rule": r.get("refusal_billed_by_rule"), "latency_s": r.get("latency_s"), "batch_id": r.get("batch_id"),
            "right": "" if right is None else int(bool(right)),
        }


def write_compact_table(log: CallLog, out_csv: Path, grade=None) -> Decimal:
    """Write the table and return the total of cost_usd over its rows (for a check against the guard's spent)."""
    total = Decimal("0")
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in compact_rows(log, grade):
            if row["cost_usd"] is not None:
                total += Decimal(str(row["cost_usd"]))
            w.writerow(row)
    return total


SAFETY_WORDS = ("safety", "policy", "safeguard", "classifier", "refus")


def is_block(r: Dict[str, object]) -> bool:
    """D-31: a block is a refusal stop, or an error that names a safety or policy reason."""
    if r.get("kind") == "refusal":
        return True
    if r.get("kind") == "error":
        err = r.get("error") or {}
        text = (str(err.get("type", "")) + " " + str(err.get("message", ""))).lower()  # type: ignore[union-attr]
        return any(w in text for w in SAFETY_WORDS)
    return False


def block_rates(log: CallLog) -> Dict[str, Dict[str, object]]:
    """Per requested model: final calls, blocked calls and the blocked share (D-31 / D-36: a refusal stop or an error that
    names a safety or policy reason; D-36 switches a model to the answer-only prompt when its share passes 2%). Counts by
    category (`error:<type>` for errors). Only reports; the switch is a decision."""
    out: Dict[str, Dict[str, object]] = {}
    for r in log.records():
        if not r.get("final") or "requested_model" not in r:
            continue
        m = out.setdefault(str(r["requested_model"]), {"calls": 0, "blocked": 0, "categories": {}})
        m["calls"] += 1  # type: ignore[operator]
        if is_block(r):
            m["blocked"] += 1  # type: ignore[operator]
            cat = str(r.get("refusal_category")) if r.get("kind") == "refusal" else "error:" + str((r.get("error") or {}).get("type"))  # type: ignore[union-attr]
            m["categories"][cat] = m["categories"].get(cat, 0) + 1  # type: ignore[index,attr-defined]
    for m in out.values():
        m["blocked_share"] = (m["blocked"] / m["calls"]) if m["calls"] else 0.0  # type: ignore[operator]
        m["over_2_percent"] = m["blocked_share"] > 0.02  # type: ignore[operator]
    return out
