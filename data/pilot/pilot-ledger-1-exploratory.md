# Pilot-1 (24 steps), all three models: EXPLORATORY results (D-86(5))

*Friday (Opus 5.5), 2026-10-12. Opened after `prereg-lock-2` was cut and posted (tag at `95fb5f8`; Zenodo v2 10.5281/zenodo.23311831).
Exploratory and descriptive only: no test, no decision; nothing here changes the locked design. Numbers: `pilot-ledger-1-exploratory.json`,
made by `python3 -m harness.analysis.explore_pilot1` (official D-76 scorers, read from the raw replies; the module text defines every view).
Run `pilot-ledger-1` (2026-10-11): Batch, effort medium; Haiku ×10, Opus ×1, Sonnet ×1 per puzzle; sets pilot-ledger-l14/l15/l16-v1
(5 / 10 / 10 base puzzles × 2 shapes). `calls.jsonl` SHA-256 411c877b…9f142.*

## In three lines

- **Opus-medium got 24-step puzzles right almost always: 96% of separate-pieces puzzles and 88% of long chains; Haiku-medium almost never (under 2%).** Sonnet-medium sat in between, at about 50%.
- **The gap is per step, compounded.** Per piece, Opus is about 99.8% right, Sonnet 96% and Haiku 83%. Over 24 steps, only Opus's rate survives.
- **Real time and Batch look the same** on the 10 puzzles checked, within the small numbers. Opus's few misses are mostly format slips on the long chain, not wrong arithmetic.

## Whole-answer accuracy (official D-76 score), with 95% intervals

Haiku: mean of each puzzle's share of its 10 tries, cluster bootstrap. Opus and Sonnet: one try per puzzle, Wilson interval.

| Preset | Shape | Haiku-medium (single try) | Opus-medium | Sonnet-medium |
|---|---|---|---|---|
| l14 | 24x1 | 2.0% [0–6] | 100.0% [57–100] | 80.0% [38–96] |
| l14 | 1x24 | 2.0% [0–6] | 100.0% [57–100] | 80.0% [38–96] |
| l15 | 24x1 | 0.0% [0–0] | 100.0% [72–100] | 50.0% [24–76] |
| l15 | 1x24 | 2.0% [0–5] | 90.0% [60–98] | 60.0% [31–83] |
| l16 | 24x1 | 0.0% [0–0] | 90.0% [60–98] | 30.0% [11–60] |
| l16 | 1x24 | 0.0% [0–0] | 80.0% [49–94] | 30.0% [11–60] |
| pooled | 24x1 | 0.4% [0–1] | 96.0% [80–99] | 48.0% [30–67] |
| pooled | 1x24 | 1.2% [0–2] | 88.0% [70–96] | 52.0% [33–70] |

## Final-answer view (the Answer line alone; at 24×1 it equals the whole answer)

| Preset | Shape | Haiku | Opus | Sonnet |
|---|---|---|---|---|
| l14 | 1x24 | 2.0% [0–6] | 100.0% [57–100] | 80.0% [38–96] |
| l15 | 1x24 | 3.0% [0–7] | 100.0% [72–100] | 60.0% [31–83] |
| l16 | 1x24 | 0.0% [0–0] | 90.0% [60–98] | 40.0% [17–69] |
| pooled | 1x24 | 1.6% [0–4] | 96.0% [80–99] | 56.0% [37–73] |

## Per step

