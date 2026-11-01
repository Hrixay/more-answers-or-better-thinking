"""From the main run's call log to the scored rows the LOCKED analysis reads (five_tests, scoring, fairness_input). Plumbing only: it makes
no analysis choice of its own. Every mapping below cites where it comes from.

    rows = main_rows.build(set_dir, [run_folder / "calls.jsonl"])     # {"tests": [...], "other": [...], "e3": [...]}

Input: the FINAL records of `calls.jsonl` (`harness/pareto/client.py` writes one per finished call; batch.py's errored, expired or
canceled items are not final and are never billed or scored) and the frozen set (`data/tasks/<set>`). The answer keys and key states
are READ from the frozen items by `meta.item_id`, never recomputed (Edith, main-analysis review spec (2)).

One row per final record:
- `base_id` = "<set_id>-<base index, 3 digits>": the set and base puzzle, as in the simulated datasets' (set_id, base_id) pair and in
  `harness/pareto/e3.e3_rows`, so one base puzzle is one key in every arm (Edith (2)).
- `shape` = "<width>x<depth>" from the record's meta (pilot/main build_requests; kscript.parse_custom_id gives the same).
- `setup`: the main runner's tag mapped to the five_tests arm names (`five_tests.tests_for`): hm -> "haiku-med", om -> "opus-med",
  ol -> "opus-low", sm -> "sonnet-med" (`FIVE_TEST_ARMS`). E3 rows come from `harness.pareto.e3.e3_rows` (setup "e3"), unchanged.
  Every other tag (hl, sl, ho, hx, the D-42 arm hv, and the real-time rt* tags) keeps its own name (`OTHER_ARMS`) and goes in
  `other`, never into the five tests (Edith (2); D-91: D-42 is outside the confirmatory family; D-35: the real-time subset is a
  latency check).
- `kind`, `stop_reason`, `refusal_category`, `error`: copied from the record as logged. scoring._dropped reads exactly these: the
  refusals_out view drops `stop_reason == "refusal"` or a block (`harness/pareto/table.is_block`: kind "refusal", or kind "error" whose
  `error` names a safety or policy reason); truncations_out drops `kind == "truncated"` or `stop_reason == "max_tokens"`. A kind that
  is not "answered" is scored wrong and votes for nothing (scoring.grade_1x24 / grade_24x1 with `kind`; scoring.vote_key).
- `cost_usd`: the record's own string, as logged (k_from_rows sums it exactly; a missing cost counts 0 and is reported there).
- the score fields: at the chain shape (1xN) `scoring.grade_1x24(answer_text, key states, lines, kind, answer_only)`, which writes the
  D-76 fields and, under D-90, `correct_original` / `format_status_original` (the official rule is the default `repeats`); at the pieces
  shape (Nx1) `scoring.grade_24x1(answer_text, key answer, lines, kind)`, which writes `answer_key`, `correct` and `pieces_right`.
  `answer_only` is True only for an item frozen with the answer-only prompt (style "d31-answer-only", D-36(5); choose_preset reads it
  the same way); the main set has none.
- `sample` (the try number from meta), `item_id`, `set_id`, `preset` (the set's setting), `line_count`, `model`, `effort`, `tag`.
Missing tries (D-48 row 23, Edith's readiness item 1): with `planned` (the run's own request list, rebuilt by `planned_requests` and
checked against the run manifest's `item_set_sha256`), every planned single-call try with no final record becomes a row of kind
"missing" (the locked scorers called with kind "missing": correct False, format_status "missing", no answer), which every view keeps
(scoring._dropped drops only refusals, blocks and truncations); and every base chain whose E3 steps are not all done gets an E3 row
with each unfinished step wrong. Missing rows are not calls: k is computed without them (main_analysis).
Nothing here reads a row's accuracy; it only computes the locked scorers' fields.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import scoring

FIVE_TEST_ARMS = {"hm": "haiku-med", "om": "opus-med", "ol": "opus-low", "sm": "sonnet-med"}   # five_tests.tests_for's arm names
OTHER_ARMS = {"hl": "haiku-low", "sl": "sonnet-low", "ho": "haiku-thinking-off", "hx": "haiku-max", "hv": "haiku-med-d42-variant",
              "rthm": "rt-haiku-med", "rtom": "rt-opus-med", "rtsm": "rt-sonnet-med"}
E3_TAG = "es"
ANSWER_ONLY_STYLE = "d31-answer-only"         # choose_preset.ANSWER_ONLY_STYLE


def load_set(set_dir: Path) -> Tuple[Dict, Dict[str, Dict]]:
    """(manifest, {item_id: item}) of a frozen set, read as stored (no re-generation)."""
    set_dir = Path(set_dir)
    man = json.loads((set_dir / "manifest.json").read_text())
    items = [json.loads(ln) for ln in (set_dir / "items.jsonl").read_text().splitlines() if ln.strip()]
    return man, {it["id"]: it for it in items}


def final_records(paths: Iterable[Path]) -> List[Dict[str, object]]:
    """The final records of one or more call logs, in file order. Two final records for one custom_id raise."""
    out: List[Dict[str, object]] = []
    seen = set()
    for path in paths:
        with open(path) as f:
            for ln in f:
                if not ln.strip():
                    continue
                rec = json.loads(ln)
                if not rec.get("final"):
                    continue
                cid = str(rec.get("custom_id"))
                if cid in seen:
                    raise ValueError(f"{cid}: two final records")
                seen.add(cid)
                out.append(rec)
    return out


def all_records(paths: Iterable[Path]) -> Iterable[Dict[str, object]]:
    """Every line of the call logs (final records and the batch / pause lines), in file order."""
    for path in paths:
        with open(path) as f:
            for ln in f:
                if ln.strip():
                    yield json.loads(ln)


def score_row(rec: Mapping[str, object], item: Mapping[str, object], setup: str) -> Dict[str, object]:
    """One final record of a single-call arm as a scored row (see the module text for every field)."""
    meta = rec.get("meta") or {}
    width, depth = int(item["width"]), int(item["depth"])                                  # type: ignore[call-overload]
    if (int(meta.get("width")), int(meta.get("depth"))) != (width, depth):                # type: ignore[call-overload, arg-type]
        raise ValueError(f"{rec.get('custom_id')}: the record's shape differs from its item's")
    kind = str(rec.get("kind"))
    text = str(rec.get("answer_text") or "")
    lines = int(item["params"]["lines"])                                                  # type: ignore[index]
    row: Dict[str, object] = {
        "base_id": f"{meta['set_id']}-{int(meta['base_index']):03d}", "set_id": meta["set_id"], "item_id": meta["item_id"],  # type: ignore[index, call-overload]
        "preset": meta.get("setting"), "shape": f"{width}x{depth}", "setup": setup, "tag": meta.get("setup"),             # type: ignore[union-attr]
        "sample": meta.get("sample"), "model": rec.get("requested_model"), "effort": rec.get("effort"), "line_count": lines,  # type: ignore[union-attr]
        "kind": kind, "stop_reason": rec.get("stop_reason"), "refusal_category": rec.get("refusal_category"),
        "cost_usd": rec.get("cost_usd"), "custom_id": rec.get("custom_id")}
    if rec.get("error") is not None:
        row["error"] = rec.get("error")
    if depth > 1:
        g = scoring.grade_1x24(text, item["chains"][0]["states"], lines, kind=kind,                                   # type: ignore[index]
                               answer_only=item.get("style") == ANSWER_ONLY_STYLE)
    else:
        g = scoring.grade_24x1(text, item["answer"], lines, kind=kind)                                               # type: ignore[arg-type]
    row.update(g)
    return row


def planned_requests(man: Mapping[str, object], items: Sequence[Dict], extras: Sequence[str], d42: bool = True) -> List[tuple]:
    """The run's single-call and real-time requests, rebuilt by the runner's own builders (main.build_main_requests, build_rt_requests)."""
    from ..pareto.main import build_main_requests, build_rt_requests
    return build_main_requests(dict(man), list(items), extras, d42) + build_rt_requests(dict(man), list(items))


def check_planned(run_dir: Path, planned: Sequence[tuple]) -> None:
    """Raise unless the rebuilt request list is exactly the one the run's manifest recorded (manifest.item_set_hash)."""
    from ..pareto.manifest import item_set_hash
    man = json.loads((Path(run_dir) / "manifest.json").read_text())
    if man.get("item_set_sha256") != item_set_hash(planned) or int(man.get("n_items", -1)) != len(planned):
        raise ValueError(f"the rebuilt request list does not match {run_dir}/manifest.json (item_set_sha256, n_items): wrong extras or set?")


