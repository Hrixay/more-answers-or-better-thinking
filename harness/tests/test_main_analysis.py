"""main_rows (the call log to scored rows) and main_analysis (every locked step on a run folder): end to end on a fake main run whose
replies cover every arm, every kind (answered right / wrong / malformed / identical repeats, refusal, truncated) and all three views;
the answer keys are read from the frozen set; the round trip with Karen's simulated rows. Offline only."""

import gzip
import itertools
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from harness.analysis import five_tests, main_analysis, main_rows, scoring
from harness.pareto import e3
from harness.pareto.main import run_main
from harness.pareto.pilot import HAIKU
from harness.pareto.transport import FakeTransport
from harness.taskgen import ledger
from harness.taskgen.freeze import write_set
from harness.tests.fakes import guard, reply

SIM = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v2"


def chain_text(states, repeat=False):
    lines = [f"1.{k} = {ledger.fmt(s)}" for k, s in enumerate(states, 1)]
    if repeat:                                                                 # D-90: every line again, identical
        lines += ["", "Summary:"] + lines
    return "\n".join(lines + [f"Answer: 1 = {ledger.fmt(states[-1])}"])


def pieces_text(answer):
    return "Answer: " + ", ".join(f"{i} = {ledger.fmt(a)}" for i, a in enumerate(answer, 1))


def bump(state, by=1):
    return [state[0] + by] + list(state[1:])


