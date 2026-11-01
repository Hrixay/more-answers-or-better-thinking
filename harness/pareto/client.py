"""The one door a model call goes through: check -> reserve -> send -> log -> commit.

For every real-time call (batches: batch.py, same rules):
  1. `assert_clean` the request (the rules of the study);
  2. work out the input-size upper bound and ask the spend guard to reserve the worst case; the guard refuses if the
     run cap or the global cap would be passed;
  3. send through the transport (dry, fake or real);
  4. normalise the reply, write the log line, then commit the real cost.

Policy (decided in D-31 / D-36, checked by tests):
  - A refusal, a truncation, an empty reply or an unexpected stop reason is a FAILED call: it is costed from its usage,
    logged and returned; it is never retried, never rephrased, never counted as an answer.
  - A reply from a different model than requested halts the guard (no fallbacks were sent, so something is wrong).
  - Only a call the API rejected before running it (rate limit, server error) is retried, at most `max_attempts`
    times, and every attempt gets its own reservation, its own key (`<custom_id>#a<n>`, n continuing across a
    restart so a key is never reused) and its own log line. A rejected call was sent, so the guard will not let it
    be released: it is committed with zero usage.
  - A dropped connection after sending is "unknown": the reservation stays open and counts as spent until a human
    has looked at the Console, and the call is never silently re-sent.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Dict, Optional

from . import prices
from .calllog import CallLog
from .outcome import ModelMismatch, Outcome, normalize
from .prices import Usage, estimate_input_tokens
from .request import assert_clean, params_hash, prompt_text
from .transport import DryTransport, Transport, TransportError

import hashlib

CUSTOM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")     # the Batch API's rule for custom_id


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def check_custom_id(custom_id: str) -> None:
    if not CUSTOM_ID_RE.match(custom_id):
        raise ValueError(f"custom_id {custom_id!r} must be 1-64 characters of letters, digits, '_' or '-'")


def halt_guard(guard, reason: str) -> None:
    guard.halt(reason)


def build_record(*, run_id: str, mode: str, custom_id: str, attempt: int, params: Dict[str, object],
                 meta: Dict[str, object], outcome: Optional[Outcome], cost: Optional[Decimal], latency_s: Optional[float],
                 final: bool, error: Optional[Dict[str, object]] = None, batch_id: Optional[str] = None) -> Dict[str, object]:
    """One log line. Contains no key and no header; the answer text is the visible reply only."""
    oc = params.get("output_config") or {}
    th = params.get("thinking") or {}
    rec: Dict[str, object] = {
        "ts": now_iso(), "run_id": run_id, "mode": mode, "custom_id": custom_id, "attempt": attempt, "final": final,
        "requested_model": params.get("model"), "effort": oc.get("effort"), "thinking": th.get("type"),  # type: ignore[union-attr]
        "max_tokens": params.get("max_tokens"), "params_hash": params_hash(params),
        "prompt_sha256": hashlib.sha256(prompt_text(params).encode()).hexdigest(), "meta": meta,
        "latency_s": None if latency_s is None else round(latency_s, 3), "batch_id": batch_id,
        "cost_usd": None if cost is None else str(cost),
    }
    if outcome is not None:
        rec.update({"kind": outcome.kind, "returned_model": outcome.returned_model, "stop_reason": outcome.stop_reason,
                    "refusal_category": outcome.refusal_category, "answer_text": outcome.answer_text,
                    "usage_raw": outcome.usage_raw, "request_id": outcome.request_id,
                    "thinking_blocks": outcome.thinking_blocks, "model_matches": outcome.model_matches,
                    "refusal_billed_by_rule": outcome.refusal_billed_by_rule,
                    "http_request_id": outcome.http_request_id,
                    "cache_write_anomaly": bool(outcome.usage.cache_write_5m_tokens or outcome.usage.cache_write_1h_tokens)})
    if error is not None:
        rec.update({"kind": "error", "error": error})
    return rec


def settle(guard, key: str, outcome: Outcome, batch: bool) -> Decimal:
    """Commit the cost of a reply that came back (answered or not). A reply from the wrong model is committed WITH the halt in
    one ledger write (Edith R4). The ledger stays CONSERVATIVE: every reply, refusals included, is committed at the cost its
    usage shows, so the caps are never under-counted. A refusal that billing rule B5 makes free (before any output, category
    cyber, general_harms or none) is committed with `free_by_rule=True`; the Console check compares the Console with the ledger
    minus those commits (Edith S2), and the paper's costs follow B5, not the committed amount."""
    reason = "" if outcome.model_matches else (
        f"model mismatch on {key}: asked {outcome.requested_model}, got {outcome.returned_model}")
    free = outcome.refusal_billed_by_rule is False
    kwargs = {"free_by_rule": True} if free else {}
    return guard.commit(key, outcome.usage, batch=batch, halt_reason=reason, **kwargs)


