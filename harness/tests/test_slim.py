"""The Study 1b slim runner (harness/pareto/slim.py): the plan file's checks, custom ids, the booking, wave 0 and the section 7 limit
rule (counts only, never answer_text), the cost-only cut order, the 2% pause, resume, and full fake runs on small frozen sets. Offline
only: DryTransport and FakeTransport, never live."""

import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest import mock

from harness.analysis.kscript import parse_custom_id
from harness.pareto import slim
from harness.pareto.batch import PausedForTruncation
from harness.pareto.calllog import CallLog
from harness.pareto.pilot import HAIKU, OPUS, load_set
from harness.pareto.prices import estimate_input_tokens, worst_case
from harness.pareto.slim import PlanError
from harness.pareto.transport import DryTransport, FakeTransport, TransportError
from harness.taskgen import freeze
from harness.tests.fakes import guard, reply
from harness.tests.test_resume import FlakyTransport

import atexit as _atexit
import shutil as _shutil


def _tmpdir() -> Path:
    """A temp folder removed when the test process exits: these tests write nowhere else."""
    d = Path(tempfile.mkdtemp(prefix="pareto-test-"))
    _atexit.register(_shutil.rmtree, d, True)
    return d


_ROOT = None


def frozen_sets():
    """Four small frozen sets (written once per test process, verified on load like the real ones): two test sets (6 and 16 steps,
    3 and 2 base puzzles) and two calibration sets (2 base puzzles each)."""
    global _ROOT
    if _ROOT is None:
        _ROOT = _tmpdir()
        for name, setting, n_base in (("slimtest-ledger-l14n6-v1", "l14n6", 3), ("slimtest-ledger-l14n16-v1", "l14n16", 2),
                                      ("slimcal-ledger-l14n6-v1", "l14n6", 2), ("slimcal-ledger-l14n16-v1", "l14n16", 2)):
            freeze.write_set(_ROOT / name, "ledger", setting, name, n_base, "d31", "scratch")
    return _ROOT


def _sha(name):
    return json.loads((frozen_sets() / name / "manifest.json").read_text())["items_sha256"]


def cb(total="0.01", calls=10):
    return {"cost_usd_sum": total, "calls": calls, "source": "test"}


def test_plan():
    root = frozen_sets()
    return {
        "study": "study1b-test", "run_id_prefix": "t-",
        "sets": [
            {"set": str(root / "slimtest-ledger-l14n6-v1"), "items_sha256": _sha("slimtest-ledger-l14n6-v1"), "steps": 6, "arms": [
                {"tag": "hx", "model": HAIKU, "effort": "max", "n": 2, "role": "confirmatory", "max_tokens": 30000, "cost_basis": cb("0.002", 1)},
                {"tag": "om", "model": OPUS, "effort": "medium", "n": 1, "role": "confirmatory", "max_tokens": 4000, "cost_basis": cb("0.02", 1)},
                {"tag": "ho", "model": HAIKU, "effort": "medium", "n": 1, "role": "descriptive", "thinking_off": True, "max_tokens": 4000,
                 "cost_basis": cb("0.0005", 1)},
                {"tag": "hh", "model": HAIKU, "effort": "high", "n": 1, "role": "descriptive", "calibrate": {"floor": 6000, "wave0_max_tokens": 64000}},
                {"tag": "ox", "model": OPUS, "effort": "max", "n": 1, "role": "descriptive", "calibrate": {"floor": 4000, "wave0_max_tokens": 64000}}]},
            {"set": str(root / "slimtest-ledger-l14n16-v1"), "items_sha256": _sha("slimtest-ledger-l14n16-v1"), "steps": 16, "arms": [
                {"tag": "hx", "model": HAIKU, "effort": "max", "n": 2, "role": "confirmatory", "calibrate": {"floor": 96000, "wave0_max_tokens": 128000}},
                {"tag": "om", "model": OPUS, "effort": "medium", "n": 1, "role": "confirmatory", "max_tokens": 9000, "cost_basis": cb("0.03", 1)}]}],
        "calibration": {"sets": [{"set": str(root / f"slimcal-ledger-l14n{n}-v1"), "items_sha256": _sha(f"slimcal-ledger-l14n{n}-v1"), "steps": n}
                                 for n in (6, 16)],
                        "base_puzzles": 2, "tries": 1,
                        "rule": {"factor": 2, "round_up_to": 1000, "max_tokens_cap": 128000, "on_truncation": 128000}},
        "cut": {"multiplier": "1.5", "share_of_cap": "0.9", "order": [{"name": "Opus-max at 6", "arms": [[6, "ox"]]},
                                                                     {"name": "Haiku-high at 6", "arms": [[6, "hh"]]}],
                "never_cut": [[6, "hx"], [6, "om"], [16, "hx"], [16, "om"]]},
    }


# items: test6 3 base x 2 forms = 6; test16 2 x 2 = 4; cal6 and cal16 2 x 2 = 4 each
TEST_CALLS = 6 * (2 + 1 + 1 + 1 + 1) + 4 * (2 + 1)          # 36 + 12 = 48
WAVE0_CALLS = 4 * 2 + 4 * 1                               # cal6: hh, ox; cal16: hx -> 12


