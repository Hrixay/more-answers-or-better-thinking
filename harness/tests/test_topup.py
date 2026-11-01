"""The top-up runner (harness/pareto/topup.py; D-99, D-100, research/topup-run-spec.md): the plan file, the tags and custom ids, the
approved prompts (team_prompts.py by file hash), E2's rounds (lead-by-2, cap 9, "(no result)", plan_failed) rebuilt from the call log,
H-pick8 from a FIXTURE main-run log, C13 through e3.py at pieces, the same-model check at hm's exact params in round 1, the booking, a
full dry run, crash resume and the 2% pause. Offline only: small frozen sets in temp folders, DryTransport / FakeTransport, never live,
never data/raw."""

import contextlib
import copy
import csv
import hashlib
import io
import json
import re
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path
from unittest import mock

import atexit as _atexit
import shutil as _shutil

from harness.analysis import scoring
from harness.analysis.curve import _puzzle
from harness.analysis.kscript import parse_custom_id
from harness.pareto import e3, main, slim, topup
from harness.pareto.batch import PausedForTruncation
from harness.pareto.calllog import CallLog
from harness.pareto.pilot import HAIKU, SETUPS as PILOT_SETUPS, load_set
from harness.pareto.prices import estimate_input_tokens, worst_case
from harness.pareto.request import prompt_text
from harness.pareto.topup import MainRunJoinError, PlanError
from harness.pareto.transport import DryTransport, FakeTransport, TransportError
from harness.taskgen import freeze, ledger
from harness.tests.fakes import guard, reply
from harness.tests.test_resume import FlakyTransport

SID = "tutest-ledger-l14n6-v1"
MAIN_RUN_ID = "main-fixture"
N_BASE = 3
# The approved team_prompts.py (D-100) as on origin/main 71c6fd1 when this runner was written.
D100_SHA256 = "14d122c73d3343d0344a20d83f779b2627b5397d1def6b8df923b5c35b4bb498"


def _tmpdir() -> Path:
    """A temp folder removed when the test process exits: these tests write nowhere else."""
    d = Path(tempfile.mkdtemp(prefix="pareto-test-"))
    _atexit.register(_shutil.rmtree, d, True)
    return d


_ROOT = None


def fixture_root() -> Path:
    """One small frozen l14n6 set (3 base puzzles, both shapes) and a fixture main-run log, written once per test process."""
    global _ROOT
    if _ROOT is None:
        _ROOT = _tmpdir()
        freeze.write_set(_ROOT / SID, "ledger", "l14n6", SID, N_BASE, "d31", "scratch")
        write_main_log(_ROOT / "main-run", load_set(_ROOT / SID)[1])
    return _ROOT


def sample_text(item_id, s):
    return f"  Fixture reply {s} for {item_id}\nAnswer: 1 = [1, 2, 3]  "


def write_main_log(folder: Path, items, skip=(), run_id=MAIN_RUN_ID):
    """A fake main-run call log: hm samples 1..10 per item (9 and 10 must be ignored), one errored attempt before a final one, one
    refusal (pieces 000, sample 3) and one truncation (chain 000, sample 5)."""
    log = CallLog(folder / "calls.jsonl")
    for it in items:
        for s in range(1, 11):
            if (it["id"], s) in skip:
                continue
            cid = f"{it['id']}-hm-{s:02d}"
            base = {"custom_id": cid, "run_id": run_id, "requested_model": HAIKU, "effort": "medium",
                    "meta": {"setup": "hm", "sample": s, "item_id": it["id"]}}
            if s == 2:
                log.write(dict(base, final=False, kind="error", error={"type": "errored"}))
            kind, text = "answered", sample_text(it["id"], s)
            if it["base_index"] == 0 and it["width"] > 1 and s == 3:
                kind, text = "refusal", ""
            if it["base_index"] == 0 and it["width"] == 1 and s == 5:
                kind, text = "truncated", "Step 1 was"
            log.write(dict(base, final=True, kind=kind, answer_text=text))
    return folder


def sha(name):
    return json.loads((fixture_root() / name / "manifest.json").read_text())["items_sha256"]


def test_plan():
    p = json.loads((Path(topup.ROOT) / "data" / "plans" / "topup-plan.json").read_text())
    p.update(set={"set": str(fixture_root() / SID), "items_sha256": sha(SID), "steps": 6}, draft="test plan",
             main_run={"run_id": MAIN_RUN_ID, "setup": "hm"}, same_model={"bases": 2, "tries": 5, "mirrors": "hm"})
    return p


def the_set():
    return load_set(fixture_root() / SID)


def main_dir():
    return fixture_root() / "main-run"


def chains_and_pieces():
    _, items = the_set()
    by = sorted(items, key=lambda it: (it["base_index"], it["width"]))
    return [it for it in by if it["width"] == 1], [it for it in by if it["width"] > 1]


def run(plan, t, out, g=None, **kw):
    return topup.run_topup(g or guard(run_cap="100"), t, out, plan, main_dir(), sleep=lambda s: None, **kw)


def records(out):
    return list(CallLog(Path(out) / "calls.jsonl").records())


def sent(t):
    return [(bid, r["custom_id"], r["params"]) for bid, reqs in t.batches.items() for r in reqs]


def answer(state):
    return f"Answer: {ledger.fmt(list(state))}"


def wrong(state, by=1):
    return [state[0] + by] + list(state[1:])


