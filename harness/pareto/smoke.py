"""The smoke run: the smallest paid run that proves the plumbing before the pilot spends real money.

    python3 -m harness.pareto.smoke plan --set SET_DIR
    python3 -m harness.pareto.smoke dry  --set SET_DIR --run-id smoke-dry --out DIR
    python3 -m harness.pareto.smoke live --set SET_DIR --run-id ID --cap 2 --clearance FILE

What it sends (puzzles: the first base puzzle, both shapes, of one pilot digit set; output limit 16,000 tokens for every
model, small on purpose; adaptive thinking, effort medium):
  - 3 REAL-TIME calls, streamed, at list price: Haiku, Sonnet, Opus on the 1x24 chain;
  - 1 small BATCH of 6 requests: Haiku x4 (2 on each shape), Sonnet x1 and Opus x1 on the 24x1 pieces.
What it confirms: the key works; effort, thinking and each model id reach the API and the reply names the model asked for;
the streaming path returns usage (and a request id); a Batch is created, polled and its results parse (result types,
custom_id matching); the guard's cost matches the Console (the human records the Console figure with
`guard.record_console_check`, which the first Batch run needs before any second wave).
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .batch import run_batches
from .calllog import CallLog
from .client import Client, check_custom_id
from .manifest import write_manifest
from .pilot import HAIKU, OPUS, SONNET, Item, load_set
from .prices import estimate_input_tokens, worst_case
from .request import build_params, prompt_text

SMOKE_MAX_TOKENS = 16_000


def _req(it: Dict, man: Dict, model: str, tag: str, k: int) -> Item:
    params = build_params(model, "medium", SMOKE_MAX_TOKENS, [{"role": "user", "content": it["prompt"]}])
    cid = f"smoke-{it['id']}-{tag}-{k:02d}".replace("_", "-")          # the full item id (Edith N57)
    check_custom_id(cid)
    meta = {"set_id": man["set_id"], "item_id": it["id"], "family": man["family"], "setup": tag, "model": model,
            "effort": "medium", "sample": k, "width": it["width"], "depth": it["depth"], "base_index": it["base_index"]}
    return cid, params, meta


def build_smoke(man: Dict, items: List[Dict]) -> Tuple[List[Item], List[Item]]:
    first = sorted([it for it in items if it["base_index"] == 0], key=lambda it: it["width"])
    pieces = [it for it in first if it["depth"] == 1][0]          # 24x1
    chain = [it for it in first if it["depth"] > 1][0]            # 1x24
    realtime = [_req(chain, man, HAIKU, "rth", 1), _req(chain, man, SONNET, "rts", 1), _req(chain, man, OPUS, "rto", 1)]
    batch = ([_req(pieces, man, HAIKU, "bh", k) for k in (1, 2)] + [_req(chain, man, HAIKU, "bh", k) for k in (1, 2)]
             + [_req(pieces, man, SONNET, "bs", 1), _req(pieces, man, OPUS, "bo", 1)])
    return realtime, batch


def plan(realtime: List[Item], batch: List[Item]) -> Dict[str, object]:
    def wc(reqs: List[Item], is_batch: bool) -> Decimal:
        return sum((worst_case(p["model"], estimate_input_tokens(prompt_text(p)), p["max_tokens"], batch=is_batch)
                    for _, p, _ in reqs), Decimal("0"))
    return {"realtime_calls": len(realtime), "realtime_worst_case_list_usd": str(wc(realtime, False)),
            "batch_requests": len(batch), "batch_worst_case_batch_price_usd": str(wc(batch, True)),
            "total_worst_case_usd": str(wc(realtime, False) + wc(batch, True)),
            "models_realtime": [p["model"] for _, p, _ in realtime], "models_batch": sorted({p["model"] for _, p, _ in batch})}


def run_smoke(guard, transport, out_dir: Path, set_dir: Path) -> Dict[str, object]:
    out_dir = Path(out_dir)
    log = CallLog(out_dir / "calls.jsonl")
    man, items = load_set(set_dir)
    realtime, batch = build_smoke(man, items)
    if not (out_dir / "manifest.json").exists():
        write_manifest(out_dir, guard, realtime + batch, "live" if transport.live else "dry", note="smoke run")
    client = Client(guard, transport, log)
    rt_results = []
    done = log.finished_ids()
    for cid, params, meta in realtime:
        if cid in done:                                  # a resumed smoke run never sends a finished call again (Edith U4)
            rt_results.append({"custom_id": cid, "kind": "already done"})
            continue
        out = client.call(cid, params, meta)
        rt_results.append({"custom_id": cid, "kind": out.kind, "returned_model": out.returned_model,
                           "usage": out.usage_raw, "http_request_id": out.http_request_id})
    summary = run_batches(guard, transport, log, batch)
    return {"realtime": rt_results, "batch": summary, "spent_usd": str(guard.spent),
            "next": f"look up what the Console shows for this run, then: python -m harness.pareto.pilot console-check --run-id {guard.run_id} --cap <cap> --clearance <the clearance json> --usd <Console total> --note <where and when>"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--set", required=True, type=Path, dest="set_dir")
    ap.add_argument("--run-id", default="smoke-dry")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--cap", help="dollars; required for live (no default); dry uses 2")
    ap.add_argument("--clearance", type=Path)
    a = ap.parse_args(argv)
    from .guard import SpendGuard
    from .transport import DryTransport
    man, items = load_set(a.set_dir)
    realtime, batch = build_smoke(man, items)
    if a.mode in ("plan", "dry"):
        guard = SpendGuard(a.run_id, Decimal(a.cap or "2"), global_spent_usd=Decimal("0"))
        print(json.dumps(plan(realtime, batch), indent=1))
        if a.mode == "dry":
            if a.out is None:
                ap.error("dry needs --out")
            print("dry run done:", run_smoke(guard, DryTransport(), a.out, a.set_dir))
        return 0
    if a.cap is None or a.clearance is None:
        ap.error("live needs an explicit --cap and --clearance")
    if a.out is not None:
        ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/); do not give --out")
    from .live import open_live_guard
    from .transport import RealTransport, TransportError
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        transport = RealTransport(guard)
        print("live run done:", run_smoke(guard, transport, folder, a.set_dir))
    except TransportError as e:
        print(f"STOPPED: the API did not accept a call ({e.kind}, status {e.status}, billed: {e.billed}). Nothing further was sent. "
              "Look at the call log and the ledger before running again; a call rejected before running is sent again on resume.")
        return 3
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
