"""Pilot-1's 24-step results for all three models: EXPLORATORY (D-86(5)), opened only after prereg-lock-2 was cut and posted.

    python3 -m harness.analysis.explore_pilot1 --sets data/tasks/pilot-ledger-l14-v1 data/tasks/pilot-ledger-l15-v1 \
        data/tasks/pilot-ledger-l16-v1 --replies data/raw/pilot-ledger-1/calls.jsonl --out data/pilot/pilot-ledger-1-exploratory.json

Exploratory and descriptive: no test, no decision. Nothing here changes the locked design; the D-87 curve's own 24-step markers
come from `curve.py` (point 7). It refuses to run before the tag prereg-lock-2 exists.

Scores are the analysis's official ones, read from the raw replies:
- whole answer (D-76): at 24x1 every piece right (scoring.grade_24x1); at 1x24 all 24 step lines right and the Answer line equal to
  line 24 (scoring.grade_1x24). The final-answer view scores the Answer line alone (`correct_final`; at 24x1 it equals the whole answer).
- per piece (24x1): pieces right / 24 per try.
- 1x24 step lines: (a) against the key, the share of the 24 step lines equal to the key's states; (b) the first wrong step, the line
  number of the first step line that differs from the key (all 24 right counts as no wrong step); (c) the local-slip per-step accuracy
  (scoring.local_steps: each step judged from the model's own previous line, as in the fairness check). (a) to (c) use the tries whose
  24 step lines can be placed (trace_parse step_states); the rest are counted as unplaceable. A try whose 24 lines are all right but
  whose Answer line is not counts 24 of 24 in (a) and (c).
- format compliance: the share of answered tries whose format is ok; truncations are stop reason max_tokens.
A puzzle's value is the mean over its tries; a cell's value is the mean over its puzzles. Intervals (95%): for Haiku (several tries per
puzzle) the cluster bootstrap over base puzzles of `curve.cluster_bootstrap` (2,000 resamples, seed 20261012); for one try per puzzle
the Wilson interval on whole-answer and final-answer counts, and the same cluster bootstrap for the per-piece and step-line shares.
The real-time check (setups rthm x5, rtom x1, rtsm x1 on l16 base puzzles 0-4) is shown next to the Batch tries on the same 10 puzzles.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..pareto.pilot import HAIKU, OPUS, SONNET
from . import curve, scoring, trace_parse
from .kscript import parse_custom_id

SETUPS: Dict[str, Tuple[str, str, str]] = {          # tag -> (model, effort, mode)
    "hm": (HAIKU, "medium", "batch"), "om": (OPUS, "medium", "batch"), "sm": (SONNET, "medium", "batch"),
    "rthm": (HAIKU, "medium", "realtime"), "rtom": (OPUS, "medium", "realtime"), "rtsm": (SONNET, "medium", "realtime")}
BATCH = ("hm", "om", "sm")
REALTIME = ("rthm", "rtom", "rtsm")
SHAPES = ("24x1", "1x24")


def read(paths: Sequence[Path], items: Mapping[str, Mapping[str, object]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    seen = set()
    for path in paths:
        with open(path) as f:
            for ln in f:
                if not ln.strip():
                    continue
                rec = json.loads(ln)
                if not rec.get("final") or not rec.get("custom_id"):
                    continue
                cid = parse_custom_id(str(rec["custom_id"]))
                if cid["puzzle"] not in items:
                    continue
                tag = str(cid["setup"])
                want = SETUPS.get(tag)
                if want is None or rec.get("requested_model") != want[0] or rec.get("effort") != want[1]:
                    raise ValueError(f"{rec['custom_id']}: setup {tag!r} with {rec.get('requested_model')} {rec.get('effort')}")
                if rec["custom_id"] in seen:
                    raise ValueError(f"{rec['custom_id']}: two final records")
                seen.add(rec["custom_id"])
                out.append({"custom_id": rec["custom_id"], "puzzle": cid["puzzle"], "setup": tag, "kind": rec.get("kind"),
                            "answer_text": rec.get("answer_text")})
    return out


def _local_job(args: Tuple[Mapping[str, object], List[Tuple[str, str]]]) -> Dict[str, Tuple[int, int, bool]]:
    """Rebuild one 1x24 puzzle (slow: the rulebook draw) and judge every answered try's steps locally."""
    item, tries = args
    pz = curve._puzzle(item)
    out: Dict[str, Tuple[int, int, bool]] = {}
    for cid, text in tries:
        res = curve._local(text, "answered", lambda: pz)
        out[cid] = (int(res["steps_judged"]), int(res["steps_right"]), bool(res["placeable"]))
    return out


