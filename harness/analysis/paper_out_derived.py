"""Derived values for the claims ledger (rows C-035, C-039, C-040 and C-101): counts and correlations over the stamped per-puzzle and
per-step rows of the Study 1 files, and the stamped values those rows quote beside them, so the ledger can pin one built file instead
of hand arithmetic.

The data output `ledger-derived` (paper_outputs.py writes it as `ledger-derived.json`). Its values are groups. Each group has its own
`tier` cell (a typed label naming one of the four tiers, or the stamped item label when the group's values are stamped values read
as is), then one value per shape (the stamped files' own shape keys, never typed) or named values. Every number is a Cell record of
one of three kinds:
- **a stamped value read as is** (`integer`, or `text_of` for a stamped label; no formula, no check): one ref to the scalar key; `raw`
  is the stamped value. A stamped tier label is printed through the typed mapping `TIER_TEXT`, which keeps its tier and drops the
  internal decision number (the style sheet allows those only in disclosure tables and source fields); `raw` keeps the stamped label.
- **a derived count** (`derive`, printed by `num_d` with 0 decimals): simple arithmetic only (a count, a smallest or a largest value)
  over refs to every scalar stamped value it is computed from, in file order. `formula` says it in words; `check` says it for a
  machine: `{"op": "count" | "count_where" | "min" | "max", "test": [cmp, threshold] (count_where only), "source": <source>,
  "pattern": <key whose "*" segments stand for every child>, "ids": {"source", "key"} (optional)}`. The pattern expands each "*" to
  every child of the stamped node in file order (with `ids`, the one "*" to each id of that stamped list); a row that lacks the
  pattern's last segment is skipped (e.g. the keep-list C9 rows left out for fewer than 2 wrong tries have no vote_at_k_O). The
  threshold is a typed number only for a scale end or a definition's own cut (0 and 100 points; more than 1 wrong try); a design value
  is read from its pinned source instead, as `{"source", "key"}`, and that ref is then the cell's last ref (E3's lead and cap, from
  the locked run plan). The refs must be exactly the pattern's expansion (plus that threshold ref), and the op over their stamped
  values must give `raw`.
- **a correlation** (row C-039 only; check op `corr`): a post hoc derivation from stamped rows, requested for the claims ledger and
  reviewed, and labelled so in its group's tier; no interval and no test. Over the rows of `item_20.<shape>.per_puzzle` with
  wrong_tries >= 2 (the keep-list C9 rule; the build refuses unless their count is C9's stamped n_kept), with x = agreement_share and
  a = accuracy_points: the Pearson correlation of x and a, and the Spearman correlations (the Pearson correlation of average ranks,
  ties sharing their mean rank) of x and a and of x and a * (100 - a), the product taken in double precision as scipy takes it
  (`TRANSFORM_NOTE`: the stamped accuracies carry floating-point noise, so the product decides some ties; the 4-decimal value of
  that one correlation depends on it, its 2-decimal value does not). The refs are every row's wrong_tries (the filter), then every
  kept row's agreement_share, then every kept row's accuracy_points, in file order. `raw` is the full float; `printed` goes through
  the shared formatter (`fmt_fixed`: half away from zero on the decimal, U+2212 minus, one more decimal if rounding would reach 0) at
  2 decimals, the precision C-039 quotes and the only one printed (Edith's Q10 ruling: the 4-decimal form depends on the arithmetic).
  Its check: `{"op": "corr", "kind", "source", "rows", "filter": {"field", "test"}, "x", "a", "dp"}`.

`recheck(S, values)` repeats every number from its refs and the pinned sources alone, and checks every printed form and every stamped
raw value. For counts it expands the pattern itself (the builder walks the rows its own way) but shares `op_fn`, the meaning of each
op, with the builder. For correlations it is a second implementation: exact rational arithmetic for the ranks (counted, not sorted),
means and sums, and a 50-digit decimal square root, against the builder's floating-point path (it shares only the definition's
double-precision product a * (100 - a)); `raw` must agree within 1e-12 and the printed form must be the exact value's rounding.
The builder runs it on its own output and refuses to return on any problem. The shared provenance audit in paper_outputs.py also
reads this file: every ref must resolve in its pinned source, and a one-ref cell with no formula must hold the stamped value as its
raw value.

Standard library only. No model or API call.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any, Callable, Dict, Iterator, List, Sequence, Tuple

from .paper_out_core import (Cell, KeyMissing, Ref, Source, Store, data_output, dec, derive, dumps, fmt_fixed, guarded_dp, integer,
                             join_key, label, num_d, parse_key, register_source, text_of)

# The locked Study 1 run plan (its e3 block: step positions, first-round calls, lead, cap), pinned at the commit on main that last
# changed it; the same SHA-256 is listed in ops/lock/LOCK-MANIFEST.md.
RUN_PLAN = register_source(Source("main_plan", "data/plans/main-l14n6-1-plan-all.json", "7c8bb4b",
                                  "3d173b387bc65810433e2850c06c724855aa40634d724a350bc2aa7d57f6f40e",
                                  what="Study 1 main run plan as locked (step voting: step positions, first-round calls, lead, cap)"))
E3_PLAN = ("e3",)

LEFT_OUT = "fewer than 2 wrong tries"      # the stamped reason a keep-list C9 row has no vote (a string match, not a value)
E3_ARM = "e3"                              # the arm's key prefix in the stamped files (e.g. counts.five_test_arms['e3 1x6'])

# The stamped groupc item label, printed with its tier but without the internal decision number (typed: an exact match is required),
# in the words of Edith's Q19 ruling for every group C row.
GROUPC_TIER = ("pre-specified descriptive (keep-list definitions stamped before the data; computed after the confirmatory results were "
               "opened)")
TIER_TEXT = {
    "pre-specified descriptive (definition fixed and timestamped before the data, D-93 stamp; computed after the confirmatory results "
    "were opened, because it was not in the stamped driver)": GROUPC_TIER,
}

NOTE = ("derived values for the claims ledger: each group carries its own tier; each derived number carries its refs (every stamped "
        "value it uses), its formula in words and a machine check that recomputes it from the refs; each stamped number is read as is "
        "(one ref, no formula)")
TIER_C9_COUNT = ("post hoc count from the keep-list C9 rows: chosen after the results were opened, and not part of keep-list C9's "
                 "stamped definition (a Spearman correlation); the rows counted are C9's stamped per-puzzle rows, which are "
                 + GROUPC_TIER)
TIER_C7_E3 = ("post hoc count: step voting's stamped per-puzzle results on the puzzles of keep-list C7's lowest single-try bin on "
              "chains, the only shape step voting ran on in the main run")
TIER_E3_STEPS = ("post hoc count over the stamped per-step rows of the main run's step voting on chains (the draws actually made, not "
                 "the offline fixed-three simulation's draws)")
TIER_E3_DRAWS = ("pre-specified descriptive, read as is: the step-voting calls made in the main run (one call is one draw for one "
                 "step); the build refuses unless the per-step draws add up to it")
TIER_E3_DESIGN = ("pre-specified design values, read as is from the locked run plan: the lead a step's vote needs (the first round "
                  "draws that many for every step, so it is also the fewest draws a step can end with) and the cap on draws per step")
TIER_THIRDS = ("pre-specified descriptive: the smallest and largest of the lookup chart's stamped third sizes (simple arithmetic, no "
               "estimate)")

TESTS: Dict[str, Callable[[float, float], bool]] = {"==": lambda v, t: v == t, "<": lambda v, t: v < t, ">": lambda v, t: v > t}

C9 = ("item_C9", "shapes")
C7 = ("item_C7", "shapes")
I20 = ("reporting", "group_b", "item_20")
I21 = ("reporting", "group_b", "item_21")
E3_DRAWS_KEY = join_key("reporting", "group_b", "item_16", E3_ARM, "calls_made")


# ---------------------------------------------------------------- derived cells and their machine check


def _as_int(x: float) -> int:
    if float(x) != int(x):
        raise ValueError(f"{x!r} is not a whole number")
    return int(x)


def _ref_threshold(check: Dict[str, Any]) -> bool:
    return check["op"] == "count_where" and isinstance(check["test"][1], dict)


def op_fn(check: Dict[str, Any]) -> Callable[..., int]:
    """The function a check's op names, over the stamped values (as floats) of its refs (a stamped threshold is the last one)."""
    op = check["op"]
    if op == "count":
        return lambda *v: len(v)
    if op == "count_where":
        cmp_, t = check["test"]
        f = TESTS[cmp_]
        if _ref_threshold(check):
            return lambda *v: sum(1 for x in v[:-1] if f(x, v[-1]))
        return lambda *v: sum(1 for x in v if f(x, t))
    if op in ("min", "max"):
        g = min if op == "min" else max

        def extreme(*v: float) -> int:
            if not v:
                raise ValueError(f"{op} of no values")
            return _as_int(g(v))
        return extreme
    raise ValueError(f"unknown op {op!r}")


