"""Self-test for the prototype generator, plus a draft scorer.

    python3 -m harness.taskgen.check

The key check re-solves every puzzle from its PROMPT TEXT ALONE, with a separate parser and solver
that share no code with the generator. If the printed rules or start values ever disagree with the
hidden answer or trace, this fails. It also checks determinism, the wiring, rule balance, and that
the four structure levels of one seed carry the same rulebook and rule sequence.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import re
import sys
from typing import Dict, List, Optional

from collections import Counter

from .prompt_d31 import BANNED as BANNED_D31, first_wrong_step, numbering_problems, parse_answer, parse_steps, score_answer
from .puzzle import PRESETS, STRUCTURE_LEVELS, Params, Puzzle, Rule, find_shortcut, generate, probe_values
from .rng import HashRNG, derive_seed

ORD = {"1st": 0, "2nd": 1, "3rd": 2, "4th": 3, "5th": 4, "6th": 5, "7th": 6, "8th": 7, "9th": 8}


# ---------------------------------------------------------------- independent parser and solver (prompt text only)

def parse_prompt(prompt: str):
    """Return (n, rules, sequences) read from the prompt text alone.

    rules: label -> ("affine", a, b) | ("table", [10 ints]) | ("pair", [100 ints]) | ("shuffle", [positions]).
    sequences: list of (start, [labels]).
    """
    n = int(re.search(r"exactly (\d+) digits", prompt).group(1))
    rules: Dict[str, tuple] = {}
    for m in re.finditer(r"^([A-Z]): multiply by (\d+), add (\d+), then keep only the last (\d+) digits\.$", prompt, re.M):
        assert int(m.group(4)) == n, f"rule {m.group(1)} says last {m.group(4)} digits, header says {n}"
        rules[m.group(1)] = ("affine", int(m.group(2)), int(m.group(3)))
    for m in re.finditer(r"^([A-Z]): replace each digit using this table: (.+)\.$", prompt, re.M):
        t = dict(pair.split("→") for pair in m.group(2).split(", "))
        assert sorted(t) == [str(d) for d in range(10)]
        rules[m.group(1)] = ("table", [int(t[str(d)]) for d in range(10)])
    for m in re.finditer(r"^([A-Z]): cut the value into pairs of digits, starting from the left \((\d+) pairs\), "
                         r"and replace each pair using this table: (.+)\.$", prompt, re.M):
        assert int(m.group(2)) * 2 == n, f"rule {m.group(1)} says {m.group(2)} pairs, header says {n} digits"
        t = dict(pair.split("→") for pair in m.group(3).split(", "))
        assert sorted(t) == ["%02d" % k for k in range(100)]
        assert all(len(v) == 2 for v in t.values())
        rules[m.group(1)] = ("pair", [int(t["%02d" % k]) for k in range(100)])
    for m in re.finditer(r"^([A-Z]): reorder the digits; the new value is the old (.+) digits, in that order\.$", prompt, re.M):
        rules[m.group(1)] = ("shuffle", [ORD[w] for w in m.group(2).split(", ")])
    seqs = [(m.group(1), m.group(2).split(", "))
            for m in re.finditer(r"^\d+\. Start at (\d+)\. Apply ([A-Z, ]+)\.$", prompt, re.M)]
    return n, rules, seqs


def apply_rule(rule: tuple, v: str, n: int) -> str:
    if rule[0] == "affine":
        return str((int(v) * rule[1] + rule[2]) % 10**n).zfill(n)
    if rule[0] == "table":
        return "".join(str(rule[1][int(c)]) for c in v)
    if rule[0] == "pair":
        return "".join("%02d" % rule[1][int(v[i:i + 2])] for i in range(0, n, 2))
    return "".join(v[i] for i in rule[1])


def solve_from_text(prompt: str) -> List[List[str]]:
    """Per sequence, the list of values after each step, using only the prompt text."""
    n, rules, seqs = parse_prompt(prompt)
    out = []
    for start, labels in seqs:
        v, vals = start, []
        for lab in labels:
            v = apply_rule(rules[lab], v, n)
            vals.append(v)
        out.append(vals)
    return out


def _probes(n: int, count: int = 4) -> List[str]:
    """Test values for the checks below; a different recipe from the generator's own."""
    out = []
    for k in range(count):
        h = hashlib.sha256(f"check-probe|{n}|{k}".encode()).hexdigest()
        out.append(str(int(h, 16) % 10**n).zfill(n))
    return out


