"""The Study 1b slim runner (D-96; research/study1b-spec.md, frozen in lock 4 at 9c007e5, sections 3, 7 and 8): a run PLAN file in, Batch requests out. A list
of single-call arms per frozen ledger set, a token limit per arm, the trial round (wave 0 here), the cost-only cut order, and nothing
else (no E3, no real-time subset, no prompt variant).

    python3 -m harness.pareto.slim plan --plan PLAN.json --cap C [--run-id ID] [--limits calibration_limits.json]
    python3 -m harness.pareto.slim dry  --plan PLAN.json --cap C --run-id ID --out DIR
    python3 -m harness.pareto.slim live --plan PLAN.json --cap C --run-id ID --clearance FILE [--expect-plan-sha256 HEX]

`--cap` is required in every mode (no default; lock-4 audit A6: the Study 1b cap is D-102's $130, so `--cap 130`). `plan` prints the
plan's `plan_sha256` in its output; `live --expect-plan-sha256 HEX` refuses unless the plan file's `plan_sha256` is HEX (audit A16:
the clearance pins it). `dry --out` refuses a folder under the repository's or the shared data root's `data/` or `research/` (audit
A5: the never-sent check searches those as text, so a dry run there would plant the test ids and prompts where it reads).

`plan` and `dry` never touch the network and never read `.env`. `live` is main.py's live path (explicit `--cap`, Edith's
`--clearance`, `live.open_live_guard`, the real transport, writing next to its ledger, `--out` refused); it refuses a plan marked
"draft" or with a measured arm's cost missing. Everything that sends, resumes or stops is REUSED, not copied: `batch.run_batches`
(waves under the caps, the Console-check stop, resume that settles only a call's own batches, read retries, the orphan refusal, the 2%
truncation pause), `batch.release_pause` / `waive_pause`, `main.window_check` (the 48-hour window), `main.check_main_set` and
`main._item` (the set check, the request, the custom id), `pilot.load_set` (the deep verify), `pilot.grader` and
`table.write_compact_table`.

The plan file (`read_plan` / `validate_plan` check it; `data/plans/study1b-plan.json` is the Study 1b plan):
- `sets`: one per length (`steps` unique), each with its folder, the manifest's `items_sha256`, and its arms. An arm has `tag`
  (lowercase letters only, as `kscript.parse_custom_id` needs; unique in its set; never `rt...` or `es`), `model` (request.MODEL_IDS),
  `effort` (request.EFFORTS, every model), `n` (tries per item, 1..99), `role`, `thinking_off` (Haiku at effort high or below only)
  and EITHER a fixed `max_tokens` (1..128,000; a measured arm, with `cost_basis` {cost_usd_sum, calls, source} for the cut order; a
  null `cost_usd_sum` means "to fill" and blocks `live`) OR `calibrate` {floor, wave0_max_tokens} (an arm set by the section 7 rule).
- `calibration`: the wave-0 sets (one per length that has a calibrated arm; already-used sets, never a test set), `base_puzzles` (the
  first B base puzzles, both forms), `tries` per item, and the `rule` {factor, round_up_to, max_tokens_cap, on_truncation}.
- `cut`: `multiplier`, `share_of_cap` (decimal strings), `order` (parts, each a list of [steps, tag]) and `never_cut`.

Custom ids: `<item id>-<tag>-<NN>` (NN = 01..n), as main.py's single-call setups. Wave-0 ids are on the calibration sets' items (for
example `ladder-ledger-l14n16-v1-003-16x1-hx-01`), so they carry the ladder set id and can never be taken for a test call; their meta
says `"phase": "calibration"`, and they are never graded here (the compact table's `right` is blank for them).

The run (all on one call log, one guard, one cap):
1. Wave 0: every calibrated arm, `tries` per calibration item, at its `wave0_max_tokens`. No truncation pause (it is not a test wave;
   a truncation there is a measurement). The limits wait until every wave-0 call is final (an errored one is sent again by running the
   same command; until then the run stops with "calibration_incomplete").
2. The limits, ONCE (a `calibration_limits` line; a resumed run reads it back): for each calibrated arm, min(max_tokens_cap,
   max(floor, factor x the largest wave-0 output, rounded up to round_up_to)); `on_truncation` (128,000) if any of its wave-0 calls
   stopped at max_tokens. Reads only custom_id, final, kind, stop_reason, meta, usage_raw.output_tokens and cost_usd: never answer_text.
3. The cut, ONCE, cost only (Edith S-1; a `cut` line): projected = wave 0's Batch cost + multiplier x the sum over the remaining arms of
   (Batch cost per call x planned calls); a calibrated arm's cost per call is its wave-0 mean, a measured arm's its `cost_basis`. While
   projected > share_of_cap x the cap, the next part of `order` is cut (recomputed after each). Arms in `never_cut` are never cut. If
   the order runs out and projected is still over, the run stops ("projected_over_cap") until `--accept-projection NOTE` records the
   user's ruling (the cut is not recomputed). That note is refused unless the stop has happened (Edith S-R1).
4. The test waves (`send_waves`; lock-4 audit A1): the CONFIRMATORY arms first (role "confirmatory": hx and om at 16, then at 6, the
   sets in plan order), then every other arm (16, then 6, then the 12-step set). Each wave is one set's arms of one phase, a
   `run_batches` call with the 2% pause (so the pause's per-tag shares never mix lengths): an arm truncating over 2% of a batch pauses
   the run before the next batch, with no automatic change (`--release-pause NOTE` goes on, `--truncation-pause-off NOTE` turns it
   off; main.py's runbook). Every confirmatory call must be FINAL before any other arm is sent: if one is not (an errored call), the
   run stops with "confirmatory_incomplete" and the same command sends it again (as wave 0). Only the send ORDER differs from one set
   at a time: the requests, custom ids, limits, cut and manifest are the same.

Resume: the SAME command again. The plan is copied into the run folder at the first start (`slim_plan.json`); a later start with a
different plan is refused. Finished calls are never sent twice; unsettled batches are collected; each `run_batches` call settles only
its own batches; an orphan stops the run (`batch.adopt_orphan` / `close_orphan`, the main runbook).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .main import TRUNCATION_PAUSE, MainSetup, _item, check_main_set, window_check
from .pilot import HAIKU, Item, grader, load_set
from .request import EFFORTS, MAX_OUTPUT_TOKENS, MODEL_IDS

ROOT = Path(__file__).resolve().parents[2]
TAG_RE = re.compile(r"^[a-z]+$")
RESERVED_TAGS = ("es",)                 # E3's step tag; "rt..." is the real-time prefix
ROLES = ("confirmatory", "descriptive", "exploratory")
THINKING_OFF_EFFORTS = ("low", "medium", "high")
PLAN_KEYS = {"study", "run_id_prefix", "draft", "notes", "sets", "calibration", "cut", "spec"}
SET_KEYS = {"set", "items_sha256", "steps", "arms", "note"}
ARM_KEYS = {"tag", "model", "effort", "n", "max_tokens", "calibrate", "cost_basis", "thinking_off", "role", "note", "to_confirm"}
ARM_REQUIRED = {"tag", "model", "effort", "n", "role"}
CAL_KEYS = {"sets", "base_puzzles", "tries", "rule", "note"}
RULE_KEYS = {"factor", "round_up_to", "max_tokens_cap", "on_truncation"}
CUT_KEYS = {"multiplier", "share_of_cap", "order", "never_cut", "note"}
LIMITS_KIND, CUT_KIND, ACCEPT_KIND = "calibration_limits", "cut", "projection_accepted"
NOTE = "Study 1b slim runner (D-96): wave 0 (calibration, ladder sets), limits and cut once (log lines), then the test sets"

ArmKey = Tuple[int, str]                 # (steps, tag)


class PlanError(ValueError):
    """The plan file breaks a rule; nothing is built or sent."""


def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _tokens(x: object, what: str) -> int:
    if not (_is_int(x) and 1 <= x <= MAX_OUTPUT_TOKENS):                                    # type: ignore[operator]
        raise PlanError(f"{what} must be an integer in 1..{MAX_OUTPUT_TOKENS}")
    return int(x)                                                                           # type: ignore[call-overload]


def _dec(x: object, what: str) -> Fraction:
    if not (isinstance(x, str) and re.fullmatch(r"\d+(\.\d+)?", x)):
        raise PlanError(f"{what} is a decimal string such as \"1.5\"")
    return Fraction(Decimal(x))


def _set_entry(s: object, where: str) -> None:
    if not isinstance(s, dict):
        raise PlanError(f"{where}: each set is an object")
    if not isinstance(s.get("set"), str) or not s["set"]:
        raise PlanError(f"{where}: a set names its folder (\"set\")")
    if not (isinstance(s.get("items_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", s["items_sha256"])):
        raise PlanError(f"{s['set']}: items_sha256 must be the manifest's 64-hex hash")
    if not (_is_int(s.get("steps")) and s["steps"] >= 1):
        raise PlanError(f"{s['set']}: steps must be a positive integer")


def validate_plan(plan: Dict) -> Dict:
    """Check a plan's shape, every arm, the calibration block and the cut (no set is read here; `load_sets` checks the sets)."""
    if not isinstance(plan, dict):
        raise PlanError("the plan is a JSON object")
    extra = set(plan) - PLAN_KEYS
    if extra:
        raise PlanError(f"unknown plan keys {sorted(extra)}")
    if not isinstance(plan.get("study"), str) or not plan["study"].strip():
        raise PlanError("the plan names its study")
    if "run_id_prefix" in plan and not (isinstance(plan["run_id_prefix"], str) and plan["run_id_prefix"]):
        raise PlanError("run_id_prefix, if given, is a non-empty string")
    sets = plan.get("sets")
    if not isinstance(sets, list) or not sets:
        raise PlanError("the plan has a non-empty list of sets")
    steps_seen, folders, arms_by_key = set(), set(), {}
    for s in sets:
        _set_entry(s, "sets")
        extra = set(s) - SET_KEYS
        if extra:
            raise PlanError(f"{s['set']}: unknown set keys {sorted(extra)}")
        if s["set"] in folders or s["steps"] in steps_seen:
            raise PlanError(f"{s['set']}: one set per folder and one set per length (the cut order names arms by length and tag)")
        folders.add(s["set"])
        steps_seen.add(s["steps"])
        arms = s.get("arms")
        if not isinstance(arms, list) or not arms:
            raise PlanError(f"{s['set']}: a non-empty list of arms")
        for a in arms:
            _check_arm(s["set"], a)
            if (s["steps"], a["tag"]) in arms_by_key:
                raise PlanError(f"{s['set']}: tag {a['tag']!r} used twice")
            arms_by_key[(s["steps"], a["tag"])] = a
    _check_calibration(plan, steps_seen, folders, arms_by_key)
    _check_cut(plan, arms_by_key)
    return plan


