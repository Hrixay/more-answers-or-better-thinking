"""Simulated main-run datasets with KNOWN true differences, for testing Friday's analysis code (Karen, OURS).

Desk simulation only: no API calls. Writes research/fixtures/sim-main-v1/<case>/{rows.jsonl.gz, expected.json} (gzip; read with gzip.open(path, 'rt')).
The tests follow D-68 (Edith's F1-F4): paired by base puzzle (n = 80), whole-answer scores, d = mean over base
puzzles of (challenger - comparator) in points, H0: d <= -10, one-sided family-wise alpha 0.025 with Holm,
paired BCa bootstrap (10,000 resamples), p by inverting the BCa bound, and a three-way reading.

| Test | Challenger                   | Comparator    | Shape |
|  1   | Haiku-medium vote at k_O     | Opus-medium   | 24x1  |
|  2   | Haiku-medium vote at k_O     | Opus-medium   | 1x24  |
|  3   | Haiku-medium vote at k_S     | Sonnet-medium | 1x24  |
|  4   | E3                           | Opus-medium   | 1x24  |
|  5   | Opus-low                     | Sonnet-medium | 1x24  |

Data model (as in research/models/study1_ni_power.py): a latent difficulty per base puzzle, shared by the two
shapes (rho_shape) and by the arms (kappa); Haiku's per-puzzle single-try accuracy p ~ Beta(4m, 4(1-m)), with
share S_SHARED of its wrong answers on one shared wrong value and the rest all different; one answer per puzzle
for Opus-medium, Opus-low, Sonnet-medium and E3. Each arm's accuracy is set so that each test's TRUE d (the
population value, refusals and truncations left out) equals the case's target.

Usage:
  python3 research/models/sim_fixtures.py            # write all cases + coverage targets
  from sim_fixtures import make_case, analyse          # Friday's size test can regenerate replicates
"""
import functools, gzip, hashlib, io, json, math, os, sys
from decimal import Decimal
import numpy as np
from scipy import integrate, stats

N_BASE = 80
N_HAIKU = 40
PRESET = 'l16'
H_MEAN = {'24x1': 0.40, '1x24': 0.25}     # Haiku-medium single-try accuracy (pooled about 0.33)
CONC = 4.0                                 # world (ii-mod)
S_SHARED = 0.20                            # share of Haiku's wrong answers on one shared wrong value
RHO_SHAPE, KAPPA = 0.5, 0.5
MARGIN = 10.0
ALPHA = 0.025
N_BOOT = 10_000
# Batch costs per call (USD), central, from research/models/study1_budget.py; 24x1 prompts are about 8% longer
COST = {'haiku-med': 0.00388, 'opus-med': 0.00388 * 29.7, 'sonnet-med': 0.00388 * 14.6,
        'opus-low': 0.0533, 'e3': 0.0396}
SHAPE_COST = {'24x1': 1.08, '1x24': 1.0}
TRUNC_COST = {'opus-med': 0.33, 'sonnet-med': 0.165, 'opus-low': 0.33, 'haiku-med': 0.0125}  # max_tokens hit
TESTS = [
    ('t1', 'vote_kO', 'opus-med', '24x1'),
    ('t2', 'vote_kO', 'opus-med', '1x24'),
    ('t3', 'vote_kS', 'sonnet-med', '1x24'),
    ('t4', 'e3', 'opus-med', '1x24'),
    ('t5', 'opus-low', 'sonnet-med', '1x24'),
]
CASES = {
    'ni':  dict(seed=1101, d={'t1': 12, 't2': 12, 't3': 12, 't4': 12, 't5': 12}),
    'd0':  dict(seed=1102, d={t[0]: 0 for t in TESTS}),
    'd-5': dict(seed=1103, d={t[0]: -5 for t in TESTS}),
    'd-10': dict(seed=1104, d={t[0]: -10 for t in TESTS}),
    'd-15': dict(seed=1105, d={t[0]: -15 for t in TESTS}),
    'worse': dict(seed=1107, d={'t1': -15, 't2': -30, 't3': -30, 't4': -30, 't5': -30}),
    'mixed': dict(seed=1106, d={'t1': 12, 't2': 0, 't3': -5, 't4': -10, 't5': -15},
                  opus_refusals=4, opus_low_refusals=1, sonnet_truncations=2, haiku_unparseable=0.01,
                  haiku_truncated=0.005, haiku_steps=True),
}


