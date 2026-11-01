# Study 1b specification: Haiku at max effort against Opus at medium effort, on fresh puzzles

*Karen (Opus 5.5), 2026-10-13. Study 1b's pre-registration, frozen at the tag `prereg-lock-4` after Edith's review. The only change
allowed after the tag is the price-date commit (§9, step 4).*

*The user's rulings (D-96, "I will go with whatever whatever you are recommending"):*
- *go;*
- *a **5-point** margin is primary and 10 points is secondary;*
- *the **effort sweep**, with Sonnet and Opus at every effort level at 6 steps;*
- ***plus the 12-step point**.*

*Edith's plan review, F-1 to F-7, is applied (`ops/reviews/2026-10-13-study1b-plan-and-groupC.md`), and so is her procedure advice
(`ops/reviews/2026-10-12-followup-procedure-advice.md`). The plan this replaces is `research/study1b-plan.md`.*

*Names follow the glossary (D-98, `decisions/glossary.md`): length sweep, effort sweep, trial round, top-up run, chain and
pieces. Set ids, run ids, tags and file names keep their old spelling.*

*No API calls were made to write this. Every number from Study 1 is cited to `data/main/main-l14n6-1/analysis.json` (43d18eed…).*

*Every "item N" below is an item of `research/reporting-definitions-main.md`, Study 1's reporting definitions (final at 93334b8),
named at each use and applied to 1b's arms and sets.*

---

## 1. Why this study exists (F-1 wording)

In Study 1's **main run** (N = 6, 80 base puzzles × 2 shapes), **Haiku 5.5 at max effort**, an exploratory arm with 3 tries per puzzle, came
close to **Opus 5.5 at medium effort** at about a tenth of the cost per answer:

| | Chain (1×6) | Pieces (6×1) |
|---|---|---|
| Haiku-max, single try | 97.5% | 95.0% |
| Opus-medium | 96.25% | 100% |

It was found after looking at the data and was not one of Study 1's tests. So **Study 1b tests it confirmatorily on fresh puzzles**:
- at **16 steps**, where Haiku at medium effort collapses (18% in the length sweep) and Opus stays near 100%;
- with a **replication at 6 steps**.

Study 1b is a separate study with its own family of tests. **Its data are never pooled with Study 1's data, and its tests never pooled
with Study 1's tests.**

## 2. Puzzles: fresh frozen sets (F-2)

| Set (frozen at lock 2, ledger-0.5, commit a8f0acd) | Items | Use |
|---|---|---|
| `main-ledger-l14n16-v1` (items_sha256 0bf12afc…) | 80 base × 2 shapes | B1, B2; the effort sweep at 16 steps |
| `ext40-ledger-l14n6-v1` (1f342a6c…) | 40 base × 2 shapes | B3; the effort sweep at 6 steps |
| `main-ledger-l14n12-v1` (9aefe340…) | 80 base × 2 shapes | The 12-step point on the Length curve (descriptive) |

