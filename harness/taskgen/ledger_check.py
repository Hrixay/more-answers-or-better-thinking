"""Self-test for the ledger family (Edith's L1-L3), written separately from the generator.

    python3 -m harness.taskgen.ledger_check [seeds_per_setting]

The independent re-solver reads the PRINTED prompt only: the line names and their order, every rule (by its sentence), every
sequence. It applies the rules with its own code (not ledger.py's) and must reproduce every stored state. On top of that:
- every step changes the state, on the chain and on each 24x1 piece (L1);
- a brute-force search over the printed rules finds no stretch of two or more steps and no 1, 2 or 3 steps that can be left out,
  on the stored start and on perturbed starts (L1);
- the measured absorption of the reference chain is at most ABSORPTION_CAP, recomputed here (L2);
- no balance is ever negative; no tie is left to chance; every rounding is named in the sentence (L3);
- the neutral-word scan (prompt_d31.BANNED); determinism; the same 24 rules in the same order at every wiring; the 24 pieces do
  not start from the chain's own states; the grader accepts the reference reply and rejects a one-unit slip.
"""

from __future__ import annotations

import itertools
import re
import sys
from typing import Dict, List, Sequence, Tuple

from .ledger import ABSORPTION_CAP, RETIRED, SETTINGS, generate, grade_d31, reference_reply
from .prompt_d31 import BANNED
from .rng import HashRNG, derive_seed


def _int(x: str) -> int:
    return int(x)


