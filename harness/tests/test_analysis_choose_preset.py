import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from harness.analysis.choose_preset import (RULE_TEXT, choose_preset, extract_haiku_medium, load_haiku_medium_rows,
                                            load_set_info, main, read_haiku_medium_replies, right_value, rows_sha256, rule_kinds,
                                            summary, trace_grades)
from harness.taskgen import ledger
from harness.tests.test_analysis_scoring import KEY, MIDDLE_WRONG, trace_text

HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"
FIELDS = ["custom_id", "requested_model", "effort", "cost_usd", "kind", "right"]


def set_info(preset, kinds=("affine", "table"), chars=1000, n_base=4):
    sid = f"pilot-{preset}-v1"
    return {"set_id": sid, "setting": preset, "family": "digits", "items_sha256": "f" * 64, "kinds": set(kinds),
            "prompt_chars": [chars] * (2 * n_base),
            "puzzles": {f"{sid}-{b:03d}-{sh}" for b in range(n_base) for sh in ("24x1", "1x24")}}


def haiku_rows(preset, right_24x1, right_1x24=None, n_base=4, tries=10, blank_instead_of_zero=False):
    """Every puzzle of a shape gets `right_*` right tries out of `tries`; the rest are 0 (or blank)."""
    right_1x24 = right_24x1 if right_1x24 is None else right_1x24
    sid = f"pilot-{preset}-v1"
    rows = []
    for b in range(n_base):
        for shape, nr in (("24x1", right_24x1), ("1x24", right_1x24)):
            for n in range(1, tries + 1):
                bad = "" if blank_instead_of_zero else "0"
                rows.append({"custom_id": f"{sid}-{b:03d}-{shape}-hm-{n:02d}", "requested_model": HAIKU, "effort": "medium",
                             "cost_usd": "0.01", "kind": "answered", "right": "1" if n <= nr else bad})
    return rows


def acc_rows(preset, rights, tries=10):
    """One puzzle per entry of `rights` (base 0 24x1, base 0 1x24, base 1 24x1, ...): that many right tries of `tries`."""
    sid = f"pilot-{preset}-v1"
    rows = []
    for j, nr in enumerate(rights):
        b, shape = j // 2, ("24x1", "1x24")[j % 2]
        for n in range(1, tries + 1):
            rows.append({"custom_id": f"{sid}-{b:03d}-{shape}-hm-{n:02d}", "requested_model": HAIKU, "effort": "medium",
                         "cost_usd": "0.01", "kind": "answered", "right": "1" if n <= nr else "0"})
    return rows


def pieces_text(over=None, head="Answer:", tail=""):
    """A 24x1 reply: the 24 pieces of KEY (the 24x1 key used here) on one Answer line, `over` {piece: state or raw text} swapped in."""
    over = over or {}
    vals = [over.get(i, st) for i, st in enumerate(KEY, 1)]
    return f"{head} " + ", ".join(f"{i} = {v if isinstance(v, str) else ledger.fmt(v)}" for i, v in enumerate(vals, 1)) + tail


def pick_of(result):
    return None if result["pick"] is None else result["pick"]["preset"]


def other_rows(preset, n_base=4):
    sid = f"pilot-{preset}-v1"
    rows = []
    for b in range(n_base):
        for shape in ("24x1", "1x24"):
            rows.append({"custom_id": f"{sid}-{b:03d}-{shape}-om-01", "requested_model": OPUS, "effort": "medium",
                         "cost_usd": "0.987654", "kind": "answered", "right": "1"})
            rows.append({"custom_id": f"{sid}-{b:03d}-{shape}-sm-01", "requested_model": SONNET, "effort": "medium",
                         "cost_usd": "0.123456", "kind": "answered", "right": "1"})
            rows.append({"custom_id": f"{sid}-{b:03d}-{shape}-hl-01", "requested_model": HAIKU, "effort": "low",
                         "cost_usd": "0.002", "kind": "answered", "right": "1"})
    return rows


