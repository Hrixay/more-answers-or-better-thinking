"""report_votes: items 7, 8a, 8b, 18 and 20 of research/reporting-definitions-main.md. One hand-computed case per item on small synthetic
rows, the open questions left out as the note requires, and one end-to-end call on the fake main run of test_main_analysis. Offline only."""

import json
import math
import subprocess
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest import mock

from harness.analysis import bootstrap, five_tests, main_rows, report_costs as rc, report_votes as rv, scoring
from harness.pareto.prices import HAIKU, OPUS, SONNET
from harness.taskgen import ledger
from harness.tests import test_main_analysis as tma

ANSWER = [[10 * j] for j in range(1, 7)]                 # one 6x1 puzzle's key: six pieces of one balance each


def pieces_text(entries):
    return "Answer: " + ", ".join(f"{i} = {ledger.fmt(a)}" for i, a in entries)


def vote_none(r, k, n=40):
    """vote@k with r samples right and n - r votes for nothing: a k-subset is wrong only if it holds no right sample."""
    return 1 - math.comb(n - r, k) / math.comb(n, k)


class Fixture:
    """Builders for a synthetic set ("s", bases 000-002) and its records and rows."""

    SET = "s"
    MODEL = {"hm": HAIKU, "om": OPUS, "sm": SONNET, "ol": OPUS, "sl": SONNET, "hl": HAIKU, "ho": HAIKU, "hx": HAIKU}
    SETUP = {**main_rows.FIVE_TEST_ARMS, **main_rows.OTHER_ARMS}

    @staticmethod
    def items(bases=(0, 1, 2), shapes=("6x1", "1x6")):
        out = {}
        for b in bases:
            for sh in shapes:
                w, d = (int(x) for x in sh.split("x"))
                out[f"s-{b:03d}-{sh}"] = {"id": f"s-{b:03d}-{sh}", "width": w, "depth": d, "base_index": b, "params": {"lines": 1},
                                          "answer": ANSWER}
        return out

    @classmethod
    def rec(cls, iid, tag, s, out_tokens=0, cost="0", text=None, kind="answered", billed=None):
        return {"custom_id": f"{iid}-{tag}-{s:02d}", "requested_model": cls.MODEL[tag], "effort": "medium", "kind": kind,
                "cost_usd": cost, "usage_raw": {"input_tokens": 0, "output_tokens": out_tokens}, "answer_text": text,
                "refusal_billed_by_rule": billed, "stop_reason": "refusal" if kind == "refusal" else "end_turn",
                "meta": {"item_id": iid, "setup": tag, "sample": s}}

    @classmethod
    def pieces_row(cls, rec, item):
        iid = rec["meta"]["item_id"]
        g = scoring.grade_24x1(rec["answer_text"], item["answer"], 1, kind=rec["kind"])
        return dict(g, setup=cls.SETUP[rec["meta"]["setup"]], shape="6x1", item_id=iid, base_id=iid.rsplit("-", 1)[0],
                    custom_id=rec["custom_id"], kind=rec["kind"], stop_reason=rec["stop_reason"], sample=rec["meta"]["sample"])

    @staticmethod
    def missing_row(iid, setup, s):
        return {"setup": setup, "shape": "6x1", "item_id": iid, "base_id": iid.rsplit("-", 1)[0], "custom_id": f"{iid}-x-{s:02d}",
                "kind": "missing", "stop_reason": None, "sample": s, "format_status": "missing", "answer_key": None, "correct": False,
                "pieces_right": 0}

    @staticmethod
    def key_row(base, shape, setup, key, right, kind="answered", cid=None):
        """A scored row with a given vote key (6x1: answer_key; 1x6: an ok trace) or, for a refusal, none; `cid` its call's custom_id."""
        r = {"setup": setup, "shape": shape, "base_id": f"s-{base:03d}", "item_id": f"s-{base:03d}-{shape}", "kind": kind,
             "stop_reason": "refusal" if kind == "refusal" else "end_turn", "correct": right and kind == "answered", "custom_id": cid}
        if shape == "6x1":
            r["answer_key"] = key if kind == "answered" else None
        else:
            r.update(format_status="ok" if kind == "answered" else kind, trace_key=key if kind == "answered" else None,
                     answer_only=False, correct_original=r["correct"])
        return r


# ---------------------------------------------------------------- item 7

