"""report_groupc (the kept group-C items of research/reporting-inventory-main.md at 93334b8: C2, C3, C5, C7, C9, C10): one hand-computed
case per item on small synthetic rows (test_report_arms.Synth), then the whole report and the CLI on the fake main run
(test_main_analysis.FakeMainRun). Offline only."""

import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from harness.analysis import bootstrap, five_tests, report_groupc as gc, scoring
from harness.analysis.curve import cluster_bootstrap
from harness.tests import test_main_analysis as tma
from harness.tests.test_report_arms import Synth, items_for


def _haiku(s, arm, base, shape, right, wrong_keys=None, n=40):
    """`right` right tries (key "A") then n - right wrong ones (key "B", or the given keys)."""
    for samp in range(1, n + 1):
        if samp <= right:
            s.add(arm, base, shape, samp, True)
        else:
            s.add(arm, base, shape, samp, False, key=(wrong_keys(samp) if wrong_keys else None))


class Helpers(unittest.TestCase):

    def test_pearson_spearman_and_mid_ranks(self):
        self.assertAlmostEqual(gc.pearson([1, 1, 0, 0], [1, 0, 0, 0]), 1 / math.sqrt(3))          # phi of a 2x2 table
        self.assertIsNone(gc.pearson([1, 1, 1], [0, 1, 0]))                                       # no variation: undefined
        self.assertIsNone(gc.pearson([0.1, 0.1, 0.1], [0, 1, 2]))                                 # checked on the values, not on fsum
        self.assertIsNone(gc.pearson([1.0], [2.0]))
        self.assertEqual(gc.mid_ranks([1.0, 0.0, 1.0, 0.0]), [3.5, 1.5, 3.5, 1.5])
        self.assertEqual(gc.mid_ranks([25.0, 25.0 + 1e-12, -25.0, 75.0]), [2.5, 2.5, 1.0, 4.0])   # equal after rounding to 1e-9
        self.assertAlmostEqual(gc.spearman([1, 2, 3, 4], [10, 20, 30, 1000]), 1.0)


