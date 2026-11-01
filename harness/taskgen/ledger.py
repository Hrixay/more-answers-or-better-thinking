"""Third puzzle family: a ledger of budget lines under bookkeeping rules (Karen's F1; D-56). DRAFT until Edith has reviewed it.

The state is a list of `lines` whole-number balances ("budget lines measured in whole units": no currency, no people, nothing
moves to anyone outside). One step is one printed rule applied to the current balances. A puzzle prints 24 rules, each used
exactly once, then the sequences, wired as w chains of depth d (24x1 ... 1x24) exactly as in puzzle.py: the same seed gives the
same 24 rules in the same order at every wiring; only the start balances and the wiring change.

Why this family: a digit puzzle is a round function (tables, permutations, an affine mix). The ledger has meaningful, NON-invertible
bookkeeping rules instead: percentages, thresholds, "the largest line", rounding. That loses the bijection guarantee digits had, so
three guards replace it (Edith's L1-L3, ops/reviews/2026-10-10-task-families-r1.md):

- L1: EVERY step changes the state (a rule that does nothing is a skippable step), on the chain and on each 24x1 piece, and the
  simulation-based skip search finds no stretch of two or more steps, and no 1, 2 or 3 steps, that can be left out.
- L2: ABSORPTION is measured by simulation (perturb one balance by one unit after step k, run the rest, count how often the final
  state still matches) and capped in advance (`ABSORPTION_CAP`). The number of rules that overwrite earlier state is capped per
  rulebook.
- L3: no ambiguity: every amount is a whole number with a stated rounding; ties for "the largest/smallest line" go to the line
  listed first; no rule can make a balance negative; the independent re-solver (ledger_check.py) parses the printed prompt and
  must reproduce every stored state.

How the rules are drawn: the rule KINDS come first, then each rule's numbers are drawn against a reference trajectory (the 1x24
chain from its start), so that every rule fires and changes the state at its place. The 24 pieces of a 24x1 puzzle start from
perturbed copies of the reference states, so the same rule fires there as well.
"""

from __future__ import annotations

import itertools
import json
import dataclasses
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .rng import HashRNG

LV_VERSION = "ledger-0.5"       # 0.4.2 plus the D-86 presets l14n4..l14n16 (N steps); no 24-step output changes (Edith lock-2 L2-3: new code, new string)
NAMES = ("Rent", "Payroll", "Supplies", "Reserve", "Travel", "Training", "Utilities", "Insurance", "Fuel", "Repairs", "Software", "Legal")
STRICT_REFERENCE_CAPS = True       # cap EACH transfer-slip size (1, 10, 100; k = 0..23) and the house-rule omit/double slips at ABSORPTION_CAP, measured on the
                                  # REFERENCE chain (the chain the 1x24 models see). The skip search and the single-unit guard also run on the five jittered probes.
ABSORPTION_CAP = 0.05          # share of single-unit slips that may vanish (Edith's L2 example; she sets the final number)
OVERWRITE_KINDS = ("top_up", "cap_move", "level_pair", "split")


@dataclass(frozen=True)
class LParams:
    total_steps: int = 24
    lines: int = 4                  # budget lines, 3..6
    digits: int = 4                 # balances start around 10^(digits-1) .. 10^digits
    overwrite_max: int = 3          # at most this many overwrite-type rules per rulebook
    max_per_kind: int = 4
    hard: bool = False              # arbitrary percentages 3..97 and arbitrary (not round) amounts
    repeat_n: int = 3               # how many times a repeat rule repeats (3..5)
    house_fires: Tuple[int, int] = (5, 8)   # the house rule must act on this many of the 24 reference steps (inclusive)
    house: bool = False             # a standing "house rule" runs straight after every rule (its threshold is tuned per puzzle)
    decoys: int = 0                 # extra rules printed in the rulebook that no sequence uses (near-duplicates of used rules)
    kinds: Tuple[str, ...] = ("move_pct_down", "move_pct_near", "top_up", "two_clause", "fee_largest", "interest",
                              "split", "pay", "levy", "boost_smallest", "cap_move", "level_pair")

    def validate(self) -> None:
        if self.total_steps not in STEP_COUNTS:
            raise ValueError(f"the ledger is built for {STEP_COUNTS} steps (D-86: the ladder lengths and the original 24)")
        if not 3 <= self.lines <= len(NAMES):
            raise ValueError(f"lines must be 3..{len(NAMES)}")
        if not 0 <= self.house_fires[0] <= self.house_fires[1] <= self.total_steps:
            raise ValueError(f"house_fires must be a window inside 0..{self.total_steps}")
        if not 3 <= self.repeat_n <= 5:
            raise ValueError("repeat_n must be 3..5")
        if not 0 <= self.decoys <= 8:
            raise ValueError("decoys must be 0..8")
        if self.lines < 4 and "rank_move" in self.kinds:
            raise ValueError("rank rules need at least 4 lines")
        if not 3 <= self.digits <= 6:
            raise ValueError("digits must be 3..6")
        unknown = [k for k in self.kinds if k not in KINDS]
        if unknown:
            raise ValueError(f"unknown rule kinds {unknown}")
        if len(self.kinds) * self.max_per_kind < self.total_steps:
            raise ValueError(f"too few rule kinds for {self.total_steps} distinct rules")


HARD_KINDS = ("move_pct_down", "move_pct_near", "top_up", "two_clause", "fee_largest", "interest", "pay", "levy",
              "pct_total", "compare_move", "excess_share", "three_way", "largest_to_smallest", "first_below", "boost_smallest",
              "split")

COMPLEX_KINDS = ("two_clause", "top_up", "pct_total", "compare_move", "excess_share", "three_way", "largest_to_smallest",
                 "first_below", "cap_move", "level_pair")

# Presets, fixed in advance (named like digits: higher = harder). The pilot picks one by D-36's rule.
SETTINGS: Dict[str, LParams] = {
    "l0": LParams(lines=3, digits=3, overwrite_max=2),
    "l1": LParams(lines=4, digits=4, overwrite_max=3),
    "l2": LParams(lines=4, digits=5, overwrite_max=3),
    "l3": LParams(lines=5, digits=5, overwrite_max=3),
    "l4": LParams(lines=6, digits=6, overwrite_max=3),
    # harder per-rule content (the free read of l1-l4 found Haiku near 100%): arbitrary percentages and amounts, and rules that
    # combine or compare two lines. Same 24 steps (D-16).
    # Per Jarvis (the user's D-25): difficulty from the procedure (more lines, rules that compare or combine lines), not from big arithmetic.
    "l5": LParams(lines=5, digits=5, overwrite_max=3, hard=True, kinds=HARD_KINDS),
    "l6": LParams(lines=6, digits=5, overwrite_max=3, hard=True, kinds=HARD_KINDS),
    "l7": LParams(lines=8, digits=5, overwrite_max=3, hard=True, kinds=HARD_KINDS),
    # the second free read found Haiku still near 90% at l5-l7: more lines, and only the compound rules that combine or compare lines
    "l8": LParams(lines=8, digits=5, overwrite_max=4, hard=True, kinds=COMPLEX_KINDS, max_per_kind=4),
    "l9": LParams(lines=12, digits=5, overwrite_max=4, hard=True, kinds=COMPLEX_KINDS, max_per_kind=4),
}

# the third read found Haiku still near 90% at l8-l9: more lines and compound rules are not the dial. These kinds ask more of ONE step:
# a simultaneous update, a step done three times, a rank-based pick, a count that sets the amount.
STEP_KINDS = ("avg_donors", "repeat_l2s", "rank_move", "count_move")
SETTINGS["l10"] = LParams(lines=6, digits=5, overwrite_max=3, hard=True, max_per_kind=4,
                          kinds=STEP_KINDS + ("two_clause", "compare_move", "excess_share", "pct_total", "largest_to_smallest"))
SETTINGS["l11"] = LParams(lines=8, digits=5, overwrite_max=3, hard=True, max_per_kind=5, decoys=7,
                          kinds=STEP_KINDS + ("two_clause", "compare_move"))

