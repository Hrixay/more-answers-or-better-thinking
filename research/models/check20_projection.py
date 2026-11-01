"""Budget projection from the D-57 20-call check (check-ledger-1, 2026-10-11): token counts and cost only, which
D-78 C allows before the lock (cost information, not performance). Karen, OURS. No API calls.

Recipe (research/mock-review-fixes.md section 6): thinking = output tokens - visible reply tokens; visible = 660
(Friday's measured l16 reply length; the answers are sealed). TM = Opus-medium mean thinking / 10,000; the high case
uses the largest single output (10,525) instead of the mean. sm_ratio = Sonnet / Opus mean thinking. Haiku is not in
the check: hm_ratio stays at the model's 1.42 (AA's Haiku/Opus output ratio at medium).
Every scenario starts from the central assumptions for the thinking keys (as study1_budget.collapse_to_central).
"""
import json
import study1_budget as m
import study1_cut_order as co

CHECK = {  # cell totals over 5 calls each: input, output tokens (Jarvis, from the spend-log row of check-ledger-1)
    ('opus', '1x24'): (15023, 34876), ('opus', '24x1'): (20478, 36168),
    ('sonnet', '1x24'): (15023, 32793), ('sonnet', '24x1'): (20478, 34031)}
VIS, MAX_OUT, N = 660, 10525, 5
P = {'opus': (4, 20), 'sonnet': (2, 10)}

def per_call(model, shape):
    i, o = CHECK[(model, shape)]
    return i / N, o / N

opus_think = sum(per_call('opus', s)[1] - VIS for s in ('1x24', '24x1')) / 2
son_think = sum(per_call('sonnet', s)[1] - VIS for s in ('1x24', '24x1')) / 2
t, t_high = opus_think / 10000, (MAX_OUT - VIS) / 10000
sm_ratio = son_think / opus_think
in_mean = sum(per_call('opus', s)[0] for s in ('1x24', '24x1')) / 2
cost_check = sum(n * (i * P[mod][0] + o * P[mod][1]) / 1e6 for (mod, sh), (i, o) in CHECK.items() for n in [1])

def apply():
    m.collapse_to_central()
    m.SC['IN'] = (in_mean,) * 3; m.SC['vis'] = (VIS,) * 3
    m.FP['TM'] = (t, t, t_high); m.SM_RATIO = sm_ratio

def s3(n_opus=3, n_son=2, out_factor=1.0, shape='mix'):
    """S3 check Batch: billed at the Batch price (50%)."""
    shapes = ('1x24', '24x1')
    def call(model):
        vals = [per_call(model, s) for s in shapes]
        i = sum(v[0] for v in vals) / len(vals); o = sum(v[1] for v in vals) / len(vals) * out_factor
        return (i * P[model][0] + o * P[model][1]) / 1e6 * 0.5
    return n_opus * call('opus') + n_son * call('sonnet')

if __name__ == '__main__':
    print(f'check cost recomputed at list ${cost_check:.4f}  (logged $2.302126)')
    print(f'Opus-medium mean thinking {opus_think:.0f} -> TM {t:.3f}; high (largest output) {t_high:.3f}; '
          f'Sonnet/Opus thinking {sm_ratio:.3f}; mean input {in_mean:.0f}')
    apply()
    for nm, n in (('as planned (A20 B20 C10)', 20), ('step 1 (B 20 -> 10)', 10)):
        m.PILOT_N['d4p'] = n
        print(nm, 'pilot low/central/high $%.2f / $%.2f / $%.2f' % tuple(m.pilot(s) for s in range(3)))
    m.RT_N = 6
    print('steps 1+3 (real-time 10 -> 6) pilot $%.2f / $%.2f / $%.2f' % tuple(m.pilot(s) for s in range(3)))
    m.RT_N = 10; m.PILOT_N['d4p'] = 20   # no shrink applies on the measured tokens: the planned pilot (B = 20)
    for name, kw in co.LADDER[:1] + co.LADDER[5:6] + co.LADDER[-1:]:
        r = [co.all_in(s, **kw) for s in range(3)]
        print(f'{name:55s} main {r[1][0]:.1f}/{r[2][0]:.1f}  all in {r[1][1]:.1f}/{r[2][1]:.1f} (central/high)')
    print('D-73 at high:', co.d73_cuts(2), '| D-72/74 budget test at high:', co.d72_budget_test(2))
    u = m.setups(1)
    print('equal-money k (central):', round(u['Opus-med'] / u['Haiku-med'], 2), ' Sonnet-matched:', round(u['Sonnet-med'] / u['Haiku-med'], 2))
    for f in (1.0, 0.7, 0.5):
        print(f'S3 (3 Opus + 2 Sonnet, Batch) at {int(f*100)}% of the measured mean output: ${s3(out_factor=f):.3f}')
    print(f'S3 at 15K max_tokens (worst case, Batch): ${(3*(in_mean*4+15000*20)+2*(in_mean*2+15000*10))/1e6*0.5:.3f}')
