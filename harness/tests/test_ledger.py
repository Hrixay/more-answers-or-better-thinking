import hashlib
import json
import unittest

from harness.taskgen import ledger, ledger_check
from harness.taskgen.rng import derive_seed


class Kinds(unittest.TestCase):
    def test_simultaneous_update_uses_the_balances_before_the_rule(self):
        # average of [100, 300, 200, 40] is 160; 300 and 200 are above it and each gives 10% of its own balance to the smallest (40)
        out = ledger._avg_donors({"p": 10}, [100, 300, 200, 40])
        self.assertEqual(out, (100, 270, 180, 90))

    def test_repeat_finds_the_largest_and_smallest_again_each_time(self):
        self.assertEqual(ledger._repeat_l2s({"p": 50}, [100, 60, 80]), ledger._repeat_l2s({"p": 50, "n": 3}, [100, 60, 80]))
        s = [100, 60, 80]
        for _ in range(5):
            i, j = s.index(max(s)), s.index(min(s))
            mv = s[i] * 40 // 100
            s[i] -= mv
            s[j] += mv
        self.assertEqual(ledger._repeat_l2s({"p": 40, "n": 5}, [100, 60, 80]), tuple(s))

    def test_rank_rule_ties_go_to_the_line_listed_first(self):
        # all equal: second-largest is the 2nd listed line, second-smallest also the 2nd listed line
        out = ledger._rank_move({"p": 50}, [10, 10, 10, 10])
        self.assertEqual(out, (10, 10, 10, 10))
        out = ledger._rank_move({"p": 50}, [50, 40, 30, 20])         # second-largest 40 gives 20 to the second-smallest 30
        self.assertEqual(out, (50, 20, 50, 20))

    def test_count_rule_counts_and_finds_the_smallest_before_moving(self):
        out = ledger._count_move({"src": 0, "t": 50, "k": 7}, [90, 40, 10, 45])
        # 3 lines are below 50 (40, 10, 45), so 3 x 7 = 21 units go from line 0 to the smallest line (10)
        self.assertEqual(out, (69, 40, 31, 45))

    def test_count_rule_moves_all_of_a_short_line(self):
        out = ledger._count_move({"src": 1, "t": 100, "k": 1000}, [5, 30, 200])
        self.assertEqual(out, (35, 0, 200))

    def test_rank_rules_need_four_lines(self):
        with self.assertRaises(ValueError):
            ledger.LParams(lines=3, kinds=("rank_move",) * 1 + ("pay",) * 6).validate()