def _derived(formula: str, check: Dict[str, Any], refs: Sequence[Ref]) -> Dict[str, Any]:
    """A derived count (or smallest/largest value): `derive` over every referenced stamped value (and, last, the stamped threshold
    if the check reads one), printed with 0 decimals, plus its machine check."""
    refs = list(refs)
    if _ref_threshold(check):
        refs.append(check.pop("_threshold"))
    rec = num_d(derive(formula, op_fn(check), *refs), dp=0).record()
    rec["check"] = check
    return rec


def _check(op: str, source: str, pattern: Sequence[str], test: Any = None, ids: Any = None) -> Dict[str, Any]:
    """A check; a stamped threshold (a Ref) is recorded by its source and key, and handed to `_derived` as the cell's last ref."""
    c: Dict[str, Any] = {"op": op, "source": source, "pattern": join_key(*pattern)}
    if test is not None:
        cmp_, t = test
        if isinstance(t, Ref):
            c["_threshold"] = t
            t = t.prov()
        c["test"] = [cmp_, t]
    if ids is not None:
        c["ids"] = {"source": ids[0], "key": ids[1]}
    return c


def expand(S: Store, check: Dict[str, Any]) -> List[str]:
    """The keys a check's pattern names, in file order. A missing segment refuses, except the last one (a row without the field)."""
    src = check["source"]
    segs = parse_key(check["pattern"])
    ids = None
    if "ids" in check:
        ids = S.get(check["ids"]["source"], check["ids"]["key"])
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            raise TypeError(f"{check['ids']}: not a stamped list of ids")
        if segs.count("*") != 1:
            raise ValueError(f"{check['pattern']}: a check with ids has exactly one '*'")
    if not segs or segs[0] == "*":
        raise ValueError(f"{check['pattern']}: a pattern starts with a named key")
    out: List[str] = []

    def walk(done: List[str], rest: List[str]) -> None:
        if not rest:
            out.append(join_key(*done))
            return
        head, tail = rest[0], rest[1:]
        if head == "*":
            node = S.get(src, join_key(*done))
            if ids is not None:
                kids = list(ids)
                missing = [k for k in kids if not (isinstance(node, dict) and k in node)]
                if missing:
                    raise KeyMissing(f"{src}:{join_key(*done)}: no entry for ids {missing[:5]}")
            elif isinstance(node, dict):
                kids = list(node)
            elif isinstance(node, list):
                kids = [str(i) for i in range(len(node))]
            else:
                raise KeyMissing(f"{src}:{join_key(*done)} has no children")
            for k in kids:
                walk(done + [k], tail)
        elif S.has(src, join_key(*done, head)):
            walk(done + [head], tail)
        elif tail:
            raise KeyMissing(f"{src}:{join_key(*done, head)} does not resolve")
        # else: this row has no such field; it is not counted

    walk([], segs)
    return out


