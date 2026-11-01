"""The preset choice (D-36 point 4 with its fallback ladder, D-48 rows 18 and 19, D-62 tie-break), from the pilot's
Haiku-medium tries ONLY.

    python3 -m harness.analysis.choose_preset extract --table pilot_compact_table.csv --out haiku_medium_only.csv
    python3 -m harness.analysis.choose_preset choose --table haiku_medium_only.csv --sets DIR1 DIR2 ... \
        --replies data/raw/<run-id>/calls.jsonl --out preset-choice.json

(Without a sub-command the arguments are read as `choose`.) Write the pick (and commit it) before anyone opens the other
models' pilot numbers. `extract` copies the Haiku-medium rows of a compact table into a new CSV with the same columns and
nothing else, so the pick can be made from that file before the Opus and Sonnet numbers are looked at. `choose` REFUSES a
table that holds any row that is not Haiku-medium unless `--allow-other-rows` is passed; with that flag it filters to
Haiku-medium before any computation, and nothing else is kept, counted, printed or returned. The sha256 of the
Haiku-medium rows it used (each row serialised as JSON with sorted keys, the lines sorted, joined by newlines) goes into the
output; it is the same whether the rows came from the full table or from the extract. The extract's `right` column is the
pilot grader's (for ledger sets the official D-76 score, the same scorers) and is still NOT used for any try of a ledger set: `choose` scores those from the replies
(`--replies`, below) whether it is given the extract or the full table, and refuses to choose without them.

Per preset (the frozen set manifest's `setting`; set ids come from the custom_id, see kscript.parse_custom_id):
a puzzle's single-try accuracy is the mean of its Haiku-medium tries' scores. A try's score (D-76: the official trace score):
  every try of a set that is not a ledger set: `right` from the table, as before;
  24x1 of a ledger set: every piece right, read from the raw reply (`--replies`) by `trace_parse.parse_pieces` (scoring.grade_24x1),
          the same reader the analysis uses (Edith R3), so the pick and the analysis cannot disagree on a reply's format;
  1x24 of a ledger set: the OFFICIAL trace score, read from the raw reply (`--replies`, the git-ignored call log) by the fixed
          parser (`trace_parse`, via scoring.grade_1x24): right only if all 24 step lines equal the key's states and the Answer
          line equals line 24; a try whose format is not ok is wrong. The `right` column is not used for these tries (the pilot's
          grader writes the final answer there). An item frozen with the answer-only prompt (style d31-answer-only, D-36(5)) is
          scored by its final answer. Only FINAL Haiku-medium records are kept from the call log; every other record is dropped as
          it is read, and nothing from it is kept, counted or returned.
A try that did not answer (a blank `right` for a set of another family; a `kind` other than answered for a ledger set: refusal,
truncation, empty reply, anything not graded) counts as WRONG and the try stays in; nothing is dropped. The preset's score is the
MEDIAN of its puzzles' accuracies, pooled across both shapes (not the mean; the mean is only reported). Also reported:
the per-shape medians, `shape_gap` (the absolute difference of the two per-shape medians) and `shape_gap_flag` (gap strictly
above 0.30), the mean, the numbers of puzzles and tries, and Haiku-medium's 1x24 format compliance (D-76: format compliance; the share of
answered trace-scored tries whose reply parses: answer-only items are not trace-scored and are left out of it, and so are tries that
did not answer; 24x1 tries never enter it) and, apart from it, the 24x1 format compliance of a ledger set (`format_compliance_24x1`:
the share of answered 24x1 tries whose Answer line parses, same denominator rule). Real-time tries (`rt` setups, a separate check) are left out.

The ladder (all comparisons exact, in fractions):
  tier 1  presets with a score in [0.25, 0.50]: pick the one closest to 0.375;
  tier 2  else presets in [0.15, 0.60]: pick the one closest to 0.375 (`band_miss` = how far outside [0.25, 0.50]);
  tier 3  else no binding pick (`pick` is None): every preset above 0.60 sets `extra_rung_needed` (the spare rung l17 runs
          only on the user's go); every preset below 0.15, or presets on both sides of the 0.15 to 0.60 window with none
          inside it, sets `outside_15_60_return_to_user` (there is no easier rung).
`band_miss` is 0.0 in tier 1. A tie on distance (the two distances agree after rounding each to 0.001) goes first to the preset with
FEWER STEPS (D-86: "ties to fewer steps"), then to the preset with FEWER distinct rule kinds (from the frozen items' `params`), then
to the shorter mean prompt (characters), then to the preset name. The step count only separates presets of different lengths, such
as the ladder's l14n4, l14n6, l14n8, l14n12 and l14n16; presets of one length (l14, l15, l16 at 24 steps) tie on it, so their order
is the K2 order as before. A preset's step count is its items' `params.total_steps` (else width times depth); when a tied preset has
no single step count (none recorded, or items of different lengths) the step count is not used for that tie.

Puzzle length (D-86). The ladder sets have N-step items: shapes "Nx1" and "1xN". Everything above holds at any N: a 1xN try is the
official trace score (all N step lines right, the Answer line equal to line N), an Nx1 try is every piece right, and the per-shape
medians are keyed by the shape in the custom_id ("1x6", "6x1"). The output fields keep their 24-step names (`score_1x24`,
`format_compliance_1x24` for the chain shape at any N, `format_compliance_24x1` for the pieces shape at any N). The ladder's
Opus-medium and Sonnet-medium tries are never read here: only Haiku-medium rows and records are kept.

Rule kinds of an item: `params.kinds` if present; for a code item `vc_kinds` and `ro_kinds` together; for a digit item the
rule kinds whose count `n_<kind>` is above zero (affine, table, pair, shuffle).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import scoring
from .kscript import parse_custom_id

MODEL = "claude-haiku-5-5"
EFFORT = "medium"
BAND_LOW, BAND_HIGH, TARGET = Fraction(1, 4), Fraction(1, 2), Fraction(3, 8)       # tier 1: [0.25, 0.50], target 0.375
WIDE_LOW, WIDE_HIGH = Fraction(3, 20), Fraction(3, 5)                              # tier 2: [0.15, 0.60]
SHAPE_GAP_FLAG_ABOVE = Fraction(3, 10)                                             # gap strictly above 0.30 is flagged
TIE_UNIT = Fraction(1, 1000)                                                       # distances are compared in tenths of a point
DIGIT_KINDS = ("affine", "table", "pair", "shuffle")
TRACE_FAMILY = "ledger"                                                            # the family whose tries are scored from the replies (D-76)
ANSWER_ONLY_STYLE = "d31-answer-only"
LADDER_PREFIX = "l14n"                                                             # the D-86 length-ladder presets l14n4..l14n16
PIECES_SHAPE = "24x1"                                                              # the 24-step pieces shape; any Nx1 is read the same way
RULE_TEXT = ("Haiku-medium tries only (no other model's numbers are read). Puzzle accuracy = mean of `right` over its "
             "tries (blank = wrong). Preset score = MEDIAN of its puzzle accuracies (not the mean), both shapes pooled. "
             "Tier 1: among presets with a score in [0.25, 0.50], pick the one closest to 0.375. Tier 2: if none, among presets "
             "in [0.15, 0.60], pick the one closest to 0.375 and report band_miss (the distance outside [0.25, 0.50]). Tier 3: "
             "if none, there is no binding pick (pick = null): if every preset is above 0.60, set extra_rung_needed (the spare "
             "rung l17 runs only on the user's go; 24-step presets only); if every preset is below 0.15, or the presets lie on both sides of "
             "the 0.15 to 0.60 window with none inside it, set outside_15_60_return_to_user (there is no easier rung). "
             "For the D-86 length ladder (presets l14n4 to l14n16) there is no further rung: tier 3 always sets "
             "outside_15_60_return_to_user and never extra_rung_needed. "
             "K2 tie-break: two presets are tied when their distances to 0.375, each rounded to 0.001, are equal; the tie "
             "goes to fewer steps (D-86; presets of the same length tie on it), then to fewer distinct rule kinds, then to the "
             "shorter mean prompt. shape_gap is the absolute difference of "
             "the two per-shape medians; shape_gap_flag is set when it is strictly above 0.30 (information only). "
             "Try scores (D-76: the official trace score): a 1x24 try of a ledger set is right only if its reply parses under the fixed rules "
             "and all 24 step lines equal the key (the Answer line equal to line 24), read from the raw reply; a try whose "
             "format is not ok is wrong (an answer-only item is scored by its final answer). A 24x1 try of a ledger set is right only "
             "if every piece is right, read from the raw reply by the same parser (Edith R3). Sets of other families use `right` as before. "
             "At N steps (D-86) every 1x24 above means the 1xN chain and every 24x1 the Nx1 pieces, in this text and in the field "
             "names (score_1x24, format_compliance_1x24, format_compliance_24x1, ...); each preset row gives its length as n_steps.")


def is_haiku_medium(row: Mapping[str, object]) -> bool:
    return row.get("requested_model") == MODEL and row.get("effort") == EFFORT


def read_table(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """All rows of a compact table with its column names. Only the model and effort columns decide what is Haiku-medium."""
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        cols = list(rd.fieldnames or [])
        for need in ("requested_model", "effort"):
            if need not in cols:
                raise ValueError(f"{path}: the table has no `{need}` column")
        return cols, [dict(r) for r in rd]


def load_haiku_medium_rows(path: Path) -> List[Dict[str, str]]:
    """Read the compact table, keeping only Haiku-medium rows."""
    return [r for r in read_table(path)[1] if is_haiku_medium(r)]


def extract_haiku_medium(table: Path, out: Path) -> Tuple[int, int]:
    """Write the Haiku-medium rows of `table` to `out` (same columns, same order) and nothing else. Returns (kept, left out)."""
    cols, rows = read_table(table)
    keep = [r for r in rows if is_haiku_medium(r)]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(keep)
    return len(keep), len(rows) - len(keep)


def rows_sha256(rows: Iterable[Mapping[str, object]]) -> str:
    lines = sorted(json.dumps(dict(r), sort_keys=True, ensure_ascii=False, default=str) for r in rows)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def rule_kinds(params: Mapping[str, object]) -> set:
    if "kinds" in params:
        return set(params["kinds"])  # type: ignore[call-overload]
    if "vc_kinds" in params or "ro_kinds" in params:
        return set(params.get("vc_kinds") or ()) | set(params.get("ro_kinds") or ())  # type: ignore[call-overload]
    return {k for k in DIGIT_KINDS if params.get("n_" + k, 0)}  # type: ignore[operator]


def item_steps(item: Mapping[str, object]) -> Optional[int]:
    """How many steps a frozen item has: `params.total_steps`, else width times depth, else None."""
    params = item.get("params") or {}
    if params.get("total_steps") is not None:                       # type: ignore[union-attr]
        return int(params["total_steps"])                           # type: ignore[index]
    if item.get("width") is not None and item.get("depth") is not None:
        return int(item["width"]) * int(item["depth"])              # type: ignore[call-overload]
    return None


def load_set_info(folder: Path) -> Dict[str, object]:
    """Read a frozen set folder (manifest.json + items.jsonl) without re-verifying it. `steps` lists the items' step counts (D-86)."""
    folder = Path(folder)
    man = json.loads((folder / "manifest.json").read_text())
    items = [json.loads(ln) for ln in (folder / "items.jsonl").read_text().splitlines() if ln.strip()]
    kinds: set = set()
    keys: Dict[str, Dict[str, object]] = {}
    steps: set = set()
    for it in items:
        kinds |= rule_kinds(it.get("params") or {})
        n = item_steps(it)
        if n is not None:
            steps.add(n)
        if man["family"] == TRACE_FAMILY and it.get("width") == 1 and int(it.get("depth") or 1) > 1:     # the 1xN key traces
            states = it["chains"][0]["states"]
            keys[it["id"]] = {"shape": scoring.chain_shape(len(states)), "states": states, "lines": int(it["params"]["lines"]),
                              "answer_only": it.get("style") == ANSWER_ONLY_STYLE}
        elif man["family"] == TRACE_FAMILY:                                                               # the Nx1 key answers
            keys[it["id"]] = {"shape": scoring.pieces_shape(len(it["answer"])), "pieces": it["answer"],
                              "lines": int(it["params"]["lines"]), "answer_only": False}
    return {"set_id": man["set_id"], "setting": man["setting"], "family": man["family"],
            "items_sha256": man.get("items_sha256"), "puzzles": {it["id"] for it in items}, "kinds": kinds,
            "prompt_chars": [len(it["prompt"]) for it in items], "keys": keys, "steps": sorted(steps)}