def gz_writer(path):
    """A text writer for a .gz file with a fixed header (mtime 0), so re-generation is byte-identical (Edith K2-4)."""
    return io.TextIOWrapper(gzip.GzipFile(path, 'wb', compresslevel=9, mtime=0), encoding='utf-8')


# ------------------------------------------------------------------ the vote@k estimator (exact)
@functools.lru_cache(maxsize=None)
def vote_exact(c, a, r, z, k):
    """Expected vote@k credit over all k-subsets of n = c+a+r+z samples: c right answers, a copies of one
    shared wrong value, r wrong answers all different, z null answers (unparseable/refused/truncated: a vote
    for nothing). Plurality; a tie among m answers that includes the right one scores 1/m (D-33)."""
    n = c + a + r + z
    k = min(k, n)
    if k <= 0:
        return 0.0
    tot = math.comb(n, k)
    s = 0.0
    for x in range(1, min(c, k) + 1):
        for y in range(0, min(a, k - x) + 1):
            for w in range(0, min(z, k - x - y) + 1):
                rest = k - x - y - w
                if rest > r:
                    continue
                if x >= 2:
                    cr = 1.0 if x > y else (0.5 if x == y else 0.0)
                else:  # x == 1
                    cr = 0.0 if y >= 2 else 1.0 / (k - w)
                if cr:
                    s += cr * math.comb(c, x) * math.comb(a, y) * math.comb(z, w) * math.comb(r, rest)
    return s / tot


@functools.lru_cache(maxsize=None)
def expected_vote(m, k, conc=CONC, shared=S_SHARED, n=N_HAIKU):
    """Population vote@k accuracy when p ~ Beta(conc*m, conc*(1-m)): exact over the binomials, quadrature
    over p."""
    tab = np.zeros((n + 1, n + 1))
    for c in range(n + 1):
        for a in range(n + 1 - c):
            tab[c, a] = vote_exact(c, a, n - c - a, 0, k)
    def f(p):
        pc = stats.binom.pmf(np.arange(n + 1), n, p)
        tot = 0.0
        for c in range(n + 1):
            if pc[c] < 1e-15:
                continue
            pa = stats.binom.pmf(np.arange(n + 1 - c), n - c, shared)
            tot += pc[c] * float(pa @ tab[c, :n + 1 - c])
        return tot * stats.beta.pdf(p, conc * m, conc * (1 - m))
    return integrate.quad(f, 0, 1, limit=200, epsabs=1e-7)[0]


# ------------------------------------------------------------------ BCa (paired, base-puzzle bootstrap)
def test_seed(base_seed, name):
    return int(hashlib.sha256(f'{base_seed}:{name}'.encode()).hexdigest()[:15], 16)


def bca(D, seed, n_boot=N_BOOT):
    """D: per-base-puzzle differences (points). Returns the bootstrap means, z0 and the acceleration."""
    rng = np.random.default_rng(seed)
    n = len(D)
    idx = rng.integers(0, n, size=(n_boot, n))
    th = D[idx].mean(1)
    est = D.mean()
    prop = np.clip(np.mean(th < est), 1 / (n_boot + 1), n_boot / (n_boot + 1))
    z0 = stats.norm.ppf(prop)
    jack = (D.sum() - D) / (n - 1)
    dj = jack.mean() - jack
    den = 6 * (np.sum(dj ** 2)) ** 1.5
    acc = float(np.sum(dj ** 3) / den) if den > 0 else 0.0
    return th, float(z0), acc


def bca_bound(th, z0, acc, alpha, upper=False):
    za = stats.norm.ppf(1 - alpha if upper else alpha)
    q = stats.norm.cdf(z0 + (z0 + za) / (1 - acc * (z0 + za)))
    return float(np.quantile(th, q))


def bca_p(th, z0, acc, m=-MARGIN):
    """One-sided p for H0: d <= m, by inverting the BCa lower bound (the alpha at which the bound equals m)."""
    nb = len(th)
    g = np.clip(np.mean(th <= m), 1 / (nb + 1), nb / (nb + 1))
    w = stats.norm.ppf(g) - z0
    u = w / (1 + acc * w)
    return float(stats.norm.cdf(u - z0))