class Item7PerPieceByHand(unittest.TestCase):
    """Two 6x1 puzzles A (base 000) and B (base 001).
    Haiku-medium: on A samples 1-30 all six pieces right, 31-40 piece 1 wrong ([11]); on B samples 1-20 right, 21-30 refused (free under
    B5), 31-40 missing (no record). Opus-medium: A right; B pieces 1-3 right, piece 4 absent, 5-6 wrong (a missing_line reply, Q10).
    Sonnet-medium: A truncated (its text holds a right Answer line), B right."""

    @classmethod
    def setUpClass(cls):
        F = Fixture
        cls.items = F.items(bases=(0, 1), shapes=("6x1",))
        A, B = "s-000-6x1", "s-001-6x1"
        recs, rows = [], []
        right = pieces_text(enumerate(ANSWER, 1))
        slip = pieces_text([(1, [11])] + list(enumerate(ANSWER, 1))[1:])
        for s in range(1, 41):
            recs.append(F.rec(A, "hm", s, 4000, "0.001", right if s <= 30 else slip))
        for s in range(1, 31):
            recs.append(F.rec(B, "hm", s, 4000, "0.001", right) if s <= 20 else F.rec(B, "hm", s, 100, "0.00005", None, "refusal", False))
        recs.append(F.rec(A, "om", 1, 2000, "0.02", right))
        recs.append(F.rec(B, "om", 1, 3000, "0.03", pieces_text([(1, [10]), (2, [20]), (3, [30]), (5, [0]), (6, [0])])))
        recs.append(F.rec(A, "sm", 1, 1000, "0.005", right, "truncated"))         # a truncated reply: no piece counts, readable or not
        recs.append(F.rec(B, "sm", 1, 1000, "0.005", right))
        rows = [F.pieces_row(r, cls.items[r["meta"]["item_id"]]) for r in recs]
        rows += [F.missing_row(B, "haiku-med", s) for s in range(31, 41)]
        cls.ctx = {"rows": rows, "other": [], "records": recs, "items": cls.items, "set_id": "s", "n": 6, "B": 400}

    def test_per_piece_accuracy_over_the_designed_tries(self):
        r = rv.per_piece_accuracy(self.ctx)["arms"]
        # Haiku: A (30 x 6/6 + 10 x 5/6) / 40 = 23/24; B 20 x 6/6 / 40 = 1/2 (refused and missing tries 0); mean 35/48
        self.assertAlmostEqual(r["haiku-med"]["mean"], 35 / 48)
        self.assertEqual((r["haiku-med"]["designed_tries"], r["haiku-med"]["n_puzzles"]), (40, 2))
        # Opus: A 1; B 3 of 6 (the readable right entries of a missing_line reply count, Q10); mean 3/4
        self.assertAlmostEqual(r["opus-med"]["mean"], 0.75)
        lo, hi = r["opus-med"]["ci95"]
        self.assertTrue(0.5 <= lo <= 0.75 <= hi <= 1.0)
        self.assertAlmostEqual(r["sonnet-med"]["mean"], 0.5)                     # the truncated try scores 0 pieces
        self.assertNotIn("haiku-low", r)                                          # an arm with no rows is not listed

    def test_per_piece_vote_at_k_by_hand(self):
        # k = 1: the per-piece accuracy again. k = 3: A's piece 1 (30 right, 10 the same wrong) is wrong when >= 2 of 3 are wrong:
        # (C(10,2) 30 + C(10,3)) / C(40,3) = 1470 / 9880; B's pieces (20 right, 20 votes for nothing): 1 - C(20,3)/C(40,3).
        r1 = rv.per_piece_vote_at(self.ctx, 1)
        self.assertAlmostEqual(r1["mean"], 35 / 48)
        r3 = rv.per_piece_vote_at(self.ctx, 3)
        a = ((1 - 1470 / 9880) + 5) / 6
        b = vote_none(20, 3)
        self.assertAlmostEqual(r3["mean"], (a + b) / 2)
        self.assertAlmostEqual(rv.per_piece_vote_at(self.ctx, 40)["mean"], 1.0)        # plurality right on every piece at k = 40

    def test_the_per_piece_curve_has_one_name_and_its_band_at_k_is_the_point_at_k(self):
        # C4 item 1: one name for the whole curve; the k_O / k_S points are its values and bands at those k. Two puzzles, 400 draws: the
        # band's ends are the two puzzles' own values (draws {B, B} and {A, A}, about 1/4 each).
        pts = rv.item_7_curve_points(self.ctx)
        self.assertEqual(len(pts), 40)
        self.assertEqual({p["bootstrap_name"] for p in pts}, {"per_piece_vote_curve:haiku-med"})
        a, b = ((1 - 1470 / 9880) + 5) / 6, vote_none(20, 3)
        lo, hi = pts[2]["ci95"]
        self.assertAlmostEqual(lo, b)
        self.assertAlmostEqual(hi, a)
        self.assertEqual(rv.per_piece_vote_at(self.ctx, 3), pts[2])                     # no name of its own
        self.assertEqual(rv.OPEN_QUESTIONS, {})

    def test_list_cost_and_cost_per_task_use_the_shared_copies(self):
        recs = {r["custom_id"]: r for r in self.ctx["records"]}
        self.assertEqual(rc.list_cost(recs["s-000-6x1-hm-01"]), Decimal("0.002"))          # 4000 output x $0.50 / MTok, no Batch half
        self.assertEqual(rc.list_cost(recs["s-001-6x1-hm-21"]), Decimal(0))               # a refusal B5 does not bill
        self.assertEqual(rc.list_cost(dict(recs["s-001-6x1-hm-21"], refusal_billed_by_rule=None, free_by_rule=True)), Decimal(0))
        self.assertEqual(rc.list_cost(dict(recs["s-001-6x1-hm-21"], refusal_billed_by_rule=True)), Decimal("0.00005"))
        self.assertFalse(hasattr(rv, "list_cost"))                                          # C3: one copy, in report_costs
        ctx = dict(self.ctx, _cache={})
        # Opus: (0.04 + 0.06) / 2 = 0.05 per puzzle, / 6 per task
        self.assertAlmostEqual(rc.cost_block(ctx, "opus-med", "6x1")["mean"], 0.05)
        # Haiku per sample (X4: the 10 missing samples cost $0 and count): A 0.002; B 20 x 0.002 / 40 = 0.001; the mean 0.0015 (X7: / 6)
        h = rc.cost_block(ctx, "haiku-med", "6x1")
        self.assertAlmostEqual(h["mean"], 0.0015)
        self.assertEqual(h["calls_without_record"], 10)
        self.assertEqual(rc.cost_block(ctx, "opus-low", "6x1")["n_bases"], 0)               # an arm with no rows has no cost

    def test_the_d42_and_realtime_arms_are_out_of_the_design(self):
        other = [dict(r, setup="haiku-med-d42-variant") for r in self.ctx["rows"] if r["setup"] == "haiku-med"][:5]
        r = rv.per_piece_accuracy(dict(self.ctx, other=other, _cache={}))
        self.assertEqual(r["out_of_design"], {"haiku-med-d42-variant": rv.OUT_OF_DESIGN})      # X5