def _records(doc: Any, path: str) -> Iterator[Tuple[str, Dict[str, Any]]]:
    if isinstance(doc, dict):
        if "printed" in doc and "kind" in doc:
            yield path, doc
            return
        for k, v in doc.items():
            yield from _records(v, f"{path}.{k}")
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from _records(v, f"{path}.{i}")


def _stamped_num(v: Any, where: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"{where} is {v!r}, not a number")
    return float(v)


def _corr_printed(v: Any, dp: int) -> str:
    """A correlation's printed form: the shared formatter, with one more decimal if rounding would reach 0."""
    return fmt_fixed(v, guarded_dp(v, dp, (0.0,)))


# ---------------------------------------------------------------- the recheck's own correlation (exact arithmetic)


def _mid_ranks_exact(v: Sequence[Fraction]) -> List[Fraction]:
    """Average ranks, counted: (values below) + (values equal + 1) / 2."""
    return [Fraction(sum(1 for w in v if w < u)) + Fraction(sum(1 for w in v if w == u) + 1, 2) for u in v]


def _pearson_exact(x: Sequence[Fraction], y: Sequence[Fraction]) -> Decimal:
    n = len(x)
    if n < 2 or n != len(y):
        raise ValueError(f"{n} and {len(y)} values")
    mx, my = sum(x, Fraction(0)) / n, sum(y, Fraction(0)) / n
    sxy = sum(((a - mx) * (b - my) for a, b in zip(x, y)), Fraction(0))
    sxx = sum(((a - mx) ** 2 for a in x), Fraction(0))
    syy = sum(((b - my) ** 2 for b in y), Fraction(0))
    if sxx == 0 or syy == 0:
        raise ValueError("a constant series")
    r2 = sxy * sxy / (sxx * syy)
    with localcontext() as c:
        c.prec = 50
        root = (Decimal(r2.numerator) / Decimal(r2.denominator)).sqrt()
    return root if sxy >= 0 else -root