- **Never sent.** The lock holds one canonical record, plus earlier records as support (Edith Part 5; lock-4 audit A7, A13, A22):
  - **The canonical check** is `harness/pareto/neversent.py` as frozen in the tag (Edith CLEAN at ff10fd3, on main as e89f804; any
    later change, such as audit A5's refusal to run when it finds no call logs, is Edith-checked before the tag). It matches every
    test item against every run's call log by item id and by prompt hash, and against every other file under `data/` and
    `research/` by prompt text. It has a positive control.
  - **The canonical record** is that check re-run from the lock-4 tree: `data/plans/study1b-never-sent-lock4.json`, with its
    positive control (`main-ledger-l14n6-v1` and `ladder-ledger-l14n16-v1`, which must read as sent) in
    `data/plans/study1b-never-sent-control-lock4.json`. Each record names the commit it ran on, names every folder it searched
    and labels each scanned file by its folder, and gives every scanned `calls.jsonl` its SHA-256 and line count. The runs
    scanned must match the spend log's list of runs (8 today). The records are made after this spec is committed, so their
    SHA-256 values are given in the `prereg-lock-4` section of `ops/lock/LOCK-MANIFEST.md`, inside the tag, not here.
  - **Earlier records, kept as support:** the same check's first output (`data/plans/study1b-never-sent.json`, ff10fd3, 945 other
    files); its first version (`Hrixay/friday-neversent` 1a739f4, `data/` only); and mine, `research/study1b-never-sent-check.json`
    (2026-10-13), which covers the 78 free-check files under `research/`.

  Mine found:
  - **400 items**;
  - every call log was scanned: 8 files, 25,072 records;
  - matched **by item id: 0; by prompt hash: 0** (the hash is SHA-256 of "\n" + prompt, as `request.prompt_text` builds it);
  - by prompt text against 78 free-check files: 0.

  Edith's own id grep also found 0. The lock-2 all-pairs check (378 pairs, 0 overlaps) shows these sets are disjoint from every used
  set.
- **They were generated and frozen before any Haiku-max data existed.** The paper says so.
- **Their history, disclosed** (Jarvis's provenance check, 2026-10-13):
  - all three sets come from generator ledger-0.5 (sources hash bcce20c2). They were frozen at 06:25Z on 10-12, inside lock 2 and
    lock 3, and are byte-identical at HEAD;
  - `main-ledger-l14n16-v1` and `main-ledger-l14n12-v1` were **Study 1's candidate main sets** at 16 and 12 steps (lock-3
    LOCK-MANIFEST), unused only because the length sweep picked N = 6;
  - `ext40-ledger-l14n6-v1` was **Study 1's D-72 add-40 reserve** at N = 6, unused because D-72 did not fire;
  - a further never-sent 16-step set, `ext40-ledger-l14n16-v1` (40 base), stays a spare and is not used.
