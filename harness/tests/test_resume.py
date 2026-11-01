"""Resuming the main run after a crash or a dropped connection (the D-93 readiness blocker): run_batches settles only its own unsettled
batches (an E3 round's batch is left for run_e3), batch reads retry transient errors and never re-submit, and a crash mid-E3 or
mid-waves followed by the same command again finishes the run with no custom id ever sent twice. Offline only (FakeTransport)."""

import itertools
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from harness.pareto import batch as batchmod
from harness.pareto import e3
from harness.pareto.calllog import CallLog
from harness.pareto.main import run_main
from harness.pareto.transport import FakeTransport, TransportError
from harness.taskgen import ledger
from harness.tests.fakes import guard, reply
from harness.tests.test_main import main_set, prompts, right_text


class FlakyTransport(FakeTransport):
    """A FakeTransport whose READS (status, results) fail with a dropped connection while `down` is set; `down_after_submit` sets it
    right after the n-th batch is submitted (a crash in the middle of settling that batch)."""

    def __init__(self, reply_fn, down_after_submit=None, blips=0):
        super().__init__(reply_fn)
        self.down = False
        self.down_after_submit = down_after_submit
        self.blips = blips                          # this many reads fail, then reads work (a short outage)
        self.reads_failed = 0

    def submit_batch(self, requests):
        bid = super().submit_batch(requests)
        if self.down_after_submit is not None and len(self.batches) == self.down_after_submit:
            self.down = True
        return bid

    def _maybe_fail(self):
        if self.down or self.blips > 0:
            self.blips = max(0, self.blips - 1)
            self.reads_failed += 1
            raise TransportError("connection", "network dropped", billed="no", retryable=True)

    def batch_status(self, batch_id):
        self._maybe_fail()
        return super().batch_status(batch_id)

    def batch_results(self, batch_id):
        self._maybe_fail()
        return super().batch_results(batch_id)


