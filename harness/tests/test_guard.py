"""Tests for harness/pareto/guard.py. Offline, fake usage only, no API calls.

Run from the repo root:  python3 -m unittest discover -s harness/tests -t .
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock

from harness.pareto import guard as guard_module
from harness.pareto import prices
from harness.pareto.guard import (CapExceeded, GuardHalted, LedgerBusy, NotLive, SpendGuard, git_runner_for,
                                  ledger_path_for, read_spent_from_spend_log)
from harness.pareto.prices import FABLE, HAIKU, OPUS, Usage

D = Decimal
REPO = Path(__file__).resolve().parents[2]
OPUS_CALL = D("1.288")  # worst_case(OPUS, 1000, 64000): 1,000 x $8/M + 64,000 x $20/M
HEAD = "abc1234" + "0" * 33
NOON = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
TEST_PRICE_DATE = "2026-10-11"   # the price-table date these tests are built around (NOON's day); the real table date moves on


def setUpModule():
    """The live-gate tests run on a fixed clock (NOON, 2026-10-11) and clearances priced on that day, so the table date is pinned here to
    match. The guard's own rule (the clearance's date equals the table's, checked today or yesterday) is what is tested, not today's table."""
    global _PRICE_PATCH
    _PRICE_PATCH = mock.patch.object(guard_module.prices, "PRICE_TABLE_DATE", TEST_PRICE_DATE)
    _PRICE_PATCH.start()


def tearDownModule():
    _PRICE_PATCH.stop()


def make(cap="30", **kw) -> SpendGuard:
    kw.setdefault("global_spent_usd", D("0"))
    return SpendGuard("pilot-test", D(cap), **kw)


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def keep(self, g):
        self.addCleanup(g.close)
        return g


class FakeGit:
    def __init__(self, head=HEAD, dirty=""):
        self.head, self.dirty, self.calls = head, dirty, []

    def __call__(self, args):
        self.calls.append(args)
        return self.head + "\n" if args[0] == "rev-parse" else self.dirty


class LiveFixture(TempDirTest):
    """A temporary repo root with a spend log, a review file and a data folder."""

    def setUp(self):
        super().setUp()
        self.repo = self.dir / "repo"
        (self.repo / "ops" / "reviews").mkdir(parents=True)
        self.set_spend_log()
        self.data = self.repo / "data"
        self.review = "ops/reviews/2026-10-10-clearance-pilot-test.md"
        (self.repo / self.review).write_text(f"Edith's clearance.\n{self.cleared()}\n")
        self.git = FakeGit()
        self.now = NOON

    def cleared(self, run_id="pilot-test", commit="abc1234", root=None):
        """The exact CLEARED line (T5/T7): run, commit and the ledger root."""
        return f"CLEARED: {run_id} {commit} {(root or self.data).resolve()}"

    def set_spend_log(self, *rows, spent=None, repo=None):
        """rows: (run_id, usd, notes). The 'Spent (rows below)' line is their sum unless `spent` is given."""
        total = sum((D(usd) for _, usd, _ in rows), D("0.00")) if spent is None else D(spent)
        lines = ["| Credit | 200.00 |", f"| Spent (rows below) | {total} |", "",
                 "| Date | Chat | Run ID | What ran | Calls | Tokens in / out / cache | USD (computed) | Console check | Notes |",
                 "|---|---|---|---|---|---|---|---|---|"]
        lines += [f"| 2026-10-10 | Friday | `{rid}` | test | 1 | 1 / 1 / 0 | {usd} | yes | {notes} |" for rid, usd, notes in rows]
        ((repo or self.repo) / "ops" / "spend-log.md").write_text("\n".join(lines) + "\n")

    def clearance(self, **overrides):
        data = {"run_id": "pilot-test", "cap_usd": "30.00", "edith_clearance": self.review,
                "user_go": "go: run the pilot, 2026-10-10", "git_commit": "abc1234",
                "price_table_date": "2026-10-11", "expires": "2026-10-12",
                "ledger_root": str(self.data.resolve()), "env_file": str(self.data.resolve().parent / ".env")}
        data.update(overrides)
        data = {k: v for k, v in data.items() if v is not ...}
        path = self.dir / "clearance.json"
        path.write_text(json.dumps(data))
        return path

    def live(self, run_id="pilot-test", cap="30", **kw):
        kw.setdefault("clearance_path", self.dir / "clearance.json")
        kw.setdefault("git", self.git)
        kw.setdefault("data_root", self.data)
        kw.setdefault("repo_root", self.repo)
        return self.keep(SpendGuard(run_id, D(cap), live=True, now=lambda: self.now, **kw))


# ============================================================================ reserving

class ReserveTest(unittest.TestCase):
    def test_reserve_books_worst_case(self):
        g = make()
        self.assertEqual(g.reserve("a", OPUS, 1000, 64000), OPUS_CALL)
        self.assertEqual(g.reserve("b", OPUS, 1000, 64000, batch=True), OPUS_CALL / 2)
        self.assertEqual(g.reserved, OPUS_CALL * D("1.5"))
        self.assertEqual(g.spent, 0)
        self.assertEqual(g.remaining_run, D(30) - OPUS_CALL * D("1.5"))
        self.assertEqual(g.remaining_global, D(200) - OPUS_CALL * D("1.5"))

    def test_batch_reservation_is_exactly_half_of_list(self):
        g = make()
        for model, est, max_tokens in ((OPUS, 3000, 64000), (HAIKU, 95000, 96000), (FABLE, 1, 1)):
            real_time = g.reserve(f"rt-{model}", model, est, max_tokens)
            batched = g.reserve(f"b-{model}", model, est, max_tokens, batch=True)
            self.assertEqual(batched * 2, real_time, model)
            self.assertEqual(real_time, prices.worst_case(model, est, max_tokens))

    def test_refuses_over_run_cap(self):
        g = make("2")
        g.reserve("a", OPUS, 1000, 64000)
        with self.assertRaisesRegex(CapExceeded, "run cap"):
            g.reserve("b", OPUS, 1000, 64000)
        self.assertEqual(g.reserved, OPUS_CALL)

    def test_refuses_over_global_cap(self):
        g = make("30", global_spent_usd=D("199"))  # run cap has room; global has $1 left
        with self.assertRaisesRegex(CapExceeded, "global cap"):
            g.reserve("a", OPUS, 1000, 64000)
        self.assertEqual(g.reserved, 0)

    def test_exactly_at_cap_is_allowed(self):
        g = make(str(OPUS_CALL))
        g.reserve("a", OPUS, 1000, 64000)
        self.assertEqual(g.remaining_run, 0)
        with self.assertRaises(CapExceeded):
            g.reserve("b", HAIKU, 0, 1)

    def test_duplicate_keys_refused_open_committed_or_released(self):
        g = make()
        g.reserve("a", OPUS, 1000, 64000)
        with self.assertRaises(ValueError):
            g.reserve("a", OPUS, 1000, 64000)
        g.commit("a", Usage(output_tokens=10))
        g.reserve("b", OPUS, 1000, 64000)
        g.release("b")
        for key in ("a", "b"):
            with self.assertRaises(ValueError):
                g.reserve(key, OPUS, 1000, 64000)

    def test_bad_caps_and_flags_refused(self):
        for cap in (30.0, 30, D("Infinity"), D("NaN"), D("-1"), "30"):
            with self.assertRaises(TypeError):
                SpendGuard("r", cap, global_spent_usd=D(0))
        with self.assertRaises(ValueError):
            SpendGuard("r", D(0), global_spent_usd=D(0))
        with self.assertRaises(TypeError):
            make(global_spent_usd=1.0)
        with self.assertRaises(TypeError):  # B1: no default for global spend on a dry guard
            SpendGuard("r", D(30))
        with self.assertRaises(ValueError):
            make(global_spent_usd=D("201"))
        with self.assertRaises(TypeError):
            make().reserve("a", OPUS, 1000, 64000, batch="yes")
        with self.assertRaises(KeyError):
            make().reserve("a", "claude-opus-4", 1000, 64000)

    def test_reserve_many_is_all_or_nothing(self):
        g = make("3")  # fits two Opus calls, not three
        with self.assertRaises(CapExceeded):
            g.reserve_many([(k, OPUS, 1000, 64000, False) for k in ("a", "b", "c")])
        self.assertEqual(g.reserved, 0)
        self.assertEqual(g.open_reservations(), {})
        with self.assertRaises(ValueError):  # duplicate inside the list
            g.reserve_many([("a", OPUS, 1000, 64000, False), ("a", OPUS, 1000, 64000, False)])
        with self.assertRaises(KeyError):  # one bad model spoils the lot
            g.reserve_many([("a", OPUS, 1000, 64000, False), ("b", "nope", 1, 1, False)])
        self.assertEqual(g.reserved, 0)
        g.reserve_many([(k, OPUS, 1000, 64000, False) for k in ("a", "b")])  # keys still unused
        self.assertEqual(g.reserved, 2 * OPUS_CALL)


# ============================================================================ settling

class CommitReleaseTest(unittest.TestCase):
    def test_commit_replaces_reservation(self):
        g = make()
        g.reserve("a", OPUS, 1000, 64000)
        got = g.commit("a", Usage(input_tokens=1000, output_tokens=2000))
        self.assertEqual(got, D("0.044"))
        self.assertEqual((g.spent, g.reserved, g.halted), (D("0.044"), 0, False))

    def test_commit_over_reservation_halts(self):
        g = make()
        g.reserve("a", HAIKU, 100, 100)
        g.reserve("b", HAIKU, 100, 100)
        got = g.commit("a", Usage(input_tokens=100, output_tokens=5000))  # estimate was wrong
        self.assertEqual(g.spent, got)  # the real cost is still recorded
        self.assertTrue(g.halted)
        self.assertIn("more than its reservation", g.halt_reason)
        with self.assertRaises(GuardHalted):
            g.reserve("c", HAIKU, 1, 1)
        with self.assertRaises(GuardHalted):
            g.reserve_many([("d", HAIKU, 1, 1, False)])
        with self.assertRaises(GuardHalted):
            g.mark_sent("b")  # reserved but unsent calls may not go out after a halt
        g.release("b")  # ... and can be dropped
        self.assertEqual(g.reserved, 0)

    def test_batch_item_billed_at_list_halts(self):
        g = make()
        g.reserve("a", OPUS, 1000, 64000, batch=True)
        g.mark_sent("a")
        cost = g.commit("a", Usage(input_tokens=1000, output_tokens=60000), batch=False)  # list price
        self.assertEqual(cost, D("0.004") + D("1.2"))
        self.assertTrue(g.halted)  # 1.204 > the 0.644 Batch reservation
        h = make()
        h.reserve("a", OPUS, 1000, 64000, batch=True)
        self.assertEqual(h.commit("a", Usage(input_tokens=1000, output_tokens=60000)), D("0.602"))
        self.assertFalse(h.halted)

    def test_real_time_reservation_cannot_commit_at_batch_price(self):
        g = make()
        g.reserve("a", OPUS, 1000, 64000)
        with self.assertRaises(ValueError):
            g.commit("a", Usage(output_tokens=1000), batch=True)
        self.assertEqual(g.reserved, OPUS_CALL)  # a refused commit leaves the reservation counted
        with self.assertRaises(TypeError):
            g.commit("a", {"output_tokens": 1})
        self.assertEqual(g.commit("a", Usage(output_tokens=1000)), D("0.02"))

    def test_spend_over_run_cap_halts(self):
        g = make("1")
        g.reserve("a", OPUS, 0, 1)
        g.commit("a", Usage(output_tokens=60000))  # $1.20, over both the reservation and the cap
        self.assertTrue(g.halted)
        self.assertGreater(g.spent, D(1))

    def test_halt_by_caller_refuses_everything_new(self):
        g = make()
        g.reserve("a", OPUS, 1000, 64000)
        g.mark_sent("a")
        g.halt("model mismatch")
        with self.assertRaises(GuardHalted):
            g.reserve("b", OPUS, 1, 1)
        self.assertEqual(g.commit("a", Usage(output_tokens=1)), D("0.00002"))  # in-flight still recorded
        self.assertEqual(g.halt_reason, "model mismatch")

    def test_refusals_truncations_and_errors_are_committed_not_released(self):
        g = make()
        for key in ("refusal", "truncated", "error"):
            g.reserve(key, OPUS, 2000, 64000)
            g.mark_sent(key)
            with self.assertRaisesRegex(ValueError, "was sent"):
                g.release(key)  # never released once sent
        self.assertEqual(g.commit("refusal", Usage(input_tokens=2000)), D("0.008"))
        self.assertEqual(g.commit("truncated", Usage(input_tokens=2000, output_tokens=64000)), D("1.288"))
        g.commit("error", Usage(input_tokens=2000, output_tokens=10))
        self.assertEqual(g.spent, D("0.008") + D("1.288") + D("0.0082"))
        self.assertFalse(g.halted)

    def test_sent_call_with_no_usage_stays_reserved(self):
        g = make()
        g.reserve("lost", OPUS, 1000, 64000)
        g.mark_sent("lost")
        self.assertEqual(g.reserved, OPUS_CALL)
        self.assertEqual(g.sent_unsettled_keys(), {"lost"})

    def test_release_unsent(self):
        g = make()
        g.reserve("a", OPUS, 1000, 64000)
        g.release("a")
        self.assertEqual((g.spent, g.reserved), (0, 0))
        for call in (lambda: g.release("a"), lambda: g.commit("a", Usage()), lambda: g.commit("x", Usage())):
            with self.assertRaises(KeyError):
                call()


class KeyApiTest(unittest.TestCase):
    def test_status_and_key_sets(self):
        g = make()
        g.reserve_many([(k, HAIKU, 10, 10, False) for k in ("a", "b", "c", "d")])
        g.mark_sent_many(["a", "b"])
        g.commit("a", Usage(output_tokens=1))
        g.release("c")
        self.assertEqual([g.status(k) for k in "abcde"], ["committed", "open", "released", "open", None])
        self.assertEqual(g.used_keys(), {"a", "b", "c", "d"})
        self.assertEqual(g.open_keys(), {"b", "d"})
        self.assertEqual(g.sent_unsettled_keys(), {"b"})

    def test_mark_sent_many_is_all_or_nothing(self):
        g = make()
        g.reserve_many([(k, HAIKU, 10, 10, True) for k in ("a", "b", "c")])
        g.mark_sent("c")
        for bad in (["a", "nope"], ["a", "c"], ["a", "a"], []):
            with self.assertRaises((KeyError, ValueError), msg=str(bad)):
                g.mark_sent_many(bad)
            self.assertEqual(g.sent_unsettled_keys(), {"c"})
        g.halt("stop")
        with self.assertRaises(GuardHalted):
            g.mark_sent_many(["a", "b"])
        self.assertEqual(g.sent_unsettled_keys(), {"c"})
        g.release("a")  # unsent items can be released after the halt
        g.release("b")

    def test_summary(self):
        g = make()
        g.reserve_many([(k, OPUS, 1000, 64000, True) for k in ("a", "b", "c")])
        g.reserve("x", OPUS, 1000, 64000)
        g.commit("a", Usage(input_tokens=1000, output_tokens=2000))
        g.release("b")
        s = g.summary(["a", "b", "c"])
        self.assertEqual(s, {"reserved": 3 * OPUS_CALL / 2, "committed": D("0.022"), "open": 1, "done": 2})
        self.assertEqual(str(s["reserved"]), "1.932")
        with self.assertRaises(KeyError):
            g.summary(["a", "never"])


class PlanWavesTest(unittest.TestCase):
    def opus_run(self, n=50, batch=False):
        return [(f"opus-{i}", OPUS, 3000, 64000, batch) for i in range(n)]

    def test_fifty_opus_calls_under_the_pilot_cap(self):
        g = make("30")
        self.assertEqual(prices.worst_case(OPUS, 3000, 64000), D("1.304"))
        with self.assertRaises(CapExceeded):  # all 50 at once (~$65) cannot be reserved
            g.reserve_many(self.opus_run())
        self.assertEqual([len(w) for w in g.plan_waves(self.opus_run())], [23, 23, 4])  # 23 x 1.304 = 29.992
        self.assertEqual([i for w in g.plan_waves(self.opus_run()) for i in w], self.opus_run())  # order kept
        self.assertEqual(g.reserved, 0)  # planning reserves nothing
        todo, sizes = self.opus_run(), []
        while todo:  # run wave by wave, re-planning what is left after each wave's real spend
            wave = g.plan_waves(todo)[0]
            g.reserve_many(wave)
            g.mark_sent_many([key for key, *_ in wave])
            for key, *_ in wave:
                g.commit(key, Usage(input_tokens=3000, output_tokens=8000))
            todo, sizes = todo[len(wave):], sizes + [len(wave)]
        self.assertEqual(sizes, [23, 19, 8])  # room after wave 1: 30 - 23 x 0.172 = 26.044, so 19 x 1.304
        self.assertEqual(g.spent, 50 * D("0.172"))
        self.assertFalse(g.halted)

    def test_batch_waves_hold_twice_as_many(self):
        g = make("30")
        self.assertEqual([len(w) for w in g.plan_waves(self.opus_run(100, batch=True))], [46, 46, 8])
        self.assertEqual([len(w) for w in g.plan_waves(self.opus_run(100))], [23, 23, 23, 23, 8])

    def test_plan_uses_what_is_left_and_wave_size(self):
        g = make("30", global_spent_usd=D("190"))  # global room $10 is the binding limit
        self.assertEqual([len(w) for w in g.plan_waves(self.opus_run(10))], [7, 3])
        self.assertEqual([len(w) for w in make().plan_waves(self.opus_run(10), max_wave_size=4)], [4, 4, 2])
        for bad in (0, -1, True, 2.0):
            with self.assertRaises(ValueError):
                make().plan_waves(self.opus_run(3), max_wave_size=bad)

    def test_single_oversized_item_raises_naming_it(self):
        with self.assertRaisesRegex(CapExceeded, "fable-big"):
            make("5").plan_waves([("ok", OPUS, 10, 100, False), ("fable-big", FABLE, 1000, 128000, False)])


# ============================================================================ B1: live guards and global spend

class LiveSetupTest(LiveFixture):
    def test_live_guard_always_has_its_per_run_ledger(self):
        g = self.live()
        self.assertEqual(g.ledger_path, self.data / "raw" / "pilot-test" / "ledger.jsonl")
        self.assertEqual(json.loads(g.ledger_path.read_text().splitlines()[0])["live"], True)

    def test_live_refuses_caller_global_spend_and_other_ledger_paths(self):
        with self.assertRaises(ValueError):
            self.live(global_spent_usd=D("0"))
        with self.assertRaises(ValueError):
            self.live(ledger_path=self.dir / "elsewhere.jsonl")

    def other_run(self, run_id="other-run"):
        """A finished live run with 0.024 committed and 1.288 still open: exposure 1.312."""
        other = self.live(run_id)
        other.reserve("x", OPUS, 1000, 64000)
        other.reserve("y", OPUS, 1000, 64000)
        other.commit("y", Usage(input_tokens=1000, output_tokens=1000))
        other.close()

    def test_global_spend_is_added_up_per_run(self):
        self.other_run()  # a ledger with no spend-log row: 1.312
        dry = self.keep(SpendGuard("dry-run", D(10), global_spent_usd=D(0), data_root=self.data))
        dry.reserve("z", FABLE, 1000, 100000)  # dry ledgers never count
        self.set_spend_log(("old-run", "150.00", ""))  # a row with no ledger
        g = self.live()
        self.assertEqual(g.global_spent, D("151.312"))  # both, not the larger of the two totals (R2)
        g.close()
        self.set_spend_log(("old-run", "150.00", ""), ("other-run", "2.00", "ledger-ok: 1.312"))
        self.assertEqual(self.live("third-run").global_spent, D("152.00"))  # per run, the larger figure

    def test_row_and_ledger_must_agree_or_carry_a_note(self):
        self.other_run()
        self.set_spend_log(("other-run", "0.024", "Console $0.02"))
        with self.assertRaisesRegex(ValueError, "ledger-ok: 1.312"):
            self.live()
        self.set_spend_log(("other-run", "0.024", "ledger-ok: 1.30"))  # a note for a different figure
        with self.assertRaises(ValueError):
            self.live()
        self.set_spend_log(("other-run", "1.312", ""))  # agreeing figures need no note
        self.assertEqual(self.live().global_spent, D("1.312"))

    def test_spend_log_rows_must_add_up_and_parse(self):
        for rows, spent in (((("a", "2.00", ""),), "1.00"), ((("a", "two dollars", ""),), "0.00")):
            self.set_spend_log(*rows, spent=spent)
            with self.assertRaises(ValueError, msg=str(rows)):
                self.live()

    def test_reads_the_real_spend_log_rows(self):
        real = REPO / "ops" / "spend-log.md"
        rows = guard_module.spend_log_rows(real)                   # parses, and the rows add up to the summary line
        self.assertEqual(sum((usd for usd, _ in rows.values()), D("0")), read_spent_from_spend_log(real))

    def test_torn_line_in_another_ledger_keeps_its_reservation_counted(self):
        other = self.live("other-run")
        other.reserve("x", OPUS, 1000, 64000)
        other.close()
        with open(other.ledger_path, "ab") as fh:
            fh.write(b'{"event": "commit", "key": "x"')  # crash mid-commit
        self.assertEqual(self.live().global_spent, OPUS_CALL)

    def test_live_refused_when_global_spend_is_over_the_cap(self):
        self.set_spend_log(("big", "200.01", ""))
        with self.assertRaises(ValueError):
            self.live()
        self.set_spend_log(("big", "199.00", ""))
        with self.assertRaises(CapExceeded):
            self.live().reserve("a", OPUS, 1000, 64000)


class SharedRootTest(LiveFixture):
    """R1: every checkout of the repo uses the main checkout's data/raw for ledgers and the live lock."""

    def checkout(self, name):
        repo = self.dir / name
        (repo / "ops" / "reviews").mkdir(parents=True)
        self.set_spend_log(repo=repo)
        return repo

    def common_git(self, args):
        if args[:2] == ["rev-parse", "--git-common-dir"]:
            return str(self.dir / "main" / ".git") + "\n"
        return self.git(args)

    def test_default_root_comes_from_the_git_common_dir(self):
        main = self.checkout("main")
        g = self.live(repo_root=main, data_root=None, git=self.common_git)
        self.assertEqual(g.data_root, (self.dir / "main" / "data").resolve())
        g.close()
        relative = lambda args: ".git\n" if args[1] == "--git-common-dir" else self.git(args)
        self.assertEqual(guard_module.shared_data_root(main, relative), (main / "data").resolve())

    def test_two_checkouts_share_the_lock_and_see_each_others_spend(self):
        main, worktree = self.checkout("main"), self.checkout("worktree")
        a = self.live("run-a", repo_root=worktree, data_root=None, git=self.common_git)
        with self.assertRaises(LedgerBusy):  # a second live run from the main checkout must wait
            self.live("run-b", repo_root=main, data_root=None, git=self.common_git)
        a.reserve("x", OPUS, 1000, 64000)
        a.close()
        b = self.live("run-b", repo_root=main, data_root=None, git=self.common_git)
        self.assertEqual(b.global_spent, OPUS_CALL)  # it sees run-a's open reservation

    def test_clearance_must_name_the_shared_root_and_the_main_env_file(self):
        main, worktree = self.checkout("main"), self.checkout("worktree")
        root = (main / "data").resolve()
        (worktree / self.review).write_text(self.cleared(root=root) + "\n")
        g = self.live(repo_root=worktree, data_root=None, git=self.common_git)  # started from a worktree
        good = dict(ledger_root=str(root), env_file=str(main.resolve() / ".env"))
        self.clearance(**good)
        self.assertIsNone(g.env_file)  # only set once the gate has passed
        g.require_live()
        self.assertEqual(g.env_file, main.resolve() / ".env")  # T6: the MAIN checkout's .env
        for wrong in (str(main / "elsewhere"), "data", str(worktree / "data")):
            self.clearance(**dict(good, ledger_root=wrong))
            with self.assertRaisesRegex(NotLive, "ledger_root", msg=wrong):
                g.require_live()
        for wrong in (str(worktree / ".env"), ".env", str(main / ".env.local"), "", ...):
            self.clearance(**dict(good, env_file=wrong))
            with self.assertRaisesRegex(NotLive, "env_file", msg=str(wrong)):
                g.require_live()

    def test_the_guard_never_touches_the_env_file(self):
        env = (self.data.resolve().parent / ".env")
        env.write_text("ANTHROPIC_API_KEY=not-a-real-key\n")
        touched = []
        real_open, real_read = open, Path.read_text

        def spy_open(file, *a, **k):
            touched.append(str(file))
            return real_open(file, *a, **k)

        def spy_read(self, *a, **k):
            touched.append(str(self))
            return real_read(self, *a, **k)
        self.clearance()
        g = self.live()
        with mock.patch("builtins.open", spy_open), mock.patch.object(Path, "read_text", spy_read):
            g.require_live()
            g.reserve("a", OPUS, 1, 1)
            g.mark_sent("a")
        self.assertEqual(g.env_file, env)
        self.assertFalse([t for t in touched if t.endswith(".env")], touched)


