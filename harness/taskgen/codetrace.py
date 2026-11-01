"""SKETCH generator for a second puzzle family: code tracing. Not reviewed, not final.

The value is a list of `length` whole numbers in 0..modulus-1. One step is one printed Python function
applied to the current list. A puzzle prints 24 functions, each used once, then the sequences, wired as
w chains of depth d (24x1 ... 1x24) exactly as in puzzle.py. The answer comes from EXECUTING THE PRINTED
TEXT; the same seed gives the same 24 functions in the same order at every wiring.

Each function is one or two "blocks" (value-changing loops and maps, reorderings, branches). Every block
is a bijection that ships with an inverse; the sketch checks the composed inverse on random lists, so a
wrong step can never be absorbed later and every step's input stays uniform at every wiring.

Guards, from decisions/briefings/2026-10-10-study1-design-check/check-codetracing.md:
- a value-changing block between any two count-driven blocks (otherwise a chain can count once and rotate
  twice);
- all 24 functions distinct, and wide variety of constants per template;
- no function leaves a random list unchanged more than 3% of the time;
- no two functions undo each other; the simulation-based shortcut finder from puzzle.py (run on the
  value-changing blocks' kinds and on the reordering kinds separately).
Python subset used: ints, lists, for/range with positive steps, if/else, % with brackets, tuple swaps,
slices without a step, one list comprehension form. No negative numbers appear in the code.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .puzzle import STRUCTURE_LEVELS, find_shortcut
from .rng import HashRNG

CT_VERSION = "codetrace-sketch-0.1"


@dataclass(frozen=True)
class CTParams:
    total_steps: int = 24
    length: int = 8                 # numbers per list
    modulus: int = 100              # values are 0..modulus-1
    blocks: int = 1                 # blocks per function: 1, 2 or 3 (3 = two value-changing + one reordering)
    nested: bool = False            # nested conditions in the swap block
    vc_kinds: Tuple[str, ...] = ("prefix", "condadd", "map")
    ro_kinds: Tuple[str, ...] = ("swap", "gather", "countrot")

    def validate(self) -> None:
        """Raise if the settings cannot give a valid puzzle (rather than quietly producing a weaker one)."""
        if self.total_steps != 24:
            raise ValueError("code tracing is built for 24 steps")
        if self.blocks not in (1, 2, 3):
            raise ValueError("blocks must be 1, 2 or 3")
        if self.length < (10 if "nested" in self.ro_kinds else 6):
            raise ValueError("lists are too short for the swap blocks (nested branches use 10 positions, swaps 5)")
        if self.modulus < 100:
            raise ValueError("values need a modulus of at least 100")
        unknown = [k for k in self.vc_kinds + self.ro_kinds if k not in FACTORIES]
        if unknown:
            raise ValueError(f"unknown block kinds: {unknown}")
        if "pairmix" in self.vc_kinds and self.length % 2:
            raise ValueError("pairmix needs an even list length")
        if "nested" in self.ro_kinds and not self.nested:
            raise ValueError("the nested block needs nested=True")
        if not self.vc_kinds or not self.ro_kinds:
            raise ValueError("need at least one value-changing and one reordering kind")


# Settings for the free difficulty test. c0 is the first sketch (already shown far too easy).
SETTINGS: Dict[str, CTParams] = {
    "c0": CTParams(length=8, modulus=100, blocks=1),
    "c1": CTParams(length=16, modulus=100, blocks=2,
                   vc_kinds=("prefix", "condadd", "map"), ro_kinds=("swap", "gather", "countrot")),
    "c2": CTParams(length=20, modulus=1000, blocks=2, nested=True,
                   vc_kinds=("prefix", "condadd", "lookahead", "map"),
                   ro_kinds=("swap", "nested", "gather", "countrot")),
    "c3": CTParams(length=24, modulus=1000, blocks=2, nested=True,
                   vc_kinds=("prefix", "condadd", "lookahead", "map", "pairmix"),
                   ro_kinds=("swap", "nested", "gather", "countrot")),
    # between c3 and c4, for the pilot's menu: c3's list length with c4's three blocks per function
    "c3b": CTParams(length=24, modulus=1000, blocks=3, nested=True,
                    vc_kinds=("prefix", "condadd", "lookahead", "map", "pairmix"),
                    ro_kinds=("swap", "nested", "gather", "countrot")),
    "c4": CTParams(length=32, modulus=1000, blocks=3, nested=True,
                   vc_kinds=("prefix", "condadd", "lookahead", "map", "pairmix"),
                   ro_kinds=("swap", "nested", "gather", "countrot")),
    "c5": CTParams(length=40, modulus=1000, blocks=3, nested=True,
                   vc_kinds=("prefix2", "condadd3", "lookahead", "map", "pairmix"),
                   ro_kinds=("swap", "nested", "gather", "countrot")),
}


@dataclass
class Block:
    kind: str
    cls: str                         # "vc" changes values; "ro" only moves them
    count_driven: bool
    lines: List[str]
    inv: Callable[[List[int]], List[int]]


# ---------------------------------------------------------------- block templates

def _units(M: int) -> List[int]:
    return [m for m in range(3, M) if math.gcd(m, M) == 1]


def b_prefix(r: HashRNG, L: int, M: int) -> Block:
    """Running total: each number gets a multiple of the (already updated) number before it."""
    c = r.randint(1, 9)
    k = r.choice([0, r.randint(1, M - 1)])
    expr = "a[i]" + (" + " + (f"{c} * " if c != 1 else "") + "a[i - 1]") + (f" + {k}" if k else "")
    lines = [f"for i in range(1, {L}):", f"    a[i] = ({expr}) % {M}"]

    def inv(b):
        a = list(b)
        for i in range(1, L):
            a[i] = (b[i] - c * b[i - 1] - k) % M
        return a
    return Block("prefix", "vc", False, lines, inv)


def b_condadd(r: HashRNG, L: int, M: int) -> Block:
    """Add one of two numbers, chosen by the already updated number before it."""
    u, v = r.randint(11, M - 11), r.randint(11, M - 11)
    if r.randint(0, 1):
        par = r.randint(0, 1)
        cond, test = f"a[i - 1] % 2 == {par}", (lambda y: y % 2 == par)
    else:
        t = r.randint(M // 4, 3 * M // 4)
        cond, test = f"a[i - 1] > {t}", (lambda y: y > t)
    lines = [f"for i in range(1, {L}):", f"    if {cond}:", f"        a[i] = (a[i] + {u}) % {M}",
             "    else:", f"        a[i] = (a[i] + {v}) % {M}"]

    def inv(b):
        a = list(b)
        for i in range(1, L):
            a[i] = (b[i] - (u if test(b[i - 1]) else v)) % M
        return a
    return Block("condadd", "vc", False, lines, inv)


def b_lookahead(r: HashRNG, L: int, M: int) -> Block:
    """Each number gets a multiple of the (not yet updated) number after it."""
    c = r.randint(1, 9)
    k = r.choice([0, r.randint(1, M - 1)])
    expr = "a[i]" + (" + " + (f"{c} * " if c != 1 else "") + "a[i + 1]") + (f" + {k}" if k else "")
    lines = [f"for i in range({L - 1}):", f"    a[i] = ({expr}) % {M}"]

    def inv(b):
        a = list(b)
        for i in range(L - 2, -1, -1):
            a[i] = (b[i] - c * a[i + 1] - k) % M
        return a
    return Block("lookahead", "vc", False, lines, inv)


def b_map(r: HashRNG, L: int, M: int) -> Block:
    """Every number: multiply, then add a multiple of its position."""
    m, d, e = r.choice(_units(M)), r.randint(1, M - 1), r.randint(0, M - 1)
    minv = pow(m, -1, M)
    tail = f" + {e}" if e else ""
    lines = [f"a = [(x * {m} + i * {d}{tail}) % {M} for i, x in enumerate(a)]"]

    def inv(b):
        return [((y - i * d - e) * minv) % M for i, y in enumerate(b)]
    return Block("map", "vc", False, lines, inv)


def b_pairmix(r: HashRNG, L: int, M: int) -> Block:
    """Mix each neighbouring pair; the second line uses the NEW first number."""
    c, d = r.randint(1, 9), r.randint(1, 9)
    lines = [f"for i in range(0, {L}, 2):", "    p = a[i]", "    q = a[i + 1]",
             f"    a[i] = (p + {c} * q) % {M}", f"    a[i + 1] = (q + {d} * a[i]) % {M}"]

    def inv(b):
        a = list(b)
        for i in range(0, L, 2):
            q = (b[i + 1] - d * b[i]) % M
            a[i], a[i + 1] = (b[i] - c * q) % M, q
        return a
    return Block("pairmix", "vc", False, lines, inv)


def b_prefix2(r: HashRNG, L: int, M: int) -> Block:
    """Each number (from the third on) gets multiples of the TWO already updated numbers before it."""
    c, d = r.randint(1, 9), r.randint(1, 9)
    k = r.choice([0, r.randint(1, M - 1)])
    tail = f" + {k}" if k else ""
    lines = [f"for i in range(2, {L}):", f"    a[i] = (a[i] + {c} * a[i - 1] + {d} * a[i - 2]{tail}) % {M}"]

    def inv(b):
        a = list(b)
        for i in range(2, L):
            a[i] = (b[i] - c * b[i - 1] - d * b[i - 2] - k) % M
        return a
    return Block("prefix2", "vc", False, lines, inv)


def b_condadd3(r: HashRNG, L: int, M: int) -> Block:
    """Add one of three numbers, chosen by two conditions on the two already updated numbers before it."""
    u, v, w = (r.randint(11, M - 11) for _ in range(3))
    par = r.randint(0, 1)
    t1, t2 = r.randint(M // 4, 3 * M // 4), r.randint(M // 4, 3 * M // 4)
    lines = [f"for i in range(2, {L}):",
             f"    if a[i - 1] % 2 == {par} and a[i - 2] > {t1}:", f"        a[i] = (a[i] + {u}) % {M}",
             f"    elif a[i - 1] > {t2}:", f"        a[i] = (a[i] + {v}) % {M}",
             "    else:", f"        a[i] = (a[i] + {w}) % {M}"]

    def inv(b):
        a = list(b)
        for i in range(2, L):
            if b[i - 1] % 2 == par and b[i - 2] > t1:
                add = u
            elif b[i - 1] > t2:
                add = v
            else:
                add = w
            a[i] = (b[i] - add) % M
        return a
    return Block("condadd3", "vc", False, lines, inv)


def _cond(r: HashRNG, idx: int, M: int):
    if r.randint(0, 1):
        par = r.randint(0, 1)
        return f"a[{idx}] % 2 == {par}", (lambda a: a[idx] % 2 == par)
    t = r.randint(M // 4, 3 * M // 4)
    return f"a[{idx}] > {t}", (lambda a: a[idx] > t)


def b_swap(r: HashRNG, L: int, M: int) -> Block:
    """A branch on one number picks which pair of positions to swap."""
    k = r.randint(0, L - 1)
    p, q, s, t = r.shuffled([i for i in range(L) if i != k])[:4]
    cond, test = _cond(r, k, M)
    lines = [f"if {cond}:", f"    a[{p}], a[{q}] = a[{q}], a[{p}]", "else:", f"    a[{s}], a[{t}] = a[{t}], a[{s}]"]

    def inv(b):
        a = list(b)
        x, y = (p, q) if test(a) else (s, t)
        a[x], a[y] = a[y], a[x]
        return a
    return Block("swap", "ro", False, lines, inv)


def b_nested(r: HashRNG, L: int, M: int) -> Block:
    """Two nested branches on two different numbers pick one of four swaps."""
    k, j = r.shuffled(range(L))[:2]
    rest = r.shuffled([i for i in range(L) if i not in (k, j)])[:8]
    cond1, test1 = _cond(r, k, M)
    cond2, test2 = _cond(r, j, M)
    cond3, test3 = _cond(r, j, M)
    pairs = [(rest[0], rest[1]), (rest[2], rest[3]), (rest[4], rest[5]), (rest[6], rest[7])]
    sw = lambda pr: f"a[{pr[0]}], a[{pr[1]}] = a[{pr[1]}], a[{pr[0]}]"
    lines = [f"if {cond1}:",
             f"    if {cond2}:", f"        {sw(pairs[0])}", "    else:", f"        {sw(pairs[1])}",
             "else:",
             f"    if {cond3}:", f"        {sw(pairs[2])}", "    else:", f"        {sw(pairs[3])}"]

    def inv(b):
        a = list(b)
        if test1(a):
            x, y = pairs[0] if test2(a) else pairs[1]
        else:
            x, y = pairs[2] if test3(a) else pairs[3]
        a[x], a[y] = a[y], a[x]
        return a
    return Block("nested", "ro", False, lines, inv)


def b_gather(r: HashRNG, L: int, M: int) -> Block:
    """Rebuild the list by reading positions (m*i + o) mod L."""
    m = r.choice([x for x in range(2, L) if math.gcd(x, L) == 1])
    o = r.randint(1, L - 1)
    lines = [f"a = [a[({m} * i + {o}) % {L}] for i in range({L})]"]
    perm = [(m * i + o) % L for i in range(L)]

    def inv(b):
        a = [0] * L
        for i in range(L):
            a[perm[i]] = b[i]
        return a
    return Block("gather", "ro", False, lines, inv)


def b_countrot(r: HashRNG, L: int, M: int) -> Block:
    """Count the numbers above a threshold, then rotate the list left by that count."""
    t = r.randint(int(M * 0.4), int(M * 0.6))
    lines = ["c = 0", "for x in a:", f"    if x > {t}:", "        c += 1", "a = a[c:] + a[:c]"]

    def inv(b):
        c = sum(1 for x in b if x > t)
        return b[L - c:] + b[:L - c]
    return Block("countrot", "ro", True, lines, inv)


FACTORIES = {f.__name__[2:]: f for f in
             (b_prefix, b_condadd, b_lookahead, b_map, b_pairmix, b_prefix2, b_condadd3, b_swap, b_nested, b_gather, b_countrot)}


# ---------------------------------------------------------------- functions

@dataclass
class Fn:
    name: str
    src: str
    blocks: List[Block]
    f: Callable = field(repr=False, default=None)

    def run(self, a: List[int]) -> List[int]:
        return self.f(a)

    def inv(self, b: List[int]) -> List[int]:
        for blk in reversed(self.blocks):
            b = blk.inv(b)
        return b

    @property
    def kinds(self) -> List[str]:
        return [b.kind for b in self.blocks]


def build_fn(name: str, blocks: List[Block]) -> Fn:
    body = "".join("    " + ln + "\n" for blk in blocks for ln in blk.lines)
    src = f"def {name}(a):\n    a = list(a)\n{body}    return a\n"
    ns: Dict = {}
    exec(src, {}, ns)
    return Fn(name, src, blocks, ns[name])


class View:
    """The shortcut finder only needs .run and .kind; this lets it look at one block kind of a function."""
    def __init__(self, fn: Fn, kind: str):
        self.run, self.kind = fn.run, kind


def _random_list(r: HashRNG, L: int, M: int) -> List[int]:
    return [r.randbelow(M) for _ in range(L)]


def plan_kinds(p: CTParams, i: int) -> List[str]:
    """Which block kinds function number i has. Fixed by position, so every puzzle has the same mix."""
    vc, ro = p.vc_kinds[i % len(p.vc_kinds)], p.ro_kinds[i % len(p.ro_kinds)]
    if p.blocks == 3:
        return [vc, ro, p.vc_kinds[(i + 2) % len(p.vc_kinds)]]
    if p.blocks == 2:
        return [vc, ro]
    return [vc] if i % 2 == 0 else [ro]


def make_functions(rng: HashRNG, p: CTParams) -> List[Fn]:
    L, M = p.length, p.modulus
    if p.blocks >= 2 and L % 2 and "pairmix" in p.vc_kinds:
        raise ValueError("pairmix needs an even list length")
    names = ["f" + c for c in "abcdefghijklmnopqrstuvwxyz"]
    fns: List[Fn] = []
    seen = set()
    for i in range(p.total_steps):
        r = rng.child(f"fn{i}")
        cr = r.child("calib")
        calib = [_random_list(cr, L, M) for _ in range(300)]
        for attempt in range(300):
            blocks = [FACTORIES[k](r, L, M) for k in plan_kinds(p, i)]
            if len(blocks) == 2 and r.randint(0, 1):
                blocks.reverse()
            elif len(blocks) == 3:
                blocks = r.shuffled(blocks)
            fn = build_fn(names[i], blocks)
            if fn.src.split("\n", 1)[1] in seen:
                continue
            ok = True
            for a in calib:
                b = fn.run(a)
                if len(b) != L or not all(0 <= x < M for x in b) or fn.inv(b) != a:
                    raise AssertionError(f"template bug in {fn.src}")
            if sum(1 for a in calib if fn.run(a) == a) > 0.03 * len(calib):
                continue  # changes nothing too often
            if any(all(g.run(fn.run(x)) == x or fn.run(g.run(x)) == x for x in calib[:6]) for g in fns):
                continue  # would undo an earlier function (or be undone by it)
            seen.add(fn.src.split("\n", 1)[1])
            fns.append(fn)
            break
        else:
            raise ValueError(f"could not draw function {i} that meets the guards at these settings")
    return fns


def count_gap_ok(order: Sequence[Fn]) -> bool:
    """Between any two count-driven blocks there must be a value-changing block."""
    since_vc = True
    for fn in order:
        for blk in fn.blocks:
            if blk.cls == "vc":
                since_vc = True
            elif blk.count_driven:
                if not since_vc:
                    return False
                since_vc = False
    return True


def make_order(rng: HashRNG, fns: List[Fn], p: CTParams, tries: int = 3000) -> List[Fn]:
    pr = rng.child("probe")
    probes = [_random_list(pr, p.length, p.modulus) for _ in range(8)]
    vc_kinds, ro_kinds = list(p.vc_kinds), list(p.ro_kinds)
    for _ in range(tries):
        order = rng.shuffled(fns)
        if not count_gap_ok(order):
            continue
        vc_view = [View(f, next((b.kind for b in f.blocks if b.cls == "vc"), "-")) for f in order]
        ro_view = [View(f, next((b.kind for b in f.blocks if b.cls == "ro"), "-")) for f in order]
        if find_shortcut(vc_view, probes, kinds=vc_kinds) is None and find_shortcut(ro_view, probes, kinds=ro_kinds) is None:
            return order
    raise ValueError("no function order without shortcuts found at these settings")


# ---------------------------------------------------------------- puzzle

@dataclass
class CTChain:
    start: List[int]
    names: List[str]
    states: List[List[int]]          # the list after each function

    @property
    def end(self) -> List[int]:
        return self.states[-1]


@dataclass
class CTPuzzle:
    id: str
    seed: str
    width: int
    depth: int
    params: CTParams
    version: str
    functions: List[Tuple[str, str, List[str]]]   # (name, source, block kinds)
    chains: List[CTChain]
    prompt: str
    answer: List[List[int]]
    style: str = "legacy"           # "legacy" (the free-test wording), "d31" or "d31-answer-only" (spec item 4)

    def to_dict(self) -> Dict:
        d = asdict(self)
        if self.style == "legacy":
            d.pop("style")          # keeps the free-test records byte-identical
        return d

    @property
    def answer_line(self) -> str:
        return "Answer: " + ", ".join(f"{i} = {fmt(a)}" for i, a in enumerate(self.answer, 1))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


def fmt(lst: Sequence[int]) -> str:
    return "[" + ", ".join(str(x) for x in lst) + "]"


def render_prompt(fns: List[Fn], chains: List[CTChain], p: CTParams, example: List[int],
                  style: str = "legacy", depth: int = 0) -> str:
    L, M = p.length, p.modulus
    out = [f"Every value here is a list of {L} whole numbers, each from 0 to {M - 1}, such as {fmt(example)}. "
           f"Each function below takes such a list and returns a new list. Read each function as ordinary Python.",
           ""]
    used = {n for c in chains for n in c.names}
    out += [f.src for f in fns if f.name in used]
    out.append("Sequences")
    for i, c in enumerate(chains, 1):
        out.append(f"{i}. Start at {fmt(c.start)}. Apply {', '.join(c.names)}.")
    out.append("")
    if style in ("d31", "d31-answer-only"):
        from .prompt_d31 import closing
        out.append(closing("code", len(chains), depth, answer_only=(style == "d31-answer-only")))
        return "\n".join(out)
    if style != "legacy":
        raise ValueError(f"unknown prompt style {style!r}")
    if len(chains) == 1:
        out.append("Apply the functions in the order listed, each to the list the one before returned. "
                   "Show a short worked solution: write the list after each function, one line per function, "
                   "like `1. fa: [...]`. Then end your reply with the line `Final 1: [...]`, giving the list "
                   "the sequence ends at.")
    else:
        out.append("Apply each sequence's functions in the order listed. Each sequence is separate. "
                   "Show a short worked solution: for each sequence, write the list after each function, "
                   "one line per function, like `1. fa: [...]`. Then end your reply with one line per sequence "
                   "of the form `Final 1: [...]`, giving the list each sequence ends at.")
    return "\n".join(out)


def generate(seed: object, width: int, depth: int, params: CTParams = SETTINGS["c1"], item_id: str = "",
             style: str = "legacy") -> CTPuzzle:
    params.validate()
    if width * depth != params.total_steps:
        raise ValueError(f"{width} x {depth} != {params.total_steps}")
    root = HashRNG(seed)
    fns = make_functions(root.child("functions"), params)
    order = make_order(root.child("order"), fns, params)
    srng = root.child(f"starts/{width}x{depth}")
    chains = []
    for c in range(width):
        names = [f.name for f in order[c * depth:(c + 1) * depth]]
        start = _random_list(srng, params.length, params.modulus)
        v, states = start, []
        for f in order[c * depth:(c + 1) * depth]:
            v = f.run(v)
            states.append(v)
        chains.append(CTChain(start, names, states))
    example = _random_list(root.child("example"), params.length, params.modulus)
    return CTPuzzle(
        id=item_id or f"{seed}-{width}x{depth}", seed=str(seed), width=width, depth=depth, params=params,
        version=CT_VERSION,
        functions=[(f.name, f.src, f.kinds) for f in fns],
        chains=chains,
        prompt=render_prompt(fns, chains, params, example, style, depth),
        answer=[c.end for c in chains],
        style=style,
    )


def reference_reply(p: CTPuzzle) -> str:
    """A perfect reply in the D-31 format (step lines when sequences have more than one function, then the answer)."""
    lines = []
    if p.depth > 1:
        for s_i, ch in enumerate(p.chains, 1):
            lines += [f"{s_i}.{k} = {fmt(st)}" for k, st in enumerate(ch.states, 1)]
    return "\n".join(lines + [p.answer_line])


def grade_d31(reply: str, p: CTPuzzle) -> Dict:
    """Whole-answer and per-piece grading of a D-31 reply, and the first wrong step of each sequence."""
    from .prompt_d31 import first_wrong_step, numbering_problems, parse_steps, score_answer
    res = score_answer(reply, [tuple(a) for a in p.answer])
    res["numbering_problems"] = numbering_problems(reply, p.width, p.depth)
    res["first_wrong_step"] = [first_wrong_step(reply, [tuple(s) for s in ch.states], i, p.width)
                               for i, ch in enumerate(p.chains, 1)] if p.depth > 1 else None
    res["steps_shown"] = len(parse_steps(reply))
    return res


def step_call(p: CTPuzzle, sequence: int, k: int) -> Tuple[str, List[int]]:
    """The E3 prompt for step k (1-based) of a sequence, and the true new list. The script feeds its own voted
    result forward in the real run; here the input is the true previous state."""
    from .prompt_d31 import step_call_prompt
    ch = p.chains[sequence - 1]
    src = {n: s for n, s, _ in p.functions}[ch.names[k - 1]]
    before = ch.start if k == 1 else ch.states[k - 2]
    return step_call_prompt("code", p.params.length, src, fmt(before)), ch.states[k - 1]


# ---------------------------------------------------------------- grading (also used by the free test)

FINAL_RE = re.compile(r"Final\s*(\d+)\s*:\s*\[([^\]]*)\]")
STEP_RE = re.compile(r"^\s*(?:\d+\.\s*)?(f[a-z])\s*:\s*\[([^\]]*)\]", re.M)


def _ints(text: str) -> Optional[List[int]]:
    try:
        return [int(x) for x in re.findall(r"-?\d+", text)]
    except ValueError:
        return None


def grade(reply: str, p) -> Dict:
    """Fully-right and per-piece grading from a reply, plus the first wrong step if the working is shown.

    `p` is a CTPuzzle or a dict from `to_dict()`.
    """
    d = p.to_dict() if hasattr(p, "to_dict") else p
    answer, chains = d["answer"], d["chains"]
    finals = {}
    for m in FINAL_RE.finditer(reply):
        finals[int(m.group(1))] = _ints(m.group(2))     # a later line for the same number wins
    per_piece = [finals.get(i + 1) == answer[i] for i in range(len(answer))]
    # working: lines like "fa: [..]"; for a chain they come in order, for separate pieces by function name
    steps = [(m.group(1), _ints(m.group(2))) for m in STEP_RE.finditer(reply)]
    first_wrong = None
    if len(chains) == 1 and steps:
        key = list(zip(chains[0]["names"], chains[0]["states"]))
        for k, (nm, st) in enumerate(steps[:len(key)]):
            if nm != key[k][0] or st != key[k][1]:
                first_wrong = k + 1
                break
    wrong_steps = None
    if len(chains) > 1 and steps:
        keyed = {c["names"][0]: c["states"][0] for c in chains}
        got = {}
        for nm, st in steps:
            got[nm] = st
        wrong_steps = sorted(nm for nm, st in keyed.items() if nm in got and got[nm] != st)
    return {"parsed": bool(finals), "pieces": len(answer), "pieces_right": sum(per_piece),
            "fully_right": all(per_piece), "per_piece": per_piece,
            "first_wrong_step": first_wrong, "wrong_functions": wrong_steps}
