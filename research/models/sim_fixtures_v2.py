"""Fixtures v2 for D-76 (Karen, OURS): the official 1x24 score is "all step lines right" (24 written states
correct, Answer line equal to line 24). Desk simulation only, no API calls.

Writes research/fixtures/sim-main-v2/:
  parse_cases.jsonl.gz   (A) crafted raw replies at 6, 8, 10 and 12 balances (l14-l17 sizes) covering every
                          accepted formatting variant and every reject reason agreed with Friday, with the
                          expected parse (ok, reason, the 24 states, the Answer state).
  <case>/rows.jsonl.gz    (B) analysis cases as in v1 (same seven cases and tests), but every 1x24 row carries
                          format_status, trace_key, final_key and slip_type, with copy slips, absorbed slips and
                          malformed replies mixed in; expected.json gives the readings under three scores:
                          official (D-76), final-answer (secondary, with measured absorption) and
                          copy-slips-forgiven (sensitivity), plus format-compliance and slip rates per arm.
Run: python3 research/models/sim_fixtures_v2.py
"""
import functools, gzip, hashlib, json, math, os, sys
from collections import Counter
import numpy as np
from scipy import stats

import sim_fixtures as v1
from sim_fixtures import gz_writer

N_BASE, N_HAIKU, PRESET, LINES = v1.N_BASE, v1.N_HAIKU, v1.PRESET, 10
H_MEAN, CONC, S_SHARED, RHO_SHAPE, KAPPA = v1.H_MEAN, v1.CONC, v1.S_SHARED, v1.RHO_SHAPE, v1.KAPPA
TESTS, CASES = v1.TESTS, v1.CASES
FORMAT_FAIL = {'haiku-med': 0.03, 'opus-med': 0.01, 'opus-low': 0.01, 'sonnet-med': 0.015}
FAIL_REASONS = ['missing_line', 'extra_line', 'misnumbered', 'wrong_length', 'non_integer', 'no_answer',
                'answer_mismatch']
WRONG_MIX = {'haiku-med': (0.75, 0.15, 0.10), 'single': (0.70, 0.20, 0.10)}   # real, copy, absorbed (unique wrong)


# ------------------------------------------------------------------ the vote (exact, fast)
@functools.lru_cache(maxsize=None)
def vote_credit(c, a, z, r, k):
    """Expected vote@k credit over all k-subsets of n = c+a+z+r samples: c right, a copies of one shared wrong
    value, z nulls (a vote for nothing), r wrong values all different. Plurality; a tie of m answers including
    the right one scores 1/m. Equal to sim_fixtures.vote_exact(c, a, r, z, k)."""
    n = c + a + z + r
    k = min(k, n)
    if k <= 0 or c == 0:
        return 0.0
    tot = math.comb(n, k)
    o = n - c - a
    s = 0.0
    for x in range(2, min(c, k) + 1):
        for y in range(0, min(a, k - x, x) + 1):
            rest = k - x - y
            if rest > o:
                continue
            s += math.comb(c, x) * math.comb(a, y) * math.comb(o, rest) * (1.0 if x > y else 0.5)
    for y in (0, 1):
        if y > a or 1 + y > k:
            continue
        rest = k - 1 - y
        if rest > o:
            continue
        base = c * math.comb(a, y)
        for w in range(0, min(z, rest) + 1):
            if rest - w > r:
                continue
            s += base * math.comb(z, w) * math.comb(r, rest - w) / (k - w)
    return s / tot


@functools.lru_cache(maxsize=None)
def expected_vote_v2(m, k, q, conc=CONC, shared=S_SHARED, n=N_HAIKU, N=300_000, seed=4242):
    """Population vote@k accuracy on the official score: p ~ Beta(conc m, conc (1-m)); each sample is null with
    probability q (format failure), else right with p, else the shared wrong trace with `shared`, else unique.
    Monte Carlo over puzzles (N, fixed seed; error about 0.001), exact over subsets."""
    rng = np.random.default_rng(seed)
    p = rng.beta(conc * m, conc * (1 - m), N)
    pv = np.stack([q * np.ones(N), (1 - q) * p, (1 - q) * (1 - p) * shared, (1 - q) * (1 - p) * (1 - shared)], 1)
    cnt = rng.multinomial(n, pv)
    tot = 0.0
    uniq, inv = np.unique(cnt, axis=0, return_inverse=True)
    vals = np.array([vote_credit(int(c), int(a), int(z), int(r), k) for z, c, a, r in uniq])
    return float(vals[inv.ravel()].mean())


# ------------------------------------------------------------------ (A) parse cases
def _trace(rng, lines):
    return [[int(v) for v in rng.integers(100, 15000, size=lines)] for _ in range(24)]


def _fmt_state(st, style='brackets', sep=', ', zeros=False):
    vals = [f'{v:05d}' if zeros else str(v) for v in st]
    body = sep.join(vals)
    return {'brackets': f'[{body}]', 'parens': f'({body})', 'none': body}[style]