class Script:
    """Scripted replies by custom id (both shapes, 3 base puzzles):
    - chain 0: task 2 draws 1 right, 2 wrong (1-1), then 3 and 4 right (3-1): decided right in 4 draws;
    - chain 1: task 3 never agrees (two wrong answers alternate, draw 9 does not parse): no result at the cap, so tasks 4-6 are never
      started and the aggregator sees "(no result)" from place 3 on;
    - chain 2: the plan lacks Task 2: plan_failed, nothing more for that puzzle;
    - pieces 0: the plan uses `## Task k` headings on their own lines (Edith R1-1);
    - pieces 1: task 4 never agrees: "(no result)" at place 4 only;
    - every other helper and every C13 step is right; aggregators, pickers and the same-model check answer something."""

    def __init__(self):
        self.chains, self.pieces = chains_and_pieces()
        self.items = {it["id"]: it for it in self.chains + self.pieces}

    def truth(self, it, k):
        return it["chains"][0]["states"][k - 1] if it["width"] == 1 else it["chains"][k - 1]["states"][0]

    def text(self, cid, params):
        c = parse_custom_id(cid)
        it, tag, sample = self.items[c["puzzle"]], c["setup"], c["sample"]
        if tag == "tp":
            if it is self.chains[2]:
                return "Task 1: a\nTask 3: c\nTask 4: d\nTask 5: e\nTask 6: f"
            if it is self.pieces[0]:
                return "\n".join(f"## Task {k}\nInstruction {k} for this piece." for k in range(1, 7))
            return "Here is the plan.\n" + "\n".join(f"Task {k}: Instruction number {k}." for k in range(1, 7))
        if tag in ("th", "es"):
            k, d = sample // 100, sample % 100
            right = self.truth(it, k)
            if tag == "th" and it is self.chains[0] and k == 2 and d == 2:
                return answer(wrong(right))
            if tag == "th" and ((it is self.chains[1] and k == 3) or (it is self.pieces[1] and k == 4)):
                return "no answer line" if d == 9 else answer(wrong(right, 1 if d % 2 else 2))
            return answer(right)
        if tag == "pk":
            return "I compared them.\nPick: 3"
        return "Answer: 1 = [1, 2, 3]"

    def batch_reply(self, cid, params):
        return {"type": "succeeded", "message": reply(model=HAIKU, text=self.text(cid, params), tout=200)}

    def reply_fn(self, params):                       # FlakyTransport's per-params form is not used: batch_reply is set
        raise AssertionError("batch_reply is set")


class Validation(unittest.TestCase):
    def bad(self, mutate):
        p = test_plan()
        mutate(p)
        with self.assertRaises(PlanError):
            topup.validate_plan(p)

    def test_the_real_plan_and_the_test_plan_pass(self):
        real = topup.read_plan(Path(topup.ROOT) / "data" / "plans" / "topup-plan.json")
        self.assertEqual((real["set"]["set"], real["main_run"]["run_id"], real["max_tokens"]), ("data/tasks/main-ledger-l14n6-v1", "main-l14n6-1", 48000))
        self.assertEqual(real["same_model"], {"bases": 20, "tries": 5, "mirrors": "hm",
                                              "note": real["same_model"]["note"]})
        self.assertEqual(real["window"]["not_before_utc"], "2026-10-14T13:01:00+00:00")       # D-99: after the main run's window
        self.assertEqual(real["parts"], ["same_model", "h_pick8", "e2", "c13"])
        self.assertFalse(real.get("draft"))                                                     # final: frozen in lock 4
        self.assertEqual((real["window"]["latest_first_round_utc"], real["window"]["stop_and_report_utc"]),
                         ("2026-10-16T23:59:00+00:00", "2026-10-18T23:59:00+00:00"))             # Jarvis, checklist section 4
        self.assertNotIn("TO CONFIRM", json.dumps(real))
        topup.validate_plan(test_plan())

    def test_the_spec_values_are_tied_to_the_code(self):
        self.bad(lambda p: p.update(model="claude-sonnet-5-5"))
        self.bad(lambda p: p.update(effort="high"))
        self.bad(lambda p: p.update(max_tokens=5000))
        self.bad(lambda p: p.update(voting={"lead": 3, "cap": 9, "first_round_draws": 2}))
        self.bad(lambda p: p.update(voting={"lead": 2, "cap": 7, "first_round_draws": 2}))
        self.bad(lambda p: p["same_model"].update(mirrors="hl"))
        self.bad(lambda p: p["main_run"].update(setup="hl"))
        self.bad(lambda p: p["same_model"].update(tries=0))
        self.bad(lambda p: p.update(parts=["e2", "e2"]))
        self.bad(lambda p: p.update(parts=["e1"]))
        self.bad(lambda p: p.update(parts=[]))
        self.bad(lambda p: p.update(surprise=1))
        self.bad(lambda p: p["set"].update(items_sha256="abc"))
        self.bad(lambda p: p["window"].update(not_before_utc="2026-10-14T13:01:00"))           # no offset
        self.bad(lambda p: p["window"].update(stop_and_report_utc="2026-10-13T00:00:00+00:00"))  # before not_before
        self.bad(lambda p: p.update(max_rounds=0))
        self.bad(lambda p: p.pop("run_id_prefix"))

    def test_the_set_is_checked_against_the_plan(self):
        p = test_plan()
        topup.load_topup_set(p)
        p["set"]["items_sha256"] = "0" * 64
        with self.assertRaises(PlanError):
            topup.load_topup_set(p)
        p = test_plan()
        p["set"]["steps"] = 12
        with self.assertRaises(PlanError):
            topup.load_topup_set(p)

    def test_start_check(self):
        from datetime import datetime
        p = topup.read_plan(Path(topup.ROOT) / "data" / "plans" / "topup-plan.json")
        t = lambda s: datetime.fromisoformat(s)
        with self.assertRaises(RuntimeError):
            topup.start_check(p, t("2026-10-14T13:00:59+00:00"), False)                       # the main run's window is still open
        topup.start_check(p, t("2026-10-14T13:01:00+00:00"), False)
        with self.assertRaises(RuntimeError):
            topup.start_check(p, t("2026-10-17T00:00:00+00:00"), False)                       # no first round after the latest date
        topup.start_check(p, t("2026-10-17T00:00:00+00:00"), True)                            # a resume may go on
        with self.assertRaises(RuntimeError):
            topup.start_check(p, t("2026-10-19T00:00:00+00:00"), True)                        # past stop-and-report


