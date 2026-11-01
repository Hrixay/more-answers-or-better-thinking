"""Shows the client/batch tests can fail: apply one deliberate break at a time, expect the suite to go red, restore.
    python3 -m harness.tests.mutate
"""
import subprocess
import sys
from pathlib import Path

MUTATIONS = [
    ("client.py", "halt_reason=reason", "halt_reason=\"\"", "model mismatch no longer halts"),
    ("batch.py", "except ConsoleCheckNeeded as e:", "except ZeroDivisionError as e:", "console check stop not handled"),
    ("client.py", "kwargs = {\"free_by_rule\": True} if free else {}", "kwargs = {}", "free refusals not flagged for the Console check"),
    ("client.py", 'final=(e.billed != "no")', "final=True", "rejected call treated as finished"),
    ("client.py", "self.guard.commit(key, Usage(), batch=False,", "print(key, batch=False,", "rejected call never settled"),
    ("client.py", "self.guard.reserve(key,", "self.guard.reserve_free(key,", "reserve skipped (call renamed)"),
    ("client.py", "assert_clean(params)\n        meta", "meta", "request rules not checked"),
    ("batch.py", "guard.commit(keys[cid], Usage(), batch=True, note", "print(keys[cid], note", "errored batch item never settled"),
    ("batch.py", "keys[cid], outcome, batch=True", "keys[cid], outcome, batch=False", "batch priced at list"),
    ("batch.py", "done = log.finished_ids()\n    todo", "done = set()\n    todo", "finished items re-sent"),
    ("batch.py", "_refuse_orphans(log)\n    if not resend:", "if not resend:", "orphaned batch not refused"),
    ("batch.py", "    if not resend:\n        still_open", "    if False:\n        still_open", "open keys do not block resubmission"),
    ("transport.py", "api_key = load_api_key(env_file if", "api_key = None or (env_file if", "API key never loaded"),
    ("batch.py", 'if guard.status(keys[cid]) != "open":', "if False:", "settled results paid twice on resume"),
    ("batch.py", "wave_spec = guard.plan_waves(plan_in, max_wave_size=max_wave_size)[0]", "wave_spec = plan_in", "no wave planning"),
    ("client.py", "and not resend:", "and False:", "resend guard removed"),
    ("transport.py", "check_sdk_pin(anthropic, requirements)", "pass", "SDK pin not checked"),
    ("transport.py", "if e.status_code < 400:", "if False:", "status below 400 treated as rejected"),
    ("outcome.py", 'elif stop == "refusal":\n        kind = "refusal"', 'elif stop == "refusal":\n        kind = "answered"', "refusal counted as answer"),
    ("outcome.py", 'elif stop == "max_tokens":\n        kind = "truncated"', 'elif stop == "max_tokens":\n        kind = "answered"', "truncation counted as answer"),
    ("apicheck.py", 'if out.kind == "refusal":', "if False:", "check does not stop at a refusal"),
    ("apicheck.py", "N_BASE = 5", "N_BASE = 4", "check set size not enforced"),
    ("apicheck.py", "except (CapExceeded, GuardHalted) as e:", "except ZeroDivisionError as e:", "guard stop not reported as incomplete"),
    ("apicheck.py", "if cid in done:", "if False:", "finished check calls re-sent"),
    ("apicheck.py", 'if before["refused"]:', "if False:", "check re-run after a refusal"),
    ("apicheck.py", 'if before["finished"] and not resume_incomplete:', "if False:", "check resumed without the flag"),
    ("apicheck.py", "except ModelMismatch as e:", "except ZeroDivisionError as e:", "model mismatch not reported as incomplete"),
]


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "pareto"
    bad = 0
    for fname, old, new, why in MUTATIONS:
        path = root / fname
        src = path.read_text()
        if old not in src:
            print(f"SKIP (pattern not found): {why}")
            bad += 1
            continue
        path.write_text(src.replace(old, new, 1))
        try:
            r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "harness/tests", "-t", ".", "-p", "test_[!l]*.py"],      # not test_ledger.py: minutes of generator work, nothing in harness/pareto
                               capture_output=True, text=True, cwd=root.parents[1])
        finally:
            path.write_text(src)
        caught = r.returncode != 0
        print(("caught   " if caught else "MISSED   ") + why)
        bad += 0 if caught else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
