"""Pilot 1's 24-step Opus-medium marker under both marking rules (Edith's E-12; the claims ledger's C-084, held for this recount). No
model call, no money; counts only (no reply text is printed or written).

    python3 -m harness.analysis.pilot1_recount --sets data/tasks/pilot-ledger-l14-v1 data/tasks/pilot-ledger-l15-v1 \\
        data/tasks/pilot-ledger-l16-v1 --replies <raw>/pilot-ledger-1/calls.jsonl --out data/pilot/pilot1-recount-e12.json

E-12 asks: under which marking rule is Pilot 1's 24-step Opus marker reported; does D-76 condition 3's format flag (a model whose
format non-compliance is above about 5%) fire under that rule; and does the shift from 0.92 to 0.94 come from one identical-repeat
chain answer accepted under Deviation 2. The paper's chain value under Deviation 2 was derived (2 x 0.94 - 0.96), assuming the pieces'
value does not change; this file measures it.

Every Opus-medium Batch try of the three Pilot 1 sets (presets l14-l16, one try per puzzle; the D-87 curve's point 7 reads the same
records, curve.read_records with only "om" opened, after prereg-lock-2) is graded by the locked scorer: a chain (1x24) by
scoring.grade_1x24, which gives the official reading under Deviation 2 (a step line repeated with the identical state is read once;
`correct`, `format_status`) and the original rule of prereg-lock-2 (any repeat fails; `correct_original`, `format_status_original`); a
pieces puzzle (24x1) by scoring.grade_24x1, which reads no step lines, so both rules give it the same reading. Per shape: right and
format-ok counts over the 25 base puzzles; pooled: the mean over base puzzles of the two shapes' mean, as curve.pilot1_points pools.
Checks (the file is refused unless every one holds): the original chain and pieces means equal the exploratory file's whole-answer
means (data/pilot/pilot-ledger-1-exploratory.json, which graded before Deviation 2), the original chain format compliance equals its
format compliance, and the pooled means equal the D-87 curve's point 7 under each rule (data/pilot/curve-ladder-l14n-1.json, original;
data/pilot/curve-ladder-l14n-1-d90.json, Deviation 2). Written once; an existing file is refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from . import curve, scoring

ROOT = Path(__file__).resolve().parents[2]
SETUP = "om"
FLAG = 0.05                       # D-76 (3): "the paper flags any model above about 5%" (non-compliance)
STAMPED = {"exploratory": ("data/pilot/pilot-ledger-1-exploratory.json", "1a5d052fd0f8958cd17a3b25c3df3ef2ee6567a7b4f37e32b26a7d26e0350e27"),
           "curve_original": ("data/pilot/curve-ladder-l14n-1.json", "1300a410d652323f9969fd2e44ff843619e72205a5e74cdf1ade01346fdc36ad"),
           "curve_d90": ("data/pilot/curve-ladder-l14n-1-d90.json", "33ab260979cffd6a720f96aeab57f6384c9e6bd49b8730d0a4eab543184120f0")}
REPLIES_SHA256 = "411c877baf3f4b399d44355c6d77126c4abd7c348d17fca194aa0e46d7f79142"   # pilot-ledger-1 calls.jsonl (LOCK-MANIFEST.md, its spend-log row)


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamped(name: str) -> dict:
    path, want = STAMPED[name]
    raw = (ROOT / path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != want:
        raise ValueError(f"{path}: SHA-256 differs from the pinned one")
    return json.loads(raw)


def grade(sets: Mapping[str, Mapping[str, object]], records: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    """One row per Opus-medium try: set, base, shape, and the reading under each rule (no reply text kept)."""
    items = {pid: (sid, it) for sid, s in sets.items() for pid, it in s["items"].items()}      # type: ignore[attr-defined]
    rows = []
    for rec in records:
        sid, it = items[str(rec["puzzle"])]
        kind = str(rec.get("kind"))
        text = str(rec.get("answer_text") or "")
        lines = int(it["params"]["lines"])                                                     # type: ignore[index]
        if int(it["depth"]) > 1:
            g = scoring.grade_1x24(text, it["chains"][0]["states"], lines, kind=kind,             # type: ignore[index]
                                   answer_only=it.get("style") == "d31-answer-only")
            rows.append({"set": sid, "base": int(it["base_index"]), "shape": "1x24", "kind": kind,
                         "d2": {"right": bool(g["correct"]), "format": str(g["format_status"])},
                         "original": {"right": bool(g["correct_original"]), "format": str(g["format_status_original"])}})
        else:
            g = scoring.grade_24x1(text, it["answer"], lines, kind=kind)                        # type: ignore[arg-type]
            r = {"right": bool(g["correct"]), "format": str(g["format_status"])}
            rows.append({"set": sid, "base": int(it["base_index"]), "shape": "24x1", "kind": kind, "d2": r, "original": dict(r)})
    return rows


def summarise(rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for rule in ("original", "d2"):
        per_shape = {}
        for shape in ("1x24", "24x1"):
            rs = [r for r in rows if r["shape"] == shape]
            answered = [r for r in rs if r["kind"] == "answered"]
            ok = sum(1 for r in answered if r[rule]["format"] == "ok")                       # type: ignore[index]
            right = sum(1 for r in rs if r[rule]["right"])                                      # type: ignore[index]
            per_shape[shape] = {"tries": len(rs), "answered": len(answered), "right": right, "mean": right / len(rs),
                                "format_ok": ok, "format_compliance": ok / len(answered),
                                "format_statuses": dict(sorted(Counter(r[rule]["format"] for r in answered).items()))}   # type: ignore[index]
        bases = sorted({(r["set"], r["base"]) for r in rows})
        val = {b: sum(1.0 for r in rows if (r["set"], r["base"]) == b and r[rule]["right"]) / 2 for b in bases}   # type: ignore[index]
        both_answered = sum(per_shape[s]["answered"] for s in per_shape)                       # type: ignore[index]
        both_ok = sum(per_shape[s]["format_ok"] for s in per_shape)                            # type: ignore[index]
        out[rule] = {"by_shape": per_shape, "pooled_mean": sum(val.values()) / len(val), "n_base": len(val),
                     "format_compliance_both_shapes": both_ok / both_answered,
                     "flag_above_5pct_non_compliance": {s: 1 - per_shape[s]["format_compliance"] > FLAG for s in per_shape}}  # type: ignore[index, operator]
    chain = [r for r in rows if r["shape"] == "1x24"]
    gained = [r for r in chain if r["d2"]["right"] and not r["original"]["right"]]                # type: ignore[index]
    lost = [r for r in chain if r["original"]["right"] and not r["d2"]["right"]]                  # type: ignore[index]
    out["shift"] = {"chain_tries_right_only_under_d2": len(gained), "chain_tries_right_only_under_original": len(lost),
                    "their_original_format_statuses": dict(sorted(Counter(r["original"]["format"] for r in gained).items())),  # type: ignore[index]
                    "their_d2_format_statuses": dict(sorted(Counter(r["d2"]["format"] for r in gained).items())),            # type: ignore[index]
                    "pieces_changed": sum(1 for r in rows if r["shape"] == "24x1" and r["d2"] != r["original"]),
                    "chain_format_ok_only_under_d2": sum(1 for r in chain if r["d2"]["format"] == "ok" != r["original"]["format"])}  # type: ignore[index]
    return out


def check(res: Mapping[str, object]) -> List[Dict[str, object]]:
    ex = stamped("exploratory")["results"][SETUP]["by_preset"]["pooled"]
    co = stamped("curve_original")["pilot1"][SETUP]["l14_to_l16"]
    cd = stamped("curve_d90")["pilot1"][SETUP]["l14_to_l16"]
    o, d = res["original"], res["d2"]                                                            # type: ignore[index]
    want = [("original chain mean = exploratory 1x24 whole answer", o["by_shape"]["1x24"]["mean"], ex["1x24"]["whole_answer"]["mean"]),
            ("original pieces mean = exploratory 24x1 whole answer", o["by_shape"]["24x1"]["mean"], ex["24x1"]["whole_answer"]["mean"]),
            ("original chain format compliance = exploratory 1x24", o["by_shape"]["1x24"]["format_compliance"], ex["1x24"]["format_compliance"]),
            ("pieces format compliance = exploratory 24x1", o["by_shape"]["24x1"]["format_compliance"], ex["24x1"]["format_compliance"]),
            ("original pooled = the curve's point 7 (original rule)", o["pooled_mean"], co["mean"]),
            ("Deviation 2 pooled = the curve's point 7 (Deviation 2)", d["pooled_mean"], cd["mean"]),
            ("base puzzles = the curve's n_base", o["n_base"], cd["n_base"])]
    out = []
    for what, ours, theirs in want:
        ok = abs(float(ours) - float(theirs)) <= 1e-9
        out.append({"what": what, "ours": ours, "stamped": theirs, "equal": ok})
        if not ok:
            raise ValueError(f"recount differs from the stamped value: {what}: {ours!r} != {theirs!r}")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sets", nargs=3, type=Path, required=True)
    ap.add_argument("--replies", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: the recount runs once and never overwrites its output")
    if not curve.lock2_is_cut():
        raise SystemExit("prereg-lock-2 is not cut: Pilot 1's Opus records stay sealed (D-86(5))")
    if sha256(a.replies) != REPLIES_SHA256:
        raise SystemExit(f"{a.replies}: not the pilot-ledger-1 calls.jsonl the lock manifest pins")
    sets = curve.load_sets(a.sets)
    if sorted(str(s["setting"]) for s in sets.values()) != sorted(curve.PILOT1_PRESETS):
        raise SystemExit(f"the sets must be Pilot 1's presets {curve.PILOT1_PRESETS}")
    rows = grade(sets, curve.read_records([a.replies], sets, [SETUP]))
    res = summarise(rows)
    git = lambda *x: subprocess.run(["git", "-C", str(ROOT), *x], check=True, capture_output=True, text=True).stdout.strip()
    doc = {"analysis": "pilot1-recount-e12", "label": "exploratory (Pilot 1, D-86(5)); a recount of a printed marker, no test",
           "question": "E-12 (Edith's check 1): the marking rule of Pilot 1's 24-step Opus marker, D-76 condition 3's format flag under "
                       "it, and the source of the shift from 0.92 to 0.94",
           "code": {"module": "harness/analysis/pilot1_recount.py", "module_sha256": sha256(Path(__file__)), "git_head": git("rev-parse", "HEAD"),
                    "git_dirty": bool(git("status", "--porcelain", "--", "harness"))},
           "inputs": {"replies_sha256": REPLIES_SHA256, "sets": {sid: s["items_sha256"] for sid, s in sorted(sets.items())},
                      "stamped": {k: {"path": p, "sha256": h} for k, (p, h) in STAMPED.items()}},
           "flag_rule": f"D-76 (3): a model whose format non-compliance is above {FLAG:.0%} is flagged",
           "result": res, "checks": check(res)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
    with open(a.out, "x") as f:
        f.write(text)
    print(f"wrote {a.out} (SHA-256 {hashlib.sha256(text.encode()).hexdigest()}); checks: {len(doc['checks'])} equal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
