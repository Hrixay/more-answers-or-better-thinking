"""The never-sent check (Study 1b, Edith F-2): an item is caught by id, by set prefix, by prompt hash under another id, and in other
data files by id or by prompt text. Lock-4 audit A5 / A13: it refuses a scan of no call log and a spend-log run with no call log
(exit 2), and records the commit, each log's SHA-256 and line count, and every folder by its full path. Offline; temp folders only."""

import atexit
import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness.pareto import neversent
from harness.pareto.request import prompt_text


def _write_set(root: Path, set_id: str, prompts):
    d = root / "tasks" / set_id
    d.mkdir(parents=True)
    lines = [json.dumps({"id": f"{set_id}-{i:03d}-6x1", "prompt": p}) for i, p in enumerate(prompts)]
    body = "\n".join(lines) + "\n"
    (d / "items.jsonl").write_text(body)
    (d / "manifest.json").write_text(json.dumps({"set_id": set_id, "items_sha256": hashlib.sha256(body.encode()).hexdigest()}))
    return d


def _log(root: Path, run: str, records):
    d = root / "raw" / run
    d.mkdir(parents=True)
    (d / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))


def _hash(prompt: str) -> str:
    return hashlib.sha256(prompt_text({"messages": [{"role": "user", "content": prompt}]}).encode()).hexdigest()