class Choose(unittest.TestCase):
    def test_in_band_closest_wins(self):
        rows = haiku_rows("pa", 2) + haiku_rows("pb", 3) + haiku_rows("pc", 4) + haiku_rows("pd", 6)
        sets = [set_info(p) for p in ("pa", "pb", "pc", "pd")]
        r = choose_preset(rows, sets)
        scores = {p["preset"]: p["score"] for p in r["presets"]}
        self.assertEqual(scores, {"pa": 0.2, "pb": 0.3, "pc": 0.4, "pd": 0.6})
        self.assertEqual(r["pick"]["preset"], "pc")
        self.assertTrue(r["pick"]["in_band"] and not r["pick"]["tie_broken"])
        self.assertEqual((r["pick"]["tier"], r["pick"]["band_miss"], r["tier"]), (1, 0.0, 1))
        self.assertEqual((r["extra_rung_needed"], r["outside_15_60_return_to_user"]), (False, False))
        pc = [p for p in r["presets"] if p["preset"] == "pc"][0]
        self.assertEqual((pc["n_puzzles"], pc["n_tries"], pc["mean"]), (8, 80, 0.4))
        self.assertEqual(pc["shape_medians"], {"1x24": 0.4, "24x1": 0.4})

    def test_exactly_025_and_050_are_in_tier_1(self):
        for rights, tries, want in ((1, 4, 0.25), (1, 2, 0.5)):
            r = choose_preset(haiku_rows("pa", rights, tries=tries) + haiku_rows("pb", 3, tries=4), [set_info("pa"), set_info("pb")])
            by = {p["preset"]: p for p in r["presets"]}
            self.assertEqual((by["pa"]["score"], by["pa"]["tier"], by["pa"]["in_band"]), (want, 1, True))
        for rights, tries in ((1, 4), (1, 2)):                                   # a lone preset at each edge: tier 1, no miss
            r = choose_preset(haiku_rows("pa", rights, tries=tries), [set_info("pa")])
            self.assertEqual((r["pick"]["tier"], r["pick"]["band_miss"], r["pick"]["in_band"]), (1, 0.0, True))
        # 0.50 (d 0.125, tier 1) beats 0.55 (d 0.175, tier 2); and a tier 1 preset wins over a nearer-looking tier 2 one
        r = choose_preset(haiku_rows("pa", 11, tries=20) + haiku_rows("pb", 1, tries=2), [set_info("pa"), set_info("pb")])
        self.assertEqual(pick_of(r), "pb")
        r = choose_preset(haiku_rows("pa", 11, tries=20) + haiku_rows("pb", 1, tries=4), [set_info("pa"), set_info("pb")])
        self.assertEqual(pick_of(r), "pb")                                       # 0.25 is tier 1; 0.55 is tier 2 and not looked at

    def test_tier_edges(self):
        want = {(2, 10): 2, (3, 20): 2, (6, 10): 2, (13, 20): 3, (1, 10): 3, (7, 10): 3}   # 0.2, 0.15, 0.6, 0.65, 0.1, 0.7
        for (nr, tries), tier in want.items():
            r = choose_preset(haiku_rows("pa", nr, tries=tries), [set_info("pa")])
            self.assertEqual(r["presets"][0]["tier"], tier, (nr, tries))

    def test_target_itself_wins_and_has_distance_zero(self):
        r = choose_preset(haiku_rows("pa", 3, tries=8) + haiku_rows("pb", 4, tries=10), [set_info("pa"), set_info("pb")])
        self.assertEqual(pick_of(r), "pa")                                       # 3/8 = 0.375 exactly
        self.assertEqual(r["presets"][0]["distance"], 0.0)
        self.assertEqual(r["pick"]["score"], 0.375)
        self.assertFalse(r["pick"]["tie_broken"])

    def test_score_is_median_not_mean(self):
        # eight puzzles: mean 0.40 is in the band, median 0.10 is not
        r = choose_preset(acc_rows("pa", [0, 0, 0, 1, 1, 10, 10, 10]) + haiku_rows("pb", 2, 6), [set_info("pa"), set_info("pb")])
        pa = [p for p in r["presets"] if p["preset"] == "pa"][0]
        self.assertAlmostEqual(pa["mean"], 0.4)
        self.assertAlmostEqual(pa["score"], 0.1)
        self.assertEqual((pa["tier"], pa["in_band"]), (3, False))
        self.assertEqual(pick_of(r), "pb")                                       # pb (0.4) is picked; pa (mean 0.4, median 0.1) is not
        # the other way round: median 0.4 is in band although the mean (0.625) is not
        r = choose_preset(acc_rows("pa", [4, 4, 4, 4, 4, 10, 10, 10]), [set_info("pa")])
        self.assertEqual((r["presets"][0]["score"], r["pick"]["tier"]), (0.4, 1))
        self.assertAlmostEqual(r["presets"][0]["mean"], 0.625)

    def test_score_is_median_over_puzzles_pooled_across_shapes(self):
        r = choose_preset(haiku_rows("pa", 2, 8), [set_info("pa")])
        p = r["presets"][0]
        self.assertEqual(p["score"], 0.5)                                       # median of [.2 x4, .8 x4]
        self.assertEqual(p["mean"], 0.5)
        self.assertEqual(p["shape_medians"], {"1x24": 0.8, "24x1": 0.2})

    def test_shape_gap_and_flag(self):
        r = choose_preset(haiku_rows("pa", 2, 8) + haiku_rows("pb", 3, 3) + haiku_rows("pc", 2, 5) + haiku_rows("pd", 2, 6),
                          [set_info(p) for p in ("pa", "pb", "pc", "pd")])
        by = {p["preset"]: p for p in r["presets"]}
        self.assertAlmostEqual(by["pa"]["shape_gap"], 0.6)
        self.assertTrue(by["pa"]["shape_gap_flag"])
        self.assertEqual((by["pb"]["shape_gap"], by["pb"]["shape_gap_flag"]), (0.0, False))
        self.assertAlmostEqual(by["pc"]["shape_gap"], 0.3)
        self.assertFalse(by["pc"]["shape_gap_flag"])                             # exactly 0.30 is not above 0.30
        self.assertEqual(by["pc"]["shape_gap_exact"], "3/10")
        self.assertTrue(by["pd"]["shape_gap_flag"])                              # 0.4
        r2 = choose_preset(haiku_rows("pb", 3, 3), [set_info("pb")])
        self.assertEqual(r2["pick"]["preset"], "pb")
        self.assertEqual((r2["pick"]["shape_gap"], r2["pick"]["shape_gap_flag"]), (0.0, False))
        r3 = choose_preset(haiku_rows("pd", 2, 6), [set_info("pd")])             # score 0.4, gap 0.4: chosen and flagged
        self.assertEqual((r3["pick"]["preset"], r3["pick"]["shape_gap_flag"]), ("pd", True))
        self.assertIn("gap 0.400", summary(r3))
        self.assertIn("ABOVE 0.30", summary(r3))
        self.assertNotIn("ABOVE 0.30", summary(r2))

    def test_median_above_060_per_shape_flag_is_gone(self):
        r = choose_preset(haiku_rows("pa", 2, 8), [set_info("pa")])
        self.assertNotIn("low_information", json.dumps(r))
        self.assertNotIn("low-information", summary(r))
        self.assertNotIn("low_information", RULE_TEXT)

    def test_k2_tie_break_kinds_first_then_prompt_length(self):
        rows = haiku_rows("pa", 3) + haiku_rows("pb", 3) + haiku_rows("pc", 3)
        # three-way tie on score: the fewest kinds, then the shortest prompt among those
        sets = [set_info("pa", kinds=("a", "b", "c"), chars=100), set_info("pb", kinds=("a", "b"), chars=900),
                set_info("pc", kinds=("a", "b"), chars=500)]
        r = choose_preset(rows, sets)
        self.assertEqual((r["pick"]["preset"], r["pick"]["tie_broken"], r["pick"]["tied_with"]), ("pc", True, ["pa", "pb"]))
        # one kind with the longest prompt beats more kinds with shorter ones
        sets = [set_info("pa", kinds=("a",), chars=5000), set_info("pb", kinds=("a", "b"), chars=100),
                set_info("pc", kinds=("a", "b", "c"), chars=50)]
        self.assertEqual(pick_of(choose_preset(rows, sets)), "pa")
        # same kinds: the shorter mean prompt wins; the preset name is only the last resort
        sets = [set_info("pa", chars=1500), set_info("pb", chars=900), set_info("pc", chars=1200)]
        r = choose_preset(rows, sets)
        self.assertEqual((r["pick"]["preset"], r["pick"]["tied_with"]), ("pb", ["pa", "pc"]))
        self.assertEqual(pick_of(choose_preset(rows, [set_info("pa"), set_info("pb"), set_info("pc")])), "pa")

    def test_equidistant_scores_tie(self):
        rows = haiku_rows("pa", 6, tries=20) + haiku_rows("pb", 9, tries=20)      # 0.30 and 0.45: both 0.075 from 0.375
        r = choose_preset(rows, [set_info("pa", kinds=("a", "b", "c")), set_info("pb", kinds=("a", "b"))])
        self.assertEqual({p["preset"]: p["distance"] for p in r["presets"]}, {"pa": 0.075, "pb": 0.075})
        self.assertEqual((r["pick"]["preset"], r["pick"]["tie_broken"]), ("pb", True))
        r = choose_preset(rows, [set_info("pa", kinds=("a", "b")), set_info("pb", kinds=("a", "b", "c"))])
        self.assertEqual(r["pick"]["preset"], "pa")                              # fewer kinds wins on either side of the target
        r = choose_preset(rows, [set_info("pa", chars=900), set_info("pb", chars=800)])
        self.assertEqual(r["pick"]["preset"], "pb")                              # same kinds: the shorter prompt

    def test_not_equidistant_means_no_tie(self):
        rows = haiku_rows("pa", 3) + haiku_rows("pb", 4)                         # 0.3 and 0.4: distances 0.075 and 0.025
        r = choose_preset(rows, [set_info("pa", kinds=("a",)), set_info("pb", kinds=("a", "b", "c"))])
        self.assertEqual((r["pick"]["preset"], r["pick"]["tie_broken"]), ("pb", False))   # nearer wins even with more kinds

    def test_tie_is_decided_after_rounding_distances_to_a_tenth_of_a_point(self):
        def pair(preset, total):                                                 # one puzzle per shape, 1000 tries: score = total / 2000
            return acc_rows(preset, [total // 2, total - total // 2], tries=1000)
        sets = [set_info("pa", kinds=("a", "b", "c"), n_base=1), set_info("pb", kinds=("a", "b"), n_base=1)]
        r = choose_preset(pair("pa", 749) + pair("pb", 752), sets)              # 0.3745 (d 0.0005) and 0.376 (d 0.001)
        d = {p["preset"]: p["distance"] for p in r["presets"]}
        self.assertLess(d["pa"], d["pb"])                                        # pa is closer, by 0.0005
        self.assertEqual((r["pick"]["preset"], r["pick"]["tie_broken"]), ("pb", True))   # both round to 0.001: K2 decides
        r = choose_preset(pair("pa", 749) + pair("pb", 753), sets)              # d 0.0005 -> 0.001 and d 0.0015 -> 0.002
        self.assertEqual((r["pick"]["preset"], r["pick"]["tie_broken"]), ("pa", False))

    def test_tier_2_closest_to_target_and_band_miss(self):
        r = choose_preset(haiku_rows("pa", 2) + haiku_rows("pb", 6) + haiku_rows("pc", 7) + haiku_rows("pd", 1),
                          [set_info(p) for p in ("pa", "pb", "pc", "pd")])
        self.assertEqual(r["pick"]["preset"], "pa")                              # 0.2 is 0.175 away, 0.6 is 0.225 away; 0.7, 0.1 are out
        self.assertEqual((r["pick"]["tier"], r["tier"], r["pick"]["in_band"], r["pick"]["no_preset_in_band"]), (2, 2, False, True))
        self.assertAlmostEqual(r["pick"]["band_miss"], 0.05)
        self.assertEqual((r["extra_rung_needed"], r["outside_15_60_return_to_user"]), (False, False))
        self.assertIn("tier 2", summary(r))
        r = choose_preset(haiku_rows("pb", 6) + haiku_rows("pc", 7), [set_info("pb"), set_info("pc")])
        self.assertEqual((r["pick"]["preset"], r["pick"]["tier"]), ("pb", 2))
        self.assertAlmostEqual(r["pick"]["band_miss"], 0.1)                      # 0.60 is 0.10 above the band
        r = choose_preset(haiku_rows("pa", 3, tries=20), [set_info("pa")])       # 0.15: the lowest tier 2 score
        self.assertEqual(r["pick"]["tier"], 2)
        self.assertAlmostEqual(r["pick"]["band_miss"], 0.1)

    def test_tier_3_every_preset_above_060(self):
        r = choose_preset(haiku_rows("pa", 7) + haiku_rows("pb", 8) + haiku_rows("pc", 9),
                          [set_info("pa"), set_info("pb"), set_info("pc")])
        self.assertIsNone(r["pick"])
        self.assertTrue(r["extra_rung_needed"])
        self.assertFalse(r["outside_15_60_return_to_user"])
        self.assertEqual(r["tier"], 3)
        self.assertIn("extra rung needed", summary(r))
        self.assertIn("Pick: NONE", summary(r))
        r = choose_preset(haiku_rows("pa", 13, tries=20), [set_info("pa")])       # 0.65 alone is above too
        self.assertTrue(r["extra_rung_needed"] and r["pick"] is None)
        r = choose_preset(haiku_rows("pa", 6) + haiku_rows("pb", 8), [set_info("pa"), set_info("pb")])
        self.assertFalse(r["extra_rung_needed"])                                 # 0.60 is inside the window: a tier 2 pick
        self.assertEqual((r["pick"]["preset"], r["pick"]["tier"]), ("pa", 2))

    def test_tier_3_every_preset_below_015(self):
        r = choose_preset(haiku_rows("pa", 1) + haiku_rows("pb", 2, tries=20), [set_info("pa"), set_info("pb")])   # 0.1 and 0.1
        self.assertIsNone(r["pick"])
        self.assertTrue(r["outside_15_60_return_to_user"])
        self.assertFalse(r["extra_rung_needed"])                                 # there is no easier rung
        self.assertIn("return to the user", summary(r))
        r = choose_preset(haiku_rows("pa", 0), [set_info("pa")])
        self.assertTrue(r["outside_15_60_return_to_user"] and r["pick"] is None)

    def test_tier_3_presets_on_both_sides_of_the_window(self):
        r = choose_preset(haiku_rows("pa", 1) + haiku_rows("pb", 7) + haiku_rows("pc", 8),
                          [set_info("pa"), set_info("pb"), set_info("pc")])
        self.assertIsNone(r["pick"])
        self.assertTrue(r["outside_15_60_return_to_user"])
        self.assertFalse(r["extra_rung_needed"])
        r = choose_preset(haiku_rows("pa", 1) + haiku_rows("pb", 7) + haiku_rows("pc", 2),    # a preset inside the window: tier 2
                          [set_info("pa"), set_info("pb"), set_info("pc")])
        self.assertEqual((r["pick"]["preset"], r["pick"]["tier"]), ("pc", 2))

    def test_presets_with_no_haiku_medium_rows_are_listed(self):
        r = choose_preset(haiku_rows("pa", 4), [set_info("pa"), set_info("pb")])
        by = {p["preset"]: p for p in r["presets"]}
        self.assertEqual((by["pb"]["n_puzzles"], by["pb"]["n_tries"], by["pb"]["score"]), (0, 0, None))
        self.assertEqual(r["presets_without_rows"], ["pb"])
        self.assertEqual(pick_of(r), "pa")
        text = summary(r)
        self.assertRegex(text, r"pb\s+0\s+0\s+None")
        self.assertIn("WARNING", text)
        json.dumps(r)                                                            # still serialisable

    def test_rule_text_states_the_ladder(self):
        for needle in ("[0.25, 0.50]", "[0.15, 0.60]", "0.375", "extra_rung_needed", "outside_15_60_return_to_user", "0.001",
                       "fewer distinct rule kinds", "shorter mean prompt", "Haiku-medium", "MEDIAN", "shape_gap_flag"):
            self.assertIn(needle, RULE_TEXT)
        self.assertEqual(choose_preset(haiku_rows("pa", 4), [set_info("pa")])["rule"], RULE_TEXT)

    def test_blank_right_counts_as_wrong_and_stays_in(self):
        r = choose_preset(haiku_rows("pa", 4, blank_instead_of_zero=True), [set_info("pa")])
        p = r["presets"][0]
        self.assertEqual((p["score"], p["n_tries"]), (0.4, 80))
        self.assertEqual([right_value({"right": v}) for v in ("1", "0", "", None, "1.0", "True")], [1, 0, 0, 0, 1, 1])
        rows = haiku_rows("pa", 4)
        rows[0]["right"] = ""
        self.assertEqual(choose_preset(rows, [set_info("pa")])["presets"][0]["n_tries"], 80)

    def test_other_models_never_enter_or_appear(self):
        base = haiku_rows("pa", 3) + haiku_rows("pb", 4)
        mixed = other_rows("pa") + base + other_rows("pb")
        sets = [set_info("pa"), set_info("pb")]
        clean, with_others = choose_preset(base, sets), choose_preset(mixed, sets)
        self.assertEqual(clean, with_others)                                     # same numbers, same input hash
        text = json.dumps(with_others).lower()
        for needle in ("opus", "sonnet", "0.987654", "0.123456", "om-01", "sm-01", "hl-01"):
            self.assertNotIn(needle, text)
        self.assertEqual(with_others["n_rows"], 160)                             # the Haiku-low rows are out too
        self.assertEqual(with_others["input_sha256"], rows_sha256(base))

    def test_realtime_tries_are_left_out(self):
        rows = haiku_rows("pa", 4)
        rows.append(dict(rows[0], custom_id="pilot-pa-v1-000-24x1-rthm-01", right="0"))
        r = choose_preset(rows, [set_info("pa")])
        self.assertEqual(r["presets"][0]["n_tries"], 80)
        r2 = choose_preset(rows, [set_info("pa")], include_realtime=True)
        self.assertEqual(r2["presets"][0]["n_tries"], 81)
        self.assertNotEqual(r["input_sha256"], r2["input_sha256"])

    def test_hash_is_order_free_and_changes_with_content(self):
        rows = haiku_rows("pa", 4)
        sets = [set_info("pa")]
        h = choose_preset(rows, sets)["input_sha256"]
        self.assertEqual(h, choose_preset(list(reversed(rows)), sets)["input_sha256"])
        rows[3]["right"] = "0" if rows[3]["right"] == "1" else "1"
        self.assertNotEqual(h, choose_preset(rows, sets)["input_sha256"])

    def test_errors(self):
        with self.assertRaises(ValueError):
            choose_preset(haiku_rows("pa", 4), [set_info("pb")])               # set not given
        with self.assertRaises(ValueError):
            choose_preset(other_rows("pa"), [set_info("pa")])                  # nothing Haiku-medium
        with self.assertRaises(ValueError):
            choose_preset(haiku_rows("pa", 4, n_base=5), [set_info("pa", n_base=4)])   # puzzle not in the frozen set


class Files(unittest.TestCase):
    def write_set(self, root, preset, params, prompt="x" * 100, n_base=2):
        d = Path(root) / f"pilot-{preset}-v1"
        d.mkdir()
        sid = f"pilot-{preset}-v1"
        items = [{"id": f"{sid}-{b:03d}-{sh}", "params": params, "prompt": prompt, "base_index": b}
                 for b in range(n_base) for sh in ("24x1", "1x24")]
        (d / "items.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
        (d / "manifest.json").write_text(json.dumps({"set_id": sid, "setting": preset, "family": "digits",
                                                     "items_sha256": "ab" * 32}))
        return d

    def write_table(self, td, rows, name="t.csv"):
        table = Path(td) / name
        with open(table, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return table

    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def refuses(self, argv):
        err = io.StringIO()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(err):
            main(argv)
        self.assertNotEqual(cm.exception.code, 0)
        return err.getvalue()

    def test_rule_kinds(self):
        self.assertEqual(rule_kinds({"n_affine": 6, "n_table": 6, "n_pair": 0, "n_shuffle": 2, "n_digits": 8}),
                         {"affine", "table", "shuffle"})
        self.assertEqual(rule_kinds({"vc_kinds": ["prefix", "map"], "ro_kinds": ["swap", "map"]}), {"prefix", "map", "swap"})
        self.assertEqual(rule_kinds({"kinds": ["a", "b", "a"]}), {"a", "b"})

    def test_cli_end_to_end_with_other_rows_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            da = self.write_set(td, "pa", {"n_affine": 6, "n_table": 6, "n_pair": 6, "n_shuffle": 6}, "x" * 300)
            db = self.write_set(td, "pb", {"n_affine": 4, "n_table": 4, "n_pair": 8, "n_shuffle": 8}, "x" * 200)
            info = load_set_info(da)
            self.assertEqual((info["setting"], info["kinds"], len(info["puzzles"])),
                             ("pa", {"affine", "table", "pair", "shuffle"}, 4))
            table = self.write_table(td, haiku_rows("pa", 3, n_base=2) + other_rows("pa", 2) + haiku_rows("pb", 3, n_base=2) + other_rows("pb", 2))
            self.assertEqual(len(load_haiku_medium_rows(table)), 80)
            out = Path(td) / "choice.json"
            code, printed = self.run_main(["choose", "--table", str(table), "--sets", str(da), str(db), "--out", str(out),
                                           "--allow-other-rows"])
            self.assertEqual(code, 0)
            self.assertIn("Pick: pb", printed)                                   # a tie on score: same kinds, shorter prompt
            self.assertNotIn("opus", (printed + out.read_text()).lower())
            res = json.loads(out.read_text())
            self.assertEqual(res["pick"]["preset"], "pb")
            self.assertEqual(len(res["input_sha256"]), 64)
            self.assertIn("rule", res)
            self.refuses(["choose", "--table", str(table), "--sets", str(da), str(db), "--out", str(out), "--allow-other-rows"])   # no silent overwrite

    def test_legacy_call_without_a_subcommand_is_choose(self):
        with tempfile.TemporaryDirectory() as td:
            da = self.write_set(td, "pa", {"n_affine": 6})
            table = self.write_table(td, haiku_rows("pa", 4, n_base=2))
            out = Path(td) / "choice.json"
            code, printed = self.run_main(["--table", str(table), "--sets", str(da), "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text())["pick"]["preset"], "pa")

    def test_choose_refuses_a_table_with_other_rows_unless_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            da = self.write_set(td, "pa", {"n_affine": 6})
            table = self.write_table(td, haiku_rows("pa", 4, n_base=2) + other_rows("pa", 2))
            out = Path(td) / "choice.json"
            err = self.refuses(["choose", "--table", str(table), "--sets", str(da), "--out", str(out)])
            self.assertIn("not Haiku-medium", err)
            self.assertIn("--allow-other-rows", err)
            self.assertIn("extract", err)
            self.assertNotIn("0.987654", err)                                    # no other-model number is echoed
            self.assertFalse(out.exists())                                       # nothing written
            code, _ = self.run_main(["choose", "--table", str(table), "--sets", str(da), "--out", str(out), "--allow-other-rows"])
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())
            # a Haiku-low row alone is also refused (it is Haiku, but not medium)
            low = self.write_table(td, haiku_rows("pa", 4, n_base=2) + [r for r in other_rows("pa", 2) if "-hl-" in r["custom_id"]], "low.csv")
            self.refuses(["choose", "--table", str(low), "--sets", str(da), "--out", str(Path(td) / "c2.json")])

    def test_extract_then_choose_gives_the_same_pick_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            da = self.write_set(td, "pa", {"n_affine": 6, "n_table": 6}, "x" * 300)
            db = self.write_set(td, "pb", {"n_affine": 4}, "x" * 200)
            full_rows = haiku_rows("pa", 3, n_base=2) + other_rows("pa", 2) + haiku_rows("pb", 5, n_base=2) + other_rows("pb", 2)
            table = self.write_table(td, full_rows)
            ext = Path(td) / "hm_only.csv"
            code, printed = self.run_main(["extract", "--table", str(table), "--out", str(ext)])
            self.assertEqual(code, 0)
            self.assertIn("80 Haiku-medium rows", printed)
            self.assertIn("24 other rows", printed)
            with open(ext, newline="") as f:
                rd = csv.DictReader(f)
                self.assertEqual(rd.fieldnames, FIELDS)                           # columns unchanged
                kept = list(rd)
            self.assertEqual(len(kept), 80)
            self.assertTrue(all(r["requested_model"] == HAIKU and r["effort"] == "medium" for r in kept))
            self.assertNotIn("opus", ext.read_text().lower())
            self.assertEqual((kept, extract_haiku_medium(table, Path(td) / "again.csv")[0]), (kept, 80))
            out_x, out_f = Path(td) / "x.json", Path(td) / "f.json"
            self.run_main(["choose", "--table", str(ext), "--sets", str(da), str(db), "--out", str(out_x)])   # accepted without a flag
            self.run_main(["choose", "--table", str(table), "--sets", str(da), str(db), "--out", str(out_f), "--allow-other-rows"])
            self.assertEqual(json.loads(out_x.read_text()), json.loads(out_f.read_text()))   # same pick, same sha256
            self.assertEqual(json.loads(out_x.read_text())["pick"]["preset"], "pa")           # 0.3 vs 0.5: pa is closer

    def test_extract_refuses_to_overwrite_and_needs_the_model_columns(self):
        with tempfile.TemporaryDirectory() as td:
            table = self.write_table(td, haiku_rows("pa", 4, n_base=1))
            ext = Path(td) / "hm.csv"
            self.run_main(["extract", "--table", str(table), "--out", str(ext)])
            self.refuses(["extract", "--table", str(table), "--out", str(ext)])
            code, _ = self.run_main(["extract", "--table", str(table), "--out", str(ext), "--overwrite"])
            self.assertEqual(code, 0)
            bad = Path(td) / "bad.csv"
            bad.write_text("custom_id,right\nx,1\n")
            with self.assertRaises(ValueError):
                extract_haiku_medium(bad, Path(td) / "o.csv")


class Trace(unittest.TestCase):
    """D-76 (the official trace score): a 1x24 try of a ledger set is scored by its trace, read from the raw reply; the table's `right` (the final answer) is
    not used for it, from the full table or from the extract. Edith R3: a 24x1 try of a ledger set is read from its reply too
    (trace_parse.parse_pieces, every piece right), never from `right`."""

    write_table, run_main, refuses = Files.write_table, Files.run_main, Files.refuses

    REPLIES = [trace_text(), trace_text(), trace_text(MIDDLE_WRONG), trace_text({24: (9, 9, 9)}, answer=KEY[-1])]
    # per 1x24 puzzle: 2 right traces, 1 with the final right but middle lines wrong, 1 unplaceable (Answer right, line 24 not)
    REPLIES_24X1 = [pieces_text(), pieces_text(), pieces_text({7: (1, 2, 3)}), pieces_text({7: "[1, 2]"})]
    # per 24x1 puzzle: 2 right, 1 with one piece wrong (format ok), 1 with a piece of the wrong length (format not ok)

    def write_ledger_set(self, root, preset="pl", n_base=2, answer_only=False):
        sid = f"pilot-{preset}-v1"
        d = Path(root) / sid
        d.mkdir()
        items = []
        for b in range(n_base):
            items.append({"id": f"{sid}-{b:03d}-24x1", "width": 24, "depth": 1, "prompt": "x" * 50, "params": {"kinds": ["sweep"], "lines": 3},
                          "answer": [list(s) for s in KEY]})
            items.append({"id": f"{sid}-{b:03d}-1x24", "width": 1, "depth": 24, "prompt": "x" * 50, "params": {"kinds": ["sweep"], "lines": 3},
                          "chains": [{"states": [list(s) for s in KEY]}], "style": "d31-answer-only" if answer_only else "d31"})
        (d / "items.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
        (d / "manifest.json").write_text(json.dumps({"set_id": sid, "setting": preset, "family": "ledger", "items_sha256": "cd" * 32}))
        return d

    def table_rows(self, preset="pl", n_base=2, right_24x1=None):
        """Every try marked right=1 at 1x24 (the pilot grader's final-answer score); 2 of 4 right at 24x1 (as the replies are), or
        `right_24x1` for every 24x1 try."""
        sid = f"pilot-{preset}-v1"
        rows = []
        for b in range(n_base):
            for shape in ("24x1", "1x24"):
                for n in range(1, 5):
                    right = "1" if shape == "1x24" or n <= 2 else "0"
                    if shape == "24x1" and right_24x1 is not None:
                        right = right_24x1
                    rows.append({"custom_id": f"{sid}-{b:03d}-{shape}-hm-{n:02d}", "requested_model": HAIKU, "effort": "medium",
                                 "cost_usd": "0.01", "kind": "answered", "right": right})
        return rows

    def write_log(self, td, preset="pl", n_base=2, replies=None, replies_24x1=None, shapes=("24x1", "1x24")):
        sid = f"pilot-{preset}-v1"
        recs = []
        for b in range(n_base):
            for shape in shapes:
                texts, earlier = (replies or self.REPLIES, trace_text()) if shape == "1x24" else (replies_24x1 or self.REPLIES_24X1, pieces_text())
                for n, text in enumerate(texts, 1):
                    cid = f"{sid}-{b:03d}-{shape}-hm-{n:02d}"
                    recs.append({"custom_id": cid, "requested_model": HAIKU, "effort": "medium", "kind": "answered", "answer_text": text,
                                 "final": True})
                    recs.append({"custom_id": cid, "requested_model": HAIKU, "effort": "medium", "kind": "answered", "answer_text": earlier,
                                 "final": False})                                              # an earlier attempt: not the final record
            recs.append({"custom_id": f"{sid}-{b:03d}-1x24-om-01", "requested_model": OPUS, "effort": "medium", "kind": "answered",
                         "answer_text": trace_text(), "final": True})                         # another model: dropped as read
        log = Path(td) / "calls.jsonl"
        log.write_text("".join(json.dumps(r) + "\n" for r in recs))
        return log

    def test_1x24_ledger_tries_are_scored_by_the_whole_trace(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            recs = read_haiku_medium_replies([self.write_log(td)])
            self.assertEqual(len(recs), 16)                                      # final Haiku-medium records only, both shapes
            self.assertTrue(all(r["requested_model"] == HAIKU for r in recs))
            trace = trace_grades(recs, [info])
            self.assertEqual([trace[f"pilot-pl-v1-000-1x24-hm-{n:02d}"]["right"] for n in range(1, 5)], [1, 1, 0, 0])
            res = choose_preset(self.table_rows(), [info], trace=trace)
            p = res["presets"][0]
            self.assertEqual(p["shape_medians"], {"1x24": 0.5, "24x1": 0.5})     # the `right` column would give 1.0 at 1x24
            self.assertEqual(p["score"], 0.5)
            self.assertEqual(p["score_1x24"], "trace (D-76)")
            self.assertEqual((p["n_answered_1x24_traced"], p["format_compliance_1x24"]), (8, 0.75))
            self.assertEqual((p["n_answered_24x1_read"], p["format_compliance_24x1"]), (8, 0.75))
            self.assertEqual(res["n_trace_scored"], 16)
            self.assertIn("1x24 trace-scored (D-76); format compliance 0.750", summary(res))
            self.assertIn("24x1 read from the replies; format compliance 0.750", summary(res))

    def test_without_the_replies_the_choice_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            with self.assertRaises(ValueError) as cm:
                choose_preset(self.table_rows(), [info])
            self.assertIn("--replies", str(cm.exception))
            rows = [dict(r, kind="refusal") for r in self.table_rows()]
            self.assertEqual(choose_preset(rows, [info])["presets"][0]["shape_medians"], {"1x24": 0.0, "24x1": 0.0})   # no answer: wrong, no reply needed

    def test_an_answer_only_item_is_scored_by_its_final_answer(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td, answer_only=True))
            replies = ["Answer: 1 = [124, 224, 324]", "Answer: [124, 224, 324]", "Answer: 1 = [1, 2, 3]", "no answer here"]
            trace = trace_grades(read_haiku_medium_replies([self.write_log(td, replies=replies)]), [info])
            self.assertEqual(choose_preset(self.table_rows(), [info], trace=trace)["presets"][0]["shape_medians"]["1x24"], 0.5)

    def test_format_compliance_counts_only_trace_scored_tries(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td, answer_only=True))
            replies = ["Answer: 1 = [124, 224, 324]", "Answer: [124, 224, 324]", "Answer: 1 = [1, 2, 3]", "no answer here"]
            trace = trace_grades(read_haiku_medium_replies([self.write_log(td, replies=replies)]), [info])
            self.assertTrue(all(g["answer_only"] is (g["shape"] == "1x24") for g in trace.values()))   # the 24x1 grades are never answer-only
            p = choose_preset(self.table_rows(), [info], trace=trace)["presets"][0]
            self.assertEqual((p["n_answered_1x24_traced"], p["format_compliance_1x24"]), (0, None))   # answer-only items are not traced
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            trace = trace_grades(read_haiku_medium_replies([self.write_log(td)]), [info])
            for n in (1, 2):                                                  # mark two right-format tries of puzzle 000 answer-only
                trace[f"pilot-pl-v1-000-1x24-hm-{n:02d}"] = dict(trace[f"pilot-pl-v1-000-1x24-hm-{n:02d}"], answer_only=True)
            p = choose_preset(self.table_rows(), [info], trace=trace)["presets"][0]
            self.assertEqual((p["n_answered_1x24_traced"], p["format_compliance_1x24"]), (6, 4 / 6))

    def test_24x1_ledger_tries_are_scored_from_the_reply_not_the_right_column(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            trace = trace_grades(read_haiku_medium_replies([self.write_log(td)]), [info])
            self.assertEqual([trace[f"pilot-pl-v1-000-24x1-hm-{n:02d}"]["right"] for n in range(1, 5)], [1, 1, 0, 0])
            for right, would in (("0", 0.0), ("1", 1.0)):                    # the table says every 24x1 try is wrong, then right
                p = choose_preset(self.table_rows(right_24x1=right), [info], trace=trace)["presets"][0]
                self.assertEqual(p["shape_medians"]["24x1"], 0.5, f"the `right` column would give {would}")

    def test_24x1_replies_in_formats_only_the_analysis_reader_handles_are_right(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            replies = [pieces_text(head="**Answer**:"), pieces_text(tail="\nAnswer check: done"), pieces_text(head="__Answer__:"),
                       "work\nAnswer: 1 = [9, 9, 9]\n" + pieces_text()]
            trace = trace_grades(read_haiku_medium_replies([self.write_log(td, replies_24x1=replies)]), [info])
            self.assertEqual([trace[f"pilot-pl-v1-001-24x1-hm-{n:02d}"]["right"] for n in range(1, 5)], [1, 1, 1, 1])
            p = choose_preset(self.table_rows(right_24x1="0"), [info], trace=trace)["presets"][0]
            self.assertEqual(p["shape_medians"]["24x1"], 1.0)
            self.assertEqual(p["format_compliance_24x1"], 1.0)

    def test_a_24x1_ledger_try_with_no_reply_is_refused_and_a_refusal_scores_0(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            trace = trace_grades(read_haiku_medium_replies([self.write_log(td, shapes=("1x24",))]), [info])
            with self.assertRaises(ValueError) as cm:
                choose_preset(self.table_rows(), [info], trace=trace)
            self.assertIn("-24x1-hm-", str(cm.exception))
            self.assertIn("--replies", str(cm.exception))
            rows = [dict(r, kind="refusal") if "-24x1-" in r["custom_id"] else r for r in self.table_rows(right_24x1="1")]
            p = choose_preset(rows, [info], trace=trace)["presets"][0]
            self.assertEqual(p["shape_medians"], {"1x24": 0.5, "24x1": 0.0})            # no answer: wrong, `right` not read
            self.assertEqual((p["n_answered_24x1_read"], p["format_compliance_24x1"]), (0, None))

    def test_format_compliance_1x24_is_unaffected_by_24x1_tries(self):
        with tempfile.TemporaryDirectory() as td:
            info = load_set_info(self.write_ledger_set(td))
            base = choose_preset(self.table_rows(), [info], trace=trace_grades(
                read_haiku_medium_replies([self.write_log(td)]), [info]))["presets"][0]
            log = self.write_log(td, replies_24x1=["no answer here"] * 4)              # every 24x1 reply without an Answer line
            trace = trace_grades(read_haiku_medium_replies([log]), [info])
            self.assertTrue(all(g["format_status"] == "no_answer" for c, g in trace.items() if "-24x1-" in c))
            p = choose_preset(self.table_rows(), [info], trace=trace)["presets"][0]
            self.assertEqual((p["n_answered_1x24_traced"], p["format_compliance_1x24"]),
                             (base["n_answered_1x24_traced"], base["format_compliance_1x24"]))
            self.assertEqual((p["n_answered_1x24_traced"], p["format_compliance_1x24"]), (8, 0.75))
            self.assertEqual((p["n_answered_24x1_read"], p["format_compliance_24x1"]), (8, 0.0))
            self.assertEqual(p["shape_medians"]["24x1"], 0.0)

    def test_extract_then_choose_with_the_replies_gives_the_same_trace_scored_pick(self):
        with tempfile.TemporaryDirectory() as td:
            d = self.write_ledger_set(td)
            log = self.write_log(td)
            table = self.write_table(td, self.table_rows() + other_rows("pl", 2))
            ext = Path(td) / "hm_only.csv"
            self.run_main(["extract", "--table", str(table), "--out", str(ext)])
            err = self.refuses(["choose", "--table", str(ext), "--sets", str(d), "--out", str(Path(td) / "no.json")])
            self.assertIn("--replies", err)                                       # the extract's `right` is never used at 1x24
            out_x, out_f = Path(td) / "x.json", Path(td) / "f.json"
            self.run_main(["choose", "--table", str(ext), "--sets", str(d), "--replies", str(log), "--out", str(out_x)])
            self.run_main(["choose", "--table", str(table), "--sets", str(d), "--replies", str(log), "--out", str(out_f),
                           "--allow-other-rows"])
            x = json.loads(out_x.read_text())
            self.assertEqual(x, json.loads(out_f.read_text()))
            self.assertEqual(x["presets"][0]["shape_medians"]["1x24"], 0.5)
            self.assertNotIn("opus", out_x.read_text().lower())


if __name__ == "__main__":
    unittest.main()