def _reply(states, answer, *, label=lambda i: f'1.{i}', eq=' = ', style='brackets', sep=', ', zeros=False,
           order=None, between=None, nl='\n', answer_line=None, prefix='', suffix='', fence=False):
    order = order or list(range(1, 25))
    out = []
    if prefix:
        out.append(prefix)
    for j, i in enumerate(order):
        out.append(f'{label(i)}{eq}{_fmt_state(states[i - 1], style, sep, zeros)}')
        if between and j == 11:
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


def parse_cases(seed=7676):
    rng = np.random.default_rng(seed)
    cases = []
    for lines in (6, 8, 10, 12):
        T = _trace(rng, lines)
        A = T[23]
        ok = lambda name, txt, states=T, ans=A: cases.append(dict(
            id=f'L{lines}-{name}', line_count=lines, reply=txt, expected=dict(ok=True, reason=None, states=states,
                                                                              answer=ans)))
        bad = lambda name, txt, reason: cases.append(dict(
            id=f'L{lines}-{name}', line_count=lines, reply=txt, expected=dict(ok=False, reason=reason, states=None,
                                                                              answer=None)))
        # accepted variants (all must parse to T and A)
        ok('plain', _reply(T, A))
        ok('extra-spaces', _reply(T, A, eq='   =   ', sep=' ,   ').replace('[', '[  ').replace(']', '  ]'))
        ok('no-spaces', _reply(T, A, eq='=', sep=','))
        ok('tabs-leading-trailing', '\n'.join('\t ' + l + ' \t' for l in _reply(T, A).split('\n')))
        ok('crlf', _reply(T, A, nl='\r\n'))
        ok('blank-lines', _reply(T, A, nl='\n\n'))
        ok('bold-label', _reply(T, A, label=lambda i: f'**1.{i}**'))
        ok('backticks', '\n'.join(f'`{l}`' if l.startswith('1.') else l for l in _reply(T, A).split('\n')))
        ok('bullets', '\n'.join(f'- {l}' if l.startswith('1.') else l for l in _reply(T, A).split('\n')))
        ok('colon', _reply(T, A, eq=': '))
        ok('parens', _reply(T, A, style='parens'))
        ok('no-brackets', _reply(T, A, style='none'))
        ok('leading-zeros', _reply(T, A, zeros=True))
        order = list(range(1, 25)); rng.shuffle(order)
        ok('any-order', _reply(T, A, order=order))
        ok('answer-lowercase', _reply(T, A, answer_line=f'answer: 1 = {_fmt_state(A)}'))
        ok('answer-bold', _reply(T, A, answer_line=f'**Answer:** 1 = {_fmt_state(A)}'))
        ok('answer-no-label', _reply(T, A, answer_line=f'Answer: {_fmt_state(A)}'))
        ok('answer-no-colon', _reply(T, A, answer_line=f'Answer 1 = {_fmt_state(A)}'))
        ok('prose-before-and-between', _reply(T, A, prefix='Here are the balances after each rule:',
                                              between='(continuing with the house rule applied)'))
        ok('trailing-prose', _reply(T, A, suffix='I applied the house rule after every step.'))
        ok('code-fence', _reply(T, A, fence=True))
        W = [list(s) for s in T]; W[23] = [v + 1 for v in W[23]]
        ok('last-answer-line-wins', _reply(T, A, prefix=f'Answer: 1 = {_fmt_state(W[23])} (draft)'))
        ok('combo-fence-bold-colon-crlf', _reply(T, A, label=lambda i: f'**1.{i}**', eq=': ', nl='\r\n', fence=True,
                                                 suffix='Done.'))
        # parses fine but a value is wrong (a slip, not a format problem): parser ok, states differ from the key
        S = [list(s) for s in T]; S[9] = [S[9][0] + 50] + S[9][1:]
        ok('value-slip-parses', _reply(S, A), states=S)
        # rejected
        drop = [i for i in range(1, 25) if i != 7]
        bad('missing-line', _reply(T, A, order=drop), 'missing_line')
        # D-90 (Deviation 2): a step line written again with the IDENTICAL state is accepted (lock-2: extra_line).
        # More D-90 cases are in parse_cases_d90 (a separate file, so round 1 stays at 148 cases)
        ok('duplicate-line', _reply(T, A, order=list(range(1, 25)) + [12]))
        bad('out-of-range-25', _reply(T + [T[23]], A, order=list(range(1, 26))), 'misnumbered')
        bad('number-zero', _reply([T[0]] + T, A, label=lambda i: f'1.{i - 1}', order=list(range(1, 26))), 'misnumbered')
        short = [list(s) for s in T]; short[4] = short[4][:-1]
        bad('short-state', _reply(short, A), 'wrong_length')
        long_ = [list(s) for s in T]; long_[4] = long_[4] + [123]
        bad('long-state', _reply(long_, A), 'wrong_length')
        bad('decimal', _reply(T, A).replace(f'{T[2][0]},', f'{T[2][0]}.0,', 1), 'non_integer')
        th = _reply(T, A).replace(str(T[3][1]), f'{T[3][1] // 1000},{T[3][1] % 1000:03d}', 1) if T[3][1] >= 1000 else None
        if th:
            bad('thousands-separator', th, 'wrong_length')
        bad('word', _reply(T, A).replace(str(T[5][0]), 'two thousand', 1), 'non_integer')
        bad('tilde', _reply(T, A).replace(str(T[6][0]), '~' + str(T[6][0]), 1), 'non_integer')
        bad('no-answer-line', _reply(T, A, answer_line=''), 'no_answer')
        bad('answer-mismatch', _reply(T, A, answer_line=f'Answer: 1 = {_fmt_state(W[23])}'), 'answer_mismatch')
        bad('answer-wrong-length', _reply(T, A, answer_line=f'Answer: 1 = {_fmt_state(A[:-1])}'), 'wrong_length')
    cases += parse_cases_r2()
    return add_strict(cases)


