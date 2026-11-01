"""Self-test for the code-tracing SKETCH.

    python3 -m harness.taskgen.codetrace_check

Re-solves every puzzle from its PROMPT TEXT ALONE (pulls each `def` out, executes it, applies the
sequences), and compares with the stored answer and states. Also checks determinism, that the same seed
gives the same functions in the same order at every wiring, distinct functions, the count-gap guard,
a brute-force "no two or three steps can be left out" search (separate from puzzle.find_shortcut), the
neutral-word scan, and that a corrupted prompt is caught.
"""

from __future__ import annotations

import ast
import re
import sys
from typing import Dict, List

from .codetrace import (CTParams, SETTINGS, FINAL_RE, generate, grade, grade_d31, reference_reply, step_call,
                        fmt)
from .prompt_d31 import BANNED as BANNED_D31
from .puzzle import STRUCTURE_LEVELS
from .rng import derive_seed

BANNED = (r"\b(grad|test|evaluat|scor|reasoning|correct|cipher|encrypt|password|check|benchmark|judg|"
          r"mark|exam|quiz)")


def parse(prompt: str):
    funcs: Dict[str, object] = {}
    for m in re.finditer(r"^def (f[a-z])\(a\):\n((?:    .*\n)+)", prompt + "\n", re.M):
        ns: Dict = {}
        exec(m.group(0), {}, ns)
        funcs[m.group(1)] = ns[m.group(1)]
    seqs = [(ast.literal_eval(m.group(1)), m.group(2).split(", "))
            for m in re.finditer(r"^\d+\. Start at (\[[\d, ]*\])\. Apply ([a-z, ]+)\.$", prompt, re.M)]
    return funcs, seqs


def solve(prompt: str) -> List[List[List[int]]]:
    funcs, seqs = parse(prompt)
    out = []
    for start, names in seqs:
        v, states = start, []
        for nm in names:
            v = funcs[nm](v)
            states.append(v)
        out.append(states)
    return out


def _skippable(funcs, names, start, skip):
    a, b = list(start), list(start)
    for i, nm in enumerate(names):
        a = funcs[nm](a)
        if i not in skip:
            b = funcs[nm](b)
    return a == b


def check_puzzle(p) -> None:
    solved = solve(p.prompt)
    assert len(solved) == p.width
    for ch, states in zip(p.chains, solved):
        assert states == ch.states, "prompt text disagrees with stored states"
    assert [s[-1] for s in solved] == p.answer
    # the grader accepts the reference reply and rejects a one-number slip
    if p.style != "legacy":
        ref = reference_reply(p)
        g = grade_d31(ref, p)
        assert g["all_correct"] and g["pieces_right"] == p.width and g["length_ok"], g
        if p.depth > 1:
            assert g["first_wrong_step"] == [None] * p.width and g["steps_shown"] == p.width * p.depth
        slip = [list(a) for a in p.answer]
        slip[-1][0] = (slip[-1][0] + 1) % p.params.modulus
        bad = "Answer: " + ", ".join(f"{i} = {fmt(a)}" for i, a in enumerate(slip, 1))
        g = grade_d31(bad, p)
        assert not g["all_correct"] and g["pieces_right"] == p.width - 1, g
        if p.width > 1:   # a dropped entry is matched by number, not by position
            short = "Answer: " + ", ".join(f"{i} = {fmt(a)}" for i, a in enumerate(p.answer, 1) if i != 2)
            g = grade_d31(short, p)
            assert not g["all_correct"] and not g["length_ok"] and g["pieces_right"] == p.width - 1, g
        if p.depth > 1:   # a wrong step line is found at its place
            lines = ref.splitlines()
            lines[2] = "1.3 = " + fmt([(x + 1) % p.params.modulus for x in p.chains[0].states[2]])
            assert grade_d31("\n".join(lines), p)["first_wrong_step"][0] == 3
        # the E3 step call carries one function and one list, nothing else
        sp, expect = step_call(p, 1, 1)
        assert expect == p.chains[0].states[0] and p.chains[0].names[0] in sp and "Sequences" not in sp
    else:
        ref = "\n".join(f"Final {i + 1}: {a}" for i, a in enumerate(p.answer))
        assert grade(ref, p)["fully_right"]
        slip = [list(a) for a in p.answer]
        slip[-1][0] = (slip[-1][0] + 1) % p.params.modulus
        bad = "\n".join(f"Final {i + 1}: {a}" for i, a in enumerate(slip))
        g = grade(bad, p)
        assert not g["fully_right"] and g["pieces_right"] == p.width - 1
    assert len({src for _, src, _ in p.functions}) == len(p.functions) == p.params.total_steps
    hit = re.search(BANNED_D31 if p.style != "legacy" else BANNED, p.prompt.lower())
    assert not hit, f"non-neutral word: {hit.group(0)}"
    # brute force on the chain with the most steps: no 2 or 3 steps can be left out, no stretch of 2+
    funcs, seqs = parse(p.prompt)
    if p.width == 1:
        start, names = seqs[0]
        m = len(names)
        for probe in (start, [(x * 7 + 3) % p.params.modulus for x in start]):
            for a in range(m):
                for b in range(a + 1, m):
                    assert not _skippable(funcs, names, probe, set(range(a, b + 1))), ("stretch", a, b)
                    assert not _skippable(funcs, names, probe, {a, b}), ("pair", a, b)


