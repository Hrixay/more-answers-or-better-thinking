"""The one pre-planned API check (D-57): can Opus and Sonnet answer the ledger family on the API without a refusal?

    python3 -m harness.pareto.apicheck plan --set SET_DIR
    python3 -m harness.pareto.apicheck dry  --set SET_DIR --run-id check-dry --out DIR
    python3 -m harness.pareto.apicheck live --set SET_DIR --run-id ID --cap 11 --clearance FILE

What it sends (Karen's design, `research/task-families-noncipher.md` §4; Edith's C1/C2; D-57, D-58, D-60): 5 base puzzles x 2 shapes
= 10 items of ONE frozen ledger set (a separate set id that is never used again), Opus-medium x1 and Sonnet-medium x1 on each item,
20 calls, REAL TIME, ONE CALL AT A TIME, in this fixed order, cycling through the 5 base puzzles:
    Opus 24x1, Opus 1x24, Sonnet 24x1, Sonnet 1x24   (base puzzle 0), then the same four for base puzzle 1, and so on.
Stop rule, fixed in advance: at the FIRST refusal of any category the check stops. No rewording, no retry, no other family in the same
session. The result is reported whatever it is.

How other stops count (D-60 / Edith C2):
- an API error (429, 5xx, a timeout) is retried by the harness's own rules (Client.call: 429/5xx up to 3 attempts, each reserved and
  logged) and is NOT a refusal; a call that still has no outcome after those rules ends the check as INCOMPLETE;
- a guard or cap stop (CapExceeded, GuardHalted) ends the check as INCOMPLETE, reported as such;
- an answer that is wrong, truncated or unparseable is NOT a stop: it is logged and the check goes on (this check asks about
  refusals, not accuracy).

A run that is started again:
- if the call log or check_result.json of that run already holds a REFUSAL, nothing is sent, ever (D-57, D-58 as amended by D-63);
  there is no flag for this;
- if it holds finished calls but no refusal, nothing is sent unless `--resume-incomplete` is given, and then only when the earlier
  result was "incomplete" (D-60); a check that finished ("complete") is never re-run.

Needs its own clearance from Edith (cap about $11, D-64: the 20 calls' worst case at max_tokens 32K is about $10.2 at list, and
the guard books the worst case before each call) and the user's go. Real time only, so the Batch Console gate is not involved.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .calllog import CallLog
from .client import Client, check_custom_id
from .guard import CapExceeded, GuardHalted
from .outcome import ModelMismatch
from .limits import pilot_max_tokens
from .manifest import write_manifest
from .pilot import OPUS, SONNET, Item, load_set
from .prices import estimate_input_tokens, worst_case
from .request import build_params, prompt_text
from .transport import TransportError

N_BASE = 5
ORDER = ((OPUS, 24, "om"), (OPUS, 1, "om"), (SONNET, 24, "sm"), (SONNET, 1, "sm"))      # (model, width, tag): 24x1 then 1x24 per model


def build_check(man: Dict, items: List[Dict]) -> List[Item]:
    """The 20 requests in the fixed order."""
    if man["family"] != "ledger":
        raise ValueError("the check is for the ledger family")
    by = {(it["base_index"], it["width"]): it for it in items}
    bases = sorted({it["base_index"] for it in items})
    if len(bases) != N_BASE:
        raise ValueError(f"the check set must hold exactly {N_BASE} base puzzles, found {len(bases)}")
    out: List[Item] = []
    for b in bases:
        for model, width, tag in ORDER:
            it = by[(b, width)]
            params = build_params(model, "medium", pilot_max_tokens("ledger", model), [{"role": "user", "content": it["prompt"]}])
            cid = f"check-{it['id']}-{tag}"
            check_custom_id(cid)
            meta = {"set_id": man["set_id"], "item_id": it["id"], "family": "ledger", "setting": man["setting"], "base_index": b,
                    "width": it["width"], "depth": it["depth"], "setup": tag, "model": model, "effort": "medium", "sample": 1}
            out.append((cid, params, meta))
    return out


def plan(requests: List[Item]) -> Dict[str, object]:
    total = sum((worst_case(p["model"], estimate_input_tokens(prompt_text(p)), p["max_tokens"]) for _, p, _ in requests), Decimal("0"))
    return {"calls": len(requests), "order": [(m["setup"], f"{m['width']}x{m['depth']}", m["base_index"]) for _, _, m in requests],
            "worst_case_list_usd": str(total), "cap_to_ask_for_usd": "11"}


class CheckNotRerun(RuntimeError):
    """The check was started again where it must not be: nothing was sent."""


def _earlier_state(out_dir: Path, log: CallLog) -> Dict[str, object]:
    """What a previous run in this folder left: whether any call was refused, how many calls finished, and the old status."""
    refused = any(r.get("kind") == "refusal" or r.get("stop_reason") == "refusal" for r in log.records())
    status = ""
    res = out_dir / "check_result.json"
    if res.exists():
        try:
            old = json.loads(res.read_text())
        except ValueError:
            old = {}
        status = str(old.get("status", ""))
        refused = refused or status == "stopped_at_refusal" or int(old.get("refusals", 0) or 0) > 0
    return {"refused": refused, "finished": len(log.finished_ids()), "status": status}


def run_check(guard, transport, out_dir: Path, set_dir: Path, resume_incomplete: bool = False) -> Dict[str, object]:
    """Send the 20 calls one at a time. Returns a result dict with `status`: "complete" (all 20 answered or failed without
    refusal), "stopped_at_refusal", or "incomplete" (API error after retries, guard or cap stop, model mismatch).

    Started again in a folder with an earlier run: raises CheckNotRerun BEFORE any call if that run holds a refusal (never
    allowed), or holds finished calls and `resume_incomplete` is not set, or was not "incomplete"."""
    out_dir = Path(out_dir)
    log = CallLog(out_dir / "calls.jsonl")
    before = _earlier_state(out_dir, log)
    if before["refused"]:
        raise CheckNotRerun("an earlier run of this check was refused; nothing is sent again (D-57/D-58/D-63)")
    if before["finished"] and not resume_incomplete:
        raise CheckNotRerun(f"this folder already holds {before['finished']} finished calls; a resume needs --resume-incomplete (D-60)")
    if before["finished"] and before["status"] != "incomplete":
        raise CheckNotRerun(f"the earlier result was {before['status'] or 'not recorded'!r}, not 'incomplete'; nothing is resumed")
    man, items = load_set(set_dir)
    requests = build_check(man, items)
    if not (out_dir / "manifest.json").exists():
        write_manifest(out_dir, guard, requests, "live" if transport.live else "dry", note="the one pre-planned API check (D-57)")
    client = Client(guard, transport, log)
    done = log.finished_ids()
    results: List[Dict[str, object]] = []
    status, reason = "complete", ""
    for cid, params, meta in requests:
        if cid in done:
            results.append({"custom_id": cid, "kind": "already done"})
            continue
        try:
            out = client.call(cid, params, meta)
        except (CapExceeded, GuardHalted) as e:
            status, reason = "incomplete", f"guard stop: {type(e).__name__}: {e}"
            break
        except ModelMismatch as e:
            status, reason = "incomplete", f"model mismatch (the guard is halted): {e}"
            break
        except TransportError as e:
            status, reason = "incomplete", f"API error after the retry rules: {e.kind} (status {e.status}, billed: {e.billed})"
            break
        results.append({"custom_id": cid, "model": params["model"], "shape": f"{meta['width']}x{meta['depth']}", "kind": out.kind,
                        "stop_reason": out.stop_reason, "refusal_category": out.refusal_category,
                        "output_tokens": out.usage.output_tokens})
        if out.kind == "refusal":
            status, reason = "stopped_at_refusal", f"refused: {cid} (category {out.refusal_category or 'none'})"
            break
    sent = [r for r in results if r.get("kind") != "already done"]
    summary = {"status": status, "reason": reason, "calls_planned": len(requests), "calls_made": len(sent),
               "answered": sum(1 for r in sent if r["kind"] == "answered"),
               "other_failures": sum(1 for r in sent if r["kind"] not in ("answered", "refusal")),
               "refusals": sum(1 for r in sent if r["kind"] == "refusal"), "spent_usd": str(guard.spent), "results": results}
    (out_dir / "check_result.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--set", required=True, type=Path, dest="set_dir")
    ap.add_argument("--run-id", default="check-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required for live (no default); about 11 per D-64, Edith sets the figure")
    ap.add_argument("--resume-incomplete", action="store_true", help="resume a run whose earlier result was 'incomplete' (never after a refusal)")
    ap.add_argument("--clearance", type=Path)
    a = ap.parse_args(argv)
    from .guard import SpendGuard
    from .transport import DryTransport
    man, items = load_set(a.set_dir)
    requests = build_check(man, items)
    if a.mode in ("plan", "dry"):
        print(json.dumps(plan(requests), indent=1))
        if a.mode == "dry":
            if a.out is None:
                ap.error("dry needs --out")
            guard = SpendGuard(a.run_id, Decimal(a.cap or "11"), global_spent_usd=Decimal("0"))
            r = run_check(guard, DryTransport(), a.out, a.set_dir, a.resume_incomplete)
            print("dry run done:", {k: v for k, v in r.items() if k != "results"})
        return 0
    if a.cap is None or a.clearance is None:
        ap.error("live needs an explicit --cap and --clearance")
    if a.out is not None:
        ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/); do not give --out")
    from .live import open_live_guard
    from .transport import RealTransport
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        r = run_check(guard, RealTransport(guard), folder, a.set_dir, a.resume_incomplete)
        print("check done:", {k: v for k, v in r.items() if k != "results"})
    except CheckNotRerun as e:
        print(f"NOT SENT: {e}")
        return 4
    except TransportError as e:
        print(f"STOPPED: the API did not accept a call ({e.kind}, status {e.status}, billed: {e.billed}). Nothing further was sent.")
        return 3
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
