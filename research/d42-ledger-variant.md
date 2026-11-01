# The D-42 prompt variant for the ledger family (draft for Edith)

*Karen (Opus 5.5), 2026-10-12. DRAFT: nothing here is decided. No model calls, and `.env` was not opened.*

*The route, as for the digit variant:*
1. *Edith clears the text.*
2. *A small free wording check runs: Opus, Sonnet and Haiku helpers; stop at the first block; no rephrasing
   or retries. These are model calls, so they need Jarvis's OK.*
3. *The user says yes to the words.*

*Code: `research/models/d42_variant.py` (the reference renderer and its checks). Rendered pairs:
`research/d42-variant/`.*

## What D-42 asks for, and what this draft does

- **D-42 (a), ruled.** "A slightly reworded prompt with the same meaning and the same banned-word rules
  (it never mentions grading, tests or evaluation), run with Haiku-medium ×10 tries on 40 main-set
  puzzles (20 base × 2 shapes)". Its results are reported as robustness, outside the confirmatory tests.
- **The digit variant (D-52) set the pattern, and this draft follows it.** Only the **opening paragraph**
  and the **closing paragraph** are reworded.
  - The `Rules` block, the `Sequences` block, the headings and the reply format are byte-identical: the
    `1.1 = v` step lines and the `Answer:` line.
  - So the same parser and grader score both wordings, and the frozen puzzles render either way.
- **One difference from the digit case.** In the ledger, the opening paragraph also holds the **house rule**.
  This draft rewords it too, keeping every condition, because the house rule is part of the opening.
  - **A narrower option, if Edith prefers:** keep the house-rule sentences word for word and reword only
    the rest. That is safer on meaning, but tests less of the wording.
- **Scope.** The main set's form only: a house rule, no decoy rules, 1×6 and 6×1.

## Side by side (main set, puzzle 000; numbers as rendered)

**Opening, approved (D-77):**
> Every value here lists the balances of 6 budget lines, in whole units, in this order: Rent, Payroll,
> Supplies, Reserve, Travel and Training. A value looks like [5115, 4085, 3424, 5116, 2910, 5411], which
> means Rent 5115, Payroll 4085, Supplies 3424, Reserve 5116, Travel 2910 and Training 5411. A balance
> never goes below 0. Each rule below says what happens to the balances. When a rule picks the line with
> the largest or the smallest balance and two or more lines are tied, it picks the one that comes first
> in the order above. House rule: straight after every rule, as part of the same step, if the line with
> the smallest balance is below 3600, move 450 units to it from the line with the largest balance, or all
> of that line if it holds fewer. The house rule acts at most once per step, always after that step's
> own rule, and does not act again on its own result. If the largest and the smallest line are the same
> line, nothing moves. The balances you write for a step are the ones after the house rule.

**Opening, variant:**
> Each value is a list of the balances of 6 budget lines, in whole units, always in this order: Rent,
> Payroll, Supplies, Reserve, Travel and Training. For instance, [5115, 4085, 3424, 5116, 2910, 5411]
> means Rent 5115, Payroll 4085, Supplies 3424, Reserve 5116, Travel 2910 and Training 5411. No balance
> can drop below 0. The rules below describe how the balances change. If a rule picks the line with the
> largest or the smallest balance and several lines share that balance, the rule picks whichever of them
> is listed first in the order above. House rule: immediately after each rule, within the same step, look
> at the line with the smallest balance; if it is below 3600, it receives 450 units from the line with
> the largest balance, or the largest line's whole balance if that is less than 450. The house rule runs
> no more than once per step, always after that step's rule, and is not applied again to its own
> outcome. If one line is both the largest and the smallest, nothing moves. Each step's balances, as you
> write them, are the balances after the house rule.

