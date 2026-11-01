"""Tests for harness/analysis/reproduction.py: the folder is deterministic and self-consistent, every prompt is the run code's on the
illustrative puzzle (never a test item), placeholders appear only where a model's text would be, and every request is a clean one with
the arm's own settings. Counts only: nothing from data/tasks is printed."""

import hashlib
import json
import unittest
from pathlib import Path

from harness.analysis import reproduction as rp
from harness.pareto import e3, main
from harness.pareto.request import assert_clean

REPO = Path(__file__).resolve().parents[2]
TASKS = REPO / "data" / "tasks"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@unittest.skipUnless((rp.ILLUSTRATION / "illustration.json").is_file() and TASKS.is_dir(), "the illustration or data/tasks is missing")
class Reproduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = rp.build(TASKS)
        cls.prompts = json.loads(cls.files["prompts.json"])
        cls.arms = json.loads(cls.files["arms.json"])["arms"]

    def test_deterministic_and_summed(self):
        self.assertEqual(rp.build(TASKS), self.files)
        sums = dict(reversed(l.split("  ", 1)) for l in self.files["SHA256SUMS"].splitlines())
        self.assertEqual(set(sums), set(self.files) - {"SHA256SUMS"})
        for name, h in sums.items():
            self.assertEqual(_sha(self.files[name]), h, name)

    def test_every_prompt_kind_and_its_record(self):
        recs = {r["file"]: r for r in self.prompts["prompts"]}
        names = {n for n in self.files if n.startswith("prompts/")}
        self.assertEqual(set(recs), names)
        kinds = {r["setup"] for r in recs.values()}
        self.assertEqual(kinds, {main.D42_SETUP.name, e3.SETUP_TAG, "tp", "th", "ta", "pk"})
        self.assertEqual(sum(1 for n in names if "-step-" in n), 8)                         # 4 chain steps, 4 pieces
        for name, r in recs.items():
            self.assertEqual(r["sha256"], _sha(self.files[name]))
            q = dict(r["request"], messages=[{"role": "user", "content": self.files[name]}])
            assert_clean(q)
            self.assertEqual(r["request"]["messages"][0]["content"], rp.PROMPT_POINTER.format(file=name.split("/", 1)[1]))

    def test_placeholders_only_where_a_model_wrote(self):
        for name, text in self.files.items():
            if not name.startswith("prompts/"):
                continue
            has = "[placeholder:" in text
            self.assertEqual(has, name.endswith(("-helper-prompt.txt", "-picker-prompt.txt")), name)
        self.assertEqual(self.files["prompts/chain-picker-prompt.txt"].count("[placeholder:"), 8)

    def test_not_a_test_item(self):
        dj = self.prompts["puzzle"]["disjointness"]
        self.assertEqual((dj["shared_set_ids"], dj["shared_seeds"], dj["shared_prompts"]), (0, 0, 0))
        self.assertGreater(dj["sets_checked"], 0)
        self.assertEqual(self.prompts["puzzle"]["not_a_test_render"]["shared"], 0)

    def test_aggregator_gets_the_true_step_results(self):
        man, chain, pieces, _ = rp.load_puzzle(TASKS)
        truths = rp.step_truths(chain)
        self.assertEqual(truths[-1], chain["answer"][0])                                    # the chain ends at its one answer
        self.assertEqual(rp.step_truths(pieces), pieces["answer"])                           # each sequence's one rule gives its answer
        agg = self.files["prompts/chain-aggregator-prompt.txt"]
        for k, t in enumerate(truths, 1):
            self.assertIn(f"Place {k}, rule ", agg)
            self.assertIn(str(t), agg)

    def test_arm_settings_are_the_run_code_s(self):
        s1 = {a["tag"]: a for a in self.arms if a["study"] == "Study 1"}
        for su in main.MAIN_SETUPS + (main.D42_SETUP,):
            a = s1[su.name]
            self.assertEqual((a["model"], a["effort"], a["max_tokens"], a["thinking_off"]), (su.model, su.effort, su.max_tokens, su.thinking_off))
            self.assertEqual(a["request"]["thinking"], {"type": "disabled"} if su.thinking_off else {"type": "adaptive"})
        from harness.pareto import ladder
        from harness.pareto.limits import pilot_max_tokens
        sweep = {a["tag"]: a for a in self.arms if a["study"] == "length sweep"}
        self.assertEqual(set(sweep), {su.name for su in ladder.LADDER_SETUPS})
        for su in ladder.LADDER_SETUPS:
            a = sweep[su.name]
            self.assertEqual((a["model"], a["effort"], a["tries_per_puzzle"], a["max_tokens"]),
                             (su.model, su.effort, su.n, pilot_max_tokens("ledger", su.model)))
        self.assertIn("Pilot 1", json.loads(self.files["arms.json"])["scope"])
        for a in self.arms:
            if isinstance(a["request"], dict):
                self.assertEqual(a["request"]["model"], a["model"])
                self.assertEqual(a["request"]["max_tokens"], a["max_tokens"])
                self.assertEqual(a["request"]["output_config"], {"effort": a["effort"]})
        self.assertEqual({a["model"] for a in self.arms}, {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"})

    def test_prices_and_parsers(self):
        p = json.loads(self.files["prices.json"])
        self.assertEqual(set(p["base"]), {"claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"})
        self.assertEqual(set(p["long_prompt"]), {"claude-haiku-5-5"})
        parsers = json.loads(self.files["parsers.json"])["parsers"]
        self.assertEqual(len(parsers), len(rp.PARSERS))
        self.assertTrue(all(x.get("doc") or x.get("source") for x in parsers))


if __name__ == "__main__":
    unittest.main()
