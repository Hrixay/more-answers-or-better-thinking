"""Study 1, H1 non-inferiority power (Karen, OURS). Mock-review fix 3, plus the refusal views of fix 4.

Desk simulation only: no API calls. It reuses the method of the 2026-10-10 precision check
(decisions/briefings/2026-10-10-study1-design-check/analyse-precision.md, scratch sim.py):
- a latent difficulty per base puzzle, shared between Haiku and Opus with latent correlation KAPPA;
- Haiku's per-puzzle single-try accuracy p_b: constant in world (i), Beta-distributed in worlds (ii);
- 40 Haiku-medium samples per puzzle; vote@k = the exact average over all k-subsets of the 40
  (D-33's estimator), plurality vote, random tie-break at expected credit 1/m;
- one Opus-medium answer per puzzle.

Per shape, one puzzle per base puzzle (B = 80 as ruled, or 120). Test per shape: the per-puzzle
difference D = vote@k - Opus; a t interval across base puzzles (close to the paired BCa bootstrap of
D-68 F4). Readings (D-68 F2), margin M:
  non-inferior if the lower bound at level L is above -M (L = 95% two-sided, i.e. one-sided 0.025, or
  99%, i.e. one-sided 0.005 = Holm's strictest step); worse by more than the margin if the unadjusted
  two-sided 95% upper end is below -M; otherwise inconclusive.
Levels: 95% two-sided (one-sided 0.025, nominal) and 99% (one-sided 0.005 = 0.025/5, Holm's
strictest step across the five tests).

Worlds (mean Haiku single-try accuracy m):
  (i)       every puzzle at m, wrong answers never coincide;
  (ii-mod)  p_b ~ Beta(4m, 4(1-m))  (sd 0.21 at m = .3);
  (ii-high) p_b ~ Beta(m, 1-m)      (sd 0.32 at m = .3);
  (iii)     (ii-mod), plus 30% of wrong answers land on one shared wrong value (sensitivity).

Run: python3 research/models/study1_ni_power.py [nsim]  -> prints tables, writes ni_power_results.json
"""
import itertools, json, math, os, sys
import numpy as np
from scipy import stats

NSIM = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4000
SEED = 20261011
N_SAMPLES = 40
KS = [15, 20, 25, 30, 35]
P_OPUS = [0.60, 0.70, 0.80, 0.90, 0.95, 0.98]
H_MEANS = [0.25, 0.375, 0.50]
WORLDS = {'i': (None, 0.0), 'ii-mod': (4.0, 0.0), 'ii-high': (1.0, 0.0), 'iii': (4.0, 0.3)}
B_MAX, B_LIST = 120, [80, 120]
KAPPA = 0.5
LEVELS = {'95': 0.05, '99': 0.01}
MARGINS = [10, 5]


def vote_table(k, n=N_SAMPLES):
    """T[c, a] = expected vote@k credit over all k-subsets of n samples holding c right answers,
    a copies of one shared wrong value, and n-c-a wrong answers that are all different."""
    T = np.zeros((n + 1, n + 1))
    tot = math.comb(n, k)
    for c in range(n + 1):
        for a in range(n + 1 - c):
            r = n - c - a
            s = 0.0
            for x in range(min(c, k) + 1):
                for y in range(min(a, k - x) + 1):
                    if k - x - y > r:
                        continue
                    if x >= 2:
                        cr = 1.0 if x > y else (0.5 if x == y else 0.0)
                    elif x == 1:
                        cr = 0.0 if y >= 2 else 1.0 / k
                    else:
                        cr = 0.0
                    if cr:
                        s += cr * math.comb(c, x) * math.comb(a, y) * math.comb(r, k - x - y)
            T[c, a] = s / tot
    return T


VT = {k: vote_table(k) for k in KS}


def haiku_p(u, conc, m):
    """u in (0,1), low u = easy. Returns per-puzzle single-try accuracy."""
    if conc is None:
        return np.full(u.shape, m)
    return stats.beta.ppf(1 - u, m * conc, (1 - m) * conc)


def draw(world, m, nsim, B, kappa, rng):
    conc, shared = WORLDS[world]
    z = rng.standard_normal((nsim, B, 2))
    eta_h = z[..., 0]
    eta_o = kappa * z[..., 0] + math.sqrt(1 - kappa ** 2) * z[..., 1]
    p = haiku_p(stats.norm.cdf(eta_h), conc, m)
    c = rng.binomial(N_SAMPLES, p)
    a = rng.binomial(N_SAMPLES - c, shared) if shared else np.zeros_like(c)
    return eta_o, c, a


def readings(D, level, margin):
    """D-68 F2: non-inferior if the lower bound at `level` (two-sided; one-sided level/2) is above -margin;
    worse by more than the margin if the unadjusted two-sided 95% interval's upper end is below -margin."""
    B = D.shape[1]
    mean = D.mean(1)
    se = D.std(1, ddof=1) / math.sqrt(B)
    t = stats.t.ppf(1 - level / 2, B - 1)
    t95 = stats.t.ppf(0.975, B - 1)
    lo, hi = mean - t * se, mean + t95 * se
    ni = lo > -margin / 100
    inf = (hi < -margin / 100) & ~ni
    return dict(ni=float(ni.mean()), inferior=float(inf.mean()), inconclusive=float((~ni & ~inf).mean()),
                half_width=float((t * se).mean() * 100))