def parse_cases_d90(seed=7678):
    """D-90 (Deviation 2, 2026-10-12): identical repeated step lines are accepted; a repeat with a different state still
    fails (extra_line); "identical" is compared after reading, so markup may differ. Separate seed and file
    (parse_cases_d90.jsonl.gz), so rounds 1 and 2 are unchanged. Each case carries expected_strict where lock-2's rule
    differs."""
    rng = np.random.default_rng(seed)
    out = []
    for lines in (6, 8, 10, 12):
        T = _trace(rng, lines)
        A = T[23]
        ok = lambda name, txt: out.append(dict(id=f'L{lines}-d90-{name}', line_count=lines, reply=txt,
                                               expected=dict(ok=True, reason=None, states=T, answer=A)))
        bad = lambda name, txt, reason: out.append(dict(id=f'L{lines}-d90-{name}', line_count=lines, reply=txt,
                                                        expected=dict(ok=False, reason=reason, states=None, answer=None)))
        plain = _reply(T, A)
        steps = plain.split('\n')[:-1]
        ok('duplicate-line-markup', '\n'.join(steps) + f'\n**1.12**={_fmt_state(T[11], sep=",")}\n' + plain.split('\n')[-1])
        C = [list(x) for x in T] + [[v + 7 for v in T[11]]]
        bad('duplicate-line-conflicting', _reply(C, A, order=list(range(1, 26))).replace('1.25 =', '1.12 =', 1),
            'extra_line')
        ok('summary-repeat-all', _reply(T, A, answer_line='') + '\nSummary:\n' + plain)
        D = [list(x) for x in T]; D[4] = [D[4][0] + 1] + D[4][1:]
        bad('summary-repeat-one-differs', _reply(T, A, answer_line='') + '\nSummary:\n' + _reply(D, A), 'extra_line')
    return add_strict(out)


def parse_cases_r2(seed=7677):
    """Round 2 (2026-10-11, after Friday's PR #24/#25 changes): one trailing '.' or ',' after a state; a prose line
    starting with 'answer' never replaces the real Answer line; an optional 'Sequence' or 'Piece' label (any case)
    before N in the Answer line. Separate seed, so the round-1 cases above are unchanged."""
    rng = np.random.default_rng(seed)
    out = []
    for lines in (6, 10):
        T = _trace(rng, lines)
        A = T[23]
        ok = lambda name, txt: out.append(dict(id=f'L{lines}-r2-{name}', line_count=lines, reply=txt,
                                               expected=dict(ok=True, reason=None, states=T, answer=A)))
        bad = lambda name, txt, reason: out.append(dict(id=f'L{lines}-r2-{name}', line_count=lines, reply=txt,
                                                        expected=dict(ok=False, reason=reason, states=None, answer=None)))
        plain = _reply(T, A)
        steps = plain.split('\n')[:-1]
        ans = f'Answer: 1 = {_fmt_state(A)}'
        ok('trailing-period-steps', '\n'.join(l + '.' for l in steps) + '\n' + ans)
        ok('trailing-comma-steps', '\n'.join(l + ',' for l in steps) + '\n' + ans)
        ok('trailing-period-answer', '\n'.join(steps) + '\n' + ans + '.')
        ok('answer-check-prose-after', plain + '\nAnswer check: every line verified.')
        ok('answer-heading-prose-before', '## Answer\n' + plain)
        ok('answer-sequence-label', '\n'.join(steps) + f'\nAnswer: Sequence 1 = {_fmt_state(A)}')
        ok('answer-SEQUENCE-upper', '\n'.join(steps) + f'\nANSWER: SEQUENCE 1 = {_fmt_state(A)}')
        ok('answer-piece-label', '\n'.join(steps) + f'\nAnswer: piece 1 = {_fmt_state(A)}')
        bad('double-period', '\n'.join(l + '..' if i == 4 else l for i, l in enumerate(steps)) + '\n' + ans, 'non_integer')
        bad('space-period', '\n'.join(l + ' .' if i == 4 else l for i, l in enumerate(steps)) + '\n' + ans, 'non_integer')
        bad('period-then-text', '\n'.join(l + '. Done' if i == 4 else l for i, l in enumerate(steps)) + '\n' + ans, 'non_integer')
        bad('trailing-semicolon', '\n'.join(l + ';' if i == 4 else l for i, l in enumerate(steps)) + '\n' + ans, 'non_integer')
        bad('answer-sequences-plural', '\n'.join(steps) + f'\nAnswer: Sequences 1 = {_fmt_state(A)}', 'no_answer')
        # Edith's conditions (2026-10-11): narrow label rule, markup, colon, prose stays prose, no Step/Line labels
        ok('answer-sequence-mixed-case', '\n'.join(steps) + f'\nAnswer: sEqUeNcE 1 = {_fmt_state(A)}')
        ok('answer-sequence-bold-label', '\n'.join(steps) + f'\nAnswer: **Sequence 1** = {_fmt_state(A)}')
        ok('answer-bold-then-piece', '\n'.join(steps) + f'\n**Answer:** Piece 1 = {_fmt_state(A)}')
        ok('answer-sequence-colon', '\n'.join(steps) + f'\nAnswer: Sequence 1: {_fmt_state(A)}')
        ok('answer-sequence-prose-after-real', plain + f'\nAnswer: Sequence 1 ends at {_fmt_state(A)}')
        bad('answer-sequence-prose-only', '\n'.join(steps) + f'\nAnswer: Sequence 1 ends at {_fmt_state(A)}', 'no_answer')
        bad('answer-step-label', '\n'.join(steps) + f'\nAnswer: Step 1 = {_fmt_state(A)}', 'no_answer')
        bad('answer-line-label', '\n'.join(steps) + f'\nAnswer: Line 1 = {_fmt_state(A)}', 'no_answer')
        # Edith's case 3: a wrong number after the label is not let through; same status as a bare wrong number
        bad('answer-bare-wrong-number', '\n'.join(steps) + f'\nAnswer: 2 = {_fmt_state(A)}', 'non_integer')
        bad('answer-sequence-wrong-number', '\n'.join(steps) + f'\nAnswer: Sequence 2 = {_fmt_state(A)}', 'non_integer')
        out[-1]['expected']['same_status_as'] = f'L{lines}-r2-answer-bare-wrong-number'
        for c in out[-2:]:   # Edith: each member of the pair must be not ok AND share the status
            c['expected']['pair_rule'] = 'both not ok, with the same status'
        ok('answer-bold-bare-number', '\n'.join(steps) + f'\nAnswer: **1** = {_fmt_state(A)}')
    return out