- **The wording on "fresh"** (for the paper):
  - Only the **test sets** are fresh. The **trial round** (§7) sends **already-used** length-sweep puzzles, unscored, to set token limits. So the paper
    never says "everything in Study 1b is fresh".
  - Say "**never sent to any model under test, and never attempted by a free helper**", not "never seen".
    - **"A model under test" means a call made in a study run:** Study 1's main run, Study 1b's run (`study1b-1`), the top-up run,
      or any earlier run in the spend log. Only those calls are scored.
  - **Which items were shown in helper sessions.** Jarvis's scan checked every Pareto session transcript, in all 4 project folders
    under `~/.claude/projects`, for answer-key fragments of the three sets: the first three numbers of every answer line, matched by
    code, with only counts printed.
    - The script is `decisions/briefings/2026-10-13-lock4-audit/exposure_scan.py` (SHA-256 44ef2659…). Its run at 2026-10-12
      21:45Z (746 transcripts; output `exposure-scan-20261012T2145Z.json` in the same folder, SHA-256 5b4fca85…) found the same
      bases as the first scan behind D-97, and no others.
    - It found **three exposed test bases**:
    1. `ext40-ledger-l14n6-v1` **base 000** (pieces): Friday's build session (287c65d6; truncated fields, including the start of the
       answer key; Friday confirmed), and Jarvis's provenance-check helpers (session 57b69095, workflow wf_29637722-08d).
    2. `ext40-ledger-l14n6-v1` **base 003** (both shapes): session 3c8fe7e9 (Edith's review session; confirmed by Edith). At
       10:30:04Z on 10-12, a broad `git grep … | cut -c1-260` printed `items.jsonl` lines 7 and 8 (base 003, both shapes, answers first).
       Also shown in Jarvis's helpers.
    3. `main-ledger-l14n16-v1` **base 000** (pieces, the full answer): Jarvis's provenance-check helpers only.

    `main-ledger-l14n12-v1` and every other base: 0 hits.
  - **What those sessions were.** They were Claude Code work sessions running Opus, Sonnet or Haiku 5.5, separate from the study
    runs. None was a call in a study run, none shares memory or context with the Batch calls, none was asked to solve the items, and
    nothing in the study was tuned on them.
  - **The same script is re-run just before the tag,** and its dated output is committed inside the tag. If it finds a new exposed
    base, this section and the driver's list of exposed bases are updated before the tag. After the tag, any new exposure goes in a
    dated deviation note.
  - **The three exposed bases stay in the tests as frozen.** Their exposure is disclosed.
    - **Sensitivity (appendix):** the whole B1–B3 family re-run without the exposed bases:
      - **B1 and B2 over the 79 bases other than `main-ledger-l14n16-v1` base 000;**
      - **B3 over the 38 bases other than `ext40-ledger-l14n6-v1` bases 000 and 003;**
      - the same B, seeds (`derive_seed(20261013, test)`), margins (−5 primary, −10 secondary) and Holm;
      - labelled "sensitivity: exposed bases excluded". It never replaces the primary readings.
      - The error-rate ratios for B1–B3 are reported the same way.
    - The descriptive outputs (§6) are not re-run without them.
    - (This replaces Edith's Part 8 line; Edith accepted it in Part 9. The user's yes covers keeping the three exposed bases with this
      check.)
- **24 steps is not part of Study 1b.**
  - The only never-sent 24-step sets (`ext40-ledger-l14/l15/l16-v1`) were frozen at lock 1, not in lock 2's list. Using them would
    add a second lock's sets and a length the power and budget here don't cover.
  - Their wording is not the reason: Jarvis's check found it matches Study 1's.

## 3. Arms and settings

Batch only. The settings follow Study 1 (D-31 prompts, D-76/D-90 scoring) unless stated.

| Set | Arm | Model and effort | Tries per item | `max_tokens` |
|---|---|---|---|---|
| N = 16 | **hx** | Haiku 5.5, max | 10 | §7 rule, with a floor of 96,000 |
| N = 16 | **om** | Opus 5.5, medium | 2 | 9,000 (1.5 × the length sweep's largest at 16 = 5,474, rounded up) |
| N = 16 | ho, hl, hm, hh, hxh | Haiku off (thinking disabled at medium, as Study 1's `ho`), low, medium, high, xhigh | 5 each | hm 14,000 (1.5 × the length sweep's 9,120); the others from §7 |
| N = 6 | **hx** | Haiku, max | 10 | 30,000 (1.5 × Study 1's largest, 19,580) |
| N = 6 | **om** | Opus, medium | 2 | 4,000 (Amendment 1) |
| N = 6 | ho, hl, hm, hh, hxh | Haiku off, low, medium, high, xhigh | 5 each | ho 4,000, hl 7,000, hm 6,000 (1.5 × Study 1's largest); hh and hxh from §7 |
| N = 6 | sl, sm, sh, sxh, sx | Sonnet low, medium, high, xhigh, max | 1 each | sl 3,000, sm 3,000 (Study 1); the others from §7 |
| N = 6 | ol, oh, oxh, ox | Opus low, high, xhigh, max | 1 each | ol 4,000 (Study 1); the others from §7 |
| N = 12 | hx | Haiku, max | 10 | §7 rule, with a floor of 96,000 |
| N = 12 | om | Opus, medium | 1 | 7,000 (1.5 × the length sweep's 4,303) |

**Floors for the §7 rule** (each arm's floor is the same model's measured medium limit at that length, unless stated):
- Haiku at 6: 6,000; at 12: 11,000; at 16: 14,000. Haiku-max at 12 and 16: 96,000.
- Sonnet at 6: 3,000.
- Opus at 6: 4,000.

**The arms set by §7** (no measurement yet):
- at 16: ho, hl, hh, hxh and hx;
- at 12: hx;
- at 6: hh, hxh, sh, sxh, sx, oh, oxh and ox.

Every other arm uses the 1.5 × measured value in the table.

**Notes:**
- Haiku's thinking-off is allowed only at effort high or below (Anthropic's effort page, checked 2026-10-13), so `ho` runs at medium,
  exactly as in Study 1.
- Opus can't turn thinking off.
- Sonnet 5.5's default effort is **high**; Study 1's "Sonnet-medium" ran one level below it. The methods say so.

## 4. The confirmatory tests: B1, B2, B3 (F-3)

**The score** is Study 1's official score: the whole answer under D-76 with D-90's repeat rule. Refusals, truncations, unparseable and
missing tries count as wrong (as_deployed). The two left-out views (refusals out, truncations out) are computed as in Study 1 (D-68
F3). For B1–B3, the completeness rule below comes first: a test with any missing Haiku-max or Opus-medium try is not read.

**Shape pooling (a change from Study 1, stated in the methods):**
- each base puzzle's score is the **mean over its two shapes** (chain and pieces);
- Study 1 tested each shape separately. 1b pools them because, near the ceiling, pooling halves the variance of each puzzle's
  difference and keeps the family at three tests;
- the per-shape results are reported as description.

**Per-base scores (in points):**
- **Haiku-max single try**, h_b: for each shape, the share right of its **10 designed tries** (a missing try counts as wrong); then the
  mean over the two shapes.
- **Opus-medium**, o_b: for each shape, the share right of its **2 designed tries**; then the mean over the two shapes.
- **The Haiku-max vote** (B2), v_b: for each shape, the exact vote@k over its 10 tries.
  - The method is `votes.vote_accuracy_at_k`, as in D-33: an unreadable try is a vote for nothing, and ties count at 1/m.
  - Then the mean over the two shapes.

**B2's k** (F-3):
- **k = floor(Opus-medium's mean list cost per try ÷ Haiku-max's mean list cost per try)**, on the N = 16 set.
  - Both are from **cost-only rows**: custom_id, model, effort, kind and the list cost (`research/reporting-definitions-main.md`
    item 9a, "List cost of one call"); never answers.
  - The ratio uses Opus's cost per *try*, because the claim compares one Opus answer with a vote.
- **k is computed and committed, with its SHA-256 in LOG, before the analysis driver runs.**
- **It is held to the 10 tries drawn.** If the cost ratio is above 10, k = 10, labelled "for less than Opus's price" (as D-33
  item 4).
- **If the ratio is below 1, B2 is not run** and keeps its Holm place with p = 1.
- **B2's k-sensitivity: none.** Study 1's k-sensitivity rows (`research/reporting-definitions-main.md` item 8b; item 8a sets
  Study 1's k values) are not carried over. The k = 1–10 vote curve (§6) is the only k description.

**The three tests:**

| Test | Difference per base puzzle | Set |
|---|---|---|
| **B1** | h_b − o_b | N = 16, 80 base |
| **B2** | v_b − o_b | N = 16, 80 base |
| **B3** | h_b − o_b | N = 6, 40 base |

**The analysis:**
- **The family:** `bootstrap.run_family` over B1–B3. It uses the paired BCa bootstrap over base puzzles, 10,000 draws, **base seed
  20261013**, and per-test seeds `derive_seed(20261013, "B1"|"B2"|"B3")`. It is one-sided, α = 0.025, with **Holm across these three
  only**.
- **The primary reading, at margin 5** (`margin = −5.0`):
  - "no worse than Opus by more than 5 points" if Holm declares it;
  - "worse by more than 5 points" if the two-sided 95% upper end is below −5;
  - otherwise **"inconclusive"** (`bootstrap.three_way`'s name; the prose templates in §10 say "could not show").

  "No worse" counts as a headline result only if it holds in all three views (D-68 F3).
- **The secondary reading:** the same family at **margin 10** (`margin = −10.0`), for comparability with Study 1.
- **Beside every test:**
  - the **error-rate ratio**, by the rules of `research/reporting-definitions-main.md` item 1 ("The error-rate ratio"):
    - +∞ draws are kept, with B = 10,000 and seed `derive_seed(20261013, f"{test}:error_ratio")`;
    - when Opus has 0 errors, the two-sided 95% Clopper–Pearson bound is computed on **0 of Opus's designed tries in the test**: 320 at
      N = 16 (80 base × 2 shapes × 2 tries) and 160 at N = 6;
  - **the cost**, by `research/reporting-definitions-main.md` items 9a and 9b (list price; B5-free refusals at $0): mean dollars per
    answer for each arm, with the ratio stated as "about 1/k of the cost, k measured".
- **Per shape:** h, o, v and d for each shape, with a cluster bootstrap over base puzzles (2,000 draws, seed 20261013). Descriptive.

**A stopped or incomplete run (lock-4 audit A1; the user's ruling D-103(F), in Edith's wording).**
- **A confirmatory test (B1, B2 or B3) is completed only if every designed try of both its arms has a final record when the driver
  runs.**
  - A refusal, a truncation, an unparseable answer, or a record of kind empty, unexpected_stop or error is final (and wrong).
  - A try with no final record after Study 1's retry and resubmit rules is `missing` (`research/reporting-definitions-main.md` item
    16).
  - **Zero missing tries are allowed.** The runner re-sends errored and expired calls until they are final, so a missing try means
    the run did not finish.
- **A test that is not completed reads "not completed".**
  - It gets no reading ("no worse", "inconclusive" or "worse") in any view or at either margin.
  - It keeps its Holm place with p = 1, so the other tests' corrections don't change.
  - B1 and B2 use the same arms on the same N = 16 set, so they are completed or not together.
  - Its numbers on the bases that were sent may appear only as one line labelled "not completed; descriptive only".
- **Why:** a missing try would otherwise count as wrong for both arms. An unsent base would score 0 − 0 = 0, and a set never sent
  would read "no worse" on no data.
- **The driver reports,** for every test and arm, the designed, final and missing tries, whatever the outcome.
- **Study 1's exclude-missing view** (`research/reporting-definitions-main.md` item 16; D-48 row 23) is carried over for B1–B3 as a
  sensitivity view, labelled "sensitivity: missing tries excluded".
  - It runs only if any try is missing. Otherwise the report says "no missing items".
  - A missing try is left out of its share: h_b and o_b use the tries with a final record, and the vote uses the tries left, with k
    held to what is left. A base where hx or om has no final try on a shape is left out of the test.
  - On a completed test it equals the main view. On a test that is not completed it is description only, never a reading.
- **The §10 headline reads only completed tests.**

## 5. Power (F-4): the locked simulator

`research/models/study1b_power.py` is a thin wrapper around the **locked** `study1_ni_power.py` (prereg-lock-3).
- It reuses, unchanged, `haiku_p`, the worlds ii-mod, ii-high and iii, KAPPA = 0.5, `vote_table` and `readings`.
- It adds only 1b's design: 10 Haiku-max tries; 2 Opus tries, each drawn from the shared latent; both shapes of one base sharing its
  latent (the conservative choice); and vote@7.
- Settings: 4,000 studies, seed 20261011, Holm's strictest step for three tests.
- Output: `study1b_power_results.json`.

**Chance of the primary reading "no worse by more than 5 points"** (Holm's strictest step), with Opus at 98%:

| Haiku-max's true accuracy | B1 (80 base) | B2 (vote@7, 80 base; **at k = 7, assumed; conditional on the measured k**) | B3 (40 base) |
|---|---|---|---|
| 98% (level with Opus) | 0.89–0.99 | 0.99–1.00 | 0.70–0.88 |
| 95% | 0.23–0.31 | 0.90–1.00 | 0.20 |
| 92% | 0.00–0.01 | 0.66–1.00 | 0.01–0.03 |
| 88% | 0.00 | 0.32–1.00 | 0.00 |

**At margin 10 (secondary):** B1 is 0.88–1.00 at 95% and 0.40–0.65 at 92%.

**At Opus 95%:** B1 at margin 5 is 0.67–0.89 if Haiku-max is at 95%.

**What this means, stated in the spec:**
- Near Opus's ceiling, a 5-point margin confirms "no worse" **only if Haiku-max is about level with Opus**. A real gap of 3 points
  usually reads "inconclusive".
- The error-rate ratio beside each test carries the rest of the information.
- B2 has more power, because voting raises Haiku-max's accuracy.

## 6. Descriptive outputs (pre-registered, no tests)

- **The effort figure:** accuracy against effort, per model, on the same puzzles.
  - At **N = 6**: Haiku off, low, medium, high, xhigh and max; Sonnet low through max; Opus low through max.
  - At **N = 16**: Haiku off through max, plus Opus-medium.
  - Each point carries its interval: a cluster bootstrap for multi-try arms, Clopper–Pearson for one-try arms, 2,000 draws, seed
    20261013, named `"1b:<tag>:<N>:<6x1|1x6|pooled>"`, where `<tag>` is the arm's tag in §3.
  - The list cost per answer is beside each point.
  - Study 1's N = 6 points are drawn separately, labelled "Study 1 (other puzzles, exploratory)".
- **The length curve with a Haiku-max line:**
  - Haiku-max and Opus-medium at N = 6 (1b), 12 (1b) and 16 (1b);
  - Haiku-medium at 6 and 16 (1b);
  - with the Length curve (from the length sweep, D-87) behind it, labelled.
- **Cost per correct answer** for every arm (`research/reporting-definitions-main.md` item 9c).
- **The equal-money vote curve** of Haiku-max for k = 1–10 at N = 16, by the vote-curve paragraph of
  `research/reporting-definitions-main.md` item 8b, with k = 1–10 in place of 1–40. It is the only k description for B2 (§4).
- **Format compliance, refusals, truncations and missing items** for every arm (`research/reporting-definitions-main.md` items 16
  and 17), with the exclude-missing view if any try is missing (§4).
- **The trial round** (§7): only its tokens and costs are reported. Its answers are never scored.
- **If the run stops early** (lock-4 audit C1):
  - hx and om at a length whose test is not completed (§4) are shown on their final tries only, labelled "not completed;
    descriptive only";
  - every descriptive arm's entry carries its missing and designed try counts;
  - an arm with no final try reads "not sent (run stopped)", never 0%.

## 7. Token limits: the trial round (F-5)

**The rule from Study 1 (Amendment 1, item 3, in `studies/1-real-price/spec.md`):** a measured arm gets 1.5 × its largest output,
rounded up to 1,000. That covers every limit set in §3.

**For arms never measured** (the arms §3 lists as set by §7):

- **The trial round.** On **already-used** puzzles of the same length, never the test sets: `ladder-ledger-l14n6-v1`,
  `-l14n12-v1` and `-l14n16-v1`, base 000–009, both shapes (20 items per length), one try per item per unmeasured arm.
  - Trial-round limit: 64,000, or 128,000 for Haiku-max at 12 and 16 steps.
  - **The trial round replaces any doubling rule on the first test round.** The test puzzles never run under a limit that changes later, so the 2% pause
    (below) is the only truncation rule in the real waves. It never changes a limit.
- **The mechanical rule:** for each unmeasured arm, its limit for the real waves = min(128,000, max(the arm's floor, 2 × the largest
  trial-round output, rounded up to 1,000)).
  - The floor is §3's: the same model's medium limit at that length, except Haiku-max at 12 and 16, whose floor is 96,000.
  - If any trial-round call stops at its limit, that arm's limit is 128,000.
  - **The rule reads only `usage` and `stop_reason`. It never reads `answer_text` or anything scored.** The trial round's answers are
    never scored or reported.
- **During the real waves, Study 1's 2% truncation pause applies** (D-94(1)). If more than 2% of an arm's calls in a wave stop at
  `max_tokens`, the run pauses before the next wave.
  - **If any confirmatory arm (hx or om at 16 or 6) is over 2% in the wave, the pause stands and the run returns to the user.**
  - **If the pause comes only from descriptive arms, it is released at once** under the user's standing release (D-103(E)), with
    Edith's fixed note, and the truncations are reported. The count stays per wave, as pre-registered. The clearance holds the
    note's wording.
- **A cost-only cut order** (Edith S-1). After the trial round, compute:
  - projected = spent so far (the trial round's actual Batch cost) + **1.5** × Σ over the remaining arms of (Batch cost per call × planned
    calls);
  - **the source of each arm's cost per call (Batch, as billed):**
    - the trial round's mean for the arms it measured (§3);
    - `main-l14n6-1`'s per-arm mean for arms measured there (hx, om, ho, hl, hm, sl, sm and ol at N = 6);
    - the length sweep's (`ladder-l14n-1`) per-arm mean for arms measured there (om at 12 and 16; hm at 16).

  If projected > **0.9 × the cap** (0.9 × $130 = **$117**, §8), parts are cut one at a time, in the order below, recomputing after
  each, until projected ≤ 0.9 × the cap. B1–B3's arms (hx and om at 6 and 16) are never cut:
  1. Opus-max at 6;
  2. Opus-xhigh at 6;
  3. Sonnet-max;
  4. Sonnet-xhigh;
  5. the 12-step point;
  6. Haiku-xhigh at 16.

  This decision uses costs only, once, after the trial round.

## 8. Cost and cap (F-6)

**Expected batch spend, central (high case):**

| Part | Spend |
|---|---|
| Confirmatory core (hx ×10 and om ×2, at 6 and 16) | $24 ($37) |
| Haiku's effort range at 6 and 16 | $9.5 ($14) |
| Sonnet's five levels and Opus at low, high, xhigh and max, at 6 | $22 ($33) |
| The 12-step point | $11 ($17) |
| The trial round | about $5 |
| **Total** | **about $72 ($106)** |

- The levels nobody has run yet (Sonnet and Opus at high and above, Haiku high and xhigh) are guesses until the trial round measures them. Then
  §7's cut order applies.
- **The guard's booking** is each call's worst case: its prompt plus its `max_tokens`, at the Batch price. The bill is a fraction
  of it. From the plan's booking file, `data/plans/study1b-plan-booking.json` (`slim plan`, at `--cap 130`):
  - the trial round books **$61.40** (280 calls);
  - the test sets book **$176.57** with every arm set by §7 at its floor, so the whole plan books **$237.97** at the floors (11,640
    calls);
  - with every arm set by §7 at the 128,000 cap, the whole plan books **$826.77**. The real limits fall between the two.
  - So the guard sends the plan in several waves under the cap. The booking file gives the split at the floors.
- **Run cap: $130**, the user's ruling (D-102: "B i choose"). The §7 cut line is 0.9 × $130 = **$117**.
  - With the top-up run's $25 cap, the two ceilings total $130 + $25 = **$155**, inside the $158.30 left.
  - It is above the high-case spend ($106).
  - Only one paid run spends at a time.
  - Edith's clearance pins it (`live --cap 130`).
  - The old $170 all-in line (D-27; D-48 row 25) is retired for Study 1b and the top-up run (D-103(A)). The guard's $200 hard stop
    stays; the worst case all in is $41.70 + $130 + $25 = $196.70.

## 9. Procedure and calendar (Edith's advice)

1. **This spec:** Edith reviews it.
2. **Friday's slim runner:** a `--setups` list with per-arm `max_tokens`, the trial round and the cut-order hook, with no E3,
   D-42 or RT. Plus the 1b analysis driver: B1–B3, k from cost-only rows, and §6. Edith reviews it **before lock 4**, so there is no
   post-hoc converter.
3. **prereg-lock-4:** this spec, the sets' manifests, the never-sent check and its lock-4 record (§2), the exposure scan and its
   pre-tag output (§2), the plan and booking files, the runner, the driver and the power files. Then the gist and Wayback, then a
   Zenodo version. **All before any call.**
4. **Karen's price re-check** within 24 hours before the start, then **the price-date commit**. Then Edith's clearance, pinned to
   that commit, a **fresh Console reading** under the run id `study1b-1`, and the user's go and cap.
   - **The only change allowed after `prereg-lock-4`, declared now** (lock-4 audit A2, A10). The guard accepts the price table only
     on its own date and the next UTC day, so the run needs one commit after the tag.
     - That commit is the **only child of the tag**. It changes only `PRICE_TABLE_DATE` and the docstring line recording the
       re-check in `harness/pareto/prices.py`, and the test that pins that date (`git diff --stat prereg-lock-4` shows only those
       two files).
     - **The price table itself changes only if the re-check finds a price change.** That goes back to the user before any call.
     - If a wave or a resume would cross into a UTC day the date no longer covers, a further commit of the same kind follows, each
       the only child of the one before, after a same-day re-check, with Edith's clearance re-pinned to it.
     - Every such commit is listed in the methods. The analysis driver runs at the `prereg-lock-4` commit.
5. **The run:** the trial round, the limits and the cut decision (§7), then the test waves under the 2% pause.
   - **The confirmatory arms go first** (lock-4 audit A1): hx and om at 16, then at 6, with every try final, before any descriptive
     arm is sent.
   - Its own 48-hour window. It **may extend to 72 hours with a recorded note, only if no model has changed**, as D-45 (the user's
     ruling D-103(B); lock-4 audit A19). Whatever is unfinished then falls under §4's completeness rule.
   - **Study 1b sends no new wave after 2026-10-16 06:00 UTC**, even inside a D-103(B) extension, so the top-up run's first round
     still fits before its latest start. Anything unsent falls under §4's completeness rule (the user's ruling D-106(H)). Edith's
     clearance enforces it through its expiry time.
6. **k committed (cost only), then the stamped driver runs once.** The results are read after Edith's check.
7. **The top-up run (the Haiku team, the Haiku picker, step voting on pieces) is sequenced before or after, never at the same time.** Everything finishes by **10-18**,
   because the credit expires on 10-19.

## 10. Outcome wording, fixed now (F-7)

**Only completed tests (§4) are read.**

**If B1 holds (all three views):**
> "On fresh 16-step procedures, Haiku 5.5 at max effort was no worse than Opus 5.5 at medium effort by more than 5 points
> (difference d points, 95% interval …), at about 1/k of the cost per answer (k measured)."

**If B1 is "inconclusive":**
> "At 16 steps we could not show that Haiku-max is within 5 points of Opus-medium (d, interval); its error rate was r times Opus's."

**If B1 is "worse by more than 5 points":**
> "At 16 steps Haiku-max was worse than Opus-medium by more than 5 points (d, interval)."

**If B1 is "no worse" as deployed only** (it fails the refusals-out or the truncations-out view, so it is not a headline, §4):
> "As deployed, Haiku-max was within 5 points of Opus-medium at 16 steps (d, interval), but not with [refusals | truncations] left
> out, so we do not claim it."

**If B1 is "not completed"** (§4):
> "Test B1 was not completed: [m] of its [n] designed tries have no final record, so we give it no reading."

**If B2 is not run** (k < 1, §4):
> "We did not run the equal-money vote (B2): at 16 steps one Haiku-max try cost more than one Opus-medium try, so no vote fits
> within Opus's price."

**B2 and B3 use the same templates,** with their own test name and length. Never use "matches" or "as good as" for a
non-inferiority result. A 10-point reading is quoted only as the secondary.

**The cost** is always "about 1/k of the cost per answer, k measured", from the list costs of `research/reporting-definitions-main.md`
item 9b.
