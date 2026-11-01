"""D-149's clean release package: what goes in and what stays private (each with its rule and reason), each released file's SHA-256
and the locks it matches, a scrub check of every released file, and (with --package) the fresh copy itself. Counts only: no match is
ever printed or written. No model call, no network, never reads .env.

    python3 -m harness.release --commit <commit> --raw <data/raw folder> --out <empty folder>
    python3 -m harness.release --commit <commit> --raw <data/raw folder> --out <empty folder> --package <empty folder> [--kind named|tmlr]
        [--add DEST=SRC ...] [--cleared PATH ...]

D-206 (2026-11-01) and D-207 (2026-11-01) settled every group the draft left in ASK: the four plan files and the spend log are IN
(each only after the counts-only privacy check is clean: GATED); Edith's reviews, the other research notes, the development reads, the
project brief, the other study folders, the proof PDFs and the paper's source are OUT. D-207 (option D): the package is a fresh copy
with no history, plus the four locks' bare records (each lock commit's object and its file list, no contents) and two files at their
pinned versions (PINNED_EXTRAS). D-215: the anonymiser's patterns (paper/tools/anon.py) are NOT released. --package writes it; LOCKED-FILES.md in it maps each file to the locks that hold it.

The ruling (D-149): release the study plans (pre-registrations), the analysis and run code, the result files and per-call records
(raw replies only where they contain no test answers), and a note mapping each released file to the locked fingerprints. Kept
private: internal team notes, the decision register (the user's words) and the test puzzles' answers. Hosting and the licence are
step 3.

How each path is decided: RULES in order, first match wins; a path no rule covers is ASK (it waits for a ruling and is never released
by default). Every tracked file at --commit is classified, plus the run folders' files under --raw for the runs RAW_RUNS names. An IN
file is listed with its SHA-256 and, for each lock tag, whether its bytes equal that lock's hash (ops/lock/LOCK-MANIFEST.md's file-hash
block at the tag), differ, or the lock does not hold it.

The scrub check reads every IN and ASK file and counts, per file and category (never the matched text):
- people: the authors' names, initials, handles and emails (Vision's anonymous-build patterns, paper/tools/anon.py at ANON_PIN, loaded
  only at its pinned SHA-256), plus any email address;
- home paths: /Users/..., /private/tmp/..., /var/folders/..., /home/...;
- secrets: API-key and token patterns (a pattern scan; .env is never opened);
- test answers: any balances list equal to a reference state of a frozen test set under data/tasks (every state after a step, every
  answer; start balances are left out, since prompts print them), read from the sets' items.jsonl at --commit;
- internal (shown, not a refusal): the chats' names and decision ids, which the code's comments cite.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
IN, OUT, ASK = "in", "out", "ask"
LOCKS = ("prereg-lock-1", "prereg-lock-2", "prereg-lock-3", "prereg-lock-4")
MANIFEST = "ops/lock/LOCK-MANIFEST.md"
ANON_PIN = ("paper/tools/anon.py", "52b1eb0")          # Vision's anonymous-build scan (SHA-256 checked below)
# D-207: two files the paper outputs read, released at the version the outputs pin (HEAD's version may differ). path -> (commit, SHA-256,
# named package only?). D-215 (2026-11-01): the third, the anonymiser's patterns (paper/tools/anon.py), is NOT released: it holds part of an
# account address, and nothing in the package needs it (the two tables that read it, TAB-19 and TAB-20, ship as built). A test asserts these
# equal the pins in harness/analysis (paper_out_core.SOURCES["plan"], paper_out_lint.VOCAB_PIN).
PINNED_EXTRAS: Dict[str, Tuple[str, str, bool]] = {
    "decisions/briefings/2026-10-15-compiler/plan-result.json": ("7b43f91", "07d38a4c790dc37c936ac3a6f1ab9bfc0eeae5f7a3cf66035e439205d4f47a28", False),
    "research/paper-notes/tools/ledger.py": ("cbec674", "8dc841567e6e85f349ccc9d39f558f5679646bdd02f3d85b3cc653b70bbc09ac", False),
}
# D-209: the public repository and the citation names (the paper's BibTeX prints them too) live in a data file that the named package
# carries and the anonymous TMLR ZIP does not (D-150), so this module names nobody.
NAMED_ONLY = ("harness/release_names.json",)
NAMES_FILE = Path(__file__).with_name("release_names.json")
# Edith's counts-only privacy check (ops/reviews/2026-11-01-release-privacy-checks.md, section 1): hits she cleared by name and exact count. They stay
# in the counts (the D-206 handle/path list) but do not hold a GATED file back. (path, category) -> (count, why).
CLEARED: Dict[Tuple[str, str], Tuple[int, str]] = {
    ("ops/spend-log.md", "home_paths"): (3, "the handle in three local folder paths (a backup and a run checkout); D-206 rules on these"),
    ("ops/spend-log.md", "people"): (3, "the same three paths"),
}
# D-206: IN only after the counts-only privacy check is clean; a file with a refusing hit is held out of the package (and listed).
GATED = ("research/topup-run-spec.md", "research/pilot-plan-ledger.md", "data/pilot-plan.md", "research/study1b-plan.md", "ops/spend-log.md")
ANON_SHA = None                                        # filled from the pinned commit's blob on first use and recorded in the output
RAW_RUNS = ("main-l14n6-1", "study1b-1", "topup-1", "ladder-l14n-1", "diag-haiku-effort-1", "pilot-ledger-1", "check-ledger-1",
            "s3-ledger-1", "smoke-1", "smoke-2")

# (rule id, path patterns, decision, reason). First match wins.
RULES: Tuple[Tuple[str, Tuple[str, ...], str, str], ...] = (
    ("secrets", (".env", "*.env", "**/.env"), OUT, "never released (never opened)"),
    ("pinned-extras", tuple(PINNED_EXTRAS), IN, "D-207: a file the paper outputs read, released at the version they pin"),
    ("team-notes", ("CHATS.md", "CLAUDE.md", "NOW.md", "LOG.md", "LOG-archive.md", "handovers/*", ".claude/*"), OUT,
     "internal team notes (D-149: kept private)"),
    ("register", ("decisions/*",), OUT, "the decision register, its briefings and evidence: the user's words (D-149: kept private)"),
    ("test-puzzles", ("data/tasks/*",), OUT, "the frozen test puzzles carry their answers (D-149: kept private)"),
    ("paper-notes", ("paper/notes/*",), OUT, "working notes, not reviewed deliverables"),
    ("test-item-renders", ("research/team-prompts/*", "research/wording-check-d42-ledger/*", "research/wording-check-e2-hpick8/*"), OUT,
     "renders a real test item; may carry its answers (D-149: test answers stay private; Jarvis, 2026-10-17)"),
    ("raw-replies", ("raw/*/calls.jsonl",), OUT, "per-call records with the replies, which hold answers to test puzzles (D-149)"),
    ("raw-process", ("raw/*/runner.log", "raw/*/*.pid", "raw/*/window.json"), OUT, "the runner's process files (local paths, pids)"),
    ("layout-tools", ("harness/tools/layout/*",), OUT, "Edith's M10: the paper's table-layout helpers and eight internal build briefs; they need the paper source, which is not released"),
    ("code", ("harness/*",), IN, "the run and analysis code"),
    ("lock-manifest", (MANIFEST,), IN, "the lock manifest: every lock's per-file hashes"),
    ("study1-plan", ("studies/1-real-price/spec.md",), IN, "Study 1's pre-registration"),
    ("locked-plans", ("research/study1b-spec.md", "research/d72-d73-lock-spec.md", "research/reporting-definitions-main.md",
                      "research/scoring-step-lines.md", "research/d42-ledger-variant.md", "research/e2-and-picker-prompts.md"), IN,
     "a pre-registration document named in the lock manifest"),
    ("run-code-inputs", ("research/models/*", "research/fixtures/*"), IN,
     "code and fixtures the run, analysis or tests read (the team prompts, the D-72 simulator, the simulated test data)"),
    ("results", ("data/main/*", "data/pilot/*", "data/plans/*", "data/paper-outputs/*"), IN,
     "result files, run plans and the paper's tables and figures"),
    ("raw-tables", ("raw/*/compact_table.csv", "raw/*/haiku_extract.csv"), IN, "the per-call tables: ids, settings, tokens, cost, outcome, right or wrong; no reply text"),
    ("raw-run-records", ("raw/*/manifest.json", "raw/*/k.json", "raw/*/calibration_limits.json", "raw/*/slim_plan.json",
                         "raw/*/topup_plan.json", "raw/*/ledger.jsonl", "raw/*/*_result.json"), IN,
     "the run's own records: its manifest, plan, k, limits and the spend guard's ledger (no reply text)"),
    ("pkg-files", (".gitignore", "harness/requirements*.txt"), IN,
     "package files; .gitignore keeps its locked bytes (its data/raw/ line stays: the push runs `git add -f data/raw`, checked with `git ls-files data/raw | wc -l`)"),
    ("team-readme", ("README.md",), OUT, "the working repository's own README; the public README is supplied with --add README.md=<file>"),
    ("released-plans", GATED[:4], IN, "D-206: a study plan (pre-registration) the paper cites; IN once the counts-only privacy check is clean"),
    ("spend-log", ("ops/spend-log.md",), IN, "D-206: the cost of every paid run; IN once the counts-only privacy check is clean (the README explains the 2-cent gap to the paper)"),
    ("reviews", ("ops/reviews/*", "ops/review-checklist.md"), OUT, "D-206: Edith's review records, internal"),
    ("proofs", ("ops/proofs/*",), OUT, "D-206: the proof PDFs and their check notes (some carry the authors' names; none is needed)"),
    ("research-notes", ("research/*",), OUT, "D-206: working documents (the claims ledger, the findings register, sweeps, the other plans' drafts)"),
    ("dev-reads", ("data/free-tests/*", "data/ledger-free-read*", "data/codetrace-free-test/*", "data/wording-check*", "data/examples/*",
                   "data/ledger-measured.json", "data/README.md"), OUT,
     "D-206: development reads on Max-plan Haiku (disclosed in the paper); they hold replies and answers to practice puzzles"),
    ("project-brief", ("the-ask.md",), OUT, "D-206: the project's original brief, in the user's words (D-149)"),
    ("paper", ("paper/*",), OUT, "D-206: the paper's source goes to arXiv, not into this package (only the final supplement PDF is packaged: --add)"),
    ("studies-other", ("studies/*",), OUT, "D-206: study briefs and logs (Study 1's and Study 5's, and Study 5's plan, which the paper does not use)"),
)

PATTERNS: Dict[str, Sequence[re.Pattern]] = {
    "home_paths": (re.compile(r"/Users/[^/\s]+"), re.compile(r"/private/(?:tmp|var)/"), re.compile(r"/var/folders/"),
                   re.compile(r"/home/[^/\s]+")),
    "emails": (re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z][A-Za-z0-9-]{0,62}\.[A-Za-z][A-Za-z0-9.-]{0,252}"),),  # bounded (linear); a domain starts with a letter, so arm keys such as om@6.pooled are not emails
    "secrets": (re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"), re.compile(r"\bghp_[A-Za-z0-9]{20,}"), re.compile(r"\bxox[abp]-[A-Za-z0-9-]{10,}"),
                re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"(?i)\b(?:api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    "internal_names": (re.compile(r"\b(?:Jarvis|Karen|Friday|Edith|Vision|Vivek)\b"),),
    "decision_ids": (re.compile(r"\bD-\d{1,3}\b"),),
}
STATE = re.compile(r"\[\s*-?\d+(?:\s*,\s*-?\d+)+\s*\]")


def _git(*args: str, text: bool = True):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=text).stdout


def classify(path: str) -> Tuple[str, str, str]:
    for rid, pats, decision, reason in RULES:
        if any(fnmatch.fnmatch(path, p) for p in pats):
            return rid, decision, reason
    return "none", ASK, "no rule covers it: waits for a ruling"


def lock_hashes(tag: str) -> Dict[str, str]:
    text = _git("show", f"{tag}:{MANIFEST}")
    block = text.split("<!-- FILE-HASHES-BEGIN -->", 1)[1].split("<!-- FILE-HASHES-END -->", 1)[0]
    out = {}
    for line in block.splitlines():
        m = re.match(r"^([0-9a-f]{64})  (.+)$", line)
        if m:
            out[m.group(2)] = m.group(1)
    if not out:
        raise ValueError(f"{tag}: no file hashes in {MANIFEST}")
    return out


def load_anon() -> Tuple[Sequence[re.Pattern], str]:
    """Vision's PEOPLE and HANDLES patterns from paper/tools/anon.py at the pinned commit (never retyped)."""
    raw = _git("show", f"{ANON_PIN[1]}:{ANON_PIN[0]}", text=False)
    ns: Dict[str, object] = {}
    exec(compile(raw, ANON_PIN[0], "exec"), ns)                                                  # the pinned blob only
    return (ns["PEOPLE"], ns["HANDLES"]), hashlib.sha256(raw).hexdigest()                     # type: ignore[return-value]


