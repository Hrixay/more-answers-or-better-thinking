"""Confirmatory statistics for Study 1: paired base-puzzle BCa bootstrap, non-inferiority p-values, Holm, three-way reading.

Rulings implemented: D-39 (five confirmatory tests, a 10-point non-inferiority margin, Holm across the five, the actual gap
always reported) and D-68 (Edith's F2 and F4: paired by base puzzle on whole-answer scoring, H0: d <= -10, one-sided
family-wise alpha = 0.025 with Holm thresholds, a three-way reading, the paired BCa bootstrap with 10,000 draws and a fixed
seed, p from inverting the bound, the sign-flip test kept only as a check for d = 0). No API or model calls; standard library.

Input. For one test, the per-base-puzzle differences x_1..x_n (challenger minus comparator whole-answer accuracy, in percentage
points; n = 80 in the study). This module never computes scores. d = mean(x) is the actual gap.

Bootstrap (`bootstrap`). B resamples of the n differences with replacement (`random.Random(seed).choices`); each statistic is
the mean (sums by `math.fsum`, so the same multiset always gives the same float). The sorted bootstrap means define the
empirical distribution F(x) = share of bootstrap means <= x. Every share passed to Phi^-1 is clipped into [1/(B+1), B/(B+1)];
F is clipped the same way (F_c) wherever it meets a quantile, so bounds and p-values can never disagree.
- Bias constant: z0 = Phi^-1(clip((#{means < d} + 0.5 * #{means == d}) / B)).
- Acceleration from the jackknife: with theta_i the mean leaving out x_i and theta_. their mean,
  a = sum((theta_. - theta_i)^3) / (6 * (sum((theta_. - theta_i)^2))^1.5), and a = 0 when the denominator is 0.
- Adjusted level for a nominal level q: u = z0 + Phi^-1(q); q_adj = Phi(z0 + u / (1 - a*u)). Where 1 - a*u <= 0 the BCa map
  has passed its pole and q_adj is its limit there: 0 if u < 0, else 1. q_adj is then nondecreasing and continuous in q.
- A LOWER end at level q is the upper empirical quantile sup{x : F_c(x) <= q_adj} (the order statistic means[floor(q_adj*B)]);
  -inf when q_adj < 1/(B+1) and +inf when q_adj >= B/(B+1), i.e. beyond what B resamples resolve.
- An UPPER end at level q is the lower empirical quantile inf{x : F_c(x) >= q_adj} (means[ceil(q_adj*B) - 1]); -inf when
  q_adj <= 1/(B+1), +inf when q_adj > B/(B+1). The two conventions mirror each other: the interval of -x is minus the interval
  of x under the same seed.
- `bca_lower_bound(x, alpha)` is the lower end at level alpha (one-sided, confidence 1 - alpha); `bca_interval(x, lo, hi)` is
  (lower end at lo, upper end at hi); the reported ci95 is the unadjusted two-sided 95% interval (0.025, 0.975).

p-value (inverting the bound). The lower bound at level alpha exceeds the margin m exactly when alpha_adj(alpha) >= G, where
G = F_c(m) = clip(share of bootstrap means <= m). Solving alpha_adj = G: w = Phi^-1(G) - z0,
z_alpha = (w * (1 - a*z0) - z0) / (1 + a*w), p = Phi(z_alpha). If 1 + a*w <= 0 the equation has no solution: with a > 0 the
bound exceeds m at every alpha (p = 0); with a < 0 it never does (p = 1). So for every alpha in (0, 1):
p <= alpha  iff  bca_lower_bound(alpha) > m (up to floating-point rounding when alpha equals p exactly).

Degenerate data. When every difference is equal (this includes n = 1) every resample is identical: z0 = a = 0, every bound
and both ends of every interval are d, and p is 0 if d > m, else 1. An empty input raises ValueError.

Seeds. Each test's seed is derived from the base seed (default 20261011) and the test's name: the first 8 bytes of
sha256("<seed>:<name>"), big-endian. Results are reproducible on the same Python version (`random` is not guaranteed stable
across versions).

Holm (`holm_one_sided`). Sort the m p-values ascending (ties keep the input order); at step j (1-based) the test is declared
non-inferior if p_(j) <= alpha / (m - j + 1); stop at the first failure; nothing after it is declared.

Three-way reading (`three_way`). "non-inferior" if Holm declares it; else "worse by more than the margin" if the unadjusted
two-sided 95% BCa interval's upper end is below the margin; else "inconclusive".

Sign-flip check for d = 0 (`sign_flip_p`). One-sided p that the mean exceeds `null`: y_i = x_i - null, T = sum(y); p is the
share of sign patterns s with sum(s_i * y_i) >= T (a 1e-9 relative tolerance counts ties as reached). Exact over all 2^n
patterns when n <= 16 (the identity pattern included); otherwise Monte Carlo with the fixed seed, p = (1 + hits) / (1 + nflips).
"""

