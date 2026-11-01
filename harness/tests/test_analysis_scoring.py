import gzip
import hashlib
import json
import unittest
from pathlib import Path

from harness.analysis import scoring
from harness.taskgen import ledger, ledger_check
from harness.taskgen.rng import derive_seed

_CACHE = {}


def puzzle(preset, width, depth):
    key = (preset, width, depth)
    if key not in _CACHE:
        _CACHE[key] = ledger.generate(derive_seed("test-scoring", preset), width, depth, ledger.SETTINGS[preset])
    return _CACHE[key]


def chain_reply(p, overrides=None):
    """The key's chain reply; `overrides` {step: balances} replaces step lines. The Answer line repeats the written line 24 (D-76: an Answer
    line that differs from line 24 makes the reply unplaceable)."""
    overrides = overrides or {}
    states = [overrides.get(k, st) for k, st in enumerate(p.chains[0].states, 1)]
    lines = [f"1.{k} = {ledger.fmt(st)}" for k, st in enumerate(states, 1)]
    return "\n".join(lines + [f"Answer: 1 = {ledger.fmt(states[-1])}"])


def reply_with_one_slip(p, k, state):
    """A chain reply whose step k is `state` and whose later steps follow correctly from it (so exactly one local slip, if `state` is wrong)."""
    rules = scoring._Rules(p)
    lines, prev = {k: list(state)}, list(state)
    for j in range(k + 1, 25):
        prev = list(rules.composite[p.chains[0].names[j - 1]](list(prev)))
        lines[j] = prev
    return chain_reply(p, lines)


def previous_of(p, k):
    return p.chains[0].start if k == 1 else p.chains[0].states[k - 2]


class Views(unittest.TestCase):
    ROWS = [{"base_id": "b1", "correct": True, "kind": "answered"}, {"base_id": "b1", "correct": False, "kind": "refusal"},
            {"base_id": "b2", "correct": True, "kind": "answered"},
            {"base_id": "b2", "correct": False, "kind": "truncated", "stop_reason": "max_tokens"},
            {"base_id": "b3", "correct": False, "kind": "refusal"}]

    def test_as_deployed_counts_failures_as_wrong(self):
        self.assertEqual(scoring.arm_scores(self.ROWS), {"b1": 50.0, "b2": 50.0, "b3": 0.0})

    def test_refusals_and_truncations_can_be_left_out(self):
        self.assertEqual(scoring.arm_scores(self.ROWS, "refusals_out"), {"b1": 100.0, "b2": 50.0})
        self.assertEqual(scoring.arm_scores(self.ROWS, "truncations_out"), {"b1": 50.0, "b2": 100.0, "b3": 0.0})
        with self.assertRaises(ValueError):
            scoring.arm_scores(self.ROWS, "nope")

    def test_paired_differences_pair_by_base_and_are_ordered(self):
        self.assertEqual(scoring.paired_differences({"b2": 100.0, "b1": 50.0, "b9": 0.0}, {"b1": 0.0, "b2": 100.0}), [50.0, 0.0])

    def test_e3_is_the_product_of_per_step_accuracies(self):
        runs = {"b1": [[True, True, True], [True, False, True], [True, True, True], [True, True, False]]}
        self.assertAlmostEqual(scoring.e3_scores(runs)["b1"], 100.0 * 1.0 * 0.75 * 0.75)
        with self.assertRaises(ValueError):
            scoring.e3_scores({"b": [[True], [True, False]]})


