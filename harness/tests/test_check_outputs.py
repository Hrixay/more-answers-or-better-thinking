"""Tests for harness/analysis/check_outputs.py (D-207): the manifest's files and pinned sources are counted on a synthetic folder."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from harness.analysis import check_outputs as co


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data/paper-outputs").mkdir(parents=True)
        (self.root / "data/in.json").write_text("{}")
        (self.root / "data/paper-outputs/A.csv").write_text("a\n")
        (self.root / "data/paper-outputs/B.csv").write_text("b\n")
        src = lambda path, b: {"commit": "abc1234", "path": path, "sha256": sha(b)}
        self.manifest = {"outputs": [
            {"id": "A", "files": {"A.csv": sha(b"a\n")}, "sources": {"x": src("data/in.json", b"{}")}},
            {"id": "B", "files": {"B.csv": sha(b"b\n")}, "sources": {"y": src("private/log.md", b"log")}}],
            "plan": src("data/in.json", b"{}")}
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        (self.root / "data/paper-outputs/MANIFEST.json").write_text(json.dumps(self.manifest))

    def test_counts_and_which_outputs_rebuild(self):
        r = co.check(self.root)
        self.assertEqual((r["files_ok"], r["files_different"], r["files_missing"]), (2, [], []))
        self.assertEqual(r["rebuilds_here"], ["A"])
        self.assertEqual(r["ships_as_built"], {"B": ["private/log.md"]})
        self.assertEqual(r["sources_absent"], ["private/log.md"])
        self.assertEqual(co.main(["--root", str(self.root)]), 0)

    def test_a_changed_output_file_fails_and_a_changed_source_fails_only_when_strict(self):
        (self.root / "data/paper-outputs/A.csv").write_text("tampered\n")
        self.assertEqual(co.main(["--root", str(self.root)]), 1)
        (self.root / "data/paper-outputs/A.csv").write_text("a\n")
        (self.root / "data/in.json").write_text("{ }")
        self.assertEqual(co.check(self.root)["sources_different"], ["data/in.json"])
        self.assertEqual(co.check(self.root)["rebuilds_here"], [])
        self.assertEqual(co.main(["--root", str(self.root)]), 0)
        self.assertEqual(co.main(["--root", str(self.root), "--strict"]), 1)

    def test_a_missing_output_file_fails(self):
        (self.root / "data/paper-outputs/B.csv").unlink()
        self.assertEqual(co.check(self.root)["files_missing"], ["B.csv"])
        self.assertEqual(co.main(["--root", str(self.root)]), 1)


    def test_an_output_marked_as_built_ships_as_built_even_when_its_sources_are_present(self):
        """Edith's P2: the status, not the sources alone, says what ships as built; its files are checked in the shipped folder."""
        self.manifest["outputs"][0]["status"] = "as built"
        self.write()
        r = co.check(self.root)
        self.assertEqual((r["rebuilds_here"], r["ships_as_built"]), ([], {"A": [], "B": ["private/log.md"]}))
        fresh = self.root / "fresh"                                             # a rebuild folder: the as-built output's files are not in it
        fresh.mkdir()
        (fresh / "B.csv").write_text("b\n")
        shutil.copy(self.root / "data/paper-outputs/MANIFEST.json", fresh / "MANIFEST.json")
        r = co.check(self.root, fresh)
        self.assertEqual((r["files_missing"], r["files_different"]), ([], []))
        (self.root / "data/paper-outputs/A.csv").write_text("tampered\n")        # and the shipped bytes are the ones checked
        self.assertEqual(co.check(self.root, fresh)["files_different"], ["A.csv"])


if __name__ == "__main__":
    unittest.main()