def true_values(world, m, k, p_o, kappa, rng, n=400000):
    eta_o, c, a = draw(world, m, 1, n, kappa, rng)
    v = VT[k][c, a].mean()
    return float(v), float(v - p_o)


def main():
    rng = np.random.default_rng(SEED)
    out = []
    for world, m in itertools.product(WORLDS, H_MEANS):
        eta_o, c, a = draw(world, m, NSIM, B_MAX, KAPPA, rng)
        trng = np.random.default_rng(SEED + 1)
        for k in KS:
            V = VT[k][c, a]
            v_true = true_values(world, m, k, 0.0, KAPPA, trng)[0]
            for p_o in P_OPUS:
                O = (eta_o < stats.norm.ppf(p_o)).astype(float)
                D = V - O
                gap = v_true - p_o
                for B in B_LIST:
                    for lvl, al in LEVELS.items():
                        for mg in MARGINS:
                            r = readings(D[:, :B], al, mg)
                            out.append(dict(world=world, h_mean=m, k=k, p_opus=p_o, B=B, level=lvl, margin=mg,
                                            vote_true=round(v_true, 4), gap_true=round(gap * 100, 1),
                                            err_ratio=round((1 - v_true) / (1 - p_o), 2), **r))
        print(f'done {world} m={m}', file=sys.stderr, flush=True)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ni_power_results.json')
    json.dump(dict(seed=SEED, nsim=NSIM, kappa=KAPPA, rows=out), open(path, 'w'), indent=0)
    return out


def refusal_views(world='ii-mod', m=0.25, k=30, p_o=0.95, B=80, refusals=(0, 2, 3, 4, 6), nsim=NSIM,
                  level=0.01, margin=10, kappa=KAPPA):
    """Fix 4: r Opus refusals at random puzzles. As deployed: a refusal is wrong. Left out: the refused
    base puzzle is dropped from the paired contrast. Returns the mean estimated gap and the readings."""
    rng = np.random.default_rng(SEED + 7)
    eta_o, c, a = draw(world, m, nsim, B, kappa, rng)
    V = VT[k][c, a]
    O = (eta_o < stats.norm.ppf(p_o)).astype(float)
    res = []
    for r in refusals:
        idx = np.argsort(rng.random((nsim, B)), axis=1)[:, :r]
        mask = np.zeros((nsim, B), bool)
        np.put_along_axis(mask, idx, True, axis=1)
        O_dep = np.where(mask, 0.0, O)
        D_dep = V - O_dep
        rd = readings(D_dep, level, margin)
        # left out: per simulated study, drop the r refused base puzzles
        D_all = V - O
        keep = ~mask
        D_lo = D_all[keep].reshape(nsim, B - r)
        rl = readings(D_lo, level, margin)
        # joint: a match as deployed that fails with the refusals left out (what D-68 F3 guards against)
        def ni_mask(Dm):
            Bm = Dm.shape[1]
            se = Dm.std(1, ddof=1) / math.sqrt(Bm)
            return Dm.mean(1) - stats.t.ppf(1 - level / 2, Bm - 1) * se > -margin / 100
        dep_only = float((ni_mask(D_dep) & ~ni_mask(D_lo)).mean())
        res.append(dict(refusals=r, shift_points=round(float((D_dep.mean(1) - D_lo.mean(1)).mean() * 100), 2),
                        ni_deployed=round(rd['ni'], 3), ni_left_out=round(rl['ni'], 3),
                        match_only_as_deployed=round(dep_only, 3)))
    return res


# ------------------------------------------------------------------ D-72: the post-pilot re-run (locked)
# Pinned for the lock (D-69, D-72, Edith's conditions in ops/reviews/2026-10-11-power-cutorder-house-T.md):
D72 = dict(seed=SEED, nsim=4000, kappa=KAPPA, B=80, B_add=120, level=0.01, margin=10, threshold=0.5,
           n_samples=N_SAMPLES)


