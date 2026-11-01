"""The Study 1 main run (D-27, D-35, prereg-lock-3 with Amendment 1): the frozen main set in, Batch requests out, the compact table
written with every arm graded (nothing is sealed in the main run).

    python3 -m harness.pareto.main plan --set SET_DIR [--extras sl,ho,hx]
    python3 -m harness.pareto.main dry  --set SET_DIR --run-id ID --out DIR [--extras ...]       # whole flow, no network
    python3 -m harness.pareto.main live --set SET_DIR --run-id ID --cap 80 --clearance FILE [--extras ...]

`plan` and `dry` never touch the network and never read `.env`. `live` has the pilot's safeguards: an explicit `--cap`, Edith's
`--clearance` file, the live guard (which refuses without the clearance and the user's go), then the real transport; it writes next to
its ledger, so `--out` is refused. A stop for the Console check is recorded with `python3 -m harness.pareto.pilot console-check` (same
run id, cap and clearance); then run the same command again: finished calls are never sent twice (`run_batches` skips them).

The set. One frozen ledger set at the chosen preset (Amendment 1: `main-ledger-l14n6-v1`, 80 base puzzles x 2 shapes, 6x1 and 1x6).

The setups (`MAIN_SETUPS`; D-27 must-haves, then the D-27 extras that use the main prompt unchanged), all through Batch:
- must: Haiku-medium x40 (`hm`), Haiku-low x40 (`hl`), Opus-medium x1 (`om`), Opus-low x1 (`ol`), Sonnet-medium x1 (`sm`);
- extras, only when named in `--extras`, in the D-73 order: Sonnet-low x1 (`sl`), Haiku thinking-off x40 at effort medium (`ho`),
  Haiku-max x3 (`hx`, the first to trim). E2 and the Haiku picker over 8 are NOT here: their wording is new and needs Edith's
  check and the user's approval first (Edith, 2026-10-12 main-run prep rulings); they plug in later.
- the D-42 (a) prompt variant (`hv`, D-91, approved): Haiku-medium x10 at 5,000 tokens on base 000-019 of the set, both shapes (40
  puzzles), with the variant wording (`harness.pareto.d42`); robustness, outside the confirmatory tests. In the plan by default
  (`--no-d42` leaves it out).
- E3 (a must) runs through `harness.pareto.e3` (step calls with lead-by-2 voting, cap 9) on the same log; `plan` reports its
  first round, its most calls (every step at the cap) and their booking under `e3`.
max_tokens (Amendment 1, item 3): the medium setups the ladder measured get 1.5x its largest output, rounded up to 1,000 (Haiku 5,000,
Opus 4,000, Sonnet 3,000); every setup it did not measure keeps the locked pilot limit (Haiku 48,000, Opus and Sonnet 32,000).

The real-time latency subset (D-35, a must): the first 10 puzzles of the set (5 base x 2 shapes), Haiku-medium x5, Sonnet-medium x1 and
Opus-medium x1, in real time at list price, with the same limits as their Batch setups (the pilot's real-time code, `pilot.run_realtime`).

Run rules (D-42 (b), D-45): every reply's model must equal the model asked (the guard halts on a mismatch; the run stops). The whole run
must finish within the window (48 hours from the first submission, `WINDOW_HOURS`; D-45 allows an extension only with a recorded note):
a live run started after the window refuses to send anything new.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .client import check_custom_id
from .pilot import HAIKU, OPUS, SONNET, Item, grader, load_set, plan, run_realtime
from .request import build_params

WINDOW_HOURS = 48
TRUNCATION_PAUSE = 0.02          # Edith, readiness item 2: a setup truncating over 2% of a wave pauses the run before the next wave
RT_PUZZLES = 10


@dataclass(frozen=True)
class MainSetup:
    name: str            # the custom_id tag: letters only (kscript.parse_custom_id)
    model: str
    effort: str
    n: int               # samples per puzzle
    max_tokens: int      # Amendment 1, item 3
    priority: str        # "must" or "extra N" (the D-73 order)
    thinking_off: bool = False


MAIN_SETUPS: Tuple[MainSetup, ...] = (
    MainSetup("hm", HAIKU, "medium", 40, 5_000, "must"),
    MainSetup("hl", HAIKU, "low", 40, 48_000, "must"),
    MainSetup("om", OPUS, "medium", 1, 4_000, "must"),
    MainSetup("ol", OPUS, "low", 1, 32_000, "must"),
    MainSetup("sm", SONNET, "medium", 1, 3_000, "must"),
    MainSetup("sl", SONNET, "low", 1, 32_000, "extra 1"),
    MainSetup("ho", HAIKU, "medium", 40, 48_000, "extra 2", thinking_off=True),
    MainSetup("hx", HAIKU, "max", 3, 48_000, "extra (first to trim)"),
)
D42_SETUP = MainSetup("hv", HAIKU, "medium", 10, 5_000, "D-42 (a)")   # D-91: the variant wording, 40 pinned puzzles
MUSTS = tuple(su.name for su in MAIN_SETUPS if su.priority == "must")
EXTRAS = tuple(su.name for su in MAIN_SETUPS if su.priority != "must")
BY_NAME: Dict[str, MainSetup] = {su.name: su for su in MAIN_SETUPS + (D42_SETUP,)}
RT_SETUPS: Tuple[Tuple[str, int], ...] = (("hm", 5), ("sm", 1), ("om", 1))   # the Batch setup each copies, and samples per puzzle
NOTE = "main run (D-27, Amendment 1): musts plus the named extras; E3 through harness.pareto.e3"


def chosen_setups(extras: Sequence[str] = ()) -> Tuple[MainSetup, ...]:
    """The must-haves plus the named extras (any of `EXTRAS`), in `MAIN_SETUPS` order."""
    bad = sorted(set(extras) - set(EXTRAS))
    if bad:
        raise ValueError(f"unknown extras {bad}; choose from {EXTRAS}")
    return tuple(su for su in MAIN_SETUPS if su.priority == "must" or su.name in extras)


def check_main_set(man: Dict, items: List[Dict]) -> int:
    """N for the main set, after checking it is a ledger set whose items are all "Nx1" or "1xN" at one N."""
    if man.get("family") != "ledger":
        raise ValueError(f"{man.get('set_id')}: the main run uses a ledger set, not {man.get('family')!r}")
    steps = {max(int(it["width"]), int(it["depth"])) for it in items}
    if len(steps) != 1:
        raise ValueError(f"{man.get('set_id')}: items of more than one length {sorted(steps)}")
    n = steps.pop()
    for it in items:
        if (int(it["width"]), int(it["depth"])) not in ((n, 1), (1, n)):
            raise ValueError(f"{it['id']}: shape {it['width']}x{it['depth']} is not {n}x1 or 1x{n}")
    return n


def _item(man: Dict, it: Dict, su: MainSetup, tag: str, k: int) -> Item:
    params = build_params(su.model, su.effort, su.max_tokens, [{"role": "user", "content": it["prompt"]}], thinking_off=su.thinking_off)
    cid = f"{it['id']}-{tag}-{k:02d}"
    check_custom_id(cid)
    meta = {"set_id": man["set_id"], "item_id": it["id"], "family": man["family"], "setting": man["setting"],
            "base_index": it["base_index"], "width": it["width"], "depth": it["depth"], "setup": tag, "model": su.model,
            "effort": su.effort, "thinking_off": su.thinking_off, "sample": k}
    return cid, params, meta


def build_d42_requests(man: Dict, items: List[Dict]) -> List[Item]:
    """D-42 (a), D-91: Haiku-medium x10 with the variant wording on the 40 pinned puzzles (`d42.d42_items`)."""
    from .d42 import d42_items
    check_main_set(man, items)
    su = D42_SETUP
    return [_item(man, it, su, su.name, k) for it in d42_items(items) for k in range(1, su.n + 1)]


def build_main_requests(man: Dict, items: List[Dict], extras: Sequence[str] = (), d42: bool = True) -> List[Item]:
    """Every Batch request of the single-call arms: each puzzle times each chosen setup's samples, then (by default) D-42 (a)."""
    check_main_set(man, items)
    out = [_item(man, it, su, su.name, k) for it in items for su in chosen_setups(extras) for k in range(1, su.n + 1)]
    return out + (build_d42_requests(man, items) if d42 else [])


