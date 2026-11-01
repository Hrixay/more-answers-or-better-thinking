"""From graded tries to the counts the fairness check reads (`fairness.SlipCounts`).

`scoring.local_steps` places every step of a reply and names the blame; this module adds them up per (preset, base puzzle, model), the grain at
which the fairness bootstrap resamples. T and G follow the step's own kind; a step of any other kind is counted in neither group (it still counts
in the house columns, because every step checks the house rule). Kind slips are blames "kind" and "decoy_confusion"; house slips are kept apart:
`house_missed` over the steps where the house rule should fire, `house_misapplied` over the steps where it should not. Unplaceable tries are
counted and left out (the plan's "Fairness check", item 4): `records_from_tries` leaves them out of the counts and `unplaceable_from_tries`
counts them per model and preset, by reason (the parse status). `fairness.fairness_indices(..., unplaceable=...)` reports those counts.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from .fairness import SlipCounts


def records_from_tries(tries: Iterable[Tuple[str, str, str, Dict[str, object]]]) -> List[SlipCounts]:
    """`tries` yields (preset, base_id, model, placed) with `placed` from `scoring.local_steps(...)` (or `first_slip_steps(...)` for the
    sensitivity view). Returns one SlipCounts per (preset, base_id, model), in sorted order."""
    acc: Dict[Tuple[str, str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for preset, base, model, placed in tries:
        if placed["unplaceable"] is not None:
            continue
        c = acc[(preset, base, model)]
        for st in placed["steps"]:
            blame = st["blame"]
            if st["cls"] in ("T", "G"):
                c[st["cls"] + "_steps"] += 1
                c[st["cls"] + "_slips"] += blame in ("kind", "decoy_confusion")
            c["house_steps_checked"] += 1
            if st["house_should_act"]:
                c["house_should_fire"] += 1
                c["house_missed"] += blame == "house_missed"
            else:
                c["house_should_not_fire"] += 1
                c["house_misapplied"] += blame == "house_misapplied"
    names = ("T_steps", "T_slips", "G_steps", "G_slips", "house_steps_checked", "house_should_fire", "house_missed",
             "house_should_not_fire", "house_misapplied")
    return [SlipCounts(preset=k[0], base_id=k[1], model=k[2], **{n: int(v.get(n, 0)) for n in names}) for k, v in sorted(acc.items())]


def unplaceable_from_tries(tries: Iterable[Tuple[str, str, str, Dict[str, object]]]) -> Dict[str, Dict[str, Dict[str, int]]]:
    """The unplaceable tries, counted: {model: {preset: {reason: tries}}}, the reason being the parse status (`placed["status"]`, for
    example "missing_line", "non_integer" or, when every step is right, "answer_mismatch"). Same `tries` as `records_from_tries` (pass a
    list, not a one-shot iterator, to use both). Models and presets with no unplaceable try are left out."""
    out: Dict[str, Dict[str, Dict[str, int]]] = {}
    for preset, _base, model, placed in tries:
        if placed["unplaceable"] is None:
            continue
        reason = str(placed.get("status") or "unknown")
        by = out.setdefault(model, {}).setdefault(preset, {})
        by[reason] = by.get(reason, 0) + 1
    return {m: {p: dict(sorted(r.items())) for p, r in sorted(v.items())} for m, v in sorted(out.items())}
