"""The pilot (D-36): turn frozen task sets into requests, plan them against the cap, run them, grade them.

    python3 -m harness.pareto.pilot plan --sets SET_DIR [SET_DIR ...]
    python3 -m harness.pareto.pilot dry  --sets SET_DIR [...] --run-id ID --out DIR     # whole flow, no network
    python3 -m harness.pareto.pilot live --sets SET_DIR [...] --run-id ID --cap 30 --clearance FILE [--rt-set SET_DIR]
    python3 -m harness.pareto.pilot console-clear --run-id ID --cap 30 --clearance FILE --note 'what was found'   (after a FAILED check)
    python3 -m harness.pareto.pilot console-check --run-id ID --cap 30 --clearance FILE --usd 1.23 --note 'Console, Usage page, 12:05'

`plan` and `dry` never touch the network and never read `.env`. `live` builds a live guard (it refuses without Edith's
clearance file and the user's go, see guard.py) and the real transport, and only then reads the key.

Setups (D-36 point 2, per Jarvis and Karen's pricing): digits: Haiku-medium x10, Sonnet-medium x1, Opus-medium x1 per
puzzle; code: Haiku-medium x10, Opus-medium x1 (no Sonnet in code, D-35). All through Batch. max_tokens come from
limits.py. The 10-puzzle real-time check is a separate step.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .batch import run_batches
from .calllog import CallLog
from .client import check_custom_id
from .limits import pilot_max_tokens
from .manifest import write_manifest
from .prices import estimate_input_tokens
from .request import build_params, prompt_text
from .table import block_rates, write_compact_table

HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"


@dataclass(frozen=True)
class Setup:
    name: str          # short, goes into the custom_id
    model: str
    effort: str
    n: int             # samples per puzzle


SETUPS = {
    "digits": (Setup("hm", HAIKU, "medium", 10), Setup("sm", SONNET, "medium", 1), Setup("om", OPUS, "medium", 1)),
    "code": (Setup("hm", HAIKU, "medium", 10), Setup("om", OPUS, "medium", 1)),
    "ledger": (Setup("hm", HAIKU, "medium", 10), Setup("sm", SONNET, "medium", 1), Setup("om", OPUS, "medium", 1)),
}

Item = Tuple[str, Dict[str, object], Dict[str, object]]

# The 10-puzzle real-time check (D-35, D-36): latency, plus batch-vs-real-time equivalence. Opus-medium, Sonnet-medium and
# Haiku-medium x5, in REAL TIME (list price), on 10 puzzles of one pilot set (digits, or the ledger: slot A's l16 set, research/pilot-plan-ledger.md). The same puzzles and setups already run
# in the pilot's Batch (Haiku x10, Sonnet x1, Opus x1), so those are the batched side of the comparison.
RT_SETUPS = (Setup("hm", HAIKU, "medium", 5), Setup("sm", SONNET, "medium", 1), Setup("om", OPUS, "medium", 1))
RT_PUZZLES = 10


def load_set(folder: Path) -> Tuple[Dict, List[Dict]]:
    """A frozen set, verified (file hash, seeds, every prompt re-solved from its text) before any request is built."""
    from ..taskgen.freeze import verify_set
    folder = Path(folder)
    man = verify_set(folder)
    items = [json.loads(ln) for ln in (folder / "items.jsonl").read_text().splitlines()]
    return man, items


def build_requests(man: Dict, items: List[Dict], setups: Optional[Tuple[Setup, ...]] = None) -> List[Item]:
    family = man["family"]
    setups = setups if setups is not None else SETUPS[family]
    out: List[Item] = []
    for it in items:
        for su in setups:
            params = build_params(su.model, su.effort, pilot_max_tokens(family, su.model),
                                  [{"role": "user", "content": it["prompt"]}])
            for k in range(1, su.n + 1):
                cid = f"{it['id']}-{su.name}-{k:02d}"
                check_custom_id(cid)
                meta = {"set_id": man["set_id"], "item_id": it["id"], "family": family, "setting": man["setting"],
                        "base_index": it["base_index"], "width": it["width"], "depth": it["depth"],
                        "setup": su.name, "model": su.model, "effort": su.effort, "sample": k}
                out.append((cid, params, meta))
    return out


def build_realtime_requests(man: Dict, items: List[Dict], n_puzzles: int = RT_PUZZLES) -> List[Item]:
    """The real-time check's requests: the first `n_puzzles` puzzles (both shapes of the first base puzzles) of a digit or ledger set."""
    family = man["family"]
    if family not in ("digits", "ledger"):
        raise ValueError("the real-time check runs on a digit or ledger set")
    chosen = sorted(items, key=lambda it: (it["base_index"], it["width"]))[:n_puzzles]
    out: List[Item] = []
    for it in chosen:
        for su in RT_SETUPS:
            params = build_params(su.model, su.effort, pilot_max_tokens(family, su.model),
                                  [{"role": "user", "content": it["prompt"]}])
            for k in range(1, su.n + 1):
                cid = f"{it['id']}-rt{su.name}-{k:02d}"
                check_custom_id(cid)
                meta = {"set_id": man["set_id"], "item_id": it["id"], "family": family, "setting": man["setting"],
                        "base_index": it["base_index"], "width": it["width"], "depth": it["depth"],
                        "setup": "rt" + su.name, "model": su.model, "effort": su.effort, "sample": k}
                out.append((cid, params, meta))
    return out


