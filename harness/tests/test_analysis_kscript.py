import unittest
from decimal import Decimal
from fractions import Fraction

from harness.analysis.kscript import (annotate, k_sensitivity, k_star, k_table, k_value, model_key, parse_custom_id,
                                      realised_spend, rows_of_sets)

D = Decimal
HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"


def row(set_id, base, shape, setup, n, model, cost, effort="medium", kind="answered"):
    return {"custom_id": f"{set_id}-{base:03d}-{shape}-{setup}-{n:02d}", "requested_model": model, "effort": effort,
            "cost_usd": cost, "kind": kind, "refusal_category": "", "right": "1"}


class Parsing(unittest.TestCase):
    def test_custom_id(self):
        p = parse_custom_id("pilot-digits-d4s-v1-003-24x1-hm-07")
        self.assertEqual((p["puzzle"], p["set_id"], p["base_index"], p["shape"], p["setup"], p["sample"], p["realtime"]),
                         ("pilot-digits-d4s-v1-003-24x1", "pilot-digits-d4s-v1", 3, "24x1", "hm", 7, False))
        self.assertTrue(parse_custom_id("s-000-1x24-rtom-01")["realtime"])
        with self.assertRaises(ValueError):
            parse_custom_id("not-a-pilot-id")

    def test_model_key_and_annotate(self):
        self.assertEqual(model_key(HAIKU, "medium"), "haiku-medium")
        self.assertEqual(model_key(OPUS, "high"), "opus-high")
        self.assertEqual(model_key(OPUS, ""), "opus-default")
        a = annotate(row("s", 0, "1x24", "om", 1, OPUS, "0.5"))
        self.assertEqual((a["model_key"], a["shape"], a["puzzle"]), ("opus-medium", "1x24", "s-000-1x24"))


class KValue(unittest.TestCase):
    def test_floor(self):
        r = k_value(D("0.0950"), D("0.0100"))
        self.assertEqual((r["k"], r["raw_k"], r["capped"], r["h1_not_run"]), (9, 9, False, False))
        self.assertEqual(k_value(D("0.10"), D("0.01"))["k"], 10)                   # exact ratio is not rounded down
        self.assertEqual(k_value("0.0299", "0.01")["k"], 2)                       # strings and floats are accepted

    def test_cap_and_samples_drawn(self):
        r = k_value(D("1.00"), D("0.01"))
        self.assertEqual((r["k"], r["raw_k"], r["capped"], r["capped_by"]), (40, 100, True, "cap"))
        r = k_value(D("1.00"), D("0.01"), samples_drawn=10)
        self.assertEqual((r["k"], r["capped"], r["capped_by"]), (10, True, "samples_drawn"))
        r = k_value(D("0.10"), D("0.01"), samples_drawn=10)
        self.assertEqual((r["k"], r["capped"]), (10, False))                       # 10 fits exactly: not capped
        r = k_value(D("1.00"), D("0.01"), cap=40, samples_drawn=60)
        self.assertEqual(r["capped_by"], "cap")
        self.assertEqual(k_value(D("1.00"), D("0.01"), cap=5)["k"], 5)

    def test_k_zero_when_haiku_costs_more(self):
        r = k_value(D("0.004"), D("0.005"))
        self.assertEqual((r["k"], r["h1_not_run"], r["capped"]), (0, True, False))
        self.assertEqual(r["spend"]["haiku_arm"], D(0))

    def test_exact_rational_floor_at_79_puzzles(self):
        # Decimal division of the mean 37/79 by the mean 1/79 gives 36.999...9 (k = 36); the exact ratio is 37.
        self.assertEqual((D(37) / D(79)) / (D(1) / D(79)) < 37, True)               # the trap this test guards against
        r = k_value(Fraction(37, 79), Fraction(1, 79))
        self.assertEqual((r["k"], r["raw_k"], r["ratio"]), (37, 37, Fraction(37)))
        self.assertEqual(k_star(Fraction(37, 79), Fraction(1, 79))["k_star"], Fraction(37))

    def test_79_puzzle_means_stay_exact_through_k_table(self):
        # 79 puzzles: comparator costs total 0.37 (mean 0.37/79), Haiku samples (one per puzzle) total 0.01 (mean 0.01/79).
        # Both means repeat forever; Decimal division would give 36.99..., the exact ratio is 37.
        comp = ["0.004"] * 78 + ["0.058"]
        hk = ["0.0001"] * 78 + ["0.0022"]
        rows = [row("s", b, "24x1", "om", 1, OPUS, comp[b]) for b in range(79)]
        rows += [row("s", b, "24x1", "hm", 1, HAIKU, hk[b]) for b in range(79)]
        c = k_table(rows)["opus"][0]
        self.assertEqual((c["ratio"], c["raw_k"]), (Fraction(37), 37))
        self.assertEqual((c["k"], c["samples_drawn"]), (1, 1))                      # only one sample per puzzle was drawn
        self.assertEqual(c["k_star"]["ratio"], Fraction(37))
        self.assertEqual(k_table(rows)["opus"][0]["k_star"]["k_star"], Fraction(1))   # capped at the 1 sample drawn
        mean_o = sum(map(D, comp), D(0)) / 79
        mean_h = sum(map(D, hk), D(0)) / 79
        self.assertLess(mean_o / mean_h, 37)                                        # the Decimal route is wrong here

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            k_value(D("1"), D("0"))
        with self.assertRaises(ValueError):
            k_value(D("-1"), D("0.1"))

    def test_realised_spend(self):
        s = realised_spend(9, D("0.095"), D("0.010"), n_puzzles=20)
        self.assertEqual((s["haiku_arm"], s["comparator_arm"], s["difference"]), (D("1.800"), D("1.900"), D("-0.100")))
        self.assertEqual(k_value(D("0.095"), D("0.010"))["spend"]["haiku_arm"], D("0.090"))


