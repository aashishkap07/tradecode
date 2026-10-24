#!/usr/bin/env python3
# usage (from the repo root): python3 research/c488_intraday_mix.py BNC_DIR   -- needs corpusO/ and corpusL/
"""Would adding an intraday engine to the C488 book help? Measured on the overlap of
the 15m corpus (32 coins, Feb 15 - Sep 16 2026) and the C488 backtest (to Aug 31)."""
import sys, os, glob, math, json, datetime as dt, numpy as np, warnings
warnings.simplefilter('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import omega_c488_research as R
SP = sys.argv[1]
DAY = 86400000
# ── 1. the intraday style the bot trades: the 'chase' entry, 1-hour hold ──────
def bars(sym):
    rows = {}
    for d in ('corpusO', 'corpusL'):
        p = f'{d}/{sym}'
        if os.path.exists(p):
            for ln in open(p):
                x = ln.split(',')
                if len(x) >= 6: rows[int(x[0])] = [float(v) for v in x[1:5]]
    t = sorted(rows); return np.array(t), np.array([rows[k] for k in t])
daily = {}; dcount = {}; gross_all = []; net_all = []
ntr = 0
for f in sorted(os.listdir('corpusO')):
    t, a = bars(f)
    o, h, l, c = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    last = -99
    for i in range(12, len(c) - 4):
        if i - last < 4: continue
        r3 = c[i] / c[i - 12] - 1; hi = h[i - 11:i + 1].max(); lo = l[i - 11:i + 1].min()
        pos = (c[i] - lo) / (hi - lo) if hi > lo else 0.5
        sg = 1 if (r3 >= 0.02 and pos >= 0.75) else (-1 if (r3 <= -0.02 and pos <= 0.25) else 0)
        if not sg: continue
        last = i
        g = sg * (c[i + 4] / c[i] - 1); ret = g - 0.0012 - 0.0004   # taker both ways + spread
        gross_all.append(g); net_all.append(ret)
        d = int(t[i]) // DAY * DAY
        daily[d] = daily.get(d, 0.0) + ret; dcount[d] = dcount.get(d, 0) + 1
        ntr += 1
# the bot takes ~23 trades a day at ~$80 notional on $250: scale the day's AVERAGE trade to that
daily = {d: daily[d] / dcount[d] * 23 * 0.32 for d in daily}
print(f"per trade: before costs {100*np.mean(gross_all):+.3f}%  after 0.16% costs {100*np.mean(net_all):+.3f}%  (n={len(net_all)})")
# ── 2. the C488 book, as it runs at $250 (top 20, $6 minimum) ─────────────────
T, syms, close, qv, fund = R.load_crypto(SP)
R.TOPN = 20
r, W, elig = R.crypto_sleeves(T, close, qv, fund)
Wc = R.combine({k: W[k] for k in ('C1', 'C2', 'C3')}, r, fund, 1)
Wc = np.where(np.abs(Wc) * 250 >= 6, Wc, 0.0)
book = dict(zip(T.tolist(), R.pnl(Wc, r, fund, 1)[0]))
days = sorted(d for d in daily if d in book and d >= min(daily) and d <= max(book))
days = [d for d in range(min(daily), max(book) + 1, DAY) if d in book]
x = np.array([daily.get(d, 0.0) for d in days]); y = np.array([book[d] for d in days])
sh = lambda v: v.mean() / v.std() * math.sqrt(365) if v.std() > 0 else float('nan')
rho = np.corrcoef(x, y)[0, 1]
print(f"overlap {dt.datetime.utcfromtimestamp(days[0]/1000):%Y-%m-%d} .. {dt.datetime.utcfromtimestamp(days[-1]/1000):%Y-%m-%d}: {len(days)} days, {ntr} intraday-style trades")
print(f"  intraday chase style (taker, 1h hold): {100*x.mean()*30.4:+.2f}%/month  Sharpe {sh(x):+.2f}")
print(f"  C488 book at \$250:                      {100*y.mean()*30.4:+.2f}%/month  Sharpe {sh(y):+.2f}")
print(f"  daily correlation between them: {rho:+.2f}")
for wgt in (0.25, 0.5, 1.0):
    z = y + wgt * x
    print(f"  book + {wgt:.2f} x intraday: {100*z.mean()*30.4:+.2f}%/month  Sharpe {sh(z):+.2f}")
# worst days: does the intraday style lose on the book's bad days?
bad = y <= np.quantile(y, 0.1)
for s2 in (-0.5, 0.0, 0.5, 1.0):
    s1 = sh(y); comb = math.sqrt(max(0.0, (s1**2 + s2**2 - 2*rho*s1*s2) / (1 - rho**2)))
    print(f"  IF an intraday engine had Sharpe {s2:+.1f} at this correlation, the best mix would reach Sharpe {comb:.2f} (book alone {s1:.2f})")
print(f"  on the book's worst 10% of days the intraday style made {100*x[bad].mean():+.3f}%/day (vs {100*x.mean():+.3f}% on average)")

