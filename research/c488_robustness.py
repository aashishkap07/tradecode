import os
import sys, numpy as np, math, datetime as dt, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import omega_c488_research as R
SP = sys.argv[1]
T, syms, close, qv, fund = R.load_crypto(SP)
r, W, elig = R.crypto_sleeves(T, close, qv, fund)
parts = {k: W[k] for k in ('C1', 'C2', 'C3')}
Wc = R.combine(parts, r, fund, 1)
def yearly(ret, label):
    ys = {}
    for t, x in zip(T, ret):
        y = dt.datetime.utcfromtimestamp(t / 1000).year; ys.setdefault(y, []).append(x)
    print(f"  {label:34}" + '  '.join(f"{y}:{100*sum(v):+6.1f}%" for y, v in sorted(ys.items())))
print("BY CALENDAR YEAR (sum of daily net returns)")
for k in ('C1', 'C2', 'C3'):
    yearly(R.pnl(W[k], r, fund, 1)[0], k)
base, d = R.pnl(Wc, r, fund, 1)
yearly(base, 'COMBO-C')
print("\nLAST 12 AND 24 MONTHS")
for n in (365, 730):
    R.show(f'COMBO-C last {n} days', R.stats(base[-n:], T[-n:]))
    for k in ('C1', 'C2', 'C3'):
        R.show(f'  {k} last {n} days', R.stats(R.pnl(W[k], r, fund, 1)[0][-n:], T[-n:]))
print("\nCOST SENSITIVITY (same weights)")
for c in (0.0008, 0.0012, 0.0016, 0.0024):
    R.show(f'COMBO-C cost {100*c:.2f}%/turnover', R.stats(R.pnl(Wc, r, fund, 1, cost=c)[0], T))
print("\nEXECUTION ONE DAY LATE (signal at close t, traded at close t+1)")
R.show('COMBO-C lag 2', R.stats(R.pnl(Wc, r, fund, 2)[0], T))
print("\nWITHOUT FUNDING (to see how much of it is funding income)")
R.show('COMBO-C funding ignored', R.stats(R.pnl(Wc, r, np.zeros_like(fund), 1)[0], T))
print(f"\n  funding contribution {100*d['funding'].mean()*365:+.1f}%/yr, gross {100*d['gross'].mean()*365:+.1f}%/yr, cost {100*d['cost'].mean()*365:.1f}%/yr")
print("\nSLEEVE CORRELATIONS (daily net, unit scale)")
U = {k: R.pnl(W[k], r, fund, 1)[0] for k in W}
live = slice(120, None)
for a in U:
    print('  ' + a + ' ' + ' '.join(f"{np.corrcoef(U[a][live], U[b][live])[0,1]:+.2f}" for b in U))
print("\nTOP-N SENSITIVITY IS NOT RE-RUN HERE (N=40 is pre-registered)")
