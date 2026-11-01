# E2 (Haiku-planned team) and H-pick8 (Haiku picker over 8): draft prompts

*Karen (Opus 5.5), 2026-10-12. DRAFT for Edith, then the user's yes to the words. These are extras (D-27
should-haves 3 and 4), so they come after D-42. No model calls.*

*Code: `research/models/team_prompts.py`. It holds the templates, the reply parsers and the checks. Rendered
for main-set puzzle 000 at both shapes, with stand-in results: `research/team-prompts/`.*

## What the locked spec fixes

- **E2** is "a stateless, Haiku-coordinated team" that "plans once and aggregates once" (D-27; spec §3, E2
  detail). It is stateless because Haiku's kept thinking could push a long chain past 100,000 input
  tokens, where the whole request is billed at 5×.
  - It serves H3: do teams that plan for themselves do worse than the script-split E3?
- **H-pick8** is a "Haiku picker over 8" (D-27). One Haiku-medium call reads 8 Haiku-medium answers to a
  puzzle and chooses one.
- **Banned words:** none in any new text (`prompt_d31.BANNED`). The answer formats are the approved ones
  wherever a reply is graded.
- **`max_tokens`:** 48,000 for every call. These are unmeasured setups (Amendment 1 §3).

## The prompts

Every call is one fresh message. Where a prompt quotes the puzzle, it uses the **approved prompt (D-77)
with only its closing paragraph replaced**. The new wording is only what follows.

### E2, call 1: the planner (one per puzzle)

*The puzzle (opening, Rules, Sequences), then for 1×6:*
> Do not apply the rules yourself. A helper will apply the rules of sequence 1 one at a time. For each
> rule, the helper sees only your instruction for that rule and the balances it starts from; it does
> not see this text. Write one instruction for each rule, in the order the sequence lists them. Each
> instruction must give the helper everything it needs: what a value means, the full rule, how ties are
> settled and the house rule. Start the instructions `Task 1:`, `Task 2:`, and so on up to `Task 6:`,
> one paragraph each, and write nothing else.

*For 6×1, the same text, except:* "A helper will handle each sequence on its own. For each sequence, the
helper sees only your instruction for it and that sequence's start balances; … Write one instruction for
each sequence, in order."

**Parsing.** The plan must have exactly `Task 1` to `Task N`, each once. Otherwise E2 fails on that
puzzle: it is counted wrong as deployed, and logged as `plan_failed`.

### E2, calls 2…: the helpers

> [the planner's Task k text]
>
> Balances
> [the balances]
>
> Follow the instruction above for these balances. Reply with one line, `Answer: v`, where v is the new
> balances.

**Which balances the helper gets:**
- for 1×6, the start balances for task 1, then the team's own agreed result for task k−1;
- for 6×1, that sequence's start balances.

This is the E3 reply form, and its parser.

### E2, last call: the aggregator (one per puzzle)

*The puzzle (opening, Rules, Sequences), then for 1×6:*
> Helpers have applied the rules of sequence 1 one at a time, each starting from the result before it.
> Their results, after each rule and its house rule, in order:
> Place 1, rule E: [..]
> …
> Place 6, rule F: [..]
>
> Use these results to write your reply. Where a result looks wrong to you, work that rule out again
> yourself and carry your own balances forward from there. *[then the approved 1×6 closing, word for
> word]*

*For 6×1:* "Helpers have applied each sequence's rule, then the house rule, to its start balances. Their
results: Sequence 1, rule E: [..] … Use these results to write your reply. Where a result looks wrong to
you, work that sequence out again yourself." *[then the approved 6×1 closing]*

The aggregator's reply is in the official format, so **E2 is graded exactly like any other arm** (D-76,
D-90).

### H-pick8 (one call per puzzle)

