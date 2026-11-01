"""Study 1b end to end (Edith's code review r1, the joint test): the REAL slim runner (harness.pareto.slim.run_slim, a fake Batch
transport, never live) runs the real plan's arms, trial round, limit rule and cut order (data/plans/study1b-plan.json) on small fixture
sets shaped like the plan's three test sets and three trial-round sets, under a cap low enough to force the §7 cut; the projection is
still over after the whole order, so the run stops, and goes on only with --accept-projection. Then study1b_k and the 1b driver run on
that run folder exactly as written. It shows: the cut arms are reported as "cut by §7 (cost)" (never missing or 0%), the calibrated
arms' limits come from calibration_limits, the manifest check passes, and the D-97 sensitivity runs. It prints a compact summary
(counts, cut arms, limits, k), never item text. Offline only.

Lock-4 audit A1 (Edith's ruling): the runner sends the confirmatory arms first (hx and om at 16, then at 6, all final before any other
arm), and the driver's completeness gate holds a test whose hx or om tries are not all final ("not completed", p = 1, no reading).
`StoppedRuns` runs the same plan four more times, stopped in four ways: (i) B3's set never sent; (ii) half of B3's set sent; (iii) one
errored hx try at 16 never sent again; (iv) stopped right after the confirmatory waves (no descriptive arm sent). Each gives "not
completed" for the right tests (B1 and B2 together: they share the N = 16 set) and leaves the other tests' readings as in the full run.
Cases (iii) and (iv) also check §6 for a run stopped early (spec §6 at 9c007e5, lock-4 audit C1): hx and om at a held length on their
final tries, "not completed; descriptive only"; an arm never sent "not sent (run stopped)", never 0%; every entry with its designed,
final and missing counts; complete arms as in the full run."""

import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from harness.analysis import kscript, study1b, study1b_k
from harness.pareto import slim
from harness.pareto.calllog import CallLog
from harness.pareto.prices import OPUS
from harness.pareto.transport import FakeTransport, TransportError
from harness.taskgen.freeze import write_set
from harness.tests.fakes import guard, reply
from harness.tests.test_study1b import bump, chain_text, fixture_set_ids, pieces_text

import atexit as _atexit
import shutil as _shutil


def _tmpdir() -> Path:
    """A temp folder removed when the test process exits: these tests write nowhere else."""
    d = Path(tempfile.mkdtemp(prefix="pareto-test-"))
    _atexit.register(_shutil.rmtree, d, True)
    return d


# FIXTURE set ids (audit A20 / K3: never the sealed sets' ids, since an item's content is seeded by its set id); the driver's and k's
# set ids are patched to them (test_study1b.fixture_set_ids). Small: 3, 4 and 2 base puzzles; the trial round on 2 bases.
TEST_SETS = (("fxe-ledger-l14n16-v1", "l14n16", 3), ("fxe40-ledger-l14n6-v1", "l14n6", 4), ("fxe-ledger-l14n12-v1", "l14n12", 2))
TRIAL_SETS = (("fxecal-ledger-l14n16-v1", "l14n16", 2), ("fxecal-ledger-l14n6-v1", "l14n6", 2), ("fxecal-ledger-l14n12-v1", "l14n12", 2))
N16, N6, N12 = (sid for sid, _, _ in TEST_SETS)
TRIAL_PREFIX = "fxecal-"
CAP = "15"                     # 0.9 x $15 = $13.50: the Opus trial round alone puts the projection over it whatever is cut
ERRORED = f"{N16}-002-16x1-hm-05"   # one DESCRIPTIVE test call errors: a missing try (planned, sent, no final record); B1-B3 complete
ERRORED_HX = f"{N16}-002-16x1-hx-10"   # StoppedRuns (iii): a confirmatory try that errors and is never sent again
CUT = "cut by §7 (cost)"
NOT_SENT = "not sent (run stopped)"
HELD = "not completed; descriptive only"


def fixture_plan(root: Path) -> dict:
    """The real plan, with its sets pointed at the fixture sets (paths and items_sha256) and base_puzzles 2; arms, tries, floors, the
    limit rule, the cost bases and the cut order unchanged."""
    plan = copy.deepcopy(slim.read_plan(slim.ROOT / "data" / "plans" / "study1b-plan.json"))
    by_steps = {16: 0, 6: 1, 12: 2}
    for s in plan["sets"]:
        sid = TEST_SETS[by_steps[s["steps"]]][0]
        s["set"] = str(root / sid)
        s["items_sha256"] = json.loads((root / sid / "manifest.json").read_text())["items_sha256"]
    for s in plan["calibration"]["sets"]:
        sid = TRIAL_SETS[by_steps[s["steps"]]][0]
        s["set"] = str(root / sid)
        s["items_sha256"] = json.loads((root / sid / "manifest.json").read_text())["items_sha256"]
    plan["calibration"]["base_puzzles"] = 2
    return slim.validate_plan(plan)