def _corr_recheck(S: Store, chk: Dict[str, Any], refs: Sequence[Dict[str, str]]) -> Decimal:
    """C-039's correlation from the pinned source alone: rebuilds the expected refs from the stamped rows, then the value exactly."""
    src, rows_key = chk["source"], chk["rows"]
    segs = parse_key(rows_key)
    ids = S.keys(src, rows_key)
    fld, (cmp_, t) = chk["filter"]["field"], chk["filter"]["test"]
    want = [join_key(*segs, pid, fld) for pid in ids]
    kept = [pid for pid, k in zip(ids, want) if TESTS[cmp_](_stamped_num(S.get(src, k), f"{src}:{k}"), t)]
    want += [join_key(*segs, pid, chk["x"]) for pid in kept] + [join_key(*segs, pid, chk["a"]) for pid in kept]
    if [(r["source"], r["key"]) for r in refs] != [(src, k) for k in want]:
        raise ValueError(f"the refs ({len(refs)}) are not every row's {fld}, then the kept rows' {chk['x']} and {chk['a']} "
                         f"({len(want)}) in file order")
    xf = [_stamped_num(S.get(src, join_key(*segs, pid, chk["x"])), "x") for pid in kept]
    af = [_stamped_num(S.get(src, join_key(*segs, pid, chk["a"])), "a") for pid in kept]
    x, a = ([Fraction(Decimal(repr(float(v)))) for v in xf],        # the stamped floats as written (dec() cuts at 12 digits for
            [Fraction(Decimal(repr(float(v)))) for v in af])       # printing; the Opus check, S1)
    kind = chk["kind"]
    if kind == "pearson_x_vs_a":
        return _pearson_exact(x, a)
    if kind == "spearman_x_vs_a":
        return _pearson_exact(_mid_ranks_exact(x), _mid_ranks_exact(a))
    if kind == "spearman_x_vs_a_times_100_minus_a":
        # The transform is the definition's double-precision product (as the builder and scipy compute it), taken exactly from
        # there on: see TRANSFORM_NOTE.
        return _pearson_exact(_mid_ranks_exact(x), _mid_ranks_exact([Fraction(v * (100.0 - v)) for v in af]))
    raise ValueError(f"unknown correlation {kind!r}")


def recheck(S: Store, values: Any) -> List[str]:
    """Recomputes every number of a ledger-derived `values` document (as written, i.e. parsed from its JSON) from its refs and the
    pinned sources alone; checks each printed form. Counts: the pattern is expanded here, not by the builder's row walks, and `op_fn`
    gives the op's meaning. Correlations: a second implementation in exact arithmetic. Returns the problems (an empty list is a
    pass)."""
    problems: List[str] = []
    for path, rec in _records(values, "values"):
        if rec["kind"] == "label":
            continue
        if rec["kind"] != "num":
            problems.append(f"{path}: kind {rec['kind']!r}")
            continue
        refs = rec.get("refs") or []
        if not refs:
            problems.append(f"{path}: a number with no refs")
            continue
        try:
            stamped = [S.get(r["source"], r["key"]) for r in refs]
        except Exception as x:                                              # noqa: BLE001
            problems.append(f"{path}: a ref does not resolve ({x})")
            continue
        chk = rec.get("check")
        if chk is None:
            if len(refs) != 1 or rec.get("formula"):
                problems.append(f"{path}: a value with no check must be one ref read as is (no formula)")
                continue
            v, r = stamped[0], refs[0]
            if type(rec.get("raw")) is not type(v) or rec.get("raw") != v:
                problems.append(f"{path}: raw {rec.get('raw')!r} != stamped {v!r} at {r['source']}:{r['key']}")
                continue
            want = TIER_TEXT.get(v, v) if isinstance(v, str) else integer(Ref(v, r["source"], r["key"])).printed
            if rec["printed"] != want:
                problems.append(f"{path}: printed {rec['printed']!r}, the stamped value prints {want!r}")
            continue
        if not rec.get("formula"):
            problems.append(f"{path}: a derived value with no formula")
        if chk.get("op") == "corr":
            try:
                exact = _corr_recheck(S, chk, refs)
            except Exception as x:                                          # noqa: BLE001
                problems.append(f"{path}: the correlation does not recompute ({x})")
                continue
            raw = rec.get("raw")
            if isinstance(raw, bool) or not isinstance(raw, float) or abs(dec(raw) - exact) > Decimal("1e-12"):
                problems.append(f"{path}: raw {raw!r}, the exact value is {exact}")
            want = _corr_printed(exact, int(chk["dp"]))
            if rec["printed"] != want:
                problems.append(f"{path}: printed {rec['printed']!r}, the exact value prints {want!r}")
            continue
        try:
            keys = expand(S, chk)
        except Exception as x:                                              # noqa: BLE001
            problems.append(f"{path}: the check's pattern does not expand ({x})")
            continue
        want_refs = [(chk["source"], k) for k in keys]
        if _ref_threshold(chk):
            want_refs.append((chk["test"][1]["source"], chk["test"][1]["key"]))
        if [(r["source"], r["key"]) for r in refs] != want_refs:
            problems.append(f"{path}: the refs ({len(refs)}) are not the pattern's expansion and threshold ({len(want_refs)}) in "
                            f"order")
            continue
        try:
            value = op_fn(chk)(*[_stamped_num(v, f"{r['source']}:{r['key']}") for v, r in zip(stamped, refs)])
        except Exception as x:                                              # noqa: BLE001
            problems.append(f"{path}: the check does not run ({x})")
            continue
        if not isinstance(rec.get("raw"), int) or isinstance(rec.get("raw"), bool) or rec["raw"] != value:
            problems.append(f"{path}: raw {rec.get('raw')!r}, the check gives {value!r}")
        if rec["printed"] != fmt_fixed(value, 0):
            problems.append(f"{path}: printed {rec['printed']!r}, the check prints {fmt_fixed(value, 0)!r}")
    return problems


