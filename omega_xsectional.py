"""Cross-sectional momentum: rank the BOARD, not each pair alone.

WHY THIS AND NOT MORE GEOMETRY. Thirty target/stop pairs are all negative and
every per-pair entry condition tested is negative too. What has NEVER been
tested here is the one thing the bot structurally cannot see: it scores each
pair IN ISOLATION (60 independent scores, then picks the best), so it has no
concept of "strongest of the board" versus "strongest in absolute terms".
Cross-sectional momentum is the best-documented effect in the academic crypto
literature and it is invisible to a per-pair scorer by construction.

Method: at each 15m timestamp, rank every pair by its trailing N-bar return,
go LONG the top k and SHORT the bottom k, hold to the same barriers, same fees,
same four-way split, non-overlapping in time.
"""
import os, glob, statistics, math, collections

FEE, H, STRIDE = 0.04, 32, 32
GEOMS={'2.00R/0.75R':(2.00,0.75), '0.50R/2.00R':(0.50,2.00), '1.00R/1.00R':(1.00,1.00)}

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

def barrier(rows,i,side,R,t,st):
    e=rows[i][4]; sg=1.0 if side=='long' else -1.0
    tp=e*(1+sg*t*R/100.0); sl=e*(1-sg*st*R/100.0)
    for b in rows[i+1:i+1+H]:
        adv=b[3] if side=='long' else b[2]; fav=b[2] if side=='long' else b[3]
        if (side=='long' and adv<=sl) or (side=='short' and adv>=sl): return -st*R-FEE
        if (side=='long' and fav>=tp) or (side=='short' and fav<=tp): return t*R-FEE
    j=min(i+H,len(rows)-1)
    return sg*(rows[j][4]/e-1)*100.0-FEE

data=load(); syms=sorted(data)
# align on timestamp
idx={s:{r[0]:k for k,r in enumerate(data[s])} for s in syms}
allts=sorted(set.intersection(*[set(idx[s]) for s in syms]))
print(f"{len(syms)} pairs, {len(allts):,} aligned 15m timestamps "
      f"({len(allts)*15/1440:.0f} days)\n")
atr={s:atrs(data[s]) for s in syms}
A=set(syms[::2]); half=len(allts)//2

for LOOK in (16, 96):        # 4h and 24h trailing return
    for K in (3, 6):
        res=collections.defaultdict(list)
        for ti in range(LOOK+20, len(allts)-H-1, STRIDE):
            ts=allts[ti]
            rets=[]
            for s in syms:
                k=idx[s][ts]
                if k<LOOK+20 or k>=len(data[s])-H-1: continue
                if atr[s][k] is None or atr[s][k]<=0: continue
                p0,p1=data[s][k-LOOK][4], data[s][k][4]
                if p0>0: rets.append((100.0*(p1/p0-1), s, k))
            if len(rets)<12: continue
            rets.sort()
            picks=[(s,k,'short') for _,s,k in rets[:K]] + [(s,k,'long') for _,s,k in rets[-K:]]
            for s,k,side in picks:
                R=2.0*atr[s][k]
                for gname,(t,st) in GEOMS.items():
                    res[gname].append((ti<half, s in A,
                                       barrier(data[s],k,side,R,t,st)))
        print(f"  LOOKBACK {LOOK*15//60}h   top/bottom {K} of {len(syms)}")
        for gname in GEOMS:
            v=[x[2] for x in res[gname]]
            if len(v)<200: continue
            m=statistics.mean(v); sd=statistics.pstdev(v) or 1e-9
            t=m/(sd/math.sqrt(len(v)))
            wr=100.0*sum(1 for x in v if x>0)/len(v)
            sp=0
            for e_ in (True,False):
                for g_ in (True,False):
                    d=[x[2] for x in res[gname] if x[0]==e_ and x[1]==g_]
                    if len(d)>=50 and statistics.mean(d)>0: sp+=1
            flag=''
            if m>0 and sp>=3: flag='  <<< POSITIVE AND REPLICATES'
            elif m>0: flag='  <-- positive, splits weak'
            print(f"      {gname:<14} n={len(v):>5,} mean {m:+.4f}% t={t:+5.2f} "
                  f"win {wr:4.1f}% splits+ {sp}/4{flag}")
        print()