**Closing for the chain (1×6), approved:**
> Apply the rules of sequence 1 in the order listed, each followed by the house rule, each to the
> balances that the rule before it and its house rule gave. Reply with the balances after each rule and
> its house rule, one per line, written `1.1 = v`, `1.2 = v`, and so on (the first number is the
> sequence, the second is the rule's place in it). Then end with one line, `Answer: 1 = v`, giving the
> balances the sequence ends at.

**Closing for the chain (1×6), variant:**
> Go through the rules of sequence 1 in the order listed, applying the house rule after each one. Each
> rule starts from the balances that the previous rule and its house rule produced. After each rule and
> its house rule, write the balances on their own line, as `1.1 = v`, `1.2 = v` and so on (the first
> number is the sequence; the second is the rule's place in it). Finish with a single line,
> `Answer: 1 = v`, containing the balances the sequence ends on.

**Closing for the pieces (6×1), approved:**
> Each sequence is one rule applied to its start balances, followed by the house rule, and the sequences
> are separate. Reply with one line, `Answer: 1 = v, 2 = v, ..., 6 = v`, giving the balances each
> sequence ends at, in order.

**Closing for the pieces (6×1), variant:**
> Every sequence is a single rule applied to its start balances and then the house rule, and the
> sequences have nothing to do with each other. Reply with one line, `Answer: 1 = v, 2 = v, ..., 6 = v`,
> containing the balances each sequence ends on, in order.

The two closings use the same rewording as the approved digit variant (D-52), adapted for the house rule.

## Meaning, clause by clause (my reading; for Edith to confirm)

| Approved | Variant | Same meaning? |
|---|---|---|
| lists the balances … in this order | a list of the balances … always in this order | yes |
| A value looks like X, which means … | For instance, X means … | yes |
| A balance never goes below 0 | No balance can drop below 0 | yes |
| Each rule below says what happens | The rules below describe how the balances change | yes |
| tie → the one that comes first in the order above | tie ("several lines share that balance") → whichever is listed first in the order above | yes. It applies to every rule's pick, the house rule's included, as in the approved text |
| straight after every rule, as part of the same step | immediately after each rule, within the same step | yes |
| smallest below t → move a to it from the largest, or all of that line if it holds fewer | smallest below t → it receives a from the largest, or the largest line's whole balance if that is less than a | yes. "That line" now names the largest line explicitly, which removes a possible misreading |
| acts at most once per step, always after that step's own rule, does not act again on its own result | runs no more than once per step, always after that step's rule, is not applied again to its own outcome | yes |
| largest and smallest are the same line → nothing moves | one line is both the largest and the smallest → nothing moves | yes |
| the balances you write for a step are the ones after the house rule | each step's balances, as you write them, are the balances after the house rule | yes |
| chain: apply each rule plus the house rule to what the one before gave; write after each; end with the Answer line | the same, reworded; the format strings are unchanged | yes |
| pieces: one rule plus the house rule each, separate; one Answer line | the same, reworded; the format string is unchanged | yes |

## Checks run (`python3 research/models/d42_variant.py`)

**All 160 main-set prompts pass.**
- The approved opening and closing rebuild exactly from the generator's own templates, which proves the
  parameters are read right.
- The Rules and Sequences blocks are byte-identical.
- No word from `prompt_d31.BANNED` appears (I checked case-insensitively, which is stricter than the
  generator); "For instance" avoids "example", which matches `\bexam`.
- No `$`.
- The reply-format strings are present.
- The variant is 5 to 8 words longer than the approved text.

## How this changes anything (in plain words, as the user asked at D-52)

- It doesn't change the puzzle, the answers or how they are marked. Only the words around the rules are
  different.
- If Haiku's accuracy on the 40 puzzles moves noticeably between the two wordings, our results depend
  partly on phrasing, and the paper says so.
- If accuracy stays about the same, that supports the main results not being an artefact of one wording.

## For Friday, after Edith clears it

- Add `style="d31-variant"` to `harness/taskgen/ledger.py`, using the same two functions as
  `research/models/d42_variant.py`.
- Run the renderer as its test: every variant must rebuild from the frozen items, with the middle
  byte-identical.
- The 40 D-42 puzzles are 20 base × 2 shapes from the main set.
- **The 40 puzzles are pinned** (Edith, 2026-10-12, before any main-run data). They are the **first 20 base
  ids of `main-ledger-l14n6-v1` in frozen order (base 000–019), at both shapes**.
- **The run:** Haiku-medium ×10 on each, at the Haiku-medium limit of 5,000 tokens.

## Status

- **2026-10-12: Edith CLEARED the wording for the free check**
  (`ops/reviews/2026-10-12-main-runner-r1-and-d42-wording.md`).
  - She keeps the **full variant**, house rule included: "it's the spirit of D-42, and the narrower one
    tests less."
  - So the narrower option above is dropped.
- **Jarvis OK'd the free wording check:**
  - Max-plan helpers only;
  - puzzles outside the main set and its ext40;
  - it checks understanding, refusals and format, and is not a performance read (D-84).
- **The free wording check is DONE (2026-10-12): 0 blocks in 9 runs** (Opus, Sonnet and Haiku helpers,
  3 each).
  - The puzzles were 3 ladder l14n6 puzzles, outside the main sets.
  - Every reply was in the exact format, and each helper used Read only.
  - The rough read: all 9 right. It is not a performance read.
  - Detail: `research/wording-check-d42-ledger/`.
- **Next: the user's yes to the words** (Jarvis puts it to them). The final wording is the
  "variant" text above.
