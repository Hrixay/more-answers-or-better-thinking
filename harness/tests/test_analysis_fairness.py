from __future__ import annotations

import random
import unittest

from harness.analysis import fairness as fx

# Three presets with different T/G mixes (as in the pilot: T's share rises with the preset).
PRESETS = {"l14": (5, 60, 150), "l15": (6, 100, 100), "l16": (10, 150, 100)}  # bases, T steps, G steps per base
HOUSE_FIRES = 60


def binom(rng, n, p):
    return sum(rng.random() < p for _ in range(n))


def generate(rates, seed):
    """rates[model] = (G rate, T rate, house-missed rate[, misapplied rate, default 1%]). The house rule should fire on HOUSE_FIRES steps per
    base puzzle and not fire on the rest."""
    rng = random.Random(seed)
    out = []
    for preset, (nb, nt, ng) in sorted(PRESETS.items()):
        for b in range(nb):
            for model, r in sorted(rates.items()):
                pg, pt, ph = r[:3]
                pm = r[3] if len(r) > 3 else 0.01
                checked = nt + ng
                quiet = checked - HOUSE_FIRES
                out.append(fx.SlipCounts(preset, f"{preset}-b{b}", model, nt, binom(rng, nt, pt), ng, binom(rng, ng, pg), checked,
                                         HOUSE_FIRES, binom(rng, HOUSE_FIRES, ph), quiet, binom(rng, quiet, pm)))
    return out


def rec(preset, base, model, ts, tsl, gs, gsl, fires=20, missed=0, misap=0):
    return fx.SlipCounts(preset, base, model, ts, tsl, gs, gsl, ts + gs, fires, missed, ts + gs - fires, misap)


class MantelHaenszel(unittest.TestCase):
    def test_two_strata_by_hand(self):
        # h1: a=10, n1=100, b=5, n0=200, N=300: a*n0/N = 2000/300 = 20/3; b*n1/N = 500/300 = 5/3.
        # h2: a=4, n1=50, b=6, n0=50, N=100:     a*n0/N = 200/100 = 2;     b*n1/N = 300/100 = 3.
        # RR_MH = (20/3 + 2) / (5/3 + 3) = (26/3) / (14/3) = 13/7.
        self.assertAlmostEqual(fx.mh_rate_ratio([(10, 100, 5, 200), (4, 50, 6, 50)]), 13 / 7, places=12)
        # The plain pooled ratio differs ((14/150) / (11/250) = 2.1212...), which is why the strata matter.
        self.assertNotAlmostEqual(13 / 7, (14 / 150) / (11 / 250), places=3)

    def test_single_stratum_is_the_plain_rate_ratio(self):
        self.assertAlmostEqual(fx.mh_rate_ratio([(12, 300, 5, 500)]), (12 / 300) / (5 / 500), places=12)
        self.assertAlmostEqual(fx.mh_rate_difference([(12, 300, 5, 500)]), 12 / 300 - 5 / 500, places=12)

    def test_zero_t_slips_correction_by_hand(self):
        # Zero T slips overall -> 0.5 is added to a_h and b_h in every stratum.
        # h1: a=0.5, n1=100, b=4.5, n0=100, N=200: a*n0/N = 0.25;  b*n1/N = 2.25.
        # h2: a=0.5, n1=50,  b=2.5, n0=150, N=200: a*n0/N = 0.375; b*n1/N = 0.625.
        # RR_MH = 0.625 / 2.875 = 5/23.
        strata = [(0, 100, 4, 100), (0, 50, 2, 150)]
        self.assertEqual(fx.mh_rate_ratio_detail(strata), (5 / 23, True))
        self.assertEqual(fx.mh_rate_ratio(strata, correction=False), 0.0)

    def test_zero_g_slips_is_finite_with_correction_and_undefined_without(self):
        strata = [(3, 100, 0, 100)]
        self.assertAlmostEqual(fx.mh_rate_ratio(strata), 3.5 / 0.5)
        self.assertIsNone(fx.mh_rate_ratio(strata, correction=False))

    def test_no_correction_when_both_groups_have_slips(self):
        self.assertEqual(fx.mh_rate_ratio_detail([(1, 100, 1, 100)]), (1.0, False))

    def test_stratum_without_steps_in_a_group_is_left_out(self):
        self.assertAlmostEqual(fx.mh_rate_ratio([(12, 300, 5, 500), (0, 0, 9, 40)]), 4.0)
        self.assertIsNone(fx.mh_rate_ratio([(0, 0, 9, 40)]))
        self.assertIsNone(fx.mh_rate_difference([(0, 0, 9, 40)]))

    def test_bad_strata_raise(self):
        with self.assertRaises(ValueError):
            fx.mh_rate_ratio([(5, 4, 1, 10)])
        with self.assertRaises(ValueError):
            fx.mh_rate_ratio([(-1, 4, 1, 10)])


class KnownAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Haiku: T rate 4x its G rate; Opus: T rate = its G rate. House = G for both.
        cls.tilted = fx.fairness_indices(generate({"haiku": (0.05, 0.20, 0.05), "opus": (0.04, 0.04, 0.04),
                                                   "sonnet": (0.04, 0.06, 0.04)}, seed=1))
        # Both models: T rate 3x G rate. House = G for both.
        cls.fair = fx.fairness_indices(generate({"haiku": (0.05, 0.15, 0.05), "opus": (0.02, 0.06, 0.02),
                                                 "sonnet": (0.03, 0.09, 0.03)}, seed=2))
        # T fair (both 2x); the house rule 4x for Haiku only.
        cls.house = fx.fairness_indices(generate({"haiku": (0.05, 0.10, 0.20), "opus": (0.03, 0.06, 0.03),
                                                  "sonnet": (0.03, 0.06, 0.03)}, seed=3))

    def test_tilted_ti_near_4_and_flag_k_fires_on_ti(self):
        r = self.tilted
        self.assertTrue(3.0 < r["TI"]["point"] < 5.5, r["TI"]["point"])
        self.assertGreater(r["TI"]["ci90"][0], 1.0)
        self.assertLessEqual(r["TI"]["ci90"][0], r["TI"]["point"])
        self.assertGreaterEqual(r["TI"]["ci90"][1], r["TI"]["point"])
        self.assertTrue(r["TI"]["assessable"])
        self.assertEqual(r["TI"]["comparison"], "opus")
        self.assertFalse(r["pooled"]["TI"])
        self.assertTrue(r["flag_k"]["fires"])
        self.assertEqual(r["flag_k"]["reason"], "fires on TI")
        self.assertTrue(0.6 < r["TI_house"]["point"] < 1.6, r["TI_house"]["point"])
        self.assertEqual(r["TI"]["dropped"], 0)
        self.assertEqual(r["TI"]["kept"], 2000)
        self.assertEqual(r["TI"]["correction_share"], 0.0)
        self.assertFalse(r["TI"]["unstable"])

    def test_tilted_rr_and_absolute_differences(self):
        r = self.tilted
        self.assertTrue(3.0 < r["RR"]["haiku"]["point"] < 5.5)
        self.assertTrue(0.6 < r["RR"]["opus"]["point"] < 1.6)
        self.assertIn("sonnet", r["RR"])
        self.assertTrue(0.10 < r["abs_diff"]["haiku"]["point"] < 0.20)
        self.assertGreater(r["abs_diff"]["haiku"]["ci90"][0], 0.0)
        self.assertTrue(-0.03 < r["abs_diff"]["opus"]["point"] < 0.03)
        self.assertAlmostEqual(r["TI"]["point"], r["RR"]["haiku"]["point"] / r["RR"]["opus"]["point"])

    def test_fair_ti_near_1_and_no_flag(self):
        r = self.fair
        self.assertTrue(0.7 < r["TI"]["point"] < 1.4, r["TI"]["point"])
        self.assertTrue(r["TI"]["ci90"][0] < 1.0 < r["TI"]["ci90"][1], r["TI"]["ci90"])
        self.assertFalse(r["flag_k"]["fires"])
        self.assertEqual(r["flag_k"]["reason"], "does not fire")
        self.assertEqual(r["flag_k"]["on"], [])

    def test_house_specific_fires_on_ti_house(self):
        r = self.house
        self.assertTrue(3.0 < r["TI_house"]["point"] < 5.5, r["TI_house"]["point"])
        self.assertEqual(r["flag_k"]["reason"], "fires on TI_house")
        self.assertFalse(r["TI"]["fires"])

    def test_counts_and_per_preset_are_reported(self):
        r = self.tilted
        self.assertEqual(r["presets"], {"l14": 5, "l15": 6, "l16": 10})
        self.assertEqual(r["counts"]["haiku"]["T_steps"], 5 * 60 + 6 * 100 + 10 * 150)
        self.assertEqual(r["per_preset"]["l16"]["opus"]["counts"]["G_steps"], 10 * 100)
        c = r["counts"]["haiku"]
        self.assertEqual(c["house_should_fire"], 21 * HOUSE_FIRES)
        self.assertEqual(c["house_steps_checked"], c["house_should_fire"] + c["house_should_not_fire"])
        self.assertIsNotNone(r["per_preset"]["l14"]["haiku"]["missed_rate"])

    def test_house_index_uses_missed_over_should_fire_only(self):
        # 3 bases, one preset: missed 5/50 per base, G 10/100; misapplied (5 per base) never enters RR_house.
        recs = [rec("p", f"b{i}", m, 100, 10, 100, 10, fires=50, missed=5, misap=5) for i in range(3) for m in ("haiku", "opus")]
        r = fx.fairness_indices(recs, B=50)
        self.assertAlmostEqual(r["RR_house"]["haiku"]["point"], (15 / 150) / (30 / 300))
        recs0 = [rec("p", f"b{i}", m, 100, 10, 100, 10, fires=50, missed=5, misap=0) for i in range(3) for m in ("haiku", "opus")]
        self.assertEqual(fx.fairness_indices(recs0, B=50)["RR_house"], r["RR_house"])