# l12 and l13 (no free read; the pilot measures them): more weight on the two kinds Haiku slipped on in read 4 (repeat, simultaneous
# average), the repeat done five times, more lines, eight decoys.
SETTINGS["l12"] = LParams(lines=8, digits=5, overwrite_max=3, hard=True, max_per_kind=7, decoys=8, repeat_n=5,
                          kinds=("repeat_l2s", "repeat_l2s", "avg_donors", "avg_donors", "rank_move", "count_move", "two_clause"))
SETTINGS["l13"] = LParams(lines=10, digits=5, overwrite_max=3, hard=True, max_per_kind=8, decoys=8, repeat_n=5,
                          kinds=("repeat_l2s", "repeat_l2s", "repeat_l2s", "avg_donors", "avg_donors", "avg_donors", "rank_move", "count_move"))

# l14 and l15: the difficulty comes from procedure on a ROUND-number base (round percentages and amounts, 4-digit balances): rules that
# make the model look again after the first move (fixed amounts larger than the deciding gap), plus a house rule after every step,
# tuned per puzzle to act on 5-8 of the 24 steps. The percentage repeat of l10-l13 is not used here.
LOOK_KINDS = ("repick2", "repeat_fixed")
SETTINGS["l14"] = LParams(lines=6, digits=4, overwrite_max=3, hard=False, max_per_kind=6, house=True, repeat_n=3,
                          kinds=LOOK_KINDS + ("rank_move", "count_move", "avg_donors", "two_clause", "compare_move"))
SETTINGS["l15"] = LParams(lines=8, digits=4, overwrite_max=3, hard=False, max_per_kind=7, house=True, repeat_n=3, decoys=6,
                          kinds=LOOK_KINDS + LOOK_KINDS + ("rank_move", "count_move", "avg_donors", "two_clause"))

# D-86 (declared deviation, shorter puzzles): the l14 rules at N steps, N in the ladder {4, 6, 8, 12, 16}. Everything else is l14's: the
# rule kinds, wording, guards and caps. The house rule's window scales with N: l14 asks it to act on 5 to 8 of 24 steps, so at N it acts on
# max(1, floor(5N/24)) to max(that, ceil(8N/24)) steps (N = 4: 1-2, 6: 1-2, 8: 1-3, 12: 2-4, 16: 3-6).
LADDER_STEPS = (4, 6, 8, 12, 16)
STEP_COUNTS = LADDER_STEPS + (24,)


