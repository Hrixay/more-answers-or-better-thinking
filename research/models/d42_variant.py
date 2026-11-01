"""The D-42 prompt variant for the ledger family (Karen, DRAFT for Edith; nothing here calls a model).

The same rule as the approved digit variant (D-52): only the opening paragraph (which holds the house rule) and the closing
paragraph are reworded. The Rules block, the Sequences block, the headings and the reply format (`1.1 = v` ... and the
`Answer:` line) are byte-identical, so the same parser and grader score both wordings and the frozen puzzles render either way.
Defined for the main set's form only: a house rule, no decoy rules, the two study shapes (1xN and Nx1).

Run: python3 research/models/d42_variant.py [SET_DIR]   (default data/tasks/main-ledger-l14n6-v1)
It rebuilds every approved prompt from the generator's own templates (to prove the parameters are read right), renders the
variant, checks that everything outside the two paragraphs is unchanged, and runs the banned-word scan (prompt_d31.BANNED)
and the no-`$` rule on every variant prompt. Exit 1 on any failure. Writes one rendered pair per shape to research/d42-variant/.
"""
import json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, ROOT)
from harness.taskgen import ledger, prompt_d31  # noqa: E402


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


def render(item):
    """(approved prompt rebuilt from the templates, variant prompt) for one frozen item."""
    p = item['prompt']
    first, rest = p.split('\n\n', 1)
    body, last = rest.rsplit('\n\n', 1)
    names = item['line_names']
    example = [int(x) for x in re.search(r'A value looks like \[([^\]]*)\]', first).group(1).split(',')]
    h = item['house']
    width, depth = int(item['width']), int(item['depth'])
    assert not item.get('decoys'), f"{item['id']}: the variant is defined for puzzles without decoy rules"
    approved_first = ledger.intro(ledger.LParams(lines=len(names), decoys=0), names, example, ledger.House(t=h['t'], a=h['a']))
    approved_last = ledger.closing_house(width, depth)
    assert approved_first == first, f"{item['id']}: the approved opening did not rebuild"
    assert approved_last == last, f"{item['id']}: the approved closing did not rebuild"
    return p, '\n\n'.join([variant_intro(names, example, h['t'], h['a']), body, variant_closing(width, depth)])


def main(set_dir):
    items = [json.loads(l) for l in open(os.path.join(set_dir, 'items.jsonl'))]
    banned = re.compile(prompt_d31.BANNED, re.I)
    fails, shown = [], set()
    for it in items:
        approved, variant = render(it)
        a_mid, v_mid = approved.split('\n\n', 1)[1].rsplit('\n\n', 1)[0], variant.split('\n\n', 1)[1].rsplit('\n\n', 1)[0]
        if a_mid != v_mid:
            fails.append(f"{it['id']}: the Rules/Sequences blocks differ")
        for m in banned.finditer(variant):
            fails.append(f"{it['id']}: banned word {m.group(0)!r} at {m.start()}")
        if '$' in variant:
            fails.append(f"{it['id']}: '$' in the variant")
        fmt = ['`1.1 = v`', '`Answer: 1 = v`'] if int(it['width']) == 1 else [f"`Answer: 1 = v, 2 = v, ..., {it['width']} = v`"]
        for f in fmt:
            if f not in variant or f not in approved:
                fails.append(f"{it['id']}: reply format {f} missing")
        shape = it['id'].rsplit('-', 1)[1]
        if shape not in shown:
            shown.add(shape)
            out = os.path.join(ROOT, 'research', 'd42-variant')
            os.makedirs(out, exist_ok=True)
            for tag, txt in (('approved', approved), ('variant', variant)):
                with open(os.path.join(out, f"{it['id']}-{tag}.txt"), 'w') as fh:
                    fh.write(txt + '\n')
    words = [len(render(it)[1].split()) - len(it['prompt'].split()) for it in items]
    print(f"{len(items)} prompts: {len(items) - len({f.split(':')[0] for f in fails})} pass"
          f" (opening and closing rebuilt exactly; middle byte-identical; no banned word; no '$'; reply format kept)."
          f" Variant length minus approved: {min(words)} to {max(words)} words.")
    for f in fails:
        print('  FAIL', f)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'tasks', 'main-ledger-l14n6-v1')))