class Misapplied(unittest.TestCase):
    def test_rate_interval_and_difference_haiku_minus_opus(self):
        r = fx.fairness_indices(generate({"haiku": (0.05, 0.10, 0.05, 0.04), "opus": (0.04, 0.08, 0.04, 0.01),
                                          "sonnet": (0.04, 0.08, 0.04, 0.01)}, seed=4), B=500)
        m = r["misapplied"]
        h = r["counts"]["haiku"]
        self.assertAlmostEqual(m["rate"]["haiku"]["point"], h["house_misapplied"] / h["house_should_not_fire"])
        self.assertEqual(m["rate"]["haiku"]["steps_should_not_fire"], h["house_should_not_fire"])
        self.assertTrue(0.03 < m["rate"]["haiku"]["point"] < 0.05)
        lo, hi = m["rate"]["haiku"]["ci90"]
        self.assertTrue(lo <= m["rate"]["haiku"]["point"] <= hi)
        d = m["diff"]["haiku-opus"]
        self.assertAlmostEqual(d["point"], m["rate"]["haiku"]["point"] - m["rate"]["opus"]["point"])
        self.assertGreater(d["ci90"][0], 0.0)
        self.assertEqual(list(m["diff"]), ["haiku-opus"])
        # Not a flag index: a 4x misapplied rate for Haiku alone moves neither TI_house nor the flag.
        self.assertFalse(r["flag_k"]["fires"])

    def test_difference_against_the_pooled_comparison_too(self):
        recs = EnoughData().build(5, 5, 5, 5, opus_missed=1, sonnet_missed=2)
        r = fx.fairness_indices(recs, B=100)
        self.assertEqual(r["comparison"]["TI_house"], "opus+sonnet")
        self.assertEqual(list(r["misapplied"]["diff"]), ["haiku-opus", "haiku-opus+sonnet"])