def score(records: Sequence[Mapping[str, object]], items: Mapping[str, Mapping[str, object]], workers: int) -> Dict[str, Dict[str, object]]:
    """Every try's scores, by custom id."""
    tries: Dict[str, Dict[str, object]] = {}
    local_in: Dict[str, List[Tuple[str, str]]] = {}
    for rec in records:
        it = items[str(rec["puzzle"])]
        kind = str(rec["kind"])
        text = str(rec.get("answer_text") or "")
        lines = int(it["params"]["lines"])                                                  # type: ignore[index]
        row: Dict[str, object] = {"setup": rec["setup"], "puzzle": rec["puzzle"], "kind": kind}
        if int(it["depth"]) > 1:
            states = [tuple(s) for s in it["chains"][0]["states"]]                       # type: ignore[index]
            g = scoring.grade_1x24(text, states, lines, kind=kind)
            row.update(shape="1x24", right=bool(g["correct"]), final_right=bool(g["correct_final"]), format_ok=g["format_status"] == "ok")
            steps = trace_parse.parse_trace(text, lines, len(states)).step_states if kind == "answered" else None
            if steps is not None:
                match = [tuple(s) == k for s, k in zip(steps, states)]
                row.update(placeable=True, lines_right=sum(match), first_wrong=next((i for i, m in enumerate(match, 1) if not m), None))
                local_in.setdefault(str(rec["puzzle"]), []).append((str(rec["custom_id"]), text))
            else:
                row.update(placeable=False)
        else:
            g = scoring.grade_24x1(text, it["answer"], lines, kind=kind)                    # type: ignore[arg-type]
            row.update(shape="24x1", right=bool(g["correct"]), final_right=bool(g["correct"]), format_ok=g["format_status"] == "ok",
                       pieces_right=int(g["pieces_right"]), pieces=len(it["answer"]))      # type: ignore[arg-type]
        tries[str(rec["custom_id"])] = row
    jobs = [(items[pid], ts) for pid, ts in sorted(local_in.items())]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_local_job, jobs):
            for cid, (judged, right, placeable) in res.items():
                tries[cid].update(steps_judged=judged, steps_right=right, local_placeable=placeable)
    return tries


def _share(per_puzzle: Dict[Tuple[str, int], Optional[float]], strata: List[List[Tuple[str, int]]], name: str) -> Dict[str, object]:
    vals = {k: v for k, v in per_puzzle.items() if v is not None}

    def stat(sample: List[object]) -> Optional[float]:
        xs = [vals[c] for c in sample if c in vals]                                         # type: ignore[index]
        return sum(xs) / len(xs) if xs else None
    allc = [c for s in strata for c in s]
    lo, hi = curve.cluster_bootstrap(strata, stat, name)
    return {"mean": stat(allc), "ci95": [lo, hi], "n_puzzles": sum(1 for c in allc if c in vals)}


