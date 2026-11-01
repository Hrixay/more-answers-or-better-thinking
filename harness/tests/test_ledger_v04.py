"""ledger-0.4: Edith's PR #19 round-2 fixes (X1, M1 to M4, m1 to m5) and the D-77 wording pin."""

import hashlib
import json
import unittest
from pathlib import Path

from harness.taskgen import freeze, ledger, ledger_check
from harness.taskgen.rng import derive_seed

KIND_ARGS = json.loads((Path(__file__).resolve().parent / "fixtures" / "ledger_kind_args.json").read_text())
_CACHE = {}


def puzzle(preset, w, d, tag="v04"):
    key = (preset, w, d, tag)
    if key not in _CACHE:
        _CACHE[key] = ledger.generate(derive_seed("test-ledger-v04", preset, tag), w, d, ledger.SETTINGS[preset])
    return _CACHE[key]


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


class Wording(unittest.TestCase):
    """D-77: the user approved these templates; only numbers, names and letters may vary. The hashes were taken from ledger-0.3, the approved code."""

    def test_rule_sentence_templates(self):
        names = ledger.NAMES[:12]
        texts = {k: ledger.KINDS[k][1](a, names) for k, a in sorted(KIND_ARGS.items())}
        self.assertEqual(set(KIND_ARGS), set(ledger.KINDS))
        self.assertEqual(hashlib.sha256(json.dumps(texts, sort_keys=True).encode()).hexdigest()[:16], "145ae1f7441352e6")

    def test_intro_house_rule_and_closings(self):
        house = ledger.House(t=1234, a=56)
        self.assertEqual(h(ledger.closing_house(1, 24)), "f79ffd0038e003de")
        self.assertEqual(h(ledger.closing_house(1, 24, True)), "833f0c96345370ae")
        self.assertEqual(h(ledger.closing_house(24, 1)), "7ad9127b3aeb7920")
        self.assertEqual(h(house.text()), "cb837d1f40b5510d")
        self.assertEqual(h(ledger.intro(ledger.SETTINGS["l16"], ledger.NAMES[:10], [1] * 10, house)), "72f90273d21e1048")


class Totality(unittest.TestCase):
    def test_the_accepted_draw_is_stored_and_shared_by_both_shapes(self):
        a, b = puzzle("l14", 1, 24), puzzle("l14", 24, 1)
        self.assertEqual(a.attempt, b.attempt)
        self.assertEqual(a.rulebook, b.rulebook)
        self.assertEqual([c.names[0] for c in b.chains], a.chains[0].names)

    def test_retired_presets_are_refused(self):
        for r in ledger.RETIRED:
            with self.assertRaises(ValueError):
                ledger.generate("x", 1, 24, ledger.SETTINGS[r])
            with self.assertRaises(ValueError):
                freeze._params("ledger", r)


