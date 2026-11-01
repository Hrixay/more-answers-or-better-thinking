"""The D-76 parser: Karen's 148 crafted replies (`research/fixtures/sim-main-v2/parse_cases.jsonl.gz`) and one test per accept and reject rule."""

import gzip
import json
import unittest
from pathlib import Path

from harness.analysis import trace_parse as tp
from harness.taskgen import prompt_d31

CASES = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v2" / "parse_cases.jsonl.gz"
L = 3
STATES = [(100 + k, 200 + k, 300 + k) for k in range(1, 25)]


def line(k, state=None, fmt="1.{k} = [{v}]"):
    state = STATES[k - 1] if state is None else state
    return fmt.format(k=k, v=", ".join(str(x) for x in state))


def reply(lines=None, answer="Answer: 1 = [124, 224, 324]"):
    lines = [line(k) for k in range(1, 25)] if lines is None else lines
    return "\n".join(lines + ([answer] if answer is not None else []))


ANSWER_LINE_FAILURES = ("no_answer", "non_integer", "wrong_length", "answer_mismatch")    # when the step lines themselves are readable


def lines_with(k, text):
    out = [line(j) for j in range(1, 25)]
    out[k - 1] = text
    return out


class KarensCases(unittest.TestCase):
    @unittest.skipUnless(CASES.is_file(), "research/fixtures/sim-main-v2 is not in this tree")
    def test_every_case_ok_or_not_and_the_states_and_answer_when_ok(self):
        with gzip.open(CASES, "rt") as f:
            cases = [json.loads(ln) for ln in f if ln.strip()]
        cases = [c for c in cases if "-r2-" not in c["id"]]        # round 1 (148); round 2 is run by Karen's runner (test_analysis_parse_fixtures)
        self.assertEqual(len(cases), 148)
        self.assertEqual(sorted({c["line_count"] for c in cases}), [6, 8, 10, 12])
        for c in cases:
            got, want = tp.parse_trace(c["reply"], c["line_count"]), c["expected"]
            self.assertEqual(got.ok, want["ok"], (c["id"], got.status, got.detail))
            if want["ok"]:
                self.assertEqual([list(s) for s in got.states], want["states"], c["id"])
                self.assertEqual(list(got.answer), want["answer"], c["id"])
            else:
                self.assertIsNone(got.states, c["id"])
                self.assertEqual(got.status, want["reason"], c["id"])            # advisory, but they agree today
            if got.ok:
                self.assertEqual(got.step_states, got.states, c["id"])
            elif got.status not in ANSWER_LINE_FAILURES:
                self.assertIsNone(got.step_states, c["id"])


class Accepts(unittest.TestCase):
    def ok(self, text, states=None):
        r = tp.parse_trace(text, L)
        self.assertEqual(r.status, "ok", (r.detail, text[:200]))
        self.assertEqual(list(r.states), states or STATES)
        self.assertEqual(r.answer, (states or STATES)[-1])
        return r

    def test_the_plain_reply(self):
        self.ok(reply())

    def test_whitespace_anywhere(self):
        self.ok(reply([line(k, fmt="  1.{k}   =   [ {v} ]  ") for k in range(1, 25)], "  Answer :  1 =  [ 124 ,224,   324 ]  "))
        self.ok(reply([line(k, fmt="\t1.{k}=[{v}]\t") for k in range(1, 25)]).replace(", ", ","))
        self.ok(reply().replace("\n", "\r\n"))
        self.ok(reply().replace("\n", "\n\n\n"))

    def test_markdown_and_bullets_around_the_label(self):
        for fmt in ("**1.{k}** = [{v}]", "`1.{k} = [{v}]`", "- 1.{k} = [{v}]", "* 1.{k} = [{v}]", "> 1.{k} = [{v}]", "**1.{k} = [{v}]**",
                    "`1.{k}` = `[{v}]`"):
            self.ok(reply([line(k, fmt=fmt) for k in range(1, 25)]))

    def test_colon_instead_of_equals(self):
        self.ok(reply([line(k, fmt="1.{k}: [{v}]") for k in range(1, 25)], "Answer: 1: [124, 224, 324]"))

    def test_square_round_or_no_brackets(self):
        for fmt in ("1.{k} = ({v})", "1.{k} = {v}"):
            self.ok(reply([line(k, fmt=fmt) for k in range(1, 25)]))
        self.ok(reply(answer="Answer: 1 = (124, 224, 324)"))
        self.ok(reply(answer="Answer: 1 = 124, 224, 324"))

    def test_leading_zeros(self):
        self.ok(reply(lines_with(3, "1.3 = [0103, 0203, 00303]"), "Answer: 1 = [0124, 224, 324]"))

    def test_any_order_and_prose_around(self):
        lines = [line(k) for k in range(24, 0, -1)]
        self.ok(reply(["Here are the balances:"] + lines[:10] + ["(the house rule fired here)"] + lines[10:]))

    def test_trailing_prose_and_a_code_fence(self):
        self.ok("```\n" + reply() + "\n```\nI applied every rule in order.")
        self.ok("```text\n" + reply() + "\n```")

    def test_the_last_answer_line_wins(self):
        self.ok("Answer: 1 = [1, 2, 3] (draft)\n" + reply())
        self.ok(reply(answer="Answer: 1 = [9, 9, 9]\nAnswer: 1 = [124, 224, 324]"))

    def test_answer_line_variants(self):
        for a in ("answer: 1 = [124, 224, 324]", "ANSWER: 1 = [124, 224, 324]", "**Answer:** 1 = [124, 224, 324]", "**Answer**: 1 = [124, 224, 324]",
                  "Answer: [124, 224, 324]", "Answer 1 = [124, 224, 324]", "Answer [124, 224, 324]", "Answer: `1 = [124, 224, 324]`",
                  "- Answer: 1 = [124, 224, 324]"):
            self.ok(reply(answer=a))

    def test_a_wrong_value_parses_fine(self):
        wrong = (1, 2, 3)
        r = tp.parse_trace(reply(lines_with(5, line(5, wrong))), L)
        self.assertTrue(r.ok)
        self.assertEqual(r.states[4], wrong)


