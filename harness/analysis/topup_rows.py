"""The top-up run's converter (`topup_rows`; spec `research/topup-run-spec.md` at 9c007e5, Edith CLEAN, section 4a-4c, with Edith's
rulings on the runner, `ops/reviews/2026-10-13-topup-spec-r1.md`): the top-up run's FINAL call-log records and the main run's call log
in, rows out. Plumbing only: every row is graded by the LOCKED scorers (`main_rows.score_row`, which calls `scoring.grade_1x24` /
`grade_24x1` with the D-76 rules and D-90's repeat rule; `harness/pareto/e3.py`'s `e3_rows`, `step_state`, `draws_by_step`), and every
E2 / picker state is read by the runner's own pure functions (`topup.e2_puzzle`, `team_prompts.parse_pick` through `topup.team_prompts`).
It never writes anything, never touches Study 1's outputs and never changes `main_rows`.

The mappings (each cites the spec):
- **E2, the Haiku team** (4b): one row per puzzle (setup "e2"). `topup.e2_puzzle` rebuilds the planner, the helpers' votes and the
  aggregator from the final records. stage "done": the aggregator's reply graded by `main_rows.score_row` for its shape (the team's
  answer). stage "plan_failed" (`team_prompts.parse_plan` finds no exact Task 1..6, or the planner did not answer: Edith's ruling 2, a
  refused or truncated planner is plan_failed): graded with kind "plan_failed" by the same scorer, so it is wrong as deployed, with the
  planner's kind and stop_reason on the row. Any other stage (the run did not finish that puzzle): `main_rows.missing_row` (kind
  "missing", wrong). The tasks' draws, status, agreed result (`answer`, the voted state key or None) and "(no result)" places are
  copied from `e2_puzzle` (at pieces a task with no result stays at its own place: Edith's ruling 4; at chain the later tasks are never
  started), with each draw's vote key (`votes`, `e3.record_vote`; Edith code r1 T-D2, spec 4b "the helpers' draws and agreed result").
- **H-pick8, the picker** (4b, 4c): one row per puzzle (setup "h-pick8"): the parsed pick k (1-8 or None) and the joined main-run row
  of Haiku-medium sample k. `correct` is that row's official score (`scoring.row_correct`); no pick (unparseable, refused, truncated,
  missing) is wrong; a pick of a sample that did not answer is that sample's row, which is wrong.
- **C13, step voting on pieces** (4b; Edith's spec note 1 and ruling 7): the locked `e3.e3_rows` run on the runner's OWN step list for the pieces items
  (`topup.c13_steps`: piece s = 1..6 built with `ledger.step_call(p, s, 1)`), so each row's `step_correct` is per piece. `e3_rows` labels
  a depth-1 puzzle "1x1"; the row is relabelled with its real shape "<width>x1" (6x1). Scored as the PRODUCT of the per-piece accuracies
  (F7) by `five_tests.e3_arm_scores`, exactly as chains. An unfinished pieces puzzle is a missing row as `main_rows._e3_missing_rows`
  makes one for chains: done pieces keep their voted result, open or never-drawn pieces are wrong.
- **The same-model check** (4b, section 3): one row per planned call (`topup.same_model_items`), graded as Haiku-medium rows are
  (`main_rows.score_row`), setup "same-model-check" so it can never be read as a Study 1 arm; a planned try with no final record is a
  missing row (wrong).
- **The main run's rows** (4c): `main_rows.build` on the main run's call log with the planned list rebuilt by
  `main_rows.planned_requests` and checked against its manifest (`main_rows.check_planned`), exactly as `main_analysis.analyse_run`
  builds Study 1's rows, restricted to the arms the spec compares with: Haiku-medium samples 1-8 ("haiku-med"), Opus-medium
  ("opus-med") and E3 at chain ("e3"). The join is by (`item_id`, `sample`): every top-up puzzle must have a FINAL main-run Haiku-medium
  record for each of samples 1-8 (the picker; the runner's own check `topup.main_run_replies` too) and every same-model puzzle for
  samples 1-5. **A failed join stops** (`JoinError`), with no per-puzzle skip (Edith's ruling 1).
- **A run cut short** (`completeness`; the user's ruling D-106(G), spec section 5 at 9c007e5, Edith's audit pass-2 ruling on P14): per
  arm (the Haiku team, the Haiku picker, step voting on pieces, the same-model check) the designed calls, the final ones and the
  missing ones. A refusal, a truncation or an unparseable answer is final. The picker and the same-model check have a fixed design
  (one call per puzzle; one per planned try). The Haiku team and step voting on pieces are adaptive (lead by 2, cap 9), so their
  missing calls are the ones the runner's OWN logic still requires when the driver runs (`topup.e2_puzzle`'s next requests for a
  puzzle that is neither done nor plan_failed; `e3.plan_round` on C13's step list): designed = final + missing, a lower bound on what
  the arm would have sent. An arm is completed only if nothing is missing (every E2 puzzle done or plan_failed; every C13 piece
  decided or at the cap). The driver reports an arm not completed as counts only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from . import main_rows, scoring
from ..pareto import e3, topup

SPEC = ("research/topup-run-spec.md at 9c007e5 (Karen; the spec frozen in lock 4, Edith CLEAN; SHA-256 "
        "f048e73a8ccc843f9d575e4fd51a0d462d1e39d5c1635bbad5d1a493170b41c5), sections 3-5; Edith's rulings on the runner "
        "(ops/reviews/2026-10-13-topup-spec-r1.md)")
E2_SETUP = "e2"
PICKER_SETUP = "h-pick8"
SAME_MODEL_SETUP = "same-model-check"     # never a Study 1 arm name (main_rows.FIVE_TEST_ARMS / OTHER_ARMS)
C13_ARM = "c13"                           # C13 rows keep setup "e3" (the product estimator reads it) and carry arm "c13"
PLAN_FAILED = "plan_failed"
MAIN_EXTRAS = ("sl", "ho", "hx")          # the extras the main run main-l14n6-1 was cleared with (harness/pareto/README.md, its command)
MAIN_TAGS = ("hm", "om", main_rows.E3_TAG)
PICK_SAMPLES = topup.PICKER_SAMPLES       # 8


class JoinError(RuntimeError):
    """The join to the main run's rows failed (spec 4c: "a failed join stops the driver")."""


