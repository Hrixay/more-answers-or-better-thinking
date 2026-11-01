"""Tests for the illustrative puzzle (harness/taskgen/illustration.py, D-141): it builds deterministically, rebuilds from its seed, and
the disjointness check refuses a shared set id, seed or prompt (on synthetic manifests: no test set is read here)."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.taskgen import illustration as il


class Illustration(unittest.TestCase):
    def setUp(self):
        self.items = il.build()

    def _tasks(self, man):
        d = tempfile.TemporaryDirectory()
        (Path(d.name) / "some-set-v1").mkdir()
        (Path(d.name) / "some-set-v1" / "manifest.json").write_text(json.dumps(man))
        return d

    def test_two_shapes_of_one_base(self):
        shapes = sorted(f"{it['width']}x{it['depth']}" for it in self.items)
        self.assertEqual(shapes, ["1x4", "4x1"])
        self.assertEqual(len({it["seed"] for it in self.items}), 1)

    def test_disjoint_passes_and_refuses(self):
        seed = str(il.derive_seed(il.SET_ID, 0))
        with self._tasks({"set_id": "other-v1", "seeds": ["1", "2"], "prompt_sha256": ["0" * 64]}) as d:
            res = il.disjointness(Path(d), self.items)
            self.assertEqual((res["sets_checked"], res["shared_seeds"], res["shared_prompts"]), (1, 0, 0))
        for bad in ({"set_id": il.SET_ID, "seeds": [], "prompt_sha256": []},
                    {"set_id": "other-v1", "seeds": [seed], "prompt_sha256": []},
                    {"set_id": "other-v1", "seeds": [], "prompt_sha256": [il.sha(self.items[0]["prompt"])]}):
            with self._tasks(bad) as d, self.assertRaises(ValueError):
                il.disjointness(Path(d), self.items)

    def test_deterministic_files(self):
        with self._tasks({"set_id": "other-v1", "seeds": [], "prompt_sha256": []}) as t, \
                tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            dj = il.disjointness(Path(t), self.items)
            fa = il.write(Path(a), il.build(), dj)
            fb = il.write(Path(b), il.build(), dj)
            self.assertEqual(fa, fb)
            self.assertIn(il.LABEL, (Path(a) / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
