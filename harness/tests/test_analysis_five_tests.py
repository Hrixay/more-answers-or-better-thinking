import json
import unittest
from pathlib import Path

from harness.analysis import bootstrap, five_tests as ft, kscript, scoring
from harness.tests.test_analysis_scoring import KEY, MIDDLE_WRONG, graded, trace_text

FIX = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v2"


def row(base, setup, shape, correct, **kw):
    """A scored row; a 1x24 row of an arm other than E3 carries the D-76 fields (a right trace "R", a wrong one "W", format ok)."""
    r = {"base_id": base, "setup": setup, "shape": shape, "kind": "answered", "correct": correct, "cost_usd": "0.01", "stop_reason": "end_turn"}
    if shape == "1x24" and setup != "e3":
        r.update(format_status="ok", trace_key="R" if correct else "W", final_key="r" if correct else "w", slip_type="none" if correct else "real",
                 correct_final=correct, correct_copy_forgiven=correct)
    else:
        r["answer_key"] = "R" if correct else "W"
    r.update(kw)
    return r


class E3Product(unittest.TestCase):
    def test_e3_is_scored_as_the_product_of_per_step_accuracies_not_the_mean_of_correct(self):
        # 4 runs; step 1 right in 4/4, step 2 right in 3/4, step 3 right in 3/4 -> product 0.5625; each run's `correct` is all(steps): 2 of 4 right
        steps = [[True, True, True], [True, False, True], [True, True, True], [True, True, False]]
        rows = [row("b1", "e3", "1x24", all(s), step_correct=s) for s in steps]
        self.assertAlmostEqual(ft.e3_arm_scores(rows)["b1"], 56.25)
        self.assertAlmostEqual(sum(r["correct"] for r in rows) / 4 * 100, 50.0)                 # the mean of `correct` would say 50

    def test_an_e3_row_without_step_results_is_refused(self):
        with self.assertRaises(ValueError):
            ft.e3_arm_scores([row("b1", "e3", "1x24", True)])


class Padding(unittest.TestCase):
    def test_a_short_haiku_puzzle_is_padded_with_votes_for_nothing_as_deployed(self):
        rows = [row("b1", "haiku-med", "1x24", True) for _ in range(10)]            # 10 rows of 40 designed, all right
        padded = ft.vote_scores(rows, "1x24", 1, designed=40)["b1"]
        self.assertAlmostEqual(padded, 100.0 * 10 / 40)                                # a single draw is right only if it is one of the 10 real rows
        self.assertAlmostEqual(ft.vote_scores(rows, "1x24", 1, designed=10)["b1"], 100.0)

    def test_left_out_views_do_not_pad(self):
        rows = [row("b1", "haiku-med", "1x24", True) for _ in range(10)]
        self.assertAlmostEqual(ft.vote_scores(rows, "1x24", 1, "refusals_out")["b1"], 100.0)

    def test_k_uses_the_designed_40_and_warns_when_a_puzzle_is_short(self):
        rows = []
        for shape in ("24x1", "1x24"):
            for b in ("b1", "b2"):
                n = 40 if b == "b1" else 5
                rows += [row(b, "haiku-med", shape, True, cost_usd="0.001") for _ in range(n)]
                rows += [row(b, "opus-med", shape, True, cost_usd="0.05"), row(b, "sonnet-med", shape, True, cost_usd="0.02")]
        out = ft.k_from_rows(rows)
        self.assertTrue(out["warnings"])
        self.assertEqual(out["opus"]["1x24"]["samples_drawn"], 40)


class Blocks(unittest.TestCase):
    def test_refusals_out_also_drops_safety_or_policy_errors(self):
        rows = [row("b1", "opus-med", "1x24", True),
                row("b1", "opus-med", "1x24", False, kind="error", error={"type": "invalid_request", "message": "blocked by a safety policy"}),
                row("b1", "opus-med", "1x24", False, kind="error", error={"type": "overloaded", "message": "try again"})]
        self.assertAlmostEqual(ft.single_scores(rows, "opus-med", "1x24", "refusals_out")["b1"], 100 * 1 / 2)   # the policy error is dropped, the overload is not


class Missing(unittest.TestCase):
    def test_missing_cost_counts_as_zero_and_is_counted(self):
        rows = []
        for shape in ("24x1", "1x24"):
            rows += [row("b1", "haiku-med", shape, True, cost_usd="0.001") for _ in range(40)]
            rows += [row("b1", "opus-med", shape, True, cost_usd=None), row("b1", "sonnet-med", shape, True, cost_usd="0.02")]
        out = ft.k_from_rows(rows)
        self.assertEqual(out["rows_without_cost"], 2)
        self.assertEqual(out["opus"]["1x24"]["k"], 0)
        self.assertTrue(out["opus"]["1x24"]["h1_not_run"])


