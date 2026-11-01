"""D-42 (a), D-91: the runner's variant renderer equals Karen's approved renderer on every frozen main-set puzzle, keeps everything but
the opening and closing paragraphs byte-identical, passes the wording rules, and the D-42 arm is Haiku-medium x10 at 5,000 tokens on
base 000-019 at both shapes."""

import importlib.util
import json
import re
import unittest
from pathlib import Path

from harness.pareto import d42
from harness.pareto.main import D42_SETUP, build_d42_requests
from harness.taskgen import prompt_d31

ROOT = Path(__file__).resolve().parents[2]
SET = ROOT / "data" / "tasks" / "main-ledger-l14n6-v1"
KAREN = ROOT / "research" / "models" / "d42_variant.py"


def _karen():
    spec = importlib.util.spec_from_file_location("karen_d42_variant", KAREN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                                             # type: ignore[union-attr]
    return mod


@unittest.skipUnless(SET.is_dir() and KAREN.is_file(), "the main set or Karen's renderer is not in this tree")
class Variant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = [json.loads(ln) for ln in (SET / "items.jsonl").read_text().splitlines() if ln.strip()]
        cls.karen = _karen()

    def test_equal_to_karens_renderer_on_every_frozen_item(self):
        for it in self.items:
            self.assertEqual(d42.render(it), self.karen.render(it), it["id"])

    def test_only_the_opening_and_closing_change_and_the_wording_rules_hold(self):
        banned = re.compile(prompt_d31.BANNED, re.I)
        for it in self.items:
            approved, variant = d42.render(it)
            self.assertEqual(approved, it["prompt"])
            mid = lambda p: p.split("\n\n", 1)[1].rsplit("\n\n", 1)[0]
            self.assertEqual(mid(variant), mid(approved), it["id"])
            self.assertNotEqual(variant, approved)
            self.assertIsNone(banned.search(variant), it["id"])
            self.assertNotIn("$", variant)
            fmt = ["`1.1 = v`", "`Answer: 1 = v`"] if int(it["width"]) == 1 else [f"`Answer: 1 = v, 2 = v, ..., {it['width']} = v`"]
            for f in fmt:
                self.assertIn(f, variant)

    def test_the_d42_arm(self):
        man = json.loads((SET / "manifest.json").read_text())
        reqs = build_d42_requests(man, self.items)
        self.assertEqual(len(reqs), 400)
        self.assertEqual(sorted({m["base_index"] for _, _, m in reqs}), list(range(20)))
        self.assertEqual({(m["width"], m["depth"]) for _, _, m in reqs}, {(6, 1), (1, 6)})
        by_id = {it["id"]: it for it in self.items}
        for cid, p, m in reqs:
            self.assertEqual((p["model"], p["output_config"]["effort"], p["max_tokens"], m["setup"]), (D42_SETUP.model, "medium", 5_000, "hv"))
            self.assertEqual(p["messages"][0]["content"], d42.variant_prompt(by_id[m["item_id"]]))
        self.assertTrue(all(it["prompt"] == d42.render(it)[0] for it in self.items))     # the frozen items are not modified


if __name__ == "__main__":
    unittest.main()