def build_rt_requests(man: Dict, items: List[Dict], n_puzzles: int = RT_PUZZLES) -> List[Item]:
    """The real-time latency subset: the first `n_puzzles` puzzles (both shapes of the first base puzzles), tags `rt<setup>`."""
    check_main_set(man, items)
    chosen = sorted(items, key=lambda it: (it["base_index"], it["width"]))[:n_puzzles]
    return [_item(man, it, BY_NAME[name], "rt" + name, k) for it in chosen for name, n in RT_SETUPS for k in range(1, n + 1)]


def main_plan(guard, man: Dict, items: List[Dict], extras: Sequence[str] = (), d42: bool = True) -> Dict[str, object]:
    """pilot.plan over the Batch requests (worst-case booking and waves), plus per-setup counts, limits and the real-time part."""
    from .prices import estimate_input_tokens, worst_case
    from .request import prompt_text
    requests = build_main_requests(man, items, extras, d42)
    out = plan(guard, requests)
    per: Dict[str, Dict[str, object]] = {}
    for cid, params, meta in requests:
        row = per.setdefault(str(meta["setup"]), {"calls": 0, "max_tokens": params["max_tokens"], "booking_usd": Decimal(0)})
        row["calls"] = int(row["calls"]) + 1                                                          # type: ignore[call-overload]
        row["booking_usd"] += worst_case(str(params["model"]), estimate_input_tokens(prompt_text(params)),  # type: ignore[operator]
                                         int(params["max_tokens"]), batch=True)                     # type: ignore[call-overload]
    rt = build_rt_requests(man, items)
    rt_wc = sum((worst_case(str(p["model"]), estimate_input_tokens(prompt_text(p)), int(p["max_tokens"]), batch=False)  # type: ignore[call-overload]
                 for _, p, _ in rt), Decimal(0))
    from . import e3
    steps = e3.chain_steps([(man, items)])
    first = e3.plan_round([(man, items)], [], steps)
    e3_one = worst_case(e3.E3_MODEL, estimate_input_tokens(prompt_text(first[0][1])), int(first[0][1]["max_tokens"]), batch=True) if first else Decimal(0)  # type: ignore[call-overload]
    out["e3"] = {"step_positions": len(steps), "first_round_calls": len(first), "max_calls_at_cap": len(steps) * e3.CAP,
                 "lead": e3.LEAD, "cap": e3.CAP, "max_tokens": int(first[0][1]["max_tokens"]) if first else None,     # type: ignore[call-overload]
                 "first_round_booking_usd": str(sum((worst_case(e3.E3_MODEL, estimate_input_tokens(prompt_text(p)), int(p["max_tokens"]),  # type: ignore[call-overload]
                                                               batch=True) for _, p, _ in first), Decimal(0))),
                 "booking_at_cap_usd_approx": str(e3_one * len(steps) * e3.CAP)}
    out.update(set_id=man["set_id"], steps=check_main_set(man, items), puzzles=len(items),
               setups=[{"name": su.name, "model": su.model, "effort": su.effort, "per_puzzle": su.n, "max_tokens": su.max_tokens,
                        "thinking_off": su.thinking_off, "priority": su.priority,
                        "calls": per[su.name]["calls"], "batch_booking_usd": str(per[su.name]["booking_usd"])}
                       for su in chosen_setups(extras) + ((D42_SETUP,) if d42 else ())],
               realtime={"calls": len(rt), "puzzles": RT_PUZZLES, "list_worst_case_usd": str(rt_wc),
                         "per_setup": {"rt" + name: n * RT_PUZZLES for name, n in RT_SETUPS}},
               not_here=["E2 and H-pick8: wording pending approval; a later, separate run"])
    return out


