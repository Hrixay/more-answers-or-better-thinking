"""D-90 (Deviation 2): a step line repeated with the IDENTICAL state is read once; a repeat with a different state still fails; the
original rule of prereg-lock-2 stays callable (`repeats="strict"`) and is the named sensitivity view "original" in scoring."""

import unittest

from harness.analysis import five_tests, scoring
from harness.analysis import trace_parse as tp

N, L = 6, 3
STATES = [(10 + k, 20 + k, 30 + k) for k in range(1, N + 1)]


def line(k, state=None, fmt="1.{k} = [{v}]"):
    state = STATES[k - 1] if state is None else state
    return fmt.format(k=k, v=", ".join(str(x) for x in state))


def chain(extra=(), answer=None):
    body = [line(k) for k in range(1, N + 1)] + list(extra)
    return "\n".join(body + [answer or f"Answer: 1 = [{', '.join(map(str, STATES[-1]))}]"])


class Parser(unittest.TestCase):
    def parse(self, text, repeats=tp.REPEATS):
        return tp.parse_trace(text, L, N, repeats=repeats)

    def test_the_default_is_the_d90_rule(self):
        self.assertEqual(tp.REPEATS, tp.REPEATS_IDENTICAL)
        with self.assertRaises(ValueError):
            self.parse(chain(), repeats="lenient")

    def test_an_identical_repeat_is_ok_and_the_strict_rule_reproduces_extra_line(self):
        text = chain([line(3)])
        r = self.parse(text)
        self.assertEqual((r.status, r.states, r.step_states), ("ok", tuple(STATES), tuple(STATES)))
        s = self.parse(text, repeats=tp.REPEATS_STRICT)
        self.assertEqual((s.status, s.states, s.step_states, s.detail), ("extra_line", None, None, "step line 1.3 is written more than once"))

    def test_three_identical_copies_are_ok(self):
        self.assertEqual(self.parse(chain([line(4), line(4)])).status, "ok")

    def test_identical_after_reading_spacing_and_markup_do_not_matter(self):
        self.assertEqual(self.parse(chain(["**1.2** = [12,22,32]", "- 1.2: [12, 22, 32]."])).status, "ok")

    def test_a_conflicting_repeat_fails_under_both_rules(self):
        for extra in ([line(3, (9, 9, 9))], [line(3), line(3, (9, 9, 9))]):
            r = self.parse(chain(extra))
            self.assertEqual((r.status, r.step_states), ("extra_line", None))
            self.assertEqual(r.detail, "step line 1.3 is written more than once with different states")
            self.assertEqual(self.parse(chain(extra), repeats=tp.REPEATS_STRICT).status, "extra_line")

    def test_a_summary_block_repeating_every_line(self):
        block = ["", "Summary:"] + [line(k) for k in range(1, N + 1)]
        self.assertEqual(self.parse(chain(block)).status, "ok")
        self.assertEqual(self.parse(chain(block), repeats=tp.REPEATS_STRICT).status, "extra_line")
        bad = list(block)
        bad[-1] = line(N, (1, 2, 3))                                   # the summary contradicts the last line
        self.assertEqual(self.parse(chain(bad)).status, "extra_line")

    def test_an_unreadable_line_repeated_word_for_word_is_judged_once_by_the_value_rules(self):
        self.assertEqual(self.parse(chain(["1.2 = [12, x, 32]"]).replace(line(2), "1.2 = [12, x, 32]", 1)).status, "non_integer")
        self.assertEqual(self.parse(chain(["1.2 = [12, x, 32]"])).status, "extra_line")   # one copy readable, one not: different

    def test_other_reject_reasons_are_unchanged(self):
        self.assertEqual(self.parse(chain([line(3)], answer="Answer: 1 = [1, 2, 3]")).status, "answer_mismatch")
        self.assertEqual(self.parse("\n".join(line(k) for k in range(1, N)) + "\n" + line(2) + "\nAnswer: 1 = [16, 26, 36]").status,
                         "missing_line")


class Scoring(unittest.TestCase):
    def grade(self, text, **kw):
        return scoring.grade_1x24(text, STATES, L, **kw)

    def test_grade_carries_both_readings(self):
        g = self.grade(chain([line(3)]))
        self.assertEqual((g["format_status"], g["correct"], g["format_status_original"], g["correct_original"], g["repeats_rule"]),
                         ("ok", True, "extra_line", False, "identical"))
        plain = self.grade(chain())
        self.assertEqual((plain["correct"], plain["correct_original"], plain["format_status_original"]), (True, True, "ok"))
        wrong = self.grade(chain([line(3, (9, 9, 9))]))
        self.assertEqual((wrong["correct"], wrong["correct_original"]), (False, False))
        s = self.grade(chain([line(3)]), repeats=tp.REPEATS_STRICT)
        self.assertEqual((s["format_status"], s["correct"], s["correct_original"]), ("extra_line", False, False))

    def test_the_original_view_in_row_correct_and_vote_key(self):
        row = dict(self.grade(chain([line(3)])), kind="answered", shape="1x6", setup="haiku-med", base_id="b0")
        self.assertTrue(scoring.row_correct(row, "official"))
        self.assertFalse(scoring.row_correct(row, "original"))
        self.assertIsNotNone(scoring.vote_key(row, "official"))
        self.assertIsNone(scoring.vote_key(row, "original"))
        old = {k: v for k, v in row.items() if k not in ("correct_original", "format_status_original", "repeats_rule")}
        self.assertTrue(scoring.row_correct(old, "original"))         # a row graded before D-90 reads its own `correct`
        self.assertIn("original", five_tests.SCORES)

    def test_rates_report_the_original_accuracy(self):
        rows = [dict(self.grade(t), kind="answered", shape="1x6", setup="sonnet-med", base_id=f"b{i}")
                for i, t in enumerate((chain([line(3)]), chain(), chain([line(3, (9, 9, 9))])))]
        r = scoring.rates_1x24(rows)["sonnet-med"]
        self.assertAlmostEqual(r["official_acc"], 2 / 3)
        self.assertAlmostEqual(r["original_acc"], 1 / 3)
        self.assertAlmostEqual(r["format_compliance_original"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