class ByHand(unittest.TestCase):

    def _c2_c3_synth(self):
        s = Synth()
        for b, (r6, r1) in enumerate(((True, True), (True, False), (False, False), (False, False))):   # Opus-medium, 0/1 each shape
            s.add("opus-med", b, "6x1", 1, r6)
            s.add("opus-med", b, "1x6", 1, r1)
            s.add("sonnet-med", b, "6x1", 1, True)                                                 # no variation at 6x1
            s.add("sonnet-med", b, "1x6", 1, b % 2 == 0)
        for b, (r6, r1) in enumerate(((40, 20), (20, 0), (0, 0))):                                 # Haiku-low: 100/50/0 and 50/0/0
            _haiku(s, "haiku-low", b, "6x1", r6)
            _haiku(s, "haiku-low", b, "1x6", r1)
        return s, s.ctx(items_for(bases=(0, 1, 2, 3), shapes=("6x1", "1x6")))

    def test_item_C2_pearson_and_phi(self):
        s, ctx = self._c2_c3_synth()
        r = gc.item_C2(ctx)
        self.assertEqual(r["label"], gc.LABEL)
        self.assertTrue(r["definition"].startswith("Per arm, across the 80 base puzzles: the Pearson correlation"))
        om = r["arms"]["opus-med"]
        self.assertEqual((om["n_bases"], om["statistic"], om["bootstrap_name"]), (4, "phi (Pearson on 0/1)", "rho:opus-med"))
        self.assertAlmostEqual(om["r"], 1 / math.sqrt(3))       # x = [1,1,0,0], y = [1,0,0,0]: sxy 0.5, sxx 1, syy 0.75
        self.assertTrue(-1.0 <= om["ci95"][0] <= om["ci95"][1] <= 1.0)
        self.assertGreater(om["draws_dropped_undefined"], 0)    # e.g. a draw of bases {2, 3} only: no variation, dropped and counted
        self.assertAlmostEqual(om["share_draws_dropped"], om["draws_dropped_undefined"] / 200)
        hl = r["arms"]["haiku-low"]
        self.assertEqual(hl["n_bases"], 3)
        self.assertAlmostEqual(hl["r"], math.sqrt(3) / 2)       # x = [100,50,0], y = [50,0,0]: sxy 2500, sxx 5000, syy 15000/9
        sm = r["arms"]["sonnet-med"]
        self.assertEqual(sm["r"], "undefined (no variation)")
        self.assertEqual(sm["why_undefined"], {"6x1": True, "1x6": False})
        self.assertEqual((sm["ci95"], sm["share_draws_dropped"]), ([None, None], 1.0))          # every draw undefined
        self.assertNotIn("e3", r["arms"])
        self.assertNotIn("haiku-med", r["arms"])                                                 # no rows: not reported

    def test_item_C3_shape_difference(self):
        s, ctx = self._c2_c3_synth()
        r = gc.item_C3(ctx)
        om = r["arms"]["opus-med"]
        self.assertEqual((om["d"], om["unit"], om["accuracy_6x1"], om["accuracy_1x6"]), (25.0, "points", 50.0, 25.0))  # [0,100,0,0]
        bases = ["s-000", "s-001", "s-002", "s-003"]
        vals = dict(zip(bases, (0.0, 100.0, 0.0, 0.0)))
        want = cluster_bootstrap([bases], lambda smp: sum(vals[b] for b in smp) / len(smp), "shape_diff:opus-med", draws=200)
        self.assertEqual(om["ci95"], list(want))                                                 # seed 20261012, name "shape_diff:opus-med"
        self.assertAlmostEqual(r["arms"]["haiku-low"]["d"], (50 + 50 + 0) / 3)
        self.assertEqual(r["arms"]["sonnet-med"]["d"], 50.0)                                       # [0, 100, 0, 100]

    def test_item_C5_interaction(self):
        s = Synth()
        # base 0: 6x1 Haiku 100 vs Opus 100 (0); 1x6 Haiku 50 vs Opus 100 (-50): 0 - (-50) = 50
        # base 1: 6x1 Haiku 0 vs Opus 0 (0); 1x6 Haiku 0 vs Opus 100 (-100): 100
        for b, (h6, o6, h1, o1) in enumerate(((40, True, 20, True), (0, False, 0, True))):
            _haiku(s, "haiku-med", b, "6x1", h6)
            _haiku(s, "haiku-med", b, "1x6", h1)
            s.add("opus-med", b, "6x1", 1, o6)
            s.add("opus-med", b, "1x6", 1, o1)
        ctx = s.ctx(items_for(bases=(0, 1), shapes=("6x1", "1x6")), k={"k_o": {"6x1": 1, "1x6": 1}, "k_s": 1})
        r = gc.item_C5(ctx)
        self.assertTrue(r["computed"])
        self.assertEqual((r["interaction"], r["t1_mean_difference"], r["t2_mean_difference"]), (75.0, 0.0, -75.0))
        self.assertEqual(r["bootstrap_name"], "shape_x_setup:haiku-med-vs-opus-med")
        want = cluster_bootstrap([["s-000", "s-001"]], lambda smp: sum({"s-000": 50.0, "s-001": 100.0}[b] for b in smp) / len(smp),
                                 "shape_x_setup:haiku-med-vs-opus-med", draws=200)
        self.assertEqual(r["ci95"], list(want))
        r0 = gc.item_C5(dict(ctx, k={"k_o": {"6x1": 0, "1x6": 1}, "k_s": 1}))
        self.assertFalse(r0["computed"])                                                          # a test that did not run

    def _c7_synth(self):
        s = Synth()
        _haiku(s, "haiku-med", 0, "6x1", 40)                                                      # bin [90,100]: vote@1 = 1
        _haiku(s, "haiku-med", 1, "6x1", 20, wrong_keys=lambda i: f"W{i}")                        # bin [50,60): 20 A, 20 distinct wrong
        _haiku(s, "haiku-med", 2, "6x1", 0, wrong_keys=lambda i: f"W{i}")                         # bin [0,10): never right
        for b in range(3):
            s.add("opus-med", b, "6x1", 1, True)
        return s

    def test_item_C7_bins_and_crossover(self):
        s = self._c7_synth()
        ctx = s.ctx(items_for(bases=(0, 1, 2)), k={"k_o": {"6x1": 22, "1x6": 1}, "k_s": 1})
        r = gc.item_C7(ctx)["shapes"]["6x1"]
        bins = r["bins"]
        self.assertEqual(sorted(bins), ["[0,10)", "[50,60)", "[90,100]"])
        self.assertEqual(bins["[90,100]"]["smallest_k_reaching_opus"], 1)
        # base 1: a draw with at most one A and only distinct wrong answers loses credit: at k = 20 that costs 2.76e-9 (0.999999997
        # after rounding), at k = 21 only 1.45e-10, which rounds to 1.0, so "reaches" (C1 item 20: after rounding to 1e-9) at k = 21
        mid = bins["[50,60)"]
        self.assertEqual(mid["smallest_k_reaching_opus"], 21)
        self.assertLess(mid["mean_vote_at_k"][20]["mean"], 1.0)                                  # unrounded, still below 1
        self.assertAlmostEqual(mid["mean_vote_at_k"][1]["mean"], (190 + 400 / 2) / 780)          # vote@2 by hand
        self.assertEqual((mid["opus_med_mean"], mid["haiku_med_single_try_mean"]), (1.0, 0.5))
        self.assertEqual(bins["[0,10)"]["smallest_k_reaching_opus"], "none up to 40")
        self.assertEqual(r["crossover_bin"], "[50,60)")                                           # 21 within k_O = 22
        r20 = gc.item_C7(dict(s.ctx(items_for(bases=(0, 1, 2)), k={"k_o": {"6x1": 20, "1x6": 1}, "k_s": 1})))["shapes"]["6x1"]
        self.assertEqual(r20["crossover_bin"], "[90,100]")                                        # 21 > k_O = 20
        self.assertFalse(r20["bins"]["[50,60)"]["reaches_within_k_O"])
        self.assertIn("[90,100] (k_O = 20)", r20["sentence"])

    def test_item_C9_spearman(self):
        s = Synth()
        same, distinct = (lambda i: "B"), (lambda i: f"W{i}")
        _haiku(s, "haiku-med", 0, "6x1", 30, same)          # agreement 1, vote@40 100, single 75: gain 25
        _haiku(s, "haiku-med", 1, "6x1", 30, distinct)      # agreement 0, gain 25
        _haiku(s, "haiku-med", 2, "6x1", 10, same)          # agreement 1, B wins: vote 0, single 25: gain -25
        _haiku(s, "haiku-med", 3, "6x1", 10, distinct)      # agreement 0, A leads 10 to 1: vote 100, single 25: gain 75
        _haiku(s, "haiku-med", 4, "6x1", 39)                # one wrong try: left out
        ctx = s.ctx(items_for(bases=(0, 1, 2, 3, 4)), k={"k_o": {"6x1": 40, "1x6": 0}, "k_s": 1})
        r = gc.item_C9(ctx)["shapes"]
        sh = r["6x1"]
        self.assertEqual((sh["n_kept"], sh["n_left_out"], sh["left_out"]), (4, 1, ["s-004"]))
        self.assertEqual([sh["per_puzzle"][f"s-00{b}"]["vote_gain"] for b in range(4)], [25.0, 25.0, -25.0, 75.0])
        self.assertEqual([sh["per_puzzle"][f"s-00{b}"]["agreement_share"] for b in range(4)], [1.0, 0.0, 1.0, 0.0])
        # ranks: agreement [3.5, 1.5, 3.5, 1.5], gain [2.5, 2.5, 1, 4]: sxy -3, sxx 4, syy 4.5
        self.assertAlmostEqual(sh["rho"], -1 / math.sqrt(2))
        self.assertEqual(sh["bootstrap_name"], "repeat_vs_gain:haiku-med:6x1")
        self.assertFalse(r["1x6"]["computed"])                                                    # k_O(1x6) = 0

    def test_item_C10_effort_contrasts(self):
        s = Synth()
        s.add("opus-med", 0, "6x1", 1, True)
        s.add("opus-med", 1, "6x1", 1, True)
        s.add("opus-low", 0, "6x1", 1, True, tout=500)                                           # $0.004 + $0.010 at list price
        s.add("opus-low", 1, "6x1", 1, False, tout=500)
        _haiku(s, "haiku-med", 0, "6x1", 20)
        _haiku(s, "haiku-med", 1, "6x1", 20)
        _haiku(s, "haiku-low", 0, "6x1", 40)
        _haiku(s, "haiku-low", 1, "6x1", 30)
        r = gc.item_C10(s.ctx(items_for(bases=(0, 1))))
        self.assertEqual(r["exploratory"], "exploratory: no Holm, no verdict")
        o = r["pairs"]["opus-low-vs-opus-med:6x1"]
        self.assertEqual((o["n"], o["d"], o["seed_name"]), (2, -50.0, "effort:opus-low-vs-opus-med:6x1"))   # [0, -100]
        want = bootstrap.paired_bca([0.0, -100.0], margin=-10.0, B=400,
                                    seed=bootstrap.derive_seed(20261011, "effort:opus-low-vs-opus-med:6x1"))
        self.assertEqual(o["ci95"], list(want["ci95"]))
        self.assertNotIn("p", o)                                                                  # d and the interval only
        self.assertAlmostEqual(o["cost_difference_usd"], 0.014 - 0.024)                          # item 9b means, list price
        h = r["pairs"]["haiku-low-vs-haiku-med:6x1"]
        self.assertEqual((h["d"], h["seed_name"]), (37.5, "effort:haiku-low-vs-haiku-med:6x1"))  # [100-50, 75-50]
        self.assertAlmostEqual(h["cost_difference_usd"], 0.0)                                    # same usage per sample
        self.assertFalse(r["pairs"]["opus-low-vs-opus-med:1x6"]["computed"])                     # no rows at 1x6


