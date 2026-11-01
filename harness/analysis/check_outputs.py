"""Check the paper's tables and figures against `data/paper-outputs/MANIFEST.json` without rebuilding them (D-207). Standard library only;
no model call, no network, no git.

    python3 -m harness.analysis.check_outputs [--root <package folder>] [--outputs <folder>] [--json]

Three things, each as counts and names of ids (never file contents):
1. every file the manifest lists exists in the outputs folder and has the listed SHA-256 (a missing or different file is a failure); an
   output the manifest marks "as built" (a rebuild in a copy without the history could not make it) is checked in the shipped folder,
   <root>/data/paper-outputs, whichever folder is being checked;
2. every pinned source an output was built from, wherever this folder holds it (by its manifest path), is counted: present with the
   pinned SHA-256, different (a file that has been edited since its pin: outputs that read it cannot be rebuilt from it; with --strict
   this is a failure) or absent (the package does not ship every source);
3. which outputs can be rebuilt here, meaning every source they read is present with its pinned bytes and the manifest does not mark
   them "as built". The others ship as built and are checked by (1). Rebuilding itself is `python3 -m harness.analysis.paper_outputs --out <empty folder> --from-disk`.

Exit status 0 when every listed output file matches (and, with --strict, no source differs), 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(root: Path, outputs: Optional[Path] = None) -> Dict[str, Any]:
    outputs = outputs or root / "data" / "paper-outputs"
    manifest = json.loads((outputs / "MANIFEST.json").read_text(encoding="utf-8"))
    files_ok, files_bad, files_missing = 0, [], []
    sources: Dict[str, str] = {}                                    # path -> pinned SHA-256 (the same path is pinned once per distinct version)
    versions: Dict[str, set] = {}
    shipped = root / "data" / "paper-outputs"
    for entry in manifest["outputs"]:
        folder = shipped if entry.get("status") == "as built" else outputs      # a rebuild folder holds none of an as-built output's files
        for name, want in entry["files"].items():
            p = folder / name
            if not p.is_file():
                files_missing.append(name)
            elif sha256(p) == want:
                files_ok += 1
            else:
                files_bad.append(name)
        for src in (entry.get("sources") or {}).values():
            versions.setdefault(src["path"], set()).add(src["sha256"])
    plan = manifest.get("plan")
    if plan:
        versions.setdefault(plan["path"], set()).add(plan["sha256"])
    state: Dict[str, Dict[str, str]] = {}                           # path -> {pinned sha -> "ok" | "differs" | "absent"}
    for path, shas in versions.items():
        p = root / path
        got = sha256(p) if p.is_file() else None
        state[path] = {s: ("absent" if got is None else "ok" if got == s else "differs") for s in shas}
    sources_differ = sorted(p for p, v in state.items() if all(x == "differs" for x in v.values()))
    rebuilds, ships = [], {}
    for entry in manifest["outputs"]:
        need = [(src["path"], src["sha256"]) for src in (entry.get("sources") or {}).values()] + ([(plan["path"], plan["sha256"])] if plan else [])
        lacking = sorted({p for p, s in need if state[p][s] != "ok"})
        (rebuilds.append(entry["id"]) if not lacking and entry.get("status") != "as built" else ships.__setitem__(entry["id"], lacking))
    return {"outputs": len(manifest["outputs"]), "files_listed": files_ok + len(files_bad) + len(files_missing), "files_ok": files_ok,
            "files_different": sorted(files_bad), "files_missing": sorted(files_missing),
            "sources_pinned_paths": len(state), "sources_present_ok": sum(1 for v in state.values() if "ok" in v.values()),
            "sources_absent": sorted(p for p, v in state.items() if all(x == "absent" for x in v.values())),
            "sources_different": sources_differ, "rebuilds_here": rebuilds, "ships_as_built": ships}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=ROOT, help="the package folder (default: this checkout)")
    ap.add_argument("--outputs", type=Path, default=None, help="the outputs folder (default: <root>/data/paper-outputs)")
    ap.add_argument("--json", action="store_true", help="print the whole result as JSON")
    ap.add_argument("--strict", action="store_true", help="a source whose bytes differ from its pin is also a failure")
    a = ap.parse_args(argv)
    r = check(a.root, a.outputs)
    bad = bool(r["files_different"] or r["files_missing"] or (a.strict and r["sources_different"]))
    if a.json:
        print(json.dumps(r, indent=1, sort_keys=True))
    else:
        print(f"outputs listed: {r['outputs']}; files listed: {r['files_listed']}; matching their SHA-256: {r['files_ok']}; "
              f"different: {len(r['files_different'])}; missing: {len(r['files_missing'])}")
        print(f"pinned source paths: {r['sources_pinned_paths']}; present with the pinned bytes: {r['sources_present_ok']}; "
              f"changed since their pin: {len(r['sources_different'])}; not in this folder: {len(r['sources_absent'])}")
        print(f"rebuildable here ({len(r['rebuilds_here'])}): {', '.join(r['rebuilds_here'])}")
        print(f"ship as built, checked by SHA-256 only ({len(r['ships_as_built'])}): {', '.join(sorted(r['ships_as_built']))}")
        for k in ("files_different", "files_missing", "sources_different"):
            if r[k]:
                print(f"{k}: {', '.join(r[k])}")
        print("ok" if not bad else "FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
