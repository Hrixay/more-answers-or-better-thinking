"""The accuracy-versus-length curve (D-87): Karen's pre-registered descriptive plan (research/pilot-plan-ledger.md, "Pre-registered
descriptive plan for the accuracy-versus-length curve"), computed from the frozen ladder sets and the ladder's raw call logs.

    python3 -m harness.analysis.curve --sets SET_DIR [...] --replies calls.jsonl [...] --out curve.json
    python3 -m harness.analysis.curve --sets ... --replies ... --pick data/pilot/preset-choice-ladder.json --out curve.json

DESCRIPTIVE ONLY. No test is run on the curve: no p-values, intervals only, nothing tuned to the chain data.

Sealing (D-86, D-87). Without `--pick` only Haiku-medium's records are read: every other record is dropped as it is read, before its
reply text is looked at. With `--pick`, the Opus-medium and Sonnet-medium ladder records are opened as well, and only when the pick file
is committed in git and unchanged (`pick_is_committed`), holds a binding pick (tier 1 or 2), was made from Haiku-medium, and names
exactly the presets and the sets (set ids and items_sha256) given. A tier-3 result (no pick) goes back to the user and opens
nothing. Pilot-1's 24-step Opus and Sonnet records are opened only with `--open-pilot1-sealed`, and only once the tag prereg-lock-2 exists (D-86(5)).

What is computed, per model (Haiku-medium x10 tries, Opus-medium x1, Sonnet-medium x1 per puzzle) and per length n:
1. Whole-answer accuracy under the official score (D-76): at nx1 every piece right (scoring.grade_24x1); at 1xn all n step lines right
   and the Answer line equal to line n (scoring.grade_1x24). A planned try with no final record counts as wrong and is reported as
   missing. A puzzle's accuracy is the share of its planned tries that are right. Three panels: "nx1", "1xn" and "pooled" (each base
   puzzle weighted equally: the mean of its two shapes). Each panel gives the mean over base puzzles; Haiku also gives the median over
   puzzles (in the pooled panel the median over all 2 x bases puzzles, the pick statistic).
2. Per-step reliability: at nx1 the per-piece accuracy (pieces right / n per try, a missing or unanswered try scores 0); at 1xn the
   local-slip per-step accuracy (scoring.local_steps: each step judged from the model's own previous balances). A 1xn try whose step
   lines cannot be placed (format) is left out and counted as unplaceable; a try whose every step is right but whose Answer line is not
   counts all n steps right. A puzzle's value is its right steps over its judged steps; a puzzle with no placeable try is left out.
3. Format compliance at 1xn (the share of answered 1xn tries whose format is ok; flagged when more than 5% are not), the number of
   truncated calls (stop reason max_tokens) and the other unanswered kinds, per model and n.
4. Haiku's plurality vote over its 10 tries (vote@10; votes.vote_accuracy_at_k at k = 10, ties at random, official vote keys
   scoring.vote_key), labelled not cost-matched.
5. Intervals, all 95% two-sided and unadjusted: a cluster bootstrap over base puzzles (percentile, 2,000 resamples, seed 20261012,
   each statistic's own seed derived from it and the statistic's name; base puzzles are resampled within their set, so every set keeps
   its size; all tries and both shapes of a base puzzle move together). Opus and Sonnet per-shape whole-answer accuracy uses the
   Wilson interval instead. The percentile ends are the sorted resample values at floor(0.025 B) and ceil(0.975 B) - 1.
6. The q^n reference: one per-step accuracy q per model, the share of all nx1 pieces right pooled over the five lengths, with the same
   bootstrap (resampling within each length's set). q^n and its band (q_lo^n, q_hi^n) are reported for each n and for n = 24 (a dotted
   extrapolation only), with the ratio observed / q^n per n and panel (Haiku: the single-try mean).
7. The 24-step pilot-1 points (optional, `--pilot1-sets` and `--pilot1-replies`; presets l14 to l16 only): Haiku-medium's pooled
   whole-answer mean over all given pilot-1 sets and over the l14 set alone, each with the cluster bootstrap. They never enter q.
8. Decision inputs, from the chosen n only (with `--pick`): p_opus = Opus-medium's 1xn accuracy (D-72's power re-run) and Opus-medium's
   pooled accuracy with the near-ceiling flag (at least 0.95 labels tests 1-2 near ceiling). Opus at the other n and Sonnet at every n
   are descriptive only. The main run's own markers are added later from the main run's data, not here.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from statistics import NormalDist
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..pareto.ladder import LADDER_PRESETS, LADDER_SETUPS
from ..taskgen import ledger
from . import scoring, trace_parse
from .bootstrap import derive_seed
from .kscript import parse_custom_id
from .votes import vote_accuracy_at_k

SEED = 20261012
DRAWS = 2000
LEVELS = (0.025, 0.975)
NEAR_CEILING = 0.95
FORMAT_FLAG_ABOVE = 0.05                    # flagged when more than 5% of answered 1xn tries are not format-ok
EXTRAPOLATE_TO = 24
PILOT1_PRESETS = ("l14", "l15", "l16")
PILOT1_SAME_RULES = "l14"
LOCK2_TAG = "prereg-lock-2"
SETUPS = {su.name: su for su in LADDER_SETUPS}            # hm (Haiku-medium x10), om (Opus-medium x1), sm (Sonnet-medium x1)
PICKER = LADDER_SETUPS[0].name
PANELS = ("nx1", "1xn", "pooled")
_Z = NormalDist().inv_cdf(0.975)


# ---------------------------------------------------------------- inputs

def load_sets(dirs: Sequence[Path]) -> Dict[str, Dict[str, object]]:
    """{set_id: {"setting", "items": {item id: item}, "bases": [base index, ...], "n": steps}} for frozen ledger sets."""
    out: Dict[str, Dict[str, object]] = {}
    for d in dirs:
        man = json.loads((Path(d) / "manifest.json").read_text())
        if man.get("family") != "ledger":
            raise ValueError(f"{man.get('set_id')}: the curve reads ledger sets only")
        items = [json.loads(ln) for ln in (Path(d) / "items.jsonl").read_text().splitlines() if ln.strip()]
        steps = {max(int(it["width"]), int(it["depth"])) for it in items}
        if len(steps) != 1:
            raise ValueError(f"{man['set_id']}: items of more than one length {sorted(steps)}")
        out[str(man["set_id"])] = {"setting": man["setting"], "items_sha256": man.get("items_sha256"), "items": {it["id"]: it for it in items},
                                   "bases": sorted({int(it["base_index"]) for it in items}), "n": steps.pop()}
    return out


def pick_is_committed(path: Path) -> bool:
    """True when `path` is tracked by git and identical to HEAD (no staged or unstaged change)."""
    path = Path(path).resolve()
    cwd = path.parent
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", path.name], cwd=cwd, capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", path.name], cwd=cwd, capture_output=True).returncode == 0
    return tracked and clean


def lock2_is_cut() -> bool:
    return subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{LOCK2_TAG}"], capture_output=True).returncode == 0


def check_pick(path: Path, sets: Mapping[str, Mapping[str, object]], committed: Callable[[Path], bool] = pick_is_committed) -> int:
    """The chosen n, after checking the pick file may open the sealed ladder answers; raises ValueError otherwise."""
    if not committed(path):
        raise ValueError(f"{path}: the pick file must be committed (tracked and unchanged) before any Opus or Sonnet answer is opened")
    res = json.loads(Path(path).read_text())
    su = SETUPS[PICKER]
    if res.get("model") != su.model or res.get("effort") != su.effort:
        raise ValueError(f"{path}: the pick was not made from Haiku-medium")
    if not res.get("pick"):
        raise ValueError(f"{path}: no binding pick (tier {res.get('tier')}): the result goes back to the user and nothing is opened")
    named = {str(p["preset"]) for p in res.get("presets") or []}
    given = {str(s["setting"]) for s in sets.values()}
    if named != given:
        raise ValueError(f"{path}: the pick covers presets {sorted(named)}, the sets given are {sorted(given)}")
    hashes = {sid: s["items_sha256"] for sid, s in sets.items()}
    if res.get("sets") != hashes:
        raise ValueError(f"{path}: the pick was made from sets {res.get('sets')}, not the sets given {hashes}")
    preset = str(res["pick"]["preset"])
    if preset not in LADDER_PRESETS:
        raise ValueError(f"{path}: the pick {preset!r} is not a ladder preset")
    return LADDER_PRESETS[preset]


def read_records(paths: Iterable[Path], sets: Mapping[str, Mapping[str, object]], opened: Sequence[str]) -> List[Dict[str, object]]:
    """The final records of the given sets' puzzles for the setups in `opened`, with only the fields the scores need. A record of any
    other setup is dropped as it is read; a record whose model or effort does not match its setup tag raises ValueError."""
    puzzles = {pid for s in sets.values() for pid in s["items"]}                          # type: ignore[attr-defined]
    out: List[Dict[str, object]] = []
    for path in paths:
        with open(path) as f:
            for ln in f:
                if not ln.strip():
                    continue
                rec = json.loads(ln)
                if not rec.get("final") or not rec.get("custom_id"):
                    continue
                cid = parse_custom_id(str(rec["custom_id"]))
                if cid["puzzle"] not in puzzles:
                    continue
                tag = str(cid["setup"])
                if tag not in opened:
                    continue                                                                 # sealed: never looked at
                su = SETUPS.get(tag)
                if su is None or rec.get("requested_model") != su.model or rec.get("effort") != su.effort:
                    raise ValueError(f"{rec['custom_id']}: setup {tag!r} with model {rec.get('requested_model')} effort {rec.get('effort')}")
                out.append({"puzzle": cid["puzzle"], "setup": tag, "sample": cid["sample"], "kind": rec.get("kind"),
                            "answer_text": rec.get("answer_text")})
    return out


# ---------------------------------------------------------------- scoring one try

def _puzzle(item: Mapping[str, object]) -> ledger.LPuzzle:
    p = item["params"]                                                                       # type: ignore[index]
    params = ledger.LParams(**{**p, "kinds": tuple(p["kinds"]), "house_fires": tuple(p["house_fires"])})  # type: ignore[arg-type]
    again = ledger.generate(item["seed"], item["width"], item["depth"], params, item_id=item["id"], style=item["style"])  # type: ignore[arg-type]
    if again.prompt != item["prompt"]:
        raise ValueError(f"{item['id']}: does not rebuild from its seed")
    return again


def score_try(rec: Mapping[str, object], item: Mapping[str, object], puzzle: Optional[Callable[[], ledger.LPuzzle]] = None) -> Dict[str, object]:
    """One try: right (official), vote key, pieces right (nx1), and for 1xn with `puzzle` the local-slip step counts."""
    kind = str(rec.get("kind"))
    text = str(rec.get("answer_text") or "")
    lines = int(item["params"]["lines"])                                                    # type: ignore[index]
    if int(item["depth"]) > 1:
        states = item["chains"][0]["states"]                                                 # type: ignore[index]
        g = scoring.grade_1x24(text, states, lines, kind=kind, answer_only=item.get("style") == "d31-answer-only")
        shape = scoring.chain_shape(len(states))
        out = {"right": bool(g["correct"]), "kind": kind, "format_ok": g["format_status"] == "ok",
               "vote": scoring.vote_key(dict(g, kind=kind, shape=shape, setup=rec.get("setup")))}
        if puzzle is not None:
            out.update(_local(text, kind, puzzle))
        return out
    g = scoring.grade_24x1(text, item["answer"], lines, kind=kind)                         # type: ignore[arg-type]
    return {"right": bool(g["correct"]), "kind": kind, "pieces_right": int(g["pieces_right"]),
            "vote": scoring.vote_key(dict(g, kind=kind, shape=scoring.pieces_shape(len(item["answer"])), setup=rec.get("setup")))}  # type: ignore[arg-type]


def _local(text: str, kind: str, puzzle: Callable[[], ledger.LPuzzle]) -> Dict[str, object]:
    if kind != "answered":
        return {"steps_judged": 0, "steps_right": 0, "placeable": False}
    pz = puzzle()
    res = scoring.local_steps(text, pz)
    if res["unplaceable"] is None:
        rows = res["steps"]                                                                  # type: ignore[assignment]
        return {"steps_judged": len(rows), "steps_right": sum(1 for r in rows if not r["slipped"]), "placeable": True}
    if trace_parse.parse_trace(text, pz.params.lines, pz.depth).step_states is not None:   # every step right, the Answer line not
        return {"steps_judged": pz.depth, "steps_right": pz.depth, "placeable": True}
    return {"steps_judged": 0, "steps_right": 0, "placeable": False}


# ---------------------------------------------------------------- statistics

def wilson(x: int, n: int) -> Tuple[Optional[float], Optional[float]]:
    if n == 0:
        return None, None
    p = x / n
    den = 1 + _Z * _Z / n
    centre = (p + _Z * _Z / (2 * n)) / den
    half = _Z * math.sqrt(p * (1 - p) / n + _Z * _Z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def _mean(xs: Sequence[float]) -> Optional[float]:
    return math.fsum(xs) / len(xs) if xs else None


def _median(xs: Sequence[float]) -> Optional[float]:
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def cluster_bootstrap(strata: Sequence[Sequence[object]], stat: Callable[[List[object]], Optional[float]], name: str,
                      draws: int = DRAWS, seed: int = SEED) -> Tuple[Optional[float], Optional[float]]:
    """Percentile interval of `stat` over `draws` resamples: each stratum's clusters (base puzzles) drawn with replacement, same size."""
    rng = random.Random(derive_seed(seed, name))
    vals: List[float] = []
    for _ in range(draws):
        sample: List[object] = []
        for s in strata:
            sample += rng.choices(list(s), k=len(s))
        v = stat(sample)
        if v is not None:
            vals.append(v)
    if not vals:
        return None, None
    vals.sort()
    b = len(vals)
    return vals[int(math.floor(LEVELS[0] * b))], vals[int(math.ceil(LEVELS[1] * b)) - 1]