class ApprovedWording(unittest.TestCase):
    def test_team_prompts_is_the_d100_file(self):
        got = hashlib.sha256(topup.TEAM_PROMPTS_PATH.read_bytes()).hexdigest()
        self.assertEqual(topup.TEAM_PROMPTS_SHA256, D100_SHA256)
        self.assertEqual(got, D100_SHA256, "research/models/team_prompts.py changed: the wording needs a new ruling (D-100)")

    def test_a_changed_file_refuses_to_load(self):
        bad = _tmpdir() / "team_prompts.py"
        bad.write_bytes(topup.TEAM_PROMPTS_PATH.read_bytes().replace(b"Follow the instruction", b"Follow  the instruction"))
        with mock.patch.object(topup, "TEAM_PROMPTS_PATH", bad), mock.patch.object(topup, "_TP", None):
            with self.assertRaises(RuntimeError):
                topup.team_prompts()

    def test_every_prompt_is_the_template_byte_for_byte(self):
        tp = topup.team_prompts()
        self.assertIs(tp.parse_plan, topup.team_prompts().parse_plan)                     # one module, loaded once
        man, items = the_set()
        for it in items:
            n = 6
            self.assertEqual(topup.planner_item(man, it)[1]["messages"][0]["content"], tp.planner_prompt(it))
            res = [list(s) for s in (it["chains"][0]["states"] if it["width"] == 1 else [c["states"][0] for c in it["chains"]])]
            res[2] = None
            self.assertEqual(topup.aggregator_item(man, it, res)[1]["messages"][0]["content"], tp.aggregator_prompt(it, res))
            self.assertIn("(no result)", tp.aggregator_prompt(it, res))
            h = topup.helper_item(man, it, 2, 1, "Do the thing.", [5, 6, 7])
            self.assertEqual(h[1]["messages"][0]["content"], tp.helper_prompt("Do the thing.", [5, 6, 7]))
            replies = ["r1", None, "", "r4", "r5", "r6", "r7", "r8"]
            self.assertEqual(topup.picker_item(man, it, replies)[1]["messages"][0]["content"], tp.picker_prompt(it, replies))
            self.assertEqual(tp.picker_prompt(it, replies).count("(no reply)"), 2)
            self.assertEqual(n, topup._n_tasks(it))

    def test_the_r1_parsers_are_the_ones_used(self):
        tp = topup.team_prompts()
        self.assertEqual(tp.parse_plan("## Task 1\nApply E.\n## Task 2\nApply C.", 2), ["Apply E.", "Apply C."])     # R1-1
        self.assertEqual(tp.parse_plan("Task 1 - a\nTask 2 — b", 2), ["a", "b"])
        self.assertIsNone(tp.parse_plan("Task 1: a\nTask 3: c", 2))
        self.assertEqual(tp.parse_pick("Pick: Reply 5,"), 5)                                                       # R1-2
        self.assertIsNone(tp.parse_pick("Pick: 9"))


class Tags(unittest.TestCase):
    def used_tags(self):
        used = set(main.BY_NAME) | {"rt" + n for n, _ in main.RT_SETUPS} | {e3.SETUP_TAG} | set(slim.RESERVED_TAGS)
        used |= {su.name for v in PILOT_SETUPS.values() for su in v}
        study1b = json.loads((Path(slim.ROOT) / "data" / "plans" / "study1b-plan.json").read_text())
        used |= {a["tag"] for s in study1b["sets"] for a in s["arms"]}
        return used

    def test_new_tags_are_letters_distinct_and_unused(self):
        self.assertEqual(len(set(topup.NEW_TAGS)), len(topup.NEW_TAGS))
        for t in topup.NEW_TAGS:
            self.assertRegex(t, r"^[a-z]+$")
            self.assertFalse(t.startswith("rt"))
            self.assertNotIn(t, self.used_tags())
        self.assertEqual(topup.TAG_C13, e3.SETUP_TAG)                                     # C13 is E3 itself, on the pieces items

    def test_every_custom_id_is_unique_parses_and_never_meets_a_main_e3_or_slim_id(self):
        man, items = the_set()
        plan = test_plan()
        ctx = topup.Context(plan, man, items, topup.main_run_replies(main_dir(), items, MAIN_RUN_ID))
        first = topup.plan_round(ctx, [])
        helpers = [topup.helper_item(man, it, k, d, "x", [1]) for it in items for k in range(1, 7) for d in range(1, 10)]
        aggs = [topup.aggregator_item(man, it, [None] * 6) for it in items]
        c13 = [e3.step_item(s, d) for s in ctx.steps for d in range(1, 10)]
        self.assertTrue({r[0] for r in first if r[2]["setup"] == "es"} <= {r[0] for r in c13})   # round 1 holds C13's first draws
        ours = [r[0] for r in first if r[2]["setup"] != "es"] + [r[0] for r in helpers + aggs + c13]
        self.assertEqual(len(ours), len(set(ours)))
        for cid in ours:
            self.assertLessEqual(len(cid), 64)
            self.assertRegex(cid, r"^[A-Za-z0-9_-]+$")
            c = parse_custom_id(cid)
            self.assertEqual(c["set_id"], SID)
        main_ids = {r[0] for r in main.build_main_requests(man, items, extras=main.EXTRAS, d42=True)}
        main_ids |= {r[0] for r in main.build_rt_requests(man, items)}
        main_e3 = {e3.step_item(s, d)[0] for s in e3.chain_steps([(man, items)]) for d in range(1, 10)}
        self.assertTrue(main_e3)
        self.assertFalse(set(ours) & (main_ids | main_e3))
        self.assertTrue(all(re.search(r"-6x1-es-\d{4}$", r[0]) for r in c13))             # C13's E3 ids are on pieces items only


