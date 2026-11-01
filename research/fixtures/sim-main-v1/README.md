# Simulated main-run datasets with known answers (sim-main-v1)

*Karen (Opus 5.5), 2026-10-11. For testing Friday's analysis code before the D-69 lock. Desk simulation
only: no API calls, no real model output. Generator: `research/models/sim_fixtures.py` (deterministic
seeds; `python3 research/models/sim_fixtures.py cases` rewrites every case).*

## What is here

Seven cases, one folder each. Each folder holds:
- `rows.jsonl.gz`: one JSON row per scored call (gzip; read with `gzip.open(path, 'rt')`);
- `expected.json`: the true differences, the k values, the accuracies, and the readings from my
  reference implementation, in three views.

| Case | True d per test (t1 … t5), points | What it exercises |
|---|---|---|
| `ni` | +12 for all five | Clearly non-inferior: all five read non-inferior |
| `d0` | 0 | No difference |
| `d-5` | −5 | Inside the margin |
| `d-10` | −10, exactly on the margin | Size: the one-sided test should reject about 2.5% of the time (see coverage below) |
| `d-15` | −15 | Beyond the margin, but n = 80 is too few to call it "worse" |
| `worse` | t1 −15; t2–t5 −30 | The "worse by more than the margin" reading |
| `mixed` | t1 +12, t2 0, t3 −5, t4 −10, t5 −15 | The Holm order, plus refusals, truncations and null answers for the three views |

"True d" is the population value with refusals and truncations left out. A single dataset at its fixed
seed gives its own d̂, which can sit well away from the truth at n = 80. The readings in `expected.json`
are for the data as generated, not for the truth.

## The tests (D-68, Edith's F1–F4)

| Test | Challenger | Comparator | Shape |
|---|---|---|---|
| t1 | Haiku-medium vote at k_O | Opus-medium | 24×1 |
| t2 | Haiku-medium vote at k_O | Opus-medium | 1×24 |
| t3 | Haiku-medium vote at k_S | Sonnet-medium | 1×24 |
| t4 | E3 | Opus-medium | 1×24 |
| t5 | Opus-low | Sonnet-medium | 1×24 |

- **The unit and the statistic.** The unit is the base puzzle, paired, with n = 80. d is the mean over
  base puzzles of challenger − comparator, in points, with whole-answer scores.
- **The vote score.** The vote arm's score per puzzle is the **exact** expected vote@k over all k-subsets
  of its samples:
  - plurality vote;
  - a tie of m answers that includes the right one scores 1/m;
  - a `null` answer is a vote for nothing.
- **E3's score.** E3 is scored by its `correct` field, which equals `all(step_correct)`, so the product
  estimator (F7) gives the same 0 or 1.
- **The hypotheses.** H0: d ≤ −10.
- **The bootstrap.** A paired base-puzzle **BCa** bootstrap with 10,000 resamples. The per-test seed is
  `int(sha256(f"{case_seed}:{test}").hexdigest()[:15], 16)`, with numpy `default_rng`.
- **p** comes from inverting the BCa lower bound at −10. The formula:
  - G = the share of bootstrap means ≤ −10, clipped to [1/(B+1), B/(B+1)];
  - w = Φ⁻¹(G) − z0;
  - u = w / (1 + a·w);
  - p = Φ(u − z0).
- **Holm.** One-sided family α = 0.025. Order the five p values; step j's threshold is 0.025/(6 − j).
  Stop at the first failure.
- **The three-way reading:**
  - **non-inferior** if the test passes Holm;
  - **worse by more than the margin** if the two-sided 95% BCa interval's upper end is below −10;
  - otherwise **inconclusive**.
- **Near-threshold readings.** `near_threshold: true` marks readings within 20% of their Holm threshold,
  or within 0.5 points of −10 at the interval's upper end. A differently seeded bootstrap may flip those.
  Friday's code should match every reading not so marked.

## The three views (D-68 F3)