def window_check(out_dir: Path, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 hours: int = WINDOW_HOURS, extension_note: Optional[str] = None) -> Dict[str, object]:
    """D-42 (b) / D-45: the run's window starts at its first live start (recorded in `window.json`); after `hours` a live run refuses
    to send anything new unless an extension note is given (recorded with its time)."""
    path = Path(out_dir) / "window.json"
    t = now()
    if path.exists():
        w = json.loads(path.read_text())
    else:
        w = {"started_utc": t.isoformat(), "hours": hours, "extensions": []}
    end = datetime.fromisoformat(str(w["started_utc"])) + timedelta(hours=int(w["hours"]))
    if t > end:
        if not extension_note:
            raise RuntimeError(f"the run window ended at {end.isoformat()} (D-42 (b)); extending it needs a note (D-45) and the user's say")
        w["extensions"].append({"at_utc": t.isoformat(), "note": extension_note})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(w, indent=1) + "\n")
    return w


def run_main(guard, transport, out_dir: Path, set_dir: Path, extras: Sequence[str] = (), poll_s: float = 60.0, sleep=None, d42: bool = True,
             pause_truncated_over: Optional[float] = TRUNCATION_PAUSE, release_pause_note: Optional[str] = None,
             waive_pause_note: Optional[str] = None,
             max_wave_size: Optional[int] = None, loader=None, with_e3: bool = True, with_rt: bool = True,
             now: Optional[Callable[[], datetime]] = None, extension_note: Optional[str] = None) -> Dict[str, object]:
    """The main run: the single-call arms through Batch, then E3 (its own Batch rounds), then the real-time subset; the compact table
    is written whatever happens. All on one call log (`out_dir/calls.jsonl`); custom ids never clash (tags differ)."""
    from .batch import run_batches
    from .calllog import CallLog
    from .manifest import write_manifest
    from .table import block_rates, write_compact_table
    out_dir = Path(out_dir)
    window_check(out_dir, **({"now": now} if now else {}), extension_note=extension_note)
    loader = loader or load_set
    man, items = loader(set_dir)
    requests = build_main_requests(man, items, extras, d42)
    rt = build_rt_requests(man, items) if with_rt else []
    log = CallLog(out_dir / "calls.jsonl")
    if waive_pause_note is not None:
        from .batch import waive_pause
        waive_pause(log, guard.run_id, waive_pause_note)                     # refuses an empty note
    if release_pause_note:
        from .batch import pause_state, release_pause
        if pause_state(log) is None:
            raise RuntimeError("--release-pause was given but the run is not paused")
        release_pause(log, guard.run_id, release_pause_note)
    if not (out_dir / "manifest.json").exists():
        write_manifest(out_dir, guard, requests + rt, "batch" if transport.live else "dry", note=NOTE)
    kw = {"sleep": sleep} if sleep is not None else {}
    items_by_id = {it["id"]: it for it in items}
    grade = grader(items_by_id, "ledger")
    e3_summary = rt_counts = None
    try:
        summary = run_batches(guard, transport, log, requests, poll_s=poll_s, max_wave_size=max_wave_size,
                              pause_truncated_over=pause_truncated_over, **kw)
        stopped = summary.stopped_for_console_check or bool(summary.paused_for_truncation)
        if with_e3 and not stopped:
            from . import e3
            e3_summary = e3.run_e3(guard, transport, out_dir, [set_dir], poll_s=poll_s, loader=loader,
                                   pause_truncated_over=pause_truncated_over, **kw)
            stopped = bool(e3_summary.get("stopped"))
        if rt and not stopped:
            rt_counts = run_realtime(guard, transport, log, rt)
    finally:
        total = write_compact_table(log, out_dir / "compact_table.csv", grade=grade)
    return {"summary": summary, "e3": e3_summary, "realtime": rt_counts, "table_cost_usd": str(total), "block_rates": block_rates(log)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--set", type=Path, required=True)
    ap.add_argument("--extras", default="", help=f"comma-separated, any of {', '.join(EXTRAS)}")
    ap.add_argument("--run-id", default="main-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required for live (no default)")
    ap.add_argument("--clearance", type=Path)
    ap.add_argument("--no-e3", action="store_true", help="plan and dry runs only: leave E3 out")
    ap.add_argument("--no-d42", action="store_true", help="leave the D-42 (a) variant arm out")
    ap.add_argument("--extend-window", help="D-45: a recorded note that extends the 48-hour window (needs the user's say)")
    ap.add_argument("--release-pause", help="after a truncation pause: a recorded note of the user's ruling to go on")
    ap.add_argument("--truncation-pause-off", help="the user's ruling to run without the 2%% truncation pause (a recorded note)")
    a = ap.parse_args(argv)
    from .guard import SpendGuard
    from .transport import DryTransport
    try:
        extras = tuple(x for x in a.extras.split(",") if x)
        chosen_setups(extras)
        man, items = load_set(a.set)                       # verified once, then reused by the run
        check_main_set(man, items)
    except ValueError as e:
        ap.error(str(e))

    def loader(_: Path) -> Tuple[Dict, List[Dict]]:
        return man, items
    if a.mode in ("plan", "dry"):
        guard = SpendGuard(a.run_id, Decimal(a.cap or "100"), global_spent_usd=Decimal("0"))
        print(json.dumps(main_plan(guard, man, items, extras, not a.no_d42), indent=1, default=str))
        if a.mode == "dry":
            if a.out is None:
                ap.error("dry needs --out")
            r = run_main(guard, DryTransport(), a.out, a.set, extras, sleep=lambda s: None, loader=loader, with_e3=not a.no_e3,
                         d42=not a.no_d42)
            print("dry run done:", r["summary"], "e3:", r["e3"], "realtime:", r["realtime"])
        return 0
    if a.cap is None or a.clearance is None:
        ap.error("live needs an explicit --cap and --clearance")
    if a.out is not None or a.no_e3:
        ap.error("live writes next to its ledger (<shared data root>/raw/<run-id>/) and always runs E3; do not give --out or --no-e3")
    from .live import open_live_guard
    from .transport import RealTransport, TransportError
    guard, folder = open_live_guard(a.run_id, Decimal(a.cap), a.clearance)
    try:
        transport = RealTransport(guard)
        r = run_main(guard, transport, folder, a.set, extras, loader=loader, extension_note=a.extend_window, d42=not a.no_d42,
                     release_pause_note=a.release_pause, waive_pause_note=a.truncation_pause_off)
        print("live run done:", r["summary"], "e3:", r["e3"], "realtime:", r["realtime"])
        if r["summary"].paused_for_truncation or (r["e3"] or {}).get("stopped") == "paused_for_truncation":
            print("PAUSED for truncation (over 2% of a wave in a setup): report the shares to Edith and the user; run the same command "
                  "with --release-pause '<the user's ruling>' only after they rule")
        if r["summary"].stopped_for_console_check or (r["e3"] or {}).get("stopped"):
            print("STOPPED for the Console check: read what the Console shows for this run, then run "
                  "`python3 -m harness.pareto.pilot console-check --run-id ... --cap ... --clearance ... --usd <dollars> --note <where from>` "
                  "and run the same main command again")
    except TransportError as e:
        print(f"STOPPED: the API did not accept a call ({e.kind}, status {e.status}, billed: {e.billed}). Nothing further was sent. "
              "Look at the call log and the ledger before running again; a call rejected before running is sent again on resume.")
        return 3
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