class Puzzles(unittest.TestCase):
    def setUp(self):
        self.man, self.items = the_set()

    def test_same_model_params_equal_hm_field_by_field(self):
        hm = next(su for su in main.MAIN_SETUPS if su.name == "hm")
        sm = topup.same_model_items(test_plan(), self.man, self.items)
        self.assertEqual(len(sm), 2 * 2 * 5)                                              # 2 bases x 2 shapes x 5 tries
        by_id = {it["id"]: it for it in self.items}
        for cid, params, meta in sm:
            it = by_id[meta["item_id"]]
            _, want, want_meta = main._item(self.man, it, hm, "hm", meta["sample"])
            self.assertEqual(set(params), set(want))
            for f in want:
                self.assertEqual(params[f], want[f], f)
            self.assertEqual((params["max_tokens"], params["output_config"], params["thinking"], params["model"]),
                             (5000, {"effort": "medium"}, {"type": "adaptive"}, HAIKU))
            self.assertEqual(params["messages"], [{"role": "user", "content": it["prompt"]}])
            self.assertEqual(cid, f"{it['id']}-sc-{meta['sample']:02d}")
            self.assertEqual(meta["setup"], "sc")
            self.assertEqual({k: v for k, v in meta.items() if k not in ("setup", "phase", "role", "mirrors")},
                             {k: v for k, v in want_meta.items() if k != "setup"})
            self.assertLess(it["base_index"], 2)
        self.assertEqual(Counter(m["width"] for _, _, m in sm), {1: 10, 6: 10})

    def test_c13_uses_the_approved_step_call_for_each_piece(self):
        steps = topup.c13_steps(self.man, self.items)
        pieces = [it for it in self.items if it["width"] > 1]
        self.assertEqual(len(steps), len(pieces) * 6)
        for st in steps:
            it = next(i for i in pieces if i["id"] == st.item_id)
            p = ledger.generate(it["seed"], 6, 1, ledger.SETTINGS["l14n6"], item_id=it["id"], style="d31")
            prompt, truth = ledger.step_call(p, st.k, 1)
            self.assertEqual((st.prompt, st.truth, st.width, st.depth), (prompt, scoring.state_key(truth), 6, 1))
            self.assertEqual(st.truth, scoring.state_key(it["chains"][st.k - 1]["states"][0]))
            self.assertIn("Balances\n" + ledger.fmt(it["chains"][st.k - 1]["start"]) + "\n", st.prompt)   # from its printed start
            cid, params, meta = e3.step_item(st, 1)
            self.assertEqual((params["max_tokens"], params["model"], params["output_config"]), (48000, HAIKU, {"effort": "medium"}))
            self.assertEqual((meta["setup"], meta["step"], meta["width"]), ("es", st.k, 6))

    def test_c13_prompts_match_the_e3_wording_with_numbers_and_rules_masked(self):
        steps = topup.c13_steps(self.man, self.items)
        chain_steps = {(s.base_index, s.k): s for s in e3.chain_steps([(self.man, self.items)])}

        def mask(prompt, it, rule_label):
            p = _puzzle(it)
            rules = {lab: txt for lab, _, txt in p.rulebook}
            return re.sub(r"\d+", "#", prompt.replace(rules[rule_label], "<RULE>"))
        by_id = {it["id"]: it for it in self.items}
        for st in steps:
            it = by_id[st.item_id]
            chain_it = next(i for i in self.items if i["width"] == 1 and i["base_index"] == it["base_index"])
            ce = chain_steps[(it["base_index"], 1)]
            got = mask(st.prompt, it, _puzzle(it).chains[st.k - 1].names[0])
            want = mask(ce.prompt, chain_it, _puzzle(chain_it).chains[0].names[0])
            names_it, names_chain = _puzzle(it).line_names, _puzzle(chain_it).line_names
            for a, b in zip(names_it, names_chain):
                want = want.replace(b, "<NAME>")
                got = got.replace(a, "<NAME>")
            self.assertEqual(got, want)


class Picker(unittest.TestCase):
    def setUp(self):
        self.man, self.items = the_set()

    def test_the_prompt_is_built_from_samples_1_to_8_of_the_main_log(self):
        tp = topup.team_prompts()
        reps = topup.main_run_replies(main_dir(), self.items, MAIN_RUN_ID)
        self.assertEqual(set(reps), {it["id"] for it in self.items})
        for it in self.items:
            r = reps[it["id"]]
            self.assertEqual(len(r), 8)
            want = [sample_text(it["id"], s) for s in range(1, 9)]
            if it["base_index"] == 0:
                bad = 3 if it["width"] > 1 else 5
                want[bad - 1] = None                                                      # refused / truncated: "(no reply)"
            self.assertEqual(r, want)
            prompt = topup.picker_item(self.man, it, r)[1]["messages"][0]["content"]
            self.assertEqual(prompt, tp.picker_prompt(it, want))
            self.assertIn(f"Reply 1\nFixture reply 1 for {it['id']}\nAnswer: 1 = [1, 2, 3]\n\nReply 2", prompt)  # trimmed
            self.assertNotIn("Fixture reply 9", prompt)
            self.assertEqual(prompt.count("(no reply)"), 1 if it["base_index"] == 0 else 0)

    def test_a_missing_sample_stops_everything_clearly(self):
        # Edith's ruling 1 (spec 4c applied to the runner): every picker puzzle needs a FINAL main-run record for each of samples 1-8;
        # otherwise nothing at all is sent and the error names the missing ids. Here sample 7 of one puzzle exists only as an error.
        it = self.items[0]
        folder = write_main_log(_tmpdir(), self.items, skip={(it["id"], 7)})
        CallLog(folder / "calls.jsonl").write({"custom_id": f"{it['id']}-hm-07", "final": False, "kind": "error", "run_id": MAIN_RUN_ID})
        with self.assertRaises(MainRunJoinError) as e:
            topup.main_run_replies(folder, self.items, MAIN_RUN_ID)
        self.assertIn(f"{it['id']}-hm-07", str(e.exception))
        t = FakeTransport(batch_reply=Script().batch_reply)
        out = _tmpdir()
        with self.assertRaises(MainRunJoinError):
            topup.run_topup(guard(run_cap="100"), t, out, test_plan(), folder, sleep=lambda s: None)
        self.assertEqual(t.batches, {})
        self.assertEqual(list(out.iterdir()), [])                                         # not even the window started

    def test_a_record_of_another_run_or_setup_is_refused(self):
        with self.assertRaises(MainRunJoinError):
            topup.main_run_replies(main_dir(), self.items, "main-l14n6-1")               # the fixture is not that run
        with self.assertRaises(MainRunJoinError):
            topup.Context(test_plan(), self.man, self.items, None)                        # the picker needs the main run


