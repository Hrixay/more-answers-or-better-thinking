# harness/pareto: prices and the spend guard

Friday's code, reviewed by Edith before any paid run. Standard library only, Python 3.9. Nothing in
`prices.py` or `guard.py` touches the network or reads environment variables.

| File | What it does |
|---|---|
| `markers.py` | Bookkeeping for an earlier run's free refusals (D-65): `plan` reads, `apply` appends `free_by_rule_marked` events through the guard. No API call, no new spend. |
| `prices.py` | The pinned price table (`PRICE_TABLE_DATE = "2026-10-11"`, from `research/facts-checked.md`), `Usage`, `cost()` from reported usage, `worst_case()` for reservations, and `estimate_input_tokens()`. Money is `Decimal` only, and any rounding raises. |
| `guard.py` | `SpendGuard`: dry run by default, worst-case reservations, run cap and global cap, halts, the live gate, the ledger and crash recovery. Also `read_spent_from_spend_log()`. |
| `request.py` | Builds and checks the parameters of a call (effort always set, adaptive thinking, "off" only for Haiku at high or below, no temperature, top_p, top_k, tool_choice, tools, prefill or other extras). `assert_clean` re-checks any params dict. |
| `outcome.py` | Turns a reply into an `Outcome`: answered, empty, refusal, truncated or unexpected stop. Only "answered" is a success. Keeps the raw usage object. |
| `calllog.py` | Append-only JSONL call log (`data/raw/<run-id>/calls.jsonl`, git-ignored, D-37). A line is written for every attempt, including failures. |
| `transport.py` | `DryTransport` (default, no network, no SDK import), `FakeTransport` (tests), `RealTransport` (the only file that imports `anthropic`; refuses unless `guard.require_live()` passes; SDK retries off). |
| `client.py` | `Client.call`: rules check, reserve, `mark_sent`, send, log, commit. Refusals and truncations are billed failed calls, never retried. A wrong returned model halts the guard. Only 429/5xx rejections are retried (each attempt reserved, logged, keyed). A dropped connection stays open and is never re-sent. |
| `batch.py` | `run_batches`: waves from `plan_waves`, results matched by `custom_id`, the batch id logged before polling, resume without re-submitting, errored/expired items committed at zero with a note and listed for Console reconciliation. |
| `limits.py` | Proposed pilot `max_tokens` per family and model (non-binding; no automatic re-run: that is pilot-only until item 5 rules). |
| `manifest.py` | The run manifest: git commit and dirty flag, source hash, price-table date, hash of the item set. Refuses to overwrite. |
| `s3check.py` | The S3 check Batch: one Batch of 5 fixed items on `smoke3-ledger-l16-v1`, billed enough for the Console to show it. Never records a Console check. |
| `table.py` | The compact per-call CSV that goes in git, and per-model block rates (the D-36 2% check; reports, never switches by itself). |
| `../tests/` | Offline tests. `python3 -m harness.tests.mutate` breaks the client, batch and outcome code on purpose, one thing at a time, and confirms the tests go red. |

Run the tests from the repo root: `python3 -m unittest discover -s harness/tests -t .`

## Prices

- `cost(model, usage, batch)`: exact billed cost. Haiku's long-prompt row applies to the WHOLE request
  (output included) when the prompt (input + cache reads + cache writes) is over 100,000 tokens.
  Batch halves every rate.
- `worst_case(model, est_input_tokens, max_tokens, batch)`: the most a call could cost. Prompt tokens
  are priced at the dearest input-side rate (the 1-hour cache write, 2x input), and output at
  `max_tokens`. For Haiku, an estimate over 90,000 is priced on the long-prompt row, a safety band
  below the 100,000 line. `batch=True` halves it.
- `estimate_input_tokens(text)`: UTF-8 bytes // 2 + 100, an upper-bound guess with no tokenizer.

## The lifecycle of one call

```
reserve(key, ...)  ->  mark_sent(key)  ->  network call  ->  commit(key, usage, note=...)
        \-> release(key)   only BEFORE mark_sent, for a call that never went out
```

- `reserve` books the worst case: at **list** price for a real-time call, at the **Batch price** (half
  of list) for `batch=True`. It refuses (`CapExceeded`) unless spent + open reservations + this one
  fit under the run cap **and** the global cap. `reserve_many` books a wave, all or nothing.
