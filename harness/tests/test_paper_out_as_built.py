"""An output a copy without the development history cannot rebuild is marked "as built", with the reason, and the build carries on
(D-207; Edith's M5). Components of paper_outputs, exercised on a synthetic folder; the whole build is checked by running it in a package copy."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.analysis import paper_out_core as core
from harness.analysis import paper_outputs as po


class AsBuilt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.out = Path(self.tmp.name) / "out"
        (self.repo / "data/paper-outputs").mkdir(parents=True)
        self.out.mkdir()
        shipped = {"outputs": [{"id": "TAB-07", "status": "built", "title": "shipped title", "sources": {"log": {"path": "LOG.md", "sha256": "ef" * 32}},
                                "files": {"TAB-07.csv": "ab" * 32, "TAB-07.tex": "cd" * 32}}, {"id": "TAB-01", "files": {}}]}
        (self.repo / "data/paper-outputs/MANIFEST.json").write_text(json.dumps(shipped))

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_entry_keeps_the_reason_and_the_shipped_hashes_and_drops_half_written_files(self):
        (self.out / "TAB-01.csv").write_text("kept: another output's file\n")
        before = {f.name for f in self.out.iterdir()}
        (self.out / "TAB-07.csv").write_text("half written\n")
        exc = core.NotShipped("LOG.md (pinned at bec30e3) is not in this copy of the repository\nsecond line")
        e = po._as_built(self.repo, self.out, before, "TAB-07", {"id": "TAB-07", "title": "t"}, exc)
        self.assertEqual((e["status"], e["reason"]), ("as built", "LOG.md (pinned at bec30e3) is not in this copy of the repository"))
        self.assertEqual(e["files"], {"TAB-07.csv": "ab" * 32, "TAB-07.tex": "cd" * 32})
        self.assertEqual(sorted(f.name for f in self.out.iterdir()), ["TAB-01.csv"])

    def test_the_entry_is_the_shipped_one_with_only_status_and_reason_changed(self):
        """Edith's P2: an as-built entry keeps the shipped sources and plan fields, not just the plan fields and the file hashes."""
        exc = core.NotShipped("LOG.md is not in this copy")
        e = po._as_built(self.repo, self.out, set(), "TAB-07", {"id": "TAB-07", "title": "plan title", "module": "m"}, exc)
        shipped = json.loads((self.repo / "data/paper-outputs/MANIFEST.json").read_text())["outputs"][0]
        self.assertEqual({k: v for k, v in e.items() if k not in ("status", "reason", "module")},
                         {k: v for k, v in shipped.items() if k != "status"})
        self.assertEqual(e["sources"], shipped["sources"])
        self.assertEqual(e["module"], "m")

    def test_a_build_without_the_history_refuses_to_write_into_the_shipped_folder(self):
        class S:                                                                # build() asks the store only whether this is disk mode
            from_disk = True
        with self.assertRaises(SystemExit) as r:
            po.build(self.repo, self.repo / "data/paper-outputs", only=["TAB-07"], store=S(), modules=["paper_out_core"])
        self.assertIn("must not write into the shipped data/paper-outputs", str(r.exception))

    def test_the_audit_skips_an_as_built_entry_whose_files_are_not_in_the_folder(self):
        entry = {"id": "TAB-07", "status": "as built", "files": {"TAB-07.cells.json": "ab" * 32}}
        self.assertEqual(po.audit(self.out, None, [entry]), [])

    def test_the_manifest_reading_names_the_count_only_when_there_is_one(self):
        m = {"generator": "g", "plan": {"path": "p", "commit": "c"}, "counts": {"built": 3, "partial": 0, "stub": 0, "todo": 0},
             "outputs": [], "dropped": []}
        self.assertNotIn("as built", po.manifest_md(m))
        m["counts"]["as built"] = 2
        self.assertIn("as built (not rebuilt in this copy; its reason is in MANIFEST.json) 2", po.manifest_md(m))


if __name__ == "__main__":
    unittest.main()
