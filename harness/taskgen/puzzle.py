"""Prototype generator for Study 1's puzzles: 24 exact sub-steps, wired as w chains of depth d.

PROTOTYPE. Nothing about the task family is final; see README.md.

How a puzzle is built from one seed:
1. A rulebook of rules printed in the prompt, in four kinds:
   - affine:  multiply by a, add b, keep the last n digits         (modular arithmetic, mod 10^n)
   - table:   replace each digit using a printed 10-entry table     (lookup, single digits)
   - pair:    replace each aligned pair of digits using a printed 100-entry table  (lookup, digit pairs)
   - shuffle: reorder the digits by a printed position order        (permutation)
2. A sequence of `total_steps` rule applications, each rule used equally often, in shuffled order.
3. A wiring (w, d) with w * d = total_steps: the sequence is cut into w consecutive pieces of d steps.
   Each piece becomes one chain with its own given start value.

The rulebook and the rule sequence depend only on the seed and the difficulty settings, so the same
seed at 24x1 and at 1x24 is the same work wired differently. Start values come from a separate stream
per wiring.

Difficulty is a set of dials in `Params` (digits per value, multiplier and addend size, how many rules
of each kind, whether pair tables are used), all at the same 24 steps. `PRESETS` names a ladder d0..d4, plus the D-25 candidates d4s and d4p.

Every rule is a bijection on n-digit strings (a is coprime to 10; tables, pair tables and shuffles are
permutations), so one wrong step always makes that chain's final value wrong. The sequence is checked
for shortcuts (see `find_shortcut`); if a setting cannot satisfy the guards, generation raises.
"""

from __future__ import annotations

import json
import string
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .rng import HashRNG

GENERATOR_VERSION = "taskgen-proto-0.3"

STRUCTURE_LEVELS: Tuple[Tuple[int, int], ...] = ((24, 1), (6, 4), (2, 12), (1, 24))

ORDINALS = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]

KINDS = ("affine", "table", "pair", "shuffle")


@dataclass(frozen=True)
class Params:
    """The difficulty dials. The step count stays total_steps (24) at every setting."""
    total_steps: int = 24
    n_digits: int = 4          # digits per value (2..9)
    n_affine: int = 4          # how many rules of each kind are printed
    n_table: int = 4
    n_pair: int = 0            # pair tables need an even n_digits
    n_shuffle: int = 4
    mult_min: int = 3          # multiplier range (mult_max squared must be below 10^n_digits)
    mult_max: int = 99
    add_min: int = 10          # addend range (must be below 10^n_digits)
    add_max: int = 999

    def n_rules(self) -> int:
        return self.n_affine + self.n_table + self.n_pair + self.n_shuffle

    def validate(self) -> None:
        if not 2 <= self.n_digits <= 9:
            raise ValueError("n_digits must be 2..9 (ordinal names go up to 9th)")
        if self.n_pair and self.n_digits % 2:
            raise ValueError("pair tables need an even number of digits")
        if min(self.n_affine, self.n_table, self.n_pair, self.n_shuffle) < 0:
            raise ValueError("rule counts cannot be negative")
        if not 0 < self.n_rules() <= min(self.total_steps, len(string.ascii_uppercase)):
            raise ValueError(f"{self.n_rules()} rules: need 1..min(total_steps, 26) so every printed rule is used")
        if self.n_affine and not (3 <= self.mult_min <= self.mult_max < 10**self.n_digits):
            raise ValueError("multiplier range must satisfy 3 <= min <= max < 10^n_digits")
        if self.n_affine and self.mult_max**2 >= 10**self.n_digits:
            # Two arithmetic steps in a row equal one rule: multiply by a1*a2, add a constant. If a1*a2
            # wraps past 10^n the combined multiplier can be tiny (or 1), which only chained levels can
            # exploit, and the shortcut guard cannot see it because nothing is skipped.
            raise ValueError("mult_max squared must stay below 10^n_digits so two arithmetic steps "
                             "cannot combine into a much easier one")
        if self.n_affine and not (1 <= self.add_min <= self.add_max < 10**self.n_digits):
            raise ValueError("addend range must satisfy 1 <= min <= max < 10^n_digits")


