"""The top-up run's converter and driver (harness.analysis.topup_rows, topup_analysis; research/topup-run-spec.md sections 3-5, Edith's
rulings on the runner): a fixture main run made by the main runner itself (run_main on a small frozen set, a scripted FakeTransport),
then the top-up runner (topup.run_topup) on the same set with a scripted fake, then the driver. Every number below is worked out by
hand from the script. Offline only: temp folders, fake transports, never live, never data/raw."""

import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

import atexit as _atexit
import shutil as _shutil

from harness.analysis import bootstrap, five_tests, topup_analysis, topup_rows
from harness.analysis.curve import cluster_bootstrap
from harness.analysis.kscript import parse_custom_id
from harness.pareto import e3, prices, topup
from harness.pareto.main import run_main
from harness.pareto.pilot import HAIKU, load_set
from harness.pareto.prices import Usage
from harness.pareto.transport import DryTransport, FakeTransport
from harness.taskgen import freeze, ledger
from harness.tests.fakes import guard, reply


def _tmpdir() -> Path:
    """A temp folder removed when the test process exits: these tests write nowhere else."""
    d = Path(tempfile.mkdtemp(prefix="pareto-test-"))
    _atexit.register(_shutil.rmtree, d, True)
    return d


SID = "tatest-ledger-l14n6-v1"
MAIN_RUN_ID = "test-run"                      # fakes.guard's run id: the main runner writes it on every record
N_BASE = 3
B, DRAWS = 400, 300                           # small, for speed (the sealed run: 10,000 and 2,000)

# Main-run Haiku-medium samples 1-8 per puzzle (P = pieces 6x1, C = chain 1x6; base index): R right, W wrong, V another wrong,
# X refused. Samples 9-40 are W.
HM = {("P", 0): "RRXWWWWW", ("P", 1): "RRRRWWVV", ("P", 2): "WWWWWWWW",
      ("C", 0): "RWRWRWRW", ("C", 1): "RRRRRRRR", ("C", 2): "WWWWWWVR"}
OM = {("P", 0): "R", ("P", 1): "W", ("P", 2): "R", ("C", 0): "W", ("C", 1): "R", ("C", 2): "W"}
MAIN_E3_WRONG = {1: 3, 2: 4}                  # chain base -> the step E3 gets wrong (every draw the same wrong answer)
# The top-up run: same-model tries 1-5 (bases 0 and 1), picker replies, C13's wrong piece.
SC = {("P", 0): "RRRWW", ("P", 1): "RRRRR", ("C", 0): "RRRRR", ("C", 1): "WWWWX"}
PICK = {("P", 0): "I compared them.\nPick: 3", ("P", 1): "Pick: 1", ("P", 2): "I cannot decide.",
        ("C", 0): "Pick: 2", ("C", 1): "**Pick: 8**", ("C", 2): "Pick: 8"}
C13_WRONG = {0: 2}                            # pieces base -> the piece C13 gets wrong
TOUT_TOP, TOUT_MAIN = 100, 50


def bump(state, by=1):
    return [state[0] + by] + list(state[1:])


def chain_text(states):
    lines = [f"1.{k} = {ledger.fmt(s)}" for k, s in enumerate(states, 1)]
    return "\n".join(lines + [f"Answer: 1 = {ledger.fmt(states[-1])}"])


def pieces_text(answer):
    return "Answer: " + ", ".join(f"{i} = {ledger.fmt(a)}" for i, a in enumerate(answer, 1))


def whole(it, mark):
    """A whole-answer reply for a puzzle: R right, W wrong (the last state / the first piece bumped by 1), V bumped by 2."""
    by = {"W": 1, "V": 2}.get(mark, 0)
    if it["width"] == 1:
        st = [list(s) for s in it["chains"][0]["states"]]
        return chain_text(st[:-1] + [bump(st[-1], by)] if by else st)
    ans = [list(a) for a in it["answer"]]
    return pieces_text([bump(ans[0], by)] + ans[1:] if by else ans)


def step_answer(state):
    return f"Answer: {ledger.fmt(list(state))}"


def key(it):
    return ("C" if it["width"] == 1 else "P", int(it["base_index"]))


_FIX = None