def make_fake(items_by_prompt, errored=ERRORED):
    """A Batch reply per custom id. Trial round: Opus high, xhigh and max write 60,000 tokens (dear, so the cut fires), the rest 1,000.
    Test calls: hx writes 2,000 tokens and om 525 (no input tokens: list cost $0.001 vs $0.0105, a cost ratio of 10.5, so k = 10 and B2
    is labelled 'for less than Opus's price' though kscript's own cap flag is off), every other arm 800. Answers: right, except hx
    when (base + try) % 4 == 0, om at 16 base 001 try 2, and other arms' every third try; ERRORED errors (a missing try)."""
    def fake(cid, params):
        if cid == errored:
            return {"type": "errored", "error": {"type": "overloaded_error"}}
        c = kscript.parse_custom_id(cid)
        tag, k = str(c["setup"]), int(c["sample"])
        item = items_by_prompt[params["messages"][0]["content"]]
        base = int(item["base_index"])
        trial = str(c["set_id"]).startswith(TRIAL_PREFIX)
        if trial:
            effort = params["output_config"]["effort"]
            tout = 60000 if params["model"] == OPUS and effort in ("high", "xhigh", "max") else 1000
            wrong = False
        else:
            tout = {"hx": 2000, "om": 525}.get(tag, 800)
            if tag == "hx":
                wrong = (base + k) % 4 == 0
            elif tag == "om":
                wrong = c["set_id"] == N16 and base == 1 and k == 2
            else:
                wrong = k % 3 == 0
        if int(item["depth"]) > 1:
            st = item["chains"][0]["states"]
            text = chain_text(st if not wrong else st[:-1] + [bump(st[-1])])
        else:
            ans = item["answer"]
            text = pieces_text(ans if not wrong else [bump(ans[0])] + ans[1:])
        return {"type": "succeeded", "message": reply(model=params["model"], text=text, tin=0, tout=tout)}
    return fake


class Stopping(FakeTransport):
    """A fake Batch transport that refuses (before running, not billed) the first batch for which `refuse(custom ids, batches
    already accepted)` is true, and every batch after it: the run stops there (the credit ran out, the deadline, the user's stop)."""

    def __init__(self, batch_reply, refuse=None):
        super().__init__(batch_reply=batch_reply)
        self.refuse, self.stopped = refuse, False

    def submit_batch(self, requests):
        ids = [r["custom_id"] for r in requests]
        if self.stopped or (self.refuse is not None and self.refuse(ids, self.batches)):
            self.stopped = True
            raise TransportError("stopped", "the run was stopped here (test)", billed="no", retryable=False)
        return super().submit_batch(requests)


def joint_run(td: Path, plan: dict, plan_path: Path, name: str, errored=ERRORED, refuse=None, max_wave_size=None) -> dict:
    """The plan through the real runner (it stops at projected_over_cap, then goes on on the ruling; a `refuse`d batch stops it for
    good), then study1b_k and the driver on the run folder as written."""
    test, cal = slim.load_sets(plan)
    fake = make_fake({it["prompt"]: it for _, _, its in test + cal for it in its}, errored)
    run_dir = td / name
    g = guard(run_cap=CAP)
    t1 = FakeTransport(batch_reply=fake)
    r1 = slim.run_slim(g, t1, run_dir, plan, sleep=lambda s: None, max_wave_size=max_wave_size)     # stops: projected over the cap
    t2 = Stopping(fake, refuse)
    try:
        r2 = slim.run_slim(g, t2, run_dir, plan, sleep=lambda s: None, max_wave_size=max_wave_size,
                           accept_projection_note="the user: go on uncut further (joint test)")
    except TransportError:
        r2 = {"stopped": "transport refused (test stop)"}
    k_path = run_dir / "k.json"
    study1b_k.main(["--run", str(run_dir), "--out", str(k_path)])
    return {"r1": r1, "r2": r2, "t1": t1, "t2": t2, "run_dir": run_dir, "k_path": k_path, "kdoc": json.loads(k_path.read_text()),
            "res": study1b.analyse(run_dir, k_path, plan_path=plan_path, B=200, draws=100),
            "sent": {x["custom_id"]: x["params"] for t in (t1, t2) for reqs in t.batches.values() for x in reqs},
            "batches": [[x["custom_id"] for x in reqs] for t in (t1, t2) for reqs in t.batches.values()]}