# One regex per sentence template (ledger.KINDS). Each returns a function of (state, names) -> state, written here independently.
def parse_rule(sentence: str, names: Sequence[str]):
    ix = {n: i for i, n in enumerate(names)}
    N = "(" + "|".join(names) + ")"
    m = re.fullmatch(rf"Move (\d+)% of {N} to {N}, rounding the amount down to a whole unit\.", sentence)
    if m:
        p, s_, d_ = int(m.group(1)), ix[m.group(2)], ix[m.group(3)]

        def f(s):
            s = list(s); amt = (s[s_] * p) // 100; s[s_] -= amt; s[d_] += amt; return s
        return f
    m = re.fullmatch(rf"Move (\d+)% of {N} to {N}, rounding the amount to the nearest whole unit \(a half rounds up\)\.", sentence)
    if m:
        p, s_, d_ = int(m.group(1)), ix[m.group(2)], ix[m.group(3)]

        def f(s):
            s = list(s); amt = (s[s_] * p * 2 + 100) // 200; s[s_] -= amt; s[d_] += amt; return s
        return f
    m = re.fullmatch(rf"If {N} is below (\d+), move units from {N} to {N} until {N} reaches (\d+), or move all of {N} if it holds fewer\.", sentence)
    if m:
        a, t, b = ix[m.group(1)], int(m.group(2)), ix[m.group(3)]
        assert ix[m.group(4)] == a and ix[m.group(5)] == a and int(m.group(6)) == t and ix[m.group(7)] == b

        def f(s):
            s = list(s)
            if s[a] < t:
                need = t - s[a]
                mv = need if s[b] >= need else s[b]
                s[a] += mv; s[b] -= mv
            return s
        return f
    m = re.fullmatch(rf"If {N} is above (\d+), move (\d+)% of {N} to {N}, rounding the amount down to a whole unit; otherwise add (\d+) units to {N}\.", sentence)
    if m:
        a, t, p, b, y = ix[m.group(1)], int(m.group(2)), int(m.group(3)), ix[m.group(5)], int(m.group(6))
        assert ix[m.group(4)] == a and ix[m.group(7)] == a

        def f(s):
            s = list(s)
            if s[a] > t:
                mv = (s[a] * p) // 100; s[a] -= mv; s[b] += mv
            else:
                s[a] += y
            return s
        return f
    m = re.fullmatch(r"Remove (\d+) units from the line with the largest balance, or all of it if it holds fewer\.", sentence)
    if m:
        fee = int(m.group(1))

        def f(s):
            s = list(s)
            big = max(s)
            i = next(k for k, v in enumerate(s) if v == big)          # a tie goes to the line listed first
            s[i] -= fee if s[i] >= fee else s[i]
            return s
        return f
    m = re.fullmatch(rf"Increase {N} by (\d+)%, rounding the increase to the nearest whole unit \(a half rounds up\)\.", sentence)
    if m:
        a, p = ix[m.group(1)], int(m.group(2))

        def f(s):
            s = list(s); s[a] += (s[a] * p * 2 + 100) // 200; return s
        return f
    m = re.fullmatch(rf"Share {N} equally between {N} and {N}: each of them receives half of {N} rounded down, and any unit left over stays in {N}\.", sentence)
    if m:
        a, b, c = ix[m.group(1)], ix[m.group(2)], ix[m.group(3)]
        assert ix[m.group(4)] == a and ix[m.group(5)] == a

        def f(s):
            s = list(s); half = s[a] // 2; s[b] += half; s[c] += half; s[a] -= 2 * half; return s
        return f
    m = re.fullmatch(rf"Move (\d+) units from {N} to {N}, or all of {N} if it holds fewer\.", sentence)
    if m:
        k, a, b = int(m.group(1)), ix[m.group(2)], ix[m.group(3)]
        assert ix[m.group(4)] == a

        def f(s):
            s = list(s); mv = k if s[a] >= k else s[a]; s[a] -= mv; s[b] += mv; return s
        return f
    m = re.fullmatch(rf"Remove (\d+)% of {N}, rounding the amount down to a whole unit\.", sentence)
    if m:
        p, a = int(m.group(1)), ix[m.group(2)]

        def f(s):
            s = list(s); s[a] -= (s[a] * p) // 100; return s
        return f
    m = re.fullmatch(r"Add (\d+) units to the line with the smallest balance\.", sentence)
    if m:
        y = int(m.group(1))

        def f(s):
            s = list(s)
            small = min(s)
            i = next(k for k, v in enumerate(s) if v == small)
            s[i] += y
            return s
        return f
    m = re.fullmatch(rf"If {N} is above (\d+), move everything above (\d+) from {N} to {N}\.", sentence)
    if m:
        a, t, b = ix[m.group(1)], int(m.group(2)), ix[m.group(5)]
        assert int(m.group(3)) == t and ix[m.group(4)] == a

        def f(s):
            s = list(s)
            if s[a] > t:
                ex = s[a] - t; s[a] = t; s[b] += ex
            return s
        return f
    m = re.fullmatch(rf"Make {N} and {N} as equal as possible: together they keep their total, {N} gets half of it rounded down, and {N} gets the rest\.", sentence)
    if m:
        a, b = ix[m.group(1)], ix[m.group(2)]
        assert ix[m.group(3)] == b and ix[m.group(4)] == a

        def f(s):
            s = list(s); tot = s[a] + s[b]; s[b] = tot // 2; s[a] = tot - tot // 2; return s
        return f
    m = re.fullmatch(r"Move (\d+)% of the line with the largest balance to the line with the smallest balance, rounding the amount down to a whole unit\.", sentence)
    if m:
        p = int(m.group(1))

        def f(s):
            s = list(s)
            big, small = max(s), min(s)
            i = next(k for k, v in enumerate(s) if v == big)
            j = next(k for k, v in enumerate(s) if v == small)
            if i != j:
                mv = (s[i] * p) // 100; s[i] -= mv; s[j] += mv
            return s
        return f
    m = re.fullmatch(r"Add (\d+) units to the first line, in the order above, whose balance is below (\d+); if no line is below (\d+), add (\d+) units to the line with the smallest balance\.", sentence)
    if m:
        y, t = int(m.group(1)), int(m.group(2))
        assert int(m.group(3)) == t and int(m.group(4)) == y

        def f(s):
            s = list(s)
            for k, v in enumerate(s):
                if v < t:
                    s[k] += y
                    return s
            small = min(s)
            s[next(k for k, v in enumerate(s) if v == small)] += y
            return s
        return f
    m = re.fullmatch(rf"Move (\d+)% of the combined balance of {N} and {N} from {N} to {N}, rounding the amount down to a whole unit, or move all of {N} if it holds fewer\.", sentence)
    if m:
        p, s_, o_, s2, d_, s3 = int(m.group(1)), ix[m.group(2)], ix[m.group(3)], ix[m.group(4)], ix[m.group(5)], ix[m.group(6)]
        assert s2 == s_ and s3 == s_

        def f(s):
            s = list(s)
            amt = ((s[s_] + s[o_]) * p) // 100
            amt = amt if amt <= s[s_] else s[s_]
            s[s_] -= amt; s[d_] += amt
            return s
        return f
    m = re.fullmatch(rf"If {N} is more than twice {N}, move (\d+)% of {N} to {N}; otherwise move (\d+)% of {N} to {N}\. Each amount is rounded down to a whole unit\.", sentence)
    if m:
        a, b, p, a2, b2, p2, b3, c = ix[m.group(1)], ix[m.group(2)], int(m.group(3)), ix[m.group(4)], ix[m.group(5)], int(m.group(6)), ix[m.group(7)], ix[m.group(8)]
        assert a2 == a and b2 == b and p2 == p and b3 == b

        def f(s):
            s = list(s)
            if s[a] > 2 * s[b]:
                mv = (s[a] * p) // 100; s[a] -= mv; s[b] += mv
            else:
                mv = (s[b] * p) // 100; s[b] -= mv; s[c] += mv
            return s
        return f
    m = re.fullmatch(rf"Take (\d+)% of the difference between {N} and {N}, rounded down to a whole unit, from the larger of the two \(from {N} if they are equal\) and add it to {N}\.", sentence)
    if m:
        p, a, b, a2, c = int(m.group(1)), ix[m.group(2)], ix[m.group(3)], ix[m.group(4)], ix[m.group(5)]
        assert a2 == a

        def f(s):
            s = list(s)
            if s[a] >= s[b]:
                d = ((s[a] - s[b]) * p) // 100; s[a] -= d
            else:
                d = ((s[b] - s[a]) * p) // 100; s[b] -= d
            s[c] += d
            return s
        return f
    m = re.fullmatch(rf"If {N} is below (\d+), add (\d+) units to {N}; if {N} is above (\d+), move (\d+)% of {N} to {N}, rounding the amount down to a whole unit; otherwise move (\d+) units from {N} to {N}, or all of {N} if it holds fewer\.", sentence)
    if m:
        a, t1, y, a2, a3, t2, p, a4, b, q, b2, a5, b3 = (ix[m.group(1)], int(m.group(2)), int(m.group(3)), ix[m.group(4)], ix[m.group(5)], int(m.group(6)),
                                                          int(m.group(7)), ix[m.group(8)], ix[m.group(9)], int(m.group(10)), ix[m.group(11)], ix[m.group(12)], ix[m.group(13)])
        assert a2 == a and a3 == a and a4 == a and a5 == a and b2 == b and b3 == b

        def f(s):
            s = list(s)
            if s[a] < t1:
                s[a] += y
            elif s[a] > t2:
                mv = (s[a] * p) // 100; s[a] -= mv; s[b] += mv
            else:
                mvq = q if s[b] >= q else s[b]
                s[b] -= mvq; s[a] += mvq
            return s
        return f
    m = re.fullmatch(r"Work out the average of all the balances, rounded down to a whole unit\. Every line whose balance is above the average gives (\d+)% of its own balance, rounded down to a whole unit, to the line with the smallest balance\. Work out the average, the smallest line and every amount from the balances before this rule, not from balances changed during it\.", sentence)
    if m:
        p = int(m.group(1))

        def f(s):
            old = list(s)
            avg = sum(old) // len(old)
            low = old.index(min(old))
            new = list(old)
            for k, v in enumerate(old):
                if v > avg:
                    give = (v * p) // 100
                    new[k] -= give
                    new[low] += give
            return new
        return f
    m = re.fullmatch(r"Do this (three|four|five) times in a row: move (\d+)% of the line with the largest balance to the line with the smallest balance, rounding the amount down to a whole unit\. Find the largest and the smallest line again each time\.", sentence)
    if m:
        times = {"three": 3, "four": 4, "five": 5}[m.group(1)]
        p = int(m.group(2))

        def f(s):
            s = list(s)
            for _ in range(times):
                big, small = max(s), min(s)
                i = next(k for k, v in enumerate(s) if v == big)
                j = next(k for k, v in enumerate(s) if v == small)
                if i != j:
                    give = (s[i] * p) // 100
                    s[i] -= give
                    s[j] += give
            return s
        return f
    m = re.fullmatch(r"The line with the second-largest balance gives (\d+)% of its balance, rounded down to a whole unit, to the line with the second-smallest balance\. Where balances are equal, the line listed first in the order above counts first, whether counting from the largest or from the smallest\.", sentence)
    if m:
        p = int(m.group(1))

        def f(s):
            s = list(s)
            ranked = sorted(zip(s, range(len(s))), key=lambda x: (-x[0], x[1]))      # largest first, earlier line first among equals
            up = ranked[1][1]
            ranked2 = sorted(zip(s, range(len(s))), key=lambda x: (x[0], x[1]))
            down = ranked2[1][1]
            give = (s[up] * p) // 100
            s[up] -= give
            s[down] += give
            return s
        return f
    m = re.fullmatch(rf"Count the lines whose balance is below (\d+)\. Move that count times (\d+) units from {N} to the line with the smallest balance, or all of {N} if it holds fewer\. Count the lines and find the smallest line before moving anything\.", sentence)
    if m:
        t, k, a = int(m.group(1)), int(m.group(2)), ix[m.group(3)]
        assert ix[m.group(4)] == a

        def f(s):
            s = list(s)
            count = len([v for v in s if v < t])
            low = next(i for i, v in enumerate(s) if v == min(s))
            amount = count * k
            if amount > s[a]:
                amount = s[a]
            s[a] -= amount
            s[low] += amount
            return s
        return f
    m = re.fullmatch(r"Go through the lines one at a time, in the order above\. Each line whose balance is above (\d+) when its turn comes gives (\d+) units to the line, other than itself, that has the smallest balance at that moment\.", sentence)
    if m:
        limit, amount = int(m.group(1)), int(m.group(2))

        def f(s):
            s = list(s)
            for turn in range(len(s)):
                if s[turn] > limit:
                    rest = [k for k in range(len(s)) if k != turn]
                    low = min(s[k] for k in rest)
                    target = next(k for k in rest if s[k] == low)
                    s[turn] -= amount
                    s[target] += amount
            return s
        return f
    m = re.fullmatch(r"Move (\d+) units from the line with the largest balance to the line with the smallest balance, or all of it if it holds fewer; then remove (\d+) units from the line that now has the largest balance, or all of it if it holds fewer\.", sentence)
    if m:
        amount, remove = int(m.group(1)), int(m.group(2))

        def f(s):
            s = list(s)
            i = next(k for k, v in enumerate(s) if v == max(s))
            j = next(k for k, v in enumerate(s) if v == min(s))
            moved = amount if s[i] >= amount else s[i]
            s[i] -= moved
            s[j] += moved
            top = next(k for k, v in enumerate(s) if v == max(s))
            s[top] -= remove if s[top] >= remove else s[top]
            return s
        return f
    m = re.fullmatch(r"Do this (three|four|five) times in a row: move (\d+) units from the line with the largest balance to the line with the smallest balance, or all of it if it holds fewer\. Find the largest and the smallest line again each time\.", sentence)
    if m:
        times, amount = {"three": 3, "four": 4, "five": 5}[m.group(1)], int(m.group(2))

        def f(s):
            s = list(s)
            for _ in range(times):
                i = next(k for k, v in enumerate(s) if v == max(s))
                j = next(k for k, v in enumerate(s) if v == min(s))
                moved = amount if s[i] >= amount else s[i]
                s[i] -= moved
                s[j] += moved
            return s
        return f
    raise AssertionError(f"rule sentence not understood by the re-solver: {sentence!r}")


