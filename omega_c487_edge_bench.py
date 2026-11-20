#!/usr/bin/env python3
"""Longer-horizon edges on 5 years of Bitget perps, pre-registered  [C487]

    python3 omega_c487_edge_bench.py WORKDIR [1D|4H]

Fetches (and caches in WORKDIR/hist) 5 years of daily and 4-hour candles for 30
liquid USDT perpetuals from Bitget's public API, then tests ten well-documented
strategies as equal-capital, volatility-scaled portfolios:
  time-series momentum (1 week, 4 weeks, a 1/2/4/8-week blend), a 20/10-day
  Donchian breakout, cross-sectional 1-week momentum and 1-day reversal, alts
  long only while BTC is above its 50-day average, buy-and-hold for reference,
  and on 4-hour bars 1-day and 3-day momentum.
Net of 0.06% taker + 0.02% half-spread per unit turnover and 0.01%/8h funding
paid on longs (shorts are credited nothing -- conservative both ways). Admitted
only if the net mean is positive in >= 3 of 4 chronological quarters AND the
Newey-West t (5 lags) is >= 2. Survivorship bias: the 30 coins are ones alive
today, which flatters anything long-biased.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
WORK = sys.argv[1] if len(sys.argv) > 1 else 'edge_work'
os.makedirs(os.path.join(WORK, 'hist'), exist_ok=True)
import json as _json
import omega_live_forensics as _lf
_COINS = "BTC ETH SOL XRP DOGE ADA BNB LINK AVAX DOT LTC BCH TRX NEAR UNI ATOM ETC FIL APT ARB OP SUI INJ AAVE XLM HBAR ICP SEI TIA WLD".split()
_G = sys.argv[2] if len(sys.argv) > 2 else '1D'
_t1 = int(time.time() * 1000)
for _c in _COINS:
    _p = os.path.join(WORK, 'hist', f'{_c}_{_G}.json')
    if not os.path.exists(_p):
        _json.dump(_lf.candles(_c + 'USDT', _t1 - 5 * 365 * 86400000, _t1, gran=_G), open(_p, 'w'))
        print(f"   fetched {_c} {_G}", flush=True)
os.chdir(WORK)
sys.argv = [sys.argv[0], _G]

import json, glob, os, math, sys, statistics as st
import numpy as np
G = sys.argv[1] if len(sys.argv) > 1 else '1D'
COST = 0.0008
BARS_PER_DAY = 1 if G == '1D' else 6
FUND_PER_BAR = 0.0003 / BARS_PER_DAY
files = sorted(glob.glob(f'hist/*_{G}.json'))
series = {}
for p in files:
    c = os.path.basename(p).split('_')[0]
    r = json.load(open(p))
    if len(r) > 200: series[c] = {x[0]: x for x in r}
T = sorted(set().union(*[s.keys() for s in series.values()]))
coins = sorted(series)
N, K = len(T), len(coins)
close = np.full((N, K), np.nan); high = close.copy(); low = close.copy()
ti = {t: i for i, t in enumerate(T)}
for j, c in enumerate(coins):
    for t, x in series[c].items():
        close[ti[t], j], high[ti[t], j], low[ti[t], j] = x[4], x[2], x[3]
ret = np.full_like(close, np.nan); ret[1:] = close[1:] / close[:-1] - 1
# only trade a coin after 60 bars of history (fresh listings are wild)
age = np.cumsum(~np.isnan(close), axis=0); alive = (age > 60) & ~np.isnan(close)
def lagret(n):
    out = np.full_like(close, np.nan); out[n:] = close[n:] / close[:-n] - 1; return out
vol = np.full_like(close, np.nan)
for i in range(30, N):
    vol[i] = np.nanstd(ret[i-29:i+1], axis=0)
def rollmax(a, n):
    out = np.full_like(a, np.nan)
    for i in range(n, N): out[i] = np.nanmax(a[i-n:i], axis=0)   # previous n bars, excluding today
    return out
def rollmin(a, n):
    out = np.full_like(a, np.nan)
    for i in range(n, N): out[i] = np.nanmin(a[i-n:i], axis=0)
    return out
def xsrank(sig):
    """+1 top third, -1 bottom third, among live coins"""
    out = np.zeros_like(sig)
    for i in range(N):
        m = alive[i] & ~np.isnan(sig[i])
        if m.sum() < 9: continue
        v = sig[i][m]; lo, hi = np.quantile(v, [1/3, 2/3])
        o = np.zeros(m.sum()); o[v >= hi] = 1; o[v <= lo] = -1
        out[i][m] = o
    return out
def turtle(n_in, n_out):
    hi_in, lo_in, hi_out, lo_out = rollmax(high, n_in), rollmin(low, n_in), rollmax(high, n_out), rollmin(low, n_out)
    pos = np.zeros_like(close)
    for i in range(1, N):
        p = pos[i-1].copy()
        c = close[i]
        p = np.where((p > 0) & (c < lo_out[i]), 0, p)
        p = np.where((p < 0) & (c > hi_out[i]), 0, p)
        p = np.where((p == 0) & (c > hi_in[i]), 1, p)
        p = np.where((p == 0) & (c < lo_in[i]), -1, p)
        pos[i] = np.nan_to_num(p)
    return pos
d = BARS_PER_DAY
btc = coins.index('BTC')
btc_ma = np.full(N, np.nan)
for i in range(50*d, N): btc_ma[i] = np.nanmean(close[i-50*d+1:i+1, btc])
SIG = {
    'TSMOM 7d (sign of last week)':       np.sign(lagret(7*d)),
    'TSMOM 28d (sign of last 4 weeks)':   np.sign(lagret(28*d)),
    'TSMOM blend 7/14/28/56d':            (np.sign(lagret(7*d)) + np.sign(lagret(14*d)) + np.sign(lagret(28*d)) + np.sign(lagret(56*d))) / 4,
    'Donchian 20/10 breakout (turtle)':   turtle(20*d, 10*d),
    'X-section momentum 7d (top-bottom)': xsrank(lagret(7*d)),
    'X-section reversal 1d (bottom-top)': -xsrank(lagret(1*d)),
    'Long alts only when BTC > 50d MA':   np.where((close[:, [btc]] > btc_ma[:, None]), 1.0, 0.0) * np.ones_like(close),
    **({'TSMOM 24h (sign of last day), 4h bars': np.sign(lagret(6)), 'TSMOM 3d, 4h bars': np.sign(lagret(18))} if G == '4H' else {}),
    'Buy and hold all (reference)':       np.ones_like(close),
}
def nw_t(x, L=5):
    x = np.asarray(x); n = len(x); m = x.mean(); e = x - m
    g0 = (e @ e) / n; s = g0
    for l in range(1, L+1): s += 2 * (1 - l/(L+1)) * (e[l:] @ e[:-l]) / n
    return m / math.sqrt(s / n) if s > 0 else float('nan')
print(f"{G}: {K} coins, {N} bars, {T and __import__('datetime').datetime.utcfromtimestamp(T[0]/1000):%Y-%m-%d} .. {__import__('datetime').datetime.utcfromtimestamp(T[-1]/1000):%Y-%m-%d}")
print(f"{'strategy':38} {'ann.net%':>8} {'t(NW)':>6} {'Q1':>7} {'Q2':>7} {'Q3':>7} {'Q4':>7} {'pos Q':>5} {'turn/yr':>7} {'maxDD%':>7}  verdict")
res = {}
for name, raw in SIG.items():
    pos = np.where(alive, np.nan_to_num(raw), 0.0)
    # risk-parity-lite: scale each coin to ~2% daily vol, capped at 1x
    scale = np.clip(0.02 / np.sqrt(d) / np.where(vol > 0, vol, np.nan), 0, 1.0)
    pos = np.nan_to_num(pos * scale)
    nlive = np.maximum(alive.sum(1), 1)[:, None]
    w = pos / nlive                                    # equal capital per coin
    gross = np.nansum(w[:-1] * np.nan_to_num(ret[1:]), axis=1)
    turn = np.nansum(np.abs(np.diff(w, axis=0)), axis=1)
    fund = np.nansum(np.clip(w[:-1], 0, None), axis=1) * FUND_PER_BAR
    net = gross - turn * COST - fund
    net = net[60*d:]; tr = turn[60*d:]
    q = np.array_split(net, 4)
    qm = [x.mean() * 365 * d * 100 for x in q]
    eq = np.cumprod(1 + net); dd = (1 - eq / np.maximum.accumulate(eq)).max() * 100
    t = nw_t(net); npos = sum(x > 0 for x in qm)
    ok = npos >= 3 and abs(t) >= 2 and net.mean() > 0
    res[name] = dict(ann=float(net.mean()*365*d*100), t=float(t), q=[float(x) for x in qm], npos=int(npos), turn=float(tr.mean()*365*d), dd=float(dd), ok=bool(ok))
    print(f"{name:38} {net.mean()*365*d*100:>+8.1f} {t:>+6.2f} " + ' '.join(f"{x:>+7.1f}" for x in qm) +
          f" {npos:>3}/4 {tr.mean()*365*d:>7.1f} {dd:>7.1f}  {'ADMIT' if ok else '-'}")
json.dump(res, open(f'edges_{G}.json', 'w'))
print('results saved to', os.path.join(os.getcwd(), f'edges_{G}.json'))