class Fixture:
    """The frozen set, the main run (run_main with a scripted fake) and the top-up run (run_topup with a scripted fake), made once."""

    def __init__(self):
        self.root = _tmpdir()
        self.set_dir = self.root / SID
        freeze.write_set(self.set_dir, "ledger", "l14n6", SID, N_BASE, "d31", "scratch")
        self.man, self.items = load_set(self.set_dir)
        self.by_id = {it["id"]: it for it in self.items}
        self.e3_truth = {(st.item_id, st.k): st.truth for st in e3.chain_steps([(self.man, self.items)])}
        self.c13_truth = {(st.item_id, st.k): st.truth for st in topup.c13_steps(self.man, self.items)}
        self.main_dir = self.root / "main-run"
        run_main(guard(run_cap="100"), FakeTransport(lambda p: reply(model=p["model"], text="Answer: nothing"),
                                                     batch_reply=self.main_reply),
                 self.main_dir, self.set_dir, ("sl", "ho", "hx"), sleep=lambda s: None)
        # the live main run's folder also holds the guard's ledger and the runner's log (the six stamped files); stand-ins here
        (self.main_dir / "ledger.jsonl").write_text("")
        (self.main_dir / "runner.log").write_text("fixture main run\n")
        self.plan_path = self.root / "topup-plan.json"
        self.plan_path.write_text(json.dumps(self.plan()))
        self.run_dir = self.root / "topup-run"
        self.run = topup.run_topup(guard(run_cap="100"), FakeTransport(batch_reply=self.top_reply), self.run_dir, self.plan(),
                                   self.main_dir, sleep=lambda s: None)

    def plan(self):
        p = json.loads((Path(topup.ROOT) / "data" / "plans" / "topup-plan.json").read_text())
        sha = json.loads((self.set_dir / "manifest.json").read_text())["items_sha256"]
        p.update(set={"set": str(self.set_dir), "items_sha256": sha, "steps": 6}, draft="test plan",
                 main_run={"run_id": MAIN_RUN_ID, "setup": "hm"}, same_model={"bases": 2, "tries": 5, "mirrors": "hm"})
        return p

    def main_reply(self, cid, params):
        c = parse_custom_id(cid)
        it, tag, s = self.by_id[c["puzzle"]], c["setup"], c["sample"]
        stop, text, tout = "end_turn", "Answer: nothing", TOUT_MAIN
        if tag == "hm":
            mark = HM[key(it)][s - 1] if s <= 8 else "W"
            if mark == "X":
                stop, text, tout = "refusal", None, 0
            else:
                text = whole(it, mark)
        elif tag == "om":
            text = whole(it, OM[key(it)])
        elif tag == "es":
            k = s // 100
            truth = [int(x) for x in self.e3_truth[(it["id"], k)].split(",")]
            text = step_answer(bump(truth) if MAIN_E3_WRONG.get(it["base_index"]) == k else truth)
        msg = reply(model=params["model"], text=text, stop=stop, category="cyber" if stop == "refusal" else None, tout=tout)
        return {"type": "succeeded", "message": msg}

    def top_reply(self, cid, params):
        c = parse_custom_id(cid)
        it, tag, s = self.by_id[c["puzzle"]], c["setup"], c["sample"]
        stop, text = "end_turn", "Answer: nothing"
        if tag == "tp":
            if key(it) == ("P", 2):
                stop, text = "refusal", None                                       # a refused planner: plan_failed (Edith ruling 2)
            elif key(it) == ("C", 2):
                text = "Task 1: a\nTask 3: c\nTask 4: d\nTask 5: e\nTask 6: f"    # no Task 2: plan_failed
            else:
                text = "\n".join(f"Task {k}: Instruction number {k}." for k in range(1, 7))
        elif tag == "th":
            k, d = s // 100, s % 100
            right = it["chains"][0]["states"][k - 1] if it["width"] == 1 else it["chains"][k - 1]["states"][0]
            if key(it) in (("C", 1), ("P", 1)) and k == (3 if it["width"] == 1 else 4):
                text = "no answer line" if d == 9 else step_answer(bump(right, 1 if d % 2 else 2))   # no result at the cap
            else:
                text = step_answer(right)
        elif tag == "ta":
            text = whole(it, "W" if key(it) == ("P", 0) else "R")
        elif tag == "pk":
            text = PICK[key(it)]
        elif tag == "es":
            k = s // 100
            truth = [int(x) for x in self.c13_truth[(it["id"], k)].split(",")]
            text = step_answer(bump(truth) if C13_WRONG.get(it["base_index"]) == k else truth)
        elif tag == "sc":
            mark = SC[key(it)][s - 1]
            if mark == "X":
                stop, text = "refusal", None
            else:
                text = whole(it, mark)
        msg = reply(model=HAIKU, text=text, stop=stop, category="cyber" if stop == "refusal" else None,
                    tout=0 if stop == "refusal" else TOUT_TOP)
        return {"type": "succeeded", "message": msg}

    def stamp(self, main_dir=None):
        """The fixture main run's own stamp (the real one, MAIN_RUN_STAMP, names main-l14n6-1's files)."""
        d = main_dir or self.main_dir
        return {"source": "fixture", "run_id": MAIN_RUN_ID,
                "sha256": {n: hashlib.sha256((d / n).read_bytes()).hexdigest() for n in topup_analysis.STAMP_FILES}}

    def analyse(self, run_dir=None, main_dir=None, **kw):
        if "stamp" not in kw:
            kw["stamp"] = self.stamp(main_dir)
        kw.setdefault("same_model_size", (2, 5))                 # the fixture's check is 2 bases x 5 tries (the spec's: 20 x 5)
        return topup_analysis.analyse(self.plan_path, run_dir or self.run_dir, main_dir or self.main_dir, B=B, draws=DRAWS, **kw)

    def built(self):
        return topup_rows.build(self.plan(), self.run_dir, self.main_dir)


def fixture() -> Fixture:
    global _FIX
    if _FIX is None:
        _FIX = Fixture()
    return _FIX


_RES = None


def result():
    global _RES
    if _RES is None:
        _RES = fixture().analyse()
    return _RES


def base(i):
    return f"{SID}-{i:03d}"


