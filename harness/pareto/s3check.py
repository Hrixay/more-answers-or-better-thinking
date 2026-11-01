"""The S3 check Batch: one small Batch that bills enough for the Anthropic Console to show it.

    python3 -m harness.pareto.s3check plan --set SET_DIR
    python3 -m harness.pareto.s3check dry  --set SET_DIR --run-id s3-dry --out DIR
    python3 -m harness.pareto.s3check live --set SET_DIR --run-id ID --cap X --clearance FILE
    python3 -m harness.pareto.s3check live --set SET_DIR --run-id ID --cap X --clearance FILE --collect   (after an interruption)

Why (the agreed plan, S3-PLAN revision 4, Proposal A; the pilot plan's step 2): smoke-2's Batch billed $0.021, under the
Console's $0.05 floor, so the guard's Batch cost could not be compared with the Console. This Batch bills about $0.27 to $0.38
(expected), enough to show, and its worst case (about $0.68 at the Batch price) fits what is left of the guard's $1 limit on
unchecked Batch reservations (machine-wide and cumulative).

What it sends: ONE Batch of 5 requests on the frozen set `smoke3-ledger-l16-v1` (ledger family, 5 base puzzles x 2 shapes),
fixed here in code, in this order:
    1. base 0, 1x24, Opus        2. base 0, 24x1, Opus        3. base 1, 1x24, Opus
    4. base 2, 1x24, Sonnet      5. base 2, 24x1, Sonnet
Every request: effort medium, adaptive thinking (request.build_params), max_tokens 15,000.

The answers are never graded and never printed: S3 items are excluded from every analysis. The summary
(`s3_result.json`) holds counts, kinds, stop reasons, token counts, cost and batch ids, never answer text.

Safeguards:
- the set must be `smoke3-ledger-l16-v1`, family ledger, setting l16, loaded with the deep verify every runner uses;
- `live` needs an explicit --cap and --clearance, goes through live.open_live_guard (the gate, the clearance file, a clean
  checkout, the price date ...) and writes next to its ledger, `<shared data root>/raw/<run-id>/`; --out is refused;
- the 5 requests must fit in ONE wave under the cap, or nothing is sent;
- the Batch goes through batch.run_batches;
- a run folder that already shows a Batch (a submit, a finished item, a reservation for one of these items, or a result
  file with items sent) is never sent again: S3NotRerun. There is no resend flag; the user decides what happens next.
- the one exception is `--collect` (Edith S3-1, S3-3): if the run stopped while waiting for the Batch or while reading its
  results (sleep, shutdown, Ctrl-C, a dropped connection), it COLLECTS that Batch's results, so its cost reaches the
  ledger. It never submits: it goes on only when the call log shows exactly one submitted, uncollected Batch whose keys
  are exactly the five S3 items, no failed submit and no submit without a batch id (an orphan); and it checks afterwards
  that no new submit was logged. Items already read before the stop are skipped, never paid twice (batch.py only
  settles a key that is still open); once the Batch is marked collected, --collect refuses;
- exit code: 0 only when the status is "complete"; 2 for any other status (the summary says why), 3 when the API refused
  the submit, 4 when nothing was sent because the folder already shows the Batch.

This command NEVER records a Console check (Edith N67). After the S3 Batch settles and the Console shows it, the passing
Console check is recorded with `python3 -m harness.pareto.pilot console-check` under the PILOT's own run id, before the pilot's
first wave; a check recorded under the S3 run id does not carry over.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Dict, List, Optional

from .batch import run_batches
from .calllog import CallLog
from .client import check_custom_id
from .manifest import write_manifest
from .pilot import OPUS, SONNET, Item, load_set
from .prices import estimate_input_tokens, worst_case
from .request import build_params, prompt_text

S3_SET_ID = "smoke3-ledger-l16-v1"
S3_FAMILY = "ledger"
S3_SETTING = "l16"
S3_MAX_TOKENS = 15_000
S3_EFFORT = "medium"
RESULT_FILE = "s3_result.json"

# (base puzzle, shape "WxD", model, tag): the five items of Proposal A, in order. Two of the three Opus items are 1x24 (shorter prompt).
S3_ITEMS = ((0, "1x24", OPUS, "om"), (0, "24x1", OPUS, "om"), (1, "1x24", OPUS, "om"),
            (2, "1x24", SONNET, "sm"), (2, "24x1", SONNET, "sm"))

NEXT = ("After the S3 Batch settles and the Console shows it, the passing Console check is recorded with "
        "`python3 -m harness.pareto.pilot console-check` under the PILOT's own run id, before the pilot's first wave; "
        "a check recorded under the S3 run id does not carry over. s3check never records a Console check itself (N67).")


class S3NotRerun(RuntimeError):
    """The S3 Batch was started again in a folder that already shows a Batch: nothing was sent."""


def check_set(man: Dict) -> None:
    """Refuse any set but the one the plan names."""
    if man.get("set_id") != S3_SET_ID:
        raise ValueError(f"the S3 check runs only on {S3_SET_ID!r}, not {man.get('set_id')!r}")
    if man.get("family") != S3_FAMILY:
        raise ValueError(f"the S3 check is for the {S3_FAMILY} family, not {man.get('family')!r}")
    if man.get("setting") != S3_SETTING:
        raise ValueError(f"the S3 check is for setting {S3_SETTING}, not {man.get('setting')!r}")


def build_s3(man: Dict, items: List[Dict]) -> List[Item]:
    """The 5 Batch requests in the fixed order. Each custom_id carries the full item id (Edith N57)."""
    check_set(man)
    by = {(it["base_index"], f"{it['width']}x{it['depth']}"): it for it in items}
    out: List[Item] = []
    for base, shape, model, tag in S3_ITEMS:
        it = by.get((base, shape))
        if it is None:
            raise ValueError(f"the set has no item for base {base}, shape {shape}")
        params = build_params(model, S3_EFFORT, S3_MAX_TOKENS, [{"role": "user", "content": it["prompt"]}])
        cid = f"s3-{it['id']}-{tag}"
        check_custom_id(cid)
        meta = {"set_id": man["set_id"], "item_id": it["id"], "family": man["family"], "setting": man["setting"],
                "base_index": base, "width": it["width"], "depth": it["depth"], "setup": tag, "model": model,
                "effort": S3_EFFORT, "sample": 1, "excluded_from_analysis": True}
        out.append((cid, params, meta))
    return out


def _item_worst_case(params: Dict) -> Decimal:
    """What the guard reserves for this Batch item: the Batch price, prompt tokens from the same upper-bound estimate."""
    return worst_case(params["model"], estimate_input_tokens(prompt_text(params)), params["max_tokens"], batch=True)


def plan(requests: List[Item]) -> Dict[str, object]:
    """The items in order, each item's worst case as the guard reserves it, the total, and the cap to ask for (the total
    rounded up to the next 10 cents; Edith sets the figure)."""
    rows = []
    total = Decimal("0")
    for cid, p, m in requests:
        est = estimate_input_tokens(prompt_text(p))
        wc = _item_worst_case(p)
        total += wc
        rows.append({"custom_id": cid, "base": m["base_index"], "shape": f"{m['width']}x{m['depth']}", "model": p["model"],
                     "effort": p["output_config"]["effort"], "thinking": p["thinking"]["type"],      # type: ignore[index]
                     "max_tokens": p["max_tokens"], "est_input_tokens": est, "worst_case_batch_usd": str(wc)})
    cap = (total * 10).to_integral_value(rounding=ROUND_CEILING) / 10
    return {"set_id": requests[0][2]["set_id"] if requests else None, "batch_requests": len(requests), "items": rows,
            "total_worst_case_batch_usd": str(total), "cap_to_ask_for_usd": str(cap),
            "note": "the worst case counts toward the guard's $1 machine-wide limit on unchecked Batch reservations"}


def _earlier_state(out_dir: Path, log: CallLog, guard, cids: List[str]) -> List[str]:
    """Why this folder already shows a Batch; empty if nothing of it was ever sent or reserved."""
    why: List[str] = []
    finished = sorted(log.finished_ids() & set(cids))
    if finished:
        why.append(f"{len(finished)} finished item(s) in the call log")
    batch_lines = [r for r in log.records() if r.get("kind") in ("batch_submitting", "batch_submitted", "batch_submit_failed")]
    if batch_lines:
        why.append(f"{len(batch_lines)} Batch submit record(s) in the call log")
    keys = sorted(k for k in guard.used_keys() for c in cids if k.startswith(c + "@") or k.startswith(c + "#a"))
    if keys:
        why.append(f"the ledger already holds reservation(s) for {keys[:5]}")
    res = out_dir / RESULT_FILE
    if res.exists():
        try:
            old = json.loads(res.read_text())
        except ValueError:
            old = {"items_sent": "unreadable"}
        if old.get("items_sent") != 0:
            why.append(f"{RESULT_FILE} says items_sent={old.get('items_sent')!r} (status {old.get('status')!r})")
    return why


def _submit_records(log: CallLog) -> List[Dict]:
    return [r for r in log.records() if r.get("kind") in ("batch_submitting", "batch_submitted", "batch_submit_failed")]


def _collectable(log: CallLog, cids: List[str]) -> str:
    """For --collect: "" if the call log shows exactly the state an interruption while polling leaves (one submit, its
    batch id logged, not yet collected, keys exactly the five S3 items). Some items may already have a result (the stop
    came while results were being read, Edith S3-3): run_batches skips them and pays nothing twice. Otherwise why not."""
    recs = _submit_records(log)
    submitting = [r for r in recs if r["kind"] == "batch_submitting"]
    submitted = [r for r in recs if r["kind"] == "batch_submitted"]
    failed = [r for r in recs if r["kind"] == "batch_submit_failed"]
    collected = {r.get("batch_id") for r in log.records() if r.get("kind") == "batch_collected"}
    if not submitting:
        return "no Batch was submitted in this run folder"
    if failed:
        return "a Batch submit failed here (billed unknown); a human must check the Console"
    if len(submitting) != 1 or len(submitted) != 1:
        if len(submitting) > len(submitted):
            return "a Batch submit has no batch id in the log (an orphan; see batch.py adopt_orphan / close_orphan)"
        return f"the log shows {len(submitting)} submit(s) and {len(submitted)} batch id(s), not exactly one"
    sub = submitted[0]
    if sub.get("wave_id") != submitting[0].get("wave_id"):
        return "the batch id in the log belongs to another wave (an orphan)"
    if sub.get("batch_id") in collected:
        return f"Batch {sub.get('batch_id')} was already collected"
    if set(dict(sub.get("keys") or {})) != set(cids):
        return "the submitted Batch does not hold exactly the five S3 items"
    return ""


def _summarise(log: CallLog, requests: List[Item]) -> List[Dict[str, object]]:
    """One row per item from the call log: kind, stop reason, refusal category, output tokens, cost. Never the answer text."""
    last: Dict[str, Dict] = {}
    cids = {c for c, _, _ in requests}
    for r in log.records():
        if r.get("custom_id") in cids:
            last[str(r["custom_id"])] = r
    rows = []
    for cid, p, m in requests:
        r = last.get(cid)
        if r is None:                                   # no result line (not sent, or sent and not collected yet)
            rows.append({"custom_id": cid, "model": p["model"], "shape": f"{m['width']}x{m['depth']}", "kind": "not sent"})
            continue
        usage = r.get("usage_raw") or {}
        rows.append({"custom_id": cid, "model": p["model"], "shape": f"{m['width']}x{m['depth']}", "kind": r.get("kind"),
                     "stop_reason": r.get("stop_reason"), "refusal_category": r.get("refusal_category"),
                     "output_tokens": usage.get("output_tokens") if isinstance(usage, dict) else None,
                     "cost_usd": r.get("cost_usd"), "batch_id": r.get("batch_id")})
    return rows


def run_s3(guard, transport, out_dir: Path, set_dir: Path, poll_s: float = 60.0, sleep=None,
           collect: bool = False) -> Dict[str, object]:
    """Send the S3 Batch once. Returns the summary (also written to `s3_result.json`) with `status`:
    "complete" (all 5 have a result: answered, refused, truncated ...), "not_sent" (the 5 do not fit in one wave under the
    cap), "stopped_for_console_check" (the guard's gate refused the reservation; nothing was sent), or "incomplete" (a cap
    or guard stop, a failed submit, missing or errored items). Raises S3NotRerun, before anything is reserved or sent, if
    the folder already shows a Batch. An interruption while waiting for the Batch writes the summary with status
    "interrupted" and re-raises; `collect=True` then collects that Batch without submitting anything (see the module
    docstring)."""
    from .guard import CapExceeded, GuardHalted
    from .transport import TransportError
    out_dir = Path(out_dir)
    man, items = load_set(set_dir)
    requests = build_s3(man, items)
    cids = [c for c, _, _ in requests]
    log = CallLog(out_dir / "calls.jsonl")
    status, reason = "complete", ""
    batch_ids: List[str] = []
    unbilled: List[str] = []
    missing: List[str] = []
    kw = {"sleep": sleep} if sleep is not None else {}
    if collect:
        return _collect(guard, transport, out_dir, man, requests, log, poll_s, kw)
    before = _earlier_state(out_dir, log, guard, cids)
    if before:
        hint = (" The run stopped while waiting for its Batch: collect it with `live --collect` (same --cap and --clearance)."
                if not _collectable(log, cids) else " There is no resend path: the user decides what happens next.")
        raise S3NotRerun("this run folder already shows the S3 Batch (" + "; ".join(before) + "); nothing is sent again." + hint)
    specs = [(f"{cid}@1", p["model"], estimate_input_tokens(prompt_text(p)), p["max_tokens"], True) for cid, p, _ in requests]
    try:
        waves = guard.plan_waves(specs)                  # CapExceeded if one item alone does not fit
    except (CapExceeded, GuardHalted) as e:
        waves, reason = [], f"{type(e).__name__}: {e}"
    if len(waves) != 1:
        reason = reason or f"the {len(requests)} items need {len(waves)} waves under this cap"
        return _write(out_dir, guard, man, requests, log, "not_sent",
                      f"{reason}; the S3 check is ONE Batch, so nothing was sent (ask for the cap that `plan` prints)", [], [], [])
    if not (out_dir / "manifest.json").exists():
        write_manifest(out_dir, guard, requests, "batch" if transport.live else "dry", note="S3 check Batch (one Batch, 5 items)")
    try:
        s = run_batches(guard, transport, log, requests, poll_s=poll_s, **kw)
        batch_ids, unbilled, missing = list(s.batches), list(s.unbilled_assumed), list(s.missing)
        if s.stopped_for_console_check:
            status, reason = "stopped_for_console_check", "the guard's Console gate refused the Batch reservation; nothing was sent"
        elif unbilled or missing:
            status, reason = "incomplete", f"errored/expired: {unbilled}; no result: {missing}"
    except (CapExceeded, GuardHalted) as e:
        status, reason = "incomplete", f"guard stop: {type(e).__name__}: {e}"
    except TransportError as e:
        status, reason = "incomplete", f"the Batch submit failed: {e.kind} (status {e.status}, billed: {e.billed}); keys stay open"
    except BaseException as e:                          # sleep, shutdown, Ctrl-C, a poll error: record it, then stop
        _write(out_dir, guard, man, requests, log, "interrupted",
               f"{type(e).__name__}: {str(e)[:300]}; if a Batch was submitted, collect it with `live --collect`", [], [], [])
        raise
    return _write(out_dir, guard, man, requests, log, status, reason, batch_ids, unbilled, missing)


def _collect(guard, transport, out_dir: Path, man: Dict, requests: List[Item], log: CallLog, poll_s: float,
             kw: Dict) -> Dict[str, object]:
    """Collect the one Batch an interrupted run left behind. Never submits: refuses unless the log shows exactly that
    state, and raises if a new submit was logged anyway."""
    cids = [c for c, _, _ in requests]
    why = _collectable(log, cids)
    if why:
        raise S3NotRerun(f"nothing to collect: {why}. Nothing was sent.")
    n_before = len(_submit_records(log))
    s = run_batches(guard, transport, log, requests, poll_s=poll_s, **kw)
    if len(_submit_records(log)) != n_before:
        raise RuntimeError("collect logged a new Batch submit; it must never submit. Stop and check the Console.")
    status, reason = "complete", "collected after an interruption"
    if s.unbilled_assumed or s.missing:
        status, reason = "incomplete", f"collected; errored/expired: {s.unbilled_assumed}; no result: {s.missing}"
    return _write(out_dir, guard, man, requests, log, status, reason, list(s.batches), list(s.unbilled_assumed),
                  list(s.missing))


def _write(out_dir: Path, guard, man: Dict, requests: List[Item], log: CallLog, status: str, reason: str,
           batch_ids: List[str], unbilled: List[str], missing: List[str]) -> Dict[str, object]:
    """Build the summary from the call log and write it to `s3_result.json`. Never the answer text."""
    rows = _summarise(log, requests)
    if not batch_ids:
        batch_ids = sorted({str(r["batch_id"]) for r in log.records() if r.get("kind") == "batch_submitted"})
    kinds: Dict[str, int] = {}
    for r in rows:
        kinds[str(r["kind"])] = kinds.get(str(r["kind"]), 0) + 1
    with_result = sum(1 for r in rows if r["kind"] != "not sent")
    submitted = {c for r in log.records() if r.get("kind") == "batch_submitting" for c in dict(r.get("keys") or {})}
    sent = len(submitted & {c for c, _, _ in requests})
    if status == "complete" and with_result != len(requests):
        status, reason = "incomplete", f"only {with_result} of {len(requests)} items have a result"
    summary = {"status": status, "reason": reason, "run_id": guard.run_id, "set_id": man["set_id"],
               "items_planned": len(requests), "items_sent": sent, "items_with_result": with_result, "kinds": kinds,
               "spent_usd": str(guard.spent),
               "worst_case_batch_usd": plan(requests)["total_worst_case_batch_usd"], "batch_ids": batch_ids,
               "unbilled_assumed": unbilled, "missing": missing, "items": rows, "next": NEXT}
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / RESULT_FILE).write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--set", required=True, type=Path, dest="set_dir")
    ap.add_argument("--run-id", default="s3-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required for live (no default); `plan` prints the figure to ask for, Edith sets it")
    ap.add_argument("--clearance", type=Path, help="live only: Edith's clearance JSON for this run id")
    ap.add_argument("--collect", action="store_true",
                    help="collect the Batch an interrupted run left behind; never submits (Edith S3-1)")
    a = ap.parse_args(argv)
    if a.mode == "live":                                   # argument checks first: nothing is loaded or opened before them
        if a.cap is None or a.clearance is None:
            ap.error("live needs an explicit --cap and --clearance")
        if a.out is not None:
            ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/); do not give --out")
    elif a.mode == "dry" and a.out is None:
        ap.error("dry needs --out")
    if a.collect and a.mode == "plan":
        ap.error("--collect goes with live (or dry)")
    from .guard import SpendGuard
    from .transport import DryTransport
    man, items = load_set(a.set_dir)
    requests = build_s3(man, items)                        # refuses a set that is not the S3 set
    if a.mode in ("plan", "dry"):
        print(json.dumps(plan(requests), indent=1))
        if a.mode == "dry":
            guard = SpendGuard(a.run_id, Decimal(a.cap or "1"), global_spent_usd=Decimal("0"))
            try:
                r = run_s3(guard, DryTransport(), a.out, a.set_dir, sleep=lambda s: None, collect=a.collect)
            except S3NotRerun as e:
                print(f"NOT SENT: {e}")
                return 4
            print("dry run done:", json.dumps({k: v for k, v in r.items() if k != "items"}, indent=1))
            return 0 if r["status"] == "complete" else 2
        return 0
    from .live import open_live_guard
    from .transport import RealTransport, TransportError
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        r = run_s3(guard, RealTransport(guard), folder, a.set_dir, collect=a.collect)
        print("S3 check done:", json.dumps({k: v for k, v in r.items() if k != "items"}, indent=1))
        print("NEXT:", NEXT)
        if r["status"] != "complete":
            print(f"NOT COMPLETE: status {r['status']!r}: {r['reason']}")
            return 2
    except S3NotRerun as e:
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
