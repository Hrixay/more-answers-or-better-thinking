"""Known-answer tests: the analysis code against Karen's simulated main-run datasets (`research/fixtures/sim-main-v1/`).

Each case has rows (one per scored call) and `expected.json` from her reference implementation (numpy, a different random stream). What must
match: the k values computed from the written rows, the actual gap d for every test in every view (exactly: it involves no random numbers),
and the three-way reading for every reading not marked `near_threshold`. The p-values and intervals must agree within Monte-Carlo error when
the tie convention is set to hers (strict `<` in z0, `bootstrap.TIE_WEIGHT = 0.0`); the default convention (mid-share, ties count half) may
differ from hers by a few hundredths on discrete data and is only required to give the same readings.

Since D-76 the official 1x24 score is the trace score (`test_analysis_fixtures_v2.py`, on `sim-main-v2`). The v1 rows carry only a final answer
at 1x24, which is exactly the answer-only fallback (D-36(5): the final answer scores every arm), so they are loaded with `answer_only` set on
the 1x24 rows of every arm but E3. The v1 expected values are unchanged: they test 24x1 and that fallback path.
"""

import json
import unittest
from pathlib import Path

from harness.analysis import bootstrap, five_tests as ft

FIX = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v1"
CASES = ["ni", "d0", "d-5", "d-10", "d-15", "worse", "mixed"]
VIEWS = {"as_deployed": "as_deployed", "refusals_out": "refusals_left_out", "truncations_out": "truncations_left_out"}
P_TOLERANCE = 0.02            # Monte-Carlo error between two bootstraps of 10,000 draws on the same data (observed worst: about 0.01)
CI_TOLERANCE = 1.3            # points: one step of the grid that single 0/1 answers give (100 / 80 = 1.25) plus noise


def load(case):
    rows = ft.load_rows(FIX / case / "rows.jsonl.gz")
    for r in rows:
        if r["shape"] == "1x24" and r["setup"] != "e3":
            r["answer_only"] = True                 # v1 rows hold the final answer only: the answer-only fallback path
    exp = json.loads((FIX / case / "expected.json").read_text())
    return rows, exp


@unittest.skipUnless(FIX.is_dir(), "research/fixtures/sim-main-v1 is not in this tree")
class KnownAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {c: load(c) for c in CASES}

    def test_k_from_the_written_rows_matches_the_generator(self):
        for case, (rows, exp) in self.data.items():
            kk = ft.k_from_rows(rows)
            self.assertEqual({s: kk["opus"][s]["k"] for s in ("24x1", "1x24")}, exp["k"]["opus_matched"], case)
            self.assertEqual(kk["sonnet"]["1x24"]["k"], exp["k"]["sonnet_matched_1x24"], case)

    def test_the_actual_gaps_match_in_every_view(self):
        for case, (rows, exp) in self.data.items():
            ko, ks = exp["k"]["opus_matched"], exp["k"]["sonnet_matched_1x24"]
            for view, ev in VIEWS.items():
                diffs = ft.test_differences(rows, ko, ks, view)
                for t, e in exp["readings"][ev].items():
                    self.assertEqual(len(diffs[t]), e["n"], (case, view, t))
                    self.assertAlmostEqual(sum(diffs[t]) / len(diffs[t]), e["d_hat"], delta=0.0015, msg=(case, view, t))

    def _check(self, case, view, tie_weight, strict_numbers):
        rows, exp = self.data[case]
        ko, ks = exp["k"]["opus_matched"], exp["k"]["sonnet_matched_1x24"]
        old = bootstrap.TIE_WEIGHT
        bootstrap.TIE_WEIGHT = tie_weight
        try:
            res = ft.analyse(rows, ko, ks, view)
        finally:
            bootstrap.TIE_WEIGHT = old
        for t, e in exp["readings"][VIEWS[view]].items():
            mine = res["tests"][t]
            if not e["near_threshold"]:
                self.assertEqual(mine["reading"], e["reading"], (case, view, t, tie_weight))
            if strict_numbers:
                self.assertAlmostEqual(mine["p"], e["p"], delta=P_TOLERANCE, msg=(case, view, t))
                self.assertAlmostEqual(mine["ci95"][0], e["ci95"][0], delta=CI_TOLERANCE, msg=(case, view, t))
                self.assertAlmostEqual(mine["ci95"][1], e["ci95"][1], delta=CI_TOLERANCE, msg=(case, view, t))

    def test_strict_tie_convention_reproduces_the_reference_p_values_and_intervals(self):
        for case in CASES:
            self._check(case, "as_deployed", 0.0, True)
        for view in ("refusals_out", "truncations_out"):
            self._check("mixed", view, 0.0, True)

    def test_default_tie_convention_gives_the_same_readings(self):
        for case in CASES:
            self._check(case, "as_deployed", bootstrap.TIE_WEIGHT, False)
        for view in ("refusals_out", "truncations_out"):
            self._check("mixed", view, bootstrap.TIE_WEIGHT, False)

    def test_the_holm_order_in_the_mixed_case(self):
        rows, exp = self.data["mixed"]
        res = ft.analyse(rows, exp["k"]["opus_matched"], exp["k"]["sonnet_matched_1x24"])
        order = [t for t in res["holm_order"]]
        e = exp["readings"]["as_deployed"]
        self.assertEqual(order, sorted(e, key=lambda t: e[t]["holm_step"]))


if __name__ == "__main__":
    unittest.main()