# ============================================================================ H2: locks and fresh ledgers

class LockTest(LiveFixture):
    def test_one_guard_per_ledger(self):
        path = self.dir / "ledger.jsonl"
        g = make(ledger_path=path)
        g.reserve("a", OPUS, 1000, 64000)
        with self.assertRaises(LedgerBusy):
            SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D(0))
        g.close()
        with self.assertRaisesRegex(ValueError, "replay"):  # a fresh guard cannot restart the run
            make(ledger_path=path)
        r = self.keep(SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D(0)))
        self.assertEqual(r.reserved, OPUS_CALL)
        with self.assertRaises(LedgerBusy):  # two replays cannot share the room
            SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D(0))

    def test_same_run_id_cannot_start_a_new_ledger(self):
        g = self.live()
        g.reserve("a", OPUS, 1000, 64000)
        g.close()
        with self.assertRaisesRegex(ValueError, "replay"):
            self.live()
        dry = self.keep(SpendGuard("dry", D(5), global_spent_usd=D(0), data_root=self.data))
        dry.close()
        with self.assertRaisesRegex(ValueError, "replay"):
            SpendGuard("dry", D(5), global_spent_usd=D(0), data_root=self.data)

    def test_only_one_live_run_at_a_time(self):
        first = self.live("run-a")
        with self.assertRaises(LedgerBusy):
            self.live("run-b")
        first.close()
        self.live("run-b")

    def test_run_id_cannot_escape_the_data_folder(self):
        for bad in ("../x", "a/b", "", ".hidden"):
            with self.assertRaises(ValueError):
                ledger_path_for(self.data, bad)

    def child(self, code):
        """Start a Python process that runs `code`, prints READY and waits for stdin to close."""
        script = (f"import sys\nsys.path.insert(0, {str(REPO)!r})\nfrom decimal import Decimal as D\n"
                  "from pathlib import Path\nfrom harness.pareto.guard import SpendGuard\n" + code +
                  "\nprint('READY', flush=True)\nsys.stdin.read()\n")
        proc = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, cwd=str(self.dir))
        self.assertEqual(proc.stdout.readline().strip(), "READY", proc.stderr.read() if proc.poll() else "")
        self.addCleanup(lambda: (proc.stdin.close(), proc.wait(10), proc.stdout.close(), proc.stderr.close()))
        return proc

    def test_two_processes_cannot_share_a_ledger(self):
        path = self.dir / "ledger.jsonl"
        make(ledger_path=path).close()
        self.child(f"g = SpendGuard.replay(Path({str(path)!r}), 'pilot-test', D('30'), global_spent_usd=D(0))")
        with self.assertRaises(LedgerBusy):
            SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D(0))

    def test_two_processes_cannot_both_run_live(self):
        self.child(f"g = SpendGuard('run-a', D('30'), live=True, repo_root=Path({str(self.repo)!r}), "
                   f"data_root=Path({str(self.data)!r}))")
        with self.assertRaises(LedgerBusy):
            self.live("run-b")


