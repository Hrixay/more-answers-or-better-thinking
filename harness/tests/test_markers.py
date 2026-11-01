import json
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

from harness.pareto import markers
from harness.pareto.prices import OPUS, Usage
from harness.tests.fakes import LiveEnv


def commit_line(key, amount, out_tokens, batch=False, free=False):
    return {"event": "commit", "key": key, "amount": amount, "batch": batch, "free_by_rule": free, "usage": {"output_tokens": out_tokens}}


def call_line(cid, kind, category, mode="realtime", attempt=1, out=0):
    return {"custom_id": cid, "kind": kind, "refusal_category": category, "mode": mode, "attempt": attempt, "stop_reason": "refusal",
            "usage_raw": {"output_tokens": out}, "request_id": "req_1"}


def write(path, lines):
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))


class Candidates(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.ledger, self.calls = self.d / "ledger.jsonl", self.d / "calls.jsonl"

    def test_keys_follow_the_guard_naming(self):
        self.assertEqual(markers.guard_key(call_line("c", "refusal", "cyber")), "c#a1")
        self.assertEqual(markers.guard_key(call_line("c", "refusal", "cyber", mode="batch")), "c@1")

    def test_only_free_zero_output_refusals_that_are_not_marked_are_listed(self):
        write(self.ledger, [commit_line("a#a1", "0.017", 0), commit_line("b@1", "0.009", 0, batch=True),
                            commit_line("c#a1", "0.03", 571), commit_line("d#a1", "0.002", 2700),
                            commit_line("e#a1", "0.01", 0), commit_line("f#a1", "0.01", 0, free=True),
                            commit_line("g#a1", "0.01", 0)])
        write(self.calls, [call_line("a", "refusal", "cyber"), call_line("b", "refusal", "cyber", mode="batch"),
                           call_line("c", "refusal", "cyber", out=571),          # billed: it had output
                           call_line("d", "answered", None),
                           call_line("e", "refusal", "bio"),                      # bio is billed
                           call_line("f", "refusal", "cyber"),                    # already flagged free
                           call_line("h", "refusal", "cyber")])                   # no commit in the ledger
        got = markers.candidates(self.ledger, self.calls)
        self.assertEqual([c["key"] for c in got], ["a#a1", "b@1"])
        self.assertEqual(sum(c["amount"] for c in got), D("0.026"))
        self.assertTrue(all(c["note"].strip() for c in got))

    def test_an_already_marked_call_is_not_listed_again(self):
        write(self.ledger, [commit_line("a#a1", "0.017", 0), {"event": "free_by_rule_marked", "key": "a#a1"}])
        write(self.calls, [call_line("a", "refusal", "cyber")])
        self.assertEqual(markers.candidates(self.ledger, self.calls), [])


class Apply(unittest.TestCase):
    def test_marks_through_a_live_guard_and_leaves_spend_alone(self):
        env = LiveEnv("marker-test", cap="5")
        g = env.guard()
        g.reserve_many([("a#a1", OPUS, 1000, 1000, False), ("b#a1", OPUS, 1000, 1000, False)])
        g.commit("a#a1", Usage(input_tokens=1000, output_tokens=0))
        g.commit("b#a1", Usage(input_tokens=1000, output_tokens=500))
        spent, adjusted = g.spent, g.rule_adjusted_spent
        cands = [{"key": "a#a1", "category": "cyber", "amount": D("0"), "note": "call log: cyber refusal, 0 output tokens"}]
        total = markers.apply_markers(g, cands)
        self.assertGreater(total, 0)
        self.assertEqual(g.spent, spent)
        self.assertEqual(g.rule_adjusted_spent, adjusted - total)
        with self.assertRaises(ValueError):                       # the guard itself refuses a commit that had output
            markers.apply_markers(g, [{"key": "b#a1", "category": "cyber", "amount": D("0"), "note": "x"}])
        with self.assertRaises(ValueError):                       # and a category B5 bills
            markers.apply_markers(g, [{"key": "b#a1", "category": "bio", "amount": D("0"), "note": "x"}])
        g.close()


if __name__ == "__main__":
    unittest.main()
