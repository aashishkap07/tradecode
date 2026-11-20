"""Is there ANY target/stop pair that is net positive after maker-both fees?

This is the question the whole project rests on. C460-5 measured the best GROSS
geometry edge at +0.0171 %/trade against a 0.08% taker round trip. C461 halved
the fee to 0.04%. So: does halving the cost lift any geometry above zero?

Random entries are the honest null -- the project's own measurement is
rho(score, win) = -0.022, so the entry score carries no cross-sectional
information and an unbiased entry IS the bot's entry, statistically.
"""
import os, glob, statistics, math

FEE, H, STRIDE = 0.04, 32, 32

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

TARGETS=[0.5,0.75,1.0,1.5,2.0,3.0]
STOPS=[0.5,0.75,1.0,1.5,2.0]

data=load(); syms=sorted(data); A=set(syms[::2])
cells={(t,st):[] for t in TARGETS for st in STOPS}
for s_ in syms:
    rows=data[s_]; atr=atrs(rows); half=len(rows)//2
    for i in range(20,len(rows)-H-1,STRIDE):
        if atr[i] is None or atr[i]<=0: continue
        R=2.0*atr[i]; e=rows[i][4]
        win=rows[i+1:i+1+H]
        for side in ('long','short'):
            sg=1.0 if side=='long' else -1.0
            for t in TARGETS:
                for st in STOPS:
                    tp=e*(1+sg*t*R/100.0); sl=e*(1-sg*st*R/100.0)
                    out=None
                    for b in win:
                        adv=b[3] if side=='long' else b[2]
                        fav=b[2] if side=='long' else b[3]
                        if (side=='long' and adv<=sl) or (side=='short' and adv>=sl):
                            out=-st*R-FEE; break
                        if (side=='long' and fav>=tp) or (side=='short' and fav<=tp):
                            out=t*R-FEE; break
                    if out is None:
                        out=sg*(win[-1][4]/e-1)*100.0-FEE if win else -FEE
                    cells[(t,st)].append((i<half, s_ in A, out))

print(f"corpus {len(syms)} pairs, {sum(len(v) for v in data.values()):,} bars, "
      f"{len(cells[(2.0,0.75)]):,} trades per cell, maker both (0.04%)\n")
print(f"  {'target':>7} {'stop':>5} {'mean %/tr':>10} {'t':>7} {'win%':>6} {'splits+':>8}")
best=[]
for t in TARGETS:
    for st in STOPS:
        v=[x[2] for x in cells[(t,st)]]
        m=statistics.mean(v); sd=statistics.pstdev(v) or 1e-9
        tt=m/(sd/math.sqrt(len(v)))
        wr=100.0*sum(1 for x in v if x>0)/len(v)
        sp=0
        for early in (True,False):
            for ga in (True,False):
                dd=[x[2] for x in cells[(t,st)] if x[0]==early and x[1]==ga]
                if len(dd)>=30 and statistics.mean(dd)>0: sp+=1
        mark=' <<<' if m>0 else ''
        print(f"  {t:>7.2f} {st:>5.2f} {m:>+10.4f} {tt:>+7.2f} {wr:>6.1f} {sp:>6}/4{mark}")
        best.append((m,t,st,tt,sp))
best.sort(reverse=True)
print(f"\n  BEST CELL: target {best[0][1]}R stop {best[0][2]}R -> {best[0][0]:+.4f}%/trade "
      f"t={best[0][3]:+.2f}, {best[0][4]}/4 splits")
print(f"  cells net positive: {sum(1 for b in best if b[0]>0)} of {len(best)}")
print(f"  shipped cell (2.00R / 0.75R): "
      f"{[b for b in best if b[1]==2.0 and b[2]==0.75][0][0]:+.4f}%/trade")