def tokens_fake(out_tokens=None, stop=None, text="Answer: 1 = 5"):
    """A reply function: output tokens and stop reason chosen by (phase, model, effort) from the prompt and params."""
    out_tokens = out_tokens or {}
    stop = stop or {}
    cal_prompts = {it["prompt"] for name in ("slimcal-ledger-l14n6-v1", "slimcal-ledger-l14n16-v1")
                   for it in load_set(frozen_sets() / name)[1]}

    def fake(p):
        phase = "w0" if p["messages"][0]["content"] in cal_prompts else "test"
        key = (phase, p["model"], p["output_config"]["effort"], p["max_tokens"])
        tout = next((v for k, v in out_tokens.items() if all(a is None or a == b for a, b in zip(k, key))), 1000)
        st = next((v for k, v in stop.items() if all(a is None or a == b for a, b in zip(k, key))), "end_turn")
        if st == "max_tokens":
            tout = p["max_tokens"]
        return reply(model=p["model"], text=text, stop=st, tout=tout)
    return fake


def run(plan, t, out, g=None, **kw):
    return slim.run_slim(g or guard(run_cap="100"), t, out, plan, sleep=lambda s: None, **kw)


def records(out):
    return list(CallLog(Path(out) / "calls.jsonl").records())


def sent_ids(t):
    return [r["custom_id"] for reqs in t.batches.values() for r in reqs]


class Validation(unittest.TestCase):
    def bad(self, mutate, msg=None):
        p = test_plan()
        mutate(p)
        with self.assertRaises(PlanError, msg=msg):
            slim.validate_plan(p)

    def arm(self, p, steps, tag):
        return next(a for s in p["sets"] if s["steps"] == steps for a in s["arms"] if a["tag"] == tag)

    def test_the_test_plan_and_the_study_plan_pass(self):
        slim.validate_plan(test_plan())
        real = slim.read_plan(Path(slim.ROOT) / "data" / "plans" / "study1b-plan.json")
        self.assertEqual(slim.missing_costs(real), [])                                   # the three ladder costs are filled
        blank = json.loads(json.dumps(real))                                              # a blank cost is still caught
        self.arm(blank, 16, "om")["cost_basis"] = {"cost_usd_sum": None, "calls": None, "source": "TO FILL"}
        self.assertEqual(slim.missing_costs(blank), [(16, "om")])

    def test_tags(self):
        for tag in ("Hx", "h1", "h-x", "", "rthx", "es"):
            self.bad(lambda p, tag=tag: self.arm(p, 6, "hx").update(tag=tag), tag)
        self.bad(lambda p: self.arm(p, 6, "om").update(tag="hx"))                       # twice in one set
        p = test_plan()
        slim.validate_plan(p)                                                           # hx and om at 6 AND 16: different sets, fine

    def test_models_efforts_thinking_off_and_limits(self):
        self.bad(lambda p: self.arm(p, 6, "om").update(model="claude-opus-4"))
        self.bad(lambda p: self.arm(p, 6, "om").update(effort="extreme"))
        self.bad(lambda p: self.arm(p, 6, "ho").update(effort="xhigh"))                  # thinking off at xhigh
        self.bad(lambda p: self.arm(p, 6, "ho").update(effort="max"))
        self.bad(lambda p: self.arm(p, 6, "om").update(thinking_off=True))               # not Haiku
        self.bad(lambda p: self.arm(p, 6, "om").update(max_tokens=128001))
        self.bad(lambda p: self.arm(p, 6, "om").update(max_tokens=0))
        self.bad(lambda p: self.arm(p, 6, "hh")["calibrate"].update(wave0_max_tokens=200000))
        self.bad(lambda p: self.arm(p, 6, "om").update(n=100))
        self.bad(lambda p: self.arm(p, 6, "om").update(role="primary"))
        for effort in ("low", "medium", "high", "xhigh", "max"):                         # every effort on every model
            for model in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"):
                p = test_plan()
                self.arm(p, 6, "om").update(model=model, effort=effort)
                slim.validate_plan(p)

    def test_an_arm_is_either_measured_or_calibrated(self):
        self.bad(lambda p: self.arm(p, 6, "om").update(calibrate={"floor": 4000, "wave0_max_tokens": 64000}))
        self.bad(lambda p: self.arm(p, 6, "hh").pop("calibrate"))
        self.bad(lambda p: self.arm(p, 6, "om").pop("cost_basis"))
        self.bad(lambda p: self.arm(p, 6, "hh").update(cost_basis=cb()))
        self.bad(lambda p: self.arm(p, 6, "om")["cost_basis"].update(cost_usd_sum="abc"))
        p = test_plan()
        self.arm(p, 6, "om")["cost_basis"].update(cost_usd_sum=None, calls=None)         # to fill: valid, but listed
        self.assertEqual(slim.missing_costs(slim.validate_plan(p)), [(6, "om")])

    def test_calibration_and_cut_blocks(self):
        self.bad(lambda p: p["calibration"]["sets"].pop())                                # no wave-0 set at 16 for hx
        self.bad(lambda p: p["calibration"]["sets"][0].update(set=p["sets"][0]["set"]))  # a test set used for calibration
        self.bad(lambda p: self.arm(p, 16, "hx")["calibrate"].update(floor=128001))
        self.bad(lambda p: p["calibration"]["rule"].update(on_truncation=130000))
        self.bad(lambda p: p["cut"]["order"].append({"name": "B1", "arms": [[16, "hx"]]}))   # never cut
        self.bad(lambda p: p["cut"]["order"].append({"name": "?", "arms": [[12, "hx"]]}))    # no such arm
        self.bad(lambda p: p["cut"].update(share_of_cap=0.9))                             # a decimal STRING
        self.bad(lambda p: p["sets"][1].update(steps=6))                                  # one set per length

    def test_sets_are_checked_against_their_manifest(self):
        p = test_plan()
        slim.load_sets(p)
        p["sets"][0]["items_sha256"] = "0" * 64
        with self.assertRaises(PlanError):
            slim.load_sets(p)
        p = test_plan()
        p["sets"][1]["steps"] = 12
        with self.assertRaises(PlanError):
            slim.load_sets(p)
        p = test_plan()
        p["calibration"]["base_puzzles"] = 3                                               # the calibration sets hold 2
        with self.assertRaises(PlanError):
            slim.load_sets(p)