def check_rulebook(n: int, rules: Dict[str, tuple]) -> None:
    """Checks on one rulebook, cheap enough for every puzzle."""
    labels = sorted(rules)
    for lab in labels:
        r = rules[lab]
        if r[0] == "affine":
            assert math.gcd(r[1], 10) == 1, f"{lab}: multiplier shares a factor with 10, so not reversible"
            assert 1 < r[1] < 10**n and 0 < r[2] < 10**n, f"{lab}: multiplier or addend out of range"
        elif r[0] == "table":
            assert sorted(r[1]) == list(range(10)), f"{lab}: table is not a permutation"
            assert all(r[1][d] != d for d in range(10)), f"{lab}: table has a fixed digit"
        elif r[0] == "pair":
            assert n % 2 == 0
            assert sorted(r[1]) == list(range(100)), f"{lab}: pair table is not a permutation"
            assert all(r[1][d] != d for d in range(100)), f"{lab}: pair table has a fixed pair"
        else:
            assert sorted(r[1]) == list(range(n)), f"{lab}: order is not a permutation"
            assert all(r[1][i] != i for i in range(n)), f"{lab}: shuffle leaves a digit in place"
    probes = _probes(n, 6)
    for x, y in itertools.permutations(labels, 2):
        assert rules[x] != rules[y], f"{x} and {y} are the same rule"
        # y after x must not give the value back (they would undo each other), on several values
        assert any(apply_rule(rules[y], apply_rule(rules[x], v, n), n) != v for v in probes), f"{x},{y} undo each other"


def check_no_shortcut(n: int, rules: Dict[str, tuple], labels: List[str]) -> None:
    """No steps can be left out without changing the result. Brute force, from the parsed prompt.

    Written separately from puzzle.find_shortcut: it re-runs the whole sequence with the steps removed,
    for every pair and triple of steps, every stretch of 2 or more steps, and, within every stretch, all
    the steps of one kind.
    """
    m = len(labels)
    probes = _probes(n, 3)

    def run(v: str, skip: set) -> str:
        for i, lab in enumerate(labels):
            if i not in skip:
                v = apply_rule(rules[lab], v, n)
        return v

    full = [run(v, set()) for v in probes]

    def same(skip: set) -> bool:
        return all(run(v, skip) == f for v, f in zip(probes, full))

    # cheapest tests first; the first probe alone rules out nearly every candidate
    def maybe(skip: set) -> bool:
        return run(probes[0], skip) == full[0] and same(skip)

    for a in range(m):
        for b in range(a + 1, m):
            assert not maybe(set(range(a, b + 1))), f"stretch {a}..{b} can be skipped: {labels}"
            for kind in ("affine", "table", "pair", "shuffle"):
                idx = {i for i in range(a, b + 1) if rules[labels[i]][0] == kind}
                if len(idx) >= 2:
                    assert not maybe(idx), f"all {kind} steps in {a}..{b} can be skipped: {labels}"
            assert not maybe({a, b}), f"steps {a},{b} can be skipped: {labels}"
            for c in range(b + 1, m):
                assert not maybe({a, b, c}), f"steps {a},{b},{c} can be skipped: {labels}"


# ---------------------------------------------------------------- draft scorer

def parse_final(reply: str, n_digits: int = 4) -> Optional[List[str]]:
    """Values on the LAST line that starts with `Final:`; None if there is no such line."""
    lines = [ln for ln in reply.strip().splitlines() if ln.strip().strip("`*").lower().startswith("final:")]
    if not lines:
        return None
    body = lines[-1].split(":", 1)[1]
    return re.findall(rf"(?<!\d)\d{{{n_digits}}}(?!\d)", body)