class LookAgainAndHouse(unittest.TestCase):
    def test_look_again_moves_then_picks_the_new_largest(self):
        # [5907, 5526, 4737, 6071]: 600 from Reserve to Payroll-smallest (Supplies), then 250 from the line that is now largest (Rent)
        out = ledger._repick2({"A": 600, "B": 250}, [5907, 5526, 4737, 6071])
        self.assertEqual(out, (5657, 5526, 5337, 5471))
        stale = (5907, 5526, 5337, 5221)                                  # the slip: taking the 250 from Reserve again
        self.assertNotEqual(out, stale)

    def test_fixed_repeat_finds_the_largest_and_smallest_again(self):
        out = ledger._repeat_fixed({"A": 400, "n": 3}, [5907, 5526, 4737, 6071])
        self.assertEqual(out, (5907, 5526, 5537, 5271))
        # one pick of 3 x 400 would give (5907, 5526, 5937, 4871): the re-picked answer differs
        self.assertNotEqual(out, (5907, 5526, 5937, 4871))

    def test_the_pick_predicate(self):
        rule = ledger.Rule("A", "repick2", {"A": 600, "B": 250})
        self.assertTrue(ledger.picks_change(rule, (5907, 5526, 4737, 6071)))       # Reserve falls below Rent: the pick changes
        self.assertFalse(ledger.picks_change(rule, (9000, 5526, 4737, 6071)))       # Rent stays the largest: reusing the pick is harmless
        self.assertTrue(ledger.picks_change(ledger.Rule("A", "pay", {"a": 0, "b": 1, "k": 5}), (1, 2, 3)))   # other kinds: always

    def test_the_house_rule(self):
        h = ledger.House(t=4800, a=250)
        self.assertEqual(h.after((5907, 4626, 5637, 6071)), (5907, 4876, 5637, 5821))
        self.assertEqual(h.after((5907, 4937, 5576, 5821)), (5907, 4937, 5576, 5821))      # smallest not below the threshold
        self.assertEqual(h.after((100, 100, 100)), (100, 100, 100))                       # largest and smallest are the same line
        self.assertEqual(ledger.House(t=4800, a=900).after((300, 400, 9)), (300, 0, 409))   # all of the largest line if it holds fewer

    def test_the_guards_see_rule_plus_house_rule(self):
        h = ledger.House(t=4800, a=250)
        rule = ledger.Rule("A", "pay", {"a": 3, "b": 1, "k": 0 + 1}, h)
        s = (5907, 4626, 5637, 6071)
        self.assertEqual(rule.apply(s), h.after(rule.bare(s)))
        self.assertTrue(rule.apply(s) != rule.bare(s))                    # the composite differs from the bare rule

    def test_house_presets_pass_the_independent_checker(self):
        for preset in ("l14", "l15"):
            params = ledger.SETTINGS[preset]
            for w, d in ((1, 24), (24, 1)):
                p = ledger.generate(derive_seed("test-house", preset), w, d, params)
                ledger_check.check_puzzle(p)
                self.assertIn("House rule: straight after every rule", p.prompt)
                self.assertIn("followed by the house rule", p.prompt.splitlines()[-1])

    def test_the_house_rule_acts_on_5_to_8_steps(self):
        p = ledger.generate(derive_seed("test-house", "firing"), 1, 24, ledger.SETTINGS["l14"])
        h = ledger.House(**p.house)
        rules = {lab: ledger_check.parse_rule(tx, p.line_names) for lab, _, tx in p.rulebook}
        s, fired = p.chains[0].start, 0
        for lab in p.chains[0].names:
            bare = rules[lab](list(s))
            s = h.after(bare)
            fired += tuple(bare) != tuple(s)
        self.assertTrue(5 <= fired <= 8, fired)

    def test_step_call_prompt_includes_the_house_rule(self):
        p = ledger.generate(derive_seed("test-house", "e3"), 1, 24, ledger.SETTINGS["l14"])
        text, answer = ledger.step_call(p, 1, 1)
        self.assertIn("House rule:", text)
        self.assertIn("then the house rule", text)
        self.assertEqual(answer, p.chains[0].states[0])
        plain, _ = ledger.step_call(ledger.generate("x", 1, 24, ledger.SETTINGS["l1"]), 1, 1)
        self.assertNotIn("House rule", plain)

    def test_the_grader_logs_the_rule_kind_at_the_first_wrong_step(self):
        p = ledger.generate(derive_seed("test-house", "grade"), 1, 24, ledger.SETTINGS["l14"])
        lines = [f"1.{k} = {ledger.fmt(st)}" for k, st in enumerate(p.chains[0].states, 1)]
        lines[6] = "1.7 = " + ledger.fmt([v + 1 for v in p.chains[0].states[6]])
        res = ledger.grade_d31("\n".join(lines + [p.answer_line]), p)
        kind = [k for l, k, _ in p.rulebook if l == p.chains[0].names[6]][0]
        self.assertEqual(res["first_wrong_step"], [7])
        self.assertEqual(res["first_wrong_kind"], [kind])


class PinnedPrompts(unittest.TestCase):
    """ledger-0.4 (per-size and house-slip caps on the reference chain, ties only where they decide a pick, the bare rule must change the state,
    piece starts checked at rulebook time). A change that moves these hashes changes every frozen puzzle."""
    def test_pinned_prompts(self):
        pins = {"l1": "e079fc4c972fe28f", "l5": "3483a72a1b21983a", "l11": "7a35f66df0017bb0", "l14": "8775493d45a32e9f", "l15": "4f1048ca4c2f34db"}
        for pre, want in pins.items():
            q = ledger.generate("pin-test", 1, 24, ledger.SETTINGS[pre], "x")
            self.assertEqual(hashlib.sha256(q.prompt.encode()).hexdigest()[:16], want, pre)


