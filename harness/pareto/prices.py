"""Pinned price table and cost-from-usage for the four models Pareto uses.

Source: `research/facts-checked.md`, rows 1a-1h and "Notes and quotes / Pricing" (Karen's check of the
Anthropic pricing page, 2026-10-10; re-checked unchanged 2026-10-11, section "Price re-check 2026-10-11"; re-checked unchanged again 2026-10-12 04:41 UTC by Karen, research/facts-checked.md). Re-check the live pricing page before every paid run and update
PRICE_TABLE_DATE with the table.

Rules the code follows (all from that file):
- Prices are US dollars per million tokens.
- Thinking tokens bill as output and count toward `max_tokens` [F-2d]. `Usage.output_tokens` includes them.
- Haiku 5.5 has a long-prompt tier [F-1e]: a request whose prompt is OVER 100,000 tokens, counting
  input, cache reads and cache writes, is billed WHOLE (output included) at the higher row. Exactly
  100,000 stays on the base row. No other model has a long-context tier.
- Batch is 50% off every rate, and stacks with the cache rates [F-1f].
- Cache writes are 1.25x input (5 minutes) or 2x input (1 hour); cache reads are per row [F-1g].
- `inference_geo: "us"` (1.1x) and fast mode (2x) are not priced because we never use them [F-1h].

Money is `decimal.Decimal` everywhere, computed in MONEY_CONTEXT, which raises on any rounding
instead of silently rounding down. Floats are never used for money.
"""

from __future__ import annotations

import decimal
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Dict

PRICE_TABLE_DATE = "2026-10-12"

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
OPUS = "claude-opus-5-5"
FABLE = "claude-fable-5-1"
MODELS = (HAIKU, SONNET, OPUS, FABLE)

MILLION = Decimal(1000000)
LONG_PROMPT_THRESHOLD = 100000  # Haiku: prompt tokens strictly above this use the long-prompt row.

# worst_case() treats a Haiku estimate above this as possibly over 100,000. The long-prompt row is a
# 5x step on the WHOLE request, so an input estimate that is a little low near the line would
# under-reserve by up to 5x. A 10% band costs almost nothing (only prompts of 90K-100K pay the higher
# reservation) and covers an estimate that is off by up to about 10%.
HAIKU_SAFETY_THRESHOLD = 90000

# 40 significant digits is far more than any sum here needs; Inexact is trapped, so if a result ever
# had to be rounded, the code raises instead of losing money in the rounding.
MONEY_CONTEXT = decimal.Context(
    prec=40,
    traps=[decimal.Inexact, decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow],
)


def money_context():
    """Use as `with money_context():` around any money arithmetic."""
    return decimal.localcontext(MONEY_CONTEXT)


@dataclass(frozen=True)
class Rates:
    """One row of the pricing page, in dollars per million tokens."""

    input: Decimal
    output: Decimal
    cache_write_5m: Decimal
    cache_write_1h: Decimal
    cache_read: Decimal


def _row(input_: str, output: str, write_5m: str, write_1h: str, read: str) -> Rates:
    return Rates(Decimal(input_), Decimal(output), Decimal(write_5m), Decimal(write_1h), Decimal(read))


# Columns: input, output, 5-minute cache write, 1-hour cache write, cache read.
PRICES: Dict[str, Rates] = {
    HAIKU: _row("0.10", "0.50", "0.125", "0.20", "0.01"),
    SONNET: _row("2", "10", "2.50", "4", "0.10"),
    OPUS: _row("4", "20", "5", "8", "0.20"),
    FABLE: _row("10", "50", "12.50", "20", "0.25"),
}

# Rows used for the WHOLE request when the prompt is over LONG_PROMPT_THRESHOLD. Haiku only.
LONG_PROMPT_PRICES: Dict[str, Rates] = {
    HAIKU: _row("0.50", "2.50", "0.625", "1", "0.05"),
}


