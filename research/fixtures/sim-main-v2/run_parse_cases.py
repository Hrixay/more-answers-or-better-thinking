"""Run the D-76 parse fixtures against a checkout of the harness (Karen). No API calls.

Usage: python3 research/fixtures/sim-main-v2/run_parse_cases.py [REPO_ROOT]
REPO_ROOT is a checkout holding harness/analysis/trace_parse.py (default: this repository). Exit code 1 on any mismatch.

Checks, per file (all in this folder):
  parse_cases.jsonl.gz  parse_trace(reply, line_count): ok must match; when ok, states and answer must match.
                        Round 1 (148) plus round 2 (ids with '-r2-').
  parse_cases_d90.jsonl.gz  the same check, D-90's repeat cases (ids with '-d90-').
  pieces_cases.jsonl.gz parse_pieces(reply, width, line_count): ok must match; when ok, entries must match.
  final_cases.jsonl.gz  parse_final(reply, line_count) (the answer-only fallback): ok, and the answer when ok.
  Pairs marked same_status_as must both be not ok and give the same status; an expected `reason` of non_integer is
  checked exactly for those pairs (elsewhere reasons are advisory).
D-90 (Deviation 2): `expected` is the official rule (identical repeated step lines accepted). The parse cases are also
run with repeats="strict" (lock-2's rule, kept for the original-rule sensitivity check) against `expected_strict` where
present, else `expected`; counted as separate '<id> [strict]' checks. Skipped, with a note, if the parser has no
`repeats` option.
"""
import gzip, inspect, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, root)
from harness.analysis import trace_parse as tp  # noqa: E402


def load(name):
    return [json.loads(l) for l in gzip.open(os.path.join(HERE, name), 'rt')]


fails, status = [], {}
PARSE = load('parse_cases.jsonl.gz') + load('parse_cases_d90.jsonl.gz')
for c in PARSE:
    r = tp.parse_trace(c['reply'], c['line_count'])
    e = c['expected']
    status[c['id']] = r.status
    good = (r.status == 'ok') == e['ok'] and (e['ok'] or e.get('reason') != 'extra_line' or r.status == 'extra_line')
    if good and e['ok']:
        good = [list(x) for x in r.states] == e['states'] and list(r.answer) == e['answer']
    if not good:
        fails.append(f"{c['id']}: got {r.status} ({r.detail}); expected ok={e['ok']}")
STRICT = 'repeats' in inspect.signature(tp.parse_trace).parameters
if STRICT:
    for c in PARSE:
        r = tp.parse_trace(c['reply'], c['line_count'], repeats='strict')
        e = c.get('expected_strict', c['expected'])
        status[c['id'] + ' [strict]'] = r.status
        good = (r.status == 'ok') == e['ok'] and (e['ok'] or not e.get('reason') == 'extra_line' or r.status == 'extra_line')
        if good and e['ok']:
            good = [list(x) for x in r.states] == e['states'] and list(r.answer) == e['answer']
        if not good:
            fails.append(f"{c['id']} [strict]: got {r.status} ({r.detail}); expected ok={e['ok']}")
for c in load('pieces_cases.jsonl.gz'):
    r = tp.parse_pieces(c['reply'], c['width'], c['line_count'])
    e = c['expected']
    status[c['id']] = r.status
    good = (r.status == 'ok') == e['ok']
    if good and e['ok']:
        good = {str(k): list(v) for k, v in r.entries.items()} == e['entries']
    if not good:
        fails.append(f"{c['id']}: got {r.status} ({r.detail}); expected ok={e['ok']}")
for c in load('final_cases.jsonl.gz'):
    st, ans = tp.parse_final(c['reply'], c['line_count'])
    e = c['expected']
    status[c['id']] = st
    good = (st == 'ok') == e['ok'] and (not e['ok'] or list(ans) == e['answer'])
    if not good:
        fails.append(f"{c['id']}: got {st}; expected ok={e['ok']}")
for name in ('parse_cases.jsonl.gz', 'final_cases.jsonl.gz'):
    for c in load(name):
        other = c['expected'].get('same_status_as')
        if not other:
            continue
        a, b = status[c['id']], status[other]
        want = c['expected'].get('reason')
        if a == 'ok' or b == 'ok' or a != b or (want and a != want):
            fails.append(f"pair {c['id']} / {other}: {a} vs {b} (want both not ok, equal{', ' + want if want else ''})")
n = len(status)
print(f'{n - len(fails)} of {n} cases pass' + ('' if STRICT else ' (strict rule not checked: this parser has no '
      'repeats option)') + ('' if not fails else ':'))
for f in fails:
    print('  FAIL', f)
sys.exit(1 if fails else 0)
