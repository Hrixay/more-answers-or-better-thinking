"""The free analyses on existing data that the user approved (D-131: "Yes to all nine", items 1-8 and 10; D-133: items 9 and 12; the
master plan's "Free analyses on existing data (ranked)", decisions/briefings/2026-10-15-compiler/master-plan.md at 7b43f91; D-157:
analysis 13, the tie view for Test B2, which is not the plan's item 13). No API call, no money.

    python3 -m harness.analysis.free_analyses --which 1,3,7 --out data/main/free-analyses \\
        --main-set data/tasks/main-ledger-l14n6-v1 --main-run <raw>/main-l14n6-1 --main-k data/main/main-l14n6-1/k.json \\
        --s1b-run <raw>/study1b-1 --s1b-k data/main/study1b-1/k.json

Every result is **post hoc** (D-131: "reported in the paper as results labelled post hoc (never as tests); none can change a
pre-registered reading"). Each analysis writes `fa<N>.json` ONCE (an existing file is refused), holding: the plan's own definition
(read from the pinned plan file, never retyped), its label, the inputs' SHA-256 (checked first against the values the locked analyses
stamped), this module's SHA-256, the seeds, the result, and `checks`: the places where this code recomputes a stamped number, which must
agree (a disagreement refuses the file).

Fixed before computing (D-131; Edith's settlement ops/reviews/2026-10-15-plan-settlement.md and g2 E-20):
- **Seeds.** Every new interval uses `bootstrap.derive_seed(FA_SEED, name)` with FA_SEED = 20261015 and the name written in the output;
  paired intervals use the locked `bootstrap.paired_bca` (B = 10,000), accuracy bands the locked cluster bootstrap (2,000 draws). No
  p-value and no verdict is reported, except in analysis 5, whose p-values are the locked tests' own.
- **Analysis 5 (E-19).** Holm in the inferiority direction over all five pre-registered tests: for each test the one-sided p-value of
  H0: d >= -10 is 1 - p, where p is the locked non-inferiority p-value (bootstrap.p_value, the same bootstrap: same differences, seed and
  B), recomputed here and checked equal to the stamped p; Holm at alpha 0.025 (bootstrap.holm_thresholds). Beside it, the stricter
  line E-19 asks for: each test's two-sided 99% BCa interval from the same bootstrap and whether it excludes -10. Disclosed as chosen
  after the main results were open; the pre-registered unadjusted three-way reading stays the result.
- **Analysis 6 (E-20).** The 16-step bins are item 20's rule on Haiku-medium at 16 steps: each puzzle's single-try accuracy over its 5
  tries (hm@16), 10-point bins, the last including 100, structurally empty bins listed as empty. Degeneracy rule: a bin with fewer than 3
  puzzles in a shape is shown but not read; if any one bin holds more than 80% of a shape's puzzles, that shape's binned table is
  "uninformative" and only the unbinned curve is read. Within a bin, the thirds use Haiku-max's own wrong-try agreement (item 4's
  pairing); puzzles with fewer than 2 wrong tries form "too few wrong tries", and that count is reported. The occupancy (Haiku-medium only,
  `fa6a.json`) is written before any Haiku-max value is binned (`fa6b.json`).
- **Analysis 4.** "Exact" is the two-sided 95% Clopper-Pearson interval (report_arms.clopper_pearson) over base puzzles, used only where
  the stamped bootstrap interval has zero width; every collapsed cell has all its puzzles right (or all wrong), so the count is x of n
  base puzzles. Revision 2 (fa4r2) takes every zero-width interval in the stamped result files by rule (FA4R2_FAMILIES), not a hand
  list; the first version's 13 cells are recomputed, checked equal and kept first. Left out, with the reason written in the output:
  the length sweep's q (no single count carries it) and item 20's cells at k below 40 (printed nowhere). Revision 3 (fa4r3, D-144)
  keeps revision 2's cells and scans every interval field by name (not only `ci95`): it adds item 9e's even-base Opus-medium accuracy
  (opus_accuracy_ci95) and the fairness check's misapplied-rule rates (ci90, given 90% exact intervals at their own level), and lists
  q's q^N bands as excluded and every two-number field it does not treat as an interval.
- **Analysis 13 (D-157).** Its definition is D-157's register row (decisions/register.md at ee30f69), read from git, since the plan's
  item 13 is a different analysis that was never approved. B2 is reproduced first (every stamped field, both margins); then Study 1's
  D-33 tie sensitivity (five_tests.tie_report) applied to B2: how often a tie decided the vote (and how often a 3-3 tie did), and B2's
  paired d with every tie scored wrong, with its interval by the rule above (no p, no reading).

The run folders are read by the locked loaders (report_groupc.build_context for Study 1; study1b.load_run and build_rows for Study 1b),
which read data/tasks/ for grading; no item record is printed or written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from . import bootstrap, five_tests, main_analysis, report_arms, report_costs, report_groupc, report_votes, scoring, study1b, votes
from .curve import cluster_bootstrap

FA_SEED = 20261015
B = bootstrap.DRAWS                     # 10,000 (paired)
DRAWS = study1b.DRAWS                   # 2,000 (cluster bands)
MARGIN = -10.0
ROOT = Path(__file__).resolve().parents[2]
PLAN = ("decisions/briefings/2026-10-15-compiler/plan-result.json", "7b43f91")
LABEL = "post hoc (D-131): reported as a result labelled post hoc, never as a test; it cannot change a pre-registered reading"

# The run files the locked analyses stamped (Study 1: the D-93 stamp; Study 1b: its analysis.json inputs).
MAIN_RUN_SHA = {"calls.jsonl": "0d04ce3870704017d79a7cd2f3603a7f124379f241f13fb3b3ce416bdd02c123",
                "compact_table.csv": "984da2841cd56f0026bb0e750968d59845d8a842af70b2aff04dcd82269df6b4",
                "ledger.jsonl": "5f175b8764dd44c1e028d9887ff88945b96489bc2e4eb368bd362ab83313957e",
                "manifest.json": "702cd7ca22da2ecd97ef7d5fe4bf8c970a92adf9de7bfeef76e5d55252de6993"}
MAIN_K_SHA = "b0f8b05f729b5e6cee6deaa2384c986646217adf72a96772d5096bd2d6e3234b"
S1B_RUN_SHA = {"calls.jsonl": "7523d30e0cf979cc323e0192c4141fee548ce33557288fefdd53f5c43e1baeb9",
               "compact_table.csv": "e2fbadd3603f4b96d103ecba5392d8dc7e31e04f167eadaf15d3d08eb8a45ca7",
               "manifest.json": "72111619a79daf91702daab908648216aa5f7a512ae9bfb7c3a282e1c39034a5",
               "calibration_limits.json": "41612c7a4e53d71e88aae5171cee741bed32bdc3d7da96000acd1c13d2d9c4ea"}
S1B_K_SHA = "4204d537769f63c1317909b4d98112fff6c4d550555568ef5aa0cd20bc4c8427"
STAMPED = {"main": ("data/main/main-l14n6-1/analysis.json", "43d18eed62604aab9006cae76a6ee04445170866486d14246fb933646823cfef"),
           "s1b": ("data/main/study1b-1/analysis.json", "239173fc617f832e7a793e57d0b3fa3dc5c968b395dade10e0720c0f1dc74332"),
           "topup": ("data/main/topup-1/analysis.json", "c76478bfd6783fed2a43f146c587d03ace739ba4f67efe6f3da5de2c1f773558"),
           "groupc": ("data/main/main-l14n6-1/groupc.json", "e1cbd4057ed94e6735d7a3ca079213d8ea6eba1240b6f5d90244545bb3f773a9"),
           "curve_d90": ("data/pilot/curve-ladder-l14n-1-d90.json", "33ab260979cffd6a720f96aeab57f6384c9e6bd49b8730d0a4eab543184120f0"),
           "curve": ("data/pilot/curve-ladder-l14n-1.json", "1300a410d652323f9969fd2e44ff843619e72205a5e74cdf1ade01346fdc36ad"),
           "fa2r2": ("data/main/free-analyses/fa2r2.json", "92aa3cfe2fb26c00b34d11edbf54b627b938a4f2db06d1306830a2f9b8e94838"),
           "fa4": ("data/main/free-analyses/fa4.json", "03376ca1bbe9ba373c6bbc3a78b6bb99a0d939cf5338473ee48d9b2926a21c90"),
           "fa4r2": ("data/main/free-analyses/fa4r2.json", "1b8a336a055ecb0eb3362f9619a7d6362c9f93fd92fe638d9634d630999c3516")}


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout.strip()


def stamped(name: str) -> dict:
    path, want = STAMPED[name]
    raw = (ROOT / path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != want:
        raise ValueError(f"{path}: SHA-256 differs from the stamped analysis")
    return json.loads(raw)


def plan_definition(n: int) -> Dict[str, str]:
    raw = subprocess.run(["git", "-C", str(ROOT), "show", f"{PLAN[1]}:{PLAN[0]}"], check=True, capture_output=True).stdout
    fa = json.loads(raw)["plan"]["free_analyses"]
    e = fa[n - 1]
    return {"source": f"{PLAN[0]} at {PLAN[1]}, plan.free_analyses[{n - 1}]", **{k: e[k] for k in sorted(e)}}


def check_files(folder: Path, want: Mapping[str, str]) -> Dict[str, str]:
    got = {f: sha256(Path(folder) / f) for f in want}
    bad = {f: (got[f], w) for f, w in want.items() if got[f] != w}
    if bad:
        raise ValueError(f"{folder}: files differ from the stamped SHA-256: {bad}")
    return got


class Checks:
    """Recomputations of stamped numbers: each must agree, or the analysis refuses to write."""

    def __init__(self) -> None:
        self.items: List[Dict[str, object]] = []

    def eq(self, what: str, ours: object, stamped_value: object, tol: float = 1e-9) -> None:
        if isinstance(ours, (int, float)) and isinstance(stamped_value, (int, float)):
            ok = abs(float(ours) - float(stamped_value)) <= tol
        else:
            ok = ours == stamped_value
        self.items.append({"what": what, "ours": ours, "stamped": stamped_value, "equal": ok})
        if not ok:
            raise ValueError(f"recomputation differs from the stamped value: {what}: {ours!r} != {stamped_value!r}")


def paired(diffs: List[float], name: str) -> Dict[str, object]:
    """d and its 95% BCa interval by the locked paired_bca (B = 10,000), seed derive_seed(FA_SEED, name). No p, no verdict."""
    if not diffs:
        return {"n": 0, "d": None, "ci95": None, "seed_name": name}
    r = bootstrap.paired_bca(diffs, margin=MARGIN, B=B, seed=bootstrap.derive_seed(FA_SEED, name))
    return {"n": r["n"], "d": r["d"], "ci95": list(r["ci95"]), "seed_name": name}


def band(values: Mapping[str, float], name: str) -> Dict[str, object]:
    """Mean over bases with the cluster bootstrap 95% band (2,000 draws), called as the locked study1b._boot calls it: ONE stratum
    holding every base puzzle, each drawn with replacement; seed derive_seed(FA_SEED, name).

    Revision 2 (fa2r2): the first version passed one stratum per base ([[v] for each base]), so every resample equalled the sample
    and every band collapsed to its mean (found 2026-10-15 while building TAB-34; fa2.json keeps that version as the record)."""
    bases = sorted(values)
    if not bases:
        return {"mean": None, "ci95": None, "n_base": 0, "bootstrap_name": name}
    lo, hi = cluster_bootstrap([bases], lambda s: math.fsum(values[b] for b in s) / len(s), name, draws=DRAWS, seed=FA_SEED)  # type: ignore[arg-type]
    return {"mean": sum(values.values()) / len(values), "ci95": [lo, hi], "n_base": len(bases), "bootstrap_name": name}


# ================================================================ contexts

class Study1:
    def __init__(self, set_dir: Path, run_dir: Path, k_path: Path):
        self.files = check_files(run_dir, MAIN_RUN_SHA)
        if sha256(k_path) != MAIN_K_SHA:
            raise ValueError(f"{k_path}: not the committed Study 1 k.json")
        self.ctx = report_groupc.build_context(set_dir, run_dir, k_path, ("sl", "ho", "hx"))
        self.a = stamped("main")
        self.inputs = {"run": self.files, "k_json_sha256": MAIN_K_SHA, "analysis_json_sha256": STAMPED["main"][1]}

    def rows(self) -> List[Mapping[str, object]]:
        return list(self.ctx["rows"]) + list(self.ctx.get("other") or [])                       # type: ignore[call-overload]

    def arm(self, arm: str, shape: str) -> List[Dict[str, object]]:
        return [dict(r) for r in self.rows() if r["setup"] == arm and r["shape"] == shape]

    def single(self, arm: str, shape: str) -> Dict[str, float]:
        """Per-base single-try accuracy in points (official, as_deployed), the locked scoring.arm_scores."""
        return scoring.arm_scores(self.arm(arm, shape), "as_deployed", "official")

    def vote(self, arm: str, shape: str, k: int) -> Dict[str, float]:
        """Per-base vote@k in points over the arm's designed samples (the locked five_tests.vote_scores, as item 10 calls it)."""
        rs = [dict(r, setup="haiku-med") for r in self.arm(arm, shape)]
        return five_tests.vote_scores(rs, shape, int(k), "as_deployed", designed=report_votes.designed(arm))   # type: ignore[return-value]