# ---------------------------------------------------------------- the top-up run's records

def top_records(run_dir: Path) -> List[Dict[str, object]]:
    """The top-up run's final records (`main_rows.final_records`: two final records for one custom id raise)."""
    return main_rows.final_records([Path(run_dir) / "calls.jsonl"])


def check_records(man: Mapping[str, object], items: Sequence[Mapping[str, object]], records: Sequence[Mapping[str, object]],
                  plan: Mapping[str, object]) -> Dict[str, Mapping[str, object]]:
    """{custom_id: final record}. Every final record must be one of the plan's parts (its tags), on an item of the set, Haiku-medium
    (`topup.finals_by_id`), and C13's E3 records must be on pieces items; otherwise ValueError (nothing is silently dropped)."""
    by_id = {str(it["id"]): it for it in items}
    tags = {"same_model": (topup.TAG_SAME_MODEL,), "h_pick8": (topup.TAG_PICKER,),
            "e2": (topup.TAG_PLANNER, topup.TAG_HELPER, topup.TAG_AGGREGATOR), "c13": (topup.TAG_C13,)}
    allowed = {t for part in plan["parts"] for t in tags[str(part)]}                                    # type: ignore[union-attr]
    for r in records:
        meta = r.get("meta") or {}
        tag, iid = str(meta.get("setup")), str(meta.get("item_id"))                                     # type: ignore[union-attr]
        if tag not in allowed:
            raise ValueError(f"{r.get('custom_id')}: tag {tag!r} is not one of the plan's parts {sorted(allowed)}")
        it = by_id.get(iid)
        if it is None or meta.get("set_id") != man["set_id"]:                                           # type: ignore[union-attr]
            raise ValueError(f"{r.get('custom_id')}: item {iid!r} is not in {man['set_id']}")
        if tag == topup.TAG_C13 and not (int(it["width"]) > 1 and int(it["depth"]) == 1):              # type: ignore[call-overload]
            raise ValueError(f"{r.get('custom_id')}: a C13 (E3) record on a chain item; C13 runs on pieces only")
    finals = topup.finals_by_id(records)                                                                # model / effort check
    if len(finals) != len(records):
        raise ValueError("a final record without a custom id")
    return finals


