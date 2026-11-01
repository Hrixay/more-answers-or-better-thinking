"""Parse fixtures at shorter chain lengths (Karen, OURS), for prereg-lock-2 (D-86: n in {4, 6, 8, 12, 16}).

The same parse rules as sim-main-v2 (D-76, plus round 2's label rule), re-rendered at n steps (n in 4, 6, 8, 12, 16):
  parse_cases_n{n}.jsonl.gz   1xn replies, parse_trace(reply, line_count, steps=n); lines 6, 8, 10, 12
  pieces_cases_n{n}.jsonl.gz  nx1 Answer lines, parse_pieces(reply, width=n, line_count=6)
The answer-only cases (final_cases) don't depend on n; reuse sim-main-v2/final_cases.jsonl.gz.
No API calls. Run: python3 research/models/sim_fixtures_n.py   (writes research/fixtures/sim-main-n/)
"""
import gzip, json, os
import numpy as np

from sim_fixtures_v2 import _fmt_state
from sim_fixtures import gz_writer

NS = (4, 6, 8, 12, 16)


def _trace(rng, lines, steps):
    return [[int(v) for v in rng.integers(100, 15000, size=lines)] for _ in range(steps)]


def _reply(states, answer, steps, *, label=lambda i: f'1.{i}', eq=' = ', style='brackets', sep=', ', zeros=False,
           order=None, between=None, nl='\n', answer_line=None, prefix='', suffix='', fence=False):
    order = order or list(range(1, steps + 1))
    out = [prefix] if prefix else []
    for j, i in enumerate(order):
        out.append(f'{label(i)}{eq}{_fmt_state(states[i - 1], style, sep, zeros)}')
        if between and j == max(0, steps // 2 - 1):
            out.append(between)
    if answer_line is None:
        answer_line = f'Answer: 1 = {_fmt_state(answer, style, sep, zeros)}'
    if answer_line:
        out.append(answer_line)
    if suffix:
        out.append(suffix)
    txt = nl.join(out)
    return f'```\n{txt}\n```' if fence else txt


# D-90 (Deviation 2): the official rule accepts identical repeated step lines. lock-2's rule ("strict", kept for the
# paper's original-rule sensitivity check) fails any repeat. Cases where the two rules differ carry expected_strict.
STRICT_DIFFERS = ('-duplicate-line', '-duplicate-line-markup', '-summary-repeat-all')


def add_strict(cases):
    for c in cases:
        if c['id'].endswith(STRICT_DIFFERS):
            c['expected_strict'] = dict(ok=False, reason='extra_line', states=None, answer=None)
    return cases


def parse_cases_n(n, seed):
    rng = np.random.default_rng(seed)
    cases = []
    for lines in (6, 8, 10, 12):
        T = _trace(rng, lines, n)
        A = T[-1]
        def ok(name, txt, states=T, ans=A):
            cases.append(dict(id=f'N{n}-L{lines}-{name}', steps=n, line_count=lines, reply=txt,
                              expected=dict(ok=True, reason=None, states=states, answer=ans)))
        def bad(name, txt, reason, extra=None):
            cases.append(dict(id=f'N{n}-L{lines}-{name}', steps=n, line_count=lines, reply=txt,
                              expected=dict(ok=False, reason=reason, states=None, answer=None, **(extra or {}))))
        R = lambda **kw: _reply(T, A, n, **kw)
        plain = R()
        steps_only = plain.split('\n')[:-1]
        ans = f'Answer: 1 = {_fmt_state(A)}'
        # accepted variants
        ok('plain', plain)
        ok('extra-spaces', R(eq='   =   ', sep=' ,   ').replace('[', '[  ').replace(']', '  ]'))
        ok('no-spaces', R(eq='=', sep=','))
        ok('crlf', R(nl='\r\n'))
        ok('blank-lines', R(nl='\n\n'))
        ok('bold-label', R(label=lambda i: f'**1.{i}**'))
        ok('bullets', '\n'.join(f'- {l}' if l.startswith('1.') else l for l in plain.split('\n')))
        ok('colon', R(eq=': '))
        ok('parens', R(style='parens'))
        ok('no-brackets', R(style='none'))
        ok('leading-zeros', R(zeros=True))
        order = list(range(1, n + 1)); rng.shuffle(order)
        ok('any-order', R(order=order))
        ok('answer-no-label', R(answer_line=f'Answer: {_fmt_state(A)}'))
        ok('prose-before-and-between', R(prefix='Here are the balances:', between='(continuing)'))
        ok('code-fence', R(fence=True))
        W = [v + 1 for v in A]
        ok('last-answer-line-wins', R(prefix=f'Answer: 1 = {_fmt_state(W)} (draft)'))
        ok('trailing-period-steps', '\n'.join(l + '.' for l in steps_only) + '\n' + ans)
        ok('trailing-period-answer', '\n'.join(steps_only) + '\n' + ans + '.')
        ok('answer-check-prose-after', plain + '\nAnswer check: every line verified.')
        ok('answer-sequence-label', '\n'.join(steps_only) + f'\nAnswer: Sequence 1 = {_fmt_state(A)}')
        ok('answer-bold-piece-label', '\n'.join(steps_only) + f'\nAnswer: **Piece 1** = {_fmt_state(A)}')
        S = [list(s) for s in T]; S[0] = [S[0][0] + 50] + S[0][1:]
        ok('value-slip-parses', _reply(S, A, n), states=S)
        # rejected
        bad('missing-line', R(order=[i for i in range(1, n + 1) if i != min(3, n)]), 'missing_line')
        # D-90 (Deviation 2): identical repeated step lines are accepted; conflicting repeats still fail
        ok('duplicate-line', R(order=list(range(1, n + 1)) + [max(1, n // 2)]))
        ok('duplicate-line-markup', '\n'.join(steps_only) + f'\n**1.{n}**={_fmt_state(T[-1], sep=",")}\n' + ans)
        C = [list(x) for x in T] + [[v + 7 for v in T[max(1, n // 2) - 1]]]
        bad('duplicate-line-conflicting', _reply(C, A, n + 1).replace(f'1.{n + 1} =', f'1.{max(1, n // 2)} =', 1),
            'extra_line')
        ok('summary-repeat-all', R(answer_line='') + '\nSummary:\n' + plain)
        Dd = [list(x) for x in T]; Dd[0] = [Dd[0][0] + 1] + Dd[0][1:]
        bad('summary-repeat-one-differs', R(answer_line='') + '\nSummary:\n' + _reply(Dd, A, n), 'extra_line')
        bad('out-of-range', _reply(T + [T[-1]], A, n + 1), 'misnumbered')
        sh = [list(s) for s in T]; sh[1] = sh[1][:-1]
        bad('short-state', _reply(sh, A, n), 'wrong_length')
        lg = [list(s) for s in T]; lg[1] = lg[1] + [123]
        bad('long-state', _reply(lg, A, n), 'wrong_length')
        bad('decimal', '\n'.join(l + '.0' if i == 1 else l for i, l in enumerate(steps_only))
            .replace(']' + '.0', '.0]') + '\n' + ans, 'non_integer')
        bad('double-period', '\n'.join(l + '..' if i == 1 else l for i, l in enumerate(steps_only)) + '\n' + ans,
            'non_integer')
        bad('no-answer-line', R(answer_line=''), 'no_answer')
        bad('answer-mismatch', R(answer_line=f'Answer: 1 = {_fmt_state(W)}'), 'answer_mismatch')
        bad('answer-sequences-plural', '\n'.join(steps_only) + f'\nAnswer: Sequences 1 = {_fmt_state(A)}',
            'no_answer')
        bad('answer-bare-wrong-number', '\n'.join(steps_only) + f'\nAnswer: 2 = {_fmt_state(A)}', 'non_integer',
            {'pair_rule': 'both not ok, with the same status'})
        bad('answer-sequence-wrong-number', '\n'.join(steps_only) + f'\nAnswer: Sequence 2 = {_fmt_state(A)}',
            'non_integer', {'pair_rule': 'both not ok, with the same status',
                            'same_status_as': f'N{n}-L{lines}-answer-bare-wrong-number'})
    return add_strict(cases)


def pieces_cases_n(n, seed):
    rng = np.random.default_rng(seed)
    S = [[int(v) for v in rng.integers(100, 15000, size=6)] for _ in range(n)]
    good = {str(i): S[i - 1] for i in range(1, n + 1)}
    ent = lambda lab='': ', '.join(f'{lab}{i} = {_fmt_state(S[i - 1])}' for i in range(1, n + 1))
    out = []
    def add(name, txt, ok, entries=None):
        out.append(dict(id=f'N{n}-P6-{name}', steps=n, width=n, line_count=6, reply=txt,
                        expected=dict(ok=ok, entries=entries if ok else None)))
    add('plain', 'Answer: ' + ent(), True, good)
    add('sequence-labels', 'Answer: ' + ent('Sequence '), True, good)
    add('bold-labels', 'Answer: ' + ', '.join(f'**Sequence {i}** = {_fmt_state(S[i - 1])}' for i in range(1, n + 1)),
        True, good)
    add('colon-entries', 'Answer: ' + ', '.join(f'{i}: {_fmt_state(S[i - 1])}' for i in range(1, n + 1)), True, good)
    add('trailing-period', 'Answer: ' + ent() + '.', True, good)
    add('prose-answer-after', 'Answer: ' + ent() + '\nAnswer check: done', True, good)
    add('step-labels', 'Answer: ' + ent('Step '), False)
    add('no-answer-line', ent(), False)
    return out


def write_all(root):
    os.makedirs(root, exist_ok=True)
    counts = {}
    for i, n in enumerate(NS):
        pc, pi = parse_cases_n(n, 8800 + i), pieces_cases_n(n, 8900 + i)
        for name, cases in ((f'parse_cases_n{n}.jsonl.gz', pc), (f'pieces_cases_n{n}.jsonl.gz', pi)):
            with gz_writer(os.path.join(root, name)) as f:
                for c in cases:
                    f.write(json.dumps(c, separators=(',', ':')) + '\n')
        counts[n] = (len(pc), len(pi))
    return counts


if __name__ == '__main__':
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures', 'sim-main-n'))
    print(write_all(root))