def _check_arm(set_name: str, a: object) -> None:
    if not isinstance(a, dict):
        raise PlanError(f"{set_name}: each arm is an object")
    where = f"{set_name}/{a.get('tag')}"
    missing = ARM_REQUIRED - set(a)
    if missing:
        raise PlanError(f"{where}: missing {sorted(missing)}")
    extra = set(a) - ARM_KEYS
    if extra:
        raise PlanError(f"{where}: unknown arm keys {sorted(extra)}")
    tag = a["tag"]
    if not (isinstance(tag, str) and TAG_RE.match(tag)):
        raise PlanError(f"{where}: a tag is lowercase letters only (kscript.parse_custom_id)")
    if tag.startswith("rt") or tag in RESERVED_TAGS:
        raise PlanError(f"{where}: tag {tag!r} is reserved (rt... is the real-time prefix, es is E3's step tag)")
    if a["model"] not in MODEL_IDS:
        raise PlanError(f"{where}: model {a['model']!r} is not one of {MODEL_IDS}")
    if a["effort"] not in EFFORTS:
        raise PlanError(f"{where}: effort {a['effort']!r} is not one of {EFFORTS}")
    off = a.get("thinking_off", False)
    if not isinstance(off, bool):
        raise PlanError(f"{where}: thinking_off is true or false")
    if off and (a["model"] != HAIKU or a["effort"] not in THINKING_OFF_EFFORTS):
        raise PlanError(f"{where}: thinking can be switched off only on Haiku, at effort high or below")
    if not (_is_int(a["n"]) and 1 <= a["n"] <= 99):
        raise PlanError(f"{where}: n (tries per item) is an integer in 1..99 (two-digit sample numbers)")
    if a["role"] not in ROLES:
        raise PlanError(f"{where}: role is one of {ROLES}")
    if ("max_tokens" in a) == ("calibrate" in a):
        raise PlanError(f"{where}: an arm has EITHER a fixed max_tokens (measured) OR calibrate (set by the wave-0 rule)")
    if "max_tokens" in a:
        _tokens(a["max_tokens"], f"{where}: max_tokens")
        cb = a.get("cost_basis")
        if not (isinstance(cb, dict) and set(cb) == {"cost_usd_sum", "calls", "source"}):
            raise PlanError(f"{where}: a measured arm has cost_basis {{cost_usd_sum, calls, source}} (cost_usd_sum null = to fill)")
        if cb["cost_usd_sum"] is not None:
            _dec(cb["cost_usd_sum"], f"{where}: cost_basis.cost_usd_sum")
            if not (_is_int(cb["calls"]) and cb["calls"] >= 1):
                raise PlanError(f"{where}: cost_basis.calls is a positive integer")
    else:
        if "cost_basis" in a:
            raise PlanError(f"{where}: a calibrated arm's cost per call comes from wave 0, not cost_basis")
        c = a["calibrate"]
        if not (isinstance(c, dict) and set(c) == {"floor", "wave0_max_tokens"}):
            raise PlanError(f"{where}: calibrate is {{floor, wave0_max_tokens}}")
        _tokens(c["floor"], f"{where}: calibrate.floor")
        _tokens(c["wave0_max_tokens"], f"{where}: calibrate.wave0_max_tokens")