# ---------------------------------------------------------------- keep-list C9 rows (C-035, C-040)


def _c9_kept(S: Store, sh: str) -> List[str]:
    """The ids of the per_puzzle rows that have a vote. Every other row must be a stamped 'fewer than 2 wrong tries' row; both counts
    must equal the stamped n_kept and n_left_out; each kept row's vote_gain sign must be that of vote_at_k_O - single_try."""
    where = f"groupc:{join_key(*C9, sh, 'per_puzzle')}"
    rows = S.get("groupc", join_key(*C9, sh, "per_puzzle"))
    if not isinstance(rows, dict):
        raise TypeError(f"{where} is not a dict")
    kept, left = [], []
    for pid, row in rows.items():
        if "vote_at_k_O" in row:
            kept.append(pid)
        elif row.get("left_out") == LEFT_OUT and "vote_gain" not in row:
            left.append(pid)
        else:
            raise ValueError(f"{where}.{pid}: neither a vote nor the stamped left_out reason")
    n_kept = S.get("groupc", join_key(*C9, sh, "n_kept"))
    n_left = S.get("groupc", join_key(*C9, sh, "n_left_out"))
    if len(kept) != n_kept or len(left) != n_left:
        raise ValueError(f"{where}: {len(kept)} rows with a vote and {len(left)} left out; stamped n_kept {n_kept!r}, "
                         f"n_left_out {n_left!r}")
    for pid in kept:
        row = rows[pid]
        g = _stamped_num(row["vote_gain"], f"{where}.{pid}.vote_gain")
        d = (_stamped_num(row["vote_at_k_O"], f"{where}.{pid}.vote_at_k_O") -
             _stamped_num(row["single_try"], f"{where}.{pid}.single_try"))
        if (g > 0) != (d > 0) or (g < 0) != (d < 0):
            raise ValueError(f"{where}.{pid}: vote_gain's sign differs from vote_at_k_O - single_try")
    return kept


def _tier_of(S: Store, key: str) -> Dict[str, Any]:
    """A stamped groupc item label as a tier cell, printed through TIER_TEXT."""
    return text_of(S.ref("groupc", key), mapping=TIER_TEXT).record()


def _c9(S: Store) -> Dict[str, Any]:
    n_kept: Dict[str, Any] = {"tier": _tier_of(S, "item_C9.label")}
    zero: Dict[str, Any] = {"tier": label(TIER_C9_COUNT).record()}
    hundred: Dict[str, Any] = {"tier": label(TIER_C9_COUNT).record()}
    vs_single: Dict[str, Any] = {"tier": label(TIER_C9_COUNT).record()}
    for sh in S.keys("groupc", join_key(*C9)):
        kept = _c9_kept(S, sh)
        n_kept[sh] = integer(S.ref("groupc", join_key(*C9, sh, "n_kept"))).record()
        rows = "every row of this per_puzzle that has one (the rows left out for fewer than 2 wrong tries have none)"
        vote_refs = [S.ref("groupc", join_key(*C9, sh, "per_puzzle", pid, "vote_at_k_O")) for pid in kept]
        gain_refs = [S.ref("groupc", join_key(*C9, sh, "per_puzzle", pid, "vote_gain")) for pid in kept]
        vote_pat = (*C9, sh, "per_puzzle", "*", "vote_at_k_O")
        gain_pat = (*C9, sh, "per_puzzle", "*", "vote_gain")
        zero[sh] = _derived(f"count of the referenced vote_at_k_O values (of {rows}) that equal 0",
                            _check("count_where", "groupc", vote_pat, ("==", 0.0)), vote_refs)
        hundred[sh] = _derived(f"count of the referenced vote_at_k_O values (of {rows}) that equal 100",
                               _check("count_where", "groupc", vote_pat, ("==", 100.0)), vote_refs)
        gain = f"the referenced vote_gain values (vote_at_k_O - single_try, in points; of {rows})"
        vs_single[sh] = {
            "below": _derived(f"count of {gain} below 0", _check("count_where", "groupc", gain_pat, ("<", 0.0)), gain_refs),
            "above": _derived(f"count of {gain} above 0", _check("count_where", "groupc", gain_pat, (">", 0.0)), gain_refs),
            "equal": _derived(f"count of {gain} equal to 0", _check("count_where", "groupc", gain_pat, ("==", 0.0)), gain_refs),
        }
        parts = [vs_single[sh][k]["raw"] for k in ("below", "above", "equal")]
        if sum(parts) != n_kept[sh]["raw"]:
            raise ValueError(f"groupc:{join_key(*C9, sh)}: below + above + equal {parts} is not n_kept {n_kept[sh]['raw']!r}")
    return {"c9_n_kept": n_kept, "c9_vote_zero": zero, "c9_vote_100": hundred, "c9_vote_vs_single": vs_single}