def score(reply: str, p: Puzzle) -> Dict[str, object]:
    got = parse_final(reply, p.params.n_digits)
    if got is None:
        return {"parsed": False, "all_correct": False, "chains_correct": 0, "chains": p.width}
    length_ok = len(got) == p.width
    # Per-sequence credit pairs values by position, so a dropped or extra value would shift every later
    # one. Without the right number of values it gets 0.
    right = sum(1 for g, a in zip(got, p.answer) if g == a) if length_ok else 0
    return {
        "parsed": True,
        "all_correct": got == p.answer,          # primary (draft): every chain right, nothing extra
        "chains_correct": right,                   # secondary (draft): per-chain credit
        "chains": p.width,
        "length_ok": length_ok,
    }


# ---------------------------------------------------------------- self-test

def _check_puzzle(p: Puzzle) -> None:
    # trace is internally consistent
    for ch in p.chains:
        assert ch.steps[0].input == ch.start
        for a, b in zip(ch.steps, ch.steps[1:]):
            assert a.output == b.input, "chain is not wired output → input"
        assert [s.rule for s in ch.steps] == ch.rules
    assert p.answer == [ch.end for ch in p.chains]
    # independent re-solve from prompt text matches trace and answer
    solved = solve_from_text(p.prompt)
    assert len(solved) == p.width, (len(solved), p.width)
    for ch, vals in zip(p.chains, solved):
        assert vals == [s.output for s in ch.steps], "prompt text disagrees with trace"
    assert [v[-1] for v in solved] == p.answer
    # scorer accepts the reference answer and rejects a one-digit slip
    if p.answer_line.startswith("Answer:"):
        _check_d31_reply(p)
    else:
        assert score(render_reference_reply(p), p)["all_correct"]
        slipped = list(p.answer)
        slipped[-1] = slipped[-1][:-1] + str((int(slipped[-1][-1]) + 1) % 10)
        assert not score("Final: " + ", ".join(slipped), p)["all_correct"]
    # balance: each rule used equally often across the whole puzzle
    counts: Dict[str, int] = {}
    for ch in p.chains:
        for r in ch.rules:
            counts[r] = counts.get(r, 0) + 1
    assert max(counts.values()) - min(counts.values()) <= 1, counts
    assert len(counts) == len(p.rulebook)
    # no rule twice in a row (a repeat can cancel itself, a shortcut only chains would get)
    for ch in p.chains:
        assert all(a != b for a, b in zip(ch.rules, ch.rules[1:])), ch.rules
    # rulebook and rule order: checks on every puzzle, written separately from the generator
    n, rules, seqs = parse_prompt(p.prompt)
    assert n == p.params.n_digits and len(rules) == p.params.n_rules()
    check_rulebook(n, rules)
    for _, labels in seqs:
        check_no_shortcut(n, rules, labels)
    # no neutral-text violations (prefix match on word starts; includes the checklist's list)
    hit = re.search(BANNED_D31 if p.answer_line.startswith("Answer:") else BANNED, p.prompt.lower())
    assert not hit, f"non-neutral word in prompt: {hit.group(0)}"


BANNED = (r"\b(grad|test|evaluat|scor|reasoning|correct|cipher|encrypt|password|check|benchmark|judg|"
          r"mark|exam|quiz)")