# ---------------------------------------------------------------- items 8a, 8b, 18, 20: one cost-and-score fixture

class CostFixture(unittest.TestCase):
    """Bases 000-002, both shapes (6x1 Haiku rows graded from real replies; R is the key, W / Wb / Wc piece 1 wrong). Costs (Batch, logged; list = 2 x Batch from the usage): Haiku-medium $0.001 per sample (4000 output
    tokens), Opus-medium $0.020 / $0.024 / $0.0325 per puzzle, Sonnet-medium $0.0101 per puzzle. So at each shape: k_O = floor(0.0255 /
    0.001) = 25, median ratio 24, k* = 51/2; k_S = floor(10.1) = 10, k* = 101/10.
    Scores. 6x1, Haiku: base 000 36 right + 4 the same wrong; 001 39 right + 1 wrong; 002 10 one wrong key + 30 another. 1x6, Haiku:
    base b has 10 (b + 1) right traces, the rest refused. Opus, Sonnet, Opus-low and E3 right everywhere."""

    OPUS_COST = {0: ("0.02", 2000), 1: ("0.024", 2400), 2: ("0.0325", 3250)}

    @classmethod
    def build(cls, k_o=None):
        F = Fixture
        items = F.items()
        recs, rows = [], []
        hm6 = {0: ["R"] * 36 + ["W"] * 4, 1: ["R"] * 39 + ["W"], 2: ["Wb"] * 10 + ["Wc"] * 30}
        text = {"R": pieces_text(enumerate(ANSWER, 1))}
        text.update({w: pieces_text([(1, [v])] + list(enumerate(ANSWER, 1))[1:]) for w, v in (("W", 11), ("Wb", 12), ("Wc", 13))})
        for b in range(3):
            for sh in ("6x1", "1x6"):
                iid = f"s-{b:03d}-{sh}"
                hm = [F.rec(iid, "hm", s, 4000, "0.001", text[hm6[b][s - 1]] if sh == "6x1" else None) for s in range(1, 41)]
                recs += hm
                if sh == "6x1":
                    rows += [F.pieces_row(r, items[iid]) for r in hm]
                recs.append(F.rec(iid, "om", 1, cls.OPUS_COST[b][1], cls.OPUS_COST[b][0]))
                recs.append(F.rec(iid, "sm", 1, 2020, "0.0101"))
                recs.append(F.rec(iid, "ol", 1, 0, "0"))
        for b in range(3):
            r = 10 * (b + 1)
            iid = f"s-{b:03d}-1x6"
            rows += [F.key_row(b, "1x6", "haiku-med", "T", True, cid=f"{iid}-hm-{s:02d}") for s in range(1, r + 1)]
            rows += [F.key_row(b, "1x6", "haiku-med", None, False, "refusal", cid=f"{iid}-hm-{s:02d}") for s in range(r + 1, 41)]
            for sh in ("6x1", "1x6"):
                for setup, tag in (("opus-med", "om"), ("sonnet-med", "sm"), ("opus-low", "ol")):
                    rows.append(F.key_row(b, sh, setup, "R" if sh == "6x1" else "T", True, cid=f"s-{b:03d}-{sh}-{tag}-01"))
            rows.append({"setup": "e3", "shape": "1x6", "base_id": f"s-{b:03d}", "item_id": f"s-{b:03d}-1x6", "kind": "answered",
                         "stop_reason": "end_turn", "step_correct": [True] * 6, "correct": True})
        k = {"k_o": k_o or {"6x1": 25, "1x6": 25}, "k_s": 10}
        return {"rows": rows, "other": [], "records": recs, "items": items, "set_id": "s", "n": 6, "k": k, "B": 300}

    def setUp(self):
        self.ctx = self.build()


