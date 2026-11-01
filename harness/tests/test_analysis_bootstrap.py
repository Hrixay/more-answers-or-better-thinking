from __future__ import annotations

import itertools
import math
import random
import unittest
from statistics import NormalDist

from harness.analysis import bootstrap as bs


def binomial_diffs(rng, n=80, gap=-0.10, tries=10):
    out = []
    for _ in range(n):
        p_comp = rng.choice([0.25, 0.4, 0.55, 0.7, 0.85, 0.95])
        p_chal = p_comp + gap
        chal = sum(rng.random() < p_chal for _ in range(tries))
        comp = sum(rng.random() < p_comp for _ in range(tries))
        out.append(100.0 * (chal - comp) / tries)
    return out


def skewed_diffs(rng, n=80, shift=0.0):
    return [(-60.0 if rng.random() < 0.2 else 2.5) + shift for _ in range(n)]


def rejection_rate(make, reps, B=1000, alpha=0.025):
    rng = random.Random(7)
    hits = sum(bs.paired_bca(make(rng), B=B, seed=1000 + i)["p_one_sided"] <= alpha for i in range(reps))
    return hits / reps


class Size(unittest.TestCase):
    def test_binomial_at_the_margin_rejects_about_alpha(self):
        rate = rejection_rate(binomial_diffs, 400)
        self.assertTrue(0.005 <= rate <= 0.06, rate)

    def test_skewed_at_the_margin_rejects_about_alpha(self):
        rate = rejection_rate(skewed_diffs, 400)
        self.assertTrue(0.005 <= rate <= 0.06, rate)

    def test_power_when_the_true_gap_is_zero(self):
        rate = rejection_rate(lambda rng: binomial_diffs(rng, gap=0.0), 200)
        self.assertGreater(rate, 0.8)


DATASETS = {
    "binomial": binomial_diffs(random.Random(11), gap=-0.05),
    "skewed": skewed_diffs(random.Random(12), shift=4.0),
    "left-skewed": [-x for x in skewed_diffs(random.Random(13), shift=12.0)],
    "small": [0.0, -20.0, 10.0, -30.0, 0.0, -10.0, 20.0, -40.0],
    "far above": [5.0, 10.0, 0.0, 15.0, 5.0, 10.0] * 10,
}
ALPHAS = [0.001, 0.005, 0.00625, 0.008333, 0.0125, 0.025, 0.05, 0.1, 0.2, 0.5, 0.8]


class Consistency(unittest.TestCase):
    def test_p_and_lower_bound_never_disagree(self):
        for name, diffs in DATASETS.items():
            for margin in (-10.0, -5.0, 0.0):
                boot = bs.bootstrap(diffs, B=2000, seed=5)
                p = bs.p_value(boot, margin)
                for alpha in ALPHAS:
                    if abs(alpha - p) < 1e-9:
                        continue
                    with self.subTest(name=name, margin=margin, alpha=alpha, p=p):
                        self.assertEqual(p <= alpha, bs.lower_end(boot, alpha) > margin)

    def test_public_functions_agree_with_the_shared_bootstrap(self):
        diffs = DATASETS["binomial"]
        r = bs.paired_bca(diffs, B=2000, seed=9)
        for alpha in (0.005, 0.025, 0.1):
            self.assertEqual(r["p_one_sided"] <= alpha, bs.bca_lower_bound(diffs, alpha, B=2000, seed=9) > -10.0)
        self.assertEqual(r["ci95"], bs.bca_interval(diffs, B=2000, seed=9))

    def test_p_is_the_inverse_of_the_bound(self):
        boot = bs.bootstrap(DATASETS["skewed"], B=4000, seed=3)
        for margin in (-12.0, -10.0, -8.0):
            p = bs.p_value(boot, margin)
            self.assertTrue(0.0 < p < 1.0)
            self.assertGreater(bs.lower_end(boot, p * 1.0001), margin)
            self.assertLessEqual(bs.lower_end(boot, p * 0.9999), margin)

    def test_interval_is_mirrored_by_negation(self):
        diffs = DATASETS["skewed"]
        lo, hi = bs.bca_interval(diffs, B=2000, seed=4)
        nlo, nhi = bs.bca_interval([-x for x in diffs], B=2000, seed=4)
        self.assertEqual((nlo, nhi), (-hi, -lo))

    def test_acceleration_matches_the_skewness_formula(self):
        xs = DATASETS["skewed"]
        m = sum(xs) / len(xs)
        expected = sum((x - m) ** 3 for x in xs) / (6 * sum((x - m) ** 2 for x in xs) ** 1.5)
        self.assertAlmostEqual(bs.bootstrap(xs, B=10, seed=1).a, expected, places=12)
        self.assertLess(expected, 0.0)

    def test_symmetric_data_is_close_to_the_normal_approximation(self):
        xs = [float(v) for v in range(-40, 41)] + [0.0] * 9
        boot = bs.bootstrap(xs, B=10_000, seed=2)
        self.assertAlmostEqual(boot.a, 0.0, places=12)
        self.assertLess(abs(boot.z0), 0.05)
        n = len(xs)
        m = sum(xs) / n
        se = math.sqrt(sum((x - m) ** 2 for x in xs) / n / n)
        self.assertAlmostEqual(bs.p_value(boot, -5.0), NormalDist().cdf(-5.0 / se), delta=0.01)