def test_states(commit: str) -> Set[str]:
    """Every reference state of every frozen test set at `commit` (after each step, and each answer), as ledger.fmt prints a state,
    minus every start balance (prompts print those). Never printed."""
    from .taskgen import ledger
    states: Set[str] = set()
    starts: Set[str] = set()
    for path in _git("ls-tree", "-r", "--name-only", commit, "data/tasks").splitlines():
        if not path.endswith("items.jsonl"):
            continue
        for line in _git("show", f"{commit}:{path}").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            for ch in it.get("chains") or []:
                if isinstance(ch, dict):
                    if isinstance(ch.get("start"), list):
                        starts.add(ledger.fmt(ch["start"]))
                    states.update(ledger.fmt(s) for s in ch.get("states") or [] if isinstance(s, list))
            ans = it.get("answer")
            for a in ans if isinstance(ans, list) else []:
                if isinstance(a, list) and all(isinstance(x, int) for x in a):
                    states.add(ledger.fmt(a))
    return states - starts


def norm_state(text: str) -> str:
    return "[" + ", ".join(x.strip() for x in text.strip()[1:-1].split(",")) + "]"


def scrub(text: str, anon: Sequence[re.Pattern], states: Set[str]) -> Dict[str, int]:
    out = {k: sum(len(p.findall(text)) for p in pats) for k, pats in PATTERNS.items()}
    out["people"] = sum(len(p.findall(text)) for p in anon)
    out["test_answers"] = sum(1 for m in STATE.finditer(text) if norm_state(m.group(0)) in states)
    return {k: v for k, v in out.items() if v}