def final_cases(seed=7679):
    """The answer-only fallback (d31-answer-only, 1x24; parse_final): expected {ok, answer}. Edith's case 1 plus
    the narrow-rule checks; the wrong-number pair must give the same status."""
    rng = np.random.default_rng(seed)
    out = []
    A = [int(v) for v in rng.integers(100, 15000, size=6)]
    add = lambda name, txt, ok, extra=None: out.append(dict(id=f'F6-{name}', line_count=6, reply=txt,
                                                           expected=dict(ok=ok, answer=A if ok else None, **(extra or {}))))
    add('plain', f'Answer: 1 = {_fmt_state(A)}', True)
    add('sequence-label', f'Answer: Sequence 1 = {_fmt_state(A)}', True)
    add('piece-label-bold', f'**Answer:** **Piece 1** = {_fmt_state(A)}', True)
    add('no-label', f'Answer: {_fmt_state(A)}', True)
    add('sequence-ends-at-prose-only', f'Answer: Sequence 1 ends at {_fmt_state(A)}', False)
    add('step-label', f'Answer: Step 1 = {_fmt_state(A)}', False)
    add('bare-wrong-number', f'Answer: 2 = {_fmt_state(A)}', False, {'reason': 'non_integer'})
    add('sequence-wrong-number', f'Answer: Sequence 2 = {_fmt_state(A)}', False,
        {'same_status_as': 'F6-bare-wrong-number', 'reason': 'non_integer'})
    for c in out[-2:]:   # Edith: each member of the pair must be not ok AND share the status
        c['expected']['pair_rule'] = 'both not ok, with the same status'
    add('bold-bare-number', f'Answer: **1** = {_fmt_state(A)}', True)
    return out


