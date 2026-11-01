"""Tests for the paper-outputs script (harness/analysis/paper_outputs.py and paper_out_core.py): keys, pins, formatting, the label
check, the writers, and a real build of a few outputs from the pinned files (read from git, so the repo's history must be present).
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness.analysis import paper_out_core as core
from harness.analysis.paper_out_core import (MINUS, KeyMissing, Ref, Source, SourceMismatch, Store, format_key, guarded_dp,
                                             interval, label, label_ok, parse_key, pct, pts, pvalue, resolve, resolve_text, tex_escape)

REPO = Path(__file__).resolve().parents[2]


def _git_ok() -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", "8be72ec"], check=True, capture_output=True)
        return True
    except Exception:
        return False


class Keys(unittest.TestCase):
    def test_round_trip(self):
        for segs in (["a", "b", "0"], ["item_9e", "shapes", "1x6", "0.3"], ["comparisons", "topup:e2-e3:1x6", "d"],
                     ["table", "e3 1x6", "cpc"], ["x", "it's"], ["L12", "USD (computed)"]):
            self.assertEqual(parse_key(format_key(segs)), segs)

    def test_brackets(self):
        self.assertEqual(parse_key("a.b['0.3'].c"), ["a", "b", "0.3", "c"])
        self.assertEqual(format_key(["a", "0.3"]), "a['0.3']")
        for bad in ("", "a..b", "a.", "a[0]", "a['x'"):
            with self.assertRaises(ValueError):
                parse_key(bad)

    def test_resolve_digit_on_dict_and_list(self):
        doc = {"by_n": {"12": 7}, "points": [10, 20, 30]}
        self.assertEqual(resolve(doc, ["by_n", "12"]), 7)
        self.assertEqual(resolve(doc, ["points", "2"]), 30)
        for bad in (["points", "3"], ["by_n", "13"], ["points", "x"], ["by_n", "12", "z"]):
            with self.assertRaises(KeyMissing):
                resolve(doc, bad)


class Pins(unittest.TestCase):
    def _store(self, body: bytes, pin: str) -> Store:
        src = {"f": Source("f", "x.json", "abc", pin)}
        return Store(Path("."), src, reader=lambda s: body)

    def test_mismatch_refuses(self):
        with self.assertRaises(SourceMismatch):
            self._store(b'{"a": 1}', "0" * 64).ref("f", "a")

    def test_match_reads_and_records_use(self):
        body = b'{"a": {"b": [5, 6]}}'
        S = self._store(body, hashlib.sha256(body).hexdigest())
        r = S.ref("f", "a.b.1")
        self.assertEqual((r.value, r.source, r.key), (6, "f", "a.b.1"))
        self.assertEqual(S.used, {"f"})

    @unittest.skipUnless(_git_ok(), "the repo's history is not available")
    def test_every_pinned_source_matches_git(self):
        for s in core.SOURCES.values():
            raw = core.git_bytes(REPO, s.commit, s.path)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), s.sha256, s.path)


class Formatting(unittest.TestCase):
    def test_minus_and_plus(self):
        self.assertEqual(core.fmt_fixed(-33.125, 2), MINUS + "33.13")
        self.assertEqual(core.fmt_fixed(17.5, 2, signed=True), "+17.50")
        self.assertEqual(core.fmt_fixed(0.0, 2, signed=True), "0.00")
        self.assertEqual(core.fmt_fixed(0.125, 2), "0.13")                  # half away from zero

    def test_one_more_decimal_near_a_bound(self):
        self.assertEqual(guarded_dp(-4.996, 2, (0.0, -5.0)), 3)            # never printed as -5.00
        self.assertEqual(guarded_dp(-4.9996, 2, (0.0, -5.0)), 4)
        self.assertEqual(guarded_dp(-0.004, 2, (0.0,)), 3)                 # not printed as -0.00
        self.assertEqual(guarded_dp(-1.15, 2, (0.0, -5.0)), 2)
        self.assertEqual(guarded_dp(-5.0, 2, (0.0, -5.0)), 2)              # exactly on the bound stays

    def test_pts_and_interval(self):
        c = pts(Ref(-4.996, "s", "k"), margin=-5.0)
        self.assertEqual(c.printed, MINUS + "4.996")
        i = interval(Ref(1.6666, "s", "a"), Ref("unbounded", "s", "b"), dp=2)
        self.assertEqual(i.printed, "[1.67, unbounded]")
        self.assertEqual([r.key for r in i.refs], ["a", "b"])

    def test_half_away_from_zero_on_the_stamped_decimal(self):
        # binary floating point gives 0.8925 * 100 = 89.24999...; the stamped number is 0.8925, so it prints 89.3
        for v, want in ((0.8925, "89.3"), (0.9275, "92.8"), (0.5125, "51.3"), (0.4875, "48.8"), (-0.125, MINUS + "12.5")):
            self.assertEqual(pct(Ref(v, "s", "k"), dp=1).printed, want)
        self.assertEqual(core.fmt_fixed(-0.005, 2), MINUS + "0.01")
        self.assertEqual(core.usd(Ref(0.00044500, "s", "k")).printed, "0.000445")
        # a computed float with binary noise in its shortest repr (723/800 = 0.90375 stored as 0.9037499999999999) rounds as its exact
        # value: 90.38 at two decimals (Karen, 2026-10-20); a float with few digits is unchanged
        self.assertEqual(pct(Ref(0.9037499999999999, "s", "k"), dp=2).printed, "90.38")
        self.assertEqual(pct(Ref(0.9037499999999999, "s", "k"), dp=1).printed, "90.4")
        self.assertEqual(core.dec(0.0011002), core.Decimal("0.0011002"))
        self.assertEqual(core.dec(1.2345678901234567e-07), core.Decimal("1.23456789012E-7"))
        self.assertEqual(core.dec(1234567890123.0), core.Decimal("1234567890123.0"))     # a whole float is exact: never cut

    def test_narrow_keeps_refs_and_refuses_unknown_titles(self):
        t = core.Table([label("Test"), label("d (points)"), label("95% interval")],
                       [[label("Test 1"), pts(Ref(-33.125, "s", "a")), interval(Ref(-43.75, "s", "b"), Ref(-23.75, "s", "c"), signed=True)]])
        n = core.narrow(t, ["Test", ("d [95% interval]", ["d (points)", "95% interval"], " ")])
        self.assertEqual([c.printed for c in n.rows[0]], ["Test 1", MINUS + "33.13 [" + MINUS + "43.75, " + MINUS + "23.75]"])
        self.assertEqual([r.key for r in n.rows[0][1].refs], ["a", "b", "c"])
        with self.assertRaises(KeyError):
            core.narrow(t, ["Shape"])

    def test_narrow_notes_and_caption(self):
        t = core.Table([label("Test"), label("p")], [[label("Test 1"), pvalue(Ref(0.5, "s", "p"))]], notes=[[label("About p.")]],
                       caption={"tier": [label("confirmatory")]})
        n = core.narrow(t, ["Test"])
        self.assertEqual(len(n.notes), 2)                                   # a pointer to the full table, then the full table's notes
        self.assertTrue(n.notes[0][0].printed.startswith("Main-text version"))
        self.assertEqual(n.caption["tier"][0].printed, "confirmatory")
        t.main_notes, t.main_caption = [[label("Only Test.")]], {"tier": [label("main")]}
        n = core.narrow(t, ["Test"])
        self.assertEqual([[c.printed for c in x] for x in n.notes], [["Only Test."]])
        self.assertEqual(n.caption["tier"][0].printed, "main")

    def test_pct_records_the_scale(self):
        c = pct(Ref(0.9859375, "s", "k"), dp=1)
        self.assertEqual((c.printed, c.formula), ("98.6", "100 * x"))

    def test_pvalue_ends(self):
        self.assertEqual(pvalue(Ref(3.99e-05, "s", "k")).printed, "<0.0001")
        self.assertEqual(pvalue(Ref(0.99996, "s", "k")).printed, ">0.9999")
        self.assertEqual(pvalue(Ref(0.0713, "s", "k")).printed, "0.0713")

    def test_stamped_number_strings(self):
        self.assertEqual(core.num(Ref("0.9085411025657543384252207397", "s", "k"), dp=3).printed, "0.909")
        self.assertEqual(core.num(Ref("257542400/7041099", "s", "k"), dp=2).printed, "36.58")
        with self.assertRaises(TypeError):
            core.num(Ref("about 3", "s", "k"))

    def test_stamped_count_prints_as_stamped(self):
        # Edith's PR #40 review, S1: a median of token counts prints exactly as stamped: no '.0' padding on a whole number, a half keeps its '.5'
        for v, want in ((600.0, "600"), (600, "600"), (1737.0, "1,737"), (7604.5, "7,604.5"), (1052.5, "1,052.5"), (361, "361"),
                        (0.5, "0.5"), (1000, "1,000"), (1000.0, "1,000"), ("2.50", "2.5"), (-1234.5, MINUS + "1,234.5"), (-600.0, MINUS + "600")):
            c = core.stamped_count(Ref(v, "s", "k"))
            self.assertEqual(c.printed, want)
            self.assertEqual((c.kind, c.raw, [r.key for r in c.refs]), ("num", v, ["k"]))
        with self.assertRaises(TypeError):
            core.stamped_count(Ref("about 3", "s", "k"))


class BarRule(unittest.TestCase):
    """The shared 95% bar rule of the figures (Edith's PR #40 review, M3; polish standard 8.6): a bar is not drawn only if its whole span
    is shorter than its marker AND neither arm sticks out a point past the marker's edge; a bar not shorter than its marker is always drawn,
    and one that stands under a point past the marker's edge (a sliver) is drawn in front of the marker."""

    def setUp(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from harness.analysis import paper_out_figures as F
        self.F, self.plt = F, plt
        self.fig = plt.figure(figsize=(3, 2))
        self.ax = self.fig.add_axes([0.2, 0.2, 0.7, 0.6])
        self.ax.set_ylim(0, 100)             # 0.6 * 2 in * 72 = 86.4 pt for 100 units: 0.864 pt a unit; a 5 pt Haiku marker is 5.6 pt = 6.48 units high

    def tearDown(self):
        self.plt.close(self.fig)

    def test_hidden_only_if_shorter_than_the_marker_and_no_arm_sticks_out(self):
        F, ax = self.F, self.ax
        self.assertTrue(F.bar_hidden(ax, "haiku", 47.5, 52.5, y=50.0))             # 4.3 pt long, centred: behind the marker
        self.assertTrue(F.bar_hidden(ax, "haiku", 47.5, 52.5))                      # no estimate given: the span alone (shorter than the marker)
        self.assertFalse(F.bar_hidden(ax, "haiku", 46.5, 53.5, y=50.0))            # 6.05 pt long: not shorter than the marker, so drawn (M3)
        self.assertFalse(F.bar_hidden(ax, "haiku", 46.5, 53.5))
        self.assertFalse(F.bar_hidden(ax, "haiku", 44.0, 56.0, y=50.0))            # clearly longer
        self.assertFalse(F.bar_hidden(ax, "haiku", 94.0, 100.0, y=100.0))          # one-sided, 5.2 pt: its lower arm sticks out 2.4 pt past the marker
        self.assertFalse(F.bar_hidden(ax, "haiku", 47.5, 55.0, y=50.0))            # 6.5 pt long: drawn however the estimate sits
        self.assertFalse(F.bar_hidden(ax, "haiku", None, None, y=50.0))             # no interval, no bar to hide
        self.assertFalse(F.bar_hidden(ax, "haiku", 50.0, 50.0, y=50.0))             # a zero-width interval is not a bar

    def test_slivers_are_the_drawn_bars_that_stand_under_a_point_past_the_marker(self):
        F, ax = self.F, self.ax
        self.assertTrue(F.bar_sliver(ax, "haiku", 46.5, 53.5, y=50.0))             # drawn, its arms 0.2 pt past the marker's edge: in front
        self.assertFalse(F.bar_sliver(ax, "haiku", 47.5, 52.5, y=50.0))            # hidden: not a sliver (it is not drawn)
        self.assertFalse(F.bar_sliver(ax, "haiku", 44.0, 56.0, y=50.0))            # a bar that shows behind its marker
        self.assertFalse(F.bar_sliver(ax, "haiku", 46.5, 53.5))                     # no estimate: no arms to read
        for lo, hi, y in ((47.5, 52.5, 50.0), (46.5, 53.5, 50.0), (44.0, 56.0, 50.0), (94.0, 100.0, 100.0)):
            self.assertFalse(F.bar_hidden(ax, "haiku", lo, hi, y=y) and F.bar_sliver(ax, "haiku", lo, hi, y=y))      # never both

    def test_a_sliver_is_drawn_beside_its_marker(self):
        # Edith's job K row 11: the bar is offset to the right of its marker (it read as a split marker through it), with no outline
        F, ax = self.F, self.ax
        self.assertFalse(F.mark(ax, 1.0, 50.0, 46.5, 53.5, "haiku", "medium", sliver_ok=True))  # not hidden (FIG-04's caption has words for it)
        bars = [c for c in ax.collections if c.get_zorder() > 3.0]                              # the bar's line stands above the marker (zorder 3)
        self.assertEqual(len(bars), 1)                                                          # the bar alone: no white outline when it is beside
        self.assertTrue(all(a.get_transform() != ax.transData for a in bars))                   # shifted sideways from the marker
        self.assertTrue(F.mark(ax, 2.0, 50.0, 47.5, 52.5, "haiku", "medium"))                   # hidden: no bar at all
        self.assertEqual(len([c for c in ax.collections]), 1)                                  # nothing added for a hidden bar

    def test_a_sliver_stops_the_build_where_no_caption_has_words_for_it(self):
        # Friday's checker on Edith's PR #40 review (M3 round, SHOULD 3): only FIG-04's caption names a bar drawn in front of its marker, so
        # every other site refuses one instead of drawing it unannounced
        F, ax = self.F, self.ax
        with self.assertRaises(ValueError):
            F.mark(ax, 1.0, 50.0, 46.5, 53.5, "haiku", "medium")                                # the default: no caption words
        with self.assertRaises(ValueError):
            F.forbid_sliver("FIG-XX", ax, "haiku", 46.5, 53.5, y=50.0)
        self.assertEqual(len(ax.collections), 0)                                                # nothing was drawn before the refusal
        F.forbid_sliver("FIG-XX", ax, "haiku", 47.5, 52.5, y=50.0)                              # hidden: nothing to refuse
        F.forbid_sliver("FIG-XX", ax, "haiku", 44.0, 56.0, y=50.0)                              # an ordinary bar
        F.forbid_sliver("FIG-XX", ax, "haiku", 46.5, 53.5)                                      # no estimate: no arms to read
        self.assertFalse(F.mark(ax, 3.0, 50.0, 44.0, 56.0, "haiku", "medium"))                  # an ordinary bar is drawn without the flag


class Labels(unittest.TestCase):
    def test_allowed_names(self):
        for t in ("Test 1", "Tests 1-4 and B1, B3", "Tests 3 and 5", "Study 1b", "1×6", "16 steps", "5-point margin",
                  "95% interval", "hx@16", "Haiku 5.5", "Opus-medium", "C13 and E3"):
            self.assertTrue(label_ok(t), t)

    def test_typed_numbers_refused(self):
        for t in ("Test 1 cost 0.5", "2026-10-13", "D-110", "k = 6", "B2 from 10 tries", "accuracy 97.5", "Study 1 (16 and 6 steps)"):
            self.assertFalse(label_ok(t), t)
            with self.assertRaises(ValueError):
                label(t)


class FileKeysAndFigureText(unittest.TestCase):
    def test_file_identity_keys(self):
        body = b'{"a": 1}'
        h = hashlib.sha256(body).hexdigest()
        S = Store(Path("."), {"f": Source("f", "x.json", "abc1234", h)}, reader=lambda s: body)
        self.assertEqual(S.ref("f", "@sha256").value, h)
        self.assertEqual(S.get("f", "@commit"), "abc1234")
        bad = Store(Path("."), {"f": Source("f", "x.json", "abc1234", "0" * 64)}, reader=lambda s: body)
        with self.assertRaises(SourceMismatch):
            bad.get("f", "@sha256")                                       # the pin is checked before its fields are printed

    def test_identifiers_and_ids_in_labels(self):
        for t in ("presets l14, l15, l16, before lock-2", "pilot-1", "see TAB-07", "SHA-256"):
            self.assertTrue(label_ok(t), t)

    def test_figure_text_check(self):
        from harness.analysis import paper_out_style as style
        from harness.analysis.paper_outputs import figure_text_problems
        style.apply_rc()
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        k = core.integer(Ref(13, "s", "k"))
        ax.text(0.5, 0.5, f"vote k = {k.printed}")
        ax.set_xlabel("vote size k (95% band)")
        ok = core.FigureOut(fig, [{"series": "v", "k": k.record()}], [label("a vote")])
        self.assertEqual(figure_text_problems(ok), [])
        ax.text(0.2, 0.2, "picker among 8 samples")
        self.assertEqual(figure_text_problems(ok), ["picker among 8 samples"])
        plt.close(fig)

    def test_figure_barred_text(self):
        from harness.analysis import paper_out_style as style
        from harness.analysis.paper_outputs import figure_barred
        style.apply_rc()
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.set_title("Haiku-medium vote at the same money")
        ok = core.FigureOut(fig, [], [label("a vote")])
        self.assertEqual(figure_barred(ok), [])
        ax.text(0.2, 0.2, "the format check (item 17)")
        self.assertEqual(figure_barred(ok), ["the format check (item 17)"])
        bad_alt = core.FigureOut(fig, [], [core.Cell("ruled in D-87; merges F5", kind="label")])   # a stamped text cut can carry one
        self.assertIn("ruled in D-87; merges F5", figure_barred(bad_alt))
        plt.close(fig)


class Writers(unittest.TestCase):
    def test_tex_escape(self):
        self.assertEqual(tex_escape("a_b & 5% " + MINUS + "1"), r"a\_b \& 5\% \ensuremath{-}1")
        self.assertEqual(tex_escape("<0.0001 |d| > 10"), r"\ensuremath{<}0.0001 \ensuremath{|}d\ensuremath{|} \ensuremath{>} 10")
        with self.assertRaises(ValueError):
            tex_escape("一")

    def test_markdown_table_keys(self):
        text = "intro\n| Run ID | USD | Note |\n|---|---|---|\n| a-1 | 0.5 | x \\| y |\n| b-2 | 1.25 | z |\nend"
        self.assertEqual(resolve_text(text, ["L5", "USD"]), "1.25")
        self.assertEqual(resolve_text(text, ["L4", "Note"]), "x | y")
        self.assertEqual(resolve_text(text, ["L1"]), "intro")
        with self.assertRaises(KeyMissing):
            resolve_text(text, ["L5", "Cost"])
        with self.assertRaises(KeyMissing):
            resolve_text(text, ["L1", "USD"])

    def test_table_files(self):
        t = core.Table([label("Arm"), label("Accuracy (%)")], [[label("Opus-medium"), pct(Ref(0.98125, "s", "k"))]])
        self.assertEqual(core.table_csv(t), "Arm,Accuracy (%)\nOpus-medium,98.1\n".encode())
        self.assertIn(rb"\toprule", core.table_tex(t, "TAB-99"))
        doc = core._cells_doc(t)
        self.assertEqual(doc["rows"][0][1]["refs"], [{"source": "s", "key": "k"}])
        t.rows.append([label("x")])
        with self.assertRaises(ValueError):
            t.check()


@unittest.skipUnless(_git_ok(), "the repo's history is not available")
class TiesRow(unittest.TestCase):
    """TAB-11's ties-counted-wrong row reads free analysis 13 only when it is B2's as-deployed tie view at B2's k."""

    def _store(self, fa13: dict) -> Store:
        b2 = {"d": 0.63, "ci95": [-1.15, 2.44], "p": 0.0001, "reading": "non-inferior", "n": 80}
        fam = {"views": {"as_deployed": {"tests": {"B2": b2}, "bases_left_out": {"B2": 0}}}}
        docs = {"s1b": {"confirmatory": {"primary_margin_5": fam, "secondary_margin_10": fam},
                        "descriptive": {"vote_curve_n16": {"k_from_k_json": 6}}},
                "s1b_k": {"k": 6}, "fa13": fa13}
        raw = {k: json.dumps(v).encode() for k, v in docs.items()}
        src = {k: Source(k, f"{k}.json", "abc", hashlib.sha256(b).hexdigest()) for k, b in raw.items()}
        return Store(Path("."), src, reader=lambda s: raw[s.name])

    def _fa13(self, **change) -> dict:
        rep = {"d": 0.63, "ci95": [-1.15, 2.44], "p": 0.0001, "reading": "non-inferior"}
        res = {"test": "B2", "view": "as_deployed", "k": 6, "reproduced": {"primary_margin_5": rep, "secondary_margin_10": rep},
               "ties_as_wrong": {"paired": {"pooled": {"n": 80, "d": -0.03, "ci95": [-2.11, 1.9]}}}}
        res.update(change)
        return {"result": res}

    def test_matching_tie_view_passes_and_others_refuse(self):
        from harness.analysis import paper_out_study1b as s1b
        s1b._b2_ties_check(self._store(self._fa13()))
        bad_rep = {"d": 0.5, "ci95": [-1.15, 2.44], "p": 0.0001, "reading": "non-inferior"}
        for change in ({"k": 5}, {"view": "refusals_out"}, {"test": "B1"},
                       {"reproduced": {"primary_margin_5": bad_rep, "secondary_margin_10": bad_rep}},
                       {"ties_as_wrong": {"paired": {"pooled": {"n": 79, "d": -0.03, "ci95": [-2.11, 1.9]}}}}):
            with self.assertRaises(ValueError, msg=str(change)):
                s1b._b2_ties_check(self._store(self._fa13(**change)))


class PaperLayout(unittest.TestCase):
    """D-159/D-160 writer features: the layout mark first, at most two short notes, bold cells, and ⟦…⟧ placeholders passed through."""

    def test_layout_short_notes_bold_and_placeholders(self):
        from harness.analysis.paper_out_core import Cell, Table, label, table_tex
        t = Table([label("A"), label("B")], [[Cell("w", bold=True), label("see ⟦TAB-14⟧")]],
                  [[label("first")], [label("second")], [label("third")]], short_notes=[0, 2], layout="float")
        tex = table_tex(t, "TAB-99").decode()
        lines = tex.splitlines()
        self.assertEqual(lines[0], "% layout: float")
        self.assertIn(r"\textbf{w} & see ⟦TAB-14⟧ \\", tex)
        self.assertEqual([l.split(":")[0] for l in lines if l.startswith("% note")], ["% note-short", "% note", "% note-short"])
        with self.assertRaises(ValueError):
            table_tex(Table([label("A")], [], [[label("n")]], short_notes=[0, 1]), "TAB-99")
        with self.assertRaises(ValueError):
            table_tex(Table([label("A")], [], layout="sideways"), "TAB-99")
        self.assertEqual(Cell("x", bold=True).record()["bold"], True)
        self.assertNotIn("bold", Cell("x").record())

    def test_longtable_caption_at_template_size_and_width(self):
        """Edith, M1-10: a long table's caption is set at the template's size and the full text width, not longtable's 4 in box; and the
        table compiles (a \\normalsize row before the caption stopped the build: "Misplaced \\noalign")."""
        from harness.analysis.paper_out_core import LONGTABLE_CAPTION_TEX, Table, label, table_tex
        t = Table([label("A"), label("B")], [[label("x"), label("y")]], layout="longtable")
        tex = table_tex(t, "TAB-99").decode().replace("⟦CAPTION⟧", "A caption").replace("⟦LABEL⟧", "tab:x")
        lines = tex.splitlines()
        begin = next(i for i, l in enumerate(lines) if l.startswith(r"\begin{xltabular}"))
        self.assertEqual(lines[begin - 1], LONGTABLE_CAPTION_TEX)
        self.assertTrue(lines[begin + 1].startswith(r"\caption{"))
        tectonic = shutil.which("tectonic")
        if os.environ.get("PARETO_TECTONIC") != "1" or tectonic is None:      # opt-in, so the suite's count does not depend on the machine (Edith's R4)
            self.skipTest("the compile check is opt-in: set PARETO_TECTONIC=1 with tectonic installed")
        with tempfile.TemporaryDirectory() as d:
            doc = (r"\documentclass[10pt]{article}\usepackage{booktabs,xltabular}\begin{document}Text.{\small " + tex + "}\\end{document}")
            (Path(d) / "t.tex").write_text(doc, encoding="utf-8")
            r = subprocess.run([tectonic, "t.tex"], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])

    def test_changes_table_pointers_are_one_form(self):
        """Edith, M1-2: the top-up row points to B.6 like its neighbours, and the supplement's form names the paper."""
        from harness.analysis import paper_out_ops as ops
        self.assertNotIn("top-up start", ops.WHERE)
        self.assertEqual(ops.where_full(ops.WHERE["changes"]), "Appendix B of the paper (Changes to the locked plans)")
        self.assertFalse([v for v in ops.WHERE.values() if "footnote" in v or "earlier start" in v])

    def test_print_form_ids_and_math(self):
        from harness.analysis.paper_out_core import tex_text
        self.assertEqual(tex_text("as in Table TAB-02 and FIG-05"), "as in ⟦TAB-02⟧ and ⟦FIG-05⟧")
        self.assertEqual(tex_text("see ⟦TAB-14⟧"), "see ⟦TAB-14⟧")                       # an existing placeholder is kept once
        self.assertEqual(tex_text("the q^N line and k_c, not kk_c"), r"the $q^{N}$ line and $k_c$, not kk\_c")
        self.assertEqual(tex_text("50% of $3"), r"50\% of \$3")
        self.assertEqual(tex_text("d (points); p, n/a, k = 4; Opus-medium's d."), r"$d$ (points); $p$, n/a, $k$~=~4; Opus-medium's $d$.")
        self.assertEqual(tex_text("the p-value, own-k, x of n, B = 10,000; Appendix B, a-b"),
                         r"the $p$-value, own-$k$, $x$ of $n$, $B$~=~10,000; Appendix~B, a-b")      # Edith, proof 3 (§3.7)
        self.assertEqual(tex_text("the letter x in 6x1; the 1/m rule"), r"the letter x in 6x1; the 1/$m$ rule")
        # a symbol with a possessive is still a symbol (Edith, proof 5, B2-M9); ties before ≤ and ≥ (B2-M10)
        self.assertEqual(tex_text("(q's input) and the k's value; d' and q'x stay"), r"($q$'s input) and the $k$'s value; d' and q'x stay")
        self.assertEqual(tex_text("yes (p ≤ 0.00004, below it)"), "yes ($p$~\\ensuremath{\\leq}~0.00004, below it)")
        self.assertEqual(tex_text("vote_at_own_k.own k vs opus-med"), r"vote\_at\_own\_k.own k vs opus-med")                  # a stamped key's k stays as stamped
        self.assertEqual(tex_text("Study 1's k.json and k = 6"), r"Study~1's k.json and $k$~=~6")                # a file name stays a name
        self.assertEqual(tex_text("q (%) and flag R; Deviation 2 rule, Test B1"), r"$q$ (\%) and flag~R; Deviation~2 rule, Test~B1")

    def test_unbreakable_spaces(self):
        from harness.analysis.paper_out_core import tex_text
        self.assertEqual(tex_text("worse by > 10 (rule)"), r"worse by \ensuremath{>}~10 (rule)")
        self.assertEqual(tex_text("Haiku-medium, k = 4"), "Haiku-medium, $k$~=~4")
        self.assertEqual(tex_text("Haiku-medium ×40"), r"Haiku-medium~\ensuremath{\times}40")
        self.assertEqual(tex_text("a > b, by > margin"), r"a \ensuremath{>}~b, by \ensuremath{>}~margin")    # a sign keeps its word
        self.assertEqual(tex_text("run 2026-10-12, then 2026-10-13T09:00Z"),
                         r"run \mbox{2026-10-12}, then \mbox{2026-10-13}\allowbreak{}\mbox{T09:00Z}")  # a date never breaks at a hyphen
        from harness.analysis import paper_out_core as core
        self.assertEqual([len(core._pieces(core.Cell(x))) for x in ("2026-10-12", "2026-10-12T09:00Z", "Opus-medium")], [1, 2, 1])

    def test_exact_thresholds_and_unsigned_intervals(self):
        from harness.analysis import paper_out_core as core
        ref = lambda v: core.Ref(v, "src", "k")
        self.assertEqual([core.exact(ref(v)).printed for v in (0.005, 0.00625, 0.025 / 3, 0.0125, 0.05, 0.05 / 3)],
                         ["0.005", "0.00625", "0.00833", "0.0125", "0.05", "0.0167"])
        self.assertEqual(core.interval(ref(-1.15), ref(2.44), dp=1, signed=True).printed, "[−1.2, 2.4]")    # Edith §2.4: no "+"

    def test_label_once_per_group_and_spaced_rows(self):
        from harness.analysis.paper_out_core import Table, label, table_tex, split_tables
        t = Table([label("Study"), label("Setting")], [[label(s), label(x)] for s, x in
                  (("Study A", "one"), ("Study A", "two"), ("Study B", "three"), ("Study B", "four"))], layout="float",
                  groups=[2], once=[0], spaced=True)
        body = [l for l in table_tex(t, "TAB-99").decode().splitlines() if l.endswith(r"\\")][1:]
        self.assertEqual([b.split(" & ")[0] for b in body], ["Study~A", "", "Study~B", ""])    # the CSV keeps every value
        tex = table_tex(t, "TAB-99").decode()
        self.assertEqual((tex.count(r"\addlinespace[1em]"), tex.count("\\addlinespace\n")), (1, 2))
        t.split_parts = [(None, [1])]
        self.assertEqual((split_tables(t)[0].once, split_tables(t)[0].spaced), ([0], True))

    def test_sideways_packing(self):
        from harness.analysis.paper_out_core import Table, label, plan_packing, split_tables, table_tex
        short = [[label(f"row {chr(97 + i)}"), label("x" * 3)] for i in range(4)]
        t = Table([label("Key"), label("Value")], short, layout="split landscape")
        t.split_parts = [([0, 1], [1]), ([2, 3], [1])]
        plan_packing(t)
        self.assertEqual(t.pack_parts, [1])                                      # two short parts share one sideways page
        self.assertIn("% pack: with-previous", table_tex(split_tables(t)[1], "TAB-99").decode())
        tall = Table([label("Key"), label("Value")], [[label(f"row {chr(97 + i % 26)}{i}"), label("y")] for i in range(40)],
                     layout="split landscape")
        tall.split_parts = [(list(range(20)), [1]), (list(range(20, 40)), [1])]
        plan_packing(tall)
        self.assertEqual(tall.pack_parts, [])                                    # two tall ones do not

    def test_split_by_rows_with_shared_widths(self):
        from harness.analysis.paper_out_core import Table, height_in, label, split_rows_by_space, split_tables
        text = "a rule text long enough to wrap over several lines of a narrow column in the sideways table"
        rows = [[label(f"check {chr(97 + i % 26)}"), label(f"quantity {chr(97 + i % 26)}{chr(98 + i % 24)}"), label(text)]
                for i in range(60)]
        t = Table([label("Check"), label("Quantity"), label("Rule")], rows, layout="landscape")
        split_rows_by_space(t, [0, 1], [2])
        parts = split_tables(t)
        self.assertGreater(len(parts), 1)
        self.assertEqual(sum(len(p.rows) for p in parts), 60)                                 # every row once, in order
        self.assertEqual(len({p.fixed_plan[1].__repr__() for p in parts}), 1)                 # one shared set of widths
        self.assertTrue(all(height_in(p) <= 6.5 for p in parts))
        self.assertLess(height_in(Table(t.columns, rows[:5], layout="landscape")), height_in(Table(t.columns, rows[:10], layout="landscape")))
        t.split_parts = [(None, [2]), (None, [1])]
        with self.assertRaises(ValueError):                                                    # parts with different columns
            split_tables(t)

    def test_curly_quotes(self):
        from harness.analysis.paper_out_core import tex_text
        self.assertEqual(tex_text('"(exact; n = 40)" marks it'), "``(exact; $n$~=~40)'' marks it")
        self.assertEqual(tex_text("the 'x' rule and the vote's share ('as stamped')"), "the `x' rule and the vote's share (`as stamped')")
        self.assertEqual(tex_text("“curly” and ‘single’"), "``curly'' and `single'")
        self.assertEqual(tex_text('the "\'structure effect\'"'), "the ``{}`structure effect'{}''")    # nested quotes keep their order

    def test_fixed_width_columns_and_font_mark(self):
        import re
        from harness.analysis.paper_out_core import Table, label, table_tex
        long = "a long text cell that has to wrap somewhere in the column"
        t = Table([label("Name"), label("Text one"), label("Text two")], [[label("x"), label(long), label(long)]] * 3, layout="float",
                  font="footnotesize")
        lines = table_tex(t, "TAB-99").decode().splitlines()
        self.assertEqual(lines[:2], ["% layout: float", "% font: footnotesize"])
        spec = next(l for l in lines if l.startswith(r"\begin{tabularx}{\linewidth}"))
        hs = [float(x) for x in re.findall(r"\\hsize=([\d.]+)\\hsize", spec)]
        self.assertEqual(len(hs), 2)
        self.assertAlmostEqual(sum(hs), 2.0, places=2)                                    # tabularx: the factors sum to the X count

    def test_fewest_lines_widens_a_row_tall_in_three_columns(self):
        from harness.analysis import paper_out_core as core
        cells = {j: [core._pieces(core.label("aaaa bbbb cccc"))] for j in range(3)}
        lo = {j: max(w for _, w in cells[j][0]) / core.PT_PER_IN + 0.04 for j in range(3)}
        one = core._one_line_pt(cells[0][0]) / core.PT_PER_IN + 0.04
        w = core._fewest_lines(cells, lo, 3 * one + 0.05)
        self.assertTrue(all(core._wrapped_lines(cells[j][0], (w[j] - 0.04) * core.PT_PER_IN) == 1 for j in range(3)))
        w = core._fewest_lines(cells, lo, 3 * one - 0.05)                                   # no room for one line in all three
        self.assertGreater(max(core._wrapped_lines(cells[j][0], (w[j] - 0.04) * core.PT_PER_IN) for j in range(3)), 1)

    def test_split_parts(self):
        from harness.analysis import paper_outputs
        from harness.analysis.paper_out_core import Table, label, split_columns, split_tables
        t = Table([label(c) for c in ("Key", "A", "B", "C")], [[label(f"r{x}") for x in "abcd"]] * 2, [[label("note")]],
                  short_notes=[0], layout="split")
        t.split_parts = [(None, [1, 2]), ([0], [3])]
        p1, p2 = split_tables(t)
        self.assertEqual([c.printed for c in p1.columns], ["Key", "A", "B"])
        g = Table([label(c) for c in ("Key", "A", "Hash")], [[label(f"r{i}"), label("x"), label("abc")] for i in range(4)],
                  layout="split", groups=[2], mono=[2])
        g.split_parts = [(None, [1]), ([1, 2, 3], [2])]
        g1, g2 = split_tables(g)
        self.assertEqual((g1.groups, g1.mono, g2.groups, g2.mono), ([2], [], [1], [1]))    # groups and typewriter columns carry over
        self.assertEqual(([c.printed for c in p2.columns], len(p2.rows)), (["Key", "C"], 1))
        self.assertEqual((p1.notes, p2.short_notes), ([], [0]))                              # the notes print once, under the last part
        with tempfile.TemporaryDirectory() as d:
            files = {}
            paper_outputs._write_tex(Path(d), "TAB-99", "TAB-99", t, "TAB-99.cells.json", files)
            self.assertEqual(sorted(files), ["TAB-99.part2.tex", "TAB-99.tex"])
            self.assertTrue((Path(d) / "TAB-99.tex").read_text().startswith("% layout: split\n"))
            self.assertFalse((Path(d) / "TAB-99.part2.tex").read_text().startswith("% layout"))
        wide = Table([label("Key")] + [label(f"Column {x}") for x in "ABCDEFGHIJKL"], [[label("a fairly long cell text")] * 13])
        parts = split_columns(wide, landscape=False)
        self.assertGreater(len(parts), 1)
        self.assertEqual([j for p in parts for j in p], list(range(1, 13)))

    def test_settings_table_helpers(self):
        from harness.analysis import paper_out_main as m
        from harness.analysis.paper_out_core import Cell
        n = lambda v: Cell(str(v), raw=v, refs=("a source",))                                # a sourced number (refs are opaque here)
        self.assertEqual(m._times([("Haiku-medium", n(10)), ("Opus-medium", n(1)), ("Sonnet-medium", n(1))]).printed,
                         "Haiku-medium ×10; Opus-medium, Sonnet-medium ×1")
        self.assertEqual(m._times([("Haiku-low", n(40)), ("Haiku, thinking off", n(40))]).printed,
                         "Haiku-low ×40; Haiku, thinking off ×40")                            # a name with a comma keeps its own ×N
        self.assertEqual(m._tests_of(["haiku-med"]), "Tests 1–3")
        self.assertEqual(m._tests_of(["opus-med", "sonnet-med", "opus-low"]), "Tests 1–5")
        self.assertEqual(m._tests_of(["e3"]), "Test 4")
        self.assertEqual(m._efforts(("ho", "hl", "hm", "hh", "hxh")), "off–xhigh")
        self.assertEqual(m._efforts(("ol", "oh", "oxh", "ox")), "low, high–max")
        with self.assertRaises(ValueError):
            m._efforts(("ol", "sl"))


class PolishChecks(unittest.TestCase):
    """paper_out_lint: Edith's polish-standard table checks (§2.8, §7.2-7.6), the spelling system (§3.3) and D-161's retired terms."""

    def _t(self, rows, cols=("Name", "Accuracy (%)"), **kw):
        from harness.analysis.paper_out_core import Cell, Table, label
        cell = lambda x: Cell(x, raw=0, refs=("a source",)) if any(ch.isdigit() for ch in x) else label(x)
        return Table([label(c) for c in cols], [[cell(x) for x in r] for r in rows], **kw)

    def test_token_medians_as_stamped(self):
        # Edith's #39 review, S1: a token median prints as stamped (a whole number or a half) and its column aligns on the point
        from harness.analysis import paper_out_lint as lint
        cols = ("Setting", "Median thinking tokens")
        self.assertEqual(lint.decimals(self._t([["a", "600"], ["b", "7,604.5"], ["c", "1,737"]], cols=cols)), [])
        self.assertEqual(len(lint.decimals(self._t([["a", "600"], ["b", "7,604.25"]], cols=cols))), 1)
        t = self._t([["a", "600"], ["b", "7,604.5"], ["c", "1,737"]], cols=cols, layout="float")
        tex = core.table_tex(t, "TAB-99").decode()
        self.assertIn(r"600\phantom{.0}", tex)
        self.assertNotIn(r"7,604.5\phantom", tex)

    def test_decimals_and_guard(self):
        from harness.analysis import paper_out_lint as lint
        self.assertEqual(lint.decimals(self._t([["a", "12.3"], ["b", "45.6"]])), [])
        self.assertEqual(len(lint.decimals(self._t([["a", "12.3"], ["b", "45.67"]]))), 1)
        self.assertEqual(lint.decimals(self._t([["a", "12.3"], ["b", "0.04"], ["c", "+4.96"]])), [])     # one more decimal near 0, 5
        self.assertEqual(lint.decimals(self._t([["a", "40; 0.909"], ["b", "—; 0.088"]], cols=("Name", "k; cost ratio"))), [])
        self.assertEqual(lint.decimals(self._t([["a", "0.00123"], ["b", "0.0456"]], cols=("Name", "Cost (US$)"))), [])
        self.assertEqual(len(lint.decimals(self._t([["a", "0.0012"], ["b", "0.0456"]], cols=("Name", "Cost (US$)")))), 1)
        self.assertEqual(lint.decimals(self._t([["a", "0.9998"], ["b", "0.250"], ["c", "0.125"]], cols=("Name", "Spend share"))), [])
        self.assertEqual(lint.decimals(self._t([["a", "0.005"], ["b", "0.00833"]], cols=("Name", "Holm threshold"))), [])
        self.assertEqual(len(lint.decimals(self._t([["a", "0.00500"], ["b", "0.00833"]], cols=("Name", "Holm threshold")))), 1)

    def test_paper_forms(self):
        from harness.analysis import paper_out_lint as lint
        ratio = ("Name", "Error-rate ratio [95% interval]")
        self.assertEqual(lint.paper_precision(self._t([["a", "3.4 [1.8, 10.1]"], ["b", "undefined (comparator errors 0 of 80)"]],
                                                      cols=ratio)), [])
        self.assertEqual(len(lint.paper_precision(self._t([["a", "3.37 [1.78, 10.07]"]], cols=ratio))), 2)     # 10.07 is a guard cell near 10
        got = lint.forms(self._t([["Tests 1-3 and lock 2", "+0.6 [−1.1, +2.4]"]]))
        self.assertEqual(len(got), 3)
        self.assertEqual(lint.forms(self._t([["Tests 1–3, Lock 2, 2026-10-12", "+0.6 [−1.1, 2.4]"]])), [])
        from harness.analysis.paper_out_core import label
        t = self._t([["a", "1.0"]], layout="float", short_notes=[0, 1])
        t.notes = [[label("a note of some words that is long enough to fill most of one printed line of the paper's notes " * 2)]] * 2
        self.assertTrue(any("together" in p for p in lint.notes(t, True)))                 # the paper prints its notes as one paragraph

    def test_constant_headers_units_bold_spelling(self):
        from harness.analysis import paper_out_lint as lint
        from harness.analysis.paper_out_core import Cell
        self.assertEqual(len(lint.constant_columns(self._t([["a", "1.0"], ["a", "2.0"]]))), 1)
        self.assertEqual(lint.headers(self._t([["a", "1.0"]], cols=("Name", "d (points) [95% interval]"))), [])
        self.assertEqual(lint.headers(self._t([["a", "1.0"]], cols=("Deviation 2 rule", "Accuracy at B1 (%)"))), [])
        self.assertEqual(len(lint.headers(self._t([["a", "1.0"]], cols=("Name", "Accuracy Rate (%)")))), 1)
        self.assertEqual(len(lint.headers(self._t([["a", "12.0%"]]))), 1)
        t = self._t([["a", "1.0"]])
        t.rows[0][0] = Cell("a", kind="label", bold=True)
        self.assertEqual(len(lint.bold(t)), 1)
        self.assertEqual(lint.spelling(self._t([["the labelled colour", "1.0"]])), [])
        self.assertEqual(len(lint.spelling(self._t([["the labeled color", "1.0"]]))), 2)

    def test_decimal_alignment_and_typewriter_columns(self):
        from harness.analysis.paper_out_core import Table, label, table_tex, mono_tex
        t = self._t([["a", "0.00123"], ["b", "0.0456"]], cols=("Name", "Cost (US$)"))
        t.layout = "float"
        self.assertIn(r"0.0456\phantom{0} \\", table_tex(t, "TAB-99").decode())                # decimal points line up
        self.assertEqual(mono_tex("sha256:9f71dc7893cf35c1 x_1"), r"\texttt{sha256:9f71dc78\allowbreak{}93cf35c1 x\_1}")
        g = self._t([["a", "1.0"], ["b", "2.0"], ["c", "3.0"]])
        g.layout, g.groups = "float", [2]
        self.assertEqual(table_tex(g, "TAB-99").decode().count(r"\addlinespace"), 1)            # row groups (Edith §7.7)

    def test_figure_checks(self):
        from harness.analysis import paper_out_style as style
        style.apply_rc()
        fig = style.plt.figure(figsize=(7.0, 3.0))
        ax = fig.add_subplot(1, 1, 1)
        ax.plot([1, 2], [1, 2], color="#1f77b4")
        ax.set_xlabel("steps in the puzzle")
        ax.text(1, 1, "small", fontsize=6)
        ax.text(1, 1.5, "p < 0.05")
        ax.set_ylabel("Accuracy (%)")
        ax.set_ylim(0, 105)
        ax.grid(axis="x")
        got = " | ".join(style.figure_problems(fig))
        for what in ("width 7.00 in", "text at 6.0 pt", "colours outside the palette", "not in sentence case", "cmr10 prints wrongly",
                     "runs past 100", "vertical gridlines", "height 3.00 in"):
            self.assertIn(what, got)
        style.plt.close(fig)
        fig = style.plt.figure(figsize=(4.5, 2.4))
        ax = fig.add_subplot(1, 1, 1)
        ax.plot([1, 2], [1, 2], color=style.color("haiku", "high"), marker=style.MODEL_MARKER["haiku"])
        ax.set_xlabel("Steps in the puzzle")
        ax.set_ylabel("Accuracy (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="y")
        ax.text(1, 1.5, "p $<$ 0.05; \\$0.01")
        self.assertEqual(style.figure_problems(fig), [])
        style.plt.close(fig)

    @unittest.skipUnless(_git_ok(), "the repo's history is not available")
    def test_retired_terms_from_karens_list(self):
        from harness.analysis import paper_out_lint as lint
        self.assertEqual(lint.vocabulary_texts(["one sample per puzzle, cost-matched"]), [])
        got = lint.vocabulary_texts(["three tries per base puzzle", 'the plan\'s word "arm" in quotes'])
        self.assertEqual([g.split(" (")[0] for g in got], ["retired term 'base puzzle' x1", "retired term 'tries' x1"])
        got = lint.vocabulary_texts(["the vote's share and each arm's share"])           # two apostrophes are not a quotation
        self.assertEqual([g.split(" (")[0] for g in got], ["retired term 'arm' x1"])


class AnonymousVariants(unittest.TestCase):
    """paper_out_anon's rewriter: identifiers withheld, the services named in neutral words, capitals only where a cell starts with one,
    and Vision's scan patterns read from her pinned anon.py."""

    def test_rewrites(self):
        from harness.analysis import paper_out_anon as pa
        rw = pa.Rewriter()
        self.assertEqual(rw.text("gist f8da61f9…; Wayback 20261011193547"), "withheld for review")
        self.assertEqual(rw.text("DOI 10.5281/zenodo.23304164"), "DOI withheld for review")
        self.assertEqual(rw.text("20261011193547"), "20261011193547")                          # only in the snapshot column
        self.assertEqual(rw.text("20261011193547", snapshot_column=True), "withheld for review")
        self.assertEqual(rw.text("Lock 1 public proof: gist with a Wayback snapshot"), "Lock 1 public proof: public posting with an archived snapshot")
        self.assertEqual(rw.text("the run may start before Zenodo v3 is published"), "the run may start before archive record v3 is published")
        self.assertEqual(rw.text("Lock 4 public proof: Zenodo v4 record created"), "Lock 4 public proof: archive record v4 created")
        self.assertEqual(rw.text("set a Zenodo record plus a gist"), "set an archive record plus a posting")
        self.assertEqual(rw.text("Wayback snapshot"), "Archived snapshot")                     # a column title keeps its capital
        self.assertEqual(rw.text("no gist or Wayback"), "no posting or snapshot")

    @unittest.skipUnless(_git_ok(), "the repo's history is not available")
    def test_scan_patterns_and_refusal(self):
        from harness.analysis import paper_out_anon as pa
        pats = pa.vision_patterns()
        self.assertEqual(len(pats), 3)
        self.assertTrue(any(p.search("see the Zenodo record") for p in pats))
        self.assertFalse(any(p.search(pa.Rewriter().text("see the Zenodo record and the gist")) for p in pats))


class RealBuild(unittest.TestCase):
    IDS = ["TAB-01", "TAB-02", "TAB-21", "TAB-24", "FIG-07"]

    def test_build_is_deterministic_and_traced(self):
        from harness.analysis import paper_outputs
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            m1 = paper_outputs.build(REPO, Path(a), only=self.IDS)
            m2 = paper_outputs.build(REPO, Path(b), only=self.IDS)
            self.assertEqual([e["files"] for e in m1["outputs"]], [e["files"] for e in m2["outputs"]])
            for e in m1["outputs"]:
                if e["status"] != "built" or e["kind"] != "table":
                    continue
                doc = json.loads((Path(a) / f"{e['id']}.cells.json").read_text())
                for row in doc["table"]["rows"]:
                    for cell in row:
                        if cell["kind"] == "num":
                            self.assertTrue(cell["refs"], cell)
                            for r in cell["refs"]:
                                self.assertIn(r["source"], doc["sources"])
                self.assertEqual(doc["output"]["id"], e["id"])


class AnonymousSplitTable(unittest.TestCase):
    """The anonymous variant of a table split by rows (S7, Edith's ruling of 2026-10-20) is written in parts, every part anonymised."""

    def _split_table(self):
        from harness.analysis.paper_out_core import Table, label, split_rows_by_space
        text = "a gist with a Wayback snapshot long enough to wrap over several lines of a narrow column in the sideways table"
        rows = [[label(f"check {chr(97 + i % 26)}"), label(f"quantity {chr(97 + i % 26)}{chr(98 + i % 24)}"), label(text)]
                for i in range(60)]
        t = Table([label("Check"), label("Quantity"), label("Rule")], rows, [[label("note")]], layout="landscape")
        split_rows_by_space(t, [0, 1], [2])
        self.assertGreater(len(core.split_tables(t)), 1)
        return t

    def test_split_table_keeps_its_split_and_is_written_in_parts(self):
        from harness.analysis import paper_out_anon as pa
        from harness.analysis import paper_outputs
        t = self._split_table()
        a = pa.Rewriter().table(t)
        self.assertEqual((a.split_parts, a.split_key, a.share_widths), (t.split_parts, t.split_key, t.share_widths))
        n = len(core.split_tables(t))
        self.assertEqual(len(core.split_tables(a)), n)
        meta = core.Meta("TAB-99", "table", "A title", "A section", "label", "content", "keys")
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            named, anon, files = {}, [], {}
            paper_outputs._write_tex(out, "TAB-99", "TAB-99", t, "TAB-99.cells.json", named)
            anon = paper_outputs._write_anon(out, "TAB-99", a, meta, {}, files)
            want = ["TAB-99.anon.tex"] + [f"TAB-99.part{k}.anon.tex" for k in range(2, n + 1)]
            self.assertEqual([x for x in anon if x.endswith(".tex")], want)
            for k, name in enumerate(want):
                self.assertTrue((out / name).exists(), name)
                text = (out / name).read_text()
                self.assertEqual(text.startswith("% layout:"), k == 0)                    # the layout mark on the first file only
                self.assertNotIn("Wayback", text)                                         # every part is anonymised, not just the first
                self.assertNotIn("gist", text)
                twin = (out / ("TAB-99.tex" if k == 0 else f"TAB-99.part{k + 1}.tex")).read_text()
                rows = lambda s: [l for l in s.splitlines() if l.endswith(r"\\")]
                self.assertEqual(len(rows(text)), len(rows(twin)))                        # the same rows in each part as the named part
            last = (out / want[-1]).read_text()
            self.assertEqual(sum(l.startswith("% note:") for l in last.splitlines()), 1)  # the notes print once, under the last part

    def test_a_split_panel_is_still_refused(self):
        from harness.analysis import paper_out_anon as pa
        from harness.analysis.paper_out_core import Table, label
        holder = Table([label("A")], [], panels=[("Panel 1", self._split_table())])
        with self.assertRaises(ValueError):
            pa.Rewriter().table(holder)


if __name__ == "__main__":
    unittest.main()
