"""Two converter fixes in paper/tools/to_latex.py (job J, 2026-10-28). Synthetic Markdown strings only; no data files.

1. "Flag R" gets a tie ("Flag~R") that must reach the LaTeX as a tie, not as \\textasciitilde{} (esc() would turn a bare ~ into
   a printed tilde).
2. The one short formula $1/m$ prints as maths, and a dollar amount (such as $0.0112) never does.
"""
import importlib.util
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "paper" / "tools" / "to_latex.py"
if not SRC.is_file():
    raise unittest.SkipTest("paper/tools/to_latex.py is not in the released package (the paper's source goes to arXiv)")


def load():
    spec = importlib.util.spec_from_file_location("to_latex_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TO_LATEX = load()


def conv(text):
    return TO_LATEX.inline(text, [])


class FlagTie(unittest.TestCase):
    def test_flag_letter_gets_a_real_tie(self):
        out = conv("Flag R was raised on both runs.")
        self.assertIn("Flag~R", out)
        self.assertNotIn("textasciitilde", out)

    def test_every_flag_in_a_sentence(self):
        out = conv("Flag A, Flag B and Flag Z.")
        self.assertEqual(out, "Flag~A, Flag~B and Flag~Z.")

    def test_a_typed_tilde_is_still_escaped(self):
        self.assertIn("\\textasciitilde{}", conv("about ~5 points"))

    def test_flag_before_a_word_is_left_alone(self):
        self.assertEqual(conv("Flag rules apply."), "Flag rules apply.")


class OneOverM(unittest.TestCase):
    def test_one_over_m_is_maths(self):
        out = conv("scores $1/m$.")
        self.assertEqual(out, "scores $1/m$.")
        self.assertNotIn("\\$", out)

    def test_the_sentence_with_m_and_one_over_m(self):
        out = conv("shared by $m$ answers, the right one among them, scores $1/m$. It is reported once.")
        self.assertEqual(out, "shared by $m$ answers, the right one among them, scores $1/m$. It is reported once.")

    def test_one_letter_symbols_still_work(self):
        self.assertEqual(conv("with $k$ samples and $k_c$ checks"), "with $k$ samples and $k_c$ checks")

    def test_dollar_amounts_stay_dollar_amounts(self):
        for amount in ("$0.0112", "$104.14", "$200", "$1", "$0.50"):
            out = conv(f"It cost {amount} in total.")
            self.assertEqual(out, f"It cost \\{amount} in total.", amount)

    def test_two_dollar_amounts_in_one_sentence(self):
        out = conv("It cost $5 and then $10, against a budget of $200.")
        self.assertEqual(out, "It cost \\$5 and then \\$10, against a budget of \\$200.")

    def test_a_price_per_unit_stays_a_dollar_amount(self):
        out = conv("The prices were $1/M tokens in and $5/M tokens out.")
        self.assertEqual(out, "The prices were \\$1/M tokens in and \\$5/M tokens out.")

    def test_dollar_amount_beside_one_over_m(self):
        out = conv("A tie scores $1/m$ and a run costs $0.0112 or $104.14.")
        self.assertEqual(out, "A tie scores $1/m$ and a run costs \\$0.0112 or \\$104.14.")

    def test_only_one_over_a_letter_is_maths(self):
        self.assertEqual(conv("a cost of $2/m$ here"), "a cost of \\$2/m\\$ here")
        self.assertEqual(conv("a cost of $1/mm$ here"), "a cost of \\$1/mm\\$ here")


if __name__ == "__main__":
    unittest.main()
