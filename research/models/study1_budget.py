# Karen's reconciled Study 1 budget model (OURS; prices BACKED facts-checked.md)
P={'o':(4,20),'s':(2,10),'h':(0.10,0.50)}
def c(m,i,o): a,b=P[m]; return (i*a+o*b)/1e6
import json, os
# ---- Task family (D-56: the ledger replaces digits as the main family) ----
# Per family: prompt tokens IN, visible step-value tokens VIS (D-31 format), thinking multiplier TM vs the digit
# output ranges below, and the pilot's per-preset prompt scales. Ledger values are PLACEHOLDERS (OURS,
# research/task-families-noncipher.md 2) until Friday measures the frozen preset (Edith L5): drop a JSON at
# research/models/ledger_measured.json with any of {"in_tokens":[lo,c,hi], "vis_tokens":[...], "tm":[...]}
# (or "prompt_chars": mean characters, converted at /3.5 central and /2.5 high) and re-run.
FAMILY='ledger'
FAMILIES={
 'digits':{'IN':(2064,2064,2889),'VIS':(150,250,400),'TM':(1.0,1.0,1.0),'PILOT_SCALES':(1.0,1.0,1.2)},
 'ledger':{'IN':(1000,1000,1400),'VIS':(250,300,450),'TM':(1.0,1.0,1.5),'PILOT_SCALES':(1.0,1.0,1.0)},
}
_m=os.path.join(os.path.dirname(os.path.abspath(__file__)),'ledger_measured.json')
if FAMILY=='ledger' and os.path.exists(_m):
    _d=json.load(open(_m))
    if 'prompt_chars' in _d: FAMILIES['ledger']['IN']=(_d['prompt_chars']/3.5,_d['prompt_chars']/3.5,_d['prompt_chars']/2.5)
    if 'in_tokens' in _d: FAMILIES['ledger']['IN']=tuple(_d['in_tokens'])
    if 'vis_tokens' in _d: FAMILIES['ledger']['VIS']=tuple(_d['vis_tokens'])
    if 'tm' in _d: FAMILIES['ledger']['TM']=tuple(_d['tm'])
FP=FAMILIES[FAMILY]
SC={ # low, central, high
 'IN':(2064,2064,2889),'ol':(2000,4000,6000),'om':(4000,10000,16000),'oh':(8000,19000,30000),
 'sm':(4000,10000,16000),'step_out':(250,700,1800),'step_in':(170,170,236),
 'e1':(1500,3000,6000),'e2':(1500,3750,6000),'agg_in':(1000,1500,4000),'samp':(500,1000,3000),
 # D-31: every reply lists the value after each step (24 short values + numbered final line), tokens
 'vis':(150,250,400)}
SC['IN']=FP['IN']; SC['vis']=FP['VIS']
HL,HM=1.6,1.42   # AA Haiku/Opus output ratios (low, medium)
SM_RATIO=1.0     # Sonnet-medium thinking relative to Opus-medium (SC['sm'] = SC['om'] in every scenario)
# D-72/D-73 (pinned for the lock): after the pilot, ledger_measured.json carries the pilot's measured means at the
# chosen preset: in_tokens and vis_tokens (same in all three scenarios), tm = [t, t, 1.25*t] with t = Opus-medium's
# mean thinking tokens / 10000, hm_ratio = Haiku-medium / Opus-medium mean thinking, sm_ratio = Sonnet-medium /
# Opus-medium mean thinking, and post_pilot = true (every scenario starts from the central assumptions). The 'high'
# column is then the high case (1.25 x measured) for the D-72/D-74 budget test and the D-73 cuts.
POST_PILOT_KEYS=('ol','om','oh','sm')   # only the thinking keys that tm scales (Edith L-a); measured via the pilot
def collapse_to_central():
    # After the pilot the THINKING assumptions start from their central values in every scenario, so that
    # tm = [t, t, 1.25 t] makes the high case exactly 1.25 x the measured thinking (not 1.6 x 1.25, as the pre-pilot
    # spread would give). Keys the pilot does not measure (E3/E2 step tokens, aggregator and sample inputs) keep
    # their low/central/high spread (Edith's review ops/reviews/2026-10-11-d74-lock-code-r1.md, L-a).
    for k in POST_PILOT_KEYS: SC[k]=(SC[k][1],)*3
