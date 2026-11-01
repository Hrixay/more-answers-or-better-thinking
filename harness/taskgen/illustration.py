"""The paper's illustrative puzzle (D-141: "a puzzle example: one small puzzle shown as a chain and as pieces, made fresh for the figure and
never from any test set"; Friday generates it "from a seed outside every frozen set (checked disjoint by program, no test item printed)").

    python3 -m harness.taskgen.illustration --tasks <data/tasks folder> --out data/paper-outputs/illustration

One base puzzle of the l14n4 preset (the l14 rule set at 4 steps: the D-86 ladder's shortest length), built by the frozen sets' own code
path (freeze._build_base, ledger.generate) from the seed derive_seed(SET_ID, 0) of a set id that names no frozen set. Disjointness is
proved against every set folder under data/tasks: the set id, the seed and both prompts' SHA-256 are compared with each folder's
manifest.json (its set_id, seeds and prompt_sha256; where a manifest has no prompt_sha256, the prompts in its items.jsonl are hashed
in memory). Nothing from a test set is printed or written: only counts. The output is labelled "illustrative, not from any test set".
Deterministic: the same code gives the same files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

from . import freeze, ledger
from .rng import derive_seed

SET_ID = "paper-illustration-ledger-l14n4-v1"
SETTING = "l14n4"
STYLE = "d31"
LABEL = "illustrative, not from any test set"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build() -> List[Dict]:
    params = freeze._params("ledger", SETTING)
    return freeze._build_base("ledger", params, SET_ID, 0, STYLE)


def disjointness(tasks: Path, items: List[Dict]) -> Dict[str, object]:
    """Counts only. Refuses (raises) on any shared set id, seed or prompt."""
    seed = str(derive_seed(SET_ID, 0))
    ours = {sha(it["prompt"]) for it in items}
    sets = seeds = prompts = hashed_from_items = 0
    for folder in sorted(p for p in Path(tasks).iterdir() if p.is_dir()):
        man_path = folder / "manifest.json"
        if not man_path.is_file():
            continue
        man = json.loads(man_path.read_text())
        sets += 1
        if man.get("set_id") == SET_ID:
            raise ValueError(f"{folder.name}: shares the illustration's set id")
        s = [str(x) for x in man.get("seeds") or []]
        seeds += len(s)
        if seed in s:
            raise ValueError(f"{folder.name}: shares the illustration's seed")
        ph = list(man.get("prompt_sha256") or [])
        if not ph:
            items_path = folder / "items.jsonl"
            if items_path.is_file():
                with items_path.open() as f:
                    ph = [sha(json.loads(line)["prompt"]) for line in f if line.strip()]
                hashed_from_items += len(ph)
        prompts += len(ph)
        if ours & set(ph):
            raise ValueError(f"{folder.name}: shares a prompt with the illustration")
    return {"sets_checked": sets, "seeds_compared": seeds, "prompt_hashes_compared": prompts,
            "prompt_hashes_computed_from_items": hashed_from_items, "shared_set_ids": 0, "shared_seeds": 0, "shared_prompts": 0,
            "illustration_set_id": SET_ID, "illustration_seed": seed}


def write(out: Path, items: List[Dict], dj: Dict[str, object]) -> Dict[str, str]:
    out.mkdir(parents=True, exist_ok=True)
    files: Dict[str, str] = {}

    def put(name: str, text: str) -> None:
        (out / name).write_text(text, encoding="utf-8")
        files[name] = sha(text)
    by_shape = {f"{it['width']}x{it['depth']}": it for it in items}
    n = int(ledger.SETTINGS[SETTING].total_steps)
    chain, pieces = by_shape[f"1x{n}"], by_shape[f"{n}x1"]
    for name, it in (("chain", chain), ("pieces", pieces)):
        put(f"{name}-prompt.txt", it["prompt"])
        p = ledger.generate(it["seed"], it["width"], it["depth"], ledger.SETTINGS[SETTING], item_id=it["id"], style=STYLE)
        if p.prompt != it["prompt"]:
            raise ValueError("the puzzle does not rebuild from its seed")
        put(f"{name}-reference-reply.txt", ledger.reference_reply(p))
    doc = {"label": LABEL, "ruling": "D-141", "set_id": SET_ID, "setting": SETTING, "style": STYLE,
           "generator": ledger.LV_VERSION, "seed": dj["illustration_seed"], "disjointness": dj,
           "puzzles": {"chain": chain, "pieces": pieces}}
    put("illustration.json", json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    put("README.md", "# Illustrative puzzle (" + LABEL + ")\n\n"
        f"One base puzzle of the {SETTING} preset (the l14 rule set at {n} steps), shown as a chain (1x{n}) and as pieces ({n}x1), made "
        f"fresh for the paper's puzzle figure (D-141) by the frozen sets' own generator ({ledger.LV_VERSION}) from the seed of set id "
        f"`{SET_ID}`, which names no frozen set. `illustration.json` holds both puzzles (prompt, rulebook, start balances, every reference "
        "state, the answer) and the disjointness proof (counts only): no shared set id, seed or prompt with any set under data/tasks/. "
        "It is not from any test set and no model has seen it. Files: `chain-prompt.txt`, `pieces-prompt.txt`, the reference replies, "
        "`illustration.json`; SHA-256 of each in `SHA256SUMS`.\n")
    sums = "".join(f"{h}  {name}\n" for name, h in sorted(files.items()))
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    items = build()
    dj = disjointness(a.tasks, items)
    files = write(a.out, items, dj)
    print(json.dumps({k: v for k, v in dj.items() if k not in ("illustration_seed",)}, sort_keys=True))
    print("wrote", len(files), "files to", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