class Rounds(unittest.TestCase):
    """The scripted fake run (Script): round contents, inputs rebuilt from the log, lead-by-2, cap 9, "(no result)", plan_failed."""

    @classmethod
    def setUpClass(cls):
        cls.script = Script()
        cls.out = _tmpdir()
        cls.t = FakeTransport(batch_reply=cls.script.batch_reply)
        cls.r = run(test_plan(), cls.t, cls.out)
        cls.recs = records(cls.out)
        cls.by_round = {}
        bids = list(cls.t.batches)
        # one Batch per round here (the cap is wide): batch i is round i
        for i, bid in enumerate(bids, 1):
            cls.by_round[i] = [(r["custom_id"], r["params"]) for r in cls.t.batches[bid]]
        cls.finals = {r["custom_id"]: r for r in cls.recs if r.get("final")}

    def tags(self, rnd):
        return Counter(parse_custom_id(c)["setup"] for c, _ in self.by_round[rnd])

    def test_it_ends_cleanly_and_no_id_is_sent_twice(self):
        self.assertIsNone(self.r["stopped"])
        ids = [c for _, c, _ in sent(self.t)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.r["rounds"], 9)
        self.assertEqual(len(self.by_round), 9)
        self.assertEqual([x["round"] for x in self.recs if x.get("kind") == "topup_round"], list(range(1, 10)))

    def test_round_1_holds_the_check_the_pickers_the_planners_and_c13s_first_draws(self):
        self.assertEqual(self.tags(1), {"sc": 20, "pk": 6, "tp": 6, "es": 3 * 6 * 2})
        sc = {c for c, _ in self.by_round[1] if parse_custom_id(c)["setup"] == "sc"}
        self.assertEqual(sc, {r[0] for r in topup.same_model_items(test_plan(), *the_set())})
        for r in range(2, 10):
            self.assertNotIn("sc", self.tags(r))
            self.assertNotIn("pk", self.tags(r))

    def test_round_2_holds_task_1_at_chain_and_all_tasks_at_pieces(self):
        ch, pc = self.script.chains, self.script.pieces
        self.assertEqual(self.tags(2), {"th": 2 * 2 + 3 * 6 * 2})                        # chain 2's plan failed
        got = {(parse_custom_id(c)["puzzle"], parse_custom_id(c)["sample"]) for c, _ in self.by_round[2]}
        self.assertEqual({x for x in got if x[0] in (ch[0]["id"], ch[1]["id"])},
                         {(ch[i]["id"], 100 + d) for i in (0, 1) for d in (1, 2)})

    def test_inputs_of_round_r_plus_1_come_from_round_r_s_log(self):
        tp = topup.team_prompts()
        ch = self.script.chains[0]
        plan_rec = self.finals[f"{ch['id']}-tp-01"]
        plan = tp.parse_plan(plan_rec["answer_text"], 6)
        self.assertEqual(plan[0], "Instruction number 1.")
        for k in range(1, 7):
            prev = ch["chains"][0]["start"] if k == 1 else topup._key_to_state(e3.decide(
                [e3.record_vote(self.finals[f"{ch['id']}-th-{k - 1:02d}{d:02d}"], 6)
                 for d in range(1, 10) if f"{ch['id']}-th-{k - 1:02d}{d:02d}" in self.finals])["answer"])
            p = self.finals[f"{ch['id']}-th-{k:02d}01"]
            sent_params = next(pp for _, c, pp in sent(self.t) if c == p["custom_id"])
            self.assertEqual(sent_params["messages"][0]["content"], tp.helper_prompt(plan[k - 1], prev))
        # pieces: every task from its own printed start, all in round 2
        pc = self.script.pieces[0]
        for k in range(1, 7):
            c = f"{pc['id']}-th-{k:02d}01"
            self.assertIn(c, [x for x, _ in self.by_round[2]])
            pp = next(pp for _, cc, pp in sent(self.t) if cc == c)
            self.assertTrue(pp["messages"][0]["content"].endswith("Balances\n" + ledger.fmt(pc["chains"][k - 1]["start"]) + "\n\n"
                                                                  + tp.HELPER_CLOSING))
            self.assertEqual(pp["messages"][0]["content"].split("\n\n")[0], f"Instruction {k} for this piece.")   # R1-1 headings

    def test_lead_by_2_stop_and_top_up(self):
        ch = self.script.chains[0]
        draws = sorted(c for c in self.finals if c.startswith(f"{ch['id']}-th-02"))
        self.assertEqual(draws, [f"{ch['id']}-th-02{d:02d}" for d in (1, 2, 3, 4)])     # 1-1, two more, 3-1: decided
        rounds = {c: r for r, xs in self.by_round.items() for c, _ in xs}
        self.assertEqual([rounds[d] for d in draws], [3, 3, 4, 4])
        self.assertEqual(sorted(c for c in self.finals if c.startswith(f"{ch['id']}-th-01")), [f"{ch['id']}-th-01{d:02d}" for d in (1, 2)])

    def test_cap_9_no_result_and_the_chain_stops_there(self):
        tp = topup.team_prompts()
        ch = self.script.chains[1]
        draws = sorted(c for c in self.finals if c.startswith(f"{ch['id']}-th-03"))
        self.assertEqual(len(draws), 9)
        self.assertFalse([c for c in self.finals if re.match(rf"{ch['id']}-th-0[456]", c)])  # never started
        agg = next(pp for _, c, pp in sent(self.t) if c == f"{ch['id']}-ta-01")
        st = ch["chains"][0]["states"]
        self.assertEqual(agg["messages"][0]["content"], tp.aggregator_prompt(ch, [list(st[0]), list(st[1]), None, None, None, None]))
        self.assertEqual(agg["messages"][0]["content"].count("(no result)"), 4)
        state = topup.e2_puzzle(*[the_set()[0], ch], self.finals)
        self.assertEqual(state["stage"], "done")
        self.assertEqual([t["status"] for t in state["tasks"]], ["done", "done", "done", "not_started", "not_started", "not_started"])
        self.assertTrue(state["tasks"][2]["at_cap"])

    def test_pieces_no_result_is_at_its_own_place_only(self):
        tp = topup.team_prompts()
        pc = self.script.pieces[1]
        agg = next(pp for _, c, pp in sent(self.t) if c == f"{pc['id']}-ta-01")
        res = [list(c["states"][0]) for c in pc["chains"]]
        res[3] = None
        self.assertEqual(agg["messages"][0]["content"], tp.aggregator_prompt(pc, res))
        self.assertEqual(len([c for c in self.finals if c.startswith(f"{pc['id']}-th-04")]), 9)

    def test_plan_failed_sends_nothing_more(self):
        ch = self.script.chains[2]
        mine = [c for _, c, _ in sent(self.t) if parse_custom_id(c)["puzzle"] == ch["id"] and parse_custom_id(c)["setup"] in ("th", "ta")]
        self.assertEqual(mine, [])
        self.assertEqual(topup.e2_puzzle(the_set()[0], ch, self.finals)["stage"], "plan_failed")

    def test_status_counts_and_the_compact_table(self):
        st = self.r["status"]
        self.assertEqual(st["same_model"], {"calls": 20, "final": 20})
        self.assertEqual(st["h_pick8"], {"puzzles": 6, "final": 6})
        self.assertEqual((st["e2"]["1x6"]["done"], st["e2"]["1x6"]["plan_failed"], st["e2"]["1x6"]["tasks_no_result"]), (2, 1, 1))
        self.assertEqual((st["e2"]["6x1"]["done"], st["e2"]["6x1"]["tasks_no_result"]), (3, 1))
        self.assertEqual((st["c13"]["steps"], st["c13"]["decided"], st["c13"]["open"]), (18, 18, 0))
        with open(self.out / "compact_table.csv") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), len(self.finals))
        for x in rows:
            tag = parse_custom_id(x["custom_id"])["setup"]
            self.assertEqual(x["right"] != "", tag in ("ta", "sc"), x["custom_id"])
        # C13 reads through e3.e3_rows unchanged: every piece right
        rows13 = e3.e3_rows([], self.recs, topup.c13_steps(*the_set()))
        self.assertEqual(len(rows13), 3)
        self.assertTrue(all(r["step_correct"] == [True] * 6 for r in rows13))

    def test_a_second_run_sends_nothing(self):
        t2 = FakeTransport(batch_reply=lambda c, p: (_ for _ in ()).throw(AssertionError("sent again")))
        r2 = run(test_plan(), t2, self.out)
        self.assertEqual((r2["rounds"], r2["calls_sent"], t2.batches), (0, 0, {}))