class Requests(unittest.TestCase):
    def setUp(self):
        self.plan = test_plan()
        self.test, self.cal = slim.load_sets(self.plan)

    def test_test_custom_ids_and_params(self):
        reqs = [r for s, m, i in self.test for r in slim.build_test_requests(self.plan, s, m, i)]
        self.assertEqual(len(reqs), TEST_CALLS)
        for cid, p, m in reqs:
            c = parse_custom_id(cid)
            self.assertEqual((c["setup"], c["sample"], c["puzzle"], c["set_id"]), (m["setup"], m["sample"], m["item_id"], m["set_id"]))
            self.assertRegex(cid, r"-[a-z]+-\d\d$")
            self.assertEqual(m["phase"], "test")
        by = {(m["set_id"], m["setup"]): p for _, p, m in reqs}
        self.assertEqual(by[("slimtest-ledger-l14n6-v1", "hh")]["max_tokens"], 6000)        # no limits given: the floor
        self.assertEqual(by[("slimtest-ledger-l14n6-v1", "ho")]["thinking"], {"type": "disabled"})
        self.assertEqual(by[("slimtest-ledger-l14n16-v1", "hx")]["max_tokens"], 96000)
        lim = slim.build_test_requests(self.plan, *self.test[0], limits={"hh": 11000}, cut=["ox"])
        self.assertEqual({p["max_tokens"] for _, p, m in lim if m["setup"] == "hh"}, {11000})
        self.assertNotIn("ox", {m["setup"] for _, _, m in lim})

    def test_wave0_ids_are_on_the_calibration_sets(self):
        w0 = slim.build_wave0_requests(self.plan, self.test, self.cal)
        self.assertEqual(len(w0), WAVE0_CALLS)
        per = Counter((m["calibrates_steps"], m["setup"]) for _, _, m in w0)
        self.assertEqual(per, {(6, "hh"): 4, (6, "ox"): 4, (16, "hx"): 4})
        for cid, p, m in w0:
            c = parse_custom_id(cid)
            self.assertTrue(c["set_id"].startswith("slimcal-"))
            self.assertEqual((c["sample"], m["phase"]), (1, "calibration"))
            self.assertEqual(p["max_tokens"], 128000 if m["setup"] == "hx" else 64000)
            self.assertLess(int(m["base_index"]), 2)


class LimitRule(unittest.TestCase):
    RULE = {"factor": 2, "round_up_to": 1000, "max_tokens_cap": 128000, "on_truncation": 128000}

    def test_arithmetic(self):
        lim = slim.calibrated_limit
        self.assertEqual(lim(2345, False, 6000, self.RULE), 6000)          # 4,690 -> 5,000, under the floor
        self.assertEqual(lim(4100, False, 6000, self.RULE), 9000)          # 8,200 rounded UP
        self.assertEqual(lim(3000, False, 4000, self.RULE), 6000)          # an exact multiple stays
        self.assertEqual(lim(40000, False, 6000, self.RULE), 80000)
        self.assertEqual(lim(70000, False, 14000, self.RULE), 128000)      # capped
        self.assertEqual(lim(10, True, 6000, self.RULE), 128000)           # a truncation gives 128,000
        self.assertEqual(lim(30000, False, 96000, self.RULE), 96000)       # hx's floor
        self.assertEqual(lim(50001, False, 96000, self.RULE), 101000)
        self.assertEqual(lim(0, False, 3000, self.RULE), 3000)             # a refusal with no output: the floor

    def test_counts_never_read_answer_text(self):
        class Poisoned(dict):
            def __getitem__(self, k):
                if k == "answer_text":
                    raise AssertionError("the rule read answer_text")
                return dict.__getitem__(self, k)

            def get(self, k, d=None):
                if k == "answer_text":
                    raise AssertionError("the rule read answer_text")
                return dict.get(self, k, d)

            def items(self):
                raise AssertionError("the rule walked the whole record")
            values = keys = __iter__ = items

        recs = [Poisoned({"custom_id": f"c{i}", "final": True, "kind": "answered", "stop_reason": "end_turn", "answer_text": "SECRET",
                          "meta": {"calibrates_steps": 6, "setup": "hh"}, "usage_raw": {"output_tokens": 1000 + i}, "cost_usd": "0.001"})
                for i in range(3)]
        recs.append(Poisoned({"custom_id": "c9", "final": True, "kind": "truncated", "stop_reason": "max_tokens", "answer_text": "SECRET",
                              "meta": {"calibrates_steps": 6, "setup": "ox"}, "usage_raw": {"output_tokens": 64000}, "cost_usd": "0.64"}))
        c = slim.wave0_counts(recs, ["c0", "c1", "c2", "c9"])
        self.assertEqual(c[(6, "hh")]["output_tokens_max"], 1002)
        self.assertEqual((c[(6, "hh")]["final"], c[(6, "ox")]["truncated"]), (3, 1))

        class PoisonLog:
            def __init__(self):
                self.lines = []

            def records(self):
                return iter(recs + self.lines)

            def write(self, line):
                self.lines.append(line)
        log = PoisonLog()
        plan = test_plan()
        w0 = [(r["custom_id"], {}, {}) for r in recs]
        line = slim.apply_limits(log, "r", plan, w0)
        got = {(a["steps"], a["tag"]): a["max_tokens"] for a in line["arms"]}
        self.assertEqual(got, {(6, "hh"): 6000, (6, "ox"): 128000, (16, "hx"): 96000})   # hx has no wave-0 record here: its floor
        self.assertIs(slim.apply_limits(log, "r", plan, w0), line)                        # once
        self.assertEqual([x["kind"] for x in log.lines], ["calibration_limits"])