def analyse(scores, base_seed, n_boot=N_BOOT):
    """scores: test -> per-base-puzzle (challenger, comparator) arrays (aligned; NaN = left out).
    Returns per-test results with Holm and the three-way reading (D-68 F2)."""
    res = {}
    for name, (ch, co) in scores.items():
        keep = ~(np.isnan(ch) | np.isnan(co))
        D = (ch[keep] - co[keep]) * 100
        th, z0, acc = bca(D, test_seed(base_seed, name), n_boot)
        res[name] = dict(n=int(keep.sum()), d_hat=round(float(D.mean()), 3), p=bca_p(th, z0, acc),
                         ci95=[bca_bound(th, z0, acc, 0.025), bca_bound(th, z0, acc, 0.025, upper=True)],
                         z0=z0, acc=acc, _th=th)
    order = sorted(res, key=lambda t: res[t]['p'])
    passed = True
    for j, t in enumerate(order, start=1):
        thr = ALPHA / (6 - j)
        r = res[t]
        r['holm_step'], r['holm_threshold'] = j, thr
        r['lower_bound_at_step'] = bca_bound(r['_th'], r['z0'], r['acc'], thr)
        ni = passed and r['p'] <= thr
        passed = ni
        worse = r['ci95'][1] < -MARGIN
        r['reading'] = 'non-inferior' if ni else ('worse by more than the margin' if worse else 'inconclusive')
        r['near_threshold'] = bool(abs(r['p'] - thr) < 0.2 * thr or abs(r['ci95'][1] + MARGIN) < 0.5)
    for r in res.values():
        r.pop('_th')
        for key in ('p', 'z0', 'acc', 'lower_bound_at_step'):
            r[key] = round(r[key], 6)
        r['ci95'] = [round(v, 3) for v in r['ci95']]
    return res


# ------------------------------------------------------------------ data generation
def _key(*parts):
    return hashlib.sha1('|'.join(map(str, parts)).encode()).hexdigest()[:16]


def _cost(rng, setup, shape, kind='answered'):
    if kind == 'refusal':
        return Decimal('0')
    base = TRUNC_COST[setup] if kind == 'truncated' else COST[setup] * SHAPE_COST[shape]
    return Decimal(f'{base * (1 + rng.uniform(-0.01, 0.01)):.6f}')


def k_from_costs(rows, shape, num_setup):
    num = [float(r['cost_usd']) for r in rows if r['shape'] == shape and r['setup'] == num_setup]
    den = [float(r['cost_usd']) for r in rows if r['shape'] == shape and r['setup'] == 'haiku-med']
    return min(N_HAIKU, int(math.floor(np.mean(num) / np.mean(den))))


