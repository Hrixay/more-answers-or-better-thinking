"""Run the n-step parse fixtures (n in 4, 6, 8, 12, 16) against a harness checkout (Karen). No API calls.

Usage: python3 research/fixtures/sim-main-n/run_parse_cases_n.py [REPO_ROOT]
Calls parse_trace(reply, line_count, steps=n) and parse_pieces(reply, width=n, line_count). Exit 1 on any mismatch.
The answer-only cases don't depend on n: run research/fixtures/sim-main-v2/run_parse_cases.py for those.
D-90 (Deviation 2): `expected` is the official rule (identical repeated step lines accepted). The parse cases are also
run with repeats="strict" (lock-2's rule, for the original-rule sensitivity check) against `expected_strict` where
present, else `expected`, as separate '<id> [strict]' checks. Skipped, with a note, if the parser has no `repeats`.
"""
import glob, gzip, inspect, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, root)
from harness.analysis import trace_parse as tp  # noqa: E402

fails, status = [], {}
for path in sorted(glob.glob(os.path.join(HERE, 'parse_cases_n*.jsonl.gz'))):
    for c in (json.loads(l) for l in gzip.open(path, 'rt')):
        r = tp.parse_trace(c['reply'], c['line_count'], steps=c['steps'])
        e = c['expected']
        status[c['id']] = r.status
        good = (r.status == 'ok') == e['ok'] and (e['ok'] or e.get('reason') != 'extra_line' or r.status == 'extra_line')
        if good and e['ok']:
            good = [list(x) for x in r.states] == e['states'] and list(r.answer) == e['answer']
        if not good:
            fails.append(f"{c['id']}: got {r.status} ({r.detail}); expected ok={e['ok']}")
    for c in (json.loads(l) for l in gzip.open(path, 'rt')):
        other = c['expected'].get('same_status_as')
        if other:
            a, b = status[c['id']], status[other]
            want = c['expected'].get('reason')
            if a == 'ok' or b == 'ok' or a != b or (want and a != want):
                fails.append(f"pair {c['id']} / {other}: {a} vs {b}")
STRICT = 'repeats' in inspect.signature(tp.parse_trace).parameters
if STRICT:
    for path in sorted(glob.glob(os.path.join(HERE, 'parse_cases_n*.jsonl.gz'))):
        for c in (json.loads(l) for l in gzip.open(path, 'rt')):
            r = tp.parse_trace(c['reply'], c['line_count'], steps=c['steps'], repeats='strict')
            e = c.get('expected_strict', c['expected'])
            status[c['id'] + ' [strict]'] = r.status
            good = (r.status == 'ok') == e['ok'] and (e['ok'] or not e.get('reason') == 'extra_line' or r.status == 'extra_line')
            if good and e['ok']:
                good = [list(x) for x in r.states] == e['states'] and list(r.answer) == e['answer']
            if not good:
                fails.append(f"{c['id']} [strict]: got {r.status} ({r.detail}); expected ok={e['ok']}")
for path in sorted(glob.glob(os.path.join(HERE, 'pieces_cases_n*.jsonl.gz'))):
    for c in (json.loads(l) for l in gzip.open(path, 'rt')):
        r = tp.parse_pieces(c['reply'], c['width'], c['line_count'])
        e = c['expected']
        status[c['id']] = r.status
        good = (r.status == 'ok') == e['ok']
        if good and e['ok']:
            good = {str(k): list(v) for k, v in r.entries.items()} == e['entries']
        if not good:
            fails.append(f"{c['id']}: got {r.status} ({r.detail}); expected ok={e['ok']}")
n = len(status)
print(f'{n - len(fails)} of {n} cases pass' + ('' if STRICT else ' (strict rule not checked: this parser has no '
      'repeats option)') + ('' if not fails else ':'))
for f in fails:
    print('  FAIL', f)
sys.exit(1 if fails else 0)
