import unittest

from harness.analysis import fairness, fairness_input, scoring
from harness.taskgen import ledger
from harness.taskgen.rng import derive_seed


def puzzle():
    return ledger.generate(derive_seed("test-fairness-input", "l14"), 1, 24, ledger.SETTINGS["l14"])


def reply(p, lines):
    out = [f"1.{k} = {ledger.fmt(lines.get(k, st))}" for k, st in enumerate(p.chains[0].states, 1)]
    return "\n".join(out + [p.answer_line])


class Records(unittest.TestCase):
    def test_counts_add_up_per_preset_base_and_model(self):
        p = puzzle()
        clean = scoring.local_steps(reply(p, {}), p)
        wrong = [p.chains[0].states[4][0] + 1] + list(p.chains[0].states[4][1:])
        # a slip at step 5 and a correct continuation from it, so exactly one local slip
        rules = scoring._Rules(p)
        lines, prev = {5: wrong}, wrong
        for k in range(6, 25):
            prev = list(rules.composite[p.chains[0].names[k - 1]](list(prev)))
            lines[k] = prev
        # `reply` writes the KEY's Answer line, so this try's Answer line differs from its own line 24 (answer_mismatch). Its step lines are
        # readable and hold a slip, so the plan places it (Edith F25-1); before that fix it was dropped and Haiku had 24 steps, not 48
        slipped = scoring.local_steps(reply(p, lines), p)
        self.assertEqual((slipped["status"], slipped["unplaceable"]), ("answer_mismatch", None))
        junk = scoring.local_steps("junk", p)
        recs = fairness_input.records_from_tries([("l14", "b1", "haiku", clean), ("l14", "b1", "haiku", slipped), ("l14", "b1", "haiku", junk),
                                                  ("l14", "b1", "opus", clean)])
        by = {r.model: r for r in recs}
        self.assertEqual(len(recs), 2)
        h, o = by["haiku"], by["opus"]
        self.assertEqual(h.house_steps_checked, 48)                      # two placed tries of 24 steps; the junk try is left out
        self.assertEqual(o.house_steps_checked, 24)
        self.assertEqual(h.T_slips + h.G_slips, 1)
        self.assertEqual(o.T_slips + o.G_slips, 0)
        self.assertEqual(h.house_should_fire + h.house_should_not_fire, 48)
        steps = sum(1 for st in clean["steps"] if st["cls"] == "T")
        self.assertEqual(o.T_steps, steps)

    def test_the_records_run_through_the_fairness_check(self):
        p = puzzle()
        clean = scoring.local_steps(reply(p, {}), p)
        recs = [r for b in ("b1", "b2", "b3") for m in ("haiku", "opus") for r in
                fairness_input.records_from_tries([("l14", b, m, clean)])]
        out = fairness.fairness_indices(recs, B=200)
        self.assertFalse(out["flag_k"]["fires"])                          # no slips at all: nothing to flag
        self.assertIn("not assessable at pilot scale", out["flag_k"]["reason"])
        self.assertEqual(out["counts"]["haiku"]["G_slips"] if "haiku" in out["counts"] else 0, 0)


class Unplaceable(unittest.TestCase):
    """Edith F25-2: unplaceable tries are counted and left out, per model and preset, by reason (the parse status)."""

    def test_counted_by_model_preset_and_reason_and_reported(self):
        p = puzzle()
        clean = scoring.local_steps(reply(p, {}), p)
        lines = reply(p, {}).splitlines()
        wrong_final = [p.chains[0].states[-1][0] + 1] + list(p.chains[0].states[-1][1:])
        right_steps_wrong_answer = scoring.local_steps("\n".join(lines[:-1] + [f"Answer: 1 = {ledger.fmt(wrong_final)}"]), p)
        missing = scoring.local_steps("\n".join(lines[:3] + lines[4:]), p)
        junk = scoring.local_steps("junk", p)
        self.assertEqual([r["status"] for r in (right_steps_wrong_answer, missing, junk)], ["answer_mismatch", "missing_line", "missing_line"])
        tries = [("l14", "b1", "haiku", clean), ("l14", "b1", "haiku", right_steps_wrong_answer), ("l14", "b2", "haiku", missing),
                 ("l15", "b3", "haiku", junk), ("l14", "b1", "opus", clean), ("l14", "b2", "opus", clean)]
        un = fairness_input.unplaceable_from_tries(tries)
        self.assertEqual(un, {"haiku": {"l14": {"answer_mismatch": 1, "missing_line": 1}, "l15": {"missing_line": 1}}})
        recs = fairness_input.records_from_tries(tries)
        self.assertEqual(sum(r.house_steps_checked for r in recs if r.model == "haiku"), 24)     # left out of the counts
        out = fairness.fairness_indices(recs, B=50, unplaceable=un)
        self.assertEqual(out["unplaceable"]["by_model_preset"]["haiku"]["l14"],
                         {"tries": 2, "by_reason": {"answer_mismatch": 1, "missing_line": 1}})
        self.assertEqual(out["unplaceable"]["by_model_preset"]["haiku"]["l15"], {"tries": 1, "by_reason": {"missing_line": 1}})
        self.assertEqual(out["per_preset"]["l14"]["haiku"]["unplaceable"]["tries"], 2)
        self.assertEqual(out["per_preset"]["l14"]["opus"]["unplaceable"], {"tries": 0, "by_reason": {}})
        self.assertEqual(fairness.fairness_indices(recs, B=50)["unplaceable"]["by_model_preset"], {})
        with self.assertRaises(ValueError):
            fairness.fairness_indices(recs, B=50, unplaceable={"haiku": {"l14": {"missing_line": -1}}})


if __name__ == "__main__":
    unittest.main()
