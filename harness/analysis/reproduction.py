"""Reproduction details for the paper (mock-review fix #11): every kind of prompt the runs sent, rendered by the run code itself on
the paper's illustrative puzzle; the request settings of every arm, as the runners build them; the pinned price table; and where the
replies are parsed. No model call, no money.

    python3 -m harness.analysis.reproduction --tasks data/tasks --out data/paper-outputs/reproduction

The puzzle is the illustrative one (D-141; data/paper-outputs/illustration, made fresh and never from any test set): its committed
illustration.json is read, checked against its SHA256SUMS, rebuilt from its seed (illustration.build) and re-proved disjoint from every
set under --tasks (illustration.disjointness, counts only). Every prompt is made by the function the run used, never retyped:
- the two shapes' prompts are the illustration's own (not copied here);
- the rewording check's variant: d42.variant_prompt (Study 1, arm hv);
- step voting: e3.chain_steps and e3.step_item (Study 1's Test 4, one prompt per chain step) and topup.c13_steps (the top-up's C13,
  one prompt per piece);
- the team: topup.planner_item, helper_item, aggregator_item and picker_item (the top-up's E2 and H-pick8; the wording is
  research/models/team_prompts.py, loaded only if its SHA-256 is the approved one, D-100).
Inputs a team prompt needs that only a model could supply are shown as labelled placeholders, never as a model's reply: the planner's
instruction in the helper prompt and the eight replies in the picker prompt. The aggregator is shown with the helper results a correct
helper returns (each step's true balances from ledger.step_call, the function that marks the step calls). No rendered text may equal a
file of research/team-prompts/, which renders a test item.

Arm settings: the length sweep's from ladder.build_ladder_requests (the illustrative puzzle is at the ladder's l14n4 preset, so the
sweep's own builder runs on it; Edith's RP-1); Study 1's from main.MAIN_SETUPS and main.D42_SETUP; Study 1b's from data/plans/study1b-plan.json (an arm calibrated by
the section 7 rule takes the limit the run recorded, read from data/main/study1b-1/analysis.json plan_as_run.limits); the top-up's
from data/plans/topup-plan.json and the e3 constants its team and step calls use. Each request is built by main._item (Study 1, Study
1b, the same-model check) or the top-up's and e3's own builders, so model, effort, thinking and max_tokens are exactly what was sent;
the prompt is replaced by a pointer to the file that holds it. The output is deterministic: no time, no commit, no path outside the repo.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..pareto import d42, e3, ladder, main, prices, slim, topup
from ..pareto.request import assert_clean
from ..taskgen import illustration, ledger

ROOT = Path(__file__).resolve().parents[2]
ILLUSTRATION = ROOT / "data" / "paper-outputs" / "illustration"
STUDY1B_PLAN = "data/plans/study1b-plan.json"
STUDY1B_ANALYSIS = "data/main/study1b-1/analysis.json"
TOPUP_PLAN = "data/plans/topup-plan.json"
TEAM_RENDERS = ROOT / "research" / "team-prompts"
LABEL = illustration.LABEL
PLANNER_PLACEHOLDER = "[placeholder: the planner's instruction for task {k}, as the planner wrote it]"
PICKER_PLACEHOLDER = "[placeholder: Haiku-medium sample {i}'s reply to this puzzle, as the run sent it]"
PROMPT_POINTER = "<the prompt in {file}>"

# Where the replies are read: (file, function or constant, what it does). Docstrings and patterns are read from the code.
PARSERS = (
    ("harness/analysis/trace_parse.py", "parse_trace", "a chain reply's step lines and Answer line"),
    ("harness/analysis/trace_parse.py", "parse_pieces", "a pieces reply's per-sequence Answer lines"),
    ("harness/analysis/trace_parse.py", "parse_final", "a reply's last Answer line as a state"),
    ("harness/analysis/trace_parse.py", "_STEP", "the step-line pattern"),
    ("harness/analysis/trace_parse.py", "_ANSWER", "the Answer-line pattern"),
    ("harness/analysis/trace_parse.py", "REPEATS_IDENTICAL", "the official repeated-line rule (Deviation 2)"),
    ("harness/analysis/scoring.py", "vote_key", "what one try votes for"),
    ("harness/analysis/scoring.py", "row_correct", "whether one try is right"),
    ("harness/pareto/e3.py", "parse_step_answer", "what one step call votes for (step voting)"),
    ("research/models/team_prompts.py", "parse_plan", "the planner's tasks"),
    ("research/models/team_prompts.py", "TASK", "the task-label pattern"),
    ("research/models/team_prompts.py", "parse_pick", "the picker's choice"),
    ("research/models/team_prompts.py", "PICK", "the Pick-line pattern"),
)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- the puzzle

def load_puzzle(tasks: Path) -> Tuple[Dict, Dict, Dict, Dict[str, object]]:
    """(manifest-like dict, chain item, pieces item, disjointness counts) from the committed illustration, checked three ways."""
    sums = dict(reversed(line.split("  ", 1)) for line in (ILLUSTRATION / "SHA256SUMS").read_text().splitlines() if line)
    if file_sha(ILLUSTRATION / "illustration.json") != sums.get("illustration.json"):
        raise ValueError("illustration.json differs from its SHA256SUMS")
    doc = json.loads((ILLUSTRATION / "illustration.json").read_text())
    chain, pieces = doc["puzzles"]["chain"], doc["puzzles"]["pieces"]
    rebuilt = json.loads(json.dumps(sorted(illustration.build(), key=lambda it: int(it["width"])), sort_keys=True))
    if rebuilt != [chain, pieces]:
        raise ValueError("the illustrative puzzle no longer rebuilds from its seed")
    dj = illustration.disjointness(tasks, [chain, pieces])
    if dj != doc["disjointness"]:
        raise ValueError("the disjointness counts differ from the illustration's")
    man = {"set_id": doc["set_id"], "family": "ledger", "setting": doc["setting"]}
    return man, chain, pieces, dj


def step_truths(it: Mapping[str, object]) -> List[List[int]]:
    """Each task's true result, from ledger.step_call (the function that marks the step calls): a chain's balances after each rule, or
    each sequence's balances after its rule."""
    from .curve import _puzzle
    p = _puzzle(it)
    if int(it["width"]) == 1:
        return [list(ledger.step_call(p, 1, k)[1]) for k in range(1, int(it["depth"]) + 1)]
    return [list(ledger.step_call(p, s, 1)[1]) for s in range(1, int(it["width"]) + 1)]


