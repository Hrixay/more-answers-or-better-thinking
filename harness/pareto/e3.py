"""E3, the scripted "perfect decomposition" arm (spec: "E3 detail", "The step-wise team's prompt (E3)", "E3 and the step-line view
(D-68 F7)"): every step of every 1xN chain is sent ALONE to Haiku-medium, from the CORRECT input (the key's state before that step),
with the approved step prompt `ledger.step_call(p, 1, k)`. Because every input is correct, the steps do not depend on each other, so
all steps of all chains go into the same Batch round.

Voting, per step: "lead-by-2, cap 9". Draws are made in rounds (FIRST_ROUND_DRAWS for a step with none yet; then as many as could
still reach the lead) until one answer's count exceeds every other answer's count by at least LEAD, or CAP draws are made. A reply
that did not answer, or whose Answer line does not read as a state (`trace_parse.parse_final`), is a vote for nothing: it uses up a
draw and counts for no answer. The voted answer is right or wrong against the key's state after the step.

Rows for test 4 (`e3_rows`): one row per base puzzle's chain, `setup` "e3", `shape` "1xN", `step_correct` (one boolean per step),
`cost_usd` (every step call of the chain, failures included). `five_tests.e3_arm_scores` scores it as the product of the per-step
accuracies (F7).

Custom ids are `<full item id>-es-<KK><DD>` (step K, draw D, two digits each). The analysis parser (`kscript.parse_custom_id`) reads
the setup tag "es" and the sample KK*100+DD. The setup tag is letters only because the parser requires that.

Nothing here reads `.env` or builds a real transport: `run_e3` takes the guard and the transport it is given (as pilot.run_pilot
does). Re-runs resume: a draw already logged as final is never planned again, and `batch.run_batches` skips finished custom ids.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..analysis import scoring, trace_parse
from ..analysis.curve import _puzzle
from ..taskgen import ledger
from .batch import run_batches
from .calllog import CallLog
from .client import check_custom_id
from .pilot import HAIKU, Item, load_set
from .request import build_params

E3_MODEL = HAIKU
E3_EFFORT = "medium"
# Amendment 1: every setup the ladder did not measure keeps the locked pilot limit (limits.pilot_max_tokens("ledger", Haiku) = 48,000).
# E3 step calls were not measured by the ladder, so they keep it. Thinking is adaptive (build_params' default).
E3_MAX_TOKENS = 48_000
SETUP_TAG = "es"            # letters only: kscript.parse_custom_id requires it
LEAD = 2
CAP = 9
FIRST_ROUND_DRAWS = 2

Sets = Sequence[Tuple[Mapping[str, object], Sequence[Mapping[str, object]]]]     # [(manifest, items), ...]


@dataclass(frozen=True)
class Step:
    """One step of one 1xN chain: the prompt sent for it and the key's state after it (`truth`, a state_key)."""
    set_id: str
    family: str
    setting: str
    item_id: str
    base_index: int
    width: int
    depth: int
    k: int
    lines: int
    prompt: str
    truth: str


def chain_steps(sets: Sets) -> List[Step]:
    """Every step of every 1xN chain (width 1, depth > 1) of the given ledger sets, in set, base and step order. Each puzzle is rebuilt
    from its stored item exactly as the curve does (`curve._puzzle`, which raises if the rebuilt prompt differs from the stored one)."""
    out: List[Step] = []
    for man, items in sets:
        if man.get("family") != "ledger":
            raise ValueError(f"{man.get('set_id')}: E3 runs ledger sets only, not {man.get('family')!r}")
        chains = sorted((it for it in items if int(it["width"]) == 1 and int(it["depth"]) > 1), key=lambda it: int(it["base_index"]))
        for it in chains:
            p = _puzzle(it)
            if p.prompt != it["prompt"]:                       # _puzzle checks this too; kept here so the rule is visible
                raise ValueError(f"{it['id']}: does not rebuild from its seed")
            for k in range(1, int(it["depth"]) + 1):
                prompt, truth = ledger.step_call(p, 1, k)
                out.append(Step(set_id=str(man["set_id"]), family=str(man["family"]), setting=str(man["setting"]), item_id=str(it["id"]),
                                base_index=int(it["base_index"]), width=int(it["width"]), depth=int(it["depth"]), k=k,
                                lines=int(p.params.lines), prompt=prompt, truth=scoring.state_key(truth)))
    return out


