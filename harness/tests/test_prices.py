"""Tests for harness/pareto/prices.py. Offline, no API calls.

Run from the repo root:  python3 -m unittest discover -s harness/tests -t .
"""

from __future__ import annotations

import random
import re
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from harness.pareto import prices
from harness.pareto.prices import FABLE, HAIKU, OPUS, SONNET, Rates, Usage, cost, worst_case

D = Decimal
FACTS = Path(__file__).resolve().parents[2] / "research" / "facts-checked.md"

# Hand-copied from research/facts-checked.md, "Notes and quotes / Pricing" (input, output,
# 5-minute write, 1-hour write, cache read), checked 2026-10-10.
EXPECTED = {
    HAIKU: ("0.10", "0.50", "0.125", "0.20", "0.01"),
    SONNET: ("2", "10", "2.50", "4", "0.10"),
    OPUS: ("4", "20", "5", "8", "0.20"),
    FABLE: ("10", "50", "12.50", "20", "0.25"),
}
EXPECTED_HAIKU_LONG = ("0.50", "2.50", "0.625", "1", "0.05")


def as_tuple(r: Rates):
    return (r.input, r.output, r.cache_write_5m, r.cache_write_1h, r.cache_read)


def read_facts_rows():
    """Parse the pricing rows straight out of the facts file."""
    names = {"Opus 5.5": OPUS, "Sonnet 5.5": SONNET, "Haiku 5.5 (≤100,000)": HAIKU,
             "Fable 5.1": FABLE, "Haiku 5.5 (>100,000)": "haiku-long"}
    rows = {}
    for line in FACTS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^- `Claude (.+?) \| (.+)`$", line)
        if m and m.group(1) in names:
            cells = [re.sub(r"/\s*MTok|[$¹²³\s]", "", c) for c in m.group(2).split("|")]
            inp, w5, w1, read, out = (D(c) for c in cells)
            rows[names[m.group(1)]] = (inp, out, w5, w1, read)
    return rows


class PriceTableTest(unittest.TestCase):
    def test_date_pinned(self):
        self.assertEqual(prices.PRICE_TABLE_DATE, "2026-10-12")

    def test_every_price_matches_expected_and_is_decimal(self):
        self.assertEqual(set(prices.PRICES), set(EXPECTED))
        for model, row in EXPECTED.items():
            got = as_tuple(prices.PRICES[model])
            for value in got:
                self.assertIsInstance(value, Decimal)
            self.assertEqual(got, tuple(D(x) for x in row), model)
        self.assertEqual(as_tuple(prices.LONG_PROMPT_PRICES[HAIKU]), tuple(D(x) for x in EXPECTED_HAIKU_LONG))
        self.assertEqual(set(prices.LONG_PROMPT_PRICES), {HAIKU}, "only Haiku has a long-prompt tier")

    @unittest.skipUnless(FACTS.is_file(), "research/facts-checked.md is not in the released package")
    def test_every_price_matches_the_facts_file(self):
        rows = read_facts_rows()
        self.assertEqual(len(rows), 5, "expected five pricing rows in research/facts-checked.md")
        for model in EXPECTED:
            self.assertEqual(as_tuple(prices.PRICES[model]), rows[model], model)
        self.assertEqual(as_tuple(prices.LONG_PROMPT_PRICES[HAIKU]), rows["haiku-long"])

    def test_cache_writes_are_1_25x_and_2x_input(self):
        for table in (prices.PRICES, prices.LONG_PROMPT_PRICES):
            for model, r in table.items():
                self.assertEqual(r.cache_write_5m, r.input * D("1.25"), model)
                self.assertEqual(r.cache_write_1h, r.input * 2, model)


