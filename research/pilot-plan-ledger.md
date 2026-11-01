# Pilot plan: ledger family (D-36 updated for D-56, D-58, D-59). DRAFT r2 for Edith, then the user

*Karen, 2026-10-10. This replaces the digit plan in `data/pilot-plan.md`. Preset names are left blank
until Friday's second free Haiku read (l5–l7) lands. No model calls were made to write this.*

**Purpose.** Measure, on practice puzzles that never enter the confirmatory analysis (D-36(1)):
- tokens and the ledger thinking multiplier;
- Haiku's accuracy and its spread across puzzles;
- how often Haiku's wrong answers repeat (at least 10 tries per puzzle);
- Opus and Sonnet accuracy;
- refusal rates per model;
- latency, and batch vs real time;
- each model's slips per rule kind, for the fairness check (D-67; section below).

It then picks the main preset.

**Presets and sizes.** Three ledger presets, each its own set id `pilot-ledger-<preset>-v1`.

**Disjoint sets (K4).** The pilot sets share no base puzzle, seed or prompt with:
- **the 20-call check set (D-57):** `check-ledger-<preset>-v1`, 5 base × 2 shapes;
- **the S3 check-Batch set:** `smoke3-ledger-<preset>-v1`;
- the free-read sets and every other set.

Friday's `freeze --disjoint` is run on each pair before the clearance.

| Slot | Preset (ledger-0.3, round-number base) | Free reads (Haiku, Max plan, whole answer) | Puzzles |
|---|---|---|---|
| A: best guess for 37.5% | **l16** (10 lines, repeat ×5, house rule on 9–12 steps, 8 decoys, in-turn sweep rules) | read 6: 8/12 ≈ 67% (chains 3/6, pieces 5/6) | 20 (10 base × 2 shapes) |
| B: middle bracket | **l15** (8 lines, 6 decoys, house rule, look-again) | read 5: 4/6 ≈ 67% (chains 3/4, pieces 1/2) | 20 (no shrink needed on the measured tokens, 2026-10-11) |
| C: easy bracket | **l14** (6 lines, round-number base) | read 5: 5/6 ≈ 83% (chains 3/4, pieces 2/2) | 10 (5 base × 2) |
| Spare rung (D-36(4)) | **l17** (harder than l16, same base; pre-built and frozen) | — | 10, only if A, B and C are all above 60% on the API |

**Retired:** l10, l12 and l13 can't be built under Edith's 5% transfer-slip cap (B1). l11 still builds but
leans on percentage arithmetic, so it is not used, per D-62.

**The check and S3 sets go at slot A** (Jarvis): `check-ledger-l16-v1` and `smoke3-ledger-l16-v1`, both
disjoint from the pilot sets.

**Why this assignment** (OURS):
- **l16 is the best guess.** The free reads put l14 and l15 above the band (83% and 67%; 12 runs, so
  noisy), and l16 is the hardest preset built on the same base.
- **l15 and l14 bracket the target from below.** That covers the case where the API's Haiku-medium is
  weaker than the Max-plan helpers.
  - There is a weak hint of this. On digit d4s, the API's Haiku got 0 of 5 whole answers right in smoke-2
    (1 puzzle).
  - The free reads on d4s got about 50% (2/4, `data/wording-check/`).
  - smoke-2's API samples used 2.6–5.5K output tokens, so the API model does think. Whether it thinks
    more or less than a Max-plan helper is unknown.
- **l17 covers the other direction:** an API Haiku stronger than the reads.
- **l14 is the least likely pick.** That's why it gets the small slot; slot B (l15) is the one shrink
  step 1 cuts.

**Does the preset rule still work if the API's Haiku runs lower than the Max-plan reads?** Yes, mostly
(OURS):
- **If the API is somewhat lower**, l15 or l14 lands in 25–50% and is picked. l16 may fall below 25% and
  is simply not chosen.
- **If the API is much lower**, every preset falls below 15%, l14 included. D-36(4) then calls for "one
  extra rung", but **the pre-built spare (l17) is harder, so it is the wrong direction.**
  - Pre-register the direction: if every preset is below 15%, the extra rung is an **easier** preset on
    the same base (for example l14 with 4 lines), built at that point, with its own small cap and the
    user's go.
  - Given l14 scored 83% in the free read, this case looks unlikely.
- **If the API is higher**, every preset sits above 60%, and the spare l17 runs as planned.

That is 50 puzzles as planned; no shrink step is needed on the measured tokens (see below). There is no code slice (D-59).

**Per puzzle** (Batch, effort medium, adaptive thinking):
- Opus-medium ×1;
- Sonnet-medium ×1;
- Haiku-medium ×10.