- **`as_deployed`** (primary): refusals, truncations and unparseable replies count as wrong. In the vote,
  they are `null` (a vote for nothing).
- **`refusals_left_out`:** a refused single answer (Opus, Sonnet, Opus-low, E3) drops that base puzzle
  from that test. A refused Haiku sample would be dropped from its vote; there are none here.
- **`truncations_left_out`:** a truncated single answer drops that base puzzle from that test. Truncated
  Haiku samples are dropped from the vote, with k capped at the samples left.
- **Unparseable** replies are wrong, or `null`, in every view. They are not blocks.

My definitions of the left-out views are written down here for Friday to check against his. If his
differ, tell me and I'll regenerate.

In `mixed`, at 1×24:
- Opus-medium refuses 4 times (`cyber`, cost 0);
- Opus-low refuses once;
- Sonnet-medium truncates twice;
- about 1% of Haiku's samples are unparseable and 0.5% are truncated.

The 4 Opus refusals move t2 from d̂ = −2.2 as deployed to −6.5 left out, about the 4–5 points the mock
review predicted.

## The row format (agreed with Friday)

`set_id, preset, base_id, shape ("24x1" | "1x24"), setup ("haiku-med" | "opus-med" | "opus-low" |
"sonnet-med" | "e3"), try (0-based), kind ("answered" | "refusal" | "truncated" | "unparseable"),
stop_reason, refusal_category, answer_key (canonical string, or null), correct, cost_usd (decimal
string)`.

- **`step_correct`** (24 booleans) is present:
  - on every E3 row;
  - on Opus-medium, Opus-low and Sonnet-medium 1×24 rows;
  - on Haiku 1×24 rows in `mixed` only.
- **What `step_correct` looks like.** A right chain occasionally has one wrong step line (3%: an absorbed
  rejoin or a copying slip), so the all-step-lines-right view can differ from whole-answer scoring.
- **`base_id` is shared by both shapes** (the matched design).
- **Haiku's wrong answers.** 20% of them land on one shared wrong value per puzzle, and the rest are all
  different. So ties, and wrong pluralities, both occur.

## k (D-33)

k = floor(mean Opus-medium (or Sonnet-medium) cost per puzzle ÷ mean Haiku-medium cost per sample),
per shape, all in, capped at 40.
- The costs are central Batch prices from `research/models/study1_budget.py`, with ±1% noise.
- That gives k_O = 29 and k_S = 14 in the plain cases. In `mixed`, the refusals (cost 0) and truncations
  change them: k_O(1×24) = 27 and k_S = 15.
- The generator asserts that the k computed from the written rows equals the k the accuracies were set
  for.

## The world behind the data (OURS; as in `research/models/study1_ni_power.py`)

- **Haiku-medium.** Its single-try accuracy per puzzle is Beta(4m, 4(1 − m)), with m = 0.40 at 24×1 and
  0.25 at 1×24 (world ii-mod).
- **The other arms.** One answer per puzzle each. Each arm's accuracy is set so that each test's true d
  hits its target.
- **Correlations.** The latent difficulty is shared across shapes (ρ = 0.5) and across arms (κ = 0.5).

## Coverage at d = −10 (the size test)

`coverage-d-10.json` holds 1,000 regenerated `d-10` datasets (seeds 500000…500999), with my reference
BCa's rates:
- **one-sided 0.025:** rejects 2.30% pooled (per test 1.5–3.4%);
- **0.005:** rejects 0.52%;
- **95% coverage:** 94.6% pooled (93.5% for t1, 93.9% for t2, 95–95.6% for the others);
- **under Holm, any of the five non-inferior:** 2.5%.

Suggested pass bands for a 200-replicate test in Friday's suite (binomial 99% ranges around these
rates):
- rejections at one-sided 0.025: expect about 5 of 200, accept 0–12, per test;
- coverage of −10 by the two-sided 95% interval: expect about 187–191 of 200, accept 178 or more, per
  test;
- under Holm, any of the five non-inferior: expect about 5 of 200, accept 0–12.
