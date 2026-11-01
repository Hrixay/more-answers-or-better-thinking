# Puzzle generator (prototype)

*Friday, 2026-10-10. Generator version `taskgen-proto-0.3`. **A prototype for teaching, not the final
design.** Nothing about Study 1's task family is decided; pre-registration item 1 rules on it. No API
calls, no dependencies beyond the Python 3.9+ standard library.*

```bash
python3 -m harness.taskgen.check          # self-test: all seven presets, 880 puzzles, ~45 s
python3 -m harness.taskgen.make_examples  # rewrites data/examples/ (deterministic)
```

Examples to read: [`data/examples/demo-4step.md`](../../data/examples/demo-4step.md) first, then
`data/examples/level-*.md`. The difficulty ladder d0–d4 is in `data/examples/presets.md`.

## What a puzzle is

Every value is a **digit string** (`0472`; the number of digits is a dial). The prompt prints a
**rulebook**, in up to four kinds of rule:

| Kind | Brief's step type | Example as printed (d0) | Work per step |
|---|---|---|---|
| arithmetic (`affine`) | modular arithmetic | `A: multiply by 81, add 683, then keep only the last 4 digits.` | one multiplication, one addition, mod 10ⁿ |
| digit table (`table`) | table lookup | `E: replace each digit using this table: 0→6, 1→3, 2→4, …` | n lookups in a 10-entry table |
| pair table (`pair`) | table lookup | `I: cut the value into pairs of digits, starting from the left (2 pairs), and replace each pair using this table: 00→38, 01→31, …` | n/2 lookups in a 100-entry table (d2 and up) |
| shuffle | permutation | `M: reorder the digits; the new value is the old 4th, 3rd, 1st, 2nd digits, in that order.` | one reordering of n positions |

Then it lists **sequences**: `1. Start at 8516. Apply A, L, H, K.` The model applies each sequence's
rules in order and ends with one line, `Final: v1, v2, …`.

A puzzle is **24 rule applications** (each printed rule used equally often, in shuffled order), cut
into *w* sequences of *d* steps: 24×1, 6×4, 2×12 or 1×24.

## How it is built (`puzzle.py`)

1. `seed + dials → rulebook`: multipliers coprime to 10, digit tables, pair tables and position orders
   that are derangements (every digit / pair / position moves). Each kind has its own random stream.
2. `seed → rule sequence`: 24 labels, balanced, shuffled, **no rule twice in a row**.
3. `(seed, w×d) → start values`: one fresh start value per sequence, from a stream named for the wiring.
4. Run the rules, record every step's input, output and one-line working (the **trace**), render the
   prompt.

**Same seed, any level → same rulebook and same 24 rule applications in the same order.** Only the cut
points and start values differ. So "only the wiring changes" holds by construction, item by item.

