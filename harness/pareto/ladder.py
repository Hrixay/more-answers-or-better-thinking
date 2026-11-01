"""The ladder pilot for prereg-lock-2 (D-86, D-87): frozen ladder sets in, Batch requests out, the compact table written with
ONLY Haiku-medium graded.

    python3 -m harness.pareto.ladder plan --sets SET_DIR [SET_DIR ...]
    python3 -m harness.pareto.ladder dry  --sets SET_DIR [...] --run-id ID --out DIR     # whole flow, no network
    python3 -m harness.pareto.ladder live --sets SET_DIR [...] --run-id ID --cap 6 --clearance FILE

`plan` and `dry` never touch the network and never read `.env`. `live` has the pilot's safeguards: it needs an explicit
`--cap` and Edith's `--clearance` file, opens the live guard (which refuses without the clearance and the user's go, see
guard.py and live.py) and only then builds the real transport; it writes next to its ledger, so `--out` is refused. If a live
run stops for the Console check, record it with `python3 -m harness.pareto.pilot console-check` (same run id, cap and
clearance) and run the same ladder command again. There is no real-time check in the ladder.

The sets. Ladder sets are ledger sets frozen at a ladder preset (`l14n4`, `l14n6`, `l14n8`, `l14n12`, `l14n16`: the l14 rules at
N steps), each base puzzle in the two shapes "Nx1" and "1xN". Any other set is refused. The number of base puzzles is whatever the
frozen sets hold (nothing here assumes 10 or 20).

The setups (`LADDER_SETUPS`, D-86 and D-87), per puzzle, all through Batch at effort medium, with max_tokens from
`limits.pilot_max_tokens("ledger", model)` (Haiku 48K, Opus 32K, Sonnet 32K): Haiku-medium x10, Opus-medium x1, Sonnet-medium x1.
Custom ids are `<full item id>-<setup>-<NN>` (pilot.build_requests), so every row names its set, base puzzle and shape.

Sealing. Haiku-medium alone picks N (`choose_preset`, the D-36(4) rule with ties to fewer steps). Every other setup is SEALED until
the pick is committed: the runner's grader (`sealed_grader`) grades a record only when it is the picker's (setup tag `hm`, model
claude-haiku-5-5, effort medium, all three); for any other record it returns None WITHOUT calling the scorer, so the compact
table's `right` column is blank for every Opus and Sonnet row and no Opus or Sonnet score exists anywhere. Their replies stay in
the git-ignored call log only. The table still carries their tokens and cost (needed for k and pricing), never a score.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ..taskgen import ledger
from .pilot import HAIKU, OPUS, SONNET, Item, Setup, build_requests, grader, load_set, plan, run_pilot

LADDER_SETUPS: Tuple[Setup, ...] = (
    Setup("hm", HAIKU, "medium", 10),       # the picker (D-36(4) via D-86): graded
    Setup("om", OPUS, "medium", 1),         # sealed until the pick is committed (D-86)
    Setup("sm", SONNET, "medium", 1),       # sealed until the pick is committed (D-87)
)
PICKER = LADDER_SETUPS[0]                   # the one setup whose answers are graded before the pick
SEALED = tuple(su.name for su in LADDER_SETUPS if su != PICKER)
LADDER_PRESETS: Dict[str, int] = {f"l14n{n}": n for n in ledger.LADDER_STEPS}
NOTE = "ladder pilot (D-86, D-87): Haiku-medium x10 picks N; Opus-medium and Sonnet-medium x1 sealed"


def ladder_steps(man: Dict, items: List[Dict]) -> int:
    """N for a ladder set, after checking it is one: a ledger set at a ladder preset whose items are all "Nx1" or "1xN" at that N.
    Anything else raises ValueError."""
    if man.get("family") != "ledger":
        raise ValueError(f"{man.get('set_id')}: the ladder runs ledger sets only, not {man.get('family')!r}")
    n = LADDER_PRESETS.get(str(man.get("setting")))
    if n is None:
        raise ValueError(f"{man.get('set_id')}: preset {man.get('setting')!r} is not a ladder preset ({', '.join(LADDER_PRESETS)})")
    for it in items:
        if (int(it["width"]), int(it["depth"])) not in ((n, 1), (1, n)):
            raise ValueError(f"{it['id']}: shape {it['width']}x{it['depth']} is not {n}x1 or 1x{n}")
    return n


def build_ladder_requests(man: Dict, items: List[Dict]) -> List[Item]:
    """The ladder's Batch requests for one checked ladder set: every puzzle times LADDER_SETUPS (pilot.build_requests)."""
    ladder_steps(man, items)
    return build_requests(man, items, LADDER_SETUPS)