class Study1b:
    def __init__(self, run_dir: Path, k_path: Path):
        self.files = check_files(run_dir, S1B_RUN_SHA)
        if sha256(k_path) != S1B_K_SHA:
            raise ValueError(f"{k_path}: not the committed Study 1b k.json")
        run = study1b.load_run(run_dir)
        self.plan = run["sets"]
        built = study1b.build_rows(self.plan, [Path(run_dir) / "calls.jsonl"], run["calibration_set_ids"])   # type: ignore[arg-type]
        self.rows = built["rows"]
        self.kdoc = study1b.check_k(k_path, run_dir)
        self.ctx = study1b.cost_ctx(self.plan, built, self.kdoc, run_dir, None)                 # type: ignore[arg-type]
        self.a = stamped("s1b")
        self.inputs = {"run": self.files, "k_json_sha256": S1B_K_SHA, "analysis_json_sha256": STAMPED["s1b"][1]}

    def tries(self, tag: str, n: int) -> int:
        return int(self.a["descriptive"]["arms"][f"{tag}@{n}"]["tries_per_item"])

    def trows(self, tag: str, n: int) -> List[Dict[str, object]]:
        return [dict(r, setup="haiku-med") for r in self.rows if r["set_id"] == study1b.SETS[n] and r["tag"] == tag]

    def single(self, tag: str, n: int) -> Dict[str, Dict[str, float]]:
        rs = self.trows(tag, n)
        return {sh: five_tests.single_scores(rs, "haiku-med", sh, "as_deployed")
                for sh in (scoring.pieces_shape(n), scoring.chain_shape(n))}

    def vote(self, tag: str, n: int, k: int) -> Dict[str, Dict[str, float]]:
        rs = self.trows(tag, n)
        return {sh: five_tests.vote_scores(rs, sh, int(k), "as_deployed", designed=self.tries(tag, n))   # type: ignore[misc]
                for sh in (scoring.pieces_shape(n), scoring.chain_shape(n))}

    def cost(self, tag: str, n: int) -> Dict[str, object]:
        """List cost per answer per form and pooled, by the locked study1b.cost_per_answer (9b), checked equal to the stamped arm."""
        return study1b.cost_per_answer(self.ctx, tag, n)


def lc(cost: Mapping[str, object], key: str) -> Fraction:
    """The list cost per answer from study1b.cost_per_answer's block (`key` a form or 'pooled')."""
    return Fraction(str(cost[key]["list_usd"]))                                                   # type: ignore[index]


def pooled_and_forms(name: str, ch: Mapping[str, Mapping[str, float]], co: Mapping[str, Mapping[str, float]]) -> Dict[str, object]:
    """Paired d (challenger minus comparator) per form and pooled over forms (study1b.pooled: a base's two forms averaged)."""
    out: Dict[str, object] = {}
    for sh in ch:
        out[sh] = paired(scoring.paired_differences(ch[sh], co[sh]), f"{name}:{sh}")
    out["pooled"] = paired(scoring.paired_differences(study1b.pooled(ch), study1b.pooled(co)), f"{name}:pooled")
    return out


def mean(xs: Mapping[str, float]) -> Optional[float]:
    return sum(xs.values()) / len(xs) if xs else None


# ================================================================ the analyses

def fa1(s1: Study1, s1b: Study1b, chk: Checks) -> Dict[str, object]:
    """One Haiku-max try against a lower-effort Haiku vote at the same money, on the same puzzles: k = floor(Haiku-max's list cost per
    answer / the other arm's), from the stamped costs (Study 1: item 24's cost per puzzle of a single try; Study 1b: the arm's pooled
    cost per answer), held to the arm's designed tries; per-base paired d = Haiku-max single try - vote@k."""
    out: Dict[str, object] = {"study1": {}, "study1b": {}}
    t24 = s1.a["reporting"]["group_b"]["item_24"]["table"]
    for shape in ("1x6", "6x1"):
        hx_cost = Fraction(str(t24[f"haiku-max {shape}"]["cost_per_puzzle"]["mean"]))
        hm_cost = Fraction(str(t24[f"haiku-med {shape}"]["cost_per_puzzle"]["mean"]))
        k = min(math.floor(hx_cost / hm_cost), report_votes.designed("haiku-med"))
        h = s1.single("haiku-max", shape)
        v = s1.vote("haiku-med", shape, k)
        chk.eq(f"Study 1 Haiku-max single try {shape} mean", mean(h), t24[f"haiku-max {shape}"]["accuracy_mean"])
        out["study1"][shape] = {"k": k, "cost_ratio": float(hx_cost / hm_cost), "haiku_max_single": mean(h), "vote_at_k": mean(v),   # type: ignore[index]
                                "paired": paired(scoring.paired_differences(h, v), f"fa1:study1:haiku-max-vs-haiku-med:{shape}")}
    arms = s1b.a["descriptive"]["arms"]
    for n in (16, 6):
        hx_c = Fraction(str(arms[f"hx@{n}"]["pooled"]["cost_per_answer"]))
        h = s1b.single("hx", n)
        chk.eq(f"Study 1b hx@{n} pooled single-try mean", mean(study1b.pooled(h)), arms[f"hx@{n}"]["pooled"]["mean"])
        for tag in ("hm", "hh", "hxh"):
            c = Fraction(str(arms[f"{tag}@{n}"]["pooled"]["cost_per_answer"]))
            k = min(math.floor(hx_c / c), s1b.tries(tag, n))
            v = s1b.vote(tag, n, k)
            out["study1b"][f"{tag}@{n}"] = {"k": k, "cost_ratio": float(hx_c / c), "designed_tries": s1b.tries(tag, n),   # type: ignore[index]
                                            "haiku_max_single_pooled": mean(study1b.pooled(h)), "vote_at_k_pooled": mean(study1b.pooled(v)),
                                            "paired": pooled_and_forms(f"fa1:study1b:{n}:hx-vs-{tag}", h, v)}
    out["note"] = ("d > 0 means one Haiku-max try scored higher than the lower-effort vote at the same money. Each row is within one "
                   "study and one set; the two studies are never pooled. Under the 1/m tie rule a 2-try vote scores about its single try.")
    return out


def fa2(s1b: Study1b, chk: Checks) -> Dict[str, object]:
    """Haiku-max vote curves at 6 and 12 steps (k = 1-10), per form and pooled, by the same code as the stamped 16-step curve
    (study1b.vote_curve, here for N = 6 and 12), and the equal-money vote against Opus-medium: k = floor(Opus-medium's pooled cost per
    answer / Haiku-max's), held to the 10 tries; paired d per form and pooled; cost per correct answer at that k."""
    out: Dict[str, object] = {}
    for n in (6, 12):
        shapes = (scoring.pieces_shape(n), scoring.chain_shape(n))
        rs = s1b.trows("hx", n)
        curves = {sh: {b: votes.vote_curve(d["answers"], d["correct"], kmax=s1b.tries("hx", n), detail=True, tie="random")
                       for b, d in sorted(five_tests._haiku_answers(rs, sh, "as_deployed", s1b.tries("hx", n), "official").items())
                       if d["answers"]} for sh in shapes}
        hx_cost = s1b.cost("hx", n)
        om_cost = s1b.cost("om", n)
        pts = []
        for kk in range(1, s1b.tries("hx", n) + 1):
            vals = {sh: {b: 100.0 * float(c[min(kk, len(c)) - 1]["acc"]) for b, c in curves[sh].items()} for sh in shapes}
            p: Dict[str, object] = {"k": kk}
            for lab, v in ((shapes[0], vals[shapes[0]]), (shapes[1], vals[shapes[1]]), ("pooled", study1b.pooled(vals))):
                p[lab] = band(v, f"fa2:hx-vote:{n}:{lab}:k{kk}")
            pts.append(p)
        chk.eq(f"hx@{n} vote@1 pooled = stamped single try", pts[0]["pooled"]["mean"],                    # type: ignore[index]
               s1b.a["descriptive"]["arms"][f"hx@{n}"]["pooled"]["mean"])
        ratio = lc(om_cost, "pooled") / lc(hx_cost, "pooled")                    # type: ignore[index]
        k = min(math.floor(ratio), s1b.tries("hx", n))
        v = s1b.vote("hx", n, k)
        o = {sh: five_tests.single_scores([dict(r, setup="opus-med") for r in s1b.rows
                                           if r["set_id"] == study1b.SETS[n] and r["tag"] == "om"], "opus-med", sh, "as_deployed")
             for sh in shapes}
        out[f"N={n}"] = {"curve": pts, "hx_cost_per_answer": hx_cost, "om_cost_per_answer": om_cost,
                         "equal_money": {"k": k, "om_over_hx_cost_ratio": float(ratio), "held_to_tries": s1b.tries("hx", n),
                                         "vote_mean_pooled": mean(study1b.pooled(v)), "om_mean_pooled": mean(study1b.pooled(o)),
                                         "vote_cost_per_answer_pooled": float(lc(hx_cost, "pooled") * k),     # type: ignore[index]
                                         "paired": pooled_and_forms(f"fa2:{n}:hx-vote-k{k}-vs-om", v, o)}}
    out["note"] = "Descriptive; never read a trend in the gap across lengths (plan, analysis 2)."
    return out