**Seeds.** `rng.py` is a SHA-256 counter-mode generator, so items regenerate byte for byte on any Python
version (Python's own `random` does not promise that). Item seeds come from `derive_seed(set_id, idx)`,
a hash, never `seed + idx`; a pilot set and a main set with different `set_id`s share nothing.

**Every rule is a bijection** (by construction, and checked algebraically for every generated rulebook).
So one wrong step always makes that sequence's final value wrong; a slip can't be "absorbed" by a later
step.

**No step can be skipped.** Shortcuts that exist only when steps are chained would make the sequential
levels easier than the parallel ones, so the generator rejects any rule order that has one:
1. A rule twice in a row, or two different rules that are each other's inverse, cancel when adjacent.
2. Rules that **commute** let non-adjacent steps cancel. A digit table and a shuffle always commute (a
   table changes digits in place, a shuffle only moves them), so `L, E, L` is just `E` when `L` undoes
   itself. Edith found this in round 1 (3.7–4.8% of puzzles at 6×4, 2×12 and 1×24, never at 24×1). With
   pair tables the same holds for a shuffle that moves whole pairs and keeps each pair's order; a shuffle
   that swaps digits inside a pair does not commute with a random pair table.

Instead of listing which kinds commute, `find_shortcut` (puzzle.py) **tests by simulation**: on fixed test
values it looks for steps that can be left out without changing the final value. It covers: a stretch of 2
or more consecutive steps with net effect "no change"; any 2 steps; any 3 steps; and, within any stretch,
all the steps of one kind. That covers every case above whatever commutes with what, including the new
rule kinds and wider values. The sequence is global and each chain is a slice of it, so this holds at every
level. Shuffles that undo themselves are used only when the inverse-pair rule leaves no other choice.

**Not covered** (stated so nobody assumes it is): leaving out 4 or more steps that are neither
consecutive nor all of one kind, and a pair of rules that merely compose into a different single rule
(composing them costs as much as applying them, so I don't count it as a shortcut). Forbidding same-kind
neighbours would not have fixed (2).

If the settings cannot satisfy these, the generator raises an error instead of quietly producing a
weaker puzzle. Examples that raise: 5 digits with pair tables (they need an even digit count), 3 digits
with 3 shuffles (only 2 exist), 8 shuffles of 4 digits (too few that aren't inverses), more printed rules
than steps, a multiplier range that doesn't fit the digit count, and a multiplier range whose square reaches 10ⁿ.
The last one matters because two arithmetic steps in a row equal one rule (multiply by a₁·a₂, add a
constant); if a₁·a₂ wraps past 10ⁿ the combined multiplier can be tiny or 1, an easier step that only the
chained levels can exploit. (Edith, round 1 of PR #2.) Nothing is skipped there, so the shortcut guard
cannot see it; the range limit is what prevents it.

## Difficulty dials

All dials are fields of `Params`, and **the step count stays 24 at every setting.** `PRESETS` names a
ladder; `generate(seed, w, d, PRESETS["d3"])`.

| Dial | Range | What it changes |
|---|---|---|
| `n_digits` | 2–9 | digits per value; longer multiplications, longer tables read, more positions to shuffle |
| `mult_min`, `mult_max` | `mult_max`² below 10ⁿ | size of the multiplier (2 → 3 → 4 digits) |
| `add_min`, `add_max` | below 10ⁿ | size of the addend |
| `n_affine`, `n_table`, `n_pair`, `n_shuffle` | 0 up to the step count, ≤ 24 rules in all | rules printed of each kind. A rulebook larger than 12 means each rule is used fewer times, so the model reads more and repeats less. At 24 rules every rule is used exactly once. When the rule count doesn't divide 24, the extra uses go to the kinds in turn, so every puzzle at a preset has the same number of steps of each kind (8 of each at d0 and d1, 6 of each at d2–d4 and d4s; d4p is 4 arithmetic, 4 digit tables, 8 pair tables and 8 shuffles) |
| `n_pair` > 0 | needs even `n_digits` | 100-entry tables on digit pairs: long lookups in a long printed table |

| Preset | Digits | Multiplier | Addend | Rules | What it is |
|---|---|---|---|---|---|
| d0 | 4 | 3–99 | 10–999 | 12 | the original prototype setting |
| d1 | 6 | 101–999 | 1,000–99,999 | 12 | wider values, bigger numbers |
| d2 | 6 | 101–999 | 10,000–999,999 | 16 | adds four 100-entry pair tables |
| d3 | 8 | 1001–9999 | 10⁶–10⁸−1 | 20 | 8 digits, 5 rules of each kind |
| d4 | 8 | 1001–9999 | 10⁶–10⁸−1 | 24 | 6 rules of each kind, each used once |
| d4s | 8 | 101–999 | 10,000–999,999 | 24 | d4's mix (6 of each kind) with smaller maths: 3-digit multipliers, 5–6 digit addends |
| d4p | 8 | 101–999 | 10,000–999,999 | 24 | d4s's small maths, but 4 arithmetic, 4 digit tables, 8 pair tables, 8 shuffles |

**d4s and d4p are candidates under D-25** (make the maths steps smaller, keep them in the mix, get
difficulty mainly from lookups and shuffles). **Neither has been tried on any model.** They are menu items
for the paid pilot, which counts slips by step kind and fixes the final settings. Both pass every guard
(see below), and the self-test checks each preset's exact per-kind step counts from a hand-written table
in `check.py`. The multiplier range 101–999 satisfies `mult_max`² < 10⁸ with room to spare (999² is under
10⁶). d0–d4 are unchanged, so `GENERATOR_VERSION` stays `taskgen-proto-0.3`.

(5 and 9 digits work and are tested; the ladder skips 5 and 9 because the step from 4 to 6 digits is
already the first big jump.) **None of these has been tried on a model, so how hard each one is for Haiku,
Sonnet or Opus is unknown.** The only data point is the free helper check on d0 (8/8 correct). Per-step
difficulty should go up with every rung, but I have no basis yet for where Opus would drop to 55–75%.

**Prompt length** (characters, mean of 30 seeds; full table in `data/examples/presets.md`):

| Preset | Rulebook | Prompt at 24×1 | at 1×24 |
|---|---|---|---|
| d0 | 1,180 | 2,057 | 1,432 |
| d1 | 1,239 | 2,164 | 1,493 |
| d2 | 4,495 | 5,420 | 4,749 |
| d3 | 5,634 | 6,607 | 5,890 |
| d4 | 6,716 | 7,689 | 6,972 |
| d4s | 6,699 | 7,672 | 6,955 |
| d4p | 8,233 | 9,206 | 8,489 |

Smaller maths barely changes the prompt (d4s is 17 characters shorter than d4, -0.2%): the multiplier and
addend are a small part of a rule line, and any saving is in the working the model writes, not in the
prompt. d4p is 1,517 characters longer than d4 (+20% at 24×1, +22% at 1×24) because it prints 8 pair
tables instead of 6; the 24×1 extra over 1×24 stays 717 characters.

Pair tables dominate the growth: each prints about 800 characters (100 entries), so d2 is already
4× the d0 prompt. Everything else grows slowly. Prompts stay well under 10,000 characters, far from any
context limit.

**Settings or levels that could make one level harder than another for a single model** (my reading;
not tested on any model):
1. *Prompt length at 24×1.* It always carries 23 more start values and sequence lines than 1×24
   (+625 characters at d0, +717 at d4). That is +44% of the prompt at d0 but only +10% at d4, so the
   imbalance shrinks up the ladder.
2. *The final line.* 24×1 must output 24 values of n digits in order; 1×24 outputs one. At d4 that is
   245 vs 15 characters. A model can lose its place in a 24-value list even if every value is right, and
   the answer-line format (design question 6) matters more at higher n.
3. *Pair tables and where the model looks things up.* Every level performs the same lookups, but in 24×1
   they are 24 independent lookups scattered through the answer, in 1×24 each uses the previous result.
   I expect no systematic difference, but it is the first thing I'd look at if 24×1 turns out harder than
   expected on d2–d4.
4. *At d4 every rule is used once,* so a 1×24 chain visits every rule once and the 24×1 version uses each
   rule in exactly one sequence. Same work, but a model working through 1×24 can't benefit from
   re-reading a rule it has used before; a 24×1 model can't either. No level difference expected.
No setting I tested makes the work unequal (same number of steps of each kind at every level, checked
on every puzzle).

**Each record** (`Puzzle.to_dict()`, see `data/examples/examples.jsonl`) holds the prompt, the answer, the
answer line, the full trace (for Study 5 and for the "script splits the task" control, which can send
one sub-step per call) and the generator version and parameters.

## The self-test (`check.py`)

- **Re-solves every puzzle from its prompt text alone**, with a separate parser and solver that share no
  code with the generator, and checks the result against the stored trace and answer. It also asserts that
  each rule line's own "last N digits" matches the header. The test corrupts one start value in a prompt
  and confirms the check fails.
- **On every puzzle**, from the parsed prompt, separately from the generator's own code:
  - every rule is reversible, every table, pair table and order is a permutation with no fixed point, and
    no two rules are the same or undo each other (checked by running one after the other on test values)
  - no steps can be left out (`check_no_shortcut`, brute force: re-runs the whole sequence with every pair
    and triple of steps removed, every stretch removed, and all the steps of one kind in every stretch
    removed). It is a separate implementation from `puzzle.find_shortcut`.
  - hand-made cases are caught by **both** implementations: `L,E,L` (table/shuffle commute), a pair table
    between two pair-moving shuffles, inverse shuffles with a table between; and non-problems are not
    flagged (`L,A,L`; a within-pair swap around a pair table). Removing the guard from the generator makes
    the self-test fail.
  - a sample of d0 rulebooks is also swept exhaustively over all 10,000 values
- The self-test runs every preset (100 d0 seeds, 20 of each other preset), each at all four levels.
- The expected number of steps of each kind is a hand-written table per preset (`EXPECTED_MIX` in
  `check.py`), not computed from the dials, so a wrong dial or a drifting mix fails the test; the test
  also fails if a preset has no entry.
- Settings that cannot meet the guards raise (see above), and the test checks that they do.
- Same number of steps of each kind at every level, determinism (regenerate and compare the JSON), no
  prompt collisions, chain wiring, rule balance, no back-to-back repeats, and a scan of the prompt for
  non-neutral words ("grade", "test", "evaluate", "score", "check", "benchmark", "judge", "mark", "exam",
  "quiz", "reasoning", "correct", "cipher", "encrypt", "password"; whole-word-start match).
- A draft scorer: `parse_final` reads the last `Final:` line; `score` returns all-or-nothing and
  per-sequence credit. It accepts the reference answer and rejects a one-digit slip. Per-sequence credit
  is 0 when the number of values is wrong, because a dropped value would shift all the later ones.

## Design problems the prototype caught

1. The first demo had rule C (swap 1st↔2nd and 3rd↔4th) applied **twice in a row**, which undoes itself.
   In the sequential wiring the model could skip both steps; in the parallel wiring they are two separate
   jobs. That breaks "equal work". Fixed (see above).
2. Edith's review found the subtler, non-adjacent version through the table/shuffle commuting. Fixed.

## Measured differences between levels (200 seeds, remeasured after the round-1 fixes)

| Level | Prompt (chars) | Answer line (chars) | Worked-step text in trace (chars) |
|---|---|---|---|
| 24×1 | 2,057 | 149 (24 values) | 991 |
| 6×4 | 1,609 | 41 | 992 |
| 2×12 | 1,513 | 17 | 992 |
| 1×24 | 1,432 | 11 (1 value) | 991 |

The work is identical; the **prompt is ~44% longer at 24×1** (24 start values instead of 1) and the
**final line is 14× longer**. Both are small in dollars (a few hundred input tokens), but listing 24
values in order is a format risk the sequential level doesn't have.

## Open design questions for the user (my view, labelled as mine)

1. **Is this the right task family?** Digits + three rule kinds keeps one value type, so chaining is
   natural and every step is exact. Alternative: letters/words, or Reasoning Gym's arithmetic and string
   generators for some steps. *My view: keep this shape; it is simple to explain and to check, and needs
   no outside code.*
2. **Difficulty and the ceiling.** *Partly answered:* the user ruled (D-16) to keep 24 steps and turn the
   per-step dials; the ladder d0–d4 above does that. A free helper check found d0 far too easy (8/8
   correct). *Still open:* which rung to start the pilot at. *My view: run two or three rungs (for example
   d2, d3, d4) on the separate pilot set and pick by the pre-registered calibration rule (item 2).*
3. **Scoring: all-or-nothing vs. partial credit.** All-or-nothing treats levels equally: every level
   needs all 24 steps right. Per-sequence credit does not: at 24×1 one slip costs 1/24, at 1×24 it costs
   everything. *My view: all-or-nothing as the primary measure; per-sequence credit only as a labelled
   secondary.*
4. **What does a majority vote vote on?** The whole answer line, or each sequence separately? Voting per
   sequence makes cheap-model voting much stronger on parallel puzzles and does nothing at 1×24. That is
   a real finding, not a bug, but it changes H1. *My view: whole-answer vote as the primary rule for every
   setup, per-sequence vote as a pre-registered secondary.*
5. **Matched or independent items across levels?** The prototype matches them: one seed gives the same
   rules and rule order at all four levels. That pairs the levels item by item (more power for the
   structure effect) but means 40 base puzzles, not 160 independent ones. *My view: matched.*
   **Cost of matching (Edith's point):** the four versions of a base puzzle are correlated, so the
   bootstrap must resample base puzzles and the mixed model needs `(1 | base puzzle)`. The brief's
   "±8 points with 160 paired items" assumed 160 independent items; matched, the real margin is wider,
   between that and the ±15 points of 40 items. The pilot can measure the correlation. Alternatives:
   160 independent puzzles (40 per level), or 160 base puzzles × 4 levels (about 4× the cost).
   **Not done on purpose:** reusing the 1×24 chain's intermediate values as the 24×1 start values. That
   would make the work identical value for value, but the 24×1 prompt would then contain 23 of its own
   answers as other sequences' start values.
6. **Answer format.** `Final: 4821, 0937, …` in order. Alternative: numbered (`1=4821 2=0937`), which
   survives a skipped value when scoring per sequence. *My view: plain list if all-or-nothing is primary.*
   The "short worked solution" instruction for Study 5 is a prompt item (item 4) and is not in the
   generated text.
7. **Same-kind steps in a row** (see above): allow, or forbid as a stricter guard. *My view: allow, and
   report it.* (This does not affect the cancellation guard, which is already on.)

Whatever difficulty settings the pilot tries (question 2) must each pass the same guards. The generator
raises if a setting cannot, and the self-test runs every preset.

## Limits of this prototype

- **Versioning:** the same seed gives different puzzles in `taskgen-proto-0.1`, `-0.2` and `-0.3` (the
  guards and the rule draws changed the sequences and rulebooks). From the first frozen set on, bump
  `GENERATOR_VERSION` whenever a seed's output changes.
- Seven difficulty presets (d0–d4 and the D-25 candidates d4s and d4p), none calibrated against any model.
- No frozen task set yet; `data/tasks/` stays empty until items 1 and 2 are ruled.
- Character counts, not token counts (counting tokens needs the API).
- Neutral wording: no words about grading, tests or evaluation; no security or biology topics. I avoided
  "code" and "cipher" for the values and tables, since they lean towards security.

## Code-tracing sketch (second family, D-20; not a reviewed generator)

`codetrace.py` is a **sketch** to test difficulty for free before a real generator is built (D-22). The
value is a list of numbers; a step is one printed Python function; a puzzle prints 24 functions, each
used once, in the same four-wiring scheme. The answer comes from executing the printed text. The
self-test is `python3 -m harness.taskgen.codetrace_check` (re-solves every puzzle from its prompt by
executing the printed code, plus a brute-force "no 2 or 3 steps can be left out" search). Results of the
free difficulty test, and the recommendation, are in `data/codetrace-free-test/README.md`.

Guards from `decisions/briefings/2026-10-10-study1-design-check/check-codetracing.md`: a value-changing
block between any two count-driven blocks; 24 distinct functions with wide constant ranges; no function
leaves a random list unchanged more than 3% of the time; no two functions undo each other; the shortcut
finder from `puzzle.py` run on the value-changing kinds and on the reordering kinds. Every block is a
bijection with a checked inverse, and the list never changes length.

| Dial | c0 (first sketch) | c1 | c2 | c3 | c4 | c5 |
|---|---|---|---|---|---|---|
| numbers per list | 8 | 16 | 20 | 24 | 32 | 40 |
| values | 0–99 | 0–99 | 0–999 | 0–999 | 0–999 | 0–999 |
| blocks per function | 1 | 2 (one value-changing, one reordering) | 2 | 2 | 3 (two value-changing, one reordering) | 3 |
| nested conditions | no | no | yes | yes | yes | yes |
| value-changing kinds | running total, add by parity/threshold, position map | same | + look-ahead sum | + neighbour-pair mix | as c3 | two-neighbour recurrence and a three-way branch on two neighbours, in place of the running total and add-by-parity |
| reordering kinds | one-branch swap, index gather, count-and-rotate | same | + nested branches | as c2 | as c2 | as c2 |

Free difficulty test of c1–c5 (Haiku, Sonnet, Opus helpers), results and a recommendation:
`data/codetrace-free-test/README.md`. Headline: Haiku is near 100% on separate pieces and about 10% on the chain
at c4; Sonnet and Opus are often stopped by a safeguard when asked for step-by-step working.


### The code-tracing generator under D-32 (built from the sketch)

`codetrace.py` is now the generator for the second family (digits stay main, D-32). Differences from the free-test
sketch (the sketch's outputs are unchanged, so `data/codetrace-free-test/` still regenerates byte for byte):

- `CTParams.validate()` raises for settings that cannot give a valid puzzle (lists too short for the swap blocks,
  `pairmix` with an odd length, an unknown block kind, `nested` kinds without `nested=True`, and so on).
- **Prompt styles** (`generate(..., style=...)`): `"legacy"` (the free-test wording), `"d31"` and `"d31-answer-only"`
  (the plain wording drafted for D-31, item 4 of the spec; `prompt_d31.py` is shared with the digit puzzles).
  `reference_reply`, `grade_d31` (whole answer, per piece, first wrong step, step-numbering problems) and `step_call`
  (the E3 prompt for one step) go with them.
- **Setting c3b** (24 numbers, three blocks per function) sits between c3 and c4, for the pilot's menu; the free test
  found Haiku's chain accuracy falling between c3 (2/2 chains) and c4 (1/10). Which setting the study uses is a
  pilot decision (D-36), not this module's.
- **`freeze.py`** writes, verifies and compares frozen task sets for either family: `n_base` base puzzles, each in both
  shapes (24×1 and 1×24, matched, D-24/D-28), base puzzle *i* seeded with `derive_seed(set_id, i)`. The writer
  never overwrites a folder, writes no timestamps (same inputs, same bytes), refuses to write under `data/tasks/`
  unless `--really-freeze` is given, and `--verify` re-solves every prompt from its printed text and checks the file
  hash, the seeds, and that both shapes of a base puzzle share the same functions in the same order. `--disjoint`
  proves two sets (pilot and main) share no set id, seed or prompt. **No set has been frozen.**

```bash
python3 -m harness.taskgen.codetrace_check 3   # self-test (about 1 minute)
python3 -m harness.taskgen.freeze --selftest   # frozen-set writer (about 5 seconds)
python3 -m harness.taskgen.freeze --family code --setting c3b --set-id scratch-demo --n-base 2 --style d31 --out /tmp/scratch-demo
```

Example prompts: `data/examples/prompts-d31/code-c3b-*.txt`, `code-step-call-e3.txt`.
