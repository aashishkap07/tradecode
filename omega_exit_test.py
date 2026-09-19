"""Does the peak-giveback exit earn its keep, and does a minimum hold help?

THE CASE, from session 20260917_103900. ARB was opened with a target of +7.3%
(2.00R, C416) and a stop at -2.1% (0.75R, C377). It ran +0.94% in eight
minutes, gave it back, and PEAK_REVERSAL closed it at -0.06% after TEN MINUTES.
RIVER aimed at +4.1%, peaked +0.25%, and C399 closed it at -0.16% after 18.

So the bot AIMS at 2R and EXITS at 0.02-0.10R. The geometry it computes so
carefully never gets to play. This measures whether that is costing money.

Geometry is the bot's own: R = 2 x ATR(14) on 15m, target 2.00R, stop 0.75R,
maker both ways, non-overlapping entries, adverse extreme first inside every
bar, both directions, four-way split.
"""
import os, glob, statistics, math

FEE, H, STRIDE = 0.04, 32, 32
TARGET_R, STOP_R = 2.00, 0.75
GIVEBACK_THR = 0.48          # the bot's own thr=48%, seen in the log

def load():
    out={}
    for f in sorted(glob.glob('corpusL/*.csv')):
        rows=[]
        for ln in open(f):
            p=ln.strip().split(',')
            if len(p)<6: continue
            try: rows.append(tuple(float(x) for x in p[:6]))
            except ValueError: pass
        rows.sort(key=lambda r:r[0])
        if len(rows)>2000: out[os.path.basename(f)[:-4]]=rows
    return out

def atrs(rows):
    n=len(rows); atr=[None]*n; tr=[0.0]*n
    for i in range(1,n):
        h,l,pc=rows[i][2],rows[i][3],rows[i-1][4]
        tr[i]=max(h-l,abs(h-pc),abs(l-pc))
    s=0.0
    for i in range(1,n):
        s+=tr[i]
        if i>14: s-=tr[i-14]
        if i>=14 and rows[i][4]: atr[i]=(s/14)/rows[i][4]*100.0
    return atr

def sim(rows, i0, side, R, atr_pct, giveback=False, min_hold=0):
    """One trade. Returns net % of price after fees."""
    e=rows[i0][4]; sg=1.0 if side=='long' else -1.0
    tp=e*(1+sg*TARGET_R*R/100.0); sl=e*(1-sg*STOP_R*R/100.0)
    peak=0.0
    for k,b in enumerate(rows[i0+1:i0+1+H], start=1):
        h,l=b[2],b[3]
        adv = l if side=='long' else h
        fav = h if side=='long' else l
        # adverse extreme first, always
        if (side=='long' and adv<=sl) or (side=='short' and adv>=sl):
            return -STOP_R*R-FEE
        if (side=='long' and fav>=tp) or (side=='short' and fav<=tp):
            return TARGET_R*R-FEE
        peak=max(peak, sg*(fav/e-1)*100.0)
        if giveback and k>min_hold and peak>0:
            now=sg*(b[4]/e-1)*100.0
            gave=peak-now
            # the bot's own C241/C280 noise veto, faithfully
            veto=min(0.75*atr_pct, 0.65*peak)
            if gave > GIVEBACK_THR*peak and gave >= veto:
                return now-FEE
    j=min(i0+H,len(rows)-1)
    return sg*(rows[j][4]/e-1)*100.0-FEE

data=load(); syms=sorted(data); A=set(syms[::2])
print(f"corpus {len(syms)} pairs, {sum(len(v) for v in data.values()):,} bars\n")
CONFIGS=[('barrier only (hold to 2R / 0.75R)', dict(giveback=False)),
         ('+ peak-giveback exit (the bot today)', dict(giveback=True, min_hold=0)),
         ('+ giveback, but not before 8 bars (2h)', dict(giveback=True, min_hold=8)),
         ('+ giveback, but not before 16 bars (4h)', dict(giveback=True, min_hold=16))]
res={name:[] for name,_ in CONFIGS}
for s_ in syms:
    rows=data[s_]; atr=atrs(rows); half=len(rows)//2
    for i in range(20,len(rows)-H-1,STRIDE):
        if atr[i] is None or atr[i]<=0: continue
        R=2.0*atr[i]
        for side in ('long','short'):
            for name,kw in CONFIGS:
                res[name].append((i<half, s_ in A, sim(rows,i,side,R,atr[i],**kw)))
base=None
for name,_ in CONFIGS:
    v=[x[2] for x in res[name]]
    m=statistics.mean(v); sd=statistics.pstdev(v) or 1e-9
    t=m/(sd/math.sqrt(len(v)))
    wr=100.0*sum(1 for x in v if x>0)/len(v)
    line=f"  {name:<40} n={len(v):>6,}  mean {m:+.4f}%  t={t:+5.2f}  win {wr:4.1f}%"
    if base is None: base=res[name]
    else:
        d=[a[2]-b[2] for a,b in zip(res[name],base)]
        dm=statistics.mean(d); dsd=statistics.pstdev(d) or 1e-9
        dt=dm/(dsd/math.sqrt(len(d)))
        wins=0
        for early in (True,False):
            for ga in (True,False):
                dd=[a[2]-b[2] for a,b in zip(res[name],base) if a[0]==early and a[1]==ga]
                if len(dd)>=30 and statistics.mean(dd)>0: wins+=1
        line+=f"\n      vs barrier: {dm:+.4f}%/trade  t={dt:+5.2f}  splits better {wins}/4"
    print(line)