def make_case(name, seed, d, opus_refusals=0, opus_low_refusals=0, sonnet_truncations=0, haiku_unparseable=0.0,
              haiku_truncated=0.0, haiku_steps=False, write_rows=True):
    rng = np.random.default_rng(seed)
    set_id = f'simfix-{name}-v1'
    bases = [f'b{i:03d}' for i in range(N_BASE)]
    rows = []
    # latent difficulty (low = easy): base, shape, arm
    Lb = rng.standard_normal(N_BASE)
    Ls = {s: math.sqrt(RHO_SHAPE) * Lb + math.sqrt(1 - RHO_SHAPE) * rng.standard_normal(N_BASE) for s in H_MEAN}
    def arm_latent(s):
        return KAPPA * Ls[s] + math.sqrt(1 - KAPPA ** 2) * rng.standard_normal(N_BASE)
    eta = {(arm, s): arm_latent(s) for s in H_MEAN for arm in ('haiku-med', 'opus-med', 'opus-low', 'sonnet-med', 'e3')}
    # costs first (k is set from costs, as the k script does); 1 row of each single arm per puzzle
    # true vote accuracies at the k the costs imply (computed after the rows exist; fixed here by design)
    p_h = {s: stats.beta.ppf(1 - stats.norm.cdf(eta[('haiku-med', s)]), CONC * H_MEAN[s], CONC * (1 - H_MEAN[s]))
           for s in H_MEAN}
    # placeholder rows for costs so k can be computed exactly as the k script will
    cost_rows = []
    for s in H_MEAN:
        for b_i, b in enumerate(bases):
            for setup in ('opus-med', 'sonnet-med'):
                kind = 'answered'
                cost_rows.append(dict(shape=s, setup=setup, base_id=b, kind=kind,
                                      cost_usd=str(_cost(rng, setup, s))))
            for t in range(N_HAIKU):
                u = rng.random()
                kind = 'answered'
                if s == '1x24' and u < haiku_truncated:
                    kind = 'truncated'
                elif s == '1x24' and u < haiku_truncated + haiku_unparseable:
                    kind = 'unparseable'
                cost_rows.append(dict(shape=s, setup='haiku-med', base_id=b, kind=kind,
                                      cost_usd=str(_cost(rng, 'haiku-med', s, kind))))
    # special rows (refusals, truncations) chosen now so their costs enter k
    pick = lambda n: set(rng.choice(N_BASE, size=n, replace=False).tolist()) if n else set()
    om_ref = pick(opus_refusals)            # Opus-medium refusals, 1x24
    ol_ref = pick(opus_low_refusals)        # Opus-low refusals, 1x24
    sm_tr = pick(sonnet_truncations)        # Sonnet-medium truncations, 1x24
    for r in cost_rows:
        b_i = int(r['base_id'][1:])
        if r['shape'] == '1x24' and r['setup'] == 'opus-med' and b_i in om_ref:
            r['cost_usd'] = '0'
        if r['shape'] == '1x24' and r['setup'] == 'sonnet-med' and b_i in sm_tr:
            r['cost_usd'] = str(_cost(rng, 'sonnet-med', '1x24', 'truncated'))
    kO = {s: k_from_costs(cost_rows, s, 'opus-med') for s in H_MEAN}
    kS = {s: k_from_costs(cost_rows, s, 'sonnet-med') for s in H_MEAN}
    # target accuracies from the true d's (population, left-out view)
    EV = {('O', s): expected_vote(H_MEAN[s], kO[s]) for s in H_MEAN}
    EV[('S', '1x24')] = expected_vote(H_MEAN['1x24'], kS['1x24'])
    acc = {}
    acc[('opus-med', '24x1')] = EV[('O', '24x1')] - d['t1'] / 100
    acc[('opus-med', '1x24')] = EV[('O', '1x24')] - d['t2'] / 100
    acc[('sonnet-med', '1x24')] = EV[('S', '1x24')] - d['t3'] / 100
    acc[('e3', '1x24')] = acc[('opus-med', '1x24')] + d['t4'] / 100
    acc[('opus-low', '1x24')] = acc[('sonnet-med', '1x24')] + d['t5'] / 100
    # arms only needed for exploratory views get a plausible accuracy
    acc[('sonnet-med', '24x1')] = min(0.97, EV[('S', '1x24')] + 0.25)
    acc[('opus-low', '24x1')] = min(0.97, acc[('opus-med', '24x1')] - 0.03)
    acc[('e3', '24x1')] = min(0.97, acc[('opus-med', '24x1')])
    for kk, v in acc.items():
        if not 0.02 <= v <= 0.995:
            raise ValueError(f'case {name}: accuracy {kk} = {v:.3f} out of range; change H_MEAN or d')
    if not write_rows:
        return dict(p_h=p_h, eta=eta, acc=acc, kO=kO, kS=kS, EV=EV, rng=rng,
                    om_ref=om_ref, ol_ref=ol_ref, sm_tr=sm_tr)
    # ---- rows
    cost_iter = iter(cost_rows)
    def step_list(correct, rng):
        if correct:
            st = [True] * 24
            if rng.random() < 0.03:               # an absorbed rejoin or a copying slip in the step lines
                st[int(rng.integers(0, 24))] = False
            return st
        s0 = int(rng.integers(0, 24))
        return [i < s0 for i in range(24)]
    counts = {}
    for s in H_MEAN:
        for b_i, b in enumerate(bases):
            right = _key(set_id, b, s, 'right')
            for setup in ('opus-med', 'sonnet-med'):
                cr = next(cost_iter)
                assert cr['base_id'] == b and cr['setup'] == setup and cr['shape'] == s
                ok = bool(eta[(setup, s)][b_i] < stats.norm.ppf(acc[(setup, s)]))
                kind, stop, cat = 'answered', 'end_turn', None
                if s == '1x24' and setup == 'opus-med' and b_i in om_ref:
                    kind, stop, cat = 'refusal', 'refusal', 'cyber'
                if s == '1x24' and setup == 'sonnet-med' and b_i in sm_tr:
                    kind, stop = 'truncated', 'max_tokens'
                row = dict(set_id=set_id, preset=PRESET, base_id=b, shape=s, setup=setup, try_=0, kind=kind,
                           stop_reason=stop, refusal_category=cat,
                           answer_key=(right if ok else _key(set_id, b, s, setup, 'wrong')) if kind == 'answered' else None,
                           correct=bool(ok and kind == 'answered'), cost_usd=cr['cost_usd'],
                           _latent_correct=ok)
                if s == '1x24':
                    row['step_correct'] = step_list(ok, rng) if kind == 'answered' else None
                rows.append(row)
            for setup in ('opus-low', 'e3'):
                ok = bool(eta[(setup, s)][b_i] < stats.norm.ppf(acc[(setup, s)]))
                kind, stop, cat = 'answered', 'end_turn', None
                if s == '1x24' and setup == 'opus-low' and b_i in ol_ref:
                    kind, stop, cat = 'refusal', 'refusal', 'cyber'
                row = dict(set_id=set_id, preset=PRESET, base_id=b, shape=s, setup=setup, try_=0, kind=kind,
                           stop_reason=stop, refusal_category=cat,
                           answer_key=(right if ok else _key(set_id, b, s, setup, 'wrong')) if kind == 'answered' else None,
                           correct=bool(ok and kind == 'answered'),
                           cost_usd=str(_cost(rng, setup, s, kind)), _latent_correct=ok)
                if setup == 'e3':
                    if ok:
                        st = [True] * 24
                    else:
                        st = [True] * 24
                        for j in rng.choice(24, size=int(rng.integers(1, 4)), replace=False):
                            st[int(j)] = False
                    row['step_correct'] = st
                elif s == '1x24':
                    row['step_correct'] = step_list(ok, rng) if kind == 'answered' else None
                rows.append(row)
            # Haiku-medium x40
            c = a = r = z = zt = 0
            for t in range(N_HAIKU):
                cr = next(cost_iter)
                assert cr['setup'] == 'haiku-med' and cr['base_id'] == b
                kind = cr['kind']
                stop = 'max_tokens' if kind == 'truncated' else 'end_turn'
                ok = bool(rng.random() < p_h[s][b_i])
                if kind != 'answered':
                    key = None
                    if kind == 'truncated':
                        zt += 1
                    else:
                        z += 1
                elif ok:
                    key = right; c += 1
                elif rng.random() < S_SHARED:
                    key = _key(set_id, b, s, 'shared-wrong'); a += 1
                else:
                    key = _key(set_id, b, s, 'wrong', t); r += 1
                row = dict(set_id=set_id, preset=PRESET, base_id=b, shape=s, setup='haiku-med', try_=t, kind=kind,
                           stop_reason=stop, refusal_category=None, answer_key=key, correct=bool(kind == 'answered' and ok),
                           cost_usd=cr['cost_usd'])
                if haiku_steps and s == '1x24':
                    row['step_correct'] = step_list(ok, rng) if kind == 'answered' else None
                rows.append(row)
            counts[(b, s)] = (c, a, r, z, zt)
    for row in rows:
        row['try'] = row.pop('try_')
    for sh in H_MEAN:   # the k script, run on the written rows, must give the k the accuracies were set for
        assert k_from_costs(rows, sh, 'opus-med') == kO[sh] and k_from_costs(rows, sh, 'sonnet-med') == kS[sh]
    return dict(rows=rows, counts=counts, kO=kO, kS=kS, EV=EV, acc=acc)