def fa3(s1b: Study1b, chk: Checks) -> Dict[str, object]:
    """B2's k-sensitivity at 16 steps: for k = 2-10 the paired d of the Haiku-max vote@k against Opus-medium (pooled over forms, as B2,
    and per form), with the cost ratio k x Haiku-max's cost per answer / Opus-medium's; then each form's own equal-money k =
    floor(Opus-medium's cost per answer in that form / Haiku-max's) and the per-form d at that k."""
    n = 16
    shapes = (scoring.pieces_shape(n), scoring.chain_shape(n))
    hx_cost, om_cost = s1b.cost("hx", n), s1b.cost("om", n)
    o = {sh: five_tests.single_scores([dict(r, setup="opus-med") for r in s1b.rows
                                       if r["set_id"] == study1b.SETS[n] and r["tag"] == "om"], "opus-med", sh, "as_deployed")
         for sh in shapes}
    rows = []
    for k in range(2, 11):
        v = s1b.vote("hx", n, k)
        res = pooled_and_forms(f"fa3:16:hx-vote-k{k}-vs-om", v, o)
        ratio = float(lc(hx_cost, "pooled") * k / lc(om_cost, "pooled"))          # type: ignore[index]
        rows.append({"k": k, "cost_ratio_pooled": ratio, **res})
        if k == int(s1b.kdoc["k"]):
            st = s1b.a["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["tests"]["B2"]
            chk.eq("B2 d at k from k.json (pooled)", res["pooled"]["d"], st["d"])                         # type: ignore[index]
    own = {}
    for sh in shapes:
        r_ = lc(om_cost, sh) / lc(hx_cost, sh)                                       # type: ignore[index]
        k = min(math.floor(r_), s1b.tries("hx", n))
        v = s1b.vote("hx", n, k)
        own[sh] = {"k": k, "om_over_hx_cost_ratio": float(r_), "vote_cost_per_answer": float(lc(hx_cost, sh) * k),  # type: ignore[index]
                   "om_cost_per_answer": float(lc(om_cost, sh)), "paired": paired(scoring.paired_differences(v[sh], o[sh]),
                                                                        f"fa3:16:own-k{k}:{sh}")}
    return {"by_k": rows, "own_equal_money_k": own, "hx_cost_per_answer": hx_cost, "om_cost_per_answer": om_cost,
            "note": "Post hoc sensitivity: B2 is unchanged; the k from k.json is the confirmatory one."}


# Analysis 4's cells: (name, source, key of the cell, key of its count of base puzzles or None to use `n`, n, full scale).
# The plan's list (7b43f91, analysis 4); C10's paired difference has no exact counterpart, so its two arms' accuracies are given.
FA4_CELLS = (
    ("Study 1b Opus-medium, 6 steps, pieces", "s1b", "descriptive.arms.om@6.6x1", "n_base", None, 100.0),
    ("Top-up comparator Opus-medium (main run), pieces", "topup", "accuracy.main-om.6x1", "n_base", None, 100.0),
    ("C10 Opus-low, pieces (main run)", "groupc", "item_C10.pairs.opus-low-vs-opus-med:6x1", None, "n", 100.0),
    ("C10 Opus-medium, pieces (main run)", "groupc", "item_C10.pairs.opus-low-vs-opus-med:6x1", None, "n", 100.0),
    ("Item 7 Opus-medium per-piece accuracy", "main", "reporting.group_b.item_7.per_piece_accuracy.arms.opus-med", "n_puzzles", None, 1.0),
    ("Item 7 Opus-low per-piece accuracy", "main", "reporting.group_b.item_7.per_piece_accuracy.arms.opus-low", "n_puzzles", None, 1.0),
    ("Length sweep Opus-medium per-step, 6 steps, pooled", "curve_d90", "models.om.by_n.6.per_step.pooled", "n_base", None, 1.0),
    ("Length sweep Opus-medium per-step, 6 steps, pieces (q's input)", "curve_d90", "models.om.by_n.6.per_step.nx1", "n_base", None, 1.0),
    ("Length sweep Opus-medium per-step, 16 steps, pooled", "curve_d90", "models.om.by_n.16.per_step.pooled", "n_base", None, 1.0),
    ("Length sweep Opus-medium per-step, 16 steps, pieces (q's input)", "curve_d90", "models.om.by_n.16.per_step.nx1", "n_base", None, 1.0),
    ("Study 1 Haiku-max 3-try vote, chains", "main", "reporting.group_b.item_10.arms.haiku-max 1x6.vote_curve.points.2", "n_base", None, 1.0),
    ("Study 1b Haiku-max vote@10, 16 steps, pieces", "s1b", "descriptive.vote_curve_n16.points.9.16x1", "n_base", None, 100.0),
    ("Study 1b Haiku thinking-off, 16 steps, chains", "s1b", "descriptive.arms.ho@16.1x16", "n_base", None, 100.0),
)


def _get(doc: Mapping[str, object], key: str) -> object:
    cur: object = doc
    for seg in key.split("."):
        cur = cur[int(seg)] if isinstance(cur, list) else cur[seg]                                  # type: ignore[index]
    return cur


def fa4(chk: Checks) -> Dict[str, object]:
    """Exact (Clopper-Pearson, two-sided 95%) intervals over base puzzles for the cells whose stamped bootstrap interval has zero width.
    Every such cell is at the scale's top (all right) or 0 (all wrong), so the count is n or 0 of n."""
    docs = {k: stamped(k) for k in ("main", "s1b", "topup", "groupc", "curve_d90")}
    out = []
    for name, src, key, nkey, nfield, full in FA4_CELLS:
        cell = _get(docs[src], key)
        if src == "groupc":
            arm = "opus-low" if "Opus-low" in name else "opus-med"
            m, n = float(cell["accuracy_means"][arm]), int(cell["n"])                                  # type: ignore[index]
            lohi = cell["ci95"]                                                                        # type: ignore[index]
            note = "the stamped interval is the paired difference's [0, 0]; each arm's exact accuracy interval is given instead"
        else:
            m, n = float(cell["mean"]), int(cell[nkey])                                                # type: ignore[index]
            lohi = cell["ci95"]                                                                        # type: ignore[index]
            note = None
        if float(lohi[0]) != float(lohi[1]):                                                           # type: ignore[index]
            raise ValueError(f"{name}: the stamped interval {lohi} does not collapse")
        if m not in (0.0, full):
            raise ValueError(f"{name}: mean {m} is neither 0 nor {full}: the count is not n or 0")
        x = n if m == full else 0
        lo, hi = report_arms.clopper_pearson(x, n)
        out.append({"cell": name, "source": STAMPED[src][0], "key": key, "stamped_mean": m, "stamped_ci95": lohi, "x": x, "n": n,
                    "unit": "points" if full == 100.0 else "share (0-1)",
                    "exact95": [lo * (100.0 if full == 100.0 else 1.0), hi * (100.0 if full == 100.0 else 1.0)], "note": note})
    return {"cells": out, "method": "report_arms.clopper_pearson(x, n), two-sided 95%, over base puzzles (the conservative unit)",
            "q_note": "the length sweep's q is estimated from pieces only, so its exact counterpart is the pieces per-step row"}


# Revision 2 of analysis 4 (Jarvis, 2026-10-15: covered by D-131, whose definition reads "wherever a bootstrap collapsed"). The first
# version's 13 cells were a hand list; revision 2 takes, by rule, every zero-width 95% interval in the stamped result files below, keeps
# the first version's cells (recomputed and checked equal to fa4.json) and adds the rest. Each family names the unit's full scale and
# where its base-puzzle count is stamped; a zero-width interval in no family and in no exclusion refuses the run.
FA4R2_FILES = ("main", "s1b", "topup", "curve", "curve_d90", "fa2r2")
FA4R2_FAMILIES = (   # (file, family in words, key pattern, full scale, where n is)
    ("main", "item 20: the vote at k = 40 within a bin and third",
     r"^reporting\.group_b\.item_20\.[^.]+\.bins\.[^.]+\.(thirds\.t[123]|too few wrong tries)\.mean_vote_at_k\.\d+$", 1.0, "bin n"),
    ("main", "item 10: a vote-curve point", r"^reporting\.group_b\.item_10\.arms\.[^.]+\.vote_curve\.points\.\d+$", 1.0, "n_base"),
    ("main", "item 24: a vote at its own equal-money k", r"^reporting\.group_b\.item_24\.table\.[^.]+\.vote_at_own_k\.[^.]+$", 100.0,
     "row base_puzzles"),
    ("main", "item 7: per-piece accuracy", r"^reporting\.group_b\.item_7\.per_piece_accuracy\.arms\.[^.]+$", 1.0, "n_puzzles"),
    ("s1b", "Study 1b: an arm at one length and shape", r"^descriptive\.arms\.[^.]+\.[^.]+$", 100.0, "n_base"),
    ("s1b", "Study 1b: a 16-step vote-curve point", r"^descriptive\.vote_curve_n16\.points\.\d+\.[^.]+$", 100.0, "n_base"),
    ("s1b", "Study 1b: a test's arm per shape", r"^per_form\.[^.]+\.[^.]+\.[^.]+$", 100.0, "n_base"),
    ("s1b", "Study 1b: the length sweep's points as copied", r"^descriptive\.length_curve\.ladder\.[^.]+\.\d+\.[^.]+$", 1.0, "n_base"),
    ("s1b", "Study 1b: a figure's copy of an arm",
     r"^descriptive\.(length_curve\.[^.]+\.\d+|effort_figure\.N=\d+\.[^.]+\.[^.]+)\.[^.]+$", 100.0, "matching arm"),
    ("topup", "top-up: an arm's accuracy", r"^accuracy\.[^.]+\.[^.]+$", 100.0, "n_base"),
    ("curve", "length sweep (original rule): per-step or whole-answer accuracy",
     r"^models\.[^.]+\.by_n\.\d+\.(per_step|whole_answer)\.[^.]+$", 1.0, "n_base"),
    ("curve", "length sweep (original rule): a Pilot 1 marker", r"^pilot1\.[^.]+\.[^.]+$", 1.0, "n_base"),
    ("curve_d90", "length sweep (Deviation 2 rule): per-step or whole-answer accuracy",
     r"^models\.[^.]+\.by_n\.\d+\.(per_step|whole_answer)\.[^.]+$", 1.0, "n_base"),
    ("curve_d90", "length sweep (Deviation 2 rule): a Pilot 1 marker", r"^pilot1\.[^.]+\.[^.]+$", 1.0, "n_base"),
    ("fa2r2", "free analysis 2: a Haiku-max vote-curve point", r"^result\.N=\d+\.curve\.\d+\.[^.]+$", 100.0, "n_base"),
)
FA4R2_EXCLUDED = (   # (file, key pattern, why)
    ("curve", r"^models\.[^.]+\.q$", "q pools every piece-step over all lengths and sets (clusters stratified by set), so no single "
                                     "count of base puzzles carries it, and its q^N bands are powers of its interval; no exact interval"),
    ("curve_d90", r"^models\.[^.]+\.q$", "as for the original rule's q"),
    ("main", r"^reporting\.group_b\.item_20\..*\.mean_vote_at_k\.\d+$",
     "item 20 at k below 40: FIG-02 draws the vote at k = 40 only, so these cells are printed nowhere"),
)
ITEM20_K = 40


def _json_sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def _zero_width(doc: object, path: str = "") -> List[Tuple[str, Mapping[str, object]]]:
    """Every dict holding a two-ended `ci95` whose ends are equal numbers, with its dotted key, in document order."""
    out: List[Tuple[str, Mapping[str, object]]] = []
    if isinstance(doc, dict):
        ci = doc.get("ci95")
        if (isinstance(ci, list) and len(ci) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in ci)
                and float(ci[0]) == float(ci[1])):
            out.append((path, doc))
        for k, v in doc.items():
            out += _zero_width(v, f"{path}.{k}" if path else str(k))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out += _zero_width(v, f"{path}.{i}")
    return out


def _fa4r2_n(docs: Mapping[str, object], src: str, key: str, cell: Mapping[str, object], where: str) -> Tuple[int, Optional[str]]:
    """The base-puzzle count for a collapsed cell, and the key it was read from when that is not the cell itself."""
    if where in ("n_base", "n_puzzles"):
        return int(cell[where]), None                                                           # type: ignore[call-overload]
    if where == "bin n":
        parent = key.rsplit(".mean_vote_at_k.", 1)[0]
        return int(_get(docs[src], parent)["n"]), parent + ".n"                                 # type: ignore[index,call-overload]
    if where == "row base_puzzles":
        row = key.split(".vote_at_own_k.", 1)[0]
        return int(_get(docs[src], row)["base_puzzles"]), row + ".base_puzzles"                 # type: ignore[index,call-overload]
    if where == "matching arm":
        segs = key.split(".")
        n_steps = segs[3] if segs[1] == "length_curve" else segs[2].split("=", 1)[1]
        shape = segs[-1]
        fields = ("mean", "designed", "final", "missing")
        arms = docs[src]["descriptive"]["arms"]                                                  # type: ignore[index]
        hits = [a for a, row in arms.items() if a.endswith(f"@{n_steps}") and isinstance(row.get(shape), dict)
                and all(row[shape].get(f) == cell.get(f) for f in fields)]
        if len(hits) != 1:
            raise ValueError(f"{src}:{key}: {len(hits)} arms match its mean, designed, final and missing at {n_steps} steps, {shape}")
        return int(arms[hits[0]][shape]["n_base"]), f"descriptive.arms.{hits[0]}.{shape}.n_base"  # type: ignore[index]
    raise ValueError(f"unknown count rule {where!r}")


