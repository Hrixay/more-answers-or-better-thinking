import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from harness.pareto import smoke
from harness.pareto.pilot import build_realtime_requests, load_set, plan_realtime, run_pilot
from harness.pareto.transport import DryTransport, FakeTransport
from harness.taskgen import freeze
from harness.tests.fakes import guard, reply


def make_set(n_base=6):
    d = Path(tempfile.mkdtemp()) / "set"
    freeze.write_set(d, "digits", "d4s", "pilot-digits-d4s-v1-test", n_base, "d31", "scratch")
    return d


class Smoke(unittest.TestCase):
    def test_smoke_shape_and_plan(self):
        man, items = load_set(make_set(1))
        rt, batch = smoke.build_smoke(man, items)
        self.assertEqual([p["model"] for _, p, _ in rt], ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"])
        self.assertEqual(len(batch), 6)
        self.assertTrue(all(p["max_tokens"] == 16_000 for _, p, _ in rt + batch))
        ids = [c for c, _, _ in rt + batch]
        self.assertEqual(len(set(ids)), 9)
        pl = smoke.plan(rt, batch)
        self.assertLess(Decimal(pl["total_worst_case_usd"]), Decimal("2"))

    def test_dry_smoke_runs_without_network(self):
        d = make_set(1)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="2")
        r = smoke.run_smoke(g, DryTransport(), out, d)
        self.assertEqual(len(r["realtime"]), 3)
        self.assertEqual(r["batch"].answered + r["batch"].failed, 6)
        self.assertEqual(g.reserved, 0)


class RealtimeCheck(unittest.TestCase):
    def test_ten_puzzles_seven_calls_each_at_list_price(self):
        man, items = load_set(make_set(6))
        rt = build_realtime_requests(man, items)
        self.assertEqual(len(rt), 10 * 7)                       # Haiku x5 + Sonnet + Opus on 10 puzzles
        self.assertEqual(len({c for c, _, _ in rt}), 70)
        pl = plan_realtime(rt)
        self.assertEqual(pl["per_setup"], {"rthm": 50, "rtsm": 10, "rtom": 10})
        self.assertGreater(Decimal(pl["list_price_worst_case_usd"]), Decimal("5"))

    def test_a_ledger_set_gets_the_same_check_with_ledger_limits(self):
        # the ledger pilot runs the real-time check on slot A's set (research/pilot-plan-ledger.md); a code set is still refused
        d = Path(tempfile.mkdtemp()) / "ledger"
        freeze.write_set(d, "ledger", "l1", "pilot-ledger-l1-v1-test", 5, "d31", "scratch")
        man, items = load_set(d)
        rt = build_realtime_requests(man, items)
        self.assertEqual(len(rt), 70)
        self.assertEqual({m["family"] for _, _, m in rt}, {"ledger"})
        self.assertEqual({(p["model"], p["max_tokens"]) for _, p, _ in rt},
                         {("claude-haiku-5-5", 48_000), ("claude-sonnet-5-5", 32_000), ("claude-opus-5-5", 32_000)})
        self.assertEqual(sorted({(m["base_index"], m["width"]) for _, _, m in rt}), [(b, w) for b in range(5) for w in (1, 24)])
        with self.assertRaises(ValueError):
            build_realtime_requests(dict(man, family="code"), items)

    def test_pilot_with_realtime_check_runs_both_and_keeps_batch_unreserved(self):
        d = make_set(6)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="60")
        seen = {"batch_flags": set()}

        class Spy(FakeTransport):
            def send(self, params):                              # only real-time calls come through send()
                seen["batch_flags"].update(r.batch for r in g.open_reservations().values())
                return super().send(params)
        r = run_pilot(g, Spy(lambda p: reply(model=p["model"])), out, [d], sleep=lambda s: None, realtime_set=d)
        self.assertEqual(r["realtime"]["answered"], 70)
        self.assertEqual(seen["batch_flags"], {False})           # real-time calls only ever reserved at list
        self.assertEqual(g.reserved, 0)


if __name__ == "__main__":
    unittest.main()


