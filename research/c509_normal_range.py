#!/usr/bin/env python3
"""C509: the book's normal range -- percentiles of its k-day returns in 2020-26
(crypto top 20, dial 15%), for the dashboard's "is this normal?" line.

    python3 research/c509_normal_range.py BNC_DIR [--out results.json]
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
r2, Wb, eb = R.crypto_sleeves(T, close, qv, fund)
W = R.combine({k: Wb[k] for k in ('C1', 'C2', 'C3')}, r2, fund, 1, target_vol=0.20)
W = np.where(np.abs(W) * 250.0 >= 6.0, W, 0.0)
x = R.pnl(W, r2, fund, 1)[0]
x = x[np.nonzero(np.abs(x) > 0)[0][0]:]
eq = np.cumprod(1 + x)
P = (1, 5, 10, 25, 50, 75, 90, 95, 99)
out = {}
for k in (1, 2, 3, 4, 5, 7, 10, 14, 21, 30, 45, 60, 90, 120, 182, 365):
    rk = eq[k:] / eq[:-k] - 1
    out[k] = [round(float(np.percentile(rk, p)), 5) for p in P]
    print(f"  {k:3d} days: " + "  ".join(f"p{p} {100*v:+6.1f}%" for p, v in zip(P, out[k])))
if '--out' in sys.argv:
    json.dump({'percentiles': list(P), 'days': {str(k): v for k, v in out.items()}}, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
