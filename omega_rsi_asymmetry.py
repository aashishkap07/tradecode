"""Does the exhaustion penalty earn its keep?

    python3 omega_fetch_corpus_32.py     # 32 pairs x ~10,400 live 15m bars -> corpusL/
    python3 omega_rsi_asymmetry.py

RESULT ON 331,400 BARS / 32 PAIRS / 108 DAYS (2026-09-16):
    SHORT into RSI <= 30   -0.4266 %/trade vs normal,  t=-6.22,  4/4 splits
    LONG  into RSI >= 70   -0.0135 %/trade vs normal,  t=-1.23,  2/4 splits
The standing rule needs 3 of 4. The brake earns its keep on the SHORT side
decisively and does not clear the bar on the LONG side -- yet the code applies
it symmetrically, and on 2026-09-16 it stacked three times over on SYN (x0.84
overbought, x0.85 rejection candle, x0.75 wick = x0.536) and refused the best
trade on the board. NOTHING WAS CHANGED ON THIS EVIDENCE: a removal needs the
same 3-of-4 an addition does. C462-7 logs the cases so the record can settle it.


THE CLAIM UNDER TEST is the bot's own, applied three times over to SYN on
2026-09-16: a long into a high RSI is worse than a long that is not. SYN was
+71% on the day when the bot first scored it, carried an RSI of 77, and took
'overbought, stretched' -16%, 'bearish rejection candle' x0.85 and 'wick
rejection' x0.75 -- compounding to 0.54 of its score, which put 0.41 under a
0.58 bar. It then ran to +156% without the bot.

Geometry is the bot's own: R = 2 x ATR(14) on 15m, target 2.00R (C416),
stop 0.75R (C377), maker both ways (C461). Non-overlapping entries, adverse
extreme first inside every bar, both directions, four-way split.
"""
import os, glob, statistics, math

FEE, H, STRIDE = 0.04, 32, 32          # maker both; 8h horizon; non-overlapping
TARGET_R, STOP_R = 2.00, 0.75

def load():
    out = {}
    for f in sorted(glob.glob('corpusL/*.csv')):
        rows = []
        for ln in open(f):
            p = ln.strip().split(',')
            if len(p) < 6: continue
            try: rows.append(tuple(float(x) for x in p[:6]))
            except ValueError: pass
        rows.sort(key=lambda r: r[0])
        if len(rows) > 2000: out[os.path.basename(f)[:-4]] = rows
    return out

def indicators(rows):
    n=len(rows); atr=[None]*n; rsi=[None]*n
    tr=[0.0]*n
    for i in range(1,n):
        h,l,pc=rows[i][2],rows[i][3],rows[i-1][4]
        tr[i]=max(h-l,abs(h-pc),abs(l-pc))
    s=0.0
    for i in range(1,n):
        s+=tr[i]
        if i>14: s-=tr[i-14]
        if i>=14 and rows[i][4]: atr[i]=(s/14)/rows[i][4]*100.0
    g=l_=0.0
    for i in range(1,n):
        d=rows[i][4]-rows[i-1][4]
        up,dn=max(d,0.0),max(-d,0.0)
        if i<=14: g+=up/14; l_+=dn/14
        else:
            g=(g*13+up)/14; l_=(l_*13+dn)/14
            rsi[i]=100.0 if l_==0 else 100.0-100.0/(1+g/l_)
    return atr,rsi

def sim(rows,i0,side,R):
    e=rows[i0][4]; sg=1.0 if side=='long' else -1.0
    tp=e*(1+sg*TARGET_R*R/100.0); sl=e*(1-sg*STOP_R*R/100.0)
    for b in rows[i0+1:i0+1+H]:
        adv=b[3] if side=='long' else b[2]
        fav=b[2] if side=='long' else b[3]
        if (side=='long' and adv<=sl) or (side=='short' and adv>=sl):
            return -STOP_R*R-FEE
        if (side=='long' and fav>=tp) or (side=='short' and fav<=tp):
            return TARGET_R*R-FEE
    j=min(i0+H,len(rows)-1)
    return sg*(rows[j][4]/e-1)*100.0-FEE

data=load()
syms=sorted(data)
print(f"corpus: {len(syms)} pairs, {sum(len(v) for v in data.values()):,} bars "
      f"({sum(len(v) for v in data.values())//len(syms)*15/1440:.0f} days each)\n")
A=set(syms[::2]); recs=[]
for s in syms:
    rows=data[s]; atr,rsi=indicators(rows)
    half=len(rows)//2
    for i in range(20,len(rows)-H-1,STRIDE):
        if atr[i] is None or rsi[i] is None or atr[i]<=0: continue
        R=2.0*atr[i]
        for side in ('long','short'):
            recs.append((s, i<half, s in A, side, rsi[i], sim(rows,i,side,R), R))
print(f"entries: {len(recs):,} (non-overlapping, both directions)\n")

def stat(rs):
    if len(rs)<30: return None
    m=statistics.mean(rs); sd=statistics.pstdev(rs) or 1e-9
    return m, m/(sd/math.sqrt(len(rs))), len(rs), 100.0*sum(1 for x in rs if x>0)/len(rs)

def report(title, sel_a, sel_b, label_a, label_b):
    print(title)
    a=[r[5] for r in recs if sel_a(r)]; b=[r[5] for r in recs if sel_b(r)]
    for lbl,rs in ((label_a,a),(label_b,b)):
        st=stat(rs)
        print(f"  {lbl:<34} n={st[2]:>6,}  mean {st[0]:+.4f}%  t={st[1]:+5.2f}  win {st[3]:.1f}%"
              if st else f"  {lbl:<34} too few")
    if stat(a) and stat(b):
        d=stat(a)[0]-stat(b)[0]
        print(f"  {'DIFFERENCE (penalised - normal)':<34} {d:+.4f}%/trade")
        # four-way split
        wins=0
        for early in (True,False):
            for grpA in (True,False):
                aa=[r[5] for r in recs if sel_a(r) and r[1]==early and r[2]==grpA]
                bb=[r[5] for r in recs if sel_b(r) and r[1]==early and r[2]==grpA]
                if len(aa)>=30 and len(bb)>=30:
                    dd=statistics.mean(aa)-statistics.mean(bb)
                    wins += dd<0
                    print(f"      split {'early' if early else 'late ':<5} "
                          f"pairs {'A' if grpA else 'B'}: {dd:+.4f}%  "
                          f"({'penalty justified' if dd<0 else 'PENALTY COSTS MONEY'})")
        print(f"  splits where the penalty is justified: {wins}/4\n")

report("RSI >= 70 LONGS  (the SYN case)",
       lambda r: r[3]=='long' and r[4]>=70, lambda r: r[3]=='long' and r[4]<70,
       "long into RSI >= 70", "long, RSI < 70")
report("RSI >= 77 LONGS  (SYN's exact reading)",
       lambda r: r[3]=='long' and r[4]>=77, lambda r: r[3]=='long' and r[4]<77,
       "long into RSI >= 77", "long, RSI < 77")
report("RSI <= 30 SHORTS (the mirror)",
       lambda r: r[3]=='short' and r[4]<=30, lambda r: r[3]=='short' and r[4]>30,
       "short into RSI <= 30", "short, RSI > 30")