class Rejects(unittest.TestCase):
    def status(self, text, want):
        r = tp.parse_trace(text, L)
        self.assertFalse(r.ok)
        self.assertIsNone(r.states)
        self.assertEqual(r.status, want, r.detail)
        return r

    def test_a_missing_step_line(self):
        r = self.status(reply([line(k) for k in range(1, 25) if k != 7]), "missing_line")
        self.assertEqual(r.detail, "step line 1.7 missing")
        self.status("Answer: 1 = [124, 224, 324]", "missing_line")

    def test_a_duplicated_step_line_with_a_different_state(self):
        self.status(reply([line(k) for k in range(1, 25)] + [line(5, (9, 9, 9))]), "extra_line")

    def test_a_duplicated_step_line_with_the_same_state_is_read_once_d90_and_fails_under_the_original_rule(self):
        text = reply([line(k) for k in range(1, 25)] + [line(5)])
        self.assertEqual((tp.parse_trace(text, L).status, tp.parse_trace(text, L).states), ("ok", tuple(STATES)))
        self.assertEqual(tp.parse_trace(text, L, repeats="strict").status, "extra_line")

    def test_a_number_outside_1_to_24(self):
        self.status(reply([line(k) for k in range(1, 25)] + ["1.25 = [1, 2, 3]"]), "misnumbered")
        self.status(reply(["1.0 = [1, 2, 3]"] + [line(k) for k in range(1, 25)]), "misnumbered")
        self.status(reply([line(k) for k in range(1, 25)] + ["2.1 = [1, 2, 3]"]), "misnumbered")

    def test_not_exactly_l_values(self):
        self.status(reply(lines_with(4, "1.4 = [104, 204]")), "wrong_length")
        self.status(reply(lines_with(4, "1.4 = [104, 204, 304, 404]")), "wrong_length")
        self.status(reply(lines_with(4, "1.4 = [104, 2,004, 304]")), "wrong_length")         # a thousands separator splits
        self.status(reply(lines_with(4, "1.4 = []")), "wrong_length")
        self.status(reply(answer="Answer: 1 = [124, 224]"), "wrong_length")

    def test_a_value_that_is_not_an_integer(self):
        for bad in ("[104.0, 204, 304]", "[one hundred, 204, 304]", "[~104, 204, 304]", "[104, , 304]", "[104, 204, 304",
                    "[104, 204, 304] (house rule)", "[104, 204, 304]..", "[104, 204, 304].,", "[104, 204, 304] .", "[104, 204, 304];"):
            self.status(reply(lines_with(4, "1.4 = " + bad)), "non_integer")
        self.status(reply(answer="Answer: 1 = [124.0, 224, 324]"), "non_integer")

    def test_no_answer_line(self):
        self.status(reply(answer=None), "no_answer")
        self.status(reply(answer="Final balances: [124, 224, 324]"), "no_answer")

    def test_an_answer_that_differs_from_line_24(self):
        r = self.status(reply(answer="Answer: 1 = [124, 224, 325]"), "answer_mismatch")
        self.assertEqual(r.answer, (124, 224, 325))                                   # still read, for the final-answer view
        self.status(reply(lines_with(24, line(24, (1, 2, 3)))), "answer_mismatch")      # the key's answer, but line 24 differs
        self.status("Answer: 1 = [124, 224, 324]\n" + reply(answer="Answer: 1 = [9, 9, 9]"), "answer_mismatch")   # the LAST line wins

    def test_the_answer_is_read_even_when_the_trace_is_not_ok(self):
        r = tp.parse_trace(reply([line(k) for k in range(1, 25) if k != 7]), L)
        self.assertEqual((r.status, r.answer), ("missing_line", STATES[-1]))
        self.assertIsNone(tp.parse_trace(reply(answer="Answer: 1 = [1, 2]"), L).answer)

    def test_a_prose_line_is_never_a_step_line(self):
        self.assertTrue(tp.parse_trace(reply() + "\nStep 1.3 was the hard one.\n1.3 times the rent is a lot", L).ok)


