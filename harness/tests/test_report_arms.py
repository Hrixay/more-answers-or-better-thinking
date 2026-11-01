"""report_arms (research/reporting-definitions-main.md items 10-17, 21, 24): one hand-computed case per item on small synthetic rows,
then the whole report on a fake main run (test_main_analysis.FakeMainRun), serialised. Offline only."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.analysis import bootstrap, fairness, five_tests, main_rows, report_arms as ra, scoring
from harness.analysis.curve import wilson
from harness.pareto import e3
from harness.taskgen import ledger
from harness.taskgen.freeze import write_set
from harness.tests import test_main_analysis as tma
from harness.tests.test_main_analysis import bump, chain_text, pieces_text

HAIKU, OPUS, SONNET = "claude-haiku-5-5", "claude-opus-5-5", "claude-sonnet-5-5"
MODEL = {"haiku-med": HAIKU, "haiku-low": HAIKU, "haiku-thinking-off": HAIKU, "haiku-max": HAIKU, "opus-med": OPUS, "opus-low": OPUS,
         "sonnet-med": SONNET, "sonnet-low": SONNET, "rt-haiku-med": HAIKU}
EFFORT = {"haiku-med": "medium", "haiku-low": "low", "haiku-thinking-off": "medium", "haiku-max": "max", "opus-med": "medium",
          "opus-low": "low", "sonnet-med": "medium", "sonnet-low": "low", "rt-haiku-med": "medium"}   # as the runner requests them


def items_for(bases=(0, 1), shapes=("6x1",), set_id="s"):
    return {f"{set_id}-{b:03d}-{sh}": {"id": f"{set_id}-{b:03d}-{sh}", "width": int(sh.split("x")[0]), "depth": int(sh.split("x")[1]),
                                       "base_index": b} for b in bases for sh in shapes}


class Synth:
    """Rows and their final records, built together (the record carries the usage the list cost reads)."""

    def __init__(self):
        self.rows, self.other, self.records = [], [], []

    def add(self, setup, base, shape, sample, right=True, key=None, kind="answered", tin=1000, tout=1000, cost_usd=None,
            category=None, billed=None, stop=None, fmt="ok", set_id="s"):
        iid = f"{set_id}-{base:03d}-{shape}"
        cid = f"{iid}-{ra.TAG_OF[setup]}-{sample:02d}"
        stop = stop or {"answered": "end_turn", "refusal": "refusal", "truncated": "max_tokens"}.get(kind)
        row = {"base_id": f"{set_id}-{base:03d}", "item_id": iid, "shape": shape, "setup": setup, "sample": sample, "kind": kind,
               "stop_reason": stop, "refusal_category": category, "custom_id": cid, "cost_usd": cost_usd, "preset": "l14n6"}
        answered = kind == "answered"
        if scoring.is_chain_shape(shape):
            k = key if key is not None else ("T" if right else "W")
            row.update(format_status=fmt if answered else kind, trace_key=k if answered and fmt == "ok" else None, final_key=k,
                       slip_type="none" if right else "real", correct=bool(right and answered), correct_final=bool(right and answered),
                       correct_copy_forgiven=bool(right and answered), correct_original=bool(right and answered),
                       format_status_original=fmt if answered else kind, answer_only=False)
        else:
            row.update(format_status=fmt if answered else kind, answer_key=(key or ("A" if right else "B")) if answered and fmt == "ok" else None,
                       correct=bool(right and answered), pieces_right=6 if right else 0)
        (self.rows if setup in main_rows.FIVE_TEST_ARMS.values() else self.other).append(row)
        if kind != "missing":
            self.records.append({"custom_id": cid, "final": True, "kind": kind, "stop_reason": stop, "refusal_category": category,
                                 "requested_model": MODEL[setup], "effort": EFFORT[setup], "cost_usd": cost_usd,
                                 "usage_raw": {"input_tokens": tin, "output_tokens": tout},
                                 "refusal_billed_by_rule": billed, "answer_text": "", "meta": {"setup": ra.TAG_OF[setup]}})
        return row

    def ctx(self, items, k=None, **kw):
        c = {"rows": self.rows, "other": self.other, "missing": [], "records": self.records, "all_records": list(self.records),
             "items": items, "set_id": "s", "n": 6, "k": k or {"k_o": {"6x1": 1, "1x6": 1}, "k_s": 1}, "B": 400, "draws": 200}
        c.update(kw)
        return c


class ByHand(unittest.TestCase):

    def test_item_10_exploratory_arms(self):
        s = Synth()
        for samp in range(1, 41):                                  # Haiku-low: base 0 all right, base 1 all wrong
            s.add("haiku-low", 0, "6x1", samp, True)
            s.add("haiku-low", 1, "6x1", samp, False)
        s.add("opus-med", 0, "6x1", 1, True)
        s.add("opus-med", 1, "6x1", 1, False)
        s.add("sonnet-med", 0, "6x1", 1, True)
        s.add("sonnet-med", 1, "6x1", 1, True)
        s.add("opus-low", 0, "6x1", 1, False)
        s.add("opus-low", 1, "6x1", 1, False)
        s.add("sonnet-low", 0, "6x1", 1, True)
        s.add("sonnet-low", 1, "6x1", 1, kind="refusal", category="cyber", billed=False)       # B5: free
        r = ra.item_10(s.ctx(items_for()))
        hl = r["arms"]["haiku-low 6x1"]
        self.assertEqual(hl["accuracy"]["as_deployed"], {"mean": 50.0, "n_base": 2})
        self.assertEqual(hl["format_compliance"]["format_compliance"], 1.0)
        # list cost: Haiku 1000 in x $0.10 + 1000 out x $0.50 per MTok = $0.0006; Opus $0.024; Sonnet $0.012
        self.assertAlmostEqual(hl["cost_per_puzzle_single_try"]["mean"], 0.0006)
        self.assertAlmostEqual(hl["cpc_by_k"][0]["cpc"], 0.0012)                             # (0.0006 + 0.0006) / (100/100)
        self.assertAlmostEqual(hl["cpc_by_k"][39]["cpc"], 0.048)                             # k = 40: 40 x 0.0012 / 1
        self.assertEqual([p["mean"] for p in hl["vote_curve"]["points"]][:2], [0.5, 0.5])          # report_votes' one curve (a share)
        self.assertEqual(hl["vote_curve"]["bootstrap_name"], "vote_curve:haiku-low:6x1")               # X1: arm names
        self.assertEqual(hl["cpc_by_k"][0]["share_draws_no_correct"] > 0, True)                        # X3: draws {1, 1} kept as +inf
        self.assertEqual(hl["cpc_by_k"][0]["ci95"][1], "unbounded")
        vo, vs = hl["own_k"]["vs opus-med"], hl["own_k"]["vs sonnet-med"]
        self.assertEqual((vo["k_value"]["k"], vo["k_value"]["raw_k"]), (40, 40))             # 0.024 / 0.0006 = 40
        self.assertEqual(vs["k_value"]["k"], 20)                                             # 0.012 / 0.0006 = 20
        self.assertEqual((vo["paired"]["d"], vo["paired"]["seed_name"]), (0.0, "explore:haiku-low:opus-med:6x1"))  # [100-100, 0-0]
        self.assertEqual((vs["paired"]["d"], vs["paired"]["seed_name"]), (-50.0, "explore:haiku-low:sonnet-med:6x1"))  # [0, -100]
        self.assertAlmostEqual(vo["cpc"]["cpc"], 40 * 0.0012)                                # the vote at its own k = 40
        sl = r["arms"]["sonnet-low 6x1"]
        self.assertEqual((sl["accuracy_cp95"]["x"], sl["accuracy_cp95"]["n"]), (1, 2))
        self.assertAlmostEqual(sl["cost_per_puzzle"]["mean"], 0.006)                         # (0.012 + $0 refusal) / 2
        self.assertAlmostEqual(sl["cpc"]["cpc"], 0.012)
        self.assertEqual(sl["counts"]["refusals"], 1)
        self.assertEqual((sl["paired"]["vs sonnet-med"]["d"], sl["paired"]["vs opus-low"]["d"]), (-50.0, 50.0))
        self.assertEqual(sl["paired"]["vs opus-low"]["seed_name"], "explore:sonnet-low:opus-low:6x1")

    def test_item_11_tests_3_and_5_at_6x1(self):
        s = Synth()
        for b in range(3):
            for samp in range(1, 41):
                s.add("haiku-med", b, "6x1", samp, True, cost_usd="0.0003")
        for b, right in enumerate((True, False, True)):
            s.add("sonnet-med", b, "6x1", 1, right, cost_usd="0.003")                         # k_S(6x1) = floor(0.003 / 0.0003) = 10
        s.add("opus-low", 0, "6x1", 1, False)
        s.add("opus-low", 1, "6x1", 1, kind="truncated")
        s.add("opus-low", 2, "6x1", 1, False)
        for b in range(3):                                   # the rest of the cost-only rows k_S(6x1) reads (k_step), consistent with k.json:
            for sh in ("6x1", "1x6"):                        # Opus = one Haiku sample, so k_O = 1 at both shapes
                s.add("opus-med", b, sh, 1, True, cost_usd="0.0003")
            s.add("haiku-med", b, "1x6", 1, True, cost_usd="0.0003")
        r = ra.item_11(s.ctx(items_for(bases=(0, 1, 2), shapes=("6x1", "1x6"))))
        self.assertEqual(r["k_s_6x1"]["k"], 10)
        t3 = r["t3@6x1"]["as_deployed"]
        self.assertAlmostEqual(t3["d"], 100 / 3)                                              # [0, 100, 0]
        self.assertEqual((t3["reading"], t3["seed_name"]), ("non-inferior", "t3@6x1"))
        self.assertEqual((t3["label"], r["label"]), ("unadjusted (exploratory, outside Holm)",) * 2)     # Edith r7, I1
        t5 = r["t5@6x1"]
        self.assertAlmostEqual(t5["as_deployed"]["d"], -200 / 3)                             # [-100, 0, -100]
        self.assertAlmostEqual(t5["refusals_out"]["d"], -200 / 3)
        self.assertEqual((t5["truncations_out"]["n"], t5["truncations_out"]["d"]), (2, -100.0))   # base 1 left out
        self.assertEqual(t5["truncations_out"]["reading"], "worse by more than the margin")
        self.assertEqual(t5["truncations_out"]["p"], 1.0)
        seed = bootstrap.derive_seed(20261011, "t5@6x1")
        self.assertEqual(bootstrap.paired_bca([-100.0, 0.0, -100.0], B=400, seed=seed)["ci95"], tuple(t5["as_deployed"]["ci95"]))

    def test_item_12_clopper_pearson(self):
        lo, hi = ra.clopper_pearson(0, 80)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 1 - 0.025 ** (1 / 80), places=12)                        # Addendum A0: 4.51% at n = 80
        self.assertAlmostEqual(ra.clopper_pearson(80, 80)[0], 0.025 ** (1 / 80), places=12)
        lo, hi = ra.clopper_pearson(5, 10)                                                    # textbook values
        self.assertAlmostEqual(lo, 0.187086, places=6)
        self.assertAlmostEqual(hi, 0.812914, places=6)
        s = Synth()
        for b in range(3):
            s.add("opus-med", b, "1x6", 1, False)
        r = ra.item_12(s.ctx(items_for(bases=(0, 1, 2), shapes=("1x6",))))
        om = r["one_try_arms"]["opus-med 1x6"]
        self.assertEqual((om["x"], om["n"], om["accuracy"]), (0, 3, 0.0))
        self.assertAlmostEqual(om["cp95"][1], 100 * (1 - 0.025 ** (1 / 3)), places=9)
        self.assertEqual(r["multi_try_arms"], {})                                            # no multi-try arm here
        s2 = Synth()
        for b, right in ((0, 40), (1, 20)):                                                  # Haiku-low: 100 and 50 points
            for samp in range(1, 41):
                s2.add("haiku-low", b, "6x1", samp, samp <= right)
        hl = ra.item_12(s2.ctx(items_for()))["multi_try_arms"]["haiku-low 6x1"]
        self.assertEqual((hl["mean"], hl["n_base"], hl["bootstrap_name"]), (75.0, 2, "accuracy:haiku-low:6x1"))   # X6
        self.assertEqual(hl["ci95"], [50.0, 100.0])                                          # draws {1, 1} and {0, 0}, about 1/4 each

    def test_item_15_near_ceiling_label(self):
        s = Synth()
        s.add("opus-med", 0, "6x1", 1, True)
        s.add("opus-med", 0, "1x6", 1, True)
        s.add("opus-med", 1, "6x1", 1, True)
        s.add("opus-med", 1, "1x6", 1, False)
        r = ra.item_15(s.ctx(items_for(shapes=("6x1", "1x6"))))
        self.assertEqual((r["label"], r["on"], r["re_decided_on_main_run"], r["beside_tests"]),
                         ("near ceiling (Amendment 1)", True, False, ["t1", "t2"]))
        self.assertEqual(r["opus_med_pooled_accuracy_main_run"]["mean"], 0.75)               # base 0: 1, base 1: (1 + 0) / 2

    def test_item_16_rates_missing_retries_long_prompts(self):
        s = Synth()
        s.add("opus-med", 0, "6x1", 1, kind="refusal", category="cyber", billed=False, tout=0)
        s.add("opus-med", 1, "6x1", 1, kind="truncated", tin=0, tout=1000)                    # $0.02 at list price
        s.add("opus-med", 2, "6x1", 1, kind="missing")
        s.add("sonnet-med", 0, "6x1", 1, kind="empty", stop="end_turn")                       # I3: not answered/refusal/truncated
        s.add("sonnet-med", 1, "6x1", 1, True, tin=100_001, tout=0)                           # over 100,000 prompt tokens
        s.add("sonnet-med", 2, "6x1", 1, True, tin=100_000, tout=0)                           # exactly 100,000: not over
        for b in range(3):                                                                     # base 0: sample 40 missing
            for samp in range(1, 41):
                s.add("haiku-med", b, "6x1", samp, True, kind="missing" if (b, samp) == (0, 40) else "answered")
        all_records = list(s.records) + [
            {"kind": "error", "custom_id": "x-rthm-01", "attempt": 1, "final": False, "meta": {"setup": "rthm"},
             "error": {"type": "rate_limit", "status": 429}},
            {"kind": "answered", "custom_id": "x-rthm-01", "attempt": 2, "final": True, "meta": {"setup": "rthm"}},
            {"kind": "error", "custom_id": "x-rthm-02", "attempt": 3, "final": False, "meta": {"setup": "rthm"},
             "error": {"type": "api_error", "status": 503}},
            {"kind": "batch_submitting", "keys": {"y-hl-01": "y-hl-01@1"}, "final": False},
            {"kind": "error", "custom_id": "y-hl-01", "final": False, "batch_id": "b1", "meta": {"setup": "hl"},
             "error": {"type": "expired"}},
            {"kind": "batch_submitting", "keys": {"y-hl-01": "y-hl-01@2"}, "final": False}]
        for i, (kind, stop) in enumerate((("answered", "end_turn"), ("refusal", "refusal"), ("truncated", "max_tokens"), ("error", None))):
            s.records.append({"custom_id": f"s-000-1x6-s1-d{i}", "final": True, "kind": kind, "stop_reason": stop,
                              "refusal_category": "cyber" if kind == "refusal" else None, "requested_model": OPUS,
                              "usage_raw": {"input_tokens": 10, "output_tokens": 0}, "meta": {"setup": "es"}})
        for b, kind in ((0, "answered"), (1, "missing")):                                      # E3 chain rows: one unfinished
            s.rows.append({"setup": "e3", "shape": "1x6", "base_id": f"s-{b:03d}", "item_id": f"s-{b:03d}-1x6", "kind": kind,
                           "stop_reason": "end_turn", "step_correct": [kind == "answered"] * 6, "correct": kind == "answered"})
        r = ra.item_16(s.ctx(items_for(bases=(0, 1, 2)), all_records=all_records))
        om = r["rates"]["opus-med 6x1"]
        self.assertEqual(om["designed_calls"], 3)
        cy = om["refusals_by_category"]["cyber"]
        self.assertEqual((cy["count"], cy["rate"], cy["wilson95"], cy["list_cost_usd"]), (1, 1 / 3, list(wilson(1, 3)), "0"))
        self.assertEqual((om["truncations"]["count"], om["truncations"]["list_cost_usd"]), (1, "0.02"))
        self.assertEqual(om["missing"]["count"], 1)
        sm = r["rates"]["sonnet-med 6x1"]
        self.assertEqual(sm["missing"]["count"], 0)                                          # r7: an empty final record is not missing
        self.assertEqual((sm["failures_by_kind"]["empty"]["count"], sm["failures_by_kind"]["empty"]["rate"]), (1, 1 / 3))
        e3r = r["e3"]
        self.assertEqual((e3r["calls_made"], e3r["label"]), (4, ra.E3_RATES_LABEL))           # C1: over the E3 calls made
        self.assertEqual((e3r["refusals_by_category"]["cyber"]["count"], e3r["refusals_by_category"]["cyber"]["rate"]), (1, 1 / 4))
        self.assertEqual((e3r["truncations"]["count"], e3r["failures_by_kind"]["error"]["count"]), (1, 1))
        self.assertEqual((e3r["missing_chains"]["count"], e3r["missing_chains"]["rate"]), (1, 1 / 2))
        self.assertEqual(r["vote_uses_samples_available"]["t1"], {"shape": "6x1", "base_puzzles_with_fewer_than_40_samples": 1,
                                                                  "ids": ["s-000"]})
        self.assertIsInstance(r["exclude_missing_view"], dict)                                # something is missing: the view runs
        rt = r["retries_and_batch_failures"]
        self.assertEqual(rt["realtime_retry_events_by_status"]["rt-haiku-med"], {"429": 1, "429_followed_by_a_retry": 1, "5xx": 1})
        self.assertEqual(rt["batch_errored_expired_canceled"]["haiku-low"], {"expired": 1, "resubmits": 1})
        self.assertEqual(r["requests_over_100k_prompt_tokens"]["by_setup"], {"sonnet-med": 1})
        s2 = Synth()
        s2.add("opus-med", 0, "6x1", 1, True)
        self.assertEqual(ra.item_16(s2.ctx(items_for(bases=(0,))))["exclude_missing_view"], "no missing items in the five tests' arms")
        s3 = Synth()
        s3.add("opus-med", 0, "6x1", 1, True)                                                 # 1 row, 2 designed: refused
        with self.assertRaises(ValueError):
            ra.item_16(s3.ctx(items_for(bases=(0, 1))))

    def test_item_16_exclude_missing_view_by_hand(self):
        # Edith driver review r8: base 0 has 39 Haiku samples (20 A right, 19 B wrong; sample 40 missing) and votes over its 39 at k = 39
        # (A wins: 100; as_deployed pads a vote for nothing and gives (1 + 20 x 1/2 + 19) / 40 = 75); base 1's opus-med call is missing,
        # so base 1 leaves t1's pair; base 2's opus-med "empty" and base 3's "error" final records are real results, kept and wrong.
        s = Synth()
        for samp in range(1, 41):
            s.add("haiku-med", 0, "6x1", samp, samp <= 20, kind="missing" if samp == 40 else "answered")
            for b in (1, 2, 3):
                s.add("haiku-med", b, "6x1", samp, True)
        s.add("opus-med", 0, "6x1", 1, True)
        s.add("opus-med", 1, "6x1", 1, kind="missing")
        s.add("opus-med", 2, "6x1", 1, kind="empty", stop="end_turn")
        s.add("opus-med", 3, "6x1", 1, kind="error", stop=None)
        ctx = s.ctx(items_for(bases=(0, 1, 2, 3)), k={"k_o": {"6x1": 39, "1x6": 1}, "k_s": 1})
        self.assertEqual(five_tests.vote_scores(ctx["rows"], "6x1", 39)["s-000"], 75.0)          # as_deployed, for contrast
        ex = ra.exclude_missing_view(ctx)
        t1 = ex["tests"]["t1"]
        self.assertEqual((t1["n"], ex["missing_left_out"]), (3, 2))                            # bases 0, 2, 3: [0, 100, 100]
        self.assertAlmostEqual(t1["d"], 200 / 3)
        self.assertEqual(ex["tests"]["t3"]["p"], 1.0)                                          # no 1x6 rows: not run

    def test_item_14_t_plus_g_minus_by_hand(self):
        # Each try's steps, by kind and blame (no house step). Classes swapped: T+ = repick2, ..., avg_donors, rank_move, count_move;
        # G- = two_clause, compare_move; sweep stays T; other kinds are in neither group.
        steps = {"haiku-med": [("avg_donors", "kind"), ("repick2", "none"), ("two_clause", "decoy_confusion"), ("compare_move", "none"),
                               ("rank_move", "none")],
                 "opus-med": [("avg_donors", "none"), ("sweep", "none"), ("two_clause", "none"), ("compare_move", "kind")]}

        class Stub:
            def place(self, r, first_slip):
                return {"unplaceable": None, "status": "ok",
                        "steps": [{"kind": k, "cls": "?", "blame": b, "house_should_act": False} for k, b in steps[r["setup"]]]}
        rows = [{"setup": arm, "preset": "l14n6", "base_id": f"s-{b:03d}", "custom_id": f"s-{b:03d}-{arm}"}
                for arm in steps for b in range(3)]
        out = ra.t_plus_g_minus({"rows": rows}, Stub(), 50)
        hand = []
        for b in range(3):                     # Haiku: T+ 3 steps (avg_donors, repick2, rank_move), 1 slip; G- 2 steps, 1 slip
            hand.append(fairness.SlipCounts("l14n6", f"s-{b:03d}", fairness.HAIKU, 3, 1, 2, 1, 5, 0, 0, 5, 0))
            hand.append(fairness.SlipCounts("l14n6", f"s-{b:03d}", fairness.OPUS, 2, 0, 2, 1, 4, 0, 0, 4, 0))   # Opus: T+ 2, 0; G- 2, 1
        self.assertTrue(out["computed"])
        self.assertEqual(json.dumps(out["indices"], sort_keys=True, default=str),
                         json.dumps(fairness.fairness_indices(sorted(hand, key=lambda x: (x.preset, x.base_id, x.model)),
                                                              comparison=fairness.OPUS, B=50, unplaceable={}), sort_keys=True, default=str))

    def test_item_17_format_flag_exact_at_5_percent(self):
        s = Synth()
        for samp in range(1, 21):                                                            # 1 of 20 not ok: exactly 5%, no flag
            s.add("haiku-low", 0, "6x1", samp, True, fmt="ok" if samp > 1 else "missing_piece")
        for samp in range(1, 21):                                                            # 2 of 20: 10%, flag
            s.add("haiku-max", 0, "6x1", samp, True, fmt="ok" if samp > 2 else "missing_piece")
        s.add("opus-med", 0, "6x1", 1, kind="refusal")                                        # no answered try: not assessable
        r = ra.item_17(s.ctx(items_for(bases=(0,))))["flags"]
        self.assertGreater(1 - 19 / 20, 0.05)                                                 # the float trap the integer test avoids
        self.assertEqual((r["haiku-low 6x1"]["fires"], r["haiku-max 6x1"]["fires"], r["opus-med 6x1"]["fires"]), (False, True, None))


class RealPuzzles(unittest.TestCase):
    """Items 13, 14 and 21 place real replies, so they use a small frozen l14n6 set."""

    @classmethod
    def setUpClass(cls):
        td = Path(tempfile.mkdtemp())
        write_set(td / "s", "ledger", "l14n6", "t-set", 3, "d31", "scratch")
        cls.man, cls.items = main_rows.load_set(td / "s")

    def ctx_from(self, specs):
        """specs: (setup tag, base, shape, sample, text or None for a refusal) -> rows scored by main_rows.score_row."""
        rows, other, recs = [], [], []
        for tag, base, shape, sample, text in specs:
            it = self.items[f"t-set-{base:03d}-{shape}"]
            meta = {"set_id": "t-set", "base_index": base, "item_id": it["id"], "width": it["width"], "depth": it["depth"],
                    "setup": tag, "sample": sample, "setting": "l14n6"}
            rec = {"custom_id": f"{it['id']}-{tag}-{sample:02d}", "final": True, "kind": "answered" if text else "refusal",
                   "stop_reason": "end_turn" if text else "refusal", "answer_text": text or "", "meta": meta,
                   "requested_model": MODEL[ra.ARM_OF_TAG[tag]], "usage_raw": {"input_tokens": 10, "output_tokens": 10}}
            name = ra.ARM_OF_TAG[tag]
            (rows if tag in main_rows.FIVE_TEST_ARMS else other).append(main_rows.score_row(rec, it, name))
            recs.append(rec)
        return {"rows": rows, "other": other, "missing": [], "records": recs, "all_records": recs, "items": self.items,
                "set_id": "t-set", "n": 6, "k": {"k_o": {"6x1": 1, "1x6": 1}, "k_s": 1}, "B": 200, "draws": 50}

    def test_item_13_first_slip_repeat_share(self):
        p6 = self.items["t-set-000-6x1"]["answer"]
        c6 = self.items["t-set-000-1x6"]["chains"][0]["states"]
        same6 = pieces_text([bump(p6[0])] + p6[1:])
        same1 = chain_text(c6[:2] + [bump(c6[2])] + c6[3:])                                 # first slip at step 3
        specs = [("hm", 0, "6x1", 1, same6), ("hm", 0, "6x1", 2, same6), ("hm", 0, "6x1", 3, pieces_text(p6[:1] + [bump(p6[1])] + p6[2:])),
                 ("hm", 0, "6x1", 4, pieces_text(p6)), ("hm", 0, "6x1", 5, None),           # a right try and a refusal: no pair
                 ("hm", 0, "1x6", 1, same1), ("hm", 0, "1x6", 2, same1), ("hm", 0, "1x6", 3, chain_text(c6[:4] + [bump(c6[4])] + c6[5:])),
                 ("hm", 0, "1x6", 4, chain_text(c6))]
        r = ra.item_13(self.ctx_from(specs))
        for shape in ("6x1", "1x6"):
            self.assertEqual((r[shape]["pairs"], r[shape]["agree"], r[shape]["wrong_placeable_tries"]), (3, 1, 3))
        self.assertEqual(r["both_shapes"], {"pairs": 6, "agree": 2, "share": 2 / 6})

    def test_item_14_slip_tables(self):
        it = self.items["t-set-000-6x1"]
        p6 = it["answer"]
        kinds = {lab: k for lab, k, _ in it["rulebook"]}
        c6 = self.items["t-set-000-1x6"]["chains"][0]["states"]
        specs = [("om", 0, "6x1", 1, pieces_text([bump(p6[0])] + p6[1:])), ("om", 0, "6x1", 2, None), ("om", 0, "6x1", 3, "Answer: nothing"),
                 ("om", 0, "1x6", 1, chain_text(c6)), ("om", 0, "1x6", 2, chain_text(c6[:-1] + [bump(c6[-1])])),
                 ("om", 0, "1x6", 3, chain_text(c6[:2] + [bump(c6[2])] + c6[3:])),
                 ("hm", 0, "1x6", 1, chain_text(c6)), ("sm", 0, "1x6", 1, chain_text(c6))]
        r = ra.item_14(self.ctx_from(specs))
        t = r["tables"]["opus-med 6x1"]["local_steps"]
        k1 = kinds[it["chains"][0]["names"][0]]                                              # piece 1's rule kind, read from the item
        self.assertEqual(sum(v["at_risk"] for kk, v in t.items() if kk.startswith("class ")), 6)   # one placed try, 6 pieces
        self.assertEqual(sum(v["slips"] for kk, v in t.items() if kk.startswith("class ")), 1)
        self.assertEqual(t[k1]["slips"], 1)
        self.assertEqual(t["house"]["steps_checked"], 6)
        self.assertEqual(t["unplaceable_by_reason"]["refusal"], 1)
        self.assertEqual(t["unplaceable"]["tries"], 2)                                       # the refusal and "Answer: nothing"
        split = r["by_final_answer"]["opus-med 1x6"]
        self.assertEqual((split["correct_final True"]["tries"], split["correct_final False"]["tries"]), (2, 1))  # step-3 slip keeps the final
        six = r["by_final_answer"]["opus-med 6x1"]                                            # C1: at 6x1 correct_final = correct
        self.assertEqual((six["correct_final True"]["tries"], six["correct_final False"]["tries"]), (0, 3))
        self.assertEqual(six["correct_final False"]["field"], "correct (= correct_final at 6x1)")
        rel = ra._relabel({"unplaceable": None, "steps": [{"kind": k, "cls": "?"} for k in
                                                          ("repick2", "avg_donors", "rank_move", "count_move", "two_clause", "compare_move")]})
        self.assertEqual([st["cls"] for st in rel["steps"]], ["T", "T", "T", "T", "G", "G"])
        self.assertEqual(r["t_plus_g_minus"]["label"], "T+/G- sensitivity split: reported, never a flag")

    def test_item_21_e3_fixed_3(self):
        steps = [st for st in e3.chain_steps([(self.man, list(self.items.values()))])]
        by = {(st.base_index, st.k): st for st in steps}

        def ans(st, right=True, alt=1):
            vals = [int(x) for x in st.truth.split(",")]
            return f"Answer: {ledger.fmt(vals if right else bump(vals, alt))}"
        plan = {0: {1: [ans(by[0, 1])] * 2,                                                   # lead-by-2 after 2 agreeing: exact, 1
                    2: [ans(by[0, 2]), ans(by[0, 2], False), ans(by[0, 2])],               # plurality right: 1
                    3: [ans(by[0, 3], False, 1), ans(by[0, 3], False, 2), ans(by[0, 3])],   # three-way tie: 1/3
                    4: ["no answer here", ans(by[0, 4]), ans(by[0, 4], False)],            # unreadable + 1-1 tie: 1/2
                    5: [ans(by[0, 5]), ans(by[0, 5]), ans(by[0, 5], False), ans(by[0, 5], False)],  # 4th draw ignored: 1
                    6: [ans(by[0, 6]), "x", "y"]},                                          # plurality among the readable: 1
                1: {1: ["x", "y", "z"], **{k: [ans(by[1, k])] * 2 for k in range(2, 7)}},  # all 3 unreadable: wrong, product 0
                2: {1: [ans(by[2, 1])], **{k: [ans(by[2, k])] * 2 for k in range(2, 7)}}}  # 1 draw only: the readable draws present (C1)
        recs = []
        for base, ks in plan.items():
            for k, texts in ks.items():
                st = by[base, k]
                for d, text in enumerate(texts, 1):
                    recs.append({"custom_id": e3.custom_id(st.item_id, k, d), "final": True, "kind": "answered", "answer_text": text,
                                 "requested_model": e3.E3_MODEL, "effort": e3.E3_EFFORT,
                                 "meta": {"setup": "es", "item_id": st.item_id, "step": k, "draw": d, "set_id": "t-set",
                                          "base_index": base, "setting": "l14n6"}})
        ctx = {"rows": [], "other": [], "records": recs, "items": self.items, "set_id": "t-set", "n": 6}
        r = ra.item_21(ctx)
        self.assertAlmostEqual(r["per_base"]["t-set-000"]["fixed3"], 100 / 6)                 # 1 x 1 x 1/3 x 1/2 x 1 x 1
        self.assertEqual([s["credit"] for s in r["per_base"]["t-set-000"]["steps"]][:4], [1.0, 1.0, 1 / 3, 0.5])
        self.assertEqual(r["per_base"]["t-set-001"]["fixed3"], 0.0)
        b2 = r["per_base"]["t-set-002"]
        self.assertEqual((b2["fixed3"], b2["steps"][0]["credit"], b2["steps"][0]["fewer_than_3"]), (100.0, 1.0, True))
        self.assertFalse(b2["steps"][1]["fewer_than_3"])                                      # the 2-agreeing stop is exact
        self.assertAlmostEqual(r["mean_fixed3"], (100 / 6 + 0 + 100) / 3)
        none = ra.item_21(dict(ctx, records=[x for x in recs if not (x["meta"]["base_index"] == 0 and x["meta"]["step"] == 1)]))
        self.assertEqual(none["per_base"]["t-set-000"]["steps"][0]["credit"], 0.0)            # no draw at all: the step is wrong


class Item24ByHand(unittest.TestCase):

    def test_item_24_table_medians_and_chart(self):
        s = Synth()
        for b, (r6, r1) in enumerate(((40, 40), (20, 30), (0, 10))):                          # Haiku-medium right tries per base
            for samp in range(1, 41):
                s.add("haiku-med", b, "6x1", samp, samp <= r6, cost_usd="0.0003")
                s.add("haiku-med", b, "1x6", samp, samp <= r1, cost_usd="0.0003")
        for b in range(3):                                   # logged (Batch) costs, which k reads: k_O(6x1) = 0.0006 / 0.0003 = 2,
            for sh, om, sm in (("6x1", "0.0006", "0.012"), ("1x6", "0.0009", "0.0003")):   # k_O(1x6) = 3, k_S = 1, k_S(6x1) = 40
                s.add("opus-med", b, sh, 1, b < 2, cost_usd=om)
                s.add("sonnet-med", b, sh, 1, True, cost_usd=sm)
                s.add("opus-low", b, sh, 1, False)
        r = ra.item_24(s.ctx(items_for(bases=(0, 1, 2), shapes=("6x1", "1x6")), k={"k_o": {"6x1": 2, "1x6": 3}, "k_s": 1}))
        self.assertEqual(r["table"]["haiku-med 6x1"]["vote_at_own_k"]["k_S"]["k"], 40)    # k_S(6x1): floor(0.012 / 0.0003) held to 40
        hm6, hm1 = r["table"]["haiku-med 6x1"], r["table"]["haiku-med 1x6"]
        self.assertEqual((hm6["accuracy_mean"], hm6["median_over_puzzles"], hm1["median_over_puzzles"]), (50.0, 50.0, 75.0))
        self.assertEqual(r["haiku_median_pooled"]["haiku-med"], 62.5)                         # median of 100, 50, 0, 100, 75, 25
        v = hm6["vote_at_own_k"]["k_O"]                                                       # k = 2: base 1 (20/20) is (190 + 400/2)/780
        self.assertEqual(v["k"], 2)
        self.assertAlmostEqual(v["mean"], (100 + 50 + 0) / 3)
        self.assertEqual((hm6["accuracy_interval"]["bootstrap_name"], hm6["accuracy_interval"]["mean"]), ("accuracy:haiku-med:6x1", 50.0))
        self.assertEqual(v["bootstrap_name"], "vote_curve:haiku-med:6x1")
        self.assertAlmostEqual(v["cost_per_puzzle"]["mean"], 2 * 0.0006)                     # 9b: k x the per-sample list cost
        om = r["table"]["opus-med 6x1"]["accuracy_cp95"]
        self.assertEqual((om["x"], om["n"]), (2, 3))
        lo, hi = ra.clopper_pearson(2, 3)
        self.assertEqual(om["cp95"], [100 * lo, 100 * hi])
        self.assertAlmostEqual(r["table"]["opus-med 6x1"]["cost_per_puzzle"]["mean"], 0.024)   # list cost from usage, not cost_usd
        self.assertAlmostEqual(r["table"]["opus-med 6x1"]["cpc"]["cpc"], 0.036)                # 3 x 0.024 / 2 right
        self.assertEqual(r["table"]["opus-low 6x1"]["cpc"]["cpc"], "undefined (no correct answer)")
        line = r["chart"]["6x1"]["haiku_med_vote_line"]
        self.assertEqual([p["k"] for p in line], list(range(1, 41)))
        self.assertAlmostEqual(line[9]["cost_per_puzzle"], 10 * 0.0006)
        self.assertEqual({p["arm"] for p in r["chart"]["6x1"]["points"]}, {"haiku-med", "opus-med", "sonnet-med", "opus-low"})


class EndToEnd(unittest.TestCase):
    """The whole report on the fake main run (every arm, refusals, truncations, repeats, E3), serialised."""

    @classmethod
    def setUpClass(cls):
        tma.FakeMainRun.setUpClass()
        f = tma.FakeMainRun
        man, items = main_rows.load_set(f.set_dir)
        planned = main_rows.planned_requests(man, list(items.values()), ("sl", "ho", "hx"))
        built = main_rows.build(f.set_dir, [f.log], planned=planned)
        all_records = [json.loads(ln) for ln in f.log.read_text().splitlines() if ln.strip()]
        cls.ctx = {"rows": built["tests"], "other": built["other"], "missing": built["missing"], "records": main_rows.final_records([f.log]),
                   "all_records": all_records, "items": items, "set_id": man["set_id"], "n": 6, "k": json.loads(f.k_path.read_text()),
                   "B": 200, "draws": 40}
        cls.res = ra.report(cls.ctx)

    def test_report_runs_and_serialises(self):
        text = json.dumps(self.res, default=str)
        for key in ("item_10", "item_11", "item_12", "item_13", "item_14", "item_15", "item_16", "item_17", "item_21", "item_24"):
            self.assertIn(key, self.res)
        self.assertGreater(len(text), 1000)
        self.assertEqual(self.res["open_questions"], {})                                     # every question answered by Addendum C

    def test_a_few_numbers_line_up_with_the_run(self):
        r = self.res
        self.assertEqual(r["item_16"]["rates"]["haiku-med 6x1"]["designed_calls"], 120)       # 3 puzzles x 40
        self.assertEqual(r["item_16"]["exclude_missing_view"], "no missing items in the five tests' arms")         # the fake run lost nothing
        self.assertIn("haiku-low 6x1", r["item_10"]["arms"])
        self.assertEqual(set(r["item_11"]["t5@6x1"]), set(scoring.VIEWS))
        self.assertTrue(r["item_15"]["on"])
        self.assertEqual(len(r["item_21"]["per_base"]), 3)
        self.assertIn("e3 1x6", r["item_24"]["table"])
        for row in r["item_12"]["one_try_arms"].values():
            self.assertTrue(row["cp95"][0] <= row["accuracy"] <= row["cp95"][1])


if __name__ == "__main__":
    unittest.main()
