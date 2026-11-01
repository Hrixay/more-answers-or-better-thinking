"""Study 1b's analysis, end to end, by the LOCKED code only (spec `study1b-spec.md`, Karen, Edith CLEAN; frozen in lock 4 at 9c007e5, D-98 names: §4 the
confirmatory tests B1-B3, §6 the descriptive outputs, on the run the slim runner made under §3 and §7). Plumbing: it calls the locked
functions in the spec's order and writes one JSON file.

    python3 -m harness.analysis.study1b --run <run folder> --k <run folder>/k.json --out <file> [--plan data/plans/study1b-plan.json]

Sealing (§9 steps 2, 3 and 6): this file, `study1b_k.py` and their tests are reviewed by Edith and stamped in prereg-lock-4 BEFORE any
call. After the run, k is computed from costs only (`study1b_k`) and committed with its SHA-256 in LOG; then this driver runs ONCE, on
the finished log, and its output is committed with the log hashes. It refuses to overwrite its output file, and it refuses to run
without Study 1's analysis.json or the ladder's curve file (§6 needs both; Edith S-D3). The output holds hashes and repository-relative
names, never an absolute path.

Inputs: the run folder as `harness.pareto.slim` wrote it (Edith S-D1), and k.json.
- The plan is the run folder's OWN copy, `slim_plan.json` (written by the runner at its first start). A `--plan` given must be the same
  plan (by `slim.plan_sha256`). The sets are loaded and checked exactly as the runner loads them (`slim.load_sets`: the deep verify,
  the plan's items_sha256 and steps). Every arm, sent or cut, is checked against §3's table (model, effort, thinking, tries per item);
  each test set must be §2's set for its length, the trial-round sets must be the ladder sets, and hx and om must be planned at
  N = 16 and N = 6.
- The call log's `calibration_limits` line (one; cross-checked with `calibration_limits.json`) gives each calibrated arm's max_tokens:
  such arms carry `calibrate` in the plan, not `max_tokens`. Its `cut` line (one) names the arms §7's cost-only cut order removed; if
  the cut was still over, the `projection_accepted` line must be there. Both lines must carry this plan's hash. An arm of B1-B3 in the
  cut, or an arm outside the plan's cut order, raises.
- The manifest (required) is rebuilt by the runner's own builder, `slim.manifest_requests` (the trial round plus every test arm at its
  floor, as the runner writes it), and must match manifest.json's item_set_sha256 and n_items.

What it computes, in order:
1. rows. The planned rows are the requests the run actually SENT, rebuilt by the runner's own builder (`slim.sent_test_requests`:
   custom_id <item id>-<tag>-<NN>, calibrated arms at their limits, cut arms left out). Every final record (`main_rows.final_records`)
   of a test set is scored by `main_rows.score_row` (the D-76 score with D-90's repeat rule: the official score; keys read from the
   frozen items); every sent try with no final record is `main_rows.missing_row` (kind "missing": wrong in every view, a vote for
   nothing). A final record outside the sent requests (a cut arm's included), or with another max_tokens or request hash, raises. An
   arm the cut removed is reported as "cut by §7 (cost)", never as missing or as 0%. The trial round (§7) runs on
   `ladder-ledger-l14n{6,12,16}-v1`: its records are identified by set id, cut to their cost fields as they are read, never scored,
   and reported only as tokens and costs (§6, step 9 below).
2. k: READ from k.json (`study1b_k`); the driver refuses to run without it, checks it was made from this run's compact_table.csv, and
   recomputes it (`study1b_k.k_from_table`); a difference raises. k from the call log's records (item 9a's list cost, `report_costs.calls`)
   is reported beside it.
3. the per-base scores (§4, form pooling). The test arms' rows are passed to the locked five_tests functions under the arm names those
   functions read (hx as "haiku-med", om as "opus-med"; nothing else changes): h_b per form is `five_tests.single_scores` (the share
   right of the arm's tries, `scoring.arm_scores`; as deployed that is the 10 designed tries, a missing try wrong), o_b the same over
   Opus's 2 designed tries, v_b per form is `five_tests.vote_scores(k, designed=10)` (`votes.vote_accuracy_at_k`: exact vote@k, an
   unreadable try a vote for nothing, ties at 1/m). Each base's score is the mean over its two forms. In the refusals-out and
   truncations-out views the locked functions leave the dropped tries out (a vote with k held to what is left); a base with no score
   left in one form, for either arm, drops out of that test in that view (counted).
4. the family (§4): `bootstrap.run_family` over B1 (h - o, N = 16), B2 (v - o, N = 16) and B3 (h - o, N = 6), B = 10,000, base seed
   20261013 (per-test seeds derive_seed(20261013, "B1" | "B2" | "B3")), one-sided alpha 0.025, Holm across these three only, the
   three-way reading; in all three views; at margin -5.0 (primary) and -10.0 (secondary). If k < 1 B2 is not run and keeps its Holm
   place with p = 1 (as five_tests._family). "No worse" is a headline only if it holds in all three views (D-68 F3).
4a. the completeness gate (lock-4 audit A1; Edith's ruling): per test and arm (hx, om) the designed tries (the requests sent), the
   final ones and the missing ones are counted (`completeness`). A test is COMPLETED only if every designed try of both its arms has a
   final record (a refusal, truncation or unreadable answer is final). A test not completed reads "not completed" in every view and at
   both margins, with no reading: it keeps its Holm place with p = 1 (as B2's k < 1 rule); its §10 line is the not-completed
   template, filled from the counts ("Test B1 was not completed: m of its n designed tries have no final record, so we give it no
   reading."; m and n over both arms); its error-rate ratio is not reported; its per-form numbers are computed on the tries with a
   final record only, labelled "not completed; descriptive only" (Edith L-2). Without the gate an unsent set scores 0 for both arms, every difference is 0, and the locked bootstrap's
   degenerate case would read it "no worse". The bootstrap is unchanged.
4b. item 16's exclude-missing view (D-48 row 23; Study 1's `report_arms.exclude_missing_view`) for B1-B3, beside the family as a
   labelled sensitivity: as deployed, with only the missing tries (kind "missing") left out (a missing single try leaves the arm's
   share over the tries left; missing Haiku-max tries drop from the vote, with k held to what is left; a base with no try left drops),
   at both margins, same k, B, seeds and Holm. Computed only when a try of hx or om at N = 16 or 6 is missing; else "no missing items".
   On a completed test it equals the main view; a test not completed keeps its Holm place at p = 1 (as in the main view) and gets
   only d, its 95% interval (cluster bootstrap) and the bases used, on its tries with a final record, labelled "not completed;
   descriptive only": never a reading (spec §4, D-103(F); Edith L-1).
5. beside every test: the error-rate ratio (`main_analysis.ratio_from_errors`, item 1's rules: +inf draws kept, 0/0 dropped and counted)
   with B = 10,000 and seed derive_seed(20261013, f"{test}:error_ratio"); when Opus has 0 errors, the two-sided 95% Clopper-Pearson upper
   bound 1 - 0.025^(1/n) on n = Opus's DESIGNED tries in the test (320 at N = 16, 160 at N = 6). And the cost (item 9, list price, B5-free
   refusals at $0): mean dollars per answer (`report_costs.base_costs`, item 9b: a sampled arm's mean per designed try, a designed try
   with no record at $0) for each arm, the vote at k costing k answers, with "about 1/k of the cost" (k measured). B2's wording says
   "for less than Opus's price" exactly when the cost ratio is above 10 (k.json's `capped`, checked against its ratio).
5a. the D-97 sensitivity (spec §2): the whole family of 4 and the error-rate ratios of 5 re-run without the exposed test bases
   (main-ledger-l14n16-v1 base 000; ext40-ledger-l14n6-v1 bases 000 and 003), so B1/B2 over 79 bases and B3 over 38, with the same k,
   B, seeds, margins and Holm, labelled "sensitivity: exposed bases excluded", appendix only. §6 is not re-run. The completeness gate
   of 4a applies as in the primary family (a test not completed in the run is not completed here either).
6. per form (§4): h, o, v and d for each form with a cluster bootstrap over base puzzles (`curve.cluster_bootstrap`, 2,000 draws, seed
   20261013, names "1b:<test>:<N>:<form>:<h|o|v|d>"). Descriptive.
7. §6 per arm x set x form / pooled: accuracy (official, as deployed, each puzzle the share right of its designed tries) with its
   interval, named "1b:<tag>:<N>:<form|pooled>", 2,000 draws, seed 20261013: the cluster bootstrap for multi-try arms, Clopper-Pearson
   (`report_arms.clopper_pearson`) for one-try arms (per form: x right of n bases; pooled: x right of the 2n tries); beside each, the
   list cost per answer (item 9b, `report_costs.cost_block` / `base_costs`) and the cost per correct answer (item 9c,
   `report_costs.cpc_block` per form; pooled the same arithmetic, `report_costs._cpc`). Then the effort figure (N = 6: Haiku off to max,
   Sonnet low to max, Opus low to max; N = 16: Haiku off to max plus Opus-medium), with Study 1's N = 6 points (its analysis.json,
   item 24) drawn separately and labelled; the length curve (Haiku-max and Opus-medium at 6, 12, 16; Haiku-medium at 6 and 16) with the
   ladder's D-87 curve (data/pilot/curve-ladder-l14n-1-d90.json) behind it, labelled. An arm the §7 cut removed appears in each as
   "cut by §7 (cost)", with no accuracy.
7a. a run stopped early (spec §6 at 9c007e5, lock-4 audit C1; Edith's pass-2 ruling): every §6 entry (each arm block, per form and
   pooled, and each point of the effort figure, the length curve and the vote curve) carries its designed, final and missing try
   counts. hx and om at a length whose test the gate (4a) holds (B1/B2 at 16, B3 at 6) are computed on their final tries only and
   labelled "not completed; descriptive only" (the vote curve with k held to the tries left, as per_form). An arm (or form) with no
   final try reads "not sent (run stopped)", with its counts and no accuracy, never 0%. Any other arm with a missing try keeps the
   official as-deployed score (a missing try wrong, spec §4) with its counts, and beside it the exclude-missing view on its final tries,
   labelled "sensitivity: missing tries excluded".
8. the equal-money vote curve of Haiku-max at N = 16, k = 1..10 (item 8's vote: `votes.vote_curve` over `five_tests._haiku_answers` with
   the 10 designed tries, official, as deployed, ties at random): per form and pooled, the mean with the cluster bootstrap
   "1b:hx-vote:16:<form|pooled>" (one name for every k, X1), the cost per answer k x hx's (9b) beside Opus-medium's, and the CPC at
   each k (9c's arithmetic).
9. format compliance, refusals, truncations and missing items for every arm (item 16's rates, `report_arms.item_16`, per set; item 17's
   flag, `report_arms.item_17`; `five_tests.format_report`), and the trial round's tokens and costs (calls, input and output
   tokens, list cost by item 9a, logged Batch cost; by set and tag).
`choices` lists every point the spec left open and the option this file implements.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from . import bootstrap, five_tests, kscript, main_analysis, main_rows, report_arms, report_costs, scoring, study1b_k, votes
from .curve import cluster_bootstrap
from ..pareto import slim
from ..pareto.main import MainSetup
from ..pareto.outcome import usage_from_raw
from ..pareto.prices import HAIKU, OPUS, SONNET

ROOT = Path(__file__).resolve().parents[2]
SPEC = "research/study1b-spec.md at 9c007e5 (the spec frozen in lock 4, Edith CLEAN; SHA-256 4b6779502c26ae1da96b55573b0f9e62d153caa4509ef543b748c5d70a72c879), sections 2, 4, 6 and 7"

SETS = {16: "main-ledger-l14n16-v1", 6: "ext40-ledger-l14n6-v1", 12: "main-ledger-l14n12-v1"}
CALIBRATION_SETS = ("ladder-ledger-l14n6-v1", "ladder-ledger-l14n12-v1", "ladder-ledger-l14n16-v1")   # §7's trial round: never scored
TESTS = {"B1": (16, "single"), "B2": (16, "vote"), "B3": (6, "single")}
CHALLENGER, COMPARATOR = "hx", "om"
DESIGNED = {CHALLENGER: 10, COMPARATOR: 2}
H, O = "haiku-med", "opus-med"               # the arm names five_tests' locked scorers read (vote_scores reads "haiku-med" only)
BASE_SEED = 20261013
FAMILY_B = bootstrap.DRAWS                   # 10,000
DRAWS = 2_000
MARGINS = (("primary_margin_5", -5.0), ("secondary_margin_10", -10.0))
K_CAP = study1b_k.CAP
LADDER_CURVE = ROOT / "data" / "pilot" / "curve-ladder-l14n-1-d90.json"
STUDY1_ANALYSIS = ROOT / "data" / "main" / "main-l14n6-1" / "analysis.json"
NOT_RUN = "not run (k < 1: one Haiku-max try costs more than one Opus-medium try)"
NOT_COMPLETED = ("not completed (a designed try of hx or om in this test's set has no final record): no reading; Holm place kept "
                 "with p = 1")
NOT_COMPLETED_TEMPLATE = "Test {t} was not completed: {m} of its {n} designed tries have no final record, so we give it no reading."
NOT_COMPLETED_DESCRIPTIVE = "not completed; descriptive only"   # spec §4: a held test's numbers on the tries with a final record
EXCLUDE_MISSING_LABEL = "exclude-missing view (only missing tries left out; otherwise as_deployed): a sensitivity beside the family"
NO_MISSING = "no missing items in B1-B3's arms (hx and om at N = 16 and N = 6)"
CUT_LABEL = "cut by §7 (cost)"                # an arm the §7 cut order removed: never sent, never "missing" or 0%
NOT_SENT = "not sent (run stopped)"           # spec §6 (C1): an arm (or form) with no final try: counts only, never 0%
MISSING_EXCLUDED_LABEL = "sensitivity: missing tries excluded"   # spec §6 (C1): a partly sent arm's view on its final tries
COUNT_KEYS = ("designed", "final", "missing")
CAPPED_WORDING = study1b_k.CAPPED_LABEL       # B2's label when the cost ratio is above 10 (§4)
EFFORT_ORDER = ("off", "low", "medium", "high", "xhigh", "max")
# D-97 (spec §2): test bases partly shown in helper or review sessions. They stay in the primary tests; the sensitivity re-runs
# the whole B1-B3 family without them (B1/B2 over 79 bases, B3 over 38), same B, seeds, margins and Holm, labelled and appendix-only.
EXPOSED_BASES = {"main-ledger-l14n16-v1": (0,), "ext40-ledger-l14n6-v1": (0, 3)}
SENSITIVITY_LABEL = "sensitivity: exposed bases excluded"
STUDY1_LABEL = "Study 1 (other puzzles, exploratory)"
LADDER_LABEL = "ladder (D-87), other puzzles"

# §3's table: tag -> (model, effort, thinking off); (N, tag) -> tries per item.
SPEC_ARMS = {"hx": (HAIKU, "max", False), "om": (OPUS, "medium", False), "ho": (HAIKU, "medium", True), "hl": (HAIKU, "low", False),
             "hm": (HAIKU, "medium", False), "hh": (HAIKU, "high", False), "hxh": (HAIKU, "xhigh", False),
             "sl": (SONNET, "low", False), "sm": (SONNET, "medium", False), "sh": (SONNET, "high", False),
             "sxh": (SONNET, "xhigh", False), "sx": (SONNET, "max", False), "ol": (OPUS, "low", False), "oh": (OPUS, "high", False),
             "oxh": (OPUS, "xhigh", False), "ox": (OPUS, "max", False)}
SPEC_N = {**{(16, t): n for t, n in (("hx", 10), ("om", 2), ("ho", 5), ("hl", 5), ("hm", 5), ("hh", 5), ("hxh", 5))},
          **{(6, t): n for t, n in (("hx", 10), ("om", 2), ("ho", 5), ("hl", 5), ("hm", 5), ("hh", 5), ("hxh", 5), ("sl", 1),
                                    ("sm", 1), ("sh", 1), ("sxh", 1), ("sx", 1), ("ol", 1), ("oh", 1), ("oxh", 1), ("ox", 1))},
          **{(12, t): n for t, n in (("hx", 10), ("om", 1))}}

CHOICES = {
    "views_pooling": "In refusals_out / truncations_out a base whose score is undefined in either form (every try of that form dropped) "
                     "leaves that test in that view (Study 1: a dropped single answer drops the base); bases dropped are counted.",
    "error_ratio_seed": "main_analysis.ratio_from_errors (locked, item 1) is called with its module seed set to 20261013 for the call "
                        "and restored after, so the draws are Random(derive_seed(20261013, f'{test}:error_ratio')).",
    "error_ratio_zero": "Opus 0 errors: the Clopper-Pearson bound replaces the locked one (which uses the number of bases) with n = the "
                        "test's designed Opus tries (bases x 2 forms x 2); the locked over-bases value is kept beside it.",
    "cost_per_answer": "item 9b's base_costs / cost_block (a designed try with no record at $0, X4), pooled = per-base mean of the two "
                       "forms; k itself uses the mean over real calls (cost-only rows), as §4 says. The '1/k' wording uses k.json's k for "
                       "B1 and B2, and floor(om / hx cost per answer at N = 6) for B3.",
    "one_try_pooled_interval": "a one-try arm's pooled point uses Clopper-Pearson on x right of the 2n tries (§6: 'Clopper-Pearson for "
                               "one-try arms').",
    "bootstrap_names": "§4 per-form intervals '1b:<test>:<N>:<form>:<h|o|v|d>'; the vote curve '1b:hx-vote:16:<form|pooled>'; <arm> in "
                       "'1b:<arm>:<N>:...' is the tag (hx, om, ...); <form> is the shape (16x1, 1x16).",
    "cpc_seed": "item 9c's CPC and 9b's cost intervals come from report_costs (locked), which draws with its own seed 20261012 and "
                "names 'cpc:<tag>:<shape>' / 'cost_mean:<tag>:<shape>'; the pooled CPC is named 'cpc:<tag>:<N>:pooled'.",
    "headline_template": "§10's template per test: 'holds' only if no worse in all three views; 'inconclusive' / 'worse' from the "
                         "as-deployed reading; an as-deployed 'no worse' that fails another view is reported as such (no §10 template).",
    "manifest_check": "the run's manifest.json is required; its item_set_sha256 and n_items must equal the list the runner wrote, "
                      "rebuilt by slim.manifest_requests (the trial round plus every test arm at its floor).",
    "plan_as_run": "the plan is the run folder's slim_plan.json; calibrated arms' max_tokens are the call log's calibration_limits "
                   "line (cross-checked with calibration_limits.json); the scored rows are planned from the requests actually sent "
                   "(slim.sent_test_requests); an arm in the cut line's cut_arms was never sent and is reported as 'cut by §7 (cost)' in "
                   "§6, never as missing or 0%; a still-over cut needs the projection_accepted line.",
    "b2_label": "B2's 'for less than Opus's price' applies when the cost ratio is above 10 (k.json's capped = ratio > 10, set by "
                "study1b_k and re-checked here); at a ratio of exactly 10, k = 10 with 'about Opus-medium's price'.",
    "inputs_required": "Study 1's analysis.json and the ladder's D-87 curve file must exist (§6 draws both); the output names files "
                       "relative to the repository (or by file name), never by absolute path.",
    "ladder_curve": "the D-90 ladder curve file (official repeat rule), Haiku-medium and Opus-medium whole-answer points.",
    "completeness_gate": "lock-4 audit A1 (Edith's ruling): a test is completed only if every designed try (request sent) of hx and om in "
                         "its set has a final record; else it reads 'not completed' in every view and margin, p = 1 in its Holm place, "
                         "§10's not-completed line (m, n over both arms), no error-rate ratio, per-form numbers on its final tries only "
                         "labelled 'not completed; descriptive only'; the D-97 sensitivity uses the run's gate. If k < 1, B2 reads "
                         "'not run'.",
    "exclude_missing_view": "item 16 / D-48 row 23 as Study 1 (report_arms.exclude_missing_view): as_deployed with only kind 'missing' "
                            "left out (singles over the tries left, the vote with designed=0 so k is held to what is left), both margins, "
                            "same k, B, seeds and Holm; computed only if a try of hx or om at N = 16 or 6 is missing. Its Holm family "
                            "holds a test not completed at p = 1 (so a completed test equals the main view); such a test gets d, a "
                            "cluster-bootstrap interval (2,000 draws) and the bases used on its final tries, 'not completed; "
                            "descriptive only', never a reading (spec §4, D-103(F); Edith L-1).",
    "run_stopped_section_6": "spec §6 at 9c007e5 (lock-4 audit C1; Edith's pass-2 ruling): every §6 entry (arm blocks per form and "
                             "pooled, effort figure, length curve, vote curve) carries designed / final / missing try counts (designed = "
                             "the requests the run sent; a §7-cut arm stays 'cut by §7 (cost)' with no counts, as it was never sent). hx "
                             "and om at a length the gate holds: final tries only, 'not completed; descriptive only'. No final try: 'not "
                             "sent (run stopped)', no accuracy. Otherwise a missing try keeps the official as-deployed score with its "
                             "counts, plus the exclude-missing view labelled 'sensitivity: missing tries excluded'.",
    "run_stopped_open_points": "points §6 leaves open, as implemented: (a) the 'not sent (run stopped)' rule is applied per form too (a "
                               "form with no final try has counts and no accuracy; the pooled as-deployed point still counts its "
                               "missing tries wrong, as spec §4); (b) an arm of hx/om at a held length with no final try at all reads "
                               "'not sent (run stopped)' (nothing to describe); (c) the final-tries-only numbers (held hx/om and the "
                               "sensitivity) use the same bootstrap names and seed as the as-deployed point, the same item 9b cost per "
                               "answer (a designed try with no record at $0), and the CPC by item 9c's arithmetic (report_costs._cpc) "
                               "over the final-tries scores; (d) the vote curve at a held N = 16 uses each base's final tries with k "
                               "held to the tries left (as per_form's vote), a base with none left dropping out.",
}


# ---------------------------------------------------------------- the run as the runner wrote it: plan, limits, cut, rows

def _sha(path: Path) -> Optional[str]:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _rel(path: Path) -> str:
    """A path for the output: relative to the repository when inside it, else the file name only (never an absolute path)."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT.resolve()))
    except ValueError:
        return p.name