def is_picker(rec: Dict[str, object]) -> bool:
    """A call-log record of the picker: setup tag, requested model and effort all Haiku-medium's. A record missing any of them is
    not the picker's (it stays sealed)."""
    meta = rec.get("meta") or {}
    return (meta.get("setup") == PICKER.name and rec.get("requested_model") == PICKER.model  # type: ignore[union-attr]
            and rec.get("effort") == PICKER.effort)


def sealed_grader(items_by_id: Dict[str, Dict], family: str) -> Callable[[Dict[str, object]], Optional[bool]]:
    """pilot.grader for the picker's records (the official D-76 score at 1xN, every piece right at Nx1); None for every other record,
    returned before the scorer is called, so no Opus or Sonnet answer is ever scored."""
    inner = grader(items_by_id, family)

    def grade(rec: Dict[str, object]) -> Optional[bool]:
        if not is_picker(rec):
            return None
        return inner(rec)
    return grade


def ladder_plan(guard, sets: List[Tuple[Dict, List[Dict]]]) -> Dict[str, object]:
    """pilot.plan over the ladder's requests, plus what the run covers: per set its preset, N and numbers of base puzzles and
    puzzles; the setups; which are sealed."""
    requests: List[Item] = []
    per_set: Dict[str, Dict[str, object]] = {}
    for man, items in sets:
        n = ladder_steps(man, items)
        requests += build_ladder_requests(man, items)
        per_set[str(man["set_id"])] = {"preset": man["setting"], "steps": n, "base_puzzles": len({it["base_index"] for it in items}),
                                       "puzzles": len(items)}
    out = plan(guard, requests)
    out.update(sets=per_set, setups=[{"name": su.name, "model": su.model, "effort": su.effort, "per_puzzle": su.n} for su in LADDER_SETUPS],
               picker=PICKER.name, sealed=list(SEALED))
    return out


def run_ladder(guard, transport, out_dir: Path, set_dirs: List[Path], poll_s: float = 60.0, sleep=None,
               max_wave_size: Optional[int] = None, loader=None) -> Dict[str, object]:
    """The ladder through pilot.run_pilot: LADDER_SETUPS, the sealed grader, no real-time check."""
    return run_pilot(guard, transport, out_dir, set_dirs, poll_s=poll_s, sleep=sleep, max_wave_size=max_wave_size,
                     build=build_ladder_requests, make_grader=sealed_grader, loader=loader, note=NOTE)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("plan", "dry", "live"))
    ap.add_argument("--sets", nargs="+", type=Path, required=True)
    ap.add_argument("--run-id", default="ladder-dry")
    ap.add_argument("--out", type=Path, help="dry runs only; a live run writes next to its ledger")
    ap.add_argument("--cap", help="dollars; required for live (no default)")
    ap.add_argument("--clearance", type=Path)
    a = ap.parse_args(argv)
    from .guard import SpendGuard
    from .transport import DryTransport
    sets = [load_set(d) for d in a.sets]                     # each set verified once (load_set), then reused by the run
    try:
        for man, items in sets:
            ladder_steps(man, items)
    except ValueError as e:
        ap.error(str(e))
    loaded = dict(zip(a.sets, sets))
    if a.mode in ("plan", "dry"):
        guard = SpendGuard(a.run_id, Decimal(a.cap or "30"), global_spent_usd=Decimal("0"))
        print(json.dumps(ladder_plan(guard, sets), indent=1))
        if a.mode == "dry":
            if a.out is None:
                ap.error("dry needs --out")
            r = run_ladder(guard, DryTransport(), a.out, a.sets, sleep=lambda s: None, loader=loaded.__getitem__)
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
        r = run_ladder(guard, transport, folder, a.sets, loader=loaded.__getitem__)
        print("live run done:", r["summary"])
        if r["summary"].stopped_for_console_check:
            print("STOPPED for the Console check: read what the Console shows for this run, then run "
                  "`python3 -m harness.pareto.pilot console-check --run-id ... --cap ... --clearance ... --usd <dollars> --note <where from>` "
                  "and run the same ladder command again")
    except TransportError as e:
        print(f"STOPPED: the API did not accept a call ({e.kind}, status {e.status}, billed: {e.billed}). Nothing further was sent. "
              "Look at the call log and the ledger before running again; a call rejected before running is sent again on resume.")
        return 3
    finally:
        guard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