class Sensitivity(unittest.TestCase):
    def test_set(self):
        s = k_sensitivity(9, median_ratio=D("11.7"), pilot_ratio=D("7.9"), cap=40, samples_drawn=10)
        self.assertEqual(s["k_band"], [7, 8, 9, 10])                         # 11 is above the 10 samples drawn
        self.assertEqual((s["k_median_ratio"], s["k_pilot_ratio"]), (10, 7))
        self.assertEqual(s["k_values"], [7, 8, 9, 10])
        self.assertNotIn("k_interpolated", s)                                # the interpolated row comes from k_star

    def test_bounds(self):
        s = k_sensitivity(1, median_ratio=D("0.4"), pilot_ratio=D("0.9"))
        self.assertEqual(s["k_band"], [1, 2, 3])
        self.assertEqual((s["k_median_ratio"], s["k_pilot_ratio"]), (1, 1))   # never below 1 where the main k is 1 or more
        s = k_sensitivity(40, median_ratio=D("95"))
        self.assertEqual(s["k_band"], [38, 39, 40])
        self.assertEqual(max(s["k_values"]), 40)                              # never above the cap
        self.assertEqual(s["k_median_ratio"], 40)
        self.assertIsNone(k_sensitivity(5)["k_median_ratio"])

    def test_k_zero_stays_zero_and_has_no_set(self):
        s = k_sensitivity(0, median_ratio=D("0.5"), pilot_ratio=Fraction(9, 10))
        self.assertEqual((s["k_median_ratio"], s["k_pilot_ratio"]), (0, 0))   # reported as 0, not raised to 1
        self.assertEqual((s["k_band"], s["k_values"]), ([], []))
        self.assertEqual(k_sensitivity(0)["k_values"], [])
        self.assertIsNone(k_sensitivity(0)["k_median_ratio"])