_SHARED: dict = {}


def shared_fixture() -> dict:
    """The fixture sets, the plan and the full joint run, made once per test process (both classes read them)."""
    if not _SHARED:
        td = _tmpdir()
        sets = _tmpdir()
        for sid, preset, nb in TEST_SETS + TRIAL_SETS:
            write_set(sets / sid, "ledger", preset, sid, nb, "d31", "scratch")
        plan = fixture_plan(sets)
        plan_path = td / "plan.json"
        plan_path.write_text(json.dumps(plan))
        _SHARED.update(td=td, plan=plan, plan_path=plan_path, full=joint_run(td, plan, plan_path, "study1b-joint"))
    return _SHARED


def _patch_ids(cls) -> None:
    fixture_set_ids({16: N16, 6: N6, 12: N12}, [sid for sid, _, _ in TRIAL_SETS], cls)


class JointRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _patch_ids(cls)
        sh = shared_fixture()
        cls.td, cls.plan, cls.plan_path = sh["td"], sh["plan"], sh["plan_path"]
        full = sh["full"]
        cls.run_dir, cls.k_path, cls.kdoc, cls.res = full["run_dir"], full["k_path"], full["kdoc"], full["res"]
        cls.r1, cls.r2, cls.t1, cls.t2, cls.sent, cls.batches = (full[k] for k in ("r1", "r2", "t1", "t2", "sent", "batches"))
        cls.limits = json.loads((cls.run_dir / "calibration_limits.json").read_text())

    def test_the_runner_stopped_then_went_on_on_the_ruling(self):
        self.assertEqual(self.r1["stopped"], "projected_over_cap")
        self.assertIsNone(self.r2["stopped"])
        cut = self.r1["cut"]
        self.assertTrue(cut["still_over"])
        order = [[st, t] for part in self.plan["cut"]["order"] for st, t in part["arms"]]
        self.assertEqual(sorted(cut["cut_arms"]), sorted(order))                      # the whole order, in its parts
        self.assertEqual([p["part"] for p in cut["cut_parts"]], [p["name"] for p in self.plan["cut"]["order"]])
        kinds = Counter(x.get("kind") for x in CallLog(self.run_dir / "calls.jsonl").records() if not x.get("final"))
        self.assertEqual((kinds["calibration_limits"], kinds["cut"], kinds["projection_accepted"]), (1, 1, 1))

    def test_cut_arms_are_reported_as_cut_not_missing(self):
        cut = {f"{t}@{st}" for st, t in self.r1["cut"]["cut_arms"]}
        self.assertEqual(cut, {"ox@6", "oxh@6", "sx@6", "sxh@6", "hx@12", "om@12", "hxh@16"})
        arms = self.res["descriptive"]["arms"]
        for key in cut:
            self.assertEqual(arms[key]["status"], CUT)
            self.assertNotIn("pooled", arms[key])
        for cid in self.sent:                                                         # never sent
            c = kscript.parse_custom_id(cid)
            n = {N16: 16, N6: 6, N12: 12}.get(str(c["set_id"]))
            self.assertNotIn(f"{c['setup']}@{n}", cut if n else set())
        self.assertEqual(self.res["plan_as_run"]["cut"]["label"], CUT)
        self.assertEqual(set(self.res["plan_as_run"]["cut"]["arms"]), cut)
        self.assertTrue(self.res["plan_as_run"]["cut"]["projection_accepted"])
        lc = self.res["descriptive"]["length_curve"]
        self.assertEqual((lc["haiku-max"]["12"], lc["opus-medium"]["12"]), ({"status": CUT}, {"status": CUT}))
        fig6 = {p["tag"]: p for p in self.res["descriptive"]["effort_figure"]["N=6"]["opus"]}
        self.assertEqual((fig6["ox"]["status"], fig6["oxh"]["status"]), (CUT, CUT))
        self.assertIn("pooled", fig6["oh"])                                          # oh is not in the order: sent and scored
        self.assertEqual(sorted(self.res["descriptive"]["format_refusals_truncations_missing"]["cut_by_section_7"]["arms"]), sorted(cut))
        rows = self.res["records"]
        self.assertEqual(rows["missing_rows"], 1)                                    # only ERRORED; no cut arm counted missing

    def test_partly_sent_descriptive_arm(self):
        """Spec §6 (C1): hm at 16 has one missing try (ERRORED): its official score counts it wrong, with its counts, and the
        exclude-missing view sits beside it, labelled. hx and om (complete) carry counts and no label."""
        arms = self.res["descriptive"]["arms"]
        hm = arms["hm@16"]
        self.assertEqual((hm["designed"], hm["final"], hm["missing"]), (30, 29, 1))     # 3 bases x 2 forms x 5
        self.assertEqual((hm["16x1"]["designed"], hm["16x1"]["missing"]), (15, 1))
        self.assertNotIn("label", hm)
        self.assertEqual(hm["missing_excluded"]["label"], "sensitivity: missing tries excluded")
        self.assertGreater(hm["missing_excluded"]["16x1"]["mean"], hm["16x1"]["mean"])   # the missing try no longer counted wrong
        self.assertEqual(hm["missing_excluded"]["1x16"], hm["1x16"])                      # nothing missing in the chain form
        for key in ("hx@16", "om@16", "hx@6", "om@6"):
            self.assertEqual(arms[key]["missing"], 0)
            self.assertFalse({"label", "status", "missing_excluded"} & set(arms[key]), key)
        fig = {p["tag"]: p for p in self.res["descriptive"]["effort_figure"]["N=16"]["haiku"]}
        self.assertEqual(fig["hm"]["missing_excluded"]["label"], "sensitivity: missing tries excluded")
        self.assertEqual(fig["hm"]["16x1"]["missing"], 1)
        self.assertNotIn("label", self.res["descriptive"]["vote_curve_n16"])

    def test_calibrated_limits_come_from_calibration_limits(self):
        lim = {(a["steps"], a["tag"]): a["max_tokens"] for a in self.limits["arms"]}
        floors = {(s["steps"], a["tag"]): a["calibrate"]["floor"] for s in self.plan["sets"] for a in s["arms"] if "calibrate" in a}
        self.assertEqual(set(lim), set(floors))
        for key, floor in floors.items():                                             # Opus high/xhigh/max at 6: 2 x 60,000; else the floor
            self.assertEqual(lim[key], 120000 if key in ((6, "oh"), (6, "oxh"), (6, "ox")) else floor, key)
        self.assertEqual(self.res["plan_as_run"]["limits"], [{k: a.get(k) for k in ("steps", "tag", "floor", "wave0_calls", "wave0_truncated",
                                                                                    "wave0_output_tokens_max", "max_tokens")}
                                                             for a in self.limits["arms"]])
        run = study1b.load_run(self.run_dir)
        for s in run["sets"]:
            mt = {a.name: a.max_tokens for a in s["arms"]}
            for cid, params, meta in s["requests"]:
                self.assertEqual(params["max_tokens"], mt[meta["setup"]])
                self.assertEqual(self.sent[cid]["max_tokens"], params["max_tokens"])   # what the runner sent
                if (s["n"], meta["setup"]) in lim:
                    self.assertEqual(params["max_tokens"], lim[(s["n"], meta["setup"])])

    def test_manifest_check_passes(self):
        mc = self.res["inputs"]["manifest_check"]
        self.assertTrue(mc["checked"])
        trial = 2 * 2 * len(floors_of(self.plan))                                     # 2 bases x 2 shapes x 1 try per calibrated arm
        test = sum(2 * nb * sum(a["n"] for a in s["arms"]) for s, (_, _, nb) in zip(self.plan["sets"], TEST_SETS))
        self.assertEqual(mc["n_items"], trial + test)
        self.assertEqual(json.loads((self.run_dir / "manifest.json").read_text())["n_items"], trial + test)

    def test_k_and_the_b2_label(self):
        self.assertEqual((self.kdoc["k"], self.kdoc["raw_k"], self.kdoc["ratio"], self.kdoc["capped"]), (10, 10, "21/2", True))
        self.assertEqual(self.res["k"]["k"], 10)
        self.assertIn("for less than Opus's price", self.res["costs_beside_tests"]["B2"]["wording"])

    def test_confirmatory_arms_are_sent_first(self):
        """A1: after the trial round, the batches go hx and om at 16, then hx and om at 6, then the other arms at 16, then at 6 (the
        12-step set is cut here); each batch is one set and one phase."""
        conf = {"hx", "om"}
        seq = []
        for ids in self.batches:
            c = [kscript.parse_custom_id(i) for i in ids]
            sids = {str(x["set_id"]) for x in c}
            if all(sid.startswith(TRIAL_PREFIX) for sid in sids):
                key = ("trial", None)                                                 # wave 0: the three trial-round sets together
            else:
                self.assertEqual(len(sids), 1)
                sid = sids.pop()
                phases = {"confirmatory" if x["setup"] in conf else "descriptive" for x in c}
                self.assertEqual(len(phases), 1)
                key = (sid, phases.pop())
            if not seq or seq[-1] != key:
                seq.append(key)
        self.assertEqual(seq, [("trial", None), (N16, "confirmatory"), (N6, "confirmatory"), (N16, "descriptive"), (N6, "descriptive")])

    def test_complete_run_passes_the_gate(self):
        comp = self.res["completeness"]
        for t in ("B1", "B2", "B3"):
            self.assertTrue(comp[t]["completed"], t)
            self.assertEqual({a["missing"] for a in comp[t]["arms"].values()}, {0})
        self.assertEqual(comp["B1"]["arms"]["hx"], {"designed": 60, "final": 60, "missing": 0})        # 3 bases x 2 forms x 10
        self.assertEqual(comp["B3"]["arms"]["om"], {"designed": 16, "final": 16, "missing": 0})        # 4 x 2 x 2
        self.assertEqual(self.res["missing_left_out"], study1b.NO_MISSING)                            # the one missing try is hm's
        for label, _ in study1b.MARGINS:
            self.assertEqual(self.res["confirmatory"][label]["completed"], {"B1": True, "B2": True, "B3": True})

    def test_d97_sensitivity_runs(self):
        sens = self.res["sensitivity_exposed_bases_excluded"]
        self.assertEqual(sens["label"], "sensitivity: exposed bases excluded")
        self.assertEqual(sens["bases_per_test"], {"B1": 2, "B2": 2, "B3": 2})        # 3 - 1 at 16; 4 - 2 at 6
        dep = sens["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["tests"]
        self.assertEqual({t: dep[t]["n"] for t in ("B1", "B2", "B3")}, {"B1": 2, "B2": 2, "B3": 2})

    def test_no_absolute_path_in_the_output(self):
        text = json.dumps(self.res, sort_keys=True, default=str)
        for absolute in (str(self.td), str(study1b.ROOT), "/private/", "/Users/", "/tmp/"):
            self.assertNotIn(absolute, text)

    def test_print_summary(self):
        """The compact summary Friday forwards: counts, cut arms, limits, k, the readings. No item text."""
        cut = self.r1["cut"]
        res = self.res
        dep = res["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["tests"]
        summary = {
            "trial_round_calls": self.r1["wave0"].answered,
            "test_calls_sent": sum(1 for c in self.sent if not c.startswith(TRIAL_PREFIX)),
            "records": res["records"],
            "cut": {"cap_usd": cut["cap_usd"], "limit_usd": cut["limit_usd"], "spent_usd": cut["spent_usd"],
                    "projected_without_cut_usd": cut["projected_without_cut_usd"], "projected_usd": cut["projected_usd"],
                    "still_over": cut["still_over"], "cut_arms": res["plan_as_run"]["cut"]["arms"],
                    "accepted": res["plan_as_run"]["cut"]["projection_accepted"]},
            "limits": {f"{a['tag']}@{a['steps']}": a["max_tokens"] for a in self.limits["arms"]},
            "manifest_check": {k: res["inputs"]["manifest_check"][k] for k in ("checked", "n_items")},
            "k": {k: self.kdoc[k] for k in ("k", "raw_k", "ratio", "capped", "label")},
            "b2_wording": res["costs_beside_tests"]["B2"]["wording"],
            "primary_as_deployed": {t: {"n": dep[t]["n"], "d": dep[t]["d"], "reading": dep[t]["reading"]} for t in ("B1", "B2", "B3")},
            "sensitivity_bases": res["sensitivity_exposed_bases_excluded"]["bases_per_test"],
            "cut_arms_in_section_6": sorted(k for k, v in res["descriptive"]["arms"].items() if v.get("status") == CUT),
        }
        print("\nJOINT RUN SUMMARY " + json.dumps(summary, sort_keys=True, default=str))
        self.assertEqual(summary["records"]["missing_rows"], 1)


def _family_readings(res: dict, part: str = "confirmatory") -> dict:
    """{(margin label, view, test): (reading, d, ci95, p)} of a driver output's family (or its D-97 sensitivity's)."""
    doc = res[part] if part == "confirmatory" else res["sensitivity_exposed_bases_excluded"]["confirmatory"]
    return {(label, v, t): (x["reading"], x["d"], None if x["ci95"] is None else list(x["ci95"]), x["p"])
            for label, c in doc.items() for v, fam in c["views"].items() for t, x in fam["tests"].items()}


class StoppedRuns(unittest.TestCase):
    """A1's three cases (Edith), plus a run stopped right after the confirmatory waves."""

    @classmethod
    def setUpClass(cls):
        _patch_ids(cls)
        sh = shared_fixture()
        cls.full = sh["full"]
        td, plan, path = sh["td"], sh["plan"], sh["plan_path"]

        def in_set(sid, tags=("hx", "om")):
            return lambda ids, done: any(i.startswith(sid + "-") and str(kscript.parse_custom_id(i)["setup"]) in tags for i in ids)

        def second_n6_batch(ids, done):                       # the first batch of hx/om at 6 goes, the second is refused
            n6 = [b for b in done.values() if b and b[0]["custom_id"].startswith(N6 + "-")]
            return in_set(N6)(ids, done) and len(n6) >= 1

        def descriptive(ids, done):
            return any(not i.startswith(TRIAL_PREFIX) and str(kscript.parse_custom_id(i)["setup"]) not in ("hx", "om") for i in ids)
        cls.never = joint_run(td, plan, path, "b3-never-sent", refuse=in_set(N6))
        cls.half = joint_run(td, plan, path, "b3-half-sent", refuse=second_n6_batch, max_wave_size=48)
        cls.errored = joint_run(td, plan, path, "hx16-errored", errored=ERRORED_HX)
        cls.conf_only = joint_run(td, plan, path, "confirmatory-only", refuse=descriptive)

    def held(self, case, tests):
        """`tests` read not completed (p = 1, no reading) in every view and margin, the sensitivity too; the others are unchanged."""
        res = case["res"]
        full = _family_readings(self.full["res"])
        for part in ("confirmatory", "sensitivity"):
            got = _family_readings(res, part)
            ref = _family_readings(self.full["res"], part)
            for key, (reading, d, ci, p) in got.items():
                if key[2] in tests:
                    self.assertEqual((reading, d, ci, p), (study1b.NOT_COMPLETED, None, None, 1.0), (part, key))
                else:
                    self.assertEqual((reading, d, ci, p), ref[key], (part, key))
        self.assertEqual(len(full), 2 * 3 * 3)
        for label, _ in study1b.MARGINS:
            c = res["confirmatory"][label]
            self.assertEqual(c["completed"], {t: t not in tests for t in ("B1", "B2", "B3")})
            for t in tests:
                arms = res["completeness"][t]["arms"]
                m, n = sum(a["missing"] for a in arms.values()), sum(a["designed"] for a in arms.values())
                self.assertEqual(c["template"][t], f"Test {t} was not completed: {m} of its {n} designed tries have no final record, "
                                                   "so we give it no reading.")
                self.assertFalse(c["headline_no_worse"][t])
                self.assertEqual(set(c["views"]["as_deployed"]["holm_thresholds"]), {"B1", "B2", "B3"})   # Holm place kept
                self.assertIn(t, c["views"]["as_deployed"]["not_completed"])
        for t in tests:
            self.assertFalse(res["completeness"][t]["completed"])
            self.assertEqual(res["completeness"][t]["reading"], study1b.NOT_COMPLETED)
            self.assertEqual(res["error_ratios"][t], {"reading": study1b.NOT_COMPLETED})
        self.assertEqual(sorted(res["sensitivity_exposed_bases_excluded"]["not_completed"]), sorted(tests))
        ex = res["missing_left_out"]                                                  # Edith L-1: the exclude-missing view
        if tests:
            for label, _ in study1b.MARGINS:
                fam = ex[label]["as_deployed"]
                main = res["confirmatory"][label]["views"]["as_deployed"]
                self.assertEqual(fam["holm_thresholds"], main["holm_thresholds"])
                for t in ("B1", "B2", "B3"):
                    if t in tests:                                                    # description only, never a reading
                        self.assertEqual(fam["tests"][t]["label"], study1b.NOT_COMPLETED_DESCRIPTIVE)
                        self.assertFalse({"reading", "declared", "p"} & set(fam["tests"][t]))
                    else:                                                             # a completed test EQUALS the main view
                        self.assertEqual(fam["tests"][t], main["tests"][t], (label, t))

    def test_i_b3_set_never_sent(self):
        self.assertEqual(self.never["r2"]["stopped"], "transport refused (test stop)")
        self.assertFalse([c for c in self.never["sent"] if c.startswith(N6 + "-")])
        self.held(self.never, ["B3"])
        comp = self.never["res"]["completeness"]["B3"]["arms"]
        self.assertEqual(comp["hx"], {"designed": 80, "final": 0, "missing": 80})                     # 4 bases x 2 forms x 10
        self.assertEqual(comp["om"], {"designed": 16, "final": 0, "missing": 16})
        ex = self.never["res"]["missing_left_out"]                                                     # the exclude-missing view
        self.assertEqual(ex["label"], study1b.EXCLUDE_MISSING_LABEL)
        self.assertEqual(ex["missing_left_out"]["B3"], {"hx": 80, "om": 16})
        dep = ex["primary_margin_5"]["as_deployed"]
        self.assertEqual((dep["tests"]["B3"]["n_base"], dep["tests"]["B3"]["d"], dep["tests"]["B3"]["bases_used"]), (0, None, []))
        self.assertEqual((dep["not_completed"], dep["not_run"]), (["B3"], []))                       # its Holm place, not "not run"
        full = self.full["res"]["confirmatory"]["primary_margin_5"]["views"]["as_deployed"]["tests"]
        self.assertEqual(dep["tests"]["B1"], full["B1"])                                              # B1: nothing missing, as the full run

    def test_ii_half_of_b3_set_sent(self):
        n6 = [c for c in self.half["sent"] if c.startswith(N6 + "-")]
        self.assertEqual(len(n6), 48)                                                                  # one batch of 48 of the 96
        self.held(self.half, ["B3"])
        comp = self.half["res"]["completeness"]["B3"]["arms"]
        self.assertEqual(comp["hx"]["missing"] + comp["om"]["missing"], 48)
        self.assertEqual(comp["hx"]["final"] + comp["om"]["final"], 48)
        ex = self.half["res"]["missing_left_out"]
        self.assertEqual(ex["bases_per_test"]["B3"], 2)                                                # the two bases sent
        b3 = ex["primary_margin_5"]["as_deployed"]["tests"]["B3"]
        self.assertEqual((b3["label"], b3["n_base"], len(b3["bases_used"])), (study1b.NOT_COMPLETED_DESCRIPTIVE, 2, 2))
        self.assertIsNotNone(b3["d"])                                                                  # numbers on the half sent,
        self.assertNotIn("reading", b3)                                                                # never a reading
        self.assertEqual(self.half["res"]["per_form"]["B3"]["label"], study1b.NOT_COMPLETED_DESCRIPTIVE)
        self.assertEqual(self.half["res"]["per_form"]["B3"]["6x1"]["d"]["n_base"], 2)                  # final tries only

    def test_iii_one_errored_try_never_sent_again(self):
        self.assertEqual(self.errored["r2"]["stopped"], "confirmatory_incomplete")                    # no descriptive arm went
        self.assertEqual(sum(ids.count(ERRORED_HX) for ids in self.errored["batches"]), 1)            # sent once, errored, not again
        self.assertFalse([c for c in self.errored["sent"] if not c.startswith(TRIAL_PREFIX)
                          and str(kscript.parse_custom_id(c)["setup"]) not in ("hx", "om")])
        self.held(self.errored, ["B1", "B2"])                                                          # B1 and B2 together
        comp = self.errored["res"]["completeness"]
        self.assertEqual(comp["B1"]["arms"]["hx"], {"designed": 60, "final": 59, "missing": 1})
        self.assertEqual(comp["B1"]["arms"], comp["B2"]["arms"])
        ex = self.errored["res"]["missing_left_out"]
        self.assertEqual(ex["missing_left_out"]["B1"], {"hx": 1, "om": 0})
        self.assertEqual(ex["primary_margin_5"]["as_deployed"]["tests"]["B1"]["n_base"], 3)          # all 3 bases, their final tries
        res, full = self.errored["res"]["descriptive"], self.full["res"]["descriptive"]                # §6 (C1)
        arms = res["arms"]
        for key, counts in (("hx@16", (60, 59, 1)), ("om@16", (12, 12, 0))):                         # N = 16 held: final tries only
            self.assertEqual(arms[key]["label"], HELD, key)
            self.assertEqual((arms[key]["designed"], arms[key]["final"], arms[key]["missing"]), counts)
        self.assertEqual(arms["hx@16"]["1x16"]["missing"], 0)
        self.assertEqual(arms["hx@16"]["16x1"]["missing"], 1)
        self.assertEqual(arms["om@16"]["pooled"]["mean"], full["arms"]["om@16"]["pooled"]["mean"])    # om: nothing missing
        self.assertNotEqual(arms["hx@16"]["16x1"]["mean"], full["arms"]["hx@16"]["16x1"]["mean"])     # hx: base 002 on 9 tries
        for key in ("hx@6", "om@6"):                                                                   # B3 complete: as the full run
            self.assertEqual(arms[key], full["arms"][key], key)
        self.assert_not_sent(res, full)
        vc = res["vote_curve_n16"]
        self.assertEqual(vc["label"], HELD)
        self.assertEqual(vc["tries"]["pooled"], {"designed": 60, "final": 59, "missing": 1})
        self.assertEqual([p["k"] for p in vc["points"]], list(range(1, 11)))
        self.assertEqual(vc["points"][0]["1x16"]["mean"], full["vote_curve_n16"]["points"][0]["1x16"]["mean"])   # chain: no missing
        fig = {p["tag"]: p for p in res["effort_figure"]["N=16"]["haiku"]}
        self.assertEqual((fig["hx"]["label"], fig["hx"]["missing"]), (HELD, 1))
        lc = res["length_curve"]
        self.assertEqual((lc["haiku-max"]["16"]["label"], lc["opus-medium"]["16"]["label"]), (HELD, HELD))
        self.assertNotIn("label", lc["haiku-max"]["6"])
        self.assertEqual(lc["haiku-max"]["12"], {"status": CUT})

    def assert_not_sent(self, res, full):
        """Every descriptive arm the §7 cut kept reads "not sent (run stopped)" with its counts (designed = missing), no accuracy and
        never 0%, in the arm blocks, the effort figure and the length curve; the cut arms stay "cut by §7 (cost)"."""
        arms = res["arms"]
        desc = [k for k, a in arms.items() if k.split("@")[0] not in ("hx", "om") and a.get("status") != CUT]
        self.assertEqual(sorted(desc), sorted(k for k, a in full["arms"].items()
                                              if k.split("@")[0] not in ("hx", "om") and a.get("status") != CUT))
        self.assertIn("hm@16", desc)
        for key in desc:
            a = arms[key]
            self.assertEqual(a["status"], NOT_SENT, key)
            self.assertEqual((a["final"], a["missing"]), (0, a["designed"]), key)
            self.assertGreater(a["designed"], 0)
            self.assertNotIn("mean", json.dumps(a), key)                                               # no accuracy anywhere
            for panel in ("pooled",) + tuple(k for k in a if k[0].isdigit()):
                self.assertEqual(a[panel]["status"], NOT_SENT, (key, panel))
        self.assertEqual((arms["hm@16"]["designed"], arms["hm@16"]["16x1"]["designed"]), (30, 15))
        for model_pts in list(res["effort_figure"]["N=6"].values()) + list(res["effort_figure"]["N=16"].values()):
            for p in model_pts:
                if p["tag"] in ("hx", "om") or p.get("status") == CUT:
                    continue
                self.assertEqual(p["status"], NOT_SENT, p["arm"])
                self.assertNotIn("pooled", p)
                self.assertEqual(p["missing"], p["designed"])
        self.assertEqual(res["length_curve"]["haiku-medium"]["16"]["status"], NOT_SENT)
        for k, a in arms.items():
            if a.get("status") == CUT:
                self.assertEqual(a, full["arms"][k])

    def test_iv_stopped_after_the_confirmatory_waves(self):
        self.assertEqual(self.conf_only["r2"]["stopped"], "transport refused (test stop)")
        self.held(self.conf_only, [])                                                                  # B1-B3 all completed
        self.assertEqual(self.conf_only["res"]["missing_left_out"], study1b.NO_MISSING)
        res, full = self.conf_only["res"]["descriptive"], self.full["res"]["descriptive"]
        arms = res["arms"]
        self.assertEqual(arms["hm@16"]["16x1"]["missing"], 15)                                         # never sent: all missing,
        self.assertEqual(arms["hm@16"]["16x1"]["status"], NOT_SENT)                                     # "not sent", never 0%
        self.assertEqual(self.conf_only["kdoc"]["k"], self.full["kdoc"]["k"])
        self.assert_not_sent(res, full)                                                                 # §6 (C1)
        for key in ("hx@16", "om@16", "hx@6", "om@6"):                                                  # complete: as the full run
            self.assertEqual(arms[key], full["arms"][key], key)
            self.assertNotIn("label", arms[key])
        self.assertEqual(res["vote_curve_n16"], full["vote_curve_n16"])
        self.assertNotIn("label", res["vote_curve_n16"])
        fig16 = {p["tag"]: p for p in res["effort_figure"]["N=16"]["haiku"]}
        full16 = {p["tag"]: p for p in full["effort_figure"]["N=16"]["haiku"]}
        self.assertEqual(fig16["hx"], full16["hx"])
        self.assertEqual(fig16["hm"], {"arm": "hm@16", "tag": "hm", "effort": "medium", "designed": 30, "final": 0, "missing": 30,
                                       "status": NOT_SENT})
        lc, flc = res["length_curve"], full["length_curve"]
        for name, n in (("haiku-max", "16"), ("haiku-max", "6"), ("opus-medium", "16"), ("opus-medium", "6")):
            self.assertEqual(lc[name][n], flc[name][n], (name, n))


def floors_of(plan):
    return [(s["steps"], a["tag"]) for s in plan["sets"] for a in s["arms"] if "calibrate" in a]


if __name__ == "__main__":
    unittest.main()
