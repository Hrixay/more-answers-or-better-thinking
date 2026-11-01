"""Render the ledger wording pack (L4, D-77) from a FROZEN set: base puzzle 0, both shapes, main and answer-only, the reference replies and
the E3 step call (sequence 1, step 3). Each main file is asserted equal to the frozen prompt, and each puzzle is asserted to rebuild from its
seed, so the pack is exactly the text the set sends.

    python3 -m harness.taskgen.wording_pack --set data/tasks/check-ledger-l16-v1 --out data/examples/prompts-ledger --tag l16-check-base0
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

from . import ledger, prompt_d31


def _params(r: Dict) -> ledger.LParams:
    return ledger.LParams(**{**r["params"], "kinds": tuple(r["params"]["kinds"]), "house_fires": tuple(r["params"]["house_fires"])})


def render(set_dir: Path, out: Path, tag: str) -> List[Path]:
    items = [json.loads(ln) for ln in (set_dir / "items.jsonl").read_text().splitlines()]
    base0 = sorted([r for r in items if r["base_index"] == 0], key=lambda r: r["width"])          # 1x24 first, then 24x1
    written = []
    for r in base0:
        shape = f"{r['width']}x{r['depth']}"
        main = ledger.generate(r["seed"], r["width"], r["depth"], _params(r), item_id=r["id"], style=r["style"])
        assert main.prompt == r["prompt"], f"{r['id']}: does not rebuild from its seed"
        only = ledger.generate(r["seed"], r["width"], r["depth"], _params(r), item_id=r["id"], style="d31-answer-only")
        reply = ledger.reference_reply(main)                       # step lines (1x24 only), then the Answer line
        g = ledger.grade_d31(reply, main)
        assert g["all_correct"] and (r["depth"] == 1 or g["steps_shown"] == r["depth"]), f"{r['id']}: the reference reply does not grade as right"
        files = {f"ledger-{tag}-{shape}.txt": main.prompt, f"ledger-{tag}-{shape}-answer-only.txt": only.prompt,
                 f"ledger-{tag}-{shape}-reference-reply.txt": reply}
        if r["depth"] > 1:
            files[f"ledger-{tag}-step-call-e3.txt"] = ledger.step_call(main, 1, 3)[0]
        for name, text in files.items():
            assert not re.search(prompt_d31.BANNED, text.lower()) and "$" not in text, f"{name}: a non-neutral word or a currency sign"
            (out / name).write_text(text)                          # byte for byte the prompt: no trailing newline
            written.append(out / name)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    for f in render(a.set, a.out, a.tag):
        print("wrote", f)


if __name__ == "__main__":
    main()
