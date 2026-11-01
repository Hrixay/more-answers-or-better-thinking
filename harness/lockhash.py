"""The D-69 lock manifest's file hashes (spec lock item 7; Edith's lock-contents plan C). No API calls.

    python3 -m harness.lockhash write     # fill the hash block of ops/lock/LOCK-MANIFEST.md from the current commit
    python3 -m harness.lockhash check     # recompute and compare with the block; exit code 1 on any difference
    python3 -m harness.lockhash released  # no git: this copy's files against the block (same, changed since, not in this copy)

Every file git tracks is hashed (SHA-256 of its bytes), except the manifest itself, which holds the hashes. The tree must be clean: the hashes
then describe exactly the committed files (`write` allows the manifest alone to differ, since it is the file being written). The block lists
`<sha256>  <path>` one per line, sorted by path, then the number of files and a digest over those lines, so a re-run on the tag shows at a
glance whether anything moved.

`released` is for a copy without the development history (D-207: the public package is a fresh copy). It needs no git and changes
nothing: it checks the block's file count and digest against its own lines, then reports how many listed files this copy holds with the
locked bytes, how many it holds changed (named), and how many it does not hold. Exit code 1 only if the block is not self-consistent.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

MANIFEST = "ops/lock/LOCK-MANIFEST.md"
BEGIN = "<!-- FILE-HASHES-BEGIN -->"
END = "<!-- FILE-HASHES-END -->"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def tracked_files(root: Path) -> List[str]:
    return sorted(p for p in _git(root, "ls-files", "-z").split("\0") if p and p != MANIFEST)


def file_hashes(root: Path) -> List[Tuple[str, str]]:
    return [(hashlib.sha256((root / p).read_bytes()).hexdigest(), p) for p in tracked_files(root)]


def block(root: Path) -> str:
    lines = [f"{h}  {p}" for h, p in file_hashes(root)]
    digest = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    return "\n".join([BEGIN, "```", *lines, "```", f"Files: {len(lines)}. SHA-256 of the lines above (each followed by a newline): {digest}", END])


def _dirty(root: Path, allow_manifest: bool) -> List[str]:
    out = [ln for ln in _git(root, "status", "--porcelain", "--untracked-files=all").splitlines() if ln.strip()]
    return [ln for ln in out if not (allow_manifest and ln[3:] == MANIFEST)]


def _current(text: str) -> str:
    a, b = text.find(BEGIN), text.find(END)
    if a < 0 or b < a:
        raise SystemExit(f"{MANIFEST} has no {BEGIN} ... {END} block")
    return text[a:b + len(END)]


DIGEST = re.compile(r"Files: (\d+)\. SHA-256 of the lines above \(each followed by a newline\): ([0-9a-f]{64})")


def released(root: Path) -> int:
    body = _current((root / MANIFEST).read_text(encoding="utf-8")).splitlines()
    m = DIGEST.fullmatch(body[-2]) if len(body) >= 5 and body[1] == body[-3] == "```" else None
    lines = body[2:-3]
    if not m or int(m.group(1)) != len(lines) or hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest() != m.group(2):
        print(f"{MANIFEST}: the hash block's file count or digest does not match its lines", file=sys.stderr)
        return 1
    same, changed, absent = 0, [], 0
    for ln in lines:
        want, path = ln.split("  ", 1)
        f = root / path
        if not f.is_file():
            absent += 1
        elif hashlib.sha256(f.read_bytes()).hexdigest() == want:
            same += 1
        else:
            changed.append(path)
    print(f"the block is self-consistent: {len(lines)} files, digest {m.group(2)}")
    print(f"in this copy with the locked bytes: {same}; changed since the lock: {len(changed)}; not in this copy: {absent}")
    for path in changed:
        print("changed since the lock: " + path)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("write", "check", "released"))
    ap.add_argument("--root", type=Path, default=None, help="default: the git top level (released: this code's copy, no git)")
    a = ap.parse_args(argv)
    if a.mode == "released":
        return released(a.root or Path(__file__).resolve().parents[1])
    try:
        root = a.root or Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    except (subprocess.CalledProcessError, OSError):
        print("this folder is not a git repository: `write` and `check` need the development repository; in a released copy run "
              "`python3 -m harness.lockhash released`", file=sys.stderr)
        return 2
    dirty = _dirty(root, allow_manifest=a.mode == "write")
    if dirty:
        print("the tree is not clean; commit or remove these first:\n" + "\n".join(dirty), file=sys.stderr)
        return 2
    path = root / MANIFEST
    text = path.read_text(encoding="utf-8")
    new = block(root)
    if a.mode == "write":
        path.write_text(text.replace(_current(text), new), encoding="utf-8")
        print(new.splitlines()[-2])
        return 0
    if _current(text) == new:
        print("ok: " + new.splitlines()[-2])
        return 0
    old = {ln for ln in _current(text).splitlines()}
    for ln in new.splitlines():
        if ln not in old:
            print("differs: " + ln, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
