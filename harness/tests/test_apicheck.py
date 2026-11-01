import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from harness.pareto import apicheck
from harness.pareto.transport import DryTransport, FakeTransport, TransportError
from harness.taskgen import freeze
from harness.tests.fakes import guard, reply


def setUpModule():
    """load_set verifies a ledger set in depth (rebuild from the seed, independent checker: minutes). These tests are about the check
    command, not the generator, so the deep part is switched off here; test_ledger.py covers it."""
    global _PATCH
    _PATCH = mock.patch.object(freeze, "_verify_ledger_item", lambda item, *a, **k: None)
    _PATCH.start()


def tearDownModule():
    _PATCH.stop()


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "check-ledger-test-v1"     # 5 base puzzles x 2 shapes of l14, frozen once (read only)


def make_set(*_ignored):
    """The frozen fixture: freezing a ledger set takes minutes, and these tests only read it."""
    return FIXTURE


class Build(unittest.TestCase):
    def test_twenty_calls_in_the_fixed_order(self):
        d = make_set()
        man, items = apicheck.load_set(d)
        reqs = apicheck.build_check(man, items)
        self.assertEqual(len(reqs), 20)
        ids = [r[0] for r in reqs]
        self.assertEqual(len(set(ids)), 20)
        self.assertTrue(all(len(i) <= 64 for i in ids))
        order = [(m["model"].split("-")[1], f"{m['width']}x{m['depth']}", m["base_index"]) for _, _, m in reqs]
        self.assertEqual(order[:4], [("opus", "24x1", 0), ("opus", "1x24", 0), ("sonnet", "24x1", 0), ("sonnet", "1x24", 0)])
        self.assertEqual([o[2] for o in order], [b for b in range(5) for _ in range(4)])
        self.assertTrue(all(p["output_config"]["effort"] == "medium" for _, p, _ in reqs))

    def test_needs_exactly_five_base_puzzles_and_the_ledger_family(self):
        man, items = apicheck.load_set(make_set())
        with self.assertRaises(ValueError):
            apicheck.build_check(man, [it for it in items if it["base_index"] < 3])
        with self.assertRaises(ValueError):
            apicheck.build_check(dict(man, family="digits"), items)

    def test_plan_has_a_worst_case(self):
        man, items = apicheck.load_set(make_set())
        p = apicheck.plan(apicheck.build_check(man, items))
        self.assertEqual(p["calls"], 20)
        self.assertGreater(float(p["worst_case_list_usd"]), 0)