def _check_calibration(plan: Dict, steps_seen: set, test_folders: set, arms_by_key: Dict[ArmKey, Dict]) -> None:
    cal = plan.get("calibration")
    calibrated_steps = {k[0] for k, a in arms_by_key.items() if "calibrate" in a}
    if cal is None:
        if calibrated_steps:
            raise PlanError("calibrated arms need a calibration block")
        return
    if not isinstance(cal, dict) or set(cal) - CAL_KEYS:
        raise PlanError(f"calibration has only the keys {sorted(CAL_KEYS)}")
    cs = cal.get("sets")
    if not isinstance(cs, list):
        raise PlanError("calibration.sets is a list")
    have = set()
    for s in cs:
        _set_entry(s, "calibration.sets")
        if set(s) - {"set", "items_sha256", "steps", "note"}:
            raise PlanError(f"{s['set']}: unknown calibration set keys")
        if s["set"] in test_folders:
            raise PlanError(f"{s['set']}: a calibration set is never a test set")
        if s["steps"] in have:
            raise PlanError(f"calibration: two sets at {s['steps']} steps")
        have.add(s["steps"])
    if calibrated_steps - have:
        raise PlanError(f"calibration: no set at {sorted(calibrated_steps - have)} steps for the calibrated arms there")
    if not (_is_int(cal.get("base_puzzles")) and cal["base_puzzles"] >= 1):
        raise PlanError("calibration.base_puzzles is a positive integer")
    if not (_is_int(cal.get("tries")) and 1 <= cal["tries"] <= 99):
        raise PlanError("calibration.tries is an integer in 1..99")
    r = cal.get("rule")
    if not (isinstance(r, dict) and set(r) == RULE_KEYS):
        raise PlanError(f"calibration.rule is {sorted(RULE_KEYS)}")
    if not (_is_int(r["factor"]) and r["factor"] >= 1) or not (_is_int(r["round_up_to"]) and r["round_up_to"] >= 1):
        raise PlanError("calibration.rule factor and round_up_to are positive integers")
    cap = _tokens(r["max_tokens_cap"], "calibration.rule.max_tokens_cap")
    if _tokens(r["on_truncation"], "calibration.rule.on_truncation") > cap:
        raise PlanError("calibration.rule.on_truncation is at most max_tokens_cap")
    for (st, tag), a in arms_by_key.items():
        if "calibrate" in a and a["calibrate"]["floor"] > cap:
            raise PlanError(f"{st}/{tag}: floor over the rule's max_tokens_cap")


def _key(x: object, what: str, arms_by_key: Dict[ArmKey, Dict]) -> ArmKey:
    if not (isinstance(x, list) and len(x) == 2 and _is_int(x[0]) and isinstance(x[1], str)):
        raise PlanError(f"{what}: an arm is named [steps, tag]")
    k = (int(x[0]), str(x[1]))
    if k not in arms_by_key:
        raise PlanError(f"{what}: no arm {list(k)} in the plan")
    return k


def _check_cut(plan: Dict, arms_by_key: Dict[ArmKey, Dict]) -> None:
    cut = plan.get("cut")
    if cut is None:
        return
    if not isinstance(cut, dict) or set(cut) - CUT_KEYS:
        raise PlanError(f"cut has only the keys {sorted(CUT_KEYS)}")
    _dec(cut.get("multiplier"), "cut.multiplier")
    if not 0 < _dec(cut.get("share_of_cap"), "cut.share_of_cap") <= 1:
        raise PlanError("cut.share_of_cap is in (0, 1]")
    never = {_key(x, "cut.never_cut", arms_by_key) for x in cut.get("never_cut") or []}
    order = cut.get("order")
    if not isinstance(order, list):
        raise PlanError("cut.order is a list of parts")
    seen = set()
    for part in order:
        if not (isinstance(part, dict) and set(part) == {"name", "arms"} and isinstance(part["arms"], list) and part["arms"]):
            raise PlanError("each cut part is {name, arms: [[steps, tag], ...]}")
        for x in part["arms"]:
            k = _key(x, f"cut part {part['name']!r}", arms_by_key)
            if k in never:
                raise PlanError(f"cut part {part['name']!r} names {list(k)}, which is never cut")
            if k in seen:
                raise PlanError(f"{list(k)} is in two cut parts")
            seen.add(k)


def read_plan(path: Path) -> Dict:
    return validate_plan(json.loads(Path(path).read_text()))


