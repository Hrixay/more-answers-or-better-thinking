# The top-up run: specification and definitions

*Karen (Opus 5.5), 2026-10-13. Final as frozen in `prereg-lock-4`, which it joins under Edith's Z-3 ruling. Names follow the
glossary (D-98). Run ids, tags and file names keep their old spelling.*

*Rulings:*
- *D-99: its own window, declared as a change from D-42(b), plus Edith's same-model check. "let's start working on it now only";*
- *D-27: the Haiku team and the Haiku picker are should-haves 3 and 4;*
- *D-94(5): step voting on pieces is C13, kept;*
- *Edith's E2/H-pick8 reviews r1 and r2 (`ops/reviews/2026-10-12-e2-hpick8-drafts-r1.md`), all five design choices accepted;*
- *the readiness checklist, §4.*

*This file holds both the spec and the dated definitions note that checklist §4 asks for. Both are fixed before any top-up result
exists. No API calls were made to write it.*

*The prompt wording is `research/e2-and-picker-prompts.md` and `research/models/team_prompts.py` (Edith CLEAN; free check 0 blocks in
18). **The user approved it in D-100: "Yes, it is my yes for the wording."***

---

## 1. What the top-up run is, and why it has its own window

**The top-up run completes three Study 1 arms that couldn't run inside the main run's window:**
- **the Haiku team (E2):** a stateless Haiku planner writes one instruction per step, Haiku helpers carry them out, and a Haiku
  aggregator writes the final answer;
- **the Haiku picker (H-pick8):** one Haiku call reads 8 of Haiku-medium's main-run answers to a puzzle and picks one;
- **step voting on pieces (C13):** E3 on the pieces shape, which the main run didn't include, so Test 4 can be read at pieces too.

All three are **exploratory** (D-27; D-68 F1). None is one of Tests 1–5.

**The deviation text for the window** (D-99; for the methods, word for word):

> **Change from D-42(b) (decided 2026-10-13, before any top-up data).** D-42(b) asked every setup to run within about 48 hours. Three
> exploratory Study 1 arms (the Haiku team, the Haiku picker, and step voting on pieces) ran in a separate top-up run, from [start
> date] to [end date] UTC, after the main run's 48-hour window (2026-10-12 13:01 to 2026-10-14 13:01 UTC) had closed. They were
> built after the main run started, and running them inside it would have held it open. Their comparisons with main-run arms
> (Opus-medium, step voting on chains, and Haiku-medium's samples) therefore span two windows. A pre-stated same-model check, which
> re-ran Haiku-medium on 40 main-set puzzles, measures whether the model's behaviour moved between the windows. The model IDs are
> pinned, and any reply naming another model stops the run, as in D-42(b).

## 2. Arms, puzzles and settings

**The puzzles** are the main set `main-ledger-l14n6-v1`: 80 base puzzles × 2 shapes (chain and pieces), 160 puzzles.

**The model** is Claude Haiku 5.5 at **medium** effort for every call, with adaptive thinking. Batch only.

**The token limit is 48,000 for every new call** (Amendment 1 §3: every setup the length sweep didn't measure keeps the locked pilot
limit). The same-model check is the exception: it uses the main run's Haiku-medium settings exactly, including 5,000.

| Arm (tag) | Calls | Puzzles |
|---|---|---|
| **Haiku team (E2)**, chain | 1 planner; then, for each of the 6 tasks in order, helper draws with lead-by-2 voting, cap 9; then 1 aggregator | 80 chain puzzles |
| **Haiku team (E2)**, pieces | 1 planner; the 6 tasks' helper draws, all at once (each piece from its printed start), lead-by-2, cap 9; then 1 aggregator | 80 pieces puzzles |
| **Haiku picker (H-pick8)** | 1 call per puzzle, reading Haiku-medium's main-run samples **1–8** of that puzzle, in sample order | all 160 |
| **Step voting on pieces (C13)** | E3 exactly as in the main run (`harness/pareto/e3.py`, Haiku-medium, lead-by-2, cap 9), with each piece as one step from its printed start | 80 pieces puzzles (480 step positions) |
| **Same-model check** | Haiku-medium ×5 at the main run's settings | base 000–019, both shapes (40 puzzles, 200 calls) |

**The rules from Edith's r1, accepted:**
- **The Haiku team's helpers** vote lead-by-2 with cap 9, using E3's at-cap rule: at 9 draws the unique most common answer wins, and a
  tie gives no result.
- **The team's aggregator** may redo a step.
- **A failed task** shows "(no result)" from its place onward.
- **A plan that doesn't have exactly Task 1 to Task 6** is `plan_failed`: that puzzle's team answer is wrong as deployed.
- **The picker** returns `Pick: k`, and its answer is sample k itself.
- **Round structure, for the build:**
  - every puzzle's task k goes in the same Batch round, and both shapes run together;
  - the Haiku team takes about 2 + 6 × its voting rounds at chain, so about 14 rounds is typical;
  - the same-model check, the pickers, the planners and step voting's first draws go in **the first round**.

**Order and windows:**
- **The run starts after 2026-10-14 13:01 UTC**, when the main run's window has closed.
- It never runs at the same time as Study 1b.
- It finishes by 10-18.
- It has its own 48-hour window from its first submission.

## 3. Edith's same-model check (D-99; as she designed it; a flag, not a gate)

**What it is:** Haiku-medium ×5, at the main run's Haiku-medium settings exactly (same model ID, effort, `max_tokens` 5,000, prompt
and Batch), on main-set **bases 000–019, both shapes** (40 puzzles, 200 calls). It runs **in the first round** of the top-up run.

