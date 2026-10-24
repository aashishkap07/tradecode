#!/usr/bin/env python3
"""C518 (descriptive): what India's tax rules do to the book's returns.

The same N2+N3 book at dial 20% on the 2020-26 Binance archive, costed as
Binance (0.07% per unit turnover), at $500. Every position is followed from
open to close (an "episode": one coin, one side), with its price P&L,
funding and trading costs. Each calendar year is then taxed three ways
(31.2% = 30% + 4% cess; surcharge ignored at this size):

  A  NET:    tax on the year's net profit, losses offset (business income --
             the "aggressive" reading for INR-settled derivatives; slab rates
             could be lower or higher than 31.2%)
  B  STRICT: s.115BBH read strictly -- every closed position's GAIN taxed,
             every LOSS ignored (no set-off of a VDA loss against any
             income). A LOWER BOUND under that reading: partial trims inside
             a position are further "transfers" and would add more tax.
  0  none (the pre-tax research figures).

The CA decides which applies (Atlas #8). This only measures what each costs.

    python3 research/c518_tax_india.py BNC_DIR
"""
import os, sys, math, warnings, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
EQ, COST, TAX = 500.0, 0.0007, 0.312
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
wl = np.zeros_like(W); wl[1:] = W[:-1]                      # the position held during day i
dw = np.abs(np.diff(np.vstack([np.zeros(k), wl]), axis=0))
daily = np.nan_to_num(wl * np.nan_to_num(r)) - np.nan_to_num(wl * fund) - dw * COST   # per coin, per day
assert np.allclose(daily.sum(1), x, atol=1e-12), "the per-coin split must add up to the book's P&L"
year = np.array([dt.datetime.utcfromtimestamp(t / 1000).year for t in T])
live = np.nonzero(np.abs(x) > 0)[0][0]
eps = []                                                     # (year closed, P&L as a fraction of equity)
S = np.sign(wl)
for j in range(k):
    i = live
    while i < n:
        if S[i, j] == 0:
            i += 1
            continue
        e = i
        while i + 1 < n and S[i + 1, j] == S[e, j]:
            i += 1
        end = min(i + 1, n - 1)                              # the day it is closed (its exit cost falls there)
        eps.append((year[end], float(daily[e:end + 1, j].sum())))
        i += 1
print("C518 (descriptive): India's tax on the N2+N3 book, dial 20%, $500, Binance costs")
print(f"  {len(eps)} positions opened and closed, {sum(1 for _, p in eps if p > 0)} with a gain\n")
print("  year | pre-tax | A: tax on net profit | B: 115BBH strict (gains taxed, losses ignored) | gains / losses booked")
rows = []
for y in sorted(set(year[live:])):
    pre = float(np.prod(1 + x[(year == y) & (np.arange(n) >= live)]) - 1)
    g = sum(p for yy, p in eps if yy == y and p > 0)
    lo = sum(p for yy, p in eps if yy == y and p <= 0)
    net = g + lo
    a = pre - TAX * max(0.0, net)
    b = pre - TAX * g
    rows.append((y, pre, a, b))
    print(f"  {y} | {100*pre:+6.1f}% | {100*a:+6.1f}% | {100*b:+6.1f}% "
          f"| +{100*g:.0f}% / {100*lo:.0f}% of equity")
pre = np.array([r_[1] for r_ in rows]); A = np.array([r_[2] for r_ in rows]); B = np.array([r_[3] for r_ in rows])
need = 1.02 ** 12 - 1
print(f"\n  average year: pre-tax {100*pre.mean():+.1f}%, A {100*A.mean():+.1f}%, B {100*B.mean():+.1f}%")
print(f"  years at >= +26.8% (2%/month): pre-tax {int((pre >= need).sum())}/{len(pre)}, A {int((A >= need).sum())}/{len(A)}, "
      f"B {int((B >= need).sum())}/{len(B)}")
g_all = sum(p for _, p in eps if p > 0); l_all = sum(p for _, p in eps if p <= 0)
print(f"  over the whole run the gains were {g_all / (g_all + l_all):.1f}x the net profit: under B, 31.2% of the gains is "
      f"{100 * TAX * g_all / (g_all + l_all):.0f}% of the net profit")