class Guards(unittest.TestCase):
    def test_each_slip_size_and_the_house_slips_are_capped_on_the_reference_chain(self):
        for preset in ("l14", "l15"):
            p = puzzle(preset, 1, 24)
            self.assertTrue(all(v <= ledger.ABSORPTION_CAP for v in p.transfer_by_size.values()), p.transfer_by_size)
            self.assertTrue(all(v <= ledger.ABSORPTION_CAP for v in p.house_variants.values()), p.house_variants)
            self.assertEqual(set(p.transfer_by_size), {"1", "10", "100"})

    def test_house_variant_absorption_counts_omit_and_double(self):
        house = ledger.House(t=500, a=100)
        rules = [ledger.Rule("A", "pay", {"a": 0, "b": 1, "k": 50}, house), ledger.Rule("B", "pay", {"a": 1, "b": 2, "k": 30}, house)]
        hv = ledger.house_variant_absorption(rules, (900, 400, 300))
        self.assertEqual(set(hv), {"omit", "double"})
        self.assertEqual(ledger.house_variant_absorption([ledger.Rule("A", "pay", {"a": 0, "b": 1, "k": 50})], (900, 400, 300)),
                         {"omit": 0.0, "double": 0.0})

    def test_single_unit_slips_at_the_start_are_counted(self):
        # a fee bigger than the largest balance empties that line, so a +-1 slip on it at the START (k = 0) leaves no trace: 2 of 6 slips
        rules = [ledger.Rule("A", "fee_largest", {"f": 1000})]
        self.assertAlmostEqual(ledger.absorption_rate(rules, (500, 300, 200)), 2 / 6)

    def test_a_fixed_repeat_that_undoes_itself_is_refused(self):
        # move 1: 300 from line 0 (600) to line 1 (100) -> (300, 400, 350); move 2: 300 from line 1 back to line 0 -> the start again
        rule = ledger.Rule("A", "repeat_fixed", {"A": 300, "n": 3})
        self.assertFalse(ledger.picks_change(rule, (600, 100, 350)))

    def test_the_fixed_repeat_does_not_undo_itself_under_the_house_rule(self):
        # Edith R3-3: two moves of 250 and three moves of 250 differ bare, but give the same state once the house rule (amount 250) has acted
        s = (2500, 2750, 3000, 6000)
        self.assertTrue(ledger.picks_change(ledger.Rule("X", "repeat_fixed", {"A": 250, "n": 3}), s))
        self.assertFalse(ledger.picks_change(ledger.Rule("X", "repeat_fixed", {"A": 250, "n": 3}, ledger.House(t=3000, a=250)), s))

    def test_no_candidate_gives_up_the_draw_at_once(self):
        # Edith R3-2: when no sweep numbers can work at a state, the draw says so instead of offering a rule that changes nothing
        self.assertIsNone(ledger._draw_rule(ledger.HashRNG("x"), "sweep", (100,) * 10, ledger.SETTINGS["l16"]))

    def test_a_rule_that_does_nothing_by_itself_is_never_drawn(self):
        rule = ledger.Rule("A", "count_move", {"src": 2, "t": 1000, "k": 50}, ledger.House(t=5000, a=100))
        s = (900, 800, 100)                         # the source is the smallest line: the bare rule moves units to itself
        self.assertEqual(rule.bare(s), s)
        for preset in ("l14", "l15"):
            p = puzzle(preset, 1, 24)
            names, bare, house, seqs = ledger_check.parse_parts(p.prompt)
            prev = p.chains[0].start
            for lab, st in zip(p.chains[0].names, p.chains[0].states):
                self.assertNotEqual(list(bare[lab](list(prev))), list(prev), (preset, lab))
                prev = st

    def test_the_house_rule_acts_on_a_piece_exactly_when_it_acts_in_the_chain(self):
        chain, pieces = puzzle("l14", 1, 24), puzzle("l14", 24, 1)
        names, bare, house, _ = ledger_check.parse_parts(chain.prompt)
        hstep = ledger_check.house_step(*house)

        def acts(lab, s):
            b = bare[lab](list(s))
            return hstep(b) != list(b)
        before = [chain.chains[0].start] + chain.chains[0].states[:-1]
        for i, (lab, s) in enumerate(zip(chain.chains[0].names, before)):
            self.assertEqual(acts(lab, pieces.chains[i].start), acts(lab, s), (i, lab))

    def test_the_independent_checker_passes_the_new_presets(self):
        for preset in ("l14", "l15"):
            for w, d in ((1, 24), (24, 1)):
                ledger_check.check_puzzle(puzzle(preset, w, d))