- **The Batch price is checked once, for the whole machine, against the Console (T1, U1-U3).** Batch
  items are committed at the Batch price, so a commit alone would not notice Batch billed at list.
  The gate applies to live guards only; real-time calls and dry guards are never gated.
  - **Before a passing check (U2):** the Batch reservations of all live runs together, at their
    worst case, may not pass **$1**, whatever became of them (answered, errored, expired, or a
    crash). So the smoke's Batch ($0.29) goes; the pilot's waves ($29.93) wait for the check.
  - **The check:** `record_console_check(dollars_seen: Decimal, note: str) -> None`, on any live
    guard with a valid clearance (it runs `require_live()` first, V2; it reads every live ledger under
    the shared root). `dollars_seen` is the Console's TOTAL
    cost since the first live run on this machine; it is compared with the spend of all live ledgers
    (real-time + Batch). Refused, with nothing recorded: if a Batch key is open in any live ledger;
    if no live ledger has a committed Batch item; if Batch spend across ALL live ledgers is under
    **$0.05** (a fixed constant; U3); and, as `ConsoleNotUpdated`, if the Console shows under 95% of
    the ledger total (wait and try again).
  - **Refusals that are free by rule (S2).** `commit(..., free_by_rule=True)` marks a refusal that
    billing rule B5 bills at $0 (before any output, in the cyber, general_harms or no category). Its
    amount stays the full usage cost, so spend and the caps are unchanged (conservative); the flag
    only takes it out of `guard.rule_adjusted_spent`. The Console check compares with the
    B5-ADJUSTED total of all live ledgers (both the 95% floor and the 5% + 1 cent ceiling), and the
    check line records `ledger_total` (adjusted) and `raw_total`. The $0.05 floor applies to BILLED
    Batch spend (free Batch refusals taken out; P1), and the line records `batch_billed` and
    `batch_raw`; a pass read from another ledger must match all four figures to that ledger's own
    commits (P2).
  - **Ledgers written before the flag existed (P3, smoke-2).** `guard.mark_free_by_rule(key, category,
    note)` appends a `free_by_rule_marked` event to the SAME ledger as the commit. It needs a live guard
    on that run (replay it) with a valid clearance (`require_live()` first), a B5-free category (cyber,
    general_harms, none), a note citing the call-log evidence, and a commit that reported 0 output
    tokens and is not free already. Replay, `scan_ledger` and the N61 rule honour it; a marker that
    fails these rules makes its own ledger refuse to replay and is ignored by other runs. A Console above the adjusted total by
    more than 5% + 1 cent FAILS even if it is at or under the raw total: either Batch billed at list
    or a "free" refusal was billed, and a human decides.
  - **Passing** (Console at most 5% + 1 cent over the adjusted ledgers; our choice, not a sourced
    figure) opens the gate for every run. At list, Batch spend X shows as 2X, which fails for X over ~$0.0105.
  - **Failing (U1)** is recorded, halts that run, and blocks EVERY live Batch reservation on the
    machine, small or large, in any run. A human finds out why, then calls
    `clear_console_block(note)` on a live guard with a valid clearance (`require_live()` first, V2):
    it writes a `console_halt_cleared` event naming each failed check it clears AND voiding every
    passing check recorded so far (V1). Clearing does not un-halt the failed run and does not open the
    gate; a NEW passing check is needed for anything over the $1 limit.
  - **Passes read from other ledgers (N61):** a pass found in another run's ledger counts only if it
    claims a ledger total and Batch spend of at least $0.05 and its ledger total and `spent` equal that
    ledger's own commits before it. A line that claims to pass but fails the figures counts as a FAILED
    check (it blocks); a pass that is not about its own ledger alone is ignored. So the smoke's check
    (made when it is the only live ledger) opens the gate for every later run; a check recorded while
    other live ledgers exist counts only inside its own run, and a later run records its own.
  - **Batch spend under $0.05 (U3):** the check cannot be recorded yet, and nothing deadlocks while the
    Batch reservations stay under $1: run one more small Batch (a few Opus items), then check. If $1
    of reservations is used up with under $0.05 spent (everything errored), Batch is not working;
    stop and investigate. That fails closed.
- `mark_sent` / `mark_sent_many` are called immediately before the network call (one Batch
  submission = one `mark_sent_many`, all or nothing). In live mode they run `require_live()` first.
  After them, `release` is refused.
- `commit` replaces the reservation with the real cost. Refusals, truncations and errors that report
  usage are committed like any answer; `note` explains a zero-cost commit. `batch=False` on a Batch
  reservation prices it at list (allowed: it can only cost more); `batch=True` on a real-time one is
  refused. A sent call with no usage stays open, counted at its worst case, until a human resolves it.
- If a commit costs more than its reservation (for example a Batch item billed at list), or spend
  passes a cap, the guard **halts**: no more `reserve` or `mark_sent`. `commit` and `release` still
  work. A halt that follows a reply (a model mismatch) goes in `commit(..., halt_reason="...")`, which
  writes the commit and the halt in ONE ledger write; replay honours it. `halt(reason)` is for halts
  with no reply to commit.
- `plan_waves(requests, max_wave_size)` splits a big run into consecutive waves that each fit what is
  left. Run the first wave, commit it, then plan again.
- For callers: `status(key)` ("open", "committed", "released" or None), `used_keys()`, `open_keys()`,
  `sent_unsettled_keys()`, and `summary(keys)` (`reserved`, `committed`, `open`, `done`) to log a wave.

## Live guards and global spend