class Run(unittest.TestCase):
    def _fake(self, d, refuse_at=None, error_at=None, wrong_at=()):
        man, items = apicheck.load_set(d)
        by_prompt = {it["prompt"]: it for it in items}
        n = {"i": 0}

        def line(it):
            return "Answer: " + ", ".join(f"{i} = {a}" for i, a in enumerate(it["answer"], 1))

        def fake(p):
            n["i"] += 1
            it = by_prompt[p["messages"][0]["content"]]
            if error_at is not None and n["i"] >= error_at:
                raise TransportError("server", "overloaded", billed="no", retryable=True, status=529)
            if refuse_at == n["i"]:
                return reply(model=p["model"], stop="refusal", category="cyber", text=None, tout=0)
            text = "Answer: 1 = [0]" if n["i"] in wrong_at else line(it)
            return reply(model=p["model"], text=text)
        return FakeTransport(fake), n

    def test_all_answered(self):
        d = make_set()
        t, n = self._fake(d)
        out = Path(tempfile.mkdtemp())
        r = apicheck.run_check(guard(run_cap="30"), t, out, d)
        self.assertEqual((r["status"], r["calls_made"], r["answered"], r["refusals"]), ("complete", 20, 20, 0))
        self.assertTrue((out / "check_result.json").exists())

    def test_stops_at_the_first_refusal_and_sends_nothing_more(self):
        d = make_set()
        t, n = self._fake(d, refuse_at=3)
        r = apicheck.run_check(guard(run_cap="30"), t, Path(tempfile.mkdtemp()), d)
        self.assertEqual(r["status"], "stopped_at_refusal")
        self.assertEqual((r["calls_made"], r["refusals"], len(t.sent)), (3, 1, 3))
        self.assertIn("cyber", r["reason"])

    def test_wrong_answers_do_not_stop_it(self):
        d = make_set()
        t, n = self._fake(d, wrong_at=(2, 5, 6))
        r = apicheck.run_check(guard(run_cap="30"), t, Path(tempfile.mkdtemp()), d)
        self.assertEqual((r["status"], r["calls_made"]), ("complete", 20))

    def test_api_error_after_retries_is_incomplete_not_a_refusal(self):
        d = make_set()
        t, n = self._fake(d, error_at=4)
        r = apicheck.run_check(guard(run_cap="30"), t, Path(tempfile.mkdtemp()), d)
        self.assertEqual(r["status"], "incomplete")
        self.assertEqual(r["refusals"], 0)
        self.assertEqual(r["calls_made"], 3)

    def test_cap_stop_is_incomplete(self):
        d = make_set()
        t, n = self._fake(d)
        r = apicheck.run_check(guard(run_cap="0.01"), t, Path(tempfile.mkdtemp()), d)
        self.assertEqual(r["status"], "incomplete")
        self.assertIn("guard stop", r["reason"])

    def test_resume_skips_finished_calls(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        t, n = self._fake(d, refuse_at=None, error_at=6)
        apicheck.run_check(guard(run_cap="30"), t, out, d)
        t2, n2 = self._fake(d)
        r = apicheck.run_check(guard(run_cap="30"), t2, out, d, resume_incomplete=True)
        self.assertEqual(len(t2.sent), 20 - 5)
        self.assertEqual(r["status"], "complete")

    def test_a_rerun_after_a_refusal_sends_nothing_ever(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        t, n = self._fake(d, refuse_at=3)
        apicheck.run_check(guard(run_cap="30"), t, out, d)
        for flag in (False, True):
            t2, n2 = self._fake(d)
            with self.assertRaises(apicheck.CheckNotRerun):
                apicheck.run_check(guard(run_cap="30"), t2, out, d, resume_incomplete=flag)
            self.assertEqual(t2.sent, [])
        self.assertEqual(json.loads((out / "check_result.json").read_text())["status"], "stopped_at_refusal")

    def test_a_refusal_in_the_log_alone_also_blocks(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        t, n = self._fake(d, refuse_at=2)
        apicheck.run_check(guard(run_cap="30"), t, out, d)
        (out / "check_result.json").unlink()                       # only calls.jsonl is left
        t2, n2 = self._fake(d)
        with self.assertRaises(apicheck.CheckNotRerun):
            apicheck.run_check(guard(run_cap="30"), t2, out, d, resume_incomplete=True)
        self.assertEqual(t2.sent, [])

    def test_a_refusal_in_the_log_blocks_even_if_the_result_file_says_incomplete(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        t, n = self._fake(d, refuse_at=2)
        apicheck.run_check(guard(run_cap="30"), t, out, d)
        res = json.loads((out / "check_result.json").read_text())
        res.update(status="incomplete", refusals=0)                      # a stale or edited result file must not reopen the check
        (out / "check_result.json").write_text(json.dumps(res))
        t2, n2 = self._fake(d)
        with self.assertRaises(apicheck.CheckNotRerun):
            apicheck.run_check(guard(run_cap="30"), t2, out, d, resume_incomplete=True)
        self.assertEqual(t2.sent, [])

    def test_a_rerun_needs_the_flag_and_an_incomplete_result(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        t, n = self._fake(d, error_at=6)
        apicheck.run_check(guard(run_cap="30"), t, out, d)          # incomplete
        t2, n2 = self._fake(d)
        with self.assertRaises(apicheck.CheckNotRerun):             # no flag
            apicheck.run_check(guard(run_cap="30"), t2, out, d)
        self.assertEqual(t2.sent, [])
        apicheck.run_check(guard(run_cap="30"), t2, out, d, resume_incomplete=True)   # flag: resumes
        t3, n3 = self._fake(d)
        with self.assertRaises(apicheck.CheckNotRerun):             # complete now: never re-run
            apicheck.run_check(guard(run_cap="30"), t3, out, d, resume_incomplete=True)
        self.assertEqual(t3.sent, [])

    def test_a_model_mismatch_is_incomplete_and_the_result_is_written(self):
        d = make_set()
        man, items = apicheck.load_set(d)
        out = Path(tempfile.mkdtemp())
        t = FakeTransport(lambda p: reply(model="claude-opus-4-8" if "opus" in p["model"] else p["model"], text="Answer: 1 = [0]"))
        r = apicheck.run_check(guard(run_cap="30"), t, out, d)
        self.assertEqual(r["status"], "incomplete")
        self.assertIn("model mismatch", r["reason"])
        self.assertTrue((out / "check_result.json").exists())
        self.assertEqual(len(t.sent), 1)

    def test_plan_asks_for_the_d64_cap(self):
        man, items = apicheck.load_set(make_set())
        self.assertEqual(apicheck.plan(apicheck.build_check(man, items))["cap_to_ask_for_usd"], "11")

    def test_dry_run_end_to_end(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        r = apicheck.run_check(guard(run_cap="30"), DryTransport(), out, d)
        self.assertEqual(r["calls_made"], 20)
        self.assertEqual(json.loads((out / "check_result.json").read_text())["calls_planned"], 20)

    def test_live_mode_needs_cap_and_clearance(self):
        d = make_set()
        with self.assertRaises(SystemExit):
            apicheck.main(["live", "--set", str(d)])


if __name__ == "__main__":
    unittest.main()