def house_step(limit: int, amount: int):
    """The printed house rule as a function of a state (written here, independently of ledger.House)."""
    def g(s):
        s = list(s)
        low = next(k for k, v in enumerate(s) if v == min(s))
        high = next(k for k, v in enumerate(s) if v == max(s))
        if s[low] < limit and low != high:
            moved = amount if s[high] >= amount else s[high]
            s[high] -= moved
            s[low] += moved
        return s
    return g


def parse_parts(prompt: str):
    """(line names, {label: bare rule function}, the house rule as (limit, amount) or None, sequences) read from the printed prompt."""
    m = re.search(r"in this order: (.+?)\. A value looks like", prompt)
    assert m, "line names not found"
    parts = re.split(r", | and ", m.group(1))
    names = [x for x in parts if x]
    rules: Dict[str, object] = {}
    for mm in re.finditer(r"^([A-Z]{1,2}): (.+)$", prompt, re.M):
        rules[mm.group(1)] = parse_rule(mm.group(2), names)
    hm = re.search(r"House rule: straight after every rule, as part of the same step, if the line with the smallest balance is below (\d+), "
                   r"move (\d+) units to it from the line with the largest balance, or all of that line if it holds fewer\. The house rule "
                   r"acts at most once per step, always after that step's own rule, and does not act again on its own result\. If the largest "
                   r"and the smallest line are the same line, nothing moves\. The balances you write for a step are the ones after the "
                   r"house rule\.", prompt)
    assert ("House rule:" in prompt) == bool(hm), "a house rule is announced but not understood (or the other way round)"
    house = (int(hm.group(1)), int(hm.group(2))) if hm else None
    seqs = []
    for mm in re.finditer(r"^\d+\. Start at \[([\d, ]*)\]\. Apply ([A-Z, ]+)\.$", prompt, re.M):
        seqs.append(([int(x) for x in mm.group(1).split(", ")], mm.group(2).split(", ")))
    return names, rules, house, seqs