# ---------------------------------------------------------------- E3 on keep-list C7's hardest bin (C-101)


def _e3_shape(S: Store) -> str:
    """The one shape E3 ran on, read from the stamped arm keys ('e3 1x6')."""
    shapes = [k.split(" ", 1)[1] for k in S.keys("main", "counts.five_test_arms") if k.split(" ", 1)[0] == E3_ARM]
    if len(shapes) != 1:
        raise ValueError(f"main:counts.five_test_arms: E3 shapes {shapes}, expected one")
    return shapes[0]


def _c7_hardest(S: Store) -> Dict[str, Any]:
    sh = _e3_shape(S)
    bins = S.get("groupc", join_key(*C7, sh, "bins"))
    lowest = min(b["bin_lower_edge"] for b in bins.values())
    hardest = [k for k, b in bins.items() if b["bin_lower_edge"] == lowest]
    if len(hardest) != 1:
        raise ValueError(f"groupc:{join_key(*C7, sh, 'bins')}: {len(hardest)} bins at the lowest edge")
    hb = hardest[0]
    ids_key = join_key(*C7, sh, "bins", hb, "base_ids")
    ids = S.get("groupc", ids_key)
    n_ref = S.ref("groupc", join_key(*C7, sh, "bins", hb, "puzzles"))
    if len(ids) != n_ref.value or len(set(ids)) != len(ids):
        raise ValueError(f"groupc:{ids_key}: {len(ids)} ids, stamped puzzles {n_ref.value!r}")
    refs = [S.ref("main", join_key(*I21, "e3_lead_by_2_per_base", b)) for b in ids]
    if any(r.value not in (0.0, 100.0) for r in refs):
        raise ValueError(f"main:{join_key(*I21, 'e3_lead_by_2_per_base')}: a value on the hardest bin is neither 0 nor 100")
    right = _derived(
        f"count of the referenced values of item_21.e3_lead_by_2_per_base (E3's per-puzzle result in points, each 0 or 100), one per "
        f"base id of groupc {ids_key} (keep-list C7's bin with the lowest stamped bin_lower_edge), that equal 100",
        _check("count_where", "main", (*I21, "e3_lead_by_2_per_base", "*"), ("==", 100.0), ids=("groupc", ids_key)), refs)
    return {"c7_hardest_bin_n": {"tier": _tier_of(S, "item_C7.label"), sh: integer(n_ref).record()},
            "c7_hardest_bin_e3_right": {"tier": label(TIER_C7_E3).record(), sh: right}}


# ---------------------------------------------------------------- E3's steps and draws in the main run (C-101)


def _plan_int(S: Store, field: str) -> Ref:
    r = S.ref(RUN_PLAN.name, join_key(*E3_PLAN, field))
    if isinstance(r.value, bool) or not isinstance(r.value, int):
        raise TypeError(f"{r.source}:{r.key} is {r.value!r}, not a whole number")
    return r