def cell(tries: Sequence[Mapping[str, object]], items: Mapping[str, Mapping[str, object]], shape: str, name: str) -> Dict[str, object]:
    """One setup x one group of puzzles x one shape."""
    by: Dict[Tuple[str, int], List[Mapping[str, object]]] = {}
    for t in tries:
        it = items[str(t["puzzle"])]
        by.setdefault((str(it["set"]), int(it["base_index"])), []).append(t)
    strata: Dict[str, List[Tuple[str, int]]] = {}
    for k in sorted(by):
        strata.setdefault(k[0], []).append(k)
    st = list(strata.values())
    n_tries = len(tries)
    answered = [t for t in tries if t["kind"] == "answered"]
    one_try = all(len(v) == 1 for v in by.values())

    def mean_of(field: str) -> Dict[Tuple[str, int], Optional[float]]:
        return {k: sum(1 for t in v if t[field]) / len(v) for k, v in by.items()}
    out: Dict[str, object] = {"puzzles": len(by), "tries": n_tries, "tries_per_puzzle": sorted({len(v) for v in by.values()}),
                              "answered": len(answered), "truncated": sum(1 for t in tries if t["kind"] == "truncated"),
                              "other_unanswered": sorted({str(t["kind"]) for t in tries if t["kind"] not in ("answered", "truncated")}),
                              "format_compliance": (sum(1 for t in answered if t["format_ok"]) / len(answered)) if answered else None}
    for field, label in (("right", "whole_answer"), ("final_right", "final_answer")):
        row = _share(mean_of(field), st, f"{name}:{label}")
        if one_try:
            x = sum(1 for t in tries if t[field])
            row.update(right=x, ci95=list(curve.wilson(x, n_tries)), interval="wilson")
        else:
            row["interval"] = "cluster bootstrap"
        out[label] = row
    if shape == "24x1":
        out["per_piece"] = _share({k: sum(int(t.get("pieces_right") or 0) / int(t["pieces"]) for t in v) / len(v) for k, v in by.items()},
                                  st, f"{name}:piece")
    else:
        placed = {k: [t for t in v if t.get("placeable")] for k, v in by.items()}
        out["unplaceable"] = sum(1 for t in answered if not t.get("placeable"))
        out["step_lines_vs_key"] = _share({k: (sum(int(t["lines_right"]) for t in v) / (24 * len(v)) if v else None)
                                           for k, v in placed.items()}, st, f"{name}:lines")
        judged = {k: (sum(int(t.get("steps_judged") or 0) for t in v), sum(int(t.get("steps_right") or 0) for t in v)) for k, v in by.items()}
        out["local_per_step"] = _share({k: (r / j if j else None) for k, (j, r) in judged.items()}, st, f"{name}:local")
        firsts = sorted(int(t["first_wrong"]) for v in placed.values() for t in v if t.get("first_wrong") is not None)
        n_placed = sum(len(v) for v in placed.values())
        out["first_wrong_step"] = {"placeable_tries": n_placed, "all_24_lines_right": n_placed - len(firsts),
                                   "median": (firsts[len(firsts) // 2] if len(firsts) % 2 else (firsts[len(firsts) // 2 - 1] + firsts[len(firsts) // 2]) / 2) if firsts else None,
                                   "mean": (sum(firsts) / len(firsts)) if firsts else None,
                                   "by_quarter": {q: sum(1 for f in firsts if lo <= f <= hi) for q, lo, hi in
                                                  (("1-6", 1, 6), ("7-12", 7, 12), ("13-18", 13, 18), ("19-24", 19, 24))}}
    return out


def report(tries: Dict[str, Dict[str, object]], items: Mapping[str, Mapping[str, object]], presets: Mapping[str, str]) -> Dict[str, object]:
    res: Dict[str, object] = {}
    groups = [(p, [s for s, q in presets.items() if q == p]) for p in sorted(set(presets.values()))] + [("pooled", list(presets))]
    for setup in BATCH:
        per: Dict[str, object] = {}
        for label, sids in groups:
            per[label] = {shape: cell([t for t in tries.values() if t["setup"] == setup and t["shape"] == shape
                                       and items[str(t["puzzle"])]["set"] in sids], items, shape, f"{setup}:{label}:{shape}")
                          for shape in SHAPES}
        res[setup] = {"model": SETUPS[setup][0], "effort": SETUPS[setup][1], "mode": "batch", "by_preset": per}
    rt_puzzles = {str(t["puzzle"]) for t in tries.values() if t["setup"] in REALTIME}
    side: Dict[str, object] = {}
    for rt, b in zip(REALTIME, BATCH):
        side[SETUPS[b][0]] = {mode: {shape: cell([t for t in tries.values() if t["setup"] == tag and t["shape"] == shape
                                                  and str(t["puzzle"]) in rt_puzzles], items, shape, f"{tag}:rt10:{shape}")
                                     for shape in SHAPES} for mode, tag in (("realtime", rt), ("batch_same_puzzles", b))}
    res["realtime_vs_batch"] = {"puzzles": sorted(rt_puzzles), "by_model": side}
    return res


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", type=Path, required=True)
    ap.add_argument("--replies", nargs="+", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    a = ap.parse_args(argv)
    if not curve.lock2_is_cut():
        raise SystemExit(f"pilot-1's Opus and Sonnet records stay sealed until the tag {curve.LOCK2_TAG} exists (D-86(5))")
    sets = curve.load_sets(a.sets)
    items: Dict[str, Dict[str, object]] = {}
    presets: Dict[str, str] = {}
    for sid, s in sets.items():
        presets[sid] = str(s["setting"])
        for pid, it in s["items"].items():                                                  # type: ignore[attr-defined]
            items[pid] = dict(it, set=sid)
    tries = score(read(a.replies, items), items, a.workers)
    res = {"status": "EXPLORATORY (D-86(5)): opened after prereg-lock-2; no test, no decision",
           "sets": {sid: {"preset": presets[sid], "items_sha256": s["items_sha256"]} for sid, s in sets.items()},
           "seed": curve.SEED, "draws": curve.DRAWS, "results": report(tries, items, presets)}
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(f"wrote {a.out}: {len(tries)} tries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