def run_realtime(guard, transport, log: CallLog, requests: List[Item], workers: int = 4) -> Dict[str, int]:
    """Send the real-time requests with Client.call (reserved at list price, streamed, latency logged), a few at a time.
    A wrong-model reply halts the guard and stops the rest; failed calls are logged and counted, not retried."""
    from concurrent.futures import ThreadPoolExecutor
    from .client import Client
    from .guard import GuardHalted
    client = Client(guard, transport, log)
    counts = {"answered": 0, "failed": 0, "not_sent": 0, "already_done": 0}
    done = log.finished_ids()
    todo = [r for r in requests if r[0] not in done]
    counts["already_done"] = len(requests) - len(todo)

    def one(r: Item) -> str:
        try:
            out = client.call(r[0], r[1], r[2])
            return "failed" if out.is_failure else "answered"
        except GuardHalted:
            return "not_sent"
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(one, todo):
            counts[res] += 1
    return counts


def grader(items_by_id: Dict[str, Dict], family: str):
    """grade(record) -> True / False for an answered call; used by table.write_compact_table for the `right` column.
    Ledger sets: the OFFICIAL D-76 score, by the analysis's own scorers (one definition, not a copy; Edith, PR #19 r4): a 1x24 try is right
    only if all 24 step lines and the Answer line are right (scoring.grade_1x24; an item frozen with the answer-only prompt is scored by its
    final answer), a 24x1 try only if every piece is right (scoring.grade_24x1). Other families: whole-answer scoring (D-39), as before."""
    from ..taskgen.prompt_d31 import score_answer

    def grade(rec: Dict[str, object]) -> Optional[bool]:
        meta = rec.get("meta") or {}
        it = items_by_id.get(str(meta.get("item_id")))  # type: ignore[union-attr]
        if it is None:
            return None
        text = str(rec.get("answer_text") or "")
        if family == "ledger":
            from ..analysis import scoring                     # imported here: harness.analysis imports harness.pareto.table
            lines = int(it["params"]["lines"])
            if int(it["depth"]) > 1:
                return bool(scoring.grade_1x24(text, it["chains"][0]["states"], lines,
                                               answer_only=it.get("style") == "d31-answer-only")["correct"])
            return bool(scoring.grade_24x1(text, it["answer"], lines)["correct"])
        answer = [tuple(a) for a in it["answer"]] if family == "code" else list(it["answer"])
        return bool(score_answer(text, answer)["all_correct"])
    return grade


