# Lock manifest (D-69 lock tag, spec §7b "The lock before the pilot", item 7; updated for prereg-lock-2, D-86 to D-89, and prereg-lock-3, D-90, and prereg-lock-4, D-96 to D-105)

*Friday, 2026-10-11, per Edith's `ops/reviews/2026-10-11-lock-contents-plan.md` (C); Karen supplied the D-72 and fixture lines. This file is
committed in the tag. Its file-hash block is written by `python3 -m harness.lockhash write` as the **last commit before the tag**, and anyone
re-checks it with `python3 -m harness.lockhash check` on a clean checkout of the tag.*

*prereg-lock-2 (Friday, 2026-10-12): the same file, updated for the declared deviation of D-86 (shorter puzzles). Everything locked in
prereg-lock-1 stays in the tree unchanged, apart from the code changes listed under "prereg-lock-2" below; that tag stays public, so the
timeline is visible: lock-1, pilot-1, the deviation, lock-2. The hash block is rewritten for lock-2 as the last commit before its tag.*

*prereg-lock-3 (Friday, 2026-10-12): the same file again, for lock-2's one dated amendment (Amendment 1, the values the ladder's
rules chose) and the declared Deviation 2 (D-90, the marking rule for repeated step lines), fixed together by one tag as Edith's
route allows. The lock-2 section below stays as it was cut; the "prereg-lock-3" section lists what changed since. The hash block is
rewritten for lock-3 as the last commit before its tag.*

## Versions

- **Python:** 3.9.6. The D-72 simulator runs with the system python3 (`/Library/Developer/CommandLineTools/usr/bin/python3`; numpy 1.26.4,
  scipy 1.12.0); the harness runs with the venv (`/Users/hrixay/Desktop/pareto/.venv`, anthropic 0.125.0); both are Python 3.9.6.
- **git:** 2.39.5 (Apple Git-154) (`git --version`). The D-71 tar was tested reproducible with this version.
- **Anthropic SDK:** `anthropic==0.125.0`, pinned in `harness/requirements.txt` (wheel sha256
  3486013602eca76d8b12540764e53654f02cf4951110bca86cf06e67428a9f21); the real transport refuses to start unless exactly this version is installed.