def parse(prompt: str):
    names, rules, house, seqs = parse_parts(prompt)
    if house:
        h = house_step(*house)
        rules = {lab: (lambda f: (lambda s: h(f(s))))(fn) for lab, fn in rules.items()}
    return names, rules, seqs


def solve(prompt: str) -> List[List[List[int]]]:
    """For each sequence in the PRINTED prompt: the balances after each rule."""
    names, rules, seqs = parse(prompt)
    out = []
    for start, labels in seqs:
        s, states = list(start), []
        for lab in labels:
            s = rules[lab](s)
            assert all(v >= 0 for v in s), "a balance went negative"
            states.append(list(s))
        out.append(states)
    return out


def _chain_fns(prompt: str):
    names, rules, seqs = parse(prompt)
    return rules, seqs


def check_puzzle(p) -> None:
    solved = solve(p.prompt)
    assert len(solved) == p.width
    for ch, states in zip(p.chains, solved):
        assert states == ch.states, "prompt text disagrees with the stored states"
    assert [s[-1] for s in solved] == p.answer
    rules, seqs = _chain_fns(p.prompt)
    used = [lab for _, labels in seqs for lab in labels]
    assert len(used) == p.params.total_steps and len(set(used)) == len(used), "every applied rule is used exactly once"
    unused = sorted(set(rules) - set(used))
    assert len(unused) == p.params.decoys and sorted(p.decoys) == unused, ("decoys", unused, p.decoys)
    # L1: every step changes the state, on the chain and on each piece
    for (start, labels), states in zip(seqs, solved):
        prev = start
        for lab, st in zip(labels, states):
            assert st != prev, f"rule {lab} changed nothing"
            prev = st
    # L3: names, determinism of ties are in the sentences; the grader accepts the reference and rejects a one-unit slip
    assert grade_d31(reference_reply(p), p)["all_correct"]
    slip = [list(a) for a in p.answer]
    slip[-1][0] += 1
    bad = "\n".join(([] if p.depth == 1 else [x for x in reference_reply(p).splitlines() if x.startswith(f"{p.width}.")][:0]) +
                    ["Answer: " + ", ".join(f"{i} = [{', '.join(map(str, a))}]" for i, a in enumerate(slip, 1))])
    g = grade_d31(bad, p)
    assert not g["all_correct"] and g["pieces_right"] == p.width - 1
    hit = re.search(BANNED, p.prompt.lower())
    assert not hit, f"non-neutral word in the prompt: {hit.group(0)}"
    assert "$" not in p.prompt, "no currency symbol"
    # the pieces do not start from the chain's own states (no answer leak between shapes)
    # L1/L2 brute force on the whole rulebook, in the printed order, from the stored reference start
    if p.depth == p.params.total_steps:
        start, labels = seqs[0]
        fns = [rules[x] for x in labels]
        full = _run(fns, start)
        m = len(fns)
        for size in (1, 2, 3):
            for combo in itertools.combinations(range(m), size):
                assert _run(fns, start, set(combo)) != full, ("steps can be left out", combo)
        for i in range(m):
            for j in range(i + 3, m):
                assert _run(fns, start, set(range(i, j + 1))) != full, ("stretch", i, j)
        rate = _absorption(fns, start)
        assert rate <= ABSORPTION_CAP, ("absorption", rate)
        assert abs(rate - p.absorption) < 1e-3, ("stored absorption differs", rate, p.absorption)
        by_size = _transfer_absorption(fns, start)                     # B1/M1: off-by-d transfers, d = 1, 10, 100, from k = 0, EACH size capped
        assert max(by_size.values()) <= ABSORPTION_CAP, ("transfer absorption", by_size)
        for d, v in by_size.items():
            assert abs(v - p.transfer_by_size[str(d)]) < 1e-3, ("stored transfer absorption differs", d, v, p.transfer_by_size)
        names_, bare_rules, house_, _ = parse_parts(p.prompt)
        hv = _house_variants([bare_rules[x] for x in labels], house_, start)    # M3: the house rule left out or done twice
        assert max(hv.values()) <= ABSORPTION_CAP, ("house-rule slip absorption", hv)
        for k_, v in hv.items():
            assert abs(v - p.house_variants[k_]) < 1e-3, ("stored house-variant absorption differs", k_, v, p.house_variants)
    names_p, bare_p, house_p, _ = parse_parts(p.prompt)
    _check_steps(p, bare_p, house_p, seqs, solved)


