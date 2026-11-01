"""Edith, PR #19 r4 (c): the pilot table's `right` for a ledger set is the official D-76 score, computed by the analysis's own scorers; other
families keep whole-answer scoring. Checked on Karen's parse cases (1x24) and pieces cases (24x1)."""

import gzip
import json
import unittest
from pathlib import Path

from harness.analysis import scoring
from harness.pareto.pilot import grader
from harness.taskgen.prompt_d31 import score_answer

FIX = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v2"


def load(name):
    with gzip.open(FIX / name, "rt") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


class LedgerRightIsTheOfficialScore(unittest.TestCase):
    def test_1x24_on_karens_parse_cases(self):
        cases = load("parse_cases.jsonl.gz")
        keys = {}
        for c in cases:
            if c["expected"]["ok"]:
                keys.setdefault(c["line_count"], c["expected"]["states"])
        n_right = 0
        for i, c in enumerate(cases):
            key = c["expected"]["states"] if c["expected"]["ok"] else keys[c["line_count"]]
            item = {"id": f"x{i}", "depth": 24, "width": 1, "params": {"lines": c["line_count"]}, "chains": [{"states": key}],
                    "answer": [key[-1]], "style": "d31"}
            got = grader({item["id"]: item}, "ledger")({"meta": {"item_id": item["id"]}, "answer_text": c["reply"]})
            want = scoring.grade_1x24(c["reply"], key, c["line_count"])["correct"]
            self.assertEqual(got, bool(want), c["id"])
            n_right += got
        self.assertGreater(n_right, 0)

    def test_an_answer_only_item_is_scored_by_its_final_answer(self):
        key = [[1, 2, 3]] * 23 + [[124, 224, 324]]
        item = {"id": "a", "depth": 24, "width": 1, "params": {"lines": 3}, "chains": [{"states": key}], "answer": [key[-1]],
                "style": "d31-answer-only"}
        self.assertTrue(grader({"a": item}, "ledger")({"meta": {"item_id": "a"}, "answer_text": "Answer: 1 = [124, 224, 324]"}))

    def test_24x1_on_karens_pieces_cases(self):
        for i, c in enumerate(load("pieces_cases.jsonl.gz")):
            e = c["expected"]
            answer = ([e["entries"][str(k)] for k in range(1, c["width"] + 1)] if e["ok"]
                      else [[k] * c["line_count"] for k in range(1, c["width"] + 1)])
            item = {"id": f"p{i}", "depth": 1, "width": c["width"], "params": {"lines": c["line_count"]}, "answer": answer}
            got = grader({item["id"]: item}, "ledger")({"meta": {"item_id": item["id"]}, "answer_text": c["reply"]})
            self.assertEqual(got, bool(scoring.grade_24x1(c["reply"], answer, c["line_count"])["correct"]), c["id"])

    def test_other_families_keep_whole_answer_scoring(self):
        item = {"id": "d", "answer": ["0123", "4567"]}
        reply = "Answer: 1 = 0123, 2 = 4567"
        got = grader({"d": item}, "digits")({"meta": {"item_id": "d"}, "answer_text": reply})
        self.assertEqual(got, score_answer(reply, ["0123", "4567"])["all_correct"])
        self.assertTrue(got)


if __name__ == "__main__":
    unittest.main()
