"""The equal-money k (D-33): how many Haiku samples cost no more than one Opus (or Sonnet) call at the same effort level.

    k = floor(comparator mean all-in cost per puzzle / Haiku mean all-in cost per sample), at most 40 and at most the
    number of samples drawn per puzzle.

"All in" means the logged cost of EVERY final call, failures, truncations and billed refusals included: the means below
are plain averages of `cost_usd` over the rows. A final call that logged no cost counts as 0 in its average and is
counted in `rows_without_cost`, never dropped. Money is Decimal throughout; the k ratio itself is an exact
`fractions.Fraction` (no Decimal rounding can move a floor), and k = 0 (Haiku costs more than the comparator per sample)
is a normal result: `h1_not_run` True, no sensitivity set, nothing raised.

k* (`k_star`, D-33 item 9): the same ratio with NO floor and NO rounding, capped at min(40, samples drawn), never
extrapolated; below 1 H1 is not run. The vote score at k* is a linear interpolation in accuracy between vote@floor(k*) and
vote@ceil(k*) (`votes.interpolated_vote_accuracy`); the caller computes it per base puzzle from this k*.

Row parsing (`parse_custom_id`). The pilot builds `custom_id = <item_id>-<setup>-<NN>` with
`item_id = <set_id>-<base index, 3 digits>-<width>x<depth>` (pilot.build_requests). So:
    puzzle   the item id, i.e. one base puzzle in one shape (`pilot-digits-d4s-v1-003-24x1`);
    shape    the `<width>x<depth>` part (`24x1` or `1x24`; at N steps, D-86, `Nx1` or `1xN`, e.g. `6x1`, `1x6`: any digits);
    setup    the tag (hm, sm, om; real-time rows carry an `rt` prefix: rthm, rtsm, rtom);
    sample   the try number.
`model_key` is `<family>-<effort>` from `requested_model` and `effort` (`claude-haiku-5-5`, `medium` -> `haiku-medium`).
It comes from the row's own model and effort columns, not from the setup tag. Real-time rows (list price, a separate
check) are left out unless asked for. Pass the rows of ONE task family to `k_table` (use `rows_of_sets`): shapes repeat
across the digit and code sets.
"""

from __future__ import annotations

import re
import math
from decimal import Decimal
from fractions import Fraction
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

CAP = 40
HAIKU_PREFIX = "haiku-"
ID_RE = re.compile(r"^(?P<puzzle>(?P<set_id>.+)-(?P<base>\d+)-(?P<shape>\d+x\d+))-(?P<setup>[a-z]+)-(?P<sample>\d+)$")
MODEL_RE = re.compile(r"^claude-([a-z]+)-")


def parse_custom_id(custom_id: str) -> Dict[str, object]:
    m = ID_RE.match(custom_id)
    if m is None:
        raise ValueError(f"custom_id {custom_id!r} does not look like <set>-<base>-<WxD>-<setup>-<NN>")
    return {"puzzle": m["puzzle"], "set_id": m["set_id"], "base_index": int(m["base"]), "shape": m["shape"],
            "setup": m["setup"], "sample": int(m["sample"]), "realtime": m["setup"].startswith("rt")}


def model_key(requested_model: str, effort: Optional[str]) -> str:
    m = MODEL_RE.match(requested_model or "")
    return f"{m[1] if m else requested_model}-{effort or 'default'}"


def annotate(row: Mapping[str, object]) -> Dict[str, object]:
    """A compact-table row plus puzzle, shape, set_id, setup, sample, realtime and model_key."""
    out = dict(row)
    out.update(parse_custom_id(str(row["custom_id"])))
    out["model_key"] = model_key(str(row.get("requested_model") or ""), row.get("effort") and str(row["effort"]))
    return out


def rows_of_sets(rows: Iterable[Mapping[str, object]], set_ids: Iterable[str]) -> List[Dict[str, object]]:
    keep = set(set_ids)
    return [dict(r) for r in rows if parse_custom_id(str(r["custom_id"]))["set_id"] in keep]


def _d(x: object) -> Decimal:
    """For display and for the Decimal spend figures; a Fraction is divided out (rounded) here, never used for a floor."""
    if isinstance(x, Decimal):
        return x
    if isinstance(x, Fraction):
        return Decimal(x.numerator) / Decimal(x.denominator)
    return Decimal(str(x))


def _cost(row: Mapping[str, object]) -> Optional[Decimal]:
    c = row.get("cost_usd")
    return None if c is None or str(c).strip() == "" else _d(c)