# ---------------------------------------------------------------- the curve

class _Cells:
    """Per setup, set and base puzzle, the scored tries of each shape ("nx1" / "1xn")."""

    def __init__(self, sets: Mapping[str, Mapping[str, object]], records: Iterable[Mapping[str, object]], local: bool):
        self.sets = sets
        self.by: Dict[Tuple[str, str, int, str], List[Dict[str, object]]] = {}
        self.seen: Dict[Tuple[str, str, int, str], set] = {}
        where = {pid: sid for sid, s in sets.items() for pid in s["items"]}                 # type: ignore[attr-defined]
        cache: Dict[str, ledger.LPuzzle] = {}
        for rec in records:
            sid = where[str(rec["puzzle"])]
            item = sets[sid]["items"][rec["puzzle"]]                                       # type: ignore[index]
            shape = "1xn" if int(item["depth"]) > 1 else "nx1"
            key = (str(rec["setup"]), sid, int(item["base_index"]), shape)
            if rec["sample"] in self.seen.setdefault(key, set()):
                raise ValueError(f"{rec['puzzle']} {rec['setup']} sample {rec['sample']}: two final records")
            self.seen[key].add(rec["sample"])

            def build(item=item):
                if item["id"] not in cache:
                    cache[item["id"]] = _puzzle(item)
                return cache[item["id"]]
            self.by.setdefault(key, []).append(score_try(rec, item, build if local and shape == "1xn" else None))

    def tries(self, setup: str, sid: str, base: int, shape: str) -> List[Dict[str, object]]:
        """The planned tries, a missing one filled as an unanswered wrong try."""
        got = list(self.by.get((setup, sid, base, shape), []))
        planned = SETUPS[setup].n
        if len(got) > planned:
            raise ValueError(f"{sid} base {base} {shape} {setup}: {len(got)} final records, {planned} planned")
        return got + [{"right": False, "kind": "missing", "pieces_right": 0, "vote": None, "steps_judged": 0, "steps_right": 0,
                       "placeable": False, "format_ok": False}] * (planned - len(got))


