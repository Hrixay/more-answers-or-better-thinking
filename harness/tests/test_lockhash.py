"""harness.lockhash: the lock manifest's file-hash block (spec lock item 7). Exercised in a throwaway git repository."""

import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import lockhash


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class LockHash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "t")
        (self.root / "a.txt").write_text("alpha\n")
        (self.root / "ops" / "lock").mkdir(parents=True)
        (self.root / lockhash.MANIFEST).write_text(f"# m\n{lockhash.BEGIN}\nnot yet\n{lockhash.END}\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "x")

    def tearDown(self):
        self.tmp.cleanup()

    def run_mode(self, mode):
        return lockhash.main([mode, "--root", str(self.root)])

    def test_write_then_check_then_a_change_is_caught(self):
        self.assertEqual(self.run_mode("write"), 0)
        text = (self.root / lockhash.MANIFEST).read_text()
        self.assertIn("  a.txt", text)
        self.assertNotIn("  " + lockhash.MANIFEST, text)              # the manifest does not hash itself
        git(self.root, "commit", "-q", "-am", "hashes")
        self.assertEqual(self.run_mode("check"), 0)
        (self.root / "a.txt").write_text("beta\n")
        git(self.root, "commit", "-q", "-am", "changed")
        self.assertEqual(self.run_mode("check"), 1)

    def test_released_checks_a_copy_without_git(self):
        (self.root / "b.txt").write_text("bravo\n")
        (self.root / "c.txt").write_text("charlie\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "more")
        self.assertEqual(self.run_mode("write"), 0)
        with tempfile.TemporaryDirectory() as d:                      # the released copy: no .git, one file changed, one not shipped
            copy = Path(d) / "copy"
            shutil.copytree(self.root, copy, ignore=shutil.ignore_patterns(".git"))
            (copy / "b.txt").write_text("changed\n")
            (copy / "c.txt").unlink()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(lockhash.main(["released", "--root", str(copy)]), 0)
            self.assertIn("with the locked bytes: 1; changed since the lock: 1; not in this copy: 1", out.getvalue())
            self.assertIn("changed since the lock: b.txt", out.getvalue())
            m = copy / lockhash.MANIFEST                               # a block whose digest no longer matches its lines
            m.write_text(m.read_text().replace("  a.txt", "  z.txt"))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(lockhash.main(["released", "--root", str(copy)]), 1)

    def test_a_dirty_tree_is_refused(self):
        (self.root / "b.txt").write_text("untracked\n")
        self.assertEqual(self.run_mode("write"), 2)
        self.assertEqual(self.run_mode("check"), 2)

    def test_outside_a_git_repository_check_points_at_released(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            here = os.getcwd()
            os.chdir(d)
            try:
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertEqual(lockhash.main(["check"]), 2)
            finally:
                os.chdir(here)
        self.assertIn("released", err.getvalue())


if __name__ == "__main__":
    unittest.main()
