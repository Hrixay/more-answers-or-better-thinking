"""Known-answer tests for the D-76 scoring: the analysis code against Karen's v2 simulated main-run datasets (`research/fixtures/sim-main-v2/`).

The rows already carry the D-76 fields (format_status, trace_key, final_key, slip_type, correct = official, correct_final,
correct_copy_forgiven). What must match `expected.json`: k from the written rows; the actual gap d of every test, exactly up to her rounding to
three decimals, in the official score's three views and in the final-answer and copy-slips-forgiven scores as deployed; the per-arm rates at
1x24 (format compliance, the absorbed and copy shares of wrong traces, the three accuracies, to her four decimals); the three-way reading of
every test not marked `near_threshold`; and, with her tie convention (`bootstrap.TIE_WEIGHT = 0.0`), p and the 95% interval within
Monte-Carlo error. The p tolerance is 0.03, not v1's 0.02: over 20 seeds the worst case here (d0, official, t4) gives p 0.387 to 0.410
(sd 0.006) against her 0.387, and with 115 compared p-values one run lands 0.0205 away. With the default tie convention (mid-share) the
readings must agree, except where that convention puts the test on a threshold: the interval's upper end within one grid step (1.3 points)
of the margin, or p within 0.03 of its Holm threshold (Karen's `near_threshold` is computed under her convention; d-15 copy-forgiven t4 is the
one such case: an upper end of exactly -10.0 under the mid-share convention, -11.25 under hers).
"""

import json
import unittest
from pathlib import Path

from harness.analysis import bootstrap, five_tests as ft, scoring

FIX = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v2"
CASES = ["ni", "d0", "d-5", "d-10", "d-15", "worse", "mixed"]
# (score, view, expected.json readings key, view key under it)
OFFICIAL = [("official", "as_deployed", "official", "as_deployed"), ("official", "refusals_out", "official", "refusals_left_out"),
            ("official", "truncations_out", "official", "truncations_left_out")]
OTHERS = [("final", "as_deployed", "final_answer_secondary", "as_deployed"), ("copy_forgiven", "as_deployed", "copy_slips_forgiven", "as_deployed")]
D_TOLERANCE = 0.0005 + 1e-9         # her d_hat is rounded to three decimals
RATE_TOLERANCE = 0.00005 + 1e-9     # her rates are rounded to four decimals
P_TOLERANCE = 0.03
CI_TOLERANCE = 1.3


def load(case):
    return ft.load_rows(FIX / case / "rows.jsonl.gz"), json.loads((FIX / case / "expected.json").read_text())


@unittest.skipUnless(FIX.is_dir(), "research/fixtures/sim-main-v2 is not in this tree")
class KnownAnswersV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {c: load(c) for c in CASES}

    def kk(self, exp):
        return exp["k"]["opus_matched"], exp["k"]["sonnet_matched_1x24"]

    def test_k_from_the_written_rows_matches_the_generator(self):
        for case, (rows, exp) in self.data.items():
            kk = ft.k_from_rows(rows)
            self.assertEqual({s: kk["opus"][s]["k"] for s in ("24x1", "1x24")}, exp["k"]["opus_matched"], case)
            self.assertEqual(kk["sonnet"]["1x24"]["k"], exp["k"]["sonnet_matched_1x24"], case)

    def test_the_actual_gaps_match_in_every_score_and_view(self):
        for case, (rows, exp) in self.data.items():
            ko, ks = self.kk(exp)
            for score, view, ekey, vkey in OFFICIAL + OTHERS:
                diffs = ft.test_differences(rows, ko, ks, view, score=score)
                for t, e in exp["readings"][ekey][vkey].items():
                    self.assertEqual(len(diffs[t]), e["n"], (case, score, view, t))
                    self.assertAlmostEqual(sum(diffs[t]) / len(diffs[t]), e["d_hat"], delta=D_TOLERANCE, msg=(case, score, view, t))

    def test_the_rates_per_arm_at_1x24(self):
        for case, (rows, exp) in self.data.items():
            mine = ft.rates(rows)
            self.assertEqual(set(mine), set(exp["rates_1x24"]), case)
            for setup, er in exp["rates_1x24"].items():
                for k, v in er.items():
                    self.assertAlmostEqual(mine[setup][k], v, delta=RATE_TOLERANCE, msg=(case, setup, k))
                m = mine[setup]
                self.assertAlmostEqual(m["absorption"], m["final_acc"] - m["official_acc"], places=12)   # final right, trace not
                fc = scoring.format_compliance([r for r in rows if scoring.is_trace_row(r)])[(setup,)]
                self.assertEqual((fc["answered"], fc["format_ok"]), (m["answered"], m["format_ok"]))

    def _check(self, case, score, view, ekey, vkey, tie_weight, strict):
        rows, exp = self.data[case]
        ko, ks = self.kk(exp)
        old = bootstrap.TIE_WEIGHT
        bootstrap.TIE_WEIGHT = tie_weight
        try:
            res = ft.analyse(rows, ko, ks, view, score=score)
        finally:
            bootstrap.TIE_WEIGHT = old
        for t, e in exp["readings"][ekey][vkey].items():
            mine = res["tests"][t]
            on_threshold = (not strict and (abs(mine["ci95"][1] - bootstrap.MARGIN) <= CI_TOLERANCE
                                             or abs(mine["p"] - e["holm_threshold"]) <= P_TOLERANCE))
            if not e["near_threshold"] and not on_threshold:
                self.assertEqual(mine["reading"], e["reading"], (case, score, view, t, tie_weight))
            if strict:
                self.assertAlmostEqual(mine["p"], e["p"], delta=P_TOLERANCE, msg=(case, score, view, t))
                self.assertAlmostEqual(mine["ci95"][0], e["ci95"][0], delta=CI_TOLERANCE, msg=(case, score, view, t))
                self.assertAlmostEqual(mine["ci95"][1], e["ci95"][1], delta=CI_TOLERANCE, msg=(case, score, view, t))

    def _combos(self):
        for case in CASES:
            yield (case,) + OFFICIAL[0]
            for c in OTHERS:
                yield (case,) + c
        for c in OFFICIAL[1:]:
            yield ("mixed",) + c

    def test_strict_tie_convention_reproduces_the_reference_p_values_and_intervals(self):
        for combo in self._combos():
            self._check(*combo, 0.0, True)

    def test_default_tie_convention_gives_the_same_readings(self):
        for combo in self._combos():
            self._check(*combo, bootstrap.TIE_WEIGHT, False)

    def test_the_secondary_bundle(self):
        rows, exp = self.data["mixed"]
        ko, ks = self.kk(exp)
        sec = ft.analyse_secondary(rows, ko, ks, B=1000)
        self.assertEqual((sec["final_answer"]["score"], sec["copy_slips_forgiven"]["score"]), ("final", "copy_forgiven"))
        self.assertEqual(set(sec["rates"]), {"haiku-med", "opus-med", "opus-low", "sonnet-med"})
        self.assertEqual(ft.analyse_all_views(rows, ko, ks, B=1000)["score"], "official")


if __name__ == "__main__":
    unittest.main()