def _run(fns, s, skip=frozenset()):
    s = list(s)
    for i, f in enumerate(fns):
        if i not in skip:
            s = f(s)
    return s


def _transfer_absorption(fns, start, sizes=(1, 10, 100)) -> Dict[int, float]:
    """Written separately from ledger.transfer_absorption_by_size: d units that belong on line i sit on line j, for every ordered pair of
    lines that the step changed, after each step and at the start; one rate per size d."""
    trail = [list(start)]
    for f in fns:
        trail.append(list(f(trail[-1])))
    final = trail[-1]
    hit = {d: 0 for d in sizes}
    seen = {d: 0 for d in sizes}
    for k in range(len(fns)):
        prev, cur = (trail[0], trail[1]) if k == 0 else (trail[k - 1], trail[k])
        moved = [q for q in range(len(cur)) if cur[q] != prev[q]]
        for i, j in itertools.permutations(moved, 2):
            for d in sizes:
                x = list(trail[k])
                if x[j] < d:
                    continue
                x[i] += d
                x[j] -= d
                for f in fns[k:]:
                    x = f(x)
                seen[d] += 1
                hit[d] += x == final
    return {d: (hit[d] / seen[d] if seen[d] else 0.0) for d in sizes}


def _house_variants(bare_fns, house, start) -> Dict[str, float]:
    """The house rule left out, or done twice, at each step where that changes the result; the rest is replayed. (Independent of ledger.)"""
    if house is None:
        return {"omit": 0.0, "double": 0.0}
    h = house_step(*house)
    states = [list(start)]
    for f in bare_fns:
        states.append(h(f(states[-1])))
    final = states[-1]
    got = {"omit": [0, 0], "double": [0, 0]}
    for k, f in enumerate(bare_fns):
        r = f(states[k])
        once = h(r)
        for name, alt in (("omit", r), ("double", h(once))):
            if alt == once:
                continue
            x = alt
            for g in bare_fns[k + 1:]:
                x = h(g(x))
            got[name][1] += 1
            got[name][0] += x == final
    return {n: (v[0] / v[1] if v[1] else 0.0) for n, v in got.items()}


