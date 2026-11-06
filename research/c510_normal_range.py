#!/usr/bin/env python3
"""C510: the normal range of the N2+N3 book (the rule the paper book trades from
C510) -- percentiles of its k-day returns in 2020-26, crypto top 20, dial 15%,
the same construction as research/c509_normal_range.py (which measured the
admitted rule). For the dashboard's "is this normal?" line.

    python3 research/c510_normal_range.py BNC_DIR [--out results.json]
"""
import os, sys, json, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
sc = np.nan_to_num(R.vol_scale(sd)); N = R.TOPN; n = len(T)
f7 = np.full_like(fund, np.nan)
for i in range(7, n):
    f7[i] = fund[i - 6:i + 1].sum(axis=0)
f7[np.isnan(close)] = np.nan
# N3: residual 14-day momentum (omega_c507_research.py), then N2: no crowded short
mkt = np.nan_to_num(np.nanmean(np.where(elig, r, np.nan), axis=1))
beta = np.ones_like(close)
for i in range(60, n):
    m = mkt[i - 59:i + 1]; vm = m.var()
    if vm <= 0:
        continue
    ri = r[i - 59:i + 1]; ok = ~np.isnan(ri)
    cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
    b = cov / vm; b[ok.sum(0) < 40] = np.nan
    beta[i] = np.where(np.isnan(b), 1.0, b)
m14 = np.full(n, np.nan)
for i in range(14, n):
    m14[i] = np.prod(1 + mkt[i - 13:i + 1]) - 1
s3 = R.xs_rank(R.lagret(close, 14) - beta * m14[:, None], elig)
s23 = np.where((s3 < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s3)
tr = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
parts = {'C1': R.banded(np.where(elig, tr * sc / N, 0.0)),
         'C2': R.weekly(s23 * sc / (2 * N * 0.2), T),
         'C3': R.weekly(-R.xs_rank(f7, elig) * sc / (2 * N * 0.2), T)}
W = R.combine(parts, r, fund, 1, target_vol=0.20)
W = np.where(np.abs(W) * 250.0 >= 6.0, W, 0.0)
x = R.pnl(W, r, fund, 1)[0]
x = x[np.nonzero(np.abs(x) > 0)[0][0]:]
eq = np.cumprod(1 + x)
P = (1, 5, 10, 25, 50, 75, 90, 95, 99)
out = {}
for k in (1, 2, 3, 4, 5, 7, 10, 14, 21, 30, 45, 60, 90, 120, 182, 365):
    rk = eq[k:] / eq[:-k] - 1
    out[k] = [round(float(np.percentile(rk, p)), 5) for p in P]
    print(f"  {k:3d} days: " + "  ".join(f"p{p} {100*v:+6.1f}%" for p, v in zip(P, out[k])))
if '--out' in sys.argv:
    json.dump({'percentiles': list(P), 'rule': 'n2n3', 'days': {str(k): v for k, v in out.items()}},
              open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
