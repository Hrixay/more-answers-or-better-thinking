"""Display names for arms, tags, shapes and tests (labels only; no values). The paper's naming follows the style sheet (D-122):
model-first ("Haiku-medium"), "Test N" never t1-t5, shapes "1×6" / "6×1" in tables only.

The five tests' design is copied from harness/analysis/five_tests.py lines 61-65 (challenger, comparator, shape, k kind); Study 1b's
from the 1b spec (B1: one Haiku-max try vs Opus-medium at 16 steps; B2: the k-try Haiku-max vote vs Opus-medium at 16 steps; B3: one
Haiku-max try vs Opus-medium at 6 steps), as stamped in study1b-1 analysis.json `completeness.<test>.arms` and `constants.test_sets`.
"""

from __future__ import annotations

import functools
import re
from typing import Any, Callable, Dict, Iterator, Tuple

TIMES = "×"

# An internal id: a pre-registration item ("item 24", "Items 16-17"), a keep-list C-number or an E-number ("C-047", "E-20", "E3").
# The style sheet keeps them to appendix tables; a main-text output that prints one (typed or stamped) refuses the build.
MAIN_TEXT_ID = re.compile(r"(?i:\bitems? \d)|\b[CE]-?\d")


def _printed(out: Any) -> Iterator[str]:
    """Every printed text of a built table (columns, rows, notes, caption, panel names and panels, main-text notes and caption) or
    figure (alt text, caption, the plotted points' text fields)."""
    def cells(cs: Any) -> Iterator[str]:
        for c in cs or []:
            yield c.printed
    if hasattr(out, "rows"):
        yield from cells(out.columns)
        for r in out.rows:
            yield from cells(r)
        for n in out.notes:
            yield from cells(n)
        for v in (out.caption or {}).values():
            yield from cells(v)
        for n in getattr(out, "main_notes", None) or []:
            yield from cells(n)
        for v in (getattr(out, "main_caption", None) or {}).values():
            yield from cells(v)
        for name, p in out.panels:
            yield name
            yield from _printed(p)
    elif hasattr(out, "alt"):
        yield from cells(out.alt)
        for v in (out.caption or {}).values():
            yield from cells(v)
        for p in out.points:
            yield from (v for v in p.values() if isinstance(v, str))
        for _, v in out.variants:
            yield from _printed(v)


def main_text(fn: Callable[..., Any]) -> Callable[..., Any]:
    """For the builder of a main-text output (its plan section has no '(appendix)'): the built output names no internal id
    (MAIN_TEXT_ID) in any printed text, or the build stops. Put it under @output, so the registered builder is the checked one."""
    @functools.wraps(fn)
    def checked(*a: Any, **k: Any) -> Any:
        out = fn(*a, **k)
        bad = sorted({t for t in _printed(out) if MAIN_TEXT_ID.search(t)})
        if bad:
            raise ValueError(f"{fn.__name__}: a main-text output names an internal id (appendix tables only): {bad}")
        return out
    return checked

# Study 1 arm ids (analysis.json item_24.table keys without the shape) -> (display name, model, effort or None)
STUDY1_ARMS: Dict[str, Tuple[str, str, str]] = {
    "haiku-low": ("Haiku-low", "haiku", "low"),
    "haiku-med": ("Haiku-medium", "haiku", "medium"),
    "haiku-max": ("Haiku-max", "haiku", "max"),
    "haiku-thinking-off": ("Haiku, thinking off", "haiku", "off"),
    "haiku-med-d42-variant": ("Haiku-medium (rewording check)", "haiku", "medium"),
    "opus-low": ("Opus-low", "opus", "low"),
    "opus-med": ("Opus-medium", "opus", "medium"),
    "sonnet-low": ("Sonnet-low", "sonnet", "low"),
    "sonnet-med": ("Sonnet-medium", "sonnet", "medium"),
    "e3": ("Step voting (E3)", "haiku", "medium"),
    "rt-haiku-med": ("Haiku-medium, real time", "haiku", "medium"),
    "rt-opus-med": ("Opus-medium, real time", "opus", "medium"),
    "rt-sonnet-med": ("Sonnet-medium, real time", "sonnet", "medium"),
}

# Study 1b tags (analysis.json descriptive.arms keys before '@') -> (display name, model, effort)
STUDY1B_TAGS: Dict[str, Tuple[str, str, str]] = {
    "ho": ("Haiku, thinking off", "haiku", "off"), "hl": ("Haiku-low", "haiku", "low"), "hm": ("Haiku-medium", "haiku", "medium"),
    "hh": ("Haiku-high", "haiku", "high"), "hxh": ("Haiku-xhigh", "haiku", "xhigh"), "hx": ("Haiku-max", "haiku", "max"),
    "ol": ("Opus-low", "opus", "low"), "om": ("Opus-medium", "opus", "medium"), "oh": ("Opus-high", "opus", "high"),
    "oxh": ("Opus-xhigh", "opus", "xhigh"), "ox": ("Opus-max", "opus", "max"),
    "sl": ("Sonnet-low", "sonnet", "low"), "sm": ("Sonnet-medium", "sonnet", "medium"), "sh": ("Sonnet-high", "sonnet", "high"),
    "sxh": ("Sonnet-xhigh", "sonnet", "xhigh"), "sx": ("Sonnet-max", "sonnet", "max"),
}

EFFORT_ORDER = ("off", "low", "medium", "high", "xhigh", "max")


def shape(s: str) -> str:
    """'1x6' -> '1×6' (tables only)."""
    a, b = s.split("x")
    return f"{a}{TIMES}{b}"


def shape_word(s: str) -> str:
    """'1x6' -> 'chain', '6x1' -> 'pieces' (the 1xN form is the chain, Nx1 the pieces)."""
    a, b = s.split("x")
    return "chain" if a == "1" else "pieces"


# Study 1's five tests: id -> (name, challenger arm, comparator arm, shape, k kind: 'O' Opus k, 'S' Sonnet k, None)
STUDY1_TESTS: Dict[str, Tuple[str, str, str, str, object]] = {
    "t1": ("Test 1", "haiku-med", "opus-med", "6x1", "O"),
    "t2": ("Test 2", "haiku-med", "opus-med", "1x6", "O"),
    "t3": ("Test 3", "haiku-med", "sonnet-med", "1x6", "S"),
    "t4": ("Test 4", "e3", "opus-med", "1x6", None),
    "t5": ("Test 5", "opus-low", "sonnet-med", "1x6", None),
}

STUDY1B_TESTS: Dict[str, Tuple[str, str, str]] = {
    "B1": ("Test B1", "One Haiku-max sample", "Opus-medium"),
    "B2": ("Test B2", "Haiku-max vote", "Opus-medium"),
    "B3": ("Test B3", "One Haiku-max sample", "Opus-medium"),
}


def challenger_name(test: str) -> str:
    name, ch, cmp_, sh, kk = STUDY1_TESTS[test]
    if ch == "haiku-med":
        return "Haiku-medium vote"
    return STUDY1_ARMS[ch][0]
