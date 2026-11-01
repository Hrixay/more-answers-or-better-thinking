import json
import unittest
from decimal import Decimal

from harness.pareto.client import Client
from harness.pareto.guard import CapExceeded, GuardHalted
from harness.pareto.outcome import ModelMismatch
from harness.pareto.request import RequestRuleError
from harness.pareto.transport import DryTransport, FakeTransport, TransportError
from harness.tests.fakes import LiveEnv, guard, params, reply, tmplog


def make(g=None, fake=None, **kw):
    g = g or guard()
    log = tmplog()
    t = FakeTransport(fake or (lambda p: reply(model=p["model"])))
    return g, t, log, Client(g, t, log, sleep=lambda s: None, **kw)


class ClientFlow(unittest.TestCase):
    def test_reserve_happens_before_send_and_commit_after(self):
        g = guard()
        seen = {}

        def fake(p):
            seen["reserved"] = g.reserved
            seen["spent"] = g.spent
            return reply(model=p["model"])
        g, t, log, c = make(g, fake)
        out = c.call("a1", params())
        self.assertGreater(seen["reserved"], 0)
        self.assertEqual(seen["spent"], 0)
        self.assertEqual(g.reserved, 0)
        self.assertGreater(g.spent, 0)
        self.assertEqual(out.kind, "answered")

    def test_log_line_written_with_raw_usage_and_no_secrets(self):
        g, t, log, c = make()
        c.call("a1", params(), meta={"item": 7})
        recs = list(log.records())
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertTrue(r["final"])
        self.assertEqual((r["custom_id"], r["requested_model"], r["returned_model"], r["effort"], r["meta"]),
                         ("a1", "claude-haiku-5-5", "claude-haiku-5-5", "medium", {"item": 7}))
        self.assertEqual(r["usage_raw"]["input_tokens"], 100)
        self.assertIn("params_hash", r)
        self.assertNotIn("sk-ant", json.dumps(r))
        self.assertIn("a1", log.finished_ids())

    def test_refusal_is_costed_logged_not_retried(self):
        g, t, log, c = make(fake=lambda p: reply(model=p["model"], stop="refusal", category="reasoning_extraction",
                                                  text=None, tin=500, tout=0))
        out = c.call("r1", params())
        self.assertEqual((out.kind, len(t.sent)), ("refusal", 1))
        self.assertGreater(g.spent, 0)                          # billed, not free
        r = list(log.records())[0]
        self.assertEqual((r["kind"], r["refusal_category"], r["final"]), ("refusal", "reasoning_extraction", True))

    def test_b5_free_refusals_are_flagged_on_the_commit_but_costed_conservatively(self):
        import json
        from pathlib import Path
        from tempfile import mkdtemp
        cases = [("cyber", None, 4370, 0, True), ("general_harms", None, 4370, 0, True), (None, None, 4370, 0, True),
                 ("bio", None, 4370, 0, False), ("reasoning_extraction", None, 4370, 0, False),
                 ("cyber", None, 4370, 571, False)]            # cyber but output tokens were produced: billed
        for k, (cat, _, tin, tout, free) in enumerate(cases):
            led = Path(mkdtemp()) / "ledger.jsonl"
            g = guard(ledger_path=led)
            c = Client(g, FakeTransport(lambda p: reply(model=p["model"], stop="refusal", category=cat, text=None, tin=tin, tout=tout)),
                       tmplog(), sleep=lambda s: None)
            out = c.call(f"b5{k}", params())
            self.assertEqual(out.refusal_billed_by_rule, not free)
            commit = [json.loads(ln) for ln in led.read_text().splitlines() if '"event": "commit"' in ln][0]
            self.assertEqual(bool(commit.get("free_by_rule")), free, (cat, tout))
            self.assertGreater(g.spent, 0)                               # conservative: the caps count it either way
            self.assertEqual(g.rule_adjusted_spent, 0 if free else g.spent)
            g.close()

    def test_truncation_is_costed_and_returned_as_failure(self):
        g, t, log, c = make(fake=lambda p: reply(model=p["model"], stop="max_tokens", tout=1000))
        out = c.call("t1", params())
        self.assertTrue(out.is_failure)
        self.assertEqual(len(t.sent), 1)
        self.assertGreater(g.spent, 0)

    def test_model_mismatch_pays_logs_then_halts(self):
        g, t, log, c = make(fake=lambda p: reply(model="claude-opus-5-5"))
        with self.assertRaises(ModelMismatch):
            c.call("m1", params())
        self.assertTrue(g.halted)
        self.assertGreater(g.spent, 0)
        self.assertEqual(list(log.records())[0]["model_matches"], False)
        with self.assertRaises(GuardHalted):
            c.call("m2", params())
        self.assertEqual(len(t.sent), 1)

    def test_rate_limit_retried_each_attempt_reserved_and_logged(self):
        calls = []

        def fake(p):
            calls.append(1)
            if len(calls) < 3:
                raise TransportError("rate_limit", "slow down", billed="no", retryable=True, status=429)
            return reply(model=p["model"])
        g, t, log, c = make(fake=fake)
        out = c.call("x1", params())
        self.assertEqual(out.kind, "answered")
        recs = list(log.records())
        self.assertEqual([(r["attempt"], r["final"], r.get("kind")) for r in recs],
                         [(1, False, "error"), (2, False, "error"), (3, True, "answered")])
        self.assertEqual(g.reserved, 0)

    def test_retries_stop_at_max_attempts(self):
        def fake(p):
            raise TransportError("server", "overloaded", billed="no", retryable=True, status=529)
        g, t, log, c = make(fake=fake, max_attempts=2)
        with self.assertRaises(TransportError):
            c.call("x2", params())
        self.assertEqual(len(t.sent), 2)
        self.assertEqual(g.spent, 0)
        self.assertEqual(g.reserved, 0)
        self.assertFalse(list(log.records())[-1]["final"])           # rejected before running: resumable (V3)

    def test_rejected_call_is_resumable_but_unknown_outcome_is_final(self):
        calls = []

        def fake(p):
            calls.append(1)
            if len(calls) == 1:
                raise TransportError("auth_or_model", "401", billed="no", retryable=False, status=401)
            return reply(model=p["model"])
        g, t, log, c = make(fake=fake)
        with self.assertRaises(TransportError):
            c.call("v3", params())
        self.assertNotIn("v3", log.finished_ids())                   # not finished: it never ran
        out = c.call("v3", params())                                 # a resumed run sends it again, no resend flag needed
        self.assertEqual(out.kind, "answered")
        self.assertIn("v3", log.finished_ids())
        # an unknown outcome stays final and is refused unless resend=True
        def drop(p):
            raise TransportError("connection", "reset", billed="unknown", retryable=False)
        g2, t2, log2, c2 = make(fake=drop)
        with self.assertRaises(TransportError):
            c2.call("u3", params())
        self.assertIn("u3", log2.finished_ids())

    def test_bad_request_not_retried(self):
        def fake(p):
            raise TransportError("bad_request", "nope", billed="no", retryable=False, status=400)
        g, t, log, c = make(fake=fake)
        with self.assertRaises(TransportError):
            c.call("x3", params())
        self.assertEqual(len(t.sent), 1)

    def test_dropped_connection_keeps_reservation_open(self):
        def fake(p):
            raise TransportError("connection", "reset", billed="unknown", retryable=False)
        g, t, log, c = make(fake=fake)
        with self.assertRaises(TransportError):
            c.call("x4", params())
        self.assertGreater(g.reserved, 0)               # counted as possibly spent until a human checks
        self.assertEqual(len(t.sent), 1)                # and never silently re-sent

    def test_cap_refuses_before_sending(self):
        g, t, log, c = make(g=guard(run_cap="0.0001"))
        with self.assertRaises(CapExceeded):
            c.call("c1", params(model="claude-opus-5-5", max_tokens=64000))
        self.assertEqual(t.sent, [])
        self.assertEqual(list(log.records()), [])

    def test_global_cap_counts_what_is_already_spent(self):
        g, t, log, c = make(g=guard(run_cap="100", global_cap="200", spent="199.999"))
        with self.assertRaises(CapExceeded):
            c.call("c2", params(model="claude-opus-5-5", max_tokens=64000))
        self.assertEqual(t.sent, [])

    def test_bad_request_rules_refused_before_reserving(self):
        g, t, log, c = make()
        p = params()
        p["temperature"] = 0
        with self.assertRaises(RequestRuleError):
            c.call("b1", p)
        with self.assertRaises(ValueError):
            c.call("has space", params())
        self.assertEqual((t.sent, g.reserved), ([], 0))

    def test_cost_matches_price_table(self):
        g, t, log, c = make(fake=lambda p: reply(model=p["model"], tin=1_000_000, tout=0))
        c.call("p1", params(max_tokens=10))
        # Haiku input list price per the pinned table: one million input tokens
        from harness.pareto.prices import cost, Usage
        self.assertEqual(g.spent, cost("claude-haiku-5-5", Usage(input_tokens=1_000_000)))