def task_starts(it: Mapping[str, object]) -> List[List[int]]:
    """The balances each helper task starts from: a chain's start, then each rule's true result; each sequence's own start."""
    chains = it["chains"]                                                                          # type: ignore[index]
    if int(it["width"]) == 1:                                                                      # type: ignore[call-overload]
        return [list(chains[0]["start"])] + step_truths(it)[:-1]
    return [list(c["start"]) for c in chains]


# ---------------------------------------------------------------- the prompts

def _strip(params: Mapping[str, object], file: str) -> Dict[str, object]:
    """The request as built, with the prompt replaced by a pointer to its file (checked to be the one message)."""
    assert_clean(dict(params))                                                                    # type: ignore[arg-type]
    msgs = params["messages"]
    if len(msgs) != 1 or msgs[0]["role"] != "user":                                              # type: ignore[index, arg-type]
        raise ValueError("a request is not one user message")
    return {**{k: v for k, v in params.items() if k != "messages"},
            "messages": [{"role": "user", "content": PROMPT_POINTER.format(file=file)}]}


def render(man: Dict, chain: Dict, pieces: Dict) -> Tuple[Dict[str, str], List[Dict[str, object]]]:
    """({file name: text}, [one record per prompt file: file, kind, run, arm tag, request with the prompt as a pointer])."""
    files: Dict[str, str] = {}
    recs: List[Dict[str, object]] = []

    def put(name: str, text: str, kind: str, run: str, item: Tuple[str, Mapping[str, object], Mapping[str, object]],
            note: Optional[str] = None) -> None:
        cid, params, meta = item
        if params["messages"][0]["content"] != text:                                            # type: ignore[index]
            raise ValueError(f"{name}: the request does not carry the rendered prompt")
        files[name] = text
        rec: Dict[str, object] = {"file": name, "sha256": sha(text), "kind": kind, "run": run, "setup": meta["setup"],
                                  "request": _strip(params, name)}
        if note:
            rec["note"] = note
        recs.append(rec)

    for shape, it in (("chain", chain), ("pieces", pieces)):
        put(f"{shape}-reworded-prompt.txt", d42.variant_prompt(it), "the rewording check's variant wording", "Study 1 main run",
            main._item(man, dict(it, prompt=d42.variant_prompt(it)), main.D42_SETUP, main.D42_SETUP.name, 1))
    for st in e3.chain_steps([(man, [chain])]):
        put(f"chain-step-{st.k}-prompt.txt", st.prompt, "step voting, one chain step (Test 4)", "Study 1 main run", e3.step_item(st, 1))
    for st in topup.c13_steps(man, [pieces]):
        put(f"pieces-step-{st.k}-prompt.txt", st.prompt, "step voting, one piece (C13)", "top-up run", e3.step_item(st, 1))
    for shape, it in (("chain", chain), ("pieces", pieces)):
        put(f"{shape}-planner-prompt.txt", topup.team_prompts().planner_prompt(it), "team planner (E2)", "top-up run",
            topup.planner_item(man, it))
        start = task_starts(it)[0]
        task = PLANNER_PLACEHOLDER.format(k=1)
        put(f"{shape}-helper-prompt.txt", topup.team_prompts().helper_prompt(task, start), "team helper (E2), task 1", "top-up run",
            topup.helper_item(man, it, 1, 1, task, start),
            note="The planner's instruction is a placeholder: in the run it was the planner's own text for task 1.")
        put(f"{shape}-aggregator-prompt.txt", topup.team_prompts().aggregator_prompt(it, step_truths(it)), "team aggregator (E2)",
            "top-up run", topup.aggregator_item(man, it, step_truths(it)),
            note="Shown with the results a correct helper returns (each task's true balances).")
        replies = [PICKER_PLACEHOLDER.format(i=i) for i in range(1, topup.PICKER_SAMPLES + 1)]
        put(f"{shape}-picker-prompt.txt", topup.team_prompts().picker_prompt(it, replies), "picker over 8 replies (H-pick8)", "top-up run",
            topup.picker_item(man, it, replies),
            note="The eight replies are placeholders: in the run they were Haiku-medium samples 1-8 of the main run.")
    return files, recs


