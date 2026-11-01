"""Write the teaching examples to data/examples/.

    python3 -m harness.taskgen.make_examples

Deterministic: running it twice gives identical files.
"""

from __future__ import annotations

import json
from pathlib import Path

import statistics

from .puzzle import PRESETS, STRUCTURE_LEVELS, Params, Puzzle, generate, render_solution
from .rng import derive_seed

OUT = Path(__file__).resolve().parents[2] / "data" / "examples"

LEVEL_NAMES = {
    (24, 1): "fully parallel: 24 separate one-step sequences",
    (6, 4): "6 sequences of 4 steps",
    (2, 12): "2 sequences of 12 steps",
    (1, 24): "fully sequential: 1 sequence of 24 steps",
}

HEADER = (
    "*Prototype example from `harness/taskgen/` ({gen}). For teaching only: nothing about the task "
    "family is decided. Regenerate with `python3 -m harness.taskgen.make_examples`.*\n"
)


def _block(p: Puzzle, title: str) -> str:
    return "\n".join([
        f"## {title}",
        "",
        f"`id: {p.id}` · `seed: {p.seed}` · prompt {len(p.prompt)} characters · "
        f"answer line {len(p.answer_line)} characters",
        "",
        "### What the model sees",
        "",
        "```text",
        p.prompt,
        "```",
        "",
        "### Answer",
        "",
        "```text",
        p.answer_line,
        "```",
        "",
        "### Full solution trace",
        "",
        "```text",
        render_solution(p),
        "```",
        "",
    ])


def write_levels() -> list:
    records = []
    seeds = [derive_seed("pareto-examples-v0", k) for k in (1, 2)]
    for w, d in STRUCTURE_LEVELS:
        parts = [f"# Structure level {w}×{d}: {LEVEL_NAMES[(w, d)]}", "", HEADER.format(gen=generate(seeds[0], w, d).generator)]
        parts.append(
            "Examples 1 and 2 use the same two seeds at every level, so each has the same rules and the same "
            "24 rule applications in the same order as its namesake in the other level files. Only the wiring "
            "(how the 24 steps are cut into sequences) and the start values differ.\n"
        )
        for k, seed in enumerate(seeds, 1):
            p = generate(seed, w, d, item_id=f"example{k}-{w}x{d}")
            records.append(p.to_dict())
            parts.append(_block(p, f"Example {k}"))
        (OUT / f"level-{w}x{d}.md").write_text("\n".join(parts))
    return records


def write_demo() -> list:
    params = Params(total_steps=4, n_affine=1, n_table=1, n_shuffle=1)
    seed = derive_seed("pareto-demo-v0")
    par = generate(seed, 4, 1, params, item_id="demo-4x1")
    seq = generate(seed, 1, 4, params, item_id="demo-1x4")
    text = "\n".join([
        "# Four-step demo: the same puzzle, wired two ways",
        "",
        HEADER.format(gen=par.generator),
        "A tiny version of the real thing: 4 sub-steps instead of 24, and 3 rules (one of each kind) instead "
        "of 12. Both versions below have the **same rules** and apply them in the **same order** "
        f"({', '.join(r for ch in par.chains for r in ch.rules)}). The only difference is the wiring.",
        "",
        "- **4×1 (parallel):** four separate one-step jobs. Each starts from its own given value, so the steps "
        "can be done in any order, by four different workers at once. A slip ruins only one of the four values.",
        "- **1×4 (sequential):** one job of four steps. Each step starts from the previous step's result, so the "
        "steps must be done in order. A slip at step 1 carries through to the end.",
        "",
        "Either way, the whole answer is right only if all four steps are done right.",
        "",
        _block(par, "Version A: 4×1, fully parallel"),
        _block(seq, "Version B: 1×4, fully sequential"),
    ])
    (OUT / "demo-4step.md").write_text(text)
    return [par.to_dict(), seq.to_dict()]


PRESET_NOTES = {
    "d0": "The prototype's original setting (4-digit values, 2-digit multipliers).",
    "d1": "Wider values and bigger numbers; the same 12 rules.",
    "d2": "Adds four 100-entry pair tables (16 rules).",
    "d3": "8-digit values, 4-digit multipliers, 5 rules of each kind (20 rules).",
    "d4": "As d3 with 6 rules of each kind: 24 rules, each used exactly once.",
    "d4s": "Candidate under D-25, untried on any model: d4 with smaller maths (3-digit multipliers, "
           "5-6 digit addends); the mix stays 6 of each kind.",
    "d4p": "Candidate under D-25, untried on any model: d4s's small maths, but only 4 arithmetic rules "
           "and 4 digit tables, with 8 pair tables and 8 shuffles in their place (24 rules, each used once).",
}


