"""E3 (harness/pareto/e3.py): step calls from the correct inputs, lead-by-2 voting with a cap of 9, rows for test 4.
Offline only: fake transport and a dry guard, never live."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.analysis import five_tests, kscript, scoring
from harness.pareto import e3
from harness.pareto.calllog import CallLog
from harness.pareto.limits import pilot_max_tokens
from harness.pareto.pilot import HAIKU, load_set
from harness.pareto.transport import FakeTransport
from harness.taskgen import ledger
from harness.taskgen.freeze import write_set
from harness.tests.fakes import guard, reply

N = 6
SID = "t-ledger-l14n6-e3"


class Decide(unittest.TestCase):
    def test_two_agreeing_draws_decide(self):
        d = e3.decide(["a", "a"])
        self.assertEqual((d["decided"], d["answer"], d["more"], d["at_cap"], d["draws"]), (True, "a", 0, False, 2))

    def test_a_one_one_split_asks_for_two_more(self):
        d = e3.decide(["a", "b"])
        self.assertEqual((d["decided"], d["done"], d["more"]), (False, False, 2))

    def test_two_one_asks_for_one_more_and_three_one_decides(self):
        self.assertEqual(e3.decide(["a", "b", "a"])["more"], 1)
        d = e3.decide(["a", "b", "a", "a"])
        self.assertEqual((d["decided"], d["answer"]), (True, "a"))

    def test_none_votes_use_a_draw_and_count_for_nothing(self):
        self.assertEqual(e3.decide([])["more"], 2)
        self.assertEqual(e3.decide([None, None])["more"], 2)
        self.assertEqual(e3.decide(["a", None])["more"], 1)
        d = e3.decide([None, "a", None, "a"])
        self.assertEqual((d["decided"], d["answer"], d["draws"]), (True, "a", 4))

    def test_more_never_passes_the_cap(self):
        d = e3.decide(["a", "b"] * 4)                     # 8 draws, 4-4: two would be needed, one is left
        self.assertEqual(d["more"], 1)

    def test_at_the_cap_a_unique_plurality_is_the_answer(self):
        d = e3.decide(["a", "b"] * 4 + ["a"])             # 5-4 after 9
        self.assertEqual((d["decided"], d["at_cap"], d["done"], d["answer"], d["more"]), (False, True, True, "a", 0))
        d = e3.decide(["a"] + [None] * 8)                 # 1-0 after 9: the lone answer
        self.assertEqual((d["at_cap"], d["answer"]), (True, "a"))

    def test_at_the_cap_a_tie_or_nothing_is_no_answer(self):
        d = e3.decide(["a", "b"] * 4 + [None])            # 4-4 after 9
        self.assertEqual((d["at_cap"], d["answer"], d["more"]), (True, None, 0))
        d = e3.decide([None] * 9)
        self.assertEqual((d["at_cap"], d["answer"]), (True, None))

    def test_constants(self):
        self.assertEqual((e3.LEAD, e3.CAP, e3.FIRST_ROUND_DRAWS), (2, 9, 2))
        self.assertEqual((e3.E3_MODEL, e3.E3_EFFORT), (HAIKU, "medium"))
        self.assertEqual(e3.E3_MAX_TOKENS, pilot_max_tokens("ledger", HAIKU))   # Amendment 1: the locked pilot limit


class Parse(unittest.TestCase):
    def test_parse_step_answer(self):
        self.assertEqual(e3.parse_step_answer("Answer: [0950, 3, 7]", 3), "950,3,7")
        self.assertEqual(e3.parse_step_answer("Working...\nAnswer: 1 = [1, 2, 3].", 3), "1,2,3")
        self.assertIsNone(e3.parse_step_answer("Answer: [1, 2]", 3))         # wrong length
        self.assertIsNone(e3.parse_step_answer("no answer line", 3))
        self.assertIsNone(e3.parse_step_answer(None, 3))

    def test_a_record_that_did_not_answer_votes_for_nothing(self):
        self.assertIsNone(e3.record_vote({"kind": "truncated", "answer_text": "Answer: [1, 2, 3]"}, 3))
        self.assertEqual(e3.record_vote({"kind": "answered", "answer_text": "Answer: [1, 2, 3]"}, 3), "1,2,3")


class WithSets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = Path(tempfile.mkdtemp())
        cls.dir = cls.td / SID
        write_set(cls.dir, "ledger", f"l14n{N}", SID, 2, "d31", "scratch")
        cls.sets = [load_set(cls.dir)]
        cls.steps = e3.chain_steps(cls.sets)
        cls.items = {it["id"]: it for it in cls.sets[0][1]}

    def chain_ids(self):
        return sorted(i for i, it in self.items.items() if int(it["width"]) == 1)


class Build(WithSets):
    def test_only_the_chains_and_every_step(self):
        chains = self.chain_ids()
        self.assertEqual(len(chains), 2)
        self.assertEqual([(s.item_id, s.k) for s in self.steps], [(c, k) for c in chains for k in range(1, N + 1)])

    def test_the_step_prompt_is_ledger_step_call_and_the_truth_its_state(self):
        for s in self.steps:
            p = ledger.generate(self.items[s.item_id]["seed"], 1, N, ledger.SETTINGS[f"l14n{N}"], item_id=s.item_id, style="d31")
            prompt, truth = ledger.step_call(p, 1, s.k)
            self.assertEqual(s.prompt, prompt)
            self.assertEqual(s.truth, scoring.state_key(truth))
            self.assertEqual(s.truth, scoring.state_key(self.items[s.item_id]["chains"][0]["states"][s.k - 1]))
            cid, params, meta = e3.step_item(s, 1)
            self.assertEqual(params["messages"], [{"role": "user", "content": prompt}])
            self.assertEqual((params["model"], params["output_config"], params["thinking"], params["max_tokens"]),
                             (HAIKU, {"effort": "medium"}, {"type": "adaptive"}, 48_000))

    def test_custom_ids_parse_and_meta(self):
        s = self.steps[0]
        for k, d in ((1, 1), (6, 9), (3, 4)):
            step = [x for x in self.steps if x.item_id == s.item_id and x.k == k][0]
            cid, _, meta = e3.step_item(step, d)
            self.assertEqual(cid, f"{s.item_id}-es-{k:02d}{d:02d}")
            self.assertLessEqual(len(cid), 64)
            got = kscript.parse_custom_id(cid)
            self.assertEqual((got["puzzle"], got["set_id"], got["base_index"], got["shape"], got["setup"], got["sample"], got["realtime"]),
                             (s.item_id, SID, step.base_index, f"1x{N}", "es", k * 100 + d, False))
            self.assertEqual(meta, {"set_id": SID, "item_id": s.item_id, "family": "ledger", "setting": f"l14n{N}",
                                    "base_index": step.base_index, "width": 1, "depth": N, "setup": "es", "model": HAIKU,
                                    "effort": "medium", "sample": k * 100 + d, "step": k, "draw": d})

    def test_the_first_round_is_two_draws_per_step(self):
        items = e3.plan_round(self.sets, [])
        self.assertEqual(len(items), 2 * N * 2)
        self.assertEqual(sorted({m["draw"] for _, _, m in items}), [1, 2])
        self.assertEqual(len({c for c, _, _ in items}), len(items))

    def test_a_set_that_is_not_ledger_is_refused(self):
        man, items = self.sets[0]
        with self.assertRaises(ValueError):
            e3.chain_steps([(dict(man, family="digits"), items)])

    def test_a_stored_prompt_that_does_not_rebuild_is_refused(self):
        man, items = self.sets[0]
        bad = [dict(it, prompt=it["prompt"] + " ") if int(it["width"]) == 1 else it for it in items]
        with self.assertRaises(ValueError):
            e3.chain_steps([(man, bad)])


def wrong(key):
    v = [int(x) for x in key.split(",")]
    return [v[0] + 1] + v[1:]


def other_wrong(key):
    v = [int(x) for x in key.split(",")]
    return [v[0] + 2] + v[1:]


class Run(WithSets):
    """Every reply is right except two scripted steps:
    - chain 0, step 3: draw 1 right, draw 2 wrong (1-1, two more), draws 3 and 4 right (3-1): decided right, 4 draws;
    - chain 1, step 2: two wrong answers alternate and draw 9 is truncated, so 4-4 at the cap: no answer, the step is wrong, 9 draws."""

    def script(self):
        chains = self.chain_ids()
        truth = {(s.item_id, s.k): s.truth for s in self.steps}

        def batch_reply(cid, params):
            p = kscript.parse_custom_id(cid)
            item_id, k, d = p["puzzle"], p["sample"] // 100, p["sample"] % 100
            key = truth[(item_id, k)]
            stop, text = "end_turn", f"Answer: {ledger.fmt([int(x) for x in key.split(',')])}"
            if (item_id, k) == (chains[0], 3) and d == 2:
                text = f"Answer: {ledger.fmt(wrong(key))}"
            if (item_id, k) == (chains[1], 2):
                if d == 9:
                    stop, text = "max_tokens", "Answer: ["
                else:
                    text = f"Answer: {ledger.fmt(wrong(key) if d % 2 else other_wrong(key))}"
            return {"type": "succeeded", "message": reply(model=HAIKU, text=text, stop=stop)}
        return chains, batch_reply

    def run_once(self, out, transport):
        return e3.run_e3(guard(run_cap="30"), transport, out, [self.dir], sleep=lambda s: None)

    def test_a_full_dry_run_then_a_resume(self):
        chains, batch_reply = self.script()
        out = Path(tempfile.mkdtemp())
        t = FakeTransport(batch_reply=batch_reply)
        r = self.run_once(out, t)
        self.assertIsNone(r["stopped"])
        self.assertEqual(r["rounds"], 5)                               # 2 draws, then +2, +2, +2, +1 for the step that reaches the cap
        self.assertEqual(r["calls_sent"], 2 * N * 2 + 2 + 7)
        self.assertEqual((r["steps"], r["decided"], r["at_cap"], r["open"], r["draws_logged"]), (2 * N, 2 * N - 1, 1, 0, 33))
        sent = [x["custom_id"] for b in t.batches.values() for x in b]
        self.assertEqual(len(sent), 33)
        self.assertEqual(len(set(sent)), 33)
        self.assertIn(f"{chains[1]}-es-0209", sent)
        self.assertNotIn(f"{chains[0]}-es-0305", sent)

        log = CallLog(out / "calls.jsonl")
        rows = e3.e3_rows(self.sets, log.records())
        self.assertEqual(len(rows), 2)
        by = {r["item_id"]: r for r in rows}
        r0, r1 = by[chains[0]], by[chains[1]]
        self.assertEqual(r0["step_correct"], [True] * N)
        self.assertEqual((r0["calls"], r0["at_cap_steps"], r0["kind"], r0["correct"]), (N * 2 + 2, 0, "answered", True))
        self.assertEqual(r1["step_correct"], [True, False] + [True] * (N - 2))
        self.assertEqual((r1["calls"], r1["at_cap_steps"], r1["kind"], r1["correct"]), (N * 2 + 7, 1, "answered", False))
        for r in rows:
            self.assertEqual((r["setup"], r["shape"]), ("e3", f"1x{N}"))
            self.assertEqual(r["base_id"], f"{SID}-{self.items[r['item_id']]['base_index']:03d}")
            self.assertGreater(float(r["cost_usd"]), 0)
        logged = sum(float(x["cost_usd"]) for x in log.records() if x.get("final"))
        self.assertAlmostEqual(sum(float(r["cost_usd"]) for r in rows), logged, places=9)
        # the rows plug into test 4's estimator: product of the per-step accuracies
        scores = five_tests.e3_arm_scores(rows, shape=f"1x{N}")
        self.assertEqual(scores, {r0["base_id"]: 100.0, r1["base_id"]: 0.0})

        # resume: nothing left to plan, so a second run sends nothing
        t2 = FakeTransport(batch_reply=batch_reply)
        r2 = self.run_once(out, t2)
        self.assertEqual((r2["rounds"], r2["calls_sent"], len(t2.batches)), (0, 0, 0))
        self.assertEqual(e3.plan_round(self.sets, log.records()), [])

    def test_an_errored_draw_is_planned_again_under_its_own_id(self):
        chains, batch_reply = self.script()
        target = f"{chains[0]}-es-0102"

        def flaky(cid, params):
            if cid == target and not flaky.failed:
                flaky.failed = True
                return {"type": "errored", "error": {"type": "api_error", "message": "overloaded"}}
            return batch_reply(cid, params)
        flaky.failed = False
        out = Path(tempfile.mkdtemp())
        t = FakeTransport(batch_reply=flaky)
        r = self.run_once(out, t)
        self.assertIsNone(r["stopped"])
        sent = [x["custom_id"] for b in t.batches.values() for x in b]
        self.assertEqual(sent.count(target), 2)                        # once errored (not billed, not a draw), once answered
        self.assertEqual(r["draws_logged"], 33)

    def test_a_truncated_step_makes_the_row_truncated(self):
        chains, _ = self.script()
        truth = {(s.item_id, s.k): s.truth for s in self.steps}

        def all_cut_on_one_step(cid, params):
            p = kscript.parse_custom_id(cid)
            item_id, k = p["puzzle"], p["sample"] // 100
            if (item_id, k) == (chains[0], 4):
                return {"type": "succeeded", "message": reply(model=HAIKU, text="Answer: [", stop="max_tokens")}
            key = truth[(item_id, k)]
            return {"type": "succeeded", "message": reply(model=HAIKU, text=f"Answer: {ledger.fmt([int(x) for x in key.split(',')])}")}
        out = Path(tempfile.mkdtemp())
        r = self.run_once(out, FakeTransport(batch_reply=all_cut_on_one_step))
        self.assertEqual(r["at_cap"], 1)
        rows = {x["item_id"]: x for x in e3.e3_rows(self.sets, CallLog(out / "calls.jsonl").records())}
        r0 = rows[chains[0]]
        self.assertEqual((r0["kind"], r0["stop_reason"], r0["step_correct"][3], r0["at_cap_steps"]), ("truncated", "max_tokens", False, 1))
        self.assertTrue(scoring._dropped(r0, "truncations_out"))
        self.assertEqual(rows[chains[1]]["kind"], "answered")

    def test_an_incomplete_chain_has_no_row_and_plan_continues_the_numbering(self):
        chains, batch_reply = self.script()
        out = Path(tempfile.mkdtemp())
        r = e3.run_e3(guard(run_cap="30"), FakeTransport(batch_reply=batch_reply), out, [self.dir], sleep=lambda s: None, max_rounds=1)
        self.assertEqual((r["rounds"], r["stopped"], r["open"]), (1, "max_rounds", 2))
        recs = list(CallLog(out / "calls.jsonl").records())
        rows = e3.e3_rows(self.sets, recs)
        self.assertEqual([x["item_id"] for x in rows], [])              # chain 0 (step 3) and chain 1 (step 2) are still open
        nxt = e3.plan_round(self.sets, recs)
        self.assertEqual(sorted(c for c, _, _ in nxt), sorted([f"{chains[0]}-es-0303", f"{chains[0]}-es-0304",
                                                                f"{chains[1]}-es-0203", f"{chains[1]}-es-0204"]))

    def test_an_e3_record_of_another_model_is_refused(self):
        rec = {"final": True, "custom_id": "x", "requested_model": "claude-opus-5-5", "effort": "medium",
               "meta": {"setup": "es", "item_id": "x", "step": 1, "draw": 1}}
        with self.assertRaises(ValueError):
            e3.plan_round(self.sets, [rec], self.steps)


if __name__ == "__main__":
    unittest.main()