def check_section_3(plan: Mapping[str, object], test_ids: Mapping[int, str], cal_ids: Sequence[str]) -> None:
    """The runner's plan against the spec: each test set is §2's set for its length, each arm (sent or cut) is §3's (model, effort,
    thinking, tries per item), the trial-round sets are the ladder sets, and hx and om are planned at N = 16 and N = 6."""
    for s in plan["sets"]:                                                                       # type: ignore[union-attr]
        n = int(s["steps"])
        sid = test_ids[n]
        if SETS.get(n) != sid:
            raise ValueError(f"{sid} is not a Study 1b set (§2: {sorted(SETS.values())})")
        for a in s["arms"]:
            tag = str(a["tag"])
            if tag not in SPEC_ARMS or (n, tag) not in SPEC_N:
                raise ValueError(f"arm {tag} at N = {n} is not in §3's table")
            got = (a["model"], a["effort"], bool(a.get("thinking_off", False)))
            if got != SPEC_ARMS[tag] or int(a["n"]) != SPEC_N[(n, tag)]:
                raise ValueError(f"arm {tag} at N = {n} is {got} x{a['n']}, §3 says {SPEC_ARMS[tag]} x{SPEC_N[(n, tag)]}")
    for sid in cal_ids:
        if sid not in CALIBRATION_SETS:
            raise ValueError(f"{sid} is not one of §7's trial-round sets {CALIBRATION_SETS}")
    for n in (16, 6):
        s = next((x for x in plan["sets"] if int(x["steps"]) == n), None)                         # type: ignore[union-attr]
        if s is None or not {CHALLENGER, COMPARATOR} <= {a["tag"] for a in s["arms"]}:
            raise ValueError(f"the test set {SETS[n]} with arms hx and om is required (B1-B3 are never cut)")