class Rows(unittest.TestCase):
    """topup_rows: each definition of section 4b, by hand."""

    @classmethod
    def setUpClass(cls):
        cls.f = fixture()
        cls.b = cls.f.built()
        cls.e2 = {(r["shape"], r["base_id"]): r for r in cls.b["e2"]}
        cls.pk = {(r["shape"], r["base_id"]): r for r in cls.b["picker"]}

    def test_the_fake_run_finished(self):
        self.assertIsNone(self.f.run["stopped"])

    def test_e2_score_is_the_aggregators_graded_answer_and_plan_failed_is_wrong(self):
        got = {k: (r["stage"], r["correct"]) for k, r in self.e2.items()}
        self.assertEqual(got, {("6x1", base(0)): ("done", False), ("6x1", base(1)): ("done", True), ("6x1", base(2)): ("plan_failed", False),
                               ("1x6", base(0)): ("done", True), ("1x6", base(1)): ("done", True), ("1x6", base(2)): ("plan_failed", False)})
        p2, c2 = self.e2[("6x1", base(2))], self.e2[("1x6", base(2))]
        self.assertEqual((p2["kind"], p2["planner_kind"], p2["planner_stop_reason"]), ("plan_failed", "refusal", "refusal"))
        self.assertEqual((c2["kind"], c2["planner_kind"], c2["planner_stop_reason"]), ("plan_failed", "answered", "end_turn"))
        self.assertEqual(c2["custom_ids"], [f"{c2['item_id']}-tp-01"])                    # plan_failed: nothing more was sent

    def test_no_result_places(self):
        c1, p1 = self.e2[("1x6", base(1))], self.e2[("6x1", base(1))]
        self.assertEqual((c1["tasks_no_result"], c1["tasks_not_started"]), ([3], [4, 5, 6]))   # chain: from its place onward
        self.assertEqual((p1["tasks_no_result"], p1["tasks_not_started"]), ([4], []))         # pieces: its own place only (ruling 4)
        self.assertEqual(c1["helper_draws"], 2 + 2 + 9)
        self.assertIsNone(c1["helper_results_key"])
        self.assertTrue(self.e2[("6x1", base(0))]["helpers_right"])
        self.assertEqual(self.e2[("1x6", base(0))]["helper_results_key"], self.e2[("1x6", base(0))]["answer_key_whole"])

    def test_e2_tasks_carry_their_agreed_result_and_each_draws_vote(self):
        # Edith code r1 T-D2 (spec 4b: "for each task, the helpers' draws and agreed result (or 'no result')")
        c0, c1 = self.e2[("1x6", base(0))], self.e2[("1x6", base(1))]
        it0 = self.f.by_id[c0["item_id"]]
        states = [",".join(str(x) for x in s) for s in it0["chains"][0]["states"]]
        self.assertEqual([t["answer"] for t in c0["tasks"]], states)                      # every task agreed on the right state
        self.assertEqual([[v["vote"] for v in t["votes"]] for t in c0["tasks"]], [[st, st] for st in states])
        self.assertEqual([[v["draw"] for v in t["votes"]] for t in c0["tasks"]], [[1, 2]] * 6)
        it1 = self.f.by_id[c1["item_id"]]
        right3 = list(it1["chains"][0]["states"][2])
        t3 = c1["tasks"][2]
        self.assertIsNone(t3["answer"])                                                    # no result at the cap
        self.assertTrue(t3["no_result"] and t3["at_cap"])
        want = [",".join(str(x) for x in bump(right3, 1 if d % 2 else 2)) for d in range(1, 9)] + [None]   # draw 9 has no answer line
        self.assertEqual([v["vote"] for v in t3["votes"]], want)
        self.assertEqual([t["answer"] for t in c1["tasks"][3:]], [None, None, None])     # never started
        self.assertEqual([t["votes"] for t in c1["tasks"][3:]], [[], [], []])
        self.assertEqual(c1["tasks"][0]["answer"], ",".join(str(x) for x in it1["chains"][0]["states"][0]))

    def test_picker_rows_join_sample_k(self):
        got = {k: (r["pick"], r["joined_kind"], r["correct"]) for k, r in self.pk.items()}
        self.assertEqual(got, {("6x1", base(0)): (3, "refusal", False),             # a pick of a no-reply sample: wrong
                               ("6x1", base(1)): (1, "answered", True),
                               ("6x1", base(2)): (None, None, False),               # no Pick line: wrong
                               ("1x6", base(0)): (2, "answered", False),
                               ("1x6", base(1)): (8, "answered", True),              # markup allowed (R1-2)
                               ("1x6", base(2)): (8, "answered", True)})
        r = self.pk[("6x1", base(0))]
        self.assertEqual(r["joined_custom_id"], f"{r['item_id']}-hm-03")
        self.assertEqual(r["sample_custom_ids"], [f"{r['item_id']}-hm-{s:02d}" for s in range(1, 9)])

    def test_c13_rows_are_relabelled_6x1_and_scored_as_the_product(self):
        rows = self.b["c13"]
        self.assertEqual([(r["shape"], r["shape_from_e3_rows"], r["arm"], r["setup"]) for r in rows], [("6x1", "1x1", "c13", "e3")] * 3)
        self.assertEqual([r["step_correct"] for r in rows], [[True, False, True, True, True, True], [True] * 6, [True] * 6])
        self.assertEqual(five_tests.e3_arm_scores(rows, "6x1"), {base(0): 0.0, base(1): 100.0, base(2): 100.0})
        self.assertEqual(five_tests.e3_arm_scores(rows, "1x1"), {})                     # nothing is left under e3_rows' label
        self.assertEqual([r["calls"] for r in rows], [12, 12, 12])

    def test_the_product_over_pieces_by_hand(self):
        rows = [{"base_id": "b", "shape": "6x1", "setup": "e3", "kind": "answered", "step_correct": s}
                for s in ([True, True, False, True, True, True], [True, True, True, True, True, True])]
        self.assertAlmostEqual(five_tests.e3_arm_scores(rows, "6x1")["b"], 50.0)            # 1 x 1 x 1/2 x 1 x 1 x 1

    def test_same_model_rows_are_their_own_setup(self):
        rows = self.b["same_model"]
        self.assertEqual(len(rows), 2 * 2 * 5)
        self.assertEqual({r["setup"] for r in rows}, {"same-model-check"})
        self.assertEqual(sum(r["correct"] for r in rows), 3 + 5 + 5 + 0)
        self.assertEqual({len(v) for v in self.b["same_model_joined"].values()}, {5})

    def test_main_rows_are_the_compared_arms_only(self):
        setups = {r["setup"] for r in self.b["main_rows"]}
        self.assertEqual(setups, {"haiku-med", "opus-med", "e3"})
        self.assertEqual(max(r["sample"] for r in self.b["main_rows"] if r["setup"] == "haiku-med"), 8)