def custom_id(item_id: str, k: int, d: int) -> str:
    return f"{item_id}-{SETUP_TAG}-{k:02d}{d:02d}"


def step_item(step: Step, d: int) -> Item:
    """The Batch request for draw `d` of `step`."""
    cid = custom_id(step.item_id, step.k, d)
    check_custom_id(cid)
    params = build_params(E3_MODEL, E3_EFFORT, E3_MAX_TOKENS, [{"role": "user", "content": step.prompt}])
    meta = {"set_id": step.set_id, "item_id": step.item_id, "family": step.family, "setting": step.setting,
            "base_index": step.base_index, "width": step.width, "depth": step.depth, "setup": SETUP_TAG, "model": E3_MODEL,
            "effort": E3_EFFORT, "sample": step.k * 100 + d, "step": step.k, "draw": d}
    return (cid, params, meta)


# ---------------------------------------------------------------- reading and voting

def parse_step_answer(reply_text: Optional[str], line_count: int) -> Optional[str]:
    """The state a step reply votes for (`scoring.state_key`), or None when its Answer line does not read as a state."""
    status, state = trace_parse.parse_final(str(reply_text or ""), line_count)
    return scoring.state_key(state) if status == "ok" and state is not None else None


def record_vote(rec: Mapping[str, object], line_count: int) -> Optional[str]:
    """What one logged draw votes for: None unless the call answered and its Answer line reads."""
    if rec.get("kind") != "answered":
        return None
    return parse_step_answer(rec.get("answer_text"), line_count)  # type: ignore[arg-type]


def decide(answers: Sequence[Optional[str]], lead: int = LEAD, cap: int = CAP) -> Dict[str, object]:
    """The lead-by-`lead` vote over one step's draws so far (None = a vote for nothing: it uses a draw and counts for no answer).

    - decided: the top answer's count minus the second's (0 if there is no second) is at least `lead`; `answer` is the top answer.
    - at_cap: `cap` draws made without that lead. Then `answer` is the unique plurality answer if there is one, otherwise None (no
      answer, so the step is wrong).
      NOTE: this at-cap rule is OUR CHOICE where the spec is silent ("lead-by-2 voting (cap 9)" says nothing about reaching the cap
      without a lead). EDITH MUST CONFIRM it before the E3 rows are used in test 4.
    - more: how many further draws to request now: 0 when decided or at the cap; otherwise the fewest that could still reach the lead,
      `lead - (top - second)`, at least 1 and never past the cap.
    - done: decided or at_cap (no more draws for this step).
    """
    draws = len(answers)
    ranked = Counter(a for a in answers if a is not None).most_common()
    top = ranked[0][1] if ranked else 0
    second = ranked[1][1] if len(ranked) > 1 else 0
    out: Dict[str, object] = {"decided": False, "at_cap": False, "done": False, "answer": None, "draws": draws, "more": 0,
                              "top": top, "second": second}
    if ranked and top - second >= lead:
        out.update(decided=True, done=True, answer=ranked[0][0])
    elif draws >= cap:
        unique_plurality = bool(ranked) and top > second       # second is 0 when there is one answer
        out.update(at_cap=True, done=True, answer=ranked[0][0] if unique_plurality else None)
    else:
        out["more"] = min(max(1, lead - (top - second)), cap - draws)
    return out


