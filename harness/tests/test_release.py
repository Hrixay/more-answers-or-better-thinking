"""Tests for harness/release.py (D-149, D-206, D-207): the rules decide in order and leave anything unruled waiting; D-206's groups are
IN or OUT, none left waiting; the scrub counts by category on synthetic text (never returning a match); the lock manifests' hash blocks
parse; Vision's patterns load at their pin; the fresh copy (--package) holds the IN files, the gated and named-only rules, the locks'
bare records and the mapping note."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness import release as rel

REPO = Path(__file__).resolve().parents[1].parent


def _git_ok(ref: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", ref], check=True, capture_output=True)
        return True
    except Exception:
        return False


class Rules(unittest.TestCase):
    def test_first_match_wins(self):
        self.assertEqual(rel.classify("CHATS.md")[1], rel.OUT)
        self.assertEqual(rel.classify("handovers/friday.md")[1], rel.OUT)
        self.assertEqual(rel.classify("decisions/register.md")[1], rel.OUT)
        self.assertEqual(rel.classify("data/tasks/main-ledger-l14n6-v1/items.jsonl")[1], rel.OUT)
        self.assertEqual(rel.classify("research/team-prompts/x.txt")[:2], ("test-item-renders", rel.OUT))
        self.assertEqual(rel.classify("harness/analysis/scoring.py")[1], rel.IN)
        self.assertEqual(rel.classify("research/study1b-spec.md")[:2], ("locked-plans", rel.IN))
        self.assertEqual(rel.classify("research/models/team_prompts.py")[1], rel.IN)
        self.assertEqual(rel.classify("raw/main-l14n6-1/compact_table.csv")[1], rel.IN)
        self.assertEqual(rel.classify("raw/main-l14n6-1/calls.jsonl")[1], rel.OUT)
        self.assertEqual(rel.classify("something/new.txt"), ("none", rel.ASK, "no rule covers it: waits for a ruling"))

    def test_d206_groups_are_decided(self):
        for path in ("research/topup-run-spec.md", "research/pilot-plan-ledger.md", "data/pilot-plan.md", "research/study1b-plan.md",
                     "ops/spend-log.md", "harness/release.py", "ops/lock/LOCK-MANIFEST.md", "studies/1-real-price/spec.md"):
            self.assertEqual(rel.classify(path)[1], rel.IN, path)
        self.assertEqual(rel.classify("harness/tools/layout/batch-f-spec.md")[:2], ("layout-tools", rel.OUT))        # Edith's M10
        self.assertEqual(rel.classify("harness/tools/layout/measure_tables.py")[1], rel.OUT)
        for path in ("ops/reviews/2026-10-12-clearance-main-l14n6-1.md", "ops/review-checklist.md", "ops/proofs/2026-10-31-proof-9-checks.md",
                     "research/some-note.md", "research/paper-notes/claims-ledger.md", "data/free-tests/x.json", "data/README.md",
                     "the-ask.md", "paper/sections/01-intro.md", "paper/supplement/x.md", "studies/5-cheap-judges/spec.md",
                     "studies/1-real-price/brief.md", "studies/1-real-price/log.md", "README.md"):
            self.assertEqual(rel.classify(path)[1], rel.OUT, path)

    def test_the_four_plans_and_the_spend_log_are_gated(self):
        self.assertEqual(set(rel.GATED), {"research/topup-run-spec.md", "research/pilot-plan-ledger.md", "data/pilot-plan.md",
                                          "research/study1b-plan.md", "ops/spend-log.md"})
        for path in rel.GATED:
            self.assertEqual(rel.classify(path)[1], rel.IN, path)

    def test_edith_cleared_the_spend_logs_paths_by_exact_count(self):
        self.assertEqual({k: v[0] for k, v in rel.CLEARED.items()}, {("ops/spend-log.md", "home_paths"): 3, ("ops/spend-log.md", "people"): 3})
        self.assertTrue(all(path in rel.GATED for path, _ in rel.CLEARED))

    def test_pinned_extras_are_released_in_spite_of_the_rules_after_them(self):
        for path in rel.PINNED_EXTRAS:
            self.assertEqual(rel.classify(path)[:2], ("pinned-extras", rel.IN), path)

    def test_the_anonymisers_patterns_are_not_released(self):
        """D-215: paper/tools/anon.py holds part of an account address, and nothing in the package needs it."""
        self.assertEqual(rel.classify("paper/tools/anon.py")[:2], ("paper", rel.OUT))
        self.assertNotIn("paper/tools/anon.py", rel.PINNED_EXTRAS)

    def test_every_pinned_extra_is_the_pin_the_outputs_read(self):
        try:
            from harness.analysis import paper_out_core, paper_out_lint
        except ImportError:
            self.skipTest("the analysis modules need numpy or matplotlib")
        plan = paper_out_core.SOURCES["plan"]
        want = {plan.path: (plan.commit, plan.sha256), paper_out_lint.VOCAB_PIN[0]: paper_out_lint.VOCAB_PIN[1:]}
        got = {k: (v[0], v[1]) for k, v in rel.PINNED_EXTRAS.items()}
        self.assertEqual(got, {k: tuple(v) for k, v in want.items()})
        self.assertEqual([k for k, v in rel.PINNED_EXTRAS.items() if v[2]], [])


class Fingerprints(unittest.TestCase):
    """Edith's MUST on 3c1284c4: four code files have their SHA-256 recorded in released data files, so editing them (even a help text) breaks the
    record. Their current bytes must still be the recorded ones."""
    RECORDED = (("harness/analysis/free_analyses.py", "data/main/free-analyses/fa13.json"),
                ("harness/analysis/pilot1_recount.py", "data/pilot/pilot1-recount-e12.json"),
                ("harness/analysis/reproduction.py", "data/paper-outputs/reproduction/sources.json"),
                ("harness/taskgen/illustration.py", "data/paper-outputs/reproduction/sources.json"))

    def test_the_recorded_code_hashes_still_match(self):
        for code, record in self.RECORDED:
            with self.subTest(code=code):
                if not (REPO / code).is_file() or not (REPO / record).is_file():
                    self.skipTest("the code or its record is not in this copy")
                digest = hashlib.sha256((REPO / code).read_bytes()).hexdigest()
                self.assertIn(digest, (REPO / record).read_text(encoding="utf-8"), f"{code} was edited after {record} recorded its hash")


class Scrub(unittest.TestCase):
    def test_counts_by_category(self):
        anon = (rel.re.compile(r"\bAlice\b"),)
        states = {"[1227, 1050, 1955]"}
        text = ("Alice wrote /Users/alice/x and /private/tmp/y; mail a.b@example.org; key sk-ant-abcdefghijkl; "
                "Jarvis ruled D-12; the state [1227,1050, 1955] and [1, 2, 3]; arm om@6.pooled is not an email")
        got = rel.scrub(text, anon, states)
        self.assertEqual(got, {"people": 1, "home_paths": 2, "emails": 1, "secrets": 1, "internal_names": 1, "decision_ids": 1,
                               "test_answers": 1})
        self.assertTrue(all(isinstance(v, int) for v in got.values()))                      # counts only, never the text

    def test_email_pattern_is_linear(self):
        import time
        t = time.time()
        rel.scrub("a." * 100000, (), set())
        self.assertLess(time.time() - t, 5.0)


class Package(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.repo = self.t / "repo"
        self.repo.mkdir()
        run = lambda *a: subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], check=True, capture_output=True)
        run("init", "-q")
        (self.repo / "secret.txt").write_text("private contents\n")
        run("add", "secret.txt")
        run("commit", "-q", "-m", "lock")
        for tag in ("prereg-lock-1", "prereg-lock-2", "prereg-lock-3", "prereg-lock-4"):
            run("tag", "-a", "-m", "Pre-registration " + tag, tag)
        self.saved = (rel.ROOT, rel.LOCKS)
        rel.ROOT = self.repo
        self.raw = self.t / "raw" / "run-1"
        self.raw.mkdir(parents=True)
        (self.raw / "compact_table.csv").write_text("a,b\n1,2\n")
        (self.raw / "k.json").write_text("{}\n")
        (self.t / "readme.md").write_text("public readme\n")

    def tearDown(self):
        rel.ROOT, rel.LOCKS = self.saved
        self.tmp.cleanup()

    def doc(self):
        def row(name, **kw):
            return {"path": f"raw/run-1/{name}", "where": "raw", "decision": rel.IN, "rule": "x", **kw}
        return {"commit": "0" * 40, "files": [
            row("compact_table.csv"), row("k.json", named_only=True),
            row("held.csv", gate={"held": True, "counts": {"home_paths": 1}}),
            {"path": "raw/run-1/runner.log", "where": "raw", "decision": rel.OUT, "rule": "x"}]}

    def make(self, kind="named", cleared=()):
        (self.raw / "held.csv").write_text("h\n")
        dest = self.t / ("pkg-" + kind + str(len(cleared)))
        summary = rel.package(self.doc(), self.t / "raw", dest, kind, [f"README.md={self.t / 'readme.md'}"], list(cleared))
        return dest, summary

    def test_writes_the_in_files_holds_the_gated_one_and_leaves_out_the_rest(self):
        dest, summary = self.make()
        self.assertEqual(summary["held"], ["raw/run-1/held.csv"])
        self.assertTrue((dest / "data/raw/run-1/compact_table.csv").exists())
        self.assertFalse((dest / "data/raw/run-1/held.csv").exists())
        self.assertFalse((dest / "data/raw/run-1/runner.log").exists())
        self.assertEqual((dest / "README.md").read_text(), "public readme\n")
        listing = json.loads((dest / "RELEASE-FILES.json").read_text())
        self.assertEqual(listing["held"], ["raw/run-1/held.csv"])

    def test_a_cleared_gated_file_is_released(self):
        saved = rel.GATED
        rel.GATED = (*saved, "raw/run-1/held.csv")
        try:
            dest, summary = self.make(cleared=("raw/run-1/held.csv",))
        finally:
            rel.GATED = saved
        self.assertEqual(summary["held"], [])
        self.assertTrue((dest / "data/raw/run-1/held.csv").exists())
        self.assertEqual(json.loads((dest / "RELEASE-FILES.json").read_text())["cleared"], ["raw/run-1/held.csv"])

    def test_cleared_must_name_a_gated_file(self):
        with self.assertRaises(SystemExit):
            self.make(cleared=("raw/run-1/compact_table.csv",))

    def test_the_tmlr_kind_leaves_out_the_named_only_files(self):
        dest, _ = self.make(kind="tmlr")
        self.assertFalse((dest / "data/raw/run-1/k.json").exists())
        self.assertTrue((dest / "data/raw/run-1/compact_table.csv").exists())
        dest, _ = self.make(kind="named")
        self.assertTrue((dest / "data/raw/run-1/k.json").exists())

    def test_the_licences_name_the_first_author_only_and_the_anonymous_zip_nobody(self):
        named, _ = self.make(kind="named")
        tmlr, _ = self.make(kind="tmlr")
        self.assertIn("Copyright (c) 2026 Hriday Kalpit Jain\n", (named / "LICENSE").read_text())
        self.assertNotIn("Lodha", (named / "LICENSE").read_text())                               # D-214: the first author only
        self.assertIn("Copyright (c) 2026 Anonymous authors\n", (tmlr / "LICENSE").read_text())
        for pkg in (named, tmlr):
            data = (pkg / "LICENSE-DATA").read_text()
            self.assertIn("Attribution 4.0 International", data)
            self.assertIn("CC BY 4.0", data)
            self.assertNotIn("D-204", data)                                                         # no decision number in a public file
            self.assertIn("per-call tables", data)
            self.assertIn("All files in this repository other than the code covered by LICENSE", data)       # the catch-all (Jarvis)
            for part in ("run records", "lock records", "plans and pre-registrations", "the supplement"):
                self.assertIn(part, data.replace("\n", " "))
            self.assertNotIn("Hriday", data)

    def test_the_citation_files_are_in_the_named_package_only(self):
        named, _ = self.make(kind="named")
        tmlr, _ = self.make(kind="tmlr")
        zen = json.loads((named / ".zenodo.json").read_text())
        self.assertEqual([c["name"] for c in zen["creators"]], ["Jain, Hriday Kalpit", "Lodha, Vivek Jain"])
        self.assertEqual(zen["license"], "MIT")
        cff = (named / "CITATION.cff").read_text()
        self.assertIn("more-answers-or-better-thinking", cff)
        self.assertIn('family-names: "Lodha"', cff)
        for name in (".zenodo.json", "CITATION.cff"):
            self.assertFalse((tmlr / name).exists())
        self.assertFalse((tmlr / "lock-records").exists())                                       # the commit objects name the authors
        self.assertIn("prereg-lock-1", (tmlr / "LOCKED-FILES.md").read_text())                    # the ids stay (D-150)
        self.assertNotIn("Hriday", "".join(p.read_text(errors="ignore") for p in tmlr.rglob("*") if p.is_file()))
        self.assertNotIn("more-answers", "".join(p.read_text(errors="ignore") for p in tmlr.rglob("*") if p.is_file()))

    def test_every_listed_path_exists_with_its_sha256_and_the_generated_ones_exist(self):
        """Edith's P3: RELEASE-FILES.json lists the package's own paths (a run file under data/raw/), each with its hash."""
        (self.t / "supp.pdf").write_bytes(b"%PDF-1.4 stand-in\n")
        dest = self.t / "pkg-listed"
        rel.package(self.doc(), self.t / "raw", dest, "named", [f"README.md={self.t / 'readme.md'}"], [], self.t / "supp.pdf")
        listing = json.loads((dest / "RELEASE-FILES.json").read_text())
        self.assertEqual(sorted(f["path"] for f in listing["files"]), ["data/raw/run-1/compact_table.csv", "data/raw/run-1/k.json"])
        for f in [*listing["files"], *listing["supplied"]]:
            self.assertEqual(hashlib.sha256((dest / f["path"]).read_bytes()).hexdigest(), f["sha256"], f["path"])
        self.assertEqual({f["path"] for f in listing["supplied"]}, {"README.md", "supplement.pdf"})
        for g in listing["generated"]:
            self.assertTrue((dest / g).exists(), g)
        for g in ("LOCKED-FILES.md", "lock-records/", ".gitattributes", "RELEASE-FILES.json", "LICENSE", "LICENSE-DATA", "CITATION.cff"):
            self.assertIn(g, listing["generated"])
        note = (dest / "LOCKED-FILES.md").read_text()
        self.assertIn("| `data/raw/run-1/compact_table.csv` | `" + hashlib.sha256(b"a,b\n1,2\n").hexdigest() + "` | n/a | n/a | n/a | n/a |", note)

    def test_git_is_told_not_to_change_line_endings(self):
        """Edith's P4: a default Windows clone (core.autocrlf=true) must not change a byte."""
        for kind in ("named", "tmlr"):
            dest, _ = self.make(kind=kind)
            lines = [l for l in (dest / ".gitattributes").read_text().splitlines() if l and not l.startswith("#")]
            self.assertEqual(lines, ["* -text"])

    def test_an_email_or_a_secret_stops_the_package_unless_known_explains_its_count(self):
        """Edith: the privacy gate stops on an email or a secret in any released file; the message holds counts and paths, not the match."""
        doc = self.doc()
        doc["files"][0]["scrub"] = {"secrets": 1, "emails": 2, "people": 3}
        with self.assertRaises(SystemExit) as r:
            rel.package(doc, self.t / "raw", self.t / "pkg-planted", "named", [], [])
        self.assertIn("raw/run-1/compact_table.csv: secrets 1", str(r.exception))
        self.assertIn("emails 2", str(r.exception))
        self.assertNotIn("people", str(r.exception))                                           # the D-206 categories stay counts in the summary
        self.assertFalse((self.t / "pkg-planted").exists())
        doc["files"][0]["scrub"] = {}                                                          # KNOWN had popped them: allowed
        doc["files"][0]["known"] = {"secrets": {"count": 1, "why": "a fake key"}}
        rel.package(doc, self.t / "raw", self.t / "pkg-known", "named", [], [])
        doc["files"][2]["scrub"] = {"emails": 1}                                               # a held file is not written, so not refused
        rel.package(doc, self.t / "raw", self.t / "pkg-held", "named", [], [])

    def test_known_keeps_both_categories_of_a_file(self):
        """Edith's LOW: a file with two explained hits keeps both reasons (setdefault, not the last one only)."""
        row = {"path": "harness/tests/test_release.py", "scrub": {"emails": 2, "secrets": 1, "home_paths": 2}}
        for (kp, kc), (kn, why) in rel.KNOWN.items():
            if row["path"] == kp and row["scrub"].get(kc) == kn:
                row["scrub"].pop(kc)
                row.setdefault("known", {})[kc] = {"count": kn, "why": why}
        self.assertEqual(sorted(row["known"]), ["emails", "home_paths", "secrets"])
        self.assertIn(("harness/tests/test_paper_out_disk.py", "emails"), rel.KNOWN)

    def test_a_supplied_file_cannot_replace_a_released_or_generated_one_or_hold_a_key(self):
        for name in ("LICENSE", "RELEASE-FILES.json", "data/raw/run-1/compact_table.csv", "lock-records/x", ".gitattributes"):
            with self.assertRaises(SystemExit, msg=name):
                rel.package(self.doc(), self.t / "raw", self.t / ("p" + str(abs(hash(name)))), "named", [f"{name}={self.t / 'readme.md'}"], [])
        (self.t / "key.txt").write_text("sk-" + "ant-abcdefghijkl\n")                           # joined here so this file shows one fake key only
        with self.assertRaises(SystemExit) as r:
            rel.package(self.doc(), self.t / "raw", self.t / "pkg-key", "named", [f"notes.txt={self.t / 'key.txt'}"], [])
        self.assertNotIn("abcdefghijkl", str(r.exception))

    def test_every_run_folder_is_needed_for_a_package(self):
        with self.assertRaises(SystemExit) as r:
            rel.require_runs({"raw_runs": ["main-l14n6-1"]})
        self.assertIn("study1b-1", str(r.exception))
        rel.require_runs({"raw_runs": list(rel.RAW_RUNS)})

    def test_the_supplement_goes_to_one_fixed_path(self):
        (self.t / "supp.pdf").write_bytes(b"%PDF-1.4 stand-in\n")
        dest = self.t / "pkg-supp"
        rel.package(self.doc(), self.t / "raw", dest, "named", [], [], self.t / "supp.pdf")
        self.assertEqual(rel.SUPPLEMENT_PATH, "supplement.pdf")
        self.assertEqual((dest / "supplement.pdf").read_bytes(), b"%PDF-1.4 stand-in\n")

    def test_the_lock_records_are_bare(self):
        dest, _ = self.make()
        for tag in rel.LOCKS:
            body = (dest / "lock-records" / f"{tag}.commit").read_bytes()
            cid = rel._git("rev-parse", f"{tag}^{{commit}}").strip()
            self.assertEqual(hashlib.sha1(b"commit %d\0" % len(body) + body).hexdigest(), cid)
            tag_body = (dest / "lock-records" / f"{tag}.tag").read_bytes()
            self.assertEqual(hashlib.sha1(b"tag %d\0" % len(tag_body) + tag_body).hexdigest(), rel._git("rev-parse", tag).strip())
            files = (dest / "lock-records" / f"{tag}.files").read_text()
            self.assertIn("secret.txt", files)
            self.assertNotIn("private contents", files + body.decode())                             # names and ids, never contents
        self.assertFalse(any("private contents" in p.read_text(errors="ignore") for p in dest.rglob("*") if p.is_file()))

    def test_refuses_a_non_empty_folder_and_a_bad_add(self):
        dest = self.t / "full"
        dest.mkdir()
        (dest / "x").write_text("x")
        with self.assertRaises(SystemExit):
            rel.package(self.doc(), self.t / "raw", dest, "named", [], [])
        for bad in ("../x=" + str(self.t / "readme.md"), "/abs=" + str(self.t / "readme.md"), "noequals"):
            with self.assertRaises(SystemExit):
                rel.package(self.doc(), self.t / "raw", self.t / ("p" + str(abs(hash(bad)))), "named", [bad], [])

    def test_the_note_maps_each_file_to_its_locks(self):
        rows = [{"path": "a.py", "sha256": "ab" * 32, "locks": {"prereg-lock-1": "same", "prereg-lock-2": "changed", "prereg-lock-3": "absent", "prereg-lock-4": "same"}}]
        note = rel.locked_files_note({"commit": "c" * 40}, rows, {t: {"commit": "d" * 40, "files": 3} for t in rel.LOCKS})
        self.assertIn("| `a.py` | `" + "ab" * 32 + "` | = | changed | - | = |", note)


@unittest.skipUnless(_git_ok("prereg-lock-4") and _git_ok(rel.ANON_PIN[1]), "the tags or Vision's commit are not available")
class Pins(unittest.TestCase):
    def test_lock_hash_blocks_parse(self):
        for tag in rel.LOCKS:
            h = rel.lock_hashes(tag)
            self.assertGreater(len(h), 100)
            self.assertTrue(all(len(v) == 64 for v in h.values()))

    def test_vision_patterns(self):
        pats, sha = rel.load_anon()
        self.assertEqual(len(pats), 2)
        self.assertEqual(len(sha), 64)


if __name__ == "__main__":
    unittest.main()
