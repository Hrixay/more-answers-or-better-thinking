# Reproduction details (illustrative, not from any test set)

Every kind of prompt the runs sent, made by the run code itself on the paper's illustrative puzzle (`../illustration/`, made fresh and never from any test set), with the request each arm sent. Built by `python3 -m harness.analysis.reproduction`.

- `prompts/`: the rewording check's variant (both shapes), step voting (each chain step, Test 4; each piece, the top-up's C13), and the team prompts (planner, helper, aggregator, picker; both shapes). The chain and pieces prompts are in `../illustration/`.
- `prompts.json`: for each prompt, its kind, run, arm tag and the request as built (model, effort, thinking, max_tokens), with the prompt shown as a pointer to its file. Placeholders mark what only a model could supply (the planner's instruction in the helper prompt, the eight replies in the picker prompt); the aggregator is shown with a correct helper's results.
- `arms.json`: every arm's settings in the length sweep, Study 1 (the main run), Study 1b and the top-up run, each with its request as built. Covered: the length sweep, Study 1 (the main run), Study 1b and the top-up run. Not covered: Pilot 1 (its 24-step markers are reported as exploratory), the Haiku effort diagnostic (exploratory; its counts are in Appendix A), and the earlier setup and smoke checks.
- `prices.json`: the pinned per-million-token price table, the long-prompt rule and the Batch discount.
- `parsers.json`: where replies are read, with each function's docstring or pattern.
- `sources.json`: SHA-256 of every code and plan file read; `SHA256SUMS`: SHA-256 of every file here.
