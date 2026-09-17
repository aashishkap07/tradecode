"""Does funding predict direction? The one information channel that IS backtestable.

THE HYPOTHESIS, and it is the best-documented one in perpetual futures: the
funding rate is the price the crowd pays to hold its position. Persistently
positive funding means longs are paying shorts, i.e. the book is crowded long.
A crowded book is fuel for a squeeze in the opposite direction. So: FADE
EXTREME FUNDING.

This is cross-sectional as well as absolute -- what matters is not "is funding
high" but "is funding high FOR THIS PAIR RIGHT NOW RELATIVE TO THE BOARD",
which is the one thing the bot's per-pair scorer structurally cannot see and
which C451-2 already computes for display.

Geometry and discipline are unchanged: R = 2 x ATR(14) 15m, barriers, adverse
extreme first, both directions, maker-both fees, non-overlapping entries.
"""
import os, glob, statistics, math, bisect

FEE, H = 0.04, 32
GEOMS={'2.00R/0.75R':(2.00,0.75),'1.00R/1.00R':(1.00,1.00),'0.50R/2.00R':(0.50,2.00)}

def load_px():
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

def load_fund():
    out={}
    for f in glob.glob('corpusF/*.csv'):
        rows=[]
        for ln in open(f):
            p=ln.strip().split(',')
            if len(p)<2: continue
            try: rows.append((int(p[0]), float(p[1])))
            except ValueError: pass
        rows.sort()
        if rows: out[os.path.basename(f)[:-4]]=rows
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

def barrier(rows,i,side,R,t,st):
    e=rows[i][4]; sg=1.0 if side=='long' else -1.0
    tp=e*(1+sg*t*R/100.0); sl=e*(1-sg*st*R/100.0)
    for b in rows[i+1:i+1+H]:
        adv=b[3] if side=='long' else b[2]; fav=b[2] if side=='long' else b[3]
        if (side=='long' and adv<=sl) or (side=='short' and adv>=sl): return -st*R-FEE
        if (side=='long' and fav>=tp) or (side=='short' and fav<=tp): return t*R-FEE
    j=min(i+H,len(rows)-1)
    return sg*(rows[j][4]/e-1)*100.0-FEE

px=load_px(); fu=load_fund()
syms=sorted(set(px)&set(fu))
print(f"{len(syms)} pairs with both price and funding\n")
atr={s:atrs(px[s]) for s in syms}
ftimes={s:[t for t,_ in fu[s]] for s in syms}

# entries ONE BAR AFTER each funding settlement -- the only moment the rate is
# a fact rather than a forecast
recs=[]
for s in syms:
    rows=px[s]; ts=[r[0] for r in rows]
    for ft,fr in fu[s]:
        i=bisect.bisect_left(ts, ft)
        if i<30 or i>=len(rows)-H-1: continue
        if atr[s][i] is None or atr[s][i]<=0: continue
        R=2.0*atr[s][i]
        recs.append(dict(sym=s,i=i,ts=ft,fr=fr,R=R,rows=rows))
print(f"{len(recs):,} funding-anchored entries")
if recs:
    tlo=min(r['ts'] for r in recs); thi=max(r['ts'] for r in recs)
    import datetime as dt
    print(f"window {dt.datetime.utcfromtimestamp(tlo/1000).date()} -> "
          f"{dt.datetime.utcfromtimestamp(thi/1000).date()}\n")
    mid=(tlo+thi)/2
    A=set(syms[::2])

# cross-sectional rank of funding at each settlement time
bytime={}
for r in recs: bytime.setdefault(r['ts'],[]).append(r)
for t,group in bytime.items():
    group.sort(key=lambda r:r['fr'])
    n=len(group)
    for k,r in enumerate(group):
        r['pct'] = k/(n-1) if n>1 else 0.5
        r['n_board']=n

def run(title, pick, geom):
    t,st=GEOMS[geom]
    v=[]
    for r in recs:
        side=pick(r)
        if side is None: continue
        v.append((r['ts']<mid, r['sym'] in A, barrier(r['rows'],r['i'],side,r['R'],t,st)))
    if len(v)<150: return
    x=[a[2] for a in v]
    m=statistics.mean(x); sd=statistics.pstdev(x) or 1e-9
    tt=m/(sd/math.sqrt(len(x)))
    wr=100.0*sum(1 for a in x if a>0)/len(x)
    sp=0
    for e_ in (True,False):
        for g_ in (True,False):
            d=[a[2] for a in v if a[0]==e_ and a[1]==g_]
            if len(d)>=40 and statistics.mean(d)>0: sp+=1
    flag=''
    if m>0 and sp>=3: flag='  <<< POSITIVE AND REPLICATES'
    elif m>0: flag='  <-- positive'
    print(f"    {title:<44} n={len(x):>5,} mean {m:+.4f}% t={tt:+5.2f} "
          f"win {wr:4.1f}% splits+ {sp}/4{flag}")

for geom in GEOMS:
    print(f"  GEOMETRY {geom}")
    run('both directions on every settlement (null)', lambda r:'long', geom)
    run('FADE: short top-decile funding', lambda r:'short' if r['pct']>=0.9 else None, geom)
    run('FADE: long bottom-decile funding', lambda r:'long' if r['pct']<=0.1 else None, geom)
    run('FADE: both tails (the real rule)',
        lambda r:'short' if r['pct']>=0.9 else ('long' if r['pct']<=0.1 else None), geom)
    run('FOLLOW: long top-decile funding',
        lambda r:'long' if r['pct']>=0.9 else None, geom)
    run('FADE on ABSOLUTE funding > +0.05%/8h',
        lambda r:'short' if r['fr']>0.0005 else None, geom)
    run('FADE on ABSOLUTE funding < -0.05%/8h',
        lambda r:'long' if r['fr']<-0.0005 else None, geom)
    print()
