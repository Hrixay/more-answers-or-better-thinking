"""The D-42 (a) prompt variant for the ledger family (D-91: the wording in `research/d42-ledger-variant.md`, Karen, Edith-cleared, approved
by the user). It renders the variant of a FROZEN item: only the opening paragraph (which holds the house rule) and the closing paragraph
are reworded; the Rules and Sequences blocks, the headings and the reply format are byte-identical, so the same parser and grader score
both wordings.

The text is Karen's renderer (`research/models/d42_variant.py`) copied exactly, so the runner does not import research code; a test
renders every item of the main set with both and requires them to be equal. It lives here and not in `harness/taskgen` on purpose: the
generator is fixed by prereg-lock-3, and every frozen set's manifest pins a hash of all of `harness/taskgen` (`freeze.sources_sha256`),
so a new file there would change the locked generator. Nothing here generates a puzzle; it re-words a frozen one.
"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping, Tuple

from ..taskgen import ledger


def _order(names):
    return ', '.join(names[:-1]) + ' and ' + names[-1]


def variant_intro(names, example, t, a):
    """The opening paragraph, reworded. Same facts, in the same order as the approved one."""
    meaning = ', '.join(f'{n} {v}' for n, v in list(zip(names, example))[:-1]) + f' and {names[-1]} {example[-1]}'
    return (f"Each value is a list of the balances of {len(names)} budget lines, in whole units, always in this order: "
            f"{_order(names)}. For instance, {ledger.fmt(example)} means {meaning}. No balance can drop below 0. "
            f"The rules below describe how the balances change. If a rule picks the line with the largest or the smallest "
            f"balance and several lines share that balance, the rule picks whichever of them is listed first in the order above. "
            f"House rule: immediately after each rule, within the same step, look at the line with the smallest balance; if it "
            f"is below {t}, it receives {a} units from the line with the largest balance, or the largest line's whole "
            f"balance if that is less than {a}. The house rule runs no more than once per step, always after that step's rule, and is not applied "
            f"again to its own outcome. If one line is both the largest and the smallest, nothing moves. Each step's balances, "
            f"as you write them, are the balances after the house rule.")


def variant_closing(width, depth):
    """The closing paragraph, reworded. The reply-format strings are copied exactly from the approved closing."""
    if width == 1:
        return ("Go through the rules of sequence 1 in the order listed, applying the house rule after each one. Each rule "
                "starts from the balances that the previous rule and its house rule produced. After each rule and its house "
                "rule, write the balances on their own line, as `1.1 = v`, `1.2 = v` and so on (the first number is the "
                "sequence; the second is the rule's place in it). Finish with a single line, `Answer: 1 = v`, containing the "
                "balances the sequence ends on.")
    if depth == 1:
        return (f"Every sequence is a single rule applied to its start balances and then the house rule, and the sequences "
                f"have nothing to do with each other. Reply with one line, `Answer: 1 = v, 2 = v, ..., {width} = v`, "
                f"containing the balances each sequence ends on, in order.")
    raise ValueError('the variant is defined for the two study shapes only')


def render(item: Mapping[str, object]) -> Tuple[str, str]:
    """(approved prompt rebuilt from the templates, variant prompt) for one frozen item; raises if the approved paragraphs do not rebuild."""
    p = str(item['prompt'])
    first, rest = p.split('\n\n', 1)
    body, last = rest.rsplit('\n\n', 1)
    names = item['line_names']
    example = [int(x) for x in re.search(r'A value looks like \[([^\]]*)\]', first).group(1).split(',')]  # type: ignore[union-attr]
    h = item['house']
    width, depth = int(item['width']), int(item['depth'])                                         # type: ignore[call-overload]
    if item.get('decoys'):
        raise ValueError(f"{item['id']}: the variant is defined for puzzles without decoy rules")
    approved_first = ledger.intro(ledger.LParams(lines=len(names), decoys=0), names, example, ledger.House(t=h['t'], a=h['a']))  # type: ignore[index, arg-type]
    approved_last = ledger.closing_house(width, depth)
    if approved_first != first:
        raise ValueError(f"{item['id']}: the approved opening did not rebuild")
    if approved_last != last:
        raise ValueError(f"{item['id']}: the approved closing did not rebuild")
    return p, '\n\n'.join([variant_intro(names, example, h['t'], h['a']), body, variant_closing(width, depth)])  # type: ignore[index]


def variant_prompt(item: Mapping[str, object]) -> str:
    return render(item)[1]


D42_BASES = range(20)          # D-91: base 000-019 of the main set, both shapes (40 puzzles)


def d42_items(items: List[Dict]) -> List[Dict]:
    """The 40 pinned puzzles of D-91, each with its variant prompt in place of the approved one (a copy; the frozen item is unchanged)."""
    out = []
    for it in sorted(items, key=lambda it: (it["base_index"], it["width"])):
        if int(it["base_index"]) in D42_BASES:
            out.append(dict(it, prompt=variant_prompt(it)))
    return out
