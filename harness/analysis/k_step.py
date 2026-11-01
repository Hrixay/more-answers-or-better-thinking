"""The equal-money k from costs ONLY, fixed before any main-run result is opened (D-33, D-70; Jarvis's readiness list, D-93).

    python3 -m harness.analysis.k_step --run <run folder> --out <run folder>/k.json

It reads five columns of the run's `compact_table.csv` and nothing else: custom_id, requested_model, effort, kind, cost_usd. It never
reads `right`, an answer or the call log. The columns are taken by name from the header with `csv.reader`, so the `right` column's
values are never parsed into a row.

Which calls count (the guard Jarvis asked for). The locked k (`five_tests.k_from_rows`) compares Opus-medium and Sonnet-medium with
Haiku-medium, the five tests' arms. In the main run several OTHER setups also call Haiku at effort medium: thinking-off (`ho`), the
D-42 variant (`hv`), E3's step calls (`es`) and the real-time subset (`rthm`). Keyed by model and effort (as `kscript.k_table` keys
them), they would be pooled into Haiku-medium and change k. So only the confirmatory tags are kept: hm -> "haiku-med", om ->
"opus-med", sm -> "sonnet-med" (`main_rows.FIVE_TEST_ARMS`), and each row's model and effort must be its tag's (else it raises).
`confirmatory_cost_rows` is the one source of rows for any k computation on a main-run table.

Output (`k.json`): k_o per shape and k_s (the integers the five tests use), `k_from_rows`'s full output (raw k, ratio, warnings, rows
without cost), the SHA-256 of compact_table.csv, and the counts of rows kept and left out by tag. The driver (`main_analysis`) refuses
to run without it and checks its k against the same computation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from . import five_tests, scoring
from .kscript import parse_custom_id
from .main_rows import FIVE_TEST_ARMS

COLUMNS = ("custom_id", "requested_model", "effort", "kind", "cost_usd")
ARM_MODEL = {"hm": ("claude-haiku-5-5", "medium"), "om": ("claude-opus-5-5", "medium"), "sm": ("claude-sonnet-5-5", "medium")}
K_TAGS = tuple(ARM_MODEL)                     # the tags whose costs the locked k reads
STEPS_AT_CHOSEN_N = 6


def read_cost_columns(table: Path) -> List[Dict[str, str]]:
    """Only COLUMNS of the compact table, by header name (the `right` column is never parsed into a row)."""
    with open(table, newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        idx = {c: header.index(c) for c in COLUMNS}
        return [{c: line[idx[c]] for c in COLUMNS} for line in rd if line]


def confirmatory_cost_rows(cols: List[Dict[str, str]]) -> Dict[str, object]:
    """{"rows": the rows k_from_rows reads (base_id, shape, setup, cost_usd, kind) for hm / om / sm only, "kept": Counter, "left_out":
    Counter by tag}. A kept row whose model or effort is not its tag's raises."""
    rows, kept, left = [], Counter(), Counter()
    for c in cols:
        cid = parse_custom_id(c["custom_id"])
        tag = str(cid["setup"])
        if tag not in K_TAGS:
            left[tag] += 1
            continue
        if (c["requested_model"], c["effort"]) != ARM_MODEL[tag]:
            raise ValueError(f"{c['custom_id']}: tag {tag} with {c['requested_model']} / {c['effort']}")
        kept[tag] += 1
        rows.append({"base_id": f"{cid['set_id']}-{int(cid['base_index']):03d}", "shape": cid["shape"], "setup": FIVE_TEST_ARMS[tag],
                     "cost_usd": c["cost_usd"] or None, "kind": c["kind"]})
    return {"rows": rows, "kept": kept, "left_out": left}


def k_from_table(table: Path, n: int = STEPS_AT_CHOSEN_N) -> Dict[str, object]:
    cols = read_cost_columns(table)
    sel = confirmatory_cost_rows(cols)
    k = five_tests.k_from_rows(sel["rows"], n=n)                                            # type: ignore[arg-type]
    pieces, chain = scoring.pieces_shape(n), scoring.chain_shape(n)
    return {"k_o": {sh: int(k["opus"][sh]["k"]) for sh in (pieces, chain)}, "k_s": int(k["sonnet"][chain]["k"]),  # type: ignore[index]
            "k_from_rows": k, "n": n, "compact_table_sha256": hashlib.sha256(Path(table).read_bytes()).hexdigest(),
            "rows_kept_by_tag": dict(sel["kept"]), "rows_left_out_by_tag": dict(sel["left_out"]),
            "columns_read": list(COLUMNS)}


def load_k(path: Path) -> Dict[str, object]:
    if not Path(path).is_file():
        raise FileNotFoundError(f"{path}: run `python3 -m harness.analysis.k_step` and commit k.json before the driver (D-93)")
    return json.loads(Path(path).read_text())


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: k is fixed once")
    res = k_from_table(a.run / "compact_table.csv")
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {a.out}: k_o {res['k_o']}, k_s {res['k_s']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
