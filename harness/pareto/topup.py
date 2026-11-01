"""The top-up run (D-99, D-100; research/topup-run-spec.md, frozen in lock 4 at 9c007e5, Edith CLEAN): a run PLAN file in, Batch rounds out. Four parts,
all Haiku-medium through Batch, on the main set `main-ledger-l14n6-v1`, in their own declared window after the main run's:

- **E2, the Haiku team** (both shapes, every puzzle): 1 planner; then the helpers, one Batch round per task round with lead-by-2 voting
  and a cap of 9 exactly as E3 (`e3.decide`, `e3.record_vote`, the same draw numbering as `e3.plan_round`); then 1 aggregator. At the
  chain (1x6) task k starts from the team's own agreed result of task k-1 (task 1 from the printed start); a task with no result at
  the cap shows "(no result)" from its place onward and the later tasks are never started. At pieces (6x1) the six tasks start from
  their sequences' printed starts and all vote at once; a task with no result shows "(no result)" at its own place only.
  A planner reply that does not parse as exactly Task 1..6 (`team_prompts.parse_plan`; a refused or truncated planner has no plan)
  is `plan_failed`: no helper and no aggregator is sent for that puzzle (it counts wrong as deployed).
- **H-pick8, the Haiku picker** (every puzzle): one call over that puzzle's main-run Haiku-medium samples 1-8 (`team_prompts.picker_prompt`,
  the visible `answer_text` of each, read from the main run's call log by custom id `<item id>-hm-NN`; a sample that did not answer
  is passed as no reply, which the builder shows as "(no reply)"). Every one of the 8 must have a FINAL main-run record, else the run
  stops before anything is sent (`MainRunJoinError`; the CLI prints REFUSED): the spec's 4c rule applied to the runner (Edith's
  ruling 1).
- **C13, step voting on pieces** (every pieces puzzle): E3 through `e3.py` unchanged. Each piece is one step from its printed start,
  built with the approved `ledger.step_call(p, s, 1)` for s = 1..6 (an `e3.Step`); `e3.plan_round`, `e3.e3_status` and `e3.e3_rows`
  run on those steps as they are. The custom ids are E3's own, `<6x1 item id>-es-SSDD`: they cannot clash with the main run's E3 ids
  (those are on 1x6 items), and `e3_rows` reads them unchanged.
- **The same-model check** (Edith, D-99): Haiku-medium x5 at the main run's `hm` settings exactly (`main._item` with `main.BY_NAME["hm"]`:
  max_tokens 5,000, effort medium, adaptive thinking, the approved prompt) on bases 000-019, both shapes, under its own tag. Never
  graded into Study 1 (its analysis is the driver's, spec section 3).

Every prompt is `research/models/team_prompts.py` (D-100) imported by file path, never copied; the file's SHA-256 is pinned
(`TEAM_PROMPTS_SHA256`) and a different file refuses to load. Every new call is Haiku-medium at 48,000 (Amendment 1 section 3,
`e3.E3_MAX_TOKENS`).

    python3 -m harness.pareto.topup plan --plan PLAN.json [--run-id ID] [--cap C] [--main-run DIR]
    python3 -m harness.pareto.topup dry  --plan PLAN.json --run-id ID --out DIR --main-run DIR [--cap C]
    python3 -m harness.pareto.topup live --plan PLAN.json --run-id ID --cap C --clearance FILE [--main-run DIR]

`plan` and `dry` never touch the network and never read `.env`. `live` is main.py's live path (explicit `--cap`, Edith's `--clearance`,
`live.open_live_guard`, the real transport, writing next to its ledger, `--out` refused), and refuses a draft plan, a run id without
the plan's prefix, a missing main-run sample, and a start outside the plan's dates. Its main-run folder defaults to the shared data
root's `raw/<main_run.run_id>/`. Refusals print `REFUSED: ...` and exit 2.

Rounds. Round r's requests are built ONLY from the call log's final records (`plan_round`, pure): the same-model check, the pickers,
the planners and C13's first draws all go in round 1; then each round holds every puzzle's next helper draws (both shapes together),
C13's further draws and the aggregators that are ready. Each round is ONE `batch.run_batches` call (waves under the caps, the
Console-check stop, resume, read retries, the orphan refusal, the 2% truncation pause), on one call log, until nothing is left or
`max_rounds` (counted from the log's `topup_round` lines, so across resumes). Before EVERY round the run's 48-hour window
(`main.window_check`) and, live, the plan's dates (`start_check`) are checked; past either, no new round is sent (`round_check`). REUSED, not copied: `batch.run_batches` / `release_pause` / `waive_pause` / `pause_state`, `main.window_check` (the 48-hour
window), `main.check_main_set`, `main._item`, `pilot.load_set`, `pilot.grader`, `pilot.plan`, `table.write_compact_table`, `slim._book`.

Resume: the SAME command again. The plan is copied into the run folder at the first start (`topup_plan.json`); a later start with a
different plan is refused. A round is marked done (`topup_round_done`) only when its `run_batches` call returned with no stop; a round
with no done line is resumed with the items it was planned with (rebuilt from the log as it stood at its `topup_round` line), so a
batch whose results were being written when the run stopped settles with the same items (batch.py's "settled before a crash" path)
before the next round is planned. A logged final record is never sent again; an errored one is sent again under its own custom id
(run_batches gives it a new guard key); a submitted, unsettled batch is collected, never re-submitted. A collected batch with no
truncation-check line is checked (`batch.check_wave`) before the next round.

The compact table's `right` column is filled only for the aggregator and the same-model check (the calls whose reply is a whole
answer); planner, helper, picker and C13 rows are left blank (their scores are the converter's, spec section 4).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import e3
from .main import BY_NAME, TRUNCATION_PAUSE, _item, check_main_set, window_check
from .pilot import HAIKU, Item, grader, load_set
from .request import build_params

ROOT = Path(__file__).resolve().parents[2]
TEAM_PROMPTS_PATH = ROOT / "research" / "models" / "team_prompts.py"
# D-100: the approved wording, research/models/team_prompts.py as on origin/main 71c6fd1 (Edith r1 CLEAN with R1-1 and R1-2).
# Any change to that file needs a new ruling; until then this module refuses to load a different file.
TEAM_PROMPTS_SHA256 = "14d122c73d3343d0344a20d83f779b2627b5397d1def6b8df923b5c35b4bb498"

# Tags (letters only, kscript.parse_custom_id). Distinct from every tag used so far: main.py (hm hl om ol sm sl ho hx hv, rt...),
# e3.py (es), slim.py's Study 1b plan (hh hxh oh ox oxh sh sx sxh). C13 is E3 itself, so it keeps E3's tag on the pieces items.
TAG_PLANNER = "tp"
TAG_HELPER = "th"
TAG_AGGREGATOR = "ta"
TAG_PICKER = "pk"
TAG_SAME_MODEL = "sc"
TAG_C13 = e3.SETUP_TAG
NEW_TAGS = (TAG_PLANNER, TAG_HELPER, TAG_AGGREGATOR, TAG_PICKER, TAG_SAME_MODEL)
GRADED_TAGS = (TAG_AGGREGATOR, TAG_SAME_MODEL)
PARTS = ("same_model", "h_pick8", "e2", "c13")
PICKER_SAMPLES = 8                       # team_prompts.picker_prompt takes exactly 8 replies (D-27 "picker over 8")
ROUND_KIND = "topup_round"
ROUND_DONE_KIND = "topup_round_done"     # written when a round's run_batches call returned with no stop (Edith code r1 T-R1)
NOTE = "top-up run (D-99, D-100): E2, H-pick8, C13 and the same-model check, in Batch rounds built from the call log"

PLAN_KEYS = {"study", "run_id_prefix", "draft", "spec", "notes", "set", "main_run", "model", "effort", "max_tokens", "voting", "parts",
             "same_model", "max_rounds", "window", "cap_proposed_usd", "booking_stand_ins", "to_confirm"}


class PlanError(ValueError):
    """The plan file breaks a rule; nothing is built or sent."""


class MainRunJoinError(RuntimeError):
    """A picker puzzle lacks a final main-run Haiku-medium record for one of its samples 1-8 (or one is of the wrong setup)."""


# ---------------------------------------------------------------- the approved prompts, imported by path

_TP = None


def team_prompts():
    """research/models/team_prompts.py, loaded by file path (it is not a package), after checking its SHA-256 against D-100's."""
    global _TP
    if _TP is None:
        got = hashlib.sha256(TEAM_PROMPTS_PATH.read_bytes()).hexdigest()
        if got != TEAM_PROMPTS_SHA256:
            raise RuntimeError(f"{TEAM_PROMPTS_PATH} has SHA-256 {got}, not the approved {TEAM_PROMPTS_SHA256} (D-100): a wording "
                               "change needs a new ruling")
        spec = importlib.util.spec_from_file_location("pareto_team_prompts_d100", TEAM_PROMPTS_PATH)
        mod = importlib.util.module_from_spec(spec)                                   # type: ignore[arg-type]
        spec.loader.exec_module(mod)                                                  # type: ignore[union-attr]
        _TP = mod
    return _TP