class Driver(unittest.TestCase):
    """topup_analysis end to end on the fixture: every number by hand."""

    @classmethod
    def setUpClass(cls):
        cls.r = result()

    def test_same_model_check(self):
        sm = self.r["same_model_check"]
        # top-up shares 60, 100 (pieces) and 100, 0 (chain); main samples 1-5: 40, 80 and 60, 100
        self.assertAlmostEqual(sm["6x1"]["d"], 20.0)
        self.assertAlmostEqual(sm["1x6"]["d"], -30.0)
        self.assertAlmostEqual(sm["pooled"]["d"], -5.0)
        self.assertEqual(sm["6x1"]["ci95"], [20.0, 20.0])
        self.assertEqual(sm["1x6"]["ci95"], [-100.0, 40.0])
        self.assertEqual(sm["pooled"]["ci95"], [-40.0, 30.0])                              # per base 30 and -40
        self.assertEqual((sm["pooled"]["bootstrap_name"], sm["pooled"]["seed"]), ("same_model:pooled", 20261014))
        per_base = {base(0): [20.0, 40.0], base(1): [20.0, -100.0]}
        want = cluster_bootstrap([sorted(per_base)], lambda s: sum(sum(per_base[b]) for b in s) / (2 * len(s)), "same_model:pooled",
                                 draws=DRAWS, seed=20261014)
        self.assertEqual(sm["pooled"]["ci95"], list(want))
        tok = sm["output_tokens"]
        self.assertEqual(tok["top_up"]["mean_output_tokens"], (19 * TOUT_TOP + 0) / 20)       # one refusal (0 out)
        self.assertEqual(tok["main"]["mean_output_tokens"], (19 * TOUT_MAIN + 0) / 20)
        self.assertAlmostEqual(tok["relative_change"], 95 / 47.5 - 1)
        self.assertEqual(sm["refusals_truncations"]["top_up"], {"calls": 20, "refusals": 1, "truncations": 0, "missing": 0})
        self.assertEqual(sm["refusals_truncations"]["main"], {"calls": 20, "refusals": 1, "truncations": 0, "missing": 0})
        self.assertEqual(sm["flag"]["status"], "fired")                                      # tokens moved by 100%
        self.assertEqual((sm["flag"]["accuracy_condition"], sm["flag"]["tokens_condition"]), (False, True))

    def test_accuracy(self):
        a = self.r["accuracy"]
        exp = {"e2": {"6x1": 100 / 3, "1x6": 200 / 3}, "c13": {"6x1": 200 / 3}, "h-pick8": {"6x1": 100 / 3, "1x6": 200 / 3},
               "vote8": {"6x1": 100 / 3, "1x6": 50.0}, "any8": {"6x1": 200 / 3, "1x6": 100.0},
               "single8": {"6x1": 25.0, "1x6": 162.5 / 3}, "main-e3": {"1x6": 100 / 3}, "main-om": {"6x1": 200 / 3, "1x6": 100 / 3}}
        for arm, per in exp.items():
            for shape, v in per.items():
                self.assertAlmostEqual(a[arm][shape]["mean"], v, msg=f"{arm} {shape}")
                self.assertEqual(a[arm][shape]["bootstrap_name"], f"topup:acc:{arm}:{shape}")
        self.assertAlmostEqual(a["e2"]["pooled"]["mean"], 50.0)
        self.assertNotIn("pooled", a["c13"])

    def test_comparisons(self):
        c = self.r["comparisons"]
        exp = {"topup:e2-e3:1x6": (100 / 3, True), "topup:e2-e3:6x1": (-100 / 3, False), "topup:e2-om:6x1": (-100 / 3, True),
               "topup:e2-om:1x6": (100 / 3, True), "topup:hp8-vote8:6x1": (0.0, True), "topup:hp8-vote8:1x6": (50 / 3, True),
               "topup:hp8-any8:6x1": (-100 / 3, True), "topup:hp8-any8:1x6": (-100 / 3, True),
               "topup:hp8-single:6x1": (25 / 3, True), "topup:hp8-single:1x6": (12.5, True)}
        self.assertEqual(set(exp), {k for k in c if k.startswith("topup:")})
        for name, (d, cross) in exp.items():
            self.assertAlmostEqual(c[name]["d"], d, msg=name)
            self.assertEqual(c[name]["n"], 3)
            self.assertEqual(c[name]["cross_window"], cross)
            self.assertEqual(c[name]["seed"], bootstrap.derive_seed(20261014, name))
            self.assertEqual(c[name].get("same_model_flag"), "fired" if cross else None)
            self.assertNotIn("p", c[name])
            self.assertNotIn("reading", c[name])
        diffs = [100.0 - 100.0, 100.0 - 0.0, 0.0 - 0.0]                                       # E2 - main E3 at 1x6, base order
        want = bootstrap.paired_bca(diffs, margin=-10, B=B, seed=bootstrap.derive_seed(20261014, "topup:e2-e3:1x6"))
        self.assertEqual(c["topup:e2-e3:1x6"]["ci95"], list(want["ci95"]))
        self.assertEqual(c["topup:hp8-vote8:6x1"]["ci95"], [0.0, 0.0])                      # all three differences 0

    def test_test4_at_pieces(self):
        t = self.r["test4_pieces"]
        self.assertEqual((t["seed_name"], t["seed_base"], t["margin"]), ("t4@6x1", 20261011, -10.0))
        self.assertEqual(t["label"], "unadjusted (exploratory, outside Holm)")
        self.assertIn("different window", t["methods_note"])
        self.assertEqual(t["same_model_flag"], "fired")
        diffs = [0.0 - 100.0, 100.0 - 0.0, 100.0 - 100.0]                                    # C13 - Opus-medium at 6x1
        want = bootstrap.paired_bca(diffs, margin=-10, B=B, seed=bootstrap.derive_seed(20261011, "t4@6x1"))
        for view in ("as_deployed", "refusals_out", "truncations_out"):
            self.assertAlmostEqual(t[view]["d"], 0.0)
            self.assertEqual(t[view]["ci95"], list(want["ci95"]))
            declared = want["p_one_sided"] <= 0.025
            self.assertEqual(t[view]["reading"], bootstrap.three_way(declared, want["ci95"], -10.0))

    def test_e2_counts(self):
        p, c = self.r["e2_counts"]["6x1"], self.r["e2_counts"]["1x6"]
        self.assertEqual(p["aggregator_changes"], {"changed": 2, "wrong_chain_turned_right": 1, "right_chain_turned_wrong": 1,
                                                   "of_which_aggregator_unreadable": 0, "of_which_helpers_had_no_result": 1,
                                                   "over_puzzles_with_a_final_aggregator": 2})
        self.assertEqual(c["aggregator_changes"], {"changed": 1, "wrong_chain_turned_right": 1, "right_chain_turned_wrong": 0,
                                                   "of_which_aggregator_unreadable": 0, "of_which_helpers_had_no_result": 1,
                                                   "over_puzzles_with_a_final_aggregator": 2})
        self.assertEqual((p["failed_tasks"], c["failed_tasks"]), ({"puzzles": 1, "tasks": 1}, {"puzzles": 1, "tasks": 1}))
        self.assertEqual(p["failed_plans"]["puzzles"], 1)
        self.assertEqual([(x["planner_kind"], x["planner_stop_reason"]) for x in p["failed_plans"]["list"]], [("refusal", "refusal")])
        self.assertEqual([(x["planner_kind"], x["planner_stop_reason"]) for x in c["failed_plans"]["list"]], [("answered", "end_turn")])
        self.assertEqual((p["unfinished_puzzles"], c["unfinished_puzzles"]), (0, 0))

    def test_picker_positions(self):
        pp = self.r["picker_positions"]
        self.assertEqual({k: v for k, v in pp["6x1"].items() if v}, {"1": 1, "3": 1, "none": 1, "puzzles": 3})
        self.assertEqual({k: v for k, v in pp["1x6"].items() if v}, {"2": 1, "8": 2, "puzzles": 3})
        self.assertEqual(pp["pooled"]["puzzles"], 6)

    def test_costs(self):
        top = prices.cost(HAIKU, Usage(input_tokens=100, output_tokens=TOUT_TOP), batch=False)
        main = prices.cost(HAIKU, Usage(input_tokens=100, output_tokens=TOUT_MAIN), batch=False)
        cs = self.r["costs"]["per_puzzle"]
        # chain E2: base 0 = 1 + 6 x 2 + 1 calls, base 1 = 1 + 2 + 2 + 9 + 1, base 2 = the planner alone
        self.assertAlmostEqual(cs["e2"]["1x6"]["mean"], float(Fraction(top) * (14 + 15 + 1) / 3))
        self.assertAlmostEqual(cs["h-pick8-extra"]["1x6"]["mean"], float(top))
        self.assertAlmostEqual(cs["h-pick8-total"]["1x6"]["mean"], float(top + 8 * main))
        self.assertAlmostEqual(cs["c13"]["6x1"]["mean"], float(12 * top))
        self.assertEqual(cs["e2"]["1x6"]["cpc"]["correct"], 2.0)
        self.assertIsNone(cs["h-pick8-extra"]["1x6"]["cpc"])                               # CPC on the picker's total only
        self.assertIsNotNone(cs["h-pick8-total"]["1x6"]["cpc"])
        self.assertAlmostEqual(cs["e2"]["1x6"]["cpc"]["cpc"], float(Fraction(top) * 30 / 2))
        self.assertIn("pooled", cs["e2"])
        self.assertIsNotNone(cs["e2"]["1x6"]["batch_mean"])

    def test_compliance(self):
        rates = self.r["format_refusals_truncations_missing"]["rates"]
        self.assertEqual(rates["same_model 1x6"]["refusals_by_category"]["cyber"]["count"], 1)
        self.assertEqual(rates["e2_planner 6x1"]["refusals_by_category"]["cyber"]["count"], 1)
        self.assertEqual(rates["e2_planner 1x6"]["plan_failed_among_answered"], {"count": 1, "answered": 3, "above_5_percent": True})
        self.assertEqual(rates["h_pick8 6x1"]["unreadable_pick_among_answered"], {"count": 1, "answered": 3, "above_5_percent": True})
        self.assertEqual(rates["e2_helpers 1x6"]["unreadable_votes"], 1)
        self.assertEqual(rates["c13 6x1"]["missing_puzzles"]["count"], 0)
        self.assertIn("e2 1x6", self.r["format_refusals_truncations_missing"]["item_17_flags"])

    def test_inputs_are_names_and_hashes_and_choices_are_written(self):
        inp = self.r["inputs"]
        self.assertEqual(inp["plan"], "topup-plan.json")
        self.assertEqual(len(inp["run"]["calls.jsonl_sha256"]), 64)
        self.assertEqual(len(inp["main_run"]["calls.jsonl_sha256"]), 64)
        self.assertTrue(inp["run_manifest_check"]["checked"])
        self.assertNotIn(str(fixture().root), json.dumps(self.r, default=str))
        for k in ("pieces_no_result", "plan_failed", "c13_rows", "join", "flag_rule", "main_run_stamp", "same_model_size"):
            self.assertIn(k, self.r["choices"])
        ch = self.r["choices"]
        self.assertIn("ruling 4", ch["pieces_no_result"])                                  # Edith code r1: the ruling numbers
        self.assertIn("ruling 1", ch["join"])
        self.assertIn("ruling 7", ch["c13_rows"])

    def test_the_stamp_and_the_code_are_recorded(self):
        st = self.r["inputs"]["main_run_stamp"]
        self.assertTrue(st["all_match"])
        self.assertEqual(set(st["files"]), set(topup_analysis.STAMP_FILES))
        for n, d in st["files"].items():
            self.assertEqual((d["expected"], d["match"]), (d["observed"], True), n)
            self.assertEqual(d["observed"], hashlib.sha256((fixture().main_dir / n).read_bytes()).hexdigest())
        code = self.r["code"]
        from harness.analysis import main_rows
        self.assertEqual(code["sha256"]["main_rows.py"], hashlib.sha256(Path(main_rows.__file__).read_bytes()).hexdigest())
        self.assertEqual(set(code["sha256"]), {"main_rows.py", "topup_rows.py", "topup_analysis.py", "topup.py"})
        self.assertIn("commit", code["git"])
        self.assertEqual(self.r["inputs"]["same_model_size_check"], {"checked": True, "bases": 2, "tries": 5, "rows": 20})