class EndToEnd(unittest.TestCase):
    """The whole report and the CLI on the fake main run (every arm, refusals, truncations, repeats, E3), serialised."""

    @classmethod
    def setUpClass(cls):
        tma.FakeMainRun.setUpClass()
        cls.f = tma.FakeMainRun
        cls.ctx = gc.build_context(cls.f.set_dir, cls.f.run_dir, cls.f.k_path, ("sl", "ho", "hx"), B=200, draws=40)
        cls.res = gc.report(cls.ctx)

    def test_report_runs_and_serialises(self):
        text = json.dumps(self.res, default=str)
        self.assertGreater(len(text), 1000)
        for key in ("item_C2", "item_C3", "item_C5", "item_C7", "item_C9", "item_C10"):
            self.assertEqual(self.res[key]["label"], gc.LABEL)
            for cid in self.res[key]["post_hoc_choices"]:
                self.assertIn(cid, self.res["post_hoc_choices"])
        for key in ("item_C1", "item_C4", "item_C6", "item_C8", "item_C11", "item_C12", "item_C13"):
            self.assertNotIn(key, self.res)
        self.assertEqual(set(self.res["post_hoc_choices"]), set(gc.POST_HOC_CHOICES))
        for cid, v in self.res["post_hoc_choices"].items():
            self.assertEqual(set(v), {"id", "item", "choice", "why"})
            self.assertEqual(v["id"], cid)
        self.assertIn("93334b8", self.res["note"])

    def test_numbers_line_up_with_the_locked_code(self):
        rows, k = self.ctx["rows"], self.ctx["k"]
        k_o, k_s = {sh: int(v) for sh, v in k["k_o"].items()}, int(k["k_s"])
        d = five_tests.test_differences(rows, k_o, k_s, "as_deployed", n=6)
        c5 = self.res["item_C5"]
        if c5["computed"]:
            self.assertAlmostEqual(c5["t1_mean_difference"], sum(d["t1"]) / len(d["t1"]))
            self.assertAlmostEqual(c5["t2_mean_difference"], sum(d["t2"]) / len(d["t2"]))
            self.assertAlmostEqual(c5["interaction"], c5["t1_mean_difference"] - c5["t2_mean_difference"])
        hm = self.res["item_C3"]["arms"]["haiku-med"]
        a6 = scoring.arm_scores([r for r in rows if r["setup"] == "haiku-med" and r["shape"] == "6x1"])
        a1 = scoring.arm_scores([r for r in rows if r["setup"] == "haiku-med" and r["shape"] == "1x6"])
        self.assertAlmostEqual(hm["d"], sum(a6[b] - a1[b] for b in a6) / len(a6))
        self.assertEqual(hm["n_bases"], 3)
        self.assertEqual(set(self.res["item_C2"]["arms"]), set(gc.BOTH_SHAPE_ARMS))
        self.assertEqual(set(self.res["item_C10"]["pairs"]), {f"{a}-vs-{c}:{sh}" for a, c in gc.EFFORT_PAIRS for sh in ("6x1", "1x6")})
        for v in self.res["item_C10"]["pairs"].values():
            self.assertTrue(v["computed"])
        for sh in ("6x1", "1x6"):
            c7 = self.res["item_C7"]["shapes"][sh]
            self.assertEqual(sum(b["puzzles"] for b in c7["bins"].values()), 3)
            c9 = self.res["item_C9"]["shapes"][sh]
            if c9["computed"]:
                self.assertEqual(c9["n_kept"] + c9["n_left_out"], 3)

    def test_cli_writes_once_and_refuses_to_overwrite(self):
        out = Path(tempfile.mkdtemp()) / "groupc.json"
        argv = ["--set", str(self.f.set_dir), "--run", str(self.f.run_dir), "--k", str(self.f.k_path), "--extras", "sl,ho,hx",
                "--out", str(out)]
        with redirect_stdout(StringIO()):
            self.assertEqual(gc.main(argv), 0)
        res = json.loads(out.read_text())
        self.assertEqual(res["inputs"]["extras"], ["sl", "ho", "hx"])
        import hashlib
        self.assertEqual(res["inputs"]["calls_jsonl_sha256"], hashlib.sha256((self.f.run_dir / "calls.jsonl").read_bytes()).hexdigest())
        self.assertEqual(res["item_C10"]["pairs"]["opus-low-vs-opus-med:6x1"]["B"], 10_000)        # the note's draws, not a test's
        self.assertEqual(res["item_C2"]["arms"]["haiku-med"]["draws"], 2_000)
        before = out.read_bytes()
        with self.assertRaises(SystemExit):
            gc.main(argv)
        self.assertEqual(out.read_bytes(), before)

    def test_k_json_from_another_table_is_refused(self):
        bad = Path(tempfile.mkdtemp()) / "k.json"
        k = json.loads(self.f.k_path.read_text())
        bad.write_text(json.dumps(dict(k, compact_table_sha256="0" * 64)))
        with self.assertRaises(ValueError):
            gc.build_context(self.f.set_dir, self.f.run_dir, bad, ("sl", "ho", "hx"))
        bad.write_text(json.dumps(dict(k, k_s=int(k["k_s"]) + 1)))
        with self.assertRaises(ValueError):
            gc.build_context(self.f.set_dir, self.f.run_dir, bad, ("sl", "ho", "hx"))
        with self.assertRaises(ValueError):                                                       # wrong extras: the manifest check
            gc.build_context(self.f.set_dir, self.f.run_dir, self.f.k_path, ("sl",))


if __name__ == "__main__":
    unittest.main()