class CostTest(unittest.TestCase):
    def test_hand_worked_opus(self):
        # 1,000 x $4/M + 2,000 x $20/M = 0.004 + 0.04
        self.assertEqual(cost(OPUS, Usage(input_tokens=1000, output_tokens=2000)), D("0.044"))

    def test_hand_worked_every_model_one_million_each_way(self):
        for model, (inp, out, _, _, _) in EXPECTED.items():
            if model == HAIKU:  # a 1M-token prompt is over 100,000: Haiku's long row
                inp, out = EXPECTED_HAIKU_LONG[0], EXPECTED_HAIKU_LONG[1]
            got = cost(model, Usage(input_tokens=1000000, output_tokens=1000000))
            self.assertEqual(got, D(inp) + D(out), model)

    def test_haiku_exactly_100000_is_base_row(self):
        u = Usage(input_tokens=100000, output_tokens=10000)
        # 100,000 x 0.10/M + 10,000 x 0.50/M = 0.01 + 0.005
        self.assertEqual(cost(HAIKU, u), D("0.015"))

    def test_haiku_100001_bills_whole_request_at_long_row(self):
        u = Usage(input_tokens=100001, output_tokens=10000)
        # 100,001 x 0.50/M + 10,000 x 2.50/M (output at the higher row too)
        self.assertEqual(cost(HAIKU, u), D("0.0500005") + D("0.025"))

    def test_haiku_threshold_counts_cache_reads_and_writes(self):
        u = Usage(input_tokens=50000, cache_read_tokens=50000, cache_write_5m_tokens=1, output_tokens=1000)
        self.assertEqual(u.prompt_tokens, 100001)
        expected = (50000 * D("0.50") + 50000 * D("0.05") + 1 * D("0.625") + 1000 * D("2.50")) / 1000000
        self.assertEqual(cost(HAIKU, u), expected)
        u2 = Usage(input_tokens=50000, cache_write_1h_tokens=50000)  # exactly 100,000: base row
        self.assertEqual(cost(HAIKU, u2), (50000 * D("0.10") + 50000 * D("0.20")) / 1000000)

    def test_no_long_tier_for_other_models(self):
        for model, (inp, _, _, _, _) in EXPECTED.items():
            if model != HAIKU:
                self.assertEqual(cost(model, Usage(input_tokens=500000)), D(inp) / 2, model)

    def test_cache_math(self):
        self.assertEqual(cost(SONNET, Usage(cache_read_tokens=1000000)), D("0.10"))
        self.assertEqual(cost(SONNET, Usage(cache_write_5m_tokens=1000000)), D("2.50"))
        self.assertEqual(cost(SONNET, Usage(cache_write_1h_tokens=1000000)), D("4"))
        self.assertEqual(cost(FABLE, Usage(cache_read_tokens=1000000)), D("0.25"))
        self.assertEqual(cost(OPUS, Usage(input_tokens=10, cache_read_tokens=1000, cache_write_5m_tokens=100,
                                          cache_write_1h_tokens=50, output_tokens=7)),
                         (10 * D(4) + 1000 * D("0.20") + 100 * D(5) + 50 * D(8) + 7 * D(20)) / 1000000)

    def test_batch_halves_and_stacks_with_cache(self):
        self.assertEqual(cost(OPUS, Usage(input_tokens=1000000, output_tokens=1000000), batch=True), D("12"))
        self.assertEqual(cost(SONNET, Usage(cache_read_tokens=1000000), batch=True), D("0.05"))
        self.assertEqual(cost(HAIKU, Usage(input_tokens=1000000, output_tokens=1000000), batch=True),
                         D("1.50"))  # long row: (0.50 + 2.50) / 2
        rng = random.Random(1)
        for _ in range(500):
            u = random_usage(rng, 200000, 64000)
            for model in EXPECTED:
                self.assertEqual(cost(model, u, batch=True) * 2, cost(model, u))

    def test_unknown_model_raises(self):
        with self.assertRaises(KeyError):
            cost("claude-opus-5", Usage(input_tokens=1))
        with self.assertRaises(KeyError):
            worst_case("claude-haiku-5", 100, 100)
        with self.assertRaises(KeyError):
            worst_case("claude-haiku-5", 95000, 100)  # unknown model above the Haiku safety line too

    def test_bad_inputs_raise(self):
        for bad in (-1, 1.5, True, "3"):
            with self.assertRaises(ValueError):
                Usage(output_tokens=bad)
            with self.assertRaises(ValueError):
                worst_case(OPUS, bad, 100)
        with self.assertRaises(ValueError):
            worst_case(OPUS, 100, 0)
        with self.assertRaises(TypeError):
            cost(OPUS, Usage(), batch="False")  # a truthy string must not halve the cost
        with self.assertRaises(TypeError):
            cost(OPUS, {"input_tokens": 1})

    def test_result_is_exact_decimal(self):
        got = cost(HAIKU, Usage(input_tokens=1), batch=True)
        self.assertIsInstance(got, Decimal)
        self.assertEqual(got, D("0.00000005"))