def check_not_a_test_render(files: Mapping[str, str]) -> Dict[str, int]:
    """No rendered text equals a file of research/team-prompts/ (renders of a test item). Counts only."""
    theirs = {file_sha(p) for p in sorted(TEAM_RENDERS.rglob("*")) if p.is_file()} if TEAM_RENDERS.is_dir() else set()
    shared = sum(1 for t in files.values() if sha(t) in theirs)
    if shared:
        raise ValueError(f"{shared} rendered prompt(s) equal a render of a test item")
    return {"team_prompt_renders_compared": len(theirs), "shared": 0}


# ---------------------------------------------------------------- the arms

def _arm(study: str, su: main.MainSetup, man: Dict, it: Dict, note: Optional[str] = None) -> Dict[str, object]:
    _, params, _ = main._item(man, it, su, su.name, 1)
    row: Dict[str, object] = {"study": study, "tag": su.name, "model": su.model, "effort": su.effort, "thinking_off": su.thinking_off,
                              "max_tokens": su.max_tokens, "tries_per_puzzle": su.n, "role": su.priority,
                              "request": _strip(params, "illustration/chain-prompt.txt")}
    if note:
        row["note"] = note
    return row


def sweep_arms(man: Dict, chain: Dict, pieces: Dict) -> List[Dict[str, object]]:
    """The length sweep's arms (TAB-13, FIG-05), built by its own runner on the illustrative puzzle: one row per setup, with its tries
    per puzzle counted from the requests the builder makes."""
    reqs = ladder.build_ladder_requests(man, [chain, pieces])
    out = []
    for su in ladder.LADDER_SETUPS:
        mine = [(cid, params, meta) for cid, params, meta in reqs if meta["setup"] == su.name and meta["item_id"] == chain["id"]]
        params = mine[0][1]
        if any(q != params for _, q, _ in mine):
            raise ValueError(f"length sweep {su.name}: the tries of one puzzle differ in their request")
        out.append({"study": "length sweep", "tag": su.name, "model": su.model, "effort": su.effort,
                    "thinking_off": params["thinking"] == {"type": "disabled"}, "max_tokens": params["max_tokens"],
                    "tries_per_puzzle": len(mine), "role": "picker (graded first)" if su == ladder.PICKER else "sealed until the pick",
                    "request": _strip(params, "illustration/chain-prompt.txt")})
    return out


