import itertools
import random
import unittest
from collections import Counter
from fractions import Fraction
from unittest import mock

from harness.analysis import votes
from harness.analysis.votes import interpolated_vote_accuracy, vote_accuracy_at_k, vote_curve


def brute(answers, correct, k, tie="random"):
    """Independent reference: every k-subset by index, credit of each, averaged."""
    total, n = 0.0, 0
    for idx in itertools.combinations(range(len(answers)), k):
        counts = Counter(answers[i] for i in idx if answers[i] is not None)
        n += 1
        if not counts:
            continue
        top = max(counts.values())
        tied = [a for a, c in counts.items() if c == top]
        if correct in tied:
            total += 1.0 / len(tied) if len(tied) == 1 or tie == "random" else 0.0
    return total / n


class HandComputed(unittest.TestCase):
    A = ["a", "a", "b", "b", "c"]          # correct = "a"

    def test_five_samples_with_ties(self):
        self.assertAlmostEqual(vote_accuracy_at_k(self.A, "a", 1)["acc"], 2 / 5)
        r3 = vote_accuracy_at_k(self.A, "a", 3)
        self.assertAlmostEqual(r3["acc"], 13 / 30)                       # (2 + 1 + 4 * 1/3) / 10
        self.assertAlmostEqual(vote_accuracy_at_k(self.A, "a", 3, tie="wrong")["acc"], 3 / 10)
        self.assertAlmostEqual(r3["tie_decided_share"], 4 / 10)          # {a, b, c}: 4 of the 10 subsets
        r5 = vote_accuracy_at_k(self.A, "a", 5)
        self.assertEqual((r5["acc"], r5["method"], r5["mc_se"], r5["n_subsets"]), (0.5, "exact", 0.0, 1))
        self.assertEqual(vote_accuracy_at_k(self.A, "a", 5, tie="wrong")["acc"], 0.0)
        self.assertEqual(r5["tie_decided_share"], 1.0)

    def test_none_is_a_vote_for_nothing(self):
        a = ["a", "a", "b", None, None]
        self.assertAlmostEqual(vote_accuracy_at_k(a, "a", 1)["acc"], 2 / 5)
        self.assertAlmostEqual(vote_accuracy_at_k(a, "a", 3)["acc"], 7 / 10)
        self.assertAlmostEqual(vote_accuracy_at_k(a, "a", 3, tie="wrong")["acc"], 5 / 10)
        self.assertEqual(vote_accuracy_at_k(a, "a", 5)["acc"], 1.0)
        self.assertEqual(vote_accuracy_at_k([None] * 5, "a", 3)["acc"], 0.0)
        self.assertEqual(vote_accuracy_at_k(["b"] * 5, "a", 3)["acc"], 0.0)   # the right answer never appears

    def test_a_tie_without_the_right_answer_is_not_counted_as_decided(self):
        a = ["b", "b", "c", "c", "a"]
        r = vote_accuracy_at_k(a, "a", 4, mode="exact")
        self.assertGreater(r["tie_any_share"], r["tie_decided_share"])


class AgainstBruteForce(unittest.TestCase):
    CASES = [
        (["a", "a", "b", "b", "c", None], "a"),
        (["x", "y", "z", "w", "v", "u", "t"], "x"),
        (["a"] * 4 + ["b"] * 3 + [None] * 2 + ["c"], "b"),
        ([None, None, "a", None], "a"),
        (["a", "b"], "b"),
    ]

    def test_exact_equals_enumeration(self):
        for answers, correct in self.CASES:
            for k in range(1, len(answers) + 1):
                for tie in ("random", "wrong"):
                    got = vote_accuracy_at_k(answers, correct, k, tie=tie)
                    self.assertEqual(got["method"], "exact")
                    self.assertAlmostEqual(got["acc"], brute(answers, correct, k, tie), places=12,
                                           msg=(answers, correct, k, tie))

    def test_exact_on_random_cases(self):
        rng = random.Random(5)
        for _ in range(40):
            n = rng.randint(2, 9)
            answers = [rng.choice(["a", "b", "c", "d", None]) for _ in range(n)]
            k = rng.randint(1, n)
            self.assertAlmostEqual(vote_accuracy_at_k(answers, "a", k)["acc"], brute(answers, "a", k), places=12)

    def test_sampled_is_within_three_standard_errors_of_exact(self):
        answers = ["a", "a", "a", "b", "b", "c", "c", "d", None, None]
        for k in (1, 3, 4, 7):
            exact = vote_accuracy_at_k(answers, "a", k)
            s = vote_accuracy_at_k(answers, "a", k, mode="sampled", ndraws=4000)
            self.assertEqual((s["method"], s["ndraws"]), ("sampled", 4000))
            self.assertGreater(s["mc_se"], 0.0)
            self.assertLessEqual(abs(s["acc"] - exact["acc"]), 3 * s["mc_se"] + 1e-12, (k, s, exact))
            self.assertAlmostEqual(s["tie_decided_share"], exact["tie_decided_share"], delta=0.05)

    def test_up_to_40_distinct_answers_are_still_counted_exactly(self):
        answers = ["a"] * 4 + [str(i) for i in range(36)]
        r = vote_accuracy_at_k(answers, "a", 5)
        self.assertEqual((r["method"], r["ndraws"], r["mc_se"]), ("exact", 0, 0.0))
        s = vote_accuracy_at_k(answers, "a", 5, mode="sampled", ndraws=4000)
        self.assertLessEqual(abs(s["acc"] - r["acc"]), 3 * s["mc_se"] + 1e-12)

    def test_beyond_the_exact_limit_falls_back_to_sampling(self):
        answers = ["a"] * 4 + [str(i) for i in range(70)]
        r = vote_accuracy_at_k(answers, "a", 5)
        self.assertEqual(r["method"], "sampled")
        self.assertGreaterEqual(r["ndraws"], 1000)
        e = vote_accuracy_at_k(answers, "a", 5, mode="exact")
        self.assertLessEqual(abs(r["acc"] - e["acc"]), 3 * r["mc_se"] + 1e-12)