from __future__ import annotations

import hashlib
import math
import random
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from statistics import NormalDist
from typing import Dict, List, Mapping, Sequence, Tuple

MARGIN = -10.0
ALPHA = 0.025
DRAWS = 10_000
SEED = 20261011
CI95 = (0.025, 0.975)
TIE_WEIGHT = 0.5   # bootstrap means equal to the observed mean count this much in z0 (0.5 = mid-share; 0.0 = the strict '<' of the textbook form)

NON_INFERIOR = "non-inferior"
WORSE = "worse by more than the margin"
INCONCLUSIVE = "inconclusive"

_PHI = NormalDist()


@dataclass(frozen=True)
class Boot:
    n: int
    d: float
    means: Tuple[float, ...]
    z0: float
    a: float
    B: int
    seed: int
    degenerate: bool


def derive_seed(seed: int, name: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{seed}:{name}".encode("utf-8")).digest()[:8], "big")


def _clip(share: float, B: int) -> float:
    return min(max(share, 1.0 / (B + 1)), B / (B + 1.0))


def _values(diffs: Sequence[float]) -> List[float]:
    xs = [float(x) for x in diffs]
    if not xs:
        raise ValueError("no differences")
    if not all(math.isfinite(x) for x in xs):
        raise ValueError("differences must be finite")
    return xs


def _acceleration(xs: List[float]) -> float:
    n = len(xs)
    total = math.fsum(xs)
    jack = [(total - x) / (n - 1) for x in xs]
    centre = math.fsum(jack) / n
    dev = [centre - t for t in jack]
    s2 = math.fsum(v * v for v in dev)
    if s2 <= 0.0:
        return 0.0
    return math.fsum(v ** 3 for v in dev) / (6.0 * s2 ** 1.5)


def bootstrap(diffs: Sequence[float], B: int = DRAWS, seed: int = SEED) -> Boot:
    if B < 1:
        raise ValueError("B must be at least 1")
    xs = _values(diffs)
    n = len(xs)
    if max(xs) == min(xs):
        return Boot(n, xs[0], (xs[0],), 0.0, 0.0, B, seed, True)
    d = math.fsum(xs) / n
    rng = random.Random(seed)
    means = tuple(sorted(math.fsum(rng.choices(xs, k=n)) / n for _ in range(B)))
    below = bisect_left(means, d)
    ties = bisect_right(means, d) - below
    z0 = _PHI.inv_cdf(_clip((below + TIE_WEIGHT * ties) / B, B))
    return Boot(n, d, means, z0, _acceleration(xs), B, seed, False)


def _check_level(q: float) -> None:
    if not 0.0 < q < 1.0:
        raise ValueError(f"level must be inside (0, 1), got {q}")


def adjusted_level(boot: Boot, q: float) -> float:
    _check_level(q)
    u = boot.z0 + _PHI.inv_cdf(q)
    den = 1.0 - boot.a * u
    if den <= 0.0:
        return 0.0 if u < 0.0 else 1.0
    return _PHI.cdf(boot.z0 + u / den)


def lower_end(boot: Boot, q: float) -> float:
    qa = adjusted_level(boot, q)
    if boot.degenerate:
        return boot.d
    if qa < 1.0 / (boot.B + 1):
        return -math.inf
    if qa >= boot.B / (boot.B + 1.0):
        return math.inf
    return boot.means[min(int(math.floor(qa * boot.B)), boot.B - 1)]


def upper_end(boot: Boot, q: float) -> float:
    qa = adjusted_level(boot, q)
    if boot.degenerate:
        return boot.d
    if qa <= 1.0 / (boot.B + 1):
        return -math.inf
    if qa > boot.B / (boot.B + 1.0):
        return math.inf
    return boot.means[max(int(math.ceil(qa * boot.B)) - 1, 0)]


def p_value(boot: Boot, margin: float = MARGIN) -> float:
    if boot.degenerate:
        return 0.0 if boot.d > margin else 1.0
    G = _clip(bisect_right(boot.means, margin) / boot.B, boot.B)
    w = _PHI.inv_cdf(G) - boot.z0
    den = 1.0 + boot.a * w
    if den <= 0.0:
        return 0.0 if boot.a > 0.0 else 1.0
    return _PHI.cdf((w * (1.0 - boot.a * boot.z0) - boot.z0) / den)


def bca_lower_bound(diffs: Sequence[float], alpha: float, B: int = DRAWS, seed: int = SEED) -> float:
    return lower_end(bootstrap(diffs, B, seed), alpha)


def bca_interval(diffs: Sequence[float], lo: float = CI95[0], hi: float = CI95[1], B: int = DRAWS,
                 seed: int = SEED) -> Tuple[float, float]:
    if not lo < hi:
        raise ValueError("lo must be below hi")
    boot = bootstrap(diffs, B, seed)
    return lower_end(boot, lo), upper_end(boot, hi)


def paired_bca(diffs: Sequence[float], margin: float = MARGIN, B: int = DRAWS, seed: int = SEED) -> Dict[str, object]:
    boot = bootstrap(diffs, B, seed)
    return {"n": boot.n, "d": boot.d, "p_one_sided": p_value(boot, margin),
            "ci95": (lower_end(boot, CI95[0]), upper_end(boot, CI95[1])), "z0": boot.z0, "a": boot.a, "B": B, "seed": seed,
            "margin": margin}


def holm_order(pvalues: Mapping[str, float]) -> List[str]:
    for name, p in pvalues.items():
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p-value for {name!r} must be in [0, 1], got {p}")
    return sorted(pvalues, key=lambda name: pvalues[name])


def holm_thresholds(pvalues: Mapping[str, float], alpha: float = ALPHA) -> Dict[str, float]:
    order = holm_order(pvalues)
    return {name: alpha / (len(order) - j) for j, name in enumerate(order)}


def holm_one_sided(pvalues: Mapping[str, float], alpha: float = ALPHA) -> Dict[str, bool]:
    declared = {name: False for name in pvalues}
    thresholds = holm_thresholds(pvalues, alpha)
    for name in holm_order(pvalues):
        if pvalues[name] > thresholds[name]:
            break
        declared[name] = True
    return declared


def three_way(declared: bool, ci95: Tuple[float, float], margin: float = MARGIN) -> str:
    if declared:
        return NON_INFERIOR
    if ci95[1] < margin:
        return WORSE
    return INCONCLUSIVE


def run_family(tests: Mapping[str, Sequence[float]], margin: float = MARGIN, alpha: float = ALPHA, B: int = DRAWS,
               seed: int = SEED) -> Dict[str, object]:
    results = {name: paired_bca(diffs, margin, B, derive_seed(seed, name)) for name, diffs in tests.items()}
    pvalues = {name: r["p_one_sided"] for name, r in results.items()}
    declared = holm_one_sided(pvalues, alpha)
    out = {}
    for name, r in results.items():
        out[name] = {"d": r["d"], "ci95": r["ci95"], "p": r["p_one_sided"], "declared": declared[name],
                     "reading": three_way(declared[name], r["ci95"], margin), "n": r["n"], "z0": r["z0"], "a": r["a"],
                     "seed": r["seed"]}
    return {"tests": out, "holm_order": holm_order(pvalues), "holm_thresholds": holm_thresholds(pvalues, alpha),
            "margin": margin, "alpha": alpha, "B": B, "seed": seed}


def _flip_tables(ys: List[float]) -> List[Tuple[int, int, List[float]]]:
    tables = []
    for start in range(0, len(ys), 8):
        chunk = ys[start:start + 8]
        table = [math.fsum(-y if mask >> i & 1 else y for i, y in enumerate(chunk)) for mask in range(1 << len(chunk))]
        tables.append((start, (1 << len(chunk)) - 1, table))
    return tables


def sign_flip_p(diffs: Sequence[float], null: float = 0.0, nflips: int = 100_000, seed: int = SEED) -> float:
    ys = [x - null for x in _values(diffs)]
    observed = math.fsum(ys)
    floor = observed - 1e-9 * max(1.0, math.fsum(abs(y) for y in ys))
    if len(ys) <= 16:
        sums = [0.0]
        for y in ys:
            sums = [s + y for s in sums] + [s - y for s in sums]
        return sum(1 for s in sums if s >= floor) / len(sums)
    if nflips < 1:
        raise ValueError("nflips must be at least 1")
    rng = random.Random(seed)
    tables = _flip_tables(ys)
    hits = 0
    for _ in range(nflips):
        bits = rng.getrandbits(len(ys))
        if sum(table[bits >> start & mask] for start, mask, table in tables) >= floor:
            hits += 1
    return (hits + 1) / (nflips + 1)