class KStar(unittest.TestCase):
    def test_no_floor_no_rounding(self):
        r = k_star(D("0.0950"), D("0.0100"))
        self.assertEqual((r["k_star"], r["k_star_float"], r["capped"], r["h1_not_run"]), (Fraction(19, 2), 9.5, False, False))
        r = k_star(D("0.294"), D("0.01"))
        self.assertEqual((r["k_star"], r["k_star_float"]), (Fraction(147, 5), 29.4))
        self.assertEqual(k_star(D("0.10"), D("0.01"))["k_star"], Fraction(10))      # whole stays whole
        self.assertEqual(k_star(0.0299, 0.01)["k_star"], Fraction(299, 100))        # floats go through their short repr

    def test_cap_and_samples_drawn_no_extrapolation(self):
        r = k_star(D("1.00"), D("0.01"))
        self.assertEqual((r["k_star"], r["ratio"], r["capped"], r["capped_by"]), (Fraction(40), Fraction(100), True, "cap"))
        r = k_star(D("0.097"), D("0.01"), samples_drawn=6)
        self.assertEqual((r["k_star"], r["capped"], r["capped_by"]), (Fraction(6), True, "samples_drawn"))
        self.assertEqual(k_star(D("0.06"), D("0.01"), samples_drawn=6)["capped"], False)   # exactly 6 fits

    def test_below_one_is_h1_not_run(self):
        r = k_star(D("0.004"), D("0.005"))
        self.assertEqual((r["h1_not_run"], r["k_star"], r["capped"]), (True, Fraction(4, 5), False))
        self.assertEqual(k_star(D("0.005"), D("0.005"))["h1_not_run"], False)       # exactly 1 is run

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            k_star(D("1"), D("0"))
        with self.assertRaises(ValueError):
            k_star(D("-1"), D("0.1"))


def make_rows():
    """Two shapes x 2 puzzles. Haiku-medium x10, Haiku-low x10, Sonnet x1, Opus x1; Haiku costs vary within a puzzle."""
    rows = []
    for shape, opus_cost, sonnet_cost in (("24x1", ("0.20", "0.30"), ("0.10", "0.14")), ("1x24", ("0.09", "0.11"), ("0.05", "0.05"))):
        for base in range(2):
            rows.append(row("s", base, shape, "om", 1, OPUS, opus_cost[base]))
            rows.append(row("s", base, shape, "sm", 1, SONNET, sonnet_cost[base]))
            for n in range(1, 11):
                rows.append(row("s", base, shape, "hm", n, HAIKU, "0.02" if n <= 9 else "0.03", kind="answered"))
                rows.append(row("s", base, shape, "hl", n, HAIKU, "0.01", effort="low"))
    rows.append(row("s", 0, "24x1", "rthm", 1, HAIKU, "5.0"))                    # real-time: left out
    return rows