class Item8aKValuesByHand(CostFixture):

    def test_every_row_k_by_hand(self):
        kv = rv.k_values(self.ctx)
        for t, pilot in (("t1", 40), ("t2", 36)):                                  # pilot 43.9 held to 40 at 6x1; 36.78 at 1x6
            self.assertEqual(kv[t]["row_k"], {"median ratio": 24, "pilot": pilot, "k*": Fraction(51, 2), "k−2": 23, "k−1": 24,
                                              "k+0": 25, "k+1": 26, "k+2": 27})
            self.assertEqual((kv[t]["k_table_k"], kv[t]["samples_drawn_designed"], kv[t]["k_table_matches_confirmatory"]), (25, 40, True))
            self.assertEqual(kv[t]["held_at_the_limit"], {})
        self.assertEqual(kv["t3"]["row_k"], {"median ratio": 10, "pilot": 12, "k*": Fraction(101, 10), "k−2": 8, "k−1": 9,
                                             "k+0": 10, "k+1": 11, "k+2": 12})
        self.assertEqual(kv["t1"]["pilot_ratio"], Fraction(1980984, 45115))

    def test_a_band_value_outside_the_limit_is_held_at_the_limit(self):
        ctx = self.build(k_o={"6x1": 40, "1x6": 25})                               # k.json says 40 at 6x1: 41 and 42 are outside 1..40
        kv = rv.k_values(ctx)
        self.assertEqual((kv["t1"]["row_k"]["k+1"], kv["t1"]["row_k"]["k+2"], kv["t1"]["row_k"]["k+0"]), (40, 40, 40))   # X8
        self.assertEqual(kv["t1"]["held_at_the_limit"], {"k+1": {"k_plus_d": 41, "held_at": 40}, "k+2": {"k_plus_d": 42, "held_at": 40}})
        self.assertEqual(kv["t2"]["held_at_the_limit"], {})
        self.assertFalse(kv["t1"]["k_table_matches_confirmatory"])
        low = rv.k_values(self.build(k_o={"6x1": 1, "1x6": 25}))["t1"]             # k_O = 1: k-1 and k-2 are below 1, held at 1
        self.assertEqual((low["row_k"]["k−2"], low["row_k"]["k−1"], low["row_k"]["k+1"]), (1, 1, 2))
        self.assertEqual(sorted(low["held_at_the_limit"]), ["k−1", "k−2"])

    def test_samples_drawn_is_the_designed_40_when_a_sample_is_missing(self):
        ctx = self.build()
        ctx["records"] = [r for r in ctx["records"] if r["custom_id"] != "s-000-1x6-hm-40"]   # one Haiku call lost at 1x6
        kv = rv.k_values(ctx)
        self.assertEqual(kv["t2"]["k_table_samples_drawn"], 39)                     # k_table's fewest real samples
        self.assertEqual(kv["t2"]["k_star"]["samples_drawn"], 40)                   # X2: k* held to the designed 40
        self.assertEqual(len(rv.arm_curve(ctx, "haiku-med", "1x6")["s-000"]), 40)

    def test_k_s_at_6x1_for_item_7(self):
        ks = rv.k_s_pieces(self.ctx)
        self.assertEqual((ks["k"], ks["ratio"], ks["shape"]), (10, Fraction(101, 10), "6x1"))
        with self.assertRaises(ValueError):                                        # the shape swap is checked against k.json's k_O
            rv.k_s_pieces(self.build(k_o={"6x1": 24, "1x6": 25}))


