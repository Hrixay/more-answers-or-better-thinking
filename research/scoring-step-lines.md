# Should "all step lines right" be the official 1×24 score? (Edith's PR #19 round-2 fallback (b))

*Karen (Opus 5.5), 2026-10-11. A quick assessment for Jarvis, for the user. Desk only, no model calls.
The trigger: Edith found that the ledger's slip absorption is not really under the 5% cap for 1-unit slips
(l14 averages about 8%).*

## The options

- **(a)** Accept a higher absorption rate, measure it and report it.
- **(b)** Make "all 24 step lines right" the official 1×24 score, in place of the final answer. It never
  forgives a slip, so absorption stops mattering.
- **(c)** Keep the final-answer score, and cap absorption per slip size in the generator.

## 1. What (b) changes in the five tests

| Test | Under (b) |
|---|---|
| 1 (vote vs Opus, 24×1) | **No change.** The whole answer at 24×1 is already "24 correct step results" (the 24 Answer entries) |
| 2 and 3 (vote vs Opus and vs Sonnet, 1×24) | The vote runs over **whole traces**: a sample's answer key is the canonical string of its 24 parsed step states. Plurality, ties at 1/m, and the vote@k estimator (D-33) are unchanged. A trace with an unparseable line is a vote for nothing. **Not** line-by-line voting, which would turn the vote into a step-wise procedure like E3 |
| 4 (E3 vs Opus, 1×24) | **Cleaner, exactly like for like.** E3's product of per-step accuracies already equals the all-steps-right probability (D-68 F7). Opus's all-step-lines score, now a sensitivity row, becomes primary |
| 5 (Opus-low vs Sonnet, 1×24) | Both arms are scored on step lines |
| Equal-money k | No change (cost only) |
| Power | Every 1×24 arm loses its absorbed and copy-slipped successes, so accuracies drop a few points. The vote also loses the support of absorbed samples. Opus's variance rises slightly as its accuracy falls from about 90%: about +10% on the half-width. `study1_ni_power.py` can rerun it |
| The preset rule (D-36(4)) | The 1×24 pilot puzzles must be scored the same way, pinned before the pilot. Haiku's 1×24 accuracy falls, so the rule may pick an easier preset |

## 2. The 1×24 vs 24×1 comparison

**It gets cleaner.**
- Both shapes then need 24 correct step results. What is left is the real difference: 1×24 steps start
  from the model's own state (chaining, context build-up, self-conditioning), while 24×1 steps start
  from given states.
- Under the final-answer score, 1×24 also gets absorption credit. That biases the structure contrast
  toward 1×24 by roughly the slip rate × the absorption rate. (b) removes it.

## 3. Risks

- **Copying and format slips count as wrong.** A right computation printed wrongly fails (Edith's N40
  case: Haiku, d4p chain B, step 22).
  - This tilts slightly toward the vote: random copy slips get outvoted, but a single Opus or Sonnet
    answer has no protection.
  - **Mitigation:** the local-slip table separates line errors that don't carry forward (copy slips)
    from real slips. Report a "copy slips forgiven" sensitivity score, and each arm's copy-slip rate.
- **D-36(5), the answer-only switch.** Answer-only replies have no step lines, so (b) can't score them.
  Pre-register that if the switch fires, the 1×24 tests fall back to the final-answer score for **all**
  arms, with absorption measured and reported (that is (a)). D-36(5)'s narrowing still awaits the user.
- **Changes beyond the score.**
  - (b) changes D-39's official scoring for 1×24, and D-36(4)'s, so **it needs the user's ruling**.
  - D-68 otherwise stands: F1–F4, Holm, the margin, the views and k. F7 flips which score is primary.
  - The final-answer score stays as a reported secondary view, with measured absorption.
- **Work before the lock.**
  - Friday: the scoring function and the trace key.
  - Karen: regenerate `research/fixtures/sim-main-v1/` with step lines on every 1×24 row, about an
    hour.
- **The claim changes slightly**, to "a fully correct worked trace as often as Opus". That is arguably
  the more useful claim for auditable work. Say so in the paper.

## 4. Recommendation (OURS)

1. **(b)**, with three parts pre-registered:
   - final-answer accuracy as the secondary view, with measured absorption;
   - the copy-slip-forgiven sensitivity;
   - the fallback to final-answer scoring if the answer-only switch fires.

   It removes the absorption tilt (which favours the vote, Edith's F5 table), makes test 4 exact, and
   needs no generator change.
2. **(a)**, if the code can't change before the lock. Report the measured rate (about 8% for 1-unit
   slips), and update the bias-table row "capped at 5%" to the measured number.
3. **Not (c).** A per-size cap means rebuilding the presets after the D-67 freeze, which would be a
   declared deviation. The free-read calibration would go stale, and it risks the timeline.