def plan_realtime(requests: List[Item]) -> Dict[str, object]:
    from .prices import worst_case
    per: Dict[str, int] = {}
    total = Decimal("0")
    for cid, p, m in requests:
        per[m["setup"]] = per.get(m["setup"], 0) + 1
        total += worst_case(p["model"], estimate_input_tokens(prompt_text(p)), p["max_tokens"], batch=False)
    return {"calls": len(requests), "per_setup": per, "list_price_worst_case_usd": str(total)}


def plan(guard, requests: List[Item]) -> Dict[str, object]:
    """What a run would do, without doing it: calls per setup, the list-price and Batch-price worst cases, and the waves."""
    from .prices import worst_case
    specs = [(cid, p["model"], estimate_input_tokens(prompt_text(p)), p["max_tokens"], True) for cid, p, _ in requests]
    per: Dict[str, int] = {}
    total = Decimal("0")
    for (cid, p, m), spec in zip(requests, specs):
        key = f"{m['family']}/{m['setup']}"
        per[key] = per.get(key, 0) + 1
        total += worst_case(spec[1], spec[2], spec[3], batch=True)
    waves = []
    remaining = list(specs)
    # plan_waves is re-planned after each wave in a real run; here, an upper-bound picture with no spend in between
    try:
        for w in guard.plan_waves(remaining):
            waves.append(len(w))
    except Exception as e:                       # CapExceeded: one call alone does not fit
        return {"calls": len(requests), "per_setup": per, "batch_worst_case_usd": str(total), "error": str(e)}
    return {"calls": len(requests), "per_setup": per, "batch_worst_case_usd": str(total),
            "waves_if_nothing_were_spent_between": waves}