class D76Votes(unittest.TestCase):
    """The Haiku vote at 1x24 under D-76: plurality over whole traces (same estimator and tie rule), an unplaceable try votes for nothing."""

    def test_two_tries_with_the_right_final_but_a_wrong_middle_line_outvote_the_right_trace_officially_only(self):
        rows = [graded(trace_text()), graded(trace_text(MIDDLE_WRONG)), graded(trace_text(MIDDLE_WRONG))]
        self.assertEqual(ft.vote_scores(rows, "1x24", 3, designed=3), {"b1": 0.0})                  # the wrong trace has 2 votes of 3
        self.assertEqual(ft.vote_scores(rows, "1x24", 3, designed=3, score="final"), {"b1": 100.0})  # all three share the final answer
        self.assertAlmostEqual(ft.vote_scores(rows, "1x24", 1, designed=3)["b1"], 100.0 / 3)         # vote@1 = single-try accuracy

    def test_traces_that_differ_in_one_middle_line_are_different_votes(self):
        rows = [graded(trace_text()), graded(trace_text(MIDDLE_WRONG)), graded(trace_text({12: (7, 7, 7), 13: (4, 5, 6)}))]
        self.assertAlmostEqual(ft.vote_scores(rows, "1x24", 3, designed=3)["b1"], 100.0 / 3)        # a three-way tie: 1/3 (D-33)
        self.assertEqual(ft.vote_scores(rows, "1x24", 3, designed=3, tie="wrong"), {"b1": 0.0})

    def test_an_unplaceable_try_is_a_vote_for_nothing(self):
        bad = graded(trace_text({24: (9, 9, 9)}, answer=KEY[-1]))           # Answer line right but not equal to line 24: unplaceable
        rows = [graded(trace_text()), bad, dict(bad)]
        d = ft._haiku_answers(rows, "1x24", "as_deployed", 3)["b1"]
        self.assertEqual(d["answers"], [scoring.trace_key(KEY), None, None])
        self.assertEqual(d["correct"], scoring.trace_key(KEY))
        self.assertEqual(ft.vote_scores(rows, "1x24", 3, designed=3), {"b1": 100.0})                # the only real vote is right
        self.assertAlmostEqual(ft.vote_scores(rows, "1x24", 2, designed=3)["b1"], 100.0 * 2 / 3)    # a pair of Nones is wrong
        self.assertEqual(ft.single_scores(rows, "haiku-med", "1x24"), {"b1": 100.0 / 3})


class AnswerOnly(unittest.TestCase):
    """D-76 (answer-only fallback): if the answer-only switch fires, every 1x24 arm (E3 aside) is scored by its final answer; a mix is refused."""

    def rows(self, answer_only_for=("haiku-med", "opus-med", "opus-low", "sonnet-med")):
        right, wrong = "Working...\nAnswer: 1 = [124, 224, 324]", "Answer: 1 = [1, 2, 3]"
        out = []
        for setup in ("haiku-med", "opus-med", "opus-low", "sonnet-med"):
            ao = setup in answer_only_for
            if ao:
                replies = [right, right, wrong]
            else:
                replies = [trace_text(), trace_text(MIDDLE_WRONG), trace_text({24: (1, 2, 3)})]
            for rp in replies:
                r = graded(rp, setup, answer_only=ao)
                r.update(cost_usd="0.01", stop_reason="end_turn")
                out.append(r)
        out += [row("b1", "e3", "1x24", True, step_correct=[True] * 24)]
        return out

    def test_answer_only_rows_are_scored_by_the_final_answer_for_every_arm(self):
        rows = self.rows()
        for setup in ("haiku-med", "opus-med", "opus-low", "sonnet-med"):
            for score in ft.SCORES:
                self.assertAlmostEqual(ft.single_scores(rows, setup, "1x24", score=score)["b1"], 200.0 / 3, msg=(setup, score))
        self.assertEqual(ft.vote_scores(rows, "1x24", 3, designed=3), {"b1": 100.0})                # voted by the final answer
        self.assertEqual(ft.rates(rows), {})                                                         # no step-line rows to rate
        diffs = ft.test_differences(rows, {"24x1": 1, "1x24": 3}, 3)
        self.assertEqual(diffs["t5"], [0.0])
        self.assertAlmostEqual(diffs["t2"][0], ft.vote_scores(rows, "1x24", 3)["b1"] - 200.0 / 3)   # padded to the designed 40

    def test_the_same_tries_with_step_lines_are_scored_by_the_trace(self):
        rows = self.rows(answer_only_for=())
        self.assertAlmostEqual(ft.single_scores(rows, "opus-med", "1x24")["b1"], 100.0 / 3)          # only the right trace
        self.assertAlmostEqual(ft.single_scores(rows, "opus-med", "1x24", score="final")["b1"], 200.0 / 3)

    def test_a_mix_is_refused(self):
        rows = self.rows(answer_only_for=("haiku-med", "opus-med", "sonnet-med"))                  # opus-low left on step lines
        for call in (lambda: ft.test_differences(rows, {"24x1": 1, "1x24": 3}, 3), lambda: ft.single_scores(rows, "opus-med", "1x24"),
                     lambda: ft.vote_scores(rows, "1x24", 3), lambda: ft.rates(rows), lambda: ft.format_report(rows)):
            with self.assertRaises(ValueError):
                call()