def fa4r2(chk: Checks) -> Dict[str, object]:
    """Revision 2 of analysis 4: the exact (Clopper-Pearson, two-sided 95%) interval over base puzzles for every zero-width interval in
    the stamped result files (FA4R2_FAMILIES), the first version's cells first and unchanged."""
    import re
    first = fa4(chk)
    stamped_first = stamped("fa4")["result"]
    chk.eq("the first version's cells, recomputed, equal fa4.json's (SHA-256 of their JSON)", _json_sha(first["cells"]),
           _json_sha(stamped_first["cells"]))
    docs = {k: stamped(k) for k in FA4R2_FILES}
    have = {(c["source"], c["key"]) for c in first["cells"]}                                     # type: ignore[index]
    added: List[Dict[str, object]] = []
    found_first = set()
    excluded: Dict[str, int] = defaultdict(int)
    for src in FA4R2_FILES:
        for key, cell in _zero_width(docs[src]):
            fam = [f for f in FA4R2_FAMILIES if f[0] == src and re.match(f[2], key)]
            if len(fam) > 1:
                raise ValueError(f"{src}:{key} matches {len(fam)} families")
            if fam and fam[0][4] == "bin n" and int(cell["k"]) != ITEM20_K:                       # type: ignore[call-overload]
                fam = []
            if not fam:
                why = [x for x in FA4R2_EXCLUDED if x[0] == src and re.match(x[1], key)]
                if not why:
                    raise ValueError(f"{src}:{key}: a zero-width interval in no family and no exclusion")
                excluded[f"{src}: {why[0][2]}"] += 1
                continue
            _, family, _, full, where = fam[0]
            path = STAMPED[src][0]
            if (path, key) in have:
                found_first.add((path, key))
                continue
            m = float(cell["mean"])                                                              # type: ignore[arg-type]
            if m not in (0.0, full):
                raise ValueError(f"{src}:{key}: mean {m} is neither 0 nor {full}: the count is not n or 0")
            n, n_key = _fa4r2_n(docs, src, key, cell, where)
            x = n if m == full else 0
            lo, hi = report_arms.clopper_pearson(x, n)
            added.append({"cell": f"{family} ({key})", "family": family, "source": path, "key": key, "stamped_mean": m,
                          "stamped_ci95": cell["ci95"], "x": x, "n": n, "n_key": n_key,
                          "unit": "points" if full == 100.0 else "share (0-1)",
                          "exact95": [lo * (100.0 if full == 100.0 else 1.0), hi * (100.0 if full == 100.0 else 1.0)], "note": None})
    in_files = {(c["source"], c["key"]) for c in first["cells"] if c["source"] in {STAMPED[f][0] for f in FA4R2_FILES}}  # type: ignore[index]
    chk.eq("every first-version cell in these files is found again by the rule", len(found_first), len(in_files))
    if found_first != in_files:
        raise ValueError(f"the rule misses first-version cells: {sorted(in_files - found_first)}")
    return {"cells": list(first["cells"]) + added, "method": first["method"], "q_note": first["q_note"],  # type: ignore[call-overload]
            "first_version_cells": len(first["cells"]), "added_cells": len(added),                     # type: ignore[arg-type]
            "families": [{"file": STAMPED[f[0]][0], "family": f[1], "key_pattern": f[2], "n_from": f[4]} for f in FA4R2_FAMILIES],
            "excluded": [{"what": k, "zero_width_intervals": v} for k, v in sorted(excluded.items())]}


# Revision 3 of analysis 4 (D-144, the user via Jarvis, 2026-10-15): revision 2 read only fields named `ci95`, so it missed collapsed
# intervals stored under other names. Revision 3 keeps revision 2's 105 cells unchanged (checked equal to fa4r2.json) and scans EVERY
# field that holds an interval, by name (FA4R3_INTERVAL_FIELD), in the same files plus groupc. Each two-number field that is not an
# interval by that rule is listed by name in the output (FA4R3_NOT_INTERVALS), so the scan's reach is on record. A collapsed interval
# in no family and no exclusion refuses the run. Each exact interval is two-sided Clopper-Pearson over base puzzles at the stamped
# interval's own level (95% for a ci95, 90% for a ci90).
FA4R3_FILES = FA4R2_FILES + ("groupc",)
FA4R3_INTERVAL_FIELD = r"^(?:.*_)?(?:ci|cp|wilson)\d\d$|^band$|_bars$"
FA4R3_NOT_INTERVALS = {"quartiles": "the first and third quartiles of a spread, not an interval for an estimate"}
FA4R3_FAMILIES = (   # (file, family, key pattern of the dict holding the field, field, point field, full scale, n rule, level rule)
    ("main", "item 9e: the cascade's Opus-medium accuracy on its half of the base puzzles",
     r"^reporting\.group_b\.item_9e\.shapes\.[^.]+\.[^.]+\.(even|odd)$", "opus_accuracy_ci95", "opus_accuracy", 100.0, "half bases",
     "0.95"),
    ("main", "fairness check: a model's misapplied-house-rule rate per step (reported only, never a flag)",
     r"^(fairness|fairness_first_slip|reporting\.group_b\.item_14\.t_plus_g_minus\.indices)\.misapplied\.rate\.[^.]+$", "ci90",
     "point", 1.0, "block presets", "block level"),
)
FA4R3_EXCLUDED = (   # (file, key pattern of the dict holding the field, field, why)
    ("curve", r"^models\.[^.]+\.q(\.by_n\.\d+|\.\d+)$", "band", "q's q^N bands: powers of q's interval; q has no exact interval"),
    ("curve_d90", r"^models\.[^.]+\.q(\.by_n\.\d+|\.\d+)$", "band", "q's q^N bands: powers of q's interval; q has no exact interval"),
)


def _interval_fields(doc: object, path: str = "") -> List[Tuple[str, str, Mapping[str, object]]]:
    """Every (dotted key of the holding dict, field name, holding dict) whose field holds two numbers, in document order."""
    out: List[Tuple[str, str, Mapping[str, object]]] = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            if isinstance(v, list) and len(v) == 2 and all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in v):
                out.append((path, str(k), doc))
        for k, v in doc.items():
            out += _interval_fields(v, f"{path}.{k}" if path else str(k))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out += _interval_fields(v, f"{path}.{i}")
    return out


def _level(docs: Mapping[str, object], src: str, key: str, rule: str) -> float:
    if rule == "block level":
        block = key.split(".misapplied.", 1)[0]
        return float(_get(docs[src], block)["level"])                                            # type: ignore[index,arg-type]
    return float(rule)


def _fa4r3_n(docs: Mapping[str, object], src: str, key: str, rule: str) -> Tuple[int, str]:
    if rule == "half bases":
        parent, half = key.rsplit(".", 1)
        return int(_get(docs[src], parent)[f"{half}_bases"]), f"{parent}.{half}_bases"            # type: ignore[index,call-overload]
    if rule == "block presets":
        block = key.split(".misapplied.", 1)[0]
        presets = _get(docs[src], block)["presets"]                                              # type: ignore[index]
        return int(sum(int(v) for v in presets.values())), f"{block}.presets"                    # type: ignore[union-attr]
    raise ValueError(f"unknown count rule {rule!r}")


def fa4r3(chk: Checks) -> Dict[str, object]:
    """Revision 3 of analysis 4: revision 2's cells unchanged, plus every collapsed interval stored under any interval field name."""
    import re
    second = stamped("fa4r2")["result"]
    have = {(c["source"], c["key"], c.get("field", "ci95")) for c in second["cells"]}               # type: ignore[index]
    docs = {k: stamped(k) for k in FA4R3_FILES}
    rx = re.compile(FA4R3_INTERVAL_FIELD)
    added: List[Dict[str, object]] = []
    excluded: Dict[str, int] = defaultdict(int)
    fields_seen: Dict[str, int] = defaultdict(int)
    not_intervals: Dict[str, int] = defaultdict(int)
    zero_by_field: Dict[str, int] = defaultdict(int)
    for src in FA4R3_FILES:
        path = STAMPED[src][0]
        for key, field, cell in _interval_fields(docs[src]):
            if not rx.search(field):
                if field not in FA4R3_NOT_INTERVALS:
                    raise ValueError(f"{src}:{key}.{field}: a two-number field that is neither an interval by name nor listed as not one")
                not_intervals[field] += 1
                continue
            fields_seen[field] += 1
            lo, hi = cell[field]                                                                    # type: ignore[misc]
            if float(lo) != float(hi):
                continue
            zero_by_field[f"{src}: {field}"] += 1
            if field == "ci95" and (src != "groupc" or (path, key, "ci95") in have):
                continue                                  # revision 2's scope: its cells, exclusions and checks, carried over below
            if (path, key, field) in have:
                continue
            fam = [f for f in FA4R3_FAMILIES if f[0] == src and f[3] == field and re.match(f[2], key)]
            if not fam:
                why = [x for x in FA4R3_EXCLUDED if x[0] == src and x[2] == field and re.match(x[1], key)]
                if not why:
                    raise ValueError(f"{src}:{key}.{field}: a zero-width interval in no family and no exclusion")
                excluded[f"{src}: {why[0][3]}"] += 1
                continue
            _, family, _, _, point_field, full, n_rule, level_rule = fam[0]
            m = float(cell[point_field])                                                             # type: ignore[arg-type]
            if m not in (0.0, full) or float(lo) != m:
                raise ValueError(f"{src}:{key}: point {m} with interval {[lo, hi]} is not all right or all wrong")
            n, n_key = _fa4r3_n(docs, src, key, n_rule)
            level = _level(docs, src, key, level_rule)
            x = n if m == full else 0
            elo, ehi = report_arms.clopper_pearson(x, n, level=level)
            scale = 100.0 if full == 100.0 else 1.0
            pct = int(round(level * 100))                         # the interval names carry the level: ci95/exact95, ci90/exact90
            added.append({"cell": f"{family} ({key})", "family": family, "source": path, "key": key, "field": field,
                          "point_field": point_field, "level": level, "stamped_mean": m, f"stamped_ci{pct}": [lo, hi], "x": x, "n": n,
                          "n_key": n_key, "unit": "points" if full == 100.0 else "share (0-1)",
                          f"exact{pct}": [elo * scale, ehi * scale], "note": None})
    # revision 2's ci95 scope must be exactly what fa4r2.json covers and excludes (its counts are recomputed here)
    r2_cells = sum(1 for c in second["cells"] if c["source"] != STAMPED["groupc"][0])            # type: ignore[index]
    r2_excl = sum(int(e["zero_width_intervals"]) for e in second["excluded"])                    # type: ignore[index]
    ci95_zero = sum(v for k, v in zero_by_field.items() if k.endswith(": ci95") and not k.startswith("groupc"))
    chk.eq("zero-width ci95 intervals outside groupc = revision 2's cells there + its exclusions", ci95_zero, r2_cells + r2_excl)
    return {"cells": list(second["cells"]) + added, "method": second["method"] + "; at the stamped interval's own level (a 90% "
            "interval gets a 90% exact interval)", "q_note": second["q_note"],
            "revision_2_cells": len(second["cells"]), "added_cells": len(added),                  # type: ignore[arg-type]
            "families": list(second["families"]) + [{"file": STAMPED[f[0]][0], "family": f[1], "key_pattern": f[2], "field": f[3],
                                                    "n_from": f[6]} for f in FA4R3_FAMILIES],    # type: ignore[operator]
            "excluded": list(second["excluded"]) + [{"what": k, "zero_width_intervals": v} for k, v in sorted(excluded.items())],  # type: ignore[operator]
            "scan": {"interval_field_rule": FA4R3_INTERVAL_FIELD, "files": [STAMPED[f][0] for f in FA4R3_FILES],
                     "interval_fields": dict(sorted(fields_seen.items())), "zero_width_by_field": dict(sorted(zero_by_field.items())),
                     "two_number_fields_not_intervals": {k: {"count": v, "why": FA4R3_NOT_INTERVALS[k]} for k, v in sorted(not_intervals.items())}}}


