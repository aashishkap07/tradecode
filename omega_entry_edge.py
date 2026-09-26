"""Can ANY entry condition beat the null?

THE SETUP, and it is bleak by construction. Across 331,400 bars and 30
target/stop pairs, NOT ONE geometry is net positive after maker-both fees; the
least-bad loses 0.0233 %/trade. So an entry filter must ADD at least that much
just to reach zero. This measures every condition the bot already computes, or
could compute from price alone, against that bar.

Same discipline throughout: non-overlapping entries, adverse extreme first,
both directions, four-way split (time early/late x pairs A/B).
"""
import os, glob, statistics, math

FEE, H, STRIDE = 0.04, 32, 32
GEOMS = {'shipped 2.00R/0.75R': (2.00, 0.75), 'least-bad 0.50R/2.00R': (0.50, 2.00)}

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

def feats(rows):
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

def ef_ratio(rows,i,n=20):
    if i<n: return None
    net=abs(rows[i][4]-rows[i-n][4])
    path=sum(abs(rows[k][4]-rows[k-1][4]) for k in range(i-n+1,i+1))
    return net/path if path>1e-12 else None

def mom(rows,i,n):
    if i<n or rows[i-n][4]<=0: return None
    return (rows[i][4]/rows[i-n][4]-1)*100.0

def barrier(rows,i,side,R,t,st):
    e=rows[i][4]; sg=1.0 if side=='long' else -1.0
    tp=e*(1+sg*t*R/100.0); sl=e*(1-sg*st*R/100.0)
    for b in rows[i+1:i+1+H]:
        adv=b[3] if side=='long' else b[2]; fav=b[2] if side=='long' else b[3]
        if (side=='long' and adv<=sl) or (side=='short' and adv>=sl): return -st*R-FEE
        if (side=='long' and fav>=tp) or (side=='short' and fav<=tp): return t*R-FEE
    j=min(i+H,len(rows)-1)
    return sg*(rows[j][4]/e-1)*100.0-FEE

data=load(); syms=sorted(data); A=set(syms[::2])
recs=[]
for s_ in syms:
    rows=data[s_]; atr=feats(rows); half=len(rows)//2
    for i in range(30,len(rows)-H-1,STRIDE):
        if atr[i] is None or atr[i]<=0: continue
        R=2.0*atr[i]
        er=ef_ratio(rows,i); m4=mom(rows,i,16); m24=mom(rows,i,96)
        hh=int(((rows[i][0]//3600000)%24))
        for side in ('long','short'):
            out={k:barrier(rows,i,side,R,*g) for k,g in GEOMS.items()}
            recs.append(dict(early=i<half, ga=s_ in A, side=side, atr=atr[i],
                             er=er, m4=m4, m24=m24, hour=hh, out=out))
print(f"{len(recs):,} entries, {len(syms)} pairs\n")

def show(title, sel, geom):
    v=[r['out'][geom] for r in recs if sel(r)]
    if len(v)<200: return None
    m=statistics.mean(v); sd=statistics.pstdev(v) or 1e-9
    t=m/(sd/math.sqrt(len(v)))
    sp=0
    for e_ in (True,False):
        for g_ in (True,False):
            d=[r['out'][geom] for r in recs if sel(r) and r['early']==e_ and r['ga']==g_]
            if len(d)>=50 and statistics.mean(d)>0: sp+=1
    flag=' <-- POSITIVE' if m>0 else ''
    print(f"    {title:<40} n={len(v):>6,} mean {m:+.4f}% t={t:+5.2f} splits+ {sp}/4{flag}")
    return m

for geom in GEOMS:
    print(f"  GEOMETRY: {geom}")
    show('ALL entries (the null)', lambda r: True, geom)
    # 1. orderliness -- the Atlas's one surviving edge
    ers=sorted(r['er'] for r in recs if r['er'] is not None)
    q=[ers[int(len(ers)*f)] for f in (0.2,0.4,0.6,0.8)]
    for lbl,lo,hi in [('orderliness Q1 (chop)',-1,q[0]),('orderliness Q2',q[0],q[1]),
                      ('orderliness Q3',q[1],q[2]),('orderliness Q4',q[2],q[3]),
                      ('orderliness Q5 (trending)',q[3],9)]:
        show(lbl, lambda r,lo=lo,hi=hi: r['er'] is not None and lo<=r['er']<hi, geom)
    # 2. momentum continuation
    show('with 4h momentum (same sign)',
         lambda r: r['m4'] is not None and ((r['m4']>0)==(r['side']=='long')), geom)
    show('against 4h momentum', 
         lambda r: r['m4'] is not None and ((r['m4']>0)!=(r['side']=='long')), geom)
    show('with 24h momentum (same sign)',
         lambda r: r['m24'] is not None and ((r['m24']>0)==(r['side']=='long')), geom)
    show('strong 24h mover >10%, with it',
         lambda r: r['m24'] is not None and abs(r['m24'])>10 and ((r['m24']>0)==(r['side']=='long')), geom)
    show('strong 24h mover >10%, against it',
         lambda r: r['m24'] is not None and abs(r['m24'])>10 and ((r['m24']>0)!=(r['side']=='long')), geom)
    # 3. volatility band
    ats=sorted(r['atr'] for r in recs)
    a1,a2=ats[len(ats)//3], ats[2*len(ats)//3]
    show('low volatility third', lambda r: r['atr']<a1, geom)
    show('mid volatility third', lambda r: a1<=r['atr']<a2, geom)
    show('high volatility third', lambda r: r['atr']>=a2, geom)
    print()