def _check_d31_reply(p: Puzzle) -> None:
    """The D-31 reply format: step lines `S.K = v` (when sequences have more than one rule) and a numbered answer line."""
    lines = []
    if p.depth > 1:
        for s_i, ch in enumerate(p.chains, 1):
            lines += [f"{s_i}.{k} = {st.output}" for k, st in enumerate(ch.steps, 1)]
    ref = "\n".join(lines + [p.answer_line])
    sc = score_answer(ref, p.answer)
    assert sc["all_correct"] and sc["pieces_right"] == p.width and sc["length_ok"], sc
    got = parse_steps(ref)
    for s_i, ch in enumerate(p.chains, 1):
        if p.depth > 1:
            assert [got[(s_i, k)] for k in range(1, p.depth + 1)] == [st.output for st in ch.steps]
            assert first_wrong_step(ref, [st.output for st in ch.steps], s_i, p.width) is None
    # one wrong digit in the last entry: whole answer wrong, other pieces keep their credit
    bad = list(p.answer)
    bad[-1] = bad[-1][:-1] + str((int(bad[-1][-1]) + 1) % 10)
    sc = score_answer("Answer: " + ", ".join(f"{i} = {a}" for i, a in enumerate(bad, 1)), p.answer)
    assert not sc["all_correct"] and sc["pieces_right"] == p.width - 1, sc
    # a dropped entry: whole answer wrong, the others still matched by number
    if p.width > 1:
        short = "Answer: " + ", ".join(f"{i} = {a}" for i, a in enumerate(p.answer, 1) if i != 2)
        sc = score_answer(short, p.answer)
        assert not sc["all_correct"] and not sc["length_ok"] and sc["pieces_right"] == p.width - 1, sc
    # a wrong step line is found at its place
    if p.depth > 1:
        ch = p.chains[0]
        wrong = list(lines)
        wrong[2] = "1.3 = " + ("0" if ch.steps[2].output != "0" * len(ch.steps[2].output) else "1") * len(ch.steps[2].output)
        assert first_wrong_step("\n".join(wrong + [p.answer_line]), [st.output for st in ch.steps], 1, p.width) == 3
        # a skipped step line is skipped, not placed as a slip; a numbering slip is flagged instead of placed
        ch = p.chains[0]
        skipped = [ln for i, ln in enumerate(lines) if i != 1]
        assert first_wrong_step("\n".join(skipped + [p.answer_line]), [st.output for st in ch.steps], 1, p.width) is None
        shifted = ["1.0 = " + lines[0].split("= ")[1]] + lines[1:]
        assert numbering_problems("\n".join(shifted), p.width, p.depth) == ["1.0"]
        assert first_wrong_step("\n".join(shifted), [st.output for st in ch.steps], 1, p.width) is None
        assert numbering_problems("\n".join(lines), p.width, p.depth) == []
    # no answer line at all
    assert not score_answer("1.1 = 0000", p.answer)["parsed"]


def render_reference_reply(p: Puzzle) -> str:
    return "Worked solution omitted.\n" + p.answer_line


def _bijective(rule, n: int) -> bool:
    outs = {rule.run(str(v).zfill(n)) for v in range(10**n)}
    return len(outs) == 10**n


def _expect_raise(fn) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected the generator to raise")


# Steps of each kind in every puzzle at a preset (24 steps in all), written out by hand and independent of Params.
EXPECTED_MIX = {
    "d0": {"affine": 8, "table": 8, "pair": 0, "shuffle": 8},
    "d1": {"affine": 8, "table": 8, "pair": 0, "shuffle": 8},
    "d2": {"affine": 6, "table": 6, "pair": 6, "shuffle": 6},
    "d3": {"affine": 6, "table": 6, "pair": 6, "shuffle": 6},
    "d4": {"affine": 6, "table": 6, "pair": 6, "shuffle": 6},
    "d4s": {"affine": 6, "table": 6, "pair": 6, "shuffle": 6},
    "d4p": {"affine": 4, "table": 4, "pair": 8, "shuffle": 8},
}