def _whole(cells: _Cells, setup: str, sid: str, base: int, shape: str) -> float:
    t = cells.tries(setup, sid, base, shape)
    return sum(1 for x in t if x["right"]) / len(t)


def _step(cells: _Cells, setup: str, sid: str, base: int, shape: str, n: int) -> Optional[float]:
    t = cells.tries(setup, sid, base, shape)
    if shape == "nx1":
        return math.fsum(int(x.get("pieces_right") or 0) / n for x in t) / len(t)
    judged = sum(int(x.get("steps_judged") or 0) for x in t)
    return sum(int(x.get("steps_right") or 0) for x in t) / judged if judged else None


def _vote(cells: _Cells, sid: str, base: int, shape: str, item: Mapping[str, object]) -> float:
    t = cells.tries(PICKER, sid, base, shape)
    correct = scoring.trace_key(item["chains"][0]["states"] if shape == "1xn" else item["answer"])  # type: ignore[index]
    return float(vote_accuracy_at_k([x["vote"] for x in t], correct, k=len(t))["acc"])  # type: ignore[misc]


def _item(sets: Mapping[str, Mapping[str, object]], sid: str, base: int, shape: str) -> Mapping[str, object]:
    for it in sets[sid]["items"].values():                                                # type: ignore[attr-defined]
        if int(it["base_index"]) == base and (int(it["depth"]) > 1) == (shape == "1xn"):
            return it
    raise KeyError((sid, base, shape))