class AlreadySent(RuntimeError):
    """This custom_id already has a final result or an open reservation; pass resend=True to send it again on purpose."""


class Client:
    def __init__(self, guard, transport: Transport, log: CallLog, max_attempts: int = 3,
                 sleep: Callable[[float], None] = time.sleep, backoff_s: float = 5.0):
        if transport.live and not guard.live:
            raise RuntimeError("a live transport needs a live guard")
        if isinstance(transport, DryTransport) and guard.live:
            raise RuntimeError("a live guard must not be paired with the dry transport")
        self.guard, self.transport, self.log = guard, transport, log
        self.max_attempts, self.sleep, self.backoff_s = max_attempts, sleep, backoff_s
        self.mode = "realtime" if transport.live else "dry"

    def call(self, custom_id: str, params: Dict[str, object], meta: Optional[Dict[str, object]] = None,
             resend: bool = False) -> Outcome:
        """Send one request and return its Outcome. Raises CapExceeded / GuardHalted (nothing sent) or ModelMismatch
        (the reply is logged and paid for first), AlreadySent (the id is finished or still open; a dropped connection
        leaves it open, and sending it again could pay twice). A failed call is returned, not raised: check
        `outcome.is_failure`. Any other exception after the call was marked sent is logged as "billed unknown" and
        re-raised; its reservation stays open."""
        check_custom_id(custom_id)
        assert_clean(params)
        meta = dict(meta or {})
        open_for_id = [k for k in self.guard.open_keys()
                       if k.startswith(custom_id + "#a") or k.startswith(custom_id + "@")]   # real-time and batch keys
        if (custom_id in self.log.finished_ids() or open_for_id) and not resend:
            raise AlreadySent(f"{custom_id!r} is already finished or has an open reservation {open_for_id}; "
                              "pass resend=True only after checking the Console")
        if resend:
            meta["resend"] = True
        est = estimate_input_tokens(prompt_text(params))
        run_id = self.guard.run_id
        last_error: Optional[TransportError] = None
        used = self.guard.used_keys()
        first = max(self.log.attempts(custom_id) + 1, 1)
        while f"{custom_id}#a{first}" in used:              # the guard's record wins: it never reuses a key
            first += 1
        for attempt in range(first, first + self.max_attempts):
            key = f"{custom_id}#a{attempt}"
            self.guard.reserve(key, params["model"], est, params["max_tokens"], batch=False)     # type: ignore[arg-type]
            try:
                self.guard.mark_sent(key)
            except Exception:
                self.guard.release(key)                    # never sent: give the reservation back
                raise
            t0 = time.monotonic()
            try:
                msg = self.transport.send(params)
            except TransportError as e:
                last_error = e
                dt = time.monotonic() - t0
                err = {"type": e.kind, "message": str(e)[:500], "billed": e.billed, "status": e.status}
                if e.billed == "no":
                    self.guard.commit(key, Usage(), batch=False,
                                      note=f"{e.kind} status={e.status}: rejected before running, assumed unbilled")
                else:
                    err["note"] = "may have been billed; reservation left open until checked against the Console"
                will_retry = e.retryable and e.billed == "no" and attempt < first + self.max_attempts - 1
                self.log.write(build_record(run_id=run_id, mode=self.mode, custom_id=custom_id, attempt=attempt,
                                            params=params, meta=meta, outcome=None, cost=None, latency_s=dt,
                                            final=(e.billed != "no"), error=err))      # a rejected call never ran: resumable (V3)
                if not will_retry:
                    raise
                self.sleep(self.backoff_s * attempt)
                continue
            except Exception as e:                          # not a TransportError: the call may have gone out
                err = {"type": type(e).__name__, "message": str(e)[:500], "billed": "unknown",
                       "note": "unexpected exception after the call was marked sent; reservation left open"}
                self.log.write(build_record(run_id=run_id, mode=self.mode, custom_id=custom_id, attempt=attempt,
                                            params=params, meta=meta, outcome=None, cost=None,
                                            latency_s=time.monotonic() - t0, final=True, error=err))
                raise
            dt = time.monotonic() - t0
            outcome = normalize(msg, params["model"])                                            # type: ignore[arg-type]
            cost = settle(self.guard, key, outcome, batch=False)
            self.log.write(build_record(run_id=run_id, mode=self.mode, custom_id=custom_id, attempt=attempt,
                                        params=params, meta=meta, outcome=outcome, cost=cost, latency_s=dt, final=True))
            if not outcome.model_matches:                      # the guard is already halted (settle)
                raise ModelMismatch(f"{custom_id}: asked {outcome.requested_model}, got {outcome.returned_model}")
            return outcome
        raise last_error  # type: ignore[misc]  (unreachable: the loop returns or raises)