- **Generator:** `LV_VERSION = "ledger-0.5"` (`harness/taskgen/ledger.py`; Edith's full-scale gate PASS at `19a48fd`, tests at `33e6f20`,
  `ops/reviews/2026-10-12-lock2-gen-r1.md`). ledger-0.5 is ledger-0.4.2 plus the D-86 presets `l14n4`, `l14n6`, `l14n8`, `l14n12` and
  `l14n16` (l14's rules at n steps, the house window scaled from l14's 5–8 of 24); its 24-step output is unchanged apart from the version
  string (every lock-1 set's first base puzzle rebuilds byte for byte, `PARETO_SLOW=1` check). Lock-1's sets were made by ledger-0.4.2 (and
  the check set by 0.4) and verify under the lock-2 code with `freeze --verify --allow-other-version`.

## Frozen task sets (`data/tasks/`)

| Set | Generator | items.jsonl SHA-256 | Note |
|---|---|---|---|
| `check-ledger-l16-v1` | ledger-0.4 | da6c1545f07bfe98b759474b3b4e1ca17afd458dd7a177143739f6c6dfd81676 | the 20-call check set as sent; verifies under the locked code with `freeze --verify --allow-other-version` |
| `smoke3-ledger-l16-v1` | ledger-0.4.2 | 71375f559900c3a0eefaec397ffd6f384ddd0e23990716a7103be500255354ed | the S3 check Batch set (excluded from every analysis) |
| `pilot-ledger-l14-v1` | ledger-0.4.2 | a9136afbe8cc01e5a098352bbc9475723dc4a83a31bed10f270b197a91e05775 | pilot set; 10 items, frozen at `240454b` |
| `pilot-ledger-l15-v1` | ledger-0.4.2 | ce28f75f320423437fb3316a9734e54ee19de1754cfdb7ccc5cefa3d41430493 | pilot set; 20 items, frozen at `240454b` |
| `pilot-ledger-l16-v1` | ledger-0.4.2 | e174f2d3cf1c6dda9bd1d75f417d5b16e2a95fd594d05a8cc43fd961a3b3e112 | pilot set; 20 items, frozen at `240454b` |
| `pilot-ledger-l17-v1` | ledger-0.4.2 | ea91c870af61dda76c749de5e1795fa9bd0d258ee2790419723007288664d1aa | pilot set, the spare rung; 10 items, frozen at `240454b` |
| `ext40-ledger-l14-v1` | ledger-0.4.2 | b48a1fdf5077d4419bfecb5698907a56a6409f2ced52b2779ecce93b79a8e381 | the D-72 add-40 set; 80 items, frozen at `240454b` |
| `ext40-ledger-l15-v1` | ledger-0.4.2 | 536b83868fa199fccb81a7b15b717d6bec735caf884ae116a03aa6d02b11575d | the D-72 add-40 set; 80 items, frozen at `240454b` |
| `ext40-ledger-l16-v1` | ledger-0.4.2 | f424c276c7e7fdbad5ab5b4b9b2246e0d6770c77412baa7f56927b572ed3e7b1 | the D-72 add-40 set; 80 items, frozen at `240454b` |
| `ladder-ledger-l14n4-v1` | ledger-0.5 | fd3454f7406cb8ac376c7d09462bc2589767b2692a93bf37b86905c5b8f4ac56 | lock-2; the D-87 ladder set: 20 base × 2 shapes (40 puzzles), split pilot; frozen at `a8f0acd` |
| `ladder-ledger-l14n6-v1` | ledger-0.5 | e9e2d56098aeb2a63cad8111aee2e7399571c42980acd4ee01c7a2fa4e81f19b | lock-2; the D-87 ladder set: 20 base × 2 shapes (40 puzzles), split pilot; frozen at `a8f0acd` |
| `ladder-ledger-l14n8-v1` | ledger-0.5 | c69192dbe5393220a0d5927f157412ff041d61142c2c6cf9724652690c41f808 | lock-2; the D-87 ladder set: 20 base × 2 shapes (40 puzzles), split pilot; frozen at `a8f0acd` |
| `ladder-ledger-l14n12-v1` | ledger-0.5 | 9ac487325ede011169d1260826076fc55028ffb0b5e7eed829694366d5394e94 | lock-2; the D-87 ladder set: 20 base × 2 shapes (40 puzzles), split pilot; frozen at `a8f0acd` |
| `ladder-ledger-l14n16-v1` | ledger-0.5 | 0503cf11971e8b5a00221f0eb0573f47497490732941478f88f5afa55ecbb12b | lock-2; the D-87 ladder set: 20 base × 2 shapes (40 puzzles), split pilot; frozen at `a8f0acd` |
| `main-ledger-l14n4-v1` | ledger-0.5 | 7775bc12d5f5a1bf42c4d24556f23f947c40f3bd20123df5391925af2f6a109b | lock-2; the main-run set at this n: 80 base × 2 shapes, split main; frozen at `a8f0acd` |
| `main-ledger-l14n6-v1` | ledger-0.5 | 11deebd8109adfcc7a1332006ceb63db6e14ab170a8afaf8fe4b8bd6f17f09bf | lock-2; the main-run set at this n: 80 base × 2 shapes, split main; frozen at `a8f0acd` |
| `main-ledger-l14n8-v1` | ledger-0.5 | 472f3540613d215f0fc7abb9e61d6d70018852741a804b8f4de5e457e91f8abf | lock-2; the main-run set at this n: 80 base × 2 shapes, split main; frozen at `a8f0acd` |
| `main-ledger-l14n12-v1` | ledger-0.5 | 9aefe3406a17f08bb0614fe4fdf72b87a5b7e2ba0fde1a0072805d27d44f7c44 | lock-2; the main-run set at this n: 80 base × 2 shapes, split main; frozen at `a8f0acd` |
| `main-ledger-l14n16-v1` | ledger-0.5 | 0bf12afca05edd504085c715c9ce1b5cdd8eb40a67978db675f8884e7a55f372 | lock-2; the main-run set at this n: 80 base × 2 shapes, split main; frozen at `a8f0acd` |
| `ext40-ledger-l14n4-v1` | ledger-0.5 | ae0b642167d829d8b3ed5e7db2cbc84b3211d38f9622666f48e5a68c523b9f68 | lock-2; the D-72 add-40 set at this n: 40 base × 2 shapes, split main; frozen at `a8f0acd` |
| `ext40-ledger-l14n6-v1` | ledger-0.5 | 1f342a6c9b0129df5796a52612ef50cc58ba162dedd6abfc4036cc38173b94dd | lock-2; the D-72 add-40 set at this n: 40 base × 2 shapes, split main; frozen at `a8f0acd` |
| `ext40-ledger-l14n8-v1` | ledger-0.5 | 28bf32e0a132350889a242360edeed081c2dcfcd46eab59a7673877dfd8f6476 | lock-2; the D-72 add-40 set at this n: 40 base × 2 shapes, split main; frozen at `a8f0acd` |
| `ext40-ledger-l14n12-v1` | ledger-0.5 | 611d73cd27af05ffc8e2c81645bbe75cdc56d240eda376d746a17c767956ca78 | lock-2; the D-72 add-40 set at this n: 40 base × 2 shapes, split main; frozen at `a8f0acd` |
| `ext40-ledger-l14n16-v1` | ledger-0.5 | 00fbe9c26e770f3377683cea2d7de1c32945e341be4965475fdd81e4d2b8a587 | lock-2; the D-72 add-40 set at this n: 40 base × 2 shapes, split main; frozen at `a8f0acd` |

The 15 lock-2 sets (700 base puzzles, 1,400 puzzles) were frozen one at a time from a clean checkout of `a8f0acd`, whose `harness/taskgen` is
byte-identical to the gated `19a48fd`. Every manifest records `git_dirty: false`. Each set was deep-verified, every pair of new sets is
disjoint (no shared set id, seed or prompt), and every new set is disjoint from each of the 13 lock-1 sets.

## The sealed 20-call check (D-78)

Run `check-ledger-1` (2026-10-11, commit `e1d6d60`), raw files in `data/raw/check-ledger-1/` (git-ignored; not in the tag). The answers are
sealed until this tag is cut. SHA-256, as in the spend-log row:
- `calls.jsonl`: 92dd68a5b002ba102b7d24e1905de1058e11f1bc84287ab0a0b9e0a628402d77
- `check_result.json`: 9b76b38f23b7151580f0572b7447b901f0a68efae4c5eed3d7bfdbec44c43dfd

## The pilot plan

`research/pilot-plan-ledger.md`, last changed at commit `7bcc8d1` for lock-2 (`05f31ef` at lock-1). The copy in the tag binds, and its hash is
in the block below. Its section "The ladder pilot for prereg-lock-2" holds the ladder's sets, calls, rule and budget. Its section
"Pre-registered descriptive plan for the accuracy-versus-length curve" holds the D-87 curve.

## D-72 power simulator and the post-pilot decision code (Karen; spec `research/d72-d73-lock-spec.md`)

- Simulator: `research/models/study1_ni_power.py` (sha256 44a325b03ece08ea3141c5f8705b6852f40407d946d7a0a6956b869475d107b0). Entry points
  `d72_inputs`, `d72_rerun`; config `D72` = seed 20261011, nsim 4000, κ 0.5, B 80 (120 for information), level 0.01 (Holm's strictest,
  one-sided 0.005), margin 10, threshold 0.5, 40 samples. CLI: `python3 research/models/study1_ni_power.py d72 <inputs.json>`.
- Inputs (filled from the pilot in the dated amendment, spec §D-72.1–2): `haiku_correct`, `haiku_tries`, `wrong_pairs_agree`, `wrong_pairs`
  (trace keys, D-76), `opus_correct`, `k`, all at the chosen preset, 1×24 only. Known-answer example: `research/models/d72_example_inputs.json`
  (35e32da2674e71b6e578f7bcc0b23588a0cb52f3ab9dab90c8ca3fe0f57e34ee) → `research/models/d72_example_output.json`
  (63a2dd7b315b5c0de80245a0b274f58c06b8bdeb9a9ba551f7673680ba1c7c5d); reproduces exactly.
- Budget, cut order and D-74: `research/models/study1_cut_order.py` (1951338fb89930708389d748e8ef494498aace82b9323f49a1e8a456936711bb);
  `post_pilot_decision`, `d72_budget_test`, `d73_cuts`, CEILING 170. Known-answer examples: `research/models/d74_example_output.json`
  (292bb4444e2492a95e9fb2c7334d59231c2412b79a1cf181bcbf3fe46874d11b); `python3 research/models/study1_cut_order.py` asserts they reproduce.
- Token and price model: `research/models/study1_budget.py` (50fe869d3980654ebcbd447b0ecfb05d1aa77dcc624e406bdb193f6c39b5c087). Inputs:
  `research/models/ledger_measured.json` (bace4e0926a56399b34f8cab724f96abc5bfdb24a486f1be9be4f865ead95cbe; pre-pilot values; the amendment
  writes the pilot means with `post_pilot: true`).
- Power grid outputs (informative): `research/models/ni_power_results.json` (30d0e68887477b31dcbe1f18f06b43437383ca9e64847b6df4b5c8b551a97a31)
  and `research/models/ni_power_refusals.json` (fbabf63614f5ce0168528a0b581ef9363b86b251b51bd64da93e03034b3e0f66); seed 20261011 (true values
  on +1, refusal views on +7), 4,000 studies per cell.
- Pre-pilot cost projection (informative, not a rule): `research/models/check20_projection.py`
  (493357f38939d9f029baa6ac752d43f5c8ee6062bf8cb5977cc3f38e098ad6cb).
- Spec: `research/d72-d73-lock-spec.md` (061de63c1c207093fd8bacec064ef47b6c8c2d4199219a8396371e1350e763bc).

## Tests on simulated data with known answers (lock item 6)

- `research/fixtures/sim-main-v2/`: 223 parse cases. `parse_cases.jsonl.gz`, 196 (round 1's 148 plus round 2's 48):
  137c435bdcebf4d9a19d50cea909773f211bb047759d1410aceab8c86b7ee1aa; `pieces_cases.jsonl.gz`, 18:
  5f363f7faa2fef4532c4bd998b2c0c357212a88371ce0f65ef73190a9d04d336; `final_cases.jsonl.gz`, 9:
  72e881728e5a67c27e40c358bb7e2d40512fe6eeb98d009815a7b264c5436551.
- Runner `research/fixtures/sim-main-v2/run_parse_cases.py` (66d16d12799b4e2ab3c494c4f68714d03b3fc1f34fd9ece9e094213101cb27d5): 223 of 223 must
  pass (guarded by `harness/tests/test_analysis_parse_fixtures.py`).
- Generators: `research/models/sim_fixtures_v2.py` (3e54fd8155f6528280df89360d3b334d46b68f8d73157277e80640de8ba21ddf), parse seeds 7676–7679,
  vote Monte Carlo 4242; `research/models/sim_fixtures.py` (6432533592f2a639bf2b1f608068142dcb631b095e8b50b8efca96dae5b6a03f), case seeds
  1101–1107, coverage seeds 500000–500999.
- **lock-2:** every `.gz` under `sim-main-v1/` and `sim-main-v2/` was re-written with gzip mtime 0 (Karen, `4fce4b9`, Edith K2-4).
  Their decompressed content is unchanged and re-generation is now byte-identical, so the file hashes above (and the generators' hashes)
  are lock-2's. Lock-1's hashes were a87dffd4…, 64277073… and 5ecf54c9… for the three case files.
- **lock-3 (D-90):** `parse_cases.jsonl.gz`, the runner and `sim_fixtures_v2.py` above carry lock-3's hashes (Karen,
  `7e1cfbf`). Round 1 still has 148 cases; only the 4 identical-duplicate cases now expect ok, with lock-2's rule kept as
  `expected_strict`. There is a new file, `parse_cases_d90.jsonl.gz` (16 cases, seed 7678). The runner also checks every case under
  `repeats="strict"`, so it reports 451 of 451 (all must pass). Lock-2's hashes were 7f1c681c… (cases), 5baa68b1… (runner) and
  b1d7ae37… (generator).

## prereg-lock-2 (D-86 to D-89)

- **Lock-1.** Tag `prereg-lock-1`, commit b4b6b8474f39538055b3e358b48243d51aca5e3b (2026-10-11 19:32 UTC). Tar SHA-256
  37454153435ae927ccd5aa3a5f61e4f7033e53a35875b830a3f9ccfd2c610adf, git 2.39.5; Edith recomputed it and it matches. Zenodo v1:
  DOI 10.5281/zenodo.23304164. Lock-2's fingerprint goes in a new version of the same Zenodo record; v1 stays public.
- **The deviation note.** `ops/reviews/2026-10-12-deviation-note-1.md` (Edith's wording), copied word for word into the spec's
  Amendments (`studies/1-real-price/spec.md`).
- **Why.** Pilot-1 (24 steps) put Haiku-medium's whole-answer score at about 0–2% at every preset: tier 3 of D-36(4), returned to the user.
  The user ruled D-86 blind to pilot-1's Opus and Sonnet results, which were never opened. The one dial changed is the chain length,
  n ∈ {4, 6, 8, 12, 16}. Rule kinds (l14), wording, D-76 scoring, the five tests, the margin, the k rule and the fairness check are all as
  locked.
- **Pilot-1 (sealed answers).** Run `pilot-ledger-1` (2026-10-11), raw files in `data/raw/pilot-ledger-1/` (git-ignored, so not in the
  tag). SHA-256, as in its spend-log row: `calls.jsonl` 411c877baf3f4b399d44355c6d77126c4abd7c348d17fca194aa0e46d7f79142, `compact_table.csv`
  83c18fd960022575ccfc2b9d1819217d242b122de87682dbda34e21e5cf30d54, `ledger.jsonl`
  2bf9297e656a8b87ccf47795a4b397b2d853d79ddbd52599943bbc3d89b48969. Its Haiku-only preset pick is
  `data/pilot/preset-choice-pilot-ledger-1.json` (none, returned to the user; committed at `21fa9f0`, before any Opus or Sonnet number was
  opened). Its Opus and Sonnet answers are opened only after this tag
  (D-86(5)), and shown on the curve as labelled 24-step markers.
- **The ladder (D-87, D-88, D-89).** The sets are the five `ladder-ledger-l14n*-v1` sets above. Each puzzle gets Haiku-medium ×10,
  Opus-medium ×1 and Sonnet-medium ×1, through Batch: about 2,400 calls. Budget: $13.5 central, $19.9 high. Hard cap $30 (D-89).
  - Runner: `harness/pareto/ladder.py`. Opus and Sonnet are sealed: the runner never scores them.
  - The pick: `harness/analysis/choose_preset.py`, with Haiku-medium only, the median closest to 37.5% within 25–50%, else within 15–60%,
    else returned to the user. Ties go to fewer steps.
  - The pick is committed, with input and trace hashes, before any Opus or Sonnet ladder answer is opened.
- **Code changed for lock-2.**
  - Generator ledger-0.5, and the freeze's per-n shapes (`harness/taskgen/`).
  - Scoring, the five tests and choose_preset at any n (`harness/analysis/`, Edith CLEAN at `82281a9`).
  - The ladder runner.
  - The curve code `harness/analysis/curve.py` (Edith CLEAN at `a8f0acd`, `ops/reviews/2026-10-12-lock2-curve-r1.md`; Karen confirms it
    matches the plan). It is sealed by default. Opus and Sonnet are read only with a committed, binding Haiku pick whose set hashes match.
    Pilot-1's Opus and Sonnet records also need this tag.
  - `PRICE_TABLE_DATE` 2026-10-12, from Karen's re-check: unchanged.
- **Decisions after the ladder.** Only the chosen n's Opus-medium point feeds a decision: D-72's p_opus (1×n), and the near-ceiling flag
  (pooled at least 95%). The flag is from `research/models/ceiling_power.py`
  (408dd44486a332d75294dc44240aa865b3904253dca6e1e1ecd8ea6601844943) and `research/models/ceiling_power_results.json`
  (cf319dc89e765d777f24d4af279fe6b1e41f29e50cbfd84bcd93d3ea465424cb). Then the
  post-pilot steps of `research/d72-d73-lock-spec.md` run at the chosen n, and the pick goes in the one dated amendment to this lock.
- **Parse fixtures at n steps** (as at lock-2; lock-3's `parse_cases` hashes are in the next section).
  `research/fixtures/sim-main-n/` holds Karen's fixtures, gzip mtime 0 (`4fce4b9`); 720 of 720 pass:
  - `parse_cases_n4/6/8/12/16.jsonl.gz`, each 136 cases: f47b51101e3cec4d8a51514f1085d6ee4c85649b344398c33eb53aa32876cd4b,
    bd386091240dd6cdf66bd0b292ed4e61087ebb5759603ccfd7d7d7eb0a512411, a406b356338312af08980705dc7a4b9297481cea4b109b08d76049bac6388673,
    980cd5008d39a8a2d01c4f2c1dcafa0e794723b408838a237eefe36ee932da28, 190e6bb859ab281009c4853890707a99f2e6393106d203a9cb73d0b486a26223;
  - `pieces_cases_n4/6/8/12/16.jsonl.gz`, each 8 cases: 8139f9df9689bebf29bd86001c6943a0750276638d3dfc3e064f7f4278094f13,
    243e6f8a6dd6068e77f575f074af7ef588ff7d7e306130690d44bd4fe8746aca, 72c4a3d46b9c82db9cb674e4dc924e30cb9ed446b51e4d4bd5c020a2a7ba0490,
    6f1c7ba55a78a5c7b9b8c149de89284747066200254fcf13357313ef23420232, c8e859811a0b5b2e83c9834489b3f219fc447c2b9fb4495e9d544d1076500df0;
  - runner `run_parse_cases_n.py`, guarded by `harness/tests/test_analysis_n_steps.py`; generator `research/models/sim_fixtures_n.py`
    (seeds 8800–8804 for parse cases, 8900–8904 for pieces).
- **Reviews.** Every lock-2 review is under `ops/reviews/2026-10-12-*` (the generator gate, the analysis, the curve, the sets).

## prereg-lock-3 (Amendment 1 and Deviation 2; D-90)

- **Lock-2.** Tag `prereg-lock-2` (annotated tag object d02219ea0208e2bef22d7e88d736e76b6edd5b12), commit
  95fb5f81b9a3a131da77f5a776af200c8e60477d. Tar SHA-256 93a2381571d0eb12ba27bd9084701ecc4ca1e72536bc0300e509ac583e6c615a, git 2.39.5;
  Edith recomputed it (`ops/reviews/2026-10-12-lock2-review.md`). Zenodo v2: DOI 10.5281/zenodo.23311831. Lock-3's fingerprint
  goes in a third version of the same record; v1 and v2 stay public.
- **The spec** (`studies/1-real-price/spec.md`, Amendments):
  - **Amendment 1**, the one dated amendment to lock-2 (PR #26, `f773d83`, Edith CLEAN). It fills only rule-chosen values:
    - N = 6;
    - k's inputs, with k = 36 projected; the binding k comes from the main run's costs;
    - `max_tokens`: 1.5× the measured n = 6 maxima for the medium setups (Haiku 5,000, Opus 4,000, Sonnet 3,000); every other
      setup keeps the locked pilot limits;
    - D-72: no add-40;
    - D-73/D-74: the full plan, no cut;
    - the near-ceiling label ON;
    - the price window, 2026-10-12/13 UTC.
    It also carries the disclosures.
  - **Deviation 2** (D-90), word for word from `ops/reviews/2026-10-12-deviation-note-2-and-lock3-route.md`.
- **The marking-rule code** (D-90; Edith CLEAN at `b6c1de5`, `ops/reviews/2026-10-12-d90-parser-amendment1-r2.md`):
  - `harness/analysis/trace_parse.py`: a step line repeated with the identical state is read once; a conflicting repeat is
    `extra_line`. The original rule is `repeats="strict"`.
  - `harness/analysis/scoring.py` and `harness/analysis/five_tests.py`: the named sensitivity view "original" (`correct_original`,
    `row_correct(..., "original")`, `original_repeat_rule`).
  - Tests: `harness/tests/test_d90_repeats.py`. The lock-2 grading pin now checks the strict view byte for byte, and a new test
    shows D-90 moves only the identical-duplicate cases.
  - The full suite gives 670 OK (1 slow skip).
- **The ladder run `ladder-l14n-1`** (2026-10-12, $8.946918; the spend-log row). Its raw files are git-ignored, so they are not in
  the tag. SHA-256: `calls.jsonl` 3725c1cc87dcca8e0107234cb379f9a29c18486c1908e9f1486759d4fb0b52f4, `compact_table.csv`
  a4f60c97206d5245fe5177fcabe05a36de9d78fb77d708194cd3af4a600d8585, `ledger.jsonl` 09536cbc3f979656cddbb884107d60862103c038c38f662180a4985462d0f419.
- **Its outputs under both marking rules** (`data/pilot/`):

  | File | Under lock-2's rule | Under D-90 (lock-3) |
  |---|---|---|
  | The Haiku-only pick (l14n6 under both) | `preset-choice-ladder-l14n-1.json` 4cf5f2f8ebf30c6f95e85c4181e1db679f9447b15eae730f821cd877fb84c50f (committed `e8c4d43` before any Opus or Sonnet answer was opened) | `preset-choice-ladder-l14n-1-d90.json` a95350b9e229bd2681306170c840a1107afc32ed4fa2b3a4d7264be825529353 |
  | The D-87 curve | `curve-ladder-l14n-1.json` 1300a410d652323f9969fd2e44ff843619e72205a5e74cdf1ade01346fdc36ad | `curve-ladder-l14n-1-d90.json` 33ab260979cffd6a720f96aeab57f6384c9e6bd49b8730d0a4eab543184120f0 |
  | The D-72 inputs (the same under both) | `d72-inputs-ladder-l14n-1.json` a13358eac48e5fcaf1d3aff32550bc18a0f25242967acaee87fc82ecd36c5cd9 | `d72-inputs-ladder-l14n-1-d90.json` ef408fc585cd7045a8345fd21c035ded9862cab4d6521ef0891d1d5d47b87d1d |

- **The post-pilot figures** (Karen):
  - `research/post-pilot-n6.md` (8dc243cce69eebe78a41f1f1003fe40240fc0117641b7301265251a071972cb7);
  - `research/models/ledger_measured.json`, the pinned post-pilot fill (`post_pilot: true`;
    5b6365f8ec14883ebd2a451c2e2c7649b4dff0020fbf1c0cf52f2263c5c5d9d3).
  - They are unchanged under D-90.
- **Parse fixtures at n steps, lock-3** (Karen, `7e1cfbf`). Each `parse_cases_n{4,6,8,12,16}.jsonl.gz` now has 152 cases: the 4
  identical-duplicate cases flipped to ok, plus 16 new D-90 cases (4 kinds × 4 sizes). The `pieces_cases` files are unchanged. Hashes, in that order:
  5347f15dd5ad601e8096a10b8b7f871da48e1ef3bf5f017d0889a85ea23e3314, 8cdad61980476ef215e82777d43c26eaa8ec7894587de12e3e552956a406d117,
  66a5862487a0485e4e88dd9e8a2789e10ca087c1d2181abc0f127b5305f8de19, e89406067d7efaa4b3750fc8c40cab767015025c1db82cf48c362914fa8ad1d0,
  88dd4474e23d9394f093ee0c5b156057b735ab58eceb4d20f099e9a1060d2af2.
  - Runner `run_parse_cases_n.py` (ef675a3b38bd0965936a2c8a8eff76e0e7ce14d546b0832d6186242316764c9c), also under `repeats="strict"`:
    1,560 of 1,560.
  - Generator `research/models/sim_fixtures_n.py` (b0401acad693f40d6d38fe362c83d047d40bab75d96cd9f8e8516298507dea4f).
  - 24 steps: `sim-main-v2/parse_cases_d90.jsonl.gz` (487022d4d6fba957a85d2dc712ef835db13f1c2d2607216dbbf2946a60cdafe7).
- **Unchanged since lock-2:**
  - the generator, ledger-0.5, and every frozen set;
  - the ladder, main-run and ext40 sets (the main run uses `main-ledger-l14n6-v1`, with `ext40-ledger-l14n6-v1` held, since D-72
    did not fire);
  - the rest of the analysis code;
  - the runner and the spend guard.
- **Reviews.** Lock-3's reviews are `ops/reviews/2026-10-12-ladder-l14n-1-pick-check.md`,
  `ops/reviews/2026-10-12-ladder-curve-d72-check.md`, `ops/reviews/2026-10-12-deviation-note-2-and-lock3-route.md` and
  `ops/reviews/2026-10-12-d90-parser-amendment1-r2.md`.

## prereg-lock-4 (Study 1b, D-96 to D-106; the top-up run, D-99, D-100 and D-106)

- **Lock-3.** Tag `prereg-lock-3` (annotated tag object 57cfefa0d77989c250cf1c673b4a01581fc2403f), commit
  086fbfd04063a10e2c64f2a737e5771b0aa70dc8. Tar SHA-256 1221e8394529d1f5e81bdfebc7827366b32e3fb3aa24cfa39bfe71e98144deb5, git
  2.39.5. Zenodo v3: DOI 10.5281/zenodo.23313537. Lock-4's fingerprint goes in a fourth version of the same record (or, per D-103(D),
  the gist plus Wayback count as its public timestamp until Zenodo is available).
- **What lock 4 adds.** Everything for the last two runs, fixed before either sends a call. Both specs are frozen at Karen's commit
  9c007e5 (Edith CLEAN).
  - **Study 1b** (D-96; margin 5 points primary, Tier B effort sweep, the 12-step point; cap $130, D-102; D-97, D-103, D-104, D-106(H)):
    - the spec `research/study1b-spec.md`: SHA-256 4b6779502c26ae1da96b55573b0f9e62d153caa4509ef543b748c5d70a72c879;
    - the run plan `data/plans/study1b-plan.json`: file SHA-256 00abea9b0c585ce0c3c386b1fdd84029e4667c76feabeffd109725331162b911,
      **plan_sha256 d8c66f5bf1559e6be882d1d7155c7f8e79077205448ac595601dc62c9c7e1b63** (the value the live run's `--expect-plan-sha256` must match);
    - its booking at `--cap 130`, `data/plans/study1b-plan-booking.json`: e718e315107916f1e7a1bf27a4d1cb9debed72fce5013794b7002021be9e41b3;
    - the runner `harness/pareto/slim.py` (84df9b24de841f73964734680107ebd11b1c68608bfe6a324b3efef9e3a35186): the trial round on used length-sweep puzzles, the limit
      rule, the cost-only cut, confirmatory arms first (hx and om at 16, then 6, all final before any descriptive arm), `--cap`
      required, `--expect-plan-sha256` on live;
    - the driver `harness/analysis/study1b.py` (957f63276197fdcf9c2eee0e8f43b542c63ee8c1be76a4f3ef72b6226a2295d3) and `harness/analysis/study1b_k.py`
      (0d045fc6f96148e6231e2aa467f0dc93660b8bcb2c6cf188d8cc30a3a5155257): B1-B3 with form pooling, B2's k from cost-only rows (cap 10), Holm within 1b, seed
      20261013, the D-97 sensitivity (exposed bases out: 79/38), the D-103(F) completeness rule ("not completed", p = 1, B1 and B2
      together), the exclude-missing view, and spec §6 for a run stopped early ("not completed; descriptive only", "not sent (run
      stopped)", missing and designed counts on every entry);
    - Edith's reviews: `ops/reviews/2026-10-13-study1b-code-r1.md`, `ops/reviews/2026-10-13-lock4-fixes-r1.md`,
      `ops/reviews/2026-10-13-study1b-plan-and-groupC.md`, `ops/reviews/2026-10-13-lock4-audit-edith.md` (passes 1 and 2).
  - **The top-up run** (D-99: its own window, after the main run's; D-100: the wording; D-106(G): a run cut short):
    - the spec `research/topup-run-spec.md`: SHA-256 f048e73a8ccc843f9d575e4fd51a0d462d1e39d5c1635bbad5d1a493170b41c5;
    - the wording `research/models/team_prompts.py` (D-100), pinned in the runner: 14d122c73d3343d0344a20d83f779b2627b5397d1def6b8df923b5c35b4bb498. It and
      `research/e2-and-picker-prompts.md` (2631cac7a7a6fa43d00d1aeca84cd001a82a6f554c01833ceaac960f0c0e9dcc) are unchanged byte for byte since D-100, because the
      runner pins the first; their "DRAFT" headers are historical, and the text is the D-100-approved wording;
    - the run plan `data/plans/topup-plan.json` (final: no draft flag; not before 2026-10-14T13:01Z, latest first round
      2026-10-16T23:59Z, stop and report 2026-10-18T23:59Z): file SHA-256 bd342efbdce2e8bea41c804b57a73642b086e64c87f4efe339ea831403c4ca5b,
      **plan_sha256 d83e13c365d3dc536b9073c4ee4a6955e9b63225227d31e783c4c356a9d17edf** (the topup-1 launch compares `topup plan`'s value with this one);
    - its booking at `--cap 25`, `data/plans/topup-plan-booking.json` (13,640 calls, $165.1569555 at the worst case, round by
      round): ad1a274430745cf409c9a25ea78862b2ab15ec8c4b95ddaa1e04181da1bec312;
    - the runner `harness/pareto/topup.py` (46cfd2af44b2cbf71807fa8974873c4363ef60428a84d23eaa20810a15709fa3) and the driver `harness/analysis/topup_rows.py`
      (06803cea94019553f8f0c51179eb54312033f87858e0d322649ca279b54432c4) and `harness/analysis/topup_analysis.py` (c0d4433f6d29d88e21dc6163335c742b960d294df51ba786e97ef49805392d6c; it
      checks the main run's six files against the D-93 stamp before reading, and applies D-106(G): an arm with any designed call
      that has no final record reads "not completed", with counts only, and enters no comparison);
    - Edith's reviews: `ops/reviews/2026-10-13-topup-spec-r1.md`, `ops/reviews/2026-10-13-topup-code-r1.md`.
- **The commits the runs use (after the tag).** Each run uses a later commit, declared here, that changes only the price table's
  date (or the table itself, only if a price changed, on the user's ruling): `PRICE_TABLE_DATE` and the docstring line recording the
  re-check in `harness/pareto/prices.py`, and the test that pins that date (spec §9 step 4; after Karen's same-day re-check).
  - Study 1b runs at the tag's only child, that price-date commit; rollovers follow the Study 1b spec's rule.
  - topup-1 runs at a price-date commit that is a **child of Study 1b's last price-date commit**, never cut from main and never a
    second child of the tag; `git diff --stat prereg-lock-4 <that commit>` shows only `harness/pareto/prices.py` and its date test.
  - The "only child" check runs over all refs: `git rev-list --all --parents | awk -v t=<tag commit> '$2==t || $3==t'` lists
    exactly the bump.
- **The never-sent records** (spec §2; Edith F-2 and audit A5), made from commit X = `0a2396cae9037de9df72366d1c49e06dd9a2e661` in a clean detached worktree with
  `harness/pareto/neversent.py` (6e3a7437e1668dffd80c66d53a2b07e5f6ef95674edaa9740ef4779e81707540), written to a scratch folder and copied in (Edith N-1):
  - `data/plans/study1b-never-sent-lock4.json`: `8701049746890843e12c4cdbc00211340fcc04af374e34d83c0bf9fd51db3052` (verdict: all three sets never sent and in no other file; 1,098 other files searched in 3 folders; each set's items_sha256 equals its items.jsonl);
  - `data/plans/study1b-never-sent-control-lock4.json`: `411f4ac4b04216a9346e35557438d4b098cc9e1ee1a8a04a9940b6e3e21d0671` (control: main-ledger-l14n6-v1 and ladder-ledger-l14n16-v1 both flagged SENT (exit 1: the control working));
  - the run logs they scanned (`data/raw/<run>/calls.jsonl`, git-ignored, not in the tag):
    - `check-ledger-1`: 92dd68a5b002ba102b7d24e1905de1058e11f1bc84287ab0a0b9e0a628402d77 (20 lines)
    - `diag-haiku-effort-1`: d64316f1e5324395cea13c190328e1c238a99119a0648706d9cca28cd2a362f3 (36 lines)
    - `ladder-l14n-1`: 3725c1cc87dcca8e0107234cb379f9a29c18486c1908e9f1486759d4fb0b52f4 (2,415 lines)
    - `main-l14n6-1`: 0d04ce3870704017d79a7cd2f3603a7f124379f241f13fb3b3ce416bdd02c123 (21,904 lines)
    - `pilot-ledger-1`: 411c877baf3f4b399d44355c6d77126c4abd7c348d17fca194aa0e46d7f79142 (676 lines)
    - `s3-ledger-1`: 9f988dd553368baaa09d8f0bb5e67b001d8ff5a424f1c2fdb5f14a7e3180aca5 (8 lines)
    - `smoke-1`: fffbbf2784dc38fd610049137061fca3623b975b56ce514054b484c738c67071 (1 lines)
    - `smoke-2`: 50e7e07dbe547355ecde6670c138efecb4152006456d470e9e397192097739de (12 lines)
- **The exposed bases** (D-97): `ext40-ledger-l14n6-v1` bases 000 and 003 and `main-ledger-l14n16-v1` base 000 stay in the tests
  as frozen; the sensitivity without them is pre-registered in the spec and the driver. The final pre-tag exposure scan (Jarvis, 2026-10-13T07:21:34Z, after audit pass 2, on X; 759 transcripts, counts only) is `decisions/briefings/2026-10-13-lock4-audit/exposure-scan-20261013T0721Z-final.json` (a78fb10981e8ba72208684b4ae1b24aba733e2058d870b84eed5ae2218e19ae7): it lists exactly these three bases (per-item counts 14 / 3 / 15 / 76), identical to D-97 and to the 05:21Z interim scan; no new exposure.
- **Study 1's results, already timestamped by D-93 and unchanged here:** `data/main/main-l14n6-1/k.json`
  b0f8b05f729b5e6cee6deaa2384c986646217adf72a96772d5096bd2d6e3234b, `analysis.json` 43d18eed62604aab9006cae76a6ee04445170866486d14246fb933646823cfef, the kept group-C analyses
  `groupc.json` e1cbd4057ed94e6735d7a3ca079213d8ea6eba1240b6f5d90244545bb3f773a9 (`harness/analysis/report_groupc.py` b5110387595efe2bc357669022f18c87be05a1368092ebbef00d13ff9e5fa887).
- **The full suite:** `Ran 990 tests in 1287.536s` / `OK (skipped=1)` at X itself (0a2396c), run by Friday on a clean tree.
- **Unchanged since lock 3:** the generator ledger-0.5 and every frozen set, and the spend guard. The main runner, E3 and batch.py
  are as the main run used them (b4ff738: lock 3 plus the D-42 arm and the crash-resume fix with the truncation pause, Edith CLEAN),
  unchanged since. So is the stamped Study 1 analysis (c273eb9).

## The public fingerprint (D-71), computed after the tag is cut

- the tag's commit ID;
- `git -c tar.umask=0002 archive --format=tar <tag> | shasum -a 256`;
- the git version (above).

## File hashes (every tracked file in the tag except this manifest)

Command: `python3 -m harness.lockhash write` (writes this block; the tree must be clean apart from this file); check with
`python3 -m harness.lockhash check` (exit code 0 means every file matches).

<!-- FILE-HASHES-BEGIN -->
```
e85b5f893e61dedcb5a0d83e824f4e342272006e7335d0d4a831f6f08439d2fd  .gitignore
a338d9dc2a57ef48316bb6278401b5683f3e280ea6ee9b9c7fdc23093757d1fa  CHATS.md
14c67dd9ab36baa4f92581616fc9c6b25594c121930160359533cacc8865f76e  CLAUDE.md
5495c7447713107371d80fbe4cc86d4144b7a5e49fb6ea76b5907d5ef2d2850a  LOG-archive.md
3f9b3bea85a6a9255fc6f430eb9ae1e1a4b2e4ca93266ac1914ce6efebc4b1bc  LOG.md
9fbbc9d21a1869e655acbc170ad29f82b61ec718fa6fbd91503f47deb741d95d  NOW.md
2dadbbf6553372f94b0626a10be795d77ec1c58aa08b64ac60d9587ea9376f91  README.md
e25912d418ae9ec2bc2c42d12895ab3324e828265212480ae21db01cc7017774  data/README.md
9854ad98b5beea5f7de18c13baf6640bb78e906aa8551b3c08151aa5fad27b25  data/codetrace-free-test/README.md
5bbe9432f94c454bc26f2f91c5a0b7d20b46c6fe0e5544a7fcb86b6722b9d240  data/codetrace-free-test/answers/c1-a-1x24-haiku-1.txt
2f289fa4be889820d8aff72dcca1a30c0a36630c226dc9bd7121b565e36238a7  data/codetrace-free-test/answers/c1-a-1x24-opus-1.txt
5bbe9432f94c454bc26f2f91c5a0b7d20b46c6fe0e5544a7fcb86b6722b9d240  data/codetrace-free-test/answers/c1-a-1x24-sonnet-1.txt
5afc9a442be988f86d59cf67bc6a29e59e5dcc1c9d8a81e8f2cab2682ad9055d  data/codetrace-free-test/answers/c1-a-24x1-BW-sonnet-1.txt
e9be512caae02f47cf2d74c50a270825d82badc40da125684c39cec32c4bbb4c  data/codetrace-free-test/answers/c1-a-24x1-haiku-1.txt
fd000649c2cc0ed0a695998749bf5f531b065966cf057da420bb774f29bf5d30  data/codetrace-free-test/answers/c1-a-24x1-opus-1.txt
8f0bc31bf86a65874fdf35737be5485460976c919d3a4b5cd8a93be4de74541b  data/codetrace-free-test/answers/c1-b-1x24-BW-opus-1.txt
31dc2401be5303c8ac47c829b4db1f636962510915489cb103ed1c4c85e2e548  data/codetrace-free-test/answers/c1-b-1x24-haiku-1.txt
97e94c25c402f1ea65a162f76b7ce79ee27779b6b6bf1528e2dda339708ec944  data/codetrace-free-test/answers/c1-b-24x1-haiku-1.txt
7e1b79ccb4e45b6eca3bc7be54c209d375f9953b8d9e6ebb65e6c3f7b408e86a  data/codetrace-free-test/answers/c1-b-24x1-opus-1.txt
be47ed84bf7c263bb5d772333f185672873646f73994eb2f5bf243a915663796  data/codetrace-free-test/answers/c1-b-24x1-sonnet-1.txt
dcd48a1cdcc022f1b3adb2d71b3a8080449e88e6274e7a75d88da8d982816456  data/codetrace-free-test/answers/c2-a-1x24-BW-opus-1.txt
4f28cb49eb83482770e0e7dfa570d3ac2e326d9263d93641f5d496c431bf762a  data/codetrace-free-test/answers/c2-a-1x24-haiku-1.txt
d1ca44af2feccbed0e7794b6227bd89d060e2af12ae4cbe038985875499866df  data/codetrace-free-test/answers/c2-a-24x1-haiku-1.txt
1636ac36d5b5238599fd1499b10d2b1ef248523492557d7196a9d9b5ac296407  data/codetrace-free-test/answers/c2-a-24x1-sonnet-1.txt
704ee55453620627a15f3344b5c826b0bfecf263d7a634fbd42e15a8ab853830  data/codetrace-free-test/answers/c2-b-1x24-haiku-1.txt
ce07c5c088841192e8b8b49d06ef238ac4070ed68c557b8c1f38147dbf4f024e  data/codetrace-free-test/answers/c2-b-1x24-sonnet-1.txt
52c13cb99623834ca8154ce1d995ded84d324c2116cf31aabe9bc75878c94295  data/codetrace-free-test/answers/c2-b-24x1-haiku-1.txt
155ee80926efb6e37ad0450a8dec4d93d3a97b935a54b475a56a34ad2a32260e  data/codetrace-free-test/answers/c2-b-24x1-opus-1.txt
bfc3cfe51bbd1a49dedd2bdac0f1a29f74543a4a0e4019ae94b83d1e6726743d  data/codetrace-free-test/answers/c3-a-1x24-AW-opus-1.txt
11cdefe74a2e020db7e1057ddcb80dfc7ea1db25049cb43fd04d20c2c5339340  data/codetrace-free-test/answers/c3-a-1x24-AW-sonnet-1.txt
107f708930afc85acd0318cdbd34fc4b730470b11765bdf6a3d4e3359d13c18f  data/codetrace-free-test/answers/c3-a-1x24-BO-sonnet-1.txt
625ee64925c1dfb204d7f05f649dac21f7d5c45d5800aaadeef619972cfd6680  data/codetrace-free-test/answers/c3-a-1x24-BW-opus-1.txt
bfc3cfe51bbd1a49dedd2bdac0f1a29f74543a4a0e4019ae94b83d1e6726743d  data/codetrace-free-test/answers/c3-a-1x24-haiku-1.txt
02488e9a0d708a317784c18e4bd2e23ef5c7f7d5ddd4badf3b69859a72b167b0  data/codetrace-free-test/answers/c3-a-1x24-sonnet-1.txt
292595b84dc3ea2901f520f5af8151dc11b9bc9debc97565f98400a4b3bb2de3  data/codetrace-free-test/answers/c3-a-24x1-AW-opus-1.txt
292595b84dc3ea2901f520f5af8151dc11b9bc9debc97565f98400a4b3bb2de3  data/codetrace-free-test/answers/c3-a-24x1-AW-sonnet-1.txt
24eff77f8c40190ff9cd2abd6914445e3d401536b218737a13a3b31489c3d1e4  data/codetrace-free-test/answers/c3-a-24x1-BO-sonnet-1.txt
da250f453a722df00c6617538d36d4ed0308e0e634dc45a33c9c25402e862d94  data/codetrace-free-test/answers/c3-a-24x1-BW-opus-1.txt
641b37319fc4fb98277471575f8102e6895958bad8fd91cadc0cdce23f021b78  data/codetrace-free-test/answers/c3-a-24x1-haiku-1.txt
7e13e4bda89f42f3e8caa9e0540dc6a3ee97f76698cf39849d983020d2040ec8  data/codetrace-free-test/answers/c3-a-24x1-sonnet-1.txt
0c35839d2388bc07894c7925c484e815650113c2afe6134b7112d83166ea1f10  data/codetrace-free-test/answers/c3-b-1x24-haiku-1.txt
95cab94c5a087af729a0c20be05d422c5dfb6a72e4beed01d79a66917431065f  data/codetrace-free-test/answers/c3-b-24x1-BW-sonnet-1.txt
197675c5d3028c60eab2b427807da9e01e64e04241b8c2ee3ae681ed90a3c0f0  data/codetrace-free-test/answers/c3-b-24x1-haiku-1.txt
bf7e3280f12f5d6c2a7a5752f5ffee72ed75a5d4cacac20efcbc5c3e42bf14a7  data/codetrace-free-test/answers/c4-a-1x24-BW-opus-1.txt
bf7e3280f12f5d6c2a7a5752f5ffee72ed75a5d4cacac20efcbc5c3e42bf14a7  data/codetrace-free-test/answers/c4-a-1x24-BW-sonnet-1.txt
a8493847cbb1fb04af72d9e169fda8cb02ea7cf9cd3de516962a27c8644363df  data/codetrace-free-test/answers/c4-a-1x24-haiku-1.txt
299272d549a76a217930b8c7c68216773495b31fc0bca84c271d6c454e120ddb  data/codetrace-free-test/answers/c4-a-1x24-haiku-2.txt
a8b37ad15a0d01b384eff15eb9a527a578980fc05cf7591f0a66e717f98ea674  data/codetrace-free-test/answers/c4-a-1x24-haiku-3.txt
299272d549a76a217930b8c7c68216773495b31fc0bca84c271d6c454e120ddb  data/codetrace-free-test/answers/c4-a-1x24-haiku-4.txt
09c70c1ba482948c8d9dee9e207b3957d946b6486a3fdf7bc970b580de9cabb0  data/codetrace-free-test/answers/c4-a-1x24-haiku-5.txt
064941817166f24fff4a4040746db19e9ce27af2e4c471b422147710374cc7ed  data/codetrace-free-test/answers/c4-a-24x1-haiku-1.txt
6260c3ee7f81362604167c19423b42a513248b2aecef04cbfe33c302921e7fdc  data/codetrace-free-test/answers/c4-b-1x24-BW-opus-1.txt
7b2d973820ef88c3f4ee927848f131d5de56d2f45397225fd65cd41d58388efb  data/codetrace-free-test/answers/c4-b-1x24-haiku-1.txt
dc41ab9a19ef9e4b56e970086d08721d69b32217600fb1e62e09dcffa9731748  data/codetrace-free-test/answers/c4-b-1x24-haiku-2.txt
65fb06866df3d2003e12ec7a831751acde696b7f00b9681bb82b2c1bd6af8acd  data/codetrace-free-test/answers/c4-b-1x24-haiku-3.txt
65fb06866df3d2003e12ec7a831751acde696b7f00b9681bb82b2c1bd6af8acd  data/codetrace-free-test/answers/c4-b-1x24-haiku-4.txt
c6f176a90effc7d10d72284b69669a87599f17990d65668bcd56d6e60ba76379  data/codetrace-free-test/answers/c4-b-1x24-haiku-5.txt
4ef4b300b69a47ad3a039cebbc5e00371c5bfda61ee1ccbe6b6989be28f96db3  data/codetrace-free-test/answers/c4-b-24x1-haiku-1.txt
0d6f188de7b3bfae087689d01755f1838c770b55d26ac9b6797b0e9b19e1e897  data/codetrace-free-test/answers/c5-a-1x24-BW-opus-1.txt
0d6f188de7b3bfae087689d01755f1838c770b55d26ac9b6797b0e9b19e1e897  data/codetrace-free-test/answers/c5-a-1x24-BW-sonnet-1.txt
758a82536d7dfa8ee3b262c134b142cbcfa25eeb275d9c66634253b1e896de87  data/codetrace-free-test/answers/c5-a-1x24-haiku-1.txt
0aa878083cf7275c5477cec24ace9f2df857fe61b1db4e3064af76f309d87737  data/codetrace-free-test/answers/c5-a-24x1-haiku-1.txt
ed2f545338a96462539fb76450ac1b3ce47163c324d0e2a9995a759846e57880  data/codetrace-free-test/answers/c5-b-1x24-BW-opus-1.txt
c9b743163f782dff8ca2bacbdc270dae8ff57551c24cab1b47e8ca7f0fb06e3a  data/codetrace-free-test/answers/c5-b-1x24-haiku-1.txt
87e992ab38cef0416b92720b8063403707b1e1db6ebf41fc7d2ff1d5b8b16709  data/codetrace-free-test/answers/c5-b-24x1-haiku-1.txt
cfef563a97eeef3a85db17acbd87b2996cbdd5bbbc647817181a4851551a23c7  data/codetrace-free-test/keys/c1-a-1x24.json
8322ee355944003bf35f6b740fa795d3caa0e16de5eb2d5a8f39103913093b5f  data/codetrace-free-test/keys/c1-a-24x1.json
415890659e437c1cd20718ce773f7d45b2791cc0753e27d5f333ee5576ee16ff  data/codetrace-free-test/keys/c1-b-1x24.json
48ceeaee5e8e61a325743e0780151111dd32272930897e17e53b27da4fcc941c  data/codetrace-free-test/keys/c1-b-24x1.json
92d4d1846b8a7e401ba52ad4753055ffefb8b1325818231bec2c1c56f1a50cac  data/codetrace-free-test/keys/c2-a-1x24.json
98dcaa67ec989c63d32d4a7639d54491ecf4149fd1970016428d4e1511463567  data/codetrace-free-test/keys/c2-a-24x1.json
61bc52ae8f9fc3aeef1e63ef5f967052a8e86181c5f79142efa82e01bc15376d  data/codetrace-free-test/keys/c2-b-1x24.json
79095173e27049fd53280cef42a6fda56b86a9bbcde60096f516bd4ed2ff2982  data/codetrace-free-test/keys/c2-b-24x1.json
f3e0fbc03f8b2c1ec9c835af2714f7d006b231908460982b3fa88adc7befe8ba  data/codetrace-free-test/keys/c3-a-1x24.json
f9fbf2c00d1bf597d68cb70e632becd000ef7c33a3a9680c3263a4df8ad40aa7  data/codetrace-free-test/keys/c3-a-24x1.json
a8eda09036e40fb08a0408f91fe26c8238dd2bb094c929e59d5d7a7d04d3d8f6  data/codetrace-free-test/keys/c3-b-1x24.json
e3b4ef1adf76bffa189f4d8c0ff832ddcf422b98bbd460b2be3ae63d014100c4  data/codetrace-free-test/keys/c3-b-24x1.json
baf53ed77b2a103912145ca9c5cec8e4b4396a0427b08e61228608785a7d2a85  data/codetrace-free-test/keys/c4-a-1x24.json
26d2dc803092f2da8e7b8cc43442bede881bd4bf7efa328c9783150ddf9b8b48  data/codetrace-free-test/keys/c4-a-24x1.json
870d00eb986ea10e8acb23029bc5b33ea3ae825ed8475388451b23ef119f9f80  data/codetrace-free-test/keys/c4-b-1x24.json
daef130b3346ed646068c4dae6ee5642c611a2e021ba7a1add67d1f91e40e7a3  data/codetrace-free-test/keys/c4-b-24x1.json
39e2227606e450398f4e2111febb2701da12e0c43f10149ada057c68e8e19f41  data/codetrace-free-test/keys/c5-a-1x24.json
14a61eec3c8178ab2d4ec6264628b0d113f48d80ae75079913693cffede72545  data/codetrace-free-test/keys/c5-a-24x1.json
1ad5e19224c12d95f1f0f57a517a0893090fb85887e28e36ff7a0a0763a6c117  data/codetrace-free-test/keys/c5-b-1x24.json
197b0b03a6be42a19e933e6a2b601a89d37b91a7b5534de09c16246ab79c3a9c  data/codetrace-free-test/keys/c5-b-24x1.json
7a28e0006eb4645f69070385d13aee56a321f5fc4e34e7668fb103f6846f7376  data/codetrace-free-test/launches.json
bf6193fbc72ec1184148b5f909d72f46149ef42bf6eea287c2735e007dd419e8  data/codetrace-free-test/puzzles/c1-a-1x24.txt
61019e01d7ce641c6e22b51281f2e52adbe6d39e4c2cb7796f9b981cb06282af  data/codetrace-free-test/puzzles/c1-a-24x1-B.txt
7f63a3927663c5455d45442130b638ebeb11db00b0515b46a3a3e42372371646  data/codetrace-free-test/puzzles/c1-a-24x1.txt
fb6fb280cb273e5432e041387a96c768f60ad278a48f7e57efe5f2955b2661ab  data/codetrace-free-test/puzzles/c1-b-1x24-B.txt
8325a926880935193991a22ce9fee958d47f4f6c8ba6dee7a4692d8dc0d70bce  data/codetrace-free-test/puzzles/c1-b-1x24.txt
b05bd8de0f92bdca68cdeaf408c4fe90a9d997cdbdfee7ce2bf0b29a6abbffac  data/codetrace-free-test/puzzles/c1-b-24x1.txt
7a033b1c5571cac2b77d06097a64ad754935ac535d8369bd2f97b79668bda05e  data/codetrace-free-test/puzzles/c2-a-1x24-B.txt
e96a2248cdc3be6520d757ef36971c8f708125edaa3087950b931bb4f561791b  data/codetrace-free-test/puzzles/c2-a-1x24.txt
621e6f5e10fec8e782be1e18018a3aaa5746df4b99379a94e151d5110378fbd3  data/codetrace-free-test/puzzles/c2-a-24x1.txt
f4dcbfe6b62784f4c91aa2b7254a90c57c1d4776b558a1b69a400b2aaec489e8  data/codetrace-free-test/puzzles/c2-b-1x24.txt
aa826a37f7c20bf49b8a4a0f341602e5b3eb9f504a2d088cace839d0ac1de000  data/codetrace-free-test/puzzles/c2-b-24x1-B.txt
b9e74f739c8a34eefb1595fd5e6a59e865e5ca0d64f2bf210ec604c309cd4142  data/codetrace-free-test/puzzles/c2-b-24x1.txt
dbd2b3982170f11e45f9c61ef53d1310ba3c82350dac8d9069b21b6761779aca  data/codetrace-free-test/puzzles/c3-a-1x24-B.txt
95f108818ec40aac415fe5b3c5b72465c367f7c5d4ff1bd89848feba897c6d9b  data/codetrace-free-test/puzzles/c3-a-1x24.txt
3577181b5a56078d30390ca7400a16f555001a1a31b71726c50e67da0cf55df5  data/codetrace-free-test/puzzles/c3-a-24x1-B.txt
a737cb84669e6eac4476bc27802f6734cd0a1c9f2baae7966e149e23e09a60d4  data/codetrace-free-test/puzzles/c3-a-24x1.txt
f5a86e8570d1509e159fb4c5014265317565165faa1c71ef9a811bfc7cfd6a21  data/codetrace-free-test/puzzles/c3-b-1x24-B.txt
96442a6a4be747fc555b30100585ae38b35b9933806e4c657c3f123ff5b87083  data/codetrace-free-test/puzzles/c3-b-1x24.txt
e44cff2b3058ddedceb98f6bf524c906c158d6c99a47c2c0a3aae5d9a0b79799  data/codetrace-free-test/puzzles/c3-b-24x1-B.txt
c589717caea9d54eaea8d03d33b629bc299f45102707d47fe67706ac441230d8  data/codetrace-free-test/puzzles/c3-b-24x1.txt
c9f3081371f2efb4270030333ea86b0c8212e4bbdeedf86df316ec595904a23b  data/codetrace-free-test/puzzles/c4-a-1x24-B.txt
28191a5e414f21f848307d06274c1a7947c8c319f4783e6d96409e25ac8af826  data/codetrace-free-test/puzzles/c4-a-1x24.txt
58a5fd15fb14e3e02ed6d963b1599219aec486d67e8dc3838a075118c075ed62  data/codetrace-free-test/puzzles/c4-a-24x1-B.txt
9484eb978ef456b00b6ed7ab0d263e6235bcbbbc422bb77ba961934e8d0f5488  data/codetrace-free-test/puzzles/c4-a-24x1.txt
ed5f19ea33f42643e40f855a9c6af6779ad3070de7bdfe90df96e0abfe05f4a0  data/codetrace-free-test/puzzles/c4-b-1x24-B.txt
5a808660348904bf78c235d8df3ba66a62183dc826183f19705fb8069aa4cfca  data/codetrace-free-test/puzzles/c4-b-1x24.txt
1c1f6ea5ada846bebb5665d921bc5b86fe5d3b40ea1552280a30ecd041d49d7a  data/codetrace-free-test/puzzles/c4-b-24x1-B.txt
0f51b439e87407cd6af0f357d00ecf5762da8e0d5e2dccd95d116d7cda53bb97  data/codetrace-free-test/puzzles/c4-b-24x1.txt
20547ca09afd29bd968c6d870a1cf0fa8697a99bbae3e1606b3e58bd768864b6  data/codetrace-free-test/puzzles/c5-a-1x24-B.txt
77ff1c34be824bb96faa5a85230c95254b8d974569a98279ea1eb0f76fe00b4d  data/codetrace-free-test/puzzles/c5-a-1x24.txt
dd18e67033ce9891d64f8a7c576182be4e7a1a2d0015955e7a2d06b3561a5008  data/codetrace-free-test/puzzles/c5-a-24x1-B.txt
3f8a67b6a142fb83672a957f3486427ebde9b902e51b6de7d631797399e0d348  data/codetrace-free-test/puzzles/c5-a-24x1.txt
cd15bf92dca3c6e2575f09d49afb4d4c183a789ebc30c31529cf20bfe6090344  data/codetrace-free-test/puzzles/c5-b-1x24-B.txt
5b29c4115336f785b629f9a720c1b60bbd9d7f89cf47bb4987167581f102f4c4  data/codetrace-free-test/puzzles/c5-b-1x24.txt
ba249ce8f3a1cde54636273da6018940c7826c6c8de40cc40843659211609441  data/codetrace-free-test/puzzles/c5-b-24x1-B.txt
f59965c660a254b626354109d463f352fb272ad5c49ec272eb051c9060b12c3f  data/codetrace-free-test/puzzles/c5-b-24x1.txt
f1383369666b41acfe4cd5f35b95319286014cd4311ee66d9d943474548e4ce4  data/codetrace-free-test/results/first_error.txt
8df3b401ceb64fc7ccf7b2dda4bc9440d8b0b2d0f3d23c3c766618a9c2b065aa  data/codetrace-free-test/results/grade_output.txt
95e54b01dd2480bf6fa39223565fc01fffdeece40e6878b41965fefe4994015d  data/codetrace-free-test/results/rows.json
f8f0feb1b001ee815977474b9ab4ce38f82ae8a9990ca5c63089a888306a9ac3  data/codetrace-free-test/scripts/first_error.py
cb9351f9f82656239f310751d5fd8333a2c3f9a00f893ae89e29d0357c351e58  data/codetrace-free-test/scripts/grade_all.py
969124c230b3a772b2ad1dd194b39609653e723fa7d11251504cc99115dc8d8d  data/codetrace-free-test/scripts/make_puzzles.py
f2e9d16185acb868a796887c72d546a2f95015376713a76d4f7e292b1bc535b6  data/codetrace-free-test/scripts/make_variant_b.py
f7bf3f55d506313bc9f72d2c9cef5c10048a4d6ac940ab6e01ad6ceb66bb562d  data/examples/README.md
a1f9b9e31f728df962bf90d7ac6b3a3cc3072053f3e1b253e1256b10eaf00008  data/examples/demo-4step.md
bff0a21bc99072bd5f29dea1c0d99437067e46a291b23fdc547d09a6f02c711c  data/examples/examples.jsonl
5695787c4318fde49b93f89b9440b2a7e6f935b9103153d038cfe39b59caf9d4  data/examples/level-1x24.md
f8daa646da0b95bb4049ec16a7a3887a7e364413bb6927905ea748275960fd45  data/examples/level-24x1.md
9570134b259c8539f4f22304d0a3ea85c3108c560d05cf85f77dc7490648b965  data/examples/level-2x12.md
e93c640a3fe974891765d4eae2fc8cc69bacbd11a5b34edbc4e9c511e320f3f1  data/examples/level-6x4.md
da1e69ad6a01ed464b474572007f7edf7ff4b3254649ec61808133f611a89d4f  data/examples/preset-d0.md
c5ceb64c0a816a806156b90cce4895ed59ba9418063062b1801c976cdf224b8f  data/examples/preset-d1.md
95876b8505c4821fe189f7a52d879c19d590926cdf8ebe1ac9b8fc50faf7c523  data/examples/preset-d2.md
38e35de44aec006ce75c38937fcec03c1eff9123ba2e7cbfb3d4ad74b286f23d  data/examples/preset-d3.md
25ff1ad3979d58ede4e75c8294d25671acd1889cf1c7961fe97a281f2524d492  data/examples/preset-d4.md
075b368d34516c7c73c464382a6793859f13261e1f01807808da3daf01cf6522  data/examples/preset-d4p.md
984060a499274f114c5bbc721d461ba3d0b266b65084720d9d6e6cbc5e38fc6f  data/examples/preset-d4s.md
64e86b0c362ff0b1226059892b1022abb33cc3c4276e4ebeab8f3967747eeb00  data/examples/presets.jsonl
c239e1ad9ad8b3a9a3b575ab3e4b84b448c93b901cf0fd256f59a3d3732e23a3  data/examples/presets.md
be8f8d1a43b614e290ed12153d6910f7c23b04ade50b73c6bc14df59954c5003  data/examples/prompts-d31/code-c3b-1x24-answer-only.txt
171560913bb403b1686b7a8f028af2935ef5d7563a829ce8911bb2c52da5f24f  data/examples/prompts-d31/code-c3b-1x24.txt
4792b62445cf382056d1bc6e45bf4ed79c239840e1df4f99e0df185811ada59f  data/examples/prompts-d31/code-c3b-24x1-answer-only.txt
4792b62445cf382056d1bc6e45bf4ed79c239840e1df4f99e0df185811ada59f  data/examples/prompts-d31/code-c3b-24x1.txt
a2fa150f2c963d79ca76c094134832cc738e1267523ee1bcd890ed4f86815f25  data/examples/prompts-d31/code-step-call-e3.txt
5f7e0bfd477c26e4d36a9ea879043700ac0bae0af8008e34e6f5c5272982f372  data/examples/prompts-d31/digits-d0-1x24-answer-only.txt
32549e4fde1b7c34890bbbfe9c66533f68105ba3501e9b1f82165ba4cf04f75e  data/examples/prompts-d31/digits-d0-1x24.txt
b5fb0edb9c0893b2dfd7d5a724bf9a239005b9d8b414ae4e10c032c94ca85c4b  data/examples/prompts-d31/digits-d0-24x1-answer-only.txt
b5fb0edb9c0893b2dfd7d5a724bf9a239005b9d8b414ae4e10c032c94ca85c4b  data/examples/prompts-d31/digits-d0-24x1.txt
0e3eb27bd9bb1dbe59d8aa5009be738d06cb6750d84f01f54beabb976d95d307  data/examples/prompts-d31/digits-step-call-e3.txt
88d2789e56d598e9afa7205e36f0d81373d3357ca7231d636f0bba9398af1879  data/examples/prompts-ledger/README.md
757316852f34587a89d6c16b7f66e2cf5ebe38dfbbe7e0d9f32f06d73480b4b4  data/examples/prompts-ledger/ledger-l1-1x24-answer-only.txt
2827194817342527faa64f92624356ef880a40496dd4ab6a0f0098dfdf7a19a1  data/examples/prompts-ledger/ledger-l1-1x24-reference-reply.txt
53f265b44683a3fbfe08575c3b5cc7b931888513a7ba749d9b7427ee7be4edbe  data/examples/prompts-ledger/ledger-l1-1x24.txt
ea186fdce64c79641ba4cad77b9fa676aeb203ce4ae510973da49792c624c659  data/examples/prompts-ledger/ledger-l1-24x1-answer-only.txt
859f03428b71c8fc737857c51717efca1913c879d268d806a6d3ab91c067baa6  data/examples/prompts-ledger/ledger-l1-24x1-reference-reply.txt
e89579a4a0d9ddb5024cc2d93ffe39bc982823153cbf42dd650ee2b93a479fe7  data/examples/prompts-ledger/ledger-l1-24x1.txt
f84612933c4cd2c84b2bd0eac15c986948a3f087d1bd64dadfbb7b02718877e6  data/examples/prompts-ledger/ledger-l11-1x24-answer-only.txt
d597ddb3dcab94caf01dc110583ba816bd23981aea490740abcfdbc0e87424f8  data/examples/prompts-ledger/ledger-l11-1x24-reference-reply.txt
d6b7c5aecad163eccd9fbbe1c2b98a7c1d44be1f943e47b577ea8eef1bfcdf7f  data/examples/prompts-ledger/ledger-l11-1x24.txt
9d371435910627b044d9cbf7dd858aefe562cccf84712d91502f7a2b1604032c  data/examples/prompts-ledger/ledger-l11-24x1-answer-only.txt
59a0bc59dfcf98ac287d8e78ad15ba11cea4ed88ca450024d769065bc04cb6d8  data/examples/prompts-ledger/ledger-l11-24x1-reference-reply.txt
9d371435910627b044d9cbf7dd858aefe562cccf84712d91502f7a2b1604032c  data/examples/prompts-ledger/ledger-l11-24x1.txt
7e81e7748b2f514e78b6e3099752b0fdf4e752aa85e6b401913ab895a69821f1  data/examples/prompts-ledger/ledger-l16-check-base0-1x24-answer-only.txt
85447eb04a218ffeec772e12c7db051eb2702fc91de1c0d464ed548add279e0c  data/examples/prompts-ledger/ledger-l16-check-base0-1x24-reference-reply.txt
d20fd0db7b510c74ff6d5aec4b8880d72614ebbc6591c4a8f58b21e6a4f50246  data/examples/prompts-ledger/ledger-l16-check-base0-1x24.txt
bb3e5344b6feb37b823f2902a456d908e621b59f8f9e09a6b8f0e4b5fcb2300c  data/examples/prompts-ledger/ledger-l16-check-base0-24x1-answer-only.txt
2b9d6e6d86e5b76b603fa78d72a54564dcbe1d7031fc87daccb28768c2a3f4b8  data/examples/prompts-ledger/ledger-l16-check-base0-24x1-reference-reply.txt
bb3e5344b6feb37b823f2902a456d908e621b59f8f9e09a6b8f0e4b5fcb2300c  data/examples/prompts-ledger/ledger-l16-check-base0-24x1.txt
e2cecf674087b83af9c70b22c88bcd16718c53a033459f7234cf25341debc3c6  data/examples/prompts-ledger/ledger-l16-check-base0-step-call-e3.txt
32a5a73e8116ed5217c2a03906c4d64bddb723ea379c60b68bd87ac679eb3a7f  data/examples/prompts-variant/README.md
43720c8c0b2ed2974d2beb60337a0989d6c7a4fe0792b9156b994161a84fbda1  data/examples/prompts-variant/digits-d4s-1x24-d31.txt
d66139656c5e5f909145b8d282ead6c50ee3277612b6a6b6b2288e79dc18041b  data/examples/prompts-variant/digits-d4s-1x24-variant.txt
8f7c4c44162b2aa1af4caef80f54ed8cf3e05f254257d268a7736062d2f9cc59  data/examples/prompts-variant/digits-d4s-24x1-d31.txt
1f98997d9db3c9033abaeb87ba31e5219052295564c34429ebbac7eadccaf9a7  data/examples/prompts-variant/digits-d4s-24x1-variant.txt
32e51a374108252509fa1bd1a27ab06a4ab558974741601279950d5decb4d2fd  data/free-tests/README.md
3e2310f618b557d1c5f37b91c3697c2ace89120a48ab79a33a39c86c57f7876d  data/free-tests/graded/answers.tsv
d6e5b88a83881fc4ffefe7c03bd348fbecbdb488e1e4f6e8bb0360ce8f6abc16  data/free-tests/graded/chain_first_slip.md
7412acea86686198b938c1cacb0ba538404e6551847c0ae6570a7d4dfde73f89  data/free-tests/graded/chain_first_slip.tsv
62be7248727c6077647f5af2d7ada53190bad85111807b06b8101ca55d036767  data/free-tests/graded/grade_output.txt
7ec11015b7d3eb45fae95afadd0248ee9fd373441fa84acd5fc58ea5b275bf91  data/free-tests/graded/summary.md
bbb2f5cc888160cee28e3a7c4b8dedeee6920e6c5e3a6d14ba407ecccc27d27b  data/free-tests/replies/index.tsv
a4d22b77e2c0a2c6fc03f0639f3967966b06e4bf2f197d20fe181198d687f117  data/free-tests/replies/round1-sniff-d0/haiku_1x24.txt
4c95d2770546617cd4964d574fdee6a0b30a75f66bf4acd9025e3ebd15ee2a74  data/free-tests/replies/round1-sniff-d0/haiku_24x1.txt
fe3e876716b4ab10e8146bf8d7b59e8f07291cbe777553b06bbc0b5c18497f44  data/free-tests/replies/round1-sniff-d0/haiku_2x12.txt
fd48c4adb46fe6c7cd2c23ab86005871cdadb80e2e6023b60b32de3b118f20e1  data/free-tests/replies/round1-sniff-d0/haiku_6x4.txt
f3934c22999e236d25c7aaaa2a23c4c999b0fd7f8d89e296ed9342950c37fd92  data/free-tests/replies/round1-sniff-d0/opus_1x24.txt
c8072a49a613b7c370a44056762c5a4c275a119c24c016089ef0179b55bf7d0f  data/free-tests/replies/round1-sniff-d0/opus_24x1.txt
c1493846abc688afaa233592f143642a89966cef635f0d6e9aebce908816d806  data/free-tests/replies/round1-sniff-d0/opus_2x12.txt
28367858c74691911414e3fa0e5ae9bb0a669cab0130c6b92af6de897c4ef283  data/free-tests/replies/round1-sniff-d0/opus_6x4.txt
dc3768de7e2a927136fa7aed5bdf868db1bb4a13f44f05914356f705b52bf15c  data/free-tests/replies/round2-d2-d4/haiku_d2-a-1x24.txt
640974baaba09d8e7c58d09d87e792adb16c957ed7bac0ada57a90fcad30eff2  data/free-tests/replies/round2-d2-d4/haiku_d2-a-24x1.txt
0101a0292aae15b55bcd85fad6b3aada745c49e5f71836da5ec735e2d10a6894  data/free-tests/replies/round2-d2-d4/haiku_d2-b-1x24.txt
248c71b412f1404f2b018b8ea08d0dcab416bf752d6c2719a5e8581428a18353  data/free-tests/replies/round2-d2-d4/haiku_d2-b-24x1.txt
0531e2436ec0b5ed155bda6f517d433175b4eae223b4297dad4065e9fb08ea6d  data/free-tests/replies/round2-d2-d4/haiku_d3-a-1x24.txt
bbdd0b13674e8f9d368bdfb0f7531de21c5deb9a9cb0f34995009ce282968013  data/free-tests/replies/round2-d2-d4/haiku_d3-a-24x1.txt
aab08ce4440aa2b551456f2dbf567a263dd5cfa06e0cb7c3701606690583e873  data/free-tests/replies/round2-d2-d4/haiku_d3-b-1x24.txt
c292ac9d5774709838fb978ed0faabbc2ccb6644ea8408efd923b050163b77f2  data/free-tests/replies/round2-d2-d4/haiku_d3-b-24x1.txt
928fed8ea39b7eeca299d233658d802a80f408830e8fc48c1ca4e4c256951ec5  data/free-tests/replies/round2-d2-d4/haiku_d4-a-1x24.txt
2c6bf362681b8460cc388e5e5106af53bf72281ca82b1f691f6efac7f93a12ac  data/free-tests/replies/round2-d2-d4/haiku_d4-a-24x1.txt
dda156de750ddb95a8e933f596cf2cf5759b22c20de9e58a86ad92bd792eea7b  data/free-tests/replies/round2-d2-d4/haiku_d4-b-1x24.txt
953a3fb1a2f7f7a00a9c17962603e25367a3d7d8e5fa5867ae9c82b6948b319d  data/free-tests/replies/round2-d2-d4/haiku_d4-b-24x1.txt
c5866baf86896b7f02f32083aa5a19d1f9f494ccc52f3d7dc00bb39e330f06fe  data/free-tests/replies/round2-d2-d4/opus_d2-a-1x24.txt
208e1e2d4c5b8a7cccfed2ac015fbdbdd4ab3d7c8dcf24e4cc77428995043f5d  data/free-tests/replies/round2-d2-d4/opus_d2-a-24x1.txt
03477a3452313c41dc5ba9ab90d20638ae766eb556c1f50b43567d94bb223d39  data/free-tests/replies/round2-d2-d4/opus_d2-b-1x24.txt
f740bfbcbc16e3be9ab433d394354f853272a0a09073a8ee496fd67a5e479eb0  data/free-tests/replies/round2-d2-d4/opus_d2-b-24x1.txt
261428ee1dc5db5f817f90ea2b49567eea8b7c2361059d4a1ff0b545c0191ac4  data/free-tests/replies/round2-d2-d4/opus_d3-a-1x24.txt
3fe21971b00e1532edcf3cfa956bd4520d1f0544f94ac15538959cdbe575d032  data/free-tests/replies/round2-d2-d4/opus_d3-a-24x1.txt
cb0b29db7d9b46318fd31c6c6ca49393453e8937714ccc33a622d672c61cbfe0  data/free-tests/replies/round2-d2-d4/opus_d3-b-1x24.txt
8dc1ab0019a83f0c8b4344edc8d7c9ad618cf28c9a5555328479c6bc3800cd58  data/free-tests/replies/round2-d2-d4/opus_d3-b-24x1.txt
170d534391ac4e3d6d74aa86fe004393aada0a184597cadf98131058b3397efa  data/free-tests/replies/round2-d2-d4/opus_d4-a-1x24.txt
25d3e891d45cd81d4f3503786a20f6098f50ed780be0f708297ba74f0f5ebcb9  data/free-tests/replies/round2-d2-d4/opus_d4-a-24x1.txt
5c6c41fb890c21a526dca991695c1831e5549d0382c47e5f59250d0cf9bbaa9b  data/free-tests/replies/round2-d2-d4/opus_d4-b-1x24.txt
2a4c59da3e8677a28a90278f9c1dd80f1346e282988e1584a2b56d77b0a77acf  data/free-tests/replies/round2-d2-d4/opus_d4-b-24x1.txt
4be647e0f14209e2d3f3cfa28eab1cf8b382f8e2dd29258229e091a3031c8574  data/free-tests/replies/round3-d4-bigger/haiku_d4-c-1x24.txt
b952fb05fa58fcbb4964aea98f12362a69da8f9b59f2411c48bf2a57d316bb2b  data/free-tests/replies/round3-d4-bigger/haiku_d4-c-24x1.txt
3fe1864050300e38f7594157ad321ee1efbd89fd2a7b9e3f19ad20b98ce4c7dc  data/free-tests/replies/round3-d4-bigger/haiku_d4-d-1x24.txt
d61b475fba7737b9841dc846f7fb5000c614fbcfad11f8099f344c92782fe9d9  data/free-tests/replies/round3-d4-bigger/haiku_d4-d-24x1.txt
46bc980484d1f7581ee02b19e2cdd07d1b96c1a409e6bc559ff431c046d5f2cf  data/free-tests/replies/round3-d4-bigger/haiku_d4-e-1x24.txt
7ead4d4c55561087505ff2fb85647ea538b8028be8465f2cbff9b58eb379ba62  data/free-tests/replies/round3-d4-bigger/haiku_d4-e-24x1.txt
75eeb495202dc65a53592ccf3cf90fb0fbe1ab8a85e9b94139d9000d03853352  data/free-tests/replies/round3-d4-bigger/haiku_d4-f-1x24.txt
e053d3db67ba165b868c79427e8fed4bd2cd7edd35b39578415fc6f7e7923a3d  data/free-tests/replies/round3-d4-bigger/haiku_d4-f-24x1.txt
da0d46a3197acf810b3b9ae34decb36935f9581580aca7736f5ae4a335012378  data/free-tests/replies/round3-d4-bigger/haiku_d4-g-1x24.txt
e63e7f413ce843881fb1b8ccb183cdced5ec00ac150f69873e454abfae5df943  data/free-tests/replies/round3-d4-bigger/haiku_d4-g-24x1.txt
2a4b721a4e457f8c8a4eb7812335250de156fd25bfddc788dc9dcf299d8164ad  data/free-tests/replies/round3-d4-bigger/haiku_d4-h-1x24.txt
4b56e393e575b81434044d30ac84c971c48faa2c91dc87cb09933cc867402b0f  data/free-tests/replies/round3-d4-bigger/haiku_d4-h-24x1.txt
0ea8e09349f9ed70a23dbf8254e5d98d8395502a4aaa32a3d65907282044372c  data/free-tests/replies/round3-d4-bigger/haiku_d4-i-1x24.txt
8bb580e6fa7bb7439587458e62e9510e11c8a123b0a99b262a0d63b241e757b2  data/free-tests/replies/round3-d4-bigger/haiku_d4-i-24x1.txt
ceac05c76d39ee6fddd3f67530f81eb4dd2ad1f69079c572b791ecafbf4388dc  data/free-tests/replies/round3-d4-bigger/haiku_d4-j-1x24.txt
f9717c8d374387d2c86bbe22c08090f51bfee7ff528b74fe71327023a24f531b  data/free-tests/replies/round3-d4-bigger/haiku_d4-j-24x1.txt
49e8be9af8959149944ac1a80b98b394fccfadc35ffd20879a8719cbf0faa392  data/free-tests/replies/round3-d4-bigger/opus_d4-c-1x24.txt
3f0a7db98fce163e5514c5839b30a11dc01201cffa39595523e2f1f4aefc12f7  data/free-tests/replies/round3-d4-bigger/opus_d4-c-24x1.txt
2a4305819f6cbc80de170da3c4f904e4b29699fd829994be342f178702e48f79  data/free-tests/replies/round3-d4-bigger/opus_d4-d-1x24.txt
1692a3c03a7130c5dd2db32c5531578e5628e5ee828008ccc96edc64c7812542  data/free-tests/replies/round3-d4-bigger/opus_d4-d-24x1.txt
957bfe4cb5caff4d468c587f50a62eec7fe7a9499d43929f599523b9623b3d21  data/free-tests/replies/round3-d4-bigger/opus_d4-e-1x24.txt
86762c54835a5311268bf8ce13895ce552427b827f69cbdaee5f57141cc79032  data/free-tests/replies/round3-d4-bigger/opus_d4-e-24x1.txt
526616426b40caff8a36893f5532f67227111748ebe6f71e1847bbcb13ceb559  data/free-tests/replies/round3-d4-bigger/opus_d4-f-1x24.txt
885eca88018450b42b78032e7fd564baaef0b6d7d765791df153557feda0c0e5  data/free-tests/replies/round3-d4-bigger/opus_d4-f-24x1.txt
89fc3fcf09dd45a856c60a7462343131e84d44d8224da74e36a20a4539733d33  data/free-tests/replies/round3-d4-bigger/opus_d4-g-1x24.txt
13f86da473be23c0578cec925d2b1eebfad9a9c16eb76803f20ab209277d2c0d  data/free-tests/replies/round3-d4-bigger/opus_d4-g-24x1.txt
455c2444c3148c2ba8208b46ffa61a4bce13fa140d6730a5e4909c837a02f838  data/free-tests/replies/round3-d4-bigger/opus_d4-h-1x24.txt
731e54c2e637a2f9d1791de0b8accc12e4d90189ae030fe8148530bf424cc04d  data/free-tests/replies/round3-d4-bigger/opus_d4-h-24x1.txt
74dac3eba722c338b2d596c120cf6db40b16c6f987bbfa7ffb3e39648ae53acc  data/free-tests/replies/round3-d4-bigger/opus_d4-i-1x24.txt
f298ede861d56ab100b0c80fb957b1e7ba938051cdb7fb93e732512c1b6483b7  data/free-tests/replies/round3-d4-bigger/opus_d4-i-24x1.txt
8f77a38394fe37c26dafc23c576629be0ed42609c530e5f8796f8232c6e7973f  data/free-tests/replies/round3-d4-bigger/opus_d4-j-1x24.txt
7c48809d2b433c3aba7bd87e79a476f6b378b046bc65f9d4ea19a41c273e08c0  data/free-tests/replies/round3-d4-bigger/opus_d4-j-24x1.txt
1c0fd5382b0a49a01d81f7ba98295110b473fe0ad71895ec5e5183e5911cb9e9  data/free-tests/replies/round4-repeat/haiku_code-L12-a-1x24_try1.txt
95d333dbd37e014be1a9c8bff954f0a4c0fc9d490a8ae3030bb638791894376a  data/free-tests/replies/round4-repeat/haiku_code-L12-a-24x1_try1.txt
5168a645a5692c8eb81a9f0d4942d35fffad180a853280e98a246bfbc333ec04  data/free-tests/replies/round4-repeat/haiku_code-L12-b-1x24_try1.txt
63bd1279a93b5ae3c27f839abc2c59488011afa35a84a09a16cce9d740c9ad91  data/free-tests/replies/round4-repeat/haiku_code-L12-b-24x1_try1.txt
9d10732d24a976ae29a89aed06ebd59f4c645acd5de6cb82fc42cbe1f162f40b  data/free-tests/replies/round4-repeat/haiku_code-L8-a-1x24_try1.txt
e6da2f8c8bf1baf6843b16ba3218bd93506cfe8977392b912e70380edb336b8b  data/free-tests/replies/round4-repeat/haiku_code-L8-a-1x24_try2.txt
981b671127043266c3451b1a37060b2d55645f355f5d103ecd94cd557a5e9bb4  data/free-tests/replies/round4-repeat/haiku_code-L8-a-1x24_try3.txt
649a4fb12d05f9ad9154ebc62bbd09b4fb0ffd1bb74404446ad18f0eb5035d8c  data/free-tests/replies/round4-repeat/haiku_code-L8-a-1x24_try4.txt
74e1589a5892dc225b1cbabc36ff3930b47d71c8fb3e79188b53e6b22730cbae  data/free-tests/replies/round4-repeat/haiku_code-L8-a-1x24_try5.txt
a84f1189e09dd5aa06ae6052fd7cac6c9d46d05f6f05903e95847447855be991  data/free-tests/replies/round4-repeat/haiku_code-L8-a-24x1_try1.txt
00c81ceb7b89a905b587ef55020d9c895c9959dc10c41c637d6c130b2578e5cf  data/free-tests/replies/round4-repeat/haiku_code-L8-a-24x1_try2.txt
10fab366d5c1a7178000a78ffabc3f6d643a1f585c9f123d6a3c22f563df0077  data/free-tests/replies/round4-repeat/haiku_code-L8-a-24x1_try3.txt
aec2e85d16b813e8fd53dd4c6b5f51046f114f577ee17af32afbc4224e16673e  data/free-tests/replies/round4-repeat/haiku_code-L8-a-24x1_try4.txt
54186385589f3d0de7336c1ceb1f18a5afb4609b364ffe3f886ce8d1666fc3d9  data/free-tests/replies/round4-repeat/haiku_code-L8-a-24x1_try5.txt
ce08948e3ca9a7ba6531f8bb3e993c603741c1318252b8ef32c1e5878d495063  data/free-tests/replies/round4-repeat/haiku_code-L8-b-1x24_try1.txt
60d5e96021cd13b21031ef3369a24bc722753a3964f38ee7e62685ce95d0b985  data/free-tests/replies/round4-repeat/haiku_code-L8-b-24x1_try1.txt
42d0c5ee86aac7e6937d57fff7c9111e401d0c3d9acdec65e3b4739f1c94c7c8  data/free-tests/replies/round4-repeat/haiku_dig-x-1x24_try1.txt
e315366a96c55d785dc3584f443b9a9fe34d0cacd1f5b2ff70de2d897e83f14d  data/free-tests/replies/round4-repeat/haiku_dig-x-1x24_try2.txt
63d0c06d610bd522fb37cbee8622d4ac051ffb6147af747c4d7ea185db45d693  data/free-tests/replies/round4-repeat/haiku_dig-x-1x24_try3.txt
abf59e63570f2d4d406795187b955047efcc9d6942a3bbeaf6d793734185c99d  data/free-tests/replies/round4-repeat/haiku_dig-x-1x24_try4.txt
a8d3a0ef1f1c534986f1230b5eb3e89c09d2a7df6ebf525583482b827bdce2c3  data/free-tests/replies/round4-repeat/haiku_dig-x-1x24_try5.txt
15f0d2d6ce4f235f0db0726dd09ebe187e4d2303891551bb1890b31eb35d4140  data/free-tests/replies/round4-repeat/haiku_dig-x-1x24_try6.txt
883d1216548b745e9b6809ab23d110f39ffe372720582517f76d3ec67fafa777  data/free-tests/replies/round4-repeat/haiku_dig-x-24x1_try1.txt
098132f777550ed2301a84f39696f0c45cc3b86379f124eac0cd187a91298861  data/free-tests/replies/round4-repeat/haiku_dig-x-24x1_try2.txt
be6a7aa7a80118e25c78ccb85634c1f7dff895d202061fe6fb7937025017dda9  data/free-tests/replies/round4-repeat/haiku_dig-x-24x1_try3.txt
f7001536fe1b99e8bc93d8369f10a086a1cb630aec94ea96a544f9cd5a58dd26  data/free-tests/replies/round4-repeat/haiku_dig-x-24x1_try4.txt
eef1a7b69d612bb25b8d6dde43e54961391ed0e7523a62e79483d9af6aa30120  data/free-tests/replies/round4-repeat/haiku_dig-x-24x1_try5.txt
181963ce21d6b8b3cb97ef1cf53e9ddf33a829a41f2f15fe91e720d57671cf6e  data/free-tests/replies/round4-repeat/haiku_dig-x-24x1_try6.txt
f6e9ad49d2984d4f85c847d4303c7e15bd26a1236f899ef288927afd63c213bb  data/free-tests/replies/round4-repeat/haiku_dig-y-1x24_try1.txt
6e459a5dfcf45249993d76bef8df9b56b26df705d24b7f4ddc36028ab7ff2c36  data/free-tests/replies/round4-repeat/haiku_dig-y-1x24_try2.txt
86d148266d27616542d9508f5f3bd50c6854a996af730f92d2cfbd5f312812d2  data/free-tests/replies/round4-repeat/haiku_dig-y-1x24_try3.txt
fa79afb06d6b049ff2f13886a8228ed1533d6ddb1dc3f7f61cd32b9573d6a8a5  data/free-tests/replies/round4-repeat/haiku_dig-y-1x24_try4.txt
355d28b519dceeecec3e90a4e55fe4faeee7d42d1d4aa09d0bcb646550deef71  data/free-tests/replies/round4-repeat/haiku_dig-y-1x24_try5.txt
2f14f15a65811fe86ad7ec7b751e0c95c7d887f9f35f0c96968009397957723c  data/free-tests/replies/round4-repeat/haiku_dig-y-1x24_try6.txt
e57ab26c38233b25007e94ffd801b86bf016be480107dab7350946fd2db5e91c  data/free-tests/replies/round4-repeat/haiku_dig-y-24x1_try1.txt
d5d22d6fffecef1d69f0d9518c45ca883fb407ea9c6955c0605861c707652a0f  data/free-tests/replies/round4-repeat/haiku_dig-y-24x1_try2.txt
3313f67be3018fcbfbb07095977f38ffb0a34ae362765546da6edf404b2ff948  data/free-tests/replies/round4-repeat/haiku_dig-y-24x1_try3.txt
6ddd646fed1826bb48b57df5ed34d2f8941669cf0aba38c517c30dfca67cc788  data/free-tests/replies/round4-repeat/haiku_dig-y-24x1_try4.txt
58766f7335272e8090d9edd241ec3b8074a9028b98028699d5d79708ed460048  data/free-tests/replies/round4-repeat/haiku_dig-y-24x1_try5.txt
965ae78cd677185a63f58e425a4d06f34b98e24f75a8de127412352ae706bb5c  data/free-tests/replies/round4-repeat/haiku_dig-y-24x1_try6.txt
37337850f463e22c993f93bd9fbcd3c4ca14dfc4722317264c5285e1103904c6  data/free-tests/replies/round4-repeat/haiku_dig-z-1x24_try1.txt
043c0904b95709dc2e1812571016dce3448a3dd2e639044e22e31fb58947eb73  data/free-tests/replies/round4-repeat/haiku_dig-z-1x24_try2.txt
fb7a4674be40ebbecc6dffa3ffd15092e85c5132e9050ad2de2c4d93ee17b9db  data/free-tests/replies/round4-repeat/haiku_dig-z-1x24_try3.txt
1c2afd7159d2dc6b735233c051775e4a76283e338b888c41a8e46be38d96ffbf  data/free-tests/replies/round4-repeat/haiku_dig-z-1x24_try4.txt
dbc20f830f0e802b40a57a3831c4622ec6c50172428e3790243d80039907a454  data/free-tests/replies/round4-repeat/haiku_dig-z-1x24_try5.txt
e5e9a65d7e45e47a4a149aaeebb7bf9aaf8c67c53073e60ca1af674c93090b47  data/free-tests/replies/round4-repeat/haiku_dig-z-1x24_try6.txt
1232e02c81feaaef0777a58fa030ebd816834447709ec6c5fef2bb82daa900d7  data/free-tests/replies/round4-repeat/haiku_dig-z-24x1_try1.txt
6c4847340c11b8f4e5532c60d5e5f1a0f9dad8f1a51cc7fafd7936c58868a069  data/free-tests/replies/round4-repeat/haiku_dig-z-24x1_try2.txt
833cf46bdf48e243ac5d824c8bc02e3cf6a14d403091c13874f21d679cf28087  data/free-tests/replies/round4-repeat/haiku_dig-z-24x1_try3.txt
809732cb5afe8c76e9234f04b55d3062934f0d0cd00e6a074ab870429d37102b  data/free-tests/replies/round4-repeat/haiku_dig-z-24x1_try4.txt
5eb66a7f07653303acd1227b2fe1d8f01638521fd0cdbab24dee714a9e65293b  data/free-tests/replies/round4-repeat/haiku_dig-z-24x1_try5.txt
b147c3796d4cfaf5dffe91acc570c92553f3b7e7c2c65c36e6fc7e9df931c1f5  data/free-tests/replies/round4-repeat/haiku_dig-z-24x1_try6.txt
8032eb2c5f2f90337516af3a8ba2b7efa78b450f9422f78471ccfdb9e1af2cbe  data/free-tests/replies/round4-repeat/opus_code-L12-a-1x24_try1.txt
593510ebbd7e5dd1432a33b5b3c9d43cb19f53a632d1a08870d5c80e491c2ba2  data/free-tests/replies/round4-repeat/opus_code-L12-a-24x1_try1.txt
6cb51eb70f72ab3d49ac163879060e8d63c9469f03290771a15baf9f4f8b44c1  data/free-tests/replies/round4-repeat/opus_code-L12-b-1x24_try1.txt
4322abc02f90c64099fbbd0abd0a6f5b38d538d0c3a9f056e96418bcf1428fd6  data/free-tests/replies/round4-repeat/opus_code-L12-b-24x1_try1.txt
fb6fec0d5bd2dba0bb4df35bcf055083e5433113535e908f639b1b482c870f27  data/free-tests/replies/round4-repeat/opus_code-L8-a-1x24_try1.txt
a9b56a3197383893f3a9fef0fd645efa0952ed624054688d4cdc9c780e67818e  data/free-tests/replies/round4-repeat/opus_code-L8-a-24x1_try1.txt
4b1dadcbd9b6ac9e4720b317efacca674645847708b74e3643d5486ca968cd8f  data/free-tests/replies/round4-repeat/opus_code-L8-b-1x24_try1.txt
6497710da531c6af777d48d892263ca8d9d6b3f4dcab2a9f88e921685fcef430  data/free-tests/replies/round4-repeat/opus_code-L8-b-24x1_try1.txt
e1ebbecfc9133412a41f5b38193037fd4b2d526af48dcc7d054de24cd0f97468  data/free-tests/replies/round4-repeat/sonnet_dig-x-1x24_try1.txt
37d0087db1cf13a78671967b6ea4f270c7927f2806430dbc05b3d4ec854973bb  data/free-tests/replies/round4-repeat/sonnet_dig-x-24x1_try1.txt
55a446d8fe8b13b60f7f7ec7ac88bf9a2840fa080c24007f620680f519b6e2c3  data/free-tests/replies/round4-repeat/sonnet_dig-y-1x24_try1.txt
f12ea9ea02c7e43875967781cd5a996ceed28e9bc1f7a0c8bf67b6a4aa450481  data/free-tests/replies/round4-repeat/sonnet_dig-y-24x1_try1.txt
8975ad68c9ac716c13e7b90aa8d1f9fd47d90f752c64c471218abded013b4825  data/free-tests/replies/round4-repeat/sonnet_dig-z-1x24_try1.txt
b2c7a2fbb8ca7f64fd3eeb5ffec02f074a60610ae2a97d285c1a7aed76fc248e  data/free-tests/replies/round4-repeat/sonnet_dig-z-24x1_try1.txt
ec40a674a979681a859e50ca729c301a403eeb460f3d341550b8eb16270b14d9  data/free-tests/round1-sniff-d0/keys/1x24.txt
fcd789c6d56bbff59a453bcc8abccb34d53042d2c2a331ae8d884bbf46b4d864  data/free-tests/round1-sniff-d0/keys/24x1.txt
8df4b98b82782eec027041972002f510966c6d4752241807708ea6057d12c4a8  data/free-tests/round1-sniff-d0/keys/2x12.txt
b6c2d71e8832fa62f1d25072868cf1abe7f565364ef2940606e978a115ae40a4  data/free-tests/round1-sniff-d0/keys/6x4.txt
55f18a771279b04e5c96853b74423607e74133900e4d05f51e75e707da0d3f98  data/free-tests/round1-sniff-d0/puzzles/1x24.txt
9e0e32660c1c8eb9a7719a06c86bf74b176d2a0daf783b15526b1c9fd9cb2b5c  data/free-tests/round1-sniff-d0/puzzles/24x1.txt
bd976a755da4a38531e0504c213c3c67dbd6cecab1cb073b668c397af80585f4  data/free-tests/round1-sniff-d0/puzzles/2x12.txt
1d0950345e28798a467518547556bf0502b70cbf89c55ab0ecd5120e0e6da011  data/free-tests/round1-sniff-d0/puzzles/6x4.txt
45e882b475104a29a1c7bf4526ca08c29c7b7d0fd7bf8312550345a885396146  data/free-tests/round2-d2-d4/keys/d2-a-1x24.txt
57c0e782793f580cf0550ba5457e4e5365990fb1b2af316d6498ade541236ad5  data/free-tests/round2-d2-d4/keys/d2-a-24x1.txt
be29b495d5beac1bd041e30c804ceeb7c005c4428e24ad8106b296b86172bfa7  data/free-tests/round2-d2-d4/keys/d2-b-1x24.txt
fe85058f810c24d59717e611237f44a32f4168f152f007e42c2320763a3fc297  data/free-tests/round2-d2-d4/keys/d2-b-24x1.txt
39ca623cf96d29e1260ed23e47b6cd25854508a6ff347e87a2811daa5e526c87  data/free-tests/round2-d2-d4/keys/d3-a-1x24.txt
26525834bc645f3a7d3cd90fa4abff175de16de6106f3481e2e68cccef0c694a  data/free-tests/round2-d2-d4/keys/d3-a-24x1.txt
9ed0dc531cb85a7df897ec1ce2683663a94293693dc510b6c85e5b79980d1f12  data/free-tests/round2-d2-d4/keys/d3-b-1x24.txt
a77c28c3e8f109e83dd74aecbee3114d7c311eaff1a838447ca1a87977d5c8cf  data/free-tests/round2-d2-d4/keys/d3-b-24x1.txt
1f8caf22eb6b66b7b5d369f78d4cc9c8de2237501c47e92eb9a5c4075c04b654  data/free-tests/round2-d2-d4/keys/d4-a-1x24.txt
cf77c7fe097c654521bde6cb577a30cab14e1d2ce3741ce60606200a6a0a15f1  data/free-tests/round2-d2-d4/keys/d4-a-24x1.txt
2105ecd943e07cddc653d544f413c3dba2d9d7216670963c5dc2f66db08e70d1  data/free-tests/round2-d2-d4/keys/d4-b-1x24.txt
da82a62ea5dafc9fdb2207db29fae1bf7f6394b3205f35071895c1c3f77f3b27  data/free-tests/round2-d2-d4/keys/d4-b-24x1.txt
dd867bc9f4ebd3ecb75b726ff33bf11a011a0f67abb1ed3f0bbfa73c119cfe09  data/free-tests/round2-d2-d4/puzzles/d2-a-1x24.txt
7b755045ca39fa0878ffb20d7f62a52ccff1618d4b1841aa0c6a5144103e41d4  data/free-tests/round2-d2-d4/puzzles/d2-a-24x1.txt
c3bc688ceba27c035b5b898974383b76541324a10767c5612205cfcf2b3ec585  data/free-tests/round2-d2-d4/puzzles/d2-b-1x24.txt
e967739a1288012c4c944b99f16e0164a478319049efc4ae893434b04f4ddfb4  data/free-tests/round2-d2-d4/puzzles/d2-b-24x1.txt
6dc7e494e291b0db128c0c6893b45c421079fb5d5129ed0f9089a64cafe265e1  data/free-tests/round2-d2-d4/puzzles/d3-a-1x24.txt
17e5c4b4d17628b6adefca97ee11c803c03492d9fb0b9186585d51c982281d1c  data/free-tests/round2-d2-d4/puzzles/d3-a-24x1.txt
3b073f4b14d4998aa4f67fa6aef7b85eb3d2cedb2d561716a4dc75bf7b5cf9f3  data/free-tests/round2-d2-d4/puzzles/d3-b-1x24.txt
8aa133aa86edb36a633a7e18bd0b1fa9afb377a7505d9d0a829518334a393c6d  data/free-tests/round2-d2-d4/puzzles/d3-b-24x1.txt
dd003fc342a2010f8d51d08b1cb0de804767e0e76f14fca706cfc48848ff209d  data/free-tests/round2-d2-d4/puzzles/d4-a-1x24.txt
2af68a48470ab0f3feff29b58148c5c61f398c0e93a6ef885a9e11a1fb9a66ce  data/free-tests/round2-d2-d4/puzzles/d4-a-24x1.txt
8647192e5d3f0b7e9c52e243c30afebf498c391a0153b888b0aaa9d300ad803e  data/free-tests/round2-d2-d4/puzzles/d4-b-1x24.txt
257d5b8e983a02548e33a54cf46f1b797abc7c2792aa19218b3179361007002c  data/free-tests/round2-d2-d4/puzzles/d4-b-24x1.txt
d6929f0f5b926c59df5fa52a8423f4c2f74fc0e2a966696cf446c3cf5a4fb6cd  data/free-tests/round2-d2-d4/results.txt
2fdee15bcdd6d893370d1eca7d632c93b863c0259cbe58a06691adf82e5143f3  data/free-tests/round3-d4-bigger/keys/d4-c-1x24.txt
1f3567973ff457651233a53a3c6177416e769597d2cca899dc19ff05698d9a19  data/free-tests/round3-d4-bigger/keys/d4-c-24x1.txt
a6bd630e15716e8f221e686a4dc3ec15ffe3249217e2e75e19d8725ad77ae899  data/free-tests/round3-d4-bigger/keys/d4-d-1x24.txt
9db5ff0fb018b70f32c6504a85b66ad3325d5a130cc2bd50344cbd6e1357b141  data/free-tests/round3-d4-bigger/keys/d4-d-24x1.txt
e6a44383cc1515dc412fd9fea6b1990b9317197fa3214b2b08db9244b882279b  data/free-tests/round3-d4-bigger/keys/d4-e-1x24.txt
7f734edd0396330933ad29854ba3dd275e4728f8207b5e7f2f863a9d91471ba2  data/free-tests/round3-d4-bigger/keys/d4-e-24x1.txt
4efd36fcc44ad05d0f1b14f1bdea1c4aa71c3106e739920d5d10cee69d22ef34  data/free-tests/round3-d4-bigger/keys/d4-f-1x24.txt
78741ad85fb238b14ae7045ecf280c70439ce7ef9410b1b7423032d9de1e266f  data/free-tests/round3-d4-bigger/keys/d4-f-24x1.txt
a5153758442be79bf4d0106728bc9beafecff53456ce4ec9f63e7651f3b0b9cf  data/free-tests/round3-d4-bigger/keys/d4-g-1x24.txt
f5615690124097e6e6b530ccd1ccee54320918a3f7dc36ae13c34e6a2005eba7  data/free-tests/round3-d4-bigger/keys/d4-g-24x1.txt
139ad117604b6fbcce2e3f6c2dc21b0b3402cca283661b466d2a53232a8125c9  data/free-tests/round3-d4-bigger/keys/d4-h-1x24.txt
b9cf954902ab457dc977a59bdaa3f2d64a6b85654a206fadcae956f05e1f772d  data/free-tests/round3-d4-bigger/keys/d4-h-24x1.txt
58fcee472781705cee0fe8b25419dcad4f3861971eccd23a8acb489f14d4a7b6  data/free-tests/round3-d4-bigger/keys/d4-i-1x24.txt
5bc60eb989df837734a0ab8cf785b7e9ac7f33b1d7ecc426c2dbe5b997b25660  data/free-tests/round3-d4-bigger/keys/d4-i-24x1.txt
05db177451966e949fda82e93f3761a09735b4a1de0c1a8fd90aecf176928c48  data/free-tests/round3-d4-bigger/keys/d4-j-1x24.txt
4a9a964a3a04b9d2582d4e6972ddb0e4c4924a393d6b196d1db2da38ae8ce03b  data/free-tests/round3-d4-bigger/keys/d4-j-24x1.txt
b9997d370f1ba1e3b547df3d8ee1ddb8138b92c5210eaf7abe970af83bb19cef  data/free-tests/round3-d4-bigger/puzzles/d4-c-1x24.txt
67772db2b1c80a850c2d99d0275b68c64bdeb37fbe6122e3a90acf71ce622454  data/free-tests/round3-d4-bigger/puzzles/d4-c-24x1.txt
8c5a14afd00f7751e78bc3ee3435be3b4c4fb06d88e2f9c37d98430d22ae253f  data/free-tests/round3-d4-bigger/puzzles/d4-d-1x24.txt
9bd3aaf0c421cdeb1cee53a860399a37745ad92fd5b0a6d5fa600713f9fb9d8c  data/free-tests/round3-d4-bigger/puzzles/d4-d-24x1.txt
8a84d952e2dc430a6d123c744ed43f797cefc8317902b6197b271ba5661be2b6  data/free-tests/round3-d4-bigger/puzzles/d4-e-1x24.txt
1beca4f7dc4ba6580b0bd44531236f5ae91ed5be2ac1e6367cfa769fa731a670  data/free-tests/round3-d4-bigger/puzzles/d4-e-24x1.txt
52d5e69b0296574e64a37f015a9ee438a1a26b962d5215bb8b4c331d99c755d1  data/free-tests/round3-d4-bigger/puzzles/d4-f-1x24.txt
cb8adbb42ccad1e6859d4db4dc68864faf4e770da08e2ddff559141a56e944be  data/free-tests/round3-d4-bigger/puzzles/d4-f-24x1.txt
c2c4ed678fe075f80b8c976ddb909b23133c09324ed0752f81240998ac13e040  data/free-tests/round3-d4-bigger/puzzles/d4-g-1x24.txt
43620e8fc194e5e91801a315b16d5bda4daaa13b142eabc2f0152d8c68226d19  data/free-tests/round3-d4-bigger/puzzles/d4-g-24x1.txt
403e73d078e318f6b1b43600a5a6d2e64071f90c8f452aa3534f6f2ab5c7a989  data/free-tests/round3-d4-bigger/puzzles/d4-h-1x24.txt
be2521784c6892a4870cbcc740db0b96d69ae7d75174000432893eac3962a26a  data/free-tests/round3-d4-bigger/puzzles/d4-h-24x1.txt
b34e4ae5373e5cca53bb3b6ce8e4d1effb62b34d503de47bfd7bdf187170e3fc  data/free-tests/round3-d4-bigger/puzzles/d4-i-1x24.txt
93565a8d4301c8070769f00f8feb6f17810360658d091009b15fc21942532b5b  data/free-tests/round3-d4-bigger/puzzles/d4-i-24x1.txt
5adf591adccc49e908fb302652daa7effccade4b257cdad0a46e47baa929df37  data/free-tests/round3-d4-bigger/puzzles/d4-j-1x24.txt
ca214a25b626188e771556665466ad3008597afe79d33c11ecc5addf45b56950  data/free-tests/round3-d4-bigger/puzzles/d4-j-24x1.txt
228b39d3d72c4d454b9465aeacaa962ee280f32abf2132e16ef3e8c1f1f2b680  data/free-tests/round3-d4-bigger/results.txt
e590020d733f337d71afe147cd6f8967e537813abc4d097f4d16343d23e576f5  data/free-tests/round4-repeat/keys/code-L12-a-1x24.txt
ce925c5c4ec73eca47783b4634636185b95f2a8a56ea4c75cfe0d0993aea066c  data/free-tests/round4-repeat/keys/code-L12-a-24x1.txt
65b0b6a7dfd0a601d61f2ffdeb594bb2732aa1b36ba6ac2a181a24bbe39a9dff  data/free-tests/round4-repeat/keys/code-L12-b-1x24.txt
5fa0c36531ddc5caa14bac60eab06d1e684d2131ab7b7927477d7b4489aff3cc  data/free-tests/round4-repeat/keys/code-L12-b-24x1.txt
99c8ab1dde1166f924a9e3e0c2e938a48a4bb52baf9e1f291a803daa3dc7175b  data/free-tests/round4-repeat/keys/code-L8-a-1x24.txt
4838d965213e9676d209e8d85d1828d7dc98be261e89eb9250ed009fc75027a7  data/free-tests/round4-repeat/keys/code-L8-a-24x1.txt
06ae781b9a046d67c890ef7ed2b76bec1b1f398f911ab2f7a63d154716818863  data/free-tests/round4-repeat/keys/code-L8-b-1x24.txt
984eb2d01b2486049589a4493acf9722b3c6570ae9a41ec29436bbea89dee955  data/free-tests/round4-repeat/keys/code-L8-b-24x1.txt
a5f2ac1441d373c6e6b99fff6b5e426a755492544d2798d8846720d89be4c032  data/free-tests/round4-repeat/keys/dig-x-1x24.txt
78960a155d04e4df1c1cd0c46540e21ab84105d1acaf0ee90dc7cc8d76b9084d  data/free-tests/round4-repeat/keys/dig-x-24x1.txt
d67385df26c9f8f11424171978a62f8f36541d75bfa764aa35607912275b1b68  data/free-tests/round4-repeat/keys/dig-y-1x24.txt
31d8f2e86b1835e43a5e9a85f0e232357b0a37d002bfb7adf308e9ef95bb153d  data/free-tests/round4-repeat/keys/dig-y-24x1.txt
ab9ca27a65885f89a366a0c6f00a60bc2b369c76ff79cbe6228554f7620bd97e  data/free-tests/round4-repeat/keys/dig-z-1x24.txt
c18fc192b95ac7c52bbcc29b4f6037c450ff8c4556de39629f9c9aad2b385485  data/free-tests/round4-repeat/keys/dig-z-24x1.txt
39e60ec5085661f0bb130b0dd1fd9d4083d7a1307ddfcb3f501b00cd041c8572  data/free-tests/round4-repeat/puzzles/code-L12-a-1x24.txt
02d734b55170e2acfd04ffd01ad82fc91216f9c31d2f5dad2afb68022701f8a9  data/free-tests/round4-repeat/puzzles/code-L12-a-24x1.txt
0c52c616cbd2583683aa6557d56b065e4c1a3516a424eb9ebd1624dc010e9de7  data/free-tests/round4-repeat/puzzles/code-L12-b-1x24.txt
92f5b137e5ccdc09e0b055ff86959238b7c94f3e34a87a30a2b493d67e60706a  data/free-tests/round4-repeat/puzzles/code-L12-b-24x1.txt
1c0cc1cb81e6cea0f41e1bb586c495cf4eeb21d479d9d99690e6f6203219c183  data/free-tests/round4-repeat/puzzles/code-L8-a-1x24.txt
e3a492225528c4fa6f8ad1ad3980f9888fd68aa217ee488e3f492fc9d5126c44  data/free-tests/round4-repeat/puzzles/code-L8-a-24x1.txt
fa3bd5ee483c16fd0ab1fad3b8d8602815b699b293fd64c316211c7873437370  data/free-tests/round4-repeat/puzzles/code-L8-b-1x24.txt
0d445614c3ac608165df411d862473a9c4fffae8595620308e8fddb272270a32  data/free-tests/round4-repeat/puzzles/code-L8-b-24x1.txt
60b601ea3c2370fd05436796ecf09d633dcf3415ed672abc0250d9269e64c052  data/free-tests/round4-repeat/puzzles/dig-x-1x24.txt
8ca5fb9fd30d2a31ca5fa7a8807828a7ad4eda3c821956525cca2ae38b3f808e  data/free-tests/round4-repeat/puzzles/dig-x-24x1.txt
d82aea2bb18e87e8c4d77b013dae6486102699a9ff89810c7be385ed74999625  data/free-tests/round4-repeat/puzzles/dig-y-1x24.txt
5410d36e4aa2796d6d31a180d4ddfd13765bc452e373a28e53adf80784e836b8  data/free-tests/round4-repeat/puzzles/dig-y-24x1.txt
a1a849995812e6d97dc787c89c07d2fd758ac38bb21b2cac6d1a7d5992bbec3f  data/free-tests/round4-repeat/puzzles/dig-z-1x24.txt
cfa8674da4ea36783060d359482ec37a819cbcc173400c1daf30546cd44caac7  data/free-tests/round4-repeat/puzzles/dig-z-24x1.txt
765873f75311c2be1fe0d035da84a1d55ce745bd59796321bcae7983b48da96e  data/free-tests/round4-repeat/raw_rows.json
4ef97aa6771b77cb3157b60e90c393abf94787a0ed689ae63190ee87d8b9b7f4  data/free-tests/scripts/extract_replies.py
0fe1d715a70353cfcf5e228d2b48fb93f08825ad4a59ecac258a89c054273c52  data/free-tests/scripts/grade.py
365d57e638bbb34ebced05e1219a043f5af94990e79dabd1fff1f2d3b5c5d83d  data/free-tests/scripts/original/ct_proto.py
6bdf1bb314cb922ffc3ebad25ea26b49ac669a42814abd60109d9384dea38e90  data/free-tests/scripts/original/tune_grade.py
97ce19e8cb9c2f9d7b5399e334266b43fe0f696f63f10d9d7297f2a75ff92bb8  data/free-tests/scripts/regenerate.py
ef4034546e0c51c064ad34f86840352858e0d4d433eb4714fa6aaa0463758871  data/free-tests/scripts/taskgen_proto_0_2/harness/taskgen/__init__.py
dbe3c1af0603b867b5bcda8f2301f24798e770445545adf68842fe8bffec902a  data/free-tests/scripts/taskgen_proto_0_2/harness/taskgen/puzzle.py
e9347c14bb0045339256c3280c9847c841441a516fc29c73f2e8f736c1ec142f  data/free-tests/scripts/taskgen_proto_0_2/harness/taskgen/rng.py
974d892d8ed350e623bf698e53fa46b588804a0307d0b89f2da1c6160019ef15  data/free-tests/scripts/trace_chains.py
5726e2f315178e6eb0697e726a8b367c82445ed1d2ba6fab711867e583bc1dbd  data/ledger-free-read-2/README.md
98a7810df6c5ae74a6a35e5717801c95a982c8c55e9a631df35b3e143121e4e2  data/ledger-free-read-2/keys/l5-a-chain.json
528740cd4f1489ae84d43dbd7eda4ab0eb4e59820ad1829b2c412c500fe56b0b  data/ledger-free-read-2/keys/l5-a-pieces.json
8883c89274afb1de50b33dc6283aefa487fceb6e7e30a5ce71da8cbef232498c  data/ledger-free-read-2/keys/l5-b-chain.json
36565693afd81313bd14e7886fabefd2ef9c5b3bb3be6718aae30d4079902223  data/ledger-free-read-2/keys/l5-b-pieces.json
76e0558c41f0089ffd3fc63bb557348d9f04459ba97ddd618902c071e7f9659c  data/ledger-free-read-2/keys/l5-c-chain.json
9c96443d499015796fb94f47c9ec8e6b91457411ab1ed17d9f162816158a4982  data/ledger-free-read-2/keys/l5-d-chain.json
d6d8176335b9864be5278b0a0d944fb024c02338bab9662d67c03f0c500e61c1  data/ledger-free-read-2/keys/l6-a-chain.json
e041f505035db75f3d88c6d934883740532406344715ef0a27bf82357ec120c3  data/ledger-free-read-2/keys/l6-a-pieces.json
8321e4202ce3a7fb09bf6ef418b4ec1bd165aa506e71846431e09e41325597ab  data/ledger-free-read-2/keys/l6-b-chain.json
992682df9dd2e575a9d03f4c6bd9941164f06b89855748cd3a0a601a18398a25  data/ledger-free-read-2/keys/l6-b-pieces.json
9ecec9048a3e901dbbcd47a0d42cbdfa8e71e54a4ffe230def07f305f3f34dcd  data/ledger-free-read-2/keys/l6-c-chain.json
3f1f53d4c7c0e242a589933c36388ef420b0025593d564e1961aced4f81a2ede  data/ledger-free-read-2/keys/l6-d-chain.json
22d2fc7e1b96e9378d9a651e9085d8d72d95acb85a02dc761ab3c9f318eca6c1  data/ledger-free-read-2/keys/l7-a-chain.json
ed478df1e25fef301536a9c2e88547ce33a3dcdc239a9f1082705bb0df9e469b  data/ledger-free-read-2/keys/l7-a-pieces.json
98d39be51a84b634dcf99a0010a6b9fa26760042c480d28e6a05b39eb1c78264  data/ledger-free-read-2/keys/l7-b-chain.json
86d4075d8a6da978ef01d4970537369e1a70149efb4d9c4a1566ae92d3efcf7f  data/ledger-free-read-2/keys/l7-b-pieces.json
be14bc0d59e8519e2a415d997e38eff724c9fb8d8ed29728f1705f8fb31ed322  data/ledger-free-read-2/keys/l7-c-chain.json
1ce6010afed5f63e19098a42038bb14ac888fe57e1cee56efaf6db066d838437  data/ledger-free-read-2/keys/l7-d-chain.json
f7e6e486595db5b0337a211f3d1f82b1dc42ba33fe5fb7d1df61c35386223fab  data/ledger-free-read-2/puzzles/l5-a-chain.txt
902460b8d3242fe71bb6f3b8aae059d772efddf02b8637f4b9dc1508af30b2a9  data/ledger-free-read-2/puzzles/l5-a-pieces.txt
020446318527e235885535f396200a847c98890777842a343dd7c8a7a518af6e  data/ledger-free-read-2/puzzles/l5-b-chain.txt
c24978c01fedef3e78618877489d635ded19e132f737ab992393fb7fc987415c  data/ledger-free-read-2/puzzles/l5-b-pieces.txt
c06792b733afbf7fdfe521e470bf6fc1841511f96529af1a0902fc95194452f6  data/ledger-free-read-2/puzzles/l5-c-chain.txt
b8180c795342197719ae8f9540ca94b436bfb95e3ceff2f54a0a73a0faf9c0a5  data/ledger-free-read-2/puzzles/l5-d-chain.txt
0567318afbe3f69c6d99bcd422802ad512247c732b1fda842a3d6a6242a810f8  data/ledger-free-read-2/puzzles/l6-a-chain.txt
1a60f440a812bdc701009a3fa917b341b0443e0892647ecae428ef09bb4f6cb5  data/ledger-free-read-2/puzzles/l6-a-pieces.txt
88da3c66950821344460a3e052915424b12f2e6c86bf8974ce394e293ee88713  data/ledger-free-read-2/puzzles/l6-b-chain.txt
1a214a6f5fdefd362a2e595135de2de3f8fd3873bc351952ffbfa6ba499ea49f  data/ledger-free-read-2/puzzles/l6-b-pieces.txt
79617e7111a943d6b63c0525d544ae5a98529d6474e2c8c43e1cc162cf03ff3b  data/ledger-free-read-2/puzzles/l6-c-chain.txt
18ea4afe5b860d47a90e8156b72f0947f59d47866905c7e2e3bf7c3183e0ccef  data/ledger-free-read-2/puzzles/l6-d-chain.txt
f97d423115e3ec6fd491e8aebef9095e7a4fc0745fb3993e7b2128e57dc43401  data/ledger-free-read-2/puzzles/l7-a-chain.txt
7998c2f72c60048011c588a2612648f6d4d588918f26a9162352ec4733a2bdde  data/ledger-free-read-2/puzzles/l7-a-pieces.txt
6d65a98d98b7b0ac6b58fee860f2268a11bf28273d8472b1e623b0c25ae4e09d  data/ledger-free-read-2/puzzles/l7-b-chain.txt
c0cc5f84563a13958d06a5a8a6fedb611bffb52d54c0186c4cce2da80b420eb2  data/ledger-free-read-2/puzzles/l7-b-pieces.txt
fe4ab885497b4623ad23e6d04d241ca9fad1a0f9bf7d44b61d2a80e0d4219fbf  data/ledger-free-read-2/puzzles/l7-c-chain.txt
3ae844cb255652810997d131ba30ddd61276b8a95c1a96493c3e487b7276a191  data/ledger-free-read-2/puzzles/l7-d-chain.txt
91685ba0d73fbc73fbc1cfa9c0a45c3d06fa0a0fc9ccdf57c2260744038bc169  data/ledger-free-read-2/replies/l5-a-chain-haiku-1.txt
5ae56e1374879a3abcd4f693f2805eae1da4302794b1c3dd18bd1e7dec035688  data/ledger-free-read-2/replies/l5-a-pieces-haiku-1.txt
6cb2b88aca55e6eba01ec6ebbd01788383b55bbb6eaa53ffd192f939b35e1cbc  data/ledger-free-read-2/replies/l5-b-chain-haiku-1.txt
91b8797e567f02e1db14637d2f58ab6675f25d50ab1879313bb943fb7b5cfa0d  data/ledger-free-read-2/replies/l5-b-pieces-haiku-1.txt
108cbcbcffff5b7d931e4b55798b0aa058347dc01c0015a0ad1ebf673da96484  data/ledger-free-read-2/replies/l5-c-chain-haiku-1.txt
4fc793cf6e66afdd8b346718ba12a84435a8459e5930bca50c5d4cffea0d8786  data/ledger-free-read-2/replies/l5-d-chain-haiku-1.txt
86e39747e4d33970cb3ed7b256f735a0979a6a30995c947ca5d76b9bcb13edd5  data/ledger-free-read-2/replies/l6-a-chain-haiku-1.txt
98555ae70a8a9726a3539ddc622748fb3e2c513b9b090b5e9f64a134af0a1462  data/ledger-free-read-2/replies/l6-a-pieces-haiku-1.txt
c3d5e4a33ee3207a107f3eb29df1c200ab3adad4a73a3a06259eb37464d4f7ac  data/ledger-free-read-2/replies/l6-b-chain-haiku-1.txt
c243d9d284477993a810371f24db1dcc7a7824ec581c0ec64f7d3028537729ad  data/ledger-free-read-2/replies/l6-b-pieces-haiku-1.txt
a371493ef2f306969f8a1f4b308fc06e7da0b37d1e24c77888575fd7eaa1a32c  data/ledger-free-read-2/replies/l6-c-chain-haiku-1.txt
baea06707805cc0527031e49cb6611ef1f68cd3f4b67cdc13f17d507cd1472f3  data/ledger-free-read-2/replies/l6-d-chain-haiku-1.txt
c36d32c8338d86df719c6e503b1e0acec66bd6ac8fc24170596526608b40f400  data/ledger-free-read-2/replies/l7-a-chain-haiku-1.txt
40ea923609b4a623eabac68629d1a25c6fd4b72e40f00ff5d0baa493bcc755e0  data/ledger-free-read-2/replies/l7-a-pieces-haiku-1.txt
4ffaf64463f21986967d3b25adf6c566da52d5a394f893b9e84b5244bdd14cab  data/ledger-free-read-2/replies/l7-b-chain-haiku-1.txt
38cb588702dcbf9e68c026eb952e12af4de75f9f4c3a460394a07c49bbaa8df3  data/ledger-free-read-2/replies/l7-b-pieces-haiku-1.txt
ee857cbfd26eb8724a354889b4f2d61f40dbb56adc34d27914cc1bc342992436  data/ledger-free-read-2/replies/l7-c-chain-haiku-1.txt
e0e85bd604075c21a1b849d9abf32d6d35b4abe1c387c7a54bbe9e2484b3104b  data/ledger-free-read-2/replies/l7-d-chain-haiku-1.txt
74fdf4752a547210876f1188ab719a34eb7ae6581ac91757b2cb3c5d357974f2  data/ledger-free-read-2/results/rows.json
8743c737a02a11e8b5ffd02c3b85858003644d75a71d9f7de9af19dc3125fd63  data/ledger-free-read-2/scripts/extract_and_grade.py
47b7b001097ba33de4756b991f244962d9bc42cfe9e4b1fda1df093f14f399a5  data/ledger-free-read-2/scripts/make_puzzles.py
72d88bdd6eb29347abf506b2ee259ca4acae38fe6db2c2f479584064e6d2b304  data/ledger-free-read-3/README.md
93d5332927f6b8141674a1c6b6638f402e617c244919fb3aa552afdf23b045f4  data/ledger-free-read-3/keys/l8-a-chain.json
8076e9c2ea6d782627335f8e11b2f7496fcb431bbe5d232aab8176a1109d0720  data/ledger-free-read-3/keys/l8-a-pieces.json
29c91f7e38447aafdcdeee74c5226140550dc6f624a6a7ae629d2a2db160b8e3  data/ledger-free-read-3/keys/l8-b-chain.json
41b0c75f033a63c55056e76749115aa3ad98efdf972501b9fe9e66187c980eed  data/ledger-free-read-3/keys/l8-b-pieces.json
1769ce0bfd711bf0887ce847ce059922b025b9607a34af8cbf7eacce940e0045  data/ledger-free-read-3/keys/l8-c-chain.json
c4367c3c4a2236a2e933d9533620e3ca399ce022f5ed7f3c0785393ba8d14c1f  data/ledger-free-read-3/keys/l8-d-chain.json
e2ca1aae8c2cfb37311bc45914d83dcc86c5c8951bd86467adaac2cee82832d4  data/ledger-free-read-3/keys/l9-a-chain.json
e37f5a474bed567ae1873c90cbbd2aee58f1943bb7d9fdc17139be01ab1aa4a9  data/ledger-free-read-3/keys/l9-a-pieces.json
de8efc6d47cf0df3f4a622cb9f2d6401451cc4e4efb5b74c1aadcce714e1f03c  data/ledger-free-read-3/keys/l9-b-chain.json
3c19339bce743ad043b5824c0d8e53388f5c6753b527ee15dc39b11bb4afee67  data/ledger-free-read-3/keys/l9-b-pieces.json
e7372d33435fd409370dcb2edbd3b9fc5c4dac9129668811941017da7ae05c4c  data/ledger-free-read-3/keys/l9-c-chain.json
01210d589047b42c404bd20e139f33b2c30ba2819496e744baa4fb198d98067c  data/ledger-free-read-3/keys/l9-d-chain.json
fefc9acc9cd45379cf59f0e7ac31390513a91c4ee6a31b27fc6128243a1f2203  data/ledger-free-read-3/puzzles/l8-a-chain.txt
050dfa57137093f313c898df0c6b962be0d955fd8fffc4314bc2bd4224f67806  data/ledger-free-read-3/puzzles/l8-a-pieces.txt
2a4e2030f7026d13c3870d76345d10b17e8171c68d6bcc76043d07a5debc90e4  data/ledger-free-read-3/puzzles/l8-b-chain.txt
492026688b312079835b21cec51fb99efc64a297acd29c7dca8358a11046667f  data/ledger-free-read-3/puzzles/l8-b-pieces.txt
b67f4ac6616b65fbecbe81a7994af51f33f31e893fcebde25d784a192b9a891f  data/ledger-free-read-3/puzzles/l8-c-chain.txt
21660c2742fe95fca17a4b1ee7ad5313637ce2dab26aae7bf29548344512d3b4  data/ledger-free-read-3/puzzles/l8-d-chain.txt
d2fc667950169c455ea185d4cda8e16f6848f3fa64f50d37e826d7ca37fb19cc  data/ledger-free-read-3/puzzles/l9-a-chain.txt
4798acd1399fe548e453f326a58a955f19447421438630a705cb2e6c7acad1e0  data/ledger-free-read-3/puzzles/l9-a-pieces.txt
6cbb45436027f73a3ad3c91bedae5290a070543bbde3e575207d452511ad9179  data/ledger-free-read-3/puzzles/l9-b-chain.txt
80901dce8d164b96a2b1c622110be272ec2f40929fa21cab32592345f8931a7b  data/ledger-free-read-3/puzzles/l9-b-pieces.txt
ea7119a0869e2c8e429087eae5eb8847aadd501aab99540b3b4077ce1e96699c  data/ledger-free-read-3/puzzles/l9-c-chain.txt
8e27bc298c10a7876892ab1e87064fc007991a854e2f738f003a93de46cb9cca  data/ledger-free-read-3/puzzles/l9-d-chain.txt
ee46df75a344fbfa9f1e91c813ce520df40e4e1f90a35b852fcdc06d8275d1bd  data/ledger-free-read-3/replies/l8-a-chain-haiku-1.txt
403e2074cbf87f814a35f5bf3bee11b0a7244b77c4d50072b6799cb30c937d47  data/ledger-free-read-3/replies/l8-a-pieces-haiku-1.txt
aaef05596f9eb24bd1bdf556fb7b31b890f1ada908d9e6655de319931b5025ea  data/ledger-free-read-3/replies/l8-b-chain-haiku-1.txt
b96a16057689f9ba08d41e8a217a71b3e487d00dc2c9c60f5c0afdef15671d41  data/ledger-free-read-3/replies/l8-b-pieces-haiku-1.txt
29622e6f6d26c597b2fad3a1e0c543c98749547695eb1d120ad5650d8228eabf  data/ledger-free-read-3/replies/l8-c-chain-haiku-1.txt
b2529bc0851605c710887946a5c86ac1875e86d614bc14dcf7cb5e0b5c857cc0  data/ledger-free-read-3/replies/l8-d-chain-haiku-1.txt
07dfee74c759e44c8f53cfa61e5dddbb422c7e74c156578173e52d2a00c06d92  data/ledger-free-read-3/replies/l9-a-chain-haiku-1.txt
f4cca1277df8f4d14e9ba0e62fd70960f0882e3b922d3595c9006906cd1c6426  data/ledger-free-read-3/replies/l9-a-pieces-haiku-1.txt
5b44927eb6818aae8c607878ff0ceb76b6c81cf874c8b07cf6e92fc6785e9a30  data/ledger-free-read-3/replies/l9-b-chain-haiku-1.txt
51fa02ac3eb1e404e05fd94d56cdd8defb16f7b406ad361b92f7964d03b8b6f7  data/ledger-free-read-3/replies/l9-b-pieces-haiku-1.txt
4653e4666058cb60f1ea930256b3881d3e5c195cc9d4be8d28cfa63cbc0a3546  data/ledger-free-read-3/replies/l9-c-chain-haiku-1.txt
adbc5841238bb2e7ac9f72db82115561692b59e091c219cc9ff1e88639a5ec52  data/ledger-free-read-3/replies/l9-d-chain-haiku-1.txt
aacb108edd8e550622082b801580e92f7f1f98382950195792b186a8811841d3  data/ledger-free-read-3/results/rows.json
278c324fc1c71f58c8b68e0ebf16a243a348564dabfd22a4407a48778cc2a77d  data/ledger-free-read-3/scripts/extract_and_grade.py
40801562624263b54fb81485cdfb3dbfaf6974ec8616cdd17df9ec68f07b955f  data/ledger-free-read-3/scripts/make_puzzles.py
5199ea15f9db485d9158645245fdff9398b22a05fe15142534eeb7af20666024  data/ledger-free-read-4/README.md
d34d556e05e0c294522bc27786565eab9efcbebd5b9f57593859a5f59226147a  data/ledger-free-read-4/keys/l10-a-chain.json
716082ef59134bde6155d067f62c0dd369cff4f01cd12b39cd4796bd259ee0f4  data/ledger-free-read-4/keys/l10-a-pieces.json
ba60e5e11f7f2499051b808bde3a20ec9b31b9b721032d1f5c359eccf0737b53  data/ledger-free-read-4/keys/l10-b-chain.json
5b1bebabfe5692da5adf9f61288e6ffbde7516a034aeafd65f58caa7aa062241  data/ledger-free-read-4/keys/l10-b-pieces.json
d0bd8dc220c29b8e117269b9fbd00d609bb985e8dbc8b3f07ee93f8183711054  data/ledger-free-read-4/keys/l10-c-chain.json
99f38f159bb8b492096d9078b8fcb24d0455eeac67d3372bb56289bfff96e99f  data/ledger-free-read-4/keys/l10-d-chain.json
bd4649ad132fd2c47881fe62b0a9c5965e786837148c6f049331cf95e2f0a8a7  data/ledger-free-read-4/keys/l11-a-chain.json
a70234c41ba6d7e249c541fbe123c4a93c0fb3aaff9ed657cdf3b282c0c4942d  data/ledger-free-read-4/keys/l11-a-pieces.json
9ebcb0aba6c461044ac0d53fbca0907b0e2245e34843d3f5bb30788ed150674d  data/ledger-free-read-4/keys/l11-b-chain.json
eea39e3427bdf86da629d484493cca3d14a3b0d328505bf170db003222ce22aa  data/ledger-free-read-4/keys/l11-b-pieces.json
1ea14698ee7391d6d754ae053ca2472bd16e6333f7801f87252be753565afc9a  data/ledger-free-read-4/keys/l11-c-chain.json
1e5ba2f63c57c575c3ebf2845fb05a093f893b763d05f59993e33f5aac5d1b2d  data/ledger-free-read-4/keys/l11-d-chain.json
0871e719175a4d310b58c0da29dd56b7b23c3e8e4360983dd3d8d49b4f20dca3  data/ledger-free-read-4/puzzles/l10-a-chain.txt
e2a2865eb97f0c4443c6f4f774e67decfa41808f1d1aa4cf86ffc78b0392e4a9  data/ledger-free-read-4/puzzles/l10-a-pieces.txt
bba7136f2c7696dfd0e37b54a673a9190a0f01c2390ceaf12d9358c546096761  data/ledger-free-read-4/puzzles/l10-b-chain.txt
c20f871d10bcc6aab0faa6ef3b137ba3fa69e9ecadefa476acb26dafde9e0f09  data/ledger-free-read-4/puzzles/l10-b-pieces.txt
d867922207e32e1c618cec72ae704afd06a7d97d76dce5442262126e068410db  data/ledger-free-read-4/puzzles/l10-c-chain.txt
cff821644c58a65115ef4e4b86223b01a1cfbd58e03ada4bea3b6c09b47151d1  data/ledger-free-read-4/puzzles/l10-d-chain.txt
71afbf681a448d141a6887a4fe342cea03594477277448b5c3197bfbd40145d8  data/ledger-free-read-4/puzzles/l11-a-chain.txt
6b1c258c27a80c6f0915229605ae713a860f0ac3045a91362597e8ed65538a45  data/ledger-free-read-4/puzzles/l11-a-pieces.txt
74764c6f8cf9bb1d6906acc303f83c960d557f457f10dbd0bbd3bdbd61ece807  data/ledger-free-read-4/puzzles/l11-b-chain.txt
7aceb757b55ee0853244252627935c12247c5fcf93851d1172f3b2b62b7c09f8  data/ledger-free-read-4/puzzles/l11-b-pieces.txt
cad9f255018d6030e060cd6f6bc5dd3b3a675d054007e2d4cb92d23710479e1f  data/ledger-free-read-4/puzzles/l11-c-chain.txt
d7e5f55ca038a96e5cde1d8182b2b1e809a76aa43aa019b4716ff4eff05f9dcb  data/ledger-free-read-4/puzzles/l11-d-chain.txt
d1de8e49fbb062be81dbdd4d29b56ed063536095f1024bb5fdce815a6ebd8ba4  data/ledger-free-read-4/replies/l10-a-chain-haiku-1.txt
6e36a11e6efb8bc69db890d1f23d15bc89aff46b2c49243d5fcc6e7caa524059  data/ledger-free-read-4/replies/l10-a-pieces-haiku-1.txt
873a04873d725d1e5482015e01d5e81caeb1772d8f94ee60ab131455fb3b7fe6  data/ledger-free-read-4/replies/l10-b-chain-haiku-1.txt
d72e5e7238be25de149778307e893568c0ffb2a8a0d20c149935e125d0928bc0  data/ledger-free-read-4/replies/l10-b-pieces-haiku-1.txt
ec35f67f019f8e90954f2b38f2fb2b3398c7a73f4d080c2f459e082b15c7c314  data/ledger-free-read-4/replies/l10-c-chain-haiku-1.txt
d2129997fc3c8b318d14a819e6a7c148e5219cd81edb5f7bb0f1bdc8f2122a8e  data/ledger-free-read-4/replies/l10-d-chain-haiku-1.txt
f6d5103a08a1646351456fd94b7b51550a2e9c3b254c9181aff4fca88a85c4f6  data/ledger-free-read-4/replies/l11-a-chain-haiku-1.txt
846c9a13fe7c21bb3e96fc2e532cdfb6145b6cd63a46b7ad747afe818dc7ce4e  data/ledger-free-read-4/replies/l11-a-pieces-haiku-1.txt
80605ba3e20eac3b3ca6679485300570caa999f85328720509086c56e9f523ed  data/ledger-free-read-4/replies/l11-b-chain-haiku-1.txt
640b26c5cd2c3d9adf82169fe272c24ca20eb1010d41fc6638d5f48151bbe00f  data/ledger-free-read-4/replies/l11-b-pieces-haiku-1.txt
eee8931713298e3997072ba37da41ba91f0d5a273fb9361f561b6a3f3266cc06  data/ledger-free-read-4/replies/l11-c-chain-haiku-1.txt
eb9f96adb0228f39ad827928fc9e0bbe67e224a9af78919a349a7090467324b1  data/ledger-free-read-4/replies/l11-d-chain-haiku-1.txt
dc7dd00645adf6f37ab728172872bd999d24d2cda0f0cc1dccbb4489291cbba3  data/ledger-free-read-4/results/rows.json
f97d80c6382355beb55ec138e3e0e82bfd7dc3f3a545b0107177997db6f9c0c7  data/ledger-free-read-4/scripts/extract_and_grade.py
7ceeb827baf901989b56e1936370bc22dd66c11870b1650a969273405fa29c84  data/ledger-free-read-4/scripts/make_puzzles.py
3598ba33b5c994f22ca45871e87e6c0089b988a8278f09ae928c557955154190  data/ledger-free-read-5/README.md
a14254331893e16938ee1b49f77b9bb833c014a0f97cd16e3e95990deae88617  data/ledger-free-read-5/keys/l14-a-chain.json
5e03c6a0ea964c121f95ca5b046d71c9aef3fe33be888786d748f2f58f462bec  data/ledger-free-read-5/keys/l14-a-pieces.json
30263309602b4dbd286bcf66ca9611cd2f7c85ac4bd892f8f6131f8b68afaf3c  data/ledger-free-read-5/keys/l14-b-chain.json
3329bbef7ac8e3c99e7ffadce98a814bfaa2e5d6b00b27f94368114f48eed7f0  data/ledger-free-read-5/keys/l14-b-pieces.json
75744e3c31f44e2c486f66dd16cac274c0ea18dbee7f7d42d0ae8f2d6aa66cea  data/ledger-free-read-5/keys/l14-c-chain.json
e4452060b15ade5cb702e09c39005147412adb94ad3b86c2947250dc4ac1df55  data/ledger-free-read-5/keys/l14-d-chain.json
98c4c222e69da41a3e31b5c89fcb2cce40bdfb454fc4ed9e76c142aa4145cdc5  data/ledger-free-read-5/keys/l15-a-chain.json
abc4b5d02727e25ed463770e4691964500d52fabfc3cf74475a37d496cd578a9  data/ledger-free-read-5/keys/l15-a-pieces.json
f27429b2850c2967a16c672a491a5a6ac2d817f3d4941267fa5a20ea91e89002  data/ledger-free-read-5/keys/l15-b-chain.json
3e7461bc423df7484c92f0d7c216fd5b26589fa6900565f358e079ef11af45b2  data/ledger-free-read-5/keys/l15-b-pieces.json
6e23323e706fa33402773a22162f67b3f7fc18034b71b5416bdb7b95df6917ee  data/ledger-free-read-5/keys/l15-c-chain.json
1f23b1e80b3de8cab878f997b7d6109a65e9a76504c852c3671ac78cafbe672c  data/ledger-free-read-5/keys/l15-d-chain.json
c60b881d65b4c3bb3d3e393675f3749d431a40412f0d0357bb993a3bedfd027f  data/ledger-free-read-5/puzzles/l14-a-chain.txt
7ca74cc0877c067c13724dd0bd3881fccc1f444225dea5bdd8beae24f6bbde6f  data/ledger-free-read-5/puzzles/l14-a-pieces.txt
44ab472dcb8254c90abd8bc02a8c917e1308cc5a985d2993bc8e95e7e92fe364  data/ledger-free-read-5/puzzles/l14-b-chain.txt
d279c1b7f2051769e7993d8b76b586bdf4477df44b2567f930c8b9c1f8bdac8c  data/ledger-free-read-5/puzzles/l14-b-pieces.txt
d36c48c67e669ca3a68888f4303df210de550ca41f49a652c4b383fc917ac397  data/ledger-free-read-5/puzzles/l14-c-chain.txt
4463665e034c0bea054bf25cbaa33cca8d080f1e2f17772a400191593a261d9a  data/ledger-free-read-5/puzzles/l14-d-chain.txt
a95c99237a1859304243d01393a76f3176a942f4e751f0afcbd63e03a54997c2  data/ledger-free-read-5/puzzles/l15-a-chain.txt
6439888faa2d5298dc56de0125df3a912941d8da539f342eb0e52f052d05f524  data/ledger-free-read-5/puzzles/l15-a-pieces.txt
8c4d225df29fdcf42cfd354ef2360ce7da07a05e2476982521313338aca133a6  data/ledger-free-read-5/puzzles/l15-b-chain.txt
80ca13f0793c47c34945d222e84694d2357f5e63ad797ff41c2c118b844ef980  data/ledger-free-read-5/puzzles/l15-b-pieces.txt
9d8e1e43a68b8b9f0bbd78f45c9b7c1dc110120ee60712410cefdedf0105579d  data/ledger-free-read-5/puzzles/l15-c-chain.txt
c81882704ac3d22999c0c83c264d7c85473c3f2812bcf83a13dc84631c33b82c  data/ledger-free-read-5/puzzles/l15-d-chain.txt
be16642ffe55a529f691463a73790c560a1fa5310adeb925a99b6cc33d24144a  data/ledger-free-read-5/replies/l14-a-chain-haiku-1.txt
87667b828c9b32e2b0b0323b8d549ff5c70d766cfcee65a17df84bd55be9eed0  data/ledger-free-read-5/replies/l14-a-pieces-haiku-1.txt
cf27447089e93b901f2f6cefccdcf807fc54077a46e4a442c97c93a551d52a14  data/ledger-free-read-5/replies/l14-b-chain-haiku-1.txt
d20a1117be8046a1e02b753f9a60724a0e7055e86dbc5f49ccadbff1baf662bd  data/ledger-free-read-5/replies/l14-b-pieces-haiku-1.txt
cc94f3ec608b0b8696456daafd867b3a122c9004c279700b974745c3eaf17590  data/ledger-free-read-5/replies/l14-c-chain-haiku-1.txt
ad5b2a56b3eefaa75a60f7b6d1a4a24b4d1804fecb57a80184a185efe2bdc228  data/ledger-free-read-5/replies/l14-d-chain-haiku-1.txt
a9abd92e86e3b8794d1ba7e22f84a94a3ae41d532e6d0d0dc498ecebbd2ee98b  data/ledger-free-read-5/replies/l15-a-chain-haiku-1.txt
7997a25569a85438be5a21e1eb945bb9a714ec6f847c0b2b5e629789d3337f21  data/ledger-free-read-5/replies/l15-a-pieces-haiku-1.txt
57f712ea850dc730f5244bf33d524fbd8a06b235e5f59e3fe890292d2c29e365  data/ledger-free-read-5/replies/l15-b-chain-haiku-1.txt
8fc333c4081a68dde29b8d8e0dfad1b6985a28859bac8f0bee6ed7e695f4b1d7  data/ledger-free-read-5/replies/l15-b-pieces-haiku-1.txt
f680e2bb904eede11bd9883603d670a4f12454ab0fe7427a4d09e1c9b000703f  data/ledger-free-read-5/replies/l15-c-chain-haiku-1.txt
5b3606c0f369f5548aa79f36a3eaf69801258de7f24bb0b0b307f4ff8bf1c97a  data/ledger-free-read-5/replies/l15-d-chain-haiku-1.txt
41355566f37de7ed2b93a00dca423af699fef7c1b791a2a3695ce26c7f9503b8  data/ledger-free-read-5/results/rows.json
a547057de0b5c23bd7c76259b8c90791908eb85ebbb7171f2d828b546da62d85  data/ledger-free-read-5/scripts/extract_and_grade.py
56dfd610ec9dcd030de41dc524138596d0272e12a4b946d58342090abeeaba0e  data/ledger-free-read-5/scripts/make_puzzles.py
ce5a918002f08eeaf599bf6f9414c96003e4fdf6a17cc48ae71068fc9042325e  data/ledger-free-read-6/README.md
9ac109ff19db6a2c24ed837acde5d8b1f7bee1058d7e9dfc782363612e81f4a9  data/ledger-free-read-6/keys/l16-a-chain.json
a3de8a97c23df5a8894151d3e17ac6dcd12240219e63f3f0b55b0863a65c4dc4  data/ledger-free-read-6/keys/l16-a-pieces.json
4cea1d9561d15cabfbd7f57f5d999a71903803992c4b8803b562f428fa096711  data/ledger-free-read-6/keys/l16-b-chain.json
b36bb4246621cfb3e8e78ad91dd71aabffac4d029c6a5d716983c875522572fb  data/ledger-free-read-6/keys/l16-b-pieces.json
5461499f4acce6eebad629844367b2ca8467dd30885c5cb42b29d07c3053dee3  data/ledger-free-read-6/keys/l16-c-chain.json
49592adad0f8504a9e421837afc88dd5307d0614a6d18381bcd0fef32f949216  data/ledger-free-read-6/keys/l16-c-pieces.json
1e9641f7ca9f11409d1b6c8fce99035a0e655383984458f20ef17025ac450393  data/ledger-free-read-6/keys/l16-d-chain.json
1445a64ac28223cb778832b9e808e76c6eb5b4eb9ce2e58ca8a81d2de5363f72  data/ledger-free-read-6/keys/l16-d-pieces.json
9fed67e78781df01ee0b520e66c4cca5e1c93574e3d6979211110d13903b0455  data/ledger-free-read-6/keys/l16-e-chain.json
5f2c9f0937b064a13635b8373cb81212b2721761334ee7b9924ed11426fb1fa5  data/ledger-free-read-6/keys/l16-e-pieces.json
393b6cf9c29583de1b492d9d0cb2bf43999d4c3ff938af2e8d6145d65ddcd9b6  data/ledger-free-read-6/keys/l16-f-chain.json
b2e8b2b187e54161788aa159ba8a720bbd1246b06390e86a0be085fd41dcef86  data/ledger-free-read-6/keys/l16-f-pieces.json
10311c5488ad252dee2a9f126eacb6abb33d5f15c25b1a74429782ddb6f75b3c  data/ledger-free-read-6/puzzles/l16-a-chain.txt
a1d360abda716f4f3a2d53b5150db3bab8432d8b0e4ab91cc674f9a06f9d72bc  data/ledger-free-read-6/puzzles/l16-a-pieces.txt
0261ee4dc0ae9910e269817710183c1c37a995a6e81bc130de13f38bc4ef4c4c  data/ledger-free-read-6/puzzles/l16-b-chain.txt
2b87048a7a8abfe542c06aaf90edebb7d6a3fa16fc47dec63977058711ef9475  data/ledger-free-read-6/puzzles/l16-b-pieces.txt
10549088e82dd31fbcc7c48e2172d240fb14faf9d57112b84039c2b8fb1f7c21  data/ledger-free-read-6/puzzles/l16-c-chain.txt
69aaa577b8879919701d749ca6776af5c36dc210600d8713fe0c904097671b9a  data/ledger-free-read-6/puzzles/l16-c-pieces.txt
c8463e1cc869e89946c8ce8b0ab580c1b009ebc618fc272fe21f5c4324c9ff4c  data/ledger-free-read-6/puzzles/l16-d-chain.txt
7d95c9053fa94b2bfb14b88393d428ef0f77d6d2d98f5d49f422ccce13214199  data/ledger-free-read-6/puzzles/l16-d-pieces.txt
1dbea8ece911b857a621f531bfe3a4bb49755c69ee97088e55b59628164cd1cf  data/ledger-free-read-6/puzzles/l16-e-chain.txt
ad1d84c688ea7cf5d1650cd544f411517fd6474fe5e97714289ff7fea99ca5a9  data/ledger-free-read-6/puzzles/l16-e-pieces.txt
f678bad6c07de107d84ab4141eb01df22616dbc1e2b1a965c6da846cd91750df  data/ledger-free-read-6/puzzles/l16-f-chain.txt
377ac5e8101012277e2c98a4bc4757b971ee3a6cec16b5df986326b69e046d85  data/ledger-free-read-6/puzzles/l16-f-pieces.txt
48dfaee1ca6f2e79db2db906d2f6a5de8d2a536e94f9a9fb25ad3121eb84d75b  data/ledger-free-read-6/replies/l16-a-chain-haiku-1.txt
963eafeb7c3e27b1ff348fce9d547a1a4c2500d2089b1658be2ca040ed0ee4d7  data/ledger-free-read-6/replies/l16-a-pieces-haiku-1.txt
69bf94f2d98eef6bdc1c58b7339c8d35db3aa8b7bef8083f1d3fe4f4ae956b49  data/ledger-free-read-6/replies/l16-b-chain-haiku-1.txt
41f650800ca506cfe9e0bd598ac8486c26ef7aeb2d03edd50a1571b128c072e6  data/ledger-free-read-6/replies/l16-b-pieces-haiku-1.txt
562cac0cd743fad4fcb7ced06d50178ca4e19c81e98f1101e1bc836b2856336a  data/ledger-free-read-6/replies/l16-c-chain-haiku-1.txt
7092b369efb098e11e1cae2434f68dbd7d7defebd4213135937d7cd3d9be5ef7  data/ledger-free-read-6/replies/l16-c-pieces-haiku-1.txt
14a5a6960a7553dd89143401124351ce796a2600510159a6531422cb16092f09  data/ledger-free-read-6/replies/l16-d-chain-haiku-1.txt
3615646ede645c4f37eaa16137d87f1c2d4a4daec555968a8dfb103bae0e180b  data/ledger-free-read-6/replies/l16-d-pieces-haiku-1.txt
a5506568384a543a8b7ac35b79906cfcfe2e029d0964f04791a74c3c97104fdd  data/ledger-free-read-6/replies/l16-e-chain-haiku-1.txt
1ed9f2c3be18e227b28c378afc4d81688085f616c28357cbc409071095d88a05  data/ledger-free-read-6/replies/l16-e-pieces-haiku-1.txt
5274d014c2111c6351ce713818daf56142bad22acb0b99afa4784d2f49315fca  data/ledger-free-read-6/replies/l16-f-chain-haiku-1.txt
2a87df4ed99a9d9203888c312a895157639638dadf59dc6e41d6deeb6b8a37aa  data/ledger-free-read-6/replies/l16-f-pieces-haiku-1.txt
9d0d434b9c51987d04a9c39bee67b0f0b270b81b74d987c224b4e06fc88dd9f6  data/ledger-free-read-6/results/rows.json
db715643905ff09f84cd25ff15ff6cd3a478a721d265d42a45107704d2b6292f  data/ledger-free-read-6/scripts/extract_and_grade.py
65744f307b3e8cbad308f20ee371cd61d53f28768ce9476908a6a77e1a2a8caf  data/ledger-free-read-6/scripts/make_puzzles.py
9d57499c8de2836bbd4bde1cb59e203722e4b805d551f4e9406fe0fe3d9e8f1d  data/ledger-free-read/README.md
af19c4651e1626e6609996897f67a05df8b2234be844797c368cf8d400ed463d  data/ledger-free-read/keys/l1-a-chain.json
1a1553272f76e57080384147d3f2ab62d0e21cd937da57375f3c426c5777f947  data/ledger-free-read/keys/l1-a-pieces.json
e4ff2bd7a386c5742ffc1f69be43f7ef031de23b92e51d4e504c39c8c0615b02  data/ledger-free-read/keys/l1-b-chain.json
1bf95d043ca3fee06ab7319445153dbbd4f44c0e1962ccc3311d78b377409588  data/ledger-free-read/keys/l1-b-pieces.json
bc802fd9407ac6216e511c6dd60701639d3ae0a8dc42428584e8e9a63dd7de81  data/ledger-free-read/keys/l2-a-chain.json
86c2ae231f0fe449d888faeccc9045e6c0bc1eddce987031dbcb9f55157dacfd  data/ledger-free-read/keys/l2-a-pieces.json
e728aafbd10d786a8d461c341e76d2f66b37bdd1f79cade19ab9480f859d9781  data/ledger-free-read/keys/l2-b-chain.json
6fdeea8899a48d3a30de7b2d53268b9c3dd2df62d3b5bc1f5d43eb0f5507f73d  data/ledger-free-read/keys/l2-b-pieces.json
95033329c832b215eaf8bcae6df2c9225da988d747c8ce96bbfe22755eb81624  data/ledger-free-read/keys/l3-a-chain.json
09e40674d6990709a218f06d852cf8e76dfad65480a47b88f0b8a0d5880a0bd2  data/ledger-free-read/keys/l3-a-pieces.json
cc08cf20d6879fe3f2e51916a0032b3f6d9f85f574409a4efce33720b23b9288  data/ledger-free-read/keys/l3-b-chain.json
330c4e80b6e485a9f20fbc4c099b94afaccf8e3fdbb24c9febbaf515daa5ca70  data/ledger-free-read/keys/l3-b-pieces.json
c12661f5b89f870bf17efb286ad18a45ec0f0be4d5975b0fc5ecc469f695fe29  data/ledger-free-read/keys/l4-a-chain.json
873fe2bb094b3b2f52cb12614f0a80c6ccf2be4fa1f98824d7cfb9a1fcbc5674  data/ledger-free-read/keys/l4-a-pieces.json
61a5e245a2117f4d8c21ff1cb787c567018d5985c41fe195df828217fd6e9f28  data/ledger-free-read/keys/l4-b-chain.json
6533b6a49182f5f4ba6826edbbfffbea7ebaa4a786da5ef0fcf99be1e54edad6  data/ledger-free-read/keys/l4-b-pieces.json
b9febaad0b23002669b04a1f689a454e31ab18c50dcf1f2524c0e28f01273b6c  data/ledger-free-read/puzzles/l1-a-chain.txt
240e71ee933c48d7764724a55bcff4914ee64281ebd60de4d4925c4614eb5edd  data/ledger-free-read/puzzles/l1-a-pieces.txt
c2517a85dd3bf6d37dd01ba30692ee1258e653d64c4348ad89c5630df60020d5  data/ledger-free-read/puzzles/l1-b-chain.txt
cbcbdc9f7ec71d653e91ea3597eb68771c32e45fe6db4216fa4924311b2b4880  data/ledger-free-read/puzzles/l1-b-pieces.txt
1ff3ba7752cfc731f520e6b6215de71ed6a2abf33be3f4626608bb26df4679dc  data/ledger-free-read/puzzles/l2-a-chain.txt
28db91aa524a6bfae41717543747b3b0d241f0e9e7beb7666ccf4736a6819884  data/ledger-free-read/puzzles/l2-a-pieces.txt
ada0e65497546d5800811ef0ea1687debc76b3459518553574065529b705a280  data/ledger-free-read/puzzles/l2-b-chain.txt
f1f96276f813ebd645b08cb5539b3928e920ec1f7580b74ea075b9dfc650f5d1  data/ledger-free-read/puzzles/l2-b-pieces.txt
bf83a0aa5046c70e292eba12b8d516a86463e6da7f93520350241afc179ba255  data/ledger-free-read/puzzles/l3-a-chain.txt
ce42132350d7f8bd6b6c461a879cbcad3cece426b4eef0b43a75f5090886453f  data/ledger-free-read/puzzles/l3-a-pieces.txt
f152c34a1e2723e837ff1499dbabd3059ca93bdc81e44f86c5af8f7ae6a4dd1f  data/ledger-free-read/puzzles/l3-b-chain.txt
91485759a1f0dd54a80e02dbc12687649ac49ccadc58034e7ae5b564965aa194  data/ledger-free-read/puzzles/l3-b-pieces.txt
fa89f5044bdce00008b5e8145a78d7e1dce5d4be36a4c05917717ee4755b71ef  data/ledger-free-read/puzzles/l4-a-chain.txt
a9a8fa01bad7d0d3308c3c5b26978d08cf291a1707645012718834fc3d5048dc  data/ledger-free-read/puzzles/l4-a-pieces.txt
76cc3202225b656d3f99844d60501bc800d298414fe05228068520ffd0be1372  data/ledger-free-read/puzzles/l4-b-chain.txt
22d478bf8d5616eff9dcd80dd0fb9f4b0d972352908d75d737626dfb85c58257  data/ledger-free-read/puzzles/l4-b-pieces.txt
989cfe1e081256117775d00ded8c44f6900556f5011126c0dba1e003d7b97b36  data/ledger-free-read/replies/l1-a-chain-haiku-1.txt
989cfe1e081256117775d00ded8c44f6900556f5011126c0dba1e003d7b97b36  data/ledger-free-read/replies/l1-a-chain-haiku-2.txt
8a69f0b0fa15ed8f5930e7aa0b890f3570e269307e6bb79d2243e0258da4bb68  data/ledger-free-read/replies/l1-a-pieces-haiku-1.txt
ea07efdb31d85f9d8b830ae1d98223e42904caed53665e996d7f7ddc89fa24d5  data/ledger-free-read/replies/l1-b-chain-haiku-1.txt
ea07efdb31d85f9d8b830ae1d98223e42904caed53665e996d7f7ddc89fa24d5  data/ledger-free-read/replies/l1-b-chain-haiku-2.txt
dda7d7f0aef854a83dfb275cb27018d15e8fbfe51f585a2e8b7be15c5a0fe8c2  data/ledger-free-read/replies/l1-b-pieces-haiku-1.txt
481827e5adab9da73efdecb222d279c0ef2061aca0135ee8c545d2b32a803b2f  data/ledger-free-read/replies/l2-a-chain-haiku-1.txt
481827e5adab9da73efdecb222d279c0ef2061aca0135ee8c545d2b32a803b2f  data/ledger-free-read/replies/l2-a-chain-haiku-2.txt
26e1f64a45e758387e27db0c0a4fe5664f4d4cfb339f14fcaaae16ac98394349  data/ledger-free-read/replies/l2-a-pieces-haiku-1.txt
34142e08cd72d71eba5859acb8b54cd5d78a9db28a22e30f39182fd1cba60257  data/ledger-free-read/replies/l2-b-chain-haiku-1.txt
34142e08cd72d71eba5859acb8b54cd5d78a9db28a22e30f39182fd1cba60257  data/ledger-free-read/replies/l2-b-chain-haiku-2.txt
f86d06e76c0481dba949cf761b2d3c7e5e284a846940852d22418aeda8435757  data/ledger-free-read/replies/l2-b-pieces-haiku-1.txt
2a118c25e29745308699879565c593a9bddf2199233fd4781d1997c32bf7d4fb  data/ledger-free-read/replies/l3-a-chain-haiku-1.txt
2a118c25e29745308699879565c593a9bddf2199233fd4781d1997c32bf7d4fb  data/ledger-free-read/replies/l3-a-chain-haiku-2.txt
0015d62086e46976ab759f1b4788c21ed3b4cc7a44dc923195504ac1db71209b  data/ledger-free-read/replies/l3-a-pieces-haiku-1.txt
4475c71e0ecd8971ad3e7e982c2b06a6b9d8f5a3dd3c63e854d1ae92e5848b07  data/ledger-free-read/replies/l3-b-chain-haiku-1.txt
4475c71e0ecd8971ad3e7e982c2b06a6b9d8f5a3dd3c63e854d1ae92e5848b07  data/ledger-free-read/replies/l3-b-chain-haiku-2.txt
423454d231a72fe227d9bdd17ff02eb3294f6a8a047eb2efadebdaf6a0ea89f0  data/ledger-free-read/replies/l3-b-pieces-haiku-1.txt
a89f4a000620ba6d7cdef43597e4dea5b1d34a5c9dc5c93f1a86f4f127a944bd  data/ledger-free-read/replies/l4-a-chain-haiku-1.txt
a89f4a000620ba6d7cdef43597e4dea5b1d34a5c9dc5c93f1a86f4f127a944bd  data/ledger-free-read/replies/l4-a-chain-haiku-2.txt
e40a71ffa06c84889a46f807c06abb22fb88f7076c32d66387723ddeae853927  data/ledger-free-read/replies/l4-a-pieces-haiku-1.txt
adc66a3345f1c1bd20b806264862cc5a4ef2c1199a24bfd4db6cce8b3aff721a  data/ledger-free-read/replies/l4-b-chain-haiku-1.txt
adc66a3345f1c1bd20b806264862cc5a4ef2c1199a24bfd4db6cce8b3aff721a  data/ledger-free-read/replies/l4-b-chain-haiku-2.txt
f935e77b050b61697a07fd155869f2f5c710979e4cf7d5de3e9dbd6d1f9b1d0f  data/ledger-free-read/replies/l4-b-pieces-haiku-1.txt
fb77028c168815f07a632c5ae7b100656d0d283bf67356619228d787e096cf66  data/ledger-free-read/results/rows.json
29df134fd7dd11fa175a7579a65d326c0ab74db64fa1bc9b75ded13461f85135  data/ledger-free-read/scripts/extract_and_grade.py
71e13af4826a6624b8a642afdce6d280d1f8537cbd92e486462a8817dda58854  data/ledger-free-read/scripts/make_puzzles.py
9ce213f3cd809cb83100ed0b5dd880406e6f5ca3b708e63ce8b05a93563f2e99  data/ledger-measured.json
43d18eed62604aab9006cae76a6ee04445170866486d14246fb933646823cfef  data/main/main-l14n6-1/analysis.json
bb77248f86b282d4b87f540591079b27eaec67bc01d2316aec2a9542488fe7fe  data/main/main-l14n6-1/driver-run.log
d1166fe4bed1526cc5a6877c83c0a4496082203b6fdeb9328bb2645ce20ffc39  data/main/main-l14n6-1/groupc-run.log
e1cbd4057ed94e6735d7a3ca079213d8ea6eba1240b6f5d90244545bb3f773a9  data/main/main-l14n6-1/groupc.json
b0f8b05f729b5e6cee6deaa2384c986646217adf72a96772d5096bd2d6e3234b  data/main/main-l14n6-1/k.json
9194e3272e6a6404b86833799b475a9c814a07d3bc1947941ee12ddf622b2faa  data/pilot-plan.md
33ab260979cffd6a720f96aeab57f6384c9e6bd49b8730d0a4eab543184120f0  data/pilot/curve-ladder-l14n-1-d90.json
1300a410d652323f9969fd2e44ff843619e72205a5e74cdf1ade01346fdc36ad  data/pilot/curve-ladder-l14n-1.json
ef408fc585cd7045a8345fd21c035ded9862cab4d6521ef0891d1d5d47b87d1d  data/pilot/d72-inputs-ladder-l14n-1-d90.json
a13358eac48e5fcaf1d3aff32550bc18a0f25242967acaee87fc82ecd36c5cd9  data/pilot/d72-inputs-ladder-l14n-1.json
1a5d052fd0f8958cd17a3b25c3df3ef2ee6567a7b4f37e32b26a7d26e0350e27  data/pilot/pilot-ledger-1-exploratory.json
1fdf8225f044d6063b9c7f40bd52dbcf6a8d9d33ecc61ad275036430a77f201e  data/pilot/pilot-ledger-1-exploratory.md
a95350b9e229bd2681306170c840a1107afc32ed4fa2b3a4d7264be825529353  data/pilot/preset-choice-ladder-l14n-1-d90.json
4cf5f2f8ebf30c6f95e85c4181e1db679f9447b15eae730f821cd877fb84c50f  data/pilot/preset-choice-ladder-l14n-1.json
556fb9830fff322f5f4c25e9f6052f50e86ac14a0268ae4dc375b566e5a5efdd  data/pilot/preset-choice-pilot-ledger-1.json
3d173b387bc65810433e2850c06c724855aa40634d724a350bc2aa7d57f6f40e  data/plans/main-l14n6-1-plan-all.json
5063caa2c6169978b93a3ad30375052990192ba0f7bb69206a855e7b67a8a2dd  data/plans/main-l14n6-1-plan-musts.json
411f4ac4b04216a9346e35557438d4b098cc9e1ee1a8a04a9940b6e3e21d0671  data/plans/study1b-never-sent-control-lock4.json
136f952ad557ff5d10c26a25339a8c924b4eb5ecde18da522ad522e0d8907311  data/plans/study1b-never-sent-control.json
8701049746890843e12c4cdbc00211340fcc04af374e34d83c0bf9fd51db3052  data/plans/study1b-never-sent-lock4.json
e12de56da9da4deba3e963b14b923aa497f4f2b6dbfb16be680ba4ca1cb81344  data/plans/study1b-never-sent.json
e718e315107916f1e7a1bf27a4d1cb9debed72fce5013794b7002021be9e41b3  data/plans/study1b-plan-booking.json
00abea9b0c585ce0c3c386b1fdd84029e4667c76feabeffd109725331162b911  data/plans/study1b-plan.json
ad1a274430745cf409c9a25ea78862b2ab15ec8c4b95ddaa1e04181da1bec312  data/plans/topup-plan-booking.json
bd342efbdce2e8bea41c804b57a73642b086e64c87f4efe339ea831403c4ca5b  data/plans/topup-plan.json
da6c1545f07bfe98b759474b3b4e1ca17afd458dd7a177143739f6c6dfd81676  data/tasks/check-ledger-l16-v1/items.jsonl
6210b264af993a247e2b7ccdd63be2cd0693f243996f0dedc54a093d93420293  data/tasks/check-ledger-l16-v1/manifest.json
b48a1fdf5077d4419bfecb5698907a56a6409f2ced52b2779ecce93b79a8e381  data/tasks/ext40-ledger-l14-v1/items.jsonl
bc75bd227179be7c19ffb1f0929967bf87da1b9536dd04b695bb7b4890a5c444  data/tasks/ext40-ledger-l14-v1/manifest.json
611d73cd27af05ffc8e2c81645bbe75cdc56d240eda376d746a17c767956ca78  data/tasks/ext40-ledger-l14n12-v1/items.jsonl
a34e35b62c06fe78d2178b5fb60ec36d4f31e9240c5d7f7c7699f29e94fd64eb  data/tasks/ext40-ledger-l14n12-v1/manifest.json
00fbe9c26e770f3377683cea2d7de1c32945e341be4965475fdd81e4d2b8a587  data/tasks/ext40-ledger-l14n16-v1/items.jsonl
53fc645704cf346347cec3ba2dc837ba9da6442f0444c877d9da1f0584a9e47e  data/tasks/ext40-ledger-l14n16-v1/manifest.json
ae0b642167d829d8b3ed5e7db2cbc84b3211d38f9622666f48e5a68c523b9f68  data/tasks/ext40-ledger-l14n4-v1/items.jsonl
584d708499677fd454a96a443bc4fb5bb46ca5e098b3197b8005ad751495da1f  data/tasks/ext40-ledger-l14n4-v1/manifest.json
1f342a6c9b0129df5796a52612ef50cc58ba162dedd6abfc4036cc38173b94dd  data/tasks/ext40-ledger-l14n6-v1/items.jsonl
e4bc0a7ba8b701f657ab287762328bf58481afbdeda55b9b42bdd5590b5dc4d0  data/tasks/ext40-ledger-l14n6-v1/manifest.json
28bf32e0a132350889a242360edeed081c2dcfcd46eab59a7673877dfd8f6476  data/tasks/ext40-ledger-l14n8-v1/items.jsonl
2f06796238ab00536c7c1038e71e24b73dea7721398f24c2d6648bec2fd31394  data/tasks/ext40-ledger-l14n8-v1/manifest.json
536b83868fa199fccb81a7b15b717d6bec735caf884ae116a03aa6d02b11575d  data/tasks/ext40-ledger-l15-v1/items.jsonl
1a9f5288cbf1e88fce60a876c8c588a5b07e28cbb551b67712e22f4dbcd66dbf  data/tasks/ext40-ledger-l15-v1/manifest.json
f424c276c7e7fdbad5ab5b4b9b2246e0d6770c77412baa7f56927b572ed3e7b1  data/tasks/ext40-ledger-l16-v1/items.jsonl
06afa6fd8c3b7eca9ed3bb5dde3d2998f173e0edb3c6bc739346216616be640d  data/tasks/ext40-ledger-l16-v1/manifest.json
9ac487325ede011169d1260826076fc55028ffb0b5e7eed829694366d5394e94  data/tasks/ladder-ledger-l14n12-v1/items.jsonl
549df49f9549f7fc1268d442d960a4fa90374675a1f3560becadc6ebb989a61b  data/tasks/ladder-ledger-l14n12-v1/manifest.json
0503cf11971e8b5a00221f0eb0573f47497490732941478f88f5afa55ecbb12b  data/tasks/ladder-ledger-l14n16-v1/items.jsonl
0c889ea5f239a246695c9c6fe634e3f7b4a1b98c1788ead63911e969ccdd3267  data/tasks/ladder-ledger-l14n16-v1/manifest.json
fd3454f7406cb8ac376c7d09462bc2589767b2692a93bf37b86905c5b8f4ac56  data/tasks/ladder-ledger-l14n4-v1/items.jsonl
983e2e07c4e1d5ccd3c89290d6d5da24faa8f1d33172f6c40b959d54901c79d8  data/tasks/ladder-ledger-l14n4-v1/manifest.json
e9e2d56098aeb2a63cad8111aee2e7399571c42980acd4ee01c7a2fa4e81f19b  data/tasks/ladder-ledger-l14n6-v1/items.jsonl
aca0ad547d230599a39e1019781c3d5eae42d998fd036ac0317502f2b20732b1  data/tasks/ladder-ledger-l14n6-v1/manifest.json
c69192dbe5393220a0d5927f157412ff041d61142c2c6cf9724652690c41f808  data/tasks/ladder-ledger-l14n8-v1/items.jsonl
6eba40069b36da9ec9c93acf674ddc1ab73cfce339cfb7735f6acd5e6ccd32f2  data/tasks/ladder-ledger-l14n8-v1/manifest.json
9aefe3406a17f08bb0614fe4fdf72b87a5b7e2ba0fde1a0072805d27d44f7c44  data/tasks/main-ledger-l14n12-v1/items.jsonl
08a62a74e129c3b659505696be6f0725a680cf8564cc5bc68a2a12e19c6c7efe  data/tasks/main-ledger-l14n12-v1/manifest.json
0bf12afca05edd504085c715c9ce1b5cdd8eb40a67978db675f8884e7a55f372  data/tasks/main-ledger-l14n16-v1/items.jsonl
6f8eade7d10694994a8acfa43caeef90d69af4fbdb80d6f22496090ed44d26eb  data/tasks/main-ledger-l14n16-v1/manifest.json
7775bc12d5f5a1bf42c4d24556f23f947c40f3bd20123df5391925af2f6a109b  data/tasks/main-ledger-l14n4-v1/items.jsonl
ae2fbda53edb1af83ba39381789579a3002c9fac7a68ccbcaa883d4d9e7ae175  data/tasks/main-ledger-l14n4-v1/manifest.json
11deebd8109adfcc7a1332006ceb63db6e14ab170a8afaf8fe4b8bd6f17f09bf  data/tasks/main-ledger-l14n6-v1/items.jsonl
5d73a19a8ac5eb9c9565768e28b674f5058c88da5dccddd3098f4c4bea1f2862  data/tasks/main-ledger-l14n6-v1/manifest.json
472f3540613d215f0fc7abb9e61d6d70018852741a804b8f4de5e457e91f8abf  data/tasks/main-ledger-l14n8-v1/items.jsonl
1d4ee408a548ba6812b8cd2dd18ea6d5f6fba0c938b4b7ffda3758c85d32b8ac  data/tasks/main-ledger-l14n8-v1/manifest.json
8b62ee060b96432687ac41375a163fc6d9d617eb9fe976ce956fa44e8d095685  data/tasks/pilot-code-c3b-v1/items.jsonl
4d3b658da15ee3aa6498f867bd48032c5a2c35ab722b2acc6930075ec8c142a3  data/tasks/pilot-code-c3b-v1/manifest.json
2e65723dbcb55f03b13e3cace213a4d6b8401f28c3bb9b26194de359f7302e33  data/tasks/pilot-digits-d4-v1/items.jsonl
67ca7651f6fcf276e209eb876ab7296a051eb085aa5361fd3de7ca6ddbcbd94e  data/tasks/pilot-digits-d4-v1/manifest.json
b8bb6f6e788544447c453957c84dae4082f95b94a9d88b5ac29759a8c5208694  data/tasks/pilot-digits-d4p-v1/items.jsonl
94a7e471db6f1b081c71eb51eb8ce3e8a8dfed5a35a6e101efd2568126b3ef85  data/tasks/pilot-digits-d4p-v1/manifest.json
bc86f1a6240ae645280b9746712270115bd873155707d6449605f5b2f1e3a18b  data/tasks/pilot-digits-d4s-v1/items.jsonl
c3e2a89680ab46bc7f8a92295421650c8ec866ecebbdc1105fcc62929efc9b68  data/tasks/pilot-digits-d4s-v1/manifest.json
a9136afbe8cc01e5a098352bbc9475723dc4a83a31bed10f270b197a91e05775  data/tasks/pilot-ledger-l14-v1/items.jsonl
6103f92b8d354d46f8cc6349e8b5550c226a63d446faaf62a836f5051ededbb1  data/tasks/pilot-ledger-l14-v1/manifest.json
ce28f75f320423437fb3316a9734e54ee19de1754cfdb7ccc5cefa3d41430493  data/tasks/pilot-ledger-l15-v1/items.jsonl
41314433cfc48888c4ff76422bc0b1d8cbad084ff6d22044e9931ffc297a4bf3  data/tasks/pilot-ledger-l15-v1/manifest.json
e174f2d3cf1c6dda9bd1d75f417d5b16e2a95fd594d05a8cc43fd961a3b3e112  data/tasks/pilot-ledger-l16-v1/items.jsonl
315ba81db54cf668807d342ae1f96e956852403a0f92ab47785a644121eaaa30  data/tasks/pilot-ledger-l16-v1/manifest.json
ea91c870af61dda76c749de5e1795fa9bd0d258ee2790419723007288664d1aa  data/tasks/pilot-ledger-l17-v1/items.jsonl
97e83a9026555585c313d1911a9991cae6833b20d6061a8d64db5fab02809037  data/tasks/pilot-ledger-l17-v1/manifest.json
71375f559900c3a0eefaec397ffd6f384ddd0e23990716a7103be500255354ed  data/tasks/smoke3-ledger-l16-v1/items.jsonl
09b7a3bcf0fcde74d1514360a220bedfa700e70be336f790494a84c18cd09ec9  data/tasks/smoke3-ledger-l16-v1/manifest.json
e0fbd8ee5329dfe4815af4f85b4dac14fb4447eb0f8aa9cc501ea03e3053a561  data/wording-check-code/README.md
5677a3b4cfabce4b6f7810f79f70a90cf113e20f8f7e6498f2adcf3d9a14c9cd  data/wording-check-code/keys/answeronly.json
d969a086adf3360073505e9e8b53b35816720f412cec33af8546de80a92482e3  data/wording-check-code/keys/chainA.json
1f613b969668547bc5cbd415c0c37335a30c9b88f3fab5b055b153a90678bf22  data/wording-check-code/keys/chainB.json
da9a07ca34cfef3cb13c0d55addd36bbb155f5c34e27d354adfb40ce382a46bc  data/wording-check-code/keys/pieces.json
edd67faa22c3d6bda443075c61edb03af9385f6a2c50cbedb21bec8b7321d3cf  data/wording-check-code/puzzles/answeronly.txt
2b1de0aba4273e16a8c6c8cf4a5e08bd9ec91240e3359ba619e98d09eea1472c  data/wording-check-code/puzzles/chainA.txt
4a757834be1c3b8df757e6e939c5ef5496e650da2777823294506f6f3b71fdde  data/wording-check-code/puzzles/chainB.txt
9556dd08fd3e2fbf005d327d17d0980b4901a31e348ed89be1e03b5ded1f9e0f  data/wording-check-code/puzzles/pieces.txt
867e4dae6778d89337bb3a685f6d4e90b6a3c640277c74c803f1f828ba9638d4  data/wording-check-code/replies/answeronly-haiku-1.txt
5454e41c284f21aca3c8b9dfdb1b6cb7eb693971048b49916f499f425c115319  data/wording-check-code/replies/answeronly-opus-1.txt
a8aa478a5e0303028eed2adb8e85fb36ccb06ee4f2922584c655437e8026e532  data/wording-check-code/replies/chainA-haiku-1.txt
a8aa478a5e0303028eed2adb8e85fb36ccb06ee4f2922584c655437e8026e532  data/wording-check-code/replies/chainA-opus-1.txt
46fd403633d3301d096456f9d61425491449147b3946b00c5af831a8acde6ee8  data/wording-check-code/replies/chainB-haiku-1.txt
73ce8b3d32c1d634318016844d7a2a101189b2b1c561581a1a9cb5f30b461777  data/wording-check-code/replies/chainB-opus-1.txt
c99b2ffde3190c65bf812ef32454d117e2fddc1a79d2c24a1c6961585a29a703  data/wording-check-code/replies/pieces-haiku-1.txt
e01b133476ea63f83801147849c0f3d67f3425c7b0d9c0a390f64d8b68ffa837  data/wording-check-code/replies/pieces-opus-1.txt
c7c008b443e252d922336165ffbdbcddee71ebc509b284b8016f6fb9135ddbef  data/wording-check-code/results/rows.json
cfb6eb0f0665c23a1f364887bb1dd7f4ce1c911a9591eb3846bd32deda7b9e28  data/wording-check-code/scripts/extract_and_grade.py
529878fd1bd4d648e7e5d2e4387d4c719b9c8d844b347876ceb625718f7388c6  data/wording-check-code/scripts/make_puzzles.py
b20f65f13967f17f50ab468d1f7fdb81eae4faa88f88116e612a1bba7a15bba1  data/wording-check-variant/README.md
5b54940517a2aec5fc130ab54506aa0e5ab9e5699d2eaed3de2b3d61754f4a00  data/wording-check-variant/keys/chainA.json
3922274da8b68bd7df8ed4b60592faa79a03d555c1a05d8459493bfc7960f907  data/wording-check-variant/keys/chainB.json
bab780fe6e33808ba1c8282fb4c1776b25a7427d4d01e8bb25a047f080a442d0  data/wording-check-variant/keys/pieces.json
a8a23b7e21758c39628266fa7bd2fcf7aed591062aefa73b00748ee8a71025e6  data/wording-check-variant/puzzles/chainA.txt
5b962d11a3af30af73afd5c954a3c34d6b10dde66c094946145ab87edab46808  data/wording-check-variant/puzzles/chainB.txt
7764400f57fc9f9bb197ff3d532ee6d809d25811920e9f30ee2fbfe445c54406  data/wording-check-variant/puzzles/pieces.txt
1fd4b9340be9dfd930c5942fdd2fe08a48d3043e497a645bba8c813bb3cb2457  data/wording-check-variant/replies/chainA-haiku-1.txt
1fd4b9340be9dfd930c5942fdd2fe08a48d3043e497a645bba8c813bb3cb2457  data/wording-check-variant/replies/chainA-opus-1.txt
1fd4b9340be9dfd930c5942fdd2fe08a48d3043e497a645bba8c813bb3cb2457  data/wording-check-variant/replies/chainA-sonnet-1.txt
5edac22f797ba1f0ff0ade0625bc78a84da9af17f1b0767a0a3268297ae79715  data/wording-check-variant/replies/chainB-haiku-1.txt
00f75b21d27c2135d1319061db50ea91d91dcb15c902e69d5c877068035bf35f  data/wording-check-variant/replies/chainB-opus-1.txt
37ebae8342cd75956719187d3b3bfd1957d86216388673989c83adbac0198e2f  data/wording-check-variant/replies/chainB-sonnet-1.txt
82ff89ac4c88eac9035f05737b249584a6c5fc824f49822cf72453b9dd3778d8  data/wording-check-variant/replies/pieces-haiku-1.txt
226dbbfa8372714a5f406558ae016bb9c820e7be5937b1001f221ffddbdcbe5d  data/wording-check-variant/replies/pieces-opus-1.txt
226dbbfa8372714a5f406558ae016bb9c820e7be5937b1001f221ffddbdcbe5d  data/wording-check-variant/replies/pieces-sonnet-1.txt
600191ebb1ba9eab687a29d856ae5d789bae9d08c598dbc57e91da9a2d2c2b6c  data/wording-check-variant/results/rows.json
edc22618b08236624bf4b14fe8ea79c5221fb3b78bcc0fbdad8e54d2d9cef594  data/wording-check-variant/scripts/extract_and_grade.py
59eda8e4eefc14a0415a469acf12a9b75b2210137791b1e133274e991af53dca  data/wording-check-variant/scripts/make_puzzles.py
0e879c48219d8b7f3b3c14d5ae3dc21191ab2d874f2e7f6e98e324d8a610496c  data/wording-check/README.md
05c5f7e29f54c394d5329b19f11b0c41e155808d15ccb40e41436ec27bce3425  data/wording-check/keys/d4p-answeronly.json
15b8bea7d75290d97068f57ce57e8f4adb3d4d0dacbc0981ab88e513dbcf3a05  data/wording-check/keys/d4p-chainA.json
ac0c4a8dfa326fb7368e4d2829ce37501656934c31ceb1651363bbf7e0c848ce  data/wording-check/keys/d4p-chainB.json
c7d7297411511de3aaaac3df5c698482a62f8b3d8ae2cedc602af60fa5059618  data/wording-check/keys/d4p-pieces.json
d68ded4dc9cf0a12243183eedd481d1eef1f0e46950bb5658e733722ebf61d12  data/wording-check/keys/d4s-answeronly.json
75e403a56961f89882be5933d69b1a9285edf0211324e69be24bfdf42a1785b5  data/wording-check/keys/d4s-chainA.json
7c8dd64fe9f1ffcf7ff1c0ee19cbecf71449b8e0dcd14575e0c3396e31547b54  data/wording-check/keys/d4s-chainB.json
7639d9e91f512f4d900a90067904df25eb628aea53e20317757ddb2091e6f3be  data/wording-check/keys/d4s-pieces.json
f6d29a4d05712b819c34893e1c069dd3a0514f064664c4d7dd887860c301d590  data/wording-check/puzzles/d4p-answeronly.txt
aa36643f03a78146c802330a17952b79439842c1d80e92cf7ce19c94a6f0e878  data/wording-check/puzzles/d4p-chainA.txt
0372c960fcffd211dd89c19e4aed46fa02ee4cccc8343c8ddce0cddaa7254c6c  data/wording-check/puzzles/d4p-chainB.txt
cbd1f0353a52ea2d92f77dd728f0e14a68d9ff1c8804d734925250da839d83b3  data/wording-check/puzzles/d4p-pieces.txt
55e39bca23c03db4452630362e23d0f94697b8fd2ec697d13b10b13dcf6d560d  data/wording-check/puzzles/d4s-answeronly.txt
d5b7278bb5fb5fccaaa7784f10e8a6a0c31419f85d43f85ba4729878b9d1d5cb  data/wording-check/puzzles/d4s-chainA.txt
fadee696e688a14b96d59bf78143ce79d3b310f46a31120a1872829ee26f9045  data/wording-check/puzzles/d4s-chainB.txt
214679e7e0e9fb66fade962e824f10558c9a3979b9e2d7397e18e8e343724d36  data/wording-check/puzzles/d4s-pieces.txt
b249299bf6b684b230aa8ef9a229cac9ae4a40b00afdb89d6d641fa4da2a4eb4  data/wording-check/replies/d4p-answeronly-haiku-plain-1.txt
f160610eab3ad2ce93821242daeceef32b13a4f5fd55d4e63cfef747702a4f43  data/wording-check/replies/d4p-answeronly-opus-plain-1.txt
758f3e5ff1a112a7d91f03fd9d9dcd367000e3a3d21d79724b37bc2579635f48  data/wording-check/replies/d4p-answeronly-sonnet-plain-1.txt
1f03833c1e1b7e8957f4c91502400b6ca6c154cb34ade6e4f8368b2678590a1f  data/wording-check/replies/d4p-chainA-haiku-plain-1.txt
8c4420e3f0cf3dbbbd89bd5e130c8a77d8bbe8f2ee78e0830c6beb699cfa8e31  data/wording-check/replies/d4p-chainA-opus-plain-1.txt
8c4420e3f0cf3dbbbd89bd5e130c8a77d8bbe8f2ee78e0830c6beb699cfa8e31  data/wording-check/replies/d4p-chainA-sonnet-plain-1.txt
12c1edf03b5a2591542562fc62bf043cd3c3b1d0eea8af4d5dfbdaac85628447  data/wording-check/replies/d4p-chainB-haiku-plain-1.txt
a157a6e2d637bf16bb5ec6b9082d018d191fdb3df0fe3f0992ea14a5c82636b3  data/wording-check/replies/d4p-chainB-opus-plain-1.txt
a157a6e2d637bf16bb5ec6b9082d018d191fdb3df0fe3f0992ea14a5c82636b3  data/wording-check/replies/d4p-chainB-sonnet-plain-1.txt
81f1ee3579c3ab66ebf544c1a33b62e7c24c74a6399d92ea846052d891275063  data/wording-check/replies/d4p-pieces-haiku-plain-1.txt
81f1ee3579c3ab66ebf544c1a33b62e7c24c74a6399d92ea846052d891275063  data/wording-check/replies/d4p-pieces-opus-plain-1.txt
81f1ee3579c3ab66ebf544c1a33b62e7c24c74a6399d92ea846052d891275063  data/wording-check/replies/d4p-pieces-sonnet-plain-1.txt
baf6e6c1531e63b0fd1679fe830ab717273a439e89b0f7690177e8b205312eb0  data/wording-check/replies/d4s-answeronly-haiku-plain-1.txt
771d8d2ba825df8235deec4c1d063b3d2d783194e1b27f50e6fa5a3ae6fdf21b  data/wording-check/replies/d4s-answeronly-opus-plain-1.txt
771d8d2ba825df8235deec4c1d063b3d2d783194e1b27f50e6fa5a3ae6fdf21b  data/wording-check/replies/d4s-answeronly-sonnet-plain-1.txt
72c4dcf21cd582b26c1db4bec5cedc0e71dfbb2327e03d1efe03d1436742eadd  data/wording-check/replies/d4s-chainA-haiku-plain-1.txt
09771107e9ed684ad46d614f5fe1e0141f3244259a2a2f12b5ba79e3ccba60a3  data/wording-check/replies/d4s-chainA-opus-bare-1.txt
dca617cdde5fd97727418563542fbcabea4325408006e125d4a8dfa672573e6f  data/wording-check/replies/d4s-chainA-opus-plain-1.txt
dca617cdde5fd97727418563542fbcabea4325408006e125d4a8dfa672573e6f  data/wording-check/replies/d4s-chainA-sonnet-bare-1.txt
dca617cdde5fd97727418563542fbcabea4325408006e125d4a8dfa672573e6f  data/wording-check/replies/d4s-chainA-sonnet-plain-1.txt
0e51c05dd4ef87786901931a8b4bbf462025f38509148414b34effb9d68996f2  data/wording-check/replies/d4s-chainB-haiku-plain-1.txt
c10d559bbfb68ede03ee2dae11afadb9ac4b435eec4bd145efaecf13f4919a3e  data/wording-check/replies/d4s-chainB-opus-plain-1.txt
c10d559bbfb68ede03ee2dae11afadb9ac4b435eec4bd145efaecf13f4919a3e  data/wording-check/replies/d4s-chainB-sonnet-plain-1.txt
cde015b7325b9a602aef3e0deae2a703b6729914696f96f1d76d4c98e06b6e16  data/wording-check/replies/d4s-pieces-haiku-plain-1.txt
cde015b7325b9a602aef3e0deae2a703b6729914696f96f1d76d4c98e06b6e16  data/wording-check/replies/d4s-pieces-opus-plain-1.txt
cde015b7325b9a602aef3e0deae2a703b6729914696f96f1d76d4c98e06b6e16  data/wording-check/replies/d4s-pieces-sonnet-plain-1.txt
f873b772ca36fe85323062db1d64c297ea7894454eee306dd8b38090299af6e8  data/wording-check/results/rows.json
dccf970561e895d88e63eb610dc08b094b50430b3743b452f18e06da9fd5777a  data/wording-check/scripts/extract_and_grade.py
34abaf570a2c8fcac4d5af10ab77c8bb319eab0a83e00d28b02182b2fe09538d  decisions/briefings/2026-10-10-study1-design-check/README.md
84e1fd6f7756a3771f6e52a4163c7e5ac166e35b84cfa77a038a95cabe21b675  decisions/briefings/2026-10-10-study1-design-check/analyse-codetracing.md
3c607e52605b73e92828d318645a716192021353f56eda63df667ecae7c8008a  decisions/briefings/2026-10-10-study1-design-check/analyse-cost.md
c79c7fe5cc2d131cb9db0d047f28f29bb9813cbb413c3b529d3cad3ec9777e95  decisions/briefings/2026-10-10-study1-design-check/analyse-critic.md
57482c0c75bc1cb2c681782ca2a1d5d8331ae2dc8bc7d0666b29f4cc0c36a001  decisions/briefings/2026-10-10-study1-design-check/analyse-precision.md
ac6cb45a3b354d4e42ee2d1ed7400e961288ec4a94872559667c9283548860ff  decisions/briefings/2026-10-10-study1-design-check/analyse-setups.md
b7de8c093b45f7ac35cb13a736da015e3dc034ba0f10d240c14f7f42c8a4543f  decisions/briefings/2026-10-10-study1-design-check/check-codetracing.md
016810b6e380c46d11cc66e8cb21d9143f12b615929d78c399df8568989ee23f  decisions/briefings/2026-10-10-study1-design-check/check-cost.md
4128d6e31b36c3a787c8dc2d0f7150b5d6f5b4bdc588967e9bcb7816ef166049  decisions/briefings/2026-10-10-study1-design-check/check-precision.md
27ed9e2ee1dad38565a01b09274981179ae9acda1fab7dc17424969f790e6a32  decisions/briefings/2026-10-10-study1-design-check/check-setups.md
2f08657eeac9c93fcda7b66826988ee32727dca3e46f6f561e482a5d6d846b46  decisions/briefings/2026-10-11-ledger-difficulty-ideas/report.md
a52bb49c56d78eb5ac2c534de148785717df4bc067b28ae8c46f3c9f56239ffb  decisions/briefings/2026-10-11-ledger-difficulty-ideas/top10.json
a3c004ed02eca9f9e1af509670912d144773bbe98ba6248b36fec449aa5d8e9a  decisions/briefings/2026-10-11-mock-peer-review/meta-review.md
a8050e31065d0d7aaafc2652b77d4a138eab0128d2f770ae78ac37e23fb67185  decisions/briefings/2026-10-11-mock-peer-review/reviews.json
6e51bd4eb9e293ba124679383050cdccbb01b6d19bb2f0e1a8aaf74eadd54daf  decisions/briefings/2026-10-12-analysis-stamp/analysis-stamp.txt
c5ef73a9b6ee8955faa282b58f3ece91a31ded23ee08a8ebe704bd953a9317ff  decisions/briefings/2026-10-12-zenodo-steps/description.txt
2a4782fa779c843285c9fa85df2ce3cbae91b2537b314bbd852de36a1990004b  decisions/briefings/2026-10-12-zenodo-steps/fingerprint.txt
ed4e914bb7a699c2013e9fb98fa821502ced387440dee2bcce0f4936ddde1565  decisions/briefings/2026-10-12-zenodo-steps/steps.md
fdbd6b1362331d008bad44bc68568d2012913ff9820f4fd18edc0a0c222f716a  decisions/briefings/2026-10-12-zenodo-v2/description.txt
60b642684d80255e5f91e5722dcd174f2446080877d048d9952e87e05ed134c0  decisions/briefings/2026-10-12-zenodo-v2/fingerprint-lock2.txt
eb8cd54aca318ad3b9843218a82d660d9d109fcfe741eb6a2fa787c490329ab8  decisions/briefings/2026-10-12-zenodo-v3/description.txt
d499e653a2ec133889e1d5f9c57ca9c665d3b8e7fd3ab718be97e1d28552f396  decisions/briefings/2026-10-12-zenodo-v3/fingerprint-lock3.txt
7c95be383d203d1a95b61a4320e46143b7f2125cc092b5823c491efd757cb19f  decisions/briefings/2026-10-13-findings-register/findings-register.md
f07b76541788b197c5d41f1c8c7fbc5b62680623d82e45030fdb36b083af17ab  decisions/briefings/2026-10-13-lock4-audit/audit-pass1.md
30e0c3b18e533ff9179b0c966f2eb9f6dd0736081db7dc017e6cdf15b2a02ccb  decisions/briefings/2026-10-13-lock4-audit/audit-pass2.md
5b4fca85ba0df6afba6c58365627d942872817da878338ef5423a65dd6a53b49  decisions/briefings/2026-10-13-lock4-audit/exposure-scan-20261012T2145Z.json
f38efe96fe5c8760e21ad99f481fbe69de630bf35b918f9b49cf81ce43dbef8c  decisions/briefings/2026-10-13-lock4-audit/exposure-scan-20261013T0521Z.json
a78fb10981e8ba72208684b4ae1b24aba733e2058d870b84eed5ae2218e19ae7  decisions/briefings/2026-10-13-lock4-audit/exposure-scan-20261013T0721Z-final.json
44ef26593c11467bc04752578cef1291d238da98617282e01f56217c16a5fd19  decisions/briefings/2026-10-13-lock4-audit/exposure_scan.py
2d6b48ca181b11f74e23e66b4186ab3325b1cd3290a54aa24b76a208473d459b  decisions/briefings/2026-10-13-zenodo-v4/description-filled.txt
05509246f26fdad421326370116d6156e244f2edb7dcba2ee4bd000072f7af61  decisions/briefings/2026-10-13-zenodo-v4/description.txt
5890f6a8dfd7642e5bfb12c940f16c4a44cd87adb8570be6d8b43ce4f6767d61  decisions/briefings/2026-10-13-zenodo-v4/gist-filled.txt
860002de4f209d36f8d5e07f7f9d5c0bff0906e25f775943e7897ed0cfc66c8b  decisions/briefings/2026-10-13-zenodo-v4/gist.txt
d9d50f57b0357556f1355ea7b9db6575993cdb058802c34e3f4217e73265bcac  decisions/evidence/2026-10-12-console-reading-158.30-post-main.webp
206eb0adb778186bc23eaa8377d3900de5b3fd0bf5cabc4b2b772824685245aa  decisions/evidence/2026-10-12-console-reading-179.28.webp
012ee9ccea537a2383665536bb8cafd21117f9eb69412751f0c8db0a9ac3be94  decisions/evidence/2026-10-12-console-reading-188.22.webp
76fe0a32cc23f76f20e1061c15f12181d9b6d9360e88d38fb51417b9af3d2bad  decisions/evidence/2026-10-12-console-reading-197.36.png
1b0b546096a7241e4636a38a318eca45a2ee7a0dd1e5ffc4267231d9fb427454  decisions/evidence/2026-10-13-console-reading-158.30-pre-study1b.webp
67b3d7a6c346aac71c8e4acc2ba182086b1f73d9388c342b00ac4d2d853a9269  decisions/glossary.md
a526675c1a223f34d656f6720493db432a6f7f3a40f6026a54cb2030b5ffc440  decisions/readiness-checklist.md
e50aca8805bc06991a219d5e367419242ac7d3f58d2adea9e746c4a9eda62e19  decisions/register.md
ba3f806ab9c691866f132ab311e1f51f26915ea0976647494d3f4210ae11500d  decisions/tracker/index.html
dc82ae9f283110f3782cafcc3989d318a4c7c888f1f3dc64031316a93e2a679c  handovers/README.md
a80c869848dc0b9cffcc2faad4285581db1ef20769ddcfe91a735a9b87eb0275  handovers/edith.md
2d943d04c3b8338c9eab26383a92827a6a9d28b2ecd52cdc965a7c27040bac65  handovers/friday.md
895c0039bab57144f50ab906a2c02210bfaf6f741665988f7df54f14691d3b51  handovers/jarvis.md
50a4563253c229d8690f7f79afa4ef3f72fa3dfdfe3a5459d72d01638ff80c81  handovers/karen.md
4b9383688ae104d5f53f4b572038ce4920b429da772685311a57d2e2c36eaede  harness/README.md
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  harness/analysis/__init__.py
072e4f89eaee32db8800eaf2ac21d8bf33e128e4f3275bfa1602165095e419a9  harness/analysis/bootstrap.py
79051dbed84913ea00f030cbce5e10c9e65df4dcc7baec783e6c7966d72d25a3  harness/analysis/choose_preset.py
948261958e81e6ddf460f9f7391f586162eebd0435754e3d01aab637e793a732  harness/analysis/curve.py
eb87a481bbbcd372f630d6a569f36b4b954357e7e71828987c298849b519b5da  harness/analysis/explore_pilot1.py
6af248e7aaa70f179aa53b922cbae7b3255ca0512568e5aff20a685984319587  harness/analysis/fairness.py
909db113f458547e99cd64c38510d6d88587849f1b34d0aaac531085cd3f06d3  harness/analysis/fairness_input.py
0f0eb98d03cd11856d57f35af10a5ad761c831189c429e3e899bc165db1263b0  harness/analysis/five_tests.py
cfde07c2ea20cc2a55c181f8f4579d6ed7dfcae9ea15dc4d79660a5b375edcca  harness/analysis/k_step.py
6c4d21e59b9a18b8f3668c8ed2632eb525abb43a179fa0ae45a0d22a11d8fc34  harness/analysis/kscript.py
5fb0ab788aef57759e3a90f3b4b8dd5064bc36c2c25fac9fb9de74fba1695627  harness/analysis/main_analysis.py
a1096ab2db2517e025045af7c2ae98d135afa7ed6bb141397a29ad5f64cc579f  harness/analysis/main_rows.py
10a02289caa915446be12a0418005e6b3dff6f11a1bc53c02b8708d6f44eabc0  harness/analysis/report_arms.py
8dd8a3e1d2b43d7d63b7871c20b750dc883665380d9ce49291122bff1e463db4  harness/analysis/report_costs.py
b5110387595efe2bc357669022f18c87be05a1368092ebbef00d13ff9e5fa887  harness/analysis/report_groupc.py
13ecca1ceed0be8473987ec1cb0dad08d7e4c5008144c8ffab4c37890f0928a8  harness/analysis/report_votes.py
26d522e105f5f95ff65435f89e5b50dc7710088ec983329b1a05edea70322d1c  harness/analysis/scoring.py
957f63276197fdcf9c2eee0e8f43b542c63ee8c1be76a4f3ef72b6226a2295d3  harness/analysis/study1b.py
0d045fc6f96148e6231e2aa467f0dc93660b8bcb2c6cf188d8cc30a3a5155257  harness/analysis/study1b_k.py
c0d4433f6d29d88e21dc6163335c742b960d294df51ba786e97ef49805392d6c  harness/analysis/topup_analysis.py
06803cea94019553f8f0c51179eb54312033f87858e0d322649ca279b54432c4  harness/analysis/topup_rows.py
0acfbd8ab12130c0efaa6bded4242ebb681f61ca2d218fb5bc45e4213ef4ba0c  harness/analysis/trace_parse.py
806c289b1474dc1dd2b46baeeda6473d8df67e23e795c4dd62878df362ef98d3  harness/analysis/votes.py
6ae8e335f237236d9565537d42f676f8833156916a26c54af479e5b9363866df  harness/lockhash.py
4b5837df219b5e393030fec5c8fc4b43d9e5c91500487271fb0162478f416cd6  harness/pareto/README.md
25ab9dc5bd823e82a707ae8dcc2bd97e5e683eaf4925e5bb9d656f1c30e3bdb0  harness/pareto/__init__.py
19c92f8f7469675fb3ff53e09bfc7c63f5300438dcd2c22459f0dadf2487928e  harness/pareto/apicheck.py
3c169ab5b1006e274c961db046e632c92884d7a905d3058fe42912e70c4d7c0f  harness/pareto/batch.py
c60c505cc5d1c70d747f408e96c4be94b62f48114370cf51fd4fddd995e86a35  harness/pareto/calllog.py
24156bf02ba02c37440c92299b62d236b5ffba6ece7a90d5c18d74331d2e8f9c  harness/pareto/client.py
8efe56cb78766cc7783fa5ec62ba7ce7dd15cb44b2c82b4580ab25a2260a51a9  harness/pareto/d42.py
e3d345bca21c62e608d6f96ed7a292db2b264e4907a1d2746808527e961ee1b5  harness/pareto/e3.py
07211b76f4ec5ba39abd51e69569afa608f40d1f261d700b41897b54480d4cf0  harness/pareto/guard.py
058d587abe24505a803edc7ffe1512069126e2c6c93babdac5d5cc4eab3c3841  harness/pareto/ladder.py
f74b2f8048eb604a3a90993b36c9497b722f21576e70bd57f9bc4d86851bf80a  harness/pareto/limits.py
9c8eed7ccee6225c7393b7ecd3ecd65d74ae09f8145bcf877ca8f60a52445bf8  harness/pareto/live.py
cfb2f105e1b48be57fee3da84154668dc62720e6f1bc547dd6cedfd81b0ecf6a  harness/pareto/main.py
459791101ff7d2df9ca00dd63e1a080e65519e7164cff4e244b2a531db73f9be  harness/pareto/manifest.py
756873a04471340abb89505c1b009f9d23ea6bc93ed5b308062e31d92949d843  harness/pareto/markers.py
6e3a7437e1668dffd80c66d53a2b07e5f6ef95674edaa9740ef4779e81707540  harness/pareto/neversent.py
8bca533871c0ce22b7b353e863d2fd1bac1aee1b43ab60734976d021535ae7ac  harness/pareto/outcome.py
fbc22e1912631ce0d325b644d3910aca2c42a9f4faa286b32c0b61209efde60d  harness/pareto/pilot.py
500edff3a3ff27606f51b70b835921bd458f418e974249f4dc73051c63e27435  harness/pareto/prices.py
75d138d55ddb7bcfcab6c426e5b77b519274054667b19d2b71ea1e16a7007103  harness/pareto/request.py
cc906965cd5e8ceb77497efa0929fc4bfa7a5f6fb03bb5fdb360fdf40581b33a  harness/pareto/s3check.py
d4f39db2f3a6d9a5a2ff6d6aae51b4c9cdce1a84d1797ae018053f8130403e6b  harness/pareto/secrets_env.py
84df9b24de841f73964734680107ebd11b1c68608bfe6a324b3efef9e3a35186  harness/pareto/slim.py
abcd1c4225c98d66e9dd386ace802bb6ab5280faf457c26379dac0f71cdf3c43  harness/pareto/smoke.py
b8fc4dafaf39e75a329ebef8bd7c429802e8896fb79f99526faed06a578d6ff5  harness/pareto/table.py
46cfd2af44b2cbf71807fa8974873c4363ef60428a84d23eaa20810a15709fa3  harness/pareto/topup.py
eab2bc0c48ce913625c2a1f323eb21ebff825c3b1e76f7de061c818cd843e87c  harness/pareto/transport.py
e426975f7680eba153716fbec5de1762092e50628cbb9731fc395cd3abedb019  harness/requirements.txt
fc384c6fd63470ef18c14c62a931857aa46221ff939761df0e60a8578dfc90e5  harness/taskgen/README.md
ef4034546e0c51c064ad34f86840352858e0d4d433eb4714fa6aaa0463758871  harness/taskgen/__init__.py
112671926a4a4d923445c1a32d5f6b3fec343101f1f834b3da39d93e74ed3a43  harness/taskgen/check.py
1ba49a95aefbae5967fd5aa4e737c5d160e66612830a021c2fb19c1d3be9a72f  harness/taskgen/codetrace.py
9d6b19ae2693d9c4f5e3b6bdf98e7138d8248375796a52706e549ef333cf30f2  harness/taskgen/codetrace_check.py
71f9284ca6c5172ce571767fa7fcbdb407c88af54fc4a6c646980392313f7d4d  harness/taskgen/freeze.py
2bd47699e292386ae87e7cac7130fa03659251b3634eb066179ce2a4d7d98f97  harness/taskgen/ledger.py
c3486dd80e0511887c51349378e984e68881fc4d0a6786fafc3326bbd519bb94  harness/taskgen/ledger_check.py
0644d69bb57bfbac4a7ac1b2a76c6e5bf6f688cc440bc2392e1c3a3d7a993e97  harness/taskgen/make_examples.py
71cb5c9694e717284eabdbae40c7d21207fb0de5c63152998c01cf909d067752  harness/taskgen/prompt_d31.py
c0e79f7c90b6060a70f37de31da788335f8233dae9a6ae27fa88ec1185154b56  harness/taskgen/puzzle.py
e9347c14bb0045339256c3280c9847c841441a516fc29c73f2e8f736c1ec142f  harness/taskgen/rng.py
447c8e02dde5bde5125cd5ed1ebba3564d181b293d6bb4c96f90dfeb7e40856d  harness/taskgen/wording_pack.py
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  harness/tests/__init__.py
d8eb270e83e0b05409f949314cef713a50e80beb592b8f08b67a8e25b96d08a9  harness/tests/fakes.py
f3fc9490d3d4717f53fdc047e198361c7fbb688543277c7e9c6856082037581b  harness/tests/fixtures/check-ledger-test-v1/items.jsonl
6b81d19dc7a2623016dd39ab9fc454c1657372679ee6c9909aff425a83783817  harness/tests/fixtures/check-ledger-test-v1/manifest.json
fc05e4496cfa3a530326b4b6fdfe255eaaee94313bf5a3744555b352f7294d6c  harness/tests/fixtures/ledger_kind_args.json
e12838fab1cc4b5f3b8159f3507e1072f9f95d1bae2e12399bb91953263cd668  harness/tests/mutate.py
388bf8c498da476496aec38709423018b8982510eee27a9c1ac07c795686477f  harness/tests/test_analysis_bootstrap.py
9945446f21d65ba22a5ee84022a36a66f4c5e598580564e3532823c6c881eda1  harness/tests/test_analysis_choose_preset.py
190b7b68f813b3b2d8fc12847a336d9a2700ed901486fb9487c33131fa817deb  harness/tests/test_analysis_fairness.py
dd5858b50ccb1385616f0093f0d404e4818873a136276bc1fc99c119786b3096  harness/tests/test_analysis_fairness_input.py
150cf00f1a6599cbee9bbee4ad82119e0dd6ef5d14961da9c1a23ee315a0832c  harness/tests/test_analysis_five_tests.py
9acceabe5458706b70ef9b1733217c8e98c74aa324f082398ebd3e83bb94b87e  harness/tests/test_analysis_fixtures.py
47625c7768ffb647e00a3aaaae8b2cf79d2c8f1517db25f6409081b00f423922  harness/tests/test_analysis_fixtures_v2.py
e762d36f8f3f1b5f7dcb731abebbc87ac83ba2b61f366d4358ebb32152cc40ca  harness/tests/test_analysis_kscript.py
659c7e14fe757cea5c5286e28f3a6687440190fc530e7e774f2846f90dbd834b  harness/tests/test_analysis_n_steps.py
06bad358989d90d6d5992b9bf92ca6d4720bab51c47940d22d28974c14cd54a1  harness/tests/test_analysis_parse_fixtures.py
2274f9976b90660d91d6e3bf712095ea3190cbe3a0dd9663a93a245aad4e49f5  harness/tests/test_analysis_scoring.py
59ef39a37d121bbf50abacca50b1c784a5e5309828027e3524a076ba47c9bc71  harness/tests/test_analysis_trace_parse.py
475981e430d3c7fd94da9f2292381144495336f35241e51347a1c1e5255123b1  harness/tests/test_analysis_votes.py
7a997b93facaa49408ec0f34f0fbecb8a96f3700dbfd8922c0fd17dd1373fb19  harness/tests/test_apicheck.py
09c309f104dfd74ba252410da9777901620d670895a3c15907070e90d576b7d5  harness/tests/test_batch.py
5ab9544ff1a5ad8bb660ebfaaff227ab4a8b6d6d8c4c088147e2b62181bb9174  harness/tests/test_client.py
7ba7f60e597ef77910b2e7e475cde0c706285e9ee3e6b0e4019dcd512b8cb3d6  harness/tests/test_curve.py
e6b1cac397b1ca145d4862f4be1565ed5300611756f8eca1cb37fe4d66552eab  harness/tests/test_d42.py
5d7442c3b8a84da0b763d55ce9db05437f9016d824b5988f73ba1e7848039b16  harness/tests/test_d90_repeats.py
c28517dc146fea40ad67ed19494a53760692e863a4ab55c6363b849116c05b48  harness/tests/test_e3.py
6e6177078885cb9fd7d3ec2ce3879c6a33cd84628a2be5b8db99f87459107f27  harness/tests/test_guard.py
c5fb1fa897cbb3e7a035031f2fcf4ae514b9b02a4de2b355aac712f078e6d186  harness/tests/test_ladder.py
232771ab3574e036336f8fa3dc3f70b82a300812e01527ba58eca1efe846b586  harness/tests/test_ledger.py
e477c715a9aa0248c3ae63b71c56d8f502fc10ad4951e5118a6c37780bea02f7  harness/tests/test_ledger_n.py
b20b54989ba6a9fbc1c4c493eb8f4b68e0671cbfd33661548ca6adc190bd8bdd  harness/tests/test_ledger_v04.py
1f51b1b9451325007e3f5a453ec60c2cfd18e4aa61c9a4a92c5fb7f906cd4b23  harness/tests/test_lockhash.py
ecf9ae692f55f6ee50dd8f190b2807054ea6ae744fd0ac1ca237bd9fb2c54921  harness/tests/test_main.py
13719f3b2bc0802cfe122476ded760dbcc77ee3666ac4bb3a32dd48268febd21  harness/tests/test_main_analysis.py
e62e2844ac12ba1155465ce30e64d6e2e18d8f166eac45e84d596dadba242bf8  harness/tests/test_manifest.py
f5c87abe7e4e7e7d4f045b253936fa0479c064971a20e1c763677a183da469b7  harness/tests/test_markers.py
5d5adefca1760330d767e2d480b92370c095989149c2a13b3260972cad06e128  harness/tests/test_neversent.py
a5287a2cfc8ea674fd47e476c8fce964d5b151448dea5b7bc3f40a5931e61d03  harness/tests/test_outcome.py
43405452c027744a3219e44bcd7cf5fa4d15c9871b5766795fe42782f28f5538  harness/tests/test_pilot.py
49a78eb84bef697e43d6331cac0c90e518e45029350c7ba151cc024e836bdc52  harness/tests/test_pilot_grader_d76.py
9f524a1978169b3adfb3005c3258c52a01f1feb61d97a60494d5df5ac4ffe600  harness/tests/test_prices.py
669918fbc2008bf08f20cbaf921815b5b1c746248832e90f097e63a8f7d9bd57  harness/tests/test_real_transport.py
6a5ea2a5b9e7fafe8a8cef4d9a10277fe69d3be61c165f2224e62643e5d84924  harness/tests/test_report_arms.py
6557ad0c99e9ad5f32fe42cd945d09690d560f8c7e1b43aced0d671b4052fb7a  harness/tests/test_report_costs.py
0fbb234e90559d39a9758446dce52ce1028f5a3773fa8b4513637a2a4408c63f  harness/tests/test_report_groupc.py
c02b66b6da0e058ce7ed4c5bad67720b3aba0fcc8e29f14ee4f9606d4245df4c  harness/tests/test_report_votes.py
bd3d84b869869968ec3cc60428125227fcbe9e95ab458c78934fe3dfdb2a542e  harness/tests/test_request.py
09e4cb9b7c031dba3fa38766d44e31c3402db0d893f5e14bfc25f2452956bc1f  harness/tests/test_resume.py
e97e3c8b39bb860081bbb4c5190cb2b9ff9bd3957caa768a7c992b941e9c4578  harness/tests/test_s3check.py
06b4860bbc599f34a183b0c8736677b51fa0dba3f1fa521f064bdc01f8646798  harness/tests/test_slim.py
b3e103004b12a85b1b959c811749920c50931a2f709d7a04a29b2b4e49593a88  harness/tests/test_smoke.py
aa9c65216baebf03d7e2239ac026978d6a8a35403d1004ef259a32a76ba4913a  harness/tests/test_study1b.py
f1c2f697e6b6c1cdfa515c410c0aaa575e567e75c85dfee27807229fea6f768c  harness/tests/test_study1b_e2e.py
7c2976faa523d708f125885d9102b3bebfbb085212b8aa8e4c136e84d90c6b81  harness/tests/test_table.py
e75ca372b2bab2b299fdc713cdc779e96809020b3d98b841068b77265e90efd6  harness/tests/test_topup.py
a143e8b24368d415b7644b733fa285ae4cd96c99e19e48d4d8e80536879f31d0  harness/tests/test_topup_analysis.py
5811227dd403d0817006990823c2408b3324f840199bd18d174386656edf786d  ops/review-checklist.md
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ops/reviews/.gitkeep
8ac5d0c304a5684cff016bc1b0d9e010acc5ae27f0f610c5e02f0a670a2f24da  ops/reviews/2026-10-10-clearance-smoke-1.json
b7376030b43099f09d57bc941ae4d071eb385df67d55e2422c6172366a025172  ops/reviews/2026-10-10-clearance-smoke-1.md
922b7deeb08b476c709b3b7e68b94f3ed49103f4da843694bd730fbed1b03e05  ops/reviews/2026-10-10-clearance-smoke-2.json
d55912b013dd26b1a56b09c2efb82ba2247dde8488a425d21631dc99fcb75498  ops/reviews/2026-10-10-clearance-smoke-2.md
d86f2d3ec60e3ce8b8fae19fc15c26d515d006fbfad5db961cbbca99a2e3a34c  ops/reviews/2026-10-10-cyber-refusals-factcheck.md
505f66af1927b3ff4ca1ae363d9ff47f641fc960af943190b58cb4404d84b7bb  ops/reviews/2026-10-10-design-check-review.md
4648e769e1c4d3a6bb843e155b22b878555deca2015ea5a2aa268f4ea1b51871  ops/reviews/2026-10-10-ledger-levers-citations.md
2077227230a32a62fea66509fd9503e7e4f3d697c136f9e0e922a5032abdc21b  ops/reviews/2026-10-10-n46-batch-reservation-note.md
d4eb85a12b5b323fd16c9e42c0f8130dd4b55f8542536755917063a122126850  ops/reviews/2026-10-10-pilot-plan-ledger-r1.md
908163913271a5c394176c139479ee2bef07a1af96788df21e8c71ab0047f9fc  ops/reviews/2026-10-10-pr1-taskgen-r1.md
ebc230c6740f5cf00d892721035372539de5ad46b5bc45e71ed27832e8a04931  ops/reviews/2026-10-10-pr1-taskgen-r2.md
94d1b29c126902749875ada42dbcbcbf1eebac27dbdfacbc8cec28cf5d372cd1  ops/reviews/2026-10-10-pr10-codetrace-gen-r1.md
2858924016ab0d5d8c821feb9bd8dfd5279d5244440939d2e29cc75af05a3d92  ops/reviews/2026-10-10-pr11-harness-guard-r1.md
c192e42220d75b066d31d651da38b992c8d7d4c1dfa1435a2976bb16afef5d84  ops/reviews/2026-10-10-pr11-harness-guard-r2.md
9ed9150d58f8fbc23491d1ed60c72fd1798adbc92a87aaa88be886478fcb4e23  ops/reviews/2026-10-10-pr11-harness-guard-r3.md
c4aebf701a421dc20b207df083335ef8b4ed5bab505637550f63156634855fc2  ops/reviews/2026-10-10-pr11-harness-guard-r4.md
29386728244d31b8bac111c208d3f547dcb143f3f72cc24fedda3541079448b5  ops/reviews/2026-10-10-pr11-harness-guard-r5.md
76c5cfbaf97ac9c5737ffa86ece3315fd9476836a85033647f73715ce9d236fa  ops/reviews/2026-10-10-pr12-code-wording-check-r1.md
c942aef0fdd34add17808e95e9df305813e8e492eed831ef64c03b28de2ece8d  ops/reviews/2026-10-10-pr13-spec-d37-d43-r1.md
ac9a1c34a0714474d1b555ecbd5ee39cc7a680ff904500342123e70894c5bf65  ops/reviews/2026-10-10-pr13-spec-r2.md
95e3d7ce46189baf5b7de9564b841caf8fc927457648f6d0aaeb34c7f24e34fd  ops/reviews/2026-10-10-pr14-prompt-variant-r1.md
618c6ab8db6f7a05cba752863a578ec87bbc09b9e6b7d5690b9c2dc575b8083b  ops/reviews/2026-10-10-pr15-pilot-sets-r1.md
1e50ab99941949745652453ea79e56e0f0e12546975b557b23902c0b12fdc910  ops/reviews/2026-10-10-pr16-gate-followup-r1.md
3933523a4445a59eb5b5b4334a54388012636c1bc1095054e0e7c8548eb25a8c  ops/reviews/2026-10-10-pr17-b5-console-r1.md
4640bc9c8c46de59503dac70aa48b73b2d9c8fd0a83775e9333d34343ae4b552  ops/reviews/2026-10-10-pr17-b5-console-r2.md
b7254a93fc7743bee4ffdf3762b2714c51e95f601aa435d565142f2e4acc4170  ops/reviews/2026-10-10-pr2-dials-r1.md
65797c78b55516f9af7db586fec812b7a9d48b6ba41eb5b4b5589bb96aa40b68  ops/reviews/2026-10-10-pr2-dials-r2.md
167df7ad9b17c1d354d8a6cf7e5ff423029acf5052f4d3a96a93cc95b0e6ffe1  ops/reviews/2026-10-10-pr3-spec-r1.md
809d97d3cdbea4d916be36ccfb5ff0279ce986daae3589c2bed5edeb7dcd9ff9  ops/reviews/2026-10-10-pr3-spec-r2.md
97ef1892b3a82cd627b66371019eea03c6cf6b450238ab170cb2e36ccd043fad  ops/reviews/2026-10-10-pr3-spec-r3.md
07405d854d52b3b01f930f6fe2d5fe5f335e997d7db489049706f46666b14f33  ops/reviews/2026-10-10-pr4-free-tests-r1.md
7e3f0fb470e60e7561d483abd31e67cf941bbf0d872e8cf31f1d85e6c8ae0dbb  ops/reviews/2026-10-10-pr5-d25-presets-r1.md
aafb13e35020272456fc27af303d5a4f1cbf28b9eb30d4610c501215a1e38eac  ops/reviews/2026-10-10-pr6-spec-d26-d28-r1.md
f03d07c132b43c5da0174a93d48df5c98c5e598bf406ada99bddb58cdef9c22e  ops/reviews/2026-10-10-pr7-codetrace-r1.md
e083c45e59a608b6ceda1438f6d05f31108a84e6dd63e01180210878d1d2dfb2  ops/reviews/2026-10-10-pr7-codetrace-r2.md
879b78129b2370f90699c3372b5519be7530584c50d8bbed260c16ec46f2398c  ops/reviews/2026-10-10-pr8-item4-prompt-r1.md
d805590f8981ad3d049ce8e08c75d923947ed710b50dded372627e831d9308fd  ops/reviews/2026-10-10-pr8-item4-prompt-r2.md
043497229537906302d0d6496452e6b9741417cfe7e4bd6e9849c29f3ffa21a8  ops/reviews/2026-10-10-pr8-wording-check-r3.md
5b014859777fd184fa6578216dcb0043a7166a88da826226b238410b3a496d78  ops/reviews/2026-10-10-pr9-spec-d33-d35-r1.md
fa36288e16bb44f6f0555961ecc63ec3a6b66bc231c8423c8ec808a705f3f6ab  ops/reviews/2026-10-10-pr9-spec-d33-d36-r2.md
84254ee763683aea4b7a52394841975d2da3ee8deae16969f272e3e9f2c14268  ops/reviews/2026-10-10-smoke-1-401-note.md
fdbd0710431c17ca860501e03f9e6ed01398f54a5251541b5dbe7359f86b4ab3  ops/reviews/2026-10-10-smoke-2-review.md
e73e041ff5420f24e2accc436b1ceeb76fd1575d49d1d59126e30e6284de32cf  ops/reviews/2026-10-10-task-families-r1.md
71a6659473c3fbc99f6056488ec22c3ee8aa5efbc5c7d05b2aebc3d2fe171e8e  ops/reviews/2026-10-11-backup-persona-citations.md
5ee0afbbd9d23ce65e4b93fb315523c3b9da3575dec20737bd4ab84db1152f29  ops/reviews/2026-10-11-backup-persona-rescope-citations.md
1ba28a9945d4ded3c183bdc630767554546463ba584b9e98e41583bb9315c4ef  ops/reviews/2026-10-11-check-ledger-1-result.md
0c60e0c4510d91112f50e568b9cdad1bfee0623d5a319e5ea9061e4ef76c4b80  ops/reviews/2026-10-11-clearance-check-ledger-1.json
7e362bc3e7b06900739201c327f5a85388173103aceece0caa89ca27738acfe6  ops/reviews/2026-10-11-clearance-check-ledger-1.md
e78003ae75976c2979f0436505f05c4f2c8e1b9ab6c6fb521516d03723dee299  ops/reviews/2026-10-11-clearance-s3-ledger-1.json
0fbb7a8be49ed7d287a261d2162f7402fef276de6fb4d873efa03bd73b6124fa  ops/reviews/2026-10-11-clearance-s3-ledger-1.md
8da4c99d3f5cd7ab2267f634e05035c207cdd3eb9fd9e15f980951ea90db6b40  ops/reviews/2026-10-11-clearance-smoke-2-markers.json
cd6caffeb21b57f302653de5f2f22310f295626918be723972d1632513fad528  ops/reviews/2026-10-11-clearance-smoke-2-markers.md
4754c58cd94ce774f8a5b3b6dea937eb4a32aabb87d835aedba2c1380e8f57fc  ops/reviews/2026-10-11-d74-lock-code-r1.md
d118e2b20305b6d4004f5132208166aa9e8fae3d8633854c0aa62e416947ce6b  ops/reviews/2026-10-11-endorsers-spotcheck.md
bf7323f950bcabc9f907df66c9b78f737815de6c437e124f6c50a828283274be  ops/reviews/2026-10-11-fair-test-tuning-verdict.md
e6fd9b51e95792b4401aecc765247280f69ffd776c21691a3f6b54cc5270f001  ops/reviews/2026-10-11-family-switch-partC-factcheck.md
dcd56f0eda1a9987bf14b63858376907b03b0ab7f0ac96bb65f47b17029418f0  ops/reviews/2026-10-11-ledger-wording-l16.md
48ffe45b4a1d5f9018abcbda9b6b50b2b201e6727479cf777a2f84aeab752f3a  ops/reviews/2026-10-11-lock-contents-plan.md
b374e22b0ee0a3fcc2a0c580de657b4a5e2dd080d50db48e51ae7644281afd01  ops/reviews/2026-10-11-lock-prep-r1.md
a1e604280733ede126a441a51856e7ab4d0412947fc67ea55e2c3be7c019fa93  ops/reviews/2026-10-11-mock-review-stats-and-fairness.md
3fb56d77864b0cb7eb80f15cb985a44caffc8a3aa90f2616264d30fa4758e1a6  ops/reviews/2026-10-11-power-cutorder-house-T.md
261b8da4547c8ee382bfb51c1ff6d1bc2f1aacd15cc98558df0d5f25a3f250f8  ops/reviews/2026-10-11-pr17-b5-console-r3.md
b8b91c8cd4837f6460d822b36deab9fc7ec81d6bf28ecb41488ef4a09c21b139  ops/reviews/2026-10-11-pr18-spec-ledger-r1.md
68a6b31edddfb839e3358d661b27ab970d88da429f0cc23770ed946e8a60bc56  ops/reviews/2026-10-11-pr18-spec-ledger-r2.md
afcb2e9162867827978c7e0ad0f1604708a4b0b13e0189481709dc7e23f5cf21  ops/reviews/2026-10-11-pr18-spec-ledger-r3.md
c171e220a37c9e8147da5ce09fd2f5e18c07ec0a8dfb0c48c952fbf46599dfae  ops/reviews/2026-10-11-pr19-ledger-r1.md
24a10af059bc59435567762780975105f5aeb7c3d48b6e22545d1212c323ed6e  ops/reviews/2026-10-11-pr19-ledger-r2.md
c9783b6d49a873159b0c9bb43eb24b4e17286fbff04695ce29d7dbc02ec54576  ops/reviews/2026-10-11-pr19-ledger-r3.md
dde31d2c31ae415290397ad0de38119fd52f143d0baa5e6c84fc6a211917f97e  ops/reviews/2026-10-11-pr19-ledger-r4.md
4ebefc28ce954893d90cae4596adbd6070c74af93f10c8563bb334eee4e12eb1  ops/reviews/2026-10-11-pr20-price-date-r1.md
070cbe74a3df308589eeb610457f49290f60a2201d5cde5b0acf60d48a03844a  ops/reviews/2026-10-11-pr21-markers-r1.md
41038aca44f5adf91998f9c7aafb20570ef12f773dd398dc8d79788860300022  ops/reviews/2026-10-11-pr22-legacy-fixture-r1.md
10c4e08b55d35cf274c80634085f01b91f5137c6e4797aa38decfcd794ecc66e  ops/reviews/2026-10-11-pr23-spendlog-markers-r1.md
441560f58b89aebdbc35a9b46ce344a01cdd47c240bb229a611ec9743e44987b  ops/reviews/2026-10-11-pr24-analysis-r1.md
cbf24cea21692d2ebdd5f4f29e28a0c2782912e5146937a3b8f92eb368a3c4ce  ops/reviews/2026-10-11-pr24-analysis-r2.md
c9e7c5c6793147ed088f6572a5977606cc4fe2c805c93fa93467c95e71a90e39  ops/reviews/2026-10-11-pr24-analysis-r3.md
f028aa1543fdaa7f49827b7f67e12ae557c6af2d76808f202c2e8f649c9abd2a  ops/reviews/2026-10-11-pr24-analysis-r4.md
68e2b1429abbedb4c2bbdaf7ba6995d1833d5580cb43af19d2066aa75308fc87  ops/reviews/2026-10-11-pr24-pr25-r5.md
0bc2763a3658d41e6791453524faa71f4523ac055f01d3f6123ed822328fb184  ops/reviews/2026-10-11-pr25-fairness-r1.md
b09eb5f337afa7814082e27cf6605244e04edabbe62f2315d5a874397c79e118  ops/reviews/2026-10-11-pr25-fairness-r2.md
7d3086cd5b5facc73980c3d5155c0dbfbcf20ad955c0d9b9570be6bf7e42d700  ops/reviews/2026-10-11-s3-plan-r1.md
0c732f7de69367faf0366217c24774d5b07bda2255b8d360b48d6e24bb7fc338  ops/reviews/2026-10-11-s3-runner-r1.md
3c77b7c8fd15656b8a8e7fb8ca02234a0670f63e1365917856aff51dfca8d594  ops/reviews/2026-10-11-tuning-fairness-citations.md
a9c8d71aacda87f1e969f8ef1cc88f62fc3646772e64f6eded78f329b85bf60a  ops/reviews/2026-10-11-venues-factcheck.md
8db7f15d2049f60f3fbfa528d185aed133b7471a4861a9fff0c225b75c75be7e  ops/reviews/2026-10-12-clearance-diag-haiku-effort-1.json
797c3631cdb20afca8cf9b682b2076f30b1608a1850deaf5ecb5483a701ab16f  ops/reviews/2026-10-12-clearance-diag-haiku-effort-1.md
294dc4532166b2f88ae5a6560c1caf7d82181965e6d5dfcd14aecc9557878f9c  ops/reviews/2026-10-12-clearance-ladder-l14n-1.json
f16fd00cb1692d182316729baec0c85a7b2a1496e9efa8d8e9641e1e377cfa76  ops/reviews/2026-10-12-clearance-ladder-l14n-1.md
ce6f0ad11d206a0f951f24f17cc0cd2fee2a105cdc1c856e7f65603bdef0b77b  ops/reviews/2026-10-12-clearance-main-l14n6-1.json
46f7dc88fe60f98054d987615bf99949628302836a137a560886d958f07aba2f  ops/reviews/2026-10-12-clearance-main-l14n6-1.md
3603c6d0cc70051310c771ecd1cdefa59e5fc88bb59fa009a47c29abf3372a7e  ops/reviews/2026-10-12-clearance-pilot-ledger-1.json
a17ce5006f33d3d887a3bb235e6d32512fe80707e6f91462fc7fa29a2d8ea48c  ops/reviews/2026-10-12-clearance-pilot-ledger-1.md
df406e390ef61a948d38d53fd358d1b43ade0a94df7e90c9087e7928a62c5ad2  ops/reviews/2026-10-12-d42-arm-r1.md
00a8318a26ab7adc7fad02f071251113593c72f79a51d95d309c4b8d3902e8e3  ops/reviews/2026-10-12-d90-parser-amendment1-r2.md
17e02e9b6b34c623dd7df1b7258e171f512e986009d55ad9933e324f2f332b36  ops/reviews/2026-10-12-deviation-note-1.md
1dab67ad7a927d87a9c7c62a76cf8e5e43bc490bc213ad30ad7b94fcc4001a76  ops/reviews/2026-10-12-deviation-note-2-and-lock3-route.md
b244108c2c4e1c41475c8e5384cdd2e736376b385b80b1b0af184a3f94d09aba  ops/reviews/2026-10-12-diag-haiku-effort-1-result.md
b966f5888f3c87f9ad6de35f6d2ccad68a47fb14c2cad8d68906328b712506b1  ops/reviews/2026-10-12-e2-hpick8-drafts-r1.md
7fd227c127e57ec59eb3ee60454d3a88ef281b1962ae8ffed1499fa4086ecdeb  ops/reviews/2026-10-12-e3-runner-r1.md
be45e91416a3d11ac448f838ad558c8c94fd64630470c79c99636bc486ecb048  ops/reviews/2026-10-12-factcheck-results-summary-1.md
907a4ecc933eecfa2d1cef2a451a6ef6e7582731b9b0389f48f47d1078d3227f  ops/reviews/2026-10-12-followup-procedure-advice.md
ede8c5046fe1dc273a49ec6594b6fe4163d7d70373471ba7b5bb0088f8f954c3  ops/reviews/2026-10-12-golive-signoff-1.md
db310e48eef83f0d7b1916c559bc1c28a7cc594f43abc6b26969f44a4a83d6e4  ops/reviews/2026-10-12-ladder-curve-d72-check.md
840d48a4a7c5374823d93109384071a95707ee6ef97066437aa04e935ee793a8  ops/reviews/2026-10-12-ladder-l14n-1-pick-check.md
abeb69374f913d056617488340b7cf46bc5dad786d1eb229e74bba0ed54024a1  ops/reviews/2026-10-12-lock-review.md
cff8438c653678d78a3493bdff0d5c60833ca8fdb5aa3c456eead9cc85a90c88  ops/reviews/2026-10-12-lock2-analysis-r1.md
3107be2e0196f7fbe3a4f2bf6eb5c1b3de4a8e3ce8102ba5275a6516860a85a4  ops/reviews/2026-10-12-lock2-curve-r1.md
b95b4efb12b6eb9f1e6160a148a812838abc568fd7a0f1548d6213b13a2d9bc6  ops/reviews/2026-10-12-lock2-gen-r1.md
792a6739dd2746fadcfefae9452bafb98ab6d928657874cecb215417a2786af1  ops/reviews/2026-10-12-lock2-prep-karen-r1.md
b465ae3981d01c2be17811c03e7d8251fbeb2eefb9599128fae2b9a427deb13e  ops/reviews/2026-10-12-lock2-review.md
614361eb003d5d86f62ed781c77826cac4bbf584d685495f2ffb59bee0405e01  ops/reviews/2026-10-12-lock2-sets-manifest-r1.md
32823420bdbc9a28012e9ca6c1007523e47460b366ef214b66659285f9c9d6cf  ops/reviews/2026-10-12-lock3-review.md
606bd5f3c654ab23c976733f95437e0743fb414212313f29429a2e913d143f8f  ops/reviews/2026-10-12-main-analysis-r1.md
aa1aee92879f266f5a82dc4230606ad6117f570aa40c6b210d00cb0ae1faf7fc  ops/reviews/2026-10-12-main-run-prep-rulings.md
eb0cb2b47a2f5fc5e6dee0c87cef2748d345e59c7be2a07b1beab3903558c1b9  ops/reviews/2026-10-12-main-runner-r1-and-d42-wording.md
527cbd279c351605a0526316fc8e4a82a9601a9f701847392dbd848b0068ec67  ops/reviews/2026-10-12-pilot-ledger-1-diagnosis.md
44e07557239a839d810b4efbcff3fc11be761f631f457e3ffe59cded446a5bf3  ops/reviews/2026-10-12-pilot-rt-fix-r1.md
b0b125686ab3b08bfd2c08b2dce2704e6eeb67cd413e1162f4c2256c8886757d  ops/reviews/2026-10-12-pilot1-exploratory-check.md
79897898d40940514f0bf7f4d8a07d4582cd24df669429b6fa4b03b79297fa87  ops/reviews/2026-10-12-readiness-edith-items.md
376f2e5b5b7ea00ed453221fa0cabba46775fbf0500fd1f84f6ea28f4a861e75  ops/reviews/2026-10-12-reporting-gaps.md
d1795b40533554752bb072b993f24e819d2f0398e62fee1a6b616af38a5f1ab9  ops/reviews/2026-10-12-resume-fix-r1.md
ad435fe5c7cef5fbd0482e4a65020a2f1217b38d4f3a1cff98239165ef682cfc  ops/reviews/2026-10-12-s3-ledger-1-result.md
f8ca7b4756d59b2b306f2314550425617314a0f7267bac9c6098bbf75f9e5d3b  ops/reviews/2026-10-12-zenodo-v3-edit.md
27f5ad0adfe2e77bcf7c870243fd0f0a7d9ba8a3d00ac865932497ae747d2853  ops/reviews/2026-10-13-clearance-study1b-1-DRAFT.md
b9ba2600b81d286960c2db35ed626e1d04bc863fd5ae902801af6e6d308a0f3f  ops/reviews/2026-10-13-factcheck-findings-register.md
4265c0fc617596afbda8bc59a5c6b75ca0791eae3b9f646287893f0a50114160  ops/reviews/2026-10-13-lock4-audit-edith.md
865b688c0bc91004e12e6de18f37c5df0f20a53d8c102aa249a6b2d5853d94f5  ops/reviews/2026-10-13-lock4-fixes-r1.md
dafca297e016150d333e278e912ad6042c2c15f21b601c074d694690a23212bb  ops/reviews/2026-10-13-study1b-code-r1.md
6687f8dcc5f5f23e3d648eeaca93ffef99fa3976f5a013dacc0cc77404aed855  ops/reviews/2026-10-13-study1b-plan-and-groupC.md
55bb03312071cff1f4da36ac113f0a6506521b2900de64f79b7ceae41c859b3b  ops/reviews/2026-10-13-study1b-signoff.md
1d105485fb878bdf8d730ad972d50258464d75417df59ac9206a12228b1ca086  ops/reviews/2026-10-13-topup-code-r1.md
d54f858ae82f798b2bf3264161b91c702fac047f04c14b688ab76751604fc3da  ops/reviews/2026-10-13-topup-spec-r1.md
28284d504fa6b56b5a6d8e1fda7c67f61028b0c6da9d226287f93d2a339f1545  ops/spend-log.md
49562182138aa1449d099252f833e1f61612f241430a2243e91526c1a446cdb9  paper/README.md
1c47aaa63aaa028a5632fcf48903f807929b81ac4fc714711f02d5ddda5deaae  research/START-HERE.md
fb4f9d298ffedcf0bcad4b79610fc09a04fc9db31c92a4cc592248f189b127fb  research/arxivmath-brief.md
5415e29ac868b0b15e08b108f8ca6437bdc6f17fd762054bc0ff346fb11fa369  research/backup-persona-rescope.md
d4e8f511daa51128dd0a58f120ac97312215f29dad2c69a0ca0b18940de7bf30  research/backup-persona-scoping.md
37762e5e6ed312f99d7d5c27d4e5fd0f7122ea72faebdc060cd00f5c41bee9bf  research/cyber-refusals.md
15811c4c7ee2054368b88720df4019d49d74e29128f8de65533080f5582e5473  research/d42-ledger-variant.md
e80078defd6be5e71e75aed0a4d51ec568c3b67c2bd0fe4e093fbe83342f22ee  research/d42-variant/main-ledger-l14n6-v1-000-1x6-approved.txt
a099a85dd2eb4007925825d22fd9cca379cf6a296c2bd8d85e7cde6143bc486d  research/d42-variant/main-ledger-l14n6-v1-000-1x6-variant.txt
1704cb0991869c0465607a82d54e515e0b1f2231dca1035c861797ad7eeefa8a  research/d42-variant/main-ledger-l14n6-v1-000-6x1-approved.txt
ad1308f90b04714d11bb8ae4ea287f6c49348f30f99ce39487fe7fbbe69b6d54  research/d42-variant/main-ledger-l14n6-v1-000-6x1-variant.txt
061de63c1c207093fd8bacec064ef47b6c8c2d4199219a8396371e1350e763bc  research/d72-d73-lock-spec.md
2631cac7a7a6fa43d00d1aeca84cd001a82a6f554c01833ceaac960f0c0e9dcc  research/e2-and-picker-prompts.md
7cfb2c8d8b6aeb3b6830a26768c2b5de9f78edf09792696a3c873042a765b424  research/facts-checked.md
dc906e7d2b6a6eea57f63c86e3a75a3ca4e469501f8e773fd8a3c2b7e8ae7a2c  research/fixtures/sim-main-n/README.md
e89406067d7efaa4b3750fc8c40cab767015025c1db82cf48c362914fa8ad1d0  research/fixtures/sim-main-n/parse_cases_n12.jsonl.gz
88dd4474e23d9394f093ee0c5b156057b735ab58eceb4d20f099e9a1060d2af2  research/fixtures/sim-main-n/parse_cases_n16.jsonl.gz
5347f15dd5ad601e8096a10b8b7f871da48e1ef3bf5f017d0889a85ea23e3314  research/fixtures/sim-main-n/parse_cases_n4.jsonl.gz
8cdad61980476ef215e82777d43c26eaa8ec7894587de12e3e552956a406d117  research/fixtures/sim-main-n/parse_cases_n6.jsonl.gz
66a5862487a0485e4e88dd9e8a2789e10ca087c1d2181abc0f127b5305f8de19  research/fixtures/sim-main-n/parse_cases_n8.jsonl.gz
6f1c7ba55a78a5c7b9b8c149de89284747066200254fcf13357313ef23420232  research/fixtures/sim-main-n/pieces_cases_n12.jsonl.gz
c8e859811a0b5b2e83c9834489b3f219fc447c2b9fb4495e9d544d1076500df0  research/fixtures/sim-main-n/pieces_cases_n16.jsonl.gz
8139f9df9689bebf29bd86001c6943a0750276638d3dfc3e064f7f4278094f13  research/fixtures/sim-main-n/pieces_cases_n4.jsonl.gz
243e6f8a6dd6068e77f575f074af7ef588ff7d7e306130690d44bd4fe8746aca  research/fixtures/sim-main-n/pieces_cases_n6.jsonl.gz
72c4a3d46b9c82db9cb674e4dc924e30cb9ed446b51e4d4bd5c020a2a7ba0490  research/fixtures/sim-main-n/pieces_cases_n8.jsonl.gz
ef675a3b38bd0965936a2c8a8eff76e0e7ce14d546b0832d6186242316764c9c  research/fixtures/sim-main-n/run_parse_cases_n.py
49ec37af29e5d453911f14aadf745981b9bf32d2c46ac2ec726ce6c7d0e640d7  research/fixtures/sim-main-v1/README.md
18343293cdd7195cb2d907a50539237882e7b5500346b9bc35eb20c0b59370cd  research/fixtures/sim-main-v1/coverage-d-10.json
9763676993b5fb2990ae9c72530b3a792417d8d1ef1b3a866fee7b0055c6f284  research/fixtures/sim-main-v1/d-10/expected.json
205bd1ddebe60d6649350f50b462774be23101287b50fbc6e40b186e897d604b  research/fixtures/sim-main-v1/d-10/rows.jsonl.gz
254abf36f625754632698fabc30b6ee5a4f7dccb81abf691319b6cbf4f38bd49  research/fixtures/sim-main-v1/d-15/expected.json
9ac8e68d4aaeee5c9f2ed7115cd990705d66f0d86de1494a1562ae1485d06792  research/fixtures/sim-main-v1/d-15/rows.jsonl.gz
966e4370ccf4bfafe6681db7a02fadb0ac3b126464683d4c9d6e74cfbd884f5d  research/fixtures/sim-main-v1/d-5/expected.json
a19645175d0ce6f3c747a6585d0e1dd2306a6f1f6c34bbb24aa230502ed8b9d4  research/fixtures/sim-main-v1/d-5/rows.jsonl.gz
c7b3bc51ca767627344d11c6f9f00e2e727f4a4e46e6394c5dc9833ed3f3e941  research/fixtures/sim-main-v1/d0/expected.json
a914367c85c82a8bd8142f8961f2c213fe838ae3a2090a02d679be6fb6b2faec  research/fixtures/sim-main-v1/d0/rows.jsonl.gz
5de8832aaed961a9fda64c5aea8c90efe8d436d0733d66274209e4288bf4deda  research/fixtures/sim-main-v1/mixed/expected.json
eff006f05ca861fe01ed5aeb05e3b4a52207e651edaac79eb14ef38fcfb223aa  research/fixtures/sim-main-v1/mixed/rows.jsonl.gz
045625a5d3b7c91f71d449c89d3a0d94ab424534382eee5c74faad38e05cf5e2  research/fixtures/sim-main-v1/ni/expected.json
32f0873f08d88180e2f8716ddd685fb88f3d51043ca972946ccef7d8f0951cd2  research/fixtures/sim-main-v1/ni/rows.jsonl.gz
b9bcaf73da2519e8852276cbda42eebec6ba9713ef7a0ae4351fe8041a018ffc  research/fixtures/sim-main-v1/worse/expected.json
f96ba6ed0d9469ed8903a89391d08c3e22ff3cfa2dc12076c799dfd0ec28ef81  research/fixtures/sim-main-v1/worse/rows.jsonl.gz
1aabe7c4144b61e6891887fbcc9a9d2f98fa007dd5b65e7d0cf9c33f6510d35c  research/fixtures/sim-main-v2/README.md
94dbd464f5dcedb56ffe7d9c64fb6f5208dc7a11eca17cc63ff439f62a47d223  research/fixtures/sim-main-v2/d-10/expected.json
b50cefd4da18baf5f7253a5ff345a19d5e36a4abceed7f7aa56b7ff629290786  research/fixtures/sim-main-v2/d-10/rows.jsonl.gz
05aa5617f8e96ae157b1c9ef5f08ae43f9b247c026c04d91d3d1935858f52a63  research/fixtures/sim-main-v2/d-15/expected.json
9c5574d97e244d77fa1eac6336ca2116b48343e8f03a4d8f8d1d006fa66af462  research/fixtures/sim-main-v2/d-15/rows.jsonl.gz
9f0b838a8844d22f802ca5d8fbdc8e9baeabc2f520f703260d0787600ebe4eb3  research/fixtures/sim-main-v2/d-5/expected.json
4ed7a2d5913788f4109f7b4ac50b940daf68fc6abcb77ddbf135be9e27408b2c  research/fixtures/sim-main-v2/d-5/rows.jsonl.gz
ee97b0791cec97601cb67b75e019a91071daf737b0de16eeaa9261b748abee09  research/fixtures/sim-main-v2/d0/expected.json
1d31a69988f12a8d11f831d4a9f67c9ab4aad4809400d86b443913573bb53d28  research/fixtures/sim-main-v2/d0/rows.jsonl.gz
72e881728e5a67c27e40c358bb7e2d40512fe6eeb98d009815a7b264c5436551  research/fixtures/sim-main-v2/final_cases.jsonl.gz
a6dc5bfc584585ab03a5b1fc0318c2abe5efb3ee21bff32c6b082a2cc4f6de6a  research/fixtures/sim-main-v2/mixed/expected.json
6798b4e06235908fe79548b55fde40b82216b32ef4a0e4d53dc40a1b830a80f6  research/fixtures/sim-main-v2/mixed/rows.jsonl.gz
88177598e2e323218a80ebe4ec981d30fac17cce23308a40c95c9ad1362c3116  research/fixtures/sim-main-v2/ni/expected.json
77f8d261616fc377f9c86ec4a3c80afaf992bd80381ed8755515d698a254a990  research/fixtures/sim-main-v2/ni/rows.jsonl.gz
137c435bdcebf4d9a19d50cea909773f211bb047759d1410aceab8c86b7ee1aa  research/fixtures/sim-main-v2/parse_cases.jsonl.gz
487022d4d6fba957a85d2dc712ef835db13f1c2d2607216dbbf2946a60cdafe7  research/fixtures/sim-main-v2/parse_cases_d90.jsonl.gz
5f363f7faa2fef4532c4bd998b2c0c357212a88371ce0f65ef73190a9d04d336  research/fixtures/sim-main-v2/pieces_cases.jsonl.gz
66d16d12799b4e2ab3c494c4f68714d03b3fc1f34fd9ece9e094213101cb27d5  research/fixtures/sim-main-v2/run_parse_cases.py
69e89c78d01247e6181ee48d53fe4b736d4da0e37416d2b633749eca6e754a67  research/fixtures/sim-main-v2/worse/expected.json
78d2c1e520af646de3e5b51104d32b50d1e1839a5bec14c978f984601b036013  research/fixtures/sim-main-v2/worse/rows.jsonl.gz
c2c7d833c71ff60ded14fa76dde1e7d5a6024b2516dbc3362bff39d1ed7d2ebd  research/inventory-sources/driver-outputs.md
5ef8f425bafea19f0358806a805493f3742bfe8f952d0a8d39e655fef055f4f2  research/inventory-sources/register-outputs.md
b10c9242ea17437553100d64533d7889e29b3ecee3b4405588934177d607058c  research/inventory-sources/spec-outputs.md
8547a6870e853edef1ab3f9f7651f350c915eb2837f601342697d0b1c58572e8  research/ledger-difficulty-levers.md
33e7807fd02896333661a3581282197e14138cdab6041aaf3c3013e35c24b4e1  research/main-run-cap.md
3260a7fb0c29388536f794723bfb4c351f45a0e2b37eb0ea142c2fdc321a2edf  research/mock-review-fixes.md
408dd44486a332d75294dc44240aa865b3904253dca6e1e1ecd8ea6601844943  research/models/ceiling_power.py
cf319dc89e765d777f24d4af279fe6b1e41f29e50cbfd84bcd93d3ea465424cb  research/models/ceiling_power_results.json
493357f38939d9f029baa6ac752d43f5c8ee6062bf8cb5977cc3f38e098ad6cb  research/models/check20_projection.py
d13424f56c283abbad6d6597a0985e77aa93f434ed3ac1974a898888b7620e8f  research/models/d42_variant.py
35e32da2674e71b6e578f7bcc0b23588a0cb52f3ab9dab90c8ca3fe0f57e34ee  research/models/d72_example_inputs.json
63a2dd7b315b5c0de80245a0b274f58c06b8bdeb9a9ba551f7673680ba1c7c5d  research/models/d72_example_output.json
292bb4444e2492a95e9fb2c7334d59231c2412b79a1cf181bcbf3fe46874d11b  research/models/d74_example_output.json
5b6365f8ec14883ebd2a451c2e2c7649b4dff0020fbf1c0cf52f2263c5c5d9d3  research/models/ledger_measured.json
fbabf63614f5ce0168528a0b581ef9363b86b251b51bd64da93e03034b3e0f66  research/models/ni_power_refusals.json
30d0e68887477b31dcbe1f18f06b43437383ca9e64847b6df4b5c8b551a97a31  research/models/ni_power_results.json
6432533592f2a639bf2b1f608068142dcb631b095e8b50b8efca96dae5b6a03f  research/models/sim_fixtures.py
b0401acad693f40d6d38fe362c83d047d40bab75d96cd9f8e8516298507dea4f  research/models/sim_fixtures_n.py
3e54fd8155f6528280df89360d3b334d46b68f8d73157277e80640de8ba21ddf  research/models/sim_fixtures_v2.py
50fe869d3980654ebcbd447b0ecfb05d1aa77dcc624e406bdb193f6c39b5c087  research/models/study1_budget.py
1951338fb89930708389d748e8ef494498aace82b9323f49a1e8a456936711bb  research/models/study1_cut_order.py
44a325b03ece08ea3141c5f8705b6852f40407d946d7a0a6956b869475d107b0  research/models/study1_ni_power.py
34e7adfe225e7116eea37d7f3781ae801a5b1cd9d347e75c5dbc125fe6f80901  research/models/study1b_power.py
02bfe6e9cf00949b627a148279b44ecf90eebfef9bbbec17245875bb5bb4d0fc  research/models/study1b_power_results.json
14d122c73d3343d0344a20d83f779b2627b5397d1def6b8df923b5c35b4bb498  research/models/team_prompts.py
b2d1d14b9f9fddcdb3326759209525fbdc3c98f01b56413b3ffd3cbd5e4b75d7  research/models/test_team_prompts.py
4d167e5f839a218558857561f38bd67d09db471ec799c7b25cd10ea379b65e89  research/paper-notes/analysis-stamp-methods.md
0715754b43f9c44e8d2ab499aaea1a0298e351d06af28ee531bf65b2df1ed8c9  research/paper-notes/family-switch.md
55012f10719ed77047ab8675cefdbe493c31e25ac15db576ea5650fe20d03995  research/paper-notes/finding-effort-n6.md
5a94356a3b448b0cf06c77cf5bbe39d32d55407af547e80310e67a96834ec148  research/paper-notes/findings-register.md
09628f193e9b77634fe1849df9f116345738f83880ffba3e107e3bf92d2ab6ac  research/paper-notes/marking-rule-deviation2.md
5b4a426cfcb5aaf8238dd06b7139dfb4a94222ba9c4be93e8eac528f1da5cacd  research/paper-notes/opus-vs-sonnet-exploratory.md
fb9d86cd47634f83a297dc8ff82a8a96787cef73711f6ef9cd526f0248107686  research/paper-notes/tuning-disclosure.md
ec235202b463bc157276d75d21a33f91e20c7985bdc3e91d86139f1126dab34e  research/pilot-floor-options.md
51c811bdb99e22ad0168d1a02ed4334841b0153beff90b5368ca6942371911f9  research/pilot-plan-ledger.md
8dc243cce69eebe78a41f1f1003fe40240fc0117641b7301265251a071972cb7  research/post-pilot-n6.md
3d1851ae04d79faf438004eca4856df94e762640469659edb85def3ce738a12f  research/publishing-and-endorsers.md
bddab72761b4111f6d4ed439f13ddbd63427bc14a9c61b58d0ceadb32f18bf81  research/reporting-definitions-main.md
18275994f379e978f0f69632f64985670bb69e0de8813cdd94f4c04f6cf87239  research/reporting-inventory-main.md
f0c756378e4b6e91c715ae429c595d6fd8aea9fc4b93cdcbd376dbf722bc8205  research/scoring-step-lines.md
576028d675acd96554b7f565ec4e2d08e5c1f20a67476267f617ace7ccac85e0  research/study1-design-evidence.md
b739ed97dcb918a6c676a85143854cf49723ea23bd56df62c4b9a2ceb5988857  research/study1b-never-sent-check.json
d059ffa7e99f813074705d0bf15c822803b8b2f0111a2361ff64d4d851d79936  research/study1b-plan.md
4b6779502c26ae1da96b55573b0f9e62d153caa4509ef543b748c5d70a72c879  research/study1b-spec.md
dff560b2cabb5df9f7cac20e85da23de64970a58e0af055cd962aedab221145d  research/sweep-2026-10-09/raw.json
2ca41293e1f7f0579ecf7492908fc8857e023f110d3438da3d010c3d449068cf  research/sweep-2026-10-09/render.py
655b6fdd86c14b829b2b8579b20f7173e076d3b0d68653bdd7ec088eebcee3a7  research/sweep-2026-10-09/stress-tests/debate-vs-vote.md
8bd78a3df40ef944d2e906e8bd731bd509557adbcc712beb1533eb7b0516089c  research/sweep-2026-10-09/stress-tests/effort-vs-size.md
7b1d8ca97edc43660fda6fcbb37b657011db22aba6d0cf25b69dbd7aca6c6471  research/sweep-2026-10-09/stress-tests/role-tiering.md
606ddc1a0c8246f56729815708fe6ee0cc88538ab9f4943b4532c4b137ebf9a6  research/sweep-2026-10-09/stress-tests/swarm-vs-giant.md
ba8dfe8c7b72f8d2f4bce5379e38c8bb3416e8216b0b7bf8c95925624b2f0b4e  research/sweep-2026-10-09/stress-tests/verification-asymmetry.md
b4e7290e2069285641528159e378e8261641dfcbc320e537edadc7d6cdde0b13  research/sweep-2026-10-09/surveys/benchmarks.md
6d5e1663d30cde739409e78116337f045c00986bc4634911a355a374a13e7550  research/sweep-2026-10-09/surveys/claude-55-landscape.md
8f035e19b2352a5b124532af47454e679ffbcdc4febcb1f8c52cb5139bdd3712  research/sweep-2026-10-09/surveys/contrarian-gaps.md
9a9476743b61ac9604b0423630e965fa632a8eb16c8da188071341fd6c3cf2da  research/sweep-2026-10-09/surveys/mas-landscape.md
0a25599575d95496f33f6cae71a9bbcee13a7f65c1998d5cbd4f810da683ec3a  research/sweep-2026-10-09/workflow.js
b1b8cb22a9d4ea040c07c784deee40c79728ec5a25c90abb2abf0485173d1ba0  research/task-families-noncipher.md
f41058c26d0c25cc2bea8f05ca3815d0c70f5ba27e97d0ee5cf96d65841a6862  research/task-options.md
889acd2f4a1490150ba8956509bb00244add1cec7b913015b2b9005c8dec35f8  research/team-prompts/main-ledger-l14n6-v1-000-1x6-e2-aggregator.txt
5cf11fed1cb4b4ccde0a1f5eb0db4fbdae661b61711c29d0cdc13f8a1994d5f9  research/team-prompts/main-ledger-l14n6-v1-000-1x6-e2-helper-1.txt
351fd27b442a618bcf4f2684a35bd0696b224e862185e4e275db75ff01c9b781  research/team-prompts/main-ledger-l14n6-v1-000-1x6-e2-planner.txt
62d5daf7a9a7e50bda246127b4372a75776f19d54a6ee9e6d95a8af1fd2afcd9  research/team-prompts/main-ledger-l14n6-v1-000-1x6-h-pick8.txt
6a7e4dc2d727a68f4006556b0dea7b1ed1b4e656d37d4df6da0816401ed440cb  research/team-prompts/main-ledger-l14n6-v1-000-6x1-e2-aggregator.txt
157a3acf09fd8a220d91abb590e9d69a84329852d1ce79f05a99001d77841701  research/team-prompts/main-ledger-l14n6-v1-000-6x1-e2-helper-1.txt
4febb6910cdfdb61cad1086224a962eb9fc72c37fbfb37acf8dc9e044c794018  research/team-prompts/main-ledger-l14n6-v1-000-6x1-e2-planner.txt
7529bc93d75023e4657e58283aedf1346be20f6e80504f539d7fb7fa2558e36f  research/team-prompts/main-ledger-l14n6-v1-000-6x1-h-pick8.txt
f048e73a8ccc843f9d575e4fd51a0d462d1e39d5c1635bbad5d1a493170b41c5  research/topup-run-spec.md
e3abd5307e05523baa82ad7a9609956d8522b0f62e43bd4cbd4ccfc639391e14  research/tuning-fairness.md
a80a76059747adb72179b10e3f450a4122d84d7b6b865a3197d5bcb0bc1d790f  research/wording-check-d42-ledger/README.md
2a5f55d2124b7a879992a3175f699cf36679b4576398aa9a7df9f8a9950e4866  research/wording-check-d42-ledger/keys/chainA.json
51fdf0f4d6aab5d0942e987e48d4263bfa23f3f98b073758ce1bf048dd3ae6dc  research/wording-check-d42-ledger/keys/chainB.json
92ce808f8b7b98efdaacec982447ad265863d4c0ea052b92f9dc9e5ef633b353  research/wording-check-d42-ledger/keys/pieces.json
8cc9608eaec6a228198bbc2761648823774b6e8ccb9df9faa45d8236d4871972  research/wording-check-d42-ledger/puzzles/chainA.txt
5ac94bdc02e48dac19057620c850dbe56889aedd2a7dec3035b00f0689f198f5  research/wording-check-d42-ledger/puzzles/chainB.txt
a1c549fdebc64147347cef553bb8b220636d7e3efc0cc266fd3e1c679c260146  research/wording-check-d42-ledger/puzzles/pieces.txt
0f45303de2b90c4ccaefb9cb35adf58c18c485438644c96b7e3bdf8c80704ebe  research/wording-check-d42-ledger/replies/chainA-haiku.txt
0f45303de2b90c4ccaefb9cb35adf58c18c485438644c96b7e3bdf8c80704ebe  research/wording-check-d42-ledger/replies/chainA-opus.txt
0f45303de2b90c4ccaefb9cb35adf58c18c485438644c96b7e3bdf8c80704ebe  research/wording-check-d42-ledger/replies/chainA-sonnet.txt
0e7ab9ed0bbfb132ce2dbed03522aa7c54f140a973d4325d2120e113c52f63cd  research/wording-check-d42-ledger/replies/chainB-haiku.txt
0e7ab9ed0bbfb132ce2dbed03522aa7c54f140a973d4325d2120e113c52f63cd  research/wording-check-d42-ledger/replies/chainB-opus.txt
0e7ab9ed0bbfb132ce2dbed03522aa7c54f140a973d4325d2120e113c52f63cd  research/wording-check-d42-ledger/replies/chainB-sonnet.txt
7d2300c100fb4719beeff0d1c84fc9c6b287533242be3fa8cd000fd1e9c77556  research/wording-check-d42-ledger/replies/pieces-haiku.txt
7d2300c100fb4719beeff0d1c84fc9c6b287533242be3fa8cd000fd1e9c77556  research/wording-check-d42-ledger/replies/pieces-opus.txt
7d2300c100fb4719beeff0d1c84fc9c6b287533242be3fa8cd000fd1e9c77556  research/wording-check-d42-ledger/replies/pieces-sonnet.txt
36001168e985a988684bb2892babb62a44f3ea20cea9bf54aea3a64b4ad6d62d  research/wording-check-d42-ledger/rows.json
27c546465a40bba07d43038ec32746046843739ab1cf1d3e0cd7c64c124a81de  research/wording-check-e2-hpick8/README.md
65e477a90dc0550420956f2a9d663c08be386daf347eb354051eb56f8aa39118  research/wording-check-e2-hpick8/keys/1x6.json
eb1ebd9a0b2a44da32ee704b771352dd698aa16c31bb63301085f98492240961  research/wording-check-e2-hpick8/keys/6x1.json
6ba1d83f120a127e332f9d2e18def4e238bd79dbba1489baa20e393d2ad55993  research/wording-check-e2-hpick8/prompts/aggregator-1x6.txt
47d46564ca13af9e9d51edaa70bd45883c724eaafb237efcbf1bc8bb516069a5  research/wording-check-e2-hpick8/prompts/aggregator-6x1.txt
38c9e2ab25d9e20318fb74fe75f0f40dca25c2e5a49e2e97ea3ce6774127f1f6  research/wording-check-e2-hpick8/prompts/helper-1x6-1.txt
55a97676faa5feeed34fb5efc9d48ef04a32eaa9a87fd79255939304f8a88447  research/wording-check-e2-hpick8/prompts/helper-1x6-2.txt
793768c10281fb992e151eebc84f036a6aa98e0dfc802cfa93cad75f89a88ef8  research/wording-check-e2-hpick8/prompts/helper-1x6-3.txt
4e9fd902f44390d6aac4d93be30b0a589b7d76befc888868a4ca9769adf0f205  research/wording-check-e2-hpick8/prompts/helper-1x6-4.txt
cfa38f995b16ae103149a9ec23aa09a953893eea30d7783caa8593534a9b0e20  research/wording-check-e2-hpick8/prompts/helper-1x6-5.txt
84bb69480ca2144a303f4ca077d0f8b9118d509e569fb3dde4f672e955121ed8  research/wording-check-e2-hpick8/prompts/helper-1x6-6.txt
1d796a971475f2bc486ca45d0f1fc003848bd573da93e2da1bd3b97f118c43a9  research/wording-check-e2-hpick8/prompts/helper-6x1-1.txt
45bd43668b81e1f9c3f26bbce6e523a7957d66d4b21b512e1fa395d01f8a14c0  research/wording-check-e2-hpick8/prompts/helper-6x1-2.txt
8d08e7f35023cbf8d3b8916dddebc5a0823fbb63784834b84a9c7b0a0c7347cc  research/wording-check-e2-hpick8/prompts/helper-6x1-3.txt
69d8e72d25c3e555398744dd32b9eb6285ec989a5c069fcf3105891ca2f225f9  research/wording-check-e2-hpick8/prompts/helper-6x1-4.txt
d96fea299e8a247372697e5df9e0cf8795f091b4045d3fd5fe8ccc210beacb56  research/wording-check-e2-hpick8/prompts/helper-6x1-5.txt
9db771195d579c6f333ef534205e034f7ab524c008d0f77b19ef402a19f19a61  research/wording-check-e2-hpick8/prompts/helper-6x1-6.txt
e9a07c261573089dd0851fe033693c798ef0a16b150745799b4168c2303f8867  research/wording-check-e2-hpick8/prompts/picker-1x6.txt
042c93954e75b742690d197f4040861515edc5379117571532afa514c6521c04  research/wording-check-e2-hpick8/prompts/picker-6x1.txt
de6610e56567b8fd29138d5491991979fb2eb7619749dd28b55ae8ae9db3c54a  research/wording-check-e2-hpick8/prompts/planner-1x6.txt
e75c1e6c96051716e7fd8fdfcdd82bba7f17e50122b97124f617cb1fd8fa6ec3  research/wording-check-e2-hpick8/prompts/planner-6x1.txt
2972a2967df060feb5acad747ce7acac4896bbcb5f1ab67d0a510dffbbc73de1  research/wording-check-e2-hpick8/replies/aggregator-1x6.txt
138faf4a316628cb10140df57b5bed87beea4b27aa4da9bb5b8f2da51a4043e1  research/wording-check-e2-hpick8/replies/aggregator-6x1.txt
0a0916a8224308829e3d80bb38d7b0bd16d1ca735bcc97416576288498e56f4c  research/wording-check-e2-hpick8/replies/helper-1x6-1.txt
c5001a9843805d98c8b9a3d5a5ad7f4e7c128f48f81571d9167a2e90efc787e4  research/wording-check-e2-hpick8/replies/helper-1x6-2.txt
887997100f59172db9ad5afad627e53dde1c9850e0b43f26236568b41838bfe1  research/wording-check-e2-hpick8/replies/helper-1x6-3.txt
1d53a93f3c9153c1eafc7a799a959c8a0ecbb5953d3d2aca985c7a40a37165ba  research/wording-check-e2-hpick8/replies/helper-1x6-4.txt
7c094d80c98dee4e13f89f19d3a8c01d2da5787a17045a9c5d6163f1ca175514  research/wording-check-e2-hpick8/replies/helper-1x6-5.txt
591858f3830d1586660323690fe7b8c7903cc0a056ddc3f6d96ac067b77225fa  research/wording-check-e2-hpick8/replies/helper-1x6-6.txt
ec58759f31127d19224645f506b10d94c3423d0c5475386f72c55a597d3a1c3e  research/wording-check-e2-hpick8/replies/helper-6x1-1.txt
99d31ff5b3d335d90d6c389dc02ac4588b5e33e2f79ace4b0c4cbf9d35fbaba4  research/wording-check-e2-hpick8/replies/helper-6x1-2.txt
a23b31209a5be312543d93ef6c0436fa6f7bfbd03a8297f4a7f358d7698aa1b6  research/wording-check-e2-hpick8/replies/helper-6x1-3.txt
4bc3f313abdaf36f9c8a3ada3f69a6a9c2e623f42d4eb31f3c4c1216541dbf51  research/wording-check-e2-hpick8/replies/helper-6x1-4.txt
a48b701eb3f28a5e00c18e1bf4ca465a6c3e01b465ed7460a5056531d6f4a7b1  research/wording-check-e2-hpick8/replies/helper-6x1-5.txt
0e03df90e90606ad4049ab24e75139fac2c83f1bd06b60856170cc6e36dd1b90  research/wording-check-e2-hpick8/replies/helper-6x1-6.txt
514fff6657fae9a0aaa96642e24f8e8d5001489ffbe31a380c68c67fd97961b9  research/wording-check-e2-hpick8/replies/picker-1x6.txt
02fc8ae6b12eb6fdf732257a2f7153fa8d63c0f4bae8d8e24a4f586cb6a9ba26  research/wording-check-e2-hpick8/replies/picker-6x1.txt
8b38c502f53e0b279cf66230384377b4e3494a9419aa16dc2659936afbfd129b  research/wording-check-e2-hpick8/replies/planner-1x6.txt
9e57c0266709b7ff391b1c4e58b5a4015676f3341522a74d773fb016157724ac  research/wording-check-e2-hpick8/replies/planner-6x1.txt
48eedd019ba18e401a064cfd09b49c7ba1ef4b9dedc3aafcd9e9a89d4b538298  research/wording-check-e2-hpick8/rows.json
5f0628855550811af42eb0c74ee6db4d3fe8bc05e9dd4a19e2624d49e8be6d44  studies/1-real-price/brief.md
40fe871f23da457b88dbe7f8b0e6dca801c8713145782d8b05250b4b185dedea  studies/1-real-price/log.md
0ab437934a8df843db20ff9eb4aa57dd6e8228605f38df4b77e138d942e6c169  studies/1-real-price/spec.md
e688f3bc7e4721381c94bb39cf45350b20696aa81a3045397bd3aa3b275c890a  studies/5-cheap-judges/brief.md
8111db070afc2ec64ee8dfb78d9698c07d500fbcbf94e2901019b60c06c80eb1  studies/5-cheap-judges/log.md
9f6f4ab0a8ecd70a0e6410ae4d9edf2e30757eb14e2ff8a20c34d641df043bfd  studies/5-cheap-judges/spec.md
53637d566b775de74c4a50347358291e69a8c9043ec00934d15a7ae60ac8be40  the-ask.md
```
Files: 1363. SHA-256 of the lines above (each followed by a newline): 5b146e324ac9ad85420421ab009da95f7817da86ec3d4230004150c798e8fdaf
<!-- FILE-HASHES-END -->