def pieces_cases(seed=7678):
    """24x1 Answer lines (parse_pieces): expected entries {N: state} and status. 24 pieces at 6 balances."""
    rng = np.random.default_rng(seed)
    out = []
    S = [[int(v) for v in rng.integers(100, 15000, size=6)] for _ in range(24)]
    ent = lambda lab='': ', '.join(f'{lab}{i} = {_fmt_state(S[i - 1])}' for i in range(1, 25))
    good = {str(i): S[i - 1] for i in range(1, 25)}
    add = lambda name, txt, ok, entries=None: out.append(dict(id=f'P6-{name}', width=24, line_count=6, reply=txt,
                                                             expected=dict(ok=ok, entries=entries if ok else None)))
    add('plain', 'Answer: ' + ent(), True, good)
    add('sequence-labels', 'Answer: ' + ent('Sequence '), True, good)
    add('piece-labels', 'Answer: ' + ent('Piece '), True, good)
    add('trailing-period', 'Answer: ' + ent() + '.', True, good)
    add('prose-answer-after', 'Answer: ' + ent() + '\nAnswer check: done', True, good)
    add('bold-answer', '**Answer**: ' + ent(), True, good)
    add('sequences-plural', 'Answer: ' + ent('Sequences '), False)
    add('no-answer-line', ent(), False)
    # Edith's conditions (2026-10-11)
    mixed = ', '.join(f'{"SeQuEnCe " if i % 2 else "piece "}{i} = {_fmt_state(S[i - 1])}' for i in range(1, 25))
    add('mixed-case-labels', 'Answer: ' + mixed, True, good)
    add('bold-labels', 'Answer: ' + ', '.join(f'**Sequence {i}** = {_fmt_state(S[i - 1])}' for i in range(1, 25)), True, good)
    add('sequence-colon-labels', 'Answer: ' + ', '.join(f'Sequence {i}: {_fmt_state(S[i - 1])}' for i in range(1, 25)), True, good)
    add('prose-sequence-ends-at-only', 'Answer: ' + ', '.join(f'Sequence {i} ends at {_fmt_state(S[i - 1])}' for i in range(1, 25)), False)
    add('prose-after-real', 'Answer: ' + ent() + '\nAnswer: Sequence 1 ends at ' + _fmt_state(S[0]), True, good)
    add('step-labels', 'Answer: ' + ent('Step '), False)
    add('line-labels', 'Answer: ' + ent('Line '), False)
    # Edith's case 2: mixed labels on one line; the label is accepted at every entry, not only the first
    lab = lambda i: ('', 'Sequence ', 'Piece ')[i % 3]
    add('mixed-labels-one-line', 'Answer: ' + ', '.join(f'{lab(i)}{i} = {_fmt_state(S[i - 1])}' for i in range(1, 25)),
        True, good)
    add('bare-colon-entries', 'Answer: ' + ', '.join(f'{i}: {_fmt_state(S[i - 1])}' for i in range(1, 25)), True, good)
    add('bold-bare-numbers', 'Answer: ' + ', '.join(f'**{i}** = {_fmt_state(S[i - 1])}' for i in range(1, 25)), True, good)
    return out


# ------------------------------------------------------------------ (B) analysis cases
def _key(*parts):
    return hashlib.sha1('|'.join(map(str, parts)).encode()).hexdigest()[:16]