`max_tokens` per B7: Opus and Sonnet 32K, Haiku 48K, to be re-checked against Friday's measured reply
lengths. That is 600 Batch calls.

**Real-time check** (D-35/D-36): the first 10 puzzles of slot A (5 base × 2), with Opus ×1, Sonnet ×1 and
Haiku ×5, streamed, at list price: 70 calls. The batched side of the comparison is the pilot's own Batch
calls on the same puzzles (Friday's design), so there are no extra duplicates.

**Cost** (OURS; `research/models/study1_budget.py`; Friday's **measured** l14–l17 lengths, @c057a6e;
thinking multiplier unmeasured):

| Variant | Low | Central | High |
|---|---|---|---|
| As planned (A 20, B 20, C 10) | $6.5 | $15 | **$34** |
| Step 1: slot B 20 → 10 | $5.5 | $12.7 | **$29.1** ✓ (thin margin) |
| Steps 1 + 3: also the real-time check 10 → 6 | $4.8 | $11.2 | $25.5 |

Smoke-2's real API output lengths (Haiku-medium 2.6–5.5K tokens per puzzle, against the model's 14K
central) suggest actual costs well below this.

**Update from the 20-call check (check-ledger-1, 2026-10-11).** Token counts and cost only, which D-78 C
allows before the lock. The projection is `research/models/check20_projection.py`.
- **Measured output per call:** Opus-medium about 7.0K (1×24) and 7.2K (24×1); Sonnet-medium 6.6K and
  6.8K. The largest single output was 10.5K.
- **Thinking**, taking visible output as 660 tokens:
  - Opus: about 6.4K, so TM = 0.64 (the high case uses the largest output: 0.99);
  - Sonnet/Opus thinking ratio 0.93.
- **Haiku is not measured.** Its Haiku/Opus ratio stays at 1.42.

| Variant | Central | High |
|---|---|---|
| As planned (A 20, B 20, C 10) | $9.6 | **$13.9** |
| Step 1 (B → 10) | $8.2 | $11.8 |
| Steps 1 + 3 | $7.2 | $10.4 |

- **No shrink step is needed:** even as planned, the high case is less than half the $30 cap. So the
  shrink rule doesn't fire, and slot B keeps its 20 puzzles.
- **Sensitivity to Haiku's thinking:** at a Haiku/Opus ratio of 2.5, the planned pilot is still about
  $15.5 high.

**Cap and shrink rule.**
- The **hard cap is $30**, enforced by the spend guard (D-36(3)).
- Before the run, if the worst case at the high estimate exceeds $30:
  1. apply **step 1** (slot B → 10 puzzles);
  2. if it is still over, apply **step 3** (the real-time check → 6 puzzles).
- Haiku stays at ×10 throughout, for the repeat-share measurement.
- Shrinking is decided before the run, never during it.
- **Pilot shrink note (2026-10-11, superseding the two points below).** On the tokens measured in the
  20-call check (check-ledger-1), the pilot as planned costs **$13.9 at the high estimate**, under half
  the $30 cap.
  - So **no shrink step applies:** slot B keeps its **20** puzzles, and the real-time check keeps its 10.
  - The trim decision is no longer needed (Jarvis is telling the user).
  - Source: `research/models/check20_projection.py`.
  - The open item is Haiku's thinking ratio, which the pilot itself measures. Even at a Haiku/Opus ratio
    of 2.5 the planned pilot is about $15.5 high.
- *(Superseded)* On the earlier modelled lengths, step 1 was needed and was enough ($29.0 at high).
- *(Superseded)* My earlier suggestion to apply step 3 too, for a margin.

**Order of runs (K1, matching the guard as merged).** Before any live run, PR #17 (with P3 fixed) must
be merged, together with the marker events for smoke-2's two free refusals. Without a passing Console
check, the guard caps all live Batch reservations at $1. So the order is:
1. **The 20-call check** (D-57; real time, one call at a time, stop at the first refusal).
2. **The S3 check Batch** (its own clearance and go).
3. **A passing `console-check --run-id <pilot run id>`,** recorded under the **pilot's own run id**.
   - Do it after the S3 Batch and before the pilot's big Batch. It lifts the $1 Batch limit for the
     pilot.
   - A pass recorded under the S3 run id does not carry over (Edith N67), because smoke-2 and the
     20-call check have spend (N64).
4. **The pilot's Batch waves, with no stop between them.** The worst case is about $30 at the Batch price
   for the 600 calls against the $30 cap, so expect two waves. A second Console reading after wave 1 is
   an optional cross-check, not a gate.
5. **The real-time check, last** (about $11 worst case at list).

Each Batch wave usually takes under an hour and at most 24 h. The old "stop after wave 1 for the
Console" (R10) is superseded by step 3.