# ============================================================================ H1: the live gate

class LiveGateTest(LiveFixture):
    def test_dry_run_is_the_default(self):
        g = make(clearance_path=self.clearance())
        self.assertFalse(g.live)
        with self.assertRaises(NotLive):
            g.require_live()
        g.reserve("a", OPUS, 1, 1)
        g.mark_sent("a")  # dry run exercises the same path without the gate

    def test_valid_clearance_passes_and_git_is_checked_once(self):
        self.clearance()
        g = self.live()
        g.require_live()
        self.assertEqual(self.git.calls, [["rev-parse", "HEAD"], guard_module.DIRTY_CHECK])
        g.require_live()
        self.assertEqual(len(self.git.calls), 2)  # the running code was loaded at start; HEAD checked once
        (self.repo / self.review).write_text(f"{self.cleared(commit=HEAD)}\n{self.cleared()}\n")
        self.clearance(cap_usd=30, git_commit=HEAD, expires="2026-10-11T23:59:00Z")
        g.require_live()
        self.clearance(expires="2026-10-17")  # ends 2026-10-18 00:00, within 7 days of noon on the 11th
        g.require_live()

    def test_rejections(self):
        bad = {
            "wrong run": dict(run_id="other-run"), "wrong cap": dict(cap_usd="31"), "bool cap": dict(cap_usd=True),
            "no cap": dict(cap_usd=...), "text cap": dict(cap_usd="thirty"),
            "empty go": dict(user_go="  "), "no go": dict(user_go=...), "empty edith": dict(edith_clearance=""),
            "go says no": dict(user_go="no"), "go without prefix": dict(user_go="go ahead"),
            "go with no words": dict(user_go="go:   "),
            "no commit": dict(git_commit=...), "other commit": dict(git_commit="def5678"),
            "not a hash": dict(git_commit="HEAD"), "short hash": dict(git_commit="abc12"),
            "old price date": dict(price_table_date="2026-10-10"), "no price date": dict(price_table_date=...),
            "expired": dict(expires="2026-10-10"), "expired time": dict(expires="2026-10-11T11:59:00+00:00"),
            "bad expiry": dict(expires="soon"), "no expiry": dict(expires=...),
            "expiry over 7 days": dict(expires="2026-10-18"), "expiry 2099": dict(expires="2099-01-01T00:00:00Z"),
            "other root": dict(ledger_root=str(self.dir / "other")), "relative root": dict(ledger_root="data"),
            "no root": dict(ledger_root=...), "no env file": dict(env_file=...),
            "relative env file": dict(env_file=".env"),
            "review outside reviews": dict(edith_clearance="NOW.md"),
            "review escapes": dict(edith_clearance="ops/reviews/../spend-log.md"),
            "missing review": dict(edith_clearance="ops/reviews/missing.md"),
        }
        g = self.live()
        for name, override in bad.items():
            self.clearance(**override)
            with self.assertRaises(NotLive, msg=name):
                g.require_live()
        (self.dir / "clearance.json").write_text("{not json")
        with self.assertRaises(NotLive):
            g.require_live()
        g.close()
        with self.assertRaises(NotLive):
            self.live("run-x", clearance_path=None).require_live()

    def test_review_file_must_have_the_exact_cleared_line(self):
        self.clearance()
        g = self.live()
        line = self.cleared()
        for text in ("Clearance for pilot-test at commit abc1234.", "NOT " + line, line + " (pending)",
                     "  " + line, line + " ", "\t" + line, "CLEARED: pilot-test abc1234",
                     self.cleared(run_id="other-run"), self.cleared(root=self.dir / "elsewhere"), "CLEARED: pilot-test"):
            (self.repo / self.review).write_text(f"Review.\n{text}\n")
            with self.assertRaises(NotLive, msg=repr(text)):
                g.require_live()
        (self.repo / self.review).write_text(f"Review.\n{line}\n")
        g.require_live()

    def test_dirty_tree_or_git_failure_refused(self):
        self.clearance()
        self.git.dirty = " M harness/pareto/guard.py"
        g = self.live()
        with self.assertRaisesRegex(NotLive, "uncommitted"):
            g.require_live()
        g.close()

        def broken(args):
            raise subprocess.CalledProcessError(128, "git")
        with self.assertRaises(NotLive):
            self.live("run-y", git=broken, clearance_path=self.clearance(run_id="run-y")).require_live()

    def test_dirty_check_covers_the_whole_tree_but_data_raw_and_reviews(self):
        repo = self.dir / "gitrepo"
        (repo / "ops" / "reviews").mkdir(parents=True)
        (repo / "data" / "raw").mkdir(parents=True)
        (repo / "data" / "tasks").mkdir(parents=True)
        (repo / "studies").mkdir()
        run = git_runner_for(repo)
        try:
            run(["init", "-q"])
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")
        (repo / "README.md").write_text("x\n")
        run(["add", "README.md"])
        run(["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"])
        (repo / "data" / "raw" / "ledger.jsonl").write_text("{}\n")
        (repo / "ops" / "reviews" / "r.md").write_text("CLEARED: x abc1234\n")
        self.assertEqual(run(guard_module.DIRTY_CHECK).strip(), "")
        (repo / "data" / "tasks" / "items.jsonl").write_text("{}\n")  # T7: a changed frozen set counts
        self.assertIn("data/tasks/", run(guard_module.DIRTY_CHECK))
        (repo / "data" / "tasks" / "items.jsonl").unlink()
        (repo / "studies" / "driver.py").write_text("print(1)\n")  # R11: an uncommitted driver script
        self.assertIn("studies/", run(guard_module.DIRTY_CHECK))

    def test_prices_must_be_checked_today_or_yesterday(self):
        self.clearance(expires="2026-10-14")
        g = self.live()
        for day, ok in ((11, True), (12, True), (13, False)):
            self.now = datetime(2026, 10, day, 1, tzinfo=timezone.utc)
            if ok:
                g.require_live()
            else:
                with self.assertRaisesRegex(NotLive, "re-check"):
                    g.require_live()

    def test_live_mark_sent_runs_the_gate(self):
        g = self.live()  # no clearance file written
        g.reserve_many([("a", OPUS, 1, 1, False), ("b", OPUS, 1, 1, False)])
        with self.assertRaises(NotLive):
            g.mark_sent("a")
        with self.assertRaises(NotLive):
            g.mark_sent_many(["a", "b"])
        self.assertEqual(g.sent_unsettled_keys(), set())
        g.release("a")
        self.clearance()
        g.mark_sent_many(["b"])
        self.assertEqual(g.sent_unsettled_keys(), {"b"})

    @unittest.skipUnless((REPO / ".git").exists(), "not a git checkout (e.g. a git archive export)")
    def test_real_git_runner_reads_this_repo(self):
        head = git_runner_for(REPO)(["rev-parse", "HEAD"]).strip()
        self.assertRegex(head, r"^[0-9a-f]{40}$")

    def test_source_never_reads_environment_or_network(self):
        for name in ("guard.py", "prices.py"):
            src = (REPO / "harness" / "pareto" / name).read_text(encoding="utf-8")
            self.assertNotRegex(src, r"os\.environ|getenv|dotenv|load_api_key|secrets_env", name)
            # The .env path is only compared (T6); nothing opens, reads or stats it.
            self.assertNotRegex(src, r"(env_file|expected_env)\)?\.(open|read_\w+|stat|exists|is_file)", name)
            imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", src, re.M)
            for banned in ("socket", "urllib", "http", "requests", "anthropic"):
                self.assertFalse([m for m in imports if m.split(".")[0] == banned], (name, banned))
            for call in re.findall(r"subprocess\.\w+\(([^,]*)", src):
                self.assertTrue(call.startswith('["git"'), (name, call))  # git is the only subprocess