class Holm(unittest.TestCase):
    def test_thresholds_and_order(self):
        p = {"t1": 0.004, "t2": 0.02, "t3": 0.001, "t4": 0.009, "t5": 0.012}
        self.assertEqual(bs.holm_order(p), ["t3", "t1", "t4", "t5", "t2"])
        th = bs.holm_thresholds(p)
        self.assertAlmostEqual(th["t3"], 0.005)
        self.assertAlmostEqual(th["t1"], 0.00625)
        self.assertAlmostEqual(th["t4"], 0.025 / 3)
        self.assertAlmostEqual(th["t5"], 0.0125)
        self.assertAlmostEqual(th["t2"], 0.025)
        self.assertEqual(bs.holm_one_sided(p), {"t1": True, "t2": False, "t3": True, "t4": False, "t5": False})

    def test_early_failure_blocks_a_later_small_p(self):
        p = {"a": 0.006, "b": 0.0061, "c": 0.0124, "d": 0.03, "e": 0.0062}
        self.assertEqual(bs.holm_order(p), ["a", "b", "e", "c", "d"])
        self.assertEqual(set(k for k, v in bs.holm_one_sided(p).items() if v), set())
        p = {"a": 0.004, "b": 0.007, "c": 0.0084, "d": 0.03, "e": 0.012}
        self.assertLessEqual(p["e"], 0.025 / 2)
        self.assertEqual(bs.holm_one_sided(p), {"a": True, "b": False, "c": False, "d": False, "e": False})

    def test_all_pass_and_none_pass(self):
        self.assertTrue(all(bs.holm_one_sided({k: 0.001 for k in "abcde"}).values()))
        self.assertFalse(any(bs.holm_one_sided({k: 0.5 for k in "abcde"}).values()))

    def test_keys_keep_insertion_order(self):
        p = {"z": 0.3, "y": 0.001, "x": 0.02}
        self.assertEqual(list(bs.holm_one_sided(p)), ["z", "y", "x"])

    def test_bad_p_raises(self):
        with self.assertRaises(ValueError):
            bs.holm_one_sided({"a": float("nan")})


class ThreeWay(unittest.TestCase):
    def test_reading_rule(self):
        self.assertEqual(bs.three_way(True, (-5.0, 3.0)), bs.NON_INFERIOR)
        self.assertEqual(bs.three_way(False, (-30.0, -12.0)), bs.WORSE)
        self.assertEqual(bs.three_way(False, (-20.0, -10.0)), bs.INCONCLUSIVE)
        self.assertEqual(bs.three_way(False, (-15.0, -2.0)), bs.INCONCLUSIVE)

    def test_three_constructed_datasets(self):
        rng = random.Random(21)
        tests = {
            "close": [rng.choice([-10.0, 0.0, 0.0, 10.0]) for _ in range(80)],
            "far worse": [rng.choice([-50.0, -30.0, -20.0, -10.0]) for _ in range(80)],
            "noisy": [rng.choice([-60.0, -20.0, 0.0, 30.0]) for _ in range(80)],
        }
        fam = bs.run_family(tests, B=4000)
        got = {name: r["reading"] for name, r in fam["tests"].items()}
        self.assertEqual(got, {"close": bs.NON_INFERIOR, "far worse": bs.WORSE, "noisy": bs.INCONCLUSIVE})
        self.assertEqual(list(fam["tests"]), list(tests))
        self.assertEqual(fam["holm_order"][0], "close")
        for name, r in fam["tests"].items():
            self.assertAlmostEqual(r["d"], sum(tests[name]) / 80)
            self.assertLessEqual(r["ci95"][0], r["d"])
            self.assertGreaterEqual(r["ci95"][1], r["d"])


