# Reporting definitions for the main run (six items), pinned before any main-run result is opened

*Karen (Opus 5.5), 2026-10-12. This is the dated note Edith asked for
(`ops/reviews/2026-10-12-reporting-gaps.md`). Friday found the gaps while building `main_analysis.py`. No
model calls, and no main-run data exists or has been opened.*

*The route:*
1. *Edith reviews this note.*
2. *Jarvis puts the one-line summary below to the user for a yes.*
3. *The note's commit is timestamped together with the converter's hash (D-93).*
4. *The paper says: "reporting definitions fixed after prereg-lock-3 and before any main-run result was
   opened".*

**Status (2026-10-12):** Edith reviewed it: **CLEAN, all three amendments accepted** (r2 section of
`ops/reviews/2026-10-12-reporting-gaps.md`, f0bf518). Next: the user's yes, via Jarvis.

**One-line summary for the user.** Six secondary or descriptive numbers get exact definitions before we
look at any result:
- the error-rate ratio (how many times more often the cheap setup is wrong);
- a stricter 5-point reading;
- the reworded-prompt comparison;
- the repeated-slip flag;
- the "too easy" flag;
- the real-time timing report.

None of them changes the five main tests.

**What every item leaves alone.** No item changes the five confirmatory tests: their k, the scores, the
10-point margin, the paired BCa bootstrap, Holm's correction or the three views (D-68 F2, F3). Every
statistic is at N = 6, uses the official score (D-76 with D-90's repeat rule) and works from the same
per-base scores the code already produces.

**Edith's proposals are adopted. I amend three points, each marked AMENDED with the reason:**
- in item 1, how resamples with zero Opus errors are handled;
- in item 4, how the pieces shape is counted;
- in item 6, which real-time calls are used.

---

## 1. The error-rate ratio

**Fills:**
- spec, Amendment 1 item 6: "the error-rate ratio (Haiku-vote errors ÷ Opus errors), with its interval";
- `research/pilot-plan-ledger.md`, ceiling section: "error ratios beside every verdict … Test 5 … its
  error ratio is reported too";
- the spec's bias table, the 10-point-margin row.

**Which tests.** Each of the five tests that ran (k ≥ 1), in the as_deployed view.

**Bases.** Exactly the base puzzles in that test's paired differences, written n.

**Per-base scores.** In points, the same ones the test uses:
- challenger c_b:
  - tests 1–3: `vote_scores` at the test's k;
  - test 4: `e3_arm_scores`;
  - test 5: `single_scores("opus-low")`;
- comparator o_b: `single_scores` of Opus-medium (tests 1, 2 and 4) or of Sonnet-medium (tests 3 and 5).

**Errors.**
- E_ch = Σ_b (100 − c_b) / 100. This is the expected number of wrong answers, and an integer for a
  single-try arm.
- E_cmp = Σ_b (100 − o_b) / 100. This is always an integer, because both comparators are single tries.
- Error rates: e = 100 · E / n, in points.

**Ratio.** R = E_ch ÷ E_cmp. **Always report E_ch, E_cmp and n beside R.**

**Interval.** A 95% percentile interval from a paired bootstrap over base puzzles.
- B = 10,000.
- RNG: `random.Random(derive_seed(20261011, f"{test}:error_ratio"))`.
- Each replicate draws n bases with replacement from the sorted base list (`rng.choices`). It recomputes
  E_ch* and E_cmp* on the drawn bases, and R* = E_ch* ÷ E_cmp*.
- If E_cmp* = 0 and E_ch* > 0, R* = +∞, and **the replicate is kept**.
- If E_ch* = E_cmp* = 0, R* is undefined. The replicate is dropped and counted.
- The ends, over the k kept values sorted (the order-statistic rule of `bootstrap.py`):
  lower = v[floor(0.025·k)] and upper = v[ceil(0.975·k) − 1].
- An end equal to +∞ is reported as "unbounded".
- The share of replicates with E_cmp* = 0 is reported.

**If the comparator has 0 errors in the data (E_cmp = 0).** R is "not defined", and no continuity
correction is used. Report instead:
1. "comparator: 0 errors in n";
2. the comparator's upper bound on its error rate: the upper end of `curve.wilson(0, n)` (the two-sided
   95% Wilson interval, z = 1.96);
3. the challenger's error rate e_ch, with its 95% percentile interval from the same replicates.

**AMENDED (Edith proposed dropping undefined replicates, with "not assessable" above 10%).** A replicate
where the comparator has no errors but the challenger does is a real outcome: the ratio is very large. So
it counts as +∞ instead of being dropped.
- Dropping those replicates would remove exactly the cases where Opus looks best. That would pull the
  interval down, in the vote's favour.
- Keeping them keeps the **lower** end valid. The lower end is the one the near-ceiling reading needs: "the
  vote makes at least X times Opus's errors".
- An unbounded upper end is then shown honestly.
- Example: if Opus has 1 error in 80, about 37% of replicates have none. Edith's rule would report "not
  assessable"; this rule still gives a lower end.

## 2. The 5-point secondary view

**Fills:**
- the spec's bias table: "a 5-point secondary view (Karen's power simulation)";
- `research/mock-review-fixes.md`, Fix 3 item 3;
- `research/pilot-plan-ledger.md`, ceiling section: "the 5-point secondary view … beside every verdict".

**Definition.** `bootstrap.run_family` over **the same per-base differences** as the confirmatory family:
- official score, as_deployed, the same k, N = 6;
- the same B = 10,000 and the same seeds (base 20261011, `derive_seed(seed, test)` per test), so each
  test's bootstrap distribution is identical to the confirmatory one;
- α = 0.025, one-sided, with Holm across the five;
- only **margin = −5.0**, in the code's sign convention.

A test that didn't run keeps its Holm place with p = 1, as in `five_tests._family`.

**Reported:** for each test, p, declared, and the three-way reading at margin 5, labelled "secondary,
5-point margin". It sits beside the 10-point verdict and never replaces it. As_deployed only.

## 3. The D-42 (a) robustness table (hv against hm)

**Fills:** D-42 (a) in spec §RULED ("reported as robustness, outside the confirmatory family"), and D-91.

**Arms:**
- **hv:** Haiku-medium ×10 under the variant wording;
- **hm(1–10):** the main run's Haiku-medium samples 1–10, by sample index;
- both on the 40 pinned puzzles: base 000–019 of `main-ledger-l14n6-v1`, both shapes (D-91).

