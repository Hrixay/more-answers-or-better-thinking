> **Superseded by `research/study1b-spec.md`** (2026-10-13). The user ruled D-96: go, 5-point primary, Tier B and the 12-step point. Edith's F-1 to F-7 are applied in the spec.

# Study 1b: a pre-registered follow-up on "Haiku at max effort", plus an effort sweep (plan for the user)

*Karen (Opus 5.5), 2026-10-13. A brief for the user, via Jarvis. No API calls; this is desk work on the opened main-run results.*

*Inputs:*
- *Edith's procedure advice: `ops/reviews/2026-10-12-followup-procedure-advice.md`;*
- *Friday's feasibility facts, from costs and token counts only;*
- *`data/main/main-l14n6-1/analysis.json` (43d18eed…);*
- *the ladder curve (`data/pilot/curve-ladder-l14n-1-d90.json`);*
- *two fresh documentation checks in `research/facts-checked.md`: the output limits, and the effort levels below.*

*Recommendations are marked as mine. The user decides.*

## 1. Background: what the main run found, in plain words

The main run asked Haiku at several effort levels. It also asked Sonnet and Opus at two levels. It used 80 six-step puzzles, each in
two forms: a chain, where each step uses the last answer, and separate pieces.

| Setup | Chain (1×6) | Pieces (6×1) | Cost per answer (list price) |
|---|---|---|---|
| Opus, medium effort | 96.25% | 100% | about 4–5¢ |
| Opus, low | 97.5% | 100% | about 4¢ |
| Sonnet, medium | 80% | 75% | about 1.5¢ |
| **Haiku, max effort, one try** | **97.5%** | **95%** | **about 0.4¢** (about 1/10 of Opus) |
| Haiku, max, vote of 3 tries | 100% | 98.75% | about 1.2–1.3¢ (about 1/4 to 1/3 of Opus) |
| Haiku, medium (the study's main cheap setup) | 44% | 51% | about 0.1¢ |

**The striking result:** Haiku at **max** effort came close to Opus on these puzzles at about a tenth of the price: 97.5% against
96.25% on the chains, and 95% against 100% on the pieces (Edith's fact check 1).

**But it's exploratory:**
- Haiku-max was an "extra" arm, with 3 tries per puzzle;
- the comparison was not one of the pre-registered tests;
- it was found after looking at the data.

So the paper can only call it a lead. To claim it, we need a **new, separately pre-registered test on fresh puzzles**. That is Study
1b.

## 2. Why a follow-up is worth it

- **It could become the paper's most useful practical finding:** "the cheap model at max effort is as good as the expensive one, for
  about a tenth of the price". But only if it holds up when tested properly.
- **Six steps may be too easy to tell the models apart.** Opus is near 100% at every length we tried. The ladder shows Opus-medium at
  97.5–100% from 4 to 16 steps.
- **Haiku at medium effort collapses at longer lengths.** It falls from about 50% at 6 steps to 18% at 16 steps. **Whether max effort
  keeps Haiku up at 16 steps is the most informative open question.**
  - If it does, the claim is much stronger.
  - If it doesn't, that's a clear and honest limit: "max effort rescues the cheap model on short procedures only".
- **The effort picture has gaps.** We never ran Haiku at high or xhigh, or Sonnet or Opus above medium. Sonnet's own default is
  "high", so our "Sonnet-medium" was a step below its default. A full effort sweep would show where each model's accuracy levels off,
  and at what cost.

## 3. The proposal

### 3a. The confirmatory question (Study 1b's own family of tests)

**Three tests, corrected for multiple testing with Holm across these three only, and never pooled with Study 1** (Edith):

| Test | Question | Puzzles |
|---|---|---|
| **B1** | Is **Haiku-max's single try** no worse than **Opus-medium** at **16 steps**? | 80 fresh 16-step puzzles, both forms (160 items) |
| **B2** | Is **Haiku-max's vote at equal money** no worse than Opus-medium at 16 steps? (k = Opus's cost ÷ Haiku-max's cost per try, about 7) | the same |
| **B3** | **Replication at 6 steps:** is Haiku-max's single try no worse than Opus-medium on **new** 6-step puzzles? | 40 fresh 6-step puzzles, both forms (80 items) |

- **Each test pairs the two models on the same puzzles.** The score is the whole answer, as in Study 1. The two forms are pooled for
  each puzzle; the per-form numbers are shown as description.
- **Haiku-max gets 10 tries per puzzle**, so its single-try accuracy is measured precisely and the equal-money vote is possible.
  **Opus-medium gets 2 tries per puzzle**, which narrows the comparison where Opus sits near 100%.
- **"No worse than" means within a set margin** (non-inferiority). **Which margin is a choice for the user:**
  - **5 points** (Edith's advice and mine): meaningful near the ceiling. A "match" then means Haiku-max is at most 5 points below Opus.
  - **10 points:** Study 1's margin, so the two are comparable. But at Opus's 98%, 10 points would allow Haiku-max at 88%, which is
    six times Opus's error rate.
  - **Either way:** the 10-point reading is shown alongside as secondary, and the **error-rate ratio** (how many times more often
    Haiku-max is wrong) is reported beside every test, by the same rules as Study 1.

### 3b. Where: fresh, never-used puzzles

**Frozen sets that were never sent exist** (Friday checked every call log):
- **at 16 steps:** `main-ledger-l14n16-v1` (80 base × 2 forms);
- **at 6 steps:** `ext40-ledger-l14n6-v1` (40 base × 2);
- also 12-step and others.

**Why they count as fresh:**
- they were generated and frozen at lock 2, **before any Haiku-max data existed**;
- they are disjoint from every used set (the lock-2 all-pairs check).

Edith accepts them as fresh after one recorded "never sent" check. The paper says how they were made.

**24 steps is not proposed.** The only never-sent 24-step sets were frozen at lock 1, outside lock 2's list. Using them would add a
second lock's sets and a length the budget here doesn't cover. (An earlier draft said they use older wording; Jarvis's check found their
wording matches Study 1's.)

**The length is chosen now from the ladder curve** (as Edith asks): 16, the longest frozen length, where Haiku-medium collapses and
Opus stays high.

### 3c. Sample size and power

This is my quick simulation; the locked D-72-style simulator replaces it in the spec. It assumes 80 puzzles pooled over both forms,
Opus at 98%, and Holm's strictest step for three tests.

| If Haiku-max's true accuracy at 16 steps is… | Chance B1 shows "no worse" at **5 points** | at **10 points** |
|---|---|---|
| 98% (level with Opus) | 0.97–1.00 | 1.00 |
| 95% | 0.13–0.32 | 1.00 |
| 92% | about 0 | 0.5–0.9 |
| 88% or below | about 0 | about 0 |

- **What this means:**
  - with a 5-point margin, Study 1b confirms "no worse" only if Haiku-max really is about level with Opus;
  - a 3-point gap comes out "not shown", which near 100% is honest, since 95% against 98% is 2.5 times the errors;
  - with 10 points, the test is easy to pass but says less.
- **B3** (40 puzzles at 6 steps) has power of about 0.8–0.9 at 5 points if Haiku-max is level with Opus.
- **B2** (the vote) should have **more** power than B1, because voting raises Haiku-max's accuracy.
- **The near-ceiling issue is real and stated up front:** at Opus's level, even 5 points resolves little. The error-rate ratio,
  reported beside each test, carries the real information.

### 3d. The effort sweep (pre-registered as description, not as tests)

**This is a pre-registered figure, "accuracy against effort", at 6 and 16 steps, on the same fresh puzzles.**
- All three models support five effort levels: low, medium, high, xhigh and max. This was checked today on Anthropic's effort page;
  Haiku can also run with thinking off.
- **The figure has no tests.** Each point has its interval, and the cost per answer is beside it.

| Tier | What it adds | Batch cost, central (high case) |
|---|---|---|
| **A (my recommendation)** | Study 1b's core (B1–B3), plus **Haiku's whole effort range** (off, low, medium, high, xhigh at ×5; max at ×10) at 6 and 16 steps | **$34** (about $51) |
| B | A, plus **Sonnet's five levels and Opus at low, high, xhigh and max at 6 steps** | $56 (about $84) |
| C | B, plus Sonnet and Opus at every level at 16 steps too | $132 (about $198): **over budget** at the high case |
| Optional | A Haiku-max and Opus-medium point at **12 steps**, so the length curve gets a Haiku-max line at 6, 12 and 16 | +$11 |

**Cost basis:**
- **Measured:** Haiku and Opus at 6 steps (main run); Opus at 12 and 16 steps (ladder).
- **Friday's estimates:** Haiku-max at 12 and 16 steps.
- **My rough guesses, to be replaced:** the levels nobody has run yet (Haiku high and xhigh; Sonnet high and up; Opus high and up),
  taken as multiples of medium. A **small first wave** measures tokens and truncations before the rest (Friday's advice). It reads
  **costs and counts only**, never answers, under a pre-set rule.
- **Output limits:** Haiku-max at 16 steps may write up to about 45,000 tokens. Haiku 5.5 allows 128,000 per call (300,000 in Batch
  with a beta header; checked today), so the limit is raised to 96,000. Opus and Sonnet at xhigh or max get 64,000, the docs'
  suggested start.

## 4. Money and time

- **Credit left:** $158.30 (the user's Console reading after the main run). It expires on **2026-10-19**, so the plan finishes by
  **10-18**.
- **The later extras run** (the E2 team, the picker and E3 at 6×1) needs its own slot and a cap of about $25. **Only one paid run can
  go at a time**, so they are sequenced.
- **Fit:**
  - Tier A's high case ($51) plus the extras (~$25) leaves about $80 unused;
  - Tier B's high case ($84) plus the extras leaves about $50;
  - Tier C doesn't fit safely.

**Steps, each with its owner and gate (Edith's procedure):**
1. **The user rules** on Study 1b: yes or no, the margin, the tier, and the 12-step point.
2. **Karen writes the Study 1b spec section:** the tests, the margin, Holm, the sets, the sweep figure and the first-wave rule. It
   includes power from the locked simulator. Edith reviews it.
3. **Friday adds a slim runner** (about half a day to a day): it runs a chosen list of setups on one set, with a token limit per arm
   and nothing else. He adds the analysis entries. Edith reviews.
4. **The fresh-set "never sent" check**, recorded.
5. **prereg-lock-4** holds the spec, the sets and the code. Then the gist and Wayback, then a Zenodo version, **all before any call**.
6. **Karen's price re-check** within 24 hours before the start; Edith's clearance; a **fresh Console reading** under the new run id; the
   user's go and cap; the 48-hour window; the 2% truncation pause.
7. **The run itself**, in Batch, takes hours, not days. Then the stamped analysis runs once.

**A realistic calendar:** steps 1–5 on 10-13 and 10-14; the run on 10-14 or 10-15; results on 10-15; the extras run either side. That
leaves room before 10-18.

## 5. What it would let the paper claim

**If B1–B3 show "no worse" at 5 points:**
> "In a separately pre-registered study on fresh puzzles, Claude Haiku 5.5 at max effort was no worse than Claude Opus 5.5 at medium
> effort, within 5 points, on 16-step procedures, at about a seventh of the cost per answer, and the result replicated at 6 steps."

That is a confirmatory, practical result.

**If B1 fails but B3 holds:**
> "Max effort lets the cheap model match the expensive one on short procedures, but not on long ones."

That is also confirmatory, and just as useful to readers.

**In either case:**
- the **effort × length figure** (descriptive) shows the full picture, such as where extra effort stops helping each model;
- Study 1's Haiku-max finding stays labelled exploratory and is reported as the reason Study 1b was run.

## 6. Recommendation (mine)

**Run Study 1b, Tier A, with the 5-point margin as primary,** plus the optional 12-step point if the user wants the length curve.

**Why:**
- it settles the most interesting finding properly, in either direction;
- it adds Haiku's full effort range;
- it stays well inside the credit (about $51 even in the high case) and the time;
- it leaves room for the planned extras run and a safety margin.

**Tier B** is a reasonable step up if the user wants Sonnet and Opus at high and max too, at 6 steps only.

**Decisions for the user:**
1. Go or no-go on Study 1b.
2. The margin: 5 points primary (recommended) or 10.
3. The tier: A (recommended), B, or C (not recommended).
4. Add the 12-step point (+$11)? Optional.