def run_pilot(guard, transport, out_dir: Path, set_dirs: List[Path], poll_s: float = 60.0, sleep=None,
              max_wave_size: Optional[int] = None, realtime_set: Optional[Path] = None,
              build: Optional[Callable[[Dict, List[Dict]], List[Item]]] = None,
              make_grader: Optional[Callable[[Dict[str, Dict], str], Callable[[Dict[str, object]], Optional[bool]]]] = None,
              loader: Optional[Callable[[Path], Tuple[Dict, List[Dict]]]] = None, note: str = "pilot (D-36)") -> Dict[str, object]:
    """Run the pilot's Batch (and, with `realtime_set`, the real-time check) and write the compact table. The ladder (ladder.py) reuses
    this with its own `build` (its setups), `make_grader` (Haiku-medium only: the other models stay sealed) and `note`; `loader` is
    `load_set` (verified) unless a test passes another. The defaults are the pilot's, unchanged."""
    out_dir = Path(out_dir)
    log = CallLog(out_dir / "calls.jsonl")
    build = build or build_requests
    make_grader = make_grader or grader
    loader = loader or load_set
    requests: List[Item] = []
    items_by_id: Dict[str, Dict] = {}
    families: Dict[str, str] = {}
    for d in set_dirs:
        man, items = loader(d)
        requests += build(man, items)
        for it in items:
            items_by_id[it["id"]] = it
            families[it["id"]] = man["family"]
    ids = [r[0] for r in requests]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate custom_id across the sets")
    rt: List[Item] = []
    if realtime_set is not None:
        rman, ritems = loader(realtime_set)
        rt = build_realtime_requests(rman, ritems)
        for cid, _, _ in rt:
            if cid in set(ids):
                raise ValueError("real-time custom_id clashes with a batch one")
        for it in ritems:
            items_by_id[it["id"]] = it
            families[it["id"]] = rman["family"]
    manifest = out_dir / "manifest.json"
    if not manifest.exists():
        write_manifest(out_dir, guard, requests + rt, "batch" if transport.live else "dry", note=note)
    kw = {"sleep": sleep} if sleep is not None else {}
    fam_of = {r[0]: r[2]["family"] for r in requests + rt}
    grade_by_family = {f: make_grader(items_by_id, f) for f in set(fam_of.values())}

    def grade(rec: Dict[str, object]) -> Optional[bool]:
        return grade_by_family[fam_of[str(rec["custom_id"])]](rec)
    try:
        summary = run_batches(guard, transport, log, requests, poll_s=poll_s, max_wave_size=max_wave_size, **kw)
        rt_counts = None
        if rt and not summary.stopped_for_console_check:
            rt_counts = run_realtime(guard, transport, log, rt)
    finally:
        # whatever happened (a halt, a crash, a stop for the Console check), the table of what was logged is written (N59)
        total = write_compact_table(log, out_dir / "compact_table.csv", grade=grade)
    return {"summary": summary, "realtime": rt_counts, "table_cost_usd": str(total), "block_rates": block_rates(log)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live", "console-check", "console-clear"))
    ap.add_argument("--sets", nargs="+", type=Path)
    ap.add_argument("--run-id", default="pilot-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required for live and console-check (no default)")
    ap.add_argument("--clearance", type=Path)
    ap.add_argument("--rt-set", type=Path, help="the set (digits or ledger) whose first 10 puzzles get the real-time check")
    ap.add_argument("--usd", help="console-check: the dollars the Console shows for this run so far")
    ap.add_argument("--note", help="console-check: where the figure came from")
    a = ap.parse_args(argv)
    from .guard import SpendGuard
    from .transport import DryTransport
    if a.mode == "console-clear":
        if not (a.run_id and a.cap and a.clearance and a.note):
            ap.error("console-clear needs --run-id --cap --clearance --note (what you found out)")
        from .live import clear_console_block
        cleared = clear_console_block(a.run_id, Decimal(a.cap), a.clearance, a.note)
        print("cleared failed Console checks:", cleared)
        return 0
    if a.mode == "console-check":
        if not (a.run_id and a.cap and a.clearance and a.usd and a.note):
            ap.error("console-check needs --run-id --cap --clearance --usd --note")
        from .guard import ConsoleNotUpdated
        from .live import record_console_check
        try:
            record_console_check(a.run_id, Decimal(a.cap), a.clearance, Decimal(a.usd), a.note)
        except ConsoleNotUpdated as e:
            print(f"NOT RECORDED: the Console does not show enough yet ({e}). Wait a few minutes and run this again.")
            return 2
        print("console check recorded")
        return 0
    if not a.sets:
        ap.error("need --sets")
    requests: List[Item] = []
    for d in a.sets:
        man, items = load_set(d)
        requests += build_requests(man, items)
    if a.mode in ("plan", "dry"):
        guard = SpendGuard(a.run_id, Decimal(a.cap or "30"), global_spent_usd=Decimal("0"))
        print(json.dumps(plan(guard, requests), indent=1))
        if a.rt_set is not None:
            rman, ritems = load_set(a.rt_set)
            print("real-time check:", json.dumps(plan_realtime(build_realtime_requests(rman, ritems)), indent=1))
        if a.mode == "dry":
            if a.out is None:
                ap.error("dry needs --out")
            r = run_pilot(guard, DryTransport(), a.out, a.sets, sleep=lambda s: None, realtime_set=a.rt_set)
            print("dry run done:", r["summary"])
        return 0
    if a.cap is None or a.clearance is None:
        ap.error("live needs an explicit --cap and --clearance")
    if a.out is not None:
        ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/); do not give --out")
    from .live import open_live_guard
    from .transport import RealTransport, TransportError
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        transport = RealTransport(guard)
        r = run_pilot(guard, transport, folder, a.sets, realtime_set=a.rt_set)
        print("live run done:", r["summary"])
        if r["summary"].stopped_for_console_check:
            print("STOPPED for the Console check: read what the Console shows for this run, then run "
                  "`pilot console-check --run-id ... --cap ... --clearance ... --usd <dollars> --note <where from>` "
                  "and run the same live command again")
    except TransportError as e:
        print(f"STOPPED: the API did not accept a call ({e.kind}, status {e.status}, billed: {e.billed}). Nothing further was sent. "
              "Look at the call log and the ledger before running again; a call rejected before running is sent again on resume.")
        return 3
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
