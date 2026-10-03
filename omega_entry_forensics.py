import re, glob, os, statistics as st
FILES=[f for f in sorted(glob.glob('omega_detail_*')) if not f.endswith('.gz')]
ent=[]
for fn in FILES:
    lines=open(fn,encoding='utf-8',errors='replace').read().splitlines()
    pru=atr=None
    for i,l in enumerate(lines):
        m=re.search(r'PRU:\s*([\d.]+)%\s*\|\s*EQI:\s*([-\d.]+)\s*\|\s*ATR:\s*([\d.]+)%',l)
        if m: pru,eqi,atr=float(m.group(1)),float(m.group(2)),float(m.group(3)); continue
        m=re.search(r'>>\s*\d\d:\d\d\s+OPEN\s+(\S+)\s+(LONG|SHORT)\s+@([\d.]+)\s+x(\d+)\s+\$([\d.]+)',l)
        if not m: continue
        sym,side,price,lev,margin=m.group(1),m.group(2),float(m.group(3)),int(m.group(4)),float(m.group(5))
        tgt=stop=score=None; fill=None
        for j in range(i+1,min(i+4,len(lines))):
            t=re.search(r'target\s*\+?([\d.]+)%\s+stop\s*-?([\d.]+)%\s+entry score\s*([\d.]+)\s+(\w+)',lines[j])
            if t: tgt,stop,score,fill=float(t.group(1)),float(t.group(2)),float(t.group(3)),t.group(4); break
        conf=None
        for j in range(i+1,min(i+8,len(lines))):
            c=re.search(r'Margin:\s*\$([\d.]+)\s*\|\s*Conf:\s*([\d.]+)',lines[j])
            if c: conf=float(c.group(2)); break
        if stop is None: continue
        ent.append(dict(sym=sym,side=side,margin=margin,lev=lev,stop=stop,tgt=tgt,
                        score=score,conf=conf,atr=atr,pru=pru,fill=fill,src=fn))
print(f"parsed {len(ent)} entries with a stop distance\n")
for e in ent: e['risk']=e['margin']*e['stop']/100.0
R=[e['risk'] for e in ent]
R.sort()
print("="*98)
print("THE REAL DOLLAR RISK PER TRADE  (margin x stop distance), against a stated $0.85")
print("="*98)
print(f"  n={len(R)}   min ${R[0]:.2f}   p10 ${R[len(R)//10]:.2f}   p25 ${R[len(R)//4]:.2f}   "
      f"median ${st.median(R):.2f}   p75 ${R[3*len(R)//4]:.2f}   p90 ${R[9*len(R)//10]:.2f}   max ${R[-1]:.2f}")
print(f"  spread min->max: {R[-1]/R[0]:.0f}x        within budget (<=$0.85): "
      f"{sum(1 for r in R if r<=0.85)}/{len(R)}")
print(f"  a risk-parity book would show EVERY one of these at ~$0.85")
print()
print("="*98)
print("WHY: IS MARGIN SCALED INVERSELY TO THE STOP, AS RISK PARITY REQUIRES?")
print("="*98)
print("  risk parity needs  margin = budget / stop,  i.e. margin x stop = constant")
print(f"  {'stop band':16} {'n':>3} {'median stop':>12} {'median margin':>14} {'needed':>9} {'median risk':>12}")
for lo,hi,nm in ((0,1,'< 1%'),(1,2,'1-2%'),(2,3,'2-3%'),(3,5,'3-5%'),(5,99,'> 5%')):
    ch=[e for e in ent if lo<=e['stop']<hi]
    if not ch: continue
    ms=st.median([e['stop'] for e in ch]); mm=st.median([e['margin'] for e in ch])
    print(f"  {nm:16} {len(ch):3} {ms:11.2f}% ${mm:13.2f} ${0.85/(ms/100):8.2f} "
          f"${st.median([e['risk'] for e in ch]):11.2f}")
print()
print("  'needed' is the margin that WOULD have risked the stated $0.85 at that stop.")