def _frac(x: object) -> Fraction:
    """An exact rational from a Fraction, int, Decimal or string; a float goes through its shortest repr."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, Decimal):
        return Fraction(x)
    if isinstance(x, float):
        return Fraction(repr(x))
    return Fraction(str(x).strip())


def _floor(x: object) -> int:
    return math.floor(_frac(x))


def _median(xs: List) -> object:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def realised_spend(k: int, comparator_cost_per_puzzle: object, haiku_cost_per_sample: object,
                   n_puzzles: int = 1) -> Dict[str, Decimal]:
    """What the two arms cost at k, over `n_puzzles` puzzles: the vote arm (k Haiku samples per puzzle) and the comparator."""
    opus, h = _d(comparator_cost_per_puzzle), _d(haiku_cost_per_sample)
    vote = k * h * n_puzzles
    comp = opus * n_puzzles
    return {"haiku_arm": vote, "comparator_arm": comp, "difference": vote - comp,
            "haiku_over_comparator": (vote / comp) if comp else Decimal(0)}


def k_value(opus_cost_per_puzzle: object, haiku_cost_per_sample: object, cap: int = CAP,
            samples_drawn: Optional[int] = None) -> Dict[str, object]:
    """k = floor(comparator cost per puzzle / Haiku cost per sample), capped at `cap` and at `samples_drawn`.
    The ratio is an exact Fraction and k is the floor of that rational (never Decimal division).
    `capped` is True when the cap or the samples drawn cut k below the floor, i.e. the vote costs less than the comparator.
    Haiku costing more than the comparator per sample gives k = 0 with `h1_not_run` True (not even one sample fits)."""
    fo, fh = _frac(opus_cost_per_puzzle), _frac(haiku_cost_per_sample)     # exact: a Fraction input stays exact
    if fh <= 0:
        raise ValueError("Haiku cost per sample must be positive")
    if fo < 0:
        raise ValueError("comparator cost per puzzle cannot be negative")
    opus, h = _d(opus_cost_per_puzzle), _d(haiku_cost_per_sample)
    ratio = fo / fh
    raw = math.floor(ratio)
    limit = cap if samples_drawn is None else min(cap, samples_drawn)
    k = min(raw, limit)
    capped = raw > limit
    capped_by = None
    if capped:
        capped_by = "samples_drawn" if samples_drawn is not None and samples_drawn < cap else "cap"
    return {"k": k, "raw_k": raw, "ratio": ratio, "capped": capped, "capped_by": capped_by, "h1_not_run": raw == 0,
            "cap": cap, "samples_drawn": samples_drawn, "comparator_cost_per_puzzle": opus,
            "haiku_cost_per_sample": h, "spend": realised_spend(k, opus, h)}


def k_star(opus_cost_per_puzzle: object, haiku_cost_per_sample: object, cap: int = CAP,
           samples_drawn: Optional[int] = None) -> Dict[str, object]:
    """k* = comparator mean all-in cost per puzzle / Haiku mean all-in cost per sample: D-33's k with no floor and no
    rounding, an exact Fraction, held to min(cap, samples_drawn) with no extrapolation. `ratio` is the uncapped value,
    `k_star` the capped one (Fraction) and `k_star_float` its float; `capped` is True when the limit cut it.
    `h1_not_run` is True when the uncapped k* is below 1 (the vote cannot afford one sample)."""
    fo, fh = _frac(opus_cost_per_puzzle), _frac(haiku_cost_per_sample)     # exact: a Fraction input stays exact
    if fh <= 0:
        raise ValueError("Haiku cost per sample must be positive")
    if fo < 0:
        raise ValueError("comparator cost per puzzle cannot be negative")
    opus, h = _d(opus_cost_per_puzzle), _d(haiku_cost_per_sample)
    ratio = fo / fh
    limit = cap if samples_drawn is None else min(cap, samples_drawn)
    capped = ratio > limit
    capped_by = None
    if capped:
        capped_by = "samples_drawn" if samples_drawn is not None and samples_drawn < cap else "cap"
    ks = Fraction(limit) if capped else ratio
    return {"k_star": ks, "k_star_float": float(ks), "ratio": ratio, "capped": capped, "capped_by": capped_by,
            "h1_not_run": ratio < 1, "cap": cap, "samples_drawn": samples_drawn,
            "comparator_cost_per_puzzle": opus, "haiku_cost_per_sample": h}


def k_sensitivity(k_main: int, median_ratio: object = None, pilot_ratio: object = None,
                  cap: int = CAP, samples_drawn: Optional[int] = None) -> Dict[str, object]:
    """The k values to report beside the main k. Every value is held to 1..min(cap, samples_drawn):
    k_median_ratio    floor of the median (over puzzles) of comparator cost / Haiku mean sample cost;
    k_pilot_ratio     floor of a cost ratio passed in from the pilot;
    k_band            k - 2 .. k + 2 (those that fall inside the range);
    k_values          all of them, sorted and without repeats.
    The interpolated k* row is not in this set: the caller computes it from `k_star`.
    When the main k is 0 (Haiku not run) there is nothing to vary: k_band and k_values are empty, and a ratio whose floor
    is 0 is reported as 0 (never raised to 1); a ratio floor above 0 is reported as it is but joins no set."""
    upper = cap if samples_drawn is None else min(cap, samples_drawn)
    low = 0 if k_main < 1 else 1

    def clamp(v: int) -> int:
        return max(low, min(v, upper))

    def from_ratio(r: object) -> Optional[int]:
        return None if r is None else clamp(_floor(r))
    out: Dict[str, object] = {"k_main": k_main, "k_median_ratio": from_ratio(median_ratio),
                              "k_pilot_ratio": from_ratio(pilot_ratio), "k_band": [], "k_values": []}
    if k_main < 1:
        return out
    band = [k_main + d for d in range(-2, 3) if 1 <= k_main + d <= upper]
    out["k_band"] = band
    singles = [out[k] for k in ("k_median_ratio", "k_pilot_ratio") if out[k] is not None]
    out["k_values"] = sorted(set(band) | {int(s) for s in singles} | {k_main})  # type: ignore[call-overload]
    return out


def _lookup(spec: object, key: Tuple[str, str]) -> object:
    return spec.get(key) if isinstance(spec, Mapping) else spec


def _cells(rows: List[Dict[str, object]], comparator_key: str, cap: int, pilot_ratio: object):
    by_puzzle: Dict[Tuple[str, str, str], List[Optional[Decimal]]] = {}
    for r in rows:
        by_puzzle.setdefault((str(r["shape"]), str(r["model_key"]), str(r["puzzle"])), []).append(_cost(r))
    shapes = sorted({k[0] for k in by_puzzle})
    haiku_keys = sorted({k[1] for k in by_puzzle if k[1].startswith(HAIKU_PREFIX)})
    cells = []
    for shape in shapes:
        comp = {p: sum((c or Decimal(0) for c in v), Decimal(0)) for (s, m, p), v in by_puzzle.items()
                if s == shape and m == comparator_key}
        if not comp:
            continue
        comp_per_puzzle = _frac(sum(comp.values(), Decimal(0))) / len(comp)           # exact means: no Decimal rounding
        for hk in haiku_keys:
            hp = {p: v for (s, m, p), v in by_puzzle.items() if s == shape and m == hk}
            if not hp:
                continue
            costs = [c for v in hp.values() for c in v]
            n_samples = len(costs)
            h_mean = _frac(sum((c or Decimal(0) for c in costs), Decimal(0))) / n_samples
            drawn = min(len(v) for v in hp.values())
            ratios = [_frac(comp[p]) / (_frac(sum((c or Decimal(0) for c in v), Decimal(0))) / len(v))     # exact, so a floor is exact
                      for p, v in hp.items() if p in comp and sum((c or Decimal(0) for c in v), Decimal(0)) > 0]
            median_ratio = _median(ratios) if ratios else None
            kv = k_value(comp_per_puzzle, h_mean, cap, drawn)
            key = (shape, hk)
            sens = k_sensitivity(int(kv["k"]), median_ratio, _lookup(pilot_ratio, key), cap, drawn)  # type: ignore[arg-type]
            ks = k_star(comp_per_puzzle, h_mean, cap, drawn)
            cells.append(dict(kv, shape=shape, haiku_key=hk, comparator_key=comparator_key,
                              n_puzzles_comparator=len(comp), n_puzzles_haiku=len(hp), n_haiku_samples=n_samples,
                              rows_without_cost=sum(1 for c in costs if c is None), median_ratio=median_ratio,
                              k_star=ks, sensitivity=sens,
                              spend_by_k={k: realised_spend(k, comp_per_puzzle, h_mean, len(comp))
                                          for k in sens["k_values"]}))  # type: ignore[union-attr]
    return cells


def k_table(rows: Iterable[Mapping[str, object]], cap: int = CAP, opus_key: str = "opus-medium",
            sonnet_key: str = "sonnet-medium", pilot_ratio: object = None,
            include_realtime: bool = False) -> Dict[str, List[Dict[str, object]]]:
    """One k per shape and per Haiku effort, against Opus-medium (`opus`) and, with its own costs, against Sonnet-medium
    (`sonnet`, the contrast). Cost per puzzle for a comparator = the mean over its puzzles of the sum of that puzzle's
    calls' cost; Haiku cost per sample = the mean `cost_usd` over its rows in the shape. `samples_drawn` for the cap is the
    fewest Haiku samples any puzzle in the cell has. `pilot_ratio` is a single value or a dict keyed by
    (shape, haiku model_key). Each cell also carries `k_star` (the dict from `k_star`, for the interpolated vote score)."""
    ann = [annotate(r) for r in rows]
    if not include_realtime:
        ann = [r for r in ann if not r["realtime"]]
    return {"opus": _cells(ann, opus_key, cap, pilot_ratio), "sonnet": _cells(ann, sonnet_key, cap, pilot_ratio)}