class CutOrder(unittest.TestCase):
    def plan_costs(self):
        plan = test_plan()
        planned = {(6, "hx"): 100, (6, "om"): 10, (6, "ho"): 50, (6, "hh"): 50, (6, "ox"): 10, (16, "hx"): 100, (16, "om"): 10}
        cost = {(6, "hx"): Fraction(1, 1000), (6, "om"): Fraction(2, 100), (6, "ho"): Fraction(5, 10000), (6, "hh"): Fraction(4, 1000),
                (6, "ox"): Fraction(1, 2), (16, "hx"): Fraction(5, 1000), (16, "om"): Fraction(4, 100)}
        return plan, planned, cost

    def test_formula_and_order(self):
        plan, planned, cost = self.plan_costs()
        # sum = 0.1 + 0.2 + 0.025 + 0.2 + 5 + 0.5 + 0.4 = 6.425; projected = 1 + 1.5 x 6.425 = 10.6375
        d = slim.decide_cut(plan, planned, cost, Fraction(1), Fraction(20))
        self.assertEqual((d["projected_usd"], d["cut_arms"], d["still_over"]), ("10.637500000", [], False))   # under 0.9 x 20 = 18
        d = slim.decide_cut(plan, planned, cost, Fraction(1), Fraction(10))                 # limit 9: cut ox -> 1 + 1.5 x 1.425 = 3.1375
        self.assertEqual((d["cut_arms"], d["projected_usd"], d["still_over"]), ([[6, "ox"]], "3.137500000", False))
        self.assertEqual([x["part"] for x in d["cut_parts"]], ["Opus-max at 6"])
        d = slim.decide_cut(plan, planned, cost, Fraction(1), Fraction(34, 10))             # limit 3.06: ox (3.1375, still over) then hh -> 2.8375
        self.assertEqual(d["cut_arms"], [[6, "hh"], [6, "ox"]])
        self.assertFalse(d["still_over"])
        d = slim.decide_cut(plan, planned, cost, Fraction(1), Fraction(2))                  # never under: the order runs out
        self.assertTrue(d["still_over"])
        self.assertNotIn([16, "hx"], d["cut_arms"])
        self.assertEqual(len(d["cut_arms"]), 2)                                             # never hx or om at 6 and 16

    def test_a_missing_cost_refuses(self):
        plan, planned, cost = self.plan_costs()
        cost[(16, "om")] = None
        with self.assertRaises(PlanError):
            slim.decide_cut(plan, planned, cost, Fraction(0), Fraction(100))


class Booking(unittest.TestCase):
    def test_per_arm_booking_is_calls_times_the_guard_worst_case(self):
        plan = test_plan()
        test, cal = slim.load_sets(plan)
        out = slim.slim_plan(guard(run_cap="100"), plan, test, cal)
        self.assertTrue(out["check_floor_total_equals_guard_worst_case"])
        s6 = out["sets"][0]
        om = next(a for a in s6["arms"] if a["tag"] == "om")
        _, man, items = test[0]
        want = sum((worst_case(OPUS, estimate_input_tokens("\n" + it["prompt"]), 4000, batch=True) for it in items), Decimal(0))
        self.assertEqual(Decimal(om["batch_booking_usd"]), want)
        self.assertEqual(om["calls"], 6)
        hh = next(a for a in s6["arms"] if a["tag"] == "hh")
        self.assertEqual((hh["floor"], hh["cap"]), (6000, 128000))
        self.assertLess(Decimal(hh["batch_booking_at_floor_usd"]), Decimal(hh["batch_booking_at_cap_usd"]))
        self.assertEqual(out["wave0"]["calls"], WAVE0_CALLS)
        self.assertEqual(out["test_calls"], TEST_CALLS)
        self.assertEqual(Decimal(out["total_batch_booking_at_floors_usd"]),
                         Decimal(out["wave0"]["batch_booking_usd"]) + sum(Decimal(s["batch_booking_at_floors_usd"]) for s in out["sets"]))
        lim = {"arms": [{"steps": 6, "tag": "hh", "max_tokens": 9000}, {"steps": 6, "tag": "ox", "max_tokens": 4000},
                        {"steps": 16, "tag": "hx", "max_tokens": 96000}]}
        g = slim.slim_plan(guard(run_cap="100"), plan, test, cal, lim)
        hh = next(a for a in g["sets"][0]["arms"] if a["tag"] == "hh")
        self.assertEqual(hh["max_tokens_given_limits"], 9000)


