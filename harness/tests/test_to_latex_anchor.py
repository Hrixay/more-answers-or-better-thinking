"""Tests for the converter's float placement options (paper/tools/to_latex.py, job L, 2026-10-29). Synthetic Markdown and table
files only; no data needed.

1. A "<!-- float: TAB-xx -->" block places that float there instead of after the first paragraph that mentions it, and prints
   nothing; ", text waits" adds a closing barrier; ", page foot" prints it at a page's foot; ", named copy" applies to the named
   paper only. A "<!-- top closed -->" block ends the paragraph before it with \\suppressfloats[t] (Edith's P9-6, proof 9).
2. A split table whose parts are all landscape pages keeps its opening \\FloatBarrier but has no closing one, so the text after it
   runs on to the foot of the page; a split table with an upright part keeps both barriers (proof 3, C.30).
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if not (REPO / "paper" / "tools" / "to_latex.py").is_file():
    raise unittest.SkipTest("paper/tools/to_latex.py is not in the released package (the paper's source goes to arXiv)")
_spec = importlib.util.spec_from_file_location("to_latex_anchor", REPO / "paper" / "tools" / "to_latex.py")
to_latex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(to_latex)

DOC = ("## Appendix: test\n\nFirst paragraph names Table TAB-90 here.\n\nSecond paragraph.\n\n<!-- float: TAB-90 -->\n\n"
       "Third paragraph.\n")
FLOAT = "\\begin{table}[t]\nSTUB\n\\end{table}"


class Anchor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = (to_latex.PLACEMENT, to_latex.DIAGRAMS, to_latex.FULL_PLACEMENT, to_latex.APPENDIX_FIGURES,
                      to_latex.float_tex, to_latex.ANON, to_latex.SUPPLEMENT)
        to_latex.PLACEMENT, to_latex.DIAGRAMS, to_latex.FULL_PLACEMENT, to_latex.APPENDIX_FIGURES = {"TAB-90": "A-test"}, {}, {}, {}
        to_latex.float_tex = lambda cid, caps, outputs, variant=None: FLOAT
        to_latex.ANON = to_latex.SUPPLEMENT = False

    def tearDown(self):
        (to_latex.PLACEMENT, to_latex.DIAGRAMS, to_latex.FULL_PLACEMENT, to_latex.APPENDIX_FIGURES,
         to_latex.float_tex, to_latex.ANON, to_latex.SUPPLEMENT) = self.saved
        self.tmp.cleanup()

    def place(self, md):
        tex = to_latex.convert("A-test", md)
        out, placed = to_latex.place_floats("A-test", tex, {}, self.tmp.name, {"TAB-90"})
        self.assertEqual(placed, ["TAB-90"])
        return out

    def test_the_marker_names_the_place(self):
        out = self.place(DOC)
        self.assertLess(out.index("Second paragraph."), out.index("STUB"))
        self.assertLess(out.index("STUB"), out.index("Third paragraph."))

    def test_without_a_marker_the_first_mention_anchors_it(self):
        out = self.place(DOC.replace("<!-- float: TAB-90 -->\n\n", ""))
        self.assertLess(out.index("STUB"), out.index("Second paragraph."))

    def test_the_marker_prints_nothing(self):
        out = self.place(DOC)
        self.assertNotIn("float here", out)
        self.assertNotIn("<!--", out)

    def test_text_waits_adds_a_closing_barrier(self):
        out = self.place(DOC.replace("TAB-90 -->", "TAB-90, text waits -->"))
        self.assertIn("\\end{table}\n\\FloatBarrier", out)
        out = self.place(DOC)
        self.assertNotIn("\\FloatBarrier", out[out.index("STUB"):])

    def test_named_copy_marker_is_ignored_in_the_review_copy(self):
        md = DOC.replace("TAB-90 -->", "TAB-90, named copy -->")
        out = self.place(md)
        self.assertLess(out.index("Second paragraph."), out.index("STUB"))  # named build: the marker applies
        to_latex.ANON = True
        out = self.place(md)
        self.assertLess(out.index("STUB"), out.index("Second paragraph."))  # review build: the first mention anchors it

    def test_page_foot_prints_at_the_foot_in_the_named_copy_only(self):
        md = DOC.replace("TAB-90 -->", "TAB-90, page foot, named copy -->")
        out = self.place(md)
        self.assertIn("\\begin{table}[!b]", out)  # named build: at a page's foot, at the marker
        self.assertLess(out.index("Second paragraph."), out.index("STUB"))
        for anon, supplement in ((True, False), (False, True)):  # review copy, then the supplement: as with no marker
            to_latex.ANON, to_latex.SUPPLEMENT = anon, supplement
            out = self.place(md)
            self.assertNotIn("[!b]", out)
            self.assertIn("\\begin{table}[tb]", out)
            self.assertLess(out.index("STUB"), out.index("Second paragraph."))

    def test_top_closed_ends_the_paragraph_before_it_in_the_named_copy_only(self):
        md = DOC.replace("<!-- float: TAB-90 -->\n\n", "").replace("here.\n\n", "here.\n\n<!-- top closed, named copy -->\n\n")
        out = self.place(md)
        closed = out.index("\\par\\suppressfloats[t]")  # named build: after the paragraph, before the float it anchors
        self.assertLess(out.index("here."), closed)
        self.assertLess(closed, out.index("STUB"))
        self.assertNotIn("<!--", out)
        for anon, supplement in ((True, False), (False, True)):  # review copy, then the supplement: nothing changes
            to_latex.ANON, to_latex.SUPPLEMENT = anon, supplement
            self.assertNotIn("\\par\\suppressfloats", self.place(md))
            self.assertEqual(self.place(md), self.place(md.replace("<!-- top closed, named copy -->\n\n", "")))

    def test_page_foot_without_named_copy_applies_to_every_copy(self):
        md = DOC.replace("TAB-90 -->", "TAB-90, page foot -->")
        for anon, supplement in ((False, False), (True, False), (False, True)):  # named paper, review copy, supplement
            to_latex.ANON, to_latex.SUPPLEMENT = anon, supplement
            out = self.place(md)
            self.assertIn("\\begin{table}[!b]", out)
            self.assertLess(out.index("Second paragraph."), out.index("STUB"))

    def test_top_closed_without_named_copy_applies_to_every_copy(self):
        md = DOC.replace("<!-- float: TAB-90 -->\n\n", "").replace("here.\n\n", "here.\n\n<!-- top closed -->\n\n")
        for anon, supplement in ((False, False), (True, False), (False, True)):  # named paper, review copy, supplement
            to_latex.ANON, to_latex.SUPPLEMENT = anon, supplement
            out = self.place(md)
            self.assertLess(out.index("here."), out.index("\\par\\suppressfloats[t]"))
            self.assertLess(out.index("\\par\\suppressfloats[t]"), out.index("STUB"))
            self.assertNotIn("<!--", out)

    def test_a_marker_for_a_float_the_file_does_not_place_stops_the_build(self):
        tex = to_latex.convert("A-test", DOC.replace("float: TAB-90", "float: TAB-91"))
        with self.assertRaises(SystemExit):
            to_latex.place_floats("A-test", tex, {}, self.tmp.name, {"TAB-90"})


def _part(layout=None):
    return ("% layout: " + layout + "\n" if layout else "") + "\\begin{tabular}{ll}\nA & B \\\\\n\\end{tabular}\n"


class RunsOn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outputs = os.path.join(self.tmp.name, "outputs")
        os.makedirs(self.outputs)
        self.saved = (to_latex.OUT_TABLES, to_latex.SUPPLEMENT, to_latex.ANON)
        to_latex.OUT_TABLES, to_latex.SUPPLEMENT, to_latex.ANON = os.path.join(self.tmp.name, "tables"), True, False

    def tearDown(self):
        to_latex.OUT_TABLES, to_latex.SUPPLEMENT, to_latex.ANON = self.saved
        self.tmp.cleanup()

    def build(self, files, layout):
        for name, text in files.items():
            Path(self.outputs, name + ".tex").write_text(text, encoding="utf-8")
        names = [n for n in files if ".part" not in n]
        return to_latex.redesigned_table("TAB-90", names, "The caption", "tab:TAB-90", layout, self.outputs)

    def test_all_landscape_parts_run_on(self):
        tex = self.build({"TAB-90": _part("split landscape"), "TAB-90.part2": _part()}, "split landscape")
        self.assertTrue(tex.startswith("\\FloatBarrier"))
        self.assertEqual(tex.count("\\FloatBarrier"), 1)
        self.assertEqual(tex.count("\\begin{sidewaystable}"), 2)
        self.assertTrue(tex.rstrip().endswith("\\end{sidewaystable}"))

    def test_an_upright_part_keeps_the_closing_barrier(self):
        tex = self.build({"TAB-90": _part("split landscape"), "TAB-90.part2": _part(),
                          "TAB-90.panel1": _part("float")}, "split landscape")
        self.assertTrue(tex.startswith("\\FloatBarrier"))
        self.assertTrue(tex.rstrip().endswith("\\FloatBarrier"))

    def test_upright_split_parts_keep_both_barriers(self):
        tex = self.build({"TAB-90": _part("split"), "TAB-90.part2": _part()}, "split")
        self.assertTrue(tex.startswith("\\FloatBarrier"))
        self.assertTrue(tex.rstrip().endswith("\\FloatBarrier"))


if __name__ == "__main__":
    unittest.main()