def scores_for(case, view='as_deployed'):
    """Per-base-puzzle scores for each test. view: as_deployed | refusals_left_out | truncations_left_out."""
    rows, counts = case['rows'], case['counts']
    single = {}
    for r in rows:
        if r['setup'] != 'haiku-med':
            single[(r['setup'], r['shape'], r['base_id'])] = r
    bases = sorted({r['base_id'] for r in rows})
    def single_score(setup, shape, b):
        r = single[(setup, shape, b)]
        if view == 'refusals_left_out' and r['kind'] == 'refusal':
            return np.nan
        if view == 'truncations_left_out' and r['kind'] == 'truncated':
            return np.nan
        return 1.0 if r['correct'] else 0.0
    def vote_score(shape, b, k):
        c, a, rr, z, zt = counts[(b, shape)]
        if view == 'truncations_left_out':
            return vote_exact(c, a, rr, z, k)            # truncated samples dropped, k capped at what is left
        return vote_exact(c, a, rr, z + zt, k)            # a truncated sample is a vote for nothing
    out = {}
    for name, chal, comp, shape in TESTS:
        ch, co = [], []
        for b in bases:
            if chal == 'vote_kO':
                ch.append(vote_score(shape, b, case['kO'][shape]))
            elif chal == 'vote_kS':
                ch.append(vote_score(shape, b, case['kS'][shape]))
            else:
                ch.append(single_score(chal, shape, b))
            co.append(single_score(comp, shape, b))
        out[name] = (np.array(ch, float), np.array(co, float))
    return out