class Runs(unittest.TestCase):
    def test_full_dry_run(self):
        out = _tmpdir()
        r = run(test_plan(), DryTransport(), out)
        self.assertIsNone(r["stopped"])
        self.assertEqual(r["wave0"].answered, WAVE0_CALLS)
        self.assertEqual(sum(s.answered for s in r["test"].values()), TEST_CALLS)
        recs = records(out)
        self.assertEqual([x["kind"] for x in recs if x.get("kind") in ("calibration_limits", "cut")], ["calibration_limits", "cut"])
        # DryTransport answers max_tokens // 4: hh and ox write 16,000 at 64K -> 32,000; hx writes 32,000 at 128K -> 64,000, under its 96,000 floor
        lim = {(a["steps"], a["tag"]): a["max_tokens"] for a in r["limits"]["arms"]}
        self.assertEqual(lim, {(6, "hh"): 32000, (6, "ox"): 32000, (16, "hx"): 96000})
        with open(out / "compact_table.csv") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), WAVE0_CALLS + TEST_CALLS)
        for x in rows:
            if parse_custom_id(x["custom_id"])["set_id"].startswith("slimcal-"):
                self.assertEqual(x["right"], "")                                           # wave 0 is never graded
        self.assertTrue((out / "calibration_limits.json").exists() and (out / "slim_plan.json").exists())
        self.assertIn("Study 1b slim runner", (out / "manifest.json").read_text())

    def test_limits_are_applied_and_a_second_run_sends_nothing(self):
        out = _tmpdir()
        g = guard(run_cap="100")
        fake = tokens_fake(out_tokens={("w0", HAIKU, "high"): 4100, ("w0", HAIKU, "max"): 50001},
                           stop={("w0", OPUS, "max"): "max_tokens"})
        t = FakeTransport(fake)
        r = run(test_plan(), t, out, g)
        self.assertIsNone(r["stopped"])
        lim = {(a["steps"], a["tag"]): a["max_tokens"] for a in r["limits"]["arms"]}
        self.assertEqual(lim, {(6, "hh"): 9000, (6, "ox"): 128000, (16, "hx"): 101000})
        sent = [r2 for reqs in t.batches.values() for r2 in reqs]
        mt = {(parse_custom_id(x["custom_id"])["set_id"], parse_custom_id(x["custom_id"])["setup"]): x["params"]["max_tokens"] for x in sent}
        self.assertEqual(mt[("slimtest-ledger-l14n6-v1", "hh")], 9000)
        self.assertEqual(mt[("slimtest-ledger-l14n6-v1", "ox")], 128000)
        self.assertEqual(mt[("slimtest-ledger-l14n16-v1", "hx")], 101000)
        self.assertEqual(mt[("slimcal-ledger-l14n16-v1", "hx")], 128000)
        # the same command again: nothing new is sent, the limits and the cut are read back, not decided again
        t2 = FakeTransport(lambda p: (_ for _ in ()).throw(AssertionError("sent again")))
        r2 = run(test_plan(), t2, out, g)
        self.assertEqual(r2["limits"]["arms"], r["limits"]["arms"])
        self.assertEqual(sum(1 for x in records(out) if x.get("kind") == "calibration_limits"), 1)
        self.assertEqual(sum(1 for x in records(out) if x.get("kind") == "cut"), 1)
        self.assertEqual(t2.batches, {})

    def test_wave0_is_sent_once_and_limits_wait_for_it(self):
        out = _tmpdir()
        g = guard(run_cap="100")

        def batch_reply(cid, params):                                                     # one wave-0 call errors
            if cid.startswith("slimcal-ledger-l14n6-v1-000-6x1-hh"):
                return {"type": "errored", "error": {"type": "overloaded_error"}}
            return {"type": "succeeded", "message": reply(model=params["model"], tout=1000)}
        t = FakeTransport(batch_reply=batch_reply)
        r = run(test_plan(), t, out, g)
        self.assertEqual(r["stopped"], "calibration_incomplete")
        self.assertFalse([x for x in records(out) if x.get("kind") == "calibration_limits"])
        t2 = FakeTransport(lambda p: reply(model=p["model"], tout=1000))
        r2 = run(test_plan(), t2, out, g)
        self.assertIsNone(r2["stopped"])
        self.assertEqual([x["custom_id"] for reqs in t2.batches.values() for x in reqs if x["custom_id"].startswith("slimcal")],
                         ["slimcal-ledger-l14n6-v1-000-6x1-hh-01"])                        # only the errored one, again

    def test_the_cut_leaves_arms_out_and_never_the_confirmatory_ones(self):
        out = _tmpdir()
        # wave 0: Opus-max writes 60,000 tokens per call (0.60 USD Batch each): projected is far over 0.9 x 5 USD
        fake = tokens_fake(out_tokens={("w0", OPUS, "max"): 60000})
        t = FakeTransport(fake)
        r = run(test_plan(), t, out, guard(run_cap="5"))
        self.assertEqual(r["cut"]["cut_arms"], [[6, "ox"]])
        self.assertIsNone(r["stopped"])
        tags = {(parse_custom_id(c)["set_id"], parse_custom_id(c)["setup"]) for c in sent_ids(t)}
        self.assertNotIn(("slimtest-ledger-l14n6-v1", "ox"), tags)
        for k in (("slimtest-ledger-l14n6-v1", "hx"), ("slimtest-ledger-l14n6-v1", "om"), ("slimtest-ledger-l14n16-v1", "hx"),
                  ("slimtest-ledger-l14n16-v1", "om")):
            self.assertIn(k, tags)
        # the two builders the 1b driver reuses: the manifest's list, and what each test set actually sent (limits, cut)
        from harness.pareto.manifest import item_set_hash
        p = test_plan()
        test, cal = slim.load_sets(p)
        man = json.loads((out / "manifest.json").read_text())
        mreqs = slim.manifest_requests(p, test, cal)
        self.assertEqual((man["item_set_sha256"], man["n_items"]), (item_set_hash(mreqs), len(mreqs)))
        sent = [x for s, m, i in test for x in slim.sent_test_requests(p, s, m, i, r["limits"], r["cut"])]
        self.assertEqual(sorted(x[0] for x in sent), sorted(c for c in sent_ids(t) if c.startswith("slimtest-")))
        by_id = {x["custom_id"]: x["params"]["max_tokens"] for reqs in t.batches.values() for x in reqs}
        self.assertTrue(all(by_id[cid] == params["max_tokens"] for cid, params, _ in sent))

    def test_projection_still_over_stops_until_the_user_rules(self):
        out = _tmpdir()
        p = test_plan()
        for s in p["sets"]:
            for a in s["arms"]:
                if "cost_basis" in a:
                    a["cost_basis"]["cost_usd_sum"] = "10"                                 # measured arms "cost" 10 USD a call
        g = guard(run_cap="100")
        r = run(p, FakeTransport(tokens_fake()), out, g)
        self.assertEqual(r["stopped"], "projected_over_cap")
        self.assertTrue(r["cut"]["still_over"])
        self.assertEqual(r["cut"]["cut_arms"], [[6, "hh"], [6, "ox"]])
        t = FakeTransport(tokens_fake())
        r = run(p, t, out, g, accept_projection_note="the user: go on (test)")
        self.assertIsNone(r["stopped"])
        self.assertEqual(sum(1 for x in records(out) if x.get("kind") == "cut"), 1)        # not recomputed
        self.assertTrue(any(x.get("kind") == "projection_accepted" for x in records(out)))
        with self.assertRaises(RuntimeError):                                              # already recorded: refused, not re-written
            run(p, FakeTransport(tokens_fake()), out, g, accept_projection_note="again")
        self.assertEqual(sum(1 for x in records(out) if x.get("kind") == "projection_accepted"), 1)

    def test_accept_projection_is_refused_before_the_stop_it_answers(self):
        """Edith S-R1: the note is accepted only when the log already holds a cut line with still_over: true."""
        p = test_plan()
        for s in p["sets"]:
            for a in s["arms"]:
                if "cost_basis" in a:
                    a["cost_basis"]["cost_usd_sum"] = "10"                                 # this projection WOULD be over the cap
        out = _tmpdir()
        g = guard(run_cap="100")
        t = FakeTransport(tokens_fake())
        with self.assertRaises(RuntimeError):                                              # on the very first command
            run(p, t, out, g, accept_projection_note="the user: go on (test)")
        self.assertEqual(t.batches, {})                                                    # nothing sent, no line written
        self.assertFalse([x for x in records(out) if x.get("kind") in ("cut", "projection_accepted")])
        r = run(p, FakeTransport(tokens_fake()), out, g)                                   # the stop happens first
        self.assertEqual(r["stopped"], "projected_over_cap")
        with self.assertRaises(RuntimeError):                                              # an empty note is no ruling
            run(p, FakeTransport(tokens_fake()), out, g, accept_projection_note="  ")
        r = run(p, FakeTransport(tokens_fake()), out, g, accept_projection_note="the user: go on (test)")
        self.assertIsNone(r["stopped"])
        # a run whose cut line is NOT still over: the note is refused at any time
        out2 = _tmpdir()
        r = run(test_plan(), FakeTransport(tokens_fake()), out2, g)
        self.assertFalse(r["cut"]["still_over"])
        with self.assertRaises(RuntimeError):
            run(test_plan(), FakeTransport(tokens_fake()), out2, g, accept_projection_note="the user: go on (test)")
        self.assertFalse([x for x in records(out2) if x.get("kind") == "projection_accepted"])

    def test_the_pause_trips_in_a_test_wave_and_changes_nothing(self):
        out = _tmpdir()
        g = guard(run_cap="100")
        fake = tokens_fake(stop={("test", OPUS, "medium", 9000): "max_tokens"})            # om at 16 truncates in the test wave
        t = FakeTransport(fake)
        r = run(test_plan(), t, out, g)
        self.assertEqual(r["stopped"], "paused_for_truncation")
        self.assertEqual(r["test"]["slimtest-ledger-l14n16-v1 confirmatory"].paused_for_truncation, {"om": 1.0})
        self.assertFalse([c for c in sent_ids(t) if c.startswith("slimtest-") and parse_custom_id(c)["setup"] in ("ho", "hh", "ox")])   # paused before any descriptive arm
        with self.assertRaises(PausedForTruncation):
            run(test_plan(), FakeTransport(fake), out, g)
        # wave 0 truncating does NOT pause (it is a measurement): checked in test_limits_are_applied (ox truncated there)
        r = run(test_plan(), FakeTransport(tokens_fake()), out, g, release_pause_note="the user: go on (test)")
        self.assertIsNone(r["stopped"])
        om16 = {x["max_tokens"] for x in records(out) if x.get("final") and x["custom_id"].startswith("slimtest-ledger-l14n16-v1")
                and parse_custom_id(x["custom_id"])["setup"] == "om"}
        self.assertEqual(om16, {9000})                                                      # no automatic change

    def test_resume_after_a_crash_sends_no_id_twice(self):
        for down_after in (1, 2, 3, 4):                                                   # wave 0, hx/om at 6, hx/om at 16, the rest at 6
            out = _tmpdir()
            g = guard(run_cap="100")
            t = FlakyTransport(tokens_fake(), down_after_submit=down_after)
            with self.assertRaises(TransportError):
                run(test_plan(), t, out, g)
            t.down = False
            t.down_after_submit = None
            r = run(test_plan(), t, out, g)
            self.assertIsNone(r["stopped"])
            ids = sent_ids(t)
            self.assertEqual(len(ids), len(set(ids)), down_after)
            self.assertEqual(len(ids), WAVE0_CALLS + TEST_CALLS)
            self.assertEqual(len(CallLog(out / "calls.jsonl").finished_ids()), WAVE0_CALLS + TEST_CALLS)

    def test_a_different_plan_cannot_resume_a_run(self):
        out = _tmpdir()
        g = guard(run_cap="100")
        run(test_plan(), DryTransport(), out, g)
        p = test_plan()
        p["sets"][0]["arms"][0]["n"] = 3
        with self.assertRaises(PlanError):
            run(p, DryTransport(), out, g)


