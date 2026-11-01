"""The main body's new table (D-159, D-160; Vision's plan, paper/notes/d159-cut-and-keep-plan.md §0c at 426d22a): Table 1, the settings
at a glance (output TAB-35). Every number is read from a pinned source; the settings' names are the house names (paper_out_names).

Columns (§0c): study, setting (model and effort), samples per puzzle, puzzles (each in two shapes), steps, role. Roles are the paper's
tiers in short words: "test" (a pre-registered confirmatory test uses it), "description" (pre-specified, no test) and "exploratory".
Rows group what the text discusses together (§0c: about 10-12 rows; the effort sweeps grouped; the top-up's designs one block).
Cross-references are written as ⟦TAB-xx⟧ placeholders, which Vision's converter resolves (D-159 H3); the CSV and cells file keep them.

The paper prints a shorter version (TAB-35.main; Vision's height target of about 2.5-3 in): each setting with its samples as
"Haiku-medium ×40", the role as one word with the test names in a short parenthesis, and the reworded-prompt check (a robustness
check the body does not discuss) left to the full table in the supplement. Study 1b's two effort-sweep rows stay two rows: the Haiku
sweep ran at 16 and 6 steps on 80 and 40 puzzles, Sonnet and Opus at 6 steps only, which one row could not say.
"""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

from .paper_out_core import NBSP, Cell, Meta, Store, Table, derive, integer, joined, label, num_d, output
from . import paper_out_core as core
from .paper_out_names import EFFORT_ORDER, STUDY1_ARMS, STUDY1_TESTS, STUDY1B_TAGS, TIMES
from .paper_out_ops import extract
from .paper_out_study1b import print_rules

DASH = label("—")
L = label
MAIN_PLAN = "main_plan"


def R(S: Store, src: str, *segs: Any):
    return S.ref(src, core.join_key(*segs))


def G(S: Store, src: str, *segs: Any) -> Any:
    return S.get(src, core.join_key(*segs))


def _setup_index(S: Store, name: str) -> int:
    for i, s in enumerate(G(S, MAIN_PLAN, "setups")):
        if s["name"] == name:
            return i
    raise ValueError(f"the main run's plan has no setup {name!r}")


def _s1_samples(S: Store, name: str) -> Cell:
    return integer(R(S, MAIN_PLAN, "setups", _setup_index(S, name), "per_puzzle"))


def _check_s1(S: Store, name: str, arm: str) -> None:
    """The plan's setup is the named arm (model and effort), so the row's name and its numbers describe the same setting."""
    s = G(S, MAIN_PLAN, "setups")[_setup_index(S, name)]
    _, family, effort = STUDY1_ARMS[arm]
    want_effort = "medium" if effort == "off" else effort
    if not str(s["model"]).startswith(f"claude-{family}") or s["effort"] != want_effort or bool(s.get("thinking_off")) != (effort == "off"):
        raise ValueError(f"main plan setup {name}: {s['model']} {s['effort']} is not {arm}")


def _bases(S: Store, src: str, *segs: Any) -> Cell:
    """A puzzles-per-shape count from a stamped count of puzzles over both shapes (each base puzzle is sent in both shapes)."""
    return num_d(derive("puzzles over both shapes / 2", lambda n: n / 2, R(S, src, *segs)), dp=0)


def _s1b(S: Store, tag: str, n: int, key: str) -> Any:
    return R(S, "s1b", "descriptive", "arms", f"{tag}@{n}", key)


def _list(cells: Sequence[Cell], sep: str = ";", tie: bool = False) -> Cell:
    """Several cells printed as one ("10; 1; 1", "4, 6, 8"), each keeping its source. A separator of letters ("and") gets spaces. With
    `tie`, the spaces are no-break spaces, so a narrow number column keeps the list on one line (the paper's Steps)."""
    if len(cells) == 1:
        return cells[0]
    if tie:
        if sep.strip().isalpha():
            return joined(*[x for i, c in enumerate(cells) for x in (([L(sep.strip())] if i else []) + [c])], sep="\u00a0")
        return joined(*[joined(c, L(sep), sep="") for c in cells[:-1]], cells[-1], sep="\u00a0")
    if sep.strip().isalpha():
        out: List[Cell] = []
        for i, c in enumerate(cells):
            out += ([L(sep.strip())] if i else []) + [c]
        return joined(*out, sep=" ")
    return joined(*[joined(c, L(sep), sep="") for c in cells[:-1]], cells[-1], sep=" ")


