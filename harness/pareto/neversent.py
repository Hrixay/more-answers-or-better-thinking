"""The "never sent" check for fresh frozen sets (Study 1b; Edith F-2).

    python3 -m harness.pareto.neversent --sets data/tasks/<set> [...] --raw data/raw --data data --out <file.json>

A set counts as fresh only if none of its items was ever sent to a model. The check matches in three ways:
- by id: every custom_id in every run's `calls.jsonl` (final records, plus the ids listed in each batch's `keys`) is compared with the
  set's item ids, and with its set id as a prefix;
- by prompt: every logged `prompt_sha256` is compared with the hash each item's prompt would get from any runner
  (`request.prompt_text` of a plain user turn, no system prompt), so an item re-used under another id is caught too;
- in the free reads: every other file under `data/` and any `--also` folder (`research/`, where the wording checks' free reads live) (the free-read, wording-check and pilot folders, plans, examples; not `data/raw`,
  whose call logs hold no prompt text, and not the set's own folder) is searched for each item's id and for its full prompt text, raw
  and JSON-escaped, so a Max-plan helper that read an item would show. A file that only names the set (a plan or spec citing its id)
  is listed separately as a mention: it shows no item was read.
Only ids, hashes and file text are read; no answer or score is opened (the call logs' answer fields are never parsed).

Lock-4 audit A5 / A13 (Edith's code items 1-3):
- It refuses (exit 2, nothing written) when `--raw` does not exist or holds no `*/calls.jsonl`: a scan of no logs proves nothing.
- It refuses (exit 2) when a run in the spend log (`--spend-log`, default `ops/spend-log.md`, read with the guard's own
  `spend_log_rows`, which also checks the rows add up) has no `<raw>/<run id>/calls.jsonl`. A row counts when its Calls cell is above
  0; a row with 0 calls is bookkeeping only (for example `smoke-2 (markers)`: two marker events appended to smoke-2's ledger) and needs
  no log of its own; a Run ID with a bracketed note is the run before the bracket (`smoke-2 (markers)` -> `smoke-2`). Logs in `--raw`
  that are not in the spend log (dry runs) are scanned too and listed.
- The record holds the commit it ran from (`git rev-parse HEAD` of this checkout, and whether the tree was clean), and for each
  call log its SHA-256, line count and path; every folder searched by its full path, and each scanned file labelled by its folder's
  full path (two `research` folders no longer collide under one name).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .request import prompt_text

ROOT = Path(__file__).resolve().parents[2]


class NothingToScan(ValueError):
    """The check would scan no call log, or the spend log names a run with no call log: refused (exit 2)."""

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".csv"}


def prompt_hashes(prompt: str) -> Set[str]:
    """The hash a runner logs for this prompt (`request.prompt_text`: system "" plus the user turn), and the plain text's hash."""
    params = {"messages": [{"role": "user", "content": prompt}]}
    return {hashlib.sha256(prompt_text(params).encode()).hexdigest(), hashlib.sha256(prompt.encode()).hexdigest()}


def load_set(set_dir: Path) -> Dict[str, object]:
    man = json.loads((set_dir / "manifest.json").read_text())
    items = [json.loads(line) for line in (set_dir / "items.jsonl").read_text().splitlines() if line.strip()]
    items_sha = hashlib.sha256((set_dir / "items.jsonl").read_bytes()).hexdigest()
    return {"set_id": man["set_id"], "manifest_items_sha256": man.get("items_sha256"), "items_sha256": items_sha, "items": items}


def logged(raw: Path) -> Dict[str, object]:
    """Every custom_id and prompt_sha256 in every run's call log, by run folder, with each log's SHA-256, line count and path. Refuses
    (NothingToScan) when `raw` does not exist or holds no */calls.jsonl."""
    if not Path(raw).is_dir():
        raise NothingToScan(f"--raw {raw} does not exist: no call log to scan, so nothing would be checked")
    logs = sorted(Path(raw).glob("*/calls.jsonl"))
    if not logs:
        raise NothingToScan(f"--raw {raw} holds no */calls.jsonl: no call log to scan, so nothing would be checked")
    out: Dict[str, object] = {}
    for log in logs:
        ids: Set[str] = set()
        hashes: Set[str] = set()
        lines = 0
        sha = hashlib.sha256()
        with open(log, "rb") as f:
            for raw_line in f:
                sha.update(raw_line)
                lines += 1
                d = json.loads(raw_line)
                if d.get("custom_id"):
                    ids.add(str(d["custom_id"]))
                if d.get("prompt_sha256"):
                    hashes.add(str(d["prompt_sha256"]))
                if isinstance(d.get("keys"), dict):
                    ids.update(str(k) for k in d["keys"])
        out[log.parent.name] = {"lines": lines, "ids": ids, "prompt_hashes": hashes, "sha256": sha.hexdigest(), "path": str(log.resolve())}
    return out