class PieceStarts(unittest.TestCase):
    def test_every_piece_start_makes_the_bare_rule_act(self):
        # review finding: a count_move whose source is the smallest line moves units to itself; only the house rule changed the state
        for preset, seed in (("l15", "piece-bare-0"), ("l15", "piece-bare-1")):
            p = ledger.generate(derive_seed("test-ledger-v04", seed), 24, 1, ledger.SETTINGS[preset])
            ledger_check.check_puzzle(p)

    def test_checker_refuses_what_the_generator_refuses(self):
        names = ledger.NAMES[:6]

        class P:                       # the fields _check_steps reads
            line_names = names
        cases = [("avg_donors", {"p": 10}, (1000, 2000, 3500, 4000, 5000, 5500)),             # 3500 is the average
                 ("compare_move", {"a": 0, "b": 1, "c": 2, "p": 10, "q": 10}, (2000, 1000, 3000, 4000, 5000, 6000)),
                 ("sweep", {"T": 3500, "A": 3600}, (1000, 2000, 4000, 4500, 5000, 6000)),
                 ("repeat_fixed", {"A": 50, "n": 3}, (1000, 2000, 3000, 4000, 5000, 9000))]
        for kind, a, s in cases:
            rule = ledger.Rule("A", kind, a)
            self.assertTrue(ledger.unclear(rule, s) or not ledger.picks_change(rule, s), kind)
            P.rulebook = [("A", kind, rule.text(names))]
            fn = ledger_check.parse_rule(rule.text(names), names)          # the checker's own reading of the printed sentence
            with self.assertRaises(AssertionError, msg=kind):
                ledger_check._check_steps(P, {"A": fn}, None, [(list(s), ["A"])], [[list(fn(list(s)))]])


class Budget(unittest.TestCase):
    """Edith R4: ledger-0.4.2 only raises the draw budget (100,000 -> 400,000) so that an unlucky l17 seed still builds (about 1 acceptance
    in 28,500 draws at l17). A seed is accepted at its first good draw, so a larger budget changes no accepted rulebook."""

    def test_the_budget_is_400000(self):
        self.assertEqual(ledger.ATTEMPT_BUDGET, 400000)
        self.assertEqual(ledger.LV_VERSION, "ledger-0.5")

    def test_a_seed_accepted_below_100000_builds_the_same_under_the_old_budget(self):
        seed, params = derive_seed("test-ledger-v04", "budget"), ledger.SETTINGS["l14"]
        new = json.loads(ledger.generate(seed, 1, 24, params).to_json())
        self.assertLess(new["attempt"], 100000)
        old_budget, old_version = ledger.ATTEMPT_BUDGET, ledger.LV_VERSION
        try:
            ledger.ATTEMPT_BUDGET, ledger.LV_VERSION = 100000, "ledger-0.4.1"
            ledger._RULEBOOKS.clear()
            old = json.loads(ledger.generate(seed, 1, 24, params).to_json())
        finally:
            ledger.ATTEMPT_BUDGET, ledger.LV_VERSION = old_budget, old_version
            ledger._RULEBOOKS.clear()
        self.assertEqual(old.pop("version"), "ledger-0.4.1")
        self.assertEqual(new.pop("version"), "ledger-0.5")
        self.assertEqual(old, new)


class Verify(unittest.TestCase):
    def test_a_set_from_another_generator_version_does_not_verify_without_the_flag(self):
        item = json.loads(puzzle("l14", 1, 24).to_json())  # as frozen: JSON, so tuples are lists
        other = dict(item, version="ledger-0.3")
        with self.assertRaises(AssertionError):
            freeze._verify_ledger_item(other)
        freeze._verify_ledger_item(other, allow_other_version=True)
        freeze._verify_ledger_item(item)
        stale = dict(item, transfer_by_size={**item["transfer_by_size"], "1": 0.0})
        if stale != item:
            with self.assertRaises(AssertionError):
                freeze._verify_ledger_item(stale)
        with self.assertRaises(AssertionError):
            freeze._verify_ledger_item(dict(item, attempt=item["attempt"] + 1))


class SelfTests(unittest.TestCase):
    """Edith X1: the two self-tests are part of the suite (one seed, the presets the study uses)."""

    def test_ledger_check_selftest(self):
        ledger_check.selftest(1, presets=("l1", "l14"))

    def test_freeze_selftest(self):
        freeze.selftest()


if __name__ == "__main__":
    unittest.main()