class FakeMainRun(unittest.TestCase):
    """One small frozen l14n6 set (3 base puzzles), the whole main runner with a fake transport, then the converter and the driver."""

    @classmethod
    def setUpClass(cls):
        cls.td = Path(tempfile.mkdtemp())
        cls.set_dir = cls.td / "main-ledger-l14n6-t"
        write_set(cls.set_dir, "ledger", "l14n6", "main-ledger-l14n6-t", 3, "d31", "scratch")
        man, items = main_rows.load_set(cls.set_dir)
        cls.items = items
        from harness.pareto import d42
        by_prompt = {it["prompt"]: it for it in items.values()}
        by_prompt.update({d42.variant_prompt(it): it for it in items.values()})
        steps = {st.prompt: st for st in e3.chain_steps([(man, list(items.values()))])}
        cycle = itertools.count()

        def fake(p):
            i = next(cycle)
            text = p["messages"][0]["content"]
            if text in steps:                                                  # E3: mostly right, every 7th a different value
                truth = steps[text].truth.split(",")
                vals = [int(x) for x in truth]
                return reply(model=p["model"], text=f"Answer: {ledger.fmt(vals if i % 7 else bump(vals))}")
            it = by_prompt[text]
            mode = i % 11
            if mode == 9:
                return reply(model=p["model"], text=None, stop="refusal", category="cyber", tout=0)
            if mode == 10:
                return reply(model=p["model"], text="1.1 = [", stop="max_tokens")
            if int(it["depth"]) > 1:
                states = it["chains"][0]["states"]
                if mode in (0, 1, 2, 3):
                    return reply(model=p["model"], text=chain_text(states))
                if mode == 4:
                    return reply(model=p["model"], text=chain_text(states, repeat=True))           # right under D-90 only
                if mode in (5, 6):
                    return reply(model=p["model"], text=chain_text(states[:-1] + [bump(states[-1])]))  # a real slip
                if mode == 7:
                    return reply(model=p["model"], text=chain_text([bump(states[0])] + states[1:]))  # a copy slip at line 1
                return reply(model=p["model"], text="I could not finish.")                         # unreadable
            ans = it["answer"]
            if mode in (0, 1, 2, 3, 4):
                return reply(model=p["model"], text=pieces_text(ans))
            if mode in (5, 6, 7):
                return reply(model=p["model"], text=pieces_text([bump(ans[0], mode)] + ans[1:]))
            return reply(model=p["model"], text="Answer: nothing")
        cls.run_dir = cls.td / "run"
        run_main(guard(run_cap="100"), FakeTransport(fake), cls.run_dir, cls.set_dir, ("sl", "ho", "hx"), sleep=lambda s: None,
                 waive_pause_note="test fixture: the fake transport truncates every 11th reply on purpose (about 9%), so the 2% "
                                  "truncation pause (b4ff738) is waived to let the fake run reach E3 and the real-time subset")
        cls.log = cls.run_dir / "calls.jsonl"
        cls.built = main_rows.build(cls.set_dir, [cls.log])
        from harness.analysis import k_step
        cls.k_path = cls.td / "k.json"
        cls.k_path.write_text(json.dumps(k_step.k_from_table(cls.run_dir / "compact_table.csv"), default=str))
        cls.res = main_analysis.analyse_run(cls.set_dir, [cls.log], cls.k_path, B=300, fairness_draws=200, run_dir=cls.run_dir,
                                            extras=("sl", "ho", "hx"))

    def test_every_final_record_is_placed_once(self):
        recs = main_rows.final_records([self.log])
        e3_calls = sum(1 for r in recs if r["meta"]["setup"] == "es")
        self.assertEqual(len(self.built["tests"]) - len(self.built["e3"]) + len(self.built["other"]) + e3_calls, len(recs))
        self.assertEqual(Counter(r["setup"] for r in self.built["tests"]),
                         {"haiku-med": 240, "opus-med": 6, "opus-low": 6, "sonnet-med": 6, "e3": 3})
        self.assertEqual(Counter(r["setup"] for r in self.built["other"]),
                         {"haiku-low": 240, "haiku-thinking-off": 240, "haiku-max": 18, "sonnet-low": 6,
                          "haiku-med-d42-variant": 60, "rt-haiku-med": 30, "rt-opus-med": 6, "rt-sonnet-med": 6})

    def test_rows_carry_what_the_locked_analysis_reads(self):
        for r in self.built["tests"]:
            self.assertTrue(r["base_id"].startswith("main-ledger-l14n6-t-"))
            self.assertIn(r["shape"], ("6x1", "1x6"))
            for k in ("kind", "stop_reason", "correct", "cost_usd"):
                self.assertIn(k, r)
            if r["setup"] != "e3" and r["shape"] == "1x6":
                for k in ("format_status", "trace_key", "final_key", "slip_type", "correct_final", "correct_copy_forgiven",
                          "correct_original", "format_status_original", "answer_only"):
                    self.assertIn(k, r)
            if r["shape"] == "6x1":
                self.assertIn("answer_key", r)
        kinds = Counter(r["kind"] for r in self.built["tests"] + self.built["other"])
        self.assertTrue({"answered", "refusal", "truncated"} <= set(kinds))
        d90 = [r for r in self.built["tests"] if r.get("format_status") == "ok" and r.get("format_status_original") == "extra_line"]
        self.assertTrue(d90 and all(r["correct"] and not r["correct_original"] for r in d90))

    def test_keys_are_read_from_the_frozen_set_not_recomputed(self):
        rec = next(r for r in main_rows.final_records([self.log]) if r["meta"]["setup"] == "om" and r["meta"]["depth"] == 6)
        stored = self.items[rec["meta"]["item_id"]]
        rec = dict(rec, kind="answered", stop_reason="end_turn", answer_text=chain_text(stored["chains"][0]["states"]))
        self.assertTrue(main_rows.score_row(rec, stored, "opus-med")["correct"])
        other = dict(stored, chains=[dict(stored["chains"][0], states=[bump(st) for st in stored["chains"][0]["states"]])])
        self.assertFalse(main_rows.score_row(rec, other, "opus-med")["correct"])   # the grade follows the stored key only

    def test_the_driver_runs_every_locked_step_and_every_view(self):
        r = self.res
        self.assertEqual(set(r["confirmatory"]["views"]), {"as_deployed", "refusals_out", "truncations_out"})
        for v in r["confirmatory"]["views"].values():
            self.assertEqual(set(v["tests"]), {"t1", "t2", "t3", "t4", "t5"})
        self.assertEqual(set(r["secondary"]) >= {"final_answer", "copy_slips_forgiven", "original_repeat_rule"}, True)
        self.assertEqual(r["original_repeat_rule_appendix"]["score"], "original")
        self.assertIn("k_o", r["k_used"])
        self.assertEqual(r["k_used"]["k_o"], json.loads(self.k_path.read_text())["k_o"])

        self.assertIn("TI", json.dumps(r["fairness"]))
        for key in ("error_ratios", "five_point_view", "d42_robustness", "flag_r", "low_information_flag", "realtime"):
            self.assertIn(key, r["reporting"])
        self.assertEqual(r["reporting"]["five_point_view"]["margin"], -5.0)
        self.assertEqual(r["reporting"]["d42_robustness"]["n_puzzles"], 6)
        self.assertEqual(r["main_run_markers"]["label"], "main run")
        self.assertEqual(r["main_run_markers"]["haiku-med"]["missing_tries"], 0)
        self.assertEqual(sorted(r["reporting"]["realtime"]["puzzles"]), sorted(self.items))      # 6 puzzles: fewer than 10 in this set
        self.assertIn("p95", r["reporting"]["realtime"]["rt-haiku-med"]["latency"])
        self.assertIn("batch_turnaround", r["reporting"])
        self.assertNotIn("provisional", json.dumps(r, default=str))

    def test_group_b_k_s_6x1_is_one_number(self):
        """k_S(6x1) has two code paths (report_votes: k_from_rows on k_step's cost rows; report_arms: kscript.k_value on the rows); the
        driver checks they agree and reports the one value."""
        gb = self.res["reporting"]["group_b"]
        self.assertGreaterEqual(gb["k_s_6x1"], 0)
        self.assertEqual(gb["k_s_6x1"], gb["item_11"]["k_s_6x1"]["k"])

    def test_group_b_is_wired_in_under_the_notes_item_numbers(self):
        gb = self.res["reporting"]["group_b"]
        items = {f"item_{i}" for i in ("7", "8a", "8b", "9a", "9b", "9c", "9d", "9e", "9f", "9g", "9h")} | \
            {f"item_{i}" for i in range(10, 25)}
        self.assertEqual({k for k in gb if k.startswith("item_")}, items)                      # items 7-24, each from one module
        self.assertEqual(set(gb["open_questions"]), {"report_votes", "report_costs", "report_arms"})
        self.assertEqual(gb["open_questions"]["report_arms"], {})
        self.assertIn("I3", gb["interpretations"])
        self.assertEqual(self.res["missing_left_out"], "no missing items in the five tests' arms")                    # item 16: nothing is missing in this run
        self.assertEqual(gb["item_16"]["exclude_missing_view"], "no missing items in the five tests' arms")
        # the shared copies (C3): one 9b cost and one curve, read the same way by every module
        self.assertAlmostEqual(gb["item_24"]["table"]["opus-med 6x1"]["cost_per_puzzle"]["mean"], gb["item_9b"]["arms"]["opus-med:6x1"]["mean"])
        self.assertAlmostEqual(gb["item_10"]["arms"]["haiku-low 6x1"]["vote_curve"]["points"][0]["mean"],
                               gb["item_9c"]["arms"]["haiku-low:6x1"]["vote_by_k"][1]["correct"] / gb["item_9c"]["arms"]["haiku-low:6x1"]["vote_by_k"][1]["n_bases"])
        self.assertEqual(gb["item_8b"]["vote_curve"]["6x1"]["bootstrap_name"], "vote_curve:haiku-med:6x1")
        json.dumps(gb, default=str)

    def test_one_shared_copy_of_9a_9b_9c_and_the_vote_curve(self):
        from harness.analysis import report_arms, report_costs, report_votes
        for mod in (report_arms, report_votes, main_analysis):
            for name in ("list_cost", "_call_costs", "_e3_costs", "_per_puzzle", "_cost_block", "_cpc", "_vote_curve", "_haiku_inputs",
                         "_single_call_cost_per_puzzle", "_haiku_sample_cost_per_puzzle", "_haiku_curve", "haiku_curves"):
                self.assertFalse(hasattr(mod, name), f"{mod.__name__}.{name}")
        for name in ("list_cost", "calls", "base_costs", "cost_block", "cpc_block"):
            self.assertTrue(callable(getattr(report_costs, name)))
        self.assertTrue(callable(report_votes.arm_curve) and callable(report_votes.curve_summary))

    def test_realtime_report_by_hand(self):
        from harness.analysis.main_analysis import realtime_report
        ids = sorted(self.items)
        recs, rt, batch = [], [], []
        for j, iid in enumerate(ids):
            for s in range(1, 6):                                                  # Haiku x5: latencies j+s, right when s is odd
                cid = f"{iid}-rthm-{s:02d}"
                recs.append({"custom_id": cid, "latency_s": float(j + s), "usage_raw": {"output_tokens": 100}})
                rt.append({"setup": "rt-haiku-med", "item_id": iid, "custom_id": cid, "kind": "answered", "correct": s % 2 == 1})
            for s in range(1, 41):                                                 # Batch Haiku x40: samples 1-5 right, the rest wrong
                cid = f"{iid}-hm-{s:02d}"
                recs.append({"custom_id": cid, "latency_s": None, "usage_raw": {"output_tokens": 50 if s <= 5 else 999}})
                batch.append({"setup": "haiku-med", "item_id": iid, "custom_id": cid, "sample": s, "kind": "answered", "correct": s <= 5})
        r = realtime_report(rt, batch, recs, self.set_dir)["rt-haiku-med"]
        self.assertEqual((r["calls"], r["latency"]["n"], r["latency"]["max"]), (30, 30, float(5 + 5)))
        self.assertAlmostEqual(r["accuracy_realtime"], 18 / 30)
        self.assertEqual(r["accuracy_batch"], 1.0)                                 # samples 1-5 only
        self.assertAlmostEqual(r["accuracy_difference"], 18 / 30 - 1.0)
        self.assertEqual((r["output_tokens_realtime"], r["output_tokens_batch"]), (100.0, 50.0))
        self.assertEqual(r["vote_of_5"]["at_once_median"], 2.5 + 5)                # per puzzle max j+5, j = 0..5: median 7.5
        self.assertEqual(r["vote_of_5"]["one_after_another_median"], 5 * 2.5 + 15)   # per puzzle sum 5j+15: median 27.5
        json.dumps(r, default=str)                                             # the whole result serialises

    def test_the_k_step_reads_costs_only_keeps_the_confirmatory_arms_and_the_driver_needs_it(self):
        from harness.analysis import k_step
        k = json.loads(self.k_path.read_text())
        self.assertEqual(k["columns_read"], ["custom_id", "requested_model", "effort", "kind", "cost_usd"])
        self.assertEqual(k["rows_kept_by_tag"], {"hm": 240, "om": 6, "sm": 6})
        for tag in ("ho", "hv", "es", "rthm", "hl", "ol"):
            self.assertIn(tag, k["rows_left_out_by_tag"])                    # Haiku-medium look-alikes never enter k
        cols = k_step.read_cost_columns(self.run_dir / "compact_table.csv")
        self.assertNotIn("right", cols[0])
        rows = k_step.confirmatory_cost_rows(cols)["rows"]
        self.assertEqual(k["k_o"], {sh: int(five_tests.k_from_rows(rows, n=6)["opus"][sh]["k"]) for sh in ("6x1", "1x6")})
        with self.assertRaises(FileNotFoundError):
            main_analysis.analyse_run(self.set_dir, [self.log], self.td / "no-k.json", B=50, fairness_draws=20)
        other = self.td / "k-other.json"
        other.write_text(json.dumps(dict(k, compact_table_sha256="0" * 64)))
        with self.assertRaises(ValueError):
            main_analysis.analyse_run(self.set_dir, [self.log], other, B=50, fairness_draws=20, run_dir=self.run_dir,
                                      extras=("sl", "ho", "hx"))
        edited = self.td / "k-edited.json"                                    # the right table hash but an edited k: refused
        edited.write_text(json.dumps(dict(k, k_s=k["k_s"] + 1)))
        with self.assertRaises(ValueError):
            main_analysis.analyse_run(self.set_dir, [self.log], edited, B=50, fairness_draws=20, run_dir=self.run_dir,
                                      extras=("sl", "ho", "hx"))