def _e3_steps(S: Store) -> Dict[str, Any]:
    lead, cap = _plan_int(S, "lead"), _plan_int(S, "cap")
    positions, first = _plan_int(S, "step_positions"), _plan_int(S, "first_round_calls")
    if first.value != lead.value * positions.value or not 0 < lead.value <= cap.value:
        raise ValueError(f"{RUN_PLAN.name}: first_round_calls {first.value} is not lead {lead.value} per step over "
                         f"{positions.value} steps (or the lead is past the cap {cap.value}); the lead is not the fewest draws")
    per_base = S.get("main", join_key(*I21, "per_base"))
    refs: List[Ref] = []
    for b, row in per_base.items():
        for i, step in enumerate(row["steps"]):
            r = S.ref("main", join_key(*I21, "per_base", b, "steps", i, "draws_logged"))
            if isinstance(r.value, bool) or not isinstance(r.value, int) or not lead.value <= r.value <= cap.value:
                raise ValueError(f"main:{r.key} is {r.value!r}, not a whole number of draws from the plan's lead to its cap")
            refs.append(r)
    if len(refs) != positions.value:
        raise ValueError(f"main: item_21 has {len(refs)} steps, the run plan stamps {positions.value} step positions")
    calls = S.ref("main", E3_DRAWS_KEY)
    if sum(r.value for r in refs) != calls.value:
        raise ValueError(f"main: item_21's draws_logged add up to {sum(r.value for r in refs)}, item_16 stamps {calls.value!r} "
                         f"E3 calls made")
    pat = (*I21, "per_base", "*", "steps", "*", "draws_logged")
    steps = ("the referenced draws_logged values: one per step of every base of item_21.per_base (the draws E3 actually made in the "
             "main run's step voting on chains; not the fixed-three simulation's draws_used)")
    plan = f"the run plan's stamped {RUN_PLAN.name}:{lead.key}"
    return {
        "e3_main_steps": {
            "tier": label(TIER_E3_STEPS).record(),
            "steps": _derived(f"count of {steps}", _check("count", "main", pat), refs),
            "steps_at_2_draws": _derived(
                f"count of {steps} that equal {plan} (the lead a step's vote needs; the plan's first round draws that many for every "
                f"step, so it is the fewest draws a step can end with)", _check("count_where", "main", pat, ("==", lead)), refs),
            "steps_at_9_draws": _derived(f"count of {steps} that equal the run plan's stamped {RUN_PLAN.name}:{cap.key} (the cap on "
                                         f"draws per step)", _check("count_where", "main", pat, ("==", cap)), refs),
            "max_draws_per_step": _derived(f"largest of {steps}", _check("max", "main", pat), refs),
        },
        "e3_main_draws": {"tier": label(TIER_E3_DRAWS).record(), "calls_made": integer(calls).record()},
        "e3_design": {"tier": label(TIER_E3_DESIGN).record(), "lead": integer(lead).record(), "cap": integer(cap).record()},
    }


# ---------------------------------------------------------------- item 20's third sizes (C-040)


def _third_refs(S: Store, sh: str) -> List[Ref]:
    bins = S.get("main", join_key(*I20, sh, "bins"))
    refs = [S.ref("main", join_key(*I20, sh, "bins", b, "thirds", t, "n")) for b in bins for t in bins[b]["thirds"]]
    if any(isinstance(r.value, bool) or not isinstance(r.value, int) for r in refs):
        raise TypeError(f"main:{join_key(*I20, sh, 'bins')}: a third's n is not a whole number")
    return refs


def _thirds(S: Store) -> Dict[str, Any]:
    out: Dict[str, Any] = {"tier": label(TIER_THIRDS).record()}
    every = "the referenced n values: one per third of every bin"
    all_refs: List[Ref] = []
    for sh in S.keys("main", join_key(*I20)):
        refs = _third_refs(S, sh)
        all_refs += refs
        pat = (*I20, sh, "bins", "*", "thirds", "*", "n")
        out[sh] = {"min": _derived(f"smallest of {every} of item_20.{sh}", _check("min", "main", pat), refs),
                   "max": _derived(f"largest of {every} of item_20.{sh}", _check("max", "main", pat), refs)}
    pat = (*I20, "*", "bins", "*", "thirds", "*", "n")
    out["both"] = {"min": _derived(f"smallest of {every} of every shape of item_20", _check("min", "main", pat), all_refs),
                   "max": _derived(f"largest of {every} of every shape of item_20", _check("max", "main", pat), all_refs)}
    return {"item20_third_sizes": out}


# ---------------------------------------------------------------- item 20's correlations (C-039; requested and reviewed)

TIER_CORR = ("post hoc derivation from stamped rows: a correlation over the lookup chart's stamped per-puzzle rows, computed after "
             "the results were opened (requested for the claims ledger; reviewed); no interval, no test; printed to two decimals, the "
             "precision quoted, since a four-decimal form would depend on how the arithmetic is done")
CORR_KINDS = ("pearson_x_vs_a", "spearman_x_vs_a", "spearman_x_vs_a_times_100_minus_a")
CORR_FILTER = ("wrong_tries", (">", 1))    # keep-list C9's rule: rows with fewer than 2 wrong tries are left out
CORR_X, CORR_A = "agreement_share", "accuracy_points"
CORR_DP = 2                                # the precision C-039 quotes, and the only one printed (Edith's Q10 ruling)
# The stamped accuracy_points carry floating-point noise (e.g. 27.500000000000004 for 11 of 40 tries right), so the ties of
# a * (100 - a) depend on how the product is evaluated. The reviewed values use the double-precision product (as scipy does); the
# 2-decimal forms are the same under exact arithmetic on the stamped decimals or on the true fractions of tries, the 4-decimal forms
# are not (0.5024 / 0.5041 / 0.5027 on chains, -0.0410 / -0.0406 / -0.0426 on pieces).
TRANSFORM_NOTE = ("a * (100 - a) is the double-precision product of the stamped floats (as scipy computes it); the stamped accuracies "
                  "carry floating-point noise, so this product decides some ties")