def d72_inputs(haiku_correct, haiku_tries, wrong_pairs_agree, wrong_pairs, opus_correct):
    """The measured inputs, all from the pilot at the CHOSEN preset, 1x24 puzzles only, as-deployed scoring.
    haiku_correct[b], haiku_tries[b]: Haiku-medium whole-answer right tries and tries per pilot puzzle (10);
    wrong_pairs_agree, wrong_pairs: pooled over puzzles, the pairs of wrong Haiku tries giving the same
      final answer, and all pairs of wrong tries (pairwise agreement, as in the fairness check);
    opus_correct[b]: Opus-medium's one answer per puzzle, 1 = right (a refusal or truncation is 0).
    Returns m (mean single try), conc (Beta concentration; None = no spread), shared (repeat share), p_opus."""
    p = np.asarray(haiku_correct, float) / np.asarray(haiku_tries, float)
    n = float(np.mean(haiku_tries))
    m = float(p.mean())
    e_pq = float(np.mean(p * (1 - p))) * n / (n - 1)          # unbiased E[p(1-p)] from binomial tries
    var_p = float(p.var(ddof=1)) - e_pq / n                    # spread between puzzles, binomial noise removed
    conc = None if var_p <= 0 else float(np.clip(m * (1 - m) / var_p - 1, 0.5, 200.0))
    agree = wrong_pairs_agree / wrong_pairs if wrong_pairs else 0.0
    shared = float(np.sqrt(agree))                             # in the model, two wrong tries agree w.p. s^2
    p_o = float(np.clip(np.mean(opus_correct), 0.5, 0.99))
    return dict(m=float(np.clip(m, 0.02, 0.98)), conc=conc, shared=shared, p_opus=p_o)


def d72_rerun(inputs, k):
    """Chance of each reading for test 2 (Haiku-medium vote at k vs Opus-medium, 1x24) at 80 and 120 base
    puzzles, at Holm's strictest step (one-sided 0.005), margin 10. Decision (power part only): add 40 base
    puzzles at 1x24 if P(conclusive) at 80 < 0.5. The budget test ($170 high case with the 40 included) and
    'never with a cut' (D-73) are checked separately."""
    cfg = D72
    rng = np.random.default_rng(cfg['seed'])
    VT_k = VT[k] if k in VT else vote_table(k)
    m, conc, shared, p_o = inputs['m'], inputs['conc'], inputs['shared'], inputs['p_opus']
    z = rng.standard_normal((cfg['nsim'], cfg['B_add'], 2))
    eta_h = z[..., 0]
    eta_o = cfg['kappa'] * z[..., 0] + math.sqrt(1 - cfg['kappa'] ** 2) * z[..., 1]
    p = haiku_p(stats.norm.cdf(eta_h), conc, m)
    c = rng.binomial(cfg['n_samples'], p)
    a = rng.binomial(cfg['n_samples'] - c, shared) if shared else np.zeros_like(c)
    D = VT_k[c, a] - (eta_o < stats.norm.ppf(p_o)).astype(float)
    out = dict(inputs=inputs, k=k, config=cfg)
    for B in (cfg['B'], cfg['B_add']):
        r = readings(D[:, :B], cfg['level'], cfg['margin'])
        r['conclusive'] = r['ni'] + r['inferior']
        out[f'B{B}'] = r
    out['add_40_power_test'] = bool(out[f"B{cfg['B']}"]['conclusive'] < cfg['threshold'])
    return out


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'd72':
    # python3 study1_ni_power.py d72 pilot_inputs.json  (keys: haiku_correct, haiku_tries, wrong_pairs_agree,
    #   wrong_pairs, opus_correct, k)
    j = json.load(open(sys.argv[2]))
    inp = d72_inputs(j['haiku_correct'], j['haiku_tries'], j['wrong_pairs_agree'], j['wrong_pairs'], j['opus_correct'])
    print(json.dumps(d72_rerun(inp, int(j['k'])), indent=1))
    sys.exit(0)

if __name__ == '__main__':
    rows = main()
    def show(world, m, B, lvl, mg):
        print(f'\nworld {world}, Haiku mean {m}, B {B}, {lvl}% interval, margin {mg}: '
              'NI / inconclusive / inferior (%), true gap in points')
        print('p_opus | ' + ' | '.join(f'k={k}' for k in KS))
        for p_o in P_OPUS:
            cells = []
            for k in KS:
                r = next(x for x in rows if x['world'] == world and x['h_mean'] == m and x['B'] == B and
                         x['level'] == lvl and x['margin'] == mg and x['k'] == k and x['p_opus'] == p_o)
                cells.append(f"{r['ni']*100:.0f}/{r['inconclusive']*100:.0f}/{r['inferior']*100:.0f} ({r['gap_true']:+.0f})")
            print(f'{p_o:.2f} | ' + ' | '.join(cells))
    for world in WORLDS:
        for m in (0.25, 0.375):
            show(world, m, 80, '99', 10)
    ref = {}
    for (w, m, p_o, k) in [('ii-mod', 0.25, 0.80, 30), ('ii-mod', 0.375, 0.90, 30), ('ii-mod', 0.375, 0.95, 30),
                           ('i', 0.25, 0.95, 30), ('ii-high', 0.375, 0.80, 30)]:
        for lvl in (0.05, 0.01):
            key = f'{w} m={m} opus={p_o} k={k} level={lvl}'
            ref[key] = refusal_views(world=w, m=m, k=k, p_o=p_o, level=lvl)
            print('\nRefusals,', key)
            for r in ref[key]:
                print(r)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ni_power_refusals.json')
    json.dump(ref, open(path, 'w'), indent=1)