def _extremes_ok(x, depth=1) -> bool:
    v = sorted(x)
    if len(v) <= depth + 1:
        return len(set(v)) == len(v)
    top, bottom = v[::-1][:depth + 1], v[:depth + 1]
    return len(set(top)) == len(top) and len(set(bottom)) == len(bottom)


def _repeat_trace(sentence, state):
    """Intermediate states and moves of a 'do this n times' rule or the first part of a two-part rule, simulated from the printed sentence."""
    m = re.fullmatch(r"Do this (three|four|five) times in a row: move (\d+) units from the line with the largest balance to the line with the smallest balance, "
                     r"or all of it if it holds fewer\. Find the largest and the smallest line again each time\.", sentence)
    if m:
        times, amount, percent = {"three": 3, "four": 4, "five": 5}[m.group(1)], int(m.group(2)), None
    else:
        m = re.fullmatch(r"Do this (three|four|five) times in a row: move (\d+)% of the line with the largest balance to the line with the smallest balance, "
                         r"rounding the amount down to a whole unit\. Find the largest and the smallest line again each time\.", sentence)
        if not m:
            return None
        times, amount, percent = {"three": 3, "four": 4, "five": 5}[m.group(1)], None, int(m.group(2))
    x, trail, moves = list(state), [], []
    for _ in range(times):
        i = next(k for k, v in enumerate(x) if v == max(x))
        j = next(k for k, v in enumerate(x) if v == min(x))
        moved = (amount if x[i] >= amount else x[i]) if amount is not None else (x[i] * percent) // 100
        x[i] -= moved
        x[j] += moved
        trail.append(list(x))
        moves.append((i, j))
    return trail, moves


