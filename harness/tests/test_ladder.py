"""The ladder runner (D-86, D-87): Haiku-medium x10, Opus-medium x1 and Sonnet-medium x1 per ladder puzzle through Batch; only
Haiku-medium is graded, Opus and Sonnet stay sealed. Offline only: DryTransport and FakeTransport, never live."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from harness.analysis import scoring
from harness.pareto import ladder
from harness.pareto.ladder import (LADDER_SETUPS, PICKER, SEALED, build_ladder_requests, is_picker, ladder_plan, ladder_steps,
                                   run_ladder, sealed_grader)
from harness.pareto.pilot import HAIKU, OPUS, SONNET
from harness.pareto.transport import DryTransport, FakeTransport
from harness.taskgen import freeze, ledger
from harness.taskgen.rng import derive_seed
from harness.tests.fakes import guard, reply

_SETS = {}


def ladder_set(n, n_base=2, sid=None):
    """An in-memory ladder set at l14n<n>: `n_base` base puzzles, each as Nx1 and 1xN (as freeze builds them, unverified)."""
    sid = sid or f"ladder-ledger-l14n{n}-test"
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


def loader_for(*sets):
    by = {Path(f"/fake/{man['set_id']}"): (man, items) for man, items in sets}
    return list(by), by.__getitem__


def right_text(it):
    """The right reply to a ledger item: the step lines and the Answer line at 1xN, every piece on the Answer line at Nx1."""
    if int(it["depth"]) > 1:
        states = it["chains"][0]["states"]
        lines = [f"1.{k} = {ledger.fmt(st)}" for k, st in enumerate(states, 1)]
        return "\n".join(lines + [f"Answer: 1 = {ledger.fmt(states[-1])}"])
    return "Answer: " + ", ".join(f"{i} = {ledger.fmt(a)}" for i, a in enumerate(it["answer"], 1))


def _rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


class Setups(unittest.TestCase):
    def test_the_setups_are_haiku_x10_opus_x1_sonnet_x1_and_only_haiku_picks(self):
        self.assertEqual([(s.name, s.model, s.effort, s.n) for s in LADDER_SETUPS],
                         [("hm", HAIKU, "medium", 10), ("om", OPUS, "medium", 1), ("sm", SONNET, "medium", 1)])
        self.assertEqual(PICKER.name, "hm")
        self.assertEqual(SEALED, ("om", "sm"))
        self.assertEqual(set(ladder.LADDER_PRESETS), {"l14n4", "l14n6", "l14n8", "l14n12", "l14n16"})


class Build(unittest.TestCase):
    def test_counts_ids_and_max_tokens(self):
        man, items = ladder_set(6, n_base=3)                 # 3 base puzzles: nothing assumes 10 or 20
        reqs = build_ladder_requests(man, items)
        self.assertEqual(len(reqs), 3 * 2 * 12)
        ids = [r[0] for r in reqs]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertTrue(all(len(i) <= 64 for i in ids))
        by_id = {it["id"] for it in items}
        for cid, p, meta in reqs:
            self.assertEqual(cid, f"{meta['item_id']}-{meta['setup']}-{meta['sample']:02d}")   # the full item id is in the custom id
            self.assertIn(meta["item_id"], by_id)
            self.assertEqual(p["max_tokens"], {HAIKU: 48_000, OPUS: 32_000, SONNET: 32_000}[p["model"]])
            self.assertEqual(p["output_config"]["effort"], "medium")
        per = {}
        for _, p, meta in reqs:
            per[(meta["setup"], p["model"])] = per.get((meta["setup"], p["model"]), 0) + 1
        self.assertEqual(per, {("hm", HAIKU): 60, ("om", OPUS): 6, ("sm", SONNET): 6})

    def test_only_ladder_sets_are_accepted(self):
        man, items = ladder_set(4, n_base=1)
        self.assertEqual(ladder_steps(man, items), 4)
        with self.assertRaises(ValueError):
            ladder_steps(dict(man, family="digits"), items)
        with self.assertRaises(ValueError):
            ladder_steps(dict(man, setting="l14"), items)                     # the 24-step preset is not a rung
        with self.assertRaises(ValueError):
            ladder_steps(dict(man, setting="l14n6"), items)                   # items at 4 steps under a 6-step preset
        bad = [dict(items[0], width=2, depth=2)] + items[1:]
        with self.assertRaises(ValueError):
            build_ladder_requests(man, bad)

    def test_plan_makes_no_calls_and_describes_the_run(self):
        sets = [ladder_set(4, n_base=3), ladder_set(6, n_base=2)]
        p = ladder_plan(guard(run_cap="30"), sets)
        self.assertEqual(p["calls"], (3 + 2) * 2 * 12)
        self.assertEqual(p["per_setup"], {"ledger/hm": 100, "ledger/om": 10, "ledger/sm": 10})
        self.assertEqual(p["sets"]["ladder-ledger-l14n4-test"], {"preset": "l14n4", "steps": 4, "base_puzzles": 3, "puzzles": 6})
        self.assertEqual(p["sets"]["ladder-ledger-l14n6-test"]["base_puzzles"], 2)
        self.assertEqual((p["picker"], p["sealed"]), ("hm", ["om", "sm"]))
        self.assertGreater(Decimal(p["batch_worst_case_usd"]), 0)


class Sealing(unittest.TestCase):
    def test_is_picker_needs_the_tag_the_model_and_the_effort(self):
        ok = {"meta": {"setup": "hm"}, "requested_model": HAIKU, "effort": "medium"}
        self.assertTrue(is_picker(ok))
        for bad in (dict(ok, meta={"setup": "om"}), dict(ok, requested_model=OPUS), dict(ok, requested_model=SONNET),
                    dict(ok, effort="high"), {k: v for k, v in ok.items() if k != "meta"}, {"meta": {"setup": "hm"}}):
            self.assertFalse(is_picker(bad), bad)

    def test_sealed_grader_never_calls_the_scorer_for_opus_or_sonnet(self):
        man, items = ladder_set(6, n_base=1)
        by_id = {it["id"]: it for it in items}
        g = sealed_grader(by_id, "ledger")
        with mock.patch.object(scoring, "grade_1x24", wraps=scoring.grade_1x24) as g1, \
                mock.patch.object(scoring, "grade_24x1", wraps=scoring.grade_24x1) as g2:
            for it in items:
                for setup, model in (("om", OPUS), ("sm", SONNET), ("hm", OPUS), ("om", HAIKU)):
                    rec = {"meta": {"item_id": it["id"], "setup": setup}, "requested_model": model, "effort": "medium",
                           "answer_text": right_text(it)}
                    self.assertIsNone(g(rec))
            self.assertEqual((g1.call_count, g2.call_count), (0, 0))
            for it in items:
                rec = {"meta": {"item_id": it["id"], "setup": "hm"}, "requested_model": HAIKU, "effort": "medium",
                       "answer_text": right_text(it)}
                self.assertTrue(g(rec))
            self.assertEqual((g1.call_count, g2.call_count), (1, 1))

    def test_fake_run_grades_haiku_only_and_leaves_opus_and_sonnet_right_blank(self):
        man, items = ladder_set(6, n_base=2)
        dirs, load = loader_for((man, items))
        by_prompt = {it["prompt"]: it for it in items}
        seen = {"n": 0}

        def fake(p):
            it = by_prompt[p["messages"][0]["content"]]
            if p["model"] != HAIKU:
                return reply(model=p["model"], text=right_text(it) + "\nSEALED " + p["model"])     # right, but never to be scored
            seen["n"] += 1
            return reply(model=p["model"], text=right_text(it) if seen["n"] % 2 else "Answer: nothing")
        out = Path(tempfile.mkdtemp())
        with mock.patch.object(scoring, "grade_1x24", wraps=scoring.grade_1x24) as g1, \
                mock.patch.object(scoring, "grade_24x1", wraps=scoring.grade_24x1) as g2:
            r = run_ladder(guard(run_cap="30"), FakeTransport(fake), out, dirs, sleep=lambda s: None, loader=load)
            scored_texts = [c.args[0] for c in g1.call_args_list + g2.call_args_list]
        self.assertEqual(r["summary"].answered, 2 * 2 * 12)
        self.assertFalse(any("SEALED" in str(t) for t in scored_texts))      # no Opus or Sonnet reply reached a scorer
        self.assertEqual(len(scored_texts), 2 * 2 * 10)                     # every Haiku reply did
        rows = _rows(out / "compact_table.csv")
        self.assertEqual(len(rows), 48)
        sealed = [x for x in rows if x["requested_model"] in (OPUS, SONNET)]
        self.assertEqual(len(sealed), 8)
        self.assertTrue(all(x["right"] == "" for x in sealed))
        self.assertTrue(all(x["cost_usd"] not in ("", None) for x in sealed))     # tokens and cost are kept for k and pricing
        haiku = [x for x in rows if x["requested_model"] == HAIKU]
        self.assertEqual(sorted({x["right"] for x in haiku}), ["0", "1"])
        self.assertEqual(sum(x["right"] == "1" for x in haiku), 20)
        self.assertTrue(all("-1x6-" in x["custom_id"] or "-6x1-" in x["custom_id"] for x in rows))
        self.assertIn("ladder pilot", (out / "manifest.json").read_text())

    def test_dry_run_end_to_end(self):
        sets = [ladder_set(4, n_base=1), ladder_set(8, n_base=1)]
        dirs, load = loader_for(*sets)
        out = Path(tempfile.mkdtemp())
        g = guard(run_cap="30")
        r = run_ladder(g, DryTransport(), out, dirs, sleep=lambda s: None, loader=load)
        self.assertEqual(r["summary"].answered + r["summary"].failed, 2 * 2 * 12)
        rows = _rows(out / "compact_table.csv")
        self.assertTrue(all(x["right"] == "" for x in rows if x["requested_model"] != HAIKU))
        self.assertEqual(g.reserved, 0)
        self.assertIsNone(r["realtime"])                                     # no real-time check in the ladder


class Cli(unittest.TestCase):
    def run_main(self, argv, sets):
        dirs, load = loader_for(*sets)
        argv = [a if a != "SETS" else str(d) for a in argv for d in ([None] if a != "SETS" else dirs)]
        out = io.StringIO()
        with mock.patch.object(ladder, "load_set", side_effect=lambda d: load(Path(d))), \
                mock.patch("harness.pareto.live.open_live_guard", side_effect=AssertionError("no live guard in tests")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = ladder.main(argv)
        return code, out.getvalue()

    def test_live_needs_cap_and_clearance_and_refuses_out(self):
        sets = [ladder_set(4, n_base=1)]
        for argv in (["live", "--sets", "SETS"], ["live", "--sets", "SETS", "--cap", "5"],
                     ["live", "--sets", "SETS", "--clearance", "c.json"],
                     ["live", "--sets", "SETS", "--cap", "5", "--clearance", "c.json", "--out", "x"]):
            with self.assertRaises(SystemExit):
                self.run_main(argv, sets)

    def test_a_set_that_is_not_a_ladder_set_is_refused(self):
        man, items = ladder_set(4, n_base=1)
        with self.assertRaises(SystemExit):
            self.run_main(["plan", "--sets", "SETS"], [(dict(man, setting="l14"), items)])

    def test_plan_and_dry(self):
        sets = [ladder_set(4, n_base=1)]
        code, out = self.run_main(["plan", "--sets", "SETS"], sets)
        self.assertEqual(code, 0)
        self.assertIn('"sealed"', out)
        with tempfile.TemporaryDirectory() as td:
            code, out = self.run_main(["dry", "--sets", "SETS", "--out", td], sets)
            self.assertEqual(code, 0)
            rows = _rows(Path(td) / "compact_table.csv")
            self.assertEqual(len(rows), 24)
            self.assertTrue(all(x["right"] == "" for x in rows if x["requested_model"] != HAIKU))
        with self.assertRaises(SystemExit):
            self.run_main(["dry", "--sets", "SETS"], sets)                  # dry needs --out


@unittest.skipUnless(hasattr(freeze, "shapes_for"), "freeze writes N-step sets only with the lock-2 generator fix (shapes_for)")
class FrozenLadderSet(unittest.TestCase):
    def test_a_frozen_l14n4_set_is_verified_and_runs_dry(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "set"
            freeze.write_set(d, "ledger", "l14n4", "ladder-ledger-l14n4-test", 1, "d31", "scratch")
            out = Path(td) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ladder.main(["dry", "--sets", str(d), "--out", str(out)]), 0)
            rows = _rows(out / "compact_table.csv")
            self.assertEqual(len(rows), 24)
            self.assertTrue(all(x["right"] == "" for x in rows if x["requested_model"] != HAIKU))


if __name__ == "__main__":
    unittest.main()
