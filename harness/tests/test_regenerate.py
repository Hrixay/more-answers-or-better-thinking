"""Tests for harness/taskgen/regenerate.py (D-212): a frozen set is rebuilt from the table and the released generator, an older recorded
generator version is put back on each item, and the result is compared with the lock manifest's hash. Tiny synthetic sets only."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from harness.taskgen import freeze, regenerate

ROW = {"set_id": "test-ledger-l14n4-v1", "family": "ledger", "setting": "l14n4", "n_base": 2, "style": "d31", "split": "scratch",
       "generator": "ledger-0.4"}


class Regenerate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.saved = regenerate.table
        regenerate.table = lambda: {ROW["set_id"]: ROW}

    def tearDown(self):
        regenerate.table = self.saved
        self.tmp.cleanup()

    def test_the_recorded_version_is_put_back_and_nothing_else_changes(self):
        regenerate.regenerate(ROW["set_id"], self.t / "a")
        plain = freeze.write_set(self.t / "plain" / ROW["set_id"], "ledger", "l14n4", ROW["set_id"], 2, "d31", "scratch")
        mine = [json.loads(ln) for ln in (self.t / "a" / ROW["set_id"] / "items.jsonl").read_text().splitlines()]
        base = [json.loads(ln) for ln in (self.t / "plain" / ROW["set_id"] / "items.jsonl").read_text().splitlines()]
        self.assertEqual({r["version"] for r in mine}, {"ledger-0.4"})
        self.assertNotEqual({r["version"] for r in base}, {"ledger-0.4"})
        strip = lambda rs: [{k: v for k, v in r.items() if k != "version"} for r in rs]
        self.assertEqual(strip(mine), strip(base))                                       # prompts, answers and every other field are the same
        self.assertEqual(plain["prompt_sha256"], json.loads((self.t / "a" / ROW["set_id"] / "manifest.json").read_text())["prompt_sha256"])

    def test_the_lock_check_says_yes_only_for_the_locked_bytes(self):
        regenerate.regenerate(ROW["set_id"], self.t / "a")
        h = hashlib.sha256((self.t / "a" / ROW["set_id"] / "items.jsonl").read_bytes()).hexdigest()
        lock = self.t / "LOCK.md"
        lock.write_text(f"{h}  data/tasks/{ROW['set_id']}/items.jsonl\n")
        self.assertTrue(regenerate.matches_lock(ROW["set_id"], self.t / "a", lock))
        lock.write_text(f"{'0' * 64}  data/tasks/{ROW['set_id']}/items.jsonl\n")
        self.assertFalse(regenerate.matches_lock(ROW["set_id"], self.t / "a", lock))
        lock.write_text("")
        self.assertFalse(regenerate.matches_lock(ROW["set_id"], self.t / "a", lock))      # no line for the set: no

    def test_the_table_holds_the_28_sets(self):
        regenerate.table = self.saved
        t = regenerate.table()
        self.assertEqual(len(t), 28)
        self.assertTrue(all(r["family"] in freeze.FAMILIES and r["style"] in freeze.STYLES and r["n_base"] > 0 for r in t.values()))

    def test_refuses_an_unknown_set(self):
        with self.assertRaises(SystemExit):
            regenerate.main(["--set", "nope", "--out", str(self.t / "x")])


if __name__ == "__main__":
    unittest.main()