# ============================================================================ ledger, replay, H5

class LedgerTest(TempDirTest):
    def state(self, g):
        return (g.spent, g.reserved, g.halted, g.used_keys(), g._done, g._seq, g.sent_unsettled_keys(),
                {k: (r.model, r.amount, r.batch, r.sent) for k, r in g.open_reservations().items()})

    def replay(self, path, cap="30"):
        return self.keep(SpendGuard.replay(path, "pilot-test", D(cap), global_spent_usd=D(0)))

    def busy_guard(self, path):
        g = make(ledger_path=path)
        g.reserve_many([("a", OPUS, 1000, 64000, False), ("b", HAIKU, 500, 8000, True)])
        g.reserve("c", OPUS, 1000, 64000)
        g.reserve("d", HAIKU, 10, 10)
        g.mark_sent_many(["a", "b", "c"])
        g.commit("a", Usage(input_tokens=1000, output_tokens=3000, cache_read_tokens=7))
        g.commit("b", Usage(input_tokens=500, output_tokens=8000))
        g.release("d")
        g.close()
        return g  # "c" is left open and sent, as after a crash mid-call

    def test_replay_reproduces_state_exactly(self):
        path = self.dir / "ledger.jsonl"
        g = self.busy_guard(path)
        r = self.replay(path)
        self.assertEqual(self.state(r), self.state(g))
        self.assertEqual(r.summary(["a", "b", "c", "d"]), g.summary(["a", "b", "c", "d"]))
        r.reserve("e", HAIKU, 1, 1)  # appending continues the sequence
        r.close()
        self.assertEqual(self.state(self.replay(path)), self.state(r))
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            event = json.loads(line)
            self.assertEqual(event["seq"], number)
            for field in ("amount", "spent", "reserved"):
                if field in event:
                    self.assertIsInstance(event[field], str)

    def over_reservation_ledger(self, path):
        g = make(ledger_path=path)
        g.reserve("a", HAIKU, 1, 1)
        g.commit("a", Usage(output_tokens=1000))  # writes commit + halt lines together
        g.close()
        lines = path.read_text().splitlines()
        self.assertEqual([json.loads(l)["event"] for l in lines[-2:]], ["commit", "halt"])
        return lines

    def test_halt_recomputed_when_the_halt_line_is_torn(self):
        path = self.dir / "ledger.jsonl"
        lines = self.over_reservation_ledger(path)
        path.write_text("\n".join(lines[:-1]) + "\n" + lines[-1][:25])  # crash mid-way through the halt line
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            r = self.replay(path)
        self.assertTrue(any("torn" in str(w.message) for w in caught))
        self.assertTrue(r.halted)
        with self.assertRaises(GuardHalted):
            r.reserve("b", HAIKU, 1, 1)
        r.close()
        events = [json.loads(l)["event"] for l in path.read_text().splitlines()]
        self.assertEqual(events[-2:], ["torn_line_dropped", "halt"])  # recorded, file clean again
        self.assertTrue(self.replay(path).halted)

    def test_caller_halt_goes_with_the_commit(self):
        path = self.dir / "ledger.jsonl"
        g = make(ledger_path=path)
        g.reserve("a", OPUS, 1000, 64000)
        g.mark_sent("a")
        with self.assertRaises(TypeError):
            g.commit("a", Usage(output_tokens=10), halt_reason=None)
        g.commit("a", Usage(output_tokens=10), halt_reason="model mismatch: got claude-other")
        self.assertTrue(g.halted)
        g.close()
        lines = path.read_text().splitlines()
        self.assertEqual([json.loads(l)["event"] for l in lines[-2:]], ["commit", "halt"])  # one write
        self.assertEqual(json.loads(lines[-2])["halt_reason"], "model mismatch: got claude-other")
        for content in ("\n".join(lines[:-1]) + "\n" + lines[-1][:20], "\n".join(lines[:-1]) + "\n"):
            path.write_text(content)  # the halt line torn, or gone
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = self.replay(path)
            self.assertTrue(r.halted)
            self.assertEqual(r.halt_reason, "model mismatch: got claude-other")
            r.close()

    def test_halt_recomputed_when_the_halt_line_is_removed(self):
        path = self.dir / "ledger.jsonl"
        lines = self.over_reservation_ledger(path)
        path.write_text("\n".join(lines[:-1]) + "\n")
        self.assertTrue(self.replay(path).halted)

    def test_halt_recomputed_for_spend_over_the_global_cap(self):
        path = self.dir / "ledger.jsonl"
        g = make(ledger_path=path)
        g.reserve("a", OPUS, 1000, 64000)
        g.commit("a", Usage(input_tokens=1000, output_tokens=2000))  # 0.044, fine at the time
        g.close()
        r = self.keep(SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D("199.99")))
        self.assertTrue(r.halted)  # other spend since then: the replayed commit now breaks the global cap
        self.assertIn("global spend", r.halt_reason)

    def test_recover_counts_open_reservations_as_spent(self):
        path = self.dir / "ledger.jsonl"
        self.busy_guard(path)
        r = self.replay(path)
        orphans = r.recover()
        self.assertEqual(list(orphans), ["c"])
        self.assertTrue(orphans["c"].sent)
        self.assertEqual(r.remaining_run, D(30) - r.spent - OPUS_CALL)  # still counted
        with self.assertRaises(ValueError):
            r.release("c")
        r.commit("c", Usage(input_tokens=1000, output_tokens=100))
        self.assertEqual(r.reserved, 0)
        r.close()
        self.assertEqual(self.state(self.replay(path)), self.state(r))

    def test_tampered_or_mismatched_ledger_is_refused(self):
        path = self.dir / "ledger.jsonl"
        self.busy_guard(path)
        lines = path.read_text().splitlines()
        cases = {
            "dropped line": lines[:3] + lines[4:],
            "changed amount": [l.replace('"amount": "1.288"', '"amount": "0.001"', 1) for l in lines],
            "broken middle line": lines[:2] + [lines[2][:20]] + lines[3:],
        }
        for name, content in cases.items():
            path.write_text("\n".join(content) + "\n")
            with self.assertRaises(Exception, msg=name):
                SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D(0))
        path.write_text("\n".join(lines) + "\n")
        for run_id, cap, live in (("other-run", "30", False), ("pilot-test", "40", False)):
            with self.assertRaises(ValueError):
                SpendGuard.replay(path, run_id, D(cap), global_spent_usd=D(0), live=live)

    def test_empty_or_torn_only_ledger_cannot_be_replayed(self):
        path = self.dir / "ledger.jsonl"
        for content in ("", '{"seq": 1, "ev'):
            path.write_text(content)
            with self.assertRaises(ValueError):
                SpendGuard.replay(path, "pilot-test", D("30"), global_spent_usd=D(0))

    def test_commit_note_and_usage_are_logged(self):
        path = self.dir / "ledger.jsonl"
        g = self.keep(make(ledger_path=path))
        g.reserve("a", OPUS, 1000, 64000)
        g.mark_sent("a")
        self.assertEqual(g.commit("a", Usage(), note="http 529, assumed unbilled"), 0)
        last = json.loads(path.read_text().splitlines()[-1])
        self.assertEqual((last["event"], D(last["amount"]), last["note"]), ("commit", 0, "http 529, assumed unbilled"))
        self.assertEqual(last["usage"]["output_tokens"], 0)