class Runs(unittest.TestCase):
    def test_full_dry_run(self):
        out = _tmpdir()
        r = run(test_plan(), DryTransport(), out)
        self.assertIsNone(r["stopped"])
        st = r["status"]
        self.assertEqual(st["e2"]["1x6"]["plan_failed"] + st["e2"]["6x1"]["plan_failed"], 6)   # "DRY RUN" is no plan
        self.assertEqual(st["c13"]["at_cap"], 18)                                              # "DRY RUN" votes for nothing
        self.assertEqual(r["rounds"], 5)                                                       # 2, +2, +2, +2, +1 draws
        self.assertIn("top-up run", (out / "manifest.json").read_text())
        self.assertTrue((out / "topup_plan.json").exists() and (out / "window.json").exists())

    def test_crash_mid_round_resume_sends_no_id_twice(self):
        for down_after in (1, 2, 4):
            out = _tmpdir()
            g = guard(run_cap="100")
            s = Script()
            t = FlakyTransport(s.reply_fn, down_after_submit=down_after)
            t.batch_reply = s.batch_reply
            with self.assertRaises(TransportError):
                run(test_plan(), t, out, g)
            t.down = False
            t.down_after_submit = None
            r = run(test_plan(), t, out, g)
            self.assertIsNone(r["stopped"], down_after)
            ids = [c for _, c, _ in sent(t)]
            self.assertEqual(len(ids), len(set(ids)), down_after)
            self.assertEqual(len(ids), len(CallLog(out / "calls.jsonl").finished_ids()))
            self.assertEqual(r["status"]["e2"]["1x6"]["done"], 2)

    def test_the_pause_trips_and_waits_for_the_user(self):
        out = _tmpdir()
        g = guard(run_cap="100")
        s = Script()

        def cut_sc(cid, params):
            if parse_custom_id(cid)["setup"] == "sc" and parse_custom_id(cid)["sample"] == 1:
                return {"type": "succeeded", "message": reply(model=HAIKU, text="Answer: [", stop="max_tokens", tout=5000)}
            return s.batch_reply(cid, params)
        r = run(test_plan(), FakeTransport(batch_reply=cut_sc), out, g)
        self.assertEqual(r["stopped"], "paused_for_truncation")
        self.assertEqual(r["rounds"], 1)
        self.assertEqual(r["summaries"][0].paused_for_truncation, {"sc": 0.2})               # 4 of 20 at max_tokens
        with self.assertRaises(PausedForTruncation):
            run(test_plan(), FakeTransport(batch_reply=s.batch_reply), out, g)
        t = FakeTransport(batch_reply=s.batch_reply)
        r = run(test_plan(), t, out, g, release_pause_note="the user: go on (test)")
        self.assertIsNone(r["stopped"])
        self.assertFalse([c for _, c, _ in sent(t) if parse_custom_id(c)["setup"] == "sc"])  # nothing re-sent
        self.assertTrue(any(x.get("kind") == "pause_released" for x in records(out)))

    def test_a_crash_while_writing_round_2s_results_resumes_with_the_same_items(self):
        # Edith code r1 T-R1: the run stops after 3 of round 2's results are logged (the 3rd committed in the guard, its log line not
        # written). Re-planned from the log as it is now, round 2 would leave out the ids already final and run_batches would refuse
        # ("mixes these items"); resumed, the round settles with the items it was planned with, and the run ends as a clean one does.
        real_write = CallLog.write
        writes = {"n": 0}

        def crashing_write(log_self, record):
            if record.get("final") and record.get("batch_id") == "fake-batch-2":
                writes["n"] += 1
                if writes["n"] == 3:
                    raise KeyboardInterrupt("crash while writing round 2's results")
            return real_write(log_self, record)
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()
        t = FakeTransport(batch_reply=s.batch_reply)
        with mock.patch.object(CallLog, "write", crashing_write), self.assertRaises(KeyboardInterrupt):
            run(test_plan(), t, out, g)
        recs = records(out)
        self.assertEqual(len([x for x in recs if x.get("final") and x.get("batch_id") == "fake-batch-2"]), 2)
        self.assertEqual(topup.round_lines(recs), (2, max(i for i, x in enumerate(recs) if x.get("kind") == "topup_round")))
        pending = topup.unsettled_ids(recs)
        self.assertEqual(pending, {r["custom_id"] for r in t.batches["fake-batch-2"]})
        ctx = topup.Context(test_plan(), *the_set(), topup.main_run_replies(main_dir(), the_set()[1], MAIN_RUN_ID))
        self.assertFalse(pending <= {r[0] for r in topup.plan_round(ctx, recs)})              # the r1 bug: re-planned, it differs
        r = run(test_plan(), t, out, g)
        self.assertIsNone(r["stopped"])
        ids = [c for _, c, _ in sent(t)]
        self.assertEqual(len(ids), len(set(ids)))                                             # no id sent twice
        self.assertEqual(len(t.batches), 9)                                                   # round 2 was never re-submitted
        recs = records(out)
        finals = [x["custom_id"] for x in recs if x.get("final")]
        self.assertEqual(len(finals), len(set(finals)))
        self.assertEqual(set(finals), set(ids))
        self.assertEqual([x["round"] for x in recs if x.get("kind") == "topup_round"], list(range(1, 10)))
        self.assertEqual([x["round"] for x in recs if x.get("kind") == "topup_round_done"], list(range(1, 10)))
        self.assertEqual((r["rounds"], r["rounds_logged"]), (8, 9))                          # round 2 resumed, then 3..9
        clean = run(test_plan(), FakeTransport(batch_reply=Script().batch_reply), _tmpdir())   # the same run with no crash
        self.assertEqual(r["status"], clean["status"])
        self.assertEqual(r["status"]["e2"]["1x6"]["done"], 2)
        self.assertEqual(g.reserved, 0)

    def test_a_crash_before_the_truncation_check_is_checked_before_the_next_round(self):
        # Edith code r1 T-R3: round 1 is collected, then the run stops before check_wave writes its line. The next start checks that
        # batch before planning anything: here 4 of 20 same-model calls hit max_tokens, so it pauses and sends nothing new.
        from harness.pareto import batch
        real_check = batch.check_wave
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()

        def cut_sc(cid, params):
            if parse_custom_id(cid)["setup"] == "sc" and parse_custom_id(cid)["sample"] == 1:
                return {"type": "succeeded", "message": reply(model=HAIKU, text="Answer: [", stop="max_tokens", tout=5000)}
            return s.batch_reply(cid, params)
        t = FakeTransport(batch_reply=cut_sc)
        with mock.patch.object(batch, "check_wave", side_effect=KeyboardInterrupt("crash before the check")), \
                self.assertRaises(KeyboardInterrupt):
            run(test_plan(), t, out, g)
        self.assertEqual(topup.unchecked_batches(records(out)), ["fake-batch-1"])
        calls = []
        with mock.patch.object(batch, "check_wave", side_effect=lambda *a, **k: calls.append(a[2]) or real_check(*a, **k)):
            r = run(test_plan(), t, out, g)
        self.assertEqual(calls, ["fake-batch-1"])                                             # checked once, by the pre-round check
        self.assertEqual((r["stopped"], r["paused"], r["rounds"]), ("paused_for_truncation", {"sc": 0.2}, 0))
        self.assertEqual(list(t.batches), ["fake-batch-1"])
        with self.assertRaises(PausedForTruncation):
            run(test_plan(), t, out, g)
        self.assertEqual(topup.unchecked_batches(records(out)), [])

    def test_max_rounds_counts_rounds_across_resumes(self):
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()
        t = FakeTransport(batch_reply=s.batch_reply)
        r = run(test_plan(), t, out, g, max_rounds=3)
        self.assertEqual((r["rounds"], r["rounds_logged"], r["stopped"]), (3, 3, "max_rounds"))
        r = run(test_plan(), t, out, g, max_rounds=3)
        self.assertEqual((r["rounds"], r["rounds_logged"], r["stopped"], len(t.batches)), (0, 3, "max_rounds", 3))
        r = run(test_plan(), t, out, g, max_rounds=5)
        self.assertEqual((r["rounds"], r["rounds_logged"], r["stopped"], len(t.batches)), (2, 5, "max_rounds", 5))
        r = run(test_plan(), t, out, g)
        self.assertEqual((r["rounds_logged"], r["stopped"]), (9, None))

    def test_a_different_plan_cannot_resume_a_run(self):
        out = _tmpdir()
        g = guard(run_cap="100")
        run(test_plan(), DryTransport(), out, g)
        p = test_plan()
        p["same_model"]["tries"] = 4
        with self.assertRaises(PlanError):
            run(p, DryTransport(), out, g)


