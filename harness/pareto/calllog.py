"""The call log: one JSON line per attempt, written even when the call fails or is refused.

`data/raw/<run-id>/calls.jsonl` holds, for every attempt: when, the model requested and returned, effort and thinking
setting, a hash of the whole request, the prompt hash, the custom_id and attempt number, batch / real-time / dry run,
the usage object exactly as returned (so offline re-pricing survives a field nobody foresaw), the cost, stop reason and
refusal category, the visible answer text, latency, and any error. Nothing here ever records a key or a header.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict, Iterator, Set


class CallLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, record: Dict[str, object]) -> None:
        line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self.path, "a") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())

    def records(self) -> Iterator[Dict[str, object]]:
        if not self.path.exists():
            return
        with open(self.path) as f:
            for ln in f:
                if ln.strip():
                    yield json.loads(ln)

    def finished_ids(self) -> Set[str]:
        """custom_ids that already have a final result (an answer, a refusal, a truncation ...). A resumed run must
        never send these again."""
        return {r["custom_id"] for r in self.records() if r.get("final")}  # type: ignore[misc]

    def attempts(self, custom_id: str) -> int:
        """How many single-call attempts of this custom_id are already logged (their guard keys are used up)."""
        return sum(1 for r in self.records() if r.get("custom_id") == custom_id and "attempt" in r)
