"""D-86: the analysis at N steps (N in 4, 6, 8, 12, 16; 24 unchanged). Karen's N-step parse fixtures, grading at N = 6, the ladder
pick (choose_preset over l14n4 .. l14n16, a tie goes to fewer steps, Haiku-medium only) and the five tests at N = 6."""

import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from harness.analysis import five_tests as ft, scoring
from harness.analysis.choose_preset import choose_preset, load_set_info, main, read_haiku_medium_replies, summary, trace_grades
from harness.taskgen import ledger
from harness.taskgen.rng import derive_seed

ROOT = Path(__file__).resolve().parents[2]
RUNNER_N = ROOT / "research" / "fixtures" / "sim-main-n" / "run_parse_cases_n.py"
HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"
L14_KINDS = list(ledger.SETTINGS["l14"].kinds)


def key(n):
    """A made-up N-step key, three balances per state (the same form as the 24-step KEY of test_analysis_scoring)."""
    return [(100 + k, 200 + k, 300 + k) for k in range(1, n + 1)]


def chain_text(states, answer=None):
    ans = states[-1] if answer is None else answer
    return "\n".join([f"1.{k} = {ledger.fmt(st)}" for k, st in enumerate(states, 1)] + [f"Answer: 1 = {ledger.fmt(ans)}"])


def pieces_text(pieces):
    return "Answer: " + ", ".join(f"{i} = {v if isinstance(v, str) else ledger.fmt(v)}" for i, v in enumerate(pieces, 1))


