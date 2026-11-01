"""Study 1b power (Karen). A thin wrapper around the LOCKED simulator `study1_ni_power.py` (prereg-lock-3). No API calls.

It reuses, unchanged, the locked pieces:
- `haiku_p` (the per-puzzle accuracy from a latent difficulty, Beta-distributed);
- the worlds (`WORLDS`: ii-mod conc 4, ii-high conc 1, iii with 30% shared wrong answers);
- `KAPPA` (the latent correlation between models);
- `vote_table` (the exact vote@k over all k-subsets, plurality, ties at 1/m);
- `readings` (non-inferior if the lower bound at the test's level is above −margin; worse if the 95% upper end is below −margin).

Study 1b's differences from Study 1, as in `research/study1b-spec.md`:
- **forms pooled per base puzzle.** Both forms of a base share its latent difficulty, which is the conservative choice: correlated
  forms help less.
- **Haiku-max has 10 tries per form.** B1 scores its single-try accuracy (correct tries ÷ 10). B2 scores vote@k over the 10 with k = 7.
- **Opus-medium has 2 tries per form.** Each try is right with probability P(η_o < Φ⁻¹(p_o) | the shared latent), so with one try it
  reduces exactly to the locked model.
- **Levels:** Holm's strictest step for three tests (one-sided 0.025/3, so a two-sided level of 0.05/3) and the nominal level.

Run: python3 research/models/study1b_power.py [nsim]   (default 4000, seed 20261011 as locked)
"""
import json, math, os, sys
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import study1_ni_power as L  # noqa: E402  (the locked simulator)

NSIM = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4000
SEED = L.SEED
TRIES_H, TRIES_O, K_VOTE = 10, 2, 7
VT_H = L.vote_table(K_VOTE, n=TRIES_H)
LEVEL_HOLM, LEVEL_NOM = 0.05 / 3, 0.05


def simulate(world, m_h, p_o, B, nsim, rng, kappa=L.KAPPA):
    conc, shared = L.WORLDS[world]
    z = rng.standard_normal((nsim, B))
    p_h = L.haiku_p(stats.norm.cdf(z), conc, m_h)                       # (nsim, B), shared by both forms
    t = stats.norm.ppf(p_o)
    p_ob = stats.norm.cdf((t - kappa * z) / math.sqrt(1 - kappa ** 2))   # Opus's per-try chance given the latent
    d_single, d_vote = np.zeros((nsim, B)), np.zeros((nsim, B))
    for _form in range(2):
        c = rng.binomial(TRIES_H, p_h)
        a = rng.binomial(TRIES_H - c, shared) if shared else np.zeros_like(c)
        o = rng.binomial(TRIES_O, p_ob) / TRIES_O
        d_single += (c / TRIES_H - o) / 2
        d_vote += (VT_H[c, a] - o) / 2
    return d_single, d_vote


def main():
    rng = np.random.default_rng(SEED)
    out = []
    for B, label in ((80, 'B1/B2 at N = 16 (main-ledger-l14n16-v1, 80 base)'), (40, 'B3 at N = 6 (ext40-ledger-l14n6-v1, 40 base)')):
        for p_o in (0.98, 0.95):
            for world in ('ii-mod', 'ii-high', 'iii'):
                for m_h in (0.98, 0.95, 0.92, 0.88):
                    ds, dv = simulate(world, m_h, p_o, B, NSIM, rng)
                    row = dict(set=label, B=B, p_opus=p_o, world=world, haiku_max_mean=m_h)
                    for name, D in (('single', ds), ('vote7', dv)):
                        if B == 40 and name == 'vote7':
                            continue
                        for margin in (5, 10):
                            r = L.readings(D, LEVEL_HOLM, margin)
                            row[f'{name}_m{margin}_holm_ni'] = round(r['ni'], 3)
                            row[f'{name}_m{margin}_holm_worse'] = round(r['inferior'], 3)
                            row[f'{name}_m{margin}_nominal_ni'] = round(L.readings(D, LEVEL_NOM, margin)['ni'], 3)
                    out.append(row)
                    print({k: v for k, v in row.items() if k not in ('set',)})
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'study1b_power_results.json')
    json.dump(dict(nsim=NSIM, seed=SEED, tries_haiku=TRIES_H, tries_opus=TRIES_O, k_vote=K_VOTE, kappa=L.KAPPA,
                   level_holm=LEVEL_HOLM, rows=out), open(path, 'w'), indent=1)
    print('written', path)


if __name__ == '__main__':
    main()
