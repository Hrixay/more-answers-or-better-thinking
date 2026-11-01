"""Offline tests of the S3 check Batch command (harness/pareto/s3check.py). DryTransport and FakeTransport only: no API call."""

import contextlib
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from harness.pareto import s3check
from harness.pareto.calllog import CallLog
from harness.pareto.prices import estimate_input_tokens, worst_case
from harness.pareto.request import prompt_text
from harness.pareto.transport import DryTransport, FakeTransport, TransportError
from harness.taskgen import freeze
from harness.pareto import prices
from harness.tests.fakes import LiveEnv, _noon, guard, reply

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "check-ledger-test-v1"     # 5 base x 2 shapes, ledger (read only)
SECRET = "Answer: 1 = [4242, 4343] SECRET-ANSWER-TEXT"                                 # must never reach the summary


def setUpModule():
    """load_set verifies a ledger set in depth (minutes); these tests are about the S3 command, so that part is switched off,
    as in test_apicheck.py. The fixture stands in for smoke3-ledger-l16-v1 only where a test says so (`as_s3`)."""
    global _PATCH
    _PATCH = mock.patch.object(freeze, "_verify_ledger_item", lambda item, *a, **k: None)
    _PATCH.start()


def tearDownModule():
    _PATCH.stop()


def as_s3():
    """Let the fixture pass the set check (its id and setting differ from the real S3 set)."""
    return mock.patch.multiple(s3check, S3_SET_ID="check-ledger-test-v1", S3_SETTING="l14")


def fake():
    return FakeTransport(lambda p: reply(model=p["model"], text=SECRET, tout=7000))


def run(g, t, out):
    with as_s3():
        return s3check.run_s3(g, t, out, FIXTURE, sleep=lambda s: None)


class Plan(unittest.TestCase):
    def test_five_items_in_order_with_models_and_15000_tokens(self):
        with as_s3():
            man, items = s3check.load_set(FIXTURE)
            reqs = s3check.build_s3(man, items)
        self.assertEqual(len(reqs), 5)
        got = [(m["base_index"], f"{m['width']}x{m['depth']}", p["model"]) for _, p, m in reqs]
        self.assertEqual(got, [(0, "1x24", "claude-opus-5-5"), (0, "24x1", "claude-opus-5-5"), (1, "1x24", "claude-opus-5-5"),
                               (2, "1x24", "claude-sonnet-5-5"), (2, "24x1", "claude-sonnet-5-5")])
        for cid, p, m in reqs:
            self.assertEqual(p["max_tokens"], 15_000)
            self.assertEqual(p["output_config"], {"effort": "medium"})
            self.assertEqual(p["thinking"], {"type": "adaptive"})
            self.assertIn(m["item_id"], cid)                                  # the full item id (Edith N57)
            self.assertLessEqual(len(cid), 64)
        self.assertEqual(len({c for c, _, _ in reqs}), 5)

    def test_plan_prints_each_worst_case_and_the_total_as_the_guard_reserves_it(self):
        with as_s3():
            man, items = s3check.load_set(FIXTURE)
            reqs = s3check.build_s3(man, items)
        pl = s3check.plan(reqs)
        want = [worst_case(p["model"], estimate_input_tokens(prompt_text(p)), 15_000, batch=True) for _, p, _ in reqs]
        self.assertEqual([Decimal(r["worst_case_batch_usd"]) for r in pl["items"]], want)
        self.assertEqual(Decimal(pl["total_worst_case_batch_usd"]), sum(want, Decimal("0")))
        self.assertGreaterEqual(Decimal(pl["cap_to_ask_for_usd"]), Decimal(pl["total_worst_case_batch_usd"]))
        self.assertLess(Decimal(pl["total_worst_case_batch_usd"]), Decimal("1"))          # under the $1 unchecked limit
        self.assertEqual([r["max_tokens"] for r in pl["items"]], [15_000] * 5)

    def test_plan_command_prints_the_items(self):
        buf = io.StringIO()
        with as_s3(), contextlib.redirect_stdout(buf):
            self.assertEqual(s3check.main(["plan", "--set", str(FIXTURE)]), 0)
        pl = json.loads(buf.getvalue())
        self.assertEqual(pl["batch_requests"], 5)


