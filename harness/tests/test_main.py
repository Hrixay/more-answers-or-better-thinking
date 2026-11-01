"""The main runner (D-27, D-35, Amendment 1): the setups, their max_tokens, the extras, the real-time subset, the run window, plan and a
fake end-to-end run. Offline only: DryTransport and FakeTransport, never live."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock

from harness.analysis.kscript import parse_custom_id
from harness.pareto import main as mainrun
from harness.pareto.main import (EXTRAS, MAIN_SETUPS, MUSTS, build_main_requests, build_rt_requests, check_main_set, chosen_setups,
                                 main_plan, run_main, window_check)
from harness.pareto.pilot import HAIKU, OPUS, SONNET
from harness.pareto.transport import DryTransport, FakeTransport
from harness.taskgen import ledger
from harness.taskgen.rng import derive_seed
from harness.tests.fakes import guard, reply

_SETS = {}


def main_set(n=6, n_base=2, sid="main-ledger-l14n6-test"):
    """An in-memory main set at l14n<n>: `n_base` base puzzles, each as Nx1 and 1xN (as freeze builds them, unverified)."""
    key = (n, n_base, sid)
    if key not in _SETS:
        items = []
        for b in range(n_base):
            seed = derive_seed(sid, b)
            for w, d in ((n, 1), (1, n)):
                rec = ledger.generate(seed, w, d, ledger.SETTINGS[f"l14n{n}"], item_id=f"{sid}-{b:03d}-{w}x{d}", style="d31").to_dict()
                rec["base_index"] = b
                items.append(rec)
        _SETS[key] = ({"set_id": sid, "family": "ledger", "setting": f"l14n{n}"}, items)
    man, items = _SETS[key]
    return json.loads(json.dumps(man)), json.loads(json.dumps(items))


def prompts(items):
    """Every prompt the runner can send for these items, approved or D-42 variant, mapped to its item."""
    from harness.pareto import d42
    out = {it["prompt"]: it for it in items}
    out.update({d42.variant_prompt(it): it for it in items})
    return out


def right_text(it):
    if int(it["depth"]) > 1:
        states = it["chains"][0]["states"]
        return "\n".join([f"1.{k} = {ledger.fmt(st)}" for k, st in enumerate(states, 1)] + [f"Answer: 1 = {ledger.fmt(states[-1])}"])
    return "Answer: " + ", ".join(f"{i} = {ledger.fmt(a)}" for i, a in enumerate(it["answer"], 1))


def _rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


class Setups(unittest.TestCase):
    def test_musts_and_extras_with_amendment_1_limits(self):
        by = {su.name: su for su in MAIN_SETUPS}
        self.assertEqual(MUSTS, ("hm", "hl", "om", "ol", "sm"))
        self.assertEqual(EXTRAS, ("sl", "ho", "hx"))
        want = {"hm": (HAIKU, "medium", 40, 5_000, False), "hl": (HAIKU, "low", 40, 48_000, False), "om": (OPUS, "medium", 1, 4_000, False),
                "ol": (OPUS, "low", 1, 32_000, False), "sm": (SONNET, "medium", 1, 3_000, False), "sl": (SONNET, "low", 1, 32_000, False),
                "ho": (HAIKU, "medium", 40, 48_000, True), "hx": (HAIKU, "max", 3, 48_000, False)}
        for name, (model, effort, n, mt, off) in want.items():
            su = by[name]
            self.assertEqual((su.model, su.effort, su.n, su.max_tokens, su.thinking_off), (model, effort, n, mt, off), name)
        self.assertEqual([su.name for su in chosen_setups()], list(MUSTS))
        self.assertEqual([su.name for su in chosen_setups(("hx", "sl"))], ["hm", "hl", "om", "ol", "sm", "sl", "hx"])
        with self.assertRaises(ValueError):
            chosen_setups(("e2",))

    def test_requests_counts_params_and_ids(self):
        man, items = main_set()
        reqs = build_main_requests(man, items, ("sl", "ho", "hx"))
        per = {}
        for cid, p, m in reqs:
            per[m["setup"]] = per.get(m["setup"], 0) + 1
            su = mainrun.BY_NAME[m["setup"]]
            self.assertEqual((p["model"], p["output_config"]["effort"], p["max_tokens"]), (su.model, su.effort, su.max_tokens))
            self.assertEqual(p["thinking"], {"type": "disabled"} if su.thinking_off else {"type": "adaptive"})
            c = parse_custom_id(cid)
            self.assertEqual((c["setup"], c["sample"], c["puzzle"]), (m["setup"], m["sample"], m["item_id"]))
        self.assertEqual(per, {"hm": 160, "hl": 160, "om": 4, "ol": 4, "sm": 4, "sl": 4, "ho": 160, "hx": 12, "hv": 40})
        self.assertNotIn("hv", {m["setup"] for _, _, m in build_main_requests(man, items, d42=False)})
        self.assertEqual(len({r[0] for r in reqs}), len(reqs))

    def test_the_real_time_subset_copies_the_batch_limits(self):
        man, items = main_set(n_base=6)
        rt = build_rt_requests(man, items)
        self.assertEqual(len({m["item_id"] for _, _, m in rt}), 10)
        self.assertEqual(sorted({m["base_index"] for _, _, m in rt}), [0, 1, 2, 3, 4])
        per = {}
        for cid, p, m in rt:
            per[m["setup"]] = per.get(m["setup"], 0) + 1
            self.assertEqual(p["max_tokens"], mainrun.BY_NAME[m["setup"][2:]].max_tokens)
            self.assertTrue(parse_custom_id(cid)["realtime"])
        self.assertEqual(per, {"rthm": 50, "rtsm": 10, "rtom": 10})

    def test_only_one_length_of_ledger_items_is_accepted(self):
        man, items = main_set()
        self.assertEqual(check_main_set(man, items), 6)
        with self.assertRaises(ValueError):
            check_main_set(dict(man, family="digits"), items)
        _, other = main_set(n=4, sid="x-l14n4")
        with self.assertRaises(ValueError):
            check_main_set(man, items + other)


class Window(unittest.TestCase):
    def test_the_window_starts_once_and_refuses_after_48_hours_without_a_note(self):
        d = Path(tempfile.mkdtemp())
        t0 = datetime(2026, 10, 13, 6, tzinfo=timezone.utc)
        window_check(d, now=lambda: t0)
        window_check(d, now=lambda: t0 + timedelta(hours=47))                   # the start is not moved
        self.assertEqual(json.loads((d / "window.json").read_text())["started_utc"], t0.isoformat())
        with self.assertRaises(RuntimeError):
            window_check(d, now=lambda: t0 + timedelta(hours=49))
        w = window_check(d, now=lambda: t0 + timedelta(hours=49), extension_note="D-45: Batch slow; the user said yes")
        self.assertEqual(len(w["extensions"]), 1)


class Runs(unittest.TestCase):
    def test_plan_makes_no_calls_and_describes_the_run(self):
        man, items = main_set()
        t = FakeTransport(lambda p: (_ for _ in ()).throw(AssertionError("plan made a call")))
        p = main_plan(guard(run_cap="100"), man, items, ("sl",))
        self.assertEqual(p["calls"], 160 + 160 + 4 * 4 + 40)
        self.assertEqual([s["name"] for s in p["setups"]], ["hm", "hl", "om", "ol", "sm", "sl", "hv"])
        self.assertEqual(p["realtime"]["calls"], 4 * 7)
        self.assertEqual(sum(Decimal(s["batch_booking_usd"]) for s in p["setups"]), Decimal(p["batch_worst_case_usd"]))
        self.assertEqual(t.sent, [])

    def test_fake_run_grades_every_arm_and_runs_the_real_time_subset(self):
        man, items = main_set()
        by_prompt = prompts(items)

        def fake(p):
            it = by_prompt[p["messages"][0]["content"]]
            return reply(model=p["model"], text=right_text(it) if p["model"] != HAIKU or p["output_config"]["effort"] == "medium" else "Answer: x")
        out = Path(tempfile.mkdtemp())
        r = run_main(guard(run_cap="100"), FakeTransport(fake), out, Path("/fake"), sleep=lambda s: None,
                     loader=lambda _: (man, items), with_e3=False)
        self.assertEqual(r["summary"].answered, 160 + 160 + 12 + 40)
        rows = _rows(out / "compact_table.csv")
        self.assertEqual(len(rows), 372 + 28)
        by = {}
        for x in rows:
            by.setdefault(parse_custom_id(x["custom_id"])["setup"], set()).add(x["right"])
        self.assertEqual(by["hl"], {"0"})                                     # Haiku-low replied "Answer: x": every try wrong
        for tag in ("hm", "om", "ol", "sm", "rthm", "rtsm", "rtom", "hv"):
            self.assertEqual(by[tag], {"1"}, tag)                             # graded, nothing sealed
        self.assertTrue((out / "window.json").exists())
        self.assertIn("main run", (out / "manifest.json").read_text())

    def test_fake_run_with_e3_writes_e3_rows_for_test_4(self):
        from harness.analysis import five_tests
        from harness.pareto import e3
        man, items = main_set(n_base=1)
        by_prompt = prompts(items)
        steps = {st.prompt: st for st in e3.chain_steps([(man, items)])}

        def fake(p):
            text = p["messages"][0]["content"]
            if text in steps:                                                  # an E3 step call: the right new balances
                return reply(model=p["model"], text=f"Answer: [{', '.join(steps[text].truth.split(','))}]")
            return reply(model=p["model"], text=right_text(by_prompt[text]))
        out = Path(tempfile.mkdtemp())
        r = run_main(guard(run_cap="100"), FakeTransport(fake), out, Path("/fake"), sleep=lambda s: None,
                     loader=lambda _: (man, items), with_rt=False)
        self.assertEqual((r["e3"]["rounds"], r["e3"]["calls_sent"], r["e3"]["decided"], r["e3"]["stopped"]), (1, 12, 6, None))
        from harness.pareto.calllog import CallLog
        rows = e3.e3_rows([(man, items)], CallLog(out / "calls.jsonl").records())
        self.assertEqual([(x["shape"], x["step_correct"]) for x in rows], [("1x6", [True] * 6)])
        self.assertEqual(list(five_tests.e3_arm_scores(rows, "1x6").values()), [100.0])

    def test_plan_reports_e3(self):
        man, items = main_set()
        p = main_plan(guard(run_cap="100"), man, items)
        self.assertEqual((p["e3"]["step_positions"], p["e3"]["first_round_calls"], p["e3"]["max_calls_at_cap"]), (12, 24, 108))
        self.assertGreater(Decimal(p["e3"]["booking_at_cap_usd_approx"]), Decimal(p["e3"]["first_round_booking_usd"]))

    def test_a_second_run_sends_nothing_new(self):
        man, items = main_set(n_base=1)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="100")
        run_main(g, DryTransport(), out, Path("/fake"), sleep=lambda s: None, loader=lambda _: (man, items), with_e3=False, with_rt=False)
        t = FakeTransport(lambda p: (_ for _ in ()).throw(AssertionError("sent again")))
        r = run_main(g, t, out, Path("/fake"), sleep=lambda s: None, loader=lambda _: (man, items), with_e3=False, with_rt=False)
        self.assertEqual(r["summary"].skipped_already_done, 80 + 80 + 6 + 20)


class Cli(unittest.TestCase):
    def call(self, argv):
        man, items = main_set()
        out = io.StringIO()
        with mock.patch.object(mainrun, "load_set", return_value=(man, items)), \
                mock.patch("harness.pareto.live.open_live_guard", side_effect=AssertionError("no live guard in tests")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = mainrun.main(argv)
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    def test_live_needs_cap_and_clearance_and_refuses_out_and_no_e3(self):
        for argv in (["live", "--set", "S"], ["live", "--set", "S", "--cap", "80"], ["live", "--set", "S", "--clearance", "c.json"],
                     ["live", "--set", "S", "--cap", "80", "--clearance", "c.json", "--out", "d"],
                     ["live", "--set", "S", "--cap", "80", "--clearance", "c.json", "--no-e3"],
                     ["plan", "--set", "S", "--extras", "e2"]):
            code, _ = self.call(argv)
            self.assertEqual(code, 2, argv)

    def test_plan_prints_the_plan(self):
        code, out = self.call(["plan", "--set", "S", "--extras", "sl,ho,hx"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["calls"], 160 + 160 + 4 * 3 + 4 + 160 + 12 + 40)


if __name__ == "__main__":
    unittest.main()
