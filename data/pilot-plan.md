# Pilot sets and plan (D-36), proposed 2026-10-10

*Friday. For Edith to clear before the sets are written to `data/tasks/` with `--really-freeze` (Jarvis: D-36 covers
the pilot sets; the main-run sets come later, after the preset choice). Nothing here has made an API call. $0 spent.*

## The four sets

| Set id | Family and setting | Size | items.jsonl SHA-256 |
|---|---|---|---|
| pilot-digits-d4s-v1 | digits d4s | 10 base × 2 = 20 | bc86f1a6240ae645280b9746712270115bd873155707d6449605f5b2f1e3a18b |
| pilot-digits-d4p-v1 | digits d4p | 10 base × 2 = 20 | b8bb6f6e788544447c453957c84dae4082f95b94a9d88b5ac29759a8c5208694 |
| pilot-digits-d4-v1 | digits d4 (reference only, D-38) | 5 base × 2 = 10 | 2e65723dbcb55f03b13e3cace213a4d6b8401f28c3bb9b26194de359f7302e33 |
| pilot-code-c3b-v1 | code c3b | 4 base × 2 = 8 | 8b62ee060b96432687ac41375a163fc6d9d617eb9fe976ce956fa44e8d095685 |

Regenerate and compare, from the repo root on the commit each manifest names (the hashes depend on the generator
sources; `freeze --verify` warns when the code differs):

```
python3 -m harness.taskgen.freeze --family digits --setting d4s --set-id pilot-digits-d4s-v1 --n-base 10 --style d31 --split pilot --out SCRATCH/pilot-digits-d4s-v1
python3 -m harness.taskgen.freeze --family digits --setting d4p --set-id pilot-digits-d4p-v1 --n-base 10 --style d31 --split pilot --out SCRATCH/pilot-digits-d4p-v1
python3 -m harness.taskgen.freeze --family digits --setting d4  --set-id pilot-digits-d4-v1  --n-base 5  --style d31 --split pilot --out SCRATCH/pilot-digits-d4-v1
python3 -m harness.taskgen.freeze --family code   --setting c3b --set-id pilot-code-c3b-v1  --n-base 4  --style d31 --split pilot --out SCRATCH/pilot-code-c3b-v1
python3 -m harness.taskgen.freeze --verify SCRATCH/<set>                 # each set
python3 -m harness.taskgen.freeze --disjoint SCRATCH/<a> SCRATCH/<b>     # each pair
```

All four verify. Pairs I checked (d4s/d4p, d4s/d4, d4p/code) share no set id, seed or prompt. Set ids follow N43
(family, preset, split); none overlaps the free-test, wording-check or wording-check-code seeds.

## The plan (offline): `python3 -m harness.pareto.pilot plan --sets <the four set folders>`

```
{
 "calls": 688,
 "per_setup": {
  "digits/hm": 500,
  "digits/sm": 50,
  "digits/om": 50,
  "code/hm": 80,
  "code/om": 8
 },
 "batch_worst_case_usd": "38.9619590",
 "waves_if_nothing_were_spent_between": [
  574,
  114
 ]
}
```

- 688 calls: digits 500 Haiku-medium + 50 Sonnet-medium + 50 Opus-medium (50 puzzles = 20 + 20 + 10); code 80
  Haiku-medium + 8 Opus-medium (8 puzzles). All through Batch. `max_tokens` from `harness/pareto/limits.py`
  (Karen's B7: digits Opus and Sonnet 32K, Haiku 48K; code Opus 64K, Haiku 96K).
- The worst-case reservation at the **Batch price** is about $38.96 for all 688 calls, against the $30 pilot cap, so the
  guard splits the run into waves (574 + 114 calls if nothing were spent between them). In a live run the plan is made
  again after each wave from the money really spent, and the first Batch run stops after its first wave until the
  Console figure is recorded (Edith's R10).
- Expected spend is far below the reservation (Karen: about $7 / $17 / $29, low / central / high).
- A full **dry run** of all 688 calls (fake replies, no network, no key) goes through two dry batches and writes the call
  log, the manifest and the compact table: `python3 -m harness.pareto.pilot dry --sets ... --run-id pilot-dry-1 --out DIR`.
- **The 10-puzzle real-time check** (D-35/D-36: latency, plus batch-vs-real-time equivalence): `--rt-set` names the digit
  set whose first 10 puzzles (5 base × both shapes of pilot-digits-d4s-v1) get Haiku-medium ×5, Sonnet-medium ×1 and
  Opus-medium ×1 **in real time, streamed, at list price**: 70 calls (50 + 10 + 10), worst-case reservation about
  **$11.38** at list (Karen's expected cost: about $4.8 central). The batched side of the comparison is the pilot's own
  Batch calls on the same puzzles and setups (Haiku ×10, Sonnet ×1, Opus ×1), so no extra batched duplicates are needed
  (tell me if Karen's $4.8 assumed separate duplicates). It runs after the Batch waves.

## The smoke run (before the pilot): `python3 -m harness.pareto.smoke plan --set <pilot-digits-d4s-v1>`

- 3 real-time calls (Haiku, Sonnet, Opus, medium, streamed, list price, 16,000-token limit) on one 1×24 chain, plus 1 small
  Batch of 6 requests (Haiku ×4, Sonnet ×1, Opus ×1; on the 24×1 pieces and the chain). Worst-case reservation:
  real-time **$0.54** + batch **$0.29** = **$0.83** against a cap of $2. Expected cost: well under $1 (ours, unbacked).
- It confirms: the key works; effort, adaptive thinking and each model id reach the API and the reply names the model asked
  for; the streamed reply returns usage and a request id; a Batch is created, polled and its results parse; the guard's cost
  matches what the Console shows (the human records the Console figure; the first Batch run needs it before any second wave).