**What it's compared with:** the main run's Haiku-medium **samples 1–5** of the same 40 puzzles.

**What's reported:**
- **Accuracy difference:** whole-answer accuracy (official score, as deployed) per puzzle, as the share right of its 5 tries. Then
  d = mean over the 40 puzzles (top-up − main), per shape and pooled. A 95% cluster bootstrap over the 20 base puzzles, 2,000 draws,
  seed `derive_seed(20261014, "same_model:<6x1|1x6|pooled>")`.
- **Output tokens:** the mean output tokens per call, both runs, and the relative change.
- **Refusal and truncation counts,** both runs.

**The flag** (stated before any data):
- it fires if **the pooled 95% interval excludes 0 and |d| > 10 points**, **or** if **mean output tokens move by more than 25%**;
- **it is a flag, not a gate.** The run continues;
- the paper reports the flag beside every cross-window comparison (§5);
- **these 200 answers are never mixed into Study 1's data** or into any Study 1 test.

## 4. Definitions, fixed before any top-up result (checklist §4)

**4a. The converter.**
- A **separate converter**, `topup_rows`, maps the top-up run's logged records to rows. It reuses the locked scorers unchanged:
  - `scoring.grade_1x24` and `grade_24x1` for answers, with the D-76 rules and D-90's repeat rule;
  - `harness/pareto/e3.py`'s `e3_rows` for step voting.
- It makes no analysis choices of its own. Every mapping cites this note.
- It never touches `main_rows` or Study 1's outputs.

**4b. The rows:**
- **The Haiku team:** one row per puzzle. It records:
  - the plan status (ok or `plan_failed`);
  - for each task, the helpers' draws and agreed result (or "no result");
  - the aggregator's reply, graded by the locked scorer for its shape.

  The puzzle's team answer is the aggregator's graded answer, and `plan_failed` counts as wrong.
- **The picker:** one row per puzzle. It records the parsed pick k (1–8, or none) and **the joined main-run row** for Haiku-medium
  sample k. A missing or unparseable pick counts as wrong.
- **Step voting on pieces:** E3 rows at pieces (`step_correct` per piece). The score is the **product of the per-piece accuracies**
  (F7), by the same rules as on chains.
- **The same-model check:** one row per call, graded as Haiku-medium rows are.

**4c. The join to main-run Haiku-medium rows** (the picker and the same-model check).
- Match by (`item_id`, `sample`), where `sample` is the main run's Haiku-medium sample index. The source is the stamped main-run rows
  from `harness/analysis/main_rows.py` on `data/raw/main-l14n6-1/` (the D-93 stamp's hashes).
- Every picker row must join to exactly 8 main-run rows (samples 1–8), and every same-model puzzle to 5 (samples 1–5). **A failed join
  stops the driver.**

**4d. vote@8 and any@8**, on samples 1–8 only, per puzzle:
- **vote@8** = `votes.vote_accuracy_at_k(answers of samples 1–8, correct, k = 8)`, with designed = 8. A missing or unparseable sample
  is a vote for nothing, and ties count at 1/m (D-33). With k = 8 there is exactly one subset;
- **any@8** = 1 if at least one of samples 1–8 is right, else 0. This is the ceiling a perfect picker could reach;
- both are reported beside the picker's accuracy, per shape and pooled.

**4e. The Haiku team's counts (Edith r1, pre-stated):**
- **aggregator changes:** puzzles where the final answer differs from the helpers' chain. Of those, how many turned a wrong chain
  right and how many turned a right chain wrong, per shape;
- **failed tasks:** puzzles with a task that ended with "(no result)", per shape;
- **failed plans:** puzzles with `plan_failed`, per shape.

**4f. Cost per puzzle** (list price, by `research/reporting-definitions-main.md` item 9a; B5-free refusals at $0; the Batch figure
beside it):
- **the Haiku team:** the planner, plus every helper draw, plus the aggregator;
- **the picker:** the picker call alone, reported as **the extra cost over vote@8's 8 samples**. The total (the 8 main-run samples'
  cost plus the picker) is shown beside it;
- **step voting on pieces:** the sum of its step draws on the puzzle.

## 5. What is reported (all exploratory; no Holm; no verdict except where stated)

**The method:** paired differences over base puzzles, as deployed, using `bootstrap.paired_bca(diffs, margin=−10, B=10_000,
seed=derive_seed(20261014, name))`. Report d and the 95% interval.