class Determinism(unittest.TestCase):
    def test_same_seed_same_result(self):
        diffs = DATASETS["binomial"]
        self.assertEqual(bs.paired_bca(diffs), bs.paired_bca(diffs))
        tests = {"t1": diffs, "t2": DATASETS["skewed"]}
        self.assertEqual(bs.run_family(tests, B=2000), bs.run_family(tests, B=2000))

    def test_different_seeds_close_results(self):
        diffs = DATASETS["binomial"]
        a = bs.paired_bca(diffs, seed=1)
        b = bs.paired_bca(diffs, seed=2)
        self.assertNotEqual(a["ci95"], b["ci95"])
        self.assertLess(abs(a["p_one_sided"] - b["p_one_sided"]), 0.01)
        self.assertLess(abs(a["ci95"][0] - b["ci95"][0]), 0.5)
        self.assertLess(abs(a["ci95"][1] - b["ci95"][1]), 0.5)

    def test_test_seeds_differ_by_name_and_are_stable(self):
        self.assertNotEqual(bs.derive_seed(bs.SEED, "t1"), bs.derive_seed(bs.SEED, "t2"))
        self.assertEqual(bs.derive_seed(bs.SEED, "t1"), bs.derive_seed(20261011, "t1"))
        fam = bs.run_family({"t1": DATASETS["small"], "t2": DATASETS["small"]}, B=500)
        self.assertNotEqual(fam["tests"]["t1"]["seed"], fam["tests"]["t2"]["seed"])


class Degenerate(unittest.TestCase):
    def test_all_equal(self):
        for value, p in ((0.0, 0.0), (-10.0, 1.0), (-25.0, 1.0)):
            r = bs.paired_bca([value] * 80)
            self.assertEqual((r["d"], r["p_one_sided"], r["ci95"], r["z0"], r["a"]), (value, p, (value, value), 0.0, 0.0))
            self.assertEqual(bs.bca_lower_bound([value] * 80, 0.025), value)

    def test_one_puzzle(self):
        r = bs.paired_bca([-3.0])
        self.assertEqual((r["n"], r["d"], r["p_one_sided"], r["ci95"]), (1, -3.0, 0.0, (-3.0, -3.0)))

    def test_two_puzzles(self):
        r = bs.paired_bca([0.0, -40.0], B=1000)
        self.assertEqual(r["d"], -20.0)
        self.assertEqual(r["a"], 0.0)
        self.assertTrue(0.0 <= r["p_one_sided"] <= 1.0)
        self.assertTrue(-40.0 <= r["ci95"][0] <= r["ci95"][1] <= 0.0)
        r = bs.paired_bca([10.0, 20.0], B=1000)
        self.assertLess(r["p_one_sided"], 0.01)

    def test_extreme_effects_stay_finite_p(self):
        r = bs.paired_bca(DATASETS["far above"], B=1000)
        self.assertTrue(0.0 <= r["p_one_sided"] < 0.005)
        r = bs.paired_bca([x - 100.0 for x in DATASETS["far above"]], B=1000)
        self.assertGreater(r["p_one_sided"], 0.99)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            bs.paired_bca([])
        with self.assertRaises(ValueError):
            bs.paired_bca([1.0, float("nan")])
        with self.assertRaises(ValueError):
            bs.bca_lower_bound([1.0, 2.0], 0.0)


class SignFlip(unittest.TestCase):
    def test_exact_n4_by_hand(self):
        # |values| 3, 1, 2, 5: the sum is 11 - 2 * (flipped mass); T = 7 needs flipped mass <= 2: {}, {1}, {2}.
        self.assertEqual(bs.sign_flip_p([3.0, 1.0, -2.0, 5.0]), 3 / 16)
        # Shifted by null = 1: y = 2, 0, -3, 4, T = 3; subsets of {2, 3, 4} with mass <= 3 are {}, {2}, {3}, twice for the 0.
        self.assertEqual(bs.sign_flip_p([3.0, 1.0, -2.0, 5.0], null=1.0), 6 / 16)
        self.assertEqual(bs.sign_flip_p([-1.0, -2.0, -3.0, -4.0]), 1.0)
        self.assertEqual(bs.sign_flip_p([1.0, 2.0, 3.0, 4.0]), 1 / 16)

    def test_monte_carlo_matches_exact_enumeration(self):
        rng = random.Random(31)
        xs = [rng.choice([-20.0, -10.0, 0.0, 10.0, 20.0, 30.0]) for _ in range(17)]
        total = sum(xs)
        exact = sum(1 for signs in itertools.product((1, -1), repeat=17)
                    if sum(s * x for s, x in zip(signs, xs)) >= total - 1e-9) / 2 ** 17
        mc = bs.sign_flip_p(xs, nflips=40_000, seed=5)
        self.assertAlmostEqual(mc, exact, delta=0.01)
        self.assertEqual(mc, bs.sign_flip_p(xs, nflips=40_000, seed=5))


if __name__ == "__main__":
    unittest.main()