def make_case_v2(name, seed, d, opus_refusals=0, opus_low_refusals=0, sonnet_truncations=0, haiku_unparseable=0.0,
                 haiku_truncated=0.0, haiku_steps=False):
    rng = np.random.default_rng(seed)
    set_id = f'simfix2-{name}-v2'
    bases = [f'b{i:03d}' for i in range(N_BASE)]
    Lb = rng.standard_normal(N_BASE)
    Ls = {s: math.sqrt(RHO_SHAPE) * Lb + math.sqrt(1 - RHO_SHAPE) * rng.standard_normal(N_BASE) for s in H_MEAN}
    eta = {(arm, s): KAPPA * Ls[s] + math.sqrt(1 - KAPPA ** 2) * rng.standard_normal(N_BASE)
           for s in H_MEAN for arm in ('haiku-med', 'opus-med', 'opus-low', 'sonnet-med', 'e3')}
    p_h = {s: stats.beta.ppf(1 - stats.norm.cdf(eta[('haiku-med', s)]), CONC * H_MEAN[s], CONC * (1 - H_MEAN[s]))
           for s in H_MEAN}
    # costs (k is set from costs, as the k script does), with refusals and truncations decided first
    pick = lambda n: set(rng.choice(N_BASE, size=n, replace=False).tolist()) if n else set()
    om_ref, ol_ref, sm_tr = pick(opus_refusals), pick(opus_low_refusals), pick(sonnet_truncations)
    cost_rows = []
    for s in H_MEAN:
        for b_i, b in enumerate(bases):
            for setup in ('opus-med', 'sonnet-med'):
                kind = 'answered'
                if s == '1x24' and setup == 'opus-med' and b_i in om_ref:
                    kind = 'refusal'
                if s == '1x24' and setup == 'sonnet-med' and b_i in sm_tr:
                    kind = 'truncated'
                cost_rows.append(dict(shape=s, setup=setup, base_id=b, kind=kind, cost_usd=str(v1._cost(rng, setup, s, kind))))
            for t in range(N_HAIKU):
                u = rng.random()
                kind = 'answered'
                if s == '1x24' and u < haiku_truncated:
                    kind = 'truncated'
                elif s == '1x24' and u < haiku_truncated + haiku_unparseable:
                    kind = 'unparseable'
                cost_rows.append(dict(shape=s, setup='haiku-med', base_id=b, kind=kind,
                                      cost_usd=str(v1._cost(rng, 'haiku-med', s, kind))))
    kO = {s: v1.k_from_costs(cost_rows, s, 'opus-med') for s in H_MEAN}
    kS = {s: v1.k_from_costs(cost_rows, s, 'sonnet-med') for s in H_MEAN}
    # true vote accuracies (official score; Haiku format failures and unparseable replies are nulls)
    qh = FORMAT_FAIL['haiku-med'] + haiku_unparseable
    EV = {('O', '24x1'): v1.expected_vote(H_MEAN['24x1'], kO['24x1']),          # 24x1 unchanged (no step lines)
          ('O', '1x24'): expected_vote_v2(H_MEAN['1x24'], kO['1x24'], round(qh, 6)),
          ('S', '1x24'): expected_vote_v2(H_MEAN['1x24'], kS['1x24'], round(qh, 6))}
    acc = {('opus-med', '24x1'): EV[('O', '24x1')] - d['t1'] / 100,
           ('opus-med', '1x24'): EV[('O', '1x24')] - d['t2'] / 100,
           ('sonnet-med', '1x24'): EV[('S', '1x24')] - d['t3'] / 100}
    acc[('e3', '1x24')] = acc[('opus-med', '1x24')] + d['t4'] / 100
    acc[('opus-low', '1x24')] = acc[('sonnet-med', '1x24')] + d['t5'] / 100
    acc[('sonnet-med', '24x1')] = min(0.97, EV[('S', '1x24')] + 0.25)
    acc[('opus-low', '24x1')] = min(0.97, acc[('opus-med', '24x1')] - 0.03)
    acc[('e3', '24x1')] = min(0.97, acc[('opus-med', '24x1')])
    for kk, v in acc.items():
        q = FORMAT_FAIL.get(kk[0], 0.0) if kk[1] == '1x24' else 0.0
        if not 0.02 <= v / (1 - q) <= 0.995:
            raise ValueError(f'case {name}: accuracy {kk} = {v:.3f} out of range')
    rows, counts = [], {}
    cit = iter(cost_rows)

    def trace_outcome(correct, mix):
        if correct:
            return 'none'
        u = rng.random()
        return 'real' if u < mix[0] else ('copy' if u < mix[0] + mix[1] else 'absorbed')

    def fmt_status(arm):
        return FAIL_REASONS[int(rng.integers(len(FAIL_REASONS)))] if rng.random() < FORMAT_FAIL[arm] else 'ok'

    for s in H_MEAN:
        for b_i, b in enumerate(bases):
            right_trace, right_final = _key(set_id, b, s, 'trace'), _key(set_id, b, s, 'final')
            right24 = _key(set_id, b, s, 'right')
            for setup in ('opus-med', 'sonnet-med', 'opus-low', 'e3'):
                cr = next(cit) if setup in ('opus-med', 'sonnet-med') else None
                kind = cr['kind'] if cr else 'answered'
                if s == '1x24' and setup == 'opus-low' and b_i in ol_ref:
                    kind = 'refusal'
                cost = cr['cost_usd'] if cr else str(v1._cost(rng, setup, s, kind))
                stop = {'answered': 'end_turn', 'refusal': 'refusal', 'truncated': 'max_tokens'}[kind]
                row = dict(set_id=set_id, preset=PRESET, line_count=LINES, base_id=b, shape=s, setup=setup, try_=0,
                           kind=kind, stop_reason=stop, refusal_category='cyber' if kind == 'refusal' else None,
                           cost_usd=cost)
                if setup == 'e3':
                    ok = bool(eta[(setup, s)][b_i] < stats.norm.ppf(acc[(setup, s)]))
                    st = [True] * 24
                    if not ok:
                        for j in rng.choice(24, size=int(rng.integers(1, 4)), replace=False):
                            st[int(j)] = False
                    row.update(step_correct=st, correct=ok, answer_key=right24 if ok else _key(set_id, b, s, 'e3w'))
                elif s == '24x1':
                    ok = bool(eta[(setup, s)][b_i] < stats.norm.ppf(acc[(setup, s)])) and kind == 'answered'
                    row.update(answer_key=(right24 if ok else _key(set_id, b, s, setup, 'w')) if kind == 'answered' else None,
                               correct=ok)
                else:   # 1x24 single answer: D-76 trace scoring
                    q = FORMAT_FAIL[setup]
                    lat_ok = bool(eta[(setup, s)][b_i] < stats.norm.ppf(acc[(setup, s)] / (1 - q)))
                    slip = trace_outcome(lat_ok, WRONG_MIX['single'])
                    fs = fmt_status(setup) if kind == 'answered' else kind
                    final_ok = slip in ('none', 'copy', 'absorbed')
                    tk = (right_trace if slip == 'none' else _key(set_id, b, s, setup, 'trace-w')) if fs == 'ok' else None
                    fk = None if kind != 'answered' or fs == 'no_answer' else (
                        right_final if final_ok else _key(set_id, b, s, setup, 'final-w'))
                    row.update(format_status=fs, trace_key=tk, final_key=fk, slip_type=slip if kind == 'answered' else None,
                               correct=bool(fs == 'ok' and slip == 'none'),
                               correct_final=bool(fk is not None and final_ok),
                               correct_copy_forgiven=bool(fs == 'ok' and slip in ('none', 'copy')))
                rows.append(row)
            # Haiku-medium x40
            cnt = {v: [0, 0, 0, 0] for v in ('official', 'final', 'copyfree', 'official_trunc_out')}   # c, a, z, r
            for t in range(N_HAIKU):
                cr = next(cit)
                kind = cr['kind']
                stop = 'max_tokens' if kind == 'truncated' else 'end_turn'
                row = dict(set_id=set_id, preset=PRESET, line_count=LINES, base_id=b, shape=s, setup='haiku-med',
                           try_=t, kind=kind, stop_reason=stop, refusal_category=None, cost_usd=cr['cost_usd'])
                right = bool(rng.random() < p_h[s][b_i])
                if s == '24x1':
                    if kind != 'answered':
                        key = None
                    elif right:
                        key = right24
                    elif rng.random() < S_SHARED:
                        key = _key(set_id, b, s, 'shared-wrong')
                    else:
                        key = _key(set_id, b, s, 'wrong', t)
                    row.update(answer_key=key, correct=bool(kind == 'answered' and right))
                    rows.append(row)
                    continue
                shared = (not right) and rng.random() < S_SHARED
                slip = 'none' if right else ('real' if shared else trace_outcome(False, WRONG_MIX['haiku-med']))
                fs = fmt_status('haiku-med') if kind == 'answered' else kind
                final_ok = slip in ('none', 'copy', 'absorbed')
                if fs == 'ok':
                    tk = right_trace if slip == 'none' else (_key(set_id, b, s, 'trace-shared') if shared
                                                             else _key(set_id, b, s, 'trace-w', t))
                else:
                    tk = None
                if kind != 'answered' or fs == 'no_answer':
                    fk = None
                else:
                    fk = right_final if final_ok else (_key(set_id, b, s, 'final-shared') if shared
                                                       else _key(set_id, b, s, 'final-w', t))
                row.update(format_status=fs, trace_key=tk, final_key=fk, slip_type=slip if kind == 'answered' else None,
                           correct=bool(fs == 'ok' and slip == 'none'),
                           correct_final=bool(fk is not None and final_ok),
                           correct_copy_forgiven=bool(fs == 'ok' and slip in ('none', 'copy')))
                rows.append(row)
                # vote counts per score view
                def put(view, cat):
                    cnt[view][{'c': 0, 'a': 1, 'z': 2, 'r': 3}[cat]] += 1
                if tk is None:
                    put('official', 'z')
                    if kind != 'truncated':
                        put('official_trunc_out', 'z')
                else:
                    cat = 'c' if slip == 'none' else ('a' if shared else 'r')
                    put('official', cat); put('official_trunc_out', cat)
                put('final', 'z' if fk is None else ('c' if final_ok else ('a' if shared else 'r')))
                put('copyfree', 'z' if fs != 'ok' else ('c' if slip in ('none', 'copy') else ('a' if shared else 'r')))
            counts[(b, s)] = {v: tuple(x) for v, x in cnt.items()}
    for r in rows:
        r['try'] = r.pop('try_')
    for sh in H_MEAN:
        assert v1.k_from_costs(rows, sh, 'opus-med') == kO[sh] and v1.k_from_costs(rows, sh, 'sonnet-med') == kS[sh]
    return dict(rows=rows, counts=counts, kO=kO, kS=kS, EV=EV, acc=acc)


