import unittest
from decimal import Decimal

from harness.pareto.batch import run_batches
from harness.pareto.guard import CapExceeded
from harness.pareto.prices import worst_case, estimate_input_tokens
from harness.pareto.transport import FakeTransport
from harness.tests.fakes import guard, params, reply, tmplog


def items(n, model="claude-haiku-5-5", max_tokens=1000):
    return [(f"i{k}", params(model=model, max_tokens=max_tokens, text=f"question {k}"), {"k": k}) for k in range(n)]


def _plain(crash_transport):
    """The same fake batches, but results come back without the crash."""
    t = FakeTransport(crash_transport.reply)
    t.batches = crash_transport.batches
    return t


class BatchRuns(unittest.TestCase):
    def test_results_matched_by_custom_id_not_order(self):
        g, log = guard(), tmplog()
        # reply text records which request it answers; FakeTransport yields results in reverse order
        t = FakeTransport(lambda p: reply(model=p["model"], text="re: " + p["messages"][0]["content"]))
        s = run_batches(g, t, log, items(5), sleep=lambda x: None)
        self.assertEqual((s.answered, s.failed, s.unbilled_assumed, s.missing), (5, 0, [], []))
        for r in log.records():
            if r.get("final"):
                self.assertEqual(r["answer_text"], "re: question " + str(r["meta"]["k"]))
        self.assertEqual(g.reserved, 0)

    def test_batch_prices_are_half(self):
        from harness.pareto.client import Client
        g1, g2 = guard(), guard()
        run_batches(g1, FakeTransport(lambda p: reply(model=p["model"], tin=1000, tout=1000)), tmplog(), items(1), sleep=lambda x: None)
        Client(g2, FakeTransport(lambda p: reply(model=p["model"], tin=1000, tout=1000)), tmplog()).call("i0", items(1)[0][1])
        self.assertEqual(g1.spent * 2, g2.spent)

    def test_refusal_in_batch_is_billed_failure(self):
        g, log = guard(), tmplog()
        t = FakeTransport(lambda p: reply(model=p["model"], stop="refusal", category="bio", text=None, tin=300, tout=0))
        s = run_batches(g, t, log, items(2), sleep=lambda x: None)
        self.assertEqual((s.answered, s.failed), (0, 2))
        self.assertGreater(g.spent, 0)

    def test_errored_expired_canceled_released_and_flagged(self):
        g, log = guard(), tmplog()

        def batch_reply(cid, p):
            if cid == "i1":
                return {"type": "errored", "error": {"type": "overloaded"}}
            if cid == "i2":
                return {"type": "expired"}
            return {"type": "succeeded", "message": reply(model=p["model"])}
        t = FakeTransport(batch_reply=batch_reply)
        s = run_batches(g, t, log, items(4), sleep=lambda x: None)
        self.assertEqual(sorted(s.unbilled_assumed), ["i1", "i2"])
        self.assertEqual(s.answered, 2)
        self.assertEqual(g.reserved, 0)
        self.assertNotIn("i1", log.finished_ids())      # a later run will send it again
        t.batch_reply = None
        t.reply = lambda p: reply(model=p["model"])
        t.polls = 0
        s2 = run_batches(g, t, log, items(4), sleep=lambda x: None)
        self.assertEqual((s2.answered, s2.skipped_already_done), (2, 2))   # i1 and i2 sent again under new keys

    def test_missing_result_stays_reserved(self):
        g, log = guard(), tmplog()

        class Dropping(FakeTransport):
            def batch_results(self, bid):
                return [r for r in super().batch_results(bid) if r["custom_id"] != "i0"]
        t = Dropping(lambda p: reply(model=p["model"]))
        s = run_batches(g, t, log, items(3), sleep=lambda x: None)
        self.assertEqual(s.missing, ["i0"])
        self.assertGreater(g.reserved, 0)

    def test_waves_split_to_fit_cap_and_all_get_done(self):
        its = items(10, model="claude-opus-5-5", max_tokens=2000)
        one = worst_case("claude-opus-5-5", estimate_input_tokens("x" * 400), 2000, batch=True)
        g, log = guard(run_cap=str(one * Decimal("3.5"))), tmplog()     # ~3 worst cases fit at once
        t = FakeTransport(lambda p: reply(model=p["model"], tin=20, tout=20))
        s = run_batches(g, t, log, its, sleep=lambda x: None)
        self.assertGreaterEqual(len(s.batches), 3)
        self.assertEqual(s.answered, 10)
        self.assertLessEqual(g.spent, g.remaining_run + g.spent)

    def test_single_item_over_cap_refused_nothing_sent(self):
        g, log = guard(run_cap="0.0001"), tmplog()
        t = FakeTransport()
        with self.assertRaises(CapExceeded):
            run_batches(g, t, log, items(1, model="claude-opus-5-5", max_tokens=64000), sleep=lambda x: None)
        self.assertEqual(t.batches, {})

    def test_finished_items_are_skipped_on_rerun(self):
        g, log = guard(), tmplog()
        t = FakeTransport(lambda p: reply(model=p["model"]))
        run_batches(g, t, log, items(3), sleep=lambda x: None)
        n_before = len(t.batches)
        s = run_batches(g, t, log, items(3), sleep=lambda x: None)
        self.assertEqual((s.skipped_already_done, len(t.batches)), (3, n_before))

    def test_submitted_but_uncollected_batch_is_collected_not_resubmitted(self):
        g1, log = guard(), tmplog()
        t = FakeTransport(lambda p: reply(model=p["model"]))
        its = items(3)
        # simulate a crash after submit: reserve + mark sent + submit + log "batch_submitted", nothing after
        from harness.pareto.prices import estimate_input_tokens as est
        from harness.pareto.request import prompt_text
        keys = {c: c + "@1" for c, _, _ in its}
        g1.reserve_many([(keys[c], p["model"], est(prompt_text(p)), p["max_tokens"], True) for c, p, _ in its])
        g1.mark_sent_many(list(keys.values()))
        bid = t.submit_batch([{"custom_id": c, "params": p} for c, p, _ in its])
        log.write({"kind": "batch_submitting", "run_id": "test-run", "wave_id": "w1", "mode": "batch", "keys": keys, "final": False})
        log.write({"kind": "batch_submitted", "run_id": "test-run", "wave_id": "w1", "batch_id": bid, "mode": "batch",
                   "keys": keys, "final": False})
        s = run_batches(g1, t, log, its, sleep=lambda x: None)
        self.assertEqual((len(t.batches), s.answered, g1.reserved), (1, 3, 0))          # no second submission

    def test_crash_before_batch_id_logged_is_an_orphan_and_stops_the_run(self):
        from harness.pareto.batch import OrphanedBatch
        g, log = guard(), tmplog()
        its = items(2)
        log.write({"kind": "batch_submitting", "run_id": "test-run", "wave_id": "w1", "mode": "batch",
                   "keys": {c: c + "@1" for c, _, _ in its}, "final": False})
        t = FakeTransport()
        with self.assertRaises(OrphanedBatch):
            run_batches(g, t, log, its, sleep=lambda x: None)
        self.assertEqual(t.batches, {})                  # nothing was submitted again

    def test_submit_failure_is_logged_unknown_and_keys_stay_counted(self):
        g, log = guard(), tmplog()

        class Failing(FakeTransport):
            def submit_batch(self, requests):
                raise ConnectionError("reset")
        with self.assertRaises(ConnectionError):
            run_batches(g, Failing(), log, items(2), sleep=lambda x: None)
        kinds = [r["kind"] for r in log.records()]
        self.assertEqual(kinds, ["batch_submitting", "batch_submit_failed"])
        self.assertGreater(g.reserved, 0)                # possibly submitted: counted until a human checks
        self.assertEqual(list(log.records())[-1]["billed"], "unknown")
        # the failed wave is resolved in the log, so this is not reported as an orphan; its keys are used up
        self.assertEqual(len(g.sent_unsettled_keys()), 2)

    def test_crash_half_way_through_collecting_resumes_cleanly(self):
        g, log = guard(), tmplog()
        t = FakeTransport(lambda p: reply(model=p["model"], text="re: " + p["messages"][0]["content"]))
        its = items(4)
        # first run: collect only two results, then "crash"
        class Crash(FakeTransport):
            def batch_results(self, bid):
                for n, r in enumerate(super().batch_results(bid)):
                    if n == 2:
                        raise KeyboardInterrupt()
                    yield r
        c = Crash(lambda p: reply(model=p["model"], text="re: " + p["messages"][0]["content"]))
        with self.assertRaises(KeyboardInterrupt):
            run_batches(g, c, log, its, sleep=lambda x: None)
        # results are fetched WHOLE before any is recorded (batch._read, so a retried read restarts cleanly): a crash while
        # fetching records none, and the re-run collects all of them from the same batch, never submitting again
        self.assertEqual(len([r for r in log.records() if r.get("final")]), 0)
        s = run_batches(g, c if False else _plain(c), log, its, sleep=lambda x: None)
        self.assertEqual(len([r for r in log.records() if r.get("final")]), 4)
        self.assertEqual((g.reserved, len(c.batches)), (0, 1))     # one submission only, nothing left open

    def test_replans_after_each_wave(self):
        # cap fits two worst cases at once; each real cost is tiny, so later waves are planned against the room left
        its = items(6, model="claude-opus-5-5", max_tokens=2000)
        one = worst_case("claude-opus-5-5", estimate_input_tokens("x" * 400), 2000, batch=True)
        g, log = guard(run_cap=str(one * Decimal("2.2"))), tmplog()
        t = FakeTransport(lambda p: reply(model=p["model"], tin=20, tout=20))
        s = run_batches(g, t, log, its, sleep=lambda x: None)
        self.assertEqual((s.answered, len(s.batches)), (6, 3))

    def test_live_guard_with_dry_transport_refused_and_the_reverse(self):
        from harness.tests.fakes import LiveEnv
        g = LiveEnv().guard()
        try:
            with self.assertRaises(RuntimeError):
                run_batches(g, FakeTransport(), tmplog(), items(1), sleep=lambda x: None)
        finally:
            g.close()

        class Live(FakeTransport):
            live = True
        with self.assertRaises(RuntimeError):
            run_batches(guard(), Live(), tmplog(), items(1), sleep=lambda x: None)

    def test_first_live_batch_run_stops_after_wave_one_until_the_console_check(self):
        from harness.tests.fakes import LiveEnv

        class LiveFake(FakeTransport):
            live = True
        its = items(10, model="claude-opus-5-5", max_tokens=32000)
        one = worst_case("claude-opus-5-5", estimate_input_tokens("x" * 400), 32000, batch=True)
        env = LiveEnv(cap=str((one * Decimal("3.5")).quantize(Decimal("0.01"))))     # about 3 per wave
        g = env.guard()
        try:
            t = LiveFake(lambda p: reply(model=p["model"], tin=20, tout=3000))     # Batch spend must reach the $0.05 check floor
            s1 = run_batches(g, t, tmplog(), its, sleep=lambda x: None)
            self.assertTrue(s1.stopped_for_console_check)
            self.assertEqual(len(s1.batches), 1)                 # wave 1 ran, wave 2 did not
            g.record_console_check(g.spent, "Console showed the same figure")
            log2 = tmplog()
            s2 = run_batches(g, t, log2, its, sleep=lambda x: None)
            self.assertFalse(s2.stopped_for_console_check)
        finally:
            g.close()

    def test_wave_summary_logged_for_console_reconciliation(self):
        g, log = guard(), tmplog()
        run_batches(g, FakeTransport(lambda p: reply(model=p["model"])), log, items(3), sleep=lambda x: None)
        rec = [r for r in log.records() if r.get("kind") == "batch_collected"][0]
        self.assertEqual((rec["wave_open"], rec["wave_done"]), (0, 3))
        self.assertEqual(Decimal(rec["wave_committed_usd"]), g.spent)
        self.assertGreater(Decimal(rec["wave_reserved_usd"]), Decimal(rec["wave_committed_usd"]))

    def _crashed_wave(self, n=3, commit_first=False):
        """A guard, a log and a transport in the state after a crash following submit (batch id logged)."""
        from harness.pareto.prices import Usage, estimate_input_tokens as est
        from harness.pareto.request import prompt_text
        g, log = guard(), tmplog()
        t = FakeTransport(lambda p: reply(model=p["model"], text="re: " + p["messages"][0]["content"]))
        its = items(n)
        keys = {c: c + "@1" for c, _, _ in its}
        g.reserve_many([(keys[c], p["model"], est(prompt_text(p)), p["max_tokens"], True) for c, p, _ in its])
        g.mark_sent_many(list(keys.values()))
        bid = t.submit_batch([{"custom_id": c, "params": p} for c, p, _ in its])
        log.write({"kind": "batch_submitting", "run_id": "test-run", "wave_id": "w1", "mode": "batch", "keys": keys, "final": False})
        log.write({"kind": "batch_submitted", "run_id": "test-run", "wave_id": "w1", "batch_id": bid, "mode": "batch",
                   "keys": keys, "final": False})
        if commit_first:
            g.commit(keys["i0"], Usage(input_tokens=50, output_tokens=20), batch=True)   # paid, but the log line was never written
        return g, log, t, its

    def test_committed_before_the_log_line_gets_its_record_and_is_not_paid_twice(self):
        g, log, t, its = self._crashed_wave(commit_first=True)
        spent_before = g.spent
        s = run_batches(g, t, log, its, sleep=lambda x: None)
        finals = [r["custom_id"] for r in log.records() if r.get("final")]
        self.assertEqual(sorted(finals), ["i0", "i1", "i2"])         # i0 got its record from the result in hand
        self.assertEqual(len(t.batches), 1)                          # nothing re-sent
        rec0 = [r for r in log.records() if r.get("custom_id") == "i0" and r.get("final")][0]
        self.assertEqual(Decimal(rec0["cost_usd"]), spent_before)    # the cost the ledger already holds
        self.assertEqual(g.reserved, 0)

    def test_open_keys_block_resubmission_unless_resend(self):
        from harness.pareto.client import AlreadySent
        g, log = guard(), tmplog()

        class Failing(FakeTransport):
            def submit_batch(self, requests):
                raise ConnectionError("reset")
        its = items(2)
        with self.assertRaises(ConnectionError):
            run_batches(g, Failing(), log, its, sleep=lambda x: None)
        t = FakeTransport(lambda p: reply(model=p["model"]))
        with self.assertRaises(AlreadySent):
            run_batches(g, t, log, its, sleep=lambda x: None)
        self.assertEqual(t.batches, {})
        s = run_batches(g, t, log, its, sleep=lambda x: None, resend=True)       # after checking the Console
        self.assertEqual(s.answered, 2)

    def test_orphan_can_be_adopted_or_closed(self):
        from harness.pareto.batch import OrphanedBatch, adopt_orphan, close_orphan
        # closed: no batch exists
        g, log = guard(), tmplog()
        its = items(2)
        keys = {c: c + "@1" for c, _, _ in its}
        from harness.pareto.prices import estimate_input_tokens as est
        from harness.pareto.request import prompt_text
        g.reserve_many([(keys[c], p["model"], est(prompt_text(p)), p["max_tokens"], True) for c, p, _ in its])
        g.mark_sent_many(list(keys.values()))
        log.write({"kind": "batch_submitting", "run_id": "test-run", "wave_id": "w1", "mode": "batch", "keys": keys, "final": False})
        t = FakeTransport(lambda p: reply(model=p["model"]))
        with self.assertRaises(OrphanedBatch):
            run_batches(g, t, log, its, sleep=lambda x: None)
        with self.assertRaises(ValueError):
            close_orphan(g, log, "w1", "  ")
        close_orphan(g, log, "w1", "listed batches in the Console; none")
        self.assertEqual(g.reserved, 0)
        s = run_batches(g, t, log, its, sleep=lambda x: None)
        self.assertEqual(s.answered, 2)
        self.assertTrue(all(k in g.used_keys() for k in ("i0@1", "i0@2")))
        # adopted: the batch exists
        g2, log2, t2, its2 = self._crashed_wave(n=2)
        log3 = tmplog()
        for r in log2.records():
            if r["kind"] == "batch_submitting":
                log3.write(r)
        with self.assertRaises(OrphanedBatch):
            run_batches(g2, t2, log3, its2, sleep=lambda x: None)
        adopt_orphan(log3, "w1", "fake-batch-1")
        s2 = run_batches(g2, t2, log3, its2, sleep=lambda x: None)
        self.assertEqual((s2.answered, len(t2.batches)), (2, 1))

    def test_duplicate_or_bad_custom_id_refused(self):
        g, log = guard(), tmplog()
        its = items(2)
        with self.assertRaises(ValueError):
            run_batches(g, FakeTransport(), log, its + [its[0]], sleep=lambda x: None)
        bad = [("bad id!", its[0][1], {})]
        with self.assertRaises(ValueError):
            run_batches(g, FakeTransport(), log, bad, sleep=lambda x: None)

    def test_model_mismatch_in_batch_halts(self):
        g, log = guard(), tmplog()
        t = FakeTransport(lambda p: reply(model="claude-opus-5-5"))
        run_batches(g, t, log, items(2), sleep=lambda x: None)
        self.assertTrue(g.halted)


if __name__ == "__main__":
    unittest.main()