class WaveOrder(unittest.TestCase):
    """Lock-4 audit A1: the confirmatory arms go first (hx and om at 16, then at 6), all final before any other arm is sent; only the
    send order changes (the requests, custom ids, limits, cut and manifest are the same)."""

    def test_the_study_plan_order(self):
        real = slim.read_plan(Path(slim.ROOT) / "data" / "plans" / "study1b-plan.json")
        self.assertEqual(slim.wave_order(real), [
            (16, "confirmatory", ["hx", "om"]), (6, "confirmatory", ["hx", "om"]),
            (16, "descriptive", ["ho", "hl", "hm", "hh", "hxh"]),
            (6, "descriptive", ["ho", "hl", "hm", "hh", "hxh", "sl", "sm", "sh", "sxh", "sx", "ol", "oh", "oxh", "ox"]),
            (12, "descriptive", ["hx", "om"])])

    def test_waves_are_the_same_requests(self):
        p = test_plan()
        test, cal = slim.load_sets(p)
        limits = {"arms": [{"steps": 6, "tag": "hh", "max_tokens": 9000}, {"steps": 6, "tag": "ox", "max_tokens": 4000},
                           {"steps": 16, "tag": "hx", "max_tokens": 101000}]}
        for cut in ({"cut_arms": []}, {"cut_arms": [[6, "ox"], [6, "hh"]]}, {"cut_arms": [[6, "ox"], [6, "hh"], [6, "ho"]]}):
            waves = slim.send_waves(p, test, limits, cut)
            per_set = [r for s, m, i in test for r in slim.sent_test_requests(p, s, m, i, limits, cut)]
            flat = [r for w in waves for r in w["requests"]]
            self.assertEqual(sorted(json.dumps(r, sort_keys=True) for r in flat), sorted(json.dumps(r, sort_keys=True) for r in per_set))
            self.assertEqual(len(flat), len(set(r[0] for r in flat)))
            self.assertEqual([(w["steps"], w["phase"]) for w in waves][:2], [(6, "confirmatory"), (16, "confirmatory")])
            for w in waves:                                                                     # item order kept inside a wave
                self.assertEqual([r[0] for r in w["requests"]], [r[0] for r in per_set if r in w["requests"]])
        self.assertEqual([(w["steps"], w["phase"]) for w in slim.send_waves(p, test, limits, {"cut_arms": [[6, "ox"], [6, "hh"], [6, "ho"]]})],
                         [(6, "confirmatory"), (16, "confirmatory")])                          # a wave the cut empties is dropped

    def test_batches_go_confirmatory_first(self):
        out = _tmpdir()
        t = FakeTransport(tokens_fake())
        r = run(test_plan(), t, out)
        self.assertIsNone(r["stopped"])
        self.assertEqual(list(r["test"]), ["slimtest-ledger-l14n6-v1 confirmatory", "slimtest-ledger-l14n16-v1 confirmatory",
                                           "slimtest-ledger-l14n6-v1 descriptive"])
        seq = []
        for reqs in t.batches.values():
            c = [parse_custom_id(x["custom_id"]) for x in reqs]
            sids = {x["set_id"] for x in c}
            key = ("wave0",) if all(x.startswith("slimcal-") for x in sids) else \
                (sids.pop(), {"confirmatory" if x["setup"] in ("hx", "om") else "descriptive" for x in c})
            self.assertTrue(len(key) == 1 or (len(key[1]) == 1 and not sids), key)                 # one set and one phase per batch
            seq.append(key if len(key) == 1 else (key[0], key[1].pop()))
        self.assertEqual(seq, [("wave0",), ("slimtest-ledger-l14n6-v1", "confirmatory"), ("slimtest-ledger-l14n16-v1", "confirmatory"),
                               ("slimtest-ledger-l14n6-v1", "descriptive")])
        man = json.loads((out / "manifest.json").read_text())                                    # the manifest is the runner's list
        p = test_plan()
        test, cal = slim.load_sets(p)
        from harness.pareto.manifest import item_set_hash
        self.assertEqual(man["item_set_sha256"], item_set_hash(slim.manifest_requests(p, test, cal)))

    def test_an_errored_confirmatory_call_holds_every_other_arm(self):
        """A confirmatory call that errors: the run stops ("confirmatory_incomplete") before any descriptive arm; the same command
        sends it again, then the rest; no id twice."""
        out = _tmpdir()
        g = guard(run_cap="100")
        bad = "slimtest-ledger-l14n16-v1-001-1x16-om-01"

        def batch_reply(cid, params):
            if cid == bad:
                return {"type": "errored", "error": {"type": "overloaded_error"}}
            return {"type": "succeeded", "message": reply(model=params["model"], tout=1000)}
        t = FakeTransport(batch_reply=batch_reply)
        r = run(test_plan(), t, out, g)
        self.assertEqual(r["stopped"], "confirmatory_incomplete")
        self.assertFalse([c for c in sent_ids(t) if c.startswith("slimtest-") and parse_custom_id(c)["setup"] in ("ho", "hh", "ox")])
        self.assertIn(bad, sent_ids(t))
        t2 = FakeTransport(lambda p: reply(model=p["model"], tout=1000))
        r2 = run(test_plan(), t2, out, g)
        self.assertIsNone(r2["stopped"])
        again = sent_ids(t2)
        self.assertEqual([c for c in again if c.startswith("slimtest-") and parse_custom_id(c)["setup"] in ("hx", "om")], [bad])  # only the errored one, again
        self.assertEqual(len(set(sent_ids(t)) | set(again)), WAVE0_CALLS + TEST_CALLS)
        self.assertEqual(len(CallLog(out / "calls.jsonl").finished_ids()), WAVE0_CALLS + TEST_CALLS)