def scores_v2(case, score='official', view='as_deployed'):
    """score: official | final | copyfree. view: as_deployed | refusals_left_out | truncations_left_out."""
    single = {(r['setup'], r['shape'], r['base_id']): r for r in case['rows'] if r['setup'] != 'haiku-med'}
    bases = sorted({r['base_id'] for r in case['rows']})
    field = {'official': 'correct', 'final': 'correct_final', 'copyfree': 'correct_copy_forgiven'}[score]

    def single_score(setup, shape, b):
        r = single[(setup, shape, b)]
        if view == 'refusals_left_out' and r['kind'] == 'refusal':
            return np.nan
        if view == 'truncations_left_out' and r['kind'] == 'truncated':
            return np.nan
        if setup == 'e3' or shape == '24x1':
            return 1.0 if r['correct'] else 0.0
        return 1.0 if r[field] else 0.0

    def vote(shape, b, k):
        if shape == '24x1':
            c, a, r_, z, zt = case['v1counts'][(b, shape)]
            return v1.vote_exact(c, a, r_, z + zt, k)
        key = 'official_trunc_out' if (score == 'official' and view == 'truncations_left_out') else \
              {'official': 'official', 'final': 'final', 'copyfree': 'copyfree'}[score]
        c, a, z, r_ = case['counts'][(b, shape)][key]
        return vote_credit(c, a, z, r_, k)

    out = {}
    for name, chal, comp, shape in TESTS:
        ch, co = [], []
        for b in bases:
            if chal == 'vote_kO':
                ch.append(vote(shape, b, case['kO'][shape]))
            elif chal == 'vote_kS':
                ch.append(vote(shape, b, case['kS'][shape]))
            else:
                ch.append(single_score(chal, shape, b))
            co.append(single_score(comp, shape, b))
        out[name] = (np.array(ch, float), np.array(co, float))
    return out


def _v1counts_exact(rows):
    groups = {}
    for r in rows:
        if r['setup'] == 'haiku-med' and r['shape'] == '24x1':
            groups.setdefault(r['base_id'], []).append(r)
    out = {}
    for b, rs in groups.items():
        right = [x for x in rs if x['correct']]
        wrong = [x['answer_key'] for x in rs if not x['correct'] and x['answer_key'] is not None]
        cnts = Counter(wrong)
        a = max(cnts.values()) if cnts and max(cnts.values()) > 1 else 0
        r_ = len(wrong) - a
        z = sum(1 for x in rs if x['answer_key'] is None)
        out[(b, '24x1')] = (len(right), a, r_, z, 0)
    return out