def _avg_ranks(v: Sequence[float]) -> List[float]:
    """1-based ranks, ties given their average rank (as scipy.stats.rankdata's 'average')."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    ranks = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def _pearson(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    mx, my = math.fsum(x) / n, math.fsum(y) / n
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.fsum((a - mx) ** 2 for a in x)
    syy = math.fsum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def corr_value(kind: str, x: Sequence[float], a: Sequence[float]) -> float:
    """The builder's correlation (floating point): Pearson of x and a; Spearman (Pearson of average ranks) of x and a, and of x and
    a * (100 - a)."""
    if kind == "pearson_x_vs_a":
        return _pearson(x, a)
    if kind == "spearman_x_vs_a":
        return _pearson(_avg_ranks(x), _avg_ranks(a))
    if kind == "spearman_x_vs_a_times_100_minus_a":
        return _pearson(_avg_ranks(x), _avg_ranks([v * (100.0 - v) for v in a]))
    raise ValueError(f"unknown correlation {kind!r}")


def _corr_cell(kind: str, value: float, refs: Sequence[Ref], rows_key: str, dp: int) -> Dict[str, Any]:
    fld, test = CORR_FILTER
    formula = (f"{kind} over the rows of {rows_key} with {fld} >= 2 (x = {CORR_X}, a = {CORR_A}; Spearman = Pearson of average "
               f"ranks); refs: every row's {fld}, then the kept rows' {CORR_X}, then their {CORR_A}, in file order")
    if kind == "spearman_x_vs_a_times_100_minus_a":
        formula += f"; {TRANSFORM_NOTE}"
    rec = Cell(_corr_printed(value, dp), raw=value, refs=tuple(refs), formula=formula).record()
    rec["check"] = {"op": "corr", "kind": kind, "source": "main", "rows": rows_key, "filter": {"field": fld, "test": list(test)},
                    "x": CORR_X, "a": CORR_A, "dp": dp}
    return rec


def _corr(S: Store) -> Dict[str, Any]:
    out: Dict[str, Any] = {"tier": label(TIER_CORR).record()}
    fld, (cmp_, t) = CORR_FILTER
    for sh in S.keys("main", join_key(*I20)):
        rows_key = join_key(*I20, sh, "per_puzzle")
        rows = S.get("main", rows_key)
        if not isinstance(rows, dict):
            raise TypeError(f"main:{rows_key} is not a dict")
        wt = [S.ref("main", join_key(*I20, sh, "per_puzzle", pid, fld)) for pid in rows]
        kept = [pid for pid, r in zip(rows, wt) if TESTS[cmp_](_stamped_num(r.value, f"main:{r.key}"), t)]
        n_kept = S.get("groupc", join_key(*C9, sh, "n_kept"))
        if len(kept) != n_kept:
            raise ValueError(f"main:{rows_key}: {len(kept)} rows with {fld} >= 2, keep-list C9 stamps n_kept {n_kept!r}")
        xs = [S.ref("main", join_key(*I20, sh, "per_puzzle", pid, CORR_X)) for pid in kept]
        as_ = [S.ref("main", join_key(*I20, sh, "per_puzzle", pid, CORR_A)) for pid in kept]
        x = [_stamped_num(r.value, f"main:{r.key}") for r in xs]
        a = [_stamped_num(r.value, f"main:{r.key}") for r in as_]
        refs = wt + xs + as_
        cell: Dict[str, Any] = {"n": _derived(f"count of item_20.{sh}'s per-puzzle rows with {fld} >= 2 (more than 1)",
                                              _check("count_where", "main", (*I20, sh, "per_puzzle", "*", fld), (cmp_, t)), wt)}
        for kind in CORR_KINDS:
            cell[kind] = _corr_cell(kind, corr_value(kind, x, a), refs, rows_key, CORR_DP)
        out[sh] = cell
    return {"item20_corr": out}


# ---------------------------------------------------------------- the output


@data_output("ledger-derived")
def ledger_derived(S: Store) -> Dict[str, Any]:
    values = {"note": label(NOTE).record(), **_c9(S), **_c7_hardest(S), **_e3_steps(S), **_thirds(S), **_corr(S)}
    problems = recheck(S, json.loads(dumps(values)))
    if problems:
        raise ValueError(f"ledger-derived: recheck failed ({len(problems)}):\n  " + "\n  ".join(problems[:20]))
    return values
