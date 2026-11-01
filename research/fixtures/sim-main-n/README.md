# Parse fixtures at shorter chain lengths (sim-main-n), for prereg-lock-2 (route a′)

*Karen (Opus 5.5), 2026-10-12. Desk work, no API calls. Generator: `research/models/sim_fixtures_n.py`
(seeds 8800–8804 for parse cases, 8900–8904 for pieces; n = 4, 6 and 8 unchanged since first written).*

These are the same D-76 parse rules as `sim-main-v2`, plus round 2's label rule, re-rendered at
**n = 4, 6, 8, 12 and 16 steps** (D-86):

| Files | Each | What they test |
|---|---|---|
| `parse_cases_n{4,6,8,12,16}.jsonl.gz` | 152 cases (136 before D-90) | `parse_trace(reply, line_count, steps=n)` at 6, 8, 10 and 12 balances. 22 accepted variants plus one value slip that still parses; 12 reject reasons, including the plural label and the wrong-number pair (`same_status_as`, both `non_integer`) |
| `pieces_cases_n{4,6,8,12,16}.jsonl.gz` | 8 cases | `parse_pieces(reply, width=n, 6)`: plain, Sequence, bold and colon labels, a trailing period and prose after the real line (all ok); Step labels and no Answer line (not ok) |

- The answer-only cases don't depend on n, so they stay in `sim-main-v2/final_cases.jsonl.gz`.
- **Runner:** `python3 research/fixtures/sim-main-n/run_parse_cases_n.py [REPO_ROOT]`.
- **Result on main's harness (2026-10-12): 720 of 720 pass.** `trace_parse` already takes `steps`, and
  `parse_pieces` already takes `width`.

## D-90, Deviation 2 (2026-10-12): repeated step lines

**The rule now:** an identical repeated step line (the same values after reading) is accepted and read
once. A repeat with a different state still fails (`extra_line`).

- **Changed in each file:** the 4 `N{n}-L*-duplicate-line` cases are now `ok`.
- **Added to each file:** 16 cases, 4 per size; together with the 4 changed ones, 20 per file and 100 in
  all.
  - `duplicate-line-markup`: line 1.n again, with markup and no spaces. ok.
  - `duplicate-line-conflicting`: extra_line.
  - `summary-repeat-all`: Sonnet's style, all n lines, then all n again under "Summary:", then the Answer line. ok.
  - `summary-repeat-one-differs`: extra_line.
  - These were added without drawing from the random generator, so every other case is unchanged.
- **The strict check:** cases where lock-2's rule differs carry `expected_strict`. The runner also checks
  `repeats="strict"` as separate `[strict]` checks, or skips them with a note if the parser has no
  `repeats`.
- **Result (2026-10-12):**
  - **1,560 of 1,560** pass on a stand-in for the D-90 rule (760 parse cases under each rule, plus 40
    pieces cases);
  - on main's lock-2 parser, exactly the 60 identical-repeat cases fail;
  - **on Friday's D-90 parser (1f03bfa): 1,560 of 1,560 pass**, confirmed by both of us.