@dataclass(frozen=True)
class Usage:
    """Token counts as the API reports them. `output_tokens` includes thinking tokens."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0

    def __post_init__(self) -> None:
        for f in fields(self):
            _check_count(f.name, getattr(self, f.name))

    @property
    def prompt_tokens(self) -> int:
        """All input-side tokens; this is what the long-prompt rule counts."""
        return (self.input_tokens + self.cache_read_tokens
                + self.cache_write_5m_tokens + self.cache_write_1h_tokens)


def _check_count(name: str, value: object) -> None:
    # bool is a subclass of int; a True/False token count is a bug, not a count.
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative int, got {value!r}")


def _check_flag(name: str, value: object) -> None:
    # A truthy string such as "False" must not switch on the Batch discount.
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be True or False, got {value!r}")


def rates_for(model: str, prompt_tokens: int) -> Rates:
    """The row that bills a request of this model with this many prompt tokens."""
    if model not in PRICES:
        raise KeyError(f"unknown model {model!r}; priced models are {sorted(PRICES)}")
    if model in LONG_PROMPT_PRICES and prompt_tokens > LONG_PROMPT_THRESHOLD:
        return LONG_PROMPT_PRICES[model]
    return PRICES[model]


def cost(model: str, usage: Usage, batch: bool = False) -> Decimal:
    """The billed cost in dollars of one request, from its reported usage. Exact, never rounded."""
    if not isinstance(usage, Usage):
        raise TypeError(f"usage must be a Usage, got {type(usage).__name__}")
    _check_flag("batch", batch)
    r = rates_for(model, usage.prompt_tokens)
    with money_context():
        total = (usage.input_tokens * r.input
                 + usage.output_tokens * r.output
                 + usage.cache_read_tokens * r.cache_read
                 + usage.cache_write_5m_tokens * r.cache_write_5m
                 + usage.cache_write_1h_tokens * r.cache_write_1h) / MILLION
        if batch:
            total = total / 2
    return total


def worst_case(model: str, est_input_tokens: int, max_tokens: int, batch: bool = False) -> Decimal:
    """The most one request could cost, given an UPPER-BOUND estimate of its prompt tokens.

    - Every prompt token is priced at the dearest input-side rate in its row, which is the 1-hour
      cache write (2x input). An uncached call costs half that on input; pricing at the cache-write
      rate keeps this a true upper bound even if the transport adds cache writes. Input is a small
      share of a reservation (output at max_tokens dominates), so this costs little headroom.
    - Output is max_tokens at the output rate (thinking counts toward max_tokens [F-2d]).
    - Haiku: an estimate above HAIKU_SAFETY_THRESHOLD (90,000) uses the long-prompt row for the
      whole request (see the comment on that constant).
    - batch=True halves it. The spend guard reserves Batch items with batch=True and real-time calls
      at list (batch=False).
    """
    _check_count("est_input_tokens", est_input_tokens)
    _check_count("max_tokens", max_tokens)
    if max_tokens < 1:
        raise ValueError("max_tokens must be at least 1")
    _check_flag("batch", batch)
    if model in LONG_PROMPT_PRICES and est_input_tokens > HAIKU_SAFETY_THRESHOLD:
        r = LONG_PROMPT_PRICES[model]
    else:
        r = rates_for(model, 0)  # raises for an unknown model
    dearest_input = max(r.input, r.cache_write_5m, r.cache_write_1h, r.cache_read)
    with money_context():
        total = (est_input_tokens * dearest_input + max_tokens * r.output) / MILLION
        if batch:
            total = total / 2
    return total


def estimate_input_tokens(text: str) -> int:
    """An UPPER-BOUND token estimate for `text`, with no tokenizer: UTF-8 bytes // 2 + 100.

    For plain ASCII this is len(text) // 2 + 100. Our prompts are digits, words and code, which we
    expect at roughly 2.5 to 3.5 characters per token (an estimate from our prompt sizes, not a
    measurement), so 2 characters per token over-reserves a little on purpose. Counting UTF-8 bytes
    instead of characters keeps non-ASCII text (several bytes per character) from being
    under-counted. The +100 covers message framing. If this estimate is ever too low, the guard sees
    the real cost exceed the reservation at commit time and halts the run.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    return len(text.encode("utf-8")) // 2 + 100
