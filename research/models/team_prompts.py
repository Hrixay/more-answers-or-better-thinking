"""DRAFT prompts for the two extras that need new wording: E2 (a stateless Haiku planner, Haiku helpers, one aggregator)
and H-pick8 (a Haiku picker over 8 Haiku-medium samples). Karen, for Edith; nothing here calls a model.

Every call is a single, fresh message (stateless, so no thinking carries over: spec section 3, E2 detail). The puzzle text
each call quotes is the APPROVED prompt (D-77) with only its closing paragraph replaced; the new closings below are the
only new wording. Reply formats the scripts parse: `Task k:` (planner), `Answer: v` (helper, as E3), the approved step
lines and `Answer:` line (aggregator, so it is graded like any other arm), `Pick: k` (picker).

Run: python3 research/models/team_prompts.py   renders every prompt for main-set puzzle 000 (both shapes) into
research/team-prompts/ and runs the banned-word scan (prompt_d31.BANNED, case-insensitive) and the no-`$` rule on the
new wording. Exit 1 on any failure.
"""
import json, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, ROOT)
from harness.taskgen import ledger, prompt_d31  # noqa: E402

# A task label: `Task k` after optional markup (`#` headings, bold, bullets, quotes), then either nothing (the text
# follows on the next lines) or one separator `:` `.` `-` (or an en or em dash) and the text (Edith R1-1).
TASK = re.compile(r'^[\s#*_`>\-]*task\s+(\d+)[\s*_`]*(?:$|[:.\-\u2013\u2014][\s*_`]*(.*)$)', re.I)
# `Pick: k`, optionally `Pick: Reply k`, with markup and one trailing `.` or `,` allowed (Edith R1-2).
PICK = re.compile(r'^[\s#*_`>\-]*pick\s*:[\s*_`]*(?:reply\s+)?(\d+)[\s*_`]*[.,]?[\s*_`]*$', re.I)


def _puzzle_without_closing(item):
    """The approved prompt up to and including the Sequences block (its closing paragraph removed)."""
    return item['prompt'].rsplit('\n\n', 1)[0]


# ---------------------------------------------------------------- E2: planner, helpers, aggregator

def planner_closing(width, depth):
    if width == 1:
        return (f"Do not apply the rules yourself. A helper will apply the rules of sequence 1 one at a time. For each "
                f"rule, the helper sees only your instruction for that rule and the balances it starts from; it does not "
                f"see this text. Write one instruction for each rule, in the order the sequence lists them. Each "
                f"instruction must give the helper everything it needs: what a value means, the full rule, how ties are "
                f"settled and the house rule. Start the instructions `Task 1:`, `Task 2:`, and so on up to `Task {depth}:`, "
                f"one paragraph each, and write nothing else.")
    return (f"Do not apply the rules yourself. A helper will handle each sequence on its own. For each sequence, the "
            f"helper sees only your instruction for it and that sequence's start balances; it does not see this text. "
            f"Write one instruction for each sequence, in order. Each instruction must give the helper everything it "
            f"needs: what a value means, the full rule, how ties are settled and the house rule. Start the "
            f"instructions `Task 1:`, `Task 2:`, and so on up to `Task {width}:`, one paragraph each, and write nothing "
            f"else.")


def planner_prompt(item):
    return _puzzle_without_closing(item) + '\n\n' + planner_closing(int(item['width']), int(item['depth']))


def parse_plan(reply, n):
    """The n task texts, or None if the plan does not have exactly tasks 1..n (then E2 fails on that puzzle)."""
    tasks, cur = {}, None
    for ln in reply.splitlines():
        m = TASK.match(ln)
        if m:
            cur = int(m.group(1))
            if cur in tasks:
                return None
            tasks[cur] = [(m.group(2) or '').strip()]
        elif cur is not None and ln.strip():
            tasks[cur].append(ln.strip())
    if sorted(tasks) != list(range(1, n + 1)):
        return None
    out = [' '.join(t for t in tasks[k] if t).strip() for k in range(1, n + 1)]
    return None if any(not t for t in out) else out          # an empty task is no instruction: the plan fails


HELPER_CLOSING = ("Follow the instruction above for these balances. Reply with one line, `Answer: v`, where v is the new "
                  "balances.")


def helper_prompt(task_text, balances):
    """One helper call: the planner's instruction, the balances, a fixed closing (the E3 reply form)."""
    return f"{task_text}\n\nBalances\n{ledger.fmt(balances)}\n\n{HELPER_CLOSING}"


def aggregator_closing(item, results):
    """`results`: one entry per task, the helpers' agreed balances or None. The approved closing ends the prompt."""
    width, depth = int(item['width']), int(item['depth'])
    seq = item['chains'][0]['names'] if width == 1 else [c['names'][0] for c in item['chains']]
    show = lambda r: ledger.fmt(r) if r is not None else '(no result)'
    if width == 1:
        lines = '\n'.join(f'Place {k}, rule {lab}: {show(r)}' for k, (lab, r) in enumerate(zip(seq, results), 1))
        head = ("Helpers have applied the rules of sequence 1 one at a time, each starting from the result before it. "
                "Their results, after each rule and its house rule, in order:")
        tail = ("Use these results to write your reply. Where a result looks wrong to you, work that rule out again "
                "yourself and carry your own balances forward from there.")
    else:
        lines = '\n'.join(f'Sequence {k}, rule {lab}: {show(r)}' for k, (lab, r) in enumerate(zip(seq, results), 1))
        head = "Helpers have applied each sequence's rule, then the house rule, to its start balances. Their results:"
        tail = "Use these results to write your reply. Where a result looks wrong to you, work that sequence out again yourself."
    return f"{head}\n{lines}\n\n{tail} {ledger.closing_house(width, depth)}"