**Per puzzle:** the share right among its **10** designed tries, under the official score, as_deployed.
Refused, truncated, unparseable or missing tries count as wrong, and the denominator stays 10.

**Per shape** (20 puzzles each) **and pooled** (40): the mean over puzzles, for hv and for hm(1–10), and
the difference **hv − hm**.

**Interval.** A 95% percentile cluster bootstrap over the 20 base puzzles:
- `curve.cluster_bootstrap`, 2,000 draws, seed 20261012;
- names `"d42:6x1"`, `"d42:1x6"` and `"d42:pooled"`;
- the statistic is the mean over the drawn bases of hv_b − hm_b;
- for the pooled value, a drawn base brings both its shapes.

**Also reported:** format compliance per arm and shape (answered tries in an ok format ÷ answered tries),
and the refusal and truncation counts.

**No test, no threshold, no verdict.** This adopts Friday's proposal as Edith accepted it.

## 4. Flag R: its inputs

**Fills:**
- `research/pilot-plan-ledger.md`, Fairness check, Flag R: "Haiku's same-slip agreement on T steps is at
  least twice its agreement on G steps, with at least 10 pairs in each";
- `harness/analysis/fairness.flag_r`, which is already coded;
- the spec's slip-analysis list: "Haiku's wrong-answer repeat share".

