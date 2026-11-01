"""harness/check_tracked.py (Edith's P1): the package's .gitignore hides data/raw/, so the push must `git add -f data/raw`; the check says
which listed files git does not track."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import check_tracked as ct


class Tracked(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for path in ("data/raw/run-1/compact_table.csv", "README.md", "lock-records/prereg-lock-1.tag"):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text("x\n")
        (self.root / ".gitignore").write_text("data/raw/\n")                                       # the locked bytes' line
        (self.root / "RELEASE-FILES.json").write_text(json.dumps({
            "files": [{"path": "data/raw/run-1/compact_table.csv"}], "supplied": [{"path": "README.md"}],
            "generated": ["RELEASE-FILES.json", "lock-records/"]}))
        self.git = lambda *a: subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a],
                                             check=True, capture_output=True)
        self.git("init", "-q")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_plain_add_leaves_the_run_files_out_and_a_forced_one_does_not(self):
        self.git("add", "-A")
        self.assertEqual(ct.untracked(self.root), ["data/raw/run-1/compact_table.csv"])
        self.assertEqual(ct.main(["--root", str(self.root)]), 1)
        self.git("add", "-f", "data/raw")
        self.assertEqual(ct.untracked(self.root), [])
        self.assertEqual(ct.main(["--root", str(self.root)]), 0)

    def test_a_folder_entry_stands_for_its_files(self):
        self.assertIn("lock-records/prereg-lock-1.tag", ct.listed(self.root))


if __name__ == "__main__":
    unittest.main()