# The difficulty ladder. All presets are 24 steps. d0 is the prototype's original setting.
PRESETS: Dict[str, Params] = {
    "d0": Params(),
    "d1": Params(n_digits=6, mult_min=101, mult_max=999, add_min=1000, add_max=99999),
    "d2": Params(n_digits=6, n_pair=4, mult_min=101, mult_max=999, add_min=10000, add_max=999999),
    "d3": Params(n_digits=8, n_affine=5, n_table=5, n_pair=5, n_shuffle=5,
                 mult_min=1001, mult_max=9999, add_min=1000000, add_max=99999999),
    "d4": Params(n_digits=8, n_affine=6, n_table=6, n_pair=6, n_shuffle=6,
                 mult_min=1001, mult_max=9999, add_min=1000000, add_max=99999999),
    # Candidates under D-25 (smaller maths steps; difficulty from lookups and shuffles). Untried on any model.
    # d4s: d4's mix (6 of each kind, 24 rules, each used once) with 3-digit multipliers and 5-6 digit addends.
    "d4s": Params(n_digits=8, n_affine=6, n_table=6, n_pair=6, n_shuffle=6,
                  mult_min=101, mult_max=999, add_min=10000, add_max=999999),
    # d4p: the same small maths numbers, fewer maths steps (4), more pair tables and shuffles (8 each).
    "d4p": Params(n_digits=8, n_affine=4, n_table=4, n_pair=8, n_shuffle=8,
                  mult_min=101, mult_max=999, add_min=10000, add_max=999999),
}


@dataclass
class Rule:
    label: str
    kind: str  # one of KINDS
    mult: int = 0
    add: int = 0
    table: List[int] = field(default_factory=list)  # table[d] = what digit d becomes
    pairs: List[int] = field(default_factory=list)  # pairs[k] = what the pair of digits k (00..99) becomes
    order: List[int] = field(default_factory=list)  # new value = old digits at these 0-based positions

    def run(self, value: str) -> str:
        """The rule applied to a value (no working shown)."""
        n = len(value)
        if self.kind == "affine":
            return str((int(value) * self.mult + self.add) % 10**n).zfill(n)
        if self.kind == "table":
            return "".join(str(self.table[int(c)]) for c in value)
        if self.kind == "pair":
            return "".join("%02d" % self.pairs[int(value[i:i + 2])] for i in range(0, n, 2))
        if self.kind == "shuffle":
            return "".join(value[i] for i in self.order)
        raise ValueError(self.kind)

    def apply(self, value: str) -> Tuple[str, str]:
        """Return (new value, one-line worked step)."""
        n = len(value)
        out = self.run(value)
        if self.kind == "affine":
            x = int(value)
            prod = x * self.mult
            total = prod + self.add
            return out, f"{x} × {self.mult} = {prod}; + {self.add} = {total}; last {n} digits → {out}"
        if self.kind == "table":
            pairs = ", ".join(f"{c}→{o}" for c, o in zip(value, out))
            return out, f"{pairs} → {out}"
        if self.kind == "pair":
            pairs = ", ".join(f"{value[i:i + 2]}→{out[i:i + 2]}" for i in range(0, n, 2))
            return out, f"{pairs} → {out}"
        picks = ", ".join(ORDINALS[i] for i in self.order)
        return out, f"{value} → take {picks} digits → {out}"

    def describe(self, n_digits: int) -> str:
        if self.kind == "affine":
            return f"{self.label}: multiply by {self.mult}, add {self.add}, then keep only the last {n_digits} digits."
        if self.kind == "table":
            pairs = ", ".join(f"{d}→{t}" for d, t in enumerate(self.table))
            return f"{self.label}: replace each digit using this table: {pairs}."
        if self.kind == "pair":
            pairs = ", ".join(f"{k:02d}→{t:02d}" for k, t in enumerate(self.pairs))
            return (f"{self.label}: cut the value into pairs of digits, starting from the left "
                    f"({n_digits // 2} pairs), and replace each pair using this table: {pairs}.")
        picks = ", ".join(ORDINALS[i] for i in self.order)
        return f"{self.label}: reorder the digits; the new value is the old {picks} digits, in that order."


@dataclass
class Step:
    rule: str
    kind: str
    input: str
    output: str
    work: str