class ProseAnswerLines(unittest.TestCase):
    """A line that starts with `answer` but does not go on like a state is prose: it never replaces the real Answer line."""

    def test_a_later_prose_answer_line_does_not_wipe_the_answer(self):
        for later in ("Answer check: every line verified.", "Answer verified above.", "## Answer", "**Answer**", "Answer:",
                      "Answer - see above", "Answers match the trace.", "answer key: as above"):
            r = tp.parse_trace(reply() + "\n" + later, L)
            self.assertEqual((r.status, r.answer), ("ok", STATES[-1]), later)
            self.assertEqual(tp.parse_final("Answer: 1 = [1, 2, 3]\n" + later, 3), ("ok", (1, 2, 3)), later)

    def test_lines_that_start_like_a_state_are_answer_lines(self):
        for a in ("Answer: 1 = [124, 224, 324]", "Answer: (124, 224, 324)", "Answer: 124, 224, 324", "Answer 1: [124, 224, 324]",
                  "Answer: `1 = [124, 224, 324]`"):
            self.assertEqual(tp.last_answer_text("x\n" + a) is not None, True, a)
        self.assertEqual(tp.parse_final("Answer: -5, 2, 3", 3), ("ok", (-5, 2, 3)))
        self.assertEqual(tp.parse_final("Answer: 1 = [1, 2, 3]\nAnswer: 1 = [1, 2]", 3), ("wrong_length", None))   # state-like: it counts

    def test_a_prose_answer_line_alone_is_no_answer(self):
        self.assertEqual(tp.parse_trace(reply(answer="Answer check: done"), L).status, "no_answer")
        self.assertEqual(tp.parse_final("Answer:\n1 = [1, 2, 3]", 3), ("no_answer", None))


class UnicodeWhitespace(unittest.TestCase):
    SPACES = ("\u00a0", "\u2003", "\u3000", "\u200b", "\ufeff", " \u00a0\u200b ")

    def test_trailing_and_leading_unicode_spaces_on_step_lines(self):
        for sp in self.SPACES:
            r = tp.parse_trace(reply([sp + line(k) + sp for k in range(1, 25)]), L)
            self.assertEqual(r.status, "ok", (repr(sp), r.detail))

    def test_trailing_and_leading_unicode_spaces_on_the_answer_line(self):
        for sp in self.SPACES:
            self.assertEqual(tp.parse_trace(reply(answer=sp + "Answer: 1 = [124, 224, 324]" + sp), L).status, "ok", repr(sp))
            self.assertEqual(tp.parse_final("Answer:" + sp + "1 =" + sp + "[1," + sp + "2, 3]" + sp, 3), ("ok", (1, 2, 3)), repr(sp))

    def test_a_zero_width_space_inside_a_number_splits_it(self):
        self.assertEqual(tp.parse_final("Answer: 1 = [1\u200b0, 2, 3]", 3)[0], "non_integer")


