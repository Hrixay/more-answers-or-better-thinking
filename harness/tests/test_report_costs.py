"""report_costs (research/reporting-definitions-main.md items 9a-9h, 19, 22, 23): one hand-computed case per item on small synthetic
rows and records, and one end-to-end call on the fake main run (test_main_analysis.FakeMainRun). Offline only."""

import json
import math
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from harness.analysis import main_rows, report_costs as rc
from harness.pareto import prices
from harness.tests import test_main_analysis as tma

SET = "s"
HAIKU, OPUS, SONNET = "claude-haiku-5-5", "claude-opus-5-5", "claude-sonnet-5-5"
ARM = {"hm": "haiku-med", "om": "opus-med", "sm": "sonnet-med", "ol": "opus-low"}
MODEL = {"hm": HAIKU, "om": OPUS, "sm": SONNET, "ol": OPUS, "hx": HAIKU, "rthm": HAIKU}


def record(cid, tag, base, shape, sample, tin, tout, kind="answered", text="x", **kw):
    w, d = shape.split("x")
    r = {"custom_id": cid, "final": True, "kind": kind, "requested_model": MODEL.get(tag, HAIKU), "effort": "medium",
         "meta": {"setup": tag, "set_id": SET, "base_index": base, "width": int(w), "depth": int(d),
                  "item_id": f"{SET}-{base:03d}-{shape}", "sample": sample},
         "usage_raw": {"input_tokens": tin, "output_tokens": tout}, "cost_usd": "0.5", "answer_text": text}
    r.update(kw)
    return r


def row(cid, tag, base, shape, sample, key, right_key="a", kind="answered"):
    r = {"custom_id": cid, "tag": tag, "setup": ARM[tag], "base_id": f"{SET}-{base:03d}", "shape": shape, "sample": sample,
         "kind": kind, "stop_reason": "end_turn", "correct": key == right_key}
    if shape.startswith("1x"):
        r.update(format_status="ok", trace_key=key, final_key=key)
    else:
        r["answer_key"] = key
    return r


def make_ctx(B=200):
    """Bases 0 and 1, both shapes. Haiku-medium x40 (1,000 in / 0 out = $0.0001 each): base 0 all right ("a"), base 1 alternating
    wrong "b" / "c". Opus-medium (3,500 in = $0.014): base 0 wrong, base 1 right. Sonnet-medium (100 in = $0.0002): both wrong.
    Opus-low (100 in = $0.0004): both right."""
    rows, recs = [], []
    for shape in ("6x1", "1x6"):
        for base in (0, 1):
            for s in range(1, 41):
                cid = f"{SET}-{base:03d}-{shape}-hm-{s:02d}"
                key = "a" if base == 0 else ("b" if s % 2 else "c")
                recs.append(record(cid, "hm", base, shape, s, 1000, 0))
                rows.append(row(cid, "hm", base, shape, s, key))
            for tag, tin, key in (("om", 3500, "z" if base == 0 else "a"), ("sm", 100, "z"), ("ol", 100, "a")):
                cid = f"{SET}-{base:03d}-{shape}-{tag}-01"
                recs.append(record(cid, tag, base, shape, 1, tin, 0))
                rows.append(row(cid, tag, base, shape, 1, key))
    return {"rows": rows, "other": [], "records": recs, "items": {}, "set_id": SET, "n": 6,
            "k": {"k_o": {"6x1": 5, "1x6": 5}, "k_s": 2}, "run_dir": None, "B": B}