def _base_id(man: Mapping[str, object], it: Mapping[str, object]) -> str:
    return f"{man['set_id']}-{int(it['base_index']):03d}"                                              # type: ignore[call-overload]


def _shape(it: Mapping[str, object]) -> str:
    return f"{it['width']}x{it['depth']}"


def _key_states(it: Mapping[str, object]) -> List[List[int]]:
    """The key the locked scorer grades against (main_rows.score_row): the chain's states at 1xN, the pieces' answer at Nx1."""
    if int(it["depth"]) > 1:                                                                            # type: ignore[call-overload]
        return [list(s) for s in it["chains"][0]["states"]]                                            # type: ignore[index]
    return [list(s) for s in it["answer"]]                                                              # type: ignore[union-attr]


def _answer_key(row: Mapping[str, object]) -> Optional[str]:
    """The graded reply's whole answer as a key: the step-line trace at 1xN (`trace_key`, ok format only), the pieces at Nx1."""
    return row.get("trace_key") if scoring.is_chain_shape(row.get("shape")) else row.get("answer_key")  # type: ignore[return-value]


# ---------------------------------------------------------------- E2

def e2_rows(man: Mapping[str, object], items: Sequence[Mapping[str, object]],
            finals: Mapping[str, Mapping[str, object]]) -> List[Dict[str, object]]:
    """One row per puzzle (see the module text). Extra fields: stage, plan_status, planner_kind / planner_stop_reason, tasks (k, status,
    draws, decided, at_cap, answer (the agreed state key, None for no result or not reached), no_result, votes (per draw: draw, kind,
    vote key or None)), tasks_no_result (places), helper_draws, helper_results_key (trace_key of the helpers' results,
    None if any is missing), helpers_right, custom_ids (every E2 call of the puzzle that has a final record)."""
    out: List[Dict[str, object]] = []
    for it in sorted(items, key=lambda x: (int(x["base_index"]), int(x["width"]))):                   # type: ignore[call-overload]
        st = topup.e2_puzzle(dict(man), dict(it), finals)
        pl_id = topup.planner_item(dict(man), dict(it))[0]
        agg_meta = dict(topup.planner_item(dict(man), dict(it))[2], setup=topup.TAG_AGGREGATOR, role="e2_aggregator")
        agg_id = f"{it['id']}-{topup.TAG_AGGREGATOR}-01"
        pl = finals.get(pl_id)
        stage = str(st["stage"])
        if stage == "done":
            row = main_rows.score_row(st["aggregator"], it, E2_SETUP)                                  # type: ignore[arg-type]
        elif stage == PLAN_FAILED:
            rec = {"custom_id": agg_id, "kind": PLAN_FAILED, "stop_reason": None, "refusal_category": None, "cost_usd": None,
                   "answer_text": None, "requested_model": e3.E3_MODEL, "effort": e3.E3_EFFORT, "meta": agg_meta}
            row = main_rows.score_row(rec, it, E2_SETUP)
        else:
            row = main_rows.missing_row(agg_id, agg_meta, it, E2_SETUP)
        lines = int(it["params"]["lines"])                                                             # type: ignore[index, call-overload]

        def votes(k: int) -> List[Dict[str, object]]:
            out_v = []
            for d in range(1, e3.CAP + 1):
                rec = finals.get(topup.helper_item_id(it, k, d))
                if rec is not None:
                    out_v.append({"draw": d, "kind": rec.get("kind"), "vote": e3.record_vote(rec, lines)})
            return out_v
        tasks = [{"k": t["k"], "status": t["status"], "draws": t["draws"], "decided": t.get("decided"), "at_cap": t.get("at_cap"),
                  "answer": t.get("answer"), "no_result": t["status"] == "done" and t["answer"] is None,
                  "votes": votes(int(t["k"]))} for t in st["tasks"]]                                  # type: ignore[union-attr]
        results = st.get("results")
        key = _key_states(it)
        helpers_key = (scoring.trace_key(results) if results is not None and all(r is not None for r in results)  # type: ignore[union-attr, arg-type]
                       else None)
        helpers_right = results is not None and len(results) == len(key) and all(                    # type: ignore[arg-type]
            r is not None and list(r) == key[i] for i, r in enumerate(results))                        # type: ignore[arg-type]
        cids = [c for c in finals if c.startswith(f"{it['id']}-") and str(finals[c]["meta"]["setup"]) in  # type: ignore[index]
                (topup.TAG_PLANNER, topup.TAG_HELPER, topup.TAG_AGGREGATOR)]
        row.update(stage=stage, plan_status=(PLAN_FAILED if stage == PLAN_FAILED else "ok" if st.get("plan") is not None else None),
                   planner_kind=None if pl is None else pl.get("kind"), planner_stop_reason=None if pl is None else pl.get("stop_reason"),
                   tasks=tasks, tasks_no_result=[t["k"] for t in tasks if t["no_result"]],
                   tasks_not_started=[t["k"] for t in tasks if t["status"] == "not_started"],
                   helper_draws=sum(int(t["draws"]) for t in tasks), helper_results_key=helpers_key, helpers_right=helpers_right,
                   answer_key_whole=_answer_key(row), custom_ids=sorted(cids))
        out.append(row)
    return out


