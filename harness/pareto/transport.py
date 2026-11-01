"""How a request actually leaves the machine. Three transports, one interface.

- `DryTransport`: the default. No network, no key, no SDK import. Returns a synthetic reply whose usage is derived from
  the request (so the reserve -> send -> commit -> log path is exercised for real).
- `FakeTransport`: scripted replies and errors, for tests (refusals, truncation, a wrong model, a server error ...).
- `RealTransport`: the Anthropic SDK. Built only after `guard.require_live()` has passed; this is the only place in the
  repository that imports `anthropic`, and the SDK's own retries are switched off (`max_retries=0`) so that every
  attempt is reserved and logged by us.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .prices import estimate_input_tokens
from .request import prompt_text
from .secrets_env import DEFAULT_ENV, load_api_key


API_BASE_URL = "https://api.anthropic.com"
REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


class TransportError(Exception):
    """A call that did not produce a normal reply.

    billed: "no"      the API refused or failed it before running it (429, 4xx, 5xx); not billed
            "unknown" it may have run (timeout or a dropped connection after sending); the reservation stays open and
                      counts as spent until a human has checked the Console
    retryable: whether sending the same request again is allowed (never for 4xx other than 429)
    """

    def __init__(self, kind: str, message: str, billed: str = "no", retryable: bool = False, status: Optional[int] = None):
        super().__init__(f"{kind}: {message}")
        self.kind, self.billed, self.retryable, self.status = kind, billed, retryable, status


class Transport:
    live = False

    def send(self, params: Dict[str, object]) -> Dict[str, object]:
        raise NotImplementedError

    def submit_batch(self, requests: List[Dict[str, object]]) -> str:
        raise NotImplementedError

    def batch_status(self, batch_id: str) -> Dict[str, object]:
        raise NotImplementedError

    def batch_results(self, batch_id: str) -> Iterable[Dict[str, object]]:
        raise NotImplementedError


def _synthetic_reply(params: Dict[str, object], text: str = "DRY RUN") -> Dict[str, object]:
    est_in = estimate_input_tokens(prompt_text(params))
    return {"id": "dry-run", "type": "message", "role": "assistant", "model": params["model"],
            "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_details": None,
            "usage": {"input_tokens": est_in // 2, "output_tokens": int(params["max_tokens"]) // 4,  # type: ignore[call-overload]
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}


class DryTransport(Transport):
    """No network. Everything it 'sends' it answers itself."""

    def __init__(self) -> None:
        self.sent: List[Dict[str, object]] = []
        self._batches: Dict[str, List[Dict[str, object]]] = {}

    def send(self, params: Dict[str, object]) -> Dict[str, object]:
        self.sent.append(params)
        return _synthetic_reply(params)

    def submit_batch(self, requests: List[Dict[str, object]]) -> str:
        bid = f"dry-batch-{len(self._batches) + 1}"
        self._batches[bid] = requests
        return bid

    def batch_status(self, batch_id: str) -> Dict[str, object]:
        return {"processing_status": "ended", "request_counts": {"processing": 0}}

    def batch_results(self, batch_id: str) -> Iterable[Dict[str, object]]:
        for r in self._batches[batch_id]:
            yield {"custom_id": r["custom_id"], "result": {"type": "succeeded", "message": _synthetic_reply(r["params"])}}  # type: ignore[arg-type]


class FakeTransport(Transport):
    """Scripted for tests. `replies` maps a custom marker or is a callable (params) -> reply dict or raises TransportError."""

    def __init__(self, reply: Callable[[Dict[str, object]], Dict[str, object]] = _synthetic_reply,
                 batch_reply: Optional[Callable[[str, Dict[str, object]], Dict[str, object]]] = None) -> None:
        self.reply, self.batch_reply = reply, batch_reply
        self.sent: List[Dict[str, object]] = []
        self.batches: Dict[str, List[Dict[str, object]]] = {}
        self.polls = 0

    def send(self, params: Dict[str, object]) -> Dict[str, object]:
        self.sent.append(params)
        return self.reply(params)

    def submit_batch(self, requests: List[Dict[str, object]]) -> str:
        bid = f"fake-batch-{len(self.batches) + 1}"
        self.batches[bid] = requests
        return bid

    def batch_status(self, batch_id: str) -> Dict[str, object]:
        self.polls += 1
        return {"processing_status": "ended" if self.polls >= 2 else "in_progress", "request_counts": {}}

    def batch_results(self, batch_id: str) -> Iterable[Dict[str, object]]:
        for r in reversed(self.batches[batch_id]):          # any order, like the real API
            cid, params = r["custom_id"], r["params"]
            if self.batch_reply:
                yield {"custom_id": cid, "result": self.batch_reply(cid, params)}  # type: ignore[arg-type]
            else:
                yield {"custom_id": cid, "result": {"type": "succeeded", "message": self.reply(params)}}  # type: ignore[arg-type]


class RealTransport(Transport):
    """The Anthropic SDK. The constructor refuses unless the spend guard's live gate passes."""

    live = True

    def __init__(self, guard, timeout_s: float = 1800.0, requirements: Path = REQUIREMENTS,
                 env_file: Optional[Path] = None) -> None:
        guard.require_live()                 # raises unless live + a matching clearance file
        import anthropic                     # imported here only; dry runs never reach this line
        check_sdk_pin(anthropic, requirements)
        base = (os.environ.get("ANTHROPIC_BASE_URL") or API_BASE_URL).rstrip("/")
        if base != API_BASE_URL:                                     # Edith T4: a redirect would send the key elsewhere
            raise RuntimeError("ANTHROPIC_BASE_URL points somewhere other than api.anthropic.com; the key may only go there")
        # the .env path is the one the cleared clearance names (guard.env_file); tests pass their own
        api_key = load_api_key(env_file if env_file is not None else guard.env_file)     # the only place the key is read; never logged or printed
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key, base_url=API_BASE_URL, max_retries=0, timeout=timeout_s)

    def send(self, params: Dict[str, object]) -> Dict[str, object]:
        """Streaming call. Billing facts (Karen, research/facts-checked.md): an HTTP error response before the stream
        starts (429, 5xx) is not billed; a timeout or disconnect, or an error event after the stream has started, may
        be billed with no usage returned, so those are `billed="unknown"` and the guard keeps the reservation open."""
        a = self._anthropic
        cm = self._client.messages.stream(**params)
        try:
            stream = cm.__enter__()                      # the request is sent here; an error response raises here
        except a.RateLimitError as e:
            raise TransportError("rate_limit", str(e), billed="no", retryable=True, status=429)
        except a.BadRequestError as e:
            raise TransportError("bad_request", str(e), billed="no", retryable=False, status=400)
        except (a.AuthenticationError, a.PermissionDeniedError, a.NotFoundError) as e:
            raise TransportError("auth_or_model", str(e), billed="no", retryable=False, status=getattr(e, "status_code", None))
        except (a.APITimeoutError, a.APIConnectionError) as e:        # subclasses of APIError: keep before APIStatusError
            raise TransportError("connection", str(e), billed="unknown", retryable=False)
        except a.APIStatusError as e:
            if e.status_code < 400:                      # not an HTTP error response: something odd, maybe mid-stream
                raise TransportError("odd_status", str(e), billed="unknown", retryable=False, status=e.status_code)
            if e.status_code >= 500:
                raise TransportError("server", str(e), billed="no", retryable=True, status=e.status_code)
            raise TransportError("api_error", str(e), billed="no", retryable=False, status=e.status_code)
        try:
            final = stream.get_final_message()
            d = final.to_dict()
            # the streamed final message has no _request_id of its own; the id is on the HTTP response (N48)
            d["_request_id"] = getattr(stream, "request_id", None) or getattr(final, "_request_id", None)
        except Exception as e:                           # anything after the stream started: possibly billed
            try:
                cm.__exit__(type(e), e, None)
            finally:
                raise TransportError("mid_stream", f"{type(e).__name__}: {e}", billed="unknown", retryable=False)
        cm.__exit__(None, None, None)
        return d

    def submit_batch(self, requests: List[Dict[str, object]]) -> str:
        return self._client.messages.batches.create(requests=requests).id

    def _read_error(self, e: Exception) -> Exception:
        """A failed READ of a batch (status or results) as a TransportError, so batch._read can retry the transient ones. Reads are
        never billed."""
        a = self._anthropic
        if isinstance(e, a.RateLimitError):
            return TransportError("rate_limit", str(e), billed="no", retryable=True, status=429)
        if isinstance(e, (a.APITimeoutError, a.APIConnectionError)):
            return TransportError("connection", str(e), billed="no", retryable=True)
        if isinstance(e, a.APIStatusError) and getattr(e, "status_code", 0) >= 500:
            return TransportError("server", str(e), billed="no", retryable=True, status=e.status_code)
        return e

    def batch_status(self, batch_id: str) -> Dict[str, object]:
        try:
            b = self._client.messages.batches.retrieve(batch_id)
        except Exception as e:
            err = self._read_error(e)
            if err is e:
                raise
            raise err from e
        return {"processing_status": b.processing_status, "request_counts": b.request_counts.to_dict()}

    def batch_results(self, batch_id: str) -> Iterable[Dict[str, object]]:
        try:
            rows = list(self._client.messages.batches.results(batch_id))
        except Exception as e:
            err = self._read_error(e)
            if err is e:
                raise
            raise err from e
        for r in rows:
            res = r.result
            entry: Dict[str, object] = {"type": res.type}
            if res.type == "succeeded":
                entry["message"] = res.message.to_dict()
            elif res.type == "errored":
                entry["error"] = res.error.to_dict() if hasattr(res.error, "to_dict") else str(res.error)
            yield {"custom_id": r.custom_id, "result": entry}


def pinned_sdk_version(requirements: Path = REQUIREMENTS) -> Optional[str]:
    """The version in harness/requirements.txt (`anthropic==X.Y.Z`), or None if the file has no such line."""
    if not Path(requirements).exists():
        return None
    for ln in Path(requirements).read_text().splitlines():
        m = re.match(r"^\s*anthropic\s*==\s*([\w.\-+]+)\s*(#.*)?$", ln)
        if m:
            return m.group(1)
    return None


def check_sdk_pin(sdk, requirements: Path = REQUIREMENTS) -> str:
    """A live run needs the SDK version pinned in harness/requirements.txt and installed exactly (checklist 2a).
    Refuses otherwise; returns the version."""
    pin = pinned_sdk_version(requirements)
    have = getattr(sdk, "__version__", None)
    if pin is None:
        raise RuntimeError("harness/requirements.txt does not pin anthropic==X.Y.Z; pin the version the pilot will use")
    if have != pin:
        raise RuntimeError(f"installed anthropic {have!r} is not the pinned {pin!r}")
    return pin


def sleep_for(seconds: float) -> None:
    time.sleep(seconds)