def _calls_cell(cell: str) -> Optional[int]:
    digits = cell.replace(",", "").strip()
    return int(digits) if re.fullmatch(r"\d+", digits) else None


def spend_log_runs(path: Path) -> Dict[str, object]:
    """The runs the spend log says made calls: {"runs": sorted run ids (a bracketed note dropped) whose rows' Calls add up above 0 (or
    are not a plain number), "bookkeeping_rows": Run IDs whose Calls are 0}. The rows are read with the guard's `spend_log_rows` (which
    refuses a table whose rows do not add up to its "Spent" line); the Calls column with the same table rule."""
    from .guard import spend_log_rows
    run_ids = spend_log_rows(Path(path))
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    head = next(i for i, line in enumerate(lines) if line.startswith("|") and "Run ID" in line)
    names = [c.strip() for c in lines[head].strip().strip("|").split("|")]
    run_col, calls_col = names.index("Run ID"), names.index("Calls")
    calls: Dict[str, Optional[int]] = {}
    for line in lines[head + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rid, n = cells[run_col].strip("`"), _calls_cell(cells[calls_col])
        old = calls.get(rid, 0)
        calls[rid] = None if n is None or old is None else old + n
    if set(calls) != set(run_ids):
        raise ValueError(f"{path}: the Run IDs read here differ from the guard's spend_log_rows")
    base = lambda rid: re.sub(r"\s*\(.*\)\s*$", "", rid).strip()                        # noqa: E731
    runs = sorted({base(r) for r, n in calls.items() if n is None or n > 0})
    return {"runs": runs, "bookkeeping_rows": sorted(r for r, n in calls.items() if n == 0)}


def head_commit(root: Path = ROOT) -> Dict[str, object]:
    """The commit this check ran from (`git rev-parse HEAD` of this checkout) and whether its tree was clean."""
    import subprocess
    try:
        def git(*args: str) -> str:
            return subprocess.run(["git", "-C", str(root)] + list(args), check=True, capture_output=True, text=True).stdout
        return {"commit": git("rev-parse", "HEAD").strip(), "tree_clean": git("status", "--porcelain") == ""}
    except Exception as e:                                                                   # no git: say so, never guess
        return {"commit": None, "tree_clean": None, "error": f"{type(e).__name__}"}


def _id_re(ident: str) -> "re.Pattern[str]":
    """An id as a whole token: not inside a longer id ("used-v1" is not found in "reused-v1"); a following "-" is allowed, since a
    custom_id is the item id plus "-<tag>-<NN>"."""
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(ident) + r"(?![A-Za-z0-9_])")