def _copy(src: Path) -> Path:
    d = _tmpdir() / src.name
    shutil.copytree(src, d)
    return d


def _drop(log: Path, pred) -> None:
    lines = [ln for ln in log.read_text().splitlines() if ln.strip()]
    log.write_text("\n".join(ln for ln in lines if not (json.loads(ln).get("final") and pred(json.loads(ln)))) + "\n")


class Stops(unittest.TestCase):
    """A failed join stops the driver; other refusals."""

    @unittest.skipUnless((Path(topup.ROOT) / topup_analysis.MAIN_RUN_STAMP["source"]).is_file(), "the D-93 stamp file is not in the released package")
    def test_the_real_stamp_is_the_d93_stamp_file(self):
        # the constants are the stamp's own lines (decisions/briefings/2026-10-12-analysis-stamp/analysis-stamp.txt)
        text = (Path(topup.ROOT) / topup_analysis.MAIN_RUN_STAMP["source"]).read_text()
        for n, h in topup_analysis.MAIN_RUN_STAMP["sha256"].items():
            self.assertRegex(text, rf"(?m)^{n.replace('.', '[.]')}\s+{h}$")
        self.assertEqual(set(topup_analysis.MAIN_RUN_STAMP["sha256"]), set(topup_analysis.STAMP_FILES))
        self.assertIn("main run main-l14n6-1", text)
        self.assertEqual(topup_analysis.MAIN_RUN_STAMP["run_id"], "main-l14n6-1")
        self.assertEqual(topup_analysis.SAME_MODEL_SIZE, (20, 5))

    def test_one_mismatched_main_run_file_stops_the_driver(self):
        f = fixture()
        for n in topup_analysis.STAMP_FILES:
            main = _copy(f.main_dir)
            stamp = f.stamp(main)
            with open(main / n, "a") as fh:
                fh.write("\n")                                                          # one byte more in one file
            with self.assertRaises(topup_analysis.StampMismatch) as cm:
                f.analyse(main_dir=main, stamp=stamp)
            self.assertIn(n, str(cm.exception))
        main = _copy(f.main_dir)
        stamp = f.stamp(main)
        (main / "runner.log").unlink()                                                    # a missing file stops it too
        with self.assertRaises(topup_analysis.StampMismatch):
            f.analyse(main_dir=main, stamp=stamp)
        with self.assertRaises(topup_analysis.StampMismatch):
            f.analyse(stamp=dict(f.stamp(), run_id="main-l14n6-1"))                       # another run's stamp

    def test_the_real_stamp_refuses_the_fixture_main_run(self):
        with self.assertRaises(topup_analysis.StampMismatch):
            fixture().analyse(stamp=topup_analysis.MAIN_RUN_STAMP)

    def test_the_same_model_check_must_be_the_specs_size(self):
        with self.assertRaises(topup_analysis.SpecSizeError):
            fixture().analyse(same_model_size=topup_analysis.SAME_MODEL_SIZE)             # the fixture is 2 x 5, not 20 x 5

    def test_a_run_folder_without_a_manifest_is_refused(self):
        f = fixture()
        run = _copy(f.run_dir)
        (run / "manifest.json").unlink()
        with self.assertRaises(ValueError) as cm:
            f.analyse(run_dir=run)
        self.assertIn("manifest.json", str(cm.exception))

    def test_a_missing_main_sample_stops_the_driver(self):
        f = fixture()
        main = _copy(f.main_dir)
        _drop(main / "calls.jsonl", lambda r: r["custom_id"].endswith("-6x1-hm-07"))
        with self.assertRaises(topup_rows.JoinError) as cm:
            f.analyse(main_dir=main)
        self.assertIn("join", str(cm.exception))
        self.assertIn("hm-07", str(cm.exception))

    def test_hm_join_refuses_a_missing_row(self):
        f = fixture()
        rows = [dict(r) for r in f.built()["main_rows"]]
        for r in rows:
            if r["setup"] == "haiku-med" and r["sample"] == 4 and r["base_id"] == base(1):
                r["kind"] = "missing"
        with self.assertRaises(topup_rows.JoinError):
            topup_rows.hm_join(rows, [it for it in f.items if it["base_index"] < 2], 5, "the same-model check")

    def test_wrong_main_extras_stop_the_driver(self):
        f = fixture()
        with self.assertRaises(topup_rows.JoinError):
            f.analyse(extras=("sl",))

    def test_a_record_outside_the_plan_stops_the_driver(self):
        f = fixture()
        plan = f.plan()
        plan["parts"] = ["same_model", "h_pick8", "e2"]
        with self.assertRaises(ValueError):
            topup_rows.check_records(f.man, f.items, topup_rows.top_records(f.run_dir), plan)

    def test_another_plan_than_the_runs_copy_is_refused(self):
        f = fixture()
        plan = f.plan()
        plan["max_rounds"] = 7
        with self.assertRaises(ValueError):
            topup_rows.build(plan, f.run_dir, f.main_dir)
        run = _copy(f.run_dir)
        (run / "topup_plan.json").unlink()
        with self.assertRaises(ValueError):
            topup_rows.build(f.plan(), run, f.main_dir)