class BlocksAndShapes(unittest.TestCase):
    def test_refusals_out_drops_a_policy_error_but_not_an_overload(self):
        rows = [{"base_id": "b", "correct": True, "kind": "answered"},
                {"base_id": "b", "correct": False, "kind": "error", "error": {"type": "x", "message": "Blocked by a safety classifier"}},
                {"base_id": "b", "correct": False, "kind": "error", "error": {"type": "overloaded_error", "message": "try later"}}]
        self.assertAlmostEqual(scoring.arm_scores(rows, "refusals_out")["b"], 50.0)

    def test_a_step_line_with_the_wrong_number_of_balances_makes_the_try_unplaceable(self):
        p = puzzle("l14", 1, 24)
        lines = chain_reply(p).splitlines()
        lines[3] = "1.4 = [1, 2, 3]"
        res = scoring.local_steps("\n".join(lines), p)
        self.assertIn("has 3 balances", res["unplaceable"])
        self.assertEqual(res["steps"], [])

    def test_a_piece_with_the_wrong_number_of_balances_is_unplaceable(self):
        p = puzzle("l14", 24, 1)
        self.assertIn("balances", scoring.local_steps(p.answer_line.replace("2 = [", "2 = [1, ", 1), p)["unplaceable"])


class StepLines(unittest.TestCase):
    def test_all_step_lines_right(self):
        p = puzzle("l14", 1, 24)
        wrong = [p.chains[0].states[6][0] + 1] + list(p.chains[0].states[6][1:])
        self.assertTrue(scoring.all_step_lines_right(chain_reply(p), p))
        self.assertFalse(scoring.all_step_lines_right(chain_reply(p, {7: wrong}), p))
        self.assertFalse(scoring.all_step_lines_right("\n".join(chain_reply(p).splitlines()[1:]), p))      # a line is missing
        self.assertFalse(scoring.all_step_lines_right(chain_reply(p) + "\n1.25 = [1, 2]", p))             # impossible numbering: wrong (D-76)
        self.assertTrue(scoring.all_step_lines_right(chain_reply(p).replace(" = ", ": "), p))              # an accepted variant
        last = chain_reply(p).splitlines()
        self.assertFalse(scoring.all_step_lines_right("\n".join(last[:-1] + [p.answer_line.replace("[", "[9", 1)]), p))  # Answer != line 24

    def test_all_step_lines_right_for_pieces_is_the_whole_answer(self):
        p = puzzle("l14", 24, 1)
        self.assertTrue(scoring.all_step_lines_right(p.answer_line, p))
        self.assertFalse(scoring.all_step_lines_right(p.answer_line.replace("1 = [", "1 = [9", 1), p))