@dataclass
class Chain:
    start: str
    rules: List[str]
    steps: List[Step]

    @property
    def end(self) -> str:
        return self.steps[-1].output if self.steps else self.start


@dataclass
class Puzzle:
    id: str
    seed: str
    width: int
    depth: int
    params: Params
    generator: str
    rulebook: List[Rule]
    chains: List[Chain]
    prompt: str
    answer: List[str]
    answer_line: str

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------- rulebook and sequence

def _derangement(rng: HashRNG, n: int) -> List[int]:
    """A permutation of range(n) with no fixed points, so every digit or position changes."""
    while True:
        p = rng.shuffled(range(n))
        if all(p[i] != i for i in range(n)):
            return p


def make_rulebook(rng: HashRNG, p: Params) -> List[Rule]:
    """Draw the rules. Each kind has its own random stream, so changing one count leaves the others alone.

    Rules of one kind are distinct and none is the inverse of another. Shuffles that undo themselves
    (double swaps) make cancelling stretches likelier, so they are used only when the inverse-pair rule
    leaves nothing else. Raises if the settings leave too few options.
    """
    p.validate()
    labels = iter(string.ascii_uppercase)
    rules: List[Rule] = []

    r = rng.child("affine")
    seen_mult: set = set()
    seen_ab: set = set()
    for _ in range(p.n_affine):
        for _try in range(10000):
            a = r.randint(p.mult_min, p.mult_max)
            b = r.randint(p.add_min, p.add_max)
            if a % 2 == 0 or a % 5 == 0 or a in seen_mult:  # a must be coprime to 10 to be reversible
                continue
            if any((a * a2) % 10**p.n_digits == 1 and (a2 * b + b2) % 10**p.n_digits == 0 for a2, b2 in seen_ab):
                continue  # would undo an earlier rule
            break
        else:
            raise ValueError("cannot draw enough distinct multipliers in this range")
        seen_mult.add(a)
        seen_ab.add((a, b))
        rules.append(Rule(next(labels), "affine", mult=a, add=b))

    r = rng.child("table")
    seen: set = set()
    for _ in range(p.n_table):
        t = _draw_distinct(lambda: _derangement(r, 10), seen, "table")
        seen.add(tuple(t))
        rules.append(Rule(next(labels), "table", table=t))

    r = rng.child("pair")
    seen = set()
    for _ in range(p.n_pair):
        t = _draw_distinct(lambda: _derangement(r, 100), seen, "pair table")
        seen.add(tuple(t))
        rules.append(Rule(next(labels), "pair", pairs=t))

    r = rng.child("shuffle")
    seen = set()
    for _ in range(p.n_shuffle):
        try:
            o = _draw_distinct(lambda: _derangement(r, p.n_digits), seen, "shuffle",
                               reject=lambda o: _inverse(o) == tuple(o), tries=200)
        except ValueError:
            o = _draw_distinct(lambda: _derangement(r, p.n_digits), seen, "shuffle")
        seen.add(tuple(o))
        rules.append(Rule(next(labels), "shuffle", order=o))
    return rules


def _draw_distinct(draw, seen: set, what: str, reject=lambda x: False, tries: int = 2000) -> List[int]:
    """Draw until the result is new, not the inverse of a seen one, and not rejected. Raise if it can't."""
    for _ in range(tries):
        x = draw()
        if not ({tuple(x), _inverse(x)} & seen) and not reject(x):
            return x
    raise ValueError(f"cannot draw another {what} rule that is distinct from the others and not their "
                     f"inverse (too few options at these settings)")


def _inverse(perm: Sequence[int]) -> Tuple[int, ...]:
    inv = [0] * len(perm)
    for i, j in enumerate(perm):
        inv[j] = i
    return tuple(inv)


# ---------------------------------------------------------------- shortcut guard

def probe_values(n_digits: int, count: int = 6) -> List[str]:
    """Fixed, deterministic test values for the shortcut guard (never used as puzzle start values)."""
    rng = HashRNG(f"probe/{n_digits}")
    return [str(rng.randbelow(10**n_digits)).zfill(n_digits) for _ in range(count)]


def _final(rules: Sequence[Rule], value: str, skip: frozenset = frozenset()) -> str:
    for i, r in enumerate(rules):
        if i not in skip:
            value = r.run(value)
    return value


