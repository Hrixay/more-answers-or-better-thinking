"""Turn one model response (an SDK object or a plain dict) into a flat, loggable Outcome.

HTTP 200 with `stop_reason: "refusal"` is NOT an exception: it is classified here, costed from its usage, and counted
as a failure. Any stop reason we do not expect is also a failure, never a success (ops/review-checklist.md 2a).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .prices import Usage

KINDS = ("answered", "empty", "refusal", "truncated", "unexpected_stop")
# Refusal categories that are billed even before any output (research/facts-checked.md correction 4).
BILLED_REFUSAL_CATEGORIES = ("bio", "frontier_llm", "reasoning_extraction")


class ModelMismatch(RuntimeError):
    """The reply came from a different model than the one requested: with no fallbacks sent, something is badly wrong."""


@dataclass
class Outcome:
    kind: str                          # one of KINDS
    requested_model: str
    returned_model: Optional[str]
    stop_reason: Optional[str]
    refusal_category: Optional[str]
    answer_text: str                   # the visible text blocks, joined
    usage: Usage
    usage_raw: Dict[str, object]       # the usage object exactly as returned, for offline re-pricing
    request_id: Optional[str]
    model_matches: bool
    thinking_blocks: int = 0
    http_request_id: Optional[str] = None
    extra: Dict[str, object] = field(default_factory=dict)

    @property
    def is_failure(self) -> bool:
        return self.kind != "answered"

    @property
    def refusal_billed_by_rule(self) -> Optional[bool]:
        """Karen's rule B5a (research/facts-checked.md): a refusal before any output is billed only for the categories
        bio, frontier_llm and reasoning_extraction (cyber, general_harms or none: $0, even though usage shows input
        tokens); a refusal with partial output is billed from usage whatever the category. None when not a refusal.
        The guard still commits the usage cost (conservative); the spend log and the cost analysis apply this rule."""
        if self.kind != "refusal":
            return None
        return bool(self.answer_text.strip() or self.thinking_blocks or self.usage.output_tokens > 0
                    or self.refusal_category in BILLED_REFUSAL_CATEGORIES)


def _as_dict(msg) -> Dict[str, object]:
    if isinstance(msg, dict):
        return msg
    for name in ("to_dict", "model_dump"):
        fn = getattr(msg, name, None)
        if callable(fn):
            return fn()
    raise TypeError(f"cannot read a response of type {type(msg).__name__}")


def usage_from_raw(raw: Dict[str, object]) -> Usage:
    """Map the API's usage object to prices.Usage. Cache writes are split by TTL when the API says how."""
    cc = raw.get("cache_creation") or {}
    total_write = int(raw.get("cache_creation_input_tokens") or 0)
    w5 = int(cc.get("ephemeral_5m_input_tokens") or 0) if isinstance(cc, dict) else 0
    w1 = int(cc.get("ephemeral_1h_input_tokens") or 0) if isinstance(cc, dict) else 0
    if total_write > w5 + w1:       # no breakdown given: price the remainder at the 5-minute rate
        w5 += total_write - (w5 + w1)
    return Usage(input_tokens=int(raw.get("input_tokens") or 0), output_tokens=int(raw.get("output_tokens") or 0),
                 cache_read_tokens=int(raw.get("cache_read_input_tokens") or 0),
                 cache_write_5m_tokens=w5, cache_write_1h_tokens=w1)


def normalize(msg, requested_model: str) -> Outcome:
    d = _as_dict(msg)
    usage_raw = dict(d.get("usage") or {})
    blocks = d.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    thinking = sum(1 for b in blocks if isinstance(b, dict) and b.get("type") in ("thinking", "redacted_thinking"))
    stop = d.get("stop_reason")
    details = d.get("stop_details") or {}
    category = details.get("category") if isinstance(details, dict) else None
    if stop in ("end_turn", "stop_sequence"):
        kind = "answered" if text.strip() else "empty"
    elif stop == "refusal":
        kind = "refusal"
    elif stop == "max_tokens":
        kind = "truncated"
    else:
        kind = "unexpected_stop"
    returned = d.get("model")
    return Outcome(kind=kind, requested_model=requested_model, returned_model=returned, stop_reason=stop,
                   refusal_category=category if stop == "refusal" else None, answer_text=text,
                   usage=usage_from_raw(usage_raw), usage_raw=usage_raw, request_id=d.get("id"),
                   model_matches=(returned == requested_model), thinking_blocks=thinking,
                   http_request_id=d.get("_request_id"))