class UnderscoreMarkup(unittest.TestCase):
    def test_underscore_bold_and_italic_answer(self):
        for a in ("__Answer__: 1 = [124, 224, 324]", "_Answer_: 1 = [124, 224, 324]", "__Answer:__ 1 = [124, 224, 324]",
                  "_answer_ 1 = [124, 224, 324]"):
            self.assertEqual(tp.parse_trace(reply(answer=a), L).status, "ok", a)

    def test_underscore_markup_on_step_lines(self):
        for fmt in ("__1.{k}__ = [{v}]", "_1.{k}_ = [{v}]", "__1.{k} = [{v}]__"):
            self.assertEqual(tp.parse_trace(reply([line(k, fmt=fmt) for k in range(1, 25)]), L).status, "ok", fmt)


class TrailingPeriodOrComma(unittest.TestCase):
    """The one parse-rule addition after the review: one `.` or `,` right after the state is a harmless formatting variant."""

    def test_one_period_or_comma_right_after_a_step_state(self):
        for fmt in ("1.{k} = [{v}].", "1.{k} = [{v}],", "1.{k} = ({v}).", "1.{k} = {v}.", "**1.{k} = [{v}].**", "1.{k} = [{v}]. "):
            self.assertEqual(tp.parse_trace(reply([line(k, fmt=fmt) for k in range(1, 25)]), L).status, "ok", fmt)

    def test_one_period_or_comma_right_after_the_answer_state(self):
        for a in ("Answer: 1 = [124, 224, 324].", "Answer: 1 = [124, 224, 324],", "Answer: [124, 224, 324].", "Answer: 124, 224, 324."):
            self.assertEqual(tp.parse_trace(reply(answer=a), L).status, "ok", a)
        self.assertEqual(tp.parse_final("Answer: 1 = [1, 2, 3].", 3), ("ok", (1, 2, 3)))

    def test_anything_more_is_still_non_integer(self):
        for bad in ("[104, 204, 304]..", "[104, 204, 304].,", "[104, 204, 304] .", "[104, 204, 304]!", "[104, 204, 304]. Done",
                    "[104, 204, 304].)"):
            self.assertEqual(tp.parse_trace(reply(lines_with(4, "1.4 = " + bad)), L).status, "non_integer", bad)
        self.assertEqual(tp.parse_final("Answer: 1 = [1, 2, 3]..", 3), ("non_integer", None))


class Final(unittest.TestCase):
    def test_parse_final(self):
        self.assertEqual(tp.parse_final("Answer: 1 = [1, 2, 3]", 3), ("ok", (1, 2, 3)))
        self.assertEqual(tp.parse_final("nothing", 3), ("no_answer", None))
        self.assertEqual(tp.parse_final("Answer: 1 = [1, 2]", 3), ("wrong_length", None))
        self.assertEqual(tp.parse_final("Answer: 1 = [1, 2, x]", 3), ("non_integer", None))


class Pieces(unittest.TestCase):
    ANSWER = [(i, i + 1, i + 2) for i in range(1, 25)]

    def text(self, entries=None):
        entries = entries if entries is not None else {i: f"[{', '.join(map(str, a))}]" for i, a in enumerate(self.ANSWER, 1)}
        return "Answer: " + ", ".join(f"{i} = {v}" for i, v in entries.items())

    def test_today_s_labelled_line(self):
        r = tp.parse_pieces(self.text(), 24, 3)
        self.assertEqual((r.status, r.entries[24]), ("ok", (24, 25, 26)))
        r = tp.parse_pieces("draft\nAnswer: 1 = [0]\n**answer:** " + self.text()[8:], 24, 3)
        self.assertTrue(r.ok)

    def test_the_value_rules_apply_to_each_entry(self):
        e = {i: f"[{', '.join(map(str, a))}]" for i, a in enumerate(self.ANSWER, 1)}
        r = tp.parse_pieces(self.text({**e, 3: "[3.0, 4, 5]"}), 24, 3)
        self.assertEqual((r.status, r.bad, 3 in r.entries, len(r.entries)), ("non_integer", {3: "non_integer"}, False, 23))
        r = tp.parse_pieces(self.text({**e, 3: "[3, 4]"}), 24, 3)
        self.assertEqual((r.status, r.detail), ("wrong_length", "piece 3 has 2 balances, not 3"))
        r = tp.parse_pieces(self.text({i: v for i, v in e.items() if i != 9}), 24, 3)
        self.assertEqual((r.status, r.detail), ("missing_line", "piece 9 missing"))
        self.assertEqual(tp.parse_pieces(self.text({**e, 25: "[1, 2, 3]"}), 24, 3).status, "misnumbered")
        self.assertEqual(tp.parse_pieces("no answer here", 24, 3).status, "no_answer")

    def test_a_repeated_entry_keeps_its_last_value_as_before(self):
        r = tp.parse_pieces(self.text() + ", 2 = [7, 7, 7]", 24, 3)
        self.assertEqual((r.status, r.entries[2]), ("ok", (7, 7, 7)))

    def test_a_sign_is_kept_the_one_intended_change(self):
        e = {i: f"[{', '.join(map(str, a))}]" for i, a in enumerate(self.ANSWER, 1)}
        r = tp.parse_pieces(self.text({**e, 3: "[-3, 4, 5]"}), 24, 3)
        self.assertEqual((r.status, r.entries[3]), ("ok", (-3, 4, 5)))
        self.assertEqual(prompt_d31.parse_answer(self.text({**e, 3: "[-3, 4, 5]"}))[3], (3, 4, 5))       # the old reader dropped it