def _panels(per_base: Callable[[int, str], Optional[float]], bases: Sequence[int], name: str, median: bool) -> Dict[str, object]:
    """Mean over base puzzles per panel, with the cluster-bootstrap interval; the pooled panel weights each base puzzle equally."""
    out: Dict[str, object] = {}
    for panel in PANELS:
        def value(b: int, panel: str = panel) -> Optional[float]:
            if panel != "pooled":
                return per_base(b, panel)
            vs = [v for v in (per_base(b, "nx1"), per_base(b, "1xn")) if v is not None]
            return _mean(vs)
        vals = {b: value(b) for b in bases}

        def stat(sample: List[object]) -> Optional[float]:
            return _mean([vals[b] for b in sample if vals[b] is not None])                   # type: ignore[index, misc]
        lo, hi = cluster_bootstrap([bases], stat, f"{name}:{panel}")
        row: Dict[str, object] = {"mean": _mean([v for v in vals.values() if v is not None]), "ci95": [lo, hi],
                                  "n_base": sum(1 for v in vals.values() if v is not None)}
        if median:
            pts = [per_base(b, s) for b in bases for s in ("nx1", "1xn")] if panel == "pooled" else [vals[b] for b in bases]
            row["median"] = _median([v for v in pts if v is not None])
        out[panel] = row
    return out