class Behaviour(unittest.TestCase):
    def test_k_equals_n_is_one_subset(self):
        a = ["a", "a", "b", "c", None, "a"]
        r = vote_accuracy_at_k(a, "a", len(a), mode="sampled")
        self.assertEqual((r["acc"], r["method"], r["n_subsets"], r["mc_se"]), (1.0, "exact", 1, 0.0))

    def test_determinism_with_the_seed(self):
        a = ["a", "a", "b", "b", "c", "c", None, "d"]
        r1 = vote_accuracy_at_k(a, "a", 3, mode="sampled", seed=7)
        r2 = vote_accuracy_at_k(a, "a", 3, mode="sampled", seed=7)
        r3 = vote_accuracy_at_k(a, "a", 3, mode="sampled", seed=8)
        self.assertEqual(r1, r2)
        self.assertNotEqual(r1["acc"], r3["acc"])

    def test_bad_input(self):
        a = ["a", "b"]
        for bad in (dict(k=0), dict(k=3), dict(k=1, tie="coin"), dict(k=1, mode="x")):
            with self.assertRaises(ValueError):
                vote_accuracy_at_k(a, "a", **bad)
        with self.assertRaises(ValueError):
            vote_accuracy_at_k(a, None, 1)
        with self.assertRaises(ValueError):
            vote_accuracy_at_k(["a", "b", "c"], "a", 2, mode="sampled", ndraws=999)


class Curve(unittest.TestCase):
    def test_curve_length_and_values(self):
        a = ["a", "a", "b", "b", "c"]
        c = vote_curve(a, "a", kmax=40)
        self.assertEqual(len(c), 5)
        self.assertAlmostEqual(c[0], 0.4)
        self.assertAlmostEqual(c[2], 13 / 30)
        self.assertAlmostEqual(c[4], 0.5)
        self.assertEqual(len(vote_curve(a, "a", kmax=3)), 3)
        d = vote_curve(a, "a", kmax=2, detail=True)
        self.assertEqual([x["k"] for x in d], [1, 2])