def fa5(s1: Study1, chk: Checks) -> Dict[str, object]:
    """E-19: Holm in the inferiority direction over all five tests, from the locked bootstrap (same differences, seeds and B)."""
    ctx = s1.ctx
    kv = main_analysis.k_values(ctx["k"]["k_from_rows"], int(ctx["n"]))                            # type: ignore[index,call-overload]
    chk.eq("k_o and k_s as stamped (k.json)", [kv["k_o"], kv["k_s"]], [s1.a["k"]["k_o"], s1.a["k"]["k_s"]])
    diffs = five_tests.test_differences(list(ctx["rows"]), kv["k_o"], kv["k_s"], "as_deployed")      # type: ignore[call-overload]
    view = s1.a["confirmatory"]["views"]["as_deployed"]
    seed = int(view["seed"])
    p_inf, per = {}, {}
    for t in ("t1", "t2", "t3", "t4", "t5"):
        bt = bootstrap.bootstrap(diffs[t], int(view["B"]), bootstrap.derive_seed(seed, t))
        p = bootstrap.p_value(bt, float(view["margin"]))
        chk.eq(f"{t} locked p", p, view["tests"][t]["p"], tol=0.0)
        chk.eq(f"{t} locked d", bt.d, view["tests"][t]["d"], tol=0.0)
        p_inf[t] = 1.0 - p
        per[t] = {"d": bt.d, "p_noninferiority_locked": p, "p_inferiority": 1.0 - p,
                  "ci99": [bootstrap.lower_end(bt, 0.005), bootstrap.upper_end(bt, 0.995)],
                  "ci95": [bootstrap.lower_end(bt, 0.025), bootstrap.upper_end(bt, 0.975)]}
        chk.eq(f"{t} locked 95% interval", per[t]["ci95"], view["tests"][t]["ci95"])
        per[t]["ci99_excludes_margin"] = per[t]["ci99"][1] < float(view["margin"])                      # type: ignore[index]
    thr = bootstrap.holm_thresholds(p_inf, float(view["alpha"]))
    held = bootstrap.holm_one_sided(p_inf, float(view["alpha"]))
    for t in per:
        per[t]["holm_threshold"] = thr[t]
        per[t]["holm_inferior"] = held[t]
    return {"tests": per, "holm_order": bootstrap.holm_order(p_inf), "alpha": view["alpha"], "margin": view["margin"],
            "method": "E-19: p_inferiority = 1 - the locked non-inferiority p (H0: d >= -10); Holm over all five at alpha 0.025; the "
                      "99% interval from the same bootstrap as the stricter line",
            "disclosure": "chosen after the main results were open; the pre-registered unadjusted three-way reading stays the result"}


def _repeat(rows: Sequence[Mapping[str, object]], n: int) -> Dict[str, object]:
    """Item 4's pairwise repeat share (main_analysis.repeat_share, the locked pairing) on rows renamed to the setup it reads."""
    return main_analysis.repeat_share([dict(r, setup="haiku-med") for r in rows], n)