class Table(unittest.TestCase):
    def cell(self, t, shape, hk, side="opus"):
        return [c for c in t[side] if c["shape"] == shape and c["haiku_key"] == hk][0]

    def test_cells(self):
        t = k_table(make_rows())
        c = self.cell(t, "24x1", "haiku-medium")
        self.assertEqual(c["comparator_cost_per_puzzle"], D("0.25"))               # mean of 0.20 and 0.30
        self.assertEqual(c["haiku_cost_per_sample"], D("0.021"))                  # (9 * 0.02 + 0.03) / 10, the real-time row not in
        self.assertEqual((c["k"], c["raw_k"], c["capped"]), (10, 11, True))      # floor(0.25 / 0.021) = 11, but 10 drawn
        self.assertEqual(c["n_puzzles_comparator"], 2)

    def test_samples_drawn_cap_applies(self):
        t = k_table(make_rows())
        c = self.cell(t, "24x1", "haiku-medium")
        self.assertEqual((c["samples_drawn"], c["k"]), (10, 10))
        self.assertEqual(c["capped_by"], "samples_drawn")
        low = self.cell(t, "24x1", "haiku-low")
        self.assertEqual((low["k"], low["capped_by"]), (10, "samples_drawn"))   # floor(0.25 / 0.01) = 25, 10 drawn

    def test_per_shape_and_per_effort(self):
        t = k_table(make_rows())
        self.assertEqual(len(t["opus"]), 4)                                       # 2 shapes x 2 Haiku efforts
        c = self.cell(t, "1x24", "haiku-medium")
        self.assertEqual(c["comparator_cost_per_puzzle"], D("0.10"))
        self.assertEqual(c["raw_k"], 4)                                           # floor(0.10 / 0.021)
        self.assertEqual(c["k"], 4)
        self.assertEqual(c["spend"]["haiku_arm"], D("0.084"))
        self.assertEqual(c["spend_by_k"][4]["comparator_arm"], D("0.20"))         # 2 puzzles x 0.10
        self.assertEqual(c["sensitivity"]["k_band"], [2, 3, 4, 5, 6])

    def test_sonnet_contrast_uses_its_own_costs(self):
        t = k_table(make_rows())
        s = self.cell(t, "24x1", "haiku-medium", "sonnet")
        self.assertEqual(s["comparator_key"], "sonnet-medium")
        self.assertEqual(s["comparator_cost_per_puzzle"], D("0.12"))
        self.assertEqual(s["raw_k"], 5)                                           # floor(0.12 / 0.021)
        o = self.cell(t, "24x1", "haiku-medium", "opus")
        self.assertNotEqual(s["k"], o["k"])

    def test_median_ratio_and_passed_in_values(self):
        t = k_table(make_rows(), pilot_ratio=D("3.5"))
        c = self.cell(t, "1x24", "haiku-medium")
        self.assertEqual(c["median_ratio"], (Fraction(9, 100) + Fraction(11, 100)) / 2 / Fraction(21, 1000))
        s = c["sensitivity"]
        self.assertEqual((s["k_median_ratio"], s["k_pilot_ratio"]), (4, 3))
        self.assertEqual(c["k_star"]["k_star"], Fraction(1, 10) / Fraction(21, 1000))   # 100/21, no floor
        self.assertEqual(self.cell(t, "24x1", "haiku-medium")["k_star"]["k_star"], Fraction(10))   # capped by 10 drawn

    def test_no_sonnet_rows_gives_no_sonnet_cells(self):
        rows = [r for r in make_rows() if SONNET not in r["requested_model"]]
        self.assertEqual(k_table(rows)["sonnet"], [])

    def test_all_in_cost_counts_failures_and_missing_costs(self):
        rows = [row("s", 0, "24x1", "om", 1, OPUS, "1.00")]
        rows += [row("s", 0, "24x1", "hm", 1, HAIKU, "0.30", kind="refusal"),
                 row("s", 0, "24x1", "hm", 2, HAIKU, "0.30", kind="answered"),
                 row("s", 0, "24x1", "hm", 3, HAIKU, "", kind="error")]
        c = k_table(rows)["opus"][0]
        self.assertEqual(c["haiku_cost_per_sample"], D("0.20"))                   # (0.30 + 0.30 + 0) / 3
        self.assertEqual((c["rows_without_cost"], c["n_haiku_samples"], c["k"]), (1, 3, 3))   # 5 fit, only 3 drawn

    def test_k_zero_cell_and_rows_of_sets(self):
        rows = [row("s", 0, "24x1", "om", 1, OPUS, "0.01"), row("s", 0, "24x1", "hm", 1, HAIKU, "0.05"),
                row("other", 0, "24x1", "om", 1, OPUS, "9")]
        c = k_table(rows_of_sets(rows, ["s"]))["opus"][0]
        self.assertEqual((c["k"], c["h1_not_run"]), (0, True))
        self.assertEqual(c["sensitivity"]["k_values"], [])
        self.assertEqual(c["spend_by_k"], {})
        self.assertEqual(c["spend"]["haiku_arm"], D(0))
        self.assertEqual((c["k_star"]["h1_not_run"], c["k_star"]["k_star"]), (True, Fraction(1, 5)))
        self.assertEqual((c["sensitivity"]["k_median_ratio"], c["sensitivity"]["k_pilot_ratio"]), (0, None))

    def test_k_zero_through_k_table_with_a_pilot_ratio_and_other_cells(self):
        # shape 24x1: Haiku dearer than Opus (k = 0); shape 1x24: cheap Haiku (k = 4). Nothing raises, the cells are independent.
        rows = [row("s", 0, "24x1", "om", 1, OPUS, "0.01"), row("s", 0, "1x24", "om", 1, OPUS, "0.04")]
        rows += [row("s", 0, sh, "hm", n, HAIKU, "0.05" if sh == "24x1" else "0.01") for sh in ("24x1", "1x24") for n in (1, 2, 3, 4, 5)]
        t = k_table(rows, pilot_ratio=D("0.7"))
        by = {c["shape"]: c for c in t["opus"]}
        self.assertEqual((by["24x1"]["k"], by["24x1"]["h1_not_run"], by["24x1"]["sensitivity"]["k_values"]), (0, True, []))
        self.assertEqual(by["24x1"]["sensitivity"]["k_pilot_ratio"], 0)
        self.assertEqual((by["1x24"]["k"], by["1x24"]["h1_not_run"]), (4, False))


if __name__ == "__main__":
    unittest.main()