class KarensParseCasesAtN(unittest.TestCase):
    def test_every_case_passes(self):
        r = subprocess.run([sys.executable, str(RUNNER_N), str(ROOT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        m = re.search(r"(\d+) of (\d+) cases pass", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertEqual(m.group(1), m.group(2), r.stdout)
        self.assertGreaterEqual(int(m.group(2)), 720, "fewer N-step parse cases than Karen's 720")


class Shapes(unittest.TestCase):
    def test_chain_and_pieces_shapes_at_any_n(self):
        for n in (4, 6, 8, 12, 16, 24):
            self.assertTrue(scoring.is_chain_shape(f"1x{n}"))
            self.assertTrue(scoring.is_pieces_shape(f"{n}x1"))
            self.assertFalse(scoring.is_chain_shape(f"{n}x1"))
            self.assertFalse(scoring.is_pieces_shape(f"1x{n}"))
            self.assertEqual((scoring.chain_shape(n), scoring.pieces_shape(n), scoring.shape_steps(f"1x{n}")), (f"1x{n}", f"{n}x1", n))
        for bad in ("1x1", "6x4", "x6", "1x", "abc", None, "", " 1x6"):
            self.assertFalse(scoring.is_chain_shape(bad) or scoring.is_pieces_shape(bad), bad)
        self.assertEqual(scoring.shape_dims("12x2"), (12, 2))
        self.assertIsNone(scoring.shape_steps("nope"))
        self.assertEqual(scoring.TRACE_SHAPE, "1x24")

    def test_trace_rows_by_shape_form(self):
        for shape, want in (("1x6", True), ("1x24", True), ("6x1", False), ("24x1", False)):
            self.assertEqual(scoring.is_trace_row({"shape": shape, "setup": "haiku-med"}), want, shape)
        self.assertFalse(scoring.is_trace_row({"shape": "1x6", "setup": "e3"}))
        self.assertFalse(scoring.is_trace_row({"shape": "1x6", "setup": "haiku-med", "answer_only": True}))
        mix = [{"shape": "1x6", "setup": "haiku-med", "answer_only": True}, {"shape": "1x6", "setup": "opus-med", "answer_only": False}]
        with self.assertRaises(ValueError):
            scoring.check_answer_only(mix)

    def test_aliases(self):
        self.assertIs(scoring.grade_chain, scoring.grade_1x24)
        self.assertIs(scoring.grade_pieces, scoring.grade_24x1)
        self.assertIs(scoring.rates_chain, scoring.rates_1x24)


class GradeAtSix(unittest.TestCase):
    K = key(6)

    def test_chain_right_slipped_and_wrong_length(self):
        g = scoring.grade_chain(chain_text(self.K), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"], g["slip_type"], g["correct_final"]), ("ok", True, "none", True))
        self.assertEqual(g["trace_key"], scoring.trace_key(self.K))
        copy = list(self.K)
        copy[2] = (1, 2, 3)                                                  # line 3 wrong, line 4 right: a copy slip
        g = scoring.grade_chain(chain_text(copy), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"], g["slip_type"], g["copy_line"], g["correct_copy_forgiven"], g["correct_final"]),
                         ("ok", False, "copy", 3, True, True))
        last = list(self.K)
        last[5] = (9, 9, 9)                                                  # line 6 (the last) wrong: a real slip
        g = scoring.grade_chain(chain_text(last), self.K, 3)
        self.assertEqual((g["correct"], g["slip_type"], g["correct_final"], g["correct_copy_forgiven"]), (False, "real", False, False))
        g = scoring.grade_chain(chain_text(self.K[:5]), self.K, 3)          # five step lines for a six-step chain
        self.assertEqual((g["format_status"], g["correct"]), ("missing_line", False))
        g = scoring.grade_chain(chain_text(key(24)[:6] + [(1, 1, 1)]), self.K, 3)    # a seventh line: 1.7 is outside 1.1 to 1.6
        self.assertEqual((g["format_status"], g["correct"]), ("misnumbered", False))
        g = scoring.grade_chain(chain_text(key(24)), self.K, 3)             # a whole 24-step reply
        self.assertEqual(g["format_status"], "misnumbered")
        short = list(self.K)
        short[1] = (1, 2)
        g = scoring.grade_chain(chain_text(short), self.K, 3)               # a state with two balances, not three
        self.assertEqual((g["format_status"], g["correct"]), ("wrong_length", False))
        self.assertEqual(scoring.grade_1x24(chain_text(self.K), self.K, 3), scoring.grade_chain(chain_text(self.K), self.K, 3))

    def test_pieces_right_slipped_and_wrong_length(self):
        g = scoring.grade_pieces(pieces_text(self.K), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"], g["pieces_right"]), ("ok", True, 6))
        one = list(self.K)
        one[3] = (1, 2, 3)
        g = scoring.grade_pieces(pieces_text(one), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"], g["pieces_right"]), ("ok", False, 5))
        g = scoring.grade_pieces(pieces_text(self.K[:5]), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"]), ("missing_line", False))
        g = scoring.grade_pieces(pieces_text(self.K + [(1, 1, 1)]), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"]), ("misnumbered", False))
        g = scoring.grade_pieces(pieces_text(self.K[:2] + ["[1, 2]"] + self.K[3:]), self.K, 3)
        self.assertEqual((g["format_status"], g["correct"]), ("wrong_length", False))

    def test_a_real_l14n6_puzzle_in_both_shapes(self):
        seed = derive_seed("test-n-steps", 6)
        chain = ledger.generate(seed, 1, 6, ledger.SETTINGS["l14n6"])
        pieces = ledger.generate(seed, 6, 1, ledger.SETTINGS["l14n6"])
        states = chain.chains[0].states
        self.assertEqual(len(states), 6)
        self.assertTrue(scoring.all_step_lines_right(chain_text(states), chain))
        self.assertFalse(scoring.all_step_lines_right(chain_text(states[:5]), chain))
        self.assertTrue(scoring.all_step_lines_right(pieces_text(pieces.answer), pieces))
        res = scoring.local_steps(chain_text(states), chain)
        self.assertEqual((res["unplaceable"], len(res["steps"]), any(s["slipped"] for s in res["steps"])), (None, 6, False))
        bad = [list(s) for s in states]
        bad[2] = [v + 1 for v in bad[2]]
        res = scoring.local_steps(chain_text(bad), chain)
        self.assertTrue(res["steps"][2]["slipped"])
        self.assertEqual(scoring.first_slip_steps(chain_text(bad), chain)["signature"][:2], (1, 3))

    def test_rates_over_1x6_rows(self):
        rows = []
        for text in (chain_text(self.K), chain_text(self.K[:5])):
            r = {"base_id": "b1", "setup": "haiku-med", "shape": "1x6", "kind": "answered"}
            r.update(scoring.grade_chain(text, self.K, 3))
            rows.append(r)
        rates = scoring.rates_chain(rows)["haiku-med"]
        self.assertEqual((rates["tries"], rates["format_ok"], rates["official_acc"]), (2, 1, 0.5))


# ---------------------------------------------------------------- the ladder pick (D-86: D-36(4) at N, ties to fewer steps)

class LadderPick(unittest.TestCase):
    """Ladder sets l14n4 .. l14n16 as tiny frozen-set folders; Haiku-medium replies decide; Opus and Sonnet rows are present but never read."""

    def write_set(self, root, n, n_base=2, chars=500):
        sid = f"ladder-ledger-l14n{n}-v1"
        d = Path(root) / sid
        d.mkdir()
        items = []
        for b in range(n_base):
            params = {"kinds": L14_KINDS, "lines": 3, "total_steps": n}
            items.append({"id": f"{sid}-{b:03d}-{n}x1", "width": n, "depth": 1, "prompt": "x" * chars, "params": params,
                          "answer": [list(s) for s in key(n)]})
            items.append({"id": f"{sid}-{b:03d}-1x{n}", "width": 1, "depth": n, "prompt": "x" * chars, "params": params,
                          "chains": [{"states": [list(s) for s in key(n)]}], "style": "d31"})
        (d / "items.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
        (d / "manifest.json").write_text(json.dumps({"set_id": sid, "setting": f"l14n{n}", "family": "ledger", "items_sha256": "ab" * 32}))
        return d

    def write_run(self, root, rights, tries=10, n_base=2):
        """The compact table and the call log for a ladder run: per preset N, every puzzle has rights[N] right Haiku tries of `tries`.
        The table's `right` is 1 everywhere (it must not be read for a ledger try); every puzzle also has Opus and Sonnet rows and
        records, and there are Opus and Sonnet records that would break the reader if it ever looked at them."""
        table_rows, recs = [], []
        for n, nr in rights.items():
            sid = f"ladder-ledger-l14n{n}-v1"
            for b in range(n_base):
                for shape in (f"{n}x1", f"1x{n}"):
                    right = chain_text(key(n)) if shape.startswith("1x") else pieces_text(key(n))
                    wrong = chain_text(key(n)[:-1] + [(1, 1, 1)]) if shape.startswith("1x") else pieces_text([(1, 1, 1)] + key(n)[1:])
                    for t in range(1, tries + 1):
                        cid = f"{sid}-{b:03d}-{shape}-hm-{t:02d}"
                        table_rows.append({"custom_id": cid, "requested_model": HAIKU, "effort": "medium", "cost_usd": "0.001",
                                           "kind": "answered", "right": "1"})
                        recs.append({"custom_id": cid, "requested_model": HAIKU, "effort": "medium", "kind": "answered",
                                     "answer_text": right if t <= nr else wrong, "final": True})
                    for tag, model in (("om", OPUS), ("sm", SONNET)):
                        cid = f"{sid}-{b:03d}-{shape}-{tag}-01"
                        table_rows.append({"custom_id": cid, "requested_model": model, "effort": "medium", "cost_usd": "0.05",
                                           "kind": "answered", "right": ""})
                        recs.append({"custom_id": cid, "requested_model": model, "effort": "medium", "kind": "answered",
                                     "answer_text": right, "final": True})
        for tag, model in (("om", OPUS), ("sm", SONNET)):                    # tripwires: unreadable ids, an unknown set
            recs.append({"custom_id": "not an id", "requested_model": model, "effort": "medium", "kind": "answered", "answer_text": "x",
                         "final": True})
            table_rows.append({"custom_id": f"unknown-set-v1-000-1x6-{tag}-01", "requested_model": model, "effort": "medium",
                               "cost_usd": "0.05", "kind": "answered", "right": "1"})
        log = Path(root) / "calls.jsonl"
        log.write_text("".join(json.dumps(r) + "\n" for r in recs))
        table = Path(root) / "table.csv"
        cols = ["custom_id", "requested_model", "effort", "cost_usd", "kind", "right"]
        table.write_text(",".join(cols) + "\n" + "".join(",".join(r[c] for c in cols) + "\n" for r in table_rows))
        return table_rows, log, table

    def pick(self, rights, tries=10, chars=None):
        chars = chars or {}
        with tempfile.TemporaryDirectory() as td:
            dirs = [self.write_set(td, n, chars=chars.get(n, 500)) for n in rights]
            rows, log, _ = self.write_run(td, rights, tries)
            sets = [load_set_info(d) for d in dirs]
            trace = trace_grades(read_haiku_medium_replies([log]), sets)
            self.assertTrue(all(c.split("-")[-2] == "hm" for c in trace))  # only Haiku-medium replies are graded
            return choose_preset(rows, sets, trace=trace)

    def test_set_info_reads_the_steps(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_set(td, 6))
            self.assertEqual(info["steps"], [6])
            self.assertEqual({k["shape"] for k in info["keys"].values()}, {"6x1", "1x6"})

    def test_picks_the_n_closest_to_0375_within_the_band(self):
        r = self.pick({4: 7, 6: 5, 8: 4, 12: 2, 16: 1})                    # 0.7, 0.5, 0.4, 0.2, 0.1
        self.assertEqual((r["pick"]["preset"], r["pick"]["tier"], r["pick"]["tie_broken"]), ("l14n8", 1, False))
        by = {p["preset"]: p for p in r["presets"]}
        self.assertEqual({p: by[p]["score"] for p in by}, {"l14n4": 0.7, "l14n6": 0.5, "l14n8": 0.4, "l14n12": 0.2, "l14n16": 0.1})
        self.assertEqual(by["l14n8"]["shape_medians"], {"1x8": 0.4, "8x1": 0.4})
        self.assertEqual({p: by[p]["n_steps"] for p in by}, {"l14n4": 4, "l14n6": 6, "l14n8": 8, "l14n12": 12, "l14n16": 16})
        self.assertEqual((by["l14n8"]["format_compliance_1x24"], by["l14n8"]["format_compliance_24x1"]), (1.0, 1.0))
        self.assertNotIn("opus", json.dumps(r).lower())
        self.assertNotIn("sonnet", json.dumps(r).lower())

    def test_a_tie_goes_to_fewer_steps(self):
        # 0.45 and 0.30 are both 0.075 from 0.375; same rule kinds; the 6-step prompts are LONGER, so the old K2 order alone would
        # pick l14n8: fewer steps comes first
        for rights in ({6: 9, 8: 6}, {6: 6, 8: 9}, {4: 15, 6: 9, 8: 6, 12: 2, 16: 0}):
            r = self.pick(rights, tries=20, chars={4: 300, 6: 900, 8: 500})
            want = "l14n6"
            self.assertEqual((r["pick"]["preset"], r["pick"]["tie_broken"]), (want, True), rights)
            self.assertIn("l14n8", r["pick"]["tied_with"])
            self.assertIn("fewer steps, then fewer rule kinds", summary(r))
        r = self.pick({6: 9, 12: 6}, tries=20, chars={6: 900, 12: 100})
        self.assertEqual((r["pick"]["preset"], r["pick"]["tied_with"]), ("l14n6", ["l14n12"]))

    def test_tier_2_closest_within_15_60_and_its_tie_also_goes_to_fewer_steps(self):
        r = self.pick({4: 7, 6: 6, 8: 2, 12: 1, 16: 0})                    # 0.7, 0.6, 0.2, 0.1, 0.0: none in [0.25, 0.50]
        self.assertEqual((r["pick"]["preset"], r["pick"]["tier"], r["pick"]["band_miss"]), ("l14n8", 2, 0.05))
        r = self.pick({4: 14, 6: 11, 8: 4, 12: 1, 16: 0}, tries=20, chars={6: 900, 8: 100})   # 0.55 and 0.20: both 0.175 away
        self.assertEqual((r["pick"]["preset"], r["pick"]["tier"], r["pick"]["tie_broken"]), ("l14n6", 2, True))

    def test_tier_3_returns_to_the_user(self):
        r = self.pick({4: 1, 6: 1, 8: 0, 12: 0, 16: 0})                    # all below 0.15
        self.assertIsNone(r["pick"])
        self.assertEqual((r["tier"], r["outside_15_60_return_to_user"], r["extra_rung_needed"]), (3, True, False))

    def test_tier_3_with_every_length_above_60_also_returns_to_the_user(self):
        # Edith L3-1: the ladder has no further rung, so never extra_rung_needed
        r = self.pick({4: 10, 6: 10, 8: 9, 12: 8, 16: 7})                 # 1.0, 1.0, 0.9, 0.8, 0.7
        self.assertIsNone(r["pick"])
        self.assertEqual((r["tier"], r["outside_15_60_return_to_user"], r["extra_rung_needed"]), (3, True, False))
        r = self.pick({16: 7})                                             # one length alone, above 0.60
        self.assertEqual((r["tier"], r["outside_15_60_return_to_user"], r["extra_rung_needed"]), (3, True, False))

    def test_every_preset_row_gives_n_steps_and_the_rule_says_what_1x24_means(self):
        r = self.pick({4: 7, 6: 4, 8: 2})
        self.assertEqual({p["preset"]: p["n_steps"] for p in r["presets"]}, {"l14n4": 4, "l14n6": 6, "l14n8": 8})
        self.assertIn("every 1x24 above means the 1xN chain", r["rule"])

    def test_the_cli_with_other_rows_allowed_never_reads_opus_or_sonnet(self):
        with tempfile.TemporaryDirectory() as td:
            dirs = [self.write_set(td, n) for n in (4, 6, 8)]
            _, log, table = self.write_run(td, {4: 7, 6: 4, 8: 2})
            out = Path(td) / "pick.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["choose", "--table", str(table), "--sets", *map(str, dirs), "--replies", str(log), "--out", str(out),
                             "--allow-other-rows"])
            self.assertEqual(code, 0)
            res = json.loads(out.read_text())
            self.assertEqual(res["pick"]["preset"], "l14n6")
            self.assertEqual(res["n_rows"], 3 * 4 * 10)                     # Haiku-medium rows only
            self.assertNotIn("opus", out.read_text().lower())


# ---------------------------------------------------------------- the five tests at N

SETUPS = ("haiku-med", "opus-med", "opus-low", "sonnet-med")
COST = {"haiku-med": "0.001", "opus-med": "0.02", "opus-low": "0.012", "sonnet-med": "0.01"}


def synthetic_rows(n, n_bases=8):
    """A small main-run dataset at N steps, graded by the real scorers. Which tries are right depends only on the base, the setup and
    the sample number, never on N, so the same dataset at 24 and at 6 must give the same results."""
    k = key(n)
    rows = []
    for b in range(n_bases):
        for si, setup in enumerate(SETUPS):
            for shape in (scoring.pieces_shape(n), scoring.chain_shape(n)):
                samples = 40 if setup == "haiku-med" else 1
                for t in range(samples):
                    right = (b * 3 + si * 5 + t * 7) % 10 < (6 if setup == "haiku-med" else 5 + (b % 3))
                    if scoring.is_chain_shape(shape):
                        states = list(k) if right else k[:1] + [(t % 3, 0, 0)] + k[2:]       # a wrong line 2, three different ways
                        g = scoring.grade_chain(chain_text(states), k, 3)
                    else:
                        pieces = list(k) if right else [(t % 3, 0, 0)] + k[1:]
                        g = scoring.grade_pieces(pieces_text(pieces), k, 3)
                    r = {"base_id": f"b{b}", "setup": setup, "shape": shape, "kind": "answered", "cost_usd": COST[setup],
                         "stop_reason": "end_turn"}
                    r.update(g)
                    rows.append(r)
        for run in range(3):
            steps = [(b + run + s) % 4 != 0 if s < 3 else True for s in range(n)]      # slips in the first 3 steps only
            rows.append({"base_id": f"b{b}", "setup": "e3", "shape": scoring.chain_shape(n), "kind": "answered", "cost_usd": "0.03",
                         "stop_reason": "end_turn", "correct": all(steps), "answer_key": None, "step_correct": steps})
    return rows


def k_inputs(rows, n):
    kk = ft.k_from_rows(rows)
    return ({sh: kk["opus"][sh]["k"] for sh in (scoring.pieces_shape(n), scoring.chain_shape(n))},
            kk["sonnet"][scoring.chain_shape(n)]["k"])


def relabel(obj, n):
    """`obj` as JSON text with the N-step shape names written as the 24-step ones (for comparing results; tuples become lists and NaN
    is compared as text)."""
    return json.dumps(obj, sort_keys=True).replace(f'"{n}x1"', '"24x1"').replace(f'"1x{n}"', '"1x24"')


class FiveTestsAtN(unittest.TestCase):
    def test_the_table_at_24_is_the_original_and_at_6_has_the_6_step_shapes(self):
        self.assertEqual(ft.TESTS, {"t1": ("haiku-med", "opus-med", "24x1", "O"), "t2": ("haiku-med", "opus-med", "1x24", "O"),
                                    "t3": ("haiku-med", "sonnet-med", "1x24", "S"), "t4": ("e3", "opus-med", "1x24", None),
                                    "t5": ("opus-low", "sonnet-med", "1x24", None)})
        self.assertEqual(ft.tests_for(24), ft.TESTS)
        self.assertEqual(ft.tests_for(6), {"t1": ("haiku-med", "opus-med", "6x1", "O"), "t2": ("haiku-med", "opus-med", "1x6", "O"),
                                           "t3": ("haiku-med", "sonnet-med", "1x6", "S"), "t4": ("e3", "opus-med", "1x6", None),
                                           "t5": ("opus-low", "sonnet-med", "1x6", None)})

    def test_the_length_is_read_from_the_rows(self):
        self.assertEqual(ft.steps_of([]), 24)
        self.assertEqual(ft.steps_of([{"shape": "1x6"}, {"shape": "6x1"}, {"base_id": "x"}]), 6)
        self.assertEqual(ft.steps_of([{"shape": "1x6"}, {"shape": "1x8"}], n=8), 8)
        with self.assertRaises(ValueError):
            ft.steps_of([{"shape": "1x6"}, {"shape": "1x8"}])

    def test_n6_gives_the_same_structure_and_numbers_as_24(self):
        r6, r24 = synthetic_rows(6), synthetic_rows(24)
        ko6, ks6 = k_inputs(r6, 6)
        ko24, ks24 = k_inputs(r24, 24)
        self.assertEqual((ko6, ks6), ({"6x1": 20, "1x6": 20}, 10))
        self.assertEqual(relabel(ko6, 6), relabel(ko24, 24))
        self.assertEqual(ks6, ks24)
        d6 = ft.test_differences(r6, ko6, ks6)
        self.assertEqual(set(d6), {"t1", "t2", "t3", "t4", "t5"})
        self.assertTrue(all(len(v) == 8 for v in d6.values()))
        self.assertEqual(d6, ft.test_differences(r24, ko24, ks24))
        self.assertEqual(d6, ft.test_differences(r6, ko6, ks6, n=6))
        a6 = ft.analyse_all_views(r6, ko6, ks6, B=300)
        a24 = ft.analyse_all_views(r24, ko24, ks24, B=300)
        self.assertEqual(set(a6["format_compliance"]["haiku-med"]), {"6x1", "1x6"})
        self.assertEqual(relabel(a6, 6), relabel(a24, 24))
        self.assertEqual(relabel(ft.rates(r6), 6), relabel(ft.rates(r24), 24))
        sec6, sec24 = ft.analyse_secondary(r6, ko6, ks6, B=200), ft.analyse_secondary(r24, ko24, ks24, B=200)
        self.assertEqual(relabel(sec6, 6), relabel(sec24, 24))
        self.assertEqual(relabel(ft.tie_report(r6, ko6, ks6, B=200), 6), relabel(ft.tie_report(r24, ko24, ks24, B=200), 24))

    def test_a_6_step_run_with_24_step_k_keys_fails_loudly(self):
        r6 = synthetic_rows(6, n_bases=2)
        with self.assertRaises(KeyError):
            ft.test_differences(r6, {"24x1": 5, "1x24": 5}, 5)


if __name__ == "__main__":
    unittest.main()