class Clock:
    """A settable clock and a FakeTransport that moves it when the n-th batch is submitted (time passing during a run)."""

    def __init__(self, start):
        from datetime import datetime
        self.t = datetime.fromisoformat(start)

    def __call__(self):
        return self.t

    def transport(self, script, jumps, base=FakeTransport, **kw):
        clock = self

        class Moving(base):
            def submit_batch(self, requests):
                bid = super().submit_batch(requests)
                if len(self.batches) in jumps:
                    from datetime import datetime
                    clock.t = datetime.fromisoformat(jumps[len(self.batches)])
                return bid
        t = Moving(**kw) if kw else Moving(batch_reply=script.batch_reply)
        if kw:
            t.batch_reply = script.batch_reply
        return t


class EveryRound(unittest.TestCase):
    """Edith code r1 T-R2: the 48-hour window and the plan's dates are checked before EVERY round, not only at the start."""

    def plan(self, hours=48):
        p = test_plan()
        p["window"].update(hours=hours, not_before_utc="2026-10-14T13:01:00+00:00", latest_first_round_utc="2026-10-16T23:59:00+00:00",
                           stop_and_report_utc="2026-10-18T23:59:00+00:00")
        return p

    def test_the_48_hour_window_ends_mid_run(self):
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()
        clock = Clock("2026-10-15T00:00:00+00:00")
        t = clock.transport(s, {2: "2026-10-17T00:00:01+00:00"})                     # 48 h and 1 s after the first start
        r = run(self.plan(), t, out, g, now=clock)
        self.assertEqual((r["stopped"], r["rounds"], len(t.batches)), ("refused", 2, 2))
        self.assertIn("window ended", r["refused"])
        recs = records(out)
        self.assertEqual([x["round"] for x in recs if x.get("kind") == "topup_round"], [1, 2])
        self.assertEqual(topup.unsettled_ids(recs), set())
        r = run(self.plan(), t, out, g, now=clock)                                     # the same command: still refused, nothing sent
        self.assertEqual((r["stopped"], r["rounds"], len(t.batches)), ("refused", 0, 2))
        r = run(self.plan(), t, out, g, now=clock, extension_note="the user: extend by a day (test)")   # D-45
        self.assertEqual((r["stopped"], len(t.batches)), (None, 9))
        self.assertTrue(json.loads((out / "window.json").read_text())["extensions"])

    def test_the_stop_and_report_date_is_checked_before_each_round(self):
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()
        clock = Clock("2026-10-16T23:00:00+00:00")
        t = clock.transport(s, {3: "2026-10-19T00:00:00+00:00"})
        r = run(self.plan(hours=500), t, out, g, now=clock, check_dates=True)
        self.assertEqual((r["stopped"], r["rounds"], len(t.batches)), ("refused", 3, 3))
        self.assertIn("stop-and-report", r["refused"])
        self.assertEqual(topup.round_lines(records(out))[0], 3)

    def test_a_late_round_after_latest_first_round_is_allowed_but_not_a_late_first_round(self):
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()
        clock = Clock("2026-10-16T23:00:00+00:00")
        t = clock.transport(s, {1: "2026-10-17T06:00:00+00:00"})                     # rounds 2.. fall after latest_first_round
        r = run(self.plan(hours=500), t, out, g, now=clock, check_dates=True)
        self.assertEqual((r["stopped"], len(t.batches)), (None, 9))
        for start in ("2026-10-14T13:00:00+00:00", "2026-10-17T00:00:00+00:00"):      # before not_before; a first round too late
            out, t = _tmpdir(), FakeTransport(batch_reply=s.batch_reply)
            r = run(self.plan(hours=500), t, out, guard(run_cap="100"), now=Clock(start), check_dates=True)
            self.assertEqual((r["stopped"], r["rounds"], t.batches), ("refused", 0, {}), start)

    def test_a_round_caught_by_a_crash_past_the_window_is_collected_and_nothing_new_is_sent(self):
        out, g, s = _tmpdir(), guard(run_cap="100"), Script()
        clock = Clock("2026-10-15T00:00:00+00:00")
        t = clock.transport(s, {2: "2026-10-17T01:00:00+00:00"}, base=FlakyTransport, reply_fn=s.reply_fn, down_after_submit=2)
        with self.assertRaises(TransportError):
            run(self.plan(), t, out, g, now=clock)                                      # round 2's batch is sent, never collected
        self.assertTrue(topup.unsettled_ids(records(out)))
        t.down, t.down_after_submit = False, None
        r = run(self.plan(), t, out, g, now=clock)
        self.assertEqual((r["stopped"], len(t.batches)), ("refused", 2))
        self.assertEqual(topup.unsettled_ids(records(out)), set())                     # collected: a read, never a re-send
        self.assertEqual(len(CallLog(out / "calls.jsonl").finished_ids()), sum(len(v) for v in t.batches.values()))