class MissingTries(unittest.TestCase):
    """D-48 row 23 (Edith's readiness item 1): a planned try with no final record is a wrong "missing" row in every view."""

    @classmethod
    def setUpClass(cls):
        FakeMainRun.setUpClass()
        cls.f = FakeMainRun
        recs = main_rows.final_records([cls.f.log])
        drop = {r["custom_id"] for r in recs if r["meta"]["setup"] in ("hm", "om")}
        drop = set(sorted(drop)[:7])                                          # 7 single calls lost
        e3_drop = {r["custom_id"] for r in recs if r["meta"]["setup"] == "es" and r["meta"]["step"] == 2}  # every step-2 draw lost
        cls.dropped, cls.e3_dropped = drop, e3_drop
        cls.log2 = cls.f.td / "calls-with-gaps.jsonl"
        cls.log2.write_text("".join(json.dumps(r) + "\n" for r in recs if r["custom_id"] not in drop | e3_drop))
        man, items = main_rows.load_set(cls.f.set_dir)
        cls.planned = main_rows.planned_requests(man, list(items.values()), ("sl", "ho", "hx"))
        cls.built = main_rows.build(cls.f.set_dir, [cls.log2], planned=cls.planned)

    def test_the_planned_list_matches_the_manifest_and_a_wrong_one_is_refused(self):
        main_rows.check_planned(self.f.run_dir, self.planned)
        man, items = main_rows.load_set(self.f.set_dir)
        with self.assertRaises(ValueError):
            main_rows.check_planned(self.f.run_dir, main_rows.planned_requests(man, list(items.values()), ("sl",)))

    def test_each_lost_try_is_a_wrong_missing_row_kept_in_every_view(self):
        miss = [r for r in self.built["missing"] if r["setup"] != "e3"]
        self.assertEqual(sorted(r["custom_id"] for r in miss), sorted(self.dropped))
        for r in miss:
            self.assertEqual((r["kind"], r["correct"], r["cost_usd"]), ("missing", False, None))
            for view in ("as_deployed", "refusals_out", "truncations_out"):
                self.assertFalse(scoring._dropped(dict(r), view), view)
            self.assertFalse(scoring.row_correct(r, "official"))
            self.assertIsNone(scoring.vote_key(r, "official"))

    def test_an_e3_chain_with_an_unfinished_step_is_a_row_with_that_step_wrong(self):
        e3m = [r for r in self.built["missing"] if r["setup"] == "e3"]
        self.assertEqual(len(e3m), 3)                                         # all 3 chains lost step 2
        for r in e3m:
            self.assertEqual((r["kind"], r["step_correct"][1]), ("missing", False))
        self.assertEqual(len([r for r in self.built["tests"] if r["setup"] == "e3"]), 3)

    def test_the_repeat_share_uses_real_calls_only(self):
        rows = [r for r in self.built["tests"] if r["setup"] == "haiku-med"]
        real = [r for r in rows if r["kind"] != "missing"]
        self.assertLess(len(real), len(rows))                                 # some Haiku tries are missing here
        self.assertEqual(main_analysis.repeat_share(rows, 6), main_analysis.repeat_share(real, 6))

    def test_the_driver_counts_missing_as_wrong_reports_the_leave_out_view_and_keeps_k_on_real_calls(self):
        r = main_analysis.analyse_run(self.f.set_dir, [self.log2], self.f.k_path, B=200, fairness_draws=100, run_dir=self.f.run_dir,
                                      extras=("sl", "ho", "hx"))
        full = main_analysis.analyse_run(self.f.set_dir, [self.f.log], self.f.k_path, B=200, fairness_draws=100, run_dir=self.f.run_dir,
                                         extras=("sl", "ho", "hx"))
        ml = r["missing_left_out"]                                                            # item 16's exclude-missing view (B-1, r7)
        self.assertEqual(ml["label"], "exclude-missing view (only missing items left out; otherwise as_deployed)")
        self.assertEqual(ml["missing_left_out"], len(self.built["missing"]))
        self.assertEqual(ml["tests"], r["reporting"]["group_b"]["item_16"]["exclude_missing_view"]["tests"])
        self.assertEqual(full["missing_left_out"], "no missing items in the five tests' arms")
        counts = r["counts"]["five_test_arms"]
        self.assertGreater(counts["haiku-med 6x1"]["missing"] + counts["haiku-med 1x6"]["missing"] + counts["opus-med 6x1"]["missing"]
                           + counts["opus-med 1x6"]["missing"], 0)
        self.assertEqual(full["counts"]["five_test_arms"]["haiku-med 6x1"]["missing"], 0)
        self.assertEqual(full["counts"]["five_test_arms"]["haiku-med 6x1"]["missing_rate"], 0.0)