def rates(rows):
    out = {}
    for setup in ('haiku-med', 'opus-med', 'opus-low', 'sonnet-med'):
        rs = [r for r in rows if r['shape'] == '1x24' and r['setup'] == setup and r['kind'] == 'answered']
        ok = [r for r in rs if r['format_status'] == 'ok']
        wrong = [r for r in ok if r['slip_type'] != 'none']
        out[setup] = dict(answered=len(rs), format_compliance=round(len(ok) / len(rs), 4),
                          trace_wrong=len(wrong),
                          absorbed_share_of_trace_wrong=round(sum(r['slip_type'] == 'absorbed' for r in wrong) / max(1, len(wrong)), 4),
                          copy_share_of_trace_wrong=round(sum(r['slip_type'] == 'copy' for r in wrong) / max(1, len(wrong)), 4),
                          official_acc=round(np.mean([r['correct'] for r in rs]), 4),
                          final_acc=round(np.mean([r['correct_final'] for r in rs]), 4),
                          copyfree_acc=round(np.mean([r['correct_copy_forgiven'] for r in rs]), 4))
    return out


def write_all(root):
    os.makedirs(root, exist_ok=True)
    pc = parse_cases()
    with gz_writer(os.path.join(root, 'parse_cases.jsonl.gz')) as f:
        for c in pc:
            f.write(json.dumps(c, separators=(',', ':')) + '\n')
    with gz_writer(os.path.join(root, 'parse_cases_d90.jsonl.gz')) as f:
        for c in parse_cases_d90():
            f.write(json.dumps(c, separators=(',', ':')) + '\n')
    with gz_writer(os.path.join(root, 'pieces_cases.jsonl.gz')) as f:
        for c in pieces_cases():
            f.write(json.dumps(c, separators=(',', ':')) + '\n')
    with gz_writer(os.path.join(root, 'final_cases.jsonl.gz')) as f:
        for c in final_cases():
            f.write(json.dumps(c, separators=(',', ':')) + '\n')
    summary = {'parse_cases': dict(n=len(pc), ok=sum(c['expected']['ok'] for c in pc))}
    for name, cfg in CASES.items():
        extra = {k: v for k, v in cfg.items() if k not in ('seed', 'd')}
        case = make_case_v2(name, cfg['seed'], cfg['d'], **extra)
        case['v1counts'] = _v1counts_exact(case['rows'])
        d = os.path.join(root, name)
        os.makedirs(d, exist_ok=True)
        with gz_writer(os.path.join(d, 'rows.jsonl.gz')) as f:
            for r in case['rows']:
                f.write(json.dumps(r, separators=(',', ':')) + '\n')
        readings = {'official': {v: v1.analyse(scores_v2(case, 'official', v), cfg['seed'])
                                 for v in ('as_deployed', 'refusals_left_out', 'truncations_left_out')},
                    'final_answer_secondary': {'as_deployed': v1.analyse(scores_v2(case, 'final'), cfg['seed'])},
                    'copy_slips_forgiven': {'as_deployed': v1.analyse(scores_v2(case, 'copyfree'), cfg['seed'])}}
        exp = dict(case=name, set_id=f'simfix2-{name}-v2', seed=cfg['seed'], n_base=N_BASE, haiku_tries=N_HAIKU,
                   line_count=LINES, true_d_official_left_out=cfg['d'],
                   k={'opus_matched': case['kO'], 'sonnet_matched_1x24': case['kS']['1x24']},
                   population_vote_accuracy={f'{w}/{s}': round(v, 5) for (w, s), v in case['EV'].items()},
                   target_accuracy_official={f'{a}/{s}': round(v, 5) for (a, s), v in case['acc'].items()},
                   rates_1x24=rates(case['rows']),
                   scoring=dict(official='D-76: format_status ok AND trace_key equals the right trace (24x1 and E3 '
                                         'unchanged); a try whose format is not ok is wrong and a null vote',
                                final_answer_secondary='final_key equals the right final; null if no Answer line',
                                copy_slips_forgiven='format ok AND slip_type in {none, copy}; in the vote a copy-slip '
                                                    'trace counts for the right trace',
                                vote='plurality over identical keys, exact vote@k, ties 1/m, null = a vote for nothing',
                                bootstrap='as v1 (paired BCa, 10,000, per-test seed from sha256)'),
                   readings=readings)
        json.dump(exp, open(os.path.join(d, 'expected.json'), 'w'), indent=1)
        summary[name] = {t: readings['official']['as_deployed'][t]['reading'] for t in readings['official']['as_deployed']}
        print(name, json.dumps(summary[name]), file=sys.stderr, flush=True)
    return summary


if __name__ == '__main__':
    # self-check: the fast vote equals v1's exact enumeration
    rng = np.random.default_rng(1)
    for _ in range(300):
        c, a, z = (int(x) for x in rng.integers(0, 15, 3))
        r = int(rng.integers(0, 40 - min(39, c + a + z) + 1)) if c + a + z < 40 else 0
        k = int(rng.integers(1, max(2, c + a + z + r) + 1))
        assert abs(vote_credit(c, a, z, r, k) - v1.vote_exact(c, a, r, z, k)) < 1e-12, (c, a, z, r, k)
    print('vote_credit matches sim_fixtures.vote_exact on 300 random count sets', file=sys.stderr)
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures', 'sim-main-v2'))
    print(json.dumps(write_all(root), indent=1))