class LiveOpen(unittest.TestCase):
    def test_open_live_guard_replays_an_existing_ledger_and_uses_the_ledger_folder(self):
        from datetime import datetime, timezone
        from harness.pareto.live import open_live_guard
        from harness.tests.fakes import LiveEnv
        env = LiveEnv(run_id="live-open")
        env.write_clearance()
        kw = dict(data_root=env.data, repo_root=env.root, git=lambda a: "abc1234\n" if a[0] == "rev-parse" else "",
                  now=lambda: datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))
        g1, folder = open_live_guard("live-open", Decimal("30"), env.clearance_path, **kw)
        self.assertEqual(folder, env.data / "raw" / "live-open")
        g1.reserve("k1", "claude-haiku-5-5", 100, 100)
        g1.close()
        g2, folder2 = open_live_guard("live-open", Decimal("30"), env.clearance_path, **kw)      # replayed, not created again
        try:
            self.assertGreater(g2.reserved, 0)
            self.assertIn("k1", g2.used_keys())
        finally:
            g2.close()


class Round4(unittest.TestCase):
    def test_smoke_resume_does_not_resend_finished_calls(self):
        d = make_set(1)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="2")
        t = DryTransport()
        smoke.run_smoke(g, t, out, d)
        n_before = len(t.sent)
        r = smoke.run_smoke(g, t, out, d)
        self.assertEqual(len(t.sent), n_before)                           # no real-time call went out again
        self.assertTrue(all(x["kind"] == "already done" for x in r["realtime"]))

    def test_smoke_ids_keep_the_full_item_id(self):
        man, items = load_set(make_set(1))
        rt, batch = smoke.build_smoke(man, items)
        self.assertTrue(all(items_id in cid for (cid, _, m), items_id in ((x, x[2]["item_id"]) for x in rt + batch)))

    def test_pilot_manifest_counts_the_realtime_calls_and_the_table_survives_a_crash(self):
        import json
        d = make_set(6)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="60")

        class Crash(FakeTransport):
            def batch_results(self, bid):
                raise RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            run_pilot(g, Crash(lambda p: reply(model=p["model"])), out, [d], sleep=lambda s: None, realtime_set=d)
        self.assertEqual(json.loads((out / "manifest.json").read_text())["n_items"], 12 * 12 + 70)   # 12 puzzles x 12 + 70 real-time
        self.assertTrue((out / "compact_table.csv").exists())              # written even though the run crashed

    def test_console_check_needs_a_valid_clearance(self):
        from datetime import datetime, timezone
        from harness.pareto.guard import NotLive
        from harness.pareto.live import open_live_guard, record_console_check
        from harness.tests.fakes import LiveEnv
        env = LiveEnv(run_id="live-cc")
        env.write_clearance()
        git = lambda a: "abc1234\n" if a[0] == "rev-parse" else ""
        late = dict(data_root=env.data, repo_root=env.root, git=git, now=lambda: datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))
        g, _ = open_live_guard("live-cc", Decimal("30"), env.clearance_path, data_root=env.data, repo_root=env.root, git=git,
                               now=lambda: datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))
        g.close()
        with self.assertRaises(NotLive):                                    # expired clearance: nothing may be recorded
            record_console_check("live-cc", Decimal("30"), env.clearance_path, Decimal("1"), "x", roots=late)

    def test_console_clear_needs_a_valid_clearance_and_a_reason(self):
        from datetime import datetime, timezone
        from harness.pareto.guard import NotLive
        from harness.pareto.live import clear_console_block, open_live_guard
        from harness.tests.fakes import LiveEnv
        env = LiveEnv(run_id="live-clr")
        env.write_clearance()
        git = lambda a: "abc1234\n" if a[0] == "rev-parse" else ""
        late = dict(data_root=env.data, repo_root=env.root, git=git, now=lambda: datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))
        g, _ = open_live_guard("live-clr", Decimal("30"), env.clearance_path, data_root=env.data, repo_root=env.root, git=git,
                               now=lambda: datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc))
        g.close()
        with self.assertRaises(NotLive):
            clear_console_block("live-clr", Decimal("30"), env.clearance_path, "found it", roots=late)
