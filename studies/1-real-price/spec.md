# Pre-registration

*Empty until ruled. This is the study's locked contract. It is filled in item by item, in conversation:
Friday drafts with Jarvis, Edith reviews, and the user rules each item. It reaches `main` by pull
request and is locked by a commit before the main run. The paper cites that commit. After it is locked,
any change is a dated amendment at the bottom, with the reason, and never a silent edit.*

---

## Status

**DRAFT SKELETON, 2026-10-10. Not locked. Nothing here is binding yet.** Friday drafted it so Edith can
review it while the user's rulings land. Only text under a **RULED** label is decided, and each such
line names its register entry in `decisions/register.md` and quotes the user's words. Text under
**DRAFTED, NOT RULED** is wording someone proposed. Text under **OPEN** is a question the user still has
to answer.

How to read the labels in each section:
- **RULED**: the user said yes; the register ID and the user's words are given.
- **DRAFTED, NOT RULED**: proposed wording, with who proposed it and what backs it (a file path, or
  "ours, unbacked").
- **OPEN**: a plain question for the user. Where a number is needed and not ruled, the number is
  labelled "suggested by <file>". It is a suggestion, not a threshold.

| # | Item | Status | Rulings so far |
|---|---|---|---|
| 1a | Task family | **ruled** | D-15, D-19, D-20 |
| 1b | Number of steps and shapes | **ruled**: 24 steps; two shapes (24×1 and 1×24), labelled honestly | D-16 (24 steps), D-24 (two shapes), D-26 (the label) |
| 1c | Matched shapes | **ruled**: each base puzzle appears in both shapes | D-28 |
| 1d | Rules of the same kind back to back | **ruled**: allowed, as built; the method says so | D-43 |
| 1e | The ledger family (main task family) | **ruled** that it replaces the digit puzzle (D-56), the code family is dropped (D-59); **drafted, not ruled**: the section's wording (including the house rule), presets and check design | D-56, D-57, D-58, D-59, D-60, D-62, D-63, D-64, D-77, D-78, D-79, D-80 |
| 2 | Difficulty calibration | **superseded for the ledger by 1e, D-56 and D-62 (preset names and the pilot are in `research/pilot-plan-ledger.md`)**; digit text: **ruled** (the pilot picks d4s or d4p by D-36's rule; Haiku-medium; band 25 to 50%; no hard slice; d4 is a reference only) | D-21, D-25, D-27, D-36, D-38, D-48 |
| P | Pilot protocol (between items 2 and 3) | **superseded by `research/pilot-plan-ledger.md` (D-56, D-59; the $7/$17/$29 digit pilot is replaced by the ledger pilot, hard cap $30)**; digit text: **ruled, and priced**: about $7 / $17 / $29 (low / central / high) against the $30 cap, per Karen's note on D-36; the sets, the pooling of the median, the tie-break and the extra-rung rule are ruled by D-48 | D-36 (with D-17, D-21, D-27, D-28, D-33, D-35), D-38, D-48 |
| 3 | Setups | **ruled** (Karen's list, trimmed; k by D-33; the real-world check is out) | D-27, D-33, D-35, D-48 |
| 4 | Prompt and output format | **ruled** for the format (the digit and code wording below is superseded by the ledger wording in 1e, which the user approves before the check) (option B, minimal wording; the exact wording is approved; the 2% switch; the code wording check is done; the sensitivity view of H1 is in; no summarised thinking) | D-31, D-36, D-40, D-41, D-48 |
| 5 | Cost accounting | **ruled** (D-33 for list price and input; D-48 for the headline cost, failures, re-runs and the price-table date) | D-33, D-48 |
| 6 | Sample size and stop-loss | **ruled** (the $170 ladder, the stop-loss, no hard slice; D-48 sets the numeric caps, halts and the pause rule) | D-27, D-48 |
| 7 | Hypotheses | **ruled** (exact text in 7b, D-68): five confirmatory tests, whole-answer scoring, a 10-point non-inferiority margin, Holm across the five; the code family is dropped (D-59), so the code secondary check is out | D-23, D-33, D-39 |
| 8 | Analysis plan | **ruled** (the confirmatory family, scoring and correction follow D-39; D-48 fixes the interval method) | D-23, D-28, D-33, D-39, D-48 |
| 9 | Data | **ruled** | D-37 (closes D-11) |
| 10 | Robustness | **ruled** (the exact variant text is still to be written and checked free) | D-42 |
| 11 | Code tracing, the second family | **dropped by D-59** (kept below as history); was **ruled**: second family, built (PR #10), free wording check done; setups ruled (Sonnet is out); subset 80 puzzles, shape and budget check ruled by D-48 | D-20, D-22, D-32, D-35, D-41, D-48 |

**Still to do before the lock** (as of 2026-10-10; the spec is not locked):
1. **The spend guard cleared:** Edith's review of PR #11 (the harness, the spend guard and the pilot runner) round 3, her
   written clearance tied to one commit, then the user's "go". No money moves before that.
2. **The exact text of the prompt variant** (item 10, D-42; drafted in PR #14): Edith clears it, then a small free
   wording check (Opus, Sonnet, Haiku helpers; stop at the first block; no rephrasing or retries), then the user's yes to
   the words.
3. **The pilot, then the main-run numbers it sets:** the preset (D-36 rule), k (D-33, from the main run's costs), the main
   run's size and per-run caps (D-48 row 25), written into this spec before any main-run data exists.
4. Edith's review of the finished spec, then the lock commit. **Every item is now ruled in principle; items marked
   DRAFTED stay as background wording.**

**Short names for the source files** (all paths are inside this repo):
- *briefing folder* = `decisions/briefings/2026-10-10-study1-design-check/`. Files there: `check-precision.md`,
  `check-cost.md`, `check-setups.md`, `check-codetracing.md`. The `analyse-*.md` files are background
  only. Where an analysis and its check disagree, this draft follows the check (the briefing folder's
  `README.md`).
- *evidence* = `research/study1-design-evidence.md` (Karen: reconciled budget in §0, item 3 evidence in §3;
  it owns the briefing's analyses from now on) · *brief* = `studies/1-real-price/brief.md` · *options* = `research/task-options.md` · *facts* =
  `research/facts-checked.md` · *taskgen* = `harness/taskgen/README.md` · *presets* =
  `data/examples/presets.md` · *H-README* = `harness/README.md` · *checklist* = `ops/review-checklist.md`.

**What the study asks** (brief): at the same dollars per task, what buys the most accuracy on Claude
5.5: a bigger model, more thinking, more samples with a vote, or a team? Does the answer change with how
the task is built (independent pieces, or one long chain)?

**Money.** $0.00 of $200 spent (`NOW.md`, `ops/spend-log.md`).

**Deadline and scope.** The $200 credit expires on **2026-10-19 (UTC)**; every paid run must finish before then, and
Study 1 is the top priority (**D-47**: "And yes, study one-stop priority for 19."). If the clock tightens, the cut
order is: the Haiku-max extra and the other ladder extras first; never Edith's clearance, the smoke run or the pilot's
preset choice. **Study 5 is out of this project** (**D-44**: "Just leave the study 5 out of this project. Don't worry
about the time. I'll push along with you."), so its about $15 budget line is freed; the logged step values keep a
judging study possible later with new credit.

---

## Remaining details: ruled (D-48)

**RULED: D-48 (2026-10-10), amended by D-49 for rows 15 and 19.** The user: "Yes to group A. And go with group B as recommended." For rows 15 and 19 (D-49): "yes to both" (row 15 restated with the current budget; row 19's too-hard fallback is d2) Every row below is ruled as written
(group A confirmed; group B ruled as recommended), at head e11264e of this branch. *(Friday drafted the sheet on 2026-10-10 at Jarvis's request, so the user could rule the remaining points in one sitting.
Each row: the question in plain words; the recommended answer; the source; and the kind: **(a)** already implied by a ruling and
only needs writing down, or **(b)** a real choice for the user. Numbers for items 5 and 6 are Karen's, `evidence` §6d; "ours" means
no file backs it. The rows are binding as of D-48.)*

**Group (a): implied by a ruling; confirmed as written**

| # | Item | Question | Ruled (as written) | Source |
|---|---|---|---|---|
| 1 | 1a, 2 | Which preset is the standard level? | **Superseded for the ledger by section 1e, D-56, D-59 and D-62; the ledger text is in `research/pilot-plan-ledger.md`.** The pilot decides: the preset (d4s or d4p) whose median single-try Haiku-medium accuracy is closest to 37.5%, among those in 25 to 50%. d4 is a reference only. | D-36 (4), D-38 |
| 2 | 2 | Haiku calibration effort? | Medium (the API default; the pilot runs Haiku-medium). | `check-setups.md` P11, `facts` 2b, D-36 |
| 3 | 2 | Band edges, and a preset at 50 to 55%? | 25 to 50% exactly, as D-36 states. If no preset is in the band, take the closest within 15 to 60%; a preset at 50 to 55% is handled by that rule (it is out of the band, so it is chosen only if nothing is in the band). | D-36 (4) |
| 4 | Pilot | Pilot set names? | **Superseded for the ledger by section 1e, D-56, D-59 and D-62; the ledger text is in `research/pilot-plan-ledger.md`.** `pilot-digits-d4s-v1`, `pilot-digits-d4p-v1`, `pilot-digits-d4-v1`, `pilot-code-c3b-v1` (family, preset, split); main sets get different ids when frozen. | D-36 (1), Edith N43; `data/pilot-plan.md` |
| 5 | Pilot | Haiku sample count in the equivalence check? | Haiku-medium ×5 in real time on 10 puzzles, next to the pilot's batched ×10. | `evidence` §6b.3, D-35, D-36; in the plan |
| 6 | 3 | The vote size k and the Haiku sample counts? | **Superseded by section 7b (D-70): Haiku is always drawn ×40, no cut to 20.** k comes from the main run's costs by D-33's formula, capped at 40; Haiku ×40 per puzzle is the maximum drawn; cut to 20 only if the pilot shows the vote flat by then. | D-33, D-27, `check-setups.md` P7 |
| 7 | 3 | Batch limits, result retention, effort and thinking in Batch? | Answered: 24-hour expiry and the other limits are in `facts` B-rows and `evidence` §6b.3; the smoke run's Batch checks that effort and adaptive thinking work in Batch. | `facts` B4, `evidence` §6b.3; smoke run |
| 8 | 3, 1a | Real-world check (ArXivMath)? | Out. It is not in D-27's list, the budget has no room for it beside the musts, and the deadline is 2026-10-19. | D-27, `evidence` §6d (6)(4), D-47 |
| 9 | 5 | Are failures counted? | Yes: refusals, truncations, empty replies and unparseable answers count as wrong, at their logged cost; none is dropped. | D-33 ("all in"), `checklist` §1 |
| 10 | 5 | Latency source? | The 10-puzzle real-time check inside the pilot. | D-35 |
| 11 | 6 | Code subset size? | 80 puzzles (40 base × 2 shapes): Opus-medium ×1, Haiku-medium ×40, E3. About $12 / $26 to 37 / $83 (low / central / high). It is the second thing cut after the ladder extras if the clock tightens. | D-32, D-35, D-47; `evidence` §6d (5) |
| 12 | 6 | Console spend limit? | Already set by the user ($200 organisation monthly limit); nothing to rule. | D-12 (done), Jarvis |
| 13 | 7 | Small details of the equal-money rule (unparseable answer = a vote for nothing; exact count where feasible, sampled otherwise; interpolated k as defined in item 7: k* unrounded, accuracy interpolated between ⌊k*⌋ and ⌈k*⌉)? | As drafted in item 7. | `evidence` §6b.2, D-33 |
| 14 | 11 | Shape of the code subset? | Two shapes × 40 base puzzles, matched. | D-32's register note |
| 15 | 11 | Where does the budget stand after the pilot? | Re-checked from the pilot's measured tokens before the main run; the D-27 stop-loss applies. Karen's central all-in, restated by **D-49** with Study 5 out: musts about $124 to 136; with shoulds 1 to 4 $140 to 152; with Haiku-max $154 to 166, all inside the $170 ladder. | `evidence` §6d, D-27, D-44, **D-49** |

**Group (b): real choices for the user (ruled as recommended)**

| # | Item | Question | Ruled (as recommended) | Source | Why it was a choice |
|---|---|---|---|---|---|
| 16 | 1a, 2 | If Opus stays near the ceiling on every preset, what then? | Accept a near-ceiling Opus and lean on the Haiku and Sonnet contrasts. Do not add steps. | D-27, D-16, Edith E9; ours | Adding steps reopens D-16 and costs days we do not have before 2026-10-19. |
| 17 | 1b | If the equal-work check fails (a model's accuracy differs between shapes for reasons other than structure)? | Report it and keep the comparisons, flagged; do not drop them. | brief, `check-setups.md` P9; ours | It changes what the paper may claim. |
| 18 | Pilot | Median over what, and ties between presets? | **Superseded for the ledger by section 1e, D-56, D-59 and D-62; the ledger text is in `research/pilot-plan-ledger.md`.** The median of each puzzle's Haiku-medium accuracy (10 tries), over all of a preset's 20 practice puzzles pooled across both shapes, with the two shapes also reported separately. A tie between presets goes to d4s (digit text; the ledger tie-break is fewer rule kinds, then the shorter mean prompt, D-62). | D-36 (4); ours | D-36 gives the target but not the pooling or the tie-break. |
| 19 | Pilot | If no preset is within 15 to 60%, which extra rung? | **Superseded for the ledger by section 1e, D-56, D-59 and D-62; the ledger text is in `research/pilot-plan-ledger.md`.** If all are too easy, build one harder rung only if the user agrees to the time; if every piloted preset comes in under 15% single-try Haiku accuracy (too hard), the fallback is **d2** (6 digits, small arithmetic), not d3 (**D-49**: d3 keeps the big arithmetic D-25 moved away from). Under the deadline, prefer taking the closest preset and reporting the miss. | D-36 (4), D-47; ours | An extra rung costs a build and a second pilot; the clock may not allow it. |
| 20 | 4 | A blocked-calls-left-out view of H1? | Yes: pre-register it as a sensitivity view of H1 and the Sonnet contrast, and report each model's block rate beside its accuracy. | Edith W4 | It adds an analysis, though at no cost. |
| 21 | 4 | Ask the API for summarised thinking? | No. Billing is the same, nothing in the design reads thinking, and Study 5 is out. | `facts` 2e, D-31, D-44; ours | It changes what is logged. |
| 22 | 5 | Headline cost? | Uncached list price, mean dollars per puzzle with every attempt counted (failed attempts at their billed cost, usually $0); the median is a sensitivity check; a cached view is a labelled offline re-pricing only. | `evidence` §6d 5(1) and 6(6)(2), `facts` 1g; D-33 | It fixes the headline number readers will quote. |
| 23 | 5 | Re-run policy? | Retry only 429/5xx, up to 3 times (already built); resubmit Batch errored or expired items in the next wave, up to 2 times; an item still without an answer, or a dropped connection, counts as wrong at its logged cost with a sensitivity view that excludes it, and the missing rate is reported per setup; vote@k uses the samples available, flagged; refusals, truncations and unparseable answers are never re-run in the main run (the first attempt is primary). | `evidence` §6d 5(2), Edith N46 | It decides how failures enter every table. |
| 24 | 5 | Price-table date? | Pin the table on the first main-run day (re-checked within 24 hours, D-42 (c)); later price changes go in the offline re-pricing only. | `evidence` §6d 6(6)(1), D-42 | It decides which prices the paper quotes. |
| 25 | 6 | Numeric stop-loss and halts? | Hard cap $200 (the credit less the spend log); ladder line $170 all in (D-27); pilot cap $30 (D-36); each main-run cap = the smaller of 1.3 × the pilot-projected cost of that run and the room left under $170. **Halt** on: money, a model mismatch or change, a stale price table, any Haiku request over 100,000 input tokens (billed about 5×; cannot happen in our design, so it means a bug). **Pause that setup and come back to the user** if more than 2% of its calls in a wave stop at the output limit (the limit binds). **Refusals do not halt** (D-31, D-36, Edith N47). | `evidence` §6d 6(4), D-27, D-36, N47 | Dollar caps are the user's money. |
| 26 | 6 | A line to remove | Remove the drafted halt trigger "any `reasoning_extraction` refusal" in item 6: it contradicts D-31 and D-36 (refusals are counted, not a stop signal). | D-31, D-36, Edith N47 | It corrects a draft that disagrees with the rulings. |
| 27 | 8 | Interval method for the headline intervals and p-values? | **Superseded by section 7b (D-68 F4): the p-values and bounds of the five tests come from the paired BCa bootstrap with p from the inverted bound; the sign-flip is kept only for d = 0.** Paired base-puzzle bootstrap (percentile intervals, 10,000 draws) for every headline interval; a sign-flip permutation test across base puzzles for the p-values; exact binomial intervals for a single setup's accuracy (Opus may fail only about twice in 40); the mixed model is a sensitivity check. If Opus is near 100% and the mixed model will not fit, report the counts and the bootstrap interval. | `check-precision.md` problem 4; ours | The pre-registration must name one method, not a menu. |

**What is not in this sheet:** the exact text of the prompt-variant check (item 10; drafted in PR #14, cleared by Edith, checked free,
then the user's yes) and the Edith-cleared spend guard (PR #11). Item 5's headline axis is partly settled through D-33; rows 22 to 24
are the rest.

---

## 1. Task family

### 1a. Which kind of task

**RULED**
- **D-15** (2026-10-10): the puzzle is Friday's digit puzzle: values are digit strings, with a printed
  rulebook of maths, lookup-table and shuffle rules (option A). Letters, words and Reasoning Gym
  composites were rejected. The user: "yes, go with option A, the digit puzzles".
- **D-19** (2026-10-10): keep the digit puzzles and turn the difficulty dials up first, testing free on
  the Max plan. If harder digits don't work, move to code tracing. The user: "Let's turn up the digits
  first and see what happens ... Otherwise, we can go to code tracing."
- **D-20** (2026-10-10): digit ("rule-following") puzzles are the main test, plus code tracing as a
  second task family on a smaller subset. The user: "I feel I like using both the rule-following
  puzzles as the main test, plus code tracing as a second family test. That's good." (Section 11.)

**DRAFTED, NOT RULED**
- **What a puzzle is.** *(Proposed by Friday; backed by `harness/taskgen/README.md` and its self-test,
  reviewed CLEAN by Edith in `ops/reviews/2026-10-10-pr1-taskgen-r2.md` and
  `ops/reviews/2026-10-10-pr2-dials-r2.md`.)*
  - Every value is a string of digits, for example `0472`.
  - The prompt prints a rulebook of up to four kinds of rule: *arithmetic* (multiply by a number, add a
    number, keep the last n digits), *digit table* (replace each digit using a 10-entry table), *pair
    table* (cut the value into pairs of digits and replace each pair using a 100-entry table) and
    *shuffle* (reorder the digits).
  - Then it lists sequences, such as "Start at 8516. Apply A, L, H, K." The model applies each sequence's
    rules in order, lists the value after each rule, and ends with one numbered line, `Answer: 1 = v, 2 = v, ...` (D-31; the exact wording is drafted in item 4).
  - D-15 describes "maths, lookup-table and shuffle rules". The pair table is a lookup table, so it fits
    that wording, but the register does not name it.
  - The register's note on D-15 (2026-10-10): "The prototype happened to use 4-digit values; how many
    digits a value has is a difficulty dial (D-16, D-21), and the standard level is about d4 (8 digits)."
- **Why these puzzles are fair to the structure question.** *(Friday; `taskgen`.)*
  - Every rule is a bijection (one wrong step always makes that sequence's final value wrong).
  - A simulation guard rejects any rule order in which steps could be skipped, so a chain cannot be
    shortened by algebra and the sequential shape is not secretly easier.
  - A separate re-solver parses the printed prompt and checks the stored answer for every puzzle.
  - The same seed gives the same rulebook and the same 24 rule applications at every wiring. Only the
    cut points and start values differ.
- **Seeds and sets.** *(Friday; `taskgen`.)* Item seeds come from `derive_seed(set_id, idx)`, a SHA-256
  hash, never `seed + idx`. The pilot set and the main set use different `set_id`s, so they share
  nothing. The generator version string (now `taskgen-proto-0.3`) is bumped whenever a seed's output
  changes, and the final frozen version is written into this spec at lock time. Frozen sets go in
  `data/tasks/<set-id>/` (`taskgen`, "Limits of this prototype").
- **No reliance on Reasoning Gym.** Reasoning Gym has no generator for modular, lookup or permutation
  steps (`facts`, corrections 1 and row 7b), so the spec names our own seeded generator only.
  *(Karen; `facts`.)*
- **Smaller maths steps (D-25).** The standard level is built by making the maths steps smaller, with
  difficulty coming mainly from lookup tables and shuffles (D-25, quoted in item 2). Candidate presets
  `d4s` and `d4p` are being added in a separate draft PR (not merged).
- **The generator we have is a prototype.** Preset d4 (8 digits, multipliers 1001-9999, 24 printed rules,
  each used once, prompt about 7,689 characters at 24×1 and 6,972 at 1×24) is the working candidate for
  the standard level (`presets`). D-21 names "about d4" but does not fix the preset.

**OPEN**
- Nothing: settled by D-48 (sheet rows 1, 8, 16).

### 1b. Number of steps and shapes

*Amended 2026-10-12 (Deviation 1, under "Amendments"; D-86, D-87): the main study uses **N steps**, with N chosen from
{4, 6, 8, 12, 16} by the ladder pilot. The two shapes are **N×1** and **1×N**, with 80 base puzzles × 2 shapes at the chosen N.
Below, 24×1 and 1×24 read as N×1 and 1×N. The 24-step text is kept as locked in `prereg-lock-1`.*

**RULED**
- **D-24** (2026-10-10): use **two shapes**, not four wirings. "Separate pieces" is **24×1** (24
  independent one-step jobs in one prompt) and "one long chain" is **1×24**, with **160 puzzles = 80 base
  puzzles × 2 shapes**. The in-between wirings (6×4 and 2×12) are dropped and named as future work. The
  user: "yes go with the two shapes , I hope it will make our research more reliable and more constructed
  so that a reader will not get confused with different things." The register adds a limit to state in the
  paper: "separate pieces" here means separate one-step tasks.
- **D-26** (2026-10-10): "separate pieces" stays as 24 one-step tasks (24×1). The paper labels it honestly as
  separate small tasks, and bigger separate tasks are named as a limit and future work. The "6 tasks of 4
  steps" alternative is not pursued. The user: "Okay, we can keep the one-step version and label it
  honestly."
- **D-16** (2026-10-10), the part that still stands: keep **24 steps** per puzzle and make puzzles harder
  by turning the per-step dials (digits, multipliers, tables, rulebook), not by adding steps. The user:
  "Yes, keep 24 steps and make the dials harder." D-24 replaces D-16's four wirings; the register marks
  D-16 "ruled, partly replaced by D-24".

**DRAFTED, NOT RULED**
- **Why two shapes (the register's reasons):** about 30% tighter answers per shape at the same cost, 80
  distinct rulebooks instead of 40, and a clearer buying guide. The 30% is per shape and for the structure
  effect. For the overall vote-vs-Opus headline the gain is only about 11 to 14% (±4.4 to ±3.8 in world
  (i), ±6.5 to ±5.8 in world (ii-mod); `analyse-precision.md` §2, as noted in
  `ops/reviews/2026-10-10-design-check-review.md`, E3).
- **What two shapes cannot show.** A gradient: whether the chain penalty grows gradually or jumps at some
  length. H3 and the brief's "structure knob" are claims about a gradient. With two endpoints the paper
  must say so (`ops/reviews/2026-10-10-design-check-review.md`, E3; ours). Under D-26 the paper also states
  the limit that "separate pieces" are separate one-step tasks, the most vote-friendly case possible, so the
  guide may overstate cheap voting for bigger separate tasks (Haiku got 96% of single pieces right,
  `check-setups.md` P1); those are future work.
- **No hard slice.** D-27 takes the D-21 fallback (the standard level alone), so no second hard level is run
  and both shapes use the one standard level.
- **Equal-work check.** *(brief, "Draft design"; `check-setups.md` P9.)* The brief checks that single-Opus
  accuracy stays flat across structure levels. At the standard level Opus is near ceiling (19 of 20 at d4,
  `LOG.md`), so that check cannot show a difference there. `check-setups.md` suggests running it on single
  Haiku tries at the standard level (the Opus-at-hard-level half no longer applies without a hard slice).
- **Reporting.** Accuracy and cost per shape, under both scorings (D-23). The 24×1 view per piece is
  likely near ceiling for every model (`ops/reviews/2026-10-10-design-check-review.md`, "D-23").

**OPEN**
- Nothing: settled by D-48 (sheet rows 17).

### 1c. The two shapes are matched

**RULED**
- **D-28** (2026-10-10): matched design. Each of the 80 base puzzles appears in both shapes, with the same
  rulebook and the same rules in the same order; only the wiring and the start values differ. The analysis
  is paired by base puzzle (a base-puzzle bootstrap or a random effect for the base puzzle). The user: "yes
  go with A". The register's reasons: a sharper shape comparison at the same cost, and "same puzzle, only the
  wiring changes" holds literally. The cost is 80 distinct rulebooks instead of 160. The pilot measures how
  alike the two shapes behave (ρ), and the paper reports it.

**DRAFTED, NOT RULED** *(supporting figures for the ruled design)*

Terms: **world (i)** = Haiku's wrong answers are scattered and every puzzle is equally hard for Haiku;
**world (ii-mod)** = puzzles differ moderately in how hard they are for Haiku (definitions in
`analyse-precision.md`, "Assumptions"). **Margin** = how far the 95% interval reaches on each side of the
estimate, in accuracy points. **Smallest detectable gap** = the smallest true difference our test would call
significant (5% level, two-sided) in 80% of repeat studies, estimated by simulation. **ρ** = how strongly a
setup being right on one shape of a base puzzle predicts it being right on the other shape of the same
puzzle.

- **Why the pairing is a gain:** the two shapes are compared on the same puzzles, so puzzle difficulty
  cancels out of the structure effect. How much it gains depends on ρ, which is unmeasured. The two end
  shapes share the rulebook and the rule order but no actual arithmetic, so ρ is probably low, which moves
  the figures towards the ρ = .2 values below (`check-precision.md`, "How the matched design is handled").
- **Figures for the matched design** (80 base puzzles × 2 shapes; margin / smallest detectable gap, world
  (i) then (ii-mod)):
  - Vote vs Opus within one shape: ±4.7 / 7.0, then ±7.4 / 10.6 (`check-precision.md`). Each puzzle is seen
    once per shape, so ρ drops out of the per-shape numbers.
  - Structure effect for Opus-medium (24×1 minus 1×24): ±6.0 / 8.7 at ρ = .2 (`check-precision.md`); about
    ±4.9 / 6.9 at ρ = .5 (`analyse-precision.md` §3).
  - Does the best setup differ by shape? (interaction margin): ±6.1 then ±9.2 at ρ = .2; ±4.7 then ±7.4 at
    ρ = .5 (`check-precision.md`, problem 7).
  - Overall vote-vs-Opus headline across all 160 puzzles, ρ = .2: ±3.8 / 5.4, then ±5.8 / 8.3
    (`analyse-precision.md` §2; not independently re-run).
- **Considered and not chosen:** an unmatched design (80 different puzzles per shape, 160 distinct
  rulebooks). Its reference row, "160 independent puzzles, unpaired", gave a structure-effect margin of
  ±9.7 in the earlier 40-per-wiring layout (`analyse-precision.md` §3), wider than the matched ±6.0 unless ρ
  is near 0. Cost is the same either way (`check-cost.md` §6).

**OPEN**
- Nothing about the matched design itself. If the pilot finds ρ extreme, it is reported and the design is
  unchanged (D-36, item 6 of the pilot protocol).

---

### 1d. Rules of the same kind back to back

**RULED**
- **D-43** (2026-10-10): two rules of the same kind may sit back to back in a puzzle, as the generator builds them,
  and the method section says so. The user: "yes to both, go with your suggestions". The register's reason: the
  generator allows it, and Edith's shortcut checks found no loophole (the multiplier range limit stops two maths
  steps collapsing into one easy step; `harness/taskgen/README.md`).

**DRAFTED, NOT RULED**
- The paper's method section states it in one sentence (Edith's Q1 wording): "two different rules of the same kind
  may follow each other, but never the same rule twice. A simulation guard rejects any sequence in which a run of
  steps, any two or three steps, or all the steps of one kind within a run can be left out, and an exhaustive search
  of larger sets in 2,000-plus puzzles found none."

**OPEN**
- Nothing.

---

## 1e. The ledger family (D-56 to D-60, D-62 to D-64, D-77 to D-80): the main task family

*DRAFT by Friday for Edith's check, then the user. Nothing below is decided until the user says yes to it. Where this section and
sections 1a to 1d differ, this section is the proposed text and 1a to 1d (the digit puzzle) are superseded as the main test.*

**What changed and why.** D-56 replaces the digit rule-following puzzle with the ledger family as the main test, because smoke-2
showed the digit wording was refused with category `cyber` by Opus (2 of 2) and Sonnet (1 of 2) on the API. D-59 drops the
code-tracing family (the study has one family; the paper states that as a limitation). D-58 as amended by D-63 and D-79: no backup family is
named; if any call of the 20-call check (below) is refused, the check stops and no other family is probed. The switch to **the user's other
research idea** in the same repo is **not automatic** (D-79): the user decides between switching and continuing Study 1 with refusals counted
and reported (asking Anthropic support is still allowed; any deletion is confirmed with the user first, with the state tagged in git).

**The puzzle.**
- The state is a list of whole-unit balances of 3 to 12 budget lines (names fixed in this order: Rent, Payroll, Supplies, Reserve,
  Travel, Training, Utilities, Insurance, Fuel, Repairs, Software, Legal). No currency symbol, no people, no transfer to anyone.
- The rulebook has 24 rules, each applied exactly once per puzzle, labelled A to X in a random order (so the printed order does not
  give the order of use). A preset may also print up to 8 *decoy* rules that no sequence uses (labels then run A to Z and AA onward);
  each decoy is a near-duplicate of a used rule that differs in one detail (the rounding, one line, a percentage or an amount). The
  intro says so: "Not every rule below is used: each sequence names the rules it applies."
- Rule kinds (25). Every rounding is named in the rule's sentence ("rounding the amount down to a whole unit", or "to the nearest
  whole unit (a half rounds up)"); a move never takes more than the line holds ("or all of X if it holds fewer"); a balance never
  goes below 0; ties for the largest or smallest line go to the line listed first. The plain kinds are percent moves (down or nearest),
  top-up to a threshold, two-clause (above a threshold move a percent, otherwise add), fee on the largest line, interest, equal split,
  fixed payment, levy, boost the smallest, cap and move the excess, level a pair, largest to smallest, first line below a threshold,
  percent of a combined balance, compare-and-move, share of a difference and a three-way threshold. The free reads showed Haiku near
  90% on lines and compound rules alone (reads 1 to 3), so the harder presets add kinds that ask more of a single step, with round
  numbers (D-62: difficulty from procedure, not from arithmetic):
  1. look again: "Move 400 units from the line with the largest balance to the line with the smallest balance, or all of it if it holds
     fewer; then remove 500 units from the line that now has the largest balance, or all of it if it holds fewer.";
  2. repeat: "Do this five times in a row: move 1400 units from the line with the largest balance to the line with the smallest balance,
     or all of it if it holds fewer. Find the largest and the smallest line again each time." (three, four or five times by preset;
     the amount is larger than the deciding gap, so the pick really changes);
  3. in-turn sweep: "Go through the lines one at a time, in the order above. Each line whose balance is above 5200 when its turn comes
     gives 200 units to the line, other than itself, that has the smallest balance at that moment." (2 to 4 givers and a change of
     receiver are required at the reference state and at every piece start);
  4. simultaneous update: "Work out the average of all the balances, rounded down to a whole unit. Every line whose balance is above
     the average gives 25% of its own balance, rounded down to a whole unit, to the line with the smallest balance. Work out the average,
     the smallest line and every amount from the balances before this rule, not from balances changed during it.";
  5. rank: "The line with the second-largest balance gives 40% of its balance, rounded down to a whole unit, to the line with the
     second-smallest balance. Where balances are equal, the line listed first in the order above counts first, whether counting from the
     largest or from the smallest.";
  6. count-then-act: "Count the lines whose balance is below 4200. Move that count times 50 units from Repairs to the line with the
     smallest balance, or all of Repairs if it holds fewer. Count the lines and find the smallest line before moving anything."
- **The house rule (the harder presets only).** One sentence printed once in the intro: "House rule: straight after every rule, as part of the
  same step, if the line with the smallest balance is below 3700, move 300 units to it from the line with the largest balance, or all of
  that line if it holds fewer. The house rule acts at most once per step, always after that step's own rule, and does not act again on its
  own result. If the largest and the smallest line are the same line, nothing moves. The balances you write for a step are the ones after the
  house rule." The threshold and the amount are tuned per puzzle so that it acts on a stated number of the 24 reference steps (5 to 8; for
  l16, 9 to 12). **So in these presets each step is two operations, the rule and then the house rule,** and the value written after step k is the
  state after both. The closing says so ("Reply with the balances after each rule and its house rule"), the grader scores that state, and the
  step-wise (E3) prompt includes the house rule. Every guard below treats rule plus house rule as one step.
- A sequence is `N. Start at [balances]. Apply J, X, Q, ...`. The rulebook's wording is the contract: an independent re-solver
  (`harness/taskgen/ledger_check.py`, written separately from the generator) reads only the printed prompt, including the house rule, and
  must reproduce every stored state.

**Shapes (unchanged in spirit, 1b/1c).** 24 steps always (D-16). 1×24 is one chain starting at the reference balances; 24×1 is 24
single-rule pieces, each self-contained: each piece starts from the reference state before its step, moved by up to ±25% on every
line and redrawn until the rule (with the house rule) changes the state and, for the look-again, repeat and sweep rules, the pick really changes,
so no piece starts from a chain state. Same 24 rules in the same order at both shapes; the pieces' starts are shape-specific. Scoring: at 24×1 a puzzle is right
only if every piece's final balances are right (D-39); at 1×24 the official score is "all step lines right" (D-76, section 7b).

**Reply format (D-31/D-40, unchanged except the house rule).** The model writes the balances after each rule (and its house rule), one per line
(`1.1 = [..]`, `1.2 = [..]`, ... for a chain), then `Answer: 1 = [..]` (or `Answer: 1 = [..], 2 = [..], ..., 24 = [..]` for the pieces). The
answer-only fallback (D-36(5)) asks for just the `Answer:` line; it is triggered only by `reasoning_extraction` blocks above 2% of any model's
answers and never by `cyber` or any other category. Both texts, for the preset the check uses (l16), are in `data/examples/prompts-ledger/` and
the wording of both is **approved (D-77, L4)**.

**Slip analysis (D-39(6), descriptive and exploratory).** For every wrong answer the grader records the first wrong step, the rule kind at
that step (and, for presets with a house rule, whether the slip was in the rule or the house rule), and whether the slip was a wrong
largest/smallest/rank pick or an arithmetic slip. Reported per model and per shape: the first wrong step and its rule kind; the share of
first slips that are picks versus arithmetic; and Haiku's wrong-answer repeat share across its 10 tries per puzzle (it matters for the vote).
The free reads were used to design the puzzles, so they are excluded; only the frozen main-run sets count.
**Disclosure (Karen, `research/tuning-fairness.md`).** The ledger's difficulty was tuned on a Haiku-only free read (Max plan), and its harder rule kinds were
added after Haiku's slips; the paper says so. The pilot reports per-rule-kind slip rates for Haiku and Opus (free, from the step values), Haiku's
repeat share, and H1 per preset, so a reader can see whether the tuning favours or hurts the vote.

**Edith's build conditions (L1 to L5), as built (generator ledger-0.4).** ledger-0.4 fixes Edith's second review of the generator (PR #19,
D-76); it adds no rule kind, dial or preset and leaves every approved sentence template byte for byte as it was (a test pins the templates).
- L1: every step (rule plus house rule) changes the state, on the reference chain and on each piece, and so does the rule without its house rule
  (the house rule never hides a rule that does nothing, Edith M4); a brute-force search over the printed rules finds no 1, 2 or 3 steps and no
  stretch of 4 or more steps that can be left out (on the reference start and five jittered starts).
- L2: absorption is measured on the composite step by simulation and capped at 5%. Three measures: (i) one unit added to or removed from one line
  at the start (k = 0) or after each step k = 1..23, on the reference chain and five jittered starts; (ii) **transfer slips (Edith's B1)**: 1, 10
  or 100 units that belong on one line sit on another, for every ordered pair of lines the step changed, at k = 0..23, **capped at 5% for each
  size separately on the reference chain** (the chain the 1×24 shape uses; not on the jittered starts, where no rulebook met a per-size cap on
  all six); (iii) **house-rule slips (Edith M3)**: the house rule left out, or applied twice, at one step, capped at 5% on the reference chain.
  Almost every rule keeps the total, so (ii) is the slip that really happens. Under D-76 these caps bound the gap between the official
  step-line score and the secondary final-answer view. Rulebooks over a cap are redrawn; three interim presets could not meet the cap and were
  retired (the generator and `freeze` refuse them). At most 3% of cells may be zero; no rule kind more than a per-preset number of times; no run
  of three rules of one kind; at most a few overwrite-type rules.
- L3: rounding and ties are in the sentences; no negative balance; a tie that decides a largest/smallest/rank pick (at the step, inside a
  look-again or repeat rule, at each turn of a sweep, and on the house rule's pick) and an exact threshold or comparison hit are redrawn (B3,
  B4); ties elsewhere in the state are allowed, since no pick depends on them. The fixed-amount repeat never undoes itself: no move reverses the
  one before and no shorter run gives the same result (Edith M2). On a piece, the house rule acts exactly when it acts at that step of the chain
  (Edith m4). The independent re-solver checks all of this from the printed text; the neutral-word scan (`prompt_d31.BANNED`) and no `$`;
  `freeze --verify` rebuilds every frozen item from its seed, compares every stored field and runs these checks, and refuses a set made by
  another generator version (B5).
- Totality (Edith X1): generation is deterministic and total up to a fixed number of draws; the accepted draw number is stored in each item; a
  rulebook is accepted only once every 24×1 piece has a start, and the 24×1 shape uses exactly those starts, so both shapes always share the
  rulebook.
- L4: the exact wording (the rule sentences above, the intro with the house rule, the closings, the E3 step prompt) is **approved (D-77)**; after
  the re-freeze Edith re-verifies that every rendered sentence matches an approved template word for word, and any wording change goes back to the user.
  The compare_move sentence of l14 (and its ext40 set), "If X is more than twice Y, move N% of X to Y; otherwise move N% of Y to Z. Each amount is
  rounded down to a whole unit.", is **approved under D-80**, a decision the user delegated. The repeat rule's count word ("three" in l14 and
  l15, "five" in l16 and l17) is covered by D-77.
- L5: token lengths per preset and shape are measured on frozen scratch sets (`data/ledger-measured.json`) before the budget is re-locked.

**Presets** (the pilot picks the final one under D-36; tie-break per D-62 and Karen's plan: fewer rule kinds, then the shorter mean prompt). The
free Haiku reads (Max plan, one try each, whole answers right, not API results) are on the right.

| Preset | Lines | Digits | Decoys | House rule | Kinds | Free-read result (Haiku) |
|---|---|---|---|---|---|---|
| l1 to l9 | 4 to 12 | 4 to 6 | 0 | no | plain and compound | 49 of 54 right (reads 1 to 3) |
| l11 | 8 | 5 | 7 | no | percentages of 5-digit balances, repeat three times, average, rank, count | 2 of 6 (read 4) |
| l14 | 6 | 4 | 0 | acts on 5 to 8 steps | round numbers: look again, repeat (3), average, rank, count | 5 of 6 (read 5) |
| l15 | 8 | 4 | 6 | acts on 5 to 8 steps | same, with more look-again rules | 4 of 6 (read 5) |
| l16 | 10 | 4 | 8 | acts on 9 to 12 steps | adds the in-turn sweep; repeat five times | 8 of 12 (read 6: chains 3 of 6, pieces 5 of 6) |
| l17 | 12 | 4 | 8 | acts on 11 to 14 steps | more sweeps and look-again rules (the spare rung) | not read |

l14's compare_move sentence ("If X is more than twice Y, move N% of X to Y; otherwise move N% of Y to Z. Each amount is rounded down to a whole
unit.") is approved under D-80, a user-delegated decision. The repeat count word ("three" or "five") is covered by D-77.

l10, l12 and l13 were interim presets (percentage repeats); they cannot meet the transfer-slip cap and are retired. Pilot slots (Karen's plan):
A = l16 (20 puzzles), B = l15 (20, cut to 10 by shrink step 1), C = l14 (10), spare rung = l17 (10, runs only if every pilot preset comes in
above 60% on the API).

**Sets.** `pilot-ledger-<preset>-v1`, `check-ledger-l16-v1` (5 base puzzles x 2 shapes) and `smoke3-ledger-l16-v1`: pairwise disjoint
(`freeze --disjoint` on every pair), each its own set id, never reused.

**The 20-call check (D-57, D-58 as amended by D-63 and D-79, D-60, D-64, D-78).** 5 base puzzles x 2 shapes of `check-ledger-l16-v1`; Opus-medium x1 and
Sonnet-medium x1 on each, 20 calls, real time, one call at a time, in a fixed order (Opus 24x1, Opus 1x24, Sonnet 24x1, Sonnet 1x24, for each
base puzzle in turn). It stops at the first refusal of any category (D-58 as amended by D-63 and D-79): no rewording, no retry, no other family in the
same session. Run again in the same folder, the command sends nothing if the log holds a refusal (there is no flag for that), and resumes after
an "incomplete" result only with an explicit `--resume-incomplete`. An API error is retried under the harness rules (up to 3 attempts, each
reserved and logged) and is not a refusal; a call that still has no outcome after that, or a guard or cap stop, ends the check as "incomplete" and
comes back to the user. A wrong, truncated or unparseable answer does not stop it (the check asks about refusals, not accuracy). Expected spend
about $3; **cap $11 (D-64, D-78; set in Edith's clearance)**, because the guard books each call's worst case before sending
it: at the check's `max_tokens` (32K for Opus and Sonnet) the 20 calls' worst case is about $10.2 at list. Edith's clearance and the user's
separate "go" come first. Command: `python3 -m harness.pareto.apicheck plan|dry|live` (`harness/pareto/apicheck.py`).

**The check ran before the lock (D-78); its record.** Run `check-ledger-1`, 2026-10-11 10:16 to 10:37 UTC, from commit `e1d6d60`, under
Edith's clearance (`ops/reviews/2026-10-11-clearance-check-ledger-1.md`), cap $11. Status complete: 20 of 20 answered, **0 refusals**, every
`stop_reason` `end_turn`. Cost $2.302126 (ledger). Tokens 71,002 in and 137,868 out; these are used only as cost information. The answers are
**sealed**, not read or graded, until the lock tag (D-69). SHA-256 of `calls.jsonl`:
`92dd68a5b002ba102b7d24e1905de1058e11f1bc84287ab0a0b9e0a628402d77`; of `check_result.json`:
`9b76b38f23b7151580f0572b7447b901f0a68efae4c5eed3d7bfdbec44c43dfd`. The check is excluded from every analysis.

**The S3 check Batch** (`harness/pareto/s3check.py`, set `smoke3-ledger-l16-v1`, 5 items: 3 Opus-medium and 2 Sonnet-medium, one Batch) exists
only so that the Console shows enough Batch spend for the guard's Console check. If it runs before the lock, the record says that it ran; its
items are excluded from every analysis, and its answers stay sealed for good (never read or graded, before or after the lock).

**Not decided here.** Which preset is the main one (the pilot decides); the S3 bill-check Batch set; whether the spare rung (l17) runs.

## 2. Difficulty calibration

> **Superseded for the ledger family** by section 1e (D-56, D-59, D-62) and `research/pilot-plan-ledger.md`. The digit and code text below is kept as history.

**RULED**
- **D-21** (2026-10-10), in principle: run the **standard level** (about d4, set so a single Haiku
  answer gets about 25 to 50% right) in full. Report difficulty as a measured dial, using each puzzle's
  Haiku single-try accuracy from its 40 samples, and state the crossover. Add a smaller hard slice only
  if the pilot finds a reachable hard target and money is left; otherwise fall back to the standard level
  alone (option A). The user: "yes, I agree with you for the standard level and full, and with your
  recommendations related to that." The register says: the exact calibration numbers, the hard target and
  the hard slice's size are fixed in the pre-registration before the pilot.
- **D-17** (2026-10-10): free rough tuning on the Max plan before the paid pilot. The user: "Yes, you can
  run the fine tuning with max helpers. and yes wait for Karen". The official setting comes from the
  paid pilot under real API conditions.
- **D-25** (2026-10-10), in principle: make the maths steps smaller (shorter numbers and multipliers). Maths
  steps stay in the mix, because mixing step kinds blocks shortcuts, but difficulty comes mainly from lookup
  tables and shuffles. The final settings are fixed from the pilot, which counts slips by step kind. The
  user: "yeah, I like what you suggested: changing the math steps to smaller steps, and that's a smarter
  way of approaching". The register's reason: the free tests found 1 maths slip in 30 placed slips.

- **D-27** (2026-10-10): no hard slice (the D-21 fallback). Quoted in item 3. The hard target, the hard
  slice's size and the go/no-go for it are therefore moot.

**DRAFTED, NOT RULED**
- **Calibration uses one Haiku try's accuracy only.** *(D-21 rules this in principle.)* The dial is each
  puzzle's single-try Haiku accuracy, measured from its 40 samples. No Opus number is used to pick the
  standard level. *(Proposed by Jarvis and agreed in D-21; `analyse-precision.md` (section 1) notes that 40
  samples make the single-try number tight.)*
- **A separate pilot set.** The calibration is run on a pilot set kept apart from the main set by seed
  (`checklist` §1 "Difficulty calibration"; `taskgen`).
- **Reporting by item difficulty is pre-registered.** Majority voting only helps where Haiku's most common
  answer is right, so results are shown by how often Haiku gets each puzzle right alone (brief, "Biggest
  risks"; `checklist` §1; consistent with D-21).
- **What the pilot must measure** *(the briefing's list; `check-setups.md` §6, `check-precision.md`
  "Corrected statements")*: the spread of Haiku's accuracy across puzzles (not just the average); how
  often Haiku's wrong answers repeat; tokens per call; Opus-medium
  on d4 through the API; the correlation between the two shapes; latency.
- **Evidence so far** (free Max-plan helper runs, rough guide only, not API calls; `LOG.md`):
  - d4, 20 puzzles: Opus fully right 19/20, Haiku 6/20.
  - d4 repeats (`data/free-tests/graded/answers.tsv`, round 4): 11 of 21 properly answered Haiku tries fully right, and all 10 wrong answers differed from
    each other. Sonnet was right 6/6. The sample is small.
  - Edith's re-grade reproduces these counts. Edith notes that "all 10 wrong answers differed" rests on only
    5 pairs that could have coincided, so it rules out only a repeat share above about 0.7 (Karen's definition: the share of wrong answers that
    land on one popular wrong value, `evidence` §2.4; `ops/reviews/2026-10-10-design-check-review.md`, E8, answered in the follow-up: no
    helper read the answer keys).
  - Opus sits near the ceiling at d4. A hard level aimed at Opus 55 to 75% is "probably out of reach" on
    these dials (`LOG.md`, design-check entry; moot without a hard slice). `check-setups.md` P10 lists levers that remain (10 to 12
    digits, dropping the arithmetic rules, two operations per step; the free-test archive shows 1 arithmetic slip in 30 placed across all free
    rounds: 0 in 20 in rounds 2 to 3, 1 in 10 in round 4 (`data/free-tests/graded/summary.md`; the one
    arithmetic slip is Haiku, puzzle y, 24×1, try 3, piece 18, in `data/free-tests/graded/answers.tsv`; the
    15 wrong chains are all traced to a first wrong step in `data/free-tests/graded/chain_first_slip.md`;
    `ops/reviews/2026-10-10-design-check-review.md`, "Follow-up", E1, and `ops/reviews/2026-10-10-pr3-spec-r1.md`,
    S8). These are helper runs, not API calls, so the pilot should confirm it before a hard preset drops
    arithmetic) and warns that the free runs used
    Claude Code's default effort, so API Opus-medium on d4 should be run first.

- **Consequences of D-21 recorded in the register** (Edith's review, E9): "40 samples" is provisional until
  item 3; the brief's Opus-medium 55 to 75% target is dropped at the standard level, so H1 would need to be
  framed as a non-inferiority test (suggested by `check-setups.md` P9; open, item 7; Edith notes the
  register's "becomes" in D-21 note (b) goes further than the evidence); and the fallback (standard level alone) cannot show where Opus starts to win.

**OPEN**
- Nothing: settled by D-48 (sheet rows 1, 2, 3, 16).

---

## Pilot protocol (between items 2 and 3)

> **Superseded for the ledger family** by section 1e (D-56, D-59, D-62) and `research/pilot-plan-ledger.md`. The digit and code text below is kept as history.

*D-36 rules the pilot protocol, on one condition: it must fit the overall budget. This section was to be
ruled first, because the pilot is the next money that moves. What D-36 does not settle is drafted or open
below.*

**RULED**
- **D-38** (2026-10-10): d4 (today's setting, big maths steps) is a reference point only, not a candidate; the
  preset rule chooses between d4s and d4p. The user: "for the d4 pilot or whatevr i will do with your suggestion".
  The register's reason: it follows D-25 (smaller maths steps), and d4 on 10 practice puzzles shows how much the
  smaller maths changed difficulty. This closes Edith's Z2.
- **D-36** (2026-10-10), the Study 1 pilot protocol. The user: "yes, go with the pilot rulebook as
  suggested as long as it is in the budget of the overall research". The register records:
  1. **Separate set.** Separate practice puzzles with their own `set_id`; nothing from the pilot enters the
     confirmatory analysis.
  2. **What is piloted.** Presets d4, d4s and d4p, about 20 practice puzzles each, both shapes; Haiku 10
     tries per puzzle; Opus-medium and Sonnet-medium one try each; a code-tracing slice of 4 base puzzles ×
     2 shapes, to measure tokens and thinking; the 10-puzzle real-time check (latency plus
     batch-vs-real-time).
  3. **Hard dollar cap of $30,** enforced by the spend guard. Karen and Friday fit the design under it, and
     Edith checks.
  4. **Preset choice.** The preset whose median single-try Haiku-medium accuracy is closest to 37.5%, among
     those in 25 to 50%. If none is in the band, take the closest when it lies within 15 to 60%; otherwise
     pilot one extra rung before the main run.
  5. **What the pilot may change.** Only the preset, how many extras fit (the D-27 ladder), and a switch of
     every model to answer-only if any model is safety-blocked on more than 2% of its answers (the D-31
     backup). It may not change hypotheses, confirmatory contrasts or margins. The pilot k is a sensitivity
     check only (D-33).
  6. **Surprises are reported, not acted on;** only money stops the study (the D-27 stop-loss). The register's
     D-36 notes quote the wording the user approved "as suggested": "If the pilot shows something
     unexpected, like Haiku repeating the same wrong answer often, or the two shapes behaving very
     differently, we run the main study unchanged and report it. That's what makes pre-registered results
     trustworthy. Only money can stop us, through the stop rule you already approved." So an extreme ρ,
     Haiku spread or repeat share is reported, and the main study goes ahead unchanged.
  7. **The first paid call** needs Edith's clearance and the user's "go".

  **Condition and its answer (register note on D-36).** The pilot had to fit the overall budget. Karen
  priced it (`evidence` §0, commit 97fed71) and confirmed the fit. The register note records:
  - d4s and d4p at 20 practice puzzles each (10 base puzzles × 2 shapes); d4 at 10 as a reference only (5
    base × 2 shapes). "About 20 each" is read as 20 practice puzzles per preset; 40 per preset would not fit.
  - **Pilot cost about $7 / $17 / $29 (low / central / high), under the $30 cap.**
  - Programme all in, central: musts $138 to $150; all four extras $154 to $166, under the $170 ladder; at
    most $181 if Haiku-max also runs, so under $200 in every central variant.

  **Per Jarvis and Karen's pricing (not in the register note itself):** Opus-medium ×1, Sonnet-medium ×1 and
  Haiku-medium ×10 per puzzle, through Batch; the code slice of 4 base × 2 shapes runs Opus-medium plus Haiku
  ×10, with no Sonnet in code (D-35); and the 10-puzzle real-time check is counted inside the pilot. If the
  numbers ever force a change, Jarvis brings the trade-off back to the user before any money moves.
- **Earlier rulings that apply to the pilot:**
  - **D-21** (quoted in item 2): the calibration numbers are fixed before the pilot; the hard target and the
    hard slice's size are moot under D-27.
  - **D-17:** the official difficulty setting comes from the paid pilot under real API conditions.
  - **D-28** (item 1c): the pilot measures ρ, and the paper reports it.
  - **D-33** (item 7): the vote size k comes from the main run's costs; the pilot includes a
    Batch-vs-real-time equivalence check.
  - **D-35** (item 3): the real-time subset is 10 puzzles, and the pilot includes a few code puzzles to
    measure how much the models think on code.
  - **D-27** (item 3): the extras ladder at $170 and the stop-loss; no hard slice.

**DRAFTED, NOT RULED**
- **Batch-vs-real-time equivalence check** (ruled by D-33 at 10 puzzles under D-35 and D-36; the design here
  is suggested by `evidence` §6b.3). Run the same 10 puzzles for Opus-medium and Haiku-medium ×5, both
  batched and in real time, and compare accuracy and tokens. Batch is not stated to behave identically to
  real time (the router, safety classifiers and sampling logic can differ), and this is the one real gap in
  the Batch plan. Related precautions, also from `evidence` §6b.3: interleave setups inside each batch, run
  all setups in a short window, log `request_id` and timestamps, log expiries per setup and resubmit them
  together, and report truncation per setup.
- **What the pilot measures** is listed in item 2 and in `evidence` §5. D-36 also names tokens and thinking
  on code.
- **The answer-only switch and "blocked".** D-36 sets the 2% line; item 4 and D-31 say what a block is and
  that blocks are counted, not a stop signal. The pilot reports block counts per model so the 2% line can
  be applied. Nothing more is drafted until item 4 settles its text.
- **Hard slice go / no-go: moot.** D-27 takes the fallback (no hard slice). If the user ever reopens a hard
  slice, Haiku's hard-preset accuracy must be measured first, because the hard-level vote-vs-Opus gap at k =
  20 runs from about -58 points to +28 as Haiku's accuracy goes from 2% to 20% (`check-precision.md`,
  problem 2).

**OPEN**
- Nothing: settled by D-48 (sheet rows 4, 5, 18, 19).

---

## 3. Setups

**RULED**
- **D-27** (2026-10-10), budget plan and item 3: Karen's list.
  - **Must-haves:** Opus-medium ×1, Opus-low ×1, Sonnet-medium ×1, Haiku-low ×40, Haiku-medium ×40, E3
    (a script splits the task, step by step, with lead-by-2 voting, cap 9), a small real-time latency subset,
    and the free offline analyses.
  - **Extras, added in this order only while the measured all-in total stays at or under $170:** (1)
    Sonnet-low ×1, (2) Haiku thinking-off ×40, (3) E2 (a stateless, Haiku-coordinated team), (4) Haiku
    picker over 8. Haiku-max ×3 is the first to trim.
  - **Dropped:** Opus-high, E1, the Opus-low picker, the picker over 16, Fable. **No hard slice** (the D-21
    fallback).
  - **Stop-loss:** if the must-haves alone would exceed $170 all in, stop and return to the user.
  - Estimate about $162 all in at central (all in = main run + pilot + code tracing + Study 5 + 5% allowance);
    see D-35 below for the later figures. (D-44 later removed Study 5 and freed its about $15.)
  - The user: "And yes, I am okay with the budget. It looks very nice." The register notes that Jarvis said
    beforehand that a yes to the budget plan also settles the setups list, and that the exact numbers (k,
    sample counts) can still move with the pilot under the equal-money rule and the pilot protocol, which
    are still open. Source: `research/study1-design-evidence.md` §0 and §3.7.
- **D-35** (2026-10-10), budget trims to D-27: (1) the real-time subset (latency plus the batch-vs-real-time check) runs on 10 puzzles, not 20; (2) Sonnet is left out of the code-tracing family, so the code setups are Opus-medium ×1, Haiku-medium ×40 and E3, while Sonnet stays in the main digit study. The user: "yes, take both trims also". The register's note (Karen's update, `evidence` §0, commit f358f85): code tracing at real prompt
  sizes costs about $31 to $44, so the D-27 plan was about $176 to $190 all in; with both trims it is about
  $166 to $178 (musts plus extras 1 to 4) or $151 to $162 (musts only), central. The $170 ladder and
  stop-loss (D-27) decide how many extras run. The pilot includes a few code puzzles to measure how much the
  models think on code. The latency subset in the must-have list above is therefore 10 puzzles.
- **D-20**: code tracing is a second family; its setups are in section 11.

**DRAFTED, NOT RULED** *(supporting detail for the ruled list. `evidence` is Karen's file.)*

*Words used.* **E3** = a script splits the puzzle into single steps and runs cheap-model votes on each
step (the "perfect decomposition" control, copied from MAKER; `options` §3.1). **E2** = a Haiku planner with
Haiku workers. A **picker** is a model that reads several sampled answers and chooses one.

- **Karen's estimated costs for the ruled list** (`evidence` §3.7; corrected tokens, Batch for single calls,
  160 puzzles; central dollars, which the pilot replaces):

  | Setup | Priority under D-27 | About $ |
  |---|---|---|
  | Opus-medium ×1 | must | 16.7 |
  | Opus-low ×1 | must | 7.1 |
  | Sonnet-medium ×1 | must | 8.3 |
  | Haiku-low ×40 | must | 10.9 |
  | Haiku-medium ×40 | must | 23.4 |
  | E3 step by step, lead-by-2 voting (cap 9), through Batch | must | 6.3 |
  | Real-time latency subset (10 puzzles under D-35) | must | about 3 for the earlier, larger subset; to be recomputed by Karen |
  | Offline analyses (both vote units, vote curves, repeat share, escalate-to-Opus-on-disagreement, break-even price ratio) | must | 0 |
  | Sonnet-low ×1; Haiku thinking off ×40; E2 (stateless); Haiku picker over 8; Haiku-max ×3 | extras, in this order (Haiku-max first to trim) | 6.2; 3.1; 4.9; 0.2; 13.9 |

  Musts about $76; musts plus extras about $104 (`evidence` §3.7).
- **E3 detail.** Lead-by-2 voting runs as step calls from the correct inputs through Batch (every rule is a
  bijection and the trace stores each step's input). Fixed-3 results are simulated offline. The split is
  free only because the puzzle lists its steps; the paper must say so (`evidence` §3.3).
- **E2 detail.** Stateless, cached, plans once and aggregates once, because Haiku's kept thinking blocks can
  push a long chain past 100,000 input tokens, where Haiku bills the whole request at 5× (`evidence` §3.4;
  `facts` rows 1e and 5b). Keep each model's conversation separate (`facts` row 5b).
- **Thinking off.** Possible on Haiku only, at high effort or below. Opus and Fable cannot disable
  thinking (`facts`, correction 2). Under D-31 the reply lists only the value after each step, so a thinking-off Haiku
  has little room to reason in its answer; read its results with that in mind (`check-setups.md` P6).
- **Effort labels are not comparable across models.** Effort is "a behavioral signal, not a strict token
  budget", and Sonnet 5.5's levels are "recalibrated" (`facts` row 2b). So contrasts such as Opus-low vs
  Sonnet-medium are read on the dollar axis, not as "effort level X vs Y". This is listed among the paper's
  limits. *(Proposed by Edith, S4; backed by `facts` row 2b.)*
- **Forbidden parameters, any setup.** Never send temperature, top_p or top_k; never force a tool choice;
  never send `fallbacks`; always set effort explicitly (`facts` rows 2b, 3, 3b, 5a; H-README rules 5 and
  6).
- **Which setups run on the code family:** see section 11.

**OPEN**
- Nothing: settled by D-48 (sheet rows 6, 7, 8).

---

## 4. Prompt and output format

**RULED**
- **D-31 (item 4, option B, kept minimal).** "Yes for item 4 we can go with your suggestion of keeping it
  minimal" and "Yes, and we should run the final wording past on the max plan itself." In the register's
  words: one frozen, plain-worded prompt for every model; the reply lists only the value after each step, then
  a numbered final answer line (e.g. "1 = 4821, 2 = 0937 …"); no "show your reasoning" or step-by-step
  wording, and no words about tests or grading. Three safety layers: (1) before the paid pilot, the exact final
  wording is run past Opus and Sonnet helpers on the Max plan, and any block means the wording changes first;
  (2) a pre-set backup: if the pilot shows blocks above a small set level for any model, every model switches
  to answer-only; (3) in the pilot, blocks are counted, not a stop signal. The block threshold and the exact
  text are fixed in the spec before the pilot (the register's note on D-31).
- **D-40** (2026-10-10): the exact prompt wording in PR #8 (`harness/taskgen/prompt_d31.py`) is approved. Chains:
  list "S.K = v" after each rule, then "Answer: 1 = v"; 24×1 pieces: the answer line only; the answer-only
  fallback text; the E3 step-call prompt; the code version uses "list/function" for "value/rule"; the banned-word
  list is enforced by the generator. The user: "and yes to the exact wording thingy". Evidence: the free wording
  check, 0 blocks in 26 runs, verified by Edith (`data/wording-check/`).
- **D-41** (2026-10-10): the free code-prompt wording check runs on the code family's solvers (Opus, Haiku), in
  small waves, stopping at the first block, with no rephrasing or retries. The user: "yes run the code wording
  check and merge both". **Done: 0 blocks in 8 runs** (`data/wording-check-code/README.md`, PR #12, light review by
  Edith pending); one run per cell, so the difficulty read is only a hint.
- **D-23** (both scorings are reported) fixes what the answer line must support: a whole-answer score and a
  per-piece score.
- *Evidence behind D-31 (Friday's free code test, `data/codetrace-free-test/README.md`; Edith's reviews of
  PR #7):* helpers asked to trace step by step and write out the working were stopped by a safety classifier in
  17 of 28 Sonnet/Opus runs (5 notices named `reasoning_extraction`; 12 gave no category); a plain wrapper was
  stopped in 0 of 16; Haiku in 0 of 28; the digit wording was never blocked in 130 free runs. These are Claude
  Code helpers, not API calls, so the API behaviour is unmeasured. `reasoning_extraction` refusals are billed
  (`facts` row 2e).

**DRAFTED, NOT RULED** (proposed by Friday under D-31; Edith has not yet cleared the text; the user says yes to
the exact words before they are frozen)

*The prompt, digit puzzles.* Four parts in this order, unchanged from the prototype except the last
paragraph (`data/examples/prompts-d31/` has full examples):

1. The opening paragraph (unchanged): `Every value here is a string of exactly 4 digits, such as 0472. Leading
   zeros count. When a rule does arithmetic, read the value as an ordinary number (0472 is 472) and write the
   result back with 4 digits.` (4 is the preset's digit count.)
2. `Rules`, then the rule lines (for example `A: multiply by 81, add 683, then keep only the last 4 digits.`).
3. `Sequences`, then one line per sequence (`1. Start at 8798. Apply J, F, L, …`).
4. The closing paragraph, by shape:
   - **One long chain (1×24):** `Apply the rules of sequence 1 in the order listed, each to the value the rule
     before it gave. Reply with the value after each rule, one per line, written `1.1 = v`, `1.2 = v`, and so
     on (the first number is the sequence, the second is the rule's place in it). Then end with one line,
     `Answer: 1 = v`, giving the value the sequence ends at.`
   - **Separate pieces (24×1):** `Each sequence is one rule applied to its start value, and the sequences are
     separate. Reply with one line, `Answer: 1 = v, 2 = v, ..., 24 = v`, giving the value each sequence ends at,
     in order.` (Each piece is one step, so its step value and its answer are the same number; asking for both
     would only repeat it. OPEN, below.)
   - **Several sequences of several rules (not used by the two-shape design; kept for the generator's other
     wirings):** the chain text with "of each sequence", "Each sequence is separate", and
     `Answer: 1 = v, 2 = v, ..., k = v`.

*The prompt, code tracing.* The same four parts; the opening paragraph becomes `Every value here is a list of
L whole numbers, each from 0 to M-1, such as [4, 72, …]. Each function below takes such a list and returns a new
list. Read each function as ordinary Python.`, then the printed `def …` functions, `Sequences`, and the same
closing paragraphs with "rule" → "function", "value" → "list", and the step and answer lines written as lists
(`1.1 = [..]`, `Answer: 1 = [..]`). The code generator is built under D-32 (separate PR); the text above is the
template it must produce.

*The step-wise team's prompt (E3).* The script sends one rule and one value per call, nothing else
(`data/examples/prompts-d31/digits-step-call-e3.txt`): the opening paragraph, `Rule`, the rule line,
`Value`, the value, then `Apply the rule to the value. Reply with one line, `Answer: v`, where v is the new
value.` The code version sends the function source and the list in the same shape.

*The pre-set backup (D-31 layer 2).* Same puzzle, closing paragraph replaced by an answer-only one:
`Apply the rules in the order listed, each to the value the rule before it gave. Reply with one line,
`Answer: 1 = v`, where v is the value the sequence ends at.` (and the pieces version). Every model switches to it
together, so no model is compared with another across two prompts.

*Words.* The prompt contains none of: grade, score, evaluate, test, benchmark, check, correct, judge, mark,
exam, quiz, reason(ing), think, "step by step", cipher, encrypt, password. The generators' self-tests scan for
them, including the closing paragraphs and the backup. This is about the puzzle prompt only; this document may
use such words. No system prompt beyond the puzzle is proposed *(ours, unbacked)*. Why the grading words stay
out: in the Opus 5.5 system card, grading awareness was voiced in 84.0% of transcripts when grading was clearly
stated, 73.1% when implied and 4.5% when barely or not disclosed (`facts`, row 4).

*Reading the reply.* The last line starting with `Answer:` is the answer; entries are matched by their number
(`1 = …, 2 = …`), so a dropped entry does not shift the rest. The whole answer is right only if the entries
are exactly 1…k and all match; the per-piece score counts the entries that match. Step lines `S.K = value`
are used only to place the first wrong step and its rule kind (the "almost never the maths" finding); missing
or badly formatted lines count as wrong, never a crash (`checklist` §2b). Parsers and scoring:
`harness/taskgen/prompt_d31.py` (`parse_answer`, `parse_steps`, `score_answer`, `first_wrong_step`, `numbering_problems`). A reply whose step
numbers cannot belong to the puzzle (a start at `1.0`, a run on to `1.25`) is flagged and no slip is placed.

*What counts as a block (for layer 3 and the threshold).* A call whose response has `stop_reason: "refusal"`
(any category), or an error response that names a safety or policy reason. Counted per model and per task
family, and **reported by category** (`stop_details.category`), with the cost of each (some refusals are billed,
`facts` correction 4). Not blocks: API, network or empty-body errors (429, 5xx, timeouts), which are retried under
the re-run policy (item 5); an empty reply with a normal stop reason is a failure, not a block unless a safeguard
is named. Truncated replies are failures but not blocks. `max_tokens` leaves room for thinking, within the 128K
limit; truncations are logged (`facts` rows 2d and 9; H-README rule 6) and the harness must show it never binds
(`options` §3.1).

*The block threshold for the backup (layer 2): RULED under D-36, point 5.* In the register's words, the pilot
may change "a switch of every model to answer-only if any model is safety-blocked on more than 2% of its
answers (the D-31 backup)". So the threshold is **more than 2% of one model's answers**, over that model's pilot
calls. The decision is made when the pilot ends, not call by call (layer 3). *(My earlier suggestion of 5% and
at least 3 is replaced.)* At the priced pilot (d4s and d4p at 20 puzzles each, d4 at 10, the code slice and the
real-time check), Opus and Sonnet give about 50 to 70 answers each, so one block is 1.4% to 2.0% and does not pass
"more than 2%"; it takes two. (Count from Edith's Y1; the answers per model are Karen's pilot sizes, to be
confirmed when the pilot is built.) Haiku gives many more answers (10 tries per puzzle), so its switch level is a
larger number of blocks.

*The free wording check (layer 1): DONE 2026-10-10, on the digit prompts.* After Edith cleared the text (PR #8
round 1), 26 fresh helpers on the Max plan read one puzzle file each and "replied exactly as it asks". Puzzles: the
new presets d4s and d4p, each as a 1×24 chain (two puzzles), a 24×1 set of separate pieces and a 1×24 answer-only
puzzle. Helpers: Opus, Sonnet and Haiku. **0 blocks in 26 runs** (replies saved, `data/wording-check/`). The
first two helpers (Opus and Sonnet, bare instruction) used code to solve it, so they say nothing about the
hand-written reply; the other 24 were told not to run code. Stop-at-the-first-block, no rephrasing and no
retries were the rules throughout. The code-tracing prompt is checked the same way once its generator exists
(D-32). Rough first read of how hard d4s and d4p are, free and tiny: `data/wording-check/README.md`.

**OPEN**
- Nothing: settled by D-40 (the exact text), D-48 rows 20 (a blocked-calls-left-out sensitivity view of H1 and the Sonnet contrast) and 21 (no summarised thinking).

---

## 5. Cost accounting

**RULED**
- Nothing in this item is ruled yet.

**DRAFTED, NOT RULED** *(All proposed in the brief, "Measurement" and item 5; backed by `facts` and
H-README as cited.)*
- **The cost axis is realised dollars per task.** Cost = the usage the API logs for each call × the pinned
  list price. Prices are pinned with their check date and re-checked against the live pricing page before
  every paid run (`facts`; `checklist` §3).
  - Per million tokens, input / output: Haiku 5.5 $0.10 / $0.50, Sonnet 5.5 $2 / $10, Opus 5.5 $4 / $20,
    Fable 5.1 $10 / $50 (`facts` rows 1a to 1d).
- **List price is the headline.** The Batch discount (50% off) and prompt caching are shown as sensitivity
  analyses (`facts` rows 1f and 1g; H-README rule 7: "The headline cost is the list price either way").
- **Thinking tokens are billed as output**, even when hidden (`facts` row 2d).
- **Haiku's long-prompt rule:** a Haiku request over 100,000 input tokens (cache reads and writes count)
  is billed at the higher rate for the whole request, output included: $0.50 / $2.50 (`facts` row 1e).
  The cost model includes it.
- **No extra modifiers.** `inference_geo: "us"` (1.1×) and fast mode (2×) are not used (`facts` row 1h).
- **Failures count in both accuracy and cost:** refusals, truncations at `max_tokens`, empty replies and
  parse failures. A refusal before any output is billed for the categories `bio`, `frontier_llm` and
  `reasoning_extraction`, and a mid-stream refusal bills what was streamed (`facts`, correction 4; H-README
  rule 6). None is dropped or re-run silently (`checklist` §1).
- **A second axis: time.** Wall-clock time along the critical path, since parallelism mostly buys time,
  not money (brief, "Measurement").
- **"Cost per task" for the per-piece view (D-23)** = the bundle's cost divided by *w*, the number of
  independent pieces in the prompt (24 at 24×1). This assumes the reader sends the pieces together in one
  call. Sending each piece alone is E3 with one vote, which is computed offline. The definition is fixed
  here so the reader-facing table cannot be argued afterwards. *(`check-setups.md` P1, via Edith, S5.)*
- **Break-even price ratio.** The Opus-to-Haiku price ratio at which the cheapest Haiku vote that reaches
  Opus's accuracy (or the margin in item 7) costs the same as Opus. If no number of tries up to 40 gets
  there, there is no break-even. It is computed offline by re-pricing the logged tokens, assuming token use
  stays the same and input and output prices move together. Haiku's surcharge above 100K tokens changes
  it. It is reported with a bootstrap interval. The list ratio today is 40× on both input and output
  (`facts` row 1c).

**OPEN**
- Nothing: settled by D-48 (sheet rows 9, 10, 22, 23, 24).

---

## 6. Sample size and stop-loss rules

**RULED**
- **D-48** (2026-10-10), sheet row 25: hard cap **$200** (the credit less the spend log); the ladder line **$170** all in (D-27); the
  pilot **$30** (D-36); each main-run cap is the smaller of 1.3 × the pilot-projected cost of that run and the room left under
  $170. **Halt** on money, a model mismatch or change, a stale price table, or any Haiku request over 100,000 input tokens.
  **Pause that setup and return to the user** if more than 2% of its calls in a wave stop at the output limit. **Refusals never
  halt** (D-31, D-36). The user: "Yes to group A. And go with group B as recommended."
- **D-27** (2026-10-10; quoted in item 3): the ladder (extras added in a fixed order only while the measured
  all-in total stays at or under $170), the stop-loss (if the must-haves alone would exceed $170 all in, stop
  and return to the user), no hard slice, and an estimate of about $162 all in at central (D-35's note later puts the plan at about $166 to $178 with
  extras 1 to 4, or $151 to $162 musts only, after code tracing was re-priced and both trims applied). The user: "And
  yes, I am okay with the budget. It looks very nice."
- **D-12** (a Console monthly spend limit, a backstop behind our own guard) is only *proposed*, not ruled.

**DRAFTED, NOT RULED**
- **Sample size follows D-24 and D-27.** 160 standard puzzles (80 base puzzles × 2 shapes), no hard slice.
- **The vote size k follows D-33 (item 7): it comes from the main run's costs, not from the pilot.**
- **Sizes and costs come from the pilot, not from guesses.** The pilot's measured tokens replace the
  stress-test estimates before the main run's size is fixed (`checklist` §1 "Stop-loss and money"; brief,
  "Budget and power").
- **The reconciled budget, as background for D-27** (Karen, `evidence` §0; central, with the pilot, the code-tracing subset, Study 5 (since taken out by D-44)
  and a 5% allowance for retries and refusals included; all estimates, not measurements):

  | Plan | All in, central | All in, high | Within $170 (15% headroom)? |
  |---|---|---|---|
  | A: 160 standard puzzles, all 12 draft setups | $224 | $387 | no, over $200 |
  | Lean A | $174 | $300 | just misses (under $200) |
  | C′-40: A plus a 40-puzzle hard slice | $254 | $435 | no |
  | Lean C′-40 | $200 | $340 | no |
  | Karen's item 3 list, musts only | $147 | $248 | yes |
  | Karen's list, musts plus shoulds 1 to 4 | $162 | $274 | yes |
  | Karen's list, all shoulds | $176 | $291 | narrowly no |

  Nothing fits at the high token case, so the pilot's measured tokens are the gate. This replaces the older
  figures in `NOW.md`, `ops/spend-log.md` and the brief (pilot about $15, main run about $110 to $125) and
  the briefing's about $198 (`evidence` §1).
- **Stop-loss triggers that halt the run** *(proposed by Friday in H-README rule 6 and Edith's
  `checklist` §1/§3)*:
  - any reply whose `model` field differs from the model requested;
  - a refusal or truncation rate above a set limit.
  The numeric limit is open.
- **Fixed in advance.** The main run's size, once set from the pilot, is written into this spec before any
  main-run data exists, with no peeking or early stopping on results. *(Ours, unbacked.)*

**OPEN**
- Nothing: settled by D-48 rows 11 (code subset), 12 (Console limit, already set), 25 (stop-loss and halts) and 26 (the `reasoning_extraction` halt trigger is removed).

---

## 7. Hypotheses

> **Section 7b (D-67 to D-80) holds the tests, p-values, headline rule, add-40 and cut rules, fairness check and lock as ruled; it replaces anything below that differs.**

**RULED**
- **D-23** (2026-10-10): report **both scorings** for "separate pieces" tasks. *Per piece*: tasks right,
  cost per task, a vote taken piece by piece (the reader-facing view). *Whole answer*: all pieces must be
  right, a vote on the whole line (the like-for-like comparison between shapes). The user: "yes I think we
  would report both right becasue thats whats makes our research fair, isn't it? and not to mislead the
  readers ?". The register says which one is the main pre-registered test, the tie and no-majority rules,
  and the answer format are fixed in items 4, 7 and 8.
- **D-33** (2026-10-10), the equal-money rule (the vote size k). The user: "Yes, on both the things that
  are waiting on me." (The user was answering Jarvis's question: "The equal-money rule: as suggested, plus Karen's
  additions (real costs saved before marking, the tie rule, the extra checks, the batch-vs-live
  comparison)?") The register records the rule as follows:
  1. **Formula.** k = floor(Opus-medium mean all-in cost per puzzle ÷ Haiku mean all-in cost per sample), at
     list price. "All in" counts failures, truncations and billed refusals in both costs (the wording of the
     drafted formula the user accepted as suggested). Note: in this rule "all in" means per call, a cost
     that includes failures and refusals. It does not mean the programme total used in D-27 and item 6.
  2. **Which data, and when.** The MAIN run's costs, computed by a script and committed (hash recorded in
     `LOG.md`) before any grading. Pilot-based k is a sensitivity check (`evidence` §6b.2).
  3. **Per what.** One k per shape and per Haiku effort.
  4. **Cap.** At 40, reported as "for less than Opus's price".
  5. **Confirmatory.** Only this k is confirmatory; the full 1 to 40 curve is reported (exploratory).
  6. **The same rule applies to the Sonnet contrast** (Haiku vote vs Sonnet-medium, with Sonnet-medium's cost).
  7. **Tie rule.** A random tie-break scored at expected credit 1/m (when the right answer is one of m tied
     answers) is primary; ties-as-wrong is a sensitivity check; report how often ties decide.
  8. **The vote@k estimator.** Subsets without replacement, at least 1,000 draws, Monte-Carlo error
     reported.
  9. **The k-sensitivity set.** The confirmatory result is also reported at k from the median cost ratio, k
     from the pilot, the interpolated k, and k − 2 to k + 2.
  10. **Realised spend** of both arms at k.
  11. **The k = 0 edge case** (Haiku costs more than Opus per sample): Karen's handling is that H1 is not run
      (`evidence` §6b.2).
  12. **Input** counted in full per sample, with a cached or "input counted once" view as a sensitivity
      check.
  13. **A token-matched secondary view** of the curve, so readers can re-price.
  14. **A Batch-vs-real-time equivalence check in the pilot** (about $5 before the 10-puzzle trim of D-35, to be
      priced by Karen); see the pilot protocol.

  Why (register): research on how ten prior papers set matched sample counts, in `evidence` §6b, and
  Edith's finding S1.

- **D-39** (2026-10-10), the hypotheses and main tests. The user: "yes to item 7." The register records:
  1. **Five confirmatory tests:** (1) H1 at 24×1: the Haiku vote at the equal-money k vs Opus-medium; (2) H1 at
     1×24; (3) H1b: the Haiku vote vs Sonnet-medium at equal money; (4) E3 vs Opus-medium at 1×24;
     (5) Opus-low vs Sonnet-medium (Anthropic's "bigger model, less thinking" advice). Each pair of models has
     one confirmatory test (tests 1 to 3 and 5).
  2. **The code family is a separate secondary check,** outside the confirmatory family.
  3. **Official scoring** for the confirmatory tests is the strict **whole-answer** scoring. The per-piece (reader)
     view is reported prominently as secondary (D-23).
  4. **"Matches" means non-inferiority within a 10-point margin;** the actual gap is always reported.
  5. **Holm's method across the five.**
  6. **Everything else** (the full three-model chart for each shape, every setup's results, the vote curves and
     the slip analysis) is reported in full as descriptive or exploratory.
  The register's evidence: Karen's contrast budget (`evidence` §3.7) less the code family; the margin suggested in
  `check-setups.md` P9; Holm per the brief and the checklist. The tie rule and the vote estimator are in D-33.

**DRAFTED, NOT RULED** *(background; D-39 above decides which tests are confirmatory, and where this text disagrees, D-39 wins)*

The brief's four candidate hypotheses (the setup chat, in the brief, "Draft hypotheses"), in plain words:
- **H1, vote vs Opus.** At the price of one Opus-medium call, does a Haiku majority vote match Opus?
  Reported by how often Haiku gets each puzzle right alone.
- **H2, perfect splitting.** Does splitting the task perfectly with a script (E3) remove the structure
  effect on dollars but keep it on time?
- **H3, AI-planned teams on deep chains.** Do teams that plan for themselves (E1, E2) get worse on deep
  chains? This replicates Kim et al. (v3) inside one task family (`facts` row 10b).
- **H4, pickers.** Is a picker worth its cost over a plain vote?

Notes from the checked briefings, each a suggestion:
- **H1 needs a margin.** Opus is near 95% at the standard level, so "no significant difference" would be
  read as "matches". `check-setups.md` P9 suggests a non-inferiority margin of 10 points (suggested by
  `check-setups.md`). In words: Haiku's vote counts as matching Opus if the lower end of the 95% interval
  for (vote minus Opus) is above minus 10 points (a one-sided test). No file computes the power of that
  test; every power figure in the files is for detecting an Opus win. The equal-dollar number of tries *k*
  is set by D-33's rule from measured costs and cannot exceed 40 (`check-precision.md`, problem 3). In one simulated
  scenario (two shapes, world ii-mod) power to detect an Opus win falls from 91% at *k* = 20 to 44% at
  *k* = 30, because more votes make Haiku better and the true gap shrinks. After the cost correction the
  likely *k* is about 22 to 29 (`evidence` §1; Edith E4), so quote power as a range, "between about
  .4 and .9 per shape".
- **H2 cannot fail on dollars.** E3 makes the same calls at every wiring, so its expected cost and
  all-or-nothing accuracy are equal across wirings by construction (`check-setups.md` P8). What remains to
  measure is time. Keep E3 as a reader option, not a dollars hypothesis.
- **H3 and H4** depend on item 3: D-27 drops E1 and the Opus-low picker, so H3 is tested with E2 only
  (an extra) and H4 with the Haiku picker over 8 only (an extra).
- **Contrast cap.** The brief says at most about 6 confirmatory contrasts, corrected with the Holm
  method (brief, "Power"; `checklist` §1). Karen's list of six (suggested by `evidence` §3.7): (1) Haiku
  vote vs Opus-medium at 24×1; (2) the same at 1×24; (3) Haiku vote vs Sonnet-medium at equal dollars;
  (4) E3 vs Opus-medium at 1×24; (5) Opus-low vs Sonnet-medium; (6) the code family. Everything else is
  exploratory. H1 would need to be framed as a non-inferiority test because Opus is near 100% (suggested by
  `check-setups.md` P9; open). `check-setups.md` P9 had a different six, including Opus-high vs Opus-medium
  at the hard level; that contrast is moot now that D-27 drops Opus-high and the hard slice.
  - Contrasts (1) and (2) are one test per shape, so the exact number of tests in the family must be
    fixed.
  - `check-precision.md` problem 6 and `analyse-precision.md` "Bottom line" 6: if the per-shape headline
    is two tests, fix their order or split the 5%. In a fixed order the first test uses the full 5%; its
    smallest detectable gap is about 20% smaller than at Holm's strictest step. Later tests are checked
    only if all earlier ones succeed.
- **Detail on the equal-money rule that D-33 does not settle (drafted from `evidence` §6b.2).**
  - An unparseable answer is a vote for nothing.
  - The vote@k average can be counted exactly where feasible (a vote depends only on how often each answer
    appears); at k = 40 there is only one subset, so its puzzle-level noise is not averaged.
  - The interpolated k (`evidence` §6b.2, as coded): k* is D-33's cost ratio, unrounded, capped at min(40, samples drawn), with no extrapolation.
    The per-base score is (1 − f)·vote@⌊k*⌋ + f·vote@⌈k*⌉, with f = k* − ⌊k*⌋. If k* < 1, H1 is not run. It is tested with the same paired BCa
    bootstrap, as one row of the k-sensitivity set.
  - Why k matters: in world (ii-mod), per-shape power to detect an Opus win goes from .91 at k = 20 to .44
    at k = 30 (`check-precision.md`, problem 3); `floor` rounding errs against the claim being tested,
    because Haiku then spends at most what Opus does.
  - The test at the matched point is a paired bootstrap over base puzzles with the non-inferiority margin
    below (open).
- **A pre-registered prediction.** The more of Haiku's wrong answers land on the same wrong value, the
  smaller the gain from voting (`check-setups.md` §5).
- **Every hypothesis is labelled confirmatory or exploratory** before the main run (`checklist` §1).

**OPEN**
- Nothing: settled by D-48 (sheet rows 13).

---

## 7b. The tests, the analysis and the lock, as ruled (D-67 to D-80)

*Friday's draft for Edith's check. Every rule below is a ruling the user has made; the register IDs are given. This section replaces the earlier
text in sections 7 and 8 and in the remaining-details rows 6 and 27 wherever they differ (each is marked "superseded by 7b").*

### The five confirmatory tests (D-39, D-68 F1 and F2)

The confirmatory Haiku arm is **Haiku-medium** (F1); Haiku-low's vote is exploratory, with every number reported. For each test the unit is the base
puzzle (n = 80, paired). For each base puzzle the score of an arm is its whole-answer accuracy (D-39; for a vote, the expected vote@k accuracy by
D-33's estimator; for E3, the product of its per-step accuracies, see below). **d** = the mean over base puzzles of (challenger − comparator), in
percentage points. H0: d ≤ −10; H1: d > −10 (non-inferiority, one-sided). Family-wise one-sided α = 0.025, Holm across the five tests: test i is declared
non-inferior at its Holm step j if its one-sided p ≤ 0.025 / (6 − j) (equivalently, the lower one-sided confidence bound at level 1 − 0.025/(6 − j) lies
above −10), stopping at the first failure.

| Test | Challenger | Comparator | Shape |
|---|---|---|---|
| 1 | Haiku-medium vote at k | Opus-medium | 24×1 |
| 2 | Haiku-medium vote at k | Opus-medium | 1×24 |
| 3 | Haiku-medium vote at k (Sonnet-matched) | Sonnet-medium | 1×24 |
| 4 | E3 | Opus-medium | 1×24 |
| 5 | Opus-low | Sonnet-medium | 1×24 |

A **three-way reading** is reported for every test: **non-inferior** (declared by Holm above); **worse by more than the margin** (the unadjusted two-sided
95% interval's upper end is below −10); otherwise **inconclusive**. The unadjusted two-sided 95% interval and the actual gap d are always reported. The
other shape for tests 3 to 5 is exploratory. The extra rung, if it runs, is **l17** (frozen with the generator); no other rung may be built, and it runs
only on the user's go (F6).

### The p-values (D-68 F4; replaces the sign-flip p-values of D-48 row 27)

All p-values and bounds come from **one paired base-puzzle BCa bootstrap**: 10,000 resamples of the 80 per-base differences, a seed fixed in the
frozen analysis code (each test's seed is derived from the base seed and the test name), p obtained by **inverting the BCa bound** so that the test and
the interval can never disagree. The sign-flip permutation test is kept only as a sensitivity check for d = 0 (superiority). Exact binomial intervals
remain for single-arm accuracies (D-48 row 27). In the bias-correction constant z0, bootstrap means that equal the observed mean count one half (a mid-share convention, pre-registered; Edith's size check on {−100, 0, +100} differences with a true mean of −10 gave 1.65% and 2.60% rejections at 0.025, against 0.75% and 1.70% for the strict form). Code: `harness/analysis/bootstrap.py`; the Python version is recorded in the lock because `random` is not
guaranteed stable across versions.

### The headline rule (D-68 F3)

The as-deployed view stays primary: a refusal, a truncation or an unparseable reply counts as wrong at its logged cost (D-31, D-48 rows 9 and 20). The
word "matches" may appear in the abstract or a headline for a test only if that test is also non-inferior with **refusals left out** (a blocked single
answer drops that base puzzle from that test; blocked Haiku samples are dropped from the vote, with k capped at what is left) **and** with **truncations
left out** (the same). Otherwise the result is reported as "matches as deployed; driven by refusals or truncations". Code: the three views in
`harness/analysis/scoring.py`.

### The official 1×24 score (D-76)

D-76 amends D-39 and D-36(4) for the 1×24 shape. Code: `harness/analysis/trace_parse.py` (the parser) and `harness/analysis/scoring.py`
(`grade_1x24`).
- **Official score.** A chain try is right only if all 24 step lines are right and the Answer line equals line 24. A try that does not parse
  under the fixed rules is unplaceable and counts as wrong (it stays in, as in the as-deployed view).
- **The Haiku vote** is a plurality over identical 24-state tuples, with the same vote@k estimator and tie rule (D-33). An unplaceable try votes
  for nothing. Two tries with the same final answer but a different middle line are different votes.
- **Fixed parse rules, the same for every arm** (agreed between Friday and Karen; the list is the docstring of `trace_parse.py`). Accepted:
  whitespace, markdown or bullets around a line, `:` for `=`, square, round or no brackets around exactly L integers, leading zeros, step lines
  in any order with prose around them, a code fence, and the last Answer line (with or without its `1 =` label). Rejected: a misnumbered,
  repeated or missing step line, a value that is not a whole number, not exactly L values, no Answer line, and an Answer that differs from
  line 24. Also accepted (signed off by Karen and Edith): one trailing period or comma right after a step state or the Answer state; the label
  word `Sequence` or `Piece` (any case, singular) before an entry number, at both shapes (the prompts call each item a "sequence"); markup
  around the label and the number (`Answer: **Sequence 1** = [...]`); and `:` after an entry number at 24×1 as well as at 1×24. A label with
  any number makes an Answer line, so `Answer: Sequence 2 = [...]` fails the value rules exactly like `Answer: 2 = [...]`.
- **The 24×1 reader uses the same Answer-line rule.** It finds its Answer line by the same definition as 1×24 (`last_answer_text`, R3-a,
  `d25f8eb`), so a prose line such as "Answer check: done" never replaces the real Answer line. `choose_preset` scores both shapes of a
  ledger set from the raw replies with these rules, and the pilot table's `right` for a ledger set is the official D-76 score from the same
  scorers (`pilot.grader`, PR #24 `67102f6`); `prompt_d31.parse_answer` is unchanged (it serves only the dropped digit and code families now).
- **Format compliance.** The share of answered 1×24 tries that parse is reported per model, from the 20-call check and the pilot and in the main
  run; the paper flags any model whose non-compliance is above about 5%.
- **The preset pick** (D-36(4)) scores 1×24 tries the same way, from the raw replies. E3's product (below) is then exactly the official score,
  and test 1 at 24×1 is unchanged.
- **Pre-registered secondary views (Karen):** the final-answer score (the Answer state alone, with the measured absorption reported beside it);
  and a "copy slips forgiven" sensitivity, in which a trace whose only error is a copying slip counts as right, in the vote too.
- **Answer-only fallback.** If the D-36(5) switch fires, every 1×24 arm falls back to final-answer scoring; a mix of the two is refused.

### E3 and the step-line view (D-68 F7)

E3 is scored as the **product of its per-step accuracies on correct inputs**. That is exactly the probability that a chain of independent step calls gets
every step right, because the all-correct path only ever sees correct inputs. It equals the "all step lines right" score and is a lower bound on E3's
final-answer accuracy; the gap comes only from a wrong path that later rejoins the right answer, which is not credited and which the absorption cap
(5%, L2) bounds. Under D-76 every 1×24 arm is scored on all step lines right, so test 4 compares like with like; the final-answer view is the secondary check.

### Haiku draws, the vote size and extra puzzles (D-70, D-72, D-73)

- **Haiku is always drawn ×40**; k is capped at the samples drawn and at 40 (D-70). The earlier "cut to 20 if the curve is flat" is dropped.
- **Add 40 base puzzles at 1×24 only (tests 2 to 5) if underpowered (D-72).** After the pilot and before the main run, the power simulator is re-run on the
  pilot's measured world (simulator version, seed and inputs are fixed in the lock). If test 2 has under a 50% chance of a conclusive reading at 80 base
  puzzles, **and** the high-case cost with the extension stays inside the $170 ladder, the 40 extension puzzles are added (about +$18 central, +$40
  high); the analysis then uses 120 base puzzles for tests 2 to 5 and the matched 80 for test 1 and the shape contrasts. The re-estimate uses the pilot's
  separate practice puzzles, never main-run data, so the type I error is not inflated. The extension sets are frozen now, disjoint from every other
  set: `ext40-ledger-l14-v1`, `ext40-ledger-l15-v1`, `ext40-ledger-l16-v1` (40 base puzzles each; only the 1×24 half is used). They stay unused unless
  the rule fires. It never fires together with the cut order below.
- **Priority (D-74).** The add-40 ranks above the exploratory extras. If the high case with the extension does not fit the $170 ladder, the extras are cut in the D-73 order (Haiku-max first, then the shoulds from 4 down to 1) to make room, and only those may be traded for it. The decision is taken once, from the pilot's measured costs and before the main run, and is reported; the confirmatory arms and the base-puzzle count are never traded.
- **The cut order, if money runs short (D-73).** Applied at most once, before the main run, from the pilot's measured costs, never during the run. Order:
  Haiku-max; the shoulds, from 4 down to 1; Haiku-low to ×20; the D-42 robustness arm to 20; the 24×1 exploratory arms; 70 base puzzles; 60 base
  puzzles (the floor). All five confirmatory tests are always kept. Below 60 base puzzles it returns to the user. It may go below D-27's musts and
  amends D-27's stop-loss. At 60 base puzzles the paper states that 1×24 is likely inconclusive.

### The fairness check and the bias table (D-67, D-68 F5)

D-67(1): **freeze.** No new rule kinds, dials or presets beyond generator ledger-0.3 (l14, l15, l16, plus the spare l17; built as ledger-0.4, which only fixes Edith's second review of the guards, D-76); the pilot only picks among them
by D-36(4); any later change goes to the user as a declared deviation.
D-67(2): **pre-registered exploratory analyses**, with the definitions in `research/pilot-plan-ledger.md` ("Fairness check"), implemented in
`harness/analysis/scoring.py`:
- **slips per rule kind for every model**, from the local-slip table (each step's rule plus house rule applied to the model's own previous balances;
  first-slip view as the sensitivity check), with the blame order house rule missed, house rule misapplied, decoy confusion, then the step's own kind;
  T (`repick2`, `repeat_fixed`, `sweep`) and G (`two_clause`, `compare_move`, `avg_donors`, `rank_move`, `count_move`) are decided by the step's own kind;
  the house rule is analysed puzzle-wide; **placement** (F25-1, F25-2): a try whose step lines read and hold a slip is placed at its first wrong
  step whatever its Answer line says; a try is unplaceable only if its step lines are missing or unreadable, or if every step is right and only
  the Answer line is wrong; unplaceable tries are counted per model and preset, with the reason, and left out;
- **Haiku's wrong-answer repeat share** across its tries (pairwise agreement of wrong answers and of first slips);
- **a test of whether Haiku's slips concentrate on the targeted kinds more than Opus's do**: the targeting index TI = RR_Haiku ÷ RR_Opus with
  RR = T-slip rate ÷ G-slip rate, Mantel-Haenszel by preset, a 90% bootstrap over base puzzles stratified by preset; and TI_house = (house rule missed ÷ steps
  where it should fire) ÷ (the G-slip rate), Mantel-Haenszel by preset, Haiku over Opus ("misapplied" has its own rate, below, and is never a flag); both values are reported every time; flag K fires on either TI or TI_house at 2 or
  more with the interval's lower end above 1, only with enough slips ("not assessable" otherwise). If Opus has too few slips, Opus and Sonnet are pooled as the comparison and the result is labelled as pooled; Sonnet's own RR is always reported as well. Strata (presets) that have no steps in one group are left out of the Mantel-Haenszel sums; a model with zero slips in a group gets 0.5 added to its slip counts in every stratum (this pulls ratios towards 1, so it is conservative). The house index is RR_house = (house rule missed ÷ steps where it should fire) ÷ the G-slip rate, and TI_house = RR_house for Haiku ÷ RR_house for Opus; "misapplied" is reported as its own rate over the steps where the house rule should NOT fire (never a flag index);
- every pilot preset is reported with **Opus and Sonnet beside Haiku**, and H1 per preset where available; the median of Haiku-medium per shape is
  reported next to the pooled one.
The free reads were used to design the puzzles, so they are excluded from all of these; only the frozen sets count. The statement in D-56 that the
family was "never iterated" concerns the *choice of family* only; the *difficulty tuning within the family* is a separate step, described below and disclosed.

**The bias table (F5; the net direction is not known in advance):**

| Choice | Favours | Bounded or measured by |
|---|---|---|
| Rule kinds tuned on Haiku's slips | Opus and Sonnet (against the vote) | The fairness check (TI, TI_house, repeat share), D-67 |
| The 10-point margin | The vote | The three-way reading; the error-rate ratios; a 5-point secondary view (Karen's power simulation) |
| Refusals and truncations count as wrong | The vote | F3 (a match must hold with them left out) |
| The 25 to 50% Haiku band | The vote | Stated as the regime studied (D-21); the scope sentence |
| 24×1 near the ceiling | Both arms, so less informative | Per-shape medians reported; a low-information flag if Haiku pieces score above 60% |
| Absorption in 1×24 | Arms that slip more (the vote) | The official 1×24 score is all step lines right (D-76), so an absorbed slip still counts as wrong; the caps (L2: single units, each transfer size and the house-rule slips on the reference chain) bound the final-answer view |

**The limitations sentence (F5):** *We developed the task's rule kinds in small free test runs with Claude Haiku 5.5 alone, adding kinds of step where Haiku
went wrong; this may make the task disproportionately hard for Haiku and its wrong answers more alike, which works against the Haiku vote. Other choices
work for it: a 10-point non-inferiority margin, refusals and truncations counted as wrong, and a difficulty band where voting helps most. Table [X] lists
each choice and how we bounded or measured it; the net direction is not known in advance.* Claims are scoped to this one synthetic, procedurally generated
family (D-59, D-21). The tuning history is in the appendix below.

### The lock before the pilot (D-69, D-71)

Before any pilot call, a **git tag** fixes the following, and **one dated amendment** after the pilot fills in only the values the pre-set rules choose
(the preset, k's inputs, `max_tokens`, whether D-72 fires):
1. this spec at D-67 to D-80: the five tests and their exact text, the headline rule, the bias table and sentence, the fairness check, the F6 and F7
   wording, and the Haiku draws, add-40 and cut rules;
2. the generator: rule kinds, dials and presets as of **ledger-0.3** (D-67); generator code **ledger-0.4.2** (`240454b`; 0.4 plus Edith's round-3
   and round-4 fixes, which change no rule kind, dial, preset or sentence), which froze the pilot, `ext40` and S3 sets. The check set stays at
   ledger-0.4 as frozen and sent; under the locked code it verifies with `freeze --verify --allow-other-version` (the text checks only). With its version string, the frozen sets for l14 to l17 (pilot sets, the 20-call check set, the S3 set) and the three
   `ext40` sets;
3. the **preset-choice script** (`harness/analysis/choose_preset.py`): it reads only the pilot's Haiku-medium tries, writes its pick (D-36(4), the K2
   tie-break, the per-shape medians) with the hash of its input, and the pick is committed **before anyone opens an Opus or Sonnet pilot number**;
4. the **k script** (`harness/analysis/kscript.py`, D-33 and D-70): floor of the cost ratio per shape and effort, cap at 40 and at the samples drawn, the
   k-sensitivity set;
5. the **analysis code with fixed seeds**: the vote@k estimator (D-33 tie rule, at least 1,000 subsets), E3 as the product of per-step accuracies, the
   paired BCa bootstrap, Holm at one-sided 0.025, the three-way reading, the refusal and truncation views, all-step-lines-right scoring, the slip tables;
6. the **tests on simulated data with known answers** (Karen's `research/fixtures/sim-main-v2/`: the D-76 rows; the parse fixtures, 223 cases in
   all: the 148 round-1 parse cases plus round 2, `pieces_cases` and the answer-only `final_cases`, run by `run_parse_cases.py` with zero
   mismatches required; the D-76 official-score pin reads round 1 only): bootstrap size near 0.025 at d = −10, power, the Holm order;
7. the D-72 power simulator (version, seed, inputs), the pilot plan, the Python and git versions, and the list of SHA-256 hashes of every file in the tag.
The repo stays private (D-08). **The public fingerprint (D-71)** is the tag's commit ID plus the SHA-256 of the uncompressed tar from
`git -c tar.umask=0002 archive --format=tar <tag> | shasum -a 256`, with the git version recorded (tested reproducible on this machine with git 2.39.5; a
different git version can write a different tar for the same tree). The user posts it in a Zenodo record with a neutral title; the team also posts a
public gist with the same fields and an Internet Archive snapshot.

*Amended 2026-10-12 (Deviation 1): `prereg-lock-2` fixes the same items at N steps, before any ladder call. Its list is under
"Amendments", in "What prereg-lock-2 fixes".*

### Measured, for the paper (limitations or appendix)

- **Transfer-slip absorption over all pairs of lines.** The L2 cap (5%) is enforced on the pairs of lines each step changes, on the reference
  chain. Measured over all ordered pairs of lines it exceeds 5%: the largest one-unit rate is 0.107, at l14 (Edith, PR #19 round 4).
- **How hard l17 is to build.** l17 accepts about 1 draw in 38,000, pooled over 16 builds (Friday's 10 and Edith's 6); one seed in each
  sample exhausted a 100,000-draw budget. Hence the 400,000-draw budget of ledger-0.4.2; no accepted rulebook changed. Most rejected
  draws are a rule slot that cannot be filled at its state (about 87%), then the house rule firing outside its window (about 12%).

### Tuning history (appendix; D-67(3))

Six small free reads with Claude Haiku 5.5 on the Max plan (not the API), one try per puzzle, 90 answers in all; no Opus or Sonnet answer informed the
design. Whole answers fully right:

| Read | Presets | Runs | Right | What was added afterwards, and why |
|---|---|---|---|---|
| 1 | l1 to l4 | 24 | 22 | Arbitrary percentages and amounts, rules that compare or combine two lines (l5 to l7): the simple rules were too easy |
| 2 | l5 to l7 | 18 | 16 | Only compound kinds, more lines (l8, l9) |
| 3 | l8, l9 | 12 | 11 | Four step-heavy kinds (simultaneous average, repeat, rank, count) and decoy rules (l10, l11), chosen from the per-step-error arithmetic and the literature, before any slip data on them |
| 4 | l10, l11 | 12 | 6 | Round-number base (an arithmetic slip showed up); fixed-amount look-again and repeat rules; the house rule (l14, l15): most chain slips were wrong largest/smallest picks on states never written down |
| 5 | l14, l15 | 12 | 9 | The in-turn sweep; more lines, the repeat five times, the house rule on 9 to 12 steps, 8 decoys (l16); a spare rung l17 (not read) |
| 6 | l16 | 12 | 8 | Nothing: the family was frozen (D-67) |

Interim presets l10, l12 and l13 could not meet the transfer-slip absorption cap and were retired. Every cell is small (12 runs or fewer per read); the
direction of the bias is in the table above.

---

## 8. Analysis plan

> **Section 7b (D-67 to D-80) holds the tests, p-values, headline rule, add-40 and cut rules, fairness check and lock as ruled; it replaces anything below that differs.**

**RULED**
- **D-23**: both scorings are reported (quoted in item 7). D-39 makes the whole-answer scoring the official one
  for the confirmatory tests; the tie rule is in D-33.
- **D-28** (quoted in item 1c): the design is matched and the analysis is paired by base puzzle (a
  base-puzzle bootstrap or a random effect for the base puzzle).
- **D-33** (quoted in item 7): the vote@k estimator and the tie rule.
- **D-39** (quoted in item 7): the confirmatory family is the five tests; the official scoring is whole-answer;
  non-inferiority within 10 points; Holm across the five; the code family is a separate secondary check; all the
  rest is descriptive or exploratory.

**DRAFTED, NOT RULED**
- **The unit of analysis is the base puzzle** (ruled by D-28; the details below are drafted). The register
  says "a base-puzzle bootstrap or a random effect for the base puzzle"; this draft uses both: the bootstrap for intervals and
  the mixed model for the setup × shape terms. *(Edith's requirement,
  `ops/reviews/2026-10-10-pr1-taskgen-r1.md`; assumed by `check-precision.md`, "How the matched design is
  handled".)*
  - Results are averaged within each base puzzle, and the test runs across base puzzles.
  - The **bootstrap resamples base puzzles**, not single versions: draw base puzzles with replacement and
    keep all versions and all setups of each drawn puzzle together, so the pairing survives.
  - The **mixed model** is a logistic model (each answer is right or wrong): accuracy ~ setup × depth
    fraction + (1 | base puzzle) (brief, "Analysis"). With two shapes, depth fraction has only two values,
    so the term becomes setup × shape.
- **Paired contrasts with Holm correction** over the confirmatory set (brief, "Analysis"). Differences
  between setups are paired on the same base puzzles.
- **Accuracy-vs-dollars frontiers** with bootstrap bands, overall and per shape (brief). The second axis
  is time.
- **The break-even price ratio** per shape, re-priced from the logs (brief; `facts` row 1c).
- **Exact intervals for lopsided data.** When Opus fails only about twice in 40, the normal-approximation
  95% intervals cover only 87% of the time at 40 base puzzles and 91.5% at 80. (In the simulated world (i).) Use an
  exact, permutation or bootstrap-t method over base puzzles, and report Opus's failure counts directly
  (`check-precision.md`, problem 4). A pre-registration must pick one method, not a menu (open question
  below).
- **Report the shape × setup interaction** (does the best setup differ by shape?) (`check-precision.md`,
  problem 7).
- **Report results by item difficulty,** using each puzzle's Haiku single-try accuracy (D-21; brief).
- **Vote curves** for any number of tries *k* from 1 to 40 are computed offline from one set of samples,
  as the average over all *k*-sample subsets (brief; `analyse-precision.md` "Assumptions"). There are
  too many subsets to list (about 10^11 at *k* = 20), but a vote depends only on how often each answer
  appears. D-33 rules the estimator: subsets without replacement, at least 1,000 draws, Monte-Carlo error
  reported, with the random tie-break (expected credit 1/m) as primary and ties-as-wrong as a sensitivity
  check, and a report of how often ties decide. Overlapping subsets add no information; the uncertainty comes
  from the base-puzzle bootstrap. At *k* = 40 there is one subset. Both vote units (per piece, whole answer)
  are shown (D-23).
- **Slips are counted with care (Edith N40).** A printed step line can be wrong while the final answer is right
  (Haiku d4p-chainB, step 22), so a "first wrong step" read from step lines can be a copying slip in the printout,
  not a slip in the work. For the slip-by-kind count that D-25 relies on, report placed slips **separately for
  replies whose final answer is right and for those whose final answer is wrong**, or count a slip only when the
  chain's later printed values follow from it. (From `ops/reviews/2026-10-10-pr8-wording-check-r3.md`; the choice
  is analysis-code detail for Edith's review, not a ruling.)
- **Failures are counted** in accuracy and cost, never dropped (item 5).
- **Exclusion rule.** After the lock, no puzzle or call is excluded, except (a) a puzzle that the
  independent re-solver shows to be faulty, or (b) a call lost to an infrastructure error and retried under
  the re-run policy (item 5). Each exclusion is logged as a dated amendment with its count. *(Ours,
  unbacked; asked for by Edith, S6, from `checklist` §1 "None are dropped or re-run silently".)*
- **Reading contrasts.** Contrasts across models are read on the dollar axis (item 3, effort labels).

**OPEN**
- Nothing: settled by D-48 (sheet rows 27).

---

## 9. Data

**RULED**
- **D-37** (2026-10-10; closes D-11): full raw call records (prompts, replies, usage) are kept **on this machine
  plus one backup copy** (for example a compressed archive in the user's Google Drive) and are **not committed to
  git**. A **compact per-call table** (model, setup, tokens, cost, right or wrong) **is committed to git**.
  Everything is released publicly with the paper, on a research-data site. No secrets in any record; the API key
  is never logged. The user: "Yes, and my okay on item 9." The register's reasons: the full records are likely
  hundreds of MB up to about 1 GB, too big for git (GitHub warns above 100 MB per file); the records hold only
  puzzles and model outputs, no personal data; the release venue and licence are fixed before publication.
  *(Built: `data/raw/` is git-ignored and `harness/pareto/table.py` writes the compact table; PR #11.)*

**DRAFTED, NOT RULED**
- **Every call is logged in full** to `data/raw/<run-id>/calls.jsonl`: timestamp, the exact model ID
  requested and returned, effort, a hash of the request parameters, `custom_id`, batch or real-time, the
  full usage object (input, output with thinking, cache read and write), `stop_reason`, refusal category,
  the visible answer text and latency (H-README rule 3). The offline re-pricing depends on these logs (and a judging
  study, which D-44 left out of this project, could use them later).
- **Each run records** the git commit, the spec's lock commit, the prompt hash and the item-set hash
  (`checklist` §2a "Logging", proposed by Edith).
- **Frozen item sets** go in `data/tasks/<set-id>/`, with pilot and main from different `set_id`s
  (`taskgen`). Batch results are joined by `custom_id`, never by position (H-README; `checklist` §2b).
- **What we release at publication** (D-37 ruled that the full call records are released with the paper): the
  frozen item sets, the generator version, the analysis code, the pinned price table and the call logs.

**OPEN**
- *(D-11 is settled by D-37. Removed from this list. The release venue and licence are fixed before publication.)*
- If the real-world check is added, ArXivMath items are CC BY-SA 4.0 (share-alike), so releasing them
  carries that licence (`options` §6.2). Do we accept that?

---

## 10. Robustness

**RULED**
- **D-42** (2026-10-10). The user: "yes to both, go with your suggestions". The register records:
  - **(a) A prompt-variant check:** a slightly reworded prompt with the same meaning and the same banned-word
    rules (it never mentions grading, tests or evaluation), run with **Haiku-medium ×10 tries on 40 main-set
    puzzles** (20 base × 2 shapes), about $2. The variant first passes the same free wording check. Its results
    are reported as robustness, outside the confirmatory family (D-39).
  - **(b) Every setup runs within about 48 hours, on pinned model IDs.** Every reply's `model` field must match
    the model requested (a mismatch stops the run). **If a model changes mid-run, stop and return to the user.**
  - **(c) Prices are re-checked against the live pricing page within 24 hours before a run.**
  Karen folds the about $2 into the budget model.
- **D-45** (2026-10-10): if slow Batch turnaround stretches the main run, the run window in D-42 (b) may extend up to
  **72 hours**, provided no model has changed; the actual window is reported. The user: "For the 4th point, I can go
  with the suggestion, yes." (This answers Edith's Q2: Batch's documented maximum is 24 hours, `facts` B4.)

**DRAFTED, NOT RULED**
- **Model IDs are pinned** to the exact strings `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`,
  `claude-fable-5-1` (no date suffix, so they do not drift; `facts` row 9) (H-README rule 6). The harness enforces
  the mismatch stop (`harness/pareto/client.py`, `batch.py`) and pins the SDK (`harness/requirements.txt`); both are in PR #11, under review.
- **No server-side fallback:** never send `fallbacks` or the fallback beta header (`facts`, correction 4).
- **The window and Batch.** Batch results can take up to 24 hours, so the window (48 hours, up to 72 under D-45) counts from the first
  submission to the last result; the pilot's wave plan (N46) is checked against it. (Batch's documented maximum is
  24 hours: `facts` B4, "24-hour expiration".)

**OPEN**
- **The exact text of the prompt variant,** and its free wording check on Max-plan helpers (stop at the first
  block; no rephrasing or retries). Friday drafts it; Edith clears it; the user says yes to the words.

---

## 11. Code tracing, the second family

> **Superseded for the ledger family** by section 1e (D-56, D-59, D-62) and `research/pilot-plan-ledger.md`. The digit and code text below is kept as history.

**RULED**
- **D-32** (2026-10-10): code tracing stays the **second** task family (digits stay main); build the code-tracing
  puzzle maker from Friday's sketch, then review. The user: "Yes, I can go with the suggestion of keeping digits as
  the main and code tracking puzzle maker as the second test". The register's plan: about 80 puzzles (40 base × 2
  shapes, matched), difficulty set on the chain shape; the setups were then trimmed by D-35 (no Sonnet). **Built:**
  the generator, grader and frozen-set writer are merged (PR #10, reviewed CLEAN by Edith); setting c3b is the
  rendered example (`data/examples/prompts-d31/code-c3b-*.txt`). D-34 merged the sketch and its free-test data.
- **D-41** (quoted in item 4): the free code-prompt wording check ran: 0 blocks in 8 runs (Opus, Haiku).
- **D-20** (2026-10-10): code tracing is the second task family, on a smaller subset. The user: "I feel I
  like using both the rule-following puzzles as the main test, plus code tracing as a second family test.
  That's good." The register notes Karen's estimate of about $15 to $30 on an 80-puzzle subset, about a
  day of Friday's work and an Edith review, and that the budget fit is checked after the pilot.
- **D-19**: code tracing is also the named fallback if harder digit puzzles don't work.
- **D-22** (2026-10-10): a free Max-plan difficulty test of the code-tracing sketch happens before Friday
  builds it. The user: "yes, I agree with the proposals for the free Max plan tests."
- **D-35** (2026-10-10), budget trims to D-27: (1) the real-time subset (latency plus the batch-vs-real-time check) runs on 10 puzzles, not 20; (2) Sonnet is left out of the code-tracing family, so the code setups are Opus-medium ×1, Haiku-medium ×40 and E3, while Sonnet stays in the main digit study. The user: "yes, take both trims also". So the code family runs Opus-medium ×1, a Haiku-medium ×40 vote and E3 (the step-wise team,
  lead-by-2 voting per D-27). Sonnet is not run on code. The register's note: code tracing at real prompt
  sizes is about $31 to $44 (before the Sonnet trim), and the pilot includes a few code puzzles to measure
  how much the models think on code.

**Where it stands.** The first sketch (lists of 8 and 12 numbers) was too easy (Opus 8/8, Haiku 12/12). The harder
free test (`data/codetrace-free-test/README.md`) found no single setting that put Haiku at 25 to 50% on both
shapes; c4 was the closest (Haiku about 100% on separate pieces and about 10% on the chain). D-32 then ruled the
build; setting c3b is the one rendered so far. The first read of c3b (8 free runs, one per cell,
`data/wording-check-code/README.md`): Opus 3 of 4 fully right; Haiku 1 of 4 (it answered once and got all 24 steps right; it declined three times by hand, which are not blocks). Calibration on
the real API happens in the pilot (D-36).

**DRAFTED, NOT RULED** *(All from `check-codetracing.md` unless stated; its verdict is "MODIFY".)*
- **What it is.** Each step applies a small generated function (3 to 5 lines of Python-like code on lists,
  strings and integers) to the current value; the same wirings as the digit puzzle; exact-match grading;
  answers computed by running the code (`options` §5.1).
- **Build only if** the free test shows Haiku's single answers land at about 25 to 50% **and** its errors
  are not mostly the same misread across samples. Otherwise save the day of Friday's work and two rounds of
  Edith's review.
- **A digit baseline.** Run the same repeat test on d4 digits for comparison, so "the vote loses ground on
  code but not on digits" compares against data. *(The d4 repeat test has now run; `LOG.md` Free test 4.)*
- **Shape.** Only the two end shapes, 40 base puzzles each = 80 puzzles, no hard code slice (consistent with D-27). *(Differs
  from Karen's 20 per wiring at four levels; see the reviewer notes.)*
- **Setups: ruled by D-35 (see above).** Earlier drafts had Sonnet-medium ×1 in the set (Karen's four,
  `options` §5.2) and suggested Opus-low ×1 and a named vote effort of medium (`check-setups.md` §5); the
  vote effort is Haiku-medium under D-35, and Opus-low is not in the code set.
- **Build guards.** Port the digit generator's shortcut guard. `check-codetracing.md` finds the real
  problem is the count-and-rotate template: put a value-changing step between any two count-driven steps,
  cap how often a step changes nothing, widen the template variants (88% of 1,000 sketch rulebooks contain
  two identical functions), and normalise value formatting in the scorer. Decide in advance whether
  "carried loop" steps stay in (its view: yes), and report vote results with and without them.
- **Statistics.** Pre-register code as a **secondary replication** with one or two named comparisons
  (does Haiku-vote-vs-Opus come out the same way as on digits; does the vote stop improving below Opus's
  score), outside the main Holm set. With 40 matched pairs it can only show a gap of about 15 to 20
  points or more, so it is a check of direction. (`check-codetracing.md` point 9.)
- **Pre-registered prediction.** A higher repeat share of wrong answers means smaller gains from voting
  (`check-setups.md` §5).
- **Cost and build time.** About $15 at Batch for the subset (`options` §5.3, Karen); about $26.2 at the
  corrected central, or about $20 with a Haiku-low vote (`check-cost.md` §3), all of which included Sonnet; about $32 central with
  Batch after a higher Haiku token guess (`check-codetracing.md` point 8). Expect 2 to 3 days from start to
  merge, not 1 (`check-codetracing.md` point 10). A pilot slice of 4 base puzzles × 2 shapes measures
  tokens only. **With Sonnet out (D-35), the code family's cost is to be recomputed by Karen;** no new
  figure is given here.
- **Fallback caveat.** Code tracing is a credible fallback for D-19 only if the digits fail for a reason
  other than Opus sitting at the ceiling, because code tracing may saturate Opus even more
  (`check-codetracing.md` point 6).

**OPEN**
- Nothing: settled by D-48 (sheet rows 14, 15).

---

## Reviewer notes (for Edith; delete before locking)

Places where repo files still disagree, or a number could not be sourced:
1. **Code-tracing subset shape and cost.** `options` §5.2 says 80 puzzles, 20 per wiring (four levels), at
   about $15 (§5.3); `check-codetracing.md` says 40 base puzzles × 2 shapes at about $32;
   `evidence` §0 prices the subset at $10.9 / $26.2 / $43.4 (low / central / high). The budget uses the
   `evidence` figure; the shape is open (section 11).
2. **Code in the Holm set?** `evidence` §3.7 and `check-setups.md` P9 list the code family as the sixth
   confirmatory contrast; `check-codetracing.md` point 9 says keep it out.
3. **Headline cost for multi-turn setups.** The brief says list price without caching. `check-setups.md` P5
   says cached or co-headline. `evidence` prices E2 as a stateless, cached coordinator but does not rule on
   the headline. Left OPEN in item 5.
4. **Not sourced:** the stop-loss limits (item 6), the prompt variant and its size (item 10), the release
   list (item 9) and the length of the "short window" (item 10) have no number in any file. Marked OPEN or
   "ours, unbacked".

Also: the register's D-21 note (b) says H1 "becomes" a non-inferiority test; Edith is telling Jarvis it
should say "may need" (`ops/reviews/2026-10-10-pr3-spec-r1.md`, S3). The checklist §4 "±8 / ±15" line is
being fixed by Edith (N25).

Resolved by D-26 and D-27: the E3 voting rule, the setups list (Opus-high, E1, Fable and pickers are
dropped), the latency subset and the hard slice. PR #4 is merged, so `data/free-tests/graded/` is cited
directly.

Resolved since the first draft: four wirings vs two shapes (D-24); old budget figures (`evidence` §0); D-15's
"4-digit values" (register note); "0 arithmetic slips" (verified, Edith's follow-up); the `H-README` clash
(already corrected on `main`); the Haiku 12/12 count (LOG).

---

## Amendments

*(After the locking commit, every change goes here as a dated entry with the reason. Nothing above
this line is ever edited silently once locked.)*

### Deviation 1 (2026-10-12)

*Copied word for word from `ops/reviews/2026-10-12-deviation-note-1.md` (Edith's wording). The checks behind
each claim, and the blinding confirmations, are in that file.*

> **Deviation 1 (2026-10-12): the number of steps per puzzle, decided after the pilot and before any main-study data.**
>
> **What was pre-registered.** `prereg-lock-1` (commit `b4b6b8474f39538055b3e358b48243d51aca5e3b`; the
> SHA-256 of the tar is `37454153435ae927ccd5aa3a5f61e4f7033e53a35875b830a3f9ccfd2c610adf`; git 2.39.5;
> Zenodo 10.5281/zenodo.23304164) fixed 24-step puzzles. It also fixed a pilot whose preset is chosen by a
> Haiku-medium-only rule (D-36(4)). If no preset scores between 15% and 60%, the decision returns to the
> user.
>
> **What happened.** The pilot `pilot-ledger-1` ran on 2026-10-11 and cost $8.73, with 0 refusals.
> Haiku-medium's whole-answer median was 0% at all three presets (means 0–2%). Under the pre-registered
> rule, the decision returned to the user. The pick file (`21fa9f0`) was committed before any Opus or Sonnet
> result was opened.
>
> We checked that the result was real: the answer keys were verified by an independent solver, and the
> scores were checked by hand. Haiku answers about 80–88% of single steps correctly, so 24-step answers are
> almost never fully right. Our earlier free tests in Claude Code had suggested about 98% per step.
>
> A small diagnostic (D-84, D-85; $0.42; Haiku only) sent the same puzzle text to the API's Haiku. Per step
> it scored 76% at effort medium and 88% at effort high, against 98% in Claude Code, which used no tools.
> The difference is the evaluation setup, not the task.
>
> **The decision (D-86, the user's ruling).** The study moves from 24 steps to N steps, as a declared
> deviation. N is chosen by a new Haiku-only pilot over N ∈ {4, 6, 8, 12, 16}, with a rule fixed in advance:
>   - for each N, take the median Haiku-medium whole-answer score, pooled over both shapes;
>   - choose the N closest to 37.5% within 25–50%;
>   - failing that, the closest within 15–60%;
>   - failing that, the decision returns to the user;
>   - a tie goes to fewer steps.
>
> The ladder has 20 base puzzles × 2 shapes at each N (D-87). Opus-medium and Sonnet-medium answer each
> ladder puzzle once. Those answers are sealed until the pick is committed, and they never enter the pick.
> After the pick, the Opus answers at the chosen N are used for the D-72 power and cost re-run. The full
> curve across all N (every model's accuracy against N) is reported as a pre-registered descriptive result,
> and no answer at a non-chosen N is used for any decision.
>
> **What changes:**
>   - the number of steps per puzzle;
>   - the frozen task sets (new ladder, main and ext40 sets at every candidate N, all disjoint from earlier
>     sets);
>   - the two shapes become N×1 and 1×N;
>   - the official score counts N step lines;
>   - the parse fixtures are added at each N;
>   - the budget and power are re-run.
>
> **What does not change:**
>   - the rule kinds (preset l14);
>   - the prompt wording (D-77, D-80);
>   - the D-76 scoring rules;
>   - the five confirmatory tests, with N as a parameter;
>   - the 10-point margin, the one-sided α of 0.025 with Holm, and the paired BCa bootstrap;
>   - the k rule (D-33, D-70);
>   - the headline rule, the fairness check and the bias table;
>   - Haiku-medium as the calibrating and confirmatory arm.
>
> **Blinding.** Up to the cut of `prereg-lock-2`, no team member opened any Opus or Sonnet answer, score
> or accuracy from the pilot. Only per-model call counts, refusals, token counts (including output lengths) and costs were seen, for pricing.
> The pilot runner scores every answered call automatically and writes the scores, Opus and Sonnet included, into
> `compact_table.csv` (SHA-256 `83c18fd960022575ccfc2b9d1819217d242b122de87682dbda34e21e5cf30d54`). That file was
> hashed but not opened. Haiku's scores were read through a Haiku-only extract and Haiku-only filters on the call
> log (`calls.jsonl`, SHA-256 `411c877baf3f4b399d44355c6d77126c4abd7c348d17fca194aa0e46d7f79142`). Every decision above
> was made on Haiku-medium data and the Haiku-only diagnostic.
>
> The pilot's Opus and Sonnet 24-step results will be opened after `prereg-lock-2` is posted, and reported
> as exploratory. The 24-step pilot and the diagnostic are reported in the paper as findings.
>
> **Other changes since `prereg-lock-1`.** One runner fix, so that the pilot's real-time check runs on a
> ledger set (`5e2b860`, reviewed CLEAN). It changed no task, wording, scoring or analysis.
>
> **The record.** `prereg-lock-2` and its fingerprint will be posted as a new version of the same Zenodo
> record. Version 1 stays public.

### What prereg-lock-2 fixes (2026-10-12; D-86 to D-89)

Before any ladder call, the tag `prereg-lock-2` fixes the following. **One dated amendment** after the ladder fills in only
the values the pre-set rules choose: N, k's inputs at N, `max_tokens`, whether D-72 fires, the D-73/D-74 outcome (any cut, or
extras traded for the add-40), and the near-ceiling label for tests 1–2.
1. **This spec with Deviation 1.** Items 1 and 3–5 of "The lock before the pilot" hold at N steps: the five tests take N as a
   parameter, and the official score (D-76) counts N step lines. In this spec and in the code's field names, 1×24 reads as
   1×N and 24×1 as N×1.
2. **The generator and the sets.**
   - Generator code **ledger-0.5** (gated at `19a48fd`): ledger-0.4.2 plus the presets `l14n4`, `l14n6`, `l14n8`, `l14n12` and
     `l14n16`. These are l14's rule kinds and dials at N steps, with the house window scaled from l14's 5–8 of 24. The 24-step
     presets are unchanged.
   - The frozen sets at every N: `ladder-ledger-l14n{N}-v1` (20 base × 2 shapes), `main-ledger-l14n{N}-v1` (80 × 2) and
     `ext40-ledger-l14n{N}-v1` (40 × 2). They are disjoint from each other and from every lock-1 set.
3. **The ladder pick and runner.**
   - The pick (`harness/analysis/choose_preset.py`) reads Haiku-medium only. It chooses the pooled median closest to 37.5%
     within 25–50%, else within 15–60%; failing both, it goes back to the user, with no further rungs. A tie goes to fewer steps.
   - The pick is committed, with the hashes of its input and traces, before any Opus or Sonnet ladder answer is opened.
   - The runner (`harness/pareto/ladder.py`) sends each puzzle to Haiku-medium ×10, Opus-medium ×1 and Sonnet-medium ×1.
     Opus and Sonnet stay sealed.
4. **The k script and the analysis code** as in items 4–5, at N. Also the curve code (`harness/analysis/curve.py`, D-87),
   which is descriptive only; just the chosen N's Opus point feeds a decision.
5. **The tests on simulated data at N**: `research/fixtures/sim-main-n/` (720 cases over the five N, zero mismatches),
   alongside `sim-main-v2`.
6. **The plan and the record.**
   - The pilot plan, `research/pilot-plan-ledger.md`. It holds the ladder rule, the budget ($13.5 central, $19.9 high,
     hard cap $30 under D-89), the near-ceiling flag and the curve plan.
   - The D-72 simulator.
   - The post-pilot decision code and its spec: `research/d72-d73-lock-spec.md`, `research/models/study1_budget.py`,
     `research/models/study1_cut_order.py` (with the D-74 known-answer examples) and `research/models/ledger_measured.json`,
     filled after the ladder by the `post_pilot` route.
   - The list of SHA-256 hashes of every file in the tag (`ops/lock/LOCK-MANIFEST.md`).
   - The public fingerprint is computed as for lock-1 and posted as a new version of the same Zenodo record.


### Amendment 1 (2026-10-12): the values the pre-set rules chose after the ladder

*The one dated amendment to `prereg-lock-2`. It fills only the values that the locked rules choose, plus disclosures; it adds no test
and changes no rule. Sources: run `ladder-l14n-1`, with SHA-256 `calls.jsonl` 3725c1cc…52f4, `compact_table.csv` a4f60c97…8585 and
`ledger.jsonl` 09536cbc…19 (spend log); and the files in `data/pilot/` named below. Every value is stated under the marking rule
of Deviation 2 (below, D-90), the rule from `prereg-lock-3` on, with the value under `prereg-lock-2`'s rule beside it where the two
differ; the `-d90` files hold the first, the others the second.*

**1. N = 6 (preset `l14n6`), tier 1.**
- Haiku-medium's pooled median whole-answer score by length, under the official D-76 score:
  - 4 steps 0.550;
  - **6 steps 0.500**;
  - 8 steps 0.500;
  - 12 steps 0.100;
  - 16 steps 0.100.
- 6 and 8 are both 0.125 from 37.5%, inside the 25–50% band, and the tie goes to fewer steps.
- The pick file is `data/pilot/preset-choice-ladder-l14n-1.json` (SHA-256 4cf5f2f8…c50f; input sha256 38a68adc…ed96). It was
  committed at `e8c4d43` before any Opus or Sonnet ladder answer was opened, and Edith recomputed it independently
  (`ops/reviews/2026-10-12-ladder-l14n-1-pick-check.md`).
- **The same under both marking rules.** Re-scored under Deviation 2 (`data/pilot/preset-choice-ladder-l14n-1-d90.json`, SHA-256
  a95350b9…9353): l14n6, with every preset's score identical. Only Haiku's 1×n format compliance moves, by 0.5 points at n = 8,
  12 and 16.
- So the main study runs on `main-ledger-l14n6-v1` (80 base × 2 shapes, 6×1 and 1×6), with `ext40-ledger-l14n6-v1` held for D-72.

**2. k's inputs (D-33, D-70).**
- From the ladder's costs at 1×6: Opus-medium $0.0207948 per puzzle, Haiku-medium $0.00056534875 per sample.
  - The ratio is 36.78, so **k = 36**: floor, cap 40.
  - Every call was Batch, so the ratio is the same at list price.
- This k feeds D-72's power re-run only. The confirmatory k is still computed from the main run's own costs by `kscript`,
  committed before any grading (D-33).
- The ladder's `k_table` shows 10 only because 10 Haiku samples were drawn per puzzle there; the main run draws 40 (D-70).

**3. `max_tokens` for the main run.**
- The locked rule (`harness/pareto/limits.py`) is that the pilot's largest outputs set the main run's limits, at about 1.5×.
- The ladder's largest outputs at n = 6 (effort medium, both shapes, 0 truncations) were:
  - Haiku 3,076 tokens;
  - Opus 2,479;
  - Sonnet 1,610.
- At 1.5×, rounded up to the next 1,000, that gives: **Haiku 5,000; Opus 4,000; Sonnet 3,000.**
- **Every setup the ladder did not measure keeps the locked pilot limits** (Haiku 48,000; Opus and Sonnet 32,000), because
  the limit must not bind. That covers any other effort, thinking off, Haiku-max, the E2/E3 step and aggregator calls, and
  H-pick8 (Edith, A1-1).
  - This only makes the guard's booking larger, never the bill; the guard sends in more waves.
  - Truncations are logged and reported per setup, as locked.

**4. D-72 (the add-40 rule).**
- **Inputs at n = 6, 1×6, official score** (`data/pilot/d72-inputs-ladder-l14n-1.json`, SHA-256 a13358ea…5cd9):
  - Haiku-medium 92 of 200 tries right (m = 0.46). Per puzzle: 1, 6, 9, 0, 7, 6, 10, 7, 1, 8, 7, 0, 3, 2, 4, 3, 10, 0, 0, 8 of 10.
  - Wrong-try pairs with the same trace: 69 of 360.
  - Opus-medium 20 of 20 (p_opus clipped to 0.99).
  - k = 36.
  - **The same under both marking rules** (`data/pilot/d72-inputs-ladder-l14n-1-d90.json`, SHA-256 ef408fc5…7d1d): the same
    per-puzzle counts, the same 69 of 360 agreeing pairs and the same 20 of 20.
- **Outcome (Karen, `research/post-pilot-n6.md`; `d72_rerun` with the pinned config, seed 20261011, nsim 4,000).**
  - Fitted inputs: m 0.46, concentration 1.163, repeat share 0.438, p_opus 0.99 (clipped from 1.00), k 36.
  - P(conclusive) at 80 base puzzles is **1.000** (non-inferior 0.00, worse by more than the margin 1.00; half-width ±14.09).
    At 120 it is also 1.000.
  - **`add_40_power_test` is false, so there is no add-40.** Karen's independent count from the raw replies matches (92/200;
    69/360).
  - In that model, test 2 reads "worse by more than the margin". That is the pinned power model's forecast under the
    measured inputs, not a result; only the main run's data decide test 2.

**5. D-73 / D-74.** `post_pilot_decision(False, 2, spent = 20.76)` gives no add-40, the **full plan** and **no cut**.
- The pinned `ledger_measured` fill (`post_pilot: true`) gives an all-in high case of **$70.3**; it is $73.6 on the exact measured
  totals. Both are far under the $170 ceiling.
- The fill: input 1,031; visible 223; tm [0.1305, 0.1305, 0.1631]; hm_ratio 1.49; sm_ratio 0.39.
- Karen notes that the single visible-output mean under-states Opus's and Sonnet's longer visible replies; the decision is the
  same either way.

**6. The near-ceiling label: ON.**
- Opus-medium's pooled whole-answer accuracy at n = 6 is 40 of 40 (1.00 ≥ 0.95): 6×1 20 of 20, 1×6 20 of 20. The same
  under both marking rules.
- So tests 1–2 are labelled near ceiling, and the paper reports the error-rate ratio (Haiku-vote errors ÷ Opus errors), with its
  interval, next to the non-inferiority result. The bias-table row is added.

**7. The price window.** The price table is dated 2026-10-12, from Karen's re-check. It covers paid main-run waves on
2026-10-12 and 2026-10-13 UTC only; any wave later than that needs Karen's re-check first (Edith, A1-4).

**Disclosures**
- **Operational correction (wording by Edith, word for word from her ladder clearance):**

> **Operational correction (no change to the design).** The lock-2 pilot plan says that pilot-1's passing Console check
> "already opens the guard's Batch gate, so no new bill check is needed". In practice the spend guard accepts a Console
> check only within the run whose ledger recorded it, because it requires a check's claimed Batch figures to match that
> ledger's own Batch commits. So, as for the pilot (N67), a fresh Console reading was recorded under the ladder's own run
> id (`ladder-l14n-1`; $11.78 used, read 2026-10-12 ~07:28 UTC) before any ladder call. This changes no task, rule,
> score, test or decision rule.

- **The post-lock runner fix** `5e2b860` (the real-time check on a ledger set) is already disclosed in Deviation 1, under
  "Other changes since `prereg-lock-1`". No other code changed between the lock-2 tag and the ladder.
- **Erratum to the lock-1 pilot plan.** One sentence reads "A l16 ×20, B l15 ×10, C l14 ×10". Slot B (l15) was **20** puzzles
  (10 base × 2), as the slot table says and as frozen and run.
- **Timing of the curve run.** `curve.py --pick` ran at about 08:00 UTC, after the pick was committed (07:54:40 UTC). That is the
  locked order. Edith had asked for a hold while she recomputed the pick; the request arrived after the run had finished. The
  output stayed unread until her go. Nothing was decided on it.

**Pointers (descriptive, not tests)**
- The D-87 curve under Deviation 2: `data/pilot/curve-ladder-l14n-1-d90.json` (SHA-256 33ab2609…20f0). Under `prereg-lock-2`'s
  rule: `data/pilot/curve-ladder-l14n-1.json` (SHA-256 1300a410…36ad).
  - Only Sonnet-medium's 1×n numbers differ. Whole answer at 1×4 is 80% (55% under the old rule), at 1×6 85% (70%), at 1×8
    85% (75%). Its 1×n format compliance is 100%, 95% and 100% (60%, 75% and 90%).
  - Haiku's and Opus's numbers are the same, apart from Haiku's format compliance (+0.5 points at n = 8, 12 and 16).
- Pilot-1's 24-step results for all three models, exploratory: `data/pilot/pilot-ledger-1-exploratory.md`. Karen's
  Opus-vs-Sonnet note: `research/paper-notes/opus-vs-sonnet-exploratory.md`.
- **Sonnet's repeated step lines** are the subject of Deviation 2, below (D-90). Its format compliance under both rules is
  reported in the appendix (Edith, A1-3).


### Deviation 2 (2026-10-12)

*Copied word for word from `ops/reviews/2026-10-12-deviation-note-2-and-lock3-route.md` (Edith's wording). The ruling is D-90.*

> **Deviation 2 (2026-10-12): the marking rule for repeated step lines, decided after the ladder and before any main-study data.**
>
> **What was pre-registered.** The official score (D-76) failed any chain answer that writes a step line more than once,
> even with the same balances (`extra_line`).
>
> **What happened.** In the ladder, Sonnet-medium often wrote every step line while working, then repeated them all,
> with identical balances, before its Answer line. At the chosen 6 steps this marked 3 of its 20 chain answers wrong
> although every value was right (14 of 20 instead of 17). Haiku and Opus were essentially unaffected. Because Sonnet
> is the comparison model in tests 3 and 5, the old rule would have made "matches" easier to reach in those tests, for
> a reason unrelated to the question.
>
> **The decision (D-90, the user's ruling).** A step line written more than once with the **identical** balances is
> accepted and read as those balances. A step line repeated with **different** balances still fails, as before. The
> rule is the same for every model. Nothing else changes. The deviation was prompted by Sonnet's ladder replies, after
> the ladder pick was made; no main-study data existed.
>
> **Reporting.** The results under the original rule are reported as a sensitivity check: one paragraph in the
> methods, one line beside tests 3 and 5, and the full tables in an appendix.

---

## How this gets locked

1. The user rules on each OPEN question. Jarvis records every ruling in `decisions/register.md`, in the
   user's words, and Friday updates the matching section (RULED text only for what the register covers).
2. Edith reviews the complete spec against `ops/review-checklist.md` until it is clean. Friday removes
   the "Reviewer notes" section.
3. The user approves the merge. The spec is then locked by a **locking commit**; its hash is written into
   the first line of this file and cited by the paper.
4. After that, any change is a **dated amendment** under "Amendments", with the reason. Never a silent
   edit. No main-run data exists before the lock.
