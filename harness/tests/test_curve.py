"""harness.analysis.curve (D-87): sealing, the whole-answer and per-step numbers, vote@10, Wilson, q^n, the pick check, pilot-1 points."""

import json
import tempfile
import unittest
from pathlib import Path

from harness.analysis import curve
from harness.pareto.ladder import LADDER_SETUPS
from harness.taskgen.freeze import write_set
from harness.taskgen.ledger import fmt

SU = {su.name: su for su in LADDER_SETUPS}


def chain_reply(states, answer=None, drop_step=None):
    lines = [f"1.{k} = {fmt(s)}" for k, s in enumerate(states, 1) if k != drop_step]
    return "\n".join(lines + [f"Answer: 1 = {fmt(answer if answer is not None else states[-1])}"])


def pieces_reply(answer):
    return "Answer: " + ", ".join(f"{i} = {fmt(a)}" for i, a in enumerate(answer, 1))


def wrong(state):
    return [state[0] + 1] + list(state[1:])


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp()
        cls.dirs = {n: Path(cls.td) / f"t-ledger-l14n{n}" for n in (4, 6)}
        write_set(cls.dirs[4], "ledger", "l14n4", "t-ledger-l14n4", 3, "d31", "scratch")
        write_set(cls.dirs[6], "ledger", "l14n6", "t-ledger-l14n6", 2, "d31", "scratch")
        cls.sets = curve.load_sets(list(cls.dirs.values()))

    def item(self, n, base, shape):
        return curve._item(self.sets, f"t-ledger-l14n{n}", base, shape)

    def rec(self, n, base, shape, setup, sample, text, kind="answered"):
        it = self.item(n, base, shape)
        su = SU[setup]
        return {"custom_id": f"{it['id']}-{setup}-{sample:02d}", "final": True, "requested_model": su.model, "effort": su.effort,
                "kind": kind, "answer_text": text}

    def right(self, n, base, shape):
        it = self.item(n, base, shape)
        return chain_reply(it["chains"][0]["states"]) if shape == "1xn" else pieces_reply(it["answer"])

    def write_log(self, recs):
        p = Path(tempfile.mkdtemp()) / "calls.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        return p

    def all_right(self, setups=("hm", "om", "sm")):
        out = []
        for n in (4, 6):
            for b in self.sets[f"t-ledger-l14n{n}"]["bases"]:
                for shape in ("nx1", "1xn"):
                    for su in setups:
                        out += [self.rec(n, b, shape, su, k, self.right(n, b, shape)) for k in range(1, SU[su].n + 1)]
        return out


class Sealing(Base):
    def test_without_a_pick_only_haiku_records_are_read(self):
        recs = self.all_right()
        got = curve.read_records([self.write_log(recs)], self.sets, (curve.PICKER,))
        self.assertEqual({r["setup"] for r in got}, {"hm"})
        out = Path(tempfile.mkdtemp()) / "c.json"
        self.assertEqual(curve.main(["--sets", *map(str, self.dirs.values()), "--replies", str(self.write_log(recs)), "--out", str(out)]), 0)
        res = json.loads(out.read_text())
        self.assertEqual((res["opened"], sorted(res["models"])), (["hm"], ["hm"]))
        self.assertNotIn("decision_inputs", res)

    def test_a_record_whose_model_does_not_match_its_setup_raises(self):
        r = self.rec(4, 0, "1xn", "hm", 1, "x")
        r["requested_model"] = SU["om"].model
        with self.assertRaises(ValueError):
            curve.read_records([self.write_log([r])], self.sets, ("hm",))

    def test_the_pick_file_must_be_committed_binding_haiku_and_name_the_sets(self):
        d = Path(tempfile.mkdtemp())
        good = {"model": SU["hm"].model, "effort": "medium", "tier": 1, "pick": {"preset": "l14n6"},
                "presets": [{"preset": "l14n4"}, {"preset": "l14n6"}], "sets": {k: v["items_sha256"] for k, v in self.sets.items()}}
        p = d / "pick.json"
        p.write_text(json.dumps(good))
        self.assertEqual(curve.check_pick(p, self.sets, committed=lambda _: True), 6)
        with self.assertRaises(ValueError):
            curve.check_pick(p, self.sets, committed=lambda _: False)
        with self.assertRaises(ValueError):
            curve.check_pick(p, self.sets)                              # a file outside any git repository is not committed
        for bad in (dict(good, pick=None, tier=3), dict(good, model=SU["om"].model),
                    dict(good, presets=[{"preset": "l14n4"}, {"preset": "l14n6"}, {"preset": "l14n8"}]),
                    dict(good, sets=dict(good["sets"], **{"t-ledger-l14n4": "0" * 64}))):
            p.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                curve.check_pick(p, self.sets, committed=lambda _: True)

    def test_pilot1_sealed_records_need_the_lock2_tag(self):
        out = Path(tempfile.mkdtemp()) / "c.json"
        log = self.write_log([])
        orig = curve.lock2_is_cut
        curve.lock2_is_cut = lambda: False
        try:
            with self.assertRaises(SystemExit):
                curve.main(["--sets", str(self.dirs[4]), "--replies", str(log), "--pilot1-sets", str(self.dirs[4]),
                            "--pilot1-replies", str(log), "--open-pilot1-sealed", "--out", str(out)])
        finally:
            curve.lock2_is_cut = orig