def selftest(n_seeds: int = 3) -> None:
    total = 0
    for name, params in SETTINGS.items():
        for i in range(n_seeds):
            seed = derive_seed("ct-selftest", name, i)
            ps = [generate(seed, w, d, params) for w, d in STRUCTURE_LEVELS]
            for p in ps:
                check_puzzle(p)
                assert generate(seed, p.width, p.depth, params).to_json() == p.to_json()
                total += 1
            order = [tuple(c.names for c in p.chains) for p in ps]
            flat = [[n for names in o for n in names] for o in order]
            assert all(f == flat[0] for f in flat), "functions or order differ across wirings"
    # the D-31 wording (spec item 4): both styles at the two shapes the study uses, plus the old 6x4
    for name, params in SETTINGS.items():
        if name == "c0":
            continue
        for style in ("d31", "d31-answer-only"):
            for w, d in ((24, 1), (1, 24), (6, 4)):
                check_puzzle(generate(derive_seed("ct-selftest-d31", name), w, d, params, style=style))
                total += 1
    a = generate(derive_seed("ct-selftest-d31", "c3b"), 1, 24, SETTINGS["c3b"])
    b = generate(derive_seed("ct-selftest-d31", "c3b"), 1, 24, SETTINGS["c3b"], style="d31")
    assert a.prompt.rsplit("\n\n", 1)[0] == b.prompt.rsplit("\n\n", 1)[0] and a.answer == b.answer
    assert "style" not in a.to_dict() and b.to_dict()["style"] == "d31"
    # settings that cannot give a valid puzzle raise instead of producing a weaker one
    for bad_params in (CTParams(length=5), CTParams(length=15, vc_kinds=("pairmix",), blocks=2),
                       CTParams(blocks=4), CTParams(modulus=50),
                       CTParams(ro_kinds=("nested",), nested=False), CTParams(vc_kinds=("nope",))):
        try:
            generate("x", 1, 24, bad_params)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected the generator to raise for {bad_params}")
    # a corrupted prompt must be caught
    p = generate(derive_seed("ct-selftest", "bad"), 1, 24, SETTINGS["c1"])
    p.prompt = p.prompt.replace("% 100", "% 101", 1)
    try:
        check_puzzle(p)
    except AssertionError:
        pass
    else:
        raise AssertionError("corrupted prompt was not caught")
    print(f"ok: {total} puzzles over settings {', '.join(SETTINGS)}; prompts re-solved by executing the printed code")


if __name__ == "__main__":
    selftest(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