def _preset_stats(params: Params, n_seeds: int = 30) -> dict:
    """Mean prompt lengths (characters) per level, measured on n_seeds fixed seeds."""
    out = {"rulebook": [], "trace": []}
    for w, d in STRUCTURE_LEVELS:
        ps = [generate(derive_seed("preset-stats", k), w, d, params) for k in range(n_seeds)]
        out[(w, d)] = statistics.mean(len(p.prompt) for p in ps)
        out["answer", (w, d)] = statistics.mean(len(p.answer_line) for p in ps)
        out["rulebook"].append(statistics.mean(len(p.prompt.split("\nSequences")[0]) for p in ps))
        out["trace"].append(statistics.mean(sum(len(s.work) for c in p.chains for s in c.steps) for p in ps))
    out["rulebook"] = statistics.mean(out["rulebook"])
    out["trace"] = statistics.mean(out["trace"])
    return out


def write_presets() -> list:
    seed = derive_seed("pareto-examples-v0", 1)
    records, rows, stats = [], [], {}
    for name, pr in PRESETS.items():
        stats[name] = _preset_stats(pr)
        p = generate(seed, 6, 4, pr, item_id=f"preset-{name}-6x4")
        records.append(p.to_dict())
        st = stats[name]
        text = "\n".join([
            f"# Difficulty preset {name}",
            "",
            HEADER.format(gen=p.generator),
            f"{PRESET_NOTES[name]}",
            "",
            f"- **Settings:** `{pr}`",
            f"- **Rules printed:** {pr.n_rules()} ({pr.n_affine} arithmetic, {pr.n_table} digit tables, "
            f"{pr.n_pair} pair tables, {pr.n_shuffle} shuffles); **steps:** {pr.total_steps}",
            f"- **Prompt length, 24×1 / 6×4 / 2×12 / 1×24 (mean characters over 30 seeds):** "
            + " / ".join(f"{st[lv]:,.0f}" for lv in STRUCTURE_LEVELS),
            "",
            "One example at 6×4 (the other wirings of the same seed have the same rules in the same order):",
            "",
            _block(p, "Example (6×4)"),
        ])
        (OUT / f"preset-{name}.md").write_text(text)
        rows.append(
            f"| {name} | {pr.n_digits} | {pr.mult_min}–{pr.mult_max} | {pr.add_min:,}–{pr.add_max:,} | "
            f"{pr.n_affine}/{pr.n_table}/{pr.n_pair}/{pr.n_shuffle} | {st['rulebook']:,.0f} | "
            + " | ".join(f"{st[lv]:,.0f}" for lv in STRUCTURE_LEVELS) + " | "
            + f"{st['answer', (24, 1)]:,.0f} / {st['answer', (1, 24)]:,.0f} |")
    (OUT / "presets.md").write_text("\n".join([
        "# Difficulty presets d0–d4, and the D-25 candidates d4s and d4p",
        "",
        HEADER.format(gen=generate(seed, 1, 24).generator),
        "Every preset has **24 steps** in the same four wirings. Only the per-step dials change: digits per "
        "value, multiplier and addend size, how many rules of each kind are printed, and whether 100-entry "
        "pair tables are used. Each preset's example is in `preset-<name>.md`. Lengths are mean characters "
        "over 30 fixed seeds, not tokens.",
        "",
        "| Preset | Digits | Multiplier | Addend | Rules (arith/table/pair/shuffle) | Rulebook chars | "
        "Prompt 24×1 | 6×4 | 2×12 | 1×24 | Answer line 24×1 / 1×24 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "The 24×1 prompt is longer than the 1×24 prompt by the 23 extra start values and sequence lines, and "
        "its final line lists 24 values instead of 1. Extra length of 24×1 over 1×24 (characters, and as a "
        "share of the 1×24 prompt): "
        + "; ".join(f"{n}: {stats[n][(24, 1)] - stats[n][(1, 24)]:,.0f} "
                    f"({(stats[n][(24, 1)] / stats[n][(1, 24)] - 1):.0%})" for n in PRESETS)
        + ". The share shrinks as the rulebook grows. See `harness/taskgen/README.md`, \"Difficulty dials\".",
        "",
    ]))
    return records


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = write_levels() + write_demo()
    preset_records = write_presets()
    for fname, recs in (("examples.jsonl", records), ("presets.jsonl", preset_records)):
        with (OUT / fname).open("w") as f:
            for r in recs:
                f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} + {len(preset_records)} puzzles to {OUT}")


if __name__ == "__main__":
    main()