class Numbers(Base):
    def test_whole_answer_median_vote_and_missing_tries(self):
        recs = []
        recs += [self.rec(4, 0, s, "hm", k, self.right(4, 0, s)) for s in ("nx1", "1xn") for k in range(1, 11)]
        it = self.item(4, 1, "1xn")
        st = it["chains"][0]["states"]
        bad = chain_reply(st[:-1] + [wrong(st[-1])], answer=wrong(st[-1]))
        recs += [self.rec(4, 1, "1xn", "hm", k, self.right(4, 1, "1xn") if k <= 5 else bad) for k in range(1, 11)]
        nx = self.item(4, 1, "nx1")
        recs += [self.rec(4, 1, "nx1", "hm", k, pieces_reply([wrong(nx["answer"][0])] + nx["answer"][1:])) for k in range(1, 11)]
        m = curve.curve({"t-ledger-l14n4": self.sets["t-ledger-l14n4"]}, curve.read_records([self.write_log(recs)], self.sets, ("hm",)), ("hm",))
        row = m["hm"]["by_n"]["4"]
        w = row["whole_answer"]
        self.assertAlmostEqual(w["nx1"]["mean"], 1 / 3)
        self.assertAlmostEqual(w["1xn"]["mean"], 1.5 / 3)
        self.assertAlmostEqual(w["pooled"]["mean"], 1.25 / 3)
        self.assertAlmostEqual(w["pooled"]["median"], 0.25)          # puzzles 1, 1, 0.5, 0, 0, 0
        self.assertEqual(row["not_answered"], {"missing": 20})
        self.assertAlmostEqual(row["vote_at_10"]["1xn"]["mean"], 1.5 / 3)   # base 1: a 5-5 tie with the right trace, credit 1/2
        self.assertAlmostEqual(row["vote_at_10"]["nx1"]["mean"], 1 / 3)
        self.assertEqual(row["vote_at_10"]["label"], "not cost-matched")
        self.assertAlmostEqual(row["per_step"]["nx1"]["mean"], (1 + 3 / 4 + 0) / 3)
        self.assertEqual(row["format_compliance_1xn"], 1.0)

    def test_per_step_counts_a_wrong_answer_line_as_all_steps_right_and_leaves_out_unplaceable_tries(self):
        it = self.item(6, 0, "1xn")
        st = it["chains"][0]["states"]
        recs = [self.rec(6, 0, "1xn", "hm", 1, chain_reply(st, answer=wrong(st[-1]))),        # every step right, the Answer line not
                self.rec(6, 0, "1xn", "hm", 2, chain_reply(st, drop_step=3))]                  # a step line missing: unplaceable
        m = curve.curve({"t-ledger-l14n6": self.sets["t-ledger-l14n6"]}, curve.read_records([self.write_log(recs)], self.sets, ("hm",)), ("hm",))
        row = m["hm"]["by_n"]["6"]
        self.assertEqual(row["whole_answer"]["1xn"]["mean"], 0.0)
        self.assertEqual(row["unplaceable_1xn"], 1)
        self.assertEqual(row["per_step"]["1xn"]["mean"], 1.0)          # base 0 only (base 1 has no placeable try)
        self.assertEqual(row["per_step"]["1xn"]["n_base"], 1)
        self.assertAlmostEqual(row["format_compliance_1xn"], 0.0)
        self.assertTrue(row["format_flag"])

    def test_after_the_pick_opus_and_sonnet_with_wilson_q_and_the_decision_inputs(self):
        opened = tuple(SU)
        m = curve.curve(self.sets, curve.read_records([self.write_log(self.all_right())], self.sets, opened), opened)
        om = m["om"]["by_n"]["6"]["whole_answer"]
        self.assertEqual((om["1xn"]["right"], om["1xn"]["tries"], om["1xn"]["interval"]), (2, 2, "wilson"))
        self.assertEqual(om["1xn"]["ci95"], list(curve.wilson(2, 2)))
        self.assertEqual((m["hm"]["q"]["q"], m["hm"]["q"]["by_n"]["4"]["q_n"], m["hm"]["q"]["by_n"]["4"]["observed_over_q_n"]["pooled"]),
                         (1.0, 1.0, 1.0))
        self.assertEqual(m["hm"]["q"]["24"]["label"], "dotted extrapolation only")
        d = curve.decision_inputs(m, 6)
        self.assertEqual((d["chosen_n"], d["p_opus_1xn"], d["opus_pooled"], d["near_ceiling"]), (6, 1.0, 1.0, True))

    def test_wilson_and_the_bootstrap(self):
        lo, hi = curve.wilson(15, 20)
        self.assertAlmostEqual(lo, 0.5313, places=4)
        self.assertAlmostEqual(hi, 0.8881, places=4)
        vals = {b: b * b / 100 for b in range(10)}

        def stat(s):
            return sum(vals[b] for b in s) / len(s)
        a = curve.cluster_bootstrap([list(vals)], stat, "x")
        self.assertEqual(a, curve.cluster_bootstrap([list(vals)], stat, "x"))       # each statistic's seed comes from its name
        self.assertNotEqual(a, curve.cluster_bootstrap([list(vals)], stat, "y"))
        self.assertTrue(0.0 < a[0] < stat(list(vals)) < a[1] < 0.81)
        self.assertEqual(curve.cluster_bootstrap([[3, 3]], stat, "z"), (0.09, 0.09))   # one value: both ends are it

    def test_two_final_records_for_one_try_raise(self):
        r = self.rec(4, 0, "1xn", "hm", 1, self.right(4, 0, "1xn"))
        with self.assertRaises(ValueError):
            curve.curve(self.sets, curve.read_records([self.write_log([r, r])], self.sets, ("hm",)), ("hm",))