def _and(items: Sequence[str]) -> str:
    """Names in a list the way a sentence reads: "low, medium, high and xhigh" (the last two joined by "and")."""
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


def _times(pairs: Sequence[Tuple[str, Cell]]) -> Cell:
    """Settings with their samples per puzzle, "Haiku-medium ×10; Opus-medium, Sonnet-medium ×1": neighbours with the same count share
    one "×n" (only when no name holds a comma, so "Haiku, thinking off" always carries its own)."""
    groups: List[Tuple[List[str], Cell]] = []
    for name, n in pairs:
        if groups and groups[-1][1].raw == n.raw and "," not in name and all("," not in x for x in groups[-1][0]):
            groups[-1][0].append(name)
        else:
            groups.append(([name], n))
    return _list([joined(L(", ".join(names) + " " + TIMES), n, sep="") for names, n in groups])


def _tests_of(arms: Sequence[str]) -> str:
    """The Study 1 tests that use any of these arms, as challenger or comparator (paper_out_names.STUDY1_TESTS): "Test 4", "Tests 1–3"."""
    nums = sorted(int(name.split()[1]) for name, ch, cmp_, _, _ in STUDY1_TESTS.values() if ch in arms or cmp_ in arms)
    if not nums:
        raise ValueError(f"TAB-35: no Study 1 test uses {list(arms)}")
    if len(nums) == 1:
        return f"Test {nums[0]}"
    if nums == list(range(nums[0], nums[-1] + 1)):
        return f"Tests {nums[0]}–{nums[-1]}"
    return "Tests " + ", ".join(map(str, nums))


def _efforts(tags: Sequence[str]) -> str:
    """A model's efforts in house order as runs, "low–max" or "low, high–max" (the tags are one model's, checked)."""
    models = {STUDY1B_TAGS[t][1] for t in tags}
    if len(models) != 1:
        raise ValueError(f"TAB-35: one model's efforts expected, got {sorted(models)}")
    idx = sorted(EFFORT_ORDER.index(STUDY1B_TAGS[t][2]) for t in tags)
    runs: List[List[int]] = []
    for i in idx:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return ", ".join(EFFORT_ORDER[r[0]] if len(r) == 1 else f"{EFFORT_ORDER[r[0]]}–{EFFORT_ORDER[r[-1]]}" for r in runs)


def _setting_runs(tags: Sequence[str]) -> str:
    """The paper's names for a model's effort settings, in house order, as runs of whole setting names (Edith, proof 2: the
    "Sonnet-low" pattern, never "Sonnet low–max"): "Sonnet-low to Sonnet-max", "Opus-low, Opus-high to Opus-max", "Haiku, thinking off
    to Haiku-xhigh". The tags are one model's (checked); the names are the house names (paper_out_names.STUDY1B_TAGS)."""
    _efforts(tags)                                                    # the one-model check
    by_effort = {EFFORT_ORDER.index(STUDY1B_TAGS[t][2]): STUDY1B_TAGS[t][0] for t in tags}
    runs: List[List[int]] = []
    for i in sorted(by_effort):
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return ", ".join(by_effort[r[0]] if len(r) == 1 else f"{by_effort[r[0]]} to {by_effort[r[-1]]}" for r in runs)


def _same(S: Store, refs: Sequence[Any], what: str) -> Any:
    vals = {r.value for r in refs}
    if len(vals) != 1:
        raise ValueError(f"TAB-35: {what} differs across the settings it groups ({sorted(map(str, vals))})")
    return refs[0]


