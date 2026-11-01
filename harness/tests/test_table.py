import csv
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import mkdtemp

from harness.pareto.client import Client
from harness.pareto.table import COLUMNS, block_rates, write_compact_table
from harness.pareto.transport import FakeTransport, TransportError
from harness.tests.fakes import guard, params, reply, tmplog


class CompactTable(unittest.TestCase):
    def test_rows_total_and_grade(self):
        g, log = guard(), tmplog()
        n = {"i": 0}

        def fake(p):
            n["i"] += 1
            if n["i"] == 2:
                return reply(model=p["model"], stop="refusal", category="bio", text=None)
            return reply(model=p["model"], text="Answer: 1 = 5")
        c = Client(g, FakeTransport(fake), log, sleep=lambda s: None)
        for k in range(3):
            c.call(f"k{k}", params(text=f"q{k}"))
        out = Path(mkdtemp()) / "t.csv"
        total = write_compact_table(log, out, grade=lambda r: r["answer_text"].endswith("5"))
        rows = list(csv.DictReader(open(out)))
        self.assertEqual(list(rows[0].keys()), COLUMNS)
        self.assertEqual([r["kind"] for r in rows], ["answered", "refusal", "answered"])
        self.assertEqual([r["right"] for r in rows], ["1", "", "1"])        # a refusal is never graded
        self.assertEqual(total, g.spent)
        self.assertNotIn("answer_text", rows[0])                              # answers stay in the raw log

    def test_block_rates(self):
        g, log = guard(), tmplog()
        n = {"i": 0}

        def fake(p):
            n["i"] += 1
            if n["i"] % 10 == 0:
                return reply(model=p["model"], stop="refusal", category="reasoning_extraction", text=None)
            return reply(model=p["model"])
        c = Client(g, FakeTransport(fake), log, sleep=lambda s: None)
        for k in range(20):
            c.call(f"b{k}", params(text=f"q{k}"))
        r = block_rates(log)["claude-haiku-5-5"]
        self.assertEqual((r["calls"], r["blocked"], r["over_2_percent"]), (20, 2, True))
        self.assertEqual(r["categories"], {"reasoning_extraction": 2})

    def test_failed_attempts_not_in_table(self):
        g, log = guard(), tmplog()
        calls = []

        def fake(p):
            calls.append(1)
            if len(calls) == 1:
                raise TransportError("rate_limit", "x", billed="no", retryable=True, status=429)
            return reply(model=p["model"])
        Client(g, FakeTransport(fake), log, sleep=lambda s: None).call("z", params())
        out = Path(mkdtemp()) / "t.csv"
        write_compact_table(log, out)
        self.assertEqual(len(list(csv.DictReader(open(out)))), 1)


if __name__ == "__main__":
    unittest.main()
