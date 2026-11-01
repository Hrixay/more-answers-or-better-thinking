# D-72, D-73 and D-74: what the lock pins for the post-pilot re-run and the cut order (scored per D-76)

*Karen (Opus 5.5), 2026-10-11. For the D-69 lock. These are the rules ruled by the user (D-72: the add-40
rule; D-73: the cut order; D-74: confirmatory precision ranks above the extras), with Edith's conditions (`ops/reviews/2026-10-11-power-cutorder-house-T.md`),
written so that after the pilot they run mechanically. No model calls.*

## Files that go into the lock

| File | Role |
|---|---|
| `research/models/study1_ni_power.py` | The power simulator. Entry points `d72_inputs` and `d72_rerun`; config `D72` |
| `research/models/study1_budget.py` | The token and price model. It reads `ledger_measured.json` |
| `research/models/study1_cut_order.py` | The ladder (`LADDER`), `CEILING = 170`, `d73_cuts`, `d72_budget_test`, `add40_cost`, `post_pilot_decision`, and the D-74 known-answer examples (`D74_EXAMPLES`) |
| `research/models/d74_example_output.json` | The expected decisions for the four D-74 examples. Running `python3 study1_cut_order.py` asserts they still reproduce |
| `research/models/d72_example_inputs.json` and `d72_example_output.json` | A synthetic known-answer check. Re-running the example must reproduce the output exactly (same seed) |
| This file | The definitions below |

The lock tag's fingerprint (D-71) covers the exact versions. Nothing in these files changes after the lock.
The pilot's numbers go only into the input file and `ledger_measured.json`, recorded in the one dated
amendment (D-69).

## D-72: the add-40 rule

**1. Inputs.** All come from the pilot, at the **chosen preset**, on **1×24 puzzles only**, scored by the
**official 1×24 score (D-76: all 24 step lines right, Answer line equal to line 24)**, as deployed:
- `haiku_correct[b]` and `haiku_tries[b]`: Haiku-medium's right tries and tries (10) for each pilot puzzle.
- `wrong_pairs_agree` and `wrong_pairs`: summed over puzzles. For each puzzle, take all pairs of its wrong
  Haiku tries; count those with the **same 24-state trace** (`trace_key`, D-76), and all of them. A null
  trace (unplaceable or malformed) never agrees with anything.
- `opus_correct[b]`: Opus-medium's one answer per puzzle, 1 if right. A refusal or truncation is 0.
- `k`: the equal-money k for 1×24 at the chosen preset, from the pilot's costs (D-33, D-70: capped at 40).

**2. How the inputs are turned into model parameters** (`d72_inputs`):
- **m** = the mean of each puzzle's share of right tries.
- **Spread between puzzles**, with binomial noise removed:
  - Var(p) = var(p̂) − E[p(1 − p)] / n, where E[p(1 − p)] = mean(p̂(1 − p̂)) · n / (n − 1).
  - The Beta concentration is m(1 − m) / Var(p) − 1, clipped to [0.5, 200].
  - If Var(p) ≤ 0, there is no spread (world i).
- **Repeat share s = √(agreeing pairs ÷ pairs).** In the model, two wrong tries agree with probability s².
- **p_opus** = Opus's mean, clipped to [0.5, 0.99].

**3. The fixed run** (`D72`):
- seed 20261011, 4,000 simulated studies, κ = 0.5, 40 samples;
- B = 80, with 120 for information;
- Holm's strictest step: one-sided 0.005, i.e. a 99% two-sided interval;
- margin 10;
- the "worse" reading uses the unadjusted two-sided 95% interval (D-68 F2).

**4. Power test.** It passes if P(conclusive) at 80 base is under 0.5, where conclusive means non-inferior
or worse. The output field is `add_40_power_test`.

**5. Budget test** (`d72_budget_test`, high case), **as amended by D-74**: confirmatory precision ranks
above the extras.
- **Walk the extras-only part of the ladder** (`LADDER[0..5]`):
  1. the full plan;
  2. then Haiku-max;
  3. then H-pick8, then E2, then Haiku-off, then Sonnet-low.

  It passes at the first step where the high case **with** the 40 is at most $170. The extras cut up to
  that step are traded for the 40.
- **Nothing at or below Haiku-low ×20 or the D-42 robustness check, and nothing confirmatory, may be
  traded.** If even the musts plus the 40 exceed $170, the test fails.
- **The all-in total after the pilot** = the main run × 1.05 + the **actual** spend before the main run.
  That spend covers the 20-call check, S3 and the pilot, from `ops/spend-log.md` (the `spent` argument).

**6. The rule** (`post_pilot_decision(power_passes, s=2, spent)`). Add the 40 extra 1×24 base puzzles
for tests 2–5 **only if both tests pass**, cutting the extras the budget test names.
- **Otherwise there is no add,** and D-73 runs as usual.
- **Decided once, from pilot data.** The decision is recorded in the dated amendment (D-69) and reported
  in the paper (D-74).
