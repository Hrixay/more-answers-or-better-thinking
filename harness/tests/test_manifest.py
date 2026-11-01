import json
import unittest
from pathlib import Path
from tempfile import mkdtemp

from harness.pareto.manifest import item_set_hash, write_manifest
from harness.tests.fakes import guard, params


class Manifest(unittest.TestCase):
    def test_written_once_with_hashes(self):
        its = [("a", params(text="x"), {}), ("b", params(text="y"), {})]
        d = Path(mkdtemp())
        p = write_manifest(d, guard(), its, "dry")
        doc = json.loads(p.read_text())
        self.assertEqual((doc["run_id"], doc["mode"], doc["n_items"]), ("test-run", "dry", 2))
        self.assertEqual(len(doc["source_sha256"]), 64)
        with self.assertRaises(FileExistsError):
            write_manifest(d, guard(), its, "dry")

    def test_item_hash_ignores_order_but_not_content(self):
        a, b = ("a", params(text="x"), {}), ("b", params(text="y"), {})
        self.assertEqual(item_set_hash([a, b]), item_set_hash([b, a]))
        self.assertNotEqual(item_set_hash([a, b]), item_set_hash([a, ("b", params(text="z"), {})]))


if __name__ == "__main__":
    unittest.main()