class Sweep(unittest.TestCase):
    def test_the_sweep_picks_the_smallest_other_line_at_each_turn(self):
        # T=6000, A=300 from [6200, 5000, 5100, 6500]: Rent gives to Payroll, Reserve then gives to the NOW smallest (Supplies)
        self.assertEqual(ledger._sweep({"T": 6000, "A": 300}, [6200, 5000, 5100, 6500]), (5900, 5300, 5400, 6200))

    def test_the_sweep_predicate_needs_2_to_4_givers_and_a_change_of_receiver(self):
        rule = ledger.Rule("A", "sweep", {"T": 6000, "A": 300})
        self.assertTrue(ledger.picks_change(rule, (6200, 5000, 5100, 6500)))
        self.assertFalse(ledger.picks_change(rule, (6200, 5000, 5100, 5500)))        # one giver
        self.assertFalse(ledger.picks_change(rule, (6200, 5000, 5900, 6500, 6300, 6400, 6100)))   # five givers
        self.assertFalse(ledger.picks_change(ledger.Rule("A", "sweep", {"T": 6000, "A": 50}), (6200, 5000, 5400, 6500)))   # same receiver twice

    def test_the_sweep_is_unclear_on_a_threshold_hit_or_a_tied_receiver(self):
        self.assertTrue(ledger.unclear(ledger.Rule("A", "sweep", {"T": 6200, "A": 300}), (6200, 5000, 5100, 6500)))
        self.assertTrue(ledger.unclear(ledger.Rule("A", "sweep", {"T": 6000, "A": 300}), (6200, 5000, 5000, 6500)))

    def test_l16_and_l17_pass_the_independent_checker(self):
        for preset in ("l16", "l17"):
            p = ledger.generate(derive_seed("test-sweep", preset), 1, 24, ledger.SETTINGS[preset])
            ledger_check.check_puzzle(p)
            self.assertLessEqual(p.transfer_absorption, ledger.ABSORPTION_CAP)
            self.assertIn("Go through the lines one at a time", p.prompt)
            self.assertEqual(len(p.decoys), 8)