def arms(man: Dict, chain: Dict, pieces: Dict) -> List[Dict[str, object]]:
    out = sweep_arms(man, chain, pieces)
    out += [_arm("Study 1", su, man, chain) for su in main.MAIN_SETUPS]
    out.append(_arm("Study 1", main.D42_SETUP, man, dict(chain, prompt=d42.variant_prompt(chain)),
                    note="the rewording check: the reworded prompt (chain-reworded-prompt.txt) in place of the approved one"))
    plan = json.loads((ROOT / STUDY1B_PLAN).read_text())
    limits = {(int(l["steps"]), str(l["tag"])): int(l["max_tokens"])
              for l in json.loads((ROOT / STUDY1B_ANALYSIS).read_text())["plan_as_run"]["limits"]}
    for s in plan["sets"]:
        for a in s["arms"]:
            calibrated = "max_tokens" not in a
            mt = limits[(int(s["steps"]), str(a["tag"]))] if calibrated else int(a["max_tokens"])
            if not calibrated and limits.get((int(s["steps"]), str(a["tag"])), mt) != mt:
                raise ValueError(f"Study 1b {a['tag']}@{s['steps']}: the plan's limit differs from the run's")
            row = _arm(f"Study 1b, {s['steps']} steps", slim._setup(a, mt), man, chain,
                       note=("max_tokens set by the section 7 rule in the run's trial round (the run's recorded limit)" if calibrated else None))
            out.append(row)
    tp = json.loads((ROOT / TOPUP_PLAN).read_text())
    if (tp["model"], tp["effort"], int(tp["max_tokens"])) != (e3.E3_MODEL, e3.E3_EFFORT, e3.E3_MAX_TOKENS):
        raise ValueError("the top-up plan's settings differ from the e3 constants its team and step calls use")
    sm = main.BY_NAME[tp["same_model"]["mirrors"]]
    out.append(_arm("top-up", main.MainSetup(topup.TAG_SAME_MODEL, sm.model, sm.effort, int(tp["same_model"]["tries"]), sm.max_tokens,
                                             "same-model check", sm.thinking_off), man, chain,
                    note=f"built by main._item with the main run's {sm.name} setup, under its own tag"))
    for tag, role in ((topup.TAG_PLANNER, "team planner"), (topup.TAG_HELPER, "team helper"), (topup.TAG_AGGREGATOR, "team aggregator"),
                      (topup.TAG_PICKER, "picker"), (e3.SETUP_TAG, "step voting (Study 1's Test 4 and the top-up's C13)")):
        out.append({"study": "Study 1 and top-up" if tag == e3.SETUP_TAG else "top-up", "tag": tag, "model": e3.E3_MODEL,
                    "effort": e3.E3_EFFORT, "thinking_off": False, "max_tokens": e3.E3_MAX_TOKENS, "role": role,
                    "request": "as in the prompt records (prompts.json)"})
    return out


# ---------------------------------------------------------------- prices and parsers

def price_table() -> Dict[str, object]:
    def row(r: prices.Rates) -> Dict[str, str]:
        return {"input": str(r.input), "output": str(r.output), "cache_write_5m": str(r.cache_write_5m),
                "cache_write_1h": str(r.cache_write_1h), "cache_read": str(r.cache_read)}
    million = prices.Usage(input_tokens=1_000_000)
    halves = {m: str(prices.cost(m, million, batch=True) / prices.cost(m, million)) for m in prices.MODELS}
    if set(halves.values()) != {"0.5"}:
        raise ValueError(f"Batch is not half price in prices.cost: {halves}")
    return {"unit": "US dollars per million tokens", "table_date_in_code": prices.PRICE_TABLE_DATE,
            "base": {m: row(r) for m, r in prices.PRICES.items()},
            "long_prompt": {m: row(r) for m, r in prices.LONG_PROMPT_PRICES.items()},
            "long_prompt_rule": f"a Haiku request whose prompt tokens exceed {prices.LONG_PROMPT_THRESHOLD:,} is billed whole at the long-prompt row",
            "batch": "every rate x 0.5 (prices.cost with batch=True; checked here for each model)",
            "source": "harness/pareto/prices.py; its dated checks of the pricing page are in research/facts-checked.md"}


def parsers() -> List[Dict[str, object]]:
    out = []
    for path, name, what in PARSERS:
        text = (ROOT / path).read_text()
        tree = ast.parse(text)
        found: Optional[Dict[str, object]] = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                found = {"kind": "function", "line": node.lineno, "doc": ast.get_docstring(node) or ""}
            elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                found = {"kind": "constant", "line": node.lineno, "source": ast.get_source_segment(text, node.value)}
        if found is None:
            raise ValueError(f"{path}: {name} not found")
        out.append({"file": path, "name": name, "what": what, "file_sha256": file_sha(ROOT / path), **found})
    return out