*The puzzle (opening, Rules, Sequences), then:*
> Here are 8 replies to the puzzle above, written separately.
>
> Reply 1
> [Haiku-medium sample 1's visible text, as returned]
> …
> Reply 8
> […]
>
> Choose the reply whose balances are right. Reply with one line, `Pick: k`, where k is the number of
> the reply you choose.

**What counts as the arm's answer:**
- It is **reply k itself**, graded exactly as that sample was. The picker copies nothing, so it can't make
  a copy slip.
- If there is no valid `Pick:` line (the last one wins; it must be 1–8), the arm gives no answer and is
  counted wrong as deployed.
- An empty, refused or truncated sample is shown as "(no reply)".

## Design choices for Edith and Jarvis (my recommendation first)

1. **E2 helpers vote per task with lead-by-2, cap 9, the same rule as E3.**
   - Then E2 differs from E3 only in what H3 asks about: who writes the instructions (Haiku vs the script)
     and working from the team's own results, not the correct ones.
   - **The alternative is one helper per task.** It is cheaper, but then E2 and E3 also differ in voting,
     which muddies H3.
   - Friday's build plan already assumes the voting version.
2. **The aggregator may redo a step** (as drafted), because that is what makes it a coordinator rather than
   a pipe.
   - The paper reports, free, how often the final answer differs from the helpers' chain.
   - **The alternative is copy-only.** Then a script could do the job, and the aggregator only adds copy
     slips.
3. **A failed task in the chain.** If no helper gives a usable result after 9 draws, the later helpers
   can't start. The aggregator then sees "(no result)" for that place and every later one, and may fill
   them in itself.
4. **Which 8 samples the picker sees:** Haiku-medium samples 1–8 of each puzzle's 40, by sample index, in
   that order. These are fixed before any data. The fixed order is stated, and position effects are not
   studied.
5. **E2 and H-pick8 at both shapes, on all 160 puzzles**, as costed (D-27).

## Edith r1 (2026-10-12): all five choices ACCEPTED, two parser fixes done

*`ops/reviews/2026-10-12-e2-hpick8-drafts-r1.md`.*

**Fixes, done:**
- **R1-1:** the plan parser now accepts:
  - a `#` heading;
  - the label alone on its line, with the text on the next lines;
  - `:`, `.`, `-` or a dash after the label.

  A label followed by plain prose ("Task 2 depends on …") stays prose. An empty task fails the plan.
- **R1-2:** the pick parser accepts `Pick: Reply k` and one trailing `.` or `,`.
- **Tests:** `research/models/test_team_prompts.py`, 10 tests, all pass.

**Pre-stated now, before any data.** These are free counts from logged data, with no new calls.
- **E2, the aggregator.** How often its final answer differs from the helpers' chain. Of those changes, how
  many turned a wrong chain right, and how many turned a right chain wrong.
- **E2, failed tasks.** How many puzzles had a task with no result, per shape. Also how many plans failed
  (`plan_failed`), per shape.
- **H-pick8**, read beside two numbers computed over the same samples 1–8 of each puzzle from the main run:
  - **vote@8:** the Haiku vote rule (D-76 official, the D-33 tie rule) over samples 1–8;
  - **any@8:** at least one of the 8 is right, the ceiling a perfect picker could reach.
- **The at-cap rule for E2's helpers is E3's:** the unique most common answer wins, and a tie gives no
  result.

**The methods text must say:**
- the planner was told what each instruction must contain (what a value means, the full rule, how ties
  are settled, the house rule). That is a help to E2;
- the picker always sees samples 1–8 in sample order, and position effects are not studied.

**When it runs:** a later, separate run after main-l14n6-1, with its own clearance and Console reading.
- H-pick8 reads that run's samples.
- E2 runs each task k of every puzzle in one Batch round, at both shapes together. That is about 14
  rounds typically, at an expected cost of about $3 (Edith).

## The wording check

**The scope (Edith):** the planner, one aggregator per shape, and the picker. It must also confirm that
the aggregator replies in the official format even though its input lists `Place k, rule X` lines.

**My proposal, waiting on Jarvis's OK:**
- **Haiku helpers only.** These prompts only ever go to Haiku.
- **Puzzles:** ladder l14n6 base 002, both shapes, outside the main sets.
- **E2 end to end, once per shape:**
  - 1 planner;
  - its parsed tasks to 6 helpers, one draw each, chained at 1×6;
  - 1 aggregator.
- **H-pick8 once per shape,** fed the ladder's own API Haiku-medium replies 1–8 to that puzzle. Those are
  already collected, so no new API call.
- **About 18 runs,** stopping at the first block.

## Free check result (2026-10-12): 0 blocks in 18 runs, every reply in the exact format

- **Plans:** both parsed.
- **Aggregators:** both replied in the official format. The `Place k` list did not leak into the reply,
  so the list stays as it is.
- **Pickers:** both replied `Pick: k`.
- **The run:** Haiku helpers only, on ladder l14n6 base 002 at both shapes, with Jarvis's OK.
- **Detail:** `research/wording-check-e2-hpick8/`.
- **Edith CONFIRMED it (r2, 2026-10-12;** the r2 section of
  `ops/reviews/2026-10-12-e2-hpick8-drafts-r1.md`). She rebuilt all 18 prompts and graded both
  aggregators with the official grader: format ok.
- **Next:** the user's yes to the words (Jarvis).
