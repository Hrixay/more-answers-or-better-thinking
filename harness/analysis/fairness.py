"""The fairness check for the ledger: are the targeted rule kinds hard for Haiku in particular, or for every model? (D-67(2), D-68.)

Definitions: Karen's "Fairness check" in `research/pilot-plan-ledger.md` and Edith's reviews, with the house index as refined and pinned by
Edith and Karen. Exploratory: it reports, it never changes the preset rule. No API or model calls; standard library only. This module never
grades replies: `harness/analysis/scoring.py` produces the counts and this module only consumes them.

Input (`SlipCounts`, or a dict with the same keys). One record per (preset, base puzzle, model), summed over that base puzzle's tries and
shapes: `T_steps` / `T_slips` (steps checked and kind slips for the targeted kinds T), `G_steps` / `G_slips` (the same for the other kinds G),
`house_should_fire` (steps where the house rule should act) with `house_missed` (it should have acted and did not), `house_should_not_fire`
(steps where it should not act) with `house_misapplied` (it should not have acted and did), and `house_steps_checked`, which must equal
should_fire + should_not_fire (every step checks the house rule). A missing (preset, base, model) record counts as all zeros.

Mantel-Haenszel rate ratio (`mh_rate_ratio`). Strata h are presets, with a_h exposed slips over n1_h exposed steps and b_h G slips over n0_h G
steps, N_h = n1_h + n0_h: RR_MH = sum_h(a_h * n0_h / N_h) / sum_h(b_h * n1_h / N_h). A stratum with n1_h = 0 or n0_h = 0 carries no
comparison and is left out of both sums. Zero-slip correction: if the kept strata have zero exposed slips in total, or zero G slips in total,
0.5 is added to BOTH a_h and b_h in every kept stratum (Haldane-Anscombe). This pulls the ratio towards 1, so it can only make a flag harder
to reach (conservative). The ratio is None (undefined) when no stratum is kept or the denominator is still 0 (only possible without the
correction); it is 0 when the numerator is 0 and the denominator is not.

Absolute differences (`mh_rate_difference`). The Mantel-Haenszel rate difference with the same strata and weights w_h = n1_h * n0_h / N_h:
RD_MH = sum_h(w_h * (a_h / n1_h - b_h / n0_h)) / sum_h(w_h), in slips per step. One stratum gives the plain a/n1 - b/n0. No correction.

Indices.
- RR_m: exposure T (a = T_slips, n1 = T_steps) against G (b = G_slips, n0 = G_steps) for model m. TI = RR_Haiku / RR_comparison.
- RR_house,m: exposure "house": a = `house_missed`, n1 = `house_should_fire`, against the same G group. TI_house = RR_house,Haiku /
  RR_house,comparison.
- Misapplied (never a flag index): "misapplied" can only happen where the house rule should NOT fire, so it gets its own rate per model,
  house_misapplied / house_should_not_fire, pooled over presets (sums over all base puzzles: both models run the same puzzles, so the preset
  mix is the same for both), with the same bootstrap interval, and the absolute difference Haiku minus Opus (and Haiku minus Opus+Sonnet
  when TI_house pooled), in misapplied slips per step.

Bootstrap interval (`fairness_indices`). B = 2,000 replicates, 90% percentile interval (5% / 95%), point estimates on the full data. The RNG
seed is `derive_seed(seed, "fairness")` from `bootstrap.py` (the first 8 bytes of sha256("<seed>:fairness"), big-endian); the default base
seed is 20261012. One replicate: for each preset in sorted order, the preset's base puzzles (sorted) are drawn with replacement, as many as
the preset has (`rng.choices`); a drawn base brings ALL its records, for every model, so Haiku and the comparison model share the draw. Every
statistic is computed on the same replicates. The zero-slip correction is decided afresh inside each replicate, from that replicate's totals.
A replicate where a statistic is undefined is dropped for that statistic and counted. Percentile ends on the k sorted kept values v:
lower = v[floor(0.05 * k)], upper = v[ceil(0.95 * k) - 1] (the same order-statistic conventions as `bootstrap.py`). The share of kept
replicates that needed the correction is reported per index; above 10% the interval is labelled unstable.

Enough data (flag K is assessed only if). On the full data, raw slips (before any correction), with the index's own groups (T and G for TI;
missed-over-should-fire and G for TI_house); the numbers are in `MINIMA`:
- Haiku: at least 20 slips over the two groups, at least 5 in each (for TI_house: at least 5 missed and at least 5 G slips);
- the comparison model: at least 10 slips over the two groups, at least 5 in each group for TI (Edith's rule in the plan); for TI_house at
  least 3 missed and at least 5 G slips (the G group as for TI); and at least 100 steps checked in each group (should-fire steps for TI_house).
If the comparison is Opus and Opus falls short, Opus and Sonnet are pooled (their counts added per base puzzle) and labelled
"opus+sonnet"; if that still falls short, or Haiku does, the index is "not assessable at pilot scale" (reported with the counts; the value
and interval are still computed and reported). Each index decides its own pooling.

Flag K. An index fires when it is assessable, its point estimate is >= 2 and its interval's lower end is > 1. Reasons: "fires on TI",
"fires on TI_house", "fires on TI and TI_house", "does not fire", or "not assessable at pilot scale: ..." when neither index is assessable;
when only one is assessable and it does not fire, "does not fire (<other> not assessable at pilot scale: ...)".

Unplaceable tries (`unplaceable`, from `fairness_input.unplaceable_from_tries`): the plan says they are counted and left out. They never enter
the records; `fairness_indices` reports them as given, per model and preset by reason (the parse status), with a total per model and preset,
under "unplaceable" in its output and under "unplaceable" in each per-preset, per-model entry (zero when none).

Flag R (`flag_r`). Haiku's same-slip pairwise agreement on T steps against G steps: fires when both have at least 10 pairs and
agree_t / pairs_t >= 2 * agree_g / pairs_g (compared exactly in integers), with agreement on T above 0 (0 >= 2 * 0 does not count).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, fields
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

from .bootstrap import derive_seed

SEED = 20261012
DRAWS = 2_000
LEVEL = 0.90
TAILS = (0.05, 0.95)
UNSTABLE_SHARE = 0.10
FLAG_TI = 2.0

HAIKU = "haiku"
SONNET = "sonnet"
OPUS = "opus"
POOLED = "opus+sonnet"

# Enough data, per index and role: (min slips over both groups, min exposed slips, min G slips, min steps in each group).
MINIMA = {
    "TI": {"haiku": (20, 5, 5, 0), "comparison": (10, 5, 5, 100)},
    "TI_house": {"haiku": (20, 5, 5, 0), "comparison": (10, 3, 5, 100)},
}

NOT_ASSESSABLE = "not assessable at pilot scale"

Stratum = Tuple[float, float, float, float]  # (a, n1, b, n0)

# Order of the count vector kept per (preset, base, model).
_FIELDS = ("T_steps", "T_slips", "G_steps", "G_slips", "house_steps_checked", "house_should_fire", "house_missed",
           "house_should_not_fire", "house_misapplied")
_I = {name: i for i, name in enumerate(_FIELDS)}


@dataclass(frozen=True)
class SlipCounts:
    preset: str
    base_id: str
    model: str
    T_steps: int
    T_slips: int
    G_steps: int
    G_slips: int
    house_steps_checked: int
    house_should_fire: int
    house_missed: int
    house_should_not_fire: int
    house_misapplied: int

    def __post_init__(self) -> None:
        where = f"{self.preset}/{self.base_id}/{self.model}"
        for name in _FIELDS:
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ValueError(f"{where}: {name} must be a non-negative int, got {v!r}")
        if self.T_slips > self.T_steps:
            raise ValueError(f"{where}: T_slips > T_steps")
        if self.G_slips > self.G_steps:
            raise ValueError(f"{where}: G_slips > G_steps")
        if self.house_steps_checked != self.house_should_fire + self.house_should_not_fire:
            raise ValueError(f"{where}: house_steps_checked != house_should_fire + house_should_not_fire")
        if self.house_missed > self.house_should_fire:
            raise ValueError(f"{where}: house_missed > house_should_fire")
        if self.house_misapplied > self.house_should_not_fire:
            raise ValueError(f"{where}: house_misapplied > house_should_not_fire")

    def vector(self) -> Tuple[int, ...]:
        return tuple(getattr(self, name) for name in _FIELDS)


def _as_record(r: Union[SlipCounts, Mapping[str, object]]) -> SlipCounts:
    if isinstance(r, SlipCounts):
        return r
    names = [f.name for f in fields(SlipCounts)]
    missing = [n for n in names if n not in r]
    if missing:
        raise ValueError(f"record is missing {missing}: {dict(r)!r}")
    return SlipCounts(**{n: (str(r[n]) if n in ("preset", "base_id", "model") else r[n]) for n in names})  # type: ignore[arg-type]


# ---------------------------------------------------------------- Mantel-Haenszel

def _kept_strata(strata: Iterable[Sequence[float]]) -> List[Stratum]:
    kept = []
    for s in strata:
        a, n1, b, n0 = (float(x) for x in s)
        if min(a, n1, b, n0) < 0 or a > n1 or b > n0:
            raise ValueError(f"bad stratum {tuple(s)!r}")
        if n1 > 0 and n0 > 0:
            kept.append((a, n1, b, n0))
    return kept


def _mh(strata: Iterable[Sequence[float]], correction: bool) -> Tuple[Optional[float], bool]:
    kept = _kept_strata(strata)
    if not kept:
        return None, False
    corrected = correction and (math.fsum(k[0] for k in kept) == 0 or math.fsum(k[2] for k in kept) == 0)
    if corrected:
        kept = [(a + 0.5, n1, b + 0.5, n0) for a, n1, b, n0 in kept]
    num = math.fsum(a * n0 / (n1 + n0) for a, n1, b, n0 in kept)
    den = math.fsum(b * n1 / (n1 + n0) for a, n1, b, n0 in kept)
    if den == 0.0:
        return None, corrected
    return num / den, corrected


def mh_rate_ratio(strata: Iterable[Sequence[float]], correction: bool = True) -> Optional[float]:
    """Mantel-Haenszel rate ratio over strata (a, n1, b, n0); None when undefined. See the module notes for the correction."""
    return _mh(strata, correction)[0]


def mh_rate_ratio_detail(strata: Iterable[Sequence[float]], correction: bool = True) -> Tuple[Optional[float], bool]:
    """(ratio, whether the 0.5 correction was applied)."""
    return _mh(strata, correction)


def mh_rate_difference(strata: Iterable[Sequence[float]]) -> Optional[float]:
    """Mantel-Haenszel rate difference (exposed rate minus G rate, slips per step); None when no stratum has steps in both groups."""
    kept = _kept_strata(strata)
    if not kept:
        return None
    num = math.fsum((a * n0 - b * n1) / (n1 + n0) for a, n1, b, n0 in kept)
    return num / math.fsum(n1 * n0 / (n1 + n0) for a, n1, b, n0 in kept)


# ---------------------------------------------------------------- data layout

class _Data:
    """Count vectors per preset, per base puzzle, per model (plus the pooled comparison)."""

    def __init__(self, records: Iterable[Union[SlipCounts, Mapping[str, object]]]):
        recs = [_as_record(r) for r in records]
        if not recs:
            raise ValueError("no records")
        seen = set()
        self.models = sorted({r.model for r in recs})
        by: Dict[str, Dict[str, Dict[str, Tuple[int, ...]]]] = {}
        for r in recs:
            key = (r.preset, r.base_id, r.model)
            if key in seen:
                raise ValueError(f"duplicate record for {key}")
            seen.add(key)
            by.setdefault(r.preset, {}).setdefault(r.base_id, {})[r.model] = r.vector()
        zero = (0,) * len(_FIELDS)
        self.presets = sorted(by)
        self.bases: Dict[str, List[str]] = {p: sorted(by[p]) for p in self.presets}
        self.vec: Dict[str, Dict[str, Dict[str, Tuple[int, ...]]]] = {}
        for p in self.presets:
            self.vec[p] = {}
            for b in self.bases[p]:
                row = {m: by[p][b].get(m, zero) for m in self.models}
                row[POOLED] = tuple(x + y for x, y in zip(row.get(OPUS, zero), row.get(SONNET, zero)))
                self.vec[p][b] = row

    def totals(self, draw: Mapping[str, Sequence[str]], model: str) -> Dict[str, Tuple[int, ...]]:
        """Per preset, the summed count vector of `model` over the drawn base puzzles."""
        out = {}
        for p in self.presets:
            acc = [0] * len(_FIELDS)
            for b in draw[p]:
                for i, x in enumerate(self.vec[p][b][model]):
                    acc[i] += x
            out[p] = tuple(acc)
        return out


def _strata(per_preset: Mapping[str, Sequence[int]], exposure: str) -> List[Stratum]:
    out = []
    for p in sorted(per_preset):
        v = per_preset[p]
        if exposure == "T":
            a, n1 = v[_I["T_slips"]], v[_I["T_steps"]]
        elif exposure == "house":
            a, n1 = v[_I["house_missed"]], v[_I["house_should_fire"]]
        else:
            raise ValueError(f"unknown exposure {exposure!r}")
        out.append((a, n1, v[_I["G_slips"]], v[_I["G_steps"]]))
    return out


def _misapplied_rate(per_preset: Mapping[str, Sequence[int]]) -> Optional[float]:
    steps = sum(v[_I["house_should_not_fire"]] for v in per_preset.values())
    return sum(v[_I["house_misapplied"]] for v in per_preset.values()) / steps if steps else None


def stratified_draw(bases_by_preset: Mapping[str, Sequence[str]], rng: random.Random) -> Dict[str, List[str]]:
    """One replicate: for each preset (sorted), draw as many of its base puzzles (sorted) as it has, with replacement."""
    return {p: rng.choices(sorted(bases_by_preset[p]), k=len(bases_by_preset[p])) for p in sorted(bases_by_preset)}


def stratified_draws(bases_by_preset: Mapping[str, Sequence[str]], B: int, seed: int) -> Iterator[Dict[str, List[str]]]:
    """The B replicates `fairness_indices` uses for this base seed (the RNG is seeded with derive_seed(seed, "fairness"))."""
    rng = random.Random(derive_seed(seed, "fairness"))
    for _ in range(B):
        yield stratified_draw(bases_by_preset, rng)


def _percentile(values: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not values:
        return None, None
    v = sorted(values)
    k = len(v)
    lo = v[min(int(math.floor(TAILS[0] * k)), k - 1)]
    hi = v[max(int(math.ceil(TAILS[1] * k)) - 1, 0)]
    return lo, hi


# ---------------------------------------------------------------- statistics of one data set (full or replicate)

def _stats(data: _Data, draw: Mapping[str, Sequence[str]], models: Sequence[str], comp: Mapping[str, str],
           mis_targets: Sequence[str]) -> Dict[str, object]:
    tot = {m: data.totals(draw, m) for m in models}
    rr: Dict[str, Dict[str, Tuple[Optional[float], bool]]] = {"T": {}, "house": {}}
    rd: Dict[str, Dict[str, Optional[float]]] = {"T": {}, "house": {}}
    for m in models:
        for exp in ("T", "house"):
            st = _strata(tot[m], exp)
            rr[exp][m] = _mh(st, True)
            rd[exp][m] = mh_rate_difference(st)
    ti: Dict[str, Tuple[Optional[float], bool]] = {}
    for name, exp in (("TI", "T"), ("TI_house", "house")):
        (rh, ch), (rc, cc) = rr[exp][HAIKU], rr[exp][comp[name]]
        val = rh / rc if rh is not None and rc is not None and rc > 0 else None
        ti[name] = (val, ch or cc)
    mis = {m: _misapplied_rate(tot[m]) for m in models}
    mis_diff = {t: (mis[HAIKU] - mis[t] if mis[HAIKU] is not None and mis[t] is not None else None) for t in mis_targets}
    return {"rr": rr, "rd": rd, "ti": ti, "tot": tot, "mis": mis, "mis_diff": mis_diff}


# ---------------------------------------------------------------- enough data

def _group_counts(per_preset: Mapping[str, Sequence[int]], exposure: str) -> Dict[str, int]:
    st = _strata(per_preset, exposure)
    return {"exposed_slips": int(sum(s[0] for s in st)), "exposed_steps": int(sum(s[1] for s in st)),
            "G_slips": int(sum(s[2] for s in st)), "G_steps": int(sum(s[3] for s in st))}


def _short(c: Mapping[str, int], minima: Tuple[int, int, int, int]) -> List[str]:
    min_total, min_exposed, min_g, min_steps = minima
    why = []
    total = c["exposed_slips"] + c["G_slips"]
    if total < min_total:
        why.append(f"{total} slips < {min_total}")
    if c["exposed_slips"] < min_exposed:
        why.append(f"{c['exposed_slips']} exposed slips < {min_exposed}")
    if c["G_slips"] < min_g:
        why.append(f"{c['G_slips']} G slips < {min_g}")
    if c["exposed_steps"] < min_steps:
        why.append(f"{c['exposed_steps']} exposed steps < {min_steps}")
    if c["G_steps"] < min_steps:
        why.append(f"{c['G_steps']} G steps < {min_steps}")
    return why


def _assess(data: _Data, full: Mapping[str, Sequence[str]], index: str, comparison: str) -> Dict[str, object]:
    exposure = "T" if index == "TI" else "house"

    def counts(m: str) -> Dict[str, int]:
        return _group_counts(data.totals(full, m), exposure)

    haiku_c = counts(HAIKU)
    haiku_short = _short(haiku_c, MINIMA[index]["haiku"])
    comp_c = counts(comparison)
    comp_short = _short(comp_c, MINIMA[index]["comparison"])
    used, pooled = comparison, False
    if comp_short and comparison == OPUS:
        used, pooled = POOLED, True
        comp_c = counts(POOLED)
        comp_short = _short(comp_c, MINIMA[index]["comparison"])
    assessable = not haiku_short and not comp_short
    reason = "assessable"
    if not assessable:
        parts = []
        if haiku_short:
            parts.append(f"{HAIKU} short ({', '.join(haiku_short)}; counts {haiku_c})")
        if comp_short:
            parts.append(f"{used} short ({', '.join(comp_short)}; counts {comp_c})")
        reason = f"{NOT_ASSESSABLE}: " + "; ".join(parts)
    return {"assessable": assessable, "comparison": used, "pooled": pooled, "reason": reason,
            "counts": {HAIKU: haiku_c, used: comp_c}}


# ---------------------------------------------------------------- the check

def _unplaceable(given: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]]) -> Dict[str, Dict[str, Dict[str, object]]]:
    """{model: {preset: {"tries": total, "by_reason": {reason: tries}}}} from {model: {preset: {reason: tries}}}, checked."""
    out: Dict[str, Dict[str, Dict[str, object]]] = {}
    for m, presets in sorted((given or {}).items()):
        for p, reasons in sorted(presets.items()):
            for reason, n in reasons.items():
                if isinstance(n, bool) or not isinstance(n, int) or n < 0:
                    raise ValueError(f"unplaceable {m}/{p}/{reason}: tries must be a non-negative int, got {n!r}")
            out.setdefault(str(m), {})[str(p)] = {"tries": sum(reasons.values()), "by_reason": dict(sorted(reasons.items()))}
    return out


def fairness_indices(records: Iterable[Union[SlipCounts, Mapping[str, object]]], comparison: str = OPUS, B: int = DRAWS,
                     seed: int = SEED, unplaceable: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None) -> Dict[str, object]:
    """TI and TI_house with their 90% stratified base-puzzle bootstrap intervals, RR and absolute differences per model, the misapplied
    rates, counts, the enough-data check (with Opus+Sonnet pooling), flag K and the unplaceable tries ({model: {preset: {reason: tries}}},
    from `fairness_input.unplaceable_from_tries`). See the module notes for every definition."""
    if B < 1:
        raise ValueError("B must be at least 1")
    unplaced = _unplaceable(unplaceable)
    data = _Data(records)
    if HAIKU not in data.models:
        raise ValueError(f"no {HAIKU} records")
    if comparison != POOLED and comparison not in data.models:
        raise ValueError(f"no {comparison} records")
    full = {p: list(data.bases[p]) for p in data.presets}

    assess = {name: _assess(data, full, name, comparison) for name in ("TI", "TI_house")}
    comp = {name: str(a["comparison"]) for name, a in assess.items()}
    models = list(data.models)
    if POOLED in comp.values() or comparison == POOLED:
        models.append(POOLED)
    mis_targets = [t for t in dict.fromkeys(([OPUS] if OPUS in data.models else []) + [comp["TI_house"]]) if t != HAIKU]

    point = _stats(data, full, models, comp, mis_targets)
    reps = [_stats(data, draw, models, comp, mis_targets) for draw in stratified_draws(data.bases, B, seed)]

    def interval(vals: Sequence[Optional[float]]) -> Dict[str, object]:
        kept = [v for v in vals if v is not None]
        return {"ci90": _percentile(kept), "kept": len(kept), "dropped": len(vals) - len(kept)}

    out_idx: Dict[str, Dict[str, object]] = {}
    for name in ("TI", "TI_house"):
        val = point["ti"][name][0]
        pairs = [s["ti"][name] for s in reps]
        iv = interval([v for v, _ in pairs])
        kept_corr = [c for v, c in pairs if v is not None]
        share = (sum(kept_corr) / len(kept_corr)) if kept_corr else None
        lo = iv["ci90"][0]
        a = assess[name]
        fires = bool(a["assessable"] and val is not None and val >= FLAG_TI and lo is not None and lo > 1.0)
        exp = "T" if name == "TI" else "house"
        out_idx[name] = {
            "point": val, "ci90": iv["ci90"], "kept": iv["kept"], "dropped": iv["dropped"],
            "comparison": comp[name], "pooled": a["pooled"],
            "correction_point": {HAIKU: point["rr"][exp][HAIKU][1], comp[name]: point["rr"][exp][comp[name]][1]},
            "correction_share": share, "unstable": share is not None and share > UNSTABLE_SHARE,
            "assessable": a["assessable"], "assess_reason": a["reason"], "assess_counts": a["counts"], "fires": fires,
        }

    def per_model(exp: str, kind: str) -> Dict[str, Dict[str, object]]:
        res = {}
        for m in models:
            if kind == "rr":
                v, c = point["rr"][exp][m]
                res[m] = dict(point=v, corrected=c, **interval([s["rr"][exp][m][0] for s in reps]))
            else:
                res[m] = dict(point=point["rd"][exp][m], **interval([s["rd"][exp][m] for s in reps]))
        return res

    counts: Dict[str, Dict[str, int]] = {}
    per_preset: Dict[str, Dict[str, Dict[str, object]]] = {}
    for m in models:
        tot = point["tot"][m]
        counts[m] = dict(zip(_FIELDS, [sum(tot[p][i] for p in data.presets) for i in range(len(_FIELDS))]))
        for p in data.presets:
            v = dict(zip(_FIELDS, tot[p]))
            per_preset.setdefault(p, {})[m] = {
                "counts": v, "bases": len(data.bases[p]),
                "T_rate": v["T_slips"] / v["T_steps"] if v["T_steps"] else None,
                "G_rate": v["G_slips"] / v["G_steps"] if v["G_steps"] else None,
                "missed_rate": v["house_missed"] / v["house_should_fire"] if v["house_should_fire"] else None,
                "misapplied_rate": v["house_misapplied"] / v["house_should_not_fire"] if v["house_should_not_fire"] else None,
                "RR": mh_rate_ratio(_strata({p: tot[p]}, "T")),
                "RR_house": mh_rate_ratio(_strata({p: tot[p]}, "house")),
                "unplaceable": unplaced.get(m, {}).get(p, {"tries": 0, "by_reason": {}}),
            }
    misapplied = {
        "rate": {m: dict(point=point["mis"][m], misapplied=counts[m]["house_misapplied"],
                         steps_should_not_fire=counts[m]["house_should_not_fire"], **interval([s["mis"][m] for s in reps]))
                 for m in models},
        "diff": {f"{HAIKU}-{t}": dict(point=point["mis_diff"][t], **interval([s["mis_diff"][t] for s in reps])) for t in mis_targets},
        "note": "reported only; not a flag index",
    }

    fired = [n for n in ("TI", "TI_house") if out_idx[n]["fires"]]
    na = [n for n in ("TI", "TI_house") if not out_idx[n]["assessable"]]
    if fired:
        reason = "fires on " + " and ".join(fired)
    elif len(na) == 2:
        reason = f"{NOT_ASSESSABLE}: TI: {out_idx['TI']['assess_reason']}; TI_house: {out_idx['TI_house']['assess_reason']}"
    elif na:
        reason = f"does not fire ({na[0]} {out_idx[na[0]]['assess_reason']})"
    else:
        reason = "does not fire"

    return {
        "TI": out_idx["TI"], "TI_house": out_idx["TI_house"],
        "RR": per_model("T", "rr"), "RR_house": per_model("house", "rr"),
        "abs_diff": per_model("T", "rd"), "abs_diff_house": per_model("house", "rd"),
        "misapplied": misapplied, "counts": counts, "per_preset": per_preset,
        "unplaceable": {"by_model_preset": unplaced, "note": "counted and left out of every count above"},
        "comparison": {"TI": comp["TI"], "TI_house": comp["TI_house"]},
        "pooled": {"TI": out_idx["TI"]["pooled"], "TI_house": out_idx["TI_house"]["pooled"]},
        "flag_k": {"fires": bool(fired), "reason": reason, "on": fired},
        "B": B, "seed": seed, "rng_seed": derive_seed(seed, "fairness"), "level": LEVEL,
        "presets": {p: len(data.bases[p]) for p in data.presets},
    }


# ---------------------------------------------------------------- flag R

def flag_r(agree_t: int, pairs_t: int, agree_g: int, pairs_g: int, min_pairs: int = 10) -> Dict[str, object]:
    """Haiku's same-slip agreement on T steps at least twice that on G steps, with at least `min_pairs` pairs in each."""
    for name, v in (("agree_t", agree_t), ("pairs_t", pairs_t), ("agree_g", agree_g), ("pairs_g", pairs_g)):
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError(f"{name} must be a non-negative int, got {v!r}")
    if agree_t > pairs_t or agree_g > pairs_g:
        raise ValueError("agreeing pairs cannot exceed total pairs")
    at = agree_t / pairs_t if pairs_t else None
    ag = agree_g / pairs_g if pairs_g else None
    if pairs_t < min_pairs or pairs_g < min_pairs:
        return {"fires": False, "agreement_T": at, "agreement_G": ag,
                "reason": f"not assessable: {pairs_t} T pairs and {pairs_g} G pairs (need {min_pairs} each)"}
    fires = agree_t > 0 and agree_t * pairs_g >= 2 * agree_g * pairs_t
    return {"fires": fires, "agreement_T": at, "agreement_G": ag,
            "reason": "fires: T agreement >= 2 x G agreement" if fires else "does not fire"}