class Runs(unittest.TestCase):
    def setUp(self):
        self.man, self.items = main_set(n_base=1)
        by_prompt = prompts(self.items)
        steps = {st.prompt: st for st in e3.chain_steps([(self.man, self.items)])}
        cycle = itertools.count()

        def fake(p):
            text = p["messages"][0]["content"]
            if text in steps:                               # E3: right, wrong, right, right, ... so some steps need a second round
                vals = [int(x) for x in steps[text].truth.split(",")]
                return reply(model=p["model"], text=f"Answer: {ledger.fmt(vals if next(cycle) % 4 != 1 else [vals[0] + 1] + vals[1:])}")
            return reply(model=p["model"], text=right_text(by_prompt[text]))
        self.fake = fake
        self.out = Path(tempfile.mkdtemp())
        self.sleeps = []

    def run_once(self, g, t):
        return run_main(g, t, self.out, Path("/fake"), sleep=self.sleeps.append, loader=lambda _: (self.man, self.items), with_rt=False)

    def sent_ids(self, t):
        return [r["custom_id"] for reqs in t.batches.values() for r in reqs]

    def finished(self):
        return CallLog(self.out / "calls.jsonl").finished_ids()

    def reference(self):
        """The same run with no fault: its custom ids and rounds."""
        t = FlakyTransport(self.fake)
        out, self.out = self.out, Path(tempfile.mkdtemp())
        r = self.run_once(guard(run_cap="100"), t)
        ids = sorted(self.sent_ids(t))
        self.out = out
        return r, ids

    def test_a_crash_mid_e3_resumes_with_no_id_sent_twice(self):
        ref, ref_ids = self.reference()
        self.assertGreaterEqual(ref["e3"]["rounds"], 2)                       # the fake makes E3 need a top-up round
        g = guard(run_cap="100")
        t = FlakyTransport(self.fake, down_after_submit=3)                  # batch 1: the single calls; 2: E3 round 1; 3: E3 round 2
        with self.assertRaises(TransportError):
            self.run_once(g, t)                                             # every read retried, then the run stops
        self.assertEqual(t.reads_failed, batchmod.READ_TRIES)
        before = Counter(self.sent_ids(t))
        t.down = False                                                      # the network is back: the same command again
        r = self.run_once(g, t)
        ids = self.sent_ids(t)
        self.assertEqual(max(Counter(ids).values()), 1)                     # no custom id was ever sent twice
        self.assertEqual(sorted(ids), ref_ids)                              # exactly the calls of a run with no fault
        self.assertFalse(set(before) & set(Counter(ids) - before))         # the re-run only sent ids that were never sent
        self.assertEqual(r["e3"]["stopped"], None)
        self.assertEqual((r["e3"]["decided"] + r["e3"]["at_cap"], r["e3"]["open"]), (6, 0))
        self.assertIn("fake-batch-3", r["summary"].left_for_their_runner)  # the single-call runner left E3's batch alone
        self.assertEqual(len(self.finished()), len(ref_ids))

    def test_a_crash_in_the_single_call_waves_resumes(self):
        _, ref_ids = self.reference()
        g = guard(run_cap="100")
        t = FlakyTransport(self.fake, down_after_submit=1)
        with self.assertRaises(TransportError):
            self.run_once(g, t)
        t.down = False
        self.run_once(g, t)
        ids = self.sent_ids(t)
        self.assertEqual(max(Counter(ids).values()), 1)
        self.assertEqual(sorted(ids), ref_ids)

    def test_a_short_outage_is_ridden_out_with_backoff_and_no_resubmit(self):
        _, ref_ids = self.reference()
        self.sleeps.clear()                                                 # count only this run's sleeps
        t = FlakyTransport(self.fake, blips=3)
        r = self.run_once(guard(run_cap="100"), t)
        self.assertEqual(sorted(self.sent_ids(t)), ref_ids)
        self.assertEqual(t.reads_failed, 3)
        self.assertEqual(self.sleeps[:3], [30.0, 60.0, 120.0])              # exponential backoff on the failed reads
        self.assertIsNone(r["e3"]["stopped"])

    def test_a_truncation_pause_stops_before_the_next_wave_and_needs_a_release_note(self):
        _, ref_ids = self.reference()
        base = self.fake

        def truncating(p):                                                    # Haiku-low truncates on every 10th call (over 2%)
            if p["output_config"]["effort"] == "low" and p["model"].startswith("claude-haiku") and next(self.n) % 10 == 0:
                return reply(model=p["model"], text="1.1 = [", stop="max_tokens")
            return base(p)
        self.n = itertools.count()
        g = guard(run_cap="100")
        t = FlakyTransport(truncating)
        r = self.run_once(g, t)
        self.assertIn("hl", r["summary"].paused_for_truncation)
        self.assertGreater(r["summary"].paused_for_truncation["hl"], 0.02)
        self.assertIsNone(r["e3"])                                            # E3 did not start
        self.assertEqual(len(t.batches), 1)                                   # nothing after the wave that tripped it
        with self.assertRaises(batchmod.PausedForTruncation):
            self.run_once(g, t)                                               # a plain re-run refuses
        r2 = run_main(g, t, self.out, Path("/fake"), sleep=self.sleeps.append, loader=lambda _: (self.man, self.items), with_rt=False,
                      release_pause_note="the user ruled: go on (test)")
        ids = self.sent_ids(t)
        self.assertEqual(max(Counter(ids).values()), 1)
        self.assertEqual(sorted(ids), ref_ids)
        self.assertIsNone(r2["e3"]["stopped"])
        kinds = [r.get("kind") for r in CallLog(self.out / "calls.jsonl").records()]
        self.assertEqual((kinds.count("paused_for_truncation"), kinds.count("pause_released")), (1, 1))

    def truncating_haiku(self):
        base, self.n = self.fake, itertools.count()

        def f(p):                                                             # Haiku-medium truncates on every 10th call
            if p["output_config"]["effort"] == "medium" and p["model"].startswith("claude-haiku") and next(self.n) % 10 == 0:
                return reply(model=p["model"], text="1.1 = [", stop="max_tokens")
            return base(p)
        return f

    def test_a_wave_settled_on_resume_is_checked_and_pauses_before_wave_2(self):
        g = guard(run_cap="100")
        t = FlakyTransport(self.truncating_haiku(), down_after_submit=1)
        kw = dict(sleep=self.sleeps.append, loader=lambda _: (self.man, self.items), with_rt=False, max_wave_size=60)
        with self.assertRaises(TransportError):
            run_main(g, t, self.out, Path("/fake"), **kw)                     # crash while settling wave 1
        t.down = False
        r = run_main(g, t, self.out, Path("/fake"), **kw)                     # the re-run settles wave 1, checks it, pauses
        self.assertTrue(r["summary"].paused_for_truncation)
        self.assertEqual(len(t.batches), 1)                                   # no wave 2 was sent
        kinds = [x.get("kind") for x in CallLog(self.out / "calls.jsonl").records()]
        self.assertEqual(kinds.count("paused_for_truncation"), 1)
        with self.assertRaises(batchmod.PausedForTruncation):
            run_main(g, t, self.out, Path("/fake"), **kw)

    def test_the_pause_can_be_waived_by_a_recorded_ruling(self):
        g = guard(run_cap="100")
        t = FlakyTransport(self.truncating_haiku())
        kw = dict(sleep=self.sleeps.append, loader=lambda _: (self.man, self.items), with_rt=False, max_wave_size=60)
        r = run_main(g, t, self.out, Path("/fake"), **kw)
        self.assertTrue(r["summary"].paused_for_truncation)
        with self.assertRaises(ValueError):
            run_main(g, t, self.out, Path("/fake"), waive_pause_note="  ", **kw)
        r = run_main(g, t, self.out, Path("/fake"), waive_pause_note="the user ruled the pause off (test)", **kw)
        self.assertFalse(r["summary"].paused_for_truncation)
        self.assertIsNone(r["e3"]["stopped"])
        kinds = [x.get("kind") for x in CallLog(self.out / "calls.jsonl").records()]
        self.assertEqual((kinds.count("truncation_pause_waived"), kinds.count("pause_released"), kinds.count("paused_for_truncation")),
                         (1, 1, 1))                                           # truncation goes on, but no second pause
        self.assertEqual(max(Counter(self.sent_ids(t)).values()), 1)

    def test_releasing_a_run_that_is_not_paused_is_refused(self):
        with self.assertRaises(RuntimeError):
            run_main(guard(run_cap="100"), FlakyTransport(self.fake), self.out, Path("/fake"), sleep=self.sleeps.append,
                     loader=lambda _: (self.man, self.items), with_rt=False, release_pause_note="nothing to release")

    def test_a_read_error_that_is_not_transient_is_not_retried(self):
        calls = []

        def bad():
            calls.append(1)
            raise TransportError("auth_or_model", "401", billed="no", retryable=False, status=401)
        with self.assertRaises(TransportError):
            batchmod._read(bad, "status", sleep=lambda s: None)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()


