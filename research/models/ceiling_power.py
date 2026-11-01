"""Power near Opus's ceiling at short N (Karen, OURS; D-86, Edith's ceiling note). Desk simulation, no API calls.
Uses study1_ni_power's model (latent difficulty, kappa 0.5, Haiku Beta worlds, 40 samples, exact vote@k).
Test 2-style reading (Holm's strictest, one-sided 0.005; worse = unadjusted 95% upper < -10), B = 80 and 120.
Run: python3 research/models/ceiling_power.py  -> ceiling_power_results.json"""
import json, os
import numpy as np
from scipy import stats
import study1_ni_power as sp

K, SEED, NSIM = 24, 20261012, 3000
rows = []
VT = sp.vote_table(K)
for world in ('i', 'ii-mod', 'ii-high', 'iii'):
    for m in (0.30, 0.375, 0.45):
        rng = np.random.default_rng(SEED)
        eta_o, c, a = sp.draw(world, m, NSIM, 120, sp.KAPPA, rng)
        V = VT[c, a]
        v_true = float(V.mean())
        for p_o in (0.95, 0.97, 0.99, 1.0):
            O = (eta_o < stats.norm.ppf(p_o)).astype(float) if p_o < 1 else np.ones_like(eta_o, dtype=float)
            for B in (80, 120):
                r = sp.readings((V - O)[:, :B], 0.01, 10)
                ratio = (1 - v_true) / (1 - p_o) if p_o < 1 else float('inf')
                rows.append(dict(world=world, h_mean=m, p_opus=p_o, B=B, k=K, vote_true=round(v_true, 3),
                                 gap_true=round((v_true - p_o) * 100, 1), err_ratio=round(ratio, 1) if p_o < 1 else None,
                                 **{x: round(y, 3) for x, y in r.items()}))
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ceiling_power_results.json')
json.dump(dict(seed=SEED, nsim=NSIM, k=K, rows=rows), open(path, 'w'), indent=0)
for world in ('i', 'ii-mod', 'ii-high', 'iii'):
    print(f'\n{world}, B=80: Haiku mean | vote acc | Opus 0.95 / 0.97 / 0.99 / 1.0  (NI/inconclusive/worse %, gap)')
    for m in (0.30, 0.375, 0.45):
        cells = []
        for p_o in (0.95, 0.97, 0.99, 1.0):
            r = next(x for x in rows if x['world'] == world and x['h_mean'] == m and x['p_opus'] == p_o and x['B'] == 80)
            cells.append(f"{r['ni']*100:.0f}/{r['inconclusive']*100:.0f}/{r['inferior']*100:.0f} ({r['gap_true']:+.0f}; x{r['err_ratio']})")
        print(f'{m} | {r["vote_true"]} | ' + ' || '.join(cells))