class InterpolatedVote(unittest.TestCase):
    A = ["a", "a", "a", "b", "b", "c"]            # six samples of one base puzzle; the right answer is "a"

    def calls(self, *args, **kw):
        """Run interpolated_vote_accuracy and list the k of every vote@k it evaluated."""
        seen = []
        real = votes.vote_accuracy_at_k

        def spy(answers, correct, k, **kwargs):
            seen.append(k)
            return real(answers, correct, k, **kwargs)
        with mock.patch.object(votes, "vote_accuracy_at_k", side_effect=spy):
            r = interpolated_vote_accuracy(*args, **kw)
        return r, seen

    def test_known_answer_fractional_kstar(self):
        v2, v3 = brute(self.A, "a", 2), brute(self.A, "a", 3)
        self.assertNotAlmostEqual(v2, v3)                                   # a real interpolation, not two equal ends
        r, seen = self.calls(self.A, "a", Fraction(12, 5))                  # k* = 2.4: f = 0.4 between k = 2 and k = 3
        self.assertAlmostEqual(r["acc"], 0.6 * v2 + 0.4 * v3, places=12)
        self.assertEqual((r["k_lo"], r["k_hi"]), (2, 3))
        self.assertAlmostEqual(r["weight"], 0.4)
        self.assertEqual(r["weight_exact"], "2/5")
        self.assertEqual(sorted(seen), [2, 3])
        self.assertFalse(r["capped"])

    def test_the_29_4_shape_with_scaled_numbers(self):
        # k* = 29.4 would be 0.6 * vote@29 + 0.4 * vote@30; here 2.4 -> 0.6 * vote@2 + 0.4 * vote@3 (the same f = 0.4)
        for given in (2.4, "2.4", Fraction(12, 5)):
            r = interpolated_vote_accuracy(self.A, "a", given)
            self.assertAlmostEqual(r["acc"], 0.6 * brute(self.A, "a", 2) + 0.4 * brute(self.A, "a", 3), places=12)
        r = interpolated_vote_accuracy([("a" if i % 3 else "b") for i in range(40)], "a", 29.4)
        w = [("a" if i % 3 else "b") for i in range(40)]
        lo, hi = vote_accuracy_at_k(w, "a", 29)["acc"], vote_accuracy_at_k(w, "a", 30)["acc"]
        self.assertAlmostEqual(r["acc"], 0.6 * lo + 0.4 * hi, places=12)
        self.assertEqual((r["k_lo"], r["k_hi"]), (29, 30))
        self.assertEqual(r["weight_exact"], "2/5")                           # 29.4 is held exact, not as 29.39999...

    def test_interpolation_is_in_accuracy_not_in_k(self):
        r = interpolated_vote_accuracy(self.A, "a", Fraction(5, 2))         # halfway
        self.assertAlmostEqual(r["acc"], (brute(self.A, "a", 2) + brute(self.A, "a", 3)) / 2, places=12)

    def test_whole_kstar_is_vote_at_kstar_and_never_touches_the_next_k(self):
        for ks in (3, 3.0, Fraction(3), "3", 3.00):
            r, seen = self.calls(self.A, "a", ks)
            self.assertEqual(seen, [3])                                      # vote@4 is not evaluated
            self.assertEqual(r["acc"], vote_accuracy_at_k(self.A, "a", 3)["acc"])
            self.assertEqual((r["k_lo"], r["k_hi"], r["weight"]), (3, 3, 0.0))
        # even a list too short to hold k* + 1 samples works: a call for k = 4 would raise
        short = ["a", "b", "a"]
        r = interpolated_vote_accuracy(short, "a", 3)
        self.assertEqual(r["acc"], vote_accuracy_at_k(short, "a", 3)["acc"])
        with self.assertRaises(ValueError):
            vote_accuracy_at_k(short, "a", 4)
        self.assertEqual(self.calls(self.A, "a", 1)[1], [1])                  # k* = 1 is vote@1 only

    def test_capped_at_the_samples_drawn_has_no_extrapolation(self):
        r, seen = self.calls(self.A, "a", 9.7)                                # six samples: k* = 9.7 is held to 6
        self.assertEqual(seen, [6])                                          # nothing above 6 is evaluated
        self.assertEqual(r["acc"], vote_accuracy_at_k(self.A, "a", 6)["acc"])
        self.assertTrue(r["capped"])
        self.assertEqual((r["k_lo"], r["k_hi"], r["weight"], r["kstar"]), (6, 6, 0.0, 6.0))
        r, seen = self.calls(self.A, "a", 5.5)                                # below the limit: interpolated between 5 and 6
        self.assertEqual(sorted(seen), [5, 6])
        self.assertFalse(r["capped"])
        r, seen = self.calls(self.A, "a", 6)                                  # exactly the limit: vote@6, not "capped"
        self.assertEqual((seen, r["capped"]), ([6], False))

    def test_capped_at_40_and_at_a_smaller_cap(self):
        w = [("a" if i % 2 else "b") for i in range(60)]
        r, seen = self.calls(w, "a", 55.5)
        self.assertEqual(seen, [40])                                          # the 40 cap, with 60 samples to spare
        self.assertTrue(r["capped"])
        r, seen = self.calls(w, "a", 7.5, cap=5)
        self.assertEqual(seen, [5])                                           # an explicit cap
        r, seen = self.calls(w, "a", 39.5)
        self.assertEqual(sorted(seen), [39, 40])                              # 40 itself may be the upper end

    def test_below_one_is_an_error_and_options_pass_through(self):
        with self.assertRaises(ValueError):
            interpolated_vote_accuracy(self.A, "a", 0.9)
        r = interpolated_vote_accuracy(self.A, "a", 2.4, tie="wrong")
        self.assertAlmostEqual(r["acc"], 0.6 * brute(self.A, "a", 2, "wrong") + 0.4 * brute(self.A, "a", 3, "wrong"), places=12)


if __name__ == "__main__":
    unittest.main()