class Pilot1(Base):
    def test_pilot1_points_and_presets(self):
        d = Path(tempfile.mkdtemp())
        write_set(d / "p-l14", "ledger", "l14", "t-pilot-ledger-l14", 1, "d31", "scratch")
        ps = curve.load_sets([d / "p-l14"])
        it = {("1xn" if int(i["depth"]) > 1 else "nx1"): i for i in ps["t-pilot-ledger-l14"]["items"].values()}
        recs = [{"custom_id": f"{it['1xn']['id']}-hm-{k:02d}", "final": True, "requested_model": SU["hm"].model, "effort": "medium",
                 "kind": "answered", "answer_text": chain_reply(it["1xn"]["chains"][0]["states"])} for k in range(1, 11)]
        res = curve.pilot1_points(ps, curve.read_records([self.write_log(recs)], ps, ("hm",)), ("hm",))
        self.assertEqual(res["hm"]["l14_only"]["mean"], 0.5)                # 1xn all right, 24x1 all missing
        self.assertEqual(res["hm"]["l14_to_l16"]["n_base"], 1)
        with self.assertRaises(ValueError):
            curve.pilot1_points(self.sets, [], ("hm",))                     # l14n* presets are not pilot-1 presets


if __name__ == "__main__":
    unittest.main()
