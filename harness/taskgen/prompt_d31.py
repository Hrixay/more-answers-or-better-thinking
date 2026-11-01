"""The plain-worded prompt endings and reply parsers drafted for ruling D-31 (spec item 4).

D-31: one frozen, plain-worded prompt for every model. The reply lists only the value after each step, then a
numbered final answer line. No "show your reasoning" or step-by-step wording, and no words about tests or grading.

Everything here is DRAFT wording until Edith has cleared it and the user has said yes to the exact text. The same
text is used for both families; only the nouns differ ("value / rule" for the digit puzzles, "list / function" for
code tracing). Existing prompts (`style="legacy"`) are unchanged.

Reply format:
- one line per step, `S.K = value`: S is the sequence, K is the place of the rule or function in it
  (omitted when every sequence is a single step: the answer line is then the same information);
- a last line `Answer: 1 = value, 2 = value, ...`, one entry per sequence, in order.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

NOUNS = {
    "digits": {"value": "the value", "unit": "rule", "units": "rules", "start": "value"},
    "code": {"value": "the list", "unit": "function", "units": "functions", "start": "list"},
    "ledger": {"value": "the balances", "unit": "rule", "units": "rules", "start": "balances"},
}

# The words the prompt must never contain (shared with the generators' self-tests). Word-start match.
BANNED = (r"\b(grad|test|evaluat|scor|reasoning|reason|think|correct|cipher|encrypt|password|check|benchmark|judg|"
          r"mark|exam|quiz|step by step|step-by-step)")


def variant_intro(n_digits: int, example: str) -> str:
    """The opening paragraph of the D-42 prompt-variant (digits only): the same meaning as the D-31 opening, other words."""
    return (f"Each value is written with exactly {n_digits} digits, such as {example}, and leading "
            f"zeros are part of the value. A rule that does arithmetic treats the value as an ordinary number "
            f"({example} is {int(example)}), and its result is written back with {n_digits} digits.")


def variant_closing(width: int, depth: int) -> str:
    """The last paragraph of the D-42 prompt-variant (digits only). Same reply format as `closing`: the step lines
    `S.K = v` and the numbered `Answer:` line are untouched, so every parser and grader works on both wordings."""
    if depth == 1:
        return (f"Every sequence is a single rule applied to its start value, and the sequences have nothing to do with "
                f"each other. Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, containing the value each "
                f"sequence ends on, in order.")
    if width == 1:
        return ("Go through the rules of sequence 1 in the order listed, giving each rule the value that the previous rule "
                "produced. After each rule, write the value it produced on its own line, as `1.1 = v`, `1.2 = v` and so on "
                "(the first number is the sequence; the second is the rule's place in it). Finish with a single line, "
                "`Answer: 1 = v`, containing the value the sequence ends on.")
    raise ValueError("the prompt variant is defined for the two study shapes only (24x1 and 1x24)")


def closing(kind: str, width: int, depth: int, answer_only: bool = False) -> str:
    """The last paragraph of the prompt, after the sequences."""
    n = NOUNS[kind]
    value, unit, units = n["value"], n["unit"], n["units"]
    if answer_only:
        # Pre-set fallback (D-31 layer 2): the same puzzle, but the reply is only the final line.
        if width == 1 and kind == "ledger":
            return (f"Apply the {units} of sequence 1 in the order listed, each to {value} the {unit} before it gave. "
                    f"Reply with one line, `Answer: 1 = v`, where v is {value} the sequence ends at.")
        if width == 1:
            return (f"Apply the {units} in the order listed, each to {value} the {unit} before it gave. "
                    f"Reply with one line, `Answer: 1 = v`, where v is {value} the sequence ends at.")
        if depth == 1:
            return (f"Each sequence is one {unit} applied to its start {n['start']}, and the sequences are "
                    f"separate. Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, giving "
                    f"{value} each sequence ends at, in order.")
        return (f"Apply the {units} of each sequence in the order listed, each to {value} the {unit} before it "
                f"gave. Each sequence is separate. Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, "
                f"giving {value} each sequence ends at, in order.")
    if depth == 1:
        return (f"Each sequence is one {unit} applied to its start {n['start']}, and the sequences are separate. "
                f"Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, giving {value} each sequence "
                f"ends at, in order.")
    if width == 1:
        return (f"Apply the {units} of sequence 1 in the order listed, each to {value} the {unit} before it gave. "
                f"Reply with {value} after each {unit}, one per line, written `1.1 = v`, `1.2 = v`, and so on "
                f"(the first number is the sequence, the second is the {unit}'s place in it). "
                f"Then end with one line, `Answer: 1 = v`, giving {value} the sequence ends at.")
    return (f"Apply the {units} of each sequence in the order listed, each to {value} the {unit} before it gave. "
            f"Each sequence is separate. Reply with {value} after each {unit}, one per line, written `1.1 = v`, "
            f"`1.2 = v`, `2.1 = v`, and so on (the first number is the sequence, the second is the {unit}'s place "
            f"in it). Then end with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, giving {value} each "
            f"sequence ends at, in order.")


def step_call_prompt(kind: str, n_digits: int, rule_text: str, value: str, intro_text: str = "", house: bool = False) -> str:
    """The prompt for ONE step of the step-wise team (E3): one rule or function and one value, nothing else.

    `rule_text` is exactly the rule line (digits) or function source (code) as printed in the full puzzle.
    """
    if kind == "digits":
        example = "0472" if n_digits == 4 else "0" + "4729183"[: n_digits - 1]
        return (f"Every value here is a string of exactly {n_digits} digits, such as {example}. Leading zeros count. "
                f"When a rule does arithmetic, read the value as an ordinary number ({example} is {int(example)}) "
                f"and write the result back with {n_digits} digits.\n\n"
                f"Rule\n{rule_text}\n\nValue\n{value}\n\n"
                f"Apply the rule to the value. Reply with one line, `Answer: v`, where v is the new value.")
    if kind == "ledger":
        if house:
            return (f"{intro_text}\n\nRule\n{rule_text}\n\nBalances\n{value}\n\n"
                    f"Apply the rule to the balances, then the house rule. Reply with one line, `Answer: v`, where v is the new balances "
                    f"after the rule and the house rule.")
        return (f"{intro_text}\n\nRule\n{rule_text}\n\nBalances\n{value}\n\n"
                f"Apply the rule to the balances. Reply with one line, `Answer: v`, where v is the new balances.")
    return (f"Each function below takes a list of whole numbers and returns a new list. Read the function as "
            f"ordinary Python.\n\n{rule_text}\n\nList\n{value}\n\n"
            f"Apply the function to the list. Reply with one line, `Answer: v`, where v is the new list.")


# ---------------------------------------------------------------- parsers

_VAL = r"(\[[^\]]*\]|\d+)"
_ANSWER = re.compile(r"^[\s`*>\-]*answer\s*:\s*(.*)$", re.I)
_ENTRY = re.compile(r"(\d+)\s*=\s*" + _VAL)
_STEP = re.compile(r"^[\s`*>\-]*(\d+)\.(\d+)\s*=\s*" + _VAL + r"[\s`*]*$")


def _val(text: str):
    if text.startswith("["):
        return tuple(int(x) for x in re.findall(r"\d+", text))
    return text


def parse_answer(reply: str) -> Optional[Dict[int, object]]:
    """Entries of the LAST line that starts with `Answer:`, as {sequence number: value}; None if there is none.

    A repeated number keeps its last value. Digit values stay strings (leading zeros count); code values are tuples.
    """
    found = None
    for ln in reply.strip().splitlines():
        m = _ANSWER.match(ln)
        if m:
            found = m.group(1)
    if found is None:
        return None
    out: Dict[int, object] = {}
    for m in _ENTRY.finditer(found):
        out[int(m.group(1))] = _val(m.group(2))
    return out


def parse_steps(reply: str) -> Dict[Tuple[int, int], object]:
    """Step lines `S.K = value` as {(S, K): value}; a repeated (S, K) keeps its last value."""
    out: Dict[Tuple[int, int], object] = {}
    for ln in reply.splitlines():
        m = _STEP.match(ln)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = _val(m.group(3))
    return out


def score_answer(reply: str, answer: List[object]) -> Dict[str, object]:
    """Whole-answer and per-piece scoring of the answer line (both are reported, D-23).

    A missing or extra entry makes the whole answer wrong; per-piece credit is given entry by entry, matched by
    the printed number (so a dropped value does not shift the others).
    """
    got = parse_answer(reply)
    n = len(answer)
    if got is None:
        return {"parsed": False, "all_correct": False, "pieces_right": 0, "pieces": n, "length_ok": False}
    right = sum(1 for i, a in enumerate(answer, 1) if got.get(i) == a)
    length_ok = sorted(got) == list(range(1, n + 1))
    return {"parsed": True, "all_correct": length_ok and right == n, "pieces_right": right, "pieces": n,
            "length_ok": length_ok}


def numbering_problems(reply: str, width: int, depth: int) -> List[str]:
    """Step lines whose numbers cannot belong to the puzzle (sequence outside 1..width, or place outside 1..depth,
    for example a reply that starts at `1.0` or runs on to `1.25`). A reply with any of these is flagged: the
    first-wrong-step reading is unreliable for it (every later line would seem to differ)."""
    return [f"{s}.{k}" for (s, k) in parse_steps(reply) if not (1 <= s <= width and 1 <= k <= depth)]


def first_wrong_step(reply: str, states: List[object], sequence: int = 1, width: int = 1) -> Optional[int]:
    """The first place K where the printed `S.K = value` line differs from the true state; None if every printed
    line agrees.

    Missing lines are skipped: only printed lines are compared (a reply that leaves out a line shows no slip at
    that place; the answer line still scores the final value). If the step numbering is off (`numbering_problems`),
    this returns None and the caller must flag the reply instead of placing a slip.
    """
    if numbering_problems(reply, width, len(states)):
        return None
    steps = parse_steps(reply)
    for k, true in enumerate(states, 1):
        if (sequence, k) in steps and steps[(sequence, k)] != true:
            return k
    return None
