"""D-86 (declared deviation, shorter puzzles): the l14 rules at N steps, N in {4, 6, 8, 12, 16}. Same kinds, wording, guards and caps as l14;
only the step count and the house rule's window (scaled from l14's 5-8 of 24) change. The 24-step presets are untouched."""

import hashlib
import re
import unittest

from harness.taskgen import ledger, ledger_check
from harness.taskgen.rng import derive_seed


class Presets(unittest.TestCase):
    def test_the_ladder_presets_are_l14_with_n_steps(self):
        base = ledger.SETTINGS["l14"]
        self.assertEqual(ledger.LADDER_STEPS, (4, 6, 8, 12, 16))
        for n in ledger.LADDER_STEPS:
            p = ledger.SETTINGS[f"l14n{n}"]
            self.assertEqual(p.total_steps, n)
            self.assertEqual({k: v for k, v in vars(p).items() if k not in ("total_steps", "house_fires")},
                             {k: v for k, v in vars(base).items() if k not in ("total_steps", "house_fires")})
        self.assertEqual({n: ledger.house_window(n) for n in ledger.LADDER_STEPS},
                         {4: (1, 2), 6: (1, 2), 8: (1, 3), 12: (2, 4), 16: (3, 6)})
        self.assertEqual(ledger.house_window(24), (5, 8))                 # l14's own window at 24

    def test_other_step_counts_are_refused(self):
        import dataclasses
        with self.assertRaises(ValueError):
            dataclasses.replace(ledger.SETTINGS["l14"], total_steps=10).validate()

    def test_the_24_step_presets_are_unchanged(self):
        q = ledger.generate("pin-test", 1, 24, ledger.SETTINGS["l14"], "x")
        self.assertEqual(hashlib.sha256(q.prompt.encode()).hexdigest()[:16], "8775493d45a32e9f")   # the ledger-0.4 pin


class Builds(unittest.TestCase):
    def test_both_shapes_build_and_pass_the_independent_checker_at_every_n(self):
        for n in ledger.LADDER_STEPS:
            p = ledger.SETTINGS[f"l14n{n}"]
            seed = derive_seed("test-ledger-n", n)
            chain, pieces = ledger.generate(seed, 1, n, p), ledger.generate(seed, n, 1, p)
            for q in (chain, pieces):
                ledger_check.check_puzzle(q)
            self.assertEqual(len(chain.chains[0].states), n)
            self.assertEqual(len(pieces.chains), n)
            self.assertEqual(chain.rulebook, pieces.rulebook)              # both shapes share the rulebook
            self.assertIn(f"..., {n} = v`", pieces.prompt)                 # the N x 1 closing names N, the same sentence otherwise

    def test_the_wording_is_the_approved_templates_with_n(self):
        p = ledger.SETTINGS["l14n6"]
        seed = derive_seed("test-ledger-n", "wording")
        pieces = ledger.generate(seed, 6, 1, p)
        self.assertEqual(ledger.closing_house(6, 1), ledger.closing_house(24, 1).replace("24 = v", "6 = v"))
        self.assertEqual(ledger.closing_house(1, 6), ledger.closing_house(1, 24))   # the 1 x N closing does not name N
        self.assertTrue(pieces.prompt.rstrip().endswith(ledger.closing_house(6, 1)))


class FreezeAndSelftest(unittest.TestCase):
    """Edith lock-2 L2-1, L2-2: the self-test and the frozen-set writer take the shapes from the preset's N."""

    def test_the_checker_selftest_runs_at_every_ladder_n(self):
        from harness.taskgen import ledger_check
        ledger_check.selftest(1, presets=tuple(f"l14n{n}" for n in ledger.LADDER_STEPS))

    def test_a_tiny_l14n6_set_freezes_and_verifies(self):
        import json
        import tempfile
        from pathlib import Path
        from harness.taskgen import freeze
        d = Path(tempfile.mkdtemp()) / "set"
        m = freeze.write_set(d, "ledger", "l14n6", "test-ledger-l14n6-v1", 2, "d31", "scratch")
        self.assertEqual(m["shapes"], ["6x1", "1x6"])
        self.assertEqual(m["n_items"], 4)
        self.assertEqual({(r["width"], r["depth"]) for r in map(json.loads, (d / "items.jsonl").read_text().splitlines())},
                         {(6, 1), (1, 6)})
        freeze.verify_set(d)
        self.assertEqual(freeze.shapes_for(ledger.SETTINGS["l14"]), ((24, 1), (1, 24)))


class OldSetsRebuildUnderNewVersion(unittest.TestCase):
    """Edith lock-2 L2-3 (one-time check): the first base puzzle of each locked ledger-0.4.2 set rebuilds byte for byte under ledger-0.5
    apart from the version string. Slow (l17 can take minutes), so it runs only with PARETO_SLOW=1."""

    @unittest.skipUnless(__import__("os").environ.get("PARETO_SLOW") == "1", "slow one-time check; set PARETO_SLOW=1")
    def test_first_base_of_each_locked_set(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[2] / "data" / "tasks"
        checked = 0
        for d in sorted(root.glob("*-ledger-*")):
            man = json.loads((d / "manifest.json").read_text())
            if man["generator"] != "ledger-0.4.2":
                continue
            for r in map(json.loads, (d / "items.jsonl").read_text().splitlines()):
                if r["base_index"] != 0:
                    continue
                params = ledger.LParams(**{**r["params"], "kinds": tuple(r["params"]["kinds"]), "house_fires": tuple(r["params"]["house_fires"])})
                again = json.loads(ledger.generate(r["seed"], r["width"], r["depth"], params, item_id=r["id"], style=r["style"]).to_json())
                stored = {k: v for k, v in r.items() if k != "base_index"}
                self.assertEqual(again.pop("version"), "ledger-0.5")
                self.assertEqual(stored.pop("version"), "ledger-0.4.2")
                self.assertEqual(again, stored, r["id"])
                checked += 1
        self.assertGreaterEqual(checked, 16)                                # 8 sets x 2 shapes


if __name__ == "__main__":
    unittest.main()