if FAMILY=='ledger' and os.path.exists(_m):
    HM=_d.get('hm_ratio',HM); SM_RATIO=_d.get('sm_ratio',SM_RATIO)
    if _d.get('post_pilot'):
        # post-pilot in_tokens and vis_tokens are the pilot's measured means, the same in all three slots
        assert len(set(_d['in_tokens']))==1 and len(set(_d['vis_tokens']))==1, 'post_pilot: in/vis tokens must be one mean'
        collapse_to_central()
B=0.5
def g(k,s,hard=False):
    v=SC[k][s]
    if hard and k=='IN': v*=1.2
    elif hard: v*=1.5
    return v
def setups(s,hard=False):
    IN=g('IN',s,hard); ol=g('ol',s,hard); om=g('om',s,hard); oh=g('oh',s,hard); sm=g('sm',s,hard)*SM_RATIO
    T=FP['TM'][s]; ol,om,oh,sm=ol*T,om*T,oh*T,sm*T   # family thinking multiplier
    hl=ol*HL; hm=om*HM; so=g('step_out',s,hard); si=g('step_in',s,hard)
    V=g('vis',s,hard)  # D-31 visible step values, added to every whole-puzzle answer
    ol,om,oh,sm,hl,hm=ol+V,om+V,oh+V,sm+V,hl+V,hm+V
    e3=72*c('h',si,so)
    return {
     'Opus-low':c('o',IN,ol)*B,'Opus-med':c('o',IN,om)*B,'Opus-high':c('o',IN,oh)*B,
     'Sonnet-med':c('s',IN,sm)*B,'Haiku-low':c('h',IN,hl)*B,'Haiku-med':c('h',IN,hm)*B,
     'H-pick8':c('h',IN+8*g('samp',s,hard),2000)*B,'H-pick16':c('h',IN+16*g('samp',s,hard),2000)*B,
     'O-pick8':c('o',IN+8*g('samp',s,hard),ol)*B,
     'E3':e3,'E1':c('o',IN,g('e1',s,hard))+c('o',g('agg_in',s,hard),g('e1',s,hard))+e3,
     'E2':c('h',IN,g('e2',s,hard))+c('h',g('agg_in',s,hard),g('e2',s,hard))+e3,
     # Karen's additions
     'E3-lead2-batch':24*9*c('h',si,so)*B, 'Sonnet-low':c('s',IN,sm*0.73)*B,
     'Haiku-max':c('h',IN,min((hm-V)*8.1+V,128000))*B,'Haiku-off':c('h',IN,1500+V)*B,
    }
def run(mix,n,s,hard=False):
    u=setups(s,hard); return n*sum(u[k]*m for k,m in mix.items())
A={'Opus-low':2,'Opus-med':1,'Opus-high':1,'Sonnet-med':1,'Haiku-low':40,'Haiku-med':40,
   'H-pick8':1,'H-pick16':1,'O-pick8':1,'E3':1,'E1':1,'E2':1}
def leanA(s): # trims: Opus-low x1, Opus-high on 80, E1 on 40, Haiku-low x20
    m=dict(A); m['Opus-low']=1; m['Haiku-low']=20; m.pop('Opus-high'); m.pop('E1')
    return run(m,160,s)+run({'Opus-high':1},80,s)+run({'E1':1},40,s)
HARD40={'Opus-low':1,'Opus-med':1,'Opus-high':1,'Haiku-med':40}
HARD40L={'Opus-low':1,'Opus-med':1,'Opus-high':1,'Haiku-med':20}
KMUST={'Opus-med':1,'Opus-low':1,'Sonnet-med':1,'Haiku-low':40,'Haiku-med':40,'E3-lead2-batch':1}
KSHOULD={'Sonnet-low':1,'Haiku-max':3,'Haiku-off':40,'E2':1,'H-pick8':1}
RT_N=10
def realtime_subset(s):
    u=setups(s)  # u[] are Batch prices; real time = 2x
    N=RT_N  # D-35: real-time subset size (10; 6 under shrink step 3)
    rt=N*2*(u['Opus-med']+u['Sonnet-med']+5*u['Haiku-med'])   # real-time runs at list (latency + one half of equivalence)
    # The batched side reuses the pilot's own Batch calls on the same puzzles (Friday's pilot plan), so no duplicate.
    return rt
def karen(s,shoulds=()):
    # Karen's standard-level list (research/study1-design-evidence.md 3.7); two shapes (D-24), no 6x4 slice
    t=run(KMUST,160,s)  # the real-time check is counted in the pilot (D-36)
    t+=run({'Haiku-med':10},40,s)  # D-42: prompt-variant robustness check, Haiku-medium x10 on 40 main-set puzzles
    for k in shoulds: t+=160*setups(s)[k]*KSHOULD[k]
    return t