def random_usage(rng, max_prompt, max_output):
    """Random usage with prompt tokens <= max_prompt and output <= max_output."""
    cuts = sorted(rng.randint(0, max_prompt) for _ in range(4))
    parts = [cuts[0], cuts[1] - cuts[0], cuts[2] - cuts[1], cuts[3] - cuts[2]]
    rng.shuffle(parts)
    return Usage(input_tokens=parts[0], cache_read_tokens=parts[1], cache_write_5m_tokens=parts[2],
                 cache_write_1h_tokens=parts[3], output_tokens=rng.randint(0, max_output))


class WorstCaseTest(unittest.TestCase):
    def test_hand_worked_opus(self):
        # input at the 1-hour cache-write rate ($8) + 64,000 x $20/M
        self.assertEqual(worst_case(OPUS, 1000, 64000), D("0.008") + D("1.28"))
        self.assertEqual(worst_case(OPUS, 1000, 64000, batch=True), (D("0.008") + D("1.28")) / 2)

    def test_haiku_safety_band(self):
        self.assertEqual(worst_case(HAIKU, 90000, 1000), (90000 * D("0.20") + 1000 * D("0.50")) / 1000000)
        self.assertEqual(worst_case(HAIKU, 90001, 1000), (90001 * D("1") + 1000 * D("2.50")) / 1000000)

    def test_worst_case_bounds_cost_for_random_usages(self):
        rng = random.Random(20261010)
        for _ in range(3000):
            model = rng.choice(list(EXPECTED))
            est = rng.choice([rng.randint(0, 5000), rng.randint(80000, 120000), rng.randint(0, 400000)])
            max_tokens = rng.randint(1, 128000)
            u = random_usage(rng, est, max_tokens)
            batch = rng.random() < 0.5
            ceiling = worst_case(model, est, max_tokens)  # list price, as the guard reserves
            self.assertLessEqual(cost(model, u, batch), ceiling, (model, est, max_tokens, u, batch))
            self.assertLessEqual(cost(model, u, True), worst_case(model, est, max_tokens, batch=True))

    def test_estimate_input_tokens(self):
        self.assertEqual(prices.estimate_input_tokens(""), 100)
        self.assertEqual(prices.estimate_input_tokens("7" * 1000), 600)
        self.assertEqual(prices.estimate_input_tokens("é" * 10), 110)  # 20 UTF-8 bytes
        with self.assertRaises(TypeError):
            prices.estimate_input_tokens(b"abc")


class MutationTest(unittest.TestCase):
    """Break prices.py on purpose and check that a test above fails. Shows the tests bite."""

    def assert_caught(self, patcher, test_case, name):
        with patcher:
            with self.assertRaises(Exception, msg=f"mutant not caught by {name}"):
                getattr(test_case(name), name)()

    def test_float_prices_are_caught(self):
        floats = Rates(4.0, 20.0, 5.0, 8.0, 0.2)
        patcher = mock.patch.dict(prices.PRICES, {OPUS: floats})
        self.assert_caught(patcher, PriceTableTest, "test_every_price_matches_expected_and_is_decimal")
        self.assert_caught(mock.patch.dict(prices.PRICES, {OPUS: floats}), CostTest, "test_hand_worked_opus")

    def test_dropping_the_long_tier_is_caught(self):
        patcher = mock.patch.object(prices, "LONG_PROMPT_PRICES", {})
        self.assert_caught(patcher, CostTest, "test_haiku_100001_bills_whole_request_at_long_row")

    def test_threshold_off_by_one_is_caught(self):
        patcher = mock.patch.object(prices, "LONG_PROMPT_THRESHOLD", 99999)
        self.assert_caught(patcher, CostTest, "test_haiku_exactly_100000_is_base_row")

    def test_dropping_the_safety_band_is_caught(self):
        patcher = mock.patch.object(prices, "HAIKU_SAFETY_THRESHOLD", 100000)
        self.assert_caught(patcher, WorstCaseTest, "test_haiku_safety_band")

    @unittest.skipUnless(FACTS.is_file(), "research/facts-checked.md is not in the released package")
    def test_a_wrong_price_is_caught(self):
        patcher = mock.patch.dict(prices.PRICES, {SONNET: Rates(D(2), D(10), D("2.50"), D(4), D("0.20"))})
        self.assert_caught(patcher, PriceTableTest, "test_every_price_matches_the_facts_file")


if __name__ == "__main__":
    unittest.main()
