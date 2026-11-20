#!/usr/bin/env python3
"""C512 (descriptive): what one day of extra signal delay costs the book.

Until C512 the bot's 00:05 UTC rebalance read the just-finished day's candle
from Bitget's history endpoint, which still held a snapshot from the first
minutes of that day: the decision used, in effect, the previous day's close.
That is the research's lag 1 becoming lag 2. This measures the difference on
the 2020-26 archive (crypto top 20, $6 floor at $250, costs and funding),
for the admitted rule and N2+N3, at dials 15% and 20%.

    python3 research/c512_lag_cost.py BNC_DIR
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
sc = np.nan_to_num(R.vol_scale(sd)); N = 20; n = len(T)
f7 = np.full_like(fund, np.nan)
for i in range(7, n):
    f7[i] = fund[i - 6:i + 1].sum(axis=0)
f7[np.isnan(close)] = np.nan
s_base = R.xs_rank(R.lagret(close, 14), elig)
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


def book(rank, dial, lag):
    parts = {'C1': R.banded(np.where(elig, tr * sc / N, 0.0)),
             'C2': R.weekly(rank * sc / (2 * N * 0.2), T),
             'C3': R.weekly(-R.xs_rank(f7, elig) * sc / (2 * N * 0.2), T)}
    W = R.combine(parts, r, fund, 1, target_vol=dial * 4 / 3 / 100)
    W = np.where(np.abs(W) * 250.0 >= 6.0, W, 0.0)
    return R.pnl(W, r, fund, lag)[0]


print("C512: one extra day of signal delay (lag 1 = as researched, lag 2 = the stale-candle bot)")
for lab, rank in (('admitted', s_base), ('N2+N3', s23)):
    for dial in (15, 20):
        x1, x2 = book(rank, dial, 1), book(rank, dial, 2)
        live = np.nonzero(np.abs(x1) > 0)[0][0] + 1
        a1, a2 = x1[live:], x2[live:]
        cagr = lambda a: (np.prod(1 + a) ** (365 / len(a)) - 1)
        sh = lambda a: a.mean() / a.std() * math.sqrt(365)
        dd = lambda a: float((1 - np.cumprod(1 + a) / np.maximum.accumulate(np.cumprod(1 + a))).max())
        print(f"  {lab:9} dial {dial}%: lag 1 {100*cagr(a1):+.1f}%/yr Sharpe {sh(a1):.2f} DD {100*dd(a1):.1f}% | "
              f"lag 2 {100*cagr(a2):+.1f}%/yr Sharpe {sh(a2):.2f} DD {100*dd(a2):.1f}% | "
              f"cost {100*(cagr(a1)-cagr(a2)):+.1f} pts/yr")


# ── the bot's actual defect, more exactly: only the PRICE inputs were a day old
# (the just-finished day's close was a first-minutes snapshot, i.e. about the
# previous close); funding came from its own endpoint and was current. So the
# trend signs, the 14-day ranks and the per-coin volatility read close t-1 at
# the decision for day t, while carry and the P&L are unchanged.
cl_s = np.vstack([np.full((1, close.shape[1]), np.nan), close[:-1]])
cl_s = np.where(np.isnan(cl_s), close, cl_s)
r_s = R.returns(cl_s); sd_s = R.trailing_std(r_s, 30); sc_s = np.nan_to_num(R.vol_scale(sd_s))
tr_s = sum(np.sign(np.nan_to_num(R.lagret(cl_s, d))) for d in (7, 14, 28, 56)) / 4.0
sb_s = R.xs_rank(R.lagret(cl_s, 14), elig)
mkt_s = np.nan_to_num(np.nanmean(np.where(elig, r_s, np.nan), axis=1))
beta_s = np.ones_like(close)
for i in range(60, n):
    m = mkt_s[i - 59:i + 1]; vm = m.var()
    if vm <= 0:
        continue
    ri = r_s[i - 59:i + 1]; ok = ~np.isnan(ri)
    cov = np.nanmean((ri - np.nanmean(ri, axis=0)) * (m - m.mean())[:, None], axis=0)
    b = cov / vm; b[ok.sum(0) < 40] = np.nan
    beta_s[i] = np.where(np.isnan(b), 1.0, b)
m14_s = np.full(n, np.nan)
for i in range(14, n):
    m14_s[i] = np.prod(1 + mkt_s[i - 13:i + 1]) - 1
s3_s = R.xs_rank(R.lagret(cl_s, 14) - beta_s * m14_s[:, None], elig)
s23_s = np.where((s3_s < 0) & (np.nan_to_num(f7, nan=0.0) < 0), 0.0, s3_s)


def book_stale(rank, dial):
    parts = {'C1': R.banded(np.where(elig, tr_s * sc_s / N, 0.0)),
             'C2': R.weekly(rank * sc_s / (2 * N * 0.2), T),
             'C3': R.weekly(-R.xs_rank(f7, elig) * sc_s / (2 * N * 0.2), T)}
    W = R.combine(parts, r, fund, 1, target_vol=dial * 4 / 3 / 100)
    W = np.where(np.abs(W) * 250.0 >= 6.0, W, 0.0)
    return R.pnl(W, r, fund, 1)[0]


print("\nthe bot's actual defect (price inputs a day old, funding current):")
for lab, rank, rank_s in (('admitted', s_base, sb_s), ('N2+N3', s23, s23_s)):
    for dial in (15, 20):
        x1, x2 = book(rank, dial, 1), book_stale(rank_s, dial)
        live = np.nonzero(np.abs(x1) > 0)[0][0] + 1
        a1, a2 = x1[live:], x2[live:]
        cagr = lambda a: (np.prod(1 + a) ** (365 / len(a)) - 1)
        sh = lambda a: a.mean() / a.std() * math.sqrt(365)
        dd = lambda a: float((1 - np.cumprod(1 + a) / np.maximum.accumulate(np.cumprod(1 + a))).max())
        print(f"  {lab:9} dial {dial}%: correct {100*cagr(a1):+.1f}%/yr Sharpe {sh(a1):.2f} DD {100*dd(a1):.1f}% | "
              f"stale prices {100*cagr(a2):+.1f}%/yr Sharpe {sh(a2):.2f} DD {100*dd(a2):.1f}% | "
              f"cost {100*(cagr(a1)-cagr(a2)):+.1f} pts/yr")