class LocalSlips(unittest.TestCase):
    def test_a_clean_chain_has_24_steps_checked_and_no_slip(self):
        p = puzzle("l14", 1, 24)
        res = scoring.local_steps(chain_reply(p), p)
        self.assertEqual((res["unplaceable"], len(res["steps"]), [s["slipped"] for s in res["steps"]].count(True)), (None, 24, 0))

    def test_a_wrong_state_carried_forward_is_counted_once(self):
        p = puzzle("l14", 1, 24)
        wrong = [p.chains[0].states[4][0] + 1] + list(p.chains[0].states[4][1:])
        # the model gets step 5 wrong and then applies every later rule correctly to its own wrong state
        rules = scoring._Rules(p)
        lines, prev = {}, p.chains[0].states[3]
        lines[5] = wrong
        prev = wrong
        for k in range(6, 25):
            nxt = list(rules.composite[p.chains[0].names[k - 1]](list(prev)))
            lines[k] = nxt
            prev = nxt
        reply = chain_reply(p, lines)
        res = scoring.local_steps(reply, p)
        self.assertEqual([s["step"] for s in res["steps"] if s["slipped"]], [5])
        first = scoring.first_slip_steps(reply, p)
        self.assertEqual([s["step"] for s in first["steps"]], [1, 2, 3, 4, 5])
        self.assertEqual(first["signature"][:2], (1, 5))

    def test_the_slip_carries_the_rule_kind_and_class(self):
        p = puzzle("l14", 1, 24)
        wrong = [p.chains[0].states[4][0] + 1] + list(p.chains[0].states[4][1:])
        res = scoring.local_steps(chain_reply(p, {5: wrong}), p)
        row = [s for s in res["steps"] if s["slipped"]][0]
        kind = [k for l, k, _ in p.rulebook if l == p.chains[0].names[4]][0]
        self.assertEqual((row["step"], row["kind"], row["blame"]), (5, kind, "kind"))
        self.assertEqual(row["cls"], scoring._step_class(kind))

    def test_classes_follow_the_steps_own_kind_only(self):
        self.assertEqual([scoring._step_class(k) for k in ("repick2", "sweep", "avg_donors", "rank_move", "pay")], ["T", "T", "G", "G", "other"])

    def test_unplaceable_tries(self):
        p = puzzle("l14", 1, 24)
        lines = chain_reply(p).splitlines()
        self.assertEqual(scoring.local_steps("\n".join(lines[:3] + lines[4:]), p)["unplaceable"], "step line 1.4 missing")
        self.assertEqual(scoring.local_steps("\n".join(lines[:-1] + ["Answer: 1 = [1, 2, 3]"]), p)["unplaceable"],
                         "the Answer line breaks the value rules (wrong_length)")
        wrong_final = [p.chains[0].states[-1][0] + 1] + list(p.chains[0].states[-1][1:])
        self.assertEqual(scoring.local_steps("\n".join(lines[:-1] + [f"Answer: 1 = {ledger.fmt(wrong_final)}"]), p)["unplaceable"],
                         "the Answer line differs from line 1.24")
        self.assertEqual(scoring.local_steps("hello", p)["unplaceable"], "step line 1.1 missing")
        self.assertEqual(scoring.local_steps(chain_reply(p) + "\n1.25 = [1]", p)["unplaceable"], "step line 1.25 is outside 1.1 to 1.24")
        self.assertIsNone(scoring.local_steps(chain_reply(p).replace("1.3 = [", "**1.3** = [", 1), p)["unplaceable"])   # an accepted variant

    def test_house_rule_missed_is_blamed_first(self):
        p = puzzle("l14", 1, 24)
        rules = scoring._Rules(p)
        for k, label in enumerate(p.chains[0].names, 1):
            plain = rules.bare[label](list(previous_of(p, k)))
            if tuple(rules.house.after(plain)) != tuple(plain):
                res = scoring.local_steps(chain_reply(p, {k: plain}), p)
                row = res["steps"][k - 1]
                self.assertEqual((row["blame"], row["house_should_act"]), ("house_missed", True))
                return
        self.fail("the house rule never acted on this puzzle")

    def test_house_rule_misapplied_when_it_should_not_have_acted(self):
        p = puzzle("l14", 1, 24)
        rules = scoring._Rules(p)
        for k, label in enumerate(p.chains[0].names, 1):
            plain = rules.bare[label](list(previous_of(p, k)))
            forced = scoring._forced_house(rules.house, plain)
            if tuple(rules.house.after(plain)) == tuple(plain) and forced != tuple(plain):
                res = scoring.local_steps(chain_reply(p, {k: list(forced)}), p)
                self.assertEqual(res["steps"][k - 1]["blame"], "house_misapplied")
                return
        self.skipTest("no step where forcing the house move changes the state")

    def test_decoy_confusion_is_named_for_a_step_that_has_a_twin(self):
        p = puzzle("l15", 1, 24)
        rules = scoring._Rules(p)
        for k, label in enumerate(p.chains[0].names, 1):
            twin = scoring._decoy_twin(p, label)
            if twin is None:
                continue
            alt = tuple(rules.bare[twin](list(previous_of(p, k))))
            wrong = tuple(rules.house.after(alt)) if rules.house else alt
            plain = tuple(rules.bare[label](list(previous_of(p, k))))
            if wrong == tuple(p.chains[0].states[k - 1]) or wrong == plain or alt == plain:
                continue
            res = scoring.local_steps(chain_reply(p, {k: list(wrong)}), p)
            self.assertEqual(res["steps"][k - 1]["blame"], "decoy_confusion")
            return
        self.skipTest("no step with a usable twin in this puzzle")

    def test_pieces_every_piece_is_checked_from_its_given_start(self):
        p = puzzle("l14", 24, 1)
        bad = p.answer_line.replace("3 = [", "3 = [9", 1)
        res = scoring.local_steps(bad, p)
        self.assertEqual(len(res["steps"]), 24)
        self.assertEqual([s["sequence"] for s in res["steps"] if s["slipped"]], [3])
        self.assertEqual(scoring.local_steps("nothing", p)["unplaceable"], "no answer line")

    def test_slip_table_counts_kinds_house_and_unplaceable(self):
        p = puzzle("l14", 1, 24)
        rules = scoring._Rules(p)
        wrong = [p.chains[0].states[4][0] + 1] + list(p.chains[0].states[4][1:])
        k_house = next(k for k, lab in enumerate(p.chains[0].names, 1)
                       if tuple(rules.house.after(rules.bare[lab](list(previous_of(p, k))))) != tuple(rules.bare[lab](list(previous_of(p, k)))))
        plain = rules.bare[p.chains[0].names[k_house - 1]](list(previous_of(p, k_house)))
        placed = [("haiku", scoring.local_steps(reply_with_one_slip(p, 5, wrong), p)),
                  ("haiku", scoring.local_steps(reply_with_one_slip(p, k_house, plain), p)),
                  ("haiku", scoring.local_steps(chain_reply(p), p)),
                  ("haiku", scoring.local_steps("junk", p))]
        t = scoring.slip_table(placed)
        self.assertEqual(t[("haiku", "unplaceable")]["tries"], 1)
        classes = {k[1]: v for k, v in t.items() if k[1].startswith("class ")}
        self.assertEqual(sum(v["at_risk"] for v in classes.values()), 72)
        self.assertEqual(sum(v["slips"] for v in classes.values()), 1)      # the step-5 slip only: the house slip is not a kind slip
        h = t[("haiku", "house")]
        self.assertEqual((h["steps_checked"], h["missed"], h["house_slips"]), (72, 1, 1))
        self.assertGreaterEqual(h["steps_house_fires"], 3)


