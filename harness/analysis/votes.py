"""The vote@k estimator (D-33): the chance that a plurality vote over k of an arm's samples is right, for one puzzle.

One base puzzle, one arm. `answers` holds the arm's samples' parsed final answers: a string each, or None for a reply with
no answer (unparseable, empty, truncated, refused). A None is a vote for nothing: it takes a place in the k-subset but
supports no answer. Answers are compared as exact strings, so the caller normalises them first.

The vote over a k-subset (drawn WITHOUT replacement from the n samples) is the plurality of its non-None answers.
Ties: the primary rule (`tie="random"`) breaks a tie at random, scored at its expectation: when the correct answer is one of
the m answers tied for the top count it earns 1/m, and 0 when it is not. `tie="wrong"` scores every tie as wrong
(a sensitivity check). A subset with no answer at all (all None) is wrong. At k = n there is exactly one subset.

Exact where feasible: a vote depends only on how many samples share each answer, so the sum over all C(n, k) subsets is
done by dynamic programming over the distinct answers (state: samples drawn so far, top count among the other answers,
how many of them hold it). Otherwise (or on request) Monte-Carlo over `ndraws` random subsets from `random.Random(seed)`.

`tie_decided_share` counts the share of subsets in which the correct answer is tied for the top count with at least one
other answer, so the random tie-break (or, under tie="wrong", the zero) decided its credit. A tie among top answers that
does not include the correct answer is scored 0 whatever the rule, so it is not counted there; `tie_any_share` counts
every subset with a tie for the top count, with or without the correct answer.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple, Union

DEFAULT_SEED = 33
MIN_DRAWS = 1000
MAX_EXACT_DISTINCT = 64          # distinct wrong answers up to which the exact count runs on mode="auto" (the DP is polynomial; 40 samples never exceed this)


def _credit(sub: Sequence[Optional[str]], correct: str, tie: str) -> Tuple[Fraction, bool, bool]:
    """Credit of one subset, whether a tie containing the correct answer decided it, whether any top tie exists."""
    counts = Counter(a for a in sub if a is not None)
    if not counts:
        return Fraction(0), False, False
    top = max(counts.values())
    tied = [a for a, c in counts.items() if c == top]
    tie_any = len(tied) > 1
    if correct not in tied:
        return Fraction(0), False, tie_any
    if len(tied) == 1:
        return Fraction(1), False, False
    return (Fraction(1, len(tied)) if tie == "random" else Fraction(0)), True, True


def _check(answers: Sequence[Optional[str]], correct: str, k: int, tie: str) -> None:
    if not isinstance(correct, str):
        raise ValueError("`correct` must be the right answer as a string")
    if tie not in ("random", "wrong"):
        raise ValueError("tie must be 'random' or 'wrong'")
    if not 1 <= k <= len(answers):
        raise ValueError(f"k must be between 1 and the number of samples ({len(answers)}), got {k}")


def _exact(answers: Sequence[Optional[str]], correct: str, k: int, tie: str) -> Tuple[Fraction, Fraction, Fraction]:
    n = len(answers)
    counts = Counter(a for a in answers if a is not None)
    c0 = counts.pop(correct, 0)
    n_none = sum(1 for a in answers if a is None)
    states: Dict[Tuple[int, int, int], int] = {(0, 0, 0): 1}       # (drawn, top count among wrong answers, how many hold it)
    for c in counts.values():
        nxt: Dict[Tuple[int, int, int], int] = defaultdict(int)
        for (dr, mx, mu), w in states.items():
            for s in range(0, min(c, k - dr) + 1):
                ww = w * math.comb(c, s)
                if s == 0:
                    key = (dr, mx, mu)
                elif s > mx:
                    key = (dr + s, s, 1)
                elif s == mx:
                    key = (dr + s, mx, mu + 1)
                else:
                    key = (dr + s, mx, mu)
                nxt[key] += ww
        states = nxt
    credit, decided, any_tie = Fraction(0), 0, 0
    for (dr, mx, mu), w in states.items():
        for t in range(0, min(c0, k - dr) + 1):
            u = k - t - dr                                           # Nones drawn
            if not 0 <= u <= n_none:
                continue
            ww = w * math.comb(c0, t) * math.comb(n_none, u)
            if t > 0 and t == mx and mu >= 1:
                decided += ww
                any_tie += ww
                if tie == "random":
                    credit += Fraction(ww, mu + 1)
            elif t > mx:
                credit += ww
            elif mx > t and mu >= 2:
                any_tie += ww
    total = math.comb(n, k)
    return credit / total, Fraction(decided, total), Fraction(any_tie, total)


def _sampled(answers: Sequence[Optional[str]], correct: str, k: int, tie: str, ndraws: int, seed: int):
    rng = random.Random(seed)
    idx = range(len(answers))
    total = total_sq = 0.0
    decided = any_tie = 0
    for _ in range(ndraws):
        cr, dec, anyt = _credit([answers[i] for i in rng.sample(idx, k)], correct, tie)
        c = float(cr)
        total += c
        total_sq += c * c
        decided += dec
        any_tie += anyt
    mean = total / ndraws
    var = max(0.0, (total_sq - ndraws * mean * mean) / (ndraws - 1))
    return mean, math.sqrt(var / ndraws), decided / ndraws, any_tie / ndraws


def vote_accuracy_at_k(answers: Sequence[Optional[str]], correct: str, k: int, ndraws: int = 1000,
                       seed: int = DEFAULT_SEED, tie: str = "random", mode: str = "auto",
                       max_distinct: int = MAX_EXACT_DISTINCT) -> Dict[str, object]:
    """Expected accuracy of a plurality vote over k of the samples. mode: "auto" (exact when the number of distinct
    wrong answers is at most `max_distinct`, else sampled), "exact" or "sampled". Returns acc, method, ndraws (random
    subsets drawn; 0 when exact), mc_se (0.0 when exact), n_subsets, tie_decided_share, tie_any_share."""
    _check(answers, correct, k, tie)
    if mode not in ("auto", "exact", "sampled"):
        raise ValueError("mode must be 'auto', 'exact' or 'sampled'")
    n = len(answers)
    wrong_distinct = len({a for a in answers if a is not None and a != correct})
    if k == n:
        cr, dec, anyt = _credit(answers, correct, tie)
        return {"acc": float(cr), "method": "exact", "ndraws": 0, "mc_se": 0.0, "n_subsets": 1,
                "tie_decided_share": float(dec), "tie_any_share": float(anyt)}
    use_exact = mode == "exact" or (mode == "auto" and wrong_distinct <= max_distinct)
    if use_exact:
        acc, dec, anyt = _exact(answers, correct, k, tie)
        return {"acc": float(acc), "method": "exact", "ndraws": 0, "mc_se": 0.0, "n_subsets": math.comb(n, k),
                "tie_decided_share": float(dec), "tie_any_share": float(anyt)}
    if ndraws < MIN_DRAWS:
        raise ValueError(f"a sampled estimate needs at least {MIN_DRAWS} subsets")
    acc, se, dec, anyt = _sampled(answers, correct, k, tie, ndraws, seed)
    return {"acc": acc, "method": "sampled", "ndraws": ndraws, "mc_se": se, "n_subsets": math.comb(n, k),
            "tie_decided_share": dec, "tie_any_share": anyt}


def vote_curve(answers: Sequence[Optional[str]], correct: str, kmax: int = 40, detail: bool = False,
               **kw) -> Union[List[float], List[Dict[str, object]]]:
    """The accuracy for k = 1..min(kmax, len(answers)); entry i is for k = i + 1. With detail=True each entry is the
    full dict from vote_accuracy_at_k plus its k. Keyword arguments (ndraws, seed, tie, mode) pass through; every k
    uses the same seed."""
    out = []
    for k in range(1, min(kmax, len(answers)) + 1):
        r = vote_accuracy_at_k(answers, correct, k, **kw)
        out.append(dict(r, k=k) if detail else r["acc"])
    return out  # type: ignore[return-value]


def _to_fraction(x: object) -> Fraction:
    """An exact rational from a Fraction, int, Decimal or string; a float goes through its shortest repr (29.4 -> 147/5)."""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return Fraction(repr(x))
    return Fraction(x) if not isinstance(x, str) else Fraction(x.strip())


def interpolated_vote_accuracy(answers: Sequence[Optional[str]], correct: str, kstar: object, cap: int = 40,
                               **kw) -> Dict[str, object]:
    """The vote score at a non-integer k* (D-33 item 9), for ONE base puzzle: a linear interpolation in ACCURACY,
    acc = (1 - f) * vote@floor(k*) + f * vote@ceil(k*), f = k* - floor(k*), each vote@k being vote_accuracy_at_k.
    k* is first held to min(cap, number of samples): beyond that there is no extrapolation and the score is
    vote@(that limit), and nothing above the limit is evaluated. A whole k* (f = 0) is just vote@k*: vote@(k* + 1)
    is not evaluated. k* below 1 is an error (H1 is not run then). Keyword arguments (ndraws, seed, tie, mode) pass through.
    Returns acc, k_lo, k_hi (equal when f = 0), weight (f, a float; `weight_exact` is the fraction as text), kstar
    (the k* actually used, a float), kstar_given (as text), capped and the two underlying vote@k dicts."""
    ks = _to_fraction(kstar)
    if ks < 1:
        raise ValueError(f"k* must be at least 1 (below 1 H1 is not run), got {float(ks)}")
    limit = min(cap, len(answers))
    capped = ks > limit
    used = Fraction(limit) if capped else ks
    k_lo = math.floor(used)
    f = used - k_lo
    lo = vote_accuracy_at_k(answers, correct, k_lo, **kw)
    if f == 0:
        return {"acc": lo["acc"], "k_lo": k_lo, "k_hi": k_lo, "weight": 0.0, "weight_exact": "0", "kstar": float(used),
                "kstar_given": str(ks), "capped": capped, "at_lo": lo, "at_hi": None}
    k_hi = k_lo + 1
    hi = vote_accuracy_at_k(answers, correct, k_hi, **kw)
    acc = float(1 - f) * lo["acc"] + float(f) * hi["acc"]          # type: ignore[operator]
    return {"acc": acc, "k_lo": k_lo, "k_hi": k_hi, "weight": float(f), "weight_exact": str(f), "kstar": float(used),
            "kstar_given": str(ks), "capped": False, "at_lo": lo, "at_hi": hi}