def house_window(n: int, at24: Tuple[int, int] = (5, 8)) -> Tuple[int, int]:
    lo = max(1, (at24[0] * n) // 24)
    hi = max(lo, -(-at24[1] * n // 24))
    return lo, hi


for _n in LADDER_STEPS:
    SETTINGS[f"l14n{_n}"] = dataclasses.replace(SETTINGS["l14"], total_steps=_n, house_fires=house_window(_n))

# l10, l12 and l13 were interim presets (percentage repeats). Under the transfer-slip cap (Edith's B1) they cannot be built in 400 attempts
# (l10: skippable steps and transfer absorption; l12 and l13: too few distinct rule texts), so they are retired; l11 and l14 to l15 build.
RETIRED = ("l10", "l12", "l13")

# l16: the in-turn sweep (the brainstorm's report, part C) joins the look-again rules; more lines, the repeat five times, a house rule that acts on
# 9-12 of the 24 steps, and 8 decoys.
SETTINGS["l16"] = LParams(lines=10, digits=4, overwrite_max=3, hard=False, max_per_kind=6, house=True, house_fires=(9, 12), repeat_n=5, decoys=8,
                          kinds=LOOK_KINDS + LOOK_KINDS + ("sweep", "sweep", "rank_move", "count_move", "avg_donors", "two_clause"))

# l17: the spare rung, one notch above l16 (12 lines, the house rule on 11-14 steps, more sweeps and look-again rules). Built and frozen in case every
# pilot preset comes in above 60% on the API; it runs only then.
SETTINGS["l17"] = LParams(lines=12, digits=4, overwrite_max=3, hard=False, max_per_kind=7, house=True, house_fires=(11, 14), repeat_n=5, decoys=8,
                          kinds=LOOK_KINDS + LOOK_KINDS + ("sweep", "sweep", "sweep", "rank_move", "avg_donors"))

State = Tuple[int, ...]


# ---------------------------------------------------------------- rule kinds

@dataclass(frozen=True)
class House:
    """The house rule: straight after a rule, if the smallest line is below t, move a units to it from the largest line (or all of
    that line if it holds fewer); nothing moves when they are the same line. Acts once, on the rule's result."""
    t: int
    a: int

    def after(self, s) -> State:
        s = list(s)
        lo, hi = s.index(min(s)), s.index(max(s))
        if s[lo] < self.t and lo != hi:
            mv = min(self.a, s[hi])
            s[hi] -= mv
            s[lo] += mv
        return tuple(s)

    def text(self) -> str:
        return (f"House rule: straight after every rule, as part of the same step, if the line with the smallest balance is below "
                f"{self.t}, move {self.a} units to it from the line with the largest balance, or all of that line if it holds fewer. "
                f"The house rule acts at most once per step, always after that step's own rule, and does not act again on its own "
                f"result. If the largest and the smallest line are the same line, nothing moves. The balances you write for a step "
                f"are the ones after the house rule.")


@dataclass(frozen=True)
class Rule:
    label: str
    kind: str
    a: Dict[str, int]
    house: Optional[House] = None

    def bare(self, s: State) -> State:
        return KINDS[self.kind][0](self.a, list(s))

    def apply(self, s: State) -> State:
        """The whole step: the rule, then the house rule when the puzzle has one. Every guard sees this composite."""
        t = KINDS[self.kind][0](self.a, list(s))
        return self.house.after(t) if self.house is not None else t

    def text(self, names: Sequence[str]) -> str:
        return KINDS[self.kind][1](self.a, names)


def _move_down(a, s):
    amt = s[a["src"]] * a["p"] // 100
    s[a["src"]] -= amt
    s[a["dst"]] += amt
    return tuple(s)


def _move_near(a, s):
    amt = (s[a["src"]] * a["p"] + 50) // 100
    s[a["src"]] -= amt
    s[a["dst"]] += amt
    return tuple(s)


def _top_up(a, s):
    if s[a["a"]] < a["t"]:
        mv = min(a["t"] - s[a["a"]], s[a["b"]])
        s[a["a"]] += mv
        s[a["b"]] -= mv
    return tuple(s)


def _two_clause(a, s):
    if s[a["a"]] > a["t"]:
        mv = s[a["a"]] * a["p"] // 100
        s[a["a"]] -= mv
        s[a["b"]] += mv
    else:
        s[a["a"]] += a["y"]
    return tuple(s)


def _fee_largest(a, s):
    i = s.index(max(s))
    s[i] -= min(a["f"], s[i])
    return tuple(s)


def _interest(a, s):
    s[a["a"]] += (s[a["a"]] * a["p"] + 50) // 100
    return tuple(s)


def _split(a, s):
    h = s[a["a"]] // 2
    s[a["b"]] += h
    s[a["c"]] += h
    s[a["a"]] -= 2 * h
    return tuple(s)


def _pay(a, s):
    m = min(a["k"], s[a["a"]])
    s[a["a"]] -= m
    s[a["b"]] += m
    return tuple(s)


def _levy(a, s):
    s[a["a"]] -= s[a["a"]] * a["p"] // 100
    return tuple(s)


def _boost_smallest(a, s):
    s[s.index(min(s))] += a["y"]
    return tuple(s)


def _cap_move(a, s):
    if s[a["a"]] > a["t"]:
        ex = s[a["a"]] - a["t"]
        s[a["a"]] = a["t"]
        s[a["b"]] += ex
    return tuple(s)


def _level_pair(a, s):
    tot = s[a["a"]] + s[a["b"]]
    s[a["a"]] = tot - tot // 2
    s[a["b"]] = tot // 2
    return tuple(s)


def _largest_to_smallest(a, s):
    i, j = s.index(max(s)), s.index(min(s))
    mv = s[i] * a["p"] // 100 if i != j else 0
    s[i] -= mv
    s[j] += mv
    return tuple(s)


def _first_below(a, s):
    for k, v in enumerate(s):
        if v < a["t"]:
            s[k] += a["y"]
            return tuple(s)
    s[s.index(min(s))] += a["y"]
    return tuple(s)


def _pct_total(a, s):
    amt = min((s[a["src"]] + s[a["other"]]) * a["p"] // 100, s[a["src"]])
    s[a["src"]] -= amt
    s[a["dst"]] += amt
    return tuple(s)


def _compare_move(a, s):
    if s[a["a"]] > 2 * s[a["b"]]:
        mv = s[a["a"]] * a["p"] // 100
        s[a["a"]] -= mv
        s[a["b"]] += mv
    else:
        mv = s[a["b"]] * a["p"] // 100
        s[a["b"]] -= mv
        s[a["c"]] += mv
    return tuple(s)


def _excess_share(a, s):
    if s[a["a"]] >= s[a["b"]]:
        d = (s[a["a"]] - s[a["b"]]) * a["p"] // 100
        s[a["a"]] -= d
    else:
        d = (s[a["b"]] - s[a["a"]]) * a["p"] // 100
        s[a["b"]] -= d
    s[a["c"]] += d
    return tuple(s)


def _three_way(a, s):
    if s[a["a"]] < a["t1"]:
        s[a["a"]] += a["y"]
    elif s[a["a"]] > a["t2"]:
        mv = s[a["a"]] * a["p"] // 100
        s[a["a"]] -= mv
        s[a["b"]] += mv
    else:
        m = min(a["q"], s[a["b"]])
        s[a["b"]] -= m
        s[a["a"]] += m
    return tuple(s)


def _avg_donors(a, s):
    """Simultaneous: the average, the smallest line and every amount come from the balances before the rule."""
    avg = sum(s) // len(s)
    j = s.index(min(s))
    before = list(s)
    for i, v in enumerate(before):
        if v > avg:
            mv = v * a["p"] // 100
            s[i] -= mv
            s[j] += mv
    return tuple(s)


REPEAT_WORDS = {3: "three", 4: "four", 5: "five"}


def _repeat_l2s(a, s):
    for _ in range(a.get("n", 3)):
        i, j = s.index(max(s)), s.index(min(s))
        if i != j:
            mv = s[i] * a["p"] // 100
            s[i] -= mv
            s[j] += mv
    return tuple(s)


def _rank_move(a, s):
    n = len(s)
    i = sorted(range(n), key=lambda k: (-s[k], k))[1]
    j = sorted(range(n), key=lambda k: (s[k], k))[1]
    mv = s[i] * a["p"] // 100
    s[i] -= mv
    s[j] += mv
    return tuple(s)


def _count_move(a, s):
    c = sum(1 for v in s if v < a["t"])
    j = s.index(min(s))
    mv = min(c * a["k"], s[a["src"]])
    s[a["src"]] -= mv
    s[j] += mv
    return tuple(s)


def _largest(s):
    return s.index(max(s))


def _repick2(a, s):
    i, j = _largest(s), s.index(min(s))
    mv = min(a["A"], s[i])
    s[i] -= mv
    s[j] += mv
    k = _largest(s)                                   # the line that NOW has the largest balance
    s[k] -= min(a["B"], s[k])
    return tuple(s)


def _repeat_fixed(a, s):
    for _ in range(a["n"]):
        i, j = _largest(s), s.index(min(s))
        mv = min(a["A"], s[i])
        s[i] -= mv
        s[j] += mv
    return tuple(s)


def _sweep(a, s):
    """In turn, in the order of the lines: a line above T when its turn comes gives A units to the smallest OTHER line at that moment."""
    for i in range(len(s)):
        if s[i] > a["T"]:
            j = min((k for k in range(len(s)) if k != i), key=lambda k: (s[k], k))
            s[i] -= a["A"]
            s[j] += a["A"]
    return tuple(s)


def _sweep_trace(a, s):
    """(number of givers, set of receivers, any tie or threshold hit) when the sweep runs from s."""
    x = list(s)
    givers, receivers, unclear_ = 0, set(), False
    for i in range(len(x)):
        if x[i] == a["T"]:
            unclear_ = True
        if x[i] > a["T"]:
            others = [k for k in range(len(x)) if k != i]
            low = min(x[k] for k in others)
            if sum(1 for k in others if x[k] == low) > 1:
                unclear_ = True
            j = min(others, key=lambda k: (x[k], k))
            x[i] -= a["A"]
            x[j] += a["A"]
            givers += 1
            receivers.add(j)
    return givers, receivers, unclear_


def house_acts(rule: "Rule", s: State) -> bool:
    """Does the house rule change the state after this rule's result at s? (False for a rule with no house rule.)"""
    if rule.house is None:
        return False
    b = rule.bare(s)
    return rule.house.after(b) != b


def picks_change(rule: "Rule", s: State) -> bool:
    """For the 'look again' kinds: does the pick made after the first move differ from the first pick at this state? (The
    deciding gap must be smaller than the amount, here AND at every piece start, or the slip 'reuse the first pick' costs nothing.)
    Always True for every other kind."""
    a = rule.a
    if rule.kind == "repick2":
        x = list(s)
        i, j = _largest(x), x.index(min(x))
        mv = min(a["A"], x[i])
        x[i] -= mv
        x[j] += mv
        return _largest(x) != i
    if rule.kind == "sweep":
        givers, receivers, _ = _sweep_trace(a, s)
        return 2 <= givers <= 4 and len(receivers) >= 2
    if rule.kind == "repeat_fixed":
        x = list(s)
        seen = set()
        trail = []
        moves = []
        for _ in range(a["n"]):
            i, j = _largest(x), x.index(min(x))
            seen.add((i, j))
            moves.append((i, j))
            mv = min(a["A"], x[i])
            x[i] -= mv
            x[j] += mv
            trail.append(tuple(x))
        if len(seen) < 2:
            return False
        if any(c == trail[-1] for c in trail[:-1]):                       # Edith M2: doing fewer moves must give a different state
            return False
        if rule.house is not None:                                       # Edith R3-3: ... also once the house rule has acted on both
            end = rule.house.after(trail[-1])
            if any(rule.house.after(c) == end for c in trail[:-1]):
                return False
        return all(moves[q] != (moves[q - 1][1], moves[q - 1][0]) for q in range(1, len(moves)))      # and no move may reverse the one before
    return True


# kind -> (apply, text). The wording is the contract the independent re-solver reads back (ledger_check.py).
KINDS: Dict[str, Tuple[Callable, Callable]] = {
    "move_pct_down": (_move_down, lambda a, n: f"Move {a['p']}% of {n[a['src']]} to {n[a['dst']]}, rounding the amount down to a whole unit."),
    "move_pct_near": (_move_near, lambda a, n: f"Move {a['p']}% of {n[a['src']]} to {n[a['dst']]}, rounding the amount to the nearest whole unit (a half rounds up)."),
    "top_up": (_top_up, lambda a, n: f"If {n[a['a']]} is below {a['t']}, move units from {n[a['b']]} to {n[a['a']]} until {n[a['a']]} reaches {a['t']}, or move all of {n[a['b']]} if it holds fewer."),
    "two_clause": (_two_clause, lambda a, n: f"If {n[a['a']]} is above {a['t']}, move {a['p']}% of {n[a['a']]} to {n[a['b']]}, rounding the amount down to a whole unit; otherwise add {a['y']} units to {n[a['a']]}."),
    "fee_largest": (_fee_largest, lambda a, n: f"Remove {a['f']} units from the line with the largest balance, or all of it if it holds fewer."),
    "interest": (_interest, lambda a, n: f"Increase {n[a['a']]} by {a['p']}%, rounding the increase to the nearest whole unit (a half rounds up)."),
    "split": (_split, lambda a, n: f"Share {n[a['a']]} equally between {n[a['b']]} and {n[a['c']]}: each of them receives half of {n[a['a']]} rounded down, and any unit left over stays in {n[a['a']]}."),
    "pay": (_pay, lambda a, n: f"Move {a['k']} units from {n[a['a']]} to {n[a['b']]}, or all of {n[a['a']]} if it holds fewer."),
    "levy": (_levy, lambda a, n: f"Remove {a['p']}% of {n[a['a']]}, rounding the amount down to a whole unit."),
    "boost_smallest": (_boost_smallest, lambda a, n: f"Add {a['y']} units to the line with the smallest balance."),
    "cap_move": (_cap_move, lambda a, n: f"If {n[a['a']]} is above {a['t']}, move everything above {a['t']} from {n[a['a']]} to {n[a['b']]}."),
    "largest_to_smallest": (_largest_to_smallest, lambda a, n: f"Move {a['p']}% of the line with the largest balance to the line with the smallest balance, rounding the amount down to a whole unit."),
    "first_below": (_first_below, lambda a, n: f"Add {a['y']} units to the first line, in the order above, whose balance is below {a['t']}; if no line is below {a['t']}, add {a['y']} units to the line with the smallest balance."),
    "pct_total": (_pct_total, lambda a, n: f"Move {a['p']}% of the combined balance of {n[a['src']]} and {n[a['other']]} from {n[a['src']]} to {n[a['dst']]}, rounding the amount down to a whole unit, or move all of {n[a['src']]} if it holds fewer."),
    "compare_move": (_compare_move, lambda a, n: f"If {n[a['a']]} is more than twice {n[a['b']]}, move {a['p']}% of {n[a['a']]} to {n[a['b']]}; otherwise move {a['p']}% of {n[a['b']]} to {n[a['c']]}. Each amount is rounded down to a whole unit."),
    "excess_share": (_excess_share, lambda a, n: f"Take {a['p']}% of the difference between {n[a['a']]} and {n[a['b']]}, rounded down to a whole unit, from the larger of the two (from {n[a['a']]} if they are equal) and add it to {n[a['c']]}."),
    "three_way": (_three_way, lambda a, n: f"If {n[a['a']]} is below {a['t1']}, add {a['y']} units to {n[a['a']]}; if {n[a['a']]} is above {a['t2']}, move {a['p']}% of {n[a['a']]} to {n[a['b']]}, rounding the amount down to a whole unit; otherwise move {a['q']} units from {n[a['b']]} to {n[a['a']]}, or all of {n[a['b']]} if it holds fewer."),
    "avg_donors": (_avg_donors, lambda a, n: f"Work out the average of all the balances, rounded down to a whole unit. Every line whose balance is above the average gives {a['p']}% of its own balance, rounded down to a whole unit, to the line with the smallest balance. Work out the average, the smallest line and every amount from the balances before this rule, not from balances changed during it."),
    "repeat_l2s": (_repeat_l2s, lambda a, n: f"Do this {REPEAT_WORDS[a.get('n', 3)]} times in a row: move {a['p']}% of the line with the largest balance to the line with the smallest balance, rounding the amount down to a whole unit. Find the largest and the smallest line again each time."),
    "rank_move": (_rank_move, lambda a, n: f"The line with the second-largest balance gives {a['p']}% of its balance, rounded down to a whole unit, to the line with the second-smallest balance. Where balances are equal, the line listed first in the order above counts first, whether counting from the largest or from the smallest."),
    "count_move": (_count_move, lambda a, n: f"Count the lines whose balance is below {a['t']}. Move that count times {a['k']} units from {n[a['src']]} to the line with the smallest balance, or all of {n[a['src']]} if it holds fewer. Count the lines and find the smallest line before moving anything."),
    "sweep": (_sweep, lambda a, n: f"Go through the lines one at a time, in the order above. Each line whose balance is above {a['T']} when its turn comes gives {a['A']} units to the line, other than itself, that has the smallest balance at that moment."),
    "repick2": (_repick2, lambda a, n: f"Move {a['A']} units from the line with the largest balance to the line with the smallest balance, or all of it if it holds fewer; then remove {a['B']} units from the line that now has the largest balance, or all of it if it holds fewer."),
    "repeat_fixed": (_repeat_fixed, lambda a, n: f"Do this {REPEAT_WORDS[a['n']]} times in a row: move {a['A']} units from the line with the largest balance to the line with the smallest balance, or all of it if it holds fewer. Find the largest and the smallest line again each time."),
    "level_pair": (_level_pair, lambda a, n: f"Make {n[a['a']]} and {n[a['b']]} as equal as possible: together they keep their total, {n[a['b']]} gets half of it rounded down, and {n[a['a']]} gets the rest."),
}


# ---------------------------------------------------------------- drawing one rule against the reference state

def _distinct_lines(rng: HashRNG, n: int, k: int) -> List[int]:
    idx = list(range(n))
    out = []
    for _ in range(k):
        out.append(idx.pop(rng.randbelow(len(idx))))
    return out


_CANDIDATES: Dict[tuple, List[Dict[str, int]]] = {}
_RULEBOOKS: Dict[tuple, tuple] = {}


def _search_candidates(kind: str, s: State, p: LParams) -> List[Dict[str, int]]:
    """Every (T, A) of the in-turn sweep, or every A of the fixed repeat, that passes the pick predicates at this state (a rule slot draws many times
    at one state, so the list is computed once and reused)."""
    n = len(s)
    ordered = sorted(s)
    cands: List[Dict[str, int]] = []
    if kind == "sweep":
        for k in (2, 3, 4):                                            # 2 to 4 givers
            base = ((ordered[n - k - 1] + ordered[n - k]) // 2 // 100) * 100
            for thr in (base, base + 100):
                for amount in range(50, min(thr - 50, 1500) + 1, 50):
                    a_ = {"T": thr, "A": amount}
                    if picks_change(Rule("_", "sweep", a_), s) and not _sweep_trace(a_, s)[2]:
                        cands.append(a_)
    else:
        for amount in range(50, 3001, 50):
            a_ = {"A": amount, "n": p.repeat_n}
            if picks_change(Rule("_", "repeat_fixed", a_), s):
                cands.append(a_)
    return cands


def _draw_rule(rng: HashRNG, kind: str, s: State, p: LParams) -> Optional[Dict[str, int]]:
    """Numbers for one rule of `kind`, drawn against the reference balances `s` so that the rule fires at this place; None when no numbers
    can work at this state (the sweep and the fixed repeat, whose candidates are searched exhaustively)."""
    n = p.lines
    M = 10 ** (p.digits - 1) * 5            # typical balance
    if p.hard:
        pct = lambda: 3 + rng.randbelow(95)                                               # 3..97, not round
        small = lambda lo, hi: max(1, M * (lo + rng.randbelow(hi - lo + 1)) // 100 + rng.randbelow(max(2, M // 90)))
    else:
        pct = lambda: (5, 8, 10, 12, 15, 20, 25, 30, 40)[rng.randbelow(9)]
        small = lambda lo, hi: max(1, M * (lo + rng.randbelow(hi - lo + 1)) // 100)  # lo..hi percent of M
    if kind in ("move_pct_down", "move_pct_near"):
        src, dst = _distinct_lines(rng, n, 2)
        return {"src": src, "dst": dst, "p": pct()}
    if kind == "top_up":
        a, b = _distinct_lines(rng, n, 2)
        return {"a": a, "b": b, "t": s[a] + small(8, 35)}
    if kind == "two_clause":
        a, b = _distinct_lines(rng, n, 2)
        t = max(1, s[a] * (70 + rng.randbelow(61)) // 100)
        if p.house:                                        # the round-number base: a round threshold (the draw above is unchanged)
            t = max(100, ((t + 50) // 100) * 100)
        return {"a": a, "b": b, "t": t, "p": pct(), "y": small(3, 12)}
    if kind == "fee_largest":
        return {"f": small(3, 15)}
    if kind == "interest":
        return {"a": rng.randbelow(n), "p": (2, 3, 4, 5, 6, 8)[rng.randbelow(6)]}
    if kind == "split":
        a, b, c = _distinct_lines(rng, n, 3)
        return {"a": a, "b": b, "c": c}
    if kind == "pay":
        a, b = _distinct_lines(rng, n, 2)
        return {"a": a, "b": b, "k": small(5, 25)}
    if kind == "levy":
        return {"a": rng.randbelow(n), "p": (3, 5, 8, 10, 15, 20)[rng.randbelow(6)]}
    if kind == "boost_smallest":
        return {"y": small(3, 12)}
    if kind == "cap_move":
        a, b = _distinct_lines(rng, n, 2)
        return {"a": a, "b": b, "t": max(1, s[a] * (60 + rng.randbelow(36)) // 100)}
    if kind == "level_pair":
        a, b = _distinct_lines(rng, n, 2)
        return {"a": a, "b": b}
    if kind == "largest_to_smallest":
        return {"p": pct()}
    if kind == "first_below":
        return {"t": max(1, s[rng.randbelow(n)] * (80 + rng.randbelow(30)) // 100), "y": small(5, 20)}
    if kind == "pct_total":
        src, other, dst = _distinct_lines(rng, n, 3)
        return {"src": src, "other": other, "dst": dst, "p": pct()}
    if kind == "compare_move":
        a, b, c = _distinct_lines(rng, n, 3)
        return {"a": a, "b": b, "c": c, "p": pct()}
    if kind == "excess_share":
        a, b, c = _distinct_lines(rng, n, 3)
        return {"a": a, "b": b, "c": c, "p": pct()}
    if kind == "three_way":
        a, b = _distinct_lines(rng, n, 2)
        lo = max(1, s[a] * (60 + rng.randbelow(21)) // 100)
        hi = max(lo + 1, s[a] * (110 + rng.randbelow(31)) // 100)
        return {"a": a, "b": b, "t1": lo, "t2": hi, "p": pct(), "y": small(5, 20), "q": small(5, 25)}
    if kind in ("sweep", "repeat_fixed"):
        key = (kind, tuple(s), p.repeat_n)
        cands = _CANDIDATES.get(key)
        if cands is None:
            cands = _search_candidates(kind, s, p)
            if len(_CANDIDATES) > 20000:
                _CANDIDATES.clear()
            _CANDIDATES[key] = cands
        if cands:
            return dict(cands[rng.randbelow(len(cands))])
        return None                                                    # nothing works at this state: the caller gives up this draw (Edith R3-2)
    if kind == "repick2":
        top = sorted(s, reverse=True)
        gap = top[0] - top[1]
        lo_a = ((gap + 49) // 50) * 50 + 50                                    # larger than the deciding gap: the pick must change
        return {"A": lo_a + 50 * rng.randbelow(8), "B": small(3, 12)}
    if kind == "avg_donors" and not p.hard:
        return {"p": (5, 10, 15, 20, 25)[rng.randbelow(5)]}
    if kind == "count_move" and not p.hard:
        thr = ((sorted(s)[n // 2] * (100 + rng.randbelow(11)) // 100 + 50) // 100) * 100 + 100     # a round threshold
        return {"src": rng.randbelow(n), "t": thr, "k": small(1, 6)}
    if kind == "avg_donors":
        return {"p": 3 + rng.randbelow(28)}
    if kind == "repeat_l2s":
        return {"p": 5 + rng.randbelow(36), "n": p.repeat_n}
    if kind == "rank_move":
        return {"p": pct()}
    if kind == "count_move":
        return {"src": rng.randbelow(n), "t": sorted(s)[n // 2] * (100 + rng.randbelow(11)) // 100 + 1, "k": small(1, 6)}
    raise ValueError(kind)


def _random_state(rng: HashRNG, p: LParams) -> State:
    lo, hi = 10 ** (p.digits - 1), 10 ** p.digits
    return tuple(lo + rng.randbelow(hi - lo) for _ in range(p.lines))


def _jitter(rng: HashRNG, s: State, pct: int) -> State:
    """A copy of `s` with every balance moved by up to +-pct percent (never below 1)."""
    return tuple(max(1, v + (v * (rng.randbelow(2 * pct + 1) - pct)) // 100) for v in s)


# ---------------------------------------------------------------- the guards (L1, L2)

def run(rules: Sequence[Rule], s: State, skip: frozenset = frozenset()) -> State:
    for i, r in enumerate(rules):
        if i not in skip:
            s = r.apply(s)
    return s


def trajectory(rules: Sequence[Rule], s: State) -> List[State]:
    out = []
    for r in rules:
        s = r.apply(s)
        out.append(s)
    return out


def every_step_changes(rules: Sequence[Rule], s: State) -> bool:
    for r in rules:
        t = r.apply(s)
        if t == s:
            return False
        s = t
    return True


def _segment_clear(rules: Sequence[Rule], s: State) -> bool:
    """A middle wiring's piece (e.g. 6x4, used only by the self-test): after its first step, every step meets the same guards as a reference step
    (the bare rule changes the state, a look-again / repeat / sweep pick really changes, no pick is tied or on a threshold)."""
    for q, r in enumerate(rules):
        t = r.apply(s)
        if t == s or r.bare(s) == s or (q and (not picks_change(r, s) or unclear(r, s))):
            return False
        s = t
    return True


def find_ledger_shortcut(rules: Sequence[Rule], probes: Sequence[State]) -> Optional[Tuple[str, Tuple[int, ...]]]:
    """Simulation test (like puzzle.find_shortcut): is there a stretch of two or more consecutive steps, or any 1, 2 or 3 steps,
    that can be left out without changing the final state on some probe? Returns a description of the first one found."""
    m = len(rules)
    for s0 in probes:
        full = run(rules, s0)
        for size in (1, 2, 3):
            for combo in itertools.combinations(range(m), size):
                if run(rules, s0, frozenset(combo)) == full:
                    return "steps", combo
        for i in range(m):
            for j in range(i + 3, m):                    # stretches of four or more (two and three are in the sets above)
                if run(rules, s0, frozenset(range(i, j + 1))) == full:
                    return "stretch", (i, j)
    return None


def absorption_rate(rules: Sequence[Rule], s0: State) -> float:
    """Share of single-unit slips that leave the final state unchanged. A slip is +1 (or -1 where the balance is above 0) on
    one balance at the start (k = 0) or after one of the first 23 steps."""
    states = trajectory(rules, s0)
    final = states[-1]
    absorbed = total = 0
    at = [s0] + states[:-1]                       # the state a slip sits in: the start (k = 0), then after each of the first 23 steps
    for k in range(len(rules)):
        for j in range(len(s0)):
            for delta in (1, -1):
                v = at[k][j] + delta
                if v < 0:
                    continue
                s = list(at[k])
                s[j] = v
                t = tuple(s)
                for r in rules[k:]:
                    t = r.apply(t)
                total += 1
                absorbed += (t == final)
    return absorbed / total if total else 0.0


TRANSFER_SIZES = (1, 10, 100)


def transfer_absorption(rules: Sequence[Rule], s0: State, sizes: Sequence[int] = TRANSFER_SIZES) -> float:
    """Share of TRANSFER slips that leave the final state unchanged (Edith's B1). Almost every rule keeps the total, so the natural slip
    is a unit left on the wrong line: d units (d = 1, 10, 100) that belong on line i sit on line j instead, for every ordered pair of lines
    that the step changed, in the state after each step k = 1..23 and also at the start (k = 0, using the lines the first step changes).
    The remaining rules are replayed; a slip is absorbed when the final balances equal the reference ones."""
    states = [s0]
    for r in rules:
        states.append(r.apply(states[-1]))
    final = states[-1]
    n = len(rules)
    absorbed = total = 0
    for k in range(n):
        a, b = (states[0], states[1]) if k == 0 else (states[k - 1], states[k])
        changed = [i for i in range(len(a)) if a[i] != b[i]]
        for i in changed:
            for j in changed:
                if i == j:
                    continue
                for d in sizes:
                    if states[k][j] - d < 0:
                        continue
                    x = list(states[k])
                    x[i] += d
                    x[j] -= d
                    x = tuple(x)
                    for r in rules[k:]:
                        x = r.apply(x)
                    total += 1
                    absorbed += x == final
    return absorbed / total if total else 0.0


def transfer_absorption_by_size(rules: Sequence[Rule], s0: State, sizes: Sequence[int] = TRANSFER_SIZES) -> Dict[int, float]:
    """The transfer-slip absorption of `transfer_absorption`, one rate per slip size (Edith M1): the 10- and 100-unit slips are almost never
    absorbed, the 1-unit slip is the one that can be."""
    states = [s0]
    for r in rules:
        states.append(r.apply(states[-1]))
    final = states[-1]
    absorbed = {d: 0 for d in sizes}
    total = {d: 0 for d in sizes}
    for k in range(len(rules)):
        a, b = (states[0], states[1]) if k == 0 else (states[k - 1], states[k])
        changed = [i for i in range(len(a)) if a[i] != b[i]]
        for i in changed:
            for j in changed:
                if i == j:
                    continue
                for d in sizes:
                    if states[k][j] - d < 0:
                        continue
                    x = list(states[k])
                    x[i] += d
                    x[j] -= d
                    x = tuple(x)
                    for r in rules[k:]:
                        x = r.apply(x)
                    total[d] += 1
                    absorbed[d] += x == final
    return {d: (absorbed[d] / total[d] if total[d] else 0.0) for d in sizes}


def house_variant_absorption(rules: Sequence[Rule], s0: State) -> Dict[str, float]:
    """Edith M3: the share of house-rule slips that vanish. At each step where the house rule acts, the slip is leaving it OUT (the rule's result
    alone) or doing it TWICE (where the second go would move again); the rest is replayed. A rulebook without a house rule returns 0.0."""
    states = [s0]
    for r in rules:
        states.append(r.apply(states[-1]))
    final = states[-1]
    got = {"omit": [0, 0], "double": [0, 0]}
    for k, r in enumerate(rules):
        if r.house is None:
            return {"omit": 0.0, "double": 0.0}
        bare = r.bare(states[k])
        once = r.house.after(bare)
        for name, alt in (("omit", bare), ("double", r.house.after(once))):
            if alt == once:
                continue
            x = alt
            for q in rules[k + 1:]:
                x = q.apply(x)
            got[name][1] += 1
            got[name][0] += x == final
    return {n: (v[0] / v[1] if v[1] else 0.0) for n, v in got.items()}


PICK_KINDS = ("repeat_l2s", "fee_largest", "boost_smallest", "largest_to_smallest", "first_below", "avg_donors", "rank_move", "count_move",
              "repick2", "repeat_fixed", "sweep")


def _dup(x) -> bool:
    return len(set(x)) < len(x)


def _extremes_clear(x, depth: int = 1) -> bool:
    """No tie decides an order-dependent pick: the `depth` largest and the `depth` smallest balances are each distinct from one another AND from the next
    balance in (depth 1: one largest and one smallest line; depth 2: also the second-largest and second-smallest, as the rank rule needs). A tie
    elsewhere in the state does not matter to any pick, and with round numbers it is common."""
    v = sorted(x)
    if len(v) <= depth + 1:
        return len(set(v)) == len(v)
    top, bottom = v[::-1][:depth + 1], v[:depth + 1]
    return len(set(top)) == len(top) and len(set(bottom)) == len(bottom)


def unclear(rule: Rule, s: State) -> bool:
    """Edith's B3 and B4: True when, at this state, an order-dependent pick (largest, smallest, a rank) is tied, or a threshold or
    comparison is hit exactly. Such places are redrawn: the printed tie rule would decide them, and the neighbouring slip would not show."""
    a, k = rule.a, rule.kind
    if k in PICK_KINDS:
        depth = 2 if k == "rank_move" else 1
        if not _extremes_clear(s, depth):
            return True
        x = list(s)
        if k == "repick2":
            i, j = _largest(x), x.index(min(x))
            mv = min(a["A"], x[i])
            x[i] -= mv
            x[j] += mv
            if not _extremes_clear(x):
                return True
        if k == "repeat_fixed":
            for _ in range(a["n"]):
                i, j = _largest(x), x.index(min(x))
                mv = min(a["A"], x[i])
                x[i] -= mv
                x[j] += mv
                if not _extremes_clear(x):
                    return True
        if k == "repeat_l2s":
            for _ in range(a.get("n", 3)):
                i, j = _largest(x), x.index(min(x))
                mv = x[i] * a["p"] // 100
                x[i] -= mv
                x[j] += mv
                if not _extremes_clear(x):
                    return True
        if k == "avg_donors" and any(v == sum(s) // len(s) for v in s):
            return True
        if k == "sweep" and _sweep_trace(a, s)[2]:
            return True
    if k == "sweep" and a["A"] >= a["T"]:
        return True
    if k in ("top_up", "two_clause", "cap_move") and s[a["a"]] == a["t"]:
        return True
    if k == "three_way" and s[a["a"]] in (a["t1"], a["t2"]):
        return True
    if k in ("first_below", "count_move") and any(v == a["t"] for v in s):
        return True
    if k == "compare_move" and s[a["a"]] == 2 * s[a["b"]]:
        return True
    if rule.house is not None:
        b = rule.bare(s)
        if not _extremes_clear(b) or min(b) == rule.house.t:
            return True
    return False


# ---------------------------------------------------------------- rulebook + sequence

def _pick_kinds(rng: HashRNG, p: LParams) -> List[str]:
    """24 rule kinds in order: no kind more than max_per_kind times, no run of three of one kind, at most overwrite_max
    overwrite-type rules."""
    kinds = list(p.kinds)
    for _ in range(1000):
        seq: List[str] = []
        count: Dict[str, int] = {}
        ov = 0
        ok = True
        for _step in range(p.total_steps):
            for _try in range(50):
                k = kinds[rng.randbelow(len(kinds))]
                if count.get(k, 0) >= p.max_per_kind:
                    continue
                if k in OVERWRITE_KINDS and ov >= p.overwrite_max:
                    continue
                if len(seq) >= 2 and seq[-1] == k and seq[-2] == k:
                    continue
                break
            else:
                ok = False
                break
            seq.append(k)
            count[k] = count.get(k, 0) + 1
            ov += k in OVERWRITE_KINDS
        if ok:
            return seq
    raise ValueError("no rule-kind sequence found at these settings")


def label_pool(p: LParams) -> List[str]:
    """A..Z, then AA, AB, ... when the rulebook holds more than 26 rules (applied rules plus decoys)."""
    n = p.total_steps + p.decoys
    return [chr(ord("A") + i) for i in range(min(n, 26))] + [f"A{chr(ord('A') + i)}" for i in range(max(0, n - 26))]


def make_decoys(rng: HashRNG, rules: Sequence[Rule], labels: Sequence[str], p: LParams, names: Sequence[str]) -> List[Rule]:
    """`p.decoys` rules no sequence uses. Each is a near-duplicate of a used rule that differs in ONE detail (the rounding for
    the two percent-move kinds; otherwise one line of the rule, or its percentage)."""
    out: List[Rule] = []
    texts = {r.text(names) for r in rules}
    src = list(range(len(rules)))
    for d in range(p.decoys):
        for _ in range(200):
            r = rules[src.pop(rng.randbelow(len(src))) if src else rng.randbelow(len(rules))]
            a = dict(r.a)
            kind = r.kind
            if kind in ("move_pct_down", "move_pct_near"):
                kind = "move_pct_near" if kind == "move_pct_down" else "move_pct_down"
            else:
                line_keys = [k for k in ("src", "dst", "a", "b", "c") if k in a]
                if line_keys and rng.randbelow(3):
                    k = line_keys[rng.randbelow(len(line_keys))]
                    others = [x for x in range(p.lines) if x != a[k] and x not in [a[j] for j in line_keys]]
                    if not others:
                        continue
                    a[k] = others[rng.randbelow(len(others))]
                elif "A" in a:
                    a["A"] = max(50, a["A"] + (rng.randbelow(2) * 2 - 1) * 50 * (1 + rng.randbelow(3)))
                elif "p" in a:
                    a["p"] = max(1, min(97, a["p"] + (rng.randbelow(2) * 2 - 1) * (2 + rng.randbelow(6))))
                else:
                    continue
            cand = Rule(labels[d], kind, a)
            tx = cand.text(names)
            if tx in texts:
                continue
            texts.add(tx)
            out.append(cand)
            break
        else:
            raise ValueError("no decoy rule found")
    return out


ATTEMPT_BUDGET = 400000      # draws per rulebook; the accepted draw's number is stored in the puzzle, so the same seed always rebuilds the same rulebook (Edith X1). l17: about 1 acceptance in 28,500 draws at about 31 draws a second, so a seed takes about 16 min on average and at worst (400,000 draws) about 3.6 h; P(no rulebook) about e^-14


def _piece_start(st: HashRNG, rule: "Rule", reference: State, ref_acts: bool, tries: int) -> Optional[State]:
    """A start for a 24x1 piece: the reference state before the step, moved by up to +-25% per line, at which the rule (with the house rule) changes
    the state, so does the rule without the house rule (Edith M4), a look-again / repeat / sweep pick really changes, no pick is tied or on a threshold, and the house rule acts exactly when it acts in the
    chain (Edith m4). None if `tries` draws find none."""
    for _ in range(tries):
        s0 = _jitter(st, reference, 25)
        if (s0 != reference and rule.apply(s0) != s0 and rule.bare(s0) != s0 and picks_change(rule, s0) and not unclear(rule, s0)
                and house_acts(rule, s0) == ref_acts):
            return s0
    return None


def make_rulebook(rng: HashRNG, p: LParams, names: Sequence[str],
                  stats: Optional[Dict[str, int]] = None) -> Tuple[List[Rule], State, List[State], List[State], List[str], int, List[State]]:
    """(rules in the order they are applied, the reference start, the reference states before each step, probe starts, labels left over for decoys,
    the number of the accepted draw, the 24x1 piece starts). The labels are a random permutation of A..X, so the printed order of the rulebook does not
    give the order of use. The draw number is part of the puzzle's record: generation is deterministic and total up to ATTEMPT_BUDGET draws, and a
    rulebook is only accepted once every 24x1 piece has a start; the 24x1 shape uses exactly those starts (so both shapes always share the rulebook)."""
    labels = label_pool(p)

    def fail(why: str) -> None:
        if stats is not None:
            stats[why] = stats.get(why, 0) + 1
    for attempt in range(ATTEMPT_BUDGET):
        r = rng.child(f"attempt{attempt}")
        kinds = _pick_kinds(r.child("kinds"), p)
        start = _random_state(r.child("start"), p)
        draw = r.child("params")
        shuffled_all = r.child("labels").shuffled(labels)
        shuffled = shuffled_all[:p.total_steps]
        s = start
        rules: List[Rule] = []
        before: List[State] = []
        ok = True
        house = None
        if p.house:                                       # T and A are tuned per puzzle: accepted only if it fires on 5-8 of the 24 steps
            hr = r.child("house")
            mean = sum(start) // len(start)
            house = House(t=max(100, (mean * (45 + hr.randbelow(50)) // 100 // 100) * 100),
                          a=max(50, (mean * (4 + hr.randbelow(9)) // 100 // 50) * 50))
        fired = 0
        for i, k in enumerate(kinds):
            found = False
            for _ in range(60):
                args = _draw_rule(draw, k, s, p)
                if args is None:                                        # no candidate at this state: the attempt fails now (R3-2)
                    break
                rule = Rule(shuffled[i], k, args, house)
                t = rule.apply(s)
                if (t != s and rule.bare(s) != s and max(t) < 10 ** (p.digits + 1) and picks_change(rule, s)
                        and not unclear(rule, s)):                      # M4: the rule itself must do something, the house rule must not hide a no-op
                    found = True
                    break
            if not found:
                ok = False
                break
            fired += t != rule.bare(s)
            before.append(s)
            rules.append(rule)
            s = t
        if not ok:
            fail("no draw")
            continue
        if p.house and not p.house_fires[0] <= fired <= p.house_fires[1]:
            fail("house fires outside its window")
            continue
        if len({x.text(names) for x in rules}) != len(rules):
            fail("same text twice")
            continue
        states = trajectory(rules, start)
        cells = [v for st in states for v in st]
        if sum(1 for v in cells if v == 0) > 0.03 * len(cells):          # a line sitting at 0 makes later rules degenerate
            fail("zeros")
            continue
        pr = r.child("probes")
        probes = [start] + [_jitter(pr, start, 10) for _ in range(5)]
        if not all(every_step_changes(rules, q) for q in probes[:1]):
            fail("a step changes nothing")
            continue
        if find_ledger_shortcut(rules, probes) is not None:
            fail("skippable steps")
            continue
        if max(absorption_rate(rules, q) for q in probes) > ABSORPTION_CAP:
            fail("single-unit absorption")
            continue
        if STRICT_REFERENCE_CAPS:
            if max(transfer_absorption_by_size(rules, start).values()) > ABSORPTION_CAP:          # B1, M1: the slip that really happens, each size on its own
                fail("transfer absorption (a size)")
                continue
            if max(house_variant_absorption(rules, start).values()) > ABSORPTION_CAP:             # M3: the house rule left out or done twice
                fail("house-rule slip absorption")
                continue
        pc = r.child("piece-starts")
        pieces = []
        for i in range(p.total_steps):
            q = _piece_start(pc.child(str(i)), rules[i], before[i], house_acts(rules[i], before[i]), 2000)
            if q is None:
                break
            pieces.append(q)
        if len(pieces) < p.total_steps:
            fail("a 24x1 piece has no start")
            continue
        fail("ACCEPTED")
        return rules, start, before, probes, shuffled_all[p.total_steps:], attempt, pieces
    raise ValueError(f"no rulebook found in {ATTEMPT_BUDGET} draws at these settings")


# ---------------------------------------------------------------- puzzle

@dataclass
class LChain:
    start: List[int]
    names: List[str]                 # rule labels, in order
    states: List[List[int]]          # the balances after each rule

    @property
    def end(self) -> List[int]:
        return self.states[-1]


@dataclass
class LPuzzle:
    id: str
    seed: str
    width: int
    depth: int
    params: LParams
    version: str
    line_names: List[str]
    rulebook: List[Tuple[str, str, str]]     # (label, kind, printed text), by label
    chains: List[LChain]
    prompt: str
    answer: List[List[int]]
    absorption: float                         # the reference chain's measured absorption (L2): single-unit slips
    transfer_absorption: float = 0.0          # the same for transfer slips of 1, 10 and 100 units (B1)
    style: str = "d31"
    decoys: List[str] = field(default_factory=list)       # labels of printed rules that no sequence uses
    house: Optional[Dict[str, int]] = None                 # {"t": .., "a": ..} when the puzzle has a house rule
    attempt: int = 0                                        # the number of the accepted rulebook draw (generation is deterministic and total)
    transfer_by_size: Dict[str, float] = field(default_factory=dict)      # measured on the reference chain, per slip size (Edith M1)
    house_variants: Dict[str, float] = field(default_factory=dict)        # house rule left out / done twice, measured (Edith M3)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @property
    def answer_line(self) -> str:
        return "Answer: " + ", ".join(f"{i} = {fmt(a)}" for i, a in enumerate(self.answer, 1))


def fmt(v: Sequence[int]) -> str:
    return "[" + ", ".join(str(x) for x in v) + "]"


def intro(p: LParams, names: Sequence[str], example: Sequence[int], house: Optional[House] = None, single: bool = False) -> str:
    order = ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]
    meaning = ", ".join(f"{n} {v}" for n, v in list(zip(names, example))[:-1]) + f" and {names[-1]} {example[-1]}"
    return (f"Every value here lists the balances of {p.lines} budget lines, in whole units, in this order: {order}. "
            f"A value looks like {fmt(example)}, which means {meaning}. A balance never goes below 0. "
            f"{'The rule below says' if single else 'Each rule below says'} what happens to the balances. When a rule picks the line with the largest or the smallest "
            f"balance and two or more lines are tied, it picks the one that comes first in the order above."
            + (" Not every rule below is used: each sequence names the rules it applies." if p.decoys and not single else "")
            + (" " + house.text() if house is not None else ""))


def closing_house(width: int, depth: int, answer_only: bool = False) -> str:
    """The last paragraph for a puzzle with a house rule: every value written is the balances after the rule AND the house rule."""
    if answer_only:
        if width == 1:
            return ("Apply the rules of sequence 1 in the order listed, each followed by the house rule, each to the balances that the "
                    "rule before it and its house rule gave. Reply with one line, `Answer: 1 = v`, where v is the balances the sequence "
                    "ends at.")
        return (f"Each sequence is one rule applied to its start balances, followed by the house rule, and the sequences are separate. "
                f"Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, giving the balances each sequence ends at, in order.")
    if width == 1:
        return ("Apply the rules of sequence 1 in the order listed, each followed by the house rule, each to the balances that the rule "
                "before it and its house rule gave. Reply with the balances after each rule and its house rule, one per line, written "
                "`1.1 = v`, `1.2 = v`, and so on (the first number is the sequence, the second is the rule's place in it). Then end "
                "with one line, `Answer: 1 = v`, giving the balances the sequence ends at.")
    return (f"Each sequence is one rule applied to its start balances, followed by the house rule, and the sequences are separate. "
            f"Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, giving the balances each sequence ends at, in order.")


def render_prompt(rules_by_label: List[Rule], chains: List[LChain], p: LParams, names: Sequence[str],
                  example: Sequence[int], depth: int, style: str = "d31", house: Optional[House] = None) -> str:
    from .prompt_d31 import closing
    out = [intro(p, names, example, house), "", "Rules"]
    out += [f"{r.label}: {r.text(names)}" for r in rules_by_label]
    out += ["", "Sequences"]
    for i, c in enumerate(chains, 1):
        out.append(f"{i}. Start at {fmt(c.start)}. Apply {', '.join(c.names)}.")
    out.append("")
    if style not in ("d31", "d31-answer-only"):
        raise ValueError(f"unknown prompt style {style!r} for the ledger")
    if house is not None:
        out.append(closing_house(len(chains), depth, answer_only=(style == "d31-answer-only")))
    else:
        out.append(closing("ledger", len(chains), depth, answer_only=(style == "d31-answer-only")))
    return "\n".join(out)


def generate(seed: object, width: int, depth: int, params: LParams = SETTINGS["l1"], item_id: str = "",
             style: str = "d31") -> LPuzzle:
    params.validate()
    if width * depth != params.total_steps:
        raise ValueError(f"{width} x {depth} != {params.total_steps}")
    if any(params == SETTINGS[r] for r in RETIRED if r in SETTINGS):
        raise ValueError("this preset is retired (it cannot meet the absorption cap); use l11 or l14 to l17")
    root = HashRNG(seed)
    names = NAMES[:params.lines]
    key = (str(seed), repr(params))                                   # the two shapes of a base puzzle share the rulebook: build it once per process
    if key not in _RULEBOOKS:
        if len(_RULEBOOKS) > 64:
            _RULEBOOKS.clear()
        _RULEBOOKS[key] = make_rulebook(root.child("rulebook"), params, names)
    rules, start, before, probes, spare, attempt, pieces = _RULEBOOKS[key]
    decoys = make_decoys(root.child("decoys"), rules, spare, params, names)
    by_label = sorted(rules + decoys, key=lambda r: (len(r.label), r.label))
    house = rules[0].house
    refstates = trajectory(rules, start)
    st = root.child(f"starts/{width}x{depth}")
    chains: List[LChain] = []
    for c in range(width):
        lo = c * depth
        seg = rules[lo:lo + depth]
        if c == 0 and depth > 1:
            s0 = start                                     # the reference chain: every rule fires here (L1)
        elif depth == 1:
            s0 = pieces[c]                                 # 24x1: the starts the rulebook check found (X1: so the 24x1 shape always exists)
        else:                                              # a middle wiring (self-test only): a perturbed copy of the reference state before the first rule
            s0 = None
            for _ in range(20):
                s0 = _piece_start(st.child(f"try{_}"), seg[0], before[lo], house_acts(seg[0], before[lo]), 2000)
                if s0 is not None and _segment_clear(seg, s0):
                    break
                s0 = None
            if s0 is None:
                raise ValueError("no start balances found at which the rule changes the state")
        states = trajectory(seg, s0)
        chains.append(LChain(list(s0), [r.label for r in seg], [list(x) for x in states]))
    example = list(_random_state(root.child("example"), params))
    answer = [list(ch.states[-1]) for ch in chains]
    return LPuzzle(
        id=item_id or f"{seed}-{width}x{depth}", seed=str(seed), width=width, depth=depth, params=params, version=LV_VERSION,
        line_names=list(names), rulebook=[(r.label, r.kind, r.text(names)) for r in by_label], chains=chains,
        prompt=render_prompt(by_label, chains, params, names, example, depth, style, house), answer=answer,
        absorption=round(absorption_rate(rules, start), 4), transfer_absorption=round(transfer_absorption(rules, start), 4), style=style, decoys=[r.label for r in decoys],
        house=None if house is None else {"t": house.t, "a": house.a}, attempt=attempt,
        transfer_by_size={str(d): round(v, 4) for d, v in transfer_absorption_by_size(rules, start).items()},
        house_variants={k: round(v, 4) for k, v in house_variant_absorption(rules, start).items()})


# ---------------------------------------------------------------- reference reply and grading (same format as the code family)

def reference_reply(p: LPuzzle) -> str:
    lines = []
    if p.depth > 1:
        for s_i, ch in enumerate(p.chains, 1):
            lines += [f"{s_i}.{k} = {fmt(st)}" for k, st in enumerate(ch.states, 1)]
    return "\n".join(lines + [p.answer_line])


def grade_d31(reply: str, p: LPuzzle) -> Dict:
    from .prompt_d31 import first_wrong_step, numbering_problems, parse_steps, score_answer
    res = score_answer(reply, [tuple(a) for a in p.answer])
    res["numbering_problems"] = numbering_problems(reply, p.width, p.depth)
    res["first_wrong_step"] = [first_wrong_step(reply, [tuple(s) for s in ch.states], i, p.width)
                               for i, ch in enumerate(p.chains, 1)] if p.depth > 1 else None
    res["steps_shown"] = len(parse_steps(reply))
    kind_of = {lab: kind for lab, kind, _ in p.rulebook}
    if p.depth > 1 and res["first_wrong_step"]:                       # the rule kind where each chain first went wrong
        res["first_wrong_kind"] = [None if s is None else kind_of[p.chains[i].names[s - 1]]
                                   for i, s in enumerate(res["first_wrong_step"])]
    return res


def step_call(p: LPuzzle, sequence: int, k: int) -> Tuple[str, List[int]]:
    """The E3 prompt for step k (1-based) of a sequence, and the true new balances."""
    from .prompt_d31 import step_call_prompt
    ch = p.chains[sequence - 1]
    rules = {lab: txt for lab, _, txt in p.rulebook}
    before = ch.start if k == 1 else ch.states[k - 2]
    house = House(**p.house) if p.house else None
    intro_text = intro(p.params, p.line_names, ch.start, house, single=True)
    return (step_call_prompt("ledger", p.params.lines, rules[ch.names[k - 1]], fmt(before), intro_text, house=house is not None),
            ch.states[k - 1])