class Cli(unittest.TestCase):
    def call(self, argv, plan=None):
        f = _tmpdir() / "plan.json"
        f.write_text(json.dumps(plan or test_plan()))
        out = io.StringIO()
        with mock.patch("harness.pareto.live.open_live_guard", side_effect=AssertionError("no live guard in tests")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = slim.main([argv[0], "--plan", str(f)] + argv[1:])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    def test_plan_prints_the_booking(self):
        code, out = self.call(["plan", "--cap", "100"])
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual((d["wave0"]["calls"], d["test_calls"]), (WAVE0_CALLS, TEST_CALLS))
        self.assertEqual((d["plan_sha256"], d["cap_usd"]), (slim.plan_sha256(test_plan()), "100"))     # A16: the hash to pin

    def test_cap_is_required_for_plan_and_dry(self):
        """A6: no 120 default; plan and dry refuse without --cap (and send nothing)."""
        self.assertEqual(self.call(["plan"])[0], 2)
        self.assertEqual(self.call(["dry", "--out", str(_tmpdir() / "d")])[0], 2)

    def test_dry_refuses_an_out_under_data_or_research(self):
        """A5: the never-sent check searches data/ and research/ as text; a dry run there would plant the test ids and prompts."""
        for bad in (Path(slim.ROOT) / "data" / "slim-dry-test-never-written", Path(slim.ROOT) / "research" / "x" / "y"):
            self.assertEqual(self.call(["dry", "--cap", "100", "--out", str(bad)])[0], 2)
            self.assertFalse(bad.exists())
        self.assertIsNone(slim.forbidden_out(_tmpdir() / "dry"))
        self.assertEqual(slim.forbidden_out(Path(slim.ROOT) / "data" / "x"), (Path(slim.ROOT) / "data").resolve())

    def test_live_expect_plan_sha256(self):
        """A16: live refuses a plan whose plan_sha256 is not the expected one, before any guard is opened; the right one goes on (to the
        live guard, stubbed here)."""
        argv = ["live", "--run-id", "t-1", "--cap", "5", "--clearance", "c.json", "--expect-plan-sha256"]
        self.assertEqual(self.call(argv + ["0" * 64])[0], 2)
        with self.assertRaisesRegex(AssertionError, "no live guard in tests"):
            self.call(argv + [slim.plan_sha256(test_plan())])
        self.assertEqual(self.call(["plan", "--cap", "100", "--expect-plan-sha256", "0" * 64])[0], 2)    # live only

    def test_live_refusals(self):
        for argv in (["live", "--run-id", "t-1"], ["live", "--run-id", "t-1", "--cap", "5"],
                     ["live", "--run-id", "t-1", "--cap", "5", "--clearance", "c.json", "--out", "d"],
                     ["live", "--run-id", "x-1", "--cap", "5", "--clearance", "c.json"]):        # wrong prefix
            self.assertEqual(self.call(argv)[0], 2, argv)
        p = test_plan()
        p["sets"][0]["arms"][1]["cost_basis"].update(cost_usd_sum=None, calls=None)
        self.assertEqual(self.call(["live", "--run-id", "t-1", "--cap", "5", "--clearance", "c.json"], p)[0], 2)
        p = test_plan()
        p["draft"] = "not final"
        self.assertEqual(self.call(["live", "--run-id", "t-1", "--cap", "5", "--clearance", "c.json"], p)[0], 2)


if __name__ == "__main__":
    unittest.main()
