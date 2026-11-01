"""Regenerate a frozen test set from the released code (D-212: the public generator rebuilds the sets, and this is said plainly), then check it
against the lock manifest. No model call, no network. Prints yes/no and counts only, never an item.

    python3 -m harness.taskgen.regenerate --list
    python3 -m harness.taskgen.regenerate --set main-ledger-l14n6-v1 --out <folder> [--check]

`frozen-sets.json` holds each set's build parameters (family, setting, base puzzles, prompt style, split) and the generator version that wrote
it. The set is built by `freeze.write_set`, exactly as at the freeze; the one thing set right afterwards is each item's `version` field, which
the released generator writes as its own version (ledger-0.5) while the item's other fields, its prompt and its answer are the same: a set
frozen by an older generator gets its recorded version back. With --check, items.jsonl's SHA-256 is compared with the line for it in
ops/lock/LOCK-MANIFEST.md (the hash block at the last lock): `yes` means the regenerated file is byte for byte the locked one.
Some sets take hours (the 16- and 17-step ledger sets); the main sets take seconds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from . import freeze

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TABLE = HERE / "frozen-sets.json"
LOCK = ROOT / "ops" / "lock" / "LOCK-MANIFEST.md"


def table() -> Dict[str, Dict]:
    return {r["set_id"]: r for r in json.loads(TABLE.read_text(encoding="utf-8"))["sets"]}


def regenerate(set_id: str, out: Path) -> Dict:
    """Write the set under `out/<set_id>`; returns the manifest. The recorded generator version is put back on each item that carries one."""
    row = table()[set_id]
    build = freeze.build_items

    def patched(*args, **kw):
        items = build(*args, **kw)
        for r in items:
            if "version" in r:
                r["version"] = row["generator"]
        return items

    freeze.build_items = patched
    try:
        return freeze.write_set(Path(out) / set_id, row["family"], row["setting"], set_id, row["n_base"], row["style"], row["split"])
    finally:
        freeze.build_items = build


def locked_hash(set_id: str, lock: Path = LOCK, name: str = "items.jsonl") -> Optional[str]:
    m = re.search(r"([0-9a-f]{64})  data/tasks/" + re.escape(set_id) + "/" + re.escape(name) + "\n", lock.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def matches_lock(set_id: str, folder: Path, lock: Path = LOCK) -> bool:
    want = locked_hash(set_id, lock)
    return want is not None and hashlib.sha256((Path(folder) / set_id / "items.jsonl").read_bytes()).hexdigest() == want


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="the 28 set ids with their generator versions and sizes")
    ap.add_argument("--set", action="append", default=[], help="a set id (repeat for several), or 'all'")
    ap.add_argument("--out", type=Path, help="a folder; each set is written under <out>/<set id>, which must not exist yet")
    ap.add_argument("--check", action="store_true", help="compare items.jsonl with the lock manifest's hash (yes/no)")
    ap.add_argument("--workers", type=int, default=None, help="at most this many worker processes (default: the machine's cores, up to 8)")
    a = ap.parse_args(argv)
    t = table()
    if a.list:
        for r in t.values():
            print(f"{r['set_id']}  {r['family']} {r['setting']}  {r['n_base']} base puzzles  {r['generator']}")
        return 0
    ids: List[str] = list(t) if a.set == ["all"] else a.set
    if not ids or a.out is None:
        ap.error("need --set <id> (or all) and --out")
    unknown = [i for i in ids if i not in t]
    if unknown:
        ap.error(f"not a frozen set: {', '.join(unknown)}")
    if a.workers:
        multiprocessing.cpu_count = lambda: a.workers                                     # freeze.write_set sizes its pool from this
    bad = 0
    for sid in ids:
        regenerate(sid, a.out)
        line = f"{sid}: written ({t[sid]['n_base'] * 2} items)"
        if a.check:
            ok = matches_lock(sid, a.out)
            bad += not ok
            line += f"; items.jsonl matches the lock manifest: {'yes' if ok else 'no'}"
        print(line, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