def _check_steps(p, rules_parts, house, seqs, solved) -> None:
    """Edith M2, M4, B3, B4, m2 from the printed text, on every step of every sequence: the bare rule does something; a repeat never undoes itself;
    no tie decides an order-dependent pick (the extremes the rule uses, and the same inside repeats, two-part rules, sweeps and the house rule's
    pick); no threshold or comparison is hit exactly."""
    names = p.line_names
    N = "(" + "|".join(names) + ")"
    sentences = {lab: txt for lab, _, txt in p.rulebook}
    for (start, labels), states in zip(seqs, solved):
        before = [start] + states[:-1]
        for lab, s in zip(labels, before):
            tx = sentences[lab]
            bare = rules_parts[lab](s)
            assert list(bare) != list(s), f"rule {lab} does nothing by itself (the house rule would hide it)"
            depth = 2 if "second-largest" in tx else 1
            if re.search(r"largest|smallest|second-|average", tx):
                assert _extremes_ok(s, depth), f"rule {lab}: a pick is tied at {s}"
            tr = _repeat_trace(tx, s)
            if tr is not None:
                trail, moves = tr
                for x in trail:
                    assert _extremes_ok(x), f"rule {lab}: a pick is tied inside the repeat at {x}"
                if "units from" in tx:                                  # the fixed-amount repeat (Edith M2)
                    assert len(set(moves)) >= 2, f"rule {lab}: the repeat never changes its pick"
                    assert all(x != trail[-1] for x in trail[:-1]), f"rule {lab}: doing fewer moves gives the same state as all of them"
                    assert all(moves[q] != (moves[q - 1][1], moves[q - 1][0]) for q in range(1, len(moves))), f"rule {lab}: a move undoes the one before"
                    if house is not None:                               # Edith R3-3: and once the house rule has acted
                        hs = house_step(*house)
                        assert all(hs(list(x)) != hs(list(trail[-1])) for x in trail[:-1]), f"rule {lab}: fewer moves give the same state after the house rule"
            m2 = re.fullmatch(r"Move (\d+) units from the line with the largest balance to the line with the smallest balance, or all of it if it holds "
                              r"fewer; then remove (\d+) units from the line that now has the largest balance, or all of it if it holds fewer\.", tx)
            if m2:
                x = list(s)
                i = next(k for k, v in enumerate(x) if v == max(x))
                j = next(k for k, v in enumerate(x) if v == min(x))
                moved = min(int(m2.group(1)), x[i])
                x[i] -= moved
                x[j] += moved
                assert _extremes_ok(x), f"rule {lab}: the second pick is tied at {x}"
                assert next(k for k, v in enumerate(x) if v == max(x)) != i, f"rule {lab}: the pick does not change after the first move"
            m3 = re.fullmatch(r"Go through the lines one at a time, in the order above\. Each line whose balance is above (\d+) when its turn comes gives "
                              r"(\d+) units to the line, other than itself, that has the smallest balance at that moment\.", tx)
            if m3:
                limit, amount = int(m3.group(1)), int(m3.group(2))
                assert amount < limit, f"rule {lab}: the sweep gives at least its own threshold"
                x = list(s)
                receivers, givers = set(), 0
                for turn in range(len(x)):
                    assert x[turn] != limit, f"rule {lab}: a balance sits exactly on {limit} at its turn"
                    if x[turn] > limit:
                        rest = [q for q in range(len(x)) if q != turn]
                        low = min(x[q] for q in rest)
                        assert sum(1 for q in rest if x[q] == low) == 1, f"rule {lab}: the smallest other line is tied at its turn"
                        j = next(q for q in rest if x[q] == low)
                        x[turn] -= amount
                        x[j] += amount
                        receivers.add(j)
                        givers += 1
                assert len(receivers) >= 2, f"rule {lab}: the receiver never changes"
                assert 2 <= givers <= 4, f"rule {lab}: {givers} lines give in the sweep (2 to 4 expected)"
            if "whose balance is above the average" in tx:
                assert sum(s) // len(s) not in s, f"rule {lab}: a balance sits exactly on the average"
            m4 = re.fullmatch(rf"If {N} is more than twice {N}, .*", tx)
            if m4:
                assert s[names.index(m4.group(1))] != 2 * s[names.index(m4.group(2))], f"rule {lab}: {m4.group(1)} is exactly twice {m4.group(2)}"
            if house is not None:
                assert _extremes_ok(bare), f"rule {lab}: the house rule's pick is tied at {bare}"
                assert min(bare) != house[0], f"rule {lab}: the smallest line sits exactly on the house threshold"
            for m in re.finditer(rf"{N} is (?:above|below) (\d+)", tx):
                assert s[names.index(m.group(1))] != int(m.group(2)), f"rule {lab}: {m.group(1)} sits exactly on {m.group(2)}"
            for m in re.finditer(r"whose balance is below (\d+)|whose balance is below (\d+);|is below (\d+); if no line", tx):
                limit = int(next(g for g in m.groups() if g))
                assert limit not in s, f"rule {lab}: a balance sits exactly on {limit}"