def curve(sets: Mapping[str, Mapping[str, object]], records: Iterable[Mapping[str, object]], opened: Sequence[str]) -> Dict[str, object]:
    """The per-model, per-length numbers (points 1 to 6 of the module text)."""
    cells = _Cells(sets, records, local=True)
    by_n = sorted(sets, key=lambda sid: int(sets[sid]["n"]))                               # type: ignore[arg-type]
    models: Dict[str, Dict[str, object]] = {}
    for setup in opened:
        per_n: Dict[str, object] = {}
        for sid in by_n:
            n = int(sets[sid]["n"])                                                         # type: ignore[arg-type]
            bases: List[int] = sets[sid]["bases"]                                           # type: ignore[assignment]
            name = f"{setup}:n{n}"
            whole = _panels(lambda b, s: _whole(cells, setup, sid, b, s), bases, f"whole:{name}", median=setup == PICKER)
            if setup != PICKER:
                for shape in ("nx1", "1xn"):
                    x = sum(1 for b in bases for t in cells.tries(setup, sid, b, shape) if t["right"])
                    k = len(bases) * SETUPS[setup].n
                    whole[shape]["ci95"] = list(wilson(x, k))                               # type: ignore[index]
                    whole[shape].update(right=x, tries=k, interval="wilson")                # type: ignore[union-attr]
            all_tries = [t for b in bases for s in ("nx1", "1xn") for t in cells.tries(setup, sid, b, s)]
            chain = [t for b in bases for t in cells.tries(setup, sid, b, "1xn")]
            answered = [t for t in chain if t["kind"] == "answered"]
            fc = (sum(1 for t in answered if t["format_ok"]) / len(answered)) if answered else None
            kinds: Dict[str, int] = {}
            for t in all_tries:
                if t["kind"] != "answered":
                    kinds[str(t["kind"])] = kinds.get(str(t["kind"]), 0) + 1
            row: Dict[str, object] = {
                "set_id": sid, "preset": sets[sid]["setting"], "n_base": len(bases), "whole_answer": whole,
                "per_step": _panels(lambda b, s: _step(cells, setup, sid, b, s, n), bases, f"step:{name}", median=False),
                "unplaceable_1xn": sum(1 for t in answered if not t.get("placeable")),
                "format_compliance_1xn": fc, "answered_1xn": len(answered),
                "format_flag": fc is not None and 1 - fc > FORMAT_FLAG_ABOVE,
                "truncated": kinds.get("truncated", 0), "not_answered": kinds}
            if setup == PICKER:
                row["vote_at_10"] = dict(_panels(lambda b, s: _vote(cells, sid, b, s, _item(sets, sid, b, s)), bases,
                                                 f"vote:{name}", median=False), label="not cost-matched")
            per_n[str(n)] = row
        models[setup] = {"model": SETUPS[setup].model, "effort": SETUPS[setup].effort, "tries_per_puzzle": SETUPS[setup].n,
                         "by_n": per_n, "q": _q(cells, sets, setup, per_n)}
    return models