KEY = [(100 + k, 200 + k, 300 + k) for k in range(1, 25)]       # a made-up 1x24 key, three balances per state


def trace_text(over=None, answer=None):
    """A 1x24 reply in the plain format: KEY with `over` {step: state} swapped in; the Answer line repeats line 24 unless `answer` is given."""
    over = over or {}
    states = [over.get(k, st) for k, st in enumerate(KEY, 1)]
    ans = states[-1] if answer is None else answer
    return "\n".join([f"1.{k} = {ledger.fmt(st)}" for k, st in enumerate(states, 1)] + [f"Answer: 1 = {ledger.fmt(ans)}"])


def graded(reply, setup="haiku-med", kind="answered", base="b1", answer_only=False):
    """A scored 1x24 row as the main run writes it (`grade_1x24`)."""
    r = {"base_id": base, "setup": setup, "shape": "1x24", "kind": kind}
    if answer_only:
        r["answer_only"] = True
    r.update(scoring.grade_1x24(reply, KEY, 3, kind=kind, answer_only=answer_only))
    return r


MIDDLE_WRONG = {12: (1, 2, 3), 13: (4, 5, 6)}                        # two middle lines wrong, the rest (and the final) right


class D76Scores(unittest.TestCase):
    """Ruling D-76: official = all 24 step lines right AND the Answer line equals line 24; the final answer is the secondary view."""

    def test_final_answer_right_but_a_middle_line_wrong_is_wrong_officially_and_right_on_the_final_view(self):
        r = graded(trace_text(MIDDLE_WRONG))
        self.assertEqual((r["format_status"], r["slip_type"]), ("ok", "absorbed"))
        self.assertFalse(scoring.row_correct(r, "official"))
        self.assertTrue(scoring.row_correct(r, "final"))
        self.assertFalse(scoring.row_correct(r, "copy_forgiven"))
        self.assertEqual(scoring.arm_scores([r], score="official"), {"b1": 0.0})
        self.assertEqual(scoring.arm_scores([r], score="final"), {"b1": 100.0})

    def test_one_wrong_middle_line_alone_is_also_wrong_officially(self):
        r = graded(trace_text({12: (1, 2, 3)}))                                  # a copy slip: wrong officially, forgiven only in the sensitivity
        self.assertEqual((r["slip_type"], r["copy_line"]), ("copy", 12))
        self.assertEqual([scoring.row_correct(r, s) for s in scoring.SCORES], [False, True, True, False])

    def test_the_right_trace_is_right_in_every_score(self):
        r = graded(trace_text())
        self.assertEqual([scoring.row_correct(r, s) for s in scoring.SCORES], [True, True, True, True])

    def test_an_answer_line_that_differs_from_line_24_is_unplaceable_and_wrong(self):
        r = graded(trace_text({24: (9, 9, 9)}, answer=KEY[-1]))              # the Answer line is the key's final, line 24 is not
        self.assertEqual(r["format_status"], "answer_mismatch")
        self.assertIsNone(r["trace_key"])
        self.assertFalse(scoring.row_correct(r, "official"))
        self.assertTrue(scoring.row_correct(r, "final"))                        # the secondary view reads the Answer line only

    def test_a_format_failure_or_a_non_answer_is_wrong(self):
        lines = trace_text().splitlines()
        for reply in ("\n".join(lines[:5] + lines[6:]), trace_text().replace("1.7 = [", "1.7 = [2,"), "no lines at all"):
            r = graded(reply)
            self.assertNotEqual(r["format_status"], "ok")
            self.assertFalse(scoring.row_correct(r, "official"))
        r = graded(None, kind="refusal")
        self.assertEqual(r["format_status"], "refusal")
        self.assertEqual([scoring.row_correct(r, s) for s in scoring.SCORES], [False, False, False, False])

    def test_a_row_marked_right_with_a_bad_format_is_refused(self):
        r = dict(graded(trace_text({24: (9, 9, 9)}, answer=KEY[-1])), correct=True)
        with self.assertRaises(ValueError):
            scoring.row_correct(r)
        with self.assertRaises(ValueError):
            scoring.row_correct({"base_id": "b", "setup": "opus-med", "shape": "1x24", "correct": True})   # no D-76 fields

    def test_vote_keys_are_whole_traces_and_an_unplaceable_try_votes_for_nothing(self):
        right, mid = graded(trace_text()), graded(trace_text(MIDDLE_WRONG))
        other_mid = graded(trace_text({12: (7, 7, 7), 13: (4, 5, 6)}))
        self.assertEqual(scoring.vote_key(right, "final"), scoring.vote_key(mid, "final"))          # the same final answer
        self.assertNotEqual(scoring.vote_key(right), scoring.vote_key(mid))                           # but different traces
        self.assertNotEqual(scoring.vote_key(mid), scoring.vote_key(other_mid))                       # differ in one middle line only
        self.assertEqual(scoring.vote_key(right), scoring.trace_key(KEY))
        bad = graded(trace_text({24: (9, 9, 9)}, answer=KEY[-1]))
        self.assertIsNone(scoring.vote_key(bad))
        self.assertIsNone(scoring.vote_key(bad, "copy_forgiven"))
        self.assertEqual(scoring.vote_key(bad, "final"), scoring.state_key(KEY[-1]))
        self.assertIsNone(scoring.vote_key(graded(None, kind="truncated"), "final"))

    def test_answer_only_rows_are_scored_by_the_final_answer_in_every_score(self):
        mid = graded("Some working.\nAnswer: 1 = " + ledger.fmt(KEY[-1]), answer_only=True)
        wrong = graded("Answer: [1, 2, 3]", answer_only=True)
        self.assertEqual([scoring.row_correct(mid, s) for s in scoring.SCORES], [True, True, True, True])
        self.assertEqual([scoring.row_correct(wrong, s) for s in scoring.SCORES], [False, False, False, False])
        self.assertEqual(scoring.vote_key(mid), scoring.state_key(KEY[-1]))
        self.assertFalse(scoring.is_trace_row(mid))

    def test_a_mix_of_answer_only_and_step_line_rows_is_refused(self):
        aonly = graded("Answer: 1 = " + ledger.fmt(KEY[-1]), setup="opus-med", answer_only=True)
        steps = graded(trace_text())
        e3 = {"base_id": "b1", "setup": "e3", "shape": "1x24", "kind": "answered", "correct": True, "answer_key": "x"}
        scoring.check_answer_only([aonly, e3])                                 # E3 is outside the switch
        scoring.check_answer_only([steps, e3])
        with self.assertRaises(ValueError):
            scoring.check_answer_only([aonly, steps])
        with self.assertRaises(ValueError):
            scoring.rates_1x24([aonly, steps])
        for fn in (scoring.arm_scores, scoring.format_compliance):                # every set-level scorer refuses it, called directly
            with self.assertRaises(ValueError, msg=fn.__name__):
                fn([aonly, steps])
        self.assertEqual(scoring.row_correct(aonly), True)                     # one row alone: the mix check is set-level
        self.assertEqual(scoring.arm_scores([steps, e3]), {"b1": 100.0})

    def test_the_answer_only_flag_is_strict(self):
        steps = graded(trace_text())
        for ok_flag, want in ((True, False), (False, True), (None, True)):
            self.assertEqual(scoring.is_trace_row(dict(steps, answer_only=ok_flag)), want, ok_flag)
        self.assertTrue(scoring.is_trace_row({k: v for k, v in steps.items() if k != "answer_only"}))   # missing: False
        for bad in ("False", "True", "false", 0, 1, "", "no"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                scoring.is_trace_row(dict(steps, answer_only=bad))
            with self.assertRaises(ValueError, msg=repr(bad)):
                scoring.check_answer_only([steps, dict(steps, answer_only=bad)])
            with self.assertRaises(ValueError, msg=repr(bad)):
                scoring.check_answer_only([dict(steps, setup="e3", answer_only=bad)])                   # checked on every row
            with self.assertRaises(ValueError, msg=repr(bad)):
                scoring.grade_1x24(trace_text(), KEY, 3, answer_only=bad)
        self.assertIs(scoring.grade_1x24(trace_text(), KEY, 3)["answer_only"], False)

    def test_format_compliance_per_model(self):
        rows = [graded(trace_text(), "haiku-med") for _ in range(3)] + [graded("junk", "haiku-med"), graded(None, "haiku-med", "refusal")]
        rows += [graded(trace_text(MIDDLE_WRONG), "opus-med"), graded(trace_text(), "opus-med")]
        fc = scoring.format_compliance(rows)
        self.assertEqual(set(fc), {("haiku-med",), ("opus-med",)})
        h = fc[("haiku-med",)]
        self.assertEqual((h["tries"], h["answered"], h["format_ok"]), (5, 4, 3))
        self.assertAlmostEqual(h["format_compliance"], 0.75)                    # over answered tries
        self.assertAlmostEqual(h["format_compliance_all_tries"], 0.6)           # a refusal counts as not ok here
        self.assertEqual(h["status_counts"], {"missing_line": 1, "ok": 3, "refusal": 1})
        self.assertAlmostEqual(fc[("opus-med",)]["format_compliance"], 1.0)     # a wrong trace in a good format is compliant
        rt = scoring.rates_1x24(rows)
        self.assertAlmostEqual(rt["haiku-med"]["format_compliance"], 0.75)
        self.assertAlmostEqual(rt["opus-med"]["absorption"], 0.5)               # final right, trace wrong: the measured gap


class Repeats(unittest.TestCase):
    def test_pairwise_agreement(self):
        r = scoring.pairwise_agreement(["a", "a", "b"])
        self.assertEqual((r["pairs"], r["agree"]), (3, 1))
        self.assertAlmostEqual(r["top_share"], 2 / 3)
        self.assertEqual(scoring.pairwise_agreement(["a"])["pairs"], 0)

    def test_pooled_share_adds_pairs_across_puzzles(self):
        r = scoring.pooled_repeat_share({"p1": ["a", "a"], "p2": ["x", "y", "x"], "p3": ["z"]})
        self.assertEqual((r["pairs"], r["agree"], r["puzzles"]), (4, 2, 2))
        self.assertAlmostEqual(r["share"], 0.5)


def with_answer(reply, answer):
    """`reply` with its Answer line replaced by `answer` (None drops it)."""
    lines = reply.splitlines()[:-1]
    return "\n".join(lines + ([answer] if answer is not None else []))


class AnswerLineOnlyFailures(unittest.TestCase):
    """Edith F25-1 and the plan's "Fairness check", item 4: a try is unplaceable only if its step lines are missing or unreadable, or if
    every step is right but the Answer line is wrong. A slip in readable step lines is placed, whatever the Answer line says."""

    def setUp(self):
        self.p = puzzle("l14", 1, 24)
        self.wrong = [self.p.chains[0].states[4][0] + 1] + list(self.p.chains[0].states[4][1:])
        self.slipped = reply_with_one_slip(self.p, 5, self.wrong)        # one slip at step 5, carried forward correctly

    def test_a_mid_chain_slip_with_a_mismatched_answer_line_is_placed_at_its_first_wrong_step(self):
        p = self.p
        for answer, status in ((p.answer_line, "answer_mismatch"),                       # the key's final, not its own line 24
                               (None, "no_answer"), ("Answer: 1 = [1, 2]", "wrong_length"), ("Answer: 1 = [x]", "non_integer")):
            reply = with_answer(self.slipped, answer)
            res = scoring.local_steps(reply, p)
            self.assertEqual((res["unplaceable"], res["status"], len(res["steps"])), (None, status, 24), answer)
            slips = [s for s in res["steps"] if s["slipped"]]
            kind = [k for lab, k, _ in p.rulebook if lab == p.chains[0].names[4]][0]
            self.assertEqual([(s["step"], s["kind"], s["blame"]) for s in slips], [(5, kind, "kind")], answer)
            first = scoring.first_slip_steps(reply, p)
            self.assertEqual((first["unplaceable"], first["signature"][:2], len(first["steps"])), (None, (1, 5), 5), answer)
            self.assertFalse(scoring.grade_1x24(reply, p.chains[0].states, p.params.lines)["correct"])   # still wrong officially
        t = scoring.slip_table([("haiku", scoring.local_steps(with_answer(self.slipped, p.answer_line), p))])
        self.assertEqual(t[("haiku", kind)]["slips"], 1)
        self.assertNotIn(("haiku", "unplaceable"), t)

    def test_every_step_right_with_a_wrong_answer_line_is_unplaceable(self):
        p = self.p
        wrong_final = [p.chains[0].states[-1][0] + 1] + list(p.chains[0].states[-1][1:])
        for answer, status in ((f"Answer: 1 = {ledger.fmt(wrong_final)}", "answer_mismatch"), (None, "no_answer"),
                               ("Answer: 1 = [1, 2]", "wrong_length")):
            res = scoring.local_steps(with_answer(chain_reply(p), answer), p)
            self.assertEqual((res["status"], res["steps"]), (status, []), answer)
            self.assertIsNotNone(res["unplaceable"], answer)
            self.assertIsNotNone(scoring.first_slip_steps(with_answer(chain_reply(p), answer), p)["unplaceable"], answer)

    def test_an_unreadable_step_line_is_unplaceable_even_with_a_slip(self):
        p = self.p
        for answer in (None, p.answer_line):
            lines = with_answer(self.slipped, answer).splitlines()
            for bad, status in (("1.9 = [1, 2.5]", "non_integer"), ("1.9 = [1, 2]", "wrong_length")):
                res = scoring.local_steps("\n".join(lines[:8] + [bad] + lines[9:]), p)
                self.assertEqual((res["status"], res["steps"]), (status, []), (bad, answer))
                self.assertIsNotNone(res["unplaceable"])
            res = scoring.local_steps("\n".join(lines[:8] + lines[9:]), p)
            self.assertEqual((res["unplaceable"], res["status"]), ("step line 1.9 missing", "missing_line"))


PARSE_CASES = Path(__file__).resolve().parents[2] / "research" / "fixtures" / "sim-main-v2" / "parse_cases.jsonl.gz"
# sha256 of the grade_1x24 rows below, computed with the code BEFORE the F25-1 change (commit 4406c55): the official D-76 score, and
# every other field grade_1x24 writes, must not move when the slip view starts reading the step lines of Answer-line-only failures.
GRADE_1X24_DIGEST = "49e0564ab4442eddf76baddd7e91e375ae191cb0977054ccd19816e2cd91e6fe"


@unittest.skipUnless(PARSE_CASES.is_file(), "research/fixtures/sim-main-v2 is not in this tree")
class OfficialScoreUnchanged(unittest.TestCase):
    """grade_1x24 on Karen's 148 v2 replies, each against two keys (the first ok case's states for its line count, and that key with
    line 12 changed), is byte-identical to its output before F25-1, and right only if the status is ok and every state equals the key."""

    D90_FIELDS = ("repeats_rule", "format_status_original", "correct_original")

    def rows(self, repeats=scoring.trace_parse.REPEATS):
        with gzip.open(PARSE_CASES, "rt") as f:
            cases = sorted((json.loads(ln) for ln in f if ln.strip()), key=lambda c: c["id"])
        cases = [c for c in cases if "-r2-" not in c["id"]]       # round 1 (148), the set the digest was pinned on; round 2: Karen's runner test
        keys = {}
        for c in cases:
            if c["expected"]["ok"] and c["line_count"] not in keys:
                keys[c["line_count"]] = [tuple(s) for s in c["expected"]["states"]]
        out = []
        for c in cases:
            key = keys[c["line_count"]]
            other = list(key)
            other[11] = (other[11][0] + 1,) + other[11][1:]
            for k in (key, other):
                out.append((c, k, scoring.grade_1x24(c["reply"], k, c["line_count"], repeats=repeats)))
        return out

    def test_identical_to_before_and_the_d76_definition(self):
        # the ORIGINAL rule (prereg-lock-2, `repeats="strict"`), less D-90's three new fields, is byte-identical to the pinned grading
        rows = self.rows(repeats="strict")
        old = [[c["id"], {k: v for k, v in g.items() if k not in self.D90_FIELDS}] for c, _, g in rows]
        self.assertEqual(hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest(), GRADE_1X24_DIGEST)
        self.assertEqual((len(rows), sum(g["correct"] for _, _, g in rows)), (296, 92))
        for c, key, g in rows:
            tp = scoring.trace_parse.parse_trace(c["reply"], c["line_count"], repeats="strict")
            self.assertEqual(g["correct"], tp.ok and [tuple(s) for s in tp.states] == key, c["id"])
            self.assertEqual(g["correct"], g["correct_original"], c["id"])

    def test_d90_changes_the_official_score_only_on_identical_repeats(self):
        new, old = self.rows(), self.rows(repeats="strict")
        moved = sorted({c["id"] for (c, _, g), (_, _, h) in zip(new, old) if g["correct"] != h["correct"]})
        self.assertEqual(moved, ["L10-duplicate-line", "L12-duplicate-line", "L6-duplicate-line", "L8-duplicate-line"])
        self.assertEqual(sum(g["correct"] for _, _, g in new), 96)    # each identical repeat is now right against its own key
        for (c, _, g), (_, _, h) in zip(new, old):
            self.assertEqual(g["correct_original"], h["correct"], c["id"])   # the "original" view reproduces the old official score


if __name__ == "__main__":
    unittest.main()