class WrongSet(unittest.TestCase):
    def test_a_set_that_is_not_smoke3_is_refused(self):
        man, items = s3check.load_set(FIXTURE)                                # check-ledger-test-v1, unpatched
        with self.assertRaises(ValueError):
            s3check.build_s3(man, items)
        with self.assertRaises(ValueError):
            s3check.main(["plan", "--set", str(FIXTURE)])
        t = DryTransport()
        with self.assertRaises(ValueError):
            s3check.run_s3(guard(run_cap="1"), t, Path(tempfile.mkdtemp()), FIXTURE)
        self.assertEqual(t._batches, {})

    def test_wrong_family_or_setting_is_refused(self):
        man, items = s3check.load_set(FIXTURE)
        for bad in (dict(man, set_id=s3check.S3_SET_ID, family="digits"), dict(man, set_id=s3check.S3_SET_ID, setting="l14")):
            with self.assertRaises(ValueError):
                s3check.build_s3(bad, items)


class DryRun(unittest.TestCase):
    def test_end_to_end_one_batch_and_a_summary_without_answer_text(self):
        out = Path(tempfile.mkdtemp())
        t = fake()
        r = run(guard(run_cap="1"), t, out)
        self.assertEqual((r["status"], r["items_planned"], r["items_sent"]), ("complete", 5, 5))
        self.assertEqual(len(t.batches), 1)                                   # ONE Batch
        self.assertEqual(len(next(iter(t.batches.values()))), 5)
        self.assertEqual(t.sent, [])                                          # no real-time call
        self.assertEqual(r["kinds"], {"answered": 5})
        self.assertEqual(r["batch_ids"], ["fake-batch-1"])
        self.assertGreater(Decimal(r["spent_usd"]), 0)
        text = (out / "s3_result.json").read_text()
        self.assertNotIn("SECRET-ANSWER-TEXT", text)
        self.assertNotIn("answer_text", text)
        self.assertIn("pilot console-check", r["next"])
        self.assertIn("PILOT's own run id", r["next"])

    def test_dry_command_writes_the_summary_and_prints_no_answer(self):
        out = Path(tempfile.mkdtemp()) / "s3"
        buf = io.StringIO()
        with as_s3(), contextlib.redirect_stdout(buf):
            self.assertEqual(s3check.main(["dry", "--set", str(FIXTURE), "--run-id", "s3-dry", "--out", str(out)]), 0)
        self.assertEqual(json.loads((out / "s3_result.json").read_text())["status"], "complete")
        self.assertNotIn("DRY RUN", buf.getvalue())                         # DryTransport's reply text
        self.assertNotIn("DRY RUN", (out / "s3_result.json").read_text())

    def test_refusals_and_truncations_are_counted_not_graded(self):
        def r(p):
            if "sonnet" in p["model"]:
                return reply(model=p["model"], stop="max_tokens", text=SECRET, tout=15000)
            return reply(model=p["model"], stop="refusal", category="cyber", text=None, tout=0)
        res = run(guard(run_cap="1"), FakeTransport(r), Path(tempfile.mkdtemp()))
        self.assertEqual(res["status"], "complete")
        self.assertEqual(res["kinds"], {"refusal": 3, "truncated": 2})

    def test_a_cap_too_small_for_one_batch_sends_nothing(self):
        out = Path(tempfile.mkdtemp())
        t = fake()
        r = run(guard(run_cap="0.30"), t, out)
        self.assertEqual((r["status"], r["items_sent"]), ("not_sent", 0))
        self.assertEqual(t.batches, {})
        self.assertFalse((out / "manifest.json").exists())
        r2 = run(guard(run_cap="1"), fake(), out)                            # nothing went out, so a run with the right cap may go
        self.assertEqual(r2["status"], "complete")

    def test_a_failed_submit_is_incomplete_and_recorded(self):
        class Fails(FakeTransport):
            def submit_batch(self, requests):
                raise TransportError("server", "overloaded", billed="unknown", status=529)
        out = Path(tempfile.mkdtemp())
        r = run(guard(run_cap="1"), Fails(lambda p: reply(model=p["model"])), out)
        self.assertEqual(r["status"], "incomplete")
        with self.assertRaises(s3check.S3NotRerun):                          # the submit may have gone out: never again
            run(guard(run_cap="1"), fake(), out)