class Bootstrap(unittest.TestCase):
    def test_stratified_draws_keep_each_presets_count(self):
        bases = {"a": ["a1", "a2", "a3"], "b": [f"b{i}" for i in range(7)], "c": ["c1"]}
        n = 0
        for draw in fx.stratified_draws(bases, 500, fx.SEED):
            n += 1
            self.assertEqual(sorted(draw), ["a", "b", "c"])
            for p, chosen in draw.items():
                self.assertEqual(len(chosen), len(bases[p]))
                self.assertTrue(set(chosen) <= set(bases[p]))
        self.assertEqual(n, 500)

    def test_a_drawn_base_brings_every_model(self):
        # Opus's counts equal Haiku's on every base puzzle: if both models share each draw, TI is exactly 1 in every replicate.
        rng = random.Random(5)
        recs = []
        for p in ("l14", "l16"):
            for b in range(8):
                ts, gs = 100 + 10 * b, 120
                t, g, h = rng.randint(1, 30), rng.randint(1, 20), rng.randint(0, 5)
                for m in ("haiku", "opus"):
                    recs.append(rec(p, f"{p}-{b}", m, ts, t, gs, g, fires=40, missed=h))
        r = fx.fairness_indices(recs, B=300)
        self.assertAlmostEqual(r["TI"]["point"], 1.0)
        self.assertAlmostEqual(r["TI"]["ci90"][0], 1.0, places=12)
        self.assertAlmostEqual(r["TI"]["ci90"][1], 1.0, places=12)
        self.assertNotAlmostEqual(r["RR"]["haiku"]["ci90"][0], r["RR"]["haiku"]["ci90"][1])

    def test_deterministic_with_the_seed(self):
        recs = generate({"haiku": (0.05, 0.12, 0.05), "opus": (0.04, 0.05, 0.04), "sonnet": (0.04, 0.05, 0.04)}, seed=9)
        a = fx.fairness_indices(recs, B=300)
        b = fx.fairness_indices(list(reversed(recs)), B=300)
        self.assertEqual(a, b)
        c = fx.fairness_indices(recs, B=300, seed=fx.SEED + 1)
        self.assertNotEqual(a["TI"]["ci90"], c["TI"]["ci90"])
        self.assertEqual(a["TI"]["point"], c["TI"]["point"])
        self.assertEqual(a["rng_seed"], fx.derive_seed(fx.SEED, "fairness"))

    def test_dropped_replicates_are_counted_and_correction_share_reported(self):
        # One preset; Haiku's T slips sit on one base puzzle out of four, so some replicates have none (corrected), and Opus's G slips
        # likewise. Every replicate keeps steps in both groups, so none is dropped; the correction share is high, so the label is unstable.
        recs = []
        for i in range(4):
            recs.append(rec("p", f"b{i}", "haiku", 100, 6 if i == 0 else 0, 100, 3))
            recs.append(rec("p", f"b{i}", "opus", 100, 2, 100, 4 if i == 1 else 0))
        r = fx.fairness_indices(recs, B=400)
        self.assertEqual(r["TI"]["dropped"], 0)
        self.assertGreater(r["TI"]["correction_share"], 0.10)
        self.assertTrue(r["TI"]["unstable"])
        # A base puzzle with no G steps: replicates drawing only it have no stratum with both groups and are dropped.
        recs = [rec("p", "b0", "haiku", 100, 5, 0, 0), rec("p", "b0", "opus", 100, 5, 0, 0),
                rec("p", "b1", "haiku", 100, 5, 100, 1), rec("p", "b1", "opus", 100, 5, 100, 5)]
        r = fx.fairness_indices(recs, B=400)
        self.assertGreater(r["TI"]["dropped"], 0)
        self.assertEqual(r["TI"]["dropped"] + r["TI"]["kept"], 400)


