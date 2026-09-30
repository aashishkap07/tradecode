#!/usr/bin/env python3
"""C515 (descriptive, a venue comparison -- no rule is chosen here): the N2+N3
book at dial 20% on the same 2020-26 Binance archive, costed as Bitget or as
Binance USD-M futures.

- Bitget (what the research assumed): 0.08% per unit turnover (0.06% taker +
  0.02% half-spread), a $6 floor on every coin.
- Binance: 0.07% (0.05% taker, Binance FAQ 360033544231, + 0.02% half-spread)
  and 0.065% (paying fees in BNB, 10% off the taker fee); per-coin order
  minimums from Binance's announcements (2023-11-02, 2023-11-22): BTC $100;
  ETH, LINK, LTC, BCH, ETC $20; every other coin $5 (with the bot's own $6
  floor on top). A target below its coin's minimum is not held.

    python3 research/c515_venue_cost.py BNC_DIR
"""
import os, sys, math, warnings
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omega_c488_research as R
from omega_c493_research import TRADFI

warnings.simplefilter('ignore')
R.EXCLUDE = set(R.EXCLUDE) | TRADFI
R.TOPN = 20
T, syms, close, qv, fund = R.load_crypto(sys.argv[1])
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
N = 20; n = len(T)
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
W0 = R.combine(parts, r, fund, 1, target_vol=20 * 4 / 3 / 100)
BIG = {'BTCUSDT': 100.0, 'ETHUSDT': 20.0, 'LINKUSDT': 20.0, 'LTCUSDT': 20.0, 'BCHUSDT': 20.0, 'ETCUSDT': 20.0}
fl_binance = np.array([max(6.0, BIG.get(s, 5.0)) for s in syms])


def run(eq, floors, cost):
    W = np.where(np.abs(W0) * eq >= floors[None, :], W0, 0.0)
    x, info = R.pnl(W, r, fund, 1, cost=cost)
    live = np.nonzero(np.abs(x) > 0)[0][0] + 1
    y = x[live:]
    mo = np.prod(1 + y) ** (365 / len(y) / 12) - 1
    sh = y.mean() / y.std() * math.sqrt(365)
    e = np.cumprod(1 + y); dd = float((1 - e / np.maximum.accumulate(e)).max())
    held = (np.abs(W) > 0)[live:].sum(1).mean()
    return mo, sh, dd, held, info['cost'][live:].sum() / (len(y) / 365)


jb, je = syms.index('BTCUSDT'), syms.index('ETHUSDT')
share = lambda eq, j: float(((np.abs(W0[:, j]) * eq >= 6.0) & (np.abs(W0[:, j]) * eq < fl_binance[j])).sum()
                            / max(1, (np.abs(W0[:, j]) * eq >= 6.0).sum()))
print("C515 (descriptive): the N2+N3 book, dial 20%, the 2020-26 Binance archive, costed per venue")
for eq in (250.0, 500.0, 1000.0):
    print(f"\n  equity ${eq:.0f}   (Binance's minimums remove {100*share(eq, jb):.0f}% of BTC's and "
          f"{100*share(eq, je):.0f}% of ETH's otherwise-held days)")
    for lab, floors, cost in (("Bitget: 0.08%/turnover, $6 floor (the research)", np.full(len(syms), 6.0), 0.0008),
                              ("Binance: 0.07%, Binance minimums", fl_binance, 0.0007),
                              ("Binance + BNB fees: 0.065%, Binance minimums", fl_binance, 0.00065)):
        mo, sh, dd, held, c = run(eq, floors, cost)
        print(f"    {lab:48} {100*mo:+5.2f}%/mo  Sharpe {sh:.2f}  maxDD {100*dd:4.1f}%  "
              f"{held:4.1f} coins held  costs {100*c:4.1f}%/yr")