| Comparison | Shape | Seed name |
|---|---|---|
| The Haiku team − step voting (main run's E3 at chain; C13 at pieces) | each | `"topup:e2-e3:<shape>"` |
| The Haiku team − Opus-medium | each | `"topup:e2-om:<shape>"` |
| The picker − vote@8; the picker − any@8; the picker − Haiku-medium single try (samples 1–8 mean) | each | `"topup:hp8-<ref>:<shape>"` |
| **Test 4 at pieces** (step voting on pieces − Opus-medium) | pieces | — |

**Test 4 at pieces** is read the way `research/reporting-definitions-main.md` item 11 reads tests 3 and 5 at the other shape:
- d, the BCa 95% interval, and the three-way reading at margin 10, using `derive_seed(20261011, "t4@6x1")`;
- labelled **exploratory, outside the Holm family**;
- with the methods note that **this arm ran in a different window from its Opus-medium comparator** (Edith r6; §1).

**Every cross-window comparison** (any top-up arm against a main-run arm) carries the same-model flag's status (§3).

**A run cut short** (the user's ruling D-106(G); it matches Study 1b's completeness rule, `research/study1b-spec.md` §4):
- If any designed call of an arm (the Haiku team, the Haiku picker, step voting on pieces, or the same-model check) has no final
  record when the driver runs, that arm reads **"not completed"**: its designed, final and missing counts only, with no score.
- A refusal, a truncation or an unparseable answer counts as final (and wrong).
- An arm that is not completed enters no comparison above. Test 4 at pieces gets no reading if step voting on pieces is not
  completed.
- If the same-model check is not completed, its flag (§3) reads "not completed" beside every cross-window comparison.

**Also reported:**
- accuracy per arm and shape (the shared cluster bootstrap, 2,000 draws, seed 20261014);
- cost per puzzle (§4f) and cost per correct answer (`research/reporting-definitions-main.md` item 9c);
- format compliance, refusals, truncations and missing items (`research/reporting-definitions-main.md` items 16 and 17);
- the §4e counts;
- the picker's position distribution, meaning how often each of samples 1–8 is picked. This is descriptive; position effects are not
  studied.

## 6. Booking, spend and cap

**Expected spend (Batch), from the main run's measured step-voting costs** (about 0.18¢ per puzzle for 6 steps):

| Part | Spend |
|---|---|
| Step voting on pieces | about $0.15 |
| The Haiku team (planners, about 3 helper draws per task, aggregators) | about $1 |
| The picker | about $0.1 |
| The same-model check | about $0.12 |
| **Total** | **about $1.5** |
| **High case** (three times, for long planner and aggregator outputs) | **about $5** |

**The guard's booking:**
- Every call is booked at 48,000 tokens; the same-model check at 5,000.
- The **first round** books about **$16**: the check's 200 calls, 160 planners, 160 pickers and step voting's 960 first draws.
- Each team helper round books about $13 at most.
- Over the whole run, the booking is about $160 at the worst case (every task to 9 draws). It is booked round by round, never all at
  once.

**Proposed cap: $25** (D-99's note).
- It covers the largest round's booking plus the high-case spend.
- With Study 1b's $130 cap (D-102), the two caps total $155, inside the $158.30 left.
- The two runs are sequenced, never at the same time.
- The cap is the user's call through Edith's clearance.

## 7. Procedure

1. **This spec joins lock 4** beside Study 1b, under Edith's Z-3 ruling, so it has a public timestamp before any data. The spec
   (Edith CLEAN at 123d775, plus the one-line cap edit of db86195), the runner and the driver are CLEAN.
   - The prompt wording is approved (D-100).
2. **Friday's top-up runner:** the Haiku team's rounds, the picker joining main-run text, C13 through `e3.py`, and the same-model
   check in round 1. Plus `topup_rows` and a driver for §4–5.
   - All are tested on **fixture or length-sweep data only**.
   - Edith reviews them before any call.
3. **Karen's price re-check** within 24 hours before the start, then **the top-up's price-date commit** (lock-4 audit P6, P15, P17):
   - `topup-1` runs at a price-date commit that is a **child of Study 1b's last price-date commit**. It is never cut from main and
     never a second child of the tag.
   - `git diff --stat prereg-lock-4 <commit>` shows only `harness/pareto/prices.py` (`PRICE_TABLE_DATE` and the docstring line
     recording the re-check) and its date test. The price table itself changes only if the re-check finds a price change, which goes
     back to the user before any call.
   - Rollovers into a later UTC day follow Study 1b's rule (`research/study1b-spec.md` §9, step 4).
4. **Edith's clearance** for run id `topup-1`, a fresh Console reading, and the user's go and cap.
5. **The run** starts after 2026-10-14 13:01 UTC, outside Study 1b's run, with the 2% truncation pause (D-94(1)) and its own window.
6. **The driver runs once** after Edith's check. The results are read only then.