class Booking(unittest.TestCase):
    def test_calls_and_booking_per_part(self):
        man, items = the_set()
        reps = topup.main_run_replies(main_dir(), items, MAIN_RUN_ID)
        out = topup.topup_plan(guard(run_cap="25"), test_plan(), man, items, reps)
        parts = out["parts"]
        self.assertEqual({k: v["calls"] for k, v in parts.items()},
                         {"same_model": 20, "h_pick8": 6, "e2_planner": 6, "e2_helpers_at_cap": 6 * 6 * 9, "e2_aggregator": 6,
                          "c13_at_cap": 3 * 6 * 9})
        self.assertEqual(parts["e2_helpers_at_cap"]["per_shape"], {"1x6": 162, "6x1": 162})
        self.assertEqual(out["round_1"]["calls"], 20 + 6 + 6 + 36)
        self.assertEqual(out["total_calls_at_worst_case"], sum(v["calls"] for v in parts.values()))
        sm = topup.same_model_items(test_plan(), man, items)
        want = sum((worst_case(HAIKU, estimate_input_tokens(prompt_text(p)), 5000, batch=True) for _, p, _ in sm), Decimal(0))
        self.assertEqual(Decimal(parts["same_model"]["batch_booking_usd"]), want)
        self.assertEqual((parts["same_model"]["max_tokens"], parts["e2_planner"]["max_tokens"], parts["c13_at_cap"]["max_tokens"]),
                         (5000, 48000, 48000))
        self.assertEqual(Decimal(out["total_batch_booking_at_worst_case_usd"]),
                         sum(Decimal(v["batch_booking_usd"]) for v in parts.values()))
        no_main = topup.topup_plan(guard(run_cap="25"), test_plan(), man, items, None)          # stand-in replies
        self.assertIn("stand-in", no_main["parts"]["h_pick8"]["basis"])
        self.assertGreater(Decimal(no_main["parts"]["h_pick8"]["batch_booking_usd"]), Decimal(parts["h_pick8"]["batch_booking_usd"]))


class Cli(unittest.TestCase):
    def call(self, argv, plan=None):
        f = _tmpdir() / "plan.json"
        f.write_text(json.dumps(plan or test_plan()))
        out = io.StringIO()
        with mock.patch("harness.pareto.live.open_live_guard", side_effect=AssertionError("no live guard in tests")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = topup.main([argv[0], "--plan", str(f)] + argv[1:])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()

    def test_plan_prints_the_booking(self):
        code, out = self.call(["plan", "--cap", "25", "--main-run", str(main_dir())])
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["round_1"]["calls"], 68)
        self.assertNotIn("Fixture reply", out)                                               # no text is printed

    def test_dry_needs_out_and_the_main_run(self):
        self.assertEqual(self.call(["dry", "--run-id", "x"])[0], 2)

    def test_a_missing_main_run_sample_is_a_clean_refusal(self):
        # Edith's ruling 1, through the command: "REFUSED: ..." and exit 2, never a traceback; nothing is planned or written
        _, items = the_set()
        folder = write_main_log(_tmpdir(), items, skip={(items[0]["id"], 4)})
        out = _tmpdir() / "run"
        for argv in (["plan", "--main-run", str(folder)], ["dry", "--run-id", "x", "--out", str(out), "--main-run", str(folder)]):
            code, text = self.call(argv)
            self.assertEqual(code, 2, argv)
            self.assertTrue(text.startswith("REFUSED: "), text[:80])
            self.assertIn(f"{items[0]['id']}-hm-04", text)
        self.assertFalse(out.exists())

    def test_live_refusals(self):
        p = test_plan()
        for argv in (["live", "--run-id", "topup-1"], ["live", "--run-id", "topup-1", "--cap", "25"],
                     ["live", "--run-id", "topup-1", "--cap", "25", "--clearance", "c.json", "--out", "d"],
                     ["live", "--run-id", "x-1", "--cap", "25", "--clearance", "c.json"],               # wrong prefix
                     ["live", "--run-id", "topup-1", "--cap", "25", "--clearance", "c.json"]):          # a draft plan
            self.assertEqual(self.call(argv, p)[0], 2, argv)


if __name__ == "__main__":
    unittest.main()
