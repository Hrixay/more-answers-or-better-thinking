# Harness

*Friday's lane. No code yet: the code is written after Study 1's pre-registration items are ruled, and
goes in by pull request with Edith's review. This file is the plan and the non-negotiable rules.*

## Planned layout (a proposal; Friday may improve it)

```
harness/
  pareto/
    client.py       the one entry point for every model call (official `anthropic` Python SDK)
    prices.py       pinned price table (with the date it was checked) and cost-from-usage
    guard.py        spend guard: dry run by default, worst-case reservation, hard cap
    batch.py        Message Batches: submit, poll, collect; results keyed by custom_id, never by position
    tasks/          our own seeded task generators, in taskgen/ (Reasoning Gym has no modular, lookup or permutation step), frozen sets
    arms/           the setups: single call, vote, picker, orchestrator-worker
    grade.py        exact-match graders
    analysis/       paired bootstrap, mixed models, Pareto frontiers, offline re-pricing
  tests/
```

## Rules for every paid call (Edith checks these before the first paid run)

1. **Dry run by default.** Spending needs an explicit live flag and the user's "go" for that run.
2. **Reserve the worst case before sending.** Estimate input tokens × the input price, plus `max_tokens`
   × the output price. Refuse the call if spent + reserved would pass the run's cap or the global cap.
   The global cap is $200 minus everything in `ops/spend-log.md`.
3. **Log every call in full** to `data/raw/<run-id>/calls.jsonl`. Each line holds:
   - timestamp, exact model ID, effort, a hash of the request parameters, `custom_id`, batch or real-time
   - usage: input, output (thinking included), cache read and cache write
   - `stop_reason`, and the refusal category if there is one
   - the visible answer text, and latency

   Study 5 and the offline re-pricing both depend on this.
4. **Cost = usage × the pinned price table**, and that includes Haiku's 5× price step above 100K-token
   prompts. Check prices against the live pricing page before each paid run. Reconcile with the
   Anthropic Console after each run.
5. **Model settings:**
   - Always set `output_config.effort` explicitly, because the defaults differ by model.
   - Use adaptive thinking.
   - Never use `budget_tokens`, which is rejected on 5.5 models.
   - Never send `temperature`, `top_p` or `top_k` on any of the four models. Haiku 5.5 rejects them with a
     400 error, and the SDK raises a `TypeError` on Opus 5.5. Every sample is drawn at the default.
   - Never force a tool choice, on any model. `tool_choice` set to `any` or `tool` is rejected on Opus,
     Sonnet and Fable. Haiku accepts it, but a forced tool call skips thinking, so it would change the
     setup. Use structured outputs instead.
6. **No server-side fallbacks.** Never use them in experiment calls. Fallback is opt-in, so:
   - Never send the beta header `server-side-fallback-2026-07-01` or a `fallbacks` field, and never use
     the SDK's `BetaRefusalFallbackMiddleware`.
   - Assert that each reply's `model` field equals the model requested. A mismatch stops the run: with no fallbacks sent, it means
     something is badly wrong (SDK path, a beta header, a proxy), and more calls would contaminate the
     data. (The exact stop rule is a pre-registration item.)
   - Log refusals (`stop_reason: "refusal"` and `stop_details.category`), empty replies and truncations
     as failures. Count a refusal's cost too: the `bio`, `frontier_llm` and `reasoning_extraction`
     categories are billed.
7. **Batch API for single-shot setups** (50% off). Multi-turn setups run in real time. The headline cost
   is the list price either way.
8. **Read the `claude-api` skill before writing any API code.** The API changed a lot in 2026, and older
   patterns break.
9. **After every paid run,** Friday adds a row to `ops/spend-log.md`.
