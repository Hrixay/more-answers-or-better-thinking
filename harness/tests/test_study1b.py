"""Study 1b's analysis (harness.analysis.study1b, study1b_k): hand-computed checks on a small fake run (fixture sets at N = 16, 6 and 12
plus a trial-round set; a run folder in the slim runner's shape: its plan copy, manifest, calibration_limits and cut lines written by
the runner's own functions, then a fake call log written record by record, the compact table by the runner's own writer), then k,
then the driver end to end. The joint run through the real runner is test_study1b_e2e. Offline only.

The fixture sets carry FIXTURE set ids (audit A20 / K3): the driver's set ids (study1b.SETS, CALIBRATION_SETS, EXPOSED_BASES) and k's
(study1b_k.K_SET) are patched to them for each test class (`fixture_set_ids`), so no test ever regenerates the sealed Study 1b sets'
items (an item's content is seeded by its set id)."""

import csv
import json
import math
import random
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence
from unittest import mock

from harness.analysis import bootstrap, curve, main_analysis, report_arms, scoring, study1b, study1b_k
from harness.pareto import prices, slim
from harness.pareto.calllog import CallLog
from harness.pareto.manifest import item_set_hash, write_manifest
from harness.pareto.prices import HAIKU, OPUS, SONNET, Usage
from harness.pareto.table import COLUMNS as TABLE_COLUMNS, write_compact_table
from harness.taskgen import ledger
from harness.taskgen.freeze import write_set
from harness.tests.fakes import guard as fake_guard

import atexit as _atexit
import shutil as _shutil


def _tmpdir() -> Path:
    """A temp folder removed when the test process exits: these tests write nowhere else."""
    d = Path(tempfile.mkdtemp(prefix="pareto-test-"))
    _atexit.register(_shutil.rmtree, d, True)
    return d


# FIXTURE set ids (never the sealed sets' ids: an item's content is seeded by its set id; audit A20 / K3)
N16, N6, N12, CAL = "fxb-ledger-l14n16-v1", "fxb40-ledger-l14n6-v1", "fxb-ledger-l14n12-v1", "fxbcal-ledger-l14n16-v1"


def fixture_set_ids(test_ids: Mapping[int, str], cal_ids: Sequence[str], cls=None):
    """Patch the driver's and k's set ids to fixture ids: study1b.SETS (N -> set id), CALIBRATION_SETS, EXPOSED_BASES (the same bases as
    D-97's: base 000 at 16, bases 000 and 003 at 6) and study1b_k.K_SET (the N = 16 set). With `cls` (a TestCase class, from
    setUpClass) the patches are started now and stopped when the class is done; without it the patchers are returned."""
    patchers = [mock.patch.object(study1b, "SETS", dict(test_ids)),
                mock.patch.object(study1b, "CALIBRATION_SETS", tuple(cal_ids)),
                mock.patch.object(study1b, "EXPOSED_BASES", {test_ids[16]: (0,), test_ids[6]: (0, 3)}),
                mock.patch.object(study1b_k, "K_SET", test_ids[16])]
    if cls is None:
        return patchers
    for p in patchers:
        p.start()
        cls.addClassCleanup(p.stop)
    return patchers
R = "R"
MISS, REF, TRUNC, GARB = "MISS", "REF", "TRUNC", "GARB"


def W(j):
    return ("W", j)


def bump(state, by=1):
    return [state[0] + by] + list(state[1:])


def chain_text(states):
    lines = [f"1.{k} = {ledger.fmt(s)}" for k, s in enumerate(states, 1)]
    return "\n".join(lines + [f"Answer: 1 = {ledger.fmt(states[-1])}"])


def pieces_text(answer):
    return "Answer: " + ", ".join(f"{i} = {ledger.fmt(a)}" for i, a in enumerate(answer, 1))


ARMS = {                                                                     # hx at 16 is set by the trial round (on CAL), as in the plan
    N16: [("hx", HAIKU, "max", 10, False), ("om", OPUS, "medium", 2, False), ("hm", HAIKU, "medium", 5, False)],
    N6: [("hx", HAIKU, "max", 10, False), ("om", OPUS, "medium", 2, False), ("sl", SONNET, "low", 1, False),
         ("ho", HAIKU, "medium", 5, True)],
    N12: [("hx", HAIKU, "max", 10, False), ("om", OPUS, "medium", 1, False)],
}
STEPS = {N16: 16, N6: 6, N12: 12}
CALIBRATED = {(16, "hx"): {"floor": 96000, "wave0_max_tokens": 128000}}
# (set, tag, base, form) -> outcomes of tries 1..n; anything not listed is right.
OUTCOMES = {
    (N16, "hx", 1, "p"): [R] * 7 + [W(1), REF, MISS],
    (N16, "hx", 1, "c"): [R] * 5 + [W(1), W(2), W(3), W(4), TRUNC],
    (N16, "hx", 2, "c"): [R] * 9 + [MISS],
    (N16, "om", 1, "p"): [R, W(1)],
    (N16, "om", 2, "c"): [R, MISS],
    (N16, "hm", 0, "c"): [R, R, R, R, W(1)],
    (N6, "hx", 1, "p"): [R] * 8 + [W(1), W(2)],
    (N6, "sl", 1, "p"): [W(1)],
    (N6, "ho", 1, "c"): [R, R, R, GARB, REF],
    (N12, "om", 1, "c"): [MISS],
}
USAGE = {(N16, "hx"): (1000, 10000), (N16, "om"): (1000, 1500), (N6, "hx"): (1000, 900), (N6, "om"): (1000, 50000),
         (CAL, "hx"): (1000, 100000)}


def outcome(sid, tag, base, form, k, n):
    seq = OUTCOMES.get((sid, tag, base, form))
    return seq[k - 1] if seq else R


