#!/usr/bin/env python3
"""C504: how likely is 2-4% a month? Measured on the research archive (crypto
only, top 20, 2020-05 -> 2026-08), for every set-up the bot can run.

  python3 research/c504_target_probability.py BNC_DIR [--out results.json]

For each set-up it reports, from the daily returns:
  - P(a calendar month >= +2%), P(month >= 0), P(month in +2..+4%);
  - P(the average month over 6 and 12 months >= +2%, compounded), over every
    rolling window and by a 30-day block bootstrap (10,000 years);
  - the same with the forward haircut used throughout (a third off the mean);
  - worst month, worst drawdown.
And the book alone at dials 5..30%: which dial gives the best chance of a
+2%/month year, and where growth (Kelly) peaks.

Nothing here is admitted or changed in the bot: it measures what exists.
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
EQ, FLOOR = 250.0, 6.0
rng = np.random.default_rng(504)

# ── the futures book at a given dial (target vol = dial x 4/3) ───────────────
r2, Wb, eb = R.crypto_sleeves(T, close, qv, fund)
parts = {k: Wb[k] for k in ('C1', 'C2', 'C3')}


def book(dial):
    W = R.combine(parts, r2, fund, 1, target_vol=dial * 4.0 / 3.0 / 100.0)
    W = np.where(np.abs(W) * EQ >= FLOOR, W, 0.0)
    x, info = R.pnl(W, r2, fund, 1)
    return x, info['gross_exp']


def savings(gross, dial, apr):
    """idle cash in Flexible Savings: reserve = margin (gross/5) + dial + 5%."""
    idle = np.clip(1.0 - gross / 5.0 - dial / 100.0 - 0.05, 0.0, 1.0)
    return idle * apr / 365.0


# ── the spot pot, S1 with C502's minimums ────────────────────────────────────
r = R.returns(close); sd = R.trailing_std(r, 30); elig = R.universe(close, qv)
sc = np.nan_to_num(R.vol_scale(sd)); zero = np.zeros_like(fund)
s = sum(np.sign(np.nan_to_num(R.lagret(close, d))) for d in (7, 14, 28, 56)) / 4.0
W1 = R.banded(np.where(elig, np.maximum(s, 0.0) * sc / 20, 0.0))
u = R.pnl(W1, r, zero, 1, cost=0.0010)[0]
n = len(T); L = np.zeros(n)
for i in range(60, n):
    v = u[i - 60:i].std() * math.sqrt(365); L[i] = 0.20 / v if v > 0 else 0.0
W0 = W1 * L[:, None]; g = np.abs(W0).sum(1); W0 = W0 * np.where(g > 1.0, 1.0 / np.maximum(g, 1e-12), 1.0)[:, None]
Ws = np.zeros_like(W0); prev = np.zeros(W0.shape[1])
for i in range(n):
    tg = np.where(W0[i] * EQ >= 2.0, W0[i], 0.0)
    tg = np.where(np.abs(tg - prev) * EQ < 1.0, prev, tg)
    Ws[i] = tg; prev = tg


def spot(apr):
    xr = R.pnl(Ws, r, zero, 1, cost=0.0010)[0]
    gl = np.zeros(n); gl[1:] = np.abs(Ws).sum(1)[:-1]
    return xr + (1.0 - gl) * apr / 365.0


live = max(np.nonzero(L > 0)[0][0] + 1, 130)          # both the book and the pot have warmed up
TT = T[live:]


def months(y):
    m = {}
    for t, v in zip(TT, y):
        k = dt.datetime.utcfromtimestamp(t / 1000).strftime('%Y-%m'); m[k] = m.get(k, 1.0) * (1 + v)
    return np.array([v - 1 for v in m.values()])


def maxdd(y):
    e = np.cumprod(1 + y); return float((1 - e / np.maximum.accumulate(e)).max())


def boot_years(y, horizon_days, reps=10000, block=30):
    """block bootstrap of daily returns: compounded return over the horizon."""
    nb = int(math.ceil(horizon_days / block)); out = np.empty(reps)
    starts = rng.integers(0, len(y) - block, size=(reps, nb))
    for k in range(reps):
        path = np.concatenate([y[a:a + block] for a in starts[k]])[:horizon_days]
        out[k] = np.prod(1 + path) - 1
    return out


def report(name, y):
    y = y[live:]
    mv = months(y)
    hair = y - y.mean() / 3.0                            # the forward haircut: a third off the mean
    res = dict(month_mean=float(mv.mean()), month_median=float(np.median(mv)),
               p_month_ge2=float((mv >= 0.02).mean()), p_month_ge0=float((mv >= 0).mean()),
               p_month_2to4=float(((mv >= 0.02) & (mv <= 0.04)).mean()), worst_month=float(mv.min()),
               maxdd=maxdd(y), cagr_month=float(np.prod(1 + y) ** (365 / len(y) / 12) - 1))
    for hm in (6, 12):
        need = 1.02 ** hm - 1
        cm = np.array([np.prod(1 + mv[i:i + hm]) - 1 for i in range(len(mv) - hm + 1)])
        res[f'p_{hm}m_roll'] = float((cm >= need).mean())
        res[f'p_{hm}m_boot'] = float((boot_years(y, int(hm * 30.44)) >= need).mean())
        res[f'p_{hm}m_boot_haircut'] = float((boot_years(hair, int(hm * 30.44)) >= need).mean())
    mh = months(hair)
    res['p_month_ge2_haircut'] = float((mh >= 0.02).mean())
    print(f"  {name:44} {100*res['cagr_month']:+5.2f}%/mo | month>=2%: {100*res['p_month_ge2']:3.0f}% "
          f"(haircut {100*res['p_month_ge2_haircut']:3.0f}%)  month>=0: {100*res['p_month_ge0']:3.0f}%  "
          f"in 2-4%: {100*res['p_month_2to4']:3.0f}% | 12 months avg>=2%: rolling {100*res['p_12m_roll']:3.0f}%, "
          f"boot {100*res['p_12m_boot']:3.0f}%, haircut {100*res['p_12m_boot_haircut']:3.0f}% | "
          f"6 months: boot {100*res['p_6m_boot']:3.0f}% | worst month {100*res['worst_month']:+5.1f}%, "
          f"max DD {100*res['maxdd']:4.1f}%")
    return res


print("=" * 150)
print(f"C504: THE PROBABILITY OF +2%/MONTH | crypto top 20 | "
      f"{dt.datetime.utcfromtimestamp(TT[0]/1000).date()} .. {dt.datetime.utcfromtimestamp(TT[-1]/1000).date()} | "
      f"Savings at 5%/yr (conservative; 7.63% on 28 Sep)")
print("=" * 150)
out = {}
xb15, g15 = book(15); xb20, g20 = book(20)
sv15 = savings(g15, 15, 0.05); sv20 = savings(g20, 20, 0.05)
xs = spot(0.05)
cfgs = {
    'book, dial 15% (running)': xb15,
    'book, dial 15% + idle cash in Savings': xb15 + sv15,
    'book, dial 20% + Savings': xb20 + sv20,
    'spot pot (S1, C502 minimums)': xs,
    'both pots: book 15% + Savings, spot pot': 0.5 * (xb15 + sv15) + 0.5 * xs,
    'both pots: book 20% + Savings, spot pot': 0.5 * (xb20 + sv20) + 0.5 * xs,
}
for k, y in cfgs.items():
    out[k] = report(k, y)

print("\n  THE DIAL, the book alone + Savings (every dial on the same data):")
dials = {}
for d in (5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 30):
    xb, gb = book(d); y = (xb + savings(gb, d, 0.05))[live:]
    b12 = boot_years(y, 365); b12h = boot_years(y - y.mean() / 3.0, 365)
    glog = float(np.mean(np.log1p(y)) * 365)
    dials[d] = dict(p12=float((b12 >= 1.02 ** 12 - 1).mean()), p12h=float((b12h >= 1.02 ** 12 - 1).mean()),
                    med12=float(np.median(b12)), p_loss12=float((b12 < 0).mean()), maxdd=maxdd(y), log_growth=glog)
    print(f"   dial {d:4.1f}%: P(a +2%/month year) {100*dials[d]['p12']:3.0f}% (haircut {100*dials[d]['p12h']:3.0f}%) | "
          f"median year {100*dials[d]['med12']:+5.0f}% | P(losing year) {100*dials[d]['p_loss12']:3.0f}% | "
          f"max DD {100*dials[d]['maxdd']:4.1f}% | log growth {100*glog:+5.1f}%/yr")
kelly = max(dials, key=lambda k: dials[k]['log_growth'])
best = max(dials, key=lambda k: dials[k]['p12h'])
print(f"   growth (Kelly) peaks at dial {kelly}% on this data; the best haircut chance of a +2%/month year is at dial {best}%")
out['dials'] = {str(k): v for k, v in dials.items()}
out['kelly_dial'] = kelly; out['best_p12_dial'] = best

# ── the arithmetic of 70-90% ─────────────────────────────────────────────────
print("\n  THE ARITHMETIC: P(month >= +2%) = Phi((mu - 2%) / sigma) for a monthly mean mu and spread sigma")
for p in (0.5, 0.7, 0.8, 0.9):
    z = {0.5: 0.0, 0.7: 0.5244, 0.8: 0.8416, 0.9: 1.2816}[p]
    for sig in (0.02, 0.04, 0.06):
        mu = 0.02 + z * sig
        print(f"   {int(100*p)}% of months >= +2% with a {100*sig:.0f}% monthly spread needs a mean of "
              f"{100*mu:+.1f}%/month -> annual Sharpe {mu / sig * math.sqrt(12):.1f}")
if '--out' in sys.argv:
    json.dump(out, open(sys.argv[sys.argv.index('--out') + 1], 'w'), indent=1)