def other_files(data: Path, exclude: Iterable[Path]) -> List[Path]:
    ex = [p.resolve() for p in exclude]
    files = []
    for p in sorted(data.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        rp = p.resolve()
        if any(rp == e or e in rp.parents for e in ex):
            continue
        files.append(p)
    return files


def _compact(hits: List[List[object]], show: int = 5) -> Dict[str, object]:
    """A match list as its count and its first few entries (the full lists of a used set run to tens of thousands of ids)."""
    hits = sorted(hits)
    return {"count": len(hits), "first": hits[:show]}


def check(set_dirs: List[Path], raw: Path, data: Path, extra: Sequence[Path] = (), spend_log: Optional[Path] = None) -> Dict[str, object]:
    """The check. Refuses (NothingToScan) with no call log in `raw`, or (given `spend_log`) when a run the spend log says made calls has
    no `<raw>/<run id>/calls.jsonl`."""
    logs = logged(raw)
    expected: Optional[Dict[str, object]] = None
    if spend_log is not None:
        expected = spend_log_runs(spend_log)
        gone = [r for r in expected["runs"] if r not in logs]                               # type: ignore[union-attr]
        if gone:
            raise NothingToScan(f"the spend log ({spend_log}) has runs with calls but no {raw}/<run id>/calls.jsonl: {gone}")
    sets = [load_set(d) for d in set_dirs]
    texts: Dict[str, str] = {}
    roots = [Path(r).resolve() for r in [data] + list(extra)]
    for root in roots:
        for p in other_files(root, [raw] + list(set_dirs)):
            texts[f"{root}/{p.relative_to(root)}"] = p.read_text(errors="replace")         # labelled by the folder's FULL path
    result: Dict[str, object] = {"ran_from": head_commit(),
                                 "raw": str(Path(raw).resolve()),
                                 "runs_scanned": {k: {"lines": v["lines"], "ids": len(v["ids"]), "prompt_hashes": len(v["prompt_hashes"]),  # type: ignore[index, arg-type]
                                                      "sha256": v["sha256"], "path": v["path"]}                                          # type: ignore[index]
                                                  for k, v in logs.items()},
                                 "other_files_scanned": len(texts),
                                 "folders_searched": [str(r) for r in roots], "sets": {}}
    if expected is not None:
        result["spend_log"] = {"path": str(Path(spend_log).resolve()), "runs_with_calls": expected["runs"],     # type: ignore[arg-type]
                               "bookkeeping_rows": expected["bookkeeping_rows"],
                               "runs_scanned_not_in_spend_log": sorted(set(logs) - set(expected["runs"])),      # type: ignore[arg-type]
                               "every_spend_log_run_scanned": True}
    for s in sets:
        sid = str(s["set_id"])
        item_ids = {str(it["id"]) for it in s["items"]}                              # type: ignore[union-attr]
        by_id, by_prefix, by_hash = [], [], []
        for run, v in logs.items():
            ids, hashes = v["ids"], v["prompt_hashes"]                               # type: ignore[index]
            for cid in ids:
                if any(cid == i or cid.startswith(i + "-") for i in item_ids):
                    by_id.append([run, cid])
                elif cid.startswith(sid):
                    by_prefix.append([run, cid])
            for it in s["items"]:                                                    # type: ignore[union-attr]
                if prompt_hashes(str(it["prompt"])) & hashes:
                    by_hash.append([run, it["id"]])
        in_files = []
        for it in s["items"]:                                                        # type: ignore[union-attr]
            id_re = _id_re(str(it["id"]))
            prompts = {str(it["prompt"]), json.dumps(str(it["prompt"]))[1:-1]}
            for name, text in texts.items():
                if id_re.search(text) or any(p in text for p in prompts):
                    in_files.append([name, it["id"]])
        sid_re = _id_re(sid)
        set_mentions = [[name, sid] for name, text in texts.items() if sid_re.search(text)]
        result["sets"][sid] = {                                                       # type: ignore[index]
            "items": len(item_ids), "items_sha256": s["items_sha256"],
            "items_sha256_matches_manifest": s["items_sha256"] == s["manifest_items_sha256"],
            "sent_by_id": _compact(by_id), "sent_under_set_prefix": _compact(by_prefix), "sent_by_prompt_hash": _compact(by_hash),
            "in_other_data_files": _compact(in_files), "set_id_mentioned_in": _compact(set_mentions, show=20),
            "never_sent": not (by_id or by_prefix or by_hash), "never_in_other_files": not in_files}
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", type=Path, nargs="+", required=True)
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--also", type=Path, nargs="*", default=[], help="more folders to search as text, e.g. research (the free checks)")
    ap.add_argument("--spend-log", type=Path, default=Path("ops/spend-log.md"),
                    help="every run in it with calls must have <raw>/<run id>/calls.jsonl (default ops/spend-log.md)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        res = check(a.sets, a.raw, a.data, a.also, a.spend_log)
    except (NothingToScan, FileNotFoundError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    for sid, r in res["sets"].items():                                               # type: ignore[union-attr]
        print(sid, "never sent" if r["never_sent"] else "SENT", "| not in other data files" if r["never_in_other_files"]
              else "| FOUND in other data files")
    return 0 if all(r["never_sent"] for r in res["sets"].values()) else 1             # type: ignore[union-attr]


if __name__ == "__main__":
    sys.exit(main())