def find_shortcut(rules: Sequence[Rule], probes: Sequence[str],
                  kinds: Sequence[str] = KINDS) -> Optional[Tuple[int, ...]]:
    """Look for steps that can be left out without changing the final value; return their positions.

    A model could skip such steps, but only where the wiring chains them together, so a sequence that
    has them would make the sequential levels easier than the parallel ones. Tested by simulation, so it
    covers whatever commutes with what (a table and a shuffle commute; so do a pair table and a shuffle
    that moves whole pairs) without relying on hand-made rules. Looks for:
    - a stretch of 2 or more consecutive steps whose net effect is "no change"
    - any 2 steps, or any 3 steps, that can be left out of the sequence leaving the result unchanged
    - within any stretch, all the steps of one kind (two or more) that can be left out together; this is
      how "the shuffles in this run cancel, because tables commute with shuffles" shows up
    `rules` can be anything with `.run(value)` and `.kind` (the code-tracing sketch passes functions over
    lists); `kinds` lists the kinds to try in the same-kind test. Candidates are found on the first probe value and confirmed on all the others. Not covered: other
    sets of 4 or more steps that are not consecutive and not all of one kind. Rules that merely compose into one simpler rule are not
    flagged (composing costs as much work as applying them).
    """
    m = len(rules)
    states = [probes[0]]
    for r in rules:
        states.append(r.run(states[-1]))
    cands: List[Tuple[int, ...]] = []
    for a in range(m):
        for b in range(a + 1, m):
            if states[b + 1] == states[a]:
                cands.append(tuple(range(a, b + 1)))
    for a in range(m):
        w = states[a]  # states[a] with steps a+1..b-1 applied
        for b in range(a + 1, m):
            if w == states[b + 1]:
                cands.append((a, b))
            t = w
            for c in range(b + 1, m):
                if t == states[c + 1]:
                    cands.append((a, b, c))
                t = rules[c].run(t)
            w = rules[b].run(w)
    for a in range(m):
        for b in range(a + 1, m):
            for kind in kinds:
                idx = [i for i in range(a, b + 1) if rules[i].kind == kind]
                if len(idx) < 2:
                    continue
                v = states[a]
                for i in range(a, b + 1):
                    if rules[i].kind != kind:
                        v = rules[i].run(v)
                if v == states[b + 1]:
                    cands.append(tuple(idx))
    for cand in cands:
        skip = frozenset(cand)
        if all(_final(rules, v, skip) == _final(rules, v) for v in probes[1:]):
            return cand
    return None