def draws_by_step(records: Iterable[Mapping[str, object]]) -> Dict[Tuple[str, int], Dict[int, Mapping[str, object]]]:
    """{(item_id, k): {draw: record}} for the FINAL E3 records of a call log (meta setup "es"). An errored, expired or canceled batch item
    is not final: it is not a draw (not billed) and is planned again. A record of another model or effort raises."""
    out: Dict[Tuple[str, int], Dict[int, Mapping[str, object]]] = {}
    for r in records:
        meta = r.get("meta") or {}
        if not r.get("final") or meta.get("setup") != SETUP_TAG:  # type: ignore[union-attr]
            continue
        if r.get("requested_model") != E3_MODEL or r.get("effort") != E3_EFFORT:
            raise ValueError(f"{r.get('custom_id')}: an E3 record must be {E3_MODEL} at {E3_EFFORT}, not {r.get('requested_model')} / {r.get('effort')}")
        key = (str(meta["item_id"]), int(meta["step"]))      # type: ignore[index]
        out.setdefault(key, {}).setdefault(int(meta["draw"]), r)  # type: ignore[index]
    return out


def step_state(step: Step, draws: Mapping[int, Mapping[str, object]]) -> Dict[str, object]:
    """`decide` over a step's logged draws (in draw order), plus the draw records."""
    recs = [draws[d] for d in sorted(draws)]
    st = decide([record_vote(r, step.lines) for r in recs])
    st["records"] = recs
    return st


def plan_round(sets: Sets, records: Iterable[Mapping[str, object]], steps: Optional[Sequence[Step]] = None) -> List[Item]:
    """The next round's requests: FIRST_ROUND_DRAWS for a step with no draws, `decide(...)["more"]` for an open step, nothing for a
    done one. New draws take the smallest draw numbers (1..CAP) not yet logged as final, so a draw that errored is sent again under its
    own custom id (run_batches gives it a new guard key) and a logged draw is never planned again. Pure: no calls, no files."""
    steps = list(steps) if steps is not None else chain_steps(sets)
    have = draws_by_step(records)
    out: List[Item] = []
    for step in steps:
        logged = have.get((step.item_id, step.k), {})
        n = min(FIRST_ROUND_DRAWS, CAP) if not logged else int(step_state(step, logged)["more"])  # type: ignore[arg-type]
        free = [d for d in range(1, CAP + 1) if d not in logged]
        out += [step_item(step, d) for d in free[:n]]
    return out


def e3_status(steps: Sequence[Step], records: Iterable[Mapping[str, object]]) -> Dict[str, int]:
    """Counts over the steps: decided, at_cap, open (still drawing), and the final E3 draws logged."""
    have = draws_by_step(records)
    out = {"steps": len(steps), "decided": 0, "at_cap": 0, "open": 0, "draws_logged": sum(len(v) for v in have.values())}
    for step in steps:
        logged = have.get((step.item_id, step.k), {})
        st = step_state(step, logged) if logged else {"decided": False, "at_cap": False}
        out["decided" if st["decided"] else "at_cap" if st["at_cap"] else "open"] += 1
    return out


# ---------------------------------------------------------------- running

def run_e3(guard, transport, out_dir: Path, set_dirs: Sequence[Path], poll_s: float = 60.0, sleep=None, max_rounds: int = CAP,
           loader: Optional[Callable[[Path], Tuple[Dict, List[Dict]]]] = None, max_wave_size: Optional[int] = None,
           pause_truncated_over: Optional[float] = None) -> Dict[str, object]:
    """Round after round through `batch.run_batches` (same guard, same rules, same call log `out_dir/calls.jsonl` as the main runner;
    the custom ids do not clash) until every step is decided or at the cap, or `max_rounds` rounds have run. Stops early when a round
    stops for the Console check, when the guard has halted, or when a round left results missing (their reservations stay open, so
    a further round would refuse them anyway). `loader` is `pilot.load_set` (verified) unless a test passes another."""
    loader = loader or load_set
    log = CallLog(Path(out_dir) / "calls.jsonl")
    sets = [loader(d) for d in set_dirs]
    steps = chain_steps(sets)
    kw = {"sleep": sleep} if sleep is not None else {}
    rounds, sent, stopped = 0, 0, None
    summaries = []
    while rounds < max_rounds:
        items = plan_round(sets, log.records(), steps)
        if not items:
            break
        rounds += 1
        s = run_batches(guard, transport, log, items, poll_s=poll_s, max_wave_size=max_wave_size,
                        pause_truncated_over=pause_truncated_over, **kw)
        summaries.append(s)
        sent += s.answered + s.failed + len(s.unbilled_assumed) + len(s.missing)
        if s.paused_for_truncation:
            stopped = "paused_for_truncation"
        elif s.stopped_for_console_check:
            stopped = "console_check"
        elif getattr(guard, "halted", False):
            stopped = "halted"
        elif s.missing:
            stopped = "missing_results"
        if stopped:
            break
    if stopped is None and plan_round(sets, log.records(), steps):
        stopped = "max_rounds"
    status = e3_status(steps, log.records())
    return {"rounds": rounds, "calls_sent": sent, "stopped": stopped, "summaries": summaries, **status}