def record(cid, params, meta, item, out):
    """One final call-log record in the client's shape."""
    model, sid, tag = params["model"], meta["set_id"], meta["setup"]
    tin, tout = USAGE.get((sid, tag), (500, 2000))
    usage = {"input_tokens": tin, "output_tokens": tout, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    rec = {"custom_id": cid, "final": True, "meta": meta, "run_id": "t", "mode": "batch", "requested_model": model,
           "returned_model": model, "effort": params["output_config"]["effort"], "thinking": params["thinking"]["type"],
           "max_tokens": params["max_tokens"], "usage_raw": usage, "batch_id": "b1", "latency_s": None,
           "cost_usd": str(prices.cost(model, Usage(tin, tout), batch=True)), "refusal_category": None, "refusal_billed_by_rule": None}
    chain = int(item["depth"]) > 1
    if out == REF:
        rec.update(kind="refusal", stop_reason="refusal", answer_text="", refusal_category="cyber", refusal_billed_by_rule=True)
    elif out == TRUNC:
        rec.update(kind="truncated", stop_reason="max_tokens", answer_text="1.1 = [")
    elif out == GARB:
        rec.update(kind="answered", stop_reason="end_turn", answer_text="I could not finish.")
    else:
        if chain:
            st = item["chains"][0]["states"]
            text = chain_text(st if out == R else st[:-1] + [bump(st[-1], out[1])])
        else:
            ans = item["answer"]
            text = pieces_text(ans if out == R else [bump(ans[0], out[1])] + ans[1:])
        rec.update(kind="answered", stop_reason="end_turn", answer_text=text)
    return rec


def _items_sha(d):
    return json.loads((Path(d) / "manifest.json").read_text())["items_sha256"]


def slim_plan(sets, arms=ARMS, cut_order=(("Sonnet-low at 6 (fixture)", [[6, "sl"]]),)):
    """A plan in the slim runner's format (slim.validate_plan) over the fixture sets: measured arms at 64,000 with a cost basis, the
    calibrated arms of CALIBRATED, the trial round on CAL (1 base, 1 try), and a cut order."""
    def arm(t, m, e, n, off, steps):
        a = {"tag": t, "model": m, "effort": e, "n": n, "role": "descriptive", "thinking_off": off}
        if (steps, t) in CALIBRATED:
            a["calibrate"] = dict(CALIBRATED[(steps, t)])
        else:
            a.update(max_tokens=64000, cost_basis={"cost_usd_sum": "0.01", "calls": 10, "source": "test"})
        return a
    return {"study": "study1b-test",
            "sets": [{"set": str(sets[sid]), "items_sha256": _items_sha(sets[sid]), "steps": STEPS[sid],
                      "arms": [arm(*a, STEPS[sid]) for a in arms[sid]]} for sid in arms],
            "calibration": {"sets": [{"set": str(sets[CAL]), "items_sha256": _items_sha(sets[CAL]), "steps": 16}], "base_puzzles": 1,
                            "tries": 1, "rule": {"factor": 2, "round_up_to": 1000, "max_tokens_cap": 128000, "on_truncation": 128000}},
            "cut": {"multiplier": "1.5", "share_of_cap": "0.9", "order": [{"name": n, "arms": a} for n, a in cut_order],
                    "never_cut": [[16, "hx"], [16, "om"], [6, "hx"], [6, "om"]]}}


def write_run(run_dir, plan, cap="1000"):
    """A run folder as the slim runner leaves it, written by the runner's own functions (plan copy, manifest, trial round, the
    calibration_limits and cut lines and file), then every test request it sends as a record with OUTCOMES (MISS: no record).
    Returns the custom ids left without a record."""
    run_dir.mkdir(parents=True)
    slim._check_plan_copy(run_dir, plan)
    test, cal = slim.load_sets(plan)
    write_manifest(run_dir, fake_guard(run_cap=cap), slim.manifest_requests(plan, test, cal), "dry", note="test")
    log = CallLog(run_dir / "calls.jsonl")
    log.write({"kind": "batch_submitted", "batch_id": "b1", "keys": {}, "final": False})
    items = {it["id"]: it for _, _, its in test + cal for it in its}
    wave0 = slim.build_wave0_requests(plan, test, cal)
    for cid, params, meta in wave0:
        log.write(record(cid, params, meta, items[meta["item_id"]], R))
    limits = slim.apply_limits(log, "t", plan, wave0)
    (run_dir / "calibration_limits.json").write_text(json.dumps(limits, indent=1, sort_keys=True) + "\n")
    cut = slim.apply_cut(log, "t", plan, test, limits, wave0, Decimal(cap))
    missing = []
    for s, man, its in test:
        for cid, params, meta in slim.sent_test_requests(plan, s, man, its, limits, cut):
            item = items[meta["item_id"]]
            form = "c" if int(item["depth"]) > 1 else "p"
            out = outcome(man["set_id"], meta["setup"], int(meta["base_index"]), form, int(meta["sample"]), None)
            if out == MISS:
                missing.append(cid)
                continue
            log.write(record(cid, params, meta, item, out))
    write_compact_table(log, run_dir / "compact_table.csv")
    return missing


def write_table(path, rows):
    """A compact table with the runner's columns from {custom_id, requested_model, effort, kind, input, output, billed} dicts."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TABLE_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({"custom_id": r["custom_id"], "requested_model": r["model"], "effort": r["effort"], "kind": r.get("kind", "answered"),
                        "input_tokens": r["tin"], "output_tokens": r["tout"], "cache_read_tokens": 0, "cache_write_tokens": 0,
                        "refusal_billed_by_rule": r.get("billed"), "cost_usd": "0", "right": 1})


class Study1bRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_set_ids({16: N16, 6: N6, 12: N12}, (CAL,), cls)
        cls.td = _tmpdir()
        cls.sets = {}
        for sid, preset, nb in ((N16, "l14n16", 3), (N6, "l14n6", 2), (N12, "l14n12", 2), (CAL, "l14n16", 1)):
            write_set(cls.td / sid, "ledger", preset, sid, nb, "d31", "scratch")
            cls.sets[sid] = cls.td / sid
        cls.splan = slim_plan(cls.sets)
        cls.plan_path = cls.td / "plan.json"
        cls.plan_path.write_text(json.dumps(cls.splan))
        cls.run_dir = cls.td / "run"
        cls.missing = write_run(cls.run_dir, cls.splan)
        cls.loaded = study1b.load_run(cls.run_dir)
        cls.plan = cls.loaded["sets"]
        cls.k_path = cls.run_dir / "k.json"
        study1b_k.main(["--run", str(cls.run_dir), "--out", str(cls.k_path)])
        cls.kdoc = json.loads(cls.k_path.read_text())
        cls.built = study1b.build_rows(cls.plan, [cls.run_dir / "calls.jsonl"])
        cls.rows = cls.built["rows"]
        cls.res = study1b.analyse(cls.run_dir, cls.k_path, B=300, draws=200)

    # ------------------------------------------------------------ k

    def test_k_by_hand(self):
        """hx at N = 16: 1,000 in + 10,000 out at Haiku list ($0.10 / $0.50 per M) = $0.0051 a try; om: 1,000 + 1,500 at Opus ($4 / $20)
        = $0.034; ratio 20/3, k = 6. The N = 6 arms (other prices) and the calibration hx (100,000 out) would move it if read."""
        k = self.kdoc
        self.assertEqual((k["k"], k["raw_k"], k["ratio"], k["capped"], k["b2_run"]), (6, 6, "20/3", False, True))
        self.assertEqual(k["calls"], {"hx": 58, "om": 11})                    # 60 and 12 planned, 2 and 1 missing (not calls)
        self.assertEqual(Fraction(k["mean_list_cost_per_try"]["hx"]), Fraction("0.0051"))
        self.assertEqual(Fraction(k["mean_list_cost_per_try"]["om"]), Fraction("0.034"))
        self.assertIn(CAL, k["rows_left_out_by_set"])
        self.assertEqual(set(k["rows_left_out_by_set"]), {CAL, N6, N12})
        self.assertEqual(k["rows_left_out_by_tag"], {"hm": 30})
        self.assertEqual(k["columns_read"], list(study1b_k.COLUMNS))
        self.assertNotIn("right", k["columns_read"])
        self.assertNotIn("cost_usd", k["columns_read"])                       # list cost from tokens (item 9a), not the logged cost
        with self.assertRaises(SystemExit):
            study1b_k.main(["--run", str(self.run_dir), "--out", str(self.k_path)])   # fixed once

    def _k_of(self, hx, om, extra=()):
        td = _tmpdir()
        rows = [dict(custom_id=f"{N16}-000-16x1-hx-{i:02d}", model=HAIKU, effort="max", tin=hx[0], tout=hx[1]) for i in range(1, 3)]
        rows += [dict(custom_id=f"{N16}-000-16x1-om-{i:02d}", model=OPUS, effort="medium", tin=om[0], tout=om[1]) for i in range(1, 3)]
        write_table(td / "compact_table.csv", rows + list(extra))
        return study1b_k.k_from_table(td / "compact_table.csv")

    def test_k_cap_10(self):
        k = self._k_of((0, 1000), (0, 1000))                                   # $0.0005 vs $0.02: ratio 40
        self.assertEqual((k["k"], k["raw_k"], k["capped"], k["label"], k["b2_run"]), (10, 40, True, "for less than Opus's price", True))

    def test_b2_label_is_ratio_above_10(self):
        """Edith S-D2: the label applies when the ratio is above 10, in k.json and in the driver's wording alike."""
        k = self._k_of((0, 2000), (0, 525))                                    # $0.001 vs $0.0105: ratio 10.5 (kscript's own flag: not capped)
        self.assertEqual((k["k"], k["raw_k"], k["ratio"], k["capped"], k["label"]), (10, 10, "21/2", True, "for less than Opus's price"))
        self.assertIn("for less than Opus's price", study1b.b2_wording(k))
        k = self._k_of((0, 2000), (0, 500))                                    # exactly 10: k = 10, not labelled
        self.assertEqual((k["k"], k["ratio"], k["capped"], k["label"]), (10, "10", False, None))
        self.assertEqual(study1b.b2_wording(k), "the vote of k = 10 Haiku-max tries, about Opus-medium's price")
        self.assertNotIn("less than", study1b.b2_wording(self.kdoc))           # k = 6
        td = _tmpdir()                                                         # the driver refuses a k.json whose flag breaks the rule
        (td / "k.json").write_text(json.dumps(dict(self.kdoc, capped=True)))
        with self.assertRaises(ValueError):
            study1b.check_k(td / "k.json", self.run_dir)

    def test_k_below_1_b2_not_run(self):
        k = self._k_of((0, 100000), (0, 1000))                                 # $0.05 vs $0.02: ratio 0.4
        self.assertEqual((k["k"], k["raw_k"], k["b2_run"]), (0, 0, False))
        self.assertEqual(k["b2_note"], study1b_k.NOT_RUN)

    def test_k_free_refusal_is_zero_and_model_checked(self):
        free = dict(custom_id=f"{N16}-001-16x1-hx-01", model=HAIKU, effort="max", tin=1000, tout=1000, kind="refusal", billed=False)
        k = self._k_of((0, 1000), (0, 1000), [free])                           # hx: ($0.0005 x 2 + $0) / 3
        self.assertEqual(Fraction(k["mean_list_cost_per_try"]["hx"]), Fraction("0.001") / 3)
        bad = dict(custom_id=f"{N16}-001-16x1-om-01", model=OPUS, effort="high", tin=1, tout=1)
        with self.assertRaises(ValueError):
            self._k_of((0, 1000), (0, 1000), [bad])

    def test_driver_rechecks_k(self):
        td = _tmpdir()
        bad = dict(self.kdoc, k=7)
        (td / "k.json").write_text(json.dumps(bad))
        with self.assertRaises(ValueError):
            study1b.check_k(td / "k.json", self.run_dir)
        self.assertEqual(self.res["k"]["k"], 6)
        self.assertEqual(self.res["k_from_call_log"]["k"], 6)

    # ------------------------------------------------------------ rows

    def test_trial_round_records_are_ignored(self):
        self.assertEqual(len(self.built["calibration"]), 2)                     # 1 base x 2 forms x 1 try
        self.assertFalse(any(r["set_id"] == CAL for r in self.rows))
        for rec in self.built["calibration"]:
            self.assertNotIn("answer_text", rec)                                # cut to cost fields as read
        cw = self.res["trial_round"]
        self.assertEqual(cw["calls"], 2)
        self.assertEqual(cw["by_set_and_tag"][f"{CAL} hx"]["output_tokens"], 200000)
        self.assertEqual(Fraction(cw["by_set_and_tag"][f"{CAL} hx"]["list_usd"]), 2 * Fraction("0.0501"))
        self.assertEqual(self.res["records"]["trial_round_ignored"], 2)
        self.assertTrue(cw["label"].startswith("the trial round"))

    # ------------------------------------------------------------ the run as the runner wrote it (Edith S-D1)

    def test_calibrated_limits_come_from_the_calibration_limits_line(self):
        """hx at 16 carries `calibrate` (no max_tokens): its trial round wrote 100,000 tokens, so 2 x 100,000 capped at 128,000."""
        hx16 = next(a for s in self.plan if s["n"] == 16 for a in s["arms"] if a.name == "hx")
        self.assertEqual(hx16.max_tokens, 128000)
        self.assertEqual({p["max_tokens"] for cid, p, m in study1b.planned_requests(next(s for s in self.plan if s["n"] == 16))
                          if m["setup"] == "hx"}, {128000})
        lim = self.res["plan_as_run"]["limits"]
        self.assertEqual([(a["steps"], a["tag"], a["max_tokens"], a["wave0_output_tokens_max"]) for a in lim], [(16, "hx", 128000, 100000)])
        self.assertEqual(self.res["plan_as_run"]["cut"]["arms"], [])
        self.assertTrue(self.res["inputs"]["manifest_check"]["checked"])

    def test_the_run_folder_is_checked(self):
        """A plan file other than the run's copy, limits that disagree, a still-over cut with no ruling, a cut naming B1-B3's arms: refused."""
        other = dict(self.splan, study="another")
        (self.td / "other.json").write_text(json.dumps(other))
        with self.assertRaises(ValueError):
            study1b.load_run(self.run_dir, self.td / "other.json")
        study1b.load_run(self.run_dir, self.plan_path)                          # the same plan: fine

        def variant(edit_line=None, edit_limits=None):
            d = _tmpdir() / "run"
            _shutil.copytree(self.run_dir, d)
            if edit_line:
                lines = [json.loads(ln) for ln in (d / "calls.jsonl").read_text().splitlines() if ln.strip()]
                (d / "calls.jsonl").write_text("".join(json.dumps(edit_line(x) or x, sort_keys=True) + "\n" for x in lines))
            if edit_limits:
                doc = json.loads((d / "calibration_limits.json").read_text())
                edit_limits(doc)
                (d / "calibration_limits.json").write_text(json.dumps(doc))
            return d
        with self.assertRaises(ValueError):
            study1b.load_run(variant(edit_limits=lambda doc: doc["arms"][0].update(max_tokens=96000)))
        with self.assertRaises(ValueError):
            study1b.load_run(variant(lambda x: dict(x, still_over=True) if x.get("kind") == "cut" else None))
        with self.assertRaises(ValueError):
            study1b.load_run(variant(lambda x: dict(x, cut_arms=[[16, "om"]]) if x.get("kind") == "cut" else None))
        d = variant()
        (d / "manifest.json").unlink()
        with self.assertRaises(FileNotFoundError):
            study1b.load_run(d)

    def test_a_cut_arm_is_reported_as_cut_not_missing(self):
        """A run whose §7 cut removed sl at 6: no sl request is planned, none is missing, §6 says 'cut by §7 (cost)'; a record of a cut
        arm in the log raises."""
        plan = slim_plan(self.sets)
        for a in plan["sets"][0]["arms"]:                                       # om at 16 'costs' $10 a call: over 0.9 x $30 whatever is cut,
            if a["tag"] == "om":                                                # so the whole order (sl at 6) is cut, and the user's ruling
                a["cost_basis"] = {"cost_usd_sum": "10", "calls": 1, "source": "test"}   # is recorded as the runner does
        d = _tmpdir() / "run"
        missing = write_run(d, plan, cap="30")
        log = CallLog(d / "calls.jsonl")
        cut = slim._one_line(log, "cut")
        self.assertEqual((cut["cut_arms"], cut["still_over"]), ([[6, "sl"]], True))
        with self.assertRaises(ValueError):                                     # still over and no ruling: no test wave ran
            study1b.load_run(d)
        slim.check_accept_projection(log, "the user: go on (test)")
        log.write({"kind": "projection_accepted", "run_id": "t", "note": "the user: go on (test)", "final": False})
        study1b_k.main(["--run", str(d), "--out", str(d / "k.json")])
        res = study1b.analyse(d, d / "k.json", B=100, draws=50)
        self.assertEqual(res["descriptive"]["arms"]["sl@6"]["status"], "cut by §7 (cost)")
        self.assertNotIn("mean", res["descriptive"]["arms"]["sl@6"])
        self.assertEqual(res["plan_as_run"]["cut"]["arms"], ["sl@6"])
        self.assertTrue(res["plan_as_run"]["cut"]["projection_accepted"])
        self.assertEqual(sorted(missing), sorted(self.missing))                 # the same tries missing; sl's never planned
        self.assertEqual(res["records"]["missing_rows"], len(self.missing))
        self.assertEqual(res["records"]["planned_rows"], self.res["records"]["planned_rows"] - 4)   # sl: 2 bases x 2 forms x 1 try
        sl = [p for p in res["descriptive"]["effort_figure"]["N=6"]["sonnet"]]
        self.assertEqual(sl, [{"arm": "sl@6", "tag": "sl", "effort": "low", "status": "cut by §7 (cost)"}])
        self.assertEqual(res["descriptive"]["format_refusals_truncations_missing"]["cut_by_section_7"]["arms"], ["sl@6"])
        self.assertNotIn("sl 6x1", res["descriptive"]["format_refusals_truncations_missing"]["item_16_rates"][N6])
        # a record of the cut arm in the log: not a request the run sent
        rec = next(json.loads(ln) for ln in (self.run_dir / "calls.jsonl").read_text().splitlines()
                   if '"final": true' in ln and '-sl-01' in ln)
        with open(d / "calls.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        with self.assertRaises(ValueError):
            study1b.build_rows(study1b.load_run(d)["sets"], [d / "calls.jsonl"])

    def test_section6_inputs_are_required_and_no_absolute_path_is_written(self):
        """Edith S-D3."""
        with self.assertRaises(FileNotFoundError):
            study1b.analyse(self.run_dir, self.k_path, B=50, draws=20, ladder_path=self.td / "no-curve.json")
        with self.assertRaises(FileNotFoundError):
            study1b.analyse(self.run_dir, self.k_path, B=50, draws=20, study1_path=self.td / "no-analysis.json")
        text = json.dumps(self.res, sort_keys=True, default=str)
        for absolute in (str(self.td), str(study1b.ROOT), "/private/", "/Users/", "/tmp/"):
            self.assertNotIn(absolute, text)
        self.assertEqual(self.res["descriptive"]["effort_figure"]["study1_points"]["source"], "data/main/main-l14n6-1/analysis.json")
        self.assertEqual(self.res["descriptive"]["length_curve"]["ladder"]["source"], "data/pilot/curve-ladder-l14n-1-d90.json")

    def test_missing_rows_are_planned_tries_without_a_record(self):
        miss = sorted(r["custom_id"] for r in self.rows if r["kind"] == "missing")
        self.assertEqual(miss, sorted(self.missing))
        self.assertEqual(len(miss), 4)
        self.assertTrue(all(not scoring.row_correct(r) for r in self.rows if r["kind"] == "missing"))

    def test_a_record_outside_the_plan_raises(self):
        td = _tmpdir()
        log = td / "calls.jsonl"
        log.write_text((self.run_dir / "calls.jsonl").read_text())
        rec = next(x for x in map(json.loads, log.read_text().splitlines()) if x.get("final") and x["custom_id"].startswith(N16))
        rec["custom_id"] = rec["custom_id"].rsplit("-", 1)[0] + "-99"
        with open(log, "a") as f:
            f.write(json.dumps(rec) + "\n")
        with self.assertRaises(ValueError):
            study1b.build_rows(self.plan, [log])

    def test_plan_is_checked_against_section_3(self):
        ids = {16: N16, 6: N6, 12: N12}
        study1b.check_section_3(self.splan, ids, [CAL])
        arms = dict(ARMS)
        arms[N16] = [("hx", HAIKU, "max", 10, False), ("om", OPUS, "medium", 1, False)]   # om x1 at 16: §3 says x2
        with self.assertRaises(ValueError):
            study1b.check_section_3(slim_plan(self.sets, arms), ids, [CAL])
        arms = {N16: ARMS[N16], N12: ARMS[N12]}                                    # B3's set missing
        with self.assertRaises(ValueError):
            study1b.check_section_3(slim_plan(self.sets, arms, ()), ids, [CAL])
        with self.assertRaises(ValueError):                                        # a trial round on a test set
            study1b.check_section_3(self.splan, ids, [N12])
        with self.assertRaises(ValueError):                                        # a set that is not §2's at its length
            study1b.check_section_3(self.splan, {**ids, 12: "other-ledger-l14n12-v1"}, [CAL])

    def test_manifest_check(self):
        """The manifest is rebuilt by the runner's own builder (the trial round plus every test arm at its floor)."""
        test, cal = slim.load_sets(self.splan)
        reqs = slim.manifest_requests(self.splan, test, cal)
        got = study1b.check_manifest(self.run_dir, reqs)
        self.assertEqual((got["checked"], got["n_items"]), (True, len(reqs)))
        self.assertEqual(len(reqs), 2 + self.res["records"]["planned_rows"])      # nothing cut here: trial round + every test try
        with self.assertRaises(FileNotFoundError):
            study1b.check_manifest(_tmpdir(), reqs)
        td = _tmpdir()
        (td / "manifest.json").write_text(json.dumps({"item_set_sha256": item_set_hash(reqs[1:]), "n_items": len(reqs) - 1}))
        with self.assertRaises(ValueError):
            study1b.check_manifest(td, reqs)

    # ------------------------------------------------------------ §4 by hand

    def b(self, sid, i):
        return f"{sid}-{i:03d}"

    def test_form_pooling_with_opus_two_tries(self):
        """h_b (share right of the 10 designed tries, missing wrong) and o_b (of Opus's 2), each the mean over the two forms."""
        sc = study1b.test_scores(self.rows, 6)
        b1 = sc["B1"]
        self.assertEqual(b1["challenger"]["16x1"], {self.b(N16, 0): 100.0, self.b(N16, 1): 70.0, self.b(N16, 2): 100.0})
        self.assertEqual(b1["challenger"]["1x16"], {self.b(N16, 0): 100.0, self.b(N16, 1): 50.0, self.b(N16, 2): 90.0})
        self.assertEqual(b1["c"], {self.b(N16, 0): 100.0, self.b(N16, 1): 60.0, self.b(N16, 2): 95.0})
        self.assertEqual(b1["comparator"]["16x1"], {self.b(N16, 0): 100.0, self.b(N16, 1): 50.0, self.b(N16, 2): 100.0})
        self.assertEqual(b1["comparator"]["1x16"], {self.b(N16, 0): 100.0, self.b(N16, 1): 100.0, self.b(N16, 2): 50.0})
        self.assertEqual(b1["o"], {self.b(N16, 0): 100.0, self.b(N16, 1): 75.0, self.b(N16, 2): 75.0})
        diffs, left = study1b.test_differences(self.rows, 6)
        self.assertEqual(diffs["B1"], [0.0, -15.0, 20.0])
        self.assertEqual(diffs["B3"], [0.0, -10.0])                            # h 100, 90; o 100, 100
        self.assertEqual(left, {"B1": 0, "B2": 0, "B3": 0})

    def test_missing_counts_as_wrong(self):
        """Base 002's chain form: 9 right and 1 missing of 10 designed tries is 90, not 100; Opus's 1 right of 2 (1 missing) is 50."""
        b1 = study1b.test_scores(self.rows, 6)["B1"]
        self.assertEqual(b1["challenger"]["1x16"][self.b(N16, 2)], 90.0)
        self.assertEqual(b1["comparator"]["1x16"][self.b(N16, 2)], 50.0)
        pt = self.res["descriptive"]["arms"]["om@12"]
        self.assertEqual(pt["1x12"]["mean"], 50.0)                             # 1 try, missing at base 001: 1 of 2 bases
        self.assertEqual((pt["1x12"]["designed"], pt["1x12"]["final"], pt["1x12"]["missing"]), (2, 1, 1))

    def test_run_stopped_section_6(self):
        """Spec §6 at 9c007e5 (C1): B1/B2 are held here (hx and om at 16 have missing tries), B3 is not. hx and om at 16 are computed
        on their final tries only, labelled; hx and om at 6 are as deployed, unlabelled; om at 12 (partly sent, descriptive) keeps the
        official score (missing wrong) with its counts and the exclude-missing view beside it; every entry carries its counts."""
        arms = self.res["descriptive"]["arms"]
        self.assertEqual(study1b.held_lengths(self.rows), [16])
        for key, counts in (("hx@16", (60, 58, 2)), ("om@16", (12, 11, 1))):
            a = arms[key]
            self.assertEqual(a["label"], "not completed; descriptive only")
            self.assertEqual((a["designed"], a["final"], a["missing"]), counts)
            self.assertNotIn("missing_excluded", a)
        self.assertEqual(arms["om@16"]["1x16"]["mean"], 100.0)                  # final only: base 002's 1 final try right (not 50)
        for key in ("hx@6", "om@6", "sl@6", "ho@6", "hm@16", "hx@12"):
            self.assertNotIn("label", arms[key], key)
            self.assertNotIn("status", arms[key], key)
            for panel in ("pooled",) + tuple(k for k in arms[key] if "x" in k and k[0].isdigit()):
                self.assertTrue({"designed", "final", "missing"} <= set(arms[key][panel]), (key, panel))
        self.assertNotIn("missing_excluded", arms["hx@6"])                      # nothing missing: no sensitivity
        om12 = arms["om@12"]
        self.assertEqual((om12["designed"], om12["final"], om12["missing"]), (4, 3, 1))
        self.assertEqual(om12["1x12"]["mean"], 50.0)                            # official: the missing try is wrong
        sens = om12["missing_excluded"]
        self.assertEqual(sens["label"], "sensitivity: missing tries excluded")
        self.assertEqual((sens["1x12"]["mean"], sens["1x12"]["n_base"]), (100.0, 1))   # final tries only: base 000's right try
        self.assertEqual(sens["12x1"]["mean"], om12["12x1"]["mean"])           # nothing missing in the pieces form
        fig = {p["tag"]: p for p in self.res["descriptive"]["effort_figure"]["N=16"]["haiku"]}
        self.assertEqual(fig["hx"]["label"], "not completed; descriptive only")
        self.assertEqual((fig["hx"]["designed"], fig["hx"]["missing"]), (60, 2))
        self.assertEqual(fig["hx"]["16x1"]["mean"], arms["hx@16"]["16x1"]["mean"])
        self.assertEqual(fig["hm"]["pooled"]["missing"], 0)
        lc = self.res["descriptive"]["length_curve"]
        self.assertEqual(lc["opus-medium"]["16"]["label"], "not completed; descriptive only")
        self.assertEqual(lc["opus-medium"]["12"]["missing_excluded"]["label"], "sensitivity: missing tries excluded")
        self.assertEqual(lc["opus-medium"]["12"]["1x12"]["missing"], 1)
        self.assertNotIn("label", lc["haiku-max"]["6"])

    def test_views_drop_refusals_and_truncations(self):
        ro = study1b.test_scores(self.rows, 6, "refusals_out")["B1"]["challenger"]
        to = study1b.test_scores(self.rows, 6, "truncations_out")["B1"]["challenger"]
        self.assertAlmostEqual(ro["16x1"][self.b(N16, 1)], 700.0 / 9)       # 7 of the 9 left (the refusal out, the missing kept)
        self.assertAlmostEqual(to["1x16"][self.b(N16, 1)], 500.0 / 9)       # 5 of the 9 left

    def test_vote_by_hand(self):
        """B2 at k = 6. Base 001's pieces form: 7 right of 10, so every 6-subset holds at least 3 right and 1 wrong at most: 100. Its chain
        form: 5 right, 4 different wrong answers and 1 truncated (a vote for nothing): a 6-subset loses only with 1 right, i.e. all 5
        others drawn, a 5-way tie at 1/5; C(5,1) = 5 of C(10,6) = 210 subsets: (205 + 1) / 210."""
        b2 = study1b.test_scores(self.rows, 6)["B2"]
        chain = 100.0 * 206 / 210
        self.assertEqual(b2["challenger"]["16x1"][self.b(N16, 1)], 100.0)
        self.assertAlmostEqual(b2["challenger"]["1x16"][self.b(N16, 1)], chain)
        self.assertAlmostEqual(b2["c"][self.b(N16, 1)], (100.0 + chain) / 2)
        diffs, _ = study1b.test_differences(self.rows, 6)
        self.assertEqual(diffs["B2"][0], 0.0)
        self.assertAlmostEqual(diffs["B2"][1], (100.0 + chain) / 2 - 75.0)
        self.assertEqual(diffs["B2"][2], 25.0)

    def test_family_seeds_margins_and_holm(self):
        """The fixture's N = 16 set has missing hx and om tries, so B1 and B2 are held by the gate (A1); B3 reads, with the held tests in
        their Holm places at p = 1. Ungated (incomplete=[]), every test matches run_family on the differences."""
        for label, margin in study1b.MARGINS:
            c = self.res["confirmatory"][label]
            self.assertEqual(c["margin"], margin)
            self.assertEqual(set(c["views"]), set(scoring.VIEWS))
            for v in c["views"].values():
                self.assertEqual(set(v["holm_thresholds"]), {"B1", "B2", "B3"})
                self.assertEqual(v["seed"], 20261013)
                self.assertEqual(v["B"], 300)
                self.assertEqual(v["tests"]["B3"]["seed"], bootstrap.derive_seed(20261013, "B3"))
                self.assertEqual(v["seeds"], {t: bootstrap.derive_seed(20261013, t) for t in ("B1", "B2", "B3")})
        diffs, _ = study1b.test_differences(self.rows, 6)
        m = max(len(v) for v in diffs.values())
        again = bootstrap.run_family({"B1": [-1000.0] * m, "B2": [-1000.0] * m, "B3": diffs["B3"]}, margin=-5.0, B=300, seed=20261013)
        dep = self.res["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["tests"]
        self.assertEqual(dep["B3"]["p"], again["tests"]["B3"]["p"])
        self.assertEqual(list(dep["B3"]["ci95"]), list(again["tests"]["B3"]["ci95"]))
        self.assertEqual(dep["B3"]["reading"], again["tests"]["B3"]["reading"])
        ungated = study1b.confirmatory(self.rows, 6, 300, incomplete=[])["primary_margin_5"]["views"]["as_deployed"]["tests"]
        full = bootstrap.run_family(diffs, margin=-5.0, B=300, seed=20261013)
        for t in diffs:
            self.assertEqual(ungated[t]["p"], full["tests"][t]["p"])
            self.assertEqual(list(ungated[t]["ci95"]), list(full["tests"][t]["ci95"]))

    # ------------------------------------------------------------ the completeness gate and the exclude-missing view (A1)

    def test_completeness_counts_per_test_and_arm(self):
        """Designed = the requests sent (a missing try included), final, missing; B1 and B2 share the N = 16 set and arms."""
        comp = self.res["completeness"]
        self.assertEqual(comp["B1"]["arms"], {"hx": {"designed": 60, "final": 58, "missing": 2},
                                              "om": {"designed": 12, "final": 11, "missing": 1}})
        self.assertEqual(comp["B2"]["arms"], comp["B1"]["arms"])
        self.assertEqual((comp["B1"]["completed"], comp["B2"]["completed"], comp["B3"]["completed"]), (False, False, True))
        self.assertEqual(comp["B3"]["arms"], {"hx": {"designed": 40, "final": 40, "missing": 0},
                                              "om": {"designed": 8, "final": 8, "missing": 0}})
        self.assertEqual(comp["B1"]["reading"], study1b.NOT_COMPLETED)
        self.assertNotIn("reading", comp["B3"])
        self.assertEqual(study1b.not_completed(self.rows), ["B1", "B2"])

    def test_not_completed_in_every_view_and_margin(self):
        for label, _ in study1b.MARGINS:
            c = self.res["confirmatory"][label]
            self.assertEqual(c["completed"], {"B1": False, "B2": False, "B3": True})
            for v in c["views"].values():
                for t in ("B1", "B2"):
                    self.assertEqual(v["tests"][t], {"n": 0, "reading": study1b.NOT_COMPLETED, "declared": False, "d": None,
                                                     "ci95": None, "p": 1.0})
                self.assertEqual(v["not_completed"], ["B1", "B2"])
                self.assertEqual(v["not_run"], [])
            self.assertEqual(c["template"]["B1"], "Test B1 was not completed: 3 of its 72 designed tries have no final record, so we give "
                                                  "it no reading.")                                 # §10's line: m, n over both arms
            self.assertEqual(c["template"]["B2"], c["template"]["B1"].replace("B1", "B2"))
            self.assertEqual((c["headline_no_worse"]["B1"], c["headline_no_worse"]["B2"]), (False, False))
        self.assertEqual(self.res["error_ratios"]["B1"], {"reading": study1b.NOT_COMPLETED})
        self.assertEqual(self.res["per_form"]["B1"]["label"], "not completed; descriptive only")
        self.assertNotIn("label", self.res["per_form"]["B3"])
        views = {v: {"tests": {"B1": {"reading": study1b.NOT_COMPLETED}}} for v in scoring.VIEWS}
        with self.assertRaises(ValueError):                                                     # the line needs the counts
            study1b.template(views, "B1")
        self.assertEqual(study1b.template(views, "B1", self.res["completeness"]), self.res["confirmatory"]["primary_margin_5"]["template"]["B1"])

    def test_per_form_of_a_held_test_uses_its_final_tries_only(self):
        """Edith L-2: B1 is held, so its per-form numbers leave the missing tries out (not wrong): hx base 001's pieces form is 7 right
        of the 9 tries with a record; om's 1 right of 2; d = (0 + (700/9 - 50) + 0) / 3. B3 (completed) is as deployed."""
        pf = self.res["per_form"]["B1"]["16x1"]
        self.assertAlmostEqual(pf["h"]["mean"], (100.0 + 700.0 / 9 + 100.0) / 3)
        self.assertAlmostEqual(pf["o"]["mean"], (100.0 + 50.0 + 100.0) / 3)
        self.assertAlmostEqual(pf["d"]["mean"], (700.0 / 9 - 50.0) / 3)
        self.assertEqual(self.res["per_form"]["B1"]["1x16"]["h"]["mean"], (100.0 + 50.0 + 100.0) / 3)   # base 002: 9 of 9, not 9 of 10

    def test_k_below_1_and_not_completed_b2_reads_not_run(self):
        dep = study1b.confirmatory(self.rows, 0, 100)["primary_margin_5"]["views"]["as_deployed"]
        self.assertEqual((dep["tests"]["B2"]["reading"], dep["tests"]["B1"]["reading"]), (study1b.NOT_RUN, study1b.NOT_COMPLETED))
        self.assertEqual((dep["not_run"], dep["not_completed"]), (["B2"], ["B1"]))

    def test_exclude_missing_view_by_hand(self):
        """Only kind "missing" left out, as deployed: hx base 001 pieces 7 right of the 9 left (the refusal kept, wrong), chain 5 of
        10: (700/9 + 50) / 2; om base 001 75, base 002's chain 1 right of the 1 left: 100. B1 = mean of (0, (700/9+50)/2 - 75, 0).
        The vote holds k to the tries left (designed=0). Not gated: B1 and B2 read here."""
        ex = self.res["missing_left_out"]
        self.assertEqual(ex["label"], study1b.EXCLUDE_MISSING_LABEL)
        self.assertEqual(ex["missing_left_out"], {"B1": {"hx": 2, "om": 1}, "B2": {"hx": 2, "om": 1}, "B3": {"hx": 0, "om": 0}})
        self.assertEqual(ex["bases_per_test"], {"B1": 3, "B2": 3, "B3": 2})
        self.assertEqual(ex["not_completed"], ["B1", "B2"])
        kept = [r for r in self.rows if r["kind"] != "missing"]
        diffs, _ = study1b.test_differences(kept, 6, "as_deployed", designed=0)
        self.assertEqual(diffs["B1"][0], 0.0)
        self.assertAlmostEqual(diffs["B1"][1], (700.0 / 9 + 50.0) / 2 - 75.0)
        self.assertEqual(diffs["B1"][2], 0.0)
        for label, margin in study1b.MARGINS:
            fam = ex[label]["as_deployed"]
            main = self.res["confirmatory"][label]["views"]["as_deployed"]
            # Edith L-1: B1 and B2 (not completed) hold their Holm places at p = 1 here too, so B3 (completed) EQUALS the main view
            self.assertEqual(fam["tests"]["B3"], main["tests"]["B3"])
            self.assertEqual(fam["holm_thresholds"], main["holm_thresholds"])
            for t in ("B1", "B2"):                                                                # description only, never a reading
                x = fam["tests"][t]
                self.assertEqual(x["label"], "not completed; descriptive only")
                self.assertNotIn("reading", x)
                self.assertNotIn("declared", x)
                self.assertEqual(x["n_base"], 3)
                self.assertEqual(x["bases_used"], [f"{N16}-000", f"{N16}-001", f"{N16}-002"])
                self.assertIsNotNone(x["ci95"][0])
            self.assertAlmostEqual(fam["tests"]["B1"]["d"], sum(diffs["B1"]) / 3)
            self.assertAlmostEqual(fam["tests"]["B2"]["d"], sum(diffs["B2"]) / 3)
        complete = [r for r in self.rows if not (r["kind"] == "missing" and r["tag"] in ("hx", "om"))]
        self.assertEqual(study1b.exclude_missing_view(complete, 6, 50), study1b.NO_MISSING)   # computed only when a test try is missing

    def test_sensitivity_without_the_exposed_bases(self):
        """D-97: the family and error ratios re-run without N16 base 000 and N6 bases 000 and 003 (only 000 exists in the fixture), same
        k, B, seeds and Holm; labelled."""
        sens = self.res["sensitivity_exposed_bases_excluded"]
        self.assertEqual(sens["label"], "sensitivity: exposed bases excluded")
        self.assertEqual(sens["excluded"], {N16: [f"{N16}-000"], N6: [f"{N6}-000", f"{N6}-003"]})
        self.assertEqual(sens["bases_per_test"], {"B1": 2, "B2": 2, "B3": 1})            # 3 - 1 and 2 - 1 fixture bases
        kept = study1b.without_exposed(self.rows)
        self.assertFalse(any(r["base_id"] in (f"{N16}-000", f"{N6}-000") for r in kept))
        self.assertTrue(any(r["base_id"] == f"{N12}-000" for r in kept))               # the 12-step set is not touched
        k = self.kdoc["k"]
        self.assertEqual(sens["not_completed"], ["B1", "B2"])                       # the run's gate (A1)
        self.assertEqual(sens["confirmatory"], study1b.confirmatory(kept, k, 300, ["B1", "B2"], study1b.completeness(self.rows)))
        self.assertIn("3 of its 72 designed tries", sens["confirmatory"]["primary_margin_5"]["template"]["B1"])   # the whole run's counts
        dep = sens["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]
        self.assertEqual(set(dep["holm_thresholds"]), {"B1", "B2", "B3"})
        self.assertEqual(dep["tests"]["B3"]["seed"], bootstrap.derive_seed(20261013, "B3"))
        self.assertEqual((dep["tests"]["B1"]["reading"], dep["tests"]["B2"]["reading"]), (study1b.NOT_COMPLETED,) * 2)
        self.assertEqual(set(sens["error_ratios"]), {"B1", "B2", "B3"})
        self.assertEqual(sens["error_ratios"]["B1"], {"reading": study1b.NOT_COMPLETED})

    def test_headline_needs_all_three_views(self):
        views = {v: {"tests": {"B1": {"reading": bootstrap.NON_INFERIOR}}} for v in scoring.VIEWS}
        self.assertTrue(study1b.template(views, "B1").startswith("holds"))
        views["truncations_out"]["tests"]["B1"]["reading"] = bootstrap.INCONCLUSIVE
        self.assertTrue(study1b.template(views, "B1").startswith("no worse as deployed only"))

    def test_b2_not_run_keeps_its_holm_place(self):
        res = study1b.confirmatory(self.rows, 0, 200)["primary_margin_5"]
        dep = res["views"]["as_deployed"]
        self.assertEqual(dep["tests"]["B2"]["p"], 1.0)
        self.assertEqual(dep["tests"]["B2"]["reading"], study1b.NOT_RUN)
        self.assertEqual(set(dep["holm_thresholds"]), {"B1", "B2", "B3"})
        self.assertEqual(res["template"]["B2"], "not run")
        self.assertEqual(study1b.error_ratios(self.rows, 0, 50)["B2"], {"reading": study1b.NOT_RUN})

    def test_error_ratio_seed_and_values(self):
        self.assertEqual(self.res["error_ratios"]["B1"], {"reading": study1b.NOT_COMPLETED})     # held by the gate (A1)
        er = study1b.error_ratios(self.rows, 6, 300, incomplete=[])["B1"]                      # ungated: the hand values
        self.assertAlmostEqual(er["E_ch"], 0.45)                               # 0 + 0.40 + 0.05
        self.assertAlmostEqual(er["E_cmp"], 0.5)                               # 0 + 0.25 + 0.25
        self.assertAlmostEqual(er["R"], 0.9)
        self.assertEqual(er["seed"], bootstrap.derive_seed(20261013, "B1:error_ratio"))
        self.assertEqual(main_analysis.ERROR_RATIO_SEED, 20261011)            # the locked module's seed is restored
        sc = study1b.test_scores(self.rows, 6)["B1"]
        bases = sorted(sc["c"])
        ech = {b: (100 - sc["c"][b]) / 100 for b in bases}
        ecm = {b: (100 - sc["o"][b]) / 100 for b in bases}
        rng = random.Random(bootstrap.derive_seed(20261013, "B1:error_ratio"))
        ratios = []
        for _ in range(300):
            d = rng.choices(bases, k=3)
            a, o = math.fsum(ech[x] for x in d), math.fsum(ecm[x] for x in d)
            if o == 0:
                if a:
                    ratios.append(math.inf)
                continue
            ratios.append(a / o)
        ratios.sort()
        lo, hi = ratios[int(math.floor(0.025 * len(ratios)))], ratios[int(math.ceil(0.975 * len(ratios))) - 1]
        self.assertEqual(er["ci95"], [main_analysis._show(lo), main_analysis._show(hi)])

    def test_error_ratio_zero_errors_uses_designed_tries(self):
        er = self.res["error_ratios"]["B3"]                                    # Opus all right at N = 6
        self.assertFalse(er["defined"])
        self.assertEqual(er["comparator_designed_tries"], 8)                   # 2 bases x 2 forms x 2 tries (160 in the real set)
        self.assertAlmostEqual(er["comparator_error_rate_upper95"], 1.0 - 0.025 ** (1.0 / 8))
        self.assertAlmostEqual(er["comparator_error_rate_upper95_over_bases"], 1.0 - 0.025 ** (1.0 / 2))
        self.assertEqual(er["comparator_note"], "comparator: 0 errors in 8 designed tries")

    # ------------------------------------------------------------ costs, §6

    def test_cost_per_answer_by_hand(self):
        """om at N = 16, item 9b: each base the mean over its 2 designed tries, a try with no record at $0: base 002's chain form is
        ($0.034 + $0) / 2; pooled per base (0.034, 0.034, 0.0255), mean 0.0935 / 3. The vote at k = 6 costs 6 hx answers."""
        c = self.res["costs_beside_tests"]
        self.assertAlmostEqual(c["B1"]["comparator"]["pooled"]["list_usd"], 0.0935 / 3)
        self.assertAlmostEqual(c["B2"]["challenger"]["16x1"]["list_usd"], 6 * 0.0051 * 29 / 30)   # base 001 pieces: 9 calls of 10
        self.assertEqual(c["B1"]["k_measured"], 6)
        self.assertEqual(c["B1"]["wording"], "about 1/6 of the cost per answer (k measured)")

    def test_section6_names_seeds_and_intervals(self):
        arms = self.res["descriptive"]["arms"]
        hx = arms["hx@16"]
        self.assertEqual(hx["16x1"]["bootstrap_name"], "1b:hx:16:16x1")
        self.assertEqual(hx["pooled"]["bootstrap_name"], "1b:hx:16:pooled")
        vals = {self.b(N16, 0): 100.0, self.b(N16, 1): 700.0 / 9, self.b(N16, 2): 100.0}     # B1 held: final tries only (C1)
        ci = curve.cluster_bootstrap([sorted(vals)], lambda s: math.fsum(vals[b] for b in s) / len(s), "1b:hx:16:16x1", draws=200,
                                     seed=20261013)
        self.assertEqual(hx["16x1"]["ci95"], list(ci))
        sl = arms["sl@6"]                                                       # one try: Clopper-Pearson, per form and pooled
        self.assertEqual((sl["6x1"]["x"], sl["6x1"]["n_base"], sl["6x1"]["mean"]), (1, 2, 50.0))
        lo, hi = report_arms.clopper_pearson(3, 4)
        self.assertEqual((sl["pooled"]["x"], sl["pooled"]["tries"]), (3, 4))
        self.assertEqual(sl["pooled"]["ci95"], [100 * lo, 100 * hi])
        self.assertEqual(sl["pooled"]["interval"], "clopper-pearson")
        self.assertIsNotNone(sl["6x1"]["cpc"]["cpc"])
        pf = self.res["per_form"]["B1"]["16x1"]
        self.assertEqual(pf["d"]["bootstrap_name"], "1b:B1:16:16x1:d")
        self.assertAlmostEqual(pf["d"]["mean"], (700.0 / 9 - 50.0) / 3)                 # B1 is held: its final tries only (L-2)

    def test_effort_figure_and_length_curve(self):
        fig = self.res["descriptive"]["effort_figure"]
        self.assertEqual([p["effort"] for p in fig["N=6"]["haiku"]], ["off", "max"])
        self.assertEqual([p["tag"] for p in fig["N=16"]["haiku"]], ["hm", "hx"])
        self.assertEqual([p["tag"] for p in fig["N=16"]["opus"]], ["om"])
        self.assertEqual(fig["study1_points"]["label"], "Study 1 (other puzzles, exploratory)")
        lc = self.res["descriptive"]["length_curve"]
        self.assertEqual(set(lc["haiku-max"]), {"6", "12", "16"})
        self.assertEqual(set(lc["haiku-medium"]), {"6", "16"})
        self.assertIsNone(lc["haiku-medium"]["6"])                             # hm not in this fixture's N = 6 plan
        self.assertEqual(lc["ladder"]["label"], "ladder (D-87), other puzzles")

    def test_vote_curve_k_1_to_10(self):
        vc = self.res["descriptive"]["vote_curve_n16"]
        self.assertEqual([p["k"] for p in vc["points"]], list(range(1, 11)))
        self.assertEqual([p["k"] for p in vc["points"] if p["equal_money_k"]], [6])
        p6 = vc["points"][5]
        self.assertAlmostEqual(p6["1x16"]["mean"], (100.0 + 100.0 * 206 / 210 + 100.0) / 3)
        self.assertAlmostEqual(p6["pooled"]["cost_per_answer"], 6 * vc["points"][0]["pooled"]["cost_per_answer"])
        k1 = vc["points"][0]["16x1"]["mean"]                                    # vote@1 = the single-try share, on the final tries
        self.assertAlmostEqual(k1, (100.0 + 700.0 / 9 + 100.0) / 3)             # (B1 held, C1): base 001 7 of its 9 final tries
        self.assertEqual(vc["label"], study1b.NOT_COMPLETED_DESCRIPTIVE)
        self.assertEqual(vc["tries"]["pooled"], {"designed": 60, "final": 58, "missing": 2})
        self.assertEqual(vc["points"][0]["16x1"]["missing"], 1)

    def test_compliance_counts(self):
        rates = self.res["descriptive"]["format_refusals_truncations_missing"]["item_16_rates"]
        hx = rates[N16]["hx 16x1"]
        self.assertEqual(hx["designed_calls"], 30)
        self.assertEqual(hx["missing"]["count"], 1)
        self.assertEqual(hx["refusals_by_category"]["cyber"]["count"], 1)
        self.assertEqual(rates[N16]["hx 1x16"]["truncations"]["count"], 1)
        flags = self.res["descriptive"]["format_refusals_truncations_missing"]["item_17_flags"]
        self.assertTrue(flags["ho 1x6"]["fires"])                               # 1 unreadable of 9 answered (> 5%)

    def test_cli_refuses_to_overwrite(self):
        out = self.td / "analysis.json"
        out.write_text("{}")
        with self.assertRaises(SystemExit):
            study1b.main(["--run", str(self.run_dir), "--k", str(self.k_path), "--out", str(out)])

    def test_cli_end_to_end(self):
        """The sealed entry point: plan + run + k.json -> one JSON file (full B and draws on the small fixture)."""
        out = self.td / "analysis-cli.json"
        self.assertEqual(study1b.main(["--run", str(self.run_dir), "--k", str(self.k_path), "--plan", str(self.plan_path),
                                       "--out", str(out)]), 0)
        doc = json.loads(out.read_text())
        self.assertEqual(doc["constants"]["B"], 10_000)
        self.assertEqual(doc["constants"]["draws"], 2_000)
        self.assertEqual(doc["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["B"], 10_000)
        self.assertEqual(doc["inputs"]["k_json_sha256"], study1b._sha(self.k_path))

    def test_output_is_json(self):
        text = json.dumps(self.res, sort_keys=True, default=str)
        self.assertIn("choices", json.loads(text))


if __name__ == "__main__":
    unittest.main()