def make_sequence(rng: HashRNG, rules: List[Rule], total_steps: int, n_digits: int,
                  tries: int = 5000) -> List[str]:
    """Use the rules about equally often, in shuffled order, with two guards.

    Every rule is used total_steps // n_rules times. The remaining uses are given out one at a time
    across the kinds in turn, so that (when the extras divide evenly) every puzzle at one setting has
    the same number of steps of each kind. Otherwise the mix would vary from item to item and add noise
    to the difficulty. Guards:
    1. No rule appears twice in a row.
    2. No steps that can be skipped (see `find_shortcut`).
    Both shortcuts exist only in the chained wiring, so they would make the work unequal across levels.
    Raises if no sequence is found. The sequence is global: each chain is a slice of it, so the guards
    hold at every structure level.
    """
    by_label = {r.label: r for r in rules}
    probes = probe_values(n_digits)
    uses = {r.label: total_steps // len(rules) for r in rules}
    extra = total_steps % len(rules)
    queue = {k: rng.shuffled([r.label for r in rules if r.kind == k]) for k in KINDS}
    kinds = rng.shuffled([k for k in KINDS if queue[k]])
    while extra:
        for k in kinds:
            if extra and queue[k]:
                uses[queue[k].pop()] += 1
                extra -= 1
    seq = [lab for lab in sorted(uses) for _ in range(uses[lab])]
    for _ in range(tries):
        out = rng.shuffled(seq)
        if all(a != b for a, b in zip(out, out[1:])) and find_shortcut([by_label[l] for l in out], probes) is None:
            return out
    raise ValueError("no rule sequence without shortcuts found; the rulebook is too small or too similar")


# ---------------------------------------------------------------- rendering

def render_prompt(rulebook: List[Rule], chains: List[Chain], n_digits: int, style: str = "legacy",
                  depth: int = 0) -> str:
    example = "0472" if n_digits == 4 else "0" + "4729183"[: n_digits - 1]
    intro = (f"Every value here is a string of exactly {n_digits} digits, such as {example}. "
             f"Leading zeros count. When a rule does arithmetic, read the value as an ordinary number "
             f"({example} is {int(example)}) and write the result back with {n_digits} digits.")
    if style == "d31-variant":                 # D-42 (a): same meaning, other words (see prompt_d31.py)
        from .prompt_d31 import variant_intro
        intro = variant_intro(n_digits, example)
    lines = [
        intro,
        "",
        "Rules",
    ]
    lines += [r.describe(n_digits) for r in rulebook]
    lines += ["", "Sequences"]
    for i, ch in enumerate(chains, 1):
        lines.append(f"{i}. Start at {ch.start}. Apply {', '.join(ch.rules)}.")
    lines.append("")
    if style == "d31-variant":
        from .prompt_d31 import variant_closing
        lines.append(variant_closing(len(chains), depth))
        return "\n".join(lines)
    if style in ("d31", "d31-answer-only"):
        # Draft wording for ruling D-31 (spec item 4); see prompt_d31.py.
        from .prompt_d31 import closing
        lines.append(closing("digits", len(chains), depth, answer_only=(style == "d31-answer-only")))
        return "\n".join(lines)
    if style != "legacy":
        raise ValueError(f"unknown prompt style {style!r}")
    if len(chains) == 1:
        lines.append("Apply each sequence's rules in the order listed. "
                     "End your reply with one line of the form `Final: v`, where v is the value the sequence ends at.")
    else:
        lines.append("Apply each sequence's rules in the order listed. Each sequence is separate. "
                     f"End your reply with one line of the form `Final: v1, v2, ..., v{len(chains)}`, "
                     "giving the value each sequence ends at, in sequence order.")
    return "\n".join(lines)


def render_solution(p: Puzzle) -> str:
    """The full worked solution, one line per sub-step."""
    out = []
    for i, ch in enumerate(p.chains, 1):
        out.append(f"Sequence {i} (start {ch.start}):")
        for s in ch.steps:
            out.append(f"  {s.rule} ({s.kind}): {s.input} → {s.output}    [{s.work}]")
        out.append(f"  ends at {ch.end}")
    out.append(p.answer_line)
    return "\n".join(out)


# ---------------------------------------------------------------- the generator

def generate(seed: object, width: int, depth: int, params: Params = Params(), item_id: str = "",
             style: str = "legacy") -> Puzzle:
    if width * depth != params.total_steps:
        raise ValueError(f"{width} x {depth} != {params.total_steps}")
    root = HashRNG(seed)
    rulebook = make_rulebook(root.child("rulebook"), params)
    by_label = {r.label: r for r in rulebook}
    sequence = make_sequence(root.child("sequence"), rulebook, params.total_steps, params.n_digits)

    start_rng = root.child(f"starts/{width}x{depth}")
    starts: List[str] = []
    while len(starts) < width:
        v = str(start_rng.randbelow(10**params.n_digits)).zfill(params.n_digits)
        if v not in starts:
            starts.append(v)

    chains: List[Chain] = []
    for c in range(width):
        labels = sequence[c * depth:(c + 1) * depth]
        value, steps = starts[c], []
        for lab in labels:
            new, work = by_label[lab].apply(value)
            steps.append(Step(lab, by_label[lab].kind, value, new, work))
            value = new
        chains.append(Chain(starts[c], labels, steps))

    answer = [ch.end for ch in chains]
    return Puzzle(
        id=item_id or f"{seed}-{width}x{depth}",
        seed=str(seed),
        width=width,
        depth=depth,
        params=params,
        generator=GENERATOR_VERSION,
        rulebook=rulebook,
        chains=chains,
        prompt=render_prompt(rulebook, chains, params.n_digits, style, depth),
        answer=answer,
        answer_line=("Final: " + ", ".join(answer)) if style == "legacy"
        else "Answer: " + ", ".join(f"{i} = {a}" for i, a in enumerate(answer, 1)),
    )