def _absorption(fns, start) -> float:
    states, s = [], list(start)
    for f in fns:
        s = f(s)
        states.append(list(s))
    final = states[-1]
    at = [list(start)] + states[:-1]               # the start (k = 0) and the state after each of the first 23 steps
    absorbed = total = 0
    for k in range(len(fns)):
        for j in range(len(start)):
            for d in (1, -1):
                v = at[k][j] + d
                if v < 0:
                    continue
                t = list(at[k]); t[j] = v
                for f in fns[k:]:
                    t = f(t)
                total += 1
                absorbed += (t == final)
    return absorbed / total


def selftest(n_seeds: int = 3, presets=None) -> None:
    total = 0
    for name, params in SETTINGS.items():
        if name in RETIRED or (presets is not None and name not in presets):
            continue
        for i in range(n_seeds):
            seed = derive_seed("ledger-selftest", name, i)
            n = params.total_steps                     # D-86: N one-step pieces, one chain of N, and a middle wiring
            ps = [generate(seed, w, d, params) for w, d in ((n, 1), (1, n), (6, 4) if n == 24 else (n // 2, 2))]
            for p in ps:
                check_puzzle(p)
                assert generate(seed, p.width, p.depth, params).to_json() == p.to_json(), "not deterministic"
                total += 1
            # the same N rules in the same order at every wiring
            flat = [[lab for ch in p.chains for lab in ch.names] for p in ps]
            assert all(f == flat[0] for f in flat), "rules or order differ across wirings"
            assert len({tuple(r) for r in (pp.rulebook for pp in ps)}) == 1, "rulebooks differ across wirings"
            # pieces do not start from the chain's own states
            chain_states = {tuple(x) for x in ps[1].chains[0].states} | {tuple(ps[1].chains[0].start)}
            assert not any(tuple(c.start) in chain_states for c in ps[0].chains), "a piece starts from a chain state"
    # a corrupted prompt must be caught
    p = generate(derive_seed("ledger-selftest", "bad"), 1, SETTINGS["l1"].total_steps, SETTINGS["l1"])
    p.prompt = p.prompt.replace(" 6%", " 7%", 1) if " 6%" in p.prompt else p.prompt.replace("Add ", "Add 1", 1)
    try:
        check_puzzle(p)
    except AssertionError:
        pass
    else:
        raise AssertionError("corrupted prompt was not caught")
    print(f"ok: {total} puzzles over settings {', '.join(SETTINGS)}; prompts re-solved from the printed text by an independent parser; "
          f"every step changes the state; no skippable steps; absorption <= {ABSORPTION_CAP:.0%}")


if __name__ == "__main__":
    selftest(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