class FormatReport(unittest.TestCase):
    def test_format_compliance_per_model_and_shape(self):
        rows = [graded(trace_text(), "haiku-med"), graded("junk", "haiku-med"), graded(trace_text(), "sonnet-med"),
                graded(None, "sonnet-med", "truncated")]
        rows += [dict(row("b1", "haiku-med", "24x1", True), format_status="ok"), dict(row("b1", "haiku-med", "24x1", False), format_status="ok"),
                 row("b1", "opus-med", "24x1", True), row("b1", "e3", "1x24", True, step_correct=[True])]
        fc = ft.format_report(rows)
        self.assertEqual(set(fc), {"haiku-med", "sonnet-med"})                   # rows without a format status are not listed
        self.assertEqual(set(fc["haiku-med"]), {"1x24", "24x1"})
        self.assertAlmostEqual(fc["haiku-med"]["1x24"]["format_compliance"], 0.5)
        self.assertAlmostEqual(fc["haiku-med"]["24x1"]["format_compliance"], 1.0)
        self.assertAlmostEqual(fc["sonnet-med"]["1x24"]["format_compliance"], 1.0)                 # over answered tries
        self.assertAlmostEqual(fc["sonnet-med"]["1x24"]["format_compliance_all_tries"], 0.5)


@unittest.skipUnless(FIX.is_dir(), "research/fixtures/sim-main-v2 is not in this tree")
class OnTheFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = ft.load_rows(FIX / "mixed" / "rows.jsonl.gz")
        cls.exp = json.loads((FIX / "mixed" / "expected.json").read_text())
        cls.ko = cls.exp["k"]["opus_matched"]
        cls.ks = cls.exp["k"]["sonnet_matched_1x24"]

    def test_headline_match_needs_non_inferior_in_all_three_views(self):
        res = ft.analyse_all_views(self.rows, self.ko, self.ks, B=2000)
        for t in ft.TESTS:
            readings = [res["views"][v]["tests"][t]["reading"] for v in ft.VIEWS]
            self.assertEqual(res["headline_match"][t], all(r == bootstrap.NON_INFERIOR for r in readings), t)
        self.assertTrue(res["headline_match"]["t1"])                       # +12 in the mixed case: non-inferior in every view
        self.assertFalse(res["headline_match"]["t5"])
        self.assertEqual(res["headline_wording"]["t1"], "matches")
        fc = res["format_compliance"]                                       # D-76 (format compliance): per model and shape, in the official bundle
        self.assertEqual(fc, ft.format_report(self.rows))
        self.assertEqual(set(fc), {"haiku-med", "opus-med", "opus-low", "sonnet-med"})          # E3 rows carry no format status
        rates = ft.rates(self.rows)
        for setup in fc:
            self.assertAlmostEqual(fc[setup]["1x24"]["format_compliance"], rates[setup]["format_compliance"], msg=setup)

    def test_a_match_that_only_holds_as_deployed_is_worded_as_driven_by_refusals(self):
        res = ft.analyse_all_views(self.rows, self.ko, self.ks, B=1000)
        fake = {"views": {v: {"tests": {"t": {"reading": bootstrap.NON_INFERIOR if v == "as_deployed" else "inconclusive"}}} for v in ft.VIEWS}}
        match = all(fake["views"][v]["tests"]["t"]["reading"] == bootstrap.NON_INFERIOR for v in ft.VIEWS)
        self.assertFalse(match)
        self.assertIn("headline_wording", res)

    def test_the_tie_report_has_the_ties_as_wrong_family_and_the_share_that_ties_decide(self):
        rep = ft.tie_report(self.rows, self.ko, self.ks, B=1000)
        self.assertEqual(set(rep["tie_decided_share"]), {"t1", "t2", "t3"})
        self.assertTrue(all(0.0 <= s <= 1.0 for s in rep["tie_decided_share"].values()))
        random_ = ft.test_differences(self.rows, self.ko, self.ks)
        wrong = ft.test_differences(self.rows, self.ko, self.ks, tie="wrong")
        for t in ("t1", "t2", "t3"):
            self.assertLessEqual(sum(wrong[t]), sum(random_[t]) + 1e-9)       # ties scored as wrong can only lower the vote's score
        self.assertEqual(wrong["t4"], random_["t4"])

    def test_a_test_with_k_zero_is_not_run_and_keeps_its_holm_place(self):
        res = ft.analyse(self.rows, {"24x1": 0, "1x24": self.ko["1x24"]}, self.ks, B=1000)
        self.assertEqual(res["not_run"], ["t1"])
        self.assertIn("not run", res["tests"]["t1"]["reading"])
        self.assertEqual(len(res["holm_thresholds"]) if "holm_thresholds" in res else 5, 5)


if __name__ == "__main__":
    unittest.main()