class ReportingByHand(unittest.TestCase):
    """research/reporting-definitions-main.md: one hand-computed case per item, the test pairs read from five_tests.tests_for, and the
    error ratio's +inf and 0/0 replicates (Edith, note review (a) and (c))."""

    def test_the_tests_and_their_comparators_come_from_the_locked_table(self):
        t = five_tests.tests_for(6)
        self.assertEqual({k: v[1] for k, v in t.items()}, {"t1": "opus-med", "t2": "opus-med", "t3": "sonnet-med", "t4": "opus-med",
                                                         "t5": "sonnet-med"})
        self.assertEqual({k: (v[0], v[2]) for k, v in t.items()}, {"t1": ("haiku-med", "6x1"), "t2": ("haiku-med", "1x6"),
                                                                  "t3": ("haiku-med", "1x6"), "t4": ("e3", "1x6"), "t5": ("opus-low", "1x6")})

    def test_error_ratio_keeps_infinite_replicates_and_drops_0_over_0(self):
        r = main_analysis.ratio_from_errors({"a": 1.0, "b": 1.0, "c": 0.0, "d": 0.0}, {"a": 1.0, "b": 0.0, "c": 0.0, "d": 0.0}, "t2", B=4000)
        self.assertEqual((r["n"], r["E_ch"], r["E_cmp"], r["R"], r["defined"]), (4, 2.0, 1.0, 2.0, True))
        self.assertEqual(r["ci95"][1], "unbounded")                       # P(no "a" in a draw) = (3/4)^4 = 0.32 > 2.5%: +inf at the top
        self.assertAlmostEqual(r["share_replicates_E_cmp_zero"], 0.75 ** 4, delta=0.03)
        self.assertGreater(r["replicates_dropped_0_over_0"], 0)           # draws of only c and d: 0/0, P = (1/2)^4
        self.assertAlmostEqual(r["replicates_dropped_0_over_0"] / 4000, 0.5 ** 4, delta=0.02)
        z = main_analysis.ratio_from_errors({"a": 1.0, "b": 0.5}, {"a": 0.0, "b": 0.0}, "t1", B=500)
        self.assertEqual((z["defined"], z["R"], z["comparator_note"]), (False, None, "comparator: 0 errors in 2"))
        self.assertAlmostEqual(z["comparator_error_rate_upper95"], 1 - 0.025 ** 0.5)          # A0: Clopper-Pearson, 0 of 2
        z80 = main_analysis.ratio_from_errors({str(i): 0.5 for i in range(80)}, {str(i): 0.0 for i in range(80)}, "t2", B=50)
        self.assertEqual(round(100 * z80["comparator_error_rate_upper95"], 2), 4.51)            # the note's own figure at n = 80
        self.assertEqual(len(z["e_ch_ci95"]), 2)
        self.assertEqual(main_analysis._ends([1.0, float("inf"), 0.5, float("inf")], 0.025, 0.975), [0.5, float("inf")])

    def test_batch_turnaround_from_the_ledger(self):
        td = Path(tempfile.mkdtemp())
        ev = [{"event": "send", "key": "a@1", "time": "2026-10-13T06:00:00+00:00"}, {"event": "send", "key": "b@1", "time": "2026-10-13T06:00:01+00:00"},
              {"event": "commit", "key": "a@1", "time": "2026-10-13T06:20:00+00:00"}, {"event": "commit", "key": "b@1", "time": "2026-10-13T06:30:00+00:00"}]
        (td / "ledger.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev))
        recs = [{"kind": "batch_submitted", "batch_id": "msgbatch_x", "wave_id": "w1", "keys": {"a": "a@1", "b": "b@1"}}]
        r = main_analysis.batch_turnaround(td, recs)
        self.assertEqual(r["msgbatch_x"], {"wave_id": "w1", "requests": 2, "turnaround_s": 1800.0, "settled_in_a_later_invocation": False})
        (td / "runner.log").write_text("INVOCATION 2026-10-13T05:59:00Z\nlive run started\nINVOCATION 2026-10-13T06:25:00Z\n")
        r2 = main_analysis.batch_turnaround(td, recs)["msgbatch_x"]                 # a re-run at 06:25 settled it: flagged
        self.assertEqual((r2["settled_in_a_later_invocation"], r2["flag"]), (True, "includes downtime (settled in a later invocation)"))
        self.assertEqual(main_analysis.batch_turnaround(Path(tempfile.mkdtemp()), recs)["computed"], False)

    def test_five_point_view_is_the_same_family_at_margin_5(self):
        from unittest import mock
        diffs = {"t1": [-7.0] * 20, "t2": [-3.0] * 20, "t3": [], "t4": [0.0] * 20, "t5": [-12.0] * 20}
        with mock.patch.object(five_tests, "test_differences", return_value=diffs):
            r = main_analysis.five_point_view([], {}, 0, 6, B=500)
        reading = {t: v["reading"] for t, v in r["tests"].items()}
        self.assertEqual(reading["t1"], "worse by more than the margin")   # -7 is beyond 5 points (non-inferior at 10)
        self.assertEqual((reading["t2"], reading["t4"]), ("non-inferior", "non-inferior"))
        self.assertEqual(reading["t5"], "worse by more than the margin")
        self.assertEqual((r["not_run"], r["margin"], r["label"]), (["t3"], -5.0, "secondary, 5-point margin"))
        self.assertEqual(r["tests"]["t3"], {"n": 0, "reading": "not run (k = 0: Haiku costs more per sample than the comparator)",
                                            "declared": False, "d": None, "ci95": None, "p": 1.0})

    def items2(self, shapes=("6x1", "1x6"), bases=(0, 1)):
        return {f"s-{b:03d}-{sh}": {"width": int(sh.split("x")[0]), "depth": int(sh.split("x")[1]), "base_index": b}
                for b in bases for sh in shapes}

    def row(self, iid, setup, sample, right, kind="answered"):
        sh = iid.rsplit("-", 1)[1]
        return {"item_id": iid, "base_id": iid.rsplit("-", 1)[0], "shape": sh, "setup": setup, "sample": sample, "kind": kind,
                "correct": right, "format_status": "ok", "stop_reason": "end_turn", "pieces_right": 6 if right else 3}

    def test_d42_by_hand_with_the_10_try_denominator(self):
        items = self.items2()
        hv, hm = [], []
        for iid in items:
            hv += [self.row(iid, "haiku-med-d42-variant", s, s <= 6) for s in range(1, 9)]       # 6 right, 2 wrong, 2 missing: 6/10
            hm += [self.row(iid, "haiku-med", s, s <= 4 or s > 10) for s in range(1, 41)]         # samples 1-10: 4 right: 4/10
        r = main_analysis.d42_robustness(hm, hv, 6, items, "s")
        for label in ("6x1", "1x6", "pooled"):
            self.assertAlmostEqual(r[label]["hv"], 0.6)
            self.assertAlmostEqual(r[label]["hm_1_10"], 0.4)
            self.assertAlmostEqual(r[label]["difference"], 0.2)
            self.assertEqual([round(x, 9) for x in r[label]["difference_ci95"]], [0.2, 0.2])
        self.assertEqual((r["n_puzzles"], r["hv_missing_tries"], r["hm_1_10_missing_tries"]), (4, 8, 0))
        self.assertEqual(r["6x1"]["hv_format_and_kinds"]["answered"], 16)

    def test_low_information_flag_by_hand_with_the_40_try_denominator(self):
        items = self.items2(shapes=("6x1",))
        rows = [self.row("s-000-6x1", "haiku-med", s, s <= 30) for s in range(1, 41)]            # 30/40
        rows += [self.row("s-001-6x1", "haiku-med", s, s <= 20) for s in range(1, 26)]           # 20/40: 15 missing count wrong
        r = main_analysis.low_information_flag(rows, 6, items)
        self.assertAlmostEqual(r["haiku_med_accuracy"], (0.75 + 0.5) / 2)
        self.assertEqual((r["fires"], r["missing_tries"]), (True, 15))
        self.assertTrue(r["label_test_1"].startswith("low information"))
        self.assertAlmostEqual(r["median"], 0.625)
        self.assertAlmostEqual(r["per_piece_accuracy"], ((30 * 1 + 10 * 0.5) / 40 + (20 * 1 + 5 * 0.5) / 40) / 2)
        rows2 = [self.row("s-000-6x1", "haiku-med", s, s <= 24) for s in range(1, 41)] + [self.row("s-001-6x1", "haiku-med", s, s <= 24) for s in range(1, 41)]
        self.assertFalse(main_analysis.low_information_flag(rows2, 6, items)["fires"])         # exactly 60%: not strictly above

    def test_flag_r_counts_by_hand(self):
        from unittest import mock

        def step(seq, k, cls, blame, written):
            return {"sequence": seq, "step": k, "cls": cls, "blame": blame, "written": written, "slipped": blame is not None}
        placed = {   # 1x6: first slip only; 6x1: every slipped piece; kind / decoy blames only
            "c1": [step(1, 1, "G", None, (0,)), step(1, 2, "T", "kind", (1, 2)), step(1, 3, "G", "kind", (7, 7))],
            "c2": [step(1, 1, "G", None, (0,)), step(1, 2, "T", "decoy_confusion", (1, 2))],
            "c3": [step(1, 1, "G", None, (0,)), step(1, 2, "T", "kind", (9, 9))],
            "c4": [step(1, 1, "G", "house_missed", (5,)), step(1, 2, "T", "kind", (1, 2))],     # first slip is a house blame: no event
            "p1": [step(1, 1, "G", "kind", (3,)), step(2, 1, "T", "kind", (4,))],
            "p2": [step(1, 1, "G", "kind", (3,)), step(2, 1, "T", "kind", (8,))],
        }
        rows = [{"setup": "haiku-med", "kind": "answered", "item_id": "x-000-1x6" if c[0] == "c" else "x-000-6x1", "custom_id": c,
                 "base_id": "x-000", "shape": "1x6" if c[0] == "c" else "6x1"} for c in placed]
        with mock.patch.object(main_analysis, "_puzzle", return_value=None), \
                mock.patch.object(scoring, "local_steps", side_effect=lambda text, pz: {"unplaceable": None, "steps": placed[text]}):
            r = main_analysis.flag_r_report(rows, {"x-000-1x6": {}, "x-000-6x1": {}}, {c: c for c in placed}, 6, B=50)
        # 1x6 cell (step 2, T): c1 (1,2), c2 (1,2), c3 (9,9): 3 pairs, 1 agreeing; 6x1: G cell (seq 1): 1 pair agreeing; T cell (seq 2): 1 pair not
        self.assertEqual((r["pairs_t"], r["agree_t"], r["pairs_g"], r["agree_g"]), (4, 1, 1, 1))
        self.assertFalse(r["flag_r"]["fires"])                                     # fewer than 10 pairs in each
        self.assertEqual(r["1x6"]["agreement_T"]["pairs"], 3)


@unittest.skipUnless(SIM.is_dir(), "research/fixtures/sim-main-v2 is not in this tree")
class RoundTripWithKarensSims(unittest.TestCase):
    """Karen's simulated rows -> a call log and frozen items synthesised to match them -> main_rows -> the same five_tests output.
    The synthetic replies reproduce each row's outcome: right or wrong, the same equality pattern of wrong traces, final answers and
    pieces, the format status, the slip type, the kind, stop reason, refusal category and cost. E3 rows are passed through unchanged on
    both sides (main_rows takes E3 rows from e3.e3_rows, tested in test_e3)."""

    CASE = "mixed"

    def synthesise(self, rows):
        L = rows[0]["line_count"]
        n = 24
        key = [[100 * k + j for j in range(L)] for k in range(1, n + 1)]
        pieces = [[1000 * k + j for j in range(L)] for k in range(1, n + 1)]
        idx = {}

        def code(base, field, value):
            d = idx.setdefault((base, field), {})
            return d.setdefault(value, len(d) + 1)

        items, recs, e3_rows = {}, [], []
        set_id = "sim-rt"
        for r in rows:
            b = int(r["base_id"][1:])
            for w, d in ((n, 1), (1, n)):
                iid = f"{set_id}-{b:03d}-{w}x{d}"
                items[iid] = {"id": iid, "width": w, "depth": d, "params": {"lines": L}, "style": "d31",
                              "chains": [{"states": key}], "answer": pieces, "base_index": b}
            if r["setup"] == "e3":
                e3_rows.append(dict(r, base_id=f"{set_id}-{b:03d}"))
                continue
            w, d = (n, 1) if r["shape"] == "24x1" else (1, n)
            iid = f"{set_id}-{b:03d}-{w}x{d}"
            text = None
            if r["kind"] == "answered" and r["shape"] == "24x1":
                if r["correct"]:
                    text = pieces_text(pieces)
                elif r["answer_key"] is None:
                    text = "Answer: nothing"
                else:
                    text = pieces_text([bump(pieces[0], code(b, "a24", r["answer_key"]))] + pieces[1:])
            elif r["kind"] == "answered":
                fs = r["format_status"]
                fin = key[-1] if r["correct_final"] else bump(key[-1], 1000 + code(b, "final", r["final_key"]))
                if fs == "ok":
                    t = code(b, "trace", r["trace_key"])
                    st = [list(s) for s in key]
                    if r["slip_type"] == "copy":
                        st[(t - 1) % (n - 1)] = bump(st[(t - 1) % (n - 1)], 1 + (t - 1) // (n - 1))
                    elif r["slip_type"] == "absorbed":
                        st[0] = bump(st[0], 50 + t)
                        st[1] = bump(st[1], 50 + t)
                    elif r["slip_type"] == "real":
                        st[0] = bump(st[0], 50 + t)
                        st[-1] = fin
                    text = chain_text(st)
                else:
                    lines = [f"1.{k} = {ledger.fmt(s)}" for k, s in enumerate(key, 1)]
                    answer = f"Answer: 1 = {ledger.fmt(fin)}"
                    if fs == "misnumbered":
                        lines.append("1.25 = [1]")
                    elif fs == "extra_line":
                        lines.append(f"1.3 = {ledger.fmt(bump(key[2], 7))}")
                    elif fs == "missing_line":
                        lines = lines[1:]
                    elif fs == "non_integer":
                        lines[0] = "1.1 = [1, x]"
                    elif fs == "wrong_length":
                        lines[0] = "1.1 = [1]"
                    elif fs == "no_answer":
                        answer = ""
                    elif fs == "answer_mismatch" and r["correct_final"]:        # line 24 wrong, the Answer line right
                        lines[-1] = f"1.24 = {ledger.fmt(bump(key[-1], 3))}"
                    text = "\n".join(lines + [answer])
            setup_tag = {"haiku-med": "hm", "opus-med": "om", "opus-low": "ol", "sonnet-med": "sm"}[r["setup"]]
            recs.append({"custom_id": f"{iid}-{setup_tag}-{len(recs):05d}", "final": True, "kind": r["kind"], "stop_reason": r["stop_reason"],
                         "refusal_category": r["refusal_category"], "cost_usd": r["cost_usd"], "answer_text": text,
                         "requested_model": HAIKU, "effort": "medium",
                         "meta": {"set_id": set_id, "item_id": iid, "base_index": b, "width": w, "depth": d, "setup": setup_tag,
                                  "setting": r.get("preset"), "sample": r.get("try")}})
        return items, recs, e3_rows

    def test_the_converter_rebuilds_rows_that_give_the_same_five_tests_output(self):
        with gzip.open(SIM / self.CASE / "rows.jsonl.gz", "rt") as f:
            sim = [json.loads(ln) for ln in f if ln.strip()]
        items, recs, e3_rows = self.synthesise(sim)
        td = Path(tempfile.mkdtemp()) / "sim-rt"
        td.mkdir()
        (td / "manifest.json").write_text(json.dumps({"set_id": "sim-rt", "family": "ledger", "setting": "sim"}))
        (td / "items.jsonl").write_text("".join(json.dumps(it) + "\n" for it in items.values()))
        built = main_rows.build(td, [], records=recs)
        mine = built["tests"] + e3_rows
        sim_rows = [dict(r, base_id=f"sim-rt-{int(r['base_id'][1:]):03d}") for r in sim]
        for a, b in ((sim_rows, mine),):
            k1, k2 = five_tests.k_from_rows(a, n=24), five_tests.k_from_rows(b, n=24)
            self.assertEqual(json.dumps(k1, sort_keys=True, default=str), json.dumps(k2, sort_keys=True, default=str))
            kv = main_analysis.k_values(k1, 24)
            for score in ("official", "final", "copy_forgiven"):
                for view in ("as_deployed", "refusals_out", "truncations_out"):
                    ra = five_tests.analyse(a, kv["k_o"], kv["k_s"], view, B=300, score=score, n=24)
                    rb = five_tests.analyse(b, kv["k_o"], kv["k_s"], view, B=300, score=score, n=24)
                    self.assertEqual(json.dumps(ra, sort_keys=True, default=str), json.dumps(rb, sort_keys=True, default=str), (score, view))


if __name__ == "__main__":
    unittest.main()