# ---------------------------------------------------------------- rows for test 4

def _no_answer_kind(recs: Sequence[Mapping[str, object]], line_count: int) -> Tuple[str, Optional[str]]:
    """Why a finished step has no voted answer: "answered" when some draw gave a readable answer (a tie at the cap: a real, wrong vote);
    otherwise the first draw's kind that is not "answered" (refusal, truncated, ...) with its stop reason; otherwise "unparseable"."""
    if any(record_vote(r, line_count) is not None for r in recs):
        return "answered", None
    for r in recs:
        if r.get("kind") != "answered":
            return str(r.get("kind")), r.get("stop_reason")  # type: ignore[return-value]
    return "unparseable", None


def e3_rows(sets: Sets, records: Iterable[Mapping[str, object]], steps: Optional[Sequence[Step]] = None) -> List[Dict[str, object]]:
    """One row per base puzzle's chain whose steps are ALL done (decided or at the cap); a chain with an open step is left out.
    `kind` is "answered" unless a step has no voted answer for a reason other than a tie (then the first such step's reason:
    `_no_answer_kind`), with that draw's `stop_reason`, so the refusals-out and truncations-out views (scoring._dropped) can act on it.
    `correct` is every step right (the product estimator reads `step_correct`)."""
    steps = list(steps) if steps is not None else chain_steps(sets)
    have = draws_by_step(list(records))
    chains: Dict[str, List[Step]] = {}
    for st in steps:
        chains.setdefault(st.item_id, []).append(st)
    rows: List[Dict[str, object]] = []
    for item_id, ch in chains.items():
        ch = sorted(ch, key=lambda s: s.k)
        states = [step_state(s, have[(item_id, s.k)]) if (item_id, s.k) in have else None for s in ch]
        if any(st is None or not st["done"] for st in states):
            continue
        kind, stop = "answered", "end_turn"
        cost, calls, at_cap = Decimal("0"), 0, 0
        correct: List[bool] = []
        for s, st in zip(ch, states):
            recs = st["records"]                                                   # type: ignore[index]
            calls += len(recs)
            cost += sum((Decimal(str(r.get("cost_usd"))) for r in recs if r.get("cost_usd") not in (None, "")), Decimal("0"))
            at_cap += bool(st["at_cap"])                                           # type: ignore[index]
            correct.append(st["answer"] is not None and st["answer"] == s.truth)  # type: ignore[index]
            if st["answer"] is None and kind == "answered":                        # type: ignore[index]
                why, why_stop = _no_answer_kind(recs, s.lines)                    # type: ignore[arg-type]
                if why != "answered":
                    kind, stop = why, why_stop
        first = ch[0]
        rows.append({"base_id": f"{first.set_id}-{first.base_index:03d}", "set_id": first.set_id, "item_id": item_id,
                     "shape": scoring.chain_shape(first.depth), "setup": "e3", "kind": kind, "stop_reason": stop,
                     "step_correct": correct, "correct": all(correct), "cost_usd": str(cost), "calls": calls, "at_cap_steps": at_cap})
    return rows
