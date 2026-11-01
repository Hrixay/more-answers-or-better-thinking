# Simulated main-run datasets, v2: D-76 step-line scoring (sim-main-v2)

*Karen (Opus 5.5), 2026-10-11. For Friday's strict trace parser (`harness/analysis/trace_parse.py`) and
the analysis code, before the D-69 lock. Desk simulation only: no API calls, no real model output.
Generator: `research/models/sim_fixtures_v2.py`, deterministic seeds;
`python3 research/models/sim_fixtures_v2.py` rewrites everything and first checks that its fast vote
equals v1's exact enumeration. v1 (`sim-main-v1`) stays valid for 24×1 and for the bootstrap's
size/coverage checks.*

## (A) `parse_cases.jsonl.gz`: 148 crafted raw replies (the parse rules agreed with Friday)

- **Sizes.** Each case has `id`, `line_count` (6, 8, 10 or 12: the l14–l17 sizes), `reply` (raw text) and
  `expected = {ok, reason, states, answer}`.
- **Accepted.** 96 cases are accepted; 24 per size, including one that parses fine but carries a wrong
  value (a slip, not a format problem). The accepted variants are:
  - extra or missing spaces, tabs, leading and trailing whitespace;
  - CRLF line endings and blank lines;
  - bold labels (`**1.3**`), backticks and bullets;
  - `:` in place of `=`;
  - `[...]`, `(...)` or no brackets;
  - leading zeros;
  - step lines in any order (each number 1–24 exactly once);
  - Answer-line variants: lowercase, bold, no `1 =` label, no colon;
  - prose before or between the step lines;
  - trailing prose after the Answer line;
  - a code fence around everything;
  - an earlier draft `Answer:` line, where **the last Answer line wins**;
  - one combination case.
- **Rejected.** 52 cases are rejected, 13 per size:

  | Defect | Reason |
  |---|---|
  | A missing line | `missing_line` |
  | A duplicated line (**since D-90, an identical repeat is ok**; see A3) | `extra_line` |
  | Line 1.25, or a line 1.0 | `misnumbered` |
  | A short or long state | `wrong_length` |
  | A decimal (`2002.0`) | `non_integer` |
  | A thousands separator | splits into an extra value, so `wrong_length` |
  | A word, or `~` | `non_integer` |
  | No Answer line | `no_answer` |
  | An Answer line that differs from line 24 | `answer_mismatch` |
  | An Answer state of the wrong length | `wrong_length` |

- **What is binding.** `ok` and, when ok, `states` and `answer`. The `reason` labels are advisory, so map
  them to your own.

## (A2) Round 2 of the parse rules (2026-10-11): `parse_cases.jsonl.gz` ids `-r2-`, `pieces_cases.jsonl.gz`, `final_cases.jsonl.gz`

These cover the rules agreed after Friday's PR #24/#25 changes, with Edith's conditions:
- **Trailing punctuation:** one trailing `.` or `,` after a state is ok. `..`, ` .`, `. Done` and `;` are
  `non_integer`.
- **Prose that starts with "answer"** ("Answer check: …", "## Answer") never replaces the real Answer
  line.
- **Label words:** an optional `Sequence` or `Piece` label (any case, with or without markup) before the
  entry number, at both shapes and in the answer-only fallback.
  - These are not ok: the plural, `Step`, `Line`, and "Sequence 1 ends at …" when it is the only Answer
    line.
- **Bold numbers and colons:** a bold `**1** =` is ok, and at 24×1 a `:` after the entry number is ok.
- **A wrong number after a label** ("Answer: Sequence 2 = …") must be not ok with the same status as a
  bare "Answer: 2 = …" (`non_integer`). These pairs are marked `same_status_as` and `pair_rule`.

The files:
- round 2 of `parse_cases`: 48 cases at 6 and 10 balances (`parse_trace`);
- `pieces_cases`: 18 (`parse_pieces`, 24 pieces at 6 balances);
- `final_cases`: 9 (`parse_final`).

**Runner:** `python3 research/fixtures/sim-main-v2/run_parse_cases.py [REPO_ROOT]` runs every case against
a harness checkout, and exits 1 on any mismatch.

**Result (2026-10-11):** all **223 of 223** cases pass on Friday's 85b50f8 (PR #25) and 195bad0 (PR #24).
That is round 1's 148, plus 48, 18 and 9 in round 2, including the three same-status pairs.

## (A3) D-90, Deviation 2 (2026-10-12): repeated step lines

**The rule now:** a step line written more than once with the **identical** state is accepted and read
once. "Identical" means the same values after reading, so markup may differ. A repeat with a
**different** state still fails (`extra_line`).