class Unfinished(unittest.TestCase):
    """Unfinished puzzles are missing rows: wrong as deployed, counted."""

    def test_an_unfinished_c13_puzzle_and_e2_puzzle(self):
        f = fixture()
        run = _copy(f.run_dir)
        p2 = next(it for it in f.items if key(it) == ("P", 2))["id"]
        c0 = next(it for it in f.items if key(it) == ("C", 0))["id"]
        _drop(run / "calls.jsonl", lambda r: r["custom_id"].startswith(f"{p2}-es-05") or r["custom_id"] == f"{c0}-ta-01")
        b = topup_rows.build(f.plan(), run, f.main_dir)
        r = next(x for x in b["c13"] if x["item_id"] == p2)
        self.assertEqual((r["kind"], r["step_correct"], r["shape"]), ("missing", [True, True, True, True, False, True], "6x1"))
        e = next(x for x in b["e2"] if x["item_id"] == c0)
        self.assertEqual((e["kind"], e["stage"], e["correct"]), ("missing", "aggregator", False))


NC = "not completed"
NUMBERS = {"n", "d", "ci95", "p", "mean", "declared", "seed"}


class CutShort(unittest.TestCase):
    """D-106(G) (spec section 5 "A run cut short" at 9c007e5; Edith's pass-2 ruling and detail): an arm with any designed call that has
    no final record reads "not completed" with its designed, final and missing counts only (no score, no flag, no reading), enters no
    comparison (each keeps its place and labels), and Test 4 at pieces gets no reading if C13 is not completed; a same-model check not
    completed gives "not completed" as the flag beside every cross-window comparison. The completed arms are as in the full run.
    `stopped` is a real top-up run stopped mid-way (the runner itself, max_rounds = 1); the others drop one arm's records from the
    finished run's log."""

    @classmethod
    def setUpClass(cls):
        cls.f = f = fixture()
        cls.full = result()
        cls.items = {key(it): it["id"] for it in f.items}
        out = _tmpdir() / "stopped"
        cls.stopped_run = topup.run_topup(guard(run_cap="100"), FakeTransport(batch_reply=f.top_reply), out, f.plan(), f.main_dir,
                                          sleep=lambda s: None, max_rounds=1)
        cls.stopped = f.analyse(run_dir=out)
        b = f.built()

        def dropped(pred):
            run = _copy(f.run_dir)
            _drop(run / "calls.jsonl", pred)
            return f.analyse(run_dir=run)
        p2, c0, p1 = cls.items[("P", 2)], cls.items[("C", 0)], cls.items[("P", 1)]
        sc0 = b["same_model"][0]["custom_id"]
        cls.c13 = dropped(lambda r: r["custom_id"].startswith(f"{p2}-es-05"))           # all draws of one C13 piece: never sent
        cls.e2 = dropped(lambda r: r["custom_id"] == f"{c0}-ta-01")                     # one aggregator never final
        cls.picker = dropped(lambda r: r["custom_id"] == f"{p1}-pk-01")                 # one picker call never final
        cls.same = dropped(lambda r: r["custom_id"] == sc0)                             # one same-model try never final

    def counts_only(self, entry, counts=None):
        self.assertEqual(entry["reading"], NC)
        self.assertFalse(NUMBERS & set(entry), entry)
        self.assertGreater(entry["missing"], 0)
        self.assertEqual(entry["designed"], entry["final"] + entry["missing"])
        if counts is not None:
            self.assertEqual((entry["designed"], entry["final"], entry["missing"]), counts)

    def held_comparisons(self, res, arm):
        held = [k for k, v in res["comparisons"].items() if k.startswith("topup:") and v.get("reading") == NC]
        for name in held:
            c = res["comparisons"][name]
            self.assertIn(arm, c["not_completed_arms"])
            self.assertFalse(NUMBERS & set(c), name)
            full = self.full["comparisons"][name]                                      # its place and labels kept
            for k in ("challenger", "comparator", "shape", "cross_window", "same_model_flag", "seed_name"):
                self.assertEqual(c.get(k), full.get(k), (name, k))
        return sorted(held)

    def unchanged(self, res, arms=(), comps=(), t4=True, same=True, positions=True, e2_counts=True, cost_arms=()):
        for a in arms:
            self.assertEqual(res["accuracy"][a], self.full["accuracy"][a], a)
        for c in comps:
            self.assertEqual(res["comparisons"][c], self.full["comparisons"][c], c)
        if t4:
            self.assertEqual(res["test4_pieces"], self.full["test4_pieces"])
        if same:
            self.assertEqual(res["same_model_check"], self.full["same_model_check"])
        if positions:
            self.assertEqual(res["picker_positions"], self.full["picker_positions"])
        if e2_counts:
            self.assertEqual(res["e2_counts"], self.full["e2_counts"])
        for a in cost_arms:
            self.assertEqual(res["costs"]["per_puzzle"][a], self.full["costs"]["per_puzzle"][a], a)

    def test_the_label_is_one_constant(self):
        self.assertEqual(topup_analysis.NOT_COMPLETED_TOPUP, "not completed")
        gate = self.full["completeness"]
        self.assertEqual(gate["not_completed"], [])
        self.assertEqual({p: g["completed"] for p, g in gate["arms"].items()},
                         {"same_model": True, "h_pick8": True, "e2": True, "c13": True})
        self.assertEqual({p: g["missing"] for p, g in gate["arms"].items()}, {"same_model": 0, "h_pick8": 0, "e2": 0, "c13": 0})
        self.assertEqual(gate["arms"]["c13"]["final"], 36)                              # 3 puzzles x 6 pieces x 2 draws
        # E2's final calls: chain 14 + 15 + 1 (as test_costs), pieces 14 + (1 + 5 x 2 + 9 + 1) + 1 (the refused planner)
        self.assertEqual(gate["arms"]["e2"]["final"], (14 + 15 + 1) + (14 + 21 + 1))
        self.assertIn("cut_short", self.full["choices"])
        self.assertIn("D-106(G)", self.full["choices"]["cut_short"])

    def test_a_run_stopped_mid_way(self):
        """The runner stops after round 1 (same-model check, pickers, planners, C13's first draws): the Haiku team is not completed;
        the picker, C13 (two agreeing draws decide each piece) and the same-model check are, and read as in the full run."""
        self.assertEqual(self.stopped_run["rounds_logged"], 1)
        r = self.stopped
        gate = r["completeness"]["arms"]
        self.assertEqual(r["completeness"]["not_completed"], ["e2"])
        self.assertEqual(gate["e2"]["final"], 6)                                         # the 6 planners
        self.assertEqual(gate["e2"]["puzzles_unfinished"], 4)                            # 2 plans failed: those 2 are finished
        self.counts_only(r["accuracy"]["e2"])
        self.assertEqual(self.held_comparisons(r, "e2"), ["topup:e2-e3:1x6", "topup:e2-e3:6x1", "topup:e2-om:1x6", "topup:e2-om:6x1"])
        self.counts_only(r["e2_counts"])
        self.counts_only(r["costs"]["per_puzzle"]["e2"])
        self.unchanged(r, arms=("h-pick8", "c13", "vote8", "any8", "single8", "main-e3", "main-om"), e2_counts=False,
                       comps=[k for k in self.full["comparisons"] if k.startswith("topup:hp8-")],
                       cost_arms=("h-pick8-extra", "h-pick8-total", "c13"))

    def test_c13_not_completed(self):
        r = self.c13
        self.assertEqual(r["completeness"]["not_completed"], ["c13"])
        self.counts_only(r["accuracy"]["c13"], (36, 34, 2))                              # the piece's 2 first draws, never final
        self.assertEqual(r["accuracy"]["c13"]["puzzles_unfinished"], 1)
        t4 = r["test4_pieces"]
        self.assertEqual(t4["reading"], NC)                                              # Test 4 at pieces: no reading
        self.assertFalse(set(topup_analysis.scoring.VIEWS) & set(t4))
        self.counts_only(t4["c13"])
        for k in ("label", "methods_note", "same_model_flag", "seed_name", "margin", "challenger", "comparator", "shape"):
            self.assertEqual(t4[k], self.full["test4_pieces"][k], k)
        self.assertEqual(self.held_comparisons(r, "c13"), ["topup:e2-e3:6x1"])
        self.assertNotIn("same_model_flag", r["comparisons"]["topup:e2-e3:6x1"])       # within the top-up window
        self.counts_only(r["costs"]["per_puzzle"]["c13"])
        self.unchanged(r, arms=("e2", "h-pick8", "vote8", "main-om"), t4=False, cost_arms=("e2", "h-pick8-total"),
                       comps=[k for k in self.full["comparisons"] if k.startswith("topup:") and k != "topup:e2-e3:6x1"])

    def test_e2_not_completed(self):
        r = self.e2
        self.assertEqual(r["completeness"]["not_completed"], ["e2"])
        self.counts_only(r["accuracy"]["e2"])
        self.assertEqual((r["accuracy"]["e2"]["missing"], r["accuracy"]["e2"]["puzzles_unfinished"]), (1, 1))   # the aggregator
        self.assertEqual(len(self.held_comparisons(r, "e2")), 4)
        self.counts_only(r["e2_counts"])
        self.unchanged(r, arms=("h-pick8", "c13"), e2_counts=False, cost_arms=("c13", "h-pick8-total"),
                       comps=[k for k in self.full["comparisons"] if k.startswith("topup:hp8-")])

    def test_picker_not_completed(self):
        r = self.picker
        self.assertEqual(r["completeness"]["not_completed"], ["h_pick8"])
        self.counts_only(r["accuracy"]["h-pick8"], (6, 5, 1))
        self.assertEqual(self.held_comparisons(r, "h-pick8"), sorted(k for k in self.full["comparisons"] if k.startswith("topup:hp8-")))
        self.counts_only(r["picker_positions"])
        self.counts_only(r["costs"]["per_puzzle"]["h-pick8-extra"])
        self.counts_only(r["costs"]["per_puzzle"]["h-pick8-total"])
        self.unchanged(r, arms=("e2", "c13", "vote8", "any8", "single8"), positions=False, cost_arms=("e2", "c13"),
                       comps=[k for k in self.full["comparisons"] if k.startswith("topup:e2-")])

    def test_same_model_check_not_completed(self):
        r = self.same
        self.assertEqual(r["completeness"]["not_completed"], ["same_model"])
        sm = r["same_model_check"]
        self.counts_only({k: v for k, v in sm.items() if k not in ("flag", "label")}, (20, 19, 1))
        self.assertEqual(sm["flag"], {"status": NC})                                    # no flag computed
        self.assertFalse({"6x1", "1x6", "pooled", "output_tokens"} & set(sm))
        for name, c in r["comparisons"].items():
            if not name.startswith("topup:"):
                continue
            full = self.full["comparisons"][name]
            if c["cross_window"]:
                self.assertEqual(c["same_model_flag"], NC, name)
            else:
                self.assertNotIn("same_model_flag", c)
            self.assertEqual({k: v for k, v in c.items() if k != "same_model_flag"},
                             {k: v for k, v in full.items() if k != "same_model_flag"}, name)   # the numbers are unchanged
        self.assertEqual(r["test4_pieces"]["same_model_flag"], NC)
        self.assertEqual({k: v for k, v in r["test4_pieces"].items() if k != "same_model_flag"},
                         {k: v for k, v in self.full["test4_pieces"].items() if k != "same_model_flag"})
        self.unchanged(r, arms=("e2", "h-pick8", "c13"), t4=False, same=False, cost_arms=("e2", "c13", "h-pick8-total"))


