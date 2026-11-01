"""Output limits (`max_tokens`) proposed for the pilot, per family and model (Karen, research/facts-checked.md B7 and
study1-design-evidence §6c; Edith agrees, N46 note). They are chosen so the limit does NOT bind: a stop at `max_tokens`
is logged as `truncated` per setup. The pilot's own largest outputs then set the main run's limits (about 1.5x).

Not built in, on purpose (Edith, condition d): re-running a truncated item once at 2x is a PILOT-only step. The main run
needs an item-5 rule first, so there is no automatic re-run here.

The reservation is max_tokens times the output price, so these numbers also drive how many waves the guard plans.
"""

from __future__ import annotations

PILOT_MAX_TOKENS = {
    ("digits", "claude-opus-5-5"): 32_000,
    ("digits", "claude-sonnet-5-5"): 32_000,
    ("digits", "claude-haiku-5-5"): 48_000,
    ("ledger", "claude-opus-5-5"): 32_000,        # D-56: the ledger replaces digits as the main family (output per puzzle is similar)
    ("ledger", "claude-sonnet-5-5"): 32_000,
    ("ledger", "claude-haiku-5-5"): 48_000,
    ("code", "claude-opus-5-5"): 64_000,
    ("code", "claude-haiku-5-5"): 96_000,
}


def pilot_max_tokens(family: str, model: str) -> int:
    """The proposed pilot limit; a family/model pair not in the table (for example Sonnet on code, which D-35 removed) is an error."""
    try:
        return PILOT_MAX_TOKENS[(family, model)]
    except KeyError:
        raise KeyError(f"no pilot max_tokens for {family!r} / {model!r}; the pilot covers {sorted(PILOT_MAX_TOKENS)}")