def aggregator_prompt(item, results):
    return _puzzle_without_closing(item) + '\n\n' + aggregator_closing(item, results)


# ---------------------------------------------------------------- H-pick8

def picker_prompt(item, replies):
    """`replies`: the visible text of Haiku-medium samples 1..8 of this puzzle, in sample order (None: no reply)."""
    assert len(replies) == 8
    shown = '\n\n'.join(f'Reply {i}\n' + (r.strip() if r and r.strip() else '(no reply)') for i, r in enumerate(replies, 1))
    return (_puzzle_without_closing(item) + '\n\n' + "Here are 8 replies to the puzzle above, written separately.\n\n"
            + shown + '\n\n' + "Choose the reply whose balances are right. Reply with one line, `Pick: k`, where k is "
            "the number of the reply you choose.")


def parse_pick(reply):
    """The chosen reply number 1..8 from the LAST `Pick:` line, or None (then the picker gives no answer)."""
    found = None
    for ln in reply.splitlines():
        m = PICK.match(ln)
        if m and 1 <= int(m.group(1)) <= 8:
            found = int(m.group(1))
    return found


# ---------------------------------------------------------------- render and check

NEW_WORDING = [planner_closing(1, 6), planner_closing(6, 1), HELPER_CLOSING,
               "Helpers have applied the rules of sequence 1 one at a time, each starting from the result before it. "
               "Their results, after each rule and its house rule, in order:",
               "Use these results to write your reply. Where a result looks wrong to you, work that rule out again yourself "
               "and carry your own balances forward from there.",
               "Helpers have applied each sequence's rule, then the house rule, to its start balances. Their results:",
               "Use these results to write your reply. Where a result looks wrong to you, work that sequence out again yourself.",
               "Here are 8 replies to the puzzle above, written separately.",
               "Choose the reply whose balances are right. Reply with one line, `Pick: k`, where k is the number of the reply "
               "you choose.", "Place 1, rule E:", "Sequence 1, rule E:", "(no result)", "(no reply)"]


def main():
    items = [json.loads(l) for l in open(os.path.join(ROOT, 'data', 'tasks', 'main-ledger-l14n6-v1', 'items.jsonl'))]
    banned = re.compile(prompt_d31.BANNED, re.I)
    fails = [f'banned word {m.group(0)!r} in: {t[:60]}...' for t in NEW_WORDING for m in banned.finditer(t)]
    fails += [f"'$' in: {t[:60]}" for t in NEW_WORDING if '$' in t]
    out = os.path.join(ROOT, 'research', 'team-prompts')
    os.makedirs(out, exist_ok=True)
    for it in items[:2]:
        shape = it['id'].rsplit('-', 1)[1]
        n = int(it['depth']) if int(it['width']) == 1 else int(it['width'])
        states = it['chains'][0]['states'] if int(it['width']) == 1 else [c['states'][0] for c in it['chains']]
        # stand-ins: a plan the parser must accept, helpers giving the key's balances (only to show the layout)
        plan = '\n'.join(f'Task {k}: (the planner\'s instruction for {"rule" if n == int(it["depth"]) else "sequence"} {k})'
                         for k in range(1, n + 1))
        tasks = parse_plan(plan, n)
        if tasks is None or parse_plan(plan.replace(f'Task {n}:', 'Task 99:'), n) is not None:
            fails.append(f'{shape}: parse_plan')
        before = it['chains'][0]['start'] if int(it['width']) == 1 else it['chains'][0]['start']
        docs = {'planner': planner_prompt(it), 'helper-1': helper_prompt(tasks[0], before),
                'aggregator': aggregator_prompt(it, [list(s) for s in states]),
                'picker': picker_prompt(it, [f'(Haiku-medium sample {i}, its visible text as returned)' for i in range(1, 9)])}
        for name, txt in docs.items():
            with open(os.path.join(out, f'{it["id"]}-e2-{name}.txt' if name != 'picker' else
                                   os.path.join(out, f'{it["id"]}-h-pick8.txt')), 'w') as fh:
                fh.write(txt + '\n')
        if parse_pick('I compared them.\nPick: 3') != 3 or parse_pick('Pick: 9') is not None or parse_pick('**Pick:** 2') != 2:
            fails.append('parse_pick')
    print(f'new wording: {len(NEW_WORDING)} pieces, {"no banned word, no $" if not fails else "FAILURES"}; '
          f'rendered E2 planner/helper/aggregator and H-pick8 for puzzle 000 at both shapes into research/team-prompts/')
    for f in fails:
        print('  FAIL', f)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