def check_manifest(run_dir: Path, reqs: Sequence[tuple]) -> Dict[str, object]:
    """The run manifest (required) against the request list the runner wrote into it, rebuilt by its own builder
    (`slim.manifest_requests`: the trial round plus every test arm at its floor): item_set_sha256 and n_items must match."""
    from ..pareto.manifest import item_set_hash
    mpath = Path(run_dir) / "manifest.json"
    if not mpath.is_file():
        raise FileNotFoundError("the run folder has no manifest.json (the runner writes it at its first start)")
    man = json.loads(mpath.read_text())
    want = (item_set_hash(reqs), len(reqs))
    if (man.get("item_set_sha256"), int(man.get("n_items", -1))) != want:
        raise ValueError("the run's manifest.json does not match the runner's own request list rebuilt from the run's plan "
                         "(item_set_sha256, n_items): wrong run folder or plan?")
    return {"checked": True, "rebuilt_by": "slim.manifest_requests (the trial round plus every test arm at its floor)",
            "n_items": len(reqs), "item_set_sha256": want[0]}


def _limits_key(doc: Mapping[str, object]) -> List[Tuple[int, str, int]]:
    return sorted((int(a["steps"]), str(a["tag"]), int(a["max_tokens"])) for a in doc["arms"])   # type: ignore[union-attr,index]


def load_run(run_dir: Path, plan_path: Optional[Path] = None, loader=None) -> Dict[str, object]:
    """The run as the slim runner wrote it (Edith S-D1). Its OWN plan copy (`slim_plan.json`; a `plan_path` given must be the same
    plan), the sets checked as the runner checks them (`slim.load_sets`), the call log's `calibration_limits` line (cross-checked with
    `calibration_limits.json`) and `cut` line (and `projection_accepted` when the cut was still over), the manifest rebuilt by the
    runner's builder, and each test set's requests as SENT (`slim.sent_test_requests`: calibrated arms at their limits, cut arms out).
    Returns {"plan", "plan_sha256", "sets": [test set: set_id, man, items, n, arms (sent MainSetups), cut (plan arms), requests],
    "calibration_set_ids", "limits", "cut", "accepted", "manifest_check"}."""
    from ..pareto.calllog import CallLog
    run_dir = Path(run_dir)
    copy = run_dir / "slim_plan.json"
    if not copy.is_file():
        raise FileNotFoundError("the run folder has no slim_plan.json (the runner's copy of the plan it ran)")
    plan = slim.validate_plan(json.loads(copy.read_text()))
    psha = slim.plan_sha256(plan)
    if plan_path is not None and slim.plan_sha256(slim.read_plan(plan_path)) != psha:
        raise ValueError(f"{Path(plan_path).name} is not the plan this run started with (its slim_plan.json)")
    test, cal = slim.load_sets(plan, loader)
    test_ids = {int(s["steps"]): str(man["set_id"]) for s, man, _ in test}
    cal_ids = [str(man["set_id"]) for _, man, _ in cal]
    check_section_3(plan, test_ids, cal_ids)
    if not (run_dir / "calls.jsonl").is_file():
        raise FileNotFoundError("the run folder has no calls.jsonl")
    log = CallLog(run_dir / "calls.jsonl")
    limits, cut, accepted = (slim._one_line(log, kind) for kind in (slim.LIMITS_KIND, slim.CUT_KIND, slim.ACCEPT_KIND))
    for kind, line in ((slim.LIMITS_KIND, limits), (slim.CUT_KIND, cut)):
        if line is None:
            raise ValueError(f"the call log has no {kind} line: the run never reached its test waves")
        if line.get("plan_sha256") != psha:
            raise ValueError(f"the call log's {kind} line was written under another plan")
    lim_file = run_dir / "calibration_limits.json"
    if not lim_file.is_file():
        raise FileNotFoundError("the run folder has no calibration_limits.json")
    if _limits_key(json.loads(lim_file.read_text())) != _limits_key(limits):                   # type: ignore[arg-type]
        raise ValueError("calibration_limits.json and the call log's calibration_limits line disagree")
    lim = {(s_, t_): m_ for s_, t_, m_ in _limits_key(limits)}                                  # type: ignore[arg-type]
    calibrated = {(int(s["steps"]), str(a["tag"])) for s in plan["sets"] for a in s["arms"] if "calibrate" in a}
    if set(lim) != calibrated:
        raise ValueError(f"the calibration_limits line covers {sorted(lim)}, the plan's calibrated arms are {sorted(calibrated)}")
    if cut.get("still_over") and accepted is None:                                              # type: ignore[union-attr]
        raise ValueError("the run stopped at projected_over_cap and the user's ruling was never recorded: no test wave ran")
    cut_keys = {(int(st), str(t)) for st, t in cut.get("cut_arms") or []}                        # type: ignore[union-attr,misc]
    order = {(int(x[0]), str(x[1])) for part in (plan.get("cut") or {}).get("order") or [] for x in part["arms"]}
    if cut_keys - order:
        raise ValueError(f"the cut line names arms outside the plan's cut order: {sorted(cut_keys - order)}")
    if cut_keys & {(n, t) for n in (16, 6) for t in (CHALLENGER, COMPARATOR)}:
        raise ValueError("the cut line names an arm of B1-B3 (hx or om at 6 or 16), which §7 never cuts")
    manifest = check_manifest(run_dir, slim.manifest_requests(plan, test, cal))
    sets: List[Dict[str, object]] = []
    for s, man, items in test:
        n = int(s["steps"])
        sent = [slim._setup(a, a["max_tokens"] if "max_tokens" in a else lim[(n, str(a["tag"]))]) for a in s["arms"]
                if (n, str(a["tag"])) not in cut_keys]
        sets.append({"set_id": str(man["set_id"]), "man": man, "items": {str(it["id"]): it for it in items}, "n": n, "arms": sent,
                     "cut": [a for a in s["arms"] if (n, str(a["tag"])) in cut_keys], "calibration": False,
                     "requests": slim.sent_test_requests(plan, s, man, items, limits, cut)})              # type: ignore[arg-type]
    return {"plan": plan, "plan_sha256": psha, "sets": sets, "calibration_set_ids": cal_ids, "limits": limits, "cut": cut,
            "accepted": accepted, "manifest_check": manifest}


def planned_requests(s: Mapping[str, object]) -> List[tuple]:
    """A test set's requests as the run sent them (`slim.sent_test_requests`, kept by `load_run`)."""
    return list(s["requests"])                                                                   # type: ignore[call-overload]


def plan_as_run(run: Mapping[str, object]) -> Dict[str, object]:
    """The output's account of the plan the run actually followed: the trial round's limits, and the §7 cut (its arms reported as cut
    by cost, never as missing)."""
    cut = run["cut"]
    acc = run["accepted"]
    return {"plan_sha256": run["plan_sha256"],
            "limits": [{k: a.get(k) for k in ("steps", "tag", "floor", "wave0_calls", "wave0_truncated", "wave0_output_tokens_max",
                                              "max_tokens")} for a in run["limits"]["arms"]],                         # type: ignore[index]
            "cut": {"label": CUT_LABEL, "arms": [f"{t}@{st}" for st, t in cut.get("cut_arms") or []],                # type: ignore[union-attr]
                    "parts": [p["part"] for p in cut.get("cut_parts") or []],                                         # type: ignore[union-attr]
                    **{k: cut.get(k) for k in ("cap_usd", "limit_usd", "spent_usd", "projected_without_cut_usd", "projected_usd",  # type: ignore[union-attr]
                                               "still_over")},
                    "projection_accepted": acc is not None, "projection_accepted_note": None if acc is None else acc.get("note")},  # type: ignore[union-attr]
            "manifest_check": run["manifest_check"]}


COST_FIELDS = ("custom_id", "requested_model", "effort", "kind", "refusal_billed_by_rule", "free_by_rule", "usage_raw", "cost_usd")


def _cost_only(rec: Mapping[str, object]) -> Dict[str, object]:
    """A trial-round record cut to its cost fields as it is read (§7: the trial round's answers are never scored or read)."""
    meta = rec.get("meta") or {}
    out = {f: rec.get(f) for f in COST_FIELDS}
    out["meta"] = {"set_id": meta.get("set_id"), "setup": meta.get("setup")}                    # type: ignore[union-attr]
    return out


def _set_of(rec: Mapping[str, object]) -> str:
    meta = rec.get("meta") or {}
    sid = meta.get("set_id")                                                                     # type: ignore[union-attr]
    return str(sid) if sid else str(kscript.parse_custom_id(str(rec["custom_id"]))["set_id"])