@output("TAB-35")
def tab_35(S: Store) -> Table:
    cols = ["Study", "Setting (model, effort)", "Samples per puzzle", "Puzzles", "Steps", "Role"]
    rows: List[List[Cell]] = []
    paper: List[List[Cell]] = []          # the paper's version: Study, setting ×samples, puzzles, steps, role (no reworded-prompt row)

    def sample(tag: str, n: int) -> Cell:
        return integer(_s1b(S, tag, n, "tries_per_item"))

    # ---- the length sweep (lock 2's ladder): Haiku-medium x10, Opus-medium and Sonnet-medium x1, the same 20 bases at each length
    curve = "curve_d90"
    lens = sorted(G(S, curve, "models", "hm", "by_n"), key=int)
    for m in ("hm", "om", "sm"):
        for n in lens:
            _same(S, [R(S, curve, "models", "hm", "by_n", lens[0], "n_base"), R(S, curve, "models", m, "by_n", n, "n_base")], "the sweep's bases")
    sweep_n = {m: integer(R(S, curve, "models", m, "tries_per_puzzle")) for m in ("hm", "om", "sm")}
    sweep_bases = integer(R(S, curve, "models", "hm", "by_n", lens[0], "n_base"))
    sweep_steps = _list([_steps(S, curve, n) for n in lens], sep=",")
    rows.append([L("Length sweep"), L("Haiku-medium; Opus-medium; Sonnet-medium"), _list(list(sweep_n.values()), tie=True), sweep_bases,
                 sweep_steps, L("description (chose the length)")])
    paper.append([L("Length sweep"), _times([(STUDY1B_TAGS[m][0], sweep_n[m]) for m in ("hm", "om", "sm")]), sweep_bases,
                  sweep_steps, L("description")])

    # ---- Study 1, the main run: 6 steps, 80 bases
    s1_bases = _bases(S, MAIN_PLAN, "puzzles")
    s1_steps = integer(R(S, MAIN_PLAN, "steps"))
    for name, arm in (("hm", "haiku-med"), ("om", "opus-med"), ("sm", "sonnet-med"), ("ol", "opus-low"), ("hl", "haiku-low"),
                      ("ho", "haiku-thinking-off"), ("hx", "haiku-max"), ("sl", "sonnet-low"), ("hv", "haiku-med")):
        _check_s1(S, name, arm)
    rows.append([L("Study 1"), L("Haiku-medium"), _s1_samples(S, "hm"), s1_bases, s1_steps, L("test (Tests 1–3, as votes)")])
    paper.append([L("Study 1"), _times([("Haiku-medium", _s1_samples(S, "hm"))]), s1_bases, s1_steps, L(f"test ({_tests_of(['haiku-med'])})")])
    _same(S, [R(S, MAIN_PLAN, "setups", _setup_index(S, x), "per_puzzle") for x in ("om", "sm", "ol")], "Study 1's single-sample arms")
    rows.append([L("Study 1"), L("Opus-medium; Sonnet-medium; Opus-low"), joined(_s1_samples(S, "om"), L("each")), s1_bases, s1_steps,
                 L("test (the comparators; Test 5)")])
    paper.append([L("Study 1"), _times([(STUDY1_ARMS[a][0], _s1_samples(S, x)) for x, a in (("om", "opus-med"), ("sm", "sonnet-med"),
                                                                                       ("ol", "opus-low"))]),
                  s1_bases, s1_steps, L(f"test ({_tests_of(['opus-med', 'sonnet-med', 'opus-low'])})")])
    cap = integer(R(S, MAIN_PLAN, "e3", "cap"))
    rows.append([L("Study 1"), L("Step voting: Haiku-medium, one step a call"), joined(L("up to"), cap, L("per" + NBSP + "step")), s1_bases, s1_steps,
                 L("test (Test 4)")])
    paper.append([L("Study 1"), joined(L("Haiku-medium step voting, up to"), cap, L("per step")), s1_bases, s1_steps,
                  L(f"test ({_tests_of(['e3'])})")])
    rows.append([L("Study 1"), L("Haiku-low; Haiku, thinking off; Haiku-max; Sonnet-low"),
                 _list([_s1_samples(S, x) for x in ("hl", "ho", "hx", "sl")], tie=True), s1_bases, s1_steps, L("exploratory")])
    paper.append([L("Study 1"), _times([(STUDY1_ARMS[a][0], _s1_samples(S, x)) for x, a in (("hl", "haiku-low"), ("ho", "haiku-thinking-off"),
                                                                                       ("hx", "haiku-max"), ("sl", "sonnet-low"))]),
                  s1_bases, s1_steps, L("exploratory")])
    rows.append([L("Study 1"), L("Haiku-medium, reworded prompt"), _s1_samples(S, "hv"),
                 _bases(S, "main", "reporting", "d42_robustness", "n_puzzles"), s1_steps, L("description (wording check)")])

    # ---- Study 1b: tests at 16 and 6 steps, the effort sweep, the 12-step point
    for n, role in ((16, "test (Tests B1, B2)"), (6, "test (Test B3)")):
        bases = integer(R(S, "s1b", "descriptive", "arms", f"hx@{n}", "pooled", "n_base"))
        rows.append([L("Study 1b"), L("Haiku-max; Opus-medium"), _list([sample("hx", n), sample("om", n)], tie=True), bases,
                     integer(_s1b(S, "hx", n, "N")), L(role)])
        paper.append([L("Study 1b"), _times([("Haiku-max", sample("hx", n)), ("Opus-medium", sample("om", n))]), bases,
                      integer(_s1b(S, "hx", n, "N")), L(role)])
    sweep = ("ho", "hl", "hm", "hh", "hxh")
    tries = [_s1b(S, t, n, "tries_per_item") for t in sweep for n in (16, 6)]
    sweep_bases2 = _list([integer(R(S, "s1b", "descriptive", "arms", f"hm@{n}", "pooled", "n_base")) for n in (16, 6)], sep="and", tie=True)
    sweep_steps2 = _list([integer(_s1b(S, "hm", n, "N")) for n in (16, 6)], sep="and", tie=True)
    # the one name for the setting is "Haiku, thinking off" (Edith, proof 4: never "with thinking off"); a list of whole items takes
    # semicolons between them and "and" before the last of a run of efforts
    rows.append([L("Study 1b"), L("Haiku, thinking off; Haiku at " + _and([STUDY1B_TAGS[t][2] for t in sweep[1:]]) + " effort"),
                 joined(integer(_same(S, tries, "the effort sweep's samples")), L("each"), sep=NBSP), sweep_bases2, sweep_steps2, L("description")])
    paper.append([L("Study 1b"), joined(L(_setting_runs(sweep) + " " + TIMES), integer(_same(S, tries, "the effort sweep's samples")),
                                        sep=""), _list([integer(R(S, "s1b", "descriptive", "arms", f"hm@{n}", "pooled", "n_base")) for n in (16, 6)],
                                                       sep="and", tie=True),
                  _list([integer(_s1b(S, "hm", n, "N")) for n in (16, 6)], sep="and", tie=True), L("description")])
    others = ("sl", "sm", "sh", "sxh", "sx", "ol", "oh", "oxh", "ox")
    one = integer(_same(S, [_s1b(S, t, 6, "tries_per_item") for t in others], "the 6-step models' samples"))
    rows.append([L("Study 1b"), L("Sonnet at " + _and([STUDY1B_TAGS[t][2] for t in others[:5]]) + " effort; Opus at "
                                  + _and([STUDY1B_TAGS[t][2] for t in others[5:]]) + " effort"),
                 joined(one, L("each"), sep=NBSP), integer(R(S, "s1b", "descriptive", "arms", "sm@6", "pooled", "n_base")), integer(_s1b(S, "sm", 6, "N")),
                 L("description")])
    paper.append([L("Study 1b"), joined(L(f"{_setting_runs(others[:5])}; {_setting_runs(others[5:])} {TIMES}"), one, sep=""),
                  integer(R(S, "s1b", "descriptive", "arms", "sm@6", "pooled", "n_base")), integer(_s1b(S, "sm", 6, "N")), L("description")])
    twelve = [L("Study 1b"), L("Haiku-max; Opus-medium"), _list([sample("hx", 12), sample("om", 12)], tie=True),
              integer(R(S, "s1b", "descriptive", "arms", "hx@12", "pooled", "n_base")), integer(_s1b(S, "hx", 12, "N"))]
    rows.append(twelve + [L("description (the 12-step point)")])
    paper.append([twelve[0], _times([("Haiku-max", sample("hx", 12)), ("Opus-medium", sample("om", 12))]), *twelve[3:], L("description")])

    # ---- the top-up run: the team, the picker, step voting on pieces and the drift check, one block
    # the drift check ran on its own, smaller set of puzzles (Edith's PR #33 review): the row says so beside the designs' count
    # only 'check: 20)' is tied: tying '(drift check: 20)' whole widens the Puzzles column, narrows Setting and Role, grows the float
    # 5.40 -> 5.86 in and strands 'B2)' and 'effort' on lines of their own (measured, proof 4 group 1 SHOULD fix)
    topup_bases = joined(integer(R(S, "topup", "accuracy", "e2", "pooled", "n_base")),
                         joined(L("(drift check:"), joined(integer(R(S, "topup", "same_model_check", "bases")), L(")"), sep=""), sep=NBSP))
    rows.append([L("Top-up"), L("Haiku-medium designs: a team, a picker, step voting on pieces; and the drift check between runs"),
                 L("see ⟦TAB-14⟧"), topup_bases, s1_steps, L("exploratory")])
    paper.append([L("Top-up"), joined(L("Haiku-medium team, picker and step voting on pieces (see ⟦TAB-14⟧); the drift check ("),
                                      integer(R(S, "topup", "same_model_check", "bases")), L(" puzzles)"), sep=""),
                  integer(R(S, "topup", "accuracy", "e2", "pooled", "n_base")), s1_steps, L("exploratory")])

    # the role definitions stay here, in the note: Edith's row for Vision deletes the caption's second sentence, which repeats them
    # (proof 4, p. 15: one place for the definitions)
    notes = [[L("Each puzzle is sent in two shapes, one chain and separate pieces; samples are per puzzle and shape. Role: test, a "
                "pre-registered confirmatory test uses the setting; description, pre-specified with no test; exploratory, neither.")]]
    caption = {"tier": [L("design summary (no results)")], "study": [L("the length sweep, Study 1, Study 1b and the top-up run")]}
    t = Table([L(c) for c in cols], rows, notes, caption, short_notes=[0], layout="float")
    t.groups = [i for i in range(1, len(rows)) if rows[i][0].printed != rows[i - 1][0].printed]     # a space above each study's first row
    paper_notes = [[L(f"Puzzles are sent in two shapes (chain and pieces); {TIMES}n: samples per puzzle and shape. Role: test, used by a "
                      "pre-registered confirmatory test; description, pre-specified, no test; exploratory, neither.")]]
    t.main_table = print_rules(Table([L(c) for c in ("Study", f"Setting {TIMES} samples per puzzle", "Puzzles", "Steps", "Role")], paper,
                                     paper_notes, caption, short_notes=[0], layout="float"))
    # Edith §7.7 (proof 2): four groups (Length sweep, Study 1, Study 1b, Top-up), the study printed once per group
    mt = t.main_table
    mt.groups = [i for i in range(1, len(paper)) if paper[i][0].printed != paper[i - 1][0].printed]
    mt.once = [0]
    # no space after every row: Edith's p. 5 called it optional, and the body is at its 12-page limit (Vision); the group breaks and
    # the study printed once per group keep a wrapped row from reading as two
    return print_rules(t)


def _steps(S: Store, curve: str, n: str) -> Cell:
    """The sweep's length at by_n key n, cut from the preset its set was frozen at (l14n<steps>), and checked equal to the key."""
    c = extract(R(S, curve, "models", "hm", "by_n", n, "preset"), r"^l14n(\d+)$")
    if str(c.raw) != str(n):
        raise ValueError(f"the sweep's length {n} is not its preset's {c.raw!r}")
    return c