class PiecesFindTheAnswerLineAs1x24Does(unittest.TestCase):
    """Edith R3-a: parse_pieces finds the Answer line by the same definition as the 1x24 reader (last_answer_text)."""
    RIGHT = "Answer: 1 = [1, 2, 3], 2 = [4, 5, 6]"
    READ = ("**Answer**: 1 = [1, 2, 3], 2 = [4, 5, 6]",
            "+ Answer: 1 = [1, 2, 3], 2 = [4, 5, 6]",
            "Answer 1 = [1, 2, 3], 2 = [4, 5, 6]",
            "__Answer__: 1 = [1, 2, 3], 2 = [4, 5, 6]",
            RIGHT + "\nAnswer check: done",                           # a prose line never replaces the real one
            RIGHT + "\n## Answer",
            RIGHT + "\nAnswer: see above",
            "**answer:** 1 = [1, 2, 3], 2 = [4, 5, 6]",
            "draft\nAnswer: 1 = [9, 9, 9]\n" + RIGHT,
            "  " + RIGHT + "  \n\n")

    def test_every_case_reads_the_right_line(self):
        for text in self.READ:
            r = tp.parse_pieces(text, 2, 3)
            self.assertEqual((r.status, r.entries), ("ok", {1: (1, 2, 3), 2: (4, 5, 6)}), text)

    def test_the_same_line_as_the_1x24_reader(self):
        for text in self.READ:
            self.assertEqual(tp.last_answer_text(text).strip(" *_`:"), "1 = [1, 2, 3], 2 = [4, 5, 6]", text)

    def test_no_answer_line(self):
        self.assertEqual(tp.parse_pieces("Answer check: done", 2, 3).status, "no_answer")


class StepStatesForTheSlipView(unittest.TestCase):
    """Edith F25-1: `step_states` keeps the 24 states when only the Answer line fails, for the fairness slip view. `status` and `states`
    are unchanged (the official score reads those)."""

    def test_set_when_only_the_answer_line_fails(self):
        for answer, status in (("Answer: 1 = [9, 9, 9]", "answer_mismatch"), (None, "no_answer"), ("Answer: 1 = [1, 2]", "wrong_length"),
                               ("Answer: 1 = [1, x, 3]", "non_integer")):
            r = tp.parse_trace(reply(answer=answer), L)
            self.assertEqual((r.status, r.states, r.step_states), (status, None, tuple(STATES)), answer)

    def test_none_when_a_step_line_is_missing_or_unreadable(self):
        for text, status in ((reply([line(k) for k in range(1, 25) if k != 7]), "missing_line"),
                             (reply(lines_with(7, "1.7 = [1, 2.5, 3]")), "non_integer"),
                             (reply(lines_with(7, "1.7 = [1, 2]")), "wrong_length"),
                             (reply() + "\n1.25 = [1, 2, 3]", "misnumbered"),
                             (reply() + "\n1.3 = [9, 9, 9]", "extra_line"),
                             (reply(lines_with(7, "1.7 = [1, 2]"), answer="Answer: 1 = [9, 9, 9]"), "wrong_length")):
            r = tp.parse_trace(text, L)
            self.assertEqual((r.status, r.states, r.step_states), (status, None, None), status)

    def test_equal_to_states_when_ok(self):
        r = tp.parse_trace(reply(), L)
        self.assertEqual((r.status, r.step_states), ("ok", r.states))