- The 40 are generated and frozen **before the lock**, disjoint from every other set. That is Friday's
  job.
- The analysis then uses 120 base puzzles for tests 2–5, and the matched 80 for test 1 and the shape
  contrasts.

**Caveats** (OURS):
- With 10 Opus answers at 1×24 (slot A) or 5 (slot C), p_opus is noisy, about ±15 points. The rule uses
  the point estimate, as pinned.
- D-74 resolves the earlier tension: extras no longer outrank the add.
- **When the add can happen.** After the pilot, with $25 spent before the main run and the examples'
  other settings, the add fits (musts plus the 40 at most $170) if Opus-medium's measured mean thinking
  is up to about **11K tokens per puzzle** (t ≈ 1.09). On today's pre-pilot high case (24K) it would not.

## D-73: the cut order

**1. The projection.**
- After the pilot, write into `research/models/ledger_measured.json` the pilot's means at the chosen
  preset:
  - `in_tokens` and `vis_tokens`, the same in all three scenarios;
  - `tm = [t, t, 1.25·t]`, with t = Opus-medium's mean thinking tokens ÷ 10,000;
  - `hm_ratio` = Haiku-medium's mean thinking ÷ Opus-medium's;
  - `sm_ratio` = Sonnet-medium's ÷ Opus-medium's;
  - **`post_pilot: true`**, so that the **thinking** assumptions (`ol`, `om`, `oh`, `sm`, the keys `tm`
    scales) start from their central values in every scenario.
    - Without it, the pre-pilot spread (16K vs 10K at medium) would stack on the 1.25, and the high case
      would come out about 2× the measured cost, not 1.25×.
    - I found and fixed this while building D-74; it is pinned in `study1_budget.collapse_to_central`.
  - **Keys the pilot does not measure keep their low, central and high spread** (Edith's L-a,
    `ops/reviews/2026-10-11-d74-lock-code-r1.md`): E3 and E2 step tokens, aggregator inputs, sample
    inputs.
  - **`in_tokens` and `vis_tokens` must each be one mean, the same in all three slots.** The code asserts
    this when `post_pilot` is set.
- Thinking tokens = `usage.output_tokens` minus the visible reply's tokens (characters ÷ 3).
- The **high** column of `study1_cut_order.py` is then the high case.
- The 1.25 covers the main run's preset mix and the setups the pilot doesn't measure (OURS).

**2. The ladder** (`LADDER`, applied once, before the main run, never during it):
1. Haiku-max;
2. H-pick8, then E2, then Haiku-off, then Sonnet-low;
3. Haiku-low ×40 → ×20;
4. the D-42 robustness check, 40 → 20 puzzles;
5. the 24×1 exploratory arms (Sonnet, E3, Opus-low);
6. base puzzles 80 → 70;
7. base puzzles 70 → 60.

`d73_cuts(2)` returns the first step whose high all-in total is at most $170.
- **If none fits** (even the minimum viable run, which is core only at 60 base, is above $170): stop and
  return to the user (D-27's stop-loss).
- **Every step keeps all five confirmatory arms** (D-68 F2).

**Which runs first.** `post_pilot_decision` runs D-72/D-74 first. If there is no add, `d73_cuts` runs. An
add and a cut **below** the extras never happen together.

**3. At 60 base,** the paper states that test 2 (H1 at 1×24) is likely inconclusive. Interval half-widths
grow by about 15% (`research/mock-review-fixes.md` §4).

**Today's model.**
- High case: cuts through step 6 (80 → 70 base), $165.8 all in.
- Central case: no cut ($133.7).
- These are placeholders until the pilot measures tokens.

## Known-answer examples for D-74 (`D74_EXAMPLES`, `d74_example_output.json`)

These use synthetic post-pilot token states (`post_pilot`): Opus-medium thinking = 10,000 · t (high =
1.25 t), input 3,350 tokens, visible 660, and $25 spent before the main run. All at the high case:

| Example | t | Power test | Decision |
|---|---|---|---|
| A | 0.6 | passes | **Add**, no cut; $153.5 with the 40 |
| B | 1.0 | passes | **Add**, after trading Haiku-max, H-pick8, E2 and Haiku-off; $169.2 |
| C | 1.6 | passes | **No add** (the musts plus the 40 come to $222); D-73 cuts through the 24×1 exploratory arms, $149.4 |
| D | 1.2 | fails | **No add**; D-73 cuts through E2, $168.9 |

The unmeasured E3 and E2 step tokens keep their high-case spread (L-a), which is why C's cuts reach the
24×1 exploratory arms (E3 among them).

Running `python3 research/models/study1_cut_order.py` asserts these four still reproduce. The D-72
simulator example (`d72_example_inputs.json`) also reproduces exactly.