class DryRun(unittest.TestCase):
    """The runner's dry path (DryTransport: every reply 'DRY RUN') read by the driver: every plan fails, every C13 piece ends with no
    result at the cap, no pick reads."""

    def test_the_driver_reads_a_dry_run(self):
        f = fixture()
        out = _tmpdir() / "dry"
        topup.run_topup(guard(run_cap="100"), DryTransport(), out, f.plan(), f.main_dir, sleep=lambda s: None)
        r = f.analyse(run_dir=out)
        self.assertEqual(r["e2_counts"]["6x1"]["failed_plans"]["puzzles"] + r["e2_counts"]["1x6"]["failed_plans"]["puzzles"], 6)
        self.assertEqual(r["accuracy"]["c13"]["6x1"]["mean"], 0.0)
        self.assertEqual(r["picker_positions"]["pooled"]["none"], 6)
        self.assertEqual(r["accuracy"]["e2"]["pooled"]["mean"], 0.0)


class Cli(unittest.TestCase):
    def test_the_command_always_checks_the_real_stamp(self):
        f = fixture()
        out = _tmpdir() / "analysis.json"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = topup_analysis.main(["--plan", str(f.plan_path), "--run", str(f.run_dir), "--main-run", str(f.main_dir), "--out", str(out)])
        self.assertEqual(code, 2)
        self.assertTrue(buf.getvalue().startswith("REFUSED: "))
        self.assertFalse(out.exists())

    def test_refuses_to_overwrite(self):
        f = fixture()
        out = _tmpdir() / "analysis.json"
        out.write_text("{}")
        with self.assertRaises(SystemExit):
            topup_analysis.main(["--plan", str(f.plan_path), "--run", str(f.run_dir), "--main-run", str(f.main_dir), "--out", str(out)])
        self.assertEqual(out.read_text(), "{}")

    def test_writes_once(self):
        f = fixture()
        out = _tmpdir() / "analysis.json"
        # the command takes no stamp or size: the module's constants stand in for the fixture here
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(topup_analysis, "MAIN_RUN_STAMP", f.stamp()), \
                mock.patch.object(topup_analysis, "SAME_MODEL_SIZE", (2, 5)):
            topup_analysis.main(["--plan", str(f.plan_path), "--run", str(f.run_dir), "--main-run", str(f.main_dir), "--out", str(out)])
        doc = json.loads(out.read_text())
        self.assertEqual(doc["constants"]["B"], 10_000)
        self.assertEqual(doc["constants"]["draws"], 2_000)
        self.assertNotIn(str(f.root), out.read_text())
        with self.assertRaises(SystemExit):
            topup_analysis.main(["--plan", str(f.plan_path), "--run", str(f.run_dir), "--main-run", str(f.main_dir), "--out", str(out)])


if __name__ == "__main__":
    unittest.main()