class Item8bByHand(CostFixture):

    def test_rows_rerun_the_family_at_each_rows_k(self):
        seen = []
        real = five_tests.test_differences

        def spy(rows, k_o, k_s, view="as_deployed", **kw):
            seen.append((dict(k_o), k_s, view))
            return real(rows, k_o, k_s, view, **kw)
        with mock.patch.object(five_tests, "test_differences", side_effect=spy):
            rows = rv.sensitivity_rows(self.ctx)
        self.assertIn(({"6x1": 23, "1x6": 23}, 8, "as_deployed"), seen)            # "k−2"
        self.assertIn(({"6x1": 40, "1x6": 36}, 12, "as_deployed"), seen)           # "pilot"
        self.assertEqual(rows["k+0"]["tests"], five_tests.analyse(self.ctx["rows"], {"6x1": 25, "1x6": 25}, 10, B=300, n=6)["tests"])
        self.assertEqual(rows["pilot"]["label"], "k-sensitivity (not confirmatory)")
        # t3 at 1x6, base b: 10 (b + 1) right, the rest votes for nothing; Sonnet right. vote@10 and vote@12 by hand:
        for name, k in (("k−2", 8), ("k+2", 12)):
            d = sum(100 * vote_none(10 * (b + 1), k) - 100 for b in range(3)) / 3
            self.assertAlmostEqual(rows[name]["tests"]["t3"]["d"], d)
        # k* = 101/10: 0.9 vote@10 + 0.1 vote@11
        d = sum(100 * (0.9 * vote_none(10 * (b + 1), 10) + 0.1 * vote_none(10 * (b + 1), 11)) - 100 for b in range(3)) / 3
        self.assertAlmostEqual(rows["k*"]["tests"]["t3"]["d"], d)
        self.assertEqual(rows["k*"]["tests"]["t5"], rows["k+0"]["tests"]["t5"])     # t4 and t5 unchanged in every row
        ctx40 = self.build(k_o={"6x1": 40, "1x6": 25})
        r40 = rv.sensitivity_rows(ctx40)
        self.assertTrue(r40["k+1"]["computed"])                                    # X8: the whole family, t1 held at 40
        self.assertEqual(r40["k+1"]["held_at_the_limit"], ["t1"])
        t1 = r40["k+1"]["tests"]["t1"]
        self.assertEqual((t1["k_label"], t1["k_plus_d"], t1["held_at"]), ("held at the limit", 41, 40))
        self.assertEqual((t1["d"], t1["p"]), (r40["k+0"]["tests"]["t1"]["d"], r40["k+0"]["tests"]["t1"]["p"]))   # its real p, not 1
        self.assertEqual(set(r40["k+2"]["tests"]), {"t1", "t2", "t3", "t4", "t5"})
        spend = rv.realised_spend_at_k(ctx40)["tests"]["t1"]["by_row"]
        self.assertEqual((spend["k+2"]["k"], spend["k+2"]["haiku_arm"]), (40, spend["k+0"]["haiku_arm"]))

    def test_realised_spend_at_list_price(self):
        r = rv.realised_spend_at_k(self.ctx)["tests"]
        # list: Haiku 0.002 per sample; Opus (0.04 + 0.048 + 0.065) / 3 = 0.051 per puzzle; 3 puzzles
        t1 = r["t1"]["by_row"]["k+0"]
        self.assertEqual((t1["haiku_arm"], t1["comparator_arm"], t1["k"]), (Decimal("0.150"), Decimal("0.153"), 25))
        self.assertEqual(r["t3"]["by_row"]["k−2"]["haiku_arm"], Decimal("0.048"))             # 8 x 0.002 x 3
        self.assertEqual(r["t3"]["by_row"]["k*"]["haiku_arm"], Decimal("0.0606"))             # 10.1 x 0.002 x 3
        self.assertEqual(r["t3"]["by_row"]["k*"]["comparator_arm"], Decimal("0.0606"))        # Sonnet 0.0202 x 3: k* spends the same

    def test_realised_spend_uses_the_shared_9b_with_missing_calls_at_0(self):
        # V-1 / X4: one Haiku sample (base 000, 6x1, sample 40) and one Opus call (base 002, 6x1) have no record: each costs $0 and its
        # puzzle stays in. Haiku per sample (0.002 + 39 x 0.002 / 40 + 0.002) / 3 = 0.0019983..; Opus (0.04 + 0.048 + 0) / 3 = 0.088 / 3
        ctx = self.build()
        ctx["records"] = [x for x in ctx["records"] if x["custom_id"] not in ("s-000-6x1-hm-40", "s-002-6x1-om-01")]
        t1 = rv.realised_spend_at_k(ctx)["tests"]["t1"]
        h = (Fraction(2, 1000) * 2 + Fraction(2, 1000) * 39 / 40) / 3
        o = Fraction(88, 1000) / 3
        self.assertEqual(Fraction(t1["haiku_list_cost_per_sample"]), Fraction(rv.kscript._d(h)))
        self.assertEqual(Fraction(t1["comparator_list_cost_per_puzzle"]), Fraction(rv.kscript._d(o)))
        self.assertAlmostEqual(float(t1["by_row"]["k+0"]["haiku_arm"]), float(25 * h * 3), places=12)
        self.assertAlmostEqual(float(t1["by_row"]["k+0"]["comparator_arm"]), 0.088, places=12)
        self.assertAlmostEqual(float(t1["comparator_list_cost_per_puzzle"]), rc.cost_block(ctx, "opus-med", "6x1")["mean"])

    def test_the_vote_curve(self):
        c = rv.vote_curve(self.ctx)
        pts = c["1x6"]["points"]
        self.assertEqual(len(pts), 40)
        for k in (1, 5, 30):
            self.assertAlmostEqual(pts[k - 1]["mean"], sum(vote_none(10 * (b + 1), k) for b in range(3)) / 3)
        self.assertEqual((pts[0]["exact"], pts[0]["sampled"], pts[0]["max_mc_se"]), (3, 0, 0.0))
        self.assertEqual(c["1x6"]["bootstrap_name"], "vote_curve:haiku-med:1x6")
        self.assertIs(c["1x6"], rv.curve_summary(self.ctx, "haiku-med", "1x6"))      # the one copy, memoised
        # 6x1, k = 2: base 000 (36 R, 4 W): (C(36,2) + 36 x 4 / 2) / C(40,2) = 702/780; 001: (C(39,2) + 39/2) / 780; 002: 0
        self.assertAlmostEqual(c["6x1"]["points"][1]["mean"], (702 / 780 + (741 + 19.5) / 780 + 0) / 3)
        # the share of 2-subsets a tie with the right answer decided: 000 144/780, 001 39/780, 002 0
        self.assertAlmostEqual(c["6x1"]["points"][1]["tie_decided_share_mean"], (144 / 780 + 39 / 780) / 3)
        lo, hi = c["6x1"]["points"][1]["ci95"]
        self.assertTrue(lo <= c["6x1"]["points"][1]["mean"] <= hi)

    def test_sign_flip(self):
        diffs = {"t1": [1.0, 2.0, 3.0], "t2": [], "t3": [-1.0, 2.0], "t4": [float(x) for x in range(-3, 15)], "t5": [0.0]}
        with mock.patch.object(five_tests, "test_differences", return_value=diffs):
            r = rv.sign_flip_check(self.ctx)
        self.assertEqual(r["t1"]["p"], 1 / 8)                                      # only the identity pattern reaches 6
        self.assertEqual(r["t3"]["p"], 2 / 4)                                      # sums 1, 3, -3, -1: two reach 1
        self.assertEqual(r["t2"], {"ran": False, "p": None})
        self.assertEqual(r["t4"]["p"], bootstrap.sign_flip_p(diffs["t4"], 0.0, 100_000, bootstrap.derive_seed(20261011, "t4:sign_flip")))
        self.assertEqual(r["label"], "sensitivity (superiority, d = 0)")


