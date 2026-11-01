"""Study 1 main run: the minimum viable run and a pre-registered cut order (Karen, OURS; mock-review fix 8).
Uses the token and price model in study1_budget.py. Desk arithmetic only, no API calls.
Every confirmatory arm (D-68 F1/F2) is kept at every step; only exploratory parts and base puzzles go."""
import study1_budget as m
m.PILOT_N["d4p"] = 10   # pilot shrink step 1 (slot B 20 -> 10), as in research/pilot-plan-ledger.md

CORE_24 = {'Haiku-med': 40, 'Opus-med': 1}                                              # test 1
CORE_124 = {'Haiku-med': 40, 'Opus-med': 1, 'Sonnet-med': 1, 'E3-lead2-batch': 1, 'Opus-low': 1}  # tests 2-5
OTHER_SHAPE = {'Sonnet-med': 1, 'E3-lead2-batch': 1, 'Opus-low': 1}                     # the same arms at 24x1
SHOULDS = [('Sonnet-low', 1), ('Haiku-off', 40), ('E2', 1), ('H-pick8', 1)]            # D-27 order 1-4
FIXED = {'check20': (2.0, 3.0, 5.0), 's3': (0.5, 1.0, 2.0)}                             # D-57 cap $5; S3 small (OURS)

def parts(s, nb=80, haiku_low=40, robust_n=40, shoulds=4, haiku_max=True, other_shape=True):
    u = m.setups(s)
    run = lambda mix, n: n * sum(u[k] * c for k, c in mix.items())
    p = {'core (tests 1-5)': run(CORE_24, nb) + run(CORE_124, nb)}
    if other_shape:
        p['other-shape arms (24x1)'] = run(OTHER_SHAPE, nb)
    if haiku_low:
        p[f'Haiku-low x{haiku_low}'] = run({'Haiku-low': haiku_low}, 2 * nb)
    if robust_n:
        p[f'D-42 robustness (Haiku-med x10 on {robust_n})'] = run({'Haiku-med': 10}, robust_n)
    for name, c in SHOULDS[:shoulds]:
        p[name] = run({name: c}, 2 * nb)
    if haiku_max:
        p['Haiku-max x3'] = run({'Haiku-max': 3}, 2 * nb)
    return p

def all_in(s, spent=None, **kw):
    """(main run, all in). Before the pilot: (main + modelled pilot, 20-call check, S3) x 1.05. After the pilot
    (D-72/D-73/D-74, pinned): `spent` = the ACTUAL spend before the main run from ops/spend-log.md, and the
    all-in total is main x 1.05 + spent."""
    main = sum(parts(s, **kw).values())
    if spent is not None:
        return main, main * 1.05 + spent
    pre = m.pilot(s) + FIXED['check20'][s] + FIXED['s3'][s]
    return main, (main + pre) * 1.05

LADDER = [
    ('Full plan (musts + shoulds 1-4 + Haiku-max)', {}),
    ('Cut 1: Haiku-max', dict(haiku_max=False)),
    ('Cut 2: H-pick8', dict(haiku_max=False, shoulds=3)),
    ('Cut 3: E2', dict(haiku_max=False, shoulds=2)),
    ('Cut 4: Haiku-off', dict(haiku_max=False, shoulds=1)),
    ('Cut 5: Sonnet-low (= musts only)', dict(haiku_max=False, shoulds=0)),
    ('Cut 6: Haiku-low x40 -> x20', dict(haiku_max=False, shoulds=0, haiku_low=20)),
    ('Cut 7: D-42 robustness 40 -> 20 puzzles', dict(haiku_max=False, shoulds=0, haiku_low=20, robust_n=20)),
    ('Cut 8: other-shape arms (24x1 Sonnet, E3, Opus-low)', dict(haiku_max=False, shoulds=0, haiku_low=20, robust_n=20, other_shape=False)),
    ('Cut 9: base puzzles 80 -> 70', dict(haiku_max=False, shoulds=0, haiku_low=20, robust_n=20, other_shape=False, nb=70)),
    ('Cut 10: base puzzles 70 -> 60 (floor)', dict(haiku_max=False, shoulds=0, haiku_low=20, robust_n=20, other_shape=False, nb=60)),
    ('MVR: core only, 60 base (no Haiku-low, no D-42 check)', dict(haiku_max=False, shoulds=0, haiku_low=0, robust_n=0, other_shape=False, nb=60)),
]

CEILING = 170.0   # the D-27 ladder line (D-48 row 25); the one ceiling for D-72 and D-73

def add40_cost(s):
    """D-72: 40 extra base puzzles at 1x24, the arms of tests 2-5, all in (x1.05)."""
    u = m.setups(s)
    return 40 * sum(u[k] * c for k, c in CORE_124.items()) * 1.05

N_EXTRA_STEPS = 6   # LADDER[0..5]: the full plan, then Haiku-max and the shoulds; D-74 may trade only these

def d73_cuts(s=2, spent=None):
    """D-73 (no add): walk the ladder from the top; return the first step whose all-in total fits the ceiling
    (high case by default), or None if even the minimum viable run doesn't fit (stop, return to the user)."""
    for name, kw in LADDER:
        tot = all_in(s, spent=spent, **kw)[1]
        if tot <= CEILING:
            return name, round(tot, 1)
    return None