def _q(cells: _Cells, sets: Mapping[str, Mapping[str, object]], setup: str, per_n: Dict[str, object]) -> Dict[str, object]:
    """The q^n reference: q = all nx1 pieces right / all nx1 pieces, pooled over the lengths (point 6)."""
    strata = [[(sid, b) for b in sets[sid]["bases"]] for sid in sets]                     # type: ignore[attr-defined]

    def stat(sample: List[object]) -> Optional[float]:
        right = total = 0
        for sid, b in sample:                                                               # type: ignore[misc]
            n = int(sets[sid]["n"])                                                         # type: ignore[arg-type]
            for t in cells.tries(setup, sid, b, "nx1"):
                right += int(t.get("pieces_right") or 0)
                total += n
        return right / total if total else None
    q = stat([c for s in strata for c in s])
    lo, hi = cluster_bootstrap(strata, stat, f"q:{setup}")
    lines: Dict[str, object] = {}
    for key, row in per_n.items():
        n = int(key)
        ref = None if q is None else q ** n
        ratio = {p: (row["whole_answer"][p]["mean"] / ref if ref else None) for p in PANELS}  # type: ignore[index]
        lines[key] = {"q_n": ref, "band": [None if lo is None else lo ** n, None if hi is None else hi ** n], "observed_over_q_n": ratio}
    ext = {"q_n": None if q is None else q ** EXTRAPOLATE_TO,
           "band": [None if lo is None else lo ** EXTRAPOLATE_TO, None if hi is None else hi ** EXTRAPOLATE_TO],
           "label": "dotted extrapolation only"}
    return {"q": q, "ci95": [lo, hi], "by_n": lines, str(EXTRAPOLATE_TO): ext}