class HandComputed(unittest.TestCase):

    def test_9a_list_cost_per_call_with_b5_free_refusals(self):
        td = Path(tempfile.mkdtemp())
        (td / "ledger.jsonl").write_text(json.dumps({"event": "commit", "key": "r4@1", "free_by_rule": True}) + "\n")
        recs = [record("r1", "hm", 0, "6x1", 1, 1000, 2000, cost_usd="0.00055"),                # 1000 x 0.10 + 2000 x 0.50 = $0.0011
                record("r2", "om", 0, "6x1", 1, 100, 0, kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False),
                record("r3", "sm", 0, "6x1", 1, 100, 0, kind="refusal", refusal_category="bio", refusal_billed_by_rule=True),
                record("r4", "om", 1, "6x1", 1, 100, 0, kind="refusal", refusal_category="none"),        # free by the ledger
                record("r5", "hm", 1, "6x1", 1, 0, 0, usage_raw={"input_tokens": 0, "output_tokens": 0,
                                                                "cache_read_input_tokens": 1000}),
                record("r6", "hm", 1, "6x1", 2, 0, 0, kind="error", usage_raw=None, cost_usd="0"),     # C1 9a: no usage, $0, counted
                record("r7", "rthm", 0, "6x1", 1, 1000, 0, cost_usd="0.0001")]                       # C1 9a: real time (list)
        out = rc.item_9a({"records": recs, "run_dir": td, "rows": [], "other": []})
        pc = out["per_call"]
        self.assertEqual(Decimal(pc["r1"]["list_usd"]), Decimal("0.0011"))
        self.assertEqual((pc["r1"]["batch_usd_logged"], pc["r1"]["batch_label"]), ("0.00055", "Batch"))
        self.assertEqual(Decimal(pc["r2"]["list_usd"]), 0)
        self.assertEqual(Decimal(pc["r3"]["list_usd"]), Decimal("0.0002"))                     # 100 x $2 / MTok, billed (bio)
        self.assertEqual(Decimal(pc["r4"]["list_usd"]), 0)
        self.assertTrue(pc["r4"]["free_b5"] and out["ledger_read_for_free_by_rule"])
        self.assertEqual(Decimal(pc["r5"]["list_usd"]), Decimal("0.00001"))                    # 1000 cache reads x $0.01 / MTok
        self.assertEqual((Decimal(pc["r6"]["list_usd"]), pc["r6"]["no_usage"], out["records_without_usage"]), (0, True, 1))
        self.assertEqual((pc["r7"]["batch_label"], Decimal(pc["r7"]["list_usd"])), ("real time (list)", Decimal("0.0001")))
        self.assertEqual(out["by_arm_shape"]["rt-haiku-med:6x1"]["batch_label"], "real time (list)")
        self.assertEqual(out["by_arm_shape"]["opus-med:6x1"]["free_b5_refusals"], 2)
        self.assertEqual(out["by_arm_shape"]["haiku-med:6x1"]["records_without_usage"], 1)
        self.assertEqual(out["price_table_date"], prices.PRICE_TABLE_DATE)                 # whatever date the pinned table carries
        self.assertEqual(rc.list_cost(dict(recs[1], refusal_billed_by_rule=None, free_by_rule=True)), 0)   # marked on the record

    def test_9b_dollars_per_puzzle_with_no_record_calls_at_0(self):
        ctx = make_ctx()
        ctx["rows"].append(row(f"{SET}-002-6x1-om-01", "om", 2, "6x1", 1, None, kind="missing"))   # X4: $0 and the puzzle stays in
        drop = f"{SET}-001-6x1-hm-40"
        ctx["records"] = [r for r in ctx["records"] if r["custom_id"] != drop]                    # a Haiku sample with no record: $0
        out = rc.item_9b(ctx)["arms"]
        om = out["opus-med:6x1"]
        self.assertAlmostEqual(om["mean"], 0.028 / 3)                                          # (0.014 + 0.014 + 0) / 3
        self.assertAlmostEqual(om["median"], 0.014)
        self.assertEqual((om["n_bases"], om["calls_without_record"]), (3, 1))
        hm = out["haiku-med:6x1"]
        self.assertEqual((hm["how"], hm["calls_without_record"]), ("per_sample", 1))
        self.assertAlmostEqual(hm["mean"], (0.0001 + 39 * 0.0001 / 40) / 2)                    # base 1: 39 real samples over the designed 40
        self.assertAlmostEqual(hm["vote_at_test_k"]["t1"]["mean"], 5 * hm["mean"])             # k_O(6x1) = 5
        self.assertEqual(len(hm["vote_mean_by_k"]), 40)
        self.assertAlmostEqual(hm["vote_mean_by_k"][39], 40 * hm["mean"])
        self.assertAlmostEqual(out["haiku-med:1x6"]["vote_at_test_k"]["t3"]["mean"], 0.0002)  # k_S = 2
        self.assertAlmostEqual(out["opus-med:1x6"]["batch_mean"], 0.5)
        self.assertEqual(out["opus-med:1x6"]["batch_label"], "Batch")

    def test_9c_cost_per_correct_answer_keeps_infinite_draws(self):
        out = rc.item_9c(make_ctx())["arms"]
        om = out["opus-med:6x1"]
        self.assertAlmostEqual(om["cpc"], 0.028)                                              # $0.028 / 1 right
        self.assertEqual(om["ci95"][1], "unbounded")                                          # X3: draws {0, 0} have none right: +inf, kept
        self.assertTrue(0.1 < om["share_draws_no_correct"] < 0.4)                             # about 1/4
        self.assertAlmostEqual(om["ci95"][0], 0.014)                                          # draws {1, 1}: $0.028 / 2
        self.assertEqual(out["sonnet-med:6x1"]["cpc"], rc.UNDEFINED_CPC)
        self.assertEqual(out["sonnet-med:6x1"]["ci95"], ["unbounded", "unbounded"])
        self.assertAlmostEqual(out["opus-low:1x6"]["cpc"], 0.0004)                            # $0.0008 / 2 right
        v = out["haiku-med:6x1"]["vote_by_k"]
        self.assertAlmostEqual(v[1]["cpc"], 0.0002)                                           # 2 x $0.0001 / (100 + 0) / 100
        self.assertAlmostEqual(v[5]["cpc"], 0.001)
        self.assertAlmostEqual(v[5]["batch_cpc"], 10 * 0.5 / 1)                               # logged $0.5 per sample, k = 5, 2 bases
        self.assertEqual(out["haiku-med:6x1"]["vote_at_test_k"]["t1"]["k"], 5)
        self.assertAlmostEqual(om["batch_cpc"], 1.0)                                          # logged $0.5 x 2 / 1 right

    def test_9c_every_haiku_arm_with_a_vote_curve_gets_cpc_at_each_k(self):
        ctx = make_ctx()
        for base in (0, 1):                                                                   # Haiku-max x3: base 0 right, base 1 wrong
            for s in (1, 2, 3):
                cid = f"{SET}-{base:03d}-6x1-hx-{s:02d}"
                ctx["records"].append(record(cid, "hx", base, "6x1", s, 1000, 0))
                ctx["other"].append(dict(row(cid, "om", base, "6x1", s, "a" if base == 0 else "b"), tag="hx", setup="haiku-max"))
        hx = rc.item_9c(ctx)["arms"]["haiku-max:6x1"]
        self.assertEqual(sorted(hx["vote_by_k"]), [1, 2, 3])                                  # k = 1..min(40, designed 3)
        self.assertAlmostEqual(hx["vote_by_k"][3]["cpc"], 3 * 0.0002 / 1)                     # 3 samples x 2 bases x $0.0001 / 1 right
        self.assertEqual(hx["vote_by_k"][2]["k"], 2)

    def test_9d_break_even_price_ratio(self):
        out = rc.item_9d(make_ctx())["cells"]
        o = out["opus-med:6x1"]
        self.assertEqual((o["k_match"], o["k_cap"]), (1, 40))                                 # Haiku vote 50 >= Opus 50 at k = 1
        self.assertAlmostEqual(o["R_list"], 140.0)                                            # $0.014 / $0.0001
        self.assertEqual(o["rho_list"], 40.0)
        self.assertAlmostEqual(o["rho_star"], 40 / 140)
        self.assertEqual(o["ci95"][1], "unbounded")                                           # draws {1, 1}: no k_match, +inf, kept
        self.assertTrue(0.1 < o["share_replicates_no_k_match"] < 0.4)
        self.assertEqual(o["share_replicates_zero_comparator_cost"], 0.0)
        s = out["sonnet-med:1x6"]
        self.assertEqual((s["k_match"], s["rho_list"]), (1, 20.0))
        self.assertAlmostEqual(s["rho_star"], 20 * 1 / 2)                                     # R_list = 0.0002 / 0.0001

    def test_9d_a_free_haiku_side_gives_rho_star_0(self):
        ctx = make_ctx()
        for r in ctx["records"]:
            if r["meta"]["setup"] == "hm" and r["meta"]["width"] == 6:
                r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)   # every Haiku 6x1 call B5-free: $0
        o = rc.item_9d(ctx)["cells"]["opus-med:6x1"]
        self.assertEqual((o["k_match"], o["rho_star"], o["R_list"], o["R_list_infinite"]), (1, 0.0, None, True))   # C4 item 2
        # draws {1, 1}: Haiku's vote 0 < Opus 100, no k_match: +inf; every other draw: R_list* = +inf, rho* = 0, kept
        self.assertEqual(o["ci95"], [0.0, "unbounded"])
        self.assertAlmostEqual(o["share_replicates_zero_haiku_cost"] + o["share_replicates_no_k_match"], 1.0)
        self.assertTrue(0.6 < o["share_replicates_zero_haiku_cost"] < 0.9)
        for r in ctx["records"]:
            if r["meta"]["setup"] == "om" and r["meta"]["width"] == 6:
                r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)
        ctx.pop("_report_costs_cache")
        both = rc.item_9d(ctx)["cells"]["opus-med:6x1"]                                      # both sides $0: 0/0, dropped and counted
        self.assertEqual(both["rho_star"], "undefined (both sides $0: R_list = 0/0)")
        self.assertGreater(both["replicates_dropped_both_sides_zero"], 0)
        self.assertEqual(both["ci95"], ["unbounded", "unbounded"])                            # only the no-k_match draws are kept

    def test_9d_a_free_comparator_gives_an_unbounded_ratio(self):
        ctx = make_ctx()
        for r in ctx["records"]:
            if r["meta"]["setup"] == "sm" and r["meta"]["width"] == 6:
                r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)   # B5-free: $0 (C1 9d)
        s = rc.item_9d(ctx)["cells"]["sonnet-med:6x1"]
        self.assertEqual((s["k_match"], s["R_list"], s["rho_star"]), (1, 0.0, "unbounded"))
        self.assertEqual(s["share_replicates_zero_comparator_cost"], 1.0)
        self.assertEqual(s["ci95"], ["unbounded", "unbounded"])

    def test_9e_cascade(self):
        out = rc.item_9e(make_ctx())["shapes"]["6x1"]
        k5 = out["5"]
        # base 1 (odd): samples 1-5 = b c b c b, top share 3/5 = 0.6 -> escalates only at tau 0.7, 0.8 (Opus right there)
        self.assertAlmostEqual(k5["frontier"]["0.3"]["accuracy"], 50.0)
        self.assertAlmostEqual(k5["frontier"]["0.3"]["mean_cost"], 0.0005)
        self.assertEqual(k5["frontier"]["0.3"]["escalation_rate"], 0.0)
        self.assertAlmostEqual(k5["frontier"]["0.7"]["accuracy"], 100.0)
        self.assertAlmostEqual(k5["frontier"]["0.7"]["mean_cost"], (0.0005 + 0.0005 + 0.014) / 2)
        self.assertEqual(k5["frontier"]["0.7"]["escalation_rate"], 0.5)
        self.assertEqual(k5["recommended_tau"], 0.7)                                          # cheapest qualifying; 0.7 and 0.8 tie -> lower tau
        e = k5["even"]
        self.assertEqual((e["cascade_accuracy"], e["opus_accuracy"], e["accuracy_difference"]), (100.0, 0.0, 100.0))
        self.assertAlmostEqual(e["cascade_mean_cost"], 0.0005)
        self.assertAlmostEqual(e["opus_mean_cost"], 0.014)
        self.assertAlmostEqual(e["cost_difference"], 0.0005 - 0.014)                          # C1 9e: the two differences, same draws
        self.assertEqual((e["bootstrap_name"], e["accuracy_difference_ci95"]), ("cascade:6x1:5", [100.0, 100.0]))
        self.assertEqual(out["10"]["recommended_tau"], 0.6)                                   # samples 1-10: b c tie, share 0.5

    def test_9e_no_usable_vote_escalates(self):
        ctx = make_ctx()
        for r in ctx["rows"]:
            if r["setup"] == "haiku-med" and r["base_id"] == "s-000" and r["sample"] <= 5:
                r["kind"] = "refusal"
        k5 = rc.item_9e(ctx)["shapes"]["6x1"]["5"]
        self.assertEqual(k5["bases_without_a_vote"], ["s-000"])                               # C1 9e: share 0, so it escalates at every tau
        self.assertEqual(k5["frontier"]["0.3"]["escalation_rate"], 0.5)
        self.assertAlmostEqual(k5["frontier"]["0.3"]["accuracy"], 0.0)                        # base 0 takes Opus (wrong); base 1 the vote (wrong)
        self.assertAlmostEqual(k5["frontier"]["0.3"]["mean_cost"], (0.0005 + 0.014 + 0.0005) / 2)

    def test_9f_cached_view(self):
        out = rc.item_9f(make_ctx())
        self.assertAlmostEqual(out["t3"]["mean_cached_cost_by_k"][0], 125e-6)                  # 1000 x $0.125 / MTok
        self.assertAlmostEqual(out["t3"]["mean_cached_cost_by_k"][7], (125 + 7 * 10) * 1e-6)   # + 7 x 1000 x $0.01 / MTok
        self.assertEqual(out["t3"]["cached_k"], 8)                                             # 125 + 10 (k - 1) <= 200
        self.assertEqual((out["t1"]["cached_k"], out["t2"]["cached_k"]), (40, 40))
        fam = out["family_row"]
        self.assertEqual(fam["label"], "cached view (offline re-pricing)")
        self.assertEqual((fam["tests"]["t1"]["k"], fam["tests"]["t3"]["k"]), (40, 8))
        self.assertEqual(out["rates_per_mtok"], {"cache_write_5m": "0.125", "cache_read": "0.01", "output": "0.50"})

    def test_9f_cached_k_0_leaves_the_test_not_run(self):
        ctx = make_ctx()
        for r in ctx["records"]:
            if r["meta"]["setup"] == "sm" and r["meta"]["width"] == 1:
                r["usage_raw"] = {"input_tokens": 10, "output_tokens": 0}                     # Sonnet $0.00002 < one cached sample
        out = rc.item_9f(ctx)
        self.assertEqual(out["t3"]["cached_k"], 0)
        self.assertEqual(out["family_row"]["tests"]["t3"]["p"], 1.0)                          # C1 9f: the k = 0 rule, not run
        self.assertIsNone(out["family_row"]["tests"]["t3"]["d"])

    def test_9g_token_matched_view(self):
        out = rc.item_9g(make_ctx())
        tm = out["token_matched_k"]
        self.assertEqual((tm["t1"]["raw_floor"], tm["t1"]["token_matched_k"]), (3, 3))        # floor(3500 / 1000)
        self.assertEqual((tm["t3"]["raw_floor"], tm["t3"]["token_matched_k"]), (0, 1))        # floor(100 / 1000), held to 1
        r5 = out["6x1"]["by_k"][4]
        self.assertEqual((r5["k"], r5["vote_at_k"], r5["haiku_mean_input_tokens"], r5["haiku_mean_output_tokens"]), (5, 50.0, 5000.0, 0.0))
        self.assertEqual(out["1x6"]["comparators"]["opus-med"]["mean_input_tokens"], 3500.0)
        self.assertEqual(out["family_row"]["tests"]["t1"]["k"], 3)

    def test_9f_9g_a_free_refusal_bills_no_tokens(self):
        ctx = make_ctx()
        r = next(r for r in ctx["records"] if r["meta"]["setup"] == "hm" and r["meta"]["width"] == 6)   # base 0, sample 1
        r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)
        f = rc.item_9f(ctx)["t1"]
        # billed input per sample: base 0 39 x 1000 / 40 = 975, base 1 1000; mean 987.5 x $0.125 / MTok at k = 1
        self.assertAlmostEqual(f["mean_cached_cost_by_k"][0], 987.5 * 0.125e-6)
        g = rc.item_9g(ctx)["token_matched_k"]["t1"]
        self.assertEqual((g["haiku_samples_pooled"], g["haiku_mean_total_tokens_per_sample"]), (80, 987.5))   # pooled: 79,000 / 80
        self.assertEqual(g["token_matched_k"], 3)                                             # floor(3500 / 987.5)

    def test_9h_opus_vs_sonnet(self):
        out = rc.item_9h(make_ctx())["6x1"]
        a = out["arms"]
        self.assertEqual((a["opus-med"]["A"]["as_deployed"], a["sonnet-med"]["A"]["as_deployed"], a["opus-low"]["A"]["as_deployed"]),
                         (0.5, 0.0, 1.0))
        om = out["pairs"]["opus-med-vs-sonnet-med"]
        p = om["point"]
        self.assertAlmostEqual(p["cost_ratio"], 70.0)                                         # 0.014 / 0.0002
        self.assertEqual(p["cpc_ratio"], rc.UNDEFINED_CPC)                                    # Sonnet's CPC is undefined
        self.assertEqual((p["acc_diff"], p["err_ratio"]), (50.0, 2.0))                        # (1 - 0) / (1 - 0.5): 2 errors over 1
        iv = om["intervals"]
        self.assertEqual(iv["acc_diff"]["ci95"], [0.0, 100.0])                                # draws {0,0}: 0; {1,1}: 100
        self.assertEqual(iv["acc_diff"]["bootstrap_name"], "ovs:acc_diff:opus-med-vs-sonnet-med:6x1")
        self.assertAlmostEqual(iv["cost_ratio"]["ci95"][0], 70.0)
        self.assertEqual(iv["err_ratio"]["ci95"][1], "unbounded")                             # C4 item 3: {1,1} has 0 Opus errors, 2/0 = +inf
        self.assertTrue(0.1 < iv["err_ratio"]["share_draws_infinite"] < 0.4)
        self.assertEqual(iv["err_ratio"]["draws_dropped"], 0)
        # cpc_ratio: Sonnet's CPC is +inf in every draw; Opus's finite / +inf = 0, kept; draws {0,0}: +inf / +inf, dropped and counted
        self.assertEqual(iv["cpc_ratio"]["ci95"], [0.0, 0.0])                                 # never withheld
        self.assertTrue(0.1 < iv["cpc_ratio"]["share_draws_dropped"] < 0.4)
        ol = out["pairs"]["opus-low-vs-sonnet-med"]
        self.assertEqual((ol["point"]["acc_diff"], ol["point"]["err_ratio"]), (100.0, "undefined (opus-low has no errors)"))
        self.assertEqual(ol["intervals"]["cpc_ratio"]["ci95"], [0.0, 0.0])                    # finite / +inf = 0 in every draw
        self.assertEqual(ol["intervals"]["err_ratio"]["ci95"], ["unbounded", "unbounded"])

    def test_9h_one_ratio_rule(self):
        self.assertEqual((rc._ratio(2.0, 0.0), rc._ratio(0.0, 3.0), rc._ratio(math.inf, 3.0), rc._ratio(3.0, math.inf)), (math.inf, 0.0, math.inf, 0.0))
        self.assertEqual((rc._ratio(0.0, 0.0), rc._ratio(math.inf, math.inf)), (None, None))   # dropped and counted
        ctx = make_ctx()
        for r in ctx["records"]:
            if r["meta"]["setup"] == "sm" and r["meta"]["width"] == 6:
                r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)   # Sonnet B5-free: C(Sonnet) = $0
        cr = rc.item_9h(ctx)["6x1"]["pairs"]["opus-med-vs-sonnet-med"]["intervals"]["cost_ratio"]
        self.assertEqual((cr["ci95"], cr["share_draws_infinite"], cr["draws_dropped"]), (["unbounded", "unbounded"], 1.0, 0))   # x / 0 = +inf

    def test_19_thinking_tokens(self):
        recs = [record("t1", "hm", 0, "6x1", 1, 0, 10, text="abcdefg"),                         # visible 7 // 3 = 2 -> thinking 8
                record("t2", "hm", 0, "6x1", 2, 0, 1, text="abcdefghi"),                        # visible 3 -> max(0, -2) = 0
                record("t3", "om", 0, "6x1", 1, 0, 5, text="ab")]                               # one call
        out = rc.item_19({"records": recs, "rows": [], "other": []})["arms"]
        hm = out["haiku-med:6x1"]
        self.assertEqual((hm["calls"], hm["median"], hm["max"]), (2, 4.0, 8))
        self.assertAlmostEqual(hm["p90"], 7.2)                                                # quantiles([0, 8], n=10, inclusive)[8]
        self.assertAlmostEqual(hm["share_of_list_cost"], 8 / 11)                              # 8 x 0.5 / (11 x 0.5)
        self.assertEqual((out["opus-med:6x1"]["p90"], out["opus-med:6x1"]["median"], out["opus-med:6x1"]["max"]), ("n < 2", 5, 5))

    def test_22_run_window(self):
        td = Path(tempfile.mkdtemp())
        (td / "window.json").write_text(json.dumps({"started_utc": "2026-10-13T00:00:00+00:00", "hours": 48,
                                                    "extensions": [{"at_utc": "2026-10-15T01:00:00+00:00", "note": "D-45 test"}]}))
        ev = [{"event": "reserve", "key": "a@1", "batch": True, "time": "2026-10-13T00:00:00+00:00"},
              {"event": "reserve", "key": "r#a1", "batch": False, "time": "2026-10-13T00:00:00+00:00"},
              {"event": "send", "key": "r#a1", "time": "2026-10-13T00:10:00+00:00"},
              {"event": "send", "key": "a@1", "time": "2026-10-13T01:00:00+00:00"},
              {"event": "commit", "key": "a@1", "time": "2026-10-13T13:00:00+00:00"},
              {"event": "commit", "key": "r#a1", "time": "2026-10-13T19:30:00+00:00"}]
        (td / "ledger.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev))
        out = rc.item_22({"run_dir": td})
        self.assertEqual(out["hours"], 18.5)                                                  # 01:00 -> 19:30
        self.assertEqual(out["hours_to_last_batch_result"], 12.0)
        self.assertEqual(out["window_json"]["extensions"][0]["note"], "D-45 test")
        self.assertIsNone(rc.item_22({"run_dir": Path(tempfile.mkdtemp())})["hours"])

    def test_23_repricing(self):
        self.assertFalse(rc.item_23({})["applies"])
        later = dict(prices.PRICES)
        later[HAIKU] = prices.Rates(Decimal("0.20"), Decimal("1.00"), Decimal("0.25"), Decimal("0.40"), Decimal("0.02"))   # Haiku doubled
        ctx = make_ctx()
        out = rc.item_23(dict(ctx, later_prices={"date": "2027-01-01", "table": later}))
        self.assertEqual((out["applies"], out["table_date"]), (True, "2027-01-01"))
        items = out["items"]
        self.assertEqual(items["item_9a"]["price_table_date"], "2027-01-01")
        self.assertAlmostEqual(items["item_9b"]["arms"]["haiku-med:6x1"]["mean"], 0.0002)      # 1000 x $0.20 / MTok
        self.assertAlmostEqual(items["item_9b"]["arms"]["opus-med:6x1"]["mean"], 0.014)        # Opus unchanged
        d = items["item_9d"]["cells"]["opus-med:6x1"]
        self.assertEqual((d["rho_list"], d["R_list"]), (20.0, 70.0))                          # Opus / doubled Haiku
        self.assertEqual(items["item_9f"]["rates_per_mtok"]["cache_write_5m"], "0.25")
        self.assertNotIn("family_row", items["item_9f"])                                      # k is never re-priced
        self.assertAlmostEqual(rc.item_9b(ctx)["arms"]["haiku-med:6x1"]["mean"], 0.0001)       # the pinned figures are untouched
        with self.assertRaises(ValueError):
            rc.item_23(dict(ctx, later_prices={"date": "2027-01-01", "table": {HAIKU: later[HAIKU]}}))
        big = make_ctx()
        cid = big["records"][0]["custom_id"]
        big["records"][0]["usage_raw"] = {"input_tokens": 100_001, "output_tokens": 0}         # a long prompt (Haiku): pinned long row $0.50
        out = rc.item_23(dict(big, later_prices={"date": "2027-01-01", "table": later}))     # C4 item 4: no long-prompt row given
        self.assertEqual(out["not_repriced"], {cid: "not re-priced (no long-prompt row)"})
        self.assertEqual(Decimal(out["items"]["item_9a"]["per_call"][cid]["list_usd"]), Decimal("0.0500005"))   # its pinned cost stays
        self.assertEqual(Decimal(out["items"]["item_9a"]["per_call"][big["records"][1]["custom_id"]]["list_usd"]), Decimal("0.0002"))
        long_row = prices.Rates(Decimal("1"), Decimal("5"), Decimal("1.25"), Decimal("2"), Decimal("0.1"))
        out = rc.item_23(dict(big, later_prices={"date": "2027-01-01", "table": later, "long_prompt_table": {HAIKU: long_row}}))
        self.assertEqual(out["not_repriced"], {})
        self.assertEqual(Decimal(out["items"]["item_9a"]["per_call"][cid]["list_usd"]), Decimal("0.100001"))   # 100,001 x $1 / MTok
        self.assertEqual(rc.OPEN_QUESTIONS, {})


class DriverReviewR8(unittest.TestCase):
    """Edith's driver review r8 (C-1 to C-5) and the tests she asked for, by hand."""

    def test_c1_at_least_after_rounding_to_1e_9_a_2_3_tie(self):
        self.assertFalse(100.0 * float(Fraction(2, 3)) >= 200 / 3)                            # 66.66666666666666 < 66.66666666666667
        self.assertTrue(rc.at_least(100.0 * float(Fraction(2, 3)), 200 / 3))
        ctx = make_ctx()                                                                      # add base 2 at 6x1: Opus right there
        for s_ in range(1, 41):
            cid = f"{SET}-002-6x1-hm-{s_:02d}"
            ctx["records"].append(record(cid, "hm", 2, "6x1", s_, 1000, 0))
            ctx["rows"].append(row(cid, "hm", 2, "6x1", s_, "a"))
        ctx["records"].append(record(f"{SET}-002-6x1-om-01", "om", 2, "6x1", 1, 3500, 0))
        ctx["rows"].append(row(f"{SET}-002-6x1-om-01", "om", 2, "6x1", 1, "a"))              # Opus: 0, 100, 100 -> 66.66666666666667
        curve = [{"acc": float(Fraction(2, 3))} for _ in range(40)]                          # Haiku's vote@k: 2/3 at every k, every base
        ctx["_cache"] = {("curve", "haiku-med", "6x1"): {f"{SET}-00{b}": curve for b in range(3)}}
        self.assertEqual(rc.item_9d(ctx)["cells"]["opus-med:6x1"]["k_match"], 1)              # a float >= would find no k at all

    def test_c2_a_later_table_with_two_ratios_gives_9d_not_computed(self):
        later = dict(prices.PRICES)
        later[OPUS] = prices.Rates(Decimal("4"), Decimal("30"), Decimal("5"), Decimal("8"), Decimal("0.2"))   # 40 on input, 60 on output
        out = rc.item_23(dict(make_ctx(), later_prices={"date": "2027-01-01", "table": later}))
        d = out["items"]["item_9d"]["cells"]
        self.assertEqual(d["opus-med:6x1"], {"not_computed": "the price ratio differs between input and output on this table"})
        self.assertEqual(d["sonnet-med:1x6"]["rho_list"], 20.0)                               # the rest of 9d and of group B still runs

    def test_c3_9h_cpc_of_0_with_right_answers_and_cost_0_over_0(self):
        ctx = make_ctx()
        for r in ctx["rows"]:
            if r["setup"] == "sonnet-med" and r["shape"] == "6x1":
                r.update(answer_key="a", correct=True)                                       # Sonnet right on both bases
        for r in ctx["records"]:
            if r["meta"]["setup"] == "sm" and r["meta"]["width"] == 6:
                r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)   # ... at $0 (B5): CPC 0
        p = rc.item_9h(ctx)["6x1"]["pairs"]["opus-med-vs-sonnet-med"]["point"]
        self.assertEqual((p["cpc_ratio"], p["cost_ratio"]), ("unbounded", "unbounded"))     # x / 0 = +inf (C4 item 3)
        for r in ctx["records"]:
            if r["meta"]["setup"] == "om" and r["meta"]["width"] == 6:
                r.update(kind="refusal", refusal_category="cyber", refusal_billed_by_rule=False)
        ctx.pop("_report_costs_cache")
        p = rc.item_9h(ctx)["6x1"]["pairs"]["opus-med-vs-sonnet-med"]["point"]
        self.assertEqual((p["cost_ratio"], p["cpc_ratio"]), ("undefined (0/0)", "undefined (0/0)"))

    def test_c4_thinking_counts_billed_tokens_only(self):
        recs = [record("t1", "hm", 0, "6x1", 1, 0, 10, text="abcdefg"),                         # visible 2 -> thinking 8, $0.000005
                record("t2", "hm", 0, "6x1", 2, 0, 10, text="", kind="refusal", refusal_category="cyber",
                       refusal_billed_by_rule=False)]                                          # B5-free: 0 billed tokens, 0 thinking
        out = rc.item_19({"records": recs, "rows": [], "other": []})["arms"]["haiku-med:6x1"]
        self.assertEqual((out["median"], out["max"]), (4.0, 8))
        self.assertAlmostEqual(out["share_of_list_cost"], 0.8)                                 # 8 x 0.5 / (10 x 0.5 + $0)

    def test_c5_the_repriced_9f_has_no_cached_k(self):
        later = dict(prices.PRICES)
        out = rc.item_23(dict(make_ctx(), later_prices={"date": "2027-01-01", "table": later}))["items"]["item_9f"]
        self.assertNotIn("cached_k", out["t1"])
        self.assertEqual(len(out["t1"]["mean_cached_cost_by_k"]), 40)

    def test_9b_interval_ends(self):
        ctx = make_ctx()
        ctx["records"] = [r for r in ctx["records"] if r["custom_id"] != f"{SET}-001-6x1-om-01"]   # base 1's Opus call: $0 (X4)
        om = rc.item_9b(ctx)["arms"]["opus-med:6x1"]
        # 2 bases, $0.014 and $0: a draw is {0, 0} (mean and median 0.014), {1, 1} (0) or mixed (0.007), about 1/4, 1/4, 1/2, so the
        # 2.5% and 97.5% order statistics of 200 draws are the two extremes, for the mean and the median alike
        self.assertEqual((om["mean"], om["median"]), (0.007, 0.007))
        self.assertEqual(om["mean_ci95"], [0.0, 0.014])
        self.assertEqual(om["median_ci95"], [0.0, 0.014])

    def test_9e_none_qualifies_takes_the_highest_accuracy(self):
        ctx = make_ctx()
        for r in ctx["rows"]:
            if r["setup"] == "haiku-med" and r["base_id"] == "s-001":
                r.update(answer_key="b", trace_key="b", final_key="b", correct=False)          # odd base 1: all 40 wrong and agreeing
        k5 = rc.item_9e(ctx)["shapes"]["6x1"]["5"]
        # share 1.0 >= every tau: the cascade never escalates and scores 0 on base 1, against Opus's 100 - 10 = 90: none qualifies; all
        # tau tie on accuracy (0) and cost, so the lower tau
        self.assertEqual((k5["rule"], k5["recommended_tau"]), ("none within 10 points: the highest odd-base accuracy", 0.3))