def d72_budget_test(s=2, spent=None):
    """D-72 budget test as amended by D-74 (confirmatory precision ranks above the extras): the 40 may be added
    if, after cutting extras in D-73 order (Haiku-max, then the shoulds 4 -> 1) and nothing else, the high case
    WITH the 40 is at most the ceiling. Returns the first such step, or passes=False."""
    add = add40_cost(s)
    for i, (name, kw) in enumerate(LADDER[:N_EXTRA_STEPS]):
        tot = all_in(s, spent=spent, **kw)[1] + add
        if tot <= CEILING:
            return dict(passes=True, step=name, extras_cut=[n for n, _ in LADDER[1:i + 1]],
                        cost_of_40=round(add, 1), all_in_with_add=round(tot, 1))
    return dict(passes=False, cost_of_40=round(add, 1),
                musts_with_add=round(all_in(s, spent=spent, **LADDER[N_EXTRA_STEPS - 1][1])[1] + add, 1))

def post_pilot_decision(power_passes, s=2, spent=None):
    """The one post-pilot decision (D-72, D-73, D-74), recorded in the dated amendment and reported in the paper.
    power_passes: study1_ni_power.d72_rerun(...)['add_40_power_test']."""
    if power_passes:
        b = d72_budget_test(s, spent)
        if b['passes']:
            return dict(add40=True, **b)
    cut = d73_cuts(s, spent)
    if cut is None:
        return dict(add40=False, step=None, action='stop and return to the user (D-27 stop-loss)')
    return dict(add40=False, step=cut[0], all_in=cut[1])

def _scenario(t, inn=3350, vis=660, hm=1.42, sm=1.0):
    """Synthetic post-pilot token state for the known-answer examples, as ledger_measured.json would hold after
    the pilot (post_pilot = true): every scenario from the central assumptions, thinking multiplier t (Opus-medium
    thinking = 10,000 t; high = 1.25 t), the same input and visible tokens in every scenario."""
    m.collapse_to_central()
    m.SC['IN'] = (inn,) * 3; m.SC['vis'] = (vis,) * 3; m.FP['TM'] = (t, t, 1.25 * t); m.HM = hm; m.SM_RATIO = sm

D74_EXAMPLES = [  # (name, thinking multiplier t, actual spend before the main run, power test passes)
    ('A: cheap tokens, power poor -> add, no cut', 0.60, 25.0, True),
    ('B: middling tokens, power poor -> add after trading extras', 1.00, 25.0, True),
    ('C: dear tokens, power poor -> no add (musts + 40 too dear), D-73 cuts', 1.60, 25.0, True),
    ('D: dearer tokens, power fine -> no add, D-73 as usual', 1.20, 25.0, False),
]

def d74_examples():
    out = {}
    saved = (dict(m.SC), dict(m.FP), m.HM, m.SM_RATIO)
    try:
        for name, t, spent, pw in D74_EXAMPLES:
            _scenario(t)
            out[name] = post_pilot_decision(pw, 2, spent)
    finally:
        m.SC.clear(); m.SC.update(saved[0]); m.FP.clear(); m.FP.update(saved[1]); m.HM, m.SM_RATIO = saved[2], saved[3]
    return out

if __name__ == '__main__':
    print('D-73 at high:', d73_cuts(2), '| at central:', d73_cuts(1))
    print('D-72/D-74 budget test at high:', d72_budget_test(2))
    import json, os, sys
    ex = d74_examples()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'd74_example_output.json')
    if len(sys.argv) > 1 and sys.argv[1] == 'write-examples':
        json.dump(ex, open(path, 'w'), indent=1)
    elif os.path.exists(path):
        assert json.load(open(path)) == json.loads(json.dumps(ex)), 'D-74 known-answer examples changed'
        print('D-74 known-answer examples reproduce')
    for k, v in ex.items():
        print(k, '->', v)
    print('step | main low/central/high | all in (incl. pilot, 20-call check, S3, x1.05) low/central/high')
    for name, kw in LADDER:
        r = [all_in(s, **kw) for s in range(3)]
        print(f"{name:55s} | {r[0][0]:6.1f} {r[1][0]:6.1f} {r[2][0]:6.1f} | {r[0][1]:6.1f} {r[1][1]:6.1f} {r[2][1]:6.1f}")
    for s, nm in enumerate(['low', 'central', 'high']):
        print(nm, {k: round(v, 1) for k, v in parts(s).items()}, 'pilot', round(m.pilot(s), 1))
    # 120 base puzzles (R2's option), core and full
    for nb in (100, 120):
        r = [all_in(s, nb=nb, haiku_max=False, shoulds=0) for s in range(3)]
        print(f'musts at {nb} base: main {r[0][0]:.1f}/{r[1][0]:.1f}/{r[2][0]:.1f}, all in {r[0][1]:.1f}/{r[1][1]:.1f}/{r[2][1]:.1f}')
        r = [all_in(s, nb=nb, haiku_max=False, shoulds=0, haiku_low=0, robust_n=0, other_shape=False) for s in range(3)]
        print(f'core only at {nb} base: main {r[0][0]:.1f}/{r[1][0]:.1f}/{r[2][0]:.1f}, all in {r[0][1]:.1f}/{r[1][1]:.1f}/{r[2][1]:.1f}')
    # +40 base at 1x24 only, core arms (tests 2-5), on top of the musts
    for s, nm in enumerate(['low', 'central', 'high']):
        u = m.setups(s)
        add = 40 * sum(u[k] * c for k, c in CORE_124.items())
        print(f'{nm}: +40 base at 1x24 only, tests 2-5 arms: +${add:.1f} main, +${add*1.05:.1f} all in')