def selftest(n_seeds: int = 100) -> None:
    digests = set()
    total = 0
    assert set(EXPECTED_MIX) == set(PRESETS), "every preset needs an expected mix"
    for name, params in PRESETS.items():
        # d0 gets the full count; the larger presets are slower to check (long prompts, big rulebooks)
        count = n_seeds if name == "d0" else max(10, n_seeds // 5)
        for i in range(count):
            seed = derive_seed("selftest", name, i)
            levels = [generate(seed, w, d, params) for w, d in STRUCTURE_LEVELS]
            for p in levels:
                _check_puzzle(p)
                # determinism: regenerate and compare byte for byte
                assert generate(seed, p.width, p.depth, params).to_json() == p.to_json()
                digests.add(hashlib.sha256(p.prompt.encode()).hexdigest())
                total += 1
            # same seed → same rulebook and same rule sequence at every level; only wiring and starts differ
            flat = [[r for ch in p.chains for r in ch.rules] for p in levels]
            assert all(f == flat[0] for f in flat)
            assert all([r.describe(params.n_digits) for r in p.rulebook]
                       == [r.describe(params.n_digits) for r in levels[0].rulebook] for p in levels)
            # equal work: the same number of steps of each kind at every level
            kinds = {tuple(sorted(Counter(s.kind for ch in p.chains for s in ch.steps).items())) for p in levels}
            assert len(kinds) == 1
            # and the same mix in every puzzle at one setting (fixed, not random). The expected counts are
            # written out per preset here, not computed from Params, so a wrong dial or a drifting mix is caught.
            expected = tuple(sorted((k, c) for k, c in EXPECTED_MIX[name].items() if c))
            assert kinds == {expected}, (name, kinds)
    assert len(digests) == total, "two prompts collided"

    # exhaustive sweep (all 10^4 values) of a few d0 rulebooks: every rule is a bijection, and no two undo each other
    for i in range(3):
        book = generate(derive_seed("selftest", "d0", i), 1, 24, PRESETS["d0"]).rulebook
        assert all(_bijective(r, 4) for r in book)
        for r1 in book:
            for r2 in book:
                if r1 is not r2:
                    assert any(r2.run(r1.run(v)) != v for v in (str(x).zfill(4) for x in range(10**4))), (r1.label, r2.label)
    # rng: integer seeds next to each other share nothing obvious
    assert HashRNG(1).getrandbits(64) != HashRNG(2).getrandbits(64)

    # the checker can fail: a corrupted start value in the prompt text must be caught
    bad = generate(derive_seed("selftest", 1), 6, 4, PRESETS["d2"])
    bad.prompt = bad.prompt.replace(f"Start at {bad.chains[2].start}.", "Start at " + "9" * bad.params.n_digits + ".", 1)
    _expect_assertion(lambda: _check_puzzle(bad), "corrupted prompt")

    # shortcut guard: hand-made cases, caught by BOTH implementations (generator's and checker's)
    n = 6
    swap_pairs = ("shuffle", [2, 3, 0, 1, 4, 5])      # moves whole pairs: commutes with pair tables
    swap_inside = ("shuffle", [1, 0, 2, 3, 4, 5])     # swaps inside a pair: does not commute with a random pair table
    rot_a, rot_b = ("shuffle", [1, 2, 0, 4, 5, 3]), ("shuffle", [2, 0, 1, 5, 3, 4])   # inverses
    t10 = ("table", [1, 2, 3, 4, 5, 6, 7, 8, 9, 0])
    pt = ("pair", [(k * 37 + 11) % 100 for k in range(100)])
    af = ("affine", 123, 45678)
    rules = {"L": swap_pairs, "S": swap_inside, "R": rot_a, "Q": rot_b, "E": t10, "T": pt, "A": af}
    cases = [(["L", "E", "L"], True),          # table and shuffle commute: L,E,L is just E
             (["L", "A", "L"], False),         # arithmetic does not commute with a shuffle
             (["L", "T", "L"], True),          # pair table and a pair-moving shuffle commute
             (["S", "T", "S"], False),         # a within-pair swap does not commute with the pair table
             (["R", "E", "Q"], True),          # inverse shuffles with a table between
             (["R", "T", "E", "Q"], False)]    # a pair table between breaks it
    for labels, should_fail in cases:
        try:
            check_no_shortcut(n, rules, labels)
            failed = False
        except AssertionError:
            failed = True
        assert failed == should_fail, ("checker", labels, failed)
        gen_rules = {"L": Rule("L", "shuffle", order=swap_pairs[1]), "S": Rule("S", "shuffle", order=swap_inside[1]),
                     "R": Rule("R", "shuffle", order=rot_a[1]), "Q": Rule("Q", "shuffle", order=rot_b[1]),
                     "E": Rule("E", "table", table=t10[1]), "T": Rule("T", "pair", pairs=pt[1]),
                     "A": Rule("A", "affine", mult=123, add=45678)}
        found = find_shortcut([gen_rules[l] for l in labels], probe_values(n)) is not None
        assert found == should_fail, ("generator", labels, found)

    # settings that cannot meet the guards raise instead of producing a weaker puzzle
    _expect_raise(lambda: generate("s", 1, 24, Params(n_digits=5, n_pair=2)))                  # odd digits, pair tables
    _expect_raise(lambda: generate("s", 1, 24, Params(n_digits=3, n_shuffle=3)))               # 3 digits: only 2 shuffles exist
    _expect_raise(lambda: generate("s", 1, 24, Params(n_affine=8, n_table=8, n_shuffle=8)))    # 8 shuffles of 4 digits: too few
    _expect_raise(lambda: generate("s", 1, 24, Params(n_affine=9, n_table=9, n_shuffle=9)))    # more rules than steps
    _expect_raise(lambda: generate("s", 1, 25, PRESETS["d0"]))                                 # wiring != 24
    _expect_raise(lambda: generate("s", 1, 24, Params(n_digits=4, mult_max=10**4)))            # multiplier out of range
    _expect_raise(lambda: generate("s", 1, 24, Params(n_digits=5, mult_min=101, mult_max=999,
                                                      add_min=1000, add_max=99999)))           # 999^2 wraps past 10^5

    # the dials that are not in a preset also work (5 and 9 digits, no pair tables)
    for kw in (dict(n_digits=5, mult_min=101, mult_max=316, add_min=1000, add_max=99999),
               dict(n_digits=9, n_affine=6, n_table=6, n_shuffle=6, mult_min=1001, mult_max=31622,
                    add_min=10**6, add_max=10**9 - 1)):
        for w, d in STRUCTURE_LEVELS:
            _check_puzzle(generate(derive_seed("selftest-dials"), w, d, Params(**kw)))

    # a dropped value gives no per-sequence credit, and non-neutral words are caught
    q = generate(derive_seed("selftest", 2), 6, 4, PRESETS["d0"])
    short = "Final: " + ", ".join(q.answer[:-1])
    assert score(short, q)["chains_correct"] == 0 and not score(short, q)["length_ok"]
    assert score(q.answer_line, q)["chains_correct"] == 6
    assert re.search(BANNED, "please check the exam") and not re.search(BANNED, q.prompt.lower())

    # the D-31 wording (spec item 4): both prompt styles at the shapes the study uses, every preset's first seed
    for name, params in PRESETS.items():
        for style in ("d31", "d31-answer-only"):
            for w, d in ((24, 1), (1, 24), (6, 4)):
                _check_puzzle(generate(derive_seed("selftest-d31", name), w, d, params, style=style))
    # the D-42 prompt variant: only the opening and the closing paragraphs change; rules, sequences and answers are the
    # same as the d31 style, and every parser and grader works on it (the variant is defined for the two study shapes)
    for name, params in PRESETS.items():
        for w, d in ((24, 1), (1, 24)):
            v = generate(derive_seed("selftest-d31", name), w, d, params, style="d31-variant")
            _check_puzzle(v)
            base = generate(derive_seed("selftest-d31", name), w, d, params, style="d31")
            assert v.answer == base.answer and v.answer_line == base.answer_line
            body = lambda t: t.split("\n\nRules\n", 1)[1].rsplit("\n\n", 1)[0]
            assert body(v.prompt) == body(base.prompt), "the rules and sequences must be identical"
            assert v.prompt != base.prompt and v.prompt.split("\n\n", 1)[0] != base.prompt.split("\n\n", 1)[0]
    try:
        generate(derive_seed("x"), 6, 4, PRESETS["d0"], style="d31-variant")
    except ValueError:
        pass
    else:
        raise AssertionError("the variant must refuse a shape other than 24x1 and 1x24")
    # the new wording changes only the last paragraph: same rules, sequences and answers as the legacy style
    a = generate(derive_seed("selftest-d31", "d3"), 1, 24, PRESETS["d3"])
    b = generate(derive_seed("selftest-d31", "d3"), 1, 24, PRESETS["d3"], style="d31")
    assert a.prompt.rsplit("\n\n", 1)[0] == b.prompt.rsplit("\n\n", 1)[0] and a.answer == b.answer
    # the 4-step demo shape works too
    demo = Params(total_steps=4, n_affine=1, n_table=1, n_shuffle=1)
    for w, d in ((4, 1), (1, 4)):
        _check_puzzle(generate(derive_seed("selftest-demo"), w, d, demo))
    print(f"ok: {total} puzzles over presets {', '.join(PRESETS)}; prompts re-solved from text; deterministic; "
          f"every rulebook and sequence checked for reversibility and skippable steps")


def _expect_assertion(fn, what: str) -> None:
    try:
        fn()
    except AssertionError:
        return
    raise AssertionError(f"{what} was not caught")


if __name__ == "__main__":
    selftest(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