def build_rows(plan: Sequence[Mapping[str, object]], logs: Sequence[Path],
               calibration_ids: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """{"rows": scored rows (setup = the tag) with the missing rows, "records": the test sets' final records, "calibration": the
    trial-round records cut to cost fields, "planned": {cid: (set_id, MainSetup, meta)}}. Planned = the requests as SENT (cut arms are
    not planned, so never missing). A final record outside them, or with another max_tokens or request hash, raises.
    `calibration_ids` None: CALIBRATION_SETS, read at call time."""
    from ..pareto.request import params_hash
    calibration_ids = CALIBRATION_SETS if calibration_ids is None else calibration_ids
    planned: Dict[str, Tuple[str, MainSetup, Dict[str, object], Dict[str, object]]] = {}
    items_of: Dict[str, Mapping[str, Mapping[str, object]]] = {}
    for s in plan:
        if s["calibration"]:
            continue
        items_of[str(s["set_id"])] = s["items"]                                                   # type: ignore[assignment]
        arms = {a.name: a for a in s["arms"]}                                                     # type: ignore[attr-defined]
        for cid, params, meta in planned_requests(s):
            planned[cid] = (str(s["set_id"]), arms[str(meta["setup"])], meta, params)
    records: List[Dict[str, object]] = []
    calibration: List[Dict[str, object]] = []
    for rec in main_rows.final_records(logs):
        if _set_of(rec) in calibration_ids:
            calibration.append(_cost_only(rec))
            continue
        records.append(rec)
    rows: List[Dict[str, object]] = []
    finals = set()
    for rec in records:
        cid = str(rec["custom_id"])
        if cid not in planned:
            raise ValueError(f"{cid}: a final record that is not among the requests sent (set {_set_of(rec)}; a cut arm is never sent)")
        sid, su, meta, params = planned[cid]
        if (rec.get("requested_model"), rec.get("effort")) != (su.model, su.effort):
            raise ValueError(f"{cid}: {rec.get('requested_model')} / {rec.get('effort')}, the plan says {su.model} / {su.effort}")
        if rec.get("thinking") is not None and (rec.get("thinking") == "disabled") != su.thinking_off:
            raise ValueError(f"{cid}: thinking {rec.get('thinking')!r}, the plan says thinking_off {su.thinking_off}")
        if rec.get("max_tokens") is not None and int(rec["max_tokens"]) != int(params["max_tokens"]):   # type: ignore[call-overload]
            raise ValueError(f"{cid}: max_tokens {rec.get('max_tokens')}, the run's plan and limits say {params['max_tokens']}")
        if rec.get("params_hash") is not None and rec["params_hash"] != params_hash(params):
            raise ValueError(f"{cid}: the record's request hash is not the rebuilt request's")
        finals.add(cid)
        rows.append(main_rows.score_row(rec, items_of[sid][str(meta["item_id"])], su.name))
    for cid, (sid, su, meta, _p) in planned.items():
        if cid not in finals:
            rows.append(main_rows.missing_row(cid, meta, items_of[sid][str(meta["item_id"])], su.name))
    return {"rows": rows, "records": records, "calibration": calibration,
            "planned": {c: v[:3] for c, v in planned.items()}}


# ---------------------------------------------------------------- §4: per-base scores, the family

def test_rows(rows: Sequence[Mapping[str, object]], set_id: str) -> List[Dict[str, object]]:
    """The test arms' rows of one set under the names the locked five_tests functions read (hx -> haiku-med, om -> opus-med)."""
    name = {CHALLENGER: H, COMPARATOR: O}
    return [dict(r, setup=name[str(r["tag"])]) for r in rows if r["set_id"] == set_id and r["tag"] in name]


def form_scores(trows: Sequence[Mapping[str, object]], n: int, which: str, view: str = "as_deployed",
                k: Optional[int] = None, designed: int = DESIGNED[CHALLENGER]) -> Dict[str, Dict[str, float]]:
    """{shape: {base: points}}: "h" Haiku-max single try, "o" Opus-medium, "v" Haiku-max vote@k (designed 10; 0 in the exclude-missing
    view, so k is held to the tries left)."""
    out: Dict[str, Dict[str, float]] = {}
    for shape in (scoring.pieces_shape(n), scoring.chain_shape(n)):
        if which == "h":
            out[shape] = five_tests.single_scores(trows, H, shape, view)
        elif which == "o":
            out[shape] = five_tests.single_scores(trows, O, shape, view)
        else:
            out[shape] = five_tests.vote_scores(trows, shape, int(k), view, designed=designed)  # type: ignore[arg-type, assignment]
    return out


def pooled(per_form: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
    """Form pooling (§4): each base's score is the mean over its two forms; a base without a score in a form is left out."""
    a, b = list(per_form.values())
    return {base: (a[base] + b[base]) / 2.0 for base in sorted(set(a) & set(b))}


def test_scores(rows: Sequence[Mapping[str, object]], k: int, view: str = "as_deployed",
                designed: int = DESIGNED[CHALLENGER]) -> Dict[str, Optional[Dict[str, object]]]:
    """{test: {"challenger": per-form scores, "comparator": per-form, "c": pooled, "o": pooled} or None when not run}."""
    out: Dict[str, Optional[Dict[str, object]]] = {}
    for t, (n, kind) in TESTS.items():
        trows = test_rows(rows, SETS[n])
        if kind == "vote" and k < 1:
            out[t] = None
            continue
        ch = form_scores(trows, n, "v" if kind == "vote" else "h", view, k, designed)
        co = form_scores(trows, n, "o", view)
        out[t] = {"n": n, "challenger": ch, "comparator": co, "c": pooled(ch), "o": pooled(co)}
    return out


def test_differences(rows: Sequence[Mapping[str, object]], k: int, view: str = "as_deployed", designed: int = DESIGNED[CHALLENGER],
                     all_rows: Optional[Sequence[Mapping[str, object]]] = None) -> Tuple[Dict[str, List[float]], Dict[str, int]]:
    """({test: per-base h_b - o_b or v_b - o_b, [] if not run}, {test: bases left out in this view}); bases are counted over
    `all_rows` (default `rows`)."""
    diffs: Dict[str, List[float]] = {}
    left: Dict[str, int] = {}
    for t, sc in test_scores(rows, k, view, designed).items():
        if sc is None:
            diffs[t], left[t] = [], 0
            continue
        diffs[t] = scoring.paired_differences(sc["c"], sc["o"])                                   # type: ignore[arg-type]
        all_bases = {str(r["base_id"]) for r in (rows if all_rows is None else all_rows) if r["set_id"] == SETS[TESTS[t][0]]}
        left[t] = len(all_bases) - len(diffs[t])
    return diffs, left


def family(diffs: Mapping[str, List[float]], margin: float, B: int, held: Optional[Mapping[str, str]] = None) -> Dict[str, object]:
    """bootstrap.run_family over B1-B3 (seed 20261013). A test that did not run (no differences: NOT_RUN), and a test in `held`
    ({test: its reading}, e.g. NOT_COMPLETED), keeps its Holm place with p = 1 (as five_tests._family): its differences are replaced
    by degenerate ones far below the margin, and it gets no reading."""
    hold: Dict[str, str] = {t: NOT_RUN for t, v in diffs.items() if not v}
    hold.update({t: r for t, r in (held or {}).items() if diffs.get(t)})
    m = max((len(v) for v in diffs.values()), default=1) or 1
    filled = {t: ([-1000.0] * m if t in hold else list(v)) for t, v in diffs.items()}
    res = bootstrap.run_family(filled, margin=margin, B=B, seed=BASE_SEED)
    for t, reading in hold.items():
        res["tests"][t] = {"n": 0, "reading": reading, "declared": False, "d": None, "ci95": None, "p": 1.0}   # type: ignore[index]
    res["not_run"] = [t for t, r in hold.items() if r == NOT_RUN]
    res["not_completed"] = [t for t, r in hold.items() if r == NOT_COMPLETED]
    res["seeds"] = {t: bootstrap.derive_seed(BASE_SEED, t) for t in diffs}
    return res


def completeness(rows: Sequence[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
    """The gate's counts (4a): per test and arm (hx, om) in the test's set, the designed tries (the requests the run sent: every row,
    a missing one included), the final ones and the missing ones; `completed` only if no designed try of either arm is missing."""
    out: Dict[str, Dict[str, object]] = {}
    for t, (n, _) in TESTS.items():
        sid = SETS[n]
        arms: Dict[str, Dict[str, int]] = {}
        for tag in (CHALLENGER, COMPARATOR):
            rs = [r for r in rows if r["set_id"] == sid and r["tag"] == tag]
            miss = sum(1 for r in rs if r.get("kind") == "missing")
            arms[tag] = {"designed": len(rs), "final": len(rs) - miss, "missing": miss}
        done = all(a["designed"] > 0 and a["missing"] == 0 for a in arms.values())
        out[t] = {"set_id": sid, "N": n, "completed": done, "arms": arms, **({} if done else {"reading": NOT_COMPLETED})}
    return out


def not_completed(rows: Sequence[Mapping[str, object]]) -> List[str]:
    """The tests the gate (4a) holds: some designed hx or om try of their set has no final record."""
    return [t for t, c in completeness(rows).items() if not c["completed"]]


def not_completed_line(t: str, counts: Mapping[str, Mapping[str, object]]) -> str:
    """§10's not-completed template for test t, m and n over both arms (from `completeness`)."""
    arms = counts[t]["arms"]                                                                      # type: ignore[index]
    m = sum(int(a["missing"]) for a in arms.values())                                             # type: ignore[union-attr]
    n = sum(int(a["designed"]) for a in arms.values())                                            # type: ignore[union-attr]
    return NOT_COMPLETED_TEMPLATE.format(t=t, m=m, n=n)


def template(views: Mapping[str, Mapping[str, object]], t: str, counts: Optional[Mapping[str, Mapping[str, object]]] = None) -> str:
    """§10's template for test t (see CHOICES["headline_template"]); a test not completed gets §10's not-completed line, filled from
    `counts` (`completeness`)."""
    readings = {v: views[v]["tests"][t]["reading"] for v in scoring.VIEWS}                       # type: ignore[index]
    dep = readings["as_deployed"]
    if dep == NOT_RUN:
        return "not run"
    if NOT_COMPLETED in readings.values():
        if counts is None:
            raise ValueError(f"{t} is not completed: its §10 line needs the completeness counts")
        return not_completed_line(t, counts)
    if all(r == bootstrap.NON_INFERIOR for r in readings.values()):
        return "holds (no worse in all three views)"
    if dep == bootstrap.WORSE:
        return "worse by more than the margin"
    if dep == bootstrap.INCONCLUSIVE:
        return "inconclusive (could not show)"
    return "no worse as deployed only; not a headline (D-68 F3: it fails another view)"


def confirmatory(rows: Sequence[Mapping[str, object]], k: int, B: int, incomplete: Optional[Sequence[str]] = None,
                 counts: Optional[Mapping[str, Mapping[str, object]]] = None) -> Dict[str, object]:
    """The family in all three views at both margins, with the headline rule and the completeness gate (4a): the tests in `incomplete`
    (None: computed from `rows`, `not_completed`) read NOT_COMPLETED with p = 1 in their Holm place, in every view and margin; their §10
    line is filled from `counts` (None: `completeness(rows)`; the D-97 sensitivity passes the whole run's)."""
    counts = completeness(rows) if counts is None else counts
    gate = list(not_completed(rows) if incomplete is None else incomplete)
    held = {t: NOT_COMPLETED for t in gate}
    diffs = {v: test_differences(rows, k, v) for v in scoring.VIEWS}
    out: Dict[str, object] = {}
    for label, margin in MARGINS:
        views = {}
        for v in scoring.VIEWS:
            res = family(diffs[v][0], margin, B, held)
            res["bases_left_out"] = diffs[v][1]
            views[v] = res
        headline = {t: all(views[v]["tests"][t]["reading"] == bootstrap.NON_INFERIOR for v in scoring.VIEWS) for t in TESTS}   # type: ignore[index]
        out[label] = {"margin": margin, "views": views, "headline_no_worse": headline,
                      "template": {t: template(views, t, counts) for t in TESTS}, "completed": {t: t not in gate for t in TESTS}}
    return out


def exclude_missing_view(rows: Sequence[Mapping[str, object]], k: int, B: int, draws: int = DRAWS) -> object:
    """4b: item 16's exclude-missing view for B1-B3 (D-48 row 23, as Study 1's report_arms.exclude_missing_view): as_deployed with only
    the missing tries left out (the vote with designed=0, so k is held to the tries left), both margins, same k, B, seeds and Holm;
    a sensitivity beside the family. NO_MISSING when no try of hx or om at N = 16 or 6 is missing. The gate (4a) holds its Holm family
    as in the main view (a test not completed at p = 1), so a completed test here equals the main view; a test not completed gets only
    d, its 95% interval (cluster bootstrap over the bases used, `draws`, seed 20261013, "1b:<test>:<N>:exclude-missing:d") and the
    bases used, on its tries with a final record, labelled NOT_COMPLETED_DESCRIPTIVE: no reading, no declared (spec §4; Edith L-1)."""
    counts = completeness(rows)
    missing = {t: {tag: a["missing"] for tag, a in c["arms"].items()} for t, c in counts.items()}             # type: ignore[union-attr]
    if not any(v for m in missing.values() for v in m.values()):
        return NO_MISSING
    gate = [t for t, c in counts.items() if not c["completed"]]
    kept = [r for r in rows if r.get("kind") != "missing"]
    diffs, left = test_differences(kept, k, "as_deployed", designed=0, all_rows=rows)
    scores = test_scores(kept, k, "as_deployed", designed=0)
    out: Dict[str, object] = {"label": EXCLUDE_MISSING_LABEL, "missing_left_out": missing, "not_completed": gate,
                              "bases_per_test": {t: len(v) for t, v in diffs.items()}, "bases_left_out": left}
    in_family = {t: (v if v or t not in gate or scores[t] is None else [0.0]) for t, v in diffs.items()}   # a held test with no base
    for label, margin in MARGINS:                                                                 # left still holds its place (not "not run")
        res = family(in_family, margin, B, {t: NOT_COMPLETED for t in gate})
        for t in gate:
            sc = scores[t]
            if sc is None:                                                                        # k < 1: B2 stays "not run"
                continue
            d = {b: float(sc["c"][b]) - float(sc["o"][b]) for b in sorted(set(sc["c"]) & set(sc["o"]))}   # type: ignore[index]
            name = f"1b:{t}:{TESTS[t][0]}:exclude-missing:d"
            res["tests"][t] = {"label": NOT_COMPLETED_DESCRIPTIVE, "d": _mean(list(d.values())), "n_base": len(d),   # type: ignore[index]
                               "bases_used": sorted(d), "ci95": _boot(sorted(d), d, name, draws), "bootstrap_name": name}
        out[label] = {"margin": margin, "as_deployed": res}
    return out


def without_exposed(rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    """The rows minus D-97's exposed test bases (whole bases: every arm, form and try)."""
    drop = {f"{sid}-{b:03d}" for sid, bases in EXPOSED_BASES.items() for b in bases}
    return [dict(r) for r in rows if str(r["base_id"]) not in drop]


def sensitivity_exposed(rows: Sequence[Mapping[str, object]], k: int, B: int) -> Dict[str, object]:
    """D-97: the whole family (both margins, three views, Holm over B1-B3) and the error-rate ratios, re-run without the exposed bases.
    The same k (from costs, k.json), B and seeds, and the run's completeness gate (4a, from all the rows). Appendix only; it never
    replaces the primary readings. §6 is not re-run."""
    kept = without_exposed(rows)
    gate = not_completed(rows)
    bases = {t: len({str(r["base_id"]) for r in test_rows(kept, SETS[n])}) for t, (n, _) in TESTS.items()}
    return {"label": SENSITIVITY_LABEL, "excluded": {sid: [f"{sid}-{b:03d}" for b in bs] for sid, bs in EXPOSED_BASES.items()},
            "bases_per_test": bases, "not_completed": gate, "confirmatory": confirmatory(kept, k, B, gate, completeness(rows)),
            "error_ratios": error_ratios(kept, k, B, gate)}


@contextlib.contextmanager
def _error_ratio_seed(seed: int) -> Iterator[None]:
    old = main_analysis.ERROR_RATIO_SEED
    main_analysis.ERROR_RATIO_SEED = seed
    try:
        yield
    finally:
        main_analysis.ERROR_RATIO_SEED = old


def error_ratios(rows: Sequence[Mapping[str, object]], k: int, B: int, incomplete: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """Item 1's error-rate ratio beside each test (as deployed), seed derive_seed(20261013, f"{test}:error_ratio"); Opus 0 errors:
    the Clopper-Pearson bound over the test's designed Opus tries. A test the gate holds (4a; `incomplete`, None: from `rows`) gets
    none: NOT_COMPLETED."""
    gate = set(not_completed(rows) if incomplete is None else incomplete)
    out: Dict[str, object] = {}
    for t, sc in test_scores(rows, k).items():
        if sc is None:
            out[t] = {"reading": NOT_RUN}
            continue
        if t in gate:
            out[t] = {"reading": NOT_COMPLETED}
            continue
        c, o = sc["c"], sc["o"]
        bases = sorted(set(c) & set(o))                                                           # type: ignore[arg-type]
        ech = {b: (100.0 - float(c[b])) / 100.0 for b in bases}                                   # type: ignore[index]
        ecm = {b: (100.0 - float(o[b])) / 100.0 for b in bases}                                   # type: ignore[index]
        with _error_ratio_seed(BASE_SEED):
            row = main_analysis.ratio_from_errors(ech, ecm, t, B)
        keep = set(bases)
        designed_o = sum(1 for r in rows if r["set_id"] == SETS[TESTS[t][0]] and r["tag"] == COMPARATOR and str(r["base_id"]) in keep)
        row.update(seed=bootstrap.derive_seed(BASE_SEED, f"{t}:error_ratio"), B=B, comparator="om (Opus 5.5, medium)",
                   comparator_designed_tries=designed_o)
        if not row["defined"] and bases:
            row["comparator_error_rate_upper95_over_bases"] = row.get("comparator_error_rate_upper95")
            row["comparator_error_rate_upper95"] = 1.0 - 0.025 ** (1.0 / designed_o) if designed_o else None
            row["comparator_note"] = f"comparator: 0 errors in {designed_o} designed tries"
        out[t] = row
    return out


def per_form(rows: Sequence[Mapping[str, object]], k: int, draws: int) -> Dict[str, object]:
    """§4 "Per form": h (or v), o and d for each form, with a cluster bootstrap over base puzzles (seed 20261013). Descriptive. A test
    the gate holds (4a) is computed on its tries with a final record only (the exclude-missing rows; the vote with designed=0) and
    labelled "not completed; descriptive only" (spec §4; Edith L-2)."""
    out: Dict[str, object] = {}
    gate = set(not_completed(rows))
    final_only = test_scores([r for r in rows if r.get("kind") != "missing"], k, "as_deployed", designed=0)
    for t, sc in test_scores(rows, k).items():
        if t in gate and sc is not None:
            sc = final_only[t]
        if sc is None:
            out[t] = {"reading": NOT_RUN}
            continue
        n = int(sc["n"])                                                                          # type: ignore[call-overload]
        stat_name = "v" if TESTS[t][1] == "vote" else "h"
        d_t: Dict[str, object] = {}
        for shape in sc["challenger"]:                                                            # type: ignore[union-attr]
            c, o = sc["challenger"][shape], sc["comparator"][shape]                               # type: ignore[index]
            bases = sorted(set(c) & set(o))
            vals = {stat_name: {b: c[b] for b in bases}, "o": {b: o[b] for b in bases}, "d": {b: c[b] - o[b] for b in bases}}
            d_t[shape] = {s: {"mean": _mean(list(v.values())), "n_base": len(v),
                              "ci95": _boot(bases, v, f"1b:{t}:{n}:{shape}:{s}", draws), "bootstrap_name": f"1b:{t}:{n}:{shape}:{s}"}
                          for s, v in vals.items()}
        if t in gate:
            d_t["label"] = NOT_COMPLETED_DESCRIPTIVE
            d_t["tries"] = "the tries with a final record only (missing tries left out; the vote with k held to the tries left)"
        out[t] = d_t
    return out


def _mean(xs: Sequence[float]) -> Optional[float]:
    return math.fsum(xs) / len(xs) if xs else None


def _boot(bases: Sequence[str], values: Mapping[str, float], name: str, draws: int) -> List[Optional[float]]:
    """The cluster bootstrap (curve.cluster_bootstrap, percentile 95%) of the mean over drawn base puzzles, seed 20261013."""
    if not bases:
        return [None, None]
    return list(cluster_bootstrap([sorted(bases)], lambda s: math.fsum(values[b] for b in s) / len(s), name, draws=draws,
                                  seed=BASE_SEED))


# ---------------------------------------------------------------- costs (items 9a-9c, report_costs' copies)

def cost_ctx(plan: Sequence[Mapping[str, object]], built: Mapping[str, object], kdoc: Mapping[str, object], run_dir: Optional[Path],
             draws: Optional[int]) -> Dict[str, object]:
    """The context report_costs / report_arms read: every 1b row under its tag ("other"), the non-calibration final records, and item
    9b's cells built from the plan (designed tries per arm; the real calls on each base), placed in report_costs' cache so its locked
    base_costs / cost_block / cpc_block use the 1b design (report_costs.cells would read Study 1's runner)."""
    rows = list(built["rows"])                                                                    # type: ignore[call-overload]
    finals = {str(r["custom_id"]) for r in built["records"]}                                     # type: ignore[union-attr]
    cells: Dict[Tuple[str, str], Dict[str, object]] = {}
    arm_of = {(str(s["set_id"]), a.name): a for s in plan if not s["calibration"] for a in s["arms"]}   # type: ignore[attr-defined]
    for r in rows:
        su = arm_of[(str(r["set_id"]), str(r["tag"]))]
        cell = cells.setdefault((str(r["tag"]), str(r["shape"])), {"tag": su.name, "how": "single" if su.n == 1 else "per_sample",
                                                                    "designed": su.n, "bases": {}})
        lst = cell["bases"].setdefault(str(r["base_id"]), [])                                    # type: ignore[union-attr]
        if str(r["custom_id"]) in finals:
            lst.append(str(r["custom_id"]))
    items = {i: it for s in plan if not s["calibration"] for i, it in s["items"].items()}         # type: ignore[union-attr]
    return {"rows": [], "other": rows, "missing": [r for r in rows if r.get("kind") == "missing"], "records": list(built["records"]),  # type: ignore[call-overload]
            "all_records": [], "items": items, "set_id": None, "n": None, "k": kdoc, "run_dir": run_dir, "B": None, "draws": draws,
            "_report_costs_cache": {"cells": cells}}


def _pooled_costs(ctx: dict, tag: str, n: int, field: str = "list") -> Dict[str, Optional[Fraction]]:
    a, _ = report_costs.base_costs(ctx, tag, scoring.pieces_shape(n), field)
    b, _ = report_costs.base_costs(ctx, tag, scoring.chain_shape(n), field)
    return {x: (None if a[x] is None or b[x] is None else (a[x] + b[x]) / 2) for x in sorted(set(a) & set(b))}   # type: ignore[operator]


def _mean_cost(costs: Mapping[str, Optional[Fraction]], scale: int = 1) -> Optional[float]:
    vals = list(costs.values())
    if not vals or any(v is None for v in vals):
        return None
    return float(sum(vals, Fraction(0)) * scale / len(vals))                                      # type: ignore[arg-type]


def cost_per_answer(ctx: dict, tag: str, n: int, scale: int = 1) -> Dict[str, object]:
    """Item 9b's mean list cost per answer (per form, cost_block; pooled, the per-base mean of the forms), the logged Batch mean beside."""
    out: Dict[str, object] = {}
    for shape in (scoring.pieces_shape(n), scoring.chain_shape(n)):
        cb = report_costs.cost_block(ctx, tag, shape, scale)
        batch, _ = report_costs.base_costs(ctx, tag, shape, "batch")
        out[shape] = {"list_usd": cb["mean"], "list_ci95": cb["mean_ci95"], "batch_usd": _mean_cost(batch, scale),
                      "calls_without_record": cb["calls_without_record"], "bootstrap_name": f"cost_mean:{tag}:{shape}"}
    out["pooled"] = {"list_usd": _mean_cost(_pooled_costs(ctx, tag, n), scale), "batch_usd": _mean_cost(_pooled_costs(ctx, tag, n, "batch"), scale)}
    out["unit"] = "USD per answer, list price (item 9b)" + (f"; the vote at k = {scale} costs {scale} answers" if scale > 1 else "")
    return out


def b2_wording(kdoc: Mapping[str, object]) -> str:
    """B2's cost wording (§4, as D-33 item 4): "for less than Opus's price" exactly when the cost ratio is above 10 (k.json's `capped`,
    which study1b_k sets as ratio > 10); "about" otherwise, a ratio of exactly 10 included."""
    k = int(kdoc["k"])                                                                             # type: ignore[call-overload]
    if kdoc["capped"]:
        return f"the vote of k = {k} Haiku-max tries, {CAPPED_WORDING} (cost ratio {kdoc['ratio']} > {K_CAP})"
    return f"the vote of k = {k} Haiku-max tries, about Opus-medium's price"


def costs_beside_tests(ctx: dict, kdoc: Mapping[str, object]) -> Dict[str, object]:
    """§4: the cost per answer of each arm beside each test, and "about 1/k of the cost" (k measured)."""
    k = int(kdoc["k"])                                                                             # type: ignore[call-overload]
    out: Dict[str, object] = {}
    for t, (n, kind) in TESTS.items():
        if kind == "vote" and k < 1:
            out[t] = {"reading": NOT_RUN}
            continue
        scale = k if kind == "vote" else 1
        ch = cost_per_answer(ctx, CHALLENGER, n, scale)
        co = cost_per_answer(ctx, COMPARATOR, n)
        a, b = ch["pooled"]["list_usd"], co["pooled"]["list_usd"]                                # type: ignore[index]
        d: Dict[str, object] = {"challenger": ch, "comparator": co,
                                "ratio_challenger_over_comparator": (a / b) if a is not None and b else None}
        if kind == "single":
            km = k if n == 16 else (math.floor(Fraction(b) / Fraction(a)) if a and b else None)     # B3: measured at N = 6
            d["k_measured"] = km
            d["k_source"] = "k.json (B2's k)" if n == 16 else "floor(om / hx list cost per answer at N = 6), descriptive"
            d["wording"] = f"about 1/{km} of the cost per answer (k measured)" if km else None
        else:
            d["wording"] = b2_wording(kdoc)
        out[t] = d
    return out


# ---------------------------------------------------------------- §6 descriptive

def _effort_label(su: MainSetup) -> str:
    return "off" if su.thinking_off else su.effort


def _try_counts(rs: Sequence[Mapping[str, object]]) -> Dict[str, int]:
    """designed (the tries the run sent: every row, a missing one included), final and missing."""
    miss = sum(1 for r in rs if r.get("kind") == "missing")
    return {"designed": len(rs), "final": len(rs) - miss, "missing": miss}


def held_lengths(rows: Sequence[Mapping[str, object]]) -> List[int]:
    """The lengths whose test the gate (4a) holds: 16 if B1/B2 is not completed, 6 if B3 is (spec §6, C1)."""
    return sorted({TESTS[t][0] for t in not_completed(rows)})


def _accuracy(ctx: dict, ar: Sequence[Mapping[str, object]], su: MainSetup, n: int, draws: int,
              final_only: bool) -> Dict[str, object]:
    """{shape: entry, "pooled": entry}: accuracy (official) with §6's interval, the cost per answer (9b) and the CPC (9c), each entry
    with its try counts. As deployed (final_only False): each puzzle the share right of its designed tries, a missing try wrong. Final
    only: the missing tries left out (a base with none left drops). A form with no final try reads NOT_SENT (C1), with no accuracy."""
    per: Dict[str, Dict[str, float]] = {}
    right_tries: Dict[str, int] = {}
    tries: Dict[str, int] = {}
    out: Dict[str, object] = {}
    for shape in (scoring.pieces_shape(n), scoring.chain_shape(n)):
        rs_all = [dict(r) for r in ar if r["shape"] == shape]
        cnt = _try_counts(rs_all)
        rs = [r for r in rs_all if r.get("kind") != "missing"] if final_only else rs_all
        per[shape] = scoring.arm_scores(rs, "as_deployed", "official")
        right_tries[shape] = sum(1 for r in rs if scoring.row_correct(r, "official"))
        tries[shape] = len(rs)
        if cnt["final"] == 0:
            out[shape] = {"status": NOT_SENT, **cnt}
            continue
        name = f"1b:{su.name}:{n}:{shape}"
        bases = sorted(per[shape])
        d: Dict[str, object] = {"mean": _mean(list(per[shape].values())), "n_base": len(bases), "unit": "points", **cnt}
        if su.n > 1:
            d.update(ci95=_boot(bases, per[shape], name, draws), interval="cluster bootstrap", bootstrap_name=name)
        else:
            x = sum(1 for b in bases if per[shape][b] == 100.0)
            lo, hi = report_arms.clopper_pearson(x, len(bases)) if bases else (None, None)
            d.update(x=x, ci95=[None if lo is None else 100.0 * lo, None if hi is None else 100.0 * hi], interval="clopper-pearson")
        d["cost_per_answer"] = report_costs.cost_block(ctx, su.name, shape)["mean"]
        if final_only:                     # cpc_block's arithmetic and fields, on the final-tries scores
            costs = {b: v for b, v in report_costs.base_costs(ctx, su.name, shape)[0].items() if v is not None}
            batch, _ = report_costs.base_costs(ctx, su.name, shape, "batch")
            d["cpc"] = (dict(report_costs._cpc(costs, per[shape], f"cpc:{su.name}:{shape}", report_costs.cluster_draws(ctx)), k=1,
                             batch_cpc=report_costs._batch_cpc(batch, per[shape], 1), how="single try") if costs else None)
        else:
            d["cpc"] = report_costs.cpc_block(ctx, su.name, shape)
        out[shape] = d
    pool = pooled(per)
    name = f"1b:{su.name}:{n}:pooled"
    p: Dict[str, object] = {"mean": _mean(list(pool.values())), "n_base": len(pool), "unit": "points", **_try_counts(ar)}
    if su.n > 1:
        p.update(ci95=_boot(sorted(pool), pool, name, draws), interval="cluster bootstrap", bootstrap_name=name)
    else:
        x, m = sum(right_tries.values()), sum(tries.values())
        lo, hi = report_arms.clopper_pearson(x, m) if m else (None, None)
        p.update(x=x, tries=m, ci95=[None if lo is None else 100.0 * lo, None if hi is None else 100.0 * hi], interval="clopper-pearson")
    costs = _pooled_costs(ctx, su.name, n)
    p["cost_per_answer"] = _mean_cost(costs)
    known = {b: v for b, v in costs.items() if v is not None}
    p["cpc"] = report_costs._cpc(known, pool, f"cpc:{su.name}:{n}:pooled", report_costs.cluster_draws(ctx)) if known else None
    out["pooled"] = p
    return out


def arm_point(ctx: dict, rows: Sequence[Mapping[str, object]], su: MainSetup, n: int, draws: int,
              held: bool = False) -> Dict[str, object]:
    """One arm at one set: accuracy per form and pooled (official) with §6's interval, the list cost per answer (9b) and the CPC (9c)
    beside it, every entry with its designed / final / missing try counts (spec §6, C1). `held`: hx or om at a length whose test the
    gate holds: final tries only, labelled "not completed; descriptive only". An arm with no final try: NOT_SENT, counts only, never
    0%. Otherwise as deployed (each puzzle the share right of its designed tries, a missing try wrong) and, if a try is missing, the
    exclude-missing view beside it ("sensitivity: missing tries excluded")."""
    sid = SETS[n]
    ar = [r for r in rows if r["set_id"] == sid and r["tag"] == su.name]
    shapes = (scoring.pieces_shape(n), scoring.chain_shape(n))
    for shape in shapes:
        counts = Counter(str(r["base_id"]) for r in ar if r["shape"] == shape)
        if any(c != su.n for c in counts.values()):
            raise ValueError(f"{su.name} {shape}: a base with other than {su.n} designed tries")
    out: Dict[str, object] = {"tag": su.name, "model": su.model, "effort": _effort_label(su), "tries_per_item": su.n, "N": n,
                              **_try_counts(ar)}
    if out["final"] == 0:
        out["status"] = NOT_SENT
        for shape in shapes:
            out[shape] = {"status": NOT_SENT, **_try_counts([r for r in ar if r["shape"] == shape])}
        out["pooled"] = {"status": NOT_SENT, **_try_counts(ar)}
        return out
    if held:
        out.update(_accuracy(ctx, ar, su, n, draws, final_only=True))
        out["label"] = NOT_COMPLETED_DESCRIPTIVE
        out["tries"] = "the tries with a final record only (missing tries left out)"
        return out
    out.update(_accuracy(ctx, ar, su, n, draws, final_only=False))
    if out["missing"]:
        out["missing_excluded"] = {"label": MISSING_EXCLUDED_LABEL, **_accuracy(ctx, ar, su, n, draws, final_only=True)}
    return out


def cut_point(a: Mapping[str, object], n: int) -> Dict[str, object]:
    """An arm the §7 cut order removed (never sent): reported as cut by cost, with no accuracy, interval or missing count."""
    return {"tag": a["tag"], "model": a["model"], "effort": "off" if a.get("thinking_off") else a["effort"], "tries_per_item": a["n"],
            "N": n, "status": CUT_LABEL}


def descriptive_arms(ctx: dict, rows: Sequence[Mapping[str, object]], plan: Sequence[Mapping[str, object]],
                     draws: int) -> Dict[str, Dict[str, object]]:
    """{"<tag>@<N>": arm_point} for every arm of every 1b set the run sent (hx and om at a held length on their final tries, C1); the
    arms the §7 cut removed as cut_point."""
    out: Dict[str, Dict[str, object]] = {}
    held = held_lengths(rows)
    for s in plan:
        if s["calibration"]:
            continue
        for su in s["arms"]:                                                                      # type: ignore[attr-defined]
            h = int(s["n"]) in held and su.name in (CHALLENGER, COMPARATOR)                       # type: ignore[call-overload]
            out[f"{su.name}@{s['n']}"] = arm_point(ctx, rows, su, int(s["n"]), draws, h)         # type: ignore[call-overload]
        for a in s.get("cut") or []:                                                              # type: ignore[attr-defined]
            out[f"{a['tag']}@{s['n']}"] = cut_point(a, int(s["n"]))                              # type: ignore[call-overload]
    return out


def _family_name(model: str) -> str:
    return {HAIKU: "haiku", SONNET: "sonnet", OPUS: "opus"}.get(model, model)


def _figure_panels(a: Mapping[str, object], n: int, fields: Sequence[str]) -> Dict[str, object]:
    """An arm block's per-form and pooled panels for a figure: `fields` plus the try counts (and a form's NOT_SENT status); the arm's
    counts, its label and its 'sensitivity: missing tries excluded' panels when it has them (spec §6, C1)."""
    keep = tuple(fields) + COUNT_KEYS + ("status",)
    def panels(src: Mapping[str, object]) -> Dict[str, object]:
        return {panel: {f: src[panel][f] for f in keep if f in src[panel]}                         # type: ignore[index,operator]
                for panel in (scoring.pieces_shape(n), scoring.chain_shape(n), "pooled")}
    out: Dict[str, object] = {k: a[k] for k in COUNT_KEYS}
    if a.get("status") == NOT_SENT:
        out["status"] = NOT_SENT
        return out
    out.update(panels(a))
    if "label" in a:
        out["label"] = a["label"]
    if "missing_excluded" in a:
        out["missing_excluded"] = {"label": a["missing_excluded"]["label"], **panels(a["missing_excluded"])}   # type: ignore[index,arg-type]
    return out


def effort_figure(arms: Mapping[str, Mapping[str, object]], study1: Mapping[str, object]) -> Dict[str, object]:
    """§6: accuracy against effort per model on the same puzzles, N = 6 (Haiku off-max, Sonnet low-max, Opus low-max) and N = 16 (Haiku
    off-max plus Opus-medium), each point the arm's per-form and pooled accuracy with its interval and cost per answer, its try counts
    and its C1 label or status (`_figure_panels`); Study 1's N = 6 points separately, labelled."""
    out: Dict[str, object] = {}
    for n in (6, 16):
        by_model: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for key, a in arms.items():
            if int(a["N"]) != n:                                                                  # type: ignore[call-overload]
                continue
            if a.get("status") == CUT_LABEL:
                by_model[_family_name(str(a["model"]))].append({"arm": key, "tag": a["tag"], "effort": a["effort"], "status": CUT_LABEL})
                continue
            by_model[_family_name(str(a["model"]))].append(
                {"arm": key, "tag": a["tag"], "effort": a["effort"],
                 **_figure_panels(a, n, ("mean", "ci95", "interval", "cost_per_answer"))})
        for v in by_model.values():
            v.sort(key=lambda p: EFFORT_ORDER.index(str(p["effort"])))
        out[f"N={n}"] = dict(sorted(by_model.items()))
    out["study1_points"] = study1
    return out


STUDY1_ARMS = {"haiku-thinking-off": ("haiku", "off"), "haiku-low": ("haiku", "low"), "haiku-med": ("haiku", "medium"),
               "haiku-max": ("haiku", "max"), "sonnet-low": ("sonnet", "low"), "sonnet-med": ("sonnet", "medium"),
               "opus-low": ("opus", "low"), "opus-med": ("opus", "medium")}


def study1_points(path: Path) -> Dict[str, object]:
    """Study 1's N = 6 points (its committed analysis.json, item 24's table: accuracy, its interval, the 9b cost per puzzle)."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"Study 1's analysis.json ({Path(path).name}) is missing: §6 draws its N = 6 points (Edith S-D3)")
    table = json.loads(Path(path).read_text())["reporting"]["group_b"]["item_24"]["table"]
    pts = []
    for key, d in sorted(table.items()):
        arm, shape = key.rsplit(" ", 1)
        if arm not in STUDY1_ARMS:
            continue
        band = (d.get("accuracy_interval") or {}).get("ci95") or (d.get("accuracy_cp95") or {}).get("cp95")
        model, effort = STUDY1_ARMS[arm]
        pts.append({"arm": arm, "model": model, "effort": effort, "shape": shape, "mean": d.get("accuracy_mean"), "ci95": band,
                    "cost_per_answer": (d.get("cost_per_puzzle") or {}).get("mean")})
    return {"label": STUDY1_LABEL, "source": _rel(path), "source_sha256": _sha(path), "points": pts}


def ladder_curve(path: Path) -> Dict[str, object]:
    """The ladder's D-87 curve (Haiku-medium x10, Opus-medium x1; whole answer per shape and pooled, shares 0-1 as in the file)."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"the ladder curve file ({Path(path).name}) is missing: §6 draws the length curve behind 1b's (Edith S-D3)")
    doc = json.loads(Path(path).read_text())
    out: Dict[str, object] = {"label": LADDER_LABEL, "source": _rel(path), "source_sha256": _sha(path), "unit": "share right (0-1)"}
    for tag, name in (("hm", "haiku-medium"), ("om", "opus-medium")):
        out[name] = {n: v.get("whole_answer") for n, v in sorted(doc["models"][tag]["by_n"].items(), key=lambda kv: int(kv[0]))}
    return out


def length_curve(arms: Mapping[str, Mapping[str, object]], ladder: Mapping[str, object]) -> Dict[str, object]:
    """§6: Haiku-max and Opus-medium at N = 6, 12, 16 (1b) and Haiku-medium at 6 and 16 (1b), per form and pooled, with the ladder behind;
    each point with its try counts and its C1 label or status (`_figure_panels`)."""
    out: Dict[str, object] = {}
    for tag, name, ns in (("hx", "haiku-max", (6, 12, 16)), ("om", "opus-medium", (6, 12, 16)), ("hm", "haiku-medium", (6, 16))):
        line = {}
        for n in ns:
            a = arms.get(f"{tag}@{n}")
            if a is not None and a.get("status") == CUT_LABEL:
                line[str(n)] = {"status": CUT_LABEL}
                continue
            line[str(n)] = None if a is None else _figure_panels(a, n, ("mean", "ci95", "interval"))
        out[name] = line
    out["ladder"] = ladder
    return out


def vote_curve(ctx: dict, rows: Sequence[Mapping[str, object]], k: int, draws: int) -> Dict[str, object]:
    """§6: Haiku-max's equal-money vote curve at N = 16, k = 1..10 (item 8's vote), per form and pooled, with the cost per answer (k x
    hx's, 9b), Opus-medium's cost per answer and the CPC at each k (9c's arithmetic); hx's try counts per form and pooled (C1). If the
    gate holds N = 16 (B1/B2 not completed): hx's final tries only, k held to the tries left in each base (a base with none left drops),
    labelled "not completed; descriptive only"; if hx has no final try at 16: NOT_SENT, counts only, no points (spec §6, C1)."""
    n = 16
    shapes = (scoring.pieces_shape(n), scoring.chain_shape(n))
    hx_rows = [r for r in rows if r["set_id"] == SETS[n] and r["tag"] == CHALLENGER]
    counts = {**{shape: _try_counts([r for r in hx_rows if r["shape"] == shape]) for shape in shapes}, "pooled": _try_counts(hx_rows)}
    doc: Dict[str, object] = {"N": n, "arm": "hx", "unit": "points", "bootstrap_names": "1b:hx-vote:16:<form|pooled> (one name for every k)",
                              "k_from_k_json": k, "tries": counts}
    if counts["pooled"]["final"] == 0:
        return dict(doc, status=NOT_SENT, points=[])
    held = n in held_lengths(rows)
    trows = test_rows([r for r in rows if r.get("kind") != "missing"] if held else rows, SETS[n])
    curves: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
    for shape in shapes:
        answers = five_tests._haiku_answers(trows, shape, "as_deployed", 0 if held else DESIGNED[CHALLENGER], "official")
        curves[shape] = {b: votes.vote_curve(d["answers"], d["correct"], kmax=DESIGNED[CHALLENGER], detail=True, tie="random")  # type: ignore[misc]
                         for b, d in sorted(answers.items()) if d["answers"]}
    om_cost = cost_per_answer(ctx, COMPARATOR, n)
    hx_costs = {shape: report_costs.base_costs(ctx, CHALLENGER, shape)[0] for shape in shapes}
    hx_pooled = _pooled_costs(ctx, CHALLENGER, n)
    pts = []
    for kk in range(1, DESIGNED[CHALLENGER] + 1):
        vals = {shape: {b: 100.0 * float(c[min(kk, len(c)) - 1]["acc"]) for b, c in curves[shape].items()} for shape in shapes}  # type: ignore[arg-type]
        pool = pooled(vals)
        p: Dict[str, object] = {"k": kk, "equal_money_k": kk == k}
        for label, v, costs in ((shapes[0], vals[shapes[0]], hx_costs[shapes[0]]), (shapes[1], vals[shapes[1]], hx_costs[shapes[1]]),
                                ("pooled", pool, hx_pooled)):
            if counts[label]["final"] == 0:
                p[label] = {"status": NOT_SENT, **counts[label]}
                continue
            known = {b: c for b, c in costs.items() if c is not None}
            name = f"cpc:{CHALLENGER}:{label}" if label != "pooled" else f"cpc:{CHALLENGER}:{n}:pooled"
            p[label] = {"mean": _mean(list(v.values())), "n_base": len(v), "ci95": _boot(sorted(v), v, f"1b:hx-vote:{n}:{label}", draws),
                        "cost_per_answer": _mean_cost(costs, kk),
                        "cpc": report_costs._cpc(known, v, name, report_costs.cluster_draws(ctx), kk) if known else None,
                        **counts[label]}
        pts.append(p)
    doc.update({"opus_medium_cost_per_answer": om_cost, "points": pts,
                "rule": "item 8: votes.vote_curve over the 10 designed tries (a missing or unreadable try votes for nothing), official, "
                        "as deployed, ties at 1/m"})
    if held:
        doc["label"] = NOT_COMPLETED_DESCRIPTIVE
        doc["rule"] = ("item 8's vote on hx's final tries only (B1/B2 not completed: missing tries left out, k held to the tries left "
                       "in each base, a base with none left out; an unreadable try votes for nothing), official, ties at 1/m")
    return doc


def compliance(ctx: dict, plan: Sequence[Mapping[str, object]], rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    """§6: format compliance, refusals, truncations and missing items for every arm (items 16 and 17's rules)."""
    rates: Dict[str, object] = {}
    for s in plan:
        if s["calibration"]:
            continue
        ctx_n = dict(ctx, n=int(s["n"]), items=s["items"])                                        # type: ignore[call-overload]
        rates[str(s["set_id"])] = report_arms.item_16(ctx_n)["rates"]
    cut = [f"{a['tag']}@{s['n']}" for s in plan if not s["calibration"] for a in s.get("cut") or []]   # type: ignore[attr-defined]
    return {"item_16_rates": rates, "item_17_flags": report_arms.item_17(ctx)["flags"],
            "cut_by_section_7": {"label": CUT_LABEL, "arms": cut, "note": "never sent: not counted as missing"},
            "format_report": five_tests.format_report(list(rows)),
            "label": "item 16: count / designed calls with Wilson 95% and list cost; item 17: non-compliance above 5% of answered tries"}


def calibration_report(calib: Sequence[Mapping[str, object]], run_dir: Optional[Path]) -> Dict[str, object]:
    """§6 / §7: the trial round's tokens and costs only (by set and tag); its answers are never scored."""
    free, _ = report_costs._ledger_free_ids(run_dir)
    by: Dict[str, Dict[str, object]] = {}
    for rec in calib:
        meta = rec.get("meta") or {}
        key = f"{meta.get('set_id')} {meta.get('setup')}"                                          # type: ignore[union-attr]
        d = by.setdefault(key, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "list_usd": Decimal(0), "batch_usd_logged": Decimal(0),
                                "batch_cost_missing": 0})
        u = usage_from_raw(dict(rec.get("usage_raw") or {}))                                      # type: ignore[call-overload]
        d["calls"] += 1                                                                            # type: ignore[operator]
        d["input_tokens"] += u.prompt_tokens                                                       # type: ignore[operator]
        d["output_tokens"] += u.output_tokens                                                      # type: ignore[operator]
        d["list_usd"] += report_costs.list_cost(rec, free)                                         # type: ignore[operator]
        if rec.get("cost_usd") in (None, ""):
            d["batch_cost_missing"] += 1                                                           # type: ignore[operator]
        else:
            d["batch_usd_logged"] += Decimal(str(rec["cost_usd"]))                                 # type: ignore[operator]
    return {"label": "the trial round (§7): tokens and costs only; answers never scored", "set_ids": list(CALIBRATION_SETS),
            "calls": len(calib), "by_set_and_tag": {k: {kk: (str(v) if isinstance(v, Decimal) else v) for kk, v in d.items()}
                                                   for k, d in sorted(by.items())}}


# ---------------------------------------------------------------- k

def check_k(k_path: Path, run_dir: Path) -> Dict[str, object]:
    """k.json, checked against this run's compact_table.csv and recomputed (study1b_k); a difference raises."""
    kdoc = study1b_k.load_k(k_path)
    table = Path(run_dir) / "compact_table.csv"
    if kdoc.get("compact_table_sha256") != _sha(table):
        raise ValueError(f"{Path(k_path).name} was computed from another compact_table.csv than this run folder's")
    again = json.loads(json.dumps(study1b_k.k_from_table(table, run_dir)))
    if again != kdoc:
        raise ValueError(f"{Path(k_path).name} differs from k recomputed now from the run's compact_table.csv (study1b_k)")
    k = int(kdoc["k"])                                                                             # type: ignore[call-overload]
    if not 0 <= k <= K_CAP:
        raise ValueError(f"{Path(k_path).name}: k = {k} is outside 0..{K_CAP}")
    if bool(kdoc["capped"]) != (Fraction(str(kdoc["ratio"])) > K_CAP):
        raise ValueError(f"{Path(k_path).name}: capped is not 'ratio > {K_CAP}' (§4)")
    return kdoc


def k_from_call_log(ctx: dict) -> Dict[str, object]:
    """Beside k.json: the same rule on the call log's final records (item 9a's list cost, report_costs.calls), N = 16, hx and om."""
    cs = report_costs.calls(ctx)
    tot: Dict[str, List[Decimal]] = defaultdict(list)
    for c in cs.values():
        if c["base_id"] and str(c["base_id"]).startswith(SETS[16] + "-") and c["tag"] in (CHALLENGER, COMPARATOR):
            tot[str(c["tag"])].append(c["list"])                                                  # type: ignore[arg-type]
    if not tot.get(CHALLENGER) or not tot.get(COMPARATOR):
        return {"k": None, "reason": "no hx or om call at N = 16"}
    h = Fraction(sum(tot[CHALLENGER], Decimal(0))) / len(tot[CHALLENGER])
    o = Fraction(sum(tot[COMPARATOR], Decimal(0))) / len(tot[COMPARATOR])
    if h <= 0:
        return {"k": None, "reason": "hx's calls cost $0 at list price"}
    kv = kscript.k_value(o, h, cap=K_CAP, samples_drawn=K_CAP)
    return {"k": kv["k"], "raw_k": kv["raw_k"], "ratio": str(kv["ratio"]), "calls": {t: len(v) for t, v in tot.items()}}


# ---------------------------------------------------------------- the run

def analyse(run_dir: Path, k_path: Path, plan_path: Optional[Path] = None, B: Optional[int] = None, draws: Optional[int] = None,
            ladder_path: Path = LADDER_CURVE, study1_path: Path = STUDY1_ANALYSIS, loader=None) -> Dict[str, object]:
    """Every step of the module text, in order. `B` and `draws` are for tests only (None: 10,000 and 2,000); `loader` too (None: the
    runner's deep verify, pilot.load_set)."""
    Bv = int(B) if B is not None else FAMILY_B
    dv = int(draws) if draws is not None else DRAWS
    run_dir = Path(run_dir)
    for p in (study1_path, ladder_path):                     # §6 needs both (Edith S-D3): refuse before reading anything else
        if not Path(p).is_file():
            raise FileNotFoundError(f"{Path(p).name} is missing: §6 needs Study 1's analysis.json and the ladder's D-87 curve")
    run = load_run(run_dir, plan_path, loader)
    plan = run["sets"]                                                                            # type: ignore[assignment]
    log = run_dir / "calls.jsonl"
    built = build_rows(plan, [log], run["calibration_set_ids"])                                   # type: ignore[arg-type]
    rows = built["rows"]                                                                          # type: ignore[assignment]
    kdoc = check_k(k_path, run_dir)
    k = int(kdoc["k"])                                                                             # type: ignore[call-overload]
    ctx = cost_ctx(plan, built, kdoc, run_dir, draws)                                             # type: ignore[arg-type]
    arms = descriptive_arms(ctx, rows, plan, dv)                                                  # type: ignore[arg-type]
    res: Dict[str, object] = {
        "spec": SPEC,
        "inputs": {"plan": "slim_plan.json (the run folder's copy)", "plan_sha256": run["plan_sha256"],
                   "slim_plan_json_sha256": _sha(run_dir / "slim_plan.json"), "calls_sha256": _sha(log),
                   "compact_table_sha256": _sha(run_dir / "compact_table.csv"), "k_json_sha256": _sha(k_path),
                   "calibration_limits_json_sha256": _sha(run_dir / "calibration_limits.json"),
                   "manifest_sha256": _sha(run_dir / "manifest.json"), "manifest_check": run["manifest_check"],
                   "sets": {str(s["set_id"]): {"n": s["n"], "items_sha256": s["man"].get("items_sha256"),                     # type: ignore[index,union-attr]
                                               "arms_sent": [a.name for a in s["arms"]],                                     # type: ignore[index,union-attr]
                                               "arms_cut": [a["tag"] for a in s["cut"]]} for s in plan},                     # type: ignore[index,union-attr]
                   "trial_round_sets": run["calibration_set_ids"]},
        "plan_as_run": plan_as_run(run),
        "records": {"final_non_calibration": len(built["records"]), "trial_round_ignored": len(built["calibration"]),  # type: ignore[arg-type]
                    "rows": len(rows), "missing_rows": sum(1 for r in rows if r.get("kind") == "missing"),           # type: ignore[union-attr]
                    "planned_rows": len(built["planned"])},                                                        # type: ignore[arg-type]
        "k": kdoc, "k_from_call_log": k_from_call_log(ctx), "b2_run": k >= 1,
        "constants": {"base_seed": BASE_SEED, "B": Bv, "draws": dv, "alpha": bootstrap.ALPHA, "margins": dict(MARGINS),
                      "designed_tries": DESIGNED, "test_sets": {t: SETS[n] for t, (n, _) in TESTS.items()}},
        "completeness": completeness(rows),                                                       # type: ignore[arg-type]
        "confirmatory": confirmatory(rows, k, Bv),                                                # type: ignore[arg-type]
        "missing_left_out": exclude_missing_view(rows, k, Bv, dv),                                    # type: ignore[arg-type]
        "error_ratios": error_ratios(rows, k, Bv),                                                # type: ignore[arg-type]
        "sensitivity_exposed_bases_excluded": sensitivity_exposed(rows, k, Bv),                   # type: ignore[arg-type]
        "costs_beside_tests": costs_beside_tests(ctx, kdoc),
        "per_form": per_form(rows, k, dv),                                                        # type: ignore[arg-type]
        "descriptive": {"arms": arms,
                        "effort_figure": effort_figure(arms, study1_points(study1_path)),
                        "length_curve": length_curve(arms, ladder_curve(ladder_path)),
                        "vote_curve_n16": vote_curve(ctx, rows, k, dv),                          # type: ignore[arg-type]
                        "format_refusals_truncations_missing": compliance(ctx, plan, rows)},     # type: ignore[arg-type]
        "trial_round": calibration_report(built["calibration"], run_dir),                        # type: ignore[arg-type]
        "choices": CHOICES}
    return res


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True,
                    help="the run folder (slim_plan.json, calls.jsonl, calibration_limits.json, manifest.json, compact_table.csv)")
    ap.add_argument("--plan", type=Path, help="optional: the plan file; it must be the run's own copy (slim_plan.json)")
    ap.add_argument("--k", type=Path, required=True, help="k.json from harness.analysis.study1b_k, committed before this runs")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: the driver runs once")
    res = analyse(a.run, a.k, a.plan)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