REFUSING = ("people", "emails", "home_paths", "secrets", "test_answers")
# Hits that are known and explained: (path, category) -> the reason and the exact count expected (a different count is a new hit).
KNOWN: Dict[Tuple[str, str], Tuple[int, str]] = {
    ("harness/tests/test_real_transport.py", "secrets"): (2, "fake keys ('sk-ant-test-…', 'sk-ant-SECRET…') that test the .env reader"),
    ("harness/tests/test_paper_out_disk.py", "emails"): (1, "a fake address at example.invalid in a test repository's git config"),
    ("harness/tests/test_check_tracked.py", "emails"): (1, "a fake address at example.invalid in a test repository's git config"),
    ("harness/tests/test_lockhash.py", "emails"): (1, "a fake address at example.invalid in a test repository's git config"),
    ("harness/tests/test_release.py", "secrets"): (1, "a fake key ('sk-ant-abc…') in the text that tests the scrub"),
    ("harness/tests/test_release.py", "emails"): (2, "fake addresses (example.org, example.invalid) in the scrub test and a test repository's git config"),
    ("harness/tests/test_release.py", "home_paths"): (2, "fake paths (/Users/alice, /private/tmp) in the text that tests the scrub"),
}


def inventory(commit: str, raw: Optional[Path]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for path in _git("ls-tree", "-r", "--name-only", commit).splitlines():
        rid, dec, why = classify(path)
        rows.append({"path": path, "where": "git", "rule": rid, "decision": dec, "reason": why})
    if raw is not None:
        for run in RAW_RUNS:
            folder = Path(raw) / run
            if not folder.is_dir():
                continue
            for f in sorted(p for p in folder.iterdir() if p.is_file()):
                rel = f"raw/{run}/{f.name}"
                rid, dec, why = classify(rel)
                rows.append({"path": rel, "where": "raw", "rule": rid, "decision": dec, "reason": why})
    return rows


def read(commit: str, raw: Optional[Path], row: Mapping[str, object]) -> bytes:
    if row["where"] == "git" and row["path"] in PINNED_EXTRAS:                                     # D-207: the version the outputs pin
        pin_commit, pin_sha, _ = PINNED_EXTRAS[str(row["path"])]
        data = _git("show", f"{pin_commit}:{row['path']}", text=False)
        if hashlib.sha256(data).hexdigest() != pin_sha:
            raise ValueError(f"{row['path']} at {pin_commit}: SHA-256 differs from the pinned one")
        return data
    if row["where"] == "git":
        return _git("show", f"{commit}:{row['path']}", text=False)
    return (Path(raw) / str(row["path"])[len("raw/"):]).read_bytes()                              # type: ignore[arg-type]


def build(commit: str, raw: Optional[Path]) -> Dict[str, object]:
    commit = _git("rev-parse", commit).strip()
    rows = inventory(commit, raw)
    locks = {t: lock_hashes(t) for t in LOCKS}
    anon, anon_sha = load_anon()
    states = test_states(commit)
    for row in rows:
        if row["decision"] == OUT:
            continue
        data = read(commit, raw, row)
        row["sha256"] = hashlib.sha256(data).hexdigest()
        row["bytes"] = len(data)
        if row["path"] in PINNED_EXTRAS:
            pin_commit, _, named_only = PINNED_EXTRAS[str(row["path"])]
            head = _git("show", f"{commit}:{row['path']}", text=False)
            row["pinned"] = {"commit": pin_commit, "head_equals_pin": head == data}
            row["named_only"] = named_only
        if row["path"] in NAMED_ONLY:
            row["named_only"] = True
        if row["where"] == "git":
            row["locks"] = {t: ("same" if h.get(row["path"]) == row["sha256"] else "changed" if row["path"] in h else "absent")  # type: ignore[arg-type]
                            for t, h in locks.items()}
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            row["scrub"] = {"binary": 1}
            continue
        row["scrub"] = scrub(text, anon, states)
        if row["scrub"].get("test_answers"):                                                    # type: ignore[union-attr]
            if row["decision"] == IN:
                raise ValueError(f"{row['path']}: a released file holds test-set states")
            row.update(decision=OUT, rule="holds-test-states", reason="holds test-set states (D-149: test answers stay private)")
        if row["path"] in GATED:                                                                 # D-206: IN once the check is clean
            counts = {k: v for k, v in row["scrub"].items() if k in REFUSING}                     # type: ignore[union-attr]
            hits = {k: v for k, v in counts.items() if CLEARED.get((str(row["path"]), k), (None,))[0] != v}
            row["gate"] = {"check": "counts-only privacy check", "held": bool(hits), "counts": counts, "cleared": sorted(set(counts) - set(hits))}
        for (kp, kc), (kn, why) in KNOWN.items():
            if row["path"] == kp and row["scrub"].get(kc) == kn:                                 # type: ignore[union-attr]
                row["scrub"].pop(kc)                                                            # type: ignore[union-attr]
                row.setdefault("known", {})[kc] = {"count": kn, "why": why}
    summary: Dict[str, object] = {d: sum(1 for r in rows if r["decision"] == d) for d in (IN, OUT, ASK)}
    handle = [r for r in rows if r["decision"] == IN and any(r.get("scrub", {}).get(k) for k in ("people", "emails", "home_paths"))]  # type: ignore[union-attr]
    summary["held_by_gate"] = sorted(str(r["path"]) for r in rows if r.get("gate", {}).get("held"))   # type: ignore[union-attr]
    summary["in_files_with_handle_or_path_hits"] = {"files": len(handle), "in_a_lock": sum(1 for r in handle if any(v != "absent" for v in r.get("locks", {}).values()))}  # type: ignore[union-attr]
    flagged = {d: {k: sum(1 for r in rows if r["decision"] == d and r.get("scrub", {}).get(k)) for k in REFUSING}  # type: ignore[union-attr]
               for d in (IN, ASK)}
    return {"draft": False, "ruling": "D-149, D-206, D-207", "commit": commit, "raw_runs": [r for r in RAW_RUNS if raw and (Path(raw) / r).is_dir()],
            "anon_patterns": {"file": ANON_PIN[0], "commit": ANON_PIN[1], "sha256": anon_sha},
            "test_states_compared": len(states), "summary": summary, "files_with_refusing_hits": flagged,
            "rules": [{"rule": r[0], "patterns": list(r[1]), "decision": r[2], "reason": r[3]} for r in RULES], "files": rows}


def lock_records(out: Optional[Path]) -> Dict[str, Dict[str, object]]:
    """D-207: each lock's BARE record, no file contents: `<tag>.tag` is the annotated tag object's exact bytes, `<tag>.commit` the commit
    object's (so sha1("commit N\\0" + bytes) is the lock commit's id, which the paper prints) and `<tag>.files` is `git ls-tree -r` of its
    tree (mode, type, blob id, path). These are exactly what Edith checked (privacy checks, section 3); they name the author, so never in the TMLR ZIP."""
    folder = out / "lock-records" if out is not None else None                                    # None: ids and counts only (the anonymous ZIP)
    if folder is not None:
        folder.mkdir(parents=True, exist_ok=True)
    rec: Dict[str, Dict[str, object]] = {}
    for tag in LOCKS:
        cid = _git("rev-parse", f"{tag}^{{commit}}").strip()
        body = _git("cat-file", "commit", cid, text=False)
        if hashlib.sha1(b"commit %d\0" % len(body) + body).hexdigest() != cid:
            raise ValueError(f"{tag}: the commit object's bytes do not hash to its id")
        tid = _git("rev-parse", tag).strip()                                                      # an annotated tag has its own object (Edith: tag, commit and tree)
        tag_body = _git("cat-file", "tag", tag, text=False)
        if _git("cat-file", "-t", tag).strip() != "tag" or hashlib.sha1(b"tag %d\0" % len(tag_body) + tag_body).hexdigest() != tid:
            raise ValueError(f"{tag}: not an annotated tag, or the tag object's bytes do not hash to its id")
        files = _git("ls-tree", "-r", f"{cid}")
        if folder is not None:
            (folder / f"{tag}.tag").write_bytes(tag_body)
            (folder / f"{tag}.commit").write_bytes(body)
            (folder / f"{tag}.files").write_text(files, encoding="utf-8")
        rec[tag] = {"commit": cid, "tag_object": tid, "files": len(files.splitlines())}
    return rec


def locked_files_note(doc: Mapping[str, object], rows: Sequence[Mapping[str, object]], records: Mapping[str, Mapping[str, object]],
                      with_records: bool = True) -> str:
    """The note the paper promises: each released file, its SHA-256, and for each lock whether the lock holds this exact file ("="),
    holds the path with other bytes ("changed"), or does not hold it ("-")."""
    sym = {"same": "=", "changed": "changed", "absent": "-"}
    lines = ["# The released files and the locks that hold them", "",
             f"Built from commit `{doc['commit']}`. Each row is a released file, its SHA-256, and what each lock says about it: `=` the lock's manifest "
             "(`ops/lock/LOCK-MANIFEST.md`, hash block at the lock's tag) lists this exact file; `changed` it lists the path with other bytes "
             "(the file was edited after the lock, as the lock text allows); `-` the lock does not list the path (the file is newer, or was not tracked then).", "",
             "To check a file: `sha256sum <path>` and compare with the row, then with the line for the path in the hash block of the lock manifest "
             "as it stood at the lock's tag (this package's copy of the manifest holds the last lock's block only)"
             + (("; `lock-records/<tag>.files` lists each lock's files with git's own blob ids, and `lock-records/<tag>.commit` (and `<tag>.tag`, the tag object) is the lock "
                 "commit's object, whose SHA-1 is the commit id below).") if with_records else ")."), ""]
    lines += ["| Lock | Commit | Files in its tree |", "|---|---|---|"]
    lines += [f"| {t} | `{r['commit']}` | {r['files']} |" for t, r in records.items()]
    lines += ["", "| File | SHA-256 | " + " | ".join(LOCKS) + " |", "|---|---|" + "---|" * len(LOCKS)]
    for r in sorted(rows, key=lambda r: str(r["path"])):
        lk = r.get("locks") or {}
        lines.append(f"| `{r['path']}` | `{r['sha256']}` | " + " | ".join(sym.get(lk.get(t, "absent"), "-") if lk else "n/a" for t in LOCKS) + " |")
    lines += ["", "`n/a`: the file is not under git (a run folder's own table or record), so no lock lists it."]
    return "\n".join(lines) + "\n"


def citation_files() -> Dict[str, str]:
    """`.zenodo.json` and `CITATION.cff` (named package only; D-205, D-209). The code's licence is MIT (D-204); the data's licence (CC BY 4.0)
    is stated in the README and LICENSE-DATA. The arXiv id and the Zenodo DOI do not exist yet: they are left out, to add at the release."""
    names = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
    PAPER_TITLE, REPO_URL, AUTHORS = names["title"], names["repo_url"], [tuple(a) for a in names["authors"]]
    zenodo = {"title": PAPER_TITLE, "upload_type": "software", "license": "MIT",
              "creators": [{"name": f"{family}, {given}"} for family, given in AUTHORS],
              "description": "Code, data and pre-registrations for the paper: how to spend a fixed budget across Claude 5.5 models (a bigger model, "
                             "more thinking, more samples, or a team), on synthetic multi-step puzzles."}
    cff = ["cff-version: 1.2.0", "message: \"If you use this repository, please cite the paper.\"", f"title: \"{PAPER_TITLE}\"", "type: software", "authors:"]
    for family, given in AUTHORS:
        cff += [f"  - family-names: \"{family}\"", f"    given-names: \"{given}\""]
    cff += ["license: MIT", f"repository-code: \"{REPO_URL}\""]
    return {".zenodo.json": json.dumps(zenodo, indent=2, ensure_ascii=False) + "\n", "CITATION.cff": "\n".join(cff) + "\n"}


MIT = """MIT License

Copyright (c) 2026 {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
DATA_HEADER = """All files in this repository other than the code covered by LICENSE (the result files, per-call tables, run records, lock records,
plans and pre-registrations, the paper's tables and figures, and the supplement) are licensed under the Creative Commons Attribution 4.0
International licence (CC BY 4.0). The code is under the MIT licence (see LICENSE). The licence text below is the official legal code from
https://creativecommons.org/licenses/by/4.0/legalcode.

"""
SUPPLEMENT_PATH = "supplement.pdf"          # where the final supplement PDF sits in the package (D-178): --supplement <file>


def licence_files(kind: str) -> Dict[str, str]:
    """`LICENSE` (MIT, D-204; D-214: the copyright line names the first author only; the anonymous ZIP says "Anonymous authors", D-150) and
    `LICENSE-DATA` (CC BY 4.0, the official legal code kept in harness/licences/)."""
    holder = "Anonymous authors"
    if kind == "named":
        family, given = json.loads(NAMES_FILE.read_text(encoding="utf-8"))["authors"][0]
        holder = f"{given} {family}"
    legal = (Path(__file__).with_name("licences") / "CC-BY-4.0.txt").read_text(encoding="utf-8")
    return {"LICENSE": MIT.format(holder=holder), "LICENSE-DATA": DATA_HEADER + legal}


GITATTRIBUTES = ("# Edith's P4: git must not change a line ending, or every SHA-256 in this repository (data/paper-outputs/MANIFEST.json,\n"
                 "# LOCKED-FILES.md, ops/lock/LOCK-MANIFEST.md) fails in a default Windows clone.\n* -text\n")


def pkg_path(row: Mapping[str, object]) -> str:
    """Where a released file sits in the package: a git file at its own path, a run folder's file under data/."""
    return str(row["path"]) if row["where"] == "git" else "data/" + str(row["path"])


def refusing_hits(doc: Mapping[str, object], cleared: Sequence[str] = (), kind: str = "named") -> List[str]:
    """Counts-only list of released files that still show an email or a secret after KNOWN explained its exact count (Edith: the privacy
    gate stops the package; no ruling accepts either in the tree)."""
    bad = []
    for row in doc["files"]:                                                                   # type: ignore[union-attr]
        if row["decision"] != IN or (kind == "tmlr" and row.get("named_only")):
            continue
        if row.get("gate", {}).get("held") and row["path"] not in cleared:                     # held: not written
            continue
        for cat in ("emails", "secrets"):
            n = (row.get("scrub") or {}).get(cat)
            if n:
                bad.append(f"{pkg_path(row)}: {cat} {n}")
    return bad


def require_runs(doc: Mapping[str, object]) -> None:
    """A package without a run folder would be missing the per-call tables D-149 releases: refuse, naming the runs."""
    missing = [r for r in RAW_RUNS if r not in doc.get("raw_runs", [])]                          # type: ignore[operator]
    if missing:
        raise SystemExit(f"--package needs every run folder under --raw; missing: {', '.join(missing)}")


def package(doc: Mapping[str, object], raw: Optional[Path], dest: Path, kind: str, adds: Sequence[str], cleared: Sequence[str],
            supplement: Optional[Path] = None) -> Dict[str, object]:
    """Write the fresh copy: every IN file (the pinned version for PINNED_EXTRAS), the locks' bare records, the supplied files (--add) and
    the mapping note. A GATED file with a refusing hit is held out unless its path is in `cleared`. kind "tmlr" leaves out the
    named-package-only files. Refuses a non-empty folder, any email or secret that KNOWN does not explain in a released file, and a
    supplied file that would replace a released or generated one."""
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} is not empty")
    stray = [c for c in cleared if c not in GATED]
    if stray:
        raise SystemExit(f"--cleared names a file that is not gated: {', '.join(stray)}")
    bad = refusing_hits(doc, cleared, kind)
    if bad:
        raise SystemExit("not written: a released file shows an email or a secret (counts only): " + "; ".join(bad))
    if supplement is not None:
        adds = [*adds, f"{SUPPLEMENT_PATH}={supplement}"]
    generated = [*licence_files(kind), ".gitattributes", "LOCKED-FILES.md", "RELEASE-FILES.json"]
    if kind == "named":                                                                        # the anonymous ZIP names neither the repository nor the authors (D-150)
        generated += [*citation_files(), "lock-records/"]
    taken = {pkg_path(r) for r in doc["files"] if r["decision"] == IN} | set(generated)        # type: ignore[union-attr]
    supplied = []
    for spec in adds:
        name, _, src = spec.partition("=")
        if not name or not src or Path(name).is_absolute() or ".." in Path(name).parts:
            raise SystemExit(f"--add wants DEST=SRC with a relative DEST, got {spec!r}")
        if name in taken or any(name.startswith(g) for g in generated if g.endswith("/")):
            raise SystemExit(f"--add {name}: a released or generated file has that path")
        data = Path(src).read_bytes()
        try:
            n = sum(len(p.findall(data.decode("utf-8"))) for p in PATTERNS["secrets"])        # a supplied text file is scanned for secrets too
        except UnicodeDecodeError:
            n = 0
        if n:
            raise SystemExit(f"--add {name}: {n} secret-like strings (counts only)")
        supplied.append((name, data))
    dest.mkdir(parents=True, exist_ok=True)
    commit = str(doc["commit"])
    written: List[Dict[str, object]] = []
    held: List[str] = []
    for row in doc["files"]:                                                                   # type: ignore[union-attr]
        if row["decision"] != IN:
            continue
        if kind == "tmlr" and row.get("named_only"):
            continue
        if row.get("gate", {}).get("held") and row["path"] not in cleared:
            held.append(str(row["path"]))
            continue
        target = dest / pkg_path(row)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = read(commit, raw, row)
        sha = hashlib.sha256(data).hexdigest()
        if row.get("sha256", sha) != sha:
            raise ValueError(f"{row['path']}: the bytes written are not the bytes the manifest hashed")
        target.write_bytes(data)
        written.append(dict(row, path=pkg_path(row), sha256=sha, bytes=len(data)))             # listed at the path it has in the package (Edith's P3)
    listed = []
    for name, data in supplied:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        listed.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    for name, text in licence_files(kind).items():
        (dest / name).write_text(text, encoding="utf-8")
    (dest / ".gitattributes").write_text(GITATTRIBUTES, encoding="utf-8")
    if kind == "named":
        for name, text in citation_files().items():
            (dest / name).write_text(text, encoding="utf-8")
    records = lock_records(dest if kind == "named" else None)                                 # the commit objects name the authors: not in the anonymous ZIP (D-150)
    (dest / "LOCKED-FILES.md").write_text(locked_files_note(doc, written, records, kind == "named"), encoding="utf-8")
    listing = {"commit": commit, "kind": kind, "files": [{k: r[k] for k in ("path", "sha256", "bytes", "rule") if k in r} | ({"pinned": r["pinned"]} if "pinned" in r else {})
                                                             for r in written], "supplied": listed, "generated": generated, "held": held, "cleared": sorted(cleared), "lock_records": records}
    (dest / "RELEASE-FILES.json").write_text(json.dumps(listing, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"written": len(written), "supplied": len(listed), "generated": generated, "held": held}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--commit", required=True)
    ap.add_argument("--raw", type=Path, default=None, help="the data/raw folder holding the run folders (outside git)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--package", type=Path, default=None, help="also write the fresh copy to this empty folder (D-207)")
    ap.add_argument("--kind", choices=("named", "tmlr"), default="named", help="tmlr leaves out the named-package-only files (the anonymiser's patterns)")
    ap.add_argument("--add", action="append", default=[], metavar="DEST=SRC", help="a file the tree does not hold (the public README, the licences, the supplement PDF)")
    ap.add_argument("--supplement", type=Path, default=None, help=f"the final supplement PDF (D-178); written to {SUPPLEMENT_PATH} in the package")
    ap.add_argument("--cleared", action="append", default=[], metavar="PATH", help="a GATED file whose privacy check Edith cleared although it has hits")
    a = ap.parse_args(argv)
    if not (ROOT / ".git").exists():
        raise SystemExit("release.py builds the package from the development repository's git history (the locks' tags, every file at a commit) "
                         "and the original run folders; this copy has neither, so it cannot run here.")
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit(f"{a.out} is not empty")
    a.out.mkdir(parents=True, exist_ok=True)
    doc = build(a.commit, a.raw)
    (a.out / "release-manifest.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if a.package is not None:
        require_runs(doc)
        print(json.dumps({"package": package(doc, a.raw, a.package, a.kind, a.add, a.cleared, a.supplement)}, indent=1))
    print(json.dumps({"summary": doc["summary"], "files_with_refusing_hits": doc["files_with_refusing_hits"],
                      "test_states_compared": doc["test_states_compared"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