# ---------------------------------------------------------------- the main run's rows and the join

def main_run_rows(main_dir: Path, set_dir: Path, extras: Sequence[str] = MAIN_EXTRAS, d42: bool = True,
                  hm_samples: int = PICK_SAMPLES) -> Dict[str, object]:
    """{"rows": the main run's scored rows of Haiku-medium samples 1..hm_samples, Opus-medium and E3 (missing rows of the planned
    tries and unfinished E3 chains included), "records": those arms' final records}. The planned list is checked against the main
    run's manifest first; a mismatch (or no manifest) stops (JoinError)."""
    main_dir, set_dir = Path(main_dir), Path(set_dir)
    man, items = main_rows.load_set(set_dir)
    planned = main_rows.planned_requests(man, list(items.values()), extras, d42)
    if not (main_dir / "manifest.json").is_file():
        raise JoinError(f"{main_dir.name}: no manifest.json, so the main run's planned list cannot be checked (spec 4c)")
    try:
        main_rows.check_planned(main_dir, planned)
    except ValueError:
        raise JoinError(f"{main_dir.name}/manifest.json does not match the main run's plan rebuilt with extras {list(extras)} "
                        "(item_set_sha256, n_items): wrong main run or extras")

    def keep(meta: Mapping[str, object]) -> bool:
        tag = str(meta.get("setup"))
        return tag in ("om", main_rows.E3_TAG) or (tag == "hm" and 1 <= int(meta.get("sample") or 0) <= hm_samples)  # type: ignore[call-overload]
    recs = [r for r in main_rows.final_records([main_dir / "calls.jsonl"]) if keep(r.get("meta") or {})]  # type: ignore[arg-type]
    built = main_rows.build(set_dir, [], records=recs, planned=[p for p in planned if keep(p[2])])
    return {"rows": built["tests"], "records": recs, "missing": built["missing"]}


def hm_join(rows: Sequence[Mapping[str, object]], items: Sequence[Mapping[str, object]], samples: int,
            what: str) -> Dict[str, List[Mapping[str, object]]]:
    """{item_id: [the main-run Haiku-medium row of sample 1, ..., sample `samples`]} for every given item. Each (item_id, sample) must
    join to exactly one row from a FINAL record (not kind "missing"); otherwise JoinError lists what failed (spec 4c)."""
    got: Dict[Tuple[str, int], List[Mapping[str, object]]] = defaultdict(list)
    for r in rows:
        if r["setup"] == "haiku-med":
            got[(str(r["item_id"]), int(r["sample"]))].append(r)                                       # type: ignore[call-overload]
    bad: List[str] = []
    out: Dict[str, List[Mapping[str, object]]] = {}
    for it in items:
        lst = []
        for s in range(1, samples + 1):
            rs = got.get((str(it["id"]), s), [])
            if len(rs) != 1 or rs[0].get("kind") == "missing":
                bad.append(f"{it['id']} sample {s}: {'no final record' if not rs or rs[0].get('kind') == 'missing' else f'{len(rs)} rows'}")
                continue
            lst.append(rs[0])
        out[str(it["id"])] = lst
    if bad:
        raise JoinError(f"{what}: {len(bad)} main-run Haiku-medium samples failed to join (first: {bad[:3]}); a failed join stops the "
                        "driver (spec 4c)")
    return out