class Rerun(unittest.TestCase):
    def test_a_rerun_into_a_folder_with_finished_items_is_refused(self):
        out = Path(tempfile.mkdtemp())
        run(guard(run_cap="1"), fake(), out)
        t2 = fake()
        with self.assertRaises(s3check.S3NotRerun):
            run(guard(run_cap="1"), t2, out)
        self.assertEqual(t2.batches, {})

    def test_a_batch_submit_record_alone_is_refused(self):
        out = Path(tempfile.mkdtemp())
        CallLog(out / "calls.jsonl").write({"kind": "batch_submitted", "run_id": "test-run", "wave_id": "w1",
                                            "batch_id": "msgbatch_x", "keys": {}, "final": False})
        t = fake()
        with self.assertRaises(s3check.S3NotRerun):
            run(guard(run_cap="1"), t, out)
        self.assertEqual(t.batches, {})

    def test_a_ledger_reservation_for_an_item_is_refused(self):
        with as_s3():
            man, items = s3check.load_set(FIXTURE)
            cid, p, _ = s3check.build_s3(man, items)[0]
        g = guard(run_cap="1")
        g.reserve(f"{cid}@1", p["model"], 100, 100, batch=True)
        t = fake()
        with self.assertRaises(s3check.S3NotRerun):
            run(g, t, Path(tempfile.mkdtemp()))
        self.assertEqual(t.batches, {})

    def test_a_result_file_with_items_sent_is_refused(self):
        out = Path(tempfile.mkdtemp())
        (out / "s3_result.json").write_text(json.dumps({"status": "complete", "items_sent": 5}))
        with self.assertRaises(s3check.S3NotRerun):
            run(guard(run_cap="1"), fake(), out)

    def test_dry_command_reports_not_sent_on_a_rerun(self):
        out = Path(tempfile.mkdtemp()) / "s3"
        args = ["dry", "--set", str(FIXTURE), "--run-id", "s3-dry", "--out", str(out)]
        with as_s3(), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(s3check.main(args), 0)
            self.assertEqual(s3check.main(args), 4)