def missing_row(cid: str, meta: Mapping[str, object], item: Mapping[str, object], setup: str) -> Dict[str, object]:
    """A planned try with no final record, scored by the locked scorers with kind "missing" (wrong, votes for nothing)."""
    rec = {"custom_id": cid, "kind": "missing", "stop_reason": None, "refusal_category": None, "cost_usd": None, "answer_text": None,
           "requested_model": meta.get("model"), "effort": meta.get("effort"), "meta": dict(meta)}
    return score_row(rec, item, setup)


def _e3_missing_rows(man: Mapping[str, object], items: Mapping[str, Dict], e3_recs: Sequence[Mapping[str, object]],
                     have_rows: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    """An E3 row (kind "missing") for every base chain with no complete row: done steps keep their voted result, open or never-drawn
    steps are wrong."""
    from ..pareto import e3 as e3mod
    steps = e3mod.chain_steps([(dict(man), list(items.values()))])
    draws = e3mod.draws_by_step(e3_recs)
    done_items = {str(r["item_id"]) for r in have_rows}
    chains: Dict[str, List] = {}
    for st in steps:
        chains.setdefault(st.item_id, []).append(st)
    out: List[Dict[str, object]] = []
    for item_id, ch in sorted(chains.items()):
        if item_id in done_items:
            continue
        ch = sorted(ch, key=lambda x: x.k)
        correct, calls = [], 0
        for st in ch:
            d = draws.get((item_id, st.k))
            if not d:
                correct.append(False)
                continue
            state = e3mod.step_state(st, d)
            calls += len(d)
            correct.append(bool(state["done"]) and state["answer"] is not None and state["answer"] == st.truth)
        first = ch[0]
        out.append({"base_id": f"{first.set_id}-{first.base_index:03d}", "set_id": first.set_id, "item_id": item_id,
                    "shape": f"1x{len(ch)}", "setup": "e3", "kind": "missing", "stop_reason": None, "step_correct": correct,
                    "correct": False, "cost_usd": None, "calls": calls})
    return out


def build(set_dir: Path, logs: Sequence[Path], records: Optional[Sequence[Mapping[str, object]]] = None,
          planned: Optional[Sequence[tuple]] = None) -> Dict[str, List[Dict[str, object]]]:
    """{"tests": the five_tests rows (four single-call arms plus E3), "other": every other arm's rows, "e3": the E3 rows (also in
    "tests")}. Every final record of the set's items is placed exactly once; a record of an unknown tag, or of an item not in the set,
    raises (so nothing is silently dropped)."""
    from ..pareto import e3 as e3mod
    man, items = load_set(set_dir)
    recs = list(records) if records is not None else final_records(logs)
    tests: List[Dict[str, object]] = []
    other: List[Dict[str, object]] = []
    e3_recs: List[Mapping[str, object]] = []
    for rec in recs:
        meta = rec.get("meta") or {}
        tag = str(meta.get("setup"))                                                       # type: ignore[union-attr]
        item = items.get(str(meta.get("item_id")))                                         # type: ignore[union-attr]
        if item is None:
            raise ValueError(f"{rec.get('custom_id')}: item {meta.get('item_id')!r} is not in {man['set_id']}")      # type: ignore[union-attr]
        if tag == E3_TAG:
            e3_recs.append(rec)
        elif tag in FIVE_TEST_ARMS:
            tests.append(score_row(rec, item, FIVE_TEST_ARMS[tag]))
        elif tag in OTHER_ARMS:
            other.append(score_row(rec, item, OTHER_ARMS[tag]))
        else:
            raise ValueError(f"{rec.get('custom_id')}: unknown setup tag {tag!r}")
    e3_rows = e3mod.e3_rows([(man, list(items.values()))], e3_recs) if e3_recs else []
    missing: List[Dict[str, object]] = []
    if planned is not None:
        finals = {str(r.get("custom_id")) for r in recs}
        for cid, _params, meta in planned:
            if cid in finals:
                continue
            tag = str(meta["setup"])
            name = FIVE_TEST_ARMS.get(tag) or OTHER_ARMS.get(tag)
            if name is None:
                raise ValueError(f"{cid}: unknown planned setup tag {tag!r}")
            row = missing_row(cid, meta, items[str(meta["item_id"])], name)
            (tests if tag in FIVE_TEST_ARMS else other).append(row)
            missing.append(row)
        e3_missing = _e3_missing_rows(man, items, e3_recs, e3_rows)
        e3_rows = e3_rows + e3_missing
        missing += e3_missing
    return {"tests": tests + e3_rows, "other": other, "e3": e3_rows, "missing": missing}