# ---------------------------------------------------------------- the picker

def picker_rows(man: Mapping[str, object], items: Sequence[Mapping[str, object]], finals: Mapping[str, Mapping[str, object]],
                joined: Mapping[str, Sequence[Mapping[str, object]]]) -> List[Dict[str, object]]:
    """One row per puzzle (see the module text): pick (1-8 or None), joined_custom_id / joined_kind (main-run sample k), correct."""
    tp = topup.team_prompts()
    out: List[Dict[str, object]] = []
    for it in sorted(items, key=lambda x: (int(x["base_index"]), int(x["width"]))):                   # type: ignore[call-overload]
        cid = f"{it['id']}-{topup.TAG_PICKER}-01"
        rec = finals.get(cid)
        kind = "missing" if rec is None else str(rec.get("kind"))
        pick = tp.parse_pick(str(rec.get("answer_text") or "")) if rec is not None and kind == "answered" else None
        sample_rows = joined[str(it["id"])]
        if len(sample_rows) != PICK_SAMPLES:
            raise JoinError(f"{it['id']}: the picker row joins to {len(sample_rows)} main-run rows, not {PICK_SAMPLES} (spec 4c)")
        j = sample_rows[pick - 1] if pick is not None else None
        out.append({"base_id": _base_id(man, it), "set_id": man["set_id"], "item_id": it["id"], "shape": _shape(it),
                    "setup": PICKER_SETUP, "tag": topup.TAG_PICKER, "custom_id": cid, "kind": kind,
                    "stop_reason": None if rec is None else rec.get("stop_reason"),
                    "refusal_category": None if rec is None else rec.get("refusal_category"),
                    "error": None if rec is None else rec.get("error"),
                    "cost_usd": None if rec is None else rec.get("cost_usd"), "pick": pick,
                    "joined_custom_id": None if j is None else j.get("custom_id"), "joined_kind": None if j is None else j.get("kind"),
                    "correct": bool(j is not None and scoring.row_correct(j, "official")),
                    "sample_custom_ids": [str(r.get("custom_id")) for r in sample_rows]})
    return out


# ---------------------------------------------------------------- C13

