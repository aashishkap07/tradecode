#!/usr/bin/env python3
"""C518 (descriptive): what "2%/month with 80% probability" demands, and where the book stands.

1. The arithmetic. For a strategy with annual Sharpe S at volatility sigma (log
   returns, normal), P(one year compounds to >= +26.8%, i.e. averages 2%/month)
   = Phi((S*sigma - sigma^2/2 - ln 1.268) / sigma). And P(a single month >= +2%).
2. The book (N2+N3, dial 20%, Binance costs, $500, + idle cash at 6.8%) by
   30-day block bootstrap: P(averaging >= 2%/month) over 1, 2 and 3 years,
   pre-tax, with the 1/3 haircut, and after tax read A (31.2% of each year's
   net profit; read B leaves ~0, research/c518_tax_india.txt).

    python3 research/c518_target_math.py BNC_DIR
"""
import os, sys, math, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
need = math.log(1.02 ** 12)
print("1. THE ARITHMETIC (normal log returns)")
print("   P(a year averages >= 2%/month)      Sharpe:  1.0    1.5    2.0    2.5    3.0")
for sig in (0.15, 0.25, 0.35, 0.50):
    row = [Phi((S * sig - sig * sig / 2 - need) / sig) for S in (1.0, 1.5, 2.0, 2.5, 3.0)]
    print(f"   at {100*sig:3.0f}% volatility                       " + '  '.join(f"{100*p:4.0f}%" for p in row))
print("   P(a single month >= +2%)")
for sig in (0.15, 0.25, 0.35):
    sm = sig / math.sqrt(12)
    row = [Phi((S * sig / 12 - 0.02) / sm) for S in (1.0, 1.5, 2.0, 2.5, 3.0)]
    print(f"   at {100*sig:3.0f}% volatility                       " + '  '.join(f"{100*p:4.0f}%" for p in row))

R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
EQ, COST = 500.0, 0.0007
BIG = {'BTCUSDT': 50.0, 'ETHUSDT': 20.0, 'LINKUSDT': 20.0, 'LTCUSDT': 20.0, 'BCHUSDT': 20.0, 'ETCUSDT': 20.0}
T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
N = 20; n, k = close.shape
sc = np.nan_to_num(R.vol_scale(sd))
f7 = np.full_like(fund, np.nan)
for i in range(7, n):
    f7[i] = fund[i - 6:i + 1].sum(axis=0)
f7[np.isnan(close)] = np.nan
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
W = R.combine(parts, r, fund, 1, target_vol=20 * 4 / 3 / 100)
floors = np.array([max(6.0, BIG.get(s, 5.0)) for s in syms])
W = np.where(np.abs(W) * EQ >= floors[None, :], W, 0.0)
x, info = R.pnl(W, r, fund, 1, cost=COST)
sav = np.clip(1.0 - info['gross_exp'] / 5.0 - 0.20 - 0.05, 0.0, 1.0) * 0.068 / 365.0
live = np.nonzero(np.abs(x) > 0)[0][0] + 1
y = (x + sav)[live:]
S = y.mean() / y.std() * math.sqrt(365); sig = y.std() * math.sqrt(365)
print(f"\n2. THE BOOK ON BINANCE ($500, dial 20%, idle cash at 6.8%): Sharpe {S:.2f} at {100*sig:.0f}% volatility, "
      f"{100*(np.prod(1+y)**(365/len(y)/12)-1):+.2f}%/month compounded (2020-26, pre-tax)")
rng = np.random.default_rng(518)


def boot(yy, days, reps=10000, block=30, tax=0.0):
    nb = int(math.ceil(days / block)); out = np.empty(reps)
    starts = rng.integers(0, len(yy) - block, size=(reps, nb))
    for q in range(reps):
        path = np.concatenate([yy[a:a + block] for a in starts[q]])[:days]
        g = 1.0
        for yr in range(0, days, 365):              # tax each year's net profit (read A)
            gy = np.prod(1 + path[yr:yr + 365])
            g *= gy - tax * max(0.0, gy - 1.0)
        out[q] = g ** (365.0 / days) - 1            # the annualised result
    return out


tgt = 1.02 ** 12 - 1
hair = y - y.mean() / 3.0
print("   P(averaging >= 2%/month)          1 year   2 years   3 years")
for lab, yy, tax in (("pre-tax, as backtested", y, 0.0), ("pre-tax, 1/3 haircut", hair, 0.0),
                     ("after tax A (31.2% of net profit)", y, 0.312), ("after tax A, 1/3 haircut", hair, 0.312)):
    ps = [float((boot(yy, d, tax=tax) >= tgt).mean()) for d in (365, 730, 1095)]
    print(f"   {lab:34} " + '   '.join(f"{100*p:5.0f}%" for p in ps))
print("   (after tax read B -- each gain taxed, losses ignored -- the book averages about 0%/year: "
      "research/c518_tax_india.txt)")