# ---------------------------------------------------------------- writing

SCOPE = ("Covered: the length sweep, Study 1 (the main run), Study 1b and the top-up run. Not covered: Pilot 1 (its 24-step markers "
         "are reported as exploratory), the Haiku effort diagnostic (exploratory; its counts are in Appendix A), and the earlier setup "
         "and smoke checks.")

CODE = ("harness/analysis/reproduction.py", "harness/pareto/d42.py", "harness/pareto/e3.py", "harness/pareto/ladder.py",
        "harness/pareto/pilot.py", "harness/pareto/limits.py", "harness/pareto/main.py",
        "harness/pareto/slim.py", "harness/pareto/topup.py", "harness/pareto/request.py", "harness/pareto/prices.py",
        "harness/taskgen/illustration.py", "harness/taskgen/ledger.py", "harness/taskgen/prompt_d31.py", "research/models/team_prompts.py",
        STUDY1B_PLAN, STUDY1B_ANALYSIS, TOPUP_PLAN)


def build(tasks: Path) -> Dict[str, str]:
    """{file name: content} for the folder."""
    man, chain, pieces, dj = load_puzzle(tasks)
    prompts, recs = render(man, chain, pieces)
    no_test = check_not_a_test_render(prompts)
    out: Dict[str, str] = {f"prompts/{k}": v for k, v in prompts.items()}
    dump = lambda o: json.dumps(o, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    out["prompts.json"] = dump({"label": LABEL, "puzzle": {"set_id": man["set_id"], "chain": chain["id"], "pieces": pieces["id"],
                                                           "disjointness": dj, "not_a_test_render": no_test},
                                "prompts": [dict(r, file=f"prompts/{r['file']}") for r in recs],
                                "shapes": "the chain and pieces prompts themselves are illustration/chain-prompt.txt and pieces-prompt.txt"})
    out["arms.json"] = dump({"label": LABEL, "arms": arms(man, chain, pieces), "scope": SCOPE,
                             "thinking": "adaptive on every arm except thinking_off, which sends {'type': 'disabled'} (Haiku only, effort high or "
                                         "below; harness/pareto/request.py)"})
    out["prices.json"] = dump(price_table())
    out["parsers.json"] = dump({"parsers": parsers()})
    out["sources.json"] = dump({"files": {p: file_sha(ROOT / p) for p in CODE}})
    out["README.md"] = (
        f"# Reproduction details ({LABEL})\n\n"
        "Every kind of prompt the runs sent, made by the run code itself on the paper's illustrative puzzle (`../illustration/`, made "
        "fresh and never from any test set), with the request each arm sent. Built by `python3 -m harness.analysis.reproduction`.\n\n"
        "- `prompts/`: the rewording check's variant (both shapes), step voting (each chain step, Test 4; each piece, the top-up's C13), "
        "and the team prompts (planner, helper, aggregator, picker; both shapes). The chain and pieces prompts are in `../illustration/`.\n"
        "- `prompts.json`: for each prompt, its kind, run, arm tag and the request as built (model, effort, thinking, max_tokens), with "
        "the prompt shown as a pointer to its file. Placeholders mark what only a model could supply (the planner's instruction in the "
        "helper prompt, the eight replies in the picker prompt); the aggregator is shown with a correct helper's results.\n"
        "- `arms.json`: every arm's settings in the length sweep, Study 1 (the main run), Study 1b and the top-up run, each with its "
        "request as built. " + SCOPE + "\n"
        "- `prices.json`: the pinned per-million-token price table, the long-prompt rule and the Batch discount.\n"
        "- `parsers.json`: where replies are read, with each function's docstring or pattern.\n"
        "- `sources.json`: SHA-256 of every code and plan file read; `SHA256SUMS`: SHA-256 of every file here.\n")
    out["SHA256SUMS"] = "".join(f"{sha(t)}  {n}\n" for n, t in sorted(out.items()))
    return out


def write(out_dir: Path, files: Mapping[str, str]) -> None:
    for name, text in files.items():
        p = Path(out_dir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def main_(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tasks", type=Path, required=True, help="the data/tasks folder (disjointness, counts only)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit(f"{a.out} is not empty: build into an empty folder")
    files = build(a.tasks)
    write(a.out, files)
    print(f"wrote {len(files)} files to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main_())
