#!/usr/bin/env python3
"""C507: how unusual is the book's first 4 days (25-28 Sep 2026: live -3.9%,
the same rule simulated on Bitget data -2.9%), and what followed such starts
in 2020-26? Descriptive only; nothing is admitted or changed.

    python3 research/c507_start_context.py BNC_DIR [--out results.json]
"""
import os, sys, json, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r2, Wb, eb = R.crypto_sleeves(T, close, qv, fund)
parts = {k: Wb[k] for k in ('C1', 'C2', 'C3')}
W = R.combine(parts, r2, fund, 1, target_vol=0.20)
W = np.where(np.abs(W) * 250.0 >= 6.0, W, 0.0)
x = R.pnl(W, r2, fund, 1)[0]
live = np.nonzero(np.abs(x) > 0)[0][0]
x = x[live:]; TT = T[live:]
eq = np.cumprod(1 + x)
n = len(x)
out = {}
print("=" * 100)
print(f"C507: THE BOOK'S FIRST DAYS IN CONTEXT | crypto top 20, dial 15% | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()} ({n} days)")
print("=" * 100)
for k, thr in ((4, -0.029), (4, -0.039), (5, -0.045)):
    rk = eq[k:] / eq[:-k] - 1
    hit = rk <= thr
    per_year = hit.sum() / (n / 365)
    # non-overlapping events: the first day of each run of hits
    ev = [i for i in range(len(hit)) if hit[i] and (i == 0 or not hit[i - 1])]
    fw = {}
    for h in (30, 90, 182, 365):
        vals = [eq[i + k + h] / eq[i + k] - 1 for i in ev if i + k + h < n]
        fw[h] = (float(np.median(vals)) if vals else float('nan'), float(np.mean(np.array(vals) > 0)) if vals else float('nan'), len(vals))
    print(f"  {k}-day loss of {100*-thr:.1f}% or more: in {100*hit.mean():.1f}% of all {k}-day spans; about {per_year:.1f} separate "
          f"episodes a year ({len(ev)} in {n/365:.1f} years)")
    print("      what followed (from the end of the episode): " + " | ".join(
        f"{h}d median {100*m:+.1f}%, positive {100*p:.0f}% of {c}" for h, (m, p, c) in fw.items()))
    out[f'{k}d_{thr}'] = dict(share=float(hit.mean()), per_year=per_year, episodes=len(ev),
                              after={str(h): dict(median=m, p_pos=p, n=c) for h, (m, p, c) in fw.items()})
print("\n  STARTING ON A RANDOM DAY: the chance of being below the start after ...")
for h in (4, 7, 14, 30, 60, 90, 182, 365):
    rh = eq[h:] / eq[:-h] - 1
    print(f"   {h:3d} days: {100*np.mean(rh < 0):4.0f}% below | median {100*np.median(rh):+6.1f}% | 10th pct {100*np.percentile(rh, 10):+6.1f}% "
          f"| 90th pct {100*np.percentile(rh, 90):+6.1f}%")
    out[f'random_start_{h}d'] = dict(p_below=float(np.mean(rh < 0)), median=float(np.median(rh)),
                                     p10=float(np.percentile(rh, 10)), p90=float(np.percentile(rh, 90)))
dd = 1 - eq / np.maximum.accumulate(eq)
under = dd > 0
runs, cur = [], 0
for u in under:
    if u:
        cur += 1
    else:
        if cur:
            runs.append(cur)
        cur = 0
print(f"\n  time under water (days from a peak back to a new peak): median {np.median(runs):.0f}, "
      f"75th pct {np.percentile(runs, 75):.0f}, 95th pct {np.percentile(runs, 95):.0f}, longest {max(runs)}")
print(f"  share of days at a new equity high: {100*np.mean(dd == 0):.0f}%  (the rest are spent below a previous high)")
out['under_water'] = dict(median=float(np.median(runs)), p75=float(np.percentile(runs, 75)),
                          p95=float(np.percentile(runs, 95)), longest=int(max(runs)), p_new_high=float(np.mean(dd == 0)))
# momentum sleeve alone: how often does it lose 2.5%+ of equity in a week
Wc2 = R.combine({'C2': Wb['C2']}, r2, fund, 1, target_vol=0.20)
x2 = R.pnl(np.where(np.abs(Wc2) * 250 >= 6, Wc2, 0), r2, fund, 1)[0][live:]
e2 = np.cumprod(1 + x2); w7 = e2[7:] / e2[:-7] - 1
print(f"\n  the momentum sleeve alone (at the book's risk): a 7-day loss of 3% or more in {100*np.mean(w7 <= -0.03):.1f}% of weeks; "
      f"yet over 2020-26 it made {100*(e2[-1]**(365/len(x2))-1):+.1f}%/yr")
if '--out' in sys.argv:
    json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