class Item7VoteCostByHand(CostFixture):

    def test_the_votes_cost_per_task_at_k_O_and_k_S(self):
        # Haiku-medium 6x1: 4000 output tokens = $0.002 per sample at list price; k_O(6x1) = 25, k_S(6x1) = 10; one piece is one task
        r = rv.item_7(self.ctx)["cost_per_task"]
        o, s_ = r["haiku-med vote at k_O"], r["haiku-med vote at k_S"]
        self.assertEqual((o["k"], s_["k"]), (25, 10))
        self.assertAlmostEqual(o["cost_per_task"], 25 * 0.002 / 6)
        self.assertAlmostEqual(s_["cost_per_task"], 10 * 0.002 / 6)
        self.assertAlmostEqual(r["haiku-med"]["cost_per_task"], 0.002 / 6)                    # X7: one sample


class Item18ByHand(CostFixture):

    def test_methods_and_mc_error(self):
        r = rv.item_18(self.ctx)
        self.assertEqual(r["vote_curve"]["per_piece_6x1"][0], {"k": 1, "exact": 18, "sampled": 0, "max_mc_se": 0.0})   # 3 puzzles x 6 pieces
        self.assertEqual(r["vote_curve"]["per_piece_6x1"][39], {"k": 40, "exact": 18, "sampled": 0, "max_mc_se": 0.0})
        for t, k in (("t1", 25), ("t2", 25), ("t3", 10)):
            self.assertEqual(r["tests"][t]["k"], k)
            for view in scoring.VIEWS:
                self.assertEqual(r["tests"][t]["views"][view], {"exact": 3, "sampled": 0, "max_mc_se": 0.0})
        self.assertEqual(r["vote_curve"]["6x1"][39], {"k": 40, "exact": 3, "sampled": 0, "max_mc_se": 0.0})

    def test_a_sampled_vote_is_counted_with_its_error(self):
        real = rv.votes.vote_accuracy_at_k

        def sampled(answers, correct, k, **kw):
            return dict(real(answers, correct, k, **kw), method="sampled", mc_se=0.01 * k)
        with mock.patch.object(rv.votes, "vote_accuracy_at_k", side_effect=sampled):
            r = rv.item_18(dict(self.ctx, _cache={}))
        self.assertEqual(r["tests"]["t3"]["views"]["as_deployed"], {"exact": 0, "sampled": 3, "max_mc_se": 0.1})


