import csv
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from harness.pareto.batch import run_batches
from harness.pareto.pilot import Setup, SETUPS, build_requests, grader, load_set, plan, run_pilot
from harness.pareto.transport import DryTransport, FakeTransport
from harness.taskgen import freeze
from harness.tests.fakes import guard, reply, tmplog


def _rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def make_set(family="digits", setting="d4s", set_id="pilot-digits-d4s-v1-test", n_base=2):
    d = Path(tempfile.mkdtemp()) / "set"
    freeze.write_set(d, family, setting, set_id, n_base, "d31", "scratch")
    return d


class PilotBuild(unittest.TestCase):
    def test_counts_and_ids(self):
        d = make_set()
        man, items = load_set(d)
        reqs = build_requests(man, items)
        # 2 base x 2 shapes = 4 puzzles; haiku x10 + sonnet + opus = 12 calls each
        self.assertEqual(len(reqs), 4 * 12)
        ids = [r[0] for r in reqs]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertTrue(all(len(i) <= 64 for i in ids))
        m = {}
        for cid, p, meta in reqs:
            m[(meta["setup"], p["model"], p["output_config"]["effort"])] = m.get((meta["setup"], p["model"], p["output_config"]["effort"]), 0) + 1
        self.assertEqual(m, {("hm", "claude-haiku-5-5", "medium"): 40, ("sm", "claude-sonnet-5-5", "medium"): 4,
                             ("om", "claude-opus-5-5", "medium"): 4})

    def test_max_tokens_from_the_limits_table_and_requests_are_clean(self):
        man, items = load_set(make_set())
        want = {"claude-haiku-5-5": 48_000, "claude-sonnet-5-5": 32_000, "claude-opus-5-5": 32_000}
        for cid, p, meta in build_requests(man, items):
            self.assertEqual(p["max_tokens"], want[p["model"]])
            self.assertEqual(set(p), {"model", "max_tokens", "messages", "output_config", "thinking"})
            self.assertEqual(p["thinking"], {"type": "adaptive"})

    def test_code_family_has_no_sonnet(self):
        man, items = load_set(make_set("code", "c3b", "pilot-code-c3b-v1-test", 1))
        reqs = build_requests(man, items)
        self.assertEqual({r[1]["model"] for r in reqs}, {"claude-haiku-5-5", "claude-opus-5-5"})
        self.assertEqual(len(reqs), 2 * 11)
        self.assertEqual({r[1]["max_tokens"] for r in reqs}, {96_000, 64_000})

    def test_a_tampered_set_is_refused(self):
        d = make_set()
        t = (d / "items.jsonl").read_text()
        (d / "items.jsonl").write_text(t.replace("Start at", "Start  at", 1))
        with self.assertRaises(AssertionError):
            load_set(d)


class PilotRun(unittest.TestCase):
    def test_plan_makes_no_calls_and_counts(self):
        man, items = load_set(make_set())
        reqs = build_requests(man, items)
        p = plan(guard(run_cap="30"), reqs)
        self.assertEqual(p["calls"], 48)
        self.assertEqual(p["per_setup"], {"digits/hm": 40, "digits/sm": 4, "digits/om": 4})
        self.assertGreater(Decimal(p["batch_worst_case_usd"]), 0)

    def test_dry_flow_end_to_end_and_table(self):
        d = make_set()
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="30")
        r = run_pilot(g, DryTransport(), out, [d], sleep=lambda s: None)
        self.assertEqual(r["summary"].answered + r["summary"].failed, 48)
        rows = _rows(out / "compact_table.csv")
        self.assertEqual(len(rows), 48)
        self.assertTrue((out / "manifest.json").exists())
        self.assertEqual(g.reserved, 0)

    def test_grading_uses_the_frozen_answer(self):
        d = make_set()
        man, items = load_set(d)
        by_id = {it["id"]: it for it in items}
        it = items[0]
        g = grader(by_id, "digits")
        good = {"meta": {"item_id": it["id"]}, "answer_text": it["answer_line"]}
        bad = {"meta": {"item_id": it["id"]}, "answer_text": "Answer: 1 = 0000"}
        self.assertTrue(g(good))
        self.assertFalse(g(bad))
        # code answers are lists
        dc = make_set("code", "c3b", "pilot-code-c3b-v1-test", 1)
        manc, itc = load_set(dc)
        gc = grader({i["id"]: i for i in itc}, "code")
        line = "Answer: " + ", ".join(f"{i} = {a}" for i, a in enumerate(itc[0]["answer"], 1))
        self.assertTrue(gc({"meta": {"item_id": itc[0]["id"]}, "answer_text": line}))
        self.assertFalse(gc({"meta": {"item_id": itc[0]["id"]}, "answer_text": "Answer: 1 = [1, 2]"}))

    def test_fake_transport_answers_are_graded_and_refusals_counted(self):
        d = make_set(n_base=1)
        man, items = load_set(d)
        by_prompt = {it["prompt"]: it for it in items}
        n = {"i": 0}

        def fake(p):
            n["i"] += 1
            it = by_prompt[p["messages"][0]["content"]]
            if n["i"] == 1:
                return reply(model=p["model"], stop="refusal", category="bio", text=None)
            return reply(model=p["model"], text=it["answer_line"])
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="30")
        r = run_pilot(g, FakeTransport(fake), out, [d], sleep=lambda s: None)
        rows = _rows(out / "compact_table.csv")
        self.assertEqual(sum(1 for x in rows if x["right"] == "1"), 23)
        self.assertEqual(sum(1 for x in rows if x["kind"] == "refusal"), 1)
        self.assertEqual(sum(1 for x in rows if x["right"] == ""), 1)


if __name__ == "__main__":
    unittest.main()
