"""Shared helpers for the harness tests. Offline only."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import mkdtemp

from harness.pareto import prices
from harness.pareto.calllog import CallLog
from harness.pareto.guard import SpendGuard
from harness.pareto.request import build_params


def reply(model="claude-haiku-5-5", text="Answer: 1 = 5", stop="end_turn", category=None, tin=100, tout=50,
          cache_read=0, cache_write=0, mid="msg_1"):
    d = {"id": mid, "type": "message", "role": "assistant", "model": model, "stop_reason": stop,
         "content": [{"type": "text", "text": text}] if text is not None else [],
         "stop_details": {"type": "refusal", "category": category} if category else None,
         "usage": {"input_tokens": tin, "output_tokens": tout, "cache_read_input_tokens": cache_read,
                   "cache_creation_input_tokens": cache_write}}
    return d


def params(model="claude-haiku-5-5", effort="medium", max_tokens=1000, text="What is 2+2?", thinking_off=False):
    return build_params(model, effort, max_tokens, [{"role": "user", "content": text}], thinking_off=thinking_off)


def guard(run_cap="10", global_cap="200", spent="0", live=False, **kw):
    return SpendGuard(run_id="test-run", run_cap_usd=Decimal(run_cap), global_cap_usd=Decimal(global_cap),
                      global_spent_usd=Decimal(spent), live=live, **kw)


def tmplog():
    d = Path(mkdtemp())
    return CallLog(d / "calls.jsonl")


def _noon(day: str) -> datetime:
    """Noon UTC on `day`: the live tests' clock sits on the price table's own date, so they keep working when the date moves on."""
    return datetime.fromisoformat(day).replace(hour=12, tzinfo=timezone.utc)


def _day_after(day: str) -> str:
    return (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()


class LiveEnv:
    """A temporary repo root (spend log, review file, data folder) and a stubbed git, so a LIVE guard can be built in a
    test without touching the real repo's data/raw. Never sends anything: it only builds guards."""

    def __init__(self, run_id="live-test", cap="30"):
        self.root = Path(mkdtemp())
        self.run_id, self.cap = run_id, cap
        (self.root / "ops" / "reviews").mkdir(parents=True)
        (self.root / "ops" / "spend-log.md").write_text(
            "| Credit | 200.00 |\n| Spent (rows below) | 0.00 |\n\n"
            "| Date | Chat | Run ID | What ran | Calls | Tokens in / out / cache | USD (computed) | Console check | Notes |\n"
            "|---|---|---|---|---|---|---|---|---|\n")
        self.review = "ops/reviews/clearance-test.md"
        self.data = self.root / "data"
        # The exact CLEARED line, from column 0: run, commit and the ledger root (guard round 3, T5/T7).
        (self.root / self.review).write_text(
            f"Clearance for run {run_id}.\nCLEARED: {run_id} abc1234 {self.data.resolve()}\n")
        self.clearance_path = self.root / "clearance.json"

    def write_clearance(self):
        self.clearance_path.write_text(json.dumps({
            "run_id": self.run_id, "cap_usd": self.cap, "edith_clearance": self.review, "user_go": "go: test",
            "git_commit": "abc1234", "price_table_date": prices.PRICE_TABLE_DATE, "expires": _day_after(prices.PRICE_TABLE_DATE),
            "ledger_root": str(self.data.resolve()),
            "env_file": str(self.data.resolve().parent / ".env")}))  # T6: the main checkout's .env; never created

    def guard(self, cleared=True):
        if cleared:
            self.write_clearance()
        g = SpendGuard(self.run_id, Decimal(self.cap), live=True, repo_root=self.root, data_root=self.data,
                       clearance_path=self.clearance_path if cleared else None,
                       git=lambda args: "abc1234\n" if args[0] == "rev-parse" else "",
                       now=lambda: _noon(prices.PRICE_TABLE_DATE))
        return g