def read_haiku_medium_replies(paths: Iterable[Path]) -> List[Dict[str, object]]:
    """The FINAL Haiku-medium records of raw call logs (JSON lines), with only the fields the trace score needs. Every other record is
    dropped as soon as it is read."""
    out: List[Dict[str, object]] = []
    for path in paths:
        with open(path) as f:
            for ln in f:
                if not ln.strip():
                    continue
                rec = json.loads(ln)
                if rec.get("final") and is_haiku_medium(rec):
                    out.append({k: rec.get(k) for k in ("custom_id", "requested_model", "effort", "kind", "answer_text")})
    return out


def trace_grades(records: Iterable[Mapping[str, object]], sets: Sequence[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """{custom_id: {"right": 1 / 0, "format_status": ..., "kind": ..., "answer_only": True / False, "shape": ...}} for the Haiku-medium
    records of ledger items: at 1x24 (1xN) the official D-76 trace score (scoring.grade_1x24; the final answer for an answer-only item),
    at 24x1 (Nx1) every piece right (scoring.grade_24x1, Edith R3). Records of other models, efforts or items are skipped: an Opus or
    Sonnet reply is never graded here."""
    keys: Dict[str, Mapping[str, object]] = {}
    for st in sets:
        keys.update(st.get("keys") or {})                                     # type: ignore[arg-type]
    out: Dict[str, Dict[str, object]] = {}
    for rec in records:
        if not is_haiku_medium(rec):
            continue
        cid = str(rec["custom_id"])
        key = keys.get(str(parse_custom_id(cid)["puzzle"]))
        if key is None:
            continue
        answer_only = scoring.answer_only_flag(key["answer_only"])
        if scoring.is_pieces_shape(key["shape"]):                            # Nx1: every piece right, read by trace_parse.parse_pieces
            g = scoring.grade_24x1(str(rec.get("answer_text") or ""), key["pieces"], int(key["lines"]),   # type: ignore[arg-type]
                                   kind=str(rec.get("kind")))
        else:
            g = scoring.grade_1x24(str(rec.get("answer_text") or ""), key["states"], int(key["lines"]),  # type: ignore[arg-type]
                                   kind=str(rec.get("kind")), answer_only=answer_only)
        out[cid] = {"right": int(bool(g["correct"])), "format_status": g["format_status"], "kind": rec.get("kind"),
                    "answer_only": answer_only, "shape": key["shape"]}
    return out


def right_value(row: Mapping[str, object]) -> int:
    return 1 if str(row.get("right", "")).strip().lower() in ("1", "1.0", "true") else 0


def _median(xs: Sequence[Fraction]) -> Fraction:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _thousandths(x: Fraction) -> int:
    """x rounded to the nearest 0.001, halves up, as a whole number of thousandths."""
    return math.floor(x * 1000 + Fraction(1, 2))


def _tier(score: Fraction) -> int:
    if BAND_LOW <= score <= BAND_HIGH:
        return 1
    return 2 if WIDE_LOW <= score <= WIDE_HIGH else 3


def _is_ladder(scored: List[Dict[str, object]]) -> bool:
    """True for the D-86 length ladder: every preset is an l14n* preset or has a length other than 24."""
    return bool(scored) and all(str(p["preset"]).startswith(LADDER_PREFIX) or p.get("n_steps") not in (None, 24) for p in scored)


def _pick(scored: List[Dict[str, object]]) -> Dict[str, object]:
    """The ladder over presets that have rows (see the module text). Returns `pick` (None when no binding pick) and the flags."""
    flags = {"extra_rung_needed": False, "outside_15_60_return_to_user": False}
    for tier in (1, 2):
        pool = [p for p in scored if p["tier"] == tier]
        if not pool:
            continue
        best = min(p["distance_key"] for p in pool)                       # type: ignore[type-var]
        tied = [p for p in pool if p["distance_key"] == best]
        by_steps = all(p.get("n_steps") is not None for p in tied)       # D-86: fewer steps first, when every tied preset has one length
        tied.sort(key=lambda p: (p["n_steps"] if by_steps else 0, p["n_rule_kinds"], p["mean_prompt_chars"], p["preset"]))
        chosen = tied[0]
        s = Fraction(chosen["score_exact"])                                # type: ignore[arg-type]
        miss = Fraction(0) if tier == 1 else (BAND_LOW - s if s < BAND_LOW else s - BAND_HIGH)
        pick = {"preset": chosen["preset"], "score": chosen["score"], "tier": tier, "in_band": tier == 1,
                "band_miss": float(miss), "no_preset_in_band": tier != 1,
                "tied_with": sorted(p["preset"] for p in tied if p is not chosen), "tie_broken": len(tied) > 1,
                "shape_gap": chosen["shape_gap"], "shape_gap_flag": chosen["shape_gap_flag"]}
        return dict(flags, pick=pick, tier=tier)
    scores = [Fraction(p["score_exact"]) for p in scored]                  # type: ignore[arg-type]
    if all(x > WIDE_HIGH for x in scores) and not _is_ladder(scored):     # the D-86 ladder has no further rung (Edith L3-1)
        flags["extra_rung_needed"] = True
    else:
        flags["outside_15_60_return_to_user"] = True                       # all below 0.15, or on both sides of the window
    return dict(flags, pick=None, tier=3)


def _try_score(r: Mapping[str, object], pid: Mapping[str, object], family: object,
               trace: Optional[Mapping[str, Mapping[str, object]]], used_trace: Dict[str, Mapping[str, object]]) -> int:
    """One try's score: for a ledger set, read from its reply by the analysis parser (the D-76 trace score at 1x24, every piece right at
    24x1, Edith R3); `right` for sets of other families."""
    if family != TRACE_FAMILY:
        return right_value(r)
    cid = str(r["custom_id"])
    if trace is not None and cid in trace:
        used_trace[cid] = trace[cid]
        return int(bool(trace[cid]["right"]))
    if r.get("kind") not in (None, "", "answered"):
        return 0                                                       # no answer: wrong, and the try stays in
    raise ValueError(f"{cid}: a ledger try is scored from its reply (D-76) and its reply was not given; pass the call log with --replies")


def _one_length(steps: Iterable[int]) -> Optional[int]:
    """A preset's step count: the one length its items share, or None (no length recorded, or items of different lengths)."""
    s = set(steps)
    return next(iter(s)) if len(s) == 1 else None


def choose_preset(rows: Iterable[Mapping[str, object]], sets: Sequence[Mapping[str, object]],
                  include_realtime: bool = False, trace: Optional[Mapping[str, Mapping[str, object]]] = None) -> Dict[str, object]:
    """The preset choice from table rows (any models: only Haiku-medium rows are looked at) and loaded set infos. `trace` is
    `trace_grades(...)` from the Haiku-medium replies; it is needed when a ledger set has answered tries (either shape)."""
    used = [dict(r) for r in rows if is_haiku_medium(r)]      # the filter comes first; nothing else is kept
    if not include_realtime:
        used = [r for r in used if not parse_custom_id(str(r["custom_id"]))["realtime"]]
    used_trace: Dict[str, Mapping[str, object]] = {}
    preset_of: Dict[str, str] = {}
    info: Dict[str, Dict[str, object]] = {}
    for s in sets:
        preset_of[str(s["set_id"])] = str(s["setting"])
        p = info.setdefault(str(s["setting"]), {"family": s["family"], "set_ids": [], "kinds": set(), "chars": [],
                                                "puzzles": set(), "steps": set()})
        p["set_ids"].append(s["set_id"])                       # type: ignore[attr-defined]
        p["kinds"] |= set(s["kinds"])                          # type: ignore[operator,arg-type]
        p["chars"] += list(s["prompt_chars"])                  # type: ignore[operator,arg-type]
        p["puzzles"] |= set(s["puzzles"])                      # type: ignore[operator,arg-type]
        p["steps"] |= set(s.get("steps") or ())                # type: ignore[operator,arg-type]
    tries: Dict[str, Dict[str, Dict[str, List[int]]]] = {}     # preset -> shape -> puzzle -> rights
    for r in used:
        pid = parse_custom_id(str(r["custom_id"]))
        preset = preset_of.get(str(pid["set_id"]))
        if preset is None:
            raise ValueError(f"set {pid['set_id']!r} is not among the --sets given")
        if pid["puzzle"] not in info[preset]["puzzles"]:       # type: ignore[operator]
            raise ValueError(f"puzzle {pid['puzzle']!r} is not in its frozen set")
        score = _try_score(r, pid, info[preset]["family"], trace, used_trace)
        tries.setdefault(preset, {}).setdefault(str(pid["shape"]), {}).setdefault(str(pid["puzzle"]), []).append(score)
    fmt: Dict[str, List[int]] = {}                             # preset -> [answered trace-scored 1xN tries, of which format ok]
    fmt_24x1: Dict[str, List[int]] = {}                        # preset -> [answered reply-scored Nx1 tries, of which format ok]
    for cid, g in used_trace.items():
        preset = preset_of[str(parse_custom_id(cid)["set_id"])]
        if scoring.is_pieces_shape(g.get("shape")):
            c = fmt_24x1.setdefault(preset, [0, 0])            # 24x1: its own count, never in the 1x24 format compliance
        elif scoring.answer_only_flag(g.get("answer_only")):
            continue                                           # scored by the final answer: not in the 1x24 format compliance
        else:
            c = fmt.setdefault(preset, [0, 0])
        if g.get("kind") == "answered":
            c[0] += 1
            c[1] += g.get("format_status") == "ok"
    scored: List[Dict[str, object]] = []
    for preset in sorted(tries):
        shape_acc = {sh: [Fraction(sum(v), len(v)) for v in pz.values()] for sh, pz in tries[preset].items()}
        accs = [a for v in shape_acc.values() for a in v]
        score = _median(accs)
        shape_medians = {sh: _median(v) for sh, v in sorted(shape_acc.items())}
        gap = (max(shape_medians.values()) - min(shape_medians.values())) if len(shape_medians) >= 2 else None
        i = info[preset]
        chars = i["chars"]
        dist = abs(score - TARGET)
        scored.append({
            "preset": preset, "family": i["family"], "set_ids": sorted(i["set_ids"]),    # type: ignore[arg-type]
            "n_puzzles": len(accs), "n_tries": sum(len(v) for pz in tries[preset].values() for v in pz.values()),
            "score": float(score), "score_exact": str(score), "mean": float(sum(accs) / len(accs)),
            "shape_medians": {sh: float(m) for sh, m in shape_medians.items()},
            "shape_n_puzzles": {sh: len(v) for sh, v in sorted(shape_acc.items())},
            "shape_gap": None if gap is None else float(gap), "shape_gap_exact": None if gap is None else str(gap),
            "shape_gap_flag": gap is not None and gap > SHAPE_GAP_FLAG_ABOVE,
            "tier": _tier(score), "in_band": _tier(score) == 1, "distance": float(dist),
            "distance_key": _thousandths(dist),                                            # thousandths, for the K2 tie
            "n_rule_kinds": len(i["kinds"]), "rule_kinds": sorted(i["kinds"]),             # type: ignore[arg-type]
            "n_steps": _one_length(i["steps"]),                                             # type: ignore[arg-type]
            "mean_prompt_chars": sum(chars) / len(chars),                                  # type: ignore[arg-type]
            "score_1x24": "trace (D-76)" if i["family"] == TRACE_FAMILY else "right column",
            "n_answered_1x24_traced": fmt.get(preset, [0, 0])[0],
            "format_compliance_1x24": (fmt[preset][1] / fmt[preset][0]) if fmt.get(preset, [0, 0])[0] else None,
            "n_answered_24x1_read": fmt_24x1.get(preset, [0, 0])[0],
            "format_compliance_24x1": (fmt_24x1[preset][1] / fmt_24x1[preset][0]) if fmt_24x1.get(preset, [0, 0])[0] else None})
    if not scored:
        raise ValueError("no Haiku-medium rows to choose from")
    ladder = _pick(scored)
    empty = []
    for preset in sorted(set(info) - set(tries)):                  # sets given but no Haiku-medium rows: listed, never silent
        i = info[preset]
        chars = i["chars"]
        empty.append({"preset": preset, "family": i["family"], "set_ids": sorted(i["set_ids"]),   # type: ignore[arg-type]
                      "n_puzzles": 0, "n_tries": 0, "score": None, "score_exact": None, "mean": None,
                      "shape_medians": {}, "shape_n_puzzles": {}, "shape_gap": None, "shape_gap_exact": None,
                      "shape_gap_flag": False, "tier": None, "in_band": False, "distance": None, "distance_key": None,
                      "n_rule_kinds": len(i["kinds"]), "rule_kinds": sorted(i["kinds"]),          # type: ignore[arg-type]
                      "n_steps": _one_length(i["steps"]),                                         # type: ignore[arg-type]
                      "mean_prompt_chars": (sum(chars) / len(chars)) if chars else None,         # type: ignore[arg-type]
                      "score_1x24": "trace (D-76)" if i["family"] == TRACE_FAMILY else "right column",
                      "n_answered_1x24_traced": 0, "format_compliance_1x24": None,
                      "n_answered_24x1_read": 0, "format_compliance_24x1": None})
    trace_rows = [{"custom_id": c, "right": int(bool(g["right"])), "format_status": g.get("format_status")} for c, g in used_trace.items()]
    return {"rule": RULE_TEXT, "model": MODEL, "effort": EFFORT, "input_sha256": rows_sha256(used), "n_rows": len(used),
            "trace_sha256": rows_sha256(trace_rows), "n_trace_scored": len(trace_rows),
            "include_realtime": include_realtime,
            "sets": {str(s["set_id"]): s.get("items_sha256") for s in sets},
            "presets_without_rows": [e["preset"] for e in empty],
            "presets": scored + empty, "pick": ladder["pick"], "tier": ladder["tier"],
            "extra_rung_needed": ladder["extra_rung_needed"],
            "outside_15_60_return_to_user": ladder["outside_15_60_return_to_user"]}


def summary(res: Mapping[str, object]) -> str:
    lines = [f"Haiku-medium only; {res['n_rows']} rows; input sha256 {res['input_sha256']}", ""]
    lines.append(f"{'preset':<10}{'puzzles':>8}{'tries':>7}{'score':>8}{'mean':>8}  {'kinds':>5}{'chars':>9}  "
                 f"{'tier':>4}  shape medians, gap")
    for p in res["presets"]:  # type: ignore[attr-defined]
        if p["score"] is None:
            lines.append(f"{p['preset']:<10}{0:>8}{0:>7}{'None':>8}{'None':>8}  {p['n_rule_kinds']:>5}"
                         f"{(p['mean_prompt_chars'] or 0):>9.0f}  {'-':>4}  no Haiku-medium rows (n = 0, score None)")
            continue
        shapes = ", ".join(f"{sh}={m:.3f}" for sh, m in p["shape_medians"].items())
        gap = "" if p["shape_gap"] is None else f", gap {p['shape_gap']:.3f}" + (" [GAP ABOVE 0.30]" if p["shape_gap_flag"] else "")
        lines.append(f"{p['preset']:<10}{p['n_puzzles']:>8}{p['n_tries']:>7}{p['score']:>8.3f}{p['mean']:>8.3f}  "
                     f"{p['n_rule_kinds']:>5}{p['mean_prompt_chars']:>9.0f}  {p['tier']:>4}  {shapes}{gap}")
        if p.get("format_compliance_1x24") is not None:
            lines.append(f"{'':<10}1x24 trace-scored (D-76); format compliance {p['format_compliance_1x24']:.3f} "
                         f"of {p['n_answered_1x24_traced']} answered tries")
        if p.get("format_compliance_24x1") is not None:
            lines.append(f"{'':<10}24x1 read from the replies; format compliance {p['format_compliance_24x1']:.3f} "
                         f"of {p['n_answered_24x1_read']} answered tries")
    k = res["pick"]
    lines.append("")
    if k is None:
        lines.append("Pick: NONE (no binding pick; no preset is in [0.25, 0.50] or [0.15, 0.60])")
    else:
        lines.append(f"Pick: {k['preset']} (score {k['score']:.3f}, tier {k['tier']})")
        if k["tie_broken"]:
            lines.append(f"  tie with {', '.join(k['tied_with'])} broken by fewer steps, then fewer rule kinds, then shorter prompt")
        if k["tier"] == 2:
            lines.append(f"  NO preset in [0.25, 0.50]; tier 2 pick from [0.15, 0.60]; missed the band by {k['band_miss']:.3f}")
        if k["shape_gap"] is not None:
            lines.append(f"  shape gap {k['shape_gap']:.3f}" + (" (above 0.30: flagged)" if k["shape_gap_flag"] else ""))
    if res["extra_rung_needed"]:
        lines.append("  every score is above 0.60: extra rung needed (the spare rung l17 runs only on the user's go)")
    if res["outside_15_60_return_to_user"]:
        lines.append("  no preset in [0.15, 0.60] and no easier rung: return to the user")
    if res["presets_without_rows"]:
        lines.append(f"  WARNING: no Haiku-medium rows for {', '.join(res['presets_without_rows'])} (not part of the pick)")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("choose", "extract", "-h", "--help"):
        args = ["choose"] + args                                    # the original form had no sub-command
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract", help="write a Haiku-medium-only copy of a compact table (same columns)")
    ex.add_argument("--table", type=Path, required=True)
    ex.add_argument("--out", type=Path, required=True)
    ex.add_argument("--overwrite", action="store_true")
    ch = sub.add_parser("choose", help="pick the preset and write the pick file")
    ch.add_argument("--table", type=Path, required=True)
    ch.add_argument("--sets", type=Path, nargs="+", required=True)
    ch.add_argument("--out", type=Path, required=True)
    ch.add_argument("--overwrite", action="store_true", help="replace an existing choice file (it is a pre-registered pick)")
    ch.add_argument("--allow-other-rows", action="store_true",
                    help="accept a table that also holds other models/efforts (they are filtered out before any computation)")
    ch.add_argument("--replies", type=Path, nargs="+", default=None,
                    help="raw call log(s) (calls.jsonl) that score every try of a ledger set (D-76 at 1x24, Edith R3 at 24x1); "
                         "only final Haiku-medium records are kept")
    a = ap.parse_args(args)
    if a.out.exists() and not a.overwrite:
        ap.error(f"{a.out} already exists; the output is written once (use --overwrite only on purpose)")
    if a.cmd == "extract":
        kept, left = extract_haiku_medium(a.table, a.out)
        print(f"{kept} Haiku-medium rows written to {a.out}; {left} other rows left out")
        return 0
    cols, all_rows = read_table(a.table)
    rows = [r for r in all_rows if is_haiku_medium(r)]
    if len(rows) != len(all_rows) and not a.allow_other_rows:
        ap.error(f"{a.table} holds {len(all_rows) - len(rows)} row(s) that are not Haiku-medium. Make a Haiku-medium-only file "
                 f"with `extract` and give that, or pass --allow-other-rows on purpose.")
    sets = [load_set_info(d) for d in a.sets]
    trace = trace_grades(read_haiku_medium_replies(a.replies), sets) if a.replies else None
    try:
        res = choose_preset(rows, sets, trace=trace)
    except ValueError as e:
        ap.error(str(e))
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(summary(res))
    print(f"\nwritten to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