def c13_rows(man: Mapping[str, object], items: Sequence[Mapping[str, object]],
             records: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    """C13's rows (see the module text): e3.e3_rows on topup.c13_steps, relabelled "<width>x1", plus a missing row for each unfinished
    pieces puzzle. Every row: setup "e3", arm "c13", step_correct (per piece), custom_ids (its E3 calls)."""
    steps = topup.c13_steps(dict(man), [dict(it) for it in items])
    es = [r for r in records if (r.get("meta") or {}).get("setup") == topup.TAG_C13]                  # type: ignore[union-attr]
    rows = [dict(r) for r in e3.e3_rows([], es, steps)]
    width = {st.item_id: st.width for st in steps}
    for r in rows:
        r.update(shape=scoring.pieces_shape(width[str(r["item_id"])]), arm=C13_ARM, shape_from_e3_rows=r["shape"])
    have = {str(r["item_id"]) for r in rows}
    draws = e3.draws_by_step(es)
    by_item: Dict[str, List[e3.Step]] = defaultdict(list)
    for st in steps:
        by_item[st.item_id].append(st)
    for item_id, ch in sorted(by_item.items()):
        if item_id in have:
            continue
        ch = sorted(ch, key=lambda s: s.k)
        correct: List[bool] = []
        calls = 0
        for st in ch:
            d = draws.get((item_id, st.k))
            if not d:
                correct.append(False)
                continue
            state = e3.step_state(st, d)
            calls += len(d)
            correct.append(bool(state["done"]) and state["answer"] is not None and state["answer"] == st.truth)
        first = ch[0]
        rows.append({"base_id": f"{first.set_id}-{first.base_index:03d}", "set_id": first.set_id, "item_id": item_id,
                     "shape": scoring.pieces_shape(first.width), "setup": "e3", "arm": C13_ARM, "kind": "missing", "stop_reason": None,
                     "step_correct": correct, "correct": False, "cost_usd": None, "calls": calls})
    ids: Dict[str, List[str]] = defaultdict(list)
    for r in es:
        ids[str((r.get("meta") or {}).get("item_id"))].append(str(r["custom_id"]))                     # type: ignore[union-attr]
    for r in rows:
        r["custom_ids"] = sorted(ids.get(str(r["item_id"]), []))
    return sorted(rows, key=lambda r: str(r["base_id"]))


# ---------------------------------------------------------------- the same-model check

def same_model_rows(plan: Mapping[str, object], man: Mapping[str, object], items: Sequence[Mapping[str, object]],
                    finals: Mapping[str, Mapping[str, object]]) -> List[Dict[str, object]]:
    """One row per planned same-model call, graded as Haiku-medium rows are; a planned call with no final record is a missing row."""
    by_id = {str(it["id"]): it for it in items}
    out: List[Dict[str, object]] = []
    for cid, _params, meta in topup.same_model_items(dict(plan), dict(man), [dict(it) for it in items]):
        it = by_id[str(meta["item_id"])]
        rec = finals.get(cid)
        out.append(main_rows.score_row(rec, it, SAME_MODEL_SETUP) if rec is not None else main_rows.missing_row(cid, meta, it, SAME_MODEL_SETUP))
    return out


# ---------------------------------------------------------------- a run cut short (D-106(G))

ARM_OF_PART = {"same_model": SAME_MODEL_SETUP, "h_pick8": PICKER_SETUP, "e2": E2_SETUP, "c13": C13_ARM}


def completeness(built: Mapping[str, object]) -> Dict[str, Dict[str, object]]:
    """{part: {"arm", "designed", "final", "missing", "completed", ...}} for each part of the plan that `build` built (see the module
    text; D-106(G)). Calls are counted from the FINAL records only (a refusal, truncation or unparseable answer is final). Same-model
    check: one designed call per planned try (`topup.same_model_items`), missing = its missing rows. Picker: one per puzzle. E2: final =
    the team's final records (planner, helpers, aggregator); missing = for each puzzle neither done nor plan_failed, the next requests
    `topup.e2_puzzle` (the runner's own logic) still plans for it. C13: final = its final E3 draws; missing = `e3.plan_round` on
    `topup.c13_steps` (the draws the runner would still send). E2 and C13 also give their unfinished puzzles."""
    out: Dict[str, Dict[str, object]] = {}
    for part, rows_key in (("same_model", "same_model"), ("h_pick8", "picker")):
        if rows_key in built:
            rows = list(built[rows_key])                                                                 # type: ignore[call-overload]
            miss = sum(1 for r in rows if r.get("kind") == "missing")
            out[part] = {"arm": ARM_OF_PART[part], "designed": len(rows), "final": len(rows) - miss, "missing": miss,
                         "unit": "calls", "completed": miss == 0}
    finals: Mapping[str, Mapping[str, object]] = built.get("finals") or {}                              # type: ignore[assignment]
    man, items = dict(built["man"]), [dict(it) for it in built["items"]]                                # type: ignore[call-overload, union-attr]
    if "e2" in built:
        tags = (topup.TAG_PLANNER, topup.TAG_HELPER, topup.TAG_AGGREGATOR)
        final = sum(1 for r in finals.values() if str((r.get("meta") or {}).get("setup")) in tags)       # type: ignore[union-attr]
        missing, unfinished = 0, []
        for it in items:
            st = topup.e2_puzzle(man, it, finals)
            if st["stage"] not in ("done", PLAN_FAILED):
                unfinished.append(str(it["id"]))
                missing += len(st["next"])                                                               # type: ignore[arg-type]
        out["e2"] = {"arm": E2_SETUP, "designed": final + missing, "final": final, "missing": missing, "unit": "calls",
                     "puzzles": len(items), "puzzles_unfinished": len(unfinished), "completed": not unfinished and missing == 0,
                     "designed_rule": "final calls + the next calls topup.e2_puzzle still plans for each puzzle neither done nor "
                                      "plan_failed (an adaptive arm: a lower bound)"}
    if "c13" in built:
        steps = topup.c13_steps(man, items)
        es = [r for r in built["records"] if (r.get("meta") or {}).get("setup") == topup.TAG_C13]       # type: ignore[union-attr]
        nxt = e3.plan_round([], es, steps)
        rows = list(built["c13"])                                                                       # type: ignore[call-overload]
        unfinished_c13 = sum(1 for r in rows if r.get("kind") == "missing")
        out["c13"] = {"arm": C13_ARM, "designed": len(es) + len(nxt), "final": len(es), "missing": len(nxt), "unit": "calls",
                      "puzzles": len(rows), "puzzles_unfinished": unfinished_c13, "completed": not nxt and unfinished_c13 == 0,
                      "designed_rule": "final draws + the draws e3.plan_round still plans on C13's step list (an adaptive arm: a "
                                       "lower bound)"}
    return out


# ---------------------------------------------------------------- everything

def build(plan: Mapping[str, object], run_dir: Path, main_dir: Path, extras: Sequence[str] = MAIN_EXTRAS,
          loader=None) -> Dict[str, object]:
    """Every row of the top-up run and the main-run rows they are compared with. Checks, in order: the plan (topup.validate_plan), the
    run folder's own copy of it (`topup_plan.json`, written by the runner), the set (deep-verified, `topup.load_topup_set`), the
    top-up records (`check_records`), the main run's planned list against its manifest, and the joins (spec 4c)."""
    plan = topup.validate_plan(json.loads(json.dumps(plan)))
    run_dir, main_dir = Path(run_dir), Path(main_dir)
    copy = run_dir / "topup_plan.json"
    if not copy.is_file():
        raise ValueError(f"{run_dir.name} has no topup_plan.json (the runner's copy of its plan): not a top-up run folder")
    if json.loads(copy.read_text()) != plan:
        raise ValueError(f"{run_dir.name}/topup_plan.json is not this plan: the run used another plan")
    man, items = topup.load_topup_set(dict(plan), loader)
    records = top_records(run_dir)
    finals = check_records(man, items, records, plan)
    main = main_run_rows(main_dir, topup.set_path(dict(plan)), extras)
    parts = tuple(plan["parts"])                                                                        # type: ignore[arg-type]
    out: Dict[str, object] = {"plan": plan, "man": man, "items": items, "records": records, "finals": finals,
                              "main_rows": main["rows"], "main_records": main["records"], "main_missing": main["missing"]}
    joined: Dict[str, List[Mapping[str, object]]] = {}
    if "h_pick8" in parts:
        try:
            topup.main_run_replies(main_dir, items, str(plan["main_run"]["run_id"]), str(plan["main_run"]["setup"]))  # type: ignore[index]
        except topup.MainRunJoinError as e:
            raise JoinError(f"the picker's join (the runner's own check): {e}")
        joined = hm_join(main["rows"], items, PICK_SAMPLES, "the picker (samples 1-8, every puzzle)")   # type: ignore[arg-type]
        out["picker"] = picker_rows(man, items, finals, joined)
    if "same_model" in parts:
        sm = plan["same_model"]
        chosen = [it for it in items if int(it["base_index"]) < int(sm["bases"])]                    # type: ignore[index, call-overload]
        out["same_model_joined"] = hm_join(main["rows"], chosen, int(sm["tries"]), "the same-model check (samples 1-5)")  # type: ignore[arg-type, index, call-overload]
        out["same_model"] = same_model_rows(plan, man, items, finals)
    if "e2" in parts:
        out["e2"] = e2_rows(man, items, finals)
    if "c13" in parts:
        out["c13"] = c13_rows(man, items, records)
    out["joined_hm"] = joined
    return out
