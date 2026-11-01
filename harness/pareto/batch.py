"""Batch runs: the same rules as `client.py`, in waves, keyed by custom_id, resumable.

- Waves: `guard.plan_waves` splits the run into consecutive groups whose worst-case reservations fit under the caps. Only
  the FIRST wave of each plan is run; then the plan is made again against the room that is really left (reservations
  are released and spend is committed as results come in), so the run goes as sequential batches.
- Items whose keys are still open (a failed submit, a missing result) are NOT sent again unless `resend=True`.
- Order of one wave: reserve all (all or nothing) -> mark all sent (all or nothing) -> log `batch_submitting` (the keys,
  BEFORE the call) -> submit -> log `batch_submitted` (the batch id, BEFORE polling). A failed submit logs
  `batch_submit_failed` (billed unknown) and re-raises; the keys stay open and counted.
- A crash between `batch_submitting` and `batch_submitted` leaves an ORPHANED batch: it may exist at Anthropic with no
  id in our log. `run_batches` refuses to go on (OrphanedBatch). A human finds out (the SDK's
  `client.messages.batches.list()` or the Console) and then calls ONE of two helpers in this module: `adopt_orphan(log,
  wave_id, batch_id)` if the batch exists (the next run collects it), or `close_orphan(guard, log, wave_id, note)` if
  none exists (it commits zero usage for each key with the note, because a sent key cannot be released, and writes the
  resolving record; the items can then be sent again under new keys).
- A crash after `batch_submitted` resumes by collecting that batch; it never submits those requests twice. Results
  already committed (guard key no longer open) are skipped, so a crash half-way through collecting is safe. A call of
  `run_batches` settles only the unsettled batches that hold ITS items: the main runner's single-call waves and E3's rounds
  share one call log, and each leaves the other's batches to their own runner (listed in `left_for_their_runner`).
- Reading a batch (status, results) retries a dropped connection, a timeout, 429 or 5xx with backoff (`_read`: 30 s doubling,
  capped at 15 min, 8 tries); a read is never billed and nothing is ever re-submitted on a retry. The results are fetched whole
  before any is recorded. After the last try it raises; the same command run again resumes.
- `pause_truncated_over` (the main runner passes 2%): every settled batch of a call's items, including one settled on a resume, is
  checked once (`check_wave`, driven by the log: a `truncation_checked` or `paused_for_truncation` line per batch), before anything new
  is submitted. A setup whose truncated share in that batch is over the threshold pauses the run before the next wave; a later call
  refuses (`PausedForTruncation`) until `release_pause(log, run_id, note)` records the user's ruling. `waive_pause(log, run_id, note)`
  (the user ruled the pause off) turns the check off for the rest of the run.
- Results come back in any order and are matched to requests by custom_id, never by position.
- Per result: succeeded -> normalised, committed at Batch prices, logged (a refusal or truncation is still a billed
  failed call, as in real-time). errored / canceled / expired -> committed with zero usage (the guard does not allow a
  release once a call is marked sent), logged, and listed in the run summary for a Console reconciliation. Anthropic's
  batch docs say errored, canceled and expired requests are not billed (Karen, research/facts-checked.md B-rows); the
  reconciliation is the check that the docs held. An item that errored is NOT retried in the same call of
  `run_batches`; a later call sends it again under a new key. A request with no result at all stays reserved (counted
  as spent) and is listed as missing.
- Guard keys are `<custom_id>@<n>`, n the smallest number the guard has not used (the guard never reuses a key).
- A live guard must go with the real transport and a dry guard with the dry/fake one.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .calllog import CallLog
from .client import build_record, check_custom_id, settle
from .guard import ConsoleCheckNeeded
from .outcome import Outcome, normalize
from .prices import Usage, estimate_input_tokens
from .request import assert_clean, prompt_text
from .transport import Transport

Item = Tuple[str, Dict[str, object], Dict[str, object]]      # (custom_id, params, meta)


@dataclass
class BatchSummary:
    batches: List[str] = field(default_factory=list)
    answered: int = 0
    failed: int = 0                                           # refusals, truncations, empty, unexpected stop
    unbilled_assumed: List[str] = field(default_factory=list)  # errored / canceled / expired custom_ids
    missing: List[str] = field(default_factory=list)          # submitted, no result came back
    skipped_already_done: int = 0
    stopped_for_console_check: bool = False                    # the first live Batch run, after its first wave (R10)
    left_for_their_runner: List[str] = field(default_factory=list)  # unsettled batches of OTHER items (e.g. an E3 round): not touched here
    paused_for_truncation: Dict[str, float] = field(default_factory=dict)  # setup -> truncated share of the wave that tripped the pause


class OrphanedBatch(RuntimeError):
    """A `batch_submitting` record has no `batch_submitted` or `batch_submit_failed` after it: see the module docstring."""


class PausedForTruncation(RuntimeError):
    """A run paused by `pause_truncated_over` and not yet released: a human must look, then release it with a note."""


def pause_state(log: CallLog) -> Optional[Dict[str, object]]:
    """The last truncation pause in the log that has no later release, or None."""
    state = None
    for r in log.records():
        if r.get("kind") == "paused_for_truncation":
            state = r
        elif r.get("kind") == "pause_released":
            state = None
    return state


def release_pause(log: CallLog, run_id: str, note: str) -> None:
    """Record that a human looked at the truncation pause and the user ruled to go on (the note says who and what)."""
    if not note.strip():
        raise ValueError("releasing a truncation pause needs a note")
    log.write({"kind": "pause_released", "run_id": run_id, "note": note, "final": False})


def waive_pause(log: CallLog, run_id: str, note: str) -> None:
    """The user's ruling to run without the truncation pause (`--truncation-pause-off`): a `truncation_pause_waived` line with the note;
    from then on no wave is checked against the threshold. A pending pause is released with the same note."""
    if not note.strip():
        raise ValueError("waiving the truncation pause needs a note (the user's ruling)")
    log.write({"kind": "truncation_pause_waived", "run_id": run_id, "note": note, "final": False})
    if pause_state(log) is not None:
        release_pause(log, run_id, note)


def pause_waived(log: CallLog) -> bool:
    return any(r.get("kind") == "truncation_pause_waived" for r in log.records())


def check_wave(log: CallLog, run_id: str, batch_id: str, threshold: float) -> Dict[str, float]:
    """Idempotent and driven by the log (Edith, resume fix R-1): a settled batch with no `truncation_checked` or
    `paused_for_truncation` line gets one now. Returns {setup: share} of the setups over the threshold (empty when it passes or
    was already checked)."""
    for r in log.records():
        if r.get("batch_id") == batch_id and r.get("kind") in ("truncation_checked", "paused_for_truncation"):
            return {}
    shares = wave_truncation(log, batch_id)
    over = {su: v for su, v in shares.items() if v > threshold}
    log.write({"kind": "paused_for_truncation" if over else "truncation_checked", "run_id": run_id, "batch_id": batch_id,
               "shares": shares, "over": over, "threshold": threshold, "final": False})
    return over


def _collected_batches_of(log: CallLog, own: set) -> List[str]:
    """The collected batches whose keys are all among `own`, in log order."""
    keys: Dict[str, set] = {}
    out: List[str] = []
    for r in log.records():
        if r.get("kind") == "batch_submitted":
            keys[str(r["batch_id"])] = set(r["keys"])                     # type: ignore[arg-type]
        elif r.get("kind") == "batch_collected" and str(r["batch_id"]) in keys and keys[str(r["batch_id"])] <= own:
            out.append(str(r["batch_id"]))
    return out


def wave_truncation(log: CallLog, batch_id: str) -> Dict[str, float]:
    """{setup: truncated share} over the FINAL results of one batch (stop reason max_tokens, kind "truncated")."""
    n: Dict[str, int] = {}
    t: Dict[str, int] = {}
    for r in log.records():
        if r.get("final") and r.get("batch_id") == batch_id:
            su = str((r.get("meta") or {}).get("setup"))                     # type: ignore[union-attr]
            n[su] = n.get(su, 0) + 1
            t[su] = t.get(su, 0) + int(r.get("kind") == "truncated" or r.get("stop_reason") == "max_tokens")
    return {su: t[su] / n[su] for su in n}


def run_batches(guard, transport: Transport, log: CallLog, items: List[Item], poll_s: float = 60.0,
                sleep: Callable[[float], None] = time.sleep, max_polls: int = 100_000,
                max_wave_size: Optional[int] = None, resend: bool = False,
                pause_truncated_over: Optional[float] = None) -> BatchSummary:
    if transport.live != guard.live:
        raise RuntimeError("a live guard goes with the real transport, a dry guard with the dry or fake one")
    mode = "batch" if transport.live else "dry"
    summary = BatchSummary()
    seen = set()
    for cid, params, _ in items:
        check_custom_id(cid)
        if cid in seen:
            raise ValueError(f"duplicate custom_id {cid!r}")
        seen.add(cid)
        assert_clean(params)
    all_items = {cid: (cid, p, m) for cid, p, m in items}
    _refuse_orphans(log)
    if pause_truncated_over is not None and pause_waived(log):
        pause_truncated_over = None                                   # the user ruled the pause off (a logged note)
    if pause_truncated_over is not None:
        paused = pause_state(log)
        if paused is not None:
            raise PausedForTruncation(f"the run paused after batch {paused.get('batch_id')}: truncated shares {paused.get('shares')}; "
                                      "report it, and only on the user's ruling release it (main.py --release-pause NOTE)")
    if not resend:
        still_open = sorted({cid for cid, _, _ in items for k in guard.open_keys() if k.startswith(cid + "@") or k.startswith(cid + "#a")}
                            - {cid for b, keys in _unsettled_batches(log) for cid in keys})
        if still_open:
            from .client import AlreadySent
            raise AlreadySent(f"{still_open[:5]} have open reservations (a failed submit or a missing result); "
                              "check the Console, then pass resend=True to send them again")
    done = log.finished_ids()
    todo = [it for it in items if it[0] not in done]
    summary.skipped_already_done = len(items) - len(todo)
    # 1. finish any batch we already submitted but never settled, if it holds THESE items. A batch of other items (the main runner's
    # single-call waves and E3's rounds share one call log) is left for the runner that owns those items: settling it here would
    # stop with "not in the items" (a crash mid-E3 could not be resumed). A batch mixing both is impossible by construction; raise.
    attempted = set()
    for batch_id, keys in _unsettled_batches(log):
        mine = set(keys) & set(all_items)
        if not mine:
            summary.left_for_their_runner.append(batch_id)
            continue
        if mine != set(keys):
            raise RuntimeError(f"batch {batch_id} mixes these items with others; settle it by hand (see the batch.py docstring)")
        _settle_batch(guard, transport, log, batch_id, all_items, keys, mode, summary, poll_s, sleep, max_polls)
        attempted.update(keys)
    # 1b. every settled batch of these items is checked for truncation once (a wave settled on a resume included), before anything new
    if pause_truncated_over is not None:
        for bid in _collected_batches_of(log, set(all_items)):
            over = check_wave(log, guard.run_id, bid, pause_truncated_over)
            if over:
                summary.paused_for_truncation = over
                return summary
    # 2. plan one wave at a time, against the room that is really left
    wave_no = len([r for r in log.records() if r.get("kind") == "batch_submitting"])
    while True:
        done = log.finished_ids()
        todo = [it for it in items if it[0] not in done and it[0] not in attempted]
        if not todo:
            return summary
        used = guard.used_keys()
        key_of = {}
        for cid, _, _ in todo:
            n = 1
            while f"{cid}@{n}" in used:
                n += 1
            key_of[cid] = f"{cid}@{n}"
        plan_in = [(key_of[cid], p["model"], estimate_input_tokens(prompt_text(p)), p["max_tokens"], True) for cid, p, _ in todo]
        by_key = {key_of[cid]: (cid, p, m) for cid, p, m in todo}
        wave_spec = guard.plan_waves(plan_in, max_wave_size=max_wave_size)[0]
        wave = [by_key[spec[0]] for spec in wave_spec]
        keys = {cid: key_of[cid] for cid, _, _ in wave}
        try:
            guard.reserve_many(list(wave_spec))
        except ConsoleCheckNeeded as e:
            # two meanings: "over the unchecked-Batch limit and no passing check yet" (record the Console figure) or "a failed
            # check blocks Batch everywhere" (a human must investigate, then console-clear); the guard's message says which
            log.write({"kind": "console_check_needed", "run_id": guard.run_id, "mode": mode, "final": False,
                       "guard_message": str(e)[:500],
                       "note": "see guard_message: record the Console figure (pilot console-check) or, after a FAILED check, find out why and use console-clear"})
            summary.stopped_for_console_check = True
            return summary
        try:
            guard.mark_sent_many(list(keys.values()))          # all or nothing
        except Exception:
            for k in keys.values():
                guard.release(k)                               # none was marked: give the reservations back
            raise
        wave_no += 1
        wave_id = f"{guard.run_id}-w{wave_no}"
        log.write({"kind": "batch_submitting", "run_id": guard.run_id, "wave_id": wave_id, "mode": mode,
                   "keys": keys, "final": False})
        try:
            batch_id = transport.submit_batch([{"custom_id": cid, "params": p} for cid, p, _ in wave])
        except Exception as e:
            log.write({"kind": "batch_submit_failed", "run_id": guard.run_id, "wave_id": wave_id, "mode": mode,
                       "keys": keys, "billed": "unknown", "error": f"{type(e).__name__}: {str(e)[:300]}", "final": False})
            raise                                              # keys stay open and counted until a human checks
        log.write({"kind": "batch_submitted", "run_id": guard.run_id, "wave_id": wave_id, "batch_id": batch_id,
                   "mode": mode, "keys": keys, "final": False})
        attempted.update(keys)
        _settle_batch(guard, transport, log, batch_id, all_items, keys, mode, summary, poll_s, sleep, max_polls)
        if pause_truncated_over is not None:
            over = check_wave(log, guard.run_id, batch_id, pause_truncated_over)
            if over:                                                 # stop BEFORE the next wave is submitted (Edith, readiness item 2)
                summary.paused_for_truncation = over
                return summary


def adopt_orphan(log: CallLog, wave_id: str, batch_id: str) -> None:
    """The batch of an orphaned wave was found at Anthropic: record its id so the next run collects it."""
    keys = None
    for r in log.records():
        if r.get("kind") == "batch_submitting" and r.get("wave_id") == wave_id:
            keys = r["keys"]
    if keys is None:
        raise KeyError(f"no batch_submitting record for wave {wave_id!r}")
    log.write({"kind": "batch_submitted", "run_id": next(iter(log.records())).get("run_id"), "wave_id": wave_id,
               "batch_id": batch_id, "mode": "batch", "keys": keys, "final": False, "adopted": True})


def close_orphan(guard, log: CallLog, wave_id: str, note: str) -> None:
    """No batch exists for an orphaned wave (checked at Anthropic): commit zero usage for each of its keys, with the note,
    and write the resolving record. The items can be sent again under new keys."""
    if not note.strip():
        raise ValueError("say what you checked (the note goes in the ledger)")
    keys = None
    for r in log.records():
        if r.get("kind") == "batch_submitting" and r.get("wave_id") == wave_id:
            keys = r["keys"]
    if keys is None:
        raise KeyError(f"no batch_submitting record for wave {wave_id!r}")
    for k in keys.values():
        if guard.status(k) == "open":
            guard.commit(k, Usage(), batch=True, note=f"orphaned batch, none found at Anthropic: {note}")
    log.write({"kind": "batch_submit_failed", "run_id": guard.run_id, "wave_id": wave_id, "mode": "batch", "keys": keys,
               "billed": "no (checked)", "error": f"closed by a human: {note}", "final": False})


def r_type_ok(res) -> bool:
    return res["result"]["type"] == "succeeded"


def _refuse_orphans(log: CallLog) -> None:
    started, resolved = {}, set()
    for r in log.records():
        if r.get("kind") == "batch_submitting":
            started[r["wave_id"]] = r["keys"]
        elif r.get("kind") in ("batch_submitted", "batch_submit_failed"):
            resolved.add(r["wave_id"])
    orphans = {w: k for w, k in started.items() if w not in resolved}
    if orphans:
        raise OrphanedBatch(f"waves {sorted(orphans)} were being submitted when the run stopped; find the batch at "
                            "Anthropic and record it, or release the keys (see the batch.py docstring)")


def _unsettled_batches(log: CallLog) -> List[Tuple[str, Dict[str, str]]]:
    submitted: Dict[str, Dict[str, str]] = {}
    collected = set()
    for r in log.records():
        if r.get("kind") == "batch_submitted":
            submitted[r["batch_id"]] = dict(r["keys"])           # type: ignore[arg-type,index]
        elif r.get("kind") == "batch_collected":
            collected.add(r["batch_id"])
        elif r.get("kind") == "batch_recollect":
            collected.discard(r["batch_id"])
    return [(b, k) for b, k in submitted.items() if b not in collected]


def recollect_batch(log: CallLog, batch_id: str, note: str) -> None:
    """A collected batch came back with results missing (their keys stay open): mark it to be collected again, so the next run
    reads its results once more (a read, never billed, never a re-send). Results already recorded are skipped by key status."""
    if not note.strip():
        raise ValueError("say what you checked (the note goes in the call log)")
    if not any(r.get("kind") == "batch_collected" and r.get("batch_id") == batch_id for r in log.records()):
        raise KeyError(f"batch {batch_id!r} was never collected")
    log.write({"kind": "batch_recollect", "batch_id": batch_id, "note": note, "final": False})


READ_RETRY_KINDS = ("connection", "rate_limit", "server")       # transport.TransportError kinds a READ may retry (never a submit)
READ_TRIES = 8                                                   # backoff 30 s, 60 s, ... capped at 15 min: about 1 h in all


def _read(fn, what: str, sleep, tries: int = READ_TRIES, base_s: float = 30.0, cap_s: float = 900.0):
    """A read-only Batch call (status or results) with retries on transient errors: a dropped connection, a timeout, 429 or 5xx.
    Reading the same batch again is safe and never billed; nothing is ever re-submitted here. After `tries` failures it raises; the
    batch stays logged as submitted and unsettled, and the same command run again settles it (run_batches step 1)."""
    from .transport import TransportError
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except TransportError as e:
            if e.kind not in READ_RETRY_KINDS or attempt == tries:
                raise
            sleep(min(cap_s, base_s * 2 ** (attempt - 1)))
    raise AssertionError("unreachable")


def _settle_batch(guard, transport, log, batch_id, wave, keys, mode, summary, poll_s, sleep, max_polls) -> None:
    summary.batches.append(batch_id)
    for _ in range(max_polls):
        if _read(lambda: transport.batch_status(batch_id), "status", sleep).get("processing_status") == "ended":
            break
        sleep(poll_s)
    else:
        raise TimeoutError(f"batch {batch_id} did not end; the reservations stay open")
    by_id = {}
    for cid in keys:
        if cid not in wave:
            raise RuntimeError(f"batch {batch_id} holds {cid!r}, which is not in the items given to run_batches")
        by_id[cid] = wave[cid]
    got = set()
    for res in _read(lambda: list(transport.batch_results(batch_id)), "results", sleep):  # fetched whole, so a retry restarts cleanly
        cid = res["custom_id"]
        if cid not in by_id:
            raise RuntimeError(f"batch {batch_id} returned an unknown custom_id {cid!r}")
        _, params, meta = by_id[cid]
        got.add(cid)
        if guard.status(keys[cid]) != "open":
            # settled before a crash: never pay it twice. If the crash came before the call-log line, write that line now
            # from the result in hand (cost from the ledger), so the item is not sent again.
            if r_type_ok(res) and cid not in log.finished_ids():
                outcome = normalize(res["result"]["message"], params["model"])
                cost = guard.summary([keys[cid]])["committed"]
                log.write(build_record(run_id=guard.run_id, mode=mode, custom_id=cid, attempt=1, params=params, meta=meta,
                                       outcome=outcome, cost=cost, latency_s=None, final=True, batch_id=batch_id))
                if outcome.is_failure:
                    summary.failed += 1
                else:
                    summary.answered += 1
            continue
        r = res["result"]
        if r["type"] == "succeeded":
            outcome = normalize(r["message"], params["model"])
            cost = settle(guard, keys[cid], outcome, batch=True)
            if outcome.is_failure:
                summary.failed += 1
            else:
                summary.answered += 1
            log.write(build_record(run_id=guard.run_id, mode=mode, custom_id=cid, attempt=1, params=params, meta=meta,
                                   outcome=outcome, cost=cost, latency_s=None, final=True, batch_id=batch_id))
        else:
            guard.commit(keys[cid], Usage(), batch=True, note=f"batch item {r['type']}: documented as not billed; reconcile with the Console")
            summary.unbilled_assumed.append(cid)
            err = {"type": r["type"], "detail": r.get("error"), "billed": "no (per batch docs)",
                   "note": "reconcile with the Console after the run"}
            log.write(build_record(run_id=guard.run_id, mode=mode, custom_id=cid, attempt=1, params=params, meta=meta,
                                   outcome=None, cost=None, latency_s=None, final=False, error=err, batch_id=batch_id))
    for cid in by_id:
        if cid not in got:
            summary.missing.append(cid)         # its reservation stays open (counted as spent)
    summ = guard.summary(list(keys.values()))
    log.write({"kind": "batch_collected", "run_id": guard.run_id, "batch_id": batch_id, "mode": mode,
               "results": len(got), "missing": sorted(set(by_id) - got), "final": False,
               "wave_reserved_usd": str(summ["reserved"]), "wave_committed_usd": str(summ["committed"]),
               "wave_open": summ["open"], "wave_done": summ["done"]})   # reconcile this against the Console before the next wave