SH14=['Sonnet-low','Haiku-off','E2','H-pick8']
PILOT_N={'d4':10,'d4s':20,'d4p':20}   # D-36 practice puzzles per preset slot (base x 2 shapes); for the ledger, read as preset slots 1-3
PILOT_CODE_N=0                         # D-59: code family dropped (was 8: 4 base x 2 shapes)
PILOT_HAIKU=10                         # Haiku-medium tries per puzzle
def pilot_parts(s):
    """D-36 pilot: per digit puzzle Opus-med x1 + Sonnet-med x1 + Haiku-med x10 (Batch);
    code slice Opus-med x1 + Haiku-med x10 (Batch); 10-puzzle real-time check (latency + batch-vs-real-time)."""
    V=SC['vis'][s]
    T=FP['TM'][s]
    def dig(scale):
        IN=SC['IN'][s]*scale
        return (c('o',IN,SC['om'][s]*T+V)+c('s',IN,SC['sm'][s]*SM_RATIO*T+V)+PILOT_HAIKU*c('h',IN,SC['om'][s]*T*HM+V))*B
    IN=(2924,2924,4094)[s]; VIS=(1200,1600,2400)[s]; TM=CODE_TM[s]
    cd=(c('o',IN,SC['om'][s]*TM+VIS)+PILOT_HAIKU*c('h',IN,SC['om'][s]*TM*HM+VIS))*B
    sc=FP['PILOT_SCALES']
    return {'main-family presets':PILOT_N['d4']*dig(sc[0])+PILOT_N['d4s']*dig(sc[1])+PILOT_N['d4p']*dig(sc[2]),
            'code slice':PILOT_CODE_N*cd,'real-time check':realtime_subset(s)}
def pilot(s): return sum(pilot_parts(s).values())
CODE_ON=False  # D-59: code family dropped for this credit
def code(s):
    if not CODE_ON: return 0.0
    # D-32/D-35: 80 puzzles (40 base x 2 shapes); Opus-med x1, Haiku-med x40 (Batch); E3 lead-by-2 step-wise (Batch); no Sonnet (D-35)
    # Prompt: c3/c4 mean 10,235 chars (Friday, data/codetrace-free-test/README.md) -> /3.5 or /2.5 (high)
    IN=(2924,2924,4094)[s]
    VIS=(1200,1600,2400)[s]          # D-31: 24 listed values, each a list of 24-32 numbers (OURS)
    TM=CODE_TM[s]                    # thinking multiplier vs digit puzzles: bigger state per step (OURS, unmeasured)
    om=SC['om'][s]*TM+VIS; sm=SC['sm'][s]*TM+VIS; hm=SC['om'][s]*TM*HM+VIS
    si=(175,175,245)[s]; so=SC['step_out'][s]*TM
    return 80*(c('o',IN,om)*B+40*c('h',IN,hm)*B+24*9*c('h',si,so)*B)
CODE_TM=(1.0,1.5,2.0)
STUDY5=(0,0,0)  # D-44: Study 5 left out of this project (was 5/15/30)
if __name__=='__main__':
    rows=[('A',lambda s:run(A,160,s)),('Lean A',leanA),
          ('C-prime-40',lambda s:run(A,160,s)+run(HARD40,40,s,True)),
          ('Lean C-prime-40',lambda s:leanA(s)+run(HARD40L,40,s,True)),
          ('Karen 3.7 musts only',lambda s:karen(s)),
          ('Karen 3.7 musts+shoulds 1-4',lambda s:karen(s,SH14)),
          ('Karen 3.7 musts+all shoulds',lambda s:karen(s,SH14+['Haiku-max']))]
    print('pilot %.1f/%.1f/%.1f  code %.1f/%.1f/%.1f'%tuple([pilot(s) for s in range(3)]+[code(s) for s in range(3)]))
    for name,f in rows:
        out=[]
        for s in range(3):
            main=f(s); sub=main+pilot(s)+code(s)+STUDY5[s]; tot=sub*1.05
            out.append((main,tot))
        print('%-26s main %6.1f / %6.1f / %6.1f | ALL-IN %6.1f / %6.1f / %6.1f'%(name,*[o[0] for o in out],*[o[1] for o in out]))