A dry guard (the default) is given `global_spent_usd` explicitly; there is no default. A live guard:
- keeps every ledger and the live-run lock under ONE root for all checkouts and worktrees (R1): the
  main checkout's `data/`, found from `git rev-parse --git-common-dir` (`shared_data_root`);
- always uses the ledger `<root>/raw/<run_id>/ledger.jsonl` (`ledger_path_for`), and refuses a fresh
  start when that ledger already has events (`SpendGuard.replay` is the only way back);
- holds an exclusive lock on its ledger and the one live-run lock `<root>/raw/.live.lock`, so only one
  live run on this machine spends at a time (`LedgerBusy` otherwise); `close()` releases both;
- adds up earlier spend **per run** (R2): for each Run ID, the larger of its rows in
  `ops/spend-log.md` (the "USD (computed)" column) and its live ledger's spent + open reservations;
  rows with no ledger and ledgers with no row count too. The rows must add up to "Spent (rows below)".
  If a row and its ledger differ, the start is refused until the row's Notes say
  `ledger-ok: <the ledger's figure>`, meaning a human reconciled the two against the Console.
  Never delete a ledger.

`repo_root`, `data_root`, `git` (a function that runs git) and `now` can be injected for tests.

## The live gate

`require_live()` raises `NotLive` unless `live=True` and the clearance file passes every check:

```json
{
  "run_id": "s1-pilot-01",
  "cap_usd": "30.00",
  "ledger_root": "/Users/hrixay/Desktop/pareto/data",
  "env_file": "/Users/hrixay/Desktop/pareto/.env",
  "git_commit": "0123abc",
  "price_table_date": "2026-10-10",
  "expires": "2026-10-11T18:00:00Z",
  "edith_clearance": "ops/reviews/2026-10-10-clearance-s1-pilot-01.md",
  "user_go": "go: run the pilot (user, in Jarvis's chat, 2026-10-10)"
}
```

- `run_id` and `cap_usd` match the guard exactly; `ledger_root` is an absolute path equal to the
  guard's shared root (R1).
- `env_file` (T6) is the absolute path `<main checkout>/.env`, where the main checkout is the parent of
  the shared root (the same git-common-dir logic). After the gate passes it is exposed as
  `guard.env_file` (a `Path`) for `RealTransport`. The guard only compares the path; it never opens,
  reads or stats the file.
- `git_commit` (7 to 40 hex characters) is HEAD, and the whole checkout has no uncommitted or
  untracked file outside `data/raw/` and `ops/reviews/` (R11, T7: `data/tasks/` counts). Git runs with
  an empty environment. The check runs once per guard, because the running code was loaded at start.
- `price_table_date` equals `prices.PRICE_TABLE_DATE`, and that date is today or yesterday (UTC).
- `expires` has not passed and is at most 7 days away (an ISO date alone means the end of that UTC day).
- `edith_clearance` is a file under `ops/reviews/` with a line, from the first column and with nothing
  before or after it, exactly `CLEARED: <run_id> <git_commit> <ledger_root>` (T5, T7), e.g.
  `CLEARED: s1-pilot-01 0123abc /Users/hrixay/Desktop/pareto/data`.
- `user_go` starts with `go:` followed by the user's words (Edith checks the words by eye).

The file is re-read on every check, so deleting it stops further sends.

## Ledger and crash recovery

Every event (open, reserve, send, commit with its usage and any halt_reason, release, halt,
console_check (with `passed` and `ledger_total`), console_halt_cleared, recover, torn_line_dropped) is
appended as one JSON line, fsynced, **before** memory changes. Amounts are strings. After a crash,
`SpendGuard.replay(path, run_id, run_cap, ...)` rebuilds the exact state. It recomputes every halt
from the commits themselves, drops a torn final line (no newline) with a warning and records it in
the next line, and refuses a gap, a changed amount, a broken middle line or another run's lines.
`recover()` lists the reservations left open. They still count as spent until a human commits their
real usage or, if they were never sent, releases them.

## Round 1 fixes on the client side (Edith's H3, H4, M1–M5; N46–N51)

- **Refuses to send twice.** `Client.call` raises `AlreadySent` for a `custom_id` that is finished or still has an open
  reservation (a dropped connection leaves one). `resend=True` is for after a Console check and is logged.
- **Keys come from the guard.** Real-time keys are `<custom_id>#a<n>` and batch keys `<custom_id>@<n>`, n the smallest number
  `guard.used_keys()` has not used.