def fa6a(s1b: Study1b) -> Dict[str, object]:
    """E-20 step 1: the occupancy of item 20's bins at 16 steps from Haiku-medium alone (hm@16, 5 tries per puzzle). No Haiku-max value."""
    n = 16
    out: Dict[str, object] = {}
    for sh in (scoring.pieces_shape(n), scoring.chain_shape(n)):
        share = s1b.single("hm", n)[sh]
        counts = defaultdict(int)
        for b, pts_ in share.items():
            counts[min(9, int(pts_ // 10))] += 1
        total = sum(counts.values())
        out[sh] = {"bins": {report_votes.BIN_LABELS[b]: counts.get(b, 0) for b in range(10)}, "puzzles": total,
                   "largest_bin_share": max(counts.values()) / total,
                   "uninformative": max(counts.values()) / total > 0.8,
                   "bins_not_read": [report_votes.BIN_LABELS[b] for b in range(10) if 0 < counts.get(b, 0) < 3]}
    out["rule"] = ("E-20: hm@16 single-try accuracy over its 5 tries, 10-point bins (the last includes 100); a bin with fewer than 3 "
                   "puzzles is shown but not read; a shape whose largest bin holds more than 80% of its puzzles is uninformative")
    return out


def fa6b(s1: Study1, s1b: Study1b, occ: Mapping[str, object]) -> Dict[str, object]:
    """Repeat shares (item 4) for Haiku-max at 6, 12 and 16 steps and on Study 1's 3 tries, and for Haiku-high and Haiku-xhigh at 6 and
    16; then, per E-20, the 16-step Haiku-max vote (vote@6, B2's k, and vote@10) by item 20's hm@16 bins and Haiku-max's own thirds."""
    rep: Dict[str, object] = {"study1:haiku-max@6": _repeat(s1.arm("haiku-max", "1x6") + s1.arm("haiku-max", "6x1"), 6),
                              "study1:haiku-med@6": _repeat(s1.arm("haiku-med", "1x6") + s1.arm("haiku-med", "6x1"), 6)}
    for tag, ns in (("hx", (6, 12, 16)), ("hh", (6, 16)), ("hxh", (6, 16)), ("hm", (6, 16))):
        for n in ns:
            rep[f"study1b:{tag}@{n}"] = _repeat([r for r in s1b.rows if r["set_id"] == study1b.SETS[n] and r["tag"] == tag], n)
    n = 16
    k6 = int(s1b.kdoc["k"])
    bins_out: Dict[str, object] = {}
    for sh in (scoring.pieces_shape(n), scoring.chain_shape(n)):
        share = s1b.single("hm", n)[sh]
        if {lab: c for lab, c in occ[sh]["bins"].items()} != {report_votes.BIN_LABELS[b]: sum(1 for v in share.values()          # type: ignore[index]
                                                                                              if min(9, int(v // 10)) == b) for b in range(10)}:
            raise ValueError("the hm@16 occupancy differs from fa6a.json")
        hx = [r for r in s1b.rows if r["set_id"] == study1b.SETS[n] and r["tag"] == "hx" and r["shape"] == sh]
        wrong: Dict[str, List[object]] = defaultdict(list)
        for r in hx:
            if r.get("kind") == "missing" or scoring.row_correct(r, "official"):
                continue
            key = scoring.vote_key(r, "official")
            wrong[str(r["base_id"])].append(key if key is not None else object())
        single = s1b.single("hx", n)[sh]
        v6, v10 = s1b.vote("hx", n, k6)[sh], s1b.vote("hx", n, s1b.tries("hx", n))[sh]
        table: Dict[str, object] = {}
        for b in range(10):
            ids = sorted(i for i, v in share.items() if min(9, int(v // 10)) == b)
            lab = report_votes.BIN_LABELS[b]
            if not ids:
                table[lab] = {"puzzles": 0, "status": "empty"}
                continue
            agr = {i: scoring.pairwise_agreement(wrong.get(i, [])) for i in ids}
            few = [i for i in ids if not agr[i]["pairs"]]
            rest = sorted((float(agr[i]["share"]), i) for i in ids if agr[i]["pairs"])
            thirds = {name: [i for _, i in rest[j * len(rest) // 3:(j + 1) * len(rest) // 3]] for j, name in enumerate(("t1", "t2", "t3"))}

            def cell(sel: List[str]) -> Dict[str, object]:
                return {"puzzles": len(sel), "single_try_mean": mean({i: single[i] for i in sel}),
                        f"vote_at_{k6}_mean": mean({i: v6[i] for i in sel}), "vote_at_10_mean": mean({i: v10[i] for i in sel})}
            table[lab] = {"puzzles": len(ids), "status": "shown, not read" if len(ids) < 3 else "read", "all": cell(ids),
                          "too_few_wrong_tries": len(few), "thirds": {t: cell(s) for t, s in thirds.items() if s}}
        bins_out[sh] = {"uninformative": occ[sh]["uninformative"], "bins": table,                                        # type: ignore[index]
                        "unbinned": {"single_try_mean": mean(single), f"vote_at_{k6}_mean": mean(v6), "vote_at_10_mean": mean(v10)}}
    return {"repeat_share": rep, "bins_16": bins_out,
            "note": "Exploratory, no causal claim (repeats are not shown to cause or prevent anything). Puzzles kept and pairs are "
                    "the counts behind each share; a None vote key never agrees (D-72.1)."}


def fa7(s1: Study1, chk: Checks) -> Dict[str, object]:
    """Study 1: one Haiku-max try (per-base single-try accuracy over its tries) against one Opus-medium answer, per shape, paired."""
    out: Dict[str, object] = {}
    t24 = s1.a["reporting"]["group_b"]["item_24"]["table"]
    for shape in ("1x6", "6x1"):
        h = s1.single("haiku-max", shape)
        o = five_tests.single_scores(list(s1.ctx["rows"]), "opus-med", shape, "as_deployed")             # type: ignore[call-overload]
        chk.eq(f"Opus-medium {shape} mean", mean(o), t24[f"opus-med {shape}"]["accuracy_mean"])
        out[shape] = {"haiku_max_single": mean(h), "opus_medium": mean(o),
                      "paired": paired(scoring.paired_differences(h, o), f"fa7:haiku-max-vs-opus-med:{shape}")}
    out["note"] = "Exploratory arm, post hoc interval; d > 0 means the Haiku-max try scored higher."
    return out


def _split(rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    tries = [r for r in rows if r.get("kind") != "missing"]
    ok = [r for r in tries if r.get("format_status") == "ok"]
    right = [r for r in tries if scoring.row_correct(r, "official")]
    return {"tries": len(tries), "missing": sum(1 for r in rows if r.get("kind") == "missing"),
            "format_ok": len(ok), "unparseable": len(tries) - len(ok), "right": len(right),
            "parseable_but_wrong": sum(1 for r in ok if not scoring.row_correct(r, "official")),
            "right_but_not_format_ok": sum(1 for r in right if r.get("format_status") != "ok"),
            "accuracy_all_tries": len(right) / len(tries) if tries else None,
            "accuracy_on_parseable_conditional": (sum(1 for r in ok if scoring.row_correct(r, "official")) / len(ok)) if ok else None,
            "status_counts": dict(sorted(defaultdict(int, {s: sum(1 for r in tries if r.get("format_status") == s)
                                                           for s in {str(r.get("format_status")) for r in tries}}).items()))}


def fa8(s1: Study1, s1b: Study1b) -> Dict[str, object]:
    """Haiku thinking-off: failures split into unparseable (format status not ok) and parseable-but-wrong, with accuracy on parseable
    tries (labelled conditional), by study, length and shape."""
    out: Dict[str, object] = {}
    for shape in ("1x6", "6x1"):
        out[f"study1:6:{shape}"] = _split(s1.arm("haiku-thinking-off", shape))
    for n in (6, 16):
        for sh in (scoring.chain_shape(n), scoring.pieces_shape(n)):
            out[f"study1b:{n}:{sh}"] = _split([r for r in s1b.rows if r["set_id"] == study1b.SETS[n] and r["tag"] == "ho" and r["shape"] == sh])
    out["note"] = ("Unparseable = the official format status is not 'ok' (D-90 rule); accuracy on parseable tries is conditional on "
                   "format and is not a whole-answer accuracy.")
    return out


def _tokens(calls: Mapping[str, Mapping[str, object]], select: Callable[[Mapping[str, object]], Optional[str]]) -> Dict[str, object]:
    from ..pareto import prices
    acc: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for cid, c in calls.items():
        g = select(c)
        if g is None or c.get("no_usage"):
            continue
        u = c["usage"]
        think = int((c.get("usage_raw") or {}).get("output_tokens_details", {}).get("thinking_tokens") or 0) if "usage_raw" in c else None
        a = acc[g]
        a["calls"] += 1
        a["input"] += float(u.prompt_tokens)
        a["output"] += float(u.output_tokens)
        a["list_usd"] += float(c["list"])
        if think is not None:
            a["thinking"] += think
            a["thinking_usd"] += float(prices.cost(str(c["model"]), prices.Usage(output_tokens=think), batch=False))
    out = {}
    for g, a in sorted(acc.items()):
        n = a["calls"]
        out[g] = {"calls": int(n), "mean_input_tokens": a["input"] / n, "mean_output_tokens": a["output"] / n,
                  "mean_thinking_tokens": a.get("thinking", 0.0) / n, "thinking_share_of_output": (a.get("thinking", 0.0) / a["output"]) if a["output"] else None,
                  "thinking_share_of_list_cost": (a.get("thinking_usd", 0.0) / a["list_usd"]) if a["list_usd"] else None,
                  "list_cost_per_call": a["list_usd"] / n}
    return out


def fa10(s1: Study1, s1b: Study1b) -> Dict[str, object]:
    """N1 (D-131 item 9): the API's own thinking-token counts (usage_raw.output_tokens_details.thinking_tokens) and measured token
    usage per arm, shape and length; thinking share of output tokens and of list cost (thinking tokens at the model's list output rate,
    prices.cost); Haiku-max/Opus-medium output-token and cost-per-call ratios per length and shape."""
    def with_raw(ctx: Mapping[str, object]) -> Dict[str, Dict[str, object]]:
        cs = report_costs.calls(ctx)                                                                 # type: ignore[arg-type]
        raw = {str(r["custom_id"]): r.get("usage_raw") for r in ctx["records"]}                      # type: ignore[union-attr]
        return {cid: dict(c, usage_raw=raw.get(cid) or {}) for cid, c in cs.items()}
    c1 = with_raw(s1.ctx)
    t1 = _tokens(c1, lambda c: f"{c['arm']} {c['shape']}" if c.get("arm") else None)
    c1b = with_raw(s1b.ctx)
    set_n = {v: k for k, v in study1b.SETS.items()}
    shape_n = {}
    for n in study1b.SETS:
        shape_n[scoring.chain_shape(n)] = n
        shape_n[scoring.pieces_shape(n)] = n
    t1b = _tokens(c1b, lambda c: f"{c['tag']}@{shape_n.get(str(c['shape']))} {c['shape']}" if c.get("tag") and str(c.get("shape")) in shape_n else None)
    ratios: Dict[str, object] = {}
    for sh in ("1x6", "6x1"):
        a, b = t1.get(f"haiku-max {sh}"), t1.get(f"opus-med {sh}")
        if a and b:
            ratios[f"study1:6:{sh}"] = {"output_tokens": a["mean_output_tokens"] / b["mean_output_tokens"],
                                        "list_cost_per_call": a["list_cost_per_call"] / b["list_cost_per_call"]}
    for n in (6, 12, 16):
        for sh in (scoring.chain_shape(n), scoring.pieces_shape(n)):
            a, b = t1b.get(f"hx@{n} {sh}"), t1b.get(f"om@{n} {sh}")
            if a and b:
                ratios[f"study1b:{n}:{sh}"] = {"output_tokens": a["mean_output_tokens"] / b["mean_output_tokens"],
                                               "list_cost_per_call": a["list_cost_per_call"] / b["list_cost_per_call"]}
    return {"study1": t1, "study1b": t1b, "haiku_max_over_opus_medium": ratios,
            "label_n1": "post hoc; thinking tokens as the API reports them (Edith's settlement N1)",
            "note": "Measured usage from the final records (no estimate); list prices from harness/pareto/prices.py."}


def fa9(s1b: Study1b, chk: Checks) -> Dict[str, object]:
    """D-133 (Edith's OK on the written definition): Sonnet-high on Study 1b's 6-step set (ext40, 40 bases) against Opus-low,
    Opus-medium, one Haiku-max try and Sonnet-medium: per-base single-try scores (official, as_deployed; an arm with several tries per
    item contributes its per-base mean), paired d = Sonnet-high minus the comparator per form and pooled (study1b.pooled), bootstrap
    paired_bca (B = 10,000), seed names "fa9:sh-vs-<tag>:<form|pooled>"; d and the 95% interval only. Cost ratio: Sonnet-high's list
    cost per answer / the comparator's (study1b.cost_per_answer); cost-per-correct ratio: the stamped descriptive.arms cpc values."""
    n = 6
    arms = s1b.a["descriptive"]["arms"]
    sh = s1b.single("sh", n)
    sh_cost = s1b.cost("sh", n)
    for tag in ("sh", "sm", "ol", "om", "hx"):
        chk.eq(f"{tag}@6 pooled single-try mean", mean(study1b.pooled(s1b.single(tag, n))), arms[f"{tag}@6"]["pooled"]["mean"])
    out: Dict[str, object] = {}
    for tag in ("ol", "om", "hx", "sm"):
        co = s1b.single(tag, n)
        c_cost = s1b.cost(tag, n)
        forms = list(sh) + ["pooled"]
        out[f"sh-vs-{tag}"] = {
            "comparator": STUDY1B_NAMES[tag], "sonnet_high_mean": {f: mean(study1b.pooled(sh)) if f == "pooled" else mean(sh[f]) for f in forms},
            "comparator_mean": {f: mean(study1b.pooled(co)) if f == "pooled" else mean(co[f]) for f in forms},
            "paired": pooled_and_forms(f"fa9:sh-vs-{tag}", sh, co),
            "cost_ratio": {f: float(lc(sh_cost, f) / lc(c_cost, f)) for f in forms},
            "cpc_ratio": {f: (arms["sh@6"][f]["cpc"]["cpc"] / arms[f"{tag}@6"][f]["cpc"]["cpc"]) for f in forms}}
    out["label"] = "post hoc exploratory; against Test 5 a cross-study reading (Study 1b's 6-step set, not Study 1's)"
    out["note"] = ("The 6-step set includes the two partly shown bases (C-066), which were never shown to a model under test; no "
                   "sensitivity run is needed (Edith, ops/reviews/2026-10-15-labelling-and-fa9-fa12-definitions.md).")
    return out


STUDY1B_NAMES = {"ol": "Opus-low", "om": "Opus-medium", "hx": "Haiku-max, one try", "sm": "Sonnet-medium"}
RHO_PRIME = (10, 20, 40, 80)


def _unbounded(x: Optional[float]) -> object:
    return "unbounded" if x is not None and math.isinf(x) else x


def fa12(s1: Study1, s1b: Study1b, chk: Checks) -> Dict[str, object]:
    """D-133 (Edith's OK on the written definition): re-pricing at a comparator:Haiku list price ratio per token rho' in {10, 20, 40, 80}
    (item 9d's rho, the same for input and output; the pinned table's is 40 for Opus, 20 for Sonnet), the measured token counts held.
    (a) Tests 1-3 and B2: R' = R x rho'/rho_list (R: the stamped equal-money cost ratio, k.json), k' = floor(R') held to the samples
        drawn (40 Haiku-medium, 10 Haiku-max), k' < 1 not run; the vote at k' by the locked code; gap = vote mean - comparator mean and
        its paired BCa 95% interval (seed "fa12:<test>:rho<rho'>"), no reading. At rho' = rho_list the row must reproduce the locked k
        and d (checks).
    (b) Item 9d's break-even for Haiku-max against Opus-medium at 6, 12 and 16 steps, per form and pooled: k_match = the smallest k in
        1..10 whose vote mean is at least (report_costs.at_least) Opus-medium's mean on the same bases; R_list = Opus-medium's mean list
        cost per answer / Haiku-max's mean list cost per try (report_costs.base_costs; pooled: study1b._pooled_costs); rho* = rho_list x
        k_match / R_list; 9d's interval: k_match, R_list and rho* recomputed in each replicate of the cluster bootstrap (one stratum of
        all bases, 2,000 draws, seed "fa12:break_even:<N>:<form|pooled>"), no k_match = +inf, kept, printed "unbounded".
    (c) Item 9f's cached view is read from the stamped Study 1 file by the table, not recomputed here."""
    from . import report_costs as rc
    out: Dict[str, object] = {"rho_prime": list(RHO_PRIME)}
    kdoc = s1.ctx["k"]
    view = s1.a["confirmatory"]["views"]["as_deployed"]["tests"]
    tests = {"t1": ("opus-med", "6x1", "opus"), "t2": ("opus-med", "1x6", "opus"), "t3": ("sonnet-med", "1x6", "sonnet")}
    rows: Dict[str, object] = {}
    for t, (comp, shp, side) in tests.items():
        R = Fraction(str(kdoc["k_from_rows"][side][shp]["ratio"]))                                      # type: ignore[index]
        rho = rc._rho_list(rc.COMPARATOR_MODEL[comp])
        c = five_tests.single_scores(list(s1.ctx["rows"]), comp, shp, "as_deployed")                    # type: ignore[call-overload]
        per = []
        for rp in RHO_PRIME:
            r_new = R * rp / rho
            k = min(math.floor(r_new), report_votes.designed("haiku-med"))
            if k < 1:
                per.append({"rho_prime": rp, "R_prime": float(r_new), "k": 0, "status": "not run (k < 1)"})
                continue
            v = s1.vote("haiku-med", shp, k)
            pr = paired(scoring.paired_differences(v, c), f"fa12:{t}:rho{rp}")
            per.append({"rho_prime": rp, "R_prime": float(r_new), "k": k, "held_to_samples": math.floor(r_new) > k,
                        "vote_mean": mean(v), "comparator_mean": mean(c), "gap": mean(v) - mean(c), "paired": pr})          # type: ignore[operator]
            if Fraction(rp) == rho:
                chk.eq(f"{t}: k at rho_list = k.json k", k, kdoc["k_from_rows"][side][shp]["k"])                        # type: ignore[index]
                chk.eq(f"{t}: d at rho_list = the locked d", pr["d"], view[t]["d"])
        rows[t] = {"comparator": comp, "shape": shp, "R_list": float(R), "rho_list": float(rho), "by_rho": per}
    R = Fraction(str(s1b.kdoc["ratio"]))
    rho = rc._rho_list(rc.COMPARATOR_MODEL["opus-med"])
    n = 16
    o = {sh_: five_tests.single_scores([dict(r, setup="opus-med") for r in s1b.rows if r["set_id"] == study1b.SETS[n] and r["tag"] == "om"],
                                       "opus-med", sh_, "as_deployed") for sh_ in (scoring.pieces_shape(n), scoring.chain_shape(n))}
    per = []
    for rp in RHO_PRIME:
        r_new = R * rp / rho
        k = min(math.floor(r_new), s1b.tries("hx", n))
        if k < 1:
            per.append({"rho_prime": rp, "R_prime": float(r_new), "k": 0, "status": "not run (k < 1)"})
            continue
        v = s1b.vote("hx", n, k)
        vp, op = study1b.pooled(v), study1b.pooled(o)
        pr = paired(scoring.paired_differences(vp, op), f"fa12:B2:rho{rp}")
        per.append({"rho_prime": rp, "R_prime": float(r_new), "k": k, "held_to_samples": math.floor(r_new) > k,
                    "vote_mean": mean(vp), "comparator_mean": mean(op), "gap": mean(vp) - mean(op), "paired": pr})      # type: ignore[operator]
        if Fraction(rp) == rho:
            chk.eq("B2: k at rho_list = k.json k", k, s1b.kdoc["k"])
            chk.eq("B2: d at rho_list = the locked d", pr["d"],
                   s1b.a["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["tests"]["B2"]["d"])
    rows["B2"] = {"comparator": "om", "N": n, "R_list": float(R), "rho_list": float(rho), "by_rho": per}
    out["tests"] = rows
    be: Dict[str, object] = {}
    rho_o = rc._rho_list(rc.COMPARATOR_MODEL["opus-med"])
    for n in (6, 12, 16):
        shapes = (scoring.pieces_shape(n), scoring.chain_shape(n))
        votes_k = {k: s1b.vote("hx", n, k) for k in range(1, s1b.tries("hx", n) + 1)}
        om = {sh_: five_tests.single_scores([dict(r, setup="opus-med") for r in s1b.rows if r["set_id"] == study1b.SETS[n] and r["tag"] == "om"],
                                            "opus-med", sh_, "as_deployed") for sh_ in shapes}
        hx_c = {sh_: rc.base_costs(s1b.ctx, "hx", sh_)[0] for sh_ in shapes}
        om_c = {sh_: rc.base_costs(s1b.ctx, "om", sh_)[0] for sh_ in shapes}
        groups = {sh_: ({k: votes_k[k][sh_] for k in votes_k}, om[sh_], hx_c[sh_], om_c[sh_]) for sh_ in shapes}
        groups["pooled"] = ({k: study1b.pooled(votes_k[k]) for k in votes_k}, study1b.pooled(om), study1b._pooled_costs(s1b.ctx, "hx", n),
                            study1b._pooled_costs(s1b.ctx, "om", n))
        res_n: Dict[str, object] = {}
        for g, (vk, oc, hc, cc) in groups.items():
            bases = sorted(b for b in oc if all(b in vk[k] for k in vk) and hc.get(b) is not None and cc.get(b) is not None)

            def solve(sample: List[str], vk=vk, oc=oc, hc=hc, cc=cc) -> Tuple[Optional[int], Fraction, Fraction, float]:
                m = len(sample)
                target = math.fsum(oc[b] for b in sample) / m
                km = next((k for k in sorted(vk) if rc.at_least(math.fsum(vk[k][b] for b in sample) / m, target)), None)
                c_pp = sum((cc[b] for b in sample), Fraction(0)) / m
                h_pt = sum((hc[b] for b in sample), Fraction(0)) / m
                return km, c_pp, h_pt, target

            km, c_pp, h_pt, target = solve(bases)
            infs, zero_c, zero_h, both = [0], [0], [0], [0]

            def stat(sample: List[object], solve=solve, infs=infs, zero_c=zero_c, zero_h=zero_h, both=both) -> Optional[float]:
                """Item 9d's replicate rules, as report_costs.item_9d writes them."""
                k2, c2, h2, _ = solve([str(x) for x in sample])
                if k2 is None:
                    infs[0] += 1
                    return math.inf
                if h2 == 0 and c2 == 0:
                    both[0] += 1
                    return None
                if h2 == 0:
                    zero_h[0] += 1
                    return 0.0
                if c2 == 0:
                    zero_c[0] += 1
                    return math.inf
                return float(rho_o * k2 / (c2 / h2))

            lo, hi = cluster_bootstrap([bases], stat, f"fa12:break_even:{n}:{g}", draws=DRAWS, seed=FA_SEED)  # type: ignore[arg-type]
            r = (c_pp / h_pt) if h_pt else None
            if km is None:
                star: object = "no break-even within 10 tries"                               # 9d's wording, held to Haiku-max's 10 tries
            elif not h_pt and not c_pp:
                star = "undefined (both sides $0: R_list = 0/0)"
            elif not h_pt:
                star = 0.0
            elif not c_pp:
                star = "unbounded"
            else:
                star = float(rho_o * km / r)                                                    # type: ignore[operator]
            res_n[g] = {"n_bases": len(bases), "k_cap": s1b.tries("hx", n), "opus_medium_mean": target,
                        "k_match": km if km is not None else star, "R_list": None if r is None else float(r), "rho_list": float(rho_o),
                        "rho_star": star, "ci95": [_unbounded(lo), _unbounded(hi)], "bootstrap_name": f"fa12:break_even:{n}:{g}",
                        "share_replicates_no_k_match": infs[0] / DRAWS, "replicates_no_k_match": infs[0],
                        "share_replicates_zero_haiku_cost": zero_h[0] / DRAWS, "share_replicates_zero_comparator_cost": zero_c[0] / DRAWS,
                        "replicates_dropped_both_sides_zero": both[0]}
            if n in (6, 12):
                fa2 = json.loads((ROOT / "data/main/free-analyses/fa2r2.json").read_text())["result"][f"N={n}"]["curve"]
                for p_ in fa2:
                    key = g if g != "pooled" else "pooled"
                    chk.eq(f"hx vote@{p_['k']} at N={n} {g} equals fa2r2's mean", mean(vk[int(p_["k"])]), p_[key]["mean"])
        be[f"N={n}"] = res_n
    out["break_even_haiku_max"] = be
    out["cached_view"] = "item 9f is read from data/main/main-l14n6-1/analysis.json reporting.group_b.item_9f (not recomputed)"
    out["label"] = "post hoc sensitivity: how far the equal-money readings rest on one price list; no reading"
    return out


# D-157 names this analysis "free analysis 13"; the plan's own item 13 (re-scoring Study 1b) was never approved, so the definition is
# the register's row, read from the commit that added it (never retyped).
FA13_RULING = ("decisions/register.md", "ee30f69", "D-157")


def register_definition(path: str, commit: str, did: str) -> Dict[str, str]:
    raw = subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], check=True, capture_output=True, text=True).stdout
    rows = [ln for ln in raw.splitlines() if ln.startswith(f"| {did} |")]
    if len(rows) != 1:
        raise ValueError(f"{path} at {commit}: expected one row for {did}, found {len(rows)}")
    cells = [c.strip() for c in rows[0].strip().strip("|").split(" | ")]
    if len(cells) != 6:
        raise ValueError(f"{path} at {commit}: {did}'s row has {len(cells)} cells, not 6")
    return {"source": f"{path} at {commit}, row {did}", **dict(zip(("id", "ruling", "status", "date", "user_words", "note"), cells))}


def _tie_patterns(answers: Sequence[Optional[str]], correct: str, k: int) -> Dict[str, object]:
    """Every k-subset of one base's tries, enumerated (C(10, 6) = 210): the credit under each tie rule and, for each subset whose credit a
    tie decided (the right answer tied for the top count with at least one other answer, as votes.py counts it), the tie's pattern
    '<top count>x<answers tied>' (e.g. '3x2' for 3-3). Cross-checks the locked dynamic programme."""
    import itertools
    from collections import Counter
    n_sub = 0
    credit = {"random": Fraction(0), "wrong": Fraction(0)}
    decided: Dict[str, int] = defaultdict(int)
    for sub in itertools.combinations(answers, k):
        n_sub += 1
        counts = Counter(a for a in sub if a is not None)
        if not counts:
            continue
        top = max(counts.values())
        tied = [a for a, c in counts.items() if c == top]
        if correct not in tied:
            continue
        if len(tied) == 1:
            credit["random"] += 1
            credit["wrong"] += 1
            continue
        credit["random"] += Fraction(1, len(tied))
        decided[f"{top}x{len(tied)}"] += 1
    return {"n_subsets": n_sub, "acc": {r: credit[r] / n_sub for r in credit}, "decided": dict(decided)}


def fa13(s1b: Study1b, chk: Checks) -> Dict[str, object]:
    """D-157: the tie view for Test B2 (Haiku-max vote@k against Opus-medium at 16 steps, k from k.json), as Study 1's D-33 tie
    sensitivity (five_tests.tie_report) gives it for Tests 1-3. First B2 is reproduced: the locked family (study1b.family, seed 20261013)
    on the locked differences (study1b.test_differences, as deployed), every stamped B2 field checked equal at both margins. Then:
    (1) how often a tie decides: per form, the mean over base puzzles of the share of k-subsets of the 10 tries in which a tie holding
    the right answer decided the credit (votes.py's tie_decided_share, as tie_report); pooled, the mean over base puzzles of the two
    forms' mean; split by the tie's pattern ('3x2' is a 3-3 tie) from a full enumeration that is checked against the locked count; and
    the base puzzles with at least one such subset. (2) B2's gap with ties counted wrong: the vote scored with tie="wrong" (every tie
    scores 0), paired d (vote minus Opus-medium) per form and pooled, bootstrap paired_bca (B = 10,000), seed names
    "fa13:B2:ties-as-wrong:<form|pooled>"; d and the 95% interval only, no p and no reading (D-131's rule for free analyses)."""
    n = 16
    k = int(s1b.kdoc["k"])
    designed = study1b.DESIGNED[study1b.CHALLENGER]
    view = "as_deployed"
    st = s1b.a["confirmatory"]
    diffs, left = study1b.test_differences(s1b.rows, k, view)
    held = {t: study1b.NOT_COMPLETED for t in study1b.not_completed(s1b.rows)}
    chk.eq("B2 bases left out (as deployed)", left["B2"], st["primary_margin_5"]["views"][view]["bases_left_out"]["B2"])
    for label, margin in study1b.MARGINS:
        fam = study1b.family(diffs, margin, B, held)
        want = st[label]["views"][view]["tests"]["B2"]
        for key in sorted(want):
            chk.eq(f"B2 {label} {key} (as deployed)", list(fam["tests"]["B2"][key]) if key == "ci95" else fam["tests"]["B2"][key], want[key])

    trows = study1b.test_rows(s1b.rows, study1b.SETS[n])
    shapes = (scoring.pieces_shape(n), scoring.chain_shape(n))
    o = study1b.form_scores(trows, n, "o", view)
    v = study1b.form_scores(trows, n, "v", view, k, designed)
    vw = {sh: five_tests.vote_scores(trows, sh, k, view, tie="wrong", designed=designed) for sh in shapes}
    det = {sh: five_tests.vote_scores(trows, sh, k, view, detail=True, designed=designed) for sh in shapes}
    chk.eq("B2 d recomputed from the per-form vote and Opus-medium scores (pooled)",
           math.fsum(scoring.paired_differences(study1b.pooled(v), study1b.pooled(o))) / len(diffs["B2"]),
           st["primary_margin_5"]["views"][view]["tests"]["B2"]["d"])

    share: Dict[str, object] = {}
    per_base: Dict[str, Dict[str, float]] = {}                       # {form: {base: share of subsets a tie decided}}
    per_base33: Dict[str, Dict[str, float]] = {}                     # the same, 3-3 ties only
    for sh in shapes:
        pats: Dict[str, int] = defaultdict(int)
        n_sub = 0
        per_base[sh], per_base33[sh] = {}, {}
        enum: Dict[str, List[float]] = {"share": [], "random": [], "wrong": []}
        bases = sorted(five_tests._haiku_answers(trows, sh, view, designed).items())
        for b, d in bases:
            e = _tie_patterns(d["answers"], d["correct"], min(k, len(d["answers"])))
            dec = sum(e["decided"].values())                                                                       # type: ignore[union-attr]
            per_base[sh][b] = float(Fraction(dec, e["n_subsets"]))                                                 # type: ignore[arg-type]
            per_base33[sh][b] = float(Fraction(e["decided"].get("3x2", 0), e["n_subsets"]))                       # type: ignore[union-attr,arg-type]
            enum["share"].append(per_base[sh][b])
            enum["random"].append(100.0 * float(e["acc"]["random"]))                                               # type: ignore[index]
            enum["wrong"].append(100.0 * float(e["acc"]["wrong"]))                                                 # type: ignore[index]
            n_sub += e["n_subsets"]                                                                                # type: ignore[operator]
            for p_, c in e["decided"].items():                                                                     # type: ignore[union-attr]
                pats[p_] += c
        locked = {"share": [det[sh][b]["tie_decided_share"] for b, _ in bases], "random": [v[sh][b] for b, _ in bases],   # type: ignore[index]
                  "wrong": [vw[sh][b] for b, _ in bases]}
        for key, what in (("share", "tie-decided share = votes.py's"), ("random", f"vote@{k}, ties at 1/m = the locked vote_scores"),
                          ("wrong", f"vote@{k}, ties wrong = vote_scores(tie='wrong')")):
            chk.eq(f"{sh}: base puzzles whose enumerated {what} differs (of {len(bases)})",
                   sum(1 for a, b_ in zip(enum[key], locked[key]) if a != b_), 0)
        share[sh] = {"tie_decided_share": mean(per_base[sh]), "tie_decided_share_3_3": mean(per_base33[sh]), "n_base": len(per_base[sh]),
                     "bases_with_a_decided_tie": sum(1 for x in per_base[sh].values() if x > 0), "subsets": n_sub,
                     "decided_subsets_by_pattern": dict(sorted(pats.items()))}
    pooled_share = study1b.pooled(per_base)
    share["pooled"] = {"tie_decided_share": mean(pooled_share), "tie_decided_share_3_3": mean(study1b.pooled(per_base33)),
                       "n_base": len(pooled_share),
                       "bases_with_a_decided_tie_in_either_form": sum(1 for b in pooled_share if any(per_base[sh][b] > 0 for sh in shapes))}

    wrong = pooled_and_forms("fa13:B2:ties-as-wrong", vw, o)
    forms = list(shapes) + ["pooled"]
    means = {f: {"vote_ties_at_1_over_m": mean(study1b.pooled(v)) if f == "pooled" else mean(v[f]),
                 "vote_ties_wrong": mean(study1b.pooled(vw)) if f == "pooled" else mean(vw[f]),
                 "opus_medium": mean(study1b.pooled(o)) if f == "pooled" else mean(o[f])} for f in forms}
    for f in forms:
        means[f]["shift_points"] = means[f]["vote_ties_wrong"] - means[f]["vote_ties_at_1_over_m"]                  # type: ignore[operator]
    chk.eq("pooled shift = d(ties wrong) - B2's d", means["pooled"]["shift_points"],
           wrong["pooled"]["d"] - st["primary_margin_5"]["views"][view]["tests"]["B2"]["d"], tol=1e-9)             # type: ignore[index,operator]
    return {"test": "B2", "N": n, "k": k, "k_source": "data/main/study1b-1/k.json", "designed_tries": designed, "view": view,
            "reproduced": {lab: {key: st[lab]["views"][view]["tests"]["B2"][key] for key in ("d", "ci95", "p", "reading")}
                           for lab, _ in study1b.MARGINS},
            "tie_decided": share, "ties_as_wrong": {"paired": wrong, "means": means},
            "label": "post hoc (D-157), labelled post hoc in the Study 1b appendix; no reading; B2's pre-registered reading is unchanged",
            "note": ("A tie decides a vote when the right answer is tied for the top count with another answer; under the locked rule it "
                     "then scores 1/m (m answers tied), here 0. With k = 6 a 3-3 tie is '3x2'; '2x2' and '2x3' are 2-2 and 2-2-2 "
                     "ties, and so on. shift_points = mean vote with ties wrong minus mean vote with ties at 1/m.")}


# ================================================================ the command

def undefined_to_null(obj: object, path: str = "", found: Optional[List[str]] = None) -> Tuple[object, List[str]]:
    """The locked scoring.pooled_repeat_share returns NaN for a share or mean over zero pairs or puzzles: written as null (JSON has no
    NaN), each place listed in the output's `undefined_as_null`."""
    found = [] if found is None else found
    if isinstance(obj, float) and math.isnan(obj):
        found.append(path)
        return None, found
    if isinstance(obj, dict):
        return {k: undefined_to_null(v, f"{path}.{k}" if path else str(k), found)[0] for k, v in obj.items()}, found
    if isinstance(obj, (list, tuple)):
        return [undefined_to_null(v, f"{path}.{i}", found)[0] for i, v in enumerate(obj)], found
    return obj, found


def interval_sanity(obj: object, path: str = "", out: Optional[Dict[str, list]] = None) -> Dict[str, list]:
    """Edith's checklist 2b, recorded in every output: each 2-number interval (`ci95`, or analysis 4's `exact95` / `exact90`) beside a point (`d`,
    `mean`, `rho_star`, or analysis 4's `stamped_mean`) must contain it (1e-9 tolerance) and have width; a zero-width interval is
    listed with its point (it is legitimate only when its data are all right or all wrong, which the reviewer checks). A cell holding
    both a `ci95` and an `exact95` is checked for each."""
    out = {"checked": [], "zero_width": [], "point_outside": []} if out is None else out
    if isinstance(obj, dict):
        pt = next((obj[k] for k in ("d", "mean", "rho_star", "stamped_mean")
                   if isinstance(obj.get(k), (int, float)) and not isinstance(obj.get(k), bool)), None)
        for name in ("ci95", "exact95", "exact90"):
            ci = obj.get(name)
            if (isinstance(ci, list) and len(ci) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in ci)
                    and pt is not None):
                where = path if name == "ci95" else f"{path}.{name}"
                out["checked"].append(where)
                if ci[0] == ci[1]:
                    out["zero_width"].append({"where": where, "point": pt})
                if not (ci[0] - 1e-9 <= pt <= ci[1] + 1e-9):
                    out["point_outside"].append({"where": where, "point": pt, name: ci})
        for k, v in obj.items():
            interval_sanity(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            interval_sanity(v, f"{path}.{i}", out)
    return out


def write_once(out_dir: Path, name: str, n: Optional[int], body: Dict[str, object], inputs: Dict[str, object], checks: Checks,
               definition: Optional[Dict[str, str]] = None) -> str:
    """`definition` (None: the plan's item n) is given only where the analysis is not the plan's item n (analysis 13, D-157)."""
    path = Path(out_dir) / f"{name}.json"
    if path.exists():
        raise SystemExit(f"{path} exists: each free analysis runs once and never overwrites its output")
    doc = {"analysis": name, "label": LABEL, "definition": definition if definition is not None else plan_definition(n) if n else None,
           "code": {"module": "harness/analysis/free_analyses.py", "module_sha256": sha256(Path(__file__)), "git_head": _git("rev-parse", "HEAD"),
                    "git_dirty": bool(_git("status", "--porcelain", "--", "harness")), "fa_seed": FA_SEED, "B": B, "draws": DRAWS},
           "inputs": inputs, "checks": checks.items}
    clean, nulls = undefined_to_null(body)
    doc["result"] = clean
    doc["undefined_as_null"] = nulls
    san = interval_sanity(clean)
    doc["interval_sanity"] = {"checked": len(san["checked"]), "zero_width": san["zero_width"], "point_outside": san["point_outside"]}
    text = json.dumps(doc, indent=1, sort_keys=True, default=lambda o: float(o) if isinstance(o, (Fraction, Decimal)) else str(o),
                      allow_nan=False) + "\n"
    with open(path, "x") as f:
        f.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--which", required=True, help="comma-separated: 1,2r2,3,4r3,5,6a,6b,7,8,9,10,12,13")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--main-set", type=Path, required=True)
    ap.add_argument("--main-run", type=Path, required=True)
    ap.add_argument("--main-k", type=Path, required=True)
    ap.add_argument("--s1b-run", type=Path, required=True)
    ap.add_argument("--s1b-k", type=Path, required=True)
    a = ap.parse_args(argv)
    which = [x.strip() for x in a.which.split(",") if x.strip()]
    a.out.mkdir(parents=True, exist_ok=True)
    s1 = Study1(a.main_set, a.main_run, a.main_k) if set(which) & {"1", "5", "6b", "7", "8", "10", "12"} else None
    s1b = Study1b(a.s1b_run, a.s1b_k) if set(which) & {"1", "2r2", "3", "6a", "6b", "8", "9", "10", "12", "13"} else None
    both = {**({"study1": s1.inputs} if s1 else {}), **({"study1b": s1b.inputs} if s1b else {})}
    for w in which:
        chk = Checks()
        definition = None
        if w == "1":
            res, n = fa1(s1, s1b, chk), 1                                                        # type: ignore[arg-type]
        elif w == "2":
            raise SystemExit("fa2.json is the first version's record; the corrected analysis 2 is --which 2r2")
        elif w == "2r2":
            res, n = fa2(s1b, chk), 2                                                            # type: ignore[arg-type]
            res["revision"] = {"of": "fa2.json", "number": 2,
                               "why": "fa2.json's cluster-bootstrap bands collapsed to their means: band() passed one stratum per base "
                                      "instead of one stratum holding every base (as study1b._boot does); the means, the paired "
                                      "differences and the costs are computed by unchanged code"}
        elif w == "3":
            res, n = fa3(s1b, chk), 3                                                            # type: ignore[arg-type]
        elif w == "4":
            raise SystemExit("fa4.json is the first version's record; the revision covering every collapsed interval is --which 4r2")
        elif w == "4r2" and (a.out / "fa4r2.json").exists():
            raise SystemExit("fa4r2.json is revision 2's record; the revision covering every interval field is --which 4r3")
        elif w == "4r2":
            res, n = fa4r2(chk), 4
            res["revision"] = {"of": "fa4.json", "number": 2,
                               "why": "fa4.json covered a hand list of 13 collapsed cells; the definition reads 'wherever a bootstrap "
                                      "collapsed', so revision 2 takes every zero-width interval in the stamped result files by rule "
                                      "(Jarvis, 2026-10-15, under D-131), keeping the first version's cells unchanged"}
        elif w == "4r3":
            res, n = fa4r3(chk), 4
            res["revision"] = {"of": "fa4r2.json", "number": 3,
                               "why": "fa4r2.json read only fields named ci95, so it missed collapsed intervals stored under other names: item "
                                      "9e's Opus-medium accuracy on the even base puzzles (opus_accuracy_ci95, printed in TAB-08) and the "
                                      "fairness check's misapplied-rule rates (ci90, printed nowhere). Revision 3 (D-144) keeps revision 2's "
                                      "cells unchanged and scans every interval field by name, listing every two-number field it does not "
                                      "treat as an interval"}
        elif w == "5":
            res, n = fa5(s1, chk), 5                                                             # type: ignore[arg-type]
        elif w == "6a":
            res, n = fa6a(s1b), 6                                                                # type: ignore[arg-type]
        elif w == "6b":
            occ = json.loads((a.out / "fa6a.json").read_text())["result"]
            res, n = fa6b(s1, s1b, occ), 6                                                       # type: ignore[arg-type]
        elif w == "7":
            res, n = fa7(s1, chk), 7                                                             # type: ignore[arg-type]
        elif w == "8":
            res, n = fa8(s1, s1b), 8                                                             # type: ignore[arg-type]
        elif w == "9":
            res, n = fa9(s1b, chk), 9                                                            # type: ignore[arg-type]
        elif w == "12":
            res, n = fa12(s1, s1b, chk), 12                                                      # type: ignore[arg-type]
        elif w == "10":
            res, n = fa10(s1, s1b), 10                                                           # type: ignore[arg-type]
        elif w == "13":
            res, n, definition = fa13(s1b, chk), 13, register_definition(*FA13_RULING)             # type: ignore[arg-type]
        else:
            raise SystemExit(f"unknown analysis {w!r}")
        inputs = both if w not in ("4r2", "4r3") else {"stamped_files": {k: {"path": STAMPED[k][0], "sha256": STAMPED[k][1]}
                                                                       for k in sorted(set(FA4R3_FILES) | {"fa4", "fa4r2"}
                                                                                       if w == "4r3" else set(FA4R2_FILES) | {"groupc", "fa4"})}}
        h = write_once(a.out, f"fa{w}", n, res, inputs, chk, definition)
        print(f"wrote {a.out}/fa{w}.json (SHA-256 {h}); checks: {len(chk.items)} equal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