class ConsoleCheckTest(LiveFixture):
    """T1, U1-U3: one PASSING Console check for the whole machine confirms that Batch bills at 50%."""

    SMALL = 16000  # an Opus Batch item at this max_tokens reserves 0.164; at 64000, 0.644

    def allow(self, rid, **overrides):
        """V2: the Console check and the clearing need a valid clearance for their run. Each run gets its
        own clearance file, and the review file gets that run's CLEARED line. `overrides` spoil fields."""
        review = self.repo / self.review
        if self.cleared(run_id=rid) not in review.read_text().splitlines():
            review.write_text(review.read_text() + self.cleared(run_id=rid) + "\n")
        path = self.clearance(**dict({"run_id": rid}, **overrides))
        mine = self.dir / f"clearance-{rid}.json"
        mine.write_text(path.read_text())
        return mine

    def live(self, run_id="pilot-test", cap="30", **kw):
        kw.setdefault("clearance_path", self.allow(run_id))
        return super().live(run_id, cap, **kw)

    def replay_live(self, run_id="pilot-test"):
        return self.keep(SpendGuard.replay(None, run_id, D("30"), live=True, repo_root=self.repo,
                                           data_root=self.data, git=self.git, now=lambda: self.now,
                                           clearance_path=self.allow(run_id)))

    def batch_wave(self, g, keys, output=60000, max_tokens=64000, usage=None):
        """Reserve and commit Opus Batch items; each costs (1,000 x 4 + output x 20) / M / 2."""
        g.reserve_many([(k, OPUS, 1000, max_tokens, True) for k in keys])
        for k in keys:  # (sending is not needed to commit; the live gate is tested elsewhere)
            g.commit(k, usage if usage is not None else Usage(input_tokens=1000, output_tokens=output))

    def failed_smoke(self):
        """A smoke run whose Console check FAILS: Batch billed at list would show 1.248, not 0.646."""
        smoke = self.live("smoke")
        smoke.reserve("rt", OPUS, 1000, 64000)
        smoke.commit("rt", Usage(input_tokens=1000, output_tokens=2000))  # real-time 0.044
        self.batch_wave(smoke, ["b1"])  # Batch 0.602 in the ledger
        smoke.record_console_check(D("1.25"), "Console total since the smoke started: $1.25")
        self.assertTrue(smoke.halted)
        self.assertIn("FAILED Console check", smoke.halt_reason)
        smoke.close()

    def test_unchecked_batch_is_limited_to_one_dollar_across_all_runs(self):
        self.assertEqual(guard_module.UNCHECKED_BATCH_LIMIT, D("1"))
        g = self.live()
        with self.assertRaisesRegex(guard_module.ConsoleCheckNeeded, r"over the \$1"):
            g.reserve_many([("big-a", OPUS, 1000, 64000, True), ("big-b", OPUS, 1000, 64000, True)])  # 1.288
        g.reserve_many([("w1", OPUS, 1000, 64000, True)])  # 0.644: the first small wave may go
        g.reserve("rt", OPUS, 1000, 64000)  # real-time calls are never gated
        with self.assertRaises(guard_module.ConsoleCheckNeeded):  # 0.644 + 0.644, even before w1 settles
            g.reserve_many([("w2", OPUS, 1000, 64000, True)])
        g.reserve_many([("w3", OPUS, 1000, self.SMALL, True)])  # 0.644 + 0.164 = 0.808 still fits
        g.close()
        r = self.replay_live()  # the reservations survive a restart
        with self.assertRaises(guard_module.ConsoleCheckNeeded):
            r.reserve_many([("w4", OPUS, 1000, self.SMALL, True), ("w5", OPUS, 1000, self.SMALL, True)])
        r.close()
        other = self.live("run-2")  # and a new run id sees them too
        with self.assertRaises(guard_module.ConsoleCheckNeeded):
            other.reserve_many([("x", OPUS, 1000, self.SMALL, True), ("y", OPUS, 1000, self.SMALL, True)])
        make().reserve_many([("dry", OPUS, 1000, 64000, True)] + [(f"d{i}", OPUS, 1000, 64000, True)
                                                                 for i in range(5)])  # dry: never gated

    def test_u2_reservations_count_even_if_every_batch_item_errored_or_crashed(self):
        errored = self.live("smoke-errored")
        self.batch_wave(errored, ["e1"], usage=Usage())  # all errored: committed at $0
        errored.close()
        crashed = self.live("smoke-crashed")
        crashed.reserve_many([("c1", OPUS, 1000, self.SMALL, True)])  # crashed before any commit
        crashed.close()
        pilot = self.live()
        self.assertEqual(pilot.console_checked, False)
        with self.assertRaises(guard_module.ConsoleCheckNeeded):  # 0.644 + 0.164 + 0.644 > 1
            pilot.reserve_many([("p1", OPUS, 1000, 64000, True)])

    def test_u1_failed_check_blocks_every_live_batch_until_a_human_clears_it(self):
        self.failed_smoke()
        pilot = self.live()
        self.assertFalse(pilot.console_checked)
        for keys, max_tokens in ((["tiny"], 1), (["p1", "p2"], 64000)):  # tiny or pilot-sized: both refused
            with self.assertRaisesRegex(guard_module.ConsoleCheckNeeded, "FAILED Console check"):
                pilot.reserve_many([(k, OPUS, 1000, max_tokens, True) for k in keys])
        pilot.reserve("rt", OPUS, 1000, 64000)  # real-time is not gated
        with self.assertRaises(NotLive):
            make().clear_console_block("dry guards cannot clear")
        with self.assertRaises(ValueError):
            pilot.clear_console_block("  ")
        cleared = pilot.clear_console_block("Console lagged; re-read the invoice: Batch billed at 50%")
        self.assertEqual([run for run, _ in cleared], ["smoke"])
        with self.assertRaises(ValueError):
            pilot.clear_console_block("nothing left to clear")
        pilot.reserve_many([("small", OPUS, 1000, self.SMALL, True)])  # 0.602 + 0.164: under the $1 limit
        with self.assertRaises(guard_module.ConsoleCheckNeeded):  # clearing does not open the gate
            pilot.reserve_many([("big", OPUS, 1000, 64000, True)])
        pilot.close()
        later = self.live("run-3")  # the clearing is in pilot's ledger, so every later run sees it
        self.assertFalse(later.console_checked)
        later.close()
        self.assertTrue(self.replay_live("smoke").halted)  # the failed run itself stays halted

    def test_u1_a_check_line_that_claims_to_pass_but_does_not_is_a_failure(self):
        g = self.live("smoke")
        self.batch_wave(g, ["b1"])
        g.record_console_check(D("0.61"), "Console: $0.61")
        g.close()
        lines = g.ledger_path.read_text().splitlines()
        check = json.loads(lines[-1])
        check["dollars_seen"] = "1.25"  # passed: true stays, but its own figures disagree
        lines[-1] = json.dumps(check, sort_keys=True)
        g.ledger_path.write_text("\n".join(lines) + "\n")
        with self.assertRaises(guard_module.ConsoleCheckNeeded):
            self.live().reserve_many([("p1", OPUS, 1000, 1, True)])

    def test_u3_floor_counts_batch_spend_across_all_live_ledgers(self):
        first = self.live("smoke-1")
        self.batch_wave(first, ["a", "b", "c"], output=1000, max_tokens=self.SMALL)  # 3 x 0.012 = 0.036
        with self.assertRaisesRegex(ValueError, "below"):
            first.record_console_check(D("0.036"), "Console: $0.04")
        first.close()
        second = self.live("smoke-2")
        self.batch_wave(second, ["d", "e"], output=1000, max_tokens=self.SMALL)  # + 0.024 = 0.060
        second.record_console_check(D("0.06"), "Console total since smoke-1 started: $0.06")
        self.assertTrue(second.console_checked)
        second.close()
        pilot = self.live()
        # N61: smoke-2's pass covers two ledgers, so another run cannot vouch for it and ignores it ...
        self.assertFalse(pilot.console_checked)
        with self.assertRaises(guard_module.ConsoleCheckNeeded):
            pilot.reserve_many([(f"p{i}", OPUS, 1000, 64000, True) for i in range(20)])
        # ... so the pilot records its own check (same Console total) and goes on.
        pilot.record_console_check(D("0.06"), "Console total since smoke-1 started: $0.06")
        pilot.reserve_many([(f"p{i}", OPUS, 1000, 64000, True) for i in range(20)])  # $12.88: the gate is open

    def test_v1_clearing_a_later_failure_does_not_revive_an_earlier_pass(self):
        smoke = self.live("smoke")
        self.batch_wave(smoke, ["b1"])  # 0.602 of Batch spend
        smoke.record_console_check(D("0.61"), "Console: $0.61")  # pass
        self.assertTrue(smoke.console_checked)
        smoke.record_console_check(D("1.25"), "Console later: $1.25")  # then a FAILED check
        self.assertFalse(smoke.console_checked)
        smoke.close()
        pilot = self.live()
        voided_before = pilot.console_checked
        cleared = pilot.clear_console_block("investigated: a Console display error")
        self.assertEqual([r for r, _ in cleared], ["smoke"])
        self.assertFalse(voided_before)
        self.assertFalse(pilot.console_checked)  # the old pass was voided by the clearing
        with self.assertRaises(guard_module.ConsoleCheckNeeded):  # a big Batch waits for a NEW pass
            pilot.reserve_many([("p1", OPUS, 1000, 64000, True), ("p2", OPUS, 1000, 64000, True)])
        pilot.close()
        later = self.live("run-3")  # the voiding is in the pilot's ledger, so every later run sees it
        self.assertFalse(later.console_checked)
        later.record_console_check(D("0.61"), "Console total, re-read after the clearing: $0.61")  # NEW pass
        later.reserve_many([("p1", OPUS, 1000, 64000, True), ("p2", OPUS, 1000, 64000, True)])

    def test_v2_check_and_clearing_need_a_valid_clearance(self):
        g = self.live("smoke")
        self.batch_wave(g, ["b1"])
        for name, overrides in (("user_go no", {"user_go": "no"}), ("expired", {"expires": "2026-10-10"}),
                                ("other run", {"run_id": "other-run"})):
            g.clearance_path = self.allow("smoke", **overrides)
            with self.assertRaises(NotLive, msg=name):
                g.record_console_check(D("0.61"), "Console: $0.61")
            with self.assertRaises(NotLive, msg=name):
                g.clear_console_block("note")
        self.assertFalse(g.console_checked)
        with self.assertRaises(NotLive):  # a dry guard can do neither
            make().record_console_check(D("0.61"), "Console")
        with self.assertRaises(NotLive):
            make().clear_console_block("note")
        g.clearance_path = self.allow("smoke")
        g.record_console_check(D("0.61"), "Console: $0.61")
        self.assertTrue(g.console_checked)

    def forge(self, run_id, *events):
        """Write a hand-made live ledger under the shared root (N61)."""
        path = guard_module.ledger_path_for(self.data, run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [{"seq": 1, "run_id": run_id, "event": "open", "live": True, "run_cap": "2"}]
        for n, event in enumerate(events, start=2):
            lines.append(dict(event, seq=n, run_id=run_id))
        path.write_text("".join(json.dumps(l) + "\n" for l in lines))

    def test_n61_a_forged_pass_in_another_ledger_opens_nothing(self):
        big = [("p1", OPUS, 1000, 64000, True), ("p2", OPUS, 1000, 64000, True)]
        zero = {"event": "console_check", "passed": True, "dollars_seen": "0", "ledger_total": "0",
                "raw_total": "0", "batch_billed": "0", "batch_raw": "0", "spent": "0", "reserved": "0"}
        self.forge("forged-zero", zero)  # "0 vs 0" claims to pass: it is a FAILED check and blocks
        first = self.live()
        with self.assertRaisesRegex(guard_module.ConsoleCheckNeeded, "FAILED"):
            first.reserve_many(big)
        first.close()
        shutil.rmtree(self.data / "raw" / "forged-zero")
        plausible = dict(zero, dollars_seen="0.61", ledger_total="0.61", raw_total="0.61", batch_billed="0.61",
                         batch_raw="0.61")
        self.forge("forged-plausible", plausible)  # figures agree, but this ledger never spent anything
        g = self.live("pilot-2")
        self.assertFalse(g.console_checked)
        with self.assertRaisesRegex(guard_module.ConsoleCheckNeeded, r"over the \$1"):
            g.reserve_many(big)

    def free_refusal(self, g, key="ref", input_tokens=2000):
        """S2: a real-time Opus refusal before any output, free by billing rule B5, booked conservatively."""
        g.reserve(key, OPUS, input_tokens, 64000)
        return g.commit(key, Usage(input_tokens=input_tokens), free_by_rule=True)

    def test_s2_free_commit_keeps_spend_and_caps_but_leaves_the_adjusted_figure(self):
        g = self.live()
        self.assertEqual(self.free_refusal(g), D("0.008"))  # the full usage cost, as before
        g.reserve("ok", OPUS, 1000, 64000)
        g.commit("ok", Usage(input_tokens=1000, output_tokens=2000))  # 0.044, billed
        self.assertEqual(g.spent, D("0.052"))  # spend and the caps still count the refusal
        self.assertEqual(g.remaining_run, D("30") - D("0.052"))
        self.assertEqual(g.rule_adjusted_spent, D("0.044"))
        g.reserve("x", OPUS, 1, 1)
        with self.assertRaises(TypeError):
            g.commit("x", Usage(), free_by_rule="yes")
        g.release("x")
        g.close()
        lines = [json.loads(l) for l in g.ledger_path.read_text().splitlines()]
        self.assertEqual([l["free_by_rule"] for l in lines if l["event"] == "commit"], [True, False])
        r = self.replay_live()
        self.assertEqual((r.spent, r.rule_adjusted_spent), (D("0.052"), D("0.044")))  # replay restores it

    def test_s2_exact_console_figure_passes_against_the_adjusted_total(self):
        g = self.live("smoke")
        self.free_refusal(g, input_tokens=20000)  # 0.08 booked, free by B5
        self.batch_wave(g, ["b1"])  # Batch 0.602: adjusted 0.602, raw 0.682
        with self.assertRaises(guard_module.ConsoleNotUpdated):  # the 95% floor is on the adjusted figure
            g.record_console_check(D("0.57"), "Console: $0.57")
        g.record_console_check(D("0.602"), "Console: $0.602, the B5-billed figure")
        self.assertTrue(g.console_checked)
        g.close()
        line = [json.loads(l) for l in g.ledger_path.read_text().splitlines() if '"console_check"' in l][-1]
        self.assertEqual((D(line["ledger_total"]), D(line["raw_total"])), (D("0.602"), D("0.682")))
        later = self.live("run-2")  # N61 still accepts it: scan_ledger recomputes the adjusted figure
        self.assertTrue(later.console_checked)

    def test_s2_free_refusal_plus_batch_billed_at_list_fails(self):
        g = self.live("smoke")
        self.free_refusal(g)  # 0.008 booked, free by B5
        self.batch_wave(g, ["b1"])  # adjusted 0.602; at list the Console would show 1.204
        g.record_console_check(D("1.204"), "Console: $1.204")
        self.assertTrue(g.halted)
        self.assertFalse(g.console_checked)

    def test_s2_console_showing_the_raw_figure(self):
        """The rule: fail when the Console is over the ADJUSTED total by more than 5% + 1 cent, even if it
        is at or under the raw total. A Console at the raw figure then passes only if the free refusals
        are small enough to sit inside the tolerance; otherwise B5 looks wrong and a human decides."""
        small = self.live("smoke-small")
        self.free_refusal(small)  # 0.008: raw 0.610, adjusted 0.602, upper edge 0.6421
        self.batch_wave(small, ["b1"])
        small.record_console_check(D("0.610"), "Console shows the raw figure")
        self.assertTrue(small.console_checked)
        small.close()
        big = self.live("smoke-big")
        self.free_refusal(big, input_tokens=20000)  # 0.08: raw 0.682 + 0.610 earlier, adjusted lower
        self.batch_wave(big, ["b2"])
        raw, adjusted = big._machine_totals()
        self.assertGreater(raw, adjusted * D("1.05") + D("0.01"))
        big.record_console_check(raw, "Console shows the raw figure: the free refusals were billed?")
        self.assertTrue(big.halted)  # B5 looks wrong: a FAILED check

    def test_p1_floor_met_only_by_free_batch_refusals_is_refused(self):
        g = self.live("smoke")
        keys = [f"ref{i}" for i in range(8)]
        g.reserve_many([(k, OPUS, 4500, 1, True) for k in keys] + [("ok", HAIKU, 1000, 3000, True)])
        for k in keys:  # 8 Opus Batch refusals before any output, free by B5: 0.009 each, booked in full
            g.commit(k, Usage(input_tokens=4500), free_by_rule=True)
        g.commit("ok", Usage(input_tokens=1000, output_tokens=3000))  # one billed Haiku answer: 0.0008
        self.assertEqual(g._machine_batch(), (D("0.0728"), D("0.0008")))
        with self.assertRaisesRegex(ValueError, "BILLED Batch spend"):  # raw 0.0728 would have met the floor
            g.record_console_check(D("0.0008"), "Console: $0.0008")
        self.assertFalse(g.console_checked)

    def test_p1_floor_met_by_billed_batch_spend_passes_and_is_recorded(self):
        g = self.live("smoke")
        g.reserve_many([("ref", OPUS, 4500, 1, True), ("b1", OPUS, 1000, 64000, True)])
        g.commit("ref", Usage(input_tokens=4500), free_by_rule=True)  # free Batch refusal: 0.009
        g.commit("b1", Usage(input_tokens=1000, output_tokens=60000))  # billed Batch: 0.602
        g.record_console_check(D("0.602"), "Console: $0.602")
        self.assertTrue(g.console_checked)
        g.close()
        line = [json.loads(l) for l in g.ledger_path.read_text().splitlines() if '"console_check"' in l][-1]
        self.assertEqual((D(line["batch_billed"]), D(line["batch_raw"])), (D("0.602"), D("0.611")))
        later = self.live("run-2")  # N61 recomputes both Batch figures from the smoke's commits
        self.assertTrue(later.console_checked)

    def test_p2_forged_batch_figures_on_an_empty_ledger_open_nothing(self):
        forged = {"event": "console_check", "passed": True, "dollars_seen": "0", "ledger_total": "0",
                  "raw_total": "0", "batch_billed": "0.05", "batch_raw": "0.05", "spent": "0", "reserved": "0"}
        self.forge("forged-batch", forged)  # passes check_passed, but this ledger has no Batch commit at all
        g = self.live()
        self.assertFalse(g.console_checked)
        with self.assertRaisesRegex(guard_module.ConsoleCheckNeeded, r"over the \$1"):
            g.reserve_many([("p1", OPUS, 1000, 64000, True), ("p2", OPUS, 1000, 64000, True)])

    # ---- P3: ledgers written before free_by_rule existed (smoke-2, M-format)

    SMOKE2_FREE = {"smoke-pilot-digits-d4s-v1-000-1x24-rto-01#a1": D("0.01748"),  # real-time Opus refusal
                   "smoke-pilot-digits-d4s-v1-000-24x1-bo-01@1": D("0.009292")}  # Batch Opus refusal

    def legacy_smoke2(self):
        """Copy the REAL smoke-2 ledger (read only) under this test's shared root."""
        try:
            common = git_runner_for(REPO)(["rev-parse", "--git-common-dir"]).strip()
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available")
        src = (REPO / common).resolve().parent / "data" / "raw" / "smoke-2" / "ledger.jsonl"
        if not src.is_file():
            self.skipTest("the real smoke-2 ledger is not on this machine")
        dst = guard_module.ledger_path_for(self.data, "smoke-2")
        dst.parent.mkdir(parents=True, exist_ok=True)
        # The real ledger now carries the two D-65 markers. These tests need the ledger as it was written in smoke-2 (before any
        # free_by_rule existed), so the appended `free_by_rule_marked` events are left out of the copy.
        keep = [ln for ln in src.read_text().splitlines(keepends=True) if '"event": "free_by_rule_marked"' not in ln]
        dst.write_text("".join(keep))
        return dst

    def replay_smoke2(self):
        return self.keep(SpendGuard.replay(None, "smoke-2", D("2"), live=True, repo_root=self.repo,
                                           data_root=self.data, git=self.git, now=lambda: self.now,
                                           clearance_path=self.allow("smoke-2", cap_usd="2")))

    def check_batch(self, g):
        """A check Batch inside the $1 limit: 2 Opus items, 0.032 billed each."""
        g.reserve_many([(k, OPUS, 1000, self.SMALL, True) for k in ("c1", "c2")])
        for k in ("c1", "c2"):
            g.commit(k, Usage(input_tokens=1000, output_tokens=3000))

    def test_p3_legacy_ledger_blocks_the_check_without_markers(self):
        self.legacy_smoke2()
        check = self.live("check")
        self.check_batch(check)
        raw, adjusted = check._machine_totals()
        self.assertEqual(raw, adjusted)  # nothing in the legacy ledger is flagged free
        true_console = adjusted - sum(self.SMOKE2_FREE.values())  # what the Console really bills
        with self.assertRaises(guard_module.ConsoleNotUpdated):  # Edith's P3: refused for good
            check.record_console_check(true_console, "Console: the true B5 figure")

    def test_p3_markers_make_the_legacy_ledger_checkable(self):
        path = self.legacy_smoke2()
        smoke = self.replay_smoke2()
        before = smoke.rule_adjusted_spent
        for key, amount in self.SMOKE2_FREE.items():
            got = smoke.mark_free_by_rule(key, "cyber", "call log: refusal_billed_by_rule false, category cyber")
            self.assertEqual(got, amount)
        self.assertEqual(smoke.spent, D("0.07062435"))  # spend and caps unchanged
        self.assertEqual(smoke.rule_adjusted_spent, before - D("0.026772"))
        smoke.close()
        again = self.replay_smoke2()
        self.assertEqual(again.rule_adjusted_spent, before - D("0.026772"))  # replay honours them
        again.close()
        self.assertEqual([json.loads(l)["event"] for l in path.read_text().splitlines()[-2:]],
                         ["free_by_rule_marked", "free_by_rule_marked"])  # appended; nothing rewritten
        check = self.live("check")
        self.check_batch(check)
        raw, adjusted = check._machine_totals()  # scan_ledger honours the markers too
        self.assertEqual(raw - adjusted, D("0.026772"))
        check.record_console_check(adjusted, "Console: the true B5 figure")
        self.assertTrue(check.console_checked)

    def test_p3_marker_is_refused_unless_it_names_a_free_refusal(self):
        self.legacy_smoke2()
        smoke = self.replay_smoke2()
        opus_rt = "smoke-pilot-digits-d4s-v1-000-1x24-rto-01#a1"
        haiku = "smoke-pilot-digits-d4s-v1-000-1x24-rth-01#a1"  # an answer: 2,724 output tokens
        with self.assertRaises(ValueError):
            smoke.mark_free_by_rule(haiku, "cyber", "evidence")
        with self.assertRaises(KeyError):
            smoke.mark_free_by_rule("no-such-key", "cyber", "evidence")
        for category in ("bio", "frontier_llm", "reasoning_extraction", ""):
            with self.assertRaises(ValueError, msg=category):
                smoke.mark_free_by_rule(opus_rt, category, "evidence")
        with self.assertRaises(ValueError):
            smoke.mark_free_by_rule(opus_rt, "cyber", "  ")
        smoke.mark_free_by_rule(opus_rt, "cyber", "evidence")
        with self.assertRaises(ValueError):  # not twice
            smoke.mark_free_by_rule(opus_rt, "cyber", "evidence")
        with self.assertRaises(NotLive):  # a dry guard cannot mark
            make().mark_free_by_rule(opus_rt, "cyber", "evidence")
        smoke.clearance_path = self.allow("smoke-2", cap_usd="2", user_go="no")
        with self.assertRaises(NotLive):  # nor a guard without a valid clearance
            smoke.mark_free_by_rule("smoke-pilot-digits-d4s-v1-000-24x1-bo-01@1", "cyber", "evidence")

    def test_p3_hand_written_invalid_marker(self):
        path = self.legacy_smoke2()
        last = json.loads(path.read_text().splitlines()[-1])
        forged = {"event": "free_by_rule_marked", "key": "smoke-pilot-digits-d4s-v1-000-1x24-rth-01#a1",
                  "category": "cyber", "note": "forged", "amount": "0.001799", "seq": last["seq"] + 1,
                  "run_id": "smoke-2", "spent": last["spent"], "reserved": last["reserved"]}
        with open(path, "a") as fh:
            fh.write(json.dumps(forged) + "\n")  # marks an ANSWER (output tokens > 0) free
        with self.assertRaisesRegex(ValueError, "invalid free_by_rule_marked"):  # its own replay refuses it
            SpendGuard.replay(None, "smoke-2", D("2"), live=True, repo_root=self.repo, data_root=self.data,
                              git=self.git, now=lambda: self.now)
        check = self.live("check")  # another run ignores it: nothing becomes free
        raw, adjusted = check._machine_totals()
        self.assertEqual(raw, adjusted)

    def test_check_refused_while_batch_keys_are_open_or_before_any_batch_item(self):
        g = self.live()
        g.reserve("rt", OPUS, 1000, 64000)
        g.commit("rt", Usage(input_tokens=1000, output_tokens=2000))
        with self.assertRaisesRegex(ValueError, "no live ledger has a committed Batch item"):
            g.record_console_check(D("0.044"), "Console: $0.04")
        g.reserve_many([("b1", OPUS, 1000, 64000, True)])
        with self.assertRaisesRegex(ValueError, "still open"):
            g.record_console_check(D("0.044"), "Console: $0.04")
        g.close()
        r = self.live("run-2")  # open Batch keys in ANOTHER live ledger (a crashed run) also block it
        with self.assertRaisesRegex(ValueError, "still open"):
            r.record_console_check(D("0.044"), "Console: $0.04")
        self.assertFalse(r.console_checked)

    def test_batch_spend_floor_is_fixed_at_five_cents(self):
        self.assertEqual(guard_module.MIN_BATCH_SPEND_FOR_CHECK, D("0.05"))
        g = self.live()
        self.batch_wave(g, ["a", "b", "c"], output=1000, max_tokens=self.SMALL)  # 0.036 of Batch spend
        with self.assertRaisesRegex(ValueError, "below"):
            g.record_console_check(D("0.036"), "Console: $0.04")
        with self.assertRaises(TypeError):  # there is no argument to lower the floor
            g.record_console_check(D("0.036"), "Console", min_batch_spend=D("0.01"))
        self.assertFalse(g.console_checked)

    def test_console_compared_with_the_ledger_total(self):
        g = self.live()
        g.reserve("rt", OPUS, 1000, 64000)
        g.commit("rt", Usage(input_tokens=1000, output_tokens=2000))  # real-time 0.044
        self.batch_wave(g, ["a"])  # Batch 0.602; ledger total 0.646
        for bad in (1.0, "0.65", D("-1")):
            with self.assertRaises(TypeError):
                g.record_console_check(bad, "Console")
        with self.assertRaises(ValueError):
            g.record_console_check(D("0.65"), "  ")
        with self.assertRaises(guard_module.ConsoleNotUpdated):  # Batch alone, or a lagging Console
            g.record_console_check(D("0.60"), "Console: $0.60")
        self.assertFalse(g.console_checked)
        g.record_console_check(D("0.65"), "Console total since this run started: $0.65")
        self.assertTrue(g.console_checked)
        self.assertFalse(g.halted)
        g.close()
        self.assertTrue(self.replay_live().console_checked)

    def test_console_showing_batch_billed_at_list_halts_and_survives_replay(self):
        self.failed_smoke()
        r = self.replay_live("smoke")
        lines = r.ledger_path.read_text().splitlines()
        self.assertTrue(r.halted)
        self.assertFalse(r.console_checked)
        r.close()
        r.ledger_path.write_text("\n".join(lines[:-1]) + "\n")  # lose the halt line: still halted, still failed
        r2 = self.replay_live("smoke")
        self.assertTrue(r2.halted)
        self.assertFalse(r2.console_checked)

    def test_tolerance_edges(self):
        g = self.live()
        self.batch_wave(g, ["a"])  # 0.602
        upper = D("0.602") * D("1.05") + D("0.01")  # 0.6421
        g.record_console_check(upper, "Console at the upper edge")
        self.assertFalse(g.halted)
        self.assertTrue(g.console_checked)
        g.record_console_check(upper + D("0.0001"), "Console just over the edge")
        self.assertTrue(g.halted)
        self.assertFalse(g.console_checked)  # a failed check now outweighs the earlier pass


class SpendLogTest(TempDirTest):
    def test_reads_the_real_spend_log(self):
        real = REPO / "ops" / "spend-log.md"
        self.assertEqual(read_spent_from_spend_log(real), sum((usd for usd, _ in guard_module.spend_log_rows(real).values()), D("0")))

    def test_needs_exactly_one_line(self):
        path = self.dir / "log.md"
        path.write_text("| Spent (rows below) | 12.34 |\n")
        self.assertEqual(read_spent_from_spend_log(path), D("12.34"))
        for text in ("| Credit | 200.00 |\n", "| Spent (rows below) | 1.00 |\n| Spent (rows below) | 2.00 |\n",
                     "| Spent (rows below) | -1.00 |\n"):
            path.write_text(text)
            with self.assertRaises(ValueError):
                read_spent_from_spend_log(path)


# ============================================================================ threads

def race(g, n_threads=200):
    """n_threads reserve one Haiku call each, all released at once. Returns how many succeeded."""
    barrier = threading.Barrier(n_threads)
    wins = []

    def worker(i):
        barrier.wait()
        try:
            g.reserve(f"t{i}", HAIKU, 0, 1000)  # $0.0005 each
            wins.append(i)
        except CapExceeded:
            pass

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return len(wins)


class ConcurrencyTest(TempDirTest):
    def test_200_threads_never_pass_the_cap(self):
        for ledger in (None, self.dir / "ledger.jsonl"):
            g = self.keep(make("0.025", ledger_path=ledger))  # room for exactly 50
            self.assertEqual(race(g), 50)
            self.assertEqual(g.reserved, D("0.025"))

    def test_concurrent_reserve_and_commit(self):
        path = self.dir / "ledger.jsonl"
        g = make("0.05", ledger_path=path)
        errors = []

        def worker(i):
            try:
                g.reserve(f"t{i}", HAIKU, 0, 1000)
            except CapExceeded:
                return
            try:
                g.mark_sent(f"t{i}")
                g.commit(f"t{i}", Usage(output_tokens=1000))
            except Exception as exc:  # would fail the test below
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual((g.spent, g.reserved), (D("0.05"), 0))  # every slot used once
        g.close()
        r = self.keep(SpendGuard.replay(path, "pilot-test", D("0.05"), global_spent_usd=D(0)))
        self.assertEqual((r.spent, r.reserved), (g.spent, g.reserved))


# ============================================================================ mutations

class NoLock:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def run_test(cls, name):
    """Run one test method on a fresh instance, with its setUp and cleanups."""
    case = cls(name)
    case.setUp()
    try:
        getattr(case, name)()
    finally:
        case.doCleanups()
        case.tearDown()


class MutationTest(unittest.TestCase):
    """Break guard.py on purpose and check that a test above fails. Shows the tests bite."""

    def caught(self, patcher, cls, name):
        with patcher:
            with self.assertRaises(AssertionError, msg=f"mutant not caught by {name}"):
                run_test(cls, name)

    def test_skipping_the_cap_check_is_caught(self):
        for name in ("test_refuses_over_run_cap", "test_refuses_over_global_cap"):
            self.caught(mock.patch.object(SpendGuard, "_check_fits", lambda self, amount, what: None),
                        ReserveTest, name)

    def test_removing_the_lock_is_caught(self):
        real = SpendGuard._check_fits

        def slow_check(self, amount, what):
            real(self, amount, what)
            time.sleep(0.002)  # widen the gap between the check and the booking

        with mock.patch.object(SpendGuard, "_check_fits", slow_check):
            g = make("0.025")
            g._lock = NoLock()
            self.assertGreater(race(g), 50, "without the lock, more than the cap gets reserved")
            self.assertEqual(race(make("0.025")), 50)

    def test_batch_at_list_or_ignored_is_caught(self):
        real = prices.worst_case

        def no_batch(model, est, max_tokens, batch=False):
            return real(model, est, max_tokens)
        self.caught(mock.patch.object(guard_module.prices, "worst_case", no_batch),
                    ReserveTest, "test_batch_reservation_is_exactly_half_of_list")

    def test_trusting_the_batch_price_on_commit_is_caught(self):
        real_cost = prices.cost
        self.caught(mock.patch.object(guard_module.prices, "cost", lambda m, u, b=False: real_cost(m, u, True)),
                    CommitReleaseTest, "test_batch_item_billed_at_list_halts")

    def test_b1_r2_ignoring_ledgers_or_rows_is_caught(self):
        real_scan = guard_module.scan_ledger
        self.caught(mock.patch.object(guard_module, "scan_ledger", lambda p: dict(real_scan(p), exposure=D(0))),
                    LiveSetupTest, "test_global_spend_is_added_up_per_run")
        self.caught(mock.patch.object(guard_module, "spend_log_rows", lambda p: {}),
                    LiveSetupTest, "test_global_spend_is_added_up_per_run")
        self.caught(mock.patch.object(guard_module, "ledger_ok_amount", lambda notes: D("1.312")),
                    LiveSetupTest, "test_row_and_ledger_must_agree_or_carry_a_note")

    def test_r1_per_checkout_root_is_caught(self):
        self.caught(mock.patch.object(guard_module, "shared_data_root", lambda repo, git: Path(repo) / "data"),
                    SharedRootTest, "test_two_checkouts_share_the_lock_and_see_each_others_spend")

    def test_r4_dropping_the_callers_halt_on_replay_is_caught(self):
        real_apply = SpendGuard._apply
        self.caught(mock.patch.object(SpendGuard, "_apply",
                                      lambda self, line, n: real_apply(self, dict(line, halt_reason=""), n)),
                    LedgerTest, "test_caller_halt_goes_with_the_commit")

    def test_r8_loose_go_or_expiry_is_caught(self):
        self.caught(mock.patch.object(guard_module, "GO_PATTERN", r"."), LiveGateTest, "test_rejections")
        self.caught(mock.patch.object(guard_module, "MAX_CLEARANCE_DAYS", 10000), LiveGateTest, "test_rejections")

    def test_t1_weakening_the_console_check_is_caught(self):
        self.caught(mock.patch.object(SpendGuard, "_console_gate_reason", lambda self, amount: ""),
                    ConsoleCheckTest, "test_unchecked_batch_is_limited_to_one_dollar_across_all_runs")
        self.caught(mock.patch.object(guard_module, "MIN_BATCH_SPEND_FOR_CHECK", D("0")),
                    ConsoleCheckTest, "test_batch_spend_floor_is_fixed_at_five_cents")
        self.caught(mock.patch.object(guard_module, "CONSOLE_MIN_SHARE", D("0")),
                    ConsoleCheckTest, "test_console_compared_with_the_ledger_total")
        self.caught(mock.patch.object(guard_module, "console_over", lambda seen, total: False),
                    ConsoleCheckTest, "test_console_showing_batch_billed_at_list_halts_and_survives_replay")
        self.caught(mock.patch.object(guard_module, "CONSOLE_TOLERANCE", (D("2"), D("0.01"))),
                    ConsoleCheckTest, "test_tolerance_edges")

    def test_u1_counting_a_failed_check_as_passing_is_caught(self):
        self.caught(mock.patch.object(guard_module, "check_passed", lambda line: True),
                    ConsoleCheckTest, "test_u1_a_check_line_that_claims_to_pass_but_does_not_is_a_failure")
        self.caught(mock.patch.object(SpendGuard, "_unresolved_failures", lambda self: set()),
                    ConsoleCheckTest, "test_u1_failed_check_blocks_every_live_batch_until_a_human_clears_it")

    def test_u2_gate_keyed_on_spend_or_without_a_limit_is_caught(self):
        real_scan = guard_module.scan_ledger
        self.caught(mock.patch.object(guard_module, "scan_ledger",
                                      lambda p: dict(real_scan(p), batch_reserved=real_scan(p)["batch_spent"])),
                    ConsoleCheckTest, "test_u2_reservations_count_even_if_every_batch_item_errored_or_crashed")
        self.caught(mock.patch.object(guard_module, "UNCHECKED_BATCH_LIMIT", D("1000")),
                    ConsoleCheckTest, "test_unchecked_batch_is_limited_to_one_dollar_across_all_runs")

    def test_s2_comparing_the_raw_total_is_caught(self):
        def raw_only(self):
            raw = self._spent + self._others["spent"]
            return raw, raw
        with mock.patch.object(SpendGuard, "_machine_totals", raw_only):
            with self.assertRaises(Exception):  # the exact B5 figure is refused as "not updated yet"
                run_test(ConsoleCheckTest, "test_s2_exact_console_figure_passes_against_the_adjusted_total")

    def test_s2_losing_the_free_flag_on_replay_is_caught(self):
        real_apply = SpendGuard._apply
        self.caught(mock.patch.object(SpendGuard, "_apply",
                                      lambda self, line, n: real_apply(self, dict(line, free_by_rule=False), n)),
                    ConsoleCheckTest, "test_s2_free_commit_keeps_spend_and_caps_but_leaves_the_adjusted_figure")

    def test_s2_n61_ignoring_free_commits_is_caught(self):
        def round5_rule(line, committed, free, *batch):
            return D(line["ledger_total"]) == committed and D(line["spent"]) == committed
        self.caught(mock.patch.object(guard_module, "ledger_check_consistent", round5_rule),
                    ConsoleCheckTest, "test_s2_exact_console_figure_passes_against_the_adjusted_total")

    def test_p3_accepting_any_marker_is_caught(self):
        self.caught(mock.patch.object(guard_module, "marker_valid", lambda marker, commit: True),
                    ConsoleCheckTest, "test_p3_hand_written_invalid_marker")
        self.caught(mock.patch.object(guard_module, "marker_valid", lambda marker, commit: True),
                    ConsoleCheckTest, "test_p3_marker_is_refused_unless_it_names_a_free_refusal")

    def test_p3_ignoring_markers_is_caught(self):
        real_scan = guard_module.scan_ledger
        with mock.patch.object(guard_module, "scan_ledger", lambda p: dict(real_scan(p), free_spent=D("0"))):
            with self.assertRaises(Exception):  # the check is refused as "not updated yet" again
                run_test(ConsoleCheckTest, "test_p3_markers_make_the_legacy_ledger_checkable")
        with mock.patch.object(SpendGuard, "_apply_marker", lambda self, commit: None):
            with self.assertRaises(Exception):
                run_test(ConsoleCheckTest, "test_p3_markers_make_the_legacy_ledger_checkable")

    def test_p1_floor_on_raw_batch_spend_is_caught(self):
        def raw_batch(self):
            raw = self._batch_spent + self._others["batch_spent"]
            return raw, raw
        self.caught(mock.patch.object(SpendGuard, "_machine_batch", raw_batch),
                    ConsoleCheckTest, "test_p1_floor_met_only_by_free_batch_refusals_is_refused")

    def test_p2_consistency_without_batch_figures_is_caught(self):
        def s2_rule(line, committed, free, *batch):  # the S2 rule: totals only, no Batch figures
            return (D(line["spent"]) == committed and D(line["raw_total"]) == committed
                    and D(line["ledger_total"]) == committed - free)
        self.caught(mock.patch.object(guard_module, "ledger_check_consistent", s2_rule),
                    ConsoleCheckTest, "test_p2_forged_batch_figures_on_an_empty_ledger_open_nothing")

    def test_v1_reviving_voided_passes_is_caught(self):
        self.caught(mock.patch.object(SpendGuard, "_valid_passes",
                                      lambda self: self._passes | self._others["passes"]),
                    ConsoleCheckTest, "test_v1_clearing_a_later_failure_does_not_revive_an_earlier_pass")

    def test_v2_skipping_the_live_gate_is_caught(self):
        self.caught(mock.patch.object(SpendGuard, "require_live", lambda self: None),
                    ConsoleCheckTest, "test_v2_check_and_clearing_need_a_valid_clearance")

    def test_n61_trusting_another_ledgers_pass_is_caught(self):
        self.caught(mock.patch.object(guard_module, "ledger_check_consistent", lambda *a: True),
                    ConsoleCheckTest, "test_n61_a_forged_pass_in_another_ledger_opens_nothing")

        def no_floor(line):  # the round-4 rule: no $0.05 floor on a recorded pass
            return line.get("passed") is True and not guard_module.console_over(
                D(line["dollars_seen"]), D(line["ledger_total"]))
        self.caught(mock.patch.object(guard_module, "check_passed", no_floor),
                    ConsoleCheckTest, "test_n61_a_forged_pass_in_another_ledger_opens_nothing")

    def test_u3_floor_counting_only_this_run_is_caught(self):
        real_scan = guard_module.scan_ledger
        with mock.patch.object(guard_module, "scan_ledger", lambda p: dict(real_scan(p), batch_spent=D("0"))):
            with self.assertRaisesRegex(ValueError, "below"):  # the check is refused: a deadlock again
                run_test(ConsoleCheckTest, "test_u3_floor_counts_batch_spend_across_all_live_ledgers")

    def test_t5_stripped_or_rootless_cleared_line_is_caught(self):
        def loose(self, value, commit):  # the round-2 rule: stripped lines, no ledger root
            text = (self.repo_root / value).read_text()
            if f"CLEARED: {self.run_id} {commit}" not in [l.strip() for l in text.splitlines()]:
                raise NotLive("no line")
        self.caught(mock.patch.object(SpendGuard, "_check_review_file", loose),
                    LiveGateTest, "test_review_file_must_have_the_exact_cleared_line")

    def test_t6_skipping_the_env_file_check_is_caught(self):
        self.caught(mock.patch.object(SpendGuard, "_check_env_file", lambda self, value: self.repo_root / ".env"),
                    SharedRootTest, "test_clearance_must_name_the_shared_root_and_the_main_env_file")

    def test_t7_r11_wide_or_narrow_dirty_check_is_caught(self):
        for rule in (["status", "--porcelain", "--", "harness/"],
                     ["status", "--porcelain", "--", ".", ":(exclude)data", ":(exclude)ops/reviews"]):
            self.caught(mock.patch.object(guard_module, "DIRTY_CHECK", rule),
                        LiveGateTest, "test_dirty_check_covers_the_whole_tree_but_data_raw_and_reviews")

    def test_h2_no_file_lock_is_caught(self):
        self.caught(mock.patch.object(guard_module.fcntl, "flock", lambda fd, op: None),
                    LockTest, "test_one_guard_per_ledger")
        self.caught(mock.patch.object(guard_module.fcntl, "flock", lambda fd, op: None),
                    LockTest, "test_only_one_live_run_at_a_time")

    def test_h1_skipping_git_or_review_checks_is_caught(self):
        self.caught(mock.patch.object(SpendGuard, "_check_git", lambda self, commit: None),
                    LiveGateTest, "test_dirty_tree_or_git_failure_refused")
        self.caught(mock.patch.object(SpendGuard, "_check_review_file", lambda self, value, commit: None),
                    LiveGateTest, "test_review_file_must_have_the_exact_cleared_line")
        self.caught(mock.patch.object(SpendGuard, "_check_prices_and_expiry", lambda self, data, now: None),
                    LiveGateTest, "test_prices_must_be_checked_today_or_yesterday")

    def test_h5_trusting_halt_lines_is_caught(self):
        real_apply = SpendGuard._apply

        def trusting_apply(self, line, number):  # replay without recomputing halts from commits
            with mock.patch.object(SpendGuard, "_halt_reason", lambda *a: ""):
                real_apply(self, line, number)
        self.caught(mock.patch.object(SpendGuard, "_apply", trusting_apply),
                    LedgerTest, "test_halt_recomputed_when_the_halt_line_is_removed")


if __name__ == "__main__":
    unittest.main()