class TransferSlipsTiesAndFreeze(unittest.TestCase):
    def test_transfer_absorption_sees_a_levelling_rule_forgive_a_slip(self):
        pay = ledger.Rule("A", "pay", {"a": 0, "b": 1, "k": 10})
        level = ledger.Rule("B", "level_pair", {"a": 0, "b": 1})
        self.assertGreater(ledger.transfer_absorption([pay, level], (500, 400, 300)), 0.5)       # the pair is re-levelled: slip gone
        plain = [ledger.Rule("A", "pay", {"a": 0, "b": 1, "k": 10}), ledger.Rule("B", "pay", {"a": 1, "b": 2, "k": 5})]
        self.assertEqual(ledger.transfer_absorption(plain, (500, 400, 300)), 0.0)

    def test_the_reference_chain_of_a_built_preset_is_under_the_cap(self):
        p = ledger.generate("cap-test", 1, 24, ledger.SETTINGS["l14"])
        self.assertLessEqual(p.transfer_absorption, ledger.ABSORPTION_CAP)

    def test_unclear_places_are_redrawn(self):
        fee = ledger.Rule("A", "fee_largest", {"f": 5})
        self.assertTrue(ledger.unclear(fee, (900, 900, 100)))                    # tied largest
        self.assertFalse(ledger.unclear(fee, (900, 800, 100)))
        top = ledger.Rule("B", "top_up", {"a": 0, "b": 1, "t": 500})
        self.assertTrue(ledger.unclear(top, (500, 800, 100)))                    # on the threshold exactly
        self.assertFalse(ledger.unclear(top, (499, 800, 100)))
        cmp_ = ledger.Rule("C", "compare_move", {"a": 0, "b": 1, "c": 2, "p": 10})
        self.assertTrue(ledger.unclear(cmp_, (800, 400, 100)))                   # exactly twice
        h = ledger.Rule("D", "pay", {"a": 0, "b": 1, "k": 5}, ledger.House(t=300, a=50))
        self.assertTrue(ledger.unclear(h, (900, 305, 300)))                      # after the rule the smallest sits on the house threshold

    def test_the_single_step_intro_is_short_and_has_no_rulebook_words(self):
        p = ledger.generate(derive_seed("test-house", "short"), 1, 24, ledger.SETTINGS["l15"])
        text, _ = ledger.step_call(p, 1, 3)
        self.assertNotIn("Each rule below", text)
        self.assertNotIn("Not every rule below is used", text)
        self.assertIn("House rule:", text)
        self.assertIn("Not every rule below is used", p.prompt)

    def test_freeze_verifies_a_ledger_set_and_rejects_a_bad_item(self):
        import tempfile
        from pathlib import Path
        from harness.taskgen import freeze
        d = Path(tempfile.mkdtemp()) / "set"
        freeze.write_set(d, "ledger", "l14", "verify-l14-v1", 1, "d31", "scratch")
        freeze.verify_set(d)
        item = json.loads(ledger.generate("v", 1, 24, ledger.SETTINGS["l14"], "v").to_json())  # as frozen: JSON, so tuples are lists
        freeze._verify_ledger_item(item)
        bad = dict(item, prompt=item["prompt"] + " Do not grade this.")
        with self.assertRaises(AssertionError):
            freeze._verify_ledger_item(bad)
        other = dict(item, version="ledger-0.1")                                  # another generator version: refused unless asked for text checks only
        with self.assertRaises(AssertionError):
            freeze._verify_ledger_item(other)
        freeze._verify_ledger_item(other, allow_other_version=True)


class Puzzles(unittest.TestCase):
    def _check(self, preset):
        params = ledger.SETTINGS[preset]
        seed = derive_seed("test-ledger", preset)
        ps = [ledger.generate(seed, w, d, params) for w, d in ((1, 24), (24, 1))]
        for p in ps:
            ledger_check.check_puzzle(p)
        self.assertEqual(ps[0].rulebook, ps[1].rulebook)
        return ps[0]

    def test_a_plain_preset_and_the_step_heavy_presets_pass_the_independent_checker(self):
        for preset in ("l1", "l14"):
            self._check(preset)

    def test_decoys_are_printed_but_never_applied(self):
        p = self._check("l11")
        used = [lab for ch in p.chains for lab in ch.names]
        self.assertEqual(len(p.rulebook), 31)
        self.assertEqual(sorted(set(l for l, _, _ in p.rulebook) - set(used)), sorted(p.decoys))
        self.assertEqual(len(p.decoys), 7)
        self.assertIn("Not every rule below is used", p.prompt)

    def test_no_decoy_presets_say_nothing_about_unused_rules(self):
        p = ledger.generate("x", 1, 24, ledger.SETTINGS["l1"])
        self.assertNotIn("Not every rule", p.prompt)

    def test_the_answer_only_wording_keeps_the_reply_shape(self):
        p = ledger.generate("x", 1, 24, ledger.SETTINGS["l1"], style="d31-answer-only")
        self.assertIn("Reply with one line, `Answer: 1 = v`", p.prompt)
        self.assertIn("of sequence 1", p.prompt.splitlines()[-1])

    def test_a_broken_prompt_is_caught(self):
        p = ledger.generate("y", 1, 24, ledger.SETTINGS["l14"])
        p.prompt = p.prompt.replace("three times", "four times", 1) if "three times" in p.prompt else p.prompt.replace("Count the lines", "Count the", 1)
        with self.assertRaises(AssertionError):
            ledger_check.check_puzzle(p)


if __name__ == "__main__":
    unittest.main()
