"""Frozen task sets: write, verify and compare (pilot and main sets must never overlap).

    python3 -m harness.taskgen.freeze --selftest
    python3 -m harness.taskgen.freeze --family digits --setting d4 --set-id pilot-digits-v1 --n-base 4 \\
        --style d31 --split pilot --out /some/scratch/dir
    python3 -m harness.taskgen.freeze --verify DIR
    python3 -m harness.taskgen.freeze --disjoint DIR_A DIR_B

A set holds `n_base` base puzzles, each in BOTH shapes (24x1 and 1x24; D-24, matched design D-28): the same rules
and rule order, only the wiring and the start values differ. Base puzzle i uses the seed
`derive_seed(set_id, i)`, so two sets with different `set_id`s share nothing. A set is written once and never
regenerated in place: the writer refuses to write into an existing folder, and refuses to write under
`data/tasks/` unless `--really-freeze` is given (it is for the user-approved pilot and main sets only; this build
writes nothing there). Files: `manifest.json` (no timestamps, so the same inputs and the same code give the same bytes) and
`items.jsonl` (one full puzzle record per line: prompt, answer, trace, seed, parameters).

Pinning the code (Edith G1): the manifest also records `git_commit`, `git_dirty` (any uncommitted change under
harness/taskgen) and `taskgen_sources_sha256` (every .py file in harness/taskgen). Version strings alone are too coarse
to pin a pre-registered set. `verify_set` WARNS (stderr; it does not fail) when the current code differs from the code
that wrote the set; the real check is still that every stored prompt re-solves to its stored answer.

Naming (Edith N43): name set ids by family, preset and split, for example `pilot-digits-d4s-v1`. A set id shared across
d4s and d4p would pair their rulebooks. Keep pilot and main set ids disjoint from each other and from the free-test
and wording-check seeds. For the run that clears a frozen set, run codetrace_check with a bigger seed count (N44).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from . import codetrace, codetrace_check, ledger, ledger_check, prompt_d31
from .check import solve_from_text
from .puzzle import GENERATOR_VERSION, PRESETS, generate as generate_digits
from .rng import derive_seed

SHAPES = ((24, 1), (1, 24))                     # the 24-step shapes; a set's shapes come from its preset's step count (shapes_for)
FAMILIES = ("digits", "code", "ledger")
STYLES = ("legacy", "d31", "d31-answer-only", "d31-variant")


def shapes_for(params) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """The two shapes of a base puzzle: N one-step pieces and one chain of N steps (N = the preset's total_steps; 24 before D-86)."""
    n = int(getattr(params, "total_steps", 24))
    return ((n, 1), (1, n))


def _params(family: str, setting: str):
    table = {"digits": PRESETS, "code": codetrace.SETTINGS, "ledger": ledger.SETTINGS}[family]
    if setting not in table:
        raise ValueError(f"unknown {family} setting {setting!r}; choose from {sorted(table)}")
    if family == "ledger" and setting in ledger.RETIRED:
        raise ValueError(f"ledger preset {setting!r} is retired (it cannot meet the absorption cap); use l11 or l14 to l17")
    return table[setting]


def build_items(family: str, setting: str, set_id: str, n_base: int, style: str) -> List[Dict]:
    if family not in FAMILIES or style not in STYLES:
        raise ValueError("unknown family or prompt style")
    if style == "d31-variant" and family != "digits":
        raise ValueError("the D-42 prompt variant exists for the digit puzzles only")
    if family == "ledger" and style not in ("d31", "d31-answer-only"):
        raise ValueError("the ledger exists in the d31 and d31-answer-only styles only")
    if n_base < 1 or not set_id:
        raise ValueError("need a set id and at least one base puzzle")
    params = _params(family, setting)
    if family == "ledger" and n_base > 1:                          # ledger bases are slow to build and independent: one process each (same output as serial)
        import multiprocessing
        with multiprocessing.get_context("fork").Pool(min(multiprocessing.cpu_count(), n_base, 8)) as pool:
            per_base = pool.starmap(_build_base, [(family, params, set_id, i, style) for i in range(n_base)])
        return [rec for recs in per_base for rec in recs]
    return [rec for i in range(n_base) for rec in _build_base(family, params, set_id, i, style)]


def _build_base(family: str, params, set_id: str, i: int, style: str) -> List[Dict]:
    """Both shapes of base puzzle i."""
    seed = derive_seed(set_id, i)
    out = []
    for w, d in shapes_for(params):
        item_id = f"{set_id}-{i:03d}-{w}x{d}"
        if family == "digits":
            p = generate_digits(seed, w, d, params, item_id=item_id, style=style)
        elif family == "code":
            p = codetrace.generate(seed, w, d, params, item_id=item_id, style=style)
        else:
            p = ledger.generate(seed, w, d, params, item_id=item_id, style=style)
        rec = p.to_dict()
        rec["base_index"] = i
        out.append(rec)
    return out


HERE = Path(__file__).resolve().parent


def sources_sha256() -> str:
    """SHA-256 over every .py file in harness/taskgen (names and bytes, sorted)."""
    h = hashlib.sha256()
    for f in sorted(HERE.glob("*.py")):
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def git_pin() -> Dict[str, object]:
    def run(*args: str) -> str:
        r = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    commit = run("rev-parse", "HEAD")
    return {"git_commit": commit or "unknown", "git_dirty": bool(run("status", "--porcelain", "--", str(HERE))) if commit else None}


def code_pin_warnings(man: Dict) -> List[str]:
    """Differences between the code that wrote a set and the code running now. Warnings, never failures."""
    out: List[str] = []
    if man.get("taskgen_sources_sha256") != sources_sha256():
        out.append("harness/taskgen sources differ from the code that wrote this set")
    now = git_pin()
    if man.get("git_commit") != now["git_commit"]:
        out.append(f"git commit differs (set: {man.get('git_commit')}, now: {now['git_commit']})")
    if man.get("git_dirty"):
        out.append("the set was written from a tree with uncommitted changes")
    return out


def _dump(items: List[Dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in items)


def write_set(out: Path, family: str, setting: str, set_id: str, n_base: int, style: str, split: str,
              really_freeze: bool = False) -> Dict:
    out = Path(out)
    if out.exists():
        raise FileExistsError(f"{out} already exists; a frozen set is never regenerated in place")
    if "data/tasks" in out.resolve().as_posix() and not really_freeze:
        raise PermissionError("writing under data/tasks/ needs --really-freeze (only for user-approved sets)")
    if split not in ("pilot", "main", "scratch"):
        raise ValueError("split must be pilot, main or scratch")
    items = build_items(family, setting, set_id, n_base, style)
    text = _dump(items)
    manifest = {
        "set_id": set_id, "family": family, "setting": setting, "split": split, "prompt_style": style,
        "generator": {"digits": GENERATOR_VERSION, "code": codetrace.CT_VERSION, "ledger": ledger.LV_VERSION}[family],
        "setting_params": asdict(_params(family, setting)),
        "n_base": n_base, "shapes": [f"{w}x{d}" for w, d in shapes_for(_params(family, setting))], "n_items": len(items),
        "seeds": [str(derive_seed(set_id, i)) for i in range(n_base)],
        "prompt_sha256": [hashlib.sha256(r["prompt"].encode()).hexdigest() for r in items],
        "items_sha256": hashlib.sha256(text.encode()).hexdigest(),
        **git_pin(), "taskgen_sources_sha256": sources_sha256(),
    }
    out.mkdir(parents=True)
    (out / "items.jsonl").write_text(text)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def _solve(family: str, prompt: str):
    if family == "digits":
        return solve_from_text(prompt)
    return codetrace_check.solve(prompt) if family == "code" else ledger_check.solve(prompt)


def _verify_ledger_item(r: Dict, allow_other_version: bool = False) -> None:
    """Edith's B5: the L1/L2 checks, the neutral-word scan and the transfer-slip cap, run on a frozen ledger item. The item is rebuilt from
    its seed and generator version; it must equal the stored one, and the independent checker (ledger_check.check_puzzle) must pass it.
    A set made by another generator version cannot be rebuilt: it still gets the text-only checks (re-solve above, word scan here)."""
    hit = re.search(prompt_d31.BANNED, r["prompt"].lower())
    assert not hit, f"{r['id']}: non-neutral word in the prompt: {hit.group(0)}"
    assert "$" not in r["prompt"], f"{r['id']}: currency symbol in the prompt"
    if r["version"] != ledger.LV_VERSION:
        if not allow_other_version:
            raise AssertionError(f"{r['id']} was made by generator {r['version']}, not {ledger.LV_VERSION}; a set from another generator version does not verify "
                                 f"(pass allow_other_version=True / --allow-other-version to run only the text checks)")
        print(f"WARNING: {r['id']} was made by generator {r['version']}, not {ledger.LV_VERSION}: only the text checks ran", file=sys.stderr)
        return
    params = ledger.LParams(**{**r["params"], "kinds": tuple(r["params"]["kinds"]), "house_fires": tuple(r["params"]["house_fires"])})
    again = ledger.generate(r["seed"], r["width"], r["depth"], params, item_id=r["id"], style=r["style"])
    assert again.prompt == r["prompt"] and again.answer == r["answer"], f"{r['id']}: does not rebuild from its seed"
    stored = {k: v for k, v in r.items() if k != "base_index"}
    assert json.loads(json.dumps(again.to_dict())) == stored, f"{r['id']}: a stored field (draw number, slip measures, chains) differs from the rebuild"
    ledger_check.check_puzzle(again)


def verify_set(folder: Path, allow_other_version: bool = False) -> Dict:
    """Re-check a written set: the file hash, the seeds, the prompt hashes, that every prompt re-solves to its stored
    answer from the printed text alone, and that both shapes of a base puzzle share rules and rule order."""
    folder = Path(folder)
    man = json.loads((folder / "manifest.json").read_text())
    text = (folder / "items.jsonl").read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == man["items_sha256"], "items.jsonl changed after freezing"
    items = [json.loads(ln) for ln in text.splitlines()]
    assert len(items) == man["n_items"] == 2 * man["n_base"]
    assert [str(derive_seed(man["set_id"], i)) for i in range(man["n_base"])] == man["seeds"], "seeds do not follow set_id"
    assert [hashlib.sha256(r["prompt"].encode()).hexdigest() for r in items] == man["prompt_sha256"]
    assert len({r["prompt"] for r in items}) == len(items), "two items have the same prompt"
    shapes = {tuple(int(x) for x in sh.split("x")) for sh in man.get("shapes", ["24x1", "1x24"])}
    n = int((man.get("setting_params") or {}).get("total_steps", 24))
    assert shapes == {(n, 1), (1, n)}, f"the manifest's shapes {sorted(shapes)} do not match its {n} steps"
    by_base: Dict[int, List[Dict]] = {}
    for r in items:
        solved = _solve(man["family"], r["prompt"])
        got = [s[-1] for s in solved]
        want = r["answer"]
        if man["family"] == "code":
            want = [list(a) for a in want]
        assert got == want, f"{r['id']}: prompt text disagrees with the stored answer"
        if man["family"] == "ledger":
            _verify_ledger_item(r, allow_other_version)
        by_base.setdefault(r["base_index"], []).append(r)
    for i, pair in by_base.items():
        assert len(pair) == 2 and {(r["width"], r["depth"]) for r in pair} == shapes, i
        order = [[n for ch in r["chains"] for n in (ch["rules"] if man["family"] == "digits" else ch["names"])]
                 for r in pair]
        assert order[0] == order[1], f"base {i}: the two shapes do not share the rule order"
        if man["family"] == "ledger":
            assert pair[0]["rulebook"] == pair[1]["rulebook"], f"base {i}: the two shapes print different rulebooks"
    for w in code_pin_warnings(man):
        print(f"WARNING: {w}", file=sys.stderr)
    return man


def disjoint(a: Path, b: Path) -> None:
    """Raise unless two sets share no seed, no set id and no prompt (pilot and main never overlap)."""
    ma, mb = (json.loads((Path(x) / "manifest.json").read_text()) for x in (a, b))
    assert ma["set_id"] != mb["set_id"], "same set id"
    assert not set(ma["seeds"]) & set(mb["seeds"]), "the sets share a seed"
    assert not set(ma["prompt_sha256"]) & set(mb["prompt_sha256"]), "the sets share a prompt"


def selftest() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for family, setting in (("digits", "d0"), ("digits", "d3"), ("code", "c1"), ("ledger", "l1")):
            for style in ("legacy", "d31"):
                if family == "ledger" and style == "legacy":
                    continue                                     # the ledger exists in the d31 styles only
                a = td / f"{family}-{setting}-{style}-a"
                m1 = write_set(a, family, setting, "selftest-set-a", 2, style, "scratch")
                verify_set(a)
                # the same inputs give the same bytes
                b = td / f"{family}-{setting}-{style}-a2"
                write_set(b, family, setting, "selftest-set-a", 2, style, "scratch")
                assert (a / "items.jsonl").read_bytes() == (b / "items.jsonl").read_bytes()
                assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()
                # never regenerated in place
                try:
                    write_set(a, family, setting, "selftest-set-a", 2, style, "scratch")
                except FileExistsError:
                    pass
                else:
                    raise AssertionError("overwrite was allowed")
                # a different set id shares nothing; the same id is caught
                c = td / f"{family}-{setting}-{style}-c"
                write_set(c, family, setting, "selftest-set-c", 2, style, "scratch")
                disjoint(a, c)
                try:
                    disjoint(a, b)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("identical sets were called disjoint")
                # a changed item is caught
                text = (c / "items.jsonl").read_text()
                (c / "items.jsonl").write_text(text.replace("Start at", "Start  at", 1))
                try:
                    verify_set(c)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("a changed item was not caught")
        # the manifest pins the code; a mismatch warns but never fails
        m = json.loads((td / "digits-d0-legacy-a" / "manifest.json").read_text())
        assert len(m["taskgen_sources_sha256"]) == 64 and "git_commit" in m and "git_dirty" in m
        assert not [w for w in code_pin_warnings(m) if "sources differ" in w]
        m2 = dict(m, taskgen_sources_sha256="0" * 64, git_commit="deadbeef", git_dirty=True)
        ws = code_pin_warnings(m2)
        assert len(ws) == 3, ws
        # writing under data/tasks needs the flag
        try:
            write_set(Path("data/tasks/selftest-should-not-exist"), "digits", "d0", "x", 1, "legacy", "scratch")
        except PermissionError:
            pass
        else:
            raise AssertionError("wrote under data/tasks without --really-freeze")
        assert not Path("data/tasks/selftest-should-not-exist").exists()
    print("ok: frozen-set writer: deterministic bytes, never overwrites, verifies from the printed text, "
          "detects changes and overlap; digits d0/d3, code c1 and ledger l1, legacy and d31 styles")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verify")
    ap.add_argument("--allow-other-version", action="store_true", help="--verify only: a ledger set made by another generator version gets the text checks only")
    ap.add_argument("--disjoint", nargs=2)
    ap.add_argument("--family", choices=FAMILIES)
    ap.add_argument("--setting")
    ap.add_argument("--set-id")
    ap.add_argument("--n-base", type=int)
    ap.add_argument("--style", choices=STYLES, default="d31")
    ap.add_argument("--split", default="scratch")
    ap.add_argument("--out")
    ap.add_argument("--really-freeze", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.verify:
        m = verify_set(Path(a.verify), a.allow_other_version)
        print(f"ok: {m['set_id']} ({m['family']} {m['setting']}, {m['n_items']} items) verifies")
    elif a.disjoint:
        disjoint(Path(a.disjoint[0]), Path(a.disjoint[1]))
        print("ok: the two sets share no set id, seed or prompt")
    else:
        if not (a.family and a.setting and a.set_id and a.n_base and a.out):
            ap.error("need --family --setting --set-id --n-base --out")
        m = write_set(Path(a.out), a.family, a.setting, a.set_id, a.n_base, a.style, a.split, a.really_freeze)
        print(f"wrote {m['n_items']} items to {a.out} (items sha256 {m['items_sha256'][:12]})")


if __name__ == "__main__":
    sys.exit(main())