- **Batch order and crashes.** reserve all → `mark_sent_many` → log `batch_submitting` → submit → log `batch_submitted` → poll →
  settle → log `batch_collected` (with the wave's reserved and committed amounts, for the Console check Edith asked for).
  A failed submit logs `batch_submit_failed` (billed unknown) and the keys stay open. A crash between `batch_submitting` and the
  batch id leaves an orphan: `run_batches` raises `OrphanedBatch` until a human records the batch (find it with the SDK's
  `messages.batches.list()` or the Console) or releases the keys with a note. Results already settled are skipped on resume.
  The run plans one wave at a time against the room left.
- **Only `run_batches` reserves at the Batch price.** `Client.call` always reserves at list (tested). The first cleared run must
  include a small batch and its cost reconciled with the Console before the next wave.
- **Errors.** A reply error after the stream starts, a timeout, a dropped connection or a status below 400 is "billed unknown":
  reserved, never retried. Any other exception after a call is marked sent is logged the same way and re-raised.
- **SDK pin.** `harness/requirements.txt` must pin `anthropic==X.Y.Z` and that exact version must be installed, or `RealTransport`
  refuses to start. The manifest records the installed version. Pinned: `anthropic==0.125.0` (2026-08-19, the newest release that supports Python 3.9, which is the only Python on this machine; every 1.x release needs Python 3.10 or later; the reason and the wheel checksum are in the file). The harness and its tests run on Python 3.9 or later. Edith checks the pin.
- **Block rates** also count errors that name a safety or policy reason (by `error:<type>`). Logs carry `http_request_id`
  (from the response) as well as the message id, and flag any cache write as an anomaly (we never ask for caching).
- **Call `guard.close()`** (or use `with`) at the end of a run; it releases the ledger and live-run locks.

## Round 3 (Edith T1-T7): running it live

- `python3 -m harness.pareto.smoke live --set SET --run-id ID --cap 2 --clearance FILE` and
  `python3 -m harness.pareto.pilot live --sets SET... --run-id ID --cap 30 --clearance FILE [--rt-set SET]` need an explicit `--cap`.
  A live run writes its call log, manifest and compact table next to its ledger, `<shared data root>/raw/<run-id>/`, and refuses `--out`.
  If that ledger already exists the guard is replayed, so the same command resumes a run that stopped.
- The first Batch wave on the machine stops the run (`stopped_for_console_check`) until the Console figure for that run is recorded:
  `python3 -m harness.pareto.pilot console-check --run-id ID --cap C --clearance FILE --usd 1.23 --note "Console, Usage page, time"`.
  The guard needs the run's Batch spend to be at least $0.05, no open Batch keys, and the Console total (real-time plus Batch since the
  run started) to be at least 95% of the ledger; it halts if the Console shows more than the ledger by over 5% + 1 cent. The Console shows
  cost by day, so pick a window that covers only this run.