class LiveArgs(unittest.TestCase):
    def _refused(self, args):
        with mock.patch("harness.pareto.live.open_live_guard", side_effect=AssertionError("must not open a live guard")), \
                mock.patch.object(s3check, "load_set", side_effect=AssertionError("must not load the set")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                s3check.main(args)

    def test_live_needs_cap_and_clearance_and_refuses_out(self):
        base = ["live", "--set", str(FIXTURE), "--run-id", "s3-x"]
        self._refused(base)
        self._refused(base + ["--cap", "0.7"])
        self._refused(base + ["--clearance", "c.json"])
        self._refused(base + ["--cap", "0.7", "--clearance", "c.json", "--out", "somewhere"])


class NoConsoleCheck(unittest.TestCase):
    """Edith N67: s3check never records a Console check; the pilot records it under its own run id."""

    def _events(self, ledger):
        return [json.loads(ln)["event"] for ln in Path(ledger).read_text().splitlines() if ln.strip()]

    def test_a_dry_run_writes_no_console_check_event(self):
        d = Path(tempfile.mkdtemp())
        g = guard(run_cap="1", ledger_path=d / "ledger.jsonl")
        try:
            run(g, fake(), d)
        finally:
            g.close()
        ev = self._events(d / "ledger.jsonl")
        self.assertIn("commit", ev)
        self.assertFalse([e for e in ev if e.startswith("console")])

    def test_a_live_guard_with_a_fake_live_transport_writes_no_console_check_event(self):
        class LiveFake(FakeTransport):
            live = True                                                       # still a fake: nothing leaves the machine
        env = LiveEnv(run_id="s3-live-test", cap="1")
        g = env.guard()
        folder = env.data / "raw" / "s3-live-test"
        try:
            r = run(g, LiveFake(lambda p: reply(model=p["model"], text=SECRET, tout=7000)), folder)
        finally:
            g.close()
        self.assertEqual(r["status"], "complete")
        ev = self._events(folder / "ledger.jsonl")
        self.assertFalse([e for e in ev if e.startswith("console")])
        self.assertNotIn("SECRET-ANSWER-TEXT", (folder / "s3_result.json").read_text())

    def test_the_code_never_calls_the_console_check(self):
        src = Path(s3check.__file__).read_text()
        for name in ("record_console_check(", "clear_console_block(", "console-check --run-id"):
            self.assertNotIn(name, src)


class PollInterrupted(FakeTransport):
    """Answers like FakeTransport, but the first poll raises (Ctrl-C), as an interruption while waiting would."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.raised = False

    def batch_status(self, batch_id):
        if not self.raised:
            self.raised = True
            raise KeyboardInterrupt("poll interrupted")
        return {"processing_status": "ended", "request_counts": {}}


def collect(g, t, out):
    with as_s3():
        return s3check.run_s3(g, t, out, FIXTURE, sleep=lambda s: None, collect=True)


def submit_count(out):
    return sum(1 for r in CallLog(out / "calls.jsonl").records() if r.get("kind") == "batch_submitting")


class Collect(unittest.TestCase):
    """Edith S3-1: an interruption while polling must not leave the Batch uncollectable; --collect never submits."""

    def test_interrupt_during_poll_then_collect(self):
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="1")
        t = PollInterrupted(lambda p: reply(model=p["model"], text=SECRET, tout=7000))
        with self.assertRaises(KeyboardInterrupt):
            run(g, t, out)
        first = json.loads((out / "s3_result.json").read_text())
        self.assertEqual((first["status"], first["items_sent"], first["items_with_result"]), ("interrupted", 5, 0))
        with self.assertRaises(s3check.S3NotRerun) as cm:                    # plain re-run: refused, points to --collect
            run(g, t, out)
        self.assertIn("--collect", str(cm.exception))
        r = collect(g, t, out)
        self.assertEqual(len(t.batches), 1)                                   # one submit in all
        self.assertEqual(submit_count(out), 1)
        self.assertEqual((r["status"], r["items_with_result"], r["kinds"]), ("complete", 5, {"answered": 5}))
        self.assertEqual(json.loads((out / "s3_result.json").read_text())["status"], "complete")
        self.assertEqual(g.open_keys(), set())
        self.assertNotIn("SECRET-ANSWER-TEXT", (out / "s3_result.json").read_text())
        with self.assertRaises(s3check.S3NotRerun):                          # collected: nothing left to collect
            collect(g, t, out)

    def test_interrupt_then_collect_with_a_replayed_live_ledger(self):
        from datetime import datetime, timezone
        from harness.pareto.live import open_live_guard

        class LiveInterrupted(PollInterrupted):
            live = True                                                       # still a fake: nothing leaves the machine
        env = LiveEnv(run_id="s3-live-collect", cap="1")
        env.write_clearance()
        roots = dict(data_root=env.data, repo_root=env.root, git=lambda a: "abc1234\n" if a[0] == "rev-parse" else "",
                     now=lambda: _noon(prices.PRICE_TABLE_DATE))
        t = LiveInterrupted(lambda p: reply(model=p["model"], tout=7000))
        g, folder = open_live_guard("s3-live-collect", Decimal("1"), env.clearance_path, **roots)
        try:
            with self.assertRaises(KeyboardInterrupt):
                run(g, t, folder)
        finally:
            g.close()
        g2, _ = open_live_guard("s3-live-collect", Decimal("1"), env.clearance_path, **roots)     # replayed
        try:
            self.assertEqual(len(g2.open_keys()), 5)
            r = collect(g2, t, folder)
            self.assertEqual(r["status"], "complete")
            self.assertEqual(g2.open_keys(), set())
            self.assertGreater(g2.spent, 0)                                   # the cost reached the ledger
        finally:
            g2.close()
        self.assertEqual(len(t.batches), 1)

    def test_network_drops_after_two_results_then_collect_pays_nothing_twice(self):
        """Edith S3-3: the connection drops while results are read; 2 of 5 are committed, no batch_collected line."""
        from datetime import datetime, timezone
        from harness.pareto.live import open_live_guard
        from harness.pareto.prices import Usage, cost

        class Drops(FakeTransport):
            live = True                                                       # still a fake: nothing leaves the machine
            dropped = False

            def batch_status(self, batch_id):
                return {"processing_status": "ended", "request_counts": {}}

            def batch_results(self, batch_id):
                for n, res in enumerate(super().batch_results(batch_id)):
                    if n == 2 and not self.dropped:
                        self.dropped = True
                        raise ConnectionError("network dropped")
                    yield res
        env = LiveEnv(run_id="s3-live-drop", cap="1")
        env.write_clearance()
        roots = dict(data_root=env.data, repo_root=env.root, git=lambda a: "abc1234\n" if a[0] == "rev-parse" else "",
                     now=lambda: _noon(prices.PRICE_TABLE_DATE))
        t = Drops(lambda p: reply(model=p["model"], tin=3000, tout=7000))
        g, folder = open_live_guard("s3-live-drop", Decimal("1"), env.clearance_path, **roots)
        try:
            with self.assertRaises(ConnectionError):
                run(g, t, folder)
            # results are fetched WHOLE before any is recorded (batch._read, resume fix 522d1cc): a drop while reading records none
            self.assertEqual(len(g.open_keys()), 5)                           # none committed, all 5 still open
        finally:
            g.close()
        log = CallLog(folder / "calls.jsonl")
        self.assertEqual(len(log.finished_ids()), 0)
        self.assertFalse([r for r in log.records() if r.get("kind") == "batch_collected"])
        self.assertEqual(json.loads((folder / "s3_result.json").read_text())["status"], "interrupted")
        g2, _ = open_live_guard("s3-live-drop", Decimal("1"), env.clearance_path, **roots)    # replayed
        try:
            r = collect(g2, t, folder)
            spent = g2.spent
            self.assertEqual(g2.open_keys(), set())
        finally:
            g2.close()
        self.assertEqual((r["status"], r["items_with_result"]), ("complete", 5))
        self.assertEqual((len(t.batches), submit_count(folder)), (1, 1))      # one submit in all
        finals = [rec["custom_id"] for rec in log.records() if rec.get("final")]
        self.assertEqual(sorted(finals), sorted(set(finals)))                 # one result line per item
        self.assertEqual(len(finals), 5)
        want = sum((cost(p["model"], Usage(input_tokens=3000, output_tokens=7000), batch=True)
                    for p in (rq["params"] for rq in t.batches["fake-batch-1"])), Decimal("0"))
        self.assertEqual(spent, want)                                         # the five items' costs, nothing paid twice
        with self.assertRaises(s3check.S3NotRerun):                          # marked collected: refused from now on
            g3, _ = open_live_guard("s3-live-drop", Decimal("1"), env.clearance_path, **roots)
            try:
                collect(g3, t, folder)
            finally:
                g3.close()

    def test_collect_with_no_batch_is_refused(self):
        t = fake()
        with self.assertRaises(s3check.S3NotRerun):
            collect(guard(run_cap="1"), t, Path(tempfile.mkdtemp()))
        self.assertEqual(t.batches, {})

    def test_collect_after_a_complete_run_is_refused(self):
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="1")
        run(g, fake(), out)
        t = fake()
        with self.assertRaises(s3check.S3NotRerun):
            collect(g, t, out)
        self.assertEqual((t.batches, submit_count(out)), ({}, 1))

    def _cids(self):
        with as_s3():
            man, items = s3check.load_set(FIXTURE)
            return [c for c, _, _ in s3check.build_s3(man, items)]

    def test_collect_with_an_orphan_is_refused(self):
        out = Path(tempfile.mkdtemp())
        keys = {c: f"{c}@1" for c in self._cids()}
        CallLog(out / "calls.jsonl").write({"kind": "batch_submitting", "run_id": "test-run", "wave_id": "test-run-w1",
                                            "mode": "dry", "keys": keys, "final": False})
        t = fake()
        with self.assertRaises(s3check.S3NotRerun) as cm:
            collect(guard(run_cap="1"), t, out)
        self.assertIn("orphan", str(cm.exception))
        with self.assertRaises(s3check.S3NotRerun):
            run(guard(run_cap="1"), t, out)
        self.assertEqual(t.batches, {})

    def test_collect_of_a_batch_that_is_not_exactly_the_five_items_is_refused(self):
        out = Path(tempfile.mkdtemp())
        keys = {c: f"{c}@1" for c in self._cids()[:4]}
        log = CallLog(out / "calls.jsonl")
        log.write({"kind": "batch_submitting", "run_id": "test-run", "wave_id": "w1", "mode": "dry", "keys": keys, "final": False})
        log.write({"kind": "batch_submitted", "run_id": "test-run", "wave_id": "w1", "batch_id": "b1", "mode": "dry",
                   "keys": keys, "final": False})
        t = fake()
        with self.assertRaises(s3check.S3NotRerun):
            collect(guard(run_cap="1"), t, out)
        self.assertEqual(t.batches, {})

    def test_collect_after_a_failed_submit_is_refused(self):
        class Fails(FakeTransport):
            def submit_batch(self, requests):
                raise TransportError("server", "overloaded", billed="unknown", status=529)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="1")
        run(g, Fails(lambda p: reply(model=p["model"])), out)
        t = fake()
        with self.assertRaises(s3check.S3NotRerun):
            collect(g, t, out)
        self.assertEqual(t.batches, {})

    def test_a_new_submit_during_collect_raises(self):
        out = Path(tempfile.mkdtemp())
        with mock.patch.object(s3check, "_collectable", lambda log, cids: ""):   # the pre-check is bypassed on purpose
            with self.assertRaises(RuntimeError):
                collect(guard(run_cap="1"), fake(), out)


class Ended(FakeTransport):
    """The Batch has ended at the first poll, so main()'s real sleep between polls is never reached."""

    def batch_status(self, batch_id):
        return {"processing_status": "ended", "request_counts": {}}


class ExitCodes(unittest.TestCase):
    """Edith S3-2: 0 only for status complete."""

    def _live(self, cap):
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap=cap)
        args = ["live", "--set", str(FIXTURE), "--run-id", "s3-x", "--cap", cap, "--clearance", "c.json"]
        with as_s3(), mock.patch("harness.pareto.live.open_live_guard", return_value=(g, out)), \
                mock.patch("harness.pareto.transport.RealTransport", lambda guard: Ended(lambda p: reply(model=p["model"]))), \
                contextlib.redirect_stdout(io.StringIO()):
            return s3check.main(args)

    def test_live_exit_code_follows_the_status(self):
        self.assertEqual(self._live("1"), 0)                                 # complete (fake transport, dry guard)
        self.assertEqual(self._live("0.30"), 2)                              # not_sent: does not fit in one Batch

    def test_dry_exit_code_follows_the_status(self):
        args = ["dry", "--set", str(FIXTURE), "--run-id", "s3-dry", "--cap", "0.30", "--out", str(Path(tempfile.mkdtemp()) / "s3")]
        with as_s3(), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(s3check.main(args), 2)


if __name__ == "__main__":
    unittest.main()