class LabelWordSequenceOrPiece(unittest.TestCase):
    """Karen, 2026-10-11: the word `Sequence` or `Piece` (any case, then whitespace) may stand before an entry number, at both shapes. The
    prompts call each item a "sequence"; "piece" is harmless. Nothing else changes."""

    def test_both_words_at_1x24(self):
        for a in ("Answer: Sequence 1 = [124, 224, 324]", "Answer: Piece 1 = [124, 224, 324]", "Answer: sequence 1 = [124, 224, 324]",
                  "**Answer**: PIECE 1: [124, 224, 324]", "Answer Sequence 1 = (124, 224, 324).", "Answer: `Sequence 1 = [124, 224, 324]`"):
            r = tp.parse_trace(reply(answer=a), L)
            self.assertEqual((r.status, r.answer), ("ok", STATES[-1]), a)
            self.assertEqual(tp.parse_final(a, 3), ("ok", (124, 224, 324)), a)

    def test_both_words_at_24x1(self):
        for text in ("Answer: Sequence 1 = [1, 2, 3], Sequence 2 = [4, 5, 6]", "Answer: Piece 1 = [1, 2, 3], Piece 2 = [4, 5, 6]",
                     "**Answer**: sequence 1 = [1, 2, 3], piece 2 = [4, 5, 6]", "Answer: 1 = [1, 2, 3], Sequence 2 = [4, 5, 6]"):
            r = tp.parse_pieces(text, 2, 3)
            self.assertEqual((r.status, r.entries), ("ok", {1: (1, 2, 3), 2: (4, 5, 6)}), text)

    def test_the_value_rules_still_apply(self):
        self.assertEqual(tp.parse_final("Answer: Sequence 1 = [1, 2]", 3), ("wrong_length", None))
        self.assertEqual(tp.parse_pieces("Answer: Sequence 1 = [1, 2.0, 3], Sequence 2 = [4, 5, 6]", 2, 3).status, "non_integer")
        self.assertEqual(tp.parse_pieces("Answer: Piece 1 = [1, 2, 3]", 2, 3).status, "missing_line")

    def test_answer_check_stays_prose(self):
        self.assertEqual(tp.parse_trace(reply(answer="Answer check: done"), L).status, "no_answer")
        self.assertEqual(tp.parse_trace(reply() + "\nAnswer check: done", L).status, "ok")
        self.assertEqual(tp.parse_pieces("Answer check: done", 2, 3).status, "no_answer")

    def test_markup_around_the_label_and_a_colon(self):
        # Karen's r2 cases: markup around the label word and number, at both shapes; `:` after the number at 24x1 too
        for a in ("Answer: **Sequence 1** = [124, 224, 324]", "**Answer:** **Piece 1** = [124, 224, 324]", "Answer: **1** = [124, 224, 324]",
                  "Answer: Sequence 1: [124, 224, 324]", "Answer: _Piece 1_: [124, 224, 324]"):
            self.assertEqual(tp.parse_trace(reply(answer=a), L).status, "ok", a)
            self.assertEqual(tp.parse_final(a, 3), ("ok", (124, 224, 324)), a)
        for text in ("Answer: **Sequence 1** = [1, 2, 3], **Sequence 2** = [4, 5, 6]", "Answer: Sequence 1: [1, 2, 3], Sequence 2: [4, 5, 6]",
                     "Answer: 1: [1, 2, 3], 2: [4, 5, 6]", "Answer: **1** = [1, 2, 3], `2` = [4, 5, 6]"):
            r = tp.parse_pieces(text, 2, 3)
            self.assertEqual((r.status, r.entries), ("ok", {1: (1, 2, 3), 2: (4, 5, 6)}), text)

    def test_a_labelled_wrong_number_fails_like_the_bare_form(self):
        # Karen's r2 case 3: `Sequence 2 = [...]` on a one-sequence Answer line gives the same status as `2 = [...]`
        bare = tp.parse_trace(reply(answer="Answer: 2 = [124, 224, 324]"), L).status
        self.assertEqual(tp.parse_trace(reply(answer="Answer: Sequence 2 = [124, 224, 324]"), L).status, bare)
        self.assertEqual(bare, "non_integer")

    def test_a_plural_or_other_word_is_not_a_label(self):
        for a in ("Answer: Sequences 1 = [124, 224, 324]", "Answer: Pieces 1 = [124, 224, 324]", "Answer: Step 1 = [124, 224, 324]",
                  "Answer: Sequence1 = [124, 224, 324]"):
            self.assertEqual(tp.parse_trace(reply(answer=a), L).status, "no_answer", a)
        self.assertEqual(tp.parse_pieces("Answer: Sequences 1 = [1, 2, 3], Sequences 2 = [4, 5, 6]", 2, 3).status, "no_answer")