- The API key is read from the `.env` the clearance names (`env_file`, the main checkout's `.env`), only inside `RealTransport`, after the
  gate and the SDK pin. `ANTHROPIC_BASE_URL` is refused unless it is `https://api.anthropic.com`; the client is built with that address.
- Run everything with the venv: `/Users/hrixay/Desktop/pareto/.venv/bin/python -m harness.pareto.pilot ...` (the SDK is installed there only).

## The S3 check Batch (`s3check.py`)

```
python3 -m harness.pareto.s3check plan --set SET_DIR
python3 -m harness.pareto.s3check dry  --set SET_DIR --run-id s3-dry --out DIR
python3 -m harness.pareto.s3check live --set SET_DIR --run-id ID --cap X --clearance FILE
python3 -m harness.pareto.s3check live --set SET_DIR --run-id ID --cap X --clearance FILE --collect   # after an interruption
```

- **What it sends:** ONE Batch of 5 requests on `smoke3-ledger-l16-v1` (S3 plan revision 4, Proposal A), fixed in code and in
  this order: base 0 1x24 Opus, base 0 24x1 Opus, base 1 1x24 Opus, base 2 1x24 Sonnet, base 2 24x1 Sonnet. Effort medium,
  adaptive thinking, `max_tokens` 15,000. Expected bill about $0.27 to $0.38, so the Console can show it; worst case about $0.68
  at the Batch price, inside what is left of the $1 unchecked-Batch limit.
- **Refuses** a set whose `set_id` is not `smoke3-ledger-l16-v1`, or whose family is not ledger or setting not l16 (the set is
  loaded with the same deep verify as every runner). It sends nothing if the 5 items do not fit in one wave under the cap.
- **`plan`** prints each item with its worst case (as the guard reserves it: Batch price, `estimate_input_tokens` of the
  prompt), the total and the cap to ask for (the total rounded up to the next 10 cents; Edith sets the figure).
- **`live`** needs an explicit `--cap` and `--clearance`, refuses `--out`, opens its guard with `live.open_live_guard` and
  writes next to its ledger, `<shared data root>/raw/<run-id>/`. The Batch goes through `batch.run_batches`.
- **No second send.** A run folder that already shows the Batch (a finished item, a Batch submit record, a reservation for one
  of the items in the ledger, or `s3_result.json` with items sent) is refused (`S3NotRerun`). There is no resend flag: the
  user decides what happens next.
- **Interrupted after the submit (Edith S3-1, S3-3).** If the run stops after the submit (sleep, shutdown, Ctrl-C, a
  connection dropped while waiting or while reading results), `s3_result.json`
  says `interrupted` and a plain `live` refuses and points to `--collect`. `live --collect` (same `--cap` and `--clearance`)
  collects that Batch so its cost reaches the ledger. It never submits: it goes on only if the call log shows exactly one
  submitted, uncollected Batch whose keys are exactly the five S3 items, no failed submit and no orphan (a submit with no
  batch id); afterwards it checks that no new submit was logged, and raises if one was. Results already read before the
  stop are skipped and never paid twice; once the Batch is marked collected, `--collect` refuses.
- **Exit code:** 0 only when the status is `complete`; 2 for any other status (`not_sent`, `stopped_for_console_check`,
  `incomplete`; the summary says why), 3 when the API refused the submit, 4 when nothing was sent because the folder already
  shows the Batch (or, with `--collect`, there is nothing to collect).
- **The summary** `s3_result.json`: status, reason, items planned and sent, kinds (answered, refusal, truncated ...), spent,
  batch ids, per-item stop reason and output tokens. Never the answer text; S3 answers are not graded (excluded from every analysis).
- **The Console check is not recorded here (Edith N67).** After the S3 Batch settles and the Console shows it, the passing
  Console check is recorded with `python3 -m harness.pareto.pilot console-check` under the PILOT's own run id, before the
  pilot's first wave; a check recorded under the S3 run id does not carry over.

## The main run (`main.py`): runbook for a multi-hour run

Written for `main-l14n6-1` (Edith's clearance and its Addendum 2). Every step uses the cleared commit, the venv's Python and nice 19.

**1. Where it runs.** One clean checkout detached at the cleared commit, in a folder that survives a reboot (NOT the session
scratchpad under /private/tmp, which a restart wipes), for example `git worktree add --detach ~/Desktop/pareto-run-<commit7> <commit>`.
Copy the clearance `.md` and `.json` into its `ops/reviews/`, untracked; `git status --porcelain` shows only those two files. The run
folder is `<data root>/raw/<run-id>/` (the data root is outside the checkout, so it survives too).

**2. Launch, detached, logging to the run folder, the Mac kept awake:**

    RUN=/Users/hrixay/Desktop/pareto/data/raw/main-l14n6-1; mkdir -p "$RUN"
    cd ~/Desktop/pareto-run-<commit7>
    caffeinate -i nice -n 19 nohup /Users/hrixay/Desktop/pareto/.venv/bin/python -m harness.pareto.main live \
        --set data/tasks/main-ledger-l14n6-v1 --run-id main-l14n6-1 --cap 100 \
        --clearance ops/reviews/2026-10-12-clearance-main-l14n6-1.json --extras sl,ho,hx >> "$RUN/runner.log" 2>&1 &
    echo $! > "$RUN/runner.pid"

`caffeinate -i` keeps the Mac from idle-sleeping while the run lives; keep it on mains power. Watch only `runner.log`, the ledger
and counts (kinds, stop reasons, refusal and truncation counts, tokens, costs, latency, E3's decided / at-cap counts): no answer, no
`right` column, no accuracy (the clearance addendum).

**3. If it stops, look at the last lines of `runner.log`, then:**
- **A dropped network, a crash, a killed process or a reboot:** run the SAME command again (step 2). Finished calls are never sent
  twice; a submitted, uncollected batch is collected, not re-submitted; the single-call waves and E3's rounds each settle only their
  own batches; E3 rebuilds its rounds from the call log. Reads retry a dropped connection for about an hour before stopping.
- **`OrphanedBatch`** (a crash between "submitting" and "submitted"): the error names the wave id. Find the batch
  (`client.messages.batches.list()` or the Console, by time and request count), then run exactly ONE of these from the run checkout,
  replacing only `<WAVE_ID>`, `<BATCH_ID>` and `<NOTE>`; then the same command as in step 2.
  - The batch exists, so adopt it (it is collected, never re-sent):

        /Users/hrixay/Desktop/pareto/.venv/bin/python -c "from harness.pareto.batch import adopt_orphan; from harness.pareto.calllog import CallLog; adopt_orphan(CallLog('/Users/hrixay/Desktop/pareto/data/raw/main-l14n6-1/calls.jsonl'), '<WAVE_ID>', '<BATCH_ID>')"

  - No batch exists (checked), so close it (its keys commit zero usage with the note; the items go again under new keys):

        /Users/hrixay/Desktop/pareto/.venv/bin/python -c "from decimal import Decimal; from pathlib import Path; from harness.pareto.batch import close_orphan; from harness.pareto.calllog import CallLog; from harness.pareto.live import open_live_guard; g, f = open_live_guard('main-l14n6-1', Decimal('100'), Path('ops/reviews/2026-10-12-clearance-main-l14n6-1.json')); close_orphan(g, CallLog(f / 'calls.jsonl'), '<WAVE_ID>', '<NOTE>'); g.close()"

- **"STOPPED for the Console check":** record the reading with `pilot console-check` (same run id, cap and clearance), then the
  same command again.
- **"PAUSED for truncation"** (a setup truncated over 2% of a wave, checked for every settled wave, one settled on a resume included):
  nothing more is sent. Report the shares (in the log line `paused_for_truncation`) to Edith and the user. Only on the user's ruling:
  the same command with `--release-pause "<ruling>"` (go on; the next waves are still checked), or with
  `--truncation-pause-off "<ruling>"` (no more checks for this run; a pending pause is released with the same note). Both refuse an
  empty note and are recorded in the call log.
- **A guard or cap stop, a model mismatch, `STOPPED: the API did not accept a call`, open keys or `AlreadySent`:** stop; go to
  Jarvis and the user (D-60). Nothing is re-sent by hand.
- **Expiry** (the clearance's `expires`, end of 2026-10-13 UTC): the live guard will not open, so nothing is sent, polled or
  collected after it (a submitted batch waits at Anthropic, results are kept there for 29 days). Resume only after Karen's price
  re-check and a refreshed clearance, with the same command.
- **Missing results** (a submitted batch came back without some custom ids; `missing` in the summary and in its `batch_collected`
  line; their keys stay open and counted): never re-send them. Look the batch up by its batch_id at Anthropic.
  - Its results are there: mark it to be collected again, then the same command (the collect path reads them; nothing is re-sent):

        /Users/hrixay/Desktop/pareto/.venv/bin/python -c "from harness.pareto.batch import recollect_batch; from harness.pareto.calllog import CallLog; recollect_batch(CallLog('/Users/hrixay/Desktop/pareto/data/raw/main-l14n6-1/calls.jsonl'), '<BATCH_ID>', '<NOTE>')"

  - Anthropic has no result for them: do NOT use `close_orphan` (it writes "billed: no (checked)" and zero usage, which can be
    wrong for a batch that was really submitted). Stop and report to Edith and Jarvis; Edith writes that closing step if it is
    ever needed (her clearance's instruction). Until then those items stay open and are reported as missing tries (counted wrong,
    D-48 row 23).

**4. When it ends (D-48 row 23):** errored, expired or canceled items are not final; re-run the same command at most twice, before
expiry, to send them again under new keys; then stop and reconcile with the Console. Then: delete both clearance copies, write the
spend-log row (per-setup cost, refusals per model and category, truncations per setup), record the SHA-256 of `calls.jsonl`,
`compact_table.csv`, `ledger.jsonl` and `runner.log`, and report. No result is opened until the analysis driver is CLEAN and its
commit is publicly timestamped (D-93); then the driver runs once on the finished log.

## Study 1b slim runner (`slim.py`)

Built to the Study 1b spec (`research/study1b-spec.md`, Karen, frozen in lock 4 at 9c007e5: section 3 arms, section 7 trial round (wave 0 here), limits and cut, section 8 cap). The plan is a FILE,
`data/plans/study1b-plan.json`; its booking (`slim plan`) is `data/plans/study1b-plan-booking.json`.

    python3 -m harness.pareto.slim plan --plan data/plans/study1b-plan.json --cap 130 [--limits calibration_limits.json]
    python3 -m harness.pareto.slim dry  --plan data/plans/study1b-plan.json --cap 130 --run-id study1b-dry --out <scratchpad DIR>
    python3 -m harness.pareto.slim live --plan data/plans/study1b-plan.json --run-id study1b-1 --cap 130 --clearance FILE \
        --expect-plan-sha256 <the plan_sha256 `slim plan` printed, pinned in the clearance>

`--cap` is required in every mode (no default; D-102's cap is $130). `slim plan` prints the plan's `plan_sha256`; `live
--expect-plan-sha256` refuses any other plan (lock-4 audit A16). `dry --out` refuses a folder under `data/` or `research/` (this
checkout's or the main checkout's): the never-sent check searches those as text (audit A5).

**How it differs from `main.py`:**
- The arms come from the plan file, per set (one set per length: 16, 6 and 12 steps), each with its tries and EITHER a fixed
  `max_tokens` (a measured arm) OR a `calibrate` floor (an arm set by the wave-0 rule). No E3, no real-time subset, no D-42 variant.
- **Wave 0 (calibration)** goes first, in the same run (same run id, ledger and cap): every calibrated arm, one try per item on base
  puzzles 000-009 of the already-used `ladder-ledger-l14n{6,12,16}-v1` set of its length, at 64,000 (128,000 for hx at 12 and 16).
  Its custom ids carry the ladder set id (`ladder-ledger-l14n16-v1-003-16x1-hx-01`, meta `"phase": "calibration"`); it is never
  graded. The analysis must drop it by set id. No truncation pause in wave 0 (a truncation there is a measurement).
- **The limits, once:** for each calibrated arm, min(128,000, max(floor, 2 x its largest wave-0 output, rounded up to 1,000));
  128,000 if any of its wave-0 calls stopped at max_tokens. Written as ONE call-log line (`calibration_limits`) and as
  `calibration_limits.json` in the run folder; a resumed run reads them back. The rule reads only usage and stop reasons, never
  `answer_text`. The limits wait until every wave-0 call is final ("calibration_incomplete": run the same command again).
- **The cut, once, costs only (Edith S-1):** projected = wave 0's Batch cost + 1.5 x the sum over the arms left of (Batch cost per call x
  planned calls); a calibrated arm's cost per call is its wave-0 mean, a measured arm's is the plan's `cost_basis`. While projected >
  0.9 x the cap, the next part of the plan's order is cut (Opus-max at 6, Opus-xhigh at 6, Sonnet-max, Sonnet-xhigh, the 12-step point,
  Haiku-xhigh at 16); hx and om at 6 and 16 are never cut. One `cut` line. If the order runs out and projected is still over, the run
  stops ("projected_over_cap"); only on the user's ruling, the same command with `--accept-projection "<ruling>"`. The note is
  refused unless the log already holds a `cut` line with `still_over: true` and no ruling yet (Edith S-R1), so it can never be given
  before the stop it answers.
- **The test waves, confirmatory arms first (lock-4 audit A1):** hx and om at 16, then hx and om at 6, then every other arm at 16,
  then at 6, then the 12-step set. Each wave is one set's arms of one phase, under the 2% truncation pause exactly as in the main run:
  a pause returns the run to the user with no automatic change (`--release-pause` / `--truncation-pause-off`). Every confirmatory call
  must be final before any other arm is sent: an errored one stops the run ("confirmatory_incomplete"; run the same command again).
  Only the send order changed: the requests, custom ids, limits, cut and manifest are the same. The driver's completeness gate
  holds a test whose hx or om tries are not all final ("not completed", p = 1 in its Holm place, no reading).
- `live` refuses a plan marked `draft`, or with a measured arm's `cost_basis` still null, or a run id without the plan's prefix
  (`study1b-`).
- The plan is copied into the run folder at the first start (`slim_plan.json`); a later start with a different plan is refused.

**Otherwise the main runbook above applies unchanged:** the clean detached checkout, `caffeinate -i nice -n 19 nohup ... slim live
...`, watching only counts and costs, the same command after a crash (finished calls are never sent twice; each `run_batches` call
settles only its own batches; reads retry), orphans, the Console check, missing results, the window, expiry and the end-of-run steps.

## Top-up run (`topup.py`)

Built to the top-up spec (`research/topup-run-spec.md`, frozen in lock 4 at 9c007e5, Karen; Edith CLEAN), D-99 (its own window
plus Edith's same-model check), D-100 (the wording) and D-106(G) (a run cut short). The plan is a FILE, `data/plans/topup-plan.json`,
final and frozen in lock 4 (`live` refuses a plan marked `draft`).

    python3 -m harness.pareto.topup plan --plan data/plans/topup-plan.json --cap 25 [--main-run DIR]
    python3 -m harness.pareto.topup dry  --plan data/plans/topup-plan.json --run-id topup-dry --out DIR --main-run DIR
    python3 -m harness.pareto.topup live --plan data/plans/topup-plan.json --run-id topup-1 --cap 25 --clearance FILE

**What it sends** (all Haiku-medium, Batch, on `main-ledger-l14n6-v1`; every new call at 48,000, Amendment 1 section 3):

| Part | Tag | Custom id | Calls |
|---|---|---|---|
| Same-model check | `sc` | `<item>-sc-NN` (NN 01..05) | main.py's `hm` params exactly (5,000), bases 000-019, both shapes, x5: 200 |
| H-pick8 | `pk` | `<item>-pk-01` | 1 per puzzle: 160 |
| E2 planner | `tp` | `<item>-tp-01` | 1 per puzzle: 160 |
| E2 helpers | `th` | `<item>-th-KKDD` (task K, draw D) | lead-by-2, cap 9 per task: at most 8,640 |
| E2 aggregator | `ta` | `<item>-ta-01` | 1 per puzzle whose plan parsed: at most 160 |
| C13 (E3 on pieces) | `es` | `<6x1 item>-es-SSDD` (piece S, draw D) | through `e3.py`, lead-by-2, cap 9: at most 4,320 |

C13 keeps E3's own tag because it IS E3 (`e3.plan_round`, `e3.e3_status` and `e3.e3_rows` run on its steps unchanged); its ids are on
the pieces items, so they never meet the main run's E3 ids (chain items). The new tags are letters only and unused by main.py, e3.py,
the pilot, the length sweep and the Study 1b plan (a test checks).

**The prompts** are `research/models/team_prompts.py`, imported by file path and pinned by SHA-256 (`TEAM_PROMPTS_SHA256`, the D-100
file): a changed file refuses to load. The picker's 8 replies are the main run's Haiku-medium samples 1-8 of that puzzle (their
`answer_text`, read from `<main run>/calls.jsonl` by custom id `<item>-hm-NN`); a sample that did not answer goes in as "(no reply)".
A puzzle missing a FINAL record for any of its samples 1-8 stops the run before anything is sent (`MainRunJoinError`, Edith's
ruling 1; the command prints `REFUSED: ...` and exits 2). `live` reads
the main run from the shared data root's `raw/main-l14n6-1/` unless `--main-run` is given.

**Rounds, built only from the call log** (`plan_round`, pure; a crash or a rerun rebuilds them exactly: a round with no
`topup_round_done` line is resumed with the items it was planned with, rebuilt from the log as it stood at its `topup_round` line, so a
batch caught half-way through writing its results settles with the same items before the next round is planned):
- Round 1: the same-model check, the pickers, the planners and C13's first two draws per piece (1,480 calls; about $17 booked at
  the worst case with stand-in picker replies).
- Then each round: every puzzle's next helper draws (both shapes together; at the chain task k starts from the team's agreed result of
  task k-1, at pieces every task from its printed start), C13's further draws, and each aggregator once its tasks are done.
- A planner reply without exactly Task 1..6 is `plan_failed`: nothing more for that puzzle. A task with no result at the cap shows
  "(no result)" from its place onward at the chain (the later tasks are never started) and at its own place only at pieces.
- One `run_batches` call per round, under the 2% truncation pause: the same stops as the main run (Console check, pause, halt,
  missing results). A `topup_round` line in the log marks each round as it starts and a `topup_round_done` line as it ends with no
  stop; a resumed round gets neither a new number nor a new line. `max_rounds` (60) bounds the run across resumes (counted from the
  `topup_round` lines; the chain needs at most 50). Before each round, a collected batch with no truncation-check line (a crash between
  collecting and checking) is checked first.

**Dates** (the plan's `window`): `live` refuses before `not_before_utc` (2026-10-14 13:01 UTC, when the main run's window closes), a
first round after `latest_first_round_utc` (2026-10-16T23:59Z), and anything after `stop_and_report_utc` (2026-10-18T23:59Z; both
confirmed by Jarvis, checklist section 4).
The 48-hour window starts at its first live start (`main.window_check`, D-45 extensions as in the main run). Both are checked before
EVERY round, not only at the start: past either, the run stops as `refused` (exit 2), collects any batch already sent, and sends
nothing new. An `--extend-window` note is recorded once per round sent past the 48 hours.

**Booking** (`plan`, at the worst case, every task and piece to 9 draws): about $165 over the whole run, booked round by round, never
at once (spec section 6: about $160; proposed cap $25; expected spend about $1.5). The compact table grades only the aggregator and
the same-model check; every other top-up row has a blank `right` (the converter scores them, spec section 4).

**Otherwise the main runbook above applies unchanged:** the clean detached checkout, `caffeinate -i nice -n 19 nohup ... topup live
...`, watching only counts and costs (`status` in the summary: per part and per shape, never any text), the same command after a crash,
orphans, the Console check, missing results, the pause (`--release-pause` / `--truncation-pause-off`), the window and the end-of-run
steps. The plan is copied into the run folder at the first start (`topup_plan.json`); a different plan cannot resume the run.

## The never-sent check (`neversent.py`; Study 1b, Edith F-2; lock-4 audit A5 / A13)

It refuses (exit 2, nothing written) when `--raw` is missing or holds no `*/calls.jsonl`, or when a run with calls in the spend log
(`--spend-log`, default `ops/spend-log.md`; a 0-call bookkeeping row such as `smoke-2 (markers)` needs no log) has no
`<raw>/<run id>/calls.jsonl`. The record holds the commit it ran from, each call log's SHA-256, line count and path, every folder
searched by its full path, and each scanned file labelled by its folder's full path.

**The lock-4 re-run (Edith's pre-approved commands; output names from the spec).** The lock tree is committed as X; run from a clean
detached worktree at X, with the worktree as the working folder; `P=/Users/hrixay/Desktop/pareto`; `$EMPTY` is a new empty folder in
a scratchpad:

    "$P/.venv/bin/python" -m harness.pareto.neversent \
      --sets "$P/data/tasks/main-ledger-l14n16-v1" "$P/data/tasks/ext40-ledger-l14n6-v1" "$P/data/tasks/main-ledger-l14n12-v1" \
      --raw "$P/data/raw" --data "$P/data" --also "$PWD/research" "$P/research" \
      --out data/plans/study1b-never-sent-lock4.json
    "$P/.venv/bin/python" -m harness.pareto.neversent \
      --sets "$P/data/tasks/main-ledger-l14n6-v1" "$P/data/tasks/ladder-ledger-l14n16-v1" \
      --raw "$P/data/raw" --data "$EMPTY" \
      --out data/plans/study1b-never-sent-control-lock4.json

The first must print "never sent | not in other data files" for all three sets (exit 0); the control must print SENT for both used
sets (exit 1: that is the control working). Both outputs are committed as X+1, which is tagged; the record names X. The checks on
them (Edith): `runs_scanned` is exactly the spend log's 8 runs, each SHA-256 matches its file, `other_files_scanned` >= 945, and each
set's `items_sha256` equals `shasum -a 256` of its `items.jsonl` in the lock tree.
