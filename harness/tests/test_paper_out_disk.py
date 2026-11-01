"""paper_out_core's disk mode (D-207: the public copy has no development history): pinned files read from their paths, SHA-256 checked
as in git mode. Exercised on a throwaway git repository and a plain copy of its files. No network."""

import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness.analysis import paper_out_core as core
from harness.analysis.paper_out_core import NeedsHistory, NotShipped, Source, SourceMismatch, Store

BODY = b'{"a": {"b": [1, 2, 3]}}\n'


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def new_repo(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.invalid")
    git(root, "config", "user.name", "t")


class DiskMode(unittest.TestCase):
    def setUp(self):
        core._DETECTED.clear()
        core._FORCED.clear()
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo, self.copy = base / "repo", base / "copy"
        self.repo.mkdir()
        new_repo(self.repo)
        (self.repo / "d").mkdir()
        (self.repo / "d" / "x.json").write_bytes(BODY)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "x")
        self.commit = git(self.repo, "rev-parse", "--short=7", "HEAD")
        self.src = {"x": Source("x", "d/x.json", self.commit, hashlib.sha256(BODY).hexdigest())}
        shutil.copytree(self.repo, self.copy, ignore=shutil.ignore_patterns(".git"))   # the fresh copy: the files, no history
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop(core.FROM_DISK_ENV, None)
        self.addCleanup(env.stop)

    def tearDown(self):
        core._DETECTED.clear()
        core._FORCED.clear()
        self.tmp.cleanup()

    def store(self, repo):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            S = Store(repo, self.src)
        return S, err.getvalue()

    def test_default_with_history_reads_the_commit(self):
        S, err = self.store(self.repo)
        self.assertFalse(S.from_disk)
        self.assertEqual(err, "")
        (self.repo / "d" / "x.json").write_bytes(b"{}\n")            # the working tree never matters in git mode
        self.assertEqual(S.get("x", "a.b.2"), 3)

    def test_disk_mode_reads_the_same_bytes_as_git_mode(self):
        G, _ = self.store(self.repo)
        D, err = self.store(self.copy)
        self.assertTrue(D.from_disk)
        self.assertEqual(D.doc("x"), G.doc("x"))
        self.assertEqual(D.ref("x", "@commit").value, self.commit)    # the pinned commit stays, as provenance
        self.assertIn("1 pinned commit(s) not in this repository", err)
        self.assertEqual(len(err.splitlines()), 1)
        _, again = self.store(self.copy)                               # said once per repository
        self.assertEqual(again, "")

    def test_a_tampered_file_is_refused_in_disk_mode(self):
        (self.copy / "d" / "x.json").write_bytes(BODY.replace(b"3", b"4"))
        D, _ = self.store(self.copy)
        with self.assertRaises(SourceMismatch) as cm:
            D.doc("x")
        self.assertIn("d/x.json on disk (pinned at", str(cm.exception))

    def test_a_missing_file_names_the_file_and_says_it_is_not_shipped(self):
        (self.copy / "d" / "x.json").unlink()
        D, _ = self.store(self.copy)
        with self.assertRaises(NotShipped) as cm:
            D.doc("x")
        self.assertIn("d/x.json", str(cm.exception))
        self.assertIn("does not ship it", str(cm.exception))
        self.assertNotIsInstance(cm.exception, FileNotFoundError)

    def test_a_copy_with_its_own_one_commit_history_is_detected(self):
        new_repo(self.copy)
        git(self.copy, "add", "-A")
        git(self.copy, "commit", "-q", "-m", "fresh copy")
        D, err = self.store(self.copy)
        self.assertTrue(D.from_disk)
        self.assertIn(self.commit, err)
        self.assertEqual(D.get("x", "a.b.0"), 1)

    def test_asked_for_by_the_environment_or_the_flag(self):
        (self.repo / "d" / "x.json").write_bytes(b"{}\n")            # disk mode on the full repository reads the working tree
        os.environ[core.FROM_DISK_ENV] = "1"
        S, err = self.store(self.repo)
        self.assertTrue(S.from_disk)
        self.assertEqual(err, "")
        with self.assertRaises(SourceMismatch):
            S.doc("x")
        os.environ[core.FROM_DISK_ENV] = "0"
        self.assertFalse(self.store(self.repo)[0].from_disk)
        core.set_from_disk(self.repo)
        self.assertTrue(self.store(self.repo)[0].from_disk)

    def test_a_custom_reader_is_never_disk_mode(self):
        self.assertFalse(Store(self.copy, self.src, reader=lambda s: BODY).from_disk)

    def test_tool_pins_read_the_same_bytes_both_ways(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(core.pinned_bytes(self.repo, self.commit, "d/x.json"), BODY)
            self.assertEqual(core.pinned_bytes(self.copy, self.commit, "d/x.json"), BODY)
            with self.assertRaises(NotShipped):
                core.pinned_bytes(self.copy, self.commit, "d/none.py")

    def test_history_checks_refuse_in_disk_mode_only(self):
        G, _ = self.store(self.repo)
        core.need_history(G, "a check")                               # git mode: nothing to refuse
        D, _ = self.store(self.copy)
        with self.assertRaises(NeedsHistory) as cm:
            core.need_history(D, "TAB-99's check")
        self.assertIn("TAB-99's check needs the development history", str(cm.exception))
        self.assertIn("MANIFEST.json", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