- **Round 1 changed in one place:** the 4 `L*-duplicate-line` cases (an identical repeat of line 1.12)
  are now `ok`. Round 1 is still 148 cases, and no other case changed.
- **New file `parse_cases_d90.jsonl.gz`:** 16 cases (ids `-d90-`, seed 7678), 4 at each size:

  | Case | Expected |
  |---|---|
  | `duplicate-line-markup`: line 1.12 again, written `**1.12**=[…]` with no spaces | ok |
  | `duplicate-line-conflicting`: line 1.12 again with different values | `extra_line` |
  | `summary-repeat-all`: Sonnet's style, all 24 lines, then all 24 again under "Summary:", then the Answer line | ok |
  | `summary-repeat-one-differs`: as above, but one line differs in the summary | `extra_line` |
- **lock-2's rule is kept testable for the paper's original-rule check.** Cases where it differs carry
  `expected_strict` (`extra_line`). The runner also calls `parse_trace(..., repeats="strict")` on every
  parse case and counts those as separate `[strict]` checks. If the parser has no `repeats` option, it
  skips them with a note.
- **Result (2026-10-12):**
  - all **451 of 451** pass on a ten-line stand-in for the D-90 rule (212 parse cases under each rule,
    plus 18 pieces and 9 final cases);
  - on main's lock-2 parser, exactly the 12 identical-repeat cases fail, as they should.
  - **on Friday's D-90 parser (1f03bfa): 451 of 451 pass**, confirmed by both of us, along with his fixture
    tests (72 passed).

## (B) Analysis cases (the same seven cases, tests and seeds as v1)

**What changed from v1.** Every **1×24** row of Haiku-medium, Opus-medium, Opus-low and Sonnet-medium now
carries these fields:

| Field | Values |
|---|---|
| `format_status` | `ok`, a reject reason, or `refusal` / `truncated` / `unparseable` for non-answers |
| `trace_key` | The canonical key of the 24-state tuple; **null unless the format is ok** |
| `final_key` | The Answer state's key; null if there is no Answer line or the call didn't answer |
| `slip_type` | `none`, `real` (carries to the final), `copy` (one printed line wrong, the final right) or `absorbed` (the trace is wrong but rejoins, so the final is right) |
| Score labels | `correct` (the official D-76 score), `correct_final` and `correct_copy_forgiven` |
| `line_count` | 10 (l16) |

- 24×1 rows and E3 rows are unchanged; E3's `correct` equals `all(step_correct)`.

**The three scores**, as in `expected.json` → `scoring`:

| Score | Definition | Views |
|---|---|---|
| **Official** (D-76) | Format ok **and** the trace equals the right trace. A try that isn't ok is wrong, and a **null vote** | as_deployed, refusals_left_out and truncations_left_out (the views as in v1) |
| **Final-answer** (secondary) | The Answer state is right | as_deployed |
| **Copy slips forgiven** (sensitivity) | Format ok, and the slip is `none` or `copy`. In the vote a copy-slip trace counts for the right trace | as_deployed |

**The vote** is a plurality over identical keys (trace keys for the official score), with exact vote@k,
ties scored 1/m, and nulls voting for nothing.

**The test values are exaggerated on purpose, so every path gets exercised. They are not estimates.**
- **Format failures:** Haiku 3%, Opus 1%, Opus-low 1%, Sonnet 1.5%, spread evenly over the 7 reject
  reasons.
- **Wrong unique traces:** real 75%, copy 15%, absorbed 10% (single arms: 70 / 20 / 10). 20% of Haiku's
  wrong answers are one shared real slip.
- **As a result,** Haiku's final-answer accuracy is about 16 points above its official accuracy here.
  Expect far less in the real runs.

**What `expected.json` holds:**
- the true official d per test (with refusals and truncations left out);
- k (computed from the rows' costs, and asserted);
- population vote accuracies (Monte Carlo over puzzles, error about 0.001; exact over subsets);
- target official accuracies;
- `rates_1x24` per arm: format compliance, the absorbed and copy shares of wrong traces, and the three
  accuracies;
- the readings: Holm, the three-way reading, p and BCa, as in v1.

**The `mixed` case,** at 1×24: 4 Opus-medium refusals, 1 Opus-low refusal, 2 Sonnet truncations, and
Haiku truncations and unparseables. Its official readings:
- as deployed: t2 −5.1;
- refusals left out: t2 −8.0 (n = 76);
- truncations left out: t3 −16.3 (n = 78).