# ---------------------------------------------------------------- the plan file

def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _utc(x: object, what: str) -> datetime:
    if not isinstance(x, str):
        raise PlanError(f"{what} is an ISO date-time string with a UTC offset")
    try:
        t = datetime.fromisoformat(x)
    except ValueError:
        raise PlanError(f"{what}: {x!r} is not an ISO date-time")
    if t.tzinfo is None:
        raise PlanError(f"{what}: give the UTC offset (+00:00)")
    return t


def validate_plan(plan: Dict) -> Dict:
    """Check the plan file. The values the spec fixes are checked against the code that implements them, so a plan cannot drift from
    them silently: the model and effort (Haiku-medium), max_tokens (e3.E3_MAX_TOKENS, Amendment 1 section 3), the voting rule (E3's
    lead, cap and first-round draws), the picker's 8 samples, and the same-model check mirroring main.py's `hm`."""
    if not isinstance(plan, dict):
        raise PlanError("the plan is a JSON object")
    extra = set(plan) - PLAN_KEYS
    if extra:
        raise PlanError(f"unknown plan keys {sorted(extra)}")
    if not isinstance(plan.get("study"), str) or not plan["study"].strip():
        raise PlanError("the plan names its study")
    if not (isinstance(plan.get("run_id_prefix"), str) and plan["run_id_prefix"]):
        raise PlanError("run_id_prefix is a non-empty string")
    s = plan.get("set")
    if not (isinstance(s, dict) and set(s) <= {"set", "items_sha256", "steps", "note"} and isinstance(s.get("set"), str) and s["set"]):
        raise PlanError("set is {set, items_sha256, steps}")
    if not (isinstance(s.get("items_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", s["items_sha256"])):
        raise PlanError("set.items_sha256 is the manifest's 64-hex hash")
    if not (_is_int(s.get("steps")) and s["steps"] >= 1):
        raise PlanError("set.steps is a positive integer")
    mr = plan.get("main_run")
    if not (isinstance(mr, dict) and set(mr) <= {"run_id", "setup", "note"} and isinstance(mr.get("run_id"), str) and mr["run_id"]):
        raise PlanError("main_run is {run_id, setup}")
    if mr.get("setup") != "hm":
        raise PlanError("main_run.setup is \"hm\": the picker reads Haiku-medium samples (D-27) and the check mirrors hm (D-99)")
    if plan.get("model") != e3.E3_MODEL or plan.get("effort") != e3.E3_EFFORT:
        raise PlanError(f"every top-up call is {e3.E3_MODEL} at {e3.E3_EFFORT} (spec section 2)")
    if plan.get("max_tokens") != e3.E3_MAX_TOKENS:
        raise PlanError(f"max_tokens for every new call is {e3.E3_MAX_TOKENS} (Amendment 1 section 3; spec section 2)")
    v = plan.get("voting")
    if v != {"lead": e3.LEAD, "cap": e3.CAP, "first_round_draws": e3.FIRST_ROUND_DRAWS}:
        raise PlanError(f"voting is E3's rule exactly: {{lead {e3.LEAD}, cap {e3.CAP}, first_round_draws {e3.FIRST_ROUND_DRAWS}}} (D-100)")
    parts = plan.get("parts")
    if not (isinstance(parts, list) and parts and len(set(parts)) == len(parts) and set(parts) <= set(PARTS)):
        raise PlanError(f"parts is a non-empty list of distinct names from {PARTS}")
    sm = plan.get("same_model")
    if "same_model" in parts:
        if not (isinstance(sm, dict) and set(sm) <= {"bases", "tries", "mirrors", "note"}):
            raise PlanError("same_model is {bases, tries, mirrors}")
        if sm.get("mirrors") != "hm":
            raise PlanError("same_model.mirrors is \"hm\" (the main run's Haiku-medium settings exactly, D-99)")
        if not (_is_int(sm.get("bases")) and sm["bases"] >= 1) or not (_is_int(sm.get("tries")) and 1 <= sm["tries"] <= 99):
            raise PlanError("same_model.bases is a positive integer and tries is 1..99")
    if not (_is_int(plan.get("max_rounds")) and plan["max_rounds"] >= 1):
        raise PlanError("max_rounds is a positive integer")
    w = plan.get("window")
    if not (isinstance(w, dict) and set(w) <= {"hours", "not_before_utc", "latest_first_round_utc", "stop_and_report_utc", "note"}):
        raise PlanError("window is {hours, not_before_utc, latest_first_round_utc, stop_and_report_utc}")
    if not (_is_int(w.get("hours")) and w["hours"] >= 1):
        raise PlanError("window.hours is a positive integer")
    t0 = _utc(w.get("not_before_utc"), "window.not_before_utc")
    for k in ("latest_first_round_utc", "stop_and_report_utc"):
        if w.get(k) is not None and _utc(w[k], f"window.{k}") <= t0:
            raise PlanError(f"window.{k} is after not_before_utc")
    b = plan.get("booking_stand_ins")
    if not (isinstance(b, dict) and set(b) <= {"helper_task_chars", "picker_reply_chars", "note"}
            and _is_int(b.get("helper_task_chars")) and _is_int(b.get("picker_reply_chars"))):
        raise PlanError("booking_stand_ins is {helper_task_chars, picker_reply_chars} (integers; booking estimates only)")
    return plan


def read_plan(path: Path) -> Dict:
    return validate_plan(json.loads(Path(path).read_text()))


def plan_sha256(plan: Dict) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def set_path(plan: Dict, root: Path = ROOT) -> Path:
    p = Path(plan["set"]["set"])
    return p if p.is_absolute() else Path(root) / p


Loader = Callable[[Path], Tuple[Dict, List[Dict]]]


def load_topup_set(plan: Dict, loader: Optional[Loader] = None, root: Path = ROOT) -> Tuple[Dict, List[Dict]]:
    """The set, deep-verified by default (`pilot.load_set`), checked as main.check_main_set and against the plan's hash and steps."""
    man, items = (loader or load_set)(set_path(plan, root))
    if man.get("items_sha256") != plan["set"]["items_sha256"]:
        raise PlanError(f"{plan['set']['set']}: the manifest's items_sha256 is not the plan's")
    n = check_main_set(man, items)
    if n != plan["set"]["steps"]:
        raise PlanError(f"{plan['set']['set']}: the set has {n} steps, the plan says {plan['set']['steps']}")
    return man, items


def start_check(plan: Dict, now: datetime, first_round_sent: bool) -> None:
    """A live start is refused before not_before_utc (the main run's window must have closed, D-99), a first round after
    latest_first_round_utc, and any round after stop_and_report_utc (both set by Jarvis; checklist section 4)."""
    w = plan["window"]
    if now < _utc(w["not_before_utc"], "not_before_utc"):
        raise RuntimeError(f"the top-up run may not start before {w['not_before_utc']} (D-99: after the main run's window closes)")
    if not first_round_sent and w.get("latest_first_round_utc") and now > _utc(w["latest_first_round_utc"], "latest_first_round_utc"):
        raise RuntimeError(f"no first round after {w['latest_first_round_utc']}: stop and report (checklist section 4)")
    if w.get("stop_and_report_utc") and now > _utc(w["stop_and_report_utc"], "stop_and_report_utc"):
        raise RuntimeError(f"past the stop-and-report cutoff {w['stop_and_report_utc']}: nothing new is sent; report (checklist section 4)")


class RoundRefused(RuntimeError):
    """A round may not be sent: the run's 48-hour window has ended (main.window_check) or a plan date says stop (start_check)."""


def round_check(plan: Dict, out_dir: Path, now: Callable[[], datetime], first_round_sent: bool, check_dates: bool,
                extension_note: Optional[str]) -> None:
    """Before EVERY round (Edith code r1 T-R2): the run's own 48-hour window (`main.window_check`, from its first start, D-45 extensions
    as in the main run) and, when `check_dates`, the plan's dates (`start_check`: not before not_before_utc, no first round after
    latest_first_round_utc, nothing after stop_and_report_utc). Raises RoundRefused."""
    try:
        window_check(out_dir, now=now, hours=int(plan["window"]["hours"]), extension_note=extension_note)
        if check_dates:
            start_check(plan, now(), first_round_sent)
    except RuntimeError as e:
        raise RoundRefused(str(e)) from None


def round_lines(records: Sequence[Mapping[str, object]]) -> Tuple[int, Optional[int]]:
    """(rounds started, the index in `records` of the last round's `topup_round` line if that round has no `topup_round_done` line
    yet, else None). Rounds are counted from the log, so `max_rounds` holds across resumes."""
    started, last, done = 0, None, False
    for i, r in enumerate(records):
        if r.get("kind") == ROUND_KIND:
            started, last, done = started + 1, i, False
        elif r.get("kind") == ROUND_DONE_KIND:
            done = True
    return started, (last if last is not None and not done else None)


def unsettled_ids(records: Sequence[Mapping[str, object]]) -> set:
    """The custom ids of every submitted batch with no `batch_collected` line (a `batch_recollect` reopens one), as batch.py reads them."""
    submitted: Dict[str, Iterable[str]] = {}
    collected = set()
    for r in records:
        if r.get("kind") == "batch_submitted":
            submitted[str(r["batch_id"])] = list(r["keys"])                              # type: ignore[call-overload]
        elif r.get("kind") == "batch_collected":
            collected.add(str(r["batch_id"]))
        elif r.get("kind") == "batch_recollect":
            collected.discard(str(r["batch_id"]))
    return {cid for b, keys in submitted.items() if b not in collected for cid in keys}


def unchecked_batches(records: Sequence[Mapping[str, object]]) -> List[str]:
    """Collected batches with no `truncation_checked` / `paused_for_truncation` line (a crash between `batch_collected` and
    `batch.check_wave`), in log order (Edith code r1 T-R3)."""
    collected: List[str] = []
    checked = set()
    for r in records:
        if r.get("kind") == "batch_collected" and str(r.get("batch_id")) not in collected:
            collected.append(str(r["batch_id"]))
        elif r.get("kind") in ("truncation_checked", "paused_for_truncation"):
            checked.add(str(r.get("batch_id")))
    return [b for b in collected if b not in checked]


# ---------------------------------------------------------------- the puzzles

def _n_tasks(it: Mapping[str, object]) -> int:
    return int(it["depth"]) if int(it["width"]) == 1 else int(it["width"])            # type: ignore[call-overload]


def _lines(it: Mapping[str, object]) -> int:
    return int(it["params"]["lines"])                                                    # type: ignore[index]


def _is_chain(it: Mapping[str, object]) -> bool:
    return int(it["width"]) == 1 and int(it["depth"]) > 1                                # type: ignore[call-overload]


def _meta(man: Mapping[str, object], it: Mapping[str, object], tag: str, sample: int, role: str, **extra) -> Dict[str, object]:
    return {"set_id": man["set_id"], "item_id": it["id"], "family": man["family"], "setting": man["setting"],
            "base_index": it["base_index"], "width": it["width"], "depth": it["depth"], "setup": tag, "model": e3.E3_MODEL,
            "effort": e3.E3_EFFORT, "thinking_off": False, "sample": sample, "phase": "topup", "role": role, **extra}


def _request(man, it, tag: str, sample_label: str, sample: int, prompt: str, role: str, **extra) -> Item:
    cid = f"{it['id']}-{tag}-{sample_label}"
    from .client import check_custom_id
    check_custom_id(cid)
    params = build_params(e3.E3_MODEL, e3.E3_EFFORT, e3.E3_MAX_TOKENS, [{"role": "user", "content": prompt}])
    return cid, params, _meta(man, it, tag, sample, role, **extra)


def planner_item(man, it) -> Item:
    return _request(man, it, TAG_PLANNER, "01", 1, team_prompts().planner_prompt(it), "e2_planner")


def helper_item(man, it, k: int, d: int, task_text: str, balances: Sequence[int]) -> Item:
    return _request(man, it, TAG_HELPER, f"{k:02d}{d:02d}", k * 100 + d, team_prompts().helper_prompt(task_text, list(balances)),
                    "e2_helper", step=k, draw=d)


def aggregator_item(man, it, results: Sequence[Optional[Sequence[int]]]) -> Item:
    res = [None if r is None else list(r) for r in results]
    return _request(man, it, TAG_AGGREGATOR, "01", 1, team_prompts().aggregator_prompt(it, res), "e2_aggregator")


def picker_item(man, it, replies: Sequence[Optional[str]]) -> Item:
    return _request(man, it, TAG_PICKER, "01", 1, team_prompts().picker_prompt(it, list(replies)), "h_pick8")


def same_model_items(plan: Dict, man: Dict, items: List[Dict]) -> List[Item]:
    """Haiku-medium x tries on bases 0..bases-1, both shapes, built by main._item with main.BY_NAME["hm"] (identical params to the main
    run's hm calls), under TAG_SAME_MODEL. Meta marks it so it is never mixed into Study 1."""
    sm = plan["same_model"]
    su = BY_NAME[sm["mirrors"]]
    chosen = sorted((it for it in items if int(it["base_index"]) < int(sm["bases"])), key=lambda it: (it["base_index"], it["width"]))
    out = []
    for it in chosen:
        for k in range(1, int(sm["tries"]) + 1):
            cid, params, meta = _item(man, it, su, TAG_SAME_MODEL, k)
            out.append((cid, params, dict(meta, phase="topup", role="same_model_check", mirrors=sm["mirrors"])))
    return out


def c13_steps(man: Dict, items: List[Dict]) -> List[e3.Step]:
    """C13: every piece of every pieces puzzle (width N, depth 1) as one E3 step from its printed start, with the approved
    `ledger.step_call(p, s, 1)` for s = 1..N (Edith's note 1). Rebuilt from the seed exactly as e3.chain_steps does."""
    from ..analysis import scoring
    from ..analysis.curve import _puzzle
    from ..taskgen import ledger
    if man.get("family") != "ledger":
        raise ValueError(f"{man.get('set_id')}: C13 runs ledger sets only")
    out: List[e3.Step] = []
    for it in sorted((it for it in items if int(it["depth"]) == 1 and int(it["width"]) > 1), key=lambda it: int(it["base_index"])):
        p = _puzzle(it)
        if p.prompt != it["prompt"]:
            raise ValueError(f"{it['id']}: does not rebuild from its seed")
        for s in range(1, int(it["width"]) + 1):
            prompt, truth = ledger.step_call(p, s, 1)
            out.append(e3.Step(set_id=str(man["set_id"]), family=str(man["family"]), setting=str(man["setting"]), item_id=str(it["id"]),
                               base_index=int(it["base_index"]), width=int(it["width"]), depth=1, k=s, lines=int(p.params.lines),
                               prompt=prompt, truth=scoring.state_key(truth)))
    return out


# ---------------------------------------------------------------- the main run's Haiku-medium samples (H-pick8)

def main_sample_id(item_id: str, s: int, setup: str = "hm") -> str:
    return f"{item_id}-{setup}-{s:02d}"


def main_run_replies(main_dir: Path, items: Iterable[Mapping[str, object]], main_run_id: str, setup: str = "hm",
                     samples: int = PICKER_SAMPLES) -> Dict[str, List[Optional[str]]]:
    """{item_id: [visible text of samples 1..8, None where the sample did not answer]} from the main run's call log. Reads only the
    records of those custom ids. Every one must be FINAL, of `main_run_id`, Haiku-medium and of setup `setup`; otherwise
    MainRunJoinError lists what is missing (nothing is sent). Never prints any text."""
    want = {main_sample_id(str(it["id"]), s, setup): (str(it["id"]), s) for it in items for s in range(1, samples + 1)}
    got: Dict[str, Mapping[str, object]] = {}
    from .calllog import CallLog
    for r in CallLog(Path(main_dir) / "calls.jsonl").records():
        cid = r.get("custom_id")
        if not r.get("final") or cid not in want:
            continue
        if cid in got:
            raise MainRunJoinError(f"{cid}: two final records in the main run's log; a human must look")
        meta = r.get("meta") or {}
        if (r.get("run_id") != main_run_id or r.get("requested_model") != HAIKU or r.get("effort") != "medium"
                or meta.get("setup") != setup or int(meta.get("sample", -1)) != want[cid][1]):  # type: ignore[union-attr,call-overload]
            raise MainRunJoinError(f"{cid}: not a {main_run_id} Haiku-medium {setup} record of that sample")
        got[str(cid)] = r
    missing = sorted(set(want) - set(got))
    if missing:
        raise MainRunJoinError(f"{len(missing)} main-run samples 1-{samples} have no final record (first: {missing[:5]}); the picker "
                               "needs all 8 of every puzzle, so nothing is sent")
    out: Dict[str, List[Optional[str]]] = {}
    for cid, (item_id, s) in sorted(want.items(), key=lambda kv: (kv[1][0], kv[1][1])):
        r = got[cid]
        out.setdefault(item_id, []).append(str(r.get("answer_text") or "") if r.get("kind") == "answered" else None)
    return out


# ---------------------------------------------------------------- E2 state, rebuilt from the call log

def finals_by_id(records: Iterable[Mapping[str, object]]) -> Dict[str, Mapping[str, object]]:
    """{custom_id: final record} for the top-up's own tags. A top-up record of another model or effort raises."""
    out: Dict[str, Mapping[str, object]] = {}
    for r in records:
        if not r.get("final") or "custom_id" not in r:
            continue
        tag = str((r.get("meta") or {}).get("setup"))                                   # type: ignore[union-attr]
        if tag in NEW_TAGS + (TAG_C13,) and (r.get("requested_model") != e3.E3_MODEL or r.get("effort") != e3.E3_EFFORT):
            raise ValueError(f"{r.get('custom_id')}: a top-up record must be {e3.E3_MODEL} at {e3.E3_EFFORT}")
        out.setdefault(str(r["custom_id"]), r)
    return out


def _key_to_state(key: Optional[str]) -> Optional[List[int]]:
    return None if key is None else [int(x) for x in key.split(",")]


def e2_puzzle(man: Dict, it: Dict, finals: Mapping[str, Mapping[str, object]]) -> Dict[str, object]:
    """One puzzle's Haiku-team state from the final records, and its next requests. Pure.

    stage: "planner" (planner not final), "plan_failed", "helpers" (some task still drawing), "aggregator" (sent or to send), "done".
    tasks: per task {draws, decided, at_cap, answer (state key or None), state (list or None), status} where status is "open",
    "done" or "not_started" (a chain task after a task with no result, or not reached yet)."""
    tp = team_prompts()
    n, lines, chain = _n_tasks(it), _lines(it), _is_chain(it)
    out: Dict[str, object] = {"item_id": it["id"], "shape": f"{it['width']}x{it['depth']}", "tasks": [], "next": [], "plan": None}
    pl = finals.get(planner_item(man, it)[0])
    if pl is None:
        out.update(stage="planner", next=[planner_item(man, it)])
        return out
    plan = tp.parse_plan(str(pl.get("answer_text") or ""), n) if pl.get("kind") == "answered" else None
    if plan is None:
        out.update(stage="plan_failed")
        return out
    out["plan"] = plan
    tasks: List[Dict[str, object]] = []
    nxt: List[Item] = []
    broken = False
    for k in range(1, n + 1):
        if chain and k > 1 and (tasks[-1]["status"] != "done" or broken):
            tasks.append({"k": k, "status": "not_started", "draws": 0, "answer": None, "state": None})
            continue
        if chain:
            start = it["chains"][0]["start"] if k == 1 else tasks[-1]["state"]
        else:
            start = it["chains"][k - 1]["start"]
        logged = {d: finals[c] for d in range(1, e3.CAP + 1) for c in [helper_item_id(it, k, d)] if c in finals}
        recs = [logged[d] for d in sorted(logged)]
        st = e3.decide([e3.record_vote(r, lines) for r in recs])
        n_new = min(e3.FIRST_ROUND_DRAWS, e3.CAP) if not logged else int(st["more"])        # type: ignore[call-overload]
        free = [d for d in range(1, e3.CAP + 1) if d not in logged]
        nxt += [helper_item(man, it, k, d, plan[k - 1], start) for d in free[:n_new]]   # type: ignore[arg-type]
        done = bool(logged) and bool(st["done"])
        tasks.append({"k": k, "status": "done" if done else "open", "draws": len(logged), "decided": st["decided"],
                      "at_cap": st["at_cap"], "answer": st["answer"] if done else None,
                      "state": _key_to_state(st["answer"]) if done else None})              # type: ignore[arg-type]
        if chain and done and st["answer"] is None:
            broken = True                                                                 # "(no result)" from here onward
    out["tasks"] = tasks
    if nxt:
        out.update(stage="helpers", next=nxt)
        return out
    results = [t["state"] for t in tasks]
    agg = aggregator_item(man, it, results)                                               # type: ignore[arg-type]
    out["results"] = results
    if agg[0] in finals:
        out.update(stage="done", aggregator=finals[agg[0]])
    else:
        out.update(stage="aggregator", next=[agg])
    return out


def helper_item_id(it: Mapping[str, object], k: int, d: int) -> str:
    return f"{it['id']}-{TAG_HELPER}-{k:02d}{d:02d}"


# ---------------------------------------------------------------- rounds

class Context:
    """Everything a round is built from that is NOT the call log: the plan, the set, C13's steps and the picker's main-run text."""

    def __init__(self, plan: Dict, man: Dict, items: List[Dict], replies: Optional[Dict[str, List[Optional[str]]]] = None):
        self.plan, self.man, self.items = plan, man, items
        self.parts = tuple(plan["parts"])
        self.same_model = same_model_items(plan, man, items) if "same_model" in self.parts else []
        self.steps = c13_steps(man, items) if "c13" in self.parts else []
        if "h_pick8" in self.parts and replies is None:
            raise MainRunJoinError("the picker needs the main run's Haiku-medium samples: give --main-run")
        self.replies = replies or {}
        self.order = sorted(items, key=lambda it: (int(it["base_index"]), int(it["width"])))


def plan_round(ctx: Context, records: Iterable[Mapping[str, object]]) -> List[Item]:
    """The next round's requests, from the call log's final records only (pure; no calls, no files). Round 1 holds the same-model
    check, the pickers, the planners and C13's first draws; later rounds the helpers' next draws (both shapes together), C13's
    further draws and the aggregators that are ready. A request whose custom id is already final is never planned."""
    recs = list(records)
    finals = finals_by_id(recs)
    out: List[Item] = [r for r in ctx.same_model if r[0] not in finals]
    if "h_pick8" in ctx.parts:
        out += [picker_item(ctx.man, it, ctx.replies[it["id"]]) for it in ctx.order if f"{it['id']}-{TAG_PICKER}-01" not in finals]
    e2_next: List[Item] = []
    if "e2" in ctx.parts:
        for it in ctx.order:
            e2_next += e2_puzzle(ctx.man, it, finals)["next"]                            # type: ignore[operator]
    planners = [r for r in e2_next if r[2]["setup"] == TAG_PLANNER]
    out += planners
    if ctx.steps:
        out += e3.plan_round([], recs, ctx.steps)
    out += [r for r in e2_next if r[2]["setup"] != TAG_PLANNER]
    return out


def topup_status(ctx: Context, records: Iterable[Mapping[str, object]]) -> Dict[str, object]:
    """Counts only (no answer text): per part, what is final; E2 stages per shape; C13 through e3.e3_status."""
    recs = list(records)
    finals = finals_by_id(recs)
    out: Dict[str, object] = {}
    if ctx.same_model:
        out["same_model"] = {"calls": len(ctx.same_model), "final": sum(r[0] in finals for r in ctx.same_model)}
    if "h_pick8" in ctx.parts:
        out["h_pick8"] = {"puzzles": len(ctx.items), "final": sum(f"{it['id']}-{TAG_PICKER}-01" in finals for it in ctx.items)}
    if "e2" in ctx.parts:
        e2: Dict[str, Dict[str, int]] = {}
        for it in ctx.order:
            st = e2_puzzle(ctx.man, it, finals)
            row = e2.setdefault(str(st["shape"]), {"puzzles": 0, "planner": 0, "plan_failed": 0, "helpers": 0, "aggregator": 0, "done": 0,
                                                   "tasks_no_result": 0, "helper_draws": 0})
            row["puzzles"] += 1
            row[str(st["stage"])] += 1
            for t in st["tasks"]:                                                         # type: ignore[union-attr]
                row["helper_draws"] += int(t["draws"])
                row["tasks_no_result"] += int(t["status"] == "done" and t["answer"] is None)
        out["e2"] = e2
    if ctx.steps:
        out["c13"] = e3.e3_status(ctx.steps, recs)
    return out


def topup_grader(items_by_id: Dict[str, Dict]):
    """pilot.grader (the official D-76 score) for the aggregator and the same-model check only; blank for every other top-up call."""
    g = grader(items_by_id, "ledger")

    def grade(rec: Dict[str, object]) -> Optional[bool]:
        return g(rec) if (rec.get("meta") or {}).get("setup") in GRADED_TAGS else None   # type: ignore[union-attr]
    return grade


# ---------------------------------------------------------------- plan (no calls)

def _book(reqs: List[Item]) -> Decimal:
    from .slim import _book as book
    return book(reqs)


def topup_plan(guard, plan: Dict, man: Dict, items: List[Dict], replies: Optional[Dict[str, List[Optional[str]]]] = None) -> Dict[str, object]:
    """Calls and the guard's Batch worst-case booking per part: round 1 exactly as it would be sent; E2's helpers and C13 at the worst
    case (every task or step to the cap); the planners and aggregators once per puzzle. Where the prompt is not known before the run
    (a helper's task text, the picker's main-run replies when no --main-run is given) a stand-in of the plan's size is used."""
    from .pilot import plan as pilot_plan
    tp = team_prompts()
    b = plan["booking_stand_ins"]
    if replies is None and "h_pick8" in plan["parts"]:
        stand_in = ["x" * int(b["picker_reply_chars"])] * PICKER_SAMPLES
        reps, picker_basis = {it["id"]: stand_in for it in items}, f"stand-in: 8 replies of {b['picker_reply_chars']} characters each"
    else:
        reps, picker_basis = replies or {}, "the main run's samples 1-8"
    ctx = Context(plan, man, items, reps)
    first = plan_round(ctx, [])
    parts: Dict[str, Dict[str, object]] = {}

    def row(name: str, reqs: List[Item], calls: int, basis: str, **kw) -> None:
        parts[name] = {"calls": calls, "max_tokens": reqs[0][1]["max_tokens"] if reqs else None, "batch_booking_usd": str(_book(reqs)),
                       "basis": basis, **kw}
    sm = [r for r in first if r[2]["setup"] == TAG_SAME_MODEL]
    row("same_model", sm, len(sm), "exact (main._item with hm)", tries=(plan.get("same_model") or {}).get("tries"),
        bases=(plan.get("same_model") or {}).get("bases"))
    pk = [r for r in first if r[2]["setup"] == TAG_PICKER]
    row("h_pick8", pk, len(pk), picker_basis)
    if "e2" in plan["parts"]:
        pl = [r for r in first if r[2]["setup"] == TAG_PLANNER]
        row("e2_planner", pl, len(pl), "exact")
        task = "x" * int(b["helper_task_chars"])
        helpers = [helper_item(man, it, k, d, task, (it["chains"][0] if _is_chain(it) else it["chains"][k - 1])["start"])
                   for it in ctx.order for k in range(1, _n_tasks(it) + 1) for d in range(1, e3.CAP + 1)]
        row("e2_helpers_at_cap", helpers, len(helpers), f"every task to {e3.CAP} draws; task text stand-in of {b['helper_task_chars']} characters",
            per_shape={sh: sum(1 for r in helpers if f"{r[2]['width']}x{r[2]['depth']}" == sh) for sh in sorted({f"{it['width']}x{it['depth']}" for it in items})})
        agg = [aggregator_item(man, it, [list(s) for s in (it["chains"][0]["states"] if _is_chain(it) else [c["states"][0] for c in it["chains"]])])
               for it in ctx.order]
        row("e2_aggregator", agg, len(agg), "the true states as stand-in results (same size)")
    if ctx.steps:
        c1 = [r for r in first if r[2]["setup"] == TAG_C13]
        at_cap = [e3.step_item(s, d) for s in ctx.steps for d in range(1, e3.CAP + 1)]
        row("c13_at_cap", at_cap, len(at_cap), f"every piece to {e3.CAP} draws (through e3.step_item)", step_positions=len(ctx.steps),
            first_round_calls=len(c1), first_round_booking_usd=str(_book(c1)))
    total = sum((Decimal(p["batch_booking_usd"]) for p in parts.values()), Decimal(0))       # type: ignore[arg-type]
    p1 = pilot_plan(guard, first)
    by_part = {}
    for _, _, m in first:
        by_part[str(m.get("role") or m["setup"])] = by_part.get(str(m.get("role") or m["setup"]), 0) + 1
    return {"study": plan["study"], "draft": plan.get("draft"), "plan_sha256": plan_sha256(plan), "set_id": man["set_id"],
            "puzzles": len(items), "parts": parts,
            "total_calls_at_worst_case": sum(int(p["calls"]) for p in parts.values()),                    # type: ignore[call-overload]
            "total_batch_booking_at_worst_case_usd": str(total),
            "round_1": {"calls": len(first), "by_role": by_part, "batch_booking_usd": str(_book(first)),
                        "waves_if_nothing_were_spent_between": p1.get("waves_if_nothing_were_spent_between"),
                        **({"wave_error": p1["error"]} if "error" in p1 else {})},
            "cap_usd": str(guard.run_cap), "cap_proposed_usd": plan.get("cap_proposed_usd"), "max_rounds": plan["max_rounds"],
            "to_confirm": plan.get("to_confirm"),
            "booking_note": "the guard's worst case per call (prices.worst_case, Batch price): prompt at the dearest input rate plus "
                            "max_tokens at the output rate; booked round by round, never all at once; the bill is a fraction of this"}


# ---------------------------------------------------------------- the run

def _check_plan_copy(out_dir: Path, plan: Dict) -> None:
    path = out_dir / "topup_plan.json"
    text = json.dumps(plan, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text() != text:
            raise PlanError(f"{path} holds a different plan: a resumed run uses the plan it started with (a new plan needs a new run id)")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run_topup(guard, transport, out_dir: Path, plan: Dict, main_run_dir: Optional[Path], poll_s: float = 60.0, sleep=None,
              pause_truncated_over: Optional[float] = TRUNCATION_PAUSE, release_pause_note: Optional[str] = None,
              waive_pause_note: Optional[str] = None, max_wave_size: Optional[int] = None, loader=None,
              now: Optional[Callable[[], datetime]] = None, extension_note: Optional[str] = None,
              max_rounds: Optional[int] = None, check_dates: Optional[bool] = None) -> Dict[str, object]:
    """Round after round through `batch.run_batches` until nothing is left, a stop, or max_rounds. Stops early (like e3.run_e3) for the
    Console check, a truncation pause, a halted guard, or missing results; and before any round past the run's 48-hour window or (when
    `check_dates`, by default a live run) a plan date (`round_check`, Edith code r1 T-R2): "refused", with the reason in `refused`.
    The compact table is written whatever happens.

    Resume (Edith code r1 T-R1): a round is marked done (`topup_round_done`) only when its `run_batches` call returned with no stop. A
    round with no done line (a crash, a stop) is RESUMED, never re-planned from the current log: its requests are rebuilt from the
    log as it stood at its `topup_round` line, so an unsettled batch settles with exactly the items it was sent with (batch.py's
    "settled before a crash" path writes any result committed but not yet logged), and the round's unsent waves go out. Only then is
    the next round planned. Before each round, any collected batch with no truncation-check line is checked (`batch.check_wave`,
    Edith code r1 T-R3). Rounds are counted from the log's `topup_round` lines, so `max_rounds` holds across resumes.

    Returns {"rounds" (run in this call, a resumed one included), "rounds_logged", "calls_sent", "stopped", "summaries", "status",
    "table_cost_usd", "block_rates"}."""
    from .batch import PausedForTruncation, check_wave, pause_state, pause_waived, release_pause, run_batches, waive_pause
    from .calllog import CallLog
    from .manifest import write_manifest
    from .table import block_rates, write_compact_table
    validate_plan(plan)
    out_dir = Path(out_dir)
    clock: Callable[[], datetime] = now or (lambda: datetime.now(timezone.utc))
    dates = bool(transport.live) if check_dates is None else bool(check_dates)
    man, items = load_topup_set(plan, loader)
    replies = (main_run_replies(main_run_dir, items, plan["main_run"]["run_id"], plan["main_run"]["setup"])   # type: ignore[arg-type]
               if "h_pick8" in plan["parts"] and main_run_dir is not None else None)
    ctx = Context(plan, man, items, replies)                                              # raises if the picker has no main run
    # only now (everything needed is in hand) may the run's own 48-hour window start. Later starts check it before each round
    # (round_check), so a batch sent before a crash is still collected past the window while nothing new goes out.
    if not (out_dir / "window.json").exists():
        window_check(out_dir, now=clock, hours=int(plan["window"]["hours"]), extension_note=extension_note)
    _check_plan_copy(out_dir, plan)
    log = CallLog(out_dir / "calls.jsonl")
    if waive_pause_note is not None:
        waive_pause(log, guard.run_id, waive_pause_note)
    if release_pause_note:
        if pause_state(log) is None:
            raise RuntimeError("--release-pause was given but the run is not paused")
        release_pause(log, guard.run_id, release_pause_note)
    if pause_truncated_over is not None and not pause_waived(log) and pause_state(log) is not None:
        p = pause_state(log)
        raise PausedForTruncation(f"the run paused after batch {p.get('batch_id')}: truncated shares {p.get('shares')}; report it, and "  # type: ignore[union-attr]
                                  "only on the user's ruling release it (topup.py --release-pause NOTE)")
    if not (out_dir / "manifest.json").exists():
        write_manifest(out_dir, guard, plan_round(ctx, log.records()), "batch" if transport.live else "dry",
                       note=f"{NOTE}; plan {plan_sha256(plan)}; the item set listed is round 1 only (later rounds are built from the log)")
    kw = {"sleep": sleep} if sleep is not None else {}
    grade = topup_grader({it["id"]: it for it in items})
    limit = max_rounds if max_rounds is not None else int(plan["max_rounds"])
    result: Dict[str, object] = {"rounds": 0, "rounds_logged": 0, "calls_sent": 0, "stopped": None, "summaries": []}

    def batches(reqs: List[Item]):
        s = run_batches(guard, transport, log, reqs, poll_s=poll_s, max_wave_size=max_wave_size,
                        pause_truncated_over=pause_truncated_over, **kw)
        result["summaries"].append(s)                                                     # type: ignore[union-attr]
        result["calls_sent"] += s.answered + s.failed + len(s.unbilled_assumed) + len(s.missing)   # type: ignore[operator]
        return s
    try:
        while True:
            # T-R3: a batch collected just before a crash, with no truncation-check line, is checked before anything else
            if pause_truncated_over is not None and not pause_waived(log):
                for bid in unchecked_batches(list(log.records())):
                    over = check_wave(log, guard.run_id, bid, pause_truncated_over)
                    if over:
                        result.update(stopped="paused_for_truncation", paused=over)
                        break
                if result["stopped"]:
                    break
            recs = list(log.records())
            started, open_at = round_lines(recs)
            pending = unsettled_ids(recs)
            if open_at is not None:
                # T-R1: resume the open round with the items it was planned with (the log as it stood at its topup_round line)
                reqs, resumed = plan_round(ctx, recs[:open_at]), True
                stray = pending - {r[0] for r in reqs}
                if stray:
                    raise RuntimeError(f"unsettled batches hold {len(stray)} ids that round {started} never planned (first: "
                                       f"{sorted(stray)[:3]}); a human must look")
            else:
                if pending:
                    raise RuntimeError(f"unsettled batches hold {len(pending)} ids outside any open round; a human must look")
                if started >= limit:
                    break
                reqs, resumed = plan_round(ctx, recs), False
                if not reqs:
                    break
            try:
                round_check(plan, out_dir, clock, started > 0, dates, extension_note)
            except RoundRefused as e:
                result.update(stopped="refused", refused=str(e))
                if pending:                       # collect what was already sent (a read, never a re-send); nothing new goes out
                    batches([r for r in reqs if r[0] in pending])
                break
            if not resumed:
                log.write({"kind": ROUND_KIND, "run_id": guard.run_id, "round": started + 1, "calls": len(reqs),
                           "by_tag": dict(Counter(str(m["setup"]) for _, _, m in reqs)), "final": False})
            result["rounds"] += 1                                                         # type: ignore[operator]
            s = batches(reqs)
            if s.paused_for_truncation:
                result["stopped"] = "paused_for_truncation"
            elif s.stopped_for_console_check:
                result["stopped"] = "console_check"
            elif getattr(guard, "halted", False):
                result["stopped"] = "halted"
            elif s.missing:
                result["stopped"] = "missing_results"
            if result["stopped"]:
                break
            log.write({"kind": ROUND_DONE_KIND, "run_id": guard.run_id, "round": started if resumed else started + 1, "final": False})
        if result["stopped"] is None and plan_round(ctx, log.records()):
            result["stopped"] = "max_rounds"
        result["status"] = topup_status(ctx, log.records())
        return result
    finally:
        result["rounds_logged"] = round_lines(list(log.records()))[0]
        result["table_cost_usd"] = str(write_compact_table(log, out_dir / "compact_table.csv", grade=grade))
        result["block_rates"] = block_rates(log)


def _brief(r: Dict[str, object]) -> Dict[str, object]:
    return {k: r.get(k) for k in ("rounds", "rounds_logged", "calls_sent", "stopped", "refused", "status", "table_cost_usd")}


def _refused(e: Exception) -> int:
    """A refusal is a clean message and exit code 2, never a traceback (Edith code r1 nit)."""
    print(f"REFUSED: {e}")
    return 2


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--run-id", default="topup-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required for live (no default)")
    ap.add_argument("--clearance", type=Path)
    ap.add_argument("--main-run", type=Path, help="the main run's folder (its calls.jsonl): the picker's samples 1-8")
    ap.add_argument("--extend-window", help="D-45: a recorded note that extends the 48-hour window (needs the user's say)")
    ap.add_argument("--release-pause", help="after a truncation pause: a recorded note of the user's ruling to go on")
    ap.add_argument("--truncation-pause-off", help="the user's ruling to run without the 2%% truncation pause (a recorded note)")
    a = ap.parse_args(argv)
    from .batch import PausedForTruncation
    from .guard import SpendGuard
    from .transport import DryTransport
    try:
        plan = read_plan(a.plan)
        if a.mode == "live" and not a.run_id.startswith(plan["run_id_prefix"]):
            raise PlanError(f"the run id must start with {plan['run_id_prefix']!r}")
        man, items = load_topup_set(plan)                    # verified once, then reused by the run
    except (ValueError, OSError) as e:
        ap.error(str(e))

    def loader(_: Path) -> Tuple[Dict, List[Dict]]:
        return man, items
    if a.mode in ("plan", "dry"):
        guard = SpendGuard(a.run_id, Decimal(a.cap or str(plan.get("cap_proposed_usd") or "25")), global_spent_usd=Decimal("0"))
        if a.mode == "dry" and (a.out is None or (a.main_run is None and "h_pick8" in plan["parts"])):
            ap.error("dry needs --out and (for the picker) --main-run")
        try:
            replies = (main_run_replies(a.main_run, items, plan["main_run"]["run_id"], plan["main_run"]["setup"])
                       if a.main_run is not None and "h_pick8" in plan["parts"] else None)
        except MainRunJoinError as e:
            return _refused(e)                               # Edith's ruling 1: a missing sample refuses the run before any call
        print(json.dumps(topup_plan(guard, plan, man, items, replies), indent=1, default=str))
        if a.mode == "dry":
            try:
                r = run_topup(guard, DryTransport(), a.out, plan, a.main_run, sleep=lambda s: None, loader=loader)
            except (MainRunJoinError, RoundRefused, PlanError) as e:
                return _refused(e)
            print("dry run done:", json.dumps(_brief(r), indent=1, default=str))
            if r["stopped"] == "refused":
                return _refused(r["refused"])                                             # type: ignore[arg-type]
        return 0
    if a.cap is None or a.clearance is None:
        ap.error("live needs an explicit --cap and --clearance")
    if a.out is not None:
        ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/); do not give --out")
    if plan.get("draft"):
        ap.error("the plan is a draft; a live run needs the final, locked plan")
    from .live import open_live_guard, run_folder
    from .transport import RealTransport, TransportError
    main_dir = a.main_run if a.main_run is not None else run_folder(plan["main_run"]["run_id"])
    if "h_pick8" in plan["parts"]:
        try:                                                 # Edith's ruling 1, checked before the live guard is even opened
            main_run_replies(main_dir, items, plan["main_run"]["run_id"], plan["main_run"]["setup"])
        except (MainRunJoinError, OSError) as e:
            return _refused(e)
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        from .calllog import CallLog
        sent_before = any(r.get("kind") == ROUND_KIND for r in CallLog(folder / "calls.jsonl").records())
        try:
            start_check(plan, datetime.now(timezone.utc), sent_before)
        except RuntimeError as e:
            return _refused(e)
        transport = RealTransport(guard)
        try:
            r = run_topup(guard, transport, folder, plan, main_dir, loader=loader, extension_note=a.extend_window,
                          release_pause_note=a.release_pause, waive_pause_note=a.truncation_pause_off)
        except (MainRunJoinError, RoundRefused, PlanError) as e:
            return _refused(e)
        print("live run done:", json.dumps(_brief(r), indent=1, default=str))
        if r["stopped"] == "refused":
            return _refused(f"{r['refused']} (anything already sent was collected; nothing new went out; report)")
        if r["stopped"] == "paused_for_truncation":
            print("PAUSED for truncation (a tag over 2% of a batch at max_tokens): report the shares to Edith and the user; run the same "
                  "command with --release-pause '<the user's ruling>' only after they rule (no limit changes by itself)")
        elif r["stopped"] == "console_check":
            print("STOPPED for the Console check: read what the Console shows for this run, then run "
                  "`python3 -m harness.pareto.pilot console-check --run-id ... --cap ... --clearance ... --usd <dollars> --note <where from>` "
                  "and run the same topup command again")
        elif r["stopped"]:
            print(f"STOPPED ({r['stopped']}): see the runbook (harness/pareto/README.md, main run section 3); then the same command again")
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