class DryAndLiveGate(unittest.TestCase):
    def test_dry_is_default_and_makes_no_network_calls(self):
        import socket
        orig = socket.socket.connect

        def boom(*a, **k):
            raise AssertionError("a dry run opened a network connection")
        socket.socket.connect = boom
        try:
            g = guard()
            self.assertFalse(g.live)
            c = Client(g, DryTransport(), tmplog())
            out = c.call("d1", params())
            self.assertEqual(out.answer_text, "DRY RUN")
        finally:
            socket.socket.connect = orig

    def test_dry_run_never_imports_the_sdk(self):
        import subprocess, sys
        code = ("import sys\n"
                "from harness.pareto.client import Client\n"
                "from harness.pareto.transport import DryTransport\n"
                "from harness.tests.fakes import guard, params, tmplog\n"
                "Client(guard(), DryTransport(), tmplog()).call('d1', params())\n"
                "assert 'anthropic' not in sys.modules, 'SDK imported by a dry run'\n")
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_real_transport_refuses_unless_guard_is_live_and_cleared(self):
        from harness.pareto.guard import NotLive
        from harness.pareto.transport import RealTransport
        with self.assertRaises(NotLive):
            RealTransport(guard(live=False))
        env = LiveEnv()
        g = env.guard(cleared=False)                        # live but no clearance file
        try:
            with self.assertRaises(NotLive):
                RealTransport(g)
        finally:
            g.close()

    def test_live_transport_with_dry_guard_refused(self):
        class Live(FakeTransport):
            live = True
        with self.assertRaises(RuntimeError):
            Client(guard(), Live(), tmplog())

    def test_dry_transport_with_live_guard_refused(self):
        g = LiveEnv().guard()
        try:
            with self.assertRaises(RuntimeError):
                Client(g, DryTransport(), tmplog())
        finally:
            g.close()

    def test_client_never_reserves_at_the_batch_price(self):
        seen = {}
        g = guard()

        def fake(p):
            seen["batch_flags"] = [r.batch for r in g.open_reservations().values()]
            return reply(model=p["model"])
        Client(g, FakeTransport(fake), tmplog(), sleep=lambda s: None).call("nb", params())
        self.assertEqual(seen["batch_flags"], [False])

    def test_finished_or_open_custom_id_is_not_sent_again(self):
        from harness.pareto.client import AlreadySent
        g, t, log, c = make()
        c.call("once", params())
        with self.assertRaises(AlreadySent):
            c.call("once", params())
        self.assertEqual(len(t.sent), 1)
        # a dropped connection leaves it open: still refused
        def drop(p):
            raise TransportError("connection", "reset", billed="unknown", retryable=False)
        g2, t2, log2, c2 = make(fake=drop)
        with self.assertRaises(TransportError):
            c2.call("drop", params())
        with self.assertRaises(AlreadySent):
            c2.call("drop", params())
        self.assertEqual(len(t2.sent), 1)
        # on purpose, after checking the Console
        with self.assertRaises(TransportError):
            c2.call("drop", params(), resend=True)
        self.assertEqual(len(t2.sent), 2)
        self.assertTrue(list(log2.records())[-1]["meta"]["resend"])

    def test_client_refuses_an_item_still_open_in_a_batch(self):
        from harness.pareto.client import AlreadySent
        g, t, log, c = make()
        g.reserve("bx@1", "claude-haiku-5-5", 10, 10, batch=True)      # an open batch key for the same custom_id
        g.mark_sent_many(["bx@1"])
        with self.assertRaises(AlreadySent):
            c.call("bx", params())
        self.assertEqual(t.sent, [])

    def test_unexpected_exception_is_logged_as_billed_unknown_and_reserved(self):
        def boom(p):
            raise TypeError("unknown keyword argument")
        g, t, log, c = make(fake=boom)
        with self.assertRaises(TypeError):
            c.call("u1", params())
        r = list(log.records())[-1]
        self.assertEqual((r["kind"], r["error"]["billed"], r["final"]), ("error", "unknown", True))
        self.assertGreater(g.reserved, 0)

    def test_attempt_numbers_continue_from_the_guard_not_only_the_log(self):
        g, t, log, c = make()
        g.reserve("k#a1", "claude-haiku-5-5", 10, 10)       # a key the log never heard of (crash between reserve and log)
        g.release("k#a1")
        c.call("k", params())
        self.assertIn("k#a2", g.used_keys())


if __name__ == "__main__":
    unittest.main()
