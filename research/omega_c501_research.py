#!/usr/bin/env python3
"""C501 round 8 (research/c501_preregistration.md): S1 spot trend, long or flat,
cash in Savings -- the candidate strategy for a second $250.

    python3 research/omega_c501_research.py BNC_DIR [--out results.json]
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
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
sc = np.nan_to_num(R.vol_scale(sd)); N = R.TOPN
EQ, FLOOR, CASH, COST_SPOT = 250.0, 6.0, 0.05, 0.0010
HOLD = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
zero = np.zeros_like(fund)

# ── S1 ───────────────────────────────────────────────────────────────────────
s = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
W1 = R.banded(np.where(elig, np.maximum(s, 0.0) * sc / N, 0.0))
u = R.pnl(W1, r, zero, 1, cost=COST_SPOT)[0]
n = len(T); L = np.zeros(n)
for i in range(60, n):
    v = u[i - 60:i].std() * math.sqrt(365)
    L[i] = 0.20 / v if v > 0 else 0.0
W = W1 * L[:, None]
g = np.abs(W).sum(1)
W = W * np.where(g > 1.0, 1.0 / np.maximum(g, 1e-12), 1.0)[:, None]
W = np.where(np.abs(W) * EQ >= FLOOR, W, 0.0)
x_risk, parts = R.pnl(W, r, zero, 1, cost=COST_SPOT)
gl = np.zeros(n); gl[1:] = np.abs(W).sum(1)[:-1]                # yesterday's decision is today's exposure
x = x_risk + (1.0 - gl) * CASH / 365.0
live = np.nonzero(L > 0)[0][0] + 1
x, TT = x[live:], T[live:]
ex = x - CASH / 365.0


def maxdd(y):
    e = np.cumprod(1 + y); return float((1 - e / np.maximum.accumulate(e)).max())


def months(y, tt):
    m = {}
    for t, v in zip(tt, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[k] = m.get(k, 1.0) * (1 + v)
    return np.array([v - 1 for v in m.values()])


t = R.nw_t(ex); q = sum(v.mean() > 0 for v in np.array_split(ex, 4)); hold = ex[TT >= HOLD].mean(); dd = maxdd(x)
adm = bool(t >= 2.0 and q >= 3 and hold > 0 and dd <= 0.35)
mv = months(x, TT)
cagr = np.prod(1 + x) ** (365 / len(x)) - 1
print("=" * 100)
print(f"C501 S1 SPOT TREND, LONG OR FLAT, CASH AT 5% | top 20 crypto, vol set point 20%, gross <= 1, 0.10% cost, $6 floor | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()}")
print("=" * 100)
print(f"  S1: CAGR {100*cagr:+.1f}%/yr = {100*((1+cagr)**(1/12)-1):+.2f}%/month compounded | vol {100*x.std()*math.sqrt(365):.1f}% | "
      f"Sharpe {x.mean()/x.std()*math.sqrt(365):.2f} | max DD {100*dd:.1f}%")
print(f"      excess over cash: {100*ex.mean()*365:+.1f}%/yr  NW t {t:+.2f}  quarters+ {q}/4  holdout 2025-26 {100*hold*365:+.1f}%/yr  "
      f"-> {'ADMIT' if adm else 'not admitted'}")
print(f"      average exposure {100*gl[live:].mean():.0f}% invested (the rest in Savings); in the market {100*(gl[live:]>0.05).mean():.0f}% of days")
print(f"      months: mean {100*mv.mean():+.2f}%  median {100*np.median(mv):+.2f}%  >= +2%: {100*(mv>=0.02).mean():.0f}%  "
      f"positive {100*(mv>0).mean():.0f}%  worst {100*mv.min():+.1f}%  best {100*mv.max():+.1f}%")
yrs = {}
for tt_, v in zip(TT, x):
    y = dt.datetime.utcfromtimestamp(tt_ / 1000).year; yrs[y] = yrs.get(y, 1.0) * (1 + v)
print("      by year: " + "  ".join(f"{y} {100*(v-1):+.0f}%" for y, v in sorted(yrs.items())))

# ── benchmarks ───────────────────────────────────────────────────────────────
b = syms.index('BTCUSDT'); rb = np.nan_to_num(r[:, b])[live:]
ew = np.nanmean(np.where(elig, r, np.nan), axis=1); ew = np.nan_to_num(ew)[live:]
for lab, y in (('buy-and-hold BTC', rb), ('equal-weight top 20 (daily, no costs)', ew)):
    c = np.prod(1 + y) ** (365 / len(y)) - 1
    print(f"  {lab:38} CAGR {100*c:+6.1f}%/yr  Sharpe {y.mean()/y.std()*math.sqrt(365):.2f}  max DD {100*maxdd(y):.1f}%  "
          f"worst month {100*months(y, TT).min():+.1f}%")

# ── the futures book, and the two pots together ─────────────────────────────
r2, Wb, eb = R.crypto_sleeves(T, close, qv, fund)
Wc = R.combine({k: Wb[k] for k in ('C1', 'C2', 'C3')}, r2, fund, 1, target_vol=0.20)
Wc = np.where(np.abs(Wc) * EQ >= FLOOR, Wc, 0.0)
xb = R.pnl(Wc, r2, fund, 1)[0][live:]
rho = np.corrcoef(xb, x)[0, 1]
both = 0.5 * xb + 0.5 * x
cb = np.prod(1 + xb) ** (365 / len(xb)) - 1; c2 = np.prod(1 + both) ** (365 / len(both)) - 1
print(f"\n  futures book (COMBO-C, dial 15%) same period: CAGR {100*cb:+.1f}%/yr = {100*((1+cb)**(1/12)-1):+.2f}%/month, "
      f"max DD {100*maxdd(xb):.1f}% | correlation with S1: {rho:+.2f}")
mb = months(both, TT)
print(f"  both pots, $250 + $250: CAGR {100*c2:+.1f}%/yr = {100*((1+c2)**(1/12)-1):+.2f}%/month, Sharpe "
      f"{both.mean()/both.std()*math.sqrt(365):.2f}, max DD {100*maxdd(both):.1f}%, worst month {100*mb.min():+.1f}%, "
      f"months >= +2%: {100*(mb>=0.02).mean():.0f}%")
res = dict(cagr=float(cagr), sharpe=float(x.mean() / x.std() * math.sqrt(365)), maxdd=dd, t=float(t), quarters=int(q),
           holdout_excess=float(hold * 365), admit=adm, exposure=float(gl[live:].mean()), month_mean=float(mv.mean()),
           month_worst=float(mv.min()), years={str(k): float(v - 1) for k, v in yrs.items()},
           corr_book=float(rho), both_cagr=float(c2), both_maxdd=maxdd(both))
if '--out' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