24×1: share of pieces right. 1×24: (a) step lines equal to the key, (b) the local-slip per-step accuracy (each step judged from the
model's own previous line), (c) the first wrong step (median line number, over tries with a wrong line), over tries whose lines can be placed.

| Preset | Model | 24×1 per piece | 1×24 lines = key | 1×24 local per step | 1×24 first wrong step (median) | all 24 lines right / placeable | unplaceable |
|---|---|---|---|---|---|---|---|
| l14 | Haiku | 88.2% [86–90] | 25.9% [18–36] | 87.1% [84–90] | 6 | 1 / 40 | 10 |
| l14 | Opus | 100.0% [100–100] | 100.0% [100–100] | 100.0% [100–100] | – | 5 / 5 | 0 |
| l14 | Sonnet | 99.2% [98–100] | 93.3% [80–100] | 98.3% [95–100] | 17 | 4 / 5 | 0 |
| l15 | Haiku | 83.2% [80–86] | 19.7% [9–33] | 80.6% [77–84] | 3 | 2 / 87 | 13 |
| l15 | Opus | 100.0% [100–100] | 100.0% [100–100] | 100.0% [100–100] | – | 9 / 9 | 1 |
| l15 | Sonnet | 95.8% [93–98] | 74.6% [52–93] | 97.1% [95–99] | 9.0 | 6 / 10 | 0 |
| l16 | Haiku | 80.3% [78–83] | 9.6% [5–15] | 74.1% [71–78] | 2.0 | 0 / 82 | 17 |
| l16 | Opus | 99.6% [99–100] | 91.2% [74–100] | 99.1% [97–100] | 6 | 8 / 9 | 1 |
| l16 | Sonnet | 94.6% [92–97] | 52.9% [27–80] | 96.7% [95–98] | 3 | 3 / 10 | 0 |
| pooled | Haiku | 83.1% [82–85] | 16.9% [12–23] | 79.3% [77–81] | 3.0 | 3 / 209 | 40 |
| pooled | Opus | 99.8% [99–100] | 96.6% [89–100] | 99.6% [99–100] | 6 | 22 / 23 | 2 |
| pooled | Sonnet | 96.0% [94–98] | 69.7% [56–83] | 97.2% [96–98] | 5.0 | 13 / 25 | 0 |

## Format compliance and truncations

| Preset | Shape | Haiku format ok | Opus | Sonnet | Truncated (Haiku / Opus / Sonnet) |
|---|---|---|---|---|---|
| l14 | 24x1 | 100.0% | 100.0% | 100.0% | 0 / 0 / 0 |
| l14 | 1x24 | 80.0% | 100.0% | 100.0% | 0 / 0 / 0 |
| l15 | 24x1 | 100.0% | 100.0% | 100.0% | 0 / 0 / 0 |
| l15 | 1x24 | 87.0% | 90.0% | 100.0% | 0 / 0 / 0 |
| l16 | 24x1 | 100.0% | 100.0% | 100.0% | 0 / 0 / 0 |
| l16 | 1x24 | 82.8% | 90.0% | 100.0% | 1 / 0 / 0 |
| pooled | 24x1 | 100.0% | 100.0% | 100.0% | 0 / 0 / 0 |
| pooled | 1x24 | 83.9% | 92.0% | 100.0% | 1 / 0 / 0 |

No refusals in any setup. The one truncation is a Haiku 1×24 try at l16 (stop reason max_tokens at 48K).

## The real-time check next to Batch (l16 base puzzles 0–4, both shapes: 10 puzzles)

Real time: Haiku ×5, Opus ×1, Sonnet ×1 per puzzle; Batch: the same puzzles' Batch tries (Haiku ×10, Opus ×1, Sonnet ×1).

| Model | Mode | 24×1 whole | 24×1 per piece | 1×24 whole | 1×24 final | 1×24 lines = key | 1×24 local | 1×24 format ok |
|---|---|---|---|---|---|---|---|---|
| haiku-5-5 | real time (25+25 tries) | 0.0% | 79.2% | 0.0% | 0.0% | 17.7% | 75.1% | 92.0% |
| haiku-5-5 | Batch (50+50 tries) | 0.0% | 81.1% | 0.0% | 0.0% | 10.0% | 76.5% | 71.4% |
| opus-5-5 | real time (5+5 tries) | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| opus-5-5 | Batch (5+5 tries) | 100.0% | 100.0% | 60.0% | 80.0% | 80.2% | 97.9% | 80.0% |
| sonnet-5-5 | real time (5+5 tries) | 20.0% | 96.7% | 40.0% | 40.0% | 52.5% | 93.3% | 100.0% |
| sonnet-5-5 | Batch (5+5 tries) | 40.0% | 95.0% | 20.0% | 20.0% | 26.7% | 95.8% | 100.0% |

## Reading notes (ours, descriptive)

- 5 Opus and 5 Sonnet answers per preset and shape are few: the intervals are wide (Wilson). Pooled over presets they are 25 each.
- Haiku's 1×24 lines-equal-to-key share is low (17%) while its local per-step accuracy is 79%: once a line is wrong, every later line
  differs from the key even when each step is applied correctly to the wrong balances. Its first wrong step is usually in the first six.
- Opus's three 1×24 misses: two are format failures under D-76 (`extra_line`: a step line written twice, at l15 base 8 and l16 base 3),
  both with the right final answer, which is why its final-answer view (96%) is above its whole-answer score (88%); one is a real slip
  (l16 base 4, first wrong line 6, wrong final answer).
- These puzzles used presets l14 to l16 at 24 steps; the main study now uses l14 at N steps (D-86), so these numbers are not the main
  study's. On the D-87 curve they appear as the labelled 24-step markers (`curve.py`, point 7).