**Tries:**
- Haiku-medium's main-run samples, all 40 per puzzle, both shapes;
- answered and placeable under `scoring.local_steps` (the official parse, D-90's rule);
- unplaceable tries are left out and counted, as locked.

**Slip events:**
- **1×6:** a try's **first** slipped step only (the first row with `slipped` true). Up to that step the
  try's input equals the key's, so two tries that slip at the same step had the same input. Later steps
  have the try's own inputs and are not used.
- **6×1:** **every** slipped piece. Each piece starts from its printed start, so every piece's slip had the
  key's input.
- **Which slips count:** only blames "kind" or "decoy_confusion", the slips flag K counts. House-rule
  blames are left out, because the house rule is analysed puzzle-wide, as locked. At 1×6, a try whose
  first slip is a house blame gives no event.
- A step's class is T or G by its own kind (`scoring._step_class`). There are no "other" kinds at l14.

**Pairs.** Within one cell (base puzzle, shape, sequence, step): every unordered pair of slip events from
two different tries. That is C(m, 2) for m events in the cell. A pair is a T pair or a G pair by the
step's class.

**Agreement.** The two events wrote **identical balances** at that step (`written`).

**Inputs to the flag.**
- pairs_t, agree_t, pairs_g and agree_g are the sums over all cells and both shapes.
- The flag is `fairness.flag_r(agree_t, pairs_t, agree_g, pairs_g, min_pairs=10)`, decided on these point
  counts.
- For information: agreement_T and agreement_G, per shape and pooled, with a 90% percentile bootstrap over
  base puzzles (B = 2,000, seed `derive_seed(20261012, "flag_r")`; a drawn base brings both shapes and all
  tries).

**AMENDED (Edith proposed the first slip at both shapes).** At 6×1 the pieces are independent, so a
"first" slip would be first by sequence number only. That would discard comparable slips for no reason.
At 1×6, "first" is needed for the reason above.

**Consistent with the repeat share.** Both use the same unit, unordered pairs of one puzzle's tries scored
as identical or not, which is the unit of D-72's wrong-pair agreement (69 of 360 at the ladder).
- **The descriptive repeat share in the slip report is pinned with it:** the main-run version of the D-72
  quantity. That is unordered pairs of **wrong** Haiku-medium tries within one base and shape that have an
  identical vote key (`scoring.vote_key`, official score), summed over both shapes and reported per shape.
- The first-slip agreement above is its step-level counterpart, split T and G for the flag.

## 5. The low-information flag

**Fills:** the spec's bias table, the row "24×1 near the ceiling … a low-information flag if Haiku pieces
score above 60%". At N = 6 this is the 6×1 shape.

**Statistic:** Haiku-medium's single-try whole-answer accuracy at 6×1.
- The official score, as_deployed: each puzzle's share right among its 40 designed samples, with missing,
  refused, truncated and unparseable samples counted as wrong.
- The mean over the 80 base puzzles.

**It fires if that is strictly above 60.0%.**

**What it does:** test 1's verdict gets the label "low information: Haiku's single try is already above
60% at 6×1". Nothing else changes.

**Also reported, for information:**
- the median over puzzles (the locked "per-shape medians");
- per-piece accuracy: the share of a try's 6 pieces that are right (0 for an unparseable try), averaged
  over tries and then over puzzles.

This is Edith's proposal, adopted.

## 6. The real-time subset report

**Fills:**
- spec item 10 (the latency source);
- D-35 (the real-time subset: "latency plus the batch-vs-real-time check");
- D-92, the user's go: "the real-time subset" is a must of `main-l14n6-1`.

**The calls.** **The main run's own** real-time subset (`harness/pareto/main.py`, `RT_SETUPS`), at list
price with the same limits as Batch:
- the first 10 puzzles of `main-ledger-l14n6-v1` (base 000–004, both shapes);
- Haiku-medium ×5 (`rthm`), Sonnet-medium ×1 (`rtsm`) and Opus-medium ×1 (`rtom`) on each;
- 70 calls.

These calls never enter the five tests.

**Latency.** Per setup, from `latency_s` of the answered calls:
- n, the median, the quartiles (`statistics.quantiles(…, n=4, method="inclusive")`) and the maximum;
- for Haiku, per puzzle, the time to a 5-sample vote if the 5 calls run **at once** (the largest of the 5)
  and **one after another** (their sum), with the median of each over the 10 puzzles.

**Batch against real time, on the same 10 puzzles:**
- per setup, the official whole-answer accuracy (share right over tries), using Batch Haiku-medium samples
  1–5 only, and Sonnet-medium's and Opus-medium's single Batch calls;
- mean output tokens per call;
- the difference, real time − Batch.

**No test.** The note says n is small (50 Haiku, 10 Sonnet and 10 Opus calls), and that the timings come
from one machine on one day.

**AMENDED (Edith proposed the pilot's subset).** D-92 put a real-time subset into the main run itself, so
the report uses those calls, at N = 6. The pilot's 24-step real-time check (70 calls, $2.62) is still
reported in the pilot section, as before.

---

**Not pinned here, as Edith ruled:** the curve at N = 6. Friday takes it from the D-87 plan's definitions,
and Edith checks the citations in the converter review.

---

# Addendum A (2026-10-12, after the D-93 audit; before any main-run result is opened)

*Karen (Opus 5.5). Asked by Jarvis from the readiness checklist (`decisions/readiness-checklist.md`, b12f257). No model calls; no
main-run data exists or has been opened. The same route as items 1–6: Edith reviews, the user says yes, and the note is timestamped
with the driver's hash.*

**What every item here leaves alone (as before).** None of these items changes the five confirmatory tests: their k, the scores,
the 10-point margin, the BCa bootstrap, Holm or the three views. Every statistic is at N = 6 and uses the official score (D-76 with
D-90's rule) unless the item says otherwise.

**Shared conventions** (they apply to every item below unless the item names its own):
- **Bootstrap for descriptive intervals:** `curve.cluster_bootstrap`, which draws base puzzles with replacement and keeps all of a
  base's shapes, tries and arms together. 2,000 draws, base seed 20261012, a percentile 95% interval, and a name per statistic as
  given.
- **Tests and test-like rows:** the confirmatory machinery, `bootstrap.run_family`, with B = 10,000, base seed 20261011, a per-test
  `derive_seed`, margin −10 and Holm across the five.
- **"List cost" of a call** (item 9a) is the cost used everywhere below, unless an item says "Batch".

## A0. Two corrections to items 1 and 6

- **Item 1, the zero-error case, now uses exact intervals.** The comparator's bound is the upper end of the two-sided 95%
  **Clopper–Pearson** interval for 0 of n, as section 7b locks ("Exact binomial intervals remain for single-arm accuracies"), not
  Wilson. At n = 80 that is 1 − 0.025^(1/80) = 4.51%.
- **Item 6, latency, adds what mock-review Fix 7 locks:**
  - the **p95** latency per setup, beside the median, quartiles and maximum (computed with
    `statistics.quantiles(…, n=20, method="inclusive")[18]`);
  - the **Batch turnaround per wave** (submit to end), reported separately and not called latency.

## 7. The per-piece view at 6×1 (D-23: "reported prominently" as the reader view)

**Fills:**
- D-23: "Per piece: tasks right, cost per task, a vote taken piece by piece";
- D-39 item 3: "The per-piece (reader) view is reported prominently as secondary".

**Pieces.** Every 6×1 reply is read with `trace_parse.parse_pieces(reply, 6, 6)`. Piece i is **right** if `entries[i]` exists and
equals the key's piece i. A refused, truncated or missing try, or a missing or unreadable entry, makes that piece wrong. Readable
entries of a partly unreadable reply get credit (Addendum C, item 7: the locked `grade_24x1` `pieces_right`).

**Per-piece accuracy, for every arm:**
1. For each try: the share of its 6 pieces right.
2. For each puzzle: the mean over its **designed** tries (a missing try counts as 0 pieces right).
3. For the arm: the mean over the 80 base puzzles.
4. Interval: the shared cluster bootstrap, named `"per_piece:<arm>"`.

**The per-piece vote (Haiku-medium):**
- For each piece i of a puzzle, the vote is `votes.vote_accuracy_at_k` over the 40 samples' entries for piece i:
  - a missing or unparseable entry is a vote for nothing;
  - the D-33 tie rule applies;
  - **at the same equal-money k** as the whole-answer vote at 6×1: k_O for the Opus side, and k_S(6×1) for the Sonnet side (item 11).
- The puzzle's per-piece vote accuracy is the mean over its 6 pieces. The arm's figure is the mean over puzzles, with the shared
  cluster bootstrap named `"per_piece_vote:<k-name>"`.
- **Also the per-piece vote curve** for k = 1 to 40, computed the same way. This is the second "vote unit" of D-27's offline
  analyses.

**Cost per task** (one piece is one task): the arm's mean list cost per 6×1 puzzle (item 9b), divided by 6. For the vote at k,
that is k × the mean list cost per Haiku sample, divided by 6.

**Labels.** Reported as secondary and descriptive, beside the whole-answer results. No test.

## 8. The k-sensitivity set (D-33 items 5, 9 and 10; 7b's sign-flip check)

**Fills:**
- D-33 item 5: "the full 1 to 40 curve is reported (exploratory)";
- item 9: "the confirmatory result is also reported at k from the median cost ratio, k from the pilot, the interpolated k, and
  k − 2 to k + 2";
- item 10: "realised spend of both arms at k";
- section 7b: "The sign-flip permutation test is kept only as a sensitivity check for d = 0".

### 8a. The k values, per vote test (t1: Opus at 6×1; t2: Opus at 1×6; t3: Sonnet at 1×6)

All costs come from the **same cost-only rows** the confirmatory k uses: Haiku-medium, Opus-medium and Sonnet-medium; Batch only;
the real-time `rt*` calls left out (`kscript.k_table` cells, `include_realtime=False`). The rules are held to 1..min(40, samples
drawn) by `kscript.k_sensitivity`.
- **k from the median ratio:** the floor of the median over puzzles of (comparator cost on that puzzle ÷ that puzzle's mean Haiku
  sample cost). This is the cell's `median_ratio`.
- **k from the pilot.** It is NOT confirmatory: Amendment 1's "only" means "not confirmatory". It is the floor of the
  **ladder-l14n-1 cost ratio at n = 6**, computed now from costs only by `kscript.k_table` on that run's `compact_table.csv`
  (SHA-256 a4f60c97…), on the set `ladder-ledger-l14n6-v1`.

  | Comparator | Shape | Comparator $/puzzle | Haiku $/sample | Ratio | k from the pilot (held to 40) |
  |---|---|---|---|---|---|
  | Opus-medium | 1×6 (t2) | 0.0207948 | 0.00056534875 | 36.782 | **36** |
  | Opus-medium | 6×1 (t1) | 0.0247623 | 0.0005639375 | 43.910 | **40** (43 held to the cap) |
  | Sonnet-medium | 1×6 (t3) | 0.00731965 | 0.00056534875 | 12.947 | **12** |
  | Sonnet-medium | 6×1 (item 11) | 0.00802165 | 0.0005639375 | 14.224 | **14** |

  Every ladder call was Batch, so these ratios equal the list-price ratios. The driver passes these four ratios as `pilot_ratio`,
  keyed by (shape, "haiku-medium").
- **The interpolated k\*:** `kscript.k_star` on the same cost inputs as k (unrounded, held to min(40, samples drawn), no
  extrapolation). Each base's challenger score is `votes.interpolated_vote_accuracy(answers, correct, k*)` (official score,
  as_deployed, tie "random").
- **k − 2 … k + 2:** each test's own confirmatory k plus d, for d = −2 … +2.
  - A test whose k + d falls outside 1..min(40, samples drawn) is **held at the nearest allowed k** in that row, and labelled "held
    at the limit" (Addendum C, X8; Edith CLEAN r8).
  - Example: at k_O(6×1) = 40, test 1 stays at 40 in the k + 1 and k + 2 rows.

### 8b. The rows reported

**Each k-sensitivity row is the whole five-test family re-run:**
- `bootstrap.run_family` with the same B, seeds, margin and Holm;
- t1–t3's challenger scores are computed at that row's k, each test at its own value;
- t4 and t5 are unchanged.

**The rows are:**
- "median ratio";
- "pilot";
- "k*";
- "k−2" to "k+2", where "k+0" is the confirmatory result itself, repeated for reference.

**Reported per row:** t1–t3's k used, d, the 95% interval, p and the reading, labelled "k-sensitivity (not confirmatory)".

**Realised spend at k** (D-33 item 10), for each test and each row's k: `kscript.realised_spend(k, comparator list cost per
puzzle, Haiku list cost per sample, n_puzzles = 80)`. That gives the vote arm's $, the comparator's $ and their ratio, at list
price (item 9a).

**The 1–40 vote curve** (D-33 item 5), per shape:
- vote@k for k = 1 to min(40, samples drawn), from `votes.vote_curve` on each base's answers (official score, as_deployed, tie
  "random");
- the mean over bases, with the shared cluster bootstrap named `"vote_curve:<arm>:<shape>"`;
- the Monte-Carlo error and the tie-decided share where the estimator samples (D-33 items 7 and 8);
- at 6×1, also in the per-piece unit (item 7). Haiku-medium here; the exploratory arms in item 10.

**The sign-flip check for d = 0** (7b):
- for each test that ran, `bootstrap.sign_flip_p(diffs, null=0.0, nflips=100_000, seed=derive_seed(20261011, f"{test}:sign_flip"))`
  on that test's confirmatory per-base differences;
- this is a one-sided p for "the challenger is better than the comparator";
- unadjusted, labelled "sensitivity (superiority, d = 0)".

## 9. The cost outputs (D-48 row 22, D-33 items 12–13, D-27's offline analyses, mock-review Fix 7)

**Fills:**
- D-48 row 22: "Uncached list price, mean dollars per puzzle with every attempt counted …; the median is a sensitivity check; a
  cached view is a labelled offline re-pricing only";
- D-33 items 12 and 13;
- D-27's must "offline analyses (… escalate-to-Opus-on-disagreement, break-even price ratio)";
- Fix 7's cost per correct answer and cascade;
- `research/paper-notes/opus-vs-sonnet-exploratory.md`.

### 9a. List cost of one call

The list cost is `prices.cost(requested_model, Usage(input, output, cache_read, cache_write_5m, cache_write_1h from usage_raw),
batch=False)`, on the pinned price table (`PRICE_TABLE_DATE` 2026-10-12).
- **A refusal that rule B5 says is not billed costs $0.** That is a refusal with `refusal_billed_by_rule` false, or one marked
  `free_by_rule`.
- Every other call (answered, truncated, unparseable, billed refusal) costs what its usage says. No call is left out.
- The Batch cost (the logged `cost_usd`) is reported alongside, labelled "Batch".

### 9b. Dollars per puzzle (the headline cost)

**The cost of an arm on one puzzle:**
- **single-call arms:** that call's list cost;
- **E3:** the sum over all its step calls on the puzzle;
- **a Haiku vote at k:** k × the puzzle's mean list cost per sample over its drawn samples. This is the expected cost of a random
  k-subset, matching the vote@k estimator.

**Per arm and shape:** the **mean** over the 80 base puzzles, which is the headline, and the **median**, which is the sensitivity
check. Each has the shared cluster bootstrap, named `"cost_mean:<arm>:<shape>"` and `"cost_median:<arm>:<shape>"`.

### 9c. Cost per correct answer (CPC; Fix 7)

CPC = Σ_b cost_b ÷ Σ_b score_b / 100.
- This uses the item 9b costs and the official, as_deployed per-base scores. For a single-try arm that is total dollars ÷ right
  answers.
- For the vote, it is computed at each k from 1 to 40 and at each test's k.
- If no answer is right, it is "undefined (no correct answer)".
- Interval: the shared cluster bootstrap, named `"cpc:<arm>:<shape>"`.
- CPC equals C ÷ A as defined in the Opus-vs-Sonnet note, so the two are one definition.

### 9d. The break-even price ratio (D-27, offline; per shape and comparator)

1. **k_match** is the smallest k in 1..min(40, samples drawn) at which the Haiku-medium vote's mean accuracy (item 8 curve, point
   estimate) is **at least** the comparator's mean accuracy on the same bases. If no k reaches it, the result is "no break-even
   within 40 samples".
2. Let R_list be the D-33 cost ratio at list price: the comparator's mean list cost per puzzle ÷ Haiku's mean list cost per sample.
   Let ρ_list be the list price ratio per token, comparator ÷ Haiku: 40 for Opus and 20 for Sonnet, the same for input and output.
3. **The break-even price ratio is ρ\* = ρ_list × k_match ÷ R_list.** Read it as: at these token counts, Haiku's vote at
   comparator-level accuracy costs less than the comparator **as long as the comparator's per-token price is more than ρ\* times
   Haiku's**.
4. **Interval:** recompute k_match, R_list and ρ\* in each replicate of the shared cluster bootstrap, named
   `"break_even:<comparator>:<shape>"`.
   - A replicate with no k_match gives ρ\* = +∞ and is kept.
   - An infinite end is reported as "unbounded".
   - The share of such replicates is reported.

### 9e. The escalate-to-Opus cascade (Fix 7, offline)

The definitions follow Fix 7 exactly, with only these pins.

**The vote.** For k_c ∈ {5, 10, 20}, the vote uses Haiku-medium samples **1..k_c by sample index**:
- the top answer is the most common non-empty vote key among them;
- **its share** is its count ÷ k_c;
- a tie for the top answer is settled by the D-33 rule at expected credit 1/m.

**Escalation.** For τ ∈ {0.3, 0.4, 0.5, 0.6, 0.7, 0.8}: if the share is below τ, the cascade takes **Opus-medium's** answer on that
puzzle (right or wrong). Otherwise it takes the vote.

**Accuracy and cost per base:**
- accuracy follows the official score;
- cost = the list cost of samples 1..k_c, plus Opus-medium's list cost on that puzzle if it escalated.

**The frontier.** Accuracy and mean cost for every (k_c, τ) pair, per shape, with the escalation rate.

**The recommended τ for each k_c**, chosen on the **odd** base puzzles (base index odd): the cheapest τ whose mean accuracy on the odd
bases is at least Opus-medium's odd-base accuracy minus 10 points.
- If none qualifies, take the τ with the highest odd-base accuracy.
- Ties go to the lower cost, then the lower τ.

**Scored on the even bases only.** Report its accuracy and mean cost beside Opus-medium's on the same even bases, with the shared
cluster bootstrap over the even bases, named `"cascade:<shape>:<k_c>"`. Labelled exploratory.

### 9f. The cached ("input counted once") view (D-33 item 12; D-48 row 22: "a labelled offline re-pricing only")

**For a Haiku vote of k samples on a puzzle:** the input is billed once as a 5-minute cache write, and k − 1 times as a cache read.
Output is billed in full for every sample.
- Cached cost(k) = (in × w + (k − 1) × in × r + Σ_{k samples} out × o) ÷ 1,000,000 dollars, where in is the puzzle's mean
  Haiku input tokens per sample.
  - **The rates are read from the pinned table** (`prices.PRICES[prices.HAIKU]`), not typed in (Edith C-2):
    w = `cache_write_5m`, r = `cache_read`, o = `output`. Today those are $0.125, $0.01 and $0.50 per MTok.
  - **The minimum cacheable length is met** (Edith C-1; `research/facts-checked.md`, 2026-10-12). Haiku 5.5 caches prompts of
    512 tokens or more, and ours average about 1,030. So this is a re-pricing caching could really achieve, still labelled
    "offline re-pricing".
- The sum over k samples uses k × the puzzle's mean output tokens per sample.
- Single-call arms are unchanged, since one call gains nothing from a cache.

**The cached k** is the largest k ≤ min(40, samples drawn) with mean cached cost(k) over puzzles ≤ the comparator's mean list cost per
puzzle. The confirmatory family is reported at that k as one more k-sensitivity row, labelled "cached view (offline re-pricing)".

### 9g. The token-matched view (D-33 item 13: "so readers can re-price")

**Per shape, for k = 1 to 40:**
- vote@k (item 8 curve);
- the mean input tokens and mean output tokens of k Haiku samples per puzzle (k × the per-puzzle means);
- beside each comparator's mean input and output tokens per puzzle.

**The token-matched k** is the floor of (comparator mean total tokens per puzzle ÷ Haiku mean total tokens per sample), where total
means input plus output as billed. It is held to 1..40. The family is reported at that k as one more k-sensitivity row, labelled
"token-matched".

### 9h. The Opus-vs-Sonnet comparison

It is computed exactly as `research/paper-notes/opus-vs-sonnet-exploratory.md` defines it. Its "cost" is item 9b and its CPC is
item 9c. Exploratory, with no test.

## 10. The exploratory arms (Haiku-low, Haiku thinking-off, Haiku-max, Sonnet-low)

**Fills:**
- D-39 item 6: "every setup's results … reported in full as descriptive or exploratory";
- D-33 item 3: "One k per shape and per Haiku effort".

Every number here is labelled exploratory, with **no Holm and no verdict**.

**For each arm and shape:**
- single-try whole-answer accuracy (`scoring.arm_scores`, official score, all three views);
- format compliance and the rates (`five_tests.rates`, `format_report`);
- refusal and truncation counts;
- list cost per puzzle (item 9b) and CPC (item 9c).

**For the Haiku arms (hl ×40, ho ×40, hx ×3):**
- **The vote curve** for k = 1 to min(40, samples drawn), as in item 8. For Haiku-max that is k = 1 to 3.
- **Each arm's own equal-money k:** `kscript.k_value` on the arm's own mean list cost per sample, against Opus-medium per shape and
  against Sonnet-medium per shape, held to the samples drawn.
- **The vote at that k against its comparator:** the paired per-base difference, with `bootstrap.paired_bca(diffs, margin=−10,
  B=10_000, seed=derive_seed(20261011, f"explore:{arm}:{comparator}:{shape}"))`. Report d and the 95% interval only.

**For Sonnet-low:** the paired difference against Sonnet-medium and against Opus-low, per shape, with the same `paired_bca` call
(seed name `f"explore:sl:{comparator}:{shape}"`). Report d and the 95% interval.

**The D-87 curve** stays as its plan defines it.

## 11. Tests 3 and 5 at the other shape (6×1), exploratory

**Fills:** section 7b: "the other shape for tests 3 to 5 is exploratory".

- **Test 5 at 6×1:** Opus-low against Sonnet-medium (`single_scores`, official score).
- **Test 3 at 6×1:** the Haiku-medium vote at **k_S(6×1)** against Sonnet-medium. k_S(6×1) is `kscript.k_value` on the 6×1
  Sonnet-medium and Haiku-medium costs, from the same cost-only cell type as the confirmatory k.
- **For each:** d, the 95% BCa interval and the three-way reading at margin 10. Use `bootstrap.paired_bca` with seed
  `derive_seed(20261011, f"{test}@6x1")`, in all three views. These are labelled **exploratory, outside the Holm family**.
- **Test 4 at 6×1** is not computed: E3 did not run at 6×1. Jarvis puts the choice to the user (readiness checklist).

## 12. Exact intervals for single-arm accuracy (D-48 row 27; section 7b)

**For every arm with one try per puzzle** (Opus-medium, Opus-low, Sonnet-medium, Sonnet-low), per shape: x right out of n base
puzzles (official score, as_deployed), with a **two-sided 95% Clopper–Pearson** interval.
- This is pure Python: bisection on the binomial CDF using `math.comb`.
- `curve.py` stays as locked.

**For arms with several tries per puzzle** (the Haiku arms), accuracy carries the shared cluster bootstrap instead. A plain binomial
interval would ignore the clustering.

**Which intervals appear where** (Edith C-3): the D-87 curve markers keep the D-87 plan's Wilson intervals, as locked. The single-arm
accuracies reported as results use Clopper–Pearson (this item).

---

# Addendum B (2026-10-12, with the D-93 inventory; before any main-run result is opened)

*Karen (Opus 5.5). These pins come out of the full inventory (`research/reporting-inventory-main.md`). Each one is an output the
locked text already promises (a register ruling, the spec, or a file hashed in the lock manifest), with a detail still open that a
programmer would otherwise have to choose. Outputs that are **not** ruled and are undefined are **not** pinned here: the inventory's
keep-or-drop list puts them to the user. The same route applies (Edith, the user's yes, then the timestamp). The shared conventions
of Addendum A apply. No item here changes the five tests.*

## 13. The first-slip repeat share (spec, slip analysis: "pairwise agreement of wrong answers and of first slips")

**Pairs:** unordered pairs of Haiku-medium tries in the same base puzzle and shape that are **wrong and placeable**
(`scoring.first_slip_steps`, official parse).

**A pair agrees** if both tries have the same first-slip signature: the same (sequence, step, written balances).

**Reported:** pairs, agreeing pairs and their share, per shape and summed over both shapes. This sits beside item 4's whole-answer
repeat share, which uses the same pairing unit.

## 14. Slips per rule kind, for every model (D-67; spec 7b, "slips per rule kind for every model")

**The table:** `scoring.slip_table` over `scoring.local_steps` (the primary view), with `scoring.first_slip_steps` as the
sensitivity view.
- Every arm whose replies hold steps or pieces: Haiku-medium, Opus-medium, Opus-low, Sonnet-medium, Sonnet-low, Haiku-low, Haiku
  thinking-off and Haiku-max.
- Both shapes. At 6×1 each piece is one step.

**Reported per arm and shape:**
- for each kind and each class: steps checked and kind slips;
- the house rows: missed and misapplied, each over its own denominator;
- decoy confusion;
- the unplaceable tries, with the parse reason.

This covers "whether the slip was in the rule or the house rule" through the blame categories.

**Also split by the final answer** (spec §8: placed slips "for replies whose final answer is right and for those whose final answer is
wrong"; Edith N40): the same table, both views, computed separately for tries whose row has `correct_final` true and false.

**Also, the T+/G− sensitivity split** (`research/pilot-plan-ledger.md`, Fairness check: "mainly for the main run"):
- T+ is T plus `avg_donors`, `rank_move` and `count_move`; G− is `two_clause` and `compare_move`;
- RR and the TI built from them are computed exactly as item 4's family (`fairness` machinery), with the class sets swapped;
- reported, never a flag.

## 15. The near-ceiling label (Amendment 1 item 6)

**The label is the one the ladder set:** ON (Opus-medium 40 of 40 at n = 6). It is **not re-decided** on main-run data.
- The driver prints "near ceiling (Amendment 1)" beside tests 1 and 2.
- It shows the main run's Opus-medium pooled accuracy beside the label, for information only.

## 16. Refusals, truncations, missing items and retries (D-48 rows 20, 23 and 25; mock-review Fix 7)

**Rates:** for each arm, shape and refusal category, and for truncations (`stop_reason` "max_tokens"):
- the count ÷ the designed calls;
- a Wilson 95% interval (`curve.wilson`; Fix 7 names Wilson for these rates);
- the list cost of those calls (item 9a), so free B5 refusals show $0.

**Missing items** (D-48 row 23): **a planned try with no final record after the retry and resubmit rules**, which is the converter's
kind `missing` (Edith r7). Reported as count ÷ designed calls, per arm and shape.
- Final records of kind **empty, unexpected_stop or error are real results**. They are wrong, reported as their own kinds in the
  rates, and **kept** by the exclude-missing view.
- **The exclude-missing view runs only if any item is missing.** Missing single answers drop that base puzzle from a test. Missing
  Haiku samples drop from the vote, with k held to what is left. The five-test family is otherwise as_deployed: only missing items
  are left out (Edith B-1). It can be built with the locked `vote_scores(designed=0)` on the real calls.
- If nothing is missing, the report says "no missing items" and no view is computed.

**"vote@k uses the samples available, flagged":** for tests 1–3, the number of base puzzles with fewer than 40 Haiku-medium samples,
and their ids.

**Retries and Batch failures** (Fix 7; spec §4, "log expiries per setup"), per setup:
- the count of real-time retry events by status (429, 5xx);
- separately, the Batch items that **errored, expired or were canceled**, and their resubmits.

Both come from the run's ledger and calls log, and are reported as counts.

**Long prompts** (spec §5): per setup, the count of requests whose prompt tokens exceed 100,000, billed at Haiku's long-prompt row.
Expected 0.

## 17. The format-compliance flag (D-76: "flags any model whose non-compliance is above about 5%")

The flag fires for an arm and shape when the non-compliance share of **answered** tries is **above 5.0%**. That share is 1 −
`format_compliance` from `five_tests.format_report`, under the official D-90 rule.

## 18. How vote@k was computed (D-33 item 8: "Monte-Carlo error reported")

For each test that uses a vote, and for the vote curve:
- the method used (`exact` or `sampled`) and the number of base puzzles of each;
- the largest `mc_se` across puzzles, which is 0 for exact counts.

This uses the values `votes.vote_accuracy_at_k` already returns.

## 19. Thinking tokens (mock-review Fix 7)

**Per call:**
- visible tokens are estimated as the number of characters of the visible reply ÷ 3, rounded down (the estimate used in
  `research/post-pilot-n6.md`; the API does not report thinking separately and D-48 row 21 keeps no summary);
- thinking tokens = max(0, output tokens − visible estimate).

**Per arm and shape:**
- the median, the p90 (`statistics.quantiles(…, n=10, method="inclusive")[8]`) and the maximum of thinking tokens;
- thinking's share of list cost: Σ thinking × output rate ÷ Σ list cost.

All of these are labelled estimates.

## 20. The vote lookup chart (mock-review Fix 7)

**Per shape:**
1. Each base puzzle's Haiku-medium single-try accuracy (official, as_deployed, over its 40 samples) puts it in a 10-point bin:
   [0,10), [10,20), … [80,90), [90,100]. The last bin includes 100.
2. Within each bin, puzzles are split into thirds by their pairwise wrong-try agreement (item 4's per-puzzle share). Puzzles with fewer
   than 2 wrong tries form a separate group, "too few wrong tries". The thirds are cut by rank, with ties going to the lower third.
3. For each cell, report the mean vote@k for k = 1 to 40 (item 8 curve), and **the smallest k at which the cell's mean vote@k reaches
   Opus-medium's mean accuracy on the same puzzles**. If none does, report "none up to 40".
4. Bands: the shared cluster bootstrap within each bin, named `"lookup:<shape>:<bin>:<third>"`.

## 21. E3 fixed-3, simulated offline (D-27, E3 detail: "Fixed-3 results are simulated offline")

**For each E3 step position**, the fixed-3 vote is the plurality of the **first 3 logged draws**, in the order drawn.
- An unreadable draw votes for nothing. The plurality is taken among the readable answers.
- If all 3 are unreadable, the step is wrong.
- Tied top answers get expected credit 1/m (D-33). (Edith B-2.)
- If the lead-by-2 rule stopped after 2 agreeing draws, those 2 already decide any 3-draw majority, so the result is exact.
- If 3 different answers tie, the D-33 rule gives expected credit 1/3.

**E3 fixed-3's score per base** is the product over its steps of the step's fixed-3 credit, by the same product rule as F7. It is
reported beside E3 lead-by-2, descriptively.

## 22. The run window (D-45: "the actual window is reported")

The window runs from the first Batch submission to the last result, in hours, taken from the run's `window.json` and ledger. Any
extension under D-45 is reported with its note.

## 23. Re-pricing at later prices (D-48 row 24: "later price changes go in the offline re-pricing only")

This applies only if Anthropic's pricing page changes before publication. In that case, item 9's costs are recomputed on the new
table and shown beside the pinned ones, labelled with the new table's date. Otherwise, nothing.

## 24. Every setup's results and the three-model chart per shape (D-39 item 6, ruled: "the full three-model chart for each shape, every setup's results")

**The table, one row per arm and shape** (every arm of the run, the confirmatory ones included):
- base puzzles;
- single-try whole-answer accuracy (official, as_deployed):
  - one-try arms: x of n with Clopper–Pearson (item 12);
  - multi-try arms: the shared cluster bootstrap;
- for Haiku arms, also **the median over puzzles per shape and pooled** (spec 7b: "the median of Haiku-medium per shape is reported
  next to the pooled one");
- the vote at the arm's own k where it has one (items 8 and 10);
- format compliance (A, `format_report`);
- refusals and truncations (item 16);
- mean list cost per puzzle (item 9b);
- CPC (item 9c).

**The chart, per shape:**
- every arm as a point: mean whole-answer accuracy (y) against mean list cost per puzzle (x, item 9b), with the bars from the table;
- plus the Haiku-medium vote curve for k = 1 to 40 as a line (items 8 and 9b).

Nothing is fitted (a fitted frontier and a time axis are in the inventory's keep-or-drop list).

---

# Addendum C (2026-10-12): implementation pins for Friday's three group-B modules, before any main-run result is opened

*Karen (Opus 5.5). Friday built group B as `report_votes` (83f48d7), `report_costs` (4aae23f) and `report_arms` (5dfaf07). Wherever
this note left a choice, the code computes nothing and names the question. Each question gets one answer here, chosen for
consistency with the locked code. The route is the same: Edith, then the timestamp. Nothing here touches the five tests.*

## C0. Cross-cutting pins

**X1. Bootstrap names.**
- Use the **arm names of `main_rows`** everywhere: `haiku-med`, `opus-med`, `opus-low`, `sonnet-med`, `e3`, `haiku-low`,
  `haiku-thinking-off`, `haiku-max`, `sonnet-low`. Never the tags.
- Shapes are `6x1`, `1x6` or `pooled`.
- `<k-name>` is `k_O` (Opus-matched) or `k_S` (Sonnet-matched).
- **One name per statistic family, shared across k.** Every k of a curve, and every k of the cost and CPC at k, is computed from the
  same resamples. This is intended: the bands are pointwise but use common draws.

**X2. "Samples drawn"** for k*, break-even and the cached k is the **designed** number: 40 for the ×40 arms and 3 for Haiku-max. This
is the same convention as the confirmatory `k_from_rows`. A puzzle with fewer real samples has its own vote held to what it has, as
`vote_scores` already does.

**X3. A bootstrap draw with no correct answer** (CPC, items 9c, 10 and 24) gives CPC = +∞. It is **kept**, an infinite end is reported
as "unbounded", and the share of such draws is reported. This is the same rule as items 1 and 9d. Dropping those draws would favour
the arm.

**X4. A designed call with no record costs $0** and its puzzle stays in. This matches as_deployed, where a missing item is wrong, and
D-48 row 22 ("failed attempts at their billed cost, usually $0"). The number of such calls is reported.

**X5. "Every arm" in items 7 and 24** means the arms of the 80-base design: haiku-med, opus-med, opus-low, sonnet-med, e3 (at 1×6 only),
haiku-low, haiku-thinking-off, haiku-max and sonnet-low. The D-42 arm (`hv`, 20 bases) and the real-time arms (`rt*`, 5 bases) are
**out**. They have their own items, 3 and 6.

**X6. The intervals that had no name.** Each is the shared cluster bootstrap with 2,000 draws.
- Multi-try accuracy (the Haiku arms; E3's per-base score) in items 12 and 24: `"accuracy:<arm>:<shape>"`.
- The per-piece vote curve (item 7): `"per_piece_vote_curve:haiku-med:<k-name>"`.
- Item 20, the lookup chart:
  - draws are made from the cell's own base puzzles, one stratum per cell;
  - the statistic is the mean vote@k at each k, with one name per cell, `"lookup:<shape>:<bin>:<third>"`;
  - `<bin>` is the lower edge (`0`, `10`, … `90`) and `<third>` is `t1`, `t2`, `t3` or `few`;
  - the "smallest k reaching Opus" is a point value, with no band.

**X7. Cost per task for a multi-try arm** (item 7):
- in the single-try per-piece view: **one sample's** mean list cost per puzzle ÷ 6;
- for the per-piece vote at k: k × that ÷ 6, as item 7 already says.

**X8. k−2 … k+2 outside 1..min(40, samples drawn)** (item 8b). This stands as first written (Edith r8 withdrew her r7 point):
- each row is still run as a whole five-test family;
- a test whose k + d falls outside the range is **held at the nearest allowed k** and labelled "held at the limit" in that row;
- the row is not dropped, and the family stays five tests with that test's **real** p.

Treating the test as not run (p = 1) would act as if it had failed, and would shift the other tests' Holm thresholds in that row for no
reason. `kscript.k_sensitivity`'s `k_band` is only a listing of values.

## C1. Item-specific pins

| Item | Question | Pin |
|---|---|---|
| 9a | An `error` record with no usage | $0, as the guard records it, counted |
| 9a | The real-time calls' "Batch" column | Shown as their actual cost (real time = list), labelled "real time (list)" |
| 9b, 9c | No k in the names | Intended: common draws across k (X1) |
| 9c | Which arms get CPC at each k | Every Haiku arm with a vote curve (haiku-med, haiku-low, haiku-thinking-off, haiku-max). The others are single-try only |
| 9d | Comparator spelling | `"break_even:opus-med:<shape>"`, `"break_even:sonnet-med:<shape>"` |
| 9d | The comparator's cost over the drawn puzzles is $0 | R_list* = 0, so ρ* = +∞, kept (X3's rule) |
| 9e | Samples 1..k_c hold no usable vote | The top share is 0, so the puzzle escalates to Opus-medium |
| 9e | Statistics and names | One name per (shape, k_c), `"cascade:<shape>:<k_c>"`, shared by six statistics on the even bases: the cascade's accuracy and mean cost, Opus-medium's accuracy and mean cost, and the two differences (cascade − Opus, accuracy and cost). All use the same draws, so they are paired |
| 9f, 9g | "Input tokens" | `Usage.prompt_tokens`: input plus any cache read and write tokens, which should all be 0 since we never request caching |
| 9f, 9g | Free B5 refusals | **Billed tokens only**: a B5-free refusal counts 0 tokens and $0, consistent with item 9a |
| 9g | "Haiku mean total tokens per sample" | Pooled over all samples in the shape (as kscript's cost per sample is pooled). The comparator's is the mean over puzzles |
| 9f | No k ≥ 1 meets the cached condition | Cached k = 0, and tests 1–3 are "not run" in that row (the k = 0 rule) |
| 9h | Statistics and names | Exactly as the Opus-vs-Sonnet note says: 10,000 draws, seed 20261012. Names are `"ovs:<stat>:<a>-vs-<b>:<shape>"`, where `<stat>` is `acc_diff`, `cost_ratio`, `cpc_ratio` or `err_ratio`, and the pairs are opus-med vs sonnet-med and opus-low vs sonnet-med. `err_ratio` follows item 1's +∞ rule |
| 19 | A group with fewer than 2 calls | p90 = "n < 2". The median and maximum are still given if n = 1 |
| 22 | The window's end | Accepted as Friday proposes: from the ledger's first Batch send to its last commit of any call, real time included, with the hours to the last Batch result alongside |
| 23 | How a later table is supplied, and what is re-priced | Only after Karen's dated re-check in `facts-checked.md`. The new rows are passed to the re-pricing function as a table of the same shape as `prices.PRICES`, with its date. Items 9a–9d and 9f are re-priced; k is never re-priced |
| 10 | View for the differences against a comparator | as_deployed only. Accuracies are given in all three views, as item 10 says |
| 14 | The final-answer split at 6×1 | At 6×1 the final answer is the whole answer, so `correct_final` = `correct` |
| 14 | "Item 4's family" for T+/G− | RR and TI with T := T+ and G := G−, computed by the same `fairness` machinery and reported. Never a flag |
| 16 | E3's denominators | E3 has no designed count, so its rates are over the E3 calls actually made, labelled as such |
| 16 | What "missing" is | **A planned try with no final record after the retry and resubmit rules**, which is the converter's kind `missing` (D-48 row 23; Edith r7; it matches the driver's `missing_left_out`). Final records of kind empty, unexpected_stop or error are **real results**: wrong, at their billed cost (usually $0), reported as their own kinds in the rates, and **kept** by the exclude-missing view |
| 20 | Thirds when a bin isn't a multiple of 3 | Sort the bin's puzzles by (agreement, base_id), ascending. Puzzle i (from 0) goes to third floor(3i / n). A whole tie group takes the third of its first member, so ties go to the lower third |
| 20 | "Reaches" | The cell's mean vote@k ≥ Opus-medium's mean on the same puzzles, compared after rounding both to 1e-9 |
| 21 | Fewer than 3 draws, not a 2-agreeing stop (only if draws errored or went missing) | Missing draws vote for nothing, and the plurality is among the readable draws present. None readable means the step is wrong |
| 7 | A partly readable 6×1 reply | **Readable entries get credit**, as in the locked `grade_24x1` `pieces_right` ("per-piece credit, D-23: entries that pass the value rules and equal the key"). A refused, truncated or missing try scores 0. This replaces item 7's "an unparseable try … makes that piece wrong" |

## C2. The arms helper's readings: confirmed

- **Item 11 outside Holm:** a family of one, non-inferior if and only if p ≤ 0.025. This is the unadjusted one-sided α; the reading
  is labelled exploratory.
- **The pooled Haiku median:** over both shapes' puzzles together, as `curve._panels` and the locked pick statistic do.
- **Arm accuracy:** the mean over puzzles. A Haiku arm's chart point sits at its single-try cost, with its vote curve drawn as the
  line.
- **Retries:** real-time 429 and 5xx records, plus Batch resubmits carrying the same id.
- **Vote-curve diagnostics:** method and mc_se per k.
- **A try that didn't answer** counts as unplaceable, with its kind.

## C3. On merge

One shared copy each of list_cost (9a), dollars per puzzle (9b), CPC (9c) and the vote curve (8), used by all three modules, as
Friday proposes.

## C4. Four last pins (2026-10-12, after the main run launched at 13:01:21Z and before any result is opened; Friday's four questions)

1. **Item 7, the band on the per-piece vote curve.**
   - The curve over k = 1..40 has **one** name, `"per_piece_vote_curve:haiku-med"`. All k share its draws.
   - The two marked points at k_O and k_S are that curve's values and bands at those k, so they need no names of their own.
   - This replaces X6's `<k-name>` suffix for this curve.
2. **Item 9d, when Haiku's side costs $0 in a draw:** R_list* = +∞, so **ρ\* = 0, kept and counted.** If Haiku is free, the vote is
   cheaper at any price ratio.
3. **Item 9h, a ratio with no value in a draw.** One rule for every ratio (cost, CPC, error), the same as item 1:
   - x / 0 with x > 0 gives +∞, kept;
   - 0 / x gives 0, kept;
   - ∞ / finite gives +∞, kept;
   - finite / ∞ gives 0, kept;
   - **0 / 0 and ∞ / ∞ are undefined: the draw is dropped and counted.**

   The interval is the percentile over the kept draws, and the share of dropped draws is reported. The interval is never withheld.
4. **Item 23, a request over 100,000 prompt tokens.** If the later table supplies its long-prompt rows, use them. Otherwise that
   request is **not re-priced**: it is listed as "not re-priced (no long-prompt row)", and its pinned-table cost stays. None are
   expected.