**Stops** (as ruled):
- money (the $30 cap; $200 global);
- a model mismatch or change, or a stale price table (D-42);
- any Haiku input over 100K tokens.

**Refusals don't stop the run.** They are counted per model and category. Under D-58 a refusal leads to
support and the "as deployed" framing, with no rewording or switch. D-36(5), the answer-only switch:
- **Edith recommends** keeping it, but triggering it **only on `reasoning_extraction` blocks above 2%** of
  any model's answers, and never on `cyber` or other categories.
- The ledger's answer-only wording would then be written and approved **now**, with the main wording
  (L4).
- **This narrows a ruling, so it awaits the user** (Jarvis is bringing it with the wording approval). I
  agree with it.

**Choosing the main preset** (D-36(4), unchanged):
1. For each puzzle, Haiku's single-try accuracy is the share of its 10 tries that are **fully right
   under the official score**:
   - a 24×1 puzzle counts as right only if all 24 pieces are right (D-39);
   - a 1×24 chain counts as right only if **all 24 step lines are right and the Answer line equals line
     24** (D-76, which amends D-36(4)).

   The final-answer view of the chains is reported beside it, with the measured absorption.
2. Each preset's score is the median over its puzzles, both shapes pooled.
   - Also report each shape's median.
   - If the two shape medians differ by more than 30 points, say so in the pilot report. That is a
     first sign of a structure effect.
