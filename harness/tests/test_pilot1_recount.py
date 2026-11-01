"""Tests for harness/analysis/pilot1_recount.py on synthetic graded rows (no reply text, no run folder): the per-shape counts, the
pooled mean over base puzzles, the format flag at D-76 (3)'s 5%, and the shift between the two marking rules."""

import unittest

from harness.analysis import pilot1_recount as pr


def _row(base, shape, d2_right, d2_fmt, orig_right=None, orig_fmt=None, kind="answered"):
    d2 = {"right": d2_right, "format": d2_fmt}
    orig = {"right": d2_right if orig_right is None else orig_right, "format": d2_fmt if orig_fmt is None else orig_fmt}
    return {"set": "s", "base": base, "shape": shape, "kind": kind, "d2": d2, "original": orig}


class Summary(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for b in range(10):
            self.rows.append(_row(b, "24x1", True, "ok"))
            self.rows.append(_row(b, "1x24", True, "ok"))
        self.rows[1] = _row(0, "1x24", True, "ok", orig_right=False, orig_fmt="extra_line")   # an identical repeat, read once under D2
        self.rows[3] = _row(1, "1x24", False, "extra_line")                                  # fails under both rules
        self.rows[4] = _row(2, "24x1", False, "missing_line", kind="max_tokens")            # not answered: left out of compliance

    def test_counts_pool_and_flag(self):
        res = pr.summarise(self.rows)
        o, d = res["original"], res["d2"]
        self.assertEqual((o["by_shape"]["1x24"]["right"], d["by_shape"]["1x24"]["right"]), (8, 9))
        self.assertEqual((o["by_shape"]["1x24"]["format_ok"], d["by_shape"]["1x24"]["format_ok"]), (8, 9))
        self.assertEqual(d["by_shape"]["24x1"]["answered"], 9)
        self.assertAlmostEqual(o["pooled_mean"], (8 + 9) / 20)
        self.assertAlmostEqual(d["pooled_mean"], (9 + 9) / 20)
        self.assertEqual(o["flag_above_5pct_non_compliance"]["1x24"], True)                 # 2 of 10 not ok: 20%
        self.assertEqual(d["flag_above_5pct_non_compliance"]["1x24"], True)                 # 1 of 10: 10%
        self.assertEqual(d["flag_above_5pct_non_compliance"]["24x1"], False)

    def test_shift(self):
        s = pr.summarise(self.rows)["shift"]
        self.assertEqual((s["chain_tries_right_only_under_d2"], s["chain_tries_right_only_under_original"], s["pieces_changed"]), (1, 0, 0))
        self.assertEqual((s["their_original_format_statuses"], s["their_d2_format_statuses"]), ({"extra_line": 1}, {"ok": 1}))
        self.assertEqual(s["chain_format_ok_only_under_d2"], 1)

    def test_flag_threshold_is_d76(self):
        self.assertEqual(pr.FLAG, 0.05)


if __name__ == "__main__":
    unittest.main()
