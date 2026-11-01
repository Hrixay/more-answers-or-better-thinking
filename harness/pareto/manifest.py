"""The run manifest: what exactly was run, written once before the first call.

`data/raw/<run-id>/manifest.json` records the run id and caps, the code that ran (git commit, whether the tree was
dirty, a SHA-256 over harness/pareto and harness/taskgen sources), the price-table date, the mode (dry or live), and a
hash of the item set (every custom_id with the hash of its full request). Two runs with the same item-set hash sent the
same requests. Refuses to overwrite an existing manifest: a new run gets a new run id.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Tuple

from .prices import PRICE_TABLE_DATE
from .request import params_hash

ROOT = Path(__file__).resolve().parents[2]


def source_hash(dirs: Iterable[str] = ("harness/pareto", "harness/taskgen")) -> str:
    h = hashlib.sha256()
    for d in dirs:
        for f in sorted((ROOT / d).rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            h.update(str(f.relative_to(ROOT)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def git_state() -> Dict[str, object]:
    def run(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain", "--", "harness"))}


def item_set_hash(items: Iterable[Tuple[str, Dict[str, object], Dict[str, object]]]) -> str:
    h = hashlib.sha256()
    for cid, params, _ in sorted(items, key=lambda it: it[0]):
        h.update(cid.encode() + b"\0" + params_hash(params).encode() + b"\0")
    return h.hexdigest()


def sdk_version() -> object:
    """The installed anthropic version, or None when the SDK is not installed (a dry run does not need it)."""
    try:
        from importlib.metadata import version
        return version("anthropic")
    except Exception:
        return None


def write_manifest(run_dir: Path, guard, items, mode: str, note: str = "") -> Path:
    path = Path(run_dir) / "manifest.json"
    if path.exists():
        raise FileExistsError(f"{path} exists: a new run needs a new run id")
    path.parent.mkdir(parents=True, exist_ok=True)
    items = list(items)
    doc = {"run_id": guard.run_id, "mode": mode, "run_cap_usd": str(guard.run_cap), "global_cap_usd": str(guard.global_cap),
           "global_spent_before_usd": str(guard.global_spent), "price_table_date": PRICE_TABLE_DATE,
           "git": git_state(), "anthropic_version": sdk_version(), "source_sha256": source_hash(), "n_items": len(items),
           "item_set_sha256": item_set_hash(items), "note": note}
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return path
