"""Tests for harness/analysis/free_analyses.py that need no run folder: the recomputation checks, the write-once rule, the plan's
definitions, analysis 4 on the committed stamped files, and the E-20 occupancy rule on synthetic scores. The analyses that read the run
folders (1-3, 5-8, 10) run once on the real data; their `checks` recompute stamped numbers and refuse a disagreement."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness.analysis import free_analyses as fa

REPO = Path(__file__).resolve().parents[2]


def _git_ok() -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", "7b43f91"], check=True, capture_output=True)
        return True
    except Exception:
        return False


class ChecksAndWriting(unittest.TestCase):
    def test_checks_refuse_a_difference(self):
        c = fa.Checks()
        c.eq("same", 1.0, 1.0)
        c.eq("list", [1, 2], [1, 2])
        with self.assertRaises(ValueError):
            c.eq("differs", 1.0, 1.0001)
        self.assertEqual([x["equal"] for x in c.items], [True, True, False])

    @unittest.skipUnless(_git_ok(), "the repo's history is not available")
    def test_write_once_and_definition(self):
        with tempfile.TemporaryDirectory() as d:
            c = fa.Checks()
            h = fa.write_once(Path(d), "fa99", 7, {"x": 1}, {"in": "puts"}, c)
            doc = json.loads((Path(d) / "fa99.json").read_text())
            self.assertEqual(doc["definition"]["rank"], 7)
            self.assertIn("post hoc", doc["label"])
            self.assertEqual(doc["code"]["fa_seed"], fa.FA_SEED)
            self.assertEqual(len(h), 64)
            with self.assertRaises(SystemExit):
                fa.write_once(Path(d), "fa99", 7, {"x": 2}, {}, c)

    def test_undefined_written_as_null(self):
        clean, found = fa.undefined_to_null({"a": {"share": float("nan"), "pairs": 0}, "b": [1.0, float("nan")]})
        self.assertEqual(clean, {"a": {"share": None, "pairs": 0}, "b": [1.0, None]})
        self.assertEqual(found, ["a.share", "b.1"])

    def test_band_resamples_bases(self):
        b = fa.band({"a": 0.0, "b": 100.0, "c": 100.0, "d": 0.0, "e": 100.0}, "fa:test-band")
        self.assertEqual(b["mean"], 60.0)
        self.assertLess(b["ci95"][0], b["ci95"][1])                                       # a real interval, not the collapsed one
        self.assertEqual(fa.band({"a": 100.0, "b": 100.0}, "fa:x")["ci95"], [100.0, 100.0])  # all right: collapses, as it should

    def test_interval_sanity(self):
        res = fa.interval_sanity({"a": {"d": 1.0, "ci95": [0.5, 2.0]}, "b": {"mean": 3.0, "ci95": [3.0, 3.0]},
                                  "c": [{"rho_star": 9.0, "ci95": [1.0, 2.0]}], "d": {"d": 1.0, "ci95": ["unbounded", 2.0]}})
        self.assertEqual(res["checked"], ["a", "b", "c.0"])
        self.assertEqual(res["zero_width"], [{"where": "b", "point": 3.0}])
        self.assertEqual(res["point_outside"], [{"where": "c.0", "point": 9.0, "ci95": [1.0, 2.0]}])

    def test_interval_sanity_reads_exact_intervals(self):
        res = fa.interval_sanity({"cells": [{"stamped_mean": 100.0, "stamped_ci95": [100.0, 100.0], "exact95": [91.2, 100.0]},
                                            {"stamped_mean": 0.0, "exact95": [0.1, 0.4]}]})
        self.assertEqual(res["checked"], ["cells.0.exact95", "cells.1.exact95"])
        self.assertEqual(res["zero_width"], [])
        self.assertEqual(res["point_outside"], [{"where": "cells.1.exact95", "point": 0.0, "exact95": [0.1, 0.4]}])
        real = fa.interval_sanity(json.loads((fa.ROOT / "data/main/free-analyses/fa4r2.json").read_text())["result"])
        self.assertEqual((len(real["checked"]), real["zero_width"], real["point_outside"]), (105, [], []))

    def test_paired_is_seeded_by_name(self):
        a = fa.paired([1.0, -2.0, 0.5, 3.0, -1.0], "fa:test")
        b = fa.paired([1.0, -2.0, 0.5, 3.0, -1.0], "fa:test")
        c = fa.paired([1.0, -2.0, 0.5, 3.0, -1.0], "fa:other")
        self.assertEqual(a, b)
        self.assertEqual(a["d"], c["d"])
        self.assertEqual(fa.paired([], "x")["n"], 0)


@unittest.skipUnless(_git_ok(), "the repo's history is not available")
class Analysis4(unittest.TestCase):
    def test_exact_intervals(self):
        res = fa.fa4(fa.Checks())
        cells = {c["cell"]: c for c in res["cells"]}
        self.assertEqual(len(cells), len(fa.FA4_CELLS))
        off = cells["Study 1b Haiku thinking-off, 16 steps, chains"]
        self.assertEqual((off["x"], off["n"], off["exact95"][0]), (0, 80, 0.0))
        om = cells["Study 1b Opus-medium, 6 steps, pieces"]
        self.assertEqual((om["x"], om["n"], om["exact95"][1]), (40, 40, 100.0))
        self.assertAlmostEqual(om["exact95"][0], 100.0 * (0.025 ** (1 / 40)), places=6)   # Clopper-Pearson lower end at x = n

    def test_revision_2_keeps_the_first_cells_and_adds_by_rule(self):
        chk = fa.Checks()
        res = fa.fa4r2(chk)
        first = fa.fa4(fa.Checks())["cells"]
        self.assertEqual(res["cells"][:len(first)], first)                                 # the first version's cells, first and unchanged
        self.assertEqual(res["first_version_cells"] + res["added_cells"], len(res["cells"]))
        keys = [(c["source"], c["key"], c["cell"]) for c in res["cells"]]    # C10's two arms share one stamped pair key
        self.assertEqual(len(keys), len(set(keys)))
        for c in res["cells"][len(first):]:
            full = 100.0 if c["unit"] == "points" else 1.0
            self.assertIn(c["x"], (0, c["n"]))
            self.assertEqual(c["stamped_mean"], full if c["x"] == c["n"] else 0.0)
            self.assertEqual(c["exact95"][1 if c["x"] == c["n"] else 0], full if c["x"] == c["n"] else 0.0)
            self.assertLess(c["exact95"][0], c["exact95"][1])
        self.assertTrue(all(i["equal"] for i in chk.items))
        self.assertEqual({e["what"].split(":")[0] for e in res["excluded"]}, {"curve", "curve_d90", "main"})

    def test_revision_3_keeps_revision_2_and_scans_every_interval_field(self):
        chk = fa.Checks()
        res = fa.fa4r3(chk)
        second = json.loads((fa.ROOT / "data/main/free-analyses/fa4r2.json").read_text())["result"]["cells"]
        self.assertEqual(res["cells"][:len(second)], second)                               # revision 2's cells, first and unchanged
        new = res["cells"][len(second):]
        self.assertEqual(sorted({c["field"] for c in new}), ["ci90", "opus_accuracy_ci95"])
        for c in new:
            pct = int(round(c["level"] * 100))
            lo, hi = c[f"exact{pct}"]
            full = 100.0 if c["unit"] == "points" else 1.0
            self.assertIn(c["x"], (0, c["n"]))
            self.assertLess(lo, hi)
            self.assertTrue(lo <= c["stamped_mean"] <= hi)
            self.assertEqual(c[f"stamped_ci{pct}"], [c["stamped_mean"], c["stamped_mean"]])
            self.assertEqual(full if c["x"] == c["n"] else 0.0, c["stamped_mean"])
        nine = [c for c in new if c["field"] == "ci90"]
        self.assertEqual({c["level"] for c in nine}, {0.9})
        self.assertAlmostEqual(nine[0]["exact90"][1], 1 - 0.05 ** (1 / nine[0]["n"]), places=9)   # x = 0: upper end 1 - (alpha/2)^(1/n)
        self.assertTrue(all(i["equal"] for i in chk.items))
        self.assertEqual(set(res["scan"]["two_number_fields_not_intervals"]), {"quartiles"})
        san = fa.interval_sanity(res)
        self.assertEqual((len(san["checked"]) >= len(res["cells"]), san["zero_width"], san["point_outside"]), (True, [], []))

    def test_revision_2_refuses_an_unknown_collapse(self):
        self.assertEqual([k for k, _ in fa._zero_width({"a": {"ci95": [1.0, 1.0], "mean": 1.0}, "b": {"ci95": [0.1, 0.2]}})], ["a"])


class Analysis13(unittest.TestCase):
    def test_tie_patterns_agree_with_the_locked_vote(self):
        from harness.analysis import votes
        cases = (["a", "a", "a", "b", "b", "b", "c", "c", None, None],     # 3-3 and 2-2 ties possible
                 ["a", "b", "b", "c", "c", "a", "d", "a", "b", "c"],
                 ["x", "x", "x", "x", "x", "x", "x", "x", "x", "y"],       # the right answer never in a tie
                 [None] * 4 + ["a", "b", "a", "b", "c", "c"])
        for answers in cases:
            for k in (2, 5, 6):
                e = fa._tie_patterns(answers, "a", k)
                for tie in ("random", "wrong"):
                    r = votes.vote_accuracy_at_k(answers, "a", k, tie=tie, mode="exact")
                    self.assertEqual(float(e["acc"][tie]), r["acc"])
                self.assertEqual(sum(e["decided"].values()) / e["n_subsets"], r["tie_decided_share"])

    def test_a_3_3_tie(self):
        e = fa._tie_patterns(["a", "a", "a", "b", "b", "b"], "a", 6)
        self.assertEqual((e["n_subsets"], e["decided"]), (1, {"3x2": 1}))
        self.assertEqual((e["acc"]["random"], e["acc"]["wrong"]), (0.5, 0))

    @unittest.skipUnless(_git_ok(), "the repo's history is not available")
    def test_definition_is_the_register_row(self):
        d = fa.register_definition(*fa.FA13_RULING)
        self.assertEqual((d["id"], d["status"], d["date"], d["user_words"]), ("D-157", "ruled", "2026-10-16", '"go with A"'))
        self.assertIn("tie view for Test B2", d["ruling"])
        with self.assertRaises(ValueError):
            fa.register_definition("decisions/register.md", "ee30f69", "D-999")
        with tempfile.TemporaryDirectory() as t:
            fa.write_once(Path(t), "fa98", 13, {"x": 1}, {}, fa.Checks(), d)
            self.assertEqual(json.loads((Path(t) / "fa98.json").read_text())["definition"], d)


if __name__ == "__main__":
    unittest.main()