def pilot1_points(sets: Mapping[str, Mapping[str, object]], records: Iterable[Mapping[str, object]], opened: Sequence[str]) -> Dict[str, object]:
    """Point 7: the 24-step pilot-1 markers, pooled over the given pilot-1 sets and over the l14 set alone."""
    bad = sorted(str(s["setting"]) for s in sets.values() if s["setting"] not in PILOT1_PRESETS)
    if bad:
        raise ValueError(f"pilot-1 points use presets {PILOT1_PRESETS} only, not {bad}")
    cells = _Cells(sets, records, local=False)
    out: Dict[str, object] = {}
    for setup in opened:
        def per_base(c: Tuple[str, int]) -> float:
            return _mean([_whole(cells, setup, c[0], c[1], s) for s in ("nx1", "1xn")])     # type: ignore[return-value]
        res: Dict[str, object] = {}
        for label, sids in (("l14_to_l16", list(sets)), ("l14_only", [s for s in sets if sets[s]["setting"] == PILOT1_SAME_RULES])):
            strata = [[(sid, b) for b in sets[sid]["bases"]] for sid in sids]              # type: ignore[attr-defined]
            if not strata:
                continue
            vals = {c: per_base(c) for s in strata for c in s}

            def stat(sample: List[object]) -> Optional[float]:
                return _mean([vals[c] for c in sample])                                     # type: ignore[index]
            lo, hi = cluster_bootstrap(strata, stat, f"pilot1:{setup}:{label}")
            res[label] = {"mean": stat([c for s in strata for c in s]), "ci95": [lo, hi], "n_base": len(vals),
                          "sets": sorted(sids), "label": f"pilot-1, presets {', '.join(sorted({str(sets[s]['setting']) for s in sids}))}, "
                                                         "before lock-2 (different rule mix, sets and timing)"}
        out[setup] = res
    return out


def decision_inputs(models: Mapping[str, Mapping[str, object]], chosen_n: int) -> Dict[str, object]:
    """Point 8: only the chosen n's Opus-medium point feeds decisions."""
    om = models["om"]["by_n"][str(chosen_n)]["whole_answer"]                              # type: ignore[index]
    pooled = om["pooled"]["mean"]
    return {"chosen_n": chosen_n, "p_opus_1xn": om["1xn"]["mean"], "p_opus_1xn_ci95": om["1xn"]["ci95"],
            "opus_pooled": pooled, "near_ceiling": pooled is not None and pooled >= NEAR_CEILING,
            "note": "Opus-medium at the chosen n only; Opus at other n and Sonnet at every n are descriptive"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", type=Path, required=True, help="the frozen ladder sets (l14n4 ... l14n16)")
    ap.add_argument("--replies", nargs="+", type=Path, required=True, help="the ladder's raw call logs (calls.jsonl)")
    ap.add_argument("--pick", type=Path, help="the committed preset-choice file; opens the Opus and Sonnet ladder answers")
    ap.add_argument("--pilot1-sets", nargs="*", type=Path, default=[])
    ap.add_argument("--pilot1-replies", nargs="*", type=Path, default=[])
    ap.add_argument("--open-pilot1-sealed", action="store_true", help="also open pilot-1's Opus and Sonnet records (after prereg-lock-2)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    sets = load_sets(a.sets)
    for sid, s in sets.items():
        if s["setting"] not in LADDER_PRESETS:
            raise SystemExit(f"{sid}: preset {s['setting']} is not a ladder preset")
    chosen = None
    opened: Tuple[str, ...] = (PICKER,)
    if a.pick:
        chosen = check_pick(a.pick, sets)
        opened = tuple(SETUPS)
    res: Dict[str, object] = {"plan": "research/pilot-plan-ledger.md, D-87 curve (descriptive only)", "seed": SEED, "draws": DRAWS,
                              "opened": list(opened), "sets": {sid: s["setting"] for sid, s in sets.items()}}
    models = curve(sets, read_records(a.replies, sets, opened), opened)
    res["models"] = models
    if chosen is not None:
        res["decision_inputs"] = decision_inputs(models, chosen)
    if a.pilot1_sets:
        p_opened: Tuple[str, ...] = (PICKER,)
        if a.open_pilot1_sealed:
            if not lock2_is_cut():
                raise SystemExit(f"pilot-1's Opus and Sonnet records stay sealed until the tag {LOCK2_TAG} exists (D-86(5))")
            p_opened = tuple(SETUPS)
        p_sets = load_sets(a.pilot1_sets)
        res["pilot1"] = pilot1_points(p_sets, read_records(a.pilot1_replies, p_sets, p_opened), p_opened)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(f"wrote {a.out}: models {', '.join(opened)}; lengths {', '.join(str(s['n']) for s in sets.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
