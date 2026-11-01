"""After the push: check that git tracks every file RELEASE-FILES.json lists (Edith's P1). The package's `.gitignore` (locked bytes) has a
`data/raw/` line, so the per-call tables and run records are tracked only if the push ran `git add -f data/raw`; a plain `git add -A`
leaves them out, and so would the Zenodo archive made from the repository. Standard library only; needs git; no network.

    python3 -m harness.check_tracked [--root <repository folder>]

Prints counts and the paths that are not tracked (paths only). Exit status 0 when every listed file is tracked, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]


def listed(root: Path) -> List[str]:
    """Every path RELEASE-FILES.json names: the released files, the supplied ones, and the generated ones (a folder entry such as
    `lock-records/` stands for the files in it)."""
    doc = json.loads((root / "RELEASE-FILES.json").read_text(encoding="utf-8"))
    paths = [f["path"] for f in doc["files"]] + [f["path"] for f in doc["supplied"]]
    for g in doc["generated"]:
        if g.endswith("/"):
            paths += sorted(p.relative_to(root).as_posix() for p in (root / g).rglob("*") if p.is_file())
        else:
            paths.append(g)
    return paths


def untracked(root: Path) -> List[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True).stdout
    tracked = {p.decode("utf-8") for p in out.split(b"\0") if p}
    return sorted((set(listed(root)) | {"RELEASE-FILES.json"}) - tracked)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=ROOT, help="the repository folder (default: this checkout)")
    a = ap.parse_args(argv)
    try:
        missing = untracked(a.root)
    except subprocess.CalledProcessError:
        print("not a git repository (or git cannot read it): run this after `git init` and the add step")
        return 1
    total = len(set(listed(a.root)) | {"RELEASE-FILES.json"})
    print(f"files listed in RELEASE-FILES.json: {total}; tracked by git: {total - len(missing)}; not tracked: {len(missing)}")
    for p in missing:
        print(f"not tracked: {p}")
    if any(p.startswith("data/raw/") for p in missing):
        print("the .gitignore hides data/raw/: add it with `git add -f data/raw`")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