class Item20ByHand(CostFixture):

    def test_bins_agreement_and_the_too_few_group(self):
        r = rv.item_20(self.ctx)["6x1"]
        per = r["per_puzzle"]
        self.assertEqual({i: v["bin"] for i, v in per.items()}, {"s-000-6x1": "[90,100]", "s-001-6x1": "[90,100]", "s-002-6x1": "[0,10)"})
        self.assertEqual(per["s-000-6x1"]["agreement_share"], 1.0)                 # 4 wrong, all the same: 6 of 6 pairs
        self.assertEqual(per["s-001-6x1"]["group"], "too few wrong tries")         # 1 wrong try
        self.assertAlmostEqual(per["s-002-6x1"]["agreement_share"], (45 + 435) / 780)
        top = r["bins"]["[90,100]"]
        # the too-few cell (base 001: 39 R, 1 W; Opus right): vote@1 = vote@2 = 0.975 < 1, vote@3 = 1
        cell = top["too few wrong tries"]
        self.assertEqual((cell["puzzles"], cell["smallest_k_reaching_opus"], cell["opus_med_mean"]), (["s-001-6x1"], 3, 1.0))
        self.assertAlmostEqual(cell["mean_vote_at_k"][1]["mean"], 0.975)
        self.assertEqual(cell["bootstrap_name"], "lookup:6x1:90:few")                         # X6
        self.assertEqual(cell["mean_vote_at_k"][1]["ci95"], [0.975, 0.975])                   # one base in the cell: the band is a point
        # base 000 (36 R, 4 W; Opus right) alone among the rest of its bin: third t1. Below k = 9 four W can tie or beat the R drawn
        t1 = top["thirds"]["t1"]
        self.assertEqual((t1["puzzles"], t1["smallest_k_reaching_opus"], t1["bootstrap_name"]), (["s-000-6x1"], 9, "lookup:6x1:90:t1"))
        self.assertAlmostEqual(t1["mean_vote_at_k"][2]["mean"], 1 - 220 / 9880)
        self.assertEqual((per["s-000-6x1"]["third"], per["s-001-6x1"]["third"]), ("t1", "few"))
        self.assertIsNone(r["bins"]["[0,10)"]["too few wrong tries"])

    def test_none_up_to_40(self):
        # base 002: no right sample, so vote@k = 0 at every k, below Opus's 1
        cell = rv.item_20(self.ctx)["6x1"]["bins"]["[0,10)"]["thirds"]["t1"]
        self.assertEqual((cell["smallest_k_reaching_opus"], cell["mean_vote_at_k"][39]["mean"]), ("none up to 40", 0.0))
        self.assertEqual(cell["bootstrap_name"], "lookup:6x1:0:t1")

    def test_the_thirds_rule_by_hand(self):
        # C1 item 20: sort by (agreement, base_id); puzzle i goes to floor(3i / n); a tie group takes its first member's third
        items = Fixture.items(bases=range(7), shapes=("6x1",))
        ctx = {"items": items, "set_id": "s"}
        shares = {"s-000-6x1": 0.4, "s-001-6x1": 0.2, "s-002-6x1": 0.1, "s-003-6x1": 0.4, "s-004-6x1": 0.5, "s-005-6x1": 0.3,
                  "s-006-6x1": 0.2}
        # sorted: 002 (0.1), 001 (0.2), 006 (0.2), 005 (0.3), 000 (0.4), 003 (0.4), 004 (0.5); floor(3i/7) = 0 0 0 1 1 2 2
        self.assertEqual(rv._thirds(ctx, shares), {"s-002-6x1": 0, "s-001-6x1": 0, "s-006-6x1": 0, "s-005-6x1": 1, "s-000-6x1": 1,
                                                    "s-003-6x1": 1, "s-004-6x1": 2})   # 003 ties 000: the lower third, 1 not 2
        self.assertEqual(rv._thirds(ctx, {"s-000-6x1": 0.5, "s-001-6x1": 0.5, "s-002-6x1": 0.5}), {f"s-00{i}-6x1": 0 for i in range(3)})

    def test_reaches_after_rounding_to_1e_9(self):
        items = Fixture.items(bases=(0,), shapes=("6x1",))
        curve = [{"acc": 1 - 1e-12}] + [{"acc": 1.0}] * 39                                    # within 1e-9 of Opus's 1 at k = 1
        ctx = {"items": items, "set_id": "s", "B": 20, "_cache": {("curve", "haiku-med", "6x1"): {"s-000": curve}}}
        cell = rv._cell(ctx, "6x1", ["s-000-6x1"], {"s-000-6x1": 1.0}, "lookup:6x1:90:t1")
        self.assertEqual(cell["smallest_k_reaching_opus"], 1)
        ctx["_cache"][("curve", "haiku-med", "6x1")] = {"s-000": [{"acc": 1 - 1e-8}] + [{"acc": 1.0}] * 39}
        self.assertEqual(rv._cell(ctx, "6x1", ["s-000-6x1"], {"s-000-6x1": 1.0}, "x")["smallest_k_reaching_opus"], 2)


# ---------------------------------------------------------------- the pilot ratios and the whole report on the fake main run

def _ladder_table():
    here = Path(__file__).resolve().parents[2]
    roots = [here]
    try:
        common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=here, capture_output=True,
                                text=True, check=True).stdout.strip()
        roots.append(Path(common).parent)
    except (OSError, subprocess.CalledProcessError):
        pass
    for root in roots:
        p = root / "data" / "raw" / "ladder-l14n-1" / "compact_table.csv"
        if p.is_file():
            return p
    return None