class RunbookOneLiners(unittest.TestCase):
    """The exact `python -c` one-liners of harness/pareto/README.md's runbook, run on fixture logs (Edith, resume fix R-2)."""
    README = Path(__file__).resolve().parents[1] / "pareto" / "README.md"
    LOG = "/Users/hrixay/Desktop/pareto/data/raw/main-l14n6-1/calls.jsonl"

    def bodies(self):
        import re
        lines = [m.group(1) for m in re.finditer(r'python -c "(.*)"', self.README.read_text())]
        out = {}
        for b in lines:
            for name in ("adopt_orphan", "close_orphan", "recollect_batch"):
                if f"from harness.pareto.batch import {name};" in b:
                    out[name] = b
        self.assertEqual(sorted(out), ["adopt_orphan", "close_orphan", "recollect_batch"])
        return out

    def make_orphan(self, td):
        from harness.pareto.batch import run_batches
        from harness.tests.fakes import params as fparams
        log = CallLog(td / "calls.jsonl")
        g = guard(run_cap="10")

        class Crash(FakeTransport):
            def submit_batch(self, requests):
                raise KeyboardInterrupt()
        its = [(f"x-{i:02d}", fparams(text=f"q{i}"), {"setup": "hm"}) for i in range(3)]
        with self.assertRaises(KeyboardInterrupt):
            run_batches(g, Crash(), log, its, sleep=lambda s: None)
        wave = next(r["wave_id"] for r in log.records() if r.get("kind") == "batch_submitting")
        return g, log, its, wave

    def run_body(self, body, td, **subs):
        body = body.replace(self.LOG, str(td / "calls.jsonl"))
        for k, v in subs.items():
            body = body.replace(k, v)
        exec(body, {})

    def test_adopt_orphan_one_liner(self):
        td = Path(tempfile.mkdtemp())
        g, log, its, wave = self.make_orphan(td)
        with self.assertRaises(batchmod.OrphanedBatch):
            batchmod.run_batches(g, FakeTransport(), log, its, sleep=lambda s: None)
        self.run_body(self.bodies()["adopt_orphan"], td, **{"<WAVE_ID>": wave, "<BATCH_ID>": "found-batch-1"})
        self.assertIn("found-batch-1", [b for b, _ in batchmod._unsettled_batches(log)])

    def test_close_orphan_one_liner(self):
        from unittest import mock
        td = Path(tempfile.mkdtemp())
        g, log, its, wave = self.make_orphan(td)
        with mock.patch("harness.pareto.live.open_live_guard", return_value=(g, td)), mock.patch.object(g, "close", create=True):
            self.run_body(self.bodies()["close_orphan"], td, **{"<WAVE_ID>": wave, "<NOTE>": "no batch at Anthropic (checked)"})
        s = batchmod.run_batches(g, FakeTransport(), log, its, sleep=lambda s: None)   # no orphan now; sent again under new keys
        self.assertEqual(s.answered, 3)

    def test_recollect_one_liner_reads_missing_results_without_resending(self):
        from harness.tests.fakes import params as fparams
        td = Path(tempfile.mkdtemp())
        log = CallLog(td / "calls.jsonl")
        g = guard(run_cap="10")
        its = [(f"y-{i:02d}", fparams(text=f"q{i}"), {"setup": "hm"}) for i in range(3)]

        class Drops(FakeTransport):
            hide = True

            def batch_results(self, bid):
                for r in super().batch_results(bid):
                    if self.hide and r["custom_id"] == "y-01":
                        continue
                    yield r
        t = Drops()
        s = batchmod.run_batches(g, t, log, its, sleep=lambda s: None)
        self.assertEqual(s.missing, ["y-01"])
        bid = s.batches[0]
        t.hide = False
        self.run_body(self.bodies()["recollect_batch"], td, **{"<BATCH_ID>": bid, "<NOTE>": "results there (checked)"})
        s2 = batchmod.run_batches(g, t, log, its, sleep=lambda s: None)
        self.assertEqual(len(t.batches), 1)                                   # nothing re-sent
        self.assertIn("y-01", log.finished_ids())
        self.assertEqual(g.reserved, 0)