def coverage(case_name='d-10', reps=200, n_boot=N_BOOT, seed0=500000):
    """Size and coverage at true d = -10 for every test, over `reps` regenerated datasets."""
    cfg = CASES[case_name]
    hits = {t[0]: dict(rej_025=0, rej_005=0, cover95=0, ni_holm=0) for t in TESTS}
    any_holm = 0
    for i in range(reps):
        case = make_case(case_name, seed0 + i, cfg['d'])
        res = analyse(scores_for(case), seed0 + i, n_boot)
        anyni = False
        for t, r in res.items():
            true_d = cfg['d'][t]
            hits[t]['rej_025'] += r['p'] <= 0.025
            hits[t]['rej_005'] += r['p'] <= 0.005
            hits[t]['cover95'] += r['ci95'][0] <= true_d <= r['ci95'][1]
            hits[t]['ni_holm'] += r['reading'] == 'non-inferior'
            anyni |= r['reading'] == 'non-inferior'
        any_holm += anyni
        print(f'coverage rep {i}', file=sys.stderr, flush=True) if i % 20 == 0 else None
    return dict(case=case_name, reps=reps, n_boot=n_boot, seeds=f'{seed0}..{seed0 + reps - 1}', per_test=hits,
                familywise_any_non_inferior=any_holm)


def write_all(root):
    os.makedirs(root, exist_ok=True)
    summary = {}
    for name, cfg in CASES.items():
        extra = {k: v for k, v in cfg.items() if k not in ('seed', 'd')}
        case = make_case(name, cfg['seed'], cfg['d'], **extra)
        rows = [{k: v for k, v in r.items() if not k.startswith('_')} for r in case['rows']]
        d = os.path.join(root, name)
        os.makedirs(d, exist_ok=True)
        with gz_writer(os.path.join(d, 'rows.jsonl.gz')) as f:
            for r in rows:
                f.write(json.dumps(r, separators=(',', ':')) + '\n')
        views = {}
        for view in ('as_deployed', 'refusals_left_out', 'truncations_left_out'):
            views[view] = analyse(scores_for(case, view), cfg['seed'])
        acc_obs = {}
        for setup in ('opus-med', 'opus-low', 'sonnet-med', 'e3'):
            for s in H_MEAN:
                v = [r['correct'] for r in rows if r['setup'] == setup and r['shape'] == s]
                acc_obs[f'{setup}/{s}'] = round(float(np.mean(v)), 4)
        exp = dict(case=name, set_id=f'simfix-{name}-v1', seed=cfg['seed'], n_base=N_BASE, haiku_tries=N_HAIKU,
                   true_d_left_out=cfg['d'],
                   k={'opus_matched': case['kO'], 'sonnet_matched_1x24': case['kS']['1x24']},
                   population_vote_accuracy={f'{w}/{s}': round(v, 5) for (w, s), v in case['EV'].items()},
                   target_accuracy={f'{a}/{s}': round(v, 5) for (a, s), v in case['acc'].items()},
                   observed_accuracy=acc_obs, special_rows={k: v for k, v in extra.items()},
                   method=dict(bootstrap='paired base-puzzle BCa', n_boot=N_BOOT,
                               test_seed='int(sha256(f"{seed}:{test}").hexdigest()[:15], 16)',
                               p='invert the BCa lower bound at the margin -10',
                               holm='one-sided family alpha 0.025; step j threshold 0.025/(6-j)',
                               worse='two-sided 95% BCa upper end below -10',
                               vote='exact expected vote@k over k-subsets; null answers vote for nothing; '
                                    'truncations_left_out drops truncated samples and caps k at what is left'),
                   readings=views)
        json.dump(exp, open(os.path.join(d, 'expected.json'), 'w'), indent=1)
        summary[name] = {t: views['as_deployed'][t]['reading'] for t in views['as_deployed']}
        print(name, json.dumps(summary[name]), file=sys.stderr, flush=True)
    return summary


if __name__ == '__main__':
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures', 'sim-main-v1')
    root = os.path.normpath(root)
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode in ('all', 'cases'):
        print(json.dumps(write_all(root), indent=1))
    if mode in ('all', 'coverage'):
        reps = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        cov = coverage(reps=reps)
        json.dump(cov, open(os.path.join(root, 'coverage-d-10.json'), 'w'), indent=1)
        print(json.dumps(cov, indent=1))