def _spend_log(root: Path, rows, name: str = "spend-log.md") -> Path:
    """A spend log in ops/spend-log.md's shape: rows of (run id, calls, usd)."""
    total = sum(float(u) for _, _, u in rows)
    body = (f"| Credit | 200.00 |\n| Spent (rows below) | {total:.2f} |\n\n"
            "| Date | Chat | Run ID | What ran | Calls | Tokens in / out / cache | USD (computed) | Console check | Notes |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            + "".join(f"| 2026-10-01 | Friday | {r} | test | {c} | 0 / 0 / 0 | {u} | - | - |\n" for r, c, u in rows))
    p = root / name
    p.write_text(body)
    return p


class NeverSent(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        atexit.register(shutil.rmtree, self.root, True)
        self.fresh = _write_set(self.root, "fresh-v1", ["Fresh prompt zero.", "Fresh prompt one."])
        self.used = _write_set(self.root, "used-v1", ["Used prompt zero."])
        self.other = _write_set(self.root, "other-v1", ["Other prompt zero."])
        self.reused = _write_set(self.root, "reused-v1", ["Reused prompt zero."])
        self.freeread = _write_set(self.root, "freeread-v1", ["Read by a helper."])
        _log(self.root, "run-a", [
            {"custom_id": "used-v1-000-6x1-hm-01", "final": True, "prompt_sha256": _hash("Used prompt zero."), "answer_text": "x"},
            {"custom_id": "elsewhere-000-6x1-hm-01", "final": True, "prompt_sha256": _hash("Reused prompt zero.")},
            {"kind": "batch_submitting", "keys": {"other-v1-999-6x1-om-01": 1}},
        ])
        (self.root / "free").mkdir()
        (self.root / "free" / "read.md").write_text("The helper read: Read by a helper.\n")

    def test_each_way_of_being_sent_is_caught(self):
        res = neversent.check([self.fresh, self.used, self.other, self.reused, self.freeread], self.root / "raw", self.root)
        s = res["sets"]
        self.assertTrue(s["fresh-v1"]["never_sent"] and s["fresh-v1"]["never_in_other_files"])
        self.assertTrue(s["fresh-v1"]["items_sha256_matches_manifest"])
        self.assertEqual(s["used-v1"]["sent_by_id"]["first"], [["run-a", "used-v1-000-6x1-hm-01"]])
        self.assertEqual(s["used-v1"]["sent_by_prompt_hash"]["first"], [["run-a", "used-v1-000-6x1"]])
        self.assertEqual(s["other-v1"]["sent_under_set_prefix"]["first"], [["run-a", "other-v1-999-6x1-om-01"]])    # a batch key, never final
        self.assertEqual(s["reused-v1"]["sent_by_prompt_hash"]["first"], [["run-a", "reused-v1-000-6x1"]])          # same prompt, other id
        self.assertFalse(s["reused-v1"]["never_sent"])
        self.assertTrue(s["freeread-v1"]["never_sent"])
        self.assertEqual(s["freeread-v1"]["in_other_data_files"]["first"], [[f"{self.root}/free/read.md", "freeread-v1-000-6x1"]])
        self.assertEqual(s["used-v1"]["in_other_data_files"]["count"], 0)        # "used-v1" inside "reused-v1" is not a match

    def test_also_folders_are_searched(self):
        extra = self.root.parent / (self.root.name + "-research")
        extra.mkdir()
        atexit.register(shutil.rmtree, extra, True)
        (extra / "check.md").write_text("A wording check quoted fresh-v1-001-6x1.\n")
        res = neversent.check([self.fresh], self.root / "raw", self.root, [extra])
        self.assertEqual(res["sets"]["fresh-v1"]["in_other_data_files"]["first"], [[f"{extra}/check.md", "fresh-v1-001-6x1"]])
        self.assertFalse(res["sets"]["fresh-v1"]["never_in_other_files"])
        (extra / "check.md").write_text("The plan names fresh-v1 only.\n")                       # a mention, not a read
        res = neversent.check([self.fresh], self.root / "raw", self.root, [extra])
        self.assertTrue(res["sets"]["fresh-v1"]["never_in_other_files"])
        self.assertEqual(res["sets"]["fresh-v1"]["set_id_mentioned_in"]["first"], [[f"{extra}/check.md", "fresh-v1"]])
        self.assertTrue(res["sets"]["fresh-v1"]["never_sent"])

    def main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            code = neversent.main(argv)
        return code, err.getvalue()

    def test_cli_exit_code(self):
        out = self.root / "res.json"
        log = _spend_log(self.root, [("run-a", "3", "0.10")])
        base = ["--raw", str(self.root / "raw"), "--data", str(self.root), "--spend-log", str(log), "--out", str(out)]
        self.assertEqual(self.main(["--sets", str(self.fresh)] + base)[0], 0)
        self.assertEqual(self.main(["--sets", str(self.used)] + base)[0], 1)

    @unittest.skipUnless(subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "HEAD"], capture_output=True).returncode == 0,
                         "the released package has no git history to name a commit from")
    def test_record_names_commit_log_hashes_and_full_folders(self):
        """A13: the commit it ran from, each call log's SHA-256 and line count, every folder searched by its full path; two folders
        with the same name (two `research` roots) are both kept."""
        a, b = self.root / "a" / "research", self.root / "b" / "research"
        for d, text in ((a, "fresh-v1-000-6x1 seen in a\n"), (b, "fresh-v1-001-6x1 seen in b\n")):
            d.mkdir(parents=True)
            (d / "note.md").write_text(text)
        res = neversent.check([self.fresh], self.root / "raw", self.root / "free", [a, b], _spend_log(self.root, [("run-a", "3", "0.1")]))
        logf = self.root / "raw" / "run-a" / "calls.jsonl"
        self.assertEqual(res["runs_scanned"]["run-a"]["sha256"], hashlib.sha256(logf.read_bytes()).hexdigest())
        self.assertEqual(res["runs_scanned"]["run-a"]["lines"], 3)
        self.assertEqual(res["runs_scanned"]["run-a"]["path"], str(logf))
        self.assertRegex(res["ran_from"]["commit"] or "", r"^[0-9a-f]{40}$")
        self.assertIn(res["ran_from"]["tree_clean"], (True, False))
        self.assertEqual(res["folders_searched"], [str(self.root / "free"), str(a), str(b)])
        self.assertEqual(sorted(x[0] for x in res["sets"]["fresh-v1"]["in_other_data_files"]["first"]),
                         [f"{a}/note.md", f"{b}/note.md"])                                      # no collision under "research"
        self.assertEqual(res["spend_log"]["runs_with_calls"], ["run-a"])

    def test_refuses_with_no_call_log(self):
        """A5: a missing --raw, or one with no */calls.jsonl, is refused (exit 2, nothing written), never read as 'never sent'."""
        out = self.root / "res.json"
        empty = self.root / "empty-raw"
        empty.mkdir()
        (empty / "run-x").mkdir()                                                    # a run folder with no calls.jsonl
        for raw in (self.root / "no-such-raw", empty):
            code, err = self.main(["--sets", str(self.fresh), "--raw", str(raw), "--data", str(self.root),
                                   "--spend-log", str(_spend_log(self.root, [])), "--out", str(out)])
            self.assertEqual(code, 2, raw)
            self.assertIn("REFUSED", err)
            self.assertFalse(out.exists())
        with self.assertRaises(neversent.NothingToScan):
            neversent.check([self.fresh], empty, self.root)

    def test_refuses_a_spend_log_run_without_its_call_log(self):
        """A5: a run with calls in the spend log must have <raw>/<run id>/calls.jsonl; a 0-call bookkeeping row ('run-a (markers)')
        needs none and maps to its run; a log not in the spend log is scanned and listed."""
        out = self.root / "res.json"
        ok = _spend_log(self.root, [("run-a", "3", "0.10"), ("run-a (markers)", "0", "0.00")])
        code, _ = self.main(["--sets", str(self.fresh), "--raw", str(self.root / "raw"), "--data", str(self.root),
                             "--spend-log", str(ok), "--out", str(out)])
        self.assertEqual(code, 0)
        rec = json.loads(out.read_text())
        self.assertEqual(rec["spend_log"]["runs_with_calls"], ["run-a"])
        self.assertEqual(rec["spend_log"]["bookkeeping_rows"], ["run-a (markers)"])
        out.unlink()
        _log(self.root, "dry-run-z", [{"custom_id": "zzz-000-6x1-hm-01", "final": True}])
        gone = _spend_log(self.root, [("run-a", "3", "0.10"), ("run-b", "1", "0.00"), ("run-c (markers)", "0", "0.00")], "gone.md")
        code, err = self.main(["--sets", str(self.fresh), "--raw", str(self.root / "raw"), "--data", str(self.root),
                               "--spend-log", str(gone), "--out", str(out)])
        self.assertEqual(code, 2)
        self.assertIn("run-b", err)
        self.assertNotIn("run-c", err)                                                # bookkeeping only: no log needed
        self.assertFalse(out.exists())
        res = neversent.check([self.fresh], self.root / "raw", self.root, (), ok)
        self.assertEqual(res["spend_log"]["runs_scanned_not_in_spend_log"], ["dry-run-z"])

    def test_the_real_spend_log_names_the_eight_runs(self):
        """The repository's spend log as read here: the eight runs with calls Edith's A5 check expects; smoke-2's marker row is
        bookkeeping only."""
        got = neversent.spend_log_runs(neversent.ROOT / "ops" / "spend-log.md")
        self.assertTrue({"check-ledger-1", "diag-haiku-effort-1", "ladder-l14n-1", "main-l14n6-1", "pilot-ledger-1", "s3-ledger-1",
                         "smoke-1", "smoke-2"} <= set(got["runs"]))
        self.assertIn("smoke-2 (markers)", got["bookkeeping_rows"])


if __name__ == "__main__":
    unittest.main()