class EndToEnd(unittest.TestCase):
    """report(ctx) on the fake main run of test_main_analysis (3 base puzzles, every arm, every kind)."""

    @classmethod
    def setUpClass(cls):
        tma.FakeMainRun.setUpClass.__func__(cls)

    def test_report_runs_and_serialises(self):
        built = main_rows.build(self.set_dir, [self.log])
        _, items = main_rows.load_set(self.set_dir)
        ctx = {"rows": built["tests"], "other": built["other"], "records": main_rows.final_records([self.log]), "items": items,
               "set_id": "main-ledger-l14n6-t", "n": 6, "k": json.loads(self.k_path.read_text()), "run_dir": self.run_dir, "B": 50}
        out = rc.report(ctx)
        text = json.dumps(out, default=str)
        self.assertIn("open_questions", out)
        for key in ("9a", "9b", "9c", "9d", "9e", "9f", "9g", "9h", "19", "22", "23"):
            self.assertIn(f"item_{key}", out)
        self.assertNotIn("NaN", text)
        n_calls = len(ctx["records"])
        self.assertEqual(len(out["item_9a"]["per_call"]), n_calls)
        self.assertEqual(out["item_9a"]["by_arm_shape"]["opus-med:6x1"]["calls"], 3)
        self.assertIn("e3:1x6", out["item_9b"]["arms"])
        self.assertIn("window_json", out["item_22"])


if __name__ == "__main__":
    unittest.main()