def plan_sha256(plan: Dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def missing_costs(plan: Dict) -> List[ArmKey]:
    return [(s["steps"], a["tag"]) for s in plan["sets"] for a in s["arms"] if "max_tokens" in a and a["cost_basis"]["cost_usd_sum"] is None]


def set_path(s: Dict, root: Path = ROOT) -> Path:
    p = Path(s["set"])
    return p if p.is_absolute() else Path(root) / p


SetT = Tuple[Dict, Dict, List[Dict]]     # (plan set entry, manifest, items)
Loader = Callable[[Path], Tuple[Dict, List[Dict]]]


def _load_one(s: Dict, loader: Loader, root: Path) -> SetT:
    man, items = loader(set_path(s, root))
    if man.get("items_sha256") != s["items_sha256"]:
        raise PlanError(f"{s['set']}: the manifest's items_sha256 {man.get('items_sha256')} is not the plan's {s['items_sha256']}")
    n = check_main_set(man, items)
    if n != s["steps"]:
        raise PlanError(f"{s['set']}: the set has {n} steps, the plan says {s['steps']}")
    return s, man, items


def load_sets(plan: Dict, loader: Optional[Loader] = None, root: Path = ROOT) -> Tuple[List[SetT], List[SetT]]:
    """(test sets, calibration sets), each loaded (deep verify by default) and checked as main.check_main_set, against the plan's
    items_sha256 and steps; set ids distinct across both lists; each calibration set holds at least `base_puzzles` base puzzles."""
    loader = loader or load_set
    test = [_load_one(s, loader, root) for s in plan["sets"]]
    cal_block = plan.get("calibration") or {}
    cal = [_load_one(s, loader, root) for s in cal_block.get("sets") or []]
    ids = [m["set_id"] for _, m, _ in test + cal]
    if len(ids) != len(set(ids)):
        raise PlanError(f"a set id appears twice: {ids}")
    for s, man, items in cal:
        if len({int(it["base_index"]) for it in items}) < int(cal_block["base_puzzles"]):
            raise PlanError(f"{s['set']}: fewer base puzzles than calibration.base_puzzles")
    return test, cal


def _setup(a: Dict, max_tokens: int, n: Optional[int] = None) -> MainSetup:
    return MainSetup(a["tag"], a["model"], a["effort"], a["n"] if n is None else n, int(max_tokens), a["role"],
                     bool(a.get("thinking_off", False)))


def build_test_requests(plan: Dict, s: Dict, man: Dict, items: List[Dict], limits: Optional[Dict[str, int]] = None,
                        cut: Iterable[str] = ()) -> List[Item]:
    """One test set's requests, in main.py's order (item, arm, try). A calibrated arm uses `limits[tag]` (the wave-0 rule's value; the
    floor when no limits are given, for the plan's lower bound); arms whose tag is in `cut` are left out."""
    check_main_set(man, items)
    cut = set(cut)
    out: List[Item] = []
    for it in items:
        for a in s["arms"]:
            if a["tag"] in cut:
                continue
            mt = a["max_tokens"] if "max_tokens" in a else (limits or {}).get(a["tag"], a["calibrate"]["floor"])
            su = _setup(a, mt)
            for k in range(1, su.n + 1):
                cid, params, meta = _item(man, it, su, su.name, k)
                out.append((cid, params, dict(meta, study=plan["study"], role=a["role"], phase="test")))
    return out


def build_wave0_requests(plan: Dict, test: List[SetT], cal: List[SetT]) -> List[Item]:
    """Wave 0: each calibrated arm of each test set, `tries` per item on the calibration set of the same length (base puzzles
    0..base_puzzles-1, both forms), at the arm's wave0_max_tokens. Custom ids carry the calibration set's id."""
    block = plan.get("calibration")
    if block is None:
        return []
    by_steps = {s["steps"]: (man, items) for s, man, items in cal}
    out: List[Item] = []
    for s, _, _ in test:
        arms = [a for a in s["arms"] if "calibrate" in a]
        if not arms:
            continue
        man, items = by_steps[s["steps"]]
        chosen = [it for it in items if int(it["base_index"]) < int(block["base_puzzles"])]
        for it in chosen:
            for a in arms:
                su = _setup(a, a["calibrate"]["wave0_max_tokens"], int(block["tries"]))
                for k in range(1, su.n + 1):
                    cid, params, meta = _item(man, it, su, su.name, k)
                    out.append((cid, params, dict(meta, study=plan["study"], role="calibration", phase="calibration",
                                                  calibrates_steps=s["steps"])))
    _no_duplicates(out)
    return out


def manifest_requests(plan: Dict, test: List[SetT], cal: List[SetT]) -> List[Item]:
    """The run manifest's request list (written once, at the first start): wave 0, then every test arm at its floor (no limits, no
    cut). The 1b analysis driver rebuilds the manifest with this same function."""
    return build_wave0_requests(plan, test, cal) + [r for s, man, items in test for r in build_test_requests(plan, s, man, items)]


def sent_test_requests(plan: Dict, s: Dict, man: Dict, items: List[Dict], limits: Optional[Dict[str, object]],
                       cut: Dict[str, object]) -> List[Item]:
    """One test set's requests as the run sends them: each calibrated arm at its calibration_limits value, the cut line's arms left
    out. The 1b analysis driver plans its scored rows with this same function."""
    return build_test_requests(plan, s, man, items, limits_for(limits, s["steps"]), cut_tags(cut, s["steps"]))


CONFIRMATORY, DESCRIPTIVE = "confirmatory", "descriptive"


def _phase(a: Dict) -> str:
    return CONFIRMATORY if a["role"] == "confirmatory" else DESCRIPTIVE


def wave_order(plan: Dict) -> List[Tuple[int, str, List[str]]]:
    """The test waves' order (lock-4 audit A1): [(steps, phase, tags)], the confirmatory arms of each set in plan order, then the other
    arms of each set in plan order (cut arms included here; `send_waves` leaves them out)."""
    out = []
    for phase in (CONFIRMATORY, DESCRIPTIVE):
        for s in plan["sets"]:
            tags = [a["tag"] for a in s["arms"] if _phase(a) == phase]
            if tags:
                out.append((int(s["steps"]), phase, tags))
    return out


def send_waves(plan: Dict, test: List[SetT], limits: Optional[Dict[str, object]], cut: Dict[str, object]) -> List[Dict[str, object]]:
    """The test requests as sent (`sent_test_requests`: limits applied, cut arms out), split into `wave_order`'s waves: [{"set_id",
    "steps", "phase", "requests"}] (a wave left empty by the cut is dropped). The union is exactly the per-set lists, item order kept."""
    by_steps = {int(s["steps"]): (s, man, items) for s, man, items in test}
    out = []
    for steps, phase, tags in wave_order(plan):
        s, man, items = by_steps[steps]
        reqs = [r for r in sent_test_requests(plan, s, man, items, limits, cut) if r[2]["setup"] in tags]
        if reqs:
            out.append({"set_id": man["set_id"], "steps": steps, "phase": phase, "requests": reqs})
    return out


def _no_duplicates(reqs: List[Item]) -> None:
    ids = [r[0] for r in reqs]
    if len(ids) != len(set(ids)):
        raise PlanError("duplicate custom_id")


# ---- the wave-0 rule (section 7): usage and stop_reason only ----

def wave0_counts(records: Iterable[Dict[str, object]], wave0_ids: Iterable[str]) -> Dict[ArmKey, Dict[str, object]]:
    """{(steps, tag): {final, truncated, output_tokens_max, cost_usd_sum}} over the FINAL records of wave 0. Reads only custom_id,
    final, kind, stop_reason, meta.calibrates_steps, meta.setup, usage_raw.output_tokens and cost_usd: never answer_text."""
    want = set(wave0_ids)
    out: Dict[ArmKey, Dict[str, object]] = {}
    for r in records:
        if not r.get("final") or r.get("custom_id") not in want:
            continue
        meta = r.get("meta") or {}
        key = (int(meta.get("calibrates_steps")), str(meta.get("setup")))                 # type: ignore[union-attr,arg-type]
        row = out.setdefault(key, {"final": 0, "truncated": 0, "output_tokens_max": 0, "cost_usd_sum": Decimal(0)})
        row["final"] += 1                                                                  # type: ignore[operator]
        row["truncated"] += int(r.get("kind") == "truncated" or r.get("stop_reason") == "max_tokens")  # type: ignore[operator]
        u = r.get("usage_raw")
        ot = u.get("output_tokens") if isinstance(u, dict) else None
        if not _is_int(ot):
            raise RuntimeError(f"{r.get('custom_id')}: a final wave-0 record with no output token count; a human must look")
        row["output_tokens_max"] = max(int(row["output_tokens_max"]), int(ot))           # type: ignore[call-overload]
        if r.get("cost_usd") is not None:
            row["cost_usd_sum"] += Decimal(str(r.get("cost_usd")))                        # type: ignore[operator]
    return out


def calibrated_limit(output_tokens_max: int, truncated: bool, floor: int, rule: Dict[str, int]) -> int:
    """Section 7: min(cap, max(floor, factor x the largest output, rounded UP to round_up_to)); on_truncation if any call truncated."""
    if truncated:
        return int(rule["on_truncation"])
    step = int(rule["round_up_to"])
    raw = int(rule["factor"]) * int(output_tokens_max)
    return min(int(rule["max_tokens_cap"]), max(int(floor), -(-raw // step) * step))


def decide_limits(plan: Dict, counts: Dict[ArmKey, Dict[str, object]]) -> Dict[str, object]:
    rule = plan["calibration"]["rule"]
    arms = []
    for s in plan["sets"]:
        for a in s["arms"]:
            if "calibrate" not in a:
                continue
            c = counts.get((s["steps"], a["tag"]), {"final": 0, "truncated": 0, "output_tokens_max": 0, "cost_usd_sum": Decimal(0)})
            lim = calibrated_limit(int(c["output_tokens_max"]), int(c["truncated"]) > 0, a["calibrate"]["floor"], rule)  # type: ignore[call-overload]
            arms.append({"steps": s["steps"], "tag": a["tag"], "wave0_calls": c["final"], "wave0_truncated": c["truncated"],
                         "wave0_output_tokens_max": c["output_tokens_max"], "wave0_cost_usd_sum": str(c["cost_usd_sum"]),
                         "floor": a["calibrate"]["floor"], "wave0_max_tokens": a["calibrate"]["wave0_max_tokens"], "max_tokens": lim})
    return {"rule": rule, "arms": arms,
            "reads": "custom_id, final, kind, stop_reason, meta, usage_raw.output_tokens, cost_usd (never answer_text)"}


def _one_line(log, kind: str) -> Optional[Dict[str, object]]:
    lines = [r for r in log.records() if r.get("kind") == kind]
    if len(lines) > 1:
        raise RuntimeError(f"more than one {kind} line in the call log; a human must look")
    return lines[0] if lines else None


def apply_limits(log, run_id: str, plan: Dict, wave0: List[Item]) -> Dict[str, object]:
    """Idempotent: the calibration_limits line if the log has one, else computed from wave 0's counts and written."""
    got = _one_line(log, LIMITS_KIND)
    if got is not None:
        return got
    line = dict(decide_limits(plan, wave0_counts(log.records(), [r[0] for r in wave0])), kind=LIMITS_KIND, run_id=run_id,
                final=False, plan_sha256=plan_sha256(plan))
    log.write(line)
    return line


def limits_for(limits: Optional[Dict[str, object]], steps: int) -> Dict[str, int]:
    if limits is None:
        return {}
    return {str(a["tag"]): int(a["max_tokens"]) for a in limits["arms"] if int(a["steps"]) == steps}  # type: ignore[index,union-attr]


# ---- the cut order (section 7, Edith S-1): costs only ----

def arm_costs(plan: Dict, limits: Dict[str, object]) -> Dict[ArmKey, Optional[Fraction]]:
    """Batch cost per call per arm: a calibrated arm's wave-0 mean, a measured arm's cost_basis (None when still to fill)."""
    out: Dict[ArmKey, Optional[Fraction]] = {}
    w0 = {(int(a["steps"]), str(a["tag"])): a for a in limits["arms"]}                    # type: ignore[union-attr,index]
    for s in plan["sets"]:
        for a in s["arms"]:
            k = (s["steps"], a["tag"])
            if "calibrate" in a:
                row = w0[k]
                n = int(row["wave0_calls"])                                                # type: ignore[call-overload]
                out[k] = Fraction(Decimal(str(row["wave0_cost_usd_sum"]))) / n if n else None
            else:
                cb = a["cost_basis"]
                out[k] = None if cb["cost_usd_sum"] is None else Fraction(Decimal(cb["cost_usd_sum"])) / int(cb["calls"])
    return out


def decide_cut(plan: Dict, planned_calls: Dict[ArmKey, int], cost: Dict[ArmKey, Optional[Fraction]], spent: Fraction,
               cap: Fraction) -> Dict[str, object]:
    """projected = spent + multiplier x sum(cost per call x planned calls) over the arms not cut; while projected > share_of_cap x cap,
    cut the next part of the order (recomputed after each). Costs only."""
    c = plan["cut"]
    mult, share = Fraction(Decimal(c["multiplier"])), Fraction(Decimal(c["share_of_cap"]))
    gaps = sorted(k for k in planned_calls if cost.get(k) is None)
    if gaps:
        raise PlanError(f"the cut needs a cost per call for every arm; missing for {[list(k) for k in gaps]}")
    limit = share * cap

    def projected(cut: set) -> Fraction:
        return spent + mult * sum((cost[k] * planned_calls[k] for k in planned_calls if k not in cut), Fraction(0))  # type: ignore[operator]
    cut: set = set()
    steps = []
    p = projected(cut)
    parts = list(c["order"])
    while p > limit and parts:
        part = parts.pop(0)
        before = p
        cut |= {(int(x[0]), str(x[1])) for x in part["arms"]}
        p = projected(cut)
        steps.append({"part": part["name"], "arms": part["arms"], "projected_before_usd": _usd(before), "projected_after_usd": _usd(p)})
    return {"cap_usd": _usd(cap), "share_of_cap": c["share_of_cap"], "multiplier": c["multiplier"], "limit_usd": _usd(limit),
            "spent_usd": _usd(spent), "projected_without_cut_usd": _usd(projected(set())), "projected_usd": _usd(p),
            "cut_parts": steps, "cut_arms": sorted([list(k) for k in cut]), "still_over": p > limit,
            "arms": [{"steps": k[0], "tag": k[1], "planned_calls": planned_calls[k], "cost_per_call_usd": _usd(cost[k])}  # type: ignore[arg-type]
                     for k in sorted(planned_calls)],
            "reads": "costs only: wave-0 cost_usd per arm, the plan's cost_basis, planned calls, the cap"}


def _usd(x: Fraction) -> str:
    return str(round(Decimal(x.numerator) / Decimal(x.denominator), 9))


def apply_cut(log, run_id: str, plan: Dict, test: List[SetT], limits: Dict[str, object], wave0: List[Item], cap: Decimal) -> Dict[str, object]:
    """Idempotent: the cut line if the log has one, else decided once (after wave 0) and written. No cut block: nothing is cut."""
    got = _one_line(log, CUT_KIND)
    if got is not None:
        return got
    planned: Dict[ArmKey, int] = {}
    for s, man, items in test:
        for _, _, m in build_test_requests(plan, s, man, items, limits_for(limits, s["steps"])):
            k = (s["steps"], str(m["setup"]))
            planned[k] = planned.get(k, 0) + 1
    ids = {r[0] for r in wave0}
    spent = sum((Fraction(Decimal(str(r["cost_usd"]))) for r in log.records()
                 if r.get("custom_id") in ids and r.get("cost_usd") is not None), Fraction(0))
    if plan.get("cut") is None:
        decision: Dict[str, object] = {"cut_arms": [], "still_over": False, "note": "the plan has no cut block"}
    else:
        decision = decide_cut(plan, planned, arm_costs(plan, limits), spent, Fraction(Decimal(cap)))
    line = dict(decision, kind=CUT_KIND, run_id=run_id, final=False, plan_sha256=plan_sha256(plan))
    log.write(line)
    return line


def cut_tags(cut: Dict[str, object], steps: int) -> List[str]:
    return [str(t) for st, t in cut.get("cut_arms") or [] if int(st) == steps]           # type: ignore[union-attr,misc]


# ---- plan (no calls) ----

def _book(reqs: List[Item]) -> Decimal:
    from .prices import estimate_input_tokens, worst_case
    from .request import prompt_text
    return sum((worst_case(str(p["model"]), estimate_input_tokens(prompt_text(p)), int(p["max_tokens"]), batch=True)  # type: ignore[call-overload]
                for _, p, _ in reqs), Decimal(0))


def slim_plan(guard, plan: Dict, test: List[SetT], cal: List[SetT], limits: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Calls, max_tokens and the guard's Batch worst-case booking per arm and set: wave 0, then the test sets with each calibrated arm
    at its floor (the lower bound), at the rule's cap (the upper bound), and, given `limits` (a calibration_limits line or file), at
    those limits. Plus the measured arms' costs for the cut, and the waves at the guard's cap (as pilot.plan, no spend in between)."""
    from .pilot import plan as pilot_plan
    w0 = build_wave0_requests(plan, test, cal)
    rule = (plan.get("calibration") or {}).get("rule") or {"max_tokens_cap": MAX_OUTPUT_TOKENS}
    w0_arms = []
    for s, _, _ in test:
        for a in s["arms"]:
            if "calibrate" in a:
                mine = [r for r in w0 if r[2]["calibrates_steps"] == s["steps"] and r[2]["setup"] == a["tag"]]
                w0_arms.append({"steps": s["steps"], "tag": a["tag"], "calls": len(mine), "max_tokens": a["calibrate"]["wave0_max_tokens"],
                                "batch_booking_usd": str(_book(mine))})
    cap_limits = {s["steps"]: {a["tag"]: int(rule["max_tokens_cap"]) for a in s["arms"] if "calibrate" in a} for s, _, _ in test}
    out_sets, tot = [], {"floor": Decimal(0), "cap": Decimal(0), "given": Decimal(0), "calls": 0}
    for s, man, items in test:
        at_floor = build_test_requests(plan, s, man, items)
        at_cap = build_test_requests(plan, s, man, items, cap_limits[s["steps"]])
        given = build_test_requests(plan, s, man, items, limits_for(limits, s["steps"])) if limits is not None else None
        arms = []
        for a in s["arms"]:
            def mine(reqs: List[Item]) -> List[Item]:
                return [r for r in reqs if r[2]["setup"] == a["tag"]]
            row: Dict[str, object] = {"tag": a["tag"], "model": a["model"], "effort": a["effort"],
                                      "thinking_off": bool(a.get("thinking_off", False)), "tries_per_item": a["n"], "role": a["role"],
                                      "calls": len(mine(at_floor))}
            if "max_tokens" in a:
                cb = a["cost_basis"]
                row.update(max_tokens=a["max_tokens"], batch_booking_usd=str(_book(mine(at_floor))),
                           cost_per_call_usd=None if cb["cost_usd_sum"] is None else _usd(Fraction(Decimal(cb["cost_usd_sum"])) / cb["calls"]),
                           cost_source=cb["source"])
            else:
                row.update(max_tokens="wave-0 rule", floor=a["calibrate"]["floor"], cap=int(rule["max_tokens_cap"]),
                           batch_booking_at_floor_usd=str(_book(mine(at_floor))), batch_booking_at_cap_usd=str(_book(mine(at_cap))))
            if given is not None:
                lim = mine(given)
                row.update(max_tokens_given_limits=lim[0][1]["max_tokens"] if lim else None, batch_booking_given_limits_usd=str(_book(lim)))
            if "to_confirm" in a:
                row["to_confirm"] = a["to_confirm"]
            arms.append(row)
        sb = {"floor": _book(at_floor), "cap": _book(at_cap), "given": _book(given) if given is not None else None}
        out_sets.append({"set": s["set"], "set_id": man["set_id"], "steps": s["steps"], "items": len(items), "arms": arms,
                         "calls": len(at_floor), "batch_booking_at_floors_usd": str(sb["floor"]),
                         "batch_booking_at_caps_usd": str(sb["cap"]),
                         **({"batch_booking_given_limits_usd": str(sb["given"])} if given is not None else {})})
        tot["calls"] += len(at_floor)                                                       # type: ignore[operator]
        tot["floor"] += sb["floor"]                                                         # type: ignore[operator]
        tot["cap"] += sb["cap"]                                                             # type: ignore[operator]
        if given is not None:
            tot["given"] += sb["given"]                                                     # type: ignore[operator]
    all_floor = w0 + [r for s, man, items in test for r in build_test_requests(plan, s, man, items)]
    p = pilot_plan(guard, all_floor)
    w0_book = _book(w0)
    return {"study": plan["study"], "draft": plan.get("draft"), "plan_sha256": plan_sha256(plan),
            "wave0": {"calls": len(w0), "batch_booking_usd": str(w0_book), "arms": w0_arms,
                      "sets": [{"set": s["set"], "set_id": m["set_id"], "steps": s["steps"]} for s, m, _ in cal]},
            "sets": out_sets, "test_calls": tot["calls"],
            "test_batch_booking_at_floors_usd": str(tot["floor"]), "test_batch_booking_at_caps_usd": str(tot["cap"]),
            **({"test_batch_booking_given_limits_usd": str(tot["given"]),
                "total_batch_booking_given_limits_usd": str(w0_book + tot["given"])} if limits is not None else {}),  # type: ignore[operator]
            "total_calls": len(w0) + tot["calls"],
            "total_batch_booking_at_floors_usd": str(w0_book + tot["floor"]),                 # type: ignore[operator]
            "total_batch_booking_at_caps_usd": str(w0_book + tot["cap"]),                     # type: ignore[operator]
            "check_floor_total_equals_guard_worst_case": Decimal(p["batch_worst_case_usd"]) == w0_book + tot["floor"],  # type: ignore[operator]
            "cut": plan.get("cut"), "costs_to_fill": [list(k) for k in missing_costs(plan)],
            "cap_usd": str(guard.run_cap), "waves_at_floors_if_nothing_were_spent_between": p.get("waves_if_nothing_were_spent_between"),
            **({"wave_error": p["error"]} if "error" in p else {}),
            "booking_note": "the guard's worst case per call (prices.worst_case, Batch price): prompt at the dearest input rate plus "
                            "max_tokens at the output rate; the bill is a fraction of this. Calibrated arms are bounded by their floor "
                            "and the rule's cap until wave 0 sets them."}


# ---- the run ----

def _check_plan_copy(out_dir: Path, plan: Dict) -> None:
    path = out_dir / "slim_plan.json"
    text = json.dumps(plan, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text() != text:
            raise PlanError(f"{path} holds a different plan: a resumed run uses the plan it started with (a new plan needs a new run id)")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def check_accept_projection(log, note: str) -> None:
    """Edith S-R1: `--accept-projection` answers the "projected_over_cap" stop, so it is accepted ONLY when the log already holds the
    `cut` line with `still_over: true` and no ruling yet (as `--release-pause` is refused when the run is not paused). A note given
    before that stop could otherwise carry an over-budget projection straight into the test waves without the user ever seeing it."""
    if not note.strip():
        raise RuntimeError("--accept-projection needs a recorded note of the user's ruling")
    cut = _one_line(log, CUT_KIND)
    if cut is None or cut.get("still_over") is not True:
        raise RuntimeError("--accept-projection was given but the run has not stopped with the projection over the cap (no cut line "
                           "with still_over: true in the call log); run without it, and give it only after that stop, on the user's ruling")
    if _one_line(log, ACCEPT_KIND) is not None:
        raise RuntimeError("--accept-projection was given but the user's ruling on the projection is already recorded; run without it")


def run_slim(guard, transport, out_dir: Path, plan: Dict, poll_s: float = 60.0, sleep=None,
             pause_truncated_over: Optional[float] = TRUNCATION_PAUSE, release_pause_note: Optional[str] = None,
             waive_pause_note: Optional[str] = None, accept_projection_note: Optional[str] = None,
             max_wave_size: Optional[int] = None, loader=None, now: Optional[Callable[[], datetime]] = None,
             extension_note: Optional[str] = None) -> Dict[str, object]:
    """Wave 0, the limits, the cut, then the test sets one at a time; all on one call log (`out_dir/calls.jsonl`). The compact table is
    written whatever happens. Returns {"wave0", "limits", "cut", "test" ({"<set id> <phase>": summary}, in send order), "stopped",
    "table_cost_usd", "block_rates"}; `stopped` is None, "console_check", "calibration_incomplete", "projected_over_cap",
    "paused_for_truncation" or "confirmatory_incomplete"."""
    from .batch import PausedForTruncation, pause_state, pause_waived, release_pause, run_batches, waive_pause
    from .calllog import CallLog
    from .manifest import write_manifest
    from .table import block_rates, write_compact_table
    validate_plan(plan)
    out_dir = Path(out_dir)
    window_check(out_dir, **({"now": now} if now else {}), extension_note=extension_note)
    test, cal = load_sets(plan, loader)
    _check_plan_copy(out_dir, plan)
    wave0 = build_wave0_requests(plan, test, cal)
    log = CallLog(out_dir / "calls.jsonl")
    if accept_projection_note is not None:
        check_accept_projection(log, accept_projection_note)
    if waive_pause_note is not None:
        waive_pause(log, guard.run_id, waive_pause_note)
    if release_pause_note:
        if pause_state(log) is None:
            raise RuntimeError("--release-pause was given but the run is not paused")
        release_pause(log, guard.run_id, release_pause_note)
    if pause_truncated_over is not None and not pause_waived(log) and pause_state(log) is not None:
        p = pause_state(log)
        raise PausedForTruncation(f"the run paused after batch {p.get('batch_id')}: truncated shares {p.get('shares')}; report it, and "  # type: ignore[union-attr]
                                  "only on the user's ruling release it (slim.py --release-pause NOTE)")
    if not (out_dir / "manifest.json").exists():
        write_manifest(out_dir, guard, manifest_requests(plan, test, cal), "batch" if transport.live else "dry",
                       note=f"{NOTE}; plan {plan_sha256(plan)}; calibrated arms listed at their floors, the limits sent are in the "
                            f"calibration_limits line")
    kw = {"sleep": sleep} if sleep is not None else {}
    grade = grader({it["id"]: it for _, _, items in test for it in items}, "ledger")      # test items only: wave 0 is never graded
    result: Dict[str, object] = {"wave0": None, "limits": None, "cut": None, "test": {}, "stopped": None}
    try:
        if wave0:
            s0 = run_batches(guard, transport, log, wave0, poll_s=poll_s, max_wave_size=max_wave_size, pause_truncated_over=None, **kw)
            result["wave0"] = s0
            if s0.stopped_for_console_check:
                result["stopped"] = "console_check"
                return result
            if _one_line(log, LIMITS_KIND) is None and set(r[0] for r in wave0) - log.finished_ids():
                result["stopped"] = "calibration_incomplete"         # an errored wave-0 call: the same command sends it again
                return result
        limits = apply_limits(log, guard.run_id, plan, wave0)
        result["limits"] = limits
        lim_file = out_dir / "calibration_limits.json"
        if not lim_file.exists():
            lim_file.write_text(json.dumps(limits, indent=1, sort_keys=True) + "\n")
        cut = apply_cut(log, guard.run_id, plan, test, limits, wave0, guard.run_cap)
        result["cut"] = cut
        if cut.get("still_over") and _one_line(log, ACCEPT_KIND) is None:
            if not (accept_projection_note and accept_projection_note.strip()):
                result["stopped"] = "projected_over_cap"
                return result
            log.write({"kind": ACCEPT_KIND, "run_id": guard.run_id, "note": accept_projection_note, "final": False})
        waves = send_waves(plan, test, limits, cut)
        confirmatory_ids = {r[0] for w in waves if w["phase"] == CONFIRMATORY for r in w["requests"]}   # type: ignore[union-attr]
        for w in waves:
            if w["phase"] != CONFIRMATORY and confirmatory_ids - log.finished_ids():
                result["stopped"] = "confirmatory_incomplete"    # an errored confirmatory call: the same command sends it again
                return result
            st = run_batches(guard, transport, log, w["requests"], poll_s=poll_s, max_wave_size=max_wave_size,   # type: ignore[arg-type]
                             pause_truncated_over=pause_truncated_over, **kw)
            result["test"][f"{w['set_id']} {w['phase']}"] = st                              # type: ignore[index]
            if st.stopped_for_console_check:
                result["stopped"] = "console_check"
                return result
            if st.paused_for_truncation:
                result["stopped"] = "paused_for_truncation"
                return result
        if confirmatory_ids - log.finished_ids():
            result["stopped"] = "confirmatory_incomplete"
        return result
    finally:
        result["table_cost_usd"] = str(write_compact_table(log, out_dir / "compact_table.csv", grade=grade))
        result["block_rates"] = block_rates(log)


def forbidden_out(out: Path, root: Path = ROOT) -> Optional[Path]:
    """The data/ or research/ folder (of this checkout, or of the shared data root's checkout) that `out` lies under, or None."""
    dirs = [Path(root) / "data", Path(root) / "research"]
    try:
        from .guard import git_runner_for, shared_data_root
        main_data = shared_data_root(Path(root), git_runner_for(Path(root)))
        dirs += [main_data, main_data.parent / "research"]
    except Exception:                                                                       # no git here: this checkout's folders only
        pass
    o = Path(out).resolve()
    for d in dirs:
        d = d.resolve()
        if o == d or d in o.parents:
            return d
    return None


def _brief(r: Dict[str, object]) -> Dict[str, object]:
    cut = r.get("cut") or {}
    return {"wave0": r["wave0"], "test": r["test"], "stopped": r["stopped"], "table_cost_usd": r.get("table_cost_usd"),
            "limits": [{k: a[k] for k in ("steps", "tag", "wave0_output_tokens_max", "wave0_truncated", "max_tokens")}  # type: ignore[index]
                       for a in (r.get("limits") or {}).get("arms", [])],                                                 # type: ignore[union-attr]
            "cut": {k: cut.get(k) for k in ("projected_without_cut_usd", "projected_usd", "limit_usd", "cut_arms", "still_over")}}  # type: ignore[union-attr]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--run-id", default="slim-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required in every mode (no default; Study 1b: 130, D-102)")
    ap.add_argument("--expect-plan-sha256", help="live only: refuse unless the plan's plan_sha256 (as `plan` prints it) is this value")
    ap.add_argument("--clearance", type=Path)
    ap.add_argument("--limits", type=Path, help="plan only: a calibration_limits.json, to book the test sets at those limits")
    ap.add_argument("--extend-window", help="D-45: a recorded note that extends the 48-hour window (needs the user's say)")
    ap.add_argument("--release-pause", help="after a truncation pause: a recorded note of the user's ruling to go on")
    ap.add_argument("--truncation-pause-off", help="the user's ruling to run without the 2%% truncation pause (a recorded note)")
    ap.add_argument("--accept-projection", help="after projected_over_cap: a recorded note of the user's ruling to go on uncut further")
    a = ap.parse_args(argv)
    if a.cap is None:
        ap.error(f"{a.mode} needs an explicit --cap (no default; Study 1b's is 130, D-102)")
    if a.expect_plan_sha256 is not None and a.mode != "live":
        ap.error("--expect-plan-sha256 is for live only (plan prints the plan_sha256 to pin)")
    if a.mode == "dry":
        if a.out is None:
            ap.error("dry needs --out")
        bad = forbidden_out(a.out)
        if bad is not None:
            ap.error(f"dry --out {a.out} is under {bad}: the never-sent check searches it; use a scratchpad folder")
    from .batch import PausedForTruncation
    from .guard import SpendGuard
    from .transport import DryTransport
    try:
        plan = read_plan(a.plan)
        if a.mode == "live" and plan.get("run_id_prefix") and not a.run_id.startswith(plan["run_id_prefix"]):
            raise PlanError(f"the run id must start with {plan['run_id_prefix']!r}")
        test, cal = load_sets(plan)                    # verified once, then reused by the run
        limits = json.loads(a.limits.read_text()) if a.limits else None
    except (ValueError, OSError) as e:
        ap.error(str(e))
    by_path = {str(set_path(s)): (man, items) for s, man, items in test + cal}

    def loader(p: Path) -> Tuple[Dict, List[Dict]]:
        return by_path[str(p)]
    if a.mode in ("plan", "dry"):
        guard = SpendGuard(a.run_id, Decimal(a.cap), global_spent_usd=Decimal("0"))
        print(json.dumps(slim_plan(guard, plan, test, cal, limits), indent=1, default=str))
        if a.mode == "dry":
            r = run_slim(guard, DryTransport(), a.out, plan, sleep=lambda s: None, loader=loader,
                         accept_projection_note=a.accept_projection)
            print("dry run done:", json.dumps(_brief(r), indent=1, default=str))
        return 0
    if a.clearance is None:
        ap.error("live needs an explicit --cap and --clearance")
    if a.expect_plan_sha256 is not None and a.expect_plan_sha256.strip().lower() != plan_sha256(plan):
        ap.error(f"the plan's plan_sha256 is {plan_sha256(plan)}, not the expected {a.expect_plan_sha256} (the cleared plan): "
                 "nothing was sent")
    if a.out is not None or a.limits is not None:
        ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/) and sets its own limits; do not give --out or --limits")
    if plan.get("draft") or missing_costs(plan):
        ap.error(f"the plan is a draft or has costs to fill {missing_costs(plan)}; a live run needs the final, locked plan")
    from .live import open_live_guard
    from .transport import RealTransport, TransportError
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        transport = RealTransport(guard)
        r = run_slim(guard, transport, folder, plan, loader=loader, extension_note=a.extend_window,
                     release_pause_note=a.release_pause, waive_pause_note=a.truncation_pause_off,
                     accept_projection_note=a.accept_projection)
        print("live run done:", json.dumps(_brief(r), indent=1, default=str))
        if r["stopped"] == "paused_for_truncation":
            print("PAUSED for truncation (an arm over 2% of a batch at max_tokens): report the shares to Edith and the user; run the same "
                  "command with --release-pause '<the user's ruling>' only after they rule (no limit changes by itself)")
        elif r["stopped"] == "console_check":
            print("STOPPED for the Console check: read what the Console shows for this run, then run "
                  "`python3 -m harness.pareto.pilot console-check --run-id ... --cap ... --clearance ... --usd <dollars> --note <where from>` "
                  "and run the same slim command again")
        elif r["stopped"] == "confirmatory_incomplete":
            print("STOPPED: some confirmatory calls (hx, om at 16 and 6) are not final (errored); no other arm is sent until they are. "
                  "Run the same command again to send them under new keys")
        elif r["stopped"] == "calibration_incomplete":
            print("STOPPED: some wave-0 calls are not final (errored or missing); run the same command again to send them under new keys")
        elif r["stopped"] == "projected_over_cap":
            print("STOPPED: after every cut in the order the projection is still over the share of the cap (the cut line); go to the user. "
                  "Only on their ruling: the same command with --accept-projection '<ruling>'")
    except PausedForTruncation as e:
        print(f"PAUSED: {e}")
        return 2
    except TransportError as e:
        print(f"STOPPED: the API did not accept a call ({e.kind}, status {e.status}, billed: {e.billed}). Nothing further was sent. "
              "Look at the call log and the ledger before running again; a call rejected before running is sent again on resume.")
        return 3
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