3. Pick the preset whose median is **closest to 37.5%, among those in 25–50%**.
4. If none is in the band, take the closest one that lies within 15–60%.
5. Otherwise, pilot one extra rung before the main run.
   - **Make the extra rung concrete now (OURS).** Friday builds and freezes it **before** the pilot (for
     example `l10`, harder than slot C by procedure, per D-62), as its own disjoint set of 10 puzzles
     (5 base × 2).
   - **Slot C is the hardest preset already buildable** (Jarvis's instruction to Friday).
   - **If the extra rung is needed,** it runs as one mini-wave of 10 puzzles × (Opus, Sonnet, Haiku ×10).
     That is about $2 central and $5 high, with a separate small cap and the user's go, because the
     pilot's own $30 is spent first.
   - **At most one extra rung.** If even that is above 60%, proceed with the hardest preset and say so:
     Haiku is near the ceiling, so the equal-money vote will "match" Opus easily, and H1 gets less
     informative. Difficulty is still reported as a measured dial (D-21). No further chasing, because
     the 10-19 credit doesn't allow it.
6. **Tie-break (K2).** If two presets are equally close to 37.5% (to the nearest 0.1 point), choose the
   one with **fewer rule kinds**. If that also ties, choose the one with the **shorter mean prompt**.
   - Why: the simpler, cheaper preset adds fewer confounds and leaves more budget.
   - This replaces D-48 row 18's digit tie-break ("goes to d4s"). Jarvis treats it as covered by D-62
     (the team's judgement on difficulty); it is stated here so the spec can carry it.

The pilot may change only the preset, the ladder of extras, and the answer-only switch (D-36(5)). Never
the hypotheses, contrasts or margins.

## Fairness check (D-67(2); exploratory, never changes the preset rule)

*Karen, 2026-10-11. Fixed before any pilot data. It reports; it does not decide. The freeze (D-67(1))
stands whatever it shows. Background: Edith's verdict `ops/reviews/2026-10-11-fair-test-tuning-verdict.md`
and `research/tuning-fairness.md` §4.*

**Question.** Some rule kinds went in because the free Haiku reads showed Haiku slipping at such steps.
Are those kinds hard for Haiku in particular, or hard for every model? If they are Haiku-specific, the
family is tilted against the Haiku vote.

**Which kinds count as "targeted"** (from the tuning history, `research/paper-notes/tuning-disclosure.md`;
**Friday confirmed the split from his commit history**). A step's group is set by its own rule kind.
- **Targeted (T):** kinds added or turned up *after* a free read showed Haiku slipping at that kind of
  step:
  - the look-again rules `repick2` and `repeat_fixed`. They were added after read 4's repeat slips, and
    listed twice in the kind draw from l15 on. After read 5 the repeat went from ×3 to ×5;
  - the in-turn `sweep`, added after read 5.
- **Other (G):** kinds set before Haiku had slipped on them, and not turned up in the frozen presets:
  - `two_clause` (from read 1) and `compare_move` (from read 2);
  - `avg_donors`, `rank_move` and `count_move`. These were added after read 3 as step-heavy kinds from
    the ideas list, before any slip data on them (`research/ledger-difficulty-levers.md`).
  - **A borderline case: `avg_donors`.** It then slipped in reads 4–6 (4 of the 9 chain misses). After
    read 4 it got double weight in l12 and l13, but both were retired under B1. In l14–l17 it is one
    draw in 7–10, like the other G kinds. The sensitivity split counts it as targeted.
- **The house rule is targeted but puzzle-wide.** It was added after read 4, and after read 5 it went
  from acting on 5–8 steps to 9–12. Every step in every frozen preset checks it, so it can't be a step
  kind. It is analysed on its own (the house index below).
- **Puzzle-wide changes outside the split** (noted in the appendix):
  - **decoys:** first in l11 for read 4, then 6 in l15 and 8 in l16 and l17;
  - **the round-number base:** with l14 and l15 after read 4 (D-62, B1).
- **Sensitivity split:** T+ (everything added from read 4 on: T plus `avg_donors`, `rank_move`,
  `count_move`) against G− (`two_clause`, `compare_move`). There are few G− steps (l17 has none), so this
  split is mainly for the main run.
- **Mix of steps** (from the kind lists; the real counts come from the frozen sets). T's share of rule
  draws is about:
  - 2 in 7 in l14;
  - 4 in 8 in l15;
  - 6 in 10 in l16;
  - 7 in 9 in l17.

  Across the pilot's slots (A l16 ×20, B l15 ×10, C l14 ×10), T and G steps come out roughly even. The
  imbalance lies **between presets**, so the index is stratified by preset (below).

**What is measured.** D-31's step lines write all the balances after each step, so this is free: no extra
calls.
1. **Slips: the local-slip table (Friday's grader; primary).**
   - Each step's rule, plus the house rule, is applied to **the model's own previous balances**:
     - in a 24×1 piece, the given start;
     - in a 1×24 chain, the model's own line for the step before.
   - A **slip** is a step whose written balances differ from that result. A wrong state carried forward
     is not counted again, so every chain step counts once.
   - **Sensitivity check:** the first-slip view, which counts only the steps up to and including a
     chain's first slip. After that the state is the model's own, and errors may breed errors (Sinha
     et al., `research/ledger-difficulty-levers.md` point 6).
2. **Per rule kind, per model** (Haiku-medium, Sonnet-medium, Opus-medium): slips ÷ steps checked, with
   the counts.
   - **Who gets the blame.** The grader works from the model's previous balances P, with R = the rule
     applied to P, and H = the house rule applied to R. It then checks, in order:
     1. the written balances equal R, but the house rule should have acted: **house rule missed**;
     2. the house rule should not have acted, but the written balances equal R with the house move
        forced: **house rule misapplied**;
     3. the written balances equal the step's decoy twin (with its house rule): **decoy confusion**;
     4. anything else: a slip of the step's own kind.
   - Cases 1 and 2 are **house slips**. They count toward the house index, not toward the step's kind.
     Case 3 counts toward the step's kind and also gets its own row.
   - A step that has both a kind slip and a house slip falls under case 4, so house slips are slightly
     undercounted. That is conservative.
3. **Haiku's repeat share** (it has 10 tries per puzzle).
   - **Whole answers:** for each puzzle with at least 2 wrong tries, the share of *pairs* of wrong tries
     that give the same final answer (pairwise agreement). Pooled over puzzles, with the share taken by
     the most common wrong answer beside it. Per preset and per shape.
   - **Per kind:** the same pairwise agreement on the slip itself.
     - Two wrong chain tries agree if they first slip at the same step with the same written balances.
     - Two wrong piece answers agree if they give the same wrong balances on the same piece.
     - Reported for T and G, and per kind.
   - The free reads can't give this: their repeat tries were byte-identical. The API's tries can;
     smoke-2's were not identical.
4. **Unplaceable tries** are counted and left out of 1–3. These are tries with missing or unreadable step
   lines, or with every step right but a wrong `Answer` line.

**The flag** (thresholds OURS, for Edith's review):
- For each model m: **RR_m = T-slip rate ÷ G-slip rate.**
  - It is combined across presets with **Mantel–Haenszel weights** (the standard rate-ratio form, with
    the preset as the stratum).
  - **Why:** T's share of steps rises with the preset (from 2 in 7 to 7 in 9), and so does difficulty.
    A plain pooled ratio would partly measure the preset rather than the kind.
  - If a model has zero slips in a group overall, add 0.5 to that model's slip counts in every stratum.
    The correction pulls ratios towards 1, so it is conservative (Edith).
- **Also reported** (Edith's review): RR for Sonnet, and the **absolute** slip-rate differences
  (T − G, per model), because ratios are unstable when slips are few.
- **Targeting index TI = RR_Haiku ÷ RR_Opus.**
  - TI = 1: the T kinds are harder than the G kinds by the same factor for Opus as for Haiku.
  - TI = 2: the T kinds are twice as Haiku-specific.
- **House index TI_house** (pinned with Edith, `ops/reviews/2026-10-11-power-cutorder-house-T.md` §4; the split denominators below confirmed by her on 2026-10-11):
  - RR_house,m = (house rule missed ÷ steps where the house rule should fire) ÷ (model m's G-slip rate).
    Whether the house rule should fire is judged on the model's own previous balances (for first-slip,
    the key's path, which is the same up to the first slip). Mantel–Haenszel by preset, as for RR.
  - TI_house = RR_house,Haiku ÷ RR_house,Opus.
  - "House rule misapplied" can only happen where the house rule should *not* fire. So it gets its own
    rate (÷ the steps where it should not fire), which is reported beside TI_house but is not a flag
    index. That keeps each numerator over the steps that could produce it.
  Every step checks the house rule.
- **Interval:** a 90% bootstrap over base puzzles, 2,000 resamples, with the seed fixed in the code.
  - It is **stratified by preset**: resample base puzzles within each preset, so every replicate keeps the
    preset mix and the T/G balance.
  - Both shapes and all tries of a base puzzle are resampled together.
  - Report the share of replicates that needed the 0.5 correction. If it is above 10%, label the interval
    **unstable**.
  - Per-preset values and the T and G step counts per model are reported alongside, so the imbalance is
    visible.
- **Flag K** (slips): TI or TI_house ≥ 2, with the interval's lower end above 1. That is two chances to
  flag, which is fine for an exploratory flag, so **both values are always reported**, flagged or not.
- **Flag R** (repeats): Haiku's same-slip agreement on T steps is at least twice its agreement on G steps,
  with at least 10 pairs in each.
- **Enough data?**
  - Flag K is assessed only if Haiku has at least 20 slips (at least 5 in each group), and the comparison
    model at least 10, with **at least 5 in each group** (Edith's rule).
  - Each group must also have at least 100 steps checked for the comparison model. This guards the
    smaller group against the imbalance. The same rule applies to the house index, with house slips as
    one group.
  - If Opus falls short, pool Opus and Sonnet, and label it as pooled.
  - If that still falls short, the result is **"not assessable at pilot scale"**. That is reported as the
    result, and the same check runs on the main run.
- **Likely outcome (OURS).**
  - Haiku should give plenty of slips: about 400 tries.
  - Opus at medium effort may slip only a handful of times in 40–50 tries, so "not assessable" is the most
    likely cross-model result.
  - The Haiku side (the per-kind profile and the repeat share) will still say something.
  - **The decisive version is the main run.** D-67(2)'s direct test uses the same definitions:
    Opus-medium's 160 answers (Opus-low as a second comparison) against Haiku-medium's 6,400 tries.

**What a flag does.** Nothing to the design. The preset rule (D-36(4)), the kinds and the puzzles stay
frozen. A flag:
- goes into the pilot report and to the user with the main-run go;
- switches the paper's limitations sentence to its measured version
  (`research/paper-notes/tuning-disclosure.md` §1);
- moves the main-run per-kind test from the appendix into the results, beside H1 and H1b.

Anything more, such as dropping a kind, would be a declared deviation, and that is the user's call.

**Also reported for every pilot preset (D-67(2)):**
- whole-answer accuracy for Haiku (the per-puzzle median used by the preset rule), Opus and Sonnet, side
  by side;
- Haiku's 10-try vote against Opus's single try, as a **pilot-scale preview only**. It is not H1: the k is
  wrong, and the puzzles are practice ones. It shows whether the vote-vs-Opus picture differs by preset,
  l14 (the least tuned) included.

**Preview from the free reads** (Haiku only, reads 4–6, 16 slips, so n is tiny; recomputed from Friday's
keys and replies):
- `avg_donors` 6;
- the repeat and look-again kinds 9;
- `count_move` 1;
- `sweep`, `rank_move`, `two_clause` and `compare_move` 0.

Without Opus this can't tell Haiku-specific from generally hard. That is what the check is for.

**Who builds it.** Friday's grader, in his lane, with no model calls. He is already adding:
- the rule kind of each wrong 24×1 piece;
- the local-slip table, where each rule is applied to the model's own previous balances.

Still needed:
- the four-case blame check above, which uses the generator's rule, house-rule and decoy functions;
- the Mantel–Haenszel index;
- the stratified bootstrap.

I can write the analysis spec as a script plan in `research/` if Jarvis wants.

**After the pilot** (feeding the main-run go):
- re-lock the budget with the measured tokens;
- set the main run's `max_tokens` at about 1.5× each setup's largest pilot output;
- decide whether the ArXivMath check fits (`research/arxivmath-brief.md`).

**Still to fill in:**
- ~~the three preset names and slots~~ (done: l16, l15, l14, with l17 spare);
- the set ids and hashes (Friday's frozen sets), including the check and S3 sets, with disjointness
  verified;
- `max_tokens` and the cost table re-run on Friday's measured reply lengths (K3; Edith recomputes the
  reservations in the clearance);
- Edith's clearance;
- the user's go.


## The ladder pilot for prereg-lock-2 (D-86, ruled 2026-10-12; text for the lock)

*Karen, 2026-10-12. Edith's conditions are built in, with her K2-1 to K2-3
(`ops/reviews/2026-10-12-lock2-prep-karen-r1.md`); her verdict on the draft is CLEAN. Ruled by the user as D-86,
with the ladder widened to N ∈ {4, 6, 8, 12, 16} for the accuracy-versus-length curve. It is binding once
lock-2 is cut. The deviation note's wording is Edith's (`ops/reviews/2026-10-12-deviation-note-1.md`), word
for word. Background: `research/pilot-floor-options.md`.*

**Why.** Pilot-1 (24 steps) put Haiku-medium's whole-answer score at 0–2% at every preset, which is tier 3
of D-36(4): returned to the user. Shortening the chain is the one dial changed. Everything else stays as
locked: rule kinds (l14), wording, D-76 scoring, the five tests, the margin, the k rule and the fairness
check. Pilot-1's Opus and Sonnet numbers were never opened.

**The sets** (frozen in lock-2, all disjoint from every existing set):
- **Ladder sets (D-87):** l14 rules at **n = 4, 6, 8, 12 and 16 steps**, each **20 base puzzles × 2 shapes** (n×1 and 1×n), so 40 puzzles per length and 200 in all.
- **Main and ext40 sets at every candidate n,** so the amendment only has to name n. That is exactly:
  - for each n = 4, 6, 8, 12 and 16, a main set of 80 base × 2 shapes and an ext40 set of 40 base × 2 shapes;
  - all frozen in lock-2 and disjoint (the ext40 set's 1×n items only, if D-72 fires).
- **Already fixed by the locked design at any n** (none of this is a new choice):
  - E3 makes n step calls per chain;
  - the k script recomputes k (D-33, D-70) at the chosen n, from the ladder's and main run's tokens;
  - the fairness check uses l14's T kinds (`repick2`, `repeat_fixed`) and G kinds (`two_clause`,
    `compare_move`, `avg_donors`, `rank_move`, `count_move`).

**Calls per ladder puzzle** (Batch, effort medium, with B7's `max_tokens`: Haiku 48K, Opus and Sonnet 32K).
D-87 adds Sonnet.
Pilot-1's passing Console check already opens the guard's Batch gate, so no new bill check is needed:
- Haiku-medium ×10;
- Opus-medium ×1, **sealed**;
- Sonnet-medium ×1, **sealed** (D-87; it is used for the curve only, never for a decision).

**The ladder rule** (Haiku-medium only):
1. For each puzzle, Haiku's single-try accuracy is the share of its 10 tries that are right under the
   official score:
   - at n×1, every piece right;
   - at 1×n, all n step lines right, with the Answer line equal to line n (D-76).
2. Each n is scored by the median over its 40 puzzles, both shapes pooled, with the shape medians also
   reported.
3. Pick the n (from 4, 6, 8, 12, 16) whose median is **closest to 37.5%, among those in 25–50%**. **A tie goes to fewer steps.**
4. If no n is in 25–50%, take the closest n within 15–60%. **A tie again goes to fewer steps.**
5. If no n is within 15–60%, return to the user. There are no further rungs.
6. The pick is committed, with input and trace hashes, **before** any Opus or Sonnet ladder answer is opened.

**After the pick:**
- Once the pick is committed (with hashes), the Opus and Sonnet ladder answers at **every** n are opened,
  for the curve below.
- **Only the Opus answers at the chosen n feed a decision:** D-72's p_opus (1×n only) and the
  near-ceiling flag.
- Opus at the other n, and Sonnet at every n, are descriptive only.
- Then the post-pilot steps of `research/d72-d73-lock-spec.md` run at the chosen n.

**Cost: the binding figure for the ladder and the cap** (D-87; Friday's method, reproduced by Karen).
Per call, the output is 1K + the measured 24-step output × n/24 (Haiku 6.9K, Opus 7.0K, Sonnet 6.6K). The
input is the actual l14n{n} prompt characters ÷ 3.4. The high case is 1.5× the output. Batch prices were
re-checked on 2026-10-12, unchanged.

| n | Ladder rung (40 puzzles; Haiku ×10 + Opus ×1 + Sonnet ×1), central / high | Main run, full plan, all in (central / high) | Musts only |
|---|---|---|---|
| 4 | $1.61 / $2.36 | $58 / $83 | $46 / $63 |
| 6 | $2.03 / $2.98 | $63 / $90 | $50 / $68 |
| 8 | $2.45 / $3.60 | $68 / $97 | $54 / $73 |
| 12 | $3.29 / $4.84 | $77 / $111 | $61 / $84 |
| 16 | $4.13 / $6.08 | $87 / $124 | $69 / $95 |

- **The ladder in total: $13.5 central / $19.9 high,** about 2,400 Batch calls. Opus is about 58% of the
  cost.
- **The hard cap is $30** (D-89), enforced by the spend guard. The guard books each call at its full
  max_tokens (about $125 worst case over 2,400 calls), so it sends in waves under the cap. Edith's
  clearance fixes the waves from the frozen sets. Runs need the user's go (D-88): only after prereg-lock-2
  is cut and Zenodo v2 is posted.
- The main-run figures include the $11.8 already spent and the ladder. **No cut is needed at any n**, and
  D-74's add-40 fits at every n.
- **Why my earlier $10.1 / $11.9 was lower:** I scaled output in proportion to n, with no fixed part. At
  short n that underestimates a fixed overhead per call (Friday's 1K floor). I also took Opus at about
  5.7K output, against the measured 7.0K, and used a smaller high-case factor (1.25 on thinking, against
  1.5 on output). Friday's basis is measured per model and more conservative, so it binds.
- **k at the main run** comes from the main run's costs (D-33). This projection gives k ≈ 40 if Haiku's
  output equals Opus's (Friday's inputs), against about 23 if Haiku thinks 2× Opus. The ladder measures
  both at l14.

**Expected:** at l14's per-piece rate of about 88% (and about 85% across presets), single tries come to
roughly 52–60% at n = 4, 38–46% at 6, 27–36% at 8, 14–22% at 12 and 7–13% at 16. So 6 or 8 is the
likely pick, and 12 and 16 chart the curve.

### The ceiling: do short puzzles make Opus and Sonnet always right? (OURS; pre-registered reporting, not a test change)

- **Not necessarily.** Opus's per-step accuracy is unknown (sealed). At 98% per step a 6-step puzzle is
  right about 89% of the time; at 99% about 94%; only near 99.5% or above does it approach 97%. Sonnet is
  likely similar or a little lower.
- **What near-ceiling does to the tests** (`research/models/ceiling_power.py`; k = 24, 80 base,
  Holm's strictest step). The verdict is then decided by how good the vote is, which depends on whether
  Haiku's errors are scattered or repeated. The pilot measures that through the repeat share:

  | World | Opus 95% | Opus 99% | Opus 100% |
  |---|---|---|---|
  | Scattered errors | the vote is about 100%, so non-inferior always | non-inferior always | non-inferior always |
  | Moderate spread, Haiku 37.5% (vote about 92%) | 46% non-inferior / 54% inconclusive | 18 / 82 | 14 / 86 |
  | Repeated errors or a wide spread (vote about 68–79%) | mostly **worse by more than the margin** | | |

- **The catch is the margin.** At the ceiling, a "match" within 10 points can hide a vote with several
  times Opus's error rate (×1.5 to ×8 in the moderate-spread world).
- **The ceiling flag** (Edith's wording):
  - The D-72 re-run uses the measured p_opus at the chosen n. It already does.
  - **Near-ceiling flag:** if Opus-medium's ladder accuracy at the chosen n is at least 95% (pooled), tests
    1–2 are labelled near ceiling, and the paper reports the **error-rate ratio** (Haiku-vote errors ÷
    Opus errors) with its interval next to the non-inferiority result.
  - A bias-table row is added (`research/paper-notes/tuning-disclosure.md`).
  - The 5-point secondary view and error ratios beside every verdict (mock-review fix 3) also stand.
- Test 5 (Opus-low vs Sonnet) may be near the ceiling on both sides; its error ratio is reported too.

**Fixtures:** `research/fixtures/sim-main-n/`: 720 of 720 pass on main's parser at n = 4, 6, 8, 12 and 16.


### Pre-registered descriptive plan for the accuracy-versus-length curve (D-87; fixed before any ladder data)

*Karen, 2026-10-12. Descriptive only. **No confirmatory test is run on the curve.** The five confirmatory
tests (D-68) run only in the main run, at the chosen n, unchanged.*

**1. What is plotted** (x = steps n ∈ {4, 6, 8, 12, 16}; y = accuracy, 0–100%):
- **Whole-answer accuracy** under the official score (D-76: every piece right at n×1; all n step lines right,
  with the Answer line equal to line n, at 1×n) for:
  - Haiku-medium's **single try**: per length, the mean over puzzles of each puzzle's share of its 10 tries
    that are right, with the **median** (the pick statistic) marked as well;
  - Opus-medium and Sonnet-medium: the share right (one answer per puzzle).
- **Three panels:** n×1, 1×n, and both shapes pooled (each base puzzle weighted equally).
- **Per-step reliability, a secondary panel:**
  - per-piece accuracy at n×1;
  - the local-slip per-step accuracy at 1×n (each step judged from the model's own previous balances,
    as in the fairness check).
- **Also reported per model and n:**
  - format compliance at 1×n (D-76 condition 3; flagged above about 5%);
  - the number of truncations (`max_tokens`);
  - **Haiku's plurality vote over its 10 tries** (vote@10), labelled "not cost-matched" (the cost-matched
    k is a main-run quantity).

**2. Intervals** (all 95%, two-sided, unadjusted, descriptive):
- **Haiku:** a cluster bootstrap over base puzzles. Percentile, 2,000 resamples, seed 20261012. All tries,
  and both shapes for the pooled panel, are resampled together.
- **Opus and Sonnet:** a Wilson interval for each shape. The pooled panel uses the same cluster bootstrap
  as Haiku.
- **Per-step panels:** the same cluster bootstrap.

**3. The p^n reference line** (shown, not fitted per length):
- For each model, estimate one per-step accuracy q: the share of all n×1 pieces right, pooled over the five
  lengths, with a bootstrap interval as in 2.
- Overlay **q^n** as a dashed line, with its band from the bootstrap of q, on the whole-answer panels.
- Report the ratio of observed to q^n per n as a description. A ratio below 1 at 1×n would fit the
  "errors breed errors" account (Sinha et al.), but it is not tested.
- One parameter per model, and nothing is tuned to the chain data.

**4. The 24-step pilot point** (pilot-1, measured before lock-2, on a different rule mix):
- **Haiku:** at n = 24, a hollow marker labelled "pilot-1, presets l14–l16, before lock-2". It is the
  pooled pilot-1 whole-answer mean for those presets, with the cluster-bootstrap interval.
- **A comparable point:** pilot-1's **l14-only** subset (slot C, 5 base × 2 shapes), shown as a second
  hollow marker with its wider interval, since it uses the same rule kinds.
- **Opus and Sonnet pilot-1 points:** opened only after lock-2 is cut, shown the same way and labelled.
- **None of these points enters the q estimate.** The q^n line is extended to n = 24 only as a dotted
  extrapolation, for comparison.
- The plot notes that pilot-1 differs in rule mix, sets and timing.

**5. What is explicitly not claimed:**
- no test of differences between models or lengths on the curve (no p-values; intervals only);
- no claim beyond n = 16, except the labelled descriptive 24-step marker;
- no causal claim about why accuracy falls with n;
- no change to the Holm family or the margin.

The curve's sample sizes (40 puzzles per length; Haiku ×10; Opus and Sonnet ×1) are for description, and
the Opus and Sonnet intervals are wide: about 12–15 points below and 4–10 above.

**6. How the Opus points are used:**
- **Only the chosen n's Opus point feeds decisions:**
  - D-72's power re-run uses p_opus = Opus-medium's 1×n accuracy at the chosen n;
  - the **near-ceiling flag** uses Opus-medium's pooled whole-answer accuracy at the chosen n (at least
    95% labels tests 1–2 near ceiling, with the error-rate ratio reported).
- Opus at other n, and Sonnet at every n, never feed a decision.
- The main run's own Opus, Sonnet and Haiku accuracies at the chosen n (fresh sets) are added to the plot
  as separate markers, labelled "main run".

**Implementation choices where the text above was silent** (Friday's `harness/analysis/curve.py` at
a8f0acd, checked by Karen against this plan; Edith reviews the code):
1. A planned try with no final record counts as wrong, and is reported as missing (as deployed).
2. The bootstrap resamples base puzzles **within their set**: within each length's set for q, and within
   each preset for the pilot-1 points. Every set keeps its size, and each statistic has its own seed
   derived from 20261012.
3. **Per step at 1×n** uses `scoring.local_steps`.
   - A try whose step lines can't be placed is left out, and counted as unplaceable.
   - A try whose steps are all right but whose Answer line is not counts all n steps right, because the
     Answer line isn't a step.
4. **Per piece at n×1:** a missing or unanswered try scores 0 pieces, so q is an as-deployed rate.
5. **Haiku's pooled median** is over all 40 puzzles (both shapes as separate puzzles). That is exactly the
   D-36(4) pick statistic. The pooled **mean** weights each base puzzle equally (the mean of its two
   shapes).
6. **vote@10 and the per-step panels** also get cluster-bootstrap intervals.

The main-run markers are added later, from the main run's data. Pilot-1's Opus and Sonnet points are
computed only after the tag prereg-lock-2 exists. The Opus and Sonnet ladder records are opened only
with a committed, binding, Haiku-made pick.