class EnoughData(unittest.TestCase):
    def build(self, opus_t, opus_g, sonnet_t, sonnet_g, haiku_t=4, haiku_g=1, opus_missed=0, sonnet_missed=0, haiku_missed=4):
        """2 presets x 3 bases, 50 T and 50 G steps per base (300 per group per model); the house rule should fire on 20 steps per base
        (120 per model). Opus and Sonnet slips spread one per base from the first."""
        recs = []
        bases = [(p, f"{p}-{i}") for p in ("l14", "l15") for i in range(3)]
        for j, (p, b) in enumerate(bases):
            recs.append(rec(p, b, "haiku", 50, haiku_t, 50, haiku_g, missed=haiku_missed, misap=1))
            recs.append(rec(p, b, "opus", 50, int(j < opus_t), 50, int(j < opus_g), missed=int(j < opus_missed)))
            recs.append(rec(p, b, "sonnet", 50, int(j < sonnet_t), 50, int(j < sonnet_g), missed=int(j < sonnet_missed)))
        return recs

    def test_ti_house_minima(self):
        # Haiku: 24 missed and 6 G slips. Opus: 3 missed (enough for TI_house: at least 3) and 7 G slips (10 in all) -> assessable.
        recs = [rec(x.preset, x.base_id, "opus", 50, 1, 50, 2, missed=1) if (x.model, x.base_id) == ("opus", "l14-0") else x
                for x in self.build(5, 6, 0, 0, opus_missed=3)]
        r = fx.fairness_indices(recs, B=100)
        self.assertEqual(r["TI_house"]["assess_counts"]["opus"], {"exposed_slips": 3, "exposed_steps": 120, "G_slips": 7, "G_steps": 300})
        self.assertTrue(r["TI_house"]["assessable"], r["TI_house"]["assess_reason"])
        self.assertEqual(r["comparison"]["TI_house"], "opus")
        # The same with 6 G slips: 9 in all, short of the 10 total; Sonnet adds nothing, so pooled and still short.
        r = fx.fairness_indices(self.build(5, 6, 0, 0, opus_missed=3), B=100)
        self.assertFalse(r["TI_house"]["assessable"])
        self.assertIn("9 slips < 10", r["TI_house"]["assess_reason"])
        # 2 missed for Opus: short; pooled with Sonnet's 2 -> 4 missed and 10 G slips: assessable as opus+sonnet.
        r = fx.fairness_indices(self.build(5, 5, 5, 5, opus_missed=2, sonnet_missed=2), B=100)
        self.assertEqual(r["comparison"]["TI_house"], "opus+sonnet")
        self.assertTrue(r["TI_house"]["assessable"])
        # Haiku with 4 missed slips (needs 5) and 18 G slips: TI_house not assessable; TI still is.
        recs = self.build(5, 5, 0, 0, opus_missed=3, haiku_g=3, haiku_missed=0)
        recs = [rec(x.preset, x.base_id, "haiku", 50, 4, 50, 3, missed=4) if (x.model, x.base_id) == ("haiku", "l14-0") else x
                for x in recs]
        r = fx.fairness_indices(recs, B=100)
        self.assertFalse(r["TI_house"]["assessable"])
        self.assertIn("haiku short (4 exposed slips < 5", r["TI_house"]["assess_reason"])
        self.assertTrue(r["TI"]["assessable"])

    def test_opus_short_pools_with_sonnet(self):
        r = fx.fairness_indices(self.build(3, 3, 3, 3), B=200)
        self.assertTrue(r["pooled"]["TI"])
        self.assertEqual(r["comparison"]["TI"], "opus+sonnet")
        self.assertEqual(r["TI"]["comparison"], "opus+sonnet")
        self.assertTrue(r["TI"]["assessable"])
        self.assertIn("opus+sonnet", r["RR"])
        self.assertEqual(r["counts"]["opus+sonnet"]["T_slips"], 6)
        self.assertAlmostEqual(r["TI"]["point"], r["RR"]["haiku"]["point"] / r["RR"]["opus+sonnet"]["point"])

    def test_opus_enough_is_not_pooled(self):
        r = fx.fairness_indices(self.build(5, 5, 0, 0), B=200)
        self.assertFalse(r["pooled"]["TI"])
        self.assertEqual(r["comparison"]["TI"], "opus")
        self.assertTrue(r["TI"]["assessable"])

    def test_pooled_still_short_is_not_assessable(self):
        r = fx.fairness_indices(self.build(2, 2, 2, 2), B=200)
        self.assertTrue(r["pooled"]["TI"])
        self.assertFalse(r["TI"]["assessable"])
        self.assertFalse(r["TI"]["fires"])
        self.assertTrue(r["TI"]["assess_reason"].startswith(fx.NOT_ASSESSABLE + ": "))
        self.assertIn("opus+sonnet short", r["TI"]["assess_reason"])
        self.assertIsNotNone(r["TI"]["point"])  # the value is still reported

    def test_haiku_short_is_not_assessable_and_both_indices_give_the_result(self):
        r = fx.fairness_indices(self.build(5, 5, 5, 5, haiku_t=1, haiku_g=1), B=200)
        self.assertFalse(r["TI"]["assessable"])
        self.assertIn("haiku short", r["TI"]["assess_reason"])
        # The house index here: Opus has no house slips at all, so it is short too.
        self.assertFalse(r["TI_house"]["assessable"])
        self.assertFalse(r["flag_k"]["fires"])
        self.assertTrue(r["flag_k"]["reason"].startswith(fx.NOT_ASSESSABLE + ": "))

    def test_comparison_step_floor(self):
        # Opus has 6 T and 6 G slips but only 60 steps per group: short on steps; Sonnet adds none of the steps it lacks either.
        recs = []
        for i in range(6):
            recs.append(rec("p", f"b{i}", "haiku", 50, 4, 50, 1))
            recs.append(rec("p", f"b{i}", "opus", 10, 1, 10, 1))
        r = fx.fairness_indices(recs, B=50, comparison="opus")
        self.assertFalse(r["TI"]["assessable"])
        self.assertIn("exposed steps < 100", r["TI"]["assess_reason"])

    def test_one_index_not_assessable_and_the_other_quiet(self):
        r = fx.fairness_indices(self.build(5, 5, 5, 5, haiku_t=1, haiku_g=3), B=200)
        # TI: Haiku 6 T + 18 G = 24 slips, 6 >= 5 in T -> assessable and quiet; TI_house: Opus has no house slips -> short.
        self.assertTrue(r["TI"]["assessable"])
        self.assertFalse(r["TI_house"]["assessable"])
        self.assertTrue(r["flag_k"]["reason"].startswith("does not fire (TI_house " + fx.NOT_ASSESSABLE))