class PilotRatios(unittest.TestCase):

    def test_the_note_table(self):
        floors = {key: math.floor(v) for key, v in rv.PILOT_RATIO.items()}
        self.assertEqual(floors, {("opus-medium", "1x6"): 36, ("opus-medium", "6x1"): 43, ("sonnet-medium", "1x6"): 12,
                                  ("sonnet-medium", "6x1"): 14})
        self.assertEqual([round(float(rv.PILOT_RATIO[k]), 3) for k in sorted(rv.PILOT_RATIO)], [36.782, 43.910, 12.947, 14.224])

    @unittest.skipUnless(_ladder_table(), "data/raw/ladder-l14n-1/compact_table.csv is not on this machine")
    def test_recomputed_from_the_ladder_table(self):
        self.assertEqual(rv.pilot_ratios_from_table(_ladder_table()), rv.PILOT_RATIO)


class EndToEndOnTheFakeMainRun(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        tma.FakeMainRun.setUpClass()
        cls.f = tma.FakeMainRun
        man, items = main_rows.load_set(cls.f.set_dir)
        planned = main_rows.planned_requests(man, list(items.values()), ("sl", "ho", "hx"))
        built = main_rows.build(cls.f.set_dir, [cls.f.log], planned=planned)
        cls.ctx = {"rows": built["tests"], "other": built["other"], "records": main_rows.final_records([cls.f.log]), "items": items,
                   "set_id": man["set_id"], "n": 6, "k": json.loads(cls.f.k_path.read_text()), "B": 300}
        cls.res = rv.report(cls.ctx)

    def test_report_runs_and_serialises(self):
        s = json.dumps(self.res, default=str)
        self.assertEqual(set(self.res), {"note", "item_7", "item_8a", "item_8b", "item_18", "item_20", "open_questions"})
        self.assertEqual(self.res["open_questions"], {})                           # the last one pinned by Addendum C4
        self.assertNotIn("NaN", s)

    def test_k_plus_0_is_the_drivers_confirmatory_result(self):
        self.assertEqual(json.dumps(self.res["item_8b"]["rows"]["k+0"]["tests"], sort_keys=True, default=str),
                         json.dumps(self.f.res["confirmatory"]["views"]["as_deployed"]["tests"], sort_keys=True, default=str))
        kv = self.res["item_8a"]["k_values"]
        self.assertEqual(kv["t1"]["k_confirmatory"], self.f.res["k_used"]["k_o"]["6x1"])
        if kv["t1"]["k_confirmatory"] == 40:                                        # equal costs per token: k_O hits the cap here
            self.assertEqual(self.res["item_8b"]["rows"]["k+1"]["tests"]["t1"]["k_label"], "held at the limit")   # X8

    def test_items_cover_every_arm_and_the_per_piece_unit(self):
        arms = self.res["item_7"]["per_piece_accuracy"]["arms"]
        self.assertEqual(set(arms), {"haiku-med", "haiku-low", "opus-med", "opus-low", "sonnet-med", "sonnet-low", "haiku-thinking-off",
                                     "haiku-max"})
        self.assertEqual(set(self.res["item_7"]["per_piece_accuracy"]["out_of_design"]), {"haiku-med-d42-variant", "rt-haiku-med",
                                                                                         "rt-opus-med", "rt-sonnet-med"})
        lf = self.f.res["reporting"]["low_information_flag"]["per_piece_accuracy"]
        self.assertAlmostEqual(arms["haiku-med"]["mean"], lf)                       # item 5's per-piece accuracy, the same rule
        ks = self.res["item_7"]["per_piece_vote"]["k_S"]["k"]
        self.assertEqual(self.res["item_7"]["per_piece_vote"]["k_S"]["bootstrap_name"], "per_piece_vote_curve:haiku-med")   # C4 item 1
        self.assertEqual(self.res["item_7"]["per_piece_vote_curve"]["points"][ks - 1]["ci95"] if ks >= 1 else None,
                         self.res["item_7"]["per_piece_vote"]["k_S"].get("ci95"))
        cpt = self.res["item_7"]["cost_per_task"]["haiku-med"]
        self.assertEqual(cpt["unit"], "one sample (X7)")
        self.assertAlmostEqual(cpt["cost_per_task"], rc.cost_block(self.ctx, "haiku-med", "6x1")["mean"] / 6)
        cells = rv._k_cells(self.ctx)
        self.assertEqual(ks, int(cells[("S", "6x1")]["k"]))                        # item 11's k_S(6x1) = the k_table cell's here
        self.assertEqual(len(self.res["item_8b"]["vote_curve"]["per_piece_6x1"]), 40)
        for t in ("t1", "t2", "t3", "t4", "t5"):
            self.assertTrue(self.res["item_8b"]["sign_flip"][t]["ran"])


if __name__ == "__main__":
    unittest.main()
