"""Study 1b, B2's k from costs ONLY, fixed and committed before the analysis driver runs (spec `study1b-spec.md` §4 "B2's k", F-3;
mirrors `k_step.py`, D-93).

    python3 -m harness.analysis.study1b_k --run <run folder> --out <run folder>/k.json

The rule (§4): k = floor(Opus-medium's mean list cost per try / Haiku-max's mean list cost per try), on the N = 16 set
(`main-ledger-l14n16-v1`), from cost-only rows; held to the 10 tries drawn (a ratio above 10 gives k = 10, labelled "for less than
Opus's price", as D-33 item 4: `capped` is exactly "ratio > 10", so a ratio in (10, 11) is labelled too and a ratio of exactly 10 is
not); a ratio below 1 means B2 is not run and keeps its Holm place with p = 1.

What it reads. Only these columns of the run's `compact_table.csv`, taken by name from the header with `csv.reader` (the `right`
column's values are never parsed into a row; no answer, no call log): custom_id, requested_model, effort, kind,
refusal_billed_by_rule and the four token columns. The list cost is item 9a's ONE copy, `report_costs.list_cost` (prices.cost on
the pinned table at list price, batch=False; a refusal that rule B5 does not bill at $0; a record with no usage at $0), applied to
the row's tokens (the compact table's cache-write total is priced at the 5-minute rate, as `outcome.usage_from_raw` prices a total
with no breakdown). B5's free marks are also read from the run's `ledger.jsonl` when it exists (`report_costs._ledger_free_ids`,
cost-only lines), as item 9a reads them.

Which rows count. Only the N = 16 set's hx (Haiku 5.5, max) and om (Opus 5.5, medium) rows; each kept row's model and effort must be
its tag's (else it raises). The trial round (§7) runs on `ladder-ledger-l14n*-v1` items, including a Haiku-max arm at 16
steps: those rows are left out by set id, as is every other set and tag, and counted by set and tag. Means are exact fractions over
the real calls (every final call, failures and refusals included: "all in", as `five_tests.k_from_rows`), and k is
`kscript.k_value(om mean, hx mean, cap=10, samples_drawn=10)`.

Output (`k.json`): k, raw_k, the exact ratio, capped (ratio > 10) and its label, b2_run, the two means and their call counts, the rows kept and
left out, the SHA-256 of compact_table.csv (and of ledger.jsonl when read), and the columns read. It refuses to overwrite an
existing file. The driver (`study1b`) refuses to run without it and recomputes it from the same table.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional

from . import kscript, report_costs
from ..pareto.prices import HAIKU, OPUS

K_SET = "main-ledger-l14n16-v1"
COLUMNS = ("custom_id", "requested_model", "effort", "kind", "refusal_billed_by_rule",
           "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
ARM_MODEL = {"hx": (HAIKU, "max"), "om": (OPUS, "medium")}
CHALLENGER, COMPARATOR = "hx", "om"
CAP = 10                                      # "held to the 10 tries drawn"
SAMPLES_DRAWN = 10
CAPPED_LABEL = "for less than Opus's price"   # §4, as D-33 item 4
NOT_RUN = "B2 not run (cost ratio below 1): it keeps its Holm place with p = 1"


def read_cost_columns(table: Path) -> List[Dict[str, str]]:
    """Only COLUMNS of the compact table, by header name (the `right` column is never parsed into a row)."""
    with open(table, newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        idx = {c: header.index(c) for c in COLUMNS}
        return [{c: line[idx[c]] for c in COLUMNS} for line in rd if line]


def _flag(v: str) -> Optional[bool]:
    """The CSV spelling of refusal_billed_by_rule (csv.DictWriter writes True / False / "")."""
    return {"True": True, "False": False, "true": True, "false": False}.get(v.strip())


def _tokens(v: str) -> int:
    return int(v) if v.strip() else 0


def row_list_cost(c: Dict[str, str], free_ids: frozenset = frozenset()) -> Decimal:
    """Item 9a's list cost of one cost-only row (report_costs.list_cost on the row's tokens, kind and B5 flag)."""
    rec = {"custom_id": c["custom_id"], "requested_model": c["requested_model"], "kind": c["kind"],
           "refusal_billed_by_rule": _flag(c["refusal_billed_by_rule"]),
           "usage_raw": {"input_tokens": _tokens(c["input_tokens"]), "output_tokens": _tokens(c["output_tokens"]),
                         "cache_read_input_tokens": _tokens(c["cache_read_tokens"]),
                         "cache_creation_input_tokens": _tokens(c["cache_write_tokens"])}}
    return report_costs.list_cost(rec, free_ids)


def k_from_table(table: Path, run_dir: Optional[Path] = None) -> Dict[str, object]:
    """B2's k from the cost-only rows of `table` (see the module text). `run_dir` is where ledger.jsonl is looked for (default: the
    table's folder)."""
    table = Path(table)
    run_dir = Path(run_dir) if run_dir is not None else table.parent
    free_ids, ledger_read = report_costs._ledger_free_ids(run_dir)
    totals = {CHALLENGER: Decimal(0), COMPARATOR: Decimal(0)}
    kept: Counter = Counter()
    left_by_set: Counter = Counter()
    left_by_tag: Counter = Counter()
    for c in read_cost_columns(table):
        cid = kscript.parse_custom_id(c["custom_id"])
        tag = str(cid["setup"])
        if cid["set_id"] != K_SET:
            left_by_set[str(cid["set_id"])] += 1
            continue
        if tag not in ARM_MODEL:
            left_by_tag[tag] += 1
            continue
        if (c["requested_model"], c["effort"]) != ARM_MODEL[tag]:
            raise ValueError(f"{c['custom_id']}: tag {tag} with {c['requested_model']} / {c['effort']}")
        kept[tag] += 1
        totals[tag] += row_list_cost(c, free_ids)
    for tag in (CHALLENGER, COMPARATOR):
        if not kept[tag]:
            raise ValueError(f"{table}: no {tag} row of {K_SET}; k cannot be computed")
    mean = {tag: Fraction(totals[tag]) / kept[tag] for tag in (CHALLENGER, COMPARATOR)}
    kv = kscript.k_value(mean[COMPARATOR], mean[CHALLENGER], cap=CAP, samples_drawn=SAMPLES_DRAWN)
    k = int(kv["k"])                                                                       # type: ignore[call-overload]
    b2_run = k >= 1
    capped = Fraction(kv["ratio"]) > CAP                                                   # §4: "if the cost ratio is above 10" (S-D2)
    out: Dict[str, object] = {
        "k": k, "raw_k": int(kv["raw_k"]), "ratio": str(kv["ratio"]), "ratio_float": float(kv["ratio"]),   # type: ignore[arg-type, call-overload]
        "capped": capped, "label": CAPPED_LABEL if capped else None, "capped_rule": f"ratio > {CAP} (§4)",
        "b2_run": b2_run, "b2_note": None if b2_run else NOT_RUN, "cap": CAP, "samples_drawn": SAMPLES_DRAWN,
        "set_id": K_SET, "n": 16, "challenger": CHALLENGER, "comparator": COMPARATOR,
        "mean_list_cost_per_try": {tag: str(mean[tag]) for tag in mean},
        "mean_list_cost_per_try_float": {tag: float(mean[tag]) for tag in mean},
        "total_list_cost": {tag: str(totals[tag]) for tag in totals}, "calls": dict(kept),
        "rows_left_out_by_set": dict(sorted(left_by_set.items())), "rows_left_out_by_tag": dict(sorted(left_by_tag.items())),
        "compact_table_sha256": hashlib.sha256(table.read_bytes()).hexdigest(), "columns_read": list(COLUMNS),
        "ledger_read_for_free_by_rule": ledger_read,
        "ledger_sha256": (hashlib.sha256((run_dir / "ledger.jsonl").read_bytes()).hexdigest() if ledger_read else None),
        "free_b5_ids_in_ledger": len(free_ids),
        "rule": "k = floor(om mean list cost per try / hx mean list cost per try) on main-ledger-l14n16-v1, cap 10 (study1b-spec §4)"}
    return out


def load_k(path: Path) -> Dict[str, object]:
    if not Path(path).is_file():
        raise FileNotFoundError(f"{path}: run `python3 -m harness.analysis.study1b_k` and commit k.json before the driver (§4, §9 step 6)")
    return json.loads(Path(path).read_text())


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="the run folder holding compact_table.csv (and ledger.jsonl)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: k is fixed once")
    res = k_from_table(a.run / "compact_table.csv", a.run)
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(f"wrote {a.out}: k = {res['k']} (raw {res['raw_k']}, ratio {res['ratio_float']:.4f}){' ' + str(res['label']) if res['label'] else ''}"
          f"{'' if res['b2_run'] else '; ' + NOT_RUN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