class Records(unittest.TestCase):
    def test_dict_records_and_house_slips_check(self):
        d = dict(preset="p", base_id="b", model="haiku", T_steps=10, T_slips=1, G_steps=10, G_slips=1, house_steps_checked=20,
                 house_should_fire=5, house_missed=1, house_should_not_fire=15, house_misapplied=1)
        self.assertEqual(fx._as_record(d).vector(), (10, 1, 10, 1, 20, 5, 1, 15, 1))
        for bad in (dict(d, T_slips=11), dict(d, house_missed=6), dict(d, house_misapplied=16), dict(d, house_should_not_fire=14),
                    dict(d, T_steps=True)):
            with self.assertRaises(ValueError):
                fx._as_record(bad)
        earlier = {k: v for k, v in d.items() if k not in ("house_should_fire", "house_should_not_fire")}
        with self.assertRaises(ValueError):  # the earlier format (house_fires) is refused, not silently read
            fx._as_record(dict(earlier, house_fires=5))

    def test_duplicates_raise(self):
        r = rec("p", "b", "haiku", 10, 1, 10, 1)
        with self.assertRaises(ValueError):
            fx.fairness_indices([r, r, rec("p", "b", "opus", 10, 1, 10, 1)], B=10)


class FlagR(unittest.TestCase):
    def test_exactly_twice_fires(self):
        self.assertTrue(fx.flag_r(20, 100, 10, 100)["fires"])
        self.assertTrue(fx.flag_r(4, 10, 2, 10)["fires"])
        self.assertTrue(fx.flag_r(2, 10, 3, 30)["fires"])  # 0.2 vs 0.1: exactly 2x across different pair counts

    def test_just_below_twice_does_not_fire(self):
        self.assertFalse(fx.flag_r(19, 100, 10, 100)["fires"])

    def test_nine_pairs_is_not_assessable(self):
        for args in ((9, 9, 0, 10), (5, 10, 0, 9)):
            res = fx.flag_r(*args)
            self.assertFalse(res["fires"])
            self.assertTrue(res["reason"].startswith("not assessable"))

    def test_ten_pairs_each_is_assessed(self):
        self.assertTrue(fx.flag_r(5, 10, 0, 10)["fires"])

    def test_zero_agreement_everywhere_does_not_fire(self):
        self.assertFalse(fx.flag_r(0, 10, 0, 10)["fires"])

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fx.flag_r(11, 10, 0, 10)
        with self.assertRaises(ValueError):
            fx.flag_r(-1, 10, 0, 10)


if __name__ == "__main__":
    unittest.main()
